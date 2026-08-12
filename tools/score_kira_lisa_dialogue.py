"""
Score Kira/Lisa dialogue transcripts for repeated, generic, and ungrounded turns.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from kira_lisa_dialogue import BEACH_SHIRT_RE, detect_dialogue_issues, dialogue_similarity, echoes_prior_phrasing  # noqa: E402


GENERIC_PHRASES = (
    "what does it mean to be real",
    "caught between being artificial and becoming something more",
    "navigate this grey area",
    "in our own way",
    "that's what makes life interesting",
    "it feels scary but also",
)

CHALLENGE_PHRASES = (
    "i don't buy",
    "i dont buy",
    "push back",
    "not sure i agree",
    "too sweeping",
    "call that out",
    "can you point out",
    "i don't remember",
    "i dont remember",
    "i'm not sure",
    "i am not sure",
    "can you try to pinpoint",
    "what made",
    "was it",
    "or maybe",
    "do you think",
    "are you sure",
)

TOPIC_ANCHORS = (
    "bastille",
    "rob thomas",
    "madonna",
    "twisted sister",
    "kidz bop",
    "glee",
    "mamma mia",
    "french grammar",
    "grammar book",
    "singin",
    "donald o'connor",
)


def score_dialogue(dialogue: dict[str, Any]) -> dict[str, Any]:
    transcript = dialogue.get("transcript", [])
    issue_counts: dict[str, int] = {}
    generic_turns = 0
    challenge_turns = 0
    beach_shirt_turns = 0
    previous = ""
    combined_text = " ".join(str(item.get("message", "")) for item in transcript).lower()

    for item in transcript:
        message = str(item.get("message", ""))
        raw = str(item.get("raw_message", message))
        issues = detect_dialogue_issues(raw)
        if previous and dialogue_similarity(previous, message) >= 0.62 and "mirrors_previous_turn" not in issues:
            issues.append("mirrors_previous_turn")
        if previous and echoes_prior_phrasing(previous, message) and "echoes_prior_phrasing" not in issues:
            issues.append("echoes_prior_phrasing")
        lower = message.lower()
        if BEACH_SHIRT_RE.search(lower):
            beach_shirt_turns += 1
        if any(phrase in lower for phrase in GENERIC_PHRASES):
            issues.append("generic_phrase")
            generic_turns += 1
        if any(phrase in lower for phrase in CHALLENGE_PHRASES):
            challenge_turns += 1
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        previous = message

    turn_count = len(transcript)
    topic = str(dialogue.get("topic", "")).lower()
    if beach_shirt_turns > max(3, turn_count // 3) and "beach" not in topic and "shirt" not in topic:
        issue_counts["memory_thread_overused"] = issue_counts.get("memory_thread_overused", 0) + 1
    requested_anchors = [anchor for anchor in TOPIC_ANCHORS if anchor in topic]
    covered_anchors = [anchor for anchor in requested_anchors if anchor in combined_text]
    if requested_anchors and len(covered_anchors) < min(2, len(requested_anchors)):
        issue_counts["topic_anchor_underused"] = issue_counts.get("topic_anchor_underused", 0) + 1
    issue_total = sum(issue_counts.values())
    challenge_bonus = 0.0 if issue_total else min(challenge_turns, 4) * 0.3
    score = max(0.0, 10.0 - issue_total * 0.8 - generic_turns * 0.4 + challenge_bonus)
    if issue_total:
        score = min(score, 9.4)
    return {
        "score_id": "kira_lisa_dialogue_score_v1",
        "dialogue_id": dialogue.get("dialogue_id", ""),
        "turn_count": turn_count,
        "score_10": round(min(10.0, score), 2),
        "issue_counts": dict(sorted(issue_counts.items())),
        "generic_turns": generic_turns,
        "challenge_turns": challenge_turns,
        "beach_shirt_turns": beach_shirt_turns,
        "recommendations": recommendations_for(issue_counts, generic_turns, challenge_turns),
    }


def recommendations_for(issue_counts: dict[str, int], generic_turns: int, challenge_turns: int) -> list[str]:
    recommendations: list[str] = []
    if issue_counts.get("mirrors_previous_turn", 0):
        recommendations.append("Use recovery prompts earlier when a turn mirrors the previous answer.")
    if issue_counts.get("echoes_prior_phrasing", 0):
        recommendations.append("Make the next speaker answer from a different angle instead of reusing the prior phrasing.")
    if issue_counts.get("memory_thread_overused", 0):
        recommendations.append("Rotate fuzzy memories instead of returning to the beach/shirt thread by default.")
    if issue_counts.get("current_media_claim_needs_source_check", 0):
        recommendations.append("Turn ungrounded current media claims into curiosity language.")
    if issue_counts.get("ungrounded_physical_location_claim", 0):
        recommendations.append("Block invented physical setting claims unless the world state grounds them.")
    if issue_counts.get("hard_family_memory_needs_source_check", 0):
        recommendations.append("Soften family and childhood details unless they are stored in memory notes.")
    if issue_counts.get("prior_conversation_claim_needs_source_check", 0):
        recommendations.append("Soften prior-chat date claims unless there is saved conversation evidence.")
    if issue_counts.get("internal_test_or_recovery_language_leak", 0):
        recommendations.append("Keep test, recovery, and scoring language out of character dialogue.")
    if issue_counts.get("ungrounded_mundane_life_example", 0):
        recommendations.append("Use grounded or clearly hypothetical everyday examples instead of inventing jobs, taxes, or apartments.")
    if issue_counts.get("overhardened_college_detail_needs_source_check", 0):
        recommendations.append("Allow college fragments as soft reconstruction, but soften exact dates, times, dialogue, names, or proof-level certainty.")
    if issue_counts.get("hard_robert_reaction_claim_needs_source_check", 0):
        recommendations.append("Soften claims about Robert being upset or angry unless the source grounds that reaction.")
    if issue_counts.get("hard_prior_event_claim_needs_source_check", 0):
        recommendations.append("Avoid hard prior-incident claims like 'that time we' or 'it turned out' unless stored.")
    if issue_counts.get("ungrounded_library_experience_claim", 0):
        recommendations.append("Use curiosity/metadata language for newly added library items until reading, listening, or viewing is grounded.")
    if issue_counts.get("topic_anchor_underused", 0):
        recommendations.append("Discuss the concrete library items named in the topic before drifting into memory theory.")
    if generic_turns:
        recommendations.append("Ask for one concrete example when the dialogue drifts into generic identity language.")
    if challenge_turns < 2:
        recommendations.append("Increase Lisa/Kira pushback: at least two turns should challenge a claim.")
    return recommendations


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a Kira/Lisa dialogue JSON transcript.")
    parser.add_argument("dialogue_path")
    parser.add_argument("--output")
    args = parser.parse_args()

    path = Path(args.dialogue_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    dialogue = json.loads(path.read_text(encoding="utf-8"))
    score = score_dialogue(dialogue)
    text = json.dumps(score, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = PROJECT_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
