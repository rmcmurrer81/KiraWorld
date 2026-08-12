#!/usr/bin/env python3
"""Static fail-closed tests for the no-save R23 carrier-annulus simulation."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import unittest

from tools import blender_simulate_kira_r23_carrier_annulus_repair as worker_module


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_carrier_annulus_repair_simulation_preparation/"
    "KIRA_R23_CARRIER_ANNULUS_REPAIR_SIMULATION_CONFIG.json"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R23CarrierAnnulusSimulationPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_status_requires_explicit_readonly_execution(self):
        self.assertEqual(
            self.config["status"],
            "BOUND_NOT_RUN_EXPLICIT_READONLY_SIMULATION_REQUIRED",
        )

    def test_worker_accepts_only_the_exact_reviewed_config(self):
        worker_module.validate_config(self.config)
        mutations = []
        changed = deepcopy(self.config)
        changed["status"] = "READY"
        mutations.append(changed)
        changed = deepcopy(self.config)
        changed["parameter_grid"]["inner_radius"].append(0.55)
        mutations.append(changed)
        changed = deepcopy(self.config)
        changed["execution_restrictions"]["render_forbidden"] = False
        mutations.append(changed)
        changed = deepcopy(self.config)
        changed["output"]["directory"] = "RecoverySprint/escaped"
        mutations.append(changed)
        changed = deepcopy(self.config)
        changed["truth_boundary"]["internal_biological_function"] = True
        mutations.append(changed)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(worker_module.AnnulusError):
                    worker_module.validate_config(mutation)

    def test_every_binding_is_exact(self):
        for label, binding in self.config["bindings"].items():
            with self.subTest(label=label):
                path = ROOT / binding["path"]
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(digest(path), binding["sha256"])

    def test_grid_is_fixed_nine_variants(self):
        grid = self.config["parameter_grid"]
        self.assertEqual(grid["ring_count"], 4)
        self.assertEqual(grid["inner_radius"], [0.25, 0.35, 0.45])
        self.assertEqual(grid["blend_power"], [1.0, 2.0, 3.0])
        self.assertEqual(len(grid["inner_radius"]) * len(grid["blend_power"]), 9)

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

    def test_worker_contains_no_save_render_or_export_operator(self):
        worker = (ROOT / self.config["bindings"]["worker"]["path"]).read_text(
            encoding="utf-8"
        )
        for marker in (
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.wm.save_mainfile",
            "bpy.ops.render.render",
            "bpy.ops.export_scene",
            "bpy.ops.export_mesh",
        ):
            self.assertNotIn(marker, worker)

    def test_worker_contains_all_added_fail_closed_gates(self):
        worker = (ROOT / self.config["bindings"]["worker"]["path"]).read_text(
            encoding="utf-8"
        )
        for marker in (
            "stable_source_boundary_exact",
            "zero_duplicate_mesh_edges",
            "patch_weight_gradient_nonregression",
            "uv_geometry_and_exact_seam_choice",
            "exact_r19_seam_pose_nonregression",
            "patch_involving_bvh_pair_count",
            "NO_CARRIER_ANNULUS_VARIANT_PASSED_ALL_ADDED_FAIL_CLOSED_GATES",
        ):
            self.assertIn(marker, worker)
        self.assertNotIn('base["faces"][861:]', worker)
        self.assertNotIn("author.DEFAULT_CONFIG", worker)

    def test_output_is_append_only_evidence_not_a_body(self):
        output = self.config["output"]
        self.assertIs(output["append_only"], True)
        self.assertEqual(output["filename"], "ANNULUS_SIMULATION_EVIDENCE.json")
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
        self.assertIn("explicit --execute-readonly-simulation is required", result.stderr)

    def test_truth_boundary_refuses_function_and_approval_claims(self):
        truth = self.config["truth_boundary"]
        for key in (
            "owner_visual_approval",
            "internal_biological_function",
            "bathroom_function",
            "pregnancy_or_reproductive_function",
            "subjective_sensation_or_experience",
            "privacy_or_memory_acceptance",
            "author_candidate_created",
        ):
            self.assertIs(truth[key], False)


if __name__ == "__main__":
    unittest.main()
