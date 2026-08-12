#!/usr/bin/env python3
"""Serve only the hash-pinned Louvre corrected R7 zero-person owner review."""

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

from package_louvre_corrected_r7_owner_review import (
    BUILD_ID,
    CONTRACT_PATH,
    DIST,
    EVIDENCE_PATH,
    MANIFEST_PATH,
    PREVIEW,
    ROOT,
    R7PackageError,
    require_contract,
)


DEFAULT_PORT = 5197
HOST = "127.0.0.1"
PROTOCOL = "louvre_corrected_zero_person_owner_review_r7"


class PinnedBuildError(RuntimeError):
    """Raised when the R7 source or output differs from its manifest."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def root_path(raw: str) -> Path:
    result = (ROOT / raw).resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PinnedBuildError(f"Manifest path escapes the project root: {raw}") from exc
    return result


def verify_record(item: dict[str, Any], *, inside: Path | None = None) -> Path:
    path = root_path(str(item.get("path") or ""))
    if inside is not None:
        try:
            path.relative_to(inside.resolve())
        except ValueError as exc:
            raise PinnedBuildError(f"Served path escapes dist: {path}") from exc
    if not path.is_file():
        raise PinnedBuildError(f"Pinned file missing: {path}")
    if path.stat().st_size != int(item.get("bytes", -1)):
        raise PinnedBuildError(f"Pinned byte count changed: {path}")
    if sha256(path) != str(item.get("sha256") or "").lower():
        raise PinnedBuildError(f"Pinned SHA-256 changed: {path}")
    return path


def validate_pinned_build() -> tuple[dict[str, Any], dict[str, tuple[Path, dict[str, Any]]]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    require_contract(contract, evidence)
    if manifest.get("manifest_kind") != "louvre_corrected_r7_pinned_owner_review":
        raise PinnedBuildError("Unexpected R7 manifest kind")
    if manifest.get("build_id") != BUILD_ID or manifest.get("status") != contract["status"]:
        raise PinnedBuildError("Unexpected R7 build identity or status")
    if manifest.get("owner_rejection") != contract["owner_rejection"]:
        raise PinnedBuildError("Owner-rejection routing differs from the truth contract")
    if manifest.get("runtime_isolation") != contract["runtime_isolation"]:
        raise PinnedBuildError("Runtime isolation differs from the truth contract")
    if manifest.get("spatial_anchors") != contract["spatial_anchors"]:
        raise PinnedBuildError("Spatial anchors differ from the truth contract")
    if manifest.get("object_invariants") != contract["object_invariants"]:
        raise PinnedBuildError("Object invariants differ from the truth contract")
    route = manifest.get("owner_review_routing") or {}
    if route.get("registered_in_world_shell_or_tardis") is not True:
        raise PinnedBuildError("The explicit R7 owner-review launch route is missing")
    if route.get("production_destination_replaced") is not False:
        raise PinnedBuildError("The unapproved R7 cannot replace the production/audit destination")
    for flag in ("transports_person", "activates_person", "mutates_shell_location"):
        if route.get(flag) is not False:
            raise PinnedBuildError(f"R7 owner-review route violates zero-person safety: {flag}")
    source_records = manifest.get("source_inputs") or []
    if not source_records:
        raise PinnedBuildError("No R7 source inputs are pinned")
    for item in source_records:
        verify_record(item)
    served: dict[str, tuple[Path, dict[str, Any]]] = {}
    pinned_paths: set[Path] = set()
    for item in manifest.get("served_files") or []:
        url = str(item.get("url") or "")
        if not url.startswith("/") or "?" in url or "#" in url or url in served:
            raise PinnedBuildError(f"Invalid or duplicate served URL: {url!r}")
        path = verify_record(item, inside=DIST)
        served[url] = (path, item)
        pinned_paths.add(path.resolve())
    if "/index.html" not in served:
        raise PinnedBuildError("Pinned R7 has no entrypoint")
    actual_paths = {path.resolve() for path in DIST.rglob("*") if path.is_file()}
    if actual_paths != pinned_paths:
        raise PinnedBuildError("R7 dist contains an unpinned addition or is missing a pinned file")
    if any(path.suffix.lower() in {".glb", ".gltf", ".fbx"} for path in actual_paths):
        raise PinnedBuildError("R7 cannot serve a scan/model asset")
    served["/"] = served["/index.html"]
    return manifest, served


class Handler(BaseHTTPRequestHandler):
    server_version = "LouvreCorrectedR7/1.0"

    def send_pinned_headers(self, status: int, content_type: str, length: int) -> None:
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

    def serve(self, body: bool) -> None:
        split = urlsplit(self.path)
        requested = unquote(split.path or "/")
        if requested == "/favicon.ico":
            self.send_pinned_headers(204, "image/x-icon", 0)
            return
        try:
            manifest, served = validate_pinned_build()
        except (OSError, ValueError, json.JSONDecodeError, R7PackageError, PinnedBuildError) as exc:
            payload = f"Pinned Louvre corrected R7 refused: {exc}\n".encode()
            self.send_pinned_headers(503, "text/plain; charset=utf-8", len(payload))
            if body:
                self.wfile.write(payload)
            return
        if requested == "/healthz":
            payload = json.dumps(
                {
                    "service": "louvre_corrected_r7_solo_owner_review",
                    "protocol": PROTOCOL,
                    "ready": True,
                    "build_id": BUILD_ID,
                    "status": manifest["status"],
                    "launch_url": f"http://{HOST}:{self.server.server_port}/?solo=1&bookmark=west_arrival",
                    "runtime_isolation": manifest["runtime_isolation"],
                    "owner_review_routing": manifest["owner_review_routing"],
                },
                sort_keys=True,
            ).encode()
            self.send_pinned_headers(200, "application/json; charset=utf-8", len(payload))
            if body:
                self.wfile.write(payload)
            return
        if requested in {"/", "/index.html"}:
            query = parse_qs(split.query, keep_blank_values=True)
            bookmarks = query.get("bookmark", [])
            allowed = {str(item["id"]) for item in manifest["review_bookmarks"]}
            valid = (
                query.get("solo") == ["1"]
                and set(query).issubset({"solo", "bookmark"})
                and (not bookmarks or (len(bookmarks) == 1 and bookmarks[0] in allowed))
            )
            if not valid:
                self.send_response(302)
                self.send_header("Location", "/?solo=1&bookmark=west_arrival")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
        record = served.get(requested)
        if record is None:
            payload = b"Not found in the pinned Louvre corrected R7 build.\n"
            self.send_pinned_headers(404, "text/plain; charset=utf-8", len(payload))
            if body:
                self.wfile.write(payload)
            return
        path, _ = record
        payload = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_pinned_headers(200, content_type, len(payload))
        if body:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self.serve(True)

    def do_HEAD(self) -> None:  # noqa: N802
        self.serve(False)

    def do_POST(self) -> None:  # noqa: N802
        payload = b"The private R7 owner-review server is read-only.\n"
        self.send_pinned_headers(405, "text/plain; charset=utf-8", len(payload))
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write(f"[Louvre R7] {self.address_string()} - {format % args}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        manifest, served = validate_pinned_build()
    except (OSError, ValueError, json.JSONDecodeError, R7PackageError, PinnedBuildError) as exc:
        print(f"Louvre corrected R7 verification FAILED: {exc}", file=sys.stderr)
        return 2
    print(
        f"Verified {BUILD_ID} ({len(served) - 1} pinned files; main + 3 smaller pyramids; "
        "Hall Napoleon visual study; 4 locked portals; zero people/minds)."
    )
    if args.verify_only:
        return 0
    if not 1 <= args.port <= 65535:
        print(f"Invalid port: {args.port}", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((HOST, args.port), Handler)
    server.daemon_threads = True
    url = f"http://{HOST}:{args.port}/?solo=1&bookmark=west_arrival"
    print(f"Serving read-only Louvre corrected R7 owner review at {url}")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping Louvre corrected R7 owner review.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
