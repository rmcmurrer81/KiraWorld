from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static.py"
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static"
)
CONTRACT = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_CONTRACT.json"
PROPOSAL = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_PROPOSAL.md"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "kira_r24_intrinsic_curved_annulus_static", MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not construct static module import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntrinsicCurvedAnnulusStructuredRetopologyStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.contract = cls.module.load_contract(CONTRACT)
        cls.bindings = cls.module.validate_immutable_bindings(cls.contract)
        cls.domains = cls.module.reconstruct_exact_domains(
            cls.contract, cls.bindings
        )
        cls.runtime = json.loads(
            cls.bindings["annular_runtime_result"].read_text(encoding="utf-8")
        )
        cls.family = cls.module.evaluate_runtime_family(
            cls.contract, cls.domains, cls.bindings
        )

    def test_01_package_is_static_append_only_and_has_no_body_artifact(self) -> None:
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(PROPOSAL.is_file())
        allowed = {
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_CONTRACT.json",
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_PROPOSAL.md",
            "CHECKPOINT.md",
        }
        actual = {path.name for path in PACKAGE.iterdir()}
        self.assertTrue(actual <= allowed)
        self.assertFalse(any(path.suffix.lower() == ".blend" for path in PACKAGE.iterdir()))
        self.assertFalse(any(path.suffix.lower() in {".png", ".jpg", ".jpeg"} for path in PACKAGE.iterdir()))

    def test_02_all_sealed_bindings_match_exact_bytes_and_hashes(self) -> None:
        self.assertEqual(len(self.bindings), 11)
        for name, path in self.bindings.items():
            with self.subTest(name=name):
                binding = self.contract["immutable_bindings"][name]
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(self.module.sha256_file(path), binding["sha256"])

    def test_03_exact_d2_collar_and_estar_topology_reconstructs(self) -> None:
        d2 = self.domains["d2_summary"]
        collar = self.domains["collar_summary"]
        estar = self.domains["estar_summary"]
        self.assertEqual((d2["face_count"], d2["euler_characteristic"]), (88, 1))
        self.assertEqual(len(d2["boundary_cycles"]), 1)
        self.assertEqual((collar["face_count"], collar["euler_characteristic"]), (73, 0))
        self.assertEqual(len(collar["vertices"]), 73)
        self.assertEqual(len(collar["boundary_cycles"]), 2)
        self.assertEqual(
            set(collar["vertices"]),
            set(self.domains["inner_cycle"]) | set(self.domains["outer_cycle"]),
        )
        self.assertEqual((estar["face_count"], estar["euler_characteristic"]), (161, 1))
        self.assertEqual(estar["boundary_cycles"], [self.domains["outer_cycle"]])
        self.assertEqual(
            set(d2["vertices"]),
            set(estar["vertices"]) - set(self.domains["outer_cycle"]),
        )
        self.assertFalse(set(d2["vertices"]) & set(self.domains["outer_cycle"]))
        self.assertEqual(len(self.domains["outside"]), 1275)
        self.assertEqual(len(self.domains["exterior_adjacent"]), 41)
        self.assertEqual(self.domains["minimum_seam_rings"], 4)

    def test_04_all_31_sealed_loops_pass_exact_intrinsic_separation(self) -> None:
        self.assertEqual(self.family["source_candidate_count"], 31)
        self.assertEqual(self.family["intrinsic_eligible_count"], 31)
        self.assertTrue(self.family["all_intrinsically_separating"])
        self.assertFalse(self.family["projected_geometry_used"])
        self.assertFalse(self.family["world_planarity_used"])
        for row in self.family["evaluations"]:
            with self.subTest(level=row["level"]):
                self.assertTrue(row["intrinsic_eligible"], row["failure_names"])
                self.assertEqual(row["failure_names"], [])
                self.assertEqual(row["details"]["point_count"], 70)
                self.assertEqual(row["details"]["segment_count"], 70)
                self.assertEqual(row["details"]["mixed_carrier_face_count"], 70)
                self.assertEqual(row["details"]["inner_side_component_count"], 1)
                self.assertEqual(row["details"]["outer_side_component_count"], 1)
                self.assertTrue(row["details"]["d2_plus_inner_side_is_one_disk"])

    def test_05_runtime_planar_failures_are_preserved_but_not_intrinsic_gates(self) -> None:
        expected = {
            "exact_inner_outer_projected_separation",
            "single_component_d2_envelope_separation",
            "chart_deviation_gate",
        }
        self.assertEqual(set(self.contract["retired_planar_gates"]), expected)
        for source, evaluation in zip(
            self.runtime["solver_summary"]["candidate_records"],
            self.family["evaluations"],
            strict=True,
        ):
            self.assertEqual(set(source["failure_names"]), expected)
            self.assertEqual(
                set(evaluation["details"]["retired_planar_failures_observed"]),
                expected,
            )
            self.assertFalse(evaluation["details"]["projected_geometry_used"])
            self.assertFalse(evaluation["details"]["world_planarity_used"])

    def test_06_intrinsic_evaluator_fails_closed_on_topology_or_provenance_drift(self) -> None:
        source = self.runtime["solver_summary"]["candidate_records"][0]

        missing_segment = copy.deepcopy(source)
        missing_segment["segment_records"].pop()
        result = self.module.evaluate_intrinsic_candidate(
            missing_segment, self.contract, self.domains
        )
        self.assertFalse(result["intrinsic_eligible"])
        self.assertTrue(result["failure_names"])

        owner_drift = copy.deepcopy(source)
        owner_drift["actual_point_records"][0]["incident_source_faces"] = [3]
        result = self.module.evaluate_intrinsic_candidate(
            owner_drift, self.contract, self.domains
        )
        self.assertFalse(result["intrinsic_eligible"])
        self.assertTrue(result["failure_names"])

        nonplanar_failure = copy.deepcopy(source)
        nonplanar_failure["failure_names"].append("exterior_adjacent_face_preservation")
        result = self.module.evaluate_intrinsic_candidate(
            nonplanar_failure, self.contract, self.domains
        )
        self.assertFalse(result["intrinsic_eligible"])
        self.assertIn(
            "nonplanar_parent_failure:exterior_adjacent_face_preservation",
            result["failure_names"],
        )

    def test_07_direct_scope_consumes_d2_and_all_73_collar_faces_only_inside_estar(self) -> None:
        scope = self.contract["structured_retopology_scope"]
        self.assertEqual(scope["future_rebuild_domain"], "complete_estar_disk")
        self.assertEqual(scope["future_consumed_defect_core_face_count"], 88)
        self.assertEqual(scope["future_consumed_transition_collar_face_count"], 73)
        self.assertEqual(scope["future_consumed_total_source_face_count"], 161)
        self.assertEqual(
            scope["d2_boundary_role"],
            "defect_localization_only_not_immutable_final_boundary",
        )
        self.assertEqual(
            scope["estar_outer_cycle_role"], "exact_immutable_graft_boundary"
        )
        self.assertTrue(scope["all_73_collar_faces_in_scope"])
        self.assertTrue(scope["require_complete_73_face_disposition_ledger"])
        self.assertEqual(scope["three_nonisoline_collar_faces_in_scope"], [106, 1238, 1273])
        self.assertTrue(scope["only_crossed_face_scope_superseded"])
        self.assertFalse(scope["additional_contour_search_allowed"])
        self.assertFalse(scope["body_or_blend_mutation_authorized_by_this_contract"])

    def test_08_future_geometry_attribute_rig_and_intersection_gates_are_bound(self) -> None:
        gates = self.contract["future_measured_candidate_gates"]
        parity = self.contract["structured_topology_parity"]
        self.assertEqual(parity["fixed_outer_boundary_edge_count"], 41)
        self.assertEqual(parity["source_annulus_total_boundary_edge_count"], 73)
        self.assertFalse(parity["all_quad_annulus_with_fixed_32_and_41_cycles_possible"])
        self.assertFalse(parity["all_quad_disk_with_fixed_41_cycle_possible"])
        self.assertTrue(parity["require_mixed_topology"])
        self.assertTrue(parity["require_odd_positive_odd_sided_face_count"])
        self.assertTrue(parity["require_zero_outer_boundary_edge_splits"])
        self.assertTrue(parity["require_exact_ordered_stitch_schedule"])
        self.assertEqual(gates["minimum_render_triangle_angle_degrees"], 12.0)
        self.assertEqual(gates["minimum_render_triangle_area_m2"], 1e-10)
        self.assertEqual(gates["maximum_new_interior_vertices"], 160)
        self.assertEqual(gates["preserve_material_index"], 5)
        self.assertEqual(gates["inherited_nonpatch_exact_pairs"], 29)
        self.assertEqual(gates["global_interface_coordinate_delta_m"], 0.0)
        self.assertEqual(gates["global_interface_unique_weld_count"], 34)
        for key in (
            "require_exact_outer_cycle_coordinates",
            "require_source_triangle_barycentric_origin_for_every_new_vertex",
            "require_finite_explicit_displacement_for_every_new_vertex",
            "require_all_new_uv_records_bound",
            "require_all_new_normals_finite",
            "require_existing_native_armature_only",
            "require_interpolated_normalized_weights",
            "require_shape_key_consistency_or_fail",
            "require_zero_changed_records_outside_estar",
            "require_private_inactive_unassigned_unpublished",
        ):
            self.assertTrue(gates[key], key)

    def test_09_future_candidate_evaluator_is_currently_fail_closed(self) -> None:
        absent = self.module.evaluate_structured_retopology_evidence(
            None, self.contract
        )
        self.assertFalse(absent["eligible"])
        self.assertEqual(absent["failure_names"], ["measured_candidate_evidence_absent"])

        incomplete = self.module.evaluate_structured_retopology_evidence(
            {"artifact": {}}, self.contract
        )
        self.assertFalse(incomplete["eligible"])
        self.assertIn("missing_section:topology", incomplete["failure_names"])

    def test_10_static_module_is_pure_python_read_only_and_has_no_blender_path(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertNotIn("bpy", imports)
        self.assertNotIn("bmesh", imports)
        self.assertNotIn("subprocess", imports)
        for forbidden in (
            "write_text(",
            "write_bytes(",
            "open_mainfile",
            "save_as_mainfile",
            "bpy.ops",
            "blender.exe",
            "point_in_polygon",
            "chart_deviation",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)

    def test_11_proposal_is_truthful_and_explicitly_retires_contour_search(self) -> None:
        text = PROPOSAL.read_text(encoding="utf-8")
        lower = text.lower()
        for token in (
            "do not search for another pelvic transition contour",
            "exact combinatorial separation",
            "all 88 d2 faces and all 73 collar faces",
            "exact 41-cycle graft boundary",
            "measured_candidate_evidence_absent",
            "no visible anatomy",
            "no existing kira or sarah file was modified",
        ):
            self.assertIn(token, lower)
        self.assertNotIn("attempt_", lower)
        self.assertNotIn("bpy.", lower)
        self.assertNotIn("blender.exe", lower)

    def test_12_static_evaluation_reports_intrinsic_pass_but_no_body_candidate(self) -> None:
        terminal = self.contract["terminal_parent_result"]
        self.assertEqual(terminal["candidate_record_count"], 31)
        self.assertEqual(terminal["eligible_candidate_count"], 0)
        self.assertIsNone(terminal["selected_eligible_candidate"])
        self.assertTrue(terminal["finite_termination_reached"])
        self.assertFalse(terminal["mesh_mutated"])
        evaluation = self.module.static_evaluation(CONTRACT)
        self.assertEqual(
            evaluation["status"],
            "STATIC_INTRINSIC_TOPOLOGY_PASS_FUTURE_RETOPOLOGY_NOT_MEASURED",
        )
        self.assertTrue(evaluation["family"]["all_intrinsically_separating"])
        self.assertFalse(evaluation["future_measured_candidate"]["eligible"])
        self.assertFalse(evaluation["blender_used"])
        self.assertFalse(evaluation["mesh_mutated"])
        self.assertFalse(evaluation["body_repair_claimed"])


if __name__ == "__main__":
    unittest.main()
