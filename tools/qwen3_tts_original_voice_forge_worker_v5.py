"""Inert append-only R5 worker for TemporaryAI original synthetic voices.

The worker is a sealed wrapper around the frozen R4/R3/R2 chain.  It accepts
only a parent-reserved pending directory and externally hash-pinned R5 payload
manifest/authorization.  This source does nothing without the explicit real-
execution gate, which remains unavailable while the shipped authorization is
disabled and the R5 independent audit is pending.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json"
)
R5_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r5_guards.py")
R5_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v5.py")
R5_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R4_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v4.py")
R4_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py")
R4_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json")
R4_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R4_INDEPENDENT_AUDIT_20260809.md"
)
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R3_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py")
R3_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
R2_CONTRACT_REL = Path(
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json"
)
R2_ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
R2_REGISTRY_REL = Path(
    "Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json"
)
R2_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")


R5_REQUIRED_PAYLOADS = {
    path.as_posix()
    for path in (
        R5_GUARDS_REL,
        R5_WORKER_REL,
        R5_RUNNER_REL,
        R4_GUARDS_REL,
        R4_WORKER_REL,
        R4_RUNNER_REL,
        R4_MANIFEST_REL,
        R4_AUDIT_REL,
        R3_GUARDS_REL,
        R3_WORKER_REL,
        R3_RUNNER_REL,
        R3_MANIFEST_REL,
        R2_WORKER_REL,
        R2_RUNNER_REL,
        R2_CONTRACT_REL,
        R2_ENVIRONMENT_REL,
        R2_REGISTRY_REL,
        R2_CORPUS_REL,
    )
}


class R5ForgeError(RuntimeError):
    """The R5 child worker failed closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bootstrap_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise R5ForgeError(f"duplicate bootstrap JSON key: {key}")
        value[key] = child
    return value


def _bootstrap_object(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha256 or "")):
        raise R5ForgeError(f"{label} hash is invalid")
    if not path.is_file() or path.is_symlink():
        raise R5ForgeError(f"{label} is missing, non-regular, or a symlink")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise R5ForgeError(f"{label} differs from its external hash")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_bootstrap_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R5ForgeError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R5ForgeError(f"{label} is not an object")
    return value


