#!/usr/bin/env python3
"""Fail-closed checks for the additive R23 repair-method boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v3.json"
BINDING = ROOT / "Avatar/avatar_builder/body_systems/modeling_acceptance_plan_binding_v4.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KiraR23Attempt08RepairBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load(CONTRACT)
        cls.binding = load(BINDING)

    def test_all_exact_bindings_resolve(self):
        rows = [self.contract["inherits"], *self.contract["evidence"].values()]
        rows.extend(
            [
                self.binding["inherits"],
                self.binding["body_authoring_contract"],
                self.binding["system_truth_note"],
                *self.binding["evidence"].values(),
            ]
        )
        for row in rows:
            with self.subTest(path=row["path"]):
                path = ROOT / row["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, row["bytes"])
                self.assertEqual(digest(path), row["sha256"])

    def test_attempt08_and_focused_diagnostic_fail_closed(self):
        attempt = load(ROOT / self.binding["evidence"]["attempt08"]["path"])
        focused = load(ROOT / self.binding["evidence"]["focused_localization"]["path"])
        self.assertEqual(attempt["status"], "NO_VARIANT_PASSED_ALL_LOCALIZED_REPAIRABLE_GATES")
        self.assertIsNone(attempt["selected_variant_id"])
        self.assertEqual(attempt["stage_c_full_pose_results"], [])
        self.assertEqual(focused["status"], "READ_ONLY_EXACT_LOCALIZATION_NOT_ACCEPTANCE")
        self.assertEqual(focused["neutral"]["patch_involving_pair_count"], 47)
        self.assertEqual(focused["neutral"]["seam_normal_failure_count_at_0_7"], 34)
        self.assertEqual(focused["operations"]["blend_saved"], False)
        self.assertEqual(focused["operations"]["render_performed"], False)

    def test_carrier_annulus_never_reaches_pose_stage(self):
        row = self.binding["evidence"]["carrier_annulus_attempt01"]
        evidence = load(ROOT / row["path"])
        self.assertEqual(evidence["status"], row["required_status"])
        self.assertEqual(len(evidence["stage_a"]), 9)
        self.assertEqual(len(evidence["stage_b_exact_neutral"]), 4)
        self.assertEqual(evidence["stage_c_exact_poses"], [])
        self.assertIsNone(evidence["selected_variant_id"])
        self.assertFalse(evidence["all_added_gates_passed"])
        self.assertTrue(evidence["immutability"]["unchanged"])
        self.assertFalse(evidence["operations"]["blend_saved"])
        self.assertFalse(evidence["operations"]["render_performed"])
        for variant in evidence["stage_a"]:
            self.assertFalse(variant["hard_checks"]["seam_continuity"])
            self.assertFalse(variant["hard_checks"]["patch_weight_gradient_nonregression"])
            self.assertFalse(variant["hard_checks"]["uv_geometry_and_exact_seam_choice"])
            self.assertFalse(variant["hard_checks"]["new_edge_stretch_at_or_below_1_35"])

    def test_generic_contract_uses_exact_mapping_and_per_edge_gates(self):
        mapping = self.contract["exact_mapping"]
        seam = self.contract["seam_and_orientation_gates"]
        pose = self.contract["rig_and_pose_gates"]
        self.assertTrue(mapping["saved_local_global_creation_ordinal_mapping_required"])
        self.assertTrue(mapping["numeric_face_or_vertex_range_classification_forbidden"])
        self.assertEqual(seam["required_seam_edge_count"], 91)
        self.assertEqual(seam["minimum_direct_patch_retained_normal_dot_per_edge"], 0.7)
        self.assertFalse(seam["whole_patch_flip_allowed"])
        self.assertEqual(pose["maximum_new_patch_edge_stretch_ratio_each_required_pose"], 1.35)
        self.assertTrue(pose["candidate_source_seam_nonregression_required"])
        self.assertFalse(pose["raw_weight_delta_envelope_is_movement_pass"])

    def test_no_implementation_or_approval_claim_is_minted(self):
        for values in (
            self.contract["implementation_truth"],
            self.binding["implementation_state"],
        ):
            for key, value in values.items():
                if key.endswith("exists") or key.endswith("implemented") or key.endswith("connected") or key.endswith("accepted"):
                    self.assertIs(value, False, key)
        self.assertFalse(self.binding["body_authoring_contract"]["selectable_geometry_method"])
        self.assertFalse(self.binding["current_method_boundary"]["new_body_restart_authorized"])


if __name__ == "__main__":
    unittest.main()
