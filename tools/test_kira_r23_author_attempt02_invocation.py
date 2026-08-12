#!/usr/bin/env python3
"""Dry/static tests for the R23 Author Attempt02 invocation correction."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.kira_r23_author_attempt02_invocation import (
    build_command,
    classified_exit_code,
    verify_all,
)


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "Tools/kira_r23_author_attempt02_invocation.py"
SPEC = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt02_invocation_preparation/"
    "INVOCATION_CONFIG.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R23AuthorAttempt02InvocationTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(SPEC.read_text(encoding="utf-8"))

    def test_sources_parse(self):
        ast.parse(LAUNCHER.read_text(encoding="utf-8"))
        json.loads(SPEC.read_text(encoding="utf-8"))

    def test_sealed_author_artifacts_are_unchanged(self):
        expected = {
            "sealed_author_config": "8e6a63a21a52e7df7db895decf71b69a55e84f3ad7401073b0e4e6130b9fb5eb",
            "sealed_author_worker": "b6fb28f0d4d9e6c043649e8119b062f3c12497ffa90567de9ef81da50b887ef0",
            "sealed_author_core": "9240eddc7901cce5fefa9dd214b237af48ea2464778bb4aa3afa6414988e6064",
            "r19_source_blend": "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f",
            "passed_attempt04_preflight": "2fd7968db9e7d00882d031d519aa04472b343cdf2141f6dcc6c672a77c0a5935",
        }
        verified = verify_all(self.spec)
        for name, digest in expected.items():
            self.assertEqual(verified[name]["sha256"], digest)

    def test_attempt01_failure_is_preserved_byte_for_byte(self):
        root = ROOT / self.spec["preserved_attempt01_failure"]["directory"]
        for name, binding in self.spec["preserved_attempt01_failure"]["files"].items():
            path = root / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, binding["bytes"], name)
            self.assertEqual(sha256(path), binding["sha256"], name)

    def test_command_uses_relative_config_and_correct_exit_option_order(self):
        command = build_command(self.spec)
        config_index = command.index("--config")
        config_argument = command[config_index + 1]
        self.assertFalse(Path(config_argument).is_absolute())
        self.assertNotIn("..", Path(config_argument).parts)
        self.assertEqual(
            config_argument,
            "RecoverySprint/continuation_20260803/"
            "kira_r23_cc0_afes_author_attempt01_preparation/"
            "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT01_CONFIG.json",
        )
        exit_index = command.index("--python-exit-code")
        python_index = command.index("--python")
        self.assertLess(exit_index, python_index)
        self.assertEqual(command[exit_index + 1], "7")
        self.assertEqual(command[-1], "--execute-authoring")

    def test_nonzero_and_hidden_traceback_cannot_be_reported_as_success(self):
        self.assertEqual(classified_exit_code(7, "", False, False, False), 7)
        self.assertEqual(classified_exit_code(3, "", False, False, False), 3)
        self.assertEqual(
            classified_exit_code(
                0,
                "Traceback (most recent call last):\nRuntimeError: fail",
                False,
                False,
                False,
            ),
            7,
        )
        self.assertEqual(classified_exit_code(0, "", False, True, False), 7)
        self.assertEqual(classified_exit_code(0, "", False, False, False), 7)
        self.assertEqual(classified_exit_code(0, "", True, False, True), 0)

    def test_wrapper_returns_effective_exit_without_shell(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("return int(effective_exit)", source)
        self.assertIn("raise SystemExit(main())", source)
        self.assertIn("shell=False", source)
        self.assertIn("subprocess.CREATE_NO_WINDOW", source)

    def test_dry_launcher_runs_without_blender_or_outputs(self):
        execution = ROOT / self.spec["future_execution"]["directory"]
        output = ROOT / self.spec["configured_author_output_unchanged"]["directory"]
        self.assertFalse(execution.exists())
        self.assertFalse(output.exists())
        result = subprocess.run(
            [sys.executable, "-B", str(LAUNCHER)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(
            record["status"], "DRY_COMMAND_CONSTRUCTION_ONLY_BLENDER_NOT_RUN"
        )
        self.assertTrue(record["config_argument_is_relative"])
        self.assertTrue(record["python_exit_code_precedes_python"])
        self.assertFalse(record["blender_run"])
        self.assertFalse(execution.exists())
        self.assertFalse(output.exists())

    def test_preparation_scope_is_invocation_only(self):
        scope = self.spec["scope"]
        self.assertTrue(scope["command_construction_only"])
        self.assertFalse(scope["sealed_author_config_changed"])
        self.assertFalse(scope["sealed_worker_changed"])
        self.assertFalse(scope["sealed_core_changed"])
        self.assertFalse(scope["mesh_author_method_changed"])
        self.assertFalse(scope["blender_run_authorized_by_preparation"])


if __name__ == "__main__":
    unittest.main()
