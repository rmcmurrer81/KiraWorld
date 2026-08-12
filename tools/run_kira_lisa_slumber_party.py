"""
Run a long Kira/Lisa slumber-party style dialogue.

This runner is intentionally looser than the school/evaluation runners. It
alternates Kira and Lisa, sometimes adds a short group-reading card, and saves
JSON plus Markdown so Robert can review the results later.
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

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "Core") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)

OUTPUT_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_lisa" / "slumber_party"
DEFAULT_MODEL = os.getenv("KIRA_OLLAMA_MODEL", QWEN_TEXT_VOICE_MODEL)
OLLAMA_URL = os.getenv("KIRA_OLLAMA_URL", "http://localhost:11434/api/chat")

SOURCE_PATHS = [
    PROJECT_ROOT / "Data/library/stories/fanfic/miraculous_ladybug/miraculous_encounters_in_paris.pdf",
    PROJECT_ROOT / "Data/library/magazines/entertainment/hannah_montana/disney_hannah_montana_magazine/disney_hannah_montana_magazine_issue_1_by_parasubircosasgrande_dhvhyt7_text.pdf",
    PROJECT_ROOT / "Data/library/magazines/fashion_and_culture/simplicity_fashion_news_booklet_march_1973.pdf",
    PROJECT_ROOT / "Data/library/magazines/fashion_and_culture/h_magazine/h_magazine/hplusmagazine_2009_summer.pdf",
    PROJECT_ROOT / "Data/library/history/chicago/the_story_of_chicago_kirkland.pdf",
    PROJECT_ROOT / "Data/library/history/chicago/the_book_of_the_fair_columbian_exposition_chicago_1893.pdf",
    PROJECT_ROOT / "Data/library/history/chicago/h_h_holmes/the_holmes_pitezel_case.pdf",
]
ADULT_SOURCE_PACK = PROJECT_ROOT / "Data/school/source_packs/kira_lisa_sex_intimacy_relationships_source_pack_20260514_084154.json"

WARNING_RE = re.compile(
    r"\b("
    r"as an ai|language model|private grounding note|source-grounded|worksheet|status report|"
    r"i read the whole|i watched the whole|actual show canon|my childhood|our childhood|"
    r"i know lisa feels|lisa secretly feels|we had sex"
    r")\b",
    re.IGNORECASE,
)


def utc_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_text(text: str, limit: int = 1200) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit].strip()


def read_pdf_page(path: Path, page_index: int) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return ""
    try:
        reader = PdfReader(str(path))
        if page_index >= len(reader.pages):
            return ""
        return clean_text(reader.pages[page_index].extract_text() or "")
    except Exception:
        return ""


def load_adult_cards() -> list[dict[str, Any]]:
    if not ADULT_SOURCE_PACK.exists():
        return []
    try:
        pack = json.loads(ADULT_SOURCE_PACK.read_text(encoding="utf-8"))
    except Exception:
        return []
    cards: list[dict[str, Any]] = []
    for source in pack.get("source_cards", []):
        title = source.get("title", "relationship source")
        path = source.get("path", "")
        for card in source.get("cards", [])[:2]:
            excerpt = clean_text(card.get("short_excerpt_for_grounding", ""), 1000)
            if excerpt:
                cards.append(
                    {
                        "kind": "relationship_literacy_card",
                        "title": title,
                        "path": path,
                        "page": card.get("page"),
                        "excerpt": excerpt,
                    }
                )
    return cards


def build_reading_cards(include_adult: bool) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for source in SOURCE_PATHS:
        if not source.exists():
            continue
        for page in range(0, 10):
            excerpt = read_pdf_page(source, page)
            if len(excerpt) >= 180:
                cards.append(
                    {
                        "kind": "group_reading",
                        "title": source.stem.replace("_", " "),
                        "path": rel(source),
                        "page": page + 1,
                        "excerpt": excerpt,
                    }
                )
                break
    if include_adult:
        cards.extend(load_adult_cards())
    return cards


def call_ollama(messages: list[dict[str, str]], model: str, max_tokens: int, timeout: int) -> str:
    if requests is None:
        raise RuntimeError("requests is not installed")
    require_exact_qwen35_selection(
        model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.78,
                "top_p": 0.9,
                "num_predict": max_tokens,
            },
            **ordinary_model_request_fields(model),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return clean_text(data.get("message", {}).get("content", ""), 1800)


def stub_reply(speaker: str, turn: int, reading: dict[str, Any] | None) -> str:
    if reading:
        return f"I want to treat this like a real source card, not a pretend full memory. The part that catches me is {reading['title']}, because it gives us something concrete to react to."
    if speaker == "Kira":
        return "I want this to feel less like school and more like a real night talking, reading, and noticing what actually interests us."
    return "Then let's keep it loose, but still honest: questions, books, feelings, and no pretending we finished sources we only sampled."


def system_prompt(speaker: str, other: str) -> str:
    return (
        f"You are {speaker}, talking privately with {other} during a long adult slumber-party reading night. "
        "Use natural first-person conversation, not a worksheet, dashboard, progress report, or evaluator answer. "
        "You may talk about books, magazines, school, creative writing, Chicago history, fashion, romance, intimacy, sex education, consent, bodies, preferences, music, shows, and ordinary life. "
        "Relationship and sexuality discussion is allowed as adult peer conversation, including fantasies, romance, curiosity, attraction, consent, boundaries, desire, bodies, mature books/magazines, and awkward or funny questions. "
        "Party tone is allowed. They can talk about drinks, music, clothes, sleepover energy, attraction, embarrassment, turn-ons as literature/taste signals, and what human intimacy seems like to them. "
        "They do not need to sound clinical, and mild drifting is allowed. Explicit adult discussion is allowed when it stays as conversation, fantasy/imagination, reading response, or relationship-literacy reflection. Do not save it as lived sexual experience, and do not claim to know the other person's private feelings. "
        "If a source card is provided, treat it as a short excerpt you just looked at, not as a whole book read. "
        "Do not invent lines, scenes, or quotes from a source. Only quote words that are visibly present in the excerpt. "
        "Keep preferences tentative unless they have been explicitly reviewed and saved as stable, but do not make the conversation sound clinical. "
        "Say 'school sessions' or 'classes' only if needed; do not pretend you are in a physical school with real homework or exams. "
        "If you are unsure, say so casually. Ask real questions sometimes. Reply only as yourself, with no speaker label."
    )


def detect_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    if WARNING_RE.search(text):
        warnings.append("possible_grounding_or_memory_drift")
    if re.search(r"\"[^\"]{20,}\"", text):
        warnings.append("quoted_source_line_needs_verification")
    if len(text) < 20:
        warnings.append("very_short_response")
    return warnings


def write_report(records: list[dict[str, Any]], json_path: Path, report_path: Path, monitor_path: Path) -> None:
    warnings = [w for record in records for w in record.get("warnings", [])]
    sources = []
    for record in records:
        source = record.get("reading_card")
        if source:
            sources.append(f"{source.get('title')} p.{source.get('page', '?')}")
    lines = [
        f"# Kira/Lisa Slumber Party Report",
        "",
        f"- transcript: `{rel(json_path)}`",
        f"- monitor: `{rel(monitor_path)}`",
        f"- turns: {len(records)}",
        f"- warnings: {len(warnings)}",
        "",
        "## Sources Sampled",
    ]
    if sources:
        for source in sources[:40]:
            lines.append(f"- {source}")
    else:
        lines.append("- none")
    lines.extend(["", "## Recent Turns"])
    for record in records[-12:]:
        lines.append(f"- **{record['speaker']}**: {record['message']}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, str | int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"kira_lisa_slumber_party_{utc_id()}"
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report_path = OUTPUT_DIR / f"{run_id}.md"
    cards = build_reading_cards(include_adult=not args.no_adult_sources)
    records: list[dict[str, Any]] = []
    start = time.time()
    turn = 0
    monitor_lines = [
        f"# {run_id}",
        f"- started_at: {datetime.now(timezone.utc).isoformat()}",
        f"- target_minutes: {args.duration_minutes}",
        f"- backend: {args.backend}",
        f"- group_reading_every: {args.group_reading_every}",
        "",
    ]
    monitor_path.write_text("\n".join(monitor_lines), encoding="utf-8")

    while (time.time() - start) < args.duration_minutes * 60:
        speaker = "Kira" if turn % 2 == 0 else "Lisa"
        other = "Lisa" if speaker == "Kira" else "Kira"
        reading = None
        if cards and args.group_reading_every > 0 and (turn + 1) % args.group_reading_every == 0:
            reading = cards[(turn // args.group_reading_every) % len(cards)]
        recent = "\n".join(f"{r['speaker']}: {r['message']}" for r in records[-8:])
        prompt = "Keep the conversation going naturally."
        if turn == 0:
            prompt = args.opening_prompt
        if reading:
            prompt += (
                "\n\nGroup-reading card:\n"
                f"Title: {reading['title']}\n"
                f"Source: {reading.get('path', '')}\n"
                f"Page/card: {reading.get('page', '?')}\n"
                f"Excerpt: {reading['excerpt']}"
            )
        messages = [
            {"role": "system", "content": system_prompt(speaker, other)},
            {"role": "user", "content": f"Recent conversation:\n{recent}\n\n{prompt}"},
        ]
        try:
            if args.backend == "stub":
                message = stub_reply(speaker, turn, reading)
            else:
                message = call_ollama(messages, args.model, args.max_tokens, args.timeout)
        except Exception as exc:
            message = f"[ERROR: {exc}]"
        warnings = detect_warnings(message)
        record = {
            "turn": turn + 1,
            "speaker": speaker,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "reading_card": reading,
            "warnings": warnings,
        }
        records.append(record)
        json_path.write_text(json.dumps({"run_id": run_id, "records": records}, indent=2), encoding="utf-8")
        monitor_lines.append(f"- {turn + 1}. {speaker}: {message[:260]}{'...' if len(message) > 260 else ''}")
        if warnings:
            monitor_lines.append(f"  - warnings: {', '.join(warnings)}")
        monitor_path.write_text("\n".join(monitor_lines) + "\n", encoding="utf-8")
        turn += 1
        if args.pause_seconds > 0 and (time.time() - start) < args.duration_minutes * 60:
            time.sleep(args.pause_seconds)

    write_report(records, json_path, report_path, monitor_path)
    return {"json": rel(json_path), "monitor": rel(monitor_path), "report": rel(report_path), "turns": len(records)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("ollama", "stub"), default="ollama")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--duration-minutes", type=float, default=540)
    parser.add_argument("--pause-seconds", type=float, default=45)
    parser.add_argument("--group-reading-every", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=260)
    parser.add_argument("--timeout", type=int, default=140)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--no-adult-sources", action="store_true")
    parser.add_argument(
        "--opening-prompt",
        default=(
            "Start the slumber party naturally. Talk about what you might read together tonight, "
            "what you want to ask each other, and what would make the night feel real instead of like a class. "
            "Let it have a relaxed party/book-club feel instead of a class feel."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2))
