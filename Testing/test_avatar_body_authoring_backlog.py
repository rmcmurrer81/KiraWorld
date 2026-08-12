from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKLOG_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "authoring_backlogs"
    / "body_authoring_backlog_after_positive_proof_20260716.json"
)
REGISTRY_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "policies"
    / "candidate_identity_variant_registry.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AvatarBodyAuthoringBacklogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backlog = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))

    def test_backlog_is_bound_to_current_registry_and_not_a_queue(self) -> None:
        self.assertEqual(sha256(REGISTRY_PATH), self.backlog["candidate_identity_registry_sha256"])
        self.assertEqual("planning_only_not_queued", self.backlog["status"])
        self.assertFalse(self.backlog["queue_created"])
        self.assertFalse(self.backlog["body_created_by_this_backlog"])
        self.assertFalse(self.backlog["mind_created"])
        self.assertFalse(self.backlog["runtime_activation_allowed"])
        self.assertEqual(1, self.backlog["generation_policy"]["maximum_concurrent_body_builds"])
        self.assertFalse(self.backlog["generation_policy"]["start_bulk_authoring_now"])

    def test_priority_routes_preserve_adult_and_non_adult_separation(self) -> None:
        next_ids = {
            item["candidate_id"]
            for item in self.backlog["next_owner_reviewed_likeness_builds"]
        }
        self.assertIn("spider_gwen_spider_gwen_20260606_013325", next_ids)
        self.assertIn("robert_mcmurrer_presence_ai", next_ids)
        self.assertIn(
            "kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026",
            next_ids,
        )
        marinette = self.backlog["separate_non_adult_test_after_gwen"][0]
        self.assertEqual("non_adult_doll_safe", marinette["maturity_lane"])
        self.assertEqual("non_adult_doll_safe_topology", marinette["topology_lane"])
        self.assertFalse(marinette["adult_anatomy_allowed"])

    def test_all_five_generated_experts_are_adult_design_sheet_backlog(self) -> None:
        self.assertEqual(
            {
                "emily_carter_ai_and_computer_programming_expert_20260605_220651",
                "jessica_hale_robotics_engineer_20260611_041314",
                "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530",
                "ryan_hale_quantum_mechanics_expert_20260608_200749",
                "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
            },
            set(self.backlog["adult_generated_experts_need_owner_design_sheets"]),
        )

    def test_beth_and_whole_series_profiles_preserve_current_fail_closed_gates(self) -> None:
        beth = self.backlog["current_engineering_proof"][0]
        self.assertEqual(
            "r6_private_diagnostic_current_r7_unpromoted_garment_author_missing",
            beth["state"],
        )
        self.assertIn("retopology author", beth["next_gate"])

        later = {
            item["candidate_id"]: item
            for item in self.backlog["later_adult_canon_or_historical_builds"]
        }
        for candidate_id in (
            "blue_played_by_julia_stiles_blue_20260605_220748",
            "hannah_baxter_belle_hannah_baxter_20260605_214834",
        ):
            self.assertEqual(
                "whole_released_series_default_selected_source_expansion_required",
                later[candidate_id]["state"],
            )
            self.assertIn("whole released series", later[candidate_id]["next_gate"])

    def test_ruby_remains_blocked_until_visible_vessel_is_resolved(self) -> None:
        ruby = next(
            item
            for item in self.backlog["blocked_until_identity_choice"]
            if item["candidate_id"].startswith("ruby_supernatural_")
        )
        self.assertIn("visible_vessel_performer_blank", ruby["blockers"])
        self.assertIn("maturity_unresolved_for_body", ruby["blockers"])
        self.assertNotIn("profile_gender_conflict", ruby["blockers"])


if __name__ == "__main__":
    unittest.main()
