from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

import conversation_loop as conversation  # noqa: E402
from tools import kira_world_shell_server as shell  # noqa: E402


class KiraPrivateAcceptanceAuditTests(unittest.TestCase):
    def test_nonstreaming_ollama_call_records_exact_metrics_and_raw_reply(self) -> None:
        instance = object.__new__(conversation.ConversationLoop)
        instance.profile = SimpleNamespace(name="Kira")
        instance.conversation_history = []
        instance.autobiographical_context = ""
        instance._active_model_call_audit = []
        instance._build_ollama_runtime_prompt = lambda: "SYSTEM"

        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "message": {"content": "  Exact raw model words.  "},
            "total_duration": 9_000_000_000,
            "load_duration": 2_000_000_000,
            "prompt_eval_count": 100,
            "prompt_eval_duration": 3_000_000_000,
            "eval_count": 6,
            "eval_duration": 4_000_000_000,
            "done_reason": "stop",
        }
        fake_requests = SimpleNamespace(
            post=Mock(return_value=response),
            exceptions=SimpleNamespace(ConnectionError=ConnectionError),
        )

        with patch.dict(sys.modules, {"requests": fake_requests}):
            result = conversation.ConversationLoop._call_ollama(
                instance,
                {"user_message": "Owner test", "memory_context": ""},
            )

        self.assertEqual(result, "Exact raw model words.")
        self.assertEqual(len(instance._active_model_call_audit), 1)
        audit = instance._active_model_call_audit[0]
        self.assertEqual(audit["raw_reply"], result)
        self.assertFalse(audit["stream"])
        self.assertFalse(audit["first_token_available"])
        self.assertEqual(
            audit["first_token_unavailable_reason"],
            "current_ollama_request_is_nonstreaming",
        )
        self.assertEqual(audit["ollama_metrics"]["load_duration"], 2_000_000_000)
        self.assertEqual(audit["ollama_metrics"]["eval_duration"], 4_000_000_000)

    def test_process_audit_observes_ordered_cleanup_without_changing_reply(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = conversation.ConversationLoop(
                    speaker="Kira",
                    relationship_state_file=Path(tmpdir) / "relationships.json",
                    privacy_session_file=Path(tmpdir) / "privacy.json",
                    decision_log_file=Path(tmpdir) / "decisions.jsonl",
                    conversation_log_file=Path(tmpdir) / "conversation.jsonl",
                    attention_state_file=Path(tmpdir) / "attention.json",
                    daily_life_state_dir=Path(tmpdir) / "daily",
                    memory_candidate_dir=Path(tmpdir) / "memory_candidates",
                )
                with patch.object(loop, "call_model", return_value="I am here with you."):
                    reply = loop.process("A neutral bounded audit sentence.")
            finally:
                os.chdir(old_cwd)

        self.assertEqual(reply, "I am here with you.")
        audit = loop.last_turn_audit
        self.assertEqual(audit["response_route"], "ordinary_model_call")
        self.assertEqual(audit["initial_pipeline_reply"], reply)
        self.assertEqual(audit["final_core_reply"], reply)
        self.assertGreater(len(audit["transformations"]), 20)
        self.assertTrue(all("stage" in item and "changed" in item for item in audit["transformations"]))

    def test_shell_private_audit_binds_prompt_sensory_and_final_reply(self) -> None:
        loop = Mock()
        loop.process.return_value = "I can see Robert on the screen and hear his podcast."
        loop.last_turn_audit = {
            "model_name": "llama3.1:8b",
            "model_calls": [{"raw_reply": "I can see Robert on the screen and hear his podcast."}],
            "transformations": [],
            "final_core_reply": "I can see Robert on the screen and hear his podcast.",
        }
        loop._active_model_call_audit = []
        session = object()
        sensory = (
            "ONE-TURN EPHEMERAL SENSORY NOTE.\n"
            "Visual derived cues (non-identifying; no object or person recognition): "
            "brightness_class=balanced, motion_class=baseline_unavailable.\n"
            "Auditory derived cue: local ASR detected possible room speech with unknown speaker."
        )
        prompt = f"PRIVATE PROMPT\n{sensory}\nRobert says: What can you see?"
        metadata = {
            "used": True,
            "cue_count": 1,
            "modalities": ["visual"],
            "cue_ids": ["cue_000001"],
        }

        with (
            patch.object(shell, "KIRA_PRIVATE_ACCEPTANCE_AUDIT_ENABLED", True),
            patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True),
            patch.object(shell, "_get_kira_core_loop", return_value=loop),
            patch.object(
                shell,
                "_one_turn_kira_sensory_context",
                return_value=(sensory, session, metadata),
            ),
            patch.object(shell, "_kira_world_core_prompt", return_value=prompt),
            patch.object(
                shell,
                "_consume_one_turn_kira_sensory_context",
                return_value={"purged": True, "removed_count": 1, "lease_preserved": True},
            ),
            patch.object(shell, "append_jsonl"),
            patch.object(shell, "_repair_kira_social_tangent", side_effect=lambda _l, _t, value, _loc, _s: value),
            patch.object(shell, "_clean_kira_world_reply", side_effect=lambda _t, value: value),
            patch.object(
                shell,
                "_repair_kira_cross_session_repeat",
                side_effect=lambda _l, _t, value, one_turn_sensory_context="": value,
            ),
            patch.object(shell, "_repair_kira_answered_question_loop", side_effect=lambda _l, _t, value, _s: value),
            patch.object(shell, "_apply_kira_spoken_truth_policy", side_effect=lambda _t, value, _s, **_k: value),
            patch.object(shell, "_replace_last_kira_public_history"),
        ):
            reply = shell._kira_world_core_reply(
                "Kira",
                "What can you see?",
                "home",
                {"active_candidate": "kira", "last_activation_at": "audit-r1"},
            )

        self.assertEqual(
            reply,
            "The brightness looks balanced; one sample can't show motion. "
            "I can't recognize objects or identities. "
            "I detect possible speech, but its speaker and source are unknown.",
        )
        self.assertLessEqual(len(reply), 180)
        audit = shell.KIRA_LAST_PRIVATE_REPLY_AUDIT
        self.assertEqual(audit["core_prompt_sha256"], hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        self.assertEqual(audit["one_turn_sensory_context"], sensory)
        self.assertEqual(audit["sensory_cue_ids"], ["cue_000001"])
        self.assertTrue(audit["one_turn_sensory_context_inserted"])
        self.assertEqual(audit["final_shell_reply"], reply)
        self.assertTrue(audit["sensory_cleanup"]["lease_preserved"])
        sensory_gate = next(
            item
            for item in audit["outer_transformations"]
            if item["stage"] == "apply_kira_sensory_truth_gate"
        )
        self.assertTrue(sensory_gate["changed"])
        self.assertEqual(sensory_gate["after"], reply)

    def test_private_audit_is_disabled_in_normal_environment_by_default(self) -> None:
        self.assertFalse(
            str(os.environ.get("KIRA_PRIVATE_ACCEPTANCE_AUDIT", "0")).strip().lower()
            in {"1", "true", "yes"}
        )


if __name__ == "__main__":
    unittest.main()
