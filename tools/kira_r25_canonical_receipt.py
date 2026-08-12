from __future__ import annotations

"""Canonical framed receipts and append-only Windows persistence for R25.

This module is deliberately transport- and controller-agnostic.  It does not
start a child process, create a pipe, or grant any Blender/body authority.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import struct
from typing import Any, Mapping
import unicodedata


RECEIPT_MAGIC = b"K25RCPT!"
RECEIPT_VERSION = 1
MAX_RECEIPT_PAYLOAD_BYTES = 1024 * 1024
RECEIPT_HEADER = struct.Struct(">8sIQ32s")
RECEIPT_HEADER_BYTES = RECEIPT_HEADER.size
MAX_RECEIPT_FRAME_BYTES = RECEIPT_HEADER_BYTES + MAX_RECEIPT_PAYLOAD_BYTES
MAX_RECEIPT_DEPTH = 32
MAX_RECEIPT_NODES = 8192
MIN_RECEIPT_INTEGER = -(2**63)
MAX_RECEIPT_INTEGER = 2**63 - 1


class ReceiptFrameError(ValueError):
    """A received frame is not the one strict canonical receipt format."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ReceiptPersistenceError(RuntimeError):
    """The exact append-only receipt could not be reserved or persisted."""


class _DuplicateKeyError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _validate_string(value: str, *, location: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ReceiptFrameError(
            "SURROGATE_FORBIDDEN",
            f"receipt string contains a surrogate code point at {location}",
        )
    if unicodedata.normalize("NFC", value) != value:
        raise ReceiptFrameError(
            "STRING_NOT_NFC",
            f"receipt string is not NFC-normalized at {location}",
        )


def _validate_canonical_value(value: Any) -> None:
    """Validate the bounded canonical subset without recursive Python calls."""

    stack: list[tuple[Any, str, int]] = [(value, "$", 1)]
    nodes = 0
    while stack:
        current, location, depth = stack.pop()
        nodes += 1
        if nodes > MAX_RECEIPT_NODES:
            raise ReceiptFrameError("NODE_LIMIT", "receipt exceeds the structural node maximum")
        if depth > MAX_RECEIPT_DEPTH:
            raise ReceiptFrameError("DEPTH_LIMIT", "receipt exceeds the nesting-depth maximum")
        if current is None or isinstance(current, bool):
            continue
        if isinstance(current, str):
            _validate_string(current, location=location)
            continue
        if isinstance(current, int):
            if current < MIN_RECEIPT_INTEGER or current > MAX_RECEIPT_INTEGER:
                raise ReceiptFrameError(
                    "INTEGER_RANGE",
                    f"receipt integer is outside signed 64-bit range at {location}",
                )
            continue
        if isinstance(current, float):
            raise ReceiptFrameError(
                "FLOAT_FORBIDDEN",
                f"floating-point values are outside the receipt canonical subset at {location}",
            )
        if isinstance(current, list):
            for index in range(len(current) - 1, -1, -1):
                stack.append((current[index], f"{location}[{index}]", depth + 1))
            continue
        if isinstance(current, dict):
            for key, child in reversed(list(current.items())):
                nodes += 1
                if nodes > MAX_RECEIPT_NODES:
                    raise ReceiptFrameError("NODE_LIMIT", "receipt exceeds the structural node maximum")
                if not isinstance(key, str):
                    raise ReceiptFrameError(
                        "NON_STRING_KEY",
                        f"receipt object key is not a string at {location}",
                    )
                _validate_string(key, location=f"{location}.<key>")
                stack.append((child, f"{location}.{key}", depth + 1))
            continue
        raise ReceiptFrameError(
            "UNSUPPORTED_VALUE",
            f"unsupported receipt value {type(current).__name__} at {location}",
        )


def _scan_json_structure(text: str) -> None:
    """Bound nesting and token nodes before invoking the JSON decoder."""

    expected_closers: list[str] = []
    nodes = 0
    index = 0
    length = len(text)
    delimiters = " \t\r\n,]}:"
    while index < length:
        character = text[index]
        if character in " \t\r\n,: ":
            index += 1
            continue
        if character in "{[":
            nodes += 1
            if nodes > MAX_RECEIPT_NODES:
                raise ReceiptFrameError("NODE_LIMIT", "receipt exceeds the structural node maximum")
            expected_closers.append("}" if character == "{" else "]")
            if len(expected_closers) > MAX_RECEIPT_DEPTH:
                raise ReceiptFrameError("DEPTH_LIMIT", "receipt exceeds the nesting-depth maximum")
            index += 1
            continue
        if character in "}]":
            if not expected_closers or expected_closers.pop() != character:
                raise ReceiptFrameError("STRUCTURE_INVALID", "receipt has mismatched structural delimiters")
            index += 1
            continue
        nodes += 1
        if nodes > MAX_RECEIPT_NODES:
            raise ReceiptFrameError("NODE_LIMIT", "receipt exceeds the structural node maximum")
        if character == '"':
            index += 1
            escaped = False
            while index < length:
                current = text[index]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    index += 1
                    break
                index += 1
            else:
                raise ReceiptFrameError("STRUCTURE_INVALID", "receipt contains an unterminated string")
            continue
        index += 1
        while index < length and text[index] not in delimiters:
            index += 1
    if expected_closers:
        raise ReceiptFrameError("STRUCTURE_INVALID", "receipt contains unclosed containers")


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the one accepted UTF-8 JSON representation for a receipt object.

    The subset intentionally excludes floats so cross-runtime float rendering
    cannot create a second spelling for the same security-relevant receipt.
    """

    if not isinstance(payload, Mapping):
        raise ReceiptFrameError("TOP_LEVEL_TYPE", "receipt payload must be an object")
    materialized = dict(payload)
    _validate_canonical_value(materialized)
    try:
        encoded = json.dumps(
            materialized,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise ReceiptFrameError("JSON_ENCODING", f"receipt JSON cannot be encoded: {exc}") from exc
    if len(encoded) > MAX_RECEIPT_PAYLOAD_BYTES:
        raise ReceiptFrameError("PAYLOAD_TOO_LARGE", "receipt payload exceeds the fixed maximum")
    return encoded


def encode_receipt_frame(payload: Mapping[str, Any]) -> bytes:
    canonical = canonical_json_bytes(payload)
    digest = hashlib.sha256(canonical).digest()
    return RECEIPT_HEADER.pack(
        RECEIPT_MAGIC,
        RECEIPT_VERSION,
        len(canonical),
        digest,
    ) + canonical


@dataclass(frozen=True)
class DecodedReceipt:
    payload: dict[str, Any]
    canonical_payload: bytes
    payload_sha256: str
    frame_sha256: str


def decode_receipt_frame(frame: bytes) -> DecodedReceipt:
    """Decode one complete frame, rejecting truncation, trailing bytes, or drift."""

    if not isinstance(frame, bytes):
        raise ReceiptFrameError("FRAME_TYPE", "receipt frame must be immutable bytes")
    if len(frame) > MAX_RECEIPT_FRAME_BYTES:
        raise ReceiptFrameError("FRAME_TOO_LARGE", "receipt frame exceeds the exact maximum")
    if len(frame) < RECEIPT_HEADER_BYTES:
        raise ReceiptFrameError("TRUNCATED_HEADER", "receipt header is truncated")
    magic, version, payload_length, expected_digest = RECEIPT_HEADER.unpack_from(frame)
    if magic != RECEIPT_MAGIC:
        raise ReceiptFrameError("MAGIC_MISMATCH", "receipt magic is not recognized")
    if version != RECEIPT_VERSION:
        raise ReceiptFrameError("VERSION_MISMATCH", "receipt version is not supported")
    if payload_length > MAX_RECEIPT_PAYLOAD_BYTES:
        raise ReceiptFrameError("PAYLOAD_TOO_LARGE", "declared receipt payload exceeds the fixed maximum")
    expected_frame_length = RECEIPT_HEADER_BYTES + payload_length
    if len(frame) < expected_frame_length:
        raise ReceiptFrameError("TRUNCATED_PAYLOAD", "receipt payload is truncated")
    if len(frame) > expected_frame_length:
        raise ReceiptFrameError("TRAILING_BYTES", "receipt frame has trailing bytes")
    canonical = frame[RECEIPT_HEADER_BYTES:]
    actual_digest = hashlib.sha256(canonical).digest()
    if not hmac.compare_digest(actual_digest, expected_digest):
        raise ReceiptFrameError("DIGEST_MISMATCH", "receipt payload SHA-256 does not match the header")
    try:
        text = canonical.decode("utf-8", errors="strict")
        _scan_json_structure(text)
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateKeyError as exc:
        raise ReceiptFrameError("DUPLICATE_KEY", f"duplicate receipt key is forbidden: {exc}") from exc
    except ReceiptFrameError:
        raise
    except RecursionError as exc:
        raise ReceiptFrameError("DEPTH_LIMIT", "receipt JSON decoder recursion was bounded") from exc
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReceiptFrameError("INVALID_JSON", f"receipt payload is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReceiptFrameError("TOP_LEVEL_TYPE", "receipt payload must be an object")
    _validate_canonical_value(payload)
    if canonical_json_bytes(payload) != canonical:
        raise ReceiptFrameError("NONCANONICAL_JSON", "receipt payload is valid JSON but not canonical JSON")
    return DecodedReceipt(
        payload=payload,
        canonical_payload=canonical,
        payload_sha256=actual_digest.hex(),
        frame_sha256=hashlib.sha256(frame).hexdigest(),
    )


def _win32_error(prefix: str) -> ReceiptPersistenceError:
    return ReceiptPersistenceError(f"{prefix}: Windows error {ctypes.get_last_error()}")


class WindowsExclusiveReceiptReservation:
    """One parent-held CREATE_NEW receipt handle with no write/delete sharing.

    A successful child frame is written byte-for-byte.  A rejected child frame
    consumes the reservation with a canonical failure receipt.  Neither close
    nor error handling deletes, truncates, or retries the exact evidence path.
    """

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    CREATE_NEW = 1
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    FILE_FLAG_WRITE_THROUGH = 0x80000000

    def __init__(self, path: Path, handle: int, kernel32: Any) -> None:
        self.path = path
        self._handle = handle
        self._kernel32 = kernel32
        self._written = False
        self._consumed = False
        self._poisoned = False
        self._closed = False

    @classmethod
    def reserve(cls, path: Path) -> "WindowsExclusiveReceiptReservation":
        if os.name != "nt":
            raise ReceiptPersistenceError("exclusive receipt reservation is Windows-only")
        exact_path = Path(path).absolute()
        if not exact_path.parent.is_dir():
            raise ReceiptPersistenceError("receipt parent directory must already exist")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        kernel32.WriteFile.restype = wintypes.BOOL
        kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
        kernel32.FlushFileBuffers.restype = wintypes.BOOL
        kernel32.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
        kernel32.GetFileSizeEx.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateFileW(
            str(exact_path),
            cls.GENERIC_READ | cls.GENERIC_WRITE,
            cls.FILE_SHARE_READ,
            None,
            cls.CREATE_NEW,
            cls.FILE_ATTRIBUTE_NORMAL | cls.FILE_FLAG_WRITE_THROUGH,
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise _win32_error("cannot reserve exact append-only receipt")
        return cls(exact_path, int(handle), kernel32)

    @property
    def written(self) -> bool:
        return self._written

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def consumed(self) -> bool:
        return self._consumed

    @property
    def poisoned(self) -> bool:
        return self._poisoned

    def _write_once(self, frame: bytes) -> None:
        if self._closed:
            raise ReceiptPersistenceError("receipt reservation is already closed")
        if self._consumed:
            raise ReceiptPersistenceError("append-only receipt reservation was already consumed")
        if not isinstance(frame, bytes) or not frame or len(frame) > MAX_RECEIPT_FRAME_BYTES:
            raise ReceiptPersistenceError("persisted receipt frame size is invalid")
        # Mark the exact slot both consumed and poisoned before the first I/O
        # call.  Only a completely written, flushed, sized, and read-back frame
        # clears poison.  Re-entry or any exception can therefore never retry.
        self._consumed = True
        self._poisoned = True
        try:
            buffer = ctypes.create_string_buffer(frame, len(frame))
            written = wintypes.DWORD()
            if not self._kernel32.WriteFile(
                self._handle,
                buffer,
                len(frame),
                ctypes.byref(written),
                None,
            ) or written.value != len(frame):
                raise _win32_error("receipt write failed; partial evidence was preserved")
            if not self._kernel32.FlushFileBuffers(self._handle):
                raise _win32_error("receipt flush failed; written evidence was preserved")
            size = ctypes.c_longlong()
            if not self._kernel32.GetFileSizeEx(self._handle, ctypes.byref(size)):
                raise _win32_error("receipt size verification failed; written evidence was preserved")
            if size.value != len(frame):
                raise ReceiptPersistenceError("receipt size mismatch; written evidence was preserved")
            try:
                persisted = self.path.read_bytes()
            except OSError as exc:
                raise ReceiptPersistenceError(
                    f"receipt readback failed; evidence was preserved: {exc}"
                ) from exc
            if persisted != frame:
                raise ReceiptPersistenceError("receipt post-write bytes differ; evidence was preserved")
            self._written = True
            self._poisoned = False
        except BaseException:
            raise

    def accept_child_frame(self, frame: object) -> DecodedReceipt:
        """Validate then persist exact child bytes, or persist one failure receipt."""

        if self._consumed:
            raise ReceiptPersistenceError("append-only receipt reservation was already consumed")
        try:
            decoded = decode_receipt_frame(frame)  # type: ignore[arg-type]
        except ReceiptFrameError as exc:
            immutable_snapshot_available = isinstance(frame, bytes)
            received_bytes = len(frame) if immutable_snapshot_available else None
            received_sha256 = hashlib.sha256(frame).hexdigest() if immutable_snapshot_available else None
            failure = encode_receipt_frame(
                {
                    "failure_code": exc.code,
                    "immutable_byte_snapshot_available": immutable_snapshot_available,
                    "received_bytes": received_bytes,
                    "received_sha256": received_sha256,
                    "received_type": type(frame).__name__,
                    "schema": "kira.avatar.r25.receipt_rejection.v1",
                    "status": "REJECTED_APPEND_ONLY",
                }
            )
            self._write_once(failure)
            raise
        self._write_once(frame)
        return decoded

    def close(self) -> None:
        if self._closed:
            return
        pending_error: BaseException | None = None
        if not self._consumed:
            try:
                self._write_once(
                    encode_receipt_frame(
                        {
                            "immutable_byte_snapshot_available": False,
                            "reason": "GRACEFUL_CLOSE_WITHOUT_CHILD_FRAME",
                            "schema": "kira.avatar.r25.receipt_reservation.v1",
                            "status": "ABANDONED_UNUSED",
                        }
                    )
                )
            except BaseException as exc:
                pending_error = exc
        if not self._kernel32.CloseHandle(self._handle):
            close_error = _win32_error("receipt reservation handle close failed")
            if pending_error is None:
                pending_error = close_error
        self._closed = True
        if pending_error is not None:
            raise pending_error

    def __enter__(self) -> "WindowsExclusiveReceiptReservation":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


__all__ = [
    "DecodedReceipt",
    "MAX_RECEIPT_DEPTH",
    "MAX_RECEIPT_FRAME_BYTES",
    "MAX_RECEIPT_INTEGER",
    "MAX_RECEIPT_NODES",
    "MAX_RECEIPT_PAYLOAD_BYTES",
    "MIN_RECEIPT_INTEGER",
    "RECEIPT_HEADER",
    "RECEIPT_HEADER_BYTES",
    "RECEIPT_MAGIC",
    "RECEIPT_VERSION",
    "ReceiptFrameError",
    "ReceiptPersistenceError",
    "WindowsExclusiveReceiptReservation",
    "canonical_json_bytes",
    "decode_receipt_frame",
    "encode_receipt_frame",
]
