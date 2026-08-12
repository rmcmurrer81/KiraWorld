from __future__ import annotations

import ctypes
import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from ctypes import wintypes
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "Core/blackwell_v10_windows_memory.py"
CONFIG_PATH = (
    ROOT
    / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v10/candidate_config.json"
)
SEAL_PATH = CONFIG_PATH.with_name("STATIC_SEAL_MANIFEST.json")
V8_ADAPTER_PATH = (
    ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py"
)


class _FakeFunction:
    def __init__(self, result):
        self.result = result
        self.argtypes = None
        self.restype = None
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.result


class _FakeKernel32:
    def __init__(self, *, status=1, process=1):
        self.GlobalMemoryStatusEx = _FakeFunction(status)
        self.GetCurrentProcess = _FakeFunction(process)


class _FakePsapi:
    def __init__(self, *, memory=1):
        self.GetProcessMemoryInfo = _FakeFunction(memory)


class BlackwellV10HostileStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module("Core.blackwell_v10_windows_memory")
        cls.contract = importlib.import_module(
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v10.candidate_contract"
        )

    def test_01_candidate_is_inactive_and_static_only(self):
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertFalse(value["production_routing_authorized"])
        self.assertFalse(value["live_execution_authorized_by_this_candidate"])
        self.assertFalse(value["playback_authorized_by_this_candidate"])
        self.assertFalse(value["current_production_route_changed"])
        self.assertFalse(value["worker_integration_implemented"])
        self.assertFalse(value["future_live_attempt_authorized"])

    def test_02_import_is_inert_and_does_not_load_heavy_modules(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "import torch", "import ollama", "subprocess", "winsound",
            "import chatterbox", "import bpy", "OpenProcess(", "urllib",
        ):
            self.assertNotIn(forbidden, source)
        for name in ("torch", "bpy", "chatterbox"):
            self.assertNotIn(name, sys.modules)

    def test_03_exact_v8_failure_source_has_untyped_pointer_calls(self):
        source = V8_ADAPTER_PATH.read_text(encoding="utf-8")
        start = source.index("def _windows_memory_mib")
        end = source.index("\n\nclass LiveBackendV8", start)
        body = source[start:end]
        self.assertIn("kernel32.GetCurrentProcess()", body)
        self.assertIn("psapi.GetProcessMemoryInfo(", body)
        self.assertNotIn("GetCurrentProcess.restype", body)
        self.assertNotIn("GetProcessMemoryInfo.argtypes", body)

    def test_04_v10_declares_pointer_width_prototypes_before_calls(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        configure = source.index("def _configure_windows_memory_apis")
        read = source.index("def _read_windows_memory_mib")
        self.assertLess(
            source.index("GetCurrentProcess.restype = wintypes.HANDLE", configure), read
        )
        self.assertLess(source.index("GetProcessMemoryInfo.argtypes", configure), read)
        self.assertIn("GetProcessMemoryInfo.restype = wintypes.BOOL", source)

    def test_05_prototype_assignment_is_exact(self):
        kernel32 = _FakeKernel32()
        psapi = _FakePsapi()
        self.module._configure_windows_memory_apis(kernel32, psapi)
        self.assertEqual(kernel32.GetCurrentProcess.argtypes, [])
        self.assertIs(kernel32.GetCurrentProcess.restype, wintypes.HANDLE)
        self.assertEqual(psapi.GetProcessMemoryInfo.argtypes[0], wintypes.HANDLE)
        self.assertIs(psapi.GetProcessMemoryInfo.argtypes[2], wintypes.DWORD)
        self.assertIs(psapi.GetProcessMemoryInfo.restype, wintypes.BOOL)

    @unittest.skipUnless(os.name == "nt", "Windows-only regression")
    def test_06_exact_untyped_regression_is_winerror_6_and_typed_probe_succeeds(self):
        module = self.module
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        counters = module._PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        ctypes.set_last_error(0)
        untyped = psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        self.assertEqual(untyped, 0)
        self.assertEqual(ctypes.get_last_error(), 6)
        values = module.windows_memory_mib()
        self.assertEqual(len(values), 4)
        self.assertGreater(values[0], 0)
        self.assertGreater(values[2], 0)
        self.assertLessEqual(values[1], values[2])

    def test_07_native_failures_keep_exact_winerror(self):
        kernel32 = _FakeKernel32()
        psapi = _FakePsapi(memory=0)
        with self.assertRaisesRegex(
            self.module.V10MemoryTelemetryError,
            r"GetProcessMemoryInfo failed: WinError 6",
        ):
            self.module._read_windows_memory_mib(
                kernel32, psapi, get_last_error=lambda: 6
            )

    def test_08_changed_v8_adapter_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / "live_adapter.py"
            changed.write_text("changed", encoding="utf-8")
            fake = types.SimpleNamespace(
                __file__=str(changed), _windows_memory_mib=lambda: None
            )
            with self.assertRaisesRegex(
                self.module.V10MemoryTelemetryError,
                "exact preserved v8 live-adapter bytes are absent",
            ):
                self.module.install_into_exact_v8_live_adapter(fake)

    def test_09_preserved_attempt_and_boundary_bytes_match(self):
        config = self.contract.load_canonical_config()
        observed = self.contract.verify_preserved_bytes(config)
        self.assertEqual(len(observed), 15)

    def test_10_seal_matches_exact_files(self):
        config = self.contract.load_canonical_config()
        seal = self.contract.verify_seal_manifest(config, SEAL_PATH)
        self.assertFalse(seal["live_execution_authorized"])
        self.assertFalse(seal["playback_authorized"])

    def test_11_missing_fresh_audit_fails_closed(self):
        config = self.contract.load_canonical_config()
        with self.assertRaises(self.contract.V10ContractError):
            self.contract.verify_fresh_audit_authorization(
                config, expected_audit_sha256="0" * 64
            )

    def test_12_production_routing_is_preserved(self):
        config = self.contract.load_canonical_config()
        routing = ROOT / "Voice/sidecars/kira_approved_voice_routing.json"
        self.assertEqual(
            self.contract.sha256_file(routing),
            config["preserved_failure_boundary"][
                "Voice/sidecars/kira_approved_voice_routing.json"
            ],
        )


if __name__ == "__main__":
    unittest.main()
