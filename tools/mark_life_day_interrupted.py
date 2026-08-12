"""Mark a stale life-day report as interrupted after power/process loss."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIFE_DIR = PROJECT_ROOT / "Data" / "life_sessions"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_report(value: str) -> Path:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.exists():
            return path
        candidate = LIFE_DIR / f"{value}.json"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Life-day JSON not found: {value}")
    paths = sorted(LIFE_DIR.glob("kira_life_day_24hour_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not paths:
        raise FileNotFoundError("No life-day JSON files found.")
    return paths[0]


def append_monitor(report_path: Path, report: dict[str, Any]) -> None:
    monitor_path = report_path.with_suffix(".monitor.md")
    if not monitor_path.exists():
        return
    lines = [
        "",
        "## Interruption",
        f"- interrupted_at: {report.get('interrupted_at', '')}",
        f"- reason: {report.get('interruption_reason', '')}",
        f"- cycles_preserved: {len(report.get('cycles', []))}",
        f"- preserved_backup_json: {report.get('interruption_backup_json', '')}",
        "",
    ]
    with monitor_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def mark_interrupted(report_path: Path, reason: str, force: bool = False) -> dict[str, Any]:
    report = load_json(report_path)
    if report.get("status") != "running" and not force:
        return {
            "path": rel(report_path),
            "status": report.get("status"),
            "changed": False,
            "reason": "Report was not marked running.",
        }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = report_path.with_name(f"{report_path.stem}_before_interrupt_mark_{stamp}.json")
    shutil.copy2(report_path, backup_path)
    monitor_path = report_path.with_suffix(".monitor.md")
    if monitor_path.exists():
        shutil.copy2(monitor_path, monitor_path.with_name(f"{monitor_path.stem}_before_interrupt_mark_{stamp}.monitor.md"))

    report["status"] = "interrupted"
    report["interrupted_at"] = utc_now()
    report["interruption_reason"] = reason
    report["interruption_backup_json"] = rel(backup_path)
    report["updated_at"] = report["interrupted_at"]
    report.setdefault("policy", {})["resume_supported"] = True
    write_json(report_path, report)
    append_monitor(report_path, report)
    return {
        "path": rel(report_path),
        "status": report.get("status"),
        "changed": True,
        "cycles": len(report.get("cycles", [])),
        "backup": rel(backup_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="", help="Run id or JSON path. Defaults to latest life-day JSON.")
    parser.add_argument("--reason", default="Process ended before the runner could close the report, likely power loss or OS shutdown.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = mark_interrupted(resolve_report(args.run), args.reason, force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
