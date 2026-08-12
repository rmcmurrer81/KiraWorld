"""Serve a code-pinned procedural notebook preview from an exact URL allowlist."""

from __future__ import annotations

import argparse
import functools
import threading
import webbrowser
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from notebook_world_integrity import VerifiedNotebookBuild, read_json_object, sha256_file, verify_code_pinned_build
    from notebook_world_preview_backend import BUILD_STATUS, REQUIRED_BUILD_ROLES
    from validate_notebook_world_request import validate_notebook_world_request
except ModuleNotFoundError:  # Imported as tools.serve_pinned_notebook_world_preview.
    from tools.notebook_world_integrity import VerifiedNotebookBuild, read_json_object, sha256_file, verify_code_pinned_build
    from tools.notebook_world_preview_backend import BUILD_STATUS, REQUIRED_BUILD_ROLES
    from tools.validate_notebook_world_request import validate_notebook_world_request


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PreviewLaunchConfig:
    root: Path
    manifest_path: Path
    manifest_sha256: str
    world_id: str
    request_id: str
    registration_relative_path: str
    display_name: str
    default_port: int


def _one_role(verified: VerifiedNotebookBuild, role: str) -> Path:
    paths = verified.role_paths.get(role, ())
    if len(paths) != 1:
        raise ValueError(f"Pinned preview must bind exactly one {role} file")
    return paths[0]


def verify_generated_preview(config: PreviewLaunchConfig) -> VerifiedNotebookBuild:
    """Verify the manifest, draft request, authorization, metadata, and isolation."""

    root = config.root.resolve()
    verified = verify_code_pinned_build(
        root=root,
        manifest_path=config.manifest_path,
        expected_manifest_sha256=config.manifest_sha256,
        expected_world_id=config.world_id,
        expected_request_id=config.request_id,
        expected_registration_relative_path=config.registration_relative_path,
        required_roles=REQUIRED_BUILD_ROLES,
    )
    registration = verified.registration
    expected_registration = {
        "registration_kind": "generated_procedural_notebook_world_preview_registration",
        "world_id": config.world_id,
        "request_id": config.request_id,
        "build_id": verified.build_id,
        "status": BUILD_STATUS,
        "prototype": True,
        "draft": True,
        "final": False,
        "approved": False,
        "runtime_registered": False,
        "home_world_mutation_allowed": False,
        "strip_mall_mutation_allowed": False,
        "loads_people": False,
        "loads_minds": False,
        "loads_voice": False,
        "loads_ollama": False,
        "launcher_requires_code_pinned_manifest": True,
        "launcher_verifies_all_manifest_bytes_before_bind": True,
    }
    for key, expected in expected_registration.items():
        if registration.get(key) != expected:
            raise ValueError(f"Pinned preview registration diverges at {key}")
    manifest_relative = config.manifest_path.resolve().relative_to(root).as_posix()
    if registration.get("pinned_build_manifest") != manifest_relative:
        raise ValueError("Registration manifest path diverges from launcher code")
    if registration.get("preview") != verified.entrypoint_relative_path:
        raise ValueError("Registration preview path diverges from the pinned entrypoint")
    server_scope = registration.get("server_scope")
    if server_scope != {
        "entire_workspace_served": False,
        "directory_listing": False,
        "exact_manifest_bound_files_only": True,
        "hash_rechecked_on_every_request": True,
    }:
        raise ValueError("Registration server scope is not exact-file fail-closed")

    request_path = _one_role(verified, "notebook_request")
    program_path = _one_role(verified, "procedural_scene_program")
    authorization_path = _one_role(verified, "preview_scope_authorization")
    if (
        registration.get("request") != request_path.relative_to(root).as_posix()
        or registration.get("program") != program_path.relative_to(root).as_posix()
        or registration.get("authorization") != authorization_path.relative_to(root).as_posix()
        or registration.get("request_sha256") != sha256_file(request_path)
        or registration.get("program_sha256") != sha256_file(program_path)
        or registration.get("authorization_sha256") != sha256_file(authorization_path)
    ):
        raise ValueError("Registration input bindings changed")
    request = read_json_object(request_path)
    errors = validate_notebook_world_request(request)
    if errors or request.get("schema_version") != 2 or request.get("status") != "draft":
        raise ValueError(f"Pinned request is no longer a valid strict-v2 draft: {errors}")
    isolation = request.get("isolation_policy", {})
    resource = request.get("resource_policy", {})
    if any(
        isolation.get(key) is not False
        for key in (
            "home_world_import_requested",
            "home_world_mutation_allowed",
            "strip_mall_mutation_allowed",
            "co_load_with_home_world",
            "co_load_with_other_notebook_worlds",
        )
    ) or any(
        resource.get(key) is not False
        for key in ("loads_kira_mind", "loads_kira_body", "loads_voice", "loads_ollama", "loads_second_person")
    ):
        raise ValueError("Pinned request no longer preserves preview isolation")

    scene = read_json_object(_one_role(verified, "scene_metadata"))
    collision = read_json_object(_one_role(verified, "collision_nav_metadata"))
    source_truth = read_json_object(_one_role(verified, "source_truth_metadata"))
    resource_budget = read_json_object(_one_role(verified, "resource_budget_metadata"))
    status = read_json_object(_one_role(verified, "build_status_metadata"))
    for metadata in (scene, collision, source_truth, resource_budget, status):
        if metadata.get("world_id") != config.world_id or metadata.get("request_id") != config.request_id or metadata.get("build_id") != verified.build_id:
            raise ValueError("Pinned preview metadata identity diverges")
    expected_scene_isolation = {
        "world_class": "separate_notebook_world",
        "home_world_mutation_allowed": False,
        "strip_mall_mutation_allowed": False,
        "runtime_registered": False,
        "person_assets_loaded": False,
        "resident_minds_loaded": False,
        "voice_loaded": False,
        "ollama_loaded": False,
    }
    if scene.get("status") != BUILD_STATUS or scene.get("isolation") != expected_scene_isolation:
        raise ValueError("Pinned scene isolation/status changed")
    if collision.get("runtime_route_claim_allowed") is not False:
        raise ValueError("Collision metadata improperly claims a runtime route")
    if source_truth.get("status") != "truth_labels_present_prototype_not_source_reconstruction":
        raise ValueError("Source-truth metadata status changed")
    if resource_budget.get("status") != "within_declared_and_backend_caps" or resource_budget.get("loads_home_world") is not False:
        raise ValueError("Resource budget no longer preserves isolated lightweight status")
    if any(status.get(key) is not False for key in ("final", "approved", "runtime_registered", "home_world_mutation", "strip_mall_mutation", "people_loaded", "minds_loaded", "voice_loaded", "ollama_loaded")):
        raise ValueError("Build status improperly broadens preview authority")
    if status.get("prototype") is not True or status.get("draft") is not True or status.get("status") != BUILD_STATUS:
        raise ValueError("Build status is not a draft prototype")

    three_paths = verified.role_paths.get("three_runtime", ())
    if len(three_paths) != 1 or verified.served_urls.get("/vendor/three/three.module.js") != three_paths[0]:
        raise ValueError("Pinned preview must serve exactly one Three.js runtime module")
    three_core_paths = verified.role_paths.get("three_core_runtime", ())
    if len(three_core_paths) != 1 or verified.served_urls.get("/vendor/three/three.core.js") != three_core_paths[0]:
        raise ValueError("Pinned preview must serve the exact Three.js core dependency")
    expected_urls = {
        "/",
        "/index.html",
        "/main.js",
        "/styles.css",
        "/data/scene_manifest.json",
        "/data/collision_nav.json",
        "/data/source_truth.json",
        "/data/resource_budget.json",
        "/data/build_status.json",
        "/vendor/three/three.module.js",
        "/vendor/three/three.core.js",
    }
    if set(verified.served_urls) != expected_urls:
        raise ValueError("Pinned preview served URL allowlist diverges")
    return verified


