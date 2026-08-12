"""Bounded Kira mind/body plus legal-spa resource smoke test.

This deliberately does not mutate the live shell state, Home World, or the strip
mall.  It loads the current Home World in an isolated browser, injects Kira's
current 3D body into that page, loads the code-pinned spa in a second page, and may
briefly load Kira's configured Ollama model.  It is short evidence, not a
several-hour stability certification.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from serve_legal_day_spa_notebook_world import (
        bind_server as bind_pinned_spa_server,
        verify_pinned_build as verify_pinned_spa_build,
    )
except ModuleNotFoundError:  # Imported as tools.kira_spa_resource_smoke.
    from tools.serve_legal_day_spa_notebook_world import (
        bind_server as bind_pinned_spa_server,
        verify_pinned_build as verify_pinned_spa_build,
    )


ROOT = Path(__file__).resolve().parents[1]
HARDWARE_PROFILE = ROOT / "Data" / "launch" / "hardware_capability_profile.json"
SPA_PROJECT = ROOT / "Data" / "world_builder" / "projects" / "legal_day_spa_avatar_builder_spa_20260714"
HOME_PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "home_world"
    / "builds"
    / "home_world_main_house_20260630_223000"
    / "preview"
)
BROWSER_HELPER = ROOT / "tools" / "kira_spa_resource_browser_smoke.mjs"
DEFAULT_REPORT = SPA_PROJECT / "resource_tests" / "kira_spa_resource_smoke_latest.json"
MODEL = "qwen3.5:9b"
MODEL_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected an object in {path}")
    return data


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load_percent", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def system_memory() -> dict[str, float]:
    status = _MemoryStatus()
    status.length = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    gb = 1024**3
    used = status.total_physical - status.available_physical
    return {
        "total_gb": round(status.total_physical / gb, 3),
        "used_gb": round(used / gb, 3),
        "available_gb": round(status.available_physical / gb, 3),
        "load_percent": float(status.memory_load_percent),
    }


def gpu_sample() -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        line = subprocess.run(command, check=True, capture_output=True, text=True, timeout=15).stdout.strip().splitlines()[0]
        name, total, used, free, utilization = [item.strip() for item in line.split(",")]
        return {
            "available": True,
            "name": name,
            "total_mb": int(total),
            "used_mb": int(used),
            "free_mb": int(free),
            "utilization_percent": int(utilization),
        }
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, IndexError):
        return {"available": False}


def process_snapshot() -> dict[int, dict[str, Any]]:
    script = (
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,WorkingSetSize,PrivatePageCount "
        "| ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    raw = json.loads(completed.stdout)
    rows = raw if isinstance(raw, list) else [raw]
    result: dict[int, dict[str, Any]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        pid = int(item.get("ProcessId") or 0)
        result[pid] = {
            "pid": pid,
            "parent_pid": int(item.get("ParentProcessId") or 0),
            "name": str(item.get("Name") or ""),
            "working_set_bytes": int(item.get("WorkingSetSize") or 0),
            "private_bytes": int(item.get("PrivatePageCount") or 0),
        }
    return result


def descendants(snapshot: dict[int, dict[str, Any]], roots: set[int]) -> list[dict[str, Any]]:
    selected = set(roots)
    changed = True
    while changed:
        changed = False
        for pid, item in snapshot.items():
            if pid not in selected and item["parent_pid"] in selected:
                selected.add(pid)
                changed = True
    return [snapshot[pid] for pid in sorted(selected) if pid in snapshot]


def process_totals(items: list[dict[str, Any]]) -> dict[str, Any]:
    mb = 1024**2
    return {
        "process_count": len(items),
        "working_set_mb": round(sum(item["working_set_bytes"] for item in items) / mb, 2),
        "private_mb": round(sum(item["private_bytes"] for item in items) / mb, 2),
        "processes": [
            {
                "pid": item["pid"],
                "parent_pid": item["parent_pid"],
                "name": item["name"],
                "working_set_mb": round(item["working_set_bytes"] / mb, 2),
                "private_mb": round(item["private_bytes"] / mb, 2),
            }
            for item in sorted(items, key=lambda row: row["working_set_bytes"], reverse=True)
        ],
    }


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_url(url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {url}: {last_error}")


def ollama_post(payload: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data if isinstance(data, dict) else {}


def ollama_loaded_models() -> list[str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [str(item.get("name") or "") for item in data.get("models", []) if isinstance(item, dict)]
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return []


def require_exact_qwen35_installed() -> None:
    """Fail before the optional smoke inference if the exact digest is absent."""

    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    matches = [
        item
        for item in data.get("models", [])
        if isinstance(item, dict) and str(item.get("name") or "") == MODEL
    ]
    if len(matches) != 1 or str(matches[0].get("digest") or "").casefold() != MODEL_DIGEST:
        raise RuntimeError("exact approved qwen3.5:9b digest is not installed")


def stop_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def evaluate_placement_decision(
    hardware_profile: dict[str, Any],
    spa_gate: dict[str, Any],
    smoke_status: str,
    minimum_available_gb: float | None,
) -> dict[str, Any]:
    observed = hardware_profile.get("known_build", {}).get("current_observed_ram", {})
    capacity_gb = int(observed.get("capacity_gb") or 0)
    stage_id = str(hardware_profile.get("current_planned_stage") or "")
    stages = {
        str(item.get("stage_id") or ""): item
        for item in hardware_profile.get("capability_stages", [])
        if isinstance(item, dict)
    }
    current_stage = stages.get(stage_id, {})
    blocked = {str(item) for item in current_stage.get("blocked_work", [])}
    reasons: list[str] = []
    if capacity_gb < 64:
        reasons.append(f"Observed RAM is {capacity_gb}GB; the established heavy world/runtime gate is 64GB.")
    if "3d_home_runtime_as_lived_world" in blocked:
        reasons.append(f"Current hardware stage {stage_id} blocks 3D Home World as a lived world.")
    if spa_gate.get("status") != "approved":
        reasons.append(f"Spa approval status is {spa_gate.get('status', 'unknown')}, not approved.")
    if spa_gate.get("runtime_kira_route_test") != "passed":
        reasons.append("The runtime Kira route test has not passed.")
    if spa_gate.get("visual_realism_review") != "passed":
        reasons.append("The visual-realism gate has not passed.")
    if spa_gate.get("robert_approval") not in {"approved", "granted"}:
        reasons.append("Robert's explicit visual approval is not recorded.")
    if smoke_status != "passed_bounded_combined_smoke":
        reasons.append("The bounded combined resource smoke did not fully pass.")
    else:
        reasons.append("A bounded resource smoke cannot certify Robert's several-hour lived-world sessions or rule out a slow leak.")
    if minimum_available_gb is not None and minimum_available_gb < 8:
        reasons.append(f"Available RAM fell below the 8GB short-smoke guardrail ({minimum_available_gb:.2f}GB).")
    return {
        "choice": "separate_notebook_world",
        "home_world_mutation_allowed": False,
        "strip_mall_deletion_allowed": False,
        "strip_mall_runtime_visibility": "empty_lot_default_owner_choice",
        "strip_mall_source_preserved": True,
        "strip_mall_restore_switch": "?stripMall=1",
        "spa_placed_on_former_strip_mall_site": False,
        "reasons": reasons,
        "reconsider_after": [
            "64GB RAM is installed and verified",
            "a supervised multi-hour Kira plus spa soak passes without lag, crash, or memory pressure",
            "the spa runtime Kira-route test passes",
            "the visual-realism and missing-prefab gates pass",
            "Robert explicitly approves the spa and its Home World placement",
        ],
    }


def resolve_pinned_spa_inputs():
    """Resolve the same code-pinned registration/build used by the scoped launcher."""
    pinned_spa = verify_pinned_spa_build()
    spa_folder = (ROOT / pinned_spa.entrypoint_relative_path).parent
    gate_paths = pinned_spa.role_paths.get("preview_approval_gate", ())
    if len(gate_paths) != 1:
        raise ValueError("Pinned spa build does not bind exactly one preview approval gate")
    spa_gate_path = gate_paths[0]
    return pinned_spa, spa_folder, spa_gate_path, read_json(spa_gate_path)


def run_smoke(duration_seconds: int, load_model: bool, report_path: Path) -> dict[str, Any]:
    hardware = read_json(HARDWARE_PROFILE)
    pinned_spa, spa_folder, spa_gate_path, spa_gate = resolve_pinned_spa_inputs()
    home_port = find_free_port()
    home_url = f"http://127.0.0.1:{home_port}/?area=home&resourceSmoke=1"
    run_dir = report_path.parent / f"run_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    ready_file = run_dir / "browser_ready.json"
    stop_file = run_dir / "stop_browser"
    home_log = (run_dir / "home_server.log").open("w", encoding="utf-8")
    browser_log = (run_dir / "browser.log").open("w", encoding="utf-8")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    processes: list[subprocess.Popen[Any]] = []
    model_was_loaded = MODEL in ollama_loaded_models()
    baseline = {"at": utc_now(), "system_memory": system_memory(), "gpu": gpu_sample()}
    browser_result: dict[str, Any] = {}
    samples: list[dict[str, Any]] = []
    smoke_status = "failed"
    spa_server = None
    spa_thread = None
    try:
        spa_server, spa_port = bind_pinned_spa_server(0)
        spa_thread = threading.Thread(target=spa_server.serve_forever, daemon=True)
        spa_thread.start()
        spa_url = f"http://127.0.0.1:{spa_port}/index.html"
        home_proc = subprocess.Popen(
            ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(home_port)],
            cwd=HOME_PREVIEW,
            stdout=home_log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        processes.append(home_proc)
        wait_url(home_url, timeout=60)
        wait_url(spa_url, timeout=30)
        browser_proc = subprocess.Popen(
            [
                "node",
                str(BROWSER_HELPER),
                "--home-url",
                home_url,
                "--spa-url",
                spa_url,
                "--ready-file",
                str(ready_file),
                "--stop-file",
                str(stop_file),
                "--max-seconds",
                "240",
            ],
            cwd=ROOT,
            stdout=browser_log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        processes.append(browser_proc)
        deadline = time.monotonic() + 150
        while not ready_file.exists() and time.monotonic() < deadline:
            if browser_proc.poll() is not None:
                raise RuntimeError(f"Browser helper exited early with code {browser_proc.returncode}")
            time.sleep(0.5)
        if not ready_file.exists():
            raise TimeoutError("Browser helper did not reach ready state")
        browser_result = read_json(ready_file)

        model_result: dict[str, Any] = {"requested": load_model, "already_loaded": model_was_loaded}
        if load_model:
            require_exact_qwen35_installed()
            started = time.monotonic()
            response = ollama_post(
                {
                    "model": MODEL,
                    "think": False,
                    "prompt": "Reply with only: OK",
                    "stream": False,
                    "keep_alive": "4m",
                    "options": {"num_predict": 4},
                }
            )
            model_result.update(
                {
                    "loaded": MODEL in ollama_loaded_models(),
                    "load_and_tiny_inference_seconds": round(time.monotonic() - started, 3),
                    "response_received": bool(response.get("done")),
                }
            )

        roots = {proc.pid for proc in processes}
        deadline = time.monotonic() + max(3, duration_seconds)
        while time.monotonic() < deadline:
            snapshot = process_snapshot()
            controlled = descendants(snapshot, roots)
            samples.append(
                {
                    "at": utc_now(),
                    "system_memory": system_memory(),
                    "gpu": gpu_sample(),
                    "controlled_processes": process_totals(controlled),
                    "ollama_loaded_models": ollama_loaded_models(),
                }
            )
            time.sleep(1)

        body_loaded = bool(browser_result.get("home", {}).get("active_avatar", {}).get("rootPresent"))
        spa_snapshot = browser_result.get("spa", {}).get("snapshot", {})
        spa_loaded = (
            spa_snapshot.get("status") == "loaded"
            or spa_snapshot.get("assetLoadState", {}).get("status") == "loaded"
        )
        processes_alive = all(proc.poll() is None for proc in processes)
        minimum_available = min(item["system_memory"]["available_gb"] for item in samples)
        smoke_status = (
            "passed_bounded_combined_smoke"
            if body_loaded and spa_loaded and processes_alive and minimum_available >= 8
            else "failed_bounded_combined_smoke"
        )
        peak_working = max(item["controlled_processes"]["working_set_mb"] for item in samples)
        peak_private = max(item["controlled_processes"]["private_mb"] for item in samples)
        peak_gpu = max((item["gpu"].get("used_mb", 0) for item in samples), default=0)
        peak_load = max(item["system_memory"]["load_percent"] for item in samples)
        measurements = {
            "sample_count": len(samples),
            "duration_seconds": duration_seconds,
            "minimum_available_ram_gb": minimum_available,
            "peak_additional_system_ram_used_from_baseline_gb": round(
                baseline["system_memory"]["available_gb"] - minimum_available,
                3,
            ),
            "peak_system_memory_load_percent": peak_load,
            "peak_controlled_working_set_mb": peak_working,
            "peak_controlled_private_mb": peak_private,
            "peak_gpu_memory_used_mb_whole_system": peak_gpu,
            "peak_additional_gpu_memory_used_from_baseline_mb": max(
                0,
                peak_gpu - int(baseline["gpu"].get("used_mb", 0)),
            ),
        }
        decision = evaluate_placement_decision(hardware, spa_gate, smoke_status, minimum_available)
        report = {
            "schema_version": 1,
            "created_at": utc_now(),
            "status": smoke_status,
            "scope": {
                "included": [
                    "current Home World Three.js source runtime",
                    "Kira's current 3D body loaded through the Home World debug injection path",
                    "code-pinned legal-spa preview and all five unique real-prefab sources",
                    "one tiny exact qwen3.5:9b inference" if load_model else "Ollama model load omitted",
                ],
                "excluded": [
                    "voice synthesis and microphone input",
                    "hours-long autonomous movement",
                    "spa Kira-route correctness",
                    "multiple synthetic people",
                    "proof against slow memory leaks, thermal throttling, or long-session crashes",
                ],
                "truth_note": "A short pass can reject an unsafe combination, but cannot certify a several-hour lived-world session.",
            },
            "inputs": {
                "hardware_profile": rel(HARDWARE_PROFILE),
                "home_preview": rel(HOME_PREVIEW),
                "spa_preview": rel(spa_folder),
                "spa_gate": rel(spa_gate_path),
                "spa_build_manifest": rel(pinned_spa.manifest_path),
                "spa_build_manifest_sha256": pinned_spa.manifest_sha256,
                "spa_registration": rel(pinned_spa.registration_path),
                "spa_registration_sha256": pinned_spa.registration_sha256,
                "spa_index_anchor_sha256": pinned_spa.index_anchor_sha256,
                "model": MODEL if load_model else None,
            },
            "baseline": baseline,
            "model": model_result,
            "browser": browser_result,
            "measurements": measurements,
            "decision": decision,
            "strip_mall": {
                "source_deleted": False,
                "runtime_visible_by_default": False,
                "restore_switch": "?stripMall=1",
                "spa_placed_here": False,
            },
            "home_world": {"modified": False},
            "raw_samples": samples,
            "run_artifacts": {"folder": rel(run_dir)},
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        try:
            stop_file.write_text("stop\n", encoding="utf-8")
        except OSError:
            pass
        for process in reversed(processes):
            stop_tree(process)
        if spa_server is not None:
            spa_server.shutdown()
            spa_server.server_close()
        if spa_thread is not None:
            spa_thread.join(timeout=5)
        if load_model and not model_was_loaded:
            try:
                ollama_post(
                    {"model": MODEL, "prompt": "", "stream": False, "think": False, "keep_alive": 0},
                    timeout=30,
                )
            except (OSError, urllib.error.URLError):
                pass
        home_log.close()
        browser_log.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=int, default=12)
    parser.add_argument("--load-kira-model", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_smoke(max(3, args.duration_seconds), args.load_kira_model, args.report.resolve())
    print(json.dumps({"status": report["status"], "decision": report["decision"], "report": rel(args.report.resolve())}, indent=2))
    return 0 if report["status"] == "passed_bounded_combined_smoke" else 1


if __name__ == "__main__":
    raise SystemExit(main())
