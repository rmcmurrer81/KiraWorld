import pickle
import sys
import threading
import unittest
from dataclasses import replace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from ephemeral_sensory_buffer import (  # noqa: E402
    EphemeralSensoryBuffer,
    LeaseValidationError,
    RawSensoryPayloadRejected,
    SensoryCapacityError,
)


class FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class EphemeralSensoryBufferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.buffer = EphemeralSensoryBuffer(
            ttl_seconds=5.0,
            max_count=8,
            max_derived_bytes=4096,
            clock=self.clock,
        )
        self.lease = self.buffer.activate("kira", "activation-r1")

    def add_cue(self, fact: object = "Robert is speaking") -> dict[str, object]:
        return self.buffer.add_factual_cue(
            self.lease,
            fact,
            source="derived_microphone_classifier",
            observed_at="2026-08-01T18:32:57-04:00",
            confidence=0.94,
        )

    def test_lease_contains_person_revision_and_cryptographic_nonce(self) -> None:
        self.assertEqual(self.lease.person_id, "kira")
        self.assertEqual(self.lease.activation_revision, "activation-r1")
        self.assertGreaterEqual(len(self.lease.session_nonce), 32)
        second = EphemeralSensoryBuffer(clock=self.clock).activate("kira", "activation-r1")
        self.assertNotEqual(self.lease.session_nonce, second.session_nonce)

    def test_every_lease_component_must_match_exactly(self) -> None:
        cue = self.add_cue()
        for bad_lease in (
            replace(self.lease, person_id="lisa"),
            replace(self.lease, activation_revision="activation-r2"),
            replace(self.lease, session_nonce=self.lease.session_nonce + "x"),
            {
                **self.lease.as_dict(),
                "unexpected": "not an exact lease",
            },
        ):
            with self.subTest(lease=bad_lease):
                with self.assertRaises(LeaseValidationError):
                    self.buffer.snapshot(bad_lease)
        self.assertEqual(self.buffer.snapshot(self.lease)["factual_cues"][0]["cue_id"], cue["cue_id"])

    def test_fact_private_attention_and_spoken_are_separate_explicit_lanes(self) -> None:
        cue = self.buffer.add_factual_cue(
            self.lease,
            {"person_present": True, "speech_activity": "detected"},
            source={"classifier": "local_derived_cue_v1"},
            observed_at="2026-08-01T18:33:00-04:00",
            confidence=0.8,
            attributes={"direction": "near desk"},
        )
        before = self.buffer.snapshot(self.lease)
        self.assertEqual(len(before["factual_cues"]), 1)
        self.assertEqual(before["private_attention_placeholders"], [])
        self.assertEqual(before["spoken_releases"], [])

        placeholder = self.buffer.add_private_attention_placeholder(self.lease, [cue["cue_id"]])
        self.assertEqual(placeholder["status"], "pending_private_decision")
        self.assertTrue(placeholder["private"])
        spoken = self.buffer.release_spoken(
            self.lease,
            "I hear you.",
            source_cue_ids=[cue["cue_id"]],
        )
        self.assertEqual(spoken["channel"], "SPOKEN")

        after = self.buffer.snapshot(self.lease)
        self.assertEqual(len(after["factual_cues"]), 1)
        self.assertEqual(len(after["private_attention_placeholders"]), 1)
        self.assertEqual(len(after["spoken_releases"]), 1)
        for lane in ("factual_cues", "private_attention_placeholders", "spoken_releases"):
            record = after[lane][0]
            self.assertTrue(record["ephemeral"])
            self.assertFalse(record["trusted_memory"])
            self.assertFalse(record["creates_consent"])
            self.assertFalse(record["changes_relationship"])

    def test_raw_media_fields_and_binary_or_base64_values_are_rejected(self) -> None:
        rejected_facts = (
            {"raw_image": "anything"},
            {"nested": {"audio_samples": [1, 2, 3]}},
            {"video_blob": "anything"},
            {"pixels": [[0, 1]]},
            {"image_data": "anything"},
            b"wave bytes",
            "data:image/png;base64,AAAA",
            "A" * 128,
        )
        for fact in rejected_facts:
            with self.subTest(fact=repr(fact)[:40]):
                with self.assertRaises(RawSensoryPayloadRejected):
                    self.add_cue(fact)
        self.assertEqual(self.buffer.stats(self.lease)["count"], 0)

    def test_derived_media_classifications_are_allowed_without_raw_media(self) -> None:
        cue = self.buffer.add_factual_cue(
            self.lease,
            {"image_classification": "one person", "audio_event": "speech detected"},
            source="local_derivative_only",
            observed_at=1234.5,
            confidence=0.75,
        )
        self.assertEqual(cue["fact"]["image_classification"], "one person")

    def test_ttl_expiry_is_deterministic_and_reclaims_byte_capacity(self) -> None:
        self.add_cue()
        occupied = self.buffer.stats(self.lease)
        self.assertEqual(occupied["count"], 1)
        self.assertGreater(occupied["derived_bytes"], 0)
        self.clock.advance(4.999)
        self.assertEqual(self.buffer.stats(self.lease)["count"], 1)
        self.clock.advance(0.001)
        self.assertEqual(self.buffer.purge_expired(), 1)
        self.assertEqual(self.buffer.stats(self.lease), {
            "count": 0,
            "derived_bytes": 0,
            "factual_cue_count": 0,
            "private_attention_placeholder_count": 0,
            "spoken_release_count": 0,
        })

    def test_count_and_derived_byte_caps_reject_without_partial_mutation(self) -> None:
        count_buffer = EphemeralSensoryBuffer(
            ttl_seconds=10,
            max_count=1,
            max_derived_bytes=4096,
            clock=self.clock,
        )
        lease = count_buffer.activate("arbitrary_person", 7)
        count_buffer.add_factual_cue(
            lease,
            "first",
            source="derived_test",
            observed_at=1.0,
            confidence=1.0,
        )
        with self.assertRaises(SensoryCapacityError):
            count_buffer.release_spoken(lease, "second")
        self.assertEqual(count_buffer.stats(lease)["count"], 1)

        byte_buffer = EphemeralSensoryBuffer(
            ttl_seconds=10,
            max_count=10,
            max_derived_bytes=80,
            clock=self.clock,
        )
        byte_lease = byte_buffer.activate("another_person", "r1")
        with self.assertRaises(SensoryCapacityError):
            byte_buffer.add_factual_cue(
                byte_lease,
                "derived observation " * 20,
                source="derived_test",
                observed_at=1.0,
                confidence=1.0,
            )
        self.assertEqual(byte_buffer.stats(byte_lease)["count"], 0)

    def test_switch_and_deactivate_purge_content_and_invalidate_old_lease(self) -> None:
        self.add_cue()
        new_lease = self.buffer.switch_person(self.lease, "lisa", "activation-r9")
        self.assertEqual(self.buffer.snapshot(new_lease)["count"], 0)
        with self.assertRaises(LeaseValidationError):
            self.buffer.snapshot(self.lease)

        self.buffer.add_factual_cue(
            new_lease,
            "Robert is nearby",
            source="derived_presence_classifier",
            observed_at=200,
            confidence=0.7,
        )
        self.assertEqual(self.buffer.deactivate(new_lease), 1)
        self.assertIsNone(self.buffer.current_lease)
        with self.assertRaises(LeaseValidationError):
            self.buffer.snapshot(new_lease)

    def test_direct_activation_switch_also_purges_without_reusing_nonce(self) -> None:
        self.add_cue()
        old_nonce = self.lease.session_nonce
        replacement = self.buffer.activate("kira", "activation-r2")
        self.assertEqual(self.buffer.snapshot(replacement)["count"], 0)
        self.assertNotEqual(replacement.session_nonce, old_nonce)

    def test_consume_exact_cues_preserves_lease_and_unrelated_newer_records(self) -> None:
        consumed = self.add_cue({"modality": "visual", "value": "bright"})
        surviving = self.add_cue({"modality": "auditory", "value": "music"})
        consumed_attention = self.buffer.add_private_attention_placeholder(
            self.lease,
            [consumed["cue_id"]],
        )
        surviving_attention = self.buffer.add_private_attention_placeholder(
            self.lease,
            [surviving["cue_id"]],
        )
        consumed_spoken = self.buffer.release_spoken(
            self.lease,
            "I can see a bright frame.",
            source_cue_ids=[consumed["cue_id"]],
        )
        old_nonce = self.lease.session_nonce

        result = self.buffer.consume_factual_cues(
            self.lease,
            [consumed["cue_id"], consumed["cue_id"]],
        )

        self.assertEqual(result["requested_cue_count"], 1)
        self.assertEqual(result["factual_cues_removed"], 1)
        self.assertEqual(result["dependent_records_removed"], 2)
        self.assertEqual(result["removed_count"], 3)
        self.assertTrue(result["lease_preserved"])
        self.assertEqual(self.buffer.current_lease.session_nonce, old_nonce)
        snapshot = self.buffer.snapshot(self.lease)
        self.assertEqual(
            [item["cue_id"] for item in snapshot["factual_cues"]],
            [surviving["cue_id"]],
        )
        self.assertNotIn(
            consumed_attention["placeholder_id"],
            [item["placeholder_id"] for item in snapshot["private_attention_placeholders"]],
        )
        self.assertEqual(
            [item["placeholder_id"] for item in snapshot["private_attention_placeholders"]],
            [surviving_attention["placeholder_id"]],
        )
        self.assertNotIn(
            consumed_spoken["release_id"],
            [item["release_id"] for item in snapshot["spoken_releases"]],
        )
        self.assertEqual(snapshot["count"], 2)

    def test_consume_cues_validates_ids_without_rotating_lease(self) -> None:
        cue = self.add_cue()
        old_nonce = self.lease.session_nonce

        with self.assertRaises(TypeError):
            self.buffer.consume_factual_cues(self.lease, cue["cue_id"])
        with self.assertRaises(ValueError):
            self.buffer.consume_factual_cues(self.lease, [" padded-cue-id "])

        no_op = self.buffer.consume_factual_cues(self.lease, ["cue_missing"])
        self.assertEqual(no_op["removed_count"], 0)
        self.assertTrue(no_op["lease_preserved"])
        self.assertEqual(self.buffer.current_lease.session_nonce, old_nonce)
        self.assertEqual(self.buffer.snapshot(self.lease)["factual_cues"][0]["cue_id"], cue["cue_id"])

    def test_returned_values_cannot_mutate_internal_content(self) -> None:
        cue = self.add_cue({"person_present": True})
        cue["fact"]["person_present"] = False
        snapshot = self.buffer.snapshot(self.lease)
        snapshot["factual_cues"][0]["fact"]["person_present"] = False
        fresh = self.buffer.snapshot(self.lease)
        self.assertTrue(fresh["factual_cues"][0]["fact"]["person_present"])

    def test_buffer_is_not_serializable_or_file_backed(self) -> None:
        self.add_cue()
        with self.assertRaises(TypeError):
            pickle.dumps(self.buffer)
        self.assertNotIn("path", vars(self.buffer))
        self.assertNotIn("file", vars(self.buffer))

    def test_thread_safe_admission_keeps_exact_count_cap(self) -> None:
        buffer = EphemeralSensoryBuffer(
            ttl_seconds=10,
            max_count=10,
            max_derived_bytes=20_000,
            clock=self.clock,
        )
        lease = buffer.activate("threaded_person", 1)
        accepted: list[str] = []
        rejected: list[str] = []
        result_lock = threading.Lock()

        def add(index: int) -> None:
            try:
                buffer.add_factual_cue(
                    lease,
                    f"derived fact {index}",
                    source="thread_test",
                    observed_at=index,
                    confidence=0.5,
                )
            except SensoryCapacityError:
                with result_lock:
                    rejected.append(str(index))
            else:
                with result_lock:
                    accepted.append(str(index))

        threads = [threading.Thread(target=add, args=(index,)) for index in range(30)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(accepted), 10)
        self.assertEqual(len(rejected), 20)
        self.assertEqual(buffer.stats(lease)["count"], 10)


if __name__ == "__main__":
    unittest.main()
