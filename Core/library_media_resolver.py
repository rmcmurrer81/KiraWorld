"""Safe read-only resolution of owner-selected local library media.

The resolver catalogs only paths a caller explicitly supplies.  It never
walks the library, decodes or plays media, copies source bytes, persists an
index, or turns source material into memory/canon/TemporaryAI evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from media_experience_session import MEDIA_KINDS, TEXT_PROVENANCE_KINDS


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa", ".sub", ".sbv", ".ttml", ".dfxp"}
LYRICS_EXTENSIONS = {".lrc"}
TEXT_SIDECAR_EXTENSIONS = {".txt", ".md", ".rtf", ".json", ".xml"}
GENERIC_DOCUMENT_EXTENSIONS = {".txt", ".md", ".rtf", ".docx", ".odt"}

_TRANSCRIPT_MARKERS = {"transcript", "transcription"}
_SCRIPT_MARKERS = {"script", "screenplay", "teleplay"}
_SUBTITLE_MARKERS = {"caption", "captions", "subtitle", "subtitles", "sub"}
_LYRICS_MARKERS = {"lyric", "lyrics"}
_OCR_MARKERS = {"ocr", "extracted_text"}
_MAGAZINE_PATH_MARKERS = {"magazine", "magazines", "periodical", "periodicals"}
_TV_PATH_MARKERS = {"tv", "tv_show", "tv_shows", "television", "episodes", "episode"}
_MOVIE_PATH_MARKERS = {"movie", "movies", "films", "film"}
_LANGUAGE_SUFFIX_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z]{2,4})?$", re.IGNORECASE)


class LibraryMediaResolutionError(ValueError):
    """Raised when a selection is unsafe, ambiguous, or unsupported."""


def _source_identity_from_stat(value: os.stat_result) -> dict[str, int | None]:
    return {
        "device": getattr(value, "st_dev", None),
        "inode": getattr(value, "st_ino", None),
        "size_bytes": value.st_size,
        "modified_ns": value.st_mtime_ns,
        "changed_ns": getattr(value, "st_ctime_ns", None),
    }


def _sha256_file(path: Path) -> tuple[str, int, dict[str, int | None]]:
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise LibraryMediaResolutionError("owner-selected media must be a regular file.")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    before_identity = _source_identity_from_stat(before)
    after_identity = _source_identity_from_stat(after)
    if before_identity != after_identity:
        raise LibraryMediaResolutionError("media source changed while it was being hashed.")
    return digest.hexdigest(), after.st_size, after_identity


def _tokens(path: Path) -> set[str]:
    tokens: set[str] = set()
    for part in path.parts:
        for token in re.split(r"[^a-z0-9]+", part.lower()):
            if token:
                tokens.add(token)
    return tokens


class LibraryMediaResolver:
    """Resolve explicit selections below one project's ``Data/library`` root."""

    def __init__(self, project_root: str | Path) -> None:
        logical_root = Path(project_root)
        if not logical_root.is_absolute():
            logical_root = Path.cwd() / logical_root
        self._logical_project_root = Path(os.path.abspath(logical_root))
        self._logical_library_root = self._logical_project_root / "Data" / "library"
        self._assert_existing_non_link_directory(self._logical_project_root, "project_root")
        self._assert_existing_non_link_directory(
            self._logical_project_root / "Data", "project Data directory"
        )
        self._assert_existing_non_link_directory(
            self._logical_library_root, "project Data/library directory"
        )
        self._project_root = self._logical_project_root.resolve(strict=True)
        self._library_root = self._logical_library_root.resolve(strict=True)
        try:
            self._library_root.relative_to(self._project_root)
        except ValueError as exc:
            raise LibraryMediaResolutionError(
                "Data/library must resolve inside the project root."
            ) from exc

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
            raise LibraryMediaResolutionError(
                f"could not safely inspect path component: {path}"
            ) from exc

    @classmethod
    def _assert_existing_non_link_directory(cls, path: Path, label: str) -> None:
        if not path.exists() or not path.is_dir():
            raise LibraryMediaResolutionError(f"{label} must be an existing directory.")
        if cls._is_link_like(path):
            raise LibraryMediaResolutionError(f"{label} must not be a symlink or junction.")

    def _candidate_for(self, selection: str | Path) -> Path:
        if not isinstance(selection, (str, Path)):
            raise LibraryMediaResolutionError("owner selection must be a string or Path.")
        raw_text = os.fspath(selection)
        if not raw_text or "\x00" in raw_text:
            raise LibraryMediaResolutionError("owner selection must be a non-empty safe path.")
        raw = Path(raw_text)
        if any(part == ".." for part in raw.parts):
            raise LibraryMediaResolutionError("path traversal components are not allowed.")

        if raw.is_absolute():
            candidate = raw
        elif len(raw.parts) >= 2 and raw.parts[0].lower() == "data" and raw.parts[1].lower() == "library":
            candidate = self._logical_project_root / raw
        else:
            candidate = self._logical_library_root / raw
        candidate = Path(os.path.abspath(candidate))
        try:
            relative = candidate.relative_to(self._logical_library_root)
        except ValueError as exc:
            raise LibraryMediaResolutionError(
                "owner selection must be inside project Data/library."
            ) from exc
        if not relative.parts:
            raise LibraryMediaResolutionError("owner selection must name one file.")

        current = self._logical_library_root
        for part in relative.parts:
            current = current / part
            if not current.exists():
                raise LibraryMediaResolutionError(
                    f"owner-selected library file does not exist: {selection}"
                )
            if self._is_link_like(current):
                raise LibraryMediaResolutionError(
                    "symlinks, junctions, and reparse-point selections are not allowed."
                )

        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(self._library_root)
        except ValueError as exc:
            raise LibraryMediaResolutionError(
                "resolved owner selection escapes project Data/library."
            ) from exc
        if not resolved.is_file():
            raise LibraryMediaResolutionError("owner selection must name a regular file.")
        return resolved

    @staticmethod
    def _sidecar_basename_hint(path: Path, markers: set[str]) -> str:
        stem_parts = [part for part in re.split(r"[._ -]+", path.stem) if part]
        while stem_parts and (
            stem_parts[-1].lower() in markers
            or _LANGUAGE_SUFFIX_RE.fullmatch(stem_parts[-1]) is not None
        ):
            stem_parts.pop()
        return ".".join(stem_parts) if stem_parts else path.stem

    def _classify(self, path: Path) -> dict[str, Any]:
        relative = path.relative_to(self._library_root)
        suffix = path.suffix.lower()
        tokens = _tokens(relative)
        top_level = relative.parts[0].lower() if relative.parts else ""

        def sidecar(
            role: str, provenance_kind: str, markers: set[str]
        ) -> dict[str, Any]:
            if provenance_kind not in TEXT_PROVENANCE_KINDS:
                raise LibraryMediaResolutionError(
                    f"session layer does not support {provenance_kind} provenance."
                )
            return {
                "family": "text_sidecar",
                "role": role,
                "experience_kind": None,
                "session_provenance_kind": provenance_kind,
                "is_primary_media": False,
                "is_sidecar": True,
                "association_status": "owner_selected_unbound_sidecar",
                "associated_basename_hint": self._sidecar_basename_hint(path, markers),
            }

        if suffix in SUBTITLE_EXTENSIONS:
            return sidecar("subtitle_sidecar", "subtitles", _SUBTITLE_MARKERS)
        if suffix in LYRICS_EXTENSIONS:
            return sidecar("lyrics_sidecar", "lyrics", _LYRICS_MARKERS)
        if suffix in TEXT_SIDECAR_EXTENSIONS:
            if tokens & _LYRICS_MARKERS:
                return sidecar("lyrics_sidecar", "lyrics", _LYRICS_MARKERS)
            if tokens & _SUBTITLE_MARKERS:
                return sidecar("subtitle_sidecar", "subtitles", _SUBTITLE_MARKERS)
            if tokens & _TRANSCRIPT_MARKERS:
                return sidecar("transcript_sidecar", "transcript", _TRANSCRIPT_MARKERS)
            if tokens & _SCRIPT_MARKERS:
                return sidecar("script_sidecar", "script", _SCRIPT_MARKERS)
            if tokens & _OCR_MARKERS:
                return sidecar("ocr_text_sidecar", "ocr", _OCR_MARKERS)

        if suffix in PDF_EXTENSIONS:
            magazine = top_level in _MAGAZINE_PATH_MARKERS or bool(tokens & _MAGAZINE_PATH_MARKERS)
            kind = "magazine" if magazine else "pdf"
            return {
                "family": "page_media",
                "role": "magazine_pdf" if magazine else "document_pdf",
                "experience_kind": kind,
                "session_provenance_kind": None,
                "is_primary_media": True,
                "is_sidecar": False,
                "page_source_form": "multipage_pdf",
            }
        if suffix in IMAGE_EXTENSIONS:
            magazine = top_level in _MAGAZINE_PATH_MARKERS or bool(tokens & _MAGAZINE_PATH_MARKERS)
            kind = "magazine" if magazine else "pdf"
            return {
                "family": "page_media",
                "role": "magazine_page_image" if magazine else "document_page_image",
                "experience_kind": kind,
                "session_provenance_kind": None,
                "is_primary_media": True,
                "is_sidecar": False,
                "page_source_form": "single_page_or_document_image",
            }
        if suffix in VIDEO_EXTENSIONS:
            if top_level in _TV_PATH_MARKERS or bool(tokens & _TV_PATH_MARKERS):
                kind = "tv"
                role = "tv_video"
            elif top_level in _MOVIE_PATH_MARKERS or bool(tokens & _MOVIE_PATH_MARKERS):
                kind = "movie"
                role = "movie_video"
            else:
                kind = "video"
                role = "general_video"
            return {
                "family": "timed_video",
                "role": role,
                "experience_kind": kind,
                "session_provenance_kind": None,
                "is_primary_media": True,
                "is_sidecar": False,
            }
        if suffix in AUDIO_EXTENSIONS:
            return {
                "family": "timed_audio",
                "role": "music_audio" if top_level == "music" else "audio_recording",
                "experience_kind": "music",
                "session_provenance_kind": None,
                "is_primary_media": True,
                "is_sidecar": False,
            }
        if suffix in GENERIC_DOCUMENT_EXTENSIONS:
            return {
                "family": "document_reference",
                "role": "document_text",
                "experience_kind": None,
                "session_provenance_kind": None,
                "is_primary_media": False,
                "is_sidecar": False,
                "requires_separate_reading_pipeline": True,
            }
        raise LibraryMediaResolutionError(
            f"unsupported owner-selected library file extension: {suffix or '[none]'}"
        )

    def resolve(self, owner_selected_path: str | Path) -> dict[str, Any]:
        """Return one detached, hash-bound, read-only descriptor."""

        resolved = self._candidate_for(owner_selected_path)
        classification = self._classify(resolved)
        experience_kind = classification["experience_kind"]
        if experience_kind is not None and experience_kind not in MEDIA_KINDS:
            raise LibraryMediaResolutionError(
                "classification is incompatible with MediaExperienceSession."
            )
        digest, size, source_identity = _sha256_file(resolved)
        descriptor = {
            "project_relative_path": resolved.relative_to(self._project_root).as_posix(),
            "sha256": digest,
            "size_bytes": size,
            "source_identity": source_identity,
            "extension": resolved.suffix.lower(),
            "classification": classification,
            "selection": {
                "owner_selected": True,
                "read_only_resolution": True,
                "auto_play": False,
                "auto_open": False,
                "raw_media_copied": False,
            },
            "implications": {
                "consent_inferred": False,
                "lived_memory_created": False,
                "canon_created": False,
                "temporary_ai_evidence_created": False,
                "publication_authorized": False,
            },
        }
        return json.loads(json.dumps(descriptor, ensure_ascii=False, sort_keys=True))

    def source_identity(self, owner_selected_path: str | Path) -> dict[str, Any]:
        """Return a stat-only identity after the same containment/link checks.

        A caller may cache this alongside a hash produced by :meth:`resolve`.
        Matching identity avoids repeatedly hashing a large unchanged item;
        any identity change requires a new full hash before an old exact-file
        decision can remain effective.
        """

        resolved = self._candidate_for(owner_selected_path)
        identity = _source_identity_from_stat(resolved.stat())
        return {
            "project_relative_path": resolved.relative_to(
                self._project_root
            ).as_posix(),
            "source_identity": json.loads(
                json.dumps(identity, ensure_ascii=False, sort_keys=True)
            ),
        }

    def catalog(self, owner_selected_paths: Iterable[str | Path]) -> dict[str, Any]:
        """Catalog exactly the supplied files; no discovery or recursive scan."""

        if isinstance(owner_selected_paths, (str, bytes, Path)):
            raise LibraryMediaResolutionError(
                "catalog expects an iterable of individual owner-selected paths."
            )
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for selection in owner_selected_paths:
            entry = self.resolve(selection)
            key = entry["project_relative_path"].casefold()
            if key in seen:
                raise LibraryMediaResolutionError(
                    "the same owner-selected file cannot appear twice in one catalog."
                )
            seen.add(key)
            entries.append(entry)
        entries.sort(key=lambda item: item["project_relative_path"].casefold())
        manifest_basis = [
            {
                "path": entry["project_relative_path"],
                "sha256": entry["sha256"],
                "classification": entry["classification"],
            }
            for entry in entries
        ]
        selection_sha256 = hashlib.sha256(
            json.dumps(
                manifest_basis,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        catalog = {
            "schema_version": 1,
            "library_root": "Data/library",
            "selection_count": len(entries),
            "selection_sha256": selection_sha256,
            "entries": entries,
            "behavior": {
                "owner_selected_files_only": True,
                "recursive_discovery_performed": False,
                "media_copied_or_modified": False,
                "source_opened_for_hashing_only": True,
                "media_decoded_or_played": False,
                "external_application_opened": False,
                "automatic_persistence": False,
                "video_studio_invoked": False,
            },
            "implications": {
                "consent_inferred": False,
                "lived_memory_created": False,
                "canon_created": False,
                "temporary_ai_evidence_created": False,
                "publication_authorized": False,
            },
        }
        return json.loads(json.dumps(catalog, ensure_ascii=False, sort_keys=True))

    @staticmethod
    def catalog_json(catalog: dict[str, Any]) -> str:
        """Return canonical JSON text without writing it anywhere."""

        return json.dumps(
            deepcopy(catalog),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
