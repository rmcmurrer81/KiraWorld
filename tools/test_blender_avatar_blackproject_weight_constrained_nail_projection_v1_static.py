from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools/blender_avatar_blackproject_weight_constrained_nail_projection_v1.py"


class BlackProjectWeightConstrainedNailAdapterStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = ADAPTER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_corrected_landmark_never_uses_bad_source_object_world_transform(self) -> None:
        self.assertIn("body.matrix_world @ vertex.co", self.source)
        self.assertIn('"source_nail_matrix_world_used_for_placement": False', self.source)
        self.assertNotIn("source_nail.matrix_world @ vertex.co", self.source)
        self.assertIn("REFERENCE_ANCHOR_MAXIMUM_ERROR_M = 0.0015", self.source)

    def test_every_ray_uses_bounded_multi_hit_connected_digit_selection(self) -> None:
        for token in (
            "MAXIMUM_RAY_HITS = 8",
            "RAY_START_OFFSET_M = 0.025",
            "RAY_LENGTH_M = 0.050",
            "for ordinal in range(MAXIMUM_RAY_HITS)",
            "all20.interpolate_raw_cage_influences(",
            "declared_digit_triangle_components(",
            "select_connected_weight_constrained_grid(",
            '"raw_component_id"',
        ):
            self.assertIn(token, self.source)

    def test_kira_binding_is_strict_and_never_remaps(self) -> None:
        for token in (
            "digit_weight_evidence(",
            "summarize_footprint_binding(",
            "MINIMUM_EXPECTED_FAMILY_WEIGHT",
            '"automatic_bone_remap_performed": False',
            "parse_blackproject_digit_bone(",
        ):
            self.assertIn(token, self.source)

    def test_complete_evaluated_shell_is_the_acceptance_gate(self) -> None:
        for token in (
            "all20.world_geometry(body, evaluated=True)",
            "stages.world_geometry(nail, evaluated=True)",
            "stages.exact_pair_record(",
            '"evaluated_armature_then_solidify"',
            "validate_final_evaluated_shell_gate(shell_raw)",
            "MAXIMUM_NORMAL_LIFT_ITERATIONS + 1",
            "NAIL_PLATE_THICKNESS_M",
        ):
            self.assertIn(token, self.source)

    def test_cached_component_is_reconstructed_without_reprojection_and_revalidated(self) -> None:
        start = self.source.index("def reconstruct_cached_nail_v1(")
        section = self.source[start:]
        self.assertIn('"reused_cached_top_surface_without_reprojection": True', section)
        self.assertIn("_validate_complete_shell(", section)
        self.assertNotIn("_candidate_grid(", section)

    def test_adapter_has_no_open_save_render_export_config_or_process_path(self) -> None:
        for pattern in (
            r"bpy\.ops\.wm\.save",
            r"bpy\.ops\.wm\.open",
            r"bpy\.ops\.render",
            r"save_as_mainfile",
            r"write_still",
            r"bpy\.ops\.export",
            r"subprocess",
            r"argparse",
        ):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
