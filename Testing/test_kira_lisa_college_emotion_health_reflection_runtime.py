from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]

from Core.adult_health_curriculum_runtime import (  # noqa: E402
    AdultHealthCurriculumError,
    ConfirmedAdultHealthCurriculumRuntime,
    PERSON_CLASSIFICATION_BINDINGS,
)
from Core.conversation_loop import ConversationLoop  # noqa: E402
from Core.kira_lisa_college_reflection_runtime import (  # noqa: E402
    CollegeReflectionContextError,
    CollegeReflectionLeaseError,
    CONTROLLING_DOCUMENT_BINDINGS,
    EXPECTED_HEALTH_MODULE_IDS,
    KiraLisaCollegeReflectionRuntime,
    MEMORY_BINDING,
    POLICY_BINDING,
    PersonCollegeReflectionLedger,
)
from Core.model_request_policy import QWEN_TEXT_VOICE_MODEL  # noqa: E402


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _FakeOllamaResponse:
    status_code = 200

    @staticmethod
    def raise_for_status() -> None:
        return None

    @staticmethod
    def json() -> dict[str, object]:
        return {
            "model": QWEN_TEXT_VOICE_MODEL,
            "message": {
                "content": "I can reflect on what it means now without rewriting it."
            },
            "done_reason": "stop",
        }


