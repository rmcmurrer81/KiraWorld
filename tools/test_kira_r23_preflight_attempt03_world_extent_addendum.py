#!/usr/bin/env python3
"""Focused tests for R23 preflight Attempt 03's one-leaf addendum."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask_attempt03.py"
ADDENDUM = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_attempt03_preparation/"
    "KIRA_R23_ATTEMPT03_WORLD_EXTENT_ADDENDUM.json"
)
ATTEMPT03_PASS = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_03/PREFLIGHT.json"
)
ATTEMPT03_FAILURE = ATTEMPT03_PASS.with_name("FAILURE_EVIDENCE.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(left, right, prefix=""):
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(set(left).union(right)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in left or key not in right:
                result.append(path)
            else:
                result.extend(differences(left[key], right[key], path))
        return result
    return [] if left == right else [prefix]


class Attempt03WorldExtentTests(unittest.TestCase):
    def setUp(self):
        self.addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))

    def test_source_parses_and_has_no_authoring_operations(self):
        source = WRAPPER.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertNotIn("bpy.ops", source)
        for token in (
            "save_as_mainfile(",
            "save_mainfile(",
            "render.render(",
            "export_scene.",
            "wm.open_mainfile(",
        ):
            self.assertNotIn(token, source)

    def test_all_bound_inputs_and_prior_attempts_are_exact(self):
        rows = [
            self.addendum["base_worker"],
            self.addendum["base_config"],
            self.addendum["source_blend"],
            self.addendum["qualified_cc0_foundation"],
            *self.addendum["preserved_attempts"],
        ]
        for row in rows:
            path = ROOT / row["path"]
            self.assertTrue(path.is_file(), row["path"])
            self.assertEqual(path.stat().st_size, row["bytes"], row["path"])
            self.assertEqual(sha256(path), row["sha256"], row["path"])

    def test_exactly_one_config_leaf_changes(self):
        config = json.loads(
            (ROOT / self.addendum["base_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        changed = deepcopy(config)
        contract = self.addendum["contract_addendum"]
        self.assertEqual(
            changed["alignment_and_mask"][
                "maximum_expanded_mask_world_extent_m"
            ],
            contract["old_value_m"],
        )
        changed["alignment_and_mask"][
            "maximum_expanded_mask_world_extent_m"
        ] = contract["new_value_m"]
        self.assertEqual(differences(config, changed), [contract["exact_config_leaf"]])
        self.assertEqual(contract["old_value_m"], 0.38)
        self.assertEqual(contract["new_value_m"], 0.4)

    def test_addendum_is_supported_by_attempt02(self):
        attempt02 = json.loads(
            (ROOT / self.addendum["preserved_attempts"][1]["path"]).read_text(
                encoding="utf-8"
            )
        )
        first = attempt02["retained_pre_failure_metrics"][
            "expanded_r19_mask_failure"
        ]["attempts"][0]
        basis = self.addendum["contract_addendum"]["evidence_basis"]
        self.assertEqual(first["exterior_rings"], 2)
        self.assertEqual(first["world_extent_m"], basis["attempt_02_measured_world_extent_m"])
        self.assertEqual(first["topology"]["face_index_sha256"], basis["attempt_02_selected_face_index_sha256_expected"])
        self.assertEqual(
            [name for name, passed in first["gates"].items() if not passed],
            ["world_extent_bounded"],
        )
        self.assertLess(first["world_extent_m"], 0.4)

    def test_smallest_passing_mask_contract_is_exact(self):
        expected = self.addendum["expected_selection"]
        self.assertEqual(expected["smallest_passing_exterior_rings"], 2)
        self.assertEqual(expected["face_count"], 695)
        self.assertEqual(expected["ordered_outer_seam_vertices"], 91)
        self.assertEqual(
            expected["face_index_sha256"],
            "6cde7db28dfee9309c3741ec232caff9379d295fd84933c40de0a880d933ddaf",
        )

    def test_locality_policy_does_not_hide_proximal_thigh_transition(self):
        policy = self.addendum["locality_proof"]
        self.assertEqual(policy["forbidden_dominant_hip_groups"], ["hip_03"])
        self.assertIn("abdomenUpper_038", policy["forbidden_dominant_upper_abdomen_groups"])
        self.assertEqual(
            policy["forbidden_dominant_distal_leg_name_tokens"],
            ["Shin", "Foot", "Toe"],
        )
        self.assertEqual(
            len(policy["permitted_but_must_be_counted_proximal_thigh_transition_groups"]),
            4,
        )
        self.assertIn("not called zero leg influence", policy["truth_note"])

    def test_actual_attempt03_append_only_evidence(self):
        self.assertNotEqual(ATTEMPT03_PASS.exists(), ATTEMPT03_FAILURE.exists())
        if ATTEMPT03_PASS.exists():
            evidence = json.loads(ATTEMPT03_PASS.read_text(encoding="utf-8"))
            self.assertEqual(
                evidence["status"], "PREFLIGHT_PASS_AUTHORING_NOT_STARTED"
            )
            self.assertTrue(all(evidence["deterministic_selection_checks"].values()))
            self.assertTrue(evidence["explicit_locality_escape_proof"]["passed"])
            self.assertEqual(
                evidence["expanded_r19_mask"]["selected_exterior_rings"], 2
            )
            self.assertIn("fresh_freeze_ledger", evidence)
            self.assertTrue(evidence["integrity"]["source_blend_exact"])
            self.assertTrue(evidence["integrity"]["r19_body_exact"])
        else:
            evidence = json.loads(ATTEMPT03_FAILURE.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "PREFLIGHT_NO_GO_NO_CANDIDATE")
            self.assertEqual(
                evidence["contract_addendum"]["exact_leaf_differences"],
                [
                    {
                        "path": (
                            "alignment_and_mask."
                            "maximum_expanded_mask_world_extent_m"
                        ),
                        "before": 0.38,
                        "after": 0.4,
                    }
                ],
            )
            self.assertTrue(
                evidence["contract_addendum"]["all_other_config_leaves_unchanged"]
            )
            self.assertEqual(evidence["error_type"], "AttributeError")
            self.assertIn("fcurves", evidence["error"])
            self.assertEqual(
                evidence["source_blend"]["sha256_after"],
                evidence["source_blend"]["expected_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
