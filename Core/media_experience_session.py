"""Grounded, in-memory media-experience session state.

This module does not open playback devices, decode or copy media, render PDF
pages, create memories, or persist records.  It is the small truth layer that a
future reviewed player/page renderer can call after it has actually presented
material to one selected person.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


MEDIA_KINDS = {"magazine", "pdf", "movie", "tv", "video", "music"}
PAGE_KINDS = {"magazine", "pdf"}
TIMED_MEDIA_KINDS = {"movie", "tv", "video", "music"}
TEXT_PROVENANCE_KINDS = {
    "ocr",
    "caption",
    "captions",
    "subtitle",
    "subtitles",
    "transcript",
    "transcripts",
    "script",
    "scripts",
    "lyrics",
    "summary",
    "metadata",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EPSILON = 1e-9


class MediaExperienceError(ValueError):
    """Raised when proposed session evidence would overstate experience."""


class MediaExperienceLeaseError(PermissionError):
    """Raised when an event is submitted under the wrong or revoked lease."""


@dataclass(frozen=True)
class MediaExperienceLease:
    """Identity binding required for every mutation of a media session."""

    session_id: str
    person_id: str
    activation_revision: str
    nonce: str


def _require_text(value: str, field: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MediaExperienceError(f"{field} must be a non-empty string.")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise MediaExperienceError(f"{field} exceeds {maximum} characters.")
    return normalized


def _number(value: float | int, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MediaExperienceError(f"{field} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise MediaExperienceError(f"{field} must be a finite number.")
    if positive and result <= 0:
        raise MediaExperienceError(f"{field} must be greater than zero.")
    if not positive and result < 0:
        raise MediaExperienceError(f"{field} must not be negative.")
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MediaExperienceSession:
    """In-memory, lease-bound truth record for one person and one media source.

    The caller remains responsible for authorization, rendering, playback, and
    perception.  This class records only explicit facts supplied after those
    systems act.  It has deliberately no save/write method.
    """

    def __init__(
        self,
        *,
        project_root: str | Path,
        source_path: str | Path,
        validated_source: Mapping[str, Any] | None = None,
        kind: str,
        person_id: str,
        activation_revision: str,
        session_id: str,
        session_nonce: str,
        media_duration_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        max_private_reactions: int = 8,
        max_private_reaction_characters: int = 1000,
    ) -> None:
        normalized_kind = str(kind).strip().lower()
        if normalized_kind not in MEDIA_KINDS:
            raise MediaExperienceError(
                f"kind must be one of: {', '.join(sorted(MEDIA_KINDS))}."
            )
        if not callable(clock):
            raise MediaExperienceError("clock must be callable.")
        if isinstance(max_private_reactions, bool) or not isinstance(max_private_reactions, int):
            raise MediaExperienceError("max_private_reactions must be an integer.")
        if max_private_reactions < 1:
            raise MediaExperienceError("max_private_reactions must be at least one.")
        if (
            isinstance(max_private_reaction_characters, bool)
            or not isinstance(max_private_reaction_characters, int)
        ):
            raise MediaExperienceError("max_private_reaction_characters must be an integer.")
        if max_private_reaction_characters < 1:
            raise MediaExperienceError(
                "max_private_reaction_characters must be at least one."
            )

        self._project_root = Path(project_root).resolve(strict=True)
        self._library_root = (self._project_root / "Data" / "library").resolve(strict=True)
        self._clock = clock
        self._last_event_time: float | None = None
        self._sequence = 0
        self._max_private_reactions = max_private_reactions
        self._max_private_reaction_characters = max_private_reaction_characters

        source = self._describe_library_source(source_path, validated_source=validated_source)
        duration: float | None = None
        if media_duration_seconds is not None:
            duration = _number(media_duration_seconds, "media_duration_seconds", positive=True)
        if normalized_kind in PAGE_KINDS and duration is not None:
            raise MediaExperienceError("page media must not declare a playback duration.")

        self._lease = MediaExperienceLease(
            session_id=_require_text(session_id, "session_id"),
            person_id=_require_text(person_id, "person_id"),
            activation_revision=_require_text(
                activation_revision, "activation_revision"
            ),
            nonce=_require_text(session_nonce, "session_nonce", maximum=512),
        )
        self._lease_active = True
        self._kind = normalized_kind
        self._source = source
        self._session_status = "active"
        self._playback_state = "ready" if normalized_kind in TIMED_MEDIA_KINDS else "not_applicable"
        self._media_clock_seconds = 0.0 if normalized_kind in TIMED_MEDIA_KINDS else None
        self._media_duration_seconds = duration
        self._playing_from_seconds: float | None = None
        self._page_presentations: list[dict[str, Any]] = []
        self._page_observations: list[dict[str, Any]] = []
        self._presented_intervals: list[dict[str, Any]] = []
        self._observed_intervals: list[dict[str, Any]] = []
        self._text_provenance: list[dict[str, Any]] = []
        self._private_reactions: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._created_at = self._event_time()
        self._append_event_at(
            "session_started",
            self._created_at,
            source_path=source["project_relative_path"],
            source_sha256=source["sha256"],
        )

    @property
    def lease(self) -> MediaExperienceLease:
        """Return the immutable lease callers must present with each event."""

        return self._lease

    def _event_time(self) -> float:
        value = _number(self._clock(), "clock value")
        if self._last_event_time is not None and value < self._last_event_time:
            raise MediaExperienceError("clock must be monotonic within a session.")
        self._last_event_time = value
        return value

    def _append_event_at(self, event_type: str, at: float, **details: Any) -> None:
        self._sequence += 1
        self._events.append(
            {
                "sequence": self._sequence,
                "event_type": event_type,
                "event_clock_seconds": at,
                **details,
            }
        )

    def _append_event(self, event_type: str, **details: Any) -> float:
        at = self._event_time()
        self._append_event_at(event_type, at, **details)
        return at

    def _require_lease(self, lease: MediaExperienceLease) -> None:
        if not isinstance(lease, MediaExperienceLease) or lease != self._lease:
            raise MediaExperienceLeaseError(
                "event lease does not match this person/session/activation."
            )
        if not self._lease_active:
            raise MediaExperienceLeaseError("media-experience lease is revoked.")

    def _require_active_session(self) -> None:
        if self._session_status != "active":
            raise MediaExperienceError("media presentation has already finished.")

    def _describe_library_source(
        self,
        source_path: str | Path,
        *,
        validated_source: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidate = Path(source_path)
        if not candidate.is_absolute():
            candidate = self._project_root / candidate
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise MediaExperienceError(f"media source does not exist: {source_path}") from exc
        if not resolved.is_file():
            raise MediaExperienceError("media source must be a file.")
        try:
            resolved.relative_to(self._library_root)
        except ValueError as exc:
            raise MediaExperienceError(
                "media source must resolve inside project Data/library."
            ) from exc
        project_relative = resolved.relative_to(self._project_root).as_posix()
        if not project_relative.startswith("Data/library/"):
            raise MediaExperienceError(
                "media source must have an exact project-relative Data/library path."
            )
        size_bytes = resolved.stat().st_size
        if validated_source is not None:
            if not isinstance(validated_source, Mapping) or set(validated_source) != {
                "project_relative_path",
                "sha256",
                "size_bytes",
                "validation_kind",
            }:
                raise MediaExperienceError(
                    "validated_source must contain exactly path, sha256, size, and validation kind."
                )
            supplied_path = str(validated_source.get("project_relative_path") or "")
            supplied_hash = str(validated_source.get("sha256") or "").strip().lower()
            supplied_size = validated_source.get("size_bytes")
            if supplied_path != project_relative:
                raise MediaExperienceError("validated source path does not match the selected source.")
            if not _SHA256_RE.fullmatch(supplied_hash):
                raise MediaExperienceError("validated source sha256 must be 64 lowercase hex characters.")
            if isinstance(supplied_size, bool) or not isinstance(supplied_size, int) or supplied_size != size_bytes:
                raise MediaExperienceError("validated source size does not match the selected source.")
            if validated_source.get("validation_kind") != "ephemeral_playback_grant_full_sha256":
                raise MediaExperienceError("validated source must come from the exact playback-grant hash gate.")
            digest = supplied_hash
            validation_kind = "ephemeral_playback_grant_full_sha256"
        else:
            digest = _sha256_file(resolved)
            validation_kind = "media_experience_direct_full_sha256"
        return {
            "project_relative_path": project_relative,
            "sha256": digest,
            "size_bytes": size_bytes,
            "validation_kind": validation_kind,
            "raw_media_copied": False,
        }

    def _require_page_kind(self) -> None:
        if self._kind not in PAGE_KINDS:
            raise MediaExperienceError("page presentation is limited to magazine/pdf sessions.")

    def _require_timed_kind(self) -> None:
        if self._kind not in TIMED_MEDIA_KINDS:
            raise MediaExperienceError("playback events require movie/tv/video/music media.")

    def _validate_media_position(self, value: float | int, field: str) -> float:
        position = _number(value, field)
        if (
            self._media_duration_seconds is not None
            and position > self._media_duration_seconds + _EPSILON
        ):
            raise MediaExperienceError(
                f"{field} exceeds the declared media duration."
            )
        return position

    @staticmethod
    def _normalize_crop(
        crop: Mapping[str, float] | Sequence[float],
    ) -> dict[str, float]:
        if isinstance(crop, Mapping):
            if set(crop) != {"x", "y", "width", "height"}:
                raise MediaExperienceError(
                    "crop must contain exactly x, y, width, and height."
                )
            values = [crop["x"], crop["y"], crop["width"], crop["height"]]
        elif isinstance(crop, Sequence) and not isinstance(crop, (str, bytes)):
            if len(crop) != 4:
                raise MediaExperienceError("crop sequence must have four values.")
            values = list(crop)
        else:
            raise MediaExperienceError("crop must be a mapping or four-number sequence.")
        x = _number(values[0], "crop.x")
        y = _number(values[1], "crop.y")
        width = _number(values[2], "crop.width", positive=True)
        height = _number(values[3], "crop.height", positive=True)
        if x > 1 or y > 1 or x + width > 1 + _EPSILON or y + height > 1 + _EPSILON:
            raise MediaExperienceError("crop must fit within normalized page bounds.")
        return {"x": x, "y": y, "width": width, "height": height}

    def present_page(
        self,
        lease: MediaExperienceLease,
        *,
        page_number: int,
        crop: Mapping[str, float] | Sequence[float],
        zoom: float,
        duration_seconds: float,
    ) -> dict[str, Any]:
        """Record an exact rendered-page presentation, not OCR or a summary."""

        self._require_lease(lease)
        self._require_active_session()
        self._require_page_kind()
        if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
            raise MediaExperienceError("page_number must be an integer of at least one.")
        normalized_crop = self._normalize_crop(crop)
        normalized_zoom = _number(zoom, "zoom", positive=True)
        normalized_duration = _number(
            duration_seconds, "duration_seconds", positive=True
        )
        presentation_id = f"page_presentation_{len(self._page_presentations) + 1:04d}"
        at = self._append_event(
            "page_presented",
            presentation_id=presentation_id,
            page_number=page_number,
            duration_seconds=normalized_duration,
        )
        record = {
            "presentation_id": presentation_id,
            "channel": "visual_page",
            "source_path": self._source["project_relative_path"],
            "source_sha256": self._source["sha256"],
            "page_number": page_number,
            "crop": normalized_crop,
            "zoom": normalized_zoom,
            "duration_seconds": normalized_duration,
            "presented_at_event_clock_seconds": at,
            "ocr_included": False,
        }
        self._page_presentations.append(record)
        return deepcopy(record)

    def observe_page(
        self,
        lease: MediaExperienceLease,
        *,
        presentation_id: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        """Record bounded visual attention to an already presented page."""

        self._require_lease(lease)
        self._require_active_session()
        self._require_page_kind()
        presentation = next(
            (
                item
                for item in self._page_presentations
                if item["presentation_id"] == presentation_id
            ),
            None,
        )
        if presentation is None:
            raise MediaExperienceError("unknown page presentation_id.")
        duration = _number(duration_seconds, "duration_seconds", positive=True)
        prior = sum(
            item["duration_seconds"]
            for item in self._page_observations
            if item["presentation_id"] == presentation_id
        )
        if prior + duration > presentation["duration_seconds"] + _EPSILON:
            raise MediaExperienceError(
                "observed page duration cannot exceed presented page duration."
            )
        observation_id = f"page_observation_{len(self._page_observations) + 1:04d}"
        at = self._append_event(
            "page_observed",
            observation_id=observation_id,
            presentation_id=presentation_id,
            duration_seconds=duration,
        )
        record = {
            "observation_id": observation_id,
            "presentation_id": presentation_id,
            "channel": "visual_page",
            "page_number": presentation["page_number"],
            "crop": deepcopy(presentation["crop"]),
            "zoom": presentation["zoom"],
            "duration_seconds": duration,
            "observed_at_event_clock_seconds": at,
            "based_on_ocr": False,
        }
        self._page_observations.append(record)
        return deepcopy(record)

    def resume(
        self,
        lease: MediaExperienceLease,
        *,
        at_media_seconds: float | None = None,
    ) -> None:
        self._require_lease(lease)
        self._require_active_session()
        self._require_timed_kind()
        if self._playback_state == "playing":
            raise MediaExperienceError("playback is already running.")
        expected = float(self._media_clock_seconds)
        position = expected if at_media_seconds is None else self._validate_media_position(
            at_media_seconds, "at_media_seconds"
        )
        if abs(position - expected) > _EPSILON:
            raise MediaExperienceError("resume position must match the exact media clock; seek first.")
        self._playing_from_seconds = position
        self._playback_state = "playing"
        self._append_event("playback_resumed", media_clock_seconds=position)

    def _close_playing_interval(self, end_seconds: float, event_type: str) -> None:
        if self._playback_state != "playing" or self._playing_from_seconds is None:
            raise MediaExperienceError("playback is not running.")
        start = self._playing_from_seconds
        if end_seconds < start - _EPSILON:
            raise MediaExperienceError("media clock cannot move backward while playing.")
        if end_seconds > start + _EPSILON:
            self._presented_intervals.append(
                {
                    "start_seconds": start,
                    "end_seconds": end_seconds,
                    "duration_seconds": end_seconds - start,
                    "presentation_channel": (
                        "audio" if self._kind == "music" else "audiovisual"
                    ),
                }
            )
        self._media_clock_seconds = end_seconds
        self._playing_from_seconds = None
        self._append_event(event_type, media_clock_seconds=end_seconds)

    def pause(
        self,
        lease: MediaExperienceLease,
        *,
        at_media_seconds: float,
    ) -> None:
        self._require_lease(lease)
        self._require_active_session()
        self._require_timed_kind()
        end = self._validate_media_position(at_media_seconds, "at_media_seconds")
        self._close_playing_interval(end, "playback_paused")
        self._playback_state = "paused"

    def seek(self, lease: MediaExperienceLease, *, to_media_seconds: float) -> None:
        self._require_lease(lease)
        self._require_active_session()
        self._require_timed_kind()
        if self._playback_state == "playing":
            raise MediaExperienceError("pause before seeking so the presented interval is exact.")
        destination = self._validate_media_position(
            to_media_seconds, "to_media_seconds"
        )
        prior = float(self._media_clock_seconds)
        self._media_clock_seconds = destination
        self._playback_state = "paused"
        self._append_event(
            "playback_seeked",
            from_media_seconds=prior,
            to_media_seconds=destination,
        )

    def finish(
        self,
        lease: MediaExperienceLease,
        *,
        at_media_seconds: float | None = None,
    ) -> None:
        """Finish presentation without creating memory, canon, or publication."""

        self._require_lease(lease)
        self._require_active_session()
        if self._kind in TIMED_MEDIA_KINDS:
            if self._playback_state == "playing":
                if at_media_seconds is None:
                    raise MediaExperienceError(
                        "a playing session requires an exact finish media clock."
                    )
                end = self._validate_media_position(
                    at_media_seconds, "at_media_seconds"
                )
                self._close_playing_interval(end, "playback_finished")
            else:
                current = float(self._media_clock_seconds)
                if at_media_seconds is not None:
                    given = self._validate_media_position(
                        at_media_seconds, "at_media_seconds"
                    )
                    if abs(given - current) > _EPSILON:
                        raise MediaExperienceError(
                            "finish position must match the paused media clock."
                        )
                self._append_event("playback_finished", media_clock_seconds=current)
            self._playback_state = "finished"
        else:
            if at_media_seconds is not None:
                raise MediaExperienceError("page sessions do not have a media clock.")
            self._append_event("page_session_finished")
        self._session_status = "finished"

    def close(self, lease: MediaExperienceLease) -> None:
        """Revoke the lease; no further event can enter this identity session."""

        self._require_lease(lease)
        if self._playback_state == "playing":
            raise MediaExperienceError("pause or finish playback before closing the lease.")
        self._append_event("session_closed")
        self._session_status = "closed"
        self._lease_active = False

    @staticmethod
    def _interval_covered(
        start: float, end: float, presented: list[dict[str, Any]]
    ) -> bool:
        cursor = start
        for interval in sorted(
            presented, key=lambda item: (item["start_seconds"], item["end_seconds"])
        ):
            interval_start = interval["start_seconds"]
            interval_end = interval["end_seconds"]
            if interval_end < cursor - _EPSILON:
                continue
            if interval_start > cursor + _EPSILON:
                return False
            cursor = max(cursor, interval_end)
            if cursor >= end - _EPSILON:
                return True
        return False

    def observe_interval(
        self,
        lease: MediaExperienceLease,
        *,
        start_seconds: float,
        end_seconds: float,
        modality: str,
    ) -> dict[str, Any]:
        """Record only a sub-interval that was actually presented."""

        self._require_lease(lease)
        self._require_timed_kind()
        start = self._validate_media_position(start_seconds, "start_seconds")
        end = self._validate_media_position(end_seconds, "end_seconds")
        if end <= start:
            raise MediaExperienceError("observed interval end must be after start.")
        normalized_modality = str(modality).strip().lower()
        allowed = {"audio"} if self._kind == "music" else {"visual", "audio", "audiovisual"}
        if normalized_modality not in allowed:
            raise MediaExperienceError(
                f"modality for {self._kind} must be one of: {', '.join(sorted(allowed))}."
            )
        if not self._interval_covered(start, end, self._presented_intervals):
            raise MediaExperienceError(
                "observed interval must be wholly covered by presented intervals."
            )
        observation_id = f"timed_observation_{len(self._observed_intervals) + 1:04d}"
        at = self._append_event(
            "media_interval_observed",
            observation_id=observation_id,
            start_seconds=start,
            end_seconds=end,
            modality=normalized_modality,
        )
        record = {
            "observation_id": observation_id,
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": end - start,
            "modality": normalized_modality,
            "observed_at_event_clock_seconds": at,
        }
        self._observed_intervals.append(record)
        return deepcopy(record)

    def add_text_provenance(
        self,
        lease: MediaExperienceLease,
        *,
        provenance_kind: str,
        content_sha256: str | None = None,
        source_path: str | Path | None = None,
        page_number: int | None = None,
        interval_seconds: Sequence[float] | None = None,
        language: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Attach a separate text source without claiming it was seen/heard."""

        self._require_lease(lease)
        normalized_kind = str(provenance_kind).strip().lower()
        if normalized_kind not in TEXT_PROVENANCE_KINDS:
            raise MediaExperienceError(
                "unsupported text provenance kind; use OCR, captions/subtitles, "
                "transcript, script, lyrics, summary, or metadata."
            )
        normalized_kind = {
            "caption": "captions",
            "subtitle": "subtitles",
            "transcripts": "transcript",
            "scripts": "script",
        }.get(normalized_kind, normalized_kind)
        if normalized_kind == "ocr":
            self._require_page_kind()
            if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
                raise MediaExperienceError("OCR provenance requires an exact page_number.")
        elif page_number is not None:
            if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
                raise MediaExperienceError("page_number must be an integer of at least one.")
        if normalized_kind in {"captions", "subtitles", "script"} and self._kind not in {
            "movie",
            "tv",
            "video",
        }:
            raise MediaExperienceError(
                "captions/subtitles/scripts require movie, tv, or video media."
            )
        if normalized_kind == "transcript" and self._kind not in TIMED_MEDIA_KINDS:
            raise MediaExperienceError(
                "transcript provenance requires movie, tv, video, or music/audio media."
            )
        if normalized_kind == "lyrics" and self._kind != "music":
            raise MediaExperienceError("lyrics provenance requires music media.")

        source: dict[str, Any]
        if source_path is not None:
            source = self._describe_library_source(source_path)
            if content_sha256 is not None:
                normalized_hash = str(content_sha256).strip().lower()
                if normalized_hash != source["sha256"]:
                    raise MediaExperienceError(
                        "provided content_sha256 does not match provenance source."
                    )
        else:
            if content_sha256 is None:
                raise MediaExperienceError(
                    "text provenance requires source_path or exact content_sha256."
                )
            normalized_hash = str(content_sha256).strip().lower()
            if not _SHA256_RE.fullmatch(normalized_hash):
                raise MediaExperienceError("content_sha256 must be 64 lowercase hex characters.")
            source = {
                "project_relative_path": None,
                "sha256": normalized_hash,
                "size_bytes": None,
                "raw_media_copied": False,
            }

        interval: dict[str, float] | None = None
        if interval_seconds is not None:
            if (
                isinstance(interval_seconds, (str, bytes))
                or not isinstance(interval_seconds, Sequence)
                or len(interval_seconds) != 2
            ):
                raise MediaExperienceError("interval_seconds must contain start and end.")
            start = self._validate_media_position(interval_seconds[0], "interval start")
            end = self._validate_media_position(interval_seconds[1], "interval end")
            if end <= start:
                raise MediaExperienceError("text provenance interval end must be after start.")
            interval = {"start_seconds": start, "end_seconds": end}

        provenance_id = f"text_provenance_{len(self._text_provenance) + 1:04d}"
        at = self._append_event(
            "text_provenance_added",
            provenance_id=provenance_id,
            provenance_kind=normalized_kind,
        )
        record = {
            "provenance_id": provenance_id,
            "provenance_kind": normalized_kind,
            "source_path": source["project_relative_path"],
            "source_sha256": source["sha256"],
            "page_number": page_number,
            "interval_seconds": interval,
            "language": None if language is None else _require_text(language, "language", maximum=64),
            "label": None if label is None else _require_text(label, "label", maximum=256),
            "added_at_event_clock_seconds": at,
            "counts_as_page_seen": False,
            "counts_as_watched": False,
            "counts_as_listened": False,
            "raw_text_stored": False,
        }
        self._text_provenance.append(record)
        return deepcopy(record)

    def add_private_reaction(
        self, lease: MediaExperienceLease, *, reaction: str
    ) -> dict[str, Any]:
        """Store one bounded session-private reaction, with no memory promotion."""

        self._require_lease(lease)
        if len(self._private_reactions) >= self._max_private_reactions:
            raise MediaExperienceError("private reaction count limit reached.")
        normalized = _require_text(
            reaction,
            "reaction",
            maximum=self._max_private_reaction_characters,
        )
        reaction_id = f"private_reaction_{len(self._private_reactions) + 1:04d}"
        at = self._append_event(
            "private_reaction_added", reaction_id=reaction_id
        )
        record = {
            "reaction_id": reaction_id,
            "reaction": normalized,
            "visibility": "session_person_private",
            "recorded_at_event_clock_seconds": at,
            "durable_memory_created": False,
            "canon_created": False,
            "temporary_ai_evidence_created": False,
            "publication_authorized": False,
        }
        self._private_reactions.append(record)
        return deepcopy(record)

    def snapshot(self, *, include_private_reactions: bool = False) -> dict[str, Any]:
        """Return a detached JSON-safe snapshot; nothing is written automatically."""

        reactions: list[dict[str, Any]]
        if include_private_reactions:
            reactions = deepcopy(self._private_reactions)
        else:
            reactions = []
        data = {
            "schema_version": 1,
            "session_id": self._lease.session_id,
            "person_id": self._lease.person_id,
            "activation_revision": self._lease.activation_revision,
            "kind": self._kind,
            "status": self._session_status,
            "created_at_event_clock_seconds": self._created_at,
            "lease": {
                "active": self._lease_active,
                "nonce_sha256": hashlib.sha256(
                    self._lease.nonce.encode("utf-8")
                ).hexdigest(),
                "scope": "one_person_one_activation_one_media_session",
            },
            "source": deepcopy(self._source),
            "playback": {
                "state": self._playback_state,
                "media_clock_seconds": self._media_clock_seconds,
                "declared_duration_seconds": self._media_duration_seconds,
                "presented_intervals": deepcopy(self._presented_intervals),
                "observed_intervals": deepcopy(self._observed_intervals),
            },
            "page_presentations": deepcopy(self._page_presentations),
            "page_observations": deepcopy(self._page_observations),
            "text_provenance": deepcopy(self._text_provenance),
            "private_reactions": {
                "count": len(self._private_reactions),
                "maximum_count": self._max_private_reactions,
                "maximum_characters_each": self._max_private_reaction_characters,
                "included_in_this_snapshot": include_private_reactions,
                "items": reactions,
            },
            "truth_boundaries": {
                "summary_or_metadata_counts_as_page_seen": False,
                "summary_or_metadata_counts_as_watched": False,
                "summary_or_metadata_counts_as_listened": False,
                "ocr_counts_as_visual_page_observation": False,
                "captions_or_script_counts_as_watched": False,
                "subtitles_or_transcript_counts_as_watched": False,
                "lyrics_counts_as_listened": False,
                "observed_intervals_must_be_presented": True,
            },
            "implications": {
                "lived_memory_created": False,
                "canon_created": False,
                "temporary_ai_evidence_created": False,
                "publication_authorized": False,
            },
            "storage": {
                "automatic_persistence": False,
                "raw_media_copied": False,
                "snapshot_return_only": True,
            },
            "events": deepcopy(self._events),
        }
        # This round trip both detaches caller-owned references and proves the
        # result contains only ordinary JSON values.
        return json.loads(json.dumps(data, ensure_ascii=False, sort_keys=True))

    def snapshot_json(self, *, include_private_reactions: bool = False) -> str:
        """Return canonical JSON text without writing it anywhere."""

        return json.dumps(
            self.snapshot(include_private_reactions=include_private_reactions),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
