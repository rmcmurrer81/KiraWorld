from __future__ import annotations

import unittest
from pathlib import Path

from Core.avatar_profiled_nonanatomy_presentation_v2 import (
    FACE_TARGETS,
    SKIN_CALIBRATION,
    component_frame_scale,
    rounded_nail_row_scale,
    silhouette_roughness,
    validate_face_target_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProfiledNonanatomyPresentationV2Tests(unittest.TestCase):
    def test_exact_face_target_manifest_is_hash_bound_and_identity_honest(self) -> None:
        report = validate_face_target_manifest(PROJECT_ROOT)
        self.assertTrue(report["exact_hashes_verified"])
        self.assertEqual(report["target_count"], 10)
        self.assertFalse(report["identity_match_claim_allowed"])
        self.assertTrue(report["qualitative_owner_direction_only"])
        self.assertLessEqual(report["maximum_target_weight"], 0.25)

    def test_face_direction_covers_hard_geometry_features(self) -> None:
        features = {str(row["feature"]) for row in FACE_TARGETS}
        self.assertTrue(
            {"chin", "nose", "mouth", "upper_lip", "lower_lip", "cheekbone"}
            <= features
        )

    def test_skin_calibration_is_warmer_darker_and_truth_bounded(self) -> None:
        source = SKIN_CALIBRATION["source_profile_srgb_hex"]
        calibrated = SKIN_CALIBRATION["calibrated_warm_non_pale_srgb_hex"]
        source_rgb = tuple(int(source[index : index + 2], 16) for index in (1, 3, 5))
        calibrated_rgb = tuple(int(calibrated[index : index + 2], 16) for index in (1, 3, 5))
        self.assertTrue(all(after < before for before, after in zip(source_rgb, calibrated_rgb)))
        self.assertIn("not measured", SKIN_CALIBRATION["truth_boundary"])

    def test_nail_row_profile_has_rounded_ends(self) -> None:
        values = [rounded_nail_row_scale(index, 9) for index in range(9)]
        self.assertLess(values[0], values[4])
        self.assertLess(values[-1], values[4])
        self.assertLess(values[-1], values[0])
        self.assertEqual(max(values), 1.0)

    def test_component_frame_has_margin(self) -> None:
        report = component_frame_scale(
            [(-0.04, -0.09), (0.05, 0.10), (0.02, 0.03)],
            minimum_scale_m=0.20,
        )
        self.assertGreaterEqual(report["ortho_scale_m"], 0.20)
        self.assertTrue(report["all_points_inside_frame"])

    def test_silhouette_metric_detects_sharp_step(self) -> None:
        smooth = silhouette_roughness([0.00, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06])
        sharp = silhouette_roughness([0.00, 0.01, 0.02, 0.20, 0.21, 0.22, 0.23])
        self.assertLess(
            smooth["maximum_absolute_second_difference"],
            sharp["maximum_absolute_second_difference"],
        )


if __name__ == "__main__":
    unittest.main()
