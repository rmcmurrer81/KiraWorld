from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
if str(CANDIDATE_ROOT) not in sys.path:
    sys.path.insert(0, str(CANDIDATE_ROOT))

import candidate_client
import candidate_contract


PROBE_PATH = ROOT / "tools" / "run_persistent_blackwell_protocol_import_only_control.py"
CAPTURE_PATH = ROOT / "tools" / "capture_blackwell_defender_exclusion_state.ps1"
APPLY_PATH = ROOT / "tools" / "apply_defender_blackwell_voice_exclusion.ps1"
APPLY_SHA256 = "87527f0c5973a6e1c3c698b0a21395562ae6db4fb94849b6271cf99591664919"
EXPECTED_CANDIDATE_HASHES = {
    "candidate_client": "b57e1a57625f8d3c55881795611b440aaf91aeb7466ee2f1231ee7bedbc3e9f1",
    "candidate_contract": "e74ce6ad83b181d5f8ca786764d5e61e2cc5e053aaebf29065063151aed38cbc",
    "candidate_config": "8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57",
    "candidate_worker": "bbf33447e7b742a3f2c79da6f7a3527b37a069e32bb888ed3d1e833345388085",
}

SPEC = importlib.util.spec_from_file_location("blackwell_protocol_import_control", PROBE_PATH)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class BlackwellDefenderProtocolImportPreparationTests(unittest.TestCase):
    def test_candidate_remains_exact_restored_attempt06(self) -> None:
        self.assertEqual(probe.exact_candidate_hashes(), EXPECTED_CANDIDATE_HASHES)
        config = candidate_contract.load_candidate_config()
        self.assertNotIn("native_thread_limits", config)
        candidate_contract.verify_candidate_config(config)

    def test_protocol_probe_static_self_check_is_inert_and_passes(self) -> None:
        result = probe.static_self_check()
        self.assertTrue(result["passed"], result)
        self.assertFalse(result["blackwell_runtime_started"])
        self.assertFalse(result["torch_imported"])
        self.assertFalse(result["gpu_used"])
        self.assertFalse(result["model_loaded"])
        self.assertFalse(result["audio_generated"])
        self.assertFalse(result["ollama_invoked"])

    def test_probe_reuses_actual_client_and_actual_worker_serve(self) -> None:
        self.assertTrue(
            issubclass(
                probe.ImportOnlyProtocolClient,
                candidate_client.PersistentBlackwellVoiceCandidateClient,
            )
        )
        source = PROBE_PATH.read_text(encoding="utf-8")
        self.assertIn('self._request("load")', source)
        self.assertIn("worker.serve(", source)
        self.assertIn("self._resource_sampler_factory()", source)
        self.assertIn('importlib.import_module("torch")', source)

    def test_import_only_child_has_no_later_runtime_calls(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        child_start = source.index("def child_serve_import_only")
        child_end = source.index("\ndef run_control", child_start)
        child = source[child_start:child_end]
        self.assertNotIn('import_module("torchaudio")', child)
        self.assertNotIn('import_module("chatterbox")', child)
        self.assertNotIn("torch.cuda", child)
        self.assertNotIn("qwen_residency_evidence(", child)
        self.assertNotIn("/api/ps", child)
        self.assertNotIn("winsound.PlaySound(", child)

    def test_probe_requires_hash_bound_defender_state_evidence(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        self.assertIn("validate_defender_state_evidence(", source)
        self.assertIn("expected_defender_exclusion_state", source)
        self.assertIn("DEFENDER_APPLY_HELPER_SHA256", source)
        self.assertEqual(candidate_contract.sha256_file(APPLY_PATH), APPLY_SHA256)

    def test_state_capture_helper_is_read_only_and_uses_sole_apply_hash(self) -> None:
        source = CAPTURE_PATH.read_text(encoding="utf-8")
        self.assertIn(APPLY_SHA256, source)
        self.assertIn("Get-MpPreference", source)
        self.assertNotIn("Add-MpPreference", source)
        self.assertNotIn("Remove-MpPreference", source)
        self.assertNotIn("Set-MpPreference", source)
        self.assertIn("FileMode]::CreateNew", source)
        self.assertIn("raw_other_exclusion_paths_recorded = $false", source)

    def test_sole_apply_helper_is_exact_path_only_and_never_disables_defender(self) -> None:
        source = APPLY_PATH.read_text(encoding="utf-8")
        expected = r"C:\Users\robmc\Kira\Voice\sidecars\chatterbox_blackwell_gpu\.venv"
        self.assertIn(expected, source)
        self.assertIn("Add-MpPreference -ExclusionPath $target", source)
        self.assertNotIn("Set-MpPreference", source)
        self.assertNotIn("DisableRealtimeMonitoring $true", source)
        self.assertNotIn("DisableBehaviorMonitoring $true", source)

    def test_capture_describe_does_not_query_or_change_defender(self) -> None:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(CAPTURE_PATH),
                "-Stage",
                "Describe",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "PREPARED_NOT_EXECUTED")
        self.assertFalse(payload["changes_defender"])
        self.assertEqual(payload["sole_apply_helper_expected_sha256"], APPLY_SHA256)


if __name__ == "__main__":
    unittest.main()
