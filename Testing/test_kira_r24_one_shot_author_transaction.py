from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock


from tools import blender_author_kira_r24_one_shot_candidate as worker
from tools import run_kira_r24_one_shot_author_transaction as controller


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "tools/blender_author_kira_r24_one_shot_candidate.py"
CONTROLLER_PATH = ROOT / "tools/run_kira_r24_one_shot_author_transaction.py"
RUNTIME_ROOT = ROOT / controller.RUNTIME_ROOT_RELATIVE


class OneShotR24StaticTests(unittest.TestCase):
    def test_01_controller_is_inert_after_r4_rejection(self) -> None:
        self.assertNotEqual(
            controller.EXECUTION_AUTHORITY_STATE,
            controller.REQUIRED_EXECUTION_AUTHORITY_STATE,
        )
        with self.assertRaisesRegex(controller.R24OneShotControllerError, "inert"):
            controller.execute_transaction(
                dependency_verifier=lambda: self.fail("dependency verification ran"),
                package_verifier=lambda: self.fail("package verification ran"),
                process_guard=lambda: self.fail("process guard ran"),
                reserver=lambda: self.fail("attempt reservation ran"),
                child_runner=lambda *args, **kwargs: self.fail("Blender ran"),
            )

    def test_02_worker_is_inert_before_bpy_or_source_open(self) -> None:
        self.assertNotEqual(worker.EXECUTION_AUTHORITY_STATE, worker.REQUIRED_EXECUTION_AUTHORITY_STATE)
        args = argparse.Namespace(
            execute_authoring=True,
            controller_nonce="0" * 64,
            source=str(ROOT / worker.SOURCE_RELATIVE),
            output=str(ROOT / worker.RUNTIME_ROOT_RELATIVE / "attempt_01" / worker.CANDIDATE_BASENAME),
            job_gate=str(ROOT / worker.RUNTIME_ROOT_RELATIVE / "attempt_01" / "gate.json"),
        )
        with self.assertRaisesRegex(worker.R24OneShotAuthorError, "inert"):
            worker.run_authoring(args, bpy_module=object())

    def test_03_symbolic_dependencies_cannot_validate(self) -> None:
        with self.assertRaisesRegex(controller.R24OneShotControllerError, "not sealed"):
            controller.verify_dependencies()
        with self.assertRaisesRegex(worker.R24OneShotAuthorError, "not sealed"):
            worker._verify_binding(worker.AUTHOR_OPERATION_BINDING, "operation")

    def test_04_no_attempt_was_created_by_static_preparation(self) -> None:
        self.assertFalse((RUNTIME_ROOT / controller.ATTEMPT_NAME).exists())

    def test_05_complete_r19_49_file_manifest_is_rehashed_and_closed(self) -> None:
        result = controller.verify_r19_package()
        self.assertEqual(result["verified_file_count_excluding_manifest"], 49)
        self.assertEqual(result["closed_directory_file_count_including_manifest"], 50)
        self.assertEqual(result["manifest"]["sha256"], controller.R19_MANIFEST_SHA256)
        self.assertEqual(result["source"]["sha256"], controller.R19_SOURCE_SHA256)

    def test_06_worker_ast_has_one_explicit_load_and_one_save(self) -> None:
        tree = ast.parse(WORKER_PATH.read_text(encoding="utf-8"))
        opens = []
        saves = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == "open_mainfile":
                opens.append(node)
            if node.func.attr == "save_as_mainfile":
                saves.append(node)
        self.assertEqual(len(opens), 1)
        self.assertEqual(len(saves), 1)
        load_ui = [item for item in opens[0].keywords if item.arg == "load_ui"]
        self.assertEqual(len(load_ui), 1)
        self.assertIsInstance(load_ui[0].value, ast.Constant)
        self.assertIs(load_ui[0].value.value, False)

    def test_07_worker_requires_exact_author_operation_result(self) -> None:
        valid = {
            "schema": "kira.avatar.r24.r5_external_surface_author_operation.v1",
            "status": "AUTHORED_IN_MEMORY_POSTSAVE_EVALUATION_REQUIRED",
            "authorized_mutated_objects": [worker.BODY_OBJECT_NAME, worker.PATCH_OBJECT_NAME],
            "save_performed": False,
            "render_performed": False,
            "export_performed": False,
            "activation_performed": False,
            "assignment_performed": False,
            "publication_performed": False,
        }
        self.assertIs(worker.validate_operation_result(valid), valid)
        for key in (
            "save_performed", "render_performed", "export_performed",
            "activation_performed", "assignment_performed", "publication_performed",
        ):
            changed = dict(valid)
            changed[key] = True
            with self.assertRaises(worker.R24OneShotAuthorError, msg=key):
                worker.validate_operation_result(changed)

    def test_08_save_helper_performs_exactly_one_call(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            output = Path(raw) / "candidate.blend"
            calls = []

            def save_as_mainfile(**kwargs):
                calls.append(kwargs)
                output.write_bytes(b"candidate")
                return {"FINISHED"}

            fake_bpy = types.SimpleNamespace(
                ops=types.SimpleNamespace(
                    wm=types.SimpleNamespace(save_as_mainfile=save_as_mainfile)
                )
            )
            worker._save_once(fake_bpy, output)
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0]["check_existing"])
            self.assertFalse(calls[0]["relative_remap"])
            with self.assertRaisesRegex(worker.R24OneShotAuthorError, "appeared"):
                worker._save_once(fake_bpy, output)
            self.assertEqual(len(calls), 1)

    def test_09_author_and_extractor_commands_share_exact_safety_flags(self) -> None:
        paths = {
            "candidate": ROOT / "x" / controller.CANDIDATE_BASENAME,
            "extraction": ROOT / "x" / "fresh" / "capture.json",
            "job_gate": ROOT / "x" / "gate.json",
        }
        dependencies = self.fake_dependencies()
        author = controller.author_command(paths, dependencies, "1" * 64)
        extractor = controller.extractor_command(paths, dependencies, "2" * 64, "1" * 64)
        self.assertEqual(author[1 : 1 + len(controller.SAFETY_FLAGS)], controller.SAFETY_FLAGS)
        self.assertEqual(extractor[1 : 1 + len(controller.SAFETY_FLAGS)], controller.SAFETY_FLAGS)
        self.assertEqual(author.count("--execute-authoring"), 1)
        self.assertEqual(author.count("--python"), 1)
        self.assertEqual(extractor.count("--python"), 1)
        self.assertNotIn(str(paths["candidate"]), author[: author.index("--")])
        self.assertIn(str(paths["candidate"]), extractor[: extractor.index("--")])

    def test_10_mocked_transaction_is_exactly_one_author_then_one_reopen(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            calls: list[list[str]] = []

            def fake_child(command, environment, **kwargs):
                command = list(command)
                calls.append(command)
                if "--execute-authoring" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_bytes(b"exact candidate bytes")
                    pid = 4101
                else:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text("{}", encoding="utf-8")
                    pid = 4102
                return self.successful_child(pid)

            gate = types.SimpleNamespace(validate_extraction_envelope=lambda *args, **kwargs: set())
            with (
                mock.patch.object(
                    controller,
                    "EXECUTION_AUTHORITY_STATE",
                    controller.REQUIRED_EXECUTION_AUTHORITY_STATE,
                ),
                mock.patch.object(controller, "_load_exact_gate", return_value=gate),
            ):
                result = controller.execute_transaction(
                    dependency_verifier=self.fake_dependencies,
                    package_verifier=lambda: {"verified": True},
                    process_guard=lambda: {"blender_process_count": 0},
                    reserver=lambda: paths,
                    child_runner=fake_child,
                )
            self.assertEqual(len(calls), 2)
            self.assertIn("--execute-authoring", calls[0])
            self.assertNotIn("--execute-authoring", calls[1])
            self.assertEqual(result["author_blender_invocation_count"], 1)
            self.assertEqual(result["fresh_reopen_blender_invocation_count"], 1)
            self.assertEqual(result["retry_count"], 0)
            self.assertFalse(result["candidate_accepted"])
            self.assertEqual(result["author"]["pid"], 4101)
            self.assertEqual(result["fresh_reopen"]["pid"], 4102)
            self.assertTrue(result["author"]["job_close"]["kill_on_job_close_applied"])
            expected = hashlib.sha256(b"exact candidate bytes").hexdigest()
            self.assertEqual(result["candidate_post_author_exit"]["sha256"], expected)
            self.assertIn(expected, calls[1])
            self.assertTrue(paths["result"].is_file())

    def test_11_author_failure_never_starts_fresh_reopen(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            calls = 0

            def failed_author(*args, **kwargs):
                nonlocal calls
                calls += 1
                return {
                    **self.successful_child(4201),
                    "returncode": 1,
                    "stderr": b"author failed",
                }

            with mock.patch.object(
                controller,
                "EXECUTION_AUTHORITY_STATE",
                controller.REQUIRED_EXECUTION_AUTHORITY_STATE,
            ):
                with self.assertRaisesRegex(controller.R24OneShotControllerError, "author child failed"):
                    controller.execute_transaction(
                        dependency_verifier=self.fake_dependencies,
                        package_verifier=lambda: {"verified": True},
                        process_guard=lambda: {"blender_process_count": 0},
                        reserver=lambda: paths,
                        child_runner=failed_author,
                    )
            self.assertEqual(calls, 1)
            self.assertFalse(paths["extraction"].exists())

    def test_12_unclean_author_exit_rejects_before_candidate_hash_or_reopen(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as raw:
            paths = self.temp_paths(Path(raw))
            calls = 0

            def unclean(*args, **kwargs):
                nonlocal calls
                calls += 1
                return {**self.successful_child(4301), "direct_exit_observed": False}

            with mock.patch.object(
                controller,
                "EXECUTION_AUTHORITY_STATE",
                controller.REQUIRED_EXECUTION_AUTHORITY_STATE,
            ):
                with self.assertRaisesRegex(controller.R24OneShotControllerError, "did not exit cleanly"):
                    controller.execute_transaction(
                        dependency_verifier=self.fake_dependencies,
                        package_verifier=lambda: {"verified": True},
                        process_guard=lambda: {"blender_process_count": 0},
                        reserver=lambda: paths,
                        child_runner=unclean,
                    )
            self.assertEqual(calls, 1)

    def test_13_source_code_has_two_direct_child_calls_and_no_retry_loop(self) -> None:
        tree = ast.parse(CONTROLLER_PATH.read_text(encoding="utf-8"))
        execute = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute_transaction"
        )
        child_calls = [
            node
            for node in ast.walk(execute)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "child_runner"
        ]
        self.assertEqual(len(child_calls), 2)
        self.assertFalse(any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(execute)))

    def test_14_parent_job_gate_binds_exact_parent_child_and_nonce(self) -> None:
        source = WORKER_PATH.read_text(encoding="utf-8")
        for literal in (
            '"parent_pid": os.getppid()',
            '"child_pid": os.getpid()',
            '"nonce": args.controller_nonce',
            '"assigned": True',
            '"kill_on_job_close": True',
        ):
            self.assertIn(literal, source)
        controller_source = CONTROLLER_PATH.read_text(encoding="utf-8")
        self.assertIn("AssignProcessToJobObject", controller_source)
        self.assertIn("0x00002000", controller_source)
        self.assertIn("candidate_after_author_exit = sha256_file(candidate)", controller_source)

    @staticmethod
    def fake_dependencies() -> dict[str, dict[str, object]]:
        return {
            "blender": {"path": "C:/fake/blender.exe", "bytes": 1, "sha256": "a" * 64},
            "author_worker": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "b" * 64},
            "external_surface_author_operation": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "c" * 64},
            "accepted_artifact_gate": {"path": str(CONTROLLER_PATH), "bytes": 1, "sha256": "d" * 64},
            "read_only_extractor": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "e" * 64},
            "intersection_helper": {"path": str(WORKER_PATH), "bytes": 1, "sha256": "f" * 64},
            "accepted_gate_contract": {"path": str(CONTROLLER_PATH), "bytes": 1, "sha256": "0" * 64},
        }

    @staticmethod
    def temp_paths(root: Path) -> dict[str, Path]:
        attempt = root / "attempt_01"
        attempt.mkdir()
        extraction_directory = attempt / "fresh_reopen"
        extraction_directory.mkdir()
        return {
            "attempt": attempt,
            "candidate": attempt / controller.CANDIDATE_BASENAME,
            "extraction_directory": extraction_directory,
            "extraction": extraction_directory / controller.FRESH_REOPEN_BASENAME,
            "job_gate": attempt / controller.JOB_GATE_BASENAME,
            "result": attempt / controller.RESULT_BASENAME,
            "failure": attempt / controller.FAILURE_BASENAME,
        }

    @staticmethod
    def successful_child(pid: int) -> dict[str, object]:
        return {
            "pid": pid,
            "returncode": 0,
            "stdout": b"ok",
            "stderr": b"",
            "direct_exit_observed": True,
            "job_assignment": {
                "assigned": True,
                "kill_on_job_close": True,
                "child_pid": pid,
            },
            "job_close": {"closed": True, "kill_on_job_close_applied": True},
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
