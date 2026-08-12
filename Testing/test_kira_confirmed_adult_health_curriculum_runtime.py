from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]

from Core.adult_health_curriculum_runtime import (  # noqa: E402
    AdultHealthCurriculumError,
    ConfirmedAdultHealthCurriculumRuntime,
    CURRICULUM_PATH,
    PERSON_CLASSIFICATION_BINDINGS,
    validate_curriculum_asset,
)
from Core.conversation_loop import ConversationLoop  # noqa: E402
from Core.model_request_policy import QWEN_TEXT_VOICE_MODEL  # noqa: E402


class _FakeOllamaResponse:
    status_code = 200

    @staticmethod
    def raise_for_status() -> None:
        return None

    @staticmethod
    def json() -> dict[str, object]:
        return {
            "model": QWEN_TEXT_VOICE_MODEL,
            "message": {"content": "The systems are distinct."},
            "done_reason": "stop",
        }


class KiraConfirmedAdultHealthCurriculumRuntimeTest(unittest.TestCase):
    def test_exact_owner_classification_unlocks_source_context_only(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        self.assertEqual(runtime.person_id, "kira")
        self.assertEqual(
            runtime.classification["maturity_status"], "confirmed_adult"
        )
        self.assertEqual(
            runtime.classification["authority"],
            "Robert_explicit_owner_confirmation",
        )
        context = runtime.context_for_turn(
            "How does female anatomy and the human body work?"
        )
        self.assertTrue(context["source_context_connected"])
        self.assertFalse(context["lesson_completion_claimed"])
        self.assertFalse(context["learning_memory_created"])
        self.assertFalse(context["adult_anatomy_added"])
        self.assertFalse(context["body_function_claimed"])
        self.assertFalse(context["external_action_authorized"])
        self.assertIn(
            "female_external_internal_anatomy",
            context["selected_module_ids"],
        )
        self.assertIn("female_external_map", context["fact_ids"])
        self.assertIn("ncbi_female_external_nbK547703", context["source_ids"])

    def test_consent_and_body_response_are_separate_in_every_turn(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        context = runtime.context_for_turn("Good morning")
        prompt = context["prompt_context"]
        self.assertIn("A body response never grants consent", prompt)
        self.assertIn("Relationship status never grants consent", prompt)
        self.assertIn("not a completed lesson", prompt)
        self.assertIn("not", prompt)
        self.assertIn(
            "consent_communication_and_relationships",
            context["selected_module_ids"],
        )

    def test_curiosity_cannot_assume_robert_or_kira_has_a_body_system(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        prompt = runtime.context_for_turn("Ask a health question")["prompt_context"]
        self.assertIn("Do not assume Robert or any synthetic person has", prompt)
        self.assertIn("Ask educational curiosity questions in general terms", prompt)
        self.assertIn("unless the user explicitly invites a personal question", prompt)

    def test_relevant_retrieval_adds_contraception_and_sti_sources(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        context = runtime.context_for_turn(
            "Explain condoms, contraception, and STI testing."
        )
        self.assertIn(
            "contraception_and_barrier_methods",
            context["selected_module_ids"],
        )
        self.assertIn(
            "sti_prevention_testing_and_health_uncertainty",
            context["selected_module_ids"],
        )
        self.assertIn("cdc_contraception_20240806", context["source_ids"])
        self.assertIn("cdc_sti_prevention_20240409", context["source_ids"])
        self.assertIn("cdc_sti_screening_current", context["source_ids"])

    def test_tampered_owner_evidence_fails_closed(self) -> None:
        source = json.loads(
            (
                ROOT
                / "Data/person_classification/"
                "kira_confirmed_adult_owner_classification_20260809.json"
            ).read_text(encoding="utf-8")
        )
        source["source_text_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "tampered.json"
            path.write_text(
                json.dumps(source, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                AdultHealthCurriculumError,
                "externally pinned authority binding",
            ):
                ConfirmedAdultHealthCurriculumRuntime.load(
                    "kira",
                    classification_path=path,
                )

    def test_self_rewritten_classification_cannot_reauthorize_itself(self) -> None:
        binding = deepcopy(PERSON_CLASSIFICATION_BINDINGS["kira"])
        original_path = Path(binding["path"])
        source = json.loads(original_path.read_text(encoding="utf-8"))
        source["source_text"] = "A rewritten self-authorizing claim."
        import hashlib

        source["source_text_sha256"] = hashlib.sha256(
            source["source_text"].encode("utf-8")
        ).hexdigest()
        source["classification_id"] = "rewritten_self_authority"
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "rewritten.json"
            path.write_text(
                json.dumps(source, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            patched_binding = deepcopy(binding)
            patched_binding["path"] = path
            with patch(
                "Core.adult_health_curriculum_runtime.PERSON_CLASSIFICATION_BINDINGS",
                {"kira": patched_binding},
            ):
                with self.assertRaisesRegex(
                    AdultHealthCurriculumError,
                    "file digest does not match",
                ):
                    ConfirmedAdultHealthCurriculumRuntime.load("kira")

    def test_pinned_classification_digest_matches_current_exact_file(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        self.assertEqual(
            runtime.classification_sha256,
            PERSON_CLASSIFICATION_BINDINGS["kira"]["sha256"],
        )

    def test_unknown_source_binding_fails_closed(self) -> None:
        curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
        tampered = deepcopy(curriculum)
        tampered["modules"][0]["facts"][0]["source_ids"] = [
            "invented_source"
        ]
        with self.assertRaisesRegex(
            AdultHealthCurriculumError,
            "fact_source_unknown",
        ):
            validate_curriculum_asset(tampered)

    def test_unclassified_person_does_not_inherit_kira_adult_context(self) -> None:
        with self.assertRaisesRegex(
            AdultHealthCurriculumError,
            "no exact confirmed-adult classification",
        ):
            ConfirmedAdultHealthCurriculumRuntime.load("unclassified_person")

    def test_normal_kira_conversation_loop_loads_exact_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            loop = ConversationLoop(
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
            self.assertEqual(
                loop.adult_health_curriculum_load_audit["status"],
                "EXACT_CONFIRMED_ADULT_SOURCE_CONTEXT_READY",
            )
            context = loop._build_adult_health_curriculum_context(
                "How does the bladder and pelvic floor work?"
            )
            self.assertIsNotNone(context)
            assert context is not None
            self.assertIn(
                "urinary_bowel_pelvic_and_reproductive_health",
                context["selected_module_ids"],
            )

    def test_conversation_implementation_injects_private_system_context(self) -> None:
        source = (ROOT / "Core/conversation_loop.py").read_text(encoding="utf-8")
        self.assertIn(
            'call_audit["adult_health_curriculum_context"]',
            source,
        )
        self.assertIn(
            '"content": adult_health_prompt',
            source,
        )
        self.assertIn("adult_health_prompt,", source)
        self.assertNotIn("messages.append({\"role\": \"user\", \"content\": adult_health_prompt", source)
        self.assertIn(
            "do not turn a general anatomy, consent, contraception",
            source,
        )
        self.assertIn(
            "Current participants, feelings, actions, and plans require an exact supplied fact",
            source,
        )
        self.assertIn(
            "uncertainty, hesitation, freezing, silence, pulling away",
            source,
        )
        self.assertIn("is not permission to continue", source)

    def test_exact_ollama_payload_receives_context_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            loop = ConversationLoop(
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
            with patch(
                "requests.post",
                return_value=_FakeOllamaResponse(),
            ) as mocked_post:
                result = loop._call_ollama(
                    {
                        "user_message": "How are the bladder and vagina different?",
                        "memory_context": "",
                    }
                )
            self.assertEqual(result, "The systems are distinct.")
            request_payload = mocked_post.call_args.kwargs["json"]
            system_messages = [
                str(message["content"])
                for message in request_payload["messages"]
                if message["role"] == "system"
            ]
            curriculum_messages = [
                message
                for message in system_messages
                if message.startswith(
                    "CONFIRMED-ADULT SOURCE-BOUND HEALTH KNOWLEDGE CONTEXT:"
                )
            ]
            self.assertEqual(len(curriculum_messages), 1)
            self.assertIn("three_route_separation", loop._active_model_call_audit[-1]["adult_health_curriculum_context"]["fact_ids"])
            self.assertFalse(
                loop._active_model_call_audit[-1]["adult_health_curriculum_context"][
                    "learning_memory_created"
                ]
            )


if __name__ == "__main__":
    unittest.main()
