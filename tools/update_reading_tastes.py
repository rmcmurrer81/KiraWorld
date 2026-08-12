"""
Roll reading reactions into evolving taste profiles.

Taste profiles are deliberately historical. A book can be loved, cooled on,
rediscovered, or outgrown without deleting earlier reactions.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REACTION_DIR = PROJECT_ROOT / "Data" / "reading" / "reactions"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "reading" / "tastes"
VALID_OWNERS = {"kira", "lisa", "kira_lisa"}

STANCE_DEFAULT_AFFINITY = {
    "love": 0.9,
    "like": 0.6,
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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _status_for(score: float) -> str:
    if score >= 0.75:
        return "favorite"
    if score >= 0.3:
        return "liked"
    if score > -0.2:
        return "uncertain_or_mixed"
    if score > -0.5:
        return "cooling"
    return "outgrown_or_disliked"


def build_empty_profile(owner: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "profile_id": f"reading_taste_profile_{owner}",
        "owner": owner,
        "generated_at": now,
        "updated_at": now,
        "policy": {
            "tastes_can_change_over_time": True,
            "newer_reactions_may_reinterpret_older_favorites": True,
            "old_likes_are_history_not_commands": True,
            "do_not_force_rereads_from_old_favorites": True,
            "private_reactions_stay_private": True,
        },
        "source_tastes": {},
        "favorite_source_paths": [],
        "cooling_or_outgrown_source_paths": [],
        "status": "active",
    }


def reaction_to_event(reaction: dict[str, Any], reaction_path: Path | None = None) -> dict[str, Any] | None:
    source = reaction.get("source", {})
    signal = reaction.get("preference_signal")
    if not isinstance(source, dict) or not isinstance(signal, dict):
        return None
    source_path = str(source.get("source_path", "")).replace("\\", "/")
    if not source_path:
        return None
    stance = str(signal.get("stance", "neutral"))
    affinity = signal.get("current_affinity", STANCE_DEFAULT_AFFINITY.get(stance, 0.0))
    delta = signal.get("interest_delta", 0.0)
    score = _clamp(float(affinity) + float(delta) * 0.5)
    return {
        "reaction_id": reaction.get("reaction_id", ""),
        "reaction_path": _relative(reaction_path) if reaction_path else "",
        "source_path": source_path,
        "title": source.get("title", Path(source_path).stem),
        "stance": stance,
        "affinity": score,
        "reasons": signal.get("reasons", []),
        "recorded_at": reaction.get("created_at") or reaction.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        "older_reactions_can_be_reinterpreted": signal.get("older_reactions_can_be_reinterpreted") is True,
    }


def apply_event(profile: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    source_path = event["source_path"]
    tastes = profile.setdefault("source_tastes", {})
    record = tastes.setdefault(
        source_path,
        {
            "source_path": source_path,
            "title": event.get("title", Path(source_path).stem),
            "current_affinity": 0.0,
            "current_status": "uncertain_or_mixed",
            "history": [],
        },
    )
    history = record.setdefault("history", [])
    history.append(event)
    recent = [float(item.get("affinity", 0.0)) for item in history[-3:]]
    record["current_affinity"] = round(sum(recent) / max(len(recent), 1), 3)
    record["current_status"] = _status_for(float(record["current_affinity"]))
    record["last_stance"] = event.get("stance", "neutral")
    record["last_reaction_id"] = event.get("reaction_id", "")
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    _refresh_lists(profile)
    return profile


def _refresh_lists(profile: dict[str, Any]) -> None:
    tastes = profile.get("source_tastes", {})
    profile["favorite_source_paths"] = sorted(
        path for path, record in tastes.items() if record.get("current_status") == "favorite"
    )
    profile["cooling_or_outgrown_source_paths"] = sorted(
        path
        for path, record in tastes.items()
        if record.get("current_status") in {"cooling", "outgrown_or_disliked"}
    )


def load_reaction_events(owner: str, reaction_dir: Path = DEFAULT_REACTION_DIR) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(reaction_dir.rglob("*.json")):
        if "template" in path.name:
            continue
        reaction = _load_json(path)
        if reaction.get("reader") != owner:
            continue
        event = reaction_to_event(reaction, path)
        if event is not None:
            events.append(event)
    return events


def build_profile(owner: str, reaction_dir: Path = DEFAULT_REACTION_DIR) -> dict[str, Any]:
    profile = build_empty_profile(owner)
    for event in load_reaction_events(owner, reaction_dir):
        apply_event(profile, event)
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Update evolving reading taste profiles from reactions.")
    parser.add_argument("--owner", choices=sorted(VALID_OWNERS))
    parser.add_argument("--reaction-dir", default=str(DEFAULT_REACTION_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    reaction_dir = Path(args.reaction_dir)
    if not reaction_dir.is_absolute():
        reaction_dir = PROJECT_ROOT / reaction_dir
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    owners = [args.owner] if args.owner else sorted(VALID_OWNERS)
    for owner in owners:
        profile = build_profile(owner, reaction_dir)
        output_path = output_dir / f"reading_taste_profile_{owner}.json"
        _write_json(output_path, profile)
        print(f"Wrote {_relative(output_path)}")


if __name__ == "__main__":
    main()
