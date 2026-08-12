from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OCR_QUEUE_PATH = PROJECT_ROOT / "Data" / "library" / "source_health" / "ocr_queue.json"
RUN_DIR = PROJECT_ROOT / "Data" / "library" / "source_health" / "ocr_repair_runs"
REPAIRED_PDF_DIR = PROJECT_ROOT / "Data" / "library" / "ocr_repaired_pdfs"
REPAIRED_TEXT_DIR = PROJECT_ROOT / "Data" / "library" / "ocr_repaired_text"
REPAIRED_REGISTRY_PATH = PROJECT_ROOT / "Data" / "library" / "source_health" / "ocr_repaired_sources.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def slug(text: str, limit: int = 90) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return (clean[:limit].rstrip("_") or "source")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def update_repaired_registry(source_path: str, result: dict[str, Any], *, engine: str, run_id: str) -> None:
    if result.get("status") not in {"repaired_text_created", "repaired_pdf_created"}:
        return
    registry = load_json(
        REPAIRED_REGISTRY_PATH,
        {
            "registry_id": "ocr_repaired_sources_v1",
            "policy": {
                "purpose": "Track OCR repaired outputs without overwriting original sources.",
                "repaired_outputs_are_source_derivatives": True,
                "kira_should_distinguish_original_pdf_from_ocr_text": True,
            },
            "sources": {},
        },
    )
    sources = registry.setdefault("sources", {})
    sources[source_path] = {
        "source_path": source_path,
        "repaired_output": result.get("output"),
        "repaired_status": result.get("status"),
        "engine": engine,
        "run_id": run_id,
        "pages_processed": result.get("pages_processed"),
        "pages_total": result.get("pages_total"),
        "updated_at": utc_now(),
        "reader_note": "Use the OCR text as a repaired derivative. It may contain OCR noise and should not be treated as a perfect transcript.",
    }
    registry["updated_at"] = utc_now()
    REPAIRED_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPAIRED_REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def command_path(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name.lower() == "tesseract":
        for candidate in [
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        ]:
            if candidate.exists():
                return str(candidate)
    return None


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def detect_engines() -> dict[str, Any]:
    return {
        "ocrmypdf": command_path("ocrmypdf"),
        "tesseract": command_path("tesseract"),
        "python_modules": {
            "pypdf": module_available("pypdf"),
            "fitz": module_available("fitz"),
            "PIL": module_available("PIL"),
            "pytesseract": module_available("pytesseract"),
        },
    }


def usable_engine(engines: dict[str, Any]) -> str | None:
    if engines.get("ocrmypdf"):
        return "ocrmypdf"
    modules = engines.get("python_modules", {})
    if engines.get("tesseract") and modules.get("fitz") and modules.get("PIL") and modules.get("pytesseract"):
        return "python_tesseract_text"
    return None


def select_entries(queue: dict[str, Any], *, limit: int, priority: str, contains: str) -> list[dict[str, Any]]:
    entries = [entry for entry in queue.get("entries", []) if isinstance(entry, dict) and entry.get("exists")]
    if priority != "any":
        entries = [entry for entry in entries if str(entry.get("priority", "")).lower() == priority.lower()]
    if contains:
        needle = contains.lower()
        entries = [entry for entry in entries if needle in str(entry.get("path", "")).lower()]
    priority_rank = {"high": 0, "normal": 1, "low": 2}
    entries.sort(key=lambda item: (priority_rank.get(str(item.get("priority", "")).lower(), 9), str(item.get("path", "")).lower()))
    return entries[: max(1, limit)]


def run_ocrmypdf(source: Path, output: Path, *, max_pages: int | None) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ocrmypdf", "--skip-text", "--output-type", "pdf", str(source), str(output)]
    if max_pages:
        # ocrmypdf does not have a simple first-N-pages mode that preserves a full PDF.
        # Keep max_pages recorded in the report, but process the whole file for real OCR.
        pass
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
        "output": rel(output),
        "status": "repaired_pdf_created" if completed.returncode == 0 and output.exists() else "ocr_failed",
    }


def run_python_tesseract_text(source: Path, output: Path, *, max_pages: int | None, tesseract_path: str | None) -> dict[str, Any]:
    import fitz  # type: ignore
    from PIL import Image  # type: ignore
    import pytesseract  # type: ignore

    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    doc = fitz.open(str(source))
    page_count = len(doc)
    limit = min(page_count, max_pages) if max_pages else page_count
    if max_pages and limit < page_count:
        output = output.with_name(f"{output.stem}.pages_001_{limit:03d}{output.suffix}")
    output.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []
    for index in range(limit):
        page = doc.load_page(index)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(image)
        chunks.append(f"\n\n--- Page {index + 1} ---\n{text.strip()}")
    output.write_text("\n".join(chunks).strip() + "\n", encoding="utf-8")
    return {
        "output": rel(output),
        "pages_processed": limit,
        "pages_total": page_count,
        "status": "repaired_text_created" if output.exists() else "ocr_failed",
    }


