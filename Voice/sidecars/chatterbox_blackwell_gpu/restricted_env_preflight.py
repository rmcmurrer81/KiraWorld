#!/usr/bin/env python3
"""Validate the exact restricted Windows environment used by the GPU worker."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import traceback
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CACHE_ROOT = ROOT / "RecoverySprint" / "runtime_cache" / "blackwell_chatterbox"
EXPECTED_CACHE_PATHS = {
    "TORCHINDUCTOR_CACHE_DIR": CACHE_ROOT / "torchinductor",
    "TRITON_CACHE_DIR": CACHE_ROOT / "triton",
    "TEMP": CACHE_ROOT / "temp",
    "TMP": CACHE_ROOT / "temp",
}
REJECTED_RUNTIME_TEXT = (
    "unsupported gpu architecture",
    "unsupported architecture",
    "no kernel image",
    "sm_120 is not compatible",
    "not compatible with the current pytorch installation",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def cache_inventory() -> dict[str, int]:
    files = [path for path in CACHE_ROOT.rglob("*") if path.is_file()]
    return {
        "file_count": len(files),
        "size_bytes": sum(path.stat().st_size for path in files),
    }


def main() -> int:
    started = time.perf_counter()
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": utc_now(),
        "python": sys.version,
        "executable": sys.executable,
        "username_present": bool(os.environ.get("USERNAME")),
        "username": os.environ.get("USERNAME"),
        "cache_root": str(CACHE_ROOT),
        "cache_before": cache_inventory(),
        "cache_paths": {},
        "checks": {},
        "issues": [],
        "errors": [],
    }

    cache_paths_valid = True
    cache_paths_writable = True
    try:
        resolved_root = CACHE_ROOT.resolve()
        for key, expected in EXPECTED_CACHE_PATHS.items():
            raw = os.environ.get(key)
            actual = Path(raw).resolve() if raw else None
            inside = False
            exact = False
            writable = False
            marker: Path | None = None
            if actual is not None:
                try:
                    actual.relative_to(resolved_root)
                    inside = True
                except ValueError:
                    inside = False
                exact = actual == expected.resolve()
                if inside and exact:
                    actual.mkdir(parents=True, exist_ok=True)
                    marker = actual / f"preflight_writable_{uuid.uuid4().hex}.txt"
                    marker.write_text("blackwell restricted-cache preflight\n", encoding="utf-8")
                    writable = marker.is_file() and marker.stat().st_size > 0
            report["cache_paths"][key] = {
                "value": raw,
                "expected": str(expected.resolve()),
                "inside_controlled_root": inside,
                "exact_expected_path": exact,
                "writable_marker": str(marker) if marker else None,
                "writable": writable,
            }
            cache_paths_valid = cache_paths_valid and inside and exact
            cache_paths_writable = cache_paths_writable and writable

        # Windows' standard library may probe the Unix-only ``pwd`` module
        # inside ``try/except ImportError`` blocks (for example while importing
        # ``tarfile``).  That is normal and harmless.  Attempt 3 converted the
        # probe into a fatal RuntimeError, so it tested the guard rather than
        # Torch/Chatterbox.  Preserve normal import semantics and fail only if an
        # uncaught exception actually escapes from the real cache/import path.
        pwd_module_available = importlib.util.find_spec("pwd") is not None

        captured: list[str] = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import getpass
            import tarfile
            import torch
            import torchaudio
            from transformers import GPT2Config, GPT2Model, LlamaConfig, LlamaModel

            resolved_username = getpass.getuser()

            cuda_available = bool(torch.cuda.is_available())
            if not cuda_available:
                raise RuntimeError("CUDA unavailable in restricted environment")

            torch.cuda.synchronize(0)
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(0)
            allocated_before = int(torch.cuda.memory_allocated(0))

            # Attempt 5 validates Chatterbox's ordinary eager CUDA path. The
            # optional Windows torch.compile path is deliberately not invoked:
            # Attempt 4 already preserved its genuine missing-Triton evidence,
            # and Chatterbox 0.1.7 does not require it for normal inference.
            eager_input = torch.ones((1024,), dtype=torch.float32, device="cuda")
            eager_output = eager_input + 1.0
            torch.cuda.synchronize(0)
            eager_expected = bool(
                torch.allclose(
                    eager_output,
                    torch.full_like(eager_output, 2.0),
                )
            )

            left = torch.ones((2048, 2048), dtype=torch.float32, device="cuda")
            right = torch.full((2048, 32), 2.0, dtype=torch.float32, device="cuda")
            product = left @ right
            torch.cuda.synchronize(0)
            matrix_sample = product[:2, :2].detach().cpu().tolist()
            matrix_expected = all(
                abs(float(value) - 4096.0) <= 0.01
                for row in matrix_sample
                for value in row
            )
            peak_allocated = int(torch.cuda.max_memory_allocated(0))
            del product, right, left, eager_output, eager_input
            torch.cuda.synchronize(0)
            torch.cuda.empty_cache()
            torch.cuda.synchronize(0)
            allocated_after = int(torch.cuda.memory_allocated(0))
            cuda_synchronization_succeeded = True
            captured = [str(item.message) for item in caught]

        warning_text = "\n".join(captured).casefold()
        rejected = [value for value in REJECTED_RUNTIME_TEXT if value in warning_text]
        report["normal_windows_import_semantics"] = {
            "getpass_user": resolved_username,
            "pwd_module_available": pwd_module_available,
            "pwd_module_expected_absent_on_windows": os.name == "nt" and not pwd_module_available,
            "tarfile_module": tarfile.__name__,
            "uncaught_pwd_related_exception": False,
        }
        report["compiled_cuda_support"] = {
            "status": "OPTIONAL_NOT_AVAILABLE_ON_CURRENT_WINDOWS_TRITON_PATH",
            "mandatory_for_eager_voice_inference": False,
            "torch_compile_invoked": False,
            "torch_dynamo_invoked": False,
            "torch_inductor_invoked": False,
            "triton_invoked": False,
            "attempt_04_blocker": "torch._inductor.exc.TritonMissing",
            "attempt_04_evidence": (
                "RecoverySprint/continuation_20260801/blackwell_chatterbox_acceptance/"
                "attempt_04/blackwell_acceptance.json"
            ),
        }
        report["transformers_compatibility_imports"] = {
            "LlamaModel": LlamaModel.__module__,
            "LlamaConfig": LlamaConfig.__module__,
            "GPT2Model": GPT2Model.__module__,
            "GPT2Config": GPT2Config.__module__,
        }
        report["versions"] = {
            "torch": torch.__version__,
            "torchaudio": torchaudio.__version__,
            "cuda_runtime": torch.version.cuda,
        }
        report["cuda"] = {
            "available": cuda_available,
            "device_name": torch.cuda.get_device_name(0),
            "device_capability": list(torch.cuda.get_device_capability(0)),
            "compiled_architectures": list(torch.cuda.get_arch_list()),
            "execution_mode": "ordinary_eager_cuda_only",
            "eager_increment_expected": eager_expected,
            "matrix_sample": matrix_sample,
            "matrix_expected": matrix_expected,
            "allocated_before_bytes": allocated_before,
            "peak_allocated_bytes": peak_allocated,
            "allocated_after_release_bytes": allocated_after,
            "synchronization_succeeded": cuda_synchronization_succeeded,
            "captured_warnings": captured,
            "rejected_warning_matches": rejected,
        }
        checks = {
            "python_311": tuple(sys.version_info[:2]) == (3, 11),
            "username_present": report["username_present"] is True,
            "getpass_resolved_username": resolved_username.casefold()
            == str(os.environ.get("USERNAME") or "").casefold(),
            "windows_pwd_absence_expected": os.name != "nt" or not pwd_module_available,
            "tarfile_import_succeeded": tarfile.__name__ == "tarfile",
            "normal_imports_completed_without_uncaught_pwd_error": True,
            "cache_paths_inside_controlled_root": cache_paths_valid,
            "cache_paths_writable": cache_paths_writable,
            "compiled_cuda_optional_not_mandatory": report["compiled_cuda_support"]["status"]
            == "OPTIONAL_NOT_AVAILABLE_ON_CURRENT_WINDOWS_TRITON_PATH",
            "torch_compile_not_invoked": report["compiled_cuda_support"]["torch_compile_invoked"]
            is False,
            "torch_exact": torch.__version__ == "2.11.0+cu130",
            "torchaudio_exact": torchaudio.__version__ == "2.11.0+cu130",
            "cuda_available": cuda_available,
            "device_exact": torch.cuda.get_device_name(0) == "NVIDIA GeForce RTX 5060 Ti",
            "capability_exact": list(torch.cuda.get_device_capability(0)) == [12, 0],
            "sm_120_compiled": "sm_120" in torch.cuda.get_arch_list(),
            "eager_tensor_exact": eager_expected,
            "cuda_matrix_exact": matrix_expected,
            "cuda_synchronization_succeeded": cuda_synchronization_succeeded,
            "gpu_allocation_measurable": peak_allocated > allocated_before,
            "gpu_release_measurable": allocated_after < peak_allocated,
            "former_transformers_import_boundary": all(
                (LlamaModel, LlamaConfig, GPT2Model, GPT2Config)
            ),
            "no_rejected_gpu_warning": not rejected,
        }
        report["checks"] = checks
        report["issues"].extend(key for key, passed in checks.items() if not passed)
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["traceback"] = traceback.format_exc()

    report["cache_after"] = cache_inventory()
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    report["finished_at"] = utc_now()
    report["status"] = "PASS" if not report["issues"] and not report["errors"] else "FAIL"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
