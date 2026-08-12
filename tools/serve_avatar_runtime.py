"""Serve the local Three.js avatar room and open a selected candidate."""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_activity_state import STATE_ROOT, write_avatar_activity_state


RUNTIME_ROOT = PROJECT_ROOT / "Avatar" / "runtime3d"


class QuietStaticHandler(http.server.SimpleHTTPRequestHandler):
    """Serve runtime assets without depending on a parent console stream."""

    def log_message(self, format: str, *args: object) -> None:
        return


def available_port(start: int = 8765) -> int:
    for port in range(start, start + 40):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No local avatar port was available.")


def ensure_build() -> None:
    built = RUNTIME_ROOT / "dist" / "index.html"
    source_files = [RUNTIME_ROOT / "index.html", *list((RUNTIME_ROOT / "src").glob("*"))]
    if built.exists() and all(not path.is_file() or path.stat().st_mtime <= built.stat().st_mtime for path in source_files):
        return
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    subprocess.run([npm, "install"], cwd=RUNTIME_ROOT, check=True)
    subprocess.run([npm, "run", "build"], cwd=RUNTIME_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", default="ladybug_marinette_expanded_smoke")
    parser.add_argument("--name", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    ensure_build()
    state_path = STATE_ROOT / f"{args.candidate}.json"
    if not state_path.exists():
        write_avatar_activity_state(
            args.candidate,
            "standing naturally in the room",
            source="avatar_runtime",
        )
    port = args.port or available_port()
    handler = functools.partial(QuietStaticHandler, directory=str(PROJECT_ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    query = urllib.parse.urlencode({"candidate": args.candidate, "name": args.name})
    url = f"http://127.0.0.1:{port}/Avatar/runtime3d/dist/index.html?{query}"
    print(url, flush=True)
    if not args.no_open:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
