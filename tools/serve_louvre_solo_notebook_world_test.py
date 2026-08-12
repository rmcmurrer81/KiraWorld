#!/usr/bin/env python3
"""Serve only the hash-pinned Louvre bounded-circulation solo-review build.

This launcher deliberately does not import the Kira World Shell, TemporaryAI,
voice, Ollama, Home World, or TARDIS code.  It is a local, read-only review
server for one static notebook-world build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "preview"
)
DIST = PREVIEW / "dist"
MANIFEST_PATH = PREVIEW / "louvre_solo_pinned_build_manifest.json"
DEFAULT_PORT = 5183
LOOPBACK_HOST = "127.0.0.1"
REQUIRED_FALSE_ISOLATION_FLAGS = (
    "temporary_ai_activation_allowed",
    "voice_loaded",
    "ollama_loaded",
    "home_world_loaded",
    "home_world_mutation_allowed",
    "strip_mall_mutation_allowed",
    "runtime_registered",
    "interior_enabled",
    "full_louvre_interior_enabled",
    "elevators_enabled",
    "gallery_enabled",
    "artwork_enabled",
    "tardis_present_by_default",
)
REQUIRED_TRUE_ISOLATION_FLAGS = (
    "solo_review_only",
    "bounded_approximate_circulation_owner_review_enabled",
)
HEALTH_PROTOCOL = "louvre_bounded_circulation_owner_review_r4"


class PinnedBuildError(RuntimeError):
    """Raised when a source input or served output is no longer pinned."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def root_relative_path(raw_path: str) -> Path:
    path = (ROOT / raw_path).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PinnedBuildError(f"Manifest path escapes the project root: {raw_path}") from exc
    return path


def verify_item(item: dict[str, Any], *, expected_root: Path | None = None) -> Path:
    relative = str(item.get("path") or "")
    path = root_relative_path(relative)
    if expected_root is not None:
        try:
            path.relative_to(expected_root.resolve())
        except ValueError as exc:
            raise PinnedBuildError(f"Served file escapes the pinned dist folder: {relative}") from exc
    if not path.is_file():
        raise PinnedBuildError(f"Pinned file is missing: {relative}")
    actual_bytes = path.stat().st_size
    expected_bytes = int(item.get("bytes") or -1)
    if actual_bytes != expected_bytes:
        raise PinnedBuildError(
            f"Pinned byte count changed for {relative}: expected {expected_bytes}, got {actual_bytes}"
        )
    actual_hash = sha256_file(path)
    expected_hash = str(item.get("sha256") or "").lower()
    if actual_hash != expected_hash:
        raise PinnedBuildError(
            f"Pinned SHA-256 changed for {relative}: expected {expected_hash}, got {actual_hash}"
        )
    return path


