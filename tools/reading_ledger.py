"""Durable reading ledger helpers for Kira/Lisa.

The ledger records exactly what chunk was read: title, source path, page/line
range, and linked chunk/reaction files. It is not a memory promoter. It is the
ground truth for later recall checks such as "what have you been reading?"
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = PROJECT_ROOT / "Data" / "reading" / "reading_ledger.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:120] or "reading"


def source_kind(source_path: str) -> str:
    lower = source_path.lower().replace("\\", "/")
    if "/fanfic/" in lower:
        return "fanfic"
    if "/scripts/" in lower:
        return "script_or_episode_source"
    if "/magazines/" in lower:
        return "magazine"
    if "/history/" in lower:
        return "history_source"
    if "/health_and_sex_education/" in lower or "/psychology_and_relationships/" in lower:
        return "adult_relationship_or_health_source"
    if "/novels/" in lower:
        return "novel"
    if "/science/" in lower:
        return "science_source"
    return "library_source"


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "ledger_id": "kira_lisa_reading_ledger",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "policy": {
            "ledger_is_not_lived_memory": True,
            "entries_are_observed_reading_chunks": True,
            "full_source_completion_requires_explicit_completed_record": True,
            "safe_recall_language": [
                "The reading ledger says I saw...",
                "I have a partial reading record for...",
                "The logged chunk was...",
            ],
            "unsafe_recall_language": [
                "I read the whole book unless the ledger says completed.",
                "I watched the whole episode unless the ledger says completed.",
                "I remember it like lived experience.",
            ],
        },
        "entries": [],
    }


def write_ledger(ledger: dict[str, Any], path: Path = LEDGER_PATH) -> None:
    ledger["updated_at"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_event_id(reader: str, source_path: str, unit_label: str) -> str:
    return f"{slug(reader)}_{slug(source_path)}_{slug(unit_label)}"


def append_reading_event(
    *,
    reader: str,
    title: str,
    source_path: str,
    position: dict[str, Any],
    chunk_path: str,
    reaction_path: str,
    session_path: str,
    status: str = "observed_partial_chunk",
    notes: list[str] | None = None,
    ledger_path: Path = LEDGER_PATH,
) -> dict[str, Any]:
    ledger = load_ledger(ledger_path)
    unit_label = str(position.get("unit_label", "unknown_position"))
    event_id = make_event_id(reader, source_path, unit_label)
    existing_ids = {str(item.get("event_id")) for item in ledger.get("entries", [])}
    entry = {
        "event_id": event_id,
        "created_at": utc_now(),
        "reader": reader,
        "title": title,
        "source_path": source_path.replace("\\", "/"),
        "source_kind": source_kind(source_path),
        "status": status,
        "position": position,
        "chunk_path": chunk_path,
        "reaction_path": reaction_path,
        "session_path": session_path,
        "completion_claim": "partial_chunk_only",
        "may_be_used_for_recall": True,
        "memory_policy": {
            "does_not_create_lived_memory": True,
            "does_not_prove_full_completion": True,
            "quote_or_page_check_required_for_plot_claims": True,
        },
        "notes": notes or [],
    }
    if event_id not in existing_ids:
        ledger.setdefault("entries", []).append(entry)
        write_ledger(ledger, ledger_path)
    return entry

