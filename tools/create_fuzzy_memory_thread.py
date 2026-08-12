"""
Create soft, conflicting memory reconstruction threads.

These records let Kira/Lisa fill gaps like humans do while keeping the result
separate from hard canon until reviewed.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THREAD_FILE = PROJECT_ROOT / "Data" / "memory_reconstruction" / "fuzzy_memory_threads.json"
VALID_OWNERS = {"kira", "lisa"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:50] or "memory_thread"


def load_threads(path: Path = DEFAULT_THREAD_FILE) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "thread_index_id": "fuzzy_memory_threads_v1",
        "status": "active",
        "policy": {
            "gap_fills_are": "soft_reconstruction_until_reviewed",
            "conflicting_perspectives_allowed": True,
            "promotion_requires": "explicit_review_or_later_confirming_memory_seed",
            "not_a_lie_by_default": True,
            "does_not_create_exact_dates_or_dialogue": True,
            "does_not_claim_other_person_private_perspective": True,
        },
        "threads": [],
    }


def validate_thread(thread: dict[str, Any]) -> list[str]:
    errors = []
    participants = thread.get("participants", [])
    if not isinstance(participants, list) or not set(participants).issubset(VALID_OWNERS) or not participants:
        errors.append("participants must contain kira and/or lisa.")
    if thread.get("canon_status") != "soft_reconstructive_memory":
        errors.append("canon_status must be soft_reconstructive_memory.")
    perspectives = thread.get("perspectives", [])
    if not isinstance(perspectives, list) or not perspectives:
        errors.append("at least one perspective is required.")
    for perspective in perspectives:
        if not isinstance(perspective, dict):
            errors.append("perspectives must be objects.")
            continue
        if perspective.get("owner") not in VALID_OWNERS:
            errors.append("perspective owner must be kira or lisa.")
        language = str(perspective.get("allowed_language", "")).lower()
        if not any(phrase in language for phrase in ("i remember it as", "feels", "might", "soft", "picture")):
            errors.append("allowed_language should soft-frame the memory.")
    unknowns = thread.get("known_unknowns", [])
    if not isinstance(unknowns, list) or not unknowns:
        errors.append("known_unknowns must list what remains uncertain.")
    return errors


def make_thread(summary: str, perspectives: list[dict[str, str]], known_unknowns: list[str]) -> dict[str, Any]:
    participants = sorted({perspective["owner"] for perspective in perspectives})
    now = datetime.now(timezone.utc).isoformat()
    thread = {
        "thread_id": f"fuzzy_memory_{_slug(summary)}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "status": "draft_active",
        "created_at": now,
        "participants": participants,
        "summary": summary,
        "canon_status": "soft_reconstructive_memory",
        "perspectives": perspectives,
        "known_unknowns": known_unknowns,
        "conversation_rule": "Participants may compare their own perspective without forcing one version to overwrite the other.",
    }
    errors = validate_thread(thread)
    if errors:
        raise ValueError("; ".join(errors))
    return thread


def append_thread(thread: dict[str, Any], path: Path = DEFAULT_THREAD_FILE) -> dict[str, Any]:
    data = load_threads(path)
    data.setdefault("threads", []).append(thread)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a soft fuzzy memory thread.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--perspective", action="append", default=[], help="owner|claim|allowed language")
    parser.add_argument("--unknown", action="append", default=[])
    parser.add_argument("--path", default=str(DEFAULT_THREAD_FILE))
    args = parser.parse_args()

    perspectives = []
    for item in args.perspective:
        parts = [part.strip() for part in item.split("|")]
        if len(parts) != 3:
            raise SystemExit("--perspective must be owner|claim|allowed language")
        perspectives.append({"owner": parts[0], "claim": parts[1], "certainty": "low_to_medium", "allowed_language": parts[2]})
    if not perspectives:
        raise SystemExit("At least one --perspective is required.")
    thread = make_thread(args.summary, perspectives, args.unknown or ["exact details remain uncertain"])
    append_thread(thread, Path(args.path))
    print(f"Wrote {thread['thread_id']}")


if __name__ == "__main__":
    main()
