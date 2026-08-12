#!/usr/bin/env python3
"""Bounded, append-only Attempt 07 import A/B probe.

The ordinary invocation is descriptive and does not start the Blackwell
runtime.  The explicitly gated run starts two fresh Python 3.11.9 children
with the candidate's exact restricted environment.  The environments differ
only by ``OPENBLAS_NUM_THREADS``: absent in the control and ``1`` in the
treatment.  Each child starts two quiescent support threads before importing
Torch, matching the important multithreaded boundary exposed by Attempt 06.

No arm loads Chatterbox, calls CUDA, generates audio, plays audio, changes
packages, modifies routing, or promotes the inactive candidate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import faulthandler
import hashlib
import hmac
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
CONFIG_PATH = CANDIDATE_ROOT / "candidate_config.json"
ATTEMPT06_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "attempt_06"
)
PROBE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_attempt07_openblas_import_ab_probe"
)
ATTEMPT06_HASHES = {
    "PERSISTENT_BLACKWELL_ACCEPTANCE.json": (
        "49daa08ae6dabe2ad46757737fd01bd8247dc9531b2621e1e7ff017f604d1ab1"
    ),
    "WORKER_PHASE_EVENTS.jsonl": (
        "e4fd32125cad5518ef0e7267d1a5298a1de8ad38cd10a826700b42905f0af31e"
    ),
    "WORKER_STDERR_FAULTHANDLER.log": (
        "de050999589fb6f5bff1a75b27cfb15cf96a3cb920cc1f3a6edf0b97bcd59c75"
    ),
}
NUMPY_CONFIG = (
    ROOT
    / "Voice"
    / "sidecars"
    / "chatterbox_blackwell_gpu"
    / ".venv"
    / "Lib"
    / "site-packages"
    / "numpy"
    / "__config__.py"
)
OPENBLAS_DLL = (
    ROOT
    / "Voice"
    / "sidecars"
    / "chatterbox_blackwell_gpu"
    / ".venv"
    / "Lib"
    / "site-packages"
    / "numpy.libs"
    / "libopenblas64__v0.3.23-293-gc2f4bdbb-gcc_10_3_0-2bde3a66a51006b2b53eb373ff767a3f.dll"
)
CONTROL = "control_prior_restricted_environment"
TREATMENT = "treatment_openblas_num_threads_1"
ENV_KEY = "OPENBLAS_NUM_THREADS"
ENV_VALUE = "1"
DEFAULT_ARM_TIMEOUT_SECONDS = 180.0


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(encoded).hexdigest()


def write_bytes_exclusive(path: Path, payload: bytes) -> str:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(payload).hexdigest()


def allocate_attempt_directory() -> Path:
    PROBE_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        path = PROBE_ROOT / f"attempt_{number:02d}"
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path
    raise RuntimeError("no append-only Attempt 07 A/B probe directory is available")


def attempt06_integrity() -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name, expected in ATTEMPT06_HASHES.items():
        path = ATTEMPT06_ROOT / name
        actual = sha256_file(path) if path.is_file() else None
        files[name] = {
            "path": relative(path),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches": actual == expected,
            "bytes": path.stat().st_size if path.is_file() else None,
        }
    return {"passed": all(item["matches"] for item in files.values()), "files": files}


def numpy_openblas_static_evidence() -> dict[str, Any]:
    config_text = NUMPY_CONFIG.read_text(encoding="utf-8")
    evidence = {
        "numpy_version": "1.26.4",
        "numpy_config_path": relative(NUMPY_CONFIG),
        "numpy_config_sha256": sha256_file(NUMPY_CONFIG),
        "openblas_dll_path": relative(OPENBLAS_DLL),
        "openblas_dll_sha256": sha256_file(OPENBLAS_DLL),
        "openblas_dll_bytes": OPENBLAS_DLL.stat().st_size,
        "build_name_openblas64_present": '"name": "openblas64"' in config_text,
        "build_version_0_3_23_dev_present": '"version": "0.3.23.dev"' in config_text,
        "build_max_threads_2_present": "MAX_THREADS=2" in config_text,
        "build_use_openmp_field": "USE_OPENMP=" in config_text,
        "threading_backend_not_proven_from_static_config": True,
        "packages_changed": False,
    }
    evidence["passed"] = all(
        evidence[key]
        for key in (
            "build_name_openblas64_present",
            "build_version_0_3_23_dev_present",
            "build_max_threads_2_present",
            "build_use_openmp_field",
        )
    )
    return evidence


def restricted_environment_pair(
    treatment_environment: dict[str, str],
) -> dict[str, dict[str, str]]:
    if treatment_environment.get(ENV_KEY) != ENV_VALUE:
        raise ValueError("treatment environment is missing the exact OpenBLAS thread limit")
    treatment = dict(treatment_environment)
    control = dict(treatment_environment)
    control.pop(ENV_KEY, None)
    differing = sorted(
        key
        for key in set(control) | set(treatment)
        if control.get(key) != treatment.get(key)
    )
    if differing != [ENV_KEY]:
        raise ValueError(f"A/B environments differ unexpectedly: {differing}")
    return {CONTROL: control, TREATMENT: treatment}


def environment_evidence(pair: dict[str, dict[str, str]]) -> dict[str, Any]:
    control = pair[CONTROL]
    treatment = pair[TREATMENT]
    differing = sorted(
        key
        for key in set(control) | set(treatment)
        if control.get(key) != treatment.get(key)
    )
    nonce_key = "KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE"
    return {
        "exact_only_difference": differing == [ENV_KEY],
        "differing_keys": differing,
        "control_openblas_num_threads": control.get(ENV_KEY),
        "treatment_openblas_num_threads": treatment.get(ENV_KEY),
        "control_keys": sorted(control),
        "treatment_keys": sorted(treatment),
        "shared_session_nonce_sha256": sha256_text(treatment[nonce_key]),
        "session_nonce_equal": control.get(nonce_key) == treatment.get(nonce_key),
        "control_model_load_opt_in": control.get("KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD"),
        "treatment_model_load_opt_in": treatment.get("KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD"),
        "offline_equal": all(
            control.get(key) == treatment.get(key) == "1"
            for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
        ),
        "cuda_visible_devices_equal": (
            control.get("CUDA_VISIBLE_DEVICES")
            == treatment.get("CUDA_VISIBLE_DEVICES")
            == "0"
        ),
    }


def blender_process_evidence() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$p=@(Get-Process -Name blender -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty Id); "
                "[Console]::Out.Write(($p | ConvertTo-Json -Compress))"
            ),
        ],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return {
            "query_succeeded": False,
            "active": None,
            "stderr": completed.stderr[-1000:],
            "process_state_changed": False,
        }
    raw = completed.stdout.strip()
    parsed = json.loads(raw) if raw else []
    pids = parsed if isinstance(parsed, list) else [parsed]
    pids = [int(value) for value in pids if value is not None]
    return {
        "query_succeeded": True,
        "active": bool(pids),
        "pids": pids,
        "process_state_changed": False,
    }


def _quiescent_support_thread(stop: threading.Event) -> None:
    stop.wait()


def child_import_probe() -> int:
    """Import Torch after support threads exist; never call CUDA or a model."""

    result: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "blackwell_openblas_import_ab_probe_child",
        "started_at": utc_now(),
        "openblas_num_threads": os.environ.get(ENV_KEY),
        "candidate_opt_in": os.environ.get("KIRA_PERSISTENT_BLACKWELL_CANDIDATE"),
        "model_load_opt_in_present": bool(
            os.environ.get("KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD")
        ),
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "packages_changed": False,
        "support_threads_started_before_import": 2,
        "passed": False,
    }
    stop = threading.Event()
    threads = [
        threading.Thread(
            target=_quiescent_support_thread,
            args=(stop,),
            name=f"attempt07-import-shape-{index}",
            daemon=True,
        )
        for index in range(2)
    ]
    for thread in threads:
        thread.start()
    faulthandler.enable(file=sys.stderr, all_threads=True)
    faulthandler.dump_traceback_later(30.0, repeat=True, file=sys.stderr, exit=False)
    started = time.perf_counter()
    try:
        if result["candidate_opt_in"] != "1":
            raise RuntimeError("restricted candidate opt-in is absent")
        if result["model_load_opt_in_present"]:
            raise RuntimeError("import probe must not receive model-load opt-in")
        if os.environ.get("HF_HUB_OFFLINE") != "1":
            raise RuntimeError("import probe is not offline")
        torch = importlib.import_module("torch")
        numpy = importlib.import_module("numpy")
        result.update(
            {
                "torch_version": str(torch.__version__),
                "numpy_version": str(numpy.__version__),
                "torch_imported": True,
                "numpy_imported": True,
                "import_elapsed_seconds": round(time.perf_counter() - started, 6),
                "passed": True,
            }
        )
        return_code = 0
    except Exception as exc:
        result.update(
            {
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "import_elapsed_seconds": round(time.perf_counter() - started, 6),
            }
        )
        return_code = 2
    finally:
        faulthandler.cancel_dump_traceback_later()
        stop.set()
        for thread in threads:
            thread.join(timeout=2)
        result["finished_at"] = utc_now()
        print(json.dumps(result, sort_keys=True), flush=True)
    return return_code


def run_arm(
    *,
    command: list[str],
    environment: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    started_at = utc_now()
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    timed_out = False
    forced_termination = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            forced_termination = True
            process.kill()
            stdout, stderr = process.communicate(timeout=10)
    parsed: dict[str, Any] | None = None
    if stdout.strip():
        try:
            candidate = json.loads(stdout.decode("utf-8").splitlines()[-1])
            if isinstance(candidate, dict):
                parsed = candidate
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
    return {
        "started_at": started_at,
        "finished_at": utc_now(),
        "wall_seconds": round(time.perf_counter() - started, 6),
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "owned_pid": process.pid,
        "owned_process_exit_code": process.returncode,
        "owned_process_forced_termination": forced_termination,
        "stdout": stdout,
        "stderr": stderr,
        "result": parsed,
    }


def hypothesis_assessment(
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    treatment_result = treatment.get("result") or {}
    treatment_passed = (
        treatment.get("timed_out") is False
        and treatment.get("owned_process_exit_code") == 0
        and treatment_result.get("passed") is True
        and treatment_result.get("torch_version") == "2.11.0+cu130"
        and treatment_result.get("numpy_version") == "1.26.4"
        and treatment_result.get("openblas_num_threads") == "1"
    )
    control_result = control.get("result") or {}
    control_elapsed = float(
        control_result.get("import_elapsed_seconds") or control.get("wall_seconds") or 0.0
    )
    treatment_elapsed = float(
        treatment_result.get("import_elapsed_seconds") or treatment.get("wall_seconds") or 0.0
    )
    strong_difference = (
        control.get("timed_out") is True
        or (
            control_result.get("passed") is True
            and control_elapsed >= max(5.0, treatment_elapsed * 3.0)
        )
    )
    supported = bool(treatment_passed and strong_difference)
    return {
        "treatment_passed": treatment_passed,
        "control_timed_out": control.get("timed_out") is True,
        "control_elapsed_seconds": control_elapsed,
        "treatment_elapsed_seconds": treatment_elapsed,
        "strong_bounded_difference": strong_difference,
        "openblas_single_thread_hypothesis_supported": supported,
        "root_cause_proven": False,
        "ready_for_separate_full_attempt07_acceptance": supported,
        "status": (
            "BOUNDED_AB_SUPPORTS_ATTEMPT07_ACCEPTANCE"
            if supported
            else "BOUNDED_AB_DOES_NOT_SUPPORT_ATTEMPT07_ACCEPTANCE"
        ),
    }


def run_ab_probe(
    *,
    expected_candidate_config_sha256: str,
    timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    expected = str(expected_candidate_config_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("exact expected candidate-config SHA-256 is required")
    actual = sha256_file(CONFIG_PATH)
    if not hmac.compare_digest(actual, expected):
        raise ValueError("candidate config does not match the operator-bound SHA-256")
    preserved = attempt06_integrity()
    if preserved["passed"] is not True:
        raise RuntimeError("Attempt 06 evidence changed; refusing A/B probe")
    openblas = numpy_openblas_static_evidence()
    if openblas["passed"] is not True:
        raise RuntimeError("installed NumPy/OpenBLAS static evidence is incomplete")
    blender = blender_process_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")

    if str(CANDIDATE_ROOT) not in sys.path:
        sys.path.insert(0, str(CANDIDATE_ROOT))
    import candidate_client
    import candidate_contract

    config = candidate_contract.load_candidate_config(CONFIG_PATH)
    candidate_contract.verify_candidate_config(config)
    nonce = "attempt07-ab-" + os.urandom(32).hex()
    treatment_environment = candidate_client.restricted_candidate_environment(
        config,
        session_nonce=nonce,
        allow_gpu_model_load=False,
    )
    pair = restricted_environment_pair(treatment_environment)
    environments = environment_evidence(pair)
    if environments["exact_only_difference"] is not True:
        raise RuntimeError("A/B environment equality was not proven")

    attempt = allocate_attempt_directory()
    command = [str(candidate_contract.project_file(config["python"])), str(Path(__file__).resolve()), "--child-import-probe"]
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_attempt07_openblas_import_ab_probe",
        "started_at": utc_now(),
        "candidate_status": config["candidate_status"],
        "candidate_config_sha256": actual,
        "operator_expected_candidate_config_sha256": expected,
        "probe_tool_sha256": sha256_file(Path(__file__).resolve()),
        "attempt06_integrity": preserved,
        "numpy_openblas_static_evidence": openblas,
        "blender_before": blender,
        "environment_ab": environments,
        "identical_child_command": command,
        "arm_timeout_seconds": timeout_seconds,
        "gpu_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "packages_changed": False,
        "routing_changed": False,
        "candidate_promoted": False,
        "arms": {},
    }
    report_path = attempt / "ATTEMPT07_OPENBLAS_IMPORT_AB_REPORT.json"
    marker_path = attempt / "ATTEMPT_STARTED.json"
    report["attempt_started_marker"] = {
        "path": relative(marker_path),
        "sha256": write_json_exclusive(
            marker_path,
            {
                "schema_version": 1,
                "artifact_kind": "persistent_blackwell_attempt07_openblas_ab_started",
                "started_at": report["started_at"],
                "candidate_config_sha256": actual,
                "probe_tool_sha256": report["probe_tool_sha256"],
                "candidate_status": config["candidate_status"],
                "model_load_opt_in": False,
                "gpu_api_invoked": False,
                "audio_generated": False,
            },
        ),
    }
    try:
        for label in (CONTROL, TREATMENT):
            arm = run_arm(
                command=command,
                environment=pair[label],
                timeout_seconds=timeout_seconds,
            )
            stdout_path = attempt / f"{label}_STDOUT.jsonl"
            stderr_path = attempt / f"{label}_STDERR_FAULTHANDLER.log"
            stdout_hash = write_bytes_exclusive(stdout_path, arm.pop("stdout"))
            stderr_hash = write_bytes_exclusive(stderr_path, arm.pop("stderr"))
            arm["stdout_path"] = relative(stdout_path)
            arm["stdout_sha256"] = stdout_hash
            arm["stderr_path"] = relative(stderr_path)
            arm["stderr_sha256"] = stderr_hash
            report["arms"][label] = arm
        report["assessment"] = hypothesis_assessment(
            report["arms"][CONTROL], report["arms"][TREATMENT]
        )
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        report["assessment"] = {
            "status": "BOUNDED_AB_FAILED_PRESERVED",
            "openblas_single_thread_hypothesis_supported": False,
            "root_cause_proven": False,
            "ready_for_separate_full_attempt07_acceptance": False,
        }
    finally:
        report["finished_at"] = utc_now()
        report["passed"] = bool(
            report.get("assessment", {}).get(
                "openblas_single_thread_hypothesis_supported"
            )
        )
        write_json_exclusive(report_path, report)
    return report_path, report


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_attempt07_openblas_import_ab_probe_description",
        "status": "PREPARED_NOT_EXECUTED",
        "current_candidate_config_sha256": sha256_file(CONFIG_PATH),
        "control": f"exact restricted environment with {ENV_KEY} absent",
        "treatment": f"same environment with {ENV_KEY}={ENV_VALUE}",
        "only_environment_difference_required": ENV_KEY,
        "default_arm_timeout_seconds": DEFAULT_ARM_TIMEOUT_SECONDS,
        "imports": ["torch", "numpy"],
        "support_threads_started_before_import": 2,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "packages_changed": False,
        "root_cause_claimed": False,
        "required_flags": [
            "--run-ab-probe",
            "--confirm-no-active-blender",
            "--expected-candidate-config-sha256 <CURRENT_EXACT_SHA256>",
        ],
        "do_not_run_while_body_or_blender_work_is_active": True,
    }


def static_self_check() -> dict[str, Any]:
    preserved = attempt06_integrity()
    openblas = numpy_openblas_static_evidence()
    source = Path(__file__).read_text(encoding="utf-8")
    child_source = inspect.getsource(child_import_probe)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    checks = {
        "attempt06_preserved": preserved["passed"] is True,
        "openblas_static_binding": openblas["passed"] is True,
        "candidate_policy_exact": config.get("native_thread_limits") == {ENV_KEY: ENV_VALUE},
        "no_top_level_torch_import": "\nimport torch\n" not in source,
        "no_chatterbox_runtime_import": (
            'importlib.import_module("chatterbox' not in child_source
            and "from chatterbox" not in child_source
        ),
        "no_audio_playback_call": not any(
            marker in child_source
            for marker in ("winsound.PlaySound(", "sounddevice.play(", "sd.play(")
        ),
        "no_package_install_call": not any(
            marker in child_source
            for marker in ("pip.main(", 'subprocess.run(["pip"', 'subprocess.Popen(["pip"')
        ),
        "probe_root_absent_or_directory": not PROBE_ROOT.exists() or PROBE_ROOT.is_dir(),
    }
    return {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_attempt07_openblas_import_ab_static_self_check",
        "checks": checks,
        "passed": all(checks.values()),
        "blackwell_runtime_started": False,
        "gpu_used": False,
        "model_loaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--static-self-check", action="store_true")
    parser.add_argument("--run-ab-probe", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    parser.add_argument("--arm-timeout-seconds", type=float, default=DEFAULT_ARM_TIMEOUT_SECONDS)
    parser.add_argument("--child-import-probe", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.child_import_probe:
        return child_import_probe()
    if args.static_self_check:
        result = static_self_check()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    if not args.run_ab_probe:
        print(json.dumps(describe(), indent=2, sort_keys=True))
        return 0
    if not args.confirm_no_active_blender:
        raise SystemExit("--confirm-no-active-blender is required")
    timeout = max(30.0, min(300.0, float(args.arm_timeout_seconds)))
    report_path, report = run_ab_probe(
        expected_candidate_config_sha256=args.expected_candidate_config_sha256,
        timeout_seconds=timeout,
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "passed": report["passed"],
                "assessment": report.get("assessment"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
