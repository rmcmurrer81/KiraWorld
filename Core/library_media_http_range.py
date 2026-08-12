"""Bounded read-only HTTP byte-range responses for validated library media.

The helper has no server, UI, playback, decoding, persistence, or policy
selection behavior.  A caller must first select and resolve a descriptor with
``LibraryMediaResolver``.  This layer revalidates that descriptor and exposes
only a bounded byte iterator suitable for an HTTP adapter.
"""

from __future__ import annotations

import hashlib
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from library_media_resolver import LibraryMediaResolver, LibraryMediaResolutionError


SAFE_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".wmv": "video/x-ms-wmv",
    ".m4v": "video/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
}

_FAMILY_EXTENSIONS = {
    "page_media": {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
    },
    "timed_video": {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"},
    "timed_audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"},
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RANGE_RE = re.compile(r"^bytes\s*=\s*(\d*)\s*-\s*(\d*)$", re.IGNORECASE)

DEFAULT_MAX_NON_RANGE_BYTES = 1024 * 1024
DEFAULT_MAX_RANGE_BYTES = 8 * 1024 * 1024
DEFAULT_READ_CHUNK_BYTES = 64 * 1024
ABSOLUTE_MAX_RESPONSE_BYTES = 16 * 1024 * 1024
ABSOLUTE_MAX_READ_CHUNK_BYTES = 1024 * 1024


class LibraryMediaHttpRangeError(ValueError):
    """Raised when a descriptor or serving boundary is unsafe."""


class RangeNotSatisfiable(LibraryMediaHttpRangeError):
    """Raised by the parser for malformed, multiple, or unavailable ranges."""


@dataclass(frozen=True)
class ByteRangeSelection:
    start: int
    end: int
    resource_size: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def _positive_bounded_int(value: int, field_name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise LibraryMediaHttpRangeError(f"{field_name} must be a positive integer.")
    if value > maximum:
        raise LibraryMediaHttpRangeError(
            f"{field_name} exceeds the absolute safety maximum of {maximum} bytes."
        )
    return value


def parse_single_byte_range(range_header: str, resource_size: int) -> ByteRangeSelection:
    """Parse one RFC-style ``bytes`` range or raise ``RangeNotSatisfiable``.

    Supported forms are ``bytes=first-last``, ``bytes=first-``, and
    ``bytes=-suffix_length``.  Multiple ranges are intentionally unsupported.
    An excessive last position is clamped to the current representation size.
    """

    if isinstance(resource_size, bool) or not isinstance(resource_size, int) or resource_size < 0:
        raise LibraryMediaHttpRangeError("resource_size must be a non-negative integer.")
    if not isinstance(range_header, str) or not range_header.strip():
        raise RangeNotSatisfiable("Range must be one non-empty bytes range.")
    if (
        len(range_header) > 256
        or "," in range_header
        or "\r" in range_header
        or "\n" in range_header
        or "\x00" in range_header
    ):
        raise RangeNotSatisfiable("multiple or oversized Range values are unsupported.")
    match = _RANGE_RE.fullmatch(range_header.strip())
    if match is None:
        raise RangeNotSatisfiable("Range must use a single bytes=start-end form.")
    first_text, last_text = match.groups()
    if not first_text and not last_text:
        raise RangeNotSatisfiable("Range must include a start or suffix length.")
    if resource_size == 0:
        raise RangeNotSatisfiable("an empty representation has no satisfiable byte range.")

    if not first_text:
        suffix_length = int(last_text)
        if suffix_length <= 0:
            raise RangeNotSatisfiable("suffix byte length must be greater than zero.")
        start = max(resource_size - suffix_length, 0)
        end = resource_size - 1
        return ByteRangeSelection(start=start, end=end, resource_size=resource_size)

    start = int(first_text)
    if start >= resource_size:
        raise RangeNotSatisfiable("range start is outside the representation.")
    if last_text:
        requested_end = int(last_text)
        if requested_end < start:
            raise RangeNotSatisfiable("range end precedes its start.")
        end = min(requested_end, resource_size - 1)
    else:
        end = resource_size - 1
    return ByteRangeSelection(start=start, end=end, resource_size=resource_size)


def _file_identity(path: Path) -> tuple[int | None, int | None, int, int, int]:
    try:
        link_stat = path.lstat()
        if stat.S_ISLNK(link_stat.st_mode):
            raise LibraryMediaHttpRangeError("validated media path became a symlink.")
        attributes = getattr(link_stat, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if attributes & reparse_flag:
            raise LibraryMediaHttpRangeError("validated media path became a reparse point.")
        current = path.stat()
    except OSError as exc:
        raise LibraryMediaHttpRangeError(
            "validated media path is no longer safely readable."
        ) from exc
    if not stat.S_ISREG(current.st_mode):
        raise LibraryMediaHttpRangeError("validated media path is no longer a regular file.")
    return (
        getattr(current, "st_dev", None),
        getattr(current, "st_ino", None),
        current.st_size,
        current.st_mtime_ns,
        current.st_ctime_ns,
    )


def _hash_with_identity(
    path: Path,
) -> tuple[str, tuple[int | None, int | None, int, int, int]]:
    before = _file_identity(path)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise LibraryMediaHttpRangeError(
            "validated media path could not be rehashed read-only."
        ) from exc
    after = _file_identity(path)
    if before != after:
        raise LibraryMediaHttpRangeError(
            "media source changed during exact hash revalidation."
        )
    return digest.hexdigest(), after


@dataclass(frozen=True)
class ReadOnlyByteRangeResponse:
    """HTTP metadata plus a bounded, read-only body iterator."""

    status_code: int
    headers: Mapping[str, str]
    range_start: int | None
    range_end: int | None
    resource_size: int
    _path: Path | None = field(default=None, repr=False, compare=False)
    _expected_identity: tuple[int | None, int | None, int, int, int] | None = field(
        default=None, repr=False, compare=False
    )
    _expected_sha256: str | None = field(default=None, repr=False, compare=False)
    _read_chunk_bytes: int = field(default=DEFAULT_READ_CHUNK_BYTES, repr=False)
    _rehash_before_stream: bool = field(default=True, repr=False, compare=False)
    _continuation_guard: Callable[[], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    @property
    def content_length(self) -> int:
        return int(self.headers.get("Content-Length", "0"))

    def iter_body(self) -> Iterator[bytes]:
        """Yield only the selected interval in chunks bounded by configuration."""

        if self._path is None or self.range_start is None or self.range_end is None:
            return
        if self.content_length == 0:
            return
        if self._continuation_guard is not None:
            self._continuation_guard()
        if self._rehash_before_stream:
            current_digest, current_identity = _hash_with_identity(self._path)
            if (
                current_identity != self._expected_identity
                or current_digest != self._expected_sha256
            ):
                raise LibraryMediaHttpRangeError(
                    "media source changed after descriptor revalidation."
                )
        elif _file_identity(self._path) != self._expected_identity:
            raise LibraryMediaHttpRangeError(
                "media source identity changed after ephemeral grant validation."
            )
        remaining = self.content_length
        try:
            with self._path.open("rb") as handle:
                handle.seek(self.range_start)
                while remaining:
                    if self._continuation_guard is not None:
                        self._continuation_guard()
                    requested = min(remaining, self._read_chunk_bytes)
                    chunk = handle.read(requested)
                    if not chunk:
                        raise LibraryMediaHttpRangeError(
                            "media source ended before the validated response range."
                        )
                    if len(chunk) > requested:
                        raise LibraryMediaHttpRangeError(
                            "read exceeded the configured response chunk boundary."
                        )
                    remaining -= len(chunk)
                    yield chunk
        finally:
            if _file_identity(self._path) != self._expected_identity:
                raise LibraryMediaHttpRangeError(
                    "media source changed while the response was being read."
                )


class LibraryMediaHttpRange:
    """Prepare bounded HTTP responses from resolver-issued descriptors only."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        max_non_range_bytes: int = DEFAULT_MAX_NON_RANGE_BYTES,
        max_range_bytes: int = DEFAULT_MAX_RANGE_BYTES,
        read_chunk_bytes: int = DEFAULT_READ_CHUNK_BYTES,
    ) -> None:
        self._project_root = Path(project_root).resolve(strict=True)
        self._resolver = LibraryMediaResolver(self._project_root)
        self._max_non_range_bytes = _positive_bounded_int(
            max_non_range_bytes,
            "max_non_range_bytes",
            ABSOLUTE_MAX_RESPONSE_BYTES,
        )
        self._max_range_bytes = _positive_bounded_int(
            max_range_bytes,
            "max_range_bytes",
            ABSOLUTE_MAX_RESPONSE_BYTES,
        )
        self._read_chunk_bytes = _positive_bounded_int(
            read_chunk_bytes,
            "read_chunk_bytes",
            ABSOLUTE_MAX_READ_CHUNK_BYTES,
        )

    def _revalidate_descriptor(
        self, descriptor: Mapping[str, Any]
    ) -> tuple[dict[str, Any], Path, str]:
        if not isinstance(descriptor, Mapping):
            raise LibraryMediaHttpRangeError(
                "a LibraryMediaResolver descriptor mapping is required."
            )
        path = descriptor.get("project_relative_path")
        digest = descriptor.get("sha256")
        size = descriptor.get("size_bytes")
        extension = descriptor.get("extension")
        classification = descriptor.get("classification")
        selection = descriptor.get("selection")
        if not isinstance(path, str) or not path.startswith("Data/library/"):
            raise LibraryMediaHttpRangeError(
                "descriptor must contain an exact Data/library project-relative path."
            )
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise LibraryMediaHttpRangeError("descriptor must contain an exact lowercase SHA-256.")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise LibraryMediaHttpRangeError("descriptor size_bytes must be non-negative.")
        if not isinstance(extension, str) or extension != extension.lower():
            raise LibraryMediaHttpRangeError("descriptor extension must be normalized.")
        if not isinstance(classification, Mapping):
            raise LibraryMediaHttpRangeError("descriptor classification is required.")
        if not isinstance(selection, Mapping) or selection.get("owner_selected") is not True:
            raise LibraryMediaHttpRangeError(
                "descriptor must retain LibraryMediaResolver owner-selection evidence."
            )
        if selection.get("read_only_resolution") is not True:
            raise LibraryMediaHttpRangeError(
                "descriptor must retain read-only resolution evidence."
            )

        try:
            current = self._resolver.resolve(path)
        except LibraryMediaResolutionError as exc:
            raise LibraryMediaHttpRangeError(
                "descriptor path failed Data/library revalidation."
            ) from exc
        for field_name in (
            "project_relative_path",
            "sha256",
            "size_bytes",
            "extension",
            "classification",
        ):
            if descriptor.get(field_name) != current.get(field_name):
                raise LibraryMediaHttpRangeError(
                    f"descriptor {field_name} no longer matches the exact library source."
                )

        mime_type = self._mime_type_for_validated_descriptor(current)

        physical = (self._project_root / path).resolve(strict=True)
        library_root = (self._project_root / "Data" / "library").resolve(strict=True)
        try:
            physical.relative_to(library_root)
        except ValueError as exc:
            raise LibraryMediaHttpRangeError(
                "revalidated descriptor resolved outside Data/library."
            ) from exc
        return current, physical, mime_type

    @staticmethod
    def _mime_type_for_validated_descriptor(
        descriptor: Mapping[str, Any],
    ) -> str:
        """Return an allowlisted MIME after resolver validation, without I/O."""

        classification = descriptor.get("classification")
        extension = descriptor.get("extension")
        if not isinstance(classification, Mapping) or not isinstance(extension, str):
            raise LibraryMediaHttpRangeError(
                "validated descriptor classification and extension are required."
            )
        family = classification.get("family")
        allowed_extensions = _FAMILY_EXTENSIONS.get(str(family))
        if allowed_extensions is None or extension not in allowed_extensions:
            raise LibraryMediaHttpRangeError(
                "descriptor is not a supported PDF, image, video, or audio source."
            )
        mime_type = SAFE_MIME_TYPES.get(extension)
        if mime_type is None:
            raise LibraryMediaHttpRangeError(
                "descriptor extension has no approved MIME type."
            )
        return mime_type

    @staticmethod
    def _base_headers(mime_type: str, digest: str) -> dict[str, str]:
        return {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Content-Type": mime_type,
            "ETag": f'"sha256-{digest}"',
            "X-Content-Type-Options": "nosniff",
        }

    def prepare(
        self,
        descriptor: Mapping[str, Any],
        *,
        range_header: str | None = None,
    ) -> ReadOnlyByteRangeResponse:
        """Revalidate a descriptor and prepare one bounded HTTP response."""

        current, physical, mime_type = self._revalidate_descriptor(descriptor)
        return self._prepare_validated(
            current,
            physical,
            mime_type,
            range_header=range_header,
            rehash_before_stream=True,
        )

    def _prepare_validated(
        self,
        current: Mapping[str, Any],
        physical: Path,
        mime_type: str,
        *,
        range_header: str | None,
        rehash_before_stream: bool,
    ) -> ReadOnlyByteRangeResponse:
        """Build a response after a caller-specific trust check.

        Strict descriptor serving passes ``rehash_before_stream=True``.  The
        ephemeral grant layer passes ``False`` only after it has independently
        rechecked its short-lived path and file-identity capability.
        """

        size = current["size_bytes"]
        digest = current["sha256"]
        headers = self._base_headers(mime_type, digest)
        identity = _file_identity(physical)
        if identity[2] != size:
            raise LibraryMediaHttpRangeError(
                "media size changed after descriptor revalidation."
            )

        if range_header is None:
            if size > self._max_non_range_bytes:
                headers.update(
                    {
                        "Content-Length": "0",
                        "X-Kira-Range-Required": "true",
                        "X-Kira-Max-Non-Range-Bytes": str(self._max_non_range_bytes),
                    }
                )
                return ReadOnlyByteRangeResponse(
                    status_code=413,
                    headers=headers,
                    range_start=None,
                    range_end=None,
                    resource_size=size,
                )
            headers["Content-Length"] = str(size)
            return ReadOnlyByteRangeResponse(
                status_code=200,
                headers=headers,
                range_start=0 if size else None,
                range_end=size - 1 if size else None,
                resource_size=size,
                _path=physical if size else None,
                _expected_identity=identity if size else None,
                _expected_sha256=digest if size else None,
                _read_chunk_bytes=self._read_chunk_bytes,
                _rehash_before_stream=rehash_before_stream,
            )

        try:
            selected = parse_single_byte_range(range_header, size)
        except RangeNotSatisfiable:
            headers.update(
                {
                    "Content-Length": "0",
                    "Content-Range": f"bytes */{size}",
                }
            )
            return ReadOnlyByteRangeResponse(
                status_code=416,
                headers=headers,
                range_start=None,
                range_end=None,
                resource_size=size,
            )
        if selected.length > self._max_range_bytes:
            headers.update(
                {
                    "Content-Length": "0",
                    "X-Kira-Max-Range-Bytes": str(self._max_range_bytes),
                }
            )
            return ReadOnlyByteRangeResponse(
                status_code=413,
                headers=headers,
                range_start=None,
                range_end=None,
                resource_size=size,
            )
        headers.update(
            {
                "Content-Length": str(selected.length),
                "Content-Range": (
                    f"bytes {selected.start}-{selected.end}/{selected.resource_size}"
                ),
            }
        )
        return ReadOnlyByteRangeResponse(
            status_code=206,
            headers=headers,
            range_start=selected.start,
            range_end=selected.end,
            resource_size=size,
            _path=physical,
            _expected_identity=identity,
            _expected_sha256=digest,
            _read_chunk_bytes=self._read_chunk_bytes,
            _rehash_before_stream=rehash_before_stream,
        )
