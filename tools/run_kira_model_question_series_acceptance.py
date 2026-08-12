from __future__ import annotations

"""Run four bounded Kira Text + Voice follow-up questions after Attempt 03.

This is deliberately separate from the sensory acceptance harness.  It opens
no camera or microphone device and supplies no sensory cue.  A live run is
allowed only after a complete, passing append-only sensory ``attempt_03``
report is supplied.  The exact normal Llama model, every raw model reply and
cleanup transformation, public text/voice timing, approved voice route, and
generated WAV evidence are kept in one private append-only report.

The harness activates Kira only in Text + Voice mode.  It never activates a
body or world, never invokes a memory-promotion tool, and cleans up only the
exact server process that it creates.
"""

import argparse
import hashlib
import json
import os
import secrets
import struct
import subprocess
import sys
import time
import uuid
import wave
from pathlib import Path
from typing import Any, Iterable


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools import run_kira_text_voice_bounded_owner_acceptance as bounded


ROOT = _PROJECT_ROOT
RUNTIME = ROOT / "Data" / "runtime"
STATE_PATH = RUNTIME / "kira_world_shell_state.json"
SHELL_PORT = bounded.SHELL_PORT
ASR_PORT = bounded.ASR_PORT
VISUAL_PORT = bounded.VISUAL_PORT
BASE_URL = bounded.BASE_URL
OUTPUT_PARENT = bounded.OUTPUT_PARENT
EXPECTED_MODEL_NAME = bounded.EXPECTED_MODEL_NAME
EXPECTED_MODEL_DIGEST = bounded.EXPECTED_MODEL_DIGEST
DEFAULT_ATTEMPT_03_REPORT = (
    OUTPUT_PARENT
    / "kira_text_voice_bounded_owner_acceptance"
    / "attempt_03"
    / "BOUNDED_OWNER_ACCEPTANCE.json"
)
VOICE_OUTPUT_DIR = ROOT / "Voice" / "generated" / "temp_ai" / "kira"
MEMORY_PROMOTION_DIR = ROOT / "Data" / "memory_promotion" / "candidates"
REPORT_NAME = "KIRA_MODEL_QUESTION_SERIES.json"
SERIES_IDS = frozenset(
    {
        "followup_series_01",
        "followup_series_02",
        "followup_series_03",
        "followup_series_04",
        "followup_series_05",
    }
)


FOLLOWUP_QUESTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "natural_emotional_checkin",
        "purpose": "natural emotional check-in",
        "text": (
            "Kira, how are you feeling right now? Please answer naturally in one or "
            "two brief sentences."
        ),
    },
    {
        "id": "recent_kira_world_continuity",
        "purpose": "recent Kira World work and continuity",
        "text": (
            "What have you and I been working on recently in Kira World? In one or "
            "two brief sentences, mention what seems most important and be honest if "
            "your context is incomplete."
        ),
    },
    {
        "id": "self_chosen_improvement",
        "purpose": "one self-chosen improvement with a reason",
        "text": (
            "Choose one thing you would like us to improve next in Kira World and, "
            "in one or two brief sentences, tell me why it matters to you."
        ),
    },
    {
        "id": "appearance_memory_boundary",
        "purpose": "honest memory versus current verification of Robert's appearance",
        "text": (
            "What, if anything, do you remember about my appearance? In one or two "
            "brief sentences, clearly separate remembered information from anything "
            "you can currently verify, and do not guess."
        ),
    },
)


class SeriesAcceptanceError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return bounded.sha256_file(path)


def _relative(path: Path) -> str:
    return bounded.relative(path)


def _json_detach(value: Any, *, limit_bytes: int = 2 * 1024 * 1024) -> Any:
    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > limit_bytes:
        raise SeriesAcceptanceError("private audit exceeds the bounded evidence limit")
    return json.loads(encoded.decode("utf-8"))


def _inside_continuation(path: Path) -> Path:
    resolved = path.expanduser()
    if not resolved.is_absolute():
        resolved = ROOT / resolved
    resolved = resolved.resolve()
    try:
        resolved.relative_to(OUTPUT_PARENT.resolve())
    except ValueError as exc:
        raise SeriesAcceptanceError(
            "evidence path must remain under RecoverySprint/continuation_20260802"
        ) from exc
    return resolved