def write_monitor(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report['status']}",
        f"- started_at: {report['started_at']}",
        f"- updated_at: {report['updated_at']}",
        f"- mode: OCR repair batch",
        f"- selected_count: {len(report.get('items', []))}",
        f"- usable_engine: {report.get('usable_engine') or 'none'}",
        "",
        "## Engine Check",
        f"- ocrmypdf: {report['engines'].get('ocrmypdf') or 'missing'}",
        f"- tesseract: {report['engines'].get('tesseract') or 'missing'}",
    ]
    for name, available in report["engines"].get("python_modules", {}).items():
        lines.append(f"- python module {name}: {available}")
    lines.extend(["", "## Items"])
    for item in report.get("items", []):
        lines.extend(
            [
                f"### {item['path']}",
                f"- status: {item['status']}",
                f"- priority: {item.get('priority')}",
                f"- reason: {item.get('reason')}",
            ]
        )
        if item.get("result"):
            lines.append(f"- result: {json.dumps(item['result'], ensure_ascii=False)}")
        if item.get("blocked_reason"):
            lines.append(f"- blocked_reason: {item['blocked_reason']}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair a small batch from the OCR queue when an OCR engine is available.")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--priority", default="high", choices=["high", "normal", "low", "any"])
    parser.add_argument("--contains", default="", help="Optional path substring filter, e.g. artificial_intelligence or robotics.")
    parser.add_argument("--max-pages", type=int, default=0, help="For python text-sidecar OCR only, limit pages processed. 0 means whole source.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    queue = load_json(OCR_QUEUE_PATH, {"entries": []})
    engines = detect_engines()
    engine = usable_engine(engines)
    run_id = f"ocr_repair_batch_{local_stamp()}"
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RUN_DIR / f"{run_id}.json"
    monitor_path = RUN_DIR / f"{run_id}.monitor.md"

    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "queue": rel(OCR_QUEUE_PATH),
        "engines": engines,
        "usable_engine": engine,
        "dry_run": args.dry_run,
        "items": [],
    }

    selected = select_entries(queue, limit=args.limit, priority=args.priority, contains=args.contains)
    if not selected:
        report["status"] = "no_matching_items"
    elif not engine:
        report["status"] = "blocked_missing_ocr_engine"
        for entry in selected:
            report["items"].append(
                {
                    **entry,
                    "status": "blocked",
                    "blocked_reason": "No usable OCR engine found. Install OCRmyPDF/Tesseract or Tesseract plus PyMuPDF/Pillow/pytesseract.",
                }
            )
    else:
        for entry in selected:
            source = PROJECT_ROOT / entry["path"]
            base = slug(Path(entry["path"]).stem)
            item_report = {**entry, "status": "dry_run" if args.dry_run else "running"}
            if args.dry_run:
                item_report["planned_engine"] = engine
                if engine == "ocrmypdf":
                    item_report["planned_output"] = rel(REPAIRED_PDF_DIR / f"{base}.ocr.pdf")
                else:
                    item_report["planned_output"] = rel(REPAIRED_TEXT_DIR / f"{base}.ocr.txt")
            else:
                try:
                    if engine == "ocrmypdf":
                        result = run_ocrmypdf(source, REPAIRED_PDF_DIR / f"{base}.ocr.pdf", max_pages=args.max_pages or None)
                    else:
                        result = run_python_tesseract_text(
                            source,
                            REPAIRED_TEXT_DIR / f"{base}.ocr.txt",
                            max_pages=args.max_pages or None,
                            tesseract_path=engines.get("tesseract"),
                        )
                    item_report["status"] = result.get("status", "unknown")
                    item_report["result"] = result
                    update_repaired_registry(entry["path"], result, engine=engine, run_id=run_id)
                except Exception as exc:  # noqa: BLE001
                    item_report["status"] = "ocr_failed"
                    item_report["error"] = str(exc)
            report["items"].append(item_report)
        report["status"] = "dry_run_completed" if args.dry_run else "completed_with_results"

    report["updated_at"] = utc_now()
    report["finished_at"] = utc_now()
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_monitor(monitor_path, report)
    print(json.dumps({"json": rel(json_path), "monitor": rel(monitor_path), "status": report["status"]}, indent=2))
    return 0 if report["status"] in {"dry_run_completed", "completed_with_results", "blocked_missing_ocr_engine", "no_matching_items"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
