"""Serve the pinned Kira wardrobe lab without exposing the workspace."""

from __future__ import annotations

import argparse
import functools
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from notebook_world_integrity import VerifiedNotebookBuild, sha256_file, verify_code_pinned_build
except ModuleNotFoundError:  # Imported as tools.serve_kira_wardrobe_lab_notebook_world.
    from tools.notebook_world_integrity import VerifiedNotebookBuild, sha256_file, verify_code_pinned_build


ROOT = Path(__file__).resolve().parents[1]
BUILD = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "kira_wardrobe_lab_notebook_world"
    / "builds"
    / "notebook_world_kira_wardrobe_lab_staged_20260715"
)
REGISTRATION = BUILD / "registration.json"
BUILD_MANIFEST = BUILD / "pinned_build_manifest.json"
BUILD_MANIFEST_SHA256 = "392c28f874efff4e68f7f4770f152d8fadac525e960969162466103fac575135"
WORLD_ID = "kira_wardrobe_lab_notebook_world"
REQUEST_ID = "notebook_world_kira_wardrobe_lab_staged_20260715"
REGISTRATION_RELATIVE_PATH = REGISTRATION.relative_to(ROOT).as_posix()
METADATA_BINDINGS = {
    "state_machine_metadata": ("state_machine", "/data/wardrobe_state_machine.json"),
    "builder_contract_metadata": ("builder_contract", "/data/builder_contract.json"),
    "core_garment_bridge_metadata": ("core_garment_bridge", "/data/core_garment_bridge.json"),
    "approval_gate_metadata": ("approval_gate", "/data/approval_gate.json"),
}


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
            "entry_javascript",
            "entry_stylesheet",
            "notebook_request",
            "placement_metadata",
            "state_machine_metadata",
            "builder_contract_metadata",
            "core_garment_bridge_metadata",
            "approval_gate_metadata",
            "model_asset",
            "three_runtime",
        },
    )
    registration = verified.registration
    if str(registration.get("build_id") or "") != verified.build_id:
        raise ValueError("Wardrobe registration build_id diverges from the pinned manifest")
    if str(registration.get("pinned_build_manifest") or "") != BUILD_MANIFEST.relative_to(ROOT).as_posix():
        raise ValueError("Wardrobe registration manifest path diverges from launcher code")
    if registration.get("launcher_requires_code_pinned_manifest") is not True or registration.get("launcher_verifies_all_manifest_bytes_before_bind") is not True:
        raise ValueError("Wardrobe registration does not require fail-closed manifest verification")
    if str(registration.get("preview") or "") != verified.entrypoint_relative_path:
        raise ValueError("Wardrobe registration preview path diverges from the pinned entrypoint")
    for role, (registration_key, expected_url) in METADATA_BINDINGS.items():
        paths = verified.role_paths[role]
        if len(paths) != 1:
            raise ValueError(f"Wardrobe manifest must bind exactly one {role}")
        relative = paths[0].relative_to(ROOT).as_posix()
        if str(registration.get(registration_key) or "") != relative:
            raise ValueError(f"Wardrobe registration {registration_key} path diverges")
        if verified.served_urls.get(expected_url) != paths[0]:
            raise ValueError(f"Wardrobe metadata URL diverges: {expected_url}")
    asset_paths = set(verified.role_paths["model_asset"])
    registered_assets = registration.get("assets")
    if not isinstance(registered_assets, list) or len(registered_assets) != 2:
        raise ValueError("Wardrobe registration must bind exactly two model assets")
    manifest_assets = {
        url: path
        for url, path in verified.served_urls.items()
        if url != "/" and path in asset_paths
    }
    registration_urls: set[str] = set()
    for item in registered_assets:
        if not isinstance(item, dict):
            raise ValueError("Wardrobe registration contains an invalid asset entry")
        url = str(item.get("url") or "")
        source = str(item.get("source") or "")
        target = (ROOT / source).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"Wardrobe asset escapes the project root: {source}") from exc
        if (
            manifest_assets.get(url) != target
            or target.stat().st_size != item.get("bytes")
            or sha256_file(target) != str(item.get("sha256") or "").lower()
            or verified.served_urls.get(url) != target
        ):
            raise ValueError(f"Wardrobe registration asset diverges: {url}")
        registration_urls.add(url)
    if registration_urls != set(manifest_assets):
        raise ValueError("Wardrobe registration and manifest asset sets diverge")
    return verified


def pinned_preview_relative_path() -> str:
    return verify_pinned_build().entrypoint_relative_path


def allowed_asset_urls() -> dict[str, Path]:
    verified = verify_pinned_build()
    asset_paths = set(verified.role_paths["model_asset"])
    return {
        url: path
        for url, path in verified.served_urls.items()
        if url != "/" and path in asset_paths
    }


class ScopedWardrobeLabHandler(SimpleHTTPRequestHandler):
    """Serve preview files, two exact model assets, and Three.js only."""

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
        self.forbidden = BUILD / ".forbidden"
        super().__init__(*args, directory=str(BUILD), **kwargs)

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
        self.send_header("Cache-Control", "no-store")
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
        ScopedWardrobeLabHandler,
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
    raise OSError(f"Could not bind requested wardrobe preview ports: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8894)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    verified = verify_pinned_build()
    server, port = bind_server(args.port)
    url = f"http://127.0.0.1:{port}/index.html"
    print("Kira-only wardrobe notebook lab")
    print(f"Manifest SHA-256: {verified.manifest_sha256}")
    print(f"Registration SHA-256: {verified.registration_sha256}")
    print("Pinned body: current Kira GLB, read-only. Pinned robe: static draft proof.")
    print("No mind, voice, Ollama, second person, or Home World is loaded or modified.")
    print("All dressing stages are blocked until real runtime evidence exists.")
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