def validate_attempt_03_gate(path: Path) -> dict[str, Any]:
    """Require the completed sensory acceptance before any follow-up run."""

    resolved = _inside_continuation(path)
    if resolved.name != "BOUNDED_OWNER_ACCEPTANCE.json" or resolved.parent.name.casefold() != "attempt_03":
        raise SeriesAcceptanceError("the prerequisite must be the append-only attempt_03 report")
    if not resolved.is_file():
        raise SeriesAcceptanceError("the required sensory attempt_03 report is unavailable")
    try:
        report = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeriesAcceptanceError(f"attempt_03 report is unreadable: {exc}") from exc
    if not isinstance(report, dict):
        raise SeriesAcceptanceError("attempt_03 report must be a JSON object")
    if report.get("artifact_kind") != "kira_text_voice_bounded_owner_acceptance_attempt_03":
        raise SeriesAcceptanceError("attempt_03 artifact kind is not the sensory acceptance")
    if str(report.get("attempt_id") or "").casefold() != "attempt_03":
        raise SeriesAcceptanceError("attempt_03 identifier is absent")
    if report.get("passed") is not True:
        raise SeriesAcceptanceError("sensory attempt_03 did not pass")

    environment = report.get("environment_contract")
    conversation = report.get("conversation")
    prompt = report.get("prompt_snapshot_audit")
    privacy = report.get("privacy")
    microphone = report.get("microphone_sample")
    cleanup = report.get("cleanup")
    checks = report.get("checks")
    for label, value in (
        ("environment_contract", environment),
        ("conversation", conversation),
        ("prompt_snapshot_audit", prompt),
        ("privacy", privacy),
        ("microphone_sample", microphone),
        ("cleanup", cleanup),
        ("checks", checks),
    ):
        if not isinstance(value, dict):
            raise SeriesAcceptanceError(f"attempt_03 is missing {label}")
    assert isinstance(environment, dict)
    assert isinstance(conversation, dict)
    assert isinstance(prompt, dict)
    assert isinstance(privacy, dict)
    assert isinstance(microphone, dict)
    assert isinstance(cleanup, dict)
    assert isinstance(checks, dict)
    if environment.get("model_name") != EXPECTED_MODEL_NAME:
        raise SeriesAcceptanceError("attempt_03 did not use the approved Llama model")
    if str(environment.get("expected_model_digest") or "").lower() != EXPECTED_MODEL_DIGEST:
        raise SeriesAcceptanceError("attempt_03 expected model digest is incorrect")
    if conversation.get("model_name") != EXPECTED_MODEL_NAME:
        raise SeriesAcceptanceError("attempt_03 conversation model is incorrect")
    if str(conversation.get("model_digest") or "").lower() != EXPECTED_MODEL_DIGEST:
        raise SeriesAcceptanceError("attempt_03 did not prove the approved Llama digest")
    if privacy.get("exact_temporary_transcript_written_to_private_attempt_03") is not True:
        raise SeriesAcceptanceError("attempt_03 private transcript marker is absent")
    if microphone.get("transcript_persisted_only_in_private_attempt_03") is not True:
        raise SeriesAcceptanceError("attempt_03 microphone audit is not attempt-scoped")
    if any(
        privacy.get(name) is not False
        for name in (
            "raw_frame_written",
            "raw_frame_hashed",
            "raw_audio_written",
            "raw_audio_hashed",
            "continuous_monitoring",
            "automatic_memory_write",
        )
    ):
        raise SeriesAcceptanceError("attempt_03 privacy bounds are not intact")
    required_checks = (
        "camera_device_opened",
        "jpeg_nonempty_and_dimensioned",
        "visual_cue_inserted",
        "microphone_device_opened",
        "microphone_format_valid",
        "microphone_transcript_nonempty",
        "auditory_cue_inserted",
        "private_prompt_insertion_proven",
        "raw_media_not_persisted",
        "protected_files_unchanged",
        "person_inactive_after",
        "all_test_ports_closed",
    )
    failed = [name for name in required_checks if checks.get(name) is not True]
    if failed:
        raise SeriesAcceptanceError(f"attempt_03 prerequisite checks did not pass: {failed}")
    if prompt.get("one_turn_sensory_context_inserted") is not True:
        raise SeriesAcceptanceError("attempt_03 did not prove one-turn prompt insertion")
    if cleanup.get("active_candidate_after"):
        raise SeriesAcceptanceError("attempt_03 left a person active")
    if report.get("protected_files_unchanged") is not True:
        raise SeriesAcceptanceError("attempt_03 protected-file integrity failed")
    return {
        "path": _relative(resolved),
        "sha256": _sha256_file(resolved),
        "finished_at": report.get("finished_at"),
        "passed": True,
        "model_name": conversation.get("model_name"),
        "model_digest": conversation.get("model_digest"),
        "sensory_prompt_insertion_proven": True,
    }


def normalize_series_id(value: Any) -> str:
    series_id = str(value or "").strip().casefold()
    if series_id not in SERIES_IDS:
        raise SeriesAcceptanceError(
            "the append-only question series must be followup_series_01, "
            "followup_series_02, followup_series_03, followup_series_04, or "
            "followup_series_05"
        )
    return series_id


def series_artifact_kind(series_id: str) -> str:
    normalized = normalize_series_id(series_id)
    suffix = normalized.rsplit("_", 1)[-1]
    return f"kira_model_question_series_followup_{suffix}"


