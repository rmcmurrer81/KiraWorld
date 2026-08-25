"""Fail-closed one-shot adapter for an isolated Kokoro runtime.

The subprocess protocol is implemented, but capabilities remain unavailable
until this product supplies an operating-system-enforced network/filesystem
sandbox. Environment flags alone are not advertised as local-only isolation.
"""

from __future__ import annotations

import hashlib
import base64
import json
import math
import os
import secrets
import signal
import stat
import subprocess
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Protocol

from ..errors import BackendUnavailableError, CancelledError, ValidationError
from ..models import BackendResult, SynthesisRequest, VoiceProfile
from .base import BackendCapabilities, CancellationToken

MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
AUDITION_EVIDENCE_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
ALLOWLIST = frozenset({"af_heart", "am_fenrir"})
PROVENANCE_SCOPE = "two_voice_generic_bootstrap_only"
MODEL_FILES = {
    "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
    "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    "voices/af_heart.pt": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
    "voices/am_fenrir.pt": "98e507eca1db08230ae3b6232d59c10aec9630022d19accac4f5d12fcec3c37a",
}
EXPECTED_WORKER_SHA256 = "b754dc942d5b80fd94964bd86f273a444937285759b29bf337a02e74611e7b72"
EXPECTED_RUNTIME_LOCK_SHA256 = "e0c5035721a091e97631818e77838aa417d2db7eff32e4b3adff643ddc3673f0"
EXPECTED_RUNTIME_BRIDGE_SHA256 = "44afec22d334c6ebf04f6584bb4ff61dda44c7e1d26088744d42379ca4c9300c"
EXPECTED_RUNTIME_PACKAGES = {
    "espeakng-loader": "0.2.4",
    "huggingface-hub": "1.28.0",
    "kokoro": "0.9.4",
    "misaki": "0.9.4",
    "phonemizer-fork": "3.3.2",
    "soundfile": "0.14.0",
    "torch": "2.11.0+cu130",
    "transformers": "5.15.1",
}
MAX_PROTOCOL_BYTES = 32_768
MAX_STDERR_BYTES = 8_192
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MXC_PROVIDER_ID = "microsoft-mxc-processcontainer-v1"
IMPLEMENTED_ISOLATION_PROVIDER_IDS: frozenset[str] = frozenset({MXC_PROVIDER_ID})
# Deliberately empty. The launch-only MXC canary is useful research evidence,
# but it does not yet prove denied network, denied outside-staging writes, or
# descendant cleanup. A later release must add those hostile canaries and close
# hash-to-launch TOCTOU before placing any provider ID in this set.
REVIEWED_ISOLATION_PROVIDER_IDS: frozenset[str] = frozenset()
REVIEWED_MXC_EXECUTABLE_SHA256: frozenset[str] = frozenset(
    {"6d2e7ee8f22e0508dc95412d4128985c1dbe29fc2688317d7cef38ee17c71504"}
)
REVIEWED_PYTHON_EXECUTABLE_SHA256: frozenset[str] = frozenset(
    {"21bb438c0d4a6f1f164b9a646f6ee000340185e5871180aec06db8d3f07c0082"}
)
RUNTIME_TREE_ALGORITHM = "sha256-relative-path-size-content-v1"
MAX_RUNTIME_TREE_FILES = 100_000
MAX_RUNTIME_TREE_BYTES = 8 * 1024 * 1024 * 1024
EXPECTED_RUNTIME_TREE = {
    "algorithm": RUNTIME_TREE_ALGORITHM,
    "file_count": 36_060,
    "total_bytes": 3_470_040_642,
    "tree_sha256": "eff6f127e3956d4e771690d50a72cc4146627392dc254ff9d806b4bbb3a3b24f",
}
EXPECTED_BASE_RUNTIME_TREE = {
    "algorithm": RUNTIME_TREE_ALGORITHM,
    "file_count": 6_265,
    "total_bytes": 155_302_843,
    "tree_sha256": "5ef513fee88aaac179968c65387a5bf1c47830a0a1e3698785b440d81627440d",
}
_LOCK_PATH = Path(__file__).resolve().parents[3] / "requirements-kokoro.lock.json"
_RUNTIME_BRIDGE_PATH = (
    Path(__file__).resolve().parents[3] / "evidence" / "kokoro_starter_runtime_bridge_v1.json"
)
_EVIDENCE_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_EVIDENCE_FILES = {
    "auditions/catalog_20260825/catalog-audition-report.json":
        "11a30ef13688d9adbb65cb81cfe5378b7f14235105c6d1b5d580498cf2ca540d",
    "auditions/catalog_20260825/catalog-audit-report.json":
        "bb486d49b779916f1a7c01dfa8a6f95fafdb1cea49a8e1118dd3b7d6022e1efd",
    "auditions/catalog_20260825/starter-owner-approval.json":
        "b91de4433382af5e1d9b92ed12773707f59624d85ddd735efdb6e15a2d4df175",
    "auditions/catalog_20260825/calm_female_approved.wav":
        "c3e3682817476212c990969901028758fbbde1eb4eb8c97153ef878b3939b33a",
    "auditions/catalog_20260825/warm_male_approved.wav":
        "0a8cdb8178bf56a6aa2442cca496dcf87a76b52e8eb0743488dc5f0e8c8a8a8e",
    "auditions/catalog_20260825/af_heart_neutral_audition.wav":
        "4c32bc7f4da15d5d9173fe6a0e783c557187cb7ff3c5379c5b6d5882e3e48a7b",
    "auditions/catalog_20260825/am_fenrir_neutral_audition.wav":
        "0532baf6ad37ef91b487031d5b8eecd4114ebf926d5e01ebc127eaae5da0bf94",
}


@dataclass(frozen=True, slots=True)
class KokoroConfig:
    python_executable: Path
    cache_root: Path
    staging_root: Path
    worker_script: Path = Path(__file__).with_name("kokoro_worker.py")
    runtime_lock: Path = _LOCK_PATH
    python_sha256: str | None = None
    runtime_bridge: Path = _RUNTIME_BRIDGE_PATH
    base_runtime_root: Path | None = None
    device: str = "cpu"
    timeout_seconds: float = 120.0
    ready_marker: Path | None = None


