"""Output-path and process capability fences used by the evaluator.

These controls are defense in depth for the evaluator process. They are not an
operating-system sandbox and must not be described as one.
"""

from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any, Iterable


def _resolved(path: os.PathLike[str] | str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def is_within(path: os.PathLike[str] | str, root: os.PathLike[str] | str) -> bool:
    candidate = _resolved(path)
    boundary = _resolved(root)
    return candidate == boundary or boundary in candidate.parents


class OutputGuard:
    """Mediates every evaluator-owned write beneath one explicit root."""

    def __init__(self, root: os.PathLike[str] | str):
        raw = Path(root).expanduser()
        if str(raw).strip() in {"", "."}:
            raise ValueError("--output-root must name a dedicated directory, not '.'")
        self.root = raw.resolve(strict=False)
        if self.root == Path(self.root.anchor):
            raise ValueError("filesystem roots cannot be evaluator output roots")

    def prepare(self) -> None:
        # Creating the named output root is the sole pre-fence filesystem write.
        # Reusing evidence would mix two evaluations, invalidate run counts, and
        # make protected-path comparisons ambiguous. An existing empty directory
        # is accepted for callers that preallocate it; any content fails closed.
        if self.root.exists():
            if not self.root.is_dir():
                raise ValueError("--output-root exists and is not a directory")
            try:
                next(self.root.iterdir())
            except StopIteration:
                return
            raise FileExistsError("--output-root must be new or empty")
        self.root.mkdir(parents=True, exist_ok=False)

    def checked(self, relative: os.PathLike[str] | str) -> Path:
        value = Path(relative)
        if value.is_absolute():
            candidate = value.resolve(strict=False)
        else:
            candidate = (self.root / value).resolve(strict=False)
        if not is_within(candidate, self.root):
            raise PermissionError(f"write escaped output root: {candidate}")
        return candidate

    def make_dir(self, relative: os.PathLike[str] | str) -> Path:
        path = self.checked(relative)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_text(self, relative: os.PathLike[str] | str, text: str) -> Path:
        path = self.checked(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        self.checked(temporary)
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return path

    def write_json(self, relative: os.PathLike[str] | str, value: Any) -> Path:
        return self.write_text(
            relative,
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )

    def append_jsonl(self, relative: os.PathLike[str] | str, value: Any) -> Path:
        path = self.checked(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return path


class ProcessWriteFence:
    """Audit-hook fence rejecting evaluator-process writes outside one root."""

    _installed = False
    _active_root: Path | None = None

    _single_path_events = {
        "os.chdir",  # chdir changes process state and complicates path proofs.
        "os.remove",
        "os.rmdir",
        "os.mkdir",
        "os.chmod",
        "os.truncate",
        "os.unlink",
        "os.symlink",
    }
    _two_path_events = {"os.rename", "os.replace", "os.link"}

    @classmethod
    def install(cls, root: os.PathLike[str] | str) -> None:
        cls._active_root = _resolved(root)
        if not cls._installed:
            sys.addaudithook(cls._audit)
            cls._installed = True

    @classmethod
    def _assert_allowed(cls, value: Any, event: str) -> None:
        if isinstance(value, int) or value is None:
            return
        if isinstance(value, bytes):
            value = os.fsdecode(value)
        root = cls._active_root
        if root is None or not is_within(value, root):
            raise PermissionError(f"{event} denied outside evaluator output root: {value}")

    @classmethod
    def _audit(cls, event: str, args: tuple[Any, ...]) -> None:
        if cls._active_root is None:
            return
        if event == "open" and args:
            path = args[0]
            writing = False
            # builtins.open emits (path, mode, flags); os.open emits
            # (path, None, flags). Inspect every mode/flag operand so os.open
            # cannot bypass the fence by placing flags in args[2].
            for mode_or_flags in args[1:]:
                if isinstance(mode_or_flags, str):
                    writing = writing or any(
                        marker in mode_or_flags for marker in ("w", "a", "+", "x")
                    )
                elif isinstance(mode_or_flags, int):
                    write_bits = (
                        os.O_WRONLY
                        | os.O_RDWR
                        | os.O_CREAT
                        | os.O_TRUNC
                        | os.O_APPEND
                    )
                    writing = writing or bool(mode_or_flags & write_bits)
            if writing:
                cls._assert_allowed(path, event)
            return
        if event in cls._single_path_events and args:
            # chdir is forbidden even inside the root so relative-path semantics
            # remain stable for the whole run.
            if event == "os.chdir":
                raise PermissionError("os.chdir is disabled during evaluation")
            cls._assert_allowed(args[0], event)
            return
        if event in cls._two_path_events and len(args) >= 2:
            cls._assert_allowed(args[0], event)
            cls._assert_allowed(args[1], event)
            return
        if event in {"subprocess.Popen", "os.system"}:
            raise PermissionError(f"{event} is disabled during evaluation")


def _host_is_loopback(host: Any) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="strict")
    text = str(host).strip().lower().strip("[]")
    if text == "localhost":
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


class LoopbackOnlyNetwork:
    """Temporarily blocks Python socket connections except loopback."""

    def __init__(self) -> None:
        self._socket_class = socket.socket
        self._getaddrinfo = socket.getaddrinfo
        self._create_connection = socket.create_connection

    def __enter__(self) -> "LoopbackOnlyNetwork":
        original_socket_class = self._socket_class
        original_getaddrinfo = self._getaddrinfo
        original_create_connection = self._create_connection

        class GuardedSocket(original_socket_class):  # type: ignore[misc, valid-type]
            def connect(self, address: Any) -> Any:
                if not isinstance(address, tuple) or not address or not _host_is_loopback(address[0]):
                    raise PermissionError(f"non-loopback socket denied: {address!r}")
                return super().connect(address)

            def connect_ex(self, address: Any) -> int:
                if not isinstance(address, tuple) or not address or not _host_is_loopback(address[0]):
                    raise PermissionError(f"non-loopback socket denied: {address!r}")
                return super().connect_ex(address)

        def guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
            if not _host_is_loopback(host):
                raise PermissionError(f"DNS/network lookup denied for non-loopback host: {host!r}")
            return original_getaddrinfo(host, *args, **kwargs)

        def guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
            if not isinstance(address, tuple) or not address or not _host_is_loopback(address[0]):
                raise PermissionError(f"non-loopback connection denied: {address!r}")
            return original_create_connection(address, *args, **kwargs)

        socket.socket = GuardedSocket
        socket.getaddrinfo = guarded_getaddrinfo
        socket.create_connection = guarded_create_connection
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        socket.socket = self._socket_class
        socket.getaddrinfo = self._getaddrinfo
        socket.create_connection = self._create_connection


def reject_output_protected_overlap(
    output_root: os.PathLike[str] | str,
    protected_paths: Iterable[os.PathLike[str] | str],
) -> None:
    output = _resolved(output_root)
    for protected in protected_paths:
        item = _resolved(protected)
        if is_within(output, item) or is_within(item, output):
            raise ValueError(
                f"protected path and output root overlap; proof would be invalid: {item}"
            )


def install_disabled_capability_environment(output_root: Path) -> dict[str, str | None]:
    """Disable optional runtime capabilities and redirect temp writes.

    Returns the previous values so callers could restore them if embedding this
    library. The command-line process intentionally leaves the disabled values in
    force until exit.
    """

    values = {
        "KIRA_VOICE_ENABLED": "0",
        "KIRA_MICROPHONE_ENABLED": "0",
        "KIRA_CAMERA_ENABLED": "0",
        "KIRA_BODY_ENABLED": "0",
        "KIRA_ROS2_ENABLED": "0",
        "KIRA_EMBODIMENT_ENABLED": "0",
        "NO_PROXY": "127.0.0.1,localhost,::1",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "ALL_PROXY": "",
        "TMP": str(output_root / "tmp"),
        "TEMP": str(output_root / "tmp"),
    }
    previous: dict[str, str | None] = {}
    for key, value in values.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    return previous