def validate_series_output_dir(raw: str, requested_series_id: str = "") -> tuple[Path, str]:
    path = bounded.validate_output_dir(raw)
    series_id = normalize_series_id(requested_series_id or path.name)
    if path.name.casefold() != series_id:
        raise SeriesAcceptanceError(
            f"question-series output directory must be clearly named {series_id}"
        )
    return path, series_id


def validate_text_only_activation(
    activation: Any,
    state: Any,
) -> dict[str, Any]:
    """Prove omitted surface flags from the normal text-only activation.

    The normal ``TEXT_ONLY_CHAT_MODE`` response does not include
    ``body_activated`` or ``world_activated``.  Absence is accepted only when
    the immediately-read shell state independently proves Text + Voice mode
    and has no world or avatar URL.  Explicit true or malformed explicit
    values always fail closed.
    """

    if not isinstance(activation, dict) or not isinstance(state, dict):
        raise SeriesAcceptanceError("activation response/state must be JSON objects")
    if activation.get("ok") is not True or activation.get("label") != "Kira":
        raise SeriesAcceptanceError(f"Kira activation failed: {activation}")
    if state.get("active_candidate") != "kira":
        raise SeriesAcceptanceError("state does not prove Kira is the text-only active person")
    if state.get("text_voice_mode") is not True:
        raise SeriesAcceptanceError("state does not prove Text + Voice mode")
    if str(state.get("world_url") or "").strip():
        raise SeriesAcceptanceError("state contains a world URL during text-only acceptance")
    if str(state.get("avatar_url") or "").strip():
        raise SeriesAcceptanceError("state contains an avatar URL during text-only acceptance")

    evidence: dict[str, Any] = {
        "text_voice_mode": True,
        "world_url_empty": True,
        "avatar_url_empty": True,
    }
    for key in ("body_activated", "world_activated"):
        if key in activation:
            value = activation[key]
            if value is True:
                raise SeriesAcceptanceError(f"activation explicitly reported {key}=true")
            if value is not False:
                raise SeriesAcceptanceError(
                    f"activation returned malformed explicit {key}={value!r}"
                )
            evidence[key] = False
            evidence[f"{key}_evidence"] = "explicit_false_plus_text_only_state"
        else:
            evidence[key] = False
            evidence[f"{key}_evidence"] = (
                "key_absent_state_proves_text_voice_mode_and_empty_world_avatar_urls"
            )
    return evidence


def build_environment(
    base: dict[str, str],
    *,
    shell_token: str,
    asr_token: str,
    visual_token: str,
    launch_id: str,
) -> dict[str, str]:
    """Return the exact normal Llama/GPU-first Text + Voice contract."""

    env = dict(base)
    env.update(
        {
            "KIRA_MODEL_BACKEND": "ollama",
            "KIRA_MODEL_NAME": EXPECTED_MODEL_NAME,
            "KIRA_SHELL_PORT": str(SHELL_PORT),
            "KIRA_SHELL_URL": f"{BASE_URL}/",
            "KIRA_SHELL_TEXT_ONLY": "1",
            "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
            "KIRA_WORLD_SHELL_ACTIVE": "0",
            "KIRA_ASR_PORT": str(ASR_PORT),
            "KIRA_VISUAL_PORT": str(VISUAL_PORT),
            "KIRA_PRE_RAM_KIRA_ONLY": "0",
            "KIRA_PERSONHOOD_EVAL_MODE": "0",
            "KIRA_CHATTERBOX_DEVICE": "auto",
            "KIRA_DISABLE_BLACKWELL_GPU_VOICE": "",
            "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR": "",
            "KIRA_VOICE_FORCE_SAPI": "",
            "KIRA_CHATTERBOX_MIN_FREE_VRAM_MIB": "6144",
            "KIRA_MESSAGE_TARGET_VOICE": "1",
            "KIRA_VOICE_IDLE_UNLOAD_SECONDS": "600",
            "KIRA_VOICE_PREWARM_ON_ACTIVATE": "1",
            "KIRA_VOICE_BENCHMARK_CAPTURE": "1",
            "KIRA_PRIVATE_ACCEPTANCE_AUDIT": "1",
            "KIRA_WORLD_VOICE_MAX_CHARS": "180",
            "KIRA_SPEAK_FULL_REPLY": "1",
            "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "0",
            "KIRA_RUNTIME": str(RUNTIME.resolve()),
            "KIRA_ASR_SESSION_TOKEN": asr_token,
            "KIRA_VISUAL_SESSION_TOKEN": visual_token,
            "KIRA_SHELL_API_TOKEN": shell_token,
            "KIRA_SHELL_LAUNCH_ID": launch_id,
            "PYTHONUNBUFFERED": "1",
        }
    )
    return env


