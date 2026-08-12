from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
if str(CANDIDATE_ROOT) not in sys.path:
    sys.path.insert(0, str(CANDIDATE_ROOT))

import candidate_contract


WRAPPER_PATH = (
    ROOT / "tools" / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state.py"
)
STRICT_PATH = ROOT / "tools" / "run_persistent_blackwell_protocol_import_only_control.py"
STRICT_SHA256 = "7fd8e006ba58aede2f34b4289c4fc857a1bc6ae76d6a6a4fcc36a7f3a0466f21"
APPLY_RESULT_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "defender_blackwell_voice_narrow_exclusion"
    / "attempt_02"
    / "APPLY_RESULT_FROM_OBSERVED_UAC_EXIT.json"
)
APPLY_RESULT_SHA256 = "f4e0a73b43a4bb6a6ade9234da3d4a55a69cac4eee1905d59f6ee9201914a057"

SPEC = importlib.util.spec_from_file_location(
    "blackwell_protocol_pending_defender_test_module",
    WRAPPER_PATH,
)
assert SPEC is not None and SPEC.loader is not None
wrapper = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wrapper
SPEC.loader.exec_module(wrapper)


class BlackwellProtocolImportPendingDefenderStateRevisionTests(unittest.TestCase):
    def test_stricter_existing_tool_is_unchanged(self) -> None:
        self.assertEqual(candidate_contract.sha256_file(STRICT_PATH), STRICT_SHA256)
        self.assertEqual(wrapper.BASE_TOOL_SHA256, STRICT_SHA256)

    def test_apply_result_record_is_exact_and_truthfully_pending(self) -> None:
        self.assertEqual(
            candidate_contract.sha256_file(APPLY_RESULT_PATH),
            APPLY_RESULT_SHA256,
        )
        evidence = wrapper.validate_apply_exit_record(APPLY_RESULT_SHA256)
        self.assertEqual(evidence["helper_exit_code_observed"], 0)
        self.assertEqual(
            evidence["helper_exact_hard_coded_target"],
            r"C:\Users\robmc\Kira\Voice\sidecars\chatterbox_blackwell_gpu\.venv",
        )
        self.assertEqual(len(evidence["helper_exit_zero_contract"]), 3)
        self.assertEqual(
            evidence["independent_defender_state"],
            "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        )
        self.assertFalse(evidence["exclusion_present_claimed"])
        self.assertFalse(evidence["latency_improvement_claimed"])
        self.assertFalse(evidence["defender_causality_claimed"])

    def test_static_self_check_passes_without_runtime(self) -> None:
        result = wrapper.static_self_check()
        self.assertTrue(result["passed"], result)
        self.assertFalse(result["defender_queried"])
        self.assertFalse(result["defender_changed"])
        self.assertFalse(result["blackwell_runtime_started"])
        self.assertFalse(result["torch_imported"])
        self.assertFalse(result["cuda_api_invoked"])
        self.assertFalse(result["model_loaded"])
        self.assertFalse(result["audio_generated"])
        self.assertFalse(result["playback_performed"])
        self.assertFalse(result["ollama_invoked"])
        self.assertFalse(result["candidate_promoted"])
        self.assertFalse(result["production_routing_changed"])

    def test_operational_wrapper_has_no_defender_or_heavy_runtime_call(self) -> None:
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        operational = source[: source.index("\ndef static_self_check")]
        for marker in (
            "Get-MpPreference",
            "Add-MpPreference",
            "Remove-MpPreference",
            "Set-MpPreference",
            "torch.cuda",
            'import_module("torch")',
            'import_module("torchaudio")',
            'import_module("chatterbox")',
            "from_pretrained(",
            "winsound.PlaySound(",
            "sounddevice.play(",
        ):
            self.assertNotIn(marker, operational)

    def test_strict_dependency_hash_is_checked_before_module_execution(self) -> None:
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        hash_gate = source.index("_sha256_before_dependency_load(BASE_TOOL_PATH)")
        module_execution = source.index("BASE_SPEC.loader.exec_module(strict_base)")
        self.assertLess(hash_gate, module_execution)

    def test_wrapper_cannot_promote_or_change_route(self) -> None:
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        operational = source[: source.index("\ndef static_self_check")]
        for marker in (
            "promote_candidate(",
            "activate_candidate(",
            "set_production_route(",
            "production_routing_authorized = True",
            '"candidate_promoted": True',
            '"production_routing_changed": True',
        ):
            self.assertNotIn(marker, operational)

    def test_eventual_pass_is_gated_on_cleanup_and_final_integrity(self) -> None:
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        final_gate = source[source.index('report["passed"] = (') :]
        self.assertIn('report["candidate_unchanged"] is True', final_gate)
        self.assertIn('report["cleanup_clean"] is True', final_gate)
        self.assertIn('report["prohibited_outcomes_absent"] is True', final_gate)

    def test_later_run_reuses_real_strict_client_path(self) -> None:
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn("strict_base.ImportOnlyProtocolClient(", source)
        self.assertIn("client.start()", source)
        self.assertIn("client.status()", source)
        self.assertIn("client.load_import_only()", source)
        self.assertIn("client.close()", source)

    def test_description_never_upgrades_unknown_state_to_a_claim(self) -> None:
        description = wrapper.describe()
        self.assertEqual(description["status"], "PREPARED_NOT_EXECUTED")
        self.assertEqual(
            description["independent_defender_state"],
            "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        )
        self.assertFalse(description["exclusion_present_claimed"])
        self.assertFalse(
            description["monitoring_enabled_claimed_from_independent_evidence"]
        )
        self.assertFalse(description["latency_improvement_claimed"])
        self.assertFalse(description["defender_causality_claimed"])
        self.assertFalse(description["defender_queried"])
        self.assertFalse(description["defender_changed"])

    def test_apply_result_json_does_not_claim_independent_state(self) -> None:
        payload = json.loads(APPLY_RESULT_PATH.read_text(encoding="utf-8"))
        boundary = payload["truth_boundary"]
        self.assertEqual(
            boundary["current_exact_exclusion_state"],
            "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        )
        self.assertFalse(boundary["latency_improvement_claimed"])
        self.assertFalse(boundary["defender_causality_claimed"])
        self.assertFalse(boundary["production_voice_acceptance_claimed"])


if __name__ == "__main__":
    unittest.main()
