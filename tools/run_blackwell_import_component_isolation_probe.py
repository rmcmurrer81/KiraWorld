#!/usr/bin/env python3
"""Prepare or run one bounded Blackwell Torch-import component-isolation arm.

The normal invocation is inert.  A live invocation is separately hash-bound,
append-only, limited to one named arm, and capped at 180 seconds.  Every arm
stops after importing Torch and observing the transitively loaded NumPy module.
No arm calls a Torch CUDA API, imports Torchaudio or Chatterbox, loads a model,
generates or plays audio, invokes Ollama or Kira, changes Defender, starts
Blender, changes production routing, or promotes the inactive candidate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import faulthandler
import hashlib
import hmac
import importlib
import json
import os
import queue
import secrets
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
WORKER_PATH = CANDIDATE_ROOT / "persistent_worker.py"
OUTPUT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_component_isolation"
)
FAILED_ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_protocol_control_pending_defender_state"
    / "attempt_01"
)
PREDECESSOR_WRAPPER_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state.py"
)
STRICT_CONTROL_PATH = ROOT / "tools" / "run_persistent_blackwell_protocol_import_only_control.py"
DIAGNOSTIC_OPT_IN = "KIRA_BLACKWELL_IMPORT_COMPONENT_ISOLATION"
DEFAULT_ARM_TIMEOUT_SECONDS = 180.0
MAX_ARM_TIMEOUT_SECONDS = 180.0
EXPECTED_CANDIDATE_HASHES = {
    "candidate_client": "b57e1a57625f8d3c55881795611b440aaf91aeb7466ee2f1231ee7bedbc3e9f1",
    "candidate_contract": "e74ce6ad83b181d5f8ca786764d5e61e2cc5e053aaebf29065063151aed38cbc",
    "candidate_config": "8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57",
    "candidate_worker": "bbf33447e7b742a3f2c79da6f7a3527b37a069e32bb888ed3d1e833345388085",
}
FAILED_EVIDENCE_HASHES = {
    "ATTEMPT_STARTED.json": "8a88c06ac31578600113de1a0a0d46ef3f9671846870db21f4a13fcfe8df1d06",
    "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json": (
        "9bf47ced167c1d6733277516207426d1f5a4dc699caa900cbfd4228730349884"
    ),
    "WORKER_PHASE_EVENTS.jsonl": "812a007bfecfb6296d3ea75f59f9bf78efb73737d46acc124fb8b10736c28dc0",
    "WORKER_STDERR_FAULTHANDLER.log": "2ae85fd00688dce004c68b62d438d75aa37e8085b796a9b34b96b42d6f45baed",
    "POST_FAILURE_PROCESS_CHECK.json": "c87cc5a66a05c274dec280505c3f474459b1cf64df2672cd0958661f06bada7a",
}
PREDECESSOR_WRAPPER_SHA256 = "cf72d1d5dcb5060b1f7fdf88deefa3d97d72351c459fca0f80736d60da9c4cd9"
STRICT_CONTROL_SHA256 = "7fd8e006ba58aede2f34b4289c4fc857a1bc6ae76d6a6a4fcc36a7f3a0466f21"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_dependency_hash(path: Path, expected: str, label: str) -> None:
    if not hmac.compare_digest(sha256_file(path), expected):
        raise RuntimeError(f"{label} changed before dependency import")


_require_dependency_hash(
    CANDIDATE_ROOT / "candidate_client.py",
    EXPECTED_CANDIDATE_HASHES["candidate_client"],
    "candidate client",
)
_require_dependency_hash(
    CANDIDATE_ROOT / "candidate_contract.py",
    EXPECTED_CANDIDATE_HASHES["candidate_contract"],
    "candidate contract",
)
if str(CANDIDATE_ROOT) not in sys.path:
    sys.path.insert(0, str(CANDIDATE_ROOT))
import candidate_client  # noqa: E402
import candidate_contract  # noqa: E402


ARM_SPECS: dict[str, dict[str, Any]] = {
    "minimal_direct": {
        "worker_module_context": False,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": False,
        "parent_pipe_drains_and_phase_fsync": False,
        "comparison": "standalone restricted-environment baseline",
    },
    "worker_context_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": False,
        "parent_pipe_drains_and_phase_fsync": False,
        "comparison": "minimal_direct isolates persistent_worker module-loading context",
    },
    "nvidia_boundary_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": True,
        "resource_sampler": "none",
        "stdin_reader": False,
        "parent_pipe_drains_and_phase_fsync": False,
        "comparison": "worker_context_only isolates one real nvidia-smi boundary query",
    },
    "resource_sampler_host_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "real_class_external_gpu_stubbed",
        "stdin_reader": False,
        "parent_pipe_drains_and_phase_fsync": False,
        "comparison": "worker_context_only isolates real ResourceSampler host sampling activity",
    },
    "stdin_reader_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": True,
        "parent_pipe_drains_and_phase_fsync": False,
        "comparison": "worker_context_only isolates the real blocked stdin-reader thread",
    },
    "pipe_drains_fsync_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": False,
        "parent_pipe_drains_and_phase_fsync": True,
        "comparison": "worker_context_only isolates live parent drains plus phase-journal fsync",
    },
    "combined_real_shape": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": True,
        "resource_sampler": "real_class_full_boundary_gpu_and_host",
        "stdin_reader": True,
        "parent_pipe_drains_and_phase_fsync": True,
        "comparison": "interaction/reproduction arm after individual components",
    },
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(encoded).hexdigest()


def exact_candidate_hashes() -> dict[str, str]:
    return {
        "candidate_client": sha256_file(CANDIDATE_ROOT / "candidate_client.py"),
        "candidate_contract": sha256_file(CANDIDATE_ROOT / "candidate_contract.py"),
        "candidate_config": sha256_file(CONFIG_PATH),
        "candidate_worker": sha256_file(WORKER_PATH),
    }


def validate_failed_evidence() -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name, expected in FAILED_EVIDENCE_HASHES.items():
        path = FAILED_ATTEMPT_ROOT / name
        actual = sha256_file(path)
        if not hmac.compare_digest(actual, expected):
            raise RuntimeError(f"preserved failed evidence changed: {name}")
        files[name] = {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    report = json.loads(
        (FAILED_ATTEMPT_ROOT / "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json").read_text(
            encoding="utf-8"
        )
    )
    post = json.loads(
        (FAILED_ATTEMPT_ROOT / "POST_FAILURE_PROCESS_CHECK.json").read_text(encoding="utf-8")
    )
    if report.get("status") != "failed_preserved" or report.get("passed") is not False:
        raise RuntimeError("failed report truth changed")
    if post.get("report_sha256") != FAILED_EVIDENCE_HASHES[
        "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json"
    ]:
        raise RuntimeError("post-failure process check report binding changed")
    return {
        "files": files,
        "report_status": "failed_preserved",
        "torch_phase_elapsed_seconds": 1100.9460583,
        "client_timeout_seconds": 1100.0,
        "independent_defender_state": "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        "post_failure_owned_child_observed": post.get("owned_voice_child_observed_after_failure"),
        "failed_attempt_changed": False,
    }


def no_active_blender_evidence() -> dict[str, Any]:
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "$p=@(Get-Process -Name blender -ErrorAction SilentlyContinue | "
            "Select-Object Id,Path,StartTime); "
            "[pscustomobject]@{count=$p.Count;processes=$p} | "
            "ConvertTo-Json -Depth 4 -Compress"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return {
            "query_succeeded": False,
            "active": None,
            "error": completed.stderr[-2000:],
            "query_kind": "Get-Process_not_CIM_or_WMI",
        }
    payload = json.loads(completed.stdout or "{}")
    count = int(payload.get("count") or 0)
    return {
        "query_succeeded": True,
        "active": count > 0,
        "count": count,
        "processes": payload.get("processes") or [],
        "query_kind": "Get-Process_not_CIM_or_WMI",
        "processes_terminated": False,
    }


def allocate_attempt_directory() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        path = OUTPUT_ROOT / f"attempt_{number:02d}"
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path
    raise RuntimeError("no append-only component-isolation attempt is available")


def _emit_phase_start(arm: str) -> None:
    print(
        json.dumps(
            {
                "schema_version": 1,
                "message_type": "event",
                "event": "component_isolation_import_started",
                "arm": arm,
                "phase": "imports.torch",
                "cuda_api_invoked": False,
                "model_loaded": False,
                "audio_generated": False,
                "production_routing_changed": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def child_arm(arm: str, result_path_value: str) -> int:
    """Run exactly one selected import-only component arm."""

    if os.environ.get(DIAGNOSTIC_OPT_IN) != "1":
        raise RuntimeError("component-isolation child opt-in is absent")
    if arm not in ARM_SPECS:
        raise ValueError("unknown component-isolation arm")
    result_path = Path(result_path_value).resolve()
    result_path.parent.resolve().relative_to(OUTPUT_ROOT.resolve())
    if result_path.name != "CHILD_RESULT.json":
        raise ValueError("child result filename is not accepted")
    hashes = exact_candidate_hashes()
    if hashes != EXPECTED_CANDIDATE_HASHES:
        raise RuntimeError("restored candidate hashes changed")
    config = candidate_contract.load_candidate_config(CONFIG_PATH)
    candidate_contract.verify_candidate_config(config)
    cache_paths = candidate_contract.verify_restricted_environment(
        config,
        require_load_opt_in=True,
    )
    spec = ARM_SPECS[arm]
    result: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "blackwell_import_component_isolation_child",
        "arm": arm,
        "component_spec": spec,
        "started_at": utc_now(),
        "candidate_hashes": hashes,
        "cache_paths": cache_paths,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "torchaudio_imported": False,
        "chatterbox_imported": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
        "passed": False,
    }
    worker: Any | None = None
    sampler: Any | None = None
    stdin_thread: threading.Thread | None = None
    stdin_queue: queue.Queue[tuple[str, Any]] | None = None
    original_gpu_probe: Any | None = None
    stubbed_gpu_calls = 0
    faulthandler.enable(file=sys.stderr, all_threads=True)
    faulthandler.dump_traceback_later(30.0, repeat=True, file=sys.stderr, exit=False)
    return_code = 2
    try:
        if spec["worker_module_context"]:
            _require_dependency_hash(
                WORKER_PATH,
                EXPECTED_CANDIDATE_HASHES["candidate_worker"],
                "candidate worker",
            )
            worker = importlib.import_module("persistent_worker")
            result["worker_module_loaded_before_torch"] = True
        else:
            result["worker_module_loaded_before_torch"] = False

        if spec["stdin_reader"]:
            stdin_queue = queue.Queue(maxsize=2)
            stdin_thread = threading.Thread(
                target=worker._stdin_reader,
                args=(stdin_queue, int(config["bounds"]["max_line_bytes"])),
                name="component-isolation-real-stdin-reader",
                daemon=True,
            )
            stdin_thread.start()

        nvidia_timing: dict[str, Any] | None = None
        if spec["nvidia_smi_boundary_call"] and spec["resource_sampler"] == "none":
            nvidia_started = time.perf_counter_ns()
            nvidia_value = worker._gpu_memory_used_mib()
            nvidia_finished = time.perf_counter_ns()
            nvidia_timing = {
                "calls": 1,
                "value_mib": nvidia_value,
                "elapsed_seconds": round(
                    (nvidia_finished - nvidia_started) / 1_000_000_000,
                    9,
                ),
            }

        if spec["resource_sampler"] != "none":
            if spec["resource_sampler"] == "real_class_external_gpu_stubbed":
                original_gpu_probe = worker._gpu_memory_used_mib

                def no_external_gpu_process() -> None:
                    nonlocal stubbed_gpu_calls
                    stubbed_gpu_calls += 1
                    return None

                worker._gpu_memory_used_mib = no_external_gpu_process
            sampler = worker.ResourceSampler()
            sampler.start()

        if spec["parent_pipe_drains_and_phase_fsync"]:
            _emit_phase_start(arm)

        active_threads = [
            {
                "name": thread.name,
                "daemon": bool(thread.daemon),
                "alive": bool(thread.is_alive()),
            }
            for thread in threading.enumerate()
        ]
        import_started_ns = time.perf_counter_ns()
        torch = importlib.import_module("torch")
        import_finished_ns = time.perf_counter_ns()
        numpy_module = sys.modules.get("numpy")
        resources = sampler.stop() if sampler is not None else None
        sampler = None
        if original_gpu_probe is not None:
            worker._gpu_memory_used_mib = original_gpu_probe
            original_gpu_probe = None
        result.update(
            {
                "passed": (
                    str(torch.__version__) == "2.11.0+cu130"
                    and "torchaudio" not in sys.modules
                    and not any(
                        name == "chatterbox" or name.startswith("chatterbox.")
                        for name in sys.modules
                    )
                ),
                "torch_imported": True,
                "torch_version": str(torch.__version__),
                "numpy_loaded_transitively": numpy_module is not None,
                "numpy_version": (
                    str(getattr(numpy_module, "__version__", ""))
                    if numpy_module is not None
                    else None
                ),
                "import_elapsed_seconds": round(
                    (import_finished_ns - import_started_ns) / 1_000_000_000,
                    9,
                ),
                "active_threads_before_import": active_threads,
                "nvidia_smi_boundary": nvidia_timing,
                "resource_sampler": resources,
                "external_gpu_probe_stub_calls": stubbed_gpu_calls,
                "torchaudio_imported": "torchaudio" in sys.modules,
                "chatterbox_imported": any(
                    name == "chatterbox" or name.startswith("chatterbox.")
                    for name in sys.modules
                ),
            }
        )
        return_code = 0 if result["passed"] else 2
    except Exception as exc:
        result.update(
            {
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc()[-12000:],
            }
        )
    finally:
        if sampler is not None:
            try:
                result["resource_sampler_after_error"] = sampler.stop()
            except Exception as exc:
                result["resource_sampler_stop_error"] = f"{type(exc).__name__}: {exc}"
        if original_gpu_probe is not None and worker is not None:
            worker._gpu_memory_used_mib = original_gpu_probe
        faulthandler.cancel_dump_traceback_later()
        result["finished_at"] = utc_now()
        result["stdin_reader_started"] = stdin_thread is not None
        result["stdin_reader_alive_before_parent_eof"] = (
            bool(stdin_thread.is_alive()) if stdin_thread is not None else False
        )
        write_json_exclusive(result_path, result)
        if stdin_thread is not None:
            stdin_thread.join(timeout=10)
    return return_code


def _drain_stdout_with_phase_fsync(
    stream: Any,
    path: Path,
    metrics: dict[str, Any],
) -> None:
    lines = 0
    fsync_calls = 0
    with path.open("xb", buffering=0) as handle:
        while True:
            raw = stream.readline(1024 * 1024 + 2)
            if raw == b"":
                break
            handle.write(raw)
            os.fsync(handle.fileno())
            lines += 1
            fsync_calls += 1
    metrics.update({"stdout_lines": lines, "phase_journal_fsync_calls": fsync_calls})


def _drain_stderr(stream: Any, path: Path, metrics: dict[str, Any]) -> None:
    total = 0
    with path.open("xb", buffering=0) as handle:
        while True:
            raw = stream.read(4096)
            if not raw:
                break
            handle.write(raw)
            total += len(raw)
    metrics["stderr_bytes"] = total


def run_one_arm(
    *,
    arm: str,
    expected_tool_sha256: str,
    expected_config_sha256: str,
    expected_failed_report_sha256: str,
    expected_post_failure_check_sha256: str,
    timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    if arm not in ARM_SPECS:
        raise ValueError("unknown component-isolation arm")
    tool_hash = sha256_file(Path(__file__).resolve())
    if not hmac.compare_digest(tool_hash, expected_tool_sha256.casefold()):
        raise ValueError("operator-bound component-isolation tool hash mismatch")
    hashes = exact_candidate_hashes()
    if hashes != EXPECTED_CANDIDATE_HASHES:
        raise RuntimeError("restored candidate hashes changed")
    if not hmac.compare_digest(
        hashes["candidate_config"],
        expected_config_sha256.casefold(),
    ):
        raise ValueError("operator-bound candidate config hash mismatch")
    if not hmac.compare_digest(
        FAILED_EVIDENCE_HASHES["PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json"],
        expected_failed_report_sha256.casefold(),
    ):
        raise ValueError("operator did not bind the preserved failed report")
    if not hmac.compare_digest(
        FAILED_EVIDENCE_HASHES["POST_FAILURE_PROCESS_CHECK.json"],
        expected_post_failure_check_sha256.casefold(),
    ):
        raise ValueError("operator did not bind the post-failure process check")
    failed_evidence = validate_failed_evidence()
    if sha256_file(PREDECESSOR_WRAPPER_PATH) != PREDECESSOR_WRAPPER_SHA256:
        raise RuntimeError("failed-run predecessor wrapper changed")
    if sha256_file(STRICT_CONTROL_PATH) != STRICT_CONTROL_SHA256:
        raise RuntimeError("strict import control changed")
    blender = no_active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")

    attempt = allocate_attempt_directory()
    child_result_path = attempt / "CHILD_RESULT.json"
    stderr_path = attempt / "CHILD_STDERR_FAULTHANDLER.log"
    phase_path = attempt / "PARENT_PHASE_JOURNAL.jsonl"
    marker_path = attempt / "ATTEMPT_STARTED.json"
    report_path = attempt / "COMPONENT_ISOLATION_REPORT.json"
    started_at = utc_now()
    marker_sha256 = write_json_exclusive(
        marker_path,
        {
            "schema_version": 1,
            "artifact_kind": "blackwell_import_component_isolation_started",
            "started_at": started_at,
            "arm": arm,
            "component_spec": ARM_SPECS[arm],
            "tool_sha256": tool_hash,
            "candidate_hashes": hashes,
            "failed_evidence": failed_evidence,
            "no_active_blender": blender,
            "timeout_seconds": timeout_seconds,
            "cuda_api_invoked": False,
            "model_loaded": False,
            "audio_generated": False,
            "candidate_promoted": False,
            "production_routing_changed": False,
        },
    )
    config = candidate_contract.load_candidate_config(CONFIG_PATH)
    environment = candidate_client.restricted_candidate_environment(
        config,
        session_nonce=secrets.token_urlsafe(48),
        allow_gpu_model_load=True,
    )
    environment[DIAGNOSTIC_OPT_IN] = "1"
    command = [
        str(candidate_contract.project_file(config["python"])),
        str(Path(__file__).resolve()),
        "--child-arm",
        arm,
        "--child-result-path",
        str(child_result_path.resolve()),
    ]
    use_pipes = bool(ARM_SPECS[arm]["parent_pipe_drains_and_phase_fsync"])
    use_stdin = bool(ARM_SPECS[arm]["stdin_reader"])
    stdout_metrics: dict[str, Any] = {}
    stderr_metrics: dict[str, Any] = {}
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    direct_stderr: Any | None = None
    if not use_pipes:
        direct_stderr = stderr_path.open("xb")
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=environment,
        stdin=subprocess.PIPE if use_stdin else subprocess.DEVNULL,
        stdout=subprocess.PIPE if use_pipes else subprocess.DEVNULL,
        stderr=subprocess.PIPE if use_pipes else direct_stderr,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if direct_stderr is not None:
        direct_stderr.close()
    if use_pipes:
        stdout_thread = threading.Thread(
            target=_drain_stdout_with_phase_fsync,
            args=(process.stdout, phase_path, stdout_metrics),
            name="component-isolation-parent-stdout-drain",
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_drain_stderr,
            args=(process.stderr, stderr_path, stderr_metrics),
            name="component-isolation-parent-stderr-drain",
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

    wall_started = time.perf_counter()
    timed_out = False
    forced_kill = False
    stdin_closed_after_result = False
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None and time.monotonic() < deadline:
        if use_stdin and child_result_path.is_file() and process.stdin is not None:
            process.stdin.close()
            stdin_closed_after_result = True
        time.sleep(0.05)
    if process.poll() is None:
        timed_out = True
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            forced_kill = True
            process.kill()
            process.wait(timeout=10)
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
    if stdout_thread is not None:
        stdout_thread.join(timeout=10)
    if stderr_thread is not None:
        stderr_thread.join(timeout=10)
    wall_seconds = round(time.perf_counter() - wall_started, 9)
    child_result = (
        json.loads(child_result_path.read_text(encoding="utf-8"))
        if child_result_path.is_file()
        else None
    )
    candidate_after = exact_candidate_hashes()
    report = {
        "schema_version": 1,
        "artifact_kind": "blackwell_import_component_isolation_report",
        "started_at": started_at,
        "finished_at": utc_now(),
        "status": (
            "completed_import_only"
            if child_result is not None and process.returncode == 0 and not timed_out
            else "bounded_timeout_preserved"
            if timed_out
            else "failed_preserved"
        ),
        "arm": arm,
        "component_spec": ARM_SPECS[arm],
        "tool_sha256": tool_hash,
        "candidate_hashes_before": hashes,
        "candidate_hashes_after": candidate_after,
        "candidate_unchanged": candidate_after == EXPECTED_CANDIDATE_HASHES,
        "failed_evidence": failed_evidence,
        "independent_defender_state": "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        "defender_queried": False,
        "defender_changed": False,
        "no_active_blender": blender,
        "attempt_started_marker": {
            "path": relative(marker_path),
            "sha256": marker_sha256,
        },
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "wall_seconds": wall_seconds,
        "owned_child_pid": process.pid,
        "owned_child_exit_code": process.returncode,
        "owned_child_forced_kill": forced_kill,
        "stdin_closed_only_after_result_or_timeout": (
            (not use_stdin) or stdin_closed_after_result or timed_out
        ),
        "parent_pipe_metrics": {
            **stdout_metrics,
            **stderr_metrics,
            "enabled": use_pipes,
        },
        "child_result": child_result,
        "child_result_artifact": (
            {
                "path": relative(child_result_path),
                "bytes": child_result_path.stat().st_size,
                "sha256": sha256_file(child_result_path),
            }
            if child_result_path.is_file()
            else None
        ),
        "stderr_artifact": (
            {
                "path": relative(stderr_path),
                "bytes": stderr_path.stat().st_size,
                "sha256": sha256_file(stderr_path),
            }
            if stderr_path.is_file()
            else None
        ),
        "phase_journal_artifact": (
            {
                "path": relative(phase_path),
                "bytes": phase_path.stat().st_size,
                "sha256": sha256_file(phase_path),
            }
            if phase_path.is_file()
            else None
        ),
        "torch_import_only": True,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "kira_invoked": False,
        "blender_started": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
        "causal_conclusion_claimed": False,
    }
    write_json_exclusive(report_path, report)
    return report_path, report


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "blackwell_import_component_isolation_description",
        "status": "PREPARED_NOT_EXECUTED",
        "arms": ARM_SPECS,
        "one_arm_per_invocation": True,
        "maximum_arm_timeout_seconds": MAX_ARM_TIMEOUT_SECONDS,
        "failed_evidence": validate_failed_evidence(),
        "candidate_hashes": exact_candidate_hashes(),
        "independent_defender_state": "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        "defender_queried": False,
        "defender_changed": False,
        "blackwell_runtime_started": False,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
    }


def static_self_check() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    child_source = source[source.index("\ndef child_arm") : source.index("\ndef _drain_stdout")]
    expected_arm_names = {
        "minimal_direct",
        "worker_context_only",
        "nvidia_boundary_only",
        "resource_sampler_host_only",
        "stdin_reader_only",
        "pipe_drains_fsync_only",
        "combined_real_shape",
    }
    checks = {
        "candidate_hashes_exact": exact_candidate_hashes() == EXPECTED_CANDIDATE_HASHES,
        "failed_evidence_exact": bool(validate_failed_evidence()["files"]),
        "predecessor_wrapper_exact": (
            sha256_file(PREDECESSOR_WRAPPER_PATH) == PREDECESSOR_WRAPPER_SHA256
        ),
        "strict_control_exact": sha256_file(STRICT_CONTROL_PATH) == STRICT_CONTROL_SHA256,
        "exact_arm_set": set(ARM_SPECS) == expected_arm_names,
        "one_arm_cli_only": ("for arm " + "in ARM_SPECS") not in source,
        "timeout_capped_at_180": MAX_ARM_TIMEOUT_SECONDS == 180.0,
        "torch_import_boundary_present": 'importlib.import_module("torch")' in child_source,
        "no_torch_cuda_call": "torch.cuda" not in child_source,
        "no_torchaudio_import_call": 'import_module("torchaudio")' not in child_source,
        "no_chatterbox_import_call": 'import_module("chatterbox")' not in child_source,
        "no_model_factory_call": "from_pretrained(" not in child_source,
        "no_audio_or_playback_call": not any(
            marker in child_source
            for marker in ("winsound.PlaySound(", "sounddevice.play(", "sd.play(")
        ),
        "no_ollama_call": ("/api" + "/ps") not in source
        and ("qwen_residency" + "_evidence(") not in source,
        "no_defender_mutation": not any(
            marker in source
            for marker in (
                "Add" + "-MpPreference",
                "Remove" + "-MpPreference",
                "Set" + "-MpPreference",
            )
        ),
        "no_elevation": ("run" + "as") not in source.casefold(),
        "no_promotion_or_route_change": not any(
            marker in source
            for marker in (
                "promote_" + "candidate(",
                "activate_" + "candidate(",
                "set_production_" + "route(",
            )
        ),
        "append_only_writes": 'path.open("xb")' in source,
    }
    return {
        "schema_version": 1,
        "artifact_kind": "blackwell_import_component_isolation_static_self_check",
        "checks": checks,
        "passed": all(checks.values()),
        "blackwell_runtime_started": False,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "defender_queried": False,
        "defender_changed": False,
        "blender_started": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--describe", action="store_true")
    group.add_argument("--static-self-check", action="store_true")
    group.add_argument("--run-arm", action="store_true")
    group.add_argument("--child-arm", choices=tuple(ARM_SPECS), help=argparse.SUPPRESS)
    parser.add_argument("--arm", choices=tuple(ARM_SPECS))
    parser.add_argument("--child-result-path", default="", help=argparse.SUPPRESS)
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-tool-sha256", default="")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    parser.add_argument("--expected-failed-report-sha256", default="")
    parser.add_argument("--expected-post-failure-check-sha256", default="")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_ARM_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if args.child_arm:
        return child_arm(args.child_arm, args.child_result_path)
    if args.static_self_check:
        result = static_self_check()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    if not args.run_arm:
        print(json.dumps(describe(), indent=2, sort_keys=True))
        return 0
    if not args.confirm_no_active_blender:
        raise SystemExit("--confirm-no-active-blender is required")
    if args.arm is None:
        raise SystemExit("--arm is required")
    timeout_seconds = max(30.0, min(MAX_ARM_TIMEOUT_SECONDS, float(args.timeout_seconds)))
    report_path, report = run_one_arm(
        arm=args.arm,
        expected_tool_sha256=args.expected_tool_sha256,
        expected_config_sha256=args.expected_candidate_config_sha256,
        expected_failed_report_sha256=args.expected_failed_report_sha256,
        expected_post_failure_check_sha256=args.expected_post_failure_check_sha256,
        timeout_seconds=timeout_seconds,
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "status": report["status"],
                "arm": report["arm"],
                "timed_out": report["timed_out"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "completed_import_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())
