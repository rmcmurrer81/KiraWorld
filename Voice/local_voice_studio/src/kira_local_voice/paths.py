"""Path containment and atomic persistence primitives."""

from __future__ import annotations

import json
import os
import re
import tempfile
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from .errors import ValidationError

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")

@dataclass(frozen=True,slots=True)
class PinnedDirectory:
    path: Path; device: int; inode: int
    @classmethod
    def capture(cls,path:Path):
        absolute=path.absolute()
        if absolute.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(absolute)):
            raise ValidationError("trusted storage root cannot be a link or junction")
        resolved=absolute.resolve(strict=True)
        if resolved!=absolute: raise ValidationError("trusted storage root changed during initialization")
        info=resolved.stat(); return cls(resolved,info.st_dev,info.st_ino)
    def assert_unchanged(self):
        if self.path.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(self.path)):
            raise ValidationError("trusted storage root became a link or junction")
        info=self.path.stat()
        if self.path.resolve(strict=True)!=self.path or (info.st_dev,info.st_ino)!=(self.device,self.inode):
            raise ValidationError("trusted storage root identity changed")

@contextmanager
def exclusive_file_lock(path: Path, *, timeout: float = 5.0):
    """Small cross-process mutex with ownership-checked cleanup."""
    path.parent.mkdir(parents=True,exist_ok=True); token=secrets.token_hex(32); deadline=time.monotonic()+timeout
    fd=-1
    while fd<0:
        try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_BINARY",0),0o600)
        except FileExistsError:
            if time.monotonic()>=deadline: raise ValidationError("timed out acquiring local storage lock")
            time.sleep(.02)
    try:
        os.write(fd,token.encode()); os.fsync(fd); yield
    finally:
        os.close(fd)
        try: owned=path.read_text(encoding="ascii")==token
        except OSError: owned=False
        if owned: path.unlink(missing_ok=True)


def safe_component(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise ValidationError(
            f"{field} must be 1-96 characters using letters, digits, dot, underscore, or hyphen"
        )
    if value in {".", ".."} or ".." in value:
        raise ValidationError(f"{field} cannot contain a parent-directory marker")
    return value


def contained_path(root: Path, *parts: str) -> Path:
    root = root.expanduser().resolve()
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValidationError("path escapes the configured local data directory") from exc
    return candidate


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_json_new(path: Path, payload: dict[str, Any]) -> None:
    """Atomically create a JSON file and refuse to replace an existing record."""

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # A same-volume hard link is an atomic create-if-absent operation. The
        # temporary inode is complete before the public name can become visible.
        os.link(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
