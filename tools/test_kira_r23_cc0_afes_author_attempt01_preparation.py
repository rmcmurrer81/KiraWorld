#!/usr/bin/env python3
"""Static and pure tests for the prepared R23 author Attempt 01."""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest

from tools.kira_r23_cc0_afes_author_core import (
    align_cycle,
    barycentric_weights,
    blend_feathered_scalar_field,
    blend_feathered_vector_field,
    clinical_longitudinal_order_checks,
    collar_point,
    cycle_parameters,
    feathered_influences,
    matching_cycle_triangles,
    maximum_adjacent_delta,
    top_four_normalized,
    zipper_bridge_parameterized,
)


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt01.py"
CORE = ROOT / "Tools/kira_r23_cc0_afes_author_core.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt01_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT01_CONFIG.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R23AuthorAttempt01PreparationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_sources_parse(self):
        ast.parse(WORKER.read_text(encoding="utf-8"))
        ast.parse(CORE.read_text(encoding="utf-8"))

    def test_all_bound_inputs_are_exact(self):
        for name, binding in self.config["inputs"].items():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, binding["bytes"], name)
            self.assertEqual(sha256(path), binding["sha256"], name)

    def test_preparation_is_inert_and_output_absent(self):
        self.assertEqual(
            self.config["status"],
            "PREPARED_NOT_RUN_EXPLICIT_EXECUTION_AUTHORIZATION_REQUIRED",
        )
        self.assertFalse(self.config["execution"]["authoring_authorized_by_preparation"])
        self.assertEqual(
            self.config["execution"]["required_cli_flag"], "--execute-authoring"
        )
        self.assertFalse((ROOT / self.config["output"]["directory"]).exists())
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn("if not args.execute_authoring", source)
        self.assertIn("--execute-authoring", source)

    def test_exact_two_ring_mask_and_freeze_ledger_are_bound(self):
        selected = self.config["selected_target_mask"]
        self.assertEqual(selected["exterior_rings"], 2)
        self.assertEqual(selected["face_count"], 695)
        self.assertEqual(selected["outer_seam_vertex_count"], 91)
        self.assertEqual(
            selected["face_index_sha256"],
            "6cde7db28dfee9309c3741ec232caff9379d295fd84933c40de0a880d933ddaf",
        )
        self.assertEqual(selected["maximum_world_extent_m"], 0.4)
        ledger = self.config["sealed_freeze_ledger"]
        self.assertEqual(ledger["surviving_primary_surface"]["vertex_count"], 12309)
        self.assertEqual(ledger["outer_seam"]["ordered_vertex_count"], 91)
        self.assertEqual(ledger["nonbody_mesh_objects"]["count"], 46)
        self.assertEqual(ledger["body_materials"]["count"], 6)
        self.assertEqual(
            ledger["actions_sha256"],
            "ac149d390ad20f1f125a79b442470703254d2f05f72c4bd75b95873f8be908f8",
        )

    def test_donor_is_structural_chart_not_visual_answer(self):
        donor = self.config["qualified_donor_disk"]
        method = self.config["authoring_method"]
        self.assertFalse(donor["visual_form_sufficient_without_bounded_relief"])
        self.assertEqual(donor["copy_scope"], "topology_and_AFES_membership_chart_only")
        self.assertFalse(donor["copy_material_uv_weight_identity_or_armature"])
        self.assertFalse(method["donor_weights_copied"])
        self.assertEqual(method["separate_anatomy_objects"], 0)
        self.assertFalse(method["booleans"])
        self.assertFalse(method["global_weld"])

    def test_clinical_relief_and_visual_rejection_contract(self):
        relief = self.config["bounded_clinical_relief"]
        self.assertLessEqual(relief["maximum_absolute_additional_relief_m"], 0.0045)
        self.assertIn("AFES_LANDMARK__urethral_opening", relief["priority_order"])
        self.assertIn("AFES_LANDMARK__vaginal_opening", relief["priority_order"])
        self.assertIn("AFES_LANDMARK__perineal_path", relief["priority_order"])
        self.assertGreater(relief["minimum_longitudinal_separation_chart"], 0.0)
        self.assertGreaterEqual(relief["feather_rings"], 3)
        self.assertLessEqual(relief["maximum_adjacent_relief_delta_m"], 0.002)
        self.assertLessEqual(relief["maximum_adjacent_tint_rgb_distance"], 0.12)
        self.assertEqual(
            set(relief["tint_rgb_by_group"]), set(relief["priority_order"])
        )
        self.assertGreaterEqual(
            min(
                channel
                for color in relief["tint_rgb_by_group"].values()
                for channel in color
            ),
            0.24,
        )
        self.assertIn(
            "urethral_opening_anterior_to_vaginal_opening",
            relief["required_order_relations"],
        )
        self.assertIn("anal_recess_posterior_and_separate_from_vaginal_opening", relief["required_order_relations"])
        self.assertEqual(
            set(relief["forbidden_visual_forms"]),
            {
                "dark_cavity",
                "plate",
                "petal",
                "insert",
                "apron",
                "detached_overlay",
                "painted_opening_without_relief",
            },
        )
        views = self.config["postsave_required_audits_before_owner_review"]
        for view in (
            "front",
            "left and right obliques",
            "left and right profiles",
            "inferior-front",
            "inferior-rear",
            "rear/perineal",
            "neutral distance",
            "seated and deformed close views",
        ):
            self.assertIn(view, views)

    def test_clinical_order_gate_is_explicit_and_fail_closed(self):
        ordered = {
            "AFES_LANDMARK__mons_pubis": 0.9,
            "AFES_LANDMARK__labia_majora": 0.7,
            "AFES_LANDMARK__clitoral_hood": 0.6,
            "AFES_LANDMARK__clitoris": 0.55,
            "AFES_LANDMARK__urethral_opening": 0.4,
            "AFES_LANDMARK__vaginal_opening": 0.2,
            "AFES_LANDMARK__fourchette": 0.1,
            "AFES_LANDMARK__perineal_path": 0.0,
            "AFES_LANDMARK__perineal_path__anal_recess": -0.3,
        }
        checks = clinical_longitudinal_order_checks(ordered, 1.0e-6)
        self.assertTrue(all(checks.values()))
        reversed_openings = dict(ordered)
        reversed_openings["AFES_LANDMARK__urethral_opening"] = 0.1
        self.assertFalse(
            clinical_longitudinal_order_checks(reversed_openings, 1.0e-6)[
                "urethral_opening_anterior_to_vaginal_opening"
            ]
        )
        missing = dict(ordered)
        del missing["AFES_LANDMARK__perineal_path__anal_recess"]
        self.assertFalse(
            clinical_longitudinal_order_checks(missing, 1.0e-6)[
                "anal_recess_posterior_and_separate_from_vaginal_opening"
            ]
        )

    def test_topology_distance_feathering_has_no_membership_step(self):
        adjacency = {
            index: {
                neighbor
                for neighbor in (index - 1, index + 1)
                if 0 <= neighbor <= 12
            }
            for index in range(13)
        }
        priorities = ["specific", "broad"]
        memberships = {
            "specific": {5, 6, 7},
            "broad": {3, 4, 5, 6, 7, 8, 9},
        }
        influences = feathered_influences(
            adjacency, memberships, priorities, feather_rings=4
        )
        self.assertEqual(influences["specific"][5], 0.5)
        self.assertEqual(influences["specific"][4], 0.5)
        self.assertGreater(influences["specific"][6], 0.5)
        self.assertLess(influences["specific"][6], 1.0)
        scalar = blend_feathered_scalar_field(
            adjacency,
            influences,
            priorities,
            {"specific": -0.002, "broad": 0.004},
        )
        vector = blend_feathered_vector_field(
            adjacency,
            influences,
            priorities,
            {"specific": (0.5, 0.3, 0.3), "broad": (0.7, 0.5, 0.4)},
            (0.72, 0.5, 0.44),
        )
        self.assertLess(maximum_adjacent_delta(adjacency, scalar), 0.002)
        self.assertLess(maximum_adjacent_delta(adjacency, vector), 0.12)
        self.assertTrue(all(-0.002 <= value <= 0.004 for value in scalar.values()))
        self.assertTrue(
            all(
                0.3 <= channel <= 0.72
                for color in vector.values()
                for channel in color
            )
        )

    def test_expected_topology_is_euler_consistent(self):
        expected = self.config["expected_structural_result"]
        self.assertEqual(
            expected["replacement_patch_edges"],
            expected["replacement_patch_vertices"]
            + expected["replacement_patch_faces"]
            - 1,
        )
        self.assertEqual(
            expected["body_edges"],
            expected["body_vertices"] + expected["body_faces"] - 2,
        )
        self.assertEqual(expected["whole_body_components"], 1)
        self.assertEqual(expected["whole_body_boundary_edges"], 0)
        self.assertEqual(expected["whole_body_nonmanifold_edges"], 0)

    def test_cycle_alignment_and_unequal_zipper_are_deterministic(self):
        reference = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)]
        candidate = [12, 13, 10, 11]
        points = {10: (1.0, 0.0, 0.0), 11: (0.0, 1.0, 0.0), 12: (-1.0, 0.0, 0.0), 13: (0.0, -1.0, 0.0)}
        aligned, record = align_cycle(reference, candidate, points)
        self.assertEqual(aligned, [10, 11, 12, 13])
        self.assertAlmostEqual(record["mean_squared_distance"], 0.0)
        lower = [0, 1, 2]
        upper = [3, 4, 5, 6, 7]
        faces = zipper_bridge_parameterized(
            lower,
            cycle_parameters([(0, 0), (1, 0), (0, 1)]),
            upper,
            cycle_parameters([(0, 0), (1, 0), (2, 1), (1, 2), (0, 1)]),
        )
        self.assertEqual(len(faces), len(lower) + len(upper))
        self.assertEqual(len(matching_cycle_triangles(upper, [8, 9, 10, 11, 12])), 10)

    def test_collar_barycentric_and_weight_helpers(self):
        self.assertEqual(collar_point((0, 0, 0), (1, 2, 3), 0.0), (0.0, 0.0, 0.0))
        self.assertEqual(collar_point((0, 0, 0), (1, 2, 3), 1.0), (1.0, 2.0, 3.0))
        bary = barycentric_weights((0.25, 0.25, 0.0), (0, 0, 0), (1, 0, 0), (0, 1, 0))
        self.assertAlmostEqual(sum(bary), 1.0)
        self.assertEqual(tuple(round(value, 3) for value in bary), (0.5, 0.25, 0.25))
        weights = top_four_normalized({"a": 4, "b": 3, "c": 2, "d": 1, "e": 0.5})
        self.assertEqual(set(weights), {"a", "b", "c", "d"})
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_worker_scope_and_truth_boundary(self):
        source = WORKER.read_text(encoding="utf-8")
        self.assertNotIn("bpy.ops.render", source)
        self.assertNotIn("export_scene", source)
        self.assertNotIn("Avatar/Library/female", source)
        self.assertNotIn("adult_anatomy_reference", source)
        truth = self.config["truth_boundary"]
        self.assertFalse(truth["internal_urinary_or_digestive_system_implemented"])
        self.assertFalse(truth["reproductive_physiology_implemented"])
        self.assertTrue(truth["owner_visual_approval_still_required"])
        self.assertFalse(self.config["execution"]["no_render_in_author_worker"] is False)


if __name__ == "__main__":
    unittest.main()
