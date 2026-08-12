from __future__ import annotations

"""Run one append-only, private Qwen webcam + microphone acceptance.

The default invocation is inert.  A live run requires every explicit consent
flag.  The live path starts the normal local Text + Voice server without a
browser, activates only Kira's bounded text/voice surface, captures one fresh
JPEG and one short microphone sample, uses the exact approved Qwen digest for
the single still, proves Qwen unload, asks a two-turn exact-Qwen question series,
and measures the approved Blackwell voice route and playback proxy.

Raw camera and microphone payloads remain memory-only.  They are never written,
hashed, or copied into the report.  The exact temporary ASR transcript and the
derived one-turn sensory context are private owner-audit evidence.
"""

import argparse
import base64
import concurrent.futures
import datetime as dt
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.transient_qwen_vision import (  # noqa: E402
    QWEN_VISION_DIGEST,
    QWEN_VISION_MODEL,
    default_gpu_workload_probe,
)
from tools import run_kira_text_voice_bounded_owner_acceptance as bounded  # noqa: E402


TEXT_MODEL = QWEN_VISION_MODEL
TEXT_DIGEST = QWEN_VISION_DIGEST
LIVE_PARENT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "qwen_webcam_microphone_live_acceptance"
)
VOICE_WAV_ROOT = ROOT / "Voice" / "generated" / "temp_ai" / "kira"
REPORT_NAME = "QWEN_WEBCAM_MICROPHONE_ACCEPTANCE.json"
IMPLEMENTATION_FILES = (
    ROOT / "Tools" / "run_qwen_webcam_microphone_live_acceptance.py",
    ROOT / "Tools" / "run_kira_text_voice_bounded_owner_acceptance.py",
    ROOT / "Tools" / "kira_world_shell_server.py",
    ROOT / "Core" / "transient_qwen_vision.py",
    ROOT / "config" / "kira_text_voice_device_capture.json",
    ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json",
)
SHELL_PORT = bounded.SHELL_PORT
ASR_PORT = bounded.ASR_PORT
VISUAL_PORT = bounded.VISUAL_PORT
BASE_URL = bounded.BASE_URL
QUESTION_SERIES = (
    (
        "Kira, what can you see in the one current camera still, what can you "
        "hear in the microphone sample, and what remains uncertain? Answer "
        "naturally, and do not identify a person or sound source unless the "
        "evidence proves it."
    ),
    (
        "No second camera frame or microphone sample was captured. In one "
        "brief natural sentence, say whether you can see or hear anything new "
        "right now. Do not claim a body pose, recall, memory, or new perception."
    ),
)
CONFIRMATION_FLAGS = (
    "execute_live",
    "confirm_camera_microphone_use",
    "confirm_private_owner_audit",
    "confirm_no_active_blender",
    "confirm_speaker_playback",
)


