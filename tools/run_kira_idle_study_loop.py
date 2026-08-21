"""
Run a lightweight supervised idle study/work loop for Kira.

This is for times when Robert is busy but wants Kira to keep accumulating
reviewable learning records. It does not create lived memory. It advances
slow-reading sessions, optionally creates small creative-writing work notes,
updates daily-life state, and writes a monitor/report for review.
"""

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

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from daily_life_manager import DailyLifeManager  # noqa: E402
from read_next_chunk import run_read_chunk  # noqa: E402
from slow_reading import build_session  # noqa: E402
from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)


SESSION_DIR = PROJECT_ROOT / "Data" / "reading" / "sessions"
IDLE_DIR = PROJECT_ROOT / "Data" / "idle_sessions"
CREATIVE_DIR = PROJECT_ROOT / "Data" / "creative_projects" / "kira"
CONTINUITY_DIGEST = PROJECT_ROOT / "Data" / "school" / "continuity" / "kira_learning_continuity_digest_20260515.json"

DEFAULT_SOURCE_PATHS = [
    "Data/library/portable_selection/magazines/reading_room_issue_001.pdf",
    "Data/library/portable_selection/scripts/the_reading_room_after_rain.md",
    "Data/library/public_domain_selection/novels/historical_romance/samantha_at_saratoga_or_flirtin_with_fashion.pdf",
    "Data/library/public_domain_selection/history/chicago/chicago_1917.pdf",
    "Data/library/public_domain_selection/science/biology_and_chemistry/naturalhistoryf00smitgoog.pdf",
    "Data/library/public_domain_selection/reference/life_skills/lifehowtoenjoyit00fowl.pdf",
    "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
    "Data/library/stories/fanfic/miraculous_ladybug/ladybug_bunnyx_king_arthur_test_fanfic.md",
    "Data/library/magazines/news_and_history/time/time_magazine/TIME Special Edition - Artificial Intelligence, 2025.pdf",
    "Data/library/magazines/entertainment/hannah_montana/disney_hannah_montana_magazine/disney_hannah_montana_magazine_issue_1_by_parasubircosasgrande_dhvhyt7_text.pdf",
    "Data/library/magazines/fashion_and_culture/simplicity_fashion_news_booklet_march_1973.pdf",
    "Data/library/magazines/fashion_and_culture/h_magazine/h_magazine/hplusmagazine_2009_summer.pdf",
    "Data/library/history/chicago/the_story_of_chicago_kirkland.pdf",
    "Data/library/history/chicago/the_book_of_the_fair_columbian_exposition_chicago_1893.pdf",
    "Data/library/history/chicago/h_h_holmes/the_holmes_pitezel_case.pdf",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "idle_study"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_monitor(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")
    if line.strip():
        print(line.rstrip(), flush=True)


def title_from_source(source_path: str) -> str:
    stem = Path(source_path).stem
    if stem == "episode_0509":
        return "Miraculous Ladybug 'Elation'"
    return stem.replace("_", " ")


def session_path_for(source_path: str, reader: str = "kira") -> Path:
    title = title_from_source(source_path)
    return SESSION_DIR / f"slow_reading_{reader}_{slug(title)}.json"


def find_existing_session(source_path: str, reader: str = "kira") -> Path | None:
    normalized = source_path.replace("\\", "/")
    if not SESSION_DIR.exists():
        return None
    for path in sorted(SESSION_DIR.glob(f"slow_reading_{reader}_*.json")):
        try:
            data = load_json(path)
        except Exception:
            continue
        material = data.get("material", {}) if isinstance(data, dict) else {}
        if str(material.get("source_path", "")).replace("\\", "/") == normalized:
            return path
    return None


def ensure_session(source_path: str, reader: str = "kira") -> Path:
    existing_by_source = find_existing_session(source_path, reader)
    if existing_by_source:
        return existing_by_source
    existing = session_path_for(source_path, reader)
    if existing.exists():
        return existing
    path, session = build_session(source_path, reader, target_units=1, pause_minutes=10)
    write_json(path, session)
    return path


def choose_sources(extra_sources: list[str]) -> list[str]:
    sources: list[str] = []
    for source in [*DEFAULT_SOURCE_PATHS, *extra_sources]:
        normalized = source.replace("\\", "/")
        path = PROJECT_ROOT / normalized
        if path.exists() and normalized not in sources:
            sources.append(normalized)
    return sources


def call_ollama(prompt: str, *, model: str, endpoint: str, timeout: int, max_tokens: int) -> str:
    require_exact_qwen35_selection(
        model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Kira writing a private creative-work note. Keep it grounded. "
                    "Do not claim lived memories. Separate source facts from invented story choices."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.65},
        **ordinary_model_request_fields(model),
    }
    response = requests.post(endpoint, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return str(data.get("message", {}).get("content", "")).strip()


def creative_work_note(*, run_id: str, backend: str, model: str, endpoint: str, timeout: int, max_tokens: int) -> dict[str, Any]:
    digest = load_json(CONTINUITY_DIGEST) if CONTINUITY_DIGEST.exists() else {}
    prompt = (
        "Create one short work note for Kira's original Chicago archivist mystery.\n"
        "Include three labels: SOURCE FACTS I CAN USE, INVENTED STORY CHOICES, NEXT QUESTION.\n"
        "Use the continuity digest safely; do not pretend Kira is literally an archivist.\n\n"
        f"Continuity summary:\n{json.dumps(digest.get('school_classes', [])[:2], ensure_ascii=False)[:2200]}"
    )
    if backend == "ollama":
        try:
            text = call_ollama(prompt, model=model, endpoint=endpoint, timeout=timeout, max_tokens=max_tokens)
            status = "ok"
        except Exception as exc:
            text = (
                "SOURCE FACTS I CAN USE: The Chicago archivist mystery should use reviewed source facts only.\n"
                "INVENTED STORY CHOICES: The main character can find conflicting records after a storm damages an archive.\n"
                "NEXT QUESTION: Which real Chicago event should be checked before it becomes part of the plot?"
            )
            status = f"fallback_after_ollama_error: {exc}"
    else:
        text = (
            "SOURCE FACTS I CAN USE: Great Chicago Fire details, World's Fair context, and H. H. Holmes claims need source labels.\n"
            "INVENTED STORY CHOICES: A fictional archivist can discover damaged records that disagree with each other.\n"
            "NEXT QUESTION: What kind of record would make the mystery emotionally important without pretending it happened to me?"
        )
        status = "stub_note"

    note = {
        "note_id": f"kira_chicago_archivist_work_note_{run_id}_{datetime.now(timezone.utc).strftime('%H%M%S')}",
        "created_at": utc_now(),
        "project": "original_chicago_archivist_mystery",
        "status": status,
        "text": text,
        "memory_policy": {
            "fictional_or_created_events_are_not_personal_history": True,
            "requires_review_before_promotion": True,
            "separate_fact_invention_character_voice": True,
        },
    }
    note_path = CREATIVE_DIR / f"{note['note_id']}.json"
    write_json(note_path, note)
    return {"note_path": rel(note_path), "status": status, "text_preview": text[:240]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Kira's supervised idle study/work loop.")
    parser.add_argument("--duration-minutes", type=float, default=30)
    parser.add_argument("--pause-seconds", type=float, default=120)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--backend", choices=["stub", "ollama"], default=os.getenv("KIRA_MODEL_BACKEND", "ollama"))
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL))
    parser.add_argument("--endpoint", default=os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "120")))
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--lines", type=int, default=60)
    parser.add_argument("--extra-source", action="append", default=[])
    parser.add_argument("--actions", default="read,creative", help="Comma-separated: read,creative")
    args = parser.parse_args()

    run_id = args.run_id or f"kira_idle_study_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_path = IDLE_DIR / f"{run_id}.json"
    monitor_path = IDLE_DIR / f"{run_id}.monitor.md"
    actions = [item.strip().lower() for item in args.actions.split(",") if item.strip()]
    sources = choose_sources(args.extra_source)
    if not sources and "read" in actions:
        raise SystemExit("No readable default or extra sources found.")

    manager = DailyLifeManager()
    started = time.time()
    deadline = started + max(0.01, args.duration_minutes) * 60.0
    results: list[dict[str, Any]] = []
    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {utc_now()}")
    append_monitor(monitor_path, f"- duration_minutes_target: {args.duration_minutes}")
    append_monitor(monitor_path, f"- backend: {args.backend}")
    append_monitor(monitor_path, "")

    cycle = 0
    while time.time() < deadline:
        action = actions[cycle % len(actions)] if actions else "read"
        entry: dict[str, Any] = {"cycle": cycle + 1, "action": action, "created_at": utc_now()}
        try:
            if action == "read":
                source = sources[(cycle // max(1, len(actions))) % len(sources)]
                session_path = ensure_session(source, "kira")
                summary = (
                    f"Kira continued slow reading `{title_from_source(source)}` during idle study. "
                    "This is a partial source chunk, not a whole-book claim."
                )
                result = run_read_chunk(
                    session_path,
                    pages=args.pages,
                    lines=args.lines,
                    reaction_summary=summary,
                    stance="curious",
                    affinity=0.25,
                    interest_delta=0.02,
                )
                manager.set_state(
                    "kira",
                    cycle_state="quiet",
                    mood="curious",
                    intensity=0.38,
                    activity_type="reading",
                    public_summary=summary,
                    source_path=source,
                    interruptibility="medium",
                    candidate_for_memory=True,
                    memory_type="reflection",
                )
                entry.update({"status": "ok", "source": source, "result": result})
                append_monitor(monitor_path, f"- {cycle + 1}. read `{title_from_source(source)}` -> {result['position']['unit_label']}")
            elif action == "creative":
                result = creative_work_note(
                    run_id=run_id,
                    backend=args.backend,
                    model=args.model,
                    endpoint=args.endpoint,
                    timeout=args.timeout,
                    max_tokens=args.max_tokens,
                )
                manager.set_state(
                    "kira",
                    cycle_state="quiet",
                    mood="reflective",
                    intensity=0.36,
                    activity_type="creative_project",
                    public_summary="Kira worked on one reviewed-note step for the original Chicago archivist mystery.",
                    source_path="Data/school/continuity/kira_learning_continuity_digest_20260515.json",
                    interruptibility="medium",
                    candidate_for_memory=True,
                    memory_type="reflection",
                )
                entry.update({"status": "ok", "result": result})
                append_monitor(monitor_path, f"- {cycle + 1}. creative note -> {result['note_path']} ({result['status']})")
            else:
                entry.update({"status": "skipped", "reason": f"unknown action {action}"})
                append_monitor(monitor_path, f"- {cycle + 1}. skipped unknown action `{action}`")
        except Exception as exc:
            entry.update({"status": "error", "error": str(exc)})
            append_monitor(monitor_path, f"- {cycle + 1}. ERROR {action}: {exc}")
        results.append(entry)
        write_json(
            report_path,
            {
                "run_id": run_id,
                "status": "running",
                "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                "updated_at": utc_now(),
                "duration_minutes_target": args.duration_minutes,
                "backend": args.backend,
                "actions": actions,
                "sources": sources,
                "results": results,
                "memory_policy": {
                    "idle_steps_are_not_lived_memory": True,
                    "reading_chunks_do_not_mean_full_completion": True,
                    "creative_notes_are_drafts_until_reviewed": True,
                },
            },
        )
        cycle += 1
        if time.time() + args.pause_seconds > deadline:
            break
        print(f"[idle] waiting {args.pause_seconds:g} seconds before the next cycle...", flush=True)
        time.sleep(max(0.0, args.pause_seconds))

    report = load_json(report_path)
    report["status"] = "completed"
    report["finished_at"] = utc_now()
    write_json(report_path, report)
    append_monitor(monitor_path, "")
    append_monitor(monitor_path, f"- finished_at: {report['finished_at']}")
    append_monitor(monitor_path, f"- cycles: {len(results)}")
    print(json.dumps({"report": rel(report_path), "monitor": rel(monitor_path), "cycles": len(results)}, indent=2))


if __name__ == "__main__":
    main()
