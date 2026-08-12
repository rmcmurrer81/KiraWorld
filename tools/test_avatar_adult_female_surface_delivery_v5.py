"""Pure/static tests for the final bounded harmonic surface repair v5."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/tooling/adult_female_surface_delivery_v5_final_bounded_repair.json"
)
ADAPTER_PATH = (
    PROJECT_ROOT
    / "tools/blender_author_adult_female_external_surface_delivery_v5.py"
)

from Core.avatar_adult_female_surface_authoring import (
    REQUIRED_RELATIONSHIPS,
    frame_from_mapping,
)
from Core.avatar_adult_female_surface_delivery_v5 import (
    BASE_DETAIL_METHOD_ID,
    FRONT_FEATURE_SAMPLE_POINTS,
    METHOD_ID,
    HarmonicSurfaceParameters,
    anchor_restore_weight,
    build_authoring_contract,
    feature_sample_displacements,
    parameters_from_mapping,
    relationship_support,
)


class AdultFemaleSurfaceDeliveryV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.parameters = parameters_from_mapping(self.config["parameters"])
        self.front_frame = frame_from_mapping(
            self.config["front_visible_sheet_frame"]
        )

    def test_append_only_method_requires_exact_v4_staging(self) -> None:
        self.assertTrue(METHOD_ID.endswith("_delivery_v5"))
        self.assertTrue(BASE_DETAIL_METHOD_ID.endswith("_delivery_v4"))
        self.assertEqual(METHOD_ID, self.config["method_id"])
        self.assertEqual(
            BASE_DETAIL_METHOD_ID,
            self.config["required_base_detail_method_id"],
        )

    def test_exact_anchor_and_observed_component_bounds_are_fail_closed(self) -> None:
        self.assertEqual(13380, self.parameters.original_anchor_vertex_count)
        self.assertLessEqual(
            self.parameters.minimum_front_component_vertices,
            self.config["reconstruction"][
                "front_component_observed_in_r17_staging"
            ],
        )
        self.assertGreaterEqual(
            self.parameters.maximum_front_component_vertices,
            self.config["reconstruction"][
                "front_component_observed_in_r17_staging"
            ],
        )
        self.assertEqual(
            134,
            self.config["reconstruction"][
                "front_anchor_neighbors_observed_in_r17_staging"
            ],
        )
        with self.assertRaisesRegex(ValueError, "original_anchor_vertex_count"):
            parameters_from_mapping({"original_anchor_vertex_count": 13379})
        with self.assertRaisesRegex(ValueError, "unknown delivery-v5 parameter"):
            parameters_from_mapping({"invented": True})

    def test_anchor_restore_boundary_is_compact_quintic_c2(self) -> None:
        self.assertEqual(1.0, anchor_restore_weight(0.0, -0.02, self.parameters))
        self.assertEqual(0.0, anchor_restore_weight(1.53, -0.02, self.parameters))
        edge = anchor_restore_weight(1.519, -0.02, self.parameters)
        self.assertGreaterEqual(edge, 0.0)
        self.assertLess(edge, 1.0e-5)
        self.assertGreater(
            anchor_restore_weight(1.20, -0.02, self.parameters),
            edge,
        )

    def test_relationship_support_is_compact_and_has_flat_outer_boundary(self) -> None:
        self.assertEqual(1.0, relationship_support(0.0, 0.25))
        self.assertEqual(0.0, relationship_support(0.78, 0.25))
        self.assertLess(relationship_support(0.779, 0.25), 1.0e-6)
        self.assertEqual(0.0, relationship_support(0.0, 1.14))

    def test_front_relationship_samples_are_complete_signed_and_very_subtle(self) -> None:
        samples = feature_sample_displacements(self.parameters)
        self.assertEqual(set(FRONT_FEATURE_SAMPLE_POINTS), set(samples))
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
        ):
            self.assertGreater(samples[name], 0.0, name)
        for name in ("vestibule", "urethral_opening", "vaginal_opening"):
            self.assertLess(samples[name], 0.0, name)
        self.assertLess(max(abs(value) for value in samples.values()), 0.00045)

    def test_contract_retains_rear_v4_and_forbids_expansive_changes(self) -> None:
        contract = build_authoring_contract(
            PROJECT_ROOT,
            self.front_frame,
            self.parameters,
        )
        self.assertEqual(METHOD_ID, contract["method_id"])
        self.assertEqual(list(REQUIRED_RELATIONSHIPS), contract["required_relationships"])
        self.assertTrue(contract["rear_v4_relationships_preserved_unchanged"])
        self.assertTrue(contract["harmonic_reconstruction"])
        self.assertFalse(contract["topology_change_allowed"])
        self.assertFalse(contract["source_anatomy_geometry_copy_allowed"])
        self.assertFalse(contract["separate_anatomy_mesh_allowed"])
        self.assertFalse(contract["boolean_anatomy_union_allowed"])
        self.assertFalse(contract["internal_tract_claim_allowed"])
        self.assertFalse(contract["runtime_activation_allowed"])
        self.assertFalse(contract["candidate_build_allowed"])
        self.assertEqual(2, contract["visual_attempt_limit"])
        self.assertFalse(contract["v6_allowed_after_this_attempt"])

    def test_adapter_is_coordinate_only_and_exposes_neutral_anchor_api(self) -> None:
        source = ADAPTER_PATH.read_text(encoding="utf-8")
        compile(source, str(ADAPTER_PATH), "exec")
        lowered = source.lower()
        for forbidden in (
            "bpy.ops.render",
            "save_as_mainfile",
            "export_scene",
            "bpy.data.objects.new",
            "bmesh.ops.subdivide_edges",
            "bmesh.ops.delete",
            "if __name__ ==",
        ):
            self.assertNotIn(forbidden, lowered)
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name
            == "repair_existing_continuous_adult_female_surface_delivery_v5"
        )
        keyword_only = [argument.arg for argument in function.args.kwonlyargs]
        for required in (
            "neutral_original_positions",
            "front_frame",
            "parameters",
        ):
            self.assertIn(required, keyword_only)
        self.assertIn("_harmonic_reconstruct", source)
        self.assertIn("_new_vertex_components", source)
        self.assertIn("_bounded_local_intersection_rollback", source)
        self.assertIn("delivery_v5_requires_exact_v4_base", source)
        self.assertIn("rear_v4_component_changed", source)

    def test_tooling_record_marks_this_as_final_inactive_visual_attempt(self) -> None:
        self.assertEqual(
            "FINAL_BOUNDED_INACTIVE_COMPONENT_REPAIR_AWAITING_VISUAL_ATTEMPT_2",
            self.config["status"],
        )
        self.assertTrue(self.config["hard_gates"]["rear_v4_component_unchanged"])
        self.assertTrue(self.config["hard_gates"]["automatic_rollback_on_failure"])
        self.assertTrue(self.config["forbidden"]["body_restart"])
        self.assertTrue(self.config["forbidden"]["candidate_build"])
        self.assertTrue(self.config["forbidden"]["runtime_activation"])
        self.assertTrue(self.config["forbidden"]["v6_after_visual_attempt"])
        self.assertEqual(
            "repair_existing_continuous_adult_female_surface_delivery_v5",
            self.config["integration_api"]["callable"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