@dataclass(frozen=True, slots=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True, slots=True)
class IsolationAttestation:
    provider_id: str
    process_tree_contained: bool
    network_denied_by_os: bool
    filesystem_confined_by_os: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MxcIsolationConfig:
    """Exact Microsoft MXC process-container policy inputs.

    The executor is externally supplied and must match a release-reviewed hash.
    Runtime, worker, and bundle roots are read-only; the staging root is the
    only writable grant. DACL fallback is prohibited.
    """

    executor: Path
    executor_sha256: str
    staging_root: Path
    readonly_roots: tuple[Path, ...]
    attestation_timeout_seconds: float = 8.0


class IsolationProvider(Protocol):
    """Future reviewed AppContainer/mxc-style launch boundary."""

    provider_id: str

    def attest(self) -> IsolationAttestation: ...

    def run(
        self,
        command: list[str],
        request: bytes,
        env: dict[str, str],
        token: CancellationToken,
        timeout: float,
        stdout_limit: int,
        stderr_limit: int,
        output_path: Path,
        output_limit: int,
    ) -> ProcessResult: ...


def _is_unc(path: Path | str) -> bool:
    value = str(path)
    return value.startswith("\\\\") or value.startswith("//")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _windows_system32() -> Path:
    """Resolve System32 through the Windows API, not caller-controlled env."""

    if os.name != "nt":
        raise ValidationError("Windows system directory is unavailable")
    import ctypes

    buffer = ctypes.create_unicode_buffer(32_768)
    length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
    if not 0 < length < len(buffer):
        raise ValidationError("Windows system directory identity is unavailable")
    path = Path(buffer.value)
    if _is_unc(path) or path.is_symlink() or (
        hasattr(os.path, "isjunction") and os.path.isjunction(path)
    ):
        raise ValidationError("Windows system directory identity is invalid")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValidationError("Windows system directory is missing") from exc
    if _is_unc(resolved) or not resolved.is_dir():
        raise ValidationError("Windows system directory identity is invalid")
    return resolved


