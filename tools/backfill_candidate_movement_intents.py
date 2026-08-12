"""Backfill candidate-authored stage directions from the public chat ledger.

The script reads only AI reply rows (``speaker_id`` -> Robert).  Robert's rows
are deliberately ineligible, so historical user wording cannot become a motor
or future-body intent.  Existing records are deduplicated by source row.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.candidate_movement_intents import (  # noqa: E402
    extract_candidate_owned_movement_intents,
    record_candidate_owned_movement_intents,
)


DEFAULT_CHAT_LOG = ROOT / "Data" / "runtime" / "kira_world_chat_log.jsonl"


def backfill(chat_log: Path) -> dict[str, object]:
    summary: dict[str, object] = {
        "chat_log": str(chat_log),
        "eligible_candidate_replies": 0,
        "replies_with_movement": 0,
        "recorded": 0,
        "deduplicated": 0,
        "candidates": {},
        "errors": [],
    }
    if not chat_log.exists():
        summary["errors"] = [f"chat log not found: {chat_log}"]
        return summary

    candidate_counts: dict[str, int] = {}
    with chat_log.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            candidate_id = str(row.get("speaker_id") or "").strip()
            label = str(row.get("speaker") or candidate_id).strip()
            target = str(row.get("to") or "").strip().lower()
            text = str(row.get("text") or "")
            if not candidate_id or target != "robert" or not text:
                continue
            if candidate_id.lower() in {"robert", "system"}:
                continue
            summary["eligible_candidate_replies"] = int(summary["eligible_candidate_replies"]) + 1
            parsed = extract_candidate_owned_movement_intents(text)
            intents = list(parsed.get("movement_intents") or [])
            if not intents:
                continue
            summary["replies_with_movement"] = int(summary["replies_with_movement"]) + 1
            try:
                result = record_candidate_owned_movement_intents(
                    candidate_id,
                    label,
                    intents,
                    source_turn_id=f"historical_chat_line_{line_number}",
                    source_at=str(row.get("at") or "") or None,
                )
            except Exception as exc:
                errors = summary["errors"]
                if isinstance(errors, list):
                    errors.append(f"line {line_number}: {type(exc).__name__}: {exc}")
                continue
            recorded = int(result.get("recorded_count") or 0)
            summary["recorded"] = int(summary["recorded"]) + recorded
            summary["deduplicated"] = int(summary["deduplicated"]) + int(
                result.get("deduplicated_count") or 0
            )
            candidate_counts[candidate_id] = candidate_counts.get(candidate_id, 0) + recorded

    summary["candidates"] = dict(sorted(candidate_counts.items()))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-log", type=Path, default=DEFAULT_CHAT_LOG)
    args = parser.parse_args()
    result = backfill(args.chat_log.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())

