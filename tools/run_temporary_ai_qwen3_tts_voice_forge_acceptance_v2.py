"""Parent launcher for one trusted TemporaryAI Qwen3-TTS forge bundle.

The launcher is inert unless all explicit execution acknowledgements are
present.  The caller may select only an opaque bundle ID.  Authorization,
hashes, model locations, worker identity, and the output root come from fixed
project-controlled records.  This module deliberately never imports the
worker: the worker is started only after its exact hash and the trusted bundle
seal have been verified.

This revision uses Hugging Face offline flags but does not claim process-level
network denial.  It installs nothing, downloads nothing, plays nothing, and
does not alter any current voice route.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import traceback
import zipfile
from email.parser import BytesParser
from email.policy import default as email_policy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json")
HARNESS_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json")
REGISTRY_REL = Path("Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json")
BUNDLE_ROOT_REL = Path("TemporaryAI/voice_forge_acceptance_bundles_v2")
OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v2")
NONCE_LEDGER_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_nonce_ledger_v2")
ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
EVALUATION_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")
NETWORK_BOUNDARY = "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL"
ISOLATED_ROOT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2")
ISOLATED_VENV_REL = ISOLATED_ROOT_REL / ".venv"
WHEEL_EVIDENCE_ROOT_REL = ISOLATED_ROOT_REL / "wheel_evidence"
EVALUATOR_ROOT_REL = ISOLATED_ROOT_REL / "evaluators"
FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
HASH = re.compile(r"[0-9a-f]{64}")


class R2LauncherError(RuntimeError):
    """The v2 parent launcher failed closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise R2LauncherError(f"{label} is not a valid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise R2LauncherError(f"{label} must be explicitly UTC")
    return parsed


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise R2LauncherError(f"cannot read trusted JSON: {path}") from exc
    if not isinstance(value, dict):
        raise R2LauncherError(f"trusted JSON is not an object: {path}")
    return value


def write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(value)
    except FileExistsError as exc:
        raise R2LauncherError(f"append-only evidence already exists: {path}") from exc


def write_new_json(path: Path, value: Any) -> None:
    write_new(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def inside(root: Path, relative_value: str | Path, label: str) -> Path:
    root = root.resolve()
    value = Path(str(relative_value))
    if value.is_absolute():
        raise R2LauncherError(f"{label} must be project-relative")
    result = (root / value).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R2LauncherError(f"{label} escaped its trusted root") from exc
    return result


def relative(path: Path, root: Path | None = None) -> str:
    effective_root = PROJECT_ROOT if root is None else root
    return path.resolve().relative_to(effective_root.resolve()).as_posix()


def require_hash(value: Any, label: str) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text):
        raise R2LauncherError(f"{label} is not an exact SHA-256")
    return text


def verify_file(path: Path, expected: Any, label: str) -> None:
    expected_hash = require_hash(expected, label)
    if not path.is_file():
        raise R2LauncherError(f"{label} is missing")
    if sha256_file(path) != expected_hash:
        raise R2LauncherError(f"{label} hash mismatch")


def canonical_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def verify_record_file(package: str, row: dict[str, Any]) -> dict[str, Any]:
    site_packages = (PROJECT_ROOT / ISOLATED_VENV_REL / "Lib/site-packages").resolve()
    record_path = inside(PROJECT_ROOT, str(row.get("record_path") or ""), f"{package} RECORD")
    try:
        record_path.relative_to(site_packages)
    except ValueError as exc:
        raise R2LauncherError(f"{package} RECORD is outside the isolated environment") from exc
    if record_path.name != "RECORD" or not record_path.parent.name.lower().endswith(".dist-info"):
        raise R2LauncherError(f"{package} RECORD is not an installed dist-info RECORD")
    dist_name = canonical_distribution_name(record_path.parent.name[:-10])
    # A dist-info directory normally embeds version after the normalized name.
    if not dist_name.startswith(canonical_distribution_name(package)):
        raise R2LauncherError(f"{package} RECORD directory does not identify that package")
    verify_file(record_path, row.get("record_sha256"), f"{package} RECORD")
    with record_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise R2LauncherError(f"{package} RECORD is empty")
    record_relative = relative(record_path, site_packages)
    seen: set[str] = set()
    verified = 0
    verified_files: list[dict[str, Any]] = []
    for record_row in rows:
        if len(record_row) != 3:
            raise R2LauncherError(f"{package} RECORD row is malformed")
        rel, encoded_hash, declared_size = record_row
        rel = rel.replace("\\", "/")
        if not rel or rel in seen:
            raise R2LauncherError(f"{package} RECORD path is empty or duplicated")
        seen.add(rel)
        file_path = inside(site_packages, rel, f"{package} installed file")
        if rel == record_relative:
            if encoded_hash or declared_size:
                raise R2LauncherError(f"{package} RECORD self-row must be unhashed")
            verified_files.append({
                "path": relative(record_path),
                "bytes": record_path.stat().st_size,
                "sha256": sha256_file(record_path),
            })
            continue
        if not encoded_hash.startswith("sha256=") or not declared_size.isdigit():
            raise R2LauncherError(f"{package} RECORD contains an unattested installed file")
        if not file_path.is_file() or file_path.stat().st_size != int(declared_size):
            raise R2LauncherError(f"{package} installed file size/missing mismatch")
        encoded = encoded_hash.split("=", 1)[1]
        padding = "=" * ((4 - len(encoded) % 4) % 4)
        try:
            expected = base64.urlsafe_b64decode(encoded + padding).hex()
        except (ValueError, TypeError) as exc:
            raise R2LauncherError(f"{package} RECORD SHA-256 is invalid") from exc
        if sha256_file(file_path) != expected:
            raise R2LauncherError(f"{package} installed file hash mismatch")
        verified_files.append({
            "path": relative(file_path),
            "bytes": file_path.stat().st_size,
            "sha256": expected,
        })
        verified += 1
    if verified <= 0:
        raise R2LauncherError(f"{package} RECORD verified no installed files")
    return {
        "version": row.get("version"),
        "record_path": relative(record_path),
        "record_sha256": row.get("record_sha256"),
        "verified_file_count": verified,
        "files": verified_files,
    }


def verify_complete_site_packages_inventory(
    spec: dict[str, Any], distribution_evidence: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    site_packages = (PROJECT_ROOT / ISOLATED_VENV_REL / "Lib/site-packages").resolve()
    inventory_spec = spec.get("site_packages_inventory") or {}
    if (
        inventory_spec.get("status") != "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY"
        or inventory_spec.get("complete_file_inventory") is not True
        or inventory_spec.get("all_distributions_and_loose_files_declared") is not True
    ):
        raise R2LauncherError("complete site-packages inventory is not accepted")
    if inside(PROJECT_ROOT, inventory_spec.get("root", ""), "site-packages root") != site_packages:
        raise R2LauncherError("site-packages inventory root mismatch")
    manifest_path = inside(
        PROJECT_ROOT,
        inventory_spec.get("manifest_path", ""),
        "site-packages inventory manifest",
    )
    try:
        manifest_path.relative_to((PROJECT_ROOT / ISOLATED_ROOT_REL).resolve())
    except ValueError as exc:
        raise R2LauncherError("site-packages inventory manifest escaped the isolated sidecar") from exc
    verify_file(manifest_path, inventory_spec.get("manifest_sha256"), "site-packages inventory manifest")
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "qwen3_tts_complete_site_packages_inventory_v2"
        or manifest.get("status") != "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY"
        or manifest.get("complete_file_inventory") is not True
        or manifest.get("site_packages_root") != relative(site_packages)
    ):
        raise R2LauncherError("site-packages inventory manifest is incomplete")
    declared_distributions = manifest.get("distributions")
    if not isinstance(declared_distributions, list):
        raise R2LauncherError("site-packages distribution inventory is invalid")
    indexed_distributions: dict[str, dict[str, Any]] = {}
    for row in declared_distributions:
        name = str(row.get("name") or "") if isinstance(row, dict) else ""
        if not name or name in indexed_distributions:
            raise R2LauncherError("site-packages distribution row is invalid/duplicate")
        indexed_distributions[name] = row
    if set(indexed_distributions) != set(distribution_evidence):
        raise R2LauncherError("site-packages inventory omits a transitive distribution")
    for name, evidence in distribution_evidence.items():
        row = indexed_distributions[name]
        for key in ("version", "record_path", "record_sha256"):
            if row.get(key) != evidence.get(key):
                raise R2LauncherError(f"site-packages inventory {name} {key} mismatch")
    ownership: dict[str, set[str]] = {}
    expected_file_evidence: dict[str, dict[str, Any]] = {}
    for name, evidence in distribution_evidence.items():
        for row in evidence["files"]:
            path = inside(PROJECT_ROOT, row["path"], f"{name} attested installed file")
            rel = relative(path, site_packages)
            ownership.setdefault(rel, set()).add(name)
            prior = expected_file_evidence.setdefault(rel, row)
            if prior["bytes"] != row["bytes"] or prior["sha256"] != row["sha256"]:
                raise R2LauncherError("overlapping distribution file evidence conflicts")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise R2LauncherError("site-packages inventory has no exact files")
    declared: set[str] = set()
    verified_rows: list[dict[str, Any]] = []
    for row in rows:
        rel = str(row.get("path") or "") if isinstance(row, dict) else ""
        if not rel or rel in declared:
            raise R2LauncherError("site-packages file row is invalid/duplicate")
        declared.add(rel)
        path = inside(site_packages, rel, "site-packages inventory file")
        verify_file(path, row.get("sha256"), f"site-packages inventory file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2LauncherError("site-packages inventory file size mismatch")
        owners = row.get("owner_distributions")
        if not isinstance(owners, list) or set(owners) != ownership.get(rel, set()):
            raise R2LauncherError("site-packages file ownership binding mismatch")
        if bool(row.get("loose_unowned_file")) != (not owners):
            raise R2LauncherError("site-packages loose-file declaration mismatch")
        if rel in expected_file_evidence:
            expected = expected_file_evidence[rel]
            if row.get("bytes") != expected["bytes"] or row.get("sha256") != expected["sha256"]:
                raise R2LauncherError("site-packages RECORD/inventory file mismatch")
        verified_rows.append({
            "path": relative(path), "bytes": row["bytes"], "sha256": row["sha256"],
            "owner_distributions": sorted(owners), "loose_unowned_file": not owners,
        })
    actual = {relative(path, site_packages) for path in site_packages.rglob("*") if path.is_file()}
    if actual != declared or not set(expected_file_evidence).issubset(declared):
        raise R2LauncherError("site-packages complete inventory drift")
    return {
        "manifest_path": relative(manifest_path),
        "manifest_sha256": inventory_spec["manifest_sha256"],
        "complete_file_inventory": True,
        "all_transitive_distributions_declared": True,
        "all_loose_files_declared": True,
        "files": verified_rows,
    }


def verify_wheel_archive(package: str, row: dict[str, Any]) -> dict[str, Any]:
    wheel_root = (PROJECT_ROOT / WHEEL_EVIDENCE_ROOT_REL).resolve()
    wheel_path = inside(PROJECT_ROOT, str(row.get("wheel_evidence_path") or ""), f"{package} wheel evidence")
    try:
        wheel_path.relative_to(wheel_root)
    except ValueError as exc:
        raise R2LauncherError(f"{package} wheel escaped the fixed evidence root") from exc
    if wheel_path.name != row.get("wheel_filename") or wheel_path.suffix.lower() != ".whl":
        raise R2LauncherError(f"{package} wheel filename/path mismatch")
    verify_file(wheel_path, row.get("wheel_sha256"), f"{package} exact wheel evidence")
    filename_parts = wheel_path.name[:-4].split("-")
    if len(filename_parts) < 5 or canonical_distribution_name(filename_parts[0]) != canonical_distribution_name(package) or filename_parts[1] != row.get("version"):
        raise R2LauncherError(f"{package} wheel filename package/version mismatch")
    try:
        with zipfile.ZipFile(wheel_path, "r") as archive:
            names = archive.namelist()
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            record_names = [name for name in names if name.endswith(".dist-info/RECORD")]
            if len(metadata_names) != 1 or len(record_names) != 1:
                raise R2LauncherError(f"{package} wheel lacks unique METADATA/RECORD")
            metadata = BytesParser(policy=email_policy).parsebytes(archive.read(metadata_names[0]))
            if canonical_distribution_name(str(metadata.get("Name") or "")) != canonical_distribution_name(package) or str(metadata.get("Version") or "") != row.get("version"):
                raise R2LauncherError(f"{package} wheel METADATA mismatch")
            record_rows = list(csv.reader(io.StringIO(archive.read(record_names[0]).decode("utf-8"))))
            seen: set[str] = set()
            verified = 0
            for record_row in record_rows:
                if len(record_row) != 3:
                    raise R2LauncherError(f"{package} wheel RECORD row is malformed")
                name, encoded_hash, declared_size = record_row
                if not name or name in seen or name not in names:
                    raise R2LauncherError(f"{package} wheel RECORD inventory is invalid")
                seen.add(name)
                if name == record_names[0]:
                    if encoded_hash or declared_size:
                        raise R2LauncherError(f"{package} wheel RECORD self-row must be unhashed")
                    continue
                if not encoded_hash.startswith("sha256=") or not declared_size.isdigit():
                    raise R2LauncherError(f"{package} wheel contains an unattested member")
                payload = archive.read(name)
                encoded = encoded_hash.split("=", 1)[1]
                padding = "=" * ((4 - len(encoded) % 4) % 4)
                expected = base64.urlsafe_b64decode(encoded + padding).hex()
                if len(payload) != int(declared_size) or sha256_bytes(payload) != expected:
                    raise R2LauncherError(f"{package} wheel member hash/size mismatch")
                verified += 1
            if set(names) != seen or verified <= 0:
                raise R2LauncherError(f"{package} wheel RECORD is incomplete")
    except (OSError, zipfile.BadZipFile, UnicodeError, csv.Error, ValueError) as exc:
        raise R2LauncherError(f"{package} wheel is not a valid exact archive: {exc}") from exc
    return {"wheel_path": relative(wheel_path), "verified_members": verified}


def verify_local_model_manifest(
    *, model_path: Path, manifest_path: Path, expected_hash: Any,
    engine: Any, version: Any, label: str,
) -> None:
    evaluator_root = (PROJECT_ROOT / EVALUATOR_ROOT_REL).resolve()
    for path in (model_path, manifest_path):
        try:
            path.relative_to(evaluator_root)
        except ValueError as exc:
            raise R2LauncherError(f"{label} escaped the fixed evaluator root") from exc
    if manifest_path.parent.resolve() != model_path.resolve():
        raise R2LauncherError(f"{label} manifest is outside its exact local model")
    verify_file(manifest_path, expected_hash, f"{label} manifest")
    payload = read_json(manifest_path)
    if payload.get("schema") != "qwen3_tts_local_evaluator_model_manifest_v2" or payload.get("complete_file_inventory") is not True:
        raise R2LauncherError(f"{label} manifest is incomplete")
    if payload.get("engine") != engine or payload.get("version") != version:
        raise R2LauncherError(f"{label} evaluator engine/version mismatch")
    rows = payload.get("files")
    if not isinstance(rows, list) or not rows:
        raise R2LauncherError(f"{label} manifest has no files")
    declared: set[str] = set()
    for row in rows:
        rel = str(row.get("path") or "") if isinstance(row, dict) else ""
        if not rel or rel in declared:
            raise R2LauncherError(f"{label} manifest file row is invalid")
        declared.add(rel)
        path = inside(model_path, rel, f"{label} model file")
        verify_file(path, row.get("sha256"), f"{label} model file")
        if path.stat().st_size != row.get("bytes"):
            raise R2LauncherError(f"{label} model file size mismatch")
    actual = {relative(path, model_path) for path in model_path.rglob("*") if path.is_file() and path.resolve() != manifest_path.resolve()}
    if actual != declared:
        raise R2LauncherError(f"{label} manifest is not a complete model inventory")


def reserve_attempt(bundle_id: str) -> Path:
    if not SAFE_ID.fullmatch(bundle_id):
        raise R2LauncherError("bundle ID is not a safe opaque ID")
    candidate_root = (PROJECT_ROOT / OUTPUT_ROOT_REL / bundle_id).resolve()
    candidate_root.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        attempt = candidate_root / f"attempt_{number:02d}"
        try:
            attempt.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return attempt
    raise R2LauncherError("no append-only R2 attempt slot remains")


def preserve_preflight_failure(attempt: Path, exc: BaseException, stage: str) -> None:
    evidence = {
        "schema": "qwen3_tts_voice_forge_parent_preflight_failure_v2",
        "status": FAILURE_STATUS,
        "utc": utc_now(),
        "stage": stage,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "attempt": relative(attempt),
        "network_boundary": NETWORK_BOUNDARY,
        "network_nonuse_proven": False,
        "worker_started": False,
        "model_loaded": False,
        "audio_generated": False,
        "fallback": {
            "text_remains_available": True,
            "voice_audio": "SILENCE_NO_AUDIO",
            "generic_voice_used": False,
            "sapi_used": False,
            "other_person_voice_used": False,
            "current_voice_route_changed": False,
        },
    }
    try:
        write_new_json(attempt / "parent_preflight_failure_v2.json", evidence)
    except R2LauncherError:
        pass


def preserve_started_or_post_failure(attempt: Path, exc: BaseException, stage: str) -> None:
    evidence = {
        "schema": "qwen3_tts_voice_forge_parent_started_or_post_failure_v2",
        "status": FAILURE_STATUS,
        "utc": utc_now(),
        "stage": stage,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "attempt": relative(attempt),
        "worker_start_attempted": True,
        "clean_worker_exit_and_acceptance_confirmed": False,
        "network_boundary": NETWORK_BOUNDARY,
        "network_nonuse_proven": False,
        "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
    }
    try:
        write_new_json(attempt / "parent_started_or_post_failure_v2.json", evidence)
    except R2LauncherError:
        pass


def verify_harness_manifest() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    manifest_path = (PROJECT_ROOT / HARNESS_MANIFEST_REL).resolve()
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "qwen3_tts_voice_forge_harness_manifest_v2" or manifest.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN":
        raise R2LauncherError("fixed harness has not passed the required independent audit")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise R2LauncherError("harness manifest file inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in records:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R2LauncherError("harness manifest row is invalid")
        rel = str(row["path"])
        if rel in indexed:
            raise R2LauncherError("harness manifest contains duplicate paths")
        path = inside(PROJECT_ROOT, rel, "harness file")
        verify_file(path, row.get("sha256"), f"harness file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2LauncherError(f"harness file size mismatch: {rel}")
        indexed[rel] = row
    required = {
        CONTRACT_REL.as_posix(), ENVIRONMENT_REL.as_posix(), WORKER_REL.as_posix(),
        RUNNER_REL.as_posix(), REGISTRY_REL.as_posix(), EVALUATION_CORPUS_REL.as_posix(),
    }
    if not required.issubset(indexed):
        raise R2LauncherError("harness manifest omits a controlling file")
    contract = read_json(PROJECT_ROOT / CONTRACT_REL)
    environment = read_json(PROJECT_ROOT / ENVIRONMENT_REL)
    worker_path = (PROJECT_ROOT / WORKER_REL).resolve()
    return manifest, contract, environment, worker_path


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


def validate_owner_authorization_before_nonce(
    *, bundle_dir: Path, declared: set[str], bundle: dict[str, Any]
) -> dict[str, Any]:
    """Resolve and validate the exact sealed owner grant before nonce use.

    This duplicate parent-side gate is intentional: a malformed, expired, or
    revoked owner grant must never consume the single-use queue nonce merely
    because the child worker would reject it later.
    """

    authorization_path = inside(
        bundle_dir,
        str(bundle.get("owner_authorization_path") or ""),
        "owner authorization",
    )
    authorization_rel = relative(authorization_path, bundle_dir)
    if authorization_rel not in declared:
        raise R2LauncherError("owner authorization is not in the trusted bundle seal")
    verify_file(
        authorization_path,
        bundle.get("owner_authorization_sha256"),
        "owner authorization",
    )
    owner = read_json(authorization_path)
    if owner.get("schema") != "qwen3_tts_original_voice_forge_owner_authorization_v2":
        raise R2LauncherError("owner authorization schema mismatch")
    if owner.get("status") != "OWNER_AUTHORIZED_SINGLE_USE" or owner.get("owner_id") != "robert":
        raise R2LauncherError("owner authorization is not active and exact")
    if owner.get("single_use") is not True or owner.get("revoked") is not False:
        raise R2LauncherError("owner authorization is revoked or not single-use")
    if owner.get("authorized_scope") != "ONE_PRIVATE_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_V2":
        raise R2LauncherError("owner authorization scope mismatch")
    for key in (
        "bundle_id", "candidate_id", "opaque_voice_id", "ai_type",
        "single_use_nonce_sha256", "queue_binding_sha256", "job_sha256",
        "canonical_profile_sha256", "canonical_creation_request_sha256",
        "identity_clearance_manifest_sha256", "watermark_evidence_manifest_sha256",
        "evaluation_corpus_sha256", "voice_design_model_manifest_sha256",
        "base_model_manifest_sha256", "environment_spec_sha256",
    ):
        if owner.get(key) != bundle.get(key):
            raise R2LauncherError(f"owner authorization {key} mismatch")
    now = datetime.now(timezone.utc)
    if parse_utc(owner.get("authorized_utc"), "authorized_utc") > now:
        raise R2LauncherError("owner authorization is from the future")
    if parse_utc(owner.get("expires_utc"), "expires_utc") <= now:
        raise R2LauncherError("owner authorization expired")
    return owner


def verify_bundle_envelope(bundle_id: str) -> tuple[dict[str, Any], dict[str, Any], Path]:
    registry = read_json(PROJECT_ROOT / REGISTRY_REL)
    if registry.get("schema") != "temporaryai_qwen3_tts_voice_forge_bundle_registry_v2":
        raise R2LauncherError("trusted registry schema mismatch")
    entries = [row for row in registry.get("append_only_entries", []) if isinstance(row, dict) and row.get("bundle_id") == bundle_id]
    if len(entries) != 1 or entries[0].get("status") != "OWNER_AUTHORIZED_SINGLE_USE":
        raise R2LauncherError("bundle has no unique owner-authorized registry entry")
    entry = entries[0]
    bundle_root = (PROJECT_ROOT / BUNDLE_ROOT_REL).resolve()
    bundle_dir = inside(bundle_root, bundle_id, "trusted bundle")
    seal_path = bundle_dir / "BUNDLE_SEAL.json"
    verify_file(seal_path, entry.get("bundle_seal_sha256"), "trusted bundle seal")
    seal = read_json(seal_path)
    if seal.get("schema") != "qwen3_tts_original_voice_forge_bundle_seal_v2" or seal.get("bundle_id") != bundle_id:
        raise R2LauncherError("bundle seal identity mismatch")
    files = seal.get("files")
    if not isinstance(files, list):
        raise R2LauncherError("bundle seal inventory is invalid")
    declared: set[str] = set()
    for row in files:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R2LauncherError("bundle seal row is invalid")
        rel = str(row["path"])
        if rel == "BUNDLE_SEAL.json" or rel in declared:
            raise R2LauncherError("bundle seal duplicate/recursive path")
        declared.add(rel)
        path = inside(bundle_dir, rel, "sealed bundle file")
        verify_file(path, row.get("sha256"), f"sealed bundle file {rel}")
        if path.stat().st_size != row.get("bytes"):
            raise R2LauncherError(f"sealed bundle file size mismatch: {rel}")
    actual = {relative(path, bundle_dir) for path in bundle_dir.rglob("*") if path.is_file() and path.name != "BUNDLE_SEAL.json"}
    if actual != declared:
        raise R2LauncherError("bundle seal is not a complete inventory")
    acceptance_path = bundle_dir / "acceptance_bundle.json"
    if "acceptance_bundle.json" not in declared:
        raise R2LauncherError("sealed acceptance bundle is missing")
    verify_file(acceptance_path, seal.get("acceptance_bundle_sha256"), "acceptance bundle")
    bundle = read_json(acceptance_path)
    if bundle.get("schema") != "qwen3_tts_original_voice_forge_acceptance_bundle_v2" or bundle.get("status") != "OWNER_AUTHORIZED_SINGLE_USE":
        raise R2LauncherError("acceptance bundle is not active")
    if bundle.get("bundle_id") != bundle_id or bundle.get("queue_kind") != "TEMPORARYAI_ORIGINAL_VOICE_FORGE_PRIVATE_ACCEPTANCE_V2":
        raise R2LauncherError("acceptance bundle queue identity mismatch")
    nonce_hash = require_hash(bundle.get("single_use_nonce_sha256"), "single-use nonce")
    if sha256_text(str(bundle.get("single_use_nonce") or "")) != nonce_hash:
        raise R2LauncherError("single-use nonce hash mismatch")
    binding_hash = require_hash(bundle.get("queue_binding_sha256"), "queue binding")
    if sha256_bytes(canonical_bytes(queue_binding_payload(bundle))) != binding_hash:
        raise R2LauncherError("queue binding mismatch")
    for key in (
        "candidate_id", "ai_type", "opaque_voice_id", "single_use_nonce_sha256",
        "queue_binding_sha256", "canonical_profile_sha256",
        "canonical_creation_request_sha256", "job_sha256",
        "owner_authorization_sha256",
        "identity_clearance_manifest_sha256", "watermark_evidence_manifest_sha256",
        "evaluation_corpus_sha256", "voice_design_model_manifest_sha256",
        "base_model_manifest_sha256", "environment_spec_sha256",
    ):
        if entry.get(key) != bundle.get(key):
            raise R2LauncherError(f"trusted registry {key} mismatch")
    validate_owner_authorization_before_nonce(
        bundle_dir=bundle_dir,
        declared=declared,
        bundle=bundle,
    )
    return bundle, entry, bundle_dir


def validate_ready_environment(contract: dict[str, Any], environment: dict[str, Any], worker_path: Path) -> Path:
    if contract.get("contract_id") != "temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2" or contract.get("version") != 2:
        raise R2LauncherError("fixed v2 contract identity mismatch")
    execution = contract.get("execution") or {}
    if execution.get("network_boundary") != NETWORK_BOUNDARY or execution.get("only_bundle_id_is_caller_selectable") is not True:
        raise R2LauncherError("contract network/caller boundary mismatch")
    if execution.get("worker_import_before_hash_and_bundle_verification_allowed") is not False:
        raise R2LauncherError("contract permits premature worker import")
    if execution.get("independent_audit_required_before_run") is not True:
        raise R2LauncherError("contract no longer requires independent audit")
    if environment.get("environment_id") != "qwen3_tts_voice_forge_isolated_windows_blackwell_v2" or environment.get("status") != "ACCEPTED_READY_FOR_ONE_BOUNDED_RUN":
        raise R2LauncherError("isolated v2 environment is not accepted ready")
    if environment.get("network_boundary") != NETWORK_BOUNDARY:
        raise R2LauncherError("environment overstates its network boundary")
    distributions = environment.get("distributions") or {}
    pins = {key: (distributions.get(key) or {}).get("version") for key in ("qwen-tts", "transformers", "accelerate")}
    if pins != {"qwen-tts": "0.1.1", "transformers": "4.57.3", "accelerate": "1.12.0"}:
        raise R2LauncherError("core package pins changed")
    python = environment.get("python") or {}
    python_path = inside(PROJECT_ROOT, str(python.get("executable_path") or ""), "isolated Python")
    verify_file(python_path, python.get("executable_sha256"), "isolated Python")
    if python_path != (PROJECT_ROOT / ISOLATED_VENV_REL / "Scripts/python.exe").resolve():
        raise R2LauncherError("isolated Python is not the fixed dedicated v2 executable")
    mandatory_packages = {
        "qwen-tts", "transformers", "accelerate", "torch", "torchaudio",
        "faster-whisper", "speechbrain",
    }
    if not mandatory_packages.issubset(distributions):
        raise R2LauncherError("mandatory runtime distributions are missing")
    distribution_evidence: dict[str, dict[str, Any]] = {}
    for package, row in sorted(distributions.items()):
        if not isinstance(row, dict):
            raise R2LauncherError(f"{package} distribution row is invalid")
        if not str(row.get("version") or ""):
            raise R2LauncherError(f"{package} version is missing")
        distribution_evidence[package] = verify_record_file(package, row)
    verify_complete_site_packages_inventory(environment, distribution_evidence)
    for package in ("torch", "torchaudio"):
        row = distributions[package]
        if not str(row.get("wheel_filename") or "").endswith(".whl"):
            raise R2LauncherError(f"{package} exact wheel filename is missing")
        verify_wheel_archive(package, row)
    cuda = environment.get("cuda") or {}
    if cuda.get("device_name") != "NVIDIA GeForce RTX 5060 Ti" or cuda.get("compute_capability") != [12, 0] or cuda.get("required_arch") != "sm_120":
        raise R2LauncherError("exact Blackwell device/capability/architecture spec mismatch")
    if not str(cuda.get("torch_cuda_build") or ""):
        raise R2LauncherError("exact Torch CUDA build is missing")
    runtime = environment.get("runtime") or {}
    if runtime.get("ordinary_eager_cuda") is not True or runtime.get("attention_implementation") != "sdpa" or runtime.get("torch_compile") is not False:
        raise R2LauncherError("runtime is not ordinary eager/SDPA")
    evaluators = environment.get("speech_evaluators") or {}
    if evaluators.get("status") != "ACCEPTED_EXACT_LOCAL_ASR_SPEECH_AND_SPEAKER_EMBEDDING":
        raise R2LauncherError("real local ASR/speech/speaker evaluators are not accepted")
    for prefix, engine_key, version_key in (
        ("asr", "asr_engine", "asr_version"),
        ("speaker", "speaker_embedding_engine", "speaker_embedding_version"),
        ("speech_classifier", "speech_classifier_engine", "speech_classifier_version"),
    ):
        model_path = inside(PROJECT_ROOT, str(evaluators.get(f"{prefix}_model_path") or ""), f"{prefix} evaluator model")
        manifest_path = inside(PROJECT_ROOT, str(evaluators.get(f"{prefix}_model_manifest_path") or ""), f"{prefix} evaluator manifest")
        verify_local_model_manifest(
            model_path=model_path,
            manifest_path=manifest_path,
            expected_hash=evaluators.get(f"{prefix}_model_manifest_sha256"),
            engine=evaluators.get(engine_key),
            version=evaluators.get(version_key),
            label=f"{prefix} evaluator",
        )
    classifier_adapter = inside(PROJECT_ROOT, str(evaluators.get("speech_classifier_adapter_path") or ""), "speech classifier adapter")
    try:
        classifier_adapter.relative_to((PROJECT_ROOT / EVALUATOR_ROOT_REL).resolve())
    except ValueError as exc:
        raise R2LauncherError("speech classifier adapter escaped the fixed evaluator root") from exc
    verify_file(classifier_adapter, evaluators.get("speech_classifier_adapter_sha256"), "speech classifier adapter")
    identity = environment.get("identity_analyzer") or {}
    if identity.get("status") != "ACCEPTED_EXACT_LOCAL_NER_AND_IMITATION_ANALYZER":
        raise R2LauncherError("real local identity analyzer is not accepted")
    adapter = inside(PROJECT_ROOT, str(identity.get("adapter_path") or ""), "identity analyzer adapter")
    try:
        adapter.relative_to((PROJECT_ROOT / EVALUATOR_ROOT_REL).resolve())
    except ValueError as exc:
        raise R2LauncherError("identity analyzer adapter escaped the fixed evaluator root") from exc
    verify_file(adapter, identity.get("adapter_sha256"), "identity analyzer adapter")
    identity_model = inside(PROJECT_ROOT, str(identity.get("model_path") or ""), "identity analyzer model")
    identity_manifest = inside(PROJECT_ROOT, str(identity.get("model_manifest_path") or ""), "identity analyzer model manifest")
    verify_local_model_manifest(
        model_path=identity_model,
        manifest_path=identity_manifest,
        expected_hash=identity.get("model_manifest_sha256"),
        engine=identity.get("engine"),
        version=identity.get("version"),
        label="identity analyzer",
    )
    if worker_path != (PROJECT_ROOT / WORKER_REL).resolve():
        raise R2LauncherError("verified worker is not the fixed v2 worker")
    return python_path


def consume_nonce(bundle: dict[str, Any], attempt: Path) -> tuple[Path, str]:
    ledger_root = (PROJECT_ROOT / NONCE_LEDGER_REL).resolve()
    ledger_path = ledger_root / f"{bundle['single_use_nonce_sha256']}.json"
    evidence = {
        "schema": "qwen3_tts_voice_forge_single_use_nonce_ledger_v2",
        "status": "CONSUMED_FOR_EXACT_QUEUE_ATTEMPT",
        "utc": utc_now(),
        "bundle_id": bundle["bundle_id"],
        "candidate_id": bundle["candidate_id"],
        "opaque_voice_id": bundle["opaque_voice_id"],
        "ai_type": bundle["ai_type"],
        "single_use_nonce_sha256": bundle["single_use_nonce_sha256"],
        "queue_binding_sha256": bundle["queue_binding_sha256"],
        "job_sha256": bundle["job_sha256"],
        "canonical_profile_sha256": bundle["canonical_profile_sha256"],
        "canonical_creation_request_sha256": bundle["canonical_creation_request_sha256"],
        "identity_clearance_manifest_sha256": bundle["identity_clearance_manifest_sha256"],
        "watermark_evidence_manifest_sha256": bundle["watermark_evidence_manifest_sha256"],
        "evaluation_corpus_sha256": bundle["evaluation_corpus_sha256"],
        "voice_design_model_manifest_sha256": bundle["voice_design_model_manifest_sha256"],
        "base_model_manifest_sha256": bundle["base_model_manifest_sha256"],
        "environment_spec_sha256": bundle["environment_spec_sha256"],
        "attempt": relative(attempt),
    }
    write_new_json(ledger_path, evidence)
    return ledger_path, sha256_file(ledger_path)


def restricted_child_environment(*, isolated_python: Path) -> dict[str, str]:
    allowed = (
        "USERNAME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA",
        "APPDATA", "SYSTEMROOT", "WINDIR",
    )
    env = {key: os.environ[key] for key in allowed if os.environ.get(key)}
    windows = Path(env.get("WINDIR") or env.get("SYSTEMROOT") or r"C:\Windows")
    cache_root = PROJECT_ROOT / "RecoverySprint/runtime_cache/qwen3_tts_voice_forge_v2"
    temp = cache_root / "temp"
    hf_cache = cache_root / "huggingface"
    torch_cache = cache_root / "torch"
    for path in (temp, hf_cache, torch_cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update({
        "PATH": os.pathsep.join((str(isolated_python.parent), str(windows / "System32"), str(windows))),
        "TEMP": str(temp), "TMP": str(temp), "HF_HOME": str(hf_cache),
        "TORCH_HOME": str(torch_cache), "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
        "CUDA_VISIBLE_DEVICES": "0", "TOKENIZERS_PARALLELISM": "false",
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "NO_PROXY": "localhost,127.0.0.1,::1",
    })
    return env


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.execute:
        raise R2LauncherError("R2 launcher is inert without --execute")
    if not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise R2LauncherError("both bounded execution acknowledgements are required")
    if not args.bundle_id or not SAFE_ID.fullmatch(args.bundle_id):
        raise R2LauncherError("one safe opaque --bundle-id is required")

    attempt = reserve_attempt(args.bundle_id)
    stage = "HARNESS_MANIFEST"
    worker_started = False
    try:
        harness_manifest, contract, environment, worker_path = verify_harness_manifest()
        stage = "TRUSTED_BUNDLE_ENVELOPE"
        bundle, _entry, _bundle_dir = verify_bundle_envelope(args.bundle_id)
        stage = "ISOLATED_ENVIRONMENT"
        isolated_python = validate_ready_environment(contract, environment, worker_path)
        stage = "SINGLE_USE_NONCE"
        ledger_path, ledger_hash = consume_nonce(bundle, attempt)
        reservation = {
            "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
            "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
            "utc": utc_now(),
            "bundle_id": args.bundle_id,
            "candidate_id": bundle["candidate_id"],
            "opaque_voice_id": bundle["opaque_voice_id"],
            "queue_binding_sha256": bundle["queue_binding_sha256"],
            **queue_binding_payload(bundle),
            "attempt": relative(attempt),
            "nonce_ledger_path": relative(ledger_path),
            "nonce_ledger_sha256": ledger_hash,
            "verified_worker_path": relative(worker_path),
            "verified_worker_sha256": sha256_file(worker_path),
            "harness_manifest_sha256": sha256_file(PROJECT_ROOT / HARNESS_MANIFEST_REL),
            "contract_sha256": sha256_file(PROJECT_ROOT / CONTRACT_REL),
            "environment_spec_sha256": sha256_file(PROJECT_ROOT / ENVIRONMENT_REL),
            "trusted_registry_sha256": sha256_file(PROJECT_ROOT / REGISTRY_REL),
            "bundle_seal_sha256": require_hash(_entry.get("bundle_seal_sha256"), "trusted bundle seal"),
            "network_boundary": NETWORK_BOUNDARY,
            "network_nonuse_proven": False,
        }
        write_new_json(attempt / "parent_reservation.json", reservation)
        command = [
            str(isolated_python), "-I", "-B", str(worker_path), "--execute",
            "--bundle-id", args.bundle_id, "--attempt-dir", str(attempt),
            "--acknowledge-private-unreviewed",
        ]
        stage = "WORKER_PROCESS"
        started = time.perf_counter()
        worker_started = True
        try:
            completed = subprocess.run(
                command, cwd=str(PROJECT_ROOT), env=restricted_child_environment(isolated_python=isolated_python),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=1800, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            write_new_json(attempt / "parent_timeout_v2.json", {
                "schema": "qwen3_tts_voice_forge_parent_failure_v2", "status": FAILURE_STATUS,
                "reason": "WORKER_TIMEOUT", "timeout_seconds": 1800, "clean_worker_exit": False,
                "network_boundary": NETWORK_BOUNDARY, "network_nonuse_proven": False,
                "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
            })
            raise R2LauncherError("verified worker timed out") from exc
        elapsed = time.perf_counter() - started
        write_new(attempt / "worker_stdout_v2.log", completed.stdout)
        write_new(attempt / "worker_stderr_v2.log", completed.stderr)
        if completed.returncode != 0:
            write_new_json(attempt / "parent_worker_failure_v2.json", {
                "schema": "qwen3_tts_voice_forge_parent_failure_v2", "status": FAILURE_STATUS,
                "worker_returncode": completed.returncode, "worker_process_seconds": elapsed,
                "clean_worker_exit": False, "network_boundary": NETWORK_BOUNDARY,
                "network_nonuse_proven": False,
                "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
            })
            raise R2LauncherError(f"verified worker failed closed with return code {completed.returncode}")
        manifest_path = attempt / "worker_manifest_v2.json"
        profile_path = attempt / "voice_profile_candidate_v2.json"
        worker_manifest = read_json(manifest_path)
        profile = read_json(profile_path)
        if worker_manifest.get("status") != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT":
            raise R2LauncherError("worker manifest did not pass every engineering gate")
        if profile.get("assignment_allowed") is not False or profile.get("owner_hearing_acceptance") != "PENDING":
            raise R2LauncherError("candidate profile overstated assignment/owner acceptance")
        if worker_manifest.get("watermark_status") != "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK":
            raise R2LauncherError("worker overstated watermark evidence")
        summary = {
            "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v2",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
            "bundle_id": args.bundle_id,
            "candidate_id": bundle["candidate_id"],
            "opaque_voice_id": bundle["opaque_voice_id"],
            "attempt": relative(attempt),
            "worker_returncode": 0,
            "worker_process_seconds": elapsed,
            "clean_worker_exit": True,
            "worker_manifest_sha256": sha256_file(manifest_path),
            "voice_profile_candidate_sha256": sha256_file(profile_path),
            "owner_hearing_acceptance": "PENDING",
            "independent_audit": "REQUIRED",
            "watermark_status": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
            "network_boundary": NETWORK_BOUNDARY,
            "network_nonuse_proven": False,
            "activation_assignment_publication_or_upload_allowed": False,
            "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
        }
        write_new_json(attempt / "parent_acceptance_v2.json", summary)
        return {**summary, "parent_acceptance_sha256": sha256_file(attempt / "parent_acceptance_v2.json")}
    except BaseException as exc:
        if not worker_started:
            preserve_preflight_failure(attempt, exc, stage)
        else:
            preserve_started_or_post_failure(attempt, exc, stage)
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--bundle-id")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    parser.add_argument("--acknowledge-no-download", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except R2LauncherError as exc:
        print(f"R2 Qwen3-TTS forge launcher failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
