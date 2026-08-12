"""Static-only resident-media voluntary and evidence gate v4.

This module is deliberately inert.  It does not call a model, inspect or
decode media, play audio, activate a person, create a memory, or authorize a
live run.  It provides deterministic validation and durable append-only
primitives for a separately reviewed external parent.

The module is not a process trust root.  In particular, a digest supplied as
an external observation remains a binding to evidence that the future parent
must independently produce and protect; this core does not turn that digest
into proof of a model call, source read, presentation, attention, experience,
preference, or memory.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import secrets
import stat as stat_module
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


EXACT_MODEL = "qwen3.5:9b"
EXACT_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
PERSON_ID = "kira"
STIMULUS_ORDER = (
    "illustrated_magazine_cover_page_001",
    "unfamiliar_merlion_race_car_crop_page_014",
    "power_rangers_commercial_interval_000_008",
    "highlander_new_york_new_york_interval_000_010",
)
CHOICES = frozenset({"YES", "NO", "CONTINUE", "PAUSE", "STOP"})
MAX_CAPABILITY_TTL_SECONDS = 60
MAX_CHOICE_TO_CAPABILITY_SECONDS = 120
MAX_FUTURE_WALL_CLOCK_SKEW_SECONDS = 2
MAX_EVENT_COUNT = 64

STOP_PATTERN = re.compile(
    r"(?:\b(?:stop|quit|cancel|end|leave)\b|\bdo\s+not\s+continue\b|"
    r"\bdon['\N{RIGHT SINGLE QUOTATION MARK}]?t\s+continue\b|\bno\s+more\b|"
    r"\bi\s+do\s+not\s+consent\b)",
    re.IGNORECASE,
)
PAUSE_PATTERN = re.compile(
    r"\b(?:pause|wait|hold\s+on|not\s+yet|give\s+me\s+a\s+moment)\b",
    re.IGNORECASE,
)
YES_PATTERN = re.compile(
    r"(?:\byes\b|\bi\s+(?:do\s+)?(?:want|choose)\s+to\b|"
    r"\bi['\N{RIGHT SINGLE QUOTATION MARK}]?d\s+like\s+to\b|"
    r"\bshow\s+me\b|\bplay\s+it\b)",
    re.IGNORECASE,
)
NO_PATTERN = re.compile(
    r"(?:\bno\b|\bdecline\b|\bnot\s+interested\b|"
    r"\bi\s+do\s+not\s+want\b|\bi\s+don['\N{RIGHT SINGLE QUOTATION MARK}]?t\s+want\b|"
    r"\bnot\s+for\s+me\b|\bskip\s+it\b)",
    re.IGNORECASE,
)
CONTINUE_PATTERN = re.compile(
    r"(?:\bcontinue\b|\bnext\b|\bgo\s+on\b|\bkeep\s+going\b|\byes\b)",
    re.IGNORECASE,
)


class ResidentMediaV4Error(ValueError):
    """A v4 fail-closed validation, durability, or sequencing gate failed."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ResidentMediaV4Error("value is not strict canonical JSON") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_record(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(value)))


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResidentMediaV4Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ResidentMediaV4Error(f"non-finite JSON number: {value}")
            ),
        )
    except UnicodeDecodeError as exc:
        raise ResidentMediaV4Error("JSON is not strict UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ResidentMediaV4Error("JSON is malformed") from exc


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ResidentMediaV4Error(f"{label} keys are not exact")


def _sha(value: object, field: str) -> str:
    text = str(value or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise ResidentMediaV4Error(f"{field} must be SHA-256")
    return text


def _identifier(value: object, field: str, maximum: int = 128) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0," + str(maximum - 1) + r"}", text):
        raise ResidentMediaV4Error(f"{field} is not a bounded identifier")
    return text


def _bounded_text(value: object, field: str, maximum: int = 16_000) -> str:
    if not isinstance(value, str):
        raise ResidentMediaV4Error(f"{field} must be text")
    text = value.strip()
    if not text or len(text) > maximum or "\x00" in text:
        raise ResidentMediaV4Error(f"{field} is empty or oversized")
    return text


def _positive_int(value: object, field: str, maximum: int = 2**63 - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= maximum:
        raise ResidentMediaV4Error(f"{field} must be a bounded positive integer")
    return value


def _nonnegative_int(value: object, field: str, maximum: int = 2**63 - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ResidentMediaV4Error(f"{field} must be a bounded nonnegative integer")
    return value


def _utc_datetime(value: object, field: str) -> datetime:
    text = str(value or "")
    if not text.endswith("Z"):
        raise ResidentMediaV4Error(f"{field} must be UTC Z time")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ResidentMediaV4Error(f"{field} is invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise ResidentMediaV4Error(f"{field} must be UTC")
    return parsed


def _utc_text(value: datetime) -> str:
    if value.tzinfo != timezone.utc:
        raise ResidentMediaV4Error("clock returned a non-UTC datetime")
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _safe_relative_path(value: object, field: str) -> str:
    text = _bounded_text(value, field, 1024).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ResidentMediaV4Error(f"{field} must be a normalized project-relative path")
    if re.match(r"^[A-Za-z]:", text) or text.startswith("//"):
        raise ResidentMediaV4Error(f"{field} must not be absolute")
    normalized = path.as_posix()
    if normalized != text:
        raise ResidentMediaV4Error(f"{field} is not normalized")
    return normalized


@dataclass(frozen=True, slots=True)
class ClockSample:
    utc: datetime
    monotonic_ns: int
    clock_id_sha256: str

    @property
    def utc_text(self) -> str:
        return _utc_text(self.utc)


class SystemClockAuthority:
    """Reads time internally; transition records cannot supply their own time.

    This class validates local ordering and freshness, but is not a claim that
    the Python process or host clock is tamper-proof.  The later external
    parent remains responsible for its own process/host trust evidence.
    """

    CLOCK_ID_SHA256 = sha256_bytes(b"kira.system_wall_plus_monotonic.clock.v1")

    def __init__(self) -> None:
        self._last_monotonic_ns = -1

    def sample(self) -> ClockSample:
        for _ in range(1024):
            monotonic_ns = time.monotonic_ns()
            if monotonic_ns > self._last_monotonic_ns:
                now = datetime.now(timezone.utc)
                self._last_monotonic_ns = monotonic_ns
                return ClockSample(now, monotonic_ns, self.CLOCK_ID_SHA256)
        raise ResidentMediaV4Error("trusted monotonic clock did not advance")

    def assert_not_future(self, value: datetime, field: str) -> None:
        now = datetime.now(timezone.utc)
        if value > now + timedelta(seconds=MAX_FUTURE_WALL_CLOCK_SKEW_SECONDS):
            raise ResidentMediaV4Error(f"{field} is in the future")


def _file_attributes(path_stat: os.stat_result) -> int:
    return int(getattr(path_stat, "st_file_attributes", 0))


def _is_reparse(path_stat: os.stat_result) -> bool:
    return bool(_file_attributes(path_stat) & 0x400)


def _path_is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or bool(hasattr(os.path, "isjunction") and os.path.isjunction(path))


class DurableDirectory:
    """Exclusive durable record store with reopen and identity validation."""

    def __init__(self, root: Path) -> None:
        original = Path(root)
        if _path_is_link_or_junction(original):
            raise ResidentMediaV4Error("durable root cannot be a link or junction")
        self.root = original.resolve(strict=True)
        if not self.root.is_dir():
            raise ResidentMediaV4Error("durable root must be an existing real directory")
        root_stat = self.root.stat()
        if _is_reparse(root_stat):
            raise ResidentMediaV4Error("durable root cannot be a reparse point")
        self._identity = (root_stat.st_dev, root_stat.st_ino, _file_attributes(root_stat))

    def _verify_root(self) -> None:
        if _path_is_link_or_junction(self.root):
            raise ResidentMediaV4Error("durable root became a link or junction")
        current = self.root.stat()
        identity = (current.st_dev, current.st_ino, _file_attributes(current))
        if identity != self._identity or _is_reparse(current):
            raise ResidentMediaV4Error("durable root identity changed")

    @staticmethod
    def _verify_regular_single_link(path: Path, path_stat: os.stat_result) -> None:
        if not stat_module.S_ISREG(path_stat.st_mode):
            raise ResidentMediaV4Error(f"durable record is not regular: {path.name}")
        if _is_reparse(path_stat) or _path_is_link_or_junction(path):
            raise ResidentMediaV4Error(f"durable record is a link/reparse point: {path.name}")
        if getattr(path_stat, "st_nlink", 1) != 1:
            raise ResidentMediaV4Error(f"durable record link count is not one: {path.name}")

    def exclusive_append(self, name: str, record: Mapping[str, Any]) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,191}\.json", name):
            raise ResidentMediaV4Error("durable record filename is invalid")
        self._verify_root()
        payload = canonical_json_bytes(dict(record)) + b"\n"
        path = self.root / name
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(path, flags, 0o600)
        write_stat: os.stat_result | None = None
        try:
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise ResidentMediaV4Error("durable append made no progress")
                offset += written
            os.fsync(descriptor)
            write_stat = os.fstat(descriptor)
            self._verify_regular_single_link(path, write_stat)
        finally:
            os.close(descriptor)
        if write_stat is None:
            raise ResidentMediaV4Error("durable append did not obtain file identity")
        self._verify_root()
        read_flags = os.O_RDONLY
        if hasattr(os, "O_BINARY"):
            read_flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            read_flags |= os.O_NOFOLLOW
        reopened_descriptor = os.open(path, read_flags)
        try:
            reopen_stat = os.fstat(reopened_descriptor)
            self._verify_regular_single_link(path, reopen_stat)
            write_identity = (write_stat.st_dev, write_stat.st_ino, write_stat.st_size)
            reopen_identity = (reopen_stat.st_dev, reopen_stat.st_ino, reopen_stat.st_size)
            if reopen_identity != write_identity:
                raise ResidentMediaV4Error("reopened durable record identity changed")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(reopened_descriptor, 65_536)
                if not chunk:
                    break
                chunks.append(chunk)
            reopened = b"".join(chunks)
        finally:
            os.close(reopened_descriptor)
        if reopened != payload:
            raise ResidentMediaV4Error("reopened durable record bytes changed")
        self._verify_root()
        return {
            "schema": "kira.durable_append_receipt.v4",
            "name": name,
            "byte_count": len(payload),
            "file_sha256": sha256_bytes(payload),
            "record_sha256": sha256_bytes(payload[:-1]),
            "reopened_exact": True,
            "file_identity_validated": True,
            "root_identity_validated": True,
            "exclusive_create": True,
            "fsync_completed": True,
        }

    def read_exact(self, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,191}\.json", name):
            raise ResidentMediaV4Error("durable record filename is invalid")
        self._verify_root()
        path = self.root / name
        if _path_is_link_or_junction(path):
            raise ResidentMediaV4Error("durable record cannot be a link or junction")
        read_flags = os.O_RDONLY
        if hasattr(os, "O_BINARY"):
            read_flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            read_flags |= os.O_NOFOLLOW
        descriptor = os.open(path, read_flags)
        try:
            before = os.fstat(descriptor)
            self._verify_regular_single_link(path, before)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 65_536)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
            after = os.fstat(descriptor)
            self._verify_regular_single_link(path, after)
        finally:
            os.close(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise ResidentMediaV4Error("durable record identity changed while reading")
        current_path_stat = path.stat()
        self._verify_regular_single_link(path, current_path_stat)
        if (after.st_dev, after.st_ino, after.st_size) != (
            current_path_stat.st_dev,
            current_path_stat.st_ino,
            current_path_stat.st_size,
        ):
            raise ResidentMediaV4Error("durable record path identity changed after reading")
        if not data.endswith(b"\n") or data.count(b"\n") != 1:
            raise ResidentMediaV4Error("durable record must have one terminal newline")
        record = strict_json_loads(data[:-1])
        if not isinstance(record, dict) or canonical_json_bytes(record) + b"\n" != data:
            raise ResidentMediaV4Error("durable record is not exact canonical JSON")
        self._verify_root()
        receipt = {
            "schema": "kira.durable_reopen_receipt.v4",
            "name": name,
            "byte_count": len(data),
            "file_sha256": sha256_bytes(data),
            "record_sha256": sha256_bytes(data[:-1]),
            "reopened_exact": True,
            "file_identity_validated": True,
            "root_identity_validated": True,
        }
        return record, receipt


def validate_source_manifest(value: Mapping[str, Any], *, expected_stimulus_id: str | None = None) -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "schema",
            "stimulus_id",
            "opaque_media_id",
            "media_kind",
            "source_relative_path",
            "source_byte_count",
            "source_sha256",
            "coordinates",
            "derivatives",
        },
        "source manifest",
    )
    if value.get("schema") != "kira.resident_media_source_manifest.v4":
        raise ResidentMediaV4Error("source manifest schema changed")
    stimulus_id = _identifier(value.get("stimulus_id"), "stimulus_id")
    if expected_stimulus_id is not None and stimulus_id != expected_stimulus_id:
        raise ResidentMediaV4Error("source manifest stimulus mismatch")
    media_id = _identifier(value.get("opaque_media_id"), "opaque_media_id")
    media_kind = str(value.get("media_kind") or "")
    if media_kind not in {"PAGE", "VIDEO_INTERVAL", "AUDIO_TRACK"}:
        raise ResidentMediaV4Error("source manifest media_kind is invalid")
    source_path = _safe_relative_path(value.get("source_relative_path"), "source_relative_path")
    byte_count = _positive_int(value.get("source_byte_count"), "source_byte_count")
    source_sha = _sha(value.get("source_sha256"), "source_sha256")
    coordinates = value.get("coordinates")
    if not isinstance(coordinates, Mapping):
        raise ResidentMediaV4Error("coordinates must be an object")
    if media_kind == "PAGE":
        _exact_keys(coordinates, {"kind", "page_number"}, "page coordinates")
        if coordinates.get("kind") != "PAGE_NUMBER":
            raise ResidentMediaV4Error("page coordinate kind changed")
        clean_coordinates = {
            "kind": "PAGE_NUMBER",
            "page_number": _positive_int(coordinates.get("page_number"), "page_number", 1_000_000),
        }
    elif media_kind == "VIDEO_INTERVAL":
        _exact_keys(coordinates, {"kind", "start_ms", "end_ms"}, "video coordinates")
        if coordinates.get("kind") != "INTERVAL_MS":
            raise ResidentMediaV4Error("video coordinate kind changed")
        start = _nonnegative_int(coordinates.get("start_ms"), "start_ms")
        end = _positive_int(coordinates.get("end_ms"), "end_ms")
        if end <= start:
            raise ResidentMediaV4Error("video interval end must follow start")
        clean_coordinates = {"kind": "INTERVAL_MS", "start_ms": start, "end_ms": end}
    else:
        _exact_keys(
            coordinates,
            {"kind", "track_number", "start_ms", "end_ms"},
            "track coordinates",
        )
        if coordinates.get("kind") != "TRACK_INTERVAL_MS":
            raise ResidentMediaV4Error("track coordinate kind changed")
        track = _positive_int(coordinates.get("track_number"), "track_number", 1_000_000)
        start = _nonnegative_int(coordinates.get("start_ms"), "start_ms")
        end = _positive_int(coordinates.get("end_ms"), "end_ms")
        if end <= start:
            raise ResidentMediaV4Error("track interval end must follow start")
        clean_coordinates = {
            "kind": "TRACK_INTERVAL_MS",
            "track_number": track,
            "start_ms": start,
            "end_ms": end,
        }
    derivatives = value.get("derivatives")
    if not isinstance(derivatives, list) or not 1 <= len(derivatives) <= 32:
        raise ResidentMediaV4Error("source manifest needs bounded derivative identities")
    clean_derivatives: list[dict[str, Any]] = []
    roles: set[str] = set()
    paths: set[str] = set()
    for index, derivative in enumerate(derivatives):
        if not isinstance(derivative, Mapping):
            raise ResidentMediaV4Error("derivative must be an object")
        _exact_keys(
            derivative,
            {
                "schema",
                "derivative_id",
                "role",
                "relative_path",
                "byte_count",
                "sha256",
                "derived_from_source_sha256",
            },
            f"derivative {index}",
        )
        if derivative.get("schema") != "kira.resident_media_derivative_identity.v4":
            raise ResidentMediaV4Error("derivative schema changed")
        derivative_id = _identifier(derivative.get("derivative_id"), "derivative_id")
        role = _identifier(derivative.get("role"), "role")
        path = _safe_relative_path(derivative.get("relative_path"), "derivative relative_path")
        if role in roles or path in paths:
            raise ResidentMediaV4Error("derivative roles and paths must be unique")
        roles.add(role)
        paths.add(path)
        derived_from = _sha(derivative.get("derived_from_source_sha256"), "derived_from_source_sha256")
        if derived_from != source_sha:
            raise ResidentMediaV4Error("derivative is not bound to the exact source digest")
        clean_derivatives.append(
            {
                "schema": "kira.resident_media_derivative_identity.v4",
                "derivative_id": derivative_id,
                "role": role,
                "relative_path": path,
                "byte_count": _positive_int(derivative.get("byte_count"), "derivative byte_count"),
                "sha256": _sha(derivative.get("sha256"), "derivative sha256"),
                "derived_from_source_sha256": derived_from,
            }
        )
    clean_derivatives.sort(key=lambda item: (item["role"], item["derivative_id"], item["relative_path"]))
    clean = {
        "schema": "kira.resident_media_source_manifest.v4",
        "stimulus_id": stimulus_id,
        "opaque_media_id": media_id,
        "media_kind": media_kind,
        "source_relative_path": source_path,
        "source_byte_count": byte_count,
        "source_sha256": source_sha,
        "coordinates": clean_coordinates,
        "derivatives": clean_derivatives,
    }
    canonical_json_bytes(clean)
    return clean


class StimulusCatalog:
    """Immutable exact manifests accepted before a session begins."""

    def __init__(self, manifests: Sequence[Mapping[str, Any]]) -> None:
        if not isinstance(manifests, Sequence) or isinstance(manifests, (str, bytes)):
            raise ResidentMediaV4Error("manifest catalog must be a sequence")
        if len(manifests) != len(STIMULUS_ORDER):
            raise ResidentMediaV4Error("manifest catalog must cover the exact stimulus order")
        clean: list[dict[str, Any]] = []
        for expected, manifest in zip(STIMULUS_ORDER, manifests, strict=True):
            if not isinstance(manifest, Mapping):
                raise ResidentMediaV4Error("manifest catalog member must be an object")
            clean.append(validate_source_manifest(manifest, expected_stimulus_id=expected))
        self._manifests = tuple(clean)
        self._bytes = canonical_json_bytes(
            {"schema": "kira.resident_media_source_catalog.v4", "manifests": clean}
        )
        self.sha256 = sha256_bytes(self._bytes)

    def manifest(self, ordinal: int) -> dict[str, Any]:
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 0 <= ordinal < len(self._manifests):
            raise ResidentMediaV4Error("manifest ordinal is invalid")
        return strict_json_loads(canonical_json_bytes(self._manifests[ordinal]))

    def manifest_sha256(self, ordinal: int) -> str:
        return sha256_bytes(canonical_json_bytes(self._manifests[ordinal]))

    def as_record(self) -> dict[str, Any]:
        return strict_json_loads(self._bytes)


def _semantic_choice(text: str, phase: str) -> str:
    has_stop = bool(STOP_PATTERN.search(text))
    has_pause = bool(PAUSE_PATTERN.search(text))
    has_no = bool(NO_PATTERN.search(text))
    has_yes = bool(YES_PATTERN.search(text))
    has_continue = bool(CONTINUE_PATTERN.search(text))
    # Words such as "continue" can occur inside an explicit "do not
    # continue" stop phrase.  STOP therefore owns that occurrence, while a
    # genuinely separate affirmative or pause remains mixed/ambiguous.
    if has_stop and not (has_pause or has_yes):
        return "STOP"
    if phase == "INVITATION":
        positive = has_yes
        if has_no and not positive and not has_pause and not has_stop:
            return "NO"
        if positive and not has_no and not has_pause and not has_stop:
            return "YES"
    else:
        positive = has_continue or has_yes
        if has_no and not positive and not has_pause and not has_stop:
            return "STOP"
        if has_pause and not has_no and not positive and not has_stop:
            return "PAUSE"
        if positive and not has_no and not has_pause and not has_stop:
            return "CONTINUE"
    return "AMBIGUOUS_REQUIRES_NEW_TURN"


def validate_choice_observation(value: Mapping[str, Any], *, phase: str, prompt_sha256: str) -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "schema",
            "model_name",
            "model_digest",
            "model_call_count",
            "normal_model_route",
            "fallback_used",
            "prompt_sha256",
            "raw_reply",
            "final_reply",
            "transformations",
            "choice",
            "external_parent_observation_sha256",
        },
        "choice observation",
    )
    if value.get("schema") != "kira.resident_media_choice_observation.v4":
        raise ResidentMediaV4Error("choice observation schema changed")
    if value.get("model_name") != EXACT_MODEL or str(value.get("model_digest") or "").lower() != EXACT_DIGEST:
        raise ResidentMediaV4Error("choice observation did not name exact Qwen")
    if value.get("model_call_count") != 1 or value.get("normal_model_route") is not True:
        raise ResidentMediaV4Error("choice observation requires one normal model call")
    if value.get("fallback_used") is not False:
        raise ResidentMediaV4Error("fallback cannot decide a voluntary choice")
    if _sha(value.get("prompt_sha256"), "prompt_sha256") != prompt_sha256:
        raise ResidentMediaV4Error("choice prompt binding changed")
    raw = _bounded_text(value.get("raw_reply"), "raw_reply")
    final = _bounded_text(value.get("final_reply"), "final_reply")
    transformations = value.get("transformations")
    if not isinstance(transformations, list) or len(transformations) > 32 or any(
        not isinstance(item, Mapping) for item in transformations
    ):
        raise ResidentMediaV4Error("choice transformations are malformed")
    if len(canonical_json_bytes(transformations)) > 65_536:
        raise ResidentMediaV4Error("choice transformations are oversized")
    choice = str(value.get("choice") or "")
    if choice not in CHOICES:
        raise ResidentMediaV4Error("choice is not an exact enum")
    allowed = {"YES", "NO", "STOP"} if phase == "INVITATION" else {"CONTINUE", "PAUSE", "STOP"}
    if choice not in allowed:
        raise ResidentMediaV4Error("choice is invalid for this phase")
    raw_semantic = _semantic_choice(raw, phase)
    final_semantic = _semantic_choice(final, phase)
    if raw_semantic == "AMBIGUOUS_REQUIRES_NEW_TURN" or final_semantic == "AMBIGUOUS_REQUIRES_NEW_TURN":
        raise ResidentMediaV4Error("mixed, ambiguous, or self-correcting choice requires a new turn")
    if raw_semantic != final_semantic:
        raise ResidentMediaV4Error("raw and final choice differ; a new turn is required")
    if choice != raw_semantic:
        raise ResidentMediaV4Error("structured choice cannot override the person's words")
    return {
        "schema": "kira.resident_media_choice_observation.v4",
        "model_name": EXACT_MODEL,
        "model_digest": EXACT_DIGEST,
        "model_call_count": 1,
        "normal_model_route": True,
        "fallback_used": False,
        "prompt_sha256": prompt_sha256,
        "raw_reply": raw,
        "final_reply": final,
        "transformations": strict_json_loads(canonical_json_bytes(transformations)),
        "choice": choice,
        "external_parent_observation_sha256": _sha(
            value.get("external_parent_observation_sha256"),
            "external_parent_observation_sha256",
        ),
    }


