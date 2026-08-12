from __future__ import annotations

import ast
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3.json"
WRAPPER = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3.py"
CONTROLLER = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v3.py"
OUTPUT_ROOT = ROOT / "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_03"
AUDIT = ROOT / "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03/INDEPENDENT_AUDIT.md"
EXACT = {
    CONTRACT: (22563, "ef002867881a78fd805754da4c9668cf08d4df0c2e8cd97af3c529b58f7531be"),
    WRAPPER: (15343, "58ca9009a9274f94640dc66cfe9ec2c30a4208a42f8d7c1dc86263e2aeabddbe"),
    CONTROLLER: (52830, "a0d5ea75c8062c66646da6f2d06ba131952f98f89515606bf53905d22016cdee"),
}


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeLocks:
    def __init__(self, paths: list[Path]) -> None:
        self.active = True
        self.locked_paths = [path.resolve(strict=True) for path in paths]


class Attempt03LockedPairStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller = _load("_test_locked_pair_v3", CONTROLLER)
        cls.wrapper = _load("_test_locked_wrapper_v3", WRAPPER)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_01_exact_closed_sources_and_pending_audit_gate(self) -> None:
        for path, (size, digest) in EXACT.items():
            value = path.read_bytes()
            self.assertEqual(len(value), size, path)
            self.assertEqual(hashlib.sha256(value).hexdigest(), digest, path)
        self.assertEqual(
            self.contract["status"],
            "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
        )
        self.assertFalse(AUDIT.exists())
        self.assertFalse(OUTPUT_ROOT.exists())
        self.assertEqual(
            self.contract["controller_audit_gate"]["path"],
            AUDIT.relative_to(ROOT).as_posix(),
        )

    def test_02_wrapper_validates_exact_contract_without_blender(self) -> None:
        observed, row = self.wrapper._load_contract(EXACT[CONTRACT][1])
        self.assertEqual(observed, self.contract)
        self.assertEqual(row["sha256"], EXACT[CONTRACT][1])
        self.assertNotIn("bpy", sys.modules)

    def test_03_attempts_01_and_02_are_exact_and_superseded(self) -> None:
        tables = (
            self.contract["locked_pair_attempt_01_preservation"],
            self.contract["locked_pair_attempt_02_preservation"],
        )
        for table in tables:
            for row in table.values():
                path = ROOT / row["path"]
                value = path.read_bytes()
                self.assertEqual(len(value), row["bytes"])
                self.assertEqual(hashlib.sha256(value).hexdigest(), row["sha256"])
        notice = (ROOT / self.contract["bindings"]["locked_pair_attempt02_supersession"]["path"]).read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("SUPERSEDED", notice.upper())

    def test_04_accepted_v5_exact_graph_and_all_transitive_rows(self) -> None:
        v5 = json.loads((ROOT / self.contract["bindings"]["afes_v5_config"]["path"]).read_text())
        for name, table in self.contract["afes_v5_transitive_rows"].items():
            self.assertEqual(v5[name], table)
            for row in table.values():
                path = ROOT / row["path"]
                value = path.read_bytes()
                self.assertEqual((len(value), hashlib.sha256(value).hexdigest()), (row["bytes"], row["sha256"]))
        self.assertEqual(
            self.contract["accepted_afes_v5_audit"]["audit_sha256"],
            "a739451fbde83ab1202a245640e39b41a11d2973ff91300356883c7c4b06f527",
        )

    def test_05_discovery_is_complete_and_project_imports_are_absent(self) -> None:
        contract_path, paths = self.controller._untrusted_discovery()
        self.assertEqual(contract_path, CONTRACT)
        self.assertEqual(len(paths), 50)
        self.assertIn(Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"), paths)
        for source_path in (CONTROLLER, WRAPPER):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            imports = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(any(name == "tools" or name.startswith("tools.") for name in imports))
        self.assertNotIn("importlib.import_module", CONTROLLER.read_text(encoding="utf-8"))

    def test_06_partial_lock_failure_invokes_no_body(self) -> None:
        calls: list[str] = []

        class Partial:
            def __init__(self) -> None:
                self.active = False
                self.count = 0

            def __enter__(self):
                self.active = True
                return self

            def add(self, path: Path) -> None:
                self.count += 1
                if self.count == 2:
                    raise self_error("partial_lock_failure")

            def __exit__(self, *args):
                self.active = False

        self_error = self.controller.LockedPairV3Error
        with self.assertRaises(self_error):
            self.controller._with_complete_lock_set(
                [CONTRACT, CONTROLLER], lambda locks: calls.append("body"),
                lock_factory=Partial,
            )
        self.assertEqual(calls, [])

    def test_07_ledger_rejects_unlocked_or_same_length_drift(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint/runtime_cache") as temp:
            path = Path(temp) / "row.bin"
            path.write_bytes(b"AAAA")
            locks = FakeLocks([path])
            ledger = self.controller.LockedByteLedger(locks, [path])
            row = {"path": path.relative_to(ROOT).as_posix(), "bytes": 4,
                   "sha256": hashlib.sha256(b"BBBB").hexdigest()}
            with self.assertRaisesRegex(self.controller.LockedPairV3Error, "locked_binding_drift"):
                ledger.read_exact(row, label="same_length_replacement")
            other = Path(temp) / "other.bin"
            other.write_bytes(b"x")
            with self.assertRaisesRegex(self.controller.LockedPairV3Error, "unlocked_path_read_refused"):
                ledger.read_path(other)

    def test_08_parent_private_graph_ignores_hostile_ambient_modules_and_dataclass(self) -> None:
        _, paths = self.controller._untrusted_discovery()
        locks = FakeLocks(paths)
        ledger = self.controller.LockedByteLedger(locks, paths)
        contract = json.loads(CONTRACT.read_text())
        v5 = json.loads((ROOT / contract["bindings"]["afes_v5_config"]["path"]).read_text())
        calls: list[object] = []
        forged = ModuleType("tools.kira_r25_afes_topology_core_v3")
        old = sys.modules.get(forged.__name__)
        sys.modules[forged.__name__] = forged
        try:
            with mock.patch.object(dataclasses, "dataclass", side_effect=lambda *a, **k: calls.append((a, k))):
                receipt, attempt03 = self.controller._load_private_parent_graph(
                    contract, v5, ledger, "a" * 64
                )
            self.assertEqual(calls, [])
            self.assertIsNot(attempt03, forged)
            self.assertNotIn(receipt, sys.modules.values())
            self.assertNotIn(attempt03, sys.modules.values())
        finally:
            if old is None:
                sys.modules.pop(forged.__name__, None)
            else:
                sys.modules[forged.__name__] = old

    def _valid_payload(self) -> tuple[dict[str, object], ModuleType]:
        graph = {
            key: self.contract["afes_v5_transitive_rows"]["bindings"][key]
            for key in (
                "attempt_01_topology_core_execution_dependency",
                "attempt_02_hardening_core_execution_dependency",
                "attempt_03_hardening_core_execution_dependency",
                "canonical_receipt_helper",
            )
        }
        analysis = {"topology_structure": {"full_normalized_topology_sha256": "b" * 64}}
        inner = {
            "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v5",
            "status": "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN",
            "config_observed_unsealed_by_parent": self.contract["bindings"]["afes_v5_config"],
            "private_execution_dependencies": graph,
            "ambient_project_modules_consumed": 0,
            "ambient_dataclasses_decorator_consumed": 0,
            "private_modules_inserted_into_sys_modules": 0,
            "analysis": analysis,
            "topology_sealing": {"measured_full_normalized_topology_sha256": "b" * 64,
                                 "this_receipt_alone_is_acceptance": False},
            "read_only_guards": {"blend_loaded_exactly": True, "blend_clean_before": True,
                "blend_clean_after": True, "data_block_inventory_unchanged": True,
                "operator_calls_by_this_extractor": 0, "edit_calls_by_this_extractor": 0,
                "persistence_calls_by_this_extractor": 0,
                "path_result_writes_by_this_extractor": 0},
        }
        payload = {
            "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v3",
            "status": "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH",
            "execution_contract": {"path": self.wrapper.CONTRACT_RELATIVE_PATH,
                                   "bytes": EXACT[CONTRACT][0], "sha256": EXACT[CONTRACT][1]},
            "accepted_afes_v5_config": self.contract["bindings"]["afes_v5_config"],
            "accepted_afes_v5_extractor": self.contract["bindings"]["afes_v5_extractor"],
            "pair_session_nonce": "c" * 64, "run_nonce": "d" * 64,
            "run_number": 1, "result_pipe_handle": 123, "child_pid": 456,
            "parent_pid": 789, "inner_attempt05_payload": inner,
            "truth_boundary": ["READ_ONLY_FOUNDATION_DIAGNOSTIC"],
        }
        validator = ModuleType("private_validator")
        validator.validate_compact_afes_analysis = lambda value: None
        return payload, validator

    def test_09_authenticated_identity_and_replay_mismatch_fail_closed(self) -> None:
        payload, validator = self._valid_payload()
        inner, digest = self.controller._validate_child_payload(
            payload=payload, run_number=1, pair_session_nonce="c" * 64,
            run_nonce="d" * 64, result_handle=123, child_pid=456,
            parent_pid=789, contract_sha256=EXACT[CONTRACT][1],
            contract=self.contract,
            v5=json.loads((ROOT / self.contract["bindings"]["afes_v5_config"]["path"]).read_text()),
            attempt03=validator,
        )
        self.assertIs(inner, payload["inner_attempt05_payload"])
        self.assertEqual(digest, "b" * 64)
        for key, wrong in (("run_nonce", "e" * 64), ("result_pipe_handle", 124), ("child_pid", 999)):
            replay = dict(payload)
            replay[key] = wrong
            with self.assertRaisesRegex(self.controller.LockedPairV3Error, "authenticated_identity_mismatch"):
                self.controller._validate_child_payload(
                    payload=replay, run_number=1, pair_session_nonce="c" * 64,
                    run_nonce="d" * 64, result_handle=123, child_pid=456,
                    parent_pid=789, contract_sha256=EXACT[CONTRACT][1],
                    contract=self.contract,
                    v5=json.loads((ROOT / self.contract["bindings"]["afes_v5_config"]["path"]).read_text()),
                    attempt03=validator,
                )

    @unittest.skipUnless(os.name == "nt", "Win32 handle classification")
    def test_10_parent_and_child_reject_non_pipe_handle(self) -> None:
        import msvcrt
        with tempfile.TemporaryFile() as stream:
            handle = int(msvcrt.get_osfhandle(stream.fileno()))
            with self.assertRaisesRegex(self.controller.LockedPairV3Error, "not_pipe"):
                self.controller._require_pipe_handle(handle)
            with self.assertRaisesRegex(self.wrapper.R25AfesExecutionV3Error, "not_pipe"):
                self.wrapper._require_pipe(handle)

    def test_11_snapshot_requires_the_complete_active_lock_set(self) -> None:
        incomplete = FakeLocks([CONTRACT])
        with self.assertRaisesRegex(self.controller.LockedPairV3Error, "complete_lock_set"):
            self.controller._snapshot_under_complete_locks([CONTRACT, CONTROLLER], incomplete)
        inactive = FakeLocks([CONTRACT])
        inactive.active = False
        with self.assertRaisesRegex(self.controller.LockedPairV3Error, "active_lock_set"):
            self.controller._snapshot_under_complete_locks([CONTRACT], inactive)

    def test_12_reservation_failure_removes_only_new_empty_root(self) -> None:
        class BrokenReservation:
            @staticmethod
            def reserve(path: Path):
                raise RuntimeError("reservation failed")

        receipt = ModuleType("broken_receipt")
        receipt.WindowsExclusiveReceiptReservation = BrokenReservation
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint/runtime_cache") as temp:
            root = Path(temp) / "attempt_03"
            with self.assertRaisesRegex(RuntimeError, "reservation failed"):
                self.controller._reserve_outcome_without_empty_orphan(root, receipt)
            self.assertFalse(root.exists())

    def test_13_missing_independent_audit_stops_before_lock_or_popen(self) -> None:
        with mock.patch.object(self.controller, "_with_complete_lock_set") as locks, mock.patch.object(
            self.controller.subprocess, "Popen"
        ) as popen:
            with self.assertRaises((FileNotFoundError, self.controller.LockedPairV3Error)):
                self.controller.run_pair(EXACT[CONTRACT][1], "f" * 64)
        locks.assert_not_called()
        popen.assert_not_called()
        self.assertFalse(OUTPUT_ROOT.exists())

    def test_14_bounded_drain_records_overflow_without_unbounded_capture(self) -> None:
        import io
        result: list[object] = []
        event = self.controller.threading.Event()
        self.controller._drain_bounded(io.BytesIO(b"x" * 100), 16, result, event)
        self.assertTrue(event.is_set())
        self.assertEqual(len(result[0]["captured"]), 16)
        self.assertEqual(result[0]["total_bytes"], 100)
        self.assertTrue(result[0]["overflow"])

    def test_15_static_sources_bind_job_tree_and_never_author_body(self) -> None:
        controller = CONTROLLER.read_text(encoding="utf-8")
        wrapper = WRAPPER.read_text(encoding="utf-8")
        for token in (
            "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", "CREATE_SUSPENDED",
            "AssignProcessToJobObject", "NtResumeProcess",
            "TerminateJobObject", "MAX_STDOUT_BYTES", "MAX_STDERR_BYTES",
        ):
            self.assertIn(token, controller)
        self.assertNotIn("bpy.ops", wrapper)
        self.assertNotIn("save_as_mainfile", wrapper)
        self.assertNotIn("--result-path", wrapper)


if __name__ == "__main__":
    unittest.main()
