"""Exact-item, owner-authored media classification corrections.

This module has two deliberately narrow responsibilities:

* interpret Robert's natural-language correction as one of the three public
  library access categories, or request clarification; and
* preserve every applied correction in an append-only JSONL ledger.

It does not inspect filenames, search the library, classify people, grant
co-viewing access, open media, or claim that anybody experienced an item.
Corrections are keyed only by an exact opaque media ID and exact file SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import threading
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


GENERAL_LIBRARY_MEDIA = "GENERAL_LIBRARY_MEDIA"
MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW = (
    "MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW"
)
EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT = (
    "EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT"
)
ACCESS_CATEGORIES = frozenset(
    {
        GENERAL_LIBRARY_MEDIA,
        MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
        EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
    }
)

LEDGER_SCHEMA = "kira.media_classification_correction.v1"
OWNER_CORRECTION_SOURCE = "robert_exact_item_natural_language"
DEFAULT_CONTENT_RATING = "UNRATED"
MAX_CORRECTION_TEXT_LENGTH = 16_384

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_RATING_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bTV[\s_-]*MA\b", re.IGNORECASE), "TV-MA"),
    (re.compile(r"\bTV[\s_-]*14\b", re.IGNORECASE), "TV-14"),
    (re.compile(r"\bTV[\s_-]*PG\b", re.IGNORECASE), "TV-PG"),
    (re.compile(r"\bTV[\s_-]*G\b", re.IGNORECASE), "TV-G"),
    (re.compile(r"\bTV[\s_-]*Y7\b", re.IGNORECASE), "TV-Y7"),
    (re.compile(r"\bTV[\s_-]*Y\b", re.IGNORECASE), "TV-Y"),
    (re.compile(r"\bPG[\s_-]*13\b", re.IGNORECASE), "PG-13"),
    (re.compile(r"\bNC[\s_-]*17\b", re.IGNORECASE), "NC-17"),
    (
        re.compile(r"\bPG(?![\s_-]*13)(?:[\s_-]*rated)?\b", re.IGNORECASE),
        "PG",
    ),
    (re.compile(r"\bG[\s_-]*rated\b", re.IGNORECASE), "G"),
    (re.compile(r"\bR[\s_-]*rated\b", re.IGNORECASE), "R"),
    (re.compile(r"\brating\s+(?:to\s+|is\s+)?R\b", re.IGNORECASE), "R"),
)

_GENERAL_RATINGS = frozenset(
    {"G", "PG", "PG-13", "TV-Y", "TV-Y7", "TV-G", "TV-PG", "TV-14"}
)
_MATURE_MAINSTREAM_RATINGS = frozenset({"R", "TV-MA"})

_CLARIFICATION = (
    "Please classify this exact item as general library media, mainstream "
    "mature media requiring an adult co-viewer, or explicit adult-only media."
)


def looks_like_media_classification_correction(correction_text: str) -> bool:
    """Return whether ordinary chat clearly asks to correct media access.

    This conservative prefilter prevents an incidental sentence such as
    ``I liked that R-rated movie`` from mutating durable owner policy.  The
    explicit owner correction action may bypass this prefilter and call the
    parser directly.
    """

    exact_text = _validated_exact_text(correction_text)
    text = (
        exact_text.casefold()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("â€™", "'")
    )
    if any(category.casefold() in text for category in ACCESS_CATEGORIES):
        return True
    if re.search(
        r"\b(?:general\s+library|adult\s+co[\s-]*view|explicit(?:\s+adult)?[\s-]*only|adult[\s-]*only|mainstream\s+(?:mature|r[\s-]*rated|adult))\b",
        text,
    ):
        return True
    if re.search(
        r"\b(?:non[\s-]*adults?|minors?)\b.{0,80}\b(?:only\s+)?with\s+an?\s+(?:confirmed\s+)?adult\b",
        text,
    ):
        return True
    if re.search(
        r"\b(?:change|set|correct|update|fix|mark|classify|reclassify)\b.{0,80}\b(?:rating|classification|access\s+category)\b",
        text,
    ) or re.search(
        r"\b(?:rating|classification|access\s+category)\b.{0,80}\b(?:change|set|correct|update|fix|mark|classify|reclassify|unknown|unclear|unsure)\b",
        text,
    ):
        return True
    if re.search(r"\b(?:marked|classified(?:\s+as)?)\s+general\s+by\s+mistake\b", text):
        return True
    if re.search(r"\b(?:not|isn't|isnt|is\s+not)\s+(?:explicit|adult[\s-]*only)\b", text):
        return True
    return False


class MediaClassificationCorrectionError(ValueError):
    """Base error for malformed or unsafe correction data."""


class MediaClassificationBindingError(MediaClassificationCorrectionError):
    """An opaque media ID does not bind to the supplied canonical path."""


class MediaClassificationLedgerError(MediaClassificationCorrectionError):
    """The append-only correction ledger is malformed or cannot be used."""


@dataclass(frozen=True, slots=True)
class MediaClassificationIntent:
    """A determinate apply intent or a safe request for clarification."""

    applied: bool
    needs_clarification: bool
    resulting_content_rating: str | None
    resulting_access_category: str | None
    clarification: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class MediaClassificationAppendResult:
    """Result of parsing and, only when determinate, appending a correction."""

    intent: MediaClassificationIntent
    record: dict[str, Any] | None

    @property
    def applied(self) -> bool:
        return self.record is not None

    @property
    def needs_clarification(self) -> bool:
        return self.intent.needs_clarification


def _validated_exact_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MediaClassificationCorrectionError(
            "Robert's correction text must be a non-empty string."
        )
    if len(value) > MAX_CORRECTION_TEXT_LENGTH or "\x00" in value:
        raise MediaClassificationCorrectionError(
            "Robert's correction text is malformed or too long."
        )
    return value


def _normalize_rating(value: object, *, allow_empty: bool = False) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_empty:
            return DEFAULT_CONTENT_RATING
        raise MediaClassificationCorrectionError("content rating is required.")
    if not isinstance(value, str):
        raise MediaClassificationCorrectionError("content rating must be text.")
    normalized = value.strip().upper().replace("_", "-").replace(" ", "-")
    aliases = {
        "PG13": "PG-13",
        "TVMA": "TV-MA",
        "TV14": "TV-14",
        "TVPG": "TV-PG",
        "TVG": "TV-G",
        "TVY7": "TV-Y7",
        "TVY": "TV-Y",
        "NC17": "NC-17",
        "NR": DEFAULT_CONTENT_RATING,
        "NOT-RATED": DEFAULT_CONTENT_RATING,
        "NOT-YET-RATED": DEFAULT_CONTENT_RATING,
        "NONE": DEFAULT_CONTENT_RATING,
    }
    normalized = aliases.get(normalized, normalized)
    if not 1 <= len(normalized) <= 32 or re.fullmatch(r"[A-Z0-9][A-Z0-9+./-]*", normalized) is None:
        raise MediaClassificationCorrectionError("content rating is malformed.")
    return normalized


def _rating_from_text(text: str) -> str | None:
    matches: list[tuple[int, str]] = []
    for pattern, rating in _RATING_PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append((match.start(), rating))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    distinct = {rating for _position, rating in matches}
    if len(distinct) != 1:
        return "__CONFLICT__"
    return matches[0][1]


def _clarification(reason: str) -> MediaClassificationIntent:
    return MediaClassificationIntent(
        applied=False,
        needs_clarification=True,
        resulting_content_rating=None,
        resulting_access_category=None,
        clarification=_CLARIFICATION,
        reason=reason,
    )


def parse_media_classification_correction(
    correction_text: str,
    *,
    current_content_rating: str | None = None,
) -> MediaClassificationIntent:
    """Interpret one exact owner correction without consulting item metadata.

    A filename, path, or title is intentionally not accepted by this parser.
    A caller supplies those values only when binding a determinate result to the
    ledger.  Unknown/ask-me wording and conflicting desired categories fail
    closed as a clarification request and are never treated as an application.
    """

    exact_text = _validated_exact_text(correction_text)
    text = (
        exact_text.casefold()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("â€™", "'")
    )

    if re.search(
        r"\b(?:do\s+not|don't|dont|should\s+not|shouldn't|shouldnt)\s+"
        r"(?:change|set|correct|update|fix|mark|classify|reclassify)\b",
        text,
    ) or re.search(
        r"\bnot\s+(?:changing|setting|correcting|updating|fixing|marking|classifying|reclassifying)\b",
        text,
    ):
        return _clarification("owner explicitly negated a classification change")

    if (
        re.search(r"\b(?:rating|classification)\s+(?:is\s+)?(?:unknown|unclear|unsure)\b", text)
        or re.search(r"\bask\s+me\b", text)
        or re.search(r"\b(?:do not|don't)\s+(?:restrict|open)\b", text)
    ):
        return _clarification("owner explicitly requested clarification before access")

    rating = _rating_from_text(exact_text)
    if rating == "__CONFLICT__":
        return _clarification("multiple conflicting content ratings were stated")

    negated_explicit = bool(
        re.search(
            r"\b(?:not|isn't|isnt|is\s+not|should\s+not\s+be|shouldn't\s+be|shouldnt\s+be)\s+"
            r"(?:explicit|adult[\s-]*only)\b",
            text,
        )
        or re.search(
            r"\b(?:do\s+not|don't|dont)\s+think\b.{0,80}\b"
            r"(?:explicit|adult[\s-]*only)\b",
            text,
        )
    )
    explicit_requested = bool(
        re.search(
            r"\b(?:explicit(?:\s+adult)?(?:[\s-]*only)?|adult[\s-]*only)\s+(?:material|media|content|folder|category)\b",
            text,
        )
        or EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT.casefold() in text
    ) and not negated_explicit

    negated_general = bool(
        re.search(
            r"\b(?:not|isn't|isnt|is\s+not|should\s+not\s+be|shouldn't\s+be|shouldnt\s+be)\s+"
            r"(?:in\s+)?general\s+library(?:\s+media)?\b",
            text,
        )
    )
    general_requested = bool(
        re.search(r"\b(?:belongs?\s+in\s+)?general\s+library(?:\s+media)?\b", text)
        or GENERAL_LIBRARY_MEDIA.casefold() in text
    ) and not negated_general
    if re.search(r"\b(?:marked|classified(?:\s+as)?)\s+general\s+by\s+mistake\b", text):
        general_requested = False

    negated_mature = bool(
        re.search(
            r"\b(?:not|isn't|isnt|is\s+not|should\s+not\s+be|shouldn't\s+be|shouldnt\s+be)\s+"
            r"(?:mainstream\s+(?:mature|r[\s-]*rated|adult)|mature\s+mainstream)\b",
            text,
        )
    )
    mature_requested = bool(
        re.search(r"\bmainstream\s+(?:mature|r[\s-]*rated|adult)\b", text)
        or re.search(r"\badult\s+co[\s-]*view(?:er|ing)?\b", text)
        or re.search(
            r"\b(?:non[\s-]*adults?|minors?)\b.{0,80}\b(?:only\s+)?with\s+an?\s+(?:confirmed\s+)?adult\b",
            text,
        )
        or MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW.casefold() in text
    ) and not negated_mature

    requested: set[str] = set()
    if explicit_requested:
        requested.add(EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT)
    if general_requested:
        requested.add(GENERAL_LIBRARY_MEDIA)
    if mature_requested:
        requested.add(MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW)

    if not requested and rating in _GENERAL_RATINGS:
        requested.add(GENERAL_LIBRARY_MEDIA)
    elif not requested and rating in _MATURE_MAINSTREAM_RATINGS:
        requested.add(MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW)

    if len(requested) != 1:
        if len(requested) > 1:
            return _clarification("conflicting access categories were stated")
        if negated_explicit or negated_general or negated_mature:
            return _clarification(
                "a category was rejected but no unambiguous replacement category was stated"
            )
        return _clarification("no supported exact access category was stated")

    resulting_category = next(iter(requested))
    if rating is None:
        resulting_rating = _normalize_rating(
            current_content_rating, allow_empty=True
        )
    else:
        resulting_rating = rating
    return MediaClassificationIntent(
        applied=True,
        needs_clarification=False,
        resulting_content_rating=resulting_rating,
        resulting_access_category=resulting_category,
        clarification=None,
        reason="exact owner correction is determinate",
    )


def _canonical_library_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise MediaClassificationCorrectionError(
            "project_relative_library_path must be canonical text."
        )
    if "\\" in value or "\x00" in value:
        raise MediaClassificationCorrectionError(
            "project_relative_library_path must use canonical forward slashes."
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.parts[:2] != ("Data", "library")
        or len(path.parts) < 3
        or path.as_posix() != value
    ):
        raise MediaClassificationCorrectionError(
            "project_relative_library_path must name one item below Data/library."
        )
    return value


def opaque_media_id_for_path(project_relative_library_path: str) -> str:
    """Return the existing library policy's exact opaque path identifier."""

    canonical = _canonical_library_path(project_relative_library_path)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _exact_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise MediaClassificationCorrectionError(
            f"{field_name} must be an exact lowercase SHA-256."
        )
    return value


