from __future__ import annotations

"""Process-isolated, cache-only ASR service for Kira Text + Voice Chat.

The browser sends one push-to-talk recording at a time.  Audio stays in memory,
is never written by this service, and is discarded immediately after the
transcript response.  This process neither imports nor changes Chatterbox.
"""

import argparse
import hmac
import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.sensory_lease import SensoryLeaseError, validate_sensory_lease
from Core.process_liveness import process_is_alive


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8770
DEFAULT_MODEL_ID = "Systran/faster-whisper-small.en"
MAX_AUDIO_BYTES = 12 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/mp4",
    "application/octet-stream",
}

_MODEL: Any | None = None
_MODEL_LOCK = threading.Lock()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _model_cache_root(model_id: str = DEFAULT_MODEL_ID) -> Path:
    explicit = str(os.environ.get("KIRA_ASR_MODEL_PATH", "")).strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    cache_name = "models--" + model_id.replace("/", "--")
    return Path.home() / ".cache" / "huggingface" / "hub" / cache_name


def resolve_cached_model_path(model_id: str = DEFAULT_MODEL_ID) -> Path | None:
    root = _model_cache_root(model_id)
    if (root / "model.bin").is_file():
        return root
    snapshots = root / "snapshots"
    if not snapshots.is_dir():
        return None
    candidates = sorted(
        (item for item in snapshots.iterdir() if item.is_dir() and (item / "model.bin").is_file()),
        key=lambda item: item.name,
    )
    return candidates[-1] if candidates else None


def health_payload() -> dict[str, Any]:
    model_path = resolve_cached_model_path()
    try:
        import faster_whisper  # noqa: F401

        package_available = True
    except Exception:
        package_available = False
    ready = bool(package_available and model_path)
    return {
        "service": "kira_text_voice_asr_sidecar",
        "status": "ready" if ready else "blocked",
        "process_isolated": True,
        "cache_only": True,
        "model_id": DEFAULT_MODEL_ID,
        "cached_model_path": str(model_path) if model_path else "",
        "package_available": package_available,
        "raw_audio_persisted": False,
        "transcript_requires_user_review": True,
        "automatic_send": False,
        "visual_understanding_enabled": False,
        "person_activation_lease_required": True,
    }


def load_model() -> Any:
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        model_path = resolve_cached_model_path()
        if model_path is None:
            raise RuntimeError("approved cache-only faster-whisper model is unavailable")
        from faster_whisper import WhisperModel

        _MODEL = WhisperModel(str(model_path), device="cpu", compute_type="int8")
        return _MODEL


def transcribe_audio_bytes(audio: bytes, *, model: Any | None = None) -> dict[str, Any]:
    if not audio:
        raise ValueError("empty audio payload")
    if len(audio) > MAX_AUDIO_BYTES:
        raise ValueError(f"audio payload exceeds {MAX_AUDIO_BYTES} bytes")
    transcriber = model if model is not None else load_model()
    segments, info = transcriber.transcribe(
        io.BytesIO(audio),
        language="en",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
        temperature=0.0,
    )
    segment_rows = []
    transcript_parts = []
    for segment in segments:
        text = str(getattr(segment, "text", "")).strip()
        if text:
            transcript_parts.append(text)
        segment_rows.append(
            {
                "start": round(float(getattr(segment, "start", 0.0)), 3),
                "end": round(float(getattr(segment, "end", 0.0)), 3),
                "text": text,
            }
        )
    return {
        "ok": True,
        "text": " ".join(transcript_parts).strip(),
        "segments": segment_rows,
        "language": str(getattr(info, "language", "en")),
        "language_probability": round(float(getattr(info, "language_probability", 0.0)), 6),
        "audio_bytes_received": len(audio),
        "raw_audio_persisted": False,
        "editable_before_send": True,
        "automatic_send": False,
        "model_id": DEFAULT_MODEL_ID,
    }


def stop_when_parent_exits(server: ThreadingHTTPServer, parent_pid: int) -> None:
    while process_is_alive(parent_pid):
        threading.Event().wait(0.5)
    server.shutdown()


class AsrHandler(BaseHTTPRequestHandler):
    server_version = "KiraTextVoiceASR/1.0"

    def _allowed_origin(self) -> str:
        origin = str(self.headers.get("Origin", "")).strip()
        allowed = {
            item.strip()
            for item in str(
                os.environ.get(
                    "KIRA_ASR_ALLOWED_ORIGINS",
                    "http://127.0.0.1:8768,http://localhost:8768",
                )
            ).split(",")
            if item.strip()
        }
        return origin if origin in allowed else ""

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self._allowed_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = str(os.environ.get("KIRA_ASR_SESSION_TOKEN", "")).strip()
        supplied = str(self.headers.get("X-Kira-ASR-Token", "")).strip()
        return bool(expected and supplied and hmac.compare_digest(expected, supplied))

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._allowed_origin():
            self._send_json(403, {"ok": False, "error": "origin_not_allowed"})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Kira-ASR-Token, X-Kira-Person, "
            "X-Kira-Activation-Revision, X-Kira-Sensory-Lease",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/health":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        if not self._authorized():
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return
        self._send_json(200, health_payload())

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/transcribe":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        if not self._authorized():
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return
        person = str(self.headers.get("X-Kira-Person", "")).strip()
        activation_revision = str(self.headers.get("X-Kira-Activation-Revision", "")).strip()
        sensory_lease = str(self.headers.get("X-Kira-Sensory-Lease", "")).strip()
        lease_secret = str(os.environ.get("KIRA_SENSORY_LEASE_SECRET", "")).strip()
        if not person or not activation_revision or not sensory_lease or not lease_secret:
            self._send_json(400, {"ok": False, "error": "person_activation_lease_required"})
            return
        try:
            validate_sensory_lease(
                sensory_lease,
                lease_secret,
                expected_person_id=person,
                expected_activation_revision=activation_revision,
            )
        except SensoryLeaseError as exc:
            self._send_json(409, {"ok": False, "error": "sensory_lease_invalid", "message": str(exc)})
            return
        content_type = str(self.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            self._send_json(415, {"ok": False, "error": "unsupported_audio_type"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length < 1 or content_length > MAX_AUDIO_BYTES:
            self._send_json(413, {"ok": False, "error": "invalid_audio_size", "max_bytes": MAX_AUDIO_BYTES})
            return
        audio = self.rfile.read(content_length)
        try:
            result = transcribe_audio_bytes(audio)
        except Exception as exc:
            self._send_json(422, {"ok": False, "error": "transcription_failed", "message": str(exc)})
            return
        result["selected_person"] = person
        result["activation_revision"] = activation_revision
        self._send_json(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the cache-only Kira Text + Voice ASR sidecar.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument("--health", action="store_true", help="Print cache/package readiness and exit.")
    args = parser.parse_args()
    if args.health:
        print(json.dumps(health_payload(), indent=2))
        return 0 if health_payload()["status"] == "ready" else 2
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("ASR sidecar must remain bound to loopback")
    if not str(os.environ.get("KIRA_ASR_SESSION_TOKEN", "")).strip():
        raise SystemExit("KIRA_ASR_SESSION_TOKEN is required")
    if len(str(os.environ.get("KIRA_SENSORY_LEASE_SECRET", "")).strip()) < 32:
        raise SystemExit("KIRA_SENSORY_LEASE_SECRET is required")
    server = ThreadingHTTPServer((args.host, args.port), AsrHandler)
    if args.parent_pid:
        threading.Thread(
            target=stop_when_parent_exits,
            args=(server, args.parent_pid),
            daemon=True,
            name="kira-asr-parent-watch",
        ).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
