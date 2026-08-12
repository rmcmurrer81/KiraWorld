#!/usr/bin/env python3
"""Observe the Kira Home World preview and write truth-report evidence.

This attaches to a Chrome/Edge DevTools endpoint, turns on Observe/Follow in the
world runtime, samples the active body truth snapshot, and saves screenshots.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import time
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json(url: str, timeout: float = 2.5):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class CdpWebSocket:
    def __init__(self, ws_url: str, timeout: float = 12.0):
        self.ws_url = ws_url
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.next_id = 1

    def connect(self):
        parsed = urllib.parse.urlparse(self.ws_url)
        if parsed.scheme != "ws":
            raise ValueError(f"Only ws:// CDP endpoints are supported, got {self.ws_url}")
        port = parsed.port or 80
        host = parsed.hostname or "127.0.0.1"
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        sock = socket.create_connection((host, port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WebSocket handshake failed: {response[:200]!r}")
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if expected_accept.encode("ascii") not in response:
            raise RuntimeError("WebSocket handshake did not return the expected accept key.")
        self.sock = sock

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _recv_exact(self, count: int) -> bytes:
        assert self.sock is not None
        data = b""
        while len(data) < count:
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise RuntimeError("WebSocket closed while reading.")
            data += chunk
        return data

    def _send_frame(self, payload: bytes, opcode: int = 1):
        assert self.sock is not None
        first = 0x80 | opcode
        length = len(payload)
        mask = os.urandom(4)
        if length < 126:
            header = struct.pack("!BB", first, 0x80 | length)
        elif length < (1 << 16):
            header = struct.pack("!BBH", first, 0x80 | 126, length)
        else:
            header = struct.pack("!BBQ", first, 0x80 | 127, length)
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def _recv_frame(self) -> bytes:
        while True:
            b1, b2 = self._recv_exact(2)
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else b""
            data = self._recv_exact(length) if length else b""
            if masked:
                data = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
            if opcode == 0x8:
                raise RuntimeError("WebSocket close frame received.")
            if opcode == 0x9:
                self._send_frame(data, opcode=0xA)
                continue
            if opcode in (0x1, 0x2, 0x0):
                return data

    def call(self, method: str, params: dict | None = None):
        message_id = self.next_id
        self.next_id += 1
        payload = {"id": message_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send_frame(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        while True:
            message = json.loads(self._recv_frame().decode("utf-8"))
            if message.get("id") != message_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP error from {method}: {message['error']}")
            return message.get("result", {})


def find_target(cdp_base: str, fragment: str) -> dict:
    targets = read_json(cdp_base.rstrip("/") + "/json/list")
    pages = [target for target in targets if target.get("type") == "page" and target.get("webSocketDebuggerUrl")]
    fragment_l = (fragment or "").lower()
    if fragment_l:
        for target in pages:
            haystack = f"{target.get('title','')} {target.get('url','')}".lower()
            if fragment_l in haystack:
                return target
    if pages:
        return pages[0]
    raise RuntimeError("No debuggable page target found.")


def maybe_launch_edge(port: int, url: str, profile_dir: Path) -> subprocess.Popen | None:
    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    edge = next((path for path in candidates if path.exists()), None)
    if not edge:
        print("Could not find msedge.exe to launch automatically.", file=sys.stderr)
        return None
    profile_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [
            str(edge),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--disable-extensions",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def runtime_eval(cdp: CdpWebSocket, expression: str):
    result = cdp.call(
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
            "timeout": 5000,
        },
    )
    remote = result.get("result", {})
    return remote.get("value")


def sample_expression(reason: str, interval_seconds: int | None = None) -> str:
    start = ""
    if interval_seconds is not None:
        start = f"dbg.startObservationReport({{ intervalSeconds: {int(interval_seconds)} }});"
    return f"""
