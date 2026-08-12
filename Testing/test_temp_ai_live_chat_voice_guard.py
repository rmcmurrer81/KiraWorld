from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from tools.temporary_ai_live_chat import load_candidate
from tools.temporary_ai_live_chat_gui import (
    TemporaryAILiveChatGUI,
    candidate_voice_output_decision,
)


ELSA_ID = "elsa_frozen_frozen_fever_frozen_ii_20260716"
KATHRYN_ID = "kathryn_merteuil_kathryn_merteuil_20260605_213017"
ROBERT_ID = "robert_mcmurrer_presence_ai"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class FakeIntVar:
    def __init__(self, value: int) -> None:
        self.value = value

    def get(self) -> int:
        return self.value

    def set(self, value: int) -> None:
        self.value = value


class TemporaryAILiveChatVoiceGuardTests(unittest.TestCase):
    def test_window_voice_checkbox_defaults_off(self) -> None:
        source = (ROOT / "tools" / "temporary_ai_live_chat_gui.py").read_text(encoding="utf-8")
        self.assertIn("self.voice_enabled = IntVar(value=0)", source)

    def test_elsa_and_kathryn_are_text_only_with_specific_reasons(self) -> None:
        for candidate_id in (ELSA_ID, KATHRYN_ID):
            with self.subTest(candidate_id=candidate_id):
                decision = candidate_voice_output_decision(load_candidate(candidate_id))
                self.assertFalse(decision["allowed"])
                self.assertTrue(decision["reason"])
                self.assertIsNone(decision["profile_path"])
                self.assertNotIn("Windows voice is active", decision["reason"])

    def test_activation_plan_voice_block_overrides_ready_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            relative = Path("Voice/profiles/temp_ai/test_voice_profile.json")
            write_json(
                root / relative,
                {
                    "target_name": "Test Person",
                    "status": {"ready_for_use": True, "ready_for_text_tts": True},
                    "sapi_approximation": {"voice_name": "Explicit Test Voice"},
                },
            )
            candidate = {
                "candidate_id": "test_person",
                "profile": {
                    "display_name": "Test Person",
                    "activation_policy": {"bounded_voice_conversation_allowed": True},
                    "voice_and_behavior": {"voice_profile": relative.as_posix()},
                },
                "activation_plan": {
                    "mode_readiness": {
                        "voice_chat": {"ready": False, "reason": "Owner listening review is incomplete."}
                    }
                },
            }

            decision = candidate_voice_output_decision(candidate, root)

        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "Owner listening review is incomplete.")

    def test_missing_candidate_profile_never_uses_global_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            candidate = {
                "candidate_id": "ready_but_missing_voice",
                "profile": {
                    "display_name": "Ready But Missing Voice",
                    "activation_policy": {"bounded_voice_conversation_allowed": True},
                },
                "activation_plan": {},
            }
            decision = candidate_voice_output_decision(candidate, Path(tmpdir))

        self.assertFalse(decision["allowed"])
        self.assertIn("No candidate-specific voice profile", decision["reason"])
        self.assertIn("fallback is disabled", decision["reason"])

    def test_explicitly_allowed_ready_candidate_specific_sapi_route_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            relative = Path("Voice/profiles/temp_ai/approved_test_voice_profile.json")
            write_json(
                root / relative,
                {
                    "target_name": "Approved Test Person",
                    "status": {"ready_for_use": True, "ready_for_text_tts": True},
                    "sapi_approximation": {
                        "voice_name": "Explicit Test Voice",
                        "rate": 0,
                        "volume": 90,
                    },
                },
            )
            candidate = {
                "candidate_id": "approved_test_person",
                "profile": {
                    "candidate_id": "approved_test_person",
                    "display_name": "Approved Test Person",
                    "activation_policy": {"bounded_voice_conversation_allowed": True},
                    "voice_and_behavior": {"voice_profile": relative.as_posix()},
                },
                "activation_plan": {"mode_readiness": {"voice_chat": {"ready": True}}},
            }

            decision = candidate_voice_output_decision(candidate, root)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["profile_path"], root / relative)

    def test_robert_bound_self_voice_stays_available_but_opt_in(self) -> None:
        decision = candidate_voice_output_decision(load_candidate(ROBERT_ID))

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["profile_path"].name, "robert_mcmurrer_voice_profile.json")

    def test_speech_boundary_turns_off_blocked_candidate_without_calling_backend(self) -> None:
        gui = object.__new__(TemporaryAILiveChatGUI)
        gui.candidate = load_candidate(ELSA_ID)
        gui.voice_enabled = FakeIntVar(1)
        gui.voice_toggle = Mock()
        gui.voice_status = Mock()

        with (
            patch("tools.temporary_ai_live_chat_gui.speak_text") as speak,
            patch("tools.temporary_ai_live_chat_gui.load_candidate_voice_config") as config,
        ):
            queued = gui.queue_reply_voice("Hello, Robert.")

        self.assertFalse(queued)
        self.assertEqual(gui.voice_enabled.get(), 0)
        speak.assert_not_called()
        config.assert_not_called()
        rendered = gui.voice_status.config.call_args.kwargs["text"]
        self.assertIn("Voice unavailable (text only)", rendered)


if __name__ == "__main__":
    unittest.main()
