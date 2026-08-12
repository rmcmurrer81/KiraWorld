#!/usr/bin/env python3
"""One-shot, default-off live acceptance for the exact sealed Blackwell v8.

Importing this module is inert.  The only live path requires the exact accepted
audit bytes and the v8 per-run environment capability.  Playback is off by
default and has a second environment capability.  This harness never changes
production routing and never selects a fallback model or voice.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
import wave
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.persistent_blackwell_voice_integration_v8 import (  # noqa: E402
    BlackwellV8Coordinator,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7.persistent_worker import (  # noqa: E402
    load_canonical_config as load_v7_config,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (  # noqa: E402
    CANONICAL_CONFIG_SHA256,
    EXACT_PROFILE_SHA256,
    EXACT_REFERENCE_SHA256,
    load_canonical_config,
    sha256_file,
    strict_json_loads,
    verify_fresh_audit_authorization,
    verify_preserved_bytes,
    verify_seal_manifest,
)


HARNESS_ID = "blackwell_v8_exact_qwen35_single_current_answer_live_acceptance_v1"
ATTEMPT_ID = "attempt_01"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_bounded_live_acceptance"
)
AUDIT_AUTHORIZATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_cpu_park_fresh_static_audit"
    / "attempt_01"
    / "AUDIT_AUTHORIZATION.json"
)
EXPECTED_AUDIT_AUTHORIZATION_SHA256 = (
    "d822b4f07eb3ad7873f5e48129494c08b85f0e06845ae01d57841476bd4ef16f"
)
HARNESS_SEAL_MANIFEST_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_bounded_live_acceptance_preparation"
    / "HARNESS_SEAL_MANIFEST.json"
)
HARNESS_AUDIT_AUTHORIZATION_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "blackwell_v8_bounded_live_acceptance_fresh_static_audit"
    / "attempt_01"
    / "AUDIT_AUTHORIZATION.json"
)
LIVE_CAPABILITY_NAME = "KIRA_AUTHORIZE_BLACKWELL_V8_BOUNDED_ENGINEERING_RUN"
LIVE_CAPABILITY_VALUE = "exact_qwen35_blackwell_v2_v8_after_fresh_audit_only"
PLAYBACK_CAPABILITY_NAME = "KIRA_AUTHORIZE_BLACKWELL_V8_SINGLE_PLAYBACK"
PLAYBACK_CAPABILITY_VALUE = "play_exact_returned_v8_attempt_01_wav_once"
EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_MODEL_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
QWEN_TTL_SECONDS = 90
MAX_PUBLIC_TEXT_UTF8_BYTES = 512
RESIDENCY_TIMEOUT_SECONDS = 5.0
RESIDENCY_CLEANUP_WAIT_SECONDS = 20.0
ATTEMPT_PATTERN = re.compile(r"attempt_[0-9]{2}\Z")

MESSAGES: tuple[dict[str, str], ...] = (
    {
        "role": "system",
        "content": (
            "You are Kira speaking privately with Robert. Answer only the current "
            "question in one short, natural sentence. Stay in the present moment. "
            "Do not describe a test, model, prompt, system, or implementation."
        ),
    },
    {
        "role": "user",
        "content": (
            "Kira, how are you feeling right now? Answer naturally in one brief "
            "sentence about the present moment."
        ),
    },
)

OWNED_RUNTIME_ROOTS: tuple[Path, ...] = (
    ROOT / "RecoverySprint/runtime_cache/blackwell_chatterbox/v7_outputs",
    ROOT / "RecoverySprint/runtime_cache/blackwell_chatterbox/v8_playback",
)


class AcceptanceError(RuntimeError):
    """A closed acceptance gate failed."""


class _MEMORYSTATUSEX(ctypes.Structure):
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


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_once_json(path: Path, value: Any) -> None:
    """Create one durable JSON artifact and refuse all overwrites."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
    ) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


class AppendOnlyLedger:
    def __init__(self, attempt: Path) -> None:
        self.root = attempt / "events"
        self.root.mkdir(parents=False, exist_ok=False)
        self.sequence = 0
        self.previous_sha256: str | None = None
        self.records: list[dict[str, Any]] = []

    def append(self, stage: str, evidence: Any) -> dict[str, Any]:
        self.sequence += 1
        record = {
            "schema_version": 1,
            "sequence": self.sequence,
            "stage": stage,
            "recorded_utc": utc_now(),
            "previous_event_sha256": self.previous_sha256,
            "evidence": evidence,
        }
        name = f"{self.sequence:03d}_{stage}.json"
        path = self.root / name
        write_once_json(path, record)
        digest = sha256_file(path)
        item = {"path": path.relative_to(self.root.parent).as_posix(), "sha256": digest}
        self.records.append(item)
        self.previous_sha256 = digest
        return item


