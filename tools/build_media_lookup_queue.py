"""Build a review queue for media preview cards that need metadata lookup."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = PROJECT_ROOT / "Data" / "media" / "preview_cards" / "generated"
QUEUE_PATH = PROJECT_ROOT / "Data" / "media" / "preview_cards" / "media_lookup_queue.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def card_title(card: dict) -> str:
    identity = card.get("identity", {}) if isinstance(card.get("identity"), dict) else {}
    local_media = card.get("local_media", {}) if isinstance(card.get("local_media"), dict) else {}
    return str(identity.get("title_guess") or card.get("title_guess") or card.get("title") or local_media.get("name") or "").strip()


def card_year(card: dict) -> str:
    identity = card.get("identity", {}) if isinstance(card.get("identity"), dict) else {}
    return str(identity.get("year_guess") or card.get("year_guess") or card.get("year") or "").strip()


def card_media_type(card: dict) -> str:
    local_media = card.get("local_media", {}) if isinstance(card.get("local_media"), dict) else {}
    return str(card.get("media_type_guess") or card.get("media_type") or local_media.get("category") or local_media.get("media_type") or "unknown")


def main() -> None:
    existing = read_json(QUEUE_PATH, {"items": []})
    existing_items = existing.get("items", []) if isinstance(existing, dict) else []
    by_card = {item.get("card_path"): item for item in existing_items if isinstance(item, dict)}
    items = []
    for path in sorted(CARDS_DIR.glob("*.json")):
        card = read_json(path, {})
        if not isinstance(card, dict):
            continue
        rel_path = path.relative_to(PROJECT_ROOT).as_posix()
        item = by_card.get(rel_path, {})
        title = card_title(card)
        year = card_year(card)
        status = item.get("status", "needs_lookup")
        items.append(
            {
                "card_path": rel_path,
                "status": status,
                "title_guess": title,
                "year_guess": year,
                "media_type_guess": card_media_type(card),
                "lookup_source_preference": item.get("lookup_source_preference", "IMDb/TMDb/Wikipedia or other factual source"),
                "ambiguity_note": item.get(
                    "ambiguity_note",
                    "If multiple works share this title, ask Robert which one before saving metadata.",
                ),
                "resolved_title": item.get("resolved_title", ""),
                "resolved_year": item.get("resolved_year", ""),
                "resolved_source_url": item.get("resolved_source_url", ""),
                "review_note": item.get("review_note", ""),
                "preview_back_of_case_summary": item.get("preview_back_of_case_summary", ""),
                "preview_curiosity_note": item.get("preview_curiosity_note", ""),
                "lookup_results": item.get("lookup_results", []),
                "lookup_error": item.get("lookup_error", ""),
            }
        )
    queue = {
        "queue_id": "media_preview_card_lookup_queue",
        "updated_at": utc_now(),
        "policy": {
            "metadata_lookup_required_before_rich_preview": True,
            "ask_robert_on_ambiguity": True,
            "preview_cards_are_not_watched_or_listened_memories": True,
            "do_not_store_streaming_account_credentials": True,
        },
        "items": items,
    }
    write_json(QUEUE_PATH, queue)
    print(f"Wrote {QUEUE_PATH.relative_to(PROJECT_ROOT).as_posix()} with {len(items)} items")


if __name__ == "__main__":
    main()
