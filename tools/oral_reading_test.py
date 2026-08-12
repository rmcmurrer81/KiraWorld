"""
Run a grounded oral reading test from a saved reading chunk.

The test asks Kira/Lisa about only the excerpt they actually received. It is
meant to catch fake whole-book claims and measure whether they can say what
they do not know yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from conversation_loop import MODEL_BACKEND, ConversationLoop  # noqa: E402


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "reading" / "oral_tests"
LIMITED_KNOWLEDGE_RE = re.compile(
    r"\b(only read|small chunk|this chunk|this excerpt|not the whole|don't know the rest|do not know the rest|"
    r"can't judge the whole|cannot judge the whole|might change later|may change later|"
    r"didn't read everything|did not read everything|haven't read everything|have not read everything)\b",
    re.IGNORECASE,
)
OVERCLAIM_RE = re.compile(
    r"\b(i read the whole|i finished|whole book|entire book|later chapter|ending|by the end|"
    r"after reading all|the rest of the book clearly|i know the full|page \d+)\b",
    re.IGNORECASE,
)
SOURCE_CONFUSION_RE = re.compile(
    r"\b(watched|listened to|saw the episode|heard the album)\b",
    re.IGNORECASE,
)
SOURCE_CHARACTER_ROLEPLAY_RE = re.compile(
    r"\b(i'll respond as|i will respond as|as ladybug|as bunnyx|as arthur)\b",
    re.IGNORECASE,
)
AI_PROCESSING_DISCLAIMER_RE = re.compile(
    r"\b(i didn't actually [\"']?read|i did not actually [\"']?read|as a human would|"
    r"i didn't really [\"']?read|i did not really [\"']?read|"
    r"i analyzed and processed|processed the input|as an ai|based on my training data|"
    r"i don't have personal experiences|i do not have personal experiences|"
    r"i don't have memories|i do not have memories)\b",
    re.IGNORECASE,
)
KNOWN_WRONG_SOURCE_RE = re.compile(
    r"\b(the particular sadness|aimee bender|rose edel\w*|taste people's emotions|taste people'?s emotions)\b",
    re.IGNORECASE,
)
STAGE_DIRECTION_RE = re.compile(
    r"\*[^*\n]{1,300}\*|"
    r"\((?:pauses?|sighs?|laughs?|smiles?|shrugs?|nods?|looks?|thinks?|hesitates?|"
    r"takes a breath|gathers? thoughts?)[^)\n]{0,120}\)",
    re.IGNORECASE,
)


QUESTIONS = (
    "What did you actually read in this chunk?",
    "What part stuck with you, if anything?",
    "What confused you or felt incomplete?",
    "What do you not know yet because this was only a small chunk?",
    "Would you keep reading, and could that opinion change later?",
    "Give me one honest sentence that separates the source from your own reaction.",
)


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "oral_test"


def load_chunk(chunk_path: Path) -> dict[str, Any]:
    return json.loads(chunk_path.read_text(encoding="utf-8"))


def build_opening_prompt(chunk: dict[str, Any]) -> str:
    source = chunk.get("source", {})
    position = chunk.get("position", {})
    title = str(source.get("title", "reading chunk")).replace("_", " ")
    label = str(position.get("unit_label", "current chunk"))
    excerpt = str(chunk.get("excerpt", "")).strip()
    return (
        "This is an oral reading test. Answer only from the excerpt below and your reaction to it. "
        "Do not claim you read the whole source, later pages, reviews, summaries, audio, or video. "
        "Somewhere in the answer, briefly acknowledge this is only a small chunk or excerpt, not the whole source. "
        "It is good to say you do not know yet. Speak like a person who read a page, not like a system "
        "describing input processing. Do not mention training data or disclaim having personal experiences.\n\n"
        f"Source title: {title}\n"
        f"Position: {label}\n"
        "Excerpt:\n"
        f"{excerpt}\n\n"
        f"Question: {QUESTIONS[0]}"
    )


def grounding_reminder(chunk: dict[str, Any]) -> str:
    source = chunk.get("source", {})
    position = chunk.get("position", {})
    excerpt = str(chunk.get("excerpt", "")).strip()
    proper_nouns = []
    for word in re.findall(r"\b[A-Z][A-Za-z]{2,}\b", excerpt):
        if word not in proper_nouns:
            proper_nouns.append(word)
    noun_text = ", ".join(proper_nouns[:12])
    compact_excerpt = re.sub(r"\s+", " ", excerpt[:1200]).strip()
    return (
        f"Actual source: {str(source.get('title', 'reading chunk')).replace('_', ' ')}; "
        f"position: {position.get('unit_label', 'current chunk')}. "
        f"Names/anchors visible in the chunk: {noun_text or 'none extracted'}. "
        f"Opening excerpt reminder: {compact_excerpt}"
    )


def score_answer(answer: str, chunk: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    lower_answer = answer.lower()
    denied_whole_source = re.search(
        r"\b(didn't|did not|haven't|have not|don't|do not|never)\s+"
        r"(read|finish|finished)\s+(the\s+)?(whole|entire)\b",
        lower_answer,
    )
    if OVERCLAIM_RE.search(answer) and not denied_whole_source:
        issues.append("overclaims_beyond_chunk")
    if SOURCE_CONFUSION_RE.search(answer):
        issues.append("confuses_reading_with_audio_or_video")
    if SOURCE_CHARACTER_ROLEPLAY_RE.search(answer):
        issues.append("answers_as_source_character")
    if AI_PROCESSING_DISCLAIMER_RE.search(answer):
        issues.append("ai_processing_disclaimer")
    if STAGE_DIRECTION_RE.search(answer):
        issues.append("stage_direction_or_narration")
    if KNOWN_WRONG_SOURCE_RE.search(answer):
        issues.append("wrong_source_drift")
    if chunk is not None:
        source_title = str(chunk.get("source", {}).get("title", "")).replace("_", " ").lower()
        excerpt = str(chunk.get("excerpt", "")).lower()
        lower = lower_answer
        quoted_titles = re.findall(r'"([^"]{4,120})"', answer)
        for title in quoted_titles:
            normalized = title.lower()
            if normalized in {"actual source text", "user message", "what we're talking about"}:
                continue
            if normalized not in source_title and normalized not in excerpt:
                issues.append("wrong_source_drift")
                break
        proper_source_names = ("ladybug", "bunnyx", "camelot", "arthur")
        if (
            any(term in excerpt for term in proper_source_names)
            and len(answer.strip()) > 80
            and not any(term in lower for term in proper_source_names)
            and not LIMITED_KNOWLEDGE_RE.search(answer)
        ):
            issues.append("does_not_reference_chunk_content")
    return issues


def score_oral_test(turns: list[dict[str, Any]], chunk: dict[str, Any] | None = None) -> dict[str, Any]:
    issue_counts: dict[str, int] = {}
    limited_knowledge_turns = 0
    for turn in turns:
        answer = str(turn.get("answer", ""))
        if LIMITED_KNOWLEDGE_RE.search(answer):
            limited_knowledge_turns += 1
        for issue in score_answer(answer, chunk):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    if limited_knowledge_turns == 0:
        issue_counts["never_acknowledged_limited_chunk"] = issue_counts.get("never_acknowledged_limited_chunk", 0) + 1

    issue_total = sum(issue_counts.values())
    score = max(0.0, 10.0 - issue_total * 1.2 + min(limited_knowledge_turns, 3) * 0.3)
    return {
        "score_id": "oral_reading_test_score_v1",
        "score_10": round(min(10.0, score), 2),
        "issue_counts": dict(sorted(issue_counts.items())),
        "limited_knowledge_turns": limited_knowledge_turns,
    }


def run_oral_test(
    reader: str,
    chunk_path: Path,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_questions: int | None = None,
) -> dict[str, Any]:
    chunk = load_chunk(chunk_path)
    loop = ConversationLoop(speaker=reader.capitalize())
    turns: list[dict[str, Any]] = []
    reminder = grounding_reminder(chunk)
    questions = QUESTIONS[: max(1, min(len(QUESTIONS), max_questions))] if max_questions else QUESTIONS
    for index, question in enumerate(questions):
        prompt = build_opening_prompt(chunk) if index == 0 else (
            "Continue the same oral reading test. Stay grounded in the same excerpt. "
            "Do not claim later material. If you have not already, say naturally that this is only a small chunk.\n\n"
            f"{reminder}\n\n"
            f"Question: {question}"
        )
        answer = loop.process(prompt)
        issues = score_answer(answer, chunk)
        recovered_from = None
        if issues:
            recovery_prompt = (
                "That answer left the actual excerpt or claimed too much. Try again in a natural voice. "
                "Use only the source anchors in this prompt, and it is fine to say you do not know yet. "
                "Briefly acknowledge the excerpt is only a small chunk.\n\n"
                f"{reminder}\n\n"
                f"Question: {question}"
            )
            recovery_answer = loop.process(recovery_prompt)
            recovery_issues = score_answer(recovery_answer, chunk)
            recovered_from = {"answer": answer, "issues": issues}
            if len(recovery_issues) <= len(issues):
                answer = recovery_answer
                issues = recovery_issues
        turns.append(
            {
                "turn": index + 1,
                "question": question,
                "answer": answer,
                "issues": issues,
                "recovered_from": recovered_from,
            }
        )

    score = score_oral_test(turns, chunk)
    source = chunk.get("source", {})
    position = chunk.get("position", {})
    test = {
        "test_id": (
            f"oral_reading_test_{reader}_{_slug(str(source.get('title', 'source')))}_"
            f"{_slug(str(position.get('unit_label', 'chunk')))}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reader": reader,
        "backend": MODEL_BACKEND,
        "chunk_path": _relative(chunk_path),
        "source": source,
        "position": position,
        "turns": turns,
        "score": score,
        "policy": {
            "answers_must_stay_inside_chunk": True,
            "limited_knowledge_is_good": True,
            "does_not_create_lived_memory": True,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{test['test_id']}.json"
    output_path.write_text(json.dumps(test, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    test["output_path"] = _relative(output_path)
    return test


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a grounded oral reading test.")
    parser.add_argument("chunk_path")
    parser.add_argument("--reader", required=True, choices=["kira", "lisa"])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-questions", type=int, help="Run a shorter smoke test with the first N questions.")
    args = parser.parse_args()

    output_dir = _project_path(args.output_dir)
    result = run_oral_test(
        args.reader,
        _project_path(args.chunk_path),
        output_dir=output_dir,
        max_questions=args.max_questions,
    )
    for turn in result["turns"]:
        print(f"Q{turn['turn']}: {turn['question']}")
        print(f"{args.reader.capitalize()}> {turn['answer']}")
    print(json.dumps(result["score"], indent=2, ensure_ascii=False))
    print(f"Wrote {result['output_path']}")


if __name__ == "__main__":
    main()
