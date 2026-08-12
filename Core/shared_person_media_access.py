"""Fail-closed maturity filtering for the shared local media library.

The policy is deliberately separate from playback and from avatar/body policy.
It reads the existing media index and an exact owner decision, returns opaque
media IDs to normal UI callers, and applies the same decision again when a
caller attempts to open an item.  It never scans, opens, decodes, copies,
plays, or modifies media.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


SUPPORTED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".webm",
        ".wmv",
        ".m4v",
        ".mp3",
        ".wav",
        ".flac",
        ".m4a",
        ".aac",
        ".ogg",
        ".opus",
    }
)
GENERAL_LIBRARY_MEDIA = "GENERAL_LIBRARY_MEDIA"
MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW = (
    "MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW"
)
EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT = (
    "EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT"
)
class SharedPersonMediaAccessError(ValueError):
    """Base error for malformed or unauthorized media access."""


class AdultScopedMediaDenied(SharedPersonMediaAccessError):
    """The exact person is not authorized for an adult-scoped item."""


class IndexedMediaNotFound(SharedPersonMediaAccessError):
    """The requested opaque ID or path is not in the sealed library index."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SharedPersonMediaAccessError(f"could not read exact policy input: {path}") from exc
    if not isinstance(value, dict):
        raise SharedPersonMediaAccessError(f"policy input must be an object: {path}")
    return value


def _exact_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SharedPersonMediaAccessError(f"{field} must be a non-empty string.")
    result = value.strip()
    if len(result) > 256 or any(character.isspace() for character in result):
        raise SharedPersonMediaAccessError(f"{field} is malformed.")
    return result


def _indexed_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SharedPersonMediaAccessError("media index path must be a non-empty string.")
    raw = value.strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or path.parts[:2] != ("Data", "library"):
        raise SharedPersonMediaAccessError("media index path is outside Data/library.")
    canonical = path.as_posix()
    if canonical != raw:
        raise SharedPersonMediaAccessError("media index path is not canonical.")
    return canonical


def _indexed_directory_prefix(value: object) -> str:
    if not isinstance(value, str) or not value.strip().endswith("/"):
        raise SharedPersonMediaAccessError(
            "adult-scoped directory prefixes must be non-empty and end with '/'."
        )
    raw = value.strip().replace("\\", "/")
    directory = _indexed_path(raw[:-1])
    return directory + "/"


def media_id_for_path(project_relative_path: str) -> str:
    exact_path = _indexed_path(project_relative_path)
    return hashlib.sha256(exact_path.encode("utf-8")).hexdigest()


def _family_for_extension(extension: str) -> str:
    if extension in {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}:
        return "page_media"
    if extension in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"}:
        return "timed_video"
    return "timed_audio"


def _friendly_title(name: str) -> str:
    stem = Path(name).stem
    words = re.sub(r"[_\-]+", " ", stem).strip()
    return words or stem or "Library item"


