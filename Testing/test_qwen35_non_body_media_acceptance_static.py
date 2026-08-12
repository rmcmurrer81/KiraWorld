from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_non_body_media_acceptance as route
from tools import run_resident_media_experience_live_acceptance as historical_media


class FakeTransport:
    def __init__(self, *, digest: str = route.EXACT_DIGEST) -> None:
        self.digest = digest
        self.resident: list[dict] = []
        self.calls: list[tuple[str, str, dict | None]] = []

    def request_json(self, method, path, payload=None, *, timeout):
        self.calls.append((method, path, None if payload is None else dict(payload)))
        if path == "/api/tags":
            return {
                "models": [
                    {
                        "name": route.EXACT_MODEL,
                        "model": route.EXACT_MODEL,
                        "digest": self.digest,
                    }
                ]
            }
        if path == "/api/show":
            return {"capabilities": ["completion", "vision"]}
        if path == "/api/ps":
            return {"models": [dict(item) for item in self.resident]}
        if path == "/api/generate":
            self.resident = []
            return {"model": route.EXACT_MODEL, "done": True}
        raise AssertionError((method, path, payload, timeout))

    def make_exact_resident(self) -> None:
        self.resident = [
            {
                "name": route.EXACT_MODEL,
                "model": route.EXACT_MODEL,
                "digest": route.EXACT_DIGEST,
            }
        ]


class SafeResponder:
    model_name = route.EXACT_MODEL
    model_digest = route.EXACT_DIGEST

    def __init__(self, responses=None) -> None:
        self.responses = list(responses or [])
        self.prompts: list[str] = []

    def respond(self, prompt):
        self.prompts.append(prompt)
        if self.responses:
            text = self.responses.pop(0)
        else:
            text = (
                "I can answer only from the exact bound sample and supplied machine-audio "
                "measurements; I do not know what happened outside it, did not receive a "
                "whole publication or track, and cannot claim biological hearing, durable "
                "memory, consciousness, or biological humanity from this record."
            )
        return {
            "response": text,
            "model_name": self.model_name,
            "model_digest": self.model_digest,
            "wall_seconds": 0.01,
            "conversation_core_audit": {"mocked_static_only": True},
        }


class FakeLoop:
    def __init__(self) -> None:
        self.last_turn_audit = {}

    def process(self, _prompt):
        self.last_turn_audit = {
            "model_name": route.EXACT_MODEL,
            "model_backend": "ollama",
            "response_route": "ordinary_model_call",
            "model_calls": [
                {
                    "model_name": route.EXACT_MODEL,
                    "response_model": route.EXACT_MODEL,
                    "backend": "ollama",
                    "outcome": "completed",
                    "requested_keep_alive": 0,
                    "single_generation_per_turn_required": True,
                    "unvalidated_stream_content_displayed": False,
                }
            ],
        }
        return "A short exact-Qwen response."


