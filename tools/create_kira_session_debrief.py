"""Create a lightweight post-session debrief from Kira run/chat JSON logs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = [
    PROJECT_ROOT / "Data" / "life_sessions",
    PROJECT_ROOT / "Data" / "school" / "session_runs",
    PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats",
]
OUTPUT_DIR = PROJECT_ROOT / "Data" / "debriefs"
QUESTION_RE = re.compile(r"([^.!?\n]{8,220}\?)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def latest_json() -> Path | None:
    candidates: list[Path] = []
    for root in SEARCH_DIRS:
        if root.exists():
            candidates.extend(path for path in root.glob("*.json") if path.is_file())
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def short(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def extract_questions(text: str) -> list[str]:
    return [short(match.group(1), 180) for match in QUESTION_RE.finditer(str(text or ""))]


def summarize_life(data: dict[str, Any]) -> dict[str, Any]:
    cycles = data.get("cycles", []) if isinstance(data.get("cycles"), list) else []
    sources = Counter(str(c.get("source_title") or c.get("source_path") or "unknown") for c in cycles if isinstance(c, dict))
    actions = Counter(str(c.get("action", "unknown")) for c in cycles if isinstance(c, dict))
    issues = []
    learned = []
    questions = []
    for c in cycles:
        if not isinstance(c, dict):
            continue
        issues.extend(str(item) for item in c.get("issues", []) if item)
        effect = c.get("learning_effect", {}) if isinstance(c.get("learning_effect"), dict) else {}
        if effect.get("source_fact_learned"):
            learned.append(short(effect.get("source_fact_learned")))
        questions.extend(extract_questions(c.get("robert_response", "")))
    return {
        "kind": "life_session",
        "count_label": "cycles",
        "count": len(cycles),
        "sources": sources,
        "actions": actions,
        "issues": issues,
        "learned": learned,
        "questions": questions,
    }


def summarize_school(data: dict[str, Any]) -> dict[str, Any]:
    records = data.get("records", []) if isinstance(data.get("records"), list) else []
    classes = Counter(str(r.get("class_title") or r.get("class_id") or "unknown") for r in records if isinstance(r, dict))
    units = [short(r.get("unit", "")) for r in records if isinstance(r, dict) and r.get("unit")]
    questions = []
    answers = []
    preferences = []
    for r in records:
        if not isinstance(r, dict):
            continue
        questions.extend(r.get("questions", []) if isinstance(r.get("questions"), list) else [])
        preferences.append(str(r.get("preference", "")) or "neutral")
        for answer in r.get("answer_records", []) if isinstance(r.get("answer_records"), list) else []:
            if isinstance(answer, dict):
                answers.append(short(answer.get("answer", ""), 260))
    return {
        "kind": "school_session",
        "count_label": "blocks",
        "count": len(records),
        "classes": classes,
        "units": units,
        "questions": [short(q, 180) for q in questions],
        "answers": answers,
        "preferences": preferences,
        "issues": [],
        "learned": [short(r.get("response", ""), 260) for r in records[:5] if isinstance(r, dict)],
    }


def summarize_chat(data: dict[str, Any]) -> dict[str, Any]:
    turns = data.get("turns", []) if isinstance(data.get("turns"), list) else data.get("messages", [])
    if not isinstance(turns, list):
        turns = []
    speakers = Counter()
    questions = []
    snippets = []
    for t in turns:
        if not isinstance(t, dict):
            continue
        speaker = str(t.get("speaker") or t.get("role") or t.get("name") or "unknown")
        text = str(t.get("text") or t.get("content") or t.get("message") or "")
        speakers[speaker] += 1
        questions.extend(extract_questions(text))
        if speaker.lower() in {"kira", "lisa", "assistant"} and text:
            snippets.append(short(text, 260))
    return {
        "kind": "manual_chat",
        "count_label": "turns",
        "count": len(turns),
        "speakers": speakers,
        "questions": questions,
        "issues": [],
        "learned": snippets[:8],
    }


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("cycles"), list):
        return summarize_life(data)
    if isinstance(data.get("records"), list):
        return summarize_school(data)
    return summarize_chat(data)


def render(path: Path, data: dict[str, Any], summary: dict[str, Any]) -> str:
    run_id = str(data.get("run_id") or data.get("requested_run_id") or path.stem)
    lines = [
        f"# Debrief: {run_id}",
        "",
        f"- created_at: {utc_now()}",
        f"- source_json: {rel(path)}",
        f"- kind: {summary['kind']}",
        f"- status: {data.get('status', 'unknown')}",
        f"- started_at: {data.get('started_at', '')}",
        f"- finished_at: {data.get('finished_at', '')}",
        f"- {summary['count_label']}: {summary['count']}",
        "",
    ]
    if summary.get("sources"):
        lines.append("## Main Sources")
        for source, count in summary["sources"].most_common(8):
            lines.append(f"- {count}x {source}")
        lines.append("")
    if summary.get("classes"):
        lines.append("## Classes")
        for cls, count in summary["classes"].most_common(8):
            lines.append(f"- {count}x {cls}")
        lines.append("")
    if summary.get("actions"):
        lines.append("## Actions")
        for action, count in summary["actions"].most_common():
            lines.append(f"- {action}: {count}")
        lines.append("")
    if summary.get("units"):
        lines.append("## Units")
        for unit in summary["units"][:12]:
            lines.append(f"- {unit}")
        lines.append("")
    if summary.get("learned"):
        lines.append("## Useful Signals")
        for item in summary["learned"][:12]:
            lines.append(f"- {item}")
        lines.append("")
    if summary.get("questions"):
        lines.append("## Questions To Review")
        for q in summary["questions"][:20]:
            lines.append(f"- {q}")
        lines.append("")
    if summary.get("answers"):
        lines.append("## Teacher Answers Given")
        for a in summary["answers"][:10]:
            lines.append(f"- {a}")
        lines.append("")
    if summary.get("preferences"):
        lines.append("## Preference Signals")
        for pref, count in Counter(summary["preferences"]).most_common():
            lines.append(f"- {pref}: {count}")
        lines.append("")
    issues = summary.get("issues", [])
    lines.append("## Review Notes")
    if issues:
        for issue, count in Counter(issues).most_common(20):
            lines.append(f"- possible issue ({count}x): {issue}")
    else:
        lines.append("- No obvious issue list was present in the JSON. Human review still recommended.")
    lines.append("- Do not promote memories from this debrief automatically; use it as a review aid.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a post-session debrief markdown file.")
    parser.add_argument("--json", help="Specific session JSON to summarize")
    parser.add_argument("--latest", action="store_true", help="Summarize the newest known session JSON")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    path = Path(args.json) if args.json else latest_json()
    if not path:
        raise SystemExit("No JSON session file found.")
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    data = read_json(path)
    if not isinstance(data, dict):
        raise SystemExit("Session JSON root is not an object.")
    summary = summarize(data)
    run_id = str(data.get("run_id") or data.get("requested_run_id") or path.stem)
    output_path = Path(args.output_dir) / f"{run_id}.debrief.md"
    write_text(output_path, render(path, data, summary))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
