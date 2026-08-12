from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS = (
    PROJECT_ROOT
    / "Tools/blender_diagnose_robert_r26_finger5_nail_modifier_stages.py"
)


class RobertR26Finger5NailModifierStageDiagnosisStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DIAGNOSIS.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        region_node = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "solidify_triangle_region"
        )
        namespace: dict[str, object] = {"Iterable": Iterable}
        exec(
            compile(
                ast.fix_missing_locations(
                    ast.Module(body=[region_node], type_ignores=[])
                ),
                str(DIAGNOSIS),
                "exec",
            ),
            namespace,
        )
        cls.region = staticmethod(namespace["solidify_triangle_region"])

    def test_exact_sealed_attempt09_and_component_bindings_are_present(self) -> None:
        for token in (
            'TARGET_NAIL_ID = "fingernail_5_L"',
            'TARGET_BONE = "finger5-3.L"',
            '"c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"',
            '"65edf49c0f72523a7728f30ee5243a522d9866f825e9b940ad44f23f41b669c8"',
            '"34b01c8323bc48f82e922c321044fbb2aca7247c20c3fafeddf8992d73a50327"',
            '"64e2e8ab4cd8bdcd7bdb0133725b43f20211446d072a92869eb22c16f00fca03"',
        ):
            self.assertIn(token, self.source)

    def test_exact_four_modifier_stages_are_bounded(self) -> None:
        for token in (
            '("no_nail_modifiers", False, False)',
            '("armature_only", True, False)',
            '("solidify_only", False, True)',
            '("current_armature_then_solidify", True, True)',
            "for stage_name, armature_enabled, solidify_enabled in STAGE_SPECS:",
            '== 216',
        ):
            self.assertIn(token, self.source)
        self.assertEqual(self.source.count("nails._projected_oval_nail_plate("), 1)
        self.assertNotIn("nails.add_natural_nails_v3(", self.source)

    def test_exact_narrow_phase_and_geometry_evidence_are_required(self) -> None:
        for token in (
            "nails.exact_auditor.classify_triangle_pair(",
            'result.get("genuine_penetration") is True',
            '"broad_phase_is_not_the_pass_gate": True',
            "body_raw_to_evaluated_rest_displacement",
            "armature_only_top_plate_from_raw_displacement",
            "solidify_index_block_comparison",
            "underlying_body_weight_inventory",
            "target_pose_from_rest_identity_maximum_absolute_delta",
        ):
            self.assertIn(token, self.source)

    def test_solidify_index_region_classifier_is_pure_and_exact(self) -> None:
        self.assertEqual(self.region((0, 1, 2), 289), "index_block_0")
        self.assertEqual(self.region((289, 290, 577), 289), "index_block_1")
        self.assertEqual(
            self.region((0, 289, 290), 289),
            "mixed_index_rim_or_unexpected",
        )
        self.assertEqual(
            self.region((578, 579, 580), 289),
            "mixed_index_rim_or_unexpected",
        )

    def test_append_only_candidate_preservation_and_cleanup_gates_exist(self) -> None:
        for token in (
            "if output_path.exists():",
            "if candidate_path.exists():",
            'evidence["candidate_absent_after"] = not candidate_path.exists()',
            "probe09.cleanup_probe_data(nail, materials)",
            'evidence["temporary_diagnosis_objects_remaining"]',
            'evidence["temporary_diagnosis_meshes_remaining"]',
            "if not all(gates.values()):",
        ):
            self.assertIn(token, self.source)

    def test_no_save_render_export_external_process_or_config_write(self) -> None:
        forbidden = (
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
