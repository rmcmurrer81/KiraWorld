from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from Core.avatar_natural_nail_delivery_v3 import (
    EXPECTED_FINGERNAIL_COUNT,
    EXPECTED_NAIL_COUNT,
    EXPECTED_TOENAIL_COUNT,
    FREE_EDGE_START_FACE_ROW,
    METHOD_ID,
    PROJECTION_GRID_SIZE,
    expected_nail_inventory,
    is_free_edge_face_row,
    material_contract,
    oval_half_width_scale,
    validate_attachment_measurement,
    validate_clearance_measurement,
    validate_delivery_records,
    validate_finite_points,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = PROJECT_ROOT / "tools" / "blender_avatar_natural_nail_delivery_v3.py"
TOOLING_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "natural_nail_delivery_v3.json"
)


class NaturalNailDeliveryV3Tests(unittest.TestCase):
    def test_inventory_has_exact_twenty_bilateral_terminal_bones(self) -> None:
        inventory = expected_nail_inventory()
        self.assertEqual(len(inventory), EXPECTED_NAIL_COUNT)
        self.assertEqual(
            sum(row["kind"] == "fingernail" for row in inventory),
            EXPECTED_FINGERNAIL_COUNT,
        )
        self.assertEqual(
            sum(row["kind"] == "toenail" for row in inventory),
            EXPECTED_TOENAIL_COUNT,
        )
        self.assertEqual(len({row["nail_id"] for row in inventory}), 20)
        self.assertEqual({row["side"] for row in inventory}, {"L", "R"})
        self.assertEqual(
            {row["bone"] for row in inventory if row["kind"] == "fingernail"},
            {
                f"finger{digit}-3.{side}"
                for side in ("L", "R")
                for digit in range(1, 6)
            },
        )
        self.assertEqual(
            {row["bone"] for row in inventory if row["kind"] == "toenail"},
            {
                f"toe{digit}-{'2' if digit == 1 else '3'}.{side}"
                for side in ("L", "R")
                for digit in range(1, 6)
            },
        )

    def test_silhouette_is_short_rounded_oval_not_square_or_pointed(self) -> None:
        profile = [
            oval_half_width_scale(row, PROJECTION_GRID_SIZE)
            for row in range(PROJECTION_GRID_SIZE)
        ]
        self.assertLess(profile[0], max(profile))
        self.assertLess(profile[-1], max(profile))
        self.assertGreater(profile[0], 0.55)
        self.assertGreater(profile[-1], 0.60)
        self.assertLess(profile[0], profile[-1])
        self.assertGreater(max(profile), 0.98)
        self.assertTrue(all(0.0 < value <= 1.0 for value in profile))

    def test_only_distal_face_band_is_softly_paler_free_edge(self) -> None:
        rows = [
            row
            for row in range(PROJECTION_GRID_SIZE - 1)
            if is_free_edge_face_row(row, PROJECTION_GRID_SIZE)
        ]
        self.assertEqual(rows, [FREE_EDGE_START_FACE_ROW])
        self.assertEqual(len(rows) * (PROJECTION_GRID_SIZE - 1), 8)
        contract = material_contract()
        self.assertTrue(contract["free_edge_is_paler_than_bed"])
        self.assertLess(contract["nail_bed"]["alpha"], 1.0)
        self.assertLess(contract["free_edge"]["alpha"], 1.0)
        self.assertFalse(contract["opaque_white_polish_allowed"])

    def test_finite_geometry_clearance_and_attachment_fail_closed(self) -> None:
        report = validate_finite_points(((0.0, 0.0, 0.0), (0.01, -0.02, 1.4)))
        self.assertTrue(report["finite_geometry"])
        with self.assertRaisesRegex(ValueError, "non-finite"):
            validate_finite_points(((math.nan, 0.0, 0.0),))
        self.assertTrue(
            validate_clearance_measurement(
                minimum_m=0.000060,
                maximum_m=0.000220,
                overlap_count=0,
            )["conservative_clearance_passed"]
        )
        with self.assertRaisesRegex(ValueError, "intersects"):
            validate_clearance_measurement(
                minimum_m=0.000060,
                maximum_m=0.000220,
                overlap_count=1,
            )
        with self.assertRaisesRegex(ValueError, "wrong terminal bone"):
            validate_attachment_measurement(
                expected_bone="finger1-3.L",
                actual_bone="finger2-3.L",
                parent_is_exact_armature=True,
                armature_modifier_targets_exact_rig=True,
                every_vertex_has_unit_terminal_bone_weight=True,
            )

    def test_full_record_contract_checks_count_dimensions_fit_and_follow(self) -> None:
        target_height = 1.651
        records = []
        for definition in expected_nail_inventory():
            records.append(
                {
                    "nail_id": definition["nail_id"],
                    "kind": definition["kind"],
                    "side": definition["side"],
                    "digit": definition["digit"],
                    "bone": definition["bone"],
                    "target_height_m": target_height,
                    "plate_length_m": target_height
                    * definition["length_height_fraction"]
                    * 0.96,
                    "plate_width_m": target_height
                    * definition["width_height_fraction"]
                    * 0.96,
                    "minimum_clearance_m": 0.000060,
                    "maximum_clearance_m": 0.000240,
                    "body_surface_triangle_overlap_count": 0,
                    "finite_geometry": True,
                    "parent_is_exact_armature": True,
                    "armature_modifier_targets_exact_rig": True,
                    "every_vertex_has_unit_terminal_bone_weight": True,
                    "rounded_oval_silhouette": True,
                    "free_edge_face_count": 8,
                }
            )
        report = validate_delivery_records(records)
        self.assertEqual(report["method_id"], METHOD_ID)
        self.assertEqual(report["component_count"], 20)
        self.assertTrue(report["all_clearances_and_overlap_gates_passed"])
        self.assertTrue(report["all_exact_terminal_bone_follow_gates_passed"])
        broken = [dict(row) for row in records]
        broken[0]["plate_width_m"] *= 0.20
        with self.assertRaisesRegex(ValueError, "width"):
            validate_delivery_records(broken)

    def test_blender_adapter_is_component_only_and_reprojects_oval_footprint(self) -> None:
        source = ADAPTER_PATH.read_text(encoding="utf-8")
        self.assertIn("def add_natural_nails_v3(", source)
        self.assertIn("body_tree.ray_cast(", source)
        self.assertIn("oval_half_width_scale(row, grid)", source)
        self.assertIn("v1.assign_rigid_bone(nail, armature, bone_name)", source)
        self.assertIn('"SOLIDIFY"', source)
        self.assertIn("validate_delivery_records(records)", source)
        self.assertNotIn("bpy.ops.render", source)
        self.assertNotIn("bpy.ops.wm.save_as_mainfile", source)
        self.assertNotIn("bpy.ops.export_scene", source)
        self.assertNotIn("body.data.vertices[", source)

    def test_avatar_builder_tooling_record_is_inactive_and_truth_bounded(self) -> None:
        payload = json.loads(TOOLING_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["method_id"], METHOD_ID)
        self.assertEqual(payload["output_contract"]["nail_count"], 20)
        self.assertFalse(payload["truth_boundaries"]["candidate_built_or_saved"])
        self.assertFalse(payload["truth_boundaries"]["runtime_activation_allowed"])
        self.assertTrue(
            payload["integration_contract"][
                "dynamic_pose_clearance_requalification_required"
            ]
        )


if __name__ == "__main__":
    unittest.main()