def bootstrap_verify_external_trust(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Verify both external trust objects before importing R5/R4/R3/R2."""

    manifest = _bootstrap_object(
        PROJECT_ROOT / PAYLOAD_MANIFEST_REL,
        args.payload_manifest_sha256,
        "R5 worker bootstrap payload manifest",
    )
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v5"
        or manifest.get("status") != "IMMUTABLE_PAYLOAD_REQUIRES_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
    ):
        raise R5ForgeError("R5 worker bootstrap payload attempted self-authorization")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R5ForgeError("R5 worker bootstrap payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R5ForgeError("R5 worker bootstrap payload row is not exact")
        rel = str(row.get("path") or "")
        if rel in indexed or rel not in R5_REQUIRED_PAYLOADS:
            raise R5ForgeError("R5 worker bootstrap payload is duplicate/unexpected")
        path = (PROJECT_ROOT / rel).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve())
        except ValueError as exc:
            raise R5ForgeError("R5 worker bootstrap payload escaped project") from exc
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R5ForgeError(f"R5 worker bootstrap payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != R5_REQUIRED_PAYLOADS:
        raise R5ForgeError("R5 worker bootstrap payload inventory is incomplete")

    authorization_path = Path(args.execution_authorization).resolve()
    try:
        auth_rel = authorization_path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R5ForgeError("R5 worker bootstrap authorization escaped project") from exc
    if not auth_rel.startswith("Data/voice/authorizations/qwen3_tts_voice_forge_v5/"):
        raise R5ForgeError("R5 worker bootstrap authorization root mismatch")
    authorization = _bootstrap_object(
        authorization_path,
        args.execution_authorization_sha256,
        "R5 worker bootstrap authorization",
    )
    exact_keys = {
        "schema", "status", "execution_allowed", "one_use",
        "payload_manifest_path", "payload_manifest_sha256",
        "independent_audit_path", "independent_audit_sha256",
        "rejected_r4_audit_path", "rejected_r4_audit_sha256",
        "bundle_id", "run_id", "authorization_nonce_sha256",
        "issued_utc", "expires_utc",
    }
    if set(authorization) != exact_keys:
        raise R5ForgeError("R5 worker bootstrap authorization fields are not exact")
    if (
        authorization.get("schema") != "qwen3_tts_voice_forge_execution_authorization_v5"
        or authorization.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization.get("execution_allowed") is not True
        or authorization.get("one_use") is not True
        or authorization.get("payload_manifest_path") != PAYLOAD_MANIFEST_REL.as_posix()
        or authorization.get("payload_manifest_sha256") != args.payload_manifest_sha256
        or authorization.get("bundle_id") != args.bundle_id
        or authorization.get("run_id") != args.run_id
        or authorization.get("rejected_r4_audit_path") != R4_AUDIT_REL.as_posix()
        or authorization.get("rejected_r4_audit_sha256")
        != "04073b96cd4d514aaa5e60b75783d0e2a1c024782fce591fc83fcfe3e2befe9b"
        or sha256_file(PROJECT_ROOT / R4_AUDIT_REL)
        != authorization.get("rejected_r4_audit_sha256")
    ):
        raise R5ForgeError("R5 worker bootstrap authorization binding mismatch")
    audit_rel = str(authorization.get("independent_audit_path") or "")
    audit_path = (PROJECT_ROOT / audit_rel).resolve()
    try:
        resolved_audit_rel = audit_path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R5ForgeError("R5 worker bootstrap independent audit escaped project") from exc
    if (
        not audit_rel.startswith("System/Docs/")
        or resolved_audit_rel != audit_rel
        or "TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_" not in audit_rel
        or not re.fullmatch(r"[0-9a-f]{64}", str(authorization.get("independent_audit_sha256") or ""))
        or not re.fullmatch(r"[0-9a-f]{64}", str(authorization.get("authorization_nonce_sha256") or ""))
        or not audit_path.is_file()
        or audit_path.is_symlink()
        or sha256_file(audit_path) != authorization.get("independent_audit_sha256")
    ):
        raise R5ForgeError("R5 worker bootstrap audit/nonce binding mismatch")
    try:
        issued = datetime.fromisoformat(str(authorization["issued_utc"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(authorization["expires_utc"]).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise R5ForgeError("R5 worker bootstrap authorization timestamps are invalid") from exc
    now = datetime.now(timezone.utc)
    if issued.tzinfo is None or expires.tzinfo is None or issued > now or now > expires:
        raise R5ForgeError("R5 worker bootstrap authorization is future-dated or expired")
    return manifest, indexed, authorization


def load_sealed_module(rel: Path, row: dict[str, Any], name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != row.get("bytes")
        or sha256_file(path) != row.get("sha256")
    ):
        raise R5ForgeError(f"sealed R5 worker dependency drift: {rel.as_posix()}")
    source = path.read_bytes()
    if len(source) != row.get("bytes") or hashlib.sha256(source).hexdigest() != row.get("sha256"):
        raise R5ForgeError(f"sealed R5 source read drift: {rel.as_posix()}")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    code = compile(source, str(path), "exec", dont_inherit=True, optimize=0)
    exec(code, module.__dict__)
    if Path(module.__file__).resolve() != path or sha256_file(path) != row.get("sha256"):
        raise R5ForgeError(f"sealed R5 dependency changed after import: {rel.as_posix()}")
    return module


def install_strict_json_readers(r5: Any, *modules: Any) -> None:
    def strict_reader(path: Path) -> dict[str, Any]:
        return r5.strict_read_json(Path(path), label=f"acceptance-critical {path}")

    for module in modules:
        if hasattr(module, "read_json"):
            module.read_json = strict_reader


def derive_worker_full_provenance(
    r5: Any,
    *,
    v2: Any,
    r3_guards: Any,
    environment: dict[str, Any],
) -> dict[str, Any]:
    """Recompute full installed RECORD and wheel maps in the child process."""

    result: dict[str, Any] = {}
    distributions = environment.get("distributions") or {}
    for package in ("torch", "torchaudio"):
        row = distributions.get(package)
        if not isinstance(row, dict):
            raise R5ForgeError(f"R5 worker {package} distribution spec is absent")
        installed_raw = v2.verify_installed_distribution(
            project_root=PROJECT_ROOT, package=package, row=row
        )
        wheel = r3_guards.attest_wheel_archive(
            project_root=PROJECT_ROOT,
            wheel_root_rel=v2.WHEEL_EVIDENCE_ROOT_REL,
            package=package,
            row=row,
        )
        binding = r3_guards.bind_wheel_to_installed_distribution(
            project_root=PROJECT_ROOT,
            isolated_venv_rel=v2.ISOLATED_VENV_REL,
            package=package,
            row=row,
            installed_evidence=installed_raw,
            wheel_evidence=wheel,
        )
        installed_files = installed_raw.get("installed_files")
        if installed_files is None:
            installed_files = installed_raw.get("files")
        if not isinstance(installed_files, list) or not installed_files:
            raise R5ForgeError(f"R5 worker {package} RECORD file map is absent")
        installed = {
            "version": installed_raw.get("version"),
            "record_path": installed_raw.get("record_path"),
            "record_sha256": installed_raw.get("record_sha256"),
            "record_rows_verified": len(installed_files),
            "installed_files": installed_files,
        }
        result[package] = {
            "environment_distribution_spec_sha256": r5.canonical_sha256(row),
            "installed_record_evidence": installed,
            "wheel_archive_evidence": wheel,
            "strict_binding": binding,
        }
    return r5.require_full_provenance_capsule(result, "worker-derived full provenance")


def _verify_ledger(
    r5: Any,
    reservation: dict[str, Any],
    *,
    authorization_sha256: str,
    bundle_id: str,
    run_id: str,
) -> dict[str, Any]:
    ledger_path = r5.inside(
        PROJECT_ROOT,
        str(reservation.get("authorization_ledger_path") or ""),
        "R5 authorization ledger",
    )
    ledger = r5.strict_read_json(
        ledger_path,
        expected_sha256=str(reservation.get("authorization_ledger_sha256") or ""),
        label="R5 one-use authorization ledger",
    )
    exact = {
        "schema",
        "status",
        "utc",
        "authorization_sha256",
        "authorization_nonce_sha256",
        "payload_manifest_sha256",
        "bundle_id",
        "run_id",
        "attempt",
    }
    if (
        set(ledger) != exact
        or ledger.get("schema") != "qwen3_tts_voice_forge_authorization_ledger_v5"
        or ledger.get("status") != "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT"
        or ledger.get("authorization_sha256") != authorization_sha256
        or ledger.get("bundle_id") != bundle_id
        or ledger.get("run_id") != run_id
        or ledger.get("attempt") != reservation.get("attempt")
    ):
        raise R5ForgeError("R5 one-use authorization ledger binding mismatch")
    return ledger


def execute_r5(
    *,
    args: argparse.Namespace,
    indexed: dict[str, dict[str, Any]],
    r5: Any,
    r4_guards: Any,
    r4_worker: Any,
    r3_guards: Any,
    r3_worker: Any,
    v2: Any,
) -> dict[str, Any]:
    pending = Path(args.pending_dir).resolve()
    if not pending.is_dir() or pending.is_symlink():
        raise R5ForgeError("R5 parent pending directory is missing or unsafe")
    authorization, authorization_evidence = r5.verify_execution_authorization(
        project_root=PROJECT_ROOT,
        authorization_path=Path(args.execution_authorization),
        expected_authorization_sha256=args.execution_authorization_sha256,
        expected_manifest_sha256=args.payload_manifest_sha256,
        bundle_id=args.bundle_id,
        run_id=args.run_id,
    )
    reservation = r5.strict_read_json(
        pending / "parent_reservation_v5.json", label="R5 parent reservation"
    )
    if (
        reservation.get("schema") != "qwen3_tts_voice_forge_parent_reservation_v5"
        or reservation.get("bundle_id") != args.bundle_id
        or reservation.get("run_id") != args.run_id
        or reservation.get("payload_manifest_sha256") != args.payload_manifest_sha256
        or reservation.get("execution_authorization_sha256")
        != args.execution_authorization_sha256
    ):
        raise R5ForgeError("R5 parent reservation identity mismatch")
    ledger = _verify_ledger(
        r5,
        reservation,
        authorization_sha256=args.execution_authorization_sha256,
        bundle_id=args.bundle_id,
        run_id=args.run_id,
    )
    preflight = r5.require_strict_provenance_map(
        reservation.get("exact_parent_preflight_provenance"), "R5 reserved preflight"
    )
    full_parent_preflight = r5.require_full_provenance_capsule(
        reservation.get("exact_parent_full_provenance"),
        "R5 reserved full parent preflight",
    )
    if r5.canonical_sha256(full_parent_preflight) != reservation.get(
        "exact_parent_full_provenance_sha256"
    ):
        raise R5ForgeError("R5 reserved full parent preflight hash mismatch")
    if {
        package: full_parent_preflight[package]["strict_binding"]
        for package in ("torch", "torchaudio")
    } != preflight:
        raise R5ForgeError("R5 reserved summary/full parent provenance differ")
    environment = r5.strict_read_json(
        PROJECT_ROOT / R2_ENVIRONMENT_REL, label="R5 worker environment spec"
    )

    # The exact frozen R4 implementation writes only inside the pending tree.
    # Its root is rebound to this one run *before* the frozen chain is installed;
    # v2 therefore still sees bundle_id/attempt_N as its exact reserved layout.
    r4_worker.R4_OUTPUT_ROOT_REL = (
        Path("Voice/voice_forge/private_review_v5") / args.run_id
    )
    r4_worker.configure_frozen_chain(r3_worker, v2, r3_guards, r4_guards)
    worker_full_pre = derive_worker_full_provenance(
        r5, v2=v2, r3_guards=r3_guards, environment=environment
    )
    r4_result = r4_worker.execute_r4(
        project_root=PROJECT_ROOT,
        bundle_id=args.bundle_id,
        attempt_dir=pending,
        r3_worker=r3_worker,
        v2=v2,
        r3_guards=r3_guards,
        r4_guards=r4_guards,
    )
    # Duplicate-key rejection occurs before any frozen ordinary json.loads.
    r4_manifest = r5.strict_read_json(
        pending / "worker_manifest_v4.json", label="R5-bound R4 worker manifest"
    )
    r4_profile = r5.strict_read_json(
        pending / "voice_profile_candidate_v4.json", label="R5-bound R4 profile"
    )
    if (
        sha256_file(pending / "worker_manifest_v4.json") != r4_result.get("manifest_sha256")
        or sha256_file(pending / "voice_profile_candidate_v4.json")
        != r4_result.get("profile_sha256")
    ):
        raise R5ForgeError("R5-bound R4 child output hashes differ")
    worker_pre = r4_manifest.get("strict_wheel_binding_worker_pre_model")
    worker_post = r4_manifest.get("strict_wheel_binding_worker_post_execution")
    worker_full_post = derive_worker_full_provenance(
        r5, v2=v2, r3_guards=r3_guards, environment=environment
    )
    if (
        {package: worker_full_pre[package]["strict_binding"] for package in ("torch", "torchaudio")}
        != worker_pre
        or {package: worker_full_post[package]["strict_binding"] for package in ("torch", "torchaudio")}
        != worker_post
    ):
        raise R5ForgeError("R5 worker R4 summary/full provenance derivations differ")
    provenance = r5.reconcile_full_provenance_capsules(
        parent_preflight=full_parent_preflight,
        reservation=full_parent_preflight,
        worker_pre_model=worker_full_pre,
        worker_post_execution=worker_full_post,
        parent_postflight=full_parent_preflight,
    )
    seals = r4_manifest.get("artifact_seals")
    r4_guards.verify_exact_artifact_set(
        attempt_dir=pending, seals=seals, r3_guards=r3_guards
    )
    profile = {
        **r4_profile,
        "schema": "qwen3_tts_original_voice_profile_candidate_v5",
        "r5_status": "PRIVATE_UNREVIEWED_PARENT_FINALIZATION_PENDING",
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization": authorization_evidence,
        "authorization_ledger_sha256": reservation["authorization_ledger_sha256"],
        "exact_provenance_sha256": provenance["canonical_full_provenance_sha256"],
        "parent_finalization_required": True,
        "later_use_acceptance_reopen_required": True,
        "assignment_allowed": False,
        "activation_allowed": False,
        "publication_or_upload_allowed": False,
        "owner_hearing_acceptance": "PENDING",
        "independent_execution_audit": "REQUIRED_AFTER_BOUNDED_RUN",
    }
    profile_path = pending / "voice_profile_candidate_v5.json"
    r5.write_new_json(profile_path, profile)
    profile_hash = sha256_file(profile_path)
    manifest = {
        "schema": "qwen3_tts_original_voice_forge_worker_manifest_v5",
        "status": "CHILD_ENGINEERING_GATES_PASSED_PARENT_FINALIZATION_PENDING",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "authorization_ledger_sha256": reservation["authorization_ledger_sha256"],
        "predecessor_worker_manifest_sha256": sha256_file(
            pending / "worker_manifest_v4.json"
        ),
        "predecessor_profile_sha256": sha256_file(
            pending / "voice_profile_candidate_v4.json"
        ),
        "profile_sha256": profile_hash,
        "artifact_seals": seals,
        "artifact_seals_sha256": r5.canonical_sha256(seals),
        "strict_wheel_binding_parent_preflight": preflight,
        "strict_wheel_binding_worker_pre_model": worker_pre,
        "strict_wheel_binding_worker_post_execution": worker_post,
        "full_provenance_parent_preflight": full_parent_preflight,
        "full_provenance_worker_pre_model": worker_full_pre,
        "full_provenance_worker_post_execution": worker_full_post,
        "exact_provenance_sha256": provenance["canonical_full_provenance_sha256"],
        "unbound_installer_generated_package_bytes_allowed": False,
        "parent_fresh_postflight_required": True,
        "parent_owned_finalization_required": True,
        "clean_process_tree_exit": "PARENT_MUST_CONFIRM",
        "owner_hearing_acceptance": "PENDING",
        "activation_assignment_publication_or_upload_allowed": False,
    }
    manifest_path = pending / "worker_manifest_v5.json"
    r5.write_new_json(manifest_path, manifest)
    manifest_hash = sha256_file(manifest_path)
    r4_guards.verify_exact_artifact_set(
        attempt_dir=pending, seals=seals, r3_guards=r3_guards
    )
    child = {
        "schema": "qwen3_tts_original_voice_forge_child_result_v5",
        "status": manifest["status"],
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_ledger_sha256": reservation["authorization_ledger_sha256"],
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest_hash,
        "profile_path": profile_path.name,
        "profile_sha256": profile_hash,
        "artifact_seals_sha256": r5.canonical_sha256(seals),
        "exact_provenance_sha256": provenance["canonical_full_provenance_sha256"],
    }
    # The parent requires these exact canonical bytes plus one LF.
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
        raise R5ForgeError("R5 worker remains inert without exact acknowledgements")
    required = (
        args.bundle_id,
        args.run_id,
        args.pending_dir,
        args.payload_manifest_sha256,
        args.execution_authorization,
        args.execution_authorization_sha256,
    )
    if not all(required):
        raise R5ForgeError("R5 worker lacks exact parent trust arguments")

    # Verify both external trust objects with only this already-invoked entry
    # source.  Import the R5 guard dependency only after its exact row and the
    # complete immutable payload have passed.
    _bootstrap_manifest, bootstrap_indexed, _bootstrap_authorization = (
        bootstrap_verify_external_trust(args)
    )
    r5 = load_sealed_module(
        R5_GUARDS_REL,
        bootstrap_indexed[R5_GUARDS_REL.as_posix()],
        "qwen3_tts_r5_worker_guards_after_external_trust",
    )
    _manifest, indexed = r5.verify_payload_manifest(
        project_root=PROJECT_ROOT,
        expected_manifest_sha256=args.payload_manifest_sha256,
        required_payloads=R5_REQUIRED_PAYLOADS,
    )
    if sha256_file(PROJECT_ROOT / R5_GUARDS_REL) != indexed[R5_GUARDS_REL.as_posix()]["sha256"]:
        raise R5ForgeError("bootstrapped R5 guards differ from immutable payload")
    r4_guards = load_sealed_module(
        R4_GUARDS_REL, indexed[R4_GUARDS_REL.as_posix()], "qwen3_tts_r4_guards_for_r5_worker"
    )
    r4_worker = load_sealed_module(
        R4_WORKER_REL, indexed[R4_WORKER_REL.as_posix()], "qwen3_tts_r4_worker_for_r5"
    )
    r3_guards = load_sealed_module(
        R3_GUARDS_REL, indexed[R3_GUARDS_REL.as_posix()], "qwen3_tts_r3_guards_for_r5_worker"
    )
    r3_worker = load_sealed_module(
        R3_WORKER_REL, indexed[R3_WORKER_REL.as_posix()], "qwen3_tts_r3_worker_for_r5"
    )
    v2 = load_sealed_module(
        R2_WORKER_REL, indexed[R2_WORKER_REL.as_posix()], "qwen3_tts_r2_worker_for_r5"
    )
    install_strict_json_readers(r5, r4_worker, r3_guards, r3_worker, v2)
    result = execute_r5(
        args=args,
        indexed=indexed,
        r5=r5,
        r4_guards=r4_guards,
        r4_worker=r4_worker,
        r3_guards=r3_guards,
        r3_worker=r3_worker,
        v2=v2,
    )
    sys.stdout.buffer.write(r5.canonical_bytes(result) + b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R5 Qwen3-TTS worker failed closed: {exc}", file=sys.stderr)
        if not isinstance(exc, (R5ForgeError, SystemExit)):
            traceback.print_exc()
        raise SystemExit(2)
