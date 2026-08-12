from __future__ import annotations

import json
from pathlib import Path
import unittest

from Core.avatar_shading_normal_repair_v1 import (
    CONFIG_PATH,
    METHOD_ID,
    combined_shading_mask_weight,
    load_validated_avatar_shading_normal_repair_v1,
    rear_scalp_mask_weight,
    smoothstep,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AvatarShadingNormalRepairV1Tests(unittest.TestCase):
    def test_config_contract_is_geometry_and_rig_safe(self) -> None:
        config, report = load_validated_avatar_shading_normal_repair_v1(
            PROJECT_ROOT
        )
        self.assertEqual(config["method_id"], METHOD_ID)
        self.assertFalse(report["geometry_edits_allowed"])
        self.assertFalse(report["existing_rig_weight_edits_allowed"])
        self.assertFalse(report["material_edits_allowed"])
        self.assertFalse(report["scalp_hair_dependencies_allowed"])

    def test_modifier_is_one_final_mask_limited_weighted_normal(self) -> None:
        config = json.loads((PROJECT_ROOT / CONFIG_PATH).read_text(encoding="utf-8"))
        modifier = config["normal_modifier"]
        self.assertEqual(modifier["type"], "WEIGHTED_NORMAL")
        self.assertEqual(modifier["mode"], "FACE_AREA_WITH_ANGLE")
        self.assertTrue(modifier["must_be_last_modifier"])
        self.assertEqual(
            modifier["mask_vertex_group"],
            "AVATAR_BUILDER_SHADING_NORMAL_MASK_V1",
        )

    def test_rear_scalp_mask_is_localized_and_soft(self) -> None:
        center = rear_scalp_mask_weight(
            normalized_body_height=0.9,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        front = rear_scalp_mask_weight(
            normalized_body_height=0.9,
            normalized_head_rearwardness=0.4,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        low = rear_scalp_mask_weight(
            normalized_body_height=0.8,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        high = rear_scalp_mask_weight(
            normalized_body_height=0.98,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=0.0,
            existing_head_neck_membership=0.5,
        )
        lateral = rear_scalp_mask_weight(
            normalized_body_height=0.9,
            normalized_head_rearwardness=0.9,
            normalized_head_lateral=1.1,
            existing_head_neck_membership=0.5,
        )
        edge = rear_scalp_mask_weight(
            normalized_body_height=0.86,
            normalized_head_rearwardness=0.7,
            normalized_head_lateral=0.9,
            existing_head_neck_membership=0.2,
        )
        self.assertAlmostEqual(center, 1.0)
        self.assertEqual(front, 0.0)
        self.assertEqual(low, 0.0)
        self.assertEqual(high, 0.0)
        self.assertEqual(lateral, 0.0)
        self.assertGreater(edge, 0.0)
        self.assertLess(edge, 1.0)

    def test_combined_mask_uses_max_not_additive_overdrive(self) -> None:
        self.assertEqual(
            combined_shading_mask_weight(
                scalp_weight=0.4,
                left_knee_weight=0.8,
                right_knee_weight=0.2,
            ),
            0.8,
        )
        self.assertEqual(
            combined_shading_mask_weight(
                scalp_weight=2.0,
                left_knee_weight=0.0,
                right_knee_weight=0.0,
            ),
            1.0,
        )

    def test_smoothstep_bounds_and_rejects_reversed_edges(self) -> None:
        self.assertEqual(smoothstep(0.0, 1.0, -1.0), 0.0)
        self.assertEqual(smoothstep(0.0, 1.0, 2.0), 1.0)
        self.assertAlmostEqual(smoothstep(0.0, 1.0, 0.5), 0.5)
        with self.assertRaises(ValueError):
            smoothstep(1.0, 1.0, 1.0)


if __name__ == "__main__":
    unittest.main()
