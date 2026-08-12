from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
if str(CANDIDATE_ROOT) not in sys.path:
    sys.path.insert(0, str(CANDIDATE_ROOT))

import candidate_client
import candidate_contract


TOOL_PATH = ROOT / "tools" / "run_blackwell_openblas_import_ab_probe.py"
REPORT_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_attempt07_openblas_import_ab_probe"
    / "attempt_01"
    / "ATTEMPT07_OPENBLAS_IMPORT_AB_REPORT.json"
)
REPORT_SHA256 = "008b04fbc89a606fff6713a2c1e2b858298eeb4da03257d5a082d190f5d4e94d"
RESTORED_CONFIG_SHA256 = "8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57"
PROBE_TOOL_SHA256 = "6e700a7d33ef0d7f7b4a71cabda10afbeeb754e83a2d429fe334872d7c06b1ec"

SPEC = importlib.util.spec_from_file_location("blackwell_openblas_attempt07_probe", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class BlackwellOpenBlasAttempt07Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(candidate_contract.CONFIG_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_live_attempt01_is_preserved_exactly(self) -> None:
        self.assertEqual(candidate_contract.sha256_file(REPORT_PATH), REPORT_SHA256)
        self.assertEqual(candidate_contract.sha256_file(TOOL_PATH), PROBE_TOOL_SHA256)
        self.assertEqual(self.report["probe_tool_sha256"], PROBE_TOOL_SHA256)
        self.assertEqual(
            self.report["assessment"]["status"],
            "BOUNDED_AB_DOES_NOT_SUPPORT_ATTEMPT07_ACCEPTANCE",
        )
        self.assertFalse(
            self.report["assessment"]["openblas_single_thread_hypothesis_supported"]
        )
        self.assertFalse(
            self.report["assessment"]["ready_for_separate_full_attempt07_acceptance"]
        )

    def test_live_control_and_treatment_were_both_fast(self) -> None:
        control = self.report["arms"][probe.CONTROL]
        treatment = self.report["arms"][probe.TREATMENT]
        self.assertFalse(control["timed_out"])
        self.assertFalse(treatment["timed_out"])
        self.assertEqual(control["owned_process_exit_code"], 0)
        self.assertEqual(treatment["owned_process_exit_code"], 0)
        self.assertAlmostEqual(control["result"]["import_elapsed_seconds"], 1.074988, places=6)
        self.assertAlmostEqual(treatment["result"]["import_elapsed_seconds"], 0.964216, places=6)

    def test_unsupported_candidate_policy_was_fully_removed(self) -> None:
        self.assertNotIn("native_thread_limits", self.config)
        self.assertEqual(
            candidate_contract.sha256_file(candidate_contract.CONFIG_PATH),
            RESTORED_CONFIG_SHA256,
        )
        hashes = candidate_contract.verify_candidate_config(self.config)
        self.assertEqual(
            hashes["candidate_client"],
            candidate_contract.sha256_file(Path(candidate_client.__file__)),
        )

    def test_restricted_environment_does_not_inherit_or_force_openblas(self) -> None:
        with patch.dict(
            os.environ,
            {
                "USERNAME": "attempt07-rejection-test",
                "USERPROFILE": r"C:\Users\attempt07-rejection-test",
                "SystemRoot": r"C:\Windows",
                "PATH": r"C:\Windows\System32",
                "OPENBLAS_NUM_THREADS": "64",
                "OMP_NUM_THREADS": "64",
                "OPENBLAS_DEFAULT_NUM_THREADS": "64",
            },
            clear=True,
        ):
            environment = candidate_client.restricted_candidate_environment(
                self.config,
                session_nonce="n" * 48,
                allow_gpu_model_load=False,
            )
        self.assertNotIn("OPENBLAS_NUM_THREADS", environment)
        self.assertNotIn("OMP_NUM_THREADS", environment)
        self.assertNotIn("OPENBLAS_DEFAULT_NUM_THREADS", environment)
        self.assertNotIn("KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD", environment)

    def test_worker_verifier_accepts_restored_environment(self) -> None:
        environment = candidate_client.restricted_candidate_environment(
            self.config,
            session_nonce="v" * 48,
            allow_gpu_model_load=False,
        )
        with patch.dict(os.environ, environment, clear=True):
            cache_paths = candidate_contract.verify_restricted_environment(
                self.config,
                require_load_opt_in=False,
            )
        self.assertIn("TEMP", cache_paths)

    def test_historical_environment_pair_had_one_difference(self) -> None:
        evidence = self.report["environment_ab"]
        self.assertTrue(evidence["exact_only_difference"])
        self.assertEqual(evidence["differing_keys"], ["OPENBLAS_NUM_THREADS"])
        self.assertIsNone(evidence["control_openblas_num_threads"])
        self.assertEqual(evidence["treatment_openblas_num_threads"], "1")

    def test_attempt06_and_installed_openblas_bindings_remain_intact(self) -> None:
        self.assertTrue(probe.attempt06_integrity()["passed"])
        evidence = probe.numpy_openblas_static_evidence()
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["numpy_version"], "1.26.4")
        self.assertTrue(evidence["build_version_0_3_23_dev_present"])
        self.assertTrue(evidence["threading_backend_not_proven_from_static_config"])

    def test_assessment_rejects_no_material_difference(self) -> None:
        assessment = probe.hypothesis_assessment(
            self.report["arms"][probe.CONTROL],
            self.report["arms"][probe.TREATMENT],
        )
        self.assertFalse(assessment["openblas_single_thread_hypothesis_supported"])
        self.assertFalse(assessment["root_cause_proven"])
        self.assertFalse(assessment["ready_for_separate_full_attempt07_acceptance"])


if __name__ == "__main__":
    unittest.main()
