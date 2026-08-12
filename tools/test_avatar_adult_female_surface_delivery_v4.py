"""Pure/static tests for the topology-preserving organic surface repair v4."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from Core.avatar_adult_female_surface_authoring import (
    REQUIRED_RELATIONSHIPS,
    frame_from_mapping,
)
from Core.avatar_adult_female_surface_authoring_v3 import (
    VisibleSurfaceParameters as V3Parameters,
    feature_sample_displacements as v3_feature_sample_displacements,
)
from Core.avatar_adult_female_surface_delivery_v4 import (
    BASE_DETAIL_METHOD_ID,
    COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES,
    COLLISION_REPAIR_MAX_PASSES,
    COLLISION_REPAIR_MAX_VERTICES,
    COLLISION_REPAIR_RETENTION_BY_RING,
    FRONT_FEATURE_SAMPLE_POINTS,
    METHOD_ID,
    OrganicSurfaceParameters,
    alignment_blend,
    build_authoring_contract,
    feature_sample_displacements,
    front_landmark_memberships,
    front_support_taper,
    parameters_from_mapping,
    rear_landmark_memberships,
    rear_support_taper,
)


CONFIG_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/tooling/"
    "adult_female_surface_delivery_v4_inactive_refinement.json"
)
ADAPTER_PATH = (
    PROJECT_ROOT
    / "tools/blender_author_adult_female_external_surface_delivery_v4.py"
)


class AdultFemaleSurfaceDeliveryV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.parameters = parameters_from_mapping(self.config["parameters"])
        self.front_frame = frame_from_mapping(self.config["front_visible_sheet_frame"])
        self.rear_frame = frame_from_mapping(self.config["rear_anal_sheet_frame"])

    def test_method_is_append_only_and_requires_exact_v3(self) -> None:
        self.assertTrue(METHOD_ID.endswith("_delivery_v4"))
        self.assertTrue(BASE_DETAIL_METHOD_ID.endswith("_v3"))
        self.assertEqual(METHOD_ID, self.config["method_id"])
        self.assertEqual(
            BASE_DETAIL_METHOD_ID,
            self.config["required_base_detail_method_id"],
        )

    def test_parameters_fail_closed_and_match_tooling_config(self) -> None:
        self.assertEqual(OrganicSurfaceParameters(**self.config["parameters"]), self.parameters)
        with self.assertRaisesRegex(ValueError, "unknown delivery-v4 parameter"):
            parameters_from_mapping({"invented": 1})
        with self.assertRaisesRegex(ValueError, "front_prominence_scale_m"):
            parameters_from_mapping({"front_prominence_scale_m": 0.006})
        with self.assertRaisesRegex(ValueError, "fairing_iterations"):
            parameters_from_mapping({"fairing_iterations": 5})
        with self.assertRaisesRegex(ValueError, "deterministic_asymmetry_fraction"):
            parameters_from_mapping({"deterministic_asymmetry_fraction": 0.2})

    def test_elliptic_support_removes_rectangular_corner_and_is_compact(self) -> None:
        self.assertEqual(1.0, front_support_taper(0.0, 0.27))
        axis_lateral = front_support_taper(0.62, 0.27)
        axis_longitudinal = front_support_taper(0.0, 0.72)
        rejected_plate_corner = front_support_taper(0.62, 0.72)
        self.assertGreater(axis_lateral, 0.10)
        self.assertGreater(axis_longitudinal, 0.50)
        self.assertLess(rejected_plate_corner, axis_lateral * 0.10)
        self.assertEqual(0.0, front_support_taper(0.83, 0.27))
        self.assertEqual(0.0, rear_support_taper(0.63, 0.04))

    def test_outer_transition_is_quintic_and_numerically_flat(self) -> None:
        self.assertEqual(0.0, front_support_taper(0.82, 0.27))
        self.assertLess(front_support_taper(0.819, 0.27), 1.0e-6)
        self.assertLess(front_support_taper(0.818, 0.27), 1.0e-6)
        self.assertEqual(0.0, alignment_blend(0.05, minimum_alignment=0.06, fade_width=0.26))
        self.assertEqual(1.0, alignment_blend(0.40, minimum_alignment=0.06, fade_width=0.26))

    def test_relationship_samples_are_complete_signed_and_low_relief(self) -> None:
        samples = feature_sample_displacements(self.parameters)
        self.assertEqual(
            set(FRONT_FEATURE_SAMPLE_POINTS).union(
                {"perineal_transition", "anal_recess", "anal_rim_left"}
            ),
            set(samples),
        )
        for name in (
            "mons_pubis",
            "labia_majora_left",
            "labia_majora_right",
            "labia_minora_left",
            "labia_minora_right",
            "clitoral_hood",
            "clitoris",
            "urethral_rim_left",
            "vaginal_rim_left",
            "fourchette",
            "perineal_transition",
            "anal_rim_left",
        ):
            self.assertGreater(samples[name], 0.0, name)
        for name in ("vestibule", "urethral_opening", "vaginal_opening", "anal_recess"):
            self.assertLess(samples[name], 0.0, name)
        self.assertLess(max(abs(value) for value in samples.values()), 0.00125)

    def test_v4_is_materially_subtler_than_rejected_v3(self) -> None:
        old = v3_feature_sample_displacements(V3Parameters())
        new = feature_sample_displacements(self.parameters)
        self.assertLess(
            max(abs(value) for value in new.values()),
            max(abs(value) for value in old.values()) * 0.35,
        )
        asymmetry_ratio = new["labia_majora_left"] / new["labia_majora_right"]
        self.assertGreater(asymmetry_ratio, 1.0)
        self.assertLess(asymmetry_ratio, 1.10)

    def test_relationship_landmarks_remain_deterministic(self) -> None:
        left = front_landmark_memberships(0.23, 0.18)
        right = front_landmark_memberships(-0.23, 0.18)
        self.assertIn("paired_labia_majora__left", left)
        self.assertNotIn("paired_labia_majora__right", left)
        self.assertIn("paired_labia_majora__right", right)
        self.assertNotIn("paired_labia_majora__left", right)
        posterior = rear_landmark_memberships(0.0, 0.14)
        self.assertIn("perineal_transition_to_anus_and_pelvic_floor", posterior)
        self.assertIn(
            "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess",
            posterior,
        )

    def test_contract_forbids_topology_weight_landmark_and_runtime_drift(self) -> None:
        contract = build_authoring_contract(
            PROJECT_ROOT,
            self.front_frame,
            self.rear_frame,
            self.parameters,
        )
        self.assertEqual(METHOD_ID, contract["method_id"])
        self.assertEqual(list(REQUIRED_RELATIONSHIPS), contract["relationships"])
        self.assertFalse(contract["topology_change_allowed"])
        self.assertTrue(contract["source_vertex_indices_must_be_preserved"])
        self.assertTrue(contract["source_skin_weights_must_be_preserved_exactly"])
        self.assertTrue(contract["source_landmark_memberships_must_be_preserved_exactly"])
        self.assertTrue(contract["same_primary_surface_required"])
        self.assertFalse(contract["separate_anatomy_mesh_allowed"])
        self.assertFalse(contract["boolean_anatomy_union_allowed"])
        self.assertFalse(contract["internal_tract_claim_allowed"])
        self.assertFalse(contract["runtime_activation_allowed"])
        self.assertTrue(contract["owner_visual_review_required"])
        repair = contract["bounded_new_intersection_repair"]
        self.assertEqual(COLLISION_REPAIR_MAX_PASSES, repair["maximum_passes"])
        self.assertEqual(COLLISION_REPAIR_MAX_VERTICES, repair["maximum_vertices"])
        self.assertEqual(
            COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES,
            repair["maximum_fraction_of_changed_vertices"],
        )
        self.assertEqual(
            list(COLLISION_REPAIR_RETENTION_BY_RING),
            repair["retention_by_offending_face_ring"],
        )
        self.assertEqual(0, repair["final_new_pair_count_required"])

    def test_adapter_is_component_only_and_exposes_bounded_integration_api(self) -> None:
        source = ADAPTER_PATH.read_text(encoding="utf-8")
        compile(source, str(ADAPTER_PATH), "exec")
        lowered = source.lower()
        for forbidden in (
            "bpy.ops.render",
            "save_as_mainfile",
            "export_scene",
            "bpy.data.objects.new",
            "bmesh.ops.subdivide_edges",
            "if __name__ ==",
        ):
            self.assertNotIn(forbidden, lowered)
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name
            == "refine_existing_continuous_adult_female_surface_delivery_v4"
        )
        keyword_only = [argument.arg for argument in function.args.kwonlyargs]
        for required in (
            "front_frame",
            "rear_frame",
            "parameters",
            "legacy_v3_front_prominence_scale_m",
            "legacy_v3_rear_prominence_scale_m",
            "legacy_v3_minimum_front_normal_alignment",
            "legacy_v3_minimum_rear_normal_alignment",
            "front_visible_sheet_minimum_outward_depth_m",
            "rear_visible_sheet_minimum_outward_depth_m",
        ):
            self.assertIn(required, keyword_only)
        self.assertIn("_group_assignment_digest", source)
        self.assertIn("_nonadjacent_intersection_face_pairs", source)
        self.assertIn("_bounded_local_intersection_rollback", source)
        self.assertIn("proposed_positions[index] - source_positions[index]", source)
        self.assertIn("FAILED_CHANGED_REGION_FRACTION_EXCEEDED", source)
        self.assertIn("delivery_v4_requires_exact_v3_base", source)

    def test_tooling_record_keeps_component_inactive_and_identity_free(self) -> None:
        self.assertEqual(
            "UNPROMOTED_INACTIVE_TARGETED_VISUAL_REPAIR_COMPONENT",
            self.config["status"],
        )
        gates = self.config["topology_rig_and_landmark_gates"]
        self.assertFalse(gates["topology_change_allowed"])
        self.assertTrue(gates["skin_weight_assignments_preserved_exactly"])
        self.assertTrue(gates["all_landmark_memberships_preserved_exactly"])
        self.assertFalse(self.config["adult_reference_use"]["copy_identity"])
        self.assertFalse(self.config["adult_reference_use"]["copy_texture"])
        self.assertTrue(self.config["forbidden"]["hair_dependency"])
        self.assertTrue(self.config["forbidden"]["runtime_activation"])
        repair = self.config["bounded_new_intersection_repair"]
        self.assertEqual(COLLISION_REPAIR_MAX_PASSES, repair["maximum_passes"])
        self.assertEqual(COLLISION_REPAIR_MAX_VERTICES, repair["maximum_vertices"])
        self.assertEqual(
            list(COLLISION_REPAIR_RETENTION_BY_RING),
            repair["retention_by_offending_face_ring"],
        )
        self.assertTrue(repair["source_inherited_pairs_are_not_repaired_or_hidden"])
        self.assertEqual(0, repair["final_new_pair_count_required"])
        self.assertEqual(
            "refine_existing_continuous_adult_female_surface_delivery_v4",
            self.config["integration_api"]["callable"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