class SharedPersonMediaAccessPolicy:
    """Read-only exact-index access policy with opaque owner-view IDs."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        access_config_path: str | Path | None = None,
        media_index_path: str | Path | None = None,
        identity_registry_path: str | Path | None = None,
    ) -> None:
        self._root = Path(project_root).resolve(strict=True)
        self._lock = threading.RLock()
        self._owner_corrections: dict[str, dict[str, Any]] = {}
        config_path = Path(access_config_path) if access_config_path else self._root / "config" / "shared_person_media_access.json"
        index_path = Path(media_index_path) if media_index_path else self._root / "Data" / "indexes" / "media_library_index.json"
        registry_path = Path(identity_registry_path) if identity_registry_path else self._root / "Avatar" / "avatar_builder" / "policies" / "candidate_identity_variant_registry.json"
        config = _load_json(config_path)
        index = _load_json(index_path)
        registry = _load_json(registry_path) if registry_path.is_file() else {"candidates": []}

        adult_ids = {_exact_id(item, "explicit_adult_candidate_id") for item in config.get("explicit_adult_candidate_ids", [])}
        non_adult_ids = {_exact_id(item, "explicit_non_adult_candidate_id") for item in config.get("explicit_non_adult_candidate_ids", [])}
        if adult_ids & non_adult_ids:
            raise SharedPersonMediaAccessError("adult and non-adult candidate IDs overlap.")
        self._explicit_adult_ids = adult_ids
        self._explicit_non_adult_ids = non_adult_ids
        self._explicit_adult_only_prefixes = tuple(
            _indexed_directory_prefix(item)
            for item in config.get("explicit_adult_only_path_prefixes", [])
        )
        self._explicit_adult_only_exact_paths = frozenset(
            _indexed_path(item)
            for item in config.get("explicit_adult_only_exact_paths", [])
        )
        self._mature_mainstream_prefixes = tuple(
            _indexed_directory_prefix(item)
            for item in config.get("mature_mainstream_path_prefixes", [])
        )
        self._mature_mainstream_exact_paths = frozenset(
            _indexed_path(item)
            for item in config.get("mature_mainstream_exact_paths", [])
        )
        ratings = config.get("mature_mainstream_metadata_ratings", [])
        if not isinstance(ratings, list):
            raise SharedPersonMediaAccessError(
                "mature_mainstream_metadata_ratings must be a list."
            )
        self._mature_mainstream_ratings = frozenset(
            str(item).strip().upper() for item in ratings if str(item).strip()
        )
        if not self._explicit_adult_only_prefixes:
            raise SharedPersonMediaAccessError(
                "explicit_adult_only_path_prefixes must contain the curated adult-folder authority."
            )
        self._registry_lanes: dict[str, str] = {}
        for candidate in registry.get("candidates", []):
            if not isinstance(candidate, dict):
                continue
            candidate_id = candidate.get("canonical_candidate_id")
            lane = (candidate.get("maturity_policy") or {}).get("lane")
            if isinstance(candidate_id, str) and isinstance(lane, str):
                self._registry_lanes[candidate_id] = lane
                for alias in candidate.get("aliases", []):
                    if isinstance(alias, str) and alias.strip():
                        self._registry_lanes[alias.strip()] = lane

        entries = index.get("entries")
        if not isinstance(entries, list):
            raise SharedPersonMediaAccessError("media library index has no entries list.")
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_path: dict[str, dict[str, Any]] = {}
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            path = _indexed_path(raw.get("path"))
            extension = str(raw.get("extension") or PurePosixPath(path).suffix).lower()
            if extension not in SUPPORTED_EXTENSIONS:
                continue
            entry = {
                "path": path,
                "name": str(raw.get("name") or PurePosixPath(path).name),
                "extension": extension,
                "family": _family_for_extension(extension),
                "media_type": str(raw.get("media_type") or ""),
                "category": str(raw.get("category") or "uncategorized"),
                "version": str(raw.get("version") or "").strip(),
                "content_rating": str(
                    raw.get("content_rating") or raw.get("rating") or ""
                ).strip(),
                "size_bytes": int(raw.get("size_bytes") or 0),
            }
            media_id = media_id_for_path(path)
            if media_id in self._by_id or path.casefold() in self._by_path:
                raise SharedPersonMediaAccessError("media index contains a duplicate supported path.")
            entry["media_id"] = media_id
            access_class, classification_source = self._automatic_access_decision(entry)
            entry["automatic_access_class"] = access_class
            entry["automatic_content_rating"] = entry["content_rating"]
            entry["automatic_classification_source"] = classification_source
            entry["access_class"] = access_class
            entry["classification_source"] = classification_source
            entry["adult_scoped"] = (
                entry["access_class"]
                == EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT
            )
            self._by_id[media_id] = entry
            self._by_path[path.casefold()] = entry

    def _automatic_access_decision(
        self, entry: Mapping[str, Any]
    ) -> tuple[str, str]:
        category = str(entry.get("category") or "")
        if category.casefold() in {"private_adult_media", "private_adult_text"}:
            return (
                EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
                f"index_category:{category.casefold()}",
            )
        path = str(entry["path"])
        if path in self._explicit_adult_only_exact_paths or any(
            path.startswith(prefix) for prefix in self._explicit_adult_only_prefixes
        ):
            return (
                EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
                "durable_owner_explicit_adult_path_policy",
            )
        rating = str(entry.get("content_rating") or "").strip().upper()
        # For material outside an explicit adult-only folder, prefer existing
        # index rating/category truth before the owner's durable exact-title or
        # exact-prefix correction.  Neither route consults filename words.
        if (
            category.casefold() == "mature_mainstream"
            or (rating and rating in self._mature_mainstream_ratings)
        ):
            return (
                MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
                (
                    f"index_content_rating:{rating}"
                    if rating and rating in self._mature_mainstream_ratings
                    else "index_category:mature_mainstream"
                ),
            )
        if path in self._mature_mainstream_exact_paths or any(
            path.startswith(prefix) for prefix in self._mature_mainstream_prefixes
        ):
            return (
                MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
                "durable_owner_mature_mainstream_path_policy",
            )
        return GENERAL_LIBRARY_MEDIA, "index_default_general_library"

    def _effective_entry(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        effective = deepcopy(dict(entry))
        media_id = str(effective.get("media_id") or "")
        with self._lock:
            correction = deepcopy(self._owner_corrections.get(media_id))
        if correction:
            effective["access_class"] = correction["resulting_access_category"]
            effective["content_rating"] = correction["resulting_content_rating"]
            effective["classification_source"] = "robert_exact_item_correction"
            effective["owner_correction_id"] = correction.get("correction_id", "")
            effective["owner_correction_file_sha256"] = correction["file_sha256"]
            effective["owner_corrected_at_utc"] = correction.get("corrected_at_utc", "")
        else:
            effective["access_class"] = effective["automatic_access_class"]
            effective["content_rating"] = effective["automatic_content_rating"]
            effective["classification_source"] = effective[
                "automatic_classification_source"
            ]
        effective["adult_scoped"] = (
            effective["access_class"]
            == EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT
        )
        return effective

    def apply_owner_correction(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Install one already hash-verified exact-item correction in memory.

        Durable append-only storage and source-file hashing belong to the owner
        correction service.  This policy rechecks the opaque ID/path binding
        and accepts only one of the three public access categories.
        """

        if not isinstance(record, Mapping):
            raise SharedPersonMediaAccessError("owner correction must be an object.")
        media_id = str(record.get("media_id") or "").strip()
        file_sha256 = str(record.get("file_sha256") or "").strip().lower()
        path = _indexed_path(record.get("project_relative_library_path"))
        access_category = str(record.get("resulting_access_category") or "").strip()
        rating = str(record.get("resulting_content_rating") or "").strip().upper()
        if not re.fullmatch(r"[0-9a-f]{64}", media_id):
            raise SharedPersonMediaAccessError("owner correction media ID is invalid.")
        if not re.fullmatch(r"[0-9a-f]{64}", file_sha256):
            raise SharedPersonMediaAccessError("owner correction file hash is invalid.")
        if access_category not in {
            GENERAL_LIBRARY_MEDIA,
            MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
            EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
        }:
            raise SharedPersonMediaAccessError("owner correction access category is invalid.")
        if not rating or len(rating) > 32:
            raise SharedPersonMediaAccessError("owner correction content rating is invalid.")
        entry = self._by_id.get(media_id)
        if entry is None or entry["path"] != path or media_id_for_path(path) != media_id:
            raise SharedPersonMediaAccessError(
                "owner correction does not match one exact indexed library item."
            )
        installed = deepcopy(dict(record))
        installed["media_id"] = media_id
        installed["file_sha256"] = file_sha256
        installed["project_relative_library_path"] = path
        installed["resulting_access_category"] = access_category
        installed["resulting_content_rating"] = rating
        with self._lock:
            self._owner_corrections[media_id] = installed
        return self.correction_context(media_id)

    def owner_correction_binding(self, media_id: str) -> dict[str, str] | None:
        """Return one internal exact-file binding without owner correction text."""

        if not isinstance(media_id, str) or not re.fullmatch(r"[0-9a-f]{64}", media_id):
            raise IndexedMediaNotFound(
                "media item is not present in the exact library index."
            )
        with self._lock:
            correction = deepcopy(self._owner_corrections.get(media_id))
        if correction is None:
            return None
        return {
            "media_id": media_id,
            "file_sha256": str(correction["file_sha256"]),
            "project_relative_library_path": str(
                correction["project_relative_library_path"]
            ),
        }

    def owner_correction_bindings(self) -> tuple[dict[str, str], ...]:
        """Return every current exact binding for server-side revalidation."""

        with self._lock:
            media_ids = tuple(sorted(self._owner_corrections))
        return tuple(
            binding
            for media_id in media_ids
            if (binding := self.owner_correction_binding(media_id)) is not None
        )

    def remove_owner_correction(
        self,
        media_id: str,
        *,
        expected_file_sha256: str,
    ) -> bool:
        """Remove only the correction whose exact hash was found stale."""

        if not isinstance(media_id, str) or not re.fullmatch(r"[0-9a-f]{64}", media_id):
            raise IndexedMediaNotFound(
                "media item is not present in the exact library index."
            )
        expected = str(expected_file_sha256 or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise SharedPersonMediaAccessError(
                "expected owner correction file hash is invalid."
            )
        with self._lock:
            current = self._owner_corrections.get(media_id)
            if current is None or current.get("file_sha256") != expected:
                return False
            del self._owner_corrections[media_id]
            return True

    def correction_context(self, media_id: str) -> dict[str, Any]:
        """Return exact internal owner context for one opaque indexed item."""

        if not isinstance(media_id, str) or not re.fullmatch(r"[0-9a-f]{64}", media_id):
            raise IndexedMediaNotFound("media item is not present in the exact library index.")
        entry = self._by_id.get(media_id)
        if entry is None:
            raise IndexedMediaNotFound("media item is not present in the exact library index.")
        effective = self._effective_entry(entry)
        return {
            "media_id": effective["media_id"],
            "project_relative_library_path": effective["path"],
            "title": _friendly_title(effective["name"]),
            "version": effective.get("version", ""),
            "content_rating": effective.get("content_rating", ""),
            "access_class": effective["access_class"],
            "classification_source": effective["classification_source"],
            "automatic_content_rating": effective["automatic_content_rating"],
            "automatic_access_class": effective["automatic_access_class"],
            "automatic_classification_source": effective[
                "automatic_classification_source"
            ],
        }

    def maturity_lane(self, person_id: str) -> str:
        exact = _exact_id(person_id, "person_id")
        if exact in self._explicit_non_adult_ids:
            return "non_adult"
        if exact in self._explicit_adult_ids:
            return "adult"
        lane = self._registry_lanes.get(exact, "unresolved")
        if lane == "adult":
            return "adult"
        if lane == "non_adult_doll_safe":
            return "non_adult"
        return "unresolved"

    def _authorize_entry(self, person_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entry = self._effective_entry(entry)
        lane = self.maturity_lane(person_id)
        if (
            entry["access_class"]
            == EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT
            and lane != "adult"
        ):
            raise AdultScopedMediaDenied("adult-scoped library media is unavailable to this person.")
        authorized = deepcopy(entry)
        authorized["requires_adult_coview"] = bool(
            lane != "adult"
            and entry["access_class"]
            == MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW
        )
        authorized["playback_status"] = (
            "adult_coview_required"
            if authorized["requires_adult_coview"]
            else "independent_playback_allowed"
        )
        return authorized

    def search(self, person_id: str, query: str, *, limit: int = 40) -> list[dict[str, Any]]:
        if not isinstance(query, str) or len(query.strip()) < 2:
            raise SharedPersonMediaAccessError("search query must contain at least two characters.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 40:
            raise SharedPersonMediaAccessError("search result limit must be within 1..40.")
        lane = self.maturity_lane(person_id)
        normalized = " ".join(re.findall(r"[a-z0-9]+", query.casefold()))
        tokens = normalized.split()
        ranked: list[tuple[int, str, dict[str, Any]]] = []
        for entry in self._by_id.values():
            effective = self._effective_entry(entry)
            if (
                effective["access_class"]
                == EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT
                and lane != "adult"
            ):
                continue
            haystack = " ".join(
                re.findall(
                    r"[a-z0-9]+",
                    f"{effective['name']} {effective['category']} {effective['path']}".casefold(),
                )
            )
            if not all(token in haystack for token in tokens):
                continue
            score = 100 if normalized in haystack else 0
            score += sum(20 for token in tokens if f" {token} " in f" {haystack} ")
            score += 10 if effective["name"].casefold().startswith(query.strip().casefold()) else 0
            ranked.append((-score, effective["name"].casefold(), effective))
        ranked.sort(key=lambda item: (item[0], item[1], item[2]["media_id"]))
        return [
            {
                "media_id": entry["media_id"],
                "title": _friendly_title(entry["name"]),
                "category": entry["category"],
                "family": _family_for_extension(entry["extension"]),
                "size_bytes": entry["size_bytes"],
                "adult_scoped": bool(entry["adult_scoped"]),
                "access_class": entry["access_class"],
                "content_rating": entry["content_rating"],
                "classification_source": entry["classification_source"],
                "adult_coview_required": bool(
                    lane != "adult"
                    and entry["access_class"]
                    == MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW
                ),
                "playback_status": (
                    "adult_coview_required"
                    if lane != "adult"
                    and entry["access_class"]
                    == MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW
                    else "independent_playback_allowed"
                ),
            }
            for _, _, entry in ranked[:limit]
        ]

    def authorize_media_id(self, person_id: str, media_id: str) -> dict[str, Any]:
        if not isinstance(media_id, str) or not re.fullmatch(r"[0-9a-f]{64}", media_id):
            raise IndexedMediaNotFound("media item is not present in the exact library index.")
        entry = self._by_id.get(media_id)
        if entry is None:
            raise IndexedMediaNotFound("media item is not present in the exact library index.")
        return self._authorize_entry(person_id, entry)

    def authorize_path(self, person_id: str, project_relative_path: str) -> dict[str, Any]:
        """Apply the same gate to a direct path; this is never a bypass."""

        path = _indexed_path(project_relative_path)
        entry = self._by_path.get(path.casefold())
        if entry is None or entry["path"] != path:
            raise IndexedMediaNotFound("media path is not present in the exact library index.")
        return self._authorize_entry(person_id, entry)

    @property
    def indexed_supported_count(self) -> int:
        return len(self._by_id)
