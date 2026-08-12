#!/usr/bin/env python3
"""Static tests for the prepared R23 seam/topology diagnostic package.

These tests must not import Blender, start Blender, or write diagnostic output.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_seam_topology_diagnostic_preparation/"
    "INVOCATION_CONFIG.json"
)
WRAPPER_PATH = ROOT / "Tools/blender_diagnose_kira_r23_seam_topology_attempt01.py"
CONTROLLER_PATH = ROOT / "Tools/kira_r23_seam_topology_diagnostic_invocation.py"
SEALED_WORKER_PATH = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt01.py"
PREFLIGHT_BASE_PATH = ROOT / "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def top_level_symbols(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


class DiagnosticPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.wrapper_source = WRAPPER_PATH.read_text(encoding="utf-8")
        cls.controller_source = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.worker_source = SEALED_WORKER_PATH.read_text(encoding="utf-8")
        cls.wrapper_tree = ast.parse(cls.wrapper_source)
        cls.controller_tree = ast.parse(cls.controller_source)
        cls.worker_tree = ast.parse(cls.worker_source)

    def test_python_and_json_parse(self) -> None:
        self.assertEqual(
            self.spec["schema"],
            "kira.avatar.r23_seam_topology_diagnostic_invocation.v1",
        )
        self.assertIsInstance(self.wrapper_tree, ast.Module)
        self.assertIsInstance(self.controller_tree, ast.Module)

    def test_bound_artifacts_and_preserved_attempts_are_exact(self) -> None:
        for label, binding in self.spec["bound_artifacts"].items():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, binding["bytes"], label)
            self.assertEqual(sha256_file(path), binding["sha256"], label)
        for label, record in self.spec["preserved_attempts"].items():
            directory = ROOT / record["directory"]
            expected = set(record["files"])
            actual = {path.name for path in directory.iterdir() if path.is_file()}
            self.assertEqual(actual, expected, label)
            for name, binding in record["files"].items():
                path = directory / name
                self.assertEqual(path.stat().st_size, binding["bytes"], f"{label}/{name}")
                self.assertEqual(sha256_file(path), binding["sha256"], f"{label}/{name}")

    def test_preflight_dependency_gap_is_only_edge_face_map(self) -> None:
        used = {
            node.attr
            for node in ast.walk(self.worker_tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "preflight_base"
        }
        available = top_level_symbols(
            ast.parse(PREFLIGHT_BASE_PATH.read_text(encoding="utf-8"))
        )
        self.assertEqual(used.difference(available), {"edge_face_map"})
        self.assertIn(
            "sealed_worker.preflight_base.edge_face_map = edge_face_map",
            self.wrapper_source,
        )

    def test_runtime_assignments_are_exact_and_bounded(self) -> None:
        targets = []
        for node in ast.walk(self.wrapper_tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Attribute):
                    continue
                rendered = ast.unparse(target)
                if rendered.startswith("sealed_worker."):
                    targets.append(rendered)
        self.assertEqual(
            sorted(targets),
            sorted(
                self.spec["runtime_patch_contract"]["runtime_assignment_targets"]
            ),
        )

    def test_instrumentation_contract_is_present(self) -> None:
        required_tokens = [
            "face_edge_incidence",
            "whole_boundary",
            "greater_than_two",
            "loose_edge_rows",
            "duplicate_mesh_rows",
            "duplicate_face_rows",
            "expected_whole",
            "whole_deltas",
            "patch_deltas",
            "patch_boundary_sha256",
            "outside_boundary_sha256",
            "matched_target_seam_sha256",
            "patch_only_boundary_sha256",
            "outside_only_boundary_sha256",
            "source_and_stop_proof",
        ]
        for token in required_tokens:
            self.assertIn(token, self.wrapper_source)
        for label in self.spec["diagnostic_contract"]["required_defect_labels"]:
            self.assertIn(label, self.wrapper_source)

    def test_patch_region_partition_is_exact(self) -> None:
        regions = self.spec["diagnostic_contract"][
            "required_patch_face_region_counts"
        ]
        self.assertEqual(regions["outer_unequal_cycle_zipper"], 91 + 154)
        self.assertEqual(regions["outer_to_inner_collar_bridge"], 154 * 2)
        self.assertEqual(regions["inner_collar_to_donor_bridge"], 154 * 2)
        self.assertEqual(regions["donor_disk_interior"], 2488)
        self.assertEqual(
            sum(value for key, value in regions.items() if key != "total"),
            regions["total"],
        )
        self.assertEqual(regions["total"], 3349)

    def test_deliberate_stop_precedes_removal_freeze_and_save(self) -> None:
        topology_call = self.worker_source.index(
            'topology = topology_gate(body, apply_evidence["patch_face_indices"], config)'
        )
        donor_remove = self.worker_source.index("bpy.data.objects.remove(donor")
        freeze_after = self.worker_source.index("freeze_after = post_author_freeze_gate")
        save = self.worker_source.index("bpy.ops.wm.save_as_mainfile")
        self.assertLess(topology_call, donor_remove)
        self.assertLess(donor_remove, freeze_after)
        self.assertLess(freeze_after, save)
        stop = self.spec["runtime_patch_contract"]["intentional_stop_error"]
        self.assertIn(stop, self.wrapper_source)
        gate = next(
            node
            for node in self.wrapper_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "diagnostic_topology_gate"
        )
        self.assertIsInstance(gate.body[-1], ast.Raise)

    def test_diagnostic_wrapper_has_no_save_render_or_export_operator(self) -> None:
        forbidden = [
            "bpy.ops.wm.save",
            "bpy.ops.render",
            "bpy.ops.export",
            "bpy.ops.wm.open",
        ]
        for token in forbidden:
            self.assertNotIn(token, self.wrapper_source)

    def test_output_paths_are_fresh_and_candidate_absent(self) -> None:
        runtime = self.spec["runtime_patch_contract"]
        output = ROOT / runtime["effective_diagnostic_output"]
        execution = ROOT / self.spec["future_execution"]["directory"]
        self.assertFalse(output.exists())
        self.assertFalse(execution.exists())
        self.assertFalse((output / runtime["candidate_filename"]).exists())

    def test_source_is_exact(self) -> None:
        binding = self.spec["bound_artifacts"]["r19_source_blend"]
        source = ROOT / binding["path"]
        self.assertEqual(source.stat().st_size, binding["bytes"])
        self.assertEqual(sha256_file(source), binding["sha256"])

    def test_controller_dry_run_builds_correct_command_without_blender(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CONTROLLER_PATH)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(
            record["status"], "DRY_COMMAND_CONSTRUCTION_ONLY_BLENDER_NOT_RUN"
        )
        self.assertFalse(record["blender_run"])
        self.assertTrue(record["config_argument_is_relative"])
        self.assertTrue(record["python_exit_code_precedes_python"])
        self.assertTrue(record["diagnostic_output_fresh"])
        self.assertTrue(record["execution_output_fresh"])
        command = record["command"]
        self.assertLess(command.index("--python-exit-code"), command.index("--python"))
        self.assertEqual(command[command.index("--python-exit-code") + 1], "7")
        self.assertEqual(
            Path(command[command.index("--python") + 1]).resolve(),
            WRAPPER_PATH.resolve(),
        )
        self.assertFalse(Path(command[command.index("--config") + 1]).is_absolute())


if __name__ == "__main__":
    unittest.main(verbosity=2)
