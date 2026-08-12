#!/usr/bin/env python3
"""Loopback-only UI for explicit multiview owner review artifacts.

There are intentionally no queue, mesh, render, export, or activation routes.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import secrets
import sys
import threading
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse
import webbrowser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_multiview_owner_review import (  # noqa: E402
    AvatarOwnerReviewError,
    build_owner_review_report,
    load_owner_review_session,
    resolve_exact_source_image,
    save_base_owner_review,
    save_scale_owner_review,
    save_source_owner_review,
)


LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8876
MAX_JSON_BYTES = 1024 * 1024
MAX_PRIVATE_IMAGE_BYTES = 128 * 1024 * 1024
UI_PATH = Path(__file__).with_name("avatar_multiview_owner_review_ui.html")


def is_loopback_peer(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def valid_loopback_host_header(value: str, port: int) -> bool:
    allowed = {
        LOOPBACK_HOST,
        f"{LOOPBACK_HOST}:{port}",
        "localhost",
        f"localhost:{port}",
        "[::1]",
        f"[::1]:{port}",
    }
    return value.strip().lower() in allowed


def valid_loopback_origin(value: str, port: int) -> bool:
    return value.strip().lower() in {
        f"http://{LOOPBACK_HOST}:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
    }


def valid_loopback_referer(value: str, port: int) -> bool:
    parsed = urlparse(value)
    if parsed.scheme.lower() != "http":
        return False
    return valid_loopback_origin(
        f"http://{parsed.netloc}", port
    ) and parsed.path.startswith("/")


class OwnerReviewApplication:
    """Stateful, lock-serialized adapter around the owner-review core."""

    def __init__(
        self,
        project_root: Path,
        manifest_path: Path,
        *,
        reviewer_id: str,
        csrf_token: str | None = None,
        source_token_key: bytes | None = None,
    ) -> None:
        self.project_root = project_root.resolve(strict=True)
        self.manifest_path = manifest_path
        self.reviewer_id = reviewer_id
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)
        self._source_token_key = source_token_key or secrets.token_bytes(32)
        self._lock = threading.RLock()
        # Fail before binding a server if any manifest/source boundary is unsafe.
        load_owner_review_session(
            self.project_root,
            self.manifest_path,
            reviewer_id=self.reviewer_id,
        )

    def _source_token(self, source_id: str, source_sha256: str) -> str:
        message = f"{source_id}\0{source_sha256}".encode("utf-8")
        return hmac.new(
            self._source_token_key, message, hashlib.sha256
        ).hexdigest()

    def session_payload(self) -> dict[str, Any]:
        with self._lock:
            session = load_owner_review_session(
                self.project_root,
                self.manifest_path,
                reviewer_id=self.reviewer_id,
            )
            manifest_sha = session["manifest_sha256"]
            for source in session["source_images"]:
                token = self._source_token(source["source_id"], source["sha256"])
                source["image_url"] = (
                    f"/private/source/{token}?manifest_sha256={manifest_sha}"
                    f"&source_sha256={source['sha256']}"
                )
            return session

    def resolve_source(
        self,
        token: str,
        *,
        manifest_sha256: str,
        source_sha256: str,
    ) -> tuple[bytes, str]:
        with self._lock:
            session = load_owner_review_session(
                self.project_root,
                self.manifest_path,
                reviewer_id=self.reviewer_id,
            )
            if manifest_sha256 != session["manifest_sha256"]:
                raise AvatarOwnerReviewError(
                    "source URL is stale; refresh the owner review page"
                )
            matched_source: Mapping[str, Any] | None = None
            for source in session["source_images"]:
                expected_token = self._source_token(
                    source["source_id"], source["sha256"]
                )
                if hmac.compare_digest(token, expected_token):
                    matched_source = source
                    break
            if matched_source is None:
                raise AvatarOwnerReviewError("private source token is invalid")
            if not hmac.compare_digest(
                source_sha256, str(matched_source["sha256"])
            ):
                raise AvatarOwnerReviewError("private source hash is invalid")
            path, media_type, size = resolve_exact_source_image(
                self.project_root,
                self.manifest_path,
                source_id=str(matched_source["source_id"]),
                expected_manifest_sha256=manifest_sha256,
                expected_source_sha256=source_sha256,
            )
            if size < 1 or size > MAX_PRIVATE_IMAGE_BYTES:
                raise AvatarOwnerReviewError(
                    "private source size is outside the local review limit"
                )
            # Rehash the exact bytes that will be sent, closing the path-check /
            # stream-open time-of-check gap.
            payload = path.read_bytes()
            if not hmac.compare_digest(
                hashlib.sha256(payload).hexdigest(), source_sha256
            ):
                raise AvatarOwnerReviewError(
                    "private source changed before exact bytes could be served"
                )
            return payload, media_type

    def report(self) -> str:
        with self._lock:
            return build_owner_review_report(
                self.project_root,
                self.manifest_path,
                reviewer_id=self.reviewer_id,
            )

    def save_source(
        self, expected_manifest_sha256: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            return save_source_owner_review(
                self.project_root,
                self.manifest_path,
                reviewer_id=self.reviewer_id,
                expected_manifest_sha256=expected_manifest_sha256,
                payload=payload,
            )

    def save_scale(
        self, expected_manifest_sha256: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            return save_scale_owner_review(
                self.project_root,
                self.manifest_path,
                reviewer_id=self.reviewer_id,
                expected_manifest_sha256=expected_manifest_sha256,
                payload=payload,
            )

    def save_base(
        self, expected_manifest_sha256: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            return save_base_owner_review(
                self.project_root,
                self.manifest_path,
                reviewer_id=self.reviewer_id,
                expected_manifest_sha256=expected_manifest_sha256,
                payload=payload,
            )

    def render_ui(self) -> bytes:
        try:
            template = UI_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            raise AvatarOwnerReviewError("owner review UI is missing") from exc
        return template.replace(
            "__CSRF_TOKEN_JSON__", json.dumps(self.csrf_token)
        ).encode("utf-8")


class OwnerReviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        app: OwnerReviewApplication,
    ) -> None:
        self.app = app
        super().__init__(server_address, OwnerReviewRequestHandler)


class OwnerReviewRequestHandler(BaseHTTPRequestHandler):
    server: OwnerReviewHTTPServer

    def _request_is_loopback_safe(self) -> bool:
        return is_loopback_peer(self.client_address[0]) and valid_loopback_host_header(
            self.headers.get("Host", ""), self.server.server_port
        )

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self'; connect-src 'self'; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )

    def _send_bytes(
        self,
        status: int,
        payload: bytes,
        content_type: str,
    ) -> None:
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
        self._send_bytes(
            status,
            json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(
            status,
            {
                "error": message,
                "body_queued": False,
                "mesh_created": False,
                "runtime_activation_allowed": False,
            },
        )

    def _csrf_is_valid(self) -> bool:
        supplied = self.headers.get("X-Owner-Review-CSRF", "")
        return hmac.compare_digest(supplied, self.server.app.csrf_token)

    def _require_api_get(self) -> bool:
        if not self._request_is_loopback_safe():
            self._send_error_json(403, "loopback host/peer check failed")
            return False
        if not self._csrf_is_valid():
            self._send_error_json(403, "owner review session token is missing")
            return False
        return True

    def _read_json_request(self) -> dict[str, Any]:
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise AvatarOwnerReviewError("Content-Type must be application/json")
        if self.headers.get("Transfer-Encoding"):
            raise AvatarOwnerReviewError("chunked request bodies are not accepted")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError as exc:
            raise AvatarOwnerReviewError("Content-Length is invalid") from exc
        if length < 2 or length > MAX_JSON_BYTES:
            raise AvatarOwnerReviewError("JSON request size is invalid")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise AvatarOwnerReviewError("request JSON is invalid") from exc
        if not isinstance(value, dict):
            raise AvatarOwnerReviewError("request JSON must be an object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not self._request_is_loopback_safe():
            self._send_error_json(403, "loopback host/peer check failed")
            return
        try:
            if parsed.path == "/":
                self._send_bytes(
                    200,
                    self.server.app.render_ui(),
                    "text/html; charset=utf-8",
                )
                return
            if parsed.path == "/api/session":
                if not self._require_api_get():
                    return
                self._send_json(200, self.server.app.session_payload())
                return
            if parsed.path == "/api/report":
                if not self._require_api_get():
                    return
                self._send_bytes(
                    200,
                    self.server.app.report().encode("utf-8"),
                    "text/markdown; charset=utf-8",
                )
                return
            if parsed.path.startswith("/private/source/"):
                if not valid_loopback_referer(
                    self.headers.get("Referer", ""), self.server.server_port
                ):
                    self._send_error_json(403, "private source referer is invalid")
                    return
                token = parsed.path.removeprefix("/private/source/")
                query = parse_qs(parsed.query, strict_parsing=True)
                if set(query) != {"manifest_sha256", "source_sha256"} or any(
                    len(values) != 1 for values in query.values()
                ):
                    raise AvatarOwnerReviewError("private source binding is invalid")
                payload, media_type = self.server.app.resolve_source(
                    token,
                    manifest_sha256=query["manifest_sha256"][0],
                    source_sha256=query["source_sha256"][0],
                )
                self.send_response(200)
                self._security_headers()
                self.send_header("Content-Type", media_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Content-Disposition", "inline")
                self.end_headers()
                self.wfile.write(payload)
                return
            self._send_error_json(404, "route not found")
        except (AvatarOwnerReviewError, OSError, ValueError) as exc:
            self._send_error_json(409, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        if not self._request_is_loopback_safe():
            self._send_error_json(403, "loopback host/peer check failed")
            return
        if not valid_loopback_origin(
            self.headers.get("Origin", ""), self.server.server_port
        ):
            self._send_error_json(403, "loopback Origin check failed")
            return
        if not self._csrf_is_valid():
            self._send_error_json(403, "owner review session token is missing")
            return
        try:
            request = self._read_json_request()
            expected_sha = str(request.get("expected_manifest_sha256") or "").strip()
            payload = request.get("payload")
            if not expected_sha or not isinstance(payload, Mapping):
                raise AvatarOwnerReviewError(
                    "current manifest hash and review payload are required"
                )
            if self.path == "/api/review/source":
                result = self.server.app.save_source(expected_sha, payload)
            elif self.path == "/api/review/scale":
                result = self.server.app.save_scale(expected_sha, payload)
            elif self.path == "/api/review/base":
                result = self.server.app.save_base(expected_sha, payload)
            else:
                self._send_error_json(404, "route not found")
                return
            self._send_json(200, result)
        except (AvatarOwnerReviewError, OSError, ValueError) as exc:
            self._send_error_json(409, str(exc))

    def log_message(self, format: str, *args: Any) -> None:
        # Avoid writing private source tokens or query hashes to routine logs.
        if "/private/source/" in str(args[0] if args else ""):
            return
        super().log_message(format, *args)


def _safe_report_output(project_root: Path, raw_path: str) -> Path:
    root = project_root.resolve(strict=True)
    raw = Path(raw_path)
    if raw.is_absolute() or ".." in raw.parts or raw.suffix.lower() != ".md":
        raise AvatarOwnerReviewError(
            "report output must be a project-relative Markdown path"
        )
    destination = root / raw
    allowed = root / "Data" / "codex_reports"
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.resolve().relative_to(allowed.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise AvatarOwnerReviewError(
            "report output must stay under Data/codex_reports"
        ) from exc
    if destination.is_symlink():
        raise AvatarOwnerReviewError("report output cannot be a symlink")
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Loopback-only explicit owner review for avatar multiview evidence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("serve", "report"):
        child = subparsers.add_parser(command)
        child.add_argument("--manifest", required=True)
        child.add_argument("--reviewer-id", default="robert_owner")
    serve = subparsers.choices["serve"]
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--open-browser", action="store_true")
    report = subparsers.choices["report"]
    report.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest_path = Path(args.manifest)
    try:
        if args.command == "report":
            report = build_owner_review_report(
                PROJECT_ROOT,
                manifest_path,
                reviewer_id=args.reviewer_id,
            )
            if args.output:
                destination = _safe_report_output(PROJECT_ROOT, args.output)
                destination.write_text(report, encoding="utf-8")
                print(destination.relative_to(PROJECT_ROOT).as_posix())
            else:
                print(report)
            return 0
        if not 0 <= args.port <= 65535:
            raise AvatarOwnerReviewError("port is invalid")
        app = OwnerReviewApplication(
            PROJECT_ROOT,
            manifest_path,
            reviewer_id=args.reviewer_id,
        )
        server = OwnerReviewHTTPServer((LOOPBACK_HOST, args.port), app)
        address = f"http://{LOOPBACK_HOST}:{server.server_port}/"
        print(f"Private owner review: {address}")
        print("Queue/build/export/activation operations are unavailable.")
        if args.open_browser:
            threading.Timer(0.2, lambda: webbrowser.open(address)).start()
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    except AvatarOwnerReviewError as exc:
        print(f"owner review blocked: {exc}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