def verify_harness_seal() -> dict[str, Any]:
    value = strict_json_loads(HARNESS_SEAL_MANIFEST_PATH.read_bytes())
    required = {"schema_version", "harness_id", "status", "files"}
    if not isinstance(value, dict) or set(value) != required:
        raise AcceptanceError("harness seal manifest schema is not exact")
    if (
        value["schema_version"] != 1
        or value["harness_id"] != HARNESS_ID
        or value["status"] != "SEALED_STATIC_ONLY_PENDING_DIFFERENT_AGENT_AUDIT"
        or not isinstance(value["files"], list)
        or len(value["files"]) != 2
    ):
        raise AcceptanceError("harness seal manifest identity is not exact")
    expected_paths = {
        "tools/run_blackwell_v8_bounded_live_acceptance.py",
        "Testing/test_blackwell_v8_bounded_live_acceptance_hostile_static.py",
    }
    observed_paths: set[str] = set()
    for index, record in enumerate(value["files"]):
        if not isinstance(record, dict) or set(record) != {"path", "bytes", "sha256"}:
            raise AcceptanceError(f"harness seal record {index} is malformed")
        relative = record["path"]
        if not isinstance(relative, str) or relative in observed_paths:
            raise AcceptanceError("harness seal paths are invalid or duplicated")
        observed_paths.add(relative)
        path = ROOT / relative
        if (
            not path.is_file()
            or path.stat().st_size != record["bytes"]
            or sha256_file(path) != record["sha256"]
        ):
            raise AcceptanceError(f"sealed harness bytes drifted: {relative}")
    if observed_paths != expected_paths:
        raise AcceptanceError("harness seal file set is not exact")
    return dict(value)


