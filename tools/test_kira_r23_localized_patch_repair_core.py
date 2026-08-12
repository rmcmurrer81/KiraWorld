#!/usr/bin/env python3
"""Pure unit tests for the bounded R23 localized patch repair helpers."""

from __future__ import annotations

import math
import unittest

from tools.kira_r23_localized_patch_repair_core import (
    OrientationConflictError,
    cubic_hermite_collar_sample,
    harmonic_interpolate_boundary_field,
    minimum_variation_closed_cycle_choices,
    orient_disk_faces_from_retained_boundary,
    project_top_four_normalized_weights,
)


class R23LocalizedPatchRepairCoreTests(unittest.TestCase):
    def test_boundary_orientation_propagates_face_parity(self):
        # Face 1 intentionally traverses the shared diagonal in the same
        # direction as face 0 and therefore must be flipped.
        faces = [(0, 1, 2), (0, 3, 2)]
        retained_boundary = [(3, 2), (1, 0), (0, 3), (2, 1)]

        result = orient_disk_faces_from_retained_boundary(
            faces, retained_boundary
        )

        self.assertEqual(result.faces, ((0, 1, 2), (0, 2, 3)))
        self.assertEqual(result.face_flip_parity, (0, 1))
        self.assertEqual(result.flipped_face_indices, (1,))
        self.assertEqual(result.boundary_edge_count, 4)

    def test_contradictory_boundary_orientation_fails_closed(self):
        faces = [(0, 1, 2), (0, 3, 2)]
        contradictory_retained_boundary = [
            (0, 1),  # Reversed relative to the otherwise coherent constraints.
            (2, 1),
            (3, 2),
            (0, 3),
        ]

        with self.assertRaises(OrientationConflictError):
            orient_disk_faces_from_retained_boundary(
                faces, contradictory_retained_boundary
            )

    def test_boundary_seed_propagates_to_an_unconstrained_interior_face(self):
        # The central face touches no boundary edge and is intentionally wound
        # backward.  Its parity must come only from the three interior edges.
        faces = [
            (0, 2, 1),
            (1, 0, 3),
            (2, 1, 4),
            (0, 2, 5),
        ]
        retained_boundary = [
            (3, 0),
            (1, 3),
            (4, 1),
            (2, 4),
            (5, 2),
            (0, 5),
        ]

        result = orient_disk_faces_from_retained_boundary(
            faces, retained_boundary
        )

        self.assertEqual(result.face_flip_parity, (1, 0, 0, 0))
        self.assertEqual(result.faces[0], (0, 1, 2))

    def test_harmonic_field_preserves_boundary_exactly(self):
        adjacency = {
            node: {
                neighbor
                for neighbor in (node - 1, node + 1)
                if 0 <= neighbor <= 4
            }
            for node in range(5)
        }
        boundary = {0: (0.125, -2.5, 7.75), 4: (1.125, 1.5, -0.25)}

        field = harmonic_interpolate_boundary_field(adjacency, boundary)

        self.assertEqual(field[0], boundary[0])
        self.assertEqual(field[4], boundary[4])
        for component in range(3):
            for node in (1, 2, 3):
                expected = 0.5 * (
                    field[node - 1][component] + field[node + 1][component]
                )
                self.assertAlmostEqual(field[node][component], expected, places=12)

    def test_harmonic_left_right_weights_are_smooth(self):
        adjacency = {
            node: {
                neighbor
                for neighbor in (node - 1, node + 1)
                if 0 <= neighbor <= 4
            }
            for node in range(5)
        }
        field = harmonic_interpolate_boundary_field(
            adjacency,
            {0: (1.0, 0.0), 4: (0.0, 1.0)},
        )

        expected = {
            0: (1.0, 0.0),
            1: (0.75, 0.25),
            2: (0.5, 0.5),
            3: (0.25, 0.75),
            4: (0.0, 1.0),
        }
        for node, values in expected.items():
            self.assertAlmostEqual(field[node][0], values[0], places=12)
            self.assertAlmostEqual(field[node][1], values[1], places=12)
            self.assertAlmostEqual(math.fsum(field[node]), 1.0, places=12)
        self.assertTrue(
            all(field[node][0] >= field[node + 1][0] for node in range(4))
        )
        self.assertTrue(
            all(field[node][1] <= field[node + 1][1] for node in range(4))
        )

    def test_top_four_projection_is_normalized_and_order_independent(self):
        forward = {
            "pelvis": 0.35,
            "left_thigh": 0.25,
            "right_thigh": 0.15,
            "spine": 0.15,
            "abdomen": 0.08,
            "helper": 0.02,
        }
        reverse = dict(reversed(tuple(forward.items())))

        projected = project_top_four_normalized_weights(forward)
        projected_reverse = project_top_four_normalized_weights(reverse)

        self.assertEqual(projected, projected_reverse)
        self.assertEqual(
            tuple(projected), ("pelvis", "left_thigh", "right_thigh", "spine")
        )
        self.assertLessEqual(len(projected), 4)
        self.assertAlmostEqual(math.fsum(projected.values()), 1.0, places=15)
        self.assertTrue(all(value > 0.0 for value in projected.values()))

    def test_cubic_collar_preserves_endpoints_and_inward_tangents(self):
        outer = (0.0, 0.0, 0.0)
        source_tangent = (1.0, 0.0, 0.0)
        donor = (1.0, 1.0, 0.0)
        donor_tangent = (0.0, 1.0, 0.0)

        start = cubic_hermite_collar_sample(
            outer, source_tangent, donor, donor_tangent, 0.0
        )
        middle = cubic_hermite_collar_sample(
            outer, source_tangent, donor, donor_tangent, 0.5
        )
        end = cubic_hermite_collar_sample(
            outer, source_tangent, donor, donor_tangent, 1.0
        )

        self.assertEqual(start.point, outer)
        self.assertEqual(start.tangent, source_tangent)
        self.assertEqual(end.point, donor)
        self.assertEqual(end.tangent, donor_tangent)
        self.assertEqual(start.bezier_control_points, end.bezier_control_points)
        self.assertEqual(start.bezier_control_points[0], outer)
        self.assertEqual(start.bezier_control_points[3], donor)
        self.assertEqual(middle.point, (0.625, 0.375, 0.0))
        self.assertEqual(middle.tangent, (1.25, 1.25, 0.0))

    def test_closed_cycle_uv_choice_uses_only_exact_values_and_is_deterministic(self):
        forward = [
            [(0.0, 0.0), (10.0, 10.0)],
            [(0.1, 0.0), (9.9, 10.0)],
            [(0.0, 0.1), (10.0, 9.9)],
        ]
        reversed_candidates = [list(reversed(row)) for row in forward]

        selected = minimum_variation_closed_cycle_choices(forward)
        selected_reversed = minimum_variation_closed_cycle_choices(
            reversed_candidates
        )

        self.assertEqual(selected, selected_reversed)
        self.assertEqual(selected, ((0.0, 0.0), (0.1, 0.0), (0.0, 0.1)))
        for index, value in enumerate(selected):
            self.assertIn(value, [tuple(row) for row in forward[index]])


if __name__ == "__main__":
    unittest.main()
