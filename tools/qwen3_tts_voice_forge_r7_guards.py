"""Static-only R7 trust guards for the TemporaryAI Qwen3-TTS voice forge.

R7 is an append-only successor to the independently rejected R6 package.  It
imports only Python's standard library and the exact sealed R6 guard source.
The shipped R7 payload and binding remain disabled.  Nothing in this module
loads a model, creates or plays audio, uses a GPU, or launches a worker.
"""

from __future__ import annotations

import contextlib
import copy
import ctypes
import hashlib
import json
import math
import os
import re
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator


HASH = re.compile(r"[0-9a-f]{64}")
HEX128 = re.compile(r"[0-9a-f]{32}")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
ZERO_HASH = "0" * 64

R7_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json"
)
R6_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json"
)
R6_PAYLOAD_MANIFEST_SHA256 = (
    "e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e"
)
R6_REJECTED_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_20260810.md"
)
R6_REJECTED_AUDIT_SHA256 = (
    "9094838509d115091da568dab55db8d6ab0a73c2642063f59f173da80cb56d10"
)
R7_AUTHORIZATION_ROOT_REL = Path(
    "Data/voice/authorizations/qwen3_tts_voice_forge_v7"
)
R7_PARENT_LEDGER_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v7"
)
R7_PARENT_RESERVATION_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v7"
)
R7_WORKER_CLAIM_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_worker_launch_claims_v7"
)
R2_CONTRACT_REL = Path(
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json"
)
R2_CONTRACT_SHA256 = (
    "8ae41050fcb5cef73d6dfc65a60a97302b0e8d7278f1dd40cc1cc9908233bab1"
)

R6_GUARD_REL = Path("tools/qwen3_tts_voice_forge_r6_guards.py")
R6_GUARD_SHA256 = (
    "8bf13ed57c3c19e729d586ed0196e8530de9c5d419b2b6c394a557fa6a05262a"
)

EXPECTED_THRESHOLDS = {
    "maximum_word_error_rate": 0.05,
    "minimum_speech_probability": 0.9,
    "maximum_pure_tone_probability": 0.1,
    "minimum_reference_to_clone_similarity": 0.8,
    "maximum_similarity_to_resident_or_generic_voice": 0.72,
}
CUDA_RETURN_SLACK_BYTES = 268435456
MAX_WORKER_SECONDS = 1800.0
EXPECTED_PREDECESSOR_EVENTS = (
    "LIVE_HASH_BOUND_WATERMARK_DOCUMENTATION_SCAN_PASSED_INITIAL_STATUS_ONLY",
    "LIVE_IDENTITY_ANALYZER_CLEARED_BEFORE_MODEL_LOAD",
    "VOICE_DESIGN_UNLOADED_BEFORE_BASE",
    "BASE_UNLOADED",
)
EXPECTED_RUNTIME_PHASE_EVENTS = (
    "VOICE_DESIGN_LOAD_COMPLETED",
    "VOICE_DESIGN_GENERATION_COMPLETED",
    "VOICE_DESIGN_UNLOAD_COMPLETED",
    "BASE_LOAD_COMPLETED",
    "CLONE_PROMPT_COMPLETED",
    "CLONE_GENERATION_COMPLETED",
    "BASE_UNLOAD_COMPLETED",
)


class R7GuardError(RuntimeError):
    """An R7 static trust, evidence, or durability boundary failed closed."""


class R7CollisionError(R7GuardError):
    """An append-only R7 authority, claim, acceptance, or token collided."""


