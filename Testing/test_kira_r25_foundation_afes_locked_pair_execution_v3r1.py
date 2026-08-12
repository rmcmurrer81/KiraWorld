from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3r1.json"
)
CONTROLLER_PATH = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v3r1.py"
WRAPPER_PATH = ROOT / (
    "tools/blender_extract_kira_r25_foundation_afes_"
    "transition_rings_execution_v3r1.py"
)
OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03"
)
AUDIT_PATH = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03/INDEPENDENT_AUDIT.md"
)


def load_private(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


controller = load_private(CONTROLLER_PATH, "_test_locked_pair_v3r1_controller")
wrapper = load_private(WRAPPER_PATH, "_test_locked_pair_v3r1_wrapper")
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def digest(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


class FakeLedger:
    def read_exact(self, row: object, *, label: str = "bound_row"):
        assert isinstance(row, dict), label
        path = ROOT / row["path"]
        value = path.read_bytes()
        if len(value) != row["bytes"] or hashlib.sha256(value).hexdigest() != row["sha256"]:
            raise AssertionError(f"drift:{label}")
        return path.resolve(strict=True), value


class LockedPairAttempt03StaticTests(unittest.TestCase):
    def test_identity_scope_and_execution_remains_audit_gated(self) -> None:
        self.assertEqual(CONFIG["schema"], "kira.avatar.r25.foundation_afes_locked_pair_execution.v3")
        self.assertEqual(CONFIG["attempt_id"], "attempt_03")
        self.assertEqual(
            CONFIG["status"],
            "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
        )
        self.assertFalse(CONFIG["scope"]["blend_mutation_allowed"])
        self.assertFalse(CONFIG["scope"]["blend_save_allowed"])
        self.assertFalse(CONFIG["scope"]["render_allowed"])
        self.assertFalse(CONFIG["scope"]["body_authoring_allowed"])
        self.assertTrue(CONFIG["truth_boundary"][
            "static_package_is_not_execution_authority_until_fresh_independent_audit"
        ])
        self.assertFalse(AUDIT_PATH.exists())
        self.assertFalse(OUTPUT_ROOT.exists())

    def test_every_bound_and_transitive_row_matches_exact_bytes(self) -> None:
        tables = [
            CONFIG["bindings"],
            CONFIG["locked_pair_attempt_01_preservation"],
            CONFIG["locked_pair_attempt_02_preservation"],
            *CONFIG["afes_v5_transitive_rows"].values(),
        ]
        for table in tables:
            for label, row in table.items():
                path = Path(row["path"])
                if not path.is_absolute():
                    path = ROOT / path
                self.assertEqual(digest(path), (row["bytes"], row["sha256"]), label)

    def test_locked_pair_attempts_01_and_02_are_exactly_preserved(self) -> None:
        expected = {
            "locked_pair_attempt01_contract": (4226, "2d814be92de63978ac1b7f2427ea67b8fbea6c21acbe5da1613641a18ed31b32"),
            "locked_pair_attempt01_wrapper": (7666, "57c3894800477a35ed8631168b836541da7703c31b8c4009297213ed80b88131"),
            "locked_pair_attempt01_controller": (18382, "4568bd9fb7b2cc0072d3e97d9fd5603dfa6943dd736c122bae218d2102119fd5"),
            "locked_pair_attempt01_test": (5523, "f8de598e7bf4ec40d5535f73196576419f1498dde50ad4d65f7ac41e1221e145"),
            "locked_pair_attempt02_contract": (5719, "4bae4355ad48a3afc9339434efa1fb7212308674b51401eff513472830163571"),
            "locked_pair_attempt02_wrapper": (8281, "01380a34c065cee1c67ba700d342d22c811aa985aa5722525718aa39d4f56f8e"),
            "locked_pair_attempt02_controller": (31503, "4f1f0413526b6c9449033f070e1a0d46fef965cc6fea6af46f1c1b52461adb06"),
            "locked_pair_attempt02_test": (14895, "dcccf95734812d5d9b5fbad2f0154d1e59bdb690ff7bd465f8a65b5fcb27e56d"),
        }
        for label, expected_digest in expected.items():
            row = CONFIG["bindings"][label]
            self.assertEqual((row["bytes"], row["sha256"]), expected_digest)

    def test_accepted_afes_v5_audit_and_full_tables_are_exact(self) -> None:
        v5 = json.loads((ROOT / CONFIG["bindings"]["afes_v5_config"]["path"]).read_text())
        self.assertEqual(
            CONFIG["accepted_afes_v5_audit"]["audit_sha256"],
            "a739451fbde83ab1202a245640e39b41a11d2973ff91300356883c7c4b06f527",
        )
        for name, table in CONFIG["afes_v5_transitive_rows"].items():
            self.assertEqual(table, v5[name])
        observed = {name: v5[name] for name in CONFIG["afes_v5_exact_contract_sections"]}
        self.assertEqual(observed, CONFIG["afes_v5_exact_contract_sections"])

    def test_unknown_provenance_v3_prototypes_are_not_bound(self) -> None:
        paths = {row["path"] for row in CONFIG["bindings"].values()}
        self.assertNotIn(
            "tools/run_kira_r25_foundation_afes_locked_pair_v3.py", paths
        )
        self.assertNotIn(
            "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3.py",
            paths,
        )
        self.assertIn(str(CONTROLLER_PATH.relative_to(ROOT)).replace("\\", "/"), paths)
        self.assertIn(str(WRAPPER_PATH.relative_to(ROOT)).replace("\\", "/"), paths)

    def test_no_project_module_import_exists_in_parent_or_wrapper(self) -> None:
        for path in (CONTROLLER_PATH, WRAPPER_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name == "tools" or alias.name.startswith("tools.") for alias in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "") == "tools" or (node.module or "").startswith("tools."))

    def test_child_checks_pipe_before_contract_or_blender(self) -> None:
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        main = source[source.index("def main()") :]
        self.assertLess(main.index("_require_pipe(values.result_handle)"), main.index("build_payload("))
        self.assertNotIn("import bpy", source[: source.index("def _real_blender_bpy")])

    def test_partial_lock_failure_calls_no_verifier_or_body(self) -> None:
        calls: list[str] = []

        class Locks:
            active = False
            locked_paths: list[Path] = []

            def __enter__(self):
                self.active = True
                return self

            def add(self, path: Path) -> None:
                calls.append(f"add:{path.name}")
                if len(calls) == 2:
                    raise controller.LockedPairV3Error("synthetic_lock_failure")
                self.locked_paths.append(path)

            def __exit__(self, *_args):
                self.active = False

        invoked = False

        def body(_locks):
            nonlocal invoked
            invoked = True

        with self.assertRaisesRegex(controller.LockedPairV3Error, "synthetic_lock_failure"):
            controller._with_complete_lock_set(
                [CONTROLLER_PATH, WRAPPER_PATH], body, lock_factory=Locks
            )
        self.assertFalse(invoked)

    def test_same_length_replacement_is_rejected_by_locked_ledger(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary_root = Path(temporary)
            target = temporary_root / "same.bin"
            target.write_bytes(b"ABCD")
            relative = target.relative_to(ROOT).as_posix()
            row = {
                "path": relative, "bytes": 4,
                "sha256": hashlib.sha256(b"ABCD").hexdigest(),
            }
            target.write_bytes(b"WXYZ")
            locks = SimpleNamespace(active=True, locked_paths=[target])
            ledger = controller.LockedByteLedger(locks, [target])
            with self.assertRaisesRegex(controller.LockedPairV3Error, "locked_binding_drift"):
                ledger.read_exact(row, label="replacement")

    def test_locked_ledger_retains_one_authoritative_read(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            target = Path(temporary) / "one.bin"
            target.write_bytes(b"retained")
            row = {
                "path": target.relative_to(ROOT).as_posix(),
                "bytes": 8,
                "sha256": hashlib.sha256(b"retained").hexdigest(),
            }
            locks = SimpleNamespace(active=True, locked_paths=[target])
            ledger = controller.LockedByteLedger(locks, [target])
            first = ledger.read_exact(row, label="one")[1]
            second = ledger.read_exact(row, label="two")[1]
            self.assertIs(first, second)
            self.assertEqual(ledger.before_snapshot()[str(target.resolve())][
                "authoritative_physical_reads"
            ], 1)

    def test_after_snapshot_requires_active_complete_lock_set(self) -> None:
        with self.assertRaisesRegex(controller.LockedPairV3Error, "active_lock"):
            controller._snapshot_under_complete_locks(
                [CONTROLLER_PATH], SimpleNamespace(active=False, locked_paths=[CONTROLLER_PATH])
            )
        with self.assertRaisesRegex(controller.LockedPairV3Error, "complete_lock"):
            controller._snapshot_under_complete_locks(
                [CONTROLLER_PATH], SimpleNamespace(active=True, locked_paths=[])
            )

    def test_parent_and_child_reject_non_pipe_handle(self) -> None:
        if os.name != "nt":
            self.skipTest("Win32 handle test")
        import msvcrt

        with tempfile.TemporaryFile() as stream:
            handle = int(msvcrt.get_osfhandle(stream.fileno()))
            with self.assertRaisesRegex(controller.LockedPairV3Error, "not_pipe"):
                controller._require_pipe_handle(handle)
            with self.assertRaisesRegex(wrapper.R25AfesExecutionV3Error, "not_pipe"):
                wrapper._require_pipe(handle)

    def test_frame_stdout_and_stderr_bounds_are_independent(self) -> None:
        for limit in (5, 7, 11):
            result: list[object] = []
            overflow = threading.Event()
            controller._drain_bounded(io.BytesIO(b"x" * (limit + 3)), limit, result, overflow)
            self.assertTrue(overflow.is_set())
            self.assertEqual(result[0]["captured"], b"x" * limit)
            self.assertTrue(result[0]["overflow"])

    def test_exact_child_only_cleanup(self) -> None:
        process = mock.Mock()
        process.poll.return_value = None
        process.wait.return_value = 0
        controller._terminate_exact_child(process)
        process.terminate.assert_called_once_with()
        process.kill.assert_not_called()

    def test_direct_popen_failure_does_not_start_blender_or_leave_frame_thread(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows process contract")
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(
                controller.subprocess, "Popen", side_effect=OSError("synthetic_popen")
            ) as popen:
                with self.assertRaisesRegex(OSError, "synthetic_popen"):
                    controller._run_child(
                        contract=CONFIG,
                        v5={"bindings": CONFIG["afes_v5_transitive_rows"]["bindings"]},
                        contract_sha256=hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                        run_number=1, pair_session_nonce="7" * 64,
                        run_nonce="8" * 64, evidence_root=Path(temporary),
                        receipt=SimpleNamespace(), attempt03=SimpleNamespace(),
                    )
        popen.assert_called_once()

    def test_private_parent_graph_ignores_ambient_security_spoofs(self) -> None:
        v5 = json.loads((ROOT / CONFIG["bindings"]["afes_v5_config"]["path"]).read_text())
        fake_names = [
            "tools.kira_r25_afes_topology_core",
            "tools.kira_r25_afes_topology_core_v2",
            "tools.kira_r25_afes_topology_core_v3",
            "tools.kira_r25_canonical_receipt",
            "dataclasses",
        ]
        fakes = {name: ModuleType(name) for name in fake_names}
        with mock.patch.dict(sys.modules, fakes, clear=False):
            receipt, attempt03 = controller._load_private_parent_graph(
                CONFIG, v5, FakeLedger(), "1" * 64
            )
        self.assertNotIn(receipt, fakes.values())
        self.assertNotIn(attempt03, fakes.values())
        self.assertTrue(callable(attempt03.validate_compact_afes_analysis))
        self.assertNotIn(receipt, sys.modules.values())
        self.assertNotIn(attempt03, sys.modules.values())

    def test_private_child_extractor_ignores_ambient_extractor(self) -> None:
        fake_bpy = ModuleType("bpy")
        fake_ambient = ModuleType("tools.blender_extract_kira_r25_foundation_afes_transition_rings_v5")
        binding = CONFIG["bindings"]["afes_v5_extractor"]
        path = ROOT / binding["path"]
        retained = {"afes_v5_extractor": (path.resolve(), path.read_bytes())}
        with mock.patch.dict(sys.modules, {fake_ambient.__name__: fake_ambient}, clear=False):
            private = wrapper._load_private_v5_extractor(
                CONFIG, fake_bpy, "2" * 64, retained
            )
        self.assertIsNot(private, fake_ambient)
        self.assertNotIn(private, sys.modules.values())
        self.assertTrue(callable(private.extract_payload))

    def _valid_payload(self):
        topology = "a" * 64
        graph = {
            key: CONFIG["afes_v5_transitive_rows"]["bindings"][key]
            for key in (
                "attempt_01_topology_core_execution_dependency",
                "attempt_02_hardening_core_execution_dependency",
                "attempt_03_hardening_core_execution_dependency",
                "canonical_receipt_helper",
            )
        }
        inner = {
            "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v5",
            "status": "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN",
            "config_observed_unsealed_by_parent": CONFIG["bindings"]["afes_v5_config"],
            "private_execution_dependencies": graph,
            "ambient_project_modules_consumed": 0,
            "ambient_dataclasses_decorator_consumed": 0,
            "private_modules_inserted_into_sys_modules": 0,
            "analysis": {"topology_structure": {"full_normalized_topology_sha256": topology}},
            "topology_sealing": {
                "measured_full_normalized_topology_sha256": topology,
                "this_receipt_alone_is_acceptance": False,
            },
            "read_only_guards": {
                "blend_loaded_exactly": True,
                "blend_clean_before": True,
                "blend_clean_after": True,
                "data_block_inventory_unchanged": True,
                "operator_calls_by_this_extractor": 0,
                "edit_calls_by_this_extractor": 0,
                "persistence_calls_by_this_extractor": 0,
                "path_result_writes_by_this_extractor": 0,
            },
        }
        return {
            "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v3",
            "status": "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH",
            "execution_contract": {
                "path": str(CONFIG_PATH.relative_to(ROOT)).replace("\\", "/"),
                "bytes": CONFIG_PATH.stat().st_size,
                "sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
            },
            "accepted_afes_v5_config": CONFIG["bindings"]["afes_v5_config"],
            "accepted_afes_v5_extractor": CONFIG["bindings"]["afes_v5_extractor"],
            "pair_session_nonce": "3" * 64,
            "run_nonce": "4" * 64,
            "run_number": 1,
            "result_pipe_handle": 123,
            "child_pid": 456,
            "parent_pid": os.getpid(),
            "inner_attempt05_payload": inner,
            "truth_boundary": [
                "READ_ONLY_FOUNDATION_DIAGNOSTIC",
                "NO_BLEND_MUTATION_OR_SAVE",
                "NO_RENDER_OR_EXPORT",
                "NO_CANDIDATE_OR_BODY_AUTHORING",
                "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
            ],
        }

    def test_authenticated_child_payload_accepts_exact_compact_evidence(self) -> None:
        payload = self._valid_payload()
        validator = SimpleNamespace(validate_compact_afes_analysis=lambda _value: None)
        inner, topology = controller._validate_child_payload(
            payload=payload, run_number=1, pair_session_nonce="3" * 64,
            run_nonce="4" * 64, result_handle=123, child_pid=456,
            contract_sha256=payload["execution_contract"]["sha256"],
            contract=CONFIG,
            v5={"bindings": CONFIG["afes_v5_transitive_rows"]["bindings"]},
            attempt03=validator,
        )
        self.assertIs(inner, payload["inner_attempt05_payload"])
        self.assertEqual(topology, "a" * 64)

    def test_nonce_contract_config_and_topology_drift_fail_closed(self) -> None:
        validator = SimpleNamespace(validate_compact_afes_analysis=lambda _value: None)
        cases = []
        for mutate in ("nonce", "contract", "config", "topology"):
            payload = self._valid_payload()
            if mutate == "nonce":
                payload["run_nonce"] = "5" * 64
            elif mutate == "contract":
                payload["execution_contract"]["sha256"] = "b" * 64
            elif mutate == "config":
                payload["accepted_afes_v5_config"] = dict(payload["accepted_afes_v5_config"])
                payload["accepted_afes_v5_config"]["sha256"] = "c" * 64
            else:
                payload["inner_attempt05_payload"]["topology_sealing"][
                    "measured_full_normalized_topology_sha256"
                ] = "d" * 64
            cases.append(payload)
        contract_sha = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
        for payload in cases:
            with self.assertRaises(controller.LockedPairV3Error):
                controller._validate_child_payload(
                    payload=payload, run_number=1, pair_session_nonce="3" * 64,
                    run_nonce="4" * 64, result_handle=123, child_pid=456,
                    contract_sha256=contract_sha, contract=CONFIG,
                    v5={"bindings": CONFIG["afes_v5_transitive_rows"]["bindings"]},
                    attempt03=validator,
                )

    def test_canonical_frame_rejects_invalid_truncated_and_trailing_data(self) -> None:
        v5 = json.loads((ROOT / CONFIG["bindings"]["afes_v5_config"]["path"]).read_text())
        receipt, _attempt03 = controller._load_private_parent_graph(
            CONFIG, v5, FakeLedger(), "6" * 64
        )
        frame = receipt.encode_receipt_frame({"a": 1})
        for invalid in (b"", frame[:-1], frame + b"x"):
            with self.assertRaises(Exception):
                receipt.decode_receipt_frame(invalid)

    def test_audit_binding_is_out_of_band_and_fail_closed(self) -> None:
        gate = CONFIG["controller_audit_gate"]
        self.assertTrue(gate["sha256_supplied_out_of_band"])
        self.assertTrue(gate["must_bind_contract_controller_and_wrapper_hashes"])
        self.assertNotIn("controller_audit", CONFIG["bindings"])
        signature = str(__import__("inspect").signature(controller.run_pair))
        self.assertIn("accepted_controller_audit_sha256", signature)
        self.assertIn("accepted_controller_audit_sha256", str(
            __import__("inspect").signature(controller._verify_everything_under_locks)
        ))

    def test_parent_reserves_outcome_before_popen_and_persists_raw_before_decode(self) -> None:
        source = CONTROLLER_PATH.read_text(encoding="utf-8")
        run_pair_source = source[source.index("def run_pair") :]
        self.assertLess(
            run_pair_source.index("WindowsExclusiveReceiptReservation.reserve"),
            run_pair_source.index("_run_child("),
        )
        child_source = source[source.index("def _run_child") : source.index("def run_pair")]
        self.assertLess(child_source.index("run_{run_number:02d}_raw_frame.bin"), child_source.index("decode_receipt_frame"))

    def test_exact_command_and_minimal_environment_are_frozen(self) -> None:
        self.assertEqual(CONFIG["process_contract"], controller._expected_process_contract())
        self.assertEqual(CONFIG["pair_acceptance"], controller._expected_pair_contract())
        self.assertEqual(CONFIG["truth_boundary"], controller._expected_truth_boundary())
        self.assertFalse(CONFIG["process_contract"]["shell"])
        self.assertTrue(CONFIG["process_contract"]["close_fds"])
        self.assertEqual(CONFIG["process_contract"]["stdin"], "DEVNULL")

    def test_static_verification_created_no_execution_evidence(self) -> None:
        self.assertFalse(OUTPUT_ROOT.exists())


if __name__ == "__main__":
    unittest.main()
