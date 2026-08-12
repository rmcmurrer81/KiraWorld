"""Serve the pinned legal-spa notebook preview without exposing the workspace."""

from __future__ import annotations

import argparse
import functools
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from notebook_world_integrity import VerifiedNotebookBuild, read_json_object, sha256_file, verify_code_pinned_build
except ModuleNotFoundError:  # Imported as tools.serve_legal_day_spa_notebook_world.
    from tools.notebook_world_integrity import VerifiedNotebookBuild, read_json_object, sha256_file, verify_code_pinned_build


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "legal_day_spa_notebook_world"
    / "builds"
    / "notebook_world_legal_day_spa_staged_20260715"
    / "preview_registration.json"
)
BUILD_MANIFEST = REGISTRATION.parent / "pinned_build_manifest.json"
BUILD_MANIFEST_SHA256 = "4b5d17bb842bdb66c3d3682dff321fa08d24cc2ff645d1b5d471d13e59d7c9f0"
WORLD_ID = "legal_day_spa_notebook_world"
REQUEST_ID = "notebook_world_legal_day_spa_staged_20260715"
REGISTRATION_RELATIVE_PATH = REGISTRATION.relative_to(ROOT).as_posix()
def verify_pinned_build() -> VerifiedNotebookBuild:
    """Verify the code-pinned manifest and all bytes before any socket bind."""
    verified = verify_code_pinned_build(
        root=ROOT,
        manifest_path=BUILD_MANIFEST,
        expected_manifest_sha256=BUILD_MANIFEST_SHA256,
        expected_world_id=WORLD_ID,
        expected_request_id=REQUEST_ID,
        expected_registration_relative_path=REGISTRATION_RELATIVE_PATH,
        required_roles={
            "registration",
            "entry_html",
            "scene_metadata",
            "notebook_request",
            "placement_metadata",
            "scene_plan_metadata",
            "tardis_review_metadata",
            "notebook_approval_gate",
            "preview_approval_gate",
            "model_asset",
            "three_runtime",
        },
    )
    registration = verified.registration
    if str(registration.get("build_id") or "") != verified.build_id:
        raise ValueError("Spa registration build_id diverges from the pinned manifest")
    if str(registration.get("pinned_build_manifest") or "") != BUILD_MANIFEST.relative_to(ROOT).as_posix():
        raise ValueError("Spa registration manifest path diverges from launcher code")
    if registration.get("launcher_requires_code_pinned_manifest") is not True or registration.get("launcher_verifies_all_manifest_bytes_before_bind") is not True:
        raise ValueError("Spa registration does not require fail-closed manifest verification")
    if str(registration.get("preview") or "") != verified.entrypoint_relative_path:
        raise ValueError("Spa registration preview path diverges from the pinned entrypoint")
    preview_gate = verified.role_paths["preview_approval_gate"]
    if len(preview_gate) != 1 or str(registration.get("source_approval_gate") or "") != preview_gate[0].relative_to(ROOT).as_posix():
        raise ValueError("Spa registration approval gate diverges from the pinned build")

    scene_paths = verified.role_paths["scene_metadata"]
    if len(scene_paths) != 1:
        raise ValueError("Spa manifest must bind exactly one scene metadata file")
    scene = read_json_object(scene_paths[0])
    asset_paths = set(verified.role_paths["model_asset"])
    manifest_assets = {
        url: path
        for url, path in verified.served_urls.items()
        if path in asset_paths and url != "/"
    }
    scene_assets: dict[str, tuple[Path, str]] = {}
    for item in scene.get("asset_instances", []):
        if not isinstance(item, dict):
            raise ValueError("Spa scene contains an invalid asset instance")
        source_url = str(item.get("source_url") or "")
        source = str(item.get("source") or "")
        expected_sha = str(item.get("source_sha256") or "").lower()
        target = (ROOT / source).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"Spa scene asset escapes the project: {source}") from exc
        prior = scene_assets.get(source_url)
        if prior is not None and prior != (target, expected_sha):
            raise ValueError(f"Spa scene has conflicting asset bindings: {source_url}")
        scene_assets[source_url] = (target, expected_sha)
    if set(scene_assets) != set(manifest_assets) or len(manifest_assets) != 5:
        raise ValueError("Spa scene and pinned manifest must bind the same five unique assets")
    for source_url, (target, expected_sha) in scene_assets.items():
        if manifest_assets[source_url] != target or sha256_file(target) != expected_sha:
            raise ValueError(f"Spa scene asset binding changed: {source_url}")
    return verified


