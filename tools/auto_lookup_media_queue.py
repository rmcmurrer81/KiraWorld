"""Auto-fill media preview-card metadata for obvious Wikipedia matches.

This is a lightweight pre-GPU helper. It updates the queue and generated
preview cards, but it does not create watched/listened memories.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from kira_media_lookup_review_panel import (
    PROJECT_ROOT,
    QUEUE_PATH,
    lookup_is_confident,
    lookup_title_for_item,
    lookup_year_for_item,
    preview_text_from_lookup,
    update_card_from_lookup,
    utc_now,
    wikipedia_lookup,
)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_result(item: dict, result: dict, status: str) -> None:
    title = str(result.get("title") or item.get("title_guess") or "")
    summary, curiosity = preview_text_from_lookup(item, result)
    item["status"] = status
    item["resolved_title"] = title
    item["resolved_year"] = item.get("resolved_year") or item.get("year_guess", "")
    item["resolved_source_url"] = str(result.get("url") or "")
    item["preview_back_of_case_summary"] = summary
    item["preview_curiosity_note"] = curiosity
    item["review_note"] = (
        f"Auto metadata lookup provider: {result.get('provider', 'Wikipedia')}\n"
        f"Query: {result.get('query', '')}\n"
        f"Best score: {result.get('best_score', '')}\n\n"
        f"Back-of-case preview:\n{summary}\n\n"
        f"Curiosity note:\n{curiosity}\n\n"
        "Preview aid only. This is not watched/listened memory."
    )
    item["reviewed_at"] = utc_now()
    item.setdefault("lookup_results", [])
    if isinstance(item["lookup_results"], list):
        item["lookup_results"].append(
            {
                "looked_up_at": utc_now(),
                "provider": result.get("provider", "Wikipedia"),
                "query": result.get("query", ""),
                "title": title,
                "url": result.get("url", ""),
                "extract": result.get("extract", ""),
                "candidates": result.get("candidates", []),
                "candidate_scores": result.get("candidate_scores", []),
                "best_score": result.get("best_score", 0),
                "auto_confident": status == "resolved_auto",
            }
        )
    update_card_from_lookup(item, result, status)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto lookup unresolved media preview cards.")
    parser.add_argument("--limit", type=int, default=20, help="Max items to look up. Use 0 for no limit.")
    parser.add_argument("--include-ambiguous", action="store_true", help="Retry ambiguous items too.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to wait between lookups.")
    args = parser.parse_args()

    queue = read_json(QUEUE_PATH, {"items": []})
    items = queue.get("items", []) if isinstance(queue, dict) else []
    allowed = {"needs_lookup", "lookup_failed", ""}
    if args.include_ambiguous:
        allowed.add("ambiguous")
    candidates = [item for item in items if isinstance(item, dict) and item.get("status", "") in allowed]
    if args.limit > 0:
        candidates = candidates[: args.limit]

    resolved = ambiguous = failed = 0
    for index, item in enumerate(candidates, start=1):
        title = lookup_title_for_item(item)
        year = lookup_year_for_item(item)
        media_type = item.get("media_type_guess") or ""
        print(f"[{index}/{len(candidates)}] {title} ({year})")
        result = wikipedia_lookup(str(title), str(year), str(media_type))
        if not result.get("ok"):
            item["status"] = "lookup_failed"
            item["lookup_error"] = result.get("error", "unknown error")
            failed += 1
        elif lookup_is_confident(item, result):
            apply_result(item, result, "resolved_auto")
            resolved += 1
        else:
            apply_result(item, result, "ambiguous")
            ambiguous += 1
        queue["updated_at"] = utc_now()
        write_json(QUEUE_PATH, queue)
        time.sleep(max(0.0, args.sleep))

    print(f"resolved_auto={resolved} ambiguous={ambiguous} failed={failed}")
    print(f"queue={QUEUE_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