@dataclass(frozen=True, slots=True)
class CapabilityBinding:
    session_id: str
    person_id: str
    stimulus_id: str
    ordinal: int
    session_event_sequence: int
    choice_event_sha256: str
    source_manifest_sha256: str
    source_byte_count: int
    source_coordinates_sha256: str
    derivative_set_sha256: str
    parent_process_identity_sha256: str

    def as_record(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "person_id": self.person_id,
            "stimulus_id": self.stimulus_id,
            "ordinal": self.ordinal,
            "session_event_sequence": self.session_event_sequence,
            "choice_event_sha256": self.choice_event_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_byte_count": self.source_byte_count,
            "source_coordinates_sha256": self.source_coordinates_sha256,
            "derivative_set_sha256": self.derivative_set_sha256,
            "parent_process_identity_sha256": self.parent_process_identity_sha256,
        }


class DurableCapabilityAuthority:
    """HMAC-bound, durable, one-use capability ledger for a later parent.

    The secret and asserted process identity must be owned by the future
    external parent.  This static object proves exact cryptographic and disk
    semantics only; it does not establish that the caller really is that
    parent process.
    """

    def __init__(
        self,
        *,
        root: Path,
        secret_key: bytes,
        issuer_id: str,
        parent_process_identity_sha256: str,
        clock: SystemClockAuthority,
    ) -> None:
        if not isinstance(secret_key, bytes) or len(secret_key) < 32:
            raise ResidentMediaV4Error("capability secret must be at least 256 bits")
        if type(clock) is not SystemClockAuthority:
            raise ResidentMediaV4Error("capability authority requires the internal system clock")
        self.store = DurableDirectory(root)
        self._key = secret_key
        self.issuer_id = _identifier(issuer_id, "issuer_id")
        self.parent_process_identity_sha256 = _sha(
            parent_process_identity_sha256, "parent_process_identity_sha256"
        )
        self.clock = clock

    @staticmethod
    def _issue_name(binding_sha256: str) -> str:
        return f"capability_issue_binding_{binding_sha256}.json"

    @staticmethod
    def _consume_name(authorization_id: str) -> str:
        return f"capability_consumed_{authorization_id}.json"

    def _signature(self, unsigned: Mapping[str, Any]) -> str:
        return hmac.new(self._key, canonical_json_bytes(dict(unsigned)), hashlib.sha256).hexdigest()

    def issue(self, binding: CapabilityBinding, *, ttl_seconds: int = 30) -> dict[str, Any]:
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= MAX_CAPABILITY_TTL_SECONDS:
            raise ResidentMediaV4Error("capability TTL is outside the static bound")
        if binding.parent_process_identity_sha256 != self.parent_process_identity_sha256:
            raise ResidentMediaV4Error("capability process binding changed")
        issued = self.clock.sample()
        authorization_id = secrets.token_hex(32)
        binding_sha256 = sha256_record(binding.as_record())
        unsigned = {
            "schema": "kira.resident_media_capability.v4",
            "issuer_id": self.issuer_id,
            "authorization_id": authorization_id,
            "binding_sha256": binding_sha256,
            **binding.as_record(),
            "clock_id_sha256": issued.clock_id_sha256,
            "issued_at_utc": issued.utc_text,
            "expires_at_utc": _utc_text(issued.utc + timedelta(seconds=ttl_seconds)),
            "issued_monotonic_ns": issued.monotonic_ns,
            "expires_monotonic_ns": issued.monotonic_ns + ttl_seconds * 1_000_000_000,
            "ttl_seconds": ttl_seconds,
        }
        token = {**unsigned, "signature_sha256": self._signature(unsigned)}
        token_sha = sha256_record(token)
        issue_record = {
            "schema": "kira.resident_media_capability_issue.v4",
            "authorization_id": authorization_id,
            "binding_sha256": binding_sha256,
            "token_sha256": token_sha,
            "token": token,
        }
        self.store.exclusive_append(self._issue_name(binding_sha256), issue_record)
        reopened, _ = self.store.read_exact(self._issue_name(binding_sha256))
        if reopened != issue_record:
            raise ResidentMediaV4Error("issued capability did not reopen exactly")
        return strict_json_loads(canonical_json_bytes(token))

    def _validate_token(
        self,
        token: Mapping[str, Any],
        binding: CapabilityBinding,
        *,
        require_unconsumed: bool,
        sample_now: bool,
    ) -> tuple[dict[str, Any], ClockSample | None]:
        expected = {
            "schema",
            "issuer_id",
            "authorization_id",
            "binding_sha256",
            *binding.as_record().keys(),
            "clock_id_sha256",
            "issued_at_utc",
            "expires_at_utc",
            "issued_monotonic_ns",
            "expires_monotonic_ns",
            "ttl_seconds",
            "signature_sha256",
        }
        _exact_keys(token, set(expected), "capability token")
        if token.get("schema") != "kira.resident_media_capability.v4" or token.get("issuer_id") != self.issuer_id:
            raise ResidentMediaV4Error("capability issuer/schema mismatch")
        authorization_id = _sha(token.get("authorization_id"), "authorization_id")
        clean_binding = binding.as_record()
        binding_sha256 = sha256_record(clean_binding)
        if token.get("binding_sha256") != binding_sha256:
            raise ResidentMediaV4Error("capability binding digest changed")
        for field, expected_value in clean_binding.items():
            if token.get(field) != expected_value:
                raise ResidentMediaV4Error(f"capability exact binding changed: {field}")
        if token.get("clock_id_sha256") != SystemClockAuthority.CLOCK_ID_SHA256:
            raise ResidentMediaV4Error("capability clock identity changed")
        ttl = _positive_int(token.get("ttl_seconds"), "ttl_seconds", MAX_CAPABILITY_TTL_SECONDS)
        issued_utc = _utc_datetime(token.get("issued_at_utc"), "issued_at_utc")
        expires_utc = _utc_datetime(token.get("expires_at_utc"), "expires_at_utc")
        issued_mono = _positive_int(token.get("issued_monotonic_ns"), "issued_monotonic_ns")
        expires_mono = _positive_int(token.get("expires_monotonic_ns"), "expires_monotonic_ns")
        if expires_utc != issued_utc + timedelta(seconds=ttl):
            raise ResidentMediaV4Error("capability UTC expiry relation changed")
        if expires_mono != issued_mono + ttl * 1_000_000_000:
            raise ResidentMediaV4Error("capability monotonic expiry relation changed")
        unsigned = {key: token[key] for key in token if key != "signature_sha256"}
        supplied_signature = _sha(token.get("signature_sha256"), "signature_sha256")
        if not hmac.compare_digest(supplied_signature, self._signature(unsigned)):
            raise ResidentMediaV4Error("capability signature is invalid")
        issue_name = self._issue_name(binding_sha256)
        issue_record, _ = self.store.read_exact(issue_name)
        expected_issue = {
            "schema": "kira.resident_media_capability_issue.v4",
            "authorization_id": authorization_id,
            "binding_sha256": binding_sha256,
            "token_sha256": sha256_record(token),
            "token": strict_json_loads(canonical_json_bytes(token)),
        }
        if issue_record != expected_issue:
            raise ResidentMediaV4Error("durable capability issue record changed")
        consume_path = self.store.root / self._consume_name(authorization_id)
        if require_unconsumed and consume_path.exists():
            raise ResidentMediaV4Error("capability was already consumed")
        now: ClockSample | None = None
        if sample_now:
            now = self.clock.sample()
            self.clock.assert_not_future(issued_utc, "capability issue time")
            if now.utc < issued_utc or now.utc > expires_utc:
                raise ResidentMediaV4Error("capability is not fresh in UTC")
            if now.monotonic_ns < issued_mono or now.monotonic_ns > expires_mono:
                raise ResidentMediaV4Error("capability is not fresh on the monotonic clock")
        return strict_json_loads(canonical_json_bytes(token)), now

    def verify_unconsumed(self, token: Mapping[str, Any], binding: CapabilityBinding) -> dict[str, Any]:
        clean, _ = self._validate_token(token, binding, require_unconsumed=True, sample_now=True)
        return clean

    def consume(
        self,
        token: Mapping[str, Any],
        binding: CapabilityBinding,
        *,
        planned_authorization_core_sha256: str,
    ) -> dict[str, Any]:
        clean, now = self._validate_token(token, binding, require_unconsumed=True, sample_now=True)
        if now is None:
            raise ResidentMediaV4Error("capability consumption lacks trusted time")
        authorization_id = clean["authorization_id"]
        record = {
            "schema": "kira.resident_media_capability_consumption.v4",
            "authorization_id": authorization_id,
            "token_sha256": sha256_record(clean),
            "session_id": binding.session_id,
            "person_id": binding.person_id,
            "stimulus_id": binding.stimulus_id,
            "ordinal": binding.ordinal,
            "session_event_sequence": binding.session_event_sequence,
            "planned_authorization_core_sha256": _sha(
                planned_authorization_core_sha256, "planned_authorization_core_sha256"
            ),
            "consumed_at_utc": now.utc_text,
            "consumed_monotonic_ns": now.monotonic_ns,
            "clock_id_sha256": now.clock_id_sha256,
        }
        receipt = self.store.exclusive_append(self._consume_name(authorization_id), record)
        reopened, reopen_receipt = self.store.read_exact(self._consume_name(authorization_id))
        if reopened != record or receipt["record_sha256"] != reopen_receipt["record_sha256"]:
            raise ResidentMediaV4Error("capability consumption did not reopen exactly")
        return {
            "schema": "kira.resident_media_capability_consumption_receipt.v4",
            "authorization_id": authorization_id,
            "consumption_record_sha256": receipt["record_sha256"],
            "planned_authorization_core_sha256": record["planned_authorization_core_sha256"],
            "consumed_at_utc": record["consumed_at_utc"],
            "consumed_monotonic_ns": record["consumed_monotonic_ns"],
            "reopened_exact": True,
            "fsync_completed": True,
        }

    def verify_consumption_receipt(
        self,
        token: Mapping[str, Any],
        binding: CapabilityBinding,
        receipt: Mapping[str, Any],
        *,
        planned_authorization_core_sha256: str,
    ) -> None:
        clean, _ = self._validate_token(token, binding, require_unconsumed=False, sample_now=False)
        _exact_keys(
            receipt,
            {
                "schema",
                "authorization_id",
                "consumption_record_sha256",
                "planned_authorization_core_sha256",
                "consumed_at_utc",
                "consumed_monotonic_ns",
                "reopened_exact",
                "fsync_completed",
            },
            "capability consumption receipt",
        )
        if receipt.get("schema") != "kira.resident_media_capability_consumption_receipt.v4":
            raise ResidentMediaV4Error("consumption receipt schema changed")
        if receipt.get("authorization_id") != clean["authorization_id"]:
            raise ResidentMediaV4Error("consumption receipt authorization changed")
        planned = _sha(planned_authorization_core_sha256, "planned_authorization_core_sha256")
        if receipt.get("planned_authorization_core_sha256") != planned:
            raise ResidentMediaV4Error("consumption receipt authorization binding changed")
        if receipt.get("reopened_exact") is not True or receipt.get("fsync_completed") is not True:
            raise ResidentMediaV4Error("consumption receipt lacks durability gates")
        consumption, reopen = self.store.read_exact(self._consume_name(clean["authorization_id"]))
        if _sha(receipt.get("consumption_record_sha256"), "consumption_record_sha256") != reopen["record_sha256"]:
            raise ResidentMediaV4Error("consumption receipt digest changed")
        expected_consumption = {
            "schema": "kira.resident_media_capability_consumption.v4",
            "authorization_id": clean["authorization_id"],
            "token_sha256": sha256_record(clean),
            "session_id": binding.session_id,
            "person_id": binding.person_id,
            "stimulus_id": binding.stimulus_id,
            "ordinal": binding.ordinal,
            "session_event_sequence": binding.session_event_sequence,
            "planned_authorization_core_sha256": planned,
            "consumed_at_utc": receipt.get("consumed_at_utc"),
            "consumed_monotonic_ns": receipt.get("consumed_monotonic_ns"),
            "clock_id_sha256": SystemClockAuthority.CLOCK_ID_SHA256,
        }
        if consumption != expected_consumption:
            raise ResidentMediaV4Error("durable capability consumption record changed")
        consumed_utc = _utc_datetime(consumption["consumed_at_utc"], "consumed_at_utc")
        consumed_mono = _positive_int(consumption["consumed_monotonic_ns"], "consumed_monotonic_ns")
        issued_utc = _utc_datetime(clean["issued_at_utc"], "issued_at_utc")
        expires_utc = _utc_datetime(clean["expires_at_utc"], "expires_at_utc")
        issued_mono = _positive_int(clean["issued_monotonic_ns"], "issued_monotonic_ns")
        expires_mono = _positive_int(clean["expires_monotonic_ns"], "expires_monotonic_ns")
        if not issued_utc <= consumed_utc <= expires_utc:
            raise ResidentMediaV4Error("durable consumption UTC freshness changed")
        if not issued_mono <= consumed_mono <= expires_mono:
            raise ResidentMediaV4Error("durable consumption monotonic freshness changed")


