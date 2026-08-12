from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock


from tools import blender_author_kira_r24_one_shot_candidate_v2 as worker
from tools import run_kira_r24_one_shot_author_transaction_v2 as controller


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "tools/blender_author_kira_r24_one_shot_candidate_v2.py"
CONTROLLER_PATH = ROOT / "tools/run_kira_r24_one_shot_author_transaction_v2.py"
V1_IDENTITIES = {
    ROOT / "tools/blender_author_kira_r24_one_shot_candidate.py": "3cad1c2fb5a9fff9f52e8ed2e7051955dfa3ad1953b32362669661b441e9d631",
    ROOT / "tools/run_kira_r24_one_shot_author_transaction.py": "cb59960f8a48dd82de2dbd65c313c6df05d4c26176989c5c5e82fe92e18157c8",
    ROOT / "Testing/test_kira_r24_one_shot_author_transaction.py": "bb4cd25d331880537b81f78c444465518a2da2622f377dcf35550576ddba39fa",
    ROOT / "System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_STATIC_PREPARATION_20260809.md": "bc118f2be708cd0da30181b59a9427abb2802c746e7ca63fd31448c444554f84",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeReservation:
    def __init__(self) -> None:
        self.closed = False
        self.close_calls = 0

    def close(self) -> dict[str, object]:
        self.close_calls += 1
        self.closed = True
        return {"closed": True, "held_through_both_children": True}


class FakeNative:
    def __init__(self, gate: Path | None = None, fail_at: str | None = None, active_after: list[int] | None = None) -> None:
        self.events: list[object] = []
        self.gate = gate
        self.fail_at = fail_at
        self.active_after = [] if active_after is None else active_after

    def create_suspended(self, command, environment, stdout_path, stderr_path):
        self.events.append("create_suspended")
        stdout_path.write_bytes(b"stdout")
        stderr_path.write_bytes(b"")
        if self.fail_at == "create":
            raise controller.R24OneShotControllerV2Error("create failure")
        return {"process": "process", "thread": "thread", "pid": 5101}

    def create_job(self):
        self.events.append("create_job_configure")
        if self.fail_at == "job":
            raise controller.R24OneShotControllerV2Error("job failure")
        return "job"

    def assign(self, job, process):
        self.events.append("assign")
        if self.fail_at == "assign":
            raise controller.R24OneShotControllerV2Error("assign failure")

    def resume(self, thread):
        self.events.append("resume")
        if self.gate is not None:
            if not self.gate.is_file():
                raise AssertionError("gate was not written before resume")
            payload = json.loads(self.gate.read_text(encoding="utf-8"))
            if payload["assigned_before_resume"] is not True:
                raise AssertionError("assignment gate is false")
            if payload["resume_authorized"] is not True or "resumed" in payload:
                raise AssertionError("gate makes an inaccurate resume claim")
        if self.fail_at == "resume":
            raise controller.R24OneShotControllerV2Error("resume failure")
        return 1

    def close_thread(self, child):
        self.events.append("close_thread")
        child["thread"] = None

    def wait_direct_and_tree(self, child, job, timeout_seconds):
        self.events.append("wait_direct_and_tree")
        return {
            "direct_exit_observed": True,
            "exit_code": 0,
            "observed_pids": [5101, 5102],
            "active_before_job_close": [],
        }

    def close_process(self, child):
        self.events.append("close_process")
        child["process"] = None

    def close_job(self, job):
        self.events.append("close_job")

    def active_system_pids(self, candidates):
        self.events.append(("active_system_pids", list(candidates)))
        return list(self.active_after)

    def terminate_and_wait(self, child, job):
        self.events.append(("terminate_and_wait", None if child is None else child["pid"], job))


class R24OneShotV2StaticTests(unittest.TestCase):
    def test_01_preserved_v1_and_checkpoint_are_byte_exact(self) -> None:
        for path, expected in V1_IDENTITIES.items():
            with self.subTest(path=path.name):
                self.assertEqual(digest(path), expected)

    def test_02_v2_controller_is_inert_before_any_verifier(self) -> None:
        self.assertIs(controller.EXECUTION_AUTHORITY_GRANTED, False)
        with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "inert"):
            controller.execute_transaction(
                package_verifier=lambda: self.fail("package verifier ran"),
                dependency_verifier=lambda: self.fail("dependency verifier ran"),
                process_guard=lambda: self.fail("process guard ran"),
                reserver=lambda: self.fail("reservation ran"),
            )

    def test_03_v2_worker_is_inert_before_bpy_or_paths(self) -> None:
        self.assertIs(worker.EXECUTION_AUTHORITY_GRANTED, False)
        args = argparse.Namespace(
            execute_authoring=True,
            child_nonce="0" * 64,
            reservation_token="1" * 64,
            source="does-not-matter",
            staging_output="does-not-matter",
            reservation="does-not-matter",
            job_gate="does-not-matter",
            role="author",
        )
        with self.assertRaisesRegex(worker.R24OneShotAuthorV2Error, "inert"):
            worker.run_authoring(args, bpy_module=object())

    def test_04_symbolic_r5_and_author_bindings_fail_closed(self) -> None:
        with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "unsealed"):
            controller.verify_dependencies()
        with self.assertRaisesRegex(worker.R24OneShotAuthorV2Error, "not byte-sealed"):
            worker._verify_binding(worker.ACCEPTED_R5_CONTRACT_BINDING, "R5")

    def test_05_static_preparation_created_no_attempt(self) -> None:
        attempt = ROOT / controller.RUNTIME_ROOT_RELATIVE / controller.ATTEMPT_NAME
        self.assertFalse(os.path.lexists(attempt))

    def test_06_full_r19_package_and_source_are_rehashed(self) -> None:
        result = controller.verify_r19_package()
        self.assertEqual(result["file_count"], 49)
        self.assertEqual(result["manifest_sha256"], controller.R19_MANIFEST_SHA256)
        self.assertEqual(result["source_sha256"], controller.R19_SOURCE_SHA256)

    def test_07_worker_ast_has_one_load_one_save_and_no_ui_load(self) -> None:
        tree = ast.parse(WORKER_PATH.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        opens = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "open_mainfile"]
        saves = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "save_as_mainfile"]
        self.assertEqual(len(opens), 1)
        self.assertEqual(len(saves), 1)
        load_ui = next(item for item in opens[0].keywords if item.arg == "load_ui")
        self.assertIs(load_ui.value.value, False)

    def test_08_worker_refuses_existing_staging_before_save(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            attempt = Path(raw) / "attempt_01"
            staging_root = attempt / "author_staging"
            staging_root.mkdir(parents=True)
            output = staging_root / ("candidate_" + "1" * 64 + ".blend")
            output.write_bytes(b"occupied")
            fake = types.SimpleNamespace(
                ops=types.SimpleNamespace(wm=types.SimpleNamespace(
                    save_as_mainfile=lambda **kwargs: self.fail("save was reached")
                ))
            )
            with self.assertRaisesRegex(worker.R24OneShotAuthorV2Error, "already exists"):
                worker.save_staging_once(fake, output, attempt)

    def test_09_worker_refuses_reparse_parent_and_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            attempt = Path(raw)
            output = attempt / "author_staging" / ("candidate_" + "2" * 64 + ".blend")
            output.parent.mkdir()
            with mock.patch.object(worker, "_is_reparse", side_effect=lambda path: path == output.parent):
                with self.assertRaisesRegex(worker.R24OneShotAuthorV2Error, "reparsed"):
                    worker.refuse_existing_or_reparse_output(output, attempt)
            output.write_bytes(b"candidate")
            with mock.patch.object(controller, "_is_reparse", side_effect=lambda path: path == output):
                with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "reparsed"):
                    controller.assert_regular_nonreparse(output, attempt)

    def test_10_operation_result_is_exact_and_forbidden_actions_reject(self) -> None:
        valid = {
            "schema": "kira.avatar.r24.r5_external_surface_author_operation.v1",
            "status": "AUTHORED_IN_MEMORY_FRESH_REOPEN_REQUIRED",
            "authorized_mutated_objects": [worker.BODY_OBJECT_NAME, worker.PATCH_OBJECT_NAME],
            "protected_scope_before_sha256": "a" * 64,
            "protected_scope_after_sha256": "a" * 64,
            "save_performed": False,
            "render_performed": False,
            "export_performed": False,
            "activation_performed": False,
            "assignment_performed": False,
            "publication_performed": False,
        }
        self.assertIs(worker.validate_operation_result(valid), valid)
        for key in ("save_performed", "render_performed", "export_performed", "activation_performed", "assignment_performed", "publication_performed"):
            changed = dict(valid)
            changed[key] = True
            with self.subTest(key=key), self.assertRaises(worker.R24OneShotAuthorV2Error):
                worker.validate_operation_result(changed)

    def test_11_create_suspended_job_assign_gate_resume_order_is_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            root = Path(raw)
            gate = root / "gate.json"
            native = FakeNative(gate=gate)
            record = controller.run_suspended_owned_child(
                ["fake.exe", "--one"], {"X": "1"}, role="author", nonce="a" * 64,
                invocation_index=1, stdout_path=root / "stdout.log", stderr_path=root / "stderr.log",
                timeout_seconds=10, job_gate_path=gate, native=native,
            )
            self.assertEqual(native.events[:7], [
                "create_suspended", "create_job_configure", "assign", "resume",
                "close_thread", "wait_direct_and_tree", "close_process",
            ])
            self.assertEqual(native.events[7], "close_job")
            self.assertEqual(native.events[8], ("active_system_pids", [5101, 5102]))
            self.assertTrue(record["tree_quiescent_after_job_close"])

    def test_12_job_assign_and_resume_failures_terminate_and_wait_exact_child_tree(self) -> None:
        for stage in ("job", "assign", "resume"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
                root = Path(raw)
                gate = root / "gate.json"
                native = FakeNative(gate=gate, fail_at=stage)
                with self.assertRaises(controller.R24OneShotControllerV2Error):
                    controller.run_suspended_owned_child(
                        ["fake.exe"], {}, role="author", nonce="b" * 64, invocation_index=1,
                        stdout_path=root / "stdout.log", stderr_path=root / "stderr.log",
                        timeout_seconds=10, job_gate_path=gate, native=native,
                    )
                job = None if stage == "job" else "job"
                self.assertIn(("terminate_and_wait", 5101, job), native.events)
                self.assertIn("close_thread", native.events)
                self.assertIn("close_process", native.events)
                if job is not None:
                    self.assertIn("close_job", native.events)

    def test_13_post_job_independent_active_pid_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            root = Path(raw)
            native = FakeNative(active_after=[5102])
            with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "remained active"):
                controller.run_suspended_owned_child(
                    ["fake.exe"], {}, role="fresh_reopen", nonce="c" * 64, invocation_index=2,
                    stdout_path=root / "stdout.log", stderr_path=root / "stderr.log",
                    timeout_seconds=10, job_gate_path=None, native=native,
                )

    def test_14_child_evidence_validates_exact_artifacts_and_strict_types(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            root = Path(raw)
            command = ["fake.exe", "--x"]
            record = self.child_record(root, command, "author", "d" * 64, 1, 5201)
            self.assertIs(controller.validate_child_evidence(
                record, expected_role="author", expected_nonce="d" * 64,
                expected_invocation_index=1, expected_command=command,
                expected_stdout_path=root / "stdout.log", expected_stderr_path=root / "stderr.log",
            ), record)
            for field, bad in (
                ("assigned_before_resume", 1), ("resumed", False),
                ("resume_previous_suspend_count", True), ("exit_code", False),
                ("job_handle_closed", False), ("tree_quiescent_after_job_close", False),
            ):
                changed = dict(record)
                changed[field] = bad
                with self.subTest(field=field), self.assertRaises(controller.R24OneShotControllerV2Error):
                    controller.validate_child_evidence(
                        changed, expected_role="author", expected_nonce="d" * 64,
                        expected_invocation_index=1, expected_command=command,
                        expected_stdout_path=root / "stdout.log", expected_stderr_path=root / "stderr.log",
                    )

    def test_15_injected_wrong_stream_path_hash_and_reparse_reject(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            root = Path(raw)
            command = ["fake.exe"]
            record = self.child_record(root, command, "author", "e" * 64, 1, 5301)
            other = root / "other.log"
            other.write_bytes(b"other")
            changed = dict(record)
            changed["stdout"] = {"path": str(other), "bytes": 5, "sha256": digest(other)}
            with self.assertRaises(controller.R24OneShotControllerV2Error):
                controller.validate_child_evidence(
                    changed, expected_role="author", expected_nonce="e" * 64,
                    expected_invocation_index=1, expected_command=command,
                    expected_stdout_path=root / "stdout.log", expected_stderr_path=root / "stderr.log",
                )
            with mock.patch.object(controller, "_is_reparse", side_effect=lambda path: path == root / "stdout.log"):
                with self.assertRaises(controller.R24OneShotControllerV2Error):
                    controller.validate_child_evidence(
                        record, expected_role="author", expected_nonce="e" * 64,
                        expected_invocation_index=1, expected_command=command,
                        expected_stdout_path=root / "stdout.log", expected_stderr_path=root / "stderr.log",
                    )

    def test_16_transaction_children_must_be_distinct_and_counts_are_derived(self) -> None:
        records = [
            {"role": "author", "invocation_index": 1, "pid": 1, "nonce": "a", "command_sha256": "1"},
            {"role": "fresh_reopen", "invocation_index": 2, "pid": 2, "nonce": "b", "command_sha256": "2"},
        ]
        self.assertEqual(controller.validate_transaction_children(records), {"author": 1, "fresh_reopen": 1, "total": 2})
        for field in ("pid", "nonce", "command_sha256"):
            changed = [dict(item) for item in records]
            changed[1][field] = changed[0][field]
            with self.subTest(field=field), self.assertRaises(controller.R24OneShotControllerV2Error):
                controller.validate_transaction_children(changed)

    def test_17_commands_use_identical_safety_flags_and_distinct_roles(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            deps = self.dependencies()
            author = controller.author_command(paths, deps, "f" * 64)
            reopen = controller.reopen_command(paths, deps, "0" * 64, "1" * 64)
            self.assertEqual(author[1:1 + len(controller.SAFETY_FLAGS)], controller.SAFETY_FLAGS)
            self.assertEqual(reopen[1:1 + len(controller.SAFETY_FLAGS)], controller.SAFETY_FLAGS)
            self.assertEqual(author.count("--execute-authoring"), 1)
            self.assertNotIn("--execute-authoring", reopen)
            self.assertIn(str(paths["candidate"]), reopen[:reopen.index("--python")])

    def test_18_mocked_transaction_runs_exactly_one_author_then_one_fresh_reopen(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            calls: list[tuple[str, list[str]]] = []

            def child_runner(command, environment, **kwargs):
                command = list(command)
                role = kwargs["role"]
                calls.append((role, command))
                if role == "author":
                    Path(command[command.index("--staging-output") + 1]).write_bytes(b"candidate-v2")
                    pid = 5401
                else:
                    Path(command[command.index("--output") + 1]).write_text("{}", encoding="utf-8")
                    pid = 5402
                return self.child_record(
                    paths["attempt"], command, role, kwargs["nonce"],
                    kwargs["invocation_index"], pid,
                    stdout=kwargs["stdout_path"], stderr=kwargs["stderr_path"],
                )

            def publish(staging, candidate, attempt):
                self.assertFalse(os.path.lexists(candidate))
                staging.rename(candidate)

            gate = types.SimpleNamespace(validate_extraction_envelope=lambda *args, **kwargs: set())
            with (
                mock.patch.object(controller, "EXECUTION_AUTHORITY_GRANTED", True),
                mock.patch.object(controller, "_load_gate", return_value=gate),
            ):
                result = controller.execute_transaction(
                    package_verifier=lambda: {"verified": True},
                    dependency_verifier=self.dependencies,
                    process_guard=lambda: {"blender_process_count": 0},
                    reserver=lambda: paths,
                    child_runner=child_runner,
                    publisher=publish,
                )
            self.assertEqual([role for role, _ in calls], ["author", "fresh_reopen"])
            self.assertEqual(result["invocation_counts_derived_from_children"], {"author": 1, "fresh_reopen": 1, "total": 2})
            self.assertEqual(result["retry_count_derived_from_invocation_sequence"], 0)
            self.assertNotEqual(result["children"][0]["pid"], result["children"][1]["pid"])
            self.assertNotEqual(result["children"][0]["nonce"], result["children"][1]["nonce"])
            self.assertFalse(result["candidate_accepted"])
            self.assertTrue(paths["result"].is_file())
            self.assertEqual(paths["reservation"].close_calls, 1)

    def test_19_invalid_author_evidence_prevents_publish_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            calls = 0
            published = False

            def bad_runner(command, environment, **kwargs):
                nonlocal calls
                calls += 1
                command = list(command)
                Path(command[command.index("--staging-output") + 1]).write_bytes(b"candidate")
                record = self.child_record(
                    paths["attempt"], command, "author", kwargs["nonce"], 1, 5501,
                    stdout=kwargs["stdout_path"], stderr=kwargs["stderr_path"],
                )
                record["assigned_before_resume"] = False
                return record

            def publisher(*args):
                nonlocal published
                published = True

            with mock.patch.object(controller, "EXECUTION_AUTHORITY_GRANTED", True):
                with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "assigned_before_resume"):
                    controller.execute_transaction(
                        package_verifier=lambda: {}, dependency_verifier=self.dependencies,
                        process_guard=lambda: {}, reserver=lambda: paths,
                        child_runner=bad_runner, publisher=publisher,
                    )
            self.assertEqual(calls, 1)
            self.assertFalse(published)
            self.assertFalse(paths["candidate"].exists())

    def test_20_candidate_and_extraction_reparse_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            paths["candidate"].write_bytes(b"candidate")
            paths["extraction"].write_text("{}", encoding="utf-8")
            for target in (paths["candidate"], paths["extraction"]):
                with self.subTest(target=target.name), mock.patch.object(
                    controller, "_is_reparse", side_effect=lambda path, target=target: path == target
                ):
                    with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "reparsed"):
                        controller.assert_regular_nonreparse(target, paths["attempt"])

    def test_21_source_contains_win32_suspended_job_and_no_replace_primitives(self) -> None:
        source = CONTROLLER_PATH.read_text(encoding="utf-8")
        for token in (
            "CREATE_SUSPENDED", "CreateProcessW", "CreateJobObjectW",
            "SetInformationJobObject", "AssignProcessToJobObject", "ResumeThread",
            "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", "MoveFileExW",
            "active_system_pids", "CREATE_NEW", "FILE_FLAG_OPEN_REPARSE_POINT",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)
        self.assertIn("MoveFileExW(str(staging), str(candidate), 0)", source)

    def test_22_controller_has_exactly_two_direct_child_calls_and_no_retry_loop(self) -> None:
        tree = ast.parse(CONTROLLER_PATH.read_text(encoding="utf-8"))
        execute = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute_transaction")
        calls = [
            node for node in ast.walk(execute)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "child_runner"
        ]
        self.assertEqual(len(calls), 2)
        self.assertFalse(any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(execute)))

    def test_23_process_guard_never_terminates_existing_blender(self) -> None:
        completed = subprocess.CompletedProcess([], 0, b'"blender.exe","100","Console","1","10 K"\r\n', b"")
        with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "already active"):
            controller.ensure_no_blender_process(runner=lambda *args, **kwargs: completed)
        clean = subprocess.CompletedProcess([], 0, b'"python.exe","101","Console","1","10 K"\r\n', b"")
        self.assertEqual(controller.ensure_no_blender_process(runner=lambda *args, **kwargs: clean)["blender_process_count"], 0)

    def test_24_real_win32_reservation_blocks_write_and_delete_until_close(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            path = Path(raw) / "reservation.json"
            reservation = controller.ExclusiveReservation.create(path, "7" * 64)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["token"], "7" * 64)
            with self.assertRaises(PermissionError):
                path.write_text("tamper", encoding="utf-8")
            with self.assertRaises(PermissionError):
                path.unlink()
            self.assertTrue(reservation.close()["closed"])
            path.write_text("released", encoding="utf-8")
            self.assertEqual(path.read_text(encoding="utf-8"), "released")

    def test_25_atomic_publish_is_no_replace_and_preserves_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            attempt = Path(raw)
            staging = attempt / "staging.blend"
            candidate = attempt / "candidate.blend"
            staging.write_bytes(b"first")
            controller.atomic_publish_no_replace(staging, candidate, attempt)
            self.assertFalse(staging.exists())
            self.assertEqual(candidate.read_bytes(), b"first")
            second = attempt / "second.blend"
            second.write_bytes(b"second")
            with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "already exists"):
                controller.atomic_publish_no_replace(second, candidate, attempt)
            self.assertEqual(candidate.read_bytes(), b"first")
            self.assertEqual(second.read_bytes(), b"second")

    def test_26_cleanup_attempts_thread_process_and_job_even_if_one_close_fails(self) -> None:
        events: list[str] = []

        class Native:
            def close_thread(self, child):
                events.append("thread")
                raise OSError("thread close")

            def close_process(self, child):
                events.append("process")

            def close_job(self, job):
                events.append("job")

        with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "unproved"):
            controller._close_child_handles_safely(Native(), {"pid": 1}, "job")
        self.assertEqual(events, ["thread", "process", "job"])

    def test_27_controller_main_remains_inert_even_with_execute_flag(self) -> None:
        with self.assertRaisesRegex(controller.R24OneShotControllerV2Error, "static"):
            controller.main(["--execute-once"])

    @staticmethod
    def dependencies() -> dict[str, dict[str, object]]:
        return {
            "blender": {"path": "C:/fake/blender.exe", "bytes": 1, "sha256": "a" * 64},
            "author_worker_v2": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "b" * 64},
            "external_surface_author_operation_r5": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "c" * 64},
            "artifact_gate_r5": {"path": str(CONTROLLER_PATH), "bytes": 1, "sha256": "d" * 64},
            "read_only_extractor_r5": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "e" * 64},
            "intersection_helper": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "f" * 64},
            "accepted_gate_contract_r5": {"path": str(CONTROLLER_PATH), "bytes": 1, "sha256": "0" * 64},
        }

    @staticmethod
    def temp_paths(root: Path) -> dict[str, object]:
        attempt = root / "attempt_01"
        staging_root = attempt / "author_staging"
        extraction_root = attempt / "fresh_reopen"
        staging_root.mkdir(parents=True)
        extraction_root.mkdir()
        reservation_path = attempt / controller.RESERVATION_BASENAME
        reservation_path.write_text("{}", encoding="utf-8")
        token = "9" * 64
        return {
            "runtime": root,
            "attempt": attempt,
            "staging_root": staging_root,
            "extraction_root": extraction_root,
            "staging": staging_root / f"candidate_{token}.blend",
            "candidate": attempt / controller.FINAL_CANDIDATE_BASENAME,
            "extraction": extraction_root / "candidate_extraction.json",
            "reservation_path": reservation_path,
            "reservation": FakeReservation(),
            "reservation_token": token,
            "result": attempt / controller.RESULT_BASENAME,
        }

    @staticmethod
    def child_record(
        root: Path,
        command: list[str],
        role: str,
        nonce: str,
        index: int,
        pid: int,
        *,
        stdout: Path | None = None,
        stderr: Path | None = None,
    ) -> dict[str, object]:
        stdout = root / "stdout.log" if stdout is None else stdout
        stderr = root / "stderr.log" if stderr is None else stderr
        stdout.write_bytes(b"stdout evidence")
        stderr.write_bytes(b"")
        return {
            "schema": "kira.avatar.r24.suspended_owned_child.v2",
            "role": role,
            "nonce": nonce,
            "invocation_index": index,
            "command_sha256": controller.canonical_sha256(command),
            "pid": pid,
            "created_suspended": True,
            "job_created": True,
            "job_configured_kill_on_close": True,
            "assigned_before_resume": True,
            "resumed": True,
            "resume_previous_suspend_count": 1,
            "direct_exit_observed": True,
            "exit_code": 0,
            "job_observed_pids": [pid],
            "job_active_pids_before_close": [],
            "thread_handle_closed": True,
            "process_handle_closed": True,
            "job_handle_closed": True,
            "post_close_active_observed_pids": [],
            "tree_quiescent_after_job_close": True,
            "stdout": {"path": str(stdout), "bytes": stdout.stat().st_size, "sha256": digest(stdout)},
            "stderr": {"path": str(stderr), "bytes": stderr.stat().st_size, "sha256": digest(stderr)},
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
