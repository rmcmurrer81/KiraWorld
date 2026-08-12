from __future__ import annotations

import argparse
import json
from pathlib import Path

from library_source_health import PROJECT_ROOT, mark_unreadable, rel


def pdf_text_stats(path: Path, pages_to_check: int) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF health scan requires pypdf. Install with: py -m pip install pypdf") from exc
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    chars_by_page: list[int] = []
    for index in range(min(total_pages, max(1, pages_to_check))):
        text = reader.pages[index].extract_text() or ""
        chars_by_page.append(len(text.strip()))
    return {
        "path": rel(path),
        "pages": total_pages,
        "checked_pages": len(chars_by_page),
        "chars_by_page": chars_by_page,
        "total_chars_checked": sum(chars_by_page),
        "likely_needs_ocr": sum(chars_by_page) < 80,
    }


def iter_pdf_paths(paths: list[str]) -> list[Path]:
    results: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.is_dir():
            results.extend(sorted(path.rglob("*.pdf")))
        elif path.exists() and path.suffix.lower() == ".pdf":
            results.append(path)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether PDFs have extractable text and optionally mark OCR-needed files.")
    parser.add_argument("paths", nargs="+", help="PDF files or directories to scan.")
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--mark", action="store_true", help="Write likely image-only PDFs to Data/library/source_health/unreadable_sources.json.")
    args = parser.parse_args()

    reports = []
    for path in iter_pdf_paths(args.paths):
        stats = pdf_text_stats(path, args.pages)
        reports.append(stats)
        if args.mark and stats["likely_needs_ocr"]:
            mark_unreadable(path, reason=f"Only {stats['total_chars_checked']} extractable chars across first {stats['checked_pages']} checked page(s).")
    print(json.dumps(reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