def validate_pinned_build() -> tuple[dict[str, Any], dict[str, tuple[Path, dict[str, Any]]]]:
    if not MANIFEST_PATH.is_file():
        raise PinnedBuildError(f"Pinned build manifest is missing: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("manifest_kind") != "solo_review_code_pinned_notebook_world_build":
        raise PinnedBuildError("Unexpected Louvre pinned-build manifest kind")
    if manifest.get("status") != "prototype_draft_not_final_not_approved":
        raise PinnedBuildError("The Louvre test must remain explicitly unapproved and non-final")

    isolation = manifest.get("runtime_isolation") or {}
    missing_true = [name for name in REQUIRED_TRUE_ISOLATION_FLAGS if isolation.get(name) is not True]
    if missing_true:
        raise PinnedBuildError(f"Required owner-review scope flags are missing: {', '.join(missing_true)}")
    if int(isolation.get("people_loaded", -1)) != 0 or int(isolation.get("minds_loaded", -1)) != 0:
        raise PinnedBuildError("A person or mind is bound to this solo-review build")
    enabled = [name for name in REQUIRED_FALSE_ISOLATION_FLAGS if isolation.get(name) is not False]
    if enabled:
        raise PinnedBuildError(f"Isolation flags are not fail-closed: {', '.join(enabled)}")

    review_bookmarks = manifest.get("review_bookmarks") or []
    bookmark_ids = [str(item.get("id") or "") for item in review_bookmarks]
    if not bookmark_ids or any(not bookmark_id for bookmark_id in bookmark_ids):
        raise PinnedBuildError("The owner-review build has no valid fixed bookmark IDs")
    if len(bookmark_ids) != len(set(bookmark_ids)):
        raise PinnedBuildError("The owner-review build has duplicate bookmark IDs")

    for item in manifest.get("source_inputs") or []:
        verify_item(item)

    served: dict[str, tuple[Path, dict[str, Any]]] = {}
    pinned_dist_paths: set[Path] = set()
    for item in manifest.get("served_files") or []:
        url = str(item.get("url") or "")
        if not url.startswith("/") or "?" in url or "#" in url:
            raise PinnedBuildError(f"Invalid served URL in manifest: {url!r}")
        if url in served:
            raise PinnedBuildError(f"Duplicate served URL in manifest: {url}")
        path = verify_item(item, expected_root=DIST)
        served[url] = (path, item)
        pinned_dist_paths.add(path.resolve())

    if "/index.html" not in served:
        raise PinnedBuildError("Pinned build has no /index.html entrypoint")
    actual_dist_paths = {path.resolve() for path in DIST.rglob("*") if path.is_file()}
    unexpected = sorted(str(path.relative_to(DIST)) for path in actual_dist_paths - pinned_dist_paths)
    missing = sorted(str(path.relative_to(DIST)) for path in pinned_dist_paths - actual_dist_paths)
    if unexpected or missing:
        raise PinnedBuildError(
            f"Dist folder differs from manifest; unexpected={unexpected or []}, missing={missing or []}"
        )

    served["/"] = served["/index.html"]
    return manifest, served


class LouvreSoloHandler(BaseHTTPRequestHandler):
    server_version = "LouvreSoloReview/1.3"

    def _send_headers(self, status: int, content_type: str, content_length: int = 0) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), usb=(), payment=(), clipboard-write=(self)",
        )
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
            "connect-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'",
        )
        self.end_headers()

    def _serve(self, *, include_body: bool) -> None:
        split = urlsplit(self.path)
        requested_path = unquote(split.path or "/")
        if requested_path == "/favicon.ico":
            self._send_headers(204, "image/x-icon", 0)
            return

        try:
            manifest, served = validate_pinned_build()
        except (OSError, ValueError, json.JSONDecodeError, PinnedBuildError) as exc:
            payload = f"Pinned Louvre build refused: {exc}\n".encode("utf-8")
            self._send_headers(503, "text/plain; charset=utf-8", len(payload))
            if include_body:
                self.wfile.write(payload)
            return

        if requested_path == "/healthz":
            isolation = manifest["runtime_isolation"]
            payload = json.dumps(
                {
                    "service": "louvre_solo_owner_review",
                    "protocol": HEALTH_PROTOCOL,
                    "ready": True,
                    "build_id": manifest["build_id"],
                    "status": manifest["status"],
                    "launch_url": f"http://{LOOPBACK_HOST}:{self.server.server_port}/?solo=1&bookmark=arrival_scale",
                    "isolation": {
                        "solo_review_only": isolation["solo_review_only"],
                        "people_loaded": isolation["people_loaded"],
                        "minds_loaded": isolation["minds_loaded"],
                        "temporary_ai_activation_allowed": isolation["temporary_ai_activation_allowed"],
                        "bounded_approximate_circulation_owner_review_enabled": isolation["bounded_approximate_circulation_owner_review_enabled"],
                        "full_louvre_interior_enabled": isolation["full_louvre_interior_enabled"],
                        "elevators_enabled": isolation["elevators_enabled"],
                        "gallery_enabled": isolation["gallery_enabled"],
                        "artwork_enabled": isolation["artwork_enabled"],
                    },
                },
                sort_keys=True,
            ).encode("utf-8")
            self._send_headers(200, "application/json; charset=utf-8", len(payload))
            if include_body:
                self.wfile.write(payload)
            return

        if requested_path in {"/", "/index.html"}:
            query = parse_qs(split.query, keep_blank_values=True)
            allowed_bookmarks = {str(item["id"]) for item in manifest["review_bookmarks"]}
            bookmark_values = query.get("bookmark", [])
            query_is_valid = (
                query.get("solo") == ["1"]
                and set(query).issubset({"solo", "bookmark"})
                and (not bookmark_values or (len(bookmark_values) == 1 and bookmark_values[0] in allowed_bookmarks))
            )
            if not query_is_valid:
                self.send_response(302)
                self.send_header("Location", "/?solo=1&bookmark=arrival_scale")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.end_headers()
                return

        record = served.get(requested_path)
        if record is None:
            payload = b"Not found in the pinned Louvre solo build.\n"
            self._send_headers(404, "text/plain; charset=utf-8", len(payload))
            if include_body:
                self.wfile.write(payload)
            return

        path, _item = record
        payload = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        self._send_headers(200, content_type, len(payload))
        if include_body:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._serve(include_body=True)

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._serve(include_body=False)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        payload = b"This solo-review server is read-only.\n"
        self._send_headers(405, "text/plain; charset=utf-8", len(payload))
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write(f"[Louvre solo] {self.address_string()} - {format % args}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically")
    parser.add_argument("--verify-only", action="store_true", help="Verify hashes and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest, served = validate_pinned_build()
    except (OSError, ValueError, json.JSONDecodeError, PinnedBuildError) as exc:
        print(f"Louvre solo build verification FAILED: {exc}", file=sys.stderr)
        return 2

    print(
        "Verified Louvre bounded-circulation solo build "
        f"{manifest['build_id']} ({len(served) - 1} pinned files; no person, mind, voice, TARDIS, or Home World)."
    )
    if args.verify_only:
        return 0

    if not (1 <= args.port <= 65535):
        print(f"Invalid port: {args.port}", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((LOOPBACK_HOST, args.port), LouvreSoloHandler)
    server.daemon_threads = True
    url = f"http://{LOOPBACK_HOST}:{args.port}/?solo=1&bookmark=arrival_scale"
    print(f"Serving read-only Louvre bounded-circulation solo test at {url}")
    print("Press Ctrl+C to stop. Feedback stays in this browser unless exported as JSON.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping Louvre solo test.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
