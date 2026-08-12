from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_positive_proof_gate import BACKLOG_PATH, REGISTRY_PATH  # noqa: E402
from Core.avatar_private_staging_planner import (  # noqa: E402
    ALLOWED_PRIVATE_JOB_TYPES,
    build_private_staging_dry_run_plan,
    evaluate_private_staging_unlock,
)


PILOT = Path(
    "Avatar/avatar_builder/candidate_sources/"
    "kira_single_body_quality_pilot_20260718"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_unlock() -> dict:
    return {
        "private_serial_staging_plan_allowed": True,
        "authoritative_batch_gate_unchanged": True,
        "quality": {
            "candidate_id": "exact_passing_inactive_body",
            "candidate_sha256": "a" * 64,
            "subject_id": "already_passed_subject_not_in_current_backlog",
        },
        "bindings": {
            "candidate_identity_registry": {
                "sha256": sha256(ROOT / REGISTRY_PATH),
            },
            "authoring_backlog": {
                "sha256": sha256(ROOT / BACKLOG_PATH),
            },
        },
    }


class AvatarPrivateStagingPlannerTests(unittest.TestCase):
    def test_current_kira_pilot_stays_visibly_locked(self) -> None:
        result = evaluate_private_staging_unlock(
            ROOT,
            PILOT / "candidate_manifest.json",
            PILOT / "rendered_visual_review.json",
        )

        self.assertFalse(result["private_serial_staging_plan_allowed"])
        self.assertEqual(result["status"], "locked_awaiting_one_exact_two_pass_body")
        self.assertIn(
            "no_exact_candidate_has_passed_single_body_two_pass_quality",
            result["failures"],
        )
        self.assertFalse(result["queue_created"])
        self.assertFalse(result["automatic_execution_started"])
        self.assertFalse(result["automatic_multi_profile_queue_allowed"])

    def test_retained_locked_report_binds_current_inputs(self) -> None:
        report = json.loads((ROOT / PILOT / "private_staging_unlock_report.json").read_text(encoding="utf-8"))
        bindings = report["exact_bindings"]

        self.assertEqual(report["status"], "locked_awaiting_one_exact_two_pass_body")
        self.assertEqual(report["dry_run_plan"]["jobs"], [])
        for name in (
            "candidate_manifest",
            "rendered_visual_review",
            "single_body_gate_report",
            "candidate_identity_registry",
            "authoring_backlog",
            "private_staging_policy",
        ):
            binding = bindings[name]
            self.assertEqual(binding["sha256"], sha256(ROOT / binding["path"]))

    def test_locked_evaluation_cannot_build_plan(self) -> None:
        evaluation = synthetic_unlock()
        evaluation["private_serial_staging_plan_allowed"] = False

        with self.assertRaises(ValueError):
            build_private_staging_dry_run_plan(ROOT, evaluation)

    def test_dry_run_contains_only_serial_private_allowlisted_jobs(self) -> None:
        plan = build_private_staging_dry_run_plan(ROOT, synthetic_unlock())

        self.assertTrue(plan["jobs"])
        self.assertEqual(plan["maximum_concurrent_private_jobs"], 1)
        previous = ""
        for job in plan["jobs"]:
            self.assertIn(job["job_type"], ALLOWED_PRIVATE_JOB_TYPES)
            self.assertEqual(job["depends_on"], [previous] if previous else [])
            self.assertEqual(job["state"], "dry_run_planned_not_queued")
            self.assertFalse(job["runtime_activation_allowed"])
            self.assertFalse(job["live_body_replacement_allowed"])
            self.assertFalse(job["public_export_allowed"])
            previous = job["job_id"]
        self.assertFalse(plan["queue_created"])
        self.assertFalse(plan["automatic_execution_started"])
        self.assertFalse(plan["automatic_multi_profile_queue_allowed"])

    def test_maturity_routes_preserve_adult_and_non_adult_separation(self) -> None:
        plan = build_private_staging_dry_run_plan(ROOT, synthetic_unlock())
        by_candidate = {job["candidate_id"]: job for job in plan["jobs"]}

        kira = by_candidate["kira_adult_avatar_build_variant_20260716"]
        self.assertEqual(kira["maturity_lane"], "adult")
        self.assertEqual(kira["topology_lane"], "confirmed_adult_topology")
        self.assertTrue(kira["adult_anatomy_allowed"])
        marinette = by_candidate[
            "marinette_main_series_doll_safe_avatar_variant_20260716"
        ]
        self.assertEqual(marinette["maturity_lane"], "non_adult_doll_safe")
        self.assertEqual(
            marinette["topology_lane"], "non_adult_doll_safe_topology"
        )
        self.assertFalse(marinette["adult_anatomy_allowed"])

    def test_registry_change_after_unlock_fails_closed(self) -> None:
        evaluation = synthetic_unlock()
        evaluation = copy.deepcopy(evaluation)
        evaluation["bindings"]["candidate_identity_registry"]["sha256"] = "0" * 64

        with self.assertRaisesRegex(ValueError, "registry changed"):
            build_private_staging_dry_run_plan(ROOT, evaluation)

    def test_unresolved_candidates_are_not_scheduled(self) -> None:
        plan = build_private_staging_dry_run_plan(ROOT, synthetic_unlock())
        scheduled = {job["candidate_id"] for job in plan["jobs"]}

        for blocked in (
            "cameron_terminator_cameron_terminator_20260605_225316",
            "mary_campbell_mary_campbell_20260605_224544",
            "peter_parker_spider_man_no_way_home_final_suit",
            "ruby_supernatural_ruby_supernatural_20260605_223416",
        ):
            self.assertNotIn(blocked, scheduled)


if __name__ == "__main__":
    unittest.main()
