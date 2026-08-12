from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import Core.realtime_audio_readiness as readiness  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path, root: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def build_bundle(
    root: Path,
    *,
    profile: str = "immersive_vr",
    sample_count: int = 40,
    authorization_status: str = "synthetic_original_voice",
    identity_claim: str = "synthetic_original",
    list_authorization: bool = True,
    sample_mutator=None,
) -> tuple[dict, Path, str]:
    run_id = "artifact_bound_test_run"
    voice = root / "voice.bin"
    voice.write_bytes(b"licensed synthetic original voice test bytes")
    collector = root / "collector.py"
    collector.write_text("# instrumented collector fixture\n", encoding="utf-8")

    config = root / "runtime_config.json"
    write_json(
        config,
        {
            "schema_version": 1,
            "artifact_kind": "realtime_audio_runtime_config",
            "run_id": run_id,
            "profile": profile,
            "engine_id": "test_streaming_engine",
            "engine_version": "1.0",
            "device_id": "test_device",
            "three_d_active": True,
            "xr_active": profile == "immersive_vr",
            "display_text_required": False if profile == "immersive_vr" else True,
            "voice_artifact_sha256": sha256(voice),
        },
    )

    authorization = root / "voice_authorization.json"
    authorization_value = {
        "schema_version": 1,
        "artifact_kind": "realtime_voice_authorization",
        "authorization_id": "test_voice_authorization_v1",
        "subject_id": "test_synthetic_subject",
        "voice_profile_id": "test_synthetic_voice_profile",
        "voice_artifact_sha256": sha256(voice),
        "authorization_status": authorization_status,
        "identity_claim": identity_claim,
        "approved_by_owner_id": "robert_mcmurrer",
        "approved_at": "2026-07-16T12:00:00Z",
        "rights_gate": {
            "consent_or_nonidentity_basis_reviewed": True,
            "recording_rights_reviewed": True,
            "model_rights_reviewed": True,
            "intended_use_rights_reviewed": True,
        },
        "claim_limits": {
            "official_voice_claim_allowed": False,
            "authentic_historical_voice_claim_allowed": False,
        },
    }
    write_json(authorization, authorization_value)

    samples = []
    for index in range(sample_count):
        request_ms = float(index * 2000)
        sample = {
            "sample_id": f"sample_{index:03d}",
            "request_monotonic_ms": request_ms,
            "first_audible_monotonic_ms": request_ms + 600.0,
            "continuation_gaps_ms": [120.0],
            "interrupt_requested_monotonic_ms": request_ms + 700.0,
            "silence_monotonic_ms": request_ms + 800.0,
            "expected_words": ["hello", "world"],
            "observed_words": ["hello", "world"],
            "dropped_reply": False,
            "audio_only_control_pass": True,
            "model_ready_before_request": True,
            "ram_headroom_percent_min": 30.0,
            "vram_headroom_percent_min": 25.0,
            "voice_identity_consistent": True,
        }
        if sample_mutator is not None:
            sample_mutator(sample, index)
        samples.append(sample)
    raw = root / "raw_samples.json"
    write_json(
        raw,
        {
            "schema_version": 1,
            "artifact_kind": "realtime_audio_raw_samples",
            "run_id": run_id,
            "profile": profile,
            "samples": samples,
        },
    )

    entry = {
        "authorization_id": authorization_value["authorization_id"],
        "authorization_artifact_sha256": sha256(authorization),
        "subject_id": authorization_value["subject_id"],
        "voice_profile_id": authorization_value["voice_profile_id"],
        "voice_artifact_sha256": authorization_value["voice_artifact_sha256"],
        "authorization_status": authorization_status,
        "identity_claim": identity_claim,
    }
    registry = root / "registry.json"
    write_json(
        registry,
        {
            "schema_version": 1,
            "registry_type": "owner_controlled_realtime_voice_authorization_registry",
            "owner_id": "robert_mcmurrer",
            "status": "owner_reviewed_entries_present" if list_authorization else "default_deny",
            "entries": [entry] if list_authorization else [],
            "policy": {},
        },
    )

    evidence = {
        "schema_version": 2,
        "run_id": run_id,
        "recorded_at": "2026-07-16T12:00:01Z",
        "completed_at": "2026-07-16T12:10:01Z",
        "evidence_kind": "instrumented_end_to_end_readiness_run_v2",
        "profile": profile,
        "collector_attestation": {
            "status": "instrumented_harness_attested",
            "collector_id": "test_collector",
            "collector_version": "1.0",
            "collector_sha256": sha256(collector),
            "monotonic_timestamps_recorded": True,
            "raw_samples_written_before_evaluation": True,
            "aggregates_supplied_by_collector": False,
        },
        "bindings": {
            "raw_samples": binding(raw, root),
            "runtime_config": binding(config, root),
            "collector": binding(collector, root),
            "voice_authorization": binding(authorization, root),
            "voice_artifact": binding(voice, root),
        },
    }
    return evidence, registry, sha256(registry)


