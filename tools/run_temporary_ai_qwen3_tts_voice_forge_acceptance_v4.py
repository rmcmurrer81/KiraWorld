"""Parent-reserved append-only R4 launcher for the inert voice forge.

Only an opaque trusted bundle ID is caller-selectable.  R4 preserves the exact
R3/R2 synthesis and evaluation chain, tightens wheel/install reconciliation,
and treats one exact result received from the verified child's stdout pipe as
the hash anchor for all parent-read profile, manifest, identity, job, and final
artifact evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R4_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json")
R4_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v4.py")
R4_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R3_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R3_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R2_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_CONTRACT_REL = Path("TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json")
R2_ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
R2_REGISTRY_REL = Path("Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json")
OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v4")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"


class R4LauncherError(RuntimeError):
    """The append-only R4 parent launcher failed closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
        raise R4LauncherError(f"cannot read exact JSON: {path}") from exc
    if not isinstance(value, dict):
        raise R4LauncherError(f"exact JSON is not an object: {path}")
    return value


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise R4LauncherError(f"append-only R4 evidence already exists: {path}") from exc


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    write_new(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n",
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def verify_r4_harness() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = (PROJECT_ROOT / R4_MANIFEST_REL).resolve()
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_harness_manifest_v4"
        or manifest.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN"
        or manifest.get("execution_allowed") is not True
    ):
        raise R4LauncherError("R4 harness has not passed a fresh independent audit")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R4LauncherError("R4 manifest inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R4LauncherError("R4 manifest row is invalid")
        rel = str(row["path"])
        if rel in indexed:
            raise R4LauncherError("R4 manifest path is duplicated")
        path = (PROJECT_ROOT / rel).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve())
        except ValueError as exc:
            raise R4LauncherError("R4 manifest path escaped the project") from exc
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R4LauncherError(f"R4 manifest file drift: {rel}")
        indexed[rel] = row
    required = {
        R4_WORKER_REL.as_posix(),
        R4_RUNNER_REL.as_posix(),
        R4_GUARDS_REL.as_posix(),
        R3_MANIFEST_REL.as_posix(),
        R3_WORKER_REL.as_posix(),
        R3_RUNNER_REL.as_posix(),
        R3_GUARDS_REL.as_posix(),
        R2_RUNNER_REL.as_posix(),
        R2_WORKER_REL.as_posix(),
        R2_CONTRACT_REL.as_posix(),
        R2_ENVIRONMENT_REL.as_posix(),
        R2_REGISTRY_REL.as_posix(),
        "Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json",
        "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R3_INDEPENDENT_AUDIT_20260809.md",
    }
    if not required.issubset(indexed):
        raise R4LauncherError("R4 manifest omits a controlling predecessor or repair file")
    return manifest, indexed