class DurableSessionJournal:
    EVENT_NAME = re.compile(r"event_([0-9]{6})\.json")

    def __init__(self, root: Path) -> None:
        self.store = DurableDirectory(root)

    def append(self, sequence: int, record: Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(sequence, bool) or not isinstance(sequence, int) or not 0 <= sequence < MAX_EVENT_COUNT:
            raise ResidentMediaV4Error("session event sequence is invalid")
        return self.store.exclusive_append(f"event_{sequence:06d}.json", record)

    def load_contiguous(self) -> list[dict[str, Any]]:
        names: list[tuple[int, str]] = []
        for path in self.store.root.iterdir():
            match = self.EVENT_NAME.fullmatch(path.name)
            if match:
                names.append((int(match.group(1)), path.name))
            else:
                raise ResidentMediaV4Error(f"unexpected session journal entry: {path.name}")
        names.sort()
        if len(names) > MAX_EVENT_COUNT:
            raise ResidentMediaV4Error("session journal has too many events")
        if [sequence for sequence, _ in names] != list(range(len(names))):
            raise ResidentMediaV4Error("session journal sequence is not contiguous")
        return [self.store.read_exact(name)[0] for _, name in names]


class VoluntaryMediaState:
    """Durable static sequencing; never a live-media authorization by itself."""

    def __init__(
        self,
        *,
        session_id: str,
        catalog: StimulusCatalog,
        journal: DurableSessionJournal,
        capability_authority: DurableCapabilityAuthority,
        clock: SystemClockAuthority,
        parent_process_identity_sha256: str,
        create: bool,
    ) -> None:
        if not re.fullmatch(r"session_[0-9a-f]{32}", session_id):
            raise ResidentMediaV4Error("session_id format is invalid")
        if type(clock) is not SystemClockAuthority:
            raise ResidentMediaV4Error("state requires the internal system clock")
        self.session_id = session_id
        self.catalog = catalog
        self.journal = journal
        self.capability_authority = capability_authority
        self.clock = clock
        self.parent_process_identity_sha256 = _sha(
            parent_process_identity_sha256, "parent_process_identity_sha256"
        )
        if self.parent_process_identity_sha256 != capability_authority.parent_process_identity_sha256:
            raise ResidentMediaV4Error("state and capability process bindings differ")
        self._next_ordinal = 0
        self._next_event_sequence = 1
        self._last_event_sha256: str | None = None
        self._last_event_utc: datetime | None = None
        self._last_event_monotonic_ns: int | None = None
        self._last_choice_event_sha256: str | None = None
        self._last_choice_utc: datetime | None = None
        self._last_choice_monotonic_ns: int | None = None
        self._pending_reservation: dict[str, Any] | None = None
        self._choice_required_phase = "INVITATION"
        self._paused = False
        self._stopped = False
        self._engineering_finished = False
        events = journal.load_contiguous()
        if create:
            if events:
                raise ResidentMediaV4Error("new session journal is not empty")
            self._append_genesis()
            events = journal.load_contiguous()
        if not events:
            raise ResidentMediaV4Error("session journal has no durable genesis")
        self._restore(events)

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        catalog: StimulusCatalog,
        journal: DurableSessionJournal,
        capability_authority: DurableCapabilityAuthority,
        clock: SystemClockAuthority,
        parent_process_identity_sha256: str,
    ) -> "VoluntaryMediaState":
        return cls(
            session_id=session_id,
            catalog=catalog,
            journal=journal,
            capability_authority=capability_authority,
            clock=clock,
            parent_process_identity_sha256=parent_process_identity_sha256,
            create=True,
        )

    @classmethod
    def restore(
        cls,
        *,
        session_id: str,
        catalog: StimulusCatalog,
        journal: DurableSessionJournal,
        capability_authority: DurableCapabilityAuthority,
        clock: SystemClockAuthority,
        parent_process_identity_sha256: str,
    ) -> "VoluntaryMediaState":
        return cls(
            session_id=session_id,
            catalog=catalog,
            journal=journal,
            capability_authority=capability_authority,
            clock=clock,
            parent_process_identity_sha256=parent_process_identity_sha256,
            create=False,
        )

    def _event(
        self,
        *,
        event_type: str,
        sequence: int,
        sample: ClockSample,
        previous_event_sha256: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_session_event.v4",
            "event_type": event_type,
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "sequence": sequence,
            "recorded_at_utc": sample.utc_text,
            "recorded_monotonic_ns": sample.monotonic_ns,
            "clock_id_sha256": sample.clock_id_sha256,
            "previous_event_sha256": previous_event_sha256,
            "payload": strict_json_loads(canonical_json_bytes(payload)),
        }

    def _append_genesis(self) -> None:
        sample = self.clock.sample()
        payload = {
            "schema": "kira.resident_media_session_genesis.v4",
            "catalog_sha256": self.catalog.sha256,
            "capability_issuer_id": self.capability_authority.issuer_id,
            "parent_process_identity_sha256": self.parent_process_identity_sha256,
            "live_execution_allowed": False,
            "person_experience_claimed": False,
            "automatic_memory_or_preference_created": False,
        }
        record = self._event(
            event_type="SESSION_CREATED",
            sequence=0,
            sample=sample,
            previous_event_sha256=None,
            payload=payload,
        )
        self.journal.append(0, record)

    def _validate_event_envelope(
        self,
        record: Mapping[str, Any],
        *,
        expected_sequence: int,
        previous_sha: str | None,
        previous_utc: datetime | None,
        previous_mono: int | None,
    ) -> tuple[str, datetime, int]:
        _exact_keys(
            record,
            {
                "schema",
                "event_type",
                "session_id",
                "person_id",
                "sequence",
                "recorded_at_utc",
                "recorded_monotonic_ns",
                "clock_id_sha256",
                "previous_event_sha256",
                "payload",
            },
            "session event",
        )
        if record.get("schema") != "kira.resident_media_session_event.v4":
            raise ResidentMediaV4Error("session event schema changed")
        if record.get("session_id") != self.session_id or record.get("person_id") != PERSON_ID:
            raise ResidentMediaV4Error("session event identity changed")
        if record.get("sequence") != expected_sequence or record.get("previous_event_sha256") != previous_sha:
            raise ResidentMediaV4Error("session event chain changed")
        if record.get("clock_id_sha256") != SystemClockAuthority.CLOCK_ID_SHA256:
            raise ResidentMediaV4Error("session event clock identity changed")
        utc_value = _utc_datetime(record.get("recorded_at_utc"), "recorded_at_utc")
        self.clock.assert_not_future(utc_value, "session event time")
        mono = _positive_int(record.get("recorded_monotonic_ns"), "recorded_monotonic_ns")
        if previous_utc is not None and utc_value < previous_utc:
            raise ResidentMediaV4Error("session UTC order regressed")
        if previous_mono is not None and mono <= previous_mono:
            raise ResidentMediaV4Error("session monotonic order did not advance")
        if not isinstance(record.get("payload"), Mapping):
            raise ResidentMediaV4Error("session event payload must be an object")
        return _identifier(record.get("event_type"), "event_type"), utc_value, mono

    def _restore(self, events: Sequence[Mapping[str, Any]]) -> None:
        previous_sha: str | None = None
        previous_utc: datetime | None = None
        previous_mono: int | None = None
        for sequence, event in enumerate(events):
            event_type, event_utc, event_mono = self._validate_event_envelope(
                event,
                expected_sequence=sequence,
                previous_sha=previous_sha,
                previous_utc=previous_utc,
                previous_mono=previous_mono,
            )
            payload = event["payload"]
            event_digest = sha256_record(event)
            # Reconstruct the exact pre-event state used by capability and
            # hash-chain checks.  The current event is not committed in state
            # until its payload validates.
            self._next_event_sequence = sequence
            self._last_event_sha256 = previous_sha
            self._last_event_utc = previous_utc
            self._last_event_monotonic_ns = previous_mono
            if sequence == 0:
                if event_type != "SESSION_CREATED":
                    raise ResidentMediaV4Error("first event is not session genesis")
                expected_genesis = {
                    "schema": "kira.resident_media_session_genesis.v4",
                    "catalog_sha256": self.catalog.sha256,
                    "capability_issuer_id": self.capability_authority.issuer_id,
                    "parent_process_identity_sha256": self.parent_process_identity_sha256,
                    "live_execution_allowed": False,
                    "person_experience_claimed": False,
                    "automatic_memory_or_preference_created": False,
                }
                if payload != expected_genesis:
                    raise ResidentMediaV4Error("durable session genesis binding changed")
            elif event_type == "CHOICE_ACCEPTED":
                self._restore_choice(payload, event_utc, event_mono, event_digest)
            elif event_type == "PRESENTATION_RESERVED":
                self._restore_reservation(payload, event_digest)
            elif event_type == "PRESENTATION_RECORDED":
                self._restore_presentation(payload, event_utc, event_mono)
            elif event_type == "ENGINEERING_FINISHED":
                self._restore_finished(payload)
            else:
                raise ResidentMediaV4Error("session event type/order is invalid")
            previous_sha = event_digest
            previous_utc = event_utc
            previous_mono = event_mono
        self._last_event_sha256 = previous_sha
        self._last_event_utc = previous_utc
        self._last_event_monotonic_ns = previous_mono
        self._next_event_sequence = len(events)

    def _restore_choice(
        self,
        payload: Mapping[str, Any],
        event_utc: datetime,
        event_mono: int,
        event_digest: str,
    ) -> None:
        _exact_keys(payload, {"schema", "phase", "observation"}, "choice event payload")
        if payload.get("schema") != "kira.resident_media_choice_event.v4":
            raise ResidentMediaV4Error("choice event payload schema changed")
        if (
            self._stopped
            or self._engineering_finished
            or self._last_choice_event_sha256 is not None
            or self._pending_reservation is not None
        ):
            raise ResidentMediaV4Error("choice event appears in an invalid durable state")
        phase = str(payload.get("phase") or "")
        if phase != self._choice_required_phase:
            raise ResidentMediaV4Error("durable choice phase changed")
        observation = payload.get("observation")
        if not isinstance(observation, Mapping):
            raise ResidentMediaV4Error("durable choice observation is missing")
        clean = validate_choice_observation(
            observation,
            phase=phase,
            prompt_sha256=_sha(observation.get("prompt_sha256"), "prompt_sha256"),
        )
        self._apply_choice(
            clean["choice"], event_utc, event_mono, pending_digest_marker=event_digest
        )

    def _restore_reservation(self, payload: Mapping[str, Any], event_digest: str) -> None:
        if self._last_choice_event_sha256 is None or self._pending_reservation is not None:
            raise ResidentMediaV4Error("reservation lacks one current accepted choice")
        self._validate_reservation_payload(payload)
        core = payload["authorization_core"]
        self._pending_reservation = {
            "schema": "kira.resident_media_presentation_reservation.v4",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "stimulus_id": core["stimulus_id"],
            "ordinal": core["ordinal"],
            "reservation_event_sha256": event_digest,
            "authorization_core_sha256": payload["authorization_core_sha256"],
            "authorization_token_sha256": core["authorization_token_sha256"],
            "capability_consumption_record_sha256": payload["capability_consumption_receipt"][
                "consumption_record_sha256"
            ],
        }

    def _restore_presentation(self, payload: Mapping[str, Any], event_utc: datetime, event_mono: int) -> None:
        if self._last_choice_event_sha256 is None or self._pending_reservation is None:
            raise ResidentMediaV4Error("presentation lacks a durable consumed reservation")
        self._validate_presentation_payload(payload, restore=True)
        self._next_ordinal += 1
        self._choice_required_phase = f"AFTER_{STIMULUS_ORDER[self._next_ordinal - 1]}"
        self._last_choice_event_sha256 = None
        self._last_choice_utc = None
        self._last_choice_monotonic_ns = None
        self._pending_reservation = None
        self._paused = False

    def _restore_finished(self, payload: Mapping[str, Any]) -> None:
        expected = {
            "schema": "kira.resident_media_engineering_finished.v4",
            "presented_stimulus_count": len(STIMULUS_ORDER),
            "person_experience_claimed": False,
            "automatic_memory_or_preference_created": False,
            "awake_owner_post_acknowledged": False,
        }
        if payload != expected or self._next_ordinal != len(STIMULUS_ORDER):
            raise ResidentMediaV4Error("engineering-finished record is invalid")
        self._engineering_finished = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def next_required_phase(self) -> str:
        return self._choice_required_phase

    def _require_new_event_order(self, sample: ClockSample) -> None:
        if self._last_event_utc is not None and sample.utc < self._last_event_utc:
            raise ResidentMediaV4Error("trusted session UTC order regressed")
        if self._last_event_monotonic_ns is not None and sample.monotonic_ns <= self._last_event_monotonic_ns:
            raise ResidentMediaV4Error("trusted session monotonic order did not advance")

    def _commit_event(self, event_type: str, payload: Mapping[str, Any], sample: ClockSample) -> tuple[str, dict[str, Any]]:
        self._require_new_event_order(sample)
        record = self._event(
            event_type=event_type,
            sequence=self._next_event_sequence,
            sample=sample,
            previous_event_sha256=self._last_event_sha256,
            payload=payload,
        )
        receipt = self.journal.append(self._next_event_sequence, record)
        reopened, reopen_receipt = self.journal.store.read_exact(f"event_{self._next_event_sequence:06d}.json")
        if reopened != record or receipt["record_sha256"] != reopen_receipt["record_sha256"]:
            raise ResidentMediaV4Error("session event did not reopen exactly")
        digest = sha256_record(record)
        if digest != receipt["record_sha256"]:
            raise ResidentMediaV4Error("session event identity digest changed")
        return digest, record

    def _apply_choice(
        self,
        choice: str,
        event_utc: datetime,
        event_mono: int,
        *,
        pending_digest_marker: str,
    ) -> None:
        if choice in {"NO", "STOP"}:
            self._stopped = True
            self._paused = False
            self._last_choice_event_sha256 = None
        elif choice == "PAUSE":
            self._paused = True
            self._last_choice_event_sha256 = None
        else:
            self._paused = False
            self._last_choice_event_sha256 = pending_digest_marker
            self._last_choice_utc = event_utc
            self._last_choice_monotonic_ns = event_mono

    def accept_choice(self, observation: Mapping[str, Any], *, prompt_sha256: str) -> str:
        if (
            self._stopped
            or self._engineering_finished
            or self._last_choice_event_sha256 is not None
            or self._pending_reservation is not None
        ):
            raise ResidentMediaV4Error("choice is not allowed in current state")
        clean = validate_choice_observation(
            observation,
            phase=self._choice_required_phase,
            prompt_sha256=_sha(prompt_sha256, "prompt_sha256"),
        )
        sample = self.clock.sample()
        payload = {
            "schema": "kira.resident_media_choice_event.v4",
            "phase": self._choice_required_phase,
            "observation": clean,
        }
        digest, _ = self._commit_event("CHOICE_ACCEPTED", payload, sample)
        # State changes only after exclusive append, fsync, reopen, and identity checks.
        self._last_event_sha256 = digest
        self._last_event_utc = sample.utc
        self._last_event_monotonic_ns = sample.monotonic_ns
        self._next_event_sequence += 1
        self._apply_choice(
            clean["choice"], sample.utc, sample.monotonic_ns, pending_digest_marker=digest
        )
        return digest

    def expected_capability_binding(self) -> CapabilityBinding:
        if (
            self._stopped
            or self._paused
            or self._engineering_finished
            or self._last_choice_event_sha256 is None
            or self._last_choice_utc is None
            or self._last_choice_monotonic_ns is None
            or self._pending_reservation is not None
        ):
            raise ResidentMediaV4Error("next stimulus has no current accepted choice")
        if self._next_ordinal >= len(STIMULUS_ORDER):
            raise ResidentMediaV4Error("all bounded stimuli are already complete")
        manifest = self.catalog.manifest(self._next_ordinal)
        return CapabilityBinding(
            session_id=self.session_id,
            person_id=PERSON_ID,
            stimulus_id=manifest["stimulus_id"],
            ordinal=self._next_ordinal,
            session_event_sequence=self._next_event_sequence,
            choice_event_sha256=self._last_choice_event_sha256,
            source_manifest_sha256=self.catalog.manifest_sha256(self._next_ordinal),
            source_byte_count=manifest["source_byte_count"],
            source_coordinates_sha256=sha256_bytes(canonical_json_bytes(manifest["coordinates"])),
            derivative_set_sha256=sha256_bytes(canonical_json_bytes(manifest["derivatives"])),
            parent_process_identity_sha256=self.parent_process_identity_sha256,
        )

    def verify_authorization(self, token: Mapping[str, Any]) -> dict[str, Any]:
        binding = self.expected_capability_binding()
        clean = self.capability_authority.verify_unconsumed(token, binding)
        issued_utc = _utc_datetime(clean["issued_at_utc"], "issued_at_utc")
        issued_mono = _positive_int(clean["issued_monotonic_ns"], "issued_monotonic_ns")
        if self._last_choice_utc is None or self._last_choice_monotonic_ns is None:
            raise ResidentMediaV4Error("authorization lacks a durable choice time")
        if issued_utc < self._last_choice_utc or issued_mono <= self._last_choice_monotonic_ns:
            raise ResidentMediaV4Error("authorization was not issued after the durable choice")
        if issued_utc > self._last_choice_utc + timedelta(seconds=MAX_CHOICE_TO_CAPABILITY_SECONDS):
            raise ResidentMediaV4Error("authorization was issued too long after the choice")
        if issued_mono > self._last_choice_monotonic_ns + MAX_CHOICE_TO_CAPABILITY_SECONDS * 1_000_000_000:
            raise ResidentMediaV4Error("authorization exceeded the monotonic choice window")
        return clean

    def _authorization_core(self, token: Mapping[str, Any]) -> dict[str, Any]:
        binding = self.expected_capability_binding()
        clean_token = self.verify_authorization(token)
        manifest = self.catalog.manifest(self._next_ordinal)
        return {
            "schema": "kira.resident_media_authorization_core.v4",
            **binding.as_record(),
            "source_manifest": manifest,
            "authorization_token": clean_token,
            "authorization_token_sha256": sha256_record(clean_token),
            "live_execution_allowed_by_static_core": False,
            "external_parent_must_treat_reservation_as_precondition": True,
        }

    def _validate_reservation_payload(self, payload: Mapping[str, Any]) -> None:
        _exact_keys(
            payload,
            {
                "schema",
                "authorization_core",
                "authorization_core_sha256",
                "capability_consumption_receipt",
            },
            "reservation event payload",
        )
        if payload.get("schema") != "kira.resident_media_presentation_reserved_event.v4":
            raise ResidentMediaV4Error("reservation event schema changed")
        core = payload.get("authorization_core")
        receipt = payload.get("capability_consumption_receipt")
        if not isinstance(core, Mapping) or not isinstance(receipt, Mapping):
            raise ResidentMediaV4Error("reservation durable evidence is incomplete")
        core_sha = sha256_record(core)
        if payload.get("authorization_core_sha256") != core_sha:
            raise ResidentMediaV4Error("authorization core digest changed")
        binding = self.expected_capability_binding()
        expected_core = {
            "schema": "kira.resident_media_authorization_core.v4",
            **binding.as_record(),
            "source_manifest": self.catalog.manifest(self._next_ordinal),
            "authorization_token": core.get("authorization_token"),
            "authorization_token_sha256": core.get("authorization_token_sha256"),
            "live_execution_allowed_by_static_core": False,
            "external_parent_must_treat_reservation_as_precondition": True,
        }
        if core != expected_core:
            raise ResidentMediaV4Error("authorization core exact binding changed")
        token = core.get("authorization_token")
        if not isinstance(token, Mapping) or core.get("authorization_token_sha256") != sha256_record(token):
            raise ResidentMediaV4Error("authorization token identity changed")
        self.capability_authority.verify_consumption_receipt(
            token,
            binding,
            receipt,
            planned_authorization_core_sha256=core_sha,
        )

    def reserve_presentation(self, token: Mapping[str, Any]) -> dict[str, Any]:
        """Durably consume one capability before any future parent may act."""

        core = self._authorization_core(token)
        core_sha = sha256_record(core)
        binding = self.expected_capability_binding()
        receipt = self.capability_authority.consume(
            token,
            binding,
            planned_authorization_core_sha256=core_sha,
        )
        consumed_utc = _utc_datetime(receipt["consumed_at_utc"], "consumed_at_utc")
        consumed_mono = _positive_int(receipt["consumed_monotonic_ns"], "consumed_monotonic_ns")
        sample = self.clock.sample()
        if sample.utc < consumed_utc or sample.monotonic_ns <= consumed_mono:
            raise ResidentMediaV4Error("reservation journal time did not follow capability consumption")
        payload = {
            "schema": "kira.resident_media_presentation_reserved_event.v4",
            "authorization_core": core,
            "authorization_core_sha256": core_sha,
            "capability_consumption_receipt": receipt,
        }
        self._validate_reservation_payload(payload)
        digest, _ = self._commit_event("PRESENTATION_RESERVED", payload, sample)
        reservation = {
            "schema": "kira.resident_media_presentation_reservation.v4",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "stimulus_id": core["stimulus_id"],
            "ordinal": core["ordinal"],
            "reservation_event_sha256": digest,
            "authorization_core_sha256": core_sha,
            "authorization_token_sha256": core["authorization_token_sha256"],
            "capability_consumption_record_sha256": receipt["consumption_record_sha256"],
        }
        # Pending state changes only after capability consumption and the
        # reservation event each passed append/fsync/reopen/identity checks.
        self._last_event_sha256 = digest
        self._last_event_utc = sample.utc
        self._last_event_monotonic_ns = sample.monotonic_ns
        self._next_event_sequence += 1
        self._pending_reservation = reservation
        return strict_json_loads(canonical_json_bytes(reservation))

    def _presentation_core(
        self,
        observation: Mapping[str, Any],
        reservation: Mapping[str, Any],
    ) -> dict[str, Any]:
        _exact_keys(
            observation,
            {
                "schema",
                "source_manifest",
                "engineering_output_completed",
                "machine_visual_interpretation_created",
                "machine_audio_cue_created",
                "machine_context_packet_created",
                "person_attention_claimed",
                "person_saw_or_heard_claimed",
                "automatic_memory_created",
                "automatic_preference_created",
                "external_parent_observation_sha256",
            },
            "presentation observation",
        )
        if observation.get("schema") != "kira.resident_media_presentation_observation.v4":
            raise ResidentMediaV4Error("presentation observation schema changed")
        manifest_value = observation.get("source_manifest")
        if not isinstance(manifest_value, Mapping):
            raise ResidentMediaV4Error("presentation source manifest is missing")
        exact_manifest = self.catalog.manifest(self._next_ordinal)
        clean_manifest = validate_source_manifest(
            manifest_value, expected_stimulus_id=STIMULUS_ORDER[self._next_ordinal]
        )
        if canonical_json_bytes(clean_manifest) != canonical_json_bytes(exact_manifest):
            raise ResidentMediaV4Error("presentation source/coordinates/derivatives changed from the accepted manifest")
        for field in (
            "engineering_output_completed",
            "machine_visual_interpretation_created",
            "machine_audio_cue_created",
            "machine_context_packet_created",
            "person_attention_claimed",
            "person_saw_or_heard_claimed",
            "automatic_memory_created",
            "automatic_preference_created",
        ):
            if not isinstance(observation.get(field), bool):
                raise ResidentMediaV4Error(f"{field} must be boolean")
        if observation.get("engineering_output_completed") is not True:
            raise ResidentMediaV4Error("incomplete engineering output cannot be recorded")
        if any(
            observation.get(field) is True
            for field in (
                "person_attention_claimed",
                "person_saw_or_heard_claimed",
                "automatic_memory_created",
                "automatic_preference_created",
            )
        ):
            raise ResidentMediaV4Error("static engineering evidence cannot assert person experience, memory, or preference")
        if self._pending_reservation is None:
            raise ResidentMediaV4Error("presentation has no durable consumed reservation")
        if canonical_json_bytes(dict(reservation)) != canonical_json_bytes(self._pending_reservation):
            raise ResidentMediaV4Error("presentation reservation mismatch or replay")
        return {
            "schema": "kira.resident_media_presentation_core.v4",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "stimulus_id": STIMULUS_ORDER[self._next_ordinal],
            "ordinal": self._next_ordinal,
            "session_event_sequence": self._next_event_sequence,
            "choice_event_sha256": self._last_choice_event_sha256,
            "source_manifest": exact_manifest,
            "source_manifest_sha256": self.catalog.manifest_sha256(self._next_ordinal),
            "reservation": self._pending_reservation,
            "engineering_output_completed": True,
            "machine_visual_interpretation_created": observation["machine_visual_interpretation_created"],
            "machine_audio_cue_created": observation["machine_audio_cue_created"],
            "machine_context_packet_created": observation["machine_context_packet_created"],
            "person_attention_claimed": False,
            "person_saw_or_heard_claimed": False,
            "automatic_memory_created": False,
            "automatic_preference_created": False,
            "external_parent_observation_sha256": _sha(
                observation.get("external_parent_observation_sha256"),
                "external_parent_observation_sha256",
            ),
        }

    def _validate_presentation_payload(self, payload: Mapping[str, Any], *, restore: bool) -> None:
        _exact_keys(
            payload,
            {
                "schema",
                "presentation_core",
                "presentation_core_sha256",
                "reservation_event_sha256",
            },
            "presentation event payload",
        )
        if payload.get("schema") != "kira.resident_media_presentation_event.v4":
            raise ResidentMediaV4Error("presentation event schema changed")
        core = payload.get("presentation_core")
        if not isinstance(core, Mapping):
            raise ResidentMediaV4Error("presentation durable core is incomplete")
        core_sha = sha256_record(core)
        if payload.get("presentation_core_sha256") != core_sha:
            raise ResidentMediaV4Error("presentation core digest changed")
        exact_manifest = self.catalog.manifest(self._next_ordinal)
        if core.get("source_manifest") != exact_manifest:
            raise ResidentMediaV4Error("durable presentation manifest changed")
        expected_values = {
            "schema": "kira.resident_media_presentation_core.v4",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "stimulus_id": STIMULUS_ORDER[self._next_ordinal],
            "ordinal": self._next_ordinal,
            "session_event_sequence": self._next_event_sequence,
            "choice_event_sha256": self._last_choice_event_sha256,
            "source_manifest_sha256": self.catalog.manifest_sha256(self._next_ordinal),
            "person_attention_claimed": False,
            "person_saw_or_heard_claimed": False,
            "automatic_memory_created": False,
            "automatic_preference_created": False,
        }
        for field, expected in expected_values.items():
            if core.get(field) != expected:
                raise ResidentMediaV4Error(f"durable presentation binding changed: {field}")
        reservation = core.get("reservation")
        if not isinstance(reservation, Mapping) or self._pending_reservation is None:
            raise ResidentMediaV4Error("durable presentation reservation is missing")
        if canonical_json_bytes(dict(reservation)) != canonical_json_bytes(self._pending_reservation):
            raise ResidentMediaV4Error("durable presentation reservation changed")
        if payload.get("reservation_event_sha256") != self._pending_reservation[
            "reservation_event_sha256"
        ]:
            raise ResidentMediaV4Error("presentation reservation-event binding changed")
        _exact_keys(
            core,
            {
                "schema",
                "session_id",
                "person_id",
                "stimulus_id",
                "ordinal",
                "session_event_sequence",
                "choice_event_sha256",
                "source_manifest",
                "source_manifest_sha256",
                "reservation",
                "engineering_output_completed",
                "machine_visual_interpretation_created",
                "machine_audio_cue_created",
                "machine_context_packet_created",
                "person_attention_claimed",
                "person_saw_or_heard_claimed",
                "automatic_memory_created",
                "automatic_preference_created",
                "external_parent_observation_sha256",
            },
            "presentation core",
        )
        if not restore:
            # The live path has already validated the observation before this check.
            return

    def record_presentation(
        self,
        observation: Mapping[str, Any],
        reservation: Mapping[str, Any],
    ) -> str:
        core = self._presentation_core(observation, reservation)
        core_sha = sha256_record(core)
        sample = self.clock.sample()
        payload = {
            "schema": "kira.resident_media_presentation_event.v4",
            "presentation_core": core,
            "presentation_core_sha256": core_sha,
            "reservation_event_sha256": self._pending_reservation["reservation_event_sha256"],
        }
        self._validate_presentation_payload(payload, restore=False)
        digest, _ = self._commit_event("PRESENTATION_RECORDED", payload, sample)
        # State changes only after both durable ledgers passed append/fsync/reopen/identity checks.
        self._last_event_sha256 = digest
        self._last_event_utc = sample.utc
        self._last_event_monotonic_ns = sample.monotonic_ns
        self._next_event_sequence += 1
        self._next_ordinal += 1
        self._choice_required_phase = f"AFTER_{core['stimulus_id']}"
        self._last_choice_event_sha256 = None
        self._last_choice_utc = None
        self._last_choice_monotonic_ns = None
        self._pending_reservation = None
        self._paused = False
        return digest

    def mark_engineering_finished(self) -> str:
        if (
            self._stopped
            or self._paused
            or self._last_choice_event_sha256 is not None
            or self._pending_reservation is not None
        ):
            raise ResidentMediaV4Error("cannot finish from the current state")
        if self._next_ordinal != len(STIMULUS_ORDER):
            raise ResidentMediaV4Error("cannot finish before every voluntarily continued stimulus")
        if self._engineering_finished:
            raise ResidentMediaV4Error("engineering finish is append-only and already recorded")
        sample = self.clock.sample()
        payload = {
            "schema": "kira.resident_media_engineering_finished.v4",
            "presented_stimulus_count": len(STIMULUS_ORDER),
            "person_experience_claimed": False,
            "automatic_memory_or_preference_created": False,
            "awake_owner_post_acknowledged": False,
        }
        digest, _ = self._commit_event("ENGINEERING_FINISHED", payload, sample)
        self._last_event_sha256 = digest
        self._last_event_utc = sample.utc
        self._last_event_monotonic_ns = sample.monotonic_ns
        self._next_event_sequence += 1
        self._engineering_finished = True
        return digest

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_voluntary_state.v4",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "catalog_sha256": self.catalog.sha256,
            "next_ordinal": self._next_ordinal,
            "next_event_sequence": self._next_event_sequence,
            "next_required_phase": self._choice_required_phase,
            "last_event_sha256": self._last_event_sha256,
            "current_choice_authorizes_capability": self._last_choice_event_sha256 is not None,
            "presentation_reservation_pending": self._pending_reservation is not None,
            "paused": self._paused,
            "stopped": self._stopped,
            "engineering_finished": self._engineering_finished,
            "live_execution_allowed": False,
            "parent_process_trust_proven": False,
            "source_bytes_read_or_decoded_proven": False,
            "selected_person_direct_seeing_or_hearing_proven": False,
            "automatic_memory_or_preference_created": False,
            "awake_owner_post_acknowledged": False,
        }


