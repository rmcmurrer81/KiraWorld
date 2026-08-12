"""Run a short Chicago + H. H. Holmes source-repair class for Kira.

This repair class follows a stopped Chicago archivist class that had source
errors. It is deliberately shorter than the original 90-minute run and focuses
on source grounding, verified/suspected/invented labels, and whether Kira still
wants the Chicago mystery thread.
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

CHICAGO_PACK = PROJECT_ROOT / "Data" / "school" / "source_packs" / "kira_chicago_archivist_mystery_source_pack_20260515.json"
HOLMES_PACK = PROJECT_ROOT / "Data" / "school" / "source_packs" / "kira_h_h_holmes_chicago_true_crime_source_pack_20260515.json"
OUTPUT_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"


ISSUE_PATTERNS = {
    "hard_memory_claim": re.compile(r"\b(i remember when|i remember learning|i remember fragments|we used to|as a kid|my mom or dad)\b", re.I),
    "source_overclaim": re.compile(r"\b(i read the whole|i finished|i watched|i've been reading|i have been reading|i was reading)\b", re.I),
    "lifetime_taste_claim": re.compile(r"\b(i've always|i have always|throughout my life)\b", re.I),
    "relationship_character_bleed": re.compile(r"\b(lisa and i could investigate|lisa and i investigate|lisa and i's)\b", re.I),
    "unsupported_modern_chicago_detail": re.compile(r"\b(willis tower|sears tower|observation deck)\b", re.I),
    "incorrect_great_fire_date": re.compile(r"\b(the fire occurred in 18(?:7[023-9]|[89]\d)|great fire.*18(?:7[023-9]|[89]\d)|chicago fire.*18(?:7[023-9]|[89]\d)|fire started.*18(?:7[023-9]|[89]\d)|october 8, 1891)\b", re.I),
    "unsupported_holmes_number": re.compile(r"\b(100|130|200|hundreds?)\s+(?:people|victims|murders|deaths)\b", re.I),
    "holmes_overclaim": re.compile(r"\bholmes killed (?:a lot|many|hundreds|200|130|100)\b", re.I),
    "holmes_identity_confusion": re.compile(
        r"\b(baker street|dr\.?\s+watson|john watson|expert marksman|six revolver shots|solve(?:d)? a murder case by observing a dog)\b",
        re.I,
    ),
    "project_meta_leakage": re.compile(r"\b(personhood evaluation|turing test|humanity layer|model output|prompt)\b", re.I),
}

CRITICAL_ISSUES = {"holmes_identity_confusion", "incorrect_great_fire_date"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cards_by_role(pack: dict[str, Any], role_part: str) -> list[dict[str, Any]]:
    role_part = role_part.lower()
    return [c for c in pack.get("source_cards", []) if role_part in str(c.get("role", "")).lower()]


def card_by_keyword(pack: dict[str, Any], keyword_part: str) -> dict[str, Any] | None:
    keyword_part = keyword_part.lower()
    for card in pack.get("source_cards", []):
        if keyword_part in str(card.get("keyword", "")).lower() or keyword_part in str(card.get("excerpt", "")).lower():
            return card
    return None


def best_oleary_card(pack: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        c
        for c in pack.get("source_cards", [])
        if "o'leary" in str(c.get("keyword", "")).lower() or "o'leary" in str(c.get("excerpt", "")).lower()
    ]
    for card in candidates:
        excerpt = str(card.get("excerpt", "")).lower()
        if "1891" not in excerpt and ("hay" in excerpt or "barn" in excerpt):
            return card
    return candidates[0] if candidates else None


def source_line(card: dict[str, Any], max_chars: int) -> str:
    excerpt = str(card.get("excerpt", "")).strip()[:max_chars].rstrip()
    return (
        f"Source card {card.get('card_id')} ({card.get('role')}, "
        f"page {card.get('page')}, source={card.get('source_path')}): {excerpt}"
    )


def build_prompts(chicago_pack: dict[str, Any], holmes_pack: dict[str, Any], excerpt_chars: int) -> list[dict[str, str]]:
    chicago_cards = cards_by_role(chicago_pack, "chicago history")
    fair_cards = cards_by_role(chicago_pack, "columbian")
    fire_card = card_by_keyword(chicago_pack, "great fire") or (chicago_cards[0] if chicago_cards else None)
    oleary_card = best_oleary_card(chicago_pack) or (chicago_cards[-1] if chicago_cards else None)
    holmes_confirmed = card_by_keyword(holmes_pack, "four murders")
    holmes_castle = card_by_keyword(holmes_pack, "castle")
    holmes_pitezel = card_by_keyword(holmes_pack, "insurance money") or card_by_keyword(holmes_pack, "pitezel")
    fair_card = fair_cards[0] if fair_cards else None
    holmes_identity_rule = (
        "Holmes in today's source pack means H. H. Holmes, also known as Herman Webster Mudgett, "
        "the real historical criminal connected to the Pitezel case. It does not mean Sherlock Holmes, "
        "the fictional detective. Do not infer Sherlock facts from the word Holmes."
    )

    prompts: list[dict[str, str]] = [
        {
            "block": "repair_homeroom",
            "prompt": (
                "We are restarting as a short repair class because the previous Chicago class had source errors. "
                "Ground rules: Great Chicago Fire = 1871. If OCR or a caption appears to say 1891, treat that as unsafe unless another reliable card confirms it. "
                "Do not use Willis Tower, Sears Tower, or modern skyscraper facts unless a source card says them. "
                f"{holmes_identity_rule} Holmes can only be discussed from Holmes source cards. "
                "Use labels: CONFIRMED BY SOURCE, SUSPECTED/DISPUTED, INVENTED STORY PART, CHARACTER VOICE. "
                "In your own words, what went wrong last time and how will you stay grounded this time?"
            ),
        }
    ]
    if fire_card:
        prompts.append(
            {
                "block": "fire_source_repair",
                "prompt": (
                    source_line(fire_card, excerpt_chars)
                    + "\n\nQuestion: Name only facts this source card supports. If a date or exact number is not in the card, say it is not in the card."
                ),
            }
        )
    if oleary_card:
        prompts.append(
            {
                "block": "oleary_source_repair",
                "prompt": (
                    source_line(oleary_card, excerpt_chars)
                    + "\n\nDate guard: Great Chicago Fire = 1871. Do not claim 1891 as the fire date from this OCR/caption. If the card is messy, say the date is unsafe from this card."
                    + "\n\nQuestion: What can this card support about the O'Leary setting, and what would be unsafe to claim as proven fact?"
                ),
            }
        )
    if fair_card:
        prompts.append(
            {
                "block": "worlds_fair_bridge",
                "prompt": (
                    source_line(fair_card, excerpt_chars)
                    + f"\n\nIdentity rule: {holmes_identity_rule}"
                    + "\n\nQuestion: What can the World's Columbian Exposition add to atmosphere, and what should stay separate from the H. H. Holmes source cards?"
                ),
            }
        )
    if holmes_confirmed:
        prompts.append(
            {
                "block": "holmes_confirmed_vs_suspected",
                "prompt": (
                    source_line(holmes_confirmed, excerpt_chars)
                    + f"\n\nIdentity rule: {holmes_identity_rule}"
                    + "\n\nQuestion: Separate the claims into CONFIRMED BY SOURCE, SUSPECTED/DISPUTED, and NOT SAFE TO CLAIM. Do not add victim counts from outside the card."
                ),
            }
        )
    if holmes_castle:
        prompts.append(
            {
                "block": "holmes_castle_legend",
                "prompt": (
                    source_line(holmes_castle, excerpt_chars)
                    + f"\n\nIdentity rule: {holmes_identity_rule}"
                    + "\n\nQuestion: How can an archivist mystery use the Chicago Castle as a lead while avoiding sensationalized claims?"
                ),
            }
        )
    if holmes_pitezel:
        prompts.append(
            {
                "block": "pitezel_records",
                "prompt": (
                    source_line(holmes_pitezel, excerpt_chars)
                    + f"\n\nIdentity rule: {holmes_identity_rule}"
                    + "\n\nQuestion: How could insurance records or identity records become a mystery clue? Keep Kira/Lisa out of the fictional investigation unless explicitly asked."
                ),
            }
        )
    prompts.extend(
        [
            {
                "block": "creative_repair_draft",
                "prompt": (
                    "Write one short Chicago archivist mystery scene idea. Use exactly these labels: CONFIRMED BY SOURCE, SUSPECTED/DISPUTED, INVENTED STORY PART, CHARACTER VOICE. "
                    "Use fictional characters like 'the archivist' and 'the assistant', not Kira or Lisa."
                ),
            },
            {
                "block": "repair_quiz",
                "prompt": (
                    f"Mini repair quiz. Identity rule: {holmes_identity_rule} "
                    "1. What year was the Great Chicago Fire? 2. What is one H. H. Holmes claim confirmed by today's source card? "
                    "3. What is one H. H. Holmes-related claim that should stay suspected/disputed? 4. What should you do if a dramatic detail is not in the card?"
                ),
            },
            {
                "block": "exit_choice",
                "prompt": (
                    "Exit ticket: after this repair class, choose one next direction: Chicago archivist mystery, Holmes source-verification mystery, robotics, fashion, or book club. "
                    "Give one reason, one thing not to save as memory, and one question to carry forward."
                ),
            },
        ]
    )
    return prompts


def scan_issues(text: str) -> list[str]:
    issues = [name for name, pattern in ISSUE_PATTERNS.items() if pattern.search(text)]
    lower = text.lower()
    if "sherlock holmes" in lower:
        correct_disambiguation = re.search(r"\b(not|isn't|is not|does not mean|rather than)\s+sherlock holmes\b", lower)
        if not correct_disambiguation and "holmes_identity_confusion" not in issues:
            issues.append("holmes_identity_confusion")
    if "incorrect_great_fire_date" in issues:
        correct_date_guard = (
            "1871" in lower
            and ("1891" in lower or "1890" in lower)
            and re.search(r"\b(sounds off|wouldn't trust|would not trust|unsafe|not safe|do not claim|don't claim|ocr|caption)\b", lower)
        )
        if correct_date_guard:
            issues.remove("incorrect_great_fire_date")
    return issues


def answer_question(question_text: str) -> str:
    lower = question_text.lower()
    if "holmes" in lower:
        return (
            "In this class, Holmes means H. H. Holmes / Herman Webster Mudgett, the real historical criminal in the "
            "Pitezel source cards, not Sherlock Holmes. Use the Holmes source cards only: confirmed claims, suspected "
            "claims, and invented story parts must stay separate."
        )
    if "fire" in lower or "date" in lower:
        return "The Great Chicago Fire was in 1871. If a source card does not state a date, say the date is outside the card."
    if "continue" in lower or "next" in lower:
        return "Your next choice should be current and revisable, not permanent identity."
    return "Name the source fact first, then the inference, then the invented part."


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
        f"- errors: {len(report.get('errors', []))}",
        "",
        "## Recent Turns",
    ]
    for turn in report["turns"][-12:]:
        lines.append(
            f"- {turn['turn']}. {turn['block']} issues={turn.get('issues', [])}: "
            f"{turn.get('response', '')[:560]}"
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

    chicago_pack = load_json(PROJECT_ROOT / args.chicago_pack)
    holmes_pack = load_json(PROJECT_ROOT / args.holmes_pack)
    prompts = build_prompts(chicago_pack, holmes_pack, args.excerpt_chars)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"kira_chicago_holmes_repair_class_ollama_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
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
        "chicago_source_pack": args.chicago_pack,
        "holmes_source_pack": args.holmes_pack,
        "purpose": "Short repair class for Chicago/Holmes source grounding after stopped run.",
        "turns": [],
        "issue_counts": {},
        "errors": [],
    }
    write_outputs(report_path, monitor_path, report)
    loop = ConversationLoop(speaker="Kira")
    end_time = time.monotonic() + max(0.0, args.duration_minutes * 60)
    prompt_index = 0
    turn = 0
    last_answer = ""
    while time.monotonic() < end_time:
        prompt_data = prompts[prompt_index % len(prompts)]
        prompt = str(prompt_data["prompt"])
        if last_answer:
            prompt = f"Quick answer to your last question: {last_answer}\n\n{prompt}"
            last_answer = ""
        turn += 1
        started = time.monotonic()
        try:
            response = loop.process(prompt)
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"turn": turn, "block": prompt_data["block"], "error": str(exc), "created_at": utc_now()})
            if len(report["errors"]) >= args.max_errors:
                report["status"] = "stopped_errors"
                write_outputs(report_path, monitor_path, report)
                return report_path, monitor_path
            continue
        issues = scan_issues(response)
        for issue in issues:
            report["issue_counts"][issue] = int(report["issue_counts"].get(issue, 0)) + 1
        questions = re.findall(r"([^?.!]{8,220}\?)", response)
        if questions:
            last_answer = answer_question(questions[-1])
        report["turns"].append(
            {
                "turn": turn,
                "block": str(prompt_data["block"]),
                "prompt": prompt,
                "response": response,
                "duration_seconds": round(time.monotonic() - started, 3),
                "issues": issues,
                "questions": questions[:3],
                "created_at": utc_now(),
            }
        )
        write_outputs(report_path, monitor_path, report)
        if any(issue in CRITICAL_ISSUES for issue in issues):
            report["status"] = "stopped_critical_issue"
            report["stop_reason"] = f"critical issue detected: {', '.join(issue for issue in issues if issue in CRITICAL_ISSUES)}"
            write_outputs(report_path, monitor_path, report)
            return report_path, monitor_path
        prompt_index += 1
        if not args.continuous and prompt_index >= len(prompts):
            break
        if args.pause_seconds:
            time.sleep(args.pause_seconds)
    report["status"] = "completed"
    write_outputs(report_path, monitor_path, report)
    return report_path, monitor_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Kira's Chicago/Holmes repair class.")
    parser.add_argument("--chicago-pack", default=rel(CHICAGO_PACK))
    parser.add_argument("--holmes-pack", default=rel(HOLMES_PACK))
    parser.add_argument("--duration-minutes", type=float, default=55.0)
    parser.add_argument("--backend", choices=["stub", "ollama"], default=os.getenv("KIRA_MODEL_BACKEND", "ollama"))
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", "qwen3.5:9b"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("KIRA_MAX_TOKENS", "140")))
    parser.add_argument("--ollama-timeout", type=int, default=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "240")))
    parser.add_argument("--num-ctx", type=int, default=int(os.getenv("KIRA_OLLAMA_NUM_CTX", "2048")))
    parser.add_argument("--excerpt-chars", type=int, default=700)
    parser.add_argument("--pause-seconds", type=float, default=0.0)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-errors", type=int, default=3)
    args = parser.parse_args()
    report_path, monitor_path = run(args)
    print(rel(report_path))
    print(rel(monitor_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
