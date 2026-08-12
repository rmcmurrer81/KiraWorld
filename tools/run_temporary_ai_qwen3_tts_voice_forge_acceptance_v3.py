"""Parent-reserved append-only R3 launcher for the inert voice forge.

Only a trusted bundle ID is caller-selectable.  The launcher verifies the
fresh R3 audit gate, every sealed source, authoritative installed-distribution
enumeration, and exact Torch/Torchaudio wheel-to-install bindings before it
starts the worker.  After a clean worker exit it independently reopens the
prompt and both WAVs before writing parent acceptance.
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
R3_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R3_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R2_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_CONTRACT_REL = Path("TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json")
R2_ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
R2_REGISTRY_REL = Path("Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json")
OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v3")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"


class R3LauncherError(RuntimeError):
    """The append-only R3 parent launcher failed closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        raise R3LauncherError(f"cannot read trusted JSON: {path}") from exc
    if not isinstance(value, dict):
        raise R3LauncherError(f"trusted JSON is not an object: {path}")
    return value


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise R3LauncherError(f"append-only R3 evidence already exists: {path}") from exc


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    write_new(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n",
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def verify_r3_harness() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = (PROJECT_ROOT / R3_MANIFEST_REL).resolve()
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_harness_manifest_v3"
        or manifest.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN"
        or manifest.get("execution_allowed") is not True
    ):
        raise R3LauncherError("R3 harness has not passed a fresh independent audit")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R3LauncherError("R3 manifest inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R3LauncherError("R3 manifest row is invalid")
        rel = str(row["path"])
        if rel in indexed:
            raise R3LauncherError("R3 manifest path is duplicated")
        path = (PROJECT_ROOT / rel).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve())
        except ValueError as exc:
            raise R3LauncherError("R3 manifest path escaped the project") from exc
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R3LauncherError(f"R3 manifest file drift: {rel}")
        indexed[rel] = row
    required = {
        R3_WORKER_REL.as_posix(), R3_RUNNER_REL.as_posix(), R3_GUARDS_REL.as_posix(),
        R2_RUNNER_REL.as_posix(), R2_WORKER_REL.as_posix(), R2_CONTRACT_REL.as_posix(),
        R2_ENVIRONMENT_REL.as_posix(), R2_REGISTRY_REL.as_posix(),
    }
    if not required.issubset(indexed):
        raise R3LauncherError("R3 manifest omits a controlling predecessor or repair file")
    return manifest, indexed