def _load_exact_r6() -> Any:
    path = Path(__file__).resolve().parents[1] / R6_GUARD_REL
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != R6_GUARD_SHA256:
        raise R7GuardError("sealed R6 guard dependency drifted")
    module = types.ModuleType("qwen3_tts_voice_forge_r6_for_r7")
    module.__file__ = str(path)
    module.__package__ = ""
    exec(compile(payload, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
    if hashlib.sha256(path.read_bytes()).hexdigest() != R6_GUARD_SHA256:
        raise R7GuardError("sealed R6 guard changed during exact import")
    return module


_SEALED_R6: Any | None = None


def sealed_r6() -> Any:
    """Load the sealed R6 guard only after an R7 worker has made its claim."""

    global _SEALED_R6
    if _SEALED_R6 is None:
        _SEALED_R6 = _load_exact_r6()
    return _SEALED_R6


def _call_sealed_r6(method: str, *args: Any, **kwargs: Any) -> Any:
    """Fail closed behind the R7 exception boundary on predecessor rejection."""

    try:
        return getattr(sealed_r6(), method)(*args, **kwargs)
    except R7GuardError:
        raise
    except Exception as exc:
        raise R7GuardError(f"sealed R6 {method} rejected the R7 projection") from exc


CORE_BINDING_KEYS = {
    "bundle_id", "candidate_id", "ai_type", "opaque_voice_id", "job_sha256",
    "owner_authorization_sha256", "queue_binding_sha256", "canonical_profile_sha256",
    "canonical_creation_request_sha256",
}
FINAL_DISABLED_PERMISSIONS = {
    "assignment_allowed": False,
    "activation_allowed": False,
    "publication_or_upload_allowed": False,
    "owner_hearing_acceptance": "PENDING",
}
ELIGIBLE_AI_TYPES = {"expert_temp_ai", "generated_original_temp_ai"}
R6_SEMANTIC_BINDING_KEYS = CORE_BINDING_KEYS | {
    "run_id", "attempt", "payload_manifest_sha256",
    "execution_authorization_sha256", "execution_authorization_nonce_sha256",
    "parent_reservation_sha256", "parent_authorization_ledger_sha256",
    "worker_launch_claim_sha256", "r4_worker_manifest_sha256", "r4_profile_sha256",
    "r5_worker_manifest_sha256", "r5_profile_sha256", "reference_wav_sha256",
    "clone_test_wav_sha256", "runtime_clone_prompt_sha256",
    "reference_transcript_sha256", "clone_transcript_sha256", "reference_text_sha256",
    "test_text_sha256", "original_trait_prompt_sha256", "generation_seed",
    "voice_design_model_revision", "voice_design_model_manifest_sha256",
    "base_model_revision", "base_model_manifest_sha256", "artifact_seals_sha256",
    "evaluator_evidence_sha256", "resource_evidence_sha256",
}
R7_SEMANTIC_ADDITIONS = {
    "worker_instance_nonce_sha256",
    "execution_authorization_path",
    "independent_audit_decision_path",
    "independent_audit_decision_sha256",
    "independent_audit_subject_sha256",
    "independent_auditor_identity_sha256",
    "independent_audit_report_path",
    "independent_audit_report_sha256",
    "evaluation_corpus_sha256",
    "entry_worker_path",
    "entry_worker_sha256",
    "worker_command_sha256",
}
SEMANTIC_BINDING_KEYS = R6_SEMANTIC_BINDING_KEYS | R7_SEMANTIC_ADDITIONS

AUDIT_DECISION_KEYS = {
    "schema",
    "status",
    "authoritative_decision",
    "static_only",
    "runtime_execution_performed",
    "audit_authorizes_execution",
    "unresolved_blockers",
    "payload_manifest_path",
    "payload_manifest_sha256",
    "payload_file_inventory_sha256",
    "rejected_r6_audit_path",
    "rejected_r6_audit_sha256",
    "audit_report_path",
    "audit_report_sha256",
    "subject_sha256",
    "auditor_identity_sha256",
    "auditor_separation",
    "completed_utc",
}
AUDITOR_SEPARATION_KEYS = {
    "fresh_independent_process",
    "subject_sources_authored_by_auditor",
}

AUTHORIZATION_KEYS = {
    "schema",
    "status",
    "execution_allowed",
    "one_use",
    "payload_manifest_path",
    "payload_manifest_sha256",
    "independent_audit_decision_path",
    "independent_audit_decision_sha256",
    "independent_audit_subject_sha256",
    "independent_auditor_identity_sha256",
    "independent_audit_path",
    "independent_audit_sha256",
    "rejected_r6_audit_path",
    "rejected_r6_audit_sha256",
    "bundle_id",
    "run_id",
    "authorization_nonce_sha256",
    "worker_instance_nonce_sha256",
    "generation_seed",
    "issued_utc",
    "expires_utc",
}

COLLISION_RESULT_KEYS = {"voice_id", "kind", "similarity"}
R7_COLLISION_KEYS = {
    "clone_test_wav_sha256",
    "corpus_manifest_sha256",
    "corpus_snapshot_sha256",
    "all_embeddings_recomputed_from_exact_wavs",
    "collision_results",
    "collision_results_sha256",
    "maximum_observed_similarity",
    "maximum_allowed_similarity",
    "no_resident_or_generic_collision",
}
R6_EVALUATOR_EVIDENCE_KEYS = {
    "schema", "status", "semantic_binding_sha256", "reference_wav_sha256",
    "clone_test_wav_sha256", "runtime_clone_prompt_sha256",
    "reference_transcript_sha256", "clone_transcript_sha256", "asr_and_speech",
    "pure_tone", "speaker_identity", "collision_corpus", "named_person_clearance",
    "watermark", "predecessor_audio_acceptance_sha256",
    "predecessor_evaluator_import_bindings_sha256", "predecessor_r2_manifest_sha256",
}
EVALUATOR_EVIDENCE_KEYS = R6_EVALUATOR_EVIDENCE_KEYS | {
    "threshold_contract_path",
    "threshold_contract_sha256",
}

RSS_SAMPLER_KEYS = {
    "maximum_observed_process_rss_bytes",
    "sample_count",
    "sampling_interval_seconds",
    "started_utc",
    "ended_utc",
    "elapsed_seconds",
    "generation_and_evaluation_phases_included",
    "is_os_high_water_mark",
}
WORKER_TELEMETRY_KEYS = {
    "rss_sampler", "os_reported_peak_process_rss_bytes",
    "os_reported_peak_process_rss_is_high_water_mark", "baseline_process_rss_bytes",
    "baseline_cuda_allocated_bytes", "baseline_cuda_reserved_bytes",
    "torch_peak_cuda_allocated_bytes", "torch_peak_cuda_reserved_bytes",
    "after_design_load_observed_cuda_allocated_bytes",
    "after_design_load_observed_cuda_reserved_bytes",
    "after_base_load_observed_cuda_allocated_bytes",
    "after_base_load_observed_cuda_reserved_bytes", "after_design_unload_cuda_allocated_bytes",
    "final_cuda_allocated_bytes", "final_cuda_reserved_bytes",
    "design_generation_observed_cuda_allocated_bytes",
    "clone_generation_observed_cuda_allocated_bytes", "point_samples_labeled_as_peaks",
}
TIMING_KEYS = {
    "voice_design_load", "voice_design_generation", "base_load", "clone_prompt",
    "clone_generation", "total_worker",
}
WORKER_RESOURCE_EVIDENCE_KEYS = {
    "schema",
    "status",
    "semantic_binding_sha256",
    "worker_reported_telemetry",
    "worker_reported_telemetry_sha256",
    "worker_reported_timings_seconds",
    "worker_reported_timings_sha256",
    "predecessor_events",
    "predecessor_events_sha256",
    "runtime_phase_events",
    "runtime_phase_events_sha256",
}
PARENT_OBSERVATION_ADDITIONS = {
    "primary_worker_pid",
    "parent_pid",
    "worker_path",
    "worker_sha256",
    "worker_command_sha256",
    "authorization_sha256",
    "worker_instance_nonce_sha256",
    "job_kill_on_close_limit_active",
    "job_accounting_query_succeeded",
    "job_extended_limits_query_succeeded",
    "total_processes",
    "total_terminated_processes",
}
R6_PARENT_OBSERVATION_KEYS = {
    "schema", "observed_by_parent_not_child", "windows_job_assigned_before_resume",
    "primary_worker_exit_code", "job_termination_requested_after_primary_exit",
    "active_processes_after_termination", "process_tree_quiescent_before_finalization",
    "quiescence_observed_utc", "finalization_started_utc", "parent_wall_seconds",
    "peak_process_memory_used_bytes", "peak_job_memory_used_bytes",
    "io_read_operation_count", "io_write_operation_count", "io_read_bytes",
    "io_write_bytes", "worker_stdout_bytes", "worker_stdout_sha256",
    "worker_stderr_bytes", "worker_stderr_sha256",
}
PARENT_OBSERVATION_KEYS = R6_PARENT_OBSERVATION_KEYS | PARENT_OBSERVATION_ADDITIONS
RESOURCE_EVIDENCE_KEYS = {
    "schema", "status", "semantic_binding_sha256", "worker_resource_evidence_sha256",
    "parent_job_observation", "parent_job_observation_sha256",
    "worker_only_telemetry_accepted_as_parent_truth", "reconciliation_passed",
}

WINDOWS_FILE_IDENTITY_KEYS = {
    "volume_serial_hex",
    "file_id_hex",
    "normalized_final_path_sha256",
}
ACCEPTED_FILE_ROW_KEYS = {
    "role",
    "path",
    "bytes",
    "sha256",
    "windows_file_identity",
}
ACCEPTANCE_KEYS = {
    "schema",
    "status",
    "accepted_utc",
    "authorization_verified_at_start_utc",
    "semantic_binding_v7",
    "semantic_binding_v7_sha256",
    "payload_manifest_path",
    "payload_manifest_sha256",
    "execution_authorization_path",
    "execution_authorization_sha256",
    "independent_audit_decision_path",
    "independent_audit_decision_sha256",
    "independent_audit_subject_sha256",
    "independent_auditor_identity_sha256",
    "independent_r7_audit_path",
    "independent_r7_audit_sha256",
    "rejected_r6_audit_path",
    "rejected_r6_audit_sha256",
    "parent_authorization_ledger_path",
    "parent_authorization_ledger_sha256",
    "worker_launch_claim_path",
    "worker_launch_claim_sha256",
    "accepted_files",
    "accepted_files_sha256",
    "held_file_identities_sha256",
    "windows_identity_commit_required",
    "owner_hearing_acceptance",
    "assignment_allowed",
    "activation_allowed",
    "publication_or_upload_allowed",
    "complete_later_use_revalidation_required",
}

R7_PROFILE_ADDITIONS = {
    "r7_status",
    "predecessor_r6_profile_sha256",
    "semantic_binding_v7",
    "semantic_binding_v7_sha256",
    "evaluator_evidence_v7_path",
    "evaluator_evidence_v7_sha256",
    "worker_resource_evidence_v7_path",
    "worker_resource_evidence_v7_sha256",
    "worker_launch_claim_v7_path",
    "worker_launch_claim_v7_sha256",
    "parent_authorization_ledger_v7_path",
    "parent_authorization_ledger_v7_sha256",
    "complete_later_use_revalidation_v7_required",
}
R7_MANIFEST_KEYS = {
    "schema", "status", "semantic_binding_v7", "semantic_binding_v7_sha256",
    "profile_sha256", "predecessor_worker_manifest_sha256",
    "predecessor_profile_sha256", "worker_launch_claim_path",
    "worker_launch_claim_sha256", "parent_authorization_ledger_path",
    "parent_authorization_ledger_sha256", "evaluator_evidence_path",
    "evaluator_evidence_sha256", "resource_evidence_path", "resource_evidence_sha256",
    "process_tree_quiescence_required_before_parent_finalization",
    "parent_evaluator_and_resource_reconciliation_required", "owner_hearing_acceptance",
    "assignment_allowed", "activation_allowed", "publication_or_upload_allowed",
}
R7_CHILD_KEYS = {
    "schema", "status", "semantic_binding_v7_sha256", "manifest_path",
    "manifest_sha256", "profile_path", "profile_sha256", "evaluator_evidence_path",
    "evaluator_evidence_sha256", "worker_resource_evidence_path",
    "worker_resource_evidence_sha256", "worker_launch_claim_path",
    "worker_launch_claim_sha256",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise R7GuardError("R7 value is not finite canonical JSON") from exc


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R7GuardError(f"duplicate R7 JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise R7GuardError(f"non-finite R7 JSON constant rejected: {value}")


def strict_json_bytes(payload: bytes, label: str) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except R7GuardError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R7GuardError(f"{label} is not strict finite UTF-8 JSON") from exc


def strict_read_json(
    path: Path, *, expected_sha256: str | None = None, label: str = "R7 JSON"
) -> Any:
    if not path.is_file() or path.is_symlink():
        raise R7GuardError(f"{label} is missing or unsafe")
    payload = path.read_bytes()
    if expected_sha256 is not None and sha256_bytes(payload) != require_hash(
        expected_sha256, f"{label} hash"
    ):
        raise R7GuardError(f"{label} differs from its exact hash")
    return strict_json_bytes(payload, label)


def require_exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = set(value) if isinstance(value, dict) else set()
        raise R7GuardError(
            f"{label} fields are not exact; missing={sorted(keys-actual)}, extra={sorted(actual-keys)}"
        )
    return value


def require_hash(value: Any, label: str, *, nonzero: bool = True) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text) or (nonzero and text == ZERO_HASH):
        raise R7GuardError(f"{label} is not an exact nonzero SHA-256")
    return text


def require_id(value: Any, label: str) -> str:
    text = str(value or "")
    if not SAFE_ID.fullmatch(text):
        raise R7GuardError(f"{label} is not one safe opaque ID")
    return text


def finite_number(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R7GuardError(f"{label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise R7GuardError(f"{label} is not finite")
    if minimum is not None and number < minimum:
        raise R7GuardError(f"{label} is below its closed lower bound")
    if maximum is not None and number > maximum:
        raise R7GuardError(f"{label} is above its closed upper bound")
    return number


def parse_utc(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise R7GuardError(f"{label} is not an exact timestamp") from exc
    if parsed.tzinfo is None:
        raise R7GuardError(f"{label} lacks a timezone")
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(str(value))
    result = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R7GuardError(f"{label} escaped its exact root") from exc
    return result


def project_relative(project_root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise R7GuardError(f"{label} escaped the project") from exc


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise R7CollisionError(f"append-only R7 path already exists: {path}") from exc


def write_new_json(path: Path, value: Any) -> None:
    payload = json.dumps(
        value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"
    write_new(path, payload)


def payload_inventory_sha256(manifest: dict[str, Any]) -> str:
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R7GuardError("R7 payload inventory is not a list")
    return canonical_sha256(rows)


def verify_payload_manifest(
    *, project_root: Path, expected_manifest_sha256: str, required_payloads: set[str]
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    project_root = project_root.resolve()
    manifest_path = project_root / R7_PAYLOAD_MANIFEST_REL
    manifest = strict_read_json(
        manifest_path,
        expected_sha256=require_hash(expected_manifest_sha256, "R7 payload hash"),
        label="R7 immutable payload manifest",
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
            "rejected_r6_audit_path",
            "rejected_r6_audit_sha256",
            "files",
        },
        "R7 payload manifest",
    )
    if (
        manifest["schema"] != "qwen3_tts_voice_forge_payload_manifest_v7"
        or manifest["status"]
        != "IMMUTABLE_STATIC_PAYLOAD_REQUIRES_FRESH_INDEPENDENT_AUDIT_AND_EXTERNAL_AUTHORIZATION"
        or manifest["execution_allowed"] is not False
        or manifest["self_authorization_allowed"] is not False
        or manifest["predecessor_payload_manifest_path"]
        != R6_PAYLOAD_MANIFEST_REL.as_posix()
        or manifest["predecessor_payload_manifest_sha256"]
        != R6_PAYLOAD_MANIFEST_SHA256
        or manifest["rejected_r6_audit_path"] != R6_REJECTED_AUDIT_REL.as_posix()
        or manifest["rejected_r6_audit_sha256"] != R6_REJECTED_AUDIT_SHA256
    ):
        raise R7GuardError("R7 payload is self-authorizing or lost its rejected predecessor")
    if sha256_file(project_root / R6_PAYLOAD_MANIFEST_REL) != R6_PAYLOAD_MANIFEST_SHA256:
        raise R7GuardError("sealed R6 payload manifest drifted")
    if sha256_file(project_root / R6_REJECTED_AUDIT_REL) != R6_REJECTED_AUDIT_SHA256:
        raise R7GuardError("sealed rejected R6 audit drifted")
    rows = manifest["files"]
    if not isinstance(rows, list):
        raise R7GuardError("R7 payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        require_exact_keys(row, {"path", "bytes", "sha256"}, "R7 payload row")
        rel = str(row["path"] or "")
        if not rel or rel in indexed or rel == R7_PAYLOAD_MANIFEST_REL.as_posix():
            raise R7GuardError("R7 payload row is empty, duplicate, or self-referential")
        target = inside(project_root, rel, "R7 payload file")
        if (
            not target.is_file()
            or target.is_symlink()
            or not isinstance(row["bytes"], int)
            or isinstance(row["bytes"], bool)
            or row["bytes"] < 0
            or target.stat().st_size != row["bytes"]
            or sha256_file(target) != require_hash(row["sha256"], f"R7 payload {rel}")
        ):
            raise R7GuardError(f"R7 immutable payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != set(required_payloads):
        raise R7GuardError("R7 immutable payload inventory is not exact")
    return manifest, indexed


def audit_subject(
    *, manifest_path: str, manifest_sha256: str, inventory_sha256: str
) -> dict[str, Any]:
    return {
        "payload_manifest_path": manifest_path,
        "payload_manifest_sha256": manifest_sha256,
        "payload_file_inventory_sha256": inventory_sha256,
        "rejected_r6_audit_path": R6_REJECTED_AUDIT_REL.as_posix(),
        "rejected_r6_audit_sha256": R6_REJECTED_AUDIT_SHA256,
    }


def validate_independent_audit_v7(
    *,
    project_root: Path,
    audit_decision_path: Path,
    expected_audit_decision_sha256: str,
    expected_manifest_sha256: str,
    expected_inventory_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    rel = project_relative(project_root, audit_decision_path, "R7 audit decision")
    if not rel.startswith("RecoverySprint/"):
        raise R7GuardError("R7 audit decision is outside append-only audit evidence")
    decision_hash = require_hash(expected_audit_decision_sha256, "R7 audit decision hash")
    payload = audit_decision_path.read_bytes()
    if sha256_bytes(payload) != decision_hash or payload != canonical_bytes(
        strict_json_bytes(payload, "R7 independent audit decision")
    ) + b"\n":
        raise R7GuardError("R7 audit decision is not exact canonical JSON plus LF")
    audit = strict_json_bytes(payload, "R7 independent audit decision")
    require_exact_keys(audit, AUDIT_DECISION_KEYS, "R7 independent audit decision")
    separation = require_exact_keys(
        audit["auditor_separation"], AUDITOR_SEPARATION_KEYS, "R7 auditor separation"
    )
    expected_subject = audit_subject(
        manifest_path=R7_PAYLOAD_MANIFEST_REL.as_posix(),
        manifest_sha256=require_hash(expected_manifest_sha256, "R7 audited payload hash"),
        inventory_sha256=require_hash(expected_inventory_sha256, "R7 audited inventory hash"),
    )
    if (
        audit["schema"] != "qwen3_tts_voice_forge_independent_static_audit_v7"
        or audit["status"] != "FINAL"
        or audit["authoritative_decision"] != "ACCEPT_STATIC_ONLY"
        or audit["static_only"] is not True
        or audit["runtime_execution_performed"] is not False
        or audit["audit_authorizes_execution"] is not False
        or audit["unresolved_blockers"] != []
        or any(audit[key] != value for key, value in expected_subject.items())
        or audit["subject_sha256"] != canonical_sha256(expected_subject)
        or separation["fresh_independent_process"] is not True
        or separation["subject_sources_authored_by_auditor"] is not False
    ):
        raise R7GuardError("R7 independent audit decision is not a closed static acceptance")
    require_hash(audit["auditor_identity_sha256"], "R7 independent auditor identity")
    completed = parse_utc(audit["completed_utc"], "R7 audit completed_utc")
    report_rel = str(audit["audit_report_path"] or "")
    report_path = inside(project_root, report_rel, "R7 audit report")
    if (
        not report_rel.startswith("System/Docs/")
        or not report_path.is_file()
        or report_path.is_symlink()
        or sha256_file(report_path)
        != require_hash(audit["audit_report_sha256"], "R7 audit report hash")
    ):
        raise R7GuardError("R7 independent audit report binding mismatch")
    return audit, {
        "decision_path": rel,
        "decision_sha256": decision_hash,
        "subject_sha256": audit["subject_sha256"],
        "auditor_identity_sha256": audit["auditor_identity_sha256"],
        "report_path": report_rel,
        "report_sha256": audit["audit_report_sha256"],
        "completed_utc": completed,
    }


def verify_execution_authorization(
    *,
    project_root: Path,
    authorization_path: Path,
    expected_authorization_sha256: str,
    expected_manifest_sha256: str,
    expected_inventory_sha256: str,
    bundle_id: str,
    run_id: str,
    verified_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    authorization_path = authorization_path.resolve()
    rel = project_relative(project_root, authorization_path, "R7 authorization")
    if not rel.startswith(R7_AUTHORIZATION_ROOT_REL.as_posix() + "/"):
        raise R7GuardError("R7 authorization is outside its append-only authority root")
    auth_hash = require_hash(expected_authorization_sha256, "R7 authorization hash")
    authorization = strict_read_json(
        authorization_path,
        expected_sha256=auth_hash,
        label="R7 execution authorization",
    )
    require_exact_keys(authorization, AUTHORIZATION_KEYS, "R7 execution authorization")
    if (
        authorization["schema"] != "qwen3_tts_voice_forge_execution_authorization_v7"
        or authorization["status"] != "FRESH_R7_STATIC_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization["execution_allowed"] is not True
        or authorization["one_use"] is not True
        or authorization["payload_manifest_path"] != R7_PAYLOAD_MANIFEST_REL.as_posix()
        or authorization["payload_manifest_sha256"] != expected_manifest_sha256
        or authorization["rejected_r6_audit_path"] != R6_REJECTED_AUDIT_REL.as_posix()
        or authorization["rejected_r6_audit_sha256"] != R6_REJECTED_AUDIT_SHA256
        or authorization["bundle_id"] != require_id(bundle_id, "R7 bundle ID")
        or authorization["run_id"] != require_id(run_id, "R7 run ID")
    ):
        raise R7GuardError("R7 authorization scope or rejected-predecessor binding mismatch")
    require_hash(authorization["authorization_nonce_sha256"], "R7 authorization nonce")
    require_hash(authorization["worker_instance_nonce_sha256"], "R7 worker nonce")
    if (
        not isinstance(authorization["generation_seed"], int)
        or isinstance(authorization["generation_seed"], bool)
        or not 0 <= authorization["generation_seed"] < 2**63
    ):
        raise R7GuardError("R7 generation seed is not one bounded integer")
    decision_path = inside(
        project_root,
        authorization["independent_audit_decision_path"],
        "R7 authorized audit decision",
    )
    audit, audit_evidence = validate_independent_audit_v7(
        project_root=project_root,
        audit_decision_path=decision_path,
        expected_audit_decision_sha256=authorization["independent_audit_decision_sha256"],
        expected_manifest_sha256=expected_manifest_sha256,
        expected_inventory_sha256=expected_inventory_sha256,
    )
    if (
        authorization["independent_audit_subject_sha256"]
        != audit_evidence["subject_sha256"]
        or authorization["independent_auditor_identity_sha256"]
        != audit_evidence["auditor_identity_sha256"]
        or authorization["independent_audit_path"] != audit_evidence["report_path"]
        or authorization["independent_audit_sha256"] != audit_evidence["report_sha256"]
    ):
        raise R7GuardError("R7 authorization changed the accepted audit identity")
    issued = parse_utc(authorization["issued_utc"], "R7 issued_utc")
    expires = parse_utc(authorization["expires_utc"], "R7 expires_utc")
    observed = (verified_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if audit_evidence["completed_utc"] > issued or issued > observed or observed > expires:
        raise R7GuardError("R7 audit/authorization time ordering is invalid")
    return authorization, {
        "path": rel,
        "bytes": authorization_path.stat().st_size,
        "sha256": auth_hash,
        "payload_manifest_sha256": expected_manifest_sha256,
        **audit_evidence,
    }


def validate_semantic_binding(value: dict[str, Any]) -> dict[str, Any]:
    require_exact_keys(value, SEMANTIC_BINDING_KEYS, "R7 semantic binding")
    _call_sealed_r6(
        "validate_semantic_binding",
        {key: value[key] for key in R6_SEMANTIC_BINDING_KEYS}
    )
    for key in (
        "worker_instance_nonce_sha256",
        "independent_audit_decision_sha256",
        "independent_audit_subject_sha256",
        "independent_auditor_identity_sha256",
        "independent_audit_report_sha256",
        "evaluation_corpus_sha256",
        "entry_worker_sha256",
        "worker_command_sha256",
    ):
        require_hash(value[key], f"R7 semantic {key}")
    for key in (
        "execution_authorization_path",
        "independent_audit_decision_path",
        "independent_audit_report_path",
        "entry_worker_path",
    ):
        if not isinstance(value[key], str) or not value[key].strip():
            raise R7GuardError(f"R7 semantic {key} is empty")
    return value


def r6_semantic_projection(value: dict[str, Any]) -> dict[str, Any]:
    validate_semantic_binding(value)
    return {key: value[key] for key in R6_SEMANTIC_BINDING_KEYS}


def evidence_subject_sha256(value: dict[str, Any]) -> str:
    validate_semantic_binding(value)
    return canonical_sha256(
        {
            key: item
            for key, item in value.items()
            if key not in {"evaluator_evidence_sha256", "resource_evidence_sha256"}
        }
    )


def load_sealed_thresholds(project_root: Path) -> dict[str, float]:
    contract = strict_read_json(
        project_root.resolve() / R2_CONTRACT_REL,
        expected_sha256=R2_CONTRACT_SHA256,
        label="R7 sealed evaluator threshold contract",
    )
    audio = contract.get("audio_acceptance")
    if not isinstance(audio, dict):
        raise R7GuardError("R7 sealed audio threshold section is absent")
    observed = {key: audio.get(key) for key in EXPECTED_THRESHOLDS}
    if observed != EXPECTED_THRESHOLDS:
        raise R7GuardError("R7 evaluator thresholds drifted from the sealed contract")
    for key, value in observed.items():
        finite_number(value, f"R7 sealed threshold {key}", minimum=0, maximum=1)
    return {key: float(value) for key, value in observed.items()}


def _adapt_r7_evaluator_to_r6(
    evidence: dict[str, Any], semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    adapted = copy.deepcopy(evidence)
    adapted.pop("threshold_contract_path", None)
    adapted.pop("threshold_contract_sha256", None)
    collision = adapted["collision_corpus"]
    collision.pop("collision_results", None)
    collision.pop("maximum_observed_similarity", None)
    adapted["schema"] = "qwen3_tts_voice_forge_evaluator_evidence_v6"
    adapted["status"] = "WORKER_EVIDENCE_PARENT_REVALIDATION_REQUIRED"
    projection = r6_semantic_projection(semantic_binding)
    adapted["semantic_binding_sha256"] = sealed_r6().evidence_subject_sha256(projection)
    return adapted


def validate_evaluator_evidence(
    evidence: dict[str, Any],
    *,
    semantic_binding: dict[str, Any],
    project_root: Path,
    expected_collision_subjects: set[tuple[str, str]],
) -> dict[str, Any]:
    validate_semantic_binding(semantic_binding)
    require_exact_keys(evidence, EVALUATOR_EVIDENCE_KEYS, "R7 evaluator evidence")
    if (
        evidence["schema"] != "qwen3_tts_voice_forge_evaluator_evidence_v7"
        or evidence["status"] != "WORKER_EVIDENCE_PARENT_REVALIDATION_REQUIRED"
        or evidence["semantic_binding_sha256"] != evidence_subject_sha256(semantic_binding)
        or evidence["threshold_contract_path"] != R2_CONTRACT_REL.as_posix()
        or evidence["threshold_contract_sha256"] != R2_CONTRACT_SHA256
    ):
        raise R7GuardError("R7 evaluator evidence is not subject/contract bound")
    limits = load_sealed_thresholds(project_root)
    _call_sealed_r6(
        "validate_evaluator_evidence",
        _adapt_r7_evaluator_to_r6(evidence, semantic_binding),
        semantic_binding=r6_semantic_projection(semantic_binding),
    )
    for role in ("reference", "clone"):
        row = evidence["asr_and_speech"][role]
        wer = finite_number(row["word_error_rate"], f"R7 {role} WER", minimum=0, maximum=1)
        speech = finite_number(
            row["speech_probability"], f"R7 {role} speech probability", minimum=0, maximum=1
        )
        if (
            finite_number(row["maximum_word_error_rate"], f"R7 {role} max WER", minimum=0, maximum=1)
            != limits["maximum_word_error_rate"]
            or finite_number(row["minimum_speech_probability"], f"R7 {role} min speech", minimum=0, maximum=1)
            != limits["minimum_speech_probability"]
            or wer > limits["maximum_word_error_rate"]
            or speech < limits["minimum_speech_probability"]
            or row["accepted"] is not True
        ):
            raise R7GuardError(f"R7 {role} ASR/speech evidence violates sealed limits")
        tone = evidence["pure_tone"][role]
        probability = finite_number(
            tone["pure_tone_probability"], f"R7 {role} pure-tone probability", minimum=0, maximum=1
        )
        if (
            finite_number(
                tone["maximum_pure_tone_probability"],
                f"R7 {role} maximum pure-tone probability",
                minimum=0,
                maximum=1,
            )
            != limits["maximum_pure_tone_probability"]
            or probability > limits["maximum_pure_tone_probability"]
        ):
            raise R7GuardError(f"R7 {role} pure-tone evidence violates sealed limits")
    speaker = evidence["speaker_identity"]
    similarity = finite_number(
        speaker["reference_to_clone_similarity"], "R7 speaker similarity", minimum=-1, maximum=1
    )
    if (
        finite_number(speaker["minimum_similarity"], "R7 minimum speaker similarity", minimum=0, maximum=1)
        != limits["minimum_reference_to_clone_similarity"]
        or similarity < limits["minimum_reference_to_clone_similarity"]
    ):
        raise R7GuardError("R7 speaker identity violates the sealed limit")
    collision = require_exact_keys(
        evidence["collision_corpus"], R7_COLLISION_KEYS, "R7 collision evidence"
    )
    results = collision["collision_results"]
    if not isinstance(results, list) or not results:
        raise R7GuardError("R7 collision result set is empty")
    subjects: set[tuple[str, str]] = set()
    scores: list[float] = []
    for row in results:
        require_exact_keys(row, COLLISION_RESULT_KEYS, "R7 collision result")
        subject = (require_id(row["voice_id"], "R7 collision voice"), require_id(row["kind"], "R7 collision kind"))
        if subject in subjects:
            raise R7GuardError("R7 collision result subject is duplicated")
        subjects.add(subject)
        scores.append(
            finite_number(row["similarity"], "R7 collision similarity", minimum=-1, maximum=1)
        )
    observed_max = max(scores)
    if (
        subjects != set(expected_collision_subjects)
        or collision["collision_results_sha256"] != canonical_sha256(results)
        or finite_number(
            collision["maximum_observed_similarity"],
            "R7 observed maximum collision similarity",
            minimum=-1,
            maximum=1,
        )
        != observed_max
        or finite_number(
            collision["maximum_allowed_similarity"],
            "R7 maximum allowed collision similarity",
            minimum=0,
            maximum=1,
        )
        != limits["maximum_similarity_to_resident_or_generic_voice"]
        or observed_max > limits["maximum_similarity_to_resident_or_generic_voice"]
        or collision["no_resident_or_generic_collision"] is not True
    ):
        raise R7GuardError("R7 collision evidence is incomplete or exceeds the sealed limit")
    return evidence


def _adapt_r7_worker_resource_to_r6(
    evidence: dict[str, Any], semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "qwen3_tts_voice_forge_worker_resource_evidence_v6",
        "status": "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED",
        "semantic_binding_sha256": sealed_r6().evidence_subject_sha256(
            r6_semantic_projection(semantic_binding)
        ),
        "worker_reported_telemetry": evidence["worker_reported_telemetry"],
        "worker_reported_telemetry_sha256": evidence[
            "worker_reported_telemetry_sha256"
        ],
        "worker_reported_timings_seconds": evidence[
            "worker_reported_timings_seconds"
        ],
        "worker_reported_timings_sha256": evidence[
            "worker_reported_timings_sha256"
        ],
        "worker_reported_events": evidence["predecessor_events"],
        "worker_reported_events_sha256": evidence["predecessor_events_sha256"],
    }


def validate_worker_resource_evidence(
    evidence: dict[str, Any], *, semantic_binding: dict[str, Any]
) -> dict[str, Any]:
    validate_semantic_binding(semantic_binding)
    require_exact_keys(
        evidence, WORKER_RESOURCE_EVIDENCE_KEYS, "R7 worker resource evidence"
    )
    if (
        evidence["schema"] != "qwen3_tts_voice_forge_worker_resource_evidence_v7"
        or evidence["status"] != "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED"
        or evidence["semantic_binding_sha256"] != evidence_subject_sha256(semantic_binding)
    ):
        raise R7GuardError("R7 worker resource evidence is not subject-bound")
    _call_sealed_r6(
        "validate_worker_resource_evidence",
        _adapt_r7_worker_resource_to_r6(evidence, semantic_binding),
        semantic_binding=r6_semantic_projection(semantic_binding),
    )
    telemetry = require_exact_keys(
        evidence["worker_reported_telemetry"], WORKER_TELEMETRY_KEYS, "R7 worker telemetry"
    )
    if canonical_sha256(telemetry) != evidence["worker_reported_telemetry_sha256"]:
        raise R7GuardError("R7 worker telemetry digest mismatch")
    rss = require_exact_keys(telemetry["rss_sampler"], RSS_SAMPLER_KEYS, "R7 RSS sampler")
    rss_started = parse_utc(rss["started_utc"], "R7 RSS start")
    rss_ended = parse_utc(rss["ended_utc"], "R7 RSS end")
    sampler_peak = rss["maximum_observed_process_rss_bytes"]
    if (
        not isinstance(sampler_peak, int)
        or isinstance(sampler_peak, bool)
        or sampler_peak <= 0
        or not isinstance(rss["sample_count"], int)
        or isinstance(rss["sample_count"], bool)
        or rss["sample_count"] < 2
        or not 0.001
        <= finite_number(rss["sampling_interval_seconds"], "R7 RSS interval")
        <= 0.1
        or finite_number(rss["elapsed_seconds"], "R7 RSS elapsed") <= 0
        or rss_started > rss_ended
        or rss["generation_and_evaluation_phases_included"] is not True
        or rss["is_os_high_water_mark"] is not False
    ):
        raise R7GuardError("R7 RSS sampler is not real, complete, and ordered")
    for key in WORKER_TELEMETRY_KEYS - {
        "rss_sampler",
        "os_reported_peak_process_rss_is_high_water_mark",
        "point_samples_labeled_as_peaks",
    }:
        value = telemetry[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise R7GuardError(f"R7 telemetry {key} is not a nonnegative integer")
    if (
        telemetry["os_reported_peak_process_rss_is_high_water_mark"] is not True
        or telemetry["point_samples_labeled_as_peaks"] is not False
        or telemetry["baseline_process_rss_bytes"] <= 0
        or telemetry["os_reported_peak_process_rss_bytes"] < sampler_peak
        or sampler_peak < telemetry["baseline_process_rss_bytes"]
    ):
        raise R7GuardError("R7 RSS/OS peak relationships are not real")
    baseline = telemetry["baseline_cuda_allocated_bytes"]
    baseline_reserved = telemetry["baseline_cuda_reserved_bytes"]
    positive_allocations = (
        "after_design_load_observed_cuda_allocated_bytes",
        "after_base_load_observed_cuda_allocated_bytes",
        "design_generation_observed_cuda_allocated_bytes",
        "clone_generation_observed_cuda_allocated_bytes",
    )
    if any(telemetry[key] <= baseline for key in positive_allocations):
        raise R7GuardError("R7 required model/generation CUDA allocation is absent")
    for allocated_key, reserved_key in (
        (
            "after_design_load_observed_cuda_allocated_bytes",
            "after_design_load_observed_cuda_reserved_bytes",
        ),
        (
            "after_base_load_observed_cuda_allocated_bytes",
            "after_base_load_observed_cuda_reserved_bytes",
        ),
    ):
        if telemetry[reserved_key] < telemetry[allocated_key]:
            raise R7GuardError("R7 CUDA reserved memory is below allocated memory")
    if (
        telemetry["torch_peak_cuda_allocated_bytes"]
        < max(telemetry[key] for key in positive_allocations)
        or telemetry["torch_peak_cuda_reserved_bytes"]
        < telemetry["torch_peak_cuda_allocated_bytes"]
        or telemetry["after_design_unload_cuda_allocated_bytes"]
        > baseline + CUDA_RETURN_SLACK_BYTES
        or telemetry["final_cuda_allocated_bytes"] > baseline + CUDA_RETURN_SLACK_BYTES
        or telemetry["final_cuda_reserved_bytes"]
        > baseline_reserved + CUDA_RETURN_SLACK_BYTES
    ):
        raise R7GuardError("R7 CUDA peak/unload-return evidence is inconsistent")
    timings = require_exact_keys(
        evidence["worker_reported_timings_seconds"], TIMING_KEYS, "R7 worker timings"
    )
    if canonical_sha256(timings) != evidence["worker_reported_timings_sha256"]:
        raise R7GuardError("R7 worker timing digest mismatch")
    components = [
        finite_number(timings[key], f"R7 timing {key}", minimum=0)
        for key in TIMING_KEYS - {"total_worker"}
    ]
    total = finite_number(timings["total_worker"], "R7 total worker timing", minimum=0)
    if any(value <= 0 for value in components) or total <= 0 or total < sum(components) or total > MAX_WORKER_SECONDS:
        raise R7GuardError("R7 worker timings are zero, nonadditive, or over the bound")
    predecessor_events = evidence["predecessor_events"]
    runtime_events = evidence["runtime_phase_events"]
    if (
        predecessor_events != list(EXPECTED_PREDECESSOR_EVENTS)
        or runtime_events != list(EXPECTED_RUNTIME_PHASE_EVENTS)
        or canonical_sha256(predecessor_events) != evidence["predecessor_events_sha256"]
        or canonical_sha256(runtime_events) != evidence["runtime_phase_events_sha256"]
    ):
        raise R7GuardError("R7 worker event sequences are not exact and closed")
    return evidence


def validate_resource_evidence(
    evidence: dict[str, Any],
    *,
    worker_evidence: dict[str, Any],
    semantic_binding: dict[str, Any],
    worker_claim: dict[str, Any],
    stdout_row: dict[str, Any],
    stderr_row: dict[str, Any],
) -> dict[str, Any]:
    validate_worker_resource_evidence(worker_evidence, semantic_binding=semantic_binding)
    require_exact_keys(evidence, RESOURCE_EVIDENCE_KEYS, "R7 resource evidence")
    if (
        evidence["schema"] != "qwen3_tts_voice_forge_resource_reconciliation_v7"
        or evidence["status"] != "PARENT_RECONCILED_AFTER_PROCESS_TREE_QUIESCENCE"
        or evidence["semantic_binding_sha256"] != evidence_subject_sha256(semantic_binding)
        or evidence["worker_resource_evidence_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or evidence["worker_only_telemetry_accepted_as_parent_truth"] is not False
        or evidence["reconciliation_passed"] is not True
    ):
        raise R7GuardError("R7 resource reconciliation status is unsafe")
    parent = require_exact_keys(
        evidence["parent_job_observation"], PARENT_OBSERVATION_KEYS, "R7 parent Job observation"
    )
    adapted_parent = {
        key: value for key, value in parent.items() if key in R6_PARENT_OBSERVATION_KEYS
    }
    adapted_parent["schema"] = "qwen3_tts_voice_forge_parent_job_observation_v6"
    adapted_resource = copy.deepcopy(evidence)
    adapted_resource["schema"] = "qwen3_tts_voice_forge_resource_reconciliation_v6"
    adapted_resource["semantic_binding_sha256"] = sealed_r6().evidence_subject_sha256(
        r6_semantic_projection(semantic_binding)
    )
    adapted_resource["parent_job_observation"] = adapted_parent
    adapted_resource["parent_job_observation_sha256"] = sealed_r6().canonical_sha256(adapted_parent)
    _call_sealed_r6(
        "validate_resource_evidence",
        adapted_resource,
        worker_evidence=_adapt_r7_worker_resource_to_r6(worker_evidence, semantic_binding),
        semantic_binding=r6_semantic_projection(semantic_binding),
    )
    if canonical_sha256(parent) != evidence["parent_job_observation_sha256"]:
        raise R7GuardError("R7 parent Job observation digest mismatch")
    for row, label in ((stdout_row, "stdout"), (stderr_row, "stderr")):
        require_exact_keys(row, ACCEPTED_FILE_ROW_KEYS, f"R7 {label} row")
    if (
        parent["schema"] != "qwen3_tts_voice_forge_parent_job_observation_v7"
        or parent["primary_worker_pid"] != worker_claim.get("worker_pid")
        or parent["primary_worker_pid"] <= 0
        or parent["parent_pid"] <= 0
        or parent["worker_path"] != semantic_binding["entry_worker_path"]
        or parent["worker_sha256"] != semantic_binding["entry_worker_sha256"]
        or parent["worker_command_sha256"] != semantic_binding["worker_command_sha256"]
        or parent["authorization_sha256"]
        != semantic_binding["execution_authorization_sha256"]
        or parent["worker_instance_nonce_sha256"]
        != semantic_binding["worker_instance_nonce_sha256"]
        or parent["job_kill_on_close_limit_active"] is not True
        or parent["job_accounting_query_succeeded"] is not True
        or parent["job_extended_limits_query_succeeded"] is not True
        or parent["total_processes"] < 1
        or parent["total_terminated_processes"] > parent["total_processes"]
        or parent["parent_wall_seconds"] <= 0
        or parent["peak_process_memory_used_bytes"] <= 0
        or parent["peak_job_memory_used_bytes"] <= 0
        or parent["worker_stdout_bytes"] != stdout_row["bytes"]
        or parent["worker_stdout_sha256"] != stdout_row["sha256"]
        or parent["worker_stderr_bytes"] != stderr_row["bytes"]
        or parent["worker_stderr_sha256"] != stderr_row["sha256"]
    ):
        raise R7GuardError("R7 parent observation is not linked to the exact claim/process/logs")
    return evidence


def validate_parent_ledger(ledger: dict[str, Any], *, expected: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "schema", "status", "utc", "authorization_sha256",
        "authorization_nonce_sha256", "worker_instance_nonce_sha256",
        "independent_audit_decision_sha256", "independent_audit_subject_sha256",
        "independent_auditor_identity_sha256", "independent_audit_report_sha256",
        "payload_manifest_sha256", "bundle_id", "run_id", "attempt",
        "parent_reservation_path", "parent_reservation_sha256",
        "verified_worker_path", "verified_worker_sha256", "worker_command_sha256",
    }
    require_exact_keys(ledger, keys, "R7 parent ledger")
    if (
        ledger["schema"] != "qwen3_tts_voice_forge_authorization_ledger_v7"
        or ledger["status"] != "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT"
        or any(ledger.get(key) != expected.get(key) for key in keys - {"schema", "status", "utc"})
    ):
        raise R7GuardError("R7 parent ledger binding mismatch")
    parse_utc(ledger["utc"], "R7 parent ledger utc")
    for key in keys & {key for key in ledger if key.endswith("sha256")}:
        require_hash(ledger[key], f"R7 ledger {key}")
    return ledger


def validate_parent_reservation(
    reservation: dict[str, Any], *, expected: dict[str, Any]
) -> dict[str, Any]:
    keys = {
        "schema", "status", "bundle_id", "run_id", "attempt",
        "payload_manifest_sha256", "execution_authorization_sha256",
        "authorization_nonce_sha256", "worker_instance_nonce_sha256",
        "independent_audit_decision_sha256", "independent_audit_subject_sha256",
        "independent_auditor_identity_sha256", "independent_audit_report_sha256",
        "generation_seed", "parent_authorization_ledger_path",
        "verified_entry_worker_path", "verified_entry_worker_sha256",
        "worker_command_sha256",
        "exact_parent_preflight_provenance", "exact_parent_full_provenance",
        "exact_parent_full_provenance_sha256", "frozen_parent_reservation_sha256",
    }
    require_exact_keys(reservation, keys, "R7 parent reservation")
    if (
        reservation["schema"] != "qwen3_tts_voice_forge_parent_reservation_v7"
        or reservation["status"]
        != "EXTERNAL_AUTHORITY_PARENT_PREFLIGHT_AND_WORKER_IDENTITY_RESERVED"
        or any(reservation.get(key) != value for key, value in expected.items())
    ):
        raise R7GuardError("R7 parent reservation binding mismatch")
    for key in (
        "payload_manifest_sha256",
        "execution_authorization_sha256",
        "authorization_nonce_sha256",
        "worker_instance_nonce_sha256",
        "independent_audit_decision_sha256",
        "independent_audit_subject_sha256",
        "independent_auditor_identity_sha256",
        "independent_audit_report_sha256",
        "verified_entry_worker_sha256",
        "worker_command_sha256",
        "exact_parent_full_provenance_sha256",
        "frozen_parent_reservation_sha256",
    ):
        require_hash(reservation[key], f"R7 parent reservation {key}")
    if (
        not isinstance(reservation["generation_seed"], int)
        or isinstance(reservation["generation_seed"], bool)
        or not 0 <= reservation["generation_seed"] < 2**63
        or not isinstance(reservation["exact_parent_preflight_provenance"], dict)
        or not isinstance(reservation["exact_parent_full_provenance"], dict)
        or canonical_sha256(reservation["exact_parent_full_provenance"])
        != reservation["exact_parent_full_provenance_sha256"]
        or not isinstance(reservation["parent_authorization_ledger_path"], str)
        or not reservation["parent_authorization_ledger_path"].strip()
    ):
        raise R7GuardError("R7 parent reservation provenance or seed is invalid")
    return reservation


def validate_worker_launch_claim(claim: dict[str, Any], *, expected: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "schema", "status", "utc", "authorization_sha256",
        "authorization_nonce_sha256", "worker_instance_nonce_sha256",
        "independent_audit_decision_sha256", "independent_audit_subject_sha256",
        "independent_auditor_identity_sha256", "independent_audit_report_sha256",
        "payload_manifest_sha256", "bundle_id", "run_id", "attempt",
        "parent_reservation_path", "parent_reservation_sha256",
        "parent_ledger_path", "parent_ledger_sha256", "worker_path",
        "worker_sha256", "worker_command_sha256", "worker_pid",
    }
    require_exact_keys(claim, keys, "R7 worker launch claim")
    if (
        claim["schema"] != "qwen3_tts_voice_forge_worker_launch_claim_v7"
        or claim["status"]
        != "WORKER_CLAIMED_ONE_USE_BEFORE_PREDECESSOR_OR_MODEL_IMPORT"
        or any(claim.get(key) != expected.get(key) for key in keys - {"schema", "status", "utc", "worker_pid"})
        or not isinstance(claim["worker_pid"], int)
        or isinstance(claim["worker_pid"], bool)
        or claim["worker_pid"] <= 0
    ):
        raise R7GuardError("R7 worker claim is not bound to the exact parent launch")
    parse_utc(claim["utc"], "R7 worker claim utc")
    return claim


def validate_r7_profile_manifest_and_child(
    *,
    r6_profile: dict[str, Any],
    r7_profile: dict[str, Any],
    r7_manifest: dict[str, Any],
    child_result: dict[str, Any],
    semantic_binding: dict[str, Any],
    r6_profile_sha256: str,
    r6_manifest_sha256: str,
    r7_profile_sha256: str,
) -> None:
    validate_semantic_binding(semantic_binding)
    semantic_sha = canonical_sha256(semantic_binding)
    require_exact_keys(
        r7_profile,
        set(r6_profile) | R7_PROFILE_ADDITIONS,
        "R7 profile",
    )
    for key, value in r6_profile.items():
        if key != "schema" and r7_profile.get(key) != value:
            raise R7GuardError(f"R7 profile changed inherited R6 field: {key}")
    if (
        r7_profile["schema"] != "qwen3_tts_original_voice_profile_candidate_v7"
        or r7_profile["r7_status"]
        != "PRIVATE_UNREVIEWED_COMPLETE_PARENT_RECONCILIATION_PENDING"
        or r7_profile["predecessor_r6_profile_sha256"] != r6_profile_sha256
        or r7_profile["semantic_binding_v7"] != semantic_binding
        or r7_profile["semantic_binding_v7_sha256"] != semantic_sha
        or r7_profile["evaluator_evidence_v7_sha256"]
        != semantic_binding["evaluator_evidence_sha256"]
        or r7_profile["worker_resource_evidence_v7_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or r7_profile["worker_launch_claim_v7_sha256"]
        != semantic_binding["worker_launch_claim_sha256"]
        or r7_profile["parent_authorization_ledger_v7_sha256"]
        != semantic_binding["parent_authorization_ledger_sha256"]
        or r7_profile["complete_later_use_revalidation_v7_required"] is not True
    ):
        raise R7GuardError("R7 profile is not an exact safe R6 extension")
    require_exact_keys(r7_manifest, R7_MANIFEST_KEYS, "R7 worker manifest")
    if (
        r7_manifest["schema"] != "qwen3_tts_original_voice_forge_worker_manifest_v7"
        or r7_manifest["status"]
        != "CHILD_GATES_PASSED_PARENT_RECONCILIATION_AND_FINALIZATION_PENDING"
        or r7_manifest["semantic_binding_v7"] != semantic_binding
        or r7_manifest["semantic_binding_v7_sha256"] != semantic_sha
        or r7_manifest["profile_sha256"] != r7_profile_sha256
        or r7_manifest["predecessor_worker_manifest_sha256"] != r6_manifest_sha256
        or r7_manifest["predecessor_profile_sha256"] != r6_profile_sha256
        or r7_manifest["worker_launch_claim_sha256"]
        != semantic_binding["worker_launch_claim_sha256"]
        or r7_manifest["parent_authorization_ledger_sha256"]
        != semantic_binding["parent_authorization_ledger_sha256"]
        or r7_manifest["evaluator_evidence_sha256"]
        != semantic_binding["evaluator_evidence_sha256"]
        or r7_manifest["resource_evidence_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or r7_manifest["process_tree_quiescence_required_before_parent_finalization"] is not True
        or r7_manifest["parent_evaluator_and_resource_reconciliation_required"] is not True
        or any(r7_manifest[key] != value for key, value in FINAL_DISABLED_PERMISSIONS.items())
    ):
        raise R7GuardError("R7 worker manifest is not fully subject-bound and disabled")
    require_exact_keys(child_result, R7_CHILD_KEYS, "R7 child result")
    if (
        child_result["schema"] != "qwen3_tts_original_voice_forge_child_result_v7"
        or child_result["status"] != r7_manifest["status"]
        or child_result["semantic_binding_v7_sha256"] != semantic_sha
        or child_result["profile_sha256"] != r7_profile_sha256
        or child_result["evaluator_evidence_sha256"]
        != semantic_binding["evaluator_evidence_sha256"]
        or child_result["worker_resource_evidence_sha256"]
        != semantic_binding["resource_evidence_sha256"]
        or child_result["worker_launch_claim_sha256"]
        != semantic_binding["worker_launch_claim_sha256"]
    ):
        raise R7GuardError("R7 child result is not exactly bound")


def create_worker_launch_claim(
    *, project_root: Path, authorization_sha256: str, claim: dict[str, Any]
) -> tuple[Path, str]:
    validate_worker_launch_claim(
        claim,
        expected={key: value for key, value in claim.items() if key not in {"schema", "status", "utc", "worker_pid"}},
    )
    path = (
        project_root.resolve()
        / R7_WORKER_CLAIM_ROOT_REL
        / f"{require_hash(authorization_sha256, 'R7 claim authorization')}.json"
    )
    write_new_json(path, claim)
    digest = sha256_file(path)
    if strict_read_json(path, expected_sha256=digest, label="R7 reopened worker claim") != claim:
        raise R7GuardError("R7 worker claim changed after exclusive creation")
    return path, digest


def _normalize_final_windows_path(value: str) -> str:
    text = value.replace("/", "\\")
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[8:]
    elif text.startswith("\\\\?\\"):
        text = text[4:]
    return os.path.normcase(os.path.normpath(text))


class _FILE_ID_128(ctypes.Structure):
    _fields_ = [("Identifier", ctypes.c_ubyte * 16)]


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_uint64), ("FileId", _FILE_ID_128)]


def _windows_api() -> dict[str, Any]:
    if os.name != "nt":
        raise R7GuardError("R7 durable acceptance requires Windows file identities")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
    ]
    create.restype = ctypes.c_void_p
    get_info = kernel32.GetFileInformationByHandleEx
    get_info.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    get_info.restype = ctypes.c_int
    get_final = kernel32.GetFinalPathNameByHandleW
    get_final.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    get_final.restype = ctypes.c_uint32
    get_size = kernel32.GetFileSizeEx
    get_size.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int64)]
    get_size.restype = ctypes.c_int
    close = kernel32.CloseHandle
    close.argtypes = [ctypes.c_void_p]
    close.restype = ctypes.c_int
    return {"create": create, "get_info": get_info, "get_final": get_final, "get_size": get_size, "close": close}


def _open_windows_lease(path: Path, *, directory: bool, api: dict[str, Any]) -> int:
    generic_read = 0x80000000
    file_read_attributes = 0x00000080
    share_read = 0x00000001
    share_write = 0x00000002
    open_existing = 3
    normal = 0x00000080
    backup_semantics = 0x02000000
    desired = file_read_attributes if directory else generic_read
    share = share_read | share_write if directory else share_read
    flags = backup_semantics if directory else normal
    handle = api["create"](str(path.resolve()), desired, share, None, open_existing, flags, None)
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, invalid):
        raise R7GuardError(
            f"cannot hold R7 {'directory' if directory else 'file'} identity: {path}; winerror={ctypes.get_last_error()}"
        )
    return int(handle)


def _identity_from_handle(handle: int, api: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
    info = _FILE_ID_INFO()
    file_id_info_class = 18
    if not api["get_info"](
        ctypes.c_void_p(handle), file_id_info_class, ctypes.byref(info), ctypes.sizeof(info)
    ):
        raise R7GuardError(f"cannot query R7 FILE_ID_INFO; winerror={ctypes.get_last_error()}")
    needed = api["get_final"](ctypes.c_void_p(handle), None, 0, 0)
    if needed <= 0:
        raise R7GuardError(f"cannot size R7 final path; winerror={ctypes.get_last_error()}")
    buffer = ctypes.create_unicode_buffer(needed + 1)
    written = api["get_final"](ctypes.c_void_p(handle), buffer, len(buffer), 0)
    if written <= 0 or written >= len(buffer):
        raise R7GuardError(f"cannot query R7 final path; winerror={ctypes.get_last_error()}")
    size = ctypes.c_int64()
    if not api["get_size"](ctypes.c_void_p(handle), ctypes.byref(size)):
        raise R7GuardError(f"cannot query R7 held size; winerror={ctypes.get_last_error()}")
    normalized = _normalize_final_windows_path(buffer.value)
    identity = {
        "volume_serial_hex": f"{int(info.VolumeSerialNumber):016x}",
        "file_id_hex": bytes(info.FileId.Identifier).hex(),
        "normalized_final_path_sha256": sha256_bytes(normalized.encode("utf-8")),
    }
    return identity, int(size.value), normalized


def windows_file_identity(path: Path) -> dict[str, Any]:
    api = _windows_api()
    handle = _open_windows_lease(path, directory=False, api=api)
    try:
        identity, _size, _final = _identity_from_handle(handle, api)
        return identity
    finally:
        api["close"](ctypes.c_void_p(handle))


def validate_windows_file_identity(value: Any, label: str) -> dict[str, Any]:
    require_exact_keys(value, WINDOWS_FILE_IDENTITY_KEYS, label)
    if (
        not re.fullmatch(r"[0-9a-f]{16}", str(value["volume_serial_hex"] or ""))
        or not HEX128.fullmatch(str(value["file_id_hex"] or ""))
    ):
        raise R7GuardError(f"{label} has an invalid Windows file ID")
    require_hash(value["normalized_final_path_sha256"], f"{label} final path")
    return value


class HeldWindowsFileSet:
    """No-write/no-delete file leases plus no-delete ancestor leases."""

    def __init__(self, *, project_root: Path, paths: list[Path]) -> None:
        self.project_root = project_root.resolve()
        self.paths = sorted({path.resolve() for path in paths}, key=lambda p: str(p).casefold())
        self.api: dict[str, Any] | None = None
        self.directory_handles: list[int] = []
        self.file_handles: dict[Path, int] = {}
        self.initial_rows: dict[Path, dict[str, Any]] = {}

    def __enter__(self) -> "HeldWindowsFileSet":
        self.api = _windows_api()
        ancestors: set[Path] = set()
        for path in self.paths:
            project_relative(self.project_root, path, "R7 held file")
            current = path.parent
            while current != self.project_root.parent:
                ancestors.add(current)
                if current == self.project_root:
                    break
                current = current.parent
        try:
            for directory in sorted(ancestors, key=lambda p: (len(p.parts), str(p).casefold())):
                handle = _open_windows_lease(directory, directory=True, api=self.api)
                self.directory_handles.append(handle)
            for path in self.paths:
                handle = _open_windows_lease(path, directory=False, api=self.api)
                self.file_handles[path] = handle
                identity, size, final_path = _identity_from_handle(handle, self.api)
                if final_path != _normalize_final_windows_path(str(path.resolve())):
                    raise R7GuardError("R7 held file resolved through a final-path alias")
                self.initial_rows[path] = {
                    "bytes": size,
                    "sha256": sha256_file(path),
                    "windows_file_identity": identity,
                }
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def add_file(self, path: Path) -> dict[str, Any]:
        if self.api is None:
            raise R7GuardError("R7 held set is not active")
        path = path.resolve()
        if path in self.file_handles:
            return self.initial_rows[path]
        project_relative(self.project_root, path, "R7 additional held file")
        handle = _open_windows_lease(path, directory=False, api=self.api)
        self.file_handles[path] = handle
        identity, size, final_path = _identity_from_handle(handle, self.api)
        if final_path != _normalize_final_windows_path(str(path)):
            raise R7GuardError("R7 additional held file resolved through an alias")
        self.initial_rows[path] = {
            "bytes": size,
            "sha256": sha256_file(path),
            "windows_file_identity": identity,
        }
        return self.initial_rows[path]

    def verify(self) -> None:
        if self.api is None:
            raise R7GuardError("R7 held set is not active")
        for path, handle in self.file_handles.items():
            identity, size, final_path = _identity_from_handle(handle, self.api)
            initial = self.initial_rows[path]
            if (
                final_path != _normalize_final_windows_path(str(path.resolve()))
                or identity != initial["windows_file_identity"]
                or size != initial["bytes"]
                or sha256_file(path) != initial["sha256"]
            ):
                raise R7GuardError(f"R7 held identity or bytes changed: {path}")

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
        if self.api is None:
            return
        for handle in reversed(list(self.file_handles.values())):
            self.api["close"](ctypes.c_void_p(handle))
        for handle in reversed(self.directory_handles):
            self.api["close"](ctypes.c_void_p(handle))
        self.file_handles.clear()
        self.directory_handles.clear()
        self.api = None


@contextlib.contextmanager
def hold_windows_file_leases(
    *, project_root: Path, paths: list[Path]
) -> Iterator[HeldWindowsFileSet]:
    with HeldWindowsFileSet(project_root=project_root, paths=paths) as held:
        yield held


def file_row_from_held(
    *, project_root: Path, role: str, path: Path, held: HeldWindowsFileSet
) -> dict[str, Any]:
    path = path.resolve()
    row = held.initial_rows.get(path)
    if row is None:
        raise R7GuardError(f"R7 accepted role is not held: {role}")
    return {
        "role": role,
        "path": project_relative(project_root, path, f"R7 accepted {role}"),
        **row,
    }


def verify_accepted_files(
    *,
    project_root: Path,
    rows: list[dict[str, Any]],
    identity_provider: Callable[[Path], dict[str, Any]] = windows_file_identity,
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise R7GuardError("R7 accepted file inventory is empty")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        require_exact_keys(row, ACCEPTED_FILE_ROW_KEYS, "R7 accepted file row")
        role = str(row["role"] or "")
        if not role or role in indexed:
            raise R7GuardError("R7 accepted role is empty or duplicate")
        path = inside(project_root, row["path"], f"R7 accepted {role}")
        expected_identity = validate_windows_file_identity(
            row["windows_file_identity"], f"R7 accepted {role} identity"
        )
        if (
            not path.is_file()
            or path.is_symlink()
            or not isinstance(row["bytes"], int)
            or isinstance(row["bytes"], bool)
            or row["bytes"] < 0
            or path.stat().st_size != row["bytes"]
            or sha256_file(path) != require_hash(row["sha256"], f"R7 accepted {role}")
            or identity_provider(path) != expected_identity
        ):
            raise R7GuardError(f"R7 accepted file bytes/identity drift: {role}")
        indexed[role] = row
    return indexed


def commit_acceptance_with_held_identities(
    *,
    project_root: Path,
    held: HeldWindowsFileSet,
    acceptance_path: Path,
    acceptance: dict[str, Any],
    reopen_validator: Callable[[dict[str, Any]], None],
    commit_token_path: Path,
) -> dict[str, Any]:
    held.verify()
    write_new_json(acceptance_path, acceptance)
    acceptance_held = held.add_file(acceptance_path)
    reopened = strict_read_json(
        acceptance_path,
        expected_sha256=acceptance_held["sha256"],
        label="R7 held durable acceptance",
    )
    if reopened != acceptance:
        raise R7GuardError("R7 acceptance changed after durable write")
    reopen_validator(reopened)
    held.verify()
    token = {
        "schema": "qwen3_tts_voice_forge_windows_identity_commit_v7",
        "status": "ACCEPTANCE_REOPENED_WITH_ALL_INPUT_LEASES_HELD",
        "acceptance_path": project_relative(project_root, acceptance_path, "R7 acceptance"),
        "acceptance_sha256": acceptance_held["sha256"],
        "acceptance_windows_file_identity": acceptance_held["windows_file_identity"],
        "held_input_identities_sha256": acceptance["held_file_identities_sha256"],
        "committed_utc": utc_now(),
    }
    write_new_json(commit_token_path, token)
    token_held = held.add_file(commit_token_path)
    if strict_read_json(
        commit_token_path,
        expected_sha256=token_held["sha256"],
        label="R7 held identity commit token",
    ) != token:
        raise R7GuardError("R7 identity commit token changed after write")
    held.verify()
    return {
        "acceptance_sha256": acceptance_held["sha256"],
        "acceptance_windows_file_identity": acceptance_held["windows_file_identity"],
        "commit_token_sha256": token_held["sha256"],
        "commit_token_windows_file_identity": token_held["windows_file_identity"],
    }


def validate_complete_reopened_acceptance(
    *,
    project_root: Path,
    acceptance: dict[str, Any],
    required_payloads: set[str],
    semantic_validator: Callable[[dict[str, dict[str, Any]], dict[str, Any]], None],
    identity_provider: Callable[[Path], dict[str, Any]] = windows_file_identity,
) -> dict[str, Any]:
    require_exact_keys(acceptance, ACCEPTANCE_KEYS, "R7 parent acceptance")
    if (
        acceptance["schema"] != "qwen3_tts_original_voice_forge_parent_acceptance_v7"
        or acceptance["status"]
        != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_FRESH_EXECUTION_AUDIT_REQUIRED"
        or acceptance["payload_manifest_path"] != R7_PAYLOAD_MANIFEST_REL.as_posix()
        or acceptance["rejected_r6_audit_path"] != R6_REJECTED_AUDIT_REL.as_posix()
        or acceptance["rejected_r6_audit_sha256"] != R6_REJECTED_AUDIT_SHA256
        or acceptance["windows_identity_commit_required"] is not True
        or acceptance["owner_hearing_acceptance"] != "PENDING"
        or acceptance["assignment_allowed"] is not False
        or acceptance["activation_allowed"] is not False
        or acceptance["publication_or_upload_allowed"] is not False
        or acceptance["complete_later_use_revalidation_required"] is not True
    ):
        raise R7GuardError("R7 later-use acceptance state is unsafe")
    semantic = validate_semantic_binding(acceptance["semantic_binding_v7"])
    if acceptance["semantic_binding_v7_sha256"] != canonical_sha256(semantic):
        raise R7GuardError("R7 later-use semantic binding digest mismatch")
    manifest, _indexed_payload = verify_payload_manifest(
        project_root=project_root,
        expected_manifest_sha256=acceptance["payload_manifest_sha256"],
        required_payloads=required_payloads,
    )
    verified_at = parse_utc(
        acceptance["authorization_verified_at_start_utc"],
        "R7 acceptance authorization verification time",
    )
    accepted_at = parse_utc(acceptance["accepted_utc"], "R7 accepted_utc")
    if accepted_at < verified_at:
        raise R7GuardError("R7 acceptance predates authorization verification")
    authorization, audit_evidence = verify_execution_authorization(
        project_root=project_root,
        authorization_path=inside(
            project_root, acceptance["execution_authorization_path"], "R7 later-use authorization"
        ),
        expected_authorization_sha256=acceptance["execution_authorization_sha256"],
        expected_manifest_sha256=acceptance["payload_manifest_sha256"],
        expected_inventory_sha256=payload_inventory_sha256(manifest),
        bundle_id=semantic["bundle_id"],
        run_id=semantic["run_id"],
        verified_at=verified_at,
    )
    exact_pairs = {
        "payload_manifest_sha256": acceptance["payload_manifest_sha256"],
        "execution_authorization_sha256": acceptance[
            "execution_authorization_sha256"
        ],
        "execution_authorization_nonce_sha256": authorization[
            "authorization_nonce_sha256"
        ],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "execution_authorization_path": acceptance["execution_authorization_path"],
        "independent_audit_decision_path": audit_evidence["decision_path"],
        "independent_audit_decision_sha256": audit_evidence["decision_sha256"],
        "independent_audit_subject_sha256": audit_evidence["subject_sha256"],
        "independent_auditor_identity_sha256": audit_evidence["auditor_identity_sha256"],
        "independent_audit_report_path": audit_evidence["report_path"],
        "independent_audit_report_sha256": audit_evidence["report_sha256"],
        "generation_seed": authorization["generation_seed"],
    }
    if any(semantic[key] != value for key, value in exact_pairs.items()):
        raise R7GuardError("R7 later-use authorization identity differs from semantic binding")
    for acceptance_key, value in (
        ("independent_audit_decision_path", audit_evidence["decision_path"]),
        ("independent_audit_decision_sha256", audit_evidence["decision_sha256"]),
        ("independent_audit_subject_sha256", audit_evidence["subject_sha256"]),
        ("independent_auditor_identity_sha256", audit_evidence["auditor_identity_sha256"]),
        ("independent_r7_audit_path", audit_evidence["report_path"]),
        ("independent_r7_audit_sha256", audit_evidence["report_sha256"]),
    ):
        if acceptance[acceptance_key] != value:
            raise R7GuardError("R7 acceptance changed the reverified audit identity")
    rows = acceptance["accepted_files"]
    if (
        canonical_sha256(rows) != acceptance["accepted_files_sha256"]
        or canonical_sha256([row["windows_file_identity"] for row in rows])
        != acceptance["held_file_identities_sha256"]
    ):
        raise R7GuardError("R7 accepted file/identity inventory digest mismatch")
    indexed = verify_accepted_files(
        project_root=project_root, rows=rows, identity_provider=identity_provider
    )
    for role, path_key, hash_key in (
        ("parent_authorization_ledger", "parent_authorization_ledger_path", "parent_authorization_ledger_sha256"),
        ("worker_launch_claim", "worker_launch_claim_path", "worker_launch_claim_sha256"),
    ):
        row = indexed.get(role)
        if row is None or row["path"] != acceptance[path_key] or row["sha256"] != acceptance[hash_key]:
            raise R7GuardError(f"R7 later-use {role} is not in the held inventory")
    if (
        acceptance["parent_authorization_ledger_sha256"]
        != semantic["parent_authorization_ledger_sha256"]
        or acceptance["worker_launch_claim_sha256"]
        != semantic["worker_launch_claim_sha256"]
    ):
        raise R7GuardError("R7 acceptance changed the semantic ledger/claim identity")
    semantic_validator(indexed, semantic)
    return acceptance


def reopen_acceptance_for_later_use(
    *,
    project_root: Path,
    acceptance_path: Path,
    expected_acceptance_sha256: str,
    commit_token_path: Path,
    expected_commit_token_sha256: str,
    required_payloads: set[str],
    semantic_validator: Callable[[dict[str, dict[str, Any]], dict[str, Any]], None],
    identity_provider: Callable[[Path], dict[str, Any]] = windows_file_identity,
) -> dict[str, Any]:
    acceptance = strict_read_json(
        acceptance_path,
        expected_sha256=expected_acceptance_sha256,
        label="R7 later-use parent acceptance",
    )
    validate_complete_reopened_acceptance(
        project_root=project_root,
        acceptance=acceptance,
        required_payloads=required_payloads,
        semantic_validator=semantic_validator,
        identity_provider=identity_provider,
    )
    token = strict_read_json(
        commit_token_path,
        expected_sha256=expected_commit_token_sha256,
        label="R7 later-use identity commit token",
    )
    require_exact_keys(
        token,
        {
            "schema", "status", "acceptance_path", "acceptance_sha256",
            "acceptance_windows_file_identity", "held_input_identities_sha256",
            "committed_utc",
        },
        "R7 identity commit token",
    )
    if (
        token["schema"] != "qwen3_tts_voice_forge_windows_identity_commit_v7"
        or token["status"] != "ACCEPTANCE_REOPENED_WITH_ALL_INPUT_LEASES_HELD"
        or token["acceptance_path"]
        != project_relative(project_root, acceptance_path, "R7 committed acceptance")
        or token["acceptance_sha256"] != expected_acceptance_sha256
        or token["held_input_identities_sha256"]
        != acceptance["held_file_identities_sha256"]
        or identity_provider(acceptance_path)
        != validate_windows_file_identity(
            token["acceptance_windows_file_identity"], "R7 committed acceptance identity"
        )
    ):
        raise R7GuardError("R7 identity commit token does not bind the acceptance")
    parse_utc(token["committed_utc"], "R7 identity commit time")
    return acceptance
