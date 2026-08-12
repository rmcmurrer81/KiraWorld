from __future__ import annotations

import http.cookiejar
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
SERVER = ROOT / "tools" / "kira_world_shell_server.py"
WAITER = ROOT / "tools" / "wait_for_kira_world_shell.py"
STOPPER = ROOT / "tools" / "stop_owned_kira_world_shell.py"

from tools import kira_world_shell_viewer as viewer


def free_loopback_port(excluded: set[int]) -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = int(sock.getsockname()[1])
        if port not in excluded:
            excluded.add(port)
            return port


def http_result(
    url: str,
    *,
    token: str = "",
    origin: str = "",
    body: dict | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, bytes, object]:
    headers = {"accept": "application/json"}
    if token:
        headers["X-Kira-Shell-Token"] = token
    if origin:
        headers["Origin"] = origin
    data = None
    method = "GET"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    client = opener or urllib.request.build_opener()
    try:
        with client.open(request, timeout=5.0) as response:
            return int(response.status), response.read(), response.headers
    except urllib.error.HTTPError as exc:
        try:
            return int(exc.code), exc.read(), exc.headers
        finally:
            exc.close()


class FreshProcessLauncherContractTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        if sys.platform != "win32":
            self.skipTest("the normal Kira owner launchers are Windows launchers")

    def _environment(
        self,
        runtime: Path,
        ports: tuple[int, int, int],
        token: str,
        launch_id: str,
    ) -> dict[str, str]:
        shell_port, asr_port, visual_port = ports
        env = os.environ.copy()
        env.update(
            {
                "KIRA_RUNTIME": str(runtime.resolve()),
                "KIRA_SHELL_PORT": str(shell_port),
                "KIRA_ASR_PORT": str(asr_port),
                "KIRA_VISUAL_PORT": str(visual_port),
                "KIRA_SHELL_TEXT_ONLY": "1",
                "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
                "KIRA_WORLD_SHELL_ACTIVE": "0",
                "KIRA_MODEL_BACKEND": "ollama",
                "KIRA_MODEL_NAME": QWEN_MODEL,
                "KIRA_MODEL_DIGEST": QWEN_DIGEST,
                "KIRA_ENABLE_QWEN35_BUFFERED_STREAM_TIMING_CANDIDATE": "1",
                "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE": "0",
                "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE": "0",
                "KIRA_ASR_SESSION_TOKEN": secrets.token_urlsafe(32),
                "KIRA_VISUAL_SESSION_TOKEN": secrets.token_urlsafe(32),
                "KIRA_SHELL_API_TOKEN": token,
                "KIRA_SHELL_LAUNCH_ID": launch_id,
                "PYTHONDONTWRITEBYTECODE": "1",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
        )
        return env

    def _start(self, env: dict[str, str]) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, str(SERVER), "--no-browser"],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def _waiter(
        self,
        url: str,
        pid: int,
        env: dict[str, str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(WAITER),
                "--url",
                url,
                "--timeout",
                str(timeout),
                "--owned-pid",
                str(pid),
            ],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=max(10.0, timeout + 5.0),
        )

    def _ports_are_closed(self, ports: tuple[int, int, int]) -> bool:
        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    return False
        return True

    def _ports_are_open(self, ports: tuple[int, ...]) -> bool:
        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) != 0:
                    return False
        return True

    def _close_exact(
        self,
        process: subprocess.Popen[str],
        url: str,
        env: dict[str, str],
        runtime: Path,
        ports: tuple[int, int, int],
    ) -> None:
        with patch.dict(os.environ, env, clear=False):
            result = viewer.api_json(
                url,
                "/api/safe-close",
                {"reason": "fresh-process launcher integration complete"},
                timeout=6.0,
            )
        self.assertTrue(result.get("ok"))
        self.assertEqual(process.wait(timeout=15.0), 0)
        process.communicate(timeout=1.0)
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not self._ports_are_closed(ports):
            time.sleep(0.1)
        self.assertTrue(self._ports_are_closed(ports))
        self.assertFalse((runtime / "kira_world_shell.lock").exists())

    def _terminate_exact_on_failure(self, process: subprocess.Popen[str] | None) -> None:
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)
        process.communicate(timeout=1.0)

    def test_real_server_waiter_viewer_and_stale_token_contract(self) -> None:
        used: set[int] = set()
        ports = (
            free_loopback_port(used),
            free_loopback_port(used),
            free_loopback_port(used),
        )
        shell_port = ports[0]
        url = f"http://127.0.0.1:{shell_port}/"
        origin = url.rstrip("/")

        with tempfile.TemporaryDirectory(prefix="kira_shell_fresh_process_") as raw_runtime:
            runtime = Path(raw_runtime)
            token_1 = secrets.token_urlsafe(32)
            launch_1 = uuid.uuid4().hex
            env_1 = self._environment(runtime, ports, token_1, launch_1)
            process_1: subprocess.Popen[str] | None = None
            process_2: subprocess.Popen[str] | None = None
            try:
                process_1 = self._start(env_1)
                ready_1 = self._waiter(url, process_1.pid, env_1, 20.0)
                self.assertEqual(ready_1.returncode, 0, ready_1.stdout + ready_1.stderr)
                self.assertNotIn(token_1, ready_1.stdout + ready_1.stderr)
                sidecar_deadline = time.monotonic() + 20.0
                while (
                    time.monotonic() < sidecar_deadline
                    and not self._ports_are_open(ports[1:])
                ):
                    time.sleep(0.1)
                sidecar_logs = "\n".join(
                    f"{path.name}: {path.read_text(encoding='utf-8', errors='replace')}"
                    for path in sorted(runtime.glob("kira_text_voice_*_*.log"))
                )
                self.assertTrue(self._ports_are_open(ports[1:]), sidecar_logs)

                status, raw, _ = http_result(url + "api/state")
                self.assertEqual(status, 403)
                self.assertEqual(
                    json.loads(raw), {"error": "local shell API authorization failed"}
                )
                wrong_token = secrets.token_urlsafe(32)
                status, _, _ = http_result(
                    url + "api/state", token=wrong_token, origin=origin
                )
                self.assertEqual(status, 403)

                wrong_env = env_1.copy()
                wrong_env["KIRA_SHELL_API_TOKEN"] = wrong_token
                rejected = self._waiter(url, process_1.pid, wrong_env, 1.2)
                self.assertEqual(rejected.returncode, 2)
                self.assertNotIn(token_1, rejected.stdout + rejected.stderr)
                self.assertNotIn(wrong_token, rejected.stdout + rejected.stderr)

                jar = http.cookiejar.CookieJar()
                opener = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(jar)
                )
                status, html, _ = http_result(url, opener=opener)
                page = html.decode("utf-8")
                self.assertEqual(status, 200)
                self.assertIn("<title>Kira Text + Voice Chat</title>", page)
                embedded = re.search(r'data-shell-api-token="([A-Za-z0-9_-]+)"', page)
                self.assertIsNotNone(embedded)
                self.assertEqual(embedded.group(1), token_1)
                self.assertGreater(len(list(jar)), 0)

                viewer_env_1 = env_1.copy()
                viewer_env_1["KIRA_SHELL_CHILD_PID"] = str(process_1.pid)
                with patch.dict(os.environ, viewer_env_1, clear=False):
                    self.assertTrue(viewer.wait_for_shell(url, 3.0))
                    state_1 = viewer.api_json(url, "/api/state", timeout=3.0)
                self.assertEqual(state_1["shell_pid"], process_1.pid)
                self.assertEqual(state_1["shell_launch_id"], launch_1)
                self.assertEqual(state_1["active_candidate"], "")

                self._close_exact(process_1, url, viewer_env_1, runtime, ports)
                process_1 = None

                token_2 = secrets.token_urlsafe(32)
                launch_2 = uuid.uuid4().hex
                env_2 = self._environment(runtime, ports, token_2, launch_2)
                process_2 = self._start(env_2)

                stale_env = env_1.copy()
                stale_env["KIRA_SHELL_CHILD_PID"] = str(process_2.pid)
                stale = self._waiter(url, process_2.pid, stale_env, 1.2)
                self.assertEqual(stale.returncode, 2)
                self.assertNotIn(token_1, stale.stdout + stale.stderr)
                self.assertNotIn(token_2, stale.stdout + stale.stderr)

                ready_2 = self._waiter(url, process_2.pid, env_2, 20.0)
                self.assertEqual(ready_2.returncode, 0, ready_2.stdout + ready_2.stderr)
                status, _, _ = http_result(
                    url + "api/state", token=token_1, origin=origin
                )
                self.assertEqual(status, 403)
                status, raw, _ = http_result(
                    url + "api/state", token=token_2, origin=origin
                )
                self.assertEqual(status, 200)
                state_2 = json.loads(raw)
                self.assertEqual(state_2["shell_pid"], process_2.pid)
                self.assertEqual(state_2["shell_launch_id"], launch_2)
                self.assertNotEqual(state_2["shell_launch_id"], launch_1)

                viewer_env_2 = env_2.copy()
                viewer_env_2["KIRA_SHELL_CHILD_PID"] = str(process_2.pid)
                self._close_exact(process_2, url, viewer_env_2, runtime, ports)
                process_2 = None
            finally:
                self._terminate_exact_on_failure(process_2)
                self._terminate_exact_on_failure(process_1)

    def test_failed_launch_cleanup_stops_only_the_exact_locked_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kira_shell_owned_stop_") as raw_runtime:
            runtime = Path(raw_runtime)
            launch_id = uuid.uuid4().hex
            child = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                (runtime / "kira_world_shell.lock").write_text(
                    json.dumps(
                        {
                            "pid": child.pid,
                            "port": 8768,
                            "launch_id": uuid.uuid4().hex,
                        }
                    ),
                    encoding="utf-8",
                )
                refused = subprocess.run(
                    [
                        sys.executable,
                        str(STOPPER),
                        "--pid",
                        str(child.pid),
                        "--port",
                        "8768",
                        "--runtime",
                        str(runtime),
                        "--launch-id",
                        launch_id,
                    ],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=10.0,
                )
                self.assertEqual(refused.returncode, 2)
                self.assertIsNone(child.poll())

                (runtime / "kira_world_shell.lock").write_text(
                    json.dumps(
                        {
                            "pid": child.pid,
                            "port": 8768,
                            "launch_id": launch_id,
                        }
                    ),
                    encoding="utf-8",
                )
                stopped = subprocess.run(
                    [
                        sys.executable,
                        str(STOPPER),
                        "--pid",
                        str(child.pid),
                        "--port",
                        "8768",
                        "--runtime",
                        str(runtime),
                        "--launch-id",
                        launch_id,
                    ],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=15.0,
                )
                self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
                child.wait(timeout=5.0)
                self.assertIsNotNone(child.returncode)
            finally:
                self._terminate_exact_on_failure(child)


if __name__ == "__main__":
    unittest.main()
