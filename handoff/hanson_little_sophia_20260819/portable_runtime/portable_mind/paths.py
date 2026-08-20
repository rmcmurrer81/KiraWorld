from __future__ import annotations

import os
import re
from pathlib import Path


SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class SandboxError(ValueError):
    """Raised when a requested path would escape the local-data sandbox."""


def _without_windows_device_prefix(value: str) -> str:
    """Normalize equivalent Win32 and extended-length path spellings."""

    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _comparison_path(path: Path) -> str:
    value = _without_windows_device_prefix(str(path))
    return os.path.normcase(os.path.abspath(value))


class LocalSandbox:
    """Resolve every writable path beneath one explicit local-only root."""

    def __init__(self, root: str | Path):
        resolved = Path(root).expanduser().resolve()
        self.root = Path(_without_windows_device_prefix(str(resolved)))
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str | Path, *, create_parent: bool = False) -> Path:
        relative_path = Path(relative)
        if relative_path.is_absolute():
            raise SandboxError("absolute paths are not allowed in the data sandbox")
        resolved_candidate = (self.root / relative_path).resolve()
        candidate = Path(_without_windows_device_prefix(str(resolved_candidate)))
        try:
            common = os.path.commonpath((_comparison_path(self.root), _comparison_path(candidate)))
        except (OSError, ValueError) as exc:
            raise SandboxError("path escapes the data sandbox") from exc
        if common != _comparison_path(self.root):
            raise SandboxError("path escapes the data sandbox")
        if create_parent:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def person_dir(self, profile_id: str) -> Path:
        if not SAFE_ID.fullmatch(profile_id):
            raise SandboxError("invalid profile identifier")
        path = self.resolve(Path("people") / profile_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def export_path(self, filename: str) -> Path:
        if not SAFE_FILENAME.fullmatch(filename):
            raise SandboxError("export filename must be a simple local filename")
        return self.resolve(Path("exports") / filename, create_parent=True)

    def import_path(self, filename: str) -> Path:
        if not SAFE_FILENAME.fullmatch(filename):
            raise SandboxError("import filename must be a simple local filename")
        return self.resolve(Path("imports") / filename, create_parent=True)


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_data_root() -> Path:
    return package_root() / "local_data"
