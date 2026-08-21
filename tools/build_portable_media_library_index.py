"""Validate the portable reading manifest and build its separate index.

This builder never reads, rewrites, or replaces the resident private
``media_library_index.json``.  Every selected file must be exact, non-adult,
and in an explicitly allowed redistribution lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "Data" / "library" / "portable_selection" / "manifest.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "Data" / "indexes" / "portable_media_library_index.json"
)
PRIVATE_INDEX = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"

ALLOWED_RIGHTS_LANES = frozenset(
    {"project_original", "us_public_domain_or_no_known_restrictions"}
)
ALLOWED_ROOTS = frozenset({"portable_selection", "public_domain_selection"})
ALLOWED_EXTENSIONS = frozenset({".pdf", ".md", ".txt"})
BLOCKED_PATH_PARTS = frozenset(
    {
        "avatar",
        "avatars",
        "private_adult_text",
        "private_adult_videos",
        "private_reference_scripts",
        "real_person_photos",
        "reference_photos",
    }
)
HEX64 = re.compile(r"[0-9a-f]{64}")


class PortableMediaIndexError(ValueError):
    """The portable manifest or one exact selected file is invalid."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortableMediaIndexError(f"could not read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise PortableMediaIndexError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_library_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PortableMediaIndexError("entry.path must be a non-empty string")
    raw = value.strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or path.parts[:2] != ("Data", "library"):
        raise PortableMediaIndexError(f"entry path is outside Data/library: {raw}")
    if path.as_posix() != raw or len(path.parts) < 4:
        raise PortableMediaIndexError(f"entry path is not canonical: {raw}")
    root = path.parts[2]
    if root not in ALLOWED_ROOTS:
        raise PortableMediaIndexError(f"entry path is outside an allowed portable lane: {raw}")
    lowered = {part.casefold() for part in path.parts}
    if lowered & BLOCKED_PATH_PARTS:
        raise PortableMediaIndexError(f"entry path uses a blocked private/photo lane: {raw}")
    return raw


