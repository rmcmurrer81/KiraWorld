from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

from tools import blender_diagnose_kira_r24_blackproject_ordered_topology_attempt30 as attempt30


ROOT = Path(__file__).resolve().parents[1]


class R24BlackProjectAttempt30StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = attempt30.load_overlay()
        cls.verified = attempt30.verify_overlay_bindings(cls.config)
        cls.runtime = attempt30.build_runtime_config(cls.config)
        cls.source28 = attempt30.ATTEMPT28_WORKER.read_text(encoding="utf-8")
        cls.source30 = attempt30.derive_attempt30_source(cls.source28)
        cls.namespace: dict[str, object] = {
            "__name__": "attempt30_static_derived",
            "__file__": str(attempt30.ATTEMPT28_WORKER),
            "__builtins__": __builtins__,
            "ATTEMPT30_RUNTIME_CONFIG": cls.runtime,
        }
        exec(compile(cls.source30, "<attempt30-derived-static>", "exec"), cls.namespace)
        cls.attempt29_diagnostic = json.loads(
            (ROOT / cls.config["bindings"]["attempt29_diagnostic"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_attempt28_and_attempt29_packages_are_exact(self) -> None:
        for key in ("preserved_attempt28_package", "preserved_attempt29_package"):
            package = self.config[key]
            rows = [self.verified[name] for name in package["binding_names"]]
            self.assertEqual(len(rows), package["file_count"])
            self.assertEqual(sum(row["bytes"] for row in rows), package["total_bytes"])
        self.assertEqual(self.config["preserved_attempt28_package"]["file_count"], 9)
        self.assertEqual(self.config["preserved_attempt28_package"]["total_bytes"], 72757)
        self.assertEqual(self.config["preserved_attempt29_package"]["file_count"], 10)
        self.assertEqual(self.config["preserved_attempt29_package"]["total_bytes"], 104277)
        self.assertFalse(
            (ROOT / "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_30").exists()
        )

    def test_attempt29_evidence_proves_order_not_coordinate_coincidence(self) -> None:
        diagnostic = self.attempt29_diagnostic
        direct = diagnostic["attempt29_direct_chart"]
        alignment = direct["alignment"]
        contract = self.config["source_identity_contract"]
        self.assertEqual(alignment["orientation"], "forward")
        self.assertEqual(alignment["rotation"], 0)
        self.assertEqual(
            alignment["capture_source_index_to_mesh_vertex_index"],
            contract["ordered_cycle_mesh_vertex_indices"],
        )
        self.assertEqual(
            diagnostic["boundary_cycle_mesh_vertex_indices_sha256"],
            contract["ordered_cycle_mesh_vertex_indices_sha256"],
        )
        self.assertGreater(direct["maximum_distance_m"], 1.0e-10)
        self.assertLessEqual(
            direct["maximum_distance_m"],
            contract["maximum_numeric_sanity_xy_distance_m"],
        )
        self.assertLessEqual(
            direct["rms_distance_m"],
            contract["maximum_numeric_sanity_rms_xy_distance_m"],
        )
        alternate = diagnostic["attempt18_body_matrix_chart"]
        self.assertFalse(alternate["matches_tolerance"])
        self.assertAlmostEqual(
            alternate["details"]["maximum_distance_m"], 0.6679807232405361
        )
        self.assertEqual(
            diagnostic["classification"],
            "CHART_MISMATCH_NOT_EXPLAINED_BY_BODY_MATRIX_ALONE",
        )

    def _identity_inputs(self) -> tuple[object, dict, dict, list, dict]:
        contract = self.config["source_identity_contract"]
        diagnostic = self.attempt29_diagnostic
        obj = SimpleNamespace(
            name=contract["object_name"],
            data=SimpleNamespace(name=contract["mesh_name"]),
        )
        current = {
            "face_count": contract["current_domain_face_count"],
            "face_indices_sha256": contract["current_domain_face_sha256"],
            "vertex_count": contract["current_domain_vertex_count"],
            "vertex_indices_sha256": contract["current_domain_vertex_sha256"],
            "boundary_edge_count": contract["current_boundary_edge_count"],
            "boundary_edge_indices_sha256": contract["current_boundary_edge_sha256"],
            "boundary_cycle_mesh_vertex_indices": list(
                contract["ordered_cycle_mesh_vertex_indices"]
            ),
            "projected_boundary_xy_m": copy.deepcopy(
                diagnostic["attempt29_direct_chart"]["aligned_computed_xy_m"]
            ),
            "chart": {"maximum_absolute_boundary_deviation_m": 0.0009},
        }
        expected = copy.deepcopy(diagnostic["expected_attempt27_xy_m"])
        capture = {
            "fixed_pslg": {
                "boundary_coordinates": [
                    {"boundary_source_index": index, "xy": point}
                    for index, point in enumerate(expected)
                ]
            }
        }
        alignment = copy.deepcopy(diagnostic["attempt29_direct_chart"]["alignment"])
        return obj, current, capture, expected, alignment

    def test_exact_topology_identity_and_bounded_sanity_pass(self) -> None:
        helper = self.namespace["attempt30_source_identity_evidence"]
        obj, current, capture, expected, alignment = self._identity_inputs()
        evidence = helper(
            self.runtime, obj, current, capture, expected, alignment  # type: ignore[misc]
        )
        self.assertTrue(evidence["all_identity_and_sanity_checks_pass"])
        self.assertTrue(all(evidence["checks"].values()))
        self.assertFalse(evidence["coordinate_coincidence_used_as_identity"])
        self.assertEqual(
            evidence["composite_topology_record_sha256"],
            self.config["source_identity_contract"]["composite_topology_record_sha256"],
        )

    def test_identity_contract_fails_closed_on_order_topology_or_numeric_drift(self) -> None:
        helper = self.namespace["attempt30_source_identity_evidence"]
        obj, current, capture, expected, alignment = self._identity_inputs()
        current["boundary_cycle_mesh_vertex_indices"][0:2] = [7, 4]
        with self.assertRaisesRegex(RuntimeError, "ordered topology identity"):
            helper(self.runtime, obj, current, capture, expected, alignment)  # type: ignore[misc]

        obj, current, capture, expected, alignment = self._identity_inputs()
        current["face_indices_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "ordered topology identity"):
            helper(self.runtime, obj, current, capture, expected, alignment)  # type: ignore[misc]

        obj, current, capture, expected, alignment = self._identity_inputs()
        alignment["maximum_xy_distance_m"] = 5.000000000000001e-10
        with self.assertRaisesRegex(RuntimeError, "numeric sanity"):
            helper(self.runtime, obj, current, capture, expected, alignment)  # type: ignore[misc]

    def test_derived_source_maps_only_after_identity_and_stops_no_save(self) -> None:
        source = self.source30
        identity_at = source.index("source_identity_evidence = attempt30_source_identity_evidence")
        targeted_at = source.index("targeted = []")
        ring_at = source.index("ring_rows = []")
        diagnostic_at = source.index('"source_identity_contract_evidence"')
        self.assertLess(identity_at, targeted_at)
        self.assertLess(targeted_at, ring_at)
        self.assertGreater(diagnostic_at, identity_at)
        self.assertNotIn("source chart does not match Attempt 27 capture", source)
        self.assertIn("targeted_complete_vertex_stars_", source)
        self.assertIn("uniform_face_ring_", source)
        self.assertIn("diagnostic-only stop before triangulation or mesh mutation", source)
        self.assertNotIn("bpy.ops.wm.save", source)
        self.assertNotIn("bmesh.ops", source)
        self.assertNotIn(".matrix_world =", source)
        self.assertNotIn("from_pydata", source)
        self.assertNotIn(".co =", source)

    def test_scope_and_all_geometry_gates_remain_unchanged(self) -> None:
        scope = self.config["scope"]
        self.assertTrue(scope["boundary_candidate_mapping_allowed"])
        for key in (
            "body_geometry_mutation_allowed",
            "patch_geometry_mutation_allowed",
            "triangulation_allowed",
            "reconstruction_allowed",
            "render_allowed",
            "blend_save_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "quality_gate_reduction_allowed",
            "sanitation_weakening_allowed",
        ):
            self.assertFalse(scope[key])
        hard = self.config["unchanged_hard_gates"]
        self.assertEqual(hard["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(hard["minimum_new_triangle_world_area_m2"], 1.0e-10)
        self.assertEqual(hard["global_seam_vertex_count"], 34)
        self.assertEqual(hard["global_seam_coordinate_delta_m"], 0.0)
        self.assertEqual(hard["standalone_patch_exact_genuine_intersections"], 0)
        self.assertEqual(hard["joined_patch_related_exact_genuine_intersections"], 0)
        self.assertEqual(hard["new_whole_body_exact_genuine_intersections"], 0)

    def test_overlay_validation_fails_closed(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"] = 11.999
        with self.assertRaisesRegex(RuntimeError, "hard gate"):
            attempt30.validate_overlay(changed)
        changed = copy.deepcopy(self.config)
        changed["source_identity_contract"]["ordered_cycle_mesh_vertex_indices"][0] = 7
        with self.assertRaisesRegex(RuntimeError, "ordered source cycle"):
            attempt30.validate_overlay(changed)
        changed = copy.deepcopy(self.config)
        changed["scope"]["triangulation_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden"):
            attempt30.validate_overlay(changed)

    def test_truth_is_diagnostic_only(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["attempts28_and29_preserved_exact"])
        self.assertTrue(truth["attempt29_direct_source_identity_proven_by_ordered_topology"])
        self.assertTrue(truth["attempt29_body_matrix_hypothesis_rejected"])
        self.assertTrue(truth["coordinate_coincidence_identity_replaced"])
        self.assertFalse(truth["fixed_32_segment_pslg_global_12_degree_feasibility"])
        for key in (
            "attempt30_blender_execution_performed",
            "attempt30_source_ring_mapping_performed",
            "attempt30_mesh_mutation_performed",
            "attempt30_reconstruction_reached",
            "attempt30_render_reached",
            "attempt30_blend_saved",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[key])


if __name__ == "__main__":
    unittest.main()