def verify_fresh_harness_audit(expected_sha256: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or ""):
        raise AcceptanceError("fresh harness audit SHA-256 is required")
    if (
        not HARNESS_AUDIT_AUTHORIZATION_PATH.is_file()
        or sha256_file(HARNESS_AUDIT_AUTHORIZATION_PATH) != expected_sha256
    ):
        raise AcceptanceError("fresh different-agent harness audit bytes are absent or drifted")
    value = strict_json_loads(HARNESS_AUDIT_AUTHORIZATION_PATH.read_bytes())
    required = {
        "schema_version", "harness_id", "harness_seal_manifest_path",
        "harness_seal_manifest_sha256", "fresh_independent_audit",
        "auditor_relationship", "verdict", "static_only",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise AcceptanceError("fresh harness audit schema is not exact")
    expected_manifest_path = HARNESS_SEAL_MANIFEST_PATH.relative_to(ROOT).as_posix()
    if (
        value["schema_version"] != 1
        or value["harness_id"] != HARNESS_ID
        or value["harness_seal_manifest_path"] != expected_manifest_path
        or value["harness_seal_manifest_sha256"] != sha256_file(HARNESS_SEAL_MANIFEST_PATH)
        or value["fresh_independent_audit"] is not True
        or value["auditor_relationship"] != "different_agent_from_harness_author"
        or value["verdict"] != "ACCEPT_STATIC_ONLY"
        or value["static_only"] is not True
    ):
        raise AcceptanceError("fresh harness audit content is not acceptable")
    verify_harness_seal()
    return dict(value)


def validate_static_and_capability_gates(
    *, playback: bool, accepted_harness_audit_sha256: str
) -> dict[str, Any]:
    config = load_canonical_config()
    harness_seal = verify_harness_seal()
    harness_audit = verify_fresh_harness_audit(accepted_harness_audit_sha256)
    if CANONICAL_CONFIG_SHA256 != "9b221b9eb4c6ada505c8e912ba5554b8831ee7484a69ac7289cbeb430f338587":
        raise AcceptanceError("sealed v8 canonical config constant drifted")
    if AUDIT_AUTHORIZATION_PATH.resolve() != (
        ROOT
        / config["fresh_audit_contract"]["required_relative_path"]
    ).resolve():
        raise AcceptanceError("v8 audit authorization path is not exact")
    actual_audit_sha = sha256_file(AUDIT_AUTHORIZATION_PATH)
    if actual_audit_sha != EXPECTED_AUDIT_AUTHORIZATION_SHA256:
        raise AcceptanceError("exact ACCEPT_STATIC_ONLY audit authorization bytes are absent")
    verify_preserved_bytes(config)
    verify_seal_manifest(
        config, ROOT / config["fresh_audit_contract"]["required_seal_manifest_path"]
    )
    audit = verify_fresh_audit_authorization(
        config, expected_audit_sha256=EXPECTED_AUDIT_AUTHORIZATION_SHA256
    )
    if config["qwen_model"] != EXPECTED_MODEL or config["qwen_digest"] != EXPECTED_MODEL_DIGEST:
        raise AcceptanceError("exact Qwen 3.5 identity drifted")
    required_false = (
        "cpu_synthesis_allowed",
        "generic_voice_allowed",
        "sapi_allowed",
        "llama_allowed",
        "substitute_reference_allowed",
        "production_routing_authorized",
        "current_production_route_changed",
    )
    if any(config.get(key) is not False for key in required_false):
        raise AcceptanceError("v8 no-substitute/default-off policy drifted")
    if config.get("automatic_fallback_inside_candidate") is not None:
        raise AcceptanceError("v8 acquired an in-candidate fallback")
    if (
        config.get("engineering_run_opt_in") != LIVE_CAPABILITY_NAME
        or config.get("engineering_run_opt_in_value") != LIVE_CAPABILITY_VALUE
        or os.environ.get(LIVE_CAPABILITY_NAME) != LIVE_CAPABILITY_VALUE
    ):
        raise AcceptanceError("exact per-run v8 live capability is absent")
    if playback:
        if os.environ.get(PLAYBACK_CAPABILITY_NAME) != PLAYBACK_CAPABILITY_VALUE:
            raise AcceptanceError("separate exact one-playback capability is absent")
    elif os.environ.get(PLAYBACK_CAPABILITY_NAME) is not None:
        raise AcceptanceError("playback capability was supplied without --playback")
    if os.environ.get(config["feature_flag"]) not in (None, "", "0"):
        raise AcceptanceError("production-like v8 feature selection is forbidden here")
    if os.name != "nt":
        raise AcceptanceError("the sealed live candidate is Windows-only")
    return {
        "audit_authorization": audit,
        "audit_authorization_sha256": actual_audit_sha,
        "harness_seal_manifest_sha256": sha256_file(HARNESS_SEAL_MANIFEST_PATH),
        "harness_seal": harness_seal,
        "fresh_harness_audit": harness_audit,
        "fresh_harness_audit_sha256": accepted_harness_audit_sha256,
        "candidate_config_sha256": CANONICAL_CONFIG_SHA256,
        "live_capability_name": LIVE_CAPABILITY_NAME,
        "live_capability_value_sha256": sha256_text(LIVE_CAPABILITY_VALUE),
        "playback_requested": playback,
        "playback_capability_name": PLAYBACK_CAPABILITY_NAME if playback else None,
        "playback_capability_value_sha256": (
            sha256_text(PLAYBACK_CAPABILITY_VALUE) if playback else None
        ),
        "production_routing_changed": False,
    }


def reserve_only_attempt() -> Path:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    existing = sorted(
        path.name
        for path in EVIDENCE_ROOT.iterdir()
        if path.is_dir() and ATTEMPT_PATTERN.fullmatch(path.name)
    )
    if existing:
        raise AcceptanceError(f"one-shot live attempt already reserved: {existing}")
    attempt = EVIDENCE_ROOT / ATTEMPT_ID
    attempt.mkdir(parents=False, exist_ok=False)
    return attempt


def _bounded_read(response: Any, maximum_bytes: int) -> bytes:
    value = response.read(maximum_bytes + 1)
    if len(value) > maximum_bytes:
        raise AcceptanceError("loopback residency response exceeded byte bound")
    return value


def ollama_residency_snapshot(label: str) -> dict[str, Any]:
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/ps", method="GET"
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=RESIDENCY_TIMEOUT_SECONDS) as response:
        if int(getattr(response, "status", 0)) != 200:
            raise AcceptanceError("Ollama /api/ps did not return HTTP 200")
        payload = strict_json_loads(_bounded_read(response, 1024 * 1024))
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise AcceptanceError("Ollama residency schema is invalid")
    records: list[dict[str, str]] = []
    for index, item in enumerate(payload["models"]):
        if not isinstance(item, dict):
            raise AcceptanceError(f"Ollama residency record {index} is invalid")
        model = str(item.get("model") or item.get("name") or "").strip()
        digest = str(item.get("digest") or "").strip().lower()
        if not model or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AcceptanceError(f"Ollama residency identity {index} is invalid")
        records.append({"model": model, "digest": digest})
    return {
        "label": label,
        "captured_utc": utc_now(),
        "elapsed_seconds": time.monotonic() - started,
        "records": records,
        "all_models_absent": not records,
    }


def wait_for_zero_residency() -> dict[str, Any]:
    started = time.monotonic()
    samples: list[dict[str, Any]] = []
    while True:
        sample = ollama_residency_snapshot("finally_cleanup_poll")
        samples.append(sample)
        if sample["all_models_absent"] is True:
            return {
                "passed": True,
                "elapsed_seconds": time.monotonic() - started,
                "samples": samples,
            }
        if time.monotonic() - started >= RESIDENCY_CLEANUP_WAIT_SECONDS:
            return {
                "passed": False,
                "elapsed_seconds": time.monotonic() - started,
                "samples": samples,
            }
        time.sleep(0.25)


