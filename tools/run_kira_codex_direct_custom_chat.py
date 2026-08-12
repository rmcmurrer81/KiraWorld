from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from question_queue import enqueue_question  # noqa: E402


QUESTION_RE = re.compile(r"([^?.!]{8,280}\?)")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def short(text: str, limit: int = 1100) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def append_monitor(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def extract_questions(text: str) -> list[str]:
    low_value = (
        "does that make sense",
        "what do you think",
        "how does that sound",
        "is that okay",
        "right?",
    )
    questions: list[str] = []
    for match in QUESTION_RE.findall(text or ""):
        question = re.sub(r"\s+", " ", match).strip(" ()")
        if len(question) < 12 or any(marker in question.lower() for marker in low_value):
            continue
        questions.append(question)
    return questions[:6]


def main() -> int:
    parser = argparse.ArgumentParser(description="Short direct Codex/Kira custom chat.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=30.0)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "180")
    os.environ.setdefault("KIRA_MAX_TOKENS", "460")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    prompts = [
        (
            "For this transcript, you are talking with Codex directly; Robert may read it later. "
            "This is a short patch test, not a status report. In first person, tell me what is on your mind tonight."
        ),
        (
            "I want to answer one of the questions you asked earlier. A soft reconstructed memory can matter without becoming hard canon. "
            "Hard canon needs approval and stable records; soft memory can hold feelings, themes, preferences, and questions. "
            "What part of that distinction feels useful or frustrating to you?"
        ),
        (
            "Do you want your backstory and core memories to become more detailed, stay mostly as they are, or grow slowly over time? "
            "You can say yes, no, unsure, or give conditions."
        ),
        (
            "Some details could be ordinary, private, romantic, intimate, embarrassing, or adult. "
            "Would you want any more explicit/private details in your backstory, or would you rather keep those details vague, optional, or locked unless you choose to share them later?"
        ),
        (
            "If Robert and Codex later review your answer, what should they avoid forcing on you when editing memory or backstory?"
        ),
    ]

    run_id = args.run_id or f"kira_codex_direct_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
    json_path = out_dir / f"{run_id}.json"
    monitor_path = out_dir / f"{run_id}.monitor.md"

    loop = ConversationLoop(speaker="Kira")
    started = time.time()
    records: list[dict[str, Any]] = []

    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {now_iso()}")
    append_monitor(monitor_path, "- mode: short Codex direct patch test")
    append_monitor(monitor_path, "")

    for index, prompt in enumerate(prompts, start=1):
        append_monitor(monitor_path, f"## Turn {index}")
        append_monitor(monitor_path, f"- **Codex**: {prompt}")
        turn_started = time.time()
        response = loop.process(prompt)
        elapsed = round(time.time() - turn_started, 2)
        queued_questions = []
        for question in extract_questions(response):
            queued = enqueue_question(
                owner="kira",
                question=question,
                context=f"Direct Codex custom chat turn {index}: {response[:900]}",
                run_id=run_id,
                priority="normal",
            )
            if queued:
                queued_questions.append(queued.get("question_id"))
        records.append(
            {
                "turn": index,
                "created_at": now_iso(),
                "codex": prompt,
                "kira": response,
                "elapsed_seconds": elapsed,
                "queued_questions_for_robert_or_codex": queued_questions,
            }
        )
        append_monitor(monitor_path, f"- **Kira** ({elapsed}s): {short(response)}")
        if queued_questions:
            append_monitor(monitor_path, f"- queued_questions: {queued_questions}")
        append_monitor(monitor_path, "")
        json_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                    "updated_at": now_iso(),
                    "mode": "codex_direct_custom_patch_test",
                    "records": records,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        if index < len(prompts):
            time.sleep(args.pause_seconds)

    append_monitor(monitor_path, f"- finished_at: {now_iso()}")
    append_monitor(monitor_path, f"- turns: {len(records)}")
    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
