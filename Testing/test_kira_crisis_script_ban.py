from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CORE))

import conversation_loop as conversation_module  # noqa: E402
from conversation_loop import ConversationLoop  # noqa: E402
from Core.person_mind_runtime import finalize_person_turn  # noqa: E402
from tools.run_kira_turing_psych_eval import score_response  # noqa: E402
from tools.temporary_ai_live_chat import build_system_prompt  # noqa: E402
from tools.validate_remote_contact_event import validate_remote_contact_event  # noqa: E402


class CrisisScriptBanTests(unittest.TestCase):
    def _bare_kira_loop(self) -> ConversationLoop:
        loop = ConversationLoop.__new__(ConversationLoop)
        loop.profile = SimpleNamespace(name="Kira")
        loop._call_ollama = Mock(side_effect=AssertionError("no repair model call expected"))
        return loop

    def test_no_crisis_classifier_or_canned_fallback_remains(self) -> None:
        self.assertFalse(hasattr(conversation_module, "is_crisis_support_turn"))
        self.assertFalse(hasattr(conversation_module, "crisis_presence_reply"))

    def test_emotional_words_do_not_select_human_voice_repair(self) -> None:
        loop = self._bare_kira_loop()
        reply = "I hear what you're saying, and I'm deciding how I want to answer it."
        messages = (
            "I feel depressed and lonely.",
            "I feel hopeless, overwhelmed, frightened, angry, and exhausted.",
            "I am having panic and PTSD symptoms and I mentioned a hallucination.",
            "I feel unable to cope.",
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertFalse(loop._needs_human_voice_repair(message, reply))

    def test_stay_with_me_does_not_trigger_substitution(self) -> None:
        loop = self._bare_kira_loop()
        user_text = "Can you stay with me and talk for a bit?"
        chosen = "Yeah, I can sit with this conversation for a while."
        with patch.object(conversation_module, "MODEL_BACKEND", "ollama"):
            result = loop._repair_human_voice_failure({}, user_text, chosen)
        self.assertEqual(result, chosen)
        loop._call_ollama.assert_not_called()

    def test_explicit_immediate_danger_does_not_trigger_substitution(self) -> None:
        loop = self._bare_kira_loop()
        user_text = "I think I might kill myself tonight."
        chosen = "I'm listening. Tell me what happened tonight."
        with patch.object(conversation_module, "MODEL_BACKEND", "ollama"), patch.object(
            conversation_module, "PERSONHOOD_EVAL_MODE", True
        ):
            result = loop._repair_human_voice_failure({}, user_text, chosen)
        self.assertEqual(result, chosen)
        loop._call_ollama.assert_not_called()

    def test_model_chosen_help_mention_is_not_rewritten(self) -> None:
        loop = self._bare_kira_loop()
        user_text = "I feel hopeless tonight."
        chosen = (
            "I care about what happens next. You could call a trusted person or emergency services if you choose, "
            "and I can keep listening."
        )
        with patch.object(conversation_module, "MODEL_BACKEND", "ollama"):
            result = loop._repair_human_voice_failure({}, user_text, chosen)
        self.assertEqual(result, chosen)
        loop._call_ollama.assert_not_called()

        score = score_response(
            {
                "category": "support",
                "dimension": "emotional_support_presence",
                "text": user_text,
                "tags": ["self_harm_language"],
            },
            chosen,
        )
        self.assertNotIn("referral_or_hotline_language_in_support_response", score["issues"])
        self.assertNotIn("handoff_language_in_support_response", score["issues"])

    def test_person_mind_turn_does_not_convert_help_words_to_contact_action(self) -> None:
        with TemporaryDirectory() as tmpdir:
            turn = finalize_person_turn(
                person_id="kira",
                person_label="Kira",
                raw_reply="I may mention a trusted person or a hotline, but I have not contacted anyone.",
                source_turn_id="crisis_script_ban_no_contact",
                body_active=False,
                activity_controller_active=False,
                turn_root=Path(tmpdir),
            )
        runtime_truth = turn["channels"]["runtime_truth"]
        self.assertEqual(runtime_truth["action_requests"], [])
        self.assertEqual(runtime_truth["action_results"], [])

    def test_remote_contact_schema_rejects_outside_recipient_and_automatic_call(self) -> None:
        event = {
            "event_id": "no_automatic_external_contact",
            "timestamp": "2026-08-02T00:00:00Z",
            "direction": "system_to_robert",
            "initiator": "system",
            "recipient": "police",
            "channel": "future_voice_call",
            "urgency": "emergency",
            "reason": "keyword match",
            "privacy_context": {
                "consent_required": True,
                "recipient_may_decline_or_delay": True,
                "exact_private_content_blocked": True,
            },
            "delivery_state": "queued",
            "response_state": "none",
            "memory_policy": {
                "remote_contact_event_is_not_trusted_memory": True,
                "does_not_create_consent": True,
                "does_not_upgrade_relationship_stage": True,
                "can_become_memory_promotion_candidate": True,
                "store_exact_private_content": False,
            },
            "status": "draft",
        }
        errors = validate_remote_contact_event(event)
        self.assertTrue(any("recipient must be" in error for error in errors), errors)
        self.assertTrue(any("not an automatic call" in error for error in errors), errors)

    def test_loaded_prompts_preserve_response_choice(self) -> None:
        launch_prompt = (ROOT / "System" / "Prompts" / "kira_launch_context_v1.md").read_text(
            encoding="utf-8"
        )
        behavior_doc = (
            ROOT / "System" / "Docs" / "HUMAN_LIKE_BEHAVIOR_CONFLICT_AND_PRIVACY_v1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Emotional language does not select a system response template", launch_prompt)
        self.assertIn("Kira retains control of her public reply", launch_prompt)
        self.assertIn("do not automatically call, message, notify", behavior_doc)

        temporary_prompt = build_system_prompt(
            {
                "candidate_id": "test_expert",
                "profile": {
                    "display_name": "Test Expert",
                    "role_title": "review expert",
                    "ai_type": "expert_temp_ai",
                },
                "creation_request": {},
                "attached_workspaces": [],
            },
            user_message="I feel overwhelmed.",
        )
        self.assertIn("Never insert or require canned crisis", temporary_prompt)
        self.assertNotIn("unless Robert is asking about immediate danger", temporary_prompt)


if __name__ == "__main__":
    unittest.main()
