"""
Create a draft media viewing/listening/reading note from the media index.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_media_viewing_note import validate_media_viewing_note


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "media" / "viewing_notes"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:80] or "media"


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _load_index(index_path: Path = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    return json.loads(index_path.read_text(encoding="utf-8"))


def _find_entry(index: dict[str, Any], source_path: str) -> dict[str, Any]:
    normalized = source_path.replace("\\", "/")
    for entry in index.get("entries", []):
        if entry.get("path") == normalized:
            return entry
    raise ValueError(f"Media path not found in index: {source_path}")


def _media_type_from_entry(entry: dict[str, Any]) -> str:
    category = entry.get("category")
    media_type = entry.get("media_type")
    if category == "movie":
        return "movie"
    if category == "tv_show":
        return "episode"
    if category == "music":
        return "music"
    if category == "music_video":
        return "music_video"
    if category in {"script", "story", "novel"}:
        return str(category)
    if media_type == "document":
        return "document"
    if media_type == "video":
        return "local_video"
    return "other"


def _default_access_mode(media_type: str) -> str:
    if media_type in {"movie", "episode", "music_video", "local_video"}:
        return "watched"
    if media_type == "music":
        return "listened"
    if media_type in {"script", "story", "novel", "document"}:
        return "read"
    return "mixed"


def build_note(
    source_path: str,
    viewer: str,
    reaction_summary: str,
    *,
    index_path: Path = DEFAULT_INDEX_PATH,
    access_mode: str | None = None,
    visibility: str = "owner_only",
) -> dict[str, Any]:
    index = _load_index(index_path)
    entry = _find_entry(index, source_path)
    media_type = _media_type_from_entry(entry)
    created_at = datetime.now(timezone.utc).isoformat()
    note_id = f"media_note_{viewer}_{_slug(Path(entry['name']).stem)}"

    return {
        "note_id": note_id,
        "viewer": viewer,
        "created_at": created_at,
        "media_title": Path(entry["name"]).stem,
        "media_type": media_type,
        "source_path_or_service": entry["path"],
        "source_index": {
            "index_id": index.get("index_id", ""),
            "generated_at": index.get("generated_at", ""),
        },
        "access_mode": access_mode or _default_access_mode(media_type),
        "reaction_summary": reaction_summary,
        "emotional_reactions": [],
        "questions": [],
        "preferences": {
            "liked": [],
            "disliked": [],
            "favorite_characters": [],
            "favorite_moments": [],
            "favorite_songs_or_sounds": [],
            "future_interest": [],
        },
        "possible_future_uses": {
            "may_inform_preferences": True,
            "may_inform_source_evidence_after_review": True,
            "may_inform_temporary_ai_proposal_after_review": True,
            "may_inform_world_reference_after_review": True,
        },
        "memory_policy": {
            "does_not_become_lived_memory": True,
            "does_not_create_temporary_ai_automatically": True,
            "source_material_remains_source": True,
        },
        "privacy": {
            "default_visibility": visibility,
            "may_share_summary": True,
            "public_export_allowed_without_review": False,
        },
        "status": "draft",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a draft media viewing note from Data/indexes/media_library_index.json.")
    parser.add_argument("source_path", help="Media path exactly as listed in the media index.")
    parser.add_argument("--viewer", default="kira", choices=["kira", "lisa", "kira_lisa", "robert_avatar", "other"])
    parser.add_argument("--reaction-summary", default="Draft note created for later reaction details.")
    parser.add_argument("--access-mode", default=None)
    parser.add_argument("--visibility", default="owner_only")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = PROJECT_ROOT / index_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    note = build_note(
        args.source_path,
        args.viewer,
        args.reaction_summary,
        index_path=index_path,
        access_mode=args.access_mode,
        visibility=args.visibility,
    )
    errors = validate_media_viewing_note(note)
    if errors:
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{note['note_id']}.draft.json"
    output_path.write_text(json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {_relative(output_path)}")


if __name__ == "__main__":
    main()
