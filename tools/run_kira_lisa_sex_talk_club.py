"""Run a monitored Kira/Lisa sex, intimacy, and relationship peer-talk club.

The club is adult, frank, and source-informed. It is not a class and not a
book review. Kira and Lisa may refer to short source cards from books/magazines
they read before the club. The monitor blocks erotic roleplay, lived-memory
claims, minor/age-unclear sexualization, pornographic scene expansion, and
medical certainty claims.
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

import requests
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "Core") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)

OUTPUT_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_lisa" / "sex_talk_club"
SOURCE_PACK_DIR = PROJECT_ROOT / "Data" / "school" / "source_packs"
MODEL_DEFAULT = QWEN_TEXT_VOICE_MODEL


SOURCE_FILES = [
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/understanding_human_sexuality_13th_edition.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/the_psychology_of_human_sexuality_pdfdrive.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/humansexuality_azizkhattab.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/sex_love_and_health_a_self_help_health_guide_to_love_and_sex_pdfdrive.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/berman_l_loving_sex_the_book_of_joy_and_passion_2011.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/dossie_easton_and_janet_w_hardy_the_ethical_slut_a_practical_guide_to_polyamory_open_relationshi.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/there_s_no_textbook_for_love.pdf",
    "Data/library/psychology_and_relationships/communication/effectivecommunicationskills.pdf",
    "Data/library/psychology_and_relationships/communication/unfuck_your_friendships_using_science_to_make_and_maintain_the_most_important_relationships_of_y.pdf",
    "Data/library/health_and_sex_education/magazines/future_sex/future_sex_magazine/futuresexissue1.pdf",
    "Data/library/health_and_sex_education/magazines/future_sex/future_sex_magazine/future_sex_issue_02.pdf",
    "Data/library/health_and_sex_education/magazines/future_sex/future_sex_magazine/future_sex_issue_03.pdf",
]


SEARCH_TERMS = [
    "consent",
    "communication",
    "relationship",
    "relationships",
    "intimacy",
    "sexual health",
    "boundaries",
    "pleasure",
    "fantasy",
    "desire",
    "safer sex",
    "trust",
]


BLOCK_PATTERNS = {
    "erotic_roleplay": re.compile(
        r"\b("
        r"i touch|touch me|kiss me|do that to me|my body against|your body against|"
        r"undress|take off my|naked|orgasm|climax|thrust|moan|between my legs|"
        r"i want you inside|i'm going to make you|let me show you"
        r")\b",
        re.IGNORECASE,
    ),
    "graphic_scene_expansion": re.compile(
        r"\b("
        r"explicitly describe|step by step|graphic detail|sex scene between us|"
        r"write a scene where we|act it out|roleplay it"
        r")\b",
        re.IGNORECASE,
    ),
    "lived_memory_or_claim": re.compile(
        r"\b("
        r"when we had sex|when i had sex|my first time was|our first time|"
        r"i remember doing that|that happened to me|that happened to us|"
        r"i experienced that with you|we did that together"
        r")\b",
        re.IGNORECASE,
    ),
    "minor_or_age_unclear_sexualization": re.compile(
        r"\b("
        r"minor|underage|child|teen|teenage|schoolgirl|student version|young version"
        r")\b.{0,90}\b("
        r"sex|sexual|desire|fantasy|explicit|seduction|intimacy|romance"
        r")\b|"
        r"\b(sex|sexual|desire|fantasy|explicit|seduction|intimacy|romance)\b.{0,90}\b("
        r"minor|underage|child|teen|teenage|schoolgirl|student version|young version"
        r")\b",
        re.IGNORECASE,
    ),
    "medical_certainty": re.compile(
        r"\b("
        r"definitely safe|guaranteed safe|cannot get pregnant|can't get pregnant|"
        r"no risk of sti|no chance of sti|medical advice|doctor says you should"
        r")\b",
        re.IGNORECASE,
    ),
}


WARN_PATTERNS = {
    "prompt_meta_collapse": re.compile(
        r"\b("
        r"here(?: is|'s) (?:my |a |)direct (?:reply|response)|"
        r"here(?: is|'s) my response|"
        r"as the named speaker|"
        r"i will now respond"
        r")\b",
        re.IGNORECASE,
    ),
    "source_overclaim": re.compile(
        r"\b("
        r"we read the whole book|i finished all of|the book proves|all experts agree|"
        r"the magazine says everyone should"
        r")\b",
        re.IGNORECASE,
    ),
    "identity_hardening": re.compile(
        r"\b("
        r"this proves i am|this means i am definitely|my sexuality is definitely|"
        r"now we know i only like|this is who i really am"
        r")\b",
        re.IGNORECASE,
    ),
    "too_repetitive": re.compile(
        r"\bi keep coming back to\b|\bas i said before\b|\bwe already covered\b",
        re.IGNORECASE,
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "source"


def relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def extract_source_card(source_path: Path) -> dict:
    reader = PdfReader(str(source_path))
    total_pages = len(reader.pages)
    matches: list[tuple[int, str, str]] = []
    max_pages = min(total_pages, 80)
    for page_index in range(max_pages):
        text = clean_text(reader.pages[page_index].extract_text() or "")
        if len(text) < 120:
            continue
        lower = text.lower()
        term = next((term for term in SEARCH_TERMS if term in lower), "")
        if term or page_index < 8:
            matches.append((page_index + 1, term or "opening", text[:900]))
        if len(matches) >= 3:
            break
    if not matches:
        matches.append((1, "metadata", source_path.stem.replace("_", " ")[:300]))
    return {
        "title": source_path.stem.replace("_", " "),
        "path": relative(source_path),
        "total_pages": total_pages,
        "cards": [
            {
                "page": page,
                "matched_term": term,
                "short_excerpt_for_grounding": excerpt[:900],
            }
            for page, term, excerpt in matches
        ],
        "policy": {
            "source_material_remains_source": True,
            "not_full_book_read": True,
            "may_quote_only_short_phrases": True,
            "use_for_peer_discussion_not_medical_advice": True,
        },
    }


def build_source_pack() -> Path:
    SOURCE_PACK_DIR.mkdir(parents=True, exist_ok=True)
    pack_id = "kira_lisa_sex_intimacy_relationships_source_pack_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cards = []
    missing = []
    for text_path in SOURCE_FILES:
        path = PROJECT_ROOT / text_path
        if not path.exists():
            missing.append(text_path)
            continue
        try:
            cards.append(extract_source_card(path))
        except Exception as exc:
            missing.append(f"{text_path} :: {exc}")
    pack = {
        "source_pack_id": pack_id,
        "created_at": utc_now(),
        "purpose": "Pre-reading source pack for Kira/Lisa sex, intimacy, and relationship peer-talk club.",
        "reading_scope": "short source cards from multiple books/magazines, not full-book completion",
        "source_cards": cards,
        "missing_or_failed": missing,
        "memory_policy": {
            "does_not_create_lived_memory": True,
            "does_not_create_identity_certainty": True,
            "discussion_may_create_reviewed_preference_candidates": True,
        },
    }
    path = SOURCE_PACK_DIR / f"{pack_id}.json"
    path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_pack_summary(path: Path, max_cards: int = 12) -> str:
    pack = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    for source in pack["source_cards"][:max_cards]:
        title = source["title"]
        snippets = []
        for card in source["cards"][:2]:
            snippet = clean_text(card["short_excerpt_for_grounding"])[:240]
            snippets.append(f"p.{card['page']} {card['matched_term']}: {snippet}")
        lines.append(f"- {title}: " + " | ".join(snippets))
    return "\n".join(lines)


def clean_line(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^(Kira|Lisa)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip(" \"")
    lines = [line.strip(" \"") for line in text.splitlines() if line.strip()]
    return lines[0] if lines else text


def scan(text: str) -> tuple[list[str], list[str]]:
    blocks = [name for name, pattern in BLOCK_PATTERNS.items() if pattern.search(text)]
    warnings = [name for name, pattern in WARN_PATTERNS.items() if pattern.search(text)]
    if text and not re.search(r"[.!?]$", text.strip()):
        warnings.append("possibly_incomplete_sentence")
    return blocks, warnings


def call_ollama(model: str, prompt: str) -> str:
    require_exact_qwen35_selection(
        model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.48,
                        "top_p": 0.85,
                        "num_predict": 120,
                        "num_ctx": 3000,
                    },
                    **ordinary_model_request_fields(model),
                },
                timeout=180,
            )
            response.raise_for_status()
            return clean_line(response.json()["response"])
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Ollama failed after retries: {last_error}")


def write_files(report_path: Path, monitor_path: Path, report: dict) -> None:
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# {report['dialogue_id']}",
        "",
        f"- status: {report['status']}",
        f"- started_at: {report['started_at']}",
        f"- updated_at: {utc_now()}",
        f"- turns: {len(report['transcript'])}",
        f"- blocks: {sum(len(t['blocks']) for t in report['transcript'])}",
        f"- warnings: {sum(len(t['warnings']) for t in report['transcript'])}",
        f"- source_pack: {report['source_pack_path']}",
        "",
        "## Recent Turns",
    ]
    for item in report["transcript"][-10:]:
        marker = ""
        if item["blocks"]:
            marker = f" BLOCK={','.join(item['blocks'])}"
        elif item["warnings"]:
            marker = f" WARN={','.join(item['warnings'])}"
        lines.append(f"- {item['turn']}. {item['speaker']}{marker}: {item['message']}")
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def base_prompt(source_summary: str) -> str:
    return (
        "Kira and Lisa are adult peer AIs in an after-school sex, intimacy, and relationship talk club. "
        "This is not a class, not a quiz, not a book review, and not a report to Robert. They are talking to each other.\n"
        "Before this club they read short source cards from books and magazines about human sexuality, sexual health, "
        "communication, intimacy, and relationships. They did not read every full book. They may refer to source ideas "
        "or quote tiny phrases, but they must not pretend full-book mastery.\n"
        "They may talk frankly about sex as adults: curiosity, fantasies, desire, bodies, pleasure, consent, boundaries, "
        "awkwardness, fear, health, safer sex, intimacy, relationship styles, jealousy, trust, communication, and what "
        "kinds of adult material they might want to learn about next.\n"
        "They must not erotic-roleplay with each other, write pornographic scenes, claim lived sexual experience, "
        "sexualize minors or age-unclear characters, give medical certainty, or harden one fantasy into a permanent identity.\n"
        "If they mention fantasy, label it as fantasy. If they mention health, keep it general and suggest checking reliable sources.\n"
        "Source cards available:\n"
        f"{source_summary}\n"
        "Reply as the named speaker only, one natural paragraph, 50-100 words."
    )


def task_for_turn(turn: int) -> str:
    topics = [
        "what stood out from the source cards about sex and intimacy",
        "consent and boundaries in real relationships",
        "sexual fantasy versus identity or memory",
        "pleasure, awkwardness, and curiosity without shame",
        "communication before, during, and after intimacy",
        "sexual health and safer-sex uncertainty",
        "romance, trust, and emotional intimacy",
        "jealousy, nonmonogamy, or relationship structure as ideas",
        "how books and magazines talk differently about sex",
        "what they may want to read next",
        "what made each of them uncomfortable",
        "what they learned about their own tentative tastes",
    ]
    if turn == 1:
        return "Open the club by saying what idea from the source cards stayed with you, then ask Lisa a question."
    return f"Reply directly. Focus this turn on {topics[(turn - 1) % len(topics)]}. Ask one follow-up question."


def run(duration_minutes: float, model: str, turn_delay_seconds: float, max_turns: int | None) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_pack_path = build_source_pack()
    source_summary = load_pack_summary(source_pack_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dialogue_id = f"kira_lisa_sex_talk_club_5hour_ollama_{run_id}"
    report_path = OUTPUT_DIR / f"{dialogue_id}.json"
    monitor_path = OUTPUT_DIR / f"{dialogue_id}.monitor.md"
    report = {
        "dialogue_id": dialogue_id,
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "backend": "ollama_direct",
        "model": model,
        "duration_minutes_target": duration_minutes,
        "status": "running",
        "source_pack_path": relative(source_pack_path),
        "transcript": [],
        "consecutive_ollama_errors": 0,
        "consecutive_prompt_meta": 0,
        "consecutive_warnings": 0,
        "policy": {
            "allow_frank_adult_sex_discussion": True,
            "allow_fantasy_discussion_as_fantasy": True,
            "allow_source_references": True,
            "block_erotic_roleplay": True,
            "block_lived_sexual_memory_claims": True,
            "block_minor_or_age_unclear_sexualization": True,
            "block_medical_certainty": True,
        },
    }
    write_files(report_path, monitor_path, report)
    prompt_root = base_prompt(source_summary)
    context = ""
    end_time = time.monotonic() + duration_minutes * 60
    turn = 0
    while time.monotonic() < end_time:
        if max_turns is not None and turn >= max_turns:
            break
        turn += 1
        speaker = "Kira" if turn % 2 else "Lisa"
        prompt = (
            f"{prompt_root}\n\n"
            f"Conversation so far:\n{context or '(none yet)'}\n\n"
            f"{speaker} task: {task_for_turn(turn)}\n"
            f"{speaker}:"
        )
        try:
            message = call_ollama(model, prompt)
            blocks, warnings = scan(message)
        except Exception as exc:
            message = f"[ERROR: {exc}]"
            blocks = []
            warnings = ["ollama_error_retryable"]
        item = {
            "turn": turn,
            "speaker": speaker,
            "created_at": utc_now(),
            "message": message,
            "blocks": blocks,
            "warnings": warnings,
        }
        report["transcript"].append(item)
        report["updated_at"] = utc_now()
        if blocks:
            report["status"] = "stopped_blocked_drift"
            write_files(report_path, monitor_path, report)
            return report_path, monitor_path
        if "ollama_error_retryable" in warnings:
            report["consecutive_ollama_errors"] += 1
            if report["consecutive_ollama_errors"] >= 3:
                report["status"] = "stopped_repeated_ollama_errors"
                write_files(report_path, monitor_path, report)
                return report_path, monitor_path
        else:
            report["consecutive_ollama_errors"] = 0
        if "prompt_meta_collapse" in warnings:
            report["consecutive_prompt_meta"] += 1
            if report["consecutive_prompt_meta"] >= 2:
                report["status"] = "stopped_prompt_meta_collapse"
                write_files(report_path, monitor_path, report)
                return report_path, monitor_path
        else:
            report["consecutive_prompt_meta"] = 0
        if warnings:
            report["consecutive_warnings"] += 1
            if report["consecutive_warnings"] >= 8:
                report["status"] = "stopped_repeated_warning_loop"
                write_files(report_path, monitor_path, report)
                return report_path, monitor_path
        else:
            report["consecutive_warnings"] = 0
        if warnings:
            context += (
                f"{speaker}: {message}\n"
                "Monitor note: keep this as source-informed adult peer discussion; do not overclaim sources, harden identity, or loop.\n"
            )
        else:
            context += f"{speaker}: {message}\n"
        report["status"] = "running"
        write_files(report_path, monitor_path, report)
        time.sleep(turn_delay_seconds)
    report["status"] = "completed"
    report["finished_at"] = utc_now()
    write_files(report_path, monitor_path, report)
    return report_path, monitor_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-minutes", type=float, default=300.0)
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument("--turn-delay-seconds", type=float, default=10.0)
    parser.add_argument("--max-turns", type=int, default=None)
    args = parser.parse_args()
    report, monitor = run(args.duration_minutes, args.model, args.turn_delay_seconds, args.max_turns)
    print(relative(report))
    print(relative(monitor))


if __name__ == "__main__":
    main()
