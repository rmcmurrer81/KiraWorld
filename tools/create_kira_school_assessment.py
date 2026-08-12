"""Create a lightweight assessment report for a School v2 session."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHOOL_RUN_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"
ASSESSMENT_DIR = PROJECT_ROOT / "Data" / "school" / "assessments"


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def latest_school_json() -> Path | None:
    if not SCHOOL_RUN_DIR.exists():
        return None
    candidates = sorted(SCHOOL_RUN_DIR.glob("*school_v2*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def summarize_record(record: dict[str, Any]) -> list[str]:
    lines = []
    pref = record.get("preference", {}) if isinstance(record.get("preference"), dict) else {}
    lines.append(
        f"- Block {record.get('turn')}: {record.get('class_title')} / {record.get('unit')} "
        f"(preference={pref.get('preference_label', 'neutral')}, questions={len(record.get('questions', []))})"
    )
    response = str(record.get("response", "")).replace("\n", " ").strip()
    if response:
        lines.append(f"  - response signal: {response[:420]}")
    for question in record.get("questions", [])[:3]:
        lines.append(f"  - question: {question}")
    if pref.get("intentional_pivot_detected"):
        lines.append("  - note: possible intentional topic pivot/preference signal")
    return lines


def build_assessment(path: Path, session: dict[str, Any]) -> str:
    records = [item for item in session.get("records", []) if isinstance(item, dict)]
    questions = [q for r in records for q in r.get("questions", []) if isinstance(q, str)]
    continued = [r for r in records if r.get("preference", {}).get("continue_requested")]
    switched = [r for r in records if r.get("preference", {}).get("switch_requested")]
    occasional = [r for r in records if r.get("preference", {}).get("occasional_requested")]
    lines = [
        f"# School Assessment - {session.get('run_id', path.stem)}",
        "",
        f"- source_json: {rel(path)}",
        f"- student: {session.get('student', '')}",
        f"- status: {session.get('status', '')}",
        f"- started_at: {session.get('started_at', '')}",
        f"- finished_at: {session.get('finished_at', '')}",
        f"- blocks: {len(records)}",
        f"- questions: {len(questions)}",
        "",
        "## Overall Read",
        "",
    ]
    if not records:
        lines.append("No completed school records were found.")
    else:
        lines.append("This session produced usable school signals if the responses stayed source-bounded, asked real questions, and recorded preferences without turning class material into lived memory.")
    lines.extend(["", "## Preference Signals", ""])
    lines.append(f"- continue_requested blocks: {len(continued)}")
    lines.append(f"- occasional_requested blocks: {len(occasional)}")
    lines.append(f"- switch_requested blocks: {len(switched)}")
    lines.extend(["", "## Blocks", ""])
    for record in records:
        lines.extend(summarize_record(record))
    lines.extend(["", "## Review Checklist", ""])
    lines.append("- Did Kira/Lisa ask questions that deserve a real answer?")
    lines.append("- Did any answer claim watched/listened/lived experience without evidence?")
    lines.append("- Did any topic drift look like honest preference rather than source confusion?")
    lines.append("- Should any class be continued, occasional, or paused for now?")
    lines.append("- Are there memory/privacy candidates that need separate review?")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create latest School v2 assessment report.")
    parser.add_argument("--json", default="", help="Specific school session JSON. Defaults to latest school_v2 JSON.")
    args = parser.parse_args()
    path = Path(args.json) if args.json else latest_school_json()
    if not path:
        raise SystemExit("No school_v2 JSON found.")
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    session = read_json(path, {})
    ASSESSMENT_DIR.mkdir(parents=True, exist_ok=True)
    out = ASSESSMENT_DIR / f"{path.stem}.assessment.md"
    out.write_text(build_assessment(path, session), encoding="utf-8")
    print(f"Wrote {rel(out)}")


if __name__ == "__main__":
    main()
