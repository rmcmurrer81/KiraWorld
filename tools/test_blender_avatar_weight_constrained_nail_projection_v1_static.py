from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = (
    PROJECT_ROOT / "Tools/blender_avatar_weight_constrained_nail_projection_v1.py"
)


class WeightConstrainedNailProjectionV1StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = ADAPTER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_bounded_multi_hit_rays_replace_global_first_hit_acceptance(self) -> None:
        for token in (
            "MAXIMUM_RAY_HITS = 8",
            "RAY_START_OFFSET_M = 0.025",
            "RAY_LENGTH_M = 0.050",
            "RAY_ADVANCE_EPSILON_M = 0.000002",
            "for ordinal in range(MAXIMUM_RAY_HITS)",
            "evaluated_tree.ray_cast(",
            "origin = hit + direction * RAY_ADVANCE_EPSILON_M",
        ):
            self.assertIn(token, self.source)

    def test_hits_are_bound_to_transferred_raw_weights(self) -> None:
        for token in (
            "all20.interpolate_raw_cage_influences(",
            '"expected_family_weight"',
            '"foreign_digit_family_weight"',
            '"wrong_side_digit_weight"',
            '"raw_component_id"',
            "MINIMUM_EXPECTED_FAMILY_WEIGHT",
        ):
            self.assertIn(token, self.source)

    def test_declared_digit_region_requires_strict_connected_triangles(self) -> None:
        for token in (
            "def declared_digit_triangle_components(",
            "triangle_eligibility_requires_all_three_vertices",
            "edge_to_triangles",
            "component_by_triangle",
            "select_connected_weight_constrained_grid(",
            "selected connected grid failed strict complete-footprint binding",
        ):
            self.assertIn(token, self.source)

    def test_projection_is_generic_and_never_remaps_a_digit(self) -> None:
        self.assertNotIn('"fingernail_5_L"', self.source)
        self.assertNotIn('"fingernail_5_R"', self.source)
        self.assertNotIn('"finger4-3.L"', self.source)
        self.assertNotIn('"finger4-3.R"', self.source)
        self.assertGreaterEqual(
            self.source.count('"automatic_bone_remap_performed": False'), 4
        )

    def test_construction_and_acceptance_use_evaluated_surfaces(self) -> None:
        for token in (
            "all20.world_geometry(\n        body, evaluated=True",
            "evaluated_tree = BVHTree.FromPolygons(",
            "stages.world_geometry(\n                        nail, evaluated=True",
            "stages.exact_pair_record(",
            '"evaluated_armature_then_solidify"',
            "validate_final_evaluated_shell_gate(shell_raw)",
        ):
            self.assertIn(token, self.source)

    def test_complete_shell_is_lifted_only_inside_existing_bounds(self) -> None:
        for token in (
            "MAXIMUM_NORMAL_LIFT_ITERATIONS + 1",
            "lift_iteration * NORMAL_LIFT_STEP_M",
            "solidify.thickness = NAIL_PLATE_THICKNESS_M",
            "solidify.offset = 1.0",
            '"complete_shell_included": True',
            '"solidify_rim_included"',
            "MAXIMUM_FINAL_CLEARANCE_M",
        ):
            self.assertIn(token, self.source)

    def test_adapter_has_no_save_render_export_config_or_process_path(self) -> None:
        forbidden = (
            r"bpy\.ops\.wm\.save",
            r"bpy\.ops\.wm\.open",
            r"bpy\.ops\.render",
            r"save_as_mainfile",
            r"write_still",
            r"bpy\.ops\.export",
            r"subprocess",
            r"config_path\.write",
            r"shutil",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