def _validated_entry(raw: object, project_root: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PortableMediaIndexError("every manifest entry must be an object")
    path = _canonical_library_path(raw.get("path"))
    source = project_root / Path(*PurePosixPath(path).parts)
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to((project_root / "Data" / "library").resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise PortableMediaIndexError(f"entry file is missing or escapes Data/library: {path}") from exc
    if source.is_symlink() or not resolved.is_file():
        raise PortableMediaIndexError(f"entry must be a regular non-symlink file: {path}")

    extension = PurePosixPath(path).suffix.casefold()
    if extension not in ALLOWED_EXTENSIONS:
        raise PortableMediaIndexError(f"entry extension is not allowed: {path}")
    if raw.get("non_adult") is not True or str(raw.get("content_rating")) != "GENERAL":
        raise PortableMediaIndexError(f"entry is not explicitly general/non-adult: {path}")
    if raw.get("long_life_loop_reading_eligible") is not True:
        raise PortableMediaIndexError(f"entry is not explicitly paced-reading eligible: {path}")
    rights_lane = str(raw.get("rights_lane") or "")
    if rights_lane not in ALLOWED_RIGHTS_LANES:
        raise PortableMediaIndexError(f"entry lacks an allowed rights lane: {path}")
    rights_note = str(raw.get("rights_note") or "").strip()
    if not rights_note:
        raise PortableMediaIndexError(f"entry lacks a rights note: {path}")
    expected_hash = str(raw.get("sha256") or "").casefold()
    if not HEX64.fullmatch(expected_hash) or _sha256(resolved) != expected_hash:
        raise PortableMediaIndexError(f"entry hash does not match: {path}")
    expected_size = raw.get("size_bytes")
    if isinstance(expected_size, bool) or not isinstance(expected_size, int):
        raise PortableMediaIndexError(f"entry size is invalid: {path}")
    if resolved.stat().st_size != expected_size:
        raise PortableMediaIndexError(f"entry size does not match: {path}")
    title = str(raw.get("title") or "").strip()
    category = str(raw.get("category") or "").strip()
    if not title or not category:
        raise PortableMediaIndexError(f"entry title/category is missing: {path}")

    slow_reading = raw.get("long_life_loop_reading_eligible") is True
    media_surface = raw.get("media_surface_eligible") is True
    return {
        "path": path,
        "name": PurePosixPath(path).name,
        "title": title,
        "extension": extension,
        "media_type": str(raw.get("media_type") or "document"),
        "category": category,
        "content_rating": "GENERAL",
        "size_bytes": expected_size,
        "sha256": expected_hash,
        "privacy_default": "general_portable_library",
        "portable_rights": {
            "lane": rights_lane,
            "note": rights_note,
            "public_domain_scope_may_differ_outside_united_states": (
                rights_lane == "us_public_domain_or_no_known_restrictions"
            ),
        },
        "library_use": {
            "can_be_chosen_for_boredom_relaxation_or_curiosity": True,
            "can_create_slow_reading_session": slow_reading,
            "must_use_paced_reading": True,
            "creates_memory_automatically": False,
            "creates_temporary_ai_automatically": False,
            "source_material_remains_source": True,
            "media_surface_eligible": media_surface,
        },
        "world_display": {
            "can_appear_as_3d_object": media_surface,
            "home_shelf_eligible": media_surface,
            "virtual_screen_playback_eligible": media_surface and extension == ".pdf",
            "preferred_home_object": (
                "magazine_or_document" if extension == ".pdf" else "text_script"
            ),
            "notes": (
                "Presentation metadata only; opening a file does not prove attention, "
                "understanding, enjoyment, or completion."
            ),
        },
    }


def build_index(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    manifest = _load_object(manifest_path)
    if manifest.get("schema_version") != 1:
        raise PortableMediaIndexError("portable manifest schema_version must be 1")
    policy = manifest.get("rights_policy")
    if not isinstance(policy, dict):
        raise PortableMediaIndexError("portable manifest rights_policy is required")
    for key in (
        "modern_resident_magazines_copied",
        "private_reference_scripts_copied",
        "real_person_avatar_reference_photos_copied",
        "robert_real_photos_copied",
    ):
        if policy.get(key) is not False:
            raise PortableMediaIndexError(f"rights_policy.{key} must be false")
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise PortableMediaIndexError("portable manifest entries must be a non-empty list")
    entries = [_validated_entry(raw, project_root) for raw in raw_entries]
    paths = [entry["path"].casefold() for entry in entries]
    if len(paths) != len(set(paths)):
        raise PortableMediaIndexError("portable manifest contains duplicate paths")
    categories = {entry["category"] for entry in entries}
    if "novel" not in categories or "script" not in categories or "magazine" not in categories:
        raise PortableMediaIndexError("portable collection must contain a novel, script, and magazine")
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    return {
        "index_id": "portable_media_library_index_v1",
        "schema_version": 1,
        "source_manifest": manifest_path.relative_to(project_root).as_posix(),
        "source_manifest_sha256": _sha256(manifest_path),
        "private_index_path": "Data/indexes/media_library_index.json",
        "private_index_was_read_or_modified": False,
        "entry_count": len(entries),
        "counts_by_category": dict(sorted(counts.items())),
        "usage_policy": {
            "portable_index_is_fallback_or_additive_only": True,
            "resident_private_index_remains_primary": True,
            "slow_reading_only": True,
            "no_instant_full_ingestion": True,
            "no_automatic_memory": True,
            "no_automatic_temporary_ai": True,
            "no_real_person_avatar_reference_photos": True,
            "no_robert_real_photos": True,
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    manifest = Path(args.manifest)
    output = Path(args.output)
    if not manifest.is_absolute():
        manifest = PROJECT_ROOT / manifest
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    if output.resolve() == PRIVATE_INDEX.resolve():
        raise SystemExit("refusing to overwrite the resident private media index")
    index = build_index(manifest.resolve(), project_root=PROJECT_ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {index['entry_count']} portable entries to {output.resolve()}")


if __name__ == "__main__":
    main()
