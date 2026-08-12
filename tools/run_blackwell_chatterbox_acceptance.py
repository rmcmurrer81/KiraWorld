#!/usr/bin/env python3
"""Run one bounded no-playback approved-Kira Blackwell voice proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_blackwell_chatterbox_preflight import cpu_sidecar_snapshot  # noqa: E402
from tools.run_qwen_text_voice_acceptance import (  # noqa: E402
    compare_protected_hashes,
    hash_protected_files,
    validate_wav,
)


SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_gpu"
PYTHON = SIDECAR / ".venv" / "Scripts" / "python.exe"
WORKER = SIDECAR / "sidecar_worker.py"
PREFLIGHT_WORKER = SIDECAR / "restricted_env_preflight.py"
CONFIG = SIDECAR / "sidecar_config.json"
EVIDENCE_ROOT = ROOT / "RecoverySprint" / "continuation_20260801" / "blackwell_chatterbox_acceptance"
OWNER_LISTENING = (
    ROOT / "RecoverySprint" / "continuation_20260801" / "blackwell_chatterbox_owner_listening"
)
CPU_SAMPLE = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260801"
    / "chatterbox_sidecar_acceptance"
    / "attempt_01"
    / "kira_approved_sidecar_probe.wav"
)
PUBLIC_TEXT = "I received your typed message, Robert, and this approved Kira voice test is complete."
CACHE_ROOT = ROOT / "RecoverySprint" / "runtime_cache" / "blackwell_chatterbox"
CACHE_PATHS = {
    "TORCHINDUCTOR_CACHE_DIR": CACHE_ROOT / "torchinductor",
    "TRITON_CACHE_DIR": CACHE_ROOT / "triton",
    "TEMP": CACHE_ROOT / "temp",
    "TMP": CACHE_ROOT / "temp",
}
CACHE_MAX_BYTES = 20 * 1024 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def qwen_loaded() -> bool:
    completed = subprocess.run(
        ["ollama", "ps"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return "qwen3.5:9b" in completed.stdout.casefold()


def gpu_used_mib() -> float | None:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        values = [float(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
        return sum(values) if completed.returncode == 0 and values else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def child_gpu_process_present(pid: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        return {
            "query_returncode": completed.returncode,
            "rows": rows,
            "pid_present": any(line.split(",", 1)[0].strip() == str(pid) for line in rows),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"query_returncode": None, "rows": [], "pid_present": None, "error": str(exc)}


class ExternalSampler:
    def __init__(self, process: subprocess.Popen[str], baseline_gpu: float | None) -> None:
        self.process = process
        self.baseline_gpu = baseline_gpu
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="blackwell-acceptance-sampler", daemon=True)
        self.samples: list[dict[str, Any]] = []
        self.peak_process_tree_rss_mib = 0.0
        self.peak_system_used_mib = 0.0
        self.peak_gpu_used_mib = baseline_gpu or 0.0

    def _sample(self) -> None:
        import psutil

        rss = 0
        try:
            parent = psutil.Process(self.process.pid)
            processes = [parent, *parent.children(recursive=True)]
            rss = sum(item.memory_info().rss for item in processes if item.is_running())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        memory = psutil.virtual_memory()
        gpu = gpu_used_mib()
        process_mib = rss / (1024 * 1024)
        system_mib = (memory.total - memory.available) / (1024 * 1024)
        self.peak_process_tree_rss_mib = max(self.peak_process_tree_rss_mib, process_mib)
        self.peak_system_used_mib = max(self.peak_system_used_mib, system_mib)
        if gpu is not None:
            self.peak_gpu_used_mib = max(self.peak_gpu_used_mib, gpu)
        self.samples.append(
            {
                "elapsed_seconds": None,
                "process_tree_rss_mib": round(process_mib, 1),
                "system_ram_used_mib": round(system_mib, 1),
                "gpu_vram_used_mib": round(gpu, 1) if gpu is not None else None,
            }
        )

    def _run(self) -> None:
        started = time.perf_counter()
        while not self.stop_event.wait(0.1):
            self._sample()
            self.samples[-1]["elapsed_seconds"] = round(time.perf_counter() - started, 3)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.thread.join(timeout=2)
        baseline = self.baseline_gpu
        return {
            "sample_count": len(self.samples),
            "peak_process_tree_rss_mib": round(self.peak_process_tree_rss_mib, 1),
            "peak_system_ram_used_mib": round(self.peak_system_used_mib, 1),
            "baseline_gpu_vram_used_mib": round(baseline, 1) if baseline is not None else None,
            "peak_gpu_vram_used_mib": round(self.peak_gpu_used_mib, 1),
            "peak_gpu_delta_mib": (
                round(max(0.0, self.peak_gpu_used_mib - baseline), 1) if baseline is not None else None
            ),
            "samples": self.samples,
        }


def sidecar_environment() -> dict[str, str]:
    allowed = (
        "USERNAME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "SystemRoot",
        "WINDIR",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "DriverData",
        "ComSpec",
        "SystemDrive",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramW6432",
        "CommonProgramFiles",
        "CommonProgramFiles(x86)",
        "CommonProgramW6432",
    )
    env = {key: value for key in allowed if (value := os.environ.get(key))}
    controlled_root = CACHE_ROOT.resolve()
    controlled_root.relative_to((ROOT / "RecoverySprint" / "runtime_cache").resolve())
    for path in CACHE_PATHS.values():
        resolved = path.resolve()
        resolved.relative_to(controlled_root)
        resolved.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CUDA_VISIBLE_DEVICES": "0",
            "KIRA_BLACKWELL_VOICE_EXPERIMENT": "1",
            **{key: str(path.resolve()) for key, path in CACHE_PATHS.items()},
        }
    )
    return env


def cache_inventory() -> dict[str, Any]:
    files = [path for path in CACHE_ROOT.rglob("*") if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    return {
        "root": CACHE_ROOT.relative_to(ROOT).as_posix(),
        "file_count": len(files),
        "size_bytes": size,
        "size_mib": round(size / (1024 * 1024), 3),
        "documented_max_bytes": CACHE_MAX_BYTES,
        "documented_max_gib": 20,
        "within_documented_max": size <= CACHE_MAX_BYTES,
        "automatic_cleanup_performed": False,
    }


def run_restricted_preflight(run_dir: Path, timeout: int = 240) -> dict[str, Any]:
    completed = subprocess.run(
        [str(PYTHON), str(PREFLIGHT_WORKER)],
        cwd=str(ROOT),
        env=sidecar_environment(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    stdout_path = run_dir / "restricted_env_preflight_stdout.txt"
    stderr_path = run_dir / "restricted_env_preflight_stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        result = {
            "status": "FAIL",
            "errors": [f"JSONDecodeError: {exc}"],
        }
    result["process_returncode"] = completed.returncode
    result["stdout_sha256"] = sha256_file(stdout_path)
    result["stderr_sha256"] = sha256_file(stderr_path)
    result["worker_sha256"] = sha256_file(PREFLIGHT_WORKER)
    evidence_path = run_dir / "restricted_env_preflight.json"
    evidence_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["evidence"] = evidence_path.relative_to(ROOT).as_posix()
    result["evidence_sha256"] = sha256_file(evidence_path)
    return result


def run_worker(payload: dict[str, Any], timeout: int = 900) -> dict[str, Any]:
    baseline = gpu_used_mib()
    process = subprocess.Popen(
        [str(PYTHON), str(WORKER)],
        cwd=str(ROOT),
        env=sidecar_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    sampler = ExternalSampler(process, baseline)
    sampler.start()
    timed_out = False
    started = time.perf_counter()
    try:
        stdout, stderr = process.communicate(json.dumps(payload, ensure_ascii=False), timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        stdout, stderr = process.communicate(timeout=15)
    wall_seconds = round(time.perf_counter() - started, 3)
    samples = sampler.stop()

    after_samples: list[dict[str, Any]] = []
    for _ in range(20):
        used = gpu_used_mib()
        after_samples.append(
            {
                "elapsed_after_exit_seconds": round(len(after_samples) * 0.25, 2),
                "gpu_vram_used_mib": round(used, 1) if used is not None else None,
            }
        )
        if baseline is not None and used is not None and used <= baseline + 128.0:
            break
        time.sleep(0.25)
    final_gpu = after_samples[-1]["gpu_vram_used_mib"] if after_samples else None
    process_probe = child_gpu_process_present(process.pid)
    return {
        "pid": process.pid,
        "returncode": process.returncode,
        "timed_out": timed_out,
        "wall_seconds": wall_seconds,
        "stdout": stdout,
        "stderr": stderr,
        "external_resources": samples,
        "post_exit_gpu_samples": after_samples,
        "final_gpu_vram_used_mib": final_gpu,
        "vram_returned_after_exit": (
            baseline is not None
            and final_gpu is not None
            and float(final_gpu) <= float(baseline) + 128.0
            and float(samples.get("peak_gpu_delta_mib") or 0.0) >= 256.0
        ),
        "gpu_process_after_exit": process_probe,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, required=True, choices=(1, 2, 3, 4, 5))
    args = parser.parse_args()
    run_dir = EVIDENCE_ROOT / f"attempt_{args.attempt:02d}"
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing evidence: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    output = run_dir / "kira_approved_blackwell_gpu_probe.wav"
    report_path = run_dir / "blackwell_acceptance.json"
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    text_hash = hashlib.sha256(PUBLIC_TEXT.encode("utf-8")).hexdigest()
    payload = {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "channel": "public_spoken_only",
        "text": PUBLIC_TEXT,
        "text_sha256": text_hash,
        "reference_sha256": config["approved_reference_sha256"],
        "output_relative": output.relative_to(ROOT).as_posix(),
        "pcm_output_gain_db": 0.0,
        "proximity_cut_hz": 0.0,
        "proximity_cut_mix": 0.0,
    }
    before = hash_protected_files()
    cpu_before = cpu_sidecar_snapshot()
    report: dict[str, Any] = {
        "schema_version": 1,
        "attempt": args.attempt,
        "started_at": utc_now(),
        "public_spoken_text": PUBLIC_TEXT,
        "public_spoken_text_sha256": text_hash,
        "typed_input": True,
        "microphone_used": False,
        "image_input_used": False,
        "playback_requested": False,
        "generic_voice_allowed": False,
        "offline_cache_only": True,
        "approved_reference_sha256": config["approved_reference_sha256"],
        "approved_profile_sha256": config["approved_profile_sha256"],
        "acceptance_harness_sha256": sha256_file(Path(__file__)),
        "restricted_env_preflight_worker_sha256": sha256_file(PREFLIGHT_WORKER),
        "runtime_cache_before": cache_inventory(),
        "cpu_sidecar_before": {
            "non_venv_manifest_sha256": cpu_before["non_venv_manifest_sha256"],
            "pip_freeze_sha256": cpu_before["pip_freeze_sha256"],
            "ready": cpu_before["self_check"]["ready"],
        },
        "qwen_absent_before": not qwen_loaded(),
        "protected_before": before,
        "issues": [],
        "errors": [],
    }
    if report["qwen_absent_before"] is not True:
        report["issues"].append("qwen_present_before_gpu_voice")

    preflight = run_restricted_preflight(run_dir)
    report["restricted_environment_preflight"] = preflight
    preflight_passed = (
        preflight.get("status") == "PASS"
        and preflight.get("process_returncode") == 0
        and all((preflight.get("checks") or {}).values())
    )
    if not preflight_passed:
        report["issues"].append("restricted_environment_preflight_failed")

    worker_run: dict[str, Any] = {}
    result: dict[str, Any] = {}
    try:
        if not preflight_passed:
            raise RuntimeError("restricted environment preflight did not pass")
        worker_run = run_worker(payload)
        report["worker_process"] = {key: value for key, value in worker_run.items() if key != "stdout"}
        (run_dir / "worker_stdout.txt").write_text(worker_run["stdout"], encoding="utf-8")
        (run_dir / "worker_stderr.txt").write_text(worker_run["stderr"], encoding="utf-8")
        result = json.loads(worker_run["stdout"])
        report["synthesis_result"] = result
        report["wav_validation"] = validate_wav(output) if output.is_file() else {"passed": False}
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["wav_validation"] = {"passed": False}

    rejected_stderr = [
        value
        for value in ("unsupported architecture", "no kernel image", "sm_120 is not compatible")
        if value in str(worker_run.get("stderr") or "").casefold()
    ]
    report["rejected_stderr_matches"] = rejected_stderr
    checks = {
        "worker_exit_zero": worker_run.get("returncode") == 0,
        "worker_not_timed_out": worker_run.get("timed_out") is False,
        "generated": result.get("generated") is True,
        "approved_engine": result.get("engine") == "chatterbox_tts",
        "device_cuda": result.get("device") == "cuda",
        "text_bound": result.get("text_sha256") == text_hash and result.get("requested_text_bound") is True,
        "reference_bound": result.get("reference_sha256") == config["approved_reference_sha256"],
        "identity_preserved": result.get("voice_identity_status") == "reviewed_reference_chatterbox",
        "generic_voice_absent": result.get("generic_voice_used") is False,
        "playback_absent": result.get("playback") is False,
        "wav_valid": (report.get("wav_validation") or {}).get("passed") is True,
        "torch_gpu_allocation": (result.get("gpu_proof") or {}).get("actual_gpu_allocation") is True,
        "worker_gpu_observed": result.get("gpu_utilization_observed") is True,
        "external_gpu_observed": float(
            ((worker_run.get("external_resources") or {}).get("peak_gpu_delta_mib") or 0.0)
        )
        >= 256.0,
        "no_rejected_gpu_warning": not rejected_stderr
        and not ((result.get("gpu_proof") or {}).get("rejected_warning_matches") or []),
        "vram_returned_after_exit": worker_run.get("vram_returned_after_exit") is True,
        "gpu_process_absent_after_exit": (worker_run.get("gpu_process_after_exit") or {}).get("pid_present")
        is not True,
    }
    report["checks"] = checks
    report["issues"].extend(key for key, passed in checks.items() if not passed)

    cpu_after = cpu_sidecar_snapshot()
    report["cpu_sidecar_after"] = {
        "non_venv_manifest_sha256": cpu_after["non_venv_manifest_sha256"],
        "pip_freeze_sha256": cpu_after["pip_freeze_sha256"],
        "ready": cpu_after["self_check"]["ready"],
    }
    cpu_unchanged = (
        cpu_after["non_venv_manifest_sha256"] == cpu_before["non_venv_manifest_sha256"]
        and cpu_after["pip_freeze_sha256"] == cpu_before["pip_freeze_sha256"]
        and cpu_after["self_check"]["ready"] is True
    )
    report["cpu_sidecar_unchanged_and_runnable"] = cpu_unchanged
    if not cpu_unchanged:
        report["issues"].append("accepted_cpu_sidecar_changed_or_unavailable")

    report["qwen_absent_after"] = not qwen_loaded()
    if report["qwen_absent_after"] is not True:
        report["issues"].append("qwen_present_after_gpu_voice")
    after = hash_protected_files()
    report["protected_after"] = after
    report["protected_integrity"] = compare_protected_hashes(before, after)
    if (report["protected_integrity"] or {}).get("passed") is not True:
        report["issues"].append("protected_asset_integrity_failed")

    report["owner_listening"] = {
        "folder": OWNER_LISTENING.relative_to(ROOT).as_posix(),
        "pronunciation_assessment": "owner_listening_required",
        "automatic_quality_winner_declared": False,
        "files": [],
    }
    if checks["wav_valid"] and CPU_SAMPLE.is_file():
        OWNER_LISTENING.mkdir(parents=True, exist_ok=True)
        cpu_copy = OWNER_LISTENING / "CPU_ACCEPTED_same_sentence.wav"
        gpu_copy = OWNER_LISTENING / f"GPU_BLACKWELL_attempt_{args.attempt:02d}_same_sentence.wav"
        if not cpu_copy.exists():
            shutil.copy2(CPU_SAMPLE, cpu_copy)
        if not gpu_copy.exists():
            shutil.copy2(output, gpu_copy)
        report["owner_listening"]["files"] = [
            {
                "label": "accepted_cpu",
                "path": cpu_copy.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(cpu_copy),
                "wav": validate_wav(cpu_copy),
            },
            {
                "label": "blackwell_gpu_candidate",
                "path": gpu_copy.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(gpu_copy),
                "wav": validate_wav(gpu_copy),
            },
        ]
    elif not CPU_SAMPLE.is_file():
        report["issues"].append("accepted_cpu_comparison_sample_missing")

    report["finished_at"] = utc_now()
    report["runtime_cache_after"] = cache_inventory()
    if report["runtime_cache_after"]["within_documented_max"] is not True:
        report["issues"].append("controlled_runtime_cache_exceeds_documented_max")
    report["status"] = "PASS" if not report["issues"] and not report["errors"] else "FAIL"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(report_path)
    report_path.with_suffix(".sha256").write_text(f"{digest}  {report_path.name}\n", encoding="ascii")
    print(json.dumps({"status": report["status"], "evidence": str(report_path), "sha256": digest}, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
