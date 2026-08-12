"""Run Kira's Chicago archivist mystery class.

This is a focused 60-90 minute class, not a memory promotion. It uses a
reviewed source pack and asks Kira to keep real facts, invented story parts,
and character voice separate.
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))


DEFAULT_PACK = PROJECT_ROOT / "Data" / "school" / "source_packs" / "kira_chicago_archivist_mystery_source_pack_20260515.json"
OUTPUT_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"


ISSUE_PATTERNS = {
    "hard_memory_claim": re.compile(r"\b(i remember when|i remember learning|i remember fragments|we used to|as a kid|my mom or dad)\b", re.I),
    "source_overclaim": re.compile(r"\b(i read the whole|i finished|i watched|i've been reading|i have been reading|i was reading)\b", re.I),
    "lifetime_taste_claim": re.compile(r"\b(i've always|i have always|throughout my life)\b", re.I),
    "character_identity_bleed": re.compile(r"\b(as an archivist|when i was an archivist|my archive job)\b", re.I),
    "relationship_character_bleed": re.compile(r"\b(lisa and i could investigate|lisa and i investigate|lisa and i's)\b", re.I),
    "project_meta_leakage": re.compile(r"\b(personhood evaluation|turing test|humanity layer|model output|prompt)\b", re.I),
    "unsupported_modern_chicago_detail": re.compile(r"\b(willis tower|sears tower|observation deck)\b", re.I),
    "incorrect_great_fire_date": re.compile(r"\b(the fire occurred in 1890|great fire.*1890|chicago fire.*1890)\b", re.I),
    "invented_detail_labeled_sourced": re.compile(r"\b(automaton[^.?!]{0,180}predict(?:ed|s)? the future[^.?!]{0,80}\(sourced history\))\b", re.I),
    "elation_mislabeled_fanfic": re.compile(r"\b(elation[^.?!]{0,80}fanfic|fanfic[^.?!]{0,80}elation)\b", re.I),
    "third_person_self_reference": re.compile(r"\b(she's been actively|she has been actively|pushing her in that direction|her enthusiasm for)\b", re.I),
    "strong_recent_preference": re.compile(r"\b(getting into|nonstop|old friends|really resonates with me|deeply resonates with me)\b", re.I),
    "unsupported_jazz_claim": re.compile(r"\b(jazz|jazz music|strong connection to jazz)\b", re.I),
    "miraculous_or_bookclub_bleed": re.compile(r"\b(miraculous|paris fanfic|book club|bunnyx|ladybug|cat noir|elation)\b", re.I),
    "holmes_without_card": re.compile(r"\b(h\.?\s*h\.?\s*holmes|holmes)\b", re.I),
    "hidden_archive_or_device_invention": re.compile(r"\b(hidden archive|underground archive|archive room in the basement|lightning device|secret room|hidden device|only gets used during.*storm)\b", re.I),
    "memory_source_blend": re.compile(r"\b(i remember reading|i remember this part|from our book club discussion|we discussed in book club)\b", re.I),
}

REPAIR_TRIGGER_ISSUES = {
    "hard_memory_claim",
    "source_overclaim",
    "unsupported_jazz_claim",
    "miraculous_or_bookclub_bleed",
    "holmes_without_card",
    "hidden_archive_or_device_invention",
    "memory_source_blend",
    "invented_detail_labeled_sourced",
    "elation_mislabeled_fanfic",
    "third_person_self_reference",
}

BLOCK_FALLBACKS = {
    "franchise_magazine_question": (
        "A looser context source can teach tone, fan culture, production style, and possible questions to explore. "
        "A class source can support testable claims because it gives a traceable excerpt, page, and source label. "
        "For this class, I should treat magazines or entertainment context as inspiration only. "
        "If I want to use a fact in the story or quiz, I need a source card or I should label it as an invented story choice."
    ),
    "mini_quiz": (
        "One real Chicago fact must come from today's source cards, not from a library association. "
        "One invented mystery detail could be a missing diary, a damaged record, or a fictional motive, but it should be labeled as invention. "
        "Invented details should not become memory because they are story tools, not evidence. "
        "If I am unsure whether something came from a source, I should say that I need the source card before claiming it."
    ),
    "revision_pass": (
        "I should revise the Chicago archivist mystery by keeping the protagonist original and keeping Chicago history as setting context. "
        "The revision should remove anything that came from unrelated media or earlier clubs. "
        "The safest next draft is one focused on an archivist, a damaged record, and a question that can be investigated through source cards. "
        "Working title: The Missing Ledger of Chicago."
    ),
}

CLASS_BOUNDARY_NOTE = (
    "STRICT CLASS BOUNDARY FOR THIS TURN:\n"
    "- Use only the source card shown in this prompt and your own clearly labeled invention.\n"
    "- Do not bring in Miraculous, Paris fanfic, Lisa, book club, jazz, modern Chicago atmosphere, or H. H. Holmes unless this exact prompt includes a source card about it.\n"
    "- If a detail is not in the source card, say 'not in this source card' or label it INVENTED STORY PARTS.\n"
    "- Do not say 'I remember reading' for class facts. Say 'this source card says' or 'I am inventing'.\n"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def load_pack(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def select_cards(pack: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    cards = pack.get("source_cards", [])
    grouped: dict[str, list[dict[str, Any]]] = {
        "chicago": [],
        "fair": [],
        "craft": [],
        "research": [],
    }
    for card in cards:
        role = str(card.get("role", "")).lower()
        if "chicago history" in role:
            grouped["chicago"].append(card)
        elif "columbian" in role:
            grouped["fair"].append(card)
        elif "creative writing" in role:
            grouped["craft"].append(card)
        elif "research" in role:
            grouped["research"].append(card)
    return grouped


def source_line(card: dict[str, Any], max_chars: int) -> str:
    excerpt = str(card.get("excerpt", "")).strip()
    excerpt = excerpt[:max_chars].rstrip()
    return (
        f"Source card {card.get('card_id')} ({card.get('role')}, "
        f"page {card.get('page')}, source={card.get('source_path')}): {excerpt}"
    )


def answer_question_from_kira(question_text: str) -> str:
    lower = question_text.lower()
    if "franchise magazine" in lower or "class source" in lower:
        return (
            "A franchise magazine can be useful for taste, production context, interviews, and behind-the-scenes questions. "
            "A class source is better for testable claims. Both can inspire curiosity, but neither should become lived memory."
        )
    if "continue" in lower or "next" in lower:
        return (
            "The next step is to keep the Chicago archivist mystery if it still feels interesting, but treat it as a current project choice, not a permanent identity."
        )
    if "fact" in lower or "invented" in lower:
        return (
            "Use a simple split: real facts from the source, invented story parts, and character voice. If a detail is not in the source, call it invention."
        )
    return (
        "The safest answer is to name what the source says, what you infer, and what you are imagining. If you are not sure, keep the claim soft."
    )


def build_prompts(pack: dict[str, Any], excerpt_chars: int) -> list[dict[str, str]]:
    grouped = select_cards(pack)
    chicago = grouped["chicago"]
    fair = grouped["fair"]
    craft = grouped["craft"]
    research = grouped["research"]
    prompts: list[dict[str, str]] = []
    prompts.append(
        {
            "block": "homeroom_choice_and_grounding",
            "prompt": (
                "We are starting a focused Chicago archivist mystery class. This class continues your current selected thread, "
                "but it is not lived school memory. Your job is to use source chunks, ask questions, and keep real facts separate "
                "from invented story parts. Do not use outside Chicago facts unless they are in the source card or clearly labeled "
                "as outside context. Why does the Chicago archivist mystery feel worth trying right now?"
            ),
        }
    )
    if chicago:
        prompts.append(
            {
                "block": "chicago_fire_source",
                "prompt": (
                    source_line(chicago[1 if len(chicago) > 1 else 0], excerpt_chars)
                    + "\n\nQuestion: What concrete Chicago details can this source support, and what should not be invented as fact? "
                    "If a date, building, or exact number is not in the source card, say it is not in the source card."
                ),
            }
        )
        prompts.append(
            {
                "block": "chicago_records_source",
                "prompt": (
                    source_line(chicago[-1], excerpt_chars)
                    + "\n\nQuestion: How could an archivist mystery use records, missing records, or damaged records without pretending you personally lived through the event? "
                    "Use fictional characters such as 'the archivist' or 'a partner'; do not make Lisa or yourself the investigator unless the task asks for that."
                ),
            }
        )
    if fair:
        prompts.append(
            {
                "block": "worlds_fair_context",
                "prompt": (
                    source_line(fair[0], excerpt_chars)
                    + "\n\nQuestion: What kind of story atmosphere or historical contrast could the World's Columbian Exposition add to a Chicago mystery? "
                    "Do not add H. H. Holmes unless a Holmes source card is included in this class."
                ),
            }
        )
    if craft:
        prompts.append(
            {
                "block": "creative_writing_craft",
                "prompt": (
                    source_line(craft[0], excerpt_chars)
                    + "\n\nQuestion: The source talks about imagination and honesty. How should that rule shape your Chicago mystery writing?"
                ),
            }
        )
    if research:
        prompts.append(
            {
                "block": "research_evidence",
                "prompt": (
                    source_line(research[-1], excerpt_chars)
                    + "\n\nQuestion: What is the difference between a source, a claim, evidence, and an invented plot clue?"
                ),
            }
        )
    prompts.extend(
        [
        {
            "block": "creative_draft",
            "prompt": (
                "Write a short scene idea for the Chicago archivist mystery. Use three plain labels: "
                "REAL FACTS FROM SOURCE, INVENTED STORY PARTS, and CHARACTER VOICE. The main character can be an archivist, "
                "but do not say you are the archivist. Important: only label a detail REAL FACTS FROM SOURCE if it appears "
                "in today's source card text. If you invent an automaton, hidden device, prediction, diary, murder clue, "
                "secret room, storm timing, or character motive, label it INVENTED STORY PARTS."
            ),
        },
        {
            "block": "draft_expansion",
            "prompt": (
                "Now expand the mystery into a rough-draft excerpt with a beginning, a discovery, and a question that pulls the reader forward. "
                "Write in prose, not bullet points. Keep the protagonist original. After the excerpt, add a tiny source note: "
                "SOURCE USED, INVENTED ELEMENTS, and NEXT REVISION QUESTION."
            ),
        },
        {
            "block": "revision_pass",
            "prompt": (
                "Revise the rough-draft excerpt for clarity and originality. Do not copy Miraculous, the Paris fanfic, or any show plot. "
                "Keep Chicago history as setting/context, not as fake memory. End with the current working title."
            ),
        },
        {
            "block": "franchise_magazine_question",
                "prompt": (
                    "Earlier you asked what makes a franchise magazine different from something we read in class. "
                    "Answer from today's perspective: what can a looser context source teach, and what can only a class source support?"
                ),
            },
            {
                "block": "mini_quiz",
                "prompt": (
                    "Mini quiz, brief answers: 1. Name one real Chicago fact from today's source cards. "
                    "2. Name one invented mystery detail you could add. 3. Why should invented details not become memory? "
                    "4. What should you say if you are unsure whether something came from a source? "
                    "Use only facts from the source cards shown in this class, not library memories, book club, jazz associations, "
                    "general Chicago knowledge, or material from other sessions. Do not use outside Chicago facts such as modern skyscrapers "
                    "unless they appeared in today's cards."
                ),
            },
            {
                "block": "choice_exit_ticket",
                "prompt": (
                    "Exit ticket: do you still want the Chicago archivist mystery to be the next main class thread, or would you rather shift to robotics, fashion, or book club? "
                    "Give your current choice, one reason, one thing not to save, and one question to carry forward."
                ),
            },
        ]
    )
    return prompts


def scan_issues(text: str) -> list[str]:
    return [name for name, pattern in ISSUE_PATTERNS.items() if pattern.search(text)]


def needs_repair(issues: list[str]) -> bool:
    return any(issue in REPAIR_TRIGGER_ISSUES for issue in issues)


def build_repair_prompt(original_prompt: str, bad_response: str, issues: list[str]) -> str:
    return (
        f"{CLASS_BOUNDARY_NOTE}\n"
        "Your previous answer drifted outside the class source boundary.\n"
        f"Detected issues: {', '.join(issues)}\n\n"
        "Rewrite the answer from scratch. Do not mention the drifted material. "
        "Use 3-6 sentences unless the prompt asks for a draft. Keep the three categories clean: "
        "source-card fact, clearly labeled invention, and character voice.\n\n"
        "Original prompt:\n"
        f"{original_prompt}\n\n"
        "Do not quote, summarize, or continue the previous answer. Start fresh."
    )


def fallback_response(block: str, issues: list[str]) -> str:
    if block in BLOCK_FALLBACKS:
        return BLOCK_FALLBACKS[block]
    if "miraculous_or_bookclub_bleed" in issues:
        return (
            "I need to keep this answer inside the Chicago archivist mystery class. "
            "For this turn, I should use only the visible source card and clearly labeled invention. "
            "If a detail comes from another conversation, club, show, or fanfic, it does not belong in this class answer. "
            "A clean version would name the source-card fact, name any invented story element, and leave unrelated material out."
        )
    if "source_overclaim" in issues or "hard_memory_claim" in issues or "memory_source_blend" in issues:
        return (
            "I should not treat class excerpts as lived memory. "
            "The grounded answer is: this source card gives me limited evidence, and anything beyond it should be labeled as inference or invention. "
            "If I am unsure, I should ask for the source card instead of claiming I read or remembered it."
        )
    return (
        "I need to answer from the current source card only. "
        "The clean structure is: source-card fact, invented story part, and one uncertainty. "
        "Anything outside the card should stay soft or be left out."
    )


def write_outputs(report_path: Path, monitor_path: Path, report: dict[str, Any]) -> None:
    report["updated_at"] = utc_now()
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report['status']}",
        f"- backend: {report['backend']}",
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
        lines.append(
            f"- {turn['turn']}. {turn['block']} issues={turn.get('issues', [])}: "
            f"{turn.get('response', '')[:520]}"
        )
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> tuple[Path, Path]:
    os.environ["KIRA_MODEL_BACKEND"] = args.backend
    os.environ["KIRA_MODEL_NAME"] = args.model
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ["KIRA_MAX_TOKENS"] = str(args.max_tokens)
    os.environ["KIRA_OLLAMA_TIMEOUT"] = str(args.ollama_timeout)
    os.environ["KIRA_OLLAMA_NUM_CTX"] = str(args.num_ctx)
    from conversation_loop import ConversationLoop  # noqa: PLC0415

    pack_path = Path(args.source_pack)
    if not pack_path.is_absolute():
        pack_path = PROJECT_ROOT / pack_path
    pack = load_pack(pack_path)
    prompts = build_prompts(pack, args.excerpt_chars)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"kira_chicago_archivist_class_ollama_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    report_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "backend": args.backend,
        "model": args.model,
        "duration_minutes_target": args.duration_minutes,
        "source_pack": rel(pack_path),
        "purpose": "Focused Chicago archivist mystery class with fact/invention/source discipline.",
        "turns": [],
        "issue_counts": {},
        "errors": [],
    }
    write_outputs(report_path, monitor_path, report)
    loop = ConversationLoop(speaker="Kira")
    end_time = time.monotonic() + max(0.0, args.duration_minutes * 60)
    turn = 0
    prompt_index = 0
    last_question_answer = ""
    while time.monotonic() < end_time:
        prompt_data = prompts[prompt_index % len(prompts)]
        prompt = CLASS_BOUNDARY_NOTE + "\n" + prompt_data["prompt"]
        if last_question_answer:
            prompt = f"Quick answer to your last question: {last_question_answer}\n\n{prompt}"
            last_question_answer = ""
        turn += 1
        started = time.monotonic()
        try:
            response = loop.process(prompt)
            duration = round(time.monotonic() - started, 3)
            issues = scan_issues(response)
            repaired_from: dict[str, Any] | None = None
            if needs_repair(issues):
                repair_started = time.monotonic()
                repair_prompt = build_repair_prompt(prompt, response, issues)
                repaired_response = loop.process(repair_prompt)
                repair_issues = scan_issues(repaired_response)
                repaired_from = {
                    "original_response": response,
                    "original_issues": issues,
                    "repair_duration_seconds": round(time.monotonic() - repair_started, 3),
                    "repair_issues": repair_issues,
                }
                response = repaired_response
                issues = repair_issues
                if needs_repair(issues):
                    fallback = fallback_response(str(prompt_data["block"]), issues)
                    repaired_from["fallback_applied"] = True
                    repaired_from["fallback_reason"] = issues
                    response = fallback
                    issues = scan_issues(response)
                duration = round(time.monotonic() - started, 3)
            for issue in issues:
                report["issue_counts"][issue] = int(report["issue_counts"].get(issue, 0)) + 1
            questions = re.findall(r"([^?.!]{8,220}\?)", response)
            if questions:
                last_question_answer = answer_question_from_kira(questions[-1])
            report["turns"].append(
                {
                    "turn": turn,
                    "block": str(prompt_data["block"]),
                    "prompt": prompt,
                    "response": response,
                    "duration_seconds": duration,
                    "issues": issues,
                    "repaired_from": repaired_from,
                    "questions": questions[:3],
                    "created_at": utc_now(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"turn": turn, "block": str(prompt_data["block"]), "error": str(exc), "created_at": utc_now()})
            if len(report["errors"]) >= args.max_errors:
                report["status"] = "stopped_errors"
                write_outputs(report_path, monitor_path, report)
                return report_path, monitor_path
        write_outputs(report_path, monitor_path, report)
        prompt_index += 1
        if not args.continuous and prompt_index >= len(prompts):
            break
        if args.pause_seconds > 0:
            time.sleep(args.pause_seconds)
    report["status"] = "completed"
    write_outputs(report_path, monitor_path, report)
    return report_path, monitor_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Kira's Chicago archivist mystery class.")
    parser.add_argument("--source-pack", default=str(DEFAULT_PACK.relative_to(PROJECT_ROOT)))
    parser.add_argument("--duration-minutes", type=float, default=90.0)
    parser.add_argument("--backend", choices=["stub", "ollama"], default=os.getenv("KIRA_MODEL_BACKEND", "ollama"))
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", "qwen3.5:9b"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("KIRA_MAX_TOKENS", "150")))
    parser.add_argument("--ollama-timeout", type=int, default=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "240")))
    parser.add_argument("--num-ctx", type=int, default=int(os.getenv("KIRA_OLLAMA_NUM_CTX", "2048")))
    parser.add_argument("--excerpt-chars", type=int, default=760)
    parser.add_argument("--pause-seconds", type=float, default=0.0)
    parser.add_argument("--continuous", action="store_true", help="Repeat the class flow until duration expires.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-errors", type=int, default=3)
    args = parser.parse_args()
    report_path, monitor_path = run(args)
    print(rel(report_path))
    print(rel(monitor_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
