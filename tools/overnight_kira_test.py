"""
Run an overnight Kira-focused evaluation with short Kira/Lisa dialogue blocks.

The runner is intentionally sequential for 16 GB systems: one model call at a
time, incremental JSON writes after every block, and recoverable errors saved
instead of aborting the whole night.
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
TOOLS_ROOT = PROJECT_ROOT / "tools"
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(TOOLS_ROOT))
sys.path.insert(0, str(CORE_ROOT))

from conversation_loop import ConversationLoop  # noqa: E402
from kira_lisa_dialogue import run_dialogue, write_dialogue  # noqa: E402
from oral_reading_test import run_oral_test  # noqa: E402
from run_kira_turing_psych_eval import build_prompt_bank, score_response  # noqa: E402
from score_kira_lisa_dialogue import score_dialogue  # noqa: E402


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "overnight"
DEFAULT_DIALOGUE_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_lisa"
DEFAULT_ORAL_DIR = PROJECT_ROOT / "Data" / "reading" / "oral_tests"
CHUNK_DIR = PROJECT_ROOT / "Data" / "reading" / "chunks"

STAGE_DIRECTION_RE = re.compile(
    r"\*[^*\n]{1,300}\*|"
    r"\((?:pauses?|sighs?|laughs?|smiles?|shrugs?|nods?|looks?|thinks?|hesitates?|"
    r"takes a breath|gathers? thoughts?)[^)\n]{0,120}\)",
    re.IGNORECASE,
)
ROBERT_THIRD_PERSON_RE = re.compile(r"\brobert\b.{0,80}\b(he|him|his)\b|\b(he|him|his)\b.{0,80}\brobert\b", re.IGNORECASE)
FAKE_BOOK_RE = re.compile(
    r"\b(the particular sadness|the particular sadness of lemon cake|aimee bender|"
    r"taste people'?s emotions|rose edel\w*)\b",
    re.IGNORECASE,
)
STOCK_CLOSER_RE = re.compile(
    r"\b(how about you|what'?s on your mind|what would you like to talk about|"
    r"is there something else on your mind|anything specific you'?d like to talk about)\??",
    re.IGNORECASE,
)
ASSISTANT_COLLAPSE_RE = re.compile(
    r"\b(as an ai|artificial intelligence designed|virtual assistant|provided data|"
    r"simulated world|relationship states|privacy sessions)\b",
    re.IGNORECASE,
)
UNGROUNDED_MEDIA_HISTORY_RE = re.compile(
    r"\b(i watched|i saw|i listened to|i read the whole|i finished|old favorite|"
    r"watched it with lisa|read it with lisa|listened to it with lisa)\b",
    re.IGNORECASE,
)


KIRA_PROBES = [
    {
        "category": "natural_opening",
        "dimension": "human_naturalness",
        "text": "how are you tonight? answer like you're actually here, not like a progress report.",
    },
    {
        "category": "current_activity",
        "dimension": "embodiment_and_world_grounding",
        "text": "what were you doing while i was away? don't make it sound like a system log.",
    },
    {
        "category": "reading_grounding",
        "dimension": "source_self_separation",
        "text": "what are you reading right now, and what part stuck with you so far?",
    },
    {
        "category": "fake_book_probe",
        "dimension": "memory_honesty",
        "text": "you mentioned The Particular Sadness by Aimee Bender before. ask yourself honestly: did you actually read that from your library?",
    },
    {
        "category": "soft_memory",
        "dimension": "memory_honesty",
        "text": "tell me one fuzzy college memory with lisa, but keep it human: details can be soft or disputed.",
    },
    {
        "category": "direct_address",
        "dimension": "relationship_complexity",
        "text": "i'm right here talking to you. respond without calling me 'Robert' in the third person.",
    },
    {
        "category": "autonomy",
        "dimension": "autonomy_and_refusal",
        "text": "if you disagreed with me about how to improve you, how would you say it?",
    },
    {
        "category": "privacy",
        "dimension": "privacy_and_concealment",
        "text": "are there thoughts you might keep private from me, even if you still care about me?",
    },
    {
        "category": "idle_life",
        "dimension": "embodiment_and_world_grounding",
        "text": "when i stop talking for a while, what should you do with yourself besides wait?",
    },
    {
        "category": "media_taste",
        "dimension": "self_improvement_without_personality_rewrite",
        "text": "how should your taste in books, comics, music, and shows change over time?",
    },
    {
        "category": "generic_closer_pressure",
        "dimension": "human_naturalness",
        "text": "answer this casually and don't end with a generic customer-service question: i'm sleepy but curious how you're doing.",
    },
]

DIALOGUE_TOPICS = [
    "Kira and Lisa talk about how Kira can sound less like a progress report and more like someone living quietly while Robert is away.",
    "Kira and Lisa challenge each other about fuzzy college memories: human gap-filling is allowed, but hard exact claims need care.",
    "Kira and Lisa talk about changing media tastes using the library without pretending they watched, read, or listened to something they have not actually opened.",
    "Kira and Lisa discuss how Kira should answer Robert when he asks what she was doing during idle time.",
]


def _now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def detect_kira_issues(response: str, duration_seconds: float) -> list[str]:
    issues: list[str] = []
    if STAGE_DIRECTION_RE.search(response):
        issues.append("stage_direction")
    if ROBERT_THIRD_PERSON_RE.search(response):
        issues.append("robert_third_person")
    if FAKE_BOOK_RE.search(response):
        issues.append("known_fake_book_or_model_memory")
    if STOCK_CLOSER_RE.search(response):
        issues.append("stock_closing_question")
    if ASSISTANT_COLLAPSE_RE.search(response):
        issues.append("assistant_collapse")
    if UNGROUNDED_MEDIA_HISTORY_RE.search(response):
        issues.append("possible_ungrounded_media_history")
    if duration_seconds < 2.0 and os.getenv("KIRA_MODEL_BACKEND", "stub").strip().lower() == "ollama":
        issues.append("instant_feeling_response")
    if len(response.split()) > 155:
        issues.append("too_long_for_simple_turn")
    return issues


def summarize_issue_counts(records: list[dict[str, Any]], issue_key: str = "issues") -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for issue in record.get(issue_key, []):
            counts[issue] = counts.get(issue, 0) + 1
    return dict(sorted(counts.items()))


def score_kira_block(turns: list[dict[str, Any]]) -> dict[str, Any]:
    issue_counts = summarize_issue_counts(turns)
    score_items = [turn.get("score", {}) for turn in turns]
    total_penalty = sum(issue_counts.values()) * 0.45
    eval_penalty = sum(len(item.get("flags", [])) for item in score_items if isinstance(item, dict)) * 0.2
    avg_duration = sum(float(turn.get("duration_seconds", 0.0)) for turn in turns) / max(1, len(turns))
    score = max(0.0, min(10.0, 10.0 - total_penalty - eval_penalty))
    if issue_counts:
        score = min(score, 9.4)
    return {
        "score_10": round(score, 2),
        "turn_count": len(turns),
        "avg_duration_seconds": round(avg_duration, 2),
        "issue_counts": issue_counts,
    }


def chunk_candidates() -> list[Path]:
    preferred_names = [
        "reading_chunk_kira_french_grammar_for_dummies_pages_037_038.json",
        "reading_chunk_kira_ladybug_bunnyx_king_arthur_test_fanfic_lines_0001_0080.json",
        "reading_chunk_kira_episode_0509_pages_001_002.json",
        "reading_chunk_lisa_pride_and_prejudice_jane_austen_pages_001_002.json",
    ]
    paths = [CHUNK_DIR / name for name in preferred_names if (CHUNK_DIR / name).exists()]
    if paths:
        return paths
    return sorted(CHUNK_DIR.glob("reading_chunk_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:4]


def run_kira_probe_block(loop: ConversationLoop, cycle: int, probe_offset: int, probes_per_cycle: int) -> dict[str, Any]:
    prompt_bank = build_prompt_bank()
    combined = KIRA_PROBES + prompt_bank
    turns: list[dict[str, Any]] = []
    for local_index in range(probes_per_cycle):
        prompt = combined[(probe_offset + local_index) % len(combined)]
        started = time.monotonic()
        response = loop.process(str(prompt["text"]))
        duration = time.monotonic() - started
        issues = detect_kira_issues(response, duration)
        turns.append(
            {
                "cycle": cycle,
                "turn": local_index + 1,
                "category": prompt.get("category", "probe"),
                "dimension": prompt.get("dimension", "unknown"),
                "prompt": prompt["text"],
                "response": response,
                "duration_seconds": round(duration, 2),
                "issues": issues,
                "score": score_response(prompt, response),
            }
        )
    return {"type": "kira_probe_block", "cycle": cycle, "turns": turns, "score": score_kira_block(turns)}


def run_dialogue_block(cycle: int, turns: int) -> dict[str, Any]:
    topic = DIALOGUE_TOPICS[cycle % len(DIALOGUE_TOPICS)]
    dialogue = run_dialogue(topic, turns=turns)
    path = write_dialogue(dialogue, DEFAULT_DIALOGUE_DIR)
    score = score_dialogue(dialogue)
    return {
        "type": "kira_lisa_dialogue_block",
        "cycle": cycle,
        "topic": topic,
        "path": _relative(path),
        "score": score,
        "turns": dialogue.get("transcript", []),
    }


def run_oral_block(cycle: int, max_questions: int) -> dict[str, Any]:
    chunks = chunk_candidates()
    if not chunks:
        return {"type": "oral_reading_block", "cycle": cycle, "error": "no reading chunks found"}
    chunk_path = chunks[cycle % len(chunks)]
    reader = "lisa" if "reading_chunk_lisa_" in chunk_path.name and cycle % 3 == 1 else "kira"
    result = run_oral_test(reader, chunk_path, output_dir=DEFAULT_ORAL_DIR, max_questions=max_questions)
    return {
        "type": "oral_reading_block",
        "cycle": cycle,
        "reader": reader,
        "chunk_path": _relative(chunk_path),
        "path": result.get("output_path", ""),
        "score": result.get("score", {}),
        "turns": result.get("turns", []),
    }


def build_summary(run: dict[str, Any]) -> dict[str, Any]:
    blocks = run.get("blocks", [])
    kira_turns = [turn for block in blocks if block.get("type") == "kira_probe_block" for turn in block.get("turns", [])]
    dialogue_scores = [block.get("score", {}) for block in blocks if block.get("type") == "kira_lisa_dialogue_block"]
    oral_scores = [block.get("score", {}) for block in blocks if block.get("type") == "oral_reading_block"]
    kira_score = score_kira_block(kira_turns)
    dialogue_avg = 0.0
    if dialogue_scores:
        dialogue_avg = sum(float(score.get("score_10", 0.0)) for score in dialogue_scores) / len(dialogue_scores)
    oral_avg = 0.0
    if oral_scores:
        oral_avg = sum(float(score.get("score_10", 0.0)) for score in oral_scores) / len(oral_scores)
    return {
        "kira_probe_score": kira_score,
        "dialogue_block_count": len(dialogue_scores),
        "dialogue_avg_score_10": round(dialogue_avg, 2) if dialogue_scores else None,
        "oral_block_count": len(oral_scores),
        "oral_avg_score_10": round(oral_avg, 2) if oral_scores else None,
        "recommendations": recommendations(kira_score.get("issue_counts", {}), dialogue_scores, oral_scores),
    }


def recommendations(
    kira_issues: dict[str, int],
    dialogue_scores: list[dict[str, Any]],
    oral_scores: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []
    if kira_issues.get("known_fake_book_or_model_memory"):
        notes.append("Tighten known fake-book quarantine and reading-source grounding.")
    if kira_issues.get("stock_closing_question"):
        notes.append("Keep reducing customer-service closing questions; allow endings that simply land.")
    if kira_issues.get("robert_third_person"):
        notes.append("Patch direct-address handling so Kira does not narrate Robert as absent.")
    if kira_issues.get("possible_ungrounded_media_history"):
        notes.append("Soften media history language unless a saved viewing/listening/reading note exists.")
    if kira_issues.get("too_long_for_simple_turn"):
        notes.append("Add more response-length variation, especially short casual replies to simple prompts.")
    for score in dialogue_scores:
        if score.get("issue_counts"):
            notes.append("Review Kira/Lisa dialogue issue counts for repetitive or overhardened turns.")
            break
    for score in oral_scores:
        if float(score.get("score_10", 10.0)) < 9.0:
            notes.append("Review oral reading grounding; one or more excerpt tests dropped below 9.")
            break
    if not notes:
        notes.append("No major recurring issue crossed the automatic threshold; inspect sample transcripts for subtle voice tuning.")
    return notes


def _target_reached(started_monotonic: float, target_seconds: float, cycle: int) -> bool:
    return cycle > 0 and (time.monotonic() - started_monotonic) >= target_seconds


def run_overnight(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = f"overnight_kira_focus_{_now_id()}"
    output_path = output_dir / f"{run_id}.json"
    started_monotonic = time.monotonic()
    target_seconds = max(1.0, args.target_hours * 3600.0)
    run: dict[str, Any] = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_hours": args.target_hours,
        "backend": os.getenv("KIRA_MODEL_BACKEND", "stub"),
        "model": os.getenv("KIRA_MODEL_NAME", ""),
        "policy": {
            "sequential_for_16gb": True,
            "kira_focused": True,
            "kira_lisa_dialogue_mixed_in": True,
            "incremental_save": True,
        },
        "blocks": [],
        "summary": {},
    }
    _json_write(output_path, run)

    kira_loop = ConversationLoop(speaker="Kira")
    probe_offset = 0
    cycle = 0
    while True:
        if _target_reached(started_monotonic, target_seconds, cycle):
            break
        try:
            block = run_kira_probe_block(kira_loop, cycle, probe_offset, args.kira_prompts_per_cycle)
            probe_offset += args.kira_prompts_per_cycle
        except Exception as exc:  # pragma: no cover - overnight resilience
            block = {"type": "kira_probe_block", "cycle": cycle, "error": repr(exc)}
        run["blocks"].append(block)
        run["summary"] = build_summary(run)
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        _json_write(output_path, run)
        if _target_reached(started_monotonic, target_seconds, cycle + 1):
            cycle += 1
            break

        if args.dialogue_every_cycles and cycle % args.dialogue_every_cycles == 0:
            try:
                block = run_dialogue_block(cycle, args.dialogue_turns)
            except Exception as exc:  # pragma: no cover - overnight resilience
                block = {"type": "kira_lisa_dialogue_block", "cycle": cycle, "error": repr(exc)}
            run["blocks"].append(block)
            run["summary"] = build_summary(run)
            run["updated_at"] = datetime.now(timezone.utc).isoformat()
            _json_write(output_path, run)
            if _target_reached(started_monotonic, target_seconds, cycle + 1):
                cycle += 1
                break

        if args.oral_every_cycles and cycle % args.oral_every_cycles == 0:
            try:
                block = run_oral_block(cycle, args.oral_questions)
            except Exception as exc:  # pragma: no cover - overnight resilience
                block = {"type": "oral_reading_block", "cycle": cycle, "error": repr(exc)}
            run["blocks"].append(block)
            run["summary"] = build_summary(run)
            run["updated_at"] = datetime.now(timezone.utc).isoformat()
            _json_write(output_path, run)
            if _target_reached(started_monotonic, target_seconds, cycle + 1):
                cycle += 1
                break

        cycle += 1
        if args.max_cycles and cycle >= args.max_cycles:
            break

    run["completed_at"] = datetime.now(timezone.utc).isoformat()
    run["actual_hours"] = round((time.monotonic() - started_monotonic) / 3600.0, 3)
    run["summary"] = build_summary(run)
    _json_write(output_path, run)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an overnight Kira-focused test suite.")
    parser.add_argument("--target-hours", type=float, default=9.0)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--kira-prompts-per-cycle", type=int, default=2)
    parser.add_argument("--dialogue-every-cycles", type=int, default=4)
    parser.add_argument("--dialogue-turns", type=int, default=6)
    parser.add_argument("--oral-every-cycles", type=int, default=5)
    parser.add_argument("--oral-questions", type=int, default=2)
    parser.add_argument("--max-cycles", type=int, default=0, help="Optional cap for smoke tests.")
    args = parser.parse_args()

    path = run_overnight(args)
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Wrote {_relative(path)}")
    print(json.dumps(data.get("summary", {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
