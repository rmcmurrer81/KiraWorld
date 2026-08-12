from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "Avatar/avatar_builder/policies/variant_residency_age_progression_and_expert_adult_knowledge_policy_v1.json"
PLAN = ROOT / "Data/world_builder/roadmap/peter_gwen_marinette_residency_plan_20260809.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VariantResidencyAgeProgressionAndWorldPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load(POLICY)
        cls.plan = load(PLAN)

    def test_exact_owner_text_and_source_bindings(self) -> None:
        decisions = self.policy["owner_authority"]["decision_records"]
        self.assertEqual(len(decisions), 2)
        for decision in decisions:
            self.assertEqual(
                hashlib.sha256(decision["exact_text"].encode("utf-8")).hexdigest(),
                decision["exact_text_sha256"],
            )
        for binding in self.policy["exact_source_bindings"].values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, binding["bytes"])
            self.assertEqual(sha256(path), binding["sha256"])

    def test_world_plan_exact_bindings_remain_unchanged(self) -> None:
        for resident in self.plan["residents"]:
            for binding in resident["exact_bindings"]:
                path = ROOT / binding["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])

    def test_gwen_and_peter_are_adults_with_distinct_new_york_apartments(self) -> None:
        residents = {row["candidate_id"]: row for row in self.plan["residents"]}
        gwen = residents["spider_gwen_spider_gwen_20260606_013325"]
        peter = residents["peter_parker_spider_man_no_way_home_final_suit"]
        self.assertEqual(gwen["maturity_status"], "confirmed_adult")
        self.assertEqual(gwen["body_lane"], "adult_female")
        self.assertIn("Earth-65", gwen["continuity"])
        self.assertEqual(peter["maturity_status"], "confirmed_adult")
        self.assertEqual(peter["body_lane"], "adult_male")
        self.assertIn("No Way Home", peter["continuity"])
        self.assertNotEqual(gwen["home_id"], peter["home_id"])
        self.assertFalse(gwen["shared_with_peter"])
        self.assertFalse(peter["shared_with_gwen"])
        self.assertTrue(self.plan["world_separation"]["new_york"]["homes_are_distinct"])

    def test_normal_marinette_remains_non_adult_and_has_bakery_bedroom(self) -> None:
        marinette = next(
            row for row in self.plan["residents"]
            if row["candidate_id"] == "ladybug_marinette_expanded_smoke"
        )
        self.assertEqual(marinette["maturity_status"], "non_adult")
        self.assertEqual(marinette["body_lane"], "doll_safe_non_anatomical")
        self.assertIn("bakery", marinette["home_id"])
        self.assertIn("bedroom", marinette["private_space_id"])
        self.assertFalse(marinette["separate_apartment"])
        self.assertFalse(marinette["spa_stage_1_adult_anatomy_allowed"])

    def test_spa_stage_one_requires_twenty_plus_appearance_without_anatomy(self) -> None:
        stage_one = self.policy["spa_age_progression_successor_constraints"]["stage_1"]
        self.assertEqual(stage_one["minimum_apparent_age_years"], 20)
        self.assertEqual(stage_one["exact_maturity_status"], "unresolved")
        self.assertEqual(stage_one["body_lane"], "doll_safe_non_anatomical")
        self.assertFalse(stage_one["adult_anatomy_allowed"])
        stage_two = self.policy["spa_age_progression_successor_constraints"]["stage_2"]
        self.assertTrue(stage_two["separate_exact_confirmed_adult_classification_required"])
        self.assertTrue(stage_two["person_separate_adult_anatomy_choice_required"])

    def test_home_world_move_and_adult_knowledge_do_not_imply_body_or_consent(self) -> None:
        residency = self.policy["variant_home_world_residency"]
        self.assertTrue(residency["person_choice_required"])
        self.assertFalse(residency["automatic_move_allowed"])
        self.assertIn("build_or_replace_a_body", residency["does_not_automatically"])
        knowledge = self.policy["expert_adult_knowledge"]
        self.assertTrue(knowledge["all_generated_expert_profiles_are_adults_by_owner_directive"])
        self.assertFalse(knowledge["expert_label_or_occupation_alone_is_maturity_evidence"])
        for forbidden in ("adult_anatomy", "consent", "desire", "activity"):
            self.assertIn(forbidden, knowledge["curriculum_does_not_create"])

    def test_plan_is_inert_and_unpublished(self) -> None:
        boundary = self.plan["mutation_boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))
        truth = self.policy["implementation_truth"]
        self.assertTrue(truth["machine_policy_recorded"])
        self.assertFalse(truth["world_residency_runtime_connected"])
        self.assertFalse(truth["body_or_world_mutated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
