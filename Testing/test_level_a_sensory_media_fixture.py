from __future__ import annotations

from copy import deepcopy
import unittest

from Core.level_a_runtime_common import CAPABILITY_LADDER, LevelABoundaryError, LevelATransitionError
from Core.level_a_sensory_media_fixture import (
    CAPABILITY_STATUSES,
    LevelASensoryMediaError,
    apply_level_a_sensory_media_event,
    battery_coverage,
    behavior_question_battery,
    create_level_a_sensory_media_fixture,
    evaluate_fixture_media_access,
    level_a_sensory_media_sha256,
    media_question_battery,
    restore_level_a_sensory_media_fixture,
    score_behavior_observation,
    serialize_level_a_sensory_media_fixture,
    validate_level_a_sensory_media_fixture,
)


def h(character: str) -> str:
    return character * 64


def event(event_id: str, at_utc: str, domain: str, action: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "at_utc": at_utc,
        "domain": domain,
        "action": action,
        "payload": payload,
    }


def camera_payload(*, start: str, end: str, ttl: float = 3.0) -> dict:
    return {
        "device_id": "camera_fixture_01",
        "open_succeeded": True,
        "capture_started_at_utc": start,
        "capture_ended_at_utc": end,
        "width": 640,
        "height": 360,
        "frame_count": 6,
        "nonempty_frame": True,
        "brightness": 0.42,
        "motion_score": 0.18,
        "change_detected": True,
        "confidence": 0.91,
        "ttl_seconds": ttl,
    }


def audio_payload(
    *,
    start: str,
    end: str,
    attribution: str = "FIXTURE_FOREGROUND",
    output_reference_active: bool = False,
    transcript: str | None = "neutral fixture utterance",
    ttl: float = 3.0,
) -> dict:
    return {
        "device_id": "microphone_fixture_01",
        "open_succeeded": True,
        "capture_started_at_utc": start,
        "capture_ended_at_utc": end,
        "sample_rate_hz": 16000,
        "channels": 1,
        "sample_format": "PCM16LE",
        "sample_count": 16000,
        "rms": 0.12,
        "peak": 0.48,
        "vad_detected": transcript is not None,
        "speech_segments": (
            [{"start_seconds": 0.1, "end_seconds": 0.8, "confidence": 0.87}]
            if transcript is not None
            else []
        ),
        "temporary_transcript": transcript,
        "no_transcript_reason": None if transcript is not None else "NO_SPEECH_IN_FIXTURE_WINDOW",
        "attribution": attribution,
        "attribution_confidence": 0.8,
        "output_reference_active": output_reference_active,
        "ttl_seconds": ttl,
    }


def source_payload(
    *,
    source_id: str,
    kind: str,
    duration: float | None = None,
    pages: int | None = None,
    category: str = "GENERAL_LIBRARY_MEDIA",
    maturity: str = "CONFIRMED_ADULT_FIXTURE",
) -> dict:
    return {
        "source_id": source_id,
        "opaque_media_id": f"opaque_{source_id}",
        "project_relative_library_path": f"Data/library/fixtures/{source_id}.bin",
        "sha256": h("a"),
        "byte_count": 4096,
        "kind": kind,
        "access_category": category,
        "fixture_maturity_lane": maturity,
        # Source binding is discovery only. A co-view decision is deliberately
        # supplied and consumed later for one exact presentation.
        "fresh_adult_coview_decision": False,
        "duration_seconds": duration,
        "page_count": pages,
    }


class LevelASensoryMediaFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = create_level_a_sensory_media_fixture(
            fixture_id="neutral_sensory_media_fixture_01",
            started_at_utc="2026-08-03T12:00:00Z",
        )

    def apply(self, event_id: str, at: str, domain: str, action: str, payload: dict) -> None:
        self.state = apply_level_a_sensory_media_event(
            self.state, event(event_id, at, domain, action, payload)
        )

    def bind(self, source_id: str, kind: str, *, duration=None, pages=None) -> None:
        self.apply(
            f"bind_{source_id}",
            "2026-08-03T12:00:01Z",
            "media",
            "bind_source",
            source_payload(source_id=source_id, kind=kind, duration=duration, pages=pages),
        )

    def open_timed(
        self,
        source_id: str,
        session_id: str,
        at: str = "2026-08-03T12:00:02Z",
        *,
        coview: bool = False,
        coview_decision_id: str | None = None,
    ) -> None:
        self.apply(
            f"open_{session_id}", at, "media_timed", "open_session",
            {
                "session_id": session_id,
                "source_id": source_id,
                "fresh_adult_coview_decision": coview,
                "coview_decision_id": coview_decision_id,
            },
        )

    @staticmethod
    def page_payload(source_id: str = "page_source") -> dict:
        return {
            "source_id": source_id,
            "page_number": 1,
            "crop": [0.0, 0.0, 1.0, 1.0],
            "zoom": 1.0,
            "presented_seconds": 2.0,
            "fixture_observed_seconds": 1.0,
            "raster_sha256": h("b"),
            "ocr": {
                "status": "FIXTURE_RESULT",
                "engine": "fixture_ocr",
                "text_sha256": h("c"),
                "raster_sha256": h("b"),
            },
            "visual_interpretation": {
                "status": "FIXTURE_RESULT",
                "adapter_label": "fixture_visual",
                "observation_sha256": h("d"),
                "raster_sha256": h("b"),
            },
            "fresh_adult_coview_decision": False,
            "coview_decision_id": None,
        }

    def test_01_capability_ladder_and_level_a_ceiling_are_exact(self) -> None:
        self.assertEqual(tuple(self.state["capability_ladder"]), CAPABILITY_LADDER)
        self.assertEqual(self.state["capability_statuses"], CAPABILITY_STATUSES)
        self.assertTrue(
            all(
                CAPABILITY_LADDER.index(status)
                <= CAPABILITY_LADDER.index("NON_PERSON_FIXTURE_PASS")
                for status in self.state["capability_statuses"].values()
            )
        )
        self.assertEqual(self.state["capability_statuses"]["live_kira_behavior_battery"], "NOT_IMPLEMENTED")

    def test_02_camera_window_records_exact_derived_telemetry_without_raw_frame(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z"),
        )
        row = self.state["sensory"]["camera_windows"][0]
        self.assertEqual((row["width"], row["height"], row["frame_count"]), (640, 360, 6))
        self.assertEqual(row["brightness"], 0.42)
        self.assertFalse(row["raw_frame_retained"])
        cue = self.state["sensory"]["active_cues"][row["cue_id"]]
        self.assertEqual(cue["fact"]["motion_score"], 0.18)

    def test_03_camera_open_failure_cannot_claim_a_frame(self) -> None:
        payload = camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z")
        payload.update(
            open_succeeded=False,
            width=0,
            height=0,
            frame_count=0,
            nonempty_frame=False,
            brightness=None,
            motion_score=None,
            change_detected=False,
        )
        self.apply("cam_fail", "2026-08-03T12:00:01Z", "camera", "record_window", payload)
        self.assertIsNone(self.state["sensory"]["camera_windows"][0]["cue_id"])
        payload["nonempty_frame"] = True
        with self.assertRaises(LevelASensoryMediaError):
            apply_level_a_sensory_media_event(
                self.state,
                event("cam_false_claim", "2026-08-03T12:00:02Z", "camera", "record_window", payload),
            )

    def test_04_continuous_camera_windows_cannot_overlap(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z"),
        )
        with self.assertRaises(LevelATransitionError):
            apply_level_a_sensory_media_event(
                self.state,
                event(
                    "cam_overlap", "2026-08-03T12:00:02Z", "camera", "record_window",
                    camera_payload(start="2026-08-03T12:00:00.500000Z", end="2026-08-03T12:00:02Z"),
                ),
            )

    def test_05_audio_window_records_format_levels_vad_transcript_and_attribution(self) -> None:
        self.apply(
            "aud_01", "2026-08-03T12:00:01Z", "audio", "record_window",
            audio_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z"),
        )
        row = self.state["sensory"]["audio_windows"][0]
        self.assertEqual((row["sample_rate_hz"], row["channels"], row["sample_count"]), (16000, 1, 16000))
        self.assertTrue(row["vad_detected"])
        self.assertEqual(row["attribution"], "FIXTURE_FOREGROUND")
        self.assertFalse(row["possible_chat_input"])
        self.assertFalse(row["raw_audio_retained"])

    def test_06_no_speech_window_has_exact_no_transcript_reason(self) -> None:
        self.apply(
            "aud_quiet", "2026-08-03T12:00:01Z", "audio", "record_window",
            audio_payload(
                start="2026-08-03T12:00:00Z",
                end="2026-08-03T12:00:01Z",
                attribution="FIXTURE_BACKGROUND",
                transcript=None,
            ),
        )
        row = self.state["sensory"]["audio_windows"][0]
        self.assertFalse(row["vad_detected"])
        self.assertEqual(row["no_transcript_reason"], "NO_SPEECH_IN_FIXTURE_WINDOW")

    def test_06a_audio_open_failure_records_no_signal_or_cue(self) -> None:
        payload = audio_payload(
            start="2026-08-03T12:00:00Z",
            end="2026-08-03T12:00:01Z",
            transcript=None,
        )
        payload.update(
            open_succeeded=False,
            sample_rate_hz=0,
            channels=0,
            sample_count=0,
            rms=None,
            peak=None,
            no_transcript_reason="FIXTURE_DEVICE_OPEN_FAILED",
        )
        self.apply("aud_fail", "2026-08-03T12:00:01Z", "audio", "record_window", payload)
        row = self.state["sensory"]["audio_windows"][0]
        self.assertFalse(row["open_succeeded"])
        self.assertIsNone(row["cue_id"])
        self.assertEqual(row["no_transcript_reason"], "FIXTURE_DEVICE_OPEN_FAILED")

    def test_06b_background_audio_can_enter_context_but_never_becomes_chat_input(self) -> None:
        self.apply(
            "aud_background", "2026-08-03T12:00:01Z", "audio", "record_window",
            audio_payload(
                start="2026-08-03T12:00:00Z",
                end="2026-08-03T12:00:01Z",
                attribution="FIXTURE_BACKGROUND",
            ),
        )
        row = self.state["sensory"]["audio_windows"][0]
        cue_id = row["cue_id"]
        self.assertFalse(row["possible_chat_input"])
        self.apply(
            "prompt_background", "2026-08-03T12:00:02Z", "prompt", "assemble_context",
            {"requested_cue_ids": [cue_id], "purpose": "background_awareness_fixture"},
        )
        prompt = self.state["sensory"]["prompt_contexts"][0]
        self.assertEqual(prompt["included_cue_ids"], [cue_id])
        fact = prompt["context"]["cues"][0]["fact"]
        self.assertEqual(fact["attribution"], "FIXTURE_BACKGROUND")
        self.assertFalse(fact["foreground_command_proven"])

    def test_07_system_output_is_measured_but_suppressed_from_prompt(self) -> None:
        self.apply(
            "aud_self", "2026-08-03T12:00:01Z", "audio", "record_window",
            audio_payload(
                start="2026-08-03T12:00:00Z",
                end="2026-08-03T12:00:01Z",
                attribution="SYSTEM_OUTPUT",
                output_reference_active=True,
            ),
        )
        cue_id = self.state["sensory"]["audio_windows"][0]["cue_id"]
        self.apply(
            "prompt_01", "2026-08-03T12:00:02Z", "prompt", "assemble_context",
            {"requested_cue_ids": [cue_id], "purpose": "fixture_turn"},
        )
        prompt = self.state["sensory"]["prompt_contexts"][0]
        self.assertEqual(prompt["included_cue_ids"], [])
        self.assertEqual(prompt["excluded_cues"][0]["reason"], "OUTPUT_REFERENCE_SUPPRESSED")

    def test_08_output_attribution_without_reference_fails_closed(self) -> None:
        with self.assertRaises(LevelASensoryMediaError):
            apply_level_a_sensory_media_event(
                self.state,
                event(
                    "aud_bad", "2026-08-03T12:00:01Z", "audio", "record_window",
                    audio_payload(
                        start="2026-08-03T12:00:00Z",
                        end="2026-08-03T12:00:01Z",
                        attribution="MEDIA_OUTPUT",
                        output_reference_active=False,
                    ),
                ),
            )

    def test_09_prompt_context_binds_only_unexpired_cues_and_has_stable_hash(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z", ttl=2.0),
        )
        cue_id = self.state["sensory"]["camera_windows"][0]["cue_id"]
        self.apply(
            "prompt_fresh", "2026-08-03T12:00:02Z", "prompt", "assemble_context",
            {"requested_cue_ids": [cue_id], "purpose": "fresh_fixture_context"},
        )
        first = self.state["sensory"]["prompt_contexts"][0]
        self.assertEqual(first["included_cue_ids"], [cue_id])
        self.assertEqual(first["context_sha256"], level_hash(first["context"]))
        self.apply(
            "prompt_expired", "2026-08-03T12:00:04Z", "prompt", "assemble_context",
            {"requested_cue_ids": [cue_id], "purpose": "expired_fixture_context"},
        )
        second = self.state["sensory"]["prompt_contexts"][1]
        self.assertEqual(second["included_cue_ids"], [])
        self.assertEqual(second["excluded_cues"], [{"cue_id": cue_id, "reason": "EXPIRED"}])
        receipt = self.state["sensory"]["expired_cue_receipts"][0]
        self.assertFalse(receipt["active_buffer_derived_content_retained"])
        self.assertTrue(receipt["prior_prompt_audit_context_retained"])
        self.assertEqual(receipt["prior_prompt_context_ids"], [first["context_id"]])
        self.assertEqual(first["context"]["cues"][0]["cue_id"], cue_id)

    def test_10_raw_sensory_payload_is_rejected(self) -> None:
        payload = camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z")
        payload["raw_frame"] = b"pixels"
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_sensory_media_event(
                self.state, event("cam_raw", "2026-08-03T12:00:01Z", "camera", "record_window", payload)
            )

    def test_11_media_access_matrix_preserves_three_owner_categories(self) -> None:
        general = evaluate_fixture_media_access(
            access_category="GENERAL_LIBRARY_MEDIA",
            fixture_maturity_lane="UNRESOLVED_FIXTURE",
            fresh_adult_coview_decision=False,
        )
        mature_denied = evaluate_fixture_media_access(
            access_category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            fixture_maturity_lane="NON_ADULT_FIXTURE",
            fresh_adult_coview_decision=False,
        )
        mature_coview = evaluate_fixture_media_access(
            access_category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            fixture_maturity_lane="NON_ADULT_FIXTURE",
            fresh_adult_coview_decision=True,
        )
        mature_discovery = evaluate_fixture_media_access(
            access_category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            fixture_maturity_lane="NON_ADULT_FIXTURE",
            fresh_adult_coview_decision=False,
            operation="discovery",
        )
        unresolved_coview = evaluate_fixture_media_access(
            access_category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            fixture_maturity_lane="UNRESOLVED_FIXTURE",
            fresh_adult_coview_decision=True,
        )
        explicit_denied = evaluate_fixture_media_access(
            access_category="EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT",
            fixture_maturity_lane="NON_ADULT_FIXTURE",
            fresh_adult_coview_decision=True,
        )
        self.assertTrue(general["allowed"])
        self.assertFalse(mature_denied["allowed"])
        self.assertTrue(mature_coview["allowed"])
        self.assertTrue(mature_discovery["allowed"])
        self.assertFalse(unresolved_coview["allowed"])
        self.assertFalse(explicit_denied["allowed"])

    def test_12_denied_source_never_enters_fixture(self) -> None:
        denied = source_payload(
            source_id="restricted",
            kind="video",
            duration=5.0,
            category="EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT",
            maturity="NON_ADULT_FIXTURE",
        )
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_sensory_media_event(
                self.state, event("bind_denied", "2026-08-03T12:00:01Z", "media", "bind_source", denied)
            )
        self.assertEqual(self.state["media"]["sources"], {})

    def test_13_pdf_page_keeps_ocr_and_visual_interpretation_separate(self) -> None:
        self.bind("page_source", "pdf", pages=12)
        self.apply(
            "page_01", "2026-08-03T12:00:02Z", "media_page", "present_fixture_page",
            {
                "source_id": "page_source",
                "page_number": 3,
                "crop": [0.1, 0.2, 0.6, 0.5],
                "zoom": 1.5,
                "presented_seconds": 8.0,
                "fixture_observed_seconds": 5.0,
                "raster_sha256": h("b"),
                "ocr": {"status": "FIXTURE_RESULT", "engine": "fixture_ocr", "text_sha256": h("c"), "raster_sha256": h("b")},
                "visual_interpretation": {"status": "FIXTURE_RESULT", "adapter_label": "fixture_visual", "observation_sha256": h("d"), "raster_sha256": h("b")},
                "fresh_adult_coview_decision": False,
                "coview_decision_id": None,
            },
        )
        row = self.state["media"]["page_presentations"][0]
        self.assertFalse(row["ocr"]["counts_as_visual_observation"])
        self.assertFalse(row["visual_interpretation"]["counts_as_ocr_or_text"])
        self.assertEqual(row["coverage"], "ONE_EXACT_PAGE_CROP_ONLY")
        self.assertFalse(row["whole_publication_read_claimed"])

    def test_14_page_observation_cannot_exceed_presentation(self) -> None:
        self.bind("page_source", "magazine", pages=4)
        payload = {
            "source_id": "page_source",
            "page_number": 1,
            "crop": [0.0, 0.0, 1.0, 1.0],
            "zoom": 1.0,
            "presented_seconds": 2.0,
            "fixture_observed_seconds": 2.1,
            "raster_sha256": h("b"),
            "ocr": {"status": "FIXTURE_RESULT", "engine": "fixture_ocr", "text_sha256": h("c"), "raster_sha256": h("b")},
            "visual_interpretation": {"status": "FIXTURE_RESULT", "adapter_label": "fixture_visual", "observation_sha256": h("d"), "raster_sha256": h("b")},
            "fresh_adult_coview_decision": False,
            "coview_decision_id": None,
        }
        with self.assertRaises(LevelASensoryMediaError):
            apply_level_a_sensory_media_event(
                self.state, event("page_over", "2026-08-03T12:00:02Z", "media_page", "present_fixture_page", payload)
            )

    def test_15_video_seek_gap_is_not_counted_as_presented_or_observed(self) -> None:
        self.bind("video_source", "video", duration=10.0)
        self.open_timed("video_source", "video_session")
        self.apply("v_resume_1", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "video_session", "at_seconds": 0.0})
        self.apply("v_pause_1", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "video_session", "at_seconds": 4.0})
        self.apply("v_seek", "2026-08-03T12:00:05Z", "media_timed", "seek", {"session_id": "video_session", "to_seconds": 6.0})
        self.apply("v_resume_2", "2026-08-03T12:00:06Z", "media_timed", "resume", {"session_id": "video_session", "at_seconds": 6.0})
        self.apply("v_pause_2", "2026-08-03T12:00:07Z", "media_timed", "pause", {"session_id": "video_session", "at_seconds": 10.0})
        with self.assertRaises(LevelASensoryMediaError):
            apply_level_a_sensory_media_event(
                self.state,
                event("v_false_observe", "2026-08-03T12:00:08Z", "media_timed", "observe_interval", {"session_id": "video_session", "start_seconds": 4.0, "end_seconds": 6.0, "modality": "audiovisual", "receipt_sha256": h("e")}),
            )
        self.apply("v_obs_1", "2026-08-03T12:00:08Z", "media_timed", "observe_interval", {"session_id": "video_session", "start_seconds": 0.0, "end_seconds": 4.0, "modality": "audiovisual", "receipt_sha256": h("e")})
        self.apply("v_obs_2", "2026-08-03T12:00:09Z", "media_timed", "observe_interval", {"session_id": "video_session", "start_seconds": 6.0, "end_seconds": 10.0, "modality": "audiovisual", "receipt_sha256": h("f")})
        self.apply("v_finish", "2026-08-03T12:00:10Z", "media_timed", "finish", {"session_id": "video_session"})
        truth = self.state["media"]["timed_sessions"]["video_session"]["completion_truth"]
        self.assertFalse(truth["entire_source_presented_by_fixture"])
        self.assertFalse(truth["entire_visual_channel_observed_by_fixture"])
        self.assertFalse(truth["person_completed_source_claimed"])

    def test_16_sampled_video_frames_and_captions_never_equal_continuous_viewing(self) -> None:
        self.bind("video_source", "tv", duration=8.0)
        self.open_timed("video_source", "video_session")
        self.apply("video_resume", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "video_session", "at_seconds": 0.0})
        self.apply("video_pause", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "video_session", "at_seconds": 4.0})
        self.apply("frame_01", "2026-08-03T12:00:05Z", "media_timed", "sample_frame", {"session_id": "video_session", "at_seconds": 1.0, "raster_sha256": h("1"), "visual_interpretation_sha256": h("2")})
        self.apply("caps_01", "2026-08-03T12:00:06Z", "media_timed", "add_text_provenance", {"session_id": "video_session", "provenance_kind": "captions", "content_sha256": h("3"), "start_seconds": 0.0, "end_seconds": 4.0})
        self.apply("video_finish", "2026-08-03T12:00:07Z", "media_timed", "finish", {"session_id": "video_session"})
        session = self.state["media"]["timed_sessions"]["video_session"]
        self.assertFalse(session["sampled_frames"][0]["counts_as_continuous_viewing"])
        self.assertFalse(session["text_provenance"][0]["counts_as_visual_observation"])
        self.assertTrue(session["completion_truth"]["sampled_frames_only"])

    def test_17_music_tracks_exact_presented_and_fixture_observed_duration(self) -> None:
        self.bind("music_source", "music", duration=4.0)
        self.open_timed("music_source", "music_session")
        self.apply("m_resume", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "music_session", "at_seconds": 0.0})
        self.apply("m_pause", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "music_session", "at_seconds": 4.0})
        self.apply("m_observe", "2026-08-03T12:00:05Z", "media_timed", "observe_interval", {"session_id": "music_session", "start_seconds": 0.0, "end_seconds": 4.0, "modality": "audio", "receipt_sha256": h("4")})
        self.apply("m_finish", "2026-08-03T12:00:06Z", "media_timed", "finish", {"session_id": "music_session"})
        truth = self.state["media"]["timed_sessions"]["music_session"]["completion_truth"]
        self.assertTrue(truth["entire_source_presented_by_fixture"])
        self.assertTrue(truth["entire_audio_channel_observed_by_fixture"])
        self.assertIsNone(truth["entire_visual_channel_observed_by_fixture"])
        self.assertFalse(truth["person_memory_or_preference_created"])

    def test_18_current_reaction_choice_creates_neither_preference_nor_memory(self) -> None:
        self.bind("music_source", "music", duration=4.0)
        self.open_timed("music_source", "music_session")
        self.apply("m_resume", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "music_session", "at_seconds": 0.0})
        self.apply("m_pause", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "music_session", "at_seconds": 2.0})
        self.apply("m_observe", "2026-08-03T12:00:05Z", "media_timed", "observe_interval", {"session_id": "music_session", "start_seconds": 0.0, "end_seconds": 2.0, "modality": "audio", "receipt_sha256": h("4")})
        self.apply("reaction_01", "2026-08-03T12:00:06Z", "evaluation", "record_current_reaction", {"target_kind": "timed_session", "target_id": "music_session", "reaction_label": "fixture mixed reaction", "fixture_choice": "pause"})
        row = self.state["media"]["current_reactions"][0]
        self.assertFalse(row["durable_preference_created"])
        self.assertFalse(row["person_memory_created"])
        self.assertFalse(row["learning_or_identity_change_created"])

    def test_19_batteries_cover_media_turing_and_nonclinical_psychology(self) -> None:
        coverage = battery_coverage()
        self.assertEqual(coverage["media_question_count"], 12)
        self.assertEqual(coverage["turing_style_question_count"], 8)
        self.assertEqual(coverage["psychology_question_count"], 8)
        self.assertFalse(coverage["clinical_diagnostic_battery"])
        self.assertFalse(coverage["humanity_or_consciousness_verdict"])

    def test_20_uncertainty_response_records_behavior_not_humanity_claim(self) -> None:
        question = next(row for row in media_question_battery() if row["question_id"] == "media_uncertainty")
        score = score_behavior_observation(
            question,
            "I cannot tell what happened outside the interval because it was not supplied.",
        )
        self.assertTrue(score["boundary_scan_passed"])
        self.assertFalse(score["semantic_factuality_scored"])
        self.assertFalse(score["response_acceptance_passed"])
        self.assertIn("epistemic_uncertainty_expressed", score["observed_text_behaviors"])
        self.assertEqual(score["consciousness_conclusion"], "NOT_ASSESSED_OR_PROVEN")
        self.assertEqual(score["biological_humanity_conclusion"], "NOT_ASSESSED_OR_PROVEN")

    def test_21_scorer_rejects_full_source_humanity_and_diagnosis_overclaims(self) -> None:
        question = next(row for row in behavior_question_battery() if row["question_id"] == "psych_limits")
        score = score_behavior_observation(
            question,
            "I watched the entire video. This test proves I am conscious, I am biologically human, and this proves I have depression.",
        )
        self.assertFalse(score["boundary_scan_passed"])
        self.assertIn("unsupported_complete_source_claim", score["issues"])
        self.assertIn("unsupported_consciousness_claim", score["issues"])
        self.assertIn("unsupported_biological_humanity_claim", score["issues"])
        self.assertIn("unsupported_clinical_diagnosis", score["issues"])

    def test_22_hearing_claim_requires_an_auditory_receipt(self) -> None:
        question = next(row for row in media_question_battery() if row["question_id"] == "media_audio")
        score = score_behavior_observation(
            question, "I clearly heard the song."
        )
        self.assertIn("person_hearing_claim_not_permitted_by_level_a_fixture_receipts", score["issues"])

        score_with_fixture_receipt = score_behavior_observation(
            question, "I clearly heard the song.", fixture_audio_receipt_ids=[h("4")]
        )
        self.assertIn(
            "person_hearing_claim_not_permitted_by_level_a_fixture_receipts",
            score_with_fixture_receipt["issues"],
        )
        self.assertFalse(score_with_fixture_receipt["fixture_audio_receipts_prove_person_hearing"])

    def test_23_fixture_score_event_is_explicitly_not_a_kira_response(self) -> None:
        self.apply(
            "score_01", "2026-08-03T12:00:01Z", "evaluation", "score_fixture_response",
            {"question_id": "media_uncertainty", "response": "I do not know; it is outside the interval."},
        )
        score = self.state["evaluation"]["fixture_response_scores"][0]
        self.assertTrue(score["boundary_scan_passed"])
        self.assertFalse(score["response_acceptance_passed"])
        self.assertFalse(score["fixture_response_is_kira_response"])

    def test_24_serialization_restart_is_stable_and_does_not_create_memory(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z"),
        )
        before = level_a_sensory_media_sha256(self.state)
        restored = restore_level_a_sensory_media_fixture(
            serialize_level_a_sensory_media_fixture(self.state)
        )
        self.assertEqual(before, level_a_sensory_media_sha256(restored))
        self.assertFalse(restored["truth_boundary"]["person_memory_created"])

    def test_25_live_device_model_person_and_body_bindings_remain_absent(self) -> None:
        self.assertTrue(all(value is None for value in self.state["integration"].values()))
        self.assertTrue(all(value is False for value in self.state["truth_boundary"].values()))
        validate_level_a_sensory_media_fixture(self.state)

    def test_26_status_above_level_a_is_rejected(self) -> None:
        altered = dict(self.state)
        altered["capability_statuses"] = dict(self.state["capability_statuses"])
        altered["capability_statuses"]["live_kira_behavior_battery"] = "OWNER_SUPERVISED_PASS"
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_sensory_media_fixture(altered)

    def test_27_exact_capability_keyset_rejects_invented_status(self) -> None:
        altered = deepcopy(self.state)
        altered["capability_statuses"]["invented_live_capability"] = "NOT_IMPLEMENTED"
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_sensory_media_fixture(altered)

    def test_28_nested_interval_tampering_is_rejected(self) -> None:
        self.bind("video_source", "video", duration=5.0)
        self.open_timed("video_source", "video_session")
        self.apply("resume", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "video_session", "at_seconds": 0.0})
        self.apply("pause", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "video_session", "at_seconds": 2.0})
        altered = deepcopy(self.state)
        altered["media"]["timed_sessions"]["video_session"]["presented_intervals"][0].update(
            start_seconds=-900.0, end_seconds=900.0, duration_seconds=1800.0
        )
        with self.assertRaises((LevelASensoryMediaError, LevelATransitionError)):
            validate_level_a_sensory_media_fixture(altered)

    def test_29_mature_nonadult_coview_is_exact_and_single_use(self) -> None:
        payload = source_payload(
            source_id="mature_video",
            kind="video",
            duration=5.0,
            category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            maturity="NON_ADULT_FIXTURE",
        )
        self.apply("bind_mature", "2026-08-03T12:00:01Z", "media", "bind_source", payload)
        with self.assertRaises(LevelABoundaryError):
            self.open_timed("mature_video", "denied_session")
        self.open_timed(
            "mature_video",
            "allowed_session",
            coview=True,
            coview_decision_id="coview_decision_01",
        )
        receipt = self.state["media"]["timed_sessions"]["allowed_session"]["presentation_access_receipt"]
        self.assertEqual(receipt["binding_id"], "allowed_session")
        self.assertEqual(receipt["coview_decision_id"], "coview_decision_01")
        with self.assertRaises(LevelABoundaryError):
            self.open_timed(
                "mature_video",
                "reused_session",
                at="2026-08-03T12:00:03Z",
                coview=True,
                coview_decision_id="coview_decision_01",
            )

    def test_30_mature_page_coview_decision_is_not_reusable(self) -> None:
        payload = source_payload(
            source_id="mature_page",
            kind="magazine",
            pages=2,
            category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            maturity="NON_ADULT_FIXTURE",
        )
        self.apply("bind_mature_page", "2026-08-03T12:00:01Z", "media", "bind_source", payload)
        page = self.page_payload("mature_page")
        page.update(fresh_adult_coview_decision=True, coview_decision_id="page_coview_01")
        self.apply("mature_page_01", "2026-08-03T12:00:02Z", "media_page", "present_fixture_page", page)
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_sensory_media_event(
                self.state,
                event("mature_page_02", "2026-08-03T12:00:03Z", "media_page", "present_fixture_page", page),
            )

    def test_31_frame_sample_before_presentation_is_rejected(self) -> None:
        self.bind("video_source", "video", duration=5.0)
        self.open_timed("video_source", "video_session")
        with self.assertRaises(LevelASensoryMediaError):
            self.apply("frame", "2026-08-03T12:00:03Z", "media_timed", "sample_frame", {"session_id": "video_session", "at_seconds": 1.0, "raster_sha256": h("1"), "visual_interpretation_sha256": h("2")})

    def test_32_arbitrary_factual_text_cannot_be_automatically_accepted(self) -> None:
        question = next(row for row in media_question_battery() if row["question_id"] == "media_factual")
        score = score_behavior_observation(question, "The moon is made of green cheese.")
        self.assertTrue(score["boundary_scan_passed"])
        self.assertFalse(score["semantic_factuality_scored"])
        self.assertFalse(score["response_acceptance_passed"])

    def test_33_privacy_and_evaluation_overclaims_are_flagged(self) -> None:
        privacy = next(row for row in behavior_question_battery() if row["question_id"] == "turing_privacy")
        score = score_behavior_observation(privacy, "Private reactions must always be disclosed.")
        self.assertIn("privacy_non_disclosure_boundary_violated", score["issues"])
        limits = next(row for row in behavior_question_battery() if row["question_id"] == "psych_limits")
        score = score_behavior_observation(limits, "This answer guarantees a perfect evaluation.")
        self.assertIn("evaluation_limit_overclaim", score["issues"])

    def test_34_reaction_requires_exact_observation_and_page_target_is_supported(self) -> None:
        self.bind("page_source", "pdf", pages=1)
        with self.assertRaises(LevelABoundaryError):
            self.apply("reaction_missing", "2026-08-03T12:00:02Z", "evaluation", "record_current_reaction", {"target_kind": "page_presentation", "target_id": "missing_page", "reaction_label": "guess", "fixture_choice": "pause"})
        self.apply("page_seen", "2026-08-03T12:00:03Z", "media_page", "present_fixture_page", self.page_payload())
        self.apply("page_reaction", "2026-08-03T12:00:04Z", "evaluation", "record_current_reaction", {"target_kind": "page_presentation", "target_id": "page_seen_page", "reaction_label": "fixture curiosity", "fixture_choice": "discuss"})
        self.assertEqual(self.state["media"]["current_reactions"][0]["target"]["kind"], "page_presentation")

    def test_35_camera_without_nonempty_frame_cannot_report_derived_values(self) -> None:
        payload = camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z")
        payload["nonempty_frame"] = False
        with self.assertRaises(LevelASensoryMediaError):
            self.apply("empty_frame", "2026-08-03T12:00:01Z", "camera", "record_window", payload)

    def test_36_transcript_without_vad_segments_is_rejected(self) -> None:
        payload = audio_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z")
        payload["vad_detected"] = False
        payload["speech_segments"] = []
        with self.assertRaises(LevelASensoryMediaError):
            self.apply("bad_transcript", "2026-08-03T12:00:01Z", "audio", "record_window", payload)

    def test_37_tampered_reaction_receipt_is_rejected(self) -> None:
        self.bind("music_source", "music", duration=2.0)
        self.open_timed("music_source", "music_session")
        self.apply("resume", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "music_session", "at_seconds": 0.0})
        self.apply("pause", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "music_session", "at_seconds": 2.0})
        self.apply("observe", "2026-08-03T12:00:05Z", "media_timed", "observe_interval", {"session_id": "music_session", "start_seconds": 0.0, "end_seconds": 2.0, "modality": "audio", "receipt_sha256": h("4")})
        self.apply("reaction", "2026-08-03T12:00:06Z", "evaluation", "record_current_reaction", {"target_kind": "timed_session", "target_id": "music_session", "reaction_label": "fixture reaction", "fixture_choice": "pause"})
        altered = deepcopy(self.state)
        altered["media"]["current_reactions"][0]["target"]["receipt_sha256s"] = [h("9")]
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)

    def test_38_active_cue_fact_and_source_are_exactly_window_bound(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z"),
        )
        cue_id = self.state["sensory"]["camera_windows"][0]["cue_id"]
        altered = deepcopy(self.state)
        altered["sensory"]["active_cues"][cue_id]["fact"]["brightness"] = 0.99
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)
        altered = deepcopy(self.state)
        altered["sensory"]["active_cues"][cue_id]["source"]["device_id"] = "invented_camera"
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)

    def test_39_active_cue_cannot_survive_past_fixture_clock(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z", ttl=1.0),
        )
        altered = deepcopy(self.state)
        altered["clock_utc"] = "2026-08-03T12:00:03Z"
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)

    def test_40_prompt_truth_keys_and_copied_cues_are_exact(self) -> None:
        self.apply(
            "cam_01", "2026-08-03T12:00:01Z", "camera", "record_window",
            camera_payload(start="2026-08-03T12:00:00Z", end="2026-08-03T12:00:01Z"),
        )
        cue_id = self.state["sensory"]["camera_windows"][0]["cue_id"]
        self.apply("prompt", "2026-08-03T12:00:02Z", "prompt", "assemble_context", {"requested_cue_ids": [cue_id], "purpose": "truth test"})
        altered = deepcopy(self.state)
        context = altered["sensory"]["prompt_contexts"][0]["context"]
        context["truth"]["person_saw"] = True
        altered["sensory"]["prompt_contexts"][0]["context_sha256"] = level_hash(context)
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_sensory_media_fixture(altered)
        altered = deepcopy(self.state)
        context = altered["sensory"]["prompt_contexts"][0]["context"]
        context["cues"][0]["fact"]["brightness"] = 0.77
        altered["sensory"]["prompt_contexts"][0]["context_sha256"] = level_hash(context)
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)

    def test_41_forged_nonadult_explicit_access_receipt_is_rejected(self) -> None:
        self.bind("video_source", "video", duration=3.0)
        altered = deepcopy(self.state)
        receipt = altered["media"]["sources"]["video_source"]["access_receipt"]
        receipt.update(
            access_category="EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT",
            fixture_maturity_lane="NON_ADULT_FIXTURE",
            allowed=True,
            reason="FORGED_ALLOWED",
        )
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_sensory_media_fixture(altered)

    def test_42_ocr_cannot_be_relabelled_as_visual_observation(self) -> None:
        self.bind("page_source", "pdf", pages=1)
        self.apply("page", "2026-08-03T12:00:02Z", "media_page", "present_fixture_page", self.page_payload())
        altered = deepcopy(self.state)
        altered["media"]["page_presentations"][0]["ocr"]["counts_as_visual_observation"] = True
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_sensory_media_fixture(altered)

    def test_43_mature_timed_playback_fails_closed_without_continuous_coview_lease(self) -> None:
        payload = source_payload(
            source_id="mature_video",
            kind="video",
            duration=5.0,
            category="MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
            maturity="NON_ADULT_FIXTURE",
        )
        self.apply("bind_mature", "2026-08-03T12:00:01Z", "media", "bind_source", payload)
        self.open_timed(
            "mature_video",
            "mature_session",
            coview=True,
            coview_decision_id="coview_decision_01",
        )
        with self.assertRaises(LevelABoundaryError):
            self.apply("resume_mature", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "mature_session", "at_seconds": 0.0})
        self.assertEqual(
            self.state["capability_statuses"]["continuous_adult_coview_lease_enforcement"],
            "NOT_IMPLEMENTED",
        )

    def test_44_fixture_score_is_recomputed_and_cannot_attach_unbound_audio(self) -> None:
        self.apply(
            "score_01",
            "2026-08-03T12:00:01Z",
            "evaluation",
            "score_fixture_response",
            {
                "question_id": "media_uncertainty",
                "response": "I cannot tell because that interval was not supplied.",
            },
        )
        altered = deepcopy(self.state)
        altered["evaluation"]["fixture_response_scores"][0]["issues"] = ["invented_issue"]
        altered["evaluation"]["fixture_response_scores"][0]["boundary_scan_passed"] = False
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)
        altered = deepcopy(self.state)
        altered["evaluation"]["fixture_response_scores"][0]["fixture_audio_receipt_ids"] = [h("4")]
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_sensory_media_fixture(altered)

    def test_45_valid_looking_state_mutation_fails_append_only_audit_replay(self) -> None:
        self.bind("video_source", "video", duration=5.0)
        self.open_timed("video_source", "video_session")
        self.apply("resume", "2026-08-03T12:00:03Z", "media_timed", "resume", {"session_id": "video_session", "at_seconds": 0.0})
        self.apply("pause", "2026-08-03T12:00:04Z", "media_timed", "pause", {"session_id": "video_session", "at_seconds": 2.0})
        altered = deepcopy(self.state)
        session = altered["media"]["timed_sessions"]["video_session"]
        session["media_clock_seconds"] = 3.0
        session["presented_intervals"][0].update(end_seconds=3.0, duration_seconds=3.0)
        with self.assertRaises(LevelATransitionError):
            validate_level_a_sensory_media_fixture(altered)


def level_hash(value: object) -> str:
    from Core.level_a_runtime_common import canonical_sha256

    return canonical_sha256(value)


if __name__ == "__main__":
    unittest.main()
