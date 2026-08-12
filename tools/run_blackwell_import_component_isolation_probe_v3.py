#!/usr/bin/env python3
"""Windows-lineage-hardened Blackwell Torch-import component-isolation probe.

The reviewed predecessor remains preserved as rejected static evidence.  This
revision adds an internally capped parent/child deadline, a hash-bound parent
authorization record, atomic-ready result semantics, bounded owned-child and
drain cleanup, and tri-state child outcome evidence. This revision additionally
binds the controller to the exact Popen launch PID so the standard Windows venv
redirector lineage is accepted without accepting an unrelated process.
"""

from __future__ import annotations

import argparse
import ctypes
import faulthandler
import hashlib
import hmac
import importlib
import importlib.util
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import time
import traceback
from ctypes import wintypes
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REJECTED_PROBE_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe.py"
REJECTED_PROBE_SHA256 = "a275123607567db7e9663036829808c51c24e792e3c44445d625a45697ee5153"
PREDECESSOR_V2_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe_v2.py"
PREDECESSOR_V2_SHA256 = "95d6a37c141b4ec7c425bc22a023e089ea91c0f041173d7940de2450d3750a0a"
REDIRECTOR_EVIDENCE_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_import_component_isolation_attempt01_analysis"
    / "WINDOWS_VENV_REDIRECTOR_MICRODIAGNOSTIC.json"
)
REDIRECTOR_EVIDENCE_SHA256 = "3606e8e42776db2a229569baee9169643f57e4cc4ac8af40098a44d6f43c7593"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


rejected: Any | None = None


def _load_rejected_dependency() -> Any:
    """Hash-gate and load the rejected helper only after the caller is bounded."""

    global rejected
    if rejected is not None:
        return rejected
    if not hmac.compare_digest(sha256_file(PREDECESSOR_V2_PATH), PREDECESSOR_V2_SHA256):
        raise RuntimeError("sealed v2 probe changed before v3 dependency load")
    if not hmac.compare_digest(
        sha256_file(REDIRECTOR_EVIDENCE_PATH), REDIRECTOR_EVIDENCE_SHA256
    ):
        raise RuntimeError("Windows redirector evidence changed before v3 dependency load")
    if not hmac.compare_digest(sha256_file(REJECTED_PROBE_PATH), REJECTED_PROBE_SHA256):
        raise RuntimeError("reviewed rejected probe changed before dependency load")
    spec = importlib.util.spec_from_file_location(
        "rejected_blackwell_import_component_probe_v2_dependency",
        REJECTED_PROBE_PATH,
    )
    assert spec is not None and spec.loader is not None
    dependency = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = dependency
    spec.loader.exec_module(dependency)
    rejected = dependency
    return dependency


OUTPUT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_component_isolation_v2"
)
DIAGNOSTIC_OPT_IN = "KIRA_BLACKWELL_IMPORT_COMPONENT_ISOLATION_V3"
PARENT_NONCE_ENV = "KIRA_BLACKWELL_IMPORT_COMPONENT_PARENT_NONCE_V3"
DEFAULT_TOTAL_TIMEOUT_SECONDS = 180.0
MAX_TOTAL_TIMEOUT_SECONDS = 180.0
MAX_IMPORT_MEASUREMENT_SECONDS = 120.0
FINALIZATION_RESERVE_SECONDS = 30.0
REPORT_WRITE_RESERVE_SECONDS = 5.0
CHILD_SELF_EXIT_GRACE_SECONDS = 5.0
OWNED_PROCESS_TERMINATE_GRACE_SECONDS = 5.0
OWNED_PROCESS_KILL_GRACE_SECONDS = 5.0
DRAIN_JOIN_SECONDS = 2.0
ARM_SPECS: dict[str, dict[str, Any]] = {
    "minimal_direct": {
        "worker_module_context": False,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": False,
        "pipe_transport_bundle": False,
        "comparison": "standalone restricted-environment baseline",
    },
    "worker_context_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": False,
        "pipe_transport_bundle": False,
        "comparison": "minimal_direct isolates exact persistent_worker module context",
    },
    "nvidia_boundary_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": True,
        "resource_sampler": "none",
        "stdin_reader": False,
        "pipe_transport_bundle": False,
        "comparison": "worker_context_only adds one exact nvidia-smi boundary query",
    },
    "resource_sampler_host_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "real_class_external_gpu_stubbed",
        "stdin_reader": False,
        "pipe_transport_bundle": False,
        "comparison": "worker_context_only adds real ResourceSampler host activity with no nvidia-smi process",
    },
    "stdin_reader_only": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": True,
        "pipe_transport_bundle": False,
        "comparison": "worker_context_only adds the real inherited-stdin reader",
    },
    "pipe_drains_phase_fsync_bundle": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": False,
        "resource_sampler": "none",
        "stdin_reader": False,
        "pipe_transport_bundle": True,
        "comparison": "worker_context_only adds one declared serialization/flush/pipe/drains/file-write/phase-fsync bundle; mechanisms inside the bundle are not individually isolated",
    },
    "combined_real_shape": {
        "worker_module_context": True,
        "nvidia_smi_boundary_call": True,
        "resource_sampler": "real_class_full_boundary_gpu_and_host",
        "stdin_reader": True,
        "pipe_transport_bundle": True,
        "comparison": "interaction/reproduction arm after individual component arms",
    },
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _windows_process_identity(pid: int) -> dict[str, Any]:
    """Read one live Windows process identity without CIM/WMI or mutation."""

    if os.name != "nt" or not isinstance(pid, int) or pid <= 0:
        return {"query_succeeded": False, "pid": pid, "error": "invalid_or_non_windows"}
    process_query_limited_information = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return {
            "query_succeeded": False,
            "pid": pid,
            "error": f"OpenProcess:{ctypes.get_last_error()}",
        }
    try:
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            return {
                "query_succeeded": False,
                "pid": pid,
                "error": f"GetProcessTimes:{ctypes.get_last_error()}",
            }
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return {
                "query_succeeded": False,
                "pid": pid,
                "error": f"QueryFullProcessImageNameW:{ctypes.get_last_error()}",
            }
        creation_time_100ns = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        return {
            "query_succeeded": True,
            "pid": pid,
            "creation_time_100ns": creation_time_100ns,
            "image_path": os.path.normcase(os.path.normpath(buffer.value)),
            "query_kind": "Win32_OpenProcess_GetProcessTimes_QueryFullProcessImageNameW",
        }
    finally:
        kernel32.CloseHandle(handle)


