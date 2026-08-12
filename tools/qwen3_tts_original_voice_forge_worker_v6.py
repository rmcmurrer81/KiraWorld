"""Inert R6 worker for the TemporaryAI Qwen3-TTS original voice forge.

The worker performs its own exclusive one-use launch claim before importing
any predecessor worker or model dependency.  The shipped authorization is
disabled, so this file cannot start a real run as sealed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R6_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json")
R6_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r6_guards.py")
R6_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v6.py")
R6_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py")
R5_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json")
R5_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r5_guards.py")
R5_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v5.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R4_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v4.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_MANIFEST_NAME = "worker_manifest_v2.json"
R5_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_20260809.md"
)
R5_AUDIT_SHA256 = "82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a"
CLAIM_ROOT_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_worker_launch_claims_v6")
RESERVATION_ROOT_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v6")
AUTH_ROOT_PREFIX = "Data/voice/authorizations/qwen3_tts_voice_forge_v6/"
HASH = re.compile(r"[0-9a-f]{64}")

R6_REQUIRED_PAYLOADS = {
    "tools/qwen3_tts_voice_forge_r6_guards.py",
    "tools/qwen3_tts_original_voice_forge_worker_v6.py",
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py",
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json",
    "tools/qwen3_tts_voice_forge_r5_guards.py",
    "tools/qwen3_tts_original_voice_forge_worker_v5.py",
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py",
    "tools/qwen3_tts_voice_forge_r4_guards.py",
    "tools/qwen3_tts_original_voice_forge_worker_v4.py",
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py",
    "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json",
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R4_INDEPENDENT_AUDIT_20260809.md",
    "tools/qwen3_tts_voice_forge_r3_guards.py",
    "tools/qwen3_tts_original_voice_forge_worker_v3.py",
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py",
    "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json",
    "tools/qwen3_tts_original_voice_forge_worker_v2.py",
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py",
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json",
    "Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json",
    "Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json",
    "Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json",
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_20260809.md",
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_REPAIR_BOUNDARY_20260810.md",
}


class R6ForgeError(RuntimeError):
    """The R6 worker failed closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R6ForgeError(f"duplicate bootstrap JSON key: {key}")
        result[key] = value
    return result


