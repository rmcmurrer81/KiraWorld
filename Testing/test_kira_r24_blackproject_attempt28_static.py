from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT28_CONFIG.json"
)
WORKER = (
    ROOT
    / "tools"
    / "blender_diagnose_kira_r24_blackproject_replacement_boundary_attempt28.py"
)
CAPTURE = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "attempt_27"
    / "NO_ADMISSIBLE_CANDIDATE_DIAGNOSTIC.json"
)
EVIDENCE_ROOT = CAPTURE.parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R24BlackProjectAttempt28StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tools import (
            blender_diagnose_kira_r24_blackproject_replacement_boundary_attempt28 as subject,
        )

        cls.subject = subject
        cls.config = subject.load_config(CONFIG)
        cls.capture = json.loads(CAPTURE.read_text(encoding="utf-8"))
        cls.analysis = subject.analyze_coordinate_suppressions(
            cls.capture,
            cls.config["coordinate_only_analysis"][
                "first_passing_suppression_cardinality"
            ],
            cls.config["diagnosis"]["required_minimum_angle_degrees"],
        )

    def test_attempt27_live_package_and_capture_are_exact(self) -> None:
        records = self.subject.verify_bindings(self.config)
        preserved = self.config["preserved_attempt27_package"]
        rows = [records[name] for name in preserved["binding_names"]]
        self.assertEqual(len(rows), 11)
        self.assertEqual(sum(row["bytes"] for row in rows), 192831)
        self.assertEqual(
            sha256(CAPTURE),
            "68eac427b1c5026146d27036430f74e0f886be75048519869ae250a32b4cd708",
        )
        self.assertEqual(self.capture["attempt_id"], "attempt_27")
        self.assertFalse(self.capture["blend_saved"])
        self.assertFalse(self.capture["runtime_changed"])

    def test_fixed_boundary_has_four_convex_corners_below_unchanged_target(self) -> None:
        fixed = self.analysis["fixed_boundary"]
        self.assertEqual(fixed["convex_corner_indices_below_target"], [2, 7, 21, 28])
        self.assertAlmostEqual(
            fixed["minimum_boundary_interior_angle_degrees"],
            8.546625595376922,
            places=12,
        )
        self.assertEqual(fixed["minimum_boundary_index"], 28)
        self.assertFalse(fixed["necessary_fixed_boundary_corner_condition_passes"])
        self.assertEqual(fixed["target_degrees"], 12.0)
        self.assertEqual(
            self.config["diagnosis"]["global_fixed_pslg_conclusion"],
            "PROVEN_INFEASIBLE_UNDER_FIXED_PSLG_BOUNDARY_CORNER_BELOW_TARGET",
        )
        self.assertFalse(
            self.config["diagnosis"]["another_interior_seed_can_repair_fixed_boundary"]
        )

    def test_exhaustive_coordinate_variants_match_sealed_static_result(self) -> None:
        expected_sets = self.config["coordinate_only_analysis"][
            "passing_suppression_sets"
        ]
        actual_sets = [
            row["suppressed_source_indices"]
            for row in self.analysis["passing_variants"]
        ]
        self.assertEqual(self.analysis["first_passing_suppression_cardinality"], 4)
        self.assertEqual(self.analysis["passing_variant_count"], 9)
        self.assertEqual(actual_sets, expected_sets)
        minimum_angles = [
            row["boundary_angle_analysis"][
                "minimum_boundary_interior_angle_degrees"
            ]
            for row in self.analysis["passing_variants"]
        ]
        area_ratios = [
            row["retained_projected_area_ratio"]
            for row in self.analysis["passing_variants"]
        ]
        self.assertEqual(
            [min(minimum_angles), max(minimum_angles)],
            self.config["coordinate_only_analysis"][
                "passing_minimum_convex_angle_range_degrees"
            ],
        )
        self.assertEqual(
            [min(area_ratios), max(area_ratios)],
            self.config["coordinate_only_analysis"][
                "retained_projected_area_ratio_range"
            ],
        )

    def test_coordinate_suppression_is_not_mislabeled_as_mesh_repair(self) -> None:
        for row in self.analysis["passing_variants"]:
            self.assertTrue(row["simple_polygon"])
            self.assertTrue(row["orientation_preserved"])
            self.assertTrue(row["necessary_corner_condition_passes"])
            self.assertFalse(row["source_mesh_topology_compatibility_proven"])
            self.assertFalse(row["repair_authorized"])
        representative = next(
            row
            for row in self.analysis["passing_variants"]
            if row["suppressed_source_indices"] == [2, 7, 21, 28]
        )
        by_index = {
            row["suppressed_source_index"]: row for row in representative["chords"]
        }
        self.assertAlmostEqual(
            by_index[2]["suppressed_point_distance_to_chord_m"],
            0.004183637734348049,
            places=15,
        )
        self.assertAlmostEqual(
            by_index[28]["suppressed_point_distance_to_chord_m"],
            0.0035740377112679416,
            places=15,
        )
        self.assertFalse(
            self.config["coordinate_only_analysis"]["direct_suppression_authorized"]
        )

    def test_source_mesh_mapping_is_bounded_to_existing_faces_and_coordinates(self) -> None:
        source = self.config["source_mesh_diagnostic"]
        self.assertEqual(source["current_face_ring_expansion"], 2)
        self.assertEqual(source["current_domain_face_count"], 88)
        self.assertEqual(len(source["current_boundary_cycle_mesh_vertex_indices"]), 32)
        self.assertEqual(source["uniform_face_ring_expansions_to_map"], list(range(3, 16)))
        self.assertEqual(
            source["targeted_vertex_star_suppression_sets"],
            self.config["coordinate_only_analysis"]["passing_suppression_sets"],
        )
        self.assertTrue(
            source["eligibility_is_necessary_not_sufficient_for_later_reconstruction"]
        )
        self.assertIn("prefer_strictly_interior_domain", source["global_seam_policy"])
        self.assertIn("reject partial seam contact", source["global_seam_policy"])
        self.assertEqual(source["maximum_local_chart_boundary_deviation_m"], 0.0011)
        self.assertEqual(self.config["unchanged_hard_gates"]["global_seam_vertex_count"], 34)

    def test_worker_is_static_import_safe_and_has_no_save_or_mutation_operator(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        compile(source, str(WORKER), "exec")
        tree = ast.parse(source)
        top_imports = [
            alias.name
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        ]
        self.assertNotIn("bpy", top_imports)
        self.assertNotIn("bmesh", top_imports)
        for forbidden in (
            "bpy.ops.wm.save",
            "save_as_mainfile",
            "bmesh.ops.delete",
            "bmesh.ops.triangle_fill",
            "bmesh.ops.triangulate",
            "export_scene",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("bpy.ops.wm.open_mainfile", source)
        self.assertIn("CAPTURED_EXISTING_SOURCE_BOUNDARY_OPTIONS_NO_REPAIR", source)
        self.assertIn("diagnostic-only stop before triangulation or mesh mutation", source)

    def test_scope_and_fail_closed_contract(self) -> None:
        self.assertEqual(self.subject.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_28").exists())
        self.assertFalse(self.config["scope"]["body_geometry_mutation_allowed"])
        self.assertFalse(self.config["scope"]["patch_geometry_mutation_allowed"])
        self.assertFalse(self.config["scope"]["triangulation_allowed"])
        self.assertFalse(self.config["scope"]["render_allowed"])
        self.assertFalse(self.config["scope"]["blend_save_allowed"])
        self.assertFalse(self.config["scope"]["quality_gate_reduction_allowed"])
        self.assertFalse(self.config["truth"]["attempt28_blender_execution_performed"])
        self.assertFalse(self.config["truth"]["body_repair_proven"])

    def test_contract_rejects_gate_scope_and_diagnosis_drift(self) -> None:
        for mutation in ("angle", "area", "scope", "corner", "seed", "simplify"):
            changed = copy.deepcopy(self.config)
            if mutation == "angle":
                changed["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"] = 11.0
            elif mutation == "area":
                changed["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"] = 0.0
            elif mutation == "scope":
                changed["scope"]["patch_geometry_mutation_allowed"] = True
            elif mutation == "corner":
                changed["diagnosis"]["convex_boundary_source_indices_below_target"] = [28]
            elif mutation == "seed":
                changed["diagnosis"]["another_interior_seed_can_repair_fixed_boundary"] = True
            else:
                changed["coordinate_only_analysis"]["direct_suppression_authorized"] = True
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.subject.validate_config(changed)


if __name__ == "__main__":
    unittest.main()
