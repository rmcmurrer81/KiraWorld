#!/usr/bin/env python3
"""Static, dry, and realistic mocked tests for R23 Attempt04 reseal v2."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v2_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V2_CONFIG.json"
)
MANIFEST_PATH = CONFIG_PATH.parent / "PACKAGE_MANIFEST.json"
CONTROLLER_PATH = ROOT / "Tools/kira_r23_author_attempt04_reseal_v2_invocation.py"
WRAPPER_PATH = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_v2_wrapper.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def import_controller() -> object:
    spec = importlib.util.spec_from_file_location("_reseal_v2_test_controller", CONTROLLER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_wrapper() -> object:
    fake_bpy = SimpleNamespace(app=SimpleNamespace(version=(5, 1, 2)))
    spec = importlib.util.spec_from_file_location("_reseal_v2_test_wrapper", WRAPPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"bpy": fake_bpy}):
        spec.loader.exec_module(module)
    return module


class FakeTimeoutProcess:
    def __init__(self) -> None:
        self.wait_calls = 0
        self.terminate_calls = 0
        self.kill_calls = 0

    def wait(self, timeout: float) -> int:
        self.wait_calls += 1
        if self.wait_calls <= 2:
            raise subprocess.TimeoutExpired("mock", timeout)
        return 7

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1


class ResealV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller = import_controller()
        cls.wrapper = import_wrapper()
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.controller_text = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.wrapper_text = WRAPPER_PATH.read_text(encoding="utf-8")

    def test_01_manifest_hashes_complete_module_closure_and_execution_disabled(self) -> None:
        self.assertFalse(self.config["execution_gate"]["execution_enabled_at_preparation"])
        self.assertEqual(
            self.config["schema"], "kira.avatar.r23_author_attempt04_reseal_v2.v1"
        )
        paths = {entry["path"] for entry in self.manifest["artifacts"]}
        self.assertEqual(paths, set(self.config["manifest_contract"]["required_artifact_paths"]))
        for entry in self.manifest["artifacts"]:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, entry["bytes"])
            self.assertEqual(sha256(path), entry["sha256"])
        bound = {value["path"] for value in self.config["bound_artifacts"].values()}
        modules = set(self.config["runtime_dependency_closure"]["project_local_modules"])
        self.assertTrue(modules.issubset(bound), sorted(modules - bound))
        for label, binding in self.config["bound_artifacts"].items():
            path = ROOT / binding["path"]
            self.assertEqual(path.stat().st_size, binding["bytes"], label)
            self.assertEqual(sha256(path), binding["sha256"], label)
        self.assertEqual(
            self.config["bound_artifacts"]["prior_reseal_no_go_manifest"]["sha256"],
            "2195f377572ce98227e8d4adea60a766026d7ebe4115ddf1a4bce31b61d55a3d",
        )
        self.assertTrue(
            self.config["runtime_dependency_closure"]
            ["delegated_reseal_bound_and_protected_closure_recursively_verified"]
        )
        self.assertIn('verified[f"delegated_bound/{label}"]', self.controller_text)
        self.assertIn('verified[f"delegated_protected/{section[\'label\']}/{name}"]', self.controller_text)

    def test_02_wrapper_requires_exact_argv_and_rejects_alternate_config(self) -> None:
        expected = self.config["command_contract"]["delegated_config_argument"]
        valid = ["blender", "--", "--config", expected, "--execute-authoring"]
        self.assertEqual(
            self.wrapper.parse_exact_worker_argv(valid, expected=expected), valid[2:]
        )
        for tail in (
            ["blender", "--", "--config", "alternate.json", "--execute-authoring"],
            ["blender", "--", "--execute-authoring", "--config", expected],
            ["blender", "--", "--config", expected, "--execute-authoring", "extra"],
        ):
            with self.assertRaises(self.wrapper.BlenderResealV2Error):
                self.wrapper.parse_exact_worker_argv(tail, expected=expected)

    def test_03_direct_wrapper_cannot_use_arbitrary_environment_hash_without_live_auth(self) -> None:
        expected = self.config["command_contract"]["delegated_config_argument"]
        argv = ["blender", "--", "--config", expected, "--execute-authoring"]
        spoofed = {
            "KIRA_R23_RESEAL_V2_PREPARATION_MANIFEST_SHA256": "a" * 64,
            "KIRA_R23_RESEAL_V2_CONFIG_SHA256": "b" * 64,
            "KIRA_R23_RESEAL_V2_AUTHORIZATION_RECORD_SHA256": "c" * 64,
            "KIRA_R23_RESEAL_V2_AUTHORIZATION_MANIFEST_SHA256": "d" * 64,
            "KIRA_R23_RESEAL_V2_AUTHORIZATION_NONCE": "x" * 32,
        }
        with mock.patch.dict(os.environ, spoofed, clear=False):
            with self.assertRaises(Exception) as caught:
                self.wrapper.main(argv)
        self.assertIn("authorization", str(caught.exception).lower())
        self.assertNotIn("require_env_sha", self.wrapper_text)
        independent_auth_index = self.wrapper_text.index(
            "bootstrap_authorization = bootstrap_verify_live_authorization("
        )
        controller_import_index = self.wrapper_text.index(
            "controller = _load_verified_controller(config)"
        )
        self.assertLess(independent_auth_index, controller_import_index)

    def _synthetic_authorization(
        self, temporary: Path, preparation: dict[str, object] | None = None
    ) -> tuple[dict[str, object], dict[str, object], list[str]]:
        controller = self.controller
        config = deepcopy(self.config)
        auth_dir = temporary / "authorization"
        auth_dir.mkdir()
        config["authorization_contract"]["directory"] = auth_dir.relative_to(ROOT).as_posix()
        config["authorization_contract"]["record_path"] = (
            auth_dir / "AUTHORIZATION.json"
        ).relative_to(ROOT).as_posix()
        config["authorization_contract"]["manifest_path"] = (
            auth_dir / "PACKAGE_MANIFEST.json"
        ).relative_to(ROOT).as_posix()
        if preparation is None:
            preparation = {
                "manifest": {"path": "prep/PACKAGE_MANIFEST.json", "bytes": 10, "sha256": "1" * 64},
                "config": {"path": "prep/CONFIG.json", "bytes": 20, "sha256": "2" * 64},
                "blender_identity": {
                    "path": self.config["blender_identity"]["path"],
                    "bytes": self.config["blender_identity"]["bytes"],
                    "sha256": self.config["blender_identity"]["sha256"],
                    "file_version": "5.1",
                    "product_version": "5.1",
                },
            }
        command = controller.build_command(config)
        reviewed = controller._expected_authorization_review(config, preparation)
        record = {
            "schema": "kira.avatar.r23_attempt04_reseal_v2_authorization.v1",
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_AUTHORIZATION",
            "authorization_id": "mock-authorization-01",
            "created_utc": "2026-08-03T00:00:00Z",
            "owner_decision_text": "Mock-only unit-test authorization record.",
            "execution_enabled": True,
            "owner_authorized": True,
            "one_run_only": True,
            "nonce": "mock_nonce_abcdefghijklmnopqrstuvwxyz0123",
            "reviewed": reviewed,
            "command_sha256": controller.canonical_sha256(command),
            "outputs": {
                "effective_directory": config["output_contract"]["effective_directory"],
                "execution_directory": config["output_contract"]["execution_directory"],
                "candidate_basename": config["output_contract"]["candidate_basename"],
                "build_evidence_basename": config["output_contract"]["build_evidence_basename"],
                "failure_evidence_basename": config["output_contract"]["failure_evidence_basename"],
            },
            "restrictions": config["authorization_contract"]["required_restrictions"],
        }
        record_path = auth_dir / "AUTHORIZATION.json"
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_AUTHORIZATION_PACKAGE",
            "created_utc": "2026-08-03T00:00:01Z",
            "authorization_id": record["authorization_id"],
            "artifacts": [
                {
                    "path": config["authorization_contract"]["record_path"],
                    "bytes": record_path.stat().st_size,
                    "sha256": sha256(record_path),
                }
            ],
        }
        (auth_dir / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return config, preparation, command

    def test_04_authorization_manifest_binds_exact_record_and_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            _, actual_preparation = self.controller.verify_preparation()
            config, preparation, command = self._synthetic_authorization(
                Path(raw), actual_preparation
            )
            authorization = self.controller.verify_authorization(config, preparation, command)
            with mock.patch.object(
                self.wrapper,
                "verify_blender_runtime",
                return_value=preparation["blender_identity"],
            ):
                wrapper_authorization = self.wrapper.bootstrap_verify_live_authorization(
                    config, command
                )
            self.assertEqual(wrapper_authorization, authorization)
            self.assertEqual(authorization["record"]["bytes"], (
                ROOT / config["authorization_contract"]["record_path"]
            ).stat().st_size)
            record_path = ROOT / config["authorization_contract"]["record_path"]
            with record_path.open("a", encoding="utf-8") as stream:
                stream.write(" ")
            with self.assertRaises(self.controller.ResealV2Error):
                self.controller.verify_authorization(config, preparation, command)
        self.assertIn('"authorization": authorization', self.controller_text)
        self.assertIn('"authorization_exact": post_authorization == authorization', self.controller_text)

    def test_05_lexical_reparse_junction_and_unsafe_segments_are_rejected_before_resolve(self) -> None:
        controller = self.controller
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            directory = Path(raw)
            child = directory / "child"
            child.mkdir()
            target_relative = (child / "file.txt").relative_to(ROOT).as_posix()
            (child / "file.txt").write_text("x", encoding="utf-8")
            original = controller.is_reparse

            def fake_reparse(path: Path) -> bool:
                return path == child or original(path)

            with mock.patch.object(controller, "is_reparse", side_effect=fake_reparse):
                with self.assertRaises(controller.ResealV2Error) as caught:
                    controller.lexical_project_path(
                        target_relative, require_exists=True, require_leaf_regular=True
                    )
            self.assertIn("reparse", str(caught.exception).lower())
        for unsafe in ("../escape", "a/../b", str(ROOT / "absolute")):
            with self.assertRaises(controller.ResealV2Error):
                controller.lexical_project_path(unsafe, require_exists=False)

    def test_06_basenames_and_exact_output_containment_reject_escape(self) -> None:
        controller = self.controller
        self.wrapper.validate_delegated_contract(controller, self.config)
        for bad in ("../candidate.blend", "sub/candidate.blend", "sub\\candidate.blend", ".."):
            with self.assertRaises(controller.ResealV2Error):
                controller.validate_basename(bad, "candidate")
        directory = ROOT / "RecoverySprint" / "mock_exact_output"
        child = controller.path_within_exact_directory(directory, "candidate.blend", "candidate")
        self.assertEqual(child.parent, directory)

    def _output_fixture(self, temporary: Path) -> tuple[dict[str, object], dict[str, object], Path]:
        controller = self.controller
        config = deepcopy(self.config)
        directory = temporary / "candidate_output"
        directory.mkdir()
        config["output_contract"]["effective_directory"] = directory.relative_to(ROOT).as_posix()
        config["output_contract"]["minimum_candidate_bytes"] = 1024
        provenance_base = {
            "schema": "kira.avatar.r23_attempt04_reseal_v2_provenance.v1",
            "preparation_manifest": {"sha256": "1" * 64},
            "reseal_v2_config": {"sha256": "2" * 64},
            "authorization_record": {"sha256": "3" * 64},
            "authorization_manifest": {"sha256": "4" * 64},
            "authorization_id": "mock",
            "authorization_nonce": "n" * 32,
            "command_sha256": "5" * 64,
            "reseal_v2_controller": {"sha256": "6" * 64},
            "reseal_v2_wrapper": {"sha256": "7" * 64},
            "delegated_repair_config": {"sha256": "8" * 64},
            "r19_source_blend": {"sha256": "9" * 64},
            "blender_identity": {"sha256": "a" * 64},
        }
        provenance = {
            **provenance_base,
            "canonical_sha256": controller.canonical_sha256(provenance_base),
        }
        candidate = directory / config["output_contract"]["candidate_basename"]
        candidate.write_bytes(b"BLENDER" + b"v" * 2041)
        build = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
            "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
            "candidate": {
                "path": f"{config['output_contract']['effective_directory']}/{candidate.name}",
                "bytes": candidate.stat().st_size,
                "sha256": sha256(candidate),
            },
            "reseal_v2_provenance": provenance,
        }
        (directory / config["output_contract"]["build_evidence_basename"]).write_text(
            json.dumps(build, indent=2) + "\n", encoding="utf-8"
        )
        return config, provenance, directory

    def test_07_realistic_success_output_validates_and_records_both_hashes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            config, provenance, _ = self._output_fixture(Path(raw))
            result = self.controller.validate_output_directory(config, provenance)
            self.assertEqual(result["classification"], "success")
            self.assertEqual(result["candidate"]["signature_ascii"], "BLENDER")
            self.assertEqual(len(result["candidate"]["sha256"]), 64)
            self.assertEqual(len(result["evidence"]["sha256"]), 64)

    def test_08_tiny_candidate_empty_evidence_extra_file_and_hash_tamper_fail(self) -> None:
        cases = ("tiny", "empty", "extra", "tamper")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
                    config, provenance, directory = self._output_fixture(Path(raw))
                    candidate = directory / config["output_contract"]["candidate_basename"]
                    build = directory / config["output_contract"]["build_evidence_basename"]
                    if case == "tiny":
                        candidate.write_bytes(b"BLENDERtiny")
                    elif case == "empty":
                        build.write_text("{}\n", encoding="utf-8")
                    elif case == "extra":
                        (directory / "unexpected.txt").write_text("x", encoding="utf-8")
                    elif case == "tamper":
                        with candidate.open("ab") as stream:
                            stream.write(b"tamper")
                    with self.assertRaises(self.controller.ResealV2Error):
                        self.controller.validate_output_directory(config, provenance)

    def test_09_failure_output_schema_and_provenance_are_required(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            config, provenance, directory = self._output_fixture(Path(raw))
            for entry in list(directory.iterdir()):
                entry.unlink()
            failure_path = directory / config["output_contract"]["failure_evidence_basename"]
            failure = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01_FAILURE",
                "status": "AUTHOR_NO_GO_NO_CANDIDATE_ACCEPTED",
                "candidate_file_exists": False,
                "reseal_v2_provenance": provenance,
            }
            failure_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            result = self.controller.validate_output_directory(config, provenance)
            self.assertEqual(result["classification"], "failure")
            failure["reseal_v2_provenance"] = {}
            failure_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(self.controller.ResealV2Error):
                self.controller.validate_output_directory(config, provenance)

    def test_10_provenance_injection_survives_runtime_clear_contract(self) -> None:
        self.assertIn('original_bind(repair_config)', self.wrapper_text)
        self.assertIn('RUNTIME["reseal_v2_provenance"] = provenance', self.wrapper_text)
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            path = Path(raw) / "evidence.json"
            path.write_text('{"schema_version": 1}\n', encoding="utf-8")
            provenance = {"schema": "mock", "canonical_sha256": "x" * 64}
            result = self.wrapper.inject_provenance_record(path, provenance)
            self.assertEqual(result["sha256"], sha256(path))
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["reseal_v2_provenance"],
                provenance,
            )

    def test_11_project_imports_occur_only_after_bootstrap_verification(self) -> None:
        controller_tree = ast.parse(self.controller_text)
        project_imports = [
            node for node in ast.walk(controller_tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            and any(
                (alias.name if isinstance(node, ast.Import) else (node.module or "")).startswith("tools")
                for alias in (node.names if isinstance(node, ast.Import) else [SimpleNamespace(name="")])
            )
        ]
        self.assertEqual(project_imports, [])
        verify_index = self.wrapper_text.index("config, bootstrap = bootstrap_verify_all_project_modules()")
        import_index = self.wrapper_text.index("topology_impl = load_verified_project_sources(config)")
        self.assertLess(verify_index, import_index)
        topology_name = "tools.blender_author_kira_r23_cc0_afes_attempt04_wrapper"
        with mock.patch.dict(sys.modules, {topology_name: SimpleNamespace()}, clear=False):
            with self.assertRaises(self.wrapper.BlenderResealV2Error):
                self.wrapper.assert_project_modules_not_preloaded(self.config)
        self.assertIn("verify_imported_dependency_files(config)", self.wrapper_text)
        self.assertIn('exec(compile(source, str(path), "exec", dont_inherit=True)', self.wrapper_text)
        self.assertNotIn("importlib.import_module", self.wrapper_text)

    def test_12_minimal_environment_removes_python_shadowing_variables(self) -> None:
        config = self.config
        preparation = {
            "manifest": {"sha256": "1" * 64},
            "config": {"sha256": "2" * 64},
        }
        authorization = {
            "record": {"sha256": "3" * 64},
            "manifest": {"sha256": "4" * 64},
            "nonce": "n" * 32,
        }
        pre = ROOT / "RecoverySprint" / "mock" / "PRE_RUN.json"
        with mock.patch.dict(
            os.environ,
            {"PYTHONPATH": "attacker", "PYTHONHOME": "attacker", "SYSTEMROOT": "C:\\Windows"},
            clear=False,
        ):
            environment = self.controller.minimal_child_environment(
                config, preparation, authorization, pre
            )
        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("PYTHONHOME", environment)
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")
        self.assertEqual(environment["KIRA_R23_RESEAL_V2_AUTHORIZATION_NONCE"], "n" * 32)

    def test_13_timeout_terminates_then_kills_only_exact_process(self) -> None:
        process = FakeTimeoutProcess()
        result = self.controller._bounded_wait(process, 0.01, 0.01)
        self.assertTrue(result["timed_out"])
        self.assertTrue(result["terminate_called"])
        self.assertTrue(result["kill_called"])
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.kill_calls, 1)
        self.assertEqual(result["returncode"], 7)

    def test_14_launch_exception_still_writes_append_only_pre_and_post(self) -> None:
        controller = self.controller
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            temporary = Path(raw)
            config = deepcopy(self.config)
            execution = temporary / "execution" / "attempt_04"
            effective = temporary / "author" / "attempt_04"
            configured = ROOT / config["output_contract"]["delegated_configured_directory"]
            outputs = {
                "configured": configured,
                "effective": effective,
                "execution": execution,
                "paths": {},
                "names": {},
            }
            preparation = {
                "manifest": {"path": "p", "bytes": 1, "sha256": "1" * 64},
                "config": {"path": "c", "bytes": 1, "sha256": "2" * 64},
            }
            authorization = {
                "record": {"path": "a", "bytes": 1, "sha256": "3" * 64},
                "manifest": {"path": "m", "bytes": 1, "sha256": "4" * 64},
                "authorization_id": "mock",
                "nonce": "n" * 32,
                "command_sha256": "5" * 64,
                "reviewed": {
                    "reseal_v2_controller": {"sha256": "6" * 64},
                    "reseal_v2_wrapper": {"sha256": "7" * 64},
                    "delegated_repair_config": {"sha256": "8" * 64},
                    "r19_source_blend": {"sha256": "9" * 64},
                    "blender_identity": {"sha256": "a" * 64},
                },
            }
            state = {"preparation": preparation, "authorization": authorization}
            with mock.patch.object(controller, "output_contract", return_value=outputs), \
                mock.patch.object(controller, "protected_state", return_value=(state, preparation, authorization)), \
                mock.patch.object(controller, "blender_processes", side_effect=[[], []]), \
                mock.patch.object(controller, "minimal_child_environment", return_value={}), \
                mock.patch.object(controller.subprocess, "Popen", side_effect=OSError("mock launch failure")):
                result = controller.execute_once(
                    config, preparation, authorization, ["mock-blender"]
                )
            self.assertEqual(result, 7)
            pre = execution / config["journal_contract"]["pre_run_basename"]
            post = execution / config["journal_contract"]["post_run_basename"]
            self.assertTrue(pre.is_file())
            self.assertTrue(post.is_file())
            record = json.loads(post.read_text(encoding="utf-8"))
            self.assertTrue(any("mock launch failure" in value for value in record["exceptions"]))
            with self.assertRaises(controller.ResealV2Error):
                controller.write_json_exclusive(post, {})

    def test_15_dry_controller_never_launches_and_live_outputs_remain_absent(self) -> None:
        output = io.StringIO()
        with mock.patch.object(self.controller, "blender_processes", return_value=[]), \
            mock.patch.object(self.controller.subprocess, "Popen") as popen, \
            redirect_stdout(output):
            self.assertEqual(self.controller.main([]), 0)
        popen.assert_not_called()
        record = json.loads(output.getvalue())
        self.assertFalse(record["execution_enabled"])
        self.assertFalse(record["authorization_presence"]["record_exists"])
        self.assertFalse(record["effective_output_exists"])
        self.assertFalse(record["execution_output_exists"])

    def test_16_pre_journal_failure_refuses_launch_but_still_writes_post(self) -> None:
        controller = self.controller
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as raw:
            temporary = Path(raw)
            config = deepcopy(self.config)
            execution = temporary / "execution" / "attempt_04"
            effective = temporary / "author" / "attempt_04"
            outputs = {
                "configured": ROOT / config["output_contract"]["delegated_configured_directory"],
                "effective": effective,
                "execution": execution,
                "paths": {},
                "names": {},
            }
            preparation = {
                "manifest": {"path": "p", "bytes": 1, "sha256": "1" * 64},
                "config": {"path": "c", "bytes": 1, "sha256": "2" * 64},
            }
            authorization = {
                "record": {"path": "a", "bytes": 1, "sha256": "3" * 64},
                "manifest": {"path": "m", "bytes": 1, "sha256": "4" * 64},
                "authorization_id": "mock",
                "nonce": "n" * 32,
                "command_sha256": "5" * 64,
                "reviewed": {
                    "reseal_v2_controller": {"sha256": "6" * 64},
                    "reseal_v2_wrapper": {"sha256": "7" * 64},
                    "delegated_repair_config": {"sha256": "8" * 64},
                    "r19_source_blend": {"sha256": "9" * 64},
                    "blender_identity": {"sha256": "a" * 64},
                },
            }
            state = {"preparation": preparation, "authorization": authorization}
            with mock.patch.object(controller, "output_contract", return_value=outputs), \
                mock.patch.object(controller, "protected_state", return_value=(state, preparation, authorization)), \
                mock.patch.object(controller, "blender_processes", side_effect=[[], []]), \
                mock.patch.object(controller, "minimal_child_environment", side_effect=OSError("mock PRE failure")), \
                mock.patch.object(controller.subprocess, "Popen") as popen:
                result = controller.execute_once(
                    config, preparation, authorization, ["mock-blender"]
                )
            self.assertEqual(result, 7)
            popen.assert_not_called()
            pre = execution / config["journal_contract"]["pre_run_basename"]
            post = execution / config["journal_contract"]["post_run_basename"]
            self.assertFalse(pre.exists())
            self.assertTrue(post.is_file())
            record = json.loads(post.read_text(encoding="utf-8"))
            self.assertFalse(record["pre_run_written"])
            self.assertTrue(any("mock PRE failure" in value for value in record["exceptions"]))


if __name__ == "__main__":
    unittest.main()