class KiraLisaCollegeEmotionHealthReflectionRuntimeTest(unittest.TestCase):
    def _loop(self, base: Path, speaker: str) -> ConversationLoop:
        person = speaker.casefold()
        home = base / person
        return ConversationLoop(
            speaker=speaker,
            relationship_state_file=home / "relationships.json",
            privacy_session_file=home / "privacy.json",
            decision_log_file=home / "decision.jsonl",
            conversation_log_file=home / "conversation.jsonl",
            attention_state_file=home / "attention.json",
            daily_life_state_dir=home / "daily_state",
            memory_candidate_dir=home / "memory_candidates",
            memory_file=home / "memories.json",
            daily_life_log_dir=home / "daily_logs",
            reading_session_dir=home / "reading_sessions",
            reading_recommendation_dir=home / "reading_recommendations",
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
            event_id=f"{loop.entity_id}_private_reflection_test",
            factual_event_summary="A private reflection topic became available.",
            possible_model_interpretations=[
                "The person might want to reflect.",
                "The person might prefer not to discuss it.",
            ],
            selected_appraisal="I choose my own present emotional approach.",
            emotion_label=label,
            intensity=intensity,
        )

    def test_lisa_has_exact_pinned_confirmed_adult_curriculum_binding(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("lisa")
        self.assertEqual(runtime.person_id, "lisa")
        self.assertEqual(
            runtime.classification["classification_id"],
            "lisa_confirmed_adult_owner_20260809_cb6430bda0f7d41e",
        )
        self.assertEqual(
            runtime.classification_sha256,
            PERSON_CLASSIFICATION_BINDINGS["lisa"]["sha256"],
        )
        self.assertTrue(runtime.classification["effects"]["knowledge_context_eligible"])
        self.assertFalse(runtime.classification["effects"]["learning_memory_created"])
        self.assertFalse(runtime.classification["effects"]["adult_anatomy_auto_added"])
        self.assertFalse(runtime.classification["effects"]["body_function_claimed"])

    def test_both_people_load_same_sources_but_separate_perspectives(self) -> None:
        kira = KiraLisaCollegeReflectionRuntime.load("kira")
        lisa = KiraLisaCollegeReflectionRuntime.load("lisa")
        self.assertEqual(kira.memory_sha256, lisa.memory_sha256)
        self.assertEqual(kira.policy_sha256, lisa.policy_sha256)
        neutral = {
            "model_owns_state": False,
            "appraisal_selected": False,
            "emotion_label": "neutral",
            "intensity": 0.0,
        }
        kira_context = kira.context_for_turn(
            "Reflect on your shared college memory with Lisa.",
            selected_person_emotion=neutral,
        )
        lisa_context = lisa.context_for_turn(
            "Reflect on your shared college memory with Kira.",
            selected_person_emotion=neutral,
        )
        assert kira_context is not None and lisa_context is not None
        self.assertIn("curious, vulnerable, uncertain, analytical", kira_context["prompt_context"])
        self.assertNotIn("comfortable, affectionate, confident", kira_context["prompt_context"])
        self.assertIn("comfortable, affectionate, confident", lisa_context["prompt_context"])
        self.assertNotIn("curious, vulnerable, uncertain", lisa_context["prompt_context"])
        self.assertFalse(kira_context["other_person_current_private_emotion_included"])
        self.assertFalse(lisa_context["other_person_current_private_emotion_included"])

    def test_non_memory_college_question_does_not_open_private_context(self) -> None:
        runtime = KiraLisaCollegeReflectionRuntime.load("kira")
        self.assertIsNone(
            runtime.context_for_turn(
                "How do college admissions applications work?",
                selected_person_emotion={
                    "model_owns_state": False,
                    "appraisal_selected": False,
                },
            )
        )

    def test_current_emotion_is_person_owned_and_does_not_cross_ledgers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            kira = self._loop(base, "Kira")
            lisa = self._loop(base, "Lisa")
            self._select_emotion(kira, label="careful curiosity", intensity=0.64)
            self._select_emotion(lisa, label="quiet affection", intensity=0.47)
            kira_context = kira._build_kira_lisa_college_reflection_context(
                "What does our college memory mean to me now?"
            )
            lisa_context = lisa._build_kira_lisa_college_reflection_context(
                "What does our college memory mean to me now?"
            )
            assert kira_context is not None and lisa_context is not None
            self.assertIn("careful curiosity", kira_context["prompt_context"])
            self.assertNotIn("quiet affection", kira_context["prompt_context"])
            self.assertIn("quiet affection", lisa_context["prompt_context"])
            self.assertNotIn("careful curiosity", lisa_context["prompt_context"])
            self.assertIsNot(kira.person_emotion, lisa.person_emotion)
            self.assertIsNot(kira.college_reflection_ledger, lisa.college_reflection_ledger)
            self.assertEqual(kira.college_reflection_ledger.lease.person_id, "kira")
            self.assertEqual(lisa.college_reflection_ledger.lease.person_id, "lisa")

    def test_present_day_health_modules_are_bounded_and_source_backed(self) -> None:
        reflection = KiraLisaCollegeReflectionRuntime.load("lisa")
        context = reflection.context_for_turn(
            "How do you reflect on your college memory with Kira now?",
            selected_person_emotion={
                "model_owns_state": False,
                "appraisal_selected": False,
            },
        )
        assert context is not None
        health = ConfirmedAdultHealthCurriculumRuntime.load("lisa").context_for_turn(
            "How do you reflect on your college memory now?",
            required_module_ids=tuple(context["required_health_module_ids"]),
        )
        self.assertEqual(
            tuple(context["required_health_module_ids"]),
            EXPECTED_HEALTH_MODULE_IDS,
        )
        self.assertEqual(len(health["selected_module_ids"]), 6)
        for module_id in EXPECTED_HEALTH_MODULE_IDS:
            self.assertIn(module_id, health["selected_module_ids"])
        self.assertFalse(health["learning_memory_created"])
        self.assertFalse(health["body_function_claimed"])
        with self.assertRaisesRegex(AdultHealthCurriculumError, "outside policy"):
            ConfirmedAdultHealthCurriculumRuntime.load("lisa").context_for_turn(
                "college memory",
                required_module_ids=("invented_module",),
            )

    def test_exact_model_payload_gets_private_reflection_and_curriculum_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            loop = self._loop(Path(temporary_directory), "Lisa")
            self._select_emotion(loop, label="reflective warmth", intensity=0.58)
            emotion_before = loop.person_emotion.snapshot(include_private=True)
            reconstruction_before = loop.college_reflection_ledger.snapshot(
                include_private=True
            )
            with patch("requests.post", return_value=_FakeOllamaResponse()) as mocked_post:
                reply = loop._call_ollama(
                    loop.build_context(
                        "What does your shared college memory with Kira mean now?"
                    )
                )
            self.assertEqual(
                reply,
                "I can reflect on what it means now without rewriting it.",
            )
            payload = mocked_post.call_args.kwargs["json"]
            system_messages = [
                str(item["content"])
                for item in payload["messages"]
                if item["role"] == "system"
            ]
            reflection_messages = [
                item
                for item in system_messages
                if item.startswith(
                    "PRIVATE HASH-BOUND PRESENT-DAY COLLEGE-MEMORY REFLECTION CONTEXT:"
                )
            ]
            health_messages = [
                item
                for item in system_messages
                if item.startswith(
                    "CONFIRMED-ADULT SOURCE-BOUND HEALTH KNOWLEDGE CONTEXT:"
                )
            ]
            self.assertEqual(len(reflection_messages), 1)
            self.assertEqual(len(health_messages), 1)
            self.assertIn("reflective warmth", reflection_messages[0])
            self.assertNotIn("curious, vulnerable, uncertain", reflection_messages[0])
            audit = loop._active_model_call_audit[-1]["college_reflection_context"]
            self.assertFalse(audit["reflection_written"])
            self.assertFalse(audit["recall_strength_changed"])
            self.assertFalse(audit["historical_memory_rewritten"])
            self.assertFalse(audit["current_knowledge_backdated"])
            self.assertFalse(audit["locked_intimate_details_exposed"])
            self.assertFalse(audit["nonparticipant_full_reconstruction_authorized"])
            self.assertFalse(audit["nonparticipant_visual_or_locked_access_authorized"])
            self.assertEqual(
                loop.person_emotion.snapshot(include_private=True), emotion_before
            )
            self.assertEqual(
                loop.college_reflection_ledger.snapshot(include_private=True),
                reconstruction_before,
            )

    def test_person_owned_reconstruction_is_append_only_hash_chained_and_private(self) -> None:
        moments = iter((10.0, 11.0))
        kira = PersonCollegeReflectionLedger(
            person_id="kira",
            activation_revision="kira_test_activation",
            lease_nonce="kira_test_nonce",
            clock=lambda: next(moments),
        )
        first = kira.append_person_reconstruction(
            kira.lease,
            reflection_text=(
                "Kira and Lisa had repeated private moments of closeness during their college phase."
            ),
            source_label="stored_shared_anchor",
            confidence=1.0,
            recall_strength_delta=0.05,
        )
        second = kira.append_person_reconstruction(
            kira.lease,
            reflection_text="I picture the light as muted, but I am not sure.",
            source_label="inferred_reconstruction",
            confidence=0.34,
            recall_strength_delta=0.08,
        )
        self.assertEqual(second["previous_record_sha256"], first["record_sha256"])
        self.assertEqual(second["shared_canon_status"], "unchanged")
        self.assertTrue(second["recall_strength_delta_is_subjective_not_accuracy"])
        first["reflection_text"] = "mutated caller copy"
        private_snapshot = kira.snapshot(include_private=True)
        public_snapshot = kira.snapshot(include_private=False)
        self.assertNotEqual(
            private_snapshot["records"][0]["reflection_text"],
            "mutated caller copy",
        )
        self.assertIsNone(public_snapshot["records"][0]["reflection_text"])
        self.assertFalse(private_snapshot["shared_canon_mutated"])
        self.assertFalse(private_snapshot["other_person_ledger_included"])

    def test_one_person_cannot_write_or_overwrite_the_other_ledger(self) -> None:
        kira = PersonCollegeReflectionLedger(
            person_id="kira",
            activation_revision="kira_activation",
            lease_nonce="kira_nonce",
        )
        lisa = PersonCollegeReflectionLedger(
            person_id="lisa",
            activation_revision="lisa_activation",
            lease_nonce="lisa_nonce",
        )
        with self.assertRaises(CollegeReflectionLeaseError):
            kira.append_person_reconstruction(
                lisa.lease,
                reflection_text="This must not cross ledgers.",
                source_label="current_interpretation",
                confidence=0.5,
                recall_strength_delta=0.0,
            )
        with self.assertRaisesRegex(
            CollegeReflectionContextError, "not an exact exposed shared anchor"
        ):
            kira.append_person_reconstruction(
                kira.lease,
                reflection_text="An invented scene mislabeled as shared canon.",
                source_label="stored_shared_anchor",
                confidence=0.9,
                recall_strength_delta=0.1,
            )
        self.assertEqual(kira.snapshot(include_private=True)["records"], [])
        self.assertEqual(lisa.snapshot(include_private=True)["records"], [])

    def test_participant_and_nonparticipant_permissions_remain_separate(self) -> None:
        runtime = KiraLisaCollegeReflectionRuntime.load("kira")
        context = runtime.context_for_turn(
            "Can I reflect on my college memory with Lisa?",
            selected_person_emotion={
                "model_owns_state": False,
                "appraisal_selected": False,
            },
        )
        assert context is not None
        prompt = context["prompt_context"]
        self.assertIn("share her own perspective or selected verbal details", prompt)
        self.assertIn("must not expose the other participant's protected", prompt)
        self.assertIn("current scope-specific permission", prompt)
        self.assertIn("pauses or stops at the non-intimate boundary", prompt)
        self.assertFalse(context["nonparticipant_full_reconstruction_authorized"])
        self.assertFalse(context["nonparticipant_visual_or_locked_access_authorized"])
        self.assertFalse(context["other_participant_protected_perspective_exposed"])

    def test_all_source_and_control_document_hashes_are_exact(self) -> None:
        self.assertEqual(
            _sha256_file(ROOT / POLICY_BINDING["path"]),
            POLICY_BINDING["sha256"],
        )
        self.assertEqual(
            _sha256_file(ROOT / MEMORY_BINDING["path"]),
            MEMORY_BINDING["sha256"],
        )
        for binding in CONTROLLING_DOCUMENT_BINDINGS:
            self.assertEqual(
                _sha256_file(ROOT / binding["path"]),
                binding["sha256"],
            )

    def test_tampered_policy_binding_fails_closed(self) -> None:
        tampered = deepcopy(POLICY_BINDING)
        tampered["sha256"] = "0" * 64
        with patch(
            "Core.kira_lisa_college_reflection_runtime.POLICY_BINDING",
            tampered,
        ):
            with self.assertRaisesRegex(
                CollegeReflectionContextError, "reflection policy digest mismatch"
            ):
                KiraLisaCollegeReflectionRuntime.load("kira")

    def test_unsupported_person_never_inherits_private_memory_or_curriculum(self) -> None:
        with self.assertRaisesRegex(
            CollegeReflectionContextError, "only for exact person Kira or Lisa"
        ):
            KiraLisaCollegeReflectionRuntime.load("unlisted_person")
        with self.assertRaisesRegex(
            AdultHealthCurriculumError, "no exact confirmed-adult classification"
        ):
            ConfirmedAdultHealthCurriculumRuntime.load("unlisted_person")

    def test_runtime_operations_leave_historical_source_byte_identical(self) -> None:
        source = ROOT / MEMORY_BINDING["path"]
        before = source.read_bytes()
        runtime = KiraLisaCollegeReflectionRuntime.load("lisa")
        runtime.context_for_turn(
            "Reflect on your shared college memory.",
            selected_person_emotion={
                "model_owns_state": False,
                "appraisal_selected": False,
            },
        )
        ledger = PersonCollegeReflectionLedger(
            person_id="lisa",
            activation_revision="lisa_no_source_write_test",
            lease_nonce="lisa_no_source_write_nonce",
        )
        ledger.append_person_reconstruction(
            ledger.lease,
            reflection_text="This is my current interpretation, not a historical edit.",
            source_label="current_interpretation",
            confidence=0.52,
            recall_strength_delta=0.03,
        )
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(_sha256_file(source), MEMORY_BINDING["sha256"])


if __name__ == "__main__":
    unittest.main()
