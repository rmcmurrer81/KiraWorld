"""Static-only R6 trust guards for the TemporaryAI Qwen3-TTS voice forge.

R6 is an append-only successor to the independently rejected R5 payload.  It
does not import Torch, Torchaudio, Qwen3-TTS, an evaluator, or any predecessor
worker.  The shipped payload and authorization template remain inert.  These
stdlib-only guards close four R5 trust gaps: semantic output binding, a
worker-owned one-use launch claim, complete later-use reopening, and parent
reconciliation of evaluator/resource evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


HASH = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
ZERO_HASH = "0" * 64

R6_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json"
)
R5_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json"
)
R5_PAYLOAD_MANIFEST_SHA256 = (
    "92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b"
)
R5_REJECTED_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_20260809.md"
)
R5_REJECTED_AUDIT_SHA256 = (
    "82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a"
)
R6_AUTHORIZATION_ROOT_REL = Path(
    "Data/voice/authorizations/qwen3_tts_voice_forge_v6"
)
R6_PARENT_LEDGER_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v6"
)
R6_WORKER_CLAIM_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_worker_launch_claims_v6"
)

ELIGIBLE_AI_TYPES = {"expert_temp_ai", "generated_original_temp_ai"}
FINAL_DISABLED_PERMISSIONS = {
    "assignment_allowed": False,
    "activation_allowed": False,
    "publication_or_upload_allowed": False,
    "owner_hearing_acceptance": "PENDING",
}

CORE_BINDING_KEYS = {
    "bundle_id",
    "candidate_id",
    "ai_type",
    "opaque_voice_id",
    "job_sha256",
    "owner_authorization_sha256",
    "queue_binding_sha256",
    "canonical_profile_sha256",
    "canonical_creation_request_sha256",
}

R5_PROFILE_ADDITIONS = {
    "r5_status",
    "payload_manifest_sha256",
    "execution_authorization",
    "authorization_ledger_sha256",
    "exact_provenance_sha256",
    "parent_finalization_required",
    "later_use_acceptance_reopen_required",
    "independent_execution_audit",
}

R5_MANIFEST_KEYS = {
    "schema",
    "status",
    "bundle_id",
    "run_id",
    "payload_manifest_sha256",
    "execution_authorization_sha256",
    "authorization_nonce_sha256",
    "authorization_ledger_sha256",
    "predecessor_worker_manifest_sha256",
    "predecessor_profile_sha256",
    "profile_sha256",
    "artifact_seals",
    "artifact_seals_sha256",
    "strict_wheel_binding_parent_preflight",
    "strict_wheel_binding_worker_pre_model",
    "strict_wheel_binding_worker_post_execution",
    "full_provenance_parent_preflight",
    "full_provenance_worker_pre_model",
    "full_provenance_worker_post_execution",
    "exact_provenance_sha256",
    "unbound_installer_generated_package_bytes_allowed",
    "parent_fresh_postflight_required",
    "parent_owned_finalization_required",
    "clean_process_tree_exit",
    "owner_hearing_acceptance",
    "activation_assignment_publication_or_upload_allowed",
}

R6_PROFILE_ADDITIONS = {
    "r6_status",
    "predecessor_r5_profile_sha256",
    "semantic_binding_v6",
    "semantic_binding_v6_sha256",
    "evaluator_evidence_path",
    "evaluator_evidence_sha256",
    "resource_evidence_path",
    "resource_evidence_sha256",
    "worker_launch_claim_path",
    "worker_launch_claim_sha256",
    "parent_authorization_ledger_path",
    "parent_authorization_ledger_sha256",
    "artifact_seals_sha256",
    "complete_later_use_revalidation_required",
}

SEMANTIC_BINDING_KEYS = CORE_BINDING_KEYS | {
    "run_id",
    "attempt",
    "payload_manifest_sha256",
    "execution_authorization_sha256",
    "execution_authorization_nonce_sha256",
    "parent_reservation_sha256",
    "parent_authorization_ledger_sha256",
    "worker_launch_claim_sha256",
    "r4_worker_manifest_sha256",
    "r4_profile_sha256",
    "r5_worker_manifest_sha256",
    "r5_profile_sha256",
    "reference_wav_sha256",
    "clone_test_wav_sha256",
    "runtime_clone_prompt_sha256",
    "reference_transcript_sha256",
    "clone_transcript_sha256",
    "reference_text_sha256",
    "test_text_sha256",
    "original_trait_prompt_sha256",
    "generation_seed",
    "voice_design_model_revision",
    "voice_design_model_manifest_sha256",
    "base_model_revision",
    "base_model_manifest_sha256",
    "artifact_seals_sha256",
    "evaluator_evidence_sha256",
    "resource_evidence_sha256",
}

R6_MANIFEST_KEYS = {
    "schema",
    "status",
    "semantic_binding_v6",
    "semantic_binding_v6_sha256",
    "profile_sha256",
    "predecessor_worker_manifest_sha256",
    "predecessor_profile_sha256",
    "worker_launch_claim_path",
    "worker_launch_claim_sha256",
    "parent_authorization_ledger_path",
    "parent_authorization_ledger_sha256",
    "artifact_seals",
    "artifact_seals_sha256",
    "evaluator_evidence_path",
    "evaluator_evidence_sha256",
    "resource_evidence_path",
    "resource_evidence_sha256",
    "process_tree_quiescence_required_before_parent_finalization",
    "parent_evaluator_and_resource_reconciliation_required",
    "owner_hearing_acceptance",
    "assignment_allowed",
    "activation_allowed",
    "publication_or_upload_allowed",
}

R6_CHILD_KEYS = {
    "schema",
    "status",
    "semantic_binding_v6_sha256",
    "manifest_path",
    "manifest_sha256",
    "profile_path",
    "profile_sha256",
    "evaluator_evidence_path",
    "evaluator_evidence_sha256",
    "worker_resource_evidence_path",
    "worker_resource_evidence_sha256",
    "worker_launch_claim_path",
    "worker_launch_claim_sha256",
    "artifact_seals_sha256",
}

EVALUATOR_EVIDENCE_KEYS = {
    "schema",
    "status",
    "semantic_binding_sha256",
    "reference_wav_sha256",
    "clone_test_wav_sha256",
    "runtime_clone_prompt_sha256",
    "reference_transcript_sha256",
    "clone_transcript_sha256",
    "asr_and_speech",
    "pure_tone",
    "speaker_identity",
    "collision_corpus",
    "named_person_clearance",
    "watermark",
    "predecessor_audio_acceptance_sha256",
    "predecessor_evaluator_import_bindings_sha256",
    "predecessor_r2_manifest_sha256",
}

ASR_ROW_KEYS = {
    "role",
    "source_wav_sha256",
    "expected_text_sha256",
    "transcript_sha256",
    "asr_mode",
    "asr_engine",
    "asr_version",
    "asr_model_manifest_sha256",
    "speech_mode",
    "speech_classifier_engine",
    "speech_classifier_version",
    "speech_classifier_model_manifest_sha256",
    "speech_classifier_adapter_sha256",
    "word_error_rate",
    "maximum_word_error_rate",
    "speech_probability",
    "minimum_speech_probability",
    "accepted",
}

TONE_ROW_KEYS = {
    "role",
    "source_wav_sha256",
    "detector",
    "pure_tone_probability",
    "maximum_pure_tone_probability",
    "pure_tone_rejected",
}

WORKER_TELEMETRY_KEYS = {
    "rss_sampler",
    "os_reported_peak_process_rss_bytes",
    "os_reported_peak_process_rss_is_high_water_mark",
    "baseline_process_rss_bytes",
    "baseline_cuda_allocated_bytes",
    "baseline_cuda_reserved_bytes",
    "torch_peak_cuda_allocated_bytes",
    "torch_peak_cuda_reserved_bytes",
    "after_design_load_observed_cuda_allocated_bytes",
    "after_design_load_observed_cuda_reserved_bytes",
    "after_base_load_observed_cuda_allocated_bytes",
    "after_base_load_observed_cuda_reserved_bytes",
    "after_design_unload_cuda_allocated_bytes",
    "final_cuda_allocated_bytes",
    "final_cuda_reserved_bytes",
    "design_generation_observed_cuda_allocated_bytes",
    "clone_generation_observed_cuda_allocated_bytes",
    "point_samples_labeled_as_peaks",
}

TIMING_KEYS = {
    "voice_design_load",
    "voice_design_generation",
    "base_load",
    "clone_prompt",
    "clone_generation",
    "total_worker",
}

PARENT_OBSERVATION_KEYS = {
    "schema",
    "observed_by_parent_not_child",
    "windows_job_assigned_before_resume",
    "primary_worker_exit_code",
    "job_termination_requested_after_primary_exit",
    "active_processes_after_termination",
    "process_tree_quiescent_before_finalization",
    "quiescence_observed_utc",
    "finalization_started_utc",
    "parent_wall_seconds",
    "peak_process_memory_used_bytes",
    "peak_job_memory_used_bytes",
    "io_read_operation_count",
    "io_write_operation_count",
    "io_read_bytes",
    "io_write_bytes",
    "worker_stdout_bytes",
    "worker_stdout_sha256",
    "worker_stderr_bytes",
    "worker_stderr_sha256",
}

WORKER_RESOURCE_EVIDENCE_KEYS = {
    "schema",
    "status",
    "semantic_binding_sha256",
    "worker_reported_telemetry",
    "worker_reported_telemetry_sha256",
    "worker_reported_timings_seconds",
    "worker_reported_timings_sha256",
    "worker_reported_events",
    "worker_reported_events_sha256",
}

RESOURCE_EVIDENCE_KEYS = {
    "schema",
    "status",
    "semantic_binding_sha256",
    "worker_resource_evidence_sha256",
    "parent_job_observation",
    "parent_job_observation_sha256",
    "worker_only_telemetry_accepted_as_parent_truth",
    "reconciliation_passed",
}

ACCEPTED_FILE_ROW_KEYS = {"role", "path", "bytes", "sha256"}

ACCEPTANCE_KEYS = {
    "schema",
    "status",
    "accepted_utc",
    "authorization_verified_at_start_utc",
    "semantic_binding_v6",
    "semantic_binding_v6_sha256",
    "payload_manifest_path",
    "payload_manifest_sha256",
    "execution_authorization_path",
    "execution_authorization_sha256",
    "independent_r6_audit_path",
    "independent_r6_audit_sha256",
    "rejected_r5_audit_path",
    "rejected_r5_audit_sha256",
    "parent_authorization_ledger_path",
    "parent_authorization_ledger_sha256",
    "worker_launch_claim_path",
    "worker_launch_claim_sha256",
    "accepted_files",
    "accepted_files_sha256",
    "owner_hearing_acceptance",
    "assignment_allowed",
    "activation_allowed",
    "publication_or_upload_allowed",
    "complete_later_use_revalidation_required",
}


class R6GuardError(RuntimeError):
    """An R6 static trust or evidence boundary failed closed."""


class R6CollisionError(R6GuardError):
    """An append-only authorization, attempt, or launch claim was reused."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise R6GuardError(f"{label} is not an exact UTC timestamp") from exc
    if parsed.tzinfo is None:
        raise R6GuardError(f"{label} lacks a timezone")
    return parsed.astimezone(timezone.utc)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(value: Any, label: str, *, nonzero: bool = True) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text) or (nonzero and text == ZERO_HASH):
        raise R6GuardError(f"{label} is not one nonzero lowercase SHA-256")
    return text