def pinned_preview_relative_path() -> str:
    """Resolve the immutable notebook registration, never the mutable latest pointer."""
    return verify_pinned_build().entrypoint_relative_path


def allowed_asset_urls(preview_root: Path | None = None) -> dict[str, Path]:
    """Return only the exact SHA-pinned GLBs referenced by this preview."""
    del preview_root  # Retained for compatibility; the manifest chooses the build.
    verified = verify_pinned_build()
    asset_paths = set(verified.role_paths["model_asset"])
    return {
        url: path
        for url, path in verified.served_urls.items()
        if url != "/" and path in asset_paths
    }


class ScopedSpaHandler(SimpleHTTPRequestHandler):
    """Serve preview files, exact model assets, and the Three.js package only."""

    def __init__(
        self,
        *args,
        served_urls: dict[str, Path],
        served_sha256: dict[str, str],
        served_bytes: dict[str, int],
        **kwargs,
    ) -> None:
        self.served_urls = {unquote(key): value.resolve() for key, value in served_urls.items()}
        self.served_sha256 = {unquote(key): value for key, value in served_sha256.items()}
        self.served_bytes = {unquote(key): value for key, value in served_bytes.items()}
        self.forbidden = BUILD_MANIFEST.parent / ".forbidden"
        super().__init__(*args, directory=str(BUILD_MANIFEST.parent), **kwargs)

    def translate_path(self, path: str) -> str:
        request_path = unquote(urlsplit(path).path)
        target = self.served_urls.get(request_path)
        if target is None:
            return str(self.forbidden)
        try:
            if (
                target.stat().st_size != self.served_bytes[request_path]
                or sha256_file(target) != self.served_sha256[request_path]
            ):
                return str(self.forbidden)
        except (KeyError, OSError):
            return str(self.forbidden)
        return str(target)

    def list_directory(self, path: str):
        self.send_error(403, "Directory listing disabled")
        return None

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' blob:; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' blob:",
        )
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def bind_server(preferred_port: int) -> tuple[ThreadingHTTPServer, int]:
    verified = verify_pinned_build()
    handler = functools.partial(
        ScopedSpaHandler,
        served_urls=verified.served_urls,
        served_sha256=verified.served_sha256,
        served_bytes=verified.served_bytes,
    )
    ports = [0] if preferred_port == 0 else list(range(preferred_port, preferred_port + 10))
    last_error: OSError | None = None
    for port in ports:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            return server, int(server.server_address[1])
        except OSError as exc:
            last_error = exc
    raise OSError(f"Could not bind requested spa preview ports: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8890)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    verified = verify_pinned_build()
    server, port = bind_server(args.port)
    url = f"http://127.0.0.1:{port}/index.html"
    print("Legal Day Spa separate notebook world")
    print(f"Pinned build: {verified.build_id} (staged, not Home World approved).")
    print(f"Manifest SHA-256: {verified.manifest_sha256}")
    print(f"Registration SHA-256: {verified.registration_sha256}")
    print("Only manifest-bound preview bytes, five exact model assets, and required Three.js modules are served.")
    print("Kira, Ollama, voice, Home World, and the strip mall are not loaded or modified.")
    print(f"Open: {url}")
    print("Close this window or press Ctrl+C to stop the preview server.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
