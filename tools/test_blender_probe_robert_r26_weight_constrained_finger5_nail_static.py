from __future__ import annotations

import ast
import hashlib
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE = (
    PROJECT_ROOT
    / "Tools/blender_probe_robert_r26_weight_constrained_finger5_nail.py"
)


class RobertR26WeightConstrainedFinger5ProbeStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PROBE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_every_fixed_binding_currently_matches_exact_bytes(self) -> None:
        assignment = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "FIXED_BINDINGS"
                for target in node.targets
            )
        )
        bindings = ast.literal_eval(assignment.value)
        for name, row in bindings.items():
            with self.subTest(name=name):
                path = PROJECT_ROOT / str(row["path"])
                self.assertTrue(path.is_file())
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    row["sha256"],
                )

    def test_exact_preserved_evidence_and_repair_hashes_are_bound(self) -> None:
        for token in (
            '"6a9626d14481f2b90c42fc25a0c268031fbd8a5616ad54625e9a87af30d1a11a"',
            '"c5df50067511dbaffcad5f735416e5b1f5777c06670e5784d2f21d409093b4fc"',
            '"620ebe22602b760c56aa7ca57986e467a7c34836d84fab6d9d4ec065ea7e4b5d"',
            '"3f0823f78cdb6e0e7c3880a89dee3ae1c35f50b6ac0f5ce61e52a169a77de2b2"',
            '"d769962a1b3f7be2e99c3ce0d2b808124f6ee6045e904c38f49079c1d658c251"',
        ):
            self.assertIn(token, self.source)

    def test_probe_is_bounded_to_exactly_one_existing_failure(self) -> None:
        for token in (
            'TARGET_NAIL_ID = "fingernail_5_L"',
            'TARGET_BONE = "finger5-3.L"',
            '"maximum_nail_objects": 1',
            '"exact_one_nail_component_instantiated"',
            'if row["nail_id"] == TARGET_NAIL_ID',
        ):
            self.assertIn(token, self.source)
        self.assertNotIn('TARGET_NAIL_ID = "fingernail_5_R"', self.source)

    def test_probe_requires_occlusion_rejection_and_connected_digit(self) -> None:
        for token in (
            '"strict_declared_digit_footprint_passed"',
            '"one_connected_declared_digit_region_selected"',
            '"occluding_first_hit_was_demonstrably_rejected"',
            '"neighboring_or_occluding_first_hit_rejected_count"',
            '"no_automatic_bone_remap"',
        ):
            self.assertIn(token, self.source)

    def test_complete_evaluated_shell_is_mandatory(self) -> None:
        for token in (
            'record["final_evaluated_complete_shell_gate"]',
            '"complete_evaluated_shell_passed"',
            '"zero_exact_final_shell_penetrations"',
            '"exact_genuine_triangle_pair_count"',
        ):
            self.assertIn(token, self.source)

    def test_preservation_and_cleanup_are_fail_closed(self) -> None:
        for token in (
            "if output_path.exists():",
            "if candidate_path.exists():",
            "cleanup_all()",
            'evidence["candidate_absent_after"] = not candidate_path.exists()',
            'evidence["temporary_objects_remaining"] != 0',
            'evidence["temporary_meshes_remaining"] != 0',
            'evidence["fixed_inputs_after"] = verify_fixed_inputs(config_path)',
        ):
            self.assertIn(token, self.source)

    def test_no_save_render_export_config_or_external_process(self) -> None:
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
