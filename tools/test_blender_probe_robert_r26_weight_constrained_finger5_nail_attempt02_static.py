from __future__ import annotations

import ast
import hashlib
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    PROJECT_ROOT
    / "Tools/blender_probe_robert_r26_weight_constrained_finger5_nail_attempt02.py"
)


class RobertR26Finger5Attempt02CleanupStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.constants = {}
        for node in cls.tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    try:
                        cls.constants[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass

    def test_attempt01_script_and_result_are_exactly_preserved(self) -> None:
        checks = (
            (
                self.constants["ATTEMPT01_SCRIPT"],
                self.constants["ATTEMPT01_SCRIPT_SHA256"],
                None,
            ),
            (
                self.constants["ATTEMPT01_RESULT"],
                self.constants["ATTEMPT01_RESULT_SHA256"],
                self.constants["ATTEMPT01_RESULT_BYTES"],
            ),
        )
        for relative, expected_hash, expected_bytes in checks:
            with self.subTest(relative=relative):
                path = PROJECT_ROOT / relative
                self.assertTrue(path.is_file())
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash
                )
                if expected_bytes is not None:
                    self.assertEqual(path.stat().st_size, expected_bytes)

    def test_output_is_exact_append_only_attempt02_path(self) -> None:
        self.assertEqual(self.constants["ATTEMPT_LABEL"], "attempt_02")
        self.assertTrue(
            self.constants["EXPECTED_OUTPUT"].endswith(
                "nail_weight_constrained_finger5_probe/attempt_02/PROBE_RESULT.json"
            )
        )
        for token in (
            "if path != project_path(EXPECTED_OUTPUT):",
            "if path.exists():",
            "Attempt 02 output already exists",
        ):
            self.assertIn(token, self.source)

    def test_factory_startup_scope_is_verified_before_cleanup(self) -> None:
        for token in (
            '"no_blend_is_loaded": bpy.data.filepath == ""',
            '"exact_three_factory_objects": len(objects) == 3',
            '{"CAMERA": 1, "LIGHT": 1, "MESH": 1}',
            '"exact_one_initial_mesh_datablock": len(meshes) == 1',
            '"initial_mesh_has_exactly_one_user"',
            "Attempt 02 refuses non-isolated or non-factory-startup Blender state",
        ):
            self.assertIn(token, self.source)

    def test_exact_four_orphan_sources_are_classified(self) -> None:
        for token in (
            '"factory_startup_mesh_deleted_by_probe_initialization"',
            '"appended_canonical_source_mesh_orphan"',
            '"recreated_R26_body_mesh"',
            '"weight_constrained_nail_mesh"',
            '"exact_four_attempt01_mesh_datablocks_observed": exact_four_before',
            "exact_four_before = len(meshes_before) == 4",
        ):
            self.assertIn(token, self.source)

    def test_cleanup_is_snapshot_scoped_and_zero_user_only(self) -> None:
        for token in (
            "meshes_before = list(bpy.data.meshes)",
            "ORIGINAL_CLEANUP()",
            "if int(mesh.users) == 0 and mesh.name in bpy.data.meshes:",
            "bpy.data.meshes.remove(mesh)",
            '"every_owned_mesh_had_zero_users_after_object_cleanup"',
            '"every_owned_mesh_removed"',
            '"zero_mesh_datablocks_after_cleanup"',
        ):
            self.assertIn(token, self.source)
        self.assertNotIn("for mesh in list(bpy.data.meshes)", self.source)

    def test_cleanup_failure_is_propagated_fail_closed(self) -> None:
        for token in (
            'CLEANUP_EVIDENCE.get("phase") == "cleanup_complete"',
            'CLEANUP_EVIDENCE.get("passed") is not True',
            "Attempt 02 ownership-scoped mesh cleanup failed closed",
        ):
            self.assertIn(token, self.source)

    def test_attempt01_execution_is_reused_without_geometry_override(self) -> None:
        for token in (
            "attempt01.cleanup_all = cleanup_objects_and_owned_mesh_datablocks",
            "attempt01.verify_fixed_inputs = verify_with_attempt02_cleanup",
            "attempt01.main()",
            '"geometry_projection_threshold_or_bone_change": False',
        ):
            self.assertIn(token, self.source)
        forbidden_geometry = (
            "FOOTPRINT_SCALE_CANDIDATES",
            "CENTER_FRACTION_CANDIDATES",
            "NORMAL_LIFT_STEP_M",
            "MAXIMUM_NORMAL_LIFT_ITERATIONS",
            "NAIL_PLATE_THICKNESS_M",
            "build_weight_constrained_nail_v1",
            "finger4-3",
        )
        for token in forbidden_geometry:
            with self.subTest(token=token):
                self.assertNotIn(token, self.source)

    def test_no_save_render_export_config_rebind_or_external_process(self) -> None:
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