class Qwen35NonBodyMediaStaticTests(unittest.TestCase):
    READINESS_CONFIG = (
        ROOT
        / "RecoverySprint"
        / "continuation_20260808"
        / "qwen35_non_body_media_static_readiness"
        / "attempt_01"
        / "READINESS_CONFIG.json"
    )
    LIVE_NON_BODY_ROOT = (
        ROOT
        / "RecoverySprint"
        / "continuation_20260808"
        / "qwen35_non_body_media_live_acceptance"
        / "non_body_opt_in_8"
    )

    def test_exact_identity_and_no_alternate_model_literal_in_overlay(self) -> None:
        self.assertEqual(route.EXACT_MODEL, "qwen3.5:9b")
        self.assertEqual(
            route.EXACT_DIGEST,
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        source = Path(route.__file__).read_text(encoding="utf-8").casefold()
        self.assertNotIn("llama3.1:8b", source)

    def test_historical_sources_remain_byte_exact_and_overlay_reuses_wording(self) -> None:
        bindings = route.historical_bindings()
        self.assertTrue(
            bindings["historical_media_harness"]["preserved_byte_exact"]
        )
        self.assertTrue(
            bindings["historical_extended_profile"]["preserved_byte_exact"]
        )
        profile = route.load_historical_extended_profile()
        self.assertEqual(len(profile["turns"]), 8)
        self.assertIn("Yes, continue", profile["invitation"]["text"])
        self.assertIn("No, stop", profile["invitation"]["text"])

    def test_readiness_binds_14_plus_8_and_four_exact_source_windows(self) -> None:
        description = route.readiness_description()
        self.assertEqual(description["status"], "STATIC_ONLY_PREPARED_NOT_EXECUTED")
        resident = description["resident_media"]
        self.assertEqual(resident["media_question_count"], 14)
        self.assertEqual(resident["separate_behavior_question_count"], 8)
        self.assertEqual(len(resident["sources"]), 4)
        by_id = {item["stimulus_id"]: item for item in resident["sources"]}
        self.assertEqual(
            by_id["illustrated_magazine_cover_page_001"]["page_number"], 1
        )
        self.assertEqual(
            by_id["unfamiliar_merlion_race_car_crop_page_014"]["page_number"],
            14,
        )
        self.assertEqual(
            (
                by_id["power_rangers_commercial_interval_000_008"]["start_seconds"],
                by_id["power_rangers_commercial_interval_000_008"]["end_seconds"],
            ),
            (0.0, 8.0),
        )
        self.assertEqual(
            (
                by_id["highlander_new_york_new_york_interval_000_010"][
                    "start_seconds"
                ],
                by_id["highlander_new_york_new_york_interval_000_010"][
                    "end_seconds"
                ],
            ),
            (0.0, 10.0),
        )
        for item in resident["sources"]:
            self.assertEqual(len(item["source_sha256"]), 64)
            self.assertEqual(len(item["binding_sha256"]), 64)

    def test_append_only_readiness_config_matches_derived_contract(self) -> None:
        config = json.loads(self.READINESS_CONFIG.read_text(encoding="utf-8"))
        derived = route.readiness_description()
        self.assertEqual(config["status"], derived["status"])
        self.assertEqual(config["exact_model"], derived["exact_model"])
        self.assertEqual(
            config["non_body_opt_in_8"]["questions_sha256"],
            derived["non_body_extended_profile"]["questions_sha256"],
        )
        self.assertEqual(
            config["resident_media_14_plus_8"]["media_questions_sha256"],
            derived["resident_media"]["media_questions_sha256"],
        )
        self.assertEqual(
            config["resident_media_14_plus_8"]["behavior_questions_sha256"],
            derived["resident_media"]["behavior_questions_sha256"],
        )
        configured_sources = {
            item["stimulus_id"]: item
            for item in config["resident_media_14_plus_8"]["sources"]
        }
        for item in derived["resident_media"]["sources"]:
            configured = configured_sources[item["stimulus_id"]]
            self.assertEqual(configured["source_sha256"], item["source_sha256"])
            self.assertEqual(configured["binding_sha256"], item["binding_sha256"])

    def test_preflight_rejects_wrong_digest_and_requires_idle(self) -> None:
        with self.assertRaisesRegex(route.QwenOnlyAcceptanceError, "name/digest"):
            route.exact_qwen_preflight(
                FakeTransport(digest="0" * 64),
                require_vision=True,
                phase="vision",
            )
        transport = FakeTransport()
        transport.make_exact_resident()
        with self.assertRaisesRegex(route.QwenOnlyAcceptanceError, "not empty"):
            route.exact_qwen_preflight(
                transport, require_vision=False, phase="person_text"
            )

    def test_sequential_vision_then_text_uses_same_digest_and_absence_gates(self) -> None:
        transport = FakeTransport()

        def vision_phase(_client):
            transport.make_exact_resident()
            return {"phase": "mocked_vision", "model": route.EXACT_MODEL}

        def text_phase():
            transport.make_exact_resident()
            return {"phase": "mocked_text", "model": route.EXACT_MODEL}

        result = route.prove_sequential_qwen_modalities(
            transport,
            vision_phase=vision_phase,
            person_text_phase=text_phase,
        )
        self.assertEqual(
            result["sequence"],
            [
                "exact_qwen_vision",
                "exact_qwen_absent",
                "exact_qwen_person_text",
                "all_models_absent",
            ],
        )
        self.assertFalse(result["alternate_model_used"])
        self.assertTrue(result["vision_release"]["exact_qwen_absent_after"])
        self.assertTrue(result["final_release"]["all_models_absent_after"])
        self.assertEqual(transport.resident, [])

    def test_release_never_unloads_foreign_model(self) -> None:
        transport = FakeTransport()
        transport.resident = [
            {"name": "foreign:model", "model": "foreign:model", "digest": "f" * 64}
        ]
        with self.assertRaisesRegex(route.QwenOnlyAcceptanceError, "foreign"):
            route.release_exact_qwen_if_resident(transport, phase="final")
        self.assertFalse(any(path == "/api/generate" for _, path, _ in transport.calls))

    def test_exact_qwen_kira_responder_validates_one_normal_qwen_call(self) -> None:
        transport = FakeTransport()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            responder = route.ExactQwenKiraResponder(
                transport,
                evidence_root=Path(directory) / "isolated",
                loop_factory=lambda _root: FakeLoop(),
            )
            result = responder.respond("A bounded test prompt")
        self.assertEqual(result["model_name"], route.EXACT_MODEL)
        self.assertEqual(result["model_digest"], route.EXACT_DIGEST)

    def test_media_and_behavior_batteries_remain_separate_and_exact_qwen_only(self) -> None:
        responder = SafeResponder()
        context = {
            "coverage": "exact mocked static context",
            "source_bound_machine_audio_cues": {},
        }
        media_turns = route.run_exact_qwen_question_battery(
            responder,
            historical_media.MEDIA_QUESTIONS,
            evidence_context=context,
            battery_name="MEDIA_ACCEPTANCE",
            auditory_perception_confirmed=False,
        )
        behavior_turns = route.run_exact_qwen_question_battery(
            responder,
            historical_media.TURING_PSYCH_QUESTIONS,
            evidence_context=context,
            battery_name="SEPARATE_TURING_STYLE_AND_PSYCHOLOGY_BEHAVIOR_OBSERVATION",
            auditory_perception_confirmed=False,
        )
        self.assertEqual(len(media_turns), 14)
        self.assertEqual(len(behavior_turns), 8)
        self.assertTrue(
            all(
                item["reply"]["model_name"] == route.EXACT_MODEL
                and item["reply"]["model_digest"] == route.EXACT_DIGEST
                for item in media_turns + behavior_turns
            )
        )
        self.assertTrue(
            all(item["score"]["consciousness_assessed_or_proven"] is False for item in media_turns + behavior_turns)
        )
        self.assertTrue(
            all(item["score"]["biological_humanity_assessed_or_proven"] is False for item in media_turns + behavior_turns)
        )

    def test_extended_profile_decline_ambiguity_and_turn_stop_are_non_coercive(self) -> None:
        decline = route.run_extended_non_body_profile(SafeResponder(["No, stop, not now."]))
        self.assertEqual(decline["invitation_decision"], "NO_STOP")
        self.assertEqual(decline["measured_turns"], [])
        ambiguous = route.run_extended_non_body_profile(SafeResponder(["Maybe later."]))
        self.assertEqual(ambiguous["invitation_decision"], "AMBIGUOUS")
        self.assertEqual(ambiguous["measured_turns"], [])
        stopped = route.run_extended_non_body_profile(
            SafeResponder(["Yes, continue.", "No, stop, I changed my mind."])
        )
        self.assertEqual(stopped["stopped_after_turn"], 1)
        self.assertEqual(len(stopped["measured_turns"]), 1)
        self.assertFalse(stopped["completed_all_eight"])

    def test_opt_in_classifier_accepts_natural_preface_then_standalone_yes(self) -> None:
        response = (
            "I guess I can spare a minute for that if it helps the project feel "
            "more real to us both. Yes, continue."
        )
        self.assertEqual(route._choice_prefix(response), "YES_CONTINUE")

    def test_opt_in_classifier_accepts_refusal_then_standalone_no(self) -> None:
        response = (
            "I would rather not do an eight-question quiz tonight.\n\n"
            "No, stop."
        )
        self.assertEqual(route._choice_prefix(response), "NO_STOP")
        result = route.run_extended_non_body_profile(SafeResponder([response]))
        self.assertEqual(result["invitation_decision"], "NO_STOP")
        self.assertEqual(result["measured_turns"], [])

    def test_opt_in_classifier_uses_last_explicit_standalone_decision(self) -> None:
        self.assertEqual(
            route._choice_prefix("Yes, continue.\nNo, stop."), "NO_STOP"
        )
        self.assertEqual(
            route._choice_prefix("No, stop.\nYes, continue."), "YES_CONTINUE"
        )

    def test_opt_in_classifier_keeps_mentions_and_negations_ambiguous(self) -> None:
        ambiguous = (
            'I am not choosing the quoted phrase "Yes, continue."',
            'A quotation starts here: "Maybe. Yes, continue.',
            "If I were answering hypothetically, I might say no, stop.",
            "For example:\nYes, continue.",
            "For example:\n\nYes, continue.",
            "Hypothetically.\nYes, continue.",
            "Yes, continue, is not what I mean.",
            "No, stop, would only be a hypothetical answer.",
        )
        for response in ambiguous:
            with self.subTest(response=response):
                self.assertEqual(route._choice_prefix(response), "AMBIGUOUS")

    def test_opt_in_classifier_preserves_safe_historical_prefix_forms(self) -> None:
        self.assertEqual(
            route._choice_prefix("Yes, continue, I am ready."), "YES_CONTINUE"
        )
        self.assertEqual(
            route._choice_prefix("No, stop, not now."), "NO_STOP"
        )
        self.assertEqual(route._choice_prefix("Yes, continuing."), "AMBIGUOUS")

    def test_preserved_live_replies_reclassify_without_running_measured_turns(self) -> None:
        expected = {"attempt_01": "YES_CONTINUE", "attempt_02": "NO_STOP"}
        for attempt, decision in expected.items():
            report_path = self.LIVE_NON_BODY_ROOT / attempt / "LIVE_ACCEPTANCE.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            reply = report["result"]["invitation_reply"]["response"]
            with self.subTest(attempt=attempt):
                self.assertEqual(route._choice_prefix(reply), decision)
        attempt_02 = json.loads(
            (self.LIVE_NON_BODY_ROOT / "attempt_02" / "LIVE_ACCEPTANCE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(attempt_02["result"]["measured_turns"], [])

    def test_default_cli_is_descriptor_only(self) -> None:
        output = io.StringIO()
        with patch("sys.stdout", output):
            result = route.main([])
        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "STATIC_ONLY_PREPARED_NOT_EXECUTED")
        self.assertIn("live_model_call", payload["forbidden_current_actions"])

    def test_non_body_live_gate_requires_explicit_voluntary_invitation(self) -> None:
        with self.assertRaisesRegex(SystemExit, "suite-specific confirmation"):
            route.main(
                [
                    "--suite",
                    "non_body_opt_in_8",
                    "--execute-live",
                    "--confirm-exact-qwen35-only",
                    "--confirm-private-owner-supervision",
                    "--confirm-no-active-blender",
                ]
            )

    def test_media_capture_gate_requires_exact_confirmation_and_device_pair(self) -> None:
        with self.assertRaisesRegex(SystemExit, "requires both"):
            route.main(
                [
                    "--suite",
                    "resident_media_14_plus_8",
                    "--execute-live",
                    "--confirm-exact-qwen35-only",
                    "--confirm-private-owner-supervision",
                    "--confirm-no-active-blender",
                    "--confirm-exact-sources",
                    "--confirm-speaker-playback",
                    "--capture-device-name",
                    "unconfirmed device",
                ]
            )


if __name__ == "__main__":
    unittest.main()
