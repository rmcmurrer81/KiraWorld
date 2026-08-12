from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNREADABLE_PATH = PROJECT_ROOT / "Data" / "library" / "source_health" / "unreadable_sources.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "library" / "source_health" / "ocr_queue.json"
REPAIRED_REGISTRY_PATH = PROJECT_ROOT / "Data" / "library" / "source_health" / "ocr_repaired_sources.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def priority_for(source_path: str, record: dict[str, Any]) -> str:
    lower = source_path.lower()
    reason = str(record.get("reason", "")).lower()
    if "time special edition" in lower or "artificial intelligence" in lower or "robot" in lower:
        return "high"
    if "0 extractable chars" in reason:
        return "high"
    if "autism" in lower or "philosophy" in lower or "agency" in lower:
        return "normal"
    return "normal"


def build_queue() -> dict[str, Any]:
    registry = load_json(UNREADABLE_PATH, {"sources": {}})
    repaired_registry = load_json(REPAIRED_REGISTRY_PATH, {"sources": {}})
    repaired_sources = repaired_registry.get("sources", {}) if isinstance(repaired_registry.get("sources"), dict) else {}
    sources = registry.get("sources", {}) if isinstance(registry.get("sources"), dict) else {}
    entries: list[dict[str, Any]] = []
    for source_path, record in sorted(sources.items()):
        if not isinstance(record, dict):
            continue
        absolute = PROJECT_ROOT / source_path
        repaired = repaired_sources.get(source_path) if isinstance(repaired_sources.get(source_path), dict) else None
        entries.append(
            {
                "path": source_path,
                "exists": absolute.exists(),
                "status": "ocr_repaired_output_available" if repaired else "needs_ocr",
                "priority": priority_for(source_path, record),
                "reason": record.get("reason", ""),
                "first_seen": record.get("first_seen", ""),
                "last_seen": record.get("last_seen", ""),
                "reader_behavior": record.get("reader_behavior", "skip_for_text_reading"),
                "repaired_output": repaired.get("repaired_output") if repaired else "",
                "repaired_pages": {
                    "processed": repaired.get("pages_processed") if repaired else None,
                    "total": repaired.get("pages_total") if repaired else None,
                }
                if repaired
                else {},
                "suggested_next_action": (
                    "Use the repaired OCR derivative for reading, while keeping the original PDF marked unreadable."
                    if repaired
                    else "Run OCR or replace with a text-readable copy, then rescan before returning it to Kira/Lisa reading."
                ),
                "policy": {
                    "do_not_force_original_pdf_reading_before_ocr": True,
                    "do_not_treat_extraction_failure_as_kira_error": True,
                    "after_ocr_rescan_before_unblocking": not bool(repaired),
                    "distinguish_original_from_ocr_derivative": bool(repaired),
                },
            }
        )
    return {
        "queue_id": "ocr_queue_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_registry": rel(UNREADABLE_PATH),
        "entry_count": len(entries),
        "policy": {
            "purpose": "Operational list of scanned/image-only or low-text PDFs needing OCR.",
            "this_does_not_delete_or_modify_sources": True,
            "kira_lisa_should_skip_until_repaired": True,
        },
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an OCR work queue from unreadable source health records.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    queue = build_queue()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": rel(output), "entries": queue["entry_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
