"""Append-only R4 evidence guards for the inert TemporaryAI voice forge.

This module is deliberately stdlib-only.  It adds three fail-closed controls
without importing Torch, Qwen3-TTS, evaluators, or any model:

* installer-generated differences are limited to three exact, non-executable
  distribution-metadata files;
* the parent parses and trusts one exact hash-bearing child result from the
  verified stdout pipe; and
* candidate/job/profile identity plus three fixed, distinct final artifacts
  are independently reconciled before parent acceptance.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


HASH = re.compile(r"[0-9a-f]{64}")
FINAL_ARTIFACT_PATHS = {
    "reference_wav": "original_design_reference.wav",
    "clone_test_wav": "runtime_clone_test.wav",
    "runtime_clone_prompt": "runtime_clone_prompt.pt",
}
EXECUTION_BINDING_FIELDS = (
    "bundle_id",
    "candidate_id",
    "opaque_voice_id",
    "ai_type",
    "job_sha256",
    "owner_authorization_sha256",
    "queue_binding_sha256",
    "canonical_profile_sha256",
    "canonical_creation_request_sha256",
    "identity_clearance_manifest_sha256",
    "watermark_evidence_manifest_sha256",
    "evaluation_corpus_sha256",
    "voice_design_model_manifest_sha256",
    "base_model_manifest_sha256",
    "environment_spec_sha256",
)


class R4GuardError(RuntimeError):
    """An R4 evidence or provenance check failed closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def require_hash(value: Any, label: str) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text):
        raise R4GuardError(f"{label} is not one lowercase SHA-256")
    return text


def inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(str(value))
    if candidate.is_absolute():
        result = candidate.resolve()
    else:
        result = (root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R4GuardError(f"{label} escaped its exact root") from exc
    return result


def execution_binding(bundle: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in EXECUTION_BINDING_FIELDS:
        value = str(bundle.get(field) or "")
        if not value:
            raise R4GuardError(f"execution binding field is empty: {field}")
        result[field] = value
    for field in EXECUTION_BINDING_FIELDS:
        if field.endswith("_sha256"):
            require_hash(result[field], f"execution binding {field}")
    return result


def _bounded_installer_metadata_paths(wheel_evidence: dict[str, Any]) -> dict[str, str]:
    record = str(wheel_evidence.get("record_path") or "")
    if "/" not in record or not record.endswith(".dist-info/RECORD"):
        raise R4GuardError("exact wheel RECORD path cannot define its metadata root")
    metadata_root = record.rsplit("/", 1)[0]
    return {
        "INSTALLER_METADATA": metadata_root + "/INSTALLER",
        "DIRECT_URL_METADATA": metadata_root + "/direct_url.json",
        "REQUESTED_METADATA": metadata_root + "/REQUESTED",
    }


def validate_installer_generated_differences(
    *, package: str, row: dict[str, Any], wheel_evidence: dict[str, Any]
) -> list[str]:
    """Reject every unbound package/code/bytecode difference.

    R4 intentionally does not accept generated ``.pyc`` files: a declared
    hash proves only which bytes are present, not that those executable bytes
    were derived from the exact wheel source.  A later successor may add a
    real derivation proof, but a reason label alone is insufficient.
    """

    declared = row.get("installer_generated_files")
    if not isinstance(declared, list):
        raise R4GuardError(
            f"{package} installer-generated differences are not an exact list"
        )
    allowed = _bounded_installer_metadata_paths(wheel_evidence)
    package_prefix = str(wheel_evidence.get("real_package_root") or "") + "/"
    accepted: list[str] = []
    seen: set[str] = set()
    for extra in declared:
        if not isinstance(extra, dict):
            raise R4GuardError(f"{package} installer-generated row is invalid")
        path = str(extra.get("path") or "")
        reason = str(extra.get("reason") or "")
        if not path or path in seen:
            raise R4GuardError(
                f"{package} installer-generated path is empty or duplicated"
            )
        seen.add(path)
        require_hash(extra.get("sha256"), f"{package} installer-generated hash")
        if not isinstance(extra.get("bytes"), int) or extra["bytes"] < 0:
            raise R4GuardError(
                f"{package} installer-generated byte count is invalid"
            )
        if reason == "INSTALLER_GENERATED_BYTECODE":
            raise R4GuardError(
                f"{package} unbound installer-generated bytecode is prohibited"
            )
        if path.startswith(package_prefix):
            raise R4GuardError(
                f"{package} unbound package payload cannot be an installer difference"
            )
        if reason not in allowed or path != allowed[reason]:
            raise R4GuardError(
                f"{package} installer difference is not exact bounded metadata"
            )
        accepted.append(path)
    return sorted(accepted)


def bind_wheel_to_installed_distribution(
    *,
    r3_guards: Any,
    project_root: Path,
    isolated_venv_rel: Path,
    package: str,
    row: dict[str, Any],
    installed_evidence: dict[str, Any],
    wheel_evidence: dict[str, Any],
) -> dict[str, Any]:
    bounded = validate_installer_generated_differences(
        package=package, row=row, wheel_evidence=wheel_evidence
    )
    result = r3_guards.bind_wheel_to_installed_distribution(
        project_root=project_root,
        isolated_venv_rel=isolated_venv_rel,
        package=package,
        row=row,
        installed_evidence=installed_evidence,
        wheel_evidence=wheel_evidence,
    )
    if sorted(result.get("installer_generated_differences") or []) != bounded:
        raise R4GuardError(
            f"{package} R3/R4 installer-difference reconciliation disagrees"
        )
    return {
        **result,
        "bounded_non_executable_installer_metadata_differences": bounded,
        "unbound_installer_generated_package_bytes_allowed": False,
        "exact_wheel_to_installed_files_bound_r4": True,
    }


def install_r4_wheel_override(r3_guards: Any) -> None:
    """Install the R4 wheel rule into one already hash-verified R3 module."""

    if getattr(r3_guards, "_r4_wheel_override_installed", False):
        return
    original = r3_guards.bind_wheel_to_installed_distribution

    def strict_bind(**kwargs: Any) -> dict[str, Any]:
        bounded = validate_installer_generated_differences(
            package=kwargs["package"],
            row=kwargs["row"],
            wheel_evidence=kwargs["wheel_evidence"],
        )
        result = original(**kwargs)
        if sorted(result.get("installer_generated_differences") or []) != bounded:
            raise R4GuardError(
                f"{kwargs['package']} R3/R4 installer-difference reconciliation disagrees"
            )
        return {
            **result,
            "bounded_non_executable_installer_metadata_differences": bounded,
            "unbound_installer_generated_package_bytes_allowed": False,
            "exact_wheel_to_installed_files_bound_r4": True,
        }

    r3_guards.bind_wheel_to_installed_distribution = strict_bind
    r3_guards._r4_wheel_override_installed = True


def parse_child_result(
    stdout: bytes, expected_binding: dict[str, str]
) -> dict[str, Any]:
    """Parse one and only one exact result emitted by the verified child."""

    try:
        text = stdout.decode("utf-8")
    except UnicodeError as exc:
        raise R4GuardError("verified child stdout is not UTF-8") from exc
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise R4GuardError("verified child did not emit exactly one result object")
    try:
        result = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise R4GuardError("verified child result is not exact JSON") from exc
    if not isinstance(result, dict):
        raise R4GuardError("verified child result is not an object")
    exact_keys = {
        "schema",
        "status",
        *EXECUTION_BINDING_FIELDS,
        "manifest_path",
        "manifest_sha256",
        "profile_path",
        "profile_sha256",
        "artifact_seals_sha256",
    }
    if set(result) != exact_keys:
        raise R4GuardError("verified child result fields are incomplete or unexpected")
    if result.get("schema") != "qwen3_tts_original_voice_forge_child_result_v4":
        raise R4GuardError("verified child result schema mismatch")
    if (
        result.get("status")
        != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT"
    ):
        raise R4GuardError("verified child did not report the exact R4 pass status")
    for field, expected in expected_binding.items():
        if result.get(field) != expected:
            raise R4GuardError(f"verified child result {field} binding mismatch")
    if result.get("manifest_path") != "worker_manifest_v4.json":
        raise R4GuardError("verified child manifest path is not fixed")
    if result.get("profile_path") != "voice_profile_candidate_v4.json":
        raise R4GuardError("verified child profile path is not fixed")
    for field in ("manifest_sha256", "profile_sha256", "artifact_seals_sha256"):
        require_hash(result.get(field), f"verified child {field}")
    return result


def read_hash_bound_json(
    path: Path, expected_sha256: str, label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = require_hash(expected_sha256, f"{label} expected hash")
    if not path.is_file() or path.is_symlink():
        raise R4GuardError(f"{label} is missing, non-regular, or a symlink")
    payload = path.read_bytes()
    actual = sha256_bytes(payload)
    if actual != expected:
        raise R4GuardError(f"{label} differs from the verified child result")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R4GuardError(f"{label} is not exact UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R4GuardError(f"{label} is not an object")
    return value, {"bytes": len(payload), "sha256": actual}


def verify_exact_artifact_set(
    *, attempt_dir: Path, seals: dict[str, Any], r3_guards: Any
) -> dict[str, Any]:
    if not isinstance(seals, dict) or set(seals) != set(FINAL_ARTIFACT_PATHS):
        raise R4GuardError("R4 final artifact seal set is incomplete")
    supplied_paths: list[str] = []
    for key, expected_path in FINAL_ARTIFACT_PATHS.items():
        seal = seals.get(key)
        if not isinstance(seal, dict) or seal.get("path") != expected_path:
            raise R4GuardError(f"{key} seal is not bound to {expected_path}")
        supplied_paths.append(str(seal["path"]))
    if len(set(supplied_paths)) != len(supplied_paths):
        raise R4GuardError("R4 final artifacts are not three distinct paths")
    if seals["reference_wav"].get("kind") != "READABLE_NON_SILENT_MONO_PCM16_WAV":
        raise R4GuardError("reference WAV seal kind mismatch")
    if seals["clone_test_wav"].get("kind") != "READABLE_NON_SILENT_MONO_PCM16_WAV":
        raise R4GuardError("clone WAV seal kind mismatch")
    if seals["runtime_clone_prompt"].get("kind") != "PERSISTED_RUNTIME_CLONE_PROMPT":
        raise R4GuardError("runtime prompt seal kind mismatch")

    reference = r3_guards.seal_pcm16_wav(
        attempt_dir / FINAL_ARTIFACT_PATHS["reference_wav"], attempt_dir
    )
    clone = r3_guards.seal_pcm16_wav(
        attempt_dir / FINAL_ARTIFACT_PATHS["clone_test_wav"], attempt_dir
    )
    prompt = r3_guards.seal_prompt_file(
        attempt_dir / FINAL_ARTIFACT_PATHS["runtime_clone_prompt"],
        attempt_dir,
        seals["runtime_clone_prompt"].get("semantic_sha256"),
    )
    observed = {
        "reference_wav": reference,
        "clone_test_wav": clone,
        "runtime_clone_prompt": prompt,
    }
    if observed != seals:
        raise R4GuardError("R4 final artifact seals differ from independent reopen")
    return observed


def validate_bound_parent_outputs(
    *,
    attempt_dir: Path,
    worker_manifest: dict[str, Any],
    profile: dict[str, Any],
    manifest_file_evidence: dict[str, Any],
    profile_file_evidence: dict[str, Any],
    child_result: dict[str, Any],
    expected_binding: dict[str, str],
    r3_guards: Any,
) -> dict[str, Any]:
    if worker_manifest.get("schema") != "qwen3_tts_original_voice_forge_worker_manifest_v4":
        raise R4GuardError("parent received the wrong R4 worker manifest schema")
    if profile.get("schema") != "qwen3_tts_original_voice_profile_candidate_v4":
        raise R4GuardError("parent received the wrong R4 profile schema")
    exact_status = "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT"
    if worker_manifest.get("status") != exact_status or child_result.get("status") != exact_status:
        raise R4GuardError("R4 worker/child status mismatch")
    if profile.get("status") != "PRIVATE_UNREVIEWED_ENGINEERING_PASS_OWNER_HEARING_PENDING":
        raise R4GuardError("R4 profile status mismatch")
    if manifest_file_evidence.get("sha256") != child_result.get("manifest_sha256"):
        raise R4GuardError("R4 manifest is not bound to verified child stdout")
    if profile_file_evidence.get("sha256") != child_result.get("profile_sha256"):
        raise R4GuardError("R4 profile is not bound to verified child stdout")
    if worker_manifest.get("profile_sha256") != profile_file_evidence.get("sha256"):
        raise R4GuardError("R4 worker manifest profile hash mismatch")

    for field, expected in expected_binding.items():
        if (
            child_result.get(field) != expected
            or worker_manifest.get(field) != expected
            or profile.get(field) != expected
        ):
            raise R4GuardError(f"R4 child/manifest/profile {field} mismatch")

    seals = worker_manifest.get("artifact_seals")
    if profile.get("artifact_seals") != seals:
        raise R4GuardError("R4 worker/profile artifact seals differ")
    seals_sha256 = canonical_sha256(seals)
    if (
        seals_sha256 != child_result.get("artifact_seals_sha256")
        or worker_manifest.get("artifact_seals_sha256") != seals_sha256
    ):
        raise R4GuardError("R4 artifact seals are not bound to verified child stdout")
    observed = verify_exact_artifact_set(
        attempt_dir=attempt_dir, seals=seals, r3_guards=r3_guards
    )

    prompt = worker_manifest.get("persisted_prompt_evidence")
    if not isinstance(prompt, dict) or profile.get("persisted_prompt_evidence") != prompt:
        raise R4GuardError("R4 profile/worker prompt evidence differs")
    if (
        prompt.get("persisted_prompt_reload_used_for_generation") is not True
        or prompt.get("in_memory_caller_prompt_used_for_generation") is not False
        or prompt.get("exact_saved_reference_reloaded") is not True
        or prompt.get("reference_wav_sha256") != observed["reference_wav"]["sha256"]
        or prompt.get("sha256") != observed["runtime_clone_prompt"]["sha256"]
        or prompt.get("artifact_seal") != observed["runtime_clone_prompt"]
        or prompt.get("created_prompt_semantic_sha256")
        != prompt.get("reloaded_prompt_semantic_sha256")
        or prompt.get("reloaded_prompt_semantic_sha256")
        != observed["runtime_clone_prompt"]["semantic_sha256"]
    ):
        raise R4GuardError("R4 persisted prompt use is not exactly artifact-bound")

    evaluator = profile.get("evaluator_mutation_guard")
    expected_wav_seals = {
        "reference_wav": observed["reference_wav"],
        "clone_test_wav": observed["clone_test_wav"],
    }
    if (
        not isinstance(evaluator, dict)
        or evaluator.get("artifact_seals") != expected_wav_seals
        or evaluator.get("checked_before_and_after_every_evaluator_operation") is not True
        or not isinstance(evaluator.get("checkpoints"), list)
        or not evaluator["checkpoints"]
        or evaluator["checkpoints"][-1] != "before_worker_acceptance"
    ):
        raise R4GuardError("R4 evaluator mutation evidence is not exact-artifact-bound")

    legacy = profile.get("artifacts")
    if not isinstance(legacy, dict):
        raise R4GuardError("R4 profile lacks predecessor artifact evidence")
    if (
        (legacy.get("reference_wav") or {}).get("sha256")
        != observed["reference_wav"]["sha256"]
        or (legacy.get("clone_test_wav") or {}).get("sha256")
        != observed["clone_test_wav"]["sha256"]
        or legacy.get("clone_prompt_sha256")
        != observed["runtime_clone_prompt"]["sha256"]
    ):
        raise R4GuardError("R4 predecessor artifact evidence differs from exact seals")
    if (
        profile.get("assignment_allowed") is not False
        or profile.get("activation_allowed") is not False
        or profile.get("publication_or_upload_allowed") is not False
        or profile.get("owner_hearing_acceptance") != "PENDING"
    ):
        raise R4GuardError("R4 profile overstates owner acceptance or use permission")
    return {
        "verified_child_manifest_sha256": manifest_file_evidence["sha256"],
        "verified_child_profile_sha256": profile_file_evidence["sha256"],
        "verified_child_artifact_seals_sha256": canonical_sha256(observed),
        "verified_execution_binding": dict(expected_binding),
        "independently_reopened_exact_distinct_artifacts": observed,
        "child_stdout_manifest_profile_hashes_enforced": True,
        "candidate_job_authorization_binding_enforced": True,
        "all_parent_acceptance_fields_derived_not_self_asserted": True,
    }


def reopen_and_validate_parent_outputs(
    *,
    attempt_dir: Path,
    child_result: dict[str, Any],
    expected_binding: dict[str, str],
    r3_guards: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest, manifest_file = read_hash_bound_json(
        attempt_dir / "worker_manifest_v4.json",
        child_result["manifest_sha256"],
        "R4 worker manifest",
    )
    profile, profile_file = read_hash_bound_json(
        attempt_dir / "voice_profile_candidate_v4.json",
        child_result["profile_sha256"],
        "R4 profile",
    )
    evidence = validate_bound_parent_outputs(
        attempt_dir=attempt_dir,
        worker_manifest=manifest,
        profile=profile,
        manifest_file_evidence=manifest_file,
        profile_file_evidence=profile_file,
        child_result=child_result,
        expected_binding=expected_binding,
        r3_guards=r3_guards,
    )
    return manifest, profile, evidence