def load_sealed_module(rel: Path, row: dict[str, Any], module_name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if path.stat().st_size != row.get("bytes") or sha256_file(path) != row.get("sha256"):
        raise R4LauncherError(f"sealed launcher dependency changed: {rel.as_posix()}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise R4LauncherError(f"cannot load sealed launcher dependency: {rel.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != path or sha256_file(path) != row.get("sha256"):
        raise R4LauncherError(
            f"sealed launcher dependency drifted after import: {rel.as_posix()}"
        )
    return module


def configure_frozen_chain(
    r3_runner: Any, v2: Any, r3_guards: Any, r4_guards: Any
) -> None:
    r4_guards.install_r4_wheel_override(r3_guards)
    r3_runner.R3_MANIFEST_REL = R4_MANIFEST_REL
    r3_runner.R3_WORKER_REL = R4_WORKER_REL
    r3_runner.R3_RUNNER_REL = R4_RUNNER_REL
    r3_runner.OUTPUT_ROOT_REL = OUTPUT_ROOT_REL
    r3_runner.install_runner_guards(v2, r3_guards)


def validate_bound_original_job(
    v2: Any, bundle: dict[str, Any], bundle_dir: Path
) -> dict[str, Any]:
    """Verify the exact sealed original-trait job before nonce consumption."""

    job_path = v2.inside(
        bundle_dir, str(bundle.get("job_path") or ""), "R4 exact sealed job"
    )
    v2.verify_file(job_path, bundle.get("job_sha256"), "R4 exact sealed job")
    job = read_json(job_path)
    if job.get("schema") != "qwen3_tts_original_voice_forge_job_v2":
        raise R4LauncherError("R4 exact job schema mismatch")
    if (
        job.get("voice_origin")
        != "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE"
        or job.get("identity_basis") != "original_trait_description"
    ):
        raise R4LauncherError("R4 job is not the original synthetic trait lane")
    for prefix in ("design_traits", "reference", "test"):
        text = str(job.get(f"{prefix}_text") or "")
        expected = str(job.get(f"{prefix}_text_sha256") or "")
        if not text.strip() or v2.sha256_text(text) != expected:
            raise R4LauncherError(f"R4 exact job {prefix} text/hash mismatch")
    if not str(job.get("language") or "").strip():
        raise R4LauncherError("R4 exact job language is empty")
    return {
        "path": v2.relative(job_path, bundle_dir),
        "bytes": job_path.stat().st_size,
        "sha256": sha256_file(job_path),
        "schema": job["schema"],
        "voice_origin": job["voice_origin"],
        "identity_basis": job["identity_basis"],
        "design_traits_text_sha256": job["design_traits_text_sha256"],
        "reference_text_sha256": job["reference_text_sha256"],
        "test_text_sha256": job["test_text_sha256"],
        "language": job["language"],
    }


def _require_strict_binding_map(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"torch", "torchaudio"}:
        raise R4LauncherError(f"{label} lacks exact Torch/Torchaudio bindings")
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
            raise R4LauncherError(f"{label} {package} binding is not strict R4 evidence")


def reserve_attempt(bundle_id: str) -> Path:
    root = (PROJECT_ROOT / OUTPUT_ROOT_REL / bundle_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        attempt = root / f"attempt_{index:02d}"
        try:
            attempt.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return attempt
    raise R4LauncherError("no bounded append-only R4 attempt slot remains")


def restricted_child_environment(v2: Any, isolated_python: Path) -> dict[str, str]:
    env = v2.restricted_child_environment(isolated_python=isolated_python)
    cache_root = PROJECT_ROOT / "RecoverySprint/runtime_cache/qwen3_tts_voice_forge_v4"
    temp = cache_root / "temp"
    hf = cache_root / "huggingface"
    torch_cache = cache_root / "torch"
    for path in (temp, hf, torch_cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "TEMP": str(temp),
            "TMP": str(temp),
            "HF_HOME": str(hf),
            "TORCH_HOME": str(torch_cache),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }
    )
    return env


def preserve_failure(attempt: Path, exc: BaseException, stage: str, started: bool) -> None:
    evidence = {
        "schema": "qwen3_tts_voice_forge_parent_failure_v4",
        "status": FAILURE_STATUS,
        "utc": utc_now(),
        "stage": stage,
        "worker_started": started,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
        "current_voice_route_changed": False,
    }
    name = "parent_started_or_post_failure_v4.json" if started else "parent_preflight_failure_v4.json"
    try:
        write_new_json(attempt / name, evidence)
    except BaseException:
        pass


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.execute:
        raise R4LauncherError("R4 launcher is inert without --execute")
    if not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise R4LauncherError("both bounded execution acknowledgements are required")
    if not args.bundle_id or not SAFE_ID.fullmatch(args.bundle_id):
        raise R4LauncherError("one safe opaque --bundle-id is required")
    attempt = reserve_attempt(args.bundle_id)
    stage = "R4_HARNESS_MANIFEST"
    worker_started = False
    try:
        _manifest, indexed = verify_r4_harness()
        r4_guards = load_sealed_module(
            R4_GUARDS_REL,
            indexed[R4_GUARDS_REL.as_posix()],
            "qwen3_tts_voice_forge_r4_guards_parent_sealed",
        )
        r3_guards = load_sealed_module(
            R3_GUARDS_REL,
            indexed[R3_GUARDS_REL.as_posix()],
            "qwen3_tts_voice_forge_r3_guards_parent_sealed_for_r4",
        )
        r3_runner = load_sealed_module(
            R3_RUNNER_REL,
            indexed[R3_RUNNER_REL.as_posix()],
            "qwen3_tts_voice_forge_runner_v3_sealed_for_r4",
        )
        v2 = load_sealed_module(
            R2_RUNNER_REL,
            indexed[R2_RUNNER_REL.as_posix()],
            "qwen3_tts_voice_forge_runner_v2_sealed_for_r4",
        )
        configure_frozen_chain(r3_runner, v2, r3_guards, r4_guards)
        contract = read_json(PROJECT_ROOT / R2_CONTRACT_REL)
        environment = read_json(PROJECT_ROOT / R2_ENVIRONMENT_REL)
        worker_path = (PROJECT_ROOT / R4_WORKER_REL).resolve()

        stage = "TRUSTED_BUNDLE_ENVELOPE"
        bundle, entry, bundle_dir = v2.verify_bundle_envelope(args.bundle_id)
        binding = r4_guards.execution_binding(bundle)
        stage = "EXACT_ORIGINAL_SYNTHETIC_JOB"
        job_evidence = validate_bound_original_job(v2, bundle, bundle_dir)
        if job_evidence["sha256"] != binding["job_sha256"]:
            raise R4LauncherError("R4 original job is not bound to the execution identity")
        stage = "R4_ISOLATED_ENVIRONMENT"
        isolated_python, exact_bindings = r3_runner.validate_ready_environment_r3(
            v2=v2,
            guards=r3_guards,
            contract=contract,
            environment=environment,
            worker_path=worker_path,
        )
        _require_strict_binding_map(exact_bindings, "parent preflight")

        stage = "SINGLE_USE_NONCE"
        ledger_path, ledger_hash = v2.consume_nonce(bundle, attempt)
        reservation = {
            "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
            "r4_schema": "qwen3_tts_voice_forge_parent_reservation_v4",
            "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
            "r4_status": "R4_STRICT_WHEEL_AND_OUTPUT_BINDING_PREFLIGHT_PASSED",
            "utc": utc_now(),
            **binding,
            **v2.queue_binding_payload(bundle),
            "attempt": relative(attempt),
            "nonce_ledger_path": relative(ledger_path),
            "nonce_ledger_sha256": ledger_hash,
            "verified_worker_path": R2_WORKER_REL.as_posix(),
            "verified_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
            "verified_entry_worker_path": R4_WORKER_REL.as_posix(),
            "verified_entry_worker_sha256": sha256_file(worker_path),
            "verified_frozen_core_worker_path": R2_WORKER_REL.as_posix(),
            "verified_frozen_core_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
            "verified_frozen_r3_worker_path": R3_WORKER_REL.as_posix(),
            "verified_frozen_r3_worker_sha256": sha256_file(PROJECT_ROOT / R3_WORKER_REL),
            "harness_manifest_sha256": sha256_file(PROJECT_ROOT / R4_MANIFEST_REL),
            "contract_sha256": sha256_file(PROJECT_ROOT / R2_CONTRACT_REL),
            "environment_spec_sha256": sha256_file(PROJECT_ROOT / R2_ENVIRONMENT_REL),
            "trusted_registry_sha256": sha256_file(PROJECT_ROOT / R2_REGISTRY_REL),
            "bundle_seal_sha256": entry["bundle_seal_sha256"],
            "verified_original_synthetic_job": job_evidence,
            "exact_wheel_to_installed_bindings": exact_bindings,
            "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
            "network_nonuse_proven": False,
        }
        write_new_json(attempt / "parent_reservation.json", reservation)

        command = [
            str(isolated_python),
            "-I",
            "-B",
            str(worker_path),
            "--execute",
            "--bundle-id",
            args.bundle_id,
            "--attempt-dir",
            str(attempt),
            "--acknowledge-private-unreviewed",
        ]
        stage = "R4_WORKER_PROCESS"
        started = time.perf_counter()
        worker_started = True
        try:
            completed = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                env=restricted_child_environment(v2, isolated_python),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1800,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise R4LauncherError("verified R4 worker timed out") from exc
        elapsed = time.perf_counter() - started
        write_new(attempt / "worker_stdout_v4.log", completed.stdout)
        write_new(attempt / "worker_stderr_v4.log", completed.stderr)
        if completed.returncode != 0:
            raise R4LauncherError(
                f"verified R4 worker failed closed with return code {completed.returncode}"
            )

        stage = "R4_CHILD_RESULT_BINDING"
        child_result = r4_guards.parse_child_result(completed.stdout, binding)
        worker_manifest, profile, parent_evidence = (
            r4_guards.reopen_and_validate_parent_outputs(
                attempt_dir=attempt,
                child_result=child_result,
                expected_binding=binding,
                r3_guards=r3_guards,
            )
        )
        _require_strict_binding_map(
            worker_manifest.get("strict_wheel_binding_preflight"),
            "worker manifest parent preflight",
        )
        _require_strict_binding_map(
            worker_manifest.get("strict_wheel_binding_worker_pre_model"),
            "worker manifest pre-model",
        )
        _require_strict_binding_map(
            worker_manifest.get("strict_wheel_binding_worker_post_execution"),
            "worker manifest post-execution",
        )

        summary = {
            "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v4",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
            **binding,
            "attempt": relative(attempt),
            "worker_returncode": completed.returncode,
            "worker_process_seconds": elapsed,
            "clean_worker_exit": True,
            "verified_child_stdout_sha256": sha256_bytes(completed.stdout),
            "verified_child_result": child_result,
            "verified_original_synthetic_job": job_evidence,
            "worker_manifest_sha256": child_result["manifest_sha256"],
            "voice_profile_candidate_sha256": child_result["profile_sha256"],
            "parent_artifact_identity_and_hash_revalidation": parent_evidence,
            "strict_wheel_binding_enforced": True,
            "owner_hearing_acceptance": "PENDING",
            "independent_audit": "REQUIRED",
            "watermark_status": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
            "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
            "network_nonuse_proven": False,
            "activation_assignment_publication_or_upload_allowed": False,
            "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
        }

        # Re-read the two exact stdout-bound JSON files and independently reopen
        # all three fixed artifacts immediately before parent acceptance.
        worker_manifest_2, profile_2, final_evidence = (
            r4_guards.reopen_and_validate_parent_outputs(
                attempt_dir=attempt,
                child_result=child_result,
                expected_binding=binding,
                r3_guards=r3_guards,
            )
        )
        if (
            worker_manifest_2 != worker_manifest
            or profile_2 != profile
            or final_evidence != parent_evidence
        ):
            raise R4LauncherError("R4 parent evidence changed between independent reopens")
        acceptance_path = attempt / "parent_acceptance_v4.json"
        write_new_json(acceptance_path, summary)
        return {**summary, "parent_acceptance_sha256": sha256_file(acceptance_path)}
    except BaseException as exc:
        preserve_failure(attempt, exc, stage, worker_started)
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
    except BaseException as exc:
        print(f"R4 Qwen3-TTS parent failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
