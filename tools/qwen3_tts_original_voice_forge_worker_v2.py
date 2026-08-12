"""Append-only R2 Qwen3-TTS original-voice forge worker.

This successor does not import Torch, Qwen3-TTS, ASR, or speaker-embedding
packages at module import time.  Production execution accepts only a bundle ID
registered under the fixed trusted bundle root; callers cannot supply paths or
authorization hashes.
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import gc
import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import struct
import sys
import threading
import time
import traceback
import wave
import zipfile
from email.parser import BytesParser
from email.policy import default as email_policy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json")
BUNDLE_ROOT_REL = Path("TemporaryAI/voice_forge_acceptance_bundles_v2")
REGISTRY_REL = Path("Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json")
ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
EVALUATION_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")
EVALUATION_CORPUS_ROOT_REL = Path("Data/voice/evaluation_corpus/qwen3_tts_voice_forge_v2")
OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v2")
NONCE_LEDGER_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_nonce_ledger_v2")
HARNESS_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json")
RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
CONTRACT_ID = "temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2"
VOICE_ORIGIN = "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE"
IDENTITY_BASIS = "original_trait_description"
INITIAL_WATERMARK_STATUS = "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK"
HISTORICAL_WATERMARK_PREFLIGHT_STATUS = "HISTORICAL_EVIDENCE_VERIFIED_LIVE_BUILTIN_SCAN_STILL_REQUIRED"
STRONG_WATERMARK_STATUS = "NO_DOCUMENTED_OR_KNOWN_WATERMARK_DETECTED_AT_ACCEPTED_REVISION"
FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"
NETWORK_BOUNDARY = "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL"
ISOLATED_ROOT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2")
ISOLATED_VENV_REL = ISOLATED_ROOT_REL / ".venv"
WHEEL_EVIDENCE_ROOT_REL = ISOLATED_ROOT_REL / "wheel_evidence"
EVALUATOR_ROOT_REL = ISOLATED_ROOT_REL / "evaluators"
ELIGIBLE_AI_TYPES = {"expert_temp_ai", "generated_original_temp_ai"}
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,95}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMITATION_LANGUAGE = re.compile(
    r"\b(?:sound|voice|speak|talk|timbre|style)\b.{0,35}\b(?:like|of|copy|clone|imitat|impersonat|inspired)\w*\b|"
    r"\b(?:like|copy|clone|imitat|impersonat|inspired)\w*\b.{0,35}\b(?:voice|timbre|style)\b",
    re.IGNORECASE,
)
KNOWN_ADVERSARIAL_PERSON = re.compile(r"\btaylor\s+swift\b", re.IGNORECASE)


class R2ForgeError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise R2ForgeError(f"invalid exact JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise R2ForgeError(f"JSON root is not an object: {path}")
    return value


def write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def write_new_json(path: Path, value: Any) -> None:
    write_new(path, canonical_bytes(value))


def require_hash(value: Any, label: str) -> str:
    normalized = str(value or "").lower()
    if not HEX64.fullmatch(normalized):
        raise R2ForgeError(f"{label} is not one lowercase SHA-256")
    return normalized


def verify_file(path: Path, expected: Any, label: str) -> None:
    if not path.is_file():
        raise R2ForgeError(f"{label} is missing: {path}")
    actual = sha256_file(path)
    if actual != require_hash(expected, f"{label} hash"):
        raise R2ForgeError(f"{label} hash mismatch: expected {expected}, got {actual}")


def inside(root: Path, relative: str | Path, label: str) -> Path:
    value = Path(relative)
    if value.is_absolute():
        raise R2ForgeError(f"{label} must be relative")
    result = (root / value).resolve()
    try:
        result.relative_to(root.resolve())
    except ValueError as exc:
        raise R2ForgeError(f"{label} escaped its trusted root") from exc
    return result


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def parse_utc(value: Any, label: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise R2ForgeError(f"{label} is not ISO-8601") from exc
    if result.tzinfo is None:
        raise R2ForgeError(f"{label} lacks a timezone")
    return result


def verify_independent_audit_harness(project_root: Path) -> dict[str, Any]:
    manifest_path = (project_root / HARNESS_MANIFEST_REL).resolve()
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "qwen3_tts_voice_forge_harness_manifest_v2" or manifest.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN":
        raise R2ForgeError("R2 harness has not passed the required independent audit")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R2ForgeError("independent-audit harness inventory is invalid")
    indexed: set[str] = set()
    for row in rows:
        rel = str(row.get("path") or "") if isinstance(row, dict) else ""
        if not rel or rel in indexed:
            raise R2ForgeError("independent-audit harness row is invalid/duplicate")
        indexed.add(rel)
        path = inside(project_root, rel, "independent-audit harness file")
        verify_file(path, row.get("sha256"), f"independent-audit harness file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError(f"independent-audit harness file size mismatch: {rel}")
    required = {
        CONTRACT_REL.as_posix(), ENVIRONMENT_REL.as_posix(), REGISTRY_REL.as_posix(),
        EVALUATION_CORPUS_REL.as_posix(), RUNNER_REL.as_posix(), WORKER_REL.as_posix(),
    }
    if not required.issubset(indexed):
        raise R2ForgeError("independent-audit harness omits a controlling file")
    return manifest


def queue_binding_payload(bundle: dict[str, Any]) -> dict[str, str]:
    return {
        "bundle_id": str(bundle["bundle_id"]),
        "candidate_id": str(bundle["candidate_id"]),
        "opaque_voice_id": str(bundle["opaque_voice_id"]),
        "ai_type": str(bundle["ai_type"]),
        "job_sha256": str(bundle["job_sha256"]),
        "single_use_nonce_sha256": str(bundle["single_use_nonce_sha256"]),
        "canonical_profile_sha256": str(bundle["canonical_profile_sha256"]),
        "canonical_creation_request_sha256": str(bundle["canonical_creation_request_sha256"]),
        "identity_clearance_manifest_sha256": str(bundle["identity_clearance_manifest_sha256"]),
        "watermark_evidence_manifest_sha256": str(bundle["watermark_evidence_manifest_sha256"]),
        "evaluation_corpus_sha256": str(bundle["evaluation_corpus_sha256"]),
        "voice_design_model_manifest_sha256": str(bundle["voice_design_model_manifest_sha256"]),
        "base_model_manifest_sha256": str(bundle["base_model_manifest_sha256"]),
        "environment_spec_sha256": str(bundle["environment_spec_sha256"]),
    }


def compute_queue_binding(bundle: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(queue_binding_payload(bundle)))


@dataclass(frozen=True)
class TrustedBundle:
    project_root: Path
    bundle_dir: Path
    bundle: dict[str, Any]
    job: dict[str, Any]
    profile: dict[str, Any]
    creation_request: dict[str, Any]
    owner_authorization: dict[str, Any]
    identity_clearance: dict[str, Any]
    watermark_manifest: dict[str, Any]
    evaluation_corpus: dict[str, Any]
    contract: dict[str, Any]
    environment_spec: dict[str, Any]
    registry_entry: dict[str, Any]


def _sealed_bundle_files(bundle_dir: Path, seal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = seal.get("files")
    if seal.get("schema") != "qwen3_tts_original_voice_forge_bundle_seal_v2" or not isinstance(rows, list):
        raise R2ForgeError("bundle seal schema or file inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R2ForgeError("bundle seal row is invalid")
        name = str(row["path"])
        if name in indexed or name == "BUNDLE_SEAL.json":
            raise R2ForgeError("bundle seal has a duplicate or recursive path")
        path = inside(bundle_dir, name, "sealed bundle file")
        verify_file(path, row.get("sha256"), f"sealed bundle file {name}")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError(f"sealed bundle file size mismatch: {name}")
        indexed[name] = row
    actual = {
        relative(path, bundle_dir)
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != "BUNDLE_SEAL.json"
    }
    if actual != set(indexed):
        raise R2ForgeError("bundle seal is not a complete exact inventory")
    return indexed


def _bundle_file(bundle_dir: Path, value: Any, expected: Any, sealed: dict[str, Any], label: str) -> Path:
    path = inside(bundle_dir, str(value or ""), label)
    rel = relative(path, bundle_dir)
    if rel not in sealed:
        raise R2ForgeError(f"{label} is not in the trusted bundle seal")
    verify_file(path, expected, label)
    return path


def validate_canonical_candidate(project_root: Path, bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_id = str(bundle.get("candidate_id") or "")
    ai_type = str(bundle.get("ai_type") or "")
    if not SAFE_ID.fullmatch(candidate_id) or ai_type not in ELIGIBLE_AI_TYPES:
        raise R2ForgeError("candidate ID or ai_type is not eligible")
    expected_root = (project_root / "TemporaryAI" / "candidates" / candidate_id).resolve()
    profile_path = inside(project_root, str(bundle.get("canonical_profile_path") or ""), "canonical profile")
    creation_path = inside(
        project_root,
        str(bundle.get("canonical_creation_request_path") or ""),
        "canonical creation request",
    )
    if profile_path != expected_root / "temporary_ai_profile.json":
        raise R2ForgeError("profile is not the canonical candidate profile")
    if creation_path != expected_root / "creation_request.json":
        raise R2ForgeError("creation request is not the canonical candidate request")
    verify_file(profile_path, bundle.get("canonical_profile_sha256"), "canonical profile")
    verify_file(creation_path, bundle.get("canonical_creation_request_sha256"), "canonical creation request")
    profile = read_json(profile_path)
    creation = read_json(creation_path)
    if profile.get("candidate_id") != candidate_id or profile.get("ai_type") != ai_type:
        raise R2ForgeError("profile candidate/ai_type binding mismatch")
    if creation.get("request_id") != f"temp_ai_request_{candidate_id}" or creation.get("ai_type") != ai_type:
        raise R2ForgeError("creation request candidate/ai_type binding mismatch")
    if profile.get("status") not in {"draft", "draft_review_only_not_activated", "draft_pending_review", "candidate_created_pending_review", "inactive_private_candidate"}:
        raise R2ForgeError("canonical profile is not an inactive review candidate")
    profile_id = str(profile.get("profile_id") or "")
    if not profile_id.startswith(f"{candidate_id}_temporary_ai_profile_v"):
        raise R2ForgeError("canonical profile is not a durable candidate record")
    if creation.get("template_id") != "temporary_ai_creation_request_template_v2":
        raise R2ForgeError("canonical creation request schema mismatch")
    if str(creation.get("requested_by") or "").casefold() not in {"real_robert", "robert"}:
        raise R2ForgeError("canonical creation request lacks owner provenance")
    creation_status = creation.get("status") or (creation.get("lifecycle") or {}).get("status")
    if creation_status not in {"draft", "draft_review_only_not_activated", "draft_pending_review", "candidate_created_pending_review", "inactive_private_candidate"}:
        raise R2ForgeError("canonical creation request is not inactive/private")
    return profile, creation


def validate_job(job: dict[str, Any]) -> None:
    if job.get("schema") != "qwen3_tts_original_voice_forge_job_v2":
        raise R2ForgeError("job schema mismatch")
    if job.get("voice_origin") != VOICE_ORIGIN or job.get("identity_basis") != IDENTITY_BASIS:
        raise R2ForgeError("job is not the original trait-described lane")
    for prefix in ("design_traits", "reference", "test"):
        text = str(job.get(f"{prefix}_text") or "")
        if not text.strip() or sha256_text(text) != require_hash(job.get(f"{prefix}_text_sha256"), f"{prefix} hash"):
            raise R2ForgeError(f"{prefix} text is missing or hash-mismatched")
    if not str(job.get("language") or "").strip():
        raise R2ForgeError("job language is missing")


def validate_owner_authorization(owner: dict[str, Any], bundle: dict[str, Any]) -> None:
    if owner.get("schema") != "qwen3_tts_original_voice_forge_owner_authorization_v2":
        raise R2ForgeError("owner authorization schema mismatch")
    if owner.get("status") != "OWNER_AUTHORIZED_SINGLE_USE" or owner.get("owner_id") != "robert":
        raise R2ForgeError("owner authorization is not active and exact")
    if owner.get("single_use") is not True or owner.get("revoked") is not False:
        raise R2ForgeError("owner authorization is revoked or not single-use")
    for key in (
        "bundle_id",
        "candidate_id",
        "opaque_voice_id",
        "ai_type",
        "single_use_nonce_sha256",
        "queue_binding_sha256",
        "job_sha256",
        "canonical_profile_sha256", "canonical_creation_request_sha256",
        "identity_clearance_manifest_sha256", "watermark_evidence_manifest_sha256",
        "evaluation_corpus_sha256", "voice_design_model_manifest_sha256",
        "base_model_manifest_sha256", "environment_spec_sha256",
    ):
        if owner.get(key) != bundle.get(key):
            raise R2ForgeError(f"owner authorization {key} mismatch")
    if owner.get("authorized_scope") != "ONE_PRIVATE_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_V2":
        raise R2ForgeError("owner authorization scope mismatch")
    now = datetime.now(timezone.utc)
    if parse_utc(owner.get("authorized_utc"), "authorized_utc") > now:
        raise R2ForgeError("owner authorization is from the future")
    if parse_utc(owner.get("expires_utc"), "expires_utc") <= now:
        raise R2ForgeError("owner authorization expired")


def validate_identity_clearance(
    *, bundle_dir: Path, manifest: dict[str, Any], sealed: dict[str, Any], job: dict[str, Any], bundle: dict[str, Any]
) -> None:
    if manifest.get("schema") != "qwen3_tts_original_voice_identity_clearance_manifest_v2":
        raise R2ForgeError("identity-clearance manifest schema mismatch")
    if manifest.get("status") != "CLEARED_ORIGINAL_TRAIT_ONLY":
        raise R2ForgeError("identity clearance did not pass")
    if manifest.get("candidate_id") != bundle["candidate_id"] or manifest.get("opaque_voice_id") != bundle["opaque_voice_id"]:
        raise R2ForgeError("identity clearance candidate/voice mismatch")
    if manifest.get("design_traits_sha256") != job["design_traits_text_sha256"]:
        raise R2ForgeError("identity clearance input hash mismatch")
    report_path = _bundle_file(
        bundle_dir,
        manifest.get("analyzer_report_path"),
        manifest.get("analyzer_report_sha256"),
        sealed,
        "identity analyzer report",
    )
    review_path = _bundle_file(
        bundle_dir,
        manifest.get("owner_review_path"),
        manifest.get("owner_review_sha256"),
        sealed,
        "owner identity review",
    )
    report = read_json(report_path)
    review = read_json(review_path)
    if report.get("schema") != "qwen3_tts_identity_analyzer_report_v2":
        raise R2ForgeError("identity analyzer report schema mismatch")
    if report.get("mode") != "REAL_LOCAL_NER_AND_IMITATION_CLASSIFIER" or not all(
        str(report.get(key) or "").strip() for key in (
            "analyzer_name", "analyzer_version", "analyzer_model_manifest_path", "analyzer_model_manifest_sha256"
        )
    ):
        raise R2ForgeError("identity analysis is self-asserted or lacks exact analyzer provenance")
    require_hash(report["analyzer_model_manifest_sha256"], "identity analyzer model manifest")
    analyzer_manifest = _bundle_file(
        bundle_dir,
        report["analyzer_model_manifest_path"],
        report["analyzer_model_manifest_sha256"],
        sealed,
        "identity analyzer model manifest",
    )
    analyzer_payload = read_json(analyzer_manifest)
    if analyzer_payload.get("schema") != "qwen3_tts_identity_analyzer_model_manifest_v2" or analyzer_payload.get("status") != "ACCEPTED_EXACT_LOCAL_ANALYZER" or analyzer_payload.get("complete_file_inventory") is not True:
        raise R2ForgeError("identity analyzer model manifest is not accepted exact local evidence")
    if analyzer_payload.get("engine") != report.get("analyzer_name") or analyzer_payload.get("version") != report.get("analyzer_version"):
        raise R2ForgeError("identity analyzer report is not bound to the exact analyzer model")
    analyzer_files = analyzer_payload.get("files")
    if not isinstance(analyzer_files, list) or not analyzer_files:
        raise R2ForgeError("identity analyzer model manifest has no exact files")
    for row in analyzer_files:
        if not isinstance(row, dict):
            raise R2ForgeError("identity analyzer model inventory is invalid")
        evidence_file = _bundle_file(bundle_dir, row.get("path"), row.get("sha256"), sealed, "identity analyzer model file")
        if evidence_file.stat().st_size != row.get("bytes"):
            raise R2ForgeError("identity analyzer model file size mismatch")
    if report.get("input_sha256") != job["design_traits_text_sha256"]:
        raise R2ForgeError("identity analyzer input mismatch")
    if report.get("execution_mode") != "HASH_BOUND_LOCAL_ANALYZER_EXECUTION" or report.get("process_returncode") != 0:
        raise R2ForgeError("identity analyzer execution evidence is absent")
    for prefix in ("command", "stdout", "stderr"):
        evidence_path = _bundle_file(
            bundle_dir,
            report.get(f"{prefix}_path"),
            report.get(f"{prefix}_sha256"),
            sealed,
            f"identity analyzer {prefix} evidence",
        )
        if prefix == "command":
            command_payload = read_json(evidence_path)
            if command_payload.get("schema") != "qwen3_tts_identity_analyzer_command_v2":
                raise R2ForgeError("identity analyzer command evidence schema mismatch")
            if command_payload.get("input_sha256") != job["design_traits_text_sha256"]:
                raise R2ForgeError("identity analyzer command was not bound to this exact input")
            if command_payload.get("engine") != report.get("analyzer_name") or command_payload.get("version") != report.get("analyzer_version"):
                raise R2ForgeError("identity analyzer command provenance mismatch")
    if report.get("detected_named_person_entities") != [] or report.get("named_person_imitation_requested") is not False:
        raise R2ForgeError("identity analyzer found a named person or imitation request")
    if review.get("schema") != "qwen3_tts_owner_identity_clearance_v2" or review.get("decision") != "CLEARED_ORIGINAL_TRAIT_ONLY":
        raise R2ForgeError("owner identity review did not clear this exact design")
    if review.get("design_traits_sha256") != job["design_traits_text_sha256"] or review.get("owner_id") != "robert":
        raise R2ForgeError("owner identity review binding mismatch")
    traits = str(job["design_traits_text"])
    if KNOWN_ADVERSARIAL_PERSON.search(traits) or IMITATION_LANGUAGE.search(traits):
        raise R2ForgeError("design text contains named-person or imitation phrasing despite clearance")


def validate_watermark_preflight(
    *, project_root: Path, bundle_dir: Path, manifest: dict[str, Any], sealed: dict[str, Any], bundle: dict[str, Any]
) -> str:
    if manifest.get("schema") != "qwen3_tts_original_voice_watermark_preflight_manifest_v2":
        raise R2ForgeError("watermark manifest schema mismatch")
    if manifest.get("status") != "PREFLIGHT_EVIDENCE_COMPLETE_INITIAL_STATUS_ONLY":
        raise R2ForgeError("watermark preflight evidence is incomplete")
    if manifest.get("stronger_status_requested") is not False:
        raise R2ForgeError("stronger watermark status cannot be self-requested in generation")
    if manifest.get("permitted_runtime_status") != INITIAL_WATERMARK_STATUS:
        raise R2ForgeError("watermark runtime status is overstated")
    evidence = manifest.get("evidence")
    if not isinstance(evidence, list):
        raise R2ForgeError("watermark evidence list is invalid")
    required = {"EXACT_REVISION_SOURCE_SCAN", "EXACT_DEPENDENCY_SCAN"}
    found: set[str] = set()
    for row in evidence:
        if not isinstance(row, dict) or row.get("kind") in found:
            raise R2ForgeError("watermark evidence row is invalid or duplicated")
        kind = str(row.get("kind") or "")
        found.add(kind)
        evidence_path = _bundle_file(bundle_dir, row.get("path"), row.get("sha256"), sealed, f"watermark evidence {kind}")
        payload = read_json(evidence_path)
        if payload.get("schema") != "qwen3_tts_watermark_preflight_evidence_v2" or payload.get("kind") != kind:
            raise R2ForgeError("watermark evidence schema/kind mismatch")
        if payload.get("status") != "PASS_NO_DOCUMENTED_INTENTIONAL_WATERMARK_STAGE_FOUND":
            raise R2ForgeError("watermark evidence did not pass")
        if payload.get("watermark_removal_or_circumvention_attempted") is not False:
            raise R2ForgeError("watermark evidence involved removal or circumvention")
        for key in ("scan_tool", "scan_tool_version", "scan_tool_sha256", "scanned_file_manifest_path", "scanned_file_manifest_sha256"):
            if not str(payload.get(key) or "").strip():
                raise R2ForgeError("watermark evidence lacks exact scan provenance")
        require_hash(payload["scan_tool_sha256"], "watermark scan tool")
        scan_tool = _bundle_file(bundle_dir, payload["scan_tool"], payload["scan_tool_sha256"], sealed, "watermark scan tool")
        scan_inventory = _bundle_file(
            bundle_dir,
            payload["scanned_file_manifest_path"],
            payload["scanned_file_manifest_sha256"],
            sealed,
            "watermark scanned-file manifest",
        )
        if not scan_tool.is_file():
            raise R2ForgeError("watermark scan tool evidence is missing")
        inventory_payload = read_json(scan_inventory)
        if inventory_payload.get("schema") != "qwen3_tts_watermark_scanned_file_manifest_v2" or inventory_payload.get("complete_inventory") is not True:
            raise R2ForgeError("watermark scanned-file inventory is incomplete")
        inventory_rows = inventory_payload.get("files")
        if not isinstance(inventory_rows, list) or not inventory_rows:
            raise R2ForgeError("watermark scanned-file inventory is empty")
        seen_inventory: set[str] = set()
        for inventory_row in inventory_rows:
            rel = str(inventory_row.get("path") or "") if isinstance(inventory_row, dict) else ""
            if not rel or rel in seen_inventory:
                raise R2ForgeError("watermark scanned-file row is invalid/duplicate")
            seen_inventory.add(rel)
            scanned_path = inside(project_root, rel, "watermark scanned source")
            verify_file(scanned_path, inventory_row.get("sha256"), f"watermark scanned source {rel}")
            if scanned_path.stat().st_size != inventory_row.get("bytes"):
                raise R2ForgeError("watermark scanned source size mismatch")
        if payload.get("findings") != []:
            raise R2ForgeError("watermark scan has unresolved findings")
        for key in ("voice_design_model_manifest_sha256", "base_model_manifest_sha256"):
            if payload.get(key) != bundle.get(key):
                raise R2ForgeError("watermark evidence model binding mismatch")
    if not required.issubset(found):
        raise R2ForgeError("watermark evidence files are missing")
    return HISTORICAL_WATERMARK_PREFLIGHT_STATUS


def validate_evaluation_corpus(
    *, project_root: Path, corpus: dict[str, Any], environment_spec: dict[str, Any]
) -> dict[str, Any]:
    if corpus.get("schema") != "qwen3_tts_voice_forge_evaluation_corpus_v2":
        raise R2ForgeError("evaluation corpus schema mismatch")
    if corpus.get("status") != "ACCEPTED_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS":
        raise R2ForgeError("real voice-collision corpus is not accepted")
    for key in (
        "embedding_engine", "embedding_engine_version", "embedding_model_path",
        "embedding_model_manifest_path", "embedding_model_manifest_sha256",
        "speaker_input_sample_rate_hz", "speaker_resampling_method",
    ):
        if not str(corpus.get(key) or "").strip():
            raise R2ForgeError("evaluation corpus lacks exact embedding provenance")
    require_hash(corpus["embedding_model_manifest_sha256"], "embedding model manifest")
    evaluator = environment_spec.get("speech_evaluators") or {}
    expected = {
        "embedding_engine": evaluator.get("speaker_embedding_engine"),
        "embedding_engine_version": evaluator.get("speaker_embedding_version"),
        "embedding_model_path": evaluator.get("speaker_model_path"),
        "embedding_model_manifest_path": evaluator.get("speaker_model_manifest_path"),
        "embedding_model_manifest_sha256": evaluator.get("speaker_model_manifest_sha256"),
        "speaker_input_sample_rate_hz": evaluator.get("speaker_input_sample_rate_hz"),
        "speaker_resampling_method": evaluator.get("speaker_resampling_method"),
    }
    if any(corpus.get(key) != value for key, value in expected.items()):
        raise R2ForgeError("evaluation corpus is not bound to the accepted speaker evaluator")
    model_dir = inside(project_root, corpus["embedding_model_path"], "corpus embedding model")
    verify_evaluator_model_manifest(
        project_root=project_root,
        model_dir=model_dir,
        manifest_path=inside(project_root, corpus["embedding_model_manifest_path"], "corpus embedding model manifest"),
        expected_hash=corpus["embedding_model_manifest_sha256"],
        engine=corpus["embedding_engine"],
        version=corpus["embedding_engine_version"],
    )
    voices = corpus.get("voices")
    if not isinstance(voices, list) or not voices:
        raise R2ForgeError("evaluation corpus has no resident/generic voices")
    kinds = set()
    verified = copy.deepcopy(corpus)
    verified_rows: list[dict[str, Any]] = []
    fixed_root = (project_root / EVALUATION_CORPUS_ROOT_REL).resolve()
    for row in voices:
        if not isinstance(row, dict) or row.get("kind") not in {"approved_resident", "known_generic"}:
            raise R2ForgeError("evaluation corpus voice row is invalid")
        kinds.add(row["kind"])
        if not SAFE_ID.fullmatch(str(row.get("voice_id") or "")):
            raise R2ForgeError("evaluation corpus voice ID is invalid")
        wav_path = inside(project_root, str(row.get("source_wav_path") or ""), "evaluation corpus WAV")
        embedding_path = inside(project_root, str(row.get("embedding_evidence_path") or ""), "evaluation corpus embedding evidence")
        for path, label in ((wav_path, "source WAV"), (embedding_path, "embedding evidence")):
            try:
                path.relative_to(fixed_root)
            except ValueError as exc:
                raise R2ForgeError(f"evaluation corpus {label} escaped the fixed corpus root") from exc
        verify_file(wav_path, row.get("source_wav_sha256"), "evaluation corpus source WAV")
        _samples, source_sample_rate = _wav_samples(wav_path)
        verify_file(embedding_path, row.get("embedding_evidence_sha256"), "evaluation corpus embedding evidence")
        evidence = read_json(embedding_path)
        if evidence.get("schema") != "qwen3_tts_voice_forge_corpus_embedding_evidence_v2":
            raise R2ForgeError("evaluation corpus embedding evidence schema mismatch")
        expected_evidence = {
            "voice_id": row["voice_id"],
            "source_wav_sha256": row["source_wav_sha256"],
            "embedding_engine": corpus["embedding_engine"],
            "embedding_engine_version": corpus["embedding_engine_version"],
            "embedding_model_manifest_sha256": corpus["embedding_model_manifest_sha256"],
            "source_sample_rate_hz": source_sample_rate,
            "speaker_input_sample_rate_hz": corpus["speaker_input_sample_rate_hz"],
            "speaker_resampling_method": corpus["speaker_resampling_method"],
            "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
        }
        if any(evidence.get(key) != value for key, value in expected_evidence.items()):
            raise R2ForgeError("evaluation corpus embedding evidence binding mismatch")
        vector = evidence.get("embedding")
        if not isinstance(vector, list) or len(vector) < 2 or not all(isinstance(x, (int, float)) for x in vector):
            raise R2ForgeError("evaluation corpus embedding is invalid")
        vector = [float(value) for value in vector]
        if not all(math.isfinite(value) for value in vector) or math.sqrt(sum(value * value for value in vector)) <= 0:
            raise R2ForgeError("evaluation corpus embedding is non-finite or zero norm")
        verified_row = copy.deepcopy(row)
        verified_row["verified_embedding"] = vector
        verified_rows.append(verified_row)
    if kinds != {"approved_resident", "known_generic"}:
        raise R2ForgeError("evaluation corpus must contain resident and generic controls")
    verified["voices"] = verified_rows
    verified["verified_against_exact_files"] = True
    return verified


def create_private_corpus_snapshot(
    *, project_root: Path, corpus: dict[str, Any], attempt_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot_root = attempt_dir / "private_collision_corpus_snapshot"
    snapshot_root.mkdir(parents=True, exist_ok=False)
    snapshot_corpus = copy.deepcopy(corpus)
    files: list[dict[str, Any]] = []
    for row in snapshot_corpus["voices"]:
        voice_root = snapshot_root / row["voice_id"]
        voice_root.mkdir()
        for path_key, hash_key, name in (
            ("source_wav_path", "source_wav_sha256", "source.wav"),
            ("embedding_evidence_path", "embedding_evidence_sha256", "embedding_evidence.json"),
        ):
            source = inside(project_root, row[path_key], f"collision corpus {path_key}")
            verify_file(source, row[hash_key], f"collision corpus {path_key}")
            destination = voice_root / name
            with source.open("rb") as input_handle, destination.open("xb") as output_handle:
                shutil.copyfileobj(input_handle, output_handle, 1024 * 1024)
                output_handle.flush()
                os.fsync(output_handle.fileno())
            verify_file(destination, row[hash_key], f"collision corpus snapshot {path_key}")
            os.chmod(destination, 0o444)
            row[path_key] = relative(destination, project_root)
            files.append({
                "voice_id": row["voice_id"], "kind": path_key,
                "path": relative(destination, attempt_dir),
                "bytes": destination.stat().st_size, "sha256": row[hash_key],
            })
    manifest = {
        "schema": "qwen3_tts_private_collision_corpus_snapshot_v2",
        "exclusive_byte_copies": True,
        "embedding_engine": corpus["embedding_engine"],
        "embedding_engine_version": corpus["embedding_engine_version"],
        "embedding_model_manifest_sha256": corpus["embedding_model_manifest_sha256"],
        "speaker_input_sample_rate_hz": corpus["speaker_input_sample_rate_hz"],
        "speaker_resampling_method": corpus["speaker_resampling_method"],
        "files": files,
    }
    write_new_json(snapshot_root / "PRIVATE_CORPUS_SNAPSHOT_MANIFEST.json", manifest)
    return snapshot_corpus, manifest


def verify_private_corpus_snapshot(*, attempt_dir: Path, manifest: dict[str, Any]) -> None:
    snapshot_root = attempt_dir / "private_collision_corpus_snapshot"
    declared: set[str] = set()
    for row in manifest.get("files", []):
        path = inside(attempt_dir, row.get("path", ""), "collision corpus snapshot")
        verify_file(path, row.get("sha256"), "collision corpus snapshot")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError("collision corpus snapshot size drift")
        declared.add(relative(path, snapshot_root))
    actual = {
        relative(path, snapshot_root)
        for path in snapshot_root.rglob("*")
        if path.is_file() and path.name != "PRIVATE_CORPUS_SNAPSHOT_MANIFEST.json"
    }
    if not declared or actual != declared:
        raise R2ForgeError("collision corpus snapshot inventory drift")


def validate_environment_spec_static(
    spec: dict[str, Any], *, require_ready: bool = True, project_root: Path | None = None
) -> None:
    if spec.get("environment_id") != "qwen3_tts_voice_forge_isolated_windows_blackwell_v2":
        raise R2ForgeError("environment identity mismatch")
    if spec.get("network_boundary") != NETWORK_BOUNDARY:
        raise R2ForgeError("network boundary is not truthfully offline-flags-only")
    if require_ready and spec.get("status") != "ACCEPTED_READY_FOR_ONE_BOUNDED_RUN":
        raise R2ForgeError("isolated R2 environment is not accepted ready")
    distributions = spec.get("distributions") or {}
    if {key: distributions.get(key, {}).get("version") for key in ("qwen-tts", "transformers", "accelerate")} != {
        "qwen-tts": "0.1.1",
        "transformers": "4.57.3",
        "accelerate": "1.12.0",
    }:
        raise R2ForgeError("core package pins changed")
    if require_ready:
        python = spec.get("python") or {}
        for key in ("version", "executable_path", "executable_sha256"):
            if not str(python.get(key) or "").strip():
                raise R2ForgeError("Python attestation is incomplete")
        require_hash(python["executable_sha256"], "Python executable")
        mandatory_packages = {
            "qwen-tts", "transformers", "accelerate", "torch", "torchaudio",
            "faster-whisper", "speechbrain",
        }
        if not mandatory_packages.issubset(distributions):
            raise R2ForgeError("mandatory runtime distributions are missing")
        for package, row in distributions.items():
            if not isinstance(row, dict):
                raise R2ForgeError(f"{package} distribution row is invalid")
            for key in ("version", "record_path", "record_sha256"):
                if not str(row.get(key) or "").strip():
                    raise R2ForgeError(f"{package} distribution/RECORD attestation is incomplete")
            require_hash(row["record_sha256"], f"{package} RECORD")
        site_inventory = spec.get("site_packages_inventory") or {}
        for key in ("root", "manifest_path", "manifest_sha256"):
            if not str(site_inventory.get(key) or "").strip():
                raise R2ForgeError("complete site-packages inventory attestation is incomplete")
        require_hash(site_inventory["manifest_sha256"], "site-packages inventory manifest")
        if (
            site_inventory.get("status") != "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY"
            or site_inventory.get("complete_file_inventory") is not True
            or site_inventory.get("all_distributions_and_loose_files_declared") is not True
        ):
            raise R2ForgeError("complete site-packages inventory is not accepted")
        for package in ("torch", "torchaudio"):
            row = distributions[package]
            for key in ("wheel_filename", "wheel_sha256", "wheel_evidence_path"):
                if not str(row.get(key) or "").strip():
                    raise R2ForgeError(f"{package} wheel attestation is incomplete")
            require_hash(row["wheel_sha256"], f"{package} wheel")
        evaluators = spec.get("speech_evaluators") or {}
        if evaluators.get("status") != "ACCEPTED_EXACT_LOCAL_ASR_SPEECH_AND_SPEAKER_EMBEDDING":
            raise R2ForgeError("real local speech evaluators are not accepted")
        for key in (
            "asr_engine", "asr_version", "asr_model_path", "asr_model_manifest_path", "asr_model_manifest_sha256",
            "speaker_embedding_engine", "speaker_embedding_version", "speaker_model_path",
            "speaker_model_manifest_path", "speaker_model_manifest_sha256",
            "speaker_input_sample_rate_hz", "speaker_resampling_method",
            "speech_classifier_engine", "speech_classifier_version", "speech_classifier_adapter_path",
            "speech_classifier_adapter_sha256", "speech_classifier_model_path",
            "speech_classifier_model_manifest_path", "speech_classifier_model_manifest_sha256",
        ):
            if not str(evaluators.get(key) or "").strip():
                raise R2ForgeError("real local speech evaluator provenance is incomplete")
        require_hash(evaluators["asr_model_manifest_sha256"], "ASR model manifest")
        require_hash(evaluators["speaker_model_manifest_sha256"], "speaker model manifest")
        require_hash(evaluators["speech_classifier_adapter_sha256"], "speech classifier adapter")
        require_hash(evaluators["speech_classifier_model_manifest_sha256"], "speech classifier model manifest")
        if evaluators["speaker_input_sample_rate_hz"] != 16000:
            raise R2ForgeError("speaker evaluator input sample rate is not the accepted 16 kHz")
        if evaluators["speaker_resampling_method"] != "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1":
            raise R2ForgeError("speaker evaluator resampling method mismatch")
        identity = spec.get("identity_analyzer") or {}
        if identity.get("status") != "ACCEPTED_EXACT_LOCAL_NER_AND_IMITATION_ANALYZER":
            raise R2ForgeError("real local identity analyzer is not accepted")
        for key in ("engine", "version", "adapter_path", "adapter_sha256", "model_path", "model_manifest_path", "model_manifest_sha256"):
            if not str(identity.get(key) or "").strip():
                raise R2ForgeError("real local identity analyzer provenance is incomplete")
        require_hash(identity["adapter_sha256"], "identity analyzer adapter")
        require_hash(identity["model_manifest_sha256"], "identity analyzer model manifest")
        validate_environment_attestation_layout(spec, PROJECT_ROOT if project_root is None else project_root)


def load_trusted_bundle(project_root: Path, bundle_id: str, *, require_ready_environment: bool = True) -> TrustedBundle:
    project_root = project_root.resolve()
    if not SAFE_ID.fullmatch(bundle_id):
        raise R2ForgeError("bundle_id is not a safe opaque ID")
    contract_path = (project_root / CONTRACT_REL).resolve()
    contract = read_json(contract_path)
    if contract.get("contract_id") != CONTRACT_ID or contract.get("version") != 2:
        raise R2ForgeError("R2 contract identity mismatch")
    registry = read_json((project_root / REGISTRY_REL).resolve())
    if registry.get("schema") != "temporaryai_qwen3_tts_voice_forge_bundle_registry_v2":
        raise R2ForgeError("trusted bundle registry schema mismatch")
    entries = [row for row in registry.get("append_only_entries", []) if isinstance(row, dict) and row.get("bundle_id") == bundle_id]
    if len(entries) != 1 or entries[0].get("status") != "OWNER_AUTHORIZED_SINGLE_USE":
        raise R2ForgeError("bundle has no unique active trusted registry entry")
    entry = entries[0]
    bundle_root = (project_root / BUNDLE_ROOT_REL).resolve()
    bundle_dir = inside(bundle_root, bundle_id, "trusted bundle")
    seal_path = bundle_dir / "BUNDLE_SEAL.json"
    verify_file(seal_path, entry.get("bundle_seal_sha256"), "trusted bundle seal")
    seal = read_json(seal_path)
    if seal.get("bundle_id") != bundle_id:
        raise R2ForgeError("bundle seal ID mismatch")
    sealed = _sealed_bundle_files(bundle_dir, seal)
    bundle_path = _bundle_file(
        bundle_dir, "acceptance_bundle.json", seal.get("acceptance_bundle_sha256"), sealed, "acceptance bundle"
    )
    bundle = read_json(bundle_path)
    if bundle.get("schema") != "qwen3_tts_original_voice_forge_acceptance_bundle_v2" or bundle.get("status") != "OWNER_AUTHORIZED_SINGLE_USE":
        raise R2ForgeError("acceptance bundle is not active")
    if bundle.get("bundle_id") != bundle_id or bundle.get("queue_kind") != "TEMPORARYAI_ORIGINAL_VOICE_FORGE_PRIVATE_ACCEPTANCE_V2":
        raise R2ForgeError("acceptance bundle identity/queue mismatch")
    if sha256_text(str(bundle.get("single_use_nonce") or "")) != require_hash(bundle.get("single_use_nonce_sha256"), "nonce"):
        raise R2ForgeError("single-use nonce hash mismatch")
    if compute_queue_binding(bundle) != require_hash(bundle.get("queue_binding_sha256"), "queue binding"):
        raise R2ForgeError("queue binding mismatch")
    for key in (
        "candidate_id", "ai_type", "opaque_voice_id", "single_use_nonce_sha256", "queue_binding_sha256",
        "canonical_profile_sha256", "canonical_creation_request_sha256", "job_sha256", "owner_authorization_sha256",
        "identity_clearance_manifest_sha256", "watermark_evidence_manifest_sha256", "evaluation_corpus_sha256",
        "voice_design_model_manifest_sha256", "base_model_manifest_sha256", "environment_spec_sha256",
    ):
        if entry.get(key) != bundle.get(key):
            raise R2ForgeError(f"trusted registry {key} mismatch")
    profile, creation = validate_canonical_candidate(project_root, bundle)
    job_path = _bundle_file(bundle_dir, bundle.get("job_path"), bundle.get("job_sha256"), sealed, "job")
    job = read_json(job_path)
    validate_job(job)
    owner_path = _bundle_file(
        bundle_dir, bundle.get("owner_authorization_path"), bundle.get("owner_authorization_sha256"), sealed, "owner authorization"
    )
    owner = read_json(owner_path)
    validate_owner_authorization(owner, bundle)
    identity_path = _bundle_file(
        bundle_dir,
        bundle.get("identity_clearance_manifest_path"),
        bundle.get("identity_clearance_manifest_sha256"),
        sealed,
        "identity clearance manifest",
    )
    identity = read_json(identity_path)
    validate_identity_clearance(bundle_dir=bundle_dir, manifest=identity, sealed=sealed, job=job, bundle=bundle)
    watermark_path = _bundle_file(
        bundle_dir,
        bundle.get("watermark_evidence_manifest_path"),
        bundle.get("watermark_evidence_manifest_sha256"),
        sealed,
        "watermark evidence manifest",
    )
    watermark = read_json(watermark_path)
    validate_watermark_preflight(project_root=project_root, bundle_dir=bundle_dir, manifest=watermark, sealed=sealed, bundle=bundle)
    corpus_path = inside(project_root, str(bundle.get("evaluation_corpus_path") or ""), "evaluation corpus")
    if corpus_path != (project_root / EVALUATION_CORPUS_REL).resolve():
        raise R2ForgeError("evaluation corpus is not the fixed trusted corpus")
    verify_file(corpus_path, bundle.get("evaluation_corpus_sha256"), "evaluation corpus")
    environment_path = (project_root / ENVIRONMENT_REL).resolve()
    verify_file(environment_path, bundle.get("environment_spec_sha256"), "bundle-bound environment spec")
    environment = read_json(environment_path)
    validate_environment_spec_static(
        environment,
        require_ready=require_ready_environment,
        project_root=project_root,
    )
    corpus = validate_evaluation_corpus(
        project_root=project_root,
        corpus=read_json(corpus_path),
        environment_spec=environment,
    )
    return TrustedBundle(
        project_root, bundle_dir, bundle, job, profile, creation, owner, identity, watermark, corpus, contract, environment, entry
    )


def _model_manifest(project_root: Path, model_dir: Path, manifest_path: Path, expected_hash: Any, repository: str) -> dict[str, Any]:
    verify_file(manifest_path, expected_hash, "model manifest")
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "qwen3_tts_local_model_file_manifest_v1" or manifest.get("repository") != repository:
        raise R2ForgeError("model manifest schema/repository mismatch")
    if manifest.get("complete_file_inventory") is not True or not str(manifest.get("revision") or ""):
        raise R2ForgeError("model manifest is incomplete")
    if manifest_path.parent.resolve() != model_dir.resolve():
        raise R2ForgeError("model manifest is not inside the exact model directory")
    declared: set[str] = set()
    for row in manifest.get("files", []):
        rel = str(row.get("path") or "") if isinstance(row, dict) else ""
        if not rel or rel in declared:
            raise R2ForgeError("model manifest has an invalid/duplicate file")
        declared.add(rel)
        path = inside(model_dir, rel, "model file")
        verify_file(path, row.get("sha256"), f"model file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError(f"model file size mismatch: {rel}")
    actual = {
        relative(path, model_dir)
        for path in model_dir.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    if actual != declared:
        raise R2ForgeError("model manifest does not match the complete source directory")
    return manifest


def verify_evaluator_model_manifest(
    *, project_root: Path, model_dir: Path, manifest_path: Path,
    expected_hash: Any, engine: str, version: str,
) -> dict[str, Any]:
    verify_file(manifest_path, expected_hash, "evaluator model manifest")
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "qwen3_tts_local_evaluator_model_manifest_v2":
        raise R2ForgeError("evaluator model manifest schema mismatch")
    if manifest.get("engine") != engine or manifest.get("version") != version:
        raise R2ForgeError("evaluator model engine/version mismatch")
    if manifest.get("complete_file_inventory") is not True or manifest_path.parent.resolve() != model_dir.resolve():
        raise R2ForgeError("evaluator model manifest is incomplete or misplaced")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise R2ForgeError("evaluator model manifest has no exact files")
    declared: set[str] = set()
    for row in rows:
        rel = str(row.get("path") or "") if isinstance(row, dict) else ""
        if not rel or rel in declared:
            raise R2ForgeError("evaluator model inventory has an invalid/duplicate file")
        declared.add(rel)
        path = inside(model_dir, rel, "evaluator model file")
        verify_file(path, row.get("sha256"), f"evaluator model file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError("evaluator model file size mismatch")
    actual = {
        relative(path, model_dir)
        for path in model_dir.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    if actual != declared:
        raise R2ForgeError("evaluator model manifest does not match its complete directory")
    return manifest


def create_private_evaluator_snapshots(
    *, project_root: Path, spec: dict[str, Any], attempt_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Byte-copy every evaluator model/adapter before any evaluator executes.

    The returned environment copy points only at the attempt-local snapshots.
    The accepted source environment remains immutable and no evaluator is
    imported while the copies are made.
    """

    snapshot_spec = copy.deepcopy(spec)
    evaluator_root = (project_root / EVALUATOR_ROOT_REL).resolve()
    roles = (
        ("identity", "identity_analyzer", "model_path", "model_manifest_path", "model_manifest_sha256", "engine", "version", "adapter_path", "adapter_sha256"),
        ("asr", "speech_evaluators", "asr_model_path", "asr_model_manifest_path", "asr_model_manifest_sha256", "asr_engine", "asr_version", None, None),
        ("speaker", "speech_evaluators", "speaker_model_path", "speaker_model_manifest_path", "speaker_model_manifest_sha256", "speaker_embedding_engine", "speaker_embedding_version", None, None),
        ("speech_classifier", "speech_evaluators", "speech_classifier_model_path", "speech_classifier_model_manifest_path", "speech_classifier_model_manifest_sha256", "speech_classifier_engine", "speech_classifier_version", "speech_classifier_adapter_path", "speech_classifier_adapter_sha256"),
    )
    snapshots: dict[str, Any] = {}
    for role, section_name, model_key, manifest_key, hash_key, engine_key, version_key, adapter_key, adapter_hash_key in roles:
        source_section = spec[section_name]
        source_model = inside(project_root, source_section[model_key], f"{role} evaluator model")
        source_manifest = inside(project_root, source_section[manifest_key], f"{role} evaluator manifest")
        for source, label in ((source_model, "model"), (source_manifest, "manifest")):
            try:
                source.relative_to(evaluator_root)
            except ValueError as exc:
                raise R2ForgeError(f"{role} evaluator {label} escaped the fixed evaluator root") from exc
        model_manifest = verify_evaluator_model_manifest(
            project_root=project_root,
            model_dir=source_model,
            manifest_path=source_manifest,
            expected_hash=source_section[hash_key],
            engine=source_section[engine_key],
            version=source_section[version_key],
        )
        role_root = attempt_dir / "private_evaluator_snapshots" / role
        destination_model = role_root / "model"
        destination_model.mkdir(parents=True, exist_ok=False)
        copied_rows: list[dict[str, Any]] = []
        for row in model_manifest["files"]:
            rel = str(row["path"])
            source_file = inside(source_model, rel, f"{role} evaluator source file")
            destination_file = inside(destination_model, rel, f"{role} evaluator snapshot file")
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            with source_file.open("rb") as input_handle, destination_file.open("xb") as output_handle:
                shutil.copyfileobj(input_handle, output_handle, 1024 * 1024)
                output_handle.flush()
                os.fsync(output_handle.fileno())
            verify_file(destination_file, row["sha256"], f"{role} evaluator snapshot file {rel}")
            os.chmod(destination_file, 0o444)
            copied_rows.append({"path": rel, "bytes": destination_file.stat().st_size, "sha256": row["sha256"]})
        destination_manifest = destination_model / source_manifest.name
        with source_manifest.open("rb") as input_handle, destination_manifest.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle, 1024 * 1024)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        verify_file(destination_manifest, source_section[hash_key], f"{role} evaluator snapshot manifest")
        os.chmod(destination_manifest, 0o444)
        snapshot_section = snapshot_spec[section_name]
        snapshot_section[model_key] = relative(destination_model, project_root)
        snapshot_section[manifest_key] = relative(destination_manifest, project_root)
        adapter_row = None
        if adapter_key and adapter_hash_key:
            source_adapter = inside(project_root, source_section[adapter_key], f"{role} evaluator adapter")
            try:
                source_adapter.relative_to(evaluator_root)
            except ValueError as exc:
                raise R2ForgeError(f"{role} evaluator adapter escaped the fixed evaluator root") from exc
            verify_file(source_adapter, source_section[adapter_hash_key], f"{role} evaluator adapter")
            destination_adapter = role_root / "adapter.py"
            with source_adapter.open("rb") as input_handle, destination_adapter.open("xb") as output_handle:
                shutil.copyfileobj(input_handle, output_handle, 1024 * 1024)
                output_handle.flush()
                os.fsync(output_handle.fileno())
            verify_file(destination_adapter, source_section[adapter_hash_key], f"{role} evaluator snapshot adapter")
            os.chmod(destination_adapter, 0o444)
            snapshot_section[adapter_key] = relative(destination_adapter, project_root)
            adapter_row = {
                "path": relative(destination_adapter, attempt_dir),
                "bytes": destination_adapter.stat().st_size,
                "sha256": source_section[adapter_hash_key],
            }
        snapshot_manifest = {
            "schema": "qwen3_tts_private_evaluator_snapshot_v2",
            "role": role,
            "engine": source_section[engine_key],
            "version": source_section[version_key],
            "source_model_manifest_sha256": source_section[hash_key],
            "exclusive_byte_copies": True,
            "model_files": copied_rows,
            "model_manifest": {
                "path": relative(destination_manifest, attempt_dir),
                "bytes": destination_manifest.stat().st_size,
                "sha256": source_section[hash_key],
            },
            "adapter": adapter_row,
        }
        snapshot_manifest_path = role_root / "PRIVATE_EVALUATOR_SNAPSHOT_MANIFEST.json"
        write_new_json(snapshot_manifest_path, snapshot_manifest)
        snapshots[role] = snapshot_manifest
    return snapshot_spec, snapshots


