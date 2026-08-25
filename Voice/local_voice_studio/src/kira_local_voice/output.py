"""Core-owned WAV verification and no-replace publication."""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import stat
import wave
from dataclasses import dataclass
from pathlib import Path

from .errors import ConflictError, ValidationError
from .models import BackendResult
from .paths import contained_path

MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_SECONDS = 600.0
ALLOWED_OUTPUT_RATES = frozenset({24_000})


@dataclass(frozen=True, slots=True)
class ValidatedOutput:
    sha256: str
    bytes: int
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    format: str = "wav"


@dataclass(frozen=True, slots=True)
class PublishedOutput:
    """Identity of the inode/name published by this job."""

    device: int
    inode: int
    bytes: int
    sha256: str


def validate_backend_output(path: Path, staging_root: Path, result: BackendResult) -> ValidatedOutput:
    staging_root = staging_root.resolve()
    candidate = contained_path(staging_root, path.name)
    if candidate != path.resolve(strict=False):
        raise ValidationError("backend output path is not the assigned staging file")
    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        raise ValidationError("backend output cannot be a link or junction")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValidationError("backend did not create a readable assigned output") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValidationError("backend output must be a regular file")
        if info.st_size <= 44 or info.st_size > MAX_OUTPUT_BYTES:
            raise ValidationError("backend output size is outside the allowed range")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            digest = hashlib.sha256()
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
            handle.seek(0)
            try:
                audio = wave.open(handle, "rb")
                channels = audio.getnchannels()
                width = audio.getsampwidth()
                rate = audio.getframerate()
                frames = audio.getnframes()
                compression = audio.getcomptype()
                payload = audio.readframes(frames)
                audio.close()
            except (wave.Error, EOFError) as exc:
                raise ValidationError("backend output is not a readable WAV") from exc
        if compression != "NONE" or channels != 1 or width != 2:
            raise ValidationError("backend output must be mono 16-bit PCM WAV")
        if rate not in ALLOWED_OUTPUT_RATES:
            raise ValidationError("backend output sample rate is unsupported")
        if len(payload) != frames * channels * width:
            raise ValidationError("backend output WAV data is truncated")
        duration = frames / rate if rate else 0.0
        if not 0 < duration <= MAX_OUTPUT_SECONDS:
            raise ValidationError("backend output duration is outside the allowed range")
        if (
            not isinstance(result.duration_seconds, (int, float))
            or isinstance(result.duration_seconds, bool)
            or not math.isfinite(float(result.duration_seconds))
        ):
            raise ValidationError("backend result duration is not finite")
        if result.format != "wav" or result.sample_rate_hz != rate:
            raise ValidationError("backend result metadata disagrees with the WAV")
        if abs(result.duration_seconds - duration) > max(1 / rate, 0.001):
            raise ValidationError("backend result duration disagrees with the WAV")
        return ValidatedOutput(
            sha256=digest.hexdigest(),
            bytes=info.st_size,
            duration_seconds=round(duration, 6),
            sample_rate_hz=rate,
            channels=channels,
            sample_width_bytes=width,
        )
    finally:
        os.close(fd)


def publish_no_replace(
    staging_path: Path, final_path: Path, checked: ValidatedOutput
) -> PublishedOutput:
    """Publish an already-validated file without ever replacing another output."""

    final_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(staging_path, final_path)
    except FileExistsError as exc:
        raise ConflictError(f"output already exists: {final_path.name}") from exc
    try:
        info = final_path.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_size != checked.bytes:
            raise ValidationError("published output identity disagrees with validated staging")
        published = PublishedOutput(info.st_dev, info.st_ino, info.st_size, checked.sha256)
    except Exception:
        # The output name was created by the hard-link operation above and the
        # reservation remains held, so this cleanup cannot target another job.
        final_path.unlink(missing_ok=True)
        raise
    staging_path.unlink()
    return published


def remove_published_if_owned(path: Path, published: PublishedOutput) -> bool:
    """Remove only the exact regular file inode published by this job.

    This is used when receipt persistence or a post-publication cancellation
    fails. The output reservation is still held while this check runs.
    """

    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        return False
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    owned = False
    try:
        fd = os.open(path, flags)
    except OSError:
        return not path.exists()
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or (info.st_dev, info.st_ino, info.st_size)
            != (published.device, published.inode, published.bytes)
        ):
            return False
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        if not hmac.compare_digest(digest.hexdigest(), published.sha256):
            return False
        after = os.fstat(fd)
        current = path.stat(follow_symlinks=False)
        if (
            (after.st_dev, after.st_ino, after.st_size)
            != (published.device, published.inode, published.bytes)
            or (current.st_dev, current.st_ino, current.st_size)
            != (published.device, published.inode, published.bytes)
        ):
            return False
        owned = True
    except OSError:
        return False
    finally:
        os.close(fd)
    if not owned:
        return False
    try:
        current = path.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino, current.st_size) != (
            published.device,
            published.inode,
            published.bytes,
        ):
            return False
        path.unlink()
        return True
    except OSError:
        return False
