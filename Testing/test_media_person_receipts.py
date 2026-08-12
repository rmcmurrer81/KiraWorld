from __future__ import annotations

import hashlib
import math
import struct
import tempfile
import unittest
from pathlib import Path

from Core.emotion_system import (
    PersonEmotionLease,
    PersonEmotionLeaseError,
    PersonEmotionStateError,
    PersonOwnedEmotionState,
)
from Core.media_experience_session import MediaExperienceSession
from Core.media_person_receipts import (
    PersonMediaReceiptError,
    PersonMediaReceiptLeaseError,
    PersonMediaReceiptLedger,
    SupervisedMusicListeningReceipt,
)
from Core.source_bound_audio_perception import (
    AudioIntervalBinding,
    TransientDecodedAudio,
    build_source_bound_audio_cue,
)


class StepClock:
    def __init__(self, value: float = 100.0, step: float = 0.25) -> None:
        self.value = value
        self.step = step

    def __call__(self) -> float:
        value = self.value
        self.value += self.step
        return value


def pcm_f32(seconds: float, sample_rate: int = 8_000) -> bytes:
    values = [
        0.2 * math.sin(2 * math.pi * 220.0 * index / sample_rate)
        for index in range(round(seconds * sample_rate))
    ]
    return struct.pack("<" + "f" * len(values), *values)


class PersonOwnedEmotionStateTests(unittest.TestCase):
    def state(self, person_id: str) -> PersonOwnedEmotionState:
        return PersonOwnedEmotionState(
            person_id=person_id,
            activation_revision=f"{person_id}-activation-7",
            lease_nonce=f"{person_id}-private-nonce",
            state_revision="emotion-r1",
            clock=StepClock(),
        )

    def test_emotional_histories_are_person_scoped_and_private_by_default(self) -> None:
        kira = self.state("kira")
        lisa = self.state("lisa")
        appraisal = kira.record_event_appraisal(
            kira.lease,
            event_id="media-window-1",
            factual_event_summary="A source-bound audio interval was analyzed.",
            possible_model_interpretations=["possibly energetic", "possibly tense"],
            selected_appraisal="I am curious but undecided.",
            emotion_label="curiosity",
            intensity=0.4,
            source_receipt_sha256="a" * 64,
        )
        kira.choose_public_expression(
            kira.lease,
            appraisal_id=appraisal["appraisal_id"],
            choice="remain_quiet",
        )
        for channel in (
            "memory_significance",
            "relationship_effect",
            "voice_prosody",
            "facial_expression",
            "posture",
            "action_influence",
        ):
            kira.record_influence(
                kira.lease,
                channel=channel,
                appraisal_id=appraisal["appraisal_id"],
                selected_effect="no external change selected",
                strength=0.0,
            )

        with self.assertRaises(PersonEmotionLeaseError):
            kira.record_event_appraisal(
                lisa.lease,
                event_id="cross-person",
                factual_event_summary="wrong lease",
                possible_model_interpretations=[],
                selected_appraisal="must fail",
                emotion_label="neutral",
                intensity=0,
            )

        public = kira.snapshot()
        private = kira.snapshot(include_private=True)
        self.assertEqual(public["person_id"], "kira")
        self.assertEqual(lisa.snapshot()["person_id"], "lisa")
        self.assertEqual(public["channels"]["event_appraisals"], [])
        self.assertEqual(public["channels"]["emotional_continuity"], [])
        self.assertNotIn("curiosity", str(public))
        self.assertIsNone(public["private_state"])
        self.assertEqual(private["private_state"]["emotion_label"], "curiosity")
        self.assertTrue(
            private["channels"]["event_appraisals"][0][
                "possible_interpretations_are_advisory"
            ]
        )
        self.assertFalse(
            public["truth_boundaries"]["private_appraisal_automatically_public"]
        )
        self.assertFalse(public["truth_boundaries"]["body_response_proves_desire_or_consent"])

    def test_public_speech_hash_and_bounded_state_validation(self) -> None:
        state = self.state("temporary-person-4")
        appraisal = state.record_event_appraisal(
            state.lease,
            event_id="event",
            factual_event_summary="fact",
            possible_model_interpretations=[],
            selected_appraisal="uncertain",
            emotion_label="uncertainty",
            intensity=0.2,
        )
        with self.assertRaises(PersonEmotionStateError):
            state.choose_public_expression(
                state.lease,
                appraisal_id=appraisal["appraisal_id"],
                choice="speak",
            )
        with self.assertRaisesRegex(PersonEmotionStateError, "unknown"):
            state.choose_public_expression(
                state.lease,
                appraisal_id="appraisal_missing",
                choice="remain_quiet",
            )
        with self.assertRaisesRegex(PersonEmotionStateError, "unknown"):
            state.record_influence(
                state.lease,
                channel="voice_prosody",
                appraisal_id="appraisal_missing",
                selected_effect="none",
                strength=0,
            )
        spoken = "I am not sure yet."
        record = state.choose_public_expression(
            state.lease,
            appraisal_id=appraisal["appraisal_id"],
            choice="speak",
            public_text_sha256=hashlib.sha256(spoken.encode()).hexdigest(),
        )
        self.assertEqual(record["choice"], "speak")
        self.assertFalse(record["inference_model_owns_state"])


class MediaPersonReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "Data" / "library" / "music" / "fixture.raw"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"exact synthetic fixture identity")
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def session(self, *, person_id: str = "kira") -> MediaExperienceSession:
        return MediaExperienceSession(
            project_root=self.root,
            source_path=self.source,
            kind="music",
            person_id=person_id,
            activation_revision="activation-r3",
            session_id=f"music-{person_id}-session-1",
            session_nonce=f"{person_id}-nonce",
            media_duration_seconds=30,
            clock=StepClock(),
        )

    def cue(self, start: float, end: float, index: int):
        binding = AudioIntervalBinding(
            stimulus_id=f"window-{index}",
            project_relative_library_path="Data/library/music/fixture.raw",
            source_sha256=self.source_hash,
            opaque_media_id="opaque-fixture",
            start_seconds=start,
            end_seconds=end,
            content_hint="non_speech",
        )
        with TransientDecodedAudio(
            binding=binding,
            sample_rate_hz=8_000,
            channels=1,
            stream_index=0,
            pcm_f32le=pcm_f32(end - start),
        ) as window:
            return build_source_bound_audio_cue(window)

    def add_window(
        self,
        receipt: SupervisedMusicListeningReceipt,
        *,
        start: float,
        end: float,
        index: int,
        retry_of: str | None = None,
        gap_reason: str | None = None,
    ):
        return receipt.add_pcm_window(
            receipt.lease,
            audio_cue=self.cue(start, end, index),
            sidecar_id="builtin-source-bound-pcm-features",
            sidecar_version="1",
            sidecar_binary_sha256="b" * 64,
            analysis_started_at_utc=f"2026-08-08T12:00:{index:02d}.000000Z",
            analysis_ended_at_utc=f"2026-08-08T12:00:{index:02d}.500000Z",
            uncertainty={
                "tempo": "provisional",
                "tonality": "not_estimated",
                "instrumentation": "unknown",
            },
            delivered_to_qwen=False,
            retry_of_window_id=retry_of,
            gap_reason=gap_reason,
        )

    def test_existing_presentation_machine_evidence_and_attention_stay_separate(self) -> None:
        session = self.session()
        session.resume(session.lease)
        session.pause(session.lease, at_media_seconds=2)
        ledger = PersonMediaReceiptLedger(media_session=session, clock=StepClock())
        presentation = ledger.record_source_presentation(
            session.lease,
            start_seconds=0,
            end_seconds=2,
            playback_clock_started_at_utc="2026-08-08T12:00:00.000000Z",
            playback_clock_ended_at_utc="2026-08-08T12:00:02.000000Z",
            actual_output_receipt_sha256="c" * 64,
        )
        evidence = ledger.record_machine_evidence(
            session.lease,
            evidence={
                "source_binding": {
                    "project_relative_library_path": "Data/library/music/fixture.raw",
                    "source_sha256": self.source_hash,
                    "start_seconds": 0,
                    "end_seconds": 2,
                },
                "basis": "actual decoded bytes",
                "uncertainty": "high",
            },
            evidence_kind="test_fixture",
            start_seconds=0,
            end_seconds=2,
            delivered_to_person_context=False,
            delivered_at_utc=None,
        )
        with self.assertRaisesRegex(PersonMediaReceiptError, "source hash does not match"):
            ledger.record_machine_evidence(
                session.lease,
                evidence={
                    "source_binding": {
                        "project_relative_library_path": "Data/library/music/fixture.raw",
                        "source_sha256": "f" * 64,
                        "start_seconds": 0,
                        "end_seconds": 2,
                    }
                },
                evidence_kind="wrong_source_fixture",
                start_seconds=0,
                end_seconds=2,
                delivered_to_person_context=False,
                delivered_at_utc=None,
            )
        ledger.record_attention_choice(
            session.lease,
            choice="pause",
            based_on_record_ids=[presentation["record_id"], evidence["record_id"]],
            person_choice_confirmed=True,
        )
        snapshot = ledger.snapshot()
        self.assertFalse(snapshot["truth_boundaries"]["presentation_is_attention"])
        self.assertFalse(snapshot["truth_boundaries"]["machine_evidence_is_attention"])
        self.assertEqual(snapshot["record_counts"]["attention_choice"], 1)

    def test_ordered_pcm_windows_gaps_overlap_retry_stop_and_release(self) -> None:
        receipt = SupervisedMusicListeningReceipt(
            media_session=self.session(), clock=StepClock()
        )
        first = self.add_window(receipt, start=0, end=4, index=1)
        second = self.add_window(receipt, start=3, end=7, index=2)
        retry = self.add_window(
            receipt,
            start=3,
            end=7,
            index=3,
            retry_of=second["window_id"],
        )
        fourth = self.add_window(
            receipt,
            start=8,
            end=10,
            index=4,
            gap_reason="bounded test intentionally omitted 7..8",
        )
        receipt.record_choice(
            receipt.lease,
            choice="continue",
            based_on_window_ids=[first["window_id"], second["window_id"]],
            person_choice_confirmed=True,
        )
        receipt.record_choice(
            receipt.lease,
            choice="stop",
            based_on_window_ids=[fourth["window_id"]],
            person_choice_confirmed=True,
        )
        with self.assertRaisesRegex(PersonMediaReceiptError, "chose stop"):
            self.add_window(receipt, start=10, end=12, index=5)
        final = receipt.finalize(
            sidecar_released=True,
            qwen_released_or_not_started=True,
        )
        self.assertEqual(final["retry_count"], 1)
        self.assertGreaterEqual(final["overlap_window_count"], 1)
        self.assertEqual(final["unexplained_gap_count"], 0)
        self.assertTrue(final["release"]["clean_release"])
        self.assertFalse(final["truth_boundaries"]["physical_playback_performed"])
        self.assertFalse(final["truth_boundaries"]["person_heard_audio"])
        self.assertFalse(
            final["truth_boundaries"]["music_listening_or_enjoyment_acceptance"]
        )
        self.assertEqual(retry["retry_of_window_id"], second["window_id"])
        self.assertFalse(first["playback_clock"]["physical_playback_performed"])
        self.assertEqual(first["capture_clock"]["started_at_utc"], "2026-08-08T12:00:01.000000Z")

    def test_metadata_cannot_substitute_for_pcm_and_single_session_cannot_promote(self) -> None:
        session = self.session()
        ledger = PersonMediaReceiptLedger(media_session=session, clock=StepClock())
        evidence = ledger.record_machine_evidence(
            session.lease,
            evidence={
                "source_binding": {
                    "project_relative_library_path": "Data/library/music/fixture.raw",
                    "source_sha256": self.source_hash,
                    "start_seconds": 0,
                    "end_seconds": 1,
                },
                "measurement_basis": "fixture actual samples",
            },
            evidence_kind="fixture",
            start_seconds=0,
            end_seconds=1,
            delivered_to_person_context=False,
            delivered_at_utc=None,
        )
        private = ledger.record_private_appraisal(
            session.lease,
            appraisal="I am undecided.",
            based_on_record_ids=[evidence["record_id"]],
        )
        ledger.record_temporary_reaction(
            session.lease,
            label="curiosity",
            intensity=0.3,
            based_on_record_ids=[evidence["record_id"]],
        )
        with self.assertRaisesRegex(PersonMediaReceiptError, "exact existing evidence"):
            ledger.record_private_appraisal(
                session.lease,
                appraisal="unsupported",
                based_on_record_ids=["machine_evidence_missing"],
            )
        with self.assertRaisesRegex(PersonMediaReceiptError, "exact existing evidence"):
            ledger.record_temporary_reaction(
                session.lease,
                label="unsupported",
                intensity=0.2,
                based_on_record_ids=["machine_evidence_missing"],
            )
        candidate = ledger.record_durable_preference_candidate(
            session.lease,
            preference_statement="I may prefer this style.",
            based_on_record_ids=[evidence["record_id"], private["record_id"]],
        )
        self.assertEqual(candidate["status"], "PENDING_LATER_CROSS_SESSION_PERSON_REVIEW")
        self.assertFalse(candidate["durable_preference_created"])
        with self.assertRaisesRegex(PersonMediaReceiptError, "external supporting-session receipts"):
            ledger.promote_durable_preference(
                session.lease,
                preference_statement="I prefer this style.",
                supporting_session_ids=[session.lease.session_id, "invented-session-2"],
                person_confirmed=True,
                reviewer_id="owner-review",
            )
        corrected = ledger.record_correction(
            session.lease,
            target_record_id=private["record_id"],
            exact_correction_text="I was curious, not undecided.",
            resulting_statement="I was curious.",
        )
        memory = ledger.promote_reviewed_memory(
            session.lease,
            memory_statement="I encountered a one-second synthetic fixture.",
            supporting_record_ids=[evidence["record_id"], corrected["record_id"]],
            person_confirmed=True,
            reviewer_id="owner-review",
        )
        public = ledger.snapshot()
        private_snapshot = ledger.snapshot(include_private=True)
        self.assertEqual(public["records"]["private_appraisal"], [])
        self.assertEqual(public["records"]["durable_preference"], [])
        self.assertEqual(public["records"]["correction"], [])
        self.assertEqual(public["records"]["reviewed_memory_promotion"], [])
        self.assertEqual(len(private_snapshot["records"]["private_appraisal"]), 1)
        self.assertEqual(len(private_snapshot["records"]["durable_preference"]), 1)
        self.assertFalse(memory["automatic_memory_promotion"])
        self.assertFalse(public["truth_boundaries"]["metadata_or_filename_counts_as_hearing"])

    def test_unexplained_music_gap_fails_closed_at_finalize(self) -> None:
        receipt = SupervisedMusicListeningReceipt(media_session=self.session())
        self.add_window(receipt, start=0, end=2, index=1)
        self.add_window(receipt, start=3, end=4, index=2)
        with self.assertRaisesRegex(PersonMediaReceiptError, "unexplained source-time gap"):
            receipt.finalize(
                sidecar_released=True,
                qwen_released_or_not_started=True,
            )

    def test_qwen_delivery_requires_exact_model_identity_and_person_lease(self) -> None:
        receipt = SupervisedMusicListeningReceipt(media_session=self.session())
        wrong_session = self.session(person_id="lisa")
        with self.assertRaises(PersonMediaReceiptLeaseError):
            receipt.add_pcm_window(
                wrong_session.lease,
                audio_cue=self.cue(0, 1, 1),
                sidecar_id="sidecar",
                sidecar_version="1",
                sidecar_binary_sha256="d" * 64,
                analysis_started_at_utc="2026-08-08T12:00:00.000000Z",
                analysis_ended_at_utc="2026-08-08T12:00:01.000000Z",
                uncertainty={},
                delivered_to_qwen=False,
            )
        with self.assertRaisesRegex(PersonMediaReceiptError, "exact qwen3.5"):
            receipt.add_pcm_window(
                receipt.lease,
                audio_cue=self.cue(0, 1, 2),
                sidecar_id="sidecar",
                sidecar_version="1",
                sidecar_binary_sha256="d" * 64,
                analysis_started_at_utc="2026-08-08T12:00:00.000000Z",
                analysis_ended_at_utc="2026-08-08T12:00:01.000000Z",
                uncertainty={},
                delivered_to_qwen=True,
                qwen_model_name="llama3.1:8b",
                qwen_model_digest="e" * 64,
                delivered_at_utc="2026-08-08T12:00:01.100000Z",
            )


if __name__ == "__main__":
    unittest.main()
