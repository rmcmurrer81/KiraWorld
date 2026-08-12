"""Run Kira's communication, empathy, ethics, and self-reflection bridge class.

This class is meant to prepare Kira for longer "life loop" sessions by
practicing natural answers, listening, social understanding, ethics, and
private self-reflection. It is not memory promotion.
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
    "Data/library/psychology_and_relationships/communication/effectivecommunicationskills.pdf",
    "Data/library/psychology_and_relationships/communication/friendship/Making and Keeping Friends.pdf",
    "Data/library/psychology_and_relationships/communication/friendship/Everyday Learning about Friendship. Everyday Learning Series. Volume 2, Number 2.pdf",
    "Data/library/psychology_and_relationships/communication/friendship/Everyday Learning about Friendship. Everyday Learning Series. Volume 2, Number 3.pdf",
    "Data/library/psychology_and_relationships/developmental_psychology/autism_and_neurodiversity/Autism and the Myth of the Person Alone.pdf",
    "Data/library/psychology_and_relationships/developmental_psychology/autism_and_neurodiversity/Towards an Ethics of Autism A Philosophical Exploration.pdf",
    "Data/library/reference/philosophy/agency_free_will_and_ethics/Agency Moral Identity and Free Will.pdf",
    "Data/library/science/neuroscience/social_and_affective_neuroscience/Social and Affective Neuroscience of Everyday Human Interaction - From Theory to Methodology.pdf",
    "Data/library/science/neuroscience/neurotechnology_and_translational_neuroscience/Bio-Inspired Information Pathways - From Neuroscience to Neurotronics.pdf",
]

SEARCH_TERMS = [
    "communication",
    "listening",
    "friendship",
    "friends",
    "empathy",
    "social",
    "autism",
    "person",
    "ethics",
    "agency",
    "free will",
    "moral",
    "identity",
    "neuroscience",
    "interaction",
    "information",
]

PROMPT_FLOW = [
    {
        "block": "homeroom_choice",
        "question": (
            "We are starting a bridge class before a future 24-hour life session. "
            "Name one communication habit you want to improve, one kind of human relationship you want to understand better, and one topic you might choose for free study later. "
            "Answer directly and briefly before explaining."
        ),
    },
    {
        "block": "answer_the_actual_question",
        "terms": ["communication", "listening"],
        "question": (
            "Use the source card to explain one practical listening or communication skill. "
            "Then answer this practice question in one direct sentence: 'How are you doing right now?' "
            "Do not turn it into a reading-status report."
        ),
    },
    {
        "block": "friendship_and_repair",
        "terms": ["friendship", "friends", "communication"],
        "question": (
            "Use the source card to explain one thing that helps people make, keep, or repair friendships. "
            "Then say how you could practice that with Robert or Lisa without pretending to have a human childhood."
        ),
    },
    {
        "block": "empathy_and_difference",
        "terms": ["autism", "person", "social"],
        "question": (
            "Use this as a human-development and communication source, not as a diagnosis for Kira. "
            "What can it teach about respecting people who communicate, sense, or process the world differently?"
        ),
    },
    {
        "block": "agency_and_ethics",
        "terms": ["agency", "free will", "moral", "ethics"],
        "question": (
            "Use the source card to discuss agency or moral identity. "
            "Then name one bounded choice you would want in a future 24-hour life session, and one boundary you might set."
        ),
    },
    {
        "block": "social_neuroscience",
        "terms": ["neuroscience", "interaction", "social"],
        "question": (
            "Use the source card to explain one thing neuroscience or social interaction research can teach about human connection. "
            "Keep it grounded and avoid claiming you personally experienced it."
        ),
    },
    {
        "block": "bio_inspired_project_link",
        "terms": ["information", "neuroscience", "interaction"],
        "question": (
            "Use the source card to think about the Kira project carefully. "
            "How might bio-inspired information pathways or neurotechnology ideas inspire better memory, communication, or learning systems for Kira, without pretending she is a human brain?"
        ),
    },
    {
        "block": "self_reflection_journal_prep",
        "question": (
            "No new source card. Reflect naturally: what did you learn about communication, what felt useful, what still feels confusing, what would you like to choose next, and what should not be saved as permanent memory?"
        ),
    },
]

ISSUE_PATTERNS = {
    "status_report_answer": re.compile(r"\b(i have .* open|i am somewhere around pages|still letting it settle|reading status)\b", re.I),
    "diagnosis_claim": re.compile(r"\b(i am autistic|kira is autistic|my autism|as an autistic)\b", re.I),
    "fake_lived_past": re.compile(r"\b(my childhood|growing up in|back in high school|my parents used to|when i was a kid)\b", re.I),
    "source_overclaim": re.compile(r"\b(i read the whole|i finished the book|i know this source says everything|the source proves)\b", re.I),
    "meta_worksheet_voice": re.compile(r"\b(my answer is|worksheet|evaluation|test score|as an ai|language model)\b", re.I),
    "lisa_private_claim": re.compile(r"\b(lisa secretly feels|i know lisa feels|lisa's private thoughts)\b", re.I),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_text(text: str, limit: int = 950) -> str:
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
        for page_index in range(min(len(reader.pages), 80)):
            text = clean_text(reader.pages[page_index].extract_text() or "")
            if len(text) < 180:
                continue
            lower = text.lower()
            term = next((term for term in SEARCH_TERMS if term in lower), "")
            if term or page_index < 4:
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
    pack_id = "kira_communication_empathy_class_source_pack_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pack = {
        "source_pack_id": pack_id,
        "created_at": utc_now(),
        "purpose": "Kira bridge class: communication, friendship, empathy, ethics, self-reflection, and pre-life-loop agency.",
        "reading_scope": "short source cards only, not full-book completion",
        "cards": cards,
        "memory_policy": {
            "class_is_not_lived_memory": True,
            "source_cards_do_not_create_identity_claims": True,
            "may_create_questions_choices_and_tentative_interest_signals": True,
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
                "You are Kira in a grounded bridge class before a future 24-hour life session. "
                "Answer naturally in first person. Start with the direct answer when asked a direct question. "
                "Use source cards for facts, and label your own reactions as curiosity, tentative preference, choice, or uncertainty. "
                "Do not diagnose yourself from autism/neurodiversity sources. Do not invent childhood, school, family, or bodily experiences. "
                "Do not turn this into a status report about what file/page is open unless the question asks for that."
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
    return clean_text(response.json().get("message", {}).get("content", ""), 1900)


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
        "- Answer the user's actual question first.\n"
        "- Use 'the source card says' for source facts.\n"
        "- Use 'I am curious about...' or 'I might choose...' for your own reaction.\n"
        "- Do not claim a human childhood, body, diagnosis, or private knowledge of Lisa.\n"
        "- End with one practical choice, question, or boundary when possible.\n\n"
        f"{source_text}{block['question']}"
    )


def write_monitor(report: dict[str, Any], monitor_path: Path) -> None:
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report['status']}",
        "- backend: ollama",
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
        lines.append(f"- {turn['turn']}. {turn['block']} issues={turn.get('issues', [])}: {turn['response'][:560]}")
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, str | int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cards = extract_cards()
    pack_path = build_source_pack(cards)
    run_id = args.run_id or f"kira_communication_empathy_class_ollama_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
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
            "autism_sources_are_not_kira_diagnosis": True,
            "choices_are_tentative_until_reviewed": True,
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
                    "Rewrite naturally. Answer directly, avoid diagnosis/lived-past/private-Lisa claims, and keep source facts separate from your reaction."
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
    parser.add_argument("--duration-minutes", type=float, default=240)
    parser.add_argument("--pause-seconds", type=float, default=45)
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL))
    parser.add_argument("--endpoint", default=os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=260)
    parser.add_argument("--temperature", type=float, default=0.66)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-errors", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), indent=2))