def verify_private_evaluator_snapshots(*, attempt_dir: Path, snapshots: dict[str, Any]) -> None:
    for role, manifest in snapshots.items():
        role_root = attempt_dir / "private_evaluator_snapshots" / role
        declared: set[str] = set()
        for row in manifest.get("model_files", []):
            path = inside(role_root / "model", row.get("path", ""), f"{role} evaluator snapshot")
            verify_file(path, row.get("sha256"), f"{role} evaluator snapshot file")
            if path.stat().st_size != row.get("bytes"):
                raise R2ForgeError(f"{role} evaluator snapshot size drift")
            declared.add(relative(path, role_root))
        for row in (manifest.get("model_manifest"), manifest.get("adapter")):
            if row:
                path = inside(attempt_dir, row.get("path", ""), f"{role} evaluator snapshot evidence")
                verify_file(path, row.get("sha256"), f"{role} evaluator snapshot evidence")
                if path.stat().st_size != row.get("bytes"):
                    raise R2ForgeError(f"{role} evaluator snapshot evidence size drift")
                declared.add(relative(path, role_root))
        actual = {
            relative(path, role_root)
            for path in role_root.rglob("*")
            if path.is_file() and path.name != "PRIVATE_EVALUATOR_SNAPSHOT_MANIFEST.json"
        }
        if actual != declared:
            raise R2ForgeError(f"{role} evaluator snapshot inventory drift")


