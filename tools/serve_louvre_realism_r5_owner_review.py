#!/usr/bin/env python3
"""Serve only the hash-pinned Louvre R5 bounded realism owner-review build.

This local read-only server does not import Kira World Shell, TemporaryAI,
voice, Ollama, Home World, TARDIS, or any person runtime.
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
    / "notebook_world_louvre_realism_r5_20260716_190000"
    / "preview"
)
DIST = PREVIEW / "dist"
MANIFEST_PATH = PREVIEW / "louvre_realism_r5_pinned_manifest.json"
DEFAULT_PORT = 5195
LOOPBACK_HOST = "127.0.0.1"
HEALTH_PROTOCOL = "louvre_real_model_context_owner_review_r5"
REQUIRED_FALSE_FLAGS = (
    "temporary_ai_activation_allowed",
    "person_systems_loaded",
    "mind_systems_loaded",
    "voice_systems_loaded",
    "ollama_loaded",
    "home_world_loaded",
    "home_world_mutation_allowed",
    "runtime_registered",
    "bounded_approximate_circulation_enabled",
    "full_louvre_interior_enabled",
    "working_door_enabled",
    "working_stairs_enabled",
    "working_elevator_enabled",
    "working_escalator_enabled",
    "gallery_inventory_enabled",
    "artwork_inventory_enabled",
    "tardis_present_by_default",
)
REQUIRED_TRUE_FLAGS = (
    "solo_review_only",
    "bounded_realism_owner_review_enabled",
    "supplied_site_context_enabled",
    "supplied_pavillon_sully_facade_enabled",
)


class PinnedBuildError(RuntimeError):
    """Raised when a source input or served output no longer matches its pin."""


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
        raise PinnedBuildError(f"Manifest path escapes project root: {raw_path}") from exc
    return path


def verify_item(item: dict[str, Any], *, expected_root: Path | None = None) -> Path:
    relative = str(item.get("path") or "")
    path = root_relative_path(relative)
    if expected_root is not None:
        try:
            path.relative_to(expected_root.resolve())
        except ValueError as exc:
            raise PinnedBuildError(f"Served file escapes pinned dist: {relative}") from exc
    if not path.is_file():
        raise PinnedBuildError(f"Pinned file is missing: {relative}")
    actual_bytes = path.stat().st_size
    expected_bytes = int(item.get("bytes", -1))
    if actual_bytes != expected_bytes:
        raise PinnedBuildError(f"Byte count changed for {relative}: expected {expected_bytes}, got {actual_bytes}")
    actual_hash = sha256_file(path)
    expected_hash = str(item.get("sha256") or "").lower()
    if actual_hash != expected_hash:
        raise PinnedBuildError(f"SHA-256 changed for {relative}: expected {expected_hash}, got {actual_hash}")
    return path


def validate_pinned_build() -> tuple[dict[str, Any], dict[str, tuple[Path, dict[str, Any]]]]:
    if not MANIFEST_PATH.is_file():
        raise PinnedBuildError(f"Manifest is missing: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("manifest_kind") != "louvre_realism_r5_pinned_owner_review":
        raise PinnedBuildError("Unexpected R5 manifest kind")
    if manifest.get("status") != "bounded_owner_review_not_complete_not_approved":
        raise PinnedBuildError("R5 must remain bounded, incomplete, and unapproved")
    isolation = manifest.get("runtime_isolation") or {}
    missing_true = [name for name in REQUIRED_TRUE_FLAGS if isolation.get(name) is not True]
    enabled_false = [name for name in REQUIRED_FALSE_FLAGS if isolation.get(name) is not False]
    if missing_true or enabled_false:
        raise PinnedBuildError(f"Isolation flags invalid; missing_true={missing_true}, enabled_false={enabled_false}")
    if int(isolation.get("people_loaded", -1)) != 0 or int(isolation.get("minds_loaded", -1)) != 0:
        raise PinnedBuildError("A person or mind is bound to R5")

    bookmark_ids = [str(item.get("id") or "") for item in manifest.get("review_bookmarks") or []]
    if not bookmark_ids or any(not value for value in bookmark_ids) or len(bookmark_ids) != len(set(bookmark_ids)):
        raise PinnedBuildError("Review bookmark IDs are missing or duplicated")

    for item in manifest.get("source_inputs") or []:
        verify_item(item)

    served: dict[str, tuple[Path, dict[str, Any]]] = {}
    pinned_paths: set[Path] = set()
    for item in manifest.get("served_files") or []:
        url = str(item.get("url") or "")
        if not url.startswith("/") or "?" in url or "#" in url or url in served:
            raise PinnedBuildError(f"Invalid or duplicate served URL: {url!r}")
        path = verify_item(item, expected_root=DIST)
        served[url] = (path, item)
        pinned_paths.add(path.resolve())
    if "/index.html" not in served:
        raise PinnedBuildError("Pinned R5 build has no entrypoint")
    actual_paths = {path.resolve() for path in DIST.rglob("*") if path.is_file()}
    if actual_paths != pinned_paths:
        unexpected = sorted(str(path.relative_to(DIST)) for path in actual_paths - pinned_paths)
        missing = sorted(str(path.relative_to(DIST)) for path in pinned_paths - actual_paths)
        raise PinnedBuildError(f"Dist differs from manifest; unexpected={unexpected}, missing={missing}")
    served["/"] = served["/index.html"]
    return manifest, served


class Handler(BaseHTTPRequestHandler):
    server_version = "LouvreRealismR5/1.0"

    def send_pinned_headers(self, status: int, content_type: str, length: int = 0) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), usb=(), payment=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
            "connect-src 'self' blob:; media-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'",
        )
        self.end_headers()

    def serve_request(self, *, include_body: bool) -> None:
        split = urlsplit(self.path)
        requested = unquote(split.path or "/")
        if requested == "/favicon.ico":
            self.send_pinned_headers(204, "image/x-icon", 0)
            return
        try:
            manifest, served = validate_pinned_build()
        except (OSError, ValueError, json.JSONDecodeError, PinnedBuildError) as exc:
            payload = f"Pinned Louvre R5 build refused: {exc}\n".encode()
            self.send_pinned_headers(503, "text/plain; charset=utf-8", len(payload))
            if include_body:
                self.wfile.write(payload)
            return

        if requested == "/healthz":
            isolation = manifest["runtime_isolation"]
            payload = json.dumps(
                {
                    "service": "louvre_realism_solo_owner_review",
                    "protocol": HEALTH_PROTOCOL,
                    "ready": True,
                    "build_id": manifest["build_id"],
                    "status": manifest["status"],
                    "launch_url": f"http://{LOOPBACK_HOST}:{self.server.server_port}/?solo=1&bookmark=arrival",
                    "isolation": isolation,
                },
                sort_keys=True,
            ).encode()
            self.send_pinned_headers(200, "application/json; charset=utf-8", len(payload))
            if include_body:
                self.wfile.write(payload)
            return

        if requested in {"/", "/index.html"}:
            query = parse_qs(split.query, keep_blank_values=True)
            allowed = {str(item["id"]) for item in manifest["review_bookmarks"]}
            values = query.get("bookmark", [])
            valid = query.get("solo") == ["1"] and set(query).issubset({"solo", "bookmark"}) and (
                not values or (len(values) == 1 and values[0] in allowed)
            )
            if not valid:
                self.send_response(302)
                self.send_header("Location", "/?solo=1&bookmark=arrival")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return

        record = served.get(requested)
        if record is None:
            payload = b"Not found in pinned Louvre R5 build.\n"
            self.send_pinned_headers(404, "text/plain; charset=utf-8", len(payload))
            if include_body:
                self.wfile.write(payload)
            return
        path, _ = record
        payload = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix.lower() == ".glb":
            content_type = "model/gltf-binary"
        elif content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        self.send_pinned_headers(200, content_type, len(payload))
        if include_body:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self.serve_request(include_body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self.serve_request(include_body=False)

    def do_POST(self) -> None:  # noqa: N802
        payload = b"This owner-review server is read-only.\n"
        self.send_pinned_headers(405, "text/plain; charset=utf-8", len(payload))
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write(f"[Louvre R5] {self.address_string()} - {format % args}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest, served = validate_pinned_build()
    except (OSError, ValueError, json.JSONDecodeError, PinnedBuildError) as exc:
        print(f"Louvre R5 verification FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"Verified {manifest['build_id']} ({len(served) - 1} pinned files; solo, zero people, no interior).")
    if args.verify_only:
        return 0
    if not 1 <= args.port <= 65535:
        print(f"Invalid port: {args.port}", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((LOOPBACK_HOST, args.port), Handler)
    server.daemon_threads = True
    url = f"http://{LOOPBACK_HOST}:{args.port}/?solo=1&bookmark=arrival"
    print(f"Serving read-only Louvre R5 owner review at {url}")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        print("\nStopping Louvre R5 owner review.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
