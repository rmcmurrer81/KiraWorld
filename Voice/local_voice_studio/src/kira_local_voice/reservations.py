"""Cross-process output and storage-quota reservations."""

from __future__ import annotations

import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

from .errors import ConflictError, ValidationError
from .paths import contained_path, exclusive_file_lock, safe_component


def _regular_file_bytes(root: Path, pattern: str) -> int:
    total = 0
    for path in root.glob(pattern):
        try:
            info = path.stat(follow_symlinks=False)
        except OSError:
            continue
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
    return total


def _reserved_bytes(root: Path) -> int:
    total = 0
    for path in root.glob("*.lock"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            amount = payload["reserved_bytes"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValidationError("local voice quota reservation record is invalid") from exc
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValidationError("local voice quota reservation record is invalid")
        total += amount
    return total


@dataclass(slots=True)
class OutputReservation:
    path: Path
    token: str
    output_name: str
    quota_guard: Path | None
    reserved_bytes: int = 0
    _released: bool = False

    @classmethod
    def acquire(
        cls,
        root: Path,
        output_name: str,
        *,
        outputs_root: Path | None = None,
        staging_root: Path | None = None,
        max_storage_bytes: int | None = None,
        reserved_bytes: int | None = None,
    ) -> "OutputReservation":
        safe_component(output_name, field="output_name")
        quota_values = (outputs_root, staging_root, max_storage_bytes, reserved_bytes)
        if all(value is None for value in quota_values):
            root.mkdir(parents=True, exist_ok=True)
            path = contained_path(root, f"{output_name}.lock")
            token = secrets.token_hex(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            try:
                fd = os.open(path, flags, 0o600)
            except FileExistsError as exc:
                raise ConflictError(f"reservation already exists: {output_name}") from exc
            try:
                payload = json.dumps(
                    {"schema": "kira.local-voice.generic-reservation.v1", "token": token,
                     "output_name": output_name}, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
                os.write(fd, payload); os.fsync(fd)
            except Exception:
                os.close(fd); path.unlink(missing_ok=True); raise
            else:
                os.close(fd)
            return cls(path, token, output_name, None, 0)
        if any(value is None for value in quota_values):
            raise ValidationError("all storage quota inputs must be provided together")
        assert outputs_root is not None and staging_root is not None
        assert max_storage_bytes is not None and reserved_bytes is not None
        if (
            not isinstance(max_storage_bytes, int)
            or isinstance(max_storage_bytes, bool)
            or max_storage_bytes <= 0
            or not isinstance(reserved_bytes, int)
            or isinstance(reserved_bytes, bool)
            or reserved_bytes <= 0
            or reserved_bytes > max_storage_bytes
        ):
            raise ValidationError("storage quota configuration is invalid")
        root.mkdir(parents=True, exist_ok=True)
        outputs_root.mkdir(parents=True, exist_ok=True)
        staging_root.mkdir(parents=True, exist_ok=True)
        path = contained_path(root, f"{output_name}.lock")
        guard = contained_path(root, ".quota.guard")
        token = secrets.token_hex(32)
        with exclusive_file_lock(guard, timeout=5.0):
            used = (
                _regular_file_bytes(outputs_root, "*.wav")
                + _regular_file_bytes(staging_root, "*")
                + _reserved_bytes(root)
            )
            if used + reserved_bytes > max_storage_bytes:
                raise ValidationError("local voice output storage quota is fully reserved")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            try:
                fd = os.open(path, flags, 0o600)
            except FileExistsError as exc:
                raise ConflictError(f"output is reserved: {output_name}.wav") from exc
            try:
                payload = json.dumps(
                    {
                        "schema": "kira.local-voice.output-reservation.v2",
                        "token": token,
                        "output_name": output_name,
                        "reserved_bytes": reserved_bytes,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                os.write(fd, payload)
                os.fsync(fd)
            except Exception:
                os.close(fd)
                path.unlink(missing_ok=True)
                raise
            else:
                os.close(fd)
        return cls(path, token, output_name, guard, reserved_bytes)

    def release(self) -> None:
        if self._released:
            return
        if self.quota_guard is None:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                self._released = True; return
            except (OSError,json.JSONDecodeError):
                return
            if (payload.get("schema")=="kira.local-voice.generic-reservation.v1"
                    and payload.get("token")==self.token and payload.get("output_name")==self.output_name):
                self.path.unlink(missing_ok=True); self._released=True
            return
        with exclusive_file_lock(self.quota_guard, timeout=5.0):
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                self._released = True
                return
            except (OSError, json.JSONDecodeError):
                return
            if (
                payload.get("schema") == "kira.local-voice.output-reservation.v2"
                and payload.get("token") == self.token
                and payload.get("output_name") == self.output_name
                and payload.get("reserved_bytes") == self.reserved_bytes
            ):
                self.path.unlink(missing_ok=True)
                self._released = True
