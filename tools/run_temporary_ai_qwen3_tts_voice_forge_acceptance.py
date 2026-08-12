"""Launch one explicit, offline, append-only Qwen3-TTS forge acceptance.

With no ``--execute`` flag this program is inert. It never installs packages,
downloads models, plays audio, activates a person, or changes current voice
routing. A real run is permitted only from the separately accepted isolated
environment and uses the exact hash-bound worker, contract, job, and local
model manifests.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import qwen3_tts_original_voice_forge_worker as worker


class LauncherError(RuntimeError):
    """The explicit parent acceptance launcher failed closed."""


def next_append_only_attempt(candidate_root: Path) -> Path:
    for number in range(1, 1000):
        path = candidate_root / f"attempt_{number:02d}"
        if not path.exists():
            return path
    raise LauncherError("no append-only voice-forge attempt slot remains")


def restricted_child_environment(
    *, isolated_python: Path, cache_root: Path | None = None
) -> dict[str, str]:
    allowed = (
        "USERNAME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "SYSTEMROOT",
        "WINDIR",
    )
    env = {key: os.environ[key] for key in allowed if os.environ.get(key)}
    windows = Path(env.get("WINDIR") or env.get("SYSTEMROOT") or r"C:\Windows")
    env["PATH"] = os.pathsep.join(
        [str(isolated_python.parent), str(windows / "System32"), str(windows)]
    )
    cache_root = cache_root or (
        PROJECT_ROOT / "RecoverySprint" / "runtime_cache" / "qwen3_tts_voice_forge"
    )
    temp = cache_root / "temp"
    hf_cache = cache_root / "huggingface"
    torch_cache = cache_root / "torch"
    for path in (temp, hf_cache, torch_cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "TEMP": str(temp),
            "TMP": str(temp),
            "HF_HOME": str(hf_cache),
            "TORCH_HOME": str(torch_cache),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "CUDA_VISIBLE_DEVICES": "0",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_PROXY": "localhost,127.0.0.1,::1",
        }
    )
    return env


def verify_launcher_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = {
        "contract": args.contract,
        "contract_sha256": args.contract_sha256,
        "environment_spec": args.environment_spec,
        "environment_spec_sha256": args.environment_spec_sha256,
        "job": args.job,
        "job_sha256": args.job_sha256,
        "worker_sha256": args.worker_sha256,
    }
    missing = sorted(key for key, value in required.items() if not value)
    if missing:
        raise LauncherError("missing explicit launcher arguments: " + ", ".join(missing))
    contract_path = Path(args.contract).resolve()
    spec_path = Path(args.environment_spec).resolve()
    job_path = Path(args.job).resolve()
    worker_path = (PROJECT_ROOT / "tools" / "qwen3_tts_original_voice_forge_worker.py").resolve()
    worker.verify_exact_file(contract_path, args.contract_sha256, "acceptance contract")
    worker.verify_exact_file(spec_path, args.environment_spec_sha256, "environment spec")
    worker.verify_exact_file(job_path, args.job_sha256, "forge job")
    worker.verify_exact_file(worker_path, args.worker_sha256, "worker")
    contract = worker.read_json(contract_path)
    spec = worker.read_json(spec_path)
    job = worker.read_json(job_path)
    worker.validate_contract(contract)
    worker.validate_environment_spec(spec, require_ready=True)
    worker.validate_job_identity(job)
    expected_spec = worker.resolve_inside(
        PROJECT_ROOT, contract["paths"]["environment_spec"], "contract environment spec"
    )
    expected_worker = worker.resolve_inside(
        PROJECT_ROOT, contract["paths"]["worker"], "contract worker"
    )
    if spec_path != expected_spec or worker_path != expected_worker:
        raise LauncherError("launcher did not receive the contract's exact environment or worker")
    return contract, spec, job


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.execute:
        raise LauncherError("launcher is inert without --execute")
    if not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise LauncherError("both bounded execution acknowledgements are required")
    contract, _spec, job = verify_launcher_inputs(args)
    paths = contract["paths"]
    isolated_python = worker.resolve_inside(
        PROJECT_ROOT, paths["isolated_python"], "isolated Python"
    )
    if not isolated_python.is_file():
        raise LauncherError("the exact isolated Qwen3-TTS Python does not exist")
    forbidden = [
        worker.resolve_inside(PROJECT_ROOT, value, "forbidden environment")
        for value in contract.get("forbidden_environment_roots", [])
    ]
    for root in forbidden:
        try:
            isolated_python.relative_to(root)
        except ValueError:
            continue
        raise LauncherError("isolated Python points into a sealed Chatterbox environment")

    private_root = worker.resolve_inside(
        PROJECT_ROOT, paths["private_output_root"], "private output root"
    )
    candidate_root = private_root / str(job["candidate_id"])
    output_dir = next_append_only_attempt(candidate_root)
    worker_path = worker.resolve_inside(PROJECT_ROOT, paths["worker"], "worker")
    command = [
        str(isolated_python),
        "-I",
        "-B",
        str(worker_path),
        "--execute",
        "--contract",
        str(Path(args.contract).resolve()),
        "--contract-sha256",
        args.contract_sha256,
        "--environment-spec",
        str(Path(args.environment_spec).resolve()),
        "--environment-spec-sha256",
        args.environment_spec_sha256,
        "--job",
        str(Path(args.job).resolve()),
        "--job-sha256",
        args.job_sha256,
        "--worker-sha256",
        args.worker_sha256,
        "--output-dir",
        str(output_dir),
        "--acknowledge-private-unreviewed",
        "--acknowledge-no-download",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=restricted_child_environment(isolated_python=isolated_python),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        if output_dir.is_dir():
            worker.write_new_json(
                output_dir / "parent_timeout.json",
                {
                    "schema": "qwen3_tts_original_voice_forge_parent_failure_v1",
                    "status": worker.FAILURE_STATUS,
                    "reason": "WORKER_TIMEOUT",
                    "timeout_seconds": 1800,
                    "generic_sapi_or_other_person_voice_used": False,
                },
            )
        raise LauncherError("worker timed out and was terminated by subprocess.run") from exc
    elapsed = time.perf_counter() - started
    if output_dir.is_dir():
        worker.write_new_bytes(output_dir / "worker_stdout.log", completed.stdout)
        worker.write_new_bytes(output_dir / "worker_stderr.log", completed.stderr)
    if completed.returncode != 0:
        if output_dir.is_dir():
            worker.write_new_json(
                output_dir / "parent_failure.json",
                {
                    "schema": "qwen3_tts_original_voice_forge_parent_failure_v1",
                    "status": worker.FAILURE_STATUS,
                    "worker_returncode": completed.returncode,
                    "worker_process_seconds": elapsed,
                    "clean_worker_exit": False,
                    "generic_sapi_or_other_person_voice_used": False,
                },
            )
        raise LauncherError(f"worker failed closed with return code {completed.returncode}")

    manifest_path = output_dir / "worker_manifest.json"
    profile_path = output_dir / "voice_profile_candidate.json"
    manifest = worker.read_json(manifest_path)
    profile = worker.read_json(profile_path)
    if manifest.get("status") != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING":
        raise LauncherError("worker manifest did not pass the bounded engineering gates")
    if profile.get("assignment_allowed") is not False or profile.get("owner_hearing_acceptance") != "PENDING":
        raise LauncherError("worker profile overstated assignment or owner acceptance")
    reference = worker.validate_readable_non_silent_wav(
        output_dir / manifest["artifacts"]["original_design_reference"]["path"]
    )
    clone_test = worker.validate_readable_non_silent_wav(
        output_dir / manifest["artifacts"]["runtime_clone_test"]["path"]
    )
    summary = {
        "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v1",
        "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING",
        "candidate_id": job["candidate_id"],
        "opaque_voice_id": job["opaque_voice_id"],
        "append_only_private_output": worker.project_relative(output_dir, PROJECT_ROOT),
        "worker_returncode": completed.returncode,
        "worker_process_seconds": elapsed,
        "clean_worker_exit": True,
        "worker_manifest_sha256": worker.sha256_file(manifest_path),
        "voice_profile_candidate_sha256": worker.sha256_file(profile_path),
        "reference_wav_sha256": reference["sha256"],
        "runtime_clone_test_wav_sha256": clone_test["sha256"],
        "actual_cuda_allocation_measured": (
            manifest["telemetry"]["peak_cuda_allocated_bytes"]
            > manifest["telemetry"]["baseline_cuda_allocated_bytes"]
        ),
        "final_vram_return_recorded": True,
        "owner_hearing_acceptance": "PENDING",
        "activation_assignment_publication_or_upload_allowed": False,
        "fallback": "TEXT_PLUS_SILENCE_ONLY_ON_ANY_FAILURE",
    }
    summary_path = output_dir / "parent_acceptance.json"
    worker.write_new_json(summary_path, summary)
    return {
        **summary,
        "parent_acceptance_sha256": worker.sha256_file(summary_path),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--contract")
    parser.add_argument("--contract-sha256")
    parser.add_argument("--environment-spec")
    parser.add_argument("--environment-spec-sha256")
    parser.add_argument("--job")
    parser.add_argument("--job-sha256")
    parser.add_argument("--worker-sha256")
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
    except (LauncherError, worker.ForgeError) as exc:
        print(f"Qwen3-TTS forge launcher failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
