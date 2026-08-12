from __future__ import annotations

"""Run one explicitly authorized, bounded Kira Text + Voice acceptance.

This harness starts the same server command and environment used by the normal
Text + Voice launcher, activates only Kira, captures exactly one transient JPEG
and one short transient WAV, submits only their derived cues to the in-memory
sensory gate, asks one public question, measures the text/voice path, purges the
sensory session, deactivates Kira, and closes the exact server it created.

Raw camera and microphone bytes are held only in local variables.  They are
never written, hashed, copied into evidence, or included in the chat prompt.
Attempts 2 and 3 are explicitly private owner audits: each records the exact
temporary ASR transcript, exact derived cues, prompt-insertion proof, and model
cleanup audit, while still persisting no raw image, decoded pixels, audio
samples, or raw-media hash.  Each attempt is append-only in its own directory.
"""

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
import secrets
import socket
import struct
import subprocess
import sys
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "Data" / "runtime"
STATE_PATH = RUNTIME / "kira_world_shell_state.json"
LIFE_LOG = RUNTIME / "kira_world_life_loop_log.jsonl"
BENCHMARK_ROOT = ROOT / "Data" / "voice" / "realtime_audio_readiness" / "live_capture"
DEFAULT_FFMPEG = (
    ROOT
    / "RecoverySprint"
    / "backups"
    / "20260731_172204_pre_sprint_backup"
    / "snapshot"
    / "external_C_KiraVideos"
    / "VideoSourceCache"
    / "tool_bin"
    / "ffmpeg.exe"
)
SHELL_PORT = 8768
ASR_PORT = 8770
VISUAL_PORT = 8771
BASE_URL = f"http://127.0.0.1:{SHELL_PORT}"
OUTPUT_PARENT = ROOT / "RecoverySprint" / "continuation_20260802"
QUESTION = (
    "Kira, this is one bounded supervised test. In one brief natural sentence, "
    "what can you actually see and hear right now? Do not guess or claim recognition "
    "that your current sensory path did not provide."
)
EXPECTED_MODEL_NAME = "llama3.1:8b"
EXPECTED_MODEL_DIGEST = (
    "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e"
)
PROTECTED_FILES = (
    ROOT / "Core" / "identity_profiles.py",
    ROOT / "Kira" / "Kira_Identity_v2.pdf",
    ROOT / "Data" / "memories_kira.json",
    ROOT / "TemporaryAI" / "candidates" / "kira" / "temporary_ai_profile.json",
    ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json",
    ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav",
    ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json",
    ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_gpu" / "sidecar_worker.py",
    ROOT / "Voice" / "sidecars" / "chatterbox_py311" / "sidecar_worker.py",
)
PRIVATE_ATTEMPT_IDS = frozenset({"attempt_02", "attempt_03"})


class AcceptanceError(RuntimeError):
    pass


class CaptureError(AcceptanceError):
    def __init__(self, message: str, result: "CaptureResult") -> None:
        super().__init__(message)
        self.result = result


@dataclass
class CaptureResult:
    """One bounded ffmpeg result; payload remains memory-only."""

    payload: bytes
    started_at_utc: str
    ended_at_utc: str
    elapsed_seconds: float
    returncode: int
    device_opened: bool
    open_status: str
    stderr_tail: str


def normalize_private_attempt_id(value: Any) -> str:
    attempt_id = str(value or "").strip().casefold()
    if attempt_id not in PRIVATE_ATTEMPT_IDS:
        raise AcceptanceError(
            "this append-only instrumentation is reserved for attempt_02 or attempt_03"
        )
    return attempt_id


def validate_private_attempt_output_name(attempt_id: str, output_dir: Path) -> None:
    if output_dir.name.casefold() != attempt_id:
        raise AcceptanceError(
            f"{attempt_id} output directory must be clearly named {attempt_id}"
        )


def private_attempt_evidence_key(prefix: str, attempt_id: str) -> str:
    return f"{str(prefix).strip()}_{normalize_private_attempt_id(attempt_id)}"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def protected_hashes() -> dict[str, str]:
    missing = [relative(path) for path in PROTECTED_FILES if not path.is_file()]
    if missing:
        raise AcceptanceError(f"protected files are missing: {missing}")
    return {relative(path): sha256_file(path) for path in PROTECTED_FILES}


def validate_output_dir(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    try:
        path.relative_to(OUTPUT_PARENT.resolve())
    except ValueError as exc:
        raise AcceptanceError(
            "output directory must be a strict descendant of "
            "RecoverySprint/continuation_20260802"
        ) from exc
    if path == OUTPUT_PARENT.resolve():
        raise AcceptanceError("output directory must be a strict descendant")
    if path.exists():
        raise AcceptanceError("append-only output directory already exists")
    return path


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", int(port))) == 0


def require_idle_preflight() -> None:
    occupied = [port for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT) if port_is_open(port)]
    if occupied:
        raise AcceptanceError(f"required loopback ports are already occupied: {occupied}")
    if STATE_PATH.is_file():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if str(state.get("active_candidate") or "").strip():
            raise AcceptanceError("a Kira World person is already active")
        if state.get("browser_lease"):
            raise AcceptanceError("an owner browser lease is already active")


