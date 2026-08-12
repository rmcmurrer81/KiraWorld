from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "Tools" / "run_persistent_blackwell_voice_candidate_v2_acceptance_revision01.py"
ORIGINAL_HARNESS = ROOT / "Tools" / "run_persistent_blackwell_voice_candidate_v2_acceptance.py"
ATTEMPT_01_READINESS = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "full_gpu_v2"
    / "attempt_01"
    / "EAGER_CUDA_READINESS.json"
)
ORIGINAL_HARNESS_SHA256 = "db55950b59c3f0ffa3a2f1831c1cba1b9a1b399d846cdea0ee48ab5e95df6223"

SPEC = importlib.util.spec_from_file_location("persistent_v2_full_gpu_revision01_test", HARNESS)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


class PersistentV2FullGpuRevision01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = harness.load_candidate_config(harness.CONFIG_PATH)
        cls.attempt_01 = json.loads(ATTEMPT_01_READINESS.read_text(encoding="utf-8"))

    def test_actual_attempt_01_260_mib_wddm_gaps_are_valid_and_recorded(self) -> None:
        self.assertEqual(
            harness.validate_eager_cuda_payload(self.attempt_01, config=self.config),
            [],
        )
        before = harness.nvidia_memory_accounting(self.attempt_01["nvidia_before"])
        after = harness.nvidia_memory_accounting(self.attempt_01["nvidia_after"])
        self.assertTrue(before["valid"], before)
        self.assertTrue(after["valid"], after)
        self.assertEqual(before["unreported_or_reserved_gap_mib"], 260)
        self.assertEqual(after["unreported_or_reserved_gap_mib"], 260)
        self.assertEqual(before["maximum_allowed_gap_mib"], 1631.1)
        self.assertIn("not attributed to a process", before["gap_interpretation"])

    def test_overtotal_memory_accounting_is_rejected(self) -> None:
        payload = copy.deepcopy(self.attempt_01)
        row = payload["nvidia_before"]["rows"][0]
        row["free_mib"] = row["total_mib"]
        row["used_mib"] = 1
        evidence = harness.nvidia_memory_accounting(payload["nvidia_before"])
        self.assertFalse(evidence["valid"], evidence)
        self.assertIn(
            "eager_nvidia_before_invalid",
            harness.validate_eager_cuda_payload(payload, config=self.config),
        )

    def test_huge_unreported_gap_is_rejected(self) -> None:
        payload = copy.deepcopy(self.attempt_01)
        row = payload["nvidia_after"]["rows"][0]
        row["free_mib"] = 0
        row["used_mib"] = 0
        evidence = harness.nvidia_memory_accounting(payload["nvidia_after"])
        self.assertFalse(evidence["valid"], evidence)
        self.assertGreater(
            evidence["unreported_or_reserved_gap_mib"],
            evidence["maximum_allowed_gap_mib"],
        )
        self.assertIn(
            "eager_nvidia_after_invalid",
            harness.validate_eager_cuda_payload(payload, config=self.config),
        )

    def test_negative_or_noninteger_values_and_driver_change_are_rejected(self) -> None:
        for key, value in (("free_mib", -1), ("used_mib", 1.5)):
            payload = copy.deepcopy(self.attempt_01)
            payload["nvidia_before"]["rows"][0][key] = value
            self.assertFalse(
                harness.nvidia_memory_accounting(payload["nvidia_before"])["valid"]
            )
        payload = copy.deepcopy(self.attempt_01)
        payload["nvidia_after"]["rows"][0]["driver_version"] = "999.99"
        self.assertIn(
            "eager_nvidia_identity_or_driver_changed",
            harness.validate_eager_cuda_payload(payload, config=self.config),
        )

    def test_original_harness_and_attempt_01_remain_preserved(self) -> None:
        self.assertEqual(harness.sha256_file(ORIGINAL_HARNESS), ORIGINAL_HARNESS_SHA256)
        self.assertEqual(
            harness.sha256_file(ATTEMPT_01_READINESS),
            "a352f59cc3830e558df6a23e9500ca951fd0fc2eec4a9aafb8a27de537701c31",
        )

    def test_static_modes_create_no_attempt_and_import_no_torch(self) -> None:
        before = harness._attempt_names()
        torch_before = "torch" in sys.modules
        result = harness.static_self_check()
        self.assertTrue(result["passed"], result)
        self.assertEqual(before, harness._attempt_names())
        self.assertEqual(torch_before, "torch" in sys.modules)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", str(HARNESS), "--describe"],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["live_execution_performed"])
        self.assertEqual(before, harness._attempt_names())


if __name__ == "__main__":
    unittest.main()
