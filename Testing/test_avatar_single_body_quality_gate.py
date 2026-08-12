from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_single_body_quality_gate import (  # noqa: E402
    REQUIRED_RENDER_VIEWS,
    REQUIRED_VISUAL_CRITERIA,
    evaluate_objective_body_gate,
    evaluate_rendered_visual_gate,
    evaluate_two_pass_body_quality,
)


PILOT = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_single_body_quality_pilot_20260718"
)


def load(name: str) -> dict:
    value = json.loads((PILOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def synthetic_passed_objective() -> dict:
    return {
        "passed": True,
        "candidate_id": "candidate_one",
        "candidate_sha256": "a" * 64,
        "render_bindings": {
            name: {"sha256": f"{index + 1:064x}"}
            for index, name in enumerate(REQUIRED_RENDER_VIEWS)
        },
    }


def synthetic_passed_review(objective: dict) -> dict:
    return {
        "schema_version": 1,
        "review_scope": "independent_rendered_candidate_review",
        "candidate_sha256": objective["candidate_sha256"],
        "reviewed_at": "2026-07-18T04:20:00-04:00",
        "reviewer": {
            "role": "codex_independent_visual_reviewer",
            "id": "test_reviewer",
        },
        "render_sha256": {
            name: objective["render_bindings"][name]["sha256"]
            for name in REQUIRED_RENDER_VIEWS
        },
        "criteria": {
            name: {"decision": "pass", "observation": "exact render inspected"}
            for name in REQUIRED_VISUAL_CRITERIA
        },
        "overall_decision": "pass",
        "owner_approval": False,
    }


class AvatarSingleBodyQualityGateTests(unittest.TestCase):
    def test_exact_kira_pilot_is_rejected_for_objective_defects(self) -> None:
        result = evaluate_objective_body_gate(ROOT, load("candidate_manifest.json"))

        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "objective_blocked")
        failures = set(result["failures"])
        for expected in (
            "candidate_rig_motion_stability_not_hash_attested",
            "body_boundary_loops_not_fully_reviewed",
            "dynamic_ground_contact_not_proven",
            "oversized_unclassified_geometry_present",
            "renderable_geometry_has_missing_materials",
            "eye_material_visual_realism_not_proven",
            "eye_eyelid_control_pair_missing",
            "eye_blink_control_pair_missing",
            "eye_socket_fit_not_measurement_proven",
            "subject_specific_mesh_authorship_not_proven",
        ):
            self.assertIn(expected, failures)
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertFalse(result["automatic_multi_profile_queue_allowed"])

    def test_pilot_two_pass_report_stays_locked(self) -> None:
        result = evaluate_two_pass_body_quality(
            ROOT,
            load("candidate_manifest.json"),
            load("rendered_visual_review.json"),
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "two_pass_quality_blocked")
        self.assertFalse(result["rendered_visual"]["passed"])
        self.assertFalse(result["owner_approval_inferred"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertFalse(result["automatic_multi_profile_queue_allowed"])
        self.assertEqual(
            result["authoritative_batch_gate_unchanged"],
            "avatar_two_distinct_subject_autobuild_gate_v2",
        )

    def test_pilot_distinguishes_raw_index_splits_from_welded_surface(self) -> None:
        result = evaluate_objective_body_gate(ROOT, load("candidate_manifest.json"))
        body = result["geometry"]["primary_body"]

        self.assertEqual(body["raw_index_surface_island_count"], 49)
        self.assertEqual(body["surface_island_count"], 1)
        self.assertEqual(body["boundary_edge_count"], 172)
        self.assertEqual(body["boundary_loop_count"], 3)
        self.assertNotIn(
            "body_surface_is_not_one_continuous_island", result["failures"]
        )
        self.assertIn("body_boundary_loops_not_fully_reviewed", result["failures"])

    def test_render_hash_tamper_fails_closed(self) -> None:
        manifest = copy.deepcopy(load("candidate_manifest.json"))
        manifest["renders"]["neutral_front"]["sha256"] = "0" * 64

        result = evaluate_objective_body_gate(ROOT, manifest)

        self.assertIn("render_neutral_front_sha256_mismatch", result["failures"])
        self.assertFalse(result["passed"])

    def test_visual_pass_requires_objective_pass_first(self) -> None:
        objective = synthetic_passed_objective()
        review = synthetic_passed_review(objective)
        objective["passed"] = False

        result = evaluate_rendered_visual_gate(objective, review)

        self.assertFalse(result["passed"])
        self.assertIn(
            "objective_pass_must_succeed_before_visual_pass", result["failures"]
        )

    def test_visual_gate_pass_does_not_infer_approval_or_release_queue(self) -> None:
        objective = synthetic_passed_objective()
        review = synthetic_passed_review(objective)

        result = evaluate_rendered_visual_gate(objective, review)

        self.assertTrue(result["passed"])
        self.assertFalse(result["owner_approval_inferred"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertFalse(result["automatic_multi_profile_queue_allowed"])

    def test_one_visual_rejection_blocks_the_entire_visual_pass(self) -> None:
        objective = synthetic_passed_objective()
        review = synthetic_passed_review(objective)
        review["criteria"]["eyes_seated_in_sockets"] = {
            "decision": "reject",
            "observation": "visible sclera protrusion",
        }

        result = evaluate_rendered_visual_gate(objective, review)

        self.assertFalse(result["passed"])
        self.assertIn(
            "visual_criterion_not_passed:eyes_seated_in_sockets",
            result["failures"],
        )

    def test_visual_review_cannot_self_create_owner_approval(self) -> None:
        objective = synthetic_passed_objective()
        review = synthetic_passed_review(objective)
        review["owner_approval"] = True

        result = evaluate_rendered_visual_gate(objective, review)

        self.assertFalse(result["passed"])
        self.assertIn(
            "visual_review_must_not_self_create_owner_approval", result["failures"]
        )


if __name__ == "__main__":
    unittest.main()
