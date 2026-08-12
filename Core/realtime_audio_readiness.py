"""Artifact-bound, fail-closed readiness checks for live and immersive speech.

The evaluator never trusts caller-supplied aggregate latency numbers.  It
verifies an instrumented run contract, immutable file bindings, raw per-request
samples, a runtime configuration, the collector bytes, the exact voice bytes,
and a separate owner-controlled voice authorization registry.  Metrics are
computed here from the bound raw samples.

This module does not synthesize, clone, play, record, or authorize a voice.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_AUTHORIZATION_REGISTRY_PATH = (
    PROJECT_ROOT / "Data" / "voice" / "policies" / "realtime_voice_authorization_registry.json"
)
VOICE_AUTHORIZATION_REGISTRY_SHA256 = "9d4b410f1a7c586d61ae63f292777a3794afa006bc2bb6848661d41fd765ce1e"
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,127}$")


@dataclass(frozen=True)
class ReadinessProfile:
    name: str
    minimum_samples: int
    minimum_interrupt_samples: int
    first_audible_ms_p95_max: float
    continuation_gap_ms_p95_max: float
    interrupt_to_silence_ms_p95_max: float
    spoken_word_coverage_min: float
    audio_only_control_pass_rate_min: float
    model_ready_before_request_rate_min: float
    ram_headroom_percent_min: float
    vram_headroom_percent_min: float
    require_3d_active: bool
    require_xr_active: bool
    require_textless_operation: bool


PROFILES: dict[str, ReadinessProfile] = {
    "desktop_live": ReadinessProfile(
        name="desktop_live",
        minimum_samples=10,
        minimum_interrupt_samples=5,
        first_audible_ms_p95_max=1500.0,
        continuation_gap_ms_p95_max=350.0,
        interrupt_to_silence_ms_p95_max=300.0,
        spoken_word_coverage_min=1.0,
        audio_only_control_pass_rate_min=1.0,
        model_ready_before_request_rate_min=0.90,
        ram_headroom_percent_min=10.0,
        vram_headroom_percent_min=10.0,
        require_3d_active=True,
        require_xr_active=False,
        require_textless_operation=False,
    ),
    "immersive_vr": ReadinessProfile(
        name="immersive_vr",
        minimum_samples=30,
        minimum_interrupt_samples=10,
        first_audible_ms_p95_max=750.0,
        continuation_gap_ms_p95_max=180.0,
        interrupt_to_silence_ms_p95_max=150.0,
        spoken_word_coverage_min=1.0,
        audio_only_control_pass_rate_min=1.0,
        model_ready_before_request_rate_min=0.98,
        ram_headroom_percent_min=20.0,
        vram_headroom_percent_min=15.0,
        require_3d_active=True,
        require_xr_active=True,
        require_textless_operation=True,
    ),
}


VOICE_STATUS_CLAIM_PAIRS = {
    "owner_self_voice": "person_approved_voice",
    "performer_verified_voice": "licensed_performer_voice",
    "licensed_shared_voice": "licensed_original_non_identity_voice",
    "synthetic_original_voice": "synthetic_original",
    "historically_informed_interpretation": "historically_informed_interpretation",
}

TOP_LEVEL_KEYS = {
    "schema_version",
    "run_id",
    "recorded_at",
    "completed_at",
    "evidence_kind",
    "profile",
    "collector_attestation",
    "bindings",
}
BINDING_ROLES = {
    "raw_samples",
    "runtime_config",
    "collector",
    "voice_authorization",
    "voice_artifact",
}
SAMPLE_KEYS = {
    "sample_id",
    "request_monotonic_ms",
    "first_audible_monotonic_ms",
    "continuation_gaps_ms",
    "interrupt_requested_monotonic_ms",
    "silence_monotonic_ms",
    "expected_words",
    "observed_words",
    "dropped_reply",
    "audio_only_control_pass",
    "model_ready_before_request",
    "ram_headroom_percent_min",
    "vram_headroom_percent_min",
    "voice_identity_consistent",
}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _integer(value: Any) -> int | None:
    number = _finite_number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _explicit_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _parse_timestamp(value: Any, label: str) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _resolve_binding(binding: Any, *, label: str, root: Path) -> tuple[Path | None, list[str]]:
    errors: list[str] = []
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "bytes"}:
        return None, [f"bindings.{label} must contain exactly path, sha256, and bytes."]
    raw_path = binding.get("path")
    expected_hash = binding.get("sha256")
    expected_bytes = _integer(binding.get("bytes"))
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"bindings.{label}.path is invalid.")
        return None, errors
    fragment = Path(raw_path)
    if fragment.is_absolute() or ".." in fragment.parts:
        errors.append(f"bindings.{label}.path must be project-relative and cannot traverse parents.")
        return None, errors
    if not isinstance(expected_hash, str) or not HEX_SHA256.fullmatch(expected_hash):
        errors.append(f"bindings.{label}.sha256 is invalid.")
    if expected_bytes is None or expected_bytes < 1:
        errors.append(f"bindings.{label}.bytes must be a positive integer.")

    root = root.resolve()
    lexical = root / fragment
    current = root
    for part in fragment.parts:
        current = current / part
        if current.is_symlink():
            errors.append(f"bindings.{label}.path may not contain a symlink.")
            return None, errors
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"bindings.{label}.path escapes the artifact root.")
        return None, errors
    if not resolved.is_file():
        errors.append(f"bindings.{label}.path is not a regular file.")
        return None, errors
    if expected_bytes is not None and resolved.stat().st_size != expected_bytes:
        errors.append(f"bindings.{label}.bytes does not match the current file.")
    if isinstance(expected_hash, str) and HEX_SHA256.fullmatch(expected_hash):
        if _sha256_file(resolved) != expected_hash:
            errors.append(f"bindings.{label}.sha256 does not match the current file.")
    return resolved, errors


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _check(
    *,
    metric: str,
    actual: Any,
    expected: Any,
    comparator: Callable[[Any, Any], bool],
    requirement: str,
) -> dict[str, Any]:
    if actual is None:
        return {
            "metric": metric,
            "status": "missing",
            "actual": None,
            "required": expected,
            "requirement": requirement,
        }
    passed = comparator(actual, expected)
    return {
        "metric": metric,
        "status": "pass" if passed else "fail",
        "actual": actual,
        "required": expected,
        "requirement": requirement,
    }


def _load_owner_registry() -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    path = VOICE_AUTHORIZATION_REGISTRY_PATH
    if path.is_symlink() or not path.is_file():
        return None, ["The code-pinned owner voice-authorization registry is missing or is a symlink."]
    if _sha256_file(path) != VOICE_AUTHORIZATION_REGISTRY_SHA256:
        return None, ["The owner voice-authorization registry does not match its code-pinned SHA-256."]
    try:
        registry = _read_json_object(path, "owner voice-authorization registry")
    except ValueError as exc:
        return None, [str(exc)]
    if set(registry) != {"schema_version", "registry_type", "owner_id", "status", "entries", "policy"}:
        errors.append("The owner voice-authorization registry has unexpected or missing keys.")
    if registry.get("schema_version") != 1:
        errors.append("The owner voice-authorization registry schema is invalid.")
    if registry.get("registry_type") != "owner_controlled_realtime_voice_authorization_registry":
        errors.append("The owner voice-authorization registry type is invalid.")
    if registry.get("owner_id") != "robert_mcmurrer":
        errors.append("The owner voice-authorization registry owner is invalid.")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        errors.append("The owner voice-authorization registry entries must be a list.")
    return registry if not errors else None, errors


def _validate_voice_authorization(
    path: Path,
    *,
    voice_artifact_sha256: str,
    registry: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        authorization = _read_json_object(path, "voice authorization artifact")
    except ValueError as exc:
        return None, [str(exc)]
    required = {
        "schema_version",
        "artifact_kind",
        "authorization_id",
        "subject_id",
        "voice_profile_id",
        "voice_artifact_sha256",
        "authorization_status",
        "identity_claim",
        "approved_by_owner_id",
        "approved_at",
        "rights_gate",
        "claim_limits",
    }
    if set(authorization) != required:
        errors.append("Voice authorization artifact has unexpected or missing keys.")
    if authorization.get("schema_version") != 1 or authorization.get("artifact_kind") != "realtime_voice_authorization":
        errors.append("Voice authorization artifact schema or kind is invalid.")
    for key in ("authorization_id", "subject_id", "voice_profile_id"):
        if _text(authorization.get(key)) is None:
            errors.append(f"Voice authorization {key} is missing.")
    if authorization.get("voice_artifact_sha256") != voice_artifact_sha256:
        errors.append("Voice authorization does not bind the exact voice artifact.")
    status = authorization.get("authorization_status")
    claim = authorization.get("identity_claim")
    if VOICE_STATUS_CLAIM_PAIRS.get(status) != claim:
        errors.append("Voice authorization status and identity claim are incompatible.")
    if authorization.get("approved_by_owner_id") != "robert_mcmurrer":
        errors.append("Voice authorization is not bound to the project owner identity.")
    if _parse_timestamp(authorization.get("approved_at"), "approved_at") is None:
        errors.append("Voice authorization approved_at must be timezone-aware ISO-8601.")
    rights = authorization.get("rights_gate")
    right_keys = {
        "consent_or_nonidentity_basis_reviewed",
        "recording_rights_reviewed",
        "model_rights_reviewed",
        "intended_use_rights_reviewed",
    }
    if not isinstance(rights, dict) or set(rights) != right_keys or any(rights.get(key) is not True for key in right_keys):
        errors.append("Voice authorization rights gate is incomplete.")
    limits = authorization.get("claim_limits")
    if (
        not isinstance(limits, dict)
        or set(limits) != {"official_voice_claim_allowed", "authentic_historical_voice_claim_allowed"}
        or limits.get("official_voice_claim_allowed") is not False
        or limits.get("authentic_historical_voice_claim_allowed") is not False
    ):
        errors.append("Voice authorization claim limits must deny official/authentic marketing claims.")

    authorization_hash = _sha256_file(path)
    if registry is None:
        errors.append("Owner voice-authorization registry is unavailable.")
    else:
        expected_entry = {
            "authorization_id": authorization.get("authorization_id"),
            "authorization_artifact_sha256": authorization_hash,
            "subject_id": authorization.get("subject_id"),
            "voice_profile_id": authorization.get("voice_profile_id"),
            "voice_artifact_sha256": authorization.get("voice_artifact_sha256"),
            "authorization_status": status,
            "identity_claim": claim,
        }
        entries = registry.get("entries") if isinstance(registry.get("entries"), list) else []
        if expected_entry not in entries:
            errors.append("Exact voice authorization is not listed in the code-pinned owner registry.")
    return authorization if not errors else None, errors


def _validate_runtime_config(
    path: Path,
    *,
    run_id: str,
    profile_name: str,
    voice_artifact_sha256: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        config = _read_json_object(path, "runtime configuration")
    except ValueError as exc:
        return None, [str(exc)]
    required = {
        "schema_version",
        "artifact_kind",
        "run_id",
        "profile",
        "engine_id",
        "engine_version",
        "device_id",
        "three_d_active",
        "xr_active",
        "display_text_required",
        "voice_artifact_sha256",
    }
    if set(config) != required:
        errors.append("Runtime configuration has unexpected or missing keys.")
    if config.get("schema_version") != 1 or config.get("artifact_kind") != "realtime_audio_runtime_config":
        errors.append("Runtime configuration schema or kind is invalid.")
    if config.get("run_id") != run_id or config.get("profile") != profile_name:
        errors.append("Runtime configuration run/profile binding is invalid.")
    for key in ("engine_id", "engine_version", "device_id"):
        if _text(config.get(key)) is None:
            errors.append(f"Runtime configuration {key} is missing.")
    for key in ("three_d_active", "xr_active", "display_text_required"):
        if _explicit_bool(config.get(key)) is None:
            errors.append(f"Runtime configuration {key} must be Boolean.")
    if config.get("voice_artifact_sha256") != voice_artifact_sha256:
        errors.append("Runtime configuration does not bind the exact voice artifact.")
    return config if not errors else None, errors


def _load_raw_samples(
    path: Path,
    *,
    run_id: str,
    profile_name: str,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        artifact = _read_json_object(path, "raw sample artifact")
    except ValueError as exc:
        return {}, [str(exc)]
    if set(artifact) != {"schema_version", "artifact_kind", "run_id", "profile", "samples"}:
        errors.append("Raw sample artifact has unexpected or missing keys.")
    if artifact.get("schema_version") != 1 or artifact.get("artifact_kind") != "realtime_audio_raw_samples":
        errors.append("Raw sample artifact schema or kind is invalid.")
    if artifact.get("run_id") != run_id or artifact.get("profile") != profile_name:
        errors.append("Raw sample artifact run/profile binding is invalid.")
    samples = artifact.get("samples")
    if not isinstance(samples, list):
        return {}, errors + ["Raw sample artifact samples must be a list."]

    sample_ids: set[str] = set()
    first_latencies: list[float] = []
    continuation_gaps: list[float] = []
    interrupt_latencies: list[float] = []
    coverage: list[float] = []
    dropped = 0
    audio_control_passes = 0
    model_ready = 0
    ram_headroom: list[float] = []
    vram_headroom: list[float] = []
    identity_consistency: list[bool] = []

    for index, sample in enumerate(samples):
        label = f"raw sample {index}"
        if not isinstance(sample, dict) or set(sample) != SAMPLE_KEYS:
            errors.append(f"{label} has unexpected or missing keys.")
            continue
        sample_id = _text(sample.get("sample_id"))
        if sample_id is None or sample_id in sample_ids:
            errors.append(f"{label} sample_id is missing or duplicated.")
        else:
            sample_ids.add(sample_id)
        request_ms = _finite_number(sample.get("request_monotonic_ms"))
        audible_ms = _finite_number(sample.get("first_audible_monotonic_ms"))
        if request_ms is None or audible_ms is None or request_ms < 0 or audible_ms < request_ms:
            errors.append(f"{label} has invalid monotonic first-audio timestamps.")
        else:
            first_latencies.append(audible_ms - request_ms)

        gaps = sample.get("continuation_gaps_ms")
        if not isinstance(gaps, list):
            errors.append(f"{label} continuation_gaps_ms must be a list.")
        else:
            for gap in gaps:
                number = _finite_number(gap)
                if number is None or number < 0:
                    errors.append(f"{label} has an invalid continuation gap.")
                else:
                    continuation_gaps.append(number)

        interrupt_ms = sample.get("interrupt_requested_monotonic_ms")
        silence_ms = sample.get("silence_monotonic_ms")
        if interrupt_ms is None and silence_ms is None:
            pass
        else:
            interrupt_number = _finite_number(interrupt_ms)
            silence_number = _finite_number(silence_ms)
            if interrupt_number is None or silence_number is None or interrupt_number < 0 or silence_number < interrupt_number:
                errors.append(f"{label} has invalid interruption timestamps.")
            else:
                interrupt_latencies.append(silence_number - interrupt_number)

        expected_words = sample.get("expected_words")
        observed_words = sample.get("observed_words")
        if (
            not isinstance(expected_words, list)
            or not expected_words
            or not all(isinstance(word, str) and word.strip() for word in expected_words)
            or not isinstance(observed_words, list)
            or not all(isinstance(word, str) and word.strip() for word in observed_words)
        ):
            errors.append(f"{label} expected/observed words are invalid.")
        else:
            expected = [word.strip().casefold() for word in expected_words]
            observed = [word.strip().casefold() for word in observed_words]
            coverage.append(1.0 if expected == observed else 0.0)

        for key in (
            "dropped_reply",
            "audio_only_control_pass",
            "model_ready_before_request",
            "voice_identity_consistent",
        ):
            if _explicit_bool(sample.get(key)) is None:
                errors.append(f"{label} {key} must be Boolean.")
        if sample.get("dropped_reply") is True:
            dropped += 1
        if sample.get("audio_only_control_pass") is True:
            audio_control_passes += 1
        if sample.get("model_ready_before_request") is True:
            model_ready += 1
        if isinstance(sample.get("voice_identity_consistent"), bool):
            identity_consistency.append(sample["voice_identity_consistent"])

        for key, destination in (
            ("ram_headroom_percent_min", ram_headroom),
            ("vram_headroom_percent_min", vram_headroom),
        ):
            value = _finite_number(sample.get(key))
            if value is None or not 0 <= value <= 100:
                errors.append(f"{label} {key} must be finite and between 0 and 100.")
            else:
                destination.append(value)

    count = len(samples)
    metrics = {
        "sample_count": count,
        "interrupt_sample_count": len(interrupt_latencies),
        "request_to_first_audible_ms_p95": _p95(first_latencies),
        "continuation_gap_ms_p95": _p95(continuation_gaps),
        "interrupt_to_silence_ms_p95": _p95(interrupt_latencies),
        "spoken_word_coverage_min": min(coverage) if coverage else None,
        "dropped_reply_count": dropped,
        "audio_only_control_pass_rate": audio_control_passes / count if count else None,
        "model_ready_before_request_rate": model_ready / count if count else None,
        "combined_ram_headroom_percent_min": min(ram_headroom) if ram_headroom else None,
        "combined_vram_headroom_percent_min": min(vram_headroom) if vram_headroom else None,
        "voice_identity_consistent": all(identity_consistency) if len(identity_consistency) == count and count else None,
    }
    return metrics, errors


def _blocked_result(
    profile_name: str,
    *,
    status: str,
    contract_errors: list[str],
    authority_errors: list[str],
    run_id: str = "",
    measured_end_to_end: bool = False,
    evidence_bindings_verified: bool = False,
    computed_metrics: dict[str, Any] | None = None,
    verified_artifact_bindings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "schema_version": 2,
        "profile": profile_name,
        "status": status,
        "readiness_claim_allowed": False,
        "measured_end_to_end": measured_end_to_end,
        "evidence_bindings_verified": evidence_bindings_verified,
        "voice_authority_verified": False,
        "contract_errors": contract_errors,
        "authority_errors": authority_errors,
        "computed_metrics": computed_metrics or {},
        "missing_metrics": [],
        "failed_metrics": [],
        "checks": [],
        "notes": [
            "Caller-supplied aggregate metrics are not readiness evidence.",
            "Only exact-hash-bound raw samples from the instrumented contract are evaluated.",
            "A separate code-pinned owner registry must list the exact voice authorization artifact.",
        ],
    }
    if run_id:
        result["run_id"] = run_id
    if verified_artifact_bindings is not None:
        result["verified_artifact_bindings"] = verified_artifact_bindings
    return result


def evaluate_realtime_audio_readiness(
    evidence: dict[str, Any],
    profile_name: str = "desktop_live",
    *,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Evaluate an exact-bound instrumented run and compute its metrics.

    Schema-v1 summaries and any unbound aggregate dictionary fail closed.
    """
    if profile_name not in PROFILES:
        raise ValueError(f"Unknown readiness profile: {profile_name!r}")
    if not isinstance(evidence, dict):
        raise TypeError("evidence must be a JSON object")
    root = (artifact_root or PROJECT_ROOT).resolve()
    profile = PROFILES[profile_name]
    contract_errors: list[str] = []
    authority_errors: list[str] = []

    if set(evidence) != TOP_LEVEL_KEYS:
        contract_errors.append("Evidence must use the exact schema-v2 instrumented-run keys; aggregate summaries are rejected.")
    if evidence.get("schema_version") != 2:
        contract_errors.append("Evidence schema_version must be 2.")
    if evidence.get("evidence_kind") != "instrumented_end_to_end_readiness_run_v2":
        contract_errors.append("Evidence kind is not an instrumented end-to-end readiness run.")
    run_id = evidence.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        contract_errors.append("Evidence run_id is invalid.")
        run_id = "invalid"
    if evidence.get("profile") != profile_name:
        contract_errors.append("Evidence profile does not match the requested evaluation profile.")
    recorded = _parse_timestamp(evidence.get("recorded_at"), "recorded_at")
    completed = _parse_timestamp(evidence.get("completed_at"), "completed_at")
    if recorded is None or completed is None or completed < recorded:
        contract_errors.append("Evidence timestamps must be timezone-aware and completed_at cannot precede recorded_at.")

    attestation = evidence.get("collector_attestation")
    attestation_keys = {
        "status",
        "collector_id",
        "collector_version",
        "collector_sha256",
        "monotonic_timestamps_recorded",
        "raw_samples_written_before_evaluation",
        "aggregates_supplied_by_collector",
    }
    if not isinstance(attestation, dict) or set(attestation) != attestation_keys:
        contract_errors.append("Collector attestation has unexpected or missing keys.")
        attestation = {}
    if attestation.get("status") != "instrumented_harness_attested":
        contract_errors.append("Collector attestation status is invalid.")
    for key in ("collector_id", "collector_version"):
        if _text(attestation.get(key)) is None:
            contract_errors.append(f"Collector attestation {key} is missing.")
    if attestation.get("monotonic_timestamps_recorded") is not True:
        contract_errors.append("Collector must attest monotonic timestamps.")
    if attestation.get("raw_samples_written_before_evaluation") is not True:
        contract_errors.append("Collector must attest raw samples were written before evaluation.")
    if attestation.get("aggregates_supplied_by_collector") is not False:
        contract_errors.append("Collector-supplied aggregate metrics are forbidden.")

    bindings = evidence.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != BINDING_ROLES:
        contract_errors.append("Evidence bindings must contain exactly the five required artifact roles.")
        bindings = {}
    resolved: dict[str, Path] = {}
    for role in BINDING_ROLES:
        path, errors = _resolve_binding(bindings.get(role), label=role, root=root)
        contract_errors.extend(errors)
        if path is not None:
            resolved[role] = path
    if len({path.resolve() for path in resolved.values()}) != len(resolved):
        contract_errors.append("Every evidence binding must point to a distinct artifact.")
    collector_binding = bindings.get("collector") if isinstance(bindings.get("collector"), dict) else {}
    if attestation.get("collector_sha256") != collector_binding.get("sha256"):
        contract_errors.append("Collector attestation does not bind the collector artifact hash.")

    metrics: dict[str, Any] = {}
    voice_hash = ""
    if isinstance(bindings.get("voice_artifact"), dict):
        voice_hash = str(bindings["voice_artifact"].get("sha256") or "")
    config: dict[str, Any] | None = None
    if "runtime_config" in resolved:
        config, errors = _validate_runtime_config(
            resolved["runtime_config"],
            run_id=run_id,
            profile_name=profile_name,
            voice_artifact_sha256=voice_hash,
        )
        contract_errors.extend(errors)
    if "raw_samples" in resolved:
        metrics, errors = _load_raw_samples(resolved["raw_samples"], run_id=run_id, profile_name=profile_name)
        contract_errors.extend(errors)

    registry, registry_errors = _load_owner_registry()
    authority_errors.extend(registry_errors)
    authorization: dict[str, Any] | None = None
    if "voice_authorization" in resolved:
        authorization, errors = _validate_voice_authorization(
            resolved["voice_authorization"],
            voice_artifact_sha256=voice_hash,
            registry=registry,
        )
        authority_errors.extend(errors)

    if contract_errors:
        return _blocked_result(
            profile_name,
            status="blocked_evidence_contract_invalid",
            contract_errors=contract_errors,
            authority_errors=authority_errors,
            run_id=run_id if run_id != "invalid" else "",
        )
    if authority_errors or authorization is None:
        return _blocked_result(
            profile_name,
            status="blocked_voice_authority_missing",
            contract_errors=[],
            authority_errors=authority_errors or ["Voice authorization artifact was not verified."],
            run_id=run_id,
            measured_end_to_end=True,
            evidence_bindings_verified=True,
            computed_metrics=metrics,
            verified_artifact_bindings=json.loads(json.dumps(bindings)),
        )
    assert config is not None

    checks: list[dict[str, Any]] = []
    add = checks.append
    add(_check(metric="sample_count", actual=metrics.get("sample_count"), expected=profile.minimum_samples, comparator=lambda a, e: a >= e, requirement="at_least"))
    add(_check(metric="interrupt_sample_count", actual=metrics.get("interrupt_sample_count"), expected=profile.minimum_interrupt_samples, comparator=lambda a, e: a >= e, requirement="at_least"))
    add(_check(metric="request_to_first_audible_ms_p95", actual=metrics.get("request_to_first_audible_ms_p95"), expected=profile.first_audible_ms_p95_max, comparator=lambda a, e: 0 <= a <= e, requirement="at_most"))
    add(_check(metric="continuation_gap_ms_p95", actual=metrics.get("continuation_gap_ms_p95"), expected=profile.continuation_gap_ms_p95_max, comparator=lambda a, e: 0 <= a <= e, requirement="at_most"))
    add(_check(metric="interrupt_to_silence_ms_p95", actual=metrics.get("interrupt_to_silence_ms_p95"), expected=profile.interrupt_to_silence_ms_p95_max, comparator=lambda a, e: 0 <= a <= e, requirement="at_most"))
    add(_check(metric="spoken_word_coverage_min", actual=metrics.get("spoken_word_coverage_min"), expected=profile.spoken_word_coverage_min, comparator=lambda a, e: e <= a <= 1.0, requirement="at_least"))
    add(_check(metric="dropped_reply_count", actual=metrics.get("dropped_reply_count"), expected=0, comparator=lambda a, e: a == e, requirement="equals"))
    add(_check(metric="audio_only_control_pass_rate", actual=metrics.get("audio_only_control_pass_rate"), expected=profile.audio_only_control_pass_rate_min, comparator=lambda a, e: e <= a <= 1.0, requirement="at_least"))
    add(_check(metric="model_ready_before_request_rate", actual=metrics.get("model_ready_before_request_rate"), expected=profile.model_ready_before_request_rate_min, comparator=lambda a, e: e <= a <= 1.0, requirement="at_least"))
    add(_check(metric="combined_ram_headroom_percent_min", actual=metrics.get("combined_ram_headroom_percent_min"), expected=profile.ram_headroom_percent_min, comparator=lambda a, e: e <= a <= 100.0, requirement="at_least"))
    add(_check(metric="combined_vram_headroom_percent_min", actual=metrics.get("combined_vram_headroom_percent_min"), expected=profile.vram_headroom_percent_min, comparator=lambda a, e: e <= a <= 100.0, requirement="at_least"))
    add(_check(metric="three_d_active", actual=config.get("three_d_active"), expected=profile.require_3d_active, comparator=lambda a, e: a is e, requirement="equals"))
    add(_check(metric="xr_active", actual=config.get("xr_active"), expected=profile.require_xr_active, comparator=lambda a, e: a is e, requirement="equals"))
    if profile.require_textless_operation:
        add(_check(metric="display_text_required", actual=config.get("display_text_required"), expected=False, comparator=lambda a, e: a is e, requirement="equals"))
    add(_check(metric="voice_identity_consistent", actual=metrics.get("voice_identity_consistent"), expected=True, comparator=lambda a, e: a is e, requirement="equals"))

    missing = [item["metric"] for item in checks if item["status"] == "missing"]
    failed = [item["metric"] for item in checks if item["status"] == "fail"]
    status = "blocked_metrics_missing" if missing else "not_ready" if failed else "ready"
    return {
        "schema_version": 2,
        "profile": profile.name,
        "run_id": run_id,
        "status": status,
        "readiness_claim_allowed": status == "ready",
        "measured_end_to_end": True,
        "evidence_bindings_verified": True,
        "voice_authority_verified": True,
        "voice_authorization": {
            "authorization_id": authorization["authorization_id"],
            "subject_id": authorization["subject_id"],
            "voice_profile_id": authorization["voice_profile_id"],
            "authorization_status": authorization["authorization_status"],
            "identity_claim": authorization["identity_claim"],
        },
        "verified_artifact_bindings": json.loads(json.dumps(bindings)),
        "contract_errors": [],
        "authority_errors": [],
        "computed_metrics": metrics,
        "missing_metrics": missing,
        "failed_metrics": failed,
        "checks": checks,
        "notes": [
            "Metrics were recomputed from exact-hash-bound raw per-request samples.",
            "Model-load or prewarm duration alone is not time to first audible speech.",
            "The run binds the collector, runtime configuration, voice bytes, and owner-listed authorization.",
            "A historically informed interpretation is never an exact historical voice claim.",
        ],
    }