def require_id(value: Any, label: str) -> str:
    text = str(value or "")
    if not SAFE_ID.fullmatch(text):
        raise R6GuardError(f"{label} is not a safe opaque ID")
    return text


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R6GuardError(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


def strict_json_bytes(payload: bytes, label: str) -> Any:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise R6GuardError(f"{label} is not UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except R6GuardError:
        raise
    except json.JSONDecodeError as exc:
        raise R6GuardError(f"{label} is not exact JSON") from exc


def strict_read_json(
    path: Path, *, expected_sha256: str | None = None, label: str | None = None
) -> dict[str, Any]:
    label = label or path.as_posix()
    if not path.is_file() or path.is_symlink():
        raise R6GuardError(f"{label} is missing, non-regular, or a symlink")
    payload = path.read_bytes()
    if expected_sha256 is not None and sha256_bytes(payload) != require_hash(
        expected_sha256, f"{label} expected hash"
    ):
        raise R6GuardError(f"{label} differs from its exact hash binding")
    value = strict_json_bytes(payload, label)
    if not isinstance(value, dict):
        raise R6GuardError(f"{label} is not a JSON object")
    return value


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise R6CollisionError(f"append-only evidence already exists: {path}") from exc


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    write_new(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n",
    )


def reserve_incident(root: Path, bundle_id: str, run_id: str) -> Path:
    """Reserve an append-only bootstrap/failure slot before a bounded attempt."""

    require_id(bundle_id, "R6 incident bundle")
    require_id(run_id, "R6 incident run")
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(64):
        incident = root / f"{run_id}_{bundle_id}_{secrets.token_hex(16)}"
        try:
            incident.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        write_new_json(
            incident / "INCIDENT_SLOT.json",
            {
                "schema": "qwen3_tts_voice_forge_incident_slot_v6",
                "status": "RESERVED_APPEND_ONLY_BEFORE_ATTEMPT",
                "utc": utc_now(),
                "bundle_id": bundle_id,
                "run_id": run_id,
            },
        )
        return incident
    raise R6CollisionError("no collision-free R6 incident slot could be reserved")


def inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(str(value))
    result = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R6GuardError(f"{label} escaped its exact root") from exc
    return result


def project_relative(project_root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise R6GuardError(f"{label} escaped the project") from exc


def require_exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        missing = sorted(keys - set(value if isinstance(value, dict) else {}))
        extra = sorted(set(value if isinstance(value, dict) else {}) - keys)
        raise R6GuardError(f"{label} fields are not exact; missing={missing}, extra={extra}")
    return value


def verify_payload_manifest(
    *, project_root: Path, expected_manifest_sha256: str, required_payloads: set[str]
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    project_root = project_root.resolve()
    path = project_root / R6_PAYLOAD_MANIFEST_REL
    manifest = strict_read_json(
        path,
        expected_sha256=require_hash(expected_manifest_sha256, "R6 payload hash"),
        label="R6 immutable payload manifest",
    )
    require_exact_keys(
        manifest,
        {
            "schema",
            "status",
            "execution_allowed",
            "self_authorization_allowed",
            "revision",
            "predecessor_payload_manifest_path",
            "predecessor_payload_manifest_sha256",
            "rejected_r5_audit_path",
            "rejected_r5_audit_sha256",
            "files",
        },
        "R6 payload manifest",
    )
    if (
        manifest["schema"] != "qwen3_tts_voice_forge_payload_manifest_v6"
        or manifest["status"]
        != "IMMUTABLE_STATIC_PAYLOAD_REQUIRES_FRESH_AUDIT_AND_EXTERNAL_AUTHORIZATION"
        or manifest["execution_allowed"] is not False
        or manifest["self_authorization_allowed"] is not False
        or manifest["predecessor_payload_manifest_path"]
        != R5_PAYLOAD_MANIFEST_REL.as_posix()
        or manifest["predecessor_payload_manifest_sha256"]
        != R5_PAYLOAD_MANIFEST_SHA256
        or manifest["rejected_r5_audit_path"] != R5_REJECTED_AUDIT_REL.as_posix()
        or manifest["rejected_r5_audit_sha256"] != R5_REJECTED_AUDIT_SHA256
    ):
        raise R6GuardError("R6 payload self-authorized or lost its exact rejected predecessor")
    if sha256_file(project_root / R5_PAYLOAD_MANIFEST_REL) != R5_PAYLOAD_MANIFEST_SHA256:
        raise R6GuardError("sealed R5 payload manifest drifted")
    if sha256_file(project_root / R5_REJECTED_AUDIT_REL) != R5_REJECTED_AUDIT_SHA256:
        raise R6GuardError("sealed rejected R5 audit drifted")
    rows = manifest["files"]
    if not isinstance(rows, list):
        raise R6GuardError("R6 payload file inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        require_exact_keys(row, {"path", "bytes", "sha256"}, "R6 payload row")
        rel = str(row["path"] or "")
        if not rel or rel in indexed or rel == R6_PAYLOAD_MANIFEST_REL.as_posix():
            raise R6GuardError("R6 payload row is empty, duplicate, or self-referential")
        target = inside(project_root, rel, "R6 payload file")
        if (
            not target.is_file()
            or target.is_symlink()
            or not isinstance(row["bytes"], int)
            or row["bytes"] < 0
            or target.stat().st_size != row["bytes"]
            or sha256_file(target) != require_hash(row["sha256"], f"R6 payload {rel}")
        ):
            raise R6GuardError(f"R6 immutable payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != set(required_payloads):
        raise R6GuardError("R6 immutable payload inventory is not exact")
    return manifest, indexed


def verify_execution_authorization(
    *,
    project_root: Path,
    authorization_path: Path,
    expected_authorization_sha256: str,
    expected_manifest_sha256: str,
    bundle_id: str,
    run_id: str,
    verified_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    authorization_path = authorization_path.resolve()
    rel = project_relative(project_root, authorization_path, "R6 authorization")
    if not rel.startswith(R6_AUTHORIZATION_ROOT_REL.as_posix() + "/"):
        raise R6GuardError("R6 authorization is outside its append-only authority root")
    auth_hash = require_hash(expected_authorization_sha256, "R6 authorization hash")
    authorization = strict_read_json(
        authorization_path,
        expected_sha256=auth_hash,
        label="R6 execution authorization",
    )
    keys = {
        "schema",
        "status",
        "execution_allowed",
        "one_use",
        "payload_manifest_path",
        "payload_manifest_sha256",
        "independent_audit_path",
        "independent_audit_sha256",
        "rejected_r5_audit_path",
        "rejected_r5_audit_sha256",
        "bundle_id",
        "run_id",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "generation_seed",
        "issued_utc",
        "expires_utc",
    }
    require_exact_keys(authorization, keys, "R6 execution authorization")
    if (
        authorization["schema"] != "qwen3_tts_voice_forge_execution_authorization_v6"
        or authorization["status"] != "FRESH_R6_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization["execution_allowed"] is not True
        or authorization["one_use"] is not True
        or authorization["payload_manifest_path"] != R6_PAYLOAD_MANIFEST_REL.as_posix()
        or authorization["payload_manifest_sha256"]
        != require_hash(expected_manifest_sha256, "R6 expected payload hash")
        or authorization["rejected_r5_audit_path"] != R5_REJECTED_AUDIT_REL.as_posix()
        or authorization["rejected_r5_audit_sha256"] != R5_REJECTED_AUDIT_SHA256
        or authorization["bundle_id"] != require_id(bundle_id, "R6 bundle ID")
        or authorization["run_id"] != require_id(run_id, "R6 run ID")
    ):
        raise R6GuardError("R6 authorization scope or rejected-predecessor binding mismatch")
    require_hash(authorization["authorization_nonce_sha256"], "R6 authorization nonce")
    require_hash(authorization["worker_instance_nonce_sha256"], "R6 worker instance nonce")
    if (
        not isinstance(authorization["generation_seed"], int)
        or isinstance(authorization["generation_seed"], bool)
        or not (0 <= authorization["generation_seed"] < 2**63)
    ):
        raise R6GuardError("R6 generation seed is not one bounded integer")
    if sha256_file(project_root / R5_REJECTED_AUDIT_REL) != R5_REJECTED_AUDIT_SHA256:
        raise R6GuardError("R6 authorization's rejected R5 audit drifted")
    audit_rel = str(authorization["independent_audit_path"] or "")
    if (
        not audit_rel.startswith("System/Docs/")
        or "TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_"
        not in audit_rel
    ):
        raise R6GuardError("R6 authorization names no fresh independent R6 audit")
    audit_path = inside(project_root, audit_rel, "R6 independent audit")
    audit_hash = require_hash(authorization["independent_audit_sha256"], "R6 audit hash")
    if not audit_path.is_file() or audit_path.is_symlink() or sha256_file(audit_path) != audit_hash:
        raise R6GuardError("R6 independent audit path/hash mismatch")
    issued = parse_utc(authorization["issued_utc"], "R6 issued_utc")
    expires = parse_utc(authorization["expires_utc"], "R6 expires_utc")
    observed = (verified_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued > observed or observed > expires:
        raise R6GuardError("R6 authorization was not valid at the trusted verification time")
    evidence = {
        "path": rel,
        "bytes": authorization_path.stat().st_size,
        "sha256": auth_hash,
        "payload_manifest_sha256": authorization["payload_manifest_sha256"],
        "independent_audit_path": audit_rel,
        "independent_audit_sha256": audit_hash,
        "rejected_r5_audit_path": R5_REJECTED_AUDIT_REL.as_posix(),
        "rejected_r5_audit_sha256": R5_REJECTED_AUDIT_SHA256,
    }
    return authorization, evidence


def validate_parent_ledger(
    ledger: dict[str, Any], *, expected: dict[str, Any]
) -> dict[str, Any]:
    keys = {
        "schema",
        "status",
        "utc",
        "authorization_sha256",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "payload_manifest_sha256",
        "bundle_id",
        "run_id",
        "attempt",
        "parent_reservation_path",
        "parent_reservation_sha256",
        "verified_worker_path",
        "verified_worker_sha256",
    }
    require_exact_keys(ledger, keys, "R6 parent authorization ledger")
    if (
        ledger["schema"] != "qwen3_tts_voice_forge_authorization_ledger_v6"
        or ledger["status"] != "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT"
        or any(ledger.get(key) != expected.get(key) for key in keys - {"schema", "status", "utc"})
    ):
        raise R6GuardError("R6 parent authorization ledger binding mismatch")
    parse_utc(ledger["utc"], "R6 parent ledger utc")
    for key in (
        "authorization_sha256",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "payload_manifest_sha256",
        "parent_reservation_sha256",
        "verified_worker_sha256",
    ):
        require_hash(ledger[key], f"R6 ledger {key}")
    return ledger


def validate_parent_reservation(
    reservation: dict[str, Any], *, expected: dict[str, Any]
) -> dict[str, Any]:
    """Validate the stable append-only parent reservation semantically."""

    keys = {
        "schema",
        "status",
        "bundle_id",
        "run_id",
        "attempt",
        "payload_manifest_sha256",
        "execution_authorization_sha256",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "generation_seed",
        "parent_authorization_ledger_path",
        "verified_entry_worker_path",
        "verified_entry_worker_sha256",
        "exact_parent_preflight_provenance",
        "exact_parent_full_provenance",
        "exact_parent_full_provenance_sha256",
        "frozen_parent_reservation_sha256",
    }
    require_exact_keys(reservation, keys, "R6 parent reservation")
    if (
        reservation["schema"]
        != "qwen3_tts_voice_forge_parent_reservation_v6"
        or reservation["status"]
        != "EXTERNAL_AUTHORITY_PARENT_PREFLIGHT_AND_WORKER_IDENTITY_RESERVED"
        or any(reservation.get(key) != value for key, value in expected.items())
    ):
        raise R6GuardError("R6 parent reservation binding mismatch")
    for key in (
        "payload_manifest_sha256",
        "execution_authorization_sha256",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "verified_entry_worker_sha256",
        "exact_parent_full_provenance_sha256",
        "frozen_parent_reservation_sha256",
    ):
        require_hash(reservation[key], f"R6 parent reservation {key}")
    if not isinstance(reservation["generation_seed"], int) or isinstance(
        reservation["generation_seed"], bool
    ):
        raise R6GuardError("R6 parent reservation seed is not an integer")
    if not isinstance(reservation["exact_parent_preflight_provenance"], dict):
        raise R6GuardError("R6 parent reservation preflight is not an object")
    if canonical_sha256(reservation["exact_parent_full_provenance"]) != reservation[
        "exact_parent_full_provenance_sha256"
    ]:
        raise R6GuardError("R6 parent reservation provenance digest mismatch")
    return reservation


def worker_claim_path(project_root: Path, authorization_sha256: str) -> Path:
    auth_hash = require_hash(authorization_sha256, "R6 worker claim authorization")
    return (project_root.resolve() / R6_WORKER_CLAIM_ROOT_REL / f"{auth_hash}.json").resolve()


def create_worker_launch_claim(
    *,
    project_root: Path,
    authorization_sha256: str,
    authorization_nonce_sha256: str,
    worker_instance_nonce_sha256: str,
    payload_manifest_sha256: str,
    bundle_id: str,
    run_id: str,
    attempt: str,
    parent_reservation_path: str,
    parent_reservation_sha256: str,
    parent_ledger_path: str,
    parent_ledger_sha256: str,
    worker_path: str,
    worker_sha256: str,
    worker_pid: int,
    created_utc: str | None = None,
) -> tuple[Path, dict[str, Any], str]:
    if not isinstance(worker_pid, int) or worker_pid <= 0:
        raise R6GuardError("R6 worker PID is not positive")
    claim = {
        "schema": "qwen3_tts_voice_forge_worker_launch_claim_v6",
        "status": "WORKER_CLAIMED_ONE_USE_BEFORE_PREDECESSOR_OR_MODEL_IMPORT",
        "utc": created_utc or utc_now(),
        "authorization_sha256": require_hash(authorization_sha256, "R6 claim auth"),
        "authorization_nonce_sha256": require_hash(authorization_nonce_sha256, "R6 claim nonce"),
        "worker_instance_nonce_sha256": require_hash(worker_instance_nonce_sha256, "R6 worker nonce"),
        "payload_manifest_sha256": require_hash(payload_manifest_sha256, "R6 claim payload"),
        "bundle_id": require_id(bundle_id, "R6 claim bundle"),
        "run_id": require_id(run_id, "R6 claim run"),
        "attempt": str(attempt),
        "parent_reservation_path": str(parent_reservation_path),
        "parent_reservation_sha256": require_hash(parent_reservation_sha256, "R6 claim reservation"),
        "parent_ledger_path": str(parent_ledger_path),
        "parent_ledger_sha256": require_hash(parent_ledger_sha256, "R6 claim ledger"),
        "worker_path": str(worker_path),
        "worker_sha256": require_hash(worker_sha256, "R6 claim worker"),
        "worker_pid": worker_pid,
    }
    path = worker_claim_path(project_root, authorization_sha256)
    write_new_json(path, claim)
    digest = sha256_file(path)
    reopened = strict_read_json(path, expected_sha256=digest, label="R6 worker launch claim")
    if reopened != claim:
        raise R6GuardError("R6 worker launch claim changed after exclusive creation")
    return path, claim, digest


def validate_worker_launch_claim(
    claim: dict[str, Any], *, expected: dict[str, Any]
) -> dict[str, Any]:
    keys = {
        "schema",
        "status",
        "utc",
        "authorization_sha256",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "payload_manifest_sha256",
        "bundle_id",
        "run_id",
        "attempt",
        "parent_reservation_path",
        "parent_reservation_sha256",
        "parent_ledger_path",
        "parent_ledger_sha256",
        "worker_path",
        "worker_sha256",
        "worker_pid",
    }
    require_exact_keys(claim, keys, "R6 worker launch claim")
    if (
        claim["schema"] != "qwen3_tts_voice_forge_worker_launch_claim_v6"
        or claim["status"]
        != "WORKER_CLAIMED_ONE_USE_BEFORE_PREDECESSOR_OR_MODEL_IMPORT"
        or any(claim.get(key) != expected.get(key) for key in keys - {"schema", "status", "utc", "worker_pid"})
        or not isinstance(claim["worker_pid"], int)
        or claim["worker_pid"] <= 0
    ):
        raise R6GuardError("R6 worker claim is not bound to the exact parent launch")
    parse_utc(claim["utc"], "R6 worker claim utc")
    return claim


def validate_core_binding(value: dict[str, Any], label: str) -> dict[str, Any]:
    require_exact_keys(value, CORE_BINDING_KEYS, label)
    for key in ("bundle_id", "candidate_id", "opaque_voice_id"):
        require_id(value[key], f"{label} {key}")
    if value["ai_type"] not in ELIGIBLE_AI_TYPES:
        raise R6GuardError(f"{label} ai_type is not eligible for original voice design")
    for key in CORE_BINDING_KEYS - {"bundle_id", "candidate_id", "ai_type", "opaque_voice_id"}:
        require_hash(value[key], f"{label} {key}")
    return value


def validate_semantic_binding(value: dict[str, Any]) -> dict[str, Any]:
    require_exact_keys(value, SEMANTIC_BINDING_KEYS, "R6 semantic binding")
    validate_core_binding({key: value[key] for key in CORE_BINDING_KEYS}, "R6 core binding")
    require_id(value["run_id"], "R6 semantic run ID")
    if not str(value["attempt"] or ""):
        raise R6GuardError("R6 semantic attempt is empty")
    for key in SEMANTIC_BINDING_KEYS - CORE_BINDING_KEYS - {
        "run_id",
        "attempt",
        "generation_seed",
        "voice_design_model_revision",
        "base_model_revision",
    }:
        require_hash(value[key], f"R6 semantic {key}")
    if (
        not isinstance(value["generation_seed"], int)
        or isinstance(value["generation_seed"], bool)
        or not (0 <= value["generation_seed"] < 2**63)
    ):
        raise R6GuardError("R6 semantic generation seed is invalid")
    if not str(value["voice_design_model_revision"] or "").strip() or not str(
        value["base_model_revision"] or ""
    ).strip():
        raise R6GuardError("R6 semantic model revisions are absent")
    return value


def evidence_subject_sha256(semantic_binding: dict[str, Any]) -> str:
    """Hash the non-circular subject to which evidence must be bound.

    The complete semantic binding carries the final evaluator/resource file
    hashes.  Those evidence files cannot themselves hash that complete object
    without a self-reference cycle, so each evidence file binds the exact
    semantic object with only the two evidence-file hash slots omitted.
    """

    validate_semantic_binding(semantic_binding)
    subject = {
        key: value
        for key, value in semantic_binding.items()
        if key not in {"evaluator_evidence_sha256", "resource_evidence_sha256"}
    }
    return canonical_sha256(subject)


def _safe_permissions(value: dict[str, Any], label: str) -> None:
    for key, expected in FINAL_DISABLED_PERMISSIONS.items():
        if value.get(key) != expected:
            raise R6GuardError(f"{label} overstates {key}")


def validate_r5_safe_extension(
    *,
    r4_profile: dict[str, Any],
    r5_profile: dict[str, Any],
    expected_core: dict[str, Any],
    expected_r4_profile_sha256: str,
    expected_payload_sha256: str,
    expected_authorization_sha256: str,
    expected_parent_ledger_sha256: str,
) -> dict[str, Any]:
    validate_core_binding(expected_core, "parent-derived core")
    expected_keys = set(r4_profile) | R5_PROFILE_ADDITIONS
    require_exact_keys(r5_profile, expected_keys, "R5 predecessor profile")
    if r4_profile.get("schema") != "qwen3_tts_original_voice_profile_candidate_v4":
        raise R6GuardError("R4 predecessor profile schema mismatch")
    if r5_profile.get("schema") != "qwen3_tts_original_voice_profile_candidate_v5":
        raise R6GuardError("R5 predecessor profile schema mismatch")
    for key, value in r4_profile.items():
        if key != "schema" and r5_profile.get(key) != value:
            raise R6GuardError(f"R5 profile is not a safe exact R4 extension: {key}")
    for key, expected in expected_core.items():
        if r4_profile.get(key) != expected or r5_profile.get(key) != expected:
            raise R6GuardError(f"R4/R5 profile semantic identity mismatch: {key}")
    _safe_permissions(r4_profile, "R4 profile")
    _safe_permissions(r5_profile, "R5 profile")
    if (
        r5_profile["r5_status"] != "PRIVATE_UNREVIEWED_PARENT_FINALIZATION_PENDING"
        or r5_profile["payload_manifest_sha256"] != expected_payload_sha256
        or r5_profile["authorization_ledger_sha256"] != expected_parent_ledger_sha256
        or r5_profile["parent_finalization_required"] is not True
        or r5_profile["later_use_acceptance_reopen_required"] is not True
        or r5_profile["independent_execution_audit"] != "REQUIRED_AFTER_BOUNDED_RUN"
    ):
        raise R6GuardError("R5 profile control fields are unsafe")
    authorization = r5_profile["execution_authorization"]
    if not isinstance(authorization, dict) or authorization.get("sha256") != expected_authorization_sha256:
        raise R6GuardError("R5 profile authorization evidence is not parent-bound")
    require_hash(expected_r4_profile_sha256, "expected R4 profile hash")
    return r5_profile


def validate_r5_manifest(
    *,
    manifest: dict[str, Any],
    expected_core: dict[str, Any],
    expected_run_id: str,
    expected_r4_manifest_sha256: str,
    expected_r4_profile_sha256: str,
    expected_r5_profile_sha256: str,
    expected_payload_sha256: str,
    expected_authorization_sha256: str,
    expected_parent_ledger_sha256: str,
) -> dict[str, Any]:
    require_exact_keys(manifest, R5_MANIFEST_KEYS, "R5 predecessor manifest")
    if (
        manifest["schema"] != "qwen3_tts_original_voice_forge_worker_manifest_v5"
        or manifest["status"]
        != "CHILD_ENGINEERING_GATES_PASSED_PARENT_FINALIZATION_PENDING"
        or manifest["bundle_id"] != expected_core["bundle_id"]
        or manifest["run_id"] != expected_run_id
        or manifest["payload_manifest_sha256"] != expected_payload_sha256
        or manifest["execution_authorization_sha256"] != expected_authorization_sha256
        or manifest["authorization_ledger_sha256"] != expected_parent_ledger_sha256
        or manifest["predecessor_worker_manifest_sha256"] != expected_r4_manifest_sha256
        or manifest["predecessor_profile_sha256"] != expected_r4_profile_sha256
        or manifest["profile_sha256"] != expected_r5_profile_sha256
        or manifest["unbound_installer_generated_package_bytes_allowed"] is not False
        or manifest["parent_fresh_postflight_required"] is not True
        or manifest["parent_owned_finalization_required"] is not True
        or manifest["owner_hearing_acceptance"] != "PENDING"
        or manifest["activation_assignment_publication_or_upload_allowed"] is not False
    ):
        raise R6GuardError("R5 predecessor manifest semantic binding mismatch")
    if canonical_sha256(manifest["artifact_seals"]) != require_hash(
        manifest["artifact_seals_sha256"], "R5 artifact seals"
    ):
        raise R6GuardError("R5 artifact seals digest mismatch")
    return manifest


def validate_r6_profile_and_manifest(
    *,
    r5_profile: dict[str, Any],
    r6_profile: dict[str, Any],
    r6_manifest: dict[str, Any],
    child_result: dict[str, Any],
    semantic_binding: dict[str, Any],
    r5_profile_sha256: str,
    r5_manifest_sha256: str,
    r6_profile_sha256: str,
) -> None:
    validate_semantic_binding(semantic_binding)
    semantic_hash = canonical_sha256(semantic_binding)
    require_exact_keys(r6_profile, set(r5_profile) | R6_PROFILE_ADDITIONS, "R6 profile")
    if r6_profile.get("schema") != "qwen3_tts_original_voice_profile_candidate_v6":
        raise R6GuardError("R6 profile schema mismatch")
    for key, value in r5_profile.items():
        if key != "schema" and r6_profile.get(key) != value:
            raise R6GuardError(f"R6 profile is not an exact safe R5 extension: {key}")
    _safe_permissions(r6_profile, "R6 profile")
    if (
        r6_profile["r6_status"] != "PRIVATE_UNREVIEWED_COMPLETE_PARENT_RECONCILIATION_PENDING"
        or r6_profile["predecessor_r5_profile_sha256"] != r5_profile_sha256
        or r6_profile["semantic_binding_v6"] != semantic_binding
        or r6_profile["semantic_binding_v6_sha256"] != semantic_hash
        or r6_profile["evaluator_evidence_sha256"] != semantic_binding["evaluator_evidence_sha256"]
        or r6_profile["evaluator_evidence_path"] != "evaluator_evidence_v6.json"
        or r6_profile["resource_evidence_sha256"] != semantic_binding["resource_evidence_sha256"]
        or r6_profile["resource_evidence_path"] != "worker_resource_evidence_v6.json"
        or r6_profile["worker_launch_claim_sha256"] != semantic_binding["worker_launch_claim_sha256"]
        or r6_profile["parent_authorization_ledger_sha256"]
        != semantic_binding["parent_authorization_ledger_sha256"]
        or r6_profile["artifact_seals_sha256"] != semantic_binding["artifact_seals_sha256"]
        or r6_profile["complete_later_use_revalidation_required"] is not True
    ):
        raise R6GuardError("R6 profile semantic/evidence binding mismatch")

    require_exact_keys(r6_manifest, R6_MANIFEST_KEYS, "R6 worker manifest")
    if (
        r6_manifest["schema"] != "qwen3_tts_original_voice_forge_worker_manifest_v6"
        or r6_manifest["status"]
        != "CHILD_GATES_PASSED_PARENT_RECONCILIATION_AND_FINALIZATION_PENDING"
        or r6_manifest["semantic_binding_v6"] != semantic_binding
        or r6_manifest["semantic_binding_v6_sha256"] != semantic_hash
        or r6_manifest["profile_sha256"] != r6_profile_sha256
        or r6_manifest["predecessor_worker_manifest_sha256"] != r5_manifest_sha256
        or r6_manifest["predecessor_profile_sha256"] != r5_profile_sha256
        or r6_manifest["worker_launch_claim_sha256"]
        != semantic_binding["worker_launch_claim_sha256"]
        or r6_manifest["worker_launch_claim_path"]
        != r6_profile["worker_launch_claim_path"]
        or r6_manifest["parent_authorization_ledger_sha256"]
        != semantic_binding["parent_authorization_ledger_sha256"]
        or r6_manifest["parent_authorization_ledger_path"]
        != r6_profile["parent_authorization_ledger_path"]
        or r6_manifest["evaluator_evidence_sha256"]
        != semantic_binding["evaluator_evidence_sha256"]
        or r6_manifest["evaluator_evidence_path"] != "evaluator_evidence_v6.json"
        or r6_manifest["resource_evidence_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or r6_manifest["resource_evidence_path"]
        != "worker_resource_evidence_v6.json"
        or r6_manifest["artifact_seals_sha256"]
        != semantic_binding["artifact_seals_sha256"]
        or canonical_sha256(r6_manifest["artifact_seals"])
        != r6_manifest["artifact_seals_sha256"]
        or r6_manifest["process_tree_quiescence_required_before_parent_finalization"] is not True
        or r6_manifest["parent_evaluator_and_resource_reconciliation_required"] is not True
    ):
        raise R6GuardError("R6 worker manifest semantic/evidence binding mismatch")
    _safe_permissions(r6_manifest, "R6 manifest")

    require_exact_keys(child_result, R6_CHILD_KEYS, "R6 child result")
    if (
        child_result["schema"] != "qwen3_tts_original_voice_forge_child_result_v6"
        or child_result["status"] != r6_manifest["status"]
        or child_result["semantic_binding_v6_sha256"] != semantic_hash
        or child_result["manifest_path"] != "worker_manifest_v6.json"
        or child_result["profile_path"] != "voice_profile_candidate_v6.json"
        or child_result["profile_sha256"] != r6_profile_sha256
        or child_result["evaluator_evidence_path"] != "evaluator_evidence_v6.json"
        or child_result["evaluator_evidence_sha256"]
        != semantic_binding["evaluator_evidence_sha256"]
        or child_result["worker_resource_evidence_path"]
        != "worker_resource_evidence_v6.json"
        or child_result["worker_resource_evidence_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or child_result["worker_launch_claim_path"]
        != r6_manifest["worker_launch_claim_path"]
        or child_result["worker_launch_claim_sha256"]
        != semantic_binding["worker_launch_claim_sha256"]
        or child_result["artifact_seals_sha256"]
        != semantic_binding["artifact_seals_sha256"]
    ):
        raise R6GuardError("R6 canonical child result is not fully bound")


def _finite_number(value: Any, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R6GuardError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise R6GuardError(f"{label} is outside its finite range")
    return result


def validate_evaluator_evidence(
    evidence: dict[str, Any], *, semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    validate_semantic_binding(semantic_binding)
    require_exact_keys(evidence, EVALUATOR_EVIDENCE_KEYS, "R6 evaluator evidence")
    if (
        evidence["schema"] != "qwen3_tts_voice_forge_evaluator_evidence_v6"
        or evidence["status"] != "WORKER_EVIDENCE_PARENT_REVALIDATION_REQUIRED"
        or evidence["semantic_binding_sha256"] != evidence_subject_sha256(semantic_binding)
        or evidence["reference_wav_sha256"] != semantic_binding["reference_wav_sha256"]
        or evidence["clone_test_wav_sha256"] != semantic_binding["clone_test_wav_sha256"]
        or evidence["runtime_clone_prompt_sha256"]
        != semantic_binding["runtime_clone_prompt_sha256"]
        or evidence["reference_transcript_sha256"]
        != semantic_binding["reference_transcript_sha256"]
        or evidence["clone_transcript_sha256"]
        != semantic_binding["clone_transcript_sha256"]
    ):
        raise R6GuardError("R6 evaluator evidence is not artifact-bound")
    roles = {
        "reference": (
            semantic_binding["reference_wav_sha256"],
            semantic_binding["reference_text_sha256"],
            semantic_binding["reference_transcript_sha256"],
        ),
        "clone": (
            semantic_binding["clone_test_wav_sha256"],
            semantic_binding["test_text_sha256"],
            semantic_binding["clone_transcript_sha256"],
        ),
    }
    require_exact_keys(evidence["asr_and_speech"], set(roles), "R6 ASR/speech roles")
    require_exact_keys(evidence["pure_tone"], set(roles), "R6 pure-tone roles")
    for role, (wav_hash, text_hash, transcript_hash) in roles.items():
        row = require_exact_keys(evidence["asr_and_speech"][role], ASR_ROW_KEYS, f"R6 {role} ASR")
        if (
            row["role"] != role
            or row["source_wav_sha256"] != wav_hash
            or row["expected_text_sha256"] != text_hash
            or row["transcript_sha256"] != transcript_hash
            or row["asr_mode"] != "REAL_LOCAL_ASR"
            or row["speech_mode"] != "REAL_LOCAL_SPEECH_CLASSIFIER"
            or row["accepted"] is not True
        ):
            raise R6GuardError(f"R6 {role} ASR/speech evidence is not exact")
        for key in (
            "asr_model_manifest_sha256",
            "speech_classifier_model_manifest_sha256",
            "speech_classifier_adapter_sha256",
        ):
            require_hash(row[key], f"R6 {role} {key}")
        wer = _finite_number(row["word_error_rate"], f"R6 {role} WER", minimum=0)
        max_wer = _finite_number(row["maximum_word_error_rate"], f"R6 {role} max WER", minimum=0)
        speech = _finite_number(row["speech_probability"], f"R6 {role} speech probability", minimum=0)
        minimum_speech = _finite_number(
            row["minimum_speech_probability"], f"R6 {role} minimum speech", minimum=0
        )
        if wer > max_wer or speech < minimum_speech:
            raise R6GuardError(f"R6 {role} ASR/speech threshold failed")
        tone = require_exact_keys(
            evidence["pure_tone"][role], TONE_ROW_KEYS, f"R6 {role} pure tone"
        )
        probability = _finite_number(
            tone["pure_tone_probability"], f"R6 {role} tone probability", minimum=0
        )
        maximum = _finite_number(
            tone["maximum_pure_tone_probability"], f"R6 {role} max tone", minimum=0
        )
        if (
            tone["role"] != role
            or tone["source_wav_sha256"] != wav_hash
            or tone["detector"] != "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2"
            or tone["pure_tone_rejected"] is not True
            or probability > maximum
        ):
            raise R6GuardError(f"R6 {role} pure-tone rejection is not bound")

    speaker = require_exact_keys(
        evidence["speaker_identity"],
        {
            "reference_wav_sha256",
            "clone_test_wav_sha256",
            "embedding_mode",
            "embedding_engine",
            "embedding_version",
            "embedding_model_manifest_sha256",
            "reference_to_clone_similarity",
            "minimum_similarity",
            "accepted",
        },
        "R6 speaker identity",
    )
    if (
        speaker["reference_wav_sha256"] != semantic_binding["reference_wav_sha256"]
        or speaker["clone_test_wav_sha256"] != semantic_binding["clone_test_wav_sha256"]
        or speaker["embedding_mode"] != "REAL_LOCAL_SPEAKER_EMBEDDING"
        or speaker["accepted"] is not True
        or _finite_number(speaker["reference_to_clone_similarity"], "R6 speaker similarity")
        < _finite_number(speaker["minimum_similarity"], "R6 minimum speaker similarity")
    ):
        raise R6GuardError("R6 speaker identity evidence failed")
    require_hash(speaker["embedding_model_manifest_sha256"], "R6 speaker model")

    collision = require_exact_keys(
        evidence["collision_corpus"],
        {
            "clone_test_wav_sha256",
            "corpus_manifest_sha256",
            "corpus_snapshot_sha256",
            "all_embeddings_recomputed_from_exact_wavs",
            "collision_results_sha256",
            "maximum_allowed_similarity",
            "no_resident_or_generic_collision",
        },
        "R6 collision corpus",
    )
    if (
        collision["clone_test_wav_sha256"] != semantic_binding["clone_test_wav_sha256"]
        or collision["all_embeddings_recomputed_from_exact_wavs"] is not True
        or collision["no_resident_or_generic_collision"] is not True
    ):
        raise R6GuardError("R6 collision evidence is not exact-WAV/recomputation bound")
    for key in ("corpus_manifest_sha256", "corpus_snapshot_sha256", "collision_results_sha256"):
        require_hash(collision[key], f"R6 collision {key}")
    _finite_number(collision["maximum_allowed_similarity"], "R6 max collision", minimum=0)

    named = require_exact_keys(
        evidence["named_person_clearance"],
        {
            "identity_basis",
            "voice_origin",
            "static_manifest_path",
            "static_manifest_sha256",
            "live_report_path",
            "live_report_sha256",
            "named_person_or_imitation_language_found",
            "cleared",
        },
        "R6 named-person clearance",
    )
    if (
        named["identity_basis"] != "original_trait_description"
        or named["voice_origin"] != "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE"
        or named["named_person_or_imitation_language_found"] is not False
        or named["cleared"] is not True
    ):
        raise R6GuardError("R6 named-person/originality clearance failed")
    require_hash(named["static_manifest_sha256"], "R6 static identity manifest")
    require_hash(named["live_report_sha256"], "R6 live identity report")

    watermark = require_exact_keys(
        evidence["watermark"],
        {
            "preflight_manifest_path",
            "preflight_manifest_sha256",
            "live_report_path",
            "live_report_sha256",
            "status_ceiling",
            "intentional_audio_watermark_proven",
            "watermark_removal_or_circumvention_attempted",
        },
        "R6 watermark evidence",
    )
    if (
        watermark["status_ceiling"] != "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK"
        or watermark["intentional_audio_watermark_proven"] is not False
        or watermark["watermark_removal_or_circumvention_attempted"] is not False
    ):
        raise R6GuardError("R6 watermark evidence overstates or circumvents")
    require_hash(watermark["preflight_manifest_sha256"], "R6 watermark preflight")
    require_hash(watermark["live_report_sha256"], "R6 watermark live report")
    for key in (
        "predecessor_audio_acceptance_sha256",
        "predecessor_evaluator_import_bindings_sha256",
        "predecessor_r2_manifest_sha256",
    ):
        require_hash(evidence[key], f"R6 evaluator {key}")
    return evidence


def validate_worker_resource_evidence(
    evidence: dict[str, Any], *, semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    validate_semantic_binding(semantic_binding)
    require_exact_keys(
        evidence, WORKER_RESOURCE_EVIDENCE_KEYS, "R6 worker resource evidence"
    )
    if (
        evidence["schema"] != "qwen3_tts_voice_forge_worker_resource_evidence_v6"
        or evidence["status"] != "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED"
        or evidence["semantic_binding_sha256"] != evidence_subject_sha256(semantic_binding)
    ):
        raise R6GuardError("R6 worker resource evidence is not subject-bound")
    telemetry = require_exact_keys(
        evidence["worker_reported_telemetry"], WORKER_TELEMETRY_KEYS, "R6 worker telemetry"
    )
    if canonical_sha256(telemetry) != evidence["worker_reported_telemetry_sha256"]:
        raise R6GuardError("R6 worker telemetry digest mismatch")
    for key, value in telemetry.items():
        if key == "rss_sampler":
            if not isinstance(value, dict) or not value:
                raise R6GuardError("R6 RSS sampler evidence is absent")
        elif key == "os_reported_peak_process_rss_is_high_water_mark":
            if value is not True:
                raise R6GuardError("R6 OS peak RSS is not a high-water mark")
        elif key == "point_samples_labeled_as_peaks":
            if value is not False:
                raise R6GuardError("R6 point samples were mislabeled as peaks")
        elif not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise R6GuardError(f"R6 telemetry {key} is not a nonnegative integer")
    timings = require_exact_keys(
        evidence["worker_reported_timings_seconds"], TIMING_KEYS, "R6 worker timings"
    )
    if canonical_sha256(timings) != evidence["worker_reported_timings_sha256"]:
        raise R6GuardError("R6 worker timings digest mismatch")
    for key, value in timings.items():
        _finite_number(value, f"R6 timing {key}", minimum=0)
    events = evidence["worker_reported_events"]
    if (
        not isinstance(events, list)
        or not all(isinstance(item, str) and item for item in events)
        or canonical_sha256(events) != evidence["worker_reported_events_sha256"]
    ):
        raise R6GuardError("R6 worker event evidence is not exact")
    return evidence


def validate_resource_evidence(
    evidence: dict[str, Any], *, worker_evidence: dict[str, Any], semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    validate_worker_resource_evidence(worker_evidence, semantic_binding=semantic_binding)
    require_exact_keys(evidence, RESOURCE_EVIDENCE_KEYS, "R6 resource evidence")
    if (
        evidence["schema"] != "qwen3_tts_voice_forge_resource_reconciliation_v6"
        or evidence["status"] != "PARENT_RECONCILED_AFTER_PROCESS_TREE_QUIESCENCE"
        or evidence["semantic_binding_sha256"] != evidence_subject_sha256(semantic_binding)
        or evidence["worker_resource_evidence_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or evidence["worker_only_telemetry_accepted_as_parent_truth"] is not False
        or evidence["reconciliation_passed"] is not True
    ):
        raise R6GuardError("R6 resource reconciliation status is unsafe")
    telemetry = worker_evidence["worker_reported_telemetry"]
    timings = worker_evidence["worker_reported_timings_seconds"]
    parent = require_exact_keys(
        evidence["parent_job_observation"], PARENT_OBSERVATION_KEYS, "R6 parent Job observation"
    )
    if (
        parent["schema"] != "qwen3_tts_voice_forge_parent_job_observation_v6"
        or parent["observed_by_parent_not_child"] is not True
        or parent["windows_job_assigned_before_resume"] is not True
        or parent["primary_worker_exit_code"] != 0
        or parent["job_termination_requested_after_primary_exit"] is not True
        or parent["active_processes_after_termination"] != 0
        or parent["process_tree_quiescent_before_finalization"] is not True
    ):
        raise R6GuardError("R6 parent did not prove process-tree quiescence")
    if canonical_sha256(parent) != evidence["parent_job_observation_sha256"]:
        raise R6GuardError("R6 parent Job observation digest mismatch")
    quiescent = parse_utc(parent["quiescence_observed_utc"], "R6 quiescence time")
    finalization = parse_utc(parent["finalization_started_utc"], "R6 finalization time")
    if quiescent > finalization:
        raise R6GuardError("R6 finalization began before process-tree quiescence")
    for key in PARENT_OBSERVATION_KEYS - {
        "schema",
        "observed_by_parent_not_child",
        "windows_job_assigned_before_resume",
        "primary_worker_exit_code",
        "job_termination_requested_after_primary_exit",
        "process_tree_quiescent_before_finalization",
        "quiescence_observed_utc",
        "finalization_started_utc",
        "parent_wall_seconds",
        "worker_stdout_sha256",
        "worker_stderr_sha256",
    }:
        if not isinstance(parent[key], int) or isinstance(parent[key], bool) or parent[key] < 0:
            raise R6GuardError(f"R6 parent observation {key} is not nonnegative")
    require_hash(parent["worker_stdout_sha256"], "R6 parent stdout hash")
    require_hash(parent["worker_stderr_sha256"], "R6 parent stderr hash")
    wall = _finite_number(parent["parent_wall_seconds"], "R6 parent wall", minimum=0)
    if wall < float(timings["total_worker"]):
        raise R6GuardError("R6 parent wall time is shorter than worker total")
    worker_peak = int(telemetry["os_reported_peak_process_rss_bytes"])
    if (
        int(parent["peak_process_memory_used_bytes"]) < worker_peak
        or int(parent["peak_job_memory_used_bytes"])
        < int(parent["peak_process_memory_used_bytes"])
    ):
        raise R6GuardError("R6 parent/worker peak memory reconciliation failed")
    return evidence


def verify_accepted_files(
    *, project_root: Path, rows: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise R6GuardError("R6 accepted file inventory is empty")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        require_exact_keys(row, ACCEPTED_FILE_ROW_KEYS, "R6 accepted file row")
        role = str(row["role"] or "")
        if not role or role in indexed:
            raise R6GuardError("R6 accepted file role is empty or duplicate")
        path = inside(project_root, row["path"], f"R6 accepted {role}")
        if (
            not path.is_file()
            or path.is_symlink()
            or not isinstance(row["bytes"], int)
            or row["bytes"] < 0
            or path.stat().st_size != row["bytes"]
            or sha256_file(path) != require_hash(row["sha256"], f"R6 accepted {role}")
        ):
            raise R6GuardError(f"R6 accepted file drift: {role}")
        indexed[role] = row
    return indexed


def validate_complete_reopened_acceptance(
    *,
    project_root: Path,
    acceptance: dict[str, Any],
    required_payloads: set[str],
    semantic_validator: Callable[[dict[str, dict[str, Any]], dict[str, Any]], None],
) -> dict[str, Any]:
    """Re-run the complete immutable trust boundary for any later use.

    The caller-supplied semantic validator must reopen and validate R4/R5/R6
    profiles/manifests, child output, artifact seals, evaluator evidence, and
    parent resource evidence from the exact accepted-file inventory.  This
    callback is mandatory; byte stability alone is never accepted.
    """

    require_exact_keys(acceptance, ACCEPTANCE_KEYS, "R6 parent acceptance")
    if (
        acceptance["schema"] != "qwen3_tts_original_voice_forge_parent_acceptance_v6"
        or acceptance["status"]
        != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_FRESH_EXECUTION_AUDIT_REQUIRED"
        or acceptance["payload_manifest_path"] != R6_PAYLOAD_MANIFEST_REL.as_posix()
        or acceptance["rejected_r5_audit_path"] != R5_REJECTED_AUDIT_REL.as_posix()
        or acceptance["rejected_r5_audit_sha256"] != R5_REJECTED_AUDIT_SHA256
        or acceptance["owner_hearing_acceptance"] != "PENDING"
        or acceptance["assignment_allowed"] is not False
        or acceptance["activation_allowed"] is not False
        or acceptance["publication_or_upload_allowed"] is not False
        or acceptance["complete_later_use_revalidation_required"] is not True
    ):
        raise R6GuardError("R6 later-use acceptance state is unsafe")
    semantic = validate_semantic_binding(acceptance["semantic_binding_v6"])
    if acceptance["semantic_binding_v6_sha256"] != canonical_sha256(semantic):
        raise R6GuardError("R6 later-use semantic binding digest mismatch")
    verify_payload_manifest(
        project_root=project_root,
        expected_manifest_sha256=acceptance["payload_manifest_sha256"],
        required_payloads=required_payloads,
    )
    verification_time = parse_utc(
        acceptance["authorization_verified_at_start_utc"],
        "R6 acceptance authorization verification time",
    )
    authorization, _ = verify_execution_authorization(
        project_root=project_root,
        authorization_path=inside(
            project_root, acceptance["execution_authorization_path"], "R6 later-use authorization"
        ),
        expected_authorization_sha256=acceptance["execution_authorization_sha256"],
        expected_manifest_sha256=acceptance["payload_manifest_sha256"],
        bundle_id=semantic["bundle_id"],
        run_id=semantic["run_id"],
        verified_at=verification_time,
    )
    if (
        authorization["authorization_nonce_sha256"]
        != semantic["execution_authorization_nonce_sha256"]
        or authorization["generation_seed"] != semantic["generation_seed"]
    ):
        raise R6GuardError("R6 later-use authorization semantic binding changed")
    audit_path = inside(project_root, acceptance["independent_r6_audit_path"], "R6 audit")
    if sha256_file(audit_path) != require_hash(
        acceptance["independent_r6_audit_sha256"], "R6 later-use audit"
    ):
        raise R6GuardError("R6 later-use fresh independent audit drifted")
    if sha256_file(project_root / R5_REJECTED_AUDIT_REL) != R5_REJECTED_AUDIT_SHA256:
        raise R6GuardError("R6 later-use rejected R5 audit drifted")
    rows = acceptance["accepted_files"]
    if canonical_sha256(rows) != acceptance["accepted_files_sha256"]:
        raise R6GuardError("R6 accepted file inventory digest mismatch")
    indexed = verify_accepted_files(project_root=project_root, rows=rows)
    for role, path_key, hash_key in (
        ("parent_authorization_ledger", "parent_authorization_ledger_path", "parent_authorization_ledger_sha256"),
        ("worker_launch_claim", "worker_launch_claim_path", "worker_launch_claim_sha256"),
    ):
        row = indexed.get(role)
        if (
            row is None
            or row["path"] != acceptance[path_key]
            or row["sha256"] != acceptance[hash_key]
        ):
            raise R6GuardError(f"R6 later-use {role} is not in the held inventory")
    semantic_validator(indexed, semantic)
    return acceptance


def reopen_acceptance_for_later_use(
    *,
    project_root: Path,
    acceptance_path: Path,
    expected_acceptance_sha256: str,
    required_payloads: set[str],
    semantic_validator: Callable[[dict[str, dict[str, Any]], dict[str, Any]], None],
) -> dict[str, Any]:
    acceptance = strict_read_json(
        acceptance_path,
        expected_sha256=expected_acceptance_sha256,
        label="R6 later-use parent acceptance",
    )
    return validate_complete_reopened_acceptance(
        project_root=project_root,
        acceptance=acceptance,
        required_payloads=required_payloads,
        semantic_validator=semantic_validator,
    )
