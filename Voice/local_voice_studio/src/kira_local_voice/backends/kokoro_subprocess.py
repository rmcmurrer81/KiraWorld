"""Fail-closed one-shot adapter for an isolated Kokoro runtime.

The subprocess protocol is implemented, but capabilities remain unavailable
until this product supplies an operating-system-enforced network/filesystem
sandbox. Environment flags alone are not advertised as local-only isolation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import stat
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..errors import BackendUnavailableError, CancelledError, ValidationError
from ..models import BackendResult, SynthesisRequest, VoiceProfile
from .base import BackendCapabilities, CancellationToken

MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "fbba31e67ad83eb66394c926627e99d35abeb087"
AUDITION_EVIDENCE_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
ALLOWLIST = frozenset({"af_heart", "am_fenrir"})
MODEL_FILES = {
    "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
    "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    "voices/af_heart.pt": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
    "voices/am_fenrir.pt": "98e507eca1db08230ae3b6232d59c10aec9630022d19accac4f5d12fcec3c37a",
}
EXPECTED_WORKER_SHA256 = "a1d16d8bd3e325284f3f5ed604fee49d443f918c028ee2d8ef003984dc4fb025"
EXPECTED_RUNTIME_LOCK_SHA256 = "25fe2fec8d1c86369a458956072b7a22b1301246514842afecf5e373b15e09d8"
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
REVIEWED_ISOLATION_PROVIDER_IDS: frozenset[str] = frozenset()
_LOCK_PATH = Path(__file__).resolve().parents[3] / "requirements-kokoro.lock.json"


@dataclass(frozen=True, slots=True)
class KokoroConfig:
    python_executable: Path
    cache_root: Path
    staging_root: Path
    worker_script: Path = Path(__file__).with_name("kokoro_worker.py")
    runtime_lock: Path = _LOCK_PATH
    python_sha256: str | None = None
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


def _hash_regular(path: Path, *, label: str) -> tuple[str, os.stat_result]:
    if _is_unc(path):
        raise ValidationError(f"{label} cannot use a UNC path")
    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        raise ValidationError(f"{label} cannot be a link or junction")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"{label} is missing") from exc
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
        "provenance_scope": "two_voice_runtime_bundle_only",
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
    try:
        if output_path.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(output_path)):
            raise OSError("link output")
        output_info=output_path.stat(follow_symlinks=False)
        if not stat.S_ISREG(output_info.st_mode): raise OSError("non-regular output")
        actual_size = output_info.st_size
    except OSError as exc:
        raise BackendUnavailableError("Kokoro worker output is missing") from exc
    if actual_size != output_bytes:
        raise BackendUnavailableError("Kokoro worker output-size attestation is invalid")
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
        "two_voice_runtime_bundle_only",
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
        if any(_is_unc(path) for path in (config.python_executable, config.worker_script, config.runtime_lock, config.cache_root, config.staging_root)):
            return False, "UNC runtime paths are not supported"
        try:
            python_hash, python_info = _hash_regular(config.python_executable, label="isolated Python")
            worker_hash, _ = _hash_regular(config.worker_script, label="Kokoro worker")
            lock_hash, _ = _hash_regular(config.runtime_lock, label="runtime lock")
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
            or python_hash != config.python_sha256
            or python_info.st_size <= 0
        ):
            return False, "isolated Python hash is not explicitly pinned"
        if worker_hash != EXPECTED_WORKER_SHA256:
            return False, "Kokoro worker source hash does not match this release"
        if lock_hash != EXPECTED_RUNTIME_LOCK_SHA256:
            return False, "runtime lock hash does not match this release"
        try:
            runtime_lock = json.loads(config.runtime_lock.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, "runtime lock is unreadable"
        if (
            not isinstance(runtime_lock, dict)
            or runtime_lock.get("schema") != "kira.kokoro.runtime-lock.v1"
            or runtime_lock.get("python") != ">=3.10,<3.14"
            or runtime_lock.get("route") != "KModel+misaki.espeak.EspeakG2P"
            or runtime_lock.get("packages") != EXPECTED_RUNTIME_PACKAGES
        ):
            return False, "runtime lock contents are not the approved pin set"
        try: installed_versions=_installed_runtime_versions(config.python_executable)
        except (OSError,ValidationError): return False,"isolated runtime package metadata is invalid"
        if installed_versions!=EXPECTED_RUNTIME_PACKAGES:
            return False,"isolated runtime packages do not match the approved lock"
        try:
            for configured,label in ((config.cache_root,"cache"),(config.staging_root,"staging")):
                if configured.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(configured)):
                    return False,f"configured {label} root cannot be a link or junction"
            cache_root = config.cache_root.resolve(strict=True)
            staging_root = config.staging_root.resolve(strict=True)
        except OSError:
            return False, "configured cache or staging root is missing"
        for root, label in ((cache_root, "cache"), (staging_root, "staging")):
            if root.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(root)) or not root.is_dir():
                return False, f"configured {label} root identity is invalid"
        bundle_root = cache_root / "sealed_bundle"
        try:
            resolved_bundle = bundle_root.resolve(strict=True)
            resolved_bundle.relative_to(cache_root)
        except (OSError, ValueError):
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
            marker_hash, _ = _hash_regular(marker, label="ready marker")
            del marker_hash
            data = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError, ValidationError, json.JSONDecodeError):
            return False, "validated local model cache marker is missing"
        expected_marker = {
            "schema": "kira.kokoro.ready.v2",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "provenance_scope":"two_voice_runtime_bundle_only",
            "audition_evidence_revision":AUDITION_EVIDENCE_REVISION,
            "audition_evidence_grants_runtime_access":False,
            "route": "KModel+misaki.espeak.EspeakG2P",
            "voices": sorted(ALLOWLIST),
            "python_sha256": python_hash,
            "worker_sha256": EXPECTED_WORKER_SHA256,
            "runtime_lock_sha256": EXPECTED_RUNTIME_LOCK_SHA256,
            "runtime_packages": EXPECTED_RUNTIME_PACKAGES,
            "bundle_files": MODEL_FILES,
        }
        if data != expected_marker:
            return False, "validated cache marker does not match all pinned identities"
        provider = self._isolation_provider
        if provider is None:
            return False, "OS-enforced network/filesystem isolation provider is not configured"
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
            return False, "OS isolation provider is not reviewed and fully attested"
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
            provenance_scope="two_voice_runtime_bundle_only",
            audition_evidence_revision=AUDITION_EVIDENCE_REVISION,
            audition_evidence_grants_runtime_access=False,
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
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
        }
        env.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
                "DO_NOT_TRACK": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        command = [
            str(self.config.python_executable),
            "-I",
            str(self.config.worker_script),
            "--one-shot",
            "--bundle-root",
            str(self.config.cache_root.resolve(strict=True) / "sealed_bundle"),
            "--staging-root",
            str(root),
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
