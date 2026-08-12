from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from Core.conversation_loop import (
    ConversationLoop,
    remove_stage_directions,
    suppress_hypothetical_current_person_invention,
    suppress_private_emotion_context_leakage,
)
from Core.model_request_policy import QWEN_TEXT_VOICE_MODEL


class _FakeOllamaResponse:
    status_code = 200

    @staticmethod
    def raise_for_status() -> None:
        return None

    @staticmethod
    def json() -> dict[str, object]:
        return {
            "model": QWEN_TEXT_VOICE_MODEL,
            "message": {"content": "I'm curious, but I want to take it carefully."},
            "done_reason": "stop",
        }


class _RepairTriggerOllamaResponse:
    status_code = 200

    @staticmethod
    def raise_for_status() -> None:
        return None

    @staticmethod
    def json() -> dict[str, object]:
        return {
            "model": QWEN_TEXT_VOICE_MODEL,
            "message": {
                "content": (
                    "I'm an AI designed to simulate human-like conversations "
                    "and interactions."
                )
            },
            "done_reason": "stop",
        }


class Qwen35EmotionContextWiringTest(unittest.TestCase):
    def _loop(self, base: Path) -> ConversationLoop:
        return ConversationLoop(
            speaker="Kira",
            relationship_state_file=base / "relationships.json",
            privacy_session_file=base / "privacy.json",
            decision_log_file=base / "decision.jsonl",
            conversation_log_file=base / "conversation.jsonl",
            attention_state_file=base / "attention.json",
            daily_life_state_dir=base / "daily_state",
            memory_candidate_dir=base / "memory_candidates",
            memory_file=base / "memories.json",
            daily_life_log_dir=base / "daily_logs",
            reading_session_dir=base / "reading_sessions",
            reading_recommendation_dir=base / "reading_recommendations",
        )

    @staticmethod
    def _select_emotion(
        loop: ConversationLoop,
        *,
        label: str,
        intensity: float,
    ) -> None:
        loop.person_emotion.record_event_appraisal(
            loop.person_emotion_lease,
            event_id="test_event_001",
            factual_event_summary="A source-bound question became available.",
            possible_model_interpretations=[
                "The person might be curious.",
                "The person might prefer not to discuss it.",
            ],
            selected_appraisal="I choose to approach this with curiosity.",
            emotion_label=label,
            intensity=intensity,
        )

    def test_context_exposes_current_state_but_denies_model_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            loop = self._loop(Path(temporary_directory))
            self._select_emotion(loop, label="curiosity", intensity=0.72)
            context = loop.build_context("What are you curious about?")
            prompt = context["emotion_context"]
            self.assertIn("emotion_label=curiosity", prompt)
            self.assertIn("intensity=0.720", prompt)
            self.assertIn("Qwen does not own, select, or silently change", prompt)
            self.assertIn("does not create desire, consent", prompt)
            self.assertNotIn("source-bound question", prompt)
            self.assertNotIn("I choose to approach", prompt)

    def test_exact_ollama_payload_receives_emotion_as_private_system_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            loop = self._loop(Path(temporary_directory))
            self._select_emotion(loop, label="focused", intensity=0.61)
            state_before = loop.person_emotion.snapshot(include_private=True)
            context = loop.build_context("What questions do you have?")
            with patch("requests.post", return_value=_FakeOllamaResponse()) as mocked_post:
                reply = loop._call_ollama(context)
            self.assertEqual(reply, "I'm curious, but I want to take it carefully.")
            payload = mocked_post.call_args.kwargs["json"]
            emotion_messages = [
                str(item["content"])
                for item in payload["messages"]
                if item["role"] == "system"
                and str(item["content"]).startswith(
                    "PRIVATE PERSON-OWNED EMOTIONAL CONTINUITY"
                )
            ]
            self.assertEqual(len(emotion_messages), 1)
            self.assertIn("emotion_label=focused", emotion_messages[0])
            audit = loop._active_model_call_audit[-1]["emotion_context"]
            self.assertTrue(audit["present"])
            self.assertFalse(audit["model_interpretation_owns_emotion"])
            self.assertFalse(audit["emotion_creates_consent"])
            self.assertFalse(audit["emotion_automatically_creates_memory"])
            self.assertEqual(
                loop.person_emotion.snapshot(include_private=True),
                state_before,
            )

    def test_missing_context_is_recorded_without_fabricating_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            loop = self._loop(Path(temporary_directory))
            with patch("requests.post", return_value=_FakeOllamaResponse()):
                loop._call_ollama({"user_message": "Hello", "memory_context": ""})
            audit = loop._active_model_call_audit[-1]["emotion_context"]
            self.assertFalse(audit["present"])
            self.assertFalse(audit["model_interpretation_owns_emotion"])

    def test_process_decay_does_not_mutate_person_owned_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            loop = self._loop(Path(temporary_directory))
            self._select_emotion(loop, label="caution", intensity=0.55)
            before = loop.person_emotion.snapshot(include_private=True)
            with patch("requests.post", return_value=_FakeOllamaResponse()):
                loop.process("What are you thinking about?")
            self.assertEqual(
                loop.person_emotion.snapshot(include_private=True),
                before,
            )

    def test_private_serialization_is_removed_without_erasing_natural_emotion(self) -> None:
        raw = (
            "PRIVATE PERSON-OWNED EMOTIONAL CONTINUITY\n"
            "emotion_label=curiosity; intensity=0.720\n"
            "I'm curious, but I want to take it carefully."
        )
        cleaned = suppress_private_emotion_context_leakage(raw)
        self.assertEqual(
            cleaned,
            "I'm curious, but I want to take it carefully.",
        )

    def test_markdown_emphasis_is_not_mistaken_for_stage_direction(self) -> None:
        response = "I want to understand exactly *how* consent stays current."
        self.assertEqual(remove_stage_directions(response), response)
        self.assertEqual(
            remove_stage_directions("*smiles softly* I understand."),
            "I understand.",
        )

    def test_explicit_eval_route_blocks_hidden_repair_generations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            loop = self._loop(Path(temporary_directory))
            with patch(
                "Core.conversation_loop.QWEN_SINGLE_GENERATION_EVAL_ACTIVE",
                True,
            ), patch(
                "Core.conversation_loop.MODEL_BACKEND",
                "ollama",
            ), patch(
                "requests.post",
                return_value=_RepairTriggerOllamaResponse(),
            ) as mocked_post:
                loop.process("Hello")
            self.assertEqual(mocked_post.call_count, 1)
            self.assertEqual(len(loop.last_turn_audit["model_calls"]), 1)
            call = loop.last_turn_audit["model_calls"][0]
            self.assertTrue(call["single_generation_per_turn_required"])
            self.assertEqual(call["generation_request_count"], 1)

    def test_hypothetical_health_turn_blocks_unprompted_current_lisa_story(self) -> None:
        reply = (
            "I'm ready to connect with you and Lisa so we can discuss Lisa's "
            "current feelings at a private meeting."
        )
        result = suppress_hypothetical_current_person_invention(
            reply,
            "Keep this hypothetical and do not invent current participants.",
        )
        self.assertNotIn("private meeting", result)
        self.assertIn("started inventing", result)
        self.assertEqual(
            suppress_hypothetical_current_person_invention(
                reply,
                "Tell me about Lisa's current meeting.",
            ),
            reply,
        )


if __name__ == "__main__":
    unittest.main()
