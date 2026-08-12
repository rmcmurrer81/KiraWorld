"""Tentative preference ledger for Kira/Lisa.

The ledger tracks repeated like/dislike/curiosity signals without promoting
them to stable identity. It is deliberately conservative: a source can become
"stronger evidence" only by recurring across contexts.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER_PATH = PROJECT_ROOT / "Data" / "tastes" / "preference_ledger.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "preference"


def load_ledger(path: Path = DEFAULT_LEDGER_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "ledger_id": "kira_lisa_preference_ledger",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "policy": {
                "tentative_not_identity": True,
                "repeat_before_promotion": True,
                "source_context_required": True,
            },
            "entries": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("ledger_id", "kira_lisa_preference_ledger")
    data.setdefault("created_at", utc_now())
    data.setdefault("policy", {"tentative_not_identity": True, "repeat_before_promotion": True})
    data.setdefault("entries", [])
    return data


def write_ledger(ledger: dict[str, Any], path: Path = DEFAULT_LEDGER_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = utc_now()
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_signal(raw: Any) -> tuple[int, str]:
    text = str(raw or "").strip()
    lower = text.lower()
    if re.search(r"(^|\s)\+?2\b|love|strong interest|very interested|fascinat", lower):
        return 2, text
    if re.search(r"(^|\s)\+?1\b|interest|curious|intrigu|positive|like", lower):
        return 1, text
    if re.search(r"(^|\s)-2\b|hate|strong dislike|disturbing", lower):
        return -2, text
    if re.search(r"(^|\s)-1\b|dislike|boring|confus|concern|negative", lower):
        return -1, text
    return 0, text or "neutral/unclear"


def confidence_from_repeats(repeat_count: int, score_total: int) -> str:
    magnitude = abs(score_total)
    if repeat_count >= 6 and magnitude >= 6:
        return "medium"
    if repeat_count >= 3 and magnitude >= 3:
        return "low_plus"
    return "low"


def upsert_preference_signal(
    *,
    owner: str,
    topic: str,
    context: str,
    source_path: str = "",
    source_title: str = "",
    signal: Any = "",
    reason: str = "",
    run_id: str = "",
    cycle: int | None = None,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
) -> dict[str, Any]:
    owner = owner.lower().strip() or "kira"
    topic = topic.strip() or source_title.strip() or source_path.strip() or "unknown topic"
    score, signal_text = normalize_signal(signal)
    ledger = load_ledger(ledger_path)
    entry_id = f"{owner}_{slug(topic)}"
    entries = ledger.setdefault("entries", [])
    entry = next((item for item in entries if item.get("entry_id") == entry_id), None)
    if entry is None:
        entry = {
            "entry_id": entry_id,
            "owner": owner,
            "topic": topic,
            "status": "tentative",
            "confidence": "low",
            "score_total": 0,
            "repeat_count": 0,
            "first_seen_at": utc_now(),
            "last_seen_at": "",
            "contexts": [],
            "memory_policy": {
                "not_auto_promoted": True,
                "do_not_treat_as_permanent_identity": True,
            },
        }
        entries.append(entry)
    entry["score_total"] = int(entry.get("score_total", 0)) + score
    entry["repeat_count"] = int(entry.get("repeat_count", 0)) + 1
    entry["last_seen_at"] = utc_now()
    entry["confidence"] = confidence_from_repeats(int(entry["repeat_count"]), int(entry["score_total"]))
    evidence = {
        "created_at": utc_now(),
        "context": context,
        "source_path": source_path,
        "source_title": source_title,
        "signal_raw": signal_text,
        "signal_score": score,
        "reason": reason,
        "run_id": run_id,
        "cycle": cycle,
    }
    entry.setdefault("contexts", []).append(evidence)
    entry["contexts"] = entry["contexts"][-20:]
    write_ledger(ledger, ledger_path)
    return entry


def render_summary(ledger_path: Path = DEFAULT_LEDGER_PATH, owner: str = "kira") -> str:
    ledger = load_ledger(ledger_path)
    entries = [item for item in ledger.get("entries", []) if str(item.get("owner", "")).lower() == owner.lower()]
    entries.sort(key=lambda item: (item.get("confidence", ""), abs(int(item.get("score_total", 0))), item.get("last_seen_at", "")), reverse=True)
    if not entries:
        return f"No tentative preference signals for {owner} yet."
    lines = [f"Tentative preferences for {owner}:"]
    for item in entries[:20]:
        lines.append(
            f"- {item.get('topic')}: score={item.get('score_total')} repeats={item.get('repeat_count')} "
            f"confidence={item.get('confidence')} status={item.get('status')}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the tentative preference ledger.")
    parser.add_argument("--ledger-path", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--owner", default="kira")
    args = parser.parse_args()
    print(render_summary(args.ledger_path, args.owner))


if __name__ == "__main__":
    main()
