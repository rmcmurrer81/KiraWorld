"""Present the local WebGL avatar as a borderless viewport over a Tk frame."""
from __future__ import annotations

import ctypes
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Any


GWL_STYLE = -16
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8
GA_ROOT = 2
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_BORDER = 0x00800000
WS_DLGFRAME = 0x00400000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
HWND_TOP = 0


def _available_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _edge_executable() -> Path | None:
    found = shutil.which("msedge")
    if found:
        return Path(found)
    roots = [os.getenv("PROGRAMFILES(X86)"), os.getenv("PROGRAMFILES"), os.getenv("LOCALAPPDATA")]
    for root in roots:
        if not root:
            continue
        candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if candidate.exists():
            return candidate
    return None


def _terminate_process_tree(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        check=False,
    )
    try:
        process.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        pass


class EmbeddedEdgeAvatar:
    """Own a borderless Edge viewport that tracks a Tk host frame."""

    def __init__(self, host: Any, project_root: Path) -> None:
        self.host = host
        self.project_root = Path(project_root)
        self.events: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self._lock = threading.Lock()
        self._generation = 0
        self._server: subprocess.Popen[Any] | None = None
        self._edge: subprocess.Popen[Any] | None = None
        self._pending_server: subprocess.Popen[Any] | None = None
        self._pending_edge: subprocess.Popen[Any] | None = None
        self._hwnd = 0
        self._host_hwnd = 0
        self.candidate_id = ""
        self.host.bind("<Configure>", self._on_configure, add="+")
        self.host.bind("<Map>", self._on_map, add="+")
        self.host.bind("<Unmap>", self._on_unmap, add="+")
        self.host.winfo_toplevel().bind("<Configure>", self._on_configure, add="+")

    @property
    def embedded(self) -> bool:
        return self.is_live()

    def is_live(self, candidate_id: str | None = None) -> bool:
        """Return true only while the current browser window and processes are alive."""
        if os.name != "nt":
            return False
        with self._lock:
            hwnd = self._hwnd
            current_candidate = self.candidate_id
            edge = self._edge
            server = self._server
        if candidate_id and current_candidate != candidate_id:
            return False
        if not hwnd or edge is None or server is None:
            return False
        if edge.poll() is not None or server.poll() is not None:
            return False
        return bool(ctypes.windll.user32.IsWindow(hwnd))

    def ensure_attached(self) -> bool:
        """Keep an existing viewport parented, visible, and correctly sized."""
        if not self.is_live():
            return False
        hwnd = self._hwnd
        user32 = ctypes.windll.user32
        if not self.host.winfo_ismapped():
            return False
        self.resize()
        host_hwnd = int(self.host.winfo_id())
        return bool(
            user32.IsWindow(hwnd)
            and int(user32.GetParent(hwnd) or 0) == host_hwnd
        )

    def start(self, candidate_id: str, display_name: str) -> None:
        if os.name != "nt":
            self.events.put(("error", candidate_id, "Embedded 3D requires Windows."))
            return
        edge = _edge_executable()
        if edge is None:
            self.events.put(("error", candidate_id, "Microsoft Edge was not found."))
            return
        self.stop()
        self.host.update_idletasks()
        host_hwnd = int(self.host.winfo_id())
        with self._lock:
            self._generation += 1
            generation = self._generation
            self.candidate_id = candidate_id
        threading.Thread(
            target=self._launch_worker,
            args=(generation, host_hwnd, edge, candidate_id, display_name),
            daemon=True,
        ).start()

    def stop(self) -> None:
        with self._lock:
            self._generation += 1
            edge, server = self._edge, self._server
            pending_edge, pending_server = self._pending_edge, self._pending_server
            self._edge = None
            self._server = None
            self._pending_edge = None
            self._pending_server = None
            self._hwnd = 0
            self._host_hwnd = 0
            self.candidate_id = ""
        _terminate_process_tree(edge)
        _terminate_process_tree(server)
        if pending_edge is not edge:
            _terminate_process_tree(pending_edge)
        if pending_server is not server:
            _terminate_process_tree(pending_server)

    def poll(self) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        failed_candidate = ""
        failed_note = ""
        with self._lock:
            if self._hwnd and self._edge is not None and self._edge.poll() is not None:
                failed_candidate = self.candidate_id
                failed_note = "The embedded avatar window closed unexpectedly."
            elif self._hwnd and self._server is not None and self._server.poll() is not None:
                failed_candidate = self.candidate_id
                failed_note = "The local avatar server stopped unexpectedly."
        if failed_candidate:
            self.stop()
            rows.append(("error", failed_candidate, failed_note))
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return rows
            if event[0] == "ready":
                with self._lock:
                    current_viewport_is_ready = bool(
                        self._hwnd
                        and self.candidate_id == event[1]
                        and self._edge is not None
                        and self._edge.poll() is None
                        and self._server is not None
                        and self._server.poll() is None
                    )
                if not current_viewport_is_ready:
                    continue
            rows.append(event)

    def resize(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        if not self.host.winfo_ismapped():
            return
        self.host.update_idletasks()
        width = int(self.host.winfo_width())
        height = int(self.host.winfo_height())
        # Tk briefly reports a 1x1 host while neighboring widgets are repacked.
        # Resizing Chromium to that transient size can discard its WebGL surface.
        if width < 8 or height < 8:
            return
        user32 = ctypes.windll.user32
        host_hwnd = int(self.host.winfo_id())
        if int(user32.GetParent(hwnd) or 0) != host_hwnd:
            self._prepare_overlay(hwnd, host_hwnd)
            self._host_hwnd = host_hwnd
        user32.SetWindowPos(
            hwnd,
            HWND_TOP,
            0,
            0,
            width,
            height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

    def _on_configure(self, _event: Any) -> None:
        self.resize()

    def _on_map(self, _event: Any) -> None:
        self.resize()

    def _on_unmap(self, _event: Any) -> None:
        # A Tk child can briefly report an unmap while surrounding widgets are
        # repacked. Leave the embedded browser alone; resize() restores it as
        # soon as the host is mapped again.
        return

    def _launch_worker(
        self,
        generation: int,
        host_hwnd: int,
        edge_path: Path,
        candidate_id: str,
        display_name: str,
    ) -> None:
        server: subprocess.Popen[Any] | None = None
        edge: subprocess.Popen[Any] | None = None
        try:
            port = _available_port()
            hidden = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            server = subprocess.Popen(
                [
                    sys.executable,
                    str(self.project_root / "tools" / "serve_avatar_runtime.py"),
                    "--candidate",
                    candidate_id,
                    "--name",
                    display_name,
                    "--port",
                    str(port),
                    "--no-open",
                ],
                cwd=str(self.project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=hidden,
            )
            with self._lock:
                if generation != self._generation:
                    _terminate_process_tree(server)
                    return
                self._pending_server = server
            token = "KiraEmbeddedAvatar-" + uuid.uuid4().hex
            query = urllib.parse.urlencode(
                {"candidate": candidate_id, "name": display_name, "embedded": "1", "title": token}
            )
            url = f"http://127.0.0.1:{port}/Avatar/runtime3d/dist/index.html?{query}"
            deadline = time.time() + 45
            while time.time() < deadline:
                if not self._is_current(generation):
                    return
                if server.poll() is not None:
                    raise RuntimeError("The local avatar server stopped before the viewport opened.")
                try:
                    with urllib.request.urlopen(url, timeout=1.2) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(0.25)
            else:
                raise RuntimeError("The local avatar server did not become ready in time.")

            profile_dir = self.project_root / "Data" / "runtime" / f"embedded_edge_{os.getpid()}_{generation}"
            profile_dir.mkdir(parents=True, exist_ok=True)
            edge = subprocess.Popen(
                [
                    str(edge_path),
                    f"--app={url}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--autoplay-policy=no-user-gesture-required",
                    "--window-position=-32000,-32000",
                    "--window-size=300,500",
                ],
                cwd=str(self.project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with self._lock:
                if generation != self._generation:
                    _terminate_process_tree(edge)
                    return
                self._pending_edge = edge
            hwnd = self._wait_for_window(token, generation, timeout=30)
            if not hwnd:
                raise RuntimeError("Edge opened, but its local avatar viewport was not found.")
            self._prepare_overlay(hwnd, host_hwnd)
            if not self._is_current(generation):
                return
            with self._lock:
                self._server = server
                self._edge = edge
                self._pending_server = None
                self._pending_edge = None
                self._hwnd = hwnd
                self._host_hwnd = host_hwnd
            self.events.put(("ready", candidate_id, "Embedded local 3D viewport ready."))
        except Exception as exc:
            self.events.put(("error", candidate_id, str(exc)))
            _terminate_process_tree(edge)
            _terminate_process_tree(server)
        finally:
            if not self._is_current(generation):
                _terminate_process_tree(edge)
                _terminate_process_tree(server)
            with self._lock:
                if self._pending_edge is edge:
                    self._pending_edge = None
                if self._pending_server is server:
                    self._pending_server = None

    def _is_current(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation

    def _wait_for_window(self, token: str, generation: int, timeout: float) -> int:
        user32 = ctypes.windll.user32
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def find_once() -> int:
            found = 0

            @callback_type
            def enum_proc(hwnd: int, _lparam: int) -> bool:
                nonlocal found
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buffer, len(buffer))
                    if token in buffer.value:
                        found = int(hwnd)
                        return False
                return True

            user32.EnumWindows(enum_proc, 0)
            return found

        deadline = time.time() + timeout
        while time.time() < deadline and self._is_current(generation):
            hwnd = find_once()
            if hwnd:
                return hwnd
            time.sleep(0.2)
        return 0

    @staticmethod
    def _prepare_overlay(hwnd: int, host_hwnd: int) -> None:
        user32 = ctypes.windll.user32
        style = int(user32.GetWindowLongW(hwnd, GWL_STYLE))
        style &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU | WS_BORDER | WS_DLGFRAME)
        style |= WS_CHILD | WS_VISIBLE
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        ex_style = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
        ex_style &= ~(WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
        ex_style |= WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        user32.SetParent(hwnd, host_hwnd)
        user32.SetWindowPos(
            hwnd,
            HWND_TOP,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

    @staticmethod
    def _strip_chrome(hwnd: int) -> None:
        user32 = ctypes.windll.user32
        style = int(user32.GetWindowLongW(hwnd, GWL_STYLE))
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU | WS_BORDER | WS_DLGFRAME)
        style |= WS_POPUP
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        ex_style = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
        ex_style |= WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        user32.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