def _same_process_identity(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    return (
        expected.get("query_succeeded") is True
        and observed.get("query_succeeded") is True
        and observed.get("pid") == expected.get("pid")
        and observed.get("creation_time_100ns") == expected.get("creation_time_100ns")
        and observed.get("image_path") == expected.get("image_path")
    )


def classify_windows_launch_lineage(
    *,
    controller_pid: int,
    popen_launch_pid: int,
    executing_child_pid: int,
    executing_child_parent_pid: int,
) -> dict[str, Any]:
    valid_ids = all(
        isinstance(value, int) and value > 0
        for value in (
            controller_pid,
            popen_launch_pid,
            executing_child_pid,
            executing_child_parent_pid,
        )
    )
    direct = (
        valid_ids
        and executing_child_pid == popen_launch_pid
        and executing_child_parent_pid == controller_pid
    )
    one_redirector = (
        valid_ids
        and executing_child_pid != popen_launch_pid
        and executing_child_parent_pid == popen_launch_pid
    )
    return {
        "passed": bool(direct or one_redirector),
        "lineage_kind": (
            "DIRECT_POPEN_CHILD"
            if direct
            else "ONE_WINDOWS_VENV_REDIRECTOR"
            if one_redirector
            else "UNRELATED_OR_UNBOUNDED_PROCESS_CHAIN"
        ),
        "controller_pid": controller_pid,
        "popen_launch_pid": popen_launch_pid,
        "executing_child_pid": executing_child_pid,
        "executing_child_parent_pid": executing_child_parent_pid,
        "maximum_redirector_depth": 1,
    }


def _launch_binding_hmac(payload: dict[str, Any], nonce: str) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "binding_hmac_sha256"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(nonce.encode("utf-8"), encoded, hashlib.sha256).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(encoded).hexdigest()


def bounded_timeouts(requested_total_seconds: float) -> tuple[float, float]:
    total = max(60.0, min(MAX_TOTAL_TIMEOUT_SECONDS, float(requested_total_seconds)))
    measurement = min(MAX_IMPORT_MEASUREMENT_SECONDS, max(30.0, total - 30.0))
    return total, measurement


def allocate_attempt_directory() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        path = OUTPUT_ROOT / f"attempt_{number:02d}"
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path
    raise RuntimeError("no append-only hardened component-isolation attempt is available")


def _child_hard_exit(stop: threading.Event, seconds: float) -> None:
    if not stop.wait(seconds):
        os._exit(124)


def _validate_launch_binding(
    *,
    arm: str,
    result_path: Path,
    authorization: dict[str, Any],
    expected_authorization_sha256: str,
    launch_binding_path_value: str,
    nonce: str,
) -> dict[str, Any]:
    binding_path = Path(launch_binding_path_value).resolve()
    binding_path.parent.resolve().relative_to(OUTPUT_ROOT.resolve())
    if binding_path.name != "PARENT_LAUNCH_BINDING.json":
        raise ValueError("parent launch-binding filename is not accepted")
    if binding_path.parent != result_path.parent:
        raise RuntimeError("parent launch binding is outside the authorized attempt")
    if authorization.get("launch_binding_path") != relative(binding_path):
        raise RuntimeError("parent launch-binding path does not match authorization")
    wait_deadline = time.monotonic() + 5.0
    while not binding_path.is_file() and time.monotonic() < wait_deadline:
        time.sleep(0.01)
    if not binding_path.is_file():
        raise RuntimeError("parent launch-binding record did not become ready")
    binding_bytes = binding_path.read_bytes()
    binding = json.loads(binding_bytes.decode("utf-8"))
    if not isinstance(binding, dict):
        raise RuntimeError("parent launch-binding record is not an object")
    observed_hmac = str(binding.get("binding_hmac_sha256") or "")
    expected_hmac = _launch_binding_hmac(binding, nonce)
    controller_identity = authorization.get("controller_process_identity")
    controller_record = controller_identity if isinstance(controller_identity, dict) else {}
    live_controller = (
        _windows_process_identity(controller_record.get("pid"))
        if isinstance(controller_record.get("pid"), int)
        else {"query_succeeded": False, "error": "missing_controller_identity"}
    )
    lineage = classify_windows_launch_lineage(
        controller_pid=int(controller_record.get("pid") or 0),
        popen_launch_pid=int(binding.get("popen_launch_pid") or 0),
        executing_child_pid=os.getpid(),
        executing_child_parent_pid=os.getppid(),
    )
    launch_process_identity = binding.get("popen_process_identity")
    launch_process_record = (
        launch_process_identity if isinstance(launch_process_identity, dict) else {}
    )
    live_launch_process = _windows_process_identity(
        os.getpid()
        if os.getpid() == int(binding.get("popen_launch_pid") or 0)
        else os.getppid()
    )
    created_time_ns = binding.get("created_time_ns")
    age_seconds = (
        (time.time_ns() - created_time_ns) / 1_000_000_000
        if isinstance(created_time_ns, int)
        else None
    )
    required = {
        "schema": binding.get("schema_version") == 1,
        "kind": binding.get("artifact_kind")
        == "blackwell_import_component_isolation_v3_parent_launch_binding",
        "arm": binding.get("arm") == arm,
        "authorization": binding.get("authorization_record_sha256")
        == expected_authorization_sha256.casefold(),
        "result_path": binding.get("child_result_path") == relative(result_path),
        "fresh_binding": age_seconds is not None and -5.0 <= age_seconds <= 120.0,
        "nonce_hmac": len(observed_hmac) == 64
        and hmac.compare_digest(observed_hmac, expected_hmac),
        "controller_identity_bound": binding.get("controller_process_identity")
        == controller_identity,
        "controller_still_live_and_exact": _same_process_identity(
            controller_record,
            live_controller,
        ),
        "launch_process_identity_bound": isinstance(launch_process_identity, dict)
        and launch_process_identity.get("pid") == binding.get("popen_launch_pid"),
        "launch_process_still_live_and_exact": _same_process_identity(
            launch_process_record,
            live_launch_process,
        ),
        "bounded_launch_lineage": lineage["passed"] is True,
    }
    if not all(required.values()):
        raise RuntimeError(
            "child Windows launch-binding contract failed: "
            f"required={required}, lineage={lineage}, live_controller={live_controller}"
        )
    return {
        "path": relative(binding_path),
        "sha256": hashlib.sha256(binding_bytes).hexdigest(),
        "bytes": len(binding_bytes),
        "required": required,
        "lineage": lineage,
        "live_controller_identity": live_controller,
        "live_launch_process_identity": live_launch_process,
    }


def _validate_child_authorization(
    *,
    arm: str,
    result_path: Path,
    authorization_path_value: str,
    expected_authorization_sha256: str,
    launch_binding_path_value: str,
    measurement_timeout_seconds: float,
) -> dict[str, Any]:
    authorization_path = Path(authorization_path_value).resolve()
    authorization_path.parent.resolve().relative_to(OUTPUT_ROOT.resolve())
    if authorization_path.name != "ATTEMPT_STARTED.json":
        raise ValueError("child authorization record filename is not accepted")
    if sha256_file(authorization_path) != expected_authorization_sha256.casefold():
        raise RuntimeError("child authorization record hash mismatch")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    nonce = str(os.environ.get(PARENT_NONCE_ENV) or "")
    created_time_ns = authorization.get("created_time_ns")
    age_seconds = (
        (time.time_ns() - created_time_ns) / 1_000_000_000
        if isinstance(created_time_ns, int)
        else None
    )
    if len(nonce) < 32 or len(nonce) > 256:
        raise RuntimeError("child parent nonce is missing or invalid")
    required = {
        "arm": authorization.get("arm") == arm,
        "nonce": authorization.get("child_parent_nonce_sha256") == sha256_text(nonce),
        "tool": authorization.get("tool_sha256") == sha256_file(Path(__file__).resolve()),
        "timeout": float(authorization.get("import_measurement_timeout_seconds") or 0.0)
        == measurement_timeout_seconds,
        "timeout_cap": measurement_timeout_seconds <= MAX_IMPORT_MEASUREMENT_SECONDS,
        "fresh_record": age_seconds is not None and -5.0 <= age_seconds <= 120.0,
        "controller_identity_present": isinstance(
            authorization.get("controller_process_identity"), dict
        ),
        "same_attempt_directory": authorization_path.parent == result_path.parent,
        "bound_result_path": authorization.get("child_result_path")
        == relative(result_path),
        "blender_query": (authorization.get("no_active_blender") or {}).get(
            "query_succeeded"
        )
        is True,
        "blender_inactive": (authorization.get("no_active_blender") or {}).get("active")
        is False,
    }
    if not all(required.values()):
        raise RuntimeError(f"child authorization contract failed: {required}")
    authorization["validated_launch_binding"] = _validate_launch_binding(
        arm=arm,
        result_path=result_path,
        authorization=authorization,
        expected_authorization_sha256=expected_authorization_sha256,
        launch_binding_path_value=launch_binding_path_value,
        nonce=nonce,
    )
    return authorization


def _emit_pipe_bundle_event(arm: str) -> None:
    print(
        json.dumps(
            {
                "schema_version": 1,
                "message_type": "event",
                "event": "component_isolation_import_started",
                "arm": arm,
                "phase": "imports.torch",
            },
            sort_keys=True,
        ),
        flush=True,
    )


def child_arm_v3(
    *,
    arm: str,
    result_path_value: str,
    authorization_path_value: str,
    expected_authorization_sha256: str,
    launch_binding_path_value: str,
    measurement_timeout_seconds: float,
) -> int:
    measurement_timeout = max(
        30.0,
        min(MAX_IMPORT_MEASUREMENT_SECONDS, float(measurement_timeout_seconds)),
    )
    hard_exit_stop = threading.Event()
    hard_exit_thread = threading.Thread(
        target=_child_hard_exit,
        args=(hard_exit_stop, measurement_timeout + CHILD_SELF_EXIT_GRACE_SECONDS),
        name="component-isolation-v3-child-hard-exit",
        daemon=True,
    )
    hard_exit_thread.start()
    if os.environ.get(DIAGNOSTIC_OPT_IN) != "1":
        raise RuntimeError("hardened component-isolation child opt-in is absent")
    if arm not in ARM_SPECS:
        raise ValueError("unknown hardened component-isolation arm")
    result_path = Path(result_path_value).resolve()
    result_path.parent.resolve().relative_to(OUTPUT_ROOT.resolve())
    if result_path.name != "CHILD_RESULT.json":
        raise ValueError("child result filename is not accepted")
    authorization = _validate_child_authorization(
        arm=arm,
        result_path=result_path,
        authorization_path_value=authorization_path_value,
        expected_authorization_sha256=expected_authorization_sha256,
        launch_binding_path_value=launch_binding_path_value,
        measurement_timeout_seconds=measurement_timeout,
    )
    dependency = _load_rejected_dependency()
    ready_path = result_path.with_name("CHILD_RESULT_READY.json")
    if result_path.exists() or ready_path.exists():
        raise RuntimeError("hardened child output already exists")
    hashes = dependency.exact_candidate_hashes()
    if hashes != dependency.EXPECTED_CANDIDATE_HASHES:
        raise RuntimeError("restored candidate hashes changed")
    config = dependency.candidate_contract.load_candidate_config(dependency.CONFIG_PATH)
    dependency.candidate_contract.verify_candidate_config(config)
    cache_paths = dependency.candidate_contract.verify_restricted_environment(
        config,
        require_load_opt_in=True,
    )
    faulthandler.enable(file=sys.stderr, all_threads=True)
    faulthandler.dump_traceback_later(30.0, repeat=True, file=sys.stderr, exit=False)
    spec = ARM_SPECS[arm]
    result: dict[str, Any] = {
        "schema_version": 3,
        "artifact_kind": "blackwell_import_component_isolation_v3_child",
        "arm": arm,
        "component_spec": spec,
        "candidate_hashes": hashes,
        "cache_paths": cache_paths,
        "authorization_record_sha256": expected_authorization_sha256.casefold(),
        "controller_process_identity": authorization["controller_process_identity"],
        "launch_binding": authorization["validated_launch_binding"],
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
    original_gpu_probe: Any | None = None
    stubbed_gpu_calls = 0
    return_code = 2
    try:
        child_blender = dependency.no_active_blender_evidence()
        result["child_no_active_blender"] = child_blender
        if (
            child_blender.get("query_succeeded") is not True
            or child_blender.get("active") is not False
        ):
            raise RuntimeError(f"child no-active-Blender gate failed: {child_blender}")
        if spec["worker_module_context"]:
            if sha256_file(dependency.WORKER_PATH) != dependency.EXPECTED_CANDIDATE_HASHES[
                "candidate_worker"
            ]:
                raise RuntimeError("candidate worker changed before module import")
            worker = importlib.import_module("persistent_worker")
            result["worker_module_loaded_before_torch"] = True
        else:
            result["worker_module_loaded_before_torch"] = False
        if spec["stdin_reader"]:
            incoming: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=2)
            stdin_thread = threading.Thread(
                target=worker._stdin_reader,
                args=(incoming, int(config["bounds"]["max_line_bytes"])),
                name="component-isolation-v3-real-stdin-reader",
                daemon=True,
            )
            stdin_thread.start()
        nvidia_boundary: dict[str, Any] | None = None
        if spec["nvidia_smi_boundary_call"] and spec["resource_sampler"] == "none":
            started = time.perf_counter_ns()
            value = worker._gpu_memory_used_mib()
            finished = time.perf_counter_ns()
            nvidia_boundary = {
                "calls": 1,
                "value_mib": value,
                "elapsed_seconds": round((finished - started) / 1_000_000_000, 9),
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
        if spec["pipe_transport_bundle"]:
            _emit_pipe_bundle_event(arm)
        result["active_threads_before_import"] = [
            {
                "name": thread.name,
                "daemon": bool(thread.daemon),
                "alive": bool(thread.is_alive()),
            }
            for thread in threading.enumerate()
        ]
        started = time.perf_counter_ns()
        torch = importlib.import_module("torch")
        finished = time.perf_counter_ns()
        numpy_module = sys.modules.get("numpy")
        resources = sampler.stop() if sampler is not None else None
        sampler = None
        if original_gpu_probe is not None:
            worker._gpu_memory_used_mib = original_gpu_probe
            original_gpu_probe = None
        result.update(
            {
                "torch_imported": True,
                "torch_version": str(torch.__version__),
                "numpy_loaded_transitively": numpy_module is not None,
                "numpy_version": (
                    str(getattr(numpy_module, "__version__", ""))
                    if numpy_module is not None
                    else None
                ),
                "import_elapsed_seconds": round((finished - started) / 1_000_000_000, 9),
                "nvidia_smi_boundary": nvidia_boundary,
                "resource_sampler": resources,
                "external_gpu_probe_stub_calls": stubbed_gpu_calls,
                "torchaudio_imported": "torchaudio" in sys.modules,
                "chatterbox_imported": any(
                    name == "chatterbox" or name.startswith("chatterbox.")
                    for name in sys.modules
                ),
            }
        )
        result["passed"] = (
            result["torch_version"] == "2.11.0+cu130"
            and result["torchaudio_imported"] is False
            and result["chatterbox_imported"] is False
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
        result["stdin_reader_started"] = stdin_thread is not None
        result["stdin_reader_alive_before_parent_eof"] = (
            stdin_thread.is_alive() if stdin_thread is not None else False
        )
        result_sha256 = write_json_exclusive(result_path, result)
        write_json_exclusive(
            ready_path,
            {
                "schema_version": 1,
                "artifact_kind": "blackwell_import_component_isolation_v3_child_ready",
                "arm": arm,
                "authorization_record_sha256": expected_authorization_sha256.casefold(),
                "launch_binding_sha256": authorization["validated_launch_binding"]["sha256"],
                "child_result_sha256": result_sha256,
                "child_result_bytes": result_path.stat().st_size,
            },
        )
        if stdin_thread is not None:
            stdin_thread.join(timeout=3)
        hard_exit_stop.set()
    return return_code


def _drain_stdout(stream: Any, path: Path, metrics: dict[str, Any]) -> None:
    lines = 0
    fsync_calls = 0
    try:
        with path.open("xb", buffering=0) as handle:
            while True:
                raw = stream.readline(1024 * 1024 + 2)
                if not raw:
                    break
                handle.write(raw)
                os.fsync(handle.fileno())
                lines += 1
                fsync_calls += 1
    except BaseException as exc:
        metrics["stdout_drain_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        metrics.update({"stdout_lines": lines, "phase_journal_fsync_calls": fsync_calls})


def _drain_stderr(stream: Any, path: Path, metrics: dict[str, Any]) -> None:
    total = 0
    try:
        with path.open("xb", buffering=0) as handle:
            while True:
                raw = stream.read(4096)
                if not raw:
                    break
                handle.write(raw)
                total += len(raw)
    except BaseException as exc:
        metrics["stderr_drain_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        metrics["stderr_bytes"] = total


def _safe_child_result(
    result_path: Path,
    ready_path: Path,
    *,
    expected_arm: str,
    expected_component_spec: dict[str, Any],
    expected_candidate_hashes: dict[str, str],
    expected_authorization_sha256: str,
    expected_launch_binding_sha256: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    evidence: dict[str, Any] = {
        "ready_marker_present": ready_path.is_file(),
        "result_present": result_path.is_file(),
        "trusted_complete": False,
        "parse_error": None,
    }
    if not ready_path.is_file():
        return None, evidence
    try:
        ready = json.loads(ready_path.read_text(encoding="utf-8"))
        if not isinstance(ready, dict):
            raise ValueError("child ready marker is not an object")
        if ready.get("schema_version") != 1:
            raise ValueError("child ready marker schema is not accepted")
        if ready.get("artifact_kind") != "blackwell_import_component_isolation_v3_child_ready":
            raise ValueError("child ready marker kind is not accepted")
        if ready.get("arm") != expected_arm:
            raise ValueError("child ready marker arm mismatch")
        if ready.get("authorization_record_sha256") != expected_authorization_sha256:
            raise ValueError("child ready authorization binding mismatch")
        if ready.get("launch_binding_sha256") != expected_launch_binding_sha256:
            raise ValueError("child ready launch-binding mismatch")
        actual_hash = sha256_file(result_path)
        actual_bytes = result_path.stat().st_size
        if ready.get("child_result_sha256") != actual_hash:
            raise ValueError("child result hash does not match ready marker")
        if int(ready.get("child_result_bytes") or -1) != actual_bytes:
            raise ValueError("child result size does not match ready marker")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError("child result is not an object")
        semantic_checks = {
            "schema": result.get("schema_version") == 3,
            "kind": result.get("artifact_kind")
            == "blackwell_import_component_isolation_v3_child",
            "arm": result.get("arm") == expected_arm,
            "component_spec": result.get("component_spec") == expected_component_spec,
            "candidate_hashes": result.get("candidate_hashes")
            == expected_candidate_hashes,
            "authorization": result.get("authorization_record_sha256")
            == expected_authorization_sha256,
            "launch_binding": isinstance(result.get("launch_binding"), dict)
            and result["launch_binding"].get("sha256") == expected_launch_binding_sha256
            and (result["launch_binding"].get("lineage") or {}).get("passed") is True,
            "child_blender_gate": isinstance(result.get("child_no_active_blender"), dict)
            and result["child_no_active_blender"].get("query_succeeded") is True
            and result["child_no_active_blender"].get("active") is False,
        }
        if not all(semantic_checks.values()):
            raise ValueError(f"child result semantic binding failed: {semantic_checks}")
        evidence.update(
            {
                "trusted_complete": True,
                "semantic_checks": semantic_checks,
                "result_sha256": actual_hash,
                "result_bytes": actual_bytes,
                "ready_sha256": sha256_file(ready_path),
                "ready_bytes": ready_path.stat().st_size,
            }
        )
        return result, evidence
    except Exception as exc:
        evidence["parse_error"] = f"{type(exc).__name__}: {exc}"
        return None, evidence


def _child_outcomes(result: dict[str, Any] | None) -> dict[str, Any]:
    keys = (
        "torch_imported",
        "cuda_api_invoked",
        "torchaudio_imported",
        "chatterbox_imported",
        "model_loaded",
        "audio_generated",
        "playback_performed",
        "ollama_invoked",
        "candidate_promoted",
        "production_routing_changed",
    )
    if not isinstance(result, dict):
        return {
            "evidence_complete": False,
            **{key: None for key in keys},
            "torch_import_only": None,
        }
    values = {
        key: result.get(key) if isinstance(result.get(key), bool) else None for key in keys
    }
    complete = all(values[key] is not None for key in keys)
    import_only = (
        values["torch_imported"] is True
        and all(
            values[key] is False
            for key in keys
            if key != "torch_imported"
        )
        if complete
        else None
    )
    return {"evidence_complete": complete, **values, "torch_import_only": import_only}


def _bounded_wait(process: subprocess.Popen[bytes], seconds: float) -> bool:
    try:
        process.wait(timeout=max(0.05, seconds))
        return True
    except subprocess.TimeoutExpired:
        return False


def _safe_join_drain(
    thread: threading.Thread | None,
    *,
    timeout_seconds: float,
    metrics: dict[str, Any],
    label: str,
) -> None:
    if thread is None:
        return
    if thread.ident is None and not thread.is_alive():
        metrics.setdefault(f"{label}_drain_error", "thread_was_not_started")
        return
    try:
        thread.join(timeout=max(0.0, timeout_seconds))
    except RuntimeError as exc:
        metrics.setdefault(f"{label}_drain_error", f"{type(exc).__name__}: {exc}")


def run_one_arm_v3(
    *,
    arm: str,
    expected_tool_sha256: str,
    expected_candidate_config_sha256: str,
    expected_failed_report_sha256: str,
    expected_post_failure_check_sha256: str,
    requested_total_timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    run_started = time.monotonic()
    total_timeout, requested_measurement_timeout = bounded_timeouts(
        requested_total_timeout_seconds
    )
    overall_deadline = run_started + total_timeout

    def remaining_seconds() -> float:
        return max(0.0, overall_deadline - time.monotonic())

    if arm not in ARM_SPECS:
        raise ValueError("unknown hardened component-isolation arm")
    tool_hash = sha256_file(Path(__file__).resolve())
    if not hmac.compare_digest(tool_hash, expected_tool_sha256.strip().casefold()):
        raise ValueError("operator-bound hardened probe hash mismatch")
    dependency = _load_rejected_dependency()
    if dependency.exact_candidate_hashes() != dependency.EXPECTED_CANDIDATE_HASHES:
        raise RuntimeError("restored candidate hashes changed")
    if not hmac.compare_digest(
        expected_candidate_config_sha256.strip().casefold(),
        dependency.EXPECTED_CANDIDATE_HASHES["candidate_config"],
    ):
        raise ValueError("operator-bound candidate config hash mismatch")
    if not hmac.compare_digest(
        expected_failed_report_sha256.strip().casefold(),
        dependency.FAILED_EVIDENCE_HASHES[
            "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json"
        ],
    ):
        raise ValueError("operator did not bind preserved failed report")
    if not hmac.compare_digest(
        expected_post_failure_check_sha256.strip().casefold(),
        dependency.FAILED_EVIDENCE_HASHES["POST_FAILURE_PROCESS_CHECK.json"],
    ):
        raise ValueError("operator did not bind post-failure process check")
    failed_evidence = dependency.validate_failed_evidence()
    controller_identity = _windows_process_identity(os.getpid())
    if controller_identity.get("query_succeeded") is not True:
        raise RuntimeError(f"controller identity gate failed: {controller_identity}")
    blender = dependency.no_active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")
    config = dependency.candidate_contract.load_candidate_config(dependency.CONFIG_PATH)
    environment = dependency.candidate_client.restricted_candidate_environment(
        config,
        session_nonce=secrets.token_urlsafe(48),
        allow_gpu_model_load=True,
    )
    available_for_measurement = remaining_seconds() - FINALIZATION_RESERVE_SECONDS
    if available_for_measurement < 30.0:
        raise RuntimeError("overall arm deadline has insufficient bounded measurement time")
    measurement_timeout = min(
        requested_measurement_timeout,
        MAX_IMPORT_MEASUREMENT_SECONDS,
        available_for_measurement,
    )
    attempt = allocate_attempt_directory()
    marker_path = attempt / "ATTEMPT_STARTED.json"
    result_path = attempt / "CHILD_RESULT.json"
    ready_path = attempt / "CHILD_RESULT_READY.json"
    launch_binding_path = attempt / "PARENT_LAUNCH_BINDING.json"
    stderr_path = attempt / "CHILD_STDERR.log"
    phase_path = attempt / "PARENT_PHASE_JOURNAL.jsonl"
    report_path = attempt / "COMPONENT_ISOLATION_V3_REPORT.json"
    child_nonce = secrets.token_urlsafe(48)
    marker_created_time_ns = time.time_ns()
    marker_hash = write_json_exclusive(
        marker_path,
        {
            "schema_version": 3,
            "artifact_kind": "blackwell_import_component_isolation_v3_started",
            "arm": arm,
            "component_spec": ARM_SPECS[arm],
            "tool_sha256": tool_hash,
            "child_parent_nonce_sha256": sha256_text(child_nonce),
            "parent_pid": os.getpid(),
            "controller_process_identity": controller_identity,
            "created_time_ns": marker_created_time_ns,
            "child_result_path": relative(result_path),
            "launch_binding_path": relative(launch_binding_path),
            "sealed_v2_predecessor": {
                "path": relative(PREDECESSOR_V2_PATH),
                "sha256": PREDECESSOR_V2_SHA256,
            },
            "redirector_microdiagnostic": {
                "path": relative(REDIRECTOR_EVIDENCE_PATH),
                "sha256": REDIRECTOR_EVIDENCE_SHA256,
            },
            "total_timeout_seconds": total_timeout,
            "import_measurement_timeout_seconds": measurement_timeout,
            "no_active_blender": blender,
            "failed_evidence": failed_evidence,
        },
    )
    environment[DIAGNOSTIC_OPT_IN] = "1"
    environment[PARENT_NONCE_ENV] = child_nonce
    command = [
        str(dependency.candidate_contract.project_file(config["python"])),
        str(Path(__file__).resolve()),
        "--child-arm-v3",
        arm,
        "--child-result-path",
        str(result_path.resolve()),
        "--child-authorization-record",
        str(marker_path.resolve()),
        "--expected-child-authorization-sha256",
        marker_hash,
        "--child-launch-binding",
        str(launch_binding_path.resolve()),
        "--child-timeout-seconds",
        str(measurement_timeout),
    ]
    use_pipe_bundle = bool(ARM_SPECS[arm]["pipe_transport_bundle"])
    use_stdin = bool(ARM_SPECS[arm]["stdin_reader"])
    stdout_metrics: dict[str, Any] = {}
    stderr_metrics: dict[str, Any] = {}
    process: subprocess.Popen[bytes] | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    direct_stderr: Any | None = None
    timed_out = False
    terminate_sent = False
    kill_sent = False
    spawn_error: str | None = None
    launch_binding_hash: str | None = None
    stdin_closed_after_ready_or_timeout = False
    operation_started = time.monotonic()
    try:
        if not use_pipe_bundle:
            direct_stderr = stderr_path.open("xb")
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=environment,
            stdin=subprocess.PIPE if use_stdin else subprocess.DEVNULL,
            stdout=subprocess.PIPE if use_pipe_bundle else subprocess.DEVNULL,
            stderr=subprocess.PIPE if use_pipe_bundle else direct_stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        popen_process_identity = _windows_process_identity(process.pid)
        if popen_process_identity.get("query_succeeded") is not True:
            raise RuntimeError(
                f"exact Popen process identity gate failed: {popen_process_identity}"
            )
        launch_binding_payload = {
            "schema_version": 1,
            "artifact_kind": "blackwell_import_component_isolation_v3_parent_launch_binding",
            "arm": arm,
            "authorization_record_sha256": marker_hash,
            "controller_process_identity": controller_identity,
            "popen_launch_pid": process.pid,
            "popen_process_identity": popen_process_identity,
            "child_result_path": relative(result_path),
            "created_time_ns": time.time_ns(),
        }
        launch_binding_payload["binding_hmac_sha256"] = _launch_binding_hmac(
            launch_binding_payload,
            child_nonce,
        )
        launch_binding_hash = write_json_exclusive(
            launch_binding_path,
            launch_binding_payload,
        )
        if direct_stderr is not None:
            direct_stderr.close()
            direct_stderr = None
        if use_pipe_bundle:
            stdout_thread = threading.Thread(
                target=_drain_stdout,
                args=(process.stdout, phase_path, stdout_metrics),
                name="component-isolation-v3-stdout-drain",
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_drain_stderr,
                args=(process.stderr, stderr_path, stderr_metrics),
                name="component-isolation-v3-stderr-drain",
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
        measurement_deadline = min(
            operation_started + measurement_timeout,
            overall_deadline - FINALIZATION_RESERVE_SECONDS,
        )
        while process.poll() is None and time.monotonic() < measurement_deadline:
            if use_stdin and ready_path.is_file() and process.stdin is not None:
                process.stdin.close()
                stdin_closed_after_ready_or_timeout = True
            time.sleep(min(0.05, max(0.001, measurement_deadline - time.monotonic())))
        if process.poll() is None:
            timed_out = True
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
                stdin_closed_after_ready_or_timeout = True
            process.terminate()
            terminate_sent = True
            terminate_wait = min(
                OWNED_PROCESS_TERMINATE_GRACE_SECONDS,
                max(0.05, remaining_seconds() - REPORT_WRITE_RESERVE_SECONDS),
            )
            if not _bounded_wait(process, terminate_wait):
                process.kill()
                kill_sent = True
                kill_wait = min(
                    OWNED_PROCESS_KILL_GRACE_SECONDS,
                    max(0.05, remaining_seconds() - REPORT_WRITE_RESERVE_SECONDS),
                )
                _bounded_wait(process, kill_wait)
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    except Exception as exc:
        spawn_error = f"{type(exc).__name__}: {exc}"
        if process is not None and process.poll() is None:
            process.kill()
            kill_sent = True
            kill_wait = min(
                OWNED_PROCESS_KILL_GRACE_SECONDS,
                max(0.05, remaining_seconds() - REPORT_WRITE_RESERVE_SECONDS),
            )
            _bounded_wait(process, kill_wait)
    finally:
        if direct_stderr is not None:
            direct_stderr.close()
    for thread, metrics, label in (
        (stdout_thread, stdout_metrics, "stdout"),
        (stderr_thread, stderr_metrics, "stderr"),
    ):
        _safe_join_drain(
            thread,
            timeout_seconds=min(
                DRAIN_JOIN_SECONDS,
                max(0.0, remaining_seconds() - REPORT_WRITE_RESERVE_SECONDS),
            ),
            metrics=metrics,
            label=label,
        )
    drains_alive = [
        thread.name
        for thread in (stdout_thread, stderr_thread)
        if thread is not None and thread.is_alive()
    ]
    if drains_alive and process is not None:
        for stream in (process.stdout, process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        for thread, metrics, label in (
            (stdout_thread, stdout_metrics, "stdout"),
            (stderr_thread, stderr_metrics, "stderr"),
        ):
            if thread is not None and thread.is_alive():
                _safe_join_drain(
                    thread,
                    timeout_seconds=min(
                        1.0,
                        max(0.0, remaining_seconds() - REPORT_WRITE_RESERVE_SECONDS),
                    ),
                    metrics=metrics,
                    label=label,
                )
        drains_alive = [
            thread.name
            for thread in (stdout_thread, stderr_thread)
            if thread is not None and thread.is_alive()
        ]
    drain_errors = {
        key: value
        for key, value in {**stdout_metrics, **stderr_metrics}.items()
        if key.endswith("_drain_error")
    }
    drains_finalized = not drains_alive and not drain_errors
    owned_child_exited = process is not None and process.poll() is not None
    child_result, result_evidence = _safe_child_result(
        result_path,
        ready_path,
        expected_arm=arm,
        expected_component_spec=ARM_SPECS[arm],
        expected_candidate_hashes=dependency.EXPECTED_CANDIDATE_HASHES,
        expected_authorization_sha256=marker_hash,
        expected_launch_binding_sha256=launch_binding_hash or "",
    )
    outcomes = _child_outcomes(child_result if result_evidence["trusted_complete"] else None)
    candidate_hashes_after = dependency.exact_candidate_hashes()
    candidate_unchanged = candidate_hashes_after == dependency.EXPECTED_CANDIDATE_HASHES

    def stable_artifact(path: Path) -> dict[str, Any] | None:
        if (
            not path.is_file()
            or not drains_finalized
            or not owned_child_exited
            or remaining_seconds() <= REPORT_WRITE_RESERVE_SECONDS
        ):
            return None
        return {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    child_result_artifact = stable_artifact(result_path)
    child_ready_artifact = stable_artifact(ready_path)
    launch_binding_artifact = stable_artifact(launch_binding_path)
    stderr_artifact = stable_artifact(stderr_path)
    phase_journal_artifact = stable_artifact(phase_path)
    wall_seconds = round(time.monotonic() - run_started, 9)
    wall_bound_exceeded = wall_seconds > total_timeout
    deadline_remaining_before_report_write = remaining_seconds()
    stdin_contract_passed = (not use_stdin) or stdin_closed_after_ready_or_timeout
    expected_transport_artifacts_present = (
        stderr_artifact is not None
        and child_result_artifact is not None
        and child_ready_artifact is not None
        and launch_binding_artifact is not None
        and launch_binding_artifact.get("sha256") == launch_binding_hash
        and ((not use_pipe_bundle) or phase_journal_artifact is not None)
    )
    drain_metrics_complete = (not use_pipe_bundle) or (
        isinstance(stdout_metrics.get("stdout_lines"), int)
        and isinstance(stdout_metrics.get("phase_journal_fsync_calls"), int)
        and isinstance(stderr_metrics.get("stderr_bytes"), int)
    )
    success_gate = {
        "not_timed_out": timed_out is False,
        "no_spawn_error": spawn_error is None,
        "trusted_semantic_result": result_evidence["trusted_complete"] is True,
        "child_declared_pass": isinstance(child_result, dict)
        and child_result.get("passed") is True,
        "exact_torch_import_only": outcomes["torch_import_only"] is True,
        "outcome_evidence_complete": outcomes["evidence_complete"] is True,
        "owned_child_exit_zero": owned_child_exited
        and process is not None
        and process.returncode == 0,
        "stdin_contract_passed": stdin_contract_passed,
        "drains_finalized_without_error": drains_finalized,
        "drain_metrics_complete": drain_metrics_complete,
        "expected_transport_artifacts_present": expected_transport_artifacts_present,
        "candidate_unchanged": candidate_unchanged,
        "wall_bound_not_exceeded": not wall_bound_exceeded,
        "report_write_reserve_present": deadline_remaining_before_report_write
        >= REPORT_WRITE_RESERVE_SECONDS,
    }
    completed_import_only = all(success_gate.values())
    report = {
        "schema_version": 3,
        "artifact_kind": "blackwell_import_component_isolation_v3_report",
        "status": (
            "completed_import_only"
            if completed_import_only
            else "bounded_timeout_preserved"
            if timed_out
            else "failed_preserved"
        ),
        "arm": arm,
        "component_spec": ARM_SPECS[arm],
        "rejected_probe_binding": {
            "path": relative(REJECTED_PROBE_PATH),
            "sha256": REJECTED_PROBE_SHA256,
            "status": "REJECTED_STATIC_EVIDENCE_DO_NOT_RUN",
        },
        "sealed_v2_predecessor": {
            "path": relative(PREDECESSOR_V2_PATH),
            "sha256": PREDECESSOR_V2_SHA256,
        },
        "redirector_microdiagnostic": {
            "path": relative(REDIRECTOR_EVIDENCE_PATH),
            "sha256": REDIRECTOR_EVIDENCE_SHA256,
        },
        "controller_process_identity": controller_identity,
        "tool_sha256": tool_hash,
        "failed_evidence": failed_evidence,
        "independent_defender_state": "UNKNOWN_PENDING_INDEPENDENT_CAPTURE",
        "total_timeout_seconds": total_timeout,
        "import_measurement_timeout_seconds": measurement_timeout,
        "observed_wall_seconds": wall_seconds,
        "wall_bound_exceeded": wall_bound_exceeded,
        "deadline_remaining_before_report_write_seconds": round(
            deadline_remaining_before_report_write, 9
        ),
        "success_gate": success_gate,
        "timed_out": timed_out,
        "spawn_error": spawn_error,
        "owned_child_pid": process.pid if process is not None else None,
        "owned_child_exit_code": process.returncode if process is not None else None,
        "owned_child_exit_observed": owned_child_exited,
        "owned_child_terminate_sent": terminate_sent,
        "owned_child_kill_sent": kill_sent,
        "stdin_closed_only_after_ready_or_timeout": (
            (not use_stdin) or stdin_closed_after_ready_or_timeout
        ),
        "drains_finalized": drains_finalized,
        "drains_alive": drains_alive,
        "drain_errors": drain_errors,
        "parent_pipe_metrics": {
            **stdout_metrics,
            **stderr_metrics,
            "bundle_enabled": use_pipe_bundle,
            "bundle_scope": (
                "serialization_flush_pipe_stdout_stderr_drains_file_writes_stdout_fsync"
                if use_pipe_bundle
                else "none"
            ),
        },
        "child_result_evidence": result_evidence,
        "child_outcomes": outcomes,
        "child_result_artifact": child_result_artifact,
        "child_ready_artifact": child_ready_artifact,
        "launch_binding_artifact": launch_binding_artifact,
        "stderr_artifact": stderr_artifact,
        "phase_journal_artifact": phase_journal_artifact,
        "candidate_hashes_after": candidate_hashes_after,
        "candidate_unchanged": candidate_unchanged,
        "harness_actions": {
            "defender_queried": False,
            "defender_changed": False,
            "elevation_invoked": False,
            "cuda_api_call_present": False,
            "model_load_path_present": False,
            "audio_or_playback_path_present": False,
            "ollama_or_kira_path_present": False,
            "blender_started": False,
            "candidate_promoted": False,
            "production_routing_changed": False,
        },
        "causal_conclusion_claimed": False,
    }
    write_json_exclusive(report_path, report)
    return report_path, report


def describe() -> dict[str, Any]:
    return {
        "schema_version": 3,
        "artifact_kind": "blackwell_import_component_isolation_v3_description",
        "status": "WINDOWS_LINEAGE_HARDENED_STATIC_REVISION_PREPARED_NOT_EXECUTED",
        "sealed_v2_predecessor": {
            "path": relative(PREDECESSOR_V2_PATH),
            "sha256": PREDECESSOR_V2_SHA256,
        },
        "redirector_microdiagnostic": {
            "path": relative(REDIRECTOR_EVIDENCE_PATH),
            "sha256": REDIRECTOR_EVIDENCE_SHA256,
        },
        "accepted_windows_lineage_depth": "direct_or_exactly_one_popen_redirector",
        "launch_process_identity_binding": "pid_creation_time_and_executable_path",
        "rejected_predecessor": {
            "path": relative(REJECTED_PROBE_PATH),
            "sha256": REJECTED_PROBE_SHA256,
            "status": "REJECTED_STATIC_EVIDENCE_DO_NOT_RUN",
        },
        "arms": ARM_SPECS,
        "one_arm_per_invocation": True,
        "maximum_total_timeout_seconds": MAX_TOTAL_TIMEOUT_SECONDS,
        "maximum_import_measurement_seconds": MAX_IMPORT_MEASUREMENT_SECONDS,
        "child_self_exit_cap_seconds": (
            MAX_IMPORT_MEASUREMENT_SECONDS + CHILD_SELF_EXIT_GRACE_SECONDS
        ),
        "blackwell_runtime_started": False,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "defender_queried": False,
        "defender_changed": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
    }


def static_self_check() -> dict[str, Any]:
    dependency = _load_rejected_dependency()
    source = Path(__file__).read_text(encoding="utf-8")
    child_source = source[source.index("\ndef child_arm_v3") : source.index("\ndef _drain_stdout")]
    direct = classify_windows_launch_lineage(
        controller_pid=10,
        popen_launch_pid=20,
        executing_child_pid=20,
        executing_child_parent_pid=10,
    )
    redirected = classify_windows_launch_lineage(
        controller_pid=10,
        popen_launch_pid=20,
        executing_child_pid=30,
        executing_child_parent_pid=20,
    )
    spoofed = classify_windows_launch_lineage(
        controller_pid=10,
        popen_launch_pid=99,
        executing_child_pid=30,
        executing_child_parent_pid=20,
    )
    checks = {
        "sealed_v2_predecessor_exact": sha256_file(PREDECESSOR_V2_PATH)
        == PREDECESSOR_V2_SHA256,
        "redirector_microdiagnostic_exact": sha256_file(REDIRECTOR_EVIDENCE_PATH)
        == REDIRECTOR_EVIDENCE_SHA256,
        "rejected_predecessor_exact": sha256_file(REJECTED_PROBE_PATH)
        == REJECTED_PROBE_SHA256,
        "candidate_hashes_exact": dependency.exact_candidate_hashes()
        == dependency.EXPECTED_CANDIDATE_HASHES,
        "one_arm_only": ("for arm " + "in ARM_SPECS") not in source,
        "run_function_clamps_internally": "bounded_timeouts(" in source
        and "requested_total_timeout_seconds" in source,
        "total_timeout_cap_180": MAX_TOTAL_TIMEOUT_SECONDS == 180.0,
        "measurement_timeout_cap_120": MAX_IMPORT_MEASUREMENT_SECONDS == 120.0,
        "whole_run_deadline_starts_at_entry": "run_started = time.monotonic()" in source,
        "child_live_blender_recheck": "child no-active-Blender gate failed" in child_source,
        "semantic_result_binding": "child result semantic binding failed" in source,
        "success_requires_exact_import_only": '"exact_torch_import_only"' in source,
        "child_self_exit_present": "os._exit(124)" in source,
        "faulthandler_repeats_every_30s": "dump_traceback_later(30.0, repeat=True"
        in child_source,
        "child_parent_record_gate": "_validate_child_authorization(" in child_source,
        "direct_windows_lineage_accepted": direct["passed"] is True
        and direct["lineage_kind"] == "DIRECT_POPEN_CHILD",
        "one_redirector_lineage_accepted": redirected["passed"] is True
        and redirected["lineage_kind"] == "ONE_WINDOWS_VENV_REDIRECTOR",
        "unrelated_lineage_rejected": spoofed["passed"] is False,
        "launch_binding_nonce_hmac": "_launch_binding_hmac(" in source,
        "live_controller_identity": "controller_still_live_and_exact" in source,
        "live_launch_process_identity": "launch_process_still_live_and_exact" in source,
        "atomic_ready_marker": "CHILD_RESULT_READY.json" in source,
        "safe_partial_result_parser": "_safe_child_result(" in source,
        "drain_liveness_checked_before_hash": "drains_finalized" in source,
        "timeout_outcomes_tri_state": "{key: None for key in keys}" in source,
        "pipe_bundle_labeled": "pipe_drains_phase_fsync_bundle" in ARM_SPECS,
        "torch_import_only_boundary": 'importlib.import_module("torch")' in child_source,
        "no_torch_cuda_call": "torch.cuda" not in child_source,
        "no_torchaudio_or_chatterbox_import": 'import_module("torchaudio")' not in child_source
        and 'import_module("chatterbox")' not in child_source,
        "no_model_factory": "from_pretrained(" not in child_source,
        "no_audio_playback": not any(
            marker in child_source
            for marker in ("winsound.PlaySound(", "sounddevice.play(", "sd.play(")
        ),
        "no_defender_mutation": not any(
            marker in source
            for marker in (
                "Add" + "-MpPreference",
                "Remove" + "-MpPreference",
                "Set" + "-MpPreference",
            )
        ),
        "no_elevation": ("run" + "as") not in source.casefold(),
        "no_promotion_route_functions": not any(
            marker in source
            for marker in (
                "promote_" + "candidate(",
                "activate_" + "candidate(",
                "set_production_" + "route(",
            )
        ),
    }
    return {
        "schema_version": 3,
        "artifact_kind": "blackwell_import_component_isolation_v3_static_self_check",
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
        "candidate_promoted": False,
        "production_routing_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--describe", action="store_true")
    group.add_argument("--static-self-check", action="store_true")
    group.add_argument("--run-arm", action="store_true")
    group.add_argument("--child-arm-v3", choices=tuple(ARM_SPECS), help=argparse.SUPPRESS)
    parser.add_argument("--arm", choices=tuple(ARM_SPECS))
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-tool-sha256", default="")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    parser.add_argument("--expected-failed-report-sha256", default="")
    parser.add_argument("--expected-post-failure-check-sha256", default="")
    parser.add_argument("--total-timeout-seconds", type=float, default=DEFAULT_TOTAL_TIMEOUT_SECONDS)
    parser.add_argument("--child-result-path", default="", help=argparse.SUPPRESS)
    parser.add_argument("--child-authorization-record", default="", help=argparse.SUPPRESS)
    parser.add_argument("--child-launch-binding", default="", help=argparse.SUPPRESS)
    parser.add_argument(
        "--expected-child-authorization-sha256",
        default="",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--child-timeout-seconds", type=float, default=0.0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child_arm_v3:
        return child_arm_v3(
            arm=args.child_arm_v3,
            result_path_value=args.child_result_path,
            authorization_path_value=args.child_authorization_record,
            expected_authorization_sha256=args.expected_child_authorization_sha256,
            launch_binding_path_value=args.child_launch_binding,
            measurement_timeout_seconds=args.child_timeout_seconds,
        )
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
    report_path, report = run_one_arm_v3(
        arm=args.arm,
        expected_tool_sha256=args.expected_tool_sha256,
        expected_candidate_config_sha256=args.expected_candidate_config_sha256,
        expected_failed_report_sha256=args.expected_failed_report_sha256,
        expected_post_failure_check_sha256=args.expected_post_failure_check_sha256,
        requested_total_timeout_seconds=args.total_timeout_seconds,
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "status": report["status"],
                "arm": report["arm"],
                "timed_out": report["timed_out"],
                "child_outcomes": report["child_outcomes"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "completed_import_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())
