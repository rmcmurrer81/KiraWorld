"""Create draft media preview cards from the local media library index.

These are Blockbuster-style curiosity cards for media Kira/Lisa cannot watch or
listen to yet. This first pass does not call the internet; it creates safe
lookup-pending drafts from local filenames so later metadata lookup can enrich
them without inventing watched/listened memories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "media" / "preview_cards" / "generated"

MEDIA_CATEGORIES = {
    "commercial_video",
    "documentary",
    "movie",
    "music",
    "music_video",
    "radio_show",
    "skit_or_parody_video",
    "soundtrack",
    "tutorial_video",
    "tv_clip",
}
PRIVATE_CATEGORIES = {"private_adult_media", "personal_video"}
YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_title(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[_\-.]+", " ", stem)
    stem = YEAR_RE.sub("", stem)
    stem = re.sub(r"\b(480p|720p|1080p|2160p|4k|x264|x265|h264|h265|aac|mp3|flac|web|webrip|bluray|dvdrip)\b", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\s+", " ", stem).strip(" -_")
    return stem.title() if stem else Path(name).stem


def guess_year(text: str) -> str:
    match = YEAR_RE.search(text)
    return match.group(1) if match else "unknown"


def card_id_for(path_text: str) -> str:
    digest = hashlib.sha1(path_text.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "_", Path(path_text).stem.lower()).strip("_")[:60]
    return f"preview_{slug or 'media'}_{digest}"


def is_media_entry(entry: dict[str, Any], include_private: bool) -> bool:
    media_type = str(entry.get("media_type", "")).lower()
    category = str(entry.get("category", "")).lower()
    if category in PRIVATE_CATEGORIES and not include_private:
        return False
    return media_type in {"audio", "video"} or category in MEDIA_CATEGORIES


def curiosity_text(category: str, media_type: str) -> str:
    if category in {"movie", "commercial_video", "tv_clip", "documentary", "skit_or_parody_video"}:
        return "This could help Kira or Lisa decide whether the story, setting, people, or themes sound worth watching later."
    if category in {"music", "soundtrack", "music_video", "radio_show"} or media_type == "audio":
        return "This could help Kira or Lisa decide whether the mood, artist, topic, or cultural context sounds worth listening to later."
    if category == "tutorial_video":
        return "This could help Kira or Lisa decide whether the skill or demonstration sounds useful to learn later."
    return "This could help Kira or Lisa decide whether the media sounds interesting enough to ask about later."


def make_card(entry: dict[str, Any]) -> dict[str, Any]:
    path_text = str(entry.get("path", ""))
    name = str(entry.get("name") or Path(path_text).name)
    category = str(entry.get("category", "unknown"))
    media_type = str(entry.get("media_type", "unknown"))
    year = guess_year(f"{name} {path_text}")
    title = normalize_title(name)
    card_id = card_id_for(path_text)
    privacy_default = str(entry.get("privacy_default", "owner_or_session_controlled"))

    return {
        "card_id": card_id,
        "schema": "media_preview_card_v1",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "status": "draft_lookup_pending",
        "local_media": {
            "path": path_text,
            "name": name,
            "media_type": media_type,
            "category": category,
            "privacy_default": privacy_default,
        },
        "identity": {
            "title_guess": title,
            "year_guess": year,
            "external_ids": {},
            "identity_confidence": "filename_only",
            "ambiguity_status": "needs_robert_review_or_metadata_lookup",
        },
        "preview": {
            "back_of_case_summary": (
                "Metadata preview pending. This card only says that this local media item exists. "
                "It is not proof that Kira or Lisa watched, heard, remembers, likes, or understands it yet."
            ),
            "why_kira_or_lisa_might_be_curious": curiosity_text(category, media_type),
            "tone_tags": [],
            "topic_tags": [category] if category != "unknown" else [],
            "content_notes": [],
        },
        "source_attribution": {
            "local_index": rel(DEFAULT_INDEX),
            "online_lookup_used": False,
            "metadata_sources": [],
        },
        "review": {
            "robert_review_status": "not_reviewed",
            "questions_for_robert": [
                "Is this title/year guess correct?",
                "Should this item be visible as a general preview card, private, or ignored?",
            ],
        },
        "usage_policy": {
            "may_read_preview_before_watching_or_listening": True,
            "may_create_curiosity_signal": True,
            "may_create_watch_or_listen_request": True,
            "may_be_declined_or_ignored": True,
            "may_be_kept_private": True,
            "creates_watched_or_listened_memory": False,
        },
    }


def existing_card_paths(output_dir: Path) -> set[str]:
    paths: set[str] = set()
    for path in output_dir.rglob("*.json") if output_dir.exists() else []:
        try:
            data = read_json(path)
        except Exception:
            continue
        local_path = data.get("local_media", {}).get("path") if isinstance(data.get("local_media"), dict) else ""
        if local_path:
            paths.add(str(local_path))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Build draft media preview cards from the local media index.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX), help="Path to media_library_index.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for generated draft cards")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of new cards to create; 0 means no limit")
    parser.add_argument("--include-private", action="store_true", help="Include private adult/personal media draft cards")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be created without writing cards")
    args = parser.parse_args()

    index_path = Path(args.index)
    output_dir = Path(args.output_dir)
    data = read_json(index_path)
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("Index file does not contain an entries list.")

    already = existing_card_paths(output_dir)
    candidates = [
        entry for entry in entries
        if isinstance(entry, dict)
        and is_media_entry(entry, args.include_private)
        and str(entry.get("path", "")) not in already
    ]
    if args.limit > 0:
        candidates = candidates[: args.limit]

    print(f"index_entries={len(entries)} candidates={len(candidates)} dry_run={args.dry_run}")
    for entry in candidates:
        card = make_card(entry)
        card_path = output_dir / f"{card['card_id']}.json"
        if args.dry_run:
            print(f"would_create {rel(card_path)} title={card['identity']['title_guess']} category={entry.get('category')}")
        else:
            write_json(card_path, card)
            print(f"created {rel(card_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