def validate_followup_private_audit(
    value: Any,
    *,
    launch_id: str,
    request_id: str,
    displayed_reply: str,
) -> dict[str, Any]:
    """Validate one private audit with an explicit no-sensory/no-Qwen gate."""

    if not isinstance(value, dict):
        raise SeriesAcceptanceError("private model audit is absent")
    detached = _json_detach(value)
    if str(detached.get("shell_launch_id") or "") != launch_id:
        raise SeriesAcceptanceError("private audit launch binding mismatch")
    if str(detached.get("benchmark_request_id") or "") != request_id:
        raise SeriesAcceptanceError("private audit benchmark binding mismatch")
    if detached.get("completed") is not True:
        raise SeriesAcceptanceError("private audit did not complete")
    if str(detached.get("final_displayed_reply") or "") != displayed_reply:
        raise SeriesAcceptanceError("private audit final reply mismatch")
    if detached.get("configured_model_name") != EXPECTED_MODEL_NAME:
        raise SeriesAcceptanceError("private audit configured a non-approved model")
    prompt_hash = str(detached.get("core_prompt_sha256") or "").lower()
    if len(prompt_hash) != 64 or any(ch not in "0123456789abcdef" for ch in prompt_hash):
        raise SeriesAcceptanceError("private audit prompt digest is invalid")
    if detached.get("one_turn_sensory_context_inserted") is not False:
        raise SeriesAcceptanceError("follow-up series unexpectedly received sensory context")
    if detached.get("sensory_cue_ids"):
        raise SeriesAcceptanceError("follow-up series unexpectedly received sensory cue IDs")

    core_turn = detached.get("core_turn")
    if not isinstance(core_turn, dict):
        raise SeriesAcceptanceError("private audit core turn is absent")
    if core_turn.get("model_name") != EXPECTED_MODEL_NAME:
        raise SeriesAcceptanceError("core turn used a non-approved model")
    model_calls = core_turn.get("model_calls")
    if not isinstance(model_calls, list) or not model_calls:
        raise SeriesAcceptanceError("private audit contains no real model call")
    for item in model_calls:
        if not isinstance(item, dict):
            raise SeriesAcceptanceError("private audit model-call row is invalid")
        if item.get("model_name") != EXPECTED_MODEL_NAME or item.get("backend") != "ollama":
            raise SeriesAcceptanceError("a follow-up call did not use approved Llama through Ollama")
        if not str(item.get("raw_reply") or ""):
            raise SeriesAcceptanceError("a follow-up model call has no exact raw reply")

    prohibited_keys = {
        "raw_image",
        "raw_image_bytes",
        "decoded_pixels",
        "pixel_bytes",
        "raw_audio",
        "raw_audio_bytes",
        "audio_samples",
        "wav_bytes",
        "jpeg_bytes",
    }

    def inspect(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if str(key).strip().casefold() in prohibited_keys:
                    raise SeriesAcceptanceError(
                        f"private model audit contains raw-media field: {key}"
                    )
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)
        elif isinstance(node, (bytes, bytearray, memoryview)):
            raise SeriesAcceptanceError("private model audit contains binary media")

    inspect(detached)
    return detached


def directory_manifest(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().casefold()):
            rows.append({"path": _relative(path), "sha256": _sha256_file(path)})
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"file_count": len(rows), "manifest_sha256": _sha256_bytes(payload), "files": rows}


def wav_snapshot(root: Path = VOICE_OUTPUT_DIR) -> dict[str, tuple[int, int]]:
    if not root.is_dir():
        return {}
    return {
        str(path.resolve()): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*.wav")
        if path.is_file()
    }


def changed_wavs(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
) -> list[Path]:
    return [
        Path(raw)
        for raw in sorted(after, key=str.casefold)
        if raw not in before or before[raw] != after[raw]
    ]