def _object(path: Path, expected_hash: str | None, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise R6ForgeError(f"{label} is missing or unsafe")
    payload = path.read_bytes()
    if expected_hash is not None:
        if not HASH.fullmatch(str(expected_hash or "")) or sha256_bytes(payload) != expected_hash:
            raise R6ForgeError(f"{label} differs from its exact hash")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R6ForgeError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R6ForgeError(f"{label} is not an object")
    return value


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R6ForgeError("R6 bootstrap path escaped project") from exc


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise R6ForgeError("R6 worker one-use launch claim already exists") from exc


def bootstrap_external_trust(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Verify payload and external authority using only this entry source."""

    manifest = _object(
        PROJECT_ROOT / R6_PAYLOAD_REL,
        args.payload_manifest_sha256,
        "R6 worker bootstrap payload",
    )
    if (
        set(manifest)
        != {
            "schema", "status", "execution_allowed", "self_authorization_allowed",
            "revision", "predecessor_payload_manifest_path",
            "predecessor_payload_manifest_sha256", "rejected_r5_audit_path",
            "rejected_r5_audit_sha256", "files",
        }
        or manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v6"
        or manifest.get("status")
        != "IMMUTABLE_STATIC_PAYLOAD_REQUIRES_FRESH_AUDIT_AND_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
        or manifest.get("predecessor_payload_manifest_path") != R5_PAYLOAD_REL.as_posix()
        or manifest.get("rejected_r5_audit_path") != R5_AUDIT_REL.as_posix()
        or manifest.get("rejected_r5_audit_sha256") != R5_AUDIT_SHA256
        or sha256_file(PROJECT_ROOT / R5_AUDIT_REL) != R5_AUDIT_SHA256
    ):
        raise R6ForgeError("R6 worker bootstrap payload is self-authorizing or unbound")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R6ForgeError("R6 worker payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R6ForgeError("R6 worker payload row is not exact")
        rel = str(row.get("path") or "")
        path = (PROJECT_ROOT / rel).resolve()
        if rel in indexed or rel == R6_PAYLOAD_REL.as_posix() or _relative(path) != rel:
            raise R6ForgeError("R6 worker payload row is duplicate or unsafe")
        if (
            not path.is_file() or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or not HASH.fullmatch(str(row.get("sha256") or ""))
            or sha256_file(path) != row.get("sha256")
        ):
            raise R6ForgeError(f"R6 worker payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != R6_REQUIRED_PAYLOADS:
        raise R6ForgeError("R6 worker payload inventory is not the exact sealed set")

    authorization_path = Path(args.execution_authorization).resolve()
    auth_rel = _relative(authorization_path)
    if not auth_rel.startswith(AUTH_ROOT_PREFIX):
        raise R6ForgeError("R6 worker authorization root mismatch")
    authorization = _object(
        authorization_path,
        args.execution_authorization_sha256,
        "R6 worker bootstrap authorization",
    )
    auth_keys = {
        "schema", "status", "execution_allowed", "one_use", "payload_manifest_path",
        "payload_manifest_sha256", "independent_audit_path", "independent_audit_sha256",
        "rejected_r5_audit_path", "rejected_r5_audit_sha256", "bundle_id", "run_id",
        "authorization_nonce_sha256", "worker_instance_nonce_sha256", "generation_seed",
        "issued_utc", "expires_utc",
    }
    if (
        set(authorization) != auth_keys
        or authorization.get("schema") != "qwen3_tts_voice_forge_execution_authorization_v6"
        or authorization.get("status") != "FRESH_R6_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization.get("execution_allowed") is not True
        or authorization.get("one_use") is not True
        or authorization.get("payload_manifest_path") != R6_PAYLOAD_REL.as_posix()
        or authorization.get("payload_manifest_sha256") != args.payload_manifest_sha256
        or authorization.get("rejected_r5_audit_path") != R5_AUDIT_REL.as_posix()
        or authorization.get("rejected_r5_audit_sha256") != R5_AUDIT_SHA256
        or authorization.get("bundle_id") != args.bundle_id
        or authorization.get("run_id") != args.run_id
        or not HASH.fullmatch(str(authorization.get("authorization_nonce_sha256") or ""))
        or not HASH.fullmatch(str(authorization.get("worker_instance_nonce_sha256") or ""))
        or not isinstance(authorization.get("generation_seed"), int)
        or isinstance(authorization.get("generation_seed"), bool)
        or not 0 <= authorization["generation_seed"] < 2**63
    ):
        raise R6ForgeError("R6 worker authorization binding mismatch")
    audit_rel = str(authorization.get("independent_audit_path") or "")
    audit_path = (PROJECT_ROOT / audit_rel).resolve()
    if (
        not audit_rel.startswith("System/Docs/")
        or "TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_" not in audit_rel
        or _relative(audit_path) != audit_rel
        or not audit_path.is_file()
        or audit_path.is_symlink()
        or sha256_file(audit_path) != authorization.get("independent_audit_sha256")
    ):
        raise R6ForgeError("R6 worker independent audit binding mismatch")
    try:
        issued = datetime.fromisoformat(str(authorization["issued_utc"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(authorization["expires_utc"]).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise R6ForgeError("R6 worker authorization timestamps are invalid") from exc
    now = datetime.now(timezone.utc)
    if issued.tzinfo is None or expires.tzinfo is None or issued > now or now > expires:
        raise R6ForgeError("R6 worker authorization is future-dated or expired")
    return manifest, indexed, authorization


def bootstrap_claim_before_predecessor_import(
    args: argparse.Namespace,
    authorization: dict[str, Any],
) -> tuple[Path, dict[str, Any], str, dict[str, Any], str]:
    """Exclusive-create/reopen the worker claim before any predecessor import."""

    pending = Path(args.pending_dir).resolve()
    if not pending.is_dir() or pending.is_symlink():
        raise R6ForgeError("R6 pending attempt is missing or unsafe")
    reservation_path = (
        PROJECT_ROOT
        / RESERVATION_ROOT_REL
        / f"{args.execution_authorization_sha256}.json"
    )
    reservation = _object(reservation_path, None, "R6 parent reservation")
    reservation_sha = sha256_file(reservation_path)
    reservation_keys = {
        "schema", "status", "bundle_id", "run_id", "attempt",
        "payload_manifest_sha256", "execution_authorization_sha256",
        "authorization_nonce_sha256", "worker_instance_nonce_sha256",
        "generation_seed", "parent_authorization_ledger_path",
        "verified_entry_worker_path", "verified_entry_worker_sha256",
        "exact_parent_preflight_provenance", "exact_parent_full_provenance",
        "exact_parent_full_provenance_sha256", "frozen_parent_reservation_sha256",
    }
    if (
        set(reservation) != reservation_keys
        or reservation.get("schema") != "qwen3_tts_voice_forge_parent_reservation_v6"
        or reservation.get("status")
        != "EXTERNAL_AUTHORITY_PARENT_PREFLIGHT_AND_WORKER_IDENTITY_RESERVED"
        or reservation.get("bundle_id") != args.bundle_id
        or reservation.get("run_id") != args.run_id
        or reservation.get("attempt") != _relative(pending)
        or reservation.get("payload_manifest_sha256") != args.payload_manifest_sha256
        or reservation.get("execution_authorization_sha256") != args.execution_authorization_sha256
        or reservation.get("authorization_nonce_sha256") != authorization["authorization_nonce_sha256"]
        or reservation.get("worker_instance_nonce_sha256") != authorization["worker_instance_nonce_sha256"]
        or reservation.get("generation_seed") != authorization["generation_seed"]
        or reservation.get("verified_entry_worker_path") != R6_WORKER_REL.as_posix()
        or reservation.get("verified_entry_worker_sha256") != sha256_file(PROJECT_ROOT / R6_WORKER_REL)
        or sha256_bytes(
            json.dumps(
                reservation.get("exact_parent_full_provenance"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        != reservation.get("exact_parent_full_provenance_sha256")
    ):
        raise R6ForgeError("R6 parent reservation binding mismatch")
    ledger_path = (PROJECT_ROOT / str(reservation.get("parent_authorization_ledger_path") or "")).resolve()
    if _relative(ledger_path) != reservation.get("parent_authorization_ledger_path"):
        raise R6ForgeError("R6 parent ledger path is unsafe")
    ledger = _object(
        ledger_path,
        None,
        "R6 parent authorization ledger",
    )
    ledger_sha = sha256_file(ledger_path)
    expected_ledger = {
        "schema": "qwen3_tts_voice_forge_authorization_ledger_v6",
        "status": "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT",
        "authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": _relative(pending),
        "parent_reservation_path": _relative(reservation_path),
        "parent_reservation_sha256": reservation_sha,
        "verified_worker_path": R6_WORKER_REL.as_posix(),
        "verified_worker_sha256": sha256_file(PROJECT_ROOT / R6_WORKER_REL),
    }
    if (
        set(ledger) != set(expected_ledger) | {"utc"}
        or any(ledger.get(key) != value for key, value in expected_ledger.items())
    ):
        raise R6ForgeError("R6 parent authorization ledger binding mismatch")
    claim = {
        "schema": "qwen3_tts_voice_forge_worker_launch_claim_v6",
        "status": "WORKER_CLAIMED_ONE_USE_BEFORE_PREDECESSOR_OR_MODEL_IMPORT",
        "utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": _relative(pending),
        "parent_reservation_path": _relative(reservation_path),
        "parent_reservation_sha256": reservation_sha,
        "parent_ledger_path": _relative(ledger_path),
        "parent_ledger_sha256": ledger_sha,
        "worker_path": R6_WORKER_REL.as_posix(),
        "worker_sha256": sha256_file(PROJECT_ROOT / R6_WORKER_REL),
        "worker_pid": os.getpid(),
    }
    claim_path = PROJECT_ROOT / CLAIM_ROOT_REL / f"{args.execution_authorization_sha256}.json"
    _write_new_json(claim_path, claim)
    claim_sha = sha256_file(claim_path)
    if _object(claim_path, claim_sha, "R6 reopened worker claim") != claim:
        raise R6ForgeError("R6 worker claim changed after creation")
    return claim_path, claim, claim_sha, ledger, ledger_sha


def claim_then_load_predecessors(
    *,
    args: argparse.Namespace,
    authorization: dict[str, Any],
    loader: Callable[[], Any],
) -> tuple[Any, tuple[Path, dict[str, Any], str, dict[str, Any], str]]:
    """Testable ordering primitive: a collision prevents ``loader`` entirely."""

    claim = bootstrap_claim_before_predecessor_import(args, authorization)
    return loader(), claim


def load_sealed_module(rel: Path, row: dict[str, Any], name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if (
        not path.is_file() or path.is_symlink()
        or path.stat().st_size != row.get("bytes")
        or sha256_file(path) != row.get("sha256")
    ):
        raise R6ForgeError(f"R6 sealed dependency drift: {rel.as_posix()}")
    source = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
    if sha256_file(path) != row.get("sha256"):
        raise R6ForgeError(f"R6 dependency changed during import: {rel.as_posix()}")
    return module


class _R5GuardProxy:
    """Delegate immutable helpers while replacing rejected R5 authorization trust."""

    def __init__(self, base: Any, authorization: dict[str, Any], evidence: dict[str, Any]) -> None:
        self._base = base
        self._authorization = authorization
        self._evidence = evidence

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def verify_execution_authorization(self, **_kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._authorization, self._evidence


def _install_seed_and_evaluator_capture(v2: Any, generation_seed: int) -> dict[str, Any]:
    captured: dict[str, Any] = {"seed_applied": False}
    original_runtime = v2.OfficialRuntimeV2

    class SeededRuntime(original_runtime):
        def environment_evidence(self, spec: dict[str, Any], project_root: Path) -> dict[str, Any]:
            result = super().environment_evidence(spec, project_root)
            self.torch.manual_seed(generation_seed)
            if self.torch.cuda.is_available():
                self.torch.cuda.manual_seed_all(generation_seed)
            captured["seed_applied"] = True
            return result

    v2.OfficialRuntimeV2 = SeededRuntime
    original_validate = v2.validate_audio_acceptance

    def capture_validate(**kwargs: Any) -> dict[str, Any]:
        result = original_validate(**kwargs)
        captured.update(
            {
                "job": kwargs["job"],
                "reference_eval": kwargs["reference_eval"],
                "clone_eval": kwargs["clone_eval"],
                "corpus": kwargs["corpus"],
                "audio_acceptance": result,
            }
        )
        return result

    v2.validate_audio_acceptance = capture_validate
    return captured


def _asr_row(role: str, evidence: dict[str, Any], expected_text_sha256: str, transcript_sha256: str, maximum_wer: float, minimum_speech: float) -> dict[str, Any]:
    return {
        "role": role,
        "source_wav_sha256": evidence["source_wav_sha256"],
        "expected_text_sha256": expected_text_sha256,
        "transcript_sha256": transcript_sha256,
        "asr_mode": evidence["asr_mode"],
        "asr_engine": evidence["asr_engine"],
        "asr_version": evidence["asr_version"],
        "asr_model_manifest_sha256": evidence["asr_model_manifest_sha256"],
        "speech_mode": evidence["speech_mode"],
        "speech_classifier_engine": evidence["speech_classifier_engine"],
        "speech_classifier_version": evidence["speech_classifier_version"],
        "speech_classifier_model_manifest_sha256": evidence["speech_classifier_model_manifest_sha256"],
        "speech_classifier_adapter_sha256": evidence["speech_classifier_adapter_sha256"],
        "word_error_rate": evidence["word_error_rate"],
        "maximum_word_error_rate": maximum_wer,
        "speech_probability": evidence["speech_probability"],
        "minimum_speech_probability": minimum_speech,
        "accepted": True,
    }


def execute_after_claim(
    *,
    args: argparse.Namespace,
    indexed: dict[str, dict[str, Any]],
    authorization: dict[str, Any],
    claim_path: Path,
    claim: dict[str, Any],
    claim_sha: str,
    ledger: dict[str, Any],
    ledger_sha: str,
) -> dict[str, Any]:
    """Run the sealed predecessor chain only after the one-use claim exists."""

    r6 = load_sealed_module(R6_GUARDS_REL, indexed[R6_GUARDS_REL.as_posix()], "qwen3_tts_r6_worker_guards")
    r5 = load_sealed_module(R5_GUARDS_REL, indexed[R5_GUARDS_REL.as_posix()], "qwen3_tts_r5_guards_for_r6")
    r5_worker = load_sealed_module(R5_WORKER_REL, indexed[R5_WORKER_REL.as_posix()], "qwen3_tts_r5_worker_for_r6")
    r4_guards = load_sealed_module(R4_GUARDS_REL, indexed[R4_GUARDS_REL.as_posix()], "qwen3_tts_r4_guards_for_r6")
    r4_worker = load_sealed_module(R4_WORKER_REL, indexed[R4_WORKER_REL.as_posix()], "qwen3_tts_r4_worker_for_r6")
    r3_guards = load_sealed_module(R3_GUARDS_REL, indexed[R3_GUARDS_REL.as_posix()], "qwen3_tts_r3_guards_for_r6")
    r3_worker = load_sealed_module(R3_WORKER_REL, indexed[R3_WORKER_REL.as_posix()], "qwen3_tts_r3_worker_for_r6")
    v2 = load_sealed_module(R2_WORKER_REL, indexed[R2_WORKER_REL.as_posix()], "qwen3_tts_r2_worker_for_r6")
    r5_worker.install_strict_json_readers(r5, r4_worker, r3_guards, r3_worker, v2)
    captured = _install_seed_and_evaluator_capture(v2, authorization["generation_seed"])
    authorization_evidence = {
        "path": _relative(Path(args.execution_authorization)),
        "bytes": Path(args.execution_authorization).stat().st_size,
        "sha256": args.execution_authorization_sha256,
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "independent_audit_path": authorization["independent_audit_path"],
        "independent_audit_sha256": authorization["independent_audit_sha256"],
        "rejected_r5_audit_path": R5_AUDIT_REL.as_posix(),
        "rejected_r5_audit_sha256": R5_AUDIT_SHA256,
    }
    proxy = _R5GuardProxy(r5, authorization, authorization_evidence)
    r5_worker._verify_ledger = lambda *_a, **_k: ledger
    r5_result = r5_worker.execute_r5(
        args=args,
        indexed=indexed,
        r5=proxy,
        r4_guards=r4_guards,
        r4_worker=r4_worker,
        r3_guards=r3_guards,
        r3_worker=r3_worker,
        v2=v2,
    )
    if captured.get("seed_applied") is not True or "audio_acceptance" not in captured:
        raise R6ForgeError("R6 seed/evaluator capture was not exercised")
    pending = Path(args.pending_dir).resolve()
    r4_profile_path = pending / "voice_profile_candidate_v4.json"
    r4_manifest_path = pending / "worker_manifest_v4.json"
    r5_profile_path = pending / "voice_profile_candidate_v5.json"
    r5_manifest_path = pending / "worker_manifest_v5.json"
    r2_manifest_path = pending / R2_MANIFEST_NAME
    r4_profile = r6.strict_read_json(r4_profile_path, label="R6 R4 profile")
    r5_profile = r6.strict_read_json(r5_profile_path, expected_sha256=r5_result["profile_sha256"], label="R6 R5 profile")
    r5_manifest = r6.strict_read_json(r5_manifest_path, expected_sha256=r5_result["manifest_sha256"], label="R6 R5 manifest")
    r2_manifest = r6.strict_read_json(r2_manifest_path, label="R6 R2 manifest")
    trusted = v2.load_trusted_bundle(PROJECT_ROOT, args.bundle_id, require_ready_environment=True)
    job = trusted.job
    reference_transcript = str(captured["reference_eval"]["transcript"]).encode("utf-8")
    clone_transcript = str(captured["clone_eval"]["transcript"]).encode("utf-8")
    r6.write_new(pending / "reference_asr_transcript_v6.txt", reference_transcript)
    r6.write_new(pending / "clone_asr_transcript_v6.txt", clone_transcript)
    artifact_seals = r5_manifest["artifact_seals"]
    models = r2_manifest["model_snapshots"]
    base_semantic = {
        **{key: r4_profile[key] for key in r6.CORE_BINDING_KEYS},
        "run_id": args.run_id,
        "attempt": _relative(pending),
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "execution_authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "parent_reservation_sha256": sha256_file(
            PROJECT_ROOT
            / RESERVATION_ROOT_REL
            / f"{args.execution_authorization_sha256}.json"
        ),
        "parent_authorization_ledger_sha256": ledger_sha,
        "worker_launch_claim_sha256": claim_sha,
        "r4_worker_manifest_sha256": sha256_file(r4_manifest_path),
        "r4_profile_sha256": sha256_file(r4_profile_path),
        "r5_worker_manifest_sha256": sha256_file(r5_manifest_path),
        "r5_profile_sha256": sha256_file(r5_profile_path),
        "reference_wav_sha256": artifact_seals["reference_wav"]["sha256"],
        "clone_test_wav_sha256": artifact_seals["clone_test_wav"]["sha256"],
        "runtime_clone_prompt_sha256": artifact_seals["runtime_clone_prompt"]["sha256"],
        "reference_transcript_sha256": sha256_bytes(reference_transcript),
        "clone_transcript_sha256": sha256_bytes(clone_transcript),
        "reference_text_sha256": job["reference_text_sha256"],
        "test_text_sha256": job["test_text_sha256"],
        "original_trait_prompt_sha256": job["design_traits_text_sha256"],
        "generation_seed": authorization["generation_seed"],
        "voice_design_model_revision": models["voice_design"]["revision"],
        "voice_design_model_manifest_sha256": trusted.bundle["voice_design_model_manifest_sha256"],
        "base_model_revision": models["base"]["revision"],
        "base_model_manifest_sha256": trusted.bundle["base_model_manifest_sha256"],
        "artifact_seals_sha256": r6.canonical_sha256(artifact_seals),
    }
    subject_sha = r6.canonical_sha256(base_semantic)
    limits = trusted.contract["audio_acceptance"]
    ref_eval = captured["reference_eval"]
    clone_eval = captured["clone_eval"]
    audio = captured["audio_acceptance"]
    evaluator = {
        "schema": "qwen3_tts_voice_forge_evaluator_evidence_v6",
        "status": "WORKER_EVIDENCE_PARENT_REVALIDATION_REQUIRED",
        "semantic_binding_sha256": subject_sha,
        "reference_wav_sha256": base_semantic["reference_wav_sha256"],
        "clone_test_wav_sha256": base_semantic["clone_test_wav_sha256"],
        "runtime_clone_prompt_sha256": base_semantic["runtime_clone_prompt_sha256"],
        "reference_transcript_sha256": base_semantic["reference_transcript_sha256"],
        "clone_transcript_sha256": base_semantic["clone_transcript_sha256"],
        "asr_and_speech": {
            "reference": _asr_row("reference", ref_eval, job["reference_text_sha256"], base_semantic["reference_transcript_sha256"], limits["maximum_word_error_rate"], limits["minimum_speech_probability"]),
            "clone": _asr_row("clone", clone_eval, job["test_text_sha256"], base_semantic["clone_transcript_sha256"], limits["maximum_word_error_rate"], limits["minimum_speech_probability"]),
        },
        "pure_tone": {
            role: {
                "role": role,
                "source_wav_sha256": row["source_wav_sha256"],
                "detector": row["pure_tone_detector"],
                "pure_tone_probability": row["pure_tone_probability"],
                "maximum_pure_tone_probability": limits["maximum_pure_tone_probability"],
                "pure_tone_rejected": True,
            }
            for role, row in (("reference", ref_eval), ("clone", clone_eval))
        },
        "speaker_identity": {
            "reference_wav_sha256": base_semantic["reference_wav_sha256"],
            "clone_test_wav_sha256": base_semantic["clone_test_wav_sha256"],
            "embedding_mode": clone_eval["embedding_mode"],
            "embedding_engine": clone_eval["embedding_engine"],
            "embedding_version": clone_eval["embedding_version"],
            "embedding_model_manifest_sha256": clone_eval["embedding_model_manifest_sha256"],
            "reference_to_clone_similarity": audio["reference_to_clone_similarity"],
            "minimum_similarity": limits["minimum_reference_to_clone_similarity"],
            "accepted": True,
        },
        "collision_corpus": {
            "clone_test_wav_sha256": base_semantic["clone_test_wav_sha256"],
            "corpus_manifest_sha256": trusted.bundle["evaluation_corpus_sha256"],
            "corpus_snapshot_sha256": r6.canonical_sha256(r2_manifest["collision_corpus_snapshot"]),
            "all_embeddings_recomputed_from_exact_wavs": True,
            "collision_results_sha256": r6.canonical_sha256(audio["collision_results"]),
            "maximum_allowed_similarity": limits["maximum_similarity_to_resident_or_generic_voice"],
            "no_resident_or_generic_collision": True,
        },
        "named_person_clearance": {
            "identity_basis": job["identity_basis"],
            "voice_origin": job["voice_origin"],
            "static_manifest_path": _relative(
                trusted.bundle_dir / trusted.bundle["identity_clearance_manifest_path"]
            ),
            "static_manifest_sha256": trusted.bundle["identity_clearance_manifest_sha256"],
            "live_report_path": _relative(pending / "live_identity_clearance_v2.json"),
            "live_report_sha256": sha256_file(pending / "live_identity_clearance_v2.json"),
            "named_person_or_imitation_language_found": False,
            "cleared": True,
        },
        "watermark": {
            "preflight_manifest_path": _relative(
                trusted.bundle_dir / trusted.bundle["watermark_evidence_manifest_path"]
            ),
            "preflight_manifest_sha256": trusted.bundle["watermark_evidence_manifest_sha256"],
            "live_report_path": _relative(pending / "live_watermark_documentation_scan_v2.json"),
            "live_report_sha256": sha256_file(pending / "live_watermark_documentation_scan_v2.json"),
            "status_ceiling": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
            "intentional_audio_watermark_proven": False,
            "watermark_removal_or_circumvention_attempted": False,
        },
        "predecessor_audio_acceptance_sha256": r6.canonical_sha256(r2_manifest["audio_acceptance"]),
        "predecessor_evaluator_import_bindings_sha256": r6.canonical_sha256(r2_manifest["evaluator_imported_module_bindings"]),
        "predecessor_r2_manifest_sha256": sha256_file(r2_manifest_path),
    }
    evaluator_path = pending / "evaluator_evidence_v6.json"
    r6.write_new_json(evaluator_path, evaluator)
    evaluator_sha = sha256_file(evaluator_path)
    worker_resource = {
        "schema": "qwen3_tts_voice_forge_worker_resource_evidence_v6",
        "status": "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED",
        "semantic_binding_sha256": subject_sha,
        "worker_reported_telemetry": r2_manifest["telemetry"],
        "worker_reported_telemetry_sha256": r6.canonical_sha256(r2_manifest["telemetry"]),
        "worker_reported_timings_seconds": r2_manifest["timings_seconds"],
        "worker_reported_timings_sha256": r6.canonical_sha256(r2_manifest["timings_seconds"]),
        "worker_reported_events": r2_manifest["events"],
        "worker_reported_events_sha256": r6.canonical_sha256(r2_manifest["events"]),
    }
    worker_resource_path = pending / "worker_resource_evidence_v6.json"
    r6.write_new_json(worker_resource_path, worker_resource)
    worker_resource_sha = sha256_file(worker_resource_path)
    semantic = {
        **base_semantic,
        "evaluator_evidence_sha256": evaluator_sha,
        "resource_evidence_sha256": worker_resource_sha,
    }
    r6.validate_semantic_binding(semantic)
    r6.validate_evaluator_evidence(evaluator, semantic_binding=semantic)
    r6.validate_worker_resource_evidence(worker_resource, semantic_binding=semantic)
    core = {key: semantic[key] for key in r6.CORE_BINDING_KEYS}
    r6.validate_r5_safe_extension(
        r4_profile=r4_profile,
        r5_profile=r5_profile,
        expected_core=core,
        expected_r4_profile_sha256=semantic["r4_profile_sha256"],
        expected_payload_sha256=args.payload_manifest_sha256,
        expected_authorization_sha256=args.execution_authorization_sha256,
        expected_parent_ledger_sha256=ledger_sha,
    )
    r6.validate_r5_manifest(
        manifest=r5_manifest,
        expected_core=core,
        expected_run_id=args.run_id,
        expected_r4_manifest_sha256=semantic["r4_worker_manifest_sha256"],
        expected_r4_profile_sha256=semantic["r4_profile_sha256"],
        expected_r5_profile_sha256=semantic["r5_profile_sha256"],
        expected_payload_sha256=args.payload_manifest_sha256,
        expected_authorization_sha256=args.execution_authorization_sha256,
        expected_parent_ledger_sha256=ledger_sha,
    )
    profile = {
        **r5_profile,
        "schema": "qwen3_tts_original_voice_profile_candidate_v6",
        "r6_status": "PRIVATE_UNREVIEWED_COMPLETE_PARENT_RECONCILIATION_PENDING",
        "predecessor_r5_profile_sha256": semantic["r5_profile_sha256"],
        "semantic_binding_v6": semantic,
        "semantic_binding_v6_sha256": r6.canonical_sha256(semantic),
        "evaluator_evidence_path": evaluator_path.name,
        "evaluator_evidence_sha256": evaluator_sha,
        "resource_evidence_path": worker_resource_path.name,
        "resource_evidence_sha256": worker_resource_sha,
        "worker_launch_claim_path": _relative(claim_path),
        "worker_launch_claim_sha256": claim_sha,
        "parent_authorization_ledger_path": claim["parent_ledger_path"],
        "parent_authorization_ledger_sha256": ledger_sha,
        "artifact_seals_sha256": semantic["artifact_seals_sha256"],
        "complete_later_use_revalidation_required": True,
    }
    profile_path = pending / "voice_profile_candidate_v6.json"
    r6.write_new_json(profile_path, profile)
    profile_sha = sha256_file(profile_path)
    manifest = {
        "schema": "qwen3_tts_original_voice_forge_worker_manifest_v6",
        "status": "CHILD_GATES_PASSED_PARENT_RECONCILIATION_AND_FINALIZATION_PENDING",
        "semantic_binding_v6": semantic,
        "semantic_binding_v6_sha256": r6.canonical_sha256(semantic),
        "profile_sha256": profile_sha,
        "predecessor_worker_manifest_sha256": semantic["r5_worker_manifest_sha256"],
        "predecessor_profile_sha256": semantic["r5_profile_sha256"],
        "worker_launch_claim_path": _relative(claim_path),
        "worker_launch_claim_sha256": claim_sha,
        "parent_authorization_ledger_path": claim["parent_ledger_path"],
        "parent_authorization_ledger_sha256": ledger_sha,
        "artifact_seals": artifact_seals,
        "artifact_seals_sha256": semantic["artifact_seals_sha256"],
        "evaluator_evidence_path": evaluator_path.name,
        "evaluator_evidence_sha256": evaluator_sha,
        "resource_evidence_path": worker_resource_path.name,
        "resource_evidence_sha256": worker_resource_sha,
        "process_tree_quiescence_required_before_parent_finalization": True,
        "parent_evaluator_and_resource_reconciliation_required": True,
        "owner_hearing_acceptance": "PENDING",
        "assignment_allowed": False,
        "activation_allowed": False,
        "publication_or_upload_allowed": False,
    }
    manifest_path = pending / "worker_manifest_v6.json"
    r6.write_new_json(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)
    child = {
        "schema": "qwen3_tts_original_voice_forge_child_result_v6",
        "status": manifest["status"],
        "semantic_binding_v6_sha256": r6.canonical_sha256(semantic),
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest_sha,
        "profile_path": profile_path.name,
        "profile_sha256": profile_sha,
        "evaluator_evidence_path": evaluator_path.name,
        "evaluator_evidence_sha256": evaluator_sha,
        "worker_resource_evidence_path": worker_resource_path.name,
        "worker_resource_evidence_sha256": worker_resource_sha,
        "worker_launch_claim_path": _relative(claim_path),
        "worker_launch_claim_sha256": claim_sha,
        "artifact_seals_sha256": semantic["artifact_seals_sha256"],
    }
    r6.validate_r6_profile_and_manifest(
        r5_profile=r5_profile,
        r6_profile=profile,
        r6_manifest=manifest,
        child_result=child,
        semantic_binding=semantic,
        r5_profile_sha256=semantic["r5_profile_sha256"],
        r5_manifest_sha256=semantic["r5_worker_manifest_sha256"],
        r6_profile_sha256=profile_sha,
    )
    return child


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    parser.add_argument("--bundle-id")
    parser.add_argument("--run-id")
    parser.add_argument("--pending-dir")
    parser.add_argument("--payload-manifest-sha256")
    parser.add_argument("--execution-authorization")
    parser.add_argument("--execution-authorization-sha256")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute or not args.acknowledge_private_unreviewed:
        raise R6ForgeError("R6 worker remains inert without exact acknowledgements")
    if not all(
        (
            args.bundle_id,
            args.run_id,
            args.pending_dir,
            args.payload_manifest_sha256,
            args.execution_authorization,
            args.execution_authorization_sha256,
        )
    ):
        raise R6ForgeError("R6 worker lacks exact parent trust arguments")
    _manifest, indexed, authorization = bootstrap_external_trust(args)
    # CRITICAL ORDER: the following exclusive claim happens before the first
    # call to load_sealed_module, predecessor import, evaluator import, or model
    # import.  A collision exits without invoking the loader.
    claim_path, claim, claim_sha, ledger, ledger_sha = bootstrap_claim_before_predecessor_import(
        args, authorization
    )
    child = execute_after_claim(
        args=args,
        indexed=indexed,
        authorization=authorization,
        claim_path=claim_path,
        claim=claim,
        claim_sha=claim_sha,
        ledger=ledger,
        ledger_sha=ledger_sha,
    )
    payload = json.dumps(child, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R6 Qwen3-TTS forge worker failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
