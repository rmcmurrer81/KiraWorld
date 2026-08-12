from __future__ import annotations

import unittest
from copy import deepcopy

from Core.avatar_human_pose_clearance_v1 import (
    METHOD_ID,
    build_pose_plan,
    segment_segment_distance,
    solve_support_contact_translation,
    validate_pose_plan,
)


class AvatarHumanPoseClearanceV1Tests(unittest.TestCase):
    def test_all_daily_life_foundations_are_bounded_and_inactive(self) -> None:
        plans = (
            build_pose_plan("neutral", body_height_m=1.65),
            build_pose_plan("seated", body_height_m=1.65, seat_top_z_m=0.47),
            build_pose_plan(
                "eating_ready", body_height_m=1.65, seat_top_z_m=0.47
            ),
            build_pose_plan(
                "lying_supine", body_height_m=1.65, support_plane_z_m=0.0
            ),
        )
        self.assertEqual({plan["pose_name"] for plan in plans}, {
            "neutral", "seated", "eating_ready", "lying_supine"
        })
        for plan in plans:
            self.assertEqual(plan["method_id"], METHOD_ID)
            self.assertFalse(plan["runtime_activation_allowed"])
            self.assertFalse(plan["animation_capability_claimed"])
            self.assertTrue(plan["assumed_euler_axis_rotation_forbidden"])
            self.assertTrue(plan["root_local_location_shortcut_forbidden"])
            self.assertTrue(plan["clearance_validation"]["passed"])

    def test_seated_plan_keeps_each_leg_on_its_side_and_feet_below_knees(self) -> None:
        plan = build_pose_plan("seated", body_height_m=1.65, seat_top_z_m=0.47)
        joints = plan["joint_targets_m"]
        for joint in ("hip", "knee", "ankle", "toe"):
            self.assertGreater(joints[f"{joint}.L"][0], 0.0)
            self.assertLess(joints[f"{joint}.R"][0], 0.0)
        self.assertLess(joints["knee.L"][1], joints["hip.L"][1])
        self.assertLess(joints["ankle.L"][2], joints["knee.L"][2])
        self.assertGreater(
            plan["clearance_validation"]["minimum_capsule_surface_clearance_m"],
            plan["clearance_validation"]["required_capsule_surface_clearance_m"],
        )

    def test_crossed_or_collapsed_seated_targets_fail_closed(self) -> None:
        plan = build_pose_plan("seated", body_height_m=1.65, seat_top_z_m=0.47)
        crossed = deepcopy(plan)
        crossed["joint_targets_m"]["ankle.L"] = (-0.03, -0.31, -0.39)
        with self.assertRaisesRegex(ValueError, "cross or collapse"):
            validate_pose_plan(crossed)

        overlapped = deepcopy(plan)
        for joint in ("knee", "ankle", "toe"):
            left = list(overlapped["joint_targets_m"][f"{joint}.L"])
            right = list(overlapped["joint_targets_m"][f"{joint}.R"])
            left[0] = 0.002
            right[0] = -0.002
            overlapped["joint_targets_m"][f"{joint}.L"] = tuple(left)
            overlapped["joint_targets_m"][f"{joint}.R"] = tuple(right)
        with self.assertRaisesRegex(ValueError, "overlap or lack required clearance"):
            validate_pose_plan(overlapped)

    def test_support_contact_is_world_vertical_and_bounded(self) -> None:
        report = solve_support_contact_translation(
            measured_support_z_m=0.61,
            support_plane_z_m=0.47,
            clearance_m=0.001,
            body_height_m=1.65,
        )
        self.assertAlmostEqual(report["world_vertical_translation_m"], -0.139)
        self.assertAlmostEqual(report["target_support_z_m"], 0.471)
        self.assertTrue(report["contact_target_without_penetration"])

    def test_unbounded_support_jump_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds the bounded"):
            solve_support_contact_translation(
                measured_support_z_m=1.40,
                support_plane_z_m=0.10,
                body_height_m=1.65,
            )

    def test_supine_rotation_has_an_explicit_larger_but_bounded_contact_range(self) -> None:
        report = solve_support_contact_translation(
            measured_support_z_m=0.83,
            support_plane_z_m=0.0,
            body_height_m=1.65,
            maximum_translation_height_fraction=0.55,
        )
        self.assertAlmostEqual(report["world_vertical_translation_m"], -0.829)
        self.assertAlmostEqual(report["maximum_allowed_translation_m"], 0.9075)

    def test_contact_pose_requires_a_measured_surface(self) -> None:
        with self.assertRaisesRegex(ValueError, "measured seat top"):
            build_pose_plan("seated", body_height_m=1.65)
        with self.assertRaisesRegex(ValueError, "measured support plane"):
            build_pose_plan("lying_supine", body_height_m=1.65)

    def test_eating_ready_is_an_upper_body_foundation_not_an_animation_claim(self) -> None:
        plan = build_pose_plan(
            "eating_ready", body_height_m=1.65, seat_top_z_m=0.47
        )
        joints = plan["joint_targets_m"]
        self.assertLess(joints["wrist.L"][1], joints["elbow.L"][1])
        self.assertGreater(joints["wrist.L"][0], 0.0)
        self.assertLess(joints["wrist.R"][0], 0.0)
        self.assertFalse(plan["animation_capability_claimed"])

    def test_supine_plan_points_headward_and_footward_after_root_rotation(self) -> None:
        plan = build_pose_plan(
            "lying_supine", body_height_m=1.65, support_plane_z_m=0.0
        )
        joints = plan["joint_targets_m"]
        self.assertGreater(joints["shoulder.L"][1], joints["hip.L"][1])
        self.assertLess(joints["ankle.L"][1], joints["hip.L"][1])

    def test_segment_distance_handles_crossing_and_parallel_segments(self) -> None:
        self.assertAlmostEqual(
            segment_segment_distance(
                (-1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, -1.0, 0.0),
                (0.0, 1.0, 0.0),
            ),
            0.0,
        )
        self.assertAlmostEqual(
            segment_segment_distance(
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 0.25, 0.0),
                (1.0, 0.25, 0.0),
            ),
            0.25,
        )


if __name__ == "__main__":
    unittest.main()