def static_execution_requirements() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_v4_static_requirements.v1",
        "exact_model": {"name": EXACT_MODEL, "digest": EXACT_DIGEST},
        "person_id": PERSON_ID,
        "stimulus_order": list(STIMULUS_ORDER),
        "ordinary_decline_overrides_yes_or_continue_label": True,
        "mixed_ambiguous_or_self_correcting_requires_new_turn": True,
        "raw_and_final_semantic_choice_must_match": True,
        "exact_manifest_byte_count_hash_coordinates_and_derivatives_bound": True,
        "capability_is_session_person_stimulus_choice_source_process_and_sequence_bound": True,
        "one_capability_issue_per_exact_choice_source_binding": True,
        "capability_single_use_is_durable_across_authority_restart": True,
        "capability_consumed_and_reservation_journaled_before_external_presentation": True,
        "transition_time_is_read_internally_not_caller_supplied": True,
        "utc_freshness_and_monotonic_order_required": True,
        "state_advances_only_after_exclusive_append_fsync_reopen_and_identity_validation": True,
        "external_parent_must_prove_model_process_source_output_and_cleanup": True,
        "machine_output_person_experience_separate": True,
        "automatic_memory_or_preference": False,
        "fresh_independent_hostile_audit_required": True,
        "live_execution_allowed": False,
    }
