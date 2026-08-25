"""Dependency-free loopback HTTP/JSON adapter."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .errors import AuthenticationError, NotFoundError, ValidationError, VoiceStudioError
from .models import SynthesisRequest
from .service import LocalVoiceService

MAX_BODY_BYTES = 32 * 1024
_TOKEN = re.compile(r"^[a-f0-9]{64}$")


def load_or_create_api_token(data_root: Path) -> str:
    """Create a per-install capability token outside public API records."""

    root = data_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".api_capability_token"
    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        raise ValidationError("API token path cannot be a link or junction")
    if not path.exists():
        token = os.urandom(32).hex()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w", encoding="ascii", newline="\n") as handle:
                handle.write(token + "\n")
                handle.flush()
                os.fsync(handle.fileno())
    try:
        info = path.stat(follow_symlinks=False)
        token = path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise ValidationError("API capability token is unavailable") from exc
    if not stat.S_ISREG(info.st_mode) or not _TOKEN.fullmatch(token):
        raise ValidationError("API capability token is invalid")
    return token


def assert_loopback_bind(host: str) -> None:
    if host != "127.0.0.1":
        raise ValidationError("bind host must be exactly 127.0.0.1")


def make_handler(service: LocalVoiceService, api_token: str):
    if not isinstance(api_token, str) or not _TOKEN.fullmatch(api_token):
        raise ValidationError("a 256-bit API capability token is required")
    rate_lock = threading.Lock()
    rate_window = {"started": time.monotonic(), "count": 0}
    class Handler(BaseHTTPRequestHandler):
        server_version = "KiraLocalVoice/0.1"

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(5.0)

        def do_GET(self) -> None:  # noqa: N802
            try:
                self._require_local_host()
                self._require_authentication()
                path = urlsplit(self.path).path
                if path == "/v1/health":
                    self._send(200, service.health())
                elif path == "/v1/capabilities":
                    self._send(200, service.capabilities())
                elif path == "/v1/voices":
                    self._send(200, {"voices": [{
                        "voice_id": voice.voice_id, "display_name": voice.display_name,
                        "source_basis": voice.source_basis.value,
                        "audition_status": voice.audition_status.value,
                        "language": voice.language, "description": voice.description,
                        "active": not service.registry.is_deactivated(voice.voice_id),
                    } for voice in service.registry.list()]})
                elif path.startswith("/v1/jobs/"):
                    self._send(200, service.get_job(path.removeprefix("/v1/jobs/")).to_dict())
                else:
                    raise NotFoundError("route not found")
            except VoiceStudioError as exc:
                self._problem(exc)

        def do_POST(self) -> None:  # noqa: N802
            try:
                self._require_local_host()
                self._require_authentication()
                path = urlsplit(self.path).path
                if path == "/v1/synthesis-jobs":
                    payload = self._json_body()
                    allowed={"text","voice_id","output_name","language","speed","style","metadata"}
                    if set(payload)-allowed:
                        raise ValidationError("request contains unknown fields")
                    request = SynthesisRequest(
                        text=payload.get("text", ""),
                        voice_id=payload.get("voice_id", ""),
                        output_name=payload.get("output_name"),
                        language=payload.get("language", "en-US"),
                        speed=payload.get("speed", 1.0),
                        style=payload.get("style", "neutral"),
                        metadata=payload.get("metadata", {}),
                    )
                    self._send(202, service.submit(request).to_dict())
                elif path.startswith("/v1/jobs/") and path.endswith("/cancel"):
                    job_id = path.removeprefix("/v1/jobs/").removesuffix("/cancel").rstrip("/")
                    self._send(200, service.cancel_job(job_id).to_dict())
                else:
                    raise NotFoundError("route not found")
            except VoiceStudioError as exc:
                self._problem(exc)
            except (TypeError, ValueError) as exc:
                self._problem(ValidationError(str(exc)))

        def _json_body(self) -> dict:
            raw_length = self.headers.get("Content-Length", "")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValidationError("Content-Length must be an integer") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise ValidationError("request body is outside the allowed size")
            if self.headers.get_content_type() != "application/json":
                raise ValidationError("Content-Type must be application/json")
            def strict_object(pairs):
                result={}
                for key,value in pairs:
                    if key in result: raise ValueError("duplicate JSON key")
                    result[key]=value
                return result
            try:
                payload = json.loads(self.rfile.read(length),object_pairs_hook=strict_object,
                    parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("non-finite number")))
            except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as exc:
                raise ValidationError("request body is not valid JSON") from exc
            if not isinstance(payload, dict):
                raise ValidationError("request body must be a JSON object")
            return payload

        def _require_local_host(self) -> None:
            host = self.headers.get("Host", "").rsplit(":", 1)[0].strip("[]").lower()
            if host not in {"127.0.0.1", "localhost"}:
                raise ValidationError("Host header must address the loopback service")
            with rate_lock:
                now = time.monotonic()
                if now - rate_window["started"] >= 60:
                    rate_window.update(started=now, count=0)
                rate_window["count"] += 1
                if rate_window["count"] > 240:
                    raise ValidationError("local request rate limit exceeded")

        def _require_authentication(self) -> None:
            supplied = self.headers.get("Authorization", "")
            expected = f"Bearer {api_token}"
            if not hmac.compare_digest(supplied, expected):
                raise AuthenticationError("local API capability token is required")

        def _problem(self, exc: VoiceStudioError) -> None:
            safe_messages = {
                "authentication_required": "local API authentication is required",
                "not_found": "resource not found",
                "conflict": "request conflicts with current local state",
                "backend_unavailable": "local synthesis backend is unavailable",
                "cancelled": "request was cancelled",
                "validation_error": "request was rejected by local validation",
            }
            self._send(
                exc.http_status,
                {"error": {"code": exc.code, "message": safe_messages.get(exc.code, "request failed")}},
            )

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args) -> None:
            # Keep text, voice IDs, and local paths out of default access logs.
            del format, args

    return Handler


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Loopback server with a hard request-thread ceiling."""

    daemon_threads = True
    request_queue_size = 16

    def __init__(self, *args, max_request_threads: int = 16, **kwargs):
        self._request_slots = threading.BoundedSemaphore(max_request_threads)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address) -> None:
        if not self._request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


def serve(host: str, port: int, data_root: Path) -> None:
    assert_loopback_bind(host)
    service = LocalVoiceService(data_root)
    token = load_or_create_api_token(data_root)
    server = BoundedThreadingHTTPServer((host, port), make_handler(service, token))
    try:
        server.serve_forever()
    finally:
        server.server_close()
        service.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kira Labs local voice API contract server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-root", type=Path, default=Path(".local_voice_data"))
    args = parser.parse_args()
    serve(args.host, args.port, args.data_root)


if __name__ == "__main__":
    main()