class LiveAcceptanceError(RuntimeError):
    """A bounded live gate failed."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    return bounded.sha256_file(path)


def implementation_hashes() -> dict[str, str]:
    missing = [relative(path) for path in IMPLEMENTATION_FILES if not path.is_file()]
    if missing:
        raise LiveAcceptanceError(f"acceptance implementation file is missing: {missing}")
    return {relative(path): sha256_file(path) for path in IMPLEMENTATION_FILES}


def build_plan() -> dict[str, Any]:
    """Return the inert, reviewable execution contract."""

    return {
        "schema_version": 1,
        "artifact_kind": "qwen_webcam_microphone_live_acceptance_plan",
        "default_mode": "INERT_NO_LIVE_IO",
        "models": {
            "one_still_vision": {
                "name": QWEN_VISION_MODEL,
                "digest": QWEN_VISION_DIGEST,
                "coverage": "SINGLE_TRANSIENT_FRAME_ONLY",
                "unload_before_text": True,
            },
            "normal_text": {"name": TEXT_MODEL, "digest": TEXT_DIGEST},
            "voice": {
                "preferred_route": "blackwell_gpu",
                "required_device": "cuda",
                "sealed_cpu_is_only_approved_fallback": True,
                "generic_or_sapi_allowed": False,
            },
        },
        "serialized_order": [
            "idle_and_exact_model_preflight",
            "same_normal_server_command_no_browser",
            "activate_kira_text_voice_only_without_voice_prewarm",
            "one_directshow_jpeg_memory_only",
            "exact_qwen_one_still_and_monitored_gpu_use",
            "verify_qwen_ollama_unload_and_vram_return",
            "local_coarse_visual_cues_from_same_jpeg",
            "one_bounded_directshow_microphone_sample_memory_only",
            "cache_only_cpu_asr_and_unknown_source_cue",
            "exact_qwen_text_turn_with_all_fresh_cues",
            "approved_blackwell_voice_synthesis_and_playback_proxy",
            "second_no_new_capture_uncertainty_turn",
            "purge_deactivate_safe_close_and_integrity_check",
        ],
        "question_series": list(QUESTION_SERIES),
        "privacy": {
            "raw_frame_written": False,
            "raw_frame_hashed": False,
            "raw_microphone_audio_written": False,
            "raw_microphone_audio_hashed": False,
            "exact_asr_transcript_in_private_report": True,
            "identity_inference": False,
            "appearance_memory": False,
            "automatic_memory_write": False,
        },
        "truth_boundaries": {
            "webcam_led_is_machine_readable": False,
            "directshow_open_plus_nonempty_frame_is_only_a_green_light_proxy": True,
            "single_channel_audio_proves_speaker_identity": False,
            "one_still_proves_temporal_continuity": False,
            "nonstreaming_ollama_exposes_exact_first_token_timestamp": False,
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-plan", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--confirm-camera-microphone-use", action="store_true")
    parser.add_argument("--confirm-private-owner-audit", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--confirm-speaker-playback", action="store_true")
    parser.add_argument("--owner-observed-camera-indicator", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--ffmpeg", default=str(bounded.DEFAULT_FFMPEG))
    parser.add_argument("--camera-device", default="USB CAMERA")
    parser.add_argument("--camera-hold-seconds", type=float, default=3.0)
    parser.add_argument("--microphone-device", default="Microphone (USB CAMERA)")
    parser.add_argument("--microphone-seconds", type=float, default=8.0)
    return parser.parse_args(argv)


def validate_live_arguments(args: argparse.Namespace) -> Path:
    missing = [name for name in CONFIRMATION_FLAGS if not bool(getattr(args, name, False))]
    if missing:
        raise LiveAcceptanceError(
            "live execution requires every explicit confirmation: " + ", ".join(missing)
        )
    if not args.output_dir:
        raise LiveAcceptanceError("--output-dir is required for an append-only live run")
    if not 2.5 <= float(args.camera_hold_seconds) <= 4.0:
        raise LiveAcceptanceError("camera hold must remain between 2.5 and 4 seconds")
    if not 3.0 <= float(args.microphone_seconds) <= 12.0:
        raise LiveAcceptanceError("microphone duration must remain between 3 and 12 seconds")
    output = Path(args.output_dir).expanduser()
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    try:
        remainder = output.relative_to(LIVE_PARENT.resolve())
    except ValueError as exc:
        raise LiveAcceptanceError(
            "output must be under RecoverySprint/continuation_20260802/"
            "qwen_webcam_microphone_live_acceptance"
        ) from exc
    if len(remainder.parts) != 1 or not re.fullmatch(r"attempt_[0-9]{2}", remainder.name):
        raise LiveAcceptanceError("output must be one exact append-only attempt_NN directory")
    if output.exists():
        raise LiveAcceptanceError("append-only output directory already exists")
    ffmpeg = Path(args.ffmpeg).expanduser().resolve()
    if not ffmpeg.is_file():
        raise LiveAcceptanceError("the approved local ffmpeg executable is unavailable")
    return output


def build_server_environment(
    *,
    shell_token: str,
    asr_token: str,
    visual_token: str,
    launch_id: str,
) -> dict[str, str]:
    """Build the normal launcher-equivalent environment with Qwen opt-in."""

    env = os.environ.copy()
    env.update(
        {
            "KIRA_MODEL_BACKEND": "ollama",
            "KIRA_MODEL_NAME": TEXT_MODEL,
            "KIRA_MODEL_DIGEST": TEXT_DIGEST,
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
            # Qwen must own the GPU before any approved voice worker exists.
            "KIRA_VOICE_PREWARM_ON_ACTIVATE": "0",
            "KIRA_VOICE_BENCHMARK_CAPTURE": "1",
            "KIRA_PRIVATE_ACCEPTANCE_AUDIT": "1",
            "KIRA_WORLD_VOICE_MAX_CHARS": "220",
            "KIRA_SPEAK_FULL_REPLY": "1",
            "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "0",
            "KIRA_ENABLE_QWEN_ONE_STILL": "1",
            "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE": "0",
            "KIRA_RUNTIME": str(bounded.RUNTIME.resolve()),
            "KIRA_ASR_SESSION_TOKEN": asr_token,
            "KIRA_VISUAL_SESSION_TOKEN": visual_token,
            "KIRA_SHELL_API_TOKEN": shell_token,
            "KIRA_SHELL_LAUNCH_ID": launch_id,
            "PYTHONUNBUFFERED": "1",
        }
    )
    return env


def safe_environment_record(env: Mapping[str, str]) -> dict[str, str]:
    allowed = (
        "KIRA_MODEL_BACKEND",
        "KIRA_MODEL_NAME",
        "KIRA_SHELL_PORT",
        "KIRA_SHELL_TEXT_ONLY",
        "KIRA_TEXT_VOICE_CHAT_ACTIVE",
        "KIRA_WORLD_SHELL_ACTIVE",
        "KIRA_ASR_PORT",
        "KIRA_VISUAL_PORT",
        "KIRA_PERSONHOOD_EVAL_MODE",
        "KIRA_CHATTERBOX_DEVICE",
        "KIRA_DISABLE_BLACKWELL_GPU_VOICE",
        "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR",
        "KIRA_VOICE_FORCE_SAPI",
        "KIRA_CHATTERBOX_MIN_FREE_VRAM_MIB",
        "KIRA_MESSAGE_TARGET_VOICE",
        "KIRA_VOICE_PREWARM_ON_ACTIVATE",
        "KIRA_VOICE_BENCHMARK_CAPTURE",
        "KIRA_PRIVATE_ACCEPTANCE_AUDIT",
        "KIRA_ENABLE_QWEN_ONE_STILL",
        "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE",
    )
    return {key: str(env.get(key, "")) for key in allowed}


def ollama_json(method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if method not in {"GET", "POST"} or path not in {"/api/tags", "/api/ps"}:
        raise ValueError("the harness exposes only Ollama inventory requests")
    raw = None
    headers = {"Accept": "application/json", "Cache-Control": "no-store"}
    if payload is not None:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(
        "http://127.0.0.1:11434" + path,
        data=raw,
        headers=headers,
        method=method,
    )
    try:
        with urllib_request.build_opener(urllib_request.ProxyHandler({})).open(
            request, timeout=10
        ) as response:
            decoded = json.loads(response.read(4 * 1024 * 1024).decode("utf-8"))
    except (OSError, urllib_error.URLError, json.JSONDecodeError) as exc:
        raise LiveAcceptanceError(f"local Ollama inventory failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise LiveAcceptanceError("local Ollama inventory returned a non-object")
    return decoded


def exact_model_inventory() -> dict[str, Any]:
    tags = ollama_json("GET", "/api/tags")
    resident = ollama_json("GET", "/api/ps")
    installed = []
    for item in tags.get("models") if isinstance(tags.get("models"), list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("model") or "")
        if name == QWEN_VISION_MODEL:
            installed.append(
                {
                    "name": name,
                    "model": item.get("model"),
                    "digest": str(item.get("digest") or "").casefold(),
                    "size": item.get("size"),
                }
            )
    residents = []
    for item in resident.get("models") if isinstance(resident.get("models"), list) else []:
        if isinstance(item, dict):
            residents.append(
                {
                    "name": item.get("name"),
                    "model": item.get("model"),
                    "digest": item.get("digest"),
                    "size_vram": item.get("size_vram"),
                    "expires_at": item.get("expires_at"),
                }
            )
    return {"installed_exact_candidates": installed, "resident_models": residents}


def require_exact_models_and_idle() -> dict[str, Any]:
    inventory = exact_model_inventory()
    by_name = {str(item.get("name")): str(item.get("digest") or "") for item in inventory["installed_exact_candidates"]}
    if by_name.get(QWEN_VISION_MODEL) != QWEN_VISION_DIGEST:
        raise LiveAcceptanceError("the exact approved Qwen vision digest is not installed")
    if by_name.get(TEXT_MODEL) != TEXT_DIGEST:
        raise LiveAcceptanceError("the exact approved Qwen text digest is not installed")
    if inventory["resident_models"]:
        raise LiveAcceptanceError("an Ollama model is already resident; the harness will not unload an unrelated workload")
    active = default_gpu_workload_probe()
    if active:
        raise LiveAcceptanceError("GPU-affecting work is active: " + ", ".join(active))
    return inventory


def _nvidia_smi_path() -> str:
    found = shutil.which("nvidia-smi")
    if found:
        return found
    candidate = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
    if candidate.is_file():
        return str(candidate)
    raise LiveAcceptanceError("nvidia-smi is unavailable for Qwen/voice GPU telemetry")


def nvidia_snapshot() -> dict[str, Any]:
    command = [
        _nvidia_smi_path(),
        "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        raise LiveAcceptanceError("nvidia-smi telemetry failed: " + completed.stderr[-500:])
    rows = []
    for line in completed.stdout.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 5:
            continue
        try:
            rows.append(
                {
                    "index": int(fields[0]),
                    "name": fields[1],
                    "memory_used_mib": float(fields[2]),
                    "memory_total_mib": float(fields[3]),
                    "utilization_percent": float(fields[4]),
                }
            )
        except ValueError:
            continue
    if not rows:
        raise LiveAcceptanceError("nvidia-smi returned no parseable GPU row")
    return {"at_utc": utc_now(), "gpus": rows}


def _gpu_used(snapshot: Mapping[str, Any], index: int = 0) -> float:
    for row in snapshot.get("gpus") if isinstance(snapshot.get("gpus"), list) else []:
        if isinstance(row, dict) and int(row.get("index") or 0) == index:
            return float(row.get("memory_used_mib") or 0.0)
    return 0.0


def _gpu_util(snapshot: Mapping[str, Any], index: int = 0) -> float:
    for row in snapshot.get("gpus") if isinstance(snapshot.get("gpus"), list) else []:
        if isinstance(row, dict) and int(row.get("index") or 0) == index:
            return float(row.get("utilization_percent") or 0.0)
    return 0.0


def monitored_call(
    call: Callable[[], dict[str, Any]],
    *,
    sample_interval_seconds: float = 0.2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one blocking local request while sampling total GPU telemetry."""

    before = nvidia_snapshot()
    samples = [before]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call)
        while not future.done():
            time.sleep(sample_interval_seconds)
            samples.append(nvidia_snapshot())
        result = future.result()
    after = nvidia_snapshot()
    samples.append(after)
    baseline = _gpu_used(before)
    peak = max((_gpu_used(item) for item in samples), default=baseline)
    return result, {
        "before": before,
        "after_immediate": after,
        "sample_interval_seconds": sample_interval_seconds,
        "sample_count": len(samples),
        "baseline_used_mib": baseline,
        "peak_used_mib": peak,
        "peak_delta_mib": round(max(0.0, peak - baseline), 3),
        "peak_utilization_percent": max((_gpu_util(item) for item in samples), default=0.0),
        "samples": samples,
    }


