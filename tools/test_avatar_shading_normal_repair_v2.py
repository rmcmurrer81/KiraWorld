from __future__ import annotations

from pathlib import Path
import unittest

from Core.avatar_shading_normal_repair_v2 import (
    METHOD_ID,
    load_validated_avatar_shading_normal_repair_v2,
    rear_scalp_mask_weight_v2,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AvatarShadingNormalRepairV2Tests(unittest.TestCase):
    def test_contract_is_scalp_only_and_geometry_safe(self) -> None:
        config, report = load_validated_avatar_shading_normal_repair_v2(PROJECT_ROOT)
        self.assertEqual(config["method_id"], METHOD_ID)
        self.assertFalse(report["geometry_or_weight_edits_allowed"])
        self.assertFalse(report["knee_repair_claimed"])
        self.assertFalse(report["scalp_hair_dependencies_allowed"])
        self.assertEqual(
            config["diagnosis"]["bilateral_knees"],
            "separate flexed-geometry and self-shadow defect; not repaired or concealed here",
        )

    def test_mask_selects_only_lower_rear_scalp_band(self) -> None:
        center = rear_scalp_mask_weight_v2(
            normalized_body_height=0.9,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        front = rear_scalp_mask_weight_v2(
            normalized_body_height=0.9,
            normalized_head_rearwardness=0.4,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        neck = rear_scalp_mask_weight_v2(
            normalized_body_height=0.84,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        crown = rear_scalp_mask_weight_v2(
            normalized_body_height=0.97,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        side = rear_scalp_mask_weight_v2(
            normalized_body_height=0.9,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=1.1,
            existing_head_neck_membership=0.5,
        )
        self.assertAlmostEqual(center, 1.0)
        self.assertEqual(front, 0.0)
        self.assertEqual(neck, 0.0)
        self.assertEqual(crown, 0.0)
        self.assertEqual(side, 0.0)

    def test_mask_has_soft_boundary(self) -> None:
        edge = rear_scalp_mask_weight_v2(
            normalized_body_height=0.875,
            normalized_head_rearwardness=0.7,
            normalized_head_lateral=0.9,
            existing_head_neck_membership=0.2,
        )
        self.assertGreater(edge, 0.0)
        self.assertLess(edge, 1.0)

    def test_blender_tool_uses_component_exact_outside_mask_gate(self) -> None:
        source = (
            PROJECT_ROOT / "tools/blender_avatar_shading_normal_repair_v2.py"
        ).read_text(encoding="utf-8")
        self.assertIn("outside_coordinate_delta", source)
        self.assertIn("normals_split_custom_set_from_vertices(result)", source)
        self.assertNotIn("vertex.co =", source)
        self.assertNotIn("modifiers.new", source)


if __name__ == "__main__":
    unittest.main()
