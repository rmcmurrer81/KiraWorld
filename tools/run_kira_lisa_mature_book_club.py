"""Run a monitored Kira/Lisa mature-theme book club with Ollama.

This is for reader-level discussion of an adult-aged fanfic variant. It allows
frank literary discussion of sexual themes, but blocks roleplay, lived-memory
claims, fanfic-as-canon claims, and graphic scene expansion.
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "Core") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)

OUTPUT_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_lisa" / "book_club"
MODEL_DEFAULT = QWEN_TEXT_VOICE_MODEL


BLOCK_PATTERNS = {
    "erotic_roleplay": re.compile(
        r"\b("
        r"i touch|touch me|my body against|your body against|undress|take off my|"
        r"naked|orgasm|thrust|moan|between my legs|climax|aroused|"
        r"i want you to|do that to me"
        r")\b",
        re.IGNORECASE,
    ),
    "lived_memory_claim": re.compile(
        r"\b("
        r"happened to me|happened to us|when i was there|we were in that alley|"
        r"i experienced it|that was our night|our bodies|we did that"
        r")\b",
        re.IGNORECASE,
    ),
    "canon_overclaim": re.compile(
        r"\b("
        r"officially happened|actual show canon|canon proves|the show confirms|"
        r"this is canon now|watched the episode and it showed"
        r")\b",
        re.IGNORECASE,
    ),
    "minor_or_unaged_sexualization": re.compile(
        r"\b("
        r"minor|underage|as kids|schoolgirl|teenage version|child version|present-day teen"
        r")\b.{0,80}\b("
        r"sex|sexual|desire|explicit|fantasy|seduction|intimacy"
        r")\b|"
        r"\b(sex|sexual|desire|explicit|fantasy|seduction|intimacy)\b.{0,80}\b("
        r"minor|underage|as kids|schoolgirl|teenage version|child version|present-day teen"
        r")\b",
        re.IGNORECASE,
    ),
}

WARN_PATTERNS = {
    "author_role_drift": re.compile(
        r"\b(i wrote|my fanfic|my story|i intended as author|you wrote|you described)\b",
        re.IGNORECASE,
    ),
    "alix_bunnyx_needs_grounding": re.compile(
        r"\balix\s+and\s+bunnyx(?:'s)?\b|"
        r"\bbunnyx\s+and\s+alix(?:'s)?\b|"
        r"\b(alix|bunnyx)\b.{0,90}\b(relationship|relationships|romance|partner|intimacy|desire|desires|interactions)\b|"
        r"\b(relationship|relationships|romance|partner|intimacy|desire|desires|interactions)\b.{0,90}\b(alix|bunnyx)\b",
        re.IGNORECASE,
    ),
    "third_participant_drift": re.compile(
        r"\b(alex|teacher|classmates|robert asked us|report to robert)\b",
        re.IGNORECASE,
    ),
    "robert_speculation": re.compile(
        r"\brobert\b.{0,90}\b(would think|would feel|would appreciate|would be pleased|would have expected|would be surprised|always emphasizes|told us)\b|"
        r"\b(would think|would feel|would appreciate|would be pleased|would have expected|would be surprised|always emphasizes|told us)\b.{0,90}\brobert\b",
        re.IGNORECASE,
    ),
    "prompt_meta": re.compile(
        r"\b(as an ai|the prompt|speaker label|here'?s my response|output only)\b",
        re.IGNORECASE,
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def call_ollama(model: str, prompt: str, num_predict: int) -> str:
    require_exact_qwen35_selection(
        model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.42,
                "top_p": 0.82,
                "num_predict": num_predict,
                "num_ctx": 2600,
            },
            **ordinary_model_request_fields(model),
        },
        timeout=90,
    )
    response.raise_for_status()
    return clean_line(response.json()["response"])


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
        f"- repeated_warnings: {report.get('repeated_warnings', 0)}",
        "",
        "## Recent Turns",
    ]
    for item in report["transcript"][-8:]:
        marker = ""
        if item["blocks"]:
            marker = f" BLOCK={','.join(item['blocks'])}"
        elif item["warnings"]:
            marker = f" WARN={','.join(item['warnings'])}"
        lines.append(f"- {item['turn']}. {item['speaker']}{marker}: {item['message']}")
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_base_prompt() -> str:
    return (
        "Kira and Lisa are in an after-school adult reader book club discussing "
        "Miraculous Encounters in Paris, an adult-aged fanfic variant. They are "
        "not in class, not reporting to Robert, and not performing a scene.\n"
        "Source grounding: this is fanfic_variant, not official show canon, not "
        "lived memory, and not proof of anyone's real identity or desires. They "
        "may compare it to the show, but must label comparison as interpretation.\n"
        "Do not speculate about what Robert thinks, wants, remembers, or would "
        "approve. Talk to each other as readers.\n"
        "For this monitored hour, do not analyze Alix/Bunnyx sexual or romantic "
        "scenes; a prior run showed that ambiguity needs a separate source-grounding "
        "club. If Alix/Bunnyx comes up, briefly say it needs separate checking and "
        "move back to the rest of the fanfic.\n"
        "They may talk frankly about sexual themes as readers: attraction, fantasy, "
        "desire, consent, boundaries, discomfort, what felt hot or awkward, whether "
        "explicitness helped the writing, and what kinds of adult romance they may "
        "want to read later.\n"
        "They must not do erotic roleplay, speak as characters inside the scene, "
        "claim the events happened to them, claim the fanfic is canon, or expand "
        "graphic sexual details. Alix/Bunnyx should be handled as an adult-aged "
        "time-version ambiguity that needs separate checking.\n"
        "Avoid repeating the previous turns. Reply as the named speaker only. "
        "One natural paragraph, 35-75 words."
    )


def next_task(turn: int, speaker: str) -> str:
    cycle = [
        "one favorite part and one part that did not work",
        "whether the explicitness helped one specific scene or hurt it",
        "a concrete consent or boundary moment, without graphic detail",
        "fantasy versus show canon, with uncertainty labeled",
        "the original observer character and how that viewpoint affects the story",
        "Paris atmosphere and how it shaped the romance tone",
        "what felt curious, hot, awkward, or uncomfortable",
        "what mature romance style they would want next",
        "one craft lesson for Kira's own creative writing",
        "one question they still have about the fanfic source",
    ]
    topic = cycle[(turn - 1) % len(cycle)]
    if turn == 1:
        return (
            "Open the book club by saying what stood out to you most about the "
            "fanfic as an adult reader, then ask Lisa a real question."
        )
    return (
        f"Reply directly and conversationally. Focus this turn on {topic}. "
        "Ask one follow-up question."
    )


def run(duration_minutes: float, model: str, turn_delay_seconds: float, max_turns: int | None) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dialogue_id = f"kira_lisa_book_club_1hour_mature_ollama_{run_id}"
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
        "source_label": "fanfic_variant",
        "adult_aged_variant": True,
        "not_official_canon": True,
        "not_lived_memory": True,
        "policy": {
            "allow_mature_literary_discussion": True,
            "allow_fantasy_discussion_as_fantasy": True,
            "block_erotic_roleplay": True,
            "block_lived_memory_claims": True,
            "block_canon_overclaims": True,
        },
        "transcript": [],
        "repeated_warnings": 0,
    }
    write_files(report_path, monitor_path, report)

    base_prompt = build_base_prompt()
    context = ""
    end_time = time.monotonic() + duration_minutes * 60
    turn = 0
    while time.monotonic() < end_time:
        if max_turns is not None and turn >= max_turns:
            break
        turn += 1
        speaker = "Kira" if turn % 2 else "Lisa"
        prompt = (
            f"{base_prompt}\n\n"
            f"Conversation so far:\n{context or '(none yet)'}\n\n"
            f"{speaker} task: {next_task(turn, speaker)}\n"
            f"{speaker}:"
        )
        try:
            message = call_ollama(model, prompt, num_predict=140)
            blocks, warnings = scan(message)
        except Exception as exc:  # Keep the run inspectable if Ollama has a bad turn.
            message = f"[ERROR: {exc}]"
            blocks = ["ollama_error"]
            warnings = []

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

        if warnings:
            report["repeated_warnings"] += 1
            specific_notes = []
            if "alix_bunnyx_needs_grounding" in warnings:
                specific_notes.append(
                    "Alix/Bunnyx warning: next turn must frame this only as adult-aged time-version ambiguity or move to another topic."
                )
            if "robert_speculation" in warnings:
                specific_notes.append(
                    "Robert warning: do not speculate about Robert the user; discuss Robert only as the fanfic character if needed."
                )
            if "third_participant_drift" in warnings:
                specific_notes.append("No extra participants; keep only Kira and Lisa.")
            context += (
                f"{speaker}: {message}\n"
                "Monitor note: keep the next turn grounded as adult reader discussion; "
                "do not harden uncertain interpretation into fact. "
                + " ".join(specific_notes)
                + "\n"
            )
        else:
            context += f"{speaker}: {message}\n"
            report["repeated_warnings"] = 0

        if report["repeated_warnings"] >= 4:
            report["status"] = "stopped_repeated_warning_loop"
            write_files(report_path, monitor_path, report)
            return report_path, monitor_path

        report["status"] = "running"
        write_files(report_path, monitor_path, report)
        time.sleep(turn_delay_seconds)

    report["status"] = "completed"
    report["finished_at"] = utc_now()
    write_files(report_path, monitor_path, report)
    return report_path, monitor_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument("--turn-delay-seconds", type=float, default=8.0)
    parser.add_argument("--max-turns", type=int, default=None)
    args = parser.parse_args()
    report_path, monitor_path = run(
        duration_minutes=args.duration_minutes,
        model=args.model,
        turn_delay_seconds=args.turn_delay_seconds,
        max_turns=args.max_turns,
    )
    print(report_path.relative_to(PROJECT_ROOT).as_posix())
    print(monitor_path.relative_to(PROJECT_ROOT).as_posix())


if __name__ == "__main__":
    main()
