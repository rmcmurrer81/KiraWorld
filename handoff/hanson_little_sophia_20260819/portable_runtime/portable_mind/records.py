from __future__ import annotations

import hashlib
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .strict_json import loads_strict


class StorageCorruption(RuntimeError):
    """An append-only record could not be parsed or validated."""


class ConcurrentMutationError(RuntimeError):
    """Another process currently owns the requested mutation lock."""


_LOCK_REGISTRY_GUARD = threading.Lock()
_LOCK_REGISTRY: dict[str, threading.RLock] = {}


def _thread_lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve(strict=False)).casefold()
    with _LOCK_REGISTRY_GUARD:
        return _LOCK_REGISTRY.setdefault(key, threading.RLock())


@contextmanager
def exclusive_file_lock(path: Path, *, blocking: bool = True):
    """Cross-platform advisory lock plus an in-process thread lock.

    The one-byte lock file contains no user content. Production mutations wait
    for the current owner; tests and diagnostics may request a clear fail-fast
    error with ``blocking=False``.
    """

    selected = path.resolve(strict=False)
    selected.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock_for(selected)
    acquired_thread = thread_lock.acquire(blocking=blocking)
    if not acquired_thread:
        raise ConcurrentMutationError(f"mutation lock is already held: {selected.name}")
    handle = None
    locked = False
    try:
        handle = selected.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                msvcrt.locking(handle.fileno(), mode, 1)
            else:
                import fcntl

                flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
                fcntl.flock(handle.fileno(), flags)
            locked = True
        except (BlockingIOError, OSError) as exc:
            raise ConcurrentMutationError(f"mutation lock is already held: {selected.name}") from exc
        yield
    finally:
        if handle is not None:
            if locked:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            handle.close()
        thread_lock.release()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_event_id(*parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


class AppendOnlyJSONL:
    """Small append-only JSONL channel with duplicate-event suppression.

    The channel is intended for a single local process. Each append is flushed and
    fsynced. Replays fail closed on malformed JSON instead of silently discarding it.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._process_lock_path = self.path.with_name(self.path.name + ".lock")

    def _records_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        result: list[dict[str, Any]] = []
        seen: dict[str, str] = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                try:
                    record = loads_strict(raw_line)
                except (json.JSONDecodeError, ValueError) as exc:
                    raise StorageCorruption(
                        f"malformed JSON in {self.path.name} at line {line_number}"
                    ) from exc
                if not isinstance(record, dict) or not isinstance(record.get("event_id"), str):
                    raise StorageCorruption(
                        f"invalid record in {self.path.name} at line {line_number}"
                    )
                event_id = record["event_id"]
                encoded = canonical_json(record)
                if event_id in seen:
                    if seen[event_id] != encoded:
                        raise StorageCorruption(
                            f"conflicting duplicate event_id in {self.path.name} at line {line_number}"
                        )
                    continue
                seen[event_id] = encoded
                result.append(record)
        return result

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock, exclusive_file_lock(self._process_lock_path):
            return self._records_unlocked()

    def find(self, event_id: str) -> dict[str, Any] | None:
        return next((record for record in self.records() if record["event_id"] == event_id), None)

    def append_once(self, record: dict[str, Any]) -> bool:
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("append-only records require a non-empty event_id")
        encoded = canonical_json(record)
        if "\n" in encoded or "\r" in encoded:
            raise ValueError("canonical JSON unexpectedly contains a raw line break")
        with self._lock, exclusive_file_lock(self._process_lock_path):
            if any(existing["event_id"] == event_id for existing in self._records_unlocked()):
                return False
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        return True

    def append_exact_or_verify(self, record: dict[str, Any]) -> bool:
        """Append one record or verify that the existing event is byte-semantic equal.

        This is used when replaying a committed transaction.  A matching event ID
        with different content is corruption, not a successful idempotent replay.
        """

        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("append-only records require a non-empty event_id")
        encoded = canonical_json(record)
        if "\n" in encoded or "\r" in encoded:
            raise ValueError("canonical JSON unexpectedly contains a raw line break")
        with self._lock, exclusive_file_lock(self._process_lock_path):
            existing = next(
                (item for item in self._records_unlocked() if item["event_id"] == event_id),
                None,
            )
            if existing is not None:
                if canonical_json(existing) != encoded:
                    raise StorageCorruption(
                        f"conflicting content for event_id in {self.path.name}: {event_id}"
                    )
                return False
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        return True

    def tail(self, count: int) -> list[dict[str, Any]]:
        if count < 0:
            raise ValueError("tail count cannot be negative")
        return self.records()[-count:] if count else []

    def extend_once(self, records: Iterable[dict[str, Any]]) -> int:
        return sum(1 for record in records if self.append_once(record))
