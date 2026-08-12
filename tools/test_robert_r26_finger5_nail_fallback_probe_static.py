from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE = (
    PROJECT_ROOT
    / "Tools/blender_probe_robert_r26_finger5_nail_local_surface_fallback.py"
)


class RobertR26Finger5FallbackProbeStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PROBE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_exact_target_and_patch_bindings_are_present(self) -> None:
        for token in (
            'TARGET_NAIL_ID = "fingernail_5_L"',
            'TARGET_BONE = "finger5-3.L"',
            '"65edf49c0f72523a7728f30ee5243a522d9866f825e9b940ad44f23f41b669c8"',
            '"c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"',
            '"05eb1e43ab6365428d693a9b3565bfedbfd3a85e8c637a92129224c125acb397"',
        ):
            self.assertIn(token, self.source)

    def test_probe_calls_only_one_private_component_constructor(self) -> None:
        self.assertEqual(self.source.count("nails._projected_oval_nail_plate("), 1)
        self.assertNotIn("nails.add_natural_nails_v3(", self.source)
        self.assertIn('== "nearest_coherent_local_surface_fallback"', self.source)
        self.assertIn('== [17, 17]', self.source)
        self.assertIn('== 24', self.source)

    def test_raw_and_evaluated_exact_gates_are_required(self) -> None:
        for token in (
            "r26.exact_cross_intersections(body, [nail])",
            "r26.component_surface_clearance_report(body, [nail])",
            'record["body_surface_triangle_overlap_count"]',
            'evaluated_exact["total_exact_genuine_triangle_pair_count"]',
            'record["grid_locality"][',
            'record["top_surface_winding"][',
            "if not all(gates.values()):",
        ):
            self.assertIn(token, self.source)

    def test_append_only_candidate_and_cleanup_gates_exist(self) -> None:
        for token in (
            "if output_path.exists():",
            "if candidate_path.exists():",
            'evidence["candidate_absent_after"] = not candidate_path.exists()',
            'evidence["temporary_probe_objects_remaining"]',
            'evidence["temporary_probe_meshes_remaining"]',
            "cleanup_probe_data(nail, materials)",
        ):
            self.assertIn(token, self.source)

    def test_no_save_render_export_or_external_process_path(self) -> None:
        forbidden = (
            r"bpy\.ops\.wm\.save",
            r"bpy\.ops\.wm\.open",
            r"bpy\.ops\.render",
            r"save_as_mainfile",
            r"write_still",
            r"bpy\.ops\.export",
            r"subprocess",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
