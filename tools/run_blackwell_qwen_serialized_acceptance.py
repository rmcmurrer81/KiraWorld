#!/usr/bin/env python3
"""Bounded Qwen -> Blackwell Chatterbox -> Qwen serialized acceptance.

This runner is intentionally inert unless ``--execute-live-acceptance`` is
provided.  It never changes a production binding, never enables playback, and
refuses to run unless the append-only Blackwell ``attempt_05`` standalone
evidence is intact and fully passing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.model_request_policy import ordinary_model_request_fields  # noqa: E402
from tools.build_blackwell_chatterbox_preflight import cpu_sidecar_snapshot  # noqa: E402
from tools import run_blackwell_chatterbox_acceptance as blackwell  # noqa: E402
from tools import run_qwen_text_voice_acceptance as qwen  # noqa: E402


PINNED_MODEL = "qwen3.5:9b"
PINNED_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
PUBLIC_SPOKEN_TEXT = (
    "I received your typed message, Robert, and this approved Kira voice test is complete."
)
APPROVED_PROFILE_SHA256 = (
    "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
)
APPROVED_REFERENCE_SHA256 = (
    "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
)
STANDALONE_ATTEMPT = 5
STANDALONE_DIR = blackwell.EVIDENCE_ROOT / "attempt_05"
STANDALONE_REPORT = STANDALONE_DIR / "blackwell_acceptance.json"
STANDALONE_REPORT_SHA256 = STANDALONE_DIR / "blackwell_acceptance.sha256"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260801"
    / "blackwell_qwen_serialized_acceptance"
)
PROFILE_PATH = ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
REFERENCE_PATH = (
    ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav"
)
REJECTED_GPU_MESSAGES = (
    "unsupported architecture",
    "no kernel image",
    "sm_120 is not compatible",
)
REQUIRED_STANDALONE_CHECKS = frozenset(
    {
        "worker_exit_zero",
        "worker_not_timed_out",
        "generated",
        "approved_engine",
        "device_cuda",
        "text_bound",
        "reference_bound",
        "identity_preserved",
        "generic_voice_absent",
        "playback_absent",
        "wav_valid",
        "torch_gpu_allocation",
        "worker_gpu_observed",
        "external_gpu_observed",
        "no_rejected_gpu_warning",
        "vram_returned_after_exit",
        "gpu_process_absent_after_exit",
    }
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tree_snapshot(root: Path) -> dict[str, Any]:
    records = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda p: p.as_posix()):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    aggregate = hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"file_count": len(records), "tree_sha256": aggregate, "files": records}


def _read_expected_sha256(path: Path, expected_name: str) -> str:
    parts = path.read_text(encoding="ascii").strip().split()
    if len(parts) != 2 or parts[1] != expected_name:
        raise qwen.AcceptanceSafetyError(f"invalid standalone checksum file: {path}")
    digest = parts[0].casefold()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise qwen.AcceptanceSafetyError("standalone checksum is not a SHA-256 value")
    return digest


def validate_standalone_attempt_05() -> dict[str, Any]:
    if not STANDALONE_REPORT.is_file() or not STANDALONE_REPORT_SHA256.is_file():
        raise qwen.AcceptanceSafetyError("Blackwell standalone attempt_05 evidence is missing")
    expected_report_hash = _read_expected_sha256(
        STANDALONE_REPORT_SHA256, STANDALONE_REPORT.name
    )
    actual_report_hash = sha256_file(STANDALONE_REPORT)
    if actual_report_hash != expected_report_hash:
        raise qwen.AcceptanceSafetyError("Blackwell standalone attempt_05 report hash mismatch")
    report = json.loads(STANDALONE_REPORT.read_text(encoding="utf-8"))
    checks = report.get("checks") if isinstance(report.get("checks"), Mapping) else {}
    missing_checks = sorted(REQUIRED_STANDALONE_CHECKS - set(checks))
    failed_checks = sorted(key for key in REQUIRED_STANDALONE_CHECKS if checks.get(key) is not True)
    preflight = report.get("restricted_environment_preflight") or {}
    synthesis = report.get("synthesis_result") or {}
    issues: list[str] = []
    if report.get("status") != "PASS" or report.get("attempt") != STANDALONE_ATTEMPT:
        issues.append("standalone_attempt_05_not_pass")
    if report.get("public_spoken_text") != PUBLIC_SPOKEN_TEXT:
        issues.append("standalone_public_text_mismatch")
    if report.get("public_spoken_text_sha256") != sha256_text(PUBLIC_SPOKEN_TEXT):
        issues.append("standalone_public_text_hash_mismatch")
    if report.get("approved_profile_sha256") != APPROVED_PROFILE_SHA256:
        issues.append("standalone_profile_hash_mismatch")
    if report.get("approved_reference_sha256") != APPROVED_REFERENCE_SHA256:
        issues.append("standalone_reference_hash_mismatch")
    if missing_checks:
        issues.append("standalone_required_checks_missing")
    if failed_checks:
        issues.append("standalone_required_checks_failed")
    if preflight.get("status") != "PASS" or preflight.get("process_returncode") != 0:
        issues.append("standalone_restricted_preflight_not_pass")
    if not (preflight.get("checks") or {}) or not all((preflight.get("checks") or {}).values()):
        issues.append("standalone_restricted_preflight_check_failed")
    if synthesis.get("generated") is not True or synthesis.get("device") != "cuda":
        issues.append("standalone_eager_cuda_synthesis_not_proven")
    if synthesis.get("engine") != "chatterbox_tts":
        issues.append("standalone_approved_engine_not_proven")
    if synthesis.get("generic_voice_used") is not False or synthesis.get("playback") is not False:
        issues.append("standalone_voice_safety_not_proven")
    if synthesis.get("reference_sha256") != APPROVED_REFERENCE_SHA256:
        issues.append("standalone_worker_reference_mismatch")
    if report.get("qwen_absent_before") is not True or report.get("qwen_absent_after") is not True:
        issues.append("standalone_qwen_absence_not_proven")
    if report.get("cpu_sidecar_unchanged_and_runnable") is not True:
        issues.append("standalone_cpu_fallback_integrity_not_proven")
    if (report.get("protected_integrity") or {}).get("passed") is not True:
        issues.append("standalone_protected_integrity_not_proven")
    if report.get("issues") or report.get("errors"):
        issues.append("standalone_report_contains_failures")
    if issues:
        raise qwen.AcceptanceSafetyError(
            "standalone attempt_05 is not an acceptable prerequisite: " + ", ".join(issues)
        )
    return {
        "attempt": STANDALONE_ATTEMPT,
        "status": "PASS",
        "report": STANDALONE_REPORT.relative_to(ROOT).as_posix(),
        "report_sha256": actual_report_hash,
        "wav_sha256": (report.get("wav_validation") or {}).get("sha256"),
        "tree": tree_snapshot(STANDALONE_DIR),
    }


def validate_static_contract() -> dict[str, Any]:
    issues: list[str] = []
    if qwen.EXPECTED_MODEL != PINNED_MODEL or qwen.EXPECTED_DIGEST != PINNED_DIGEST:
        issues.append("shared_qwen_pin_changed")
    if blackwell.PUBLIC_TEXT != PUBLIC_SPOKEN_TEXT:
        issues.append("shared_blackwell_public_text_changed")
    config = json.loads(blackwell.CONFIG.read_text(encoding="utf-8"))
    if config.get("approved_profile") != PROFILE_PATH.relative_to(ROOT).as_posix():
        issues.append("approved_profile_path_changed")
    if config.get("approved_reference") != REFERENCE_PATH.relative_to(ROOT).as_posix():
        issues.append("approved_reference_path_changed")
    if config.get("approved_profile_sha256") != APPROVED_PROFILE_SHA256:
        issues.append("configured_profile_hash_changed")
    if config.get("approved_reference_sha256") != APPROVED_REFERENCE_SHA256:
        issues.append("configured_reference_hash_changed")
    if not PROFILE_PATH.is_file() or sha256_file(PROFILE_PATH) != APPROVED_PROFILE_SHA256:
        issues.append("approved_profile_file_hash_mismatch")
    if not REFERENCE_PATH.is_file() or sha256_file(REFERENCE_PATH) != APPROVED_REFERENCE_SHA256:
        issues.append("approved_reference_file_hash_mismatch")
    if config.get("input_channel") != "public_spoken_only":
        issues.append("sidecar_public_spoken_contract_changed")
    if config.get("compute_device") != "cuda":
        issues.append("sidecar_not_cuda")
    if config.get("playback") is not False:
        issues.append("sidecar_playback_not_disabled")
    if config.get("generic_voice_fallback_allowed") is not False:
        issues.append("generic_voice_fallback_enabled")
    if config.get("offline_cache_only") is not True:
        issues.append("sidecar_offline_cache_contract_changed")
    if issues:
        raise qwen.AcceptanceSafetyError("serialized static contract failed: " + ", ".join(issues))
    return {
        "qwen_model": PINNED_MODEL,
        "qwen_digest": PINNED_DIGEST,
        "public_spoken_text_sha256": sha256_text(PUBLIC_SPOKEN_TEXT),
        "approved_profile": PROFILE_PATH.relative_to(ROOT).as_posix(),
        "approved_profile_sha256": APPROVED_PROFILE_SHA256,
        "approved_reference": REFERENCE_PATH.relative_to(ROOT).as_posix(),
        "approved_reference_sha256": APPROVED_REFERENCE_SHA256,
        "sidecar_config_sha256": sha256_file(blackwell.CONFIG),
        "sidecar_worker_sha256": sha256_file(blackwell.WORKER),
        "playback": False,
        "generic_or_sapi_fallback_allowed": False,
        "image_input_allowed": False,
    }


def _parse_strict_spoken_reply(content: str, nonce: str) -> dict[str, Any]:
    issues: list[str] = []

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_non_finite(value: str) -> Any:
        raise ValueError(f"non-finite JSON value: {value}")

    parsed: Any = None
    try:
        parsed = json.loads(
            str(content or ""),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        issues.append("malformed_or_non_strict_json")
    if type(parsed) is not dict:
        issues.append("reply_not_object")
    else:
        if set(parsed) != {"SPOKEN", "nonce"}:
            issues.append("reply_shape_not_public_spoken_and_nonce_only")
        if type(parsed.get("SPOKEN")) is not str or parsed.get("SPOKEN") != PUBLIC_SPOKEN_TEXT:
            issues.append("spoken_text_not_exact")
        if type(parsed.get("nonce")) is not str or parsed.get("nonce") != nonce:
            issues.append("nonce_not_exact")
    issues = list(dict.fromkeys(issues))
    return {
        "passed": not issues,
        "parsed": parsed if type(parsed) is dict else None,
        "spoken": parsed.get("SPOKEN") if type(parsed) is dict else None,
        "observed_nonce": parsed.get("nonce") if type(parsed) is dict else None,
        "issues": issues,
    }


def qwen_public_spoken_probe(
    client: qwen.SafeOllamaClient,
    label: str,
    *,
    nonce: str,
) -> dict[str, Any]:
    expected_nonce = qwen._validate_lifecycle_nonce(nonce)
    expected = {"SPOKEN": PUBLIC_SPOKEN_TEXT, "nonce": expected_nonce}
    payload = {
        "model": PINNED_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Text-only serialized acceptance fixture. Return only the strict JSON object "
                    "required by the supplied schema. Copy both constants exactly; add no prose."
                ),
            },
            {"role": "user", "content": qwen.canonical_json(expected)},
        ],
        "stream": False,
        "keep_alive": "10m",
        "format": qwen.json_schema(
            {
                "SPOKEN": {"type": "string", "const": PUBLIC_SPOKEN_TEXT},
                "nonce": {"type": "string", "const": expected_nonce},
            },
            ["SPOKEN", "nonce"],
        ),
        "options": {
            "temperature": 0,
            "seed": 5187,
            "num_ctx": qwen.LIFECYCLE_CONTEXT_LENGTH,
            "num_predict": 128,
        },
        **ordinary_model_request_fields(PINNED_MODEL, keep_alive="10m"),
    }
    started = time.perf_counter()
    response = client.chat(payload)
    latency_ms = (time.perf_counter() - started) * 1000
    message = qwen._message(response)
    content = str(message.get("content") or "").strip()
    parsed = _parse_strict_spoken_reply(content, expected_nonce)
    residency = qwen.wait_for_model_state(
        client,
        loaded=True,
        required_context_length=qwen.LIFECYCLE_CONTEXT_LENGTH,
    )
    issues = list(parsed["issues"])
    if response.get("model") != PINNED_MODEL:
        issues.append("response_model_mismatch")
    if message.get("thinking") not in (None, ""):
        issues.append("thinking_returned_despite_think_false")
    if residency.get("passed") is not True:
        issues.append("exact_digest_residency_not_proven")
        issues.extend(f"residency_{item}" for item in residency.get("issues") or [])
    loaded = residency.get("loaded_record") or {}
    if str(loaded.get("digest") or "").strip().casefold() != PINNED_DIGEST:
        issues.append("loaded_digest_mismatch")
    issues = list(dict.fromkeys(issues))
    return {
        "label": label,
        "passed": not issues,
        "expected_nonce": expected_nonce,
        "observed_nonce": parsed.get("observed_nonce"),
        "response_model": response.get("model"),
        "response_text": content,
        "strict_public_spoken_reply": parsed,
        "released_spoken_text": parsed.get("spoken"),
        "released_spoken_text_sha256": (
            sha256_text(parsed["spoken"]) if isinstance(parsed.get("spoken"), str) else None
        ),
        "release_boundary": {
            "released_field": "SPOKEN",
            "released_fields": ["SPOKEN"],
            "unreleased_fields": ["nonce"],
            "private_mind_released": False,
            "factual_truth_released": False,
        },
        "loaded_digest": str(loaded.get("digest") or "").strip().casefold(),
        "request_policy": {
            "model": PINNED_MODEL,
            "digest": PINNED_DIGEST,
            "think": False,
            "images": False,
            "microphone": False,
        },
        "metrics": qwen.response_metrics(response, latency_ms),
        "ps": residency,
        "issues": issues,
    }


def _qwen_named_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for record in records:
        identifiers = " ".join(
            str(record.get(key) or "") for key in ("name", "model", "digest")
        ).casefold()
        if "qwen" in identifiers or PINNED_DIGEST in identifiers:
            result.append(dict(record))
    return result


class QwenAbsenceMonitor:
    """Read-only Ollama residency monitor used only while voice owns the GPU."""

    def __init__(self, client: qwen.SafeOllamaClient, interval_seconds: float = 0.25) -> None:
        self.client = client
        self.interval_seconds = max(0.1, min(1.0, float(interval_seconds)))
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name="blackwell-qwen-absence-monitor",
            daemon=True,
        )
        self.samples: list[dict[str, Any]] = []
        self.errors: list[str] = []

    def _capture(self) -> None:
        try:
            records = self.client.ps()
            strict = qwen.inspect_expected_model_residency(records)
            named = _qwen_named_records(records)
            self.samples.append(
                {
                    "at": utc_now(),
                    "qwen_named_records": named,
                    "expected_model_resident": strict.get("resident"),
                    "expected_model_identity_issues": strict.get("issues") or [],
                }
            )
        except Exception as exc:
            self.errors.append(f"{type(exc).__name__}: {exc}")

    def _run(self) -> None:
        self._capture()
        while not self.stop_event.wait(self.interval_seconds):
            self._capture()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            self.errors.append("monitor_thread_did_not_stop")
        qwen_seen = any(sample["qwen_named_records"] for sample in self.samples)
        identity_issue = any(sample["expected_model_identity_issues"] for sample in self.samples)
        return {
            "passed": bool(self.samples) and not self.errors and not qwen_seen and not identity_issue,
            "sample_count": len(self.samples),
            "qwen_seen": qwen_seen,
            "identity_issue_seen": identity_issue,
            "errors": list(dict.fromkeys(self.errors)),
            "samples": self.samples,
        }


def build_voice_payload(run_dir: Path, spoken_text: str) -> tuple[dict[str, Any], Path]:
    if spoken_text != PUBLIC_SPOKEN_TEXT:
        raise qwen.AcceptanceSafetyError("only the exact approved public SPOKEN sentence may be voiced")
    output = run_dir / "kira_approved_blackwell_gpu_serialized_probe.wav"
    text_hash = sha256_text(spoken_text)
    return (
        {
            "schema_version": 1,
            "request_id": str(uuid.uuid4()),
            "channel": "public_spoken_only",
            "text": spoken_text,
            "text_sha256": text_hash,
            "reference_sha256": APPROVED_REFERENCE_SHA256,
            "output_relative": output.relative_to(ROOT).as_posix(),
            "pcm_output_gain_db": 0.0,
            "proximity_cut_hz": 0.0,
            "proximity_cut_mix": 0.0,
        },
        output,
    )


def validate_voice_run(
    worker_run: Mapping[str, Any],
    result: Mapping[str, Any],
    output: Path,
    monitor: Mapping[str, Any],
) -> dict[str, Any]:
    wav = qwen.validate_wav(output) if output.is_file() else {"passed": False}
    stderr = str(worker_run.get("stderr") or "")
    rejected_stderr = [value for value in REJECTED_GPU_MESSAGES if value in stderr.casefold()]
    checks = {
        "worker_exit_zero": worker_run.get("returncode") == 0,
        "worker_not_timed_out": worker_run.get("timed_out") is False,
        "generated": result.get("generated") is True,
        "approved_engine": result.get("engine") == "chatterbox_tts",
        "device_cuda": result.get("device") == "cuda",
        "public_spoken_channel": result.get("channel") == "public_spoken_only",
        "text_bound": result.get("text_sha256") == sha256_text(PUBLIC_SPOKEN_TEXT)
        and result.get("requested_text_bound") is True,
        "reference_bound": result.get("reference_sha256") == APPROVED_REFERENCE_SHA256,
        "audio_output_bound": result.get("audio_relative") == output.relative_to(ROOT).as_posix(),
        "identity_preserved": result.get("voice_identity_status") == "reviewed_reference_chatterbox",
        "generic_voice_absent": result.get("generic_voice_used") is False,
        "playback_absent": result.get("playback") is False,
        "wav_valid": wav.get("passed") is True,
        "torch_gpu_allocation": (result.get("gpu_proof") or {}).get("actual_gpu_allocation") is True,
        "worker_gpu_observed": result.get("gpu_utilization_observed") is True,
        "external_gpu_observed": float(
            ((worker_run.get("external_resources") or {}).get("peak_gpu_delta_mib") or 0.0)
        )
        >= 256.0,
        "no_rejected_gpu_warning": not rejected_stderr
        and not ((result.get("gpu_proof") or {}).get("rejected_warning_matches") or []),
        "clean_worker_exit_vram_return": worker_run.get("vram_returned_after_exit") is True,
        "gpu_process_absent_after_exit": (
            (worker_run.get("gpu_process_after_exit") or {}).get("pid_present") is not True
        ),
        "qwen_absent_for_entire_synthesis": monitor.get("passed") is True,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "issues": [key for key, passed in checks.items() if not passed],
        "wav_validation": wav,
        "rejected_stderr_matches": rejected_stderr,
        "qwen_absence_monitor": dict(monitor),
    }


def _new_run_directory(attempt: int) -> Path:
    if type(attempt) is not int or not 1 <= attempt <= 99:
        raise qwen.AcceptanceSafetyError("serialized attempt must be an integer from 1 through 99")
    run_dir = EVIDENCE_ROOT / f"attempt_{attempt:02d}"
    run_dir.resolve().relative_to(EVIDENCE_ROOT.resolve())
    if run_dir.exists():
        raise qwen.AcceptanceSafetyError(f"refusing to overwrite existing evidence: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _cpu_summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "non_venv_manifest_sha256": snapshot.get("non_venv_manifest_sha256"),
        "pip_freeze_sha256": snapshot.get("pip_freeze_sha256"),
        "ready": (snapshot.get("self_check") or {}).get("ready"),
    }


def execute_serialized_acceptance(
    *,
    attempt: int,
    endpoint: str,
    timeout_seconds: float,
    worker_timeout_seconds: int,
) -> tuple[dict[str, Any], Path]:
    # Static/prerequisite validation occurs before creating evidence or touching
    # model residency. A missing/tampered standalone PASS is a no-op failure.
    static_contract = validate_static_contract()
    standalone_before = validate_standalone_attempt_05()
    client = qwen.SafeOllamaClient(
        endpoint,
        timeout_seconds=timeout_seconds,
        max_chat_requests=2,
    )
    run_dir = _new_run_directory(attempt)
    report: dict[str, Any] = {
        "schema_version": 1,
        "suite_id": "blackwell_qwen_serialized_acceptance_v1",
        "attempt": attempt,
        "started_at": utc_now(),
        "status": "running",
        "scope": {
            "qwen_text_only": True,
            "image_input_used": False,
            "microphone_input_used": False,
            "playback_requested": False,
            "generic_or_sapi_voice_allowed": False,
            "production_bindings_changed": False,
            "models_serialized": True,
        },
        "static_contract": static_contract,
        "standalone_attempt_05_before": standalone_before,
        "sequence": [],
        "issues": [],
        "errors": [],
    }
    protected_before = qwen.hash_protected_files()
    cpu_before = cpu_sidecar_snapshot()
    immutable_before = {
        "sidecar_config_sha256": sha256_file(blackwell.CONFIG),
        "sidecar_worker_sha256": sha256_file(blackwell.WORKER),
    }
    report["protected_before"] = protected_before
    report["cpu_sidecar_before"] = _cpu_summary(cpu_before)
    qwen_owned = False
    voice_monitor: QwenAbsenceMonitor | None = None
    voice_monitor_result: dict[str, Any] = {
        "passed": False,
        "sample_count": 0,
        "errors": ["voice_monitor_not_started"],
    }
    try:
        installed_before = qwen.validate_exact_install(client.tags())
        report["installed_model_before"] = installed_before
        initial_absence = qwen.wait_for_model_state(
            client,
            loaded=False,
            timeout_seconds=2.0,
            poll_seconds=0.25,
        )
        report["initial_qwen_absence"] = initial_absence
        report["sequence"].append(
            {"at": utc_now(), "stage": "initial_qwen_absence", "passed": initial_absence["passed"]}
        )
        if initial_absence.get("passed") is not True or blackwell.qwen_loaded():
            raise qwen.AcceptanceSafetyError(
                "Qwen was resident before the serialized harness; lifecycle ownership refused"
            )

        first_nonce, second_nonce = qwen.new_lifecycle_nonce_pair()
        qwen_owned = True
        first = qwen_public_spoken_probe(client, "before_gpu_voice", nonce=first_nonce)
        report["first_qwen_response"] = first
        report["sequence"].append(
            {"at": utc_now(), "stage": "exact_promoted_qwen_response", "passed": first["passed"]}
        )
        if first.get("passed") is not True:
            raise qwen.AcceptanceSafetyError("first exact promoted Qwen response failed")

        unload = qwen.lifecycle_unload_probe(client, "before_blackwell_voice")
        report["qwen_unload_before_voice"] = unload
        report["sequence"].append(
            {"at": utc_now(), "stage": "qwen_unloaded_before_voice", "passed": unload["passed"]}
        )
        if unload.get("passed") is not True or blackwell.qwen_loaded():
            raise qwen.AcceptanceSafetyError("Qwen clean absence before GPU voice was not proven")
        qwen_owned = False

        released_spoken = first.get("released_spoken_text")
        payload, output = build_voice_payload(run_dir, str(released_spoken or ""))
        report["spoken_release"] = {
            "source": "first_qwen_response.strict_public_spoken_reply.SPOKEN",
            "released_fields": ["SPOKEN"],
            "released_text_sha256": payload["text_sha256"],
            "worker_channel": payload["channel"],
            "nonce_released_to_voice": False,
            "full_qwen_response_released_to_voice": False,
        }
        voice_monitor = QwenAbsenceMonitor(client)
        voice_monitor.start()
        try:
            worker_run = blackwell.run_worker(payload, timeout=worker_timeout_seconds)
        finally:
            voice_monitor_result = voice_monitor.stop()
            voice_monitor = None
        (run_dir / "worker_stdout.txt").write_text(
            str(worker_run.get("stdout") or ""), encoding="utf-8"
        )
        (run_dir / "worker_stderr.txt").write_text(
            str(worker_run.get("stderr") or ""), encoding="utf-8"
        )
        result = json.loads(str(worker_run.get("stdout") or ""))
        voice_validation = validate_voice_run(
            worker_run,
            result,
            output,
            voice_monitor_result,
        )
        report["blackwell_worker"] = {
            key: value for key, value in worker_run.items() if key not in {"stdout", "stderr"}
        }
        report["blackwell_synthesis_result"] = result
        report["blackwell_voice_validation"] = voice_validation
        report["sequence"].append(
            {
                "at": utc_now(),
                "stage": "eager_cuda_blackwell_voice_worker_exit_and_vram_release",
                "passed": voice_validation["passed"],
            }
        )
        if voice_validation.get("passed") is not True:
            raise qwen.AcceptanceSafetyError("serialized eager-CUDA Chatterbox proof failed")

        post_voice_absence = qwen.wait_for_model_state(client, loaded=False)
        report["qwen_absence_after_voice"] = post_voice_absence
        if post_voice_absence.get("passed") is not True or blackwell.qwen_loaded():
            raise qwen.AcceptanceSafetyError("Qwen was not absent after voice synthesis")

        report["installed_model_after_voice"] = qwen.validate_exact_install(client.tags())
        qwen_owned = True
        second = qwen_public_spoken_probe(client, "after_gpu_voice_reload", nonce=second_nonce)
        report["second_qwen_response"] = second
        second_unique = (
            first.get("expected_nonce") != second.get("expected_nonce")
            and first.get("observed_nonce") != second.get("observed_nonce")
        )
        report["sequence"].append(
            {
                "at": utc_now(),
                "stage": "same_digest_qwen_reload_second_response",
                "passed": second.get("passed") is True and second_unique,
            }
        )
        if second.get("passed") is not True or not second_unique:
            raise qwen.AcceptanceSafetyError("second exact Qwen response or unique reload nonce failed")
        if first.get("loaded_digest") != second.get("loaded_digest") or second.get("loaded_digest") != PINNED_DIGEST:
            raise qwen.AcceptanceSafetyError("Qwen digest changed across the serialized voice boundary")

        final_unload = qwen.lifecycle_unload_probe(client, "final_clean_unload")
        report["final_qwen_unload"] = final_unload
        report["sequence"].append(
            {"at": utc_now(), "stage": "final_clean_qwen_unload", "passed": final_unload["passed"]}
        )
        if final_unload.get("passed") is not True or blackwell.qwen_loaded():
            raise qwen.AcceptanceSafetyError("final Qwen unload was not clean")
        qwen_owned = False
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        if qwen_owned:
            try:
                cleanup = qwen.lifecycle_unload_probe(client, "exception_owned_qwen_cleanup")
                report["exception_qwen_cleanup"] = cleanup
                report["sequence"].append(
                    {"at": utc_now(), "stage": "exception_owned_qwen_cleanup", "passed": cleanup["passed"]}
                )
                qwen_owned = False
            except Exception as cleanup_exc:
                report["errors"].append(
                    f"cleanup:{type(cleanup_exc).__name__}: {cleanup_exc}"
                )
    finally:
        if voice_monitor is not None:
            voice_monitor_result = voice_monitor.stop()
        report.setdefault("qwen_absence_monitor", voice_monitor_result)
        cpu_after = cpu_sidecar_snapshot()
        report["cpu_sidecar_after"] = _cpu_summary(cpu_after)
        cpu_integrity = (
            cpu_after.get("non_venv_manifest_sha256") == cpu_before.get("non_venv_manifest_sha256")
            and cpu_after.get("pip_freeze_sha256") == cpu_before.get("pip_freeze_sha256")
            and (cpu_after.get("self_check") or {}).get("ready") is True
        )
        report["cpu_sidecar_unchanged_and_runnable"] = cpu_integrity
        protected_after = qwen.hash_protected_files()
        report["protected_after"] = protected_after
        report["protected_integrity"] = qwen.compare_protected_hashes(
            protected_before, protected_after
        )
        try:
            standalone_after = validate_standalone_attempt_05()
        except Exception as exc:
            standalone_after = {
                "attempt": STANDALONE_ATTEMPT,
                "status": "INVALID_AFTER_SEQUENCE",
                "error": f"{type(exc).__name__}: {exc}",
                "tree": tree_snapshot(STANDALONE_DIR) if STANDALONE_DIR.is_dir() else None,
            }
            report["errors"].append(
                f"standalone_attempt_05_after:{type(exc).__name__}: {exc}"
            )
        report["standalone_attempt_05_after"] = standalone_after
        immutable_after = {
            "sidecar_config_sha256": sha256_file(blackwell.CONFIG),
            "sidecar_worker_sha256": sha256_file(blackwell.WORKER),
        }
        report["immutable_inputs"] = {
            "before": immutable_before,
            "after": immutable_after,
            "passed": immutable_before == immutable_after
            and standalone_before["tree"]["tree_sha256"]
            == ((standalone_after.get("tree") or {}).get("tree_sha256")),
        }
        final_absence: dict[str, Any]
        try:
            final_absence = qwen.wait_for_model_state(
                client,
                loaded=False,
                timeout_seconds=2.0,
                poll_seconds=0.25,
            )
        except Exception as exc:
            final_absence = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
        report["final_qwen_absence"] = final_absence
        final_checks = {
            "first_exact_promoted_qwen_response": (report.get("first_qwen_response") or {}).get("passed") is True,
            "qwen_unloaded_before_voice": (report.get("qwen_unload_before_voice") or {}).get("passed") is True,
            "only_public_spoken_released": (report.get("spoken_release") or {}).get("released_fields") == ["SPOKEN"],
            "eager_cuda_blackwell_voice_passed": (report.get("blackwell_voice_validation") or {}).get("passed") is True,
            "qwen_absent_during_voice": (report.get("blackwell_voice_validation") or {}).get("qwen_absence_monitor", {}).get("passed") is True,
            "worker_exit_and_vram_release": (report.get("blackwell_voice_validation") or {}).get("checks", {}).get("clean_worker_exit_vram_return") is True,
            "same_digest_second_qwen_response": (report.get("second_qwen_response") or {}).get("passed") is True
            and (report.get("second_qwen_response") or {}).get("loaded_digest") == PINNED_DIGEST,
            "final_clean_qwen_unload": (report.get("final_qwen_unload") or {}).get("passed") is True
            and final_absence.get("passed") is True,
            "cpu_sidecar_unchanged_and_runnable": cpu_integrity,
            "protected_files_unchanged": (report.get("protected_integrity") or {}).get("passed") is True,
            "attempt_05_and_sidecar_inputs_unchanged": report["immutable_inputs"]["passed"] is True,
        }
        report["checks"] = final_checks
        report["issues"].extend(key for key, passed in final_checks.items() if not passed)
        report["issues"] = list(dict.fromkeys(report["issues"]))
        report["finished_at"] = utc_now()
        report["status"] = (
            "PASS" if not report["issues"] and not report["errors"] else "FAIL"
        )
        report_path = run_dir / "blackwell_qwen_serialized_acceptance.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        digest = sha256_file(report_path)
        report_path.with_suffix(".sha256").write_text(
            f"{digest}  {report_path.name}\n", encoding="ascii"
        )
    return report, run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the bounded append-only exact-Qwen -> eager-CUDA Kira voice -> exact-Qwen proof."
        )
    )
    parser.add_argument(
        "--execute-live-acceptance",
        action="store_true",
        help="Required explicit acknowledgement that serialized local Qwen and GPU voice inference will run.",
    )
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:11434/api/chat",
        help="Loopback Ollama endpoint only.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--worker-timeout-seconds", type=int, default=900)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.execute_live_acceptance:
        parser.error(
            "live inference is disabled by default; pass --execute-live-acceptance after reviewing the bounded plan"
        )
    if not 1 <= args.worker_timeout_seconds <= 900:
        parser.error("--worker-timeout-seconds must be between 1 and 900")
    try:
        report, run_dir = execute_serialized_acceptance(
            attempt=args.attempt,
            endpoint=args.endpoint,
            timeout_seconds=args.timeout_seconds,
            worker_timeout_seconds=args.worker_timeout_seconds,
        )
    except (qwen.AcceptanceSafetyError, qwen.LocalOllamaError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": report["status"],
                "evidence": str(
                    run_dir / "blackwell_qwen_serialized_acceptance.json"
                ),
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