def load_sealed_module(rel: Path, row: dict[str, Any], module_name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if path.stat().st_size != row.get("bytes") or sha256_file(path) != row.get("sha256"):
        raise R3LauncherError(f"sealed launcher dependency changed: {rel.as_posix()}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise R3LauncherError(f"cannot load sealed launcher dependency: {rel.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != path or sha256_file(path) != row.get("sha256"):
        raise R3LauncherError(f"sealed launcher dependency drifted after import: {rel.as_posix()}")
    return module


def install_runner_guards(v2: Any, guards: Any) -> None:
    original_site = v2.verify_complete_site_packages_inventory

    def site_guard(spec: dict[str, Any], distribution_evidence: dict[str, Any]) -> dict[str, Any]:
        return guards.verify_authoritative_distribution_inventory(
            project_root=PROJECT_ROOT,
            isolated_venv_rel=v2.ISOLATED_VENV_REL,
            spec=spec,
            distribution_evidence=distribution_evidence,
            base_verifier=original_site,
            base_verifier_style="runner",
        )

    def wheel_payload_guard(package: str, row: dict[str, Any]) -> dict[str, Any]:
        return guards.attest_wheel_archive(
            project_root=PROJECT_ROOT,
            wheel_root_rel=v2.WHEEL_EVIDENCE_ROOT_REL,
            package=package,
            row=row,
        )

    v2.verify_complete_site_packages_inventory = site_guard
    v2.verify_wheel_archive = wheel_payload_guard
    v2.WORKER_REL = R3_WORKER_REL
    v2.HARNESS_MANIFEST_REL = R3_MANIFEST_REL


def validate_ready_environment_r3(
    *, v2: Any, guards: Any, contract: dict[str, Any], environment: dict[str, Any], worker_path: Path
) -> tuple[Path, dict[str, Any]]:
    isolated_python = v2.validate_ready_environment(contract, environment, worker_path)
    bindings: dict[str, Any] = {}
    for package in ("torch", "torchaudio"):
        installed = v2.verify_record_file(package, environment["distributions"][package])
        wheel = guards.attest_wheel_archive(
            project_root=PROJECT_ROOT,
            wheel_root_rel=v2.WHEEL_EVIDENCE_ROOT_REL,
            package=package,
            row=environment["distributions"][package],
        )
        bindings[package] = guards.bind_wheel_to_installed_distribution(
            project_root=PROJECT_ROOT,
            isolated_venv_rel=v2.ISOLATED_VENV_REL,
            package=package,
            row=environment["distributions"][package],
            installed_evidence=installed,
            wheel_evidence=wheel,
        )
    return isolated_python, bindings


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
    raise R3LauncherError("no bounded append-only R3 attempt slot remains")


def restricted_child_environment(v2: Any, isolated_python: Path) -> dict[str, str]:
    env = v2.restricted_child_environment(isolated_python=isolated_python)
    # Preserve the R2 restricted/offline boundary but isolate R3 temporary state.
    cache_root = PROJECT_ROOT / "RecoverySprint/runtime_cache/qwen3_tts_voice_forge_v3"
    temp = cache_root / "temp"
    hf = cache_root / "huggingface"
    torch_cache = cache_root / "torch"
    for path in (temp, hf, torch_cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update({
        "TEMP": str(temp), "TMP": str(temp), "HF_HOME": str(hf),
        "TORCH_HOME": str(torch_cache), "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
    })
    return env


def preserve_failure(attempt: Path, exc: BaseException, stage: str, started: bool) -> None:
    evidence = {
        "schema": "qwen3_tts_voice_forge_parent_failure_v3",
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
    name = "parent_started_or_post_failure_v3.json" if started else "parent_preflight_failure_v3.json"
    try:
        write_new_json(attempt / name, evidence)
    except BaseException:
        pass


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.execute:
        raise R3LauncherError("R3 launcher is inert without --execute")
    if not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise R3LauncherError("both bounded execution acknowledgements are required")
    if not args.bundle_id or not SAFE_ID.fullmatch(args.bundle_id):
        raise R3LauncherError("one safe opaque --bundle-id is required")
    attempt = reserve_attempt(args.bundle_id)
    stage = "R3_HARNESS_MANIFEST"
    worker_started = False
    try:
        _manifest, indexed = verify_r3_harness()
        guards = load_sealed_module(
            R3_GUARDS_REL,
            indexed[R3_GUARDS_REL.as_posix()],
            "qwen3_tts_voice_forge_r3_guards_parent_sealed",
        )
        v2 = load_sealed_module(
            R2_RUNNER_REL,
            indexed[R2_RUNNER_REL.as_posix()],
            "qwen3_tts_voice_forge_runner_v2_sealed_for_r3",
        )
        install_runner_guards(v2, guards)
        contract = read_json(PROJECT_ROOT / R2_CONTRACT_REL)
        environment = read_json(PROJECT_ROOT / R2_ENVIRONMENT_REL)
        worker_path = (PROJECT_ROOT / R3_WORKER_REL).resolve()
        stage = "TRUSTED_BUNDLE_ENVELOPE"
        bundle, entry, _bundle_dir = v2.verify_bundle_envelope(args.bundle_id)
        stage = "R3_ISOLATED_ENVIRONMENT"
        isolated_python, exact_bindings = validate_ready_environment_r3(
            v2=v2, guards=guards, contract=contract,
            environment=environment, worker_path=worker_path,
        )
        stage = "SINGLE_USE_NONCE"
        ledger_path, ledger_hash = v2.consume_nonce(bundle, attempt)
        reservation = {
            "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
            "r3_schema": "qwen3_tts_voice_forge_parent_reservation_v3",
            "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
            "r3_status": "R3_FOUR_BLOCKER_PREFLIGHT_PASSED",
            "utc": utc_now(),
            "bundle_id": args.bundle_id,
            "candidate_id": bundle["candidate_id"],
            "opaque_voice_id": bundle["opaque_voice_id"],
            "queue_binding_sha256": bundle["queue_binding_sha256"],
            **v2.queue_binding_payload(bundle),
            "attempt": relative(attempt),
            "nonce_ledger_path": relative(ledger_path),
            "nonce_ledger_sha256": ledger_hash,
            # Legacy R2 core fields truthfully identify the sealed imported core.
            "verified_worker_path": R2_WORKER_REL.as_posix(),
            "verified_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
            # R3 fields separately bind the actual subprocess entry worker.
            "verified_entry_worker_path": R3_WORKER_REL.as_posix(),
            "verified_entry_worker_sha256": sha256_file(worker_path),
            "verified_frozen_core_worker_path": R2_WORKER_REL.as_posix(),
            "verified_frozen_core_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
            "harness_manifest_sha256": sha256_file(PROJECT_ROOT / R3_MANIFEST_REL),
            "contract_sha256": sha256_file(PROJECT_ROOT / R2_CONTRACT_REL),
            "environment_spec_sha256": sha256_file(PROJECT_ROOT / R2_ENVIRONMENT_REL),
            "trusted_registry_sha256": sha256_file(PROJECT_ROOT / R2_REGISTRY_REL),
            "bundle_seal_sha256": entry["bundle_seal_sha256"],
            "exact_wheel_to_installed_bindings": exact_bindings,
            "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
            "network_nonuse_proven": False,
        }
        write_new_json(attempt / "parent_reservation.json", reservation)
        command = [
            str(isolated_python), "-I", "-B", str(worker_path), "--execute",
            "--bundle-id", args.bundle_id, "--attempt-dir", str(attempt),
            "--acknowledge-private-unreviewed",
        ]
        stage = "R3_WORKER_PROCESS"
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
            raise R3LauncherError("verified R3 worker timed out") from exc
        elapsed = time.perf_counter() - started
        write_new(attempt / "worker_stdout_v3.log", completed.stdout)
        write_new(attempt / "worker_stderr_v3.log", completed.stderr)
        if completed.returncode != 0:
            raise R3LauncherError(f"verified R3 worker failed closed with return code {completed.returncode}")
        stage = "R3_PARENT_ARTIFACT_REOPEN"
        manifest_path = attempt / "worker_manifest_v3.json"
        profile_path = attempt / "voice_profile_candidate_v3.json"
        worker_manifest = read_json(manifest_path)
        profile = read_json(profile_path)
        parent_artifacts = guards.validate_parent_artifacts(
            attempt_dir=attempt, worker_manifest=worker_manifest, profile=profile
        )
        if profile.get("assignment_allowed") is not False or profile.get("owner_hearing_acceptance") != "PENDING":
            raise R3LauncherError("R3 profile overstated assignment/owner acceptance")
        summary = {
            "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v3",
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
            "parent_artifact_revalidation": parent_artifacts,
            "owner_hearing_acceptance": "PENDING",
            "independent_audit": "REQUIRED",
            "watermark_status": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
            "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
            "network_nonuse_proven": False,
            "activation_assignment_publication_or_upload_allowed": False,
            "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
        }
        # Reopen one last time immediately before append-only parent acceptance.
        guards.validate_parent_artifacts(
            attempt_dir=attempt, worker_manifest=worker_manifest, profile=profile
        )
        acceptance_path = attempt / "parent_acceptance_v3.json"
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
        print(f"R3 Qwen3-TTS parent failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
