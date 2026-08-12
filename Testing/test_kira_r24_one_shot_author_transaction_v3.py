from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


from tools import blender_author_kira_r24_one_shot_candidate_v3 as worker
from tools import run_kira_r24_one_shot_author_transaction_v3 as controller


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
WORKER_PATH = ROOT / "tools/blender_author_kira_r24_one_shot_candidate_v3.py"
CONTROLLER_PATH = ROOT / "tools/run_kira_r24_one_shot_author_transaction_v3.py"

PRESERVED_IDENTITIES = {
    ROOT / "tools/blender_author_kira_r24_one_shot_candidate.py":
        "3cad1c2fb5a9fff9f52e8ed2e7051955dfa3ad1953b32362669661b441e9d631",
    ROOT / "tools/run_kira_r24_one_shot_author_transaction.py":
        "cb59960f8a48dd82de2dbd65c313c6df05d4c26176989c5c5e82fe92e18157c8",
    ROOT / "Testing/test_kira_r24_one_shot_author_transaction.py":
        "bb4cd25d331880537b81f78c444465518a2da2622f377dcf35550576ddba39fa",
    ROOT / "System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_STATIC_PREPARATION_20260809.md":
        "bc118f2be708cd0da30181b59a9427abb2802c746e7ca63fd31448c444554f84",
    ROOT / "tools/blender_author_kira_r24_one_shot_candidate_v2.py":
        "620b76f55d445376103da5e9a46cea2a2c1a36e20229b49548a47c5fb646a24a",
    ROOT / "tools/run_kira_r24_one_shot_author_transaction_v2.py":
        "131c61358309b4fba3aea4fe2040ceef90c7611bcf499c19ffdcdc9dcc62a6f6",
    ROOT / "Testing/test_kira_r24_one_shot_author_transaction_v2.py":
        "c0514872f866f8779499268b7191a8d57df51ef8430fdb7104f493daa5cc265b",
    ROOT / "System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_STATIC_PREPARATION_V2_20260809.md":
        "9f5ecfc637a9abc02cc5f9a4c480961db7f14d78cd801abc9bbb139844ec4676",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def harmless_command(text: str = "V3_REAL_SUSPENDED_JOB_OK") -> list[str]:
    return [sys.executable, "-B", "-c", f"print({text!r}, flush=True)"]


class R24OneShotV3StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        TMP.mkdir(exist_ok=True)

    def test_01_v1_v2_and_their_checkpoints_are_byte_exact(self) -> None:
        for path, expected in PRESERVED_IDENTITIES.items():
            with self.subTest(path=path.name):
                self.assertEqual(digest(path), expected)

    def test_02_controller_authority_fails_before_any_work(self) -> None:
        self.assertIs(controller.EXECUTION_AUTHORITY_GRANTED, False)
        with mock.patch.object(controller, "verify_r19_package") as package:
            with self.assertRaisesRegex(controller.R24OneShotControllerV3Error, "inert"):
                controller.execute_transaction()
            package.assert_not_called()

    def test_03_worker_authority_fails_before_bpy_or_paths(self) -> None:
        self.assertIs(worker.EXECUTION_AUTHORITY_GRANTED, False)
        with self.assertRaisesRegex(worker.R24OneShotAuthorV3Error, "inert"):
            worker.run_authoring(argparse.Namespace(execute_authoring=True), bpy_module=object())

    def test_04_r7_contract_and_author_operation_remain_symbolic(self) -> None:
        for binding in (worker.ACCEPTED_R7_CONTRACT_BINDING, worker.AUTHOR_OPERATION_R7_BINDING):
            self.assertIsNone(binding["bytes"])
            self.assertIsNone(binding["sha256"])
            with self.assertRaisesRegex(worker.R24OneShotAuthorV3Error, "unsealed"):
                worker._verify_binding(binding, "R7")
        for name in ("accepted_gate_contract_r7", "external_surface_author_operation_r7"):
            with self.assertRaisesRegex(controller.R24OneShotControllerV3Error, "unsealed"):
                controller._binding(controller.DEPENDENCY_BINDINGS[name], name)

    def test_05_static_preparation_created_no_attempt(self) -> None:
        attempt = ROOT / controller.RUNTIME_ROOT_RELATIVE / controller.ATTEMPT_NAME
        self.assertFalse(os.path.lexists(attempt))

    def test_06_full_r19_package_and_source_are_still_exact(self) -> None:
        result = controller.verify_r19_package()
        self.assertEqual(result, {
            "manifest_sha256": controller.R19_MANIFEST_SHA256,
            "file_count": 49,
            "source_sha256": controller.R19_SOURCE_SHA256,
        })

    def test_07_worker_has_one_private_save_with_existing_check_enabled(self) -> None:
        tree = ast.parse(WORKER_PATH.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        opens = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "open_mainfile"]
        saves = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "save_as_mainfile"]
        self.assertEqual(len(opens), 1)
        self.assertEqual(len(saves), 1)
        self.assertIs(next(item for item in opens[0].keywords if item.arg == "load_ui").value.value, False)
        self.assertIs(next(item for item in saves[0].keywords if item.arg == "check_existing").value.value, True)
        self.assertNotIn("check_existing=False", WORKER_PATH.read_text(encoding="utf-8"))

    def test_08_private_save_then_no_replace_sealed_publication_is_real(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            attempt = Path(raw)
            private = attempt / "private.blend"
            staging = attempt / "sealed.blend"
            calls: list[dict[str, object]] = []

            def save_as_mainfile(**kwargs: object) -> set[str]:
                calls.append(dict(kwargs))
                Path(str(kwargs["filepath"])).write_bytes(b"private-candidate-v3")
                return {"FINISHED"}

            bpy = types.SimpleNamespace(
                ops=types.SimpleNamespace(wm=types.SimpleNamespace(save_as_mainfile=save_as_mainfile))
            )
            result = worker.save_private_once_then_seal(bpy, private, staging, attempt=attempt)
            self.assertFalse(os.path.lexists(private))
            self.assertEqual(staging.read_bytes(), b"private-candidate-v3")
            self.assertEqual(calls, [{
                "filepath": str(private), "check_existing": True, "relative_remap": False,
            }])
            self.assertEqual(result["blender_save_count"], 1)
            self.assertEqual(result["private_to_staging_no_replace_count"], 1)

    def test_09_preexisting_private_or_sealed_target_blocks_before_save(self) -> None:
        for occupied_name in ("private.blend", "sealed.blend"):
            with self.subTest(occupied=occupied_name), tempfile.TemporaryDirectory(dir=TMP) as raw:
                attempt = Path(raw)
                private = attempt / "private.blend"
                staging = attempt / "sealed.blend"
                (attempt / occupied_name).write_bytes(b"occupied")
                bpy = types.SimpleNamespace(ops=types.SimpleNamespace(wm=types.SimpleNamespace(
                    save_as_mainfile=lambda **kwargs: self.fail("Blender save was reached")
                )))
                with self.assertRaisesRegex(worker.R24OneShotAuthorV3Error, "already exists"):
                    worker.save_private_once_then_seal(bpy, private, staging, attempt=attempt)

    def test_10_final_publication_is_atomic_no_replace(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            source = root / "sealed.blend"
            final = root / "final.blend"
            source.write_bytes(b"sealed")
            controller.atomic_no_replace(source, final, root=root)
            self.assertFalse(os.path.lexists(source))
            self.assertEqual(final.read_bytes(), b"sealed")
            source.write_bytes(b"replacement")
            with self.assertRaises(controller.R24OneShotControllerV3Error):
                controller.atomic_no_replace(source, final, root=root)
            self.assertEqual(final.read_bytes(), b"sealed")
            self.assertEqual(source.read_bytes(), b"replacement")

    def test_11_actual_junction_alias_is_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            target = root / "real"
            alias = root / "alias"
            target.mkdir()
            completed = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(alias), str(target)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=False, check=False, timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
            try:
                with self.assertRaisesRegex(controller.R24OneShotControllerV3Error, "reparse"):
                    controller.checked_path(alias / "candidate.blend", root=root)
                with self.assertRaisesRegex(worker.R24OneShotAuthorV3Error, "reparse"):
                    worker.checked_path(alias / "candidate.blend", root=root)
            finally:
                if os.path.lexists(alias):
                    os.rmdir(alias)

    def test_12_r7_operation_result_scope_and_forbidden_actions_are_exact(self) -> None:
        valid = {
            "schema": "kira.avatar.r24.r7_external_surface_author_operation.v1",
            "status": "AUTHORED_IN_MEMORY_FRESH_REOPEN_REQUIRED",
            "authorized_mutated_objects": [worker.BODY_OBJECT_NAME, worker.PATCH_OBJECT_NAME],
            "protected_scope_before_sha256": "d" * 64,
            "protected_scope_after_sha256": "d" * 64,
            "save_performed": False, "render_performed": False,
            "export_performed": False, "activation_performed": False,
            "assignment_performed": False, "publication_performed": False,
        }
        self.assertIs(worker.validate_operation_result(valid), valid)
        for key in (
            "save_performed", "render_performed", "export_performed",
            "activation_performed", "assignment_performed", "publication_performed",
        ):
            changed = dict(valid)
            changed[key] = True
            with self.subTest(key=key), self.assertRaises(worker.R24OneShotAuthorV3Error):
                worker.validate_operation_result(changed)

    def test_13_actual_suspended_job_lifecycle_and_direct_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            nonce = "a" * 64
            stdout = root / "stdout.log"
            stderr = root / "stderr.log"
            command = harmless_command()
            record = controller.run_production_child(
                command, controller.child_environment(nonce), role="integration_probe",
                nonce=nonce, invocation_index=1, stdout_path=stdout, stderr_path=stderr,
                timeout_seconds=30, job_gate_path=None, boundary_root=root,
            )
            controller.validate_child_record(
                record, role="integration_probe", nonce=nonce, index=1,
                command=command, stdout_path=stdout, stderr_path=stderr, boundary_root=root,
            )
            self.assertEqual(stdout.read_text(encoding="utf-8").strip(), "V3_REAL_SUSPENDED_JOB_OK")
            self.assertTrue(record["created_suspended"])
            self.assertTrue(record["assigned_before_resume"])
            self.assertEqual(record["resume_previous_suspend_count"], 1)
            self.assertEqual(record["post_close_active_pids"], [])

    def test_14_injected_post_create_failure_terminates_waits_and_closes(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            native = controller.WindowsSuspendedJobNativeV3()
            native._restore_inheritance = lambda context: (_ for _ in ()).throw(
                RuntimeError("INJECTED_POST_CREATE_FAILURE")
            )
            with self.assertRaises(controller.R24OneShotOwnedFailureV3Error) as raised:
                native.create_suspended(
                    [sys.executable, "-B", "-c", "import time; time.sleep(30)"],
                    controller.child_environment("b" * 64), root / "stdout.log", root / "stderr.log",
                )
            report = raised.exception.cleanup_report
            self.assertEqual(raised.exception.stage, "post_CreateProcessW_inheritability_restore")
            self.assertTrue(report["terminate_process_attempted"])
            self.assertTrue(report["direct_wait_observed"])
            self.assertTrue(report["cleanup_complete"])
            self.assertEqual(report["errors"], [])
            self.assertEqual(native.active_system_pids([report["pid"]]), [])

    def test_15_cleanup_exception_is_recorded_propagated_and_not_suppressed(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            native = controller.WindowsSuspendedJobNativeV3()
            original_cleanup = native.failure_cleanup
            observed: dict[str, object] = {}
            native._restore_inheritance = lambda context: (_ for _ in ()).throw(
                RuntimeError("INJECTED_POST_CREATE_FAILURE")
            )

            def cleanup_then_raise(context: object, job: object) -> dict[str, object]:
                observed.update(original_cleanup(context, job))
                raise OSError("INJECTED_CLEANUP_EXCEPTION")

            native.failure_cleanup = cleanup_then_raise
            with self.assertRaises(controller.R24OneShotCleanupV3Error) as raised:
                native.create_suspended(
                    [sys.executable, "-B", "-c", "import time; time.sleep(30)"],
                    controller.child_environment("c" * 64), root / "stdout.log", root / "stderr.log",
                )
            self.assertTrue(observed["cleanup_complete"])
            self.assertIn("cleanup_raised:OSError:INJECTED_CLEANUP_EXCEPTION", raised.exception.cleanup_report["errors"])
            self.assertEqual(native.active_system_pids([raised.exception.cleanup_report["pid"]]), [])

    def test_16_exclusive_reservation_survives_both_actual_child_lifetimes(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            path = root / "CANDIDATE_RESERVATION_V3.json"
            reservation = controller.ExclusiveReservationV3.create(path, "e" * 64)
            script = (
                "from pathlib import Path; import sys\n"
                "p=Path(sys.argv[1]); results=[]\n"
                "try:\n p.write_text('overwrite', encoding='utf-8'); results.append('write_open')\n"
                "except OSError:\n results.append('write_blocked')\n"
                "try:\n p.unlink(); results.append('delete_open')\n"
                "except OSError:\n results.append('delete_blocked')\n"
                "print('|'.join(results), flush=True)\n"
            )
            try:
                for index, role in ((1, "author"), (2, "fresh_reopen")):
                    nonce = f"{index:x}" * 64
                    stdout = root / f"child_{index}.stdout.log"
                    stderr = root / f"child_{index}.stderr.log"
                    record = controller.run_production_child(
                        [sys.executable, "-B", "-c", script, str(path)],
                        controller.child_environment(nonce), role=role, nonce=nonce,
                        invocation_index=index, stdout_path=stdout, stderr_path=stderr,
                        timeout_seconds=30, job_gate_path=None, boundary_root=root,
                    )
                    self.assertTrue(record["tree_quiescent_after_close"])
                    self.assertEqual(stdout.read_text(encoding="utf-8").strip(), "write_blocked|delete_blocked")
                    self.assertFalse(reservation.closed)
            finally:
                reservation.close()
            path.write_text("released", encoding="utf-8")
            self.assertEqual(path.read_text(encoding="utf-8"), "released")

    def test_17_production_entry_points_offer_no_evidence_or_native_injection(self) -> None:
        self.assertEqual(list(inspect.signature(controller.execute_transaction).parameters), [])
        production = inspect.signature(controller.run_production_child).parameters
        self.assertNotIn("native", production)
        self.assertNotIn("evidence", production)
        source = inspect.getsource(controller.execute_transaction)
        self.assertEqual(source.count("run_production_child("), 2)
        self.assertNotIn("_run_owned_child(", source)

    def test_18_child_evidence_is_strict_and_tampering_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=TMP) as raw:
            root = Path(raw)
            nonce = "f" * 64
            command = harmless_command("STRICT_EVIDENCE")
            stdout = root / "stdout.log"
            stderr = root / "stderr.log"
            record = controller.run_production_child(
                command, controller.child_environment(nonce), role="integration_probe",
                nonce=nonce, invocation_index=1, stdout_path=stdout, stderr_path=stderr,
                timeout_seconds=30, job_gate_path=None, boundary_root=root,
            )
            changed = dict(record)
            changed["evidence_origin"] = "INJECTED"
            with self.assertRaisesRegex(controller.R24OneShotControllerV3Error, "evidence rejected"):
                controller.validate_child_record(
                    changed, role="integration_probe", nonce=nonce, index=1,
                    command=command, stdout_path=stdout, stderr_path=stderr, boundary_root=root,
                )

    def test_19_two_child_counts_require_distinct_identity_and_exact_order(self) -> None:
        rows = [
            {"role": "author", "invocation_index": 1, "pid": 11, "nonce": "a", "command_sha256": "x"},
            {"role": "fresh_reopen", "invocation_index": 2, "pid": 12, "nonce": "b", "command_sha256": "y"},
        ]
        self.assertEqual(controller.derive_child_counts(rows), {"author": 1, "fresh_reopen": 1, "total": 2})
        changed = [dict(item) for item in rows]
        changed[1]["pid"] = 11
        with self.assertRaisesRegex(controller.R24OneShotControllerV3Error, "not distinct"):
            controller.derive_child_counts(changed)

    def test_20_commands_keep_private_authoring_and_read_only_reopen_boundaries(self) -> None:
        controller_text = CONTROLLER_PATH.read_text(encoding="utf-8")
        worker_text = WORKER_PATH.read_text(encoding="utf-8")
        self.assertIn("--private-write-output", controller_text)
        self.assertIn("--sealed-staging-output", controller_text)
        self.assertIn("--disable-autoexec", controller.SAFETY_FLAGS)
        self.assertIn("--factory-startup", controller.SAFETY_FLAGS)
        self.assertIn("private_to_staging_no_replace_count", worker_text)
        self.assertIn("atomic_no_replace(paths[\"sealed_staging\"], paths[\"candidate\"]", controller_text)
        self.assertNotIn("check_existing=False", worker_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
