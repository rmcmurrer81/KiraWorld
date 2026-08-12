"""Build a review queue for shared Kira/Lisa memory candidates.

This tool does not promote memories. It only creates/updates a queue that
tracks separate Kira, Lisa, and Robert/Codex review states.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIR = PROJECT_ROOT / "Data" / "memory_promotion" / "candidates"
QUEUE_PATH = PROJECT_ROOT / "Data" / "memory_review" / "shared_memory_review_queue.json"


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


def compact_text(value, fallback: str = "") -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return fallback


def default_review_state() -> dict:
    return {
        "state": "pending",
        "summary": "",
        "private_notes": "",
        "review_source": "",
        "reviewed_at": None,
    }


def default_layers() -> dict:
    return {
        "shared_event": "",
        "kira_perspective": "",
        "lisa_perspective": "",
        "robert_inserted": "",
        "fictional_or_soft_reconstruction": "",
        "private_do_not_share": "",
        "research_needed": "",
    }


def candidate_paths() -> list[Path]:
    if not CANDIDATE_DIR.exists():
        return []
    return sorted(
        path
        for path in CANDIDATE_DIR.glob("*.json")
        if "shared" in path.name.lower() or read_json(path, {}).get("owner") == "shared"
    )


def queue_item_from_candidate(path: Path, existing: dict | None = None) -> dict:
    existing = existing or {}
    data = read_json(path, {})
    candidate_id = data.get("candidate_id") or data.get("id") or path.stem
    participant_review = data.get("participant_review", {}) if isinstance(data, dict) else {}
    source = data.get("source", {}) if isinstance(data.get("source"), dict) else {}
    privacy = data.get("privacy", {}) if isinstance(data.get("privacy"), dict) else {}

    layers = default_layers()
    layers.update(existing.get("layers", {}) if isinstance(existing.get("layers"), dict) else {})
    if not layers["shared_event"]:
        layers["shared_event"] = compact_text(data.get("summary"))
    if not layers["fictional_or_soft_reconstruction"]:
        layers["fictional_or_soft_reconstruction"] = compact_text(data.get("known_unknowns"))
    if not layers["research_needed"]:
        layers["research_needed"] = compact_text(data.get("forbidden_inferences"))

    reviews = {
        "kira": default_review_state(),
        "lisa": default_review_state(),
        "robert_codex": default_review_state(),
    }
    existing_reviews = existing.get("reviews", {}) if isinstance(existing.get("reviews"), dict) else {}
    for key in reviews:
        reviews[key].update(existing_reviews.get(key, {}) if isinstance(existing_reviews.get(key), dict) else {})

    kira_review = participant_review.get("kira_review", {}) if isinstance(participant_review.get("kira_review"), dict) else {}
    lisa_review = participant_review.get("lisa_review", {}) if isinstance(participant_review.get("lisa_review"), dict) else {}
    if reviews["kira"]["state"] == "pending" and kira_review:
        reviews["kira"].update(
            {
                "state": "qualified_yes",
                "summary": compact_text(kira_review.get("summary")),
                "private_notes": compact_text(kira_review.get("privacy_notes")),
                "review_source": kira_review.get("source", ""),
            }
        )
    if reviews["lisa"]["state"] == "pending" and lisa_review:
        reviews["lisa"].update(
            {
                "state": "qualified_yes",
                "summary": compact_text(lisa_review.get("summary")),
                "private_notes": compact_text(lisa_review.get("privacy_notes")),
                "review_source": lisa_review.get("source", ""),
            }
        )

    item = {
        "queue_id": existing.get("queue_id") or candidate_id,
        "candidate_id": candidate_id,
        "candidate_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "status": existing.get("status", "needs_robert_codex_review"),
        "promotion_status": existing.get("promotion_status", "not_promoted"),
        "title": existing.get("title") or compact_text(data.get("summary"), candidate_id)[:120],
        "summary": data.get("summary", ""),
        "detail": data.get("detail", ""),
        "participants": existing.get("participants") or ["Kira", "Lisa"],
        "privacy_level": existing.get("privacy_level") or privacy.get("level", "requires_review"),
        "sharing_rule": existing.get("sharing_rule") or privacy.get("sharing_rule", "requires_all_participant_consent"),
        "source": existing.get("source") or source,
        "layers": layers,
        "reviews": reviews,
        "notes": existing.get("notes", ""),
        "created_at": existing.get("created_at") or utc_now(),
        "updated_at": utc_now(),
    }
    return item


def build_queue() -> dict:
    queue = read_json(QUEUE_PATH, {"items": []})
    old_items = queue.get("items", []) if isinstance(queue, dict) else []
    by_candidate = {
        item.get("candidate_id"): item
        for item in old_items
        if isinstance(item, dict) and item.get("candidate_id")
    }
    items = [queue_item_from_candidate(path, by_candidate.get(read_json(path, {}).get("candidate_id") or path.stem)) for path in candidate_paths()]
    return {
        "schema": "shared_memory_review_queue_v1",
        "updated_at": utc_now(),
        "policy": {
            "rule": "Do not promote shared memories unless Kira and Lisa have separate review states and the promoted layer is the overlapping shareable version.",
            "promotion_default": "not_promoted",
            "private_by_default": True,
        },
        "items": items,
    }


def main() -> None:
    queue = build_queue()
    write_json(QUEUE_PATH, queue)
    print(json.dumps({"queue": str(QUEUE_PATH.relative_to(PROJECT_ROOT)), "items": len(queue["items"])}, indent=2))


if __name__ == "__main__":
    main()
