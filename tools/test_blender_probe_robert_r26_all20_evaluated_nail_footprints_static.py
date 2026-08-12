from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE = (
    PROJECT_ROOT
    / "Tools/blender_probe_robert_r26_all20_evaluated_nail_footprints.py"
)


class RobertR26All20EvaluatedNailFootprintsStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PROBE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_exact_preserved_and_pure_audit_bindings_are_present(self) -> None:
        for token in (
            '"c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"',
            '"c5df50067511dbaffcad5f735416e5b1f5777c06670e5784d2f21d409093b4fc"',
            '"620ebe22602b760c56aa7ca57986e467a7c34836d84fab6d9d4ec065ea7e4b5d"',
            '"94c5df362b83fccbe64cc0d076339dd35237cd83b80d81bc63332113509f0bf6"',
            '"0b9f5f583230aa0e8c09ba95e3e64b0bd386d5be560ca75b25f8d91f282b0307"',
        ):
            self.assertIn(token, self.source)

    def test_all_twenty_are_audited_without_one_digit_special_case(self) -> None:
        for token in (
            "for definition in expected_nail_inventory()",
            '"all_20_inventory_entries_recorded": len(records) == 20',
            '"all_20_exhausted_exact_48_bounded_candidates"',
            '"expected_candidate_count": 48',
            '"automatic_bone_remap_performed": False',
        ):
            self.assertIn(token, self.source)
        self.assertNotIn('if nail_id == "fingernail_5_L"', self.source)
        self.assertNotIn('if bone_name == "finger5-3.L"', self.source)

    def test_evaluated_body_drives_both_bounded_projection_paths(self) -> None:
        for token in (
            "evaluated_points, evaluated_triangles = world_geometry(body, evaluated=True)",
            "evaluated_tree.ray_cast(",
            "evaluated_tree.find_nearest(",
            '"projection_method": "evaluated_first_hit_raycast"',
            '"projection_method": "evaluated_nearest_coherent_fallback"',
            "PRIMARY_GRID = PROJECTION_GRID_SIZE",
            "FALLBACK_GRID = 17",
            "FOOTPRINT_SCALE_CANDIDATES",
            "CENTER_FRACTION_CANDIDATES",
        ):
            self.assertIn(token, self.source)

    def test_evaluated_hits_map_to_raw_weights_and_fail_closed(self) -> None:
        for token in (
            "interpolate_raw_cage_influences(",
            "r26.barycentric(",
            "body.data.vertices[int(vertex_index)].groups",
            "summarize_footprint_binding(",
            'if binding["passed"] is True:',
            '"selected_candidate_index": selected_index',
            '"passed": selected_index is not None',
            '"raw_cage_mapping_distance_bound_m"',
        ):
            self.assertIn(token, self.source)

    def test_no_nail_mesh_candidate_save_render_or_external_process(self) -> None:
        for token in (
            '"nail_objects_instantiated": 0',
            '"no_nail_geometry_instantiated"',
            "if output_path.exists():",
            "if candidate_path.exists():",
            "cleanup_all()",
            'evidence["candidate_absent_after"] = not candidate_path.exists()',
        ):
            self.assertIn(token, self.source)
        forbidden = (
            r"bpy\.data\.meshes\.new",
            r"_projected_oval_nail_plate",
            r"add_natural_nails_v3",
            r"bpy\.ops\.wm\.save",
            r"bpy\.ops\.wm\.open",
            r"bpy\.ops\.render",
            r"save_as_mainfile",
            r"write_still",
            r"bpy\.ops\.export",
            r"subprocess",
            r"config_path\.write",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
