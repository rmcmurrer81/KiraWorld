from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RecoverySprint" / "continuation_20260808" / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT29_CONFIG.json"
WORKER = ROOT / "tools" / "blender_diagnose_kira_r24_blackproject_chart_mismatch_attempt29.py"
EVIDENCE_ROOT = ROOT / "RecoverySprint" / "continuation_20260803" / "kira_r24_internal_midpoint_fair_surface"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R24BlackProjectAttempt29StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tools import blender_diagnose_kira_r24_blackproject_chart_mismatch_attempt29 as subject

        cls.subject = subject
        cls.config = subject.load_overlay(CONFIG)
        cls.records = subject.verify_bindings(cls.config)
        cls.source29 = subject.derive_attempt29_source(
            subject.ATTEMPT28_WORKER.read_text(encoding="utf-8")
        )
        cls.namespace = {
            "__name__": "attempt29_static_subject",
            "__file__": str(WORKER),
            "__builtins__": __builtins__,
        }
        exec(compile(cls.source29, "<attempt29-derived-static>", "exec"), cls.namespace, cls.namespace)

    def test_attempt28_package_and_exact_live_failure_are_preserved(self) -> None:
        preserved = self.config["preserved_attempt28_package"]
        rows = [self.records[name] for name in preserved["binding_names"]]
        self.assertEqual(len(rows), 9)
        self.assertEqual(sum(row["bytes"] for row in rows), 72757)
        expected = {
            "attempt28_started": "d029c56021305e08e9bd299d44b13d513f1ba3e1de87c3d0ef5e914ea1707af8",
            "attempt28_failure": "e49cade6fd41ccec7ded923d171e4aa05fcec08d420d642ad967d4d6949ecd47",
            "attempt28_stdout": "436a6df53f5f2c2feaefbd16bfd79f83bd82e69df6cde1e857fef3db66a36056",
            "attempt28_stderr": "f3166283ebad25dbbf658f5e8ea8a000018ef6be659c4eaddb9a5fbeb9edf156",
        }
        for name, digest in expected.items():
            self.assertEqual(self.records[name]["sha256"], digest)
        self.assertFalse((EVIDENCE_ROOT / "attempt_28" / "CHART_MISMATCH_DIAGNOSTIC.json").exists())

    def test_derived_source_instruments_exact_fatal_boundary_before_mapping(self) -> None:
        compile(self.source29, "<attempt29-derived>", "exec")
        self.assertIn("attempt29_build_chart_mismatch_diagnostic", self.source29)
        self.assertIn("CAPTURED_COMPUTED_VS_EXPECTED_CHART_MISMATCH_NO_REPAIR", self.source29)
        self.assertIn("diagnostic-only stop before boundary candidate mapping", self.source29)
        capture_position = self.source29.index("mismatch = attempt29_build_chart_mismatch_diagnostic")
        mapping_position = self.source29.index("        targeted = []")
        self.assertLess(capture_position, mapping_position)
        self.assertNotIn("source chart does not match Attempt 27 capture", self.source29)
        for stale in ("attempt_28", "attempt28", "Attempt 28", "ATTEMPT28"):
            self.assertNotIn(stale, self.source29)

    def test_alignment_details_preserve_exact_source_mapping_and_deltas(self) -> None:
        function = self.namespace["attempt29_alignment_details"]
        expected = [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]]
        chart = {
            "cycle_mesh_vertex_indices": [12, 13, 10, 11],
            "coordinates_xy_m": [[2.0, 1.0], [0.0, 1.0], [0.0, 0.0], [2.0, 0.0]],
        }
        details = function(expected, chart)
        self.assertEqual(
            details["alignment"]["capture_source_index_to_mesh_vertex_index"],
            [10, 11, 12, 13],
        )
        self.assertEqual(details["maximum_distance_m"], 0.0)
        self.assertEqual(details["rms_distance_m"], 0.0)
        self.assertTrue(all(row["distance_m"] == 0.0 for row in details["delta_rows"]))

    def test_capture_contract_compares_direct_and_attempt18_body_matrix_paths(self) -> None:
        contract = self.config["chart_mismatch_contract"]
        self.assertEqual(contract["expected_coordinate_count"], 32)
        self.assertEqual(contract["match_tolerance_m"], 1.0e-10)
        self.assertEqual(
            contract["attempt18_matrix_contract"],
            "appended_patch.matrix_world = sealed_body.matrix_world.copy()",
        )
        self.assertTrue(contract["capture_per_coordinate_deltas"])
        self.assertTrue(contract["compute_alternative_chart_without_datablock_assignment"])
        self.assertTrue(contract["classification_is_diagnostic_not_repair"])
        self.assertIn("body.matrix_world.copy()", self.source29)
        self.assertIn("body_minus_direct_matrix_world", self.source29)

    def test_worker_is_blender_lazy_and_contains_no_save_or_geometry_mutation(self) -> None:
        wrapper_source = WORKER.read_text(encoding="utf-8")
        tree = ast.parse(wrapper_source)
        top_imports = [
            alias.name
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        ]
        self.assertNotIn("bpy", top_imports)
        self.assertNotIn("bmesh", top_imports)
        for source in (wrapper_source, self.source29):
            for forbidden in (
                "bpy.ops.wm.save",
                "save_as_mainfile",
                "bmesh.ops.delete",
                "bmesh.ops.triangle_fill",
                "bmesh.ops.triangulate",
                "export_scene",
                ".matrix_world =",
            ):
                self.assertNotIn(forbidden, source)

    def test_scope_paths_and_unchanged_gates(self) -> None:
        self.assertEqual(self.subject.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertEqual(self.config["output"]["diagnostic"], "CHART_MISMATCH_DIAGNOSTIC.json")
        self.assertFalse((EVIDENCE_ROOT / "attempt_29").exists())
        self.assertFalse(self.config["scope"]["boundary_candidate_mapping_allowed"])
        self.assertFalse(self.config["scope"]["triangulation_allowed"])
        self.assertFalse(self.config["scope"]["body_geometry_mutation_allowed"])
        self.assertFalse(self.config["scope"]["blend_save_allowed"])
        self.assertEqual(
            self.config["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"],
            12.0,
        )
        self.assertEqual(
            self.config["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"],
            1.0e-10,
        )
        self.assertEqual(self.config["unchanged_hard_gates"]["global_seam_vertex_count"], 34)

    def test_truth_does_not_claim_diagnosis_or_repair_before_live_capture(self) -> None:
        truth = self.config["truth"]
        self.assertFalse(self.config["diagnosis"]["likely_mismatch_hypothesis_proven"])
        self.assertFalse(truth["attempt29_blender_execution_performed"])
        self.assertFalse(truth["attempt29_chart_mismatch_captured"])
        self.assertFalse(truth["attempt29_boundary_mapping_reached"])
        self.assertFalse(truth["attempt29_mesh_mutation_performed"])
        self.assertFalse(truth["attempt29_blend_saved"])
        self.assertFalse(truth["runtime_changed"])
        self.assertFalse(truth["body_repair_proven"])

    def test_contract_fails_closed_on_scope_gate_and_capture_drift(self) -> None:
        for mutation in ("angle", "area", "scope", "mapping", "tolerance", "capture"):
            changed = copy.deepcopy(self.config)
            if mutation == "angle":
                changed["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"] = 11.0
            elif mutation == "area":
                changed["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"] = 0.0
            elif mutation == "scope":
                changed["scope"]["patch_geometry_mutation_allowed"] = True
            elif mutation == "mapping":
                changed["scope"]["boundary_candidate_mapping_allowed"] = True
            elif mutation == "tolerance":
                changed["chart_mismatch_contract"]["match_tolerance_m"] = 1.0
            else:
                changed["chart_mismatch_contract"]["capture_before_original_attempt28_fatal_check"] = False
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.subject.validate_overlay(changed)


if __name__ == "__main__":
    unittest.main()