(() => {{
  const dbg = window.kiraHomeWorldDebug;
  if (!dbg) return {{ error: "kiraHomeWorldDebug not found", href: location.href }};
  dbg.setObserveFollow(true);
  {start}
  return dbg.observationSample({json.dumps(reason)});
}})()
"""


def summarize_sample(sample: dict) -> str:
    runtime = sample.get("runtime") or {}
    truth = sample.get("mindBodyTruth") or runtime.get("mindBodyTruth") or {}
    claim = runtime.get("activeShellClaim") or truth.get("shellClaim") or {}
    label = runtime.get("activeLabel") or claim.get("label") or "unknown"
    action = runtime.get("activeAction") or truth.get("runtimeAction") or "unknown"
    claim_action = claim.get("action") or "none"
    pos = runtime.get("activePosition") or {}
    ctf = runtime.get("captureFlag") or {}
    verdict = "AGREES" if truth.get("agrees", True) else "FALSE/NEEDS REVIEW"
    reasons = "; ".join(truth.get("mismatchReasons") or [])
    where = f"x={pos.get('x','?')} y={pos.get('y','?')} z={pos.get('z','?')}"
    ctf_bits = ""
    if ctf:
        ctf_bits = f" | CTF phase={ctf.get('phase')} actor={ctf.get('actor')} enemies={ctf.get('npcCount')}"
    if reasons:
        reasons = f" | reasons: {reasons}"
    return f"{sample.get('iso')} | {label} | claim={claim_action} runtime={action} | {where} | {verdict}{reasons}{ctf_bits}"


def capture_screenshot(cdp: CdpWebSocket, path: Path):
    cdp.call("Page.bringToFront")
    data = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True}).get("data")
    if not data:
        return False
    path.write_bytes(base64.b64decode(data))
    return True


def copy_runtime_chat_logs(out_dir: Path) -> list[Path]:
    copied: list[Path] = []
    for source in [
        Path("Data/runtime/kira_world_chat_log.jsonl"),
        Path("Data/runtime/kira_world_life_loop_log.jsonl"),
    ]:
        if not source.exists():
            continue
        destination = out_dir / source.name
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe active Kira World body behavior and save truth evidence.")
    parser.add_argument("--cdp", default="http://127.0.0.1:9335", help="Chrome/Edge DevTools HTTP endpoint.")
    parser.add_argument("--duration-minutes", type=float, default=180.0)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--screenshot-every-seconds", type=int, default=300)
    parser.add_argument("--target-url-fragment", default="home", help="Pick the first debuggable page whose title/url contains this.")
    parser.add_argument("--out-dir", default="", help="Output directory. Defaults to Logs/observation_reports/<timestamp>.")
    parser.add_argument("--launch-edge", action="store_true", help="Launch Edge with remote debugging first.")
    parser.add_argument("--url", default="http://127.0.0.1:5173/?area=home", help="URL to open when --launch-edge is used.")
    parser.add_argument("--leave-following", action="store_true", help="Leave Observe/Follow active when the report exits.")
    parser.add_argument("--keep-browser-open", action="store_true", help="Do not close the Edge process launched by this script.")
    args = parser.parse_args()

    parsed_cdp = urllib.parse.urlparse(args.cdp)
    cdp_port = parsed_cdp.port or 9335
    launched = None
    if args.launch_edge:
        launched = maybe_launch_edge(cdp_port, args.url, Path("_tmp_kira_observer_edge_profile").resolve())
        time.sleep(2.5)

    out_dir = Path(args.out_dir) if args.out_dir else Path("Logs/observation_reports") / now_stamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshots = out_dir / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "samples.jsonl"
    md_path = out_dir / "report.md"

    try:
        target = find_target(args.cdp, args.target_url_fragment)
    except Exception as exc:
        print(f"Could not connect to DevTools at {args.cdp}: {exc}", file=sys.stderr)
        print("Open the world in Edge/Chrome with --remote-debugging-port=9335, or rerun this script with --launch-edge.", file=sys.stderr)
        if launched:
            launched.terminate()
        return 2

    cdp = CdpWebSocket(target["webSocketDebuggerUrl"])
    lines = [
        "# Kira Life Loop Observation Report",
        "",
        f"- Started: {datetime.now().isoformat(timespec='seconds')}",
        f"- Target: {target.get('title')} | {target.get('url')}",
        f"- Interval: {args.interval_seconds}s",
        f"- Screenshot Every: {args.screenshot_every_seconds}s",
        "",
        "## Samples",
        "",
    ]
    start_time = time.time()
    deadline = start_time + max(1, args.duration_minutes * 60.0)
    next_sample = start_time
    next_screenshot = start_time
    sample_count = 0
    screenshot_count = 0

    try:
        cdp.connect()
        runtime_eval(cdp, sample_expression("external_report_start", args.interval_seconds))
        with jsonl_path.open("a", encoding="utf-8") as jsonl:
            while time.time() < deadline:
                now = time.time()
                if now >= next_sample:
                    sample = runtime_eval(cdp, sample_expression("external_report_interval"))
                    if not isinstance(sample, dict):
                        sample = {"error": "Runtime sample was not an object", "raw": sample, "iso": datetime.now().isoformat()}
                    jsonl.write(json.dumps(sample, ensure_ascii=False) + "\n")
                    jsonl.flush()
                    line = summarize_sample(sample)
                    lines.append(f"- {line}")
                    print(line)
                    sample_count += 1
                    next_sample = now + args.interval_seconds
                if now >= next_screenshot:
                    shot_path = screenshots / f"screenshot_{sample_count:04d}_{now_stamp()}.png"
                    if capture_screenshot(cdp, shot_path):
                        screenshot_count += 1
                        lines.append(f"  - screenshot: `{shot_path.name}`")
                    next_screenshot = now + args.screenshot_every_seconds
                time.sleep(0.5)
    finally:
        if not args.leave_following:
            try:
                runtime_eval(cdp, "(() => { window.kiraHomeWorldDebug?.stopObservationReport?.(); window.kiraHomeWorldDebug?.setObserveFollow?.(false); return true; })()")
            except Exception:
                pass
        cdp.close()

    copied_logs = copy_runtime_chat_logs(out_dir)
    lines.extend([
        "",
        "## Totals",
        "",
        f"- Samples: {sample_count}",
        f"- Screenshots: {screenshot_count}",
        f"- Copied Chat/Life Logs: {len(copied_logs)}",
        f"- Finished: {datetime.now().isoformat(timespec='seconds')}",
    ])
    if copied_logs:
        lines.extend(["", "## Copied Logs", ""])
        lines.extend([f"- `{path.name}`" for path in copied_logs])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote report: {md_path}")
    print(f"Wrote samples: {jsonl_path}")
    print(f"Wrote screenshots: {screenshots}")
    if launched and not args.keep_browser_open:
        launched.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
