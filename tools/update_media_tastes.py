"""
Build evolving media taste profiles for Kira/Lisa from lightweight reactions.

This is 16GB-safe: it uses titles, categories, and small JSON reaction records.
It does not watch videos, listen to audio, or treat media as lived memory.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEDIA_INDEX = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
DEFAULT_REACTION_DIR = PROJECT_ROOT / "Data" / "tastes" / "media_reactions"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "tastes" / "media_taste_profiles"
VALID_OWNERS = {"kira", "lisa", "kira_lisa"}

STANCE_SCORE = {
    "love": 0.9,
    "like": 0.55,
    "curious": 0.25,
    "neutral": 0.0,
    "mixed": 0.0,
    "cooling": -0.25,
    "outgrown": -0.45,
    "dislike": -0.65,
}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _status_for(score: float) -> str:
    if score >= 0.72:
        return "favorite"
    if score >= 0.28:
        return "liked"
    if score > -0.2:
        return "uncertain_or_mixed"
    if score > -0.5:
        return "cooling"
    return "outgrown_or_disliked"


def _title_from_path(path: str) -> str:
    return Path(path).stem.replace("_", " ")


def infer_tags(entry: dict[str, Any]) -> list[str]:
    path = str(entry.get("path", "")).lower()
    category = str(entry.get("category", "unknown"))
    name = str(entry.get("name", "")).lower()
    text = f"{path} {name}"
    tags = {category}

    keyword_tags = {
        "history": ["history", "tudor", "victorian", "egypt", "president", "titanic", "prohibition"],
        "time_travel": ["time_travel", "time travel", "doctor_who", "12_01", "running_against_time"],
        "musical": ["frozen", "annie", "freaky_friday", "teen_beach", "lion_king", "little_mermaid", "first_date"],
        "superhero": ["spider", "power_rangers", "marvel", "gizmoduck"],
        "comfort_cartoon": ["ducktales", "miraculous", "jackie_chan_adventures"],
        "ai_identity": ["not_quite_human", "computer", "artificial_intelligence", "assistant"],
        "classic_horror": ["frankenstein", "dracula", "abbott_and_costello"],
        "documentary": ["documentary", "explained", "journey", "witness"],
    }
    for tag, words in keyword_tags.items():
        if any(word in text for word in words):
            tags.add(tag)
    return sorted(tags)


def build_empty_profile(owner: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "profile_id": f"media_taste_profile_{owner}",
        "owner": owner,
        "generated_at": now,
        "updated_at": now,
        "policy": {
            "tastes_can_change_over_time": True,
            "old_favorites_are_history_not_commands": True,
            "media_reactions_do_not_create_lived_memory": True,
            "video_audio_understanding_is_metadata_first_until_gpu": True,
            "kira_and_lisa_may_disagree": True,
        },
        "current_curiosity_tags": [],
        "source_tastes": {},
        "favorite_source_paths": [],
        "cooling_or_outgrown_source_paths": [],
        "discovery_pool": [],
        "status": "active",
    }


def reaction_to_event(reaction: dict[str, Any], reaction_path: Path | None = None) -> dict[str, Any] | None:
    source_path = str(reaction.get("source_path", "")).replace("\\", "/")
    if not source_path:
        return None
    stance = str(reaction.get("stance", "neutral"))
    score = _clamp(float(reaction.get("affinity", STANCE_SCORE.get(stance, 0.0))))
    return {
        "reaction_id": reaction.get("reaction_id", ""),
        "reaction_path": _relative(reaction_path) if reaction_path else "",
        "source_path": source_path,
        "title": reaction.get("title", _title_from_path(source_path)),
        "stance": stance,
        "affinity": score,
        "tags": reaction.get("tags", []),
        "reasons": reaction.get("reasons", []),
        "recorded_at": reaction.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "may_change_later": reaction.get("may_change_later", True) is True,
    }


def apply_event(profile: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    tastes = profile.setdefault("source_tastes", {})
    record = tastes.setdefault(
        event["source_path"],
        {
            "source_path": event["source_path"],
            "title": event.get("title", _title_from_path(event["source_path"])),
            "current_affinity": 0.0,
            "current_status": "uncertain_or_mixed",
            "tags": [],
            "history": [],
        },
    )
    record.setdefault("history", []).append(event)
    record["tags"] = sorted(set(record.get("tags", [])) | set(event.get("tags", [])))
    recent = [float(item.get("affinity", 0.0)) for item in record["history"][-3:]]
    record["current_affinity"] = round(sum(recent) / max(len(recent), 1), 3)
    record["current_status"] = _status_for(float(record["current_affinity"]))
    record["last_stance"] = event.get("stance", "neutral")
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    _refresh_profile(profile)
    return profile


def seed_discovery_pool(profile: dict[str, Any], media_index: dict[str, Any], limit: int = 40) -> dict[str, Any]:
    entries = media_index.get("entries", [])
    pool = []
    tag_counts: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        tags = infer_tags(entry)
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        if len(pool) < limit:
            pool.append(
                {
                    "source_path": entry.get("path", ""),
                    "title": _title_from_path(str(entry.get("path", ""))),
                    "category": entry.get("category", "unknown"),
                    "tags": tags,
                    "status": "untried",
                    "may_be_sampled_later": True,
                }
            )
    profile["discovery_pool"] = pool
    profile["current_curiosity_tags"] = [
        tag for tag, _count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:12]
    ]
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    return profile


def _refresh_profile(profile: dict[str, Any]) -> None:
    tastes = profile.get("source_tastes", {})
    profile["favorite_source_paths"] = sorted(
        path for path, record in tastes.items() if record.get("current_status") == "favorite"
    )
    profile["cooling_or_outgrown_source_paths"] = sorted(
        path
        for path, record in tastes.items()
        if record.get("current_status") in {"cooling", "outgrown_or_disliked"}
    )
    tags: dict[str, int] = {}
    for record in tastes.values():
        if record.get("current_status") in {"liked", "favorite", "uncertain_or_mixed"}:
            for tag in record.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1
    if tags:
        profile["current_curiosity_tags"] = [
            tag for tag, _count in sorted(tags.items(), key=lambda item: (-item[1], item[0]))[:12]
        ]


def load_reactions(owner: str, reaction_dir: Path) -> list[dict[str, Any]]:
    events = []
    if not reaction_dir.exists():
        return events
    for path in sorted(reaction_dir.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("owner") != owner:
            continue
        event = reaction_to_event(data, path)
        if event:
            events.append(event)
    return events


def build_profile(owner: str, media_index_path: Path = DEFAULT_MEDIA_INDEX, reaction_dir: Path = DEFAULT_REACTION_DIR) -> dict[str, Any]:
    profile = build_empty_profile(owner)
    if media_index_path.exists():
        seed_discovery_pool(profile, json.loads(media_index_path.read_text(encoding="utf-8")))
    for event in load_reactions(owner, reaction_dir):
        apply_event(profile, event)
    return profile


def make_reaction(owner: str, source_path: str, stance: str, reasons: list[str], tags: list[str] | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    slug = re.sub(r"[^a-z0-9]+", "_", Path(source_path).stem.lower()).strip("_")[:40] or "media"
    return {
        "reaction_id": f"media_reaction_{owner}_{slug}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "owner": owner,
        "source_path": source_path.replace("\\", "/"),
        "title": _title_from_path(source_path),
        "stance": stance,
        "affinity": STANCE_SCORE.get(stance, 0.0),
        "tags": tags or [],
        "reasons": reasons,
        "may_change_later": True,
        "does_not_create_lived_memory": True,
        "created_at": now,
        "status": "draft",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Update media taste profiles from lightweight reactions.")
    parser.add_argument("--owner", choices=sorted(VALID_OWNERS))
    parser.add_argument("--media-index", default=str(DEFAULT_MEDIA_INDEX))
    parser.add_argument("--reaction-dir", default=str(DEFAULT_REACTION_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--add-reaction", action="store_true")
    parser.add_argument("--source-path", default="")
    parser.add_argument("--stance", choices=sorted(STANCE_SCORE), default="curious")
    parser.add_argument("--reason", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    args = parser.parse_args()

    reaction_dir = Path(args.reaction_dir)
    output_dir = Path(args.output_dir)
    if not reaction_dir.is_absolute():
        reaction_dir = PROJECT_ROOT / reaction_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    media_index = Path(args.media_index)
    if not media_index.is_absolute():
        media_index = PROJECT_ROOT / media_index

    if args.add_reaction:
        if not args.owner or not args.source_path:
            raise SystemExit("--add-reaction requires --owner and --source-path")
        reaction = make_reaction(args.owner, args.source_path, args.stance, args.reason, args.tag)
        path = reaction_dir / f"{reaction['reaction_id']}.json"
        _write_json(path, reaction)
        print(f"Wrote {_relative(path)}")

    owners = [args.owner] if args.owner else sorted(VALID_OWNERS)
    for owner in owners:
        profile = build_profile(owner, media_index, reaction_dir)
        path = output_dir / f"media_taste_profile_{owner}.json"
        _write_json(path, profile)
        print(f"Wrote {_relative(path)}")


if __name__ == "__main__":
    main()
