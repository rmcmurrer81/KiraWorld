"""Different-agent hostile static probes for sealed Blackwell V11.

No live branch is entered.  The only child process used is the sealed
standard-library static fixture explicitly allowed by the V11 contract.
"""

from __future__ import annotations

import copy
import ctypes
import hashlib
import importlib
import json
import math
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PACKAGE = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11"
SEAL = PACKAGE / "STATIC_SEAL_MANIFEST.json"
AUTHOR_CHECKPOINT = (
    ROOT
    / "RecoverySprint/continuation_20260811/"
    "blackwell_v11_typed_memory_integration_static_preparation/attempt_01/CHECKPOINT.md"
)
AUTHOR_RESULT = AUTHOR_CHECKPOINT.with_name("AUTHOR_STATIC_TEST_RESULT.json")

EXPECTED_SEAL_SHA256 = "dfa12cb753721d5bb8553dd34509698f12b36ba846a049bc96cd182147b32b20"
EXPECTED_AUTHOR_CHECKPOINT_SHA256 = (
    "52601c5f8ca0a3e608570326a6621cc1796d3d862437133ee29da9471f073788"
)
EXPECTED_AUTHOR_RESULT_SHA256 = (
    "ec2ccfd709be0c39ec56192627acea1496ac2a3bbb6bf6f8312381b91d83dc19"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class FakeFunction:
    def __init__(self, result, callback=None):
        self.result = result
        self.callback = callback
        self.argtypes = None
        self.restype = None
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        if self.callback is not None:
            self.callback(*args)
        return self.result


class FakeKernel32:
    def __init__(self, *, status=1, process=1, status_callback=None):
        self.GlobalMemoryStatusEx = FakeFunction(status, status_callback)
        self.GetCurrentProcess = FakeFunction(process)


class FakePsapi:
    def __init__(self, *, memory=1, memory_callback=None):
        self.GetProcessMemoryInfo = FakeFunction(memory, memory_callback)


class BlackwellV11IndependentHostileAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11.candidate_contract"
        )
        cls.worker = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11.worker_entry"
        )
        cls.integration = importlib.import_module(
            "Core.persistent_blackwell_voice_integration_v11"
        )
        cls.memory = importlib.import_module("Core.blackwell_v10_windows_memory")

    def test_01_exact_seal_author_evidence_and_closure(self):
        self.assertEqual(sha256_file(SEAL), EXPECTED_SEAL_SHA256)
        self.assertEqual(
            sha256_file(AUTHOR_CHECKPOINT), EXPECTED_AUTHOR_CHECKPOINT_SHA256
        )
        self.assertEqual(sha256_file(AUTHOR_RESULT), EXPECTED_AUTHOR_RESULT_SHA256)
        config = self.contract.load_canonical_config()
        sealed = self.contract.verify_seal_manifest(config, SEAL)
        self.assertEqual(len(sealed["files"]), 6)
        self.assertEqual(len(self.contract.verify_preserved_bytes(config)), 14)

    def test_02_strict_config_rejects_type_unknown_duplicate_and_nonfinite(self):
        config = self.contract.load_canonical_config()
        changed = copy.deepcopy(config)
        changed["future_live_attempt_authorized"] = 0
        with self.assertRaises(self.contract.V11ContractError):
            self.contract._validate_config(changed)
        changed = copy.deepcopy(config)
        changed["static_test_contract"]["unknown"] = False
        with self.assertRaises(self.contract.V11ContractError):
            self.contract._validate_config(changed)
        with self.assertRaises(self.contract.V11ContractError):
            self.contract._strict_json(b'{"a":1,"a":2}')
        with self.assertRaises(self.contract.V11ContractError):
            self.contract._strict_json(b'{"value":NaN}')

    def test_03_v10_authority_is_static_only_and_exact(self):
        value = self.contract.verify_v10_static_audit(
            self.contract.load_canonical_config()
        )
        self.assertEqual(
            value["verdict"],
            "ACCEPT_V10_STATIC_MEMORY_REPAIR_FOR_FUTURE_HARNESS_AUTHORING_ONLY",
        )
        self.assertIs(value["static_only"], True)
        self.assertIs(value["live_authorized"], False)

    def test_04_parent_and_direct_worker_refuse_live_before_prepare_or_process(self):
        with patch.object(
            self.integration.BlackwellV11Coordinator,
            "_v9_process",
            side_effect=AssertionError("no process may be constructed"),
        ):
            with self.assertRaises(self.contract.V11ContractError):
                self.integration.BlackwellV11Coordinator.bounded_engineering_candidate()
        original = list(sys.argv)
        try:
            sys.argv = ["worker_entry.py", "--live", "--nonce", token("direct-live")]
            with patch.object(
                self.worker,
                "prepare_live_memory_integration",
                side_effect=AssertionError("typed integration must remain unreachable"),
            ):
                self.assertEqual(self.worker.main(), 93)
        finally:
            sys.argv = original

    def test_05_worker_modes_and_audit_argument_fail_closed(self):
        audit = token("audit")
        for argv in (
            [],
            ["--live", "--static-fixture"],
        ):
            original = list(sys.argv)
            try:
                sys.argv = ["worker_entry.py", *argv]
                self.assertEqual(self.worker.main(), 91)
            finally:
                sys.argv = original
        delegated, observed = self.worker._extract_v11_audit_and_strip(
            ["--static-fixture", "--accepted-v11-audit-sha256", audit]
        )
        self.assertEqual(observed, audit)
        self.assertNotIn("--accepted-v11-audit-sha256", delegated)
        with self.assertRaises(self.contract.V11ContractError):
            self.worker._extract_v11_audit_and_strip(
                ["--live", "--accepted-v11-audit-sha256", "A" * 64]
            )

    def test_06_capability_check_is_replayable_opt_in_not_live_authority(self):
        config = self.contract.load_canonical_config()
        key = config["engineering_run_opt_in"]
        value = config["engineering_run_opt_in_value"]
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(self.contract.V11ContractError):
                self.contract.verify_per_run_live_capability(config)
        with patch.dict(os.environ, {key: value}, clear=True):
            self.contract.verify_per_run_live_capability(config)
            self.contract.verify_per_run_live_capability(config)
        self.assertFalse(config["future_live_attempt_authorized"])

    def test_07_ctypes_prototypes_are_pointer_width_and_declared_before_calls(self):
        kernel32 = FakeKernel32()
        psapi = FakePsapi()
        self.memory._configure_windows_memory_apis(kernel32, psapi)
        self.assertEqual(kernel32.GetCurrentProcess.argtypes, [])
        self.assertIs(kernel32.GetCurrentProcess.restype, self.memory.wintypes.HANDLE)
        self.assertIs(
            psapi.GetProcessMemoryInfo.argtypes[0], self.memory.wintypes.HANDLE
        )
        self.assertIs(
            psapi.GetProcessMemoryInfo.argtypes[2], self.memory.wintypes.DWORD
        )
        self.assertIs(psapi.GetProcessMemoryInfo.restype, self.memory.wintypes.BOOL)

    def test_08_native_failures_are_fail_closed_with_exact_stage(self):
        with self.assertRaisesRegex(
            self.memory.V10MemoryTelemetryError,
            "GlobalMemoryStatusEx failed: WinError 8",
        ):
            self.memory._read_windows_memory_mib(
                FakeKernel32(status=0), FakePsapi(), get_last_error=lambda: 8
            )
        with self.assertRaisesRegex(
            self.memory.V10MemoryTelemetryError,
            "GetCurrentProcess returned a null handle: WinError 6",
        ):
            self.memory._read_windows_memory_mib(
                FakeKernel32(process=None), FakePsapi(), get_last_error=lambda: 6
            )
        with self.assertRaisesRegex(
            self.memory.V10MemoryTelemetryError,
            "GetProcessMemoryInfo failed: WinError 6",
        ):
            self.memory._read_windows_memory_mib(
                FakeKernel32(), FakePsapi(memory=0), get_last_error=lambda: 6
            )

    def test_09_invalid_memory_relations_are_rejected(self):
        def status_callback(pointer):
            status = ctypes.cast(
                pointer, ctypes.POINTER(self.memory._MEMORYSTATUSEX)
            ).contents
            status.ullTotalPageFile = 1024
            status.ullAvailPageFile = 2048
            status.ullAvailPhys = 1024

        def memory_callback(_handle, pointer, _size):
            counters = ctypes.cast(
                pointer, ctypes.POINTER(self.memory._PROCESS_MEMORY_COUNTERS)
            ).contents
            counters.WorkingSetSize = 1024

        with self.assertRaisesRegex(
            self.memory.V10MemoryTelemetryError, "non-finite or invalid"
        ):
            self.memory._read_windows_memory_mib(
                FakeKernel32(status_callback=status_callback),
                FakePsapi(memory_callback=memory_callback),
            )

    def test_10_real_typed_current_process_probe_is_finite(self):
        values = self.memory.windows_memory_mib()
        self.assertEqual(len(values), 4)
        self.assertTrue(all(type(value) is float for value in values))
        self.assertTrue(all(math.isfinite(value) and value >= 0 for value in values))
        self.assertGreater(values[0], 0)
        self.assertGreater(values[2], 0)
        self.assertLessEqual(values[1], values[2])

    def test_11_changed_adapter_file_is_rejected(self):
        fake = types.SimpleNamespace(
            __file__=str(PACKAGE / "worker_entry.py"),
            _windows_memory_mib=lambda: None,
        )
        with self.assertRaises(self.memory.V10MemoryTelemetryError):
            self.memory.install_into_exact_v8_live_adapter(fake)

    def test_12_exact_file_string_must_not_let_a_forged_module_object_pass(self):
        def _windows_memory_mib():
            return None

        fake = types.SimpleNamespace(
            __file__=str(
                ROOT
                / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/"
                "live_adapter.py"
            ),
            _windows_memory_mib=_windows_memory_mib,
        )
        with self.assertRaises(self.memory.V10MemoryTelemetryError):
            self.memory.install_into_exact_v8_live_adapter(fake)

    def test_13_v11_prepare_must_not_accept_poisoned_adapter_module_object(self):
        module_name = (
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter"
        )
        package = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8"
        )
        sentinel = object()
        previous_module = sys.modules.get(module_name, sentinel)
        previous_attribute = getattr(package, "live_adapter", sentinel)

        def _windows_memory_mib():
            return None

        fake = types.ModuleType(module_name)
        fake.__file__ = str(
            ROOT
            / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py"
        )
        fake._windows_memory_mib = _windows_memory_mib
        try:
            sys.modules[module_name] = fake
            package.live_adapter = fake
            with patch.object(
                self.contract,
                "verify_future_fresh_audit_authorization",
                return_value={"static_only": True, "live_authorized": False},
            ), patch.object(
                self.contract, "verify_per_run_live_capability", return_value=None
            ):
                with self.assertRaises(self.contract.V11ContractError):
                    self.worker.prepare_live_memory_integration(token("future-audit"))
        finally:
            if previous_module is sentinel:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous_module
            if previous_attribute is sentinel:
                try:
                    delattr(package, "live_adapter")
                except AttributeError:
                    pass
            else:
                package.live_adapter = previous_attribute

    def test_14_static_topology_binds_identity_rejects_replay_and_cleans_handles(self):
        coordinator = self.integration.BlackwellV11Coordinator.static_fixture_candidate(
            nonce=token("independent-static-topology")
        )
        try:
            started = coordinator.start()
            self.assertNotEqual(started["root_pid"], started["worker_pid"])
            self.assertEqual(
                started["worker_direct_parent_pid"], started["root_pid"]
            )
            self.assertTrue(started["launcher_process_handle_owned"])
            self.assertTrue(started["worker_process_handle_owned"])
            self.assertTrue(started["worker_child_job_proof"]["same_retained_job"])
            self.assertTrue(started["worker_child_job_proof"]["kill_on_close"])
            first = coordinator._invoke("fixture_echo", {"sequence": 1})
            second = coordinator._invoke("fixture_echo", {"sequence": 2})
            self.assertNotEqual(first["request_id"], second["request_id"])
            self.assertEqual(first["worker_pid"], started["worker_pid"])
            self.assertEqual(
                first["process_identity_digest"],
                started["worker_process_identity_digest"],
            )
        finally:
            cleanup = coordinator.close()
        self.assertTrue(cleanup["root_exited"])
        self.assertTrue(cleanup["worker_child_exited"])
        self.assertTrue(cleanup["entire_bound_tree_exited"])
        self.assertTrue(cleanup["worker_child_handle_closed"])
        self.assertTrue(cleanup["job_handle_closed"])
        self.assertTrue(cleanup["root_standard_streams_closed"])
        self.assertEqual(cleanup["errors"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