def _resolved_local_nonreparse(path: Path, *, label: str) -> Path:
    """Reject UNC resolution and every link/reparse ancestor."""

    if _is_unc(path):
        raise ValidationError(f"{label} cannot use a UNC path")
    absolute = Path(os.path.abspath(path))
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"{label} is missing") from exc
    if _is_unc(resolved) or os.path.normcase(str(resolved)) != os.path.normcase(str(absolute)):
        raise ValidationError(f"{label} has a redirected identity")
    for ancestor in (absolute, *absolute.parents):
        try:
            info = ancestor.lstat()
        except OSError as exc:
            raise ValidationError(f"{label} ancestor is unreadable") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        if (
            ancestor.is_symlink()
            or (hasattr(os.path, "isjunction") and os.path.isjunction(ancestor))
            or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValidationError(f"{label} cannot traverse a reparse point")
    return resolved


def _hash_regular(path: Path, *, label: str) -> tuple[str, os.stat_result]:
    resolved = _resolved_local_nonreparse(path, label=label)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(resolved, flags)
    except OSError as exc:
        raise ValidationError(f"{label} is unreadable") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValidationError(f"{label} must be a regular file")
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        after = os.fstat(fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValidationError(f"{label} changed during validation")
        return digest.hexdigest(), after
    finally:
        os.close(fd)


def _read_small_regular(path: Path, *, label: str, limit: int = 64 * 1024) -> tuple[bytes, str]:
    """Read and hash one bounded regular file through the same open handle."""

    resolved = _resolved_local_nonreparse(path, label=label)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(resolved, flags)
    except OSError as exc:
        raise ValidationError(f"{label} is unreadable") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > limit:
            raise ValidationError(f"{label} size is invalid")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            block = os.read(fd, min(64 * 1024, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b"".join(chunks)
        after = os.fstat(fd)
        if (
            len(data) != before.st_size
            or len(data) > limit
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise ValidationError(f"{label} changed during validation")
        return data, hashlib.sha256(data).hexdigest()
    finally:
        os.close(fd)


def _runtime_tree_attestation(root: Path) -> dict[str, object]:
    """Hash every file in one sealed runtime tree with no exclusions.

    The digest binds canonical relative paths, byte sizes, and content hashes.
    Unmanifested modules, ``.pth`` files, bytecode, native extensions, or added
    distributions therefore change the result. Links, junctions, other
    reparse points, resolved UNC roots, and non-regular objects fail closed.
    """

    if _is_unc(root):
        raise ValidationError("runtime tree cannot use a UNC path")
    absolute = Path(os.path.abspath(root))
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise ValidationError("runtime tree is missing") from exc
    if _is_unc(resolved) or os.path.normcase(str(resolved)) != os.path.normcase(str(absolute)):
        raise ValidationError("runtime tree has a redirected identity")
    for ancestor in (resolved, *resolved.parents):
        try:
            info = ancestor.lstat()
        except OSError as exc:
            raise ValidationError("runtime tree ancestor is unreadable") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        if (
            ancestor.is_symlink()
            or (hasattr(os.path, "isjunction") and os.path.isjunction(ancestor))
            or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValidationError("runtime tree ancestor cannot be a reparse point")
    if not resolved.is_dir():
        raise ValidationError("runtime tree is not a directory")

    pending = [resolved]
    files: list[tuple[str, Path, int]] = []
    total_bytes = 0
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise ValidationError("runtime tree is unreadable") from exc
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise ValidationError("runtime tree entry is unreadable") from exc
            attributes = getattr(info, "st_file_attributes", 0)
            if entry.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                raise ValidationError("runtime tree entry cannot be a reparse point")
            path = Path(entry.path)
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ValidationError("runtime tree contains a non-regular entry")
            try:
                relative = path.relative_to(resolved).as_posix()
            except ValueError as exc:
                raise ValidationError("runtime tree entry escaped its root") from exc
            if not relative or "\0" in relative:
                raise ValidationError("runtime tree entry name is invalid")
            total_bytes += info.st_size
            files.append((relative, path, info.st_size))
            if len(files) > MAX_RUNTIME_TREE_FILES or total_bytes > MAX_RUNTIME_TREE_BYTES:
                raise ValidationError("runtime tree exceeds release bounds")

    files.sort(key=lambda item: item[0].casefold())
    folded = [item[0].casefold() for item in files]
    if len(folded) != len(set(folded)):
        raise ValidationError("runtime tree has case-colliding paths")
    digest = hashlib.sha256()
    observed_bytes = 0
    for relative, path, expected_size in files:
        file_hash, info = _hash_regular(path, label="runtime tree file")
        if info.st_size != expected_size:
            raise ValidationError("runtime tree changed during validation")
        observed_bytes += info.st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    if observed_bytes != total_bytes:
        raise ValidationError("runtime tree changed during validation")
    return {
        "algorithm": RUNTIME_TREE_ALGORITHM,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "tree_sha256": digest.hexdigest(),
    }


def _installed_runtime_versions(python_executable: Path) -> dict[str,str]:
    environment_root=python_executable.resolve(strict=True).parent.parent
    if os.name=="nt": candidates=(environment_root/"Lib"/"site-packages",)
    else: candidates=tuple((environment_root/"lib").glob("python*/site-packages"))
    site_roots=[path.resolve(strict=True) for path in candidates if path.is_dir()]
    if len(site_roots)!=1: raise ValidationError("isolated runtime site-packages root is ambiguous")
    site=site_roots[0]; versions={}
    for metadata in site.glob("*.dist-info/METADATA"):
        if metadata.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(metadata)):
            raise ValidationError("runtime package metadata cannot be a link")
        try:
            raw=metadata.read_text(encoding="utf-8",errors="strict")
        except (OSError,UnicodeDecodeError):
            continue
        name=version=None
        for line in raw.splitlines():
            if name is None and line.startswith("Name: "): name=line[6:].strip().lower().replace("_","-")
            elif version is None and line.startswith("Version: "): version=line[9:].strip()
            if name is not None and version is not None: break
        if name in EXPECTED_RUNTIME_PACKAGES:
            if name in versions: raise ValidationError("duplicate runtime package metadata is present")
            versions[name]=version
    return versions


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                process.kill()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired as exc:
            raise BackendUnavailableError("Kokoro process tree did not terminate") from exc


def _bounded_process(
    command: list[str],
    request: bytes,
    env: dict[str, str],
    token: CancellationToken,
    timeout: float,
    stdout_limit: int,
    stderr_limit: int,
    output_path: Path,
    output_limit: int,
) -> ProcessResult:
    popen_options: dict[str, object] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "env": env,
        "close_fds": True,
    }
    if os.name == "nt":
        popen_options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    else:
        popen_options["start_new_session"] = True
    process = subprocess.Popen(command, **popen_options)
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    stdout, stderr = bytearray(), bytearray()
    overflow = threading.Event()

    def read(pipe, target: bytearray, limit: int) -> None:
        for chunk in iter(lambda: pipe.read(4096), b""):
            remaining = max(0, limit - len(target))
            if len(chunk) > remaining:
                overflow.set()
            if remaining:
                target.extend(chunk[:remaining])

    threads = [
        threading.Thread(target=read, args=(process.stdout, stdout, stdout_limit), daemon=True),
        threading.Thread(target=read, args=(process.stderr, stderr, stderr_limit), daemon=True),
    ]
    for thread in threads:
        thread.start()
    def close_streams() -> None:
        for thread in threads:
            thread.join(timeout=1)
        process.stdout.close(); process.stderr.close()
    try:
        process.stdin.write(request)
        process.stdin.close()
    except (BrokenPipeError, OSError):
        _terminate_tree(process)
        close_streams()
        raise BackendUnavailableError("Kokoro worker closed its input unexpectedly")
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        try:
            output_too_large = output_path.exists() and output_path.stat().st_size > output_limit
        except OSError:
            output_too_large = True
        if token.cancelled or time.monotonic() >= deadline or overflow.is_set() or output_too_large:
            _terminate_tree(process)
            close_streams()
            output_path.unlink(missing_ok=True)
            if token.cancelled:
                raise CancelledError("Kokoro process cancelled")
            raise BackendUnavailableError("Kokoro process exceeded a bounded execution limit")
        time.sleep(0.02)
    close_streams()
    if any(thread.is_alive() for thread in threads):
        raise BackendUnavailableError("Kokoro protocol streams did not close")
    try:
        output_too_large = output_path.exists() and output_path.stat().st_size > output_limit
    except OSError:
        output_too_large = True
    if overflow.is_set() or output_too_large:
        output_path.unlink(missing_ok=True)
        raise BackendUnavailableError("Kokoro process exceeded a bounded execution limit")
    token.raise_if_cancelled()
    return ProcessResult(process.returncode, bytes(stdout), bytes(stderr))


ProcessRunner = Callable[
    [list[str], bytes, dict[str, str], CancellationToken, float, int, int, Path, int],
    ProcessResult,
]


class MxcIsolationProvider:
    """Pinned Microsoft MXC BaseContainer provider with a live launch canary.

    Readiness is intentionally stricter than ``wxc-exec --probe`` because a
    host can expose the API while the required Windows velocity keys remain
    disabled. The provider therefore requires both the exact probe result and
    a real, zero-output process-container launch under the same deny-network,
    explicit-filesystem policy used for synthesis.
    """

    provider_id = MXC_PROVIDER_ID

    def __init__(self, config: MxcIsolationConfig, runner: ProcessRunner = _bounded_process):
        self.config = config
        self._runner = runner

    def _outer_environment(self) -> dict[str, str]:
        """Minimal fixed environment for the absolute, hash-pinned MXC tool."""

        system32 = _windows_system32()
        windows_root = str(system32.parent)
        staging = _resolved_local_nonreparse(
            self.config.staging_root, label="MXC staging root"
        )
        return {
            "SYSTEMROOT": windows_root,
            "WINDIR": windows_root,
            "PATH": str(system32),
            "TEMP": str(staging),
            "TMP": str(staging),
        }

    def _resolved_roots(self) -> tuple[Path, tuple[Path, ...]]:
        config = self.config
        if os.name != "nt":
            raise ValidationError("MXC process-container isolation requires Windows")
        if (
            not isinstance(config.executor_sha256, str)
            or len(config.executor_sha256) != 64
            or config.executor_sha256 not in REVIEWED_MXC_EXECUTABLE_SHA256
        ):
            raise ValidationError("MXC executor hash is not release reviewed")
        actual_hash, info = _hash_regular(config.executor, label="MXC executor")
        if (
            actual_hash != config.executor_sha256
            or config.executor.suffix.lower() != ".exe"
            or info.st_size <= 0
        ):
            raise ValidationError("MXC executor identity is invalid")
        try:
            with config.executor.open("rb") as handle:
                if handle.read(2) != b"MZ":
                    raise ValidationError("MXC executor identity is invalid")
        except OSError as exc:
            raise ValidationError("MXC executor is unreadable") from exc

        try:
            staging = _resolved_local_nonreparse(
                config.staging_root, label="MXC staging root"
            )
            if not staging.is_dir():
                raise ValidationError("MXC staging root is invalid")
        except OSError as exc:
            raise ValidationError("MXC staging root is missing") from exc

        supplied = config.readonly_roots
        if not isinstance(supplied, tuple) or not 1 <= len(supplied) <= 16:
            raise ValidationError("MXC read-only root set is invalid")
        system_root = _windows_system32()
        roots: list[Path] = []
        for root in (*supplied, system_root):
            try:
                resolved = _resolved_local_nonreparse(root, label="MXC read-only root")
            except (OSError, ValidationError) as exc:
                raise ValidationError("MXC read-only root is missing") from exc
            if not resolved.is_dir():
                raise ValidationError("MXC read-only root is invalid")
            if resolved not in roots:
                roots.append(resolved)
        for root in roots:
            try:
                staging.relative_to(root)
            except ValueError:
                pass
            else:
                raise ValidationError("MXC writable staging cannot overlap a read-only grant")
            try:
                root.relative_to(staging)
            except ValueError:
                pass
            else:
                raise ValidationError("MXC read-only grant cannot be beneath writable staging")
        return staging, tuple(roots)

    @staticmethod
    def _contained(path: Path, roots: tuple[Path, ...], *, label: str) -> Path:
        try:
            resolved = _resolved_local_nonreparse(path, label=label)
        except (OSError, ValidationError) as exc:
            raise ValidationError(f"{label} is missing") from exc
        if not any(_is_relative_to(resolved, root) for root in roots):
            raise ValidationError(f"{label} is outside the MXC read-only grants")
        return resolved

    @staticmethod
    def _policy(
        *,
        command: list[str],
        env: dict[str, str],
        staging: Path,
        readonly_roots: tuple[Path, ...],
        cwd: Path,
        timeout: float,
    ) -> dict[str, object]:
        if not command or any(not isinstance(item, str) or not item or "\0" in item for item in command):
            raise ValidationError("MXC child command is invalid")
        if len(command) > 32:
            raise ValidationError("MXC child command has too many arguments")
        if len(env) > 32:
            raise ValidationError("MXC child environment is too large")
        environment: list[str] = []
        for key, value in sorted(env.items()):
            if (
                not isinstance(key, str)
                or not isinstance(value, str)
                or not key
                or "=" in key
                or "\0" in key
                or "\0" in value
                or len(key) > 128
                or len(value) > 4096
            ):
                raise ValidationError("MXC child environment is invalid")
            environment.append(f"{key}={value}")
        milliseconds = min(600_000, max(1_000, math.ceil(timeout * 1000)))
        return {
            "version": "0.6.0-alpha",
            "containment": "processcontainer",
            "lifecycle": {"destroyOnExit": True, "preservePolicy": False},
            "process": {
                "commandLine": subprocess.list2cmdline(command),
                "cwd": str(cwd),
                "env": environment,
                "timeout": milliseconds,
            },
            "filesystem": {
                "readwritePaths": [str(staging)],
                "readonlyPaths": [str(root) for root in readonly_roots],
                "deniedPaths": [],
            },
            "fallback": {"allowDaclMutation": False},
            "network": {
                "defaultPolicy": "block",
                "enforcementMode": "capabilities",
                "allowedHosts": [],
                "blockedHosts": [],
                "allowLocalNetwork": False,
            },
            "ui": {"disable": True, "clipboard": "none", "injection": False},
            "processContainer": {
                "leastPrivilege": True,
                "capabilities": [],
                "ui": {
                    "isolation": "container",
                    "desktopSystemControl": False,
                    "systemSettings": "none",
                    "ime": False,
                },
            },
        }

    @staticmethod
    def _wrapped_command(executor: Path, policy: dict[str, object]) -> list[str]:
        encoded = json.dumps(
            policy, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        if len(encoded) > MAX_PROTOCOL_BYTES:
            raise ValidationError("MXC policy exceeds the protocol bound")
        return [
            str(executor),
            "--config-base64",
            base64.b64encode(encoded).decode("ascii"),
        ]

    def _control_run(
        self,
        command: list[str],
        *,
        request: bytes = b"",
        timeout: float,
        output_path: Path,
        output_limit: int = 1024,
    ) -> ProcessResult:
        return self._runner(
            command,
            request,
            self._outer_environment(),
            CancellationToken(threading.Event()),
            timeout,
            MAX_PROTOCOL_BYTES,
            MAX_STDERR_BYTES,
            output_path,
            output_limit,
        )

    def attest(self) -> IsolationAttestation:
        try:
            staging, roots = self._resolved_roots()
            timeout = self.config.attestation_timeout_seconds
            if (
                not isinstance(timeout, (int, float))
                or isinstance(timeout, bool)
                or not math.isfinite(float(timeout))
                or not 1 <= float(timeout) <= 30
            ):
                raise ValidationError("MXC attestation timeout is invalid")
            sentinel = staging / f".mxc-attestation-{secrets.token_hex(12)}.partial"
            probe = self._control_run(
                [str(self.config.executor), "--probe"],
                timeout=float(timeout),
                output_path=sentinel,
            )
            if probe.returncode != 0 or probe.stderr or sentinel.exists():
                raise BackendUnavailableError("MXC capability probe failed")
            probe_data = _strict_json(probe.stdout)
            if set(probe_data) != {"tier", "needsDaclAugmentation", "warnings", "probes"}:
                raise BackendUnavailableError("MXC capability probe schema is invalid")
            details = probe_data.get("probes")
            if (
                probe_data.get("tier") != "base-container"
                or probe_data.get("needsDaclAugmentation") is not False
                or probe_data.get("warnings") != []
                or not isinstance(details, dict)
                or details.get("baseContainerApiPresent") is not True
            ):
                raise BackendUnavailableError("MXC BaseContainer capability is unavailable")

            cmd = self._contained(
                _windows_system32() / "cmd.exe",
                roots,
                label="MXC canary executable",
            )
            policy = self._policy(
                command=[str(cmd), "/d", "/c", "exit", "0"],
                env={
                    "SYSTEMROOT": str(_windows_system32().parent),
                    "WINDIR": str(_windows_system32().parent),
                },
                staging=staging,
                readonly_roots=roots,
                cwd=cmd.parent,
                timeout=float(timeout),
            )
            canary = self._control_run(
                self._wrapped_command(self.config.executor, policy),
                timeout=float(timeout),
                output_path=sentinel,
            )
            if canary.returncode != 0 or canary.stdout or canary.stderr or sentinel.exists():
                raise BackendUnavailableError("MXC BaseContainer launch canary failed")
        except (BackendUnavailableError, CancelledError, OSError, ValidationError):
            return IsolationAttestation(
                self.provider_id, False, False, False,
                "pinned MXC BaseContainer probe or launch canary did not pass",
            )
        # A successful no-op launch is necessary but not sufficient. It does
        # not itself observe denied loopback/outbound access, a denied write
        # outside staging, or descendant cleanup. Keep every security claim
        # false until those hostile canaries exist and pass on the target host.
        return IsolationAttestation(
            self.provider_id,
            False,
            False,
            False,
            "MXC launch canary passed, but hostile isolation canaries are not implemented",
        )

    def run(
        self,
        command: list[str],
        request: bytes,
        env: dict[str, str],
        token: CancellationToken,
        timeout: float,
        stdout_limit: int,
        stderr_limit: int,
        output_path: Path,
        output_limit: int,
    ) -> ProcessResult:
        attestation = self.attest()
        if not (
            attestation.process_tree_contained
            and attestation.network_denied_by_os
            and attestation.filesystem_confined_by_os
        ):
            raise BackendUnavailableError("MXC isolation is not currently attested")
        staging, roots = self._resolved_roots()
        if (
            _is_unc(output_path)
            or output_path.exists()
            or output_path.suffix != ".partial"
            or output_path.resolve(strict=False).parent != staging
        ):
            raise ValidationError("MXC assigned output path is invalid")
        python = self._contained(Path(command[0]), roots, label="MXC child interpreter")
        if len(command) < 4 or command[1:3] != ["-I", "-S"]:
            raise ValidationError("MXC Kokoro child command shape is invalid")
        worker = self._contained(Path(command[3]), roots, label="MXC Kokoro worker")
        checked_command = [str(python), "-I", "-S", str(worker), *command[4:]]
        runtime_root = python.parent.parent
        expected_site_packages = runtime_root / "Lib" / "site-packages"
        for flag, root_kind in (
            ("--bundle-root", "readonly"),
            ("--staging-root", "writable"),
            ("--runtime-root", "runtime"),
            ("--runtime-site-packages", "site-packages"),
            ("--base-runtime-root", "base-runtime"),
        ):
            if checked_command.count(flag) != 1:
                raise ValidationError("MXC Kokoro child path arguments are incomplete")
            index = checked_command.index(flag)
            if index + 1 >= len(checked_command):
                raise ValidationError("MXC Kokoro child path argument is invalid")
            value = Path(checked_command[index + 1])
            if root_kind == "readonly":
                self._contained(value, roots, label="MXC model bundle")
            elif root_kind == "writable" and value.resolve(strict=True) != staging:
                raise ValidationError("MXC child staging root does not match its writable grant")
            elif root_kind == "runtime" and value.resolve(strict=True) != runtime_root:
                raise ValidationError("MXC child runtime root is invalid")
            elif (
                root_kind == "site-packages"
                and value.resolve(strict=True) != expected_site_packages.resolve(strict=True)
            ):
                raise ValidationError("MXC child site-packages root is invalid")
            elif root_kind == "base-runtime":
                base = self._contained(value, roots, label="MXC base Python runtime")
                if base == runtime_root or base not in roots:
                    raise ValidationError("MXC base Python runtime root is invalid")
        policy = self._policy(
            command=checked_command,
            env=env,
            staging=staging,
            readonly_roots=roots,
            cwd=worker.parent,
            timeout=timeout,
        )
        return self._runner(
            self._wrapped_command(self.config.executor, policy),
            request,
            self._outer_environment(),
            token,
            timeout,
            stdout_limit,
            stderr_limit,
            output_path,
            output_limit,
        )


def _release_provider_matches(
    provider: IsolationProvider | None,
    backend_config: KokoroConfig,
    bundle_root: Path,
) -> bool:
    """Require the exact concrete provider, production runner, and minimum roots.

    This is intentionally not duck typing. An object or subclass that merely
    repeats a reviewed provider ID cannot enter the release path.
    """

    if type(provider) is not MxcIsolationProvider:
        return False
    assert isinstance(provider, MxcIsolationProvider)
    if (
        provider.provider_id not in REVIEWED_ISOLATION_PROVIDER_IDS
        or provider._runner is not _bounded_process
    ):
        return False
    try:
        runtime_root = backend_config.python_executable.resolve(strict=True).parent.parent
        if backend_config.base_runtime_root is None:
            return False
        base_runtime_root = _resolved_local_nonreparse(
            backend_config.base_runtime_root, label="base Python runtime root"
        )
        worker_root = backend_config.worker_script.resolve(strict=True).parent
        sealed_bundle = bundle_root.resolve(strict=True)
        staging = backend_config.staging_root.resolve(strict=True)
        configured_staging, configured_roots = provider._resolved_roots()
        system_root = _windows_system32()
    except (OSError, ValidationError):
        return False
    expected_roots = {
        runtime_root, base_runtime_root, worker_root, sealed_bundle, system_root,
    }
    return configured_staging == staging and set(configured_roots) == expected_roots


def _strict_json(data: bytes) -> dict[str, object]:
    def strict_object(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError("duplicate JSON key")
            result[key]=value
        return result
    try:
        decoded = data.decode("utf-8", errors="strict")
        value = json.loads(decoded,object_pairs_hook=strict_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise BackendUnavailableError("Kokoro worker returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise BackendUnavailableError("Kokoro worker returned an invalid result object")
    return value


def _parse_success_response(
    data: bytes, *, request: SynthesisRequest, output_path: Path
) -> BackendResult:
    response = _strict_json(data)
    required = {
        "schema",
        "ok",
        "format",
        "sample_rate_hz",
        "duration_seconds",
        "output_bytes",
        "backend_name",
        "backend_version",
        "model_source",
        "model_revision",
        "voice_id",
        "license_id",
        "offline",
        "provenance_scope",
    }
    if set(response) != required or response.get("schema") != "kira.kokoro.result.v2":
        raise BackendUnavailableError("Kokoro worker result schema is invalid")
    if response.get("ok") is not True or response.get("offline") is not True:
        raise BackendUnavailableError("Kokoro worker did not attest offline success")
    exact = {
        "format": "wav",
        "sample_rate_hz": 24_000,
        "backend_name": "kokoro-direct-subprocess",
        "backend_version": "2.0",
        "model_source": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "voice_id": request.voice_id,
        "license_id": "Apache-2.0",
        "provenance_scope": PROVENANCE_SCOPE,
    }
    if any(response.get(key) != expected for key, expected in exact.items()):
        raise BackendUnavailableError("Kokoro worker provenance attestation is invalid")
    duration, output_bytes = response.get("duration_seconds"), response.get("output_bytes")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(float(duration))
        or not 0 < float(duration) <= 600
        or not isinstance(output_bytes, int)
        or isinstance(output_bytes, bool)
        or not 44 < output_bytes <= MAX_OUTPUT_BYTES
    ):
        raise BackendUnavailableError("Kokoro worker media attestation is invalid")
    fd = -1
    try:
        resolved_output = _resolved_local_nonreparse(
            output_path, label="Kokoro worker output"
        )
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(resolved_output, flags)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("non-regular output")
        actual_size = before.st_size
        with os.fdopen(fd, "rb", closefd=False) as raw:
            with wave.open(raw, "rb") as audio:
                channels = audio.getnchannels()
                sample_width = audio.getsampwidth()
                sample_rate = audio.getframerate()
                frames = audio.getnframes()
                compression = audio.getcomptype()
        after = os.fstat(fd)
    except (OSError, ValidationError, EOFError, wave.Error) as exc:
        raise BackendUnavailableError("Kokoro worker output is missing") from exc
    finally:
        if fd >= 0:
            os.close(fd)
    if actual_size != output_bytes:
        raise BackendUnavailableError("Kokoro worker output-size attestation is invalid")
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or channels != 1
        or sample_width != 2
        or sample_rate != 24_000
        or compression != "NONE"
        or not 0 < frames <= 24_000 * 600
    ):
        raise BackendUnavailableError("Kokoro worker WAV contract is invalid")
    actual_duration = frames / sample_rate
    if abs(actual_duration - float(duration)) > (1 / sample_rate + 0.000001):
        raise BackendUnavailableError("Kokoro worker duration attestation is invalid")
    return BackendResult(
        "wav",
        24_000,
        float(duration),
        "kokoro-direct-subprocess",
        "2.0",
        False,
        MODEL_REPO,
        MODEL_REVISION,
        request.voice_id,
        "Apache-2.0",
        True,
        PROVENANCE_SCOPE,
    )


class KokoroSubprocessBackend:
    def __init__(self, config: KokoroConfig, isolation_provider: IsolationProvider | None = None):
        self.config = config
        self._isolation_provider = isolation_provider

    def _readiness(self) -> tuple[bool, str | None]:
        config = self.config
        if config.device not in {"cpu", "cuda"}:
            return False, "invalid device"
        if (
            not isinstance(config.timeout_seconds, (int, float))
            or isinstance(config.timeout_seconds, bool)
            or not math.isfinite(float(config.timeout_seconds))
            or not 1 <= config.timeout_seconds <= 600
        ):
            return False, "invalid process timeout"
        if any(
            _is_unc(path)
            for path in (
                config.python_executable,
                config.worker_script,
                config.runtime_lock,
                config.runtime_bridge,
                config.cache_root,
                config.staging_root,
            )
        ):
            return False, "UNC runtime paths are not supported"
        try:
            python_hash, python_info = _hash_regular(config.python_executable, label="isolated Python")
            worker_hash, _ = _hash_regular(config.worker_script, label="Kokoro worker")
            lock_bytes, lock_hash = _read_small_regular(
                config.runtime_lock, label="runtime lock"
            )
            bridge_bytes, bridge_hash = _read_small_regular(
                config.runtime_bridge, label="starter runtime evidence bridge"
            )
        except ValidationError as exc:
            return False, str(exc)
        if os.name == "nt":
            try:
                with config.python_executable.open("rb") as handle:
                    executable_magic = handle.read(2)
            except OSError:
                return False, "isolated Python is unreadable"
            if config.python_executable.suffix.lower() != ".exe" or executable_magic != b"MZ":
                return False, "isolated Python executable identity is invalid"
        elif not os.access(config.python_executable, os.X_OK):
            return False, "isolated Python is not executable"
        if (
            not isinstance(config.python_sha256, str)
            or len(config.python_sha256) != 64
            or config.python_sha256 not in REVIEWED_PYTHON_EXECUTABLE_SHA256
            or python_hash != config.python_sha256
            or python_info.st_size <= 0
        ):
            return False, "isolated Python hash is not release reviewed"
        if worker_hash != EXPECTED_WORKER_SHA256:
            return False, "Kokoro worker source hash does not match this release"
        if lock_hash != EXPECTED_RUNTIME_LOCK_SHA256:
            return False, "runtime lock hash does not match this release"
        if bridge_hash != EXPECTED_RUNTIME_BRIDGE_SHA256:
            return False, "starter runtime evidence bridge does not match this release"
        try:
            bridge = _strict_json(bridge_bytes)
        except BackendUnavailableError:
            return False, "starter runtime evidence bridge is invalid"
        if (
            bridge.get("schema") != "kira.kokoro.starter-runtime-bridge.v1"
            or bridge.get("status") != "EXACT_TWO_VOICE_GENERIC_BOOTSTRAP_BINDING"
            or bridge.get("model_repo") != MODEL_REPO
            or bridge.get("runtime_model_revision") != MODEL_REVISION
            or bridge.get("route") != "KModel+misaki.espeak.EspeakG2P"
            or bridge.get("license_id") != "Apache-2.0"
            or bridge.get("provenance_scope") != PROVENANCE_SCOPE
            or bridge.get("voice_ids") != sorted(ALLOWLIST)
            or bridge.get("bundle_files") != MODEL_FILES
            or bridge.get("evidence_files") != EXPECTED_EVIDENCE_FILES
            or bridge.get("audition_evidence_grants_runtime_access") is not True
            or bridge.get("activation_performed") is not False
        ):
            return False, "starter runtime evidence bridge contents are invalid"
        try:
            evidence_root = _EVIDENCE_ROOT.resolve(strict=True)
            if (
                _EVIDENCE_ROOT.is_symlink()
                or (hasattr(os.path, "isjunction") and os.path.isjunction(_EVIDENCE_ROOT))
                or not evidence_root.is_dir()
            ):
                raise ValidationError("release evidence root identity is invalid")
            for relative, expected_hash in EXPECTED_EVIDENCE_FILES.items():
                evidence_path = _EVIDENCE_ROOT.joinpath(*relative.split("/"))
                evidence_path.resolve(strict=True).relative_to(evidence_root)
                actual_hash, _ = _hash_regular(
                    evidence_path, label=f"release evidence file {relative}"
                )
                if actual_hash != expected_hash:
                    raise ValidationError(f"release evidence file {relative} hash is invalid")
        except (OSError, ValueError, ValidationError):
            return False, "starter runtime evidence set is invalid"
        try:
            runtime_lock = _strict_json(lock_bytes)
        except BackendUnavailableError:
            return False, "runtime lock is unreadable"
        if (
            runtime_lock.get("schema") != "kira.kokoro.runtime-lock.v1"
            or runtime_lock.get("python") != ">=3.10,<3.14"
            or runtime_lock.get("route") != "KModel+misaki.espeak.EspeakG2P"
            or runtime_lock.get("model_repo") != MODEL_REPO
            or runtime_lock.get("model_revision") != MODEL_REVISION
            or runtime_lock.get("voice_ids") != sorted(ALLOWLIST)
            or runtime_lock.get("bundle_files") != MODEL_FILES
            or runtime_lock.get("runtime_bridge_sha256") != EXPECTED_RUNTIME_BRIDGE_SHA256
            or runtime_lock.get("reviewed_python_executable_sha256")
            != sorted(REVIEWED_PYTHON_EXECUTABLE_SHA256)
            or runtime_lock.get("runtime_tree") != EXPECTED_RUNTIME_TREE
            or runtime_lock.get("base_runtime_tree") != EXPECTED_BASE_RUNTIME_TREE
            or runtime_lock.get("packages") != EXPECTED_RUNTIME_PACKAGES
            or runtime_lock.get("isolation") != {
                "provider_id": MXC_PROVIDER_ID,
                "deny_network": True,
                "allow_dacl_fallback": False,
                "reviewed_executor_sha256": sorted(REVIEWED_MXC_EXECUTABLE_SHA256),
                "live_launch_canary_required": True,
            }
        ):
            return False, "runtime lock contents are not the approved pin set"
        try: installed_versions=_installed_runtime_versions(config.python_executable)
        except (OSError,ValidationError): return False,"isolated runtime package metadata is invalid"
        if installed_versions!=EXPECTED_RUNTIME_PACKAGES:
            return False,"isolated runtime packages do not match the approved lock"
        if config.base_runtime_root is None or _is_unc(config.base_runtime_root):
            return False, "base Python runtime root is not configured locally"
        try:
            runtime_tree = _runtime_tree_attestation(
                config.python_executable.resolve(strict=True).parent.parent
            )
        except (OSError, ValidationError):
            return False, "isolated runtime tree identity is invalid"
        if runtime_tree != EXPECTED_RUNTIME_TREE:
            return False, "isolated runtime tree does not match the reviewed release"
        try:
            base_runtime_tree = _runtime_tree_attestation(config.base_runtime_root)
        except (OSError, ValidationError):
            return False, "base Python runtime tree identity is invalid"
        if base_runtime_tree != EXPECTED_BASE_RUNTIME_TREE:
            return False, "base Python runtime tree does not match the reviewed release"
        try:
            cache_root = _resolved_local_nonreparse(config.cache_root, label="cache root")
            staging_root = _resolved_local_nonreparse(config.staging_root, label="staging root")
        except (OSError, ValidationError):
            return False, "configured cache or staging root is missing"
        for root, label in ((cache_root, "cache"), (staging_root, "staging")):
            if root.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(root)) or not root.is_dir():
                return False, f"configured {label} root identity is invalid"
        bundle_root = cache_root / "sealed_bundle"
        try:
            resolved_bundle = _resolved_local_nonreparse(
                bundle_root, label="sealed model bundle"
            )
            resolved_bundle.relative_to(cache_root)
        except (OSError, ValueError, ValidationError):
            return False, "sealed model bundle is missing"
        if bundle_root.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(bundle_root)):
            return False, "sealed model bundle cannot be a link or junction"
        for relative, expected_hash in MODEL_FILES.items():
            model_path = resolved_bundle.joinpath(*relative.split("/"))
            try:
                model_path.resolve(strict=True).relative_to(resolved_bundle)
                actual_hash, _ = _hash_regular(model_path, label=f"model bundle file {relative}")
            except (OSError, ValueError, ValidationError):
                return False, f"model bundle file {relative} is invalid"
            if actual_hash != expected_hash:
                return False, f"model bundle file {relative} hash is invalid"
        marker = config.ready_marker or cache_root / "kira_kokoro_ready.json"
        try:
            marker.resolve(strict=True).relative_to(cache_root)
            marker_bytes, _ = _read_small_regular(marker, label="ready marker")
            data = _strict_json(marker_bytes)
        except (OSError, ValueError, ValidationError, BackendUnavailableError):
            return False, "validated local model cache marker is missing"
        expected_marker = {
            "schema": "kira.kokoro.ready.v3",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "provenance_scope":PROVENANCE_SCOPE,
            "audition_evidence_revision":AUDITION_EVIDENCE_REVISION,
            "audition_evidence_grants_runtime_access":True,
            "route": "KModel+misaki.espeak.EspeakG2P",
            "voices": sorted(ALLOWLIST),
            "python_sha256": python_hash,
            "worker_sha256": EXPECTED_WORKER_SHA256,
            "runtime_lock_sha256": EXPECTED_RUNTIME_LOCK_SHA256,
            "runtime_bridge_sha256": EXPECTED_RUNTIME_BRIDGE_SHA256,
            "runtime_packages": EXPECTED_RUNTIME_PACKAGES,
            "runtime_tree": EXPECTED_RUNTIME_TREE,
            "base_runtime_tree": EXPECTED_BASE_RUNTIME_TREE,
            "bundle_files": MODEL_FILES,
        }
        if data != expected_marker:
            return False, "validated cache marker does not match all pinned identities"
        provider = self._isolation_provider
        if not _release_provider_matches(provider, config, resolved_bundle):
            return False, "no OS isolation provider is release reviewed for this runtime"
        assert isinstance(provider, MxcIsolationProvider)
        try:
            attestation = provider.attest()
        except Exception:
            return False, "OS isolation provider attestation failed"
        if (
            provider.provider_id not in REVIEWED_ISOLATION_PROVIDER_IDS
            or attestation.provider_id != provider.provider_id
            or not attestation.process_tree_contained
            or not attestation.network_denied_by_os
            or not attestation.filesystem_confined_by_os
        ):
            return False, attestation.reason or "OS isolation provider is not reviewed and fully attested"
        return True, None

    def capabilities(self) -> BackendCapabilities:
        ready, reason = self._readiness()
        return BackendCapabilities(
            "kokoro-direct-subprocess",
            "2.0",
            ready,
            ("wav",),
            ("en-US",),
            False,
            False,
            False,
            offline=ready,
            network_access="none" if ready else "not_os_enforced",
            telemetry="none" if ready else "disabled_by_environment_only",
            model_source=MODEL_REPO,
            model_revision=MODEL_REVISION,
            license_id="Apache-2.0",
            voice_ids=tuple(sorted(ALLOWLIST)),
            provenance_scope=PROVENANCE_SCOPE,
            audition_evidence_revision=AUDITION_EVIDENCE_REVISION,
            audition_evidence_grants_runtime_access=True,
            unavailable_reason=reason,
        )

    def synthesize(
        self,
        request: SynthesisRequest,
        voice: VoiceProfile,
        output_path: Path,
        cancellation: CancellationToken,
    ) -> BackendResult:
        del voice
        caps = self.capabilities()
        if not caps.ready:
            raise BackendUnavailableError(caps.unavailable_reason or "Kokoro unavailable")
        if request.voice_id not in ALLOWLIST or request.language != "en-US":
            raise ValidationError("Kokoro voice or language is not allowed")
        if (
            not isinstance(request.speed, (int, float))
            or isinstance(request.speed, bool)
            or not math.isfinite(float(request.speed))
            or not 0.5 <= request.speed <= 2.0
        ):
            raise ValidationError("Kokoro speed is outside bounds")
        if _is_unc(output_path):
            raise ValidationError("Kokoro output cannot use a UNC path")
        root = self.config.staging_root.resolve(strict=True)
        candidate = output_path.resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValidationError("assigned Kokoro output escapes staging") from exc
        if candidate.parent != root or candidate.exists() or candidate.suffix != ".partial":
            raise ValidationError("assigned Kokoro staging output is invalid")
        payload = json.dumps(
            {
                "schema": "kira.kokoro.request.v2",
                "text": request.text,
                "voice_id": request.voice_id,
                "speed": request.speed,
                "output_path": str(candidate),
            },
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(payload) > MAX_PROTOCOL_BYTES:
            raise ValidationError("Kokoro request exceeds protocol bound")
        assert self.config.base_runtime_root is not None
        system32 = _windows_system32()
        windows_root = str(system32.parent)
        env = {
                "SYSTEMROOT": windows_root,
                "WINDIR": windows_root,
                "TEMP": str(root),
                "TMP": str(root),
                "PATH": os.pathsep.join(
                    (str(self.config.python_executable.resolve(strict=True).parent),
                     str(system32))
                ),
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
                "DO_NOT_TRACK": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "CUDA_CACHE_DISABLE": "1",
        }
        command = [
            str(self.config.python_executable),
            "-I",
            "-S",
            str(self.config.worker_script),
            "--one-shot",
            "--bundle-root",
            str(self.config.cache_root.resolve(strict=True) / "sealed_bundle"),
            "--staging-root",
            str(root),
            "--runtime-root",
            str(self.config.python_executable.resolve(strict=True).parent.parent),
            "--runtime-site-packages",
            str(
                self.config.python_executable.resolve(strict=True).parent.parent
                / "Lib" / "site-packages"
            ),
            "--base-runtime-root",
            str(
                _resolved_local_nonreparse(
                    self.config.base_runtime_root, label="base Python runtime root"
                )
            ),
            "--device",
            self.config.device,
        ]
        assert self._isolation_provider is not None
        process = self._isolation_provider.run(
            command,
            payload,
            env,
            cancellation,
            min(float(self.config.timeout_seconds), 600.0),
            MAX_PROTOCOL_BYTES,
            MAX_STDERR_BYTES,
            candidate,
            MAX_OUTPUT_BYTES,
        )
        cancellation.raise_if_cancelled()
        if process.returncode != 0:
            raise BackendUnavailableError("Kokoro worker failed")
        return _parse_success_response(process.stdout, request=request, output_path=candidate)
