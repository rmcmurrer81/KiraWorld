from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from tools import prepare_kira_r18_bounded_bald_authoring as prep


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class KiraR18BoundedBaldAuthoringPreparationTests(unittest.TestCase):
    def test_exact_frozen_sources_and_whole_r17_package_validate(self) -> None:
        blend = PROJECT_ROOT / prep.R17_BLEND_RELATIVE
        before = hashlib.sha256(blend.read_bytes()).hexdigest()
        result = prep.validate_sources(PROJECT_ROOT)
        after = hashlib.sha256(blend.read_bytes()).hexdigest()

        self.assertEqual(before, prep.R17_BLEND_SHA256)
        self.assertEqual(after, before)
        self.assertEqual(result["r17_package_file_count"], 34)
        self.assertEqual(
            result["r17_package_inventory_sha256"],
            prep.R17_PACKAGE_INVENTORY_SHA256,
        )

    def test_exact_ordered_pelvic_boundaries_are_frozen(self) -> None:
        self.assertEqual((len(prep.P1_BOUNDARY), len(set(prep.P1_BOUNDARY))), (70, 70))
        self.assertEqual((len(prep.P2_BOUNDARY), len(set(prep.P2_BOUNDARY))), (30, 30))
        self.assertEqual((len(prep.P3_BOUNDARY), len(set(prep.P3_BOUNDARY))), (90, 90))
        self.assertEqual(
            prep.index_set_sha256(prep.P1_BOUNDARY),
            "507b50a612b8fbe4f8946b7b58d58904e643db8e007e23922f859260cfe07c5b",
        )
        self.assertEqual(
            prep.index_set_sha256(prep.P2_BOUNDARY),
            "167d63dbf5aac79b2e1f9e1a6550c3a510ffb459d187b06dea90a06a043e0866",
        )
        self.assertEqual(
            prep.index_set_sha256(prep.P3_BOUNDARY),
            "bdcd9a9416a420404b9e472436a9272b5ed1c33082faa4048e0cae410539268a",
        )

    def test_plan_is_inactive_bald_append_only_and_component_bounded(self) -> None:
        plan = prep.build_plan(prep.validate_sources(PROJECT_ROOT))
        output = plan["future_output_contract"]
        self.assertTrue(output["append_only_new_directory"])
        self.assertTrue(output["inactive"])
        self.assertTrue(output["private_owner_review_only"])
        self.assertFalse(output["activated"])
        self.assertFalse(output["runtime_export_allowed"])
        self.assertFalse(output["hair_or_clothing_allowed"])

        masks = plan["authorized_masks"]
        self.assertEqual(
            set(masks),
            {
                "P1_front_connected_surface_first",
                "P2_rear_connected_surface_conditional",
                "P3_combined_exact_fallback",
                "N_nails",
                "S_rear_scalp",
                "K_knees",
                "F_face_and_brows",
                "H_hands",
                "T_feet",
            },
        )
        self.assertEqual(masks["F_face_and_brows"]["F2_only_weight_change"], {"from": 0.20, "to": 0.12})
        self.assertFalse(masks["N_nails"]["body_or_digit_mutation_authorized_by_N"])

    def test_movement_plan_has_required_pose_and_truth_boundaries(self) -> None:
        plan = prep.build_plan(prep.validate_sources(PROJECT_ROOT))
        movement = plan["movement_and_deformation_review"]
        states = set(movement["required_states"])
        self.assertIn("neutral_standing", states)
        self.assertIn("left_knee_bend_30_55_80_degrees", states)
        self.assertIn("right_knee_bend_30_55_80_degrees", states)
        self.assertIn("bilateral_knee_bend", states)
        self.assertIn("seated_side_contact", states)
        self.assertIn("neutral_restored_after_every_pose", states)
        self.assertIn("does not prove", movement["claim_limit"])
        self.assertFalse(plan["medical_truth_boundary"]["bathroom_function_implemented_or_claimed"])
        self.assertFalse(plan["medical_truth_boundary"]["pregnancy_or_reproductive_function_implemented_or_claimed"])

    def test_preparation_script_has_no_blender_or_runtime_mutation_api(self) -> None:
        path = PROJECT_ROOT / "tools/prepare_kira_r18_bounded_bald_authoring.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertNotIn("bpy", imports)
        for forbidden in (
            "save_as_mainfile",
            "bpy.ops.render",
            "bpy.ops.export",
            "Avatar/models/temp_ai",
            "body_selections/kira_runtime",
            "kira_world_shell_state.json",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
