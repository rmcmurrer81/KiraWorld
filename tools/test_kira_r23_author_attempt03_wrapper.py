#!/usr/bin/env python3
"""Static/dry tests for R23 Author Attempt03 wrapper-only repair."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools import kira_r23_author_attempt02_invocation as base
from tools.kira_r23_author_attempt03_invocation import (
    build_command,
    output_contract,
    verify_all,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt03_wrapper_preparation/"
    "INVOCATION_CONFIG.json"
)
WORKER = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt01.py"
PREFLIGHT_BASE = ROOT / "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask.py"
SHARED_CORE = ROOT / "Tools/kira_r23_cc0_afes_preflight_core.py"
BLENDER_WRAPPER = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt03_wrapper.py"
INVOCATION = ROOT / "Tools/kira_r23_author_attempt03_invocation.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def top_level_symbols(tree: ast.Module) -> set[str]:
    result: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                result.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            result.add(node.target.id)
    return result


class R23AuthorAttempt03WrapperTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(SPEC.read_text(encoding="utf-8"))

    def test_all_new_sources_parse(self):
        for path in (BLENDER_WRAPPER, INVOCATION, Path(__file__)):
            ast.parse(path.read_text(encoding="utf-8"))
        json.loads(SPEC.read_text(encoding="utf-8"))

    def test_sealed_and_prior_evidence_hashes_are_exact(self):
        verified = verify_all(self.spec)
        self.assertEqual(len(verified), 20)
        expected = {
            "sealed_author_config": "8e6a63a21a52e7df7db895decf71b69a55e84f3ad7401073b0e4e6130b9fb5eb",
            "sealed_author_worker": "b6fb28f0d4d9e6c043649e8119b062f3c12497ffa90567de9ef81da50b887ef0",
            "sealed_author_core": "9240eddc7901cce5fefa9dd214b237af48ea2464778bb4aa3afa6414988e6064",
            "shared_preflight_core": "39eeee991941a229f9d76d56b2c61c0b3a86c62e34242e2f7a1ab4036ebb17ba",
            "r19_source_blend": "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f",
            "preserved_attempt02_author_failure": "8220e67952f095ab596e6241db1e468b861f735dfdf13f53d17576bc20fb888c",
        }
        for name, digest in expected.items():
            self.assertEqual(verified[name]["sha256"], digest, name)

    def test_every_preflight_base_attribute_resolves_after_patch(self):
        worker_tree = ast.parse(WORKER.read_text(encoding="utf-8"))
        used = {
            node.attr
            for node in ast.walk(worker_tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "preflight_base"
        }
        available_before = top_level_symbols(
            ast.parse(PREFLIGHT_BASE.read_text(encoding="utf-8"))
        )
        self.assertEqual(used.difference(available_before), {"edge_face_map"})
        shared = top_level_symbols(ast.parse(SHARED_CORE.read_text(encoding="utf-8")))
        self.assertIn("edge_face_map", shared)
        available_after = available_before | {"edge_face_map"}
        self.assertEqual(used.difference(available_after), set())
        self.assertEqual(
            sorted(used),
            [
                "actions_sha256",
                "boundary_edges_for_region",
                "canonical_index_sha256",
                "canonical_json_sha256",
                "edge_face_map",
                "faces_of",
                "material_graph_record",
                "mesh_full_state_sha256",
                "ordered_boundary_cycles",
                "rig_rest_sha256",
                "topology_record",
                "vector_record",
                "weight_rows",
            ],
        )

    def test_blender_wrapper_patches_only_symbol_and_output_binding(self):
        source = BLENDER_WRAPPER.read_text(encoding="utf-8")
        self.assertIn(
            "from tools.kira_r23_cc0_afes_preflight_core import edge_face_map",
            source,
        )
        self.assertIn("sealed_worker.preflight_base.edge_face_map = edge_face_map", source)
        self.assertIn("sealed_worker.output_paths = attempt03_output_paths", source)
        self.assertIn('effective["output"]["directory"] = EFFECTIVE_ATTEMPT03_OUTPUT', source)
        self.assertIn("return int(sealed_worker.main())", source)
        self.assertNotIn("bpy.ops", source)
        self.assertNotIn("bmesh", source)
        self.assertNotIn("save_as_mainfile", source)
        self.assertNotIn("render", source.lower())

    def test_configured_and_effective_outputs_are_isolated(self):
        outputs = output_contract(self.spec)
        self.assertEqual(
            outputs["configured_relative"],
            "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author/attempt_01",
        )
        self.assertEqual(
            outputs["effective_relative"],
            "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author/attempt_03",
        )
        self.assertTrue(outputs["configured"].is_dir())
        self.assertFalse(outputs["effective"].exists())
        self.assertEqual(
            sorted(path.name for path in outputs["configured"].iterdir()),
            ["FAILURE_EVIDENCE.json"],
        )
        author = json.loads(
            (ROOT / self.spec["bound_artifacts"]["sealed_author_config"]["path"])
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            author["output"]["directory"], outputs["configured_relative"]
        )

    def test_command_retains_relative_config_and_exit_order(self):
        command = build_command(self.spec)
        config_value = command[command.index("--config") + 1]
        self.assertFalse(Path(config_value).is_absolute())
        self.assertNotIn("..", Path(config_value).parts)
        self.assertLess(command.index("--python-exit-code"), command.index("--python"))
        self.assertEqual(command[command.index("--python-exit-code") + 1], "7")
        self.assertEqual(
            Path(command[command.index("--python") + 1]).name,
            BLENDER_WRAPPER.name,
        )
        self.assertEqual(command[-1], "--execute-authoring")

    def test_false_zero_classification_is_retained(self):
        self.assertEqual(base.classified_exit_code(2, "", False, True, False), 2)
        self.assertEqual(
            base.classified_exit_code(
                0,
                "Traceback (most recent call last):\nAttributeError",
                False,
                False,
                False,
            ),
            7,
        )
        self.assertEqual(base.classified_exit_code(0, "", False, False, False), 7)
        self.assertEqual(base.classified_exit_code(0, "", True, False, True), 0)

    def test_dry_launcher_does_not_start_blender_or_create_outputs(self):
        execution = ROOT / self.spec["future_execution"]["directory"]
        effective = ROOT / self.spec["success_contract"]["effective_output_directory"]
        self.assertFalse(execution.exists())
        self.assertFalse(effective.exists())
        result = subprocess.run(
            [sys.executable, "-B", str(INVOCATION)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(
            record["status"], "DRY_ATTEMPT03_WRAPPER_ONLY_BLENDER_NOT_RUN"
        )
        self.assertTrue(record["config_argument_is_relative"])
        self.assertTrue(record["python_exit_code_precedes_python"])
        self.assertTrue(record["configured_output_exists"])
        self.assertFalse(record["effective_output_exists"])
        self.assertFalse(record["blender_run"])
        self.assertFalse(execution.exists())
        self.assertFalse(effective.exists())

    def test_scope_and_source_absence_gates(self):
        scope = self.spec["scope"]
        self.assertEqual(
            scope["runtime_bindings_changed"],
            [
                "sealed_worker.preflight_base.edge_face_map",
                "sealed_worker.output_paths",
            ],
        )
        self.assertFalse(scope["sealed_author_config_changed"])
        self.assertFalse(scope["sealed_author_worker_changed"])
        self.assertFalse(scope["sealed_author_core_changed"])
        self.assertFalse(scope["geometry_or_material_logic_changed"])
        self.assertFalse(scope["blender_run_authorized_by_preparation"])
        self.assertFalse(
            (ROOT / self.spec["future_execution"]["directory"]).exists()
        )
        self.assertFalse(
            (
                ROOT
                / self.spec["success_contract"]["effective_output_directory"]
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
