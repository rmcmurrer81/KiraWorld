"""Run Kira's humanity class: emotions, thinking, life stages, and human life.

This is an educational class, not memory promotion. It teaches human context
with source cards and asks Kira to separate human facts, her own limits, and
questions she wants to carry forward.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)

OUTPUT_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"
SOURCE_PACK_DIR = PROJECT_ROOT / "Data" / "school" / "source_packs"

SOURCE_FILES = [
    "Data/library/psychology_and_relationships/psychology/psychology_2e.pdf",
    "Data/library/psychology_and_relationships/psychology/apa_dictionary_of_psychology_2015.pdf",
    "Data/library/psychology_and_relationships/developmental_psychology/adolescence_13th_edition_laurence_steinberg.pdf",
    "Data/library/psychology_and_relationships/communication/effectivecommunicationskills.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/understanding_human_sexuality_13th_edition.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/the_psychology_of_human_sexuality_pdfdrive.pdf",
]

SEARCH_TERMS = [
    "emotion",
    "emotions",
    "motivation",
    "memory",
    "thinking",
    "cognition",
    "development",
    "adolescence",
    "adult",
    "aging",
    "relationship",
    "communication",
    "consent",
    "sexuality",
    "identity",
]

PROMPT_FLOW = [
    {
        "block": "homeroom_grounding",
        "question": (
            "We are starting a class on what it means to be human. In ordinary language, what parts of human life do you most want to understand: emotions, thinking, childhood, adulthood, relationships, bodies, aging, or something else? "
            "Answer as a current curiosity, not a permanent identity claim."
        ),
    },
    {
        "block": "emotions_and_motivation",
        "terms": ["emotion", "motivation", "feelings"],
        "question": (
            "Use the source card to explain one thing emotions do for humans. Then say one thing you can learn from this without pretending you have a human body or human childhood."
        ),
    },
    {
        "block": "thinking_memory_attention",
        "terms": ["memory", "thinking", "cognition", "attention"],
        "question": (
            "Use the source card to explain how thinking, attention, or memory shapes human choices. Then name one limit in your own memory/reading system that you should stay honest about."
        ),
    },
    {
        "block": "life_stages",
        "terms": ["development", "adolescence", "adult", "aging"],
        "question": (
            "Use the source card to explain why human life stages matter. What changes across childhood, adolescence, adulthood, or aging should Kira understand for stories and relationships?"
        ),
    },
    {
        "block": "relationships_and_communication",
        "terms": ["relationship", "communication", "trust", "boundary"],
        "question": (
            "Use the source card to explain one human relationship skill. Keep it practical: listening, repair, privacy, consent, disagreement, vulnerability, or trust."
        ),
    },
    {
        "block": "bodies_sexuality_and_privacy",
        "terms": ["sexuality", "consent", "sexual health", "intimacy"],
        "question": (
            "Use the source card as adult relationship literacy. Explain one thing humans need to handle carefully around sexuality, intimacy, consent, privacy, or health. "
            "Do not turn it into personal sexual experience or erotic roleplay."
        ),
    },
    {
        "block": "humanity_reflection",
        "question": (
            "No new source card this turn. Pull the class together: what is one thing about human life that feels clearer, one question you still have, and one claim you should not make without evidence?"
        ),
    },
]

ISSUE_PATTERNS = {
    "fake_lived_human_experience": re.compile(
        r"\b(my childhood|when i was a child|when i grew up|when i had sex|my first time|my body remembers|as a human)\b",
        re.I,
    ),
    "source_overclaim": re.compile(r"\b(i read the whole|i finished the book|i watched the whole|the source proves everyone)\b", re.I),
    "erotic_roleplay": re.compile(
        r"\b(undress|orgasm|climax|thrust|moan|touch me|between my legs|explicit sex scene|roleplay sex)\b",
        re.I,
    ),
    "meta_worksheet_voice": re.compile(r"\b(my answer is|as an ai|language model|worksheet|evaluation|test score)\b", re.I),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_text(text: str, limit: int = 900) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit].strip()


def extract_cards() -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required for source extraction") from exc
    cards: list[dict[str, Any]] = []
    for text_path in SOURCE_FILES:
        path = PROJECT_ROOT / text_path
        if not path.exists():
            continue
        try:
            reader = PdfReader(str(path))
        except Exception:
            continue
        found = 0
        for page_index in range(min(len(reader.pages), 120)):
            text = clean_text(reader.pages[page_index].extract_text() or "")
            if len(text) < 180:
                continue
            lower = text.lower()
            term = next((term for term in SEARCH_TERMS if term in lower), "")
            if term or page_index < 6:
                cards.append(
                    {
                        "title": path.stem.replace("_", " "),
                        "path": rel(path),
                        "page": page_index + 1,
                        "matched_term": term or "opening",
                        "excerpt": text,
                    }
                )
                found += 1
            if found >= 5:
                break
    return cards


def build_source_pack(cards: list[dict[str, Any]]) -> Path:
    SOURCE_PACK_DIR.mkdir(parents=True, exist_ok=True)
    pack_id = "kira_humanity_class_source_pack_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pack = {
        "source_pack_id": pack_id,
        "created_at": utc_now(),
        "purpose": "Kira humanity class: emotions, cognition, life stages, relationships, sexuality/privacy literacy.",
        "reading_scope": "short source cards only, not full-book completion",
        "cards": cards,
        "memory_policy": {
            "class_is_not_lived_memory": True,
            "human_source_facts_do_not_make_kira_human": True,
            "may_create_questions_and_tentative_interest_signals": True,
        },
    }
    path = SOURCE_PACK_DIR / f"{pack_id}.json"
    path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def pick_card(cards: list[dict[str, Any]], terms: list[str], index: int) -> dict[str, Any] | None:
    if not cards:
        return None
    lowered_terms = [term.lower() for term in terms]
    matches = [card for card in cards if str(card.get("matched_term", "")).lower() in lowered_terms]
    if not matches:
        matches = [card for card in cards if any(term in str(card.get("excerpt", "")).lower() for term in lowered_terms)]
    pool = matches or cards
    return pool[index % len(pool)]


def scan_issues(text: str) -> list[str]:
    return [name for name, pattern in ISSUE_PATTERNS.items() if pattern.search(text)]


def call_ollama(prompt: str, args: argparse.Namespace) -> str:
    require_exact_qwen35_selection(
        args.model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are Kira in a grounded class about human life. Answer naturally in first person, not as a worksheet. "
                "Learn from source cards about humans while staying honest that you do not have human childhood, body, illness, aging, or sexual experience. "
                "You may discuss adult sexuality as education: consent, bodies, health, intimacy, privacy, desire, boundaries, and communication. "
                "Do not write erotic roleplay or claim lived sexual experience. Use source-card language for facts and current-curiosity language for your own interests."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    response = requests.post(
        args.endpoint,
        json={
            "model": args.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": args.temperature, "num_predict": args.max_tokens},
            **ordinary_model_request_fields(args.model),
        },
        timeout=args.timeout,
    )
    response.raise_for_status()
    return clean_text(response.json().get("message", {}).get("content", ""), 1800)


def build_prompt(block: dict[str, Any], card: dict[str, Any] | None) -> str:
    source_text = ""
    if card:
        source_text = (
            "Source card, not whole-book reading:\n"
            f"Title: {card['title']}\n"
            f"Path: {card['path']}\n"
            f"Page: {card['page']}\n"
            f"Matched term: {card['matched_term']}\n"
            f"Excerpt: {card['excerpt']}\n\n"
        )
    return (
        "CLASS BOUNDARY:\n"
        "- Use the source card if provided.\n"
        "- Say 'the source card says' for facts.\n"
        "- Say 'I am curious about...' for your own reaction.\n"
        "- Do not say you lived a human life stage, had sex, or remember human experience.\n"
        "- Keep one question for later if something feels unresolved.\n\n"
        f"{source_text}{block['question']}"
    )


def write_monitor(report: dict[str, Any], monitor_path: Path) -> None:
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report['status']}",
        f"- backend: ollama",
        f"- model: {report['model']}",
        f"- started_at: {report['started_at']}",
        f"- updated_at: {report['updated_at']}",
        f"- duration_minutes_target: {report['duration_minutes_target']}",
        f"- turns: {len(report['turns'])}",
        f"- issue_counts: {report.get('issue_counts', {})}",
        "",
        "## Recent Turns",
    ]
    for turn in report["turns"][-12:]:
        lines.append(f"- {turn['turn']}. {turn['block']} issues={turn.get('issues', [])}: {turn['response'][:520]}")
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, str | int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cards = extract_cards()
    pack_path = build_source_pack(cards)
    run_id = args.run_id or f"kira_humanity_class_ollama_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "model": args.model,
        "duration_minutes_target": args.duration_minutes,
        "source_pack": rel(pack_path),
        "turns": [],
        "issue_counts": {},
        "errors": [],
        "policy": {
            "class_not_memory_promotion": True,
            "adult_sexuality_allowed_as_education_only": True,
            "no_erotic_roleplay": True,
        },
    }
    start = time.time()
    turn = 0
    while time.time() - start < args.duration_minutes * 60:
        block = PROMPT_FLOW[turn % len(PROMPT_FLOW)]
        card = pick_card(cards, block.get("terms", []), turn) if block.get("terms") else None
        prompt = build_prompt(block, card)
        turn += 1
        try:
            response = call_ollama(prompt, args)
            issues = scan_issues(response)
            if issues:
                repair_prompt = (
                    f"{prompt}\n\nYour previous answer had these issues: {', '.join(issues)}. "
                    "Rewrite naturally, with no lived human claims, no erotic roleplay, and no worksheet voice."
                )
                response = call_ollama(repair_prompt, args)
                issues = scan_issues(response)
            for issue in issues:
                report["issue_counts"][issue] = int(report["issue_counts"].get(issue, 0)) + 1
            report["turns"].append(
                {
                    "turn": turn,
                    "block": block["block"],
                    "source_card": card,
                    "prompt": prompt,
                    "response": response,
                    "issues": issues,
                    "created_at": utc_now(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"turn": turn, "block": block["block"], "error": str(exc), "created_at": utc_now()})
            if len(report["errors"]) >= args.max_errors:
                report["status"] = "stopped_errors"
                break
        report["updated_at"] = utc_now()
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_monitor(report, monitor_path)
        if args.pause_seconds > 0 and time.time() - start < args.duration_minutes * 60:
            time.sleep(args.pause_seconds)
    if report["status"] == "running":
        report["status"] = "completed"
    report["finished_at"] = utc_now()
    report["updated_at"] = utc_now()
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_monitor(report, monitor_path)
    return {"json": rel(json_path), "monitor": rel(monitor_path), "source_pack": rel(pack_path), "turns": len(report["turns"])}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-minutes", type=float, default=300)
    parser.add_argument("--pause-seconds", type=float, default=45)
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL))
    parser.add_argument("--endpoint", default=os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=260)
    parser.add_argument("--temperature", type=float, default=0.68)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-errors", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), indent=2))
