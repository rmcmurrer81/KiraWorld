#!/usr/bin/env python3
"""Prove the isolated stable PyTorch build executes real RTX 5060 Ti kernels."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = (
    ROOT
    / "Voice"
    / "sidecars"
    / "chatterbox_blackwell_gpu"
    / "evidence"
    / "torch_gpu_readiness.json"
)
EXPECTED_DEVICE = "NVIDIA GeForce RTX 5060 Ti"
EXPECTED_TORCH = "2.11.0+cu130"
EXPECTED_TORCHAUDIO = "2.11.0+cu130"
EXPECTED_CUDA = "13.0"
REJECTED_TEXT = (
    "not compatible with the current pytorch installation",
    "unsupported gpu architecture",
    "unsupported architecture",
    "no kernel image",
    "sm_120 is not compatible",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nvidia_memory() -> dict[str, Any]:
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
    completed = subprocess.run(
        [
            str(executable),
            "--query-gpu=name,driver_version,memory.total,memory.free,memory.used",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    rows = []
    for line in completed.stdout.splitlines():
        values = [item.strip() for item in line.split(",")]
        if len(values) == 5:
            rows.append(
                {
                    "name": values[0],
                    "driver_version": values[1],
                    "total_mib": int(values[2]),
                    "free_mib": int(values[3]),
                    "used_mib": int(values[4]),
                }
            )
    return {
        "returncode": completed.returncode,
        "rows": rows,
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    target = args.output.resolve()
    target.relative_to(ROOT.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing readiness evidence: {target}")

    started = time.perf_counter()
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": utc_now(),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "nvidia_before": nvidia_memory(),
        "issues": [],
        "errors": [],
    }
    captured: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import torch
            import torchaudio

            cuda_available = bool(torch.cuda.is_available())
            device_name = torch.cuda.get_device_name(0) if cuda_available else None
            capability = list(torch.cuda.get_device_capability(0)) if cuda_available else None
            architectures = list(torch.cuda.get_arch_list())
            report["versions"] = {
                "torch": torch.__version__,
                "torchaudio": torchaudio.__version__,
                "torch_cuda_runtime": torch.version.cuda,
            }
            report["cuda"] = {
                "available": cuda_available,
                "device_name": device_name,
                "device_capability": capability,
                "compiled_architectures": architectures,
                "sm_120_compiled": "sm_120" in architectures,
            }
            if not cuda_available:
                report["issues"].append("cuda_unavailable")
                raise RuntimeError("CUDA is not available")

            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(0)
            allocated_before = int(torch.cuda.memory_allocated(0))
            reserved_before = int(torch.cuda.memory_reserved(0))
            free_before, total_before = torch.cuda.mem_get_info(0)

            # A 4096 x 4096 float32 matrix makes the allocation externally
            # measurable while the small deterministic corner proves the
            # actual CUDA matmul result, rather than mere device visibility.
            left = torch.ones((4096, 4096), dtype=torch.float32, device="cuda")
            right = torch.full((4096, 64), 2.0, dtype=torch.float32, device="cuda")
            product = left @ right
            torch.cuda.synchronize()
            sample = product[:2, :2].detach().cpu().tolist()
            expected_value = 8192.0
            expected = all(
                abs(float(value) - expected_value) <= 0.01
                for row in sample
                for value in row
            )
            allocated_during = int(torch.cuda.memory_allocated(0))
            reserved_during = int(torch.cuda.memory_reserved(0))
            peak_allocated = int(torch.cuda.max_memory_allocated(0))
            peak_reserved = int(torch.cuda.max_memory_reserved(0))
            free_during, total_during = torch.cuda.mem_get_info(0)

            del product, right, left
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            allocated_after = int(torch.cuda.memory_allocated(0))
            reserved_after = int(torch.cuda.memory_reserved(0))
            free_after, total_after = torch.cuda.mem_get_info(0)
            report["cuda_operation"] = {
                "kind": "float32_cuda_matmul",
                "left_shape": [4096, 4096],
                "right_shape": [4096, 64],
                "result_shape": [4096, 64],
                "sample": sample,
                "expected_value": expected_value,
                "expected_result": expected,
                "allocated_before_bytes": allocated_before,
                "allocated_during_bytes": allocated_during,
                "allocated_after_release_bytes": allocated_after,
                "reserved_before_bytes": reserved_before,
                "reserved_during_bytes": reserved_during,
                "reserved_after_release_bytes": reserved_after,
                "peak_allocated_bytes": peak_allocated,
                "peak_reserved_bytes": peak_reserved,
                "free_before_bytes": int(free_before),
                "free_during_bytes": int(free_during),
                "free_after_release_bytes": int(free_after),
                "total_before_bytes": int(total_before),
                "total_during_bytes": int(total_during),
                "total_after_bytes": int(total_after),
                "allocation_measurable": allocated_during > allocated_before,
                "release_measurable": allocated_after < allocated_during,
            }
            captured.extend(str(item.message) for item in caught)

        checks = {
            "python_311": tuple(sys.version_info[:2]) == (3, 11),
            "torch_exact": report["versions"]["torch"] == EXPECTED_TORCH,
            "torchaudio_exact": report["versions"]["torchaudio"] == EXPECTED_TORCHAUDIO,
            "cuda_runtime_exact": report["versions"]["torch_cuda_runtime"] == EXPECTED_CUDA,
            "cuda_available": report["cuda"]["available"] is True,
            "device_exact": report["cuda"]["device_name"] == EXPECTED_DEVICE,
            "capability_exact": report["cuda"]["device_capability"] == [12, 0],
            "sm_120_compiled": report["cuda"]["sm_120_compiled"] is True,
            "cuda_result_exact": report["cuda_operation"]["expected_result"] is True,
            "allocation_measurable": report["cuda_operation"]["allocation_measurable"] is True,
            "release_measurable": report["cuda_operation"]["release_measurable"] is True,
        }
        report["checks"] = checks
        report["issues"].extend(key for key, passed in checks.items() if not passed)
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")

    report["captured_warnings"] = captured
    warning_text = "\n".join(captured).casefold()
    report["rejected_warning_matches"] = [value for value in REJECTED_TEXT if value in warning_text]
    if report["rejected_warning_matches"]:
        report["issues"].append("unsupported_architecture_warning")
    report["nvidia_after"] = nvidia_memory()
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    report["finished_at"] = utc_now()
    report["status"] = "PASS" if not report["issues"] and not report["errors"] else "FAIL"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(target)
    target.with_suffix(".sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "evidence": str(target), "sha256": digest}, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
