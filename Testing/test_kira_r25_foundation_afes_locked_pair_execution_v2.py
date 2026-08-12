from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from tools import kira_r25_canonical_receipt as canonical_receipt
from tools import run_kira_r25_foundation_afes_locked_pair_v2 as controller


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / controller.CONTRACT_RELATIVE_PATH
REAL_OUTPUT = ROOT / controller.OUTPUT_RELATIVE_PATH


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeLocks:
    def __init__(self, *, fail_on_add: int | None = None) -> None:
        self.fail_on_add = fail_on_add
        self.active = False
        self.closed = False
        self.locked_paths: list[Path] = []
        self.locked_bytes: list[bytes] = []

    def __enter__(self) -> "FakeLocks":
        self.active = True
        return self

    def add(self, path: Path) -> None:
        if self.fail_on_add == len(self.locked_paths) + 1:
            raise controller.LockedPairV2Error("synthetic_partial_lock_failure")
        exact = Path(path).resolve(strict=True)
        self.locked_paths.append(exact)
        self.locked_bytes.append(exact.read_bytes())

    def close(self) -> None:
        self.closed = True
        self.active = False

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminated = 0
        self.killed = 0

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated += 1
        self.returncode = -15

    def kill(self) -> None:
        self.killed += 1
        self.returncode = -9

    def wait(self, timeout: int | None = None) -> int:
        if self.returncode is None:
            raise AssertionError("wait called before exact synthetic child termination")
        return self.returncode


