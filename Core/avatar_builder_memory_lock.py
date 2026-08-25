"""Cooperative cross-process lock for Avatar Builder resident memory writes."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import os
from pathlib import Path
import re
import time
from typing import Any, Iterator


UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00$"
)


class AvatarBuilderMemoryLockError(RuntimeError):
    """Raised when the shared memory write lock cannot be acquired."""


def lock_path_for(memory_path: Path) -> Path:
    return memory_path.with_name(f".{memory_path.name}.lock")


def is_canonical_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or UTC_TIMESTAMP_RE.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


@contextmanager
def locked_memory_write(memory_path: Path, *, timeout_seconds: float = 10.0) -> Iterator[None]:
    """Serialize cooperating writers without publishing resident memory.

    The one-byte lock file is intentionally persistent so deleting and
    recreating it cannot split two writers across different file identities.
    """

    if timeout_seconds <= 0:
        raise ValueError("memory lock timeout must be positive")
    lock_path = lock_path_for(memory_path)
    handle = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b", buffering=0)
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        if handle is not None:
            handle.close()
        raise AvatarBuilderMemoryLockError(
            "unable to initialize Avatar Builder memory write lock"
        ) from exc
    acquired = False
    deadline = time.monotonic() + timeout_seconds
    try:
        while not acquired:
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise AvatarBuilderMemoryLockError(
                        "timed out acquiring Avatar Builder memory write lock"
                    )
                time.sleep(0.025)
        yield
    finally:
        if acquired:
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


__all__ = [
    "AvatarBuilderMemoryLockError",
    "is_canonical_utc_timestamp",
    "lock_path_for",
    "locked_memory_write",
]
