from __future__ import annotations

import json
from pathlib import Path
import unittest

from Core.avatar_kira_appearance_delivery_v3 import (
    CONFIG_PATH,
    METHOD_ID,
    brow_profile,
    continuous_strip_topology,
    load_validated_kira_appearance_delivery_v3,
    regional_skin_multiplier,
    required_face_vertex_count,
    tapered_line_radius,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class KiraAppearanceDeliveryV3Tests(unittest.TestCase):
    def test_hash_bound_qualitative_reference_contract(self) -> None:
        config, report = load_validated_kira_appearance_delivery_v3(PROJECT_ROOT)
        self.assertEqual(config["method_id"], METHOD_ID)
        self.assertEqual(report["qualitative_reference_count"], 6)
        self.assertFalse(report["identity_match_claim_allowed"])
        self.assertFalse(report["measured_color_claim_allowed"])
        self.assertFalse(report["texture_or_geometry_copy_allowed"])
        self.assertTrue(report["natural_scalp_is_unchanged_primary_skin_surface"])

    def test_config_forbids_hair_and_body_geometry_changes(self) -> None:
        config = json.loads((PROJECT_ROOT / CONFIG_PATH).read_text(encoding="utf-8"))
        bald = config["bald_low_resource_boundary"]
        self.assertTrue(bald["natural_scalp_is_primary_skin_surface"])
        self.assertFalse(bald["separate_scalp_material_allowed"])
        for key in (
            "scalp_hair_provider_allowed",
            "scalp_hair_object_allowed",
            "scalp_hair_material_allowed",
            "scalp_hair_texture_allowed",
            "scalp_hair_controller_allowed",
        ):
            self.assertFalse(bald[key])
        self.assertTrue(config["forbidden"]["body_geometry_change"])
        self.assertTrue(config["forbidden"]["rig_or_weight_change"])

    def test_regional_tint_is_bilateral_bounded_and_non_flat(self) -> None:
        left = regional_skin_multiplier(
            normalized_lateral=-0.2,
            normalized_height=0.305,
            frontness=1.0,
        )
        right = regional_skin_multiplier(
            normalized_lateral=0.2,
            normalized_height=0.305,
            frontness=1.0,
        )
        torso = regional_skin_multiplier(
            normalized_lateral=0.0,
            normalized_height=0.55,
            frontness=0.5,
        )
        face = regional_skin_multiplier(
            normalized_lateral=0.075,
            normalized_height=0.895,
            frontness=1.0,
        )
        self.assertEqual(left, right)
        self.assertNotEqual(torso, face)
        for row in (left, right, torso, face):
            self.assertGreaterEqual(min(row), 0.9)
            self.assertLessEqual(max(row), 1.04)

    def test_brow_profile_is_continuous_shallow_and_tapered(self) -> None:
        samples = [
            brow_profile(u=-1.0 + index * 0.1, side_sign=1.0)
            for index in range(21)
        ]
        centers = [row["center_offset_eye_heights"] for row in samples]
        thickness = [row["half_thickness_eye_heights"] for row in samples]
        self.assertLess(max(centers), 0.40)
        self.assertGreater(min(centers), 0.17)
        self.assertGreater(thickness[10], thickness[0] * 2.0)
        self.assertGreater(thickness[10], thickness[-1] * 5.0)
        self.assertLess(
            max(abs(b - a) for a, b in zip(centers, centers[1:])),
            0.04,
        )

    def test_bilateral_brow_profiles_mirror(self) -> None:
        for u in (-1.0, -0.5, 0.0, 0.5, 1.0):
            left = brow_profile(u=u, side_sign=1.0)
            right = brow_profile(u=-u, side_sign=-1.0)
            self.assertAlmostEqual(
                left["center_offset_eye_heights"],
                right["center_offset_eye_heights"],
            )
            self.assertAlmostEqual(
                left["half_thickness_eye_heights"],
                right["half_thickness_eye_heights"],
            )

    def test_brow_topology_is_one_strip_not_strokes(self) -> None:
        topology = continuous_strip_topology(21)
        self.assertEqual(topology["vertex_count"], 42)
        self.assertEqual(topology["quad_count"], 20)
        self.assertTrue(topology["single_connected_strip"])
        self.assertEqual(topology["separate_stroke_count"], 0)
        with self.assertRaises(ValueError):
            continuous_strip_topology(20)

    def test_lash_and_lid_radius_tapers_without_breaking(self) -> None:
        self.assertAlmostEqual(tapered_line_radius(u=0.0), 1.0)
        self.assertAlmostEqual(tapered_line_radius(u=-1.0), 0.18)
        self.assertAlmostEqual(tapered_line_radius(u=1.0), 0.18)
        self.assertGreater(tapered_line_radius(u=0.5), 0.18)

    def test_polygon_membership_gate_handles_triangles_and_quads(self) -> None:
        self.assertEqual(required_face_vertex_count(3), 3)
        self.assertEqual(required_face_vertex_count(4), 3)
        self.assertEqual(required_face_vertex_count(5), 4)
        with self.assertRaises(ValueError):
            required_face_vertex_count(2)


if __name__ == "__main__":
    unittest.main()
