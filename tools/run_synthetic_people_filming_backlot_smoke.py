"""Run the pinned filming-backlot launcher and its headless Three.js smoke."""

from __future__ import annotations

import argparse
import subprocess
import threading
from pathlib import Path

try:
    from serve_pinned_notebook_world_preview import bind_server
    from serve_synthetic_people_filming_backlot_notebook_world import BUILD_ID, ROOT, WORLD_ID, launch_config
except ModuleNotFoundError:  # Imported as tools.run_synthetic_people_filming_backlot_smoke.
    from tools.serve_pinned_notebook_world_preview import bind_server
    from tools.serve_synthetic_people_filming_backlot_notebook_world import BUILD_ID, ROOT, WORLD_ID, launch_config


HELPER = ROOT / "tools" / "notebook_world_preview_browser_smoke.mjs"
DEFAULT_REPORT = ROOT / "Data" / "codex_reports" / "evidence" / "20260716_filming_backlot_browser_smoke.json"
DEFAULT_SCREENSHOT = ROOT / "Data" / "codex_reports" / "evidence" / "20260716_filming_backlot_browser_smoke.png"
DEFAULT_CAMERA_DIR = ROOT / "Data" / "codex_reports" / "evidence" / "20260716_filming_backlot_cameras"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--screenshot", type=Path, default=DEFAULT_SCREENSHOT)
    parser.add_argument("--camera-dir", type=Path, default=DEFAULT_CAMERA_DIR)
    args = parser.parse_args()
    server, port, verified = bind_server(launch_config(0), 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        command = [
            "node",
            str(HELPER),
            "--url",
            f"http://127.0.0.1:{port}/index.html",
            "--report",
            str(args.report.resolve()),
            "--screenshot",
            str(args.screenshot.resolve()),
            "--camera-dir",
            str(args.camera_dir.resolve()),
            "--expected-world",
            WORLD_ID,
            "--expected-build",
            BUILD_ID,
            "--expected-rooms",
            "2",
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False, timeout=150)
        print(f"Pinned manifest: {verified.manifest_sha256}")
        print(f"Report: {args.report.resolve()}")
        print(f"Screenshot: {args.screenshot.resolve()}")
        print(f"Camera screenshots: {args.camera_dir.resolve()}")
        return completed.returncode
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
