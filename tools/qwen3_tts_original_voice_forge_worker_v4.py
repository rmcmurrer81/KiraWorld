"""Append-only inert R4 worker for TemporaryAI original synthetic voices.

R4 executes the exact sealed R3/R2 chain only after a fresh R4 audit gate.  It
adds no model behavior.  Its sole purpose is to bind the honest R3 result to an
exact candidate/job/profile identity and to emit one hash-anchored child result
for the parent through stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R4_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json")
R4_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v4.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R4_OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v4")
R4_FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"


class R4ForgeError(RuntimeError):
    """The append-only R4 worker failed closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise R4ForgeError(f"cannot read exact JSON: {path}") from exc
    if not isinstance(value, dict):
        raise R4ForgeError(f"exact JSON is not an object: {path}")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise R4ForgeError(f"append-only R4 evidence already exists: {path}") from exc


def verify_r4_harness(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    project_root = project_root.resolve()
    manifest_path = (project_root / R4_MANIFEST_REL).resolve()
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_harness_manifest_v4"
        or manifest.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN"
        or manifest.get("execution_allowed") is not True
    ):
        raise R4ForgeError("R4 harness has not passed a fresh independent audit")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R4ForgeError("R4 manifest file inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R4ForgeError("R4 manifest row is invalid")
        rel = str(row["path"])
        if rel in indexed:
            raise R4ForgeError("R4 manifest path is duplicated")
        path = (project_root / rel).resolve()
        try:
            path.relative_to(project_root)
        except ValueError as exc:
            raise R4ForgeError("R4 manifest path escaped the project") from exc
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R4ForgeError(f"R4 manifest file drift: {rel}")
        indexed[rel] = row
    required = {
        R4_WORKER_REL.as_posix(),
        R4_GUARDS_REL.as_posix(),
        R3_WORKER_REL.as_posix(),
        R3_GUARDS_REL.as_posix(),
        R2_WORKER_REL.as_posix(),
        "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py",
        "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py",
        "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py",
        "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json",
        "Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json",
        "Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json",
        "Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json",
        "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json",
        "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R3_INDEPENDENT_AUDIT_20260809.md",
    }
    if not required.issubset(indexed):
        raise R4ForgeError("R4 manifest omits a controlling predecessor or repair file")
    return manifest, indexed


def load_sealed_module(
    *, project_root: Path, rel: Path, row: dict[str, Any], module_name: str
) -> Any:
    path = (project_root / rel).resolve()
    if path.stat().st_size != row.get("bytes") or sha256_file(path) != row.get("sha256"):
        raise R4ForgeError(f"sealed module changed before import: {rel.as_posix()}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise R4ForgeError(f"cannot load sealed module: {rel.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != path or sha256_file(path) != row.get("sha256"):
        raise R4ForgeError(f"sealed module origin/hash changed after import: {rel.as_posix()}")
    return module


def configure_frozen_chain(r3_worker: Any, v2: Any, r3_guards: Any, r4_guards: Any) -> None:
    r4_guards.install_r4_wheel_override(r3_guards)
    r3_worker.R3_MANIFEST_REL = R4_MANIFEST_REL
    r3_worker.R3_WORKER_REL = R4_WORKER_REL
    r3_worker.R3_OUTPUT_ROOT_REL = R4_OUTPUT_ROOT_REL
    r3_worker.install_r3_preimport_guards(v2, r3_guards)


def _require_strict_binding_map(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"torch", "torchaudio"}:
        raise R4ForgeError(f"{label} lacks exact Torch/Torchaudio bindings")
    for package in ("torch", "torchaudio"):
        row = value.get(package)
        if (
            not isinstance(row, dict)
            or row.get("exact_wheel_to_installed_files_bound_r4") is not True
            or row.get("unbound_installer_generated_package_bytes_allowed") is not False
            or not isinstance(
                row.get("bounded_non_executable_installer_metadata_differences"), list
            )
        ):
            raise R4ForgeError(f"{label} {package} binding is not an R4 strict proof")


def execute_r4(
    *,
    project_root: Path,
    bundle_id: str,
    attempt_dir: Path,
    r3_worker: Any,
    v2: Any,
    r3_guards: Any,
    r4_guards: Any,
) -> dict[str, Any]:
    trusted = v2.load_trusted_bundle(
        project_root, bundle_id, require_ready_environment=True
    )
    binding = r4_guards.execution_binding(trusted.bundle)
    reservation = read_json(attempt_dir / "parent_reservation.json")
    for field, expected in binding.items():
        if reservation.get(field) != expected:
            raise R4ForgeError(f"parent reservation {field} binding mismatch")
    parent_job = reservation.get("verified_original_synthetic_job")
    if (
        not isinstance(parent_job, dict)
        or parent_job.get("sha256") != binding["job_sha256"]
        or parent_job.get("voice_origin")
        != "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE"
        or parent_job.get("identity_basis") != "original_trait_description"
        or trusted.job.get("voice_origin") != parent_job.get("voice_origin")
        or trusted.job.get("identity_basis") != parent_job.get("identity_basis")
    ):
        raise R4ForgeError("parent reservation original-synthetic job proof mismatch")
    _require_strict_binding_map(
        reservation.get("exact_wheel_to_installed_bindings"),
        "parent preflight",
    )

    r3_result = r3_worker.execute_r3(
        project_root=project_root,
        bundle_id=bundle_id,
        attempt_dir=attempt_dir,
        v2=v2,
        guards=r3_guards,
    )
    predecessor_profile_path = attempt_dir / "voice_profile_candidate_v3.json"
    predecessor_manifest_path = attempt_dir / "worker_manifest_v3.json"
    predecessor_profile = read_json(predecessor_profile_path)
    predecessor_manifest = read_json(predecessor_manifest_path)
    if (
        sha256_file(predecessor_profile_path) != r3_result.get("profile_sha256")
        or sha256_file(predecessor_manifest_path) != r3_result.get("manifest_sha256")
        or predecessor_manifest.get("profile_sha256")
        != sha256_file(predecessor_profile_path)
    ):
        raise R4ForgeError("R3 predecessor result/profile hashes are not exact")
    for field in ("bundle_id", "candidate_id", "opaque_voice_id"):
        expected = binding[field]
        if (
            predecessor_manifest.get(field) != expected
            or predecessor_profile.get(field) != expected
        ):
            raise R4ForgeError(f"R3 predecessor {field} mismatch")
    for field in (
        "ai_type",
        "job_sha256",
        "owner_authorization_sha256",
        "queue_binding_sha256",
        "canonical_profile_sha256",
        "canonical_creation_request_sha256",
    ):
        if predecessor_profile.get(field) != binding[field]:
            raise R4ForgeError(f"R3 predecessor profile {field} mismatch")

    r3_guards.validate_parent_artifacts(
        attempt_dir=attempt_dir,
        worker_manifest=predecessor_manifest,
        profile=predecessor_profile,
    )
    observed_seals = r4_guards.verify_exact_artifact_set(
        attempt_dir=attempt_dir,
        seals=predecessor_manifest.get("artifact_seals"),
        r3_guards=r3_guards,
    )
    predecessor_core_manifest = read_json(attempt_dir / "worker_manifest_v2.json")
    _require_strict_binding_map(
        (predecessor_core_manifest.get("environment") or {}).get(
            "exact_wheel_to_installed_bindings"
        ),
        "worker pre-model provenance",
    )
    _require_strict_binding_map(
        (predecessor_core_manifest.get("post_execution_environment_provenance") or {}).get(
            "exact_wheel_to_installed_bindings_reverified"
        ),
        "worker post-execution provenance",
    )

    prompt_evidence = predecessor_manifest.get("persisted_prompt_evidence")
    if not isinstance(prompt_evidence, dict):
        raise R4ForgeError("R3 predecessor prompt evidence is absent")
    profile = {
        **predecessor_profile,
        **binding,
        "schema": "qwen3_tts_original_voice_profile_candidate_v4",
        "r4_repair_status": "PARENT_OUTPUT_IDENTITY_HASH_AND_ARTIFACT_BINDING_ENFORCED",
        "predecessor_profile_sha256": sha256_file(predecessor_profile_path),
        "artifact_seals": observed_seals,
        "persisted_prompt_evidence": prompt_evidence,
        "assignment_allowed": False,
        "activation_allowed": False,
        "publication_or_upload_allowed": False,
        "owner_hearing_acceptance": "PENDING",
        "independent_audit": "REQUIRED",
    }
    profile_path = attempt_dir / "voice_profile_candidate_v4.json"
    write_new_json(profile_path, profile)
    profile_sha256 = sha256_file(profile_path)
    r4_guards.verify_exact_artifact_set(
        attempt_dir=attempt_dir, seals=observed_seals, r3_guards=r3_guards
    )

    manifest = {
        "schema": "qwen3_tts_original_voice_forge_worker_manifest_v4",
        "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
        **binding,
        "private_append_only": True,
        "single_use_nonce_consumed": True,
        "predecessor_worker_manifest_sha256": sha256_file(predecessor_manifest_path),
        "predecessor_profile_sha256": sha256_file(predecessor_profile_path),
        "profile_sha256": profile_sha256,
        "artifact_seals": observed_seals,
        "artifact_seals_sha256": r4_guards.canonical_sha256(observed_seals),
        "persisted_prompt_evidence": prompt_evidence,
        "strict_wheel_binding_preflight": reservation[
            "exact_wheel_to_installed_bindings"
        ],
        "strict_wheel_binding_worker_pre_model": predecessor_core_manifest[
            "environment"
        ]["exact_wheel_to_installed_bindings"],
        "strict_wheel_binding_worker_post_execution": predecessor_core_manifest[
            "post_execution_environment_provenance"
        ]["exact_wheel_to_installed_bindings_reverified"],
        "unbound_installer_generated_package_bytes_allowed": False,
        "owner_hearing_acceptance": "PENDING",
        "independent_audit": "REQUIRED",
        "watermark_status": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
        "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
        "network_nonuse_proven": False,
        "activation_assignment_publication_or_upload_allowed": False,
        "failure_policy": R4_FAILURE_STATUS,
        "clean_worker_exit": "PARENT_MUST_CONFIRM_AFTER_EXIT",
    }
    manifest_path = attempt_dir / "worker_manifest_v4.json"
    write_new_json(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)
    r4_guards.verify_exact_artifact_set(
        attempt_dir=attempt_dir, seals=observed_seals, r3_guards=r3_guards
    )
    child_result = {
        "schema": "qwen3_tts_original_voice_forge_child_result_v4",
        "status": manifest["status"],
        **binding,
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest_sha256,
        "profile_path": profile_path.name,
        "profile_sha256": profile_sha256,
        "artifact_seals_sha256": r4_guards.canonical_sha256(observed_seals),
    }
    reopened_manifest, reopened_profile, _derived = (
        r4_guards.reopen_and_validate_parent_outputs(
            attempt_dir=attempt_dir,
            child_result=child_result,
            expected_binding=binding,
            r3_guards=r3_guards,
        )
    )
    if reopened_manifest != manifest or reopened_profile != profile:
        raise R4ForgeError("R4 child outputs changed before the stdout hash handoff")
    return child_result


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
        raise R4ForgeError("R4 worker is inert without exact execution acknowledgement")
    if not args.bundle_id or not args.attempt_dir:
        raise R4ForgeError("bundle ID and parent-reserved attempt are required")
    _manifest, indexed = verify_r4_harness(PROJECT_ROOT)
    r4_guards = load_sealed_module(
        project_root=PROJECT_ROOT,
        rel=R4_GUARDS_REL,
        row=indexed[R4_GUARDS_REL.as_posix()],
        module_name="qwen3_tts_voice_forge_r4_guards_worker_sealed",
    )
    r3_guards = load_sealed_module(
        project_root=PROJECT_ROOT,
        rel=R3_GUARDS_REL,
        row=indexed[R3_GUARDS_REL.as_posix()],
        module_name="qwen3_tts_voice_forge_r3_guards_sealed_for_r4",
    )
    r3_worker = load_sealed_module(
        project_root=PROJECT_ROOT,
        rel=R3_WORKER_REL,
        row=indexed[R3_WORKER_REL.as_posix()],
        module_name="qwen3_tts_original_voice_forge_worker_v3_sealed_for_r4",
    )
    v2 = load_sealed_module(
        project_root=PROJECT_ROOT,
        rel=R2_WORKER_REL,
        row=indexed[R2_WORKER_REL.as_posix()],
        module_name="qwen3_tts_original_voice_forge_worker_v2_sealed_for_r4",
    )
    configure_frozen_chain(r3_worker, v2, r3_guards, r4_guards)
    result = execute_r4(
        project_root=PROJECT_ROOT,
        bundle_id=args.bundle_id,
        attempt_dir=Path(args.attempt_dir).resolve(),
        r3_worker=r3_worker,
        v2=v2,
        r3_guards=r3_guards,
        r4_guards=r4_guards,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R4 Qwen3-TTS forge failed closed: {exc}", file=sys.stderr)
        if not isinstance(exc, (R4ForgeError, SystemExit)):
            traceback.print_exc()
        raise SystemExit(2)
