"""Privacy-safe event capture for supervised live voice measurements.

The recorder is inert unless explicitly enabled by the world-shell launcher.
It records public word tokens and monotonic pipeline events, never Robert's
prompt, a raw model reply, private mind text, or truth-channel text.  Writing
is asynchronous so capture I/O is not placed on the first-audio path.
"""

from __future__ import annotations

import ctypes
import datetime as dt
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURE_ROOT = PROJECT_ROOT / "Data" / "voice" / "realtime_audio_readiness" / "live_capture"

_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", flags=re.UNICODE)
_FORBIDDEN_KEY_PARTS = ("prompt", "raw", "reply_text", "private", "truth", "mind")
_PUBLIC_WORD_KEYS = {
    "public_words",
    "expected_public_words",
    "synthesized_public_words",
    "playback_proxy_public_words",
    "owner_observed_public_words",
}
_ALLOWED_DETAIL_KEYS = {
    "candidate",
    "candidate_label",
    "interface",
    "engine",
    "device",
    "pipeline",
    "reason",
    "chunk_index",
    "chunk_count",
    "queue_position",
    "generated",
    "played",
    "complete",
    "cancelled",
    "interrupted",
    "privacy_safe_for_speech",
    "dialogue_names_spoken",
    "non_name_word_coverage_exact",
    "expected_public_word_count",
    "synthesized_public_word_count",
    "playback_proxy_public_word_count",
    "expected_vs_synthesized_exact",
    "expected_vs_playback_proxy_exact",
    "owner_observed_exact",
    "owner_true_first_audible_monotonic_ms",
    "first_audible_proxy_kind",
    "silence_proxy_kind",
    "public_words",
    "expected_public_words",
    "synthesized_public_words",
    "playback_proxy_public_words",
    "owner_observed_public_words",
    "playback_reason",
    "generation_reason",
    "route_id",
    "approved_voice_path_used",
    "device",
    "route_attempt_summary",
    "preferred_failure_reason",
    "gpu_synthesis_attempted",
    "cpu_synthesis_attempted",
    "automatic_cpu_fallback_used",
    "blackwell_self_check_cache_status",
    "blackwell_self_check_cache_scope",
    "blackwell_self_check_cache_key_sha256",
    "gpu_actual_allocation",
    "gpu_actual_execution",
    "gpu_utilization_observed",
    "peak_allocated_bytes",
    "peak_reserved_bytes",
    "peak_process_rss_mib",
    "peak_system_ram_used_mib",
    "baseline_gpu_vram_used_mib",
    "peak_gpu_vram_used_mib",
    "peak_sidecar_gpu_delta_mib",
    "sidecar_process_seconds",
    "sidecar_lifecycle",
    "persistent_worker_reused",
    "staging_promoted_to_caller_target",
    "generic_voice_used",
    "sapi_voice_used",
    "fallback_used",
    "test_only_injected_client",
    "production_route_promoted",
    "production_routing_authorized",
    "qwen_absence_proven_for_accepted_generation",
    "voice_identity_unchanged",
    "owner_observation_required",
    "audio_generated",
    "audio_played",
}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _public_tokens(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    tokens: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        found = _TOKEN_RE.findall(item.casefold())
        if len(found) == 1 and found[0] == item.strip().casefold():
            tokens.append(found[0].replace("’", "'"))
    return tokens


def _safe_details(details: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep a narrow schema that cannot accidentally persist private text."""

    safe: dict[str, Any] = {}
    for raw_key, value in (details or {}).items():
        key = str(raw_key or "").strip()
        lower = key.casefold()
        if key not in _ALLOWED_DETAIL_KEYS:
            continue
        if any(part in lower for part in _FORBIDDEN_KEY_PARTS) and not isinstance(value, (bool, type(None))):
            continue
        if key in _PUBLIC_WORD_KEYS:
            safe[key] = None if value is None and key.startswith("owner_") else _public_tokens(value)
        elif value is None or isinstance(value, (bool, int, float)):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value[:160]
    return safe


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


_WIN_MEMORY_APIS: tuple[Any, Any] | None = None


def _windows_memory_apis() -> tuple[Any, Any]:
    global _WIN_MEMORY_APIS
    if _WIN_MEMORY_APIS is None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        _WIN_MEMORY_APIS = (kernel32, psapi)
    return _WIN_MEMORY_APIS


def _memory_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {"available": False, "source": "unavailable"}
    if os.name == "nt":
        try:
            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                result = {
                    "available": True,
                    "source": "GlobalMemoryStatusEx",
                    "system_total_bytes": int(status.ullTotalPhys),
                    "system_available_bytes": int(status.ullAvailPhys),
                    "system_load_percent": int(status.dwMemoryLoad),
                }
            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            kernel32, psapi = _windows_memory_apis()
            process = kernel32.GetCurrentProcess()
            if psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
                result["process_working_set_bytes"] = int(counters.WorkingSetSize)
                result["process_peak_working_set_bytes"] = int(counters.PeakWorkingSetSize)
        except Exception as exc:  # pragma: no cover - platform defensive path
            result["error"] = type(exc).__name__
        return result

    try:  # Portable best effort used by tests and non-Windows development.
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total_pages = int(os.sysconf("SC_PHYS_PAGES"))
        avail_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        result = {
            "available": True,
            "source": "sysconf",
            "system_total_bytes": page_size * total_pages,
            "system_available_bytes": page_size * avail_pages,
        }
    except Exception as exc:  # pragma: no cover - platform defensive path
        result["error"] = type(exc).__name__
    return result


def _gpu_snapshot() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"available": False, "source": "nvidia-smi", "reason": "nvidia_smi_not_found"}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            [
                executable,
                "--query-gpu=index,memory.total,memory.used,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
            creationflags=flags,
        )
    except Exception as exc:  # pragma: no cover - hardware/tool boundary
        return {"available": False, "source": "nvidia-smi", "reason": type(exc).__name__}
    if completed.returncode != 0:
        return {"available": False, "source": "nvidia-smi", "reason": "query_failed"}
    devices: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 5:
            continue
        try:
            devices.append(
                {
                    "index": int(fields[0]),
                    "total_mib": int(fields[1]),
                    "used_mib": int(fields[2]),
                    "free_mib": int(fields[3]),
                    "utilization_percent": int(fields[4]),
                }
            )
        except ValueError:
            continue
    return {
        "available": bool(devices),
        "source": "nvidia-smi",
        "devices": devices,
        "sampling_note": "completion_boundary_only_to_avoid_first_audio_subprocess_delay",
    }


def resource_snapshot(*, include_gpu: bool = False) -> dict[str, Any]:
    snapshot = {"ram": _memory_snapshot()}
    snapshot["gpu"] = (
        _gpu_snapshot()
        if include_gpu
        else {
            "available": False,
            "source": "not_sampled_at_latency_sensitive_event",
        }
    )
    return snapshot


class VoiceBenchmarkRecorder:
    """Asynchronously persist one JSONL timeline per public voice request."""

    def __init__(
        self,
        capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
        *,
        enabled: bool = False,
        project_root: str | Path = PROJECT_ROOT,
    ) -> None:
        self.enabled = bool(enabled)
        self.project_root = Path(project_root).resolve()
        self.capture_root = Path(capture_root).resolve()
        try:
            self.capture_root.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("Voice benchmark capture root must stay inside the project root") from exc
        self._lock = threading.Lock()
        self._sequences: dict[str, int] = {}
        self._events: dict[str, list[str]] = {}
        self._writer_errors: list[str] = []
        self._write_queue: queue.Queue[tuple[Path, bytes] | None] = queue.Queue()
        self._writer: threading.Thread | None = None
        if self.enabled:
            self._writer = threading.Thread(
                target=self._writer_loop,
                name="kira-voice-benchmark-writer",
                daemon=True,
            )
            self._writer.start()

    def _writer_loop(self) -> None:
        while True:
            item = self._write_queue.get()
            try:
                if item is None:
                    return
                path, payload = item
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("ab") as handle:
                        handle.write(payload)
                except OSError as exc:
                    with self._lock:
                        self._writer_errors.append(f"{type(exc).__name__}: {exc}")
            finally:
                self._write_queue.task_done()

    def request_path(self, request_id: str) -> Path:
        identifier = str(request_id or "").strip()
        if not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise ValueError("Invalid voice benchmark request id")
        return self.capture_root / f"voice_request_{identifier}.jsonl"

    def start_request(
        self,
        *,
        candidate: str,
        candidate_label: str,
        interface: str,
        monotonic_ns: int | None = None,
    ) -> str:
        if not self.enabled:
            return ""
        request_id = uuid.uuid4().hex
        self.record_event(
            request_id,
            "request_submitted",
            {
                "candidate": candidate,
                "candidate_label": candidate_label,
                "interface": interface,
                "owner_observation_required": True,
            },
            monotonic_ns=monotonic_ns,
        )
        return request_id

    def record_event(
        self,
        request_id: str,
        event: str,
        details: Mapping[str, Any] | None = None,
        *,
        monotonic_ns: int | None = None,
        include_gpu: bool = False,
    ) -> float | None:
        if not self.enabled or not request_id:
            return None
        if not _EVENT_RE.fullmatch(str(event or "")):
            raise ValueError("Invalid voice benchmark event name")
        timestamp_ns = int(monotonic_ns if monotonic_ns is not None else time.perf_counter_ns())
        timestamp_ms = timestamp_ns / 1_000_000.0
        with self._lock:
            sequence = self._sequences.get(request_id, 0) + 1
            self._sequences[request_id] = sequence
            self._events.setdefault(request_id, []).append(event)
            # Keep sequence assignment and queue insertion together. Producer
            # and playback callbacks can arrive on different threads for the
            # same request; the JSONL line order must still match sequence.
            record = {
                "schema_version": 1,
                "artifact_kind": "kira_voice_benchmark_event",
                "request_id": request_id,
                "sequence": sequence,
                "event": event,
                "monotonic_ns": timestamp_ns,
                "monotonic_ms": round(timestamp_ms, 6),
                "wall_time_utc": _utc_now(),
                "process_id": os.getpid(),
                "thread_id": threading.get_ident(),
                "details": _safe_details(details),
                "resources": resource_snapshot(include_gpu=include_gpu),
                "privacy": {
                    "public_word_tokens_only": True,
                    "raw_prompt_recorded": False,
                    "raw_reply_recorded": False,
                    "private_mind_recorded": False,
                    "truth_channel_recorded": False,
                },
            }
            payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            self._write_queue.put((self.request_path(request_id), payload))
        return timestamp_ms

    def has_event(self, request_id: str, event: str) -> bool:
        with self._lock:
            return event in self._events.get(request_id, [])

    def finish_request(
        self,
        request_id: str,
        details: Mapping[str, Any],
        *,
        monotonic_ns: int | None = None,
        include_gpu: bool = True,
    ) -> float | None:
        timestamp = self.record_event(
            request_id,
            "request_completed",
            details,
            monotonic_ns=monotonic_ns,
            include_gpu=include_gpu,
        )
        self.flush()
        return timestamp

    def flush(self) -> None:
        if self.enabled:
            self._write_queue.join()

    @property
    def writer_errors(self) -> list[str]:
        with self._lock:
            return list(self._writer_errors)
