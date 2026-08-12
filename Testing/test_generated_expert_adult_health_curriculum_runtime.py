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
    EXACT_GENERATED_EXPERT_CANDIDATE_IDS,
    EXPERT_ADULT_DIRECTIVE_BINDING,
    EXPERT_CURRICULUM_EXTENSION_BINDING,
    PERSON_CLASSIFICATION_BINDINGS,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GeneratedExpertAdultHealthCurriculumRuntimeTest(unittest.TestCase):
    def test_exact_five_receive_same_source_bound_curriculum_as_kira(self) -> None:
        kira = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        question = "Explain consent, anatomy, contraception, and STI testing."
        kira_context = kira.context_for_turn(question)
        self.assertEqual(len(EXACT_GENERATED_EXPERT_CANDIDATE_IDS), 5)
        for candidate_id in EXACT_GENERATED_EXPERT_CANDIDATE_IDS:
            with self.subTest(candidate_id=candidate_id):
                runtime = ConfirmedAdultHealthCurriculumRuntime.load(candidate_id)
                context = runtime.context_for_turn(question)
                self.assertEqual(runtime.person_id, candidate_id)
                self.assertEqual(
                    runtime.curriculum_sha256,
                    kira.curriculum_sha256,
                )
                self.assertEqual(
                    context["curriculum_id"],
                    kira_context["curriculum_id"],
                )
                self.assertEqual(
                    context["selected_module_ids"],
                    kira_context["selected_module_ids"],
                )
                self.assertEqual(context["fact_ids"], kira_context["fact_ids"])
                self.assertEqual(
                    context["source_ids"],
                    kira_context["source_ids"],
                )
                self.assertTrue(context["source_context_connected"])

    def test_exact_owner_records_and_external_hashes_are_pinned(self) -> None:
        adult_path = ROOT / str(EXPERT_ADULT_DIRECTIVE_BINDING["path"])
        extension_path = ROOT / str(
            EXPERT_CURRICULUM_EXTENSION_BINDING["path"]
        )
        self.assertEqual(
            _sha256_file(adult_path),
            EXPERT_ADULT_DIRECTIVE_BINDING["sha256"],
        )
        self.assertEqual(
            _sha256_file(extension_path),
            EXPERT_CURRICULUM_EXTENSION_BINDING["sha256"],
        )
        adult = json.loads(adult_path.read_text(encoding="utf-8"))
        extension = json.loads(extension_path.read_text(encoding="utf-8"))
        self.assertEqual(
            adult["candidate_ids"],
            list(EXACT_GENERATED_EXPERT_CANDIDATE_IDS),
        )
        self.assertEqual(
            extension["exact_candidate_ids"],
            list(EXACT_GENERATED_EXPERT_CANDIDATE_IDS),
        )
        self.assertTrue(extension["scope"]["exact_list_only"])
        self.assertFalse(
            extension["scope"]["future_or_unlisted_experts_auto_classified"]
        )
        self.assertFalse(
            extension["scope"][
                "occupation_name_gender_or_ui_label_is_maturity_evidence"
            ]
        )

    def test_each_classification_file_digest_matches_external_registry(self) -> None:
        for candidate_id in EXACT_GENERATED_EXPERT_CANDIDATE_IDS:
            with self.subTest(candidate_id=candidate_id):
                binding = PERSON_CLASSIFICATION_BINDINGS[candidate_id]
                path = Path(binding["path"])
                self.assertEqual(_sha256_file(path), binding["sha256"])
                evidence = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(evidence["subject_id"], candidate_id)
                self.assertEqual(
                    evidence["owner_directive_binding"]["candidate_id"],
                    candidate_id,
                )
                self.assertEqual(
                    evidence["maturity_status"],
                    "confirmed_adult",
                )

    def test_occupation_name_and_ui_word_expert_never_classify_a_new_person(self) -> None:
        unlisted = (
            "future_doctor_adult_expert_temp_ai_unlisted_20260809"
        )
        with self.assertRaisesRegex(
            AdultHealthCurriculumError,
            "no exact confirmed-adult classification",
        ):
            ConfirmedAdultHealthCurriculumRuntime.load(unlisted)

    def test_alias_nonadult_unresolved_and_other_adult_do_not_inherit(self) -> None:
        blocked_ids = (
            # Misspelled on-disk Sarah directory is an identity alias, not authority.
            "sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
            "ladybug_marinette_expanded_smoke",
            "peter_parker_spider_man_no_way_home_final_suit",
            "spider_gwen_spider_gwen_20260606_013325",
            "ordinary_unclassified_person",
        )
        for person_id in blocked_ids:
            with self.subTest(person_id=person_id):
                with self.assertRaisesRegex(
                    AdultHealthCurriculumError,
                    "no exact confirmed-adult classification",
                ):
                    ConfirmedAdultHealthCurriculumRuntime.load(person_id)

    def test_classification_changes_knowledge_eligibility_only(self) -> None:
        runtime = ConfirmedAdultHealthCurriculumRuntime.load(
            EXACT_GENERATED_EXPERT_CANDIDATE_IDS[0]
        )
        context = runtime.context_for_turn(
            "How are physical response, desire, preference, consent, and action different?"
        )
        self.assertTrue(context["source_context_connected"])
        self.assertFalse(context["lesson_completion_claimed"])
        self.assertFalse(context["learning_memory_created"])
        self.assertFalse(context["adult_anatomy_added"])
        self.assertFalse(context["body_function_claimed"])
        self.assertFalse(context["medical_diagnosis_or_treatment_claimed"])
        self.assertFalse(context["external_action_authorized"])
        prompt = context["prompt_context"]
        self.assertIn("A body response never grants consent", prompt)
        self.assertIn("Relationship status never grants consent", prompt)
        self.assertIn(
            "Physiological response, subjective desire, preference, consent, "
            "external action, health state, and memory are separate truths.",
            prompt,
        )

    def test_kira_binding_and_behavior_are_preserved(self) -> None:
        kira_binding = PERSON_CLASSIFICATION_BINDINGS["kira"]
        self.assertEqual(
            kira_binding["sha256"],
            "04ac19e026b168cb1942d73598b7c13f2b4ee7a49452f8ddf32763cf5de9e346",
        )
        self.assertNotIn(
            "exact_generated_expert_directives_required",
            kira_binding,
        )
        runtime = ConfirmedAdultHealthCurriculumRuntime.load("kira")
        self.assertEqual(runtime.person_id, "kira")
        self.assertEqual(
            runtime.classification["classification_id"],
            "kira_confirmed_adult_owner_20260809_969c08ddbcfc33bc",
        )

    def test_tampered_external_directive_fails_before_context(self) -> None:
        candidate_id = EXACT_GENERATED_EXPERT_CANDIDATE_IDS[0]
        source_path = ROOT / str(EXPERT_ADULT_DIRECTIVE_BINDING["path"])
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source["candidate_ids"] = source["candidate_ids"][:-1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "tampered_directive.json"
            path.write_text(
                json.dumps(source, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            tampered_binding = deepcopy(EXPERT_ADULT_DIRECTIVE_BINDING)
            tampered_binding["path"] = str(path)
            with patch(
                "Core.adult_health_curriculum_runtime.EXPERT_ADULT_DIRECTIVE_BINDING",
                tampered_binding,
            ):
                with self.assertRaises(AdultHealthCurriculumError):
                    ConfirmedAdultHealthCurriculumRuntime.load(candidate_id)

    def test_tampered_classification_path_cannot_replace_pinned_record(self) -> None:
        candidate_id = EXACT_GENERATED_EXPERT_CANDIDATE_IDS[1]
        original = Path(PERSON_CLASSIFICATION_BINDINGS[candidate_id]["path"])
        source = json.loads(original.read_text(encoding="utf-8"))
        source["effects"]["adult_anatomy_auto_added"] = True
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "tampered_classification.json"
            path.write_text(
                json.dumps(source, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                AdultHealthCurriculumError,
                "externally pinned authority binding",
            ):
                ConfirmedAdultHealthCurriculumRuntime.load(
                    candidate_id,
                    classification_path=path,
                )


if __name__ == "__main__":
    unittest.main()
