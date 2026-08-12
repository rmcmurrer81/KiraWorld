"""Serve the pinned zero-person Daily Movement Exam notebook world."""

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
except ModuleNotFoundError:
    from tools.notebook_world_integrity import VerifiedNotebookBuild, sha256_file, verify_code_pinned_build


ROOT = Path(__file__).resolve().parents[1]
BUILD = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "daily_movement_exam_notebook_world"
    / "builds"
    / "notebook_world_daily_movement_exam_20260717_160706"
)
REGISTRATION = BUILD / "registration.json"
BUILD_MANIFEST = BUILD / "pinned_build_manifest.json"
BUILD_MANIFEST_SHA256 = "28a7913d9c8a7f2eca520532b665359097d6a7666c53f783331d8ff5315454cc"
WORLD_ID = "daily_movement_exam_notebook_world"
REQUEST_ID = "notebook_world_daily_movement_exam_20260717_160706"
REGISTRATION_RELATIVE_PATH = REGISTRATION.relative_to(ROOT).as_posix()
METADATA_BINDINGS = {
    "scene_program_metadata": ("scene_program", "/data/scene_program.json"),
    "approval_gate_metadata": ("approval_gate", "/data/approval_gate.json"),
    "resource_isolation_metadata": ("resource_isolation_gate", "/data/resource_isolation_gate.json"),
    "quality_gate_metadata": ("quality_gate", "/data/quality_gate.json"),
}


def verify_pinned_build() -> VerifiedNotebookBuild:
    """Fail closed unless every served byte matches the code-pinned manifest."""
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
            "scene_program_metadata",
            "approval_gate_metadata",
            "resource_isolation_metadata",
            "quality_gate_metadata",
            "three_runtime",
        },
    )
    registration = verified.registration
    if str(registration.get("build_id") or "") != verified.build_id:
        raise ValueError("Daily Movement Exam registration build_id diverges")
    if str(registration.get("pinned_build_manifest") or "") != BUILD_MANIFEST.relative_to(ROOT).as_posix():
        raise ValueError("Daily Movement Exam registration manifest path diverges")
    if registration.get("launcher_requires_code_pinned_manifest") is not True:
        raise ValueError("Daily Movement Exam launcher pin is not required")
    if registration.get("launcher_verifies_all_manifest_bytes_before_bind") is not True:
        raise ValueError("Daily Movement Exam does not verify all bytes")
    if str(registration.get("preview") or "") != verified.entrypoint_relative_path:
        raise ValueError("Daily Movement Exam entrypoint diverges")
    for key in (
        "loads_person_assets",
        "loads_kira_body",
        "loads_kira_mind",
        "loads_voice",
        "loads_ollama",
        "loads_second_person",
        "modifies_home_world",
        "runtime_registered",
        "body_skill_execution_allowed",
    ):
        if registration.get(key) is not False:
            raise ValueError(f"Daily Movement Exam isolation flag must remain false: {key}")
    for role, (registration_key, expected_url) in METADATA_BINDINGS.items():
        paths = verified.role_paths[role]
        if len(paths) != 1:
            raise ValueError(f"Daily Movement Exam must bind exactly one {role}")
        relative = paths[0].relative_to(ROOT).as_posix()
        if str(registration.get(registration_key) or "") != relative:
            raise ValueError(f"Daily Movement Exam registration {registration_key} diverges")
        if verified.served_urls.get(expected_url) != paths[0]:
            raise ValueError(f"Daily Movement Exam metadata URL diverges: {expected_url}")
    if "model_asset" in verified.role_paths:
        raise ValueError("Daily Movement Exam zero-person preview must not bind a model asset")
    return verified


class ScopedDailyMovementExamHandler(SimpleHTTPRequestHandler):
    """Serve only exact manifest-bound URLs; never expose the workspace."""

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
        ScopedDailyMovementExamHandler,
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
    raise OSError(f"Could not bind Daily Movement Exam preview ports: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8896)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    verified = verify_pinned_build()
    server, port = bind_server(args.port)
    url = f"http://127.0.0.1:{port}/index.html"
    print("Daily Movement Exam - zero-person isolated notebook world")
    print(f"Manifest SHA-256: {verified.manifest_sha256}")
    print("No body, mind, voice, Ollama, Home World, microphone, webcam, or second person is loaded.")
    print("The moving capsule is a route-clearance probe, not Kira.")
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
