"""
Create a local-source pack draft for a future Temporary AI request.

This does not create or activate a Temporary AI. It only records which local
library items may be reviewed later, and labels video/audio as post-GPU or
transcript-needed evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "temporary_ai_source_packs"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "source_pack"


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _load_index(index_path: Path) -> dict[str, Any]:
    return json.loads(index_path.read_text(encoding="utf-8"))


def _matches_query(entry: dict[str, Any], queries: list[str]) -> bool:
    text = " ".join(str(entry.get(key, "")) for key in ("path", "name", "category", "media_type")).lower()
    return all(query.lower() in text for query in queries)


def evidence_mode(entry: dict[str, Any]) -> str:
    media_type = entry.get("media_type")
    category = entry.get("category")
    if media_type == "document" or category in {"script", "story", "novel", "comic_books", "manga"}:
        return "pre_gpu_text_extractable"
    if media_type in {"video", "audio"}:
        return "post_gpu_or_transcript_needed"
    return "metadata_only"


def build_pack(
    *,
    character_id: str,
    display_name: str,
    source_paths: list[str],
    queries: list[str],
    notes: str,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> dict[str, Any]:
    index = _load_index(index_path)
    wanted = {path.replace("\\", "/") for path in source_paths}
    entries = []
    missing = sorted(wanted)
    for entry in index.get("entries", []):
        path = str(entry.get("path", "")).replace("\\", "/")
        include = path in wanted or (queries and _matches_query(entry, queries))
        if not include:
            continue
        if path in missing:
            missing.remove(path)
        entries.append(
            {
                "source_path": path,
                "name": entry.get("name", ""),
                "category": entry.get("category", ""),
                "media_type": entry.get("media_type", ""),
                "evidence_mode": evidence_mode(entry),
                "current_pre_gpu_use": (
                    "metadata_and_filename_only"
                    if evidence_mode(entry) == "post_gpu_or_transcript_needed"
                    else "slow_reading_or_text_extraction_possible"
                ),
                "post_gpu_use": {
                    "visual_scene_review": entry.get("media_type") == "video",
                    "audio_or_voice_review": entry.get("media_type") in {"video", "audio"},
                    "character_presence_review": True,
                },
            }
        )
    entries.sort(key=lambda item: item["source_path"])
    now = datetime.now(timezone.utc).isoformat()
    return {
        "source_pack_id": f"temporary_ai_source_pack_{_slug(character_id)}",
        "created_at": now,
        "updated_at": now,
        "character_id": character_id,
        "display_name": display_name,
        "notes": notes,
        "source_count": len(entries),
        "sources": entries,
        "missing_requested_paths": missing,
        "policy": {
            "does_not_create_temporary_ai": True,
            "requires_later_review_before_activation": True,
            "video_and_audio_wait_for_gpu_or_transcripts": True,
            "source_material_remains_source": True,
            "fanfic_or_variant_sources_must_be_labeled": True,
            "do_not_treat_source_events_as_kira_or_lisa_lived_memory": True,
        },
        "status": "draft",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a future Temporary AI local source pack.")
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--source-path", action="append", default=[])
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--notes", default="")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = PROJECT_ROOT / index_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    pack = build_pack(
        character_id=args.character_id,
        display_name=args.display_name,
        source_paths=args.source_path,
        queries=args.query,
        notes=args.notes,
        index_path=index_path,
    )
    output_path = output_dir / f"{pack['source_pack_id']}.draft.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {_relative(output_path)}")
    print(f"Source count: {pack['source_count']}")
    if pack["missing_requested_paths"]:
        print("Missing requested paths:")
        for path in pack["missing_requested_paths"]:
            print(f"- {path}")


if __name__ == "__main__":
    main()
