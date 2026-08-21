"""
Manage pre-GPU slow reading sessions for Kira and Lisa.

This tool does not extract full book contents. It tracks paced reading
activity, reactions, and progress so books remain experiences over time
instead of instant ingestion.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_slow_reading_session import validate_slow_reading_session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_INDEX_PATH = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
PORTABLE_INDEX_PATH = (
    PROJECT_ROOT / "Data" / "indexes" / "portable_media_library_index.json"
)
DEFAULT_INDEX_PATH = (
    PRIVATE_INDEX_PATH if PRIVATE_INDEX_PATH.is_file() else PORTABLE_INDEX_PATH
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "reading" / "sessions"
READABLE_CATEGORIES = {"novel", "story", "script", "comic_books", "manga", "history"}
READABLE_MEDIA_TYPES = {"document"}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:80] or "reading"


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_session(path: Path, session: dict[str, Any]) -> None:
    errors = validate_slow_reading_session(session)
    if errors:
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _material_type(entry: dict[str, Any]) -> str:
    category = str(entry.get("category", "other"))
    if category == "comic_books":
        return "comic"
    if category == "manga":
        return "manga"
    if category in {"novel", "story", "script"}:
        return category
    if category == "history":
        return "document"
    if entry.get("media_type") == "document":
        return "document"
    return "other"


def _source_authority(entry: dict[str, Any]) -> str:
    path = str(entry.get("path", "")).lower()
    if "/fanfic/" in path:
        return "fanfic_variant"
    if "/scripts/" in path or "/tv_shows/" in path or "/movies/" in path:
        return "canon_source"
    return "raw_library_source"


def _unit_type_for(material_type: str) -> str:
    if material_type == "script":
        return "scene"
    if material_type == "comic":
        return "issue"
    if material_type == "manga":
        return "chapter"
    if material_type in {"story", "fanfic"}:
        return "section"
    if material_type == "document":
        return "section"
    return "chapter"


def _merge_index_documents(
    primary: dict[str, Any], additive: dict[str, Any] | None
) -> dict[str, Any]:
    primary_entries = primary.get("entries")
    if not isinstance(primary_entries, list):
        raise ValueError("reading index has no entries list")
    additive_entries: list[Any] = []
    if additive is not None:
        raw_additive = additive.get("entries")
        if not isinstance(raw_additive, list):
            raise ValueError("portable reading index has no entries list")
        additive_entries = raw_additive
    merged_entries: list[Any] = []
    seen: set[str] = set()
    for raw in [*primary_entries, *additive_entries]:
        if not isinstance(raw, dict):
            merged_entries.append(raw)
            continue
        path = raw.get("path")
        key = (
            str(path).strip().replace("\\", "/").casefold()
            if isinstance(path, str)
            else ""
        )
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        merged_entries.append(raw)
    result = dict(primary)
    result["entries"] = merged_entries
    result["entry_count"] = len(merged_entries)
    result["portable_index_merged_in_memory"] = additive is not None
    return result


def _load_index(index_path: Path = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    primary = _load_json(index_path)
    additive = None
    try:
        is_private_default = index_path.resolve() == PRIVATE_INDEX_PATH.resolve()
    except OSError:
        is_private_default = False
    if is_private_default and PORTABLE_INDEX_PATH.is_file():
        additive = _load_json(PORTABLE_INDEX_PATH)
    return _merge_index_documents(primary, additive)


def readable_entries(index: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for entry in index.get("entries", []):
        category = entry.get("category")
        media_type = entry.get("media_type")
        library_use = entry.get("library_use", {})
        if (
            category in READABLE_CATEGORIES
            or media_type in READABLE_MEDIA_TYPES
            or library_use.get("can_create_slow_reading_session") is True
        ):
            entries.append(entry)
    return entries


def find_entry(index: dict[str, Any], source_path: str) -> dict[str, Any]:
    normalized = source_path.replace("\\", "/")
    for entry in index.get("entries", []):
        if entry.get("path") == normalized:
            return entry
    raise ValueError(f"Readable source path not found in index: {source_path}")


def build_session(
    source_path: str,
    reader: str,
    *,
    index_path: Path = DEFAULT_INDEX_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    unit_type: str | None = None,
    target_units: int = 1,
    pause_minutes: int = 30,
    visibility: str = "reader_private",
    status: str = "active",
) -> tuple[Path, dict[str, Any]]:
    index = _load_index(index_path)
    entry = find_entry(index, source_path)
    material_type = _material_type(entry)
    title = Path(str(entry["name"])).stem
    session_id = f"slow_reading_{reader}_{_slug(title)}"
    created_at = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": session_id,
        "reader": reader,
        "created_at": created_at,
        "updated_at": created_at,
        "material": {
            "title": title,
            "material_type": material_type,
            "source_path": entry["path"],
            "source_authority": _source_authority(entry),
            "temporary_ai_source_candidate": True,
        },
        "pacing": {
            "mode": "slow_consumption",
            "unit_type": unit_type or _unit_type_for(material_type),
            "target_units_per_session": target_units,
            "minimum_pause_between_sessions_minutes": pause_minutes,
            "allow_instant_full_ingestion": False,
            "may_stop_early": True,
            "may_reread": True,
        },
        "progress": {
            "state": "reading" if status == "active" else "draft",
            "current_unit_label": "not_started",
            "completed_units": [],
            "percent_complete_estimate": 0.0,
            "last_session_summary": "Slow reading session started.",
        },
        "reflection": {
            "shareable_summary": "Started reading slowly.",
            "private_reaction": "",
            "questions": [],
            "themes_noticed": [],
            "favorites": [],
            "discomfort_or_fears": [],
            "curiosity_triggers": [],
        },
        "inner_life_influence": {
            "may_influence_dreams": True,
            "may_influence_hopes": True,
            "may_influence_fantasies": True,
            "may_influence_fears": True,
            "may_influence_creative_projects": True,
            "influence_is_indirect": True,
            "dreams_remain_not_real_events": True,
        },
        "memory_policy": {
            "source_material_remains_source": True,
            "does_not_become_lived_memory": True,
            "does_not_create_temporary_ai_automatically": True,
            "reading_session_may_become_memory_candidate": True,
            "store_only_selected_reaction_unless_reader_chooses_more": True,
        },
        "privacy": {
            "default_visibility": visibility,
            "robert_can_see_status": True,
            "robert_can_see_private_reaction_without_permission": False,
            "may_share_summary": True,
            "public_export_allowed_without_review": False,
        },
        "status": status,
    }
    output_path = output_dir / f"{session_id}.json"
    return output_path, session


def advance_session(
    session: dict[str, Any],
    *,
    unit_label: str,
    summary: str,
    percent: float | None = None,
    private_reaction: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    progress = session["progress"]
    completed = progress.setdefault("completed_units", [])
    if unit_label not in completed:
        completed.append(unit_label)
    progress["state"] = "reading"
    progress["current_unit_label"] = unit_label
    progress["last_session_summary"] = summary
    if percent is not None:
        progress["percent_complete_estimate"] = max(0.0, min(100.0, percent))
    else:
        target = max(float(session["pacing"].get("target_units_per_session", 1)), 1.0)
        progress["percent_complete_estimate"] = min(100.0, len(completed) * (5.0 / target))
    session["reflection"]["shareable_summary"] = summary
    if private_reaction is not None:
        session["reflection"]["private_reaction"] = private_reaction
    session["updated_at"] = now
    session["status"] = "active"
    return session


def set_status(session: dict[str, Any], status: str, summary: str = "") -> dict[str, Any]:
    session["status"] = status
    session["progress"]["state"] = "completed" if status == "completed" else status
    if summary:
        session["progress"]["last_session_summary"] = summary
        session["reflection"]["shareable_summary"] = summary
    if status == "completed":
        session["progress"]["percent_complete_estimate"] = 100.0
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    return session


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Kira/Lisa slow reading sessions.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List readable library items.")

    start_parser = subparsers.add_parser("start", help="Start a slow reading session.")
    start_parser.add_argument("source_path")
    start_parser.add_argument("--reader", required=True, choices=["kira", "lisa", "kira_lisa", "robert_avatar", "temporary_ai"])
    start_parser.add_argument("--unit-type", choices=["page", "chapter", "scene", "issue", "volume", "section", "passage"])
    start_parser.add_argument("--target-units", type=int, default=1)
    start_parser.add_argument("--pause-minutes", type=int, default=30)
    start_parser.add_argument("--visibility", default="reader_private")

    advance_parser = subparsers.add_parser("advance", help="Advance one reading session by one unit.")
    advance_parser.add_argument("session_path")
    advance_parser.add_argument("--unit", required=True)
    advance_parser.add_argument("--summary", required=True)
    advance_parser.add_argument("--percent", type=float)
    advance_parser.add_argument("--private-reaction")

    status_parser = subparsers.add_parser("status", help="Set session status.")
    status_parser.add_argument("session_path")
    status_parser.add_argument("--status", required=True, choices=["paused", "completed", "abandoned", "archived"])
    status_parser.add_argument("--summary", default="")

    validate_parser = subparsers.add_parser("validate", help="Validate a slow reading session.")
    validate_parser.add_argument("session_path")

    args = parser.parse_args()
    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = PROJECT_ROOT / index_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    if args.command == "list":
        index = _load_index(index_path)
        rows = [
            {
                "path": entry["path"],
                "title": Path(entry["name"]).stem,
                "category": entry.get("category"),
                "media_type": entry.get("media_type"),
            }
            for entry in readable_entries(index)
        ]
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    if args.command == "start":
        path, session = build_session(
            args.source_path,
            args.reader,
            index_path=index_path,
            output_dir=output_dir,
            unit_type=args.unit_type,
            target_units=args.target_units,
            pause_minutes=args.pause_minutes,
            visibility=args.visibility,
        )
        _write_session(path, session)
        print(f"Wrote {_relative(path)}")
        return

    session_path = Path(getattr(args, "session_path", ""))
    if not session_path.is_absolute():
        session_path = PROJECT_ROOT / session_path
    session = _load_json(session_path)

    if args.command == "advance":
        session = advance_session(
            session,
            unit_label=args.unit,
            summary=args.summary,
            percent=args.percent,
            private_reaction=args.private_reaction,
        )
        _write_session(session_path, session)
        print(f"Updated {_relative(session_path)}")
    elif args.command == "status":
        session = set_status(session, args.status, args.summary)
        _write_session(session_path, session)
        print(f"Updated {_relative(session_path)}")
    elif args.command == "validate":
        errors = validate_slow_reading_session(session)
        if errors:
            print(f"{_relative(session_path)} is not valid:")
            for error in errors:
                print(f"- {error}")
            raise SystemExit(1)
        print(f"{_relative(session_path)} is structurally valid.")


if __name__ == "__main__":
    main()