def windows_memory_snapshot() -> dict[str, Any]:
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise AcceptanceError("GlobalMemoryStatusEx failed")
    unit = 1024.0 * 1024.0
    commit_used = status.ullTotalPageFile - status.ullAvailPageFile
    return {
        "total_physical_mib": status.ullTotalPhys / unit,
        "available_physical_mib": status.ullAvailPhys / unit,
        "system_commit_used_mib": commit_used / unit,
        "system_commit_limit_mib": status.ullTotalPageFile / unit,
        "memory_load_percent": int(status.dwMemoryLoad),
    }


def nvidia_memory_snapshot() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi.exe") or shutil.which("nvidia-smi")
    if not executable:
        raise AcceptanceError("nvidia-smi is unavailable")
    command = [
        str(Path(executable).resolve()),
        "--query-gpu=index,name,uuid,memory.total,memory.free,memory.used",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=5.0,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise AcceptanceError("nvidia-smi resource query failed")
    rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(rows) != 1:
        raise AcceptanceError("exactly one NVIDIA GPU is required")
    fields = [item.strip() for item in rows[0].split(",")]
    if len(fields) != 6:
        raise AcceptanceError("nvidia-smi resource schema is invalid")
    try:
        index, name, gpu_uuid = fields[:3]
        total, free, used = (float(value) for value in fields[3:])
    except (TypeError, ValueError) as exc:
        raise AcceptanceError("nvidia-smi memory values are invalid") from exc
    if index != "0" or name != "NVIDIA GeForce RTX 5060 Ti" or not gpu_uuid:
        raise AcceptanceError("exact Blackwell device identity is absent")
    if not all(math.isfinite(value) and value >= 0 for value in (total, free, used)):
        raise AcceptanceError("nvidia-smi returned non-finite memory")
    return {
        "gpu_index": 0,
        "gpu_name": name,
        "gpu_uuid": gpu_uuid,
        "memory_total_mib": total,
        "memory_free_mib": free,
        "memory_used_mib": used,
        "nvidia_smi_path": str(Path(executable).resolve()),
        "nvidia_smi_sha256": sha256_file(Path(executable).resolve()),
    }


def capture_host_resources(label: str) -> dict[str, Any]:
    return {
        "label": label,
        "captured_utc": utc_now(),
        "ram": windows_memory_snapshot(),
        "vram": nvidia_memory_snapshot(),
    }


def validate_public_text(value: Any, claimed_sha256: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AcceptanceError("Qwen public text is empty or requires transformation")
    if "\n" in value or "\r" in value:
        raise AcceptanceError("Qwen public text is not one line")
    if len(value.encode("utf-8")) > MAX_PUBLIC_TEXT_UTF8_BYTES:
        raise AcceptanceError("Qwen public text exceeds the short-answer bound")
    if sha256_text(value) != claimed_sha256:
        raise AcceptanceError("Qwen public text hash is not exact")
    lowered = value.casefold()
    forbidden = (
        "as an ai", "language model", "system prompt", "this test", "the test",
        "benchmark", "llama", "sapi", "generic voice",
    )
    if any(item in lowered for item in forbidden):
        raise AcceptanceError("Qwen public text violates the natural-current-answer gate")
    if sum(value.count(mark) for mark in ".!?") > 2:
        raise AcceptanceError("Qwen public text is not a brief sentence")
    return value


def require_success(envelope: Any, stage: str) -> dict[str, Any]:
    if not isinstance(envelope, Mapping) or not isinstance(envelope.get("value"), Mapping):
        raise AcceptanceError(f"{stage} returned no exact semantic result")
    value = dict(envelope["value"])
    if value.get("success") is not True:
        raise AcceptanceError(f"{stage} failed closed: {value.get('error')}")
    return value


def validate_wav_lease(lease: Mapping[str, Any], expected_text_sha256: str) -> dict[str, Any]:
    required = {
        "handle_id", "artifact_sha256", "generation_id", "resolved_path",
        "byte_length",
    }
    if not required.issubset(lease):
        raise AcceptanceError("WAV lease is incomplete")
    path = Path(str(lease["resolved_path"]))
    if not path.is_absolute() or path.is_symlink():
        raise AcceptanceError("WAV lease path is unsafe")
    owned = (ROOT / load_v7_config()["owned_output_root"]).resolve()
    resolved = path.resolve(strict=True)
    resolved.relative_to(owned)
    actual_sha = sha256_file(resolved)
    if actual_sha != lease["artifact_sha256"] or resolved.stat().st_size != lease["byte_length"]:
        raise AcceptanceError("WAV bytes do not match the retained lease")
    with wave.open(str(resolved), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        frame_count = reader.getnframes()
    if channels != 1 or sample_width != 2 or sample_rate != 24000 or frame_count <= 0:
        raise AcceptanceError("WAV format is not exact mono PCM-16 24 kHz")
    return {
        "resolved_path": str(resolved),
        "artifact_sha256": actual_sha,
        "generation_id": lease["generation_id"],
        "text_sha256": expected_text_sha256,
        "byte_length": lease["byte_length"],
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate,
    }


def owned_runtime_residue() -> dict[str, Any]:
    roots: list[dict[str, Any]] = []
    total_files = 0
    for root in OWNED_RUNTIME_ROOTS:
        files = [] if not root.exists() else sorted(
            path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
        )
        total_files += len(files)
        roots.append({"root": str(root), "exists": root.exists(), "files": files})
    return {"zero_file_residue": total_files == 0, "total_files": total_files, "roots": roots}


def protected_boundary_snapshot() -> dict[str, Any]:
    """Rehash v2/v7/v8, production routing, and the accepted audit bytes."""

    config = load_canonical_config()
    audit = strict_json_loads(AUDIT_AUTHORIZATION_PATH.read_bytes())
    if not isinstance(audit, dict) or not isinstance(audit.get("seal_manifest_sha256"), str):
        raise AcceptanceError("accepted audit cannot bind the v8 seal")
    expected: dict[str, str] = {
        **config["sealed_v2_production_components"],
        **config["sealed_v7_accepted_boundary"],
        "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/candidate_config.json": (
            CANONICAL_CONFIG_SHA256
        ),
        config["fresh_audit_contract"]["required_seal_manifest_path"]: (
            audit["seal_manifest_sha256"]
        ),
        config["fresh_audit_contract"]["required_relative_path"]: (
            EXPECTED_AUDIT_AUTHORIZATION_SHA256
        ),
    }
    records: dict[str, Any] = {}
    for relative, expected_sha in sorted(expected.items()):
        path = ROOT / relative
        actual = sha256_file(path) if path.is_file() else None
        records[relative] = {
            "expected_sha256": expected_sha,
            "actual_sha256": actual,
            "matched": actual == expected_sha,
        }
    return {
        "captured_utc": utc_now(),
        "passed": all(record["matched"] for record in records.values()),
        "records": records,
        "production_routing_sha256": records[
            "Voice/sidecars/kira_approved_voice_routing.json"
        ]["actual_sha256"],
    }


def _stage_call(
    report: dict[str, Any], ledger: AppendOnlyLedger, stage: str,
    operation: Callable[[], Any],
) -> Any:
    started_utc = utc_now()
    started = time.monotonic()
    result: Any = None
    operation_error: BaseException | None = None
    try:
        result = operation()
    except BaseException as exc:
        operation_error = exc
    ended = time.monotonic()
    stage_record: dict[str, Any] = {
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "wall_elapsed_seconds": ended - started,
        "result": result,
    }
    if operation_error is not None:
        stage_record["operation_error"] = {
            "error_type": type(operation_error).__name__,
            "error": str(operation_error),
        }
    try:
        stage_record["host_resources_after"] = capture_host_resources(stage + "_after")
    except Exception as exc:
        stage_record["host_resource_error"] = f"{type(exc).__name__}:{exc}"
    report["stages"][stage] = stage_record
    ledger.append(stage, stage_record)
    if operation_error is not None:
        raise operation_error
    if "host_resource_error" in stage_record:
        raise AcceptanceError(f"{stage} host RAM/VRAM evidence failed")
    return result


def execute_live(
    *, playback: bool = False, accepted_harness_audit_sha256: str = ""
) -> tuple[int, Path]:
    """Consume the sole attempt and run the exact serialized live sequence."""

    gates = validate_static_and_capability_gates(
        playback=playback,
        accepted_harness_audit_sha256=accepted_harness_audit_sha256,
    )
    attempt = reserve_only_attempt()
    ledger = AppendOnlyLedger(attempt)
    write_once_json(
        attempt / "RUN_AUTHORIZATION.json",
        {
            "schema_version": 1,
            "harness_id": HARNESS_ID,
            "attempt_id": ATTEMPT_ID,
            "reserved_utc": utc_now(),
            **gates,
        },
    )
    ledger.append("authorization", gates)
    report: dict[str, Any] = {
        "schema_version": 1,
        "harness_id": HARNESS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_utc": utc_now(),
        "status": "RUNNING",
        "accepted": False,
        "playback_requested": playback,
        "playback_performed": False,
        "owner_hearing_proven": False,
        "production_routing_changed": False,
        "model_identity": {"model": EXPECTED_MODEL, "digest": EXPECTED_MODEL_DIGEST},
        "candidate_config_sha256": CANONICAL_CONFIG_SHA256,
        "audit_authorization_sha256": EXPECTED_AUDIT_AUTHORIZATION_SHA256,
        "stages": {},
        "errors": [],
    }
    coordinator: BlackwellV8Coordinator | None = None
    started_worker = False
    main_sequence_passed = False
    cleanup_value: dict[str, Any] | None = None
    close_value: dict[str, Any] | None = None
    try:
        protected_before = protected_boundary_snapshot()
        report["protected_boundary_before"] = protected_before
        if protected_before["passed"] is not True:
            raise AcceptanceError("protected v2-v8/production bytes drifted before live work")
        report["resources_before"] = capture_host_resources("before_live_worker")
        before = ollama_residency_snapshot("before_live_worker")
        report["residency_before"] = before
        ledger.append("pre_live", {
            "resources": report["resources_before"], "residency": before
        })
        if before["all_models_absent"] is not True:
            raise AcceptanceError("a model was resident before the owned attempt")

        nonce = sha256_text(f"{HARNESS_ID}:{ATTEMPT_ID}:{uuid.uuid4().hex}")
        owner = f"{HARNESS_ID}:owner:{uuid.uuid4().hex}"
        session = f"{HARNESS_ID}:session:{uuid.uuid4().hex}"
        token = f"{HARNESS_ID}:token:{uuid.uuid4().hex}"
        coordinator = BlackwellV8Coordinator.bounded_engineering_candidate(
            nonce=nonce,
            accepted_audit_sha256=EXPECTED_AUDIT_AUTHORIZATION_SHA256,
        )
        start = _stage_call(report, ledger, "worker_start", coordinator.start)
        started_worker = True
        if (
            start.get("started") is not True
            or start.get("job_or_process_group_owned") is not True
            or start.get("created_suspended") is not True
            or (start.get("job_assignment_proof") or {}).get("assigned_before_resume") is not True
            or (start.get("job_assignment_proof") or {}).get("kill_on_close") is not True
        ):
            raise AcceptanceError("worker process/Job identity is not exact")

        loaded_env = _stage_call(
            report, ledger, "voice_load", lambda: coordinator.load(owner=owner)
        )
        loaded = require_success(loaded_env, "voice_load")
        if loaded.get("state") != "LOADED_CUDA":
            raise AcceptanceError("voice did not load on exact CUDA")
        component_fingerprint = loaded.get("component_fingerprint")
        model_generation = loaded.get("model_generation")
        condition_digest = loaded.get("condition_digest")
        if not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (component_fingerprint, model_generation, condition_digest)
        ):
            raise AcceptanceError("voice component/model/condition hashes are invalid")

        parked_env = _stage_call(
            report, ledger, "voice_park_cpu",
            lambda: coordinator.park(reason="one exact Qwen 3.5 current-answer generation"),
        )
        parked = require_success(parked_env, "voice_park_cpu")
        if (
            parked.get("state") != "PARKED_CPU"
            or parked.get("model_generation") != model_generation
            or parked.get("component_fingerprint") != component_fingerprint
            or (parked.get("component_transfer") or {}).get("from_device") != "cuda"
            or (parked.get("component_transfer") or {}).get("to_device") != "cpu"
        ):
            raise AcceptanceError("voice CPU park/component ledger is not exact")

        qwen_load_env = _stage_call(
            report, ledger, "qwen_load",
            lambda: coordinator.qwen_load(
                owner=owner, session=session, token=token, ttl_seconds=QWEN_TTL_SECONDS
            ),
        )
        qwen_load = require_success(qwen_load_env, "qwen_load")
        if qwen_load.get("state") != "QWEN_OWNED":
            raise AcceptanceError("exact Qwen ownership did not commit")

        qwen_stream_env = _stage_call(
            report, ledger, "qwen_single_generation",
            lambda: coordinator.qwen_stream(
                owner=owner,
                session=session,
                token=token,
                messages=[dict(item) for item in MESSAGES],
            ),
        )
        qwen_stream = require_success(qwen_stream_env, "qwen_single_generation")
        public_text = validate_public_text(
            qwen_stream.get("text"), qwen_stream.get("text_sha256")
        )
        if (
            qwen_stream.get("state") != "PARKED_CPU"
            or (qwen_stream.get("residency_precommit") or {}).get("records") != []
            or (qwen_stream.get("residency_after") or {}).get("records") != []
        ):
            raise AcceptanceError("Qwen keep_alive=0 unload was not verified")
        after_qwen = ollama_residency_snapshot("after_qwen_before_voice_resume")
        report["qwen_unload_verification"] = {
            "worker_precommit": qwen_stream["residency_precommit"],
            "worker_after": qwen_stream["residency_after"],
            "independent_after": after_qwen,
            "verified": after_qwen["all_models_absent"] is True,
        }
        ledger.append("qwen_unload_verified", report["qwen_unload_verification"])
        if after_qwen["all_models_absent"] is not True:
            raise AcceptanceError("independent Qwen unload check found residency")
        report["public_text"] = public_text
        report["public_text_sha256"] = sha256_text(public_text)
        report["raw_qwen_text_equals_public_text"] = qwen_stream["text"] == public_text
        report["spoken_text_equals_public_text"] = True

        resumed_env = _stage_call(
            report, ledger, "voice_resume_cuda",
            lambda: coordinator.resume(reason="Qwen absence verified before exact synthesis"),
        )
        resumed = require_success(resumed_env, "voice_resume_cuda")
        if (
            resumed.get("state") != "LOADED_CUDA"
            or resumed.get("model_generation") != model_generation
            or resumed.get("component_fingerprint") != component_fingerprint
            or (resumed.get("component_transfer") or {}).get("from_device") != "cpu"
            or (resumed.get("component_transfer") or {}).get("to_device") != "cuda"
        ):
            raise AcceptanceError("voice CUDA resume/component ledger is not exact")

        synthesis_request = {
            "text": public_text,
            "text_sha256": sha256_text(public_text),
            "input_channel": "public_spoken_only",
            "profile_sha256": EXACT_PROFILE_SHA256,
            "reference_sha256": EXACT_REFERENCE_SHA256,
            "condition_digest": condition_digest,
        }
        synthesis_env = _stage_call(
            report, ledger, "exact_text_synthesis",
            lambda: coordinator.synthesize(synthesis_request),
        )
        synthesis = require_success(synthesis_env, "exact_text_synthesis")
        if (
            synthesis.get("device") != "cuda"
            or synthesis.get("text_sha256") != sha256_text(public_text)
            or synthesis.get("profile_sha256") != EXACT_PROFILE_SHA256
            or synthesis.get("reference_sha256") != EXACT_REFERENCE_SHA256
            or synthesis.get("generic_voice_used") is not False
            or synthesis.get("sapi_voice_used") is not False
            or synthesis.get("fallback_used") is not False
            or synthesis.get("model_generation") != model_generation
            or synthesis.get("component_fingerprint") != component_fingerprint
        ):
            raise AcceptanceError("synthesis used a non-exact component/text/route")
        lease = synthesis.get("artifact_lease")
        if not isinstance(lease, Mapping):
            raise AcceptanceError("synthesis returned no retained WAV lease")
        report["wav"] = validate_wav_lease(lease, sha256_text(public_text))
        report["voice_hashes"] = {
            "model_generation": model_generation,
            "component_fingerprint": component_fingerprint,
            "condition_digest": condition_digest,
            "profile_sha256": EXACT_PROFILE_SHA256,
            "reference_sha256": EXACT_REFERENCE_SHA256,
            "wav_sha256": report["wav"]["artifact_sha256"],
        }
        ledger.append("wav_verified", {
            "wav": report["wav"], "voice_hashes": report["voice_hashes"]
        })

        if playback:
            playback_id = sha256_text(
                f"{HARNESS_ID}:{ATTEMPT_ID}:{lease['artifact_sha256']}:{uuid.uuid4().hex}"
            )
            playback_env = _stage_call(
                report, ledger, "optional_playback",
                lambda: coordinator.playback(lease, playback_id=playback_id),
            )
            played = require_success(playback_env, "optional_playback")
            telemetry = played.get("playback")
            if (
                not isinstance(telemetry, Mapping)
                or telemetry.get("artifact_sha256") != lease["artifact_sha256"]
                or telemetry.get("played_memory_sha256") != lease["artifact_sha256"]
                or telemetry.get("route") != "blackwell_gpu"
                or telemetry.get("device") != "cuda"
                or telemetry.get("generic_voice_used") is not False
                or telemetry.get("sapi_voice_used") is not False
                or telemetry.get("fallback_used") is not False
                or telemetry.get("playback_process_in_inherited_job") is not True
                or telemetry.get("owned_copy_deleted_after_return") is not True
                or telemetry.get("owner_hearing_proven") is not False
            ):
                raise AcceptanceError("playback route/bytes/Job/hearing truth is not exact")
            report["playback_performed"] = True
            report["playback"] = dict(telemetry)
        else:
            report["playback"] = {
                "requested": False,
                "performed": False,
                "reason": "separate playback capability not requested",
            }
        main_sequence_passed = True
    except BaseException as exc:
        report["errors"].append(
            {
                "phase": "main_sequence",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
    finally:
        cleanup_started_utc = utc_now()
        cleanup_started = time.monotonic()
        process = None if coordinator is None else getattr(coordinator, "process", None)
        process_reports_running = False
        if process is not None:
            try:
                process_reports_running = bool(process.is_running)
            except BaseException:
                process_reports_running = False
        if coordinator is not None and (started_worker or process_reports_running):
            try:
                cleanup_env = coordinator.cleanup(reason="v8_bounded_live_acceptance_finally")
                cleanup_value = dict(cleanup_env)
            except BaseException as exc:
                report["errors"].append({
                    "phase": "finally_cleanup",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
        if coordinator is not None:
            try:
                close_value = coordinator.close()
            except BaseException as exc:
                report["errors"].append({
                    "phase": "finally_close",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
        try:
            final_residency = wait_for_zero_residency()
        except BaseException as exc:
            final_residency = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            report["errors"].append({
                "phase": "finally_residency",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        try:
            residue = owned_runtime_residue()
        except BaseException as exc:
            residue = {
                "zero_file_residue": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            report["errors"].append({
                "phase": "finally_residue",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        try:
            final_resources = capture_host_resources("finally_after_cleanup")
        except BaseException as exc:
            final_resources = {
                "error_type": type(exc).__name__, "error": str(exc)
            }
            report["errors"].append({
                "phase": "finally_resources",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        try:
            protected_after = protected_boundary_snapshot()
            protected_unchanged = bool(
                protected_after.get("passed") is True
                and report.get("protected_boundary_before", {}).get("records")
                == protected_after.get("records")
            )
            if not protected_unchanged:
                report["errors"].append({
                    "phase": "finally_protected_boundary",
                    "error_type": "AcceptanceError",
                    "error": "protected v2-v8/production bytes changed",
                })
        except BaseException as exc:
            protected_after = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            protected_unchanged = False
            report["errors"].append({
                "phase": "finally_protected_boundary",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        semantic_cleanup = (
            isinstance(cleanup_value, Mapping)
            and isinstance(cleanup_value.get("value"), Mapping)
            and cleanup_value["value"].get("unloaded") is True
            and cleanup_value["value"].get("cleanup_debt") is False
        )
        process_closed = (
            isinstance(close_value, Mapping) and close_value.get("root_exited") is True
        )
        finally_cleanup = {
            "started_utc": cleanup_started_utc,
            "ended_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - cleanup_started,
            "cleanup_result": cleanup_value,
            "close_result": close_value,
            "semantic_unload_proven": semantic_cleanup,
            "owned_worker_tree_exited": process_closed,
            "qwen_zero_residency": final_residency,
            "owned_runtime_residue": residue,
            "resources_after": final_resources,
            "protected_boundary_after": protected_after,
            "protected_boundary_unchanged": protected_unchanged,
        }
        finally_cleanup["zero_residue_proven"] = bool(
            semantic_cleanup
            and process_closed
            and final_residency.get("passed") is True
            and residue.get("zero_file_residue") is True
            and "error_type" not in final_resources
            and protected_unchanged
        )
        report["finally_cleanup"] = finally_cleanup
        try:
            ledger.append("finally_cleanup", finally_cleanup)
        except BaseException as exc:
            report["errors"].append({
                "phase": "finally_ledger",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    report["ended_utc"] = utc_now()
    report["event_chain"] = list(ledger.records)
    report["accepted"] = bool(
        main_sequence_passed
        and not report["errors"]
        and report["finally_cleanup"]["zero_residue_proven"] is True
    )
    if report["accepted"]:
        report["status"] = (
            "ENGINEERING_PASS_PLAYBACK_COMPLETED_OWNER_HEARING_NOT_CLAIMED"
            if playback
            else "ENGINEERING_PASS_NO_PLAYBACK"
        )
    else:
        report["status"] = "ENGINEERING_FAIL_CLEANUP_RECORDED"
    final_path = attempt / "FINAL_REPORT.json"
    write_once_json(final_path, report)
    return (0 if report["accepted"] else 1), final_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="consume the sole append-only live attempt after all environment gates",
    )
    parser.add_argument(
        "--playback",
        action="store_true",
        help="play the exact verified returned WAV once; requires a second capability",
    )
    parser.add_argument(
        "--accepted-harness-audit-sha256",
        default="",
        help="exact SHA-256 of the future different-agent harness audit authorization",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute_live:
        sys.stderr.write(
            "Blackwell v8 live acceptance is default-off; --execute-live and the exact "
            "per-run environment capability are required.\n"
        )
        return 64
    if args.playback and not args.execute_live:
        return 64
    try:
        code, final_path = execute_live(
            playback=bool(args.playback),
            accepted_harness_audit_sha256=args.accepted_harness_audit_sha256,
        )
    except BaseException as exc:
        sys.stderr.write(f"Blackwell v8 live acceptance refused before reservation: {type(exc).__name__}: {exc}\n")
        return 65
    sys.stdout.write(str(final_path) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
