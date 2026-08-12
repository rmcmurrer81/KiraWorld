#!/usr/bin/env python3
"""Static fail-closed tests for the no-save R23 repair simulation package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_localized_patch_repair_simulation_preparation/"
    "KIRA_R23_LOCALIZED_PATCH_REPAIR_SIMULATION_CONFIG.json"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R23LocalizedPatchSimulationPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_status_requires_explicit_readonly_execution(self):
        self.assertEqual(
            self.config["status"],
            "BOUND_NOT_RUN_EXPLICIT_READONLY_SIMULATION_REQUIRED",
        )

    def test_every_binding_is_exact(self):
        for label, binding in self.config["bindings"].items():
            with self.subTest(label=label):
                path = ROOT / binding["path"]
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(digest(path), binding["sha256"])

    def test_grid_is_fixed_twenty_seven_variants(self):
        grid = self.config["parameter_grid"]
        self.assertEqual(len(grid["outer_scale"]), 3)
        self.assertEqual(len(grid["donor_scale"]), 3)
        self.assertEqual(len(grid["clearance_m"]), 3)
        self.assertEqual(
            len(grid["outer_scale"])
            * len(grid["donor_scale"])
            * len(grid["clearance_m"]),
            27,
        )

    def test_all_mutating_outputs_are_forbidden(self):
        restrictions = self.config["execution_restrictions"]
        for key in (
            "blend_save_forbidden",
            "render_forbidden",
            "export_forbidden",
            "runtime_mutation_forbidden",
            "activation_assignment_publication_forbidden",
        ):
            self.assertIs(restrictions[key], True)

    def test_worker_contains_no_blend_save_render_or_export_operator(self):
        worker = (ROOT / self.config["bindings"]["worker"]["path"]).read_text(
            encoding="utf-8"
        )
        forbidden = (
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.wm.save_mainfile",
            "bpy.ops.render.render",
            "bpy.ops.export_scene",
            "bpy.ops.export_mesh",
        )
        for marker in forbidden:
            self.assertNotIn(marker, worker)

    def test_no_author_output_path_is_configured(self):
        output = self.config["output"]
        self.assertEqual(output["filename"], "SIMULATION_EVIDENCE.json")
        self.assertNotIn("candidate_blend", output)
        self.assertNotIn("render", output)

    def test_worker_refuses_plain_python_without_explicit_flag(self):
        worker = ROOT / self.config["bindings"]["worker"]["path"]
        result = subprocess.run(
            [sys.executable, str(worker), "--config", str(CONFIG)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit --execute-readonly-simulation flag is required", result.stderr)

    def test_truth_boundary_refuses_function_and_approval_claims(self):
        truth = self.config["truth_boundary"]
        self.assertIs(truth["owner_visual_approval"], False)
        self.assertIs(truth["internal_biological_function"], False)
        self.assertIs(truth["subjective_sensation_or_experience"], False)
        self.assertIs(truth["author_candidate_created"], False)


if __name__ == "__main__":
    unittest.main()