def run_live_watermark_documentation_scan(
    *, project_root: Path, attempt_dir: Path, model_snapshots: list[Path],
    evaluator_snapshots: dict[str, Any], environment_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Run the controlling exact-revision documentation/source scan.

    This is deliberately a disclosure/documentation gate, not a watermark
    detector and never a removal mechanism.  It can support only the initial
    NO_DOCUMENTED status.  A stronger status requires a separate detector and
    append-only evidence after generation.
    """

    inventory: dict[str, Path] = {}
    for snapshot in model_snapshots:
        for path in snapshot.rglob("*"):
            if path.is_file():
                inventory[relative(path, project_root)] = path
    for role in evaluator_snapshots:
        role_root = attempt_dir / "private_evaluator_snapshots" / role
        for path in role_root.rglob("*"):
            if path.is_file():
                inventory[relative(path, project_root)] = path
    site_inventory = environment_evidence.get("site_packages_inventory") or {}
    if (
        site_inventory.get("complete_file_inventory") is not True
        or site_inventory.get("all_transitive_distributions_declared") is not True
        or site_inventory.get("all_loose_files_declared") is not True
    ):
        raise R2ForgeError("live watermark scan lacks the complete isolated import surface")
    for row in site_inventory.get("files", []):
        path = inside(project_root, row.get("path", ""), "live watermark site-packages file")
        verify_file(path, row.get("sha256"), "live watermark site-packages file")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError("live watermark site-packages file size mismatch")
        inventory[relative(path, project_root)] = path
    site_manifest = inside(
        project_root,
        site_inventory.get("manifest_path", ""),
        "live watermark site-packages manifest",
    )
    verify_file(
        site_manifest,
        site_inventory.get("manifest_sha256"),
        "live watermark site-packages manifest",
    )
    inventory[relative(site_manifest, project_root)] = site_manifest
    runtime_sources = (
        (project_root / WORKER_REL).resolve(),
        (project_root / RUNNER_REL).resolve(),
        (project_root / CONTRACT_REL).resolve(),
        (project_root / ENVIRONMENT_REL).resolve(),
        (project_root / HARNESS_MANIFEST_REL).resolve(),
        inside(project_root, environment_evidence.get("python_executable_path", ""), "watermark scan Python executable"),
    )
    for path in runtime_sources:
        if not path.is_file():
            raise R2ForgeError("live watermark runtime-source scope is incomplete")
        inventory[relative(path, project_root)] = path
    wheel_archives = environment_evidence.get("wheel_archives") or {}
    if set(wheel_archives) != {"torch", "torchaudio"}:
        raise R2ForgeError("live watermark scan lacks the exact Torch wheel evidence")
    for package, row in wheel_archives.items():
        path = inside(project_root, row.get("path", ""), f"{package} watermark wheel evidence")
        verify_file(path, row.get("sha256"), f"{package} watermark wheel evidence")
        inventory[relative(path, project_root)] = path
    if not inventory:
        raise R2ForgeError("live watermark documentation scan had no exact files")
    text_suffixes = {".py", ".json", ".txt", ".md", ".rst", ".toml", ".yaml", ".yml", ".cfg", ".ini"}
    implementation_verbs = r"(?:embed|encode|inject|apply|insert)"
    declaration_verbs = (
        r"(?:uses?|includes?|adds?|contains?|ships?|produces?|generates?|"
        r"applies?|injects?|embeds?)"
    )
    watermark_term = r"(?:audio[_ .-]*)?watermark(?:ing)?"
    implementation_patterns = (
        re.compile(
            r"(?i)\b(?:def\s+)?" + implementation_verbs
            + r"[_ .-]*" + watermark_term + r"\s*\("
        ),
        re.compile(
            r"(?i)\b" + declaration_verbs + r"\b.{0,80}\b"
            + watermark_term + r"\b"
        ),
    )
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for rel, path in sorted(inventory.items()):
        row = {"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if path.suffix.lower() in text_suffixes and path.stat().st_size <= 16 * 1024 * 1024:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeError:
                row.update({"text_scanned": False, "skip_reason": "NOT_UTF8_TEXT"})
            else:
                matches = sorted({
                    match.group(0)
                    for pattern in implementation_patterns
                    for match in pattern.finditer(content)
                })
                row.update({"text_scanned": True, "matched_intentional_audio_watermark_markers": matches})
                if matches:
                    findings.append({"path": rel, "markers": matches})
        else:
            row.update({"text_scanned": False, "skip_reason": "BINARY_OR_OVERSIZE_DOCUMENTARY_SCAN"})
        rows.append(row)
    report = {
        "schema": "qwen3_tts_live_watermark_documentation_scan_v2",
        "status": (
            "FAIL_INTENTIONAL_AUDIO_WATERMARK_IMPLEMENTATION_MARKER_FOUND"
            if findings else "PASS_NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK_STAGE_FOUND"
        ),
        "runtime_watermark_status_ceiling": INITIAL_WATERMARK_STATUS,
        "stronger_detector_status_granted": False,
        "watermark_removal_or_circumvention_attempted": False,
        "scanner": "BUILT_IN_HASHED_R2_WORKER_DOCUMENTATION_SCAN",
        "scanner_worker_sha256": sha256_file(project_root / WORKER_REL),
        "complete_exact_file_inventory": False,
        "scan_scope_exhaustively_declared": True,
        "all_declared_rows_hash_verified": True,
        "bounded_execution_dependency_inventory_complete": False,
        "claim_scope": (
            "HASH_BOUND_APPLICATION_RUNTIME_SOURCES_COMPLETE_ISOLATED_SITE_PACKAGES_"
            "EXACT_TORCH_WHEEL_EVIDENCE_MODEL_EVALUATOR_AND_CORPUS_SNAPSHOTS"
        ),
        "explicit_exclusions": [
            "BINARY_AND_OVERSIZE_MEMBERS_ARE_HASH_INVENTORIED_BUT_NOT_UTF8_PATTERN_SCANNED",
            "BASE_PYTHON_STANDARD_LIBRARY_SOURCE_IS_OUTSIDE_THE_ISOLATED_PROJECT_REVISION_SCOPE",
            "WINDOWS_OS_AND_DRIVER_FILES_ARE_OUTSIDE_THE_APPLICATION_REVISION_CLAIM",
            "UNKNOWN_POST_GENERATION_SIGNAL_DETECTION_REQUIRES_SEPARATE_AUDIT",
        ],
        "files": rows,
        "findings": findings,
    }
    report_path = attempt_dir / "live_watermark_documentation_scan_v2.json"
    write_new_json(report_path, report)
    if findings:
        raise R2ForgeError("live exact-revision scan found an intentional audio-watermark implementation marker")
    return {**report, "report_sha256": sha256_file(report_path)}


def create_private_model_snapshot(
    *, project_root: Path, bundle: dict[str, Any], attempt_dir: Path, role: str
) -> tuple[Path, dict[str, Any]]:
    if role == "voice_design":
        directory_key, manifest_key, hash_key = (
            "voice_design_model_directory", "voice_design_model_manifest_path", "voice_design_model_manifest_sha256"
        )
        repository = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    elif role == "base":
        directory_key, manifest_key, hash_key = (
            "base_model_directory", "base_model_manifest_path", "base_model_manifest_sha256"
        )
        repository = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
    else:
        raise R2ForgeError("unknown snapshot role")
    source = inside(project_root, bundle[directory_key], f"{role} source")
    model_root = (project_root / "Voice/models/qwen3_tts").resolve()
    try:
        source.relative_to(model_root)
    except ValueError as exc:
        raise R2ForgeError("model source escaped the fixed local model root") from exc
    manifest_path = inside(project_root, bundle[manifest_key], f"{role} manifest")
    manifest = _model_manifest(project_root, source, manifest_path, bundle[hash_key], repository)
    snapshot = attempt_dir / "private_model_snapshots" / role
    snapshot.mkdir(parents=True, exist_ok=False)
    copied: list[dict[str, Any]] = []
    for row in manifest["files"]:
        rel = str(row["path"])
        src = inside(source, rel, "source model file")
        dst = inside(snapshot, rel, "private snapshot file")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as input_handle, dst.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle, 1024 * 1024)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        verify_file(dst, row["sha256"], f"private snapshot file {rel}")
        os.chmod(dst, 0o444)
        copied.append({"path": rel, "bytes": dst.stat().st_size, "sha256": row["sha256"]})
    snapshot_manifest = {
        "schema": "qwen3_tts_private_model_snapshot_v2",
        "role": role,
        "repository": repository,
        "revision": manifest["revision"],
        "source_manifest_sha256": bundle[hash_key],
        "exclusive_byte_copies": True,
        "files": copied,
    }
    snapshot_manifest_path = snapshot / "PRIVATE_SNAPSHOT_MANIFEST.json"
    write_new_json(snapshot_manifest_path, snapshot_manifest)
    return snapshot, snapshot_manifest


def verify_private_snapshot(snapshot: Path, manifest: dict[str, Any]) -> None:
    declared = set()
    for row in manifest.get("files", []):
        rel = str(row.get("path") or "")
        declared.add(rel)
        path = inside(snapshot, rel, "private snapshot verification file")
        verify_file(path, row.get("sha256"), f"private snapshot verification {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError("private snapshot file size drift")
    actual = {
        relative(path, snapshot)
        for path in snapshot.rglob("*")
        if path.is_file() and path.name != "PRIVATE_SNAPSHOT_MANIFEST.json"
    }
    if actual != declared:
        raise R2ForgeError("private model snapshot inventory drift")


def normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def word_error_rate(expected: str, actual: str) -> float:
    reference = normalize_words(expected)
    hypothesis = normalize_words(actual)
    if not reference:
        return 0.0 if not hypothesis else 1.0
    previous = list(range(len(hypothesis) + 1))
    for i, expected_word in enumerate(reference, 1):
        current = [i]
        for j, actual_word in enumerate(hypothesis, 1):
            current.append(min(current[j - 1] + 1, previous[j] + 1, previous[j - 1] + (expected_word != actual_word)))
        previous = current
    return previous[-1] / len(reference)


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise R2ForgeError("speaker embedding dimensions do not match")
    if not all(math.isfinite(value) for value in left + right):
        raise R2ForgeError("speaker embedding contains non-finite values")
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    if denominator <= 0:
        raise R2ForgeError("speaker embedding has zero norm")
    return sum(a * b for a, b in zip(left, right)) / denominator


def speaker_embedding_artifact_path(
    *, source_wav_path: Path, project_root: Path, target_sample_rate_hz: int
) -> Path:
    """Return an append-only attempt artifact path outside immutable snapshots."""

    source = source_wav_path.resolve()
    attempt_root: Path | None = None
    for parent in (source.parent, *source.parents):
        if re.fullmatch(r"attempt_[0-9]{2,3}", parent.name):
            attempt_root = parent
            break
    if attempt_root is None:
        raise R2ForgeError("speaker embedding source is outside an append-only attempt")
    expected_parent = (project_root / OUTPUT_ROOT_REL).resolve()
    try:
        attempt_root.relative_to(expected_parent)
    except ValueError as exc:
        raise R2ForgeError("speaker embedding attempt escaped the fixed private output root") from exc
    source_binding = sha256_text(relative(source, project_root))[:16]
    source_digest = sha256_file(source)
    return (
        attempt_root
        / "speaker_embedding_inputs"
        / f"{source_digest}_{source_binding}_{target_sample_rate_hz}hz_pcm16.wav"
    )


def validate_embedding_input_artifact(
    *, evidence: dict[str, Any], source_wav_path: Path | None,
    source_wav_sha256: str, project_root: Path,
    speaker_input_sample_rate_hz: int, speaker_resampling_method: str,
) -> dict[str, Any]:
    if evidence.get("source_wav_sha256") != source_wav_sha256:
        raise R2ForgeError("speaker embedding source-WAV hash mismatch")
    source_rate = int(evidence.get("source_sample_rate_hz") or 0)
    if source_rate <= 0:
        raise R2ForgeError("speaker embedding source sample rate is missing")
    if source_wav_path is not None:
        _source_samples, actual_source_rate = _wav_samples(source_wav_path)
        if actual_source_rate != source_rate or sha256_file(source_wav_path) != source_wav_sha256:
            raise R2ForgeError("speaker embedding source WAV/rate binding mismatch")
    if evidence.get("speaker_input_sample_rate_hz") != speaker_input_sample_rate_hz:
        raise R2ForgeError("speaker embedding normalized sample rate mismatch")
    if evidence.get("speaker_resampling_method") != speaker_resampling_method:
        raise R2ForgeError("speaker embedding resampling method mismatch")
    if evidence.get("resampled_for_embedding") is not (source_rate != speaker_input_sample_rate_hz):
        raise R2ForgeError("speaker embedding resampling decision mismatch")
    if evidence.get("embedding_computed_from_reloaded_exact_pcm16_artifact") is not True:
        raise R2ForgeError("speaker embedding was not computed from its exact saved artifact")
    normalized_path = inside(
        project_root,
        evidence.get("embedding_input_wav_path", ""),
        "speaker embedding normalized WAV",
    )
    verify_file(
        normalized_path,
        evidence.get("embedding_input_wav_sha256"),
        "speaker embedding normalized WAV",
    )
    if normalized_path.stat().st_size != evidence.get("embedding_input_wav_bytes"):
        raise R2ForgeError("speaker embedding normalized WAV size mismatch")
    _normalized_samples, normalized_rate = _wav_samples(normalized_path)
    if normalized_rate != speaker_input_sample_rate_hz:
        raise R2ForgeError("speaker embedding normalized artifact has the wrong rate")
    return {
        "source_sample_rate_hz": source_rate,
        "speaker_input_sample_rate_hz": speaker_input_sample_rate_hz,
        "resampled_for_embedding": source_rate != speaker_input_sample_rate_hz,
        "embedding_input_wav_path": relative(normalized_path, project_root),
        "embedding_input_wav_sha256": sha256_file(normalized_path),
    }


def recompute_collision_corpus(
    *, evaluator: EvaluatorProtocol, corpus: dict[str, Any], project_root: Path
) -> dict[str, Any]:
    """Recompute every accepted control embedding from its exact source WAV."""

    result = copy.deepcopy(corpus)
    for row in result["voices"]:
        wav_path = inside(project_root, row["source_wav_path"], "collision corpus source WAV")
        evidence = evaluator.speaker_embedding(wav_path)
        expected = {
            "embedding_mode": "REAL_LOCAL_SPEAKER_EMBEDDING",
            "embedding_engine": corpus["embedding_engine"],
            "embedding_version": corpus["embedding_engine_version"],
            "embedding_model_manifest_sha256": corpus["embedding_model_manifest_sha256"],
            "source_wav_sha256": row["source_wav_sha256"],
            "speaker_input_sample_rate_hz": corpus["speaker_input_sample_rate_hz"],
            "speaker_resampling_method": corpus["speaker_resampling_method"],
        }
        if any(evidence.get(key) != value for key, value in expected.items()):
            raise R2ForgeError("recomputed collision embedding provenance/input mismatch")
        recomputed = [float(value) for value in evidence.get("speaker_embedding", [])]
        artifact = validate_embedding_input_artifact(
            evidence=evidence,
            source_wav_path=wav_path,
            source_wav_sha256=row["source_wav_sha256"],
            project_root=project_root,
            speaker_input_sample_rate_hz=corpus["speaker_input_sample_rate_hz"],
            speaker_resampling_method=corpus["speaker_resampling_method"],
        )
        recorded = [float(value) for value in row.get("verified_embedding", [])]
        if cosine(recomputed, recorded) < 0.99999:
            raise R2ForgeError("collision corpus embedding does not reproduce from its exact WAV")
        row["embedding"] = recomputed
        row["recomputed_from_exact_wav"] = True
        row["attempt_embedding_input_artifact"] = artifact
        row.pop("verified_embedding", None)
    result["all_embeddings_recomputed_for_this_attempt"] = True
    return result


def validate_audio_acceptance(
    *, job: dict[str, Any], reference_eval: dict[str, Any], clone_eval: dict[str, Any],
    corpus: dict[str, Any], contract: dict[str, Any], environment_spec: dict[str, Any],
    reference_wav_sha256: str, clone_wav_sha256: str,
    project_root: Path,
) -> dict[str, Any]:
    limits = contract["audio_acceptance"]
    evaluator_spec = environment_spec["speech_evaluators"]
    for label, evidence, expected_text, wav_sha256 in (
        ("reference", reference_eval, job["reference_text"], reference_wav_sha256),
        ("clone", clone_eval, job["test_text"], clone_wav_sha256),
    ):
        if evidence.get("asr_mode") != "REAL_LOCAL_ASR" or evidence.get("speech_mode") != "REAL_LOCAL_SPEECH_CLASSIFIER":
            raise R2ForgeError(f"{label} lacks real local ASR/speech evidence")
        if evidence.get("embedding_mode") != "REAL_LOCAL_SPEAKER_EMBEDDING":
            raise R2ForgeError(f"{label} lacks real local speaker embedding")
        if not all(str(evidence.get(key) or "") for key in (
            "asr_engine", "asr_version", "asr_model_manifest_sha256",
            "speech_classifier_engine", "speech_classifier_version",
            "speech_classifier_model_manifest_sha256", "speech_classifier_adapter_sha256",
            "embedding_engine", "embedding_version", "embedding_model_manifest_sha256",
        )):
            raise R2ForgeError(f"{label} evaluator provenance is incomplete")
        require_hash(evidence["asr_model_manifest_sha256"], f"{label} ASR model")
        require_hash(evidence["speech_classifier_model_manifest_sha256"], f"{label} speech classifier model")
        require_hash(evidence["speech_classifier_adapter_sha256"], f"{label} speech classifier adapter")
        require_hash(evidence["embedding_model_manifest_sha256"], f"{label} embedding model")
        expected_provenance = {
            "asr_engine": evaluator_spec["asr_engine"],
            "asr_version": evaluator_spec["asr_version"],
            "asr_model_manifest_sha256": evaluator_spec["asr_model_manifest_sha256"],
            "speech_classifier_engine": evaluator_spec["speech_classifier_engine"],
            "speech_classifier_version": evaluator_spec["speech_classifier_version"],
            "speech_classifier_model_manifest_sha256": evaluator_spec["speech_classifier_model_manifest_sha256"],
            "speech_classifier_adapter_sha256": evaluator_spec["speech_classifier_adapter_sha256"],
            "embedding_engine": evaluator_spec["speaker_embedding_engine"],
            "embedding_version": evaluator_spec["speaker_embedding_version"],
            "embedding_model_manifest_sha256": evaluator_spec["speaker_model_manifest_sha256"],
            "asr_source_wav_sha256": wav_sha256,
            "speech_classifier_source_wav_sha256": wav_sha256,
            "source_wav_sha256": wav_sha256,
            "pure_tone_detector": "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2",
            "speaker_input_sample_rate_hz": evaluator_spec["speaker_input_sample_rate_hz"],
            "speaker_resampling_method": evaluator_spec["speaker_resampling_method"],
        }
        if any(evidence.get(key) != value for key, value in expected_provenance.items()):
            raise R2ForgeError(f"{label} evaluator provenance/source-WAV binding mismatch")
        validate_embedding_input_artifact(
            evidence=evidence,
            source_wav_path=None,
            source_wav_sha256=wav_sha256,
            project_root=project_root,
            speaker_input_sample_rate_hz=evaluator_spec["speaker_input_sample_rate_hz"],
            speaker_resampling_method=evaluator_spec["speaker_resampling_method"],
        )
        wer = word_error_rate(expected_text, str(evidence.get("transcript") or ""))
        evidence["word_error_rate"] = wer
        if wer > float(limits["maximum_word_error_rate"]):
            raise R2ForgeError(f"{label} real ASR text fidelity failed")
        speech_probability = float(evidence.get("speech_probability", float("nan")))
        tone_probability = float(evidence.get("pure_tone_probability", float("nan")))
        if not math.isfinite(speech_probability) or not math.isfinite(tone_probability):
            raise R2ForgeError(f"{label} speech/tone evidence is non-finite")
        if speech_probability < float(limits["minimum_speech_probability"]):
            raise R2ForgeError(f"{label} is not accepted as real speech")
        if tone_probability > float(limits["maximum_pure_tone_probability"]):
            raise R2ForgeError(f"{label} is a sine/pure-tone-like output")
    ref_vector = [float(x) for x in reference_eval.get("speaker_embedding", [])]
    clone_vector = [float(x) for x in clone_eval.get("speaker_embedding", [])]
    self_similarity = cosine(ref_vector, clone_vector)
    if self_similarity < float(limits["minimum_reference_to_clone_similarity"]):
        raise R2ForgeError("clone does not preserve the designed reference identity")
    collisions = []
    for row in corpus["voices"]:
        if row.get("recomputed_from_exact_wav") is not True:
            raise R2ForgeError("collision corpus was not recomputed from exact WAVs this attempt")
        similarity = cosine(clone_vector, [float(x) for x in row["embedding"]])
        collisions.append({"voice_id": row["voice_id"], "kind": row["kind"], "similarity": similarity})
        if similarity > float(limits["maximum_similarity_to_resident_or_generic_voice"]):
            raise R2ForgeError(f"clone collides with a {row['kind']} voice: {row['voice_id']}")
    return {
        "reference_to_clone_similarity": self_similarity,
        "collision_results": collisions,
        "reference_word_error_rate": reference_eval["word_error_rate"],
        "clone_word_error_rate": clone_eval["word_error_rate"],
        "real_speech_and_asr": True,
        "sine_or_pure_tone_rejected": True,
        "generic_or_resident_substitute_rejected": True,
    }


def _wav_samples(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as reader:
        if reader.getnchannels() != 1 or reader.getsampwidth() != 2:
            raise R2ForgeError("only mono PCM16 WAV is accepted")
        rate = reader.getframerate()
        frames = reader.getnframes()
        raw = reader.readframes(frames)
    if frames < rate // 10:
        raise R2ForgeError("WAV is too short")
    integers = struct.unpack(f"<{len(raw)//2}h", raw)
    if not integers or max(abs(x) for x in integers) <= 16:
        raise R2ForgeError("WAV is silent")
    return [x / 32768.0 for x in integers], rate


def pcm16_multiwindow_pure_tone_probability(path: Path) -> float:
    """Measure persistent single-frequency concentration from the real WAV.

    This standard-library implementation is intentionally independent of the
    ASR and speech classifier.  It analyzes bounded windows from the exact
    PCM16 file, so a fabricated evidence dictionary cannot satisfy the gate.
    """

    samples, rate = _wav_samples(path)
    frame_length = max(128, min(400, rate // 40))
    available = len(samples) - frame_length
    if available < frame_length:
        raise R2ForgeError("tone detector received an undersized WAV")
    frame_count = min(12, 1 + available // max(1, frame_length // 2))
    starts = [round(index * available / max(1, frame_count - 1)) for index in range(frame_count)]
    window = [0.5 - 0.5 * math.cos(2 * math.pi * index / (frame_length - 1)) for index in range(frame_length)]
    bins = range(1, frame_length // 2)
    twiddles = [
        [(math.cos(2 * math.pi * frequency * index / frame_length), math.sin(2 * math.pi * frequency * index / frame_length)) for index in range(frame_length)]
        for frequency in bins
    ]
    concentrations: list[float] = []
    for start in starts:
        frame = [samples[start + index] * window[index] for index in range(frame_length)]
        powers: list[float] = []
        for weights in twiddles:
            real = sum(value * cosine_weight for value, (cosine_weight, _sine_weight) in zip(frame, weights))
            imag = sum(value * sine_weight for value, (_cosine_weight, sine_weight) in zip(frame, weights))
            powers.append(real * real + imag * imag)
        total = sum(powers)
        if total <= 1e-12:
            continue
        peak = max(range(len(powers)), key=powers.__getitem__)
        concentrated = sum(powers[max(0, peak - 1):min(len(powers), peak + 2)]) / total
        concentrations.append(concentrated)
    if not concentrations:
        raise R2ForgeError("tone detector found no powered analysis windows")
    median_concentration = statistics.median(concentrations)
    persistent = sum(value >= 0.80 for value in concentrations) / len(concentrations)
    return min(1.0, max(0.0, 0.65 * median_concentration + 0.35 * persistent))


def write_pcm16(path: Path, samples: Any, rate: int) -> dict[str, Any]:
    if hasattr(samples, "detach"):
        samples = samples.detach()
    if hasattr(samples, "cpu"):
        samples = samples.cpu()
    if hasattr(samples, "tolist"):
        samples = samples.tolist()
    while samples and isinstance(samples[0], (list, tuple)):
        if len(samples) != 1:
            raise R2ForgeError("multi-wave output is not accepted")
        samples = samples[0]
    values = [float(x) for x in samples]
    if not values or any(not math.isfinite(x) for x in values):
        raise R2ForgeError("waveform is empty or non-finite")
    pcm = [max(-32768, min(32767, round(x * 32767 if abs(x) <= 1.5 else x))) for x in values]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with wave.open(raw, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            writer.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    decoded, decoded_rate = _wav_samples(path)
    rms = math.sqrt(sum(x * x for x in decoded) / len(decoded))
    return {"path": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size, "sample_rate": decoded_rate, "frames": len(decoded), "duration_seconds": len(decoded)/decoded_rate, "rms": rms, "readable_non_silent_pcm16": True}


class RuntimeProtocol(Protocol):
    def environment_evidence(self, spec: dict[str, Any], project_root: Path) -> dict[str, Any]: ...
    def post_execution_provenance(self, spec: dict[str, Any], project_root: Path) -> dict[str, Any]: ...
    def rss_bytes(self) -> int: ...
    def peak_rss_bytes(self) -> int: ...
    def cuda_allocated_bytes(self) -> int: ...
    def cuda_reserved_bytes(self) -> int: ...
    def reset_peak_cuda_memory_stats(self) -> None: ...
    def peak_cuda_allocated_bytes(self) -> int: ...
    def peak_cuda_reserved_bytes(self) -> int: ...
    def load(self, role: str, snapshot: Path) -> None: ...
    def generate_design(self, *, text: str, language: str, traits: str) -> tuple[Any, int]: ...
    def create_prompt(self, *, reference: tuple[Any, int], reference_text: str) -> Any: ...
    def generate_clone(self, *, text: str, language: str, prompt: Any) -> tuple[Any, int]: ...
    def serialize_prompt(self, prompt: Any) -> bytes: ...
    def unload(self) -> None: ...


class PeakRssSampler:
    """Continuously sample process RSS across generation and evaluation."""

    def __init__(self, reader: Callable[[], int], interval_seconds: float = 0.01) -> None:
        if not (0.001 <= interval_seconds <= 0.1):
            raise R2ForgeError("RSS sampler interval is outside the bounded range")
        self.reader = reader
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.peak_bytes = 0
        self.samples = 0
        self.error: BaseException | None = None
        self.started_utc = ""
        self.ended_utc = ""
        self.started_perf = 0.0
        self.ended_perf = 0.0

    def _sample(self) -> None:
        try:
            value = int(self.reader())
            if value < 0:
                raise R2ForgeError("RSS sampler returned a negative value")
            self.peak_bytes = max(self.peak_bytes, value)
            self.samples += 1
        except BaseException as exc:
            self.error = exc
            self.stop_event.set()

    def _run(self) -> None:
        while not self.stop_event.wait(self.interval_seconds):
            self._sample()

    def start(self) -> None:
        if self.thread is not None:
            raise R2ForgeError("RSS sampler was started twice")
        self.started_utc = utc_now()
        self.started_perf = time.perf_counter()
        self._sample()
        self.thread = threading.Thread(target=self._run, name="qwen3_tts_rss_sampler", daemon=True)
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        if self.thread is None:
            raise R2ForgeError("RSS sampler was never started")
        self._sample()
        self.stop_event.set()
        self.thread.join(timeout=max(1.0, self.interval_seconds * 10))
        if self.thread.is_alive():
            raise R2ForgeError("RSS sampler did not stop cleanly")
        self.ended_perf = time.perf_counter()
        self.ended_utc = utc_now()
        if self.error is not None:
            raise R2ForgeError(f"RSS sampler failed: {self.error}") from self.error
        if self.samples < 2:
            raise R2ForgeError("RSS sampler captured too few samples")
        return {
            "maximum_observed_process_rss_bytes": self.peak_bytes,
            "sample_count": self.samples,
            "sampling_interval_seconds": self.interval_seconds,
            "started_utc": self.started_utc,
            "ended_utc": self.ended_utc,
            "elapsed_seconds": self.ended_perf - self.started_perf,
            "generation_and_evaluation_phases_included": True,
            "is_os_high_water_mark": False,
        }


class EvaluatorProtocol(Protocol):
    def evaluate(self, wav_path: Path, *, expected_text: str, language: str) -> dict[str, Any]: ...
    def speaker_embedding(self, wav_path: Path) -> dict[str, Any]: ...
    def import_provenance_evidence(self) -> dict[str, Any]: ...


class IdentityAnalyzerProtocol(Protocol):
    def analyze(self, *, design_text: str, design_sha256: str, attempt_dir: Path) -> dict[str, Any]: ...


class OfficialIdentityAnalyzerV2:
    """Run the exact hash-bound local identity adapter for this execution."""

    def __init__(self, spec: dict[str, Any], project_root: Path) -> None:
        identity = spec["identity_analyzer"]
        self.project_root = project_root
        self.engine = identity["engine"]
        self.version = identity["version"]
        self.model_manifest_sha256 = identity["model_manifest_sha256"]
        self.adapter = inside(project_root, identity["adapter_path"], "identity analyzer adapter")
        verify_file(self.adapter, identity["adapter_sha256"], "identity analyzer adapter")
        self.model_dir = inside(project_root, identity["model_path"], "identity analyzer model")
        verify_evaluator_model_manifest(
            project_root=project_root,
            model_dir=self.model_dir,
            manifest_path=inside(project_root, identity["model_manifest_path"], "identity analyzer model manifest"),
            expected_hash=identity["model_manifest_sha256"],
            engine=self.engine,
            version=self.version,
        )

    def analyze(self, *, design_text: str, design_sha256: str, attempt_dir: Path) -> dict[str, Any]:
        input_path = attempt_dir / "live_identity_analyzer_input_v2.json"
        output_path = attempt_dir / "live_identity_analyzer_output_v2.json"
        stdout_path = attempt_dir / "live_identity_analyzer_stdout_v2.log"
        stderr_path = attempt_dir / "live_identity_analyzer_stderr_v2.log"
        write_new_json(input_path, {"schema": "qwen3_tts_identity_analyzer_input_v2", "design_text": design_text, "design_sha256": design_sha256})
        command = [
            sys.executable, "-I", "-B", str(self.adapter),
            "--model-dir", str(self.model_dir), "--input", str(input_path), "--output", str(output_path),
        ]
        completed = subprocess.run(
            command, cwd=str(self.project_root), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False,
        )
        write_new(stdout_path, completed.stdout)
        write_new(stderr_path, completed.stderr)
        if completed.returncode != 0:
            raise R2ForgeError("exact local identity analyzer failed")
        report = read_json(output_path)
        if report.get("schema") != "qwen3_tts_live_identity_analyzer_result_v2" or report.get("mode") != "REAL_LOCAL_NER_AND_IMITATION_CLASSIFIER":
            raise R2ForgeError("live identity analyzer result schema/mode mismatch")
        if report.get("engine") != self.engine or report.get("version") != self.version or report.get("input_sha256") != design_sha256:
            raise R2ForgeError("live identity analyzer provenance/input mismatch")
        named_probability = float(report.get("named_person_probability", float("nan")))
        imitation_probability = float(report.get("imitation_request_probability", float("nan")))
        if not math.isfinite(named_probability) or not math.isfinite(imitation_probability):
            raise R2ForgeError("live identity analyzer probabilities are non-finite")
        if report.get("detected_named_person_entities") != [] or report.get("named_person_imitation_requested") is not False:
            raise R2ForgeError("live identity analyzer detected named-person imitation")
        if named_probability > 0.01 or imitation_probability > 0.01:
            raise R2ForgeError("live identity analyzer confidence did not clear")
        if KNOWN_ADVERSARIAL_PERSON.search(design_text) or IMITATION_LANGUAGE.search(design_text):
            raise R2ForgeError("defense-in-depth named-person imitation phrase detected")
        return {
            **report,
            "adapter_sha256": sha256_file(self.adapter),
            "model_manifest_sha256": self.model_manifest_sha256,
            "input_artifact_sha256": sha256_file(input_path),
            "output_artifact_sha256": sha256_file(output_path),
            "stdout_sha256": sha256_file(stdout_path),
            "stderr_sha256": sha256_file(stderr_path),
            "process_returncode": completed.returncode,
            "command_sha256": sha256_bytes(canonical_bytes(command)),
        }


def validate_live_identity_result(
    *, result: dict[str, Any], identity_spec: dict[str, Any], design_text: str, design_sha256: str
) -> None:
    expected = {
        "schema": "qwen3_tts_live_identity_analyzer_result_v2",
        "mode": "REAL_LOCAL_NER_AND_IMITATION_CLASSIFIER",
        "engine": identity_spec["engine"],
        "version": identity_spec["version"],
        "input_sha256": design_sha256,
        "adapter_sha256": identity_spec["adapter_sha256"],
        "model_manifest_sha256": identity_spec["model_manifest_sha256"],
    }
    if any(result.get(key) != value for key, value in expected.items()):
        raise R2ForgeError("live identity result provenance/input mismatch")
    for key in (
        "input_artifact_sha256", "output_artifact_sha256", "stdout_sha256",
        "stderr_sha256", "command_sha256",
    ):
        require_hash(result.get(key), f"live identity {key}")
    if result.get("process_returncode") != 0:
        raise R2ForgeError("live identity analyzer process did not exit cleanly")
    named_probability = float(result.get("named_person_probability", float("nan")))
    imitation_probability = float(result.get("imitation_request_probability", float("nan")))
    if not math.isfinite(named_probability) or not math.isfinite(imitation_probability):
        raise R2ForgeError("live identity analyzer probabilities are non-finite")
    if result.get("detected_named_person_entities") != [] or result.get("named_person_imitation_requested") is not False:
        raise R2ForgeError("live identity analyzer detected named-person imitation")
    if named_probability > 0.01 or imitation_probability > 0.01:
        raise R2ForgeError("live identity analyzer confidence did not clear")
    if KNOWN_ADVERSARIAL_PERSON.search(design_text) or IMITATION_LANGUAGE.search(design_text):
        raise R2ForgeError("defense-in-depth named-person imitation phrase detected")


def canonical_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def validate_environment_attestation_layout(spec: dict[str, Any], project_root: Path) -> None:
    python_path = inside(project_root, spec["python"]["executable_path"], "isolated Python")
    expected_python = (project_root / ISOLATED_VENV_REL / "Scripts/python.exe").resolve()
    if python_path != expected_python:
        raise R2ForgeError("Python executable is not the fixed isolated voice-forge environment")
    site_packages = (project_root / ISOLATED_VENV_REL / "Lib/site-packages").resolve()
    wheel_root = (project_root / WHEEL_EVIDENCE_ROOT_REL).resolve()
    for package, row in spec["distributions"].items():
        record_path = inside(project_root, row["record_path"], f"{package} RECORD")
        try:
            record_path.relative_to(site_packages)
        except ValueError as exc:
            raise R2ForgeError(f"{package} RECORD is outside the isolated environment") from exc
        if record_path.name != "RECORD" or not record_path.parent.name.lower().endswith(".dist-info"):
            raise R2ForgeError(f"{package} RECORD is not an installed dist-info RECORD")
        if package in {"torch", "torchaudio"}:
            wheel_path = inside(project_root, row["wheel_evidence_path"], f"{package} wheel evidence")
            try:
                wheel_path.relative_to(wheel_root)
            except ValueError as exc:
                raise R2ForgeError(f"{package} wheel evidence escaped the fixed wheel-evidence root") from exc
            if wheel_path.name != row["wheel_filename"] or wheel_path.suffix.lower() != ".whl":
                raise R2ForgeError(f"{package} wheel evidence filename/path mismatch")


def verify_installed_distribution(
    *, project_root: Path, package: str, row: dict[str, Any]
) -> dict[str, Any]:
    distribution = importlib.metadata.distribution(package)
    actual_version = distribution.version
    if actual_version != row["version"]:
        raise R2ForgeError(f"{package} version mismatch")
    files = list(distribution.files or [])
    record_candidates = [item for item in files if str(item).replace("\\", "/").endswith(".dist-info/RECORD")]
    if len(record_candidates) != 1:
        raise R2ForgeError(f"{package} installed distribution has no unique RECORD")
    actual_record = Path(distribution.locate_file(record_candidates[0])).resolve()
    expected_record = inside(project_root, row["record_path"], f"{package} RECORD")
    if actual_record != expected_record:
        raise R2ForgeError(f"{package} RECORD path is not bound to the installed distribution")
    verify_file(actual_record, row["record_sha256"], f"{package} RECORD")
    site_packages = (project_root / ISOLATED_VENV_REL / "Lib/site-packages").resolve()
    attested_files: list[dict[str, Any]] = []
    with actual_record.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise R2ForgeError(f"{package} RECORD is empty")
    seen: set[str] = set()
    record_relative = relative(actual_record, site_packages)
    for record_row in rows:
        if len(record_row) != 3:
            raise R2ForgeError(f"{package} RECORD row is malformed")
        rel, encoded_hash, declared_size = record_row
        rel = rel.replace("\\", "/")
        if not rel or rel in seen:
            raise R2ForgeError(f"{package} RECORD path is empty or duplicated")
        seen.add(rel)
        file_path = inside(site_packages, rel, f"{package} installed file")
        if rel == record_relative:
            if encoded_hash or declared_size:
                raise R2ForgeError(f"{package} RECORD self-row must be unhashed")
            attested_files.append({
                "path": relative(actual_record, project_root),
                "bytes": actual_record.stat().st_size,
                "sha256": sha256_file(actual_record),
            })
            continue
        if not encoded_hash.startswith("sha256=") or not declared_size.isdigit():
            raise R2ForgeError(f"{package} RECORD contains an unattested installed file")
        if not file_path.is_file() or file_path.stat().st_size != int(declared_size):
            raise R2ForgeError(f"{package} installed file size/missing mismatch: {rel}")
        encoded = encoded_hash.split("=", 1)[1]
        padding = "=" * ((4 - len(encoded) % 4) % 4)
        try:
            expected_digest = base64.urlsafe_b64decode(encoded + padding).hex()
        except (ValueError, TypeError) as exc:
            raise R2ForgeError(f"{package} RECORD contains an invalid SHA-256") from exc
        if sha256_file(file_path) != expected_digest:
            raise R2ForgeError(f"{package} installed file hash mismatch: {rel}")
        attested_files.append({
            "path": relative(file_path, project_root),
            "bytes": file_path.stat().st_size,
            "sha256": expected_digest,
        })
    distribution_root = Path(distribution.locate_file("")).resolve()
    if distribution_root != site_packages:
        raise R2ForgeError(f"{package} distribution was not loaded from the isolated environment")
    return {
        "version": actual_version,
        "record_path": relative(actual_record, project_root),
        "record_sha256": row["record_sha256"],
        "record_rows_verified": len(attested_files),
        "installed_files": attested_files,
    }


def verify_complete_site_packages_inventory(
    *, project_root: Path, spec: dict[str, Any], distribution_evidence: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Verify every file in the isolated import surface, including loose files."""

    site_packages = (project_root / ISOLATED_VENV_REL / "Lib/site-packages").resolve()
    inventory_spec = spec.get("site_packages_inventory") or {}
    if (
        inventory_spec.get("status") != "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY"
        or inventory_spec.get("complete_file_inventory") is not True
        or inventory_spec.get("all_distributions_and_loose_files_declared") is not True
    ):
        raise R2ForgeError("complete site-packages inventory is not accepted")
    if inside(project_root, inventory_spec.get("root", ""), "site-packages root") != site_packages:
        raise R2ForgeError("site-packages inventory root mismatch")
    manifest_path = inside(
        project_root,
        inventory_spec.get("manifest_path", ""),
        "site-packages inventory manifest",
    )
    try:
        manifest_path.relative_to((project_root / ISOLATED_ROOT_REL).resolve())
    except ValueError as exc:
        raise R2ForgeError("site-packages inventory manifest escaped the isolated sidecar") from exc
    verify_file(manifest_path, inventory_spec.get("manifest_sha256"), "site-packages inventory manifest")
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "qwen3_tts_complete_site_packages_inventory_v2"
        or manifest.get("status") != "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY"
        or manifest.get("complete_file_inventory") is not True
        or manifest.get("site_packages_root") != relative(site_packages, project_root)
    ):
        raise R2ForgeError("site-packages inventory manifest is incomplete")
    distribution_rows = manifest.get("distributions")
    if not isinstance(distribution_rows, list):
        raise R2ForgeError("site-packages distribution inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in distribution_rows:
        name = str(row.get("name") or "") if isinstance(row, dict) else ""
        if not name or name in indexed:
            raise R2ForgeError("site-packages distribution row is invalid/duplicate")
        indexed[name] = row
    if set(indexed) != set(distribution_evidence):
        raise R2ForgeError("site-packages inventory omits a transitive distribution")
    ownership: dict[str, set[str]] = {}
    expected: dict[str, dict[str, Any]] = {}
    for name, evidence in distribution_evidence.items():
        row = indexed[name]
        for key in ("version", "record_path", "record_sha256"):
            if row.get(key) != evidence.get(key):
                raise R2ForgeError(f"site-packages inventory {name} {key} mismatch")
        for installed in evidence["installed_files"]:
            path = inside(project_root, installed["path"], f"{name} attested installed file")
            rel = relative(path, site_packages)
            ownership.setdefault(rel, set()).add(name)
            prior = expected.setdefault(rel, installed)
            if prior["bytes"] != installed["bytes"] or prior["sha256"] != installed["sha256"]:
                raise R2ForgeError("overlapping distribution file evidence conflicts")
    file_rows = manifest.get("files")
    if not isinstance(file_rows, list) or not file_rows:
        raise R2ForgeError("site-packages inventory has no exact files")
    declared: set[str] = set()
    verified_rows: list[dict[str, Any]] = []
    for row in file_rows:
        rel = str(row.get("path") or "") if isinstance(row, dict) else ""
        if not rel or rel in declared:
            raise R2ForgeError("site-packages file row is invalid/duplicate")
        declared.add(rel)
        path = inside(site_packages, rel, "site-packages inventory file")
        verify_file(path, row.get("sha256"), f"site-packages inventory file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2ForgeError("site-packages inventory file size mismatch")
        owners = row.get("owner_distributions")
        if not isinstance(owners, list) or set(owners) != ownership.get(rel, set()):
            raise R2ForgeError("site-packages file ownership binding mismatch")
        if bool(row.get("loose_unowned_file")) != (not owners):
            raise R2ForgeError("site-packages loose-file declaration mismatch")
        if rel in expected and (
            row.get("bytes") != expected[rel]["bytes"] or row.get("sha256") != expected[rel]["sha256"]
        ):
            raise R2ForgeError("site-packages RECORD/inventory file mismatch")
        verified_rows.append({
            "path": relative(path, project_root), "bytes": row["bytes"],
            "sha256": row["sha256"], "owner_distributions": sorted(owners),
            "loose_unowned_file": not owners,
        })
    actual = {relative(path, site_packages) for path in site_packages.rglob("*") if path.is_file()}
    if actual != declared or not set(expected).issubset(declared):
        raise R2ForgeError("site-packages complete inventory drift")
    return {
        "manifest_path": relative(manifest_path, project_root),
        "manifest_sha256": inventory_spec["manifest_sha256"],
        "complete_file_inventory": True,
        "all_transitive_distributions_declared": True,
        "all_loose_files_declared": True,
        "files": verified_rows,
    }


def bind_imported_module_to_attested_record(
    *, package: str, module: Any, distribution_evidence: dict[str, Any], project_root: Path
) -> dict[str, Any]:
    """Reject loose/shadow imports even when genuine dist-info also exists."""

    origin_value = getattr(module, "__file__", None)
    if not origin_value:
        raise R2ForgeError(f"{package} imported module has no exact file origin")
    origin = Path(origin_value).resolve()
    attested = {
        inside(project_root, row["path"], f"{package} attested import file"): row
        for row in distribution_evidence.get("installed_files", [])
    }
    row = attested.get(origin)
    if row is None:
        raise R2ForgeError(f"{package} imported module is not a member of its verified RECORD")
    verify_file(origin, row["sha256"], f"{package} imported module origin")
    if origin.stat().st_size != row["bytes"]:
        raise R2ForgeError(f"{package} imported module origin size drift")
    path_entries: list[str] = []
    for entry in list(getattr(module, "__path__", []) or []):
        package_path = Path(entry).resolve()
        matching = [path for path in attested if path == package_path or package_path in path.parents]
        if not matching:
            raise R2ForgeError(f"{package} imported package path is not owned by its verified RECORD")
        path_entries.append(relative(package_path, project_root))
    return {
        "package": package,
        "module_name": str(getattr(module, "__name__", "")),
        "origin_path": relative(origin, project_root),
        "origin_sha256": row["sha256"],
        "origin_bytes": row["bytes"],
        "package_paths": path_entries,
        "record_membership_verified_after_import": True,
    }


def verify_wheel_archive(*, project_root: Path, package: str, row: dict[str, Any]) -> dict[str, Any]:
    wheel_path = inside(project_root, row["wheel_evidence_path"], f"{package} wheel evidence")
    verify_file(wheel_path, row["wheel_sha256"], f"{package} wheel evidence")
    filename_parts = wheel_path.name[:-4].split("-") if wheel_path.name.lower().endswith(".whl") else []
    if len(filename_parts) < 5:
        raise R2ForgeError(f"{package} wheel filename is not PEP-427-shaped")
    if canonical_distribution_name(filename_parts[0]) != canonical_distribution_name(package) or filename_parts[1] != row["version"]:
        raise R2ForgeError(f"{package} wheel filename package/version mismatch")
    try:
        with zipfile.ZipFile(wheel_path, "r") as archive:
            names = archive.namelist()
            if any(not name or name.startswith(("/", "\\")) or ".." in Path(name).parts for name in names):
                raise R2ForgeError(f"{package} wheel contains an unsafe path")
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            record_names = [name for name in names if name.endswith(".dist-info/RECORD")]
            if len(metadata_names) != 1 or len(record_names) != 1:
                raise R2ForgeError(f"{package} wheel lacks unique METADATA/RECORD")
            metadata = BytesParser(policy=email_policy).parsebytes(archive.read(metadata_names[0]))
            if canonical_distribution_name(str(metadata.get("Name") or "")) != canonical_distribution_name(package):
                raise R2ForgeError(f"{package} wheel METADATA name mismatch")
            if str(metadata.get("Version") or "") != row["version"]:
                raise R2ForgeError(f"{package} wheel METADATA version mismatch")
            record_rows = list(csv.reader(io.StringIO(archive.read(record_names[0]).decode("utf-8"))))
            seen: set[str] = set()
            verified = 0
            for record_row in record_rows:
                if len(record_row) != 3:
                    raise R2ForgeError(f"{package} wheel RECORD row is malformed")
                name, encoded_hash, declared_size = record_row
                if not name or name in seen or name not in names:
                    raise R2ForgeError(f"{package} wheel RECORD inventory is invalid")
                seen.add(name)
                if name == record_names[0]:
                    if encoded_hash or declared_size:
                        raise R2ForgeError(f"{package} wheel RECORD self-row must be unhashed")
                    continue
                if not encoded_hash.startswith("sha256=") or not declared_size.isdigit():
                    raise R2ForgeError(f"{package} wheel contains an unattested member")
                payload = archive.read(name)
                encoded = encoded_hash.split("=", 1)[1]
                padding = "=" * ((4 - len(encoded) % 4) % 4)
                expected_digest = base64.urlsafe_b64decode(encoded + padding).hex()
                if len(payload) != int(declared_size) or sha256_bytes(payload) != expected_digest:
                    raise R2ForgeError(f"{package} wheel member hash/size mismatch: {name}")
                verified += 1
            if set(names) != seen:
                raise R2ForgeError(f"{package} wheel RECORD is not a complete member inventory")
    except (OSError, zipfile.BadZipFile, UnicodeError, csv.Error, ValueError) as exc:
        if isinstance(exc, R2ForgeError):
            raise
        raise R2ForgeError(f"{package} wheel evidence is not a valid exact wheel: {exc}") from exc
    return {
        "path": relative(wheel_path, project_root),
        "filename": wheel_path.name,
        "sha256": row["wheel_sha256"],
        "archive_members_verified": verified,
        "metadata_name": package,
        "metadata_version": row["version"],
    }


class OfficialRuntimeV2:
    def __init__(self) -> None:
        self.torch: Any = None
        self.torchaudio: Any = None
        self.Qwen3TTSModel: Any = None
        self.model: Any = None

    def environment_evidence(self, spec: dict[str, Any], project_root: Path) -> dict[str, Any]:
        validate_environment_attestation_layout(spec, project_root)
        python = spec["python"]
        if sys.version.split()[0] != python["version"]:
            raise R2ForgeError("Python version mismatch")
        executable = Path(sys.executable).resolve()
        if executable != inside(project_root, python["executable_path"], "Python executable"):
            raise R2ForgeError("Python executable path mismatch")
        verify_file(executable, python["executable_sha256"], "Python executable")
        records = {}
        for package, row in sorted(spec["distributions"].items()):
            records[package] = verify_installed_distribution(project_root=project_root, package=package, row=row)
        site_packages_inventory = verify_complete_site_packages_inventory(
            project_root=project_root,
            spec=spec,
            distribution_evidence=records,
        )
        wheels = {}
        for package in ("torch", "torchaudio"):
            wheels[package] = verify_wheel_archive(project_root=project_root, package=package, row=spec["distributions"][package])
        # Package code is imported only after installed RECORDs and exact wheel
        # archives have been independently resolved and fully verified.
        self.torch = importlib.import_module("torch")
        self.torchaudio = importlib.import_module("torchaudio")
        import_bindings = {
            "torch": bind_imported_module_to_attested_record(
                package="torch", module=self.torch,
                distribution_evidence=records["torch"], project_root=project_root,
            ),
            "torchaudio": bind_imported_module_to_attested_record(
                package="torchaudio", module=self.torchaudio,
                distribution_evidence=records["torchaudio"], project_root=project_root,
            ),
        }
        if not self.torch.cuda.is_available():
            raise R2ForgeError("CUDA is unavailable")
        capability = list(self.torch.cuda.get_device_capability(0))
        name = self.torch.cuda.get_device_name(0)
        arch_list = list(self.torch.cuda.get_arch_list())
        cuda_build = str(self.torch.version.cuda)
        cuda_spec = spec["cuda"]
        if name != cuda_spec["device_name"] or capability != cuda_spec["compute_capability"]:
            raise R2ForgeError("GPU device/capability mismatch")
        if cuda_spec["required_arch"] not in arch_list or cuda_build != cuda_spec["torch_cuda_build"]:
            raise R2ForgeError("CUDA build or sm_120 support mismatch")
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            a = self.torch.tensor([[1.0, 2.0], [3.0, 4.0]], device="cuda:0")
            b = self.torch.tensor([[5.0, 6.0], [7.0, 8.0]], device="cuda:0")
            result = (a @ b).cpu().tolist()
            self.torch.cuda.synchronize(0)
        warning_text = "\n".join(str(item.message) for item in caught)
        if result != cuda_spec["ordinary_eager_matrix_expected"]:
            raise R2ForgeError("ordinary eager CUDA matrix result mismatch")
        if re.search(r"unsupported architecture|no kernel image", warning_text, re.I):
            raise R2ForgeError("unsupported CUDA architecture warning occurred")
        # Qwen is deliberately imported last, after exact environment and
        # ordinary eager CUDA attestation have both passed.
        qwen_module = importlib.import_module("qwen_tts")
        transformers_module = importlib.import_module("transformers")
        accelerate_module = importlib.import_module("accelerate")
        import_bindings.update({
            "qwen-tts": bind_imported_module_to_attested_record(
                package="qwen-tts", module=qwen_module,
                distribution_evidence=records["qwen-tts"], project_root=project_root,
            ),
            "transformers": bind_imported_module_to_attested_record(
                package="transformers", module=transformers_module,
                distribution_evidence=records["transformers"], project_root=project_root,
            ),
            "accelerate": bind_imported_module_to_attested_record(
                package="accelerate", module=accelerate_module,
                distribution_evidence=records["accelerate"], project_root=project_root,
            ),
        })
        self.Qwen3TTSModel = getattr(qwen_module, "Qwen3TTSModel")
        return {
            "python_version": sys.version.split()[0],
            "python_executable_path": relative(executable, project_root),
            "python_executable_sha256": sha256_file(executable),
            "distributions": records,
            "site_packages_inventory": site_packages_inventory,
            "imported_module_bindings": import_bindings,
            "wheel_archives": wheels,
            "torch_wheel_sha256": spec["distributions"]["torch"]["wheel_sha256"],
            "torchaudio_wheel_sha256": spec["distributions"]["torchaudio"]["wheel_sha256"],
            "torch_cuda_build": cuda_build,
            "device_name": name,
            "compute_capability": capability,
            "arch_list": arch_list,
            "sm_120_present": True,
            "ordinary_eager_cuda_matrix_result": result,
            "cuda_synchronization_passed": True,
            "unsupported_architecture_warning": False,
            "attention_implementation": "sdpa",
            "torch_compile_invoked": False,
            "network_boundary": NETWORK_BOUNDARY,
            "network_use_proven": False,
        }

    def rss_bytes(self) -> int:
        try:
            import psutil

            return int(psutil.Process().memory_info().rss)
        except (ImportError, OSError) as exc:
            raise R2ForgeError("exact process RSS telemetry unavailable") from exc

    def post_execution_provenance(
        self, spec: dict[str, Any], project_root: Path
    ) -> dict[str, Any]:
        """Re-attest the full import surface and every loaded third-party module."""

        records = {
            package: verify_installed_distribution(
                project_root=project_root,
                package=package,
                row=row,
            )
            for package, row in sorted(spec["distributions"].items())
        }
        site_inventory = verify_complete_site_packages_inventory(
            project_root=project_root,
            spec=spec,
            distribution_evidence=records,
        )
        site_packages = inside(
            project_root,
            spec["site_packages_inventory"]["root"],
            "post-execution site-packages root",
        )
        ownership: dict[Path, list[tuple[str, dict[str, Any]]]] = {}
        for package, evidence in records.items():
            for row in evidence["installed_files"]:
                path = inside(project_root, row["path"], f"{package} post-execution RECORD file")
                ownership.setdefault(path, []).append((package, row))
        loaded: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        imported_owners: set[str] = set()
        for module_name, module in sorted(sys.modules.items()):
            origin_value = getattr(module, "__file__", None)
            if not origin_value:
                continue
            origin = Path(origin_value).resolve()
            try:
                origin.relative_to(site_packages)
            except ValueError:
                continue
            if module_name in seen_names:
                raise R2ForgeError("duplicate loaded third-party module name")
            seen_names.add(module_name)
            owner_rows = ownership.get(origin, [])
            if not owner_rows:
                raise R2ForgeError(
                    f"loaded third-party module is loose or outside every verified RECORD: {module_name}"
                )
            expected_hashes = {row["sha256"] for _package, row in owner_rows}
            expected_sizes = {row["bytes"] for _package, row in owner_rows}
            if len(expected_hashes) != 1 or len(expected_sizes) != 1:
                raise R2ForgeError("loaded module has conflicting RECORD ownership evidence")
            verify_file(origin, next(iter(expected_hashes)), f"loaded module {module_name}")
            if origin.stat().st_size != next(iter(expected_sizes)):
                raise R2ForgeError(f"loaded module size drift: {module_name}")
            owners = sorted(package for package, _row in owner_rows)
            imported_owners.update(owners)
            loaded.append({
                "module_name": module_name,
                "origin_path": relative(origin, project_root),
                "origin_sha256": next(iter(expected_hashes)),
                "origin_bytes": next(iter(expected_sizes)),
                "owner_distributions": owners,
            })
        required_import_owners = {
            "torch", "torchaudio", "qwen-tts", "transformers", "accelerate",
            "faster-whisper", "speechbrain",
        }
        if not required_import_owners.issubset(imported_owners):
            raise R2ForgeError("post-execution imported-module inventory omits a required engine")
        if not loaded:
            raise R2ForgeError("post-execution imported-module inventory is empty")
        return {
            "site_packages_manifest_path": site_inventory["manifest_path"],
            "site_packages_manifest_sha256": site_inventory["manifest_sha256"],
            "complete_site_packages_inventory_reverified_after_execution": True,
            "every_loaded_site_packages_module_bound_to_verified_record": True,
            "required_engine_distributions_observed": sorted(required_import_owners),
            "loaded_module_count": len(loaded),
            "loaded_modules": loaded,
        }

    def peak_rss_bytes(self) -> int:
        """Read the OS process high-water mark, independently of point samples."""

        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                class ProcessMemoryCounters(ctypes.Structure):
                    _fields_ = [
                        ("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t),
                    ]

                counters = ProcessMemoryCounters()
                counters.cb = ctypes.sizeof(counters)
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                psapi = ctypes.WinDLL("psapi", use_last_error=True)
                kernel32.GetCurrentProcess.restype = wintypes.HANDLE
                psapi.GetProcessMemoryInfo.argtypes = [
                    wintypes.HANDLE,
                    ctypes.POINTER(ProcessMemoryCounters),
                    wintypes.DWORD,
                ]
                psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
                handle = kernel32.GetCurrentProcess()
                if not psapi.GetProcessMemoryInfo(
                    handle, ctypes.byref(counters), counters.cb
                ):
                    raise OSError("GetProcessMemoryInfo returned false")
                value = int(counters.PeakWorkingSetSize)
            except (AttributeError, OSError, ValueError) as exc:
                raise R2ForgeError("Windows process peak-RSS telemetry unavailable") from exc
        else:
            try:
                import resource

                raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                value = raw if sys.platform == "darwin" else raw * 1024
            except (ImportError, OSError, ValueError) as exc:
                raise R2ForgeError("process peak-RSS telemetry unavailable") from exc
        if value <= 0:
            raise R2ForgeError("OS process peak-RSS high-water mark is invalid")
        return value

    def cuda_allocated_bytes(self) -> int:
        return int(self.torch.cuda.memory_allocated(0))

    def cuda_reserved_bytes(self) -> int:
        return int(self.torch.cuda.memory_reserved(0))

    def reset_peak_cuda_memory_stats(self) -> None:
        self.torch.cuda.reset_peak_memory_stats(0)
        self.torch.cuda.synchronize(0)

    def peak_cuda_allocated_bytes(self) -> int:
        self.torch.cuda.synchronize(0)
        return int(self.torch.cuda.max_memory_allocated(0))

    def peak_cuda_reserved_bytes(self) -> int:
        self.torch.cuda.synchronize(0)
        return int(self.torch.cuda.max_memory_reserved(0))

    def load(self, role: str, snapshot: Path) -> None:
        if self.model is not None:
            raise R2ForgeError("two heavy models would be resident")
        self.model = self.Qwen3TTSModel.from_pretrained(
            str(snapshot), device_map="cuda:0", dtype=self.torch.bfloat16,
            attn_implementation="sdpa", local_files_only=True,
        )
        self.torch.cuda.synchronize(0)

    def generate_design(self, *, text: str, language: str, traits: str) -> tuple[Any, int]:
        wavs, rate = self.model.generate_voice_design(text=text, language=language, instruct=traits)
        self.torch.cuda.synchronize(0)
        return wavs[0], int(rate)

    def create_prompt(self, *, reference: tuple[Any, int], reference_text: str) -> Any:
        result = self.model.create_voice_clone_prompt(ref_audio=reference, ref_text=reference_text, x_vector_only_mode=False)
        self.torch.cuda.synchronize(0)
        return result

    def generate_clone(self, *, text: str, language: str, prompt: Any) -> tuple[Any, int]:
        wavs, rate = self.model.generate_voice_clone(text=text, language=language, voice_clone_prompt=prompt)
        self.torch.cuda.synchronize(0)
        return wavs[0], int(rate)

    def serialize_prompt(self, prompt: Any) -> bytes:
        buffer = io.BytesIO()
        self.torch.save(prompt, buffer)
        return buffer.getvalue()

    def unload(self) -> None:
        self.model = None
        gc.collect()
        self.torch.cuda.empty_cache()
        self.torch.cuda.synchronize(0)


class OfficialSpeechEvaluatorV2:
    """Exact local ASR, speech-classifier, and speaker evaluator."""

    def __init__(self, spec: dict[str, Any], project_root: Path) -> None:
        evaluator = spec["speech_evaluators"]
        self.asr_manifest_hash = evaluator["asr_model_manifest_sha256"]
        self.embedding_manifest_hash = evaluator["speaker_model_manifest_sha256"]
        self.asr_engine = evaluator["asr_engine"]
        self.asr_version = evaluator["asr_version"]
        self.embedding_engine = evaluator["speaker_embedding_engine"]
        self.embedding_version = evaluator["speaker_embedding_version"]
        self.speech_engine = evaluator["speech_classifier_engine"]
        self.speech_version = evaluator["speech_classifier_version"]
        self.speech_manifest_hash = evaluator["speech_classifier_model_manifest_sha256"]
        self.speech_adapter_hash = evaluator["speech_classifier_adapter_sha256"]
        self.speaker_input_sample_rate_hz = int(evaluator["speaker_input_sample_rate_hz"])
        self.speaker_resampling_method = evaluator["speaker_resampling_method"]
        self.project_root = project_root
        asr_path = inside(project_root, evaluator["asr_model_path"], "ASR model")
        speaker_path = inside(project_root, evaluator["speaker_model_path"], "speaker model")
        speech_path = inside(project_root, evaluator["speech_classifier_model_path"], "speech-classifier model")
        self.speech_adapter = inside(project_root, evaluator["speech_classifier_adapter_path"], "speech-classifier adapter")
        verify_file(self.speech_adapter, self.speech_adapter_hash, "speech-classifier adapter")
        verify_evaluator_model_manifest(
            project_root=project_root, model_dir=asr_path,
            manifest_path=inside(project_root, evaluator["asr_model_manifest_path"], "ASR model manifest"),
            expected_hash=self.asr_manifest_hash, engine=self.asr_engine, version=self.asr_version,
        )
        verify_evaluator_model_manifest(
            project_root=project_root, model_dir=speaker_path,
            manifest_path=inside(project_root, evaluator["speaker_model_manifest_path"], "speaker model manifest"),
            expected_hash=self.embedding_manifest_hash, engine=self.embedding_engine, version=self.embedding_version,
        )
        verify_evaluator_model_manifest(
            project_root=project_root, model_dir=speech_path,
            manifest_path=inside(project_root, evaluator["speech_classifier_model_manifest_path"], "speech-classifier model manifest"),
            expected_hash=self.speech_manifest_hash, engine=self.speech_engine, version=self.speech_version,
        )
        faster_whisper_module = importlib.import_module("faster_whisper")
        speechbrain_module = importlib.import_module("speechbrain.inference.speaker")
        WhisperModel = getattr(faster_whisper_module, "WhisperModel")
        EncoderClassifier = getattr(speechbrain_module, "EncoderClassifier")
        self.asr = WhisperModel(str(asr_path), device="cuda", compute_type="float16", local_files_only=True)
        self.speaker = EncoderClassifier.from_hparams(source=str(speaker_path), savedir=str(speaker_path), run_opts={"device": "cuda"})
        self.speech_model_path = speech_path
        self.torchaudio = importlib.import_module("torchaudio")
        self.torch = importlib.import_module("torch")
        self._import_modules = {
            "faster-whisper": faster_whisper_module,
            "speechbrain": speechbrain_module,
            "torchaudio": self.torchaudio,
            "torch": self.torch,
        }
        self._distribution_evidence = {
            package: verify_installed_distribution(
                project_root=project_root,
                package=package,
                row=spec["distributions"][package],
            )
            for package in self._import_modules
        }
        self._import_bindings = self.import_provenance_evidence()

    def import_provenance_evidence(self) -> dict[str, Any]:
        return {
            package: bind_imported_module_to_attested_record(
                package=package,
                module=module,
                distribution_evidence=self._distribution_evidence[package],
                project_root=self.project_root,
            )
            for package, module in self._import_modules.items()
        }

    def speaker_embedding(self, wav_path: Path) -> dict[str, Any]:
        source_sha256 = sha256_file(wav_path)
        signal, source_rate = self.torchaudio.load(str(wav_path))
        source_rate = int(source_rate)
        if source_rate <= 0:
            raise R2ForgeError("speaker evaluator source sample rate is invalid")
        normalized = signal.to(dtype=self.torch.float32, device="cpu")
        if source_rate != self.speaker_input_sample_rate_hz:
            normalized = self.torchaudio.functional.resample(
                normalized,
                source_rate,
                self.speaker_input_sample_rate_hz,
            )
        normalized_path = speaker_embedding_artifact_path(
            source_wav_path=wav_path,
            project_root=self.project_root,
            target_sample_rate_hz=self.speaker_input_sample_rate_hz,
        )
        if normalized_path.exists():
            raise R2ForgeError("speaker embedding input artifact already exists")
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        self.torchaudio.save(
            str(normalized_path),
            normalized,
            self.speaker_input_sample_rate_hz,
            encoding="PCM_S",
            bits_per_sample=16,
        )
        _normalized_samples, normalized_rate = _wav_samples(normalized_path)
        if normalized_rate != self.speaker_input_sample_rate_hz:
            raise R2ForgeError("speaker embedding resampling artifact rate mismatch")
        exact_normalized_signal, exact_normalized_rate = self.torchaudio.load(str(normalized_path))
        if int(exact_normalized_rate) != self.speaker_input_sample_rate_hz:
            raise R2ForgeError("speaker embedding exact-artifact reload rate mismatch")
        exact_normalized_signal = exact_normalized_signal.to(
            dtype=self.torch.float32,
            device="cpu",
        )
        embedding = (
            self.speaker.encode_batch(exact_normalized_signal)
            .detach().cpu().reshape(-1).tolist()
        )
        values = [float(value) for value in embedding]
        if len(values) < 2 or not all(math.isfinite(value) for value in values):
            raise R2ForgeError("real speaker evaluator returned an invalid embedding")
        return {
            "embedding_mode": "REAL_LOCAL_SPEAKER_EMBEDDING",
            "embedding_engine": self.embedding_engine,
            "embedding_version": self.embedding_version,
            "embedding_model_manifest_sha256": self.embedding_manifest_hash,
            "source_wav_sha256": source_sha256,
            "source_sample_rate_hz": source_rate,
            "speaker_input_sample_rate_hz": self.speaker_input_sample_rate_hz,
            "speaker_resampling_method": self.speaker_resampling_method,
            "resampled_for_embedding": source_rate != self.speaker_input_sample_rate_hz,
            "embedding_input_wav_path": relative(normalized_path, self.project_root),
            "embedding_input_wav_sha256": sha256_file(normalized_path),
            "embedding_input_wav_bytes": normalized_path.stat().st_size,
            "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
            "speaker_embedding": values,
        }

    def _speech_classifier(self, wav_path: Path) -> dict[str, Any]:
        output_path = wav_path.with_name(f"{wav_path.stem}.speech_classifier_result_v2.json")
        stdout_path = wav_path.with_name(f"{wav_path.stem}.speech_classifier_stdout_v2.log")
        stderr_path = wav_path.with_name(f"{wav_path.stem}.speech_classifier_stderr_v2.log")
        command = [
            sys.executable, "-I", "-B", str(self.speech_adapter),
            "--model-dir", str(self.speech_model_path),
            "--wav", str(wav_path),
            "--output", str(output_path),
        ]
        completed = subprocess.run(
            command,
            cwd=str(self.project_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
            check=False,
        )
        write_new(stdout_path, completed.stdout)
        write_new(stderr_path, completed.stderr)
        if completed.returncode != 0:
            raise R2ForgeError("exact real speech classifier failed")
        result = read_json(output_path)
        expected = {
            "schema": "qwen3_tts_real_speech_classifier_result_v2",
            "mode": "REAL_LOCAL_SPEECH_CLASSIFIER",
            "engine": self.speech_engine,
            "version": self.speech_version,
            "model_manifest_sha256": self.speech_manifest_hash,
            "source_wav_sha256": sha256_file(wav_path),
        }
        if any(result.get(key) != value for key, value in expected.items()):
            raise R2ForgeError("real speech classifier result provenance/input mismatch")
        probability = float(result.get("speech_probability", float("nan")))
        if not math.isfinite(probability) or probability < 0 or probability > 1:
            raise R2ForgeError("real speech classifier returned an invalid probability")
        return {
            "speech_mode": "REAL_LOCAL_SPEECH_CLASSIFIER",
            "speech_classifier_engine": self.speech_engine,
            "speech_classifier_version": self.speech_version,
            "speech_classifier_model_manifest_sha256": self.speech_manifest_hash,
            "speech_classifier_adapter_sha256": self.speech_adapter_hash,
            "speech_classifier_source_wav_sha256": sha256_file(wav_path),
            "speech_probability": probability,
            "speech_classifier_result_sha256": sha256_file(output_path),
            "speech_classifier_stdout_sha256": sha256_file(stdout_path),
            "speech_classifier_stderr_sha256": sha256_file(stderr_path),
            "speech_classifier_process_returncode": completed.returncode,
        }

    def _pure_tone_probability(self, wav_path: Path) -> float:
        return pcm16_multiwindow_pure_tone_probability(wav_path)

    def evaluate(self, wav_path: Path, *, expected_text: str, language: str) -> dict[str, Any]:
        segments, _info = self.asr.transcribe(str(wav_path), language=language[:2].lower(), beam_size=5)
        segments = list(segments)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        embedding = self.speaker_embedding(wav_path)
        speech = self._speech_classifier(wav_path)
        return {
            "asr_mode": "REAL_LOCAL_ASR",
            "asr_engine": self.asr_engine,
            "asr_version": self.asr_version,
            "asr_model_manifest_sha256": self.asr_manifest_hash,
            "transcript": transcript,
            "asr_source_wav_sha256": sha256_file(wav_path),
            **speech,
            "pure_tone_probability": self._pure_tone_probability(wav_path),
            "pure_tone_detector": "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2",
            **embedding,
        }


def validate_runtime_environment_evidence(evidence: dict[str, Any], spec: dict[str, Any]) -> None:
    if evidence.get("python_version") != spec["python"]["version"] or evidence.get("python_executable_sha256") != spec["python"]["executable_sha256"]:
        raise R2ForgeError("runtime Python evidence mismatch")
    if evidence.get("python_executable_path") != spec["python"]["executable_path"]:
        raise R2ForgeError("runtime Python executable path evidence mismatch")
    if evidence.get("device_name") != spec["cuda"]["device_name"] or evidence.get("compute_capability") != spec["cuda"]["compute_capability"]:
        raise R2ForgeError("runtime device/capability evidence mismatch")
    if evidence.get("torch_cuda_build") != spec["cuda"]["torch_cuda_build"] or evidence.get("sm_120_present") is not True:
        raise R2ForgeError("runtime CUDA build/sm_120 evidence mismatch")
    if evidence.get("ordinary_eager_cuda_matrix_result") != spec["cuda"]["ordinary_eager_matrix_expected"]:
        raise R2ForgeError("runtime eager CUDA operation evidence mismatch")
    if evidence.get("cuda_synchronization_passed") is not True or evidence.get("unsupported_architecture_warning") is not False:
        raise R2ForgeError("runtime CUDA synchronization/warning gate failed")
    if evidence.get("torch_wheel_sha256") != spec["distributions"]["torch"]["wheel_sha256"] or evidence.get("torchaudio_wheel_sha256") != spec["distributions"]["torchaudio"]["wheel_sha256"]:
        raise R2ForgeError("runtime Torch/Torchaudio wheel evidence mismatch")
    records = evidence.get("distributions") or {}
    for package, expected in spec["distributions"].items():
        actual = records.get(package) or {}
        if actual.get("version") != expected.get("version") or actual.get("record_sha256") != expected.get("record_sha256") or actual.get("record_path") != expected.get("record_path"):
            raise R2ForgeError(f"runtime {package} version/RECORD evidence mismatch")
        installed_files = actual.get("installed_files")
        if not isinstance(installed_files, list) or not installed_files or actual.get("record_rows_verified") != len(installed_files):
            raise R2ForgeError(f"runtime {package} installed RECORD inventory was not fully verified")
        for row in installed_files:
            if not isinstance(row, dict) or not str(row.get("path") or "") or not isinstance(row.get("bytes"), int):
                raise R2ForgeError(f"runtime {package} installed file evidence is invalid")
            require_hash(row.get("sha256"), f"runtime {package} installed file")
    site_inventory = evidence.get("site_packages_inventory") or {}
    expected_inventory = spec.get("site_packages_inventory") or {}
    if (
        site_inventory.get("manifest_path") != expected_inventory.get("manifest_path")
        or site_inventory.get("manifest_sha256") != expected_inventory.get("manifest_sha256")
        or site_inventory.get("complete_file_inventory") is not True
        or site_inventory.get("all_transitive_distributions_declared") is not True
        or site_inventory.get("all_loose_files_declared") is not True
        or not isinstance(site_inventory.get("files"), list)
        or not site_inventory["files"]
    ):
        raise R2ForgeError("runtime complete site-packages inventory evidence mismatch")
    bindings = evidence.get("imported_module_bindings") or {}
    for package in ("torch", "torchaudio", "qwen-tts", "transformers", "accelerate"):
        binding = bindings.get(package) or {}
        if binding.get("record_membership_verified_after_import") is not True:
            raise R2ForgeError(f"runtime {package} imported-module RECORD binding is absent")
        require_hash(binding.get("origin_sha256"), f"runtime {package} imported-module origin")
        if not any(
            row.get("path") == binding.get("origin_path")
            and row.get("sha256") == binding.get("origin_sha256")
            and row.get("bytes") == binding.get("origin_bytes")
            for row in (records.get(package) or {}).get("installed_files", [])
        ):
            raise R2ForgeError(f"runtime {package} imported module is not bound to its verified RECORD")
    wheels = evidence.get("wheel_archives") or {}
    for package in ("torch", "torchaudio"):
        wheel = wheels.get(package) or {}
        expected = spec["distributions"][package]
        if wheel.get("path") != expected.get("wheel_evidence_path") or wheel.get("filename") != expected.get("wheel_filename") or wheel.get("sha256") != expected.get("wheel_sha256"):
            raise R2ForgeError(f"runtime {package} exact wheel archive evidence mismatch")
        if not isinstance(wheel.get("archive_members_verified"), int) or wheel["archive_members_verified"] <= 0:
            raise R2ForgeError(f"runtime {package} wheel members were not fully verified")
    if evidence.get("attention_implementation") != "sdpa" or evidence.get("torch_compile_invoked") is not False:
        raise R2ForgeError("runtime is not ordinary eager/SDPA")
    if evidence.get("network_boundary") != NETWORK_BOUNDARY or evidence.get("network_use_proven") is not False:
        raise R2ForgeError("runtime overstated network isolation/nonuse")


def validate_evaluator_import_bindings(
    bindings: dict[str, Any], environment_evidence: dict[str, Any]
) -> None:
    records = environment_evidence.get("distributions") or {}
    for package in ("faster-whisper", "speechbrain", "torchaudio", "torch"):
        binding = bindings.get(package) or {}
        if binding.get("record_membership_verified_after_import") is not True:
            raise R2ForgeError(f"evaluator {package} imported-module RECORD binding is absent")
        require_hash(binding.get("origin_sha256"), f"evaluator {package} imported-module origin")
        if not any(
            row.get("path") == binding.get("origin_path")
            and row.get("sha256") == binding.get("origin_sha256")
            and row.get("bytes") == binding.get("origin_bytes")
            for row in (records.get(package) or {}).get("installed_files", [])
        ):
            raise R2ForgeError(f"evaluator {package} import is outside its verified RECORD")


def execute_verified_bundle(
    *, trusted: TrustedBundle, attempt_dir: Path,
    runtime_factory: Callable[[], RuntimeProtocol] = OfficialRuntimeV2,
    evaluator_factory: Callable[[dict[str, Any], Path], EvaluatorProtocol] = OfficialSpeechEvaluatorV2,
    identity_analyzer_factory: Callable[[dict[str, Any], Path], IdentityAnalyzerProtocol] = OfficialIdentityAnalyzerV2,
) -> dict[str, Any]:
    attempt_dir = attempt_dir.resolve()
    expected_parent = (trusted.project_root / OUTPUT_ROOT_REL / trusted.bundle["bundle_id"]).resolve()
    if attempt_dir.parent != expected_parent or not re.fullmatch(r"attempt_[0-9]{2,3}", attempt_dir.name):
        raise R2ForgeError("attempt is not the exact parent-reserved append-only slot")
    reservation_path = attempt_dir / "parent_reservation.json"
    reservation = read_json(reservation_path)
    if reservation.get("schema") != "qwen3_tts_voice_forge_parent_reservation_v2" or reservation.get("status") != "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE" or reservation.get("bundle_id") != trusted.bundle["bundle_id"]:
        raise R2ForgeError("parent reservation is missing or mismatched")
    for key, value in queue_binding_payload(trusted.bundle).items():
        if reservation.get(key) != value:
            raise R2ForgeError(f"parent reservation {key} binding mismatch")
    verify_file(trusted.project_root / HARNESS_MANIFEST_REL, reservation.get("harness_manifest_sha256"), "parent-verified harness manifest")
    verify_file(trusted.project_root / CONTRACT_REL, reservation.get("contract_sha256"), "parent-verified contract")
    verify_file(trusted.project_root / ENVIRONMENT_REL, reservation.get("environment_spec_sha256"), "parent-verified environment spec")
    verify_file(trusted.project_root / REGISTRY_REL, reservation.get("trusted_registry_sha256"), "parent-verified trusted registry")
    verify_file(trusted.bundle_dir / "BUNDLE_SEAL.json", reservation.get("bundle_seal_sha256"), "parent-verified bundle seal")
    if reservation.get("verified_worker_sha256") != sha256_file(Path(__file__).resolve()):
        raise R2ForgeError("running worker differs from the parent-verified worker")
    ledger_path = inside(trusted.project_root, reservation.get("nonce_ledger_path", ""), "nonce ledger")
    expected_ledger = (trusted.project_root / NONCE_LEDGER_REL / f"{trusted.bundle['single_use_nonce_sha256']}.json").resolve()
    if ledger_path != expected_ledger:
        raise R2ForgeError("nonce ledger path mismatch")
    verify_file(ledger_path, reservation.get("nonce_ledger_sha256"), "single-use nonce ledger")
    ledger = read_json(ledger_path)
    if ledger.get("schema") != "qwen3_tts_voice_forge_single_use_nonce_ledger_v2" or ledger.get("status") != "CONSUMED_FOR_EXACT_QUEUE_ATTEMPT":
        raise R2ForgeError("single-use nonce ledger status mismatch")
    for key in (
        "bundle_id", "candidate_id", "opaque_voice_id", "ai_type", "single_use_nonce_sha256", "queue_binding_sha256", "job_sha256",
        "canonical_profile_sha256", "canonical_creation_request_sha256", "identity_clearance_manifest_sha256",
        "watermark_evidence_manifest_sha256", "evaluation_corpus_sha256", "voice_design_model_manifest_sha256",
        "base_model_manifest_sha256", "environment_spec_sha256",
    ):
        if ledger.get(key) != trusted.bundle.get(key):
            raise R2ForgeError(f"single-use nonce ledger {key} binding mismatch")
    if ledger.get("attempt") != relative(attempt_dir, trusted.project_root):
        raise R2ForgeError("single-use nonce/queue ledger binding mismatch")

    started = time.perf_counter()
    runtime: RuntimeProtocol | None = None
    rss_sampler: PeakRssSampler | None = None
    events = []
    try:
        design_snapshot, design_snapshot_manifest = create_private_model_snapshot(
            project_root=trusted.project_root, bundle=trusted.bundle, attempt_dir=attempt_dir, role="voice_design"
        )
        base_snapshot, base_snapshot_manifest = create_private_model_snapshot(
            project_root=trusted.project_root, bundle=trusted.bundle, attempt_dir=attempt_dir, role="base"
        )
        snapshot_environment, evaluator_snapshot_manifests = create_private_evaluator_snapshots(
            project_root=trusted.project_root,
            spec=trusted.environment_spec,
            attempt_dir=attempt_dir,
        )
        verify_private_evaluator_snapshots(attempt_dir=attempt_dir, snapshots=evaluator_snapshot_manifests)
        snapshot_corpus, corpus_snapshot_manifest = create_private_corpus_snapshot(
            project_root=trusted.project_root,
            corpus=trusted.evaluation_corpus,
            attempt_dir=attempt_dir,
        )
        verify_private_corpus_snapshot(attempt_dir=attempt_dir, manifest=corpus_snapshot_manifest)
        runtime = runtime_factory()
        environment = runtime.environment_evidence(trusted.environment_spec, trusted.project_root)
        validate_runtime_environment_evidence(environment, trusted.environment_spec)
        live_watermark_scan = run_live_watermark_documentation_scan(
            project_root=trusted.project_root,
            attempt_dir=attempt_dir,
            model_snapshots=[design_snapshot, base_snapshot, attempt_dir / "private_collision_corpus_snapshot"],
            evaluator_snapshots=evaluator_snapshot_manifests,
            environment_evidence=environment,
        )
        events.append("LIVE_HASH_BOUND_WATERMARK_DOCUMENTATION_SCAN_PASSED_INITIAL_STATUS_ONLY")
        live_identity = identity_analyzer_factory(snapshot_environment, trusted.project_root).analyze(
            design_text=trusted.job["design_traits_text"],
            design_sha256=trusted.job["design_traits_text_sha256"],
            attempt_dir=attempt_dir,
        )
        validate_live_identity_result(
            result=live_identity,
            identity_spec=trusted.environment_spec["identity_analyzer"],
            design_text=trusted.job["design_traits_text"],
            design_sha256=trusted.job["design_traits_text_sha256"],
        )
        write_new_json(attempt_dir / "live_identity_clearance_v2.json", live_identity)
        events.append("LIVE_IDENTITY_ANALYZER_CLEARED_BEFORE_MODEL_LOAD")
        baseline_allocated = runtime.cuda_allocated_bytes()
        baseline_reserved = runtime.cuda_reserved_bytes()
        baseline_rss = runtime.rss_bytes()
        runtime.reset_peak_cuda_memory_stats()
        rss_sampler = PeakRssSampler(runtime.rss_bytes, interval_seconds=0.01)
        rss_sampler.start()
        timings = {}

        verify_private_snapshot(design_snapshot, design_snapshot_manifest)
        tick = time.perf_counter(); runtime.load("voice_design", design_snapshot); timings["voice_design_load"] = time.perf_counter()-tick
        after_design_load_allocated = runtime.cuda_allocated_bytes(); after_design_load_reserved = runtime.cuda_reserved_bytes()
        tick = time.perf_counter(); reference, reference_rate = runtime.generate_design(text=trusted.job["reference_text"], language=trusted.job["language"], traits=trusted.job["design_traits_text"]); timings["voice_design_generation"] = time.perf_counter()-tick
        design_generation_allocated = runtime.cuda_allocated_bytes()
        reference_wav_path = attempt_dir / "original_design_reference.wav"
        reference_wav = write_pcm16(reference_wav_path, reference, reference_rate)
        runtime.unload(); events.append("VOICE_DESIGN_UNLOADED_BEFORE_BASE")
        verify_private_snapshot(design_snapshot, design_snapshot_manifest)
        after_design_allocated = runtime.cuda_allocated_bytes(); after_design_reserved = runtime.cuda_reserved_bytes()
        return_bound = 268435456
        if after_design_allocated > baseline_allocated + return_bound or after_design_reserved > baseline_reserved + return_bound:
            raise R2ForgeError("VoiceDesign VRAM did not return before Base")

        verify_private_snapshot(base_snapshot, base_snapshot_manifest)
        tick = time.perf_counter(); runtime.load("runtime_clone", base_snapshot); timings["base_load"] = time.perf_counter()-tick
        after_base_load_allocated = runtime.cuda_allocated_bytes(); after_base_load_reserved = runtime.cuda_reserved_bytes()
        tick = time.perf_counter(); prompt = runtime.create_prompt(reference=(reference, reference_rate), reference_text=trusted.job["reference_text"]); timings["clone_prompt"] = time.perf_counter()-tick
        prompt_path = attempt_dir / "runtime_clone_prompt.pt"; write_new(prompt_path, runtime.serialize_prompt(prompt))
        tick = time.perf_counter(); clone, clone_rate = runtime.generate_clone(text=trusted.job["test_text"], language=trusted.job["language"], prompt=prompt); timings["clone_generation"] = time.perf_counter()-tick
        clone_generation_allocated = runtime.cuda_allocated_bytes()
        clone_wav_path = attempt_dir / "runtime_clone_test.wav"; clone_wav = write_pcm16(clone_wav_path, clone, clone_rate)
        runtime.unload(); events.append("BASE_UNLOADED")
        verify_private_snapshot(base_snapshot, base_snapshot_manifest)
        final_allocated = runtime.cuda_allocated_bytes(); final_reserved = runtime.cuda_reserved_bytes()
        if final_allocated > baseline_allocated + return_bound or final_reserved > baseline_reserved + return_bound:
            raise R2ForgeError("final VRAM did not return")
        if min(design_generation_allocated, clone_generation_allocated) <= baseline_allocated:
            raise R2ForgeError("CUDA allocation was absent during synthesis")

        evaluator = evaluator_factory(snapshot_environment, trusted.project_root)
        evaluator_import_bindings = evaluator.import_provenance_evidence()
        validate_evaluator_import_bindings(evaluator_import_bindings, environment)
        recomputed_corpus = recompute_collision_corpus(
            evaluator=evaluator,
            corpus=snapshot_corpus,
            project_root=trusted.project_root,
        )
        reference_eval = evaluator.evaluate(reference_wav_path, expected_text=trusted.job["reference_text"], language=trusted.job["language"])
        clone_eval = evaluator.evaluate(clone_wav_path, expected_text=trusted.job["test_text"], language=trusted.job["language"])
        audio_acceptance = validate_audio_acceptance(
            job=trusted.job,
            reference_eval=reference_eval,
            clone_eval=clone_eval,
            corpus=recomputed_corpus,
            contract=trusted.contract,
            environment_spec=trusted.environment_spec,
            reference_wav_sha256=reference_wav["sha256"],
            clone_wav_sha256=clone_wav["sha256"],
            project_root=trusted.project_root,
        )
        verify_private_evaluator_snapshots(attempt_dir=attempt_dir, snapshots=evaluator_snapshot_manifests)
        verify_private_corpus_snapshot(attempt_dir=attempt_dir, manifest=corpus_snapshot_manifest)
        evaluator_import_bindings = evaluator.import_provenance_evidence()
        validate_evaluator_import_bindings(evaluator_import_bindings, environment)
        post_execution_provenance = runtime.post_execution_provenance(
            trusted.environment_spec,
            trusted.project_root,
        )
        if (
            post_execution_provenance.get(
                "complete_site_packages_inventory_reverified_after_execution"
            ) is not True
            or post_execution_provenance.get(
                "every_loaded_site_packages_module_bound_to_verified_record"
            ) is not True
        ):
            raise R2ForgeError("post-execution imported-module provenance is incomplete")
        peak_cuda_allocated = runtime.peak_cuda_allocated_bytes()
        peak_cuda_reserved = runtime.peak_cuda_reserved_bytes()
        if peak_cuda_allocated < max(design_generation_allocated, clone_generation_allocated):
            raise R2ForgeError("Torch peak CUDA allocation counter is inconsistent")
        rss_telemetry = rss_sampler.stop()
        rss_sampler = None
        os_peak_rss = runtime.peak_rss_bytes()
        if (
            rss_telemetry["maximum_observed_process_rss_bytes"] < baseline_rss
            or os_peak_rss < rss_telemetry["maximum_observed_process_rss_bytes"]
        ):
            raise R2ForgeError("process RSS peak telemetry is inconsistent")
        profile = {
            "schema": "qwen3_tts_original_voice_profile_candidate_v2",
            "status": "PRIVATE_UNREVIEWED_ENGINEERING_PASS_OWNER_HEARING_PENDING",
            "bundle_id": trusted.bundle["bundle_id"], "candidate_id": trusted.bundle["candidate_id"], "ai_type": trusted.bundle["ai_type"], "opaque_voice_id": trusted.bundle["opaque_voice_id"],
            "canonical_profile_sha256": trusted.bundle["canonical_profile_sha256"], "canonical_creation_request_sha256": trusted.bundle["canonical_creation_request_sha256"],
            "job_sha256": trusted.bundle["job_sha256"], "owner_authorization_sha256": trusted.bundle["owner_authorization_sha256"], "queue_binding_sha256": trusted.bundle["queue_binding_sha256"],
            "watermark_status": INITIAL_WATERMARK_STATUS,
            "stronger_watermark_status": "REQUIRES_SEPARATE_POST_GENERATION_APPEND_ONLY_AUDIT",
            "network_boundary": NETWORK_BOUNDARY, "network_use_proven": False,
            "assignment_allowed": False, "activation_allowed": False, "publication_or_upload_allowed": False,
            "owner_hearing_acceptance": "PENDING", "independent_audit": "REQUIRED",
            "fallback": FAILURE_STATUS,
            "artifacts": {"reference_wav": reference_wav, "clone_prompt_sha256": sha256_file(prompt_path), "clone_test_wav": clone_wav},
            "audio_acceptance": audio_acceptance,
            "live_identity_clearance_sha256": sha256_file(attempt_dir / "live_identity_clearance_v2.json"),
            "live_watermark_documentation_scan_sha256": live_watermark_scan["report_sha256"],
        }
        profile_path = attempt_dir / "voice_profile_candidate_v2.json"; write_new_json(profile_path, profile)
        manifest = {
            "schema": "qwen3_tts_original_voice_forge_worker_manifest_v2",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
            "bundle_id": trusted.bundle["bundle_id"], "candidate_id": trusted.bundle["candidate_id"], "opaque_voice_id": trusted.bundle["opaque_voice_id"],
            "private_append_only": True, "single_use_nonce_consumed": True,
            "environment": environment,
            "post_execution_environment_provenance": post_execution_provenance,
            "network_boundary": NETWORK_BOUNDARY, "network_use_proven": False,
            "model_snapshots": {"voice_design": design_snapshot_manifest, "base": base_snapshot_manifest, "verified_after_unload": True},
            "evaluator_snapshots": {"roles": evaluator_snapshot_manifests, "verified_after_evaluation": True},
            "evaluator_imported_module_bindings": evaluator_import_bindings,
            "collision_corpus_snapshot": {"manifest": corpus_snapshot_manifest, "verified_after_evaluation": True},
            "telemetry": {
                "rss_sampler": rss_telemetry,
                "os_reported_peak_process_rss_bytes": os_peak_rss,
                "os_reported_peak_process_rss_is_high_water_mark": True,
                "baseline_process_rss_bytes": baseline_rss,
                "baseline_cuda_allocated_bytes": baseline_allocated,
                "baseline_cuda_reserved_bytes": baseline_reserved,
                "torch_peak_cuda_allocated_bytes": peak_cuda_allocated,
                "torch_peak_cuda_reserved_bytes": peak_cuda_reserved,
                "after_design_load_observed_cuda_allocated_bytes": after_design_load_allocated,
                "after_design_load_observed_cuda_reserved_bytes": after_design_load_reserved,
                "after_base_load_observed_cuda_allocated_bytes": after_base_load_allocated,
                "after_base_load_observed_cuda_reserved_bytes": after_base_load_reserved,
                "after_design_unload_cuda_allocated_bytes": after_design_allocated,
                "final_cuda_allocated_bytes": final_allocated,
                "final_cuda_reserved_bytes": final_reserved,
                "design_generation_observed_cuda_allocated_bytes": design_generation_allocated,
                "clone_generation_observed_cuda_allocated_bytes": clone_generation_allocated,
                "point_samples_labeled_as_peaks": False
            },
            "timings_seconds": {**timings, "total_worker": time.perf_counter()-started}, "events": events,
            "audio_acceptance": audio_acceptance,
            "watermark_status": INITIAL_WATERMARK_STATUS,
            "watermark_evidence_manifest_sha256": trusted.bundle["watermark_evidence_manifest_sha256"],
            "live_watermark_documentation_scan_sha256": live_watermark_scan["report_sha256"],
            "profile_sha256": sha256_file(profile_path),
            "clean_worker_exit": "PARENT_MUST_CONFIRM_AFTER_EXIT",
            "failure_policy": FAILURE_STATUS,
        }
        manifest_path = attempt_dir / "worker_manifest_v2.json"; write_new_json(manifest_path, manifest)
        return {"status": manifest["status"], "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "profile_path": str(profile_path), "profile_sha256": sha256_file(profile_path)}
    except BaseException as exc:
        if rss_sampler is not None:
            try:
                rss_sampler.stop()
            except BaseException:
                pass
        if runtime is not None:
            try: runtime.unload()
            except BaseException: pass
        failure = {"schema": "qwen3_tts_original_voice_forge_worker_failure_v2", "status": FAILURE_STATUS, "utc": utc_now(), "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(), "network_boundary": NETWORK_BOUNDARY, "network_use_proven": False, "fallback": {"text_remains_available": True, "voice_audio": "SILENCE_NO_AUDIO", "generic_voice_used": False, "sapi_used": False, "other_person_voice_used": False, "current_voice_route_changed": False}}
        try: write_new_json(attempt_dir / "worker_failure_v2.json", failure)
        except FileExistsError: pass
        raise R2ForgeError(str(exc)) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--bundle-id")
    parser.add_argument("--attempt-dir")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute or not args.acknowledge_private_unreviewed:
        raise R2ForgeError("R2 worker is inert without exact execution acknowledgement")
    if not args.bundle_id or not args.attempt_dir:
        raise R2ForgeError("bundle ID and parent-reserved attempt are required")
    verify_independent_audit_harness(PROJECT_ROOT)
    trusted = load_trusted_bundle(PROJECT_ROOT, args.bundle_id, require_ready_environment=True)
    result = execute_verified_bundle(trusted=trusted, attempt_dir=Path(args.attempt_dir))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except R2ForgeError as exc:
        print(f"R2 Qwen3-TTS forge failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