class LockedPairExecutionV2Tests(unittest.TestCase):
    def test_rejected_attempt01_is_byte_preserved(self) -> None:
        expected = {
            "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v1.json": (
                4226,
                "2d814be92de63978ac1b7f2427ea67b8fbea6c21acbe5da1613641a18ed31b32",
            ),
            "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v1.py": (
                7666,
                "57c3894800477a35ed8631168b836541da7703c31b8c4009297213ed80b88131",
            ),
            "tools/run_kira_r25_foundation_afes_locked_pair.py": (
                18382,
                "4568bd9fb7b2cc0072d3e97d9fd5603dfa6943dd736c122bae218d2102119fd5",
            ),
            "Testing/test_kira_r25_foundation_afes_locked_pair_execution.py": (
                5523,
                "f8de598e7bf4ec40d5535f73196576419f1498dde50ad4d65f7ac41e1221e145",
            ),
            "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/CHECKPOINT.md": (
                3235,
                "7ce537d69a8954f7ccbd023aa2840ccd5870db99f039243280d7741f9c463092",
            ),
            "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/INDEPENDENT_AUDIT_ATTEMPT_01.md": (
                8704,
                "eda4a07a27e89196a9e4cb083cdb10506500d4fc845d748017952e735eaab654",
            ),
        }
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(sha256_file(path), digest, relative)

    def test_contract_and_source_are_narrow_and_not_executable_authority(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["schema"],
            "kira.avatar.r25.foundation_afes_locked_pair_execution.v2",
        )
        self.assertEqual(contract["attempt_id"], "attempt_02")
        self.assertTrue(contract["scope"]["read_only_blender_diagnostic"])
        for key in (
            "blend_mutation_allowed",
            "blend_save_allowed",
            "render_allowed",
            "candidate_creation_allowed",
            "body_authoring_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "export_allowed",
            "publication_allowed",
        ):
            self.assertFalse(contract["scope"][key], key)
        process = contract["process_contract"]
        self.assertEqual(process["maximum_stdout_bytes"], 4 * 1024 * 1024)
        self.assertEqual(process["maximum_stderr_bytes"], 4 * 1024 * 1024)
        self.assertTrue(process["project_modules_import_only_after_locked_verification"])
        source = (ROOT / contract["bindings"]["parent_controller"]["path"]).read_text(
            encoding="utf-8"
        )
        self.assertNotIn(".communicate(", source)
        for forbidden in ("bpy.ops.wm.save", "render.render", "export_scene", "save_as_mainfile"):
            self.assertNotIn(forbidden, source)
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                self.assertFalse((node.module or "").startswith("tools"))
            if isinstance(node, ast.Import):
                self.assertNotIn("bpy", {alias.name for alias in node.names})

    def test_real_contract_fully_verifies_only_against_complete_discovered_set(self) -> None:
        digest = sha256_file(CONTRACT)
        contract_path, _, paths = controller._untrusted_discovery()
        verified, exact_paths = controller._verify_everything_under_locks(
            expected_contract_sha256=digest,
            contract_path=contract_path,
            expected_locked_paths={path.resolve(strict=True) for path in paths},
        )
        self.assertEqual(verified["attempt_id"], "attempt_02")
        self.assertEqual(set(exact_paths), {path.resolve(strict=True) for path in paths})

    def test_full_contract_drift_fails_before_binding_or_launch_work(self) -> None:
        digest = sha256_file(CONTRACT)
        contract_path, parsed, paths = controller._untrusted_discovery()
        hostile = copy.deepcopy(parsed)
        hostile["scope"]["body_authoring_allowed"] = True
        real_parse = controller._parse_json

        def changed_parse(path: Path, label: str) -> dict[str, object]:
            if label == "locked_contract":
                return hostile
            return real_parse(path, label)

        with mock.patch.object(controller, "_parse_json", side_effect=changed_parse):
            with self.assertRaisesRegex(controller.LockedPairV2Error, "scope_drift"):
                controller._verify_everything_under_locks(
                    expected_contract_sha256=digest,
                    contract_path=contract_path,
                    expected_locked_paths={path.resolve(strict=True) for path in paths},
                )

    def test_complete_lock_set_precedes_body_and_partial_lock_failure_never_calls_body(self) -> None:
        paths = [CONTRACT, ROOT / "tools/kira_r25_canonical_receipt.py"]
        observed: list[bool] = []

        def body(locks: FakeLocks) -> str:
            observed.append(locks.active and set(locks.locked_paths) == set(paths))
            return "called"

        result = controller._with_complete_lock_set(
            paths, body, lock_factory=FakeLocks
        )
        self.assertEqual(result, "called")
        self.assertEqual(observed, [True])
        called = False

        def forbidden_body(locks: FakeLocks) -> None:
            nonlocal called
            called = True

        failing = FakeLocks(fail_on_add=2)
        with self.assertRaisesRegex(controller.LockedPairV2Error, "partial_lock"):
            controller._with_complete_lock_set(
                paths, forbidden_body, lock_factory=lambda: failing
            )
        self.assertFalse(called)
        self.assertTrue(failing.closed)

    def test_same_length_prelock_replacement_is_rejected_before_launch(self) -> None:
        cache = ROOT / "RecoverySprint/runtime_cache"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="r25_toctou_", dir=cache) as folder:
            path = Path(folder) / "synthetic_executable.bin"
            path.write_bytes(b"GOOD")
            row = {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": 4,
                "sha256": hashlib.sha256(b"GOOD").hexdigest(),
            }
            path.write_bytes(b"EVIL")
            launched = False
            fake = FakeLocks()

            def locked_verify_then_launch(locks: FakeLocks) -> None:
                nonlocal launched
                controller._verify_row_locked("synthetic_executable", row)
                launched = True

            with self.assertRaisesRegex(controller.LockedPairV2Error, "binding_drift"):
                controller._with_complete_lock_set(
                    [path], locked_verify_then_launch, lock_factory=lambda: fake
                )
            self.assertEqual(fake.locked_bytes, [b"EVIL"])
            self.assertFalse(launched)

    def test_after_snapshot_is_refused_after_unlock(self) -> None:
        fake = FakeLocks()
        with fake:
            fake.add(CONTRACT)
            before = controller._snapshot_under_complete_locks([CONTRACT], fake)
            self.assertEqual(before[str(CONTRACT.resolve())]["sha256"], sha256_file(CONTRACT))
        with self.assertRaisesRegex(controller.LockedPairV2Error, "without_active"):
            controller._snapshot_under_complete_locks([CONTRACT], fake)

    def test_bounded_drain_caps_memory_and_requests_exact_child_termination(self) -> None:
        result: list[object] = []
        event = threading.Event()
        controller._drain_bounded(io.BytesIO(b"x" * 64), 10, result, event)
        self.assertTrue(event.is_set())
        self.assertEqual(len(result), 1)
        info = result[0]
        self.assertEqual(info["captured"], b"x" * 10)
        self.assertEqual(info["total_bytes"], 64)
        self.assertTrue(info["overflow"])
        process = FakeProcess()
        reason = controller._wait_bounded_child(
            process, timeout_seconds=180, overflow_event=event
        )
        self.assertEqual(reason, "bounded_stream_limit_exceeded")
        self.assertEqual(process.terminated, 1)
        self.assertEqual(process.killed, 0)

    def _assert_post_root_failure_is_canonical_and_append_only(
        self, synthetic_failure: BaseException
    ) -> None:
        cache = ROOT / "RecoverySprint/runtime_cache"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="r25_outcome_", dir=cache) as folder:
            base = Path(folder)
            bound = base / "bound.bin"
            contract_path = base / "contract.json"
            bound.write_bytes(b"locked")
            contract_path.write_text("{}", encoding="utf-8")
            output = base / "attempt"
            relative_output = output.relative_to(ROOT).as_posix()
            real_complete_lock = controller._with_complete_lock_set

            def complete_lock(paths: object, body: object) -> object:
                return real_complete_lock(
                    paths, body, lock_factory=FakeLocks
                )

            patches = (
                mock.patch.object(
                    controller,
                    "_untrusted_discovery",
                    return_value=(contract_path, {}, [bound]),
                ),
                mock.patch.object(
                    controller,
                    "_verify_everything_under_locks",
                    return_value=({}, [bound]),
                ),
                mock.patch.object(
                    controller,
                    "_import_locked_modules",
                    return_value=(canonical_receipt, object()),
                ),
                mock.patch.object(controller, "_with_complete_lock_set", side_effect=complete_lock),
                mock.patch.object(controller, "_run_child", side_effect=synthetic_failure),
                mock.patch.object(controller, "OUTPUT_RELATIVE_PATH", relative_output),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
                with self.assertRaises(type(synthetic_failure)):
                    controller.run_pair("0" * 64)
                receipt_path = output / "CONTROLLER_OUTCOME.receipt.bin"
                first = receipt_path.read_bytes()
                decoded = canonical_receipt.decode_receipt_frame(first).payload
                self.assertEqual(decoded["status"], "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY")
                self.assertEqual(decoded["failure_type"], type(synthetic_failure).__name__)
                self.assertIn(str(synthetic_failure), decoded["failure"])
                with self.assertRaises(FileExistsError):
                    controller.run_pair("0" * 64)
                self.assertEqual(receipt_path.read_bytes(), first)

    def test_popen_failure_gets_canonical_append_only_outcome(self) -> None:
        self._assert_post_root_failure_is_canonical_and_append_only(
            OSError("synthetic_popen_failure")
        )

    def test_run_child_handles_direct_popen_failure_without_blender(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cache = ROOT / "RecoverySprint/runtime_cache"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="r25_popen_", dir=cache) as folder:
            with mock.patch.object(
                controller.subprocess,
                "Popen",
                side_effect=OSError("synthetic_direct_popen_failure"),
            ):
                with self.assertRaisesRegex(OSError, "synthetic_direct_popen_failure"):
                    controller._run_child(
                        contract=contract,
                        contract_sha256=sha256_file(CONTRACT),
                        run_number=1,
                        nonce="1" * 64,
                        evidence_root=Path(folder),
                        receipt_module=canonical_receipt,
                        topology_module=object(),
                    )

    def test_frame_mismatch_gets_canonical_append_only_outcome(self) -> None:
        self._assert_post_root_failure_is_canonical_and_append_only(
            controller.LockedPairV2Error("synthetic_frame_mismatch")
        )

    def test_real_execution_root_remains_absent(self) -> None:
        self.assertFalse(REAL_OUTPUT.exists())


if __name__ == "__main__":
    unittest.main()