class ScopedPinnedPreviewHandler(SimpleHTTPRequestHandler):
    """Serve only exact manifest-bound URLs and re-check bytes per request."""

    def __init__(
        self,
        *args,
        served_urls: dict[str, Path],
        served_sha256: dict[str, str],
        served_bytes: dict[str, int],
        forbidden_path: Path,
        **kwargs,
    ) -> None:
        self.served_urls = {unquote(key): value.resolve() for key, value in served_urls.items()}
        self.served_sha256 = {unquote(key): value for key, value in served_sha256.items()}
        self.served_bytes = {unquote(key): value for key, value in served_bytes.items()}
        self.forbidden_path = forbidden_path
        super().__init__(*args, directory=str(forbidden_path.parent), **kwargs)

    def translate_path(self, path: str) -> str:
        request_path = unquote(urlsplit(path).path)
        target = self.served_urls.get(request_path)
        if target is None:
            return str(self.forbidden_path)
        try:
            if (
                target.stat().st_size != self.served_bytes[request_path]
                or sha256_file(target) != self.served_sha256[request_path]
            ):
                return str(self.forbidden_path)
        except (KeyError, OSError):
            return str(self.forbidden_path)
        return str(target)

    def list_directory(self, path: str):
        self.send_error(403, "Directory listing disabled")
        return None

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler convention.
        self.send_error(405, "Read-only preview")

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def bind_server(config: PreviewLaunchConfig, preferred_port: int | None = None) -> tuple[ThreadingHTTPServer, int, VerifiedNotebookBuild]:
    verified = verify_generated_preview(config)
    handler = functools.partial(
        ScopedPinnedPreviewHandler,
        served_urls=verified.served_urls,
        served_sha256=verified.served_sha256,
        served_bytes=verified.served_bytes,
        forbidden_path=verified.manifest_path.parent / ".forbidden_notebook_preview_path",
    )
    requested = config.default_port if preferred_port is None else preferred_port
    ports = [0] if requested == 0 else list(range(requested, requested + 10))
    last_error: OSError | None = None
    for port in ports:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            return server, int(server.server_address[1]), verified
        except OSError as exc:
            last_error = exc
    raise OSError(f"Could not bind requested notebook preview ports: {last_error}")


def serve(config: PreviewLaunchConfig, *, preferred_port: int | None = None, open_browser: bool = True) -> int:
    server, port, verified = bind_server(config, preferred_port)
    url = f"http://127.0.0.1:{port}/index.html"
    print(config.display_name)
    print(f"Pinned build: {verified.build_id}")
    print(f"Status: {BUILD_STATUS}")
    print(f"Manifest SHA-256: {verified.manifest_sha256}")
    print("Exact manifest-bound files only; directory listing and workspace access are disabled.")
    print("No people, minds, voice, Ollama, Home World, or strip-mall mutation is loaded or allowed.")
    print(f"Open: {url}")
    print("Close this window or press Ctrl+C to stop the isolated preview server.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--registration", required=True, help="Project-relative registration path")
    parser.add_argument("--display-name", default="Procedural notebook world preview")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    config = PreviewLaunchConfig(
        root=ROOT,
        manifest_path=args.manifest,
        manifest_sha256=args.manifest_sha256,
        world_id=args.world_id,
        request_id=args.request_id,
        registration_relative_path=args.registration,
        display_name=args.display_name,
        default_port=args.port,
    )
    return serve(config, preferred_port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
