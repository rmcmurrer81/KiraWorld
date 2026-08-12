"""Validate Kira/Lisa development queue files.

The queue is allowed to guide future classes, but it is not memory. This
validator catches missing review labels that would make tentative signals too
easy to promote accidentally.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TRACKS = (
    "memory_candidates",
    "curiosity_questions",
    "preference_signals",
    "next_class_choices",
)

REQUIRED_ITEM_FIELDS = ("id", "status", "confidence", "source_refs", "do_not_infer")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level value must be an object")
    return data


def validate_item(track: str, item: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(item, dict):
        return [f"{track}[{index}] must be an object"]
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item:
            errors.append(f"{track}[{index}] missing required field: {field}")
    if not isinstance(item.get("source_refs"), list) or not item.get("source_refs"):
        errors.append(f"{track}[{index}] source_refs must be a non-empty list")
    if not isinstance(item.get("do_not_infer"), list) or not item.get("do_not_infer"):
        errors.append(f"{track}[{index}] do_not_infer must be a non-empty list")
    status = str(item.get("status", "")).lower()
    if "promoted" in status and "not_promoted" not in status:
        errors.append(f"{track}[{index}] status appears promoted; queue items must not promote memory")
    return errors


def validate_queue(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rules = data.get("global_rules")
    if not isinstance(rules, dict):
        errors.append("global_rules must be an object")
    else:
        if rules.get("conversation_logs_are_memory") is not False:
            errors.append("global_rules.conversation_logs_are_memory must be false")
        if rules.get("requires_review_before_memory_promotion") is not True:
            errors.append("global_rules.requires_review_before_memory_promotion must be true")
    for track in REQUIRED_TRACKS:
        items = data.get(track)
        if not isinstance(items, list):
            errors.append(f"{track} must be a list")
            continue
        for index, item in enumerate(items):
            errors.extend(validate_item(track, item, index))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Kira development queue JSON file.")
    parser.add_argument("path", nargs="?", default="Data/development_queue/kira_development_queue_20260515.json")
    args = parser.parse_args()
    path = Path(args.path)
    data = load_json(path)
    errors = validate_queue(data)
    if errors:
        print(f"{path}: INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"{path}: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