def wait_for_vram_return(baseline_used_mib: float, *, tolerance_mib: float = 512.0) -> dict[str, Any]:
    deadline = time.monotonic() + 30.0
    samples = []
    returned = False
    final_inventory: dict[str, Any] = {}
    while time.monotonic() < deadline:
        sample = nvidia_snapshot()
        samples.append(sample)
        final_inventory = exact_model_inventory()
        returned = (
            not final_inventory["resident_models"]
            and _gpu_used(sample) <= float(baseline_used_mib) + tolerance_mib
        )
        if returned:
            break
        time.sleep(0.25)
    return {
        "returned": returned,
        "baseline_used_mib": float(baseline_used_mib),
        "tolerance_mib": float(tolerance_mib),
        "final_used_mib": _gpu_used(samples[-1]) if samples else None,
        "resident_models_after": final_inventory.get("resident_models", []),
        "samples": samples,
    }


def voice_wav_snapshot(root: Path = VOICE_WAV_ROOT) -> dict[str, tuple[int, int]]:
    if not root.is_dir():
        return {}
    return {
        str(path.resolve()): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*.wav")
        if path.is_file()
    }


def collect_new_voice_wavs(
    before: Mapping[str, tuple[int, int]],
    root: Path = VOICE_WAV_ROOT,
) -> list[dict[str, Any]]:
    after = voice_wav_snapshot(root)
    evidence = []
    for raw_path, signature in sorted(after.items()):
        if before.get(raw_path) == signature:
            continue
        path = Path(raw_path)
        payload = path.read_bytes()
        audit = bounded.pcm_wav_audit(payload)
        payload = b""
        evidence.append(
            {
                "path": relative(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "modified_ns": path.stat().st_mtime_ns,
                "wav": audit,
            }
        )
    return evidence


def classify_microphone_evidence(
    *,
    wav_audit: Mapping[str, Any],
    transcript: str,
    segments: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    speech_detected = bool(transcript.strip() and segments)
    if speech_detected:
        no_transcript_reason = ""
    elif not bool(wav_audit.get("non_silent")):
        no_transcript_reason = "CAPTURED_AUDIO_WAS_DIGITALLY_SILENT"
    elif not transcript.strip():
        no_transcript_reason = "NO_SPEECH_TRANSCRIPT_RETURNED_FROM_BOUNDED_ASR"
    else:
        no_transcript_reason = "NO_BOUNDED_SPEECH_SEGMENT_RETURNED"
    return {
        "voice_activity_detected": speech_detected,
        "speech_segment_count": len(segments),
        "source_attribution": "UNRESOLVED_SINGLE_CHANNEL_MIXTURE",
        "speaker_identity": "UNKNOWN",
        "background_vs_nearfield_distinction": "NOT_PROVEN",
        "podcast_or_media_identified": False,
        "robert_identified": False,
        "no_transcript_reason": no_transcript_reason,
    }


def second_turn_no_new_capture_truth(reply: str) -> bool:
    """Require a short no-new-perception answer without a memory claim."""

    clean = re.sub(r"\s+", " ", str(reply or "").strip()).casefold()
    if not clean or len(clean) > 240:
        return False
    if re.search(
        r"\b(?:remember|recall|memory|bedroom|brick wall|previous scene|"
        r"sitting|standing|lying|walking)\b",
        clean,
    ):
        return False
    if re.search(r"\bi (?:can|do) (?:see|hear)\b", clean):
        return False
    return bool(
        re.search(
            r"\b(?:no (?:fresh|new) sensory information|"
            r"(?:do not|don't) have (?:fresh|new) sensory information|"
            r"can(?:not|'t) (?:see|hear|perceive)|"
            r"nothing new|without another capture|no new (?:image|audio|capture))\b",
            clean,
        )
    )


def validate_private_audit(
    value: Any,
    *,
    launch_id: str,
    request_id: str,
    displayed_reply: str,
    expected_cue_ids: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LiveAcceptanceError("private model audit is absent")
    if str(value.get("shell_launch_id") or "") != launch_id:
        raise LiveAcceptanceError("private model audit launch binding mismatch")
    if str(value.get("benchmark_request_id") or "") != request_id:
        raise LiveAcceptanceError("private model audit request binding mismatch")
    if value.get("completed") is not True:
        raise LiveAcceptanceError("private model audit did not complete")
    if str(value.get("final_displayed_reply") or "") != displayed_reply:
        raise LiveAcceptanceError("private model audit displayed reply mismatch")
    cue_ids = sorted(str(item) for item in value.get("sensory_cue_ids") or [])
    if cue_ids != sorted(str(item) for item in expected_cue_ids):
        raise LiveAcceptanceError("private model audit cue binding mismatch")
    expected_context = bool(expected_cue_ids)
    if bool(value.get("one_turn_sensory_context_inserted")) != expected_context:
        raise LiveAcceptanceError("private model audit sensory-context truth mismatch")
    prompt_hash = str(value.get("core_prompt_sha256") or "").casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", prompt_hash):
        raise LiveAcceptanceError("private model audit prompt hash is invalid")
    core_turn = value.get("core_turn") if isinstance(value.get("core_turn"), dict) else {}
    model_calls = core_turn.get("model_calls") if isinstance(core_turn.get("model_calls"), list) else []
    if not model_calls or not any(
        str(item.get("raw_reply") or "") for item in model_calls if isinstance(item, dict)
    ):
        raise LiveAcceptanceError("private model audit lacks an exact raw model reply")
    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > 2 * 1024 * 1024:
        raise LiveAcceptanceError("private model audit exceeds the bounded size")
    prohibited = {
        "raw_image", "raw_image_bytes", "decoded_pixels", "pixel_bytes",
        "raw_audio", "raw_audio_bytes", "audio_samples", "wav_bytes", "jpeg_bytes",
    }

    def inspect(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if str(key).casefold() in prohibited:
                    raise LiveAcceptanceError(f"private audit contains raw-media field {key}")
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)
        elif isinstance(node, (bytes, bytearray, memoryview)):
            raise LiveAcceptanceError("private audit contains a binary payload")

    inspect(value)
    return json.loads(encoded.decode("utf-8"))


def _duration_from_ns(value: Any) -> float | None:
    try:
        return round(int(value) / 1_000_000_000.0, 6)
    except (TypeError, ValueError):
        return None


def project_model_audit(private: Mapping[str, Any]) -> dict[str, Any]:
    core = private.get("core_turn") if isinstance(private.get("core_turn"), dict) else {}
    calls = core.get("model_calls") if isinstance(core.get("model_calls"), list) else []
    primary = next(
        (
            dict(item)
            for item in calls
            if isinstance(item, dict) and item.get("outcome") == "completed"
        ),
        dict(calls[0]) if calls and isinstance(calls[0], dict) else {},
    )
    metrics = primary.get("ollama_metrics") if isinstance(primary.get("ollama_metrics"), dict) else {}
    first_token_available = bool(primary.get("first_token_available"))
    return {
        "configured_model_name": private.get("configured_model_name"),
        "actual_model_name": primary.get("model_name"),
        "expected_model_digest": TEXT_DIGEST,
        "request_started_at": primary.get("request_started_at"),
        "request_ended_at": primary.get("request_ended_at"),
        "request_wall_seconds": primary.get("request_wall_seconds"),
        "ollama_total_seconds": _duration_from_ns(metrics.get("total_duration")),
        "ollama_load_seconds": _duration_from_ns(metrics.get("load_duration")),
        "ollama_prompt_eval_seconds": _duration_from_ns(metrics.get("prompt_eval_duration")),
        "ollama_eval_seconds": _duration_from_ns(metrics.get("eval_duration")),
        "model_load_boundary": {
            "separate_start_end_available": False,
            "duration_available_from_ollama": metrics.get("load_duration") is not None,
            "reason": "nonstreaming Ollama reports load duration but not separate wall-clock boundaries",
        },
        "first_token": {
            "available": first_token_available,
            "at": primary.get("first_token_at") if first_token_available else None,
            "seconds": primary.get("first_token_seconds") if first_token_available else None,
            "unavailable_reason": primary.get("first_token_unavailable_reason")
            or ("nonstreaming response exposes only text-complete" if not first_token_available else ""),
        },
        "exact_raw_model_replies": [
            str(item.get("raw_reply") or "") for item in calls if isinstance(item, dict)
        ],
        "initial_pipeline_reply": core.get("initial_pipeline_reply"),
        "core_transformations": core.get("transformations"),
        "outer_transformations": private.get("outer_transformations"),
        "raw_shell_reply_before_movement_extraction": private.get(
            "raw_shell_reply_before_movement_extraction"
        ),
        "movement_extraction_changed_reply": private.get(
            "movement_extraction_changed_reply"
        ),
        "final_displayed_reply": private.get("final_displayed_reply"),
        "prompt": {
            "assembled_at": private.get("prompt_assembled_at"),
            "sha256": private.get("core_prompt_sha256"),
            "utf8_bytes": private.get("core_prompt_utf8_bytes"),
            "one_turn_sensory_context_inserted": private.get(
                "one_turn_sensory_context_inserted"
            ),
            "exact_one_turn_sensory_context": private.get("one_turn_sensory_context"),
            "sensory_cue_ids": private.get("sensory_cue_ids"),
            "sensory_modalities": private.get("sensory_modalities"),
            "sensory_cleanup": private.get("sensory_cleanup"),
        },
    }


def run_chat_turn(
    *,
    index: int,
    question: str,
    expected_cue_ids: Sequence[str],
    shell_token: str,
    launch_id: str,
    after_text_ready: Callable[[], None] | None = None,
) -> dict[str, Any]:
    # last_life_voice_output uses the existing +00:00 timestamp convention for
    # its bounded comparison, so retain that exact convention here.
    turn_started_at = bounded.utc_now()
    wavs_before = voice_wav_snapshot()
    benchmark = bounded.request_json(
        f"{BASE_URL}/api/voice-benchmark/submit",
        token=shell_token,
        method="POST",
        body={},
    )
    request_id = str(benchmark.get("benchmark_capture_id") or "")
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise LiveAcceptanceError("voice benchmark did not return a bound request ID")
    chat_started_at = utc_now()
    chat_started = time.perf_counter()
    chat = bounded.request_json(
        f"{BASE_URL}/api/chat",
        token=shell_token,
        method="POST",
        body={
            "text": question,
            "benchmark_request_id": request_id,
            "private_acceptance_audit": True,
        },
        timeout=360,
    )
    chat_ended_at = utc_now()
    chat_http_seconds = round(time.perf_counter() - chat_started, 6)
    displayed = str(chat.get("ai_line") or "").strip()
    if chat.get("ok") is not True or not displayed:
        raise LiveAcceptanceError(f"turn {index} returned no displayed reply")
    private = validate_private_audit(
        chat.get("private_acceptance_audit"),
        launch_id=launch_id,
        request_id=request_id,
        displayed_reply=displayed,
        expected_cue_ids=expected_cue_ids,
    )
    # The signed sensory lease is intentionally short-lived.  Allow the live
    # harness to purge already-consumed camera/microphone state immediately
    # after the exact private prompt audit, before slow voice synthesis can
    # cause the lease to expire.
    if after_text_ready is not None:
        after_text_ready()
    records, benchmark_path = bounded.load_benchmark(request_id, timeout_seconds=900)
    wavs = collect_new_voice_wavs(wavs_before)
    voice_route = bounded.last_life_voice_output(turn_started_at)
    ollama_after = exact_model_inventory()
    model = project_model_audit(private)
    if model["configured_model_name"] != TEXT_MODEL or model["actual_model_name"] != TEXT_MODEL:
        raise LiveAcceptanceError(f"turn {index} did not use the exact normal Qwen route")
    chunks = voice_route.get("voice_chunk_results") if isinstance(voice_route.get("voice_chunk_results"), list) else []
    approved_gpu = bool(chunks) and all(
        isinstance(item, dict)
        and item.get("approved_voice_path_used") == "blackwell_gpu"
        and item.get("route_id") == "blackwell_gpu"
        and item.get("device") == "cuda"
        and item.get("gpu_synthesis_attempted") is True
        and item.get("gpu_actual_allocation") is True
        and item.get("cpu_synthesis_attempted") is False
        and item.get("automatic_cpu_fallback_used") is False
        for item in chunks
    )
    return {
        "turn_index": index,
        "question": question,
        "question_sha256": bounded.sha256_bytes(question.encode("utf-8")),
        "expected_fresh_cue_ids": list(expected_cue_ids),
        "submitted_at_utc": turn_started_at,
        "chat_started_at_utc": chat_started_at,
        "text_complete_at_utc": chat_ended_at,
        "chat_http_wall_seconds": chat_http_seconds,
        "displayed_reply": displayed,
        "displayed_reply_sha256": bounded.sha256_bytes(displayed.encode("utf-8")),
        "voice_queue_immediate_result": chat.get("voice_result"),
        "benchmark_request_id": request_id,
        "benchmark": {
            "path": relative(benchmark_path),
            "sha256": sha256_file(benchmark_path),
            "events": [item.get("event") for item in records],
            "request_to_text_complete_seconds": bounded.event_latency(records, "text_ready"),
            "request_to_synthesis_start_seconds": bounded.event_latency(
                records, "chunk_synthesis_start"
            ),
            "request_to_playback_start_proxy_seconds": bounded.event_latency(
                records, "first_playback_proxy"
            ),
            "request_to_voice_complete_seconds": bounded.event_latency(
                records, "request_completed"
            ),
            "phase_timings": bounded.benchmark_phase_audit(records),
        },
        "model": model,
        "voice": {
            "route": voice_route,
            "approved_blackwell_gpu_only": approved_gpu,
            "sealed_cpu_fallback_used": any(
                bool(item.get("automatic_cpu_fallback_used"))
                for item in chunks
                if isinstance(item, dict)
            ),
            "generated_wavs": wavs,
            "generated_wavs_are_readable_non_silent": bool(wavs)
            and all(bool(item["wav"].get("non_silent")) for item in wavs),
            "playback_is_api_proxy_not_owner_hearing_proof": True,
        },
        "ollama_after_turn": ollama_after,
        "qwen_absent_after_turn": not any(
            str(item.get("name") or item.get("model") or "") == QWEN_VISION_MODEL
            for item in ollama_after["resident_models"]
        ),
    }


def _insert_local_visual_cue(
    *,
    jpeg: bytes,
    visual_token: str,
    shell_token: str,
    sensory_lease: str,
    activation_revision: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started_at = utc_now()
    started = time.perf_counter()
    derived = bounded.request_binary_json(
        f"http://127.0.0.1:{VISUAL_PORT}/api/derive-cues",
        jpeg,
        headers={
            "Content-Type": "image/jpeg",
            "X-Kira-Visual-Token": visual_token,
            "X-Kira-Person": "kira",
            "X-Kira-Activation-Revision": activation_revision,
            "X-Kira-Sensory-Lease": sensory_lease,
        },
        timeout=60,
    )
    ended_at = utc_now()
    if derived.get("ok") is not True:
        raise LiveAcceptanceError("local visual cue derivation failed")
    cues = derived.get("cues") if isinstance(derived.get("cues"), list) else []
    confidence = max(
        [0.1]
        + [
            max(0.0, min(1.0, float(item.get("confidence") or 0.0)))
            for item in cues
            if isinstance(item, dict)
        ]
    )
    fact = {"modality": "visual", "event": "non_identifying_local_frame_cues", "cues": cues}
    source = {
        "kind": "local_visual_perception_sidecar",
        "backend": str(derived.get("source") or ""),
        "person_session_bound": True,
    }
    insertion = bounded.request_json(
        f"{BASE_URL}/api/sensory/cue",
        token=shell_token,
        method="POST",
        body={
            "sensory_lease": sensory_lease,
            "fact": fact,
            "source": source,
            "observed_at": str(derived.get("observed_at") or ended_at),
            "confidence": confidence,
            "attributes": {
                "capture_reason": "qwen_webcam_microphone_live_acceptance",
                "identity_inference_performed": False,
                "automatic_spoken_response": False,
                "automatic_memory_write": False,
            },
        },
    )
    return derived, {
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "accepted": insertion.get("ok") is True,
        "cue_id": insertion.get("cue_id"),
        "private_attention_placeholder_id": insertion.get(
            "private_attention_placeholder_id"
        ),
        "exact_fact": fact,
        "exact_source": source,
        "buffer_stats_after": insertion.get("stats"),
    }


def _insert_microphone_cue(
    *,
    wav: bytes,
    asr_token: str,
    shell_token: str,
    sensory_lease: str,
    activation_revision: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started_at = utc_now()
    started = time.perf_counter()
    asr = bounded.request_binary_json(
        f"http://127.0.0.1:{ASR_PORT}/api/transcribe",
        wav,
        headers={
            "Content-Type": "audio/wav",
            "X-Kira-ASR-Token": asr_token,
            "X-Kira-Person": "kira",
            "X-Kira-Activation-Revision": activation_revision,
            "X-Kira-Sensory-Lease": sensory_lease,
        },
        timeout=180,
    )
    ended_at = utc_now()
    if asr.get("ok") is not True:
        raise LiveAcceptanceError("bounded ASR failed")
    transcript = str(asr.get("text") or "").strip()
    insertion: dict[str, Any] = {"ok": False, "reason": "empty_transcript", "cue_id": ""}
    fact: dict[str, Any] = {}
    source: dict[str, Any] = {}
    if transcript:
        fact = {
            "modality": "auditory",
            "event": "possible_speech",
            "speaker": "unknown",
            "source_attribution": "UNRESOLVED_SINGLE_CHANNEL_MIXTURE",
            "transcript": transcript,
        }
        source = {
            "kind": "local_microphone_asr",
            "model_id": str(asr.get("model_id") or ""),
            "person_session_bound": True,
        }
        insertion = bounded.request_json(
            f"{BASE_URL}/api/sensory/cue",
            token=shell_token,
            method="POST",
            body={
                "sensory_lease": sensory_lease,
                "fact": fact,
                "source": source,
                "observed_at": ended_at,
                "confidence": max(
                    0.0, min(1.0, float(asr.get("language_probability") or 0.5))
                ),
                "attributes": {
                    "language": str(asr.get("language") or ""),
                    "segment_count": len(asr.get("segments") or []),
                    "speaker_identity_proven": False,
                    "background_vs_nearfield_proven": False,
                    "automatic_spoken_response": False,
                    "automatic_memory_write": False,
                },
            },
        )
    return asr, {
        "asr_started_at_utc": started_at,
        "asr_ended_at_utc": ended_at,
        "asr_elapsed_seconds": round(time.perf_counter() - started, 6),
        "accepted": insertion.get("ok") is True,
        "cue_id": insertion.get("cue_id"),
        "private_attention_placeholder_id": insertion.get(
            "private_attention_placeholder_id"
        ),
        "exact_fact": fact,
        "exact_source": source,
        "buffer_stats_after": insertion.get("stats"),
        "no_transcript_reason": insertion.get("reason") if not transcript else "",
    }


def _protected_hashes() -> dict[str, str]:
    return bounded.protected_hashes()


def run_live(args: argparse.Namespace, output_dir: Path) -> int:
    ffmpeg = Path(args.ffmpeg).expanduser().resolve()
    bounded.require_idle_preflight()
    inventory_before = require_exact_models_and_idle()
    protected_before = _protected_hashes()
    output_dir.mkdir(parents=True)

    launch_id = uuid.uuid4().hex
    shell_token = secrets.token_urlsafe(32)
    asr_token = secrets.token_urlsafe(32)
    visual_token = secrets.token_urlsafe(32)
    env = build_server_environment(
        shell_token=shell_token,
        asr_token=asr_token,
        visual_token=visual_token,
        launch_id=launch_id,
    )
    stdout_path = output_dir / "server.stdout.log"
    stderr_path = output_dir / "server.stderr.log"
    report_path = output_dir / REPORT_NAME
    started_at = utc_now()
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "qwen_webcam_microphone_live_acceptance",
        "evidence_classification": "private_owner_acceptance_contains_temporary_asr_text",
        "started_at_utc": started_at,
        "launch_id": launch_id,
        "plan": build_plan(),
        "environment": safe_environment_record(env),
        "implementation_hashes_at_execution": implementation_hashes(),
        "models_before": inventory_before,
        "protected_before": protected_before,
        "privacy": {
            "raw_frame_written": False,
            "raw_frame_hashed": False,
            "raw_microphone_audio_written": False,
            "raw_microphone_audio_hashed": False,
            "identity_inference_performed": False,
            "appearance_memory_used": False,
            "automatic_memory_write": False,
        },
    }
    server: subprocess.Popen[bytes] | None = None
    sensory_lease = ""
    original_sensory_lease = ""
    activation_revision = ""
    visual_purged = False
    sensory_purged = False
    deactivated = False
    safe_closed = False
    jpeg = b""
    wav = b""
    encoded_jpeg = ""
    camera_capture: bounded.CaptureResult | None = None
    microphone_capture: bounded.CaptureResult | None = None

    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            server = subprocess.Popen(
                [sys.executable, str(ROOT / "tools" / "kira_world_shell_server.py"), "--no-browser"],
                cwd=str(ROOT),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        report["server_pid"] = server.pid
        readiness_started = time.perf_counter()
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
            "elapsed_seconds": round(time.perf_counter() - readiness_started, 6),
            "stdout": waiter.stdout[-2000:],
            "stderr": waiter.stderr[-2000:],
        }
        if waiter.returncode != 0:
            raise LiveAcceptanceError("the exact normal readiness helper failed")

        asr_health, asr_ready = bounded.sidecar_health(
            f"http://127.0.0.1:{ASR_PORT}/health", "X-Kira-ASR-Token", asr_token
        )
        visual_health, visual_ready = bounded.sidecar_health(
            f"http://127.0.0.1:{VISUAL_PORT}/health",
            "X-Kira-Visual-Token",
            visual_token,
        )
        report["sidecars"] = {
            "asr": {**asr_health, "ready_wait_seconds": asr_ready},
            "visual": {**visual_health, "ready_wait_seconds": visual_ready},
        }
        activation = bounded.request_json(
            f"{BASE_URL}/api/activate",
            token=shell_token,
            method="POST",
            body={"candidate": "kira", "source": "qwen_webcam_microphone_live_acceptance"},
        )
        state = bounded.request_json(f"{BASE_URL}/api/state", token=shell_token)
        sensory_lease = str(state.get("sensory_lease") or "")
        original_sensory_lease = sensory_lease
        activation_revision = str(
            ((state.get("sensory_session") or {}).get("activation_revision"))
            or state.get("last_activation_at")
            or ""
        )
        if (
            activation.get("ok") is not True
            or activation.get("label") != "Kira"
            or state.get("active_candidate") != "kira"
            or not sensory_lease
            or not activation_revision
        ):
            raise LiveAcceptanceError("Kira text/voice-only activation did not bind a sensory lease")
        report["activation"] = {
            "active_candidate": state.get("active_candidate"),
            "active_label": state.get("active_label"),
            "activation_revision": activation_revision,
            "body_activated": activation.get("body_activated", False),
            "world_activated": activation.get("world_activated", False),
            "voice_prewarm_started": activation.get("voice_prewarm_started"),
        }

        camera_capture = bounded.capture_one_jpeg(
            ffmpeg,
            args.camera_device,
            hold_seconds=float(args.camera_hold_seconds),
        )
        jpeg = camera_capture.payload
        jpeg_bytes = len(jpeg)
        jpeg_width, jpeg_height = bounded.jpeg_dimensions(jpeg)
        captured_at = camera_capture.ended_at_utc
        encoded_jpeg = base64.b64encode(jpeg).decode("ascii")
        qwen_before = exact_model_inventory()
        if qwen_before["resident_models"]:
            raise LiveAcceptanceError("Ollama was not empty immediately before Qwen")

        def qwen_call() -> dict[str, Any]:
            return bounded.request_json(
                f"{BASE_URL}/api/sensory/qwen-look",
                token=shell_token,
                method="POST",
                body={
                    "sensory_lease": sensory_lease,
                    "person_id": "kira",
                    "activation_revision": activation_revision,
                    "captured_at": captured_at,
                    "jpeg_base64": encoded_jpeg,
                },
                timeout=180,
            )

        qwen_result, qwen_gpu = monitored_call(qwen_call)
        encoded_jpeg = ""
        if (
            qwen_result.get("ok") is not True
            or qwen_result.get("model") != QWEN_VISION_MODEL
            or str(qwen_result.get("model_digest") or "").casefold() != QWEN_VISION_DIGEST
            or qwen_result.get("coverage") != "SINGLE_TRANSIENT_FRAME_ONLY"
        ):
            raise LiveAcceptanceError("exact Qwen one-still response contract failed")
        qwen_after = exact_model_inventory()
        if qwen_after["resident_models"]:
            raise LiveAcceptanceError("Qwen did not unload before the text phase")
        qwen_vram_return = wait_for_vram_return(qwen_gpu["baseline_used_mib"])
        if not qwen_vram_return["returned"]:
            raise LiveAcceptanceError("Qwen VRAM did not return after unload")

        visual_derived, visual_insert = _insert_local_visual_cue(
            jpeg=jpeg,
            visual_token=visual_token,
            shell_token=shell_token,
            sensory_lease=sensory_lease,
            activation_revision=activation_revision,
        )
        camera_capture.payload = b""
        jpeg = b""
        report["camera"] = {
            "device": {
                "api": "DirectShow",
                "device_id": str(args.camera_device),
                "ffmpeg_selector": f"video={args.camera_device}",
            },
            "capture_started_at_utc": camera_capture.started_at_utc,
            "capture_ended_at_utc": camera_capture.ended_at_utc,
            "capture_elapsed_seconds": camera_capture.elapsed_seconds,
            "requested_hold_seconds": float(args.camera_hold_seconds),
            "device_opened": camera_capture.device_opened,
            "device_open_status": camera_capture.open_status,
            "ffmpeg_returncode": camera_capture.returncode,
            "captured_frame_count": 1,
            "encoded_byte_count": jpeg_bytes,
            "encoded_nonempty": jpeg_bytes > 0,
            "jpeg_dimensions": {"width": jpeg_width, "height": jpeg_height},
            "brightness_class": bounded.cue_value(
                visual_derived.get("cues"), "brightness_class"
            ),
            "motion_class": bounded.cue_value(
                visual_derived.get("cues"), "motion_class"
            ),
            "coarse_face_count": bounded.cue_value(
                visual_derived.get("cues"), "coarse_face_count"
            ),
            "exact_local_derived_cues": visual_derived.get("cues"),
            "local_cue_insertion": visual_insert,
            "green_light_proxy": {
                "proxy_kind": "DirectShow_open_plus_nonempty_encoded_frame",
                "proxy_passed": bool(camera_capture.device_opened and jpeg_bytes > 0),
                "hardware_indicator_machine_readable": False,
                "owner_reported_indicator_observed_during_this_run": bool(
                    args.owner_observed_camera_indicator
                ),
                "truth": (
                    "OWNER_OBSERVED"
                    if args.owner_observed_camera_indicator
                    else "NOT_OBSERVED_BY_HARNESS"
                ),
            },
            "raw_frame_persisted": False,
            "raw_frame_hashed": False,
        }
        report["qwen_one_still"] = {
            "before_inventory": qwen_before,
            "result": qwen_result,
            "gpu_telemetry": qwen_gpu,
            "after_inventory": qwen_after,
            "vram_return": qwen_vram_return,
            "exact_derived_scene_is_recorded_only_in_first_turn_private_prompt": True,
            "raw_frame_persisted": False,
            "raw_frame_hashed": False,
        }

        microphone_capture = bounded.capture_one_wav(
            ffmpeg,
            args.microphone_device,
            float(args.microphone_seconds),
        )
        wav = microphone_capture.payload
        wav_audit = bounded.pcm_wav_audit(wav)
        asr, audio_insert = _insert_microphone_cue(
            wav=wav,
            asr_token=asr_token,
            shell_token=shell_token,
            sensory_lease=sensory_lease,
            activation_revision=activation_revision,
        )
        microphone_capture.payload = b""
        wav = b""
        transcript = str(asr.get("text") or "").strip()
        segments = bounded.exact_asr_segments(asr.get("segments"))
        mic_classification = classify_microphone_evidence(
            wav_audit=wav_audit,
            transcript=transcript,
            segments=segments,
        )
        report["microphone"] = {
            "device": {
                "api": "DirectShow",
                "device_id": str(args.microphone_device),
                "ffmpeg_selector": f"audio={args.microphone_device}",
            },
            "capture_started_at_utc": microphone_capture.started_at_utc,
            "capture_ended_at_utc": microphone_capture.ended_at_utc,
            "capture_elapsed_seconds": microphone_capture.elapsed_seconds,
            "requested_capture_seconds": float(args.microphone_seconds),
            "device_opened": microphone_capture.device_opened,
            "device_open_status": microphone_capture.open_status,
            "ffmpeg_returncode": microphone_capture.returncode,
            "format_and_levels": wav_audit,
            "audio_bytes_received_by_asr": asr.get("audio_bytes_received"),
            "asr": {
                "model_id": asr.get("model_id"),
                "language": asr.get("language"),
                "language_probability": asr.get("language_probability"),
                "vad_filter_enabled": True,
                "vad_speech_detected": mic_classification["voice_activity_detected"],
                "exact_segments": segments,
                "exact_temporary_transcript": transcript,
                "transcript_sha256": (
                    bounded.sha256_bytes(transcript.encode("utf-8")) if transcript else None
                ),
                "transcript_is_private_attempt_evidence_only": True,
                "started_at_utc": audio_insert["asr_started_at_utc"],
                "ended_at_utc": audio_insert["asr_ended_at_utc"],
                "elapsed_seconds": audio_insert["asr_elapsed_seconds"],
            },
            "source_and_speaker_classification": mic_classification,
            "cue_insertion": audio_insert,
            "raw_audio_persisted": False,
            "raw_audio_hashed": False,
        }

        expected_cues = [
            str(qwen_result.get("cue_id") or ""),
            str(visual_insert.get("cue_id") or ""),
        ]
        if audio_insert.get("accepted") and audio_insert.get("cue_id"):
            expected_cues.append(str(audio_insert["cue_id"]))
        if not all(expected_cues):
            raise LiveAcceptanceError("one of the expected fresh sensory cue IDs is absent")
        report["vision_qwen_unloaded_before_qwen_text"] = {
            "proven": not qwen_after["resident_models"] and qwen_vram_return["returned"],
            "inventory": qwen_after,
            "vram_return": qwen_vram_return,
        }

        def purge_consumed_capture_state() -> None:
            nonlocal visual_purged, sensory_purged, sensory_lease
            visual_purge = bounded.request_binary_json(
                f"http://127.0.0.1:{VISUAL_PORT}/api/purge",
                b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-Kira-Visual-Token": visual_token,
                    "X-Kira-Person": "kira",
                    "X-Kira-Activation-Revision": activation_revision,
                    "X-Kira-Sensory-Lease": original_sensory_lease,
                },
                timeout=30,
            )
            visual_purged = visual_purge.get("ok") is True
            if not visual_purged:
                raise LiveAcceptanceError("visual sidecar did not purge consumed capture state")
            sensory_purge = bounded.request_json(
                f"{BASE_URL}/api/sensory/purge",
                token=shell_token,
                method="POST",
                body={"sensory_lease": original_sensory_lease},
            )
            sensory_purged = sensory_purge.get("ok") is True
            sensory_lease = str(sensory_purge.get("sensory_lease") or "")
            if not sensory_purged or not sensory_lease:
                raise LiveAcceptanceError("shell sensory buffer did not purge and renew")

        first_turn = run_chat_turn(
            index=1,
            question=QUESTION_SERIES[0],
            expected_cue_ids=expected_cues,
            shell_token=shell_token,
            launch_id=launch_id,
            after_text_ready=purge_consumed_capture_state,
        )
        turns = [
            first_turn,
            run_chat_turn(
                index=2,
                question=QUESTION_SERIES[1],
                expected_cue_ids=[],
                shell_token=shell_token,
                launch_id=launch_id,
            ),
        ]
        report["turns"] = turns
        first_context = str(turns[0]["model"]["prompt"]["exact_one_turn_sensory_context"] or "")
        report["prompt_context_proof"] = {
            "first_turn_context": first_context,
            "first_turn_cue_ids": turns[0]["model"]["prompt"]["sensory_cue_ids"],
            "contains_qwen_single_still": "Qwen transient one-still cue" in first_context,
            "contains_local_brightness": "brightness_class=" in first_context,
            "contains_microphone_unknown_source": (
                "unknown speaker" in first_context if transcript else True
            ),
            "temporary_transcript_present_exactly": (
                bool(transcript and json.dumps(transcript, ensure_ascii=False) in first_context)
                if transcript
                else True
            ),
            "second_turn_has_no_new_sensory_context": not bool(
                turns[1]["model"]["prompt"]["one_turn_sensory_context_inserted"]
            ),
            "second_turn_no_new_capture_truth": second_turn_no_new_capture_truth(
                turns[1]["displayed_reply"]
            ),
        }

        if not visual_purged or not sensory_purged:
            raise LiveAcceptanceError("consumed sensory state was not purged before voice")
        deactivate = bounded.request_json(
            f"{BASE_URL}/api/deactivate", token=shell_token, method="POST", body={}
        )
        deactivated = deactivate.get("ok") is True
        close = bounded.request_json(
            f"{BASE_URL}/api/safe-close",
            token=shell_token,
            method="POST",
            body={"reason": "Qwen webcam microphone live acceptance complete"},
        )
        safe_closed = close.get("ok") is True
        server.wait(timeout=30)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and any(
            bounded.port_is_open(port) for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT)
        ):
            time.sleep(0.25)
        after_state = json.loads(bounded.STATE_PATH.read_text(encoding="utf-8"))
        protected_after = _protected_hashes()
        ollama_after = exact_model_inventory()
        final_vram_return = wait_for_vram_return(
            float(report["qwen_one_still"]["gpu_telemetry"]["baseline_used_mib"])
        )
        final_gpu = nvidia_snapshot()
        report["cleanup"] = {
            "visual_sidecar_purged": visual_purged,
            "sensory_buffer_purged": sensory_purged,
            "kira_deactivated": deactivated,
            "safe_close_accepted": safe_closed,
            "server_exit_code": server.returncode,
            "shell_port_closed": not bounded.port_is_open(SHELL_PORT),
            "asr_port_closed": not bounded.port_is_open(ASR_PORT),
            "visual_port_closed": not bounded.port_is_open(VISUAL_PORT),
            "active_candidate_after": after_state.get("active_candidate"),
            "browser_lease_after": after_state.get("browser_lease"),
            "ollama_after": ollama_after,
            "final_vram_return_after_voice_and_server_close": final_vram_return,
            "final_gpu": final_gpu,
        }
        report["protected_after"] = protected_after
        report["checks"] = {
            "launcher_ready": waiter.returncode == 0,
            "kira_text_voice_only": bool(
                report["activation"]["body_activated"] is False
                and report["activation"]["world_activated"] is False
            ),
            "camera_directshow_opened": bool(camera_capture.device_opened),
            "camera_green_light_proxy_passed": bool(
                report["camera"]["green_light_proxy"]["proxy_passed"]
            ),
            "one_nonempty_dimensioned_frame": bool(
                report["camera"]["captured_frame_count"] == 1
                and jpeg_bytes > 0
                and jpeg_width > 0
                and jpeg_height > 0
            ),
            "qwen_exact_digest": qwen_result.get("model_digest") == QWEN_VISION_DIGEST,
            "qwen_actual_gpu_activity": bool(qwen_gpu["peak_delta_mib"] >= 256.0),
            "qwen_gpu_is_rtx_5060_ti": any(
                "RTX 5060 Ti" in str(row.get("name") or "")
                for sample in qwen_gpu["samples"]
                for row in sample.get("gpus", [])
                if isinstance(row, dict)
            ),
            "vision_qwen_unloaded_before_qwen_text": bool(
                report["vision_qwen_unloaded_before_qwen_text"]["proven"]
            ),
            "local_visual_cue_inserted": bool(visual_insert.get("accepted")),
            "microphone_directshow_opened": bool(microphone_capture.device_opened),
            "microphone_pcm_16khz_mono": bool(
                wav_audit.get("codec") == "pcm_s16le"
                and wav_audit.get("sample_rate_hz") == 16000
                and wav_audit.get("channels") == 1
            ),
            "microphone_level_audited": bool(
                "rms_dbfs" in wav_audit and "peak_dbfs" in wav_audit
            ),
            "speaker_source_not_fabricated": bool(
                mic_classification["speaker_identity"] == "UNKNOWN"
                and mic_classification["background_vs_nearfield_distinction"] == "NOT_PROVEN"
            ),
            "first_turn_exact_prompt_context": all(
                bool(value)
                for value in report["prompt_context_proof"].values()
            ),
            "two_exact_qwen_text_turns": len(turns) == 2
            and all(turn["model"]["actual_model_name"] == TEXT_MODEL for turn in turns),
            "raw_and_final_transformations_audited": all(
                bool(turn["model"]["exact_raw_model_replies"])
                and isinstance(turn["model"]["core_transformations"], list)
                and isinstance(turn["model"]["outer_transformations"], list)
                for turn in turns
            ),
            "approved_blackwell_gpu_voice_each_turn": all(
                turn["voice"]["approved_blackwell_gpu_only"] for turn in turns
            ),
            "readable_non_silent_generated_wav_each_turn": all(
                turn["voice"]["generated_wavs_are_readable_non_silent"] for turn in turns
            ),
            "qwen_absent_after_each_turn": all(turn["qwen_absent_after_turn"] for turn in turns),
            "raw_capture_media_not_persisted_or_hashed": True,
            "protected_files_unchanged": protected_before == protected_after,
            "person_inactive_after": not after_state.get("active_candidate"),
            "all_test_ports_closed": not any(
                bounded.port_is_open(port) for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT)
            ),
            "ollama_empty_after": not ollama_after["resident_models"],
            "final_vram_return_after_voice": bool(final_vram_return["returned"]),
        }
        report["passed"] = all(report["checks"].values())
        report["finished_at_utc"] = utc_now()
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({"passed": report["passed"], "report": relative(report_path)}, indent=2))
        return 0 if report["passed"] else 2
    except Exception as exc:
        report["failed_at_utc"] = utc_now()
        report["failure"] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, bounded.CaptureError):
            report["capture_failure"] = bounded.capture_metadata(exc.result)
            exc.result.payload = b""
        raise
    finally:
        jpeg = b""
        wav = b""
        encoded_jpeg = ""
        if camera_capture is not None:
            camera_capture.payload = b""
        if microphone_capture is not None:
            microphone_capture.payload = b""
        if server is not None and server.poll() is None:
            try:
                if sensory_lease and not sensory_purged:
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
                        body={"reason": "Qwen webcam microphone acceptance cleanup"},
                        timeout=5,
                    )
                server.wait(timeout=15)
            except Exception:
                # Only the exact child created by this harness is targeted.
                if server.poll() is None:
                    server.terminate()
                    try:
                        server.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=10)
        if output_dir.exists() and "finished_at_utc" not in report:
            report["cleanup_attempted"] = True
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.describe_plan:
        print(json.dumps(build_plan(), indent=2, ensure_ascii=False))
        return 0
    output = validate_live_arguments(args)
    return run_live(args, output)


if __name__ == "__main__":
    raise SystemExit(main())
