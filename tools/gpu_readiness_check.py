"""Post-install GPU readiness check for Kira.

Run this after installing an NVIDIA GPU and driver. It is intentionally safe:
it checks Windows/NVIDIA/Ollama visibility, runs a tiny local model prompt when
available, and writes a timestamped report for later review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.model_request_policy import ordinary_model_request_fields


REPORT_DIR = PROJECT_ROOT / "Data" / "hardware" / "gpu_readiness"
DEFAULT_MODEL = "qwen3.5:9b"
DEFAULT_MODEL_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
OLLAMA_CHAT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_ENDPOINT = "http://127.0.0.1:11434/api/tags"
MAX_OLLAMA_RESPONSE_BYTES = 8 * 1024 * 1024
OLLAMA_EXE = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "command": command,
        }
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"{command[0]} not found", "command": command}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": "command timed out", "command": command}


def find_nvidia_smi() -> str | None:
    found = shutil.which("nvidia-smi")
    if found:
        return found
    common = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"
    return str(common) if common.exists() else None


def parse_gpu_query(output: str) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            memory_total_mb = int(float(parts[2]))
            memory_used_mb = int(float(parts[3]))
        except ValueError:
            memory_total_mb = 0
            memory_used_mb = 0
        gpus.append(
            {
                "name": parts[0],
                "driver_version": parts[1],
                "memory_total_mb": memory_total_mb,
                "memory_used_mb": memory_used_mb,
                "temperature_c": parts[4],
            }
        )
    return gpus


def check_nvidia_smi() -> dict[str, Any]:
    nvidia_smi = find_nvidia_smi()
    if not nvidia_smi:
        return {"ok": False, "detail": "nvidia-smi not found. Install/reinstall the NVIDIA driver after the GPU is installed.", "gpus": []}
    query = run_command(
        [
            nvidia_smi,
            "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu",
            "--format=csv,noheader,nounits",
        ],
        timeout=15,
    )
    gpus = parse_gpu_query(query.get("stdout", ""))
    return {
        "ok": bool(query["ok"] and gpus),
        "detail": query.get("stderr") or query.get("stdout") or "nvidia-smi returned no GPU rows",
        "nvidia_smi": nvidia_smi,
        "raw": query,
        "gpus": gpus,
    }


def check_ollama_installed() -> dict[str, Any]:
    path = shutil.which("ollama") or (str(OLLAMA_EXE) if OLLAMA_EXE.exists() else "")
    if not path:
        return {"ok": False, "detail": "ollama command not found"}
    version = run_command([path, "--version"], timeout=20)
    return {"ok": version["ok"], "path": path, "detail": version["stdout"] or version["stderr"]}


def check_ollama_models() -> dict[str, Any]:
    path = shutil.which("ollama") or (str(OLLAMA_EXE) if OLLAMA_EXE.exists() else "")
    if not path:
        return {"ok": False, "detail": "ollama command not found", "models": []}
    listed = run_command([path, "list"], timeout=30)
    models = []
    for line in listed.get("stdout", "").splitlines()[1:]:
        name = line.split()[0] if line.split() else ""
        if name:
            models.append(name)
    return {"ok": listed["ok"], "detail": listed["stdout"] or listed["stderr"], "models": models}


def _read_bounded_json(response: Any) -> dict[str, Any]:
    raw = response.read(MAX_OLLAMA_RESPONSE_BYTES + 1)
    if len(raw) > MAX_OLLAMA_RESPONSE_BYTES:
        raise ValueError("Ollama response exceeded the bounded size")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Ollama response was not a JSON object")
    return parsed


def check_exact_ollama_model_identity(
    model: str = DEFAULT_MODEL,
    digest: str = DEFAULT_MODEL_DIGEST,
    timeout: int = 10,
) -> dict[str, Any]:
    """Verify the exact Qwen name and digest without loading any model."""

    if model != DEFAULT_MODEL or digest.casefold() != DEFAULT_MODEL_DIGEST:
        return {
            "ok": False,
            "model": model,
            "expected_digest": digest,
            "detail": "GPU readiness is pinned to the exact approved Qwen 3.5 model",
        }
    request = urllib.request.Request(
        OLLAMA_TAGS_ENDPOINT,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = _read_bounded_json(response)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        return {
            "ok": False,
            "model": model,
            "expected_digest": digest,
            "detail": f"exact model identity check failed: {type(exc).__name__}",
        }
    records = []
    for item in payload.get("models") or []:
        if not isinstance(item, dict):
            continue
        identifiers = {
            str(item.get(key) or "").strip()
            for key in ("name", "model")
            if str(item.get(key) or "").strip()
        }
        if model in identifiers:
            records.append(item)
    observed_digest = (
        str(records[0].get("digest") or "").strip().casefold()
        if len(records) == 1
        else ""
    )
    ok = len(records) == 1 and observed_digest == digest.casefold()
    return {
        "ok": ok,
        "model": model,
        "expected_digest": digest.casefold(),
        "observed_digest": observed_digest,
        "matching_record_count": len(records),
        "detail": (
            "exact Qwen 3.5 name and digest verified"
            if ok
            else "exact Qwen 3.5 name/digest record was absent, duplicated, or mismatched"
        ),
    }


def run_ollama_probe(model: str, timeout: int) -> dict[str, Any]:
    if model != DEFAULT_MODEL:
        return {
            "ok": False,
            "model": model,
            "detail": "model probe blocked because the requested model is not exact Qwen 3.5",
        }
    prompt = "Reply with exactly: Kira GPU probe OK"
    request_fields = ordinary_model_request_fields(model, keep_alive=0)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 24},
        **request_fields,
    }
    request = urllib.request.Request(
        OLLAMA_CHAT_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = _read_bounded_json(response)
        response_model = str(response_payload.get("model") or "").strip()
        message = response_payload.get("message")
        text = str(message.get("content") or "").strip() if isinstance(message, dict) else ""
        error = ""
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        response_payload = {}
        response_model = ""
        text = ""
        error = type(exc).__name__
    elapsed = time.perf_counter() - started
    ok = bool(
        not error
        and response_model == model
        and response_payload.get("done") is True
        and re.search(r"kira\s+gpu\s+probe\s+ok", text, re.IGNORECASE)
    )
    return {
        "ok": ok,
        "elapsed_seconds": round(elapsed, 2),
        "model": model,
        "response_model": response_model,
        "think": request_fields.get("think"),
        "keep_alive": request_fields.get("keep_alive"),
        "stdout": text[-1000:],
        "stderr": error,
        "detail": "exact non-thinking model replied" if ok else "exact model probe did not return expected text",
    }


def check_ollama_gpu_processes() -> dict[str, Any]:
    nvidia_smi = find_nvidia_smi()
    if not nvidia_smi:
        return {"ok": False, "detail": "nvidia-smi not found"}
    result = run_command(
        [
            nvidia_smi,
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        timeout=15,
    )
    rows = [line.strip() for line in result.get("stdout", "").splitlines() if line.strip()]
    ollama_rows = [row for row in rows if "ollama" in row.lower()]
    return {
        "ok": bool(ollama_rows),
        "detail": "Ollama GPU process detected" if ollama_rows else "No Ollama GPU process detected at check time",
        "all_compute_rows": rows,
        "ollama_rows": ollama_rows,
    }


def build_report(model: str, run_probe: bool, timeout: int) -> dict[str, Any]:
    nvidia = check_nvidia_smi()
    ollama = check_ollama_installed()
    models = check_ollama_models()
    identity = check_exact_ollama_model_identity(model, DEFAULT_MODEL_DIGEST)
    if run_probe and identity.get("ok") is True:
        probe = run_ollama_probe(model, timeout)
    elif run_probe:
        probe = {
            "ok": False,
            "model": model,
            "detail": "model probe blocked because exact Qwen name/digest was not verified",
        }
    else:
        probe = {"ok": None, "detail": "probe skipped"}
    gpu_processes = check_ollama_gpu_processes() if run_probe else {"ok": None, "detail": "probe skipped"}
    total_vram_gb = 0.0
    if nvidia.get("gpus"):
        total_vram_gb = max(gpu.get("memory_total_mb", 0) for gpu in nvidia["gpus"]) / 1024
    suggested_stage = "stage_16gb_gpu_bridge" if total_vram_gb >= 11 else "stage_16gb_setup"
    if total_vram_gb >= 11:
        guidance = [
            "Good bridge GPU detected. Use one local model at a time until RAM is upgraded.",
            "Try Kira chat and short life/school tests before longer sessions.",
            "Expect 12GB VRAM to help speed/CPU heat, but still avoid multiple AIs or heavy 3D world runtime.",
        ]
    else:
        guidance = [
            "GPU was not detected yet. Install driver/card, reboot, then rerun this check.",
            "Keep using short CPU/RAM-safe tests until nvidia-smi sees the GPU.",
        ]
    return {
        "report_id": f"gpu_readiness_{now_id()}",
        "created_at": utc_now(),
        "model": model,
        "model_digest": DEFAULT_MODEL_DIGEST,
        "nvidia": nvidia,
        "ollama": ollama,
        "ollama_models": models,
        "ollama_model_identity": identity,
        "ollama_probe": probe,
        "ollama_gpu_processes": gpu_processes,
        "detected_vram_gb": round(total_vram_gb, 2),
        "suggested_stage": suggested_stage,
        "guidance": guidance,
    }


def print_report(report: dict[str, Any]) -> None:
    print("Kira GPU readiness check")
    print("=" * 24)
    print(f"Report: {report['report_id']}")
    print(f"Detected VRAM: {report['detected_vram_gb']} GB")
    print(f"Suggested stage: {report['suggested_stage']}")
    for gpu in report["nvidia"].get("gpus", []):
        used = gpu.get("memory_used_mb", 0) / 1024
        total = gpu.get("memory_total_mb", 0) / 1024
        print(f"GPU: {gpu.get('name')} driver={gpu.get('driver_version')} VRAM={used:.1f}/{total:.1f} GB temp={gpu.get('temperature_c')}C")
    print(f"NVIDIA: {'PASS' if report['nvidia'].get('ok') else 'FAIL'} - {report['nvidia'].get('detail')}")
    print(f"Ollama: {'PASS' if report['ollama'].get('ok') else 'FAIL'} - {report['ollama'].get('detail')}")
    print(
        "Exact Qwen identity: "
        f"{'PASS' if report['ollama_model_identity'].get('ok') else 'FAIL'} - "
        f"{report['ollama_model_identity'].get('detail')}"
    )
    print(f"Model probe: {report['ollama_probe'].get('ok')} - {report['ollama_probe'].get('detail')}")
    print(f"Ollama GPU process: {report['ollama_gpu_processes'].get('ok')} - {report['ollama_gpu_processes'].get('detail')}")
    print("\nGuidance:")
    for item in report["guidance"]:
        print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check NVIDIA GPU and Ollama readiness for Kira.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--probe", action="store_true", help="Run one tiny Ollama model prompt.")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.model != DEFAULT_MODEL:
        parser.error(f"--model must be the exact authorized model: {DEFAULT_MODEL}")

    report = build_report(args.model, args.probe, args.timeout)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{report['report_id']}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)
        print(f"\nSaved: {report_path.relative_to(PROJECT_ROOT).as_posix()}")

    if not report["nvidia"].get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