def request_json(
    url: str,
    *,
    token: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = None
    headers = {"X-Kira-Shell-Token": token, "Cache-Control": "no-store"}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    headers.update(extra_headers or {})
    req = urllib_request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib_request.build_opener(urllib_request.ProxyHandler({})).open(
            req, timeout=timeout
        ) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
    except urllib_error.HTTPError as exc:
        message = exc.read(65536).decode("utf-8", errors="replace")
        raise AcceptanceError(f"{method} {url} returned HTTP {exc.code}: {message}") from exc
    if len(raw) > 4 * 1024 * 1024:
        raise AcceptanceError(f"oversized JSON response from {url}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise AcceptanceError(f"non-object JSON response from {url}")
    return value


def request_binary_json(
    url: str,
    payload: bytes,
    *,
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    req = urllib_request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib_request.build_opener(urllib_request.ProxyHandler({})).open(
            req, timeout=timeout
        ) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
    except urllib_error.HTTPError as exc:
        message = exc.read(65536).decode("utf-8", errors="replace")
        raise AcceptanceError(f"POST {url} returned HTTP {exc.code}: {message}") from exc
    if len(raw) > 4 * 1024 * 1024:
        raise AcceptanceError(f"oversized sidecar response from {url}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise AcceptanceError(f"non-object sidecar response from {url}")
    return value


def sidecar_health(url: str, header: str, token: str, *, timeout_seconds: float = 90) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    last = "not contacted"
    while time.perf_counter() - started < timeout_seconds:
        try:
            req = urllib_request.Request(url, headers={header: token, "Cache-Control": "no-store"})
            with urllib_request.build_opener(urllib_request.ProxyHandler({})).open(
                req, timeout=3
            ) as response:
                value = json.loads(response.read(1024 * 1024).decode("utf-8"))
            if isinstance(value, dict) and value.get("status") == "ready":
                return value, round(time.perf_counter() - started, 3)
            last = json.dumps(value, sort_keys=True)[:400]
        except Exception as exc:  # bounded readiness polling
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.25)
    raise AcceptanceError(f"sidecar did not become ready: {url}: {last}")


def run_ffmpeg_capture(command: list[str], *, timeout: float) -> CaptureResult:
    started_at = utc_now()
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        result = CaptureResult(
            payload=bytes(exc.stdout or b""),
            started_at_utc=started_at,
            ended_at_utc=utc_now(),
            elapsed_seconds=round(time.perf_counter() - started, 3),
            returncode=-1,
            device_opened=bool(exc.stdout),
            open_status=(
                "encoded_output_observed_before_timeout"
                if exc.stdout
                else "not_confirmed_timeout"
            ),
            stderr_tail=bytes(exc.stderr or b"").decode(
                "utf-8", errors="replace"
            )[-2000:],
        )
        raise CaptureError("bounded ffmpeg capture timed out", result) from exc
    ended_at = utc_now()
    elapsed = round(time.perf_counter() - started, 3)
    payload = bytes(completed.stdout or b"")
    stderr = bytes(completed.stderr or b"").decode("utf-8", errors="replace")[-2000:]
    result = CaptureResult(
        payload=payload,
        started_at_utc=started_at,
        ended_at_utc=ended_at,
        elapsed_seconds=elapsed,
        returncode=int(completed.returncode),
        device_opened=bool(completed.returncode == 0 and payload),
        open_status=(
            "confirmed_by_nonempty_encoded_output"
            if completed.returncode == 0 and payload
            else "not_confirmed"
        ),
        stderr_tail=stderr,
    )
    if result.returncode != 0 or not result.payload:
        raise CaptureError(
            f"bounded ffmpeg capture failed with {result.returncode}: {result.stderr_tail}",
            result,
        )
    return result


def capture_metadata(result: CaptureResult) -> dict[str, Any]:
    """Detach timing/open evidence without copying transient payload bytes."""

    return {
        "started_at": result.started_at_utc,
        "ended_at": result.ended_at_utc,
        "elapsed_seconds": result.elapsed_seconds,
        "returncode": result.returncode,
        "device_opened": result.device_opened,
        "open_status": result.open_status,
        "encoded_output_nonempty": bool(result.payload),
        "stderr_tail": result.stderr_tail,
        "raw_payload_persisted": False,
    }


def run_ffmpeg(command: list[str], *, timeout: float) -> bytes:
    """Compatibility wrapper returning only transient bytes."""

    return run_ffmpeg_capture(command, timeout=timeout).payload


def camera_capture_command(
    ffmpeg: Path,
    device: str,
    *,
    hold_seconds: float,
) -> list[str]:
    # `trim=start=` consumes the live input for the requested interval before
    # selecting the one and only encoded output frame.  Hidden or extra frames
    # are not returned to the harness.
    return [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "dshow",
        "-i", f"video={device}", "-frames:v", "1",
        "-vf", f"trim=start={hold_seconds:.3f},scale=640:-2",
        "-q:v", "5", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
    ]


def microphone_capture_command(
    ffmpeg: Path,
    device: str,
    *,
    duration_seconds: float,
) -> list[str]:
    return [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "dshow",
        "-i", f"audio={device}", "-t", f"{duration_seconds:.3f}",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "wav", "pipe:1",
    ]


def capture_one_jpeg(
    ffmpeg: Path,
    device: str,
    *,
    hold_seconds: float = 3.0,
) -> CaptureResult:
    return run_ffmpeg_capture(
        camera_capture_command(ffmpeg, device, hold_seconds=hold_seconds),
        timeout=30,
    )


def capture_one_wav(
    ffmpeg: Path,
    device: str,
    duration_seconds: float,
) -> CaptureResult:
    return run_ffmpeg_capture(
        microphone_capture_command(
            ffmpeg,
            device,
            duration_seconds=duration_seconds,
        ),
        timeout=max(30, duration_seconds + 20),
    )


def jpeg_dimensions(payload: bytes) -> tuple[int, int]:
    """Read JPEG SOF dimensions without decoding or retaining pixel data."""

    if len(payload) < 4 or payload[:2] != b"\xff\xd8":
        raise AcceptanceError("camera output is not a JPEG stream")
    index = 2
    sof_markers = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    while index + 3 < len(payload):
        if payload[index] != 0xFF:
            index += 1
            continue
        while index < len(payload) and payload[index] == 0xFF:
            index += 1
        if index >= len(payload):
            break
        marker = payload[index]
        index += 1
        if marker in {0x01, *range(0xD0, 0xDA)}:
            continue
        if index + 2 > len(payload):
            break
        segment_length = int.from_bytes(payload[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(payload):
            break
        if marker in sof_markers:
            if segment_length < 7:
                break
            height = int.from_bytes(payload[index + 3:index + 5], "big")
            width = int.from_bytes(payload[index + 5:index + 7], "big")
            if width < 1 or height < 1:
                break
            return width, height
        index += segment_length
    raise AcceptanceError("JPEG dimensions could not be read from the bounded frame")


def pcm_wav_audit(payload: bytes) -> dict[str, Any]:
    """Return format/level evidence without retaining samples or hashing audio."""

    try:
        with wave.open(io.BytesIO(payload), "rb") as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            declared_frame_count = reader.getnframes()
            compression = reader.getcomptype()
            frames = reader.readframes(declared_frame_count)
    except (EOFError, wave.Error) as exc:
        raise AcceptanceError(f"microphone output is not a readable WAV: {exc}") from exc
    if compression != "NONE" or sample_width != 2:
        raise AcceptanceError("microphone WAV must be uncompressed PCM signed 16-bit")
    if channels < 1 or sample_rate < 1:
        raise AcceptanceError("microphone WAV has an invalid channel or sample-rate header")
    block_align = channels * sample_width
    frame_count = len(frames) // block_align
    sample_count = len(frames) // 2
    samples = struct.unpack(f"<{sample_count}h", frames[: sample_count * 2]) if sample_count else ()
    peak_sample = max((abs(value) for value in samples), default=0)
    mean_square = sum(value * value for value in samples) / sample_count if sample_count else 0.0
    rms_sample = math.sqrt(mean_square)
    full_scale = 32768.0

    def dbfs(linear: float) -> float | None:
        return round(20.0 * math.log10(linear), 3) if linear > 0 else None

    rms_linear = rms_sample / full_scale
    peak_linear = peak_sample / full_scale
    return {
        "container": "wav",
        "codec": "pcm_s16le",
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "declared_frame_count": declared_frame_count,
        "frame_count": frame_count,
        "sample_count": sample_count,
        "duration_seconds": round(frame_count / sample_rate, 6) if sample_rate else 0.0,
        "rms_linear": round(rms_linear, 6),
        "rms_dbfs": dbfs(rms_linear),
        "peak_linear": round(peak_linear, 6),
        "peak_dbfs": dbfs(peak_linear),
        "non_silent": peak_sample > 0,
    }


def cue_value(cues: Any, kind: str) -> Any:
    for item in cues if isinstance(cues, list) else []:
        if isinstance(item, dict) and str(item.get("name") or "") == kind:
            return item.get("value")
    return None


def load_benchmark(request_id: str, timeout_seconds: float = 900) -> tuple[list[dict[str, Any]], Path]:
    path = BENCHMARK_ROOT / f"voice_request_{request_id}.jsonl"
    deadline = time.monotonic() + timeout_seconds
    records: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        if path.is_file():
            try:
                records = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except (OSError, json.JSONDecodeError):
                records = []
            if any(row.get("event") == "request_completed" for row in records):
                return records, path
        time.sleep(0.25)
    raise AcceptanceError("voice benchmark did not reach request_completed")


def event_latency(records: list[dict[str, Any]], event: str) -> float | None:
    submitted = next((row for row in records if row.get("event") == "request_submitted"), None)
    target = next((row for row in records if row.get("event") == event), None)
    if not submitted or not target:
        return None
    return round(
        (float(target["monotonic_ns"]) - float(submitted["monotonic_ns"])) / 1_000_000_000,
        3,
    )


def _event_record(
    records: list[dict[str, Any]],
    event: str,
    *,
    occurrence: int = 0,
) -> dict[str, Any] | None:
    matches = [row for row in records if row.get("event") == event]
    return matches[occurrence] if 0 <= occurrence < len(matches) else None


def _seconds_between(
    first: dict[str, Any] | None,
    second: dict[str, Any] | None,
) -> float | None:
    if not first or not second:
        return None
    try:
        return round(
            (int(second["monotonic_ns"]) - int(first["monotonic_ns"]))
            / 1_000_000_000,
            6,
        )
    except (KeyError, TypeError, ValueError):
        return None


def benchmark_phase_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Project all public voice phase boundaries and exact relative timings."""

    submitted = _event_record(records, "request_submitted")
    received = _event_record(records, "chat_request_received")
    text_ready = _event_record(records, "text_ready")
    payload_ready = _event_record(records, "voice_payload_ready")
    pipeline_start = _event_record(records, "voice_pipeline_start")
    completed = _event_record(records, "request_completed")
    synthesis_starts = [row for row in records if row.get("event") == "chunk_synthesis_start"]
    synthesis_ends = [row for row in records if row.get("event") == "chunk_synthesis_end"]
    playback_starts = [row for row in records if row.get("event") == "chunk_playback_start"]
    playback_ends = [row for row in records if row.get("event") == "chunk_playback_end"]
    chunk_indexes = sorted(
        {
            int((row.get("details") or {}).get("chunk_index"))
            for row in synthesis_starts + synthesis_ends + playback_starts + playback_ends
            if isinstance(row.get("details"), dict)
            and isinstance((row.get("details") or {}).get("chunk_index"), int)
        }
    )
    chunks: list[dict[str, Any]] = []
    for chunk_index in chunk_indexes:
        def chunk_event(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
            return next(
                (
                    row
                    for row in rows
                    if (row.get("details") or {}).get("chunk_index") == chunk_index
                ),
                None,
            )

        synthesis_start = chunk_event(synthesis_starts)
        synthesis_end = chunk_event(synthesis_ends)
        playback_start = chunk_event(playback_starts)
        playback_end = chunk_event(playback_ends)
        chunks.append(
            {
                "chunk_index": chunk_index,
                "request_to_synthesis_start_seconds": _seconds_between(submitted, synthesis_start),
                "synthesis_seconds": _seconds_between(synthesis_start, synthesis_end),
                "synthesis_to_playback_start_seconds": _seconds_between(synthesis_end, playback_start),
                "playback_seconds": _seconds_between(playback_start, playback_end),
                "synthesis_end_details": (
                    dict(synthesis_end.get("details") or {}) if synthesis_end else {}
                ),
                "playback_end_details": (
                    dict(playback_end.get("details") or {}) if playback_end else {}
                ),
            }
        )
    timeline = []
    for row in records:
        offset = _seconds_between(submitted, row)
        timeline.append(
            {
                "sequence": row.get("sequence"),
                "event": row.get("event"),
                "monotonic_ns": row.get("monotonic_ns"),
                "wall_time_utc": row.get("wall_time_utc"),
                "request_offset_seconds": offset,
                "details": dict(row.get("details") or {})
                if isinstance(row.get("details"), dict)
                else {},
            }
        )
    return {
        "submit_to_chat_receive_seconds": _seconds_between(submitted, received),
        "chat_receive_to_text_ready_seconds": _seconds_between(received, text_ready),
        "text_ready_to_voice_payload_seconds": _seconds_between(text_ready, payload_ready),
        "voice_payload_to_pipeline_start_seconds": _seconds_between(payload_ready, pipeline_start),
        "pipeline_start_to_first_synthesis_seconds": _seconds_between(
            pipeline_start,
            synthesis_starts[0] if synthesis_starts else None,
        ),
        "request_total_seconds": _seconds_between(submitted, completed),
        "chunks": chunks,
        "event_timeline": timeline,
    }


def exact_asr_segments(value: Any) -> list[dict[str, Any]]:
    """Bound exact private ASR evidence without accepting arbitrary fields."""

    rows: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "start_seconds": round(float(item.get("start") or 0.0), 3),
                "end_seconds": round(float(item.get("end") or 0.0), 3),
                "text": str(item.get("text") or "")[:1000],
            }
        )
        if len(rows) >= 128:
            break
    return rows


def selected_llama_model(inventory: dict[str, Any]) -> dict[str, Any]:
    rows = inventory.get("llama3_1_8b") if isinstance(inventory, dict) else []
    for item in rows if isinstance(rows, list) else []:
        if isinstance(item, dict) and str(item.get("name") or "") == "llama3.1:8b":
            return {
                key: item.get(key)
                for key in ("name", "model", "digest", "size")
            }
    return {}


def validate_private_model_audit(
    value: Any,
    *,
    expected_launch_id: str,
    expected_request_id: str,
    expected_reply: str,
    expected_cue_ids: list[str],
) -> dict[str, Any]:
    """Validate and detach the one-shot private server audit response."""

    if not isinstance(value, dict):
        raise AcceptanceError("private model audit is absent from the chat response")
    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > 2 * 1024 * 1024:
        raise AcceptanceError("private model audit exceeds the bounded evidence limit")
    if str(value.get("shell_launch_id") or "") != expected_launch_id:
        raise AcceptanceError("private model audit launch binding mismatch")
    if str(value.get("benchmark_request_id") or "") != expected_request_id:
        raise AcceptanceError("private model audit benchmark binding mismatch")
    if value.get("completed") is not True:
        raise AcceptanceError("private model audit did not complete")
    if str(value.get("final_displayed_reply") or "") != expected_reply:
        raise AcceptanceError("private model audit final reply mismatch")
    prompt_hash = str(value.get("core_prompt_sha256") or "").lower()
    if len(prompt_hash) != 64 or any(ch not in "0123456789abcdef" for ch in prompt_hash):
        raise AcceptanceError("private model audit prompt digest is invalid")
    if value.get("one_turn_sensory_context_inserted") is not True:
        raise AcceptanceError("private model audit did not prove sensory prompt insertion")
    supplied_cue_ids = sorted(str(item) for item in value.get("sensory_cue_ids") or [])
    if supplied_cue_ids != sorted(expected_cue_ids):
        raise AcceptanceError("private model audit cue IDs do not match inserted cues")
    core_turn = value.get("core_turn") if isinstance(value.get("core_turn"), dict) else {}
    model_calls = core_turn.get("model_calls") if isinstance(core_turn.get("model_calls"), list) else []
    if not model_calls:
        raise AcceptanceError("private model audit contains no real model-call record")
    if not any(str(item.get("raw_reply") or "") for item in model_calls if isinstance(item, dict)):
        raise AcceptanceError("private model audit contains no exact raw model reply")

    # The private hook may contain text and hashes, but it must never become a
    # transport for captured pixels or audio samples.
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
                    raise AcceptanceError(
                        f"private model audit contains prohibited raw-media field: {key}"
                    )
                inspect(child)
        elif isinstance(node, list):
            for child in node:
                inspect(child)
        elif isinstance(node, (bytes, bytearray, memoryview)):
            raise AcceptanceError("private model audit contains a binary value")

    inspect(value)
    return json.loads(encoded.decode("utf-8"))


def last_life_voice_output(started_at_utc: str) -> dict[str, Any]:
    if not LIFE_LOG.is_file():
        return {}
    latest: dict[str, Any] = {}
    for line in LIFE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            record.get("event") == "voice_output"
            and record.get("candidate") == "kira"
            and str(record.get("at") or "") >= started_at_utc
        ):
            latest = record
    result = latest.get("result") if isinstance(latest.get("result"), dict) else {}
    safe_chunks = []
    for item in result.get("voice_chunk_results") if isinstance(result.get("voice_chunk_results"), list) else []:
        if not isinstance(item, dict):
            continue
        safe_chunks.append(
            {
                key: item.get(key)
                for key in (
                    "spoken", "generated", "reason", "generation_elapsed_seconds",
                    "continuation_gap_seconds", "route_id", "approved_voice_path_used",
                    "device", "route_attempt_summary", "preferred_failure_reason",
                    "gpu_synthesis_attempted", "cpu_synthesis_attempted",
                    "automatic_cpu_fallback_used", "gpu_actual_allocation",
                    "gpu_utilization_observed", "peak_allocated_bytes",
                    "peak_reserved_bytes", "peak_process_rss_mib",
                    "peak_system_ram_used_mib", "baseline_gpu_vram_used_mib",
                    "peak_gpu_vram_used_mib", "peak_sidecar_gpu_delta_mib",
                    "sidecar_process_seconds",
                )
                if key in item
            }
        )
    return {
        "at": latest.get("at"),
        "spoken": result.get("spoken"),
        "complete": result.get("complete"),
        "reason": result.get("reason"),
        "duration_seconds": result.get("duration_seconds"),
        "queue_wait_seconds": result.get("queue_wait_seconds"),
        "pipeline": result.get("pipeline"),
        "max_continuation_gap_seconds": result.get("max_continuation_gap_seconds"),
        "voice_chunk_results": safe_chunks,
    }


def ollama_inventory() -> dict[str, Any]:
    opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
    tags: dict[str, Any] = {}
    resident: dict[str, Any] = {}
    try:
        with opener.open("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            tags = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
    except Exception as exc:
        tags = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        with opener.open("http://127.0.0.1:11434/api/ps", timeout=5) as response:
            resident = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
    except Exception as exc:
        resident = {"error": f"{type(exc).__name__}: {exc}"}
    llama = []
    for item in tags.get("models") if isinstance(tags.get("models"), list) else []:
        if isinstance(item, dict) and str(item.get("name") or "") == "llama3.1:8b":
            llama.append({key: item.get(key) for key in ("name", "model", "digest", "size")})
    resident_rows = []
    for item in resident.get("models") if isinstance(resident.get("models"), list) else []:
        if isinstance(item, dict):
            resident_rows.append({key: item.get(key) for key in ("name", "model", "digest", "size_vram")})
    return {"llama3_1_8b": llama, "resident_models": resident_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ffmpeg", default=str(DEFAULT_FFMPEG))
    parser.add_argument("--camera-device", default="USB CAMERA")
    parser.add_argument("--camera-hold-seconds", type=float, default=3.0)
    parser.add_argument("--microphone-device", default="Microphone (USB CAMERA)")
    parser.add_argument("--microphone-seconds", type=float, default=8.0)
    parser.add_argument("--attempt-id", default="attempt_02")
    parser.add_argument("--private-acceptance-audit", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Refusing live devices/person activation without --execute")
    attempt_id = normalize_private_attempt_id(args.attempt_id)
    if not args.private_acceptance_audit:
        raise AcceptanceError(
            f"{attempt_id} requires --private-acceptance-audit because its report contains "
            "the exact temporary transcript and raw-model cleanup audit"
        )
    if not 2.5 <= float(args.camera_hold_seconds) <= 4.0:
        raise AcceptanceError("camera hold must stay between 2.5 and 4 seconds")
    if not 3.0 <= float(args.microphone_seconds) <= 12.0:
        raise AcceptanceError("microphone duration must stay between 3 and 12 seconds")

    output_dir = validate_output_dir(args.output_dir)
    validate_private_attempt_output_name(attempt_id, output_dir)
    ffmpeg = Path(args.ffmpeg).resolve()
    if not ffmpeg.is_file():
        raise AcceptanceError("approved local ffmpeg executable is unavailable")
    require_idle_preflight()
    output_dir.mkdir(parents=True)

    launch_id = uuid.uuid4().hex
    shell_token = secrets.token_urlsafe(32)
    asr_token = secrets.token_urlsafe(32)
    visual_token = secrets.token_urlsafe(32)
    started_at = utc_now()
    before_hashes = protected_hashes()
    before_ollama = ollama_inventory()
    env = os.environ.copy()
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

    stdout_path = output_dir / "server.stdout.log"
    stderr_path = output_dir / "server.stderr.log"
    report_path = output_dir / "BOUNDED_OWNER_ACCEPTANCE.json"
    server: subprocess.Popen[bytes] | None = None
    sensory_lease = ""
    original_sensory_lease = ""
    activation_revision = ""
    visual_purged = False
    sensory_purged = False
    deactivated = False
    safe_closed = False
    report: dict[str, Any] = {
        "schema_version": 2,
        "artifact_kind": f"kira_text_voice_bounded_owner_acceptance_{attempt_id}",
        "attempt_id": attempt_id,
        "evidence_classification": "private_owner_acceptance",
        "started_at": started_at,
        "launch_id": launch_id,
        "question": QUESTION,
        "privacy": {
            "camera_frames_captured": 1,
            "camera_requested_hold_seconds": float(args.camera_hold_seconds),
            "microphone_capture_seconds": float(args.microphone_seconds),
            "raw_frame_written": False,
            "raw_frame_hashed": False,
            "raw_audio_written": False,
            "raw_audio_hashed": False,
            private_attempt_evidence_key(
                "exact_temporary_transcript_written_to_private",
                attempt_id,
            ): True,
            "transcript_not_promoted_to_memory": True,
            "continuous_monitoring": False,
            "identity_inference_performed": False,
            "automatic_memory_write": False,
        },
        "environment_contract": {
            "model_name": EXPECTED_MODEL_NAME,
            "expected_model_digest": EXPECTED_MODEL_DIGEST,
            "private_acceptance_audit": True,
            "personhood_eval_mode": False,
            "chatterbox_device": "auto",
            "blackwell_gpu_disabled": False,
            "sealed_cpu_disabled": False,
            "sapi_forced": False,
            "qwen_vision_enabled": False,
        },
        "protected_before": before_hashes,
        "ollama_before": before_ollama,
    }

    try:
        stdout_handle = stdout_path.open("wb")
        stderr_handle = stderr_path.open("wb")
        try:
            server = subprocess.Popen(
                [sys.executable, str(ROOT / "tools" / "kira_world_shell_server.py"), "--no-browser"],
                cwd=str(ROOT), env=env, stdout=stdout_handle, stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()
        report["server_pid"] = server.pid

        wait_started = time.perf_counter()
        waiter = subprocess.run(
            [
                sys.executable, str(ROOT / "tools" / "wait_for_kira_world_shell.py"),
                "--url", f"{BASE_URL}/", "--timeout", "60", "--owned-pid", str(server.pid),
            ],
            cwd=str(ROOT), env=env, text=True, capture_output=True, timeout=70, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        report["launcher_readiness"] = {
            "returncode": waiter.returncode,
            "elapsed_seconds": round(time.perf_counter() - wait_started, 3),
            "stdout": waiter.stdout[-2000:],
            "stderr": waiter.stderr[-2000:],
        }
        if waiter.returncode != 0:
            raise AcceptanceError("the exact launcher readiness helper failed")

        asr_health, asr_ready_seconds = sidecar_health(
            f"http://127.0.0.1:{ASR_PORT}/health", "X-Kira-ASR-Token", asr_token
        )
        visual_health, visual_ready_seconds = sidecar_health(
            f"http://127.0.0.1:{VISUAL_PORT}/health", "X-Kira-Visual-Token", visual_token
        )
        report["sidecars"] = {
            "asr": {**asr_health, "ready_wait_seconds": asr_ready_seconds},
            "visual": {**visual_health, "ready_wait_seconds": visual_ready_seconds},
        }

        activation = request_json(
            f"{BASE_URL}/api/activate", token=shell_token, method="POST",
            body={"candidate": "kira", "source": "bounded_owner_acceptance_20260802"},
        )
        if activation.get("ok") is not True or activation.get("label") != "Kira":
            raise AcceptanceError(f"Kira activation failed: {activation}")
        state = request_json(f"{BASE_URL}/api/state", token=shell_token)
        sensory_lease = str(state.get("sensory_lease") or "")
        original_sensory_lease = sensory_lease
        activation_revision = str(
            ((state.get("sensory_session") or {}).get("activation_revision"))
            or state.get("last_activation_at")
            or ""
        )
        if state.get("active_candidate") != "kira" or not sensory_lease or not activation_revision:
            raise AcceptanceError("activation did not produce an exact Kira sensory lease")
        report["activation"] = {
            "active_candidate": state.get("active_candidate"),
            "active_label": state.get("active_label"),
            "activation_revision": activation_revision,
            "body_activated": activation.get("body_activated", False),
            "world_activated": activation.get("world_activated", False),
            "voice_prewarm_started": activation.get("voice_prewarm_started"),
        }

        camera_capture = capture_one_jpeg(
            ffmpeg,
            args.camera_device,
            hold_seconds=float(args.camera_hold_seconds),
        )
        jpeg = camera_capture.payload
        if len(jpeg) > 1024 * 1024:
            raise AcceptanceError("bounded camera JPEG exceeded the visual sidecar limit")
        jpeg_byte_count = len(jpeg)
        jpeg_width, jpeg_height = jpeg_dimensions(jpeg)
        visual_derive_started_at = utc_now()
        visual_derive_started = time.perf_counter()
        visual_result = request_binary_json(
            f"http://127.0.0.1:{VISUAL_PORT}/api/derive-cues", jpeg,
            headers={
                "Content-Type": "image/jpeg", "X-Kira-Visual-Token": visual_token,
                "X-Kira-Person": "kira", "X-Kira-Activation-Revision": activation_revision,
                "X-Kira-Sensory-Lease": sensory_lease,
            }, timeout=60,
        )
        visual_derive_ended_at = utc_now()
        visual_derive_seconds = round(time.perf_counter() - visual_derive_started, 3)
        jpeg = b""
        camera_capture.payload = b""
        if visual_result.get("ok") is not True:
            raise AcceptanceError(f"visual cue derivation failed: {visual_result}")
        visual_cues = visual_result.get("cues") if isinstance(visual_result.get("cues"), list) else []
        cue_confidence = max(
            [0.1]
            + [
                max(0.0, min(1.0, float(item.get("confidence") or 0.0)))
                for item in visual_cues if isinstance(item, dict)
            ]
        )
        visual_fact = {
            "modality": "visual",
            "event": "non_identifying_local_frame_cues",
            "cues": visual_cues,
        }
        visual_source = {
            "kind": "local_visual_perception_sidecar",
            "backend": str(visual_result.get("source") or ""),
            "person_session_bound": True,
        }
        visual_insert_started_at = utc_now()
        visual_insert_started = time.perf_counter()
        visual_gate = request_json(
            f"{BASE_URL}/api/sensory/cue", token=shell_token, method="POST",
            body={
                "sensory_lease": sensory_lease,
                "fact": visual_fact,
                "source": visual_source,
                "observed_at": str(visual_result.get("observed_at") or utc_now()),
                "confidence": cue_confidence,
                "attributes": {"capture_reason": "bounded_owner_acceptance", "identity_inference_performed": False, "automatic_spoken_response": False, "automatic_memory_write": False},
            },
        )
        visual_insert_ended_at = utc_now()
        visual_insert_seconds = round(time.perf_counter() - visual_insert_started, 3)
        derived_frame_size = cue_value(visual_cues, "frame_size")
        report["visual_sample"] = {
            "device": {
                "api": "DirectShow",
                "device_id": str(args.camera_device),
                "ffmpeg_selector": f"video={args.camera_device}",
            },
            "capture_started_at": camera_capture.started_at_utc,
            "capture_ended_at": camera_capture.ended_at_utc,
            "capture_elapsed_seconds": camera_capture.elapsed_seconds,
            "requested_hold_seconds": float(args.camera_hold_seconds),
            "device_opened": camera_capture.device_opened,
            "device_open_status": camera_capture.open_status,
            "ffmpeg_returncode": camera_capture.returncode,
            "captured_frame_count": 1,
            "encoded_byte_count": jpeg_byte_count,
            "encoded_nonempty": jpeg_byte_count > 0,
            "jpeg_dimensions": {"width": jpeg_width, "height": jpeg_height},
            "jpeg_dimensions_match_derived_cue": derived_frame_size
            == {"width": jpeg_width, "height": jpeg_height},
            "source": visual_result.get("source"),
            "brightness_class": cue_value(visual_cues, "brightness_class"),
            "motion_class": cue_value(visual_cues, "motion_class"),
            "coarse_face_count": cue_value(visual_cues, "coarse_face_count"),
            "exact_derived_cues": visual_cues,
            "derivation": {
                "started_at": visual_derive_started_at,
                "ended_at": visual_derive_ended_at,
                "elapsed_seconds": visual_derive_seconds,
                "observed_at": visual_result.get("observed_at"),
            },
            "insertion": {
                "started_at": visual_insert_started_at,
                "ended_at": visual_insert_ended_at,
                "elapsed_seconds": visual_insert_seconds,
                "accepted": visual_gate.get("ok") is True,
                "cue_id": visual_gate.get("cue_id"),
                "private_attention_placeholder_id": visual_gate.get(
                    "private_attention_placeholder_id"
                ),
                "exact_fact": visual_fact,
                "exact_source": visual_source,
                "buffer_stats_after": visual_gate.get("stats"),
            },
            "identity_inference_performed": False,
            "gate_accepted": visual_gate.get("ok") is True,
            "raw_frame_persisted": visual_result.get("raw_frame_persisted", False),
        }

        microphone_capture = capture_one_wav(
            ffmpeg,
            args.microphone_device,
            float(args.microphone_seconds),
        )
        wav = microphone_capture.payload
        wav_format = pcm_wav_audit(wav)
        asr_started_at = utc_now()
        asr_started = time.perf_counter()
        asr_result = request_binary_json(
            f"http://127.0.0.1:{ASR_PORT}/api/transcribe", wav,
            headers={
                "Content-Type": "audio/wav", "X-Kira-ASR-Token": asr_token,
                "X-Kira-Person": "kira", "X-Kira-Activation-Revision": activation_revision,
                "X-Kira-Sensory-Lease": sensory_lease,
            }, timeout=180,
        )
        asr_ended_at = utc_now()
        asr_seconds = round(time.perf_counter() - asr_started, 3)
        wav = b""
        microphone_capture.payload = b""
        if asr_result.get("ok") is not True:
            raise AcceptanceError(f"ASR failed: {asr_result}")
        transcript = str(asr_result.get("text") or "").strip()
        transcript_words = transcript.split()
        exact_segments = exact_asr_segments(asr_result.get("segments"))
        voiced_duration_seconds = round(
            sum(
                max(0.0, row["end_seconds"] - row["start_seconds"])
                for row in exact_segments
            ),
            3,
        )
        auditory_gate: dict[str, Any] = {"ok": False, "reason": "empty_transcript"}
        auditory_fact: dict[str, Any] = {}
        auditory_source: dict[str, Any] = {}
        auditory_insert_started_at = ""
        auditory_insert_ended_at = ""
        auditory_insert_seconds: float | None = None
        if transcript:
            auditory_fact = {
                "modality": "auditory",
                "event": "possible_speech",
                "speaker": "robert_or_unknown",
                "transcript": transcript,
            }
            auditory_source = {
                "kind": "local_microphone_asr",
                "model_id": str(asr_result.get("model_id") or ""),
                "person_session_bound": True,
            }
            auditory_insert_started_at = utc_now()
            auditory_insert_started = time.perf_counter()
            auditory_gate = request_json(
                f"{BASE_URL}/api/sensory/cue", token=shell_token, method="POST",
                body={
                    "sensory_lease": sensory_lease,
                    "fact": auditory_fact,
                    "source": auditory_source,
                    "observed_at": utc_now(),
                    "confidence": max(0.0, min(1.0, float(asr_result.get("language_probability") or 0.5))),
                    "attributes": {"language": str(asr_result.get("language") or ""), "segment_count": len(asr_result.get("segments") or []), "automatic_spoken_response": False, "automatic_memory_write": False},
                },
            )
            auditory_insert_ended_at = utc_now()
            auditory_insert_seconds = round(
                time.perf_counter() - auditory_insert_started,
                3,
            )
        report["microphone_sample"] = {
            "device": {
                "api": "DirectShow",
                "device_id": str(args.microphone_device),
                "ffmpeg_selector": f"audio={args.microphone_device}",
            },
            "capture_started_at": microphone_capture.started_at_utc,
            "capture_ended_at": microphone_capture.ended_at_utc,
            "capture_elapsed_seconds": microphone_capture.elapsed_seconds,
            "device_opened": microphone_capture.device_opened,
            "device_open_status": microphone_capture.open_status,
            "ffmpeg_returncode": microphone_capture.returncode,
            "capture_seconds": float(args.microphone_seconds),
            "format_and_levels": wav_format,
            "audio_bytes_received": asr_result.get("audio_bytes_received"),
            "asr_started_at": asr_started_at,
            "asr_ended_at": asr_ended_at,
            "asr_elapsed_seconds": asr_seconds,
            "transcript_nonempty": bool(transcript),
            "transcript_word_count": len(transcript_words),
            "transcript_sha256": sha256_bytes(transcript.encode("utf-8")) if transcript else None,
            "exact_temporary_transcript": transcript,
            private_attempt_evidence_key(
                "transcript_persisted_only_in_private",
                attempt_id,
            ): True,
            "language": asr_result.get("language"),
            "language_probability": asr_result.get("language_probability"),
            "vad_filter_enabled": True,
            "vad_speech_detected": bool(exact_segments),
            "vad_voiced_duration_seconds": voiced_duration_seconds,
            "segment_count": len(exact_segments),
            "exact_segments": exact_segments,
            "insertion": {
                "started_at": auditory_insert_started_at,
                "ended_at": auditory_insert_ended_at,
                "elapsed_seconds": auditory_insert_seconds,
                "accepted": auditory_gate.get("ok") is True,
                "cue_id": auditory_gate.get("cue_id"),
                "private_attention_placeholder_id": auditory_gate.get(
                    "private_attention_placeholder_id"
                ),
                "exact_fact": auditory_fact,
                "exact_source": auditory_source,
                "buffer_stats_after": auditory_gate.get("stats"),
            },
            "gate_accepted": auditory_gate.get("ok") is True,
            "raw_audio_persisted": asr_result.get("raw_audio_persisted", False),
        }
        transcript = ""
        transcript_words = []

        benchmark = request_json(
            f"{BASE_URL}/api/voice-benchmark/submit", token=shell_token,
            method="POST", body={},
        )
        request_id = str(benchmark.get("benchmark_capture_id") or "")
        if not request_id:
            raise AcceptanceError("voice benchmark capture was not enabled")
        expected_cue_ids = [
            str(value)
            for value in (
                visual_gate.get("cue_id"),
                auditory_gate.get("cue_id"),
            )
            if str(value or "").strip()
        ]
        chat_started = time.perf_counter()
        chat = request_json(
            f"{BASE_URL}/api/chat", token=shell_token, method="POST",
            body={
                "text": QUESTION,
                "benchmark_request_id": request_id,
                "private_acceptance_audit": True,
            },
            timeout=300,
        )
        chat_elapsed = round(time.perf_counter() - chat_started, 3)
        if chat.get("ok") is not True or not str(chat.get("ai_line") or "").strip():
            raise AcceptanceError(f"Kira chat did not return a public reply: {chat}")
        displayed_reply = str(chat.get("ai_line") or "")
        private_model_audit = validate_private_model_audit(
            chat.get("private_acceptance_audit"),
            expected_launch_id=launch_id,
            expected_request_id=request_id,
            expected_reply=displayed_reply,
            expected_cue_ids=expected_cue_ids,
        )
        ollama_after_chat = ollama_inventory()
        report["ollama_after_chat"] = ollama_after_chat
        exact_model = selected_llama_model(ollama_after_chat)
        if not exact_model:
            exact_model = selected_llama_model(before_ollama)
        model_digest = str(exact_model.get("digest") or "").lower()
        if len(model_digest) != 64 or any(
            char not in "0123456789abcdef" for char in model_digest
        ):
            raise AcceptanceError("exact llama3.1:8b digest is unavailable")
        if model_digest != EXPECTED_MODEL_DIGEST:
            raise AcceptanceError("installed llama3.1:8b digest does not match the approved model")
        records, benchmark_path = load_benchmark(request_id)
        post_chat_state = request_json(f"{BASE_URL}/api/state", token=shell_token)
        core_turn_audit = (
            private_model_audit.get("core_turn")
            if isinstance(private_model_audit.get("core_turn"), dict)
            else {}
        )
        model_calls = (
            core_turn_audit.get("model_calls")
            if isinstance(core_turn_audit.get("model_calls"), list)
            else []
        )
        raw_model_replies = [
            str(item.get("raw_reply") or "")
            for item in model_calls
            if isinstance(item, dict)
        ]
        primary_model_call = next(
            (
                dict(item)
                for item in model_calls
                if isinstance(item, dict) and item.get("outcome") == "completed"
            ),
            dict(model_calls[0]) if model_calls and isinstance(model_calls[0], dict) else {},
        )
        ollama_metrics = (
            primary_model_call.get("ollama_metrics")
            if isinstance(primary_model_call.get("ollama_metrics"), dict)
            else {}
        )
        if str(private_model_audit.get("configured_model_name") or "") != EXPECTED_MODEL_NAME:
            raise AcceptanceError("private model audit configured-model mismatch")
        if str(primary_model_call.get("model_name") or "") != EXPECTED_MODEL_NAME:
            raise AcceptanceError("private model audit actual model-call name mismatch")
        exact_sensory_prompt = str(
            private_model_audit.get("one_turn_sensory_context") or ""
        )
        transcript_prompt_token = (
            json.dumps(
                report["microphone_sample"]["exact_temporary_transcript"],
                ensure_ascii=False,
            )
            if report["microphone_sample"]["exact_temporary_transcript"]
            else ""
        )

        def duration_seconds_from_ns(value: Any) -> float | None:
            try:
                return round(int(value) / 1_000_000_000.0, 6)
            except (TypeError, ValueError):
                return None

        report["conversation"] = {
            "selected_person": "kira",
            "model_name": EXPECTED_MODEL_NAME,
            "model_digest": model_digest,
            "displayed_reply": displayed_reply,
            "displayed_reply_sha256": sha256_bytes(displayed_reply.encode("utf-8")),
            "chat_http_wall_seconds": chat_elapsed,
            "request_to_text_ready_seconds": event_latency(records, "text_ready"),
            "request_to_voice_payload_ready_seconds": event_latency(records, "voice_payload_ready"),
            "request_to_synthesis_start_seconds": event_latency(records, "chunk_synthesis_start"),
            "request_to_first_playback_proxy_seconds": event_latency(records, "first_playback_proxy"),
            "request_to_voice_complete_seconds": event_latency(records, "request_completed"),
            "true_first_audible_owner_observed": False,
            "voice_queue_immediate_result": chat.get("voice_result"),
            "benchmark_path": relative(benchmark_path),
            "benchmark_sha256": sha256_file(benchmark_path),
            "benchmark_event_count": len(records),
            "benchmark_events": [row.get("event") for row in records],
            "voice_phase_timings": benchmark_phase_audit(records),
        }
        report["prompt_snapshot_audit"] = {
            "assembled_at": private_model_audit.get("prompt_assembled_at"),
            "sha256": private_model_audit.get("core_prompt_sha256"),
            "utf8_bytes": private_model_audit.get("core_prompt_utf8_bytes"),
            "one_turn_sensory_context_inserted": private_model_audit.get(
                "one_turn_sensory_context_inserted"
            ),
            "exact_one_turn_sensory_context": private_model_audit.get(
                "one_turn_sensory_context"
            ),
            "exact_inserted_cue_ids": private_model_audit.get("sensory_cue_ids"),
            "modalities": private_model_audit.get("sensory_modalities"),
            "sensory_cleanup": private_model_audit.get("sensory_cleanup"),
            "visual_brightness_present_exactly": str(
                report["visual_sample"]["brightness_class"]
            )
            in exact_sensory_prompt,
            "visual_motion_present_exactly": str(
                report["visual_sample"]["motion_class"]
            )
            in exact_sensory_prompt,
            "temporary_transcript_present_exactly": bool(
                transcript_prompt_token
                and transcript_prompt_token in exact_sensory_prompt
            ),
            "buffer_stats_after_chat": (
                post_chat_state.get("sensory_session") or {}
            ).get("stats")
            if isinstance(post_chat_state.get("sensory_session"), dict)
            else {},
        }
        report["model_audit"] = {
            "exact_model": exact_model,
            "configured_model_name": private_model_audit.get("configured_model_name"),
            "response_route": core_turn_audit.get("response_route"),
            "model_call_count": len(model_calls),
            "model_calls": model_calls,
            "primary_model_call_started_at": primary_model_call.get("request_started_at"),
            "primary_model_call_ended_at": primary_model_call.get("request_ended_at"),
            "primary_model_call_wall_seconds": primary_model_call.get("request_wall_seconds"),
            "separate_model_load_start_end_available": False,
            "separate_model_load_boundary_unavailable_reason": (
                "ollama_nonstreaming_response_reports_load_duration_but_not_separate_load_timestamps"
            ),
            "ollama_total_seconds": duration_seconds_from_ns(
                ollama_metrics.get("total_duration")
            ),
            "ollama_load_seconds": duration_seconds_from_ns(
                ollama_metrics.get("load_duration")
            ),
            "ollama_prompt_eval_seconds": duration_seconds_from_ns(
                ollama_metrics.get("prompt_eval_duration")
            ),
            "ollama_eval_seconds": duration_seconds_from_ns(
                ollama_metrics.get("eval_duration")
            ),
            "first_token_available": primary_model_call.get("first_token_available"),
            "first_token_unavailable_reason": primary_model_call.get(
                "first_token_unavailable_reason"
            ),
            "exact_raw_model_replies": raw_model_replies,
            "initial_pipeline_reply": core_turn_audit.get("initial_pipeline_reply"),
            "core_cleanup_transformations": core_turn_audit.get("transformations"),
            "outer_cleanup_transformations": private_model_audit.get(
                "outer_transformations"
            ),
            "raw_shell_reply_before_movement_extraction": private_model_audit.get(
                "raw_shell_reply_before_movement_extraction"
            ),
            "movement_extraction_changed_reply": private_model_audit.get(
                "movement_extraction_changed_reply"
            ),
            "final_displayed_reply": private_model_audit.get("final_displayed_reply"),
        }
        report["voice_route"] = last_life_voice_output(started_at)

        visual_purge = request_binary_json(
            f"http://127.0.0.1:{VISUAL_PORT}/api/purge", b"{}",
            headers={
                "Content-Type": "application/json", "X-Kira-Visual-Token": visual_token,
                "X-Kira-Person": "kira", "X-Kira-Activation-Revision": activation_revision,
                "X-Kira-Sensory-Lease": original_sensory_lease,
            }, timeout=30,
        )
        visual_purged = visual_purge.get("ok") is True
        sensory_purge = request_json(
            f"{BASE_URL}/api/sensory/purge", token=shell_token, method="POST",
            body={"sensory_lease": original_sensory_lease},
        )
        sensory_purged = sensory_purge.get("ok") is True
        sensory_lease = str(sensory_purge.get("sensory_lease") or "")
        deactivate = request_json(
            f"{BASE_URL}/api/deactivate", token=shell_token, method="POST", body={}
        )
        deactivated = deactivate.get("ok") is True
        close = request_json(
            f"{BASE_URL}/api/safe-close", token=shell_token, method="POST",
            body={"reason": "bounded owner acceptance complete"},
        )
        safe_closed = close.get("ok") is True
        server.wait(timeout=30)

        close_deadline = time.monotonic() + 15
        while time.monotonic() < close_deadline and any(
            port_is_open(port) for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT)
        ):
            time.sleep(0.25)
        after_hashes = protected_hashes()
        after_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        after_ollama = ollama_inventory()
        report["cleanup"] = {
            "visual_sidecar_purged": visual_purged,
            "sensory_buffer_purged": sensory_purged,
            "kira_deactivated": deactivated,
            "safe_close_accepted": safe_closed,
            "server_exit_code": server.returncode,
            "shell_port_closed": not port_is_open(SHELL_PORT),
            "asr_port_closed": not port_is_open(ASR_PORT),
            "visual_port_closed": not port_is_open(VISUAL_PORT),
            "active_candidate_after": after_state.get("active_candidate"),
            "browser_lease_after": after_state.get("browser_lease"),
        }
        report["protected_after"] = after_hashes
        report["protected_files_unchanged"] = before_hashes == after_hashes
        report["ollama_after"] = after_ollama
        report["checks"] = {
            "launcher_ready": waiter.returncode == 0,
            "asr_ready": asr_health.get("status") == "ready",
            "visual_ready": visual_health.get("status") == "ready",
            "one_frame_only": True,
            "camera_device_opened": bool(report["visual_sample"]["device_opened"]),
            "camera_held_about_three_seconds": float(
                report["visual_sample"]["capture_elapsed_seconds"] or 0.0
            ) >= 2.5,
            "jpeg_nonempty_and_dimensioned": bool(
                report["visual_sample"]["encoded_nonempty"]
                and report["visual_sample"]["jpeg_dimensions"]["width"] > 0
                and report["visual_sample"]["jpeg_dimensions"]["height"] > 0
                and report["visual_sample"]["jpeg_dimensions_match_derived_cue"]
            ),
            "visual_cue_inserted": bool(
                report["visual_sample"]["insertion"]["accepted"]
                and report["visual_sample"]["insertion"]["cue_id"]
            ),
            "bounded_microphone_only": True,
            "microphone_device_opened": bool(
                report["microphone_sample"]["device_opened"]
            ),
            "microphone_format_valid": bool(
                report["microphone_sample"]["format_and_levels"]["codec"]
                == "pcm_s16le"
                and report["microphone_sample"]["format_and_levels"]["channels"] == 1
                and report["microphone_sample"]["format_and_levels"]["sample_rate_hz"]
                == 16000
            ),
            "microphone_transcript_nonempty": bool(
                report["microphone_sample"]["transcript_nonempty"]
            ),
            "auditory_cue_inserted": bool(
                report["microphone_sample"]["insertion"]["accepted"]
                and report["microphone_sample"]["insertion"]["cue_id"]
            ),
            "raw_media_not_persisted": bool(
                report["visual_sample"]["raw_frame_persisted"] is False
                and report["microphone_sample"]["raw_audio_persisted"] is False
                and report["privacy"]["raw_frame_written"] is False
                and report["privacy"]["raw_audio_written"] is False
            ),
            "private_prompt_insertion_proven": bool(
                report["prompt_snapshot_audit"]["one_turn_sensory_context_inserted"]
                and sorted(report["prompt_snapshot_audit"]["exact_inserted_cue_ids"] or [])
                == sorted(expected_cue_ids)
                and report["prompt_snapshot_audit"]["visual_brightness_present_exactly"]
                and report["prompt_snapshot_audit"]["visual_motion_present_exactly"]
                and report["prompt_snapshot_audit"]["temporary_transcript_present_exactly"]
            ),
            "exact_model_digest_proven": bool(model_digest),
            "raw_model_reply_audited": bool(raw_model_replies),
            "cleanup_transformations_audited": isinstance(
                report["model_audit"]["core_cleanup_transformations"],
                list,
            )
            and isinstance(
                report["model_audit"]["outer_cleanup_transformations"],
                list,
            ),
            "kira_replied": bool(report["conversation"]["displayed_reply"]),
            "voice_request_completed": "request_completed" in report["conversation"]["benchmark_events"],
            "approved_voice_path_proven": bool(report["voice_route"].get("voice_chunk_results")),
            "protected_files_unchanged": before_hashes == after_hashes,
            "person_inactive_after": not after_state.get("active_candidate"),
            "all_test_ports_closed": not any(port_is_open(port) for port in (SHELL_PORT, ASR_PORT, VISUAL_PORT)),
            "ollama_empty_after": not after_ollama.get("resident_models"),
        }
        report["passed"] = all(report["checks"].values())
        report["finished_at"] = utc_now()
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"passed": report["passed"], "report": relative(report_path)}, indent=2))
        return 0 if report["passed"] else 2
    except Exception as exc:
        report["failed_at"] = utc_now()
        report["failure"] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, CaptureError):
            report["capture_failure"] = capture_metadata(exc.result)
            exc.result.payload = b""
        raise
    finally:
        # Clear local byte variables before any evidence write in a failure path.
        jpeg = b"" if "jpeg" in locals() else b""
        wav = b"" if "wav" in locals() else b""
        transcript = "" if "transcript" in locals() else ""
        if "camera_capture" in locals() and isinstance(camera_capture, CaptureResult):
            camera_capture.payload = b""
        if "microphone_capture" in locals() and isinstance(microphone_capture, CaptureResult):
            microphone_capture.payload = b""
        if server is not None and server.poll() is None:
            try:
                if sensory_lease and not sensory_purged:
                    request_json(
                        f"{BASE_URL}/api/sensory/purge", token=shell_token,
                        method="POST", body={"sensory_lease": sensory_lease}, timeout=5,
                    )
            except Exception:
                pass
            try:
                if not deactivated:
                    request_json(f"{BASE_URL}/api/deactivate", token=shell_token, method="POST", body={}, timeout=5)
            except Exception:
                pass
            try:
                if not safe_closed:
                    request_json(
                        f"{BASE_URL}/api/safe-close", token=shell_token, method="POST",
                        body={"reason": "bounded owner acceptance cleanup"}, timeout=5,
                    )
                server.wait(timeout=15)
            except Exception:
                # This is the exact child created above; terminate no other PID.
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
        if output_dir.exists() and not report_path.exists():
            report["cleanup"] = {
                "visual_sidecar_purge_attempted": visual_purged,
                "sensory_buffer_purge_attempted": sensory_purged,
                "kira_deactivation_attempted": deactivated,
                "safe_close_attempted": safe_closed,
                "server_exit_code": server.returncode if server is not None else None,
                "shell_port_closed": not port_is_open(SHELL_PORT),
                "asr_port_closed": not port_is_open(ASR_PORT),
                "visual_port_closed": not port_is_open(VISUAL_PORT),
            }
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