def readiness_profile_contract(profile_name: str) -> dict[str, Any]:
    """Return the serializable target and evidence contract for a harness."""
    if profile_name not in PROFILES:
        raise ValueError(f"Unknown readiness profile: {profile_name!r}")
    profile = PROFILES[profile_name]
    return {
        "schema_version": 2,
        "profile": profile.name,
        "minimum_samples": profile.minimum_samples,
        "minimum_interrupt_samples": profile.minimum_interrupt_samples,
        "targets": {
            "request_to_first_audible_ms_p95_max": profile.first_audible_ms_p95_max,
            "continuation_gap_ms_p95_max": profile.continuation_gap_ms_p95_max,
            "interrupt_to_silence_ms_p95_max": profile.interrupt_to_silence_ms_p95_max,
            "spoken_word_coverage_min": profile.spoken_word_coverage_min,
            "dropped_reply_count_max": 0,
            "audio_only_control_pass_rate_min": profile.audio_only_control_pass_rate_min,
            "model_ready_before_request_rate_min": profile.model_ready_before_request_rate_min,
            "combined_ram_headroom_percent_min": profile.ram_headroom_percent_min,
            "combined_vram_headroom_percent_min": profile.vram_headroom_percent_min,
        },
        "required_context": {
            "three_d_active": profile.require_3d_active,
            "xr_active": profile.require_xr_active,
            "display_text_required": False if profile.require_textless_operation else "measured_but_optional",
        },
        "required_bindings": sorted(BINDING_ROLES),
        "authority": {
            "owner_registry": "code_pinned_default_deny",
            "compatible_status_claim_pairs": VOICE_STATUS_CLAIM_PAIRS,
            "caller_supplied_approval_is_not_authority": True,
        },
        "aggregate_policy": "computed_by_evaluator_from_bound_raw_samples_only",
    }