def evaluate_with_registry(evidence: dict, root: Path, registry: Path, registry_hash: str, profile: str):
    with (
        patch.object(readiness, "VOICE_AUTHORIZATION_REGISTRY_PATH", registry),
        patch.object(readiness, "VOICE_AUTHORIZATION_REGISTRY_SHA256", registry_hash),
    ):
        return readiness.evaluate_realtime_audio_readiness(evidence, profile, artifact_root=root)


class RealtimeAudioReadinessTests(unittest.TestCase):
    def test_complete_artifact_bound_vr_run_can_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(root)
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "immersive_vr")

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["readiness_claim_allowed"])
        self.assertTrue(result["evidence_bindings_verified"])
        self.assertTrue(result["voice_authority_verified"])
        self.assertEqual(result["computed_metrics"]["request_to_first_audible_ms_p95"], 600.0)

    def test_unbound_aggregate_dictionary_is_rejected(self) -> None:
        result = readiness.evaluate_realtime_audio_readiness(
            {
                "sample_count": 40,
                "request_to_first_audible_ms_p95": 1.0,
                "voice_authorization_status": "synthetic_original_voice",
                "voice_identity_claim": "synthetic_original",
            },
            "immersive_vr",
        )
        self.assertEqual(result["status"], "blocked_evidence_contract_invalid")
        self.assertFalse(result["readiness_claim_allowed"])

    def test_schema_v1_baseline_is_not_a_measured_run(self) -> None:
        baseline = json.loads(
            (PROJECT_ROOT / "Data" / "voice" / "realtime_audio_readiness" / "kira_cpu_chatterbox_baseline_20260716.json").read_text(encoding="utf-8")
        )
        result = readiness.evaluate_realtime_audio_readiness(baseline, "desktop_live")
        self.assertEqual(result["status"], "blocked_evidence_contract_invalid")
        self.assertFalse(result["measured_end_to_end"])

    def test_incompatible_voice_status_and_claim_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(
                root,
                authorization_status="synthetic_original_voice",
                identity_claim="licensed_performer_voice",
            )
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "immersive_vr")
        self.assertEqual(result["status"], "blocked_voice_authority_missing")
        self.assertTrue(any("incompatible" in item for item in result["authority_errors"]))

    def test_caller_authorization_not_listed_in_owner_registry_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(root, list_authorization=False)
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "immersive_vr")
        self.assertEqual(result["status"], "blocked_voice_authority_missing")
        self.assertTrue(result["measured_end_to_end"])
        self.assertTrue(result["evidence_bindings_verified"])
        self.assertTrue(any("not listed" in item for item in result["authority_errors"]))

    def test_nonfinite_sample_value_is_rejected(self) -> None:
        def mutate(sample, index):
            if index == 0:
                sample["ram_headroom_percent_min"] = float("inf")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(root, sample_mutator=mutate)
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "immersive_vr")
        self.assertEqual(result["status"], "blocked_evidence_contract_invalid")
        self.assertTrue(any("finite" in item for item in result["contract_errors"]))

    def test_headroom_above_100_is_rejected(self) -> None:
        def mutate(sample, index):
            if index == 0:
                sample["vram_headroom_percent_min"] = 101.0

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(root, sample_mutator=mutate)
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "immersive_vr")
        self.assertEqual(result["status"], "blocked_evidence_contract_invalid")

    def test_measured_latency_failure_is_not_ready(self) -> None:
        def mutate(sample, index):
            sample["first_audible_monotonic_ms"] = sample["request_monotonic_ms"] + 4000.0

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(root, profile="desktop_live", sample_mutator=mutate)
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "desktop_live")
        self.assertEqual(result["status"], "not_ready")
        self.assertIn("request_to_first_audible_ms_p95", result["failed_metrics"])

    def test_missing_interrupt_samples_remains_blocked(self) -> None:
        def mutate(sample, index):
            sample["interrupt_requested_monotonic_ms"] = None
            sample["silence_monotonic_ms"] = None

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, registry, registry_hash = build_bundle(root, sample_mutator=mutate)
            result = evaluate_with_registry(evidence, root, registry, registry_hash, "immersive_vr")
        self.assertEqual(result["status"], "blocked_metrics_missing")
        self.assertIn("interrupt_to_silence_ms_p95", result["missing_metrics"])

    def test_contract_requires_bound_raw_artifacts(self) -> None:
        contract = readiness.readiness_profile_contract("immersive_vr")
        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(contract["minimum_interrupt_samples"], 10)
        self.assertIn("raw_samples", contract["required_bindings"])
        self.assertEqual(contract["aggregate_policy"], "computed_by_evaluator_from_bound_raw_samples_only")
        self.assertNotIn("status", contract)


if __name__ == "__main__":
    unittest.main()
