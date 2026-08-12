#!/usr/bin/env python3
"""Record the immutable pre-install baseline for the Blackwell voice sidecar."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CPU_SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_py311"
CPU_PYTHON = CPU_SIDECAR / ".venv" / "Scripts" / "python.exe"
TARGET = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_gpu"
EVIDENCE = TARGET / "evidence"
SNAPSHOT = EVIDENCE / "preinstall_system_snapshot.json"
SNAPSHOT_HASH = EVIDENCE / "preinstall_system_snapshot.sha256"
PROFILE = ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
REFERENCE = (
    ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=True,
    )


def nvidia_snapshot() -> dict[str, object]:
    full = run(["nvidia-smi"]).stdout
    query_fields = "name,memory.total,memory.free,memory.used,driver_version,compute_cap"
    query = run(
        [
            "nvidia-smi",
            f"--query-gpu={query_fields}",
            "--format=csv,noheader,nounits",
        ]
    ).stdout.strip().splitlines()
    if len(query) != 1:
        raise RuntimeError(f"expected exactly one GPU row, got {len(query)}")
    values = [value.strip() for value in query[0].split(",")]
    if len(values) != 6:
        raise RuntimeError("unexpected nvidia-smi query shape")
    cuda_match = re.search(r"CUDA UMD Version:\s*([0-9.]+)", full)
    if not cuda_match:
        cuda_match = re.search(r"CUDA Version:\s*([0-9.]+)", full)
    if not cuda_match:
        raise RuntimeError("driver-supported CUDA level not found")
    return {
        "name": values[0],
        "memory_total_mib": int(values[1]),
        "memory_free_mib": int(values[2]),
        "memory_used_mib": int(values[3]),
        "driver_version": values[4],
        "compute_capability": values[5],
        "driver_supported_cuda": cuda_match.group(1),
        "nvidia_smi_sha256": hashlib.sha256(full.encode("utf-8")).hexdigest(),
    }


class MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def memory_snapshot() -> dict[str, object]:
    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    mib = 1024 * 1024
    return {
        "total_physical_mib": round(status.ullTotalPhys / mib, 1),
        "free_physical_mib": round(status.ullAvailPhys / mib, 1),
        "memory_load_percent": int(status.dwMemoryLoad),
    }


def cpu_sidecar_snapshot() -> dict[str, object]:
    if not CPU_PYTHON.is_file():
        raise FileNotFoundError(f"accepted CPU sidecar Python missing: {CPU_PYTHON}")
    records: list[dict[str, object]] = []
    for path in sorted(CPU_SIDECAR.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if ".venv" in path.parts or not path.is_file():
            continue
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    freeze = run([str(CPU_PYTHON), "-m", "pip", "freeze", "--all"]).stdout
    version_probe = run(
        [
            str(CPU_PYTHON),
            "-c",
            (
                "import importlib.metadata as m, json, platform, sys, torch, torchaudio; "
                "print(json.dumps({'python': platform.python_version(), "
                "'base_executable': sys._base_executable, 'torch': torch.__version__, "
                "'torchaudio': torchaudio.__version__, "
                "'chatterbox': m.version('chatterbox-tts')}))"
            ),
        ]
    )
    self_env = dict(os.environ)
    self_env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "CUDA_VISIBLE_DEVICES": "",
        }
    )
    self_check = run(
        [str(CPU_PYTHON), str(CPU_SIDECAR / "sidecar_worker.py"), "--self-check"],
        env=self_env,
    )
    parsed_self_check = json.loads(self_check.stdout)
    if not parsed_self_check.get("ready"):
        raise RuntimeError(f"accepted CPU sidecar self-check failed: {parsed_self_check}")
    return {
        "path": CPU_SIDECAR.relative_to(ROOT).as_posix(),
        "non_venv_file_count": len(records),
        "non_venv_files": records,
        "non_venv_manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "pip_freeze_sha256": hashlib.sha256(freeze.encode("utf-8")).hexdigest(),
        "pip_freeze_line_count": len([line for line in freeze.splitlines() if line.strip()]),
        "versions": json.loads(version_probe.stdout),
        "self_check": parsed_self_check,
    }


def ollama_ps() -> list[object]:
    request = Request("http://127.0.0.1:11434/api/ps", method="GET")
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    models = payload.get("models")
    if not isinstance(models, list):
        raise RuntimeError("unexpected Ollama /api/ps payload")
    return models


def main() -> int:
    if SNAPSHOT.exists() or SNAPSHOT_HASH.exists():
        raise FileExistsError("refusing to overwrite the Blackwell pre-install baseline")
    if not CPU_SIDECAR.is_dir() or not PROFILE.is_file() or not REFERENCE.is_file():
        raise FileNotFoundError("accepted CPU sidecar or approved Kira voice source is missing")
    if (TARGET / ".venv").exists():
        raise RuntimeError("Blackwell environment already exists; pre-install snapshot is too late")
    models = ollama_ps()
    if models:
        raise RuntimeError("resource serialization requires Ollama to be empty before preflight")
    gpu = nvidia_snapshot()
    if gpu["name"] != "NVIDIA GeForce RTX 5060 Ti" or gpu["compute_capability"] != "12.0":
        raise RuntimeError(f"unexpected Blackwell device: {gpu}")
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "pre-install baseline for additive official Blackwell Chatterbox sidecar",
        "global_python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "unchanged_required": True,
        },
        "new_environment_python": {
            "source_executable": str(json.loads(run([str(CPU_PYTHON), "-c", "import json,sys; print(json.dumps(sys._base_executable))"]).stdout)),
            "required_version": "3.11.9",
        },
        "gpu": gpu,
        "system_memory": memory_snapshot(),
        "ollama_models_before_install": models,
        "cpu_sidecar": cpu_sidecar_snapshot(),
        "approved_voice": {
            "profile": PROFILE.relative_to(ROOT).as_posix(),
            "profile_sha256": sha256_file(PROFILE),
            "reference": REFERENCE.relative_to(ROOT).as_posix(),
            "reference_sha256": sha256_file(REFERENCE),
        },
        "constraints": {
            "cpu_sidecar_must_remain_runnable": True,
            "global_python_must_remain_unchanged": True,
            "official_stable_packages_only": True,
            "nightly_allowed_in_this_environment": False,
            "qwen_or_blender_or_studio_concurrent": False,
        },
    }
    text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    SNAPSHOT.write_text(text, encoding="utf-8")
    SNAPSHOT_HASH.write_text(
        f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {SNAPSHOT.name}\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "snapshot": SNAPSHOT.relative_to(ROOT).as_posix(),
                "snapshot_sha256": sha256_file(SNAPSHOT),
                "cpu_sidecar_manifest_sha256": record["cpu_sidecar"]["non_venv_manifest_sha256"],
                "gpu": gpu,
                "free_system_ram_mib": record["system_memory"]["free_physical_mib"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
