"""Review queue for questions Kira/Lisa ask outside the current source scope."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_PATH = PROJECT_ROOT / "Data" / "questions" / "kira_questions_for_robert_or_codex.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "question"


def load_queue(path: Path = DEFAULT_QUEUE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "queue_id": "kira_questions_for_robert_or_codex",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "policy": {
                "answer_later": True,
                "do_not_hallucinate_missing_answers": True,
                "questions_are_not_memories": True,
            },
            "questions": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("queue_id", "kira_questions_for_robert_or_codex")
    data.setdefault("created_at", utc_now())
    data.setdefault("policy", {"answer_later": True, "questions_are_not_memories": True})
    data.setdefault("questions", [])
    return data


def write_queue(queue: dict[str, Any], path: Path = DEFAULT_QUEUE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    queue["updated_at"] = utc_now()
    path.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def enqueue_question(
    *,
    owner: str,
    question: str,
    context: str,
    source_path: str = "",
    source_title: str = "",
    run_id: str = "",
    cycle: int | None = None,
    priority: str = "normal",
    queue_path: Path = DEFAULT_QUEUE_PATH,
) -> dict[str, Any] | None:
    question = re.sub(r"\s+", " ", str(question or "")).strip()
    if not question:
        return None
    owner = owner.lower().strip() or "kira"
    queue = load_queue(queue_path)
    questions = queue.setdefault("questions", [])
    existing = next(
        (
            item
            for item in questions
            if item.get("owner") == owner
            and item.get("question_normalized") == question.lower()
            and item.get("status") in {"open", "deferred"}
        ),
        None,
    )
    if existing:
        existing["last_seen_at"] = utc_now()
        existing["repeat_count"] = int(existing.get("repeat_count", 1)) + 1
        existing.setdefault("contexts", []).append(
            {"created_at": utc_now(), "context": context, "source_path": source_path, "source_title": source_title, "run_id": run_id, "cycle": cycle}
        )
        existing["contexts"] = existing["contexts"][-12:]
        write_queue(queue, queue_path)
        return existing
    item = {
        "question_id": f"{owner}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{slug(question)}",
        "owner": owner,
        "question": question,
        "question_normalized": question.lower(),
        "status": "open",
        "priority": priority,
        "created_at": utc_now(),
        "last_seen_at": utc_now(),
        "repeat_count": 1,
        "contexts": [
            {"created_at": utc_now(), "context": context, "source_path": source_path, "source_title": source_title, "run_id": run_id, "cycle": cycle}
        ],
        "answer": {
            "answered_at": "",
            "answered_by": "",
            "text": "",
            "source_links": [],
        },
        "memory_policy": {
            "not_auto_promoted": True,
            "answer_before_memory_use": True,
        },
    }
    questions.append(item)
    write_queue(queue, queue_path)
    return item


def render_open(queue_path: Path = DEFAULT_QUEUE_PATH, owner: str = "kira") -> str:
    queue = load_queue(queue_path)
    questions = [
        item
        for item in queue.get("questions", [])
        if item.get("status") in {"open", "deferred"} and str(item.get("owner", "")).lower() == owner.lower()
    ]
    if not questions:
        return f"No open questions for {owner}."
    questions.sort(key=lambda item: (item.get("priority", ""), item.get("last_seen_at", "")), reverse=True)
    lines = [f"Open questions for {owner}:"]
    for item in questions[:30]:
        lines.append(f"- {item.get('question')} (priority={item.get('priority')}, repeats={item.get('repeat_count')})")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Kira/Lisa queued questions.")
    parser.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--owner", default="kira")
    args = parser.parse_args()
    print(render_open(args.queue_path, args.owner))


if __name__ == "__main__":
    main()
