"""Serve the exact pinned filming-backlot draft without exposing the workspace."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from serve_pinned_notebook_world_preview import PreviewLaunchConfig, serve, verify_generated_preview
except ModuleNotFoundError:  # Imported as tools.serve_synthetic_people_filming_backlot_notebook_world.
    from tools.serve_pinned_notebook_world_preview import PreviewLaunchConfig, serve, verify_generated_preview


ROOT = Path(__file__).resolve().parents[1]
WORLD_ID = "synthetic_people_filming_backlot_notebook_world"
REQUEST_ID = "notebook_world_synthetic_people_filming_backlot_20260716_144216"
BUILD_ID = "filming_preview_20260716_r3"
BUILD_ROOT = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / WORLD_ID
    / "builds"
    / REQUEST_ID
    / "preview_builds"
    / BUILD_ID
)
MANIFEST = BUILD_ROOT / "pinned_build_manifest.json"
MANIFEST_SHA256 = "68605a2447359a2eedae1871ffbcb3c43b1b3943fb37e56be1755d52812b45d9"
REGISTRATION_RELATIVE_PATH = (BUILD_ROOT / "registration.json").relative_to(ROOT).as_posix()


def launch_config(port: int = 8898) -> PreviewLaunchConfig:
    """Return the immutable code-pinned configuration for this one draft build."""

    return PreviewLaunchConfig(
        root=ROOT,
        manifest_path=MANIFEST,
        manifest_sha256=MANIFEST_SHA256,
        world_id=WORLD_ID,
        request_id=REQUEST_ID,
        registration_relative_path=REGISTRATION_RELATIVE_PATH,
        display_name="Synthetic People Filming Backlot - isolated two-room prototype draft",
        default_port=port,
    )


def verify_pinned_build():
    """Verify all manifest bytes and fail-closed isolation before socket bind."""

    verified = verify_generated_preview(launch_config())
    if verified.build_id != BUILD_ID:
        raise ValueError("Filming-backlot build id diverges from launcher code")
    return verified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8898)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    verify_pinned_build()
    return serve(launch_config(args.port), preferred_port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
