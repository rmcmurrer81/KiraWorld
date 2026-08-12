from __future__ import annotations

import unittest

from Core.avatar_nail_weight_constrained_projection_v1 import (
    NailWeightConstrainedProjectionError,
    hit_meets_declared_digit_gate,
    select_connected_weight_constrained_grid,
    validate_final_evaluated_shell_gate,
)


def hit(
    ordinal: int,
    component: int,
    *,
    expected: float,
    foreign: float,
    distance: float = 0.001,
    depth: float = 0.010,
    dominant: bool = True,
) -> dict[str, object]:
    return {
        "ray_hit_ordinal": ordinal,
        "ray_depth_m": depth,
        "distance_to_expected_point_m": distance,
        "evaluated_triangle_index": component * 100 + ordinal,
        "raw_triangle_index": component * 10 + ordinal,
        "raw_component_id": component,
        "expected_family_weight": expected,
        "foreign_digit_family_weight": foreign,
        "wrong_side_digit_weight": 0.0,
        "expected_family_is_dominant": dominant,
        "outward_normal_alignment": 0.9,
    }


def shell(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "body_surface_space": "evaluated_rest",
        "nail_surface_space": "evaluated_armature_then_solidify",
        "exact_narrow_phase_used": True,
        "complete_shell_included": True,
        "solidify_rim_included": True,
        "source_top_vertex_count": 81,
        "evaluated_shell_vertex_count": 162,
        "exact_genuine_triangle_pair_count": 0,
        "minimum_unsigned_surface_clearance_m": 0.000055,
        "maximum_unsigned_surface_clearance_m": 0.00031,
        "body_mesh_unchanged": True,
        "official_rig_unchanged": True,
        "body_modifier_stack_unchanged": True,
        "automatic_bone_remap_performed": False,
    }
    result.update(overrides)
    return result


class NailWeightConstrainedProjectionV1Tests(unittest.TestCase):
    def test_declared_digit_gate_accepts_exact_family_hit(self) -> None:
        self.assertTrue(
            hit_meets_declared_digit_gate(
                hit(0, 5, expected=0.995, foreign=0.005)
            )
        )

    def test_declared_digit_gate_rejects_neighboring_family(self) -> None:
        self.assertFalse(
            hit_meets_declared_digit_gate(
                hit(0, 4, expected=0.0, foreign=1.0, dominant=False)
            )
        )

    def test_occluding_first_hit_is_skipped_without_bone_remap(self) -> None:
        stacks = [
            [
                hit(0, 4, expected=0.0, foreign=1.0, dominant=False),
                hit(1, 5, expected=1.0, foreign=0.0, depth=0.021),
            ]
            for _index in range(9)
        ]
        result = select_connected_weight_constrained_grid(
            stacks, center_sample_index=4
        )
        self.assertEqual(result["selected_raw_component_id"], 5)
        self.assertEqual(
            result["neighboring_or_occluding_first_hit_rejected_count"], 9
        )
        self.assertEqual(result["selected_hit_ordinals"], [1] * 9)
        self.assertFalse(result["automatic_bone_remap_performed"])

    def test_mixed_components_cannot_form_one_grid(self) -> None:
        stacks = [
            [hit(0, 5, expected=1.0, foreign=0.0)],
            [hit(0, 6, expected=1.0, foreign=0.0)],
            [hit(0, 5, expected=1.0, foreign=0.0)],
        ]
        with self.assertRaisesRegex(
            NailWeightConstrainedProjectionError,
            "no declared-digit connected component covers",
        ):
            select_connected_weight_constrained_grid(stacks, center_sample_index=1)

    def test_center_ray_must_have_declared_digit_hit(self) -> None:
        stacks = [
            [hit(0, 5, expected=1.0, foreign=0.0)],
            [hit(0, 4, expected=0.0, foreign=1.0, dominant=False)],
            [hit(0, 5, expected=1.0, foreign=0.0)],
        ]
        with self.assertRaisesRegex(
            NailWeightConstrainedProjectionError,
            "center ray has no declared-digit",
        ):
            select_connected_weight_constrained_grid(stacks, center_sample_index=1)

    def test_complete_component_is_chosen_over_incomplete_nearer_component(self) -> None:
        stacks = [
            [
                hit(0, 7, expected=1.0, foreign=0.0, distance=0.0001),
                hit(1, 5, expected=1.0, foreign=0.0, distance=0.001),
            ],
            [
                hit(0, 7, expected=1.0, foreign=0.0, distance=0.0001),
                hit(1, 5, expected=1.0, foreign=0.0, distance=0.001),
            ],
            [hit(1, 5, expected=1.0, foreign=0.0, distance=0.001)],
        ]
        result = select_connected_weight_constrained_grid(
            stacks, center_sample_index=1
        )
        self.assertEqual(result["selected_raw_component_id"], 5)

    def test_final_evaluated_complete_shell_passes(self) -> None:
        result = validate_final_evaluated_shell_gate(shell())
        self.assertTrue(result["passed"])
        self.assertEqual(result["evaluated_shell_vertex_count"], 162)

    def test_top_plate_only_cannot_pass_as_complete_shell(self) -> None:
        with self.assertRaisesRegex(
            NailWeightConstrainedProjectionError,
            "solidify_two_surface_blocks_present",
        ):
            validate_final_evaluated_shell_gate(
                shell(evaluated_shell_vertex_count=81)
            )

    def test_any_exact_penetration_fails(self) -> None:
        with self.assertRaisesRegex(
            NailWeightConstrainedProjectionError,
            "zero_exact_genuine_penetrations",
        ):
            validate_final_evaluated_shell_gate(
                shell(exact_genuine_triangle_pair_count=1)
            )

    def test_raw_body_or_unmodified_nail_cannot_pass(self) -> None:
        with self.assertRaises(NailWeightConstrainedProjectionError):
            validate_final_evaluated_shell_gate(
                shell(
                    body_surface_space="raw_cage",
                    nail_surface_space="raw_top_plate",
                )
            )

    def test_bone_remap_claim_fails_shell_gate(self) -> None:
        with self.assertRaisesRegex(
            NailWeightConstrainedProjectionError,
            "no_automatic_bone_remap",
        ):
            validate_final_evaluated_shell_gate(
                shell(automatic_bone_remap_performed=True)
            )


if __name__ == "__main__":
    unittest.main()