def _optional_exact_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise MediaClassificationCorrectionError(f"{field_name} is malformed.")
    if len(value) > 1024 or "\x00" in value:
        raise MediaClassificationCorrectionError(f"{field_name} is malformed.")
    return value


def _source(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise MediaClassificationCorrectionError(
            "previous_classification_source is required."
        )
    if len(value) > 512 or "\x00" in value:
        raise MediaClassificationCorrectionError(
            "previous_classification_source is malformed."
        )
    return value


def _category(value: object, field_name: str) -> str:
    if not isinstance(value, str) or value not in ACCESS_CATEGORIES:
        raise MediaClassificationCorrectionError(
            f"{field_name} must be one of the three supported access categories."
        )
    return value


def _utc_timestamp(now: datetime) -> str:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise MediaClassificationLedgerError("UTC clock must return an aware datetime.")
    return now.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


class MediaClassificationCorrectionStore:
    """Thread-safe append-only JSONL correction ledger."""

    def __init__(
        self,
        ledger_path: str | Path,
        *,
        utc_clock: Callable[[], datetime] | None = None,
        allowed_root: str | Path | None = None,
    ) -> None:
        self._path = Path(ledger_path)
        self._allowed_root = (
            None
            if allowed_root is None
            else Path(os.path.abspath(Path(allowed_root)))
        )
        if self._allowed_root is not None:
            self._path = Path(os.path.abspath(self._path))
            if self._path.parent != self._allowed_root:
                raise MediaClassificationLedgerError(
                    "ledger path must be directly inside its controlled root."
                )
        self._utc_clock = utc_clock or (lambda: datetime.now(timezone.utc))
        if not callable(self._utc_clock):
            raise MediaClassificationLedgerError("utc_clock must be callable.")
        self._lock = threading.RLock()
        self._records: list[dict[str, Any]] = []
        self._latest: dict[tuple[str, str], dict[str, Any]] = {}
        self._next_sequence = 1
        self._validate_controlled_location()
        self._load_existing()

    @property
    def ledger_path(self) -> Path:
        return self._path

    @property
    def record_count(self) -> int:
        with self._lock:
            return len(self._records)

    @staticmethod
    def _is_link_like(path: Path) -> bool:
        try:
            if path.is_symlink():
                return True
            is_junction = getattr(path, "is_junction", None)
            if callable(is_junction) and is_junction():
                return True
            attributes = getattr(path.lstat(), "st_file_attributes", 0)
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            return bool(attributes & reparse_flag)
        except OSError as exc:
            raise MediaClassificationLedgerError(
                "could not inspect the controlled ledger path."
            ) from exc

    def _validate_controlled_location(self) -> None:
        if self._allowed_root is None:
            return
        parent = self._allowed_root.parent
        if not parent.exists() or not parent.is_dir() or self._is_link_like(parent):
            raise MediaClassificationLedgerError(
                "controlled ledger parent must be an existing non-link directory."
            )
        if self._allowed_root.exists() and (
            not self._allowed_root.is_dir()
            or self._is_link_like(self._allowed_root)
        ):
            raise MediaClassificationLedgerError(
                "controlled ledger root must be a non-link directory."
            )
        if self._path.exists() and (
            not self._path.is_file() or self._is_link_like(self._path)
        ):
            raise MediaClassificationLedgerError(
                "controlled ledger must be a regular non-link file."
            )

    def _validated_record(self, value: object, line_number: int) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise MediaClassificationLedgerError(
                f"ledger line {line_number} must be a JSON object."
            )
        try:
            sequence = value["append_sequence"]
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
                raise MediaClassificationLedgerError(
                    f"ledger line {line_number} has an invalid append sequence."
                )
            if value.get("schema") != LEDGER_SCHEMA:
                raise MediaClassificationLedgerError(
                    f"ledger line {line_number} has an unsupported schema."
                )
            media_id = _exact_sha256(value["opaque_media_id"], "opaque_media_id")
            file_sha256 = _exact_sha256(value["file_sha256"], "file_sha256")
            canonical_path = _canonical_library_path(
                value["project_relative_library_path"]
            )
            if opaque_media_id_for_path(canonical_path) != media_id:
                raise MediaClassificationBindingError(
                    f"ledger line {line_number} media ID/path binding is invalid."
                )
            _optional_exact_text(value.get("title"), "title")
            _optional_exact_text(value.get("version"), "version")
            _category(value["previous_access_category"], "previous_access_category")
            _normalize_rating(value["previous_content_rating"])
            _source(value["previous_classification_source"])
            _validated_exact_text(value["robert_exact_correction_text"])
            timestamp = value["correction_utc"]
            if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
                raise MediaClassificationLedgerError(
                    f"ledger line {line_number} has an invalid UTC timestamp."
                )
            datetime.fromisoformat(timestamp[:-1] + "+00:00")
            _normalize_rating(value["resulting_content_rating"])
            _category(value["resulting_access_category"], "resulting_access_category")
            if value.get("classification_source") != OWNER_CORRECTION_SOURCE:
                raise MediaClassificationLedgerError(
                    f"ledger line {line_number} has an invalid correction source."
                )
        except KeyError as exc:
            raise MediaClassificationLedgerError(
                f"ledger line {line_number} is missing {exc.args[0]}."
            ) from exc
        except (ValueError, TypeError) as exc:
            if isinstance(exc, MediaClassificationCorrectionError):
                raise
            raise MediaClassificationLedgerError(
                f"ledger line {line_number} is malformed."
            ) from exc
        return deepcopy(value)

    def _load_existing(self) -> None:
        self._validate_controlled_location()
        if not self._path.exists():
            return
        if not self._path.is_file():
            raise MediaClassificationLedgerError("ledger path must be a regular file.")
        previous_sequence = 0
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    record = self._validated_record(json.loads(line), line_number)
                    sequence = record["append_sequence"]
                    if sequence <= previous_sequence:
                        raise MediaClassificationLedgerError(
                            "ledger append sequences must be strictly increasing."
                        )
                    previous_sequence = sequence
                    self._records.append(record)
                    self._latest[
                        (record["opaque_media_id"], record["file_sha256"])
                    ] = record
        except (OSError, json.JSONDecodeError) as exc:
            raise MediaClassificationLedgerError(
                "could not read the append-only correction ledger."
            ) from exc
        self._next_sequence = previous_sequence + 1

    def append_correction(
        self,
        *,
        media_id: str,
        file_sha256: str,
        project_relative_library_path: str,
        title: str | None,
        version: str | None,
        previous_access_category: str,
        previous_classification_source: str,
        robert_exact_correction_text: str,
        current_content_rating: str | None = None,
    ) -> MediaClassificationAppendResult:
        """Parse and durably append one exact correction when determinate.

        Clarification results return normally with ``record is None`` and do
        not create or modify the ledger file.
        """

        exact_text = _validated_exact_text(robert_exact_correction_text)
        intent = parse_media_classification_correction(
            exact_text, current_content_rating=current_content_rating
        )
        if intent.needs_clarification:
            return MediaClassificationAppendResult(intent=intent, record=None)

        exact_media_id = _exact_sha256(media_id, "media_id")
        exact_file_hash = _exact_sha256(file_sha256, "file_sha256")
        canonical_path = _canonical_library_path(project_relative_library_path)
        if opaque_media_id_for_path(canonical_path) != exact_media_id:
            raise MediaClassificationBindingError(
                "opaque media ID does not match the exact canonical library path."
            )
        exact_title = _optional_exact_text(title, "title")
        exact_version = _optional_exact_text(version, "version")
        previous_category = _category(
            previous_access_category, "previous_access_category"
        )
        previous_rating = _normalize_rating(
            current_content_rating, allow_empty=True
        )
        previous_source = _source(previous_classification_source)

        with self._lock:
            record: dict[str, Any] = {
                "schema": LEDGER_SCHEMA,
                "append_sequence": self._next_sequence,
                "opaque_media_id": exact_media_id,
                "file_sha256": exact_file_hash,
                "project_relative_library_path": canonical_path,
                "title": exact_title,
                "version": exact_version,
                "previous_access_category": previous_category,
                "previous_content_rating": previous_rating,
                "previous_classification_source": previous_source,
                "robert_exact_correction_text": exact_text,
                "correction_utc": _utc_timestamp(self._utc_clock()),
                "resulting_content_rating": intent.resulting_content_rating,
                "resulting_access_category": intent.resulting_access_category,
                "classification_source": OWNER_CORRECTION_SOURCE,
            }
            payload = json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._validate_controlled_location()
                with self._path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(payload + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise MediaClassificationLedgerError(
                    "could not durably append the classification correction."
                ) from exc
            self._records.append(record)
            self._latest[(exact_media_id, exact_file_hash)] = record
            self._next_sequence += 1
            return MediaClassificationAppendResult(
                intent=intent, record=deepcopy(record)
            )

    def latest_for(
        self, media_id: str, file_sha256: str
    ) -> dict[str, Any] | None:
        """Return only the latest exact media-ID/file-hash correction."""

        exact_media_id = _exact_sha256(media_id, "media_id")
        exact_file_hash = _exact_sha256(file_sha256, "file_sha256")
        with self._lock:
            record = self._latest.get((exact_media_id, exact_file_hash))
            return deepcopy(record) if record is not None else None

    def latest_records(self) -> tuple[dict[str, Any], ...]:
        """Return the latest record for every exact item version, append-ordered."""

        with self._lock:
            return tuple(
                deepcopy(record)
                for record in sorted(
                    self._latest.values(),
                    key=lambda value: value["append_sequence"],
                )
            )

    def history_for(
        self, media_id: str, file_sha256: str
    ) -> tuple[dict[str, Any], ...]:
        """Return append-order history for one exact item version."""

        exact_media_id = _exact_sha256(media_id, "media_id")
        exact_file_hash = _exact_sha256(file_sha256, "file_sha256")
        with self._lock:
            return tuple(
                deepcopy(record)
                for record in self._records
                if record["opaque_media_id"] == exact_media_id
                and record["file_sha256"] == exact_file_hash
            )
