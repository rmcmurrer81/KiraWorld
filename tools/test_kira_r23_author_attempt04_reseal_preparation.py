#!/usr/bin/env python3
"""Focused static, dry, negative, and mocked-execution tests for R23 reseal."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_CONFIG.json"
)
MANIFEST = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_preparation/PACKAGE_MANIFEST.json"
)
CONTROLLER = ROOT / "Tools/kira_r23_author_attempt04_reseal_invocation.py"
WRAPPER = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_wrapper.py"
TOPOLOGY_IMPL = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt04_wrapper.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Attempt04ResealPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.controller_text = CONTROLLER.read_text(encoding="utf-8")
        cls.wrapper_text = WRAPPER.read_text(encoding="utf-8")
        cls.topology_text = TOPOLOGY_IMPL.read_text(encoding="utf-8")

    def test_inert_schema_has_no_arbitrary_spec_execution(self) -> None:
        self.assertEqual(
            self.config["schema"], "kira.avatar.r23_author_attempt04_repair.v1"
        )
        self.assertEqual(
            self.config["reseal_schema"],
            "kira.avatar.r23_author_attempt04_reseal.v1",
        )
        self.assertFalse(self.config["execution_gate"]["execution_enabled_at_preparation"])
        tree = ast.parse(self.controller_text)
        string_values = {
            node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn("--spec", string_values)
        self.assertIn("--execute-attempt04-reseal", string_values)
        authorization = ROOT / self.config["execution_gate"]["authorization_path"]
        self.assertFalse(authorization.exists())

    def test_manifest_and_every_configured_hash_are_exact(self) -> None:
        manifest_paths = {entry["path"] for entry in self.manifest["artifacts"]}
        self.assertEqual(
            manifest_paths,
            set(self.config["manifest_contract"]["required_artifact_paths"]),
        )
        for entry in self.manifest["artifacts"]:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(path.stat().st_size, entry["bytes"], entry["path"])
            self.assertEqual(sha256(path), entry["sha256"], entry["path"])
        for label, binding in self.config["bound_artifacts"].items():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, binding["bytes"], label)
            self.assertEqual(sha256(path), binding["sha256"], label)
        for section in self.config["preserved_append_only_evidence"]:
            directory = ROOT / section["directory"]
            self.assertEqual(
                sorted(entry.name for entry in directory.iterdir()),
                sorted(section["files"]),
                section["label"],
            )
            for name, binding in section["files"].items():
                path = directory / name
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])

    def test_complete_project_runtime_dependency_closure_is_bound(self) -> None:
        required = {
            "Tools/kira_r23_author_attempt02_invocation.py",
            "Tools/blender_author_kira_r23_cc0_afes_attempt04_wrapper.py",
            "Tools/blender_author_kira_r23_cc0_afes_attempt01.py",
            "Tools/kira_r23_cc0_afes_preflight_core.py",
            "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask.py",
            "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask_attempt03.py",
            "Tools/kira_r23_blender51_action_serializer.py",
            "Tools/kira_r23_cc0_afes_author_core.py",
            "Tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_wrapper.py",
            "Tools/kira_r23_author_attempt04_reseal_invocation.py",
        }
        bound = {binding["path"] for binding in self.config["bound_artifacts"].values()}
        self.assertTrue(required.issubset(bound), sorted(required.difference(bound)))
        self.assertEqual(
            self.config["runtime_dependency_closure"]["project_local_modules"],
            sorted(required),
        )
        self.assertFalse(self.config["runtime_dependency_closure"]["dynamic_local_imports_found"])

    def test_topology_repair_and_face_edges_shadow_fix_remain_exact(self) -> None:
        aliases = {
            alias.asname or alias.name
            for node in ast.walk(ast.parse(self.topology_text))
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
            if alias.name == "face_edges"
        }
        self.assertEqual(aliases, {"topology_face_edges"})
        self.assertIn("actual_chords == expected_chords", self.topology_text)
        self.assertIn('context="EDGES"', self.topology_text)
        self.assertNotIn("remove_doubles", self.topology_text)
        final = self.config["nominal_corrected_final"]
        self.assertEqual(
            (final["vertices"], final["mesh_edges"], final["faces"]),
            (13940, 41551, 27590),
        )
        self.assertEqual(final["boundary_edges"], 330)
        self.assertEqual(final["boundary_cycles"], 23)
        self.assertEqual(final["euler"], -21)

    def test_current_final_policy_and_no_go_evidence_are_bound(self) -> None:
        bindings = self.config["bound_artifacts"]
        self.assertEqual(
            bindings["current_system_body_systems_plan"]["sha256"],
            "c066e9d42519380b92591dcf71ac54f674545867d19bb1422885d1dc3f85a86f",
        )
        self.assertEqual(
            bindings["current_adult_curriculum_policy"]["sha256"],
            "c89019aa77b3af69505220eafd5fdca6f8a0ed17163d325bcbad10cf7c7a95f1",
        )
        self.assertEqual(
            bindings["attempt04_no_go_manifest"]["sha256"],
            "82936ec796abdb95c4350994d94b1200706292de2661a5ca495193814815921d",
        )
        no_claims = self.config["clinical_semantics_contract"]["no_claims"]
        self.assertIn("complete working biological anatomy", no_claims)
        self.assertTrue(self.config["clinical_semantics_contract"]["metadata_only_no_geometry_creation"])

    def test_blender_identity_positive_and_negative(self) -> None:
        from tools import kira_r23_author_attempt04_reseal_invocation as controller

        observed = controller.verify_blender_identity(self.config)
        self.assertEqual(observed["bytes"], 108687824)
        self.assertEqual(
            observed["sha256"],
            "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5",
        )
        with mock.patch.object(controller, "sha256_file", return_value="0" * 64):
            with self.assertRaises(controller.Attempt04ResealError):
                controller.verify_blender_identity(self.config)

    def test_unexpected_directory_and_reparse_are_rejected(self) -> None:
        from tools import kira_r23_author_attempt04_reseal_invocation as controller

        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            directory = Path(raw)
            file_path = directory / "expected.txt"
            file_path.write_text("x", encoding="utf-8")
            section = {
                "label": "test",
                "directory": file_path.parent.relative_to(ROOT).as_posix(),
                "files": {
                    "expected.txt": {
                        "bytes": 1,
                        "sha256": sha256(file_path),
                    }
                },
            }
            controller.verify_exact_directory(section)
            (directory / "unexpected").mkdir()
            with self.assertRaises(controller.Attempt04ResealError):
                controller.verify_exact_directory(section)
            (directory / "unexpected").rmdir()
            original = controller.is_reparse

            def fake_reparse(path: Path) -> bool:
                return path.name == "expected.txt" or original(path)

            with mock.patch.object(controller, "is_reparse", side_effect=fake_reparse):
                with self.assertRaises(controller.Attempt04ResealError):
                    controller.verify_exact_directory(section)

    def test_dry_default_is_output_isolated_and_never_runs_subprocess(self) -> None:
        from tools import kira_r23_author_attempt04_reseal_invocation as controller

        output = io.StringIO()
        with mock.patch.object(controller.base, "blender_process_count", return_value=0):
            with mock.patch.object(controller.subprocess, "run") as run:
                with redirect_stdout(output):
                    self.assertEqual(controller.main([]), 0)
                run.assert_not_called()
        record = json.loads(output.getvalue())
        self.assertEqual(
            record["status"],
            "DRY_ATTEMPT04_RESEAL_PREPARED_NOT_AUTHORIZED_BLENDER_NOT_RUN",
        )
        self.assertFalse(record["execution_enabled"])
        self.assertFalse(record["authorization_exists"])
        self.assertFalse(record["effective_output_exists"])
        self.assertFalse(record["execution_output_exists"])

    def test_execute_flag_refuses_without_authorization_before_output(self) -> None:
        from tools import kira_r23_author_attempt04_reseal_invocation as controller

        effective = ROOT / self.config["repair_contract"]["effective_output"]
        execution = ROOT / self.config["future_execution"]["directory"]
        self.assertFalse(effective.exists())
        self.assertFalse(execution.exists())
        with mock.patch.object(controller.base, "blender_process_count", return_value=0):
            with self.assertRaises(controller.Attempt04ResealError):
                controller.main(["--execute-attempt04-reseal"])
        self.assertFalse(effective.exists())
        self.assertFalse(execution.exists())

    def _mock_execute(self, tamper: bool) -> tuple[int, dict[str, object]]:
        from tools import kira_r23_author_attempt04_reseal_invocation as controller

        config = deepcopy(self.config)
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            temporary = Path(raw)
            effective = temporary / "author"
            execution = temporary / "execution"
            outputs = {
                "configured": ROOT / config["repair_contract"]["configured_output_required"],
                "configured_relative": config["repair_contract"]["configured_output_required"],
                "effective": effective,
                "effective_relative": effective.relative_to(ROOT).as_posix(),
                "execution": execution,
                "execution_relative": execution.relative_to(ROOT).as_posix(),
            }
            manifest = {
                "path": "reviewed/PACKAGE_MANIFEST.json",
                "bytes": 1,
                "sha256": "1" * 64,
                "artifacts": {},
            }
            blender = {
                "path": self.config["blender_identity"]["path"],
                "bytes": self.config["blender_identity"]["bytes"],
                "sha256": self.config["blender_identity"]["sha256"],
                "file_version": "5.1",
                "product_version": "5.1",
            }
            authorization = {"sha256": "2" * 64}
            snapshot = {"protected": {"path": "x", "bytes": 1, "sha256": "3" * 64}}

            def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
                effective.mkdir(parents=True)
                (effective / config["success_contract"]["build_evidence"]).write_text(
                    "{}\n", encoding="utf-8"
                )
                (effective / config["success_contract"]["candidate"]).write_bytes(b"blend")
                return SimpleNamespace(returncode=0)

            verify_sequence: list[object] = [snapshot]
            verify_sequence.append(
                controller.Attempt04ResealError("post-run tamper") if tamper else snapshot
            )
            with mock.patch.object(controller, "verify_all", side_effect=verify_sequence):
                with mock.patch.object(controller, "output_contract", return_value=outputs):
                    with mock.patch.object(controller, "build_command", return_value=["mock-blender"]):
                        with mock.patch.object(controller.base, "blender_process_count", return_value=0):
                            with mock.patch.object(controller.subprocess, "run", side_effect=fake_run):
                                with mock.patch.object(controller, "verify_manifest", return_value=manifest):
                                    with mock.patch.object(controller, "verify_blender_identity", return_value=blender):
                                        result = controller.execute_once(
                                            config, manifest, blender, authorization
                                        )
            post = json.loads(
                (execution / config["future_execution"]["post_run"]).read_text(
                    encoding="utf-8"
                )
            )
            return result, post

    def test_mocked_execute_success_requires_postrun_equality(self) -> None:
        result, post = self._mock_execute(tamper=False)
        self.assertEqual(result, 0)
        self.assertTrue(post["postrun_protection"]["passed"])
        self.assertEqual(
            post["postrun_protection"]["pre_snapshot_sha256"],
            post["postrun_protection"]["post_snapshot_sha256"],
        )

    def test_mocked_postrun_tamper_forces_nonzero_and_records_error(self) -> None:
        result, post = self._mock_execute(tamper=True)
        self.assertEqual(result, 7)
        self.assertFalse(post["postrun_protection"]["passed"])
        self.assertIn("post-run tamper", post["postrun_protection"]["error"])


if __name__ == "__main__":
    unittest.main()
