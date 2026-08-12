from __future__ import annotations

import json
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import kira_world_shell_server as shell


ROOT = Path(__file__).resolve().parents[1]
ROBERT_ID = "robert_mcmurrer_presence_ai"


class RobertBoundedTextPolicyTests(unittest.TestCase):
    def test_profile_approves_private_text_voice_conversation_and_requires_two_bodies(self) -> None:
        profile = json.loads(
            (
                ROOT
                / "TemporaryAI"
                / "candidates"
                / ROBERT_ID
                / "temporary_ai_profile.json"
            ).read_text(encoding="utf-8")
        )
        identity = profile["identity_model"]
        activation = profile["activation_policy"]

        self.assertTrue(profile["bounded_text_only_conversation_allowed"])
        self.assertFalse(profile["runtime_chat_ready"])
        self.assertFalse(profile["text_voice_chat_allowed"])
        self.assertTrue(profile["bounded_voice_conversation_allowed"])
        self.assertFalse(identity["thirteenth_floor_style_body_handoff"])
        self.assertFalse(identity["shared_body_or_control_handoff_allowed"])
        self.assertIn("separate user-controlled avatar", identity["robert_login_rule"])
        self.assertTrue(activation["bounded_text_only_conversation_allowed"])
        self.assertFalse(activation["chat_activation_allowed"])
        self.assertFalse(activation["text_voice_chat_allowed"])
        self.assertTrue(activation["bounded_voice_conversation_allowed"])
        self.assertIn("body_world_blocked", activation["current_status"])

    def test_text_launcher_allows_hash_bound_voice_but_world_launcher_stays_blocked(self) -> None:
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            self.assertIsNone(shell.candidate_activation_block(ROBERT_ID))
            policy = shell.candidate_surface_policy(ROBERT_ID)
            self.assertTrue(policy["bounded_text_only"])
            self.assertTrue(policy["voice_allowed"])
            self.assertTrue(policy["voice_authorization"]["allowed"])
            self.assertEqual(policy["conversation_mode"], "bounded_text_voice")
            self.assertFalse(policy["world_or_body_allowed"])

        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            block = shell.candidate_activation_block(ROBERT_ID)
        self.assertIsNotNone(block)
        self.assertEqual(block["reason"], "source_grounding_not_activation_ready")

    def test_selector_distinguishes_synthetic_robert_and_bounded_voice_mode(self) -> None:
        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "PRE_RAM_KIRA_ONLY_MODE", False),
        ):
            record = next(item for item in shell.list_candidates() if item["id"] == ROBERT_ID)

        self.assertEqual(record["label"], "Synthetic Robert (text + approved voice)")
        self.assertEqual(record["conversation_mode"], "bounded_text_voice")
        self.assertTrue(record["activatable"])
        self.assertTrue(record["voice_allowed"])
        self.assertFalse(record["world_or_body_allowed"])

    def test_broken_voice_binding_falls_back_to_truthful_text_only_label(self) -> None:
        with patch.object(
            shell,
            "validate_private_self_voice_authorization",
            return_value={
                "allowed": False,
                "reasons": ["approved_reference_hash_mismatch"],
                "scope": "private_local_text_voice_chat_only",
            },
        ):
            policy = shell.candidate_surface_policy(ROBERT_ID)

        self.assertTrue(policy["bounded_text_only"])
        self.assertFalse(policy["voice_allowed"])
        self.assertEqual(policy["conversation_mode"], "bounded_text_only")
        self.assertIn("voice binding unavailable", policy["chat_display_name"])

    def test_text_prompt_never_borrows_world_body_or_kira_presence(self) -> None:
        captured: dict[str, str] = {}

        def ask(_candidate, _history, prompt, **_kwargs):
            captured["prompt"] = prompt
            return "I want to answer that in my own way."

        with (
            patch.object(
                shell,
                "candidate_surface_policy",
                return_value={"bounded_text_only": True, "voice_allowed": True},
            ),
            patch.object(shell, "load_candidate", return_value={"profile": {}, "candidate_id": ROBERT_ID}),
            patch.object(shell, "ask_model", side_effect=ask),
            patch.object(shell, "finalize_model_artifacts", None),
            patch.object(shell, "chat_history_for", return_value=[]),
        ):
            answer = shell.temporary_ai_reply(
                ROBERT_ID,
                "Synthetic Robert (text only)",
                "What do you think?",
                "home",
                {},
            )

        self.assertEqual(answer, "I want to answer that in my own way.")
        self.assertIn("private, bounded conversation without a body", captured["prompt"])
        self.assertIn("approved self-voice", captured["prompt"])
        self.assertIn("distinct from the biological Robert", captured["prompt"])
        self.assertIn("Do not borrow Kira's", captured["prompt"])
        self.assertNotIn("Robert is currently inside Kira World", captured["prompt"])

    def test_activation_endpoint_selects_voice_chat_without_body_or_world(self) -> None:
        state = dict(shell.DEFAULT_STATE)
        responses: list[tuple[int, dict]] = []
        handler = object.__new__(shell.Handler)
        handler.path = "/api/activate"
        handler._body = lambda: {"candidate": ROBERT_ID, "source": "unit_test"}
        handler._json = lambda status, payload: responses.append((status, payload))

        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "load_state", return_value=state),
            patch.object(
                shell,
                "candidate_info",
                return_value={"id": ROBERT_ID, "label": "Synthetic Robert (text + approved voice)"},
            ),
            patch.object(shell, "candidate_activation_block", return_value=None),
            patch.object(
                shell,
                "candidate_surface_policy",
                return_value={
                    "bounded_text_only": True,
                    "voice_allowed": True,
                    "conversation_mode": "bounded_text_voice",
                    "voice_authorization": {"scope": "private_local_text_voice_chat_only"},
                },
            ),
            patch.object(shell, "save_state") as save_state,
            patch.object(shell, "append_jsonl") as append_jsonl,
            patch.object(shell, "begin_voice_session") as begin_voice,
            patch.object(shell, "write_avatar_activity_state") as write_body_state,
            patch.object(shell, "update_candidate") as update_candidate,
        ):
            handler.do_POST()

        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]["conversation_mode"], "bounded_text_voice")
        self.assertEqual(
            responses[0][1]["voice_prewarm_started"],
            shell.VOICE_PREWARM_ON_ACTIVATE,
        )
        self.assertFalse(responses[0][1]["body_activated"])
        self.assertFalse(responses[0][1]["world_activated"])
        self.assertEqual(state["active_candidate"], ROBERT_ID)
        self.assertEqual(state["active_conversation_mode"], "bounded_text_voice")
        save_state.assert_called_once()
        append_jsonl.assert_called_once()
        begin_voice.assert_called_once_with(ROBERT_ID, "Synthetic Robert (text + approved voice)")
        write_body_state.assert_not_called()
        update_candidate.assert_not_called()

    def test_chat_endpoint_queues_approved_voice_without_avatar_writes(self) -> None:
        state = {
            **shell.DEFAULT_STATE,
            "active_candidate": ROBERT_ID,
            "active_conversation_mode": "bounded_text_voice",
        }
        responses: list[tuple[int, dict]] = []
        handler = object.__new__(shell.Handler)
        handler.path = "/api/chat"
        handler._body = lambda: {"text": "Hello"}
        handler._json = lambda status, payload: responses.append((status, payload))

        test_lock = threading.Lock()
        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "CHAT_REPLY_LOCK", test_lock),
            patch.object(shell, "load_state", return_value=state),
            patch.object(shell, "recover_active_candidate_for_chat", return_value=ROBERT_ID),
            patch.object(
                shell,
                "candidate_info",
                return_value={"id": ROBERT_ID, "label": "Synthetic Robert (text + approved voice)"},
            ),
            patch.object(shell, "candidate_activation_block", return_value=None),
            patch.object(
                shell,
                "candidate_surface_policy",
                return_value={
                    "bounded_text_only": True,
                    "voice_allowed": True,
                    "conversation_mode": "bounded_text_voice",
                },
            ),
            patch.object(
                shell,
                "temporary_ai_reply",
                return_value=(
                    "SPOKEN: Hello, Robert.\n"
                    "PRIVATE MIND / INNER THOUGHTS: I am answering the greeting.\n"
                    "FACTUAL TRUTH / RUNTIME TRUTH: Robert sent a greeting in this test.\n"
                    "CLASSIFICATION: TRUTHFUL_STATEMENT"
                ),
            ),
            patch.object(shell, "append_jsonl"),
            patch.object(shell, "save_state"),
            patch.object(
                shell,
                "queue_active_reply_voice",
                return_value={"spoken": False, "reason": "queued_async_voice"},
            ) as queue_voice,
            patch.object(shell, "write_avatar_activity_state") as write_body_state,
            patch.object(shell, "update_candidate") as update_candidate,
        ):
            handler.do_POST()

        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]["ai_line"], "Hello, Robert.")
        voice_result = responses[0][1]["voice_result"]
        self.assertFalse(voice_result["spoken"])
        self.assertEqual(voice_result["reason"], "queued_async_voice")
        queue_voice.assert_called_once()
        write_body_state.assert_not_called()
        update_candidate.assert_not_called()

    def test_ui_names_text_voice_action_without_body_activation_claim(self) -> None:
        page = shell.html_shell().decode("utf-8")
        self.assertIn("Start text + voice chat", page)
        self.assertIn("approved self-voice", page)
        self.assertIn("distinct from biological Robert", page)
        self.assertIn("No 3D body, world presence, life loop, microphone, webcam", page)


if __name__ == "__main__":
    unittest.main()