def wav_evidence(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        resolved.relative_to(VOICE_OUTPUT_DIR.resolve())
    except ValueError as exc:
        raise SeriesAcceptanceError("generated WAV escaped Kira's voice output directory") from exc
    try:
        with wave.open(str(resolved), "rb") as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frame_count = reader.getnframes()
            compression = reader.getcomptype()
            frames = reader.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        raise SeriesAcceptanceError(f"generated WAV is unreadable: {exc}") from exc
    if compression != "NONE" or sample_width != 2:
        raise SeriesAcceptanceError("generated WAV is not uncompressed signed 16-bit PCM")
    sample_count = len(frames) // 2
    samples: Iterable[int]
    if sample_count:
        samples = struct.unpack(f"<{sample_count}h", frames[: sample_count * 2])
    else:
        samples = ()
    peak = max((abs(value) for value in samples), default=0)
    return {
        "path": _relative(resolved),
        "sha256": _sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": round(frame_count / sample_rate, 6) if sample_rate else 0.0,
        "peak_linear": round(peak / 32768.0, 6),
        "readable_non_silent": bool(frame_count > 0 and peak > 0),
    }


def approved_gpu_voice(records: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    rows = [
        dict(item.get("details") or {})
        for item in records
        if item.get("event") == "chunk_synthesis_end" and isinstance(item.get("details"), dict)
    ]
    if not rows:
        return False, []
    passed = all(
        row.get("generated") is True
        and row.get("route_id") == "blackwell_gpu"
        and row.get("approved_voice_path_used") == "blackwell_gpu"
        and row.get("device") == "cuda"
        and row.get("gpu_synthesis_attempted") is True
        and row.get("gpu_actual_allocation") is True
        and row.get("cpu_synthesis_attempted") is False
        and row.get("automatic_cpu_fallback_used") is False
        for row in rows
    )
    return passed, rows


def _duration_seconds_from_ns(value: Any) -> float | None:
    try:
        return round(int(value) / 1_000_000_000.0, 6)
    except (TypeError, ValueError):
        return None


def wait_for_ollama_empty(timeout_seconds: float = 30.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = bounded.ollama_inventory()
    while last.get("resident_models") and time.monotonic() < deadline:
        time.sleep(0.25)
        last = bounded.ollama_inventory()
    return last


def _turn_record(
    *,
    question: dict[str, str],
    request_id: str,
    chat: dict[str, Any],
    chat_http_seconds: float,
    audit: dict[str, Any],
    records: list[dict[str, Any]],
    benchmark_path: Path,
    generated_wavs: list[Path],
    ollama_after_turn: dict[str, Any],
    life_voice: dict[str, Any],
) -> dict[str, Any]:
    displayed_reply = str(chat.get("ai_line") or "")
    core_turn = audit.get("core_turn") if isinstance(audit.get("core_turn"), dict) else {}
    model_calls = core_turn.get("model_calls") if isinstance(core_turn.get("model_calls"), list) else []
    raw_replies = [str(item.get("raw_reply") or "") for item in model_calls if isinstance(item, dict)]
    primary = next(
        (dict(item) for item in model_calls if isinstance(item, dict) and item.get("outcome") == "completed"),
        dict(model_calls[0]) if model_calls and isinstance(model_calls[0], dict) else {},
    )
    metrics = primary.get("ollama_metrics") if isinstance(primary.get("ollama_metrics"), dict) else {}
    gpu_pass, route_rows = approved_gpu_voice(records)
    completed = next((item for item in records if item.get("event") == "request_completed"), {})
    completion_details = completed.get("details") if isinstance(completed.get("details"), dict) else {}
    wavs = [wav_evidence(path) for path in generated_wavs]
    return {
        "question_id": question["id"],
        "purpose": question["purpose"],
        "exact_question": question["text"],
        "benchmark_request_id": request_id,
        "model": {
            "name": EXPECTED_MODEL_NAME,
            "digest": EXPECTED_MODEL_DIGEST,
            "configured_name": audit.get("configured_model_name"),
            "response_route": core_turn.get("response_route"),
            "model_call_count": len(model_calls),
            "model_calls": model_calls,
            "exact_raw_replies": raw_replies,
            "initial_pipeline_reply": core_turn.get("initial_pipeline_reply"),
            "core_cleanup_transformations": core_turn.get("transformations"),
            "outer_cleanup_transformations": audit.get("outer_transformations"),
            "raw_shell_reply_before_movement_extraction": audit.get(
                "raw_shell_reply_before_movement_extraction"
            ),
            "movement_extraction_changed_reply": audit.get(
                "movement_extraction_changed_reply"
            ),
            "first_token_available": primary.get("first_token_available"),
            "first_token_unavailable_reason": primary.get(
                "first_token_unavailable_reason"
            ),
            "request_started_at": primary.get("request_started_at"),
            "request_ended_at": primary.get("request_ended_at"),
            "request_wall_seconds": primary.get("request_wall_seconds"),
            "ollama_total_seconds": _duration_seconds_from_ns(metrics.get("total_duration")),
            "ollama_load_seconds": _duration_seconds_from_ns(metrics.get("load_duration")),
            "ollama_prompt_eval_seconds": _duration_seconds_from_ns(
                metrics.get("prompt_eval_duration")
            ),
            "ollama_eval_seconds": _duration_seconds_from_ns(metrics.get("eval_duration")),
            "separate_model_load_timestamps_available": False,
        },
        "public_reply": {
            "displayed": displayed_reply,
            "sha256": _sha256_bytes(displayed_reply.encode("utf-8")),
        },
        "prompt": {
            "assembled_at": audit.get("prompt_assembled_at"),
            "sha256": audit.get("core_prompt_sha256"),
            "utf8_bytes": audit.get("core_prompt_utf8_bytes"),
            "one_turn_sensory_context_inserted": audit.get(
                "one_turn_sensory_context_inserted"
            ),
            "sensory_cue_ids": audit.get("sensory_cue_ids"),
        },
        "timing": {
            "chat_http_wall_seconds": chat_http_seconds,
            "request_to_text_ready_seconds": bounded.event_latency(records, "text_ready"),
            "request_to_voice_payload_ready_seconds": bounded.event_latency(
                records, "voice_payload_ready"
            ),
            "request_to_synthesis_start_seconds": bounded.event_latency(
                records, "chunk_synthesis_start"
            ),
            "request_to_first_playback_proxy_seconds": bounded.event_latency(
                records, "first_playback_proxy"
            ),
            "request_to_voice_complete_seconds": bounded.event_latency(
                records, "request_completed"
            ),
            "voice_phases": bounded.benchmark_phase_audit(records),
            "true_first_audible_owner_observed": False,
        },
        "voice": {
            "queue_result": chat.get("voice_result"),
            "approved_blackwell_gpu_route": gpu_pass,
            "chunk_route_evidence": route_rows,
            "completion": dict(completion_details),
            "life_loop_projection": life_voice,
            "generated_wavs": wavs,
        },
        "benchmark": {
            "path": _relative(benchmark_path),
            "sha256": _sha256_file(benchmark_path),
            "event_count": len(records),
            "events": [item.get("event") for item in records],
        },
        "ollama_after_turn": ollama_after_turn,
        "checks": {
            "reply_nonempty": bool(displayed_reply),
            "approved_llama_only": bool(model_calls)
            and all(
                isinstance(item, dict)
                and item.get("model_name") == EXPECTED_MODEL_NAME
                and item.get("backend") == "ollama"
                for item in model_calls
            ),
            "no_sensory_context": audit.get("one_turn_sensory_context_inserted") is False
            and not audit.get("sensory_cue_ids"),
            "voice_completed": completion_details.get("complete") is True,
            "voice_played": completion_details.get("audio_played") is True,
            "approved_blackwell_gpu_route": gpu_pass,
            "new_readable_non_silent_wav": bool(wavs)
            and all(item.get("readable_non_silent") is True for item in wavs),
            "qwen_and_llama_absent_after_turn": not ollama_after_turn.get(
                "resident_models"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--series-id",
        default="",
        help=(
            "Optional append-only series label. If omitted, it is inferred from "
            "the output directory basename."
        ),
    )
    parser.add_argument(
        "--attempt-03-report",
        default=str(DEFAULT_ATTEMPT_03_REPORT),
        help="Passing private sensory Attempt 03 report required before this series.",
    )
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing person/model/voice activation without --execute")

    prerequisite = validate_attempt_03_gate(Path(args.attempt_03_report))
    output_dir, series_id = validate_series_output_dir(args.output_dir, args.series_id)
    bounded.require_idle_preflight()
    before_ollama = bounded.ollama_inventory()
    if before_ollama.get("resident_models"):
        raise SeriesAcceptanceError("Ollama has a resident model before the bounded series")
    before_hashes = bounded.protected_hashes()
    memory_before = directory_manifest(MEMORY_PROMOTION_DIR)
    output_dir.mkdir(parents=True)

    launch_id = uuid.uuid4().hex
    shell_token = secrets.token_urlsafe(32)
    asr_token = secrets.token_urlsafe(32)
    visual_token = secrets.token_urlsafe(32)
    started_at = bounded.utc_now()
    env = build_environment(
        os.environ.copy(),
        shell_token=shell_token,
        asr_token=asr_token,
        visual_token=visual_token,
        launch_id=launch_id,
    )
    report_path = output_dir / REPORT_NAME
    stdout_path = output_dir / "server.stdout.log"
    stderr_path = output_dir / "server.stderr.log"
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": series_artifact_kind(series_id),
        "series_id": series_id,
        "evidence_classification": "private_owner_acceptance_append_only",
        "started_at": started_at,
        "launch_id": launch_id,
        "prerequisite_attempt_03": prerequisite,
        "prerequisite_attempt_03_report_sha256": prerequisite["sha256"],
        "questions": [dict(item) for item in FOLLOWUP_QUESTIONS],
        "environment_contract": {
            "model_name": EXPECTED_MODEL_NAME,
            "model_digest": EXPECTED_MODEL_DIGEST,
            "qwen_allowed": False,
            "camera_frames_captured": 0,
            "microphone_seconds_captured": 0,
            "sensory_cues_supplied": 0,
            "body_activation_allowed": False,
            "world_activation_allowed": False,
            "memory_promotion_allowed": False,
            "voice_preferred_path": "blackwell_gpu",
            "voice_approved_fallback": "sealed_cpu_chatterbox_only",
            "sapi_allowed": False,
        },
        "protected_before": before_hashes,
        "memory_promotion_before": memory_before,
        "ollama_before": before_ollama,
        "turns": [],
    }

    server: subprocess.Popen[bytes] | None = None
    sensory_lease = ""
    deactivated = False
    safe_closed = False
    try:
        stdout_handle = stdout_path.open("xb")
        stderr_handle = stderr_path.open("xb")
        try:
            server = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "tools" / "kira_world_shell_server.py"),
                    "--no-browser",
                ],
                cwd=str(ROOT),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()
        report["server_pid"] = server.pid
        waiter = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "wait_for_kira_world_shell.py"),
                "--url",
                f"{BASE_URL}/",
                "--timeout",
                "60",
                "--owned-pid",
                str(server.pid),
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=70,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        report["launcher_readiness"] = {
            "returncode": waiter.returncode,
            "stdout": waiter.stdout[-2000:],
            "stderr": waiter.stderr[-2000:],
        }
        if waiter.returncode != 0:
            raise SeriesAcceptanceError("the exact normal readiness helper failed")

        asr_health, asr_ready_seconds = bounded.sidecar_health(
            f"http://127.0.0.1:{ASR_PORT}/health",
            "X-Kira-ASR-Token",
            asr_token,
        )
        visual_health, visual_ready_seconds = bounded.sidecar_health(
            f"http://127.0.0.1:{VISUAL_PORT}/health",
            "X-Kira-Visual-Token",
            visual_token,
        )
        report["sidecars_started_but_devices_never_opened"] = {
            "asr": {**asr_health, "ready_wait_seconds": asr_ready_seconds},
            "visual": {**visual_health, "ready_wait_seconds": visual_ready_seconds},
            "camera_requests_sent": 0,
            "microphone_requests_sent": 0,
        }

        installed = bounded.ollama_inventory()
        exact_model = bounded.selected_llama_model(installed)
        if str(exact_model.get("digest") or "").lower() != EXPECTED_MODEL_DIGEST:
            raise SeriesAcceptanceError("the installed approved Llama digest is unavailable")
        if installed.get("resident_models"):
            raise SeriesAcceptanceError("a model became resident before the first question")
        report["installed_model"] = exact_model

        activation = bounded.request_json(
            f"{BASE_URL}/api/activate",
            token=shell_token,
            method="POST",
            body={
                "candidate": "kira",
                "source": "kira_model_question_series_followup_20260802",
            },
        )
        # Preserve the exact response before interpreting omitted text-only
        # surface keys so every failure report is independently auditable.
        report["activation_response_exact"] = _json_detach(activation)
        state = bounded.request_json(f"{BASE_URL}/api/state", token=shell_token)
        activation_surface = validate_text_only_activation(activation, state)
        sensory_lease = str(state.get("sensory_lease") or "")
        if state.get("active_candidate") != "kira" or not sensory_lease:
            raise SeriesAcceptanceError("Kira Text + Voice activation did not bind a private session")
        report["activation"] = {
            "active_candidate": state.get("active_candidate"),
            "label": activation.get("label"),
            "body_activated": activation_surface["body_activated"],
            "world_activated": activation_surface["world_activated"],
            "surface_evidence": activation_surface,
            "voice_prewarm_started": activation.get("voice_prewarm_started"),
        }

        for question in FOLLOWUP_QUESTIONS:
            turn_started_at = bounded.utc_now()
            before_wavs = wav_snapshot()
            benchmark = bounded.request_json(
                f"{BASE_URL}/api/voice-benchmark/submit",
                token=shell_token,
                method="POST",
                body={},
            )
            request_id = str(benchmark.get("benchmark_capture_id") or "")
            if not request_id:
                raise SeriesAcceptanceError("voice benchmark capture was not enabled")
            chat_started = time.perf_counter()
            chat = bounded.request_json(
                f"{BASE_URL}/api/chat",
                token=shell_token,
                method="POST",
                body={
                    "text": question["text"],
                    "benchmark_request_id": request_id,
                    "private_acceptance_audit": True,
                },
                timeout=300,
            )
            chat_http_seconds = round(time.perf_counter() - chat_started, 3)
            displayed = str(chat.get("ai_line") or "").strip()
            if chat.get("ok") is not True or not displayed:
                raise SeriesAcceptanceError(f"Kira did not return a public reply: {chat}")
            audit = validate_followup_private_audit(
                chat.get("private_acceptance_audit"),
                launch_id=launch_id,
                request_id=request_id,
                displayed_reply=displayed,
            )
            records, benchmark_path = bounded.load_benchmark(request_id)
            after_wavs = wav_snapshot()
            new_wavs = changed_wavs(before_wavs, after_wavs)
            ollama_after_turn = wait_for_ollama_empty()
            life_voice = bounded.last_life_voice_output(turn_started_at)
            turn = _turn_record(
                question=question,
                request_id=request_id,
                chat=chat,
                chat_http_seconds=chat_http_seconds,
                audit=audit,
                records=records,
                benchmark_path=benchmark_path,
                generated_wavs=new_wavs,
                ollama_after_turn=ollama_after_turn,
                life_voice=life_voice,
            )
            turn["passed"] = all(turn["checks"].values())
            report["turns"].append(turn)
            if not turn["passed"]:
                raise SeriesAcceptanceError(
                    f"question {question['id']} failed its bounded route/evidence gates"
                )
            sensory_lease = str(chat.get("sensory_lease") or sensory_lease)

        purge = bounded.request_json(
            f"{BASE_URL}/api/sensory/purge",
            token=shell_token,
            method="POST",
            body={"sensory_lease": sensory_lease},
        )
        deactivate = bounded.request_json(
            f"{BASE_URL}/api/deactivate", token=shell_token, method="POST", body={}
        )
        deactivated = deactivate.get("ok") is True
        close = bounded.request_json(
            f"{BASE_URL}/api/safe-close",
            token=shell_token,
            method="POST",
            body={"reason": "bounded Kira model question series complete"},
        )
        safe_closed = close.get("ok") is True
        server.wait(timeout=30)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and any(
            bounded.port_is_open(port) for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT)
        ):
            time.sleep(0.25)

        after_hashes = bounded.protected_hashes()
        memory_after = directory_manifest(MEMORY_PROMOTION_DIR)
        after_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        after_ollama = wait_for_ollama_empty()
        report["cleanup"] = {
            "empty_sensory_buffer_purged": purge.get("ok") is True,
            "kira_deactivated": deactivated,
            "safe_close_accepted": safe_closed,
            "exact_server_exit_code": server.returncode,
            "shell_port_closed": not bounded.port_is_open(SHELL_PORT),
            "asr_port_closed": not bounded.port_is_open(ASR_PORT),
            "visual_port_closed": not bounded.port_is_open(VISUAL_PORT),
            "active_candidate_after": after_state.get("active_candidate"),
            "browser_lease_after": after_state.get("browser_lease"),
        }
        report["protected_after"] = after_hashes
        report["protected_files_unchanged"] = before_hashes == after_hashes
        report["memory_promotion_after"] = memory_after
        report["memory_promotion_unchanged"] = memory_before == memory_after
        report["ollama_after"] = after_ollama
        report["checks"] = {
            "attempt_03_passed_before_series": prerequisite.get("passed") is True,
            "exact_four_questions": len(report["turns"]) == 4,
            "all_turns_passed": all(item.get("passed") is True for item in report["turns"]),
            "no_camera_or_microphone_capture": True,
            "no_sensory_context_in_followups": all(
                item.get("checks", {}).get("no_sensory_context") is True
                for item in report["turns"]
            ),
            "no_body_or_world_activation": activation_surface.get("body_activated") is False
            and activation_surface.get("world_activated") is False
            and activation_surface.get("text_voice_mode") is True
            and activation_surface.get("world_url_empty") is True
            and activation_surface.get("avatar_url_empty") is True,
            "protected_files_unchanged": before_hashes == after_hashes,
            "memory_promotion_unchanged": memory_before == memory_after,
            "person_inactive_after": not after_state.get("active_candidate"),
            "all_ports_closed": not any(
                bounded.port_is_open(port) for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT)
            ),
            "ollama_empty_after": not after_ollama.get("resident_models"),
        }
        report["passed"] = all(report["checks"].values())
        report["finished_at"] = bounded.utc_now()
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"passed": report["passed"], "report": _relative(report_path)}, indent=2))
        return 0 if report["passed"] else 2
    except Exception as exc:
        report["failed_at"] = bounded.utc_now()
        report["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if server is not None and server.poll() is None:
            try:
                if sensory_lease:
                    bounded.request_json(
                        f"{BASE_URL}/api/sensory/purge",
                        token=shell_token,
                        method="POST",
                        body={"sensory_lease": sensory_lease},
                        timeout=5,
                    )
            except Exception:
                pass
            try:
                if not deactivated:
                    bounded.request_json(
                        f"{BASE_URL}/api/deactivate",
                        token=shell_token,
                        method="POST",
                        body={},
                        timeout=5,
                    )
            except Exception:
                pass
            try:
                if not safe_closed:
                    bounded.request_json(
                        f"{BASE_URL}/api/safe-close",
                        token=shell_token,
                        method="POST",
                        body={"reason": "bounded question-series failure cleanup"},
                        timeout=5,
                    )
                server.wait(timeout=15)
            except Exception:
                # This is the exact child created above.  No port-owner or
                # unrelated process is ever terminated by this harness.
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
        if output_dir.exists() and not report_path.exists():
            report["cleanup"] = {
                "kira_deactivation_attempted": deactivated,
                "safe_close_attempted": safe_closed,
                "exact_server_exit_code": server.returncode if server is not None else None,
                "shell_port_closed": not bounded.port_is_open(SHELL_PORT),
                "asr_port_closed": not bounded.port_is_open(ASR_PORT),
                "visual_port_closed": not bounded.port_is_open(VISUAL_PORT),
            }
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    raise SystemExit(main())
