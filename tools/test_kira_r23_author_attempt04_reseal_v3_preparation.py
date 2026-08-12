#!/usr/bin/env python3
"""No-Blender tests for the R23 Attempt04 reseal v3 preparation."""

from __future__ import annotations

import hashlib
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_PATH = ROOT / "Tools/kira_r23_author_attempt04_reseal_v3_invocation.py"
WRAPPER_PATH = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_v3_wrapper.py"
PREP = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v3_preparation"
)
CONFIG_PATH = PREP / "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V3_CONFIG.json"
MANIFEST_PATH = PREP / "PACKAGE_MANIFEST.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def import_controller() -> object:
    spec = importlib.util.spec_from_file_location("_reseal_v3_controller_test", CONTROLLER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_wrapper() -> object:
    fake_bpy = types.ModuleType("bpy")
    fake_bpy.data = types.SimpleNamespace(filepath="")
    fake_bpy.app = types.SimpleNamespace(version_string="5.1-test")
    prior = sys.modules.get("bpy")
    sys.modules["bpy"] = fake_bpy
    try:
        spec = importlib.util.spec_from_file_location("_reseal_v3_wrapper_test", WRAPPER_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if prior is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = prior


class ResealV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller = import_controller()
        cls.wrapper = import_wrapper()
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_01_prior_v2_is_byte_for_byte_preserved(self) -> None:
        section = self.config["preserved_append_only_evidence"][0]
        directory = ROOT / section["directory"]
        self.assertEqual(sorted(path.name for path in directory.iterdir()), sorted(section["files"]))
        for name, record in section["files"].items():
            path = directory / name
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(digest(path), record["sha256"])

    def test_02_author_config_and_repair_overlay_are_distinct_and_exact(self) -> None:
        handoff = self.controller.verify_author_handoff(self.config)
        self.assertNotEqual(
            handoff["sealed_author_config"], handoff["repair_overlay_config"]
        )
        self.assertEqual(
            handoff["sealed_author_schema"],
            "kira.avatar.r23_cc0_afes_author_attempt01.v1",
        )
        self.assertEqual(
            handoff["repair_overlay_schema"],
            "kira.avatar.r23_author_attempt04_repair.v1",
        )
        artifacts = self.config["bound_artifacts"]
        for label in ("sealed_author_config", "repair_overlay_config"):
            self.controller.verify_binding(artifacts[label], label)

    def test_02a_author_runtime_inputs_are_all_locked_and_overlay_is_current(self) -> None:
        handoff = self.config["handoff_contract"]
        author = json.loads(
            (ROOT / handoff["sealed_author_config_argument"]).read_text(encoding="utf-8")
        )
        overlay = json.loads(
            (ROOT / handoff["repair_overlay_config_argument"]).read_text(encoding="utf-8")
        )
        original_overlay = json.loads(
            (
                ROOT
                / self.config["bound_artifacts"]["original_repair_overlay"]["path"]
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(overlay["repair_contract"], original_overlay["repair_contract"])
        self.assertEqual(
            overlay["nominal_source_baseline"],
            original_overlay["nominal_source_baseline"],
        )
        v3_by_path = {
            row["path"]: row for row in self.config["bound_artifacts"].values()
        }
        for label, row in author["inputs"].items():
            with self.subTest(author_input=label):
                self.assertIn(row["path"], v3_by_path)
                self.assertEqual(v3_by_path[row["path"]], row)
                self.controller.verify_binding(row, f"author/{label}")
        for label, row in overlay["bound_artifacts"].items():
            with self.subTest(overlay_binding=label):
                self.assertIn(row["path"], v3_by_path)
                self.assertEqual(v3_by_path[row["path"]], row)
                self.controller.verify_binding(row, f"overlay/{label}")

    def test_03_command_tail_passes_only_attempt01_author_config(self) -> None:
        command = self.controller.build_command(self.config)
        handoff = self.config["handoff_contract"]
        self.assertEqual(
            command[-3:],
            ["--config", handoff["sealed_author_config_argument"], "--execute-authoring"],
        )
        self.assertNotIn(handoff["repair_overlay_config_argument"], command)
        self.assertEqual(command.count("--python"), 1)
        self.assertNotIn("--python-expr", command)
        self.assertEqual(command.count("--"), 1)

    def test_04_complete_argv_rejects_every_prefix_or_tail_change(self) -> None:
        command = self.controller.build_command(self.config)
        self.assertEqual(
            self.controller.validate_complete_child_argv(command, command), command
        )
        mutations = []
        mutations.append(command[:1] + ["--python", "evil.py"] + command[1:])
        mutations.append(command[:1] + ["--python-expr", "raise Exception()"] + command[1:])
        mutations.append(command[:8] + ["--python", "evil.py"] + command[8:])
        mutations.append(command[:4] + [str(ROOT / "wrong.blend")] + command[5:])
        mutations.append(command[:8] + [str(ROOT / "wrong.py")] + command[9:])
        mutations.append(["wrong-blender.exe", *command[1:]])
        mutations.append(command[:5] + ["--python", command[7], "--python-exit-code", "7"] + command[9:])
        mutations.append(command[:9] + ["--", "--"] + command[10:])
        mutations.append(command + ["--extra"])
        mutations.append(command[:-2] + ["different.json", command[-1]])
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(self.controller.ResealV3Error):
                    self.controller.validate_complete_child_argv(mutation, command)

    def test_05_wrapper_checks_the_same_complete_actual_argv(self) -> None:
        command = self.controller.build_command(self.config)
        expected = self.wrapper.expected_command(self.config)
        self.assertEqual(command, expected)
        self.wrapper.validate_complete_argv(command, expected)
        for extra in (
            ["--python", "evil.py"],
            ["--python-expr", "evil()"],
            ["--"],
        ):
            with self.assertRaises(self.wrapper.BlenderResealV3Error):
                self.wrapper.validate_complete_argv(
                    command[:1] + extra + command[1:], expected
                )

    def test_06_runtime_import_order_is_a_bound_exact_set(self) -> None:
        closure = self.config["runtime_dependency_closure"]
        self.assertEqual(
            set(closure["project_local_modules"]),
            set(closure["verified_source_import_order"]),
        )
        bound_paths = {
            row["path"] for row in self.config["bound_artifacts"].values()
        }
        self.assertTrue(set(closure["project_local_modules"]).issubset(bound_paths))
        wrapper_text = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn("compile(source, module.__file__", wrapper_text)
        self.assertIn("project modules preloaded before verification", wrapper_text)

    def test_06a_instrumented_handoff_preserves_author_argv_and_sets_only_overlay(self) -> None:
        handoff = self.config["handoff_contract"]
        author = json.loads((ROOT / handoff["sealed_author_config_argument"]).read_text(encoding="utf-8"))
        overlay = json.loads((ROOT / handoff["repair_overlay_config_argument"]).read_text(encoding="utf-8"))
        original_overlay = json.loads(
            (
                ROOT
                / self.config["bound_artifacts"]["original_repair_overlay"]["path"]
            ).read_text(encoding="utf-8")
        )
        command = self.controller.build_command(self.config)
        topology = types.SimpleNamespace(REPAIR_CONFIG=None)
        before = list(command)
        record = self.wrapper.apply_config_handoff(
            topology, self.config, command, author, overlay, original_overlay
        )
        self.assertEqual(command, before)
        self.assertEqual(
            topology.REPAIR_CONFIG.as_posix(), handoff["repair_overlay_config_argument"]
        )
        self.assertEqual(record["author_schema"], handoff["sealed_author_schema"])
        self.assertTrue(record["worker_argv_unchanged"])
        bad_author = dict(author)
        bad_author["schema"] = overlay["schema"]
        with self.assertRaises(self.wrapper.BlenderResealV3Error):
            self.wrapper.apply_config_handoff(
                types.SimpleNamespace(REPAIR_CONFIG=None),
                self.config,
                command,
                bad_author,
                overlay,
                original_overlay,
            )

    def test_06b_repair_overlay_covers_every_topology_runtime_consumer_before_mutation(self) -> None:
        topology_path = ROOT / "Tools/blender_author_kira_r23_cc0_afes_attempt04_wrapper.py"
        tree = ast.parse(topology_path.read_text(encoding="utf-8"))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        def constant_slice(node: ast.AST) -> str | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            return None

        consumed: set[str] = set()
        for function_name, variable in (
            ("verify_repair_config", "config"),
            ("capture_source_baseline", "repair_config"),
        ):
            for node in ast.walk(functions[function_name]):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == variable
                ):
                    key = constant_slice(node.slice)
                    if key:
                        consumed.add(key)
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == variable
                    and node.func.attr == "get"
                    and node.args
                ):
                    key = constant_slice(node.args[0])
                    if key:
                        consumed.add(key)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            outer_key = constant_slice(node.slice)
            inner = node.value
            if (
                outer_key
                and isinstance(inner, ast.Subscript)
                and isinstance(inner.value, ast.Name)
                and inner.value.id == "RUNTIME"
                and constant_slice(inner.slice) == "repair_config"
            ):
                consumed.add(outer_key)

        expected = {
            "schema",
            "status",
            "bound_artifacts",
            "preserved_append_only_evidence",
            "repair_contract",
            "nominal_source_baseline",
            "nominal_corrected_final",
            "clinical_semantics_contract",
        }
        self.assertEqual(consumed, expected)
        overlay = json.loads(
            (
                ROOT
                / self.config["handoff_contract"]["repair_overlay_config_argument"]
            ).read_text(encoding="utf-8")
        )
        original = json.loads(
            (
                ROOT
                / self.config["bound_artifacts"]["original_repair_overlay"]["path"]
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(consumed.issubset(overlay))
        for key in (
            "repair_contract",
            "nominal_source_baseline",
            "nominal_corrected_final",
            "clinical_semantics_contract",
        ):
            self.assertEqual(overlay[key], original[key])
        clinical_labels = set(
            overlay["clinical_semantics_contract"]["bound_source_labels"]
        )
        self.assertTrue(clinical_labels)
        self.assertTrue(clinical_labels.issubset(overlay["bound_artifacts"]))
        for label in clinical_labels:
            binding = overlay["bound_artifacts"][label]
            path = ROOT / binding["path"]
            self.assertEqual(path.stat().st_size, binding["bytes"])
            self.assertEqual(digest(path), binding["sha256"])

    def test_07_ntfs_unsafe_basenames_are_rejected(self) -> None:
        valid = [
            "AUTHORIZATION_CLAIM.json",
            "PRE_RUN.json",
            "blender_stdout.log",
            "kira_r23_cc0_afes_core_transfer_attempt_04.blend",
        ]
        for value in valid:
            self.assertEqual(self.controller.validate_windows_basename(value), value)
        invalid = [
            "", ".", "..", "x:y", "x::$DATA", "bad ", "bad.", "a/b",
            "a\\b", "bad?name", "bad*name", "bad|name", "bad<name",
            "bad>name", 'bad"name', "CON", "con.txt", "NUL.json", "COM0",
            "COM1.txt", "LPT9.log", "CONIN$", "CONOUT$.txt", "\x01bad",
            "évidence.json", "a" * 129,
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(self.controller.ResealV3Error):
                    self.controller.validate_windows_basename(value)

    @unittest.skipUnless(os.name == "nt", "Win32 lock semantics")
    def test_08_no_follow_handle_denies_write_replace_delete_until_close(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            target = directory / "locked.json"
            replacement = directory / "replacement.json"
            target.write_bytes(b'{"stable":true}')
            replacement.write_bytes(b'{"stable":false}')
            handle = self.controller.Win32LockedHandle.open_existing(target)
            try:
                self.assertEqual(handle.read_bytes(), b'{"stable":true}')
                with self.assertRaises(OSError):
                    target.write_bytes(b"changed")
                with self.assertRaises(OSError):
                    os.replace(replacement, target)
                with self.assertRaises(OSError):
                    target.unlink()
            finally:
                handle.close()
            target.write_bytes(b"changed")
            self.assertEqual(target.read_bytes(), b"changed")

    @unittest.skipUnless(os.name == "nt", "Win32 same-handle parsing")
    def test_09_json_is_parsed_from_the_locked_handle_not_reopened_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            target = Path(temporary) / "record.json"
            target.write_text('{"value":7}', encoding="utf-8")
            handle = self.controller.Win32LockedHandle.open_existing(target)
            try:
                with mock.patch.object(Path, "open", side_effect=AssertionError("reopen")), mock.patch.object(
                    Path, "read_text", side_effect=AssertionError("reopen")
                ):
                    value = self.controller.json_from_locked(handle, "test")
                self.assertEqual(value, {"value": 7})
            finally:
                handle.close()

    @unittest.skipUnless(os.name == "nt", "Win32 duplicate log-handle refresh")
    def test_09aa_read_refreshes_size_after_duplicate_handle_write(self) -> None:
        import msvcrt

        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            target = Path(temporary) / "child.log"
            handle = self.controller.Win32LockedHandle.create_new(target)
            duplicate = handle.duplicate_raw(inheritable=False)
            try:
                with os.fdopen(
                    msvcrt.open_osfhandle(duplicate, os.O_WRONLY), "wb"
                ) as stream:
                    stream.write(b"child-log-evidence")
                    stream.flush()
                duplicate = None
                self.assertEqual(handle.read_bytes(), b"child-log-evidence")
                self.assertEqual(handle.size, len(b"child-log-evidence"))
            finally:
                if duplicate is not None:
                    self.controller._kernel32().CloseHandle(duplicate)
                handle.close()

    @unittest.skipUnless(os.name == "nt", "Win32 STARTUPINFOEX handle inheritance")
    def test_09a_exact_locked_handle_is_inherited_by_a_tiny_non_blender_child(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            target = Path(temporary) / "lease.bin"
            target.write_bytes(b"v3-handle-lease")
            handle = self.controller.Win32LockedHandle.open_existing(
                target, inheritable=True
            )
            script = (
                "import ctypes,sys; from ctypes import wintypes; "
                "k=ctypes.WinDLL('kernel32',use_last_error=True); "
                "k.SetFilePointerEx.argtypes=[wintypes.HANDLE,ctypes.c_longlong,ctypes.POINTER(ctypes.c_longlong),wintypes.DWORD]; "
                "k.ReadFile.argtypes=[wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID]; "
                "h=int(sys.argv[1]); p=ctypes.c_longlong(); "
                "assert k.SetFilePointerEx(h,0,ctypes.byref(p),0); "
                "b=ctypes.create_string_buffer(15); n=wintypes.DWORD(); "
                "assert k.ReadFile(h,b,15,ctypes.byref(n),None); "
                "sys.stdout.buffer.write(b.raw[:n.value])"
            )
            startup = subprocess.STARTUPINFO()
            startup.lpAttributeList = {"handle_list": [handle.handle]}
            try:
                process = subprocess.Popen(
                    [sys.executable, "-c", script, str(handle.handle)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    startupinfo=startup,
                )
                handle.set_inheritable(False)
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, stderr.decode(errors="replace"))
                self.assertEqual(stdout, b"v3-handle-lease")
            finally:
                handle.close()

    def test_09b_direct_wrapper_without_controller_lease_fails_closed(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(self.wrapper.BlenderResealV3Error):
                self.wrapper._lease_json()

    def test_10_claim_binds_nonce_processes_and_complete_command(self) -> None:
        command = self.controller.build_command(self.config)
        authorization = {
            "authorization_id": "mock-id",
            "nonce": "n" * 32,
            "record": {"sha256": "1" * 64},
            "manifest": {"sha256": "2" * 64},
        }
        claim = self.controller.build_claim(
            self.config,
            authorization,
            command,
            controller_pid=111,
            child_pid=222,
            child_created_utc="2026-08-03T00:00:00Z",
        )
        self.assertEqual(claim["authorization_nonce"], "n" * 32)
        self.assertEqual(claim["controller_pid"], 111)
        self.assertEqual(claim["child_pid"], 222)
        self.assertEqual(claim["command"], command)
        self.assertEqual(claim["command_sha256"], self.controller.canonical_sha256(command))
        self.assertEqual(claim["atomic_claim"]["method"], "CREATE_NEW_NO_FOLLOW_HELD_HANDLE")

    @unittest.skipUnless(os.name == "nt", "Win32 locked authorization")
    def test_10a_authorization_manifest_and_record_are_parsed_from_locked_handles(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            config = copy.deepcopy(self.config)
            auth_dir = Path(temporary) / "authorization"
            auth_dir.mkdir()
            relative_dir = auth_dir.relative_to(ROOT).as_posix()
            record_path = auth_dir / "AUTHORIZATION.json"
            manifest_path = auth_dir / "PACKAGE_MANIFEST.json"
            contract = config["authorization_contract"]
            contract["directory"] = relative_dir
            contract["record_path"] = record_path.relative_to(ROOT).as_posix()
            contract["manifest_path"] = manifest_path.relative_to(ROOT).as_posix()
            contract["reviewed_binding_labels"] = []
            command = self.controller.build_command(config)
            locked_records = {
                "blender_executable": {
                    "path": config["blender_identity"]["path"],
                    "bytes": config["blender_identity"]["bytes"],
                    "sha256": config["blender_identity"]["sha256"],
                    "file_identity": {"unit_test": True},
                }
            }
            reviewed = self.controller.expected_authorization_review(
                config, locked_records, command
            )
            record = {
                "schema": contract["record_schema"],
                "authorized": True,
                "one_run_only": True,
                "authorization_id": "unit-test-auth",
                "nonce": "n" * 32,
                "owner_decision_text": "Unit-test authorization only.",
                "reviewed": reviewed,
                "restrictions": contract["required_restrictions"],
                "command_sha256": self.controller.canonical_sha256(command),
            }
            record_path.write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            manifest = {
                "schema": contract["manifest_schema"],
                "authorization_id": "unit-test-auth",
                "record": {
                    "path": record_path.relative_to(ROOT).as_posix(),
                    "bytes": record_path.stat().st_size,
                    "sha256": digest(record_path),
                },
            }
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(Path, "read_text", side_effect=AssertionError("path reopen")), mock.patch.object(
                Path, "open", side_effect=AssertionError("path reopen")
            ):
                authorization, handles = self.controller.verify_authorization_locked(
                    config, locked_records, command
                )
            try:
                self.assertEqual(authorization["nonce"], "n" * 32)
                self.assertEqual(authorization["record"]["sha256"], digest(record_path))
                with self.assertRaises(OSError):
                    record_path.write_text("tamper", encoding="utf-8")
            finally:
                self.controller.close_handles(handles.values())

    @unittest.skipUnless(os.name == "nt", "Win32 immutable authorization review")
    def test_10b_read_only_review_acquires_every_reviewed_label_without_side_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            bound = directory / "bound.bin"
            bound.write_bytes(b"immutable-review-input")
            fake_blender = directory / "blender.exe"
            fake_blender.write_bytes(b"mock-blender-executable")
            temp_config_path = directory / "CONFIG.json"
            temp_manifest_path = directory / "PACKAGE_MANIFEST.json"
            config = copy.deepcopy(self.config)
            shared_binding = {
                "path": bound.relative_to(ROOT).as_posix(),
                "bytes": bound.stat().st_size,
                "sha256": digest(bound),
            }
            config["bound_artifacts"] = {
                label: dict(shared_binding)
                for label in config["bound_artifacts"]
            }
            config["blender_identity"] = {
                **config["blender_identity"],
                "path": str(fake_blender),
                "bytes": fake_blender.stat().st_size,
                "sha256": digest(fake_blender),
            }
            temp_config_path.write_text(
                json.dumps(config, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temp_manifest_path.write_text(
                json.dumps(
                    {
                        "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_PREPARATION",
                        "artifacts": [
                            {
                                "path": temp_config_path.relative_to(ROOT).as_posix(),
                                "bytes": temp_config_path.stat().st_size,
                                "sha256": digest(temp_config_path),
                            }
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            before = sorted(path.name for path in directory.iterdir())
            with mock.patch.object(
                self.controller, "CONFIG_PATH", temp_config_path
            ), mock.patch.object(
                self.controller, "MANIFEST_PATH", temp_manifest_path
            ), mock.patch.object(
                self.controller.subprocess, "Popen"
            ) as popen:
                command = self.controller.build_command(config)
                review = self.controller.read_only_authorization_review(
                    config, command
                )
            popen.assert_not_called()
            self.assertEqual(before, sorted(path.name for path in directory.iterdir()))
            reviewed = review["reviewed"]
            self.assertEqual(
                set(config["authorization_contract"]["reviewed_binding_labels"]),
                set(reviewed) - {
                    "blender_identity",
                    "blender_executable",
                    "handoff",
                    "command",
                    "command_sha256",
                    "output_contract",
                },
            )
            self.assertFalse(review["authorization_created"])
            self.assertFalse(review["journal_created"])
            self.assertFalse(review["output_created"])
            self.assertFalse(review["process_started"])
            self.assertEqual(
                review["reviewed_sha256"],
                self.controller.canonical_sha256(reviewed),
            )

    def test_11_post_binds_final_exact_pre_and_claim_bytes(self) -> None:
        pre_bytes = b'{"final":"pre"}\n'
        claim_bytes = b'{"final":"claim"}\n'
        post = self.controller.build_post_run(
            self.config,
            pre_bytes=pre_bytes,
            claim_bytes=claim_bytes,
            stdout_record={"sha256": "3" * 64},
            stderr_record={"sha256": "4" * 64},
            child_pid=222,
            wait={"returncode": 0},
            output_validation={"classification": "success"},
            exceptions=[],
        )
        self.assertEqual(post["final_pre_run"]["bytes"], len(pre_bytes))
        self.assertEqual(
            post["final_pre_run"]["sha256"], hashlib.sha256(pre_bytes).hexdigest()
        )
        self.assertEqual(
            post["authorization_claim"]["sha256"],
            hashlib.sha256(claim_bytes).hexdigest(),
        )
        self.assertEqual(
            post["journal_exact_closure"]["expected_entries"],
            sorted(self.config["journal_contract"]["exact_entries"]),
        )

    def test_11a_post_never_claims_final_pass_before_controller_rescans(self) -> None:
        post = self.controller.build_post_run(
            self.config,
            pre_bytes=b'{"pre":true}\n',
            claim_bytes=b'{"claim":true}\n',
            stdout_record={"sha256": "1" * 64},
            stderr_record={"sha256": "2" * 64},
            child_pid=123,
            wait={"returncode": 0},
            output_validation={
                "classification": "success",
                "final_closure_before_post": {
                    "exact_after_child_exit": True
                },
            },
            exceptions=[],
            journal_observed_before_post_write=sorted(
                self.config["journal_contract"]["exact_entries"]
            ),
        )
        self.assertEqual(
            post["acceptance_status"],
            "PRE_POST_GATES_PASSED_PENDING_FINAL_CONTROLLER_RESCAN",
        )
        self.assertNotEqual(post["acceptance_status"], "PASSED")

    def test_11b_every_unexpected_pre_post_gate_has_nonempty_failed_fallback(self) -> None:
        for gate in (
            "claim_read",
            "pre_read",
            "stdout_read",
            "stderr_read",
            "output_rescan",
            "journal_rescan",
            "normal_post_assembly",
        ):
            with self.subTest(gate=gate):
                try:
                    raise RuntimeError(f"injected:{gate}")
                except RuntimeError as error:
                    post = self.controller.build_emergency_post_run(
                        command=["mock-blender"],
                        child_pid=123,
                        wait={"returncode": None, "timed_out": False},
                        output_validation=None,
                        exceptions=[f"injected:{gate}"],
                        finalizer_error=error,
                    )
                encoded = self.controller.json_line_bytes(post)
                self.assertGreater(len(encoded), 0)
                self.assertEqual(post["acceptance_status"], "FAILED")
                self.assertTrue(post["emergency_single_write_finalizer"]["used"])
                self.assertNotEqual(post["acceptance_status"], "PASSED")

    def test_12_journal_exact_closure_rejects_extra_or_missing_entry(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            for name in self.config["journal_contract"]["exact_entries"]:
                (directory / name).touch()
            self.assertEqual(
                self.controller.verify_journal_closure(self.config, directory),
                sorted(self.config["journal_contract"]["exact_entries"]),
            )
            (directory / "EXTRA.json").touch()
            with self.assertRaises(self.controller.ResealV3Error):
                self.controller.verify_journal_closure(self.config, directory)

    def test_12aa_journal_drift_is_captured_in_nonempty_failed_post(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            for name in self.config["journal_contract"]["exact_entries"]:
                (directory / name).touch()
            (directory / "EXTRA.json").touch()
            captured_exceptions: list[str] = []
            observed = self.controller.capture_journal_closure_for_post(
                self.config, directory, captured_exceptions
            )
            self.assertIn("EXTRA.json", observed)
            self.assertTrue(captured_exceptions)
            post = self.controller.build_post_run(
                self.config,
                pre_bytes=b'{"pre":true}\n',
                claim_bytes=b'{"claim":true}\n',
                stdout_record={"sha256": "1" * 64},
                stderr_record={"sha256": "2" * 64},
                child_pid=123,
                wait={"returncode": 0},
                output_validation={
                    "classification": "success",
                    "final_closure_before_post": {
                        "exact_after_child_exit": True
                    },
                },
                exceptions=captured_exceptions,
                journal_observed_before_post_write=observed,
            )
            post_bytes = self.controller.json_line_bytes(post)
            self.assertGreater(len(post_bytes), 0)
            self.assertEqual(post["acceptance_status"], "FAILED")
            self.assertFalse(
                post["journal_exact_closure"]["exact_before_post_write"]
            )
            self.assertIn("pre_post_journal_rescan", post["exceptions"][0])

    @unittest.skipUnless(os.name == "nt", "Win32 atomic journal claim")
    def test_12a_execution_directory_atomically_consumes_the_one_run(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            config = copy.deepcopy(self.config)
            target = Path(temporary) / "attempt_04"
            config["output_contract"]["execution_directory"] = target.relative_to(ROOT).as_posix()
            directory_handle, leaves = self.controller.create_execution_journal(config)
            try:
                self.assertEqual(
                    sorted(path.name for path in target.iterdir()),
                    sorted(config["journal_contract"]["exact_entries"]),
                )
                with self.assertRaises(self.controller.ResealV3Error):
                    self.controller.create_execution_journal(config)
            finally:
                self.controller.close_handles(leaves.values())
                directory_handle.close()

    def test_13_authorization_output_and_execution_are_absent(self) -> None:
        self.assertEqual(
            self.controller.authorization_presence(self.config),
            {"directory": False, "record": False, "manifest": False},
        )
        output = self.config["output_contract"]
        self.assertFalse((ROOT / output["effective_directory"]).exists())
        self.assertFalse((ROOT / output["execution_directory"]).exists())
        self.assertFalse(
            (ROOT / self.config["authorization_contract"]["directory"]).exists()
        )

    def test_14_dry_main_never_calls_popen_or_creates_journal(self) -> None:
        fake_preparation = {"manifest_artifacts": {}, "bound_artifacts": {}}
        with mock.patch.object(
            self.controller, "verify_preparation", return_value=(self.config, fake_preparation)
        ), mock.patch.object(
            self.controller, "build_command", return_value=["mock-blender"]
        ), mock.patch.object(
            self.controller.subprocess, "Popen"
        ) as popen:
            result = self.controller.main([])
        self.assertEqual(result, 0)
        popen.assert_not_called()

    def test_15_source_contains_parent_child_output_lock_handshake(self) -> None:
        controller_text = CONTROLLER_PATH.read_text(encoding="utf-8")
        wrapper_text = WRAPPER_PATH.read_text(encoding="utf-8")
        for token in (
            "KIRA_R23_RESEAL_V3_OUTPUT_LOCKED_EVENT_HANDLE",
            "KIRA_R23_RESEAL_V3_OUTPUT_VALIDATED_EVENT_HANDLE",
            "KIRA_R23_RESEAL_V3_OUTPUT_HANDLE_PIPE_WRITE",
            "validate_transferred_output_handles",
            "read_output_handle_transfer",
            "SetEvent(output validated)",
        ):
            self.assertIn(token, controller_text)
        for token in (
            "_inject_provenance_and_hold_outputs",
            "_transfer_output_handles_to_parent",
            "DuplicateHandle(output",
            "SetEvent(output locked)",
            "KIRA_R23_RESEAL_V3_OUTPUT_VALIDATED_EVENT_HANDLE",
        ):
            self.assertIn(token, wrapper_text)

    @unittest.skipUnless(os.name == "nt", "Win32 candidate/evidence binding")
    def test_15a_child_and_parent_reject_mismatched_candidate_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary) / "output"
            directory.mkdir()
            config = copy.deepcopy(self.config)
            contract = config["output_contract"]
            contract["effective_directory"] = directory.relative_to(ROOT).as_posix()
            candidate_path = directory / contract["candidate_basename"]
            evidence_path = directory / contract["build_evidence_basename"]
            candidate_bytes = b"BLENDER" + (b"x" * int(contract["minimum_candidate_bytes"]))
            candidate_path.write_bytes(candidate_bytes)
            base_payload = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
                "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
                "candidate": {
                    "path": "WRONG.blend",
                    "bytes": 1,
                    "sha256": "0" * 64,
                    "inactive": True,
                    "unassigned": True,
                    "unpublished": True,
                    "runtime_eligible": False,
                    "owner_approved": False,
                },
            }
            evidence_path.write_text(
                json.dumps(base_payload, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaises(self.wrapper.BlenderResealV3Error):
                self.wrapper._inject_provenance_and_hold_outputs(
                    config, {"test": "provenance"}, 0
                )
            unchanged = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertNotIn("reseal_v3_provenance", unchanged)

            provenance = {"test": "provenance"}
            parent_payload = copy.deepcopy(base_payload)
            parent_payload["reseal_v3_provenance"] = provenance
            evidence_path.write_text(
                json.dumps(parent_payload, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaises(self.controller.ResealV3Error):
                self.controller.validate_output_directory(
                    config, provenance, hold=False
                )

            parent_payload["candidate"].update(
                {
                    "path": candidate_path.relative_to(ROOT).as_posix(),
                    "bytes": len(candidate_bytes),
                    "sha256": hashlib.sha256(candidate_bytes).hexdigest(),
                }
            )
            evidence_path.write_text(
                json.dumps(parent_payload, indent=2) + "\n", encoding="utf-8"
            )
            accepted = self.controller.validate_output_directory(
                config, provenance, hold=False
            )
            self.assertEqual(accepted["classification"], "success")

    @unittest.skipUnless(os.name == "nt", "Win32 gap-free output handle transfer")
    def test_15b_concurrent_child_writable_lock_is_duplicated_and_held_by_parent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary) / "output"
            directory.mkdir()
            config = copy.deepcopy(self.config)
            contract = config["output_contract"]
            contract["effective_directory"] = directory.relative_to(ROOT).as_posix()
            candidate_path = directory / contract["candidate_basename"]
            evidence_path = directory / contract["build_evidence_basename"]
            candidate_bytes = b"BLENDER" + (b"y" * int(contract["minimum_candidate_bytes"]))
            candidate_path.write_bytes(candidate_bytes)
            provenance = {"test": "same-file-object-transfer"}
            evidence = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
                "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
                "candidate": {
                    "path": candidate_path.relative_to(ROOT).as_posix(),
                    "bytes": len(candidate_bytes),
                    "sha256": hashlib.sha256(candidate_bytes).hexdigest(),
                    "inactive": True,
                    "unassigned": True,
                    "unpublished": True,
                    "runtime_eligible": False,
                    "owner_approved": False,
                },
                "reseal_v3_provenance": provenance,
            }
            evidence_path.write_text(
                json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
            )
            child_script = r'''
import ctypes, json, os, sys
from ctypes import wintypes
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
k.CreateFileW.restype = wintypes.HANDLE
k.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
k.OpenProcess.restype = wintypes.HANDLE
k.GetCurrentProcess.restype = wintypes.HANDLE
k.DuplicateHandle.argtypes = [wintypes.HANDLE,wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
k.DuplicateHandle.restype = wintypes.BOOL
k.CloseHandle.argtypes = [wintypes.HANDLE]
GENERIC_READ=0x80000000; GENERIC_WRITE=0x40000000; FILE_SHARE_READ=1
OPEN_EXISTING=3; NORMAL=0x80; OPEN_REPARSE=0x00200000; BACKUP=0x02000000
PROCESS_DUP_HANDLE=0x40; SAME=2
parent = k.OpenProcess(PROCESS_DUP_HANDLE, False, int(sys.argv[1]))
paths = {"directory": (sys.argv[2], GENERIC_READ, OPEN_REPARSE|BACKUP), "BUILD_EVIDENCE.json": (sys.argv[3], GENERIC_READ|GENERIC_WRITE, OPEN_REPARSE|NORMAL), sys.argv[5]: (sys.argv[4], GENERIC_READ, OPEN_REPARSE|NORMAL)}
local = {}; remote = {}
for label,(path,access,flags) in paths.items():
    handle = k.CreateFileW(path, access, FILE_SHARE_READ, None, OPEN_EXISTING, flags, None)
    assert int(handle) != int(ctypes.c_void_p(-1).value), (label, ctypes.get_last_error())
    local[label] = int(handle)
    target = wintypes.HANDLE()
    assert k.DuplicateHandle(k.GetCurrentProcess(), handle, parent, ctypes.byref(target), 0, False, SAME)
    remote[label] = int(target.value)
print(json.dumps({"schema":"kira.avatar.r23_attempt04_reseal_v3_output_handle_transfer.v1","classification":"success","handles":remote}), flush=True)
sys.stdin.buffer.read(1)
for handle in local.values(): k.CloseHandle(handle)
k.CloseHandle(parent)
'''
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    child_script,
                    str(os.getpid()),
                    str(directory),
                    str(evidence_path),
                    str(candidate_path),
                    contract["candidate_basename"],
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            held: list[object] = []
            try:
                assert process.stdout is not None
                line = process.stdout.readline()
                if not line:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    assert process.stderr is not None
                    self.fail(process.stderr.read().decode(errors="replace"))
                transfer = json.loads(line.decode("utf-8"))
                # This is the exact share conflict that broke the prior design.
                with self.assertRaises(self.controller.ResealV3Error):
                    self.controller.Win32LockedHandle.open_existing(evidence_path)
                validation, held = self.controller.validate_transferred_output_handles(
                    config, provenance, transfer, hold=True
                )
                self.assertEqual(validation["classification"], "success")
                self.assertTrue(
                    validation["handle_transfer"]["no_close_reopen_gap"]
                )
                assert process.stdin is not None
                process.stdin.write(b"x")
                process.stdin.close()
                self.assertEqual(process.wait(timeout=15), 0)
                # The duplicated parent-side file object retains the original
                # deny-write/delete share reservation after child exit.
                with self.assertRaises(OSError):
                    evidence_path.write_text("tamper", encoding="utf-8")
                final_closure = self.controller.rescan_transferred_output_closure(
                    config, validation, held
                )
                self.assertTrue(final_closure["exact_after_child_exit"])
                extra = directory / "EXTRA_AFTER_TRANSFER.txt"
                extra.write_text("must fail closure", encoding="utf-8")
                with self.assertRaises(self.controller.ResealV3Error):
                    self.controller.rescan_transferred_output_closure(
                        config, validation, held
                    )
                captured_exceptions: list[str] = []
                captured = self.controller.capture_final_output_closure_for_post(
                    config, validation, held, captured_exceptions
                )
                self.assertFalse(captured["exact_after_child_exit"])
                self.assertEqual(
                    captured["acceptance"],
                    "FAIL_OUTPUT_CLOSURE_DRIFT_POST_MUST_STILL_BE_WRITTEN",
                )
                self.assertTrue(captured_exceptions)
                post = self.controller.build_post_run(
                    config,
                    pre_bytes=b'{"pre":true}\n',
                    claim_bytes=b'{"claim":true}\n',
                    stdout_record={"sha256": "1" * 64},
                    stderr_record={"sha256": "2" * 64},
                    child_pid=123,
                    wait={"returncode": 0},
                    output_validation={
                        **validation,
                        "final_closure_before_post": captured,
                    },
                    exceptions=captured_exceptions,
                )
                post_bytes = self.controller.json_line_bytes(post)
                self.assertGreater(len(post_bytes), 0)
                self.assertFalse(
                    post["output_validation"]["final_closure_before_post"][
                        "exact_after_child_exit"
                    ]
                )
                self.assertIn("final_output_rescan", post["exceptions"][0])
                self.assertEqual(post["acceptance_status"], "FAILED")
                extra.unlink()
            finally:
                self.controller.close_handles(held)
                if process.poll() is None:
                    process.kill()
                    process.wait()
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
            evidence_path.write_text("released", encoding="utf-8")
            self.assertEqual(evidence_path.read_text(encoding="utf-8"), "released")

    def test_16_controller_and_wrapper_compile_without_blender(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            py_compile.compile(
                str(CONTROLLER_PATH), cfile=str(Path(temporary) / "controller.pyc"), doraise=True
            )
            py_compile.compile(
                str(WRAPPER_PATH), cfile=str(Path(temporary) / "wrapper.pyc"), doraise=True
            )

    def test_17_package_manifest_exactly_binds_all_required_artifacts(self) -> None:
        self.assertTrue(MANIFEST_PATH.is_file(), "final package manifest is missing")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["artifact_kind"],
            "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_PREPARATION",
        )
        artifacts = manifest["artifacts"]
        self.assertEqual(
            {row["path"] for row in artifacts},
            set(self.config["manifest_contract"]["required_artifact_paths"]),
        )
        for row in artifacts:
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(digest(path), row["sha256"])

    def test_18_test_results_are_truthful_and_final(self) -> None:
        record = json.loads((PREP / "TEST_RESULTS.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "PASSED")
        self.assertGreaterEqual(record["tests_run"], 18)
        self.assertEqual(record["failures"], 0)
        self.assertEqual(record["errors"], 0)
        self.assertFalse(record["blender_invoked"])
        self.assertFalse(record["blend_mutated"])
        self.assertFalse(record["live_authorization_exists"])
        self.assertFalse(record["candidate_directory_exists"])
        self.assertFalse(record["execution_directory_exists"])


if __name__ == "__main__":
    unittest.main()
