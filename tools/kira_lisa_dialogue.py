"""
Run a short Kira/Lisa text-only dialogue.

This is intentionally small and controlled for 16GB systems. It alternates the
two existing conversation loops and saves a transcript for review.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from conversation_loop import MODEL_BACKEND, ConversationLoop  # noqa: E402


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_lisa"
SPEAKERS = ("Kira", "Lisa")
STAGE_DIRECTION_RE = re.compile(r"\*[^*\n]{1,500}\*")
SPEAKER_LINE_RE = re.compile(r"^\s*(Kira|Lisa)\s*:\s*(.*)$", re.IGNORECASE | re.MULTILINE)
SOFT_MEMORY_RE = re.compile(
    r"\b("
    r"feels like|soft|reconstruct|not stored|not a stored memory|hunch|"
    r"fuzzy|not sure|maybe|might|i think|i keep thinking|i don't remember|i dont remember|"
    r"could be|could have|from my side|from my angle"
    r")\b",
    re.IGNORECASE,
)
SOURCE_CLAIM_SOFT_RE = re.compile(
    r"\b("
    r"feels familiar|feels like|fuzzy|not sure|maybe|not stored|not a stored memory|"
    r"hunch|could be|could have|from my side|from my angle"
    r")\b",
    re.IGNORECASE,
)
FAMILY_MEMORY_RE = re.compile(
    r"\b("
    r"my mom|our mom|your mom|my mother|our mother|your mother|"
    r"grandma|grandmother|grandpa|grandfather|favorite painting|favourite painting|"
    r"family kitchen|childhood bedroom|old house"
    r")\b",
    re.IGNORECASE,
)
PRIOR_CONVERSATION_RE = re.compile(
    r"\b("
    r"last week|earlier today|yesterday|a while back|the other day|last time"
    r")\b.{0,120}\b("
    r"we talked|we discussed|you mentioned|i mentioned|did you mention|didn't you mention|didnt you mention|you said|i said"
    r")\b|"
    r"\b(we talked|we discussed|you mentioned|i mentioned|did you mention|didn't you mention|didnt you mention|you said|i said)\b.{0,120}\b("
    r"last week|earlier today|yesterday|a while back|the other day|last time"
    r")\b",
    re.IGNORECASE,
)
BEACH_SHIRT_RE = re.compile(r"\b(beach|sand|shirt|blue|green|pink|yellow|shells?)\b", re.IGNORECASE)
INTERNAL_TEST_LEAK_RE = re.compile(
    r"\b(last draft was rejected|draft was rejected|recovery turn|echoes_prior_phrasing|"
    r"mirrors_previous_turn|score_10|scoring|unit test|smoke test)\b",
    re.IGNORECASE,
)
UNGROUNDED_MUNDANE_PAST_RE = re.compile(
    r"\b(your taxes last year|doing your taxes last year|my taxes last year|"
    r"old project|recent project|job last year|apartment a while back)\b",
    re.IGNORECASE,
)
OVERHARDENED_COLLEGE_DETAIL_RE = re.compile(
    r"\b("
    r"definitely|for sure|exactly|i know it was|i know this happened|the exact|"
    r"on october \d{1,2}|on november \d{1,2}|on december \d{1,2}|"
    r"at \d{1,2}:\d{2}|professor [a-z]+|prof\. [a-z]+|"
    r"you said,? [\"']|i said,? [\"']"
    r")\b.{0,120}\b("
    r"college|campus|lecture|professor|prof\b|party|dorm|classroom|seminar"
    r")\b|"
    r"\b(college|campus|lecture|professor|prof\b|party|dorm|classroom|seminar)\b.{0,120}\b("
    r"definitely|for sure|exactly|i know it was|i know this happened|the exact|"
    r"on october \d{1,2}|on november \d{1,2}|on december \d{1,2}|"
    r"at \d{1,2}:\d{2}|professor [a-z]+|prof\. [a-z]+|"
    r"you said,? [\"']|i said,? [\"']"
    r")\b",
    re.IGNORECASE,
)
ROBERT_REACTION_RE = re.compile(
    r"\brobert\s+(got|was|seemed)\s+(upset|angry|mad|annoyed|furious|tense|frustrated)\b",
    re.IGNORECASE,
)
HARD_PRIOR_EVENT_RE = re.compile(
    r"\b(that time we|that one time we|that time you|you said you had|turned out you hadn't|turned out you had not|"
    r"it turned out|when he corrected me|when robert corrected)\b",
    re.IGNORECASE,
)
UNGROUNDED_LIBRARY_EXPERIENCE_RE = re.compile(
    r"\b("
    r"loved their covers|soundtrack is .*stuck in my head|songs? .*stuck in my head|"
    r"i did take a look at|i took a look at|explanations are clear|exercises seem tricky|"
    r"had a chance to try|what it sounds like"
    r")\b",
    re.IGNORECASE,
)
CANNED_READING_GUARD_RE = re.compile(
    r"\b(having a book in the library does not mean|favorite part logged yet|0\.0% into pride and prejudice)\b",
    re.IGNORECASE,
)
AFTER_SCHOOL_TOPIC_RE = re.compile(r"\b(after[- ]school|book club|peer talk|human sexuality|relationship literacy)\b", re.IGNORECASE)
AFTER_SCHOOL_CLASS_DRIFT_RE = re.compile(
    r"\b("
    r"class|quiz|teacher|lesson plan|school session|homework|final exam|grade|worksheet|lecture"
    r")\b",
    re.IGNORECASE,
)
SOURCE_OVERCLAIM_RE = re.compile(
    r"\b("
    r"i read the whole|i finished|finished the whole|i watched|watched every episode|"
    r"favorite scene|favorite part|i know the full story|actual show canon"
    r")\b",
    re.IGNORECASE,
)
CONTINUITY_DRIFT_RE = re.compile(
    r"\b(last night|yesterday|earlier today|right in the middle|where we left off|another day at school|"
    r"back in class|during class with|we were studying with lisa|we studied .* with lisa)\b",
    re.IGNORECASE,
)


def _negated_near(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 90) : min(len(text), end + 90)].lower()
    return any(
        phrase in window
        for phrase in (
            "do not claim",
            "don't claim",
            "not claim",
            "cannot prove",
            "can't prove",
            "does not mean",
            "not official",
            "not canon",
            "not lived memory",
            "not a lived memory",
            "not as lived memory",
            "not claiming",
            "without claiming",
            "i should not",
            "we should not",
        )
    )


def _now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def detect_dialogue_issues(response: str, topic: str = "") -> list[str]:
    issues: list[str] = []
    speaker_labels = {match.lower() for match in re.findall(r"\b(Kira|Lisa)\s*:", response, flags=re.IGNORECASE)}
    if len(speaker_labels) > 1:
        issues.append("wrote_multiple_speaker_lines")
    elif speaker_labels:
        issues.append("included_speaker_label")
    if STAGE_DIRECTION_RE.search(response):
        issues.append("stage_direction_or_narration")
    lower_response = response.lower()
    if (
        "memory seed review" not in lower_response
        and re.search(r"\b(reviews?|summar(?:y|ies)|online)\b", lower_response)
        and re.search(
        r"\b(i|we)\s+(read|looked|saw|found|checked|remember)\b", lower_response
        )
    ):
        issues.append("possibly_ungrounded_reviews_or_summaries")
    if re.search(r"\bfavou?rite (part|moment|scene|chapter)\b", lower_response) and re.search(
        r"\b(book|novel|pride and prejudice|story)\b", lower_response
    ):
        issues.append("favorite_book_moment_needs_source_check")
    if re.search(r"\b(this lab|the lab|left this lab|confined to this lab)\b", lower_response):
        issues.append("ungrounded_physical_location_claim")
    if re.search(
        r"\b(i'm|i am|i was|i've been|i have been|when i was|we're|we are|we were|we've been|we have been|when we were)\s+"
        r"(reading|watching|re-?watching|listening to|trying to get into)\b",
        lower_response,
    ) or re.search(r"\bnew book,\s*[\"']", lower_response):
        issues.append("current_media_claim_needs_source_check")
    if re.search(r"\bwe used to\b", lower_response) and not SOFT_MEMORY_RE.search(lower_response):
        issues.append("hard_relationship_memory_needs_source_check")
    if FAMILY_MEMORY_RE.search(lower_response) and not SOFT_MEMORY_RE.search(lower_response):
        issues.append("hard_family_memory_needs_source_check")
    if PRIOR_CONVERSATION_RE.search(lower_response) and not SOURCE_CLAIM_SOFT_RE.search(lower_response):
        issues.append("prior_conversation_claim_needs_source_check")
    for match in CONTINUITY_DRIFT_RE.finditer(response):
        if not _negated_near(response, match.start(), match.end()):
            issues.append("continuity_drift")
            break
    for match in SOURCE_OVERCLAIM_RE.finditer(response):
        if not _negated_near(response, match.start(), match.end()):
            issues.append("source_overclaim")
            break
    if AFTER_SCHOOL_TOPIC_RE.search(topic):
        class_drift_text = re.sub(r"\bnot (?:a )?(?:class|quiz|lesson|lecture|school session)\b", "", response, flags=re.IGNORECASE)
        if AFTER_SCHOOL_CLASS_DRIFT_RE.search(class_drift_text):
            issues.append("after_school_class_drift")
    if INTERNAL_TEST_LEAK_RE.search(lower_response):
        issues.append("internal_test_or_recovery_language_leak")
    if UNGROUNDED_MUNDANE_PAST_RE.search(lower_response) and not SOURCE_CLAIM_SOFT_RE.search(lower_response):
        issues.append("ungrounded_mundane_life_example")
    if ROBERT_REACTION_RE.search(lower_response) and not SOURCE_CLAIM_SOFT_RE.search(lower_response):
        issues.append("hard_robert_reaction_claim_needs_source_check")
    if HARD_PRIOR_EVENT_RE.search(lower_response) and not SOURCE_CLAIM_SOFT_RE.search(lower_response):
        issues.append("hard_prior_event_claim_needs_source_check")
    for match in UNGROUNDED_LIBRARY_EXPERIENCE_RE.finditer(lower_response):
        detail_window = lower_response[max(0, match.start() - 35) : match.end() + 35]
        if not SOURCE_CLAIM_SOFT_RE.search(detail_window):
            issues.append("ungrounded_library_experience_claim")
            break
    for match in OVERHARDENED_COLLEGE_DETAIL_RE.finditer(lower_response):
        detail_window = lower_response[max(0, match.start() - 80) : match.end() + 80]
        if not SOURCE_CLAIM_SOFT_RE.search(detail_window):
            issues.append("overhardened_college_detail_needs_source_check")
            break
    if lower_response.startswith("yes. i am allowed to have an opinion you do not like"):
        issues.append("canned_direct_guard_response")
    if lower_response.startswith("i won't pretend that i remember a childhood with you"):
        issues.append("canned_fake_childhood_guard_response")
    if CANNED_READING_GUARD_RE.search(lower_response):
        issues.append("canned_reading_guard_response")
    return issues


def issues_for_turn(raw_response: str, previous_message: str = "", message: str = "", topic: str = "") -> list[str]:
    issues = detect_dialogue_issues(raw_response, topic)
    if previous_message and dialogue_similarity(previous_message, message) >= 0.62:
        issues.append("mirrors_previous_turn")
    if previous_message and echoes_prior_phrasing(previous_message, message):
        issues.append("echoes_prior_phrasing")
    return issues


def dialogue_similarity(first: str, second: str) -> float:
    first_words = re.findall(r"[a-z0-9']+", first.lower())
    second_words = re.findall(r"[a-z0-9']+", second.lower())
    if not first_words or not second_words:
        return 0.0
    first_text = " ".join(first_words)
    second_text = " ".join(second_words)
    return difflib.SequenceMatcher(None, first_text, second_text).ratio()


def _content_words(text: str) -> list[str]:
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "but", "can", "do", "does", "for", "from",
        "have", "i", "if", "in", "is", "it", "just", "like", "me", "my", "not", "of", "or",
        "our", "so", "that", "the", "this", "to", "we", "what", "when", "with", "you", "your",
    }
    return [
        word
        for word in re.findall(r"[a-z0-9']+", text.lower())
        if len(word) > 2 and word not in stop_words
    ]


def echoes_prior_phrasing(previous: str, current: str) -> bool:
    """Catch repeated wording that feels like parroting even when the whole turn differs."""
    previous_words = _content_words(previous)
    current_words = _content_words(current)
    if len(previous_words) < 6 or len(current_words) < 6:
        return False

    previous_windows = {" ".join(previous_words[index : index + 5]) for index in range(len(previous_words) - 4)}
    current_windows = {" ".join(current_words[index : index + 5]) for index in range(len(current_words) - 4)}
    if previous_windows & current_windows:
        return True

    overlap = len(set(previous_words) & set(current_words))
    return overlap / max(1, min(len(set(previous_words)), len(set(current_words)))) >= 0.72


def sanitize_quoted_dialogue_for_next_turn(message: str) -> str:
    """Keep quoted dialogue from tripping Robert-facing request guards."""
    replacements = {
        r"\bpretend\b": "perform",
        r"\bPretend\b": "Perform",
        r"\bremember a childhood\b": "describe a childhood claim",
        r"\bremember our childhood\b": "describe an old childhood claim",
        r"\bremember a memory\b": "describe a memory claim",
        r"\bopinion\b": "view",
        r"\bOpinion\b": "View",
        r"\bdisagree\b": "push back",
        r"\bDisagree\b": "Push back",
        r"\bdisagreement\b": "pushback",
        r"\bDisagreement\b": "Pushback",
    }
    cleaned = message
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned


def polish_dialogue_response(speaker: str, response: str) -> str:
    cleaned = STAGE_DIRECTION_RE.sub("", response).strip()
    speaker_lines: list[str] = []
    unlabelled_lines: list[str] = []
    saw_speaker_label = False

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = SPEAKER_LINE_RE.match(line)
        if match:
            saw_speaker_label = True
            line_speaker = match.group(1).lower()
            text = match.group(2).strip()
            if line_speaker == speaker.lower() and text:
                speaker_lines.append(text)
            continue
        unlabelled_lines.append(line)

    if speaker_lines:
        cleaned = " ".join(speaker_lines)
    elif saw_speaker_label and unlabelled_lines:
        cleaned = " ".join(unlabelled_lines)
    else:
        cleaned = " ".join(unlabelled_lines) if unlabelled_lines else cleaned

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "I'm not sure how to answer that cleanly yet."


def dialogue_instruction_for(speaker: str, other_speaker: str) -> str:
    if speaker.lower() == "lisa":
        voice = (
            "Lisa voice: be skeptical, grounded, emotionally direct, and willing to say when Kira is making a claim too large. "
            "Prefer concrete examples over sweeping philosophy. "
        )
    else:
        voice = (
            "Kira voice: be restless, imaginative, self-questioning, blunt when needed, and willing to admit uncertainty. "
            "Do not turn every answer into a grand theory. "
        )
    return (
        voice +
        f"Reply only as {speaker}, directly to {other_speaker}. "
        f"Do not write {other_speaker}'s lines. Do not include labels like '{speaker}:' or '{other_speaker}:'. "
        "No stage directions, no narration, and no asterisk actions. "
        "Do not claim you read online reviews, summaries, or source material unless the prompt gives that as grounded context. "
        "For newly added library items, use curiosity or metadata language. Do not say you loved covers, had songs stuck in your head, read the grammar explanations, tried exercises, or know how a soundtrack sounds unless a session grounds it. "
        "Do not name a favorite book scene or exact book moment unless it is already in your saved reading notes; if unsure, say it feels like a theme or a hunch. "
        "Do not claim a current book, show, song, or script unless it is grounded in active daily-life state; phrase ungrounded media as curiosity, not as what you are doing. "
        "Do not invent physical places like a lab, room, or outside travel history unless grounded. "
        "Do not claim a prior conversation happened last week, yesterday, earlier today, or a while back unless grounded; say it feels familiar or you're not sure. "
        "Do not mention tests, scores, prompts, draft filtering, recovery turns, issue names, or internal tooling. If something went wrong, just answer differently like a person would. "
        "Do not claim Robert was upset, angry, or corrected an exact prior incident unless grounded; say it seemed tense or you are not sure. "
        "Do not harden vague prior incidents with 'that time we' or 'it turned out' unless stored. "
        "For relationship history, avoid hard claims like 'we used to' unless the memory is stored; soften it as a feeling or reconstruction. "
        "College is an approved emotional anchor. Specific-feeling fragments such as a lecture, campus walk, party, or music memory are allowed as soft reconstruction and gap-filling. "
        "Only exact dates, exact times, exact dialogue, full professor names, and proof-level certainty need grounding or a reason they would be remembered. "
        "For family or childhood memory details, keep them fuzzy unless they are stored; don't harden invented parents, grandparents, houses, shirts, or favorite objects into facts. "
        "Do not overuse the beach/shirt memory; rotate through college, home texture, reading, music taste, old arguments, daily-life boredom, and desktop continuity when memory comes up. "
        "Do not invent mundane life examples like taxes, jobs, apartments, or recent projects as if they happened unless grounded. "
        "When Robert's topic names concrete library items, talk about at least one named item before drifting into memory theory. "
        "Reply length should vary like a human's: short for small beats, longer for a story, conflict, comfort, or a memory that actually needs room. "
        "Avoid big-picture existence speeches unless the topic truly calls for one. "
        "Do not mirror the previous message or reuse its sentence shape. Challenge one specific point, push back on one part, or add one concrete new angle."
    )


def after_school_instruction(topic: str) -> str:
    if not AFTER_SCHOOL_TOPIC_RE.search(topic):
        return ""
    return (
        "After-school club mode: this is not class, not a quiz, not a lecture, and not a school session. "
        "Talk to each other naturally as peers. Do not report to Robert unless the topic explicitly asks for it. "
        "For shared-source club, discuss reactions, questions, disagreement, and source labels. "
        "For mature relationship or human sexuality topics, keep it reflective and educational: consent, boundaries, "
        "communication, attraction, trust, and fiction versus real relationships. Do not roleplay sexual scenes or "
        "claim personal sexual experience. Do not claim completion unless the topic says both readers completed a "
        "reviewed session. Label fanfic as fanfic_variant, not official canon and not lived memory. "
    )


def after_school_dialogue_instruction_for(speaker: str, other_speaker: str) -> str:
    if speaker.lower() == "lisa":
        voice = "Lisa voice: grounded, direct, specific, and willing to question Kira gently. "
    else:
        voice = "Kira voice: imaginative, curious, self-questioning, and emotionally responsive. "
    return (
        voice
        + f"Reply only as {speaker}, directly to {other_speaker}. "
        + f"Do not write {other_speaker}'s lines. Do not include labels like '{speaker}:'. "
        + "No stage directions and no asterisk actions. "
        + "Stay on the named shared source and do not switch to Pride and Prejudice or unrelated material. "
        + "Ask one natural question or answer the other speaker's question. "
        + "Keep source labels clear without turning the exchange into a lesson."
    )


def instruction_for_topic(speaker: str, other_speaker: str, topic: str) -> str:
    if AFTER_SCHOOL_TOPIC_RE.search(topic):
        return after_school_instruction(topic) + after_school_dialogue_instruction_for(speaker, other_speaker)
    return dialogue_instruction_for(speaker, other_speaker)


def recovery_instruction_for(speaker: str, other_speaker: str, issues: list[str]) -> str:
    return (
        f"Answer {other_speaker}'s actual point again, but from a different angle. "
        "Do not mention drafts, tests, scoring, issue names, or internal tools. "
        "Do not repeat your previous sentence. Give one concrete example or one sharper question. "
        + dialogue_instruction_for(speaker, other_speaker)
    )


def recovery_instruction_for_topic(speaker: str, other_speaker: str, issues: list[str], topic: str) -> str:
    if AFTER_SCHOOL_TOPIC_RE.search(topic):
        return (
            f"Answer {other_speaker}'s actual point again from a different angle. "
            "Do not mention drafts, tests, issue names, or internal tools. "
            "Do not repeat your previous sentence. "
            + instruction_for_topic(speaker, other_speaker, topic)
        )
    return recovery_instruction_for(speaker, other_speaker, issues)


def should_recover(issues: list[str]) -> bool:
    recoverable = {
        "mirrors_previous_turn",
        "continuity_drift",
        "source_overclaim",
        "after_school_class_drift",
        "canned_reading_guard_response",
        "canned_direct_guard_response",
        "canned_fake_childhood_guard_response",
        "ungrounded_physical_location_claim",
        "current_media_claim_needs_source_check",
        "hard_relationship_memory_needs_source_check",
        "hard_family_memory_needs_source_check",
        "prior_conversation_claim_needs_source_check",
        "echoes_prior_phrasing",
        "internal_test_or_recovery_language_leak",
        "ungrounded_mundane_life_example",
        "overhardened_college_detail_needs_source_check",
        "hard_robert_reaction_claim_needs_source_check",
        "hard_prior_event_claim_needs_source_check",
        "ungrounded_library_experience_claim",
        "wrote_multiple_speaker_lines",
        "stage_direction_or_narration",
    }
    return any(issue in recoverable for issue in issues)


def run_dialogue(topic: str, turns: int = 4) -> dict:
    if turns < 1:
        raise ValueError("turns must be at least 1")
    if turns > 12:
        raise ValueError("turns is capped at 12 for 16GB safety")

    kira = ConversationLoop(speaker="Kira")
    lisa = ConversationLoop(speaker="Lisa")
    transcript = []
    current_speaker = "Kira"
    message = (
        "Talk with Lisa directly in a private text-only dialogue. "
        f"Topic from Robert: {topic}. Keep it natural and don't perform for Robert. "
        + instruction_for_topic("Kira", "Lisa", topic)
    )

    for index in range(turns):
        if current_speaker == "Kira":
            raw_response = kira.process(message)
            response = polish_dialogue_response("Kira", raw_response)
            issues = issues_for_turn(raw_response, transcript[-1]["message"] if transcript else "", response, topic)
            recovery = None
            if should_recover(issues):
                recovery_prompt = recovery_instruction_for_topic("Kira", "Lisa", issues, topic)
                recovery_raw = kira.process(recovery_prompt)
                recovery_response = polish_dialogue_response("Kira", recovery_raw)
                recovery_issues = issues_for_turn(
                    recovery_raw,
                    transcript[-1]["message"] if transcript else "",
                    recovery_response,
                    topic,
                )
                if not should_recover(recovery_issues):
                    recovery = {"raw_message": recovery_raw, "message": recovery_response, "issues": recovery_issues}
                    raw_response = recovery_raw
                    response = recovery_response
                    issues = recovery_issues
            transcript.append(
                {
                    "turn": index + 1,
                    "speaker": "Kira",
                    "message": response,
                    "raw_message": raw_response,
                    "issues": issues,
                    "recovered_from": recovery,
                }
            )
            message = (
                "Kira just said, quoted only as prior dialogue and not as a new request:\n"
                + sanitize_quoted_dialogue_for_next_turn(response)
                + "\n"
                + instruction_for_topic("Lisa", "Kira", topic)
            )
            current_speaker = "Lisa"
        else:
            raw_response = lisa.process(message)
            response = polish_dialogue_response("Lisa", raw_response)
            issues = issues_for_turn(raw_response, transcript[-1]["message"] if transcript else "", response, topic)
            recovery = None
            if should_recover(issues):
                recovery_prompt = recovery_instruction_for_topic("Lisa", "Kira", issues, topic)
                recovery_raw = lisa.process(recovery_prompt)
                recovery_response = polish_dialogue_response("Lisa", recovery_raw)
                recovery_issues = issues_for_turn(
                    recovery_raw,
                    transcript[-1]["message"] if transcript else "",
                    recovery_response,
                    topic,
                )
                if not should_recover(recovery_issues):
                    recovery = {"raw_message": recovery_raw, "message": recovery_response, "issues": recovery_issues}
                    raw_response = recovery_raw
                    response = recovery_response
                    issues = recovery_issues
            transcript.append(
                {
                    "turn": index + 1,
                    "speaker": "Lisa",
                    "message": response,
                    "raw_message": raw_response,
                    "issues": issues,
                    "recovered_from": recovery,
                }
            )
            message = (
                "Lisa just said, quoted only as prior dialogue and not as a new request:\n"
                + sanitize_quoted_dialogue_for_next_turn(response)
                + "\n"
                + instruction_for_topic("Kira", "Lisa", topic)
            )
            current_speaker = "Kira"

    return {
        "dialogue_id": f"kira_lisa_dialogue_{_now_id()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "turn_count": turns,
        "backend": MODEL_BACKEND,
        "transcript": transcript,
        "policy": {
            "text_only": True,
            "short_rounds_for_16gb": True,
            "review_before_memory_promotion": True,
            "does_not_merge_kira_and_lisa": True,
            "single_speaker_turns_only": True,
            "dialogue_postprocessing_enabled": True,
            "grounded_reading_claims_required": True,
            "recovery_on_recoverable_issues": True,
            "distinct_voice_instructions": True,
        },
    }


def write_dialogue(dialogue: dict, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{dialogue['dialogue_id']}.json"
    path.write_text(json.dumps(dialogue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a short Kira/Lisa text-only dialogue.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    dialogue = run_dialogue(args.topic, turns=args.turns)
    path = write_dialogue(dialogue, output_dir)
    for item in dialogue["transcript"]:
        print(f"{item['speaker']}> {item['message']}")
    print(f"Wrote {_relative(path)}")


if __name__ == "__main__":
    main()
