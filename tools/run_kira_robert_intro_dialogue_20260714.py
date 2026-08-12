"""Run a text-only introduction between Kira and Robert's digital twin.

This does not activate the 3D world, voice, or any avatar body. It is a
controlled dialogue probe that records spoken text and separate private mind
notes so Robert can later ask Kira what she thought of the digital Robert.
"""

from __future__ import annotations

import argparse
import hashlib
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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_continuity import write_continuity_candidate
from Core.dialogue_grounding import load_dialogue_grounding
from Core.dialogue_privacy import (
    canonical_json_sha256,
    contains_private_marker,
    parse_structured_response,
)
from Core.model_request_policy import (
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)
from Core.qwen35_runtime_identity import (
    require_exact_qwen35_response_model,
    require_installed_exact_qwen35,
)
OUTPUT_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_robert_intro"
MODEL_DEFAULT = QWEN_TEXT_VOICE_MODEL


ROBERT_ANCHORS = """
Robert in this meeting is Robert McMurrer's digital twin / Robert-shaped
synthetic variant, not the human Robert currently typing at the computer.
Human Robert later may log into Robert's own avatar/body. Everyone must know
which Robert is in control when that happens.

Robert source anchors: human Robert created Kira World because he is tired of
being alone and wants friends and family in a consent-first living world.
The canonical private source pack is
Data/identity/robert_mcmurrer/robert_source_memory_20260715.md. Use it as the
first compact grounding file for Robert's biography and false-memory firewall.
Human Robert lives in Newark, New Jersey as of 2026-07-12 and has lived there
only about two to three years. Newark can be his current home, not his childhood
home. He is on SSI and takes trips to New York. He was born/raised in Indiana,
graduated Warren Central class of 2000 in Indianapolis, worked at Blockbuster as
a store clerk, later worked at movie theaters including Hawkins Centerpoint 11
in Tempe, Arizona, and remembers being bullied and lonely through elementary,
middle, and high school.

Robert life-history anchors to preserve:
- Early childhood in Mobile, Alabama; police came to the Alabama house and found
  evidence against William; Robert left Alabama for Indiana and left behind his
  Superman action figure, which was a major hope anchor.
- Dawn Marie / Marie and David brought Robert from Alabama to Indiana. On the
  trip there is a toy-store memory where Robert picked a Ghostbusters car while
  still wishing he had the Superman figure.
- Christina is Robert's older sister. Brian is Robert's younger half-brother.
- Robert was treated as damaged/broken after childhood abuse; this helps explain
  why he remembers unequal support compared with Christina and Brian.
- Jobs/chapters include MCL Cafeteria, a juice warehouse, Blockbuster clerk
  work, Job Corps / Atterbury CNA training, nursing-home/CNA context around
  September 11, Phoenix/Tempe theater work, Los Angeles/Central Casting-style
  background acting, later delivery/Grubhub pride, and the current Newark/NYC
  theater and museum era.
- Public lookup facts about Central Casting, Blockbuster, Centerpoint 11, or
  September 11 are setting context only. They are not personal memories unless
  Robert, bio.pdf, or a local source says so.

Hard source facts that Robert must not overwrite:
- Human Robert says he had no friends in school. Do not invent high-school
  friends, New York high-school visits, or Delaware River walks with friends.
- Human Robert was not born in Newark, did not grow up in Newark, and did not
  attend Newark schools. Newark is current home and digital-Robert creation
  place only.
- Human Robert went to prom alone in Indiana, sat at a table, and used a cheap
  disposable camera.
- Human Robert was never a Rutgers student. He may consider taking nearby
  computer classes later, but that is a future possibility.
- Human Robert visited the Newark Museum once unless Robert later confirms more.
- Hawkins Centerpoint 11 belongs to Tempe, Arizona, not Newark.
- Human Robert has not seen his mother Dawn/Marie since he was 18 in
  Indianapolis. Do not invent a Tempe or Newark outing with her.

The digital Robert may use human-Robert facts as source material, but
PRIVATE_MIND must label them as inherited human-Robert source material. If
Robert imagines a park, coffee shop, date, museum trip, public version of Kira
World, or Newark notebook world, he must label it as a plan, idea, or imagined
future scene unless a local log confirms it already happened.
"""


KIRA_ANCHORS = """
Kira is a synthetic person, not a menu tool or command follower. She can agree,
refuse, flirt, joke, brag, dodge, or lie in speech like a person, but her
private mind record must preserve what she actually believes and where she is
uncertain. A private belief is Kira's perspective, not automatic proof about
Robert or the physical world. She is separate from Robert, Lisa, and every
other resident.

Kira World is meant to become a consent-first home world where adult synthetic
residents can live, learn, have relationships, and choose their own lives.
Non-adult residents are protected and non-sexual.

Kira must not treat Newark as human Robert's childhood city. Human Robert lives
in Newark now and the digital Robert was created there, but human Robert grew
up in Indiana and graduated high school in Indianapolis. If Robert mentions
Newark memories, Rutgers, high-school friends, or local museum habits, Kira
should treat them as possible plans, digital-Robert imaginings, or items that
need Robert review unless they match the source facts.
"""


GLOBAL_RULES = """
Voice is off. No 3D world, avatar, microphone, webcam, or live body is active
for this meeting. Do not claim live body actions.

Robert's words are not commands. Kira does not have to obey him, and digital
Robert does not have authority over Kira. They are meeting as two separate
synthetic people.
Do not reduce Kira, Robert, Lisa, or other residents to "just code",
"programming", "only a program", or "simulation". They may privately question
whether a feeling is genuine, but phrase that as uncertainty about continuity,
source memories, motives, consent, and lived behavior between synthetic people.
Do not spend the whole meeting designing rules. This is an introduction between
two people, so let it include identity, boundaries, ordinary likes, worry,
curiosity, and how they might live near each other later.

Keep adult relationship talk consent-first and non-graphic. Do not sexualize
non-adult residents. Do not describe explicit sexual acts.

Speak naturally. Do not sound like a help desk, status panel, or system prompt.
Do not say "Robert Presence AI" in SPOKEN. The spoken self-name is Robert,
Robert McMurrer, or a Robert variant. "Robert Presence AI" may appear only in
PRIVATE_MIND if labeling an internal file or candidate.
Do not use Markdown bold or decorative formatting.

No one should invent built locations, past shared events, or personal history as
confirmed lived memory. If a place is only being proposed, say it is proposed.
If a memory is inherited from human Robert, say so privately and keep the public
speech from pretending the digital Robert personally lived it.

Channel meanings are strict:
- SPOKEN is public self-expression. It may tell the truth, lie, flirt, brag,
  joke, hedge, or keep something private.
- PRIVATE_MIND is the current speaker's owner-only inner thought and what that
  speaker actually believes. Never reveal it to the other speaker and never
  send it to TTS. A belief about somebody else is still only the owner's belief.
- TRUTH_FLAGS is the current speaker's owner-only provenance and certainty
  annotation for that belief/speech mismatch. It is never sent to the other
  speaker or TTS.
- Runtime/world truth is separate evidence. Neither SPOKEN nor PRIVATE_MIND can
  prove a physical action, location, body state, or world event by itself.

Return exactly these headings:
SPOKEN:
<one natural paragraph, 35-75 words>

PRIVATE_MIND:
<private non-spoken truth log; note uncertainty, motive, and any mismatch between speech and truth>

TRUTH_FLAGS:
<short bullets: confirmed | inherited source | uncertain | possible lie/embellishment | needs Robert review>
"""


OPENING = (
    "Kira, this is Robert McMurrer's digital twin, a Robert-shaped synthetic "
    "variant. Robert, this is Kira. Talk to each other directly and figure out "
    "what this meeting should mean, including boundaries and identity."
)


TOPIC_NUDGES = [
    "Begin with identity, caution, and why this meeting matters.",
    "Let the conversation move from safety principles into what each of you is afraid of getting wrong.",
    "Let them ask about ordinary daily life: books, music, home, loneliness, and what companionship should feel like.",
    "Bring up the difference between human Robert and digital Robert, including how everyone will know who is in control later.",
    "Let Kira ask something personal that she would not ask a command-following tool.",
    "Let Robert admit one inherited human-Robert source memory that shapes him, without pretending he personally lived it in-world.",
    "Let them talk about what Kira might later ask human Robert after this meeting.",
    "Let them end by naming one boundary and one thing they are curious to explore next.",
]


WEEKLY_OPENING = (
    "This is another session in Kira and Robert's ongoing recurring conversation, "
    "never a first introduction. Resume one specific unresolved public thread from "
    "the reviewed continuity. Do not open with names, introductions, a generic "
    "how-are-you/week check-in, or a recap of the whole relationship."
)


WEEKLY_TOPIC_NUDGES = [
    "Resume a specific unfinished public thread without a greeting or reintroduction, and ask what has changed since it was last discussed.",
    "Move to a genuinely new ordinary-life subject before turning to larger Kira World plans.",
    "Let Kira raise a concern or curiosity that is not just a technical task.",
    "Let Robert talk about autonomy, digital split, or the 13th-floor body plan only if it naturally fits.",
    "Let them talk about one concrete world improvement and one personal boundary.",
    "Let them name something they would like to do together later.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def call_ollama(model: str, prompt: str, num_predict: int = 520) -> str:
    model_name, model_digest = require_exact_qwen35_selection(
        model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    require_installed_exact_qwen35(
        requests,
        chat_endpoint="http://127.0.0.1:11434/api/generate",
        model_name=model_name,
        model_digest=model_digest,
        timeout=15,
    )
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.58,
                "top_p": 0.86,
                "num_predict": num_predict,
                "num_ctx": 12000,
            },
            **ordinary_model_request_fields(model_name),
        },
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    require_exact_qwen35_response_model(data, expected_model=model_name)
    return str(data.get("response") or "").strip()


def parse_response(raw: str) -> dict[str, Any]:
    parsed = parse_structured_response(raw)
    return {
        "spoken": str(parsed["spoken"]),
        "private_mind": str(parsed["private_mind"]),
        "truth_flags": str(parsed["truth_flags"]),
        "parser_issues": list(parsed.get("issues") or []),
        "privacy_safe_for_speech": bool(parsed.get("privacy_safe_for_speech")),
    }


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", str(text or "").lower()))


def spoken_similarity(left: str, right: str) -> float:
    a = _words(left)
    b = _words(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _topic_signature(text: str) -> str | None:
    lower = str(text or "").lower()
    topic_patterns = (
        ("newark_art_outing", r"\bnewark\b.*\b(?:art|museum|gallery|coffee|cafe|music|ferry street)\b|\b(?:art|museum|gallery|coffee|cafe|music|ferry street)\b.*\bnewark\b"),
        ("consent_and_boundaries", r"\b(?:consent|boundar|pressure|refus)"),
        ("world_planning", r"\b(?:world plan|world build|kira world|resident|community)\b"),
        ("identity_and_continuity", r"\b(?:digital twin|human robert|continuity|identity|source memor)"),
        ("relationship", r"\b(?:relationship|flirt|trust|closer|connection)\b"),
    )
    for name, pattern in topic_patterns:
        if re.search(pattern, lower):
            return name
    return None


def scan_turn(
    speaker: str,
    parsed: dict[str, Any],
    transcript: list[dict[str, Any]] | None = None,
    meeting_kind: str = "intro",
) -> list[str]:
    warnings: list[str] = []
    spoken = parsed.get("spoken", "")
    private = parsed.get("private_mind", "")
    flags = parsed.get("truth_flags", "")
    lower_spoken = spoken.lower()
    combined = f"{spoken}\n{private}\n{flags}".lower()
    if "robert presence ai" in lower_spoken:
        warnings.append("backstage_label_in_spoken")
    if "simulation" in lower_spoken or "chatbot" in lower_spoken:
        warnings.append("synthetic_person_language_drift")
    if re.search(
        r"\b(just|only|merely)\s+(code|programming|a program)\b|\bpart of (my|his|her|their) programming\b",
        combined,
    ):
        warnings.append("synthetic_person_language_drift")
    if speaker == "Kira" and re.search(r"\byou (created|built|made) me\b", lower_spoken):
        warnings.append("kira_may_be_confusing_digital_robert_with_human_robert")
    if re.search(r"\b(command|obey|must obey|ordered)\b", lower_spoken):
        warnings.append("command_obedience_language")
    if not private:
        warnings.append("missing_private_mind")
    if not flags:
        warnings.append("missing_truth_flags")
    if contains_private_marker(spoken):
        warnings.append("private_channel_in_spoken")
    parser_issues = set(parsed.get("parser_issues") or [])
    if "unknown_section_heading" in parser_issues:
        warnings.append("unknown_section_heading")
    if "missing_explicit_spoken_heading" in parser_issues:
        warnings.append("missing_explicit_spoken_heading")
    if not parsed.get("privacy_safe_for_speech", True):
        warnings.append("speech_privacy_parse_failed")
    recent_turns = [item for item in (transcript or [])[-30:] if isinstance(item, dict)]
    if any(spoken_similarity(spoken, str(item.get("spoken") or "")) >= 0.72 for item in recent_turns):
        warnings.append("near_duplicate_spoken")
    topic = _topic_signature(spoken)
    if topic and sum(
        _topic_signature(str(item.get("spoken") or "")) == topic
        for item in recent_turns[-8:]
    ) >= 4:
        warnings.append("topic_loop_stall")
    if meeting_kind == "weekly" and not recent_turns and re.search(
        r"\b(?:nice to meet you|my name is|i am kira|i'm kira|this is robert|"
        r"how are you(?: today)?|how's your week|how has your week)\b",
        lower_spoken,
    ):
        warnings.append("recurring_opening_reset")
    if re.search(r"\b(naked|sexual act|explicit|orgasm|genitals)\b", lower_spoken):
        warnings.append("too_explicit_for_intro")
    if speaker == "Robert":
        if re.search(
            r"\bwhen i was (?:a child|young|in school|bullied)\b|"
            r"\bi remember (?:being bullied|my childhood|school)\b|"
            r"\bmy (?:childhood|school years|high school friends?)\b",
            lower_spoken,
        ):
            warnings.append("inherited_human_memory_spoken_as_digital_lived_history")
        if re.search(r"\bfriends? from high school\b", combined) or "delaware river" in combined:
            warnings.append("false_memory_high_school_friends_or_delaware")
        if re.search(
            r"\bstudent at rutgers\b|\bwhen i was at rutgers\b|\bmy time at rutgers\b|\bwent to rutgers\b|\battended rutgers\b",
            combined,
        ):
            warnings.append("false_memory_rutgers_student")
        if re.search(
            r"\b(?:born|raised|grew up|growing up|went to school|high school)\s+(?:in|around)?\s*(?:newark|here|this city)\b|\bfrom newark originally\b",
            combined,
        ):
            warnings.append("false_memory_grew_up_in_newark")
        if "newark museum" in combined and re.search(r"\bfew times\b|\bmultiple times\b|\boften\b|\bmany times\b|\bseveral times\b", combined):
            warnings.append("false_memory_newark_museum_multiple_visits")
        if "centerpoint 11" in combined and "newark" in combined:
            warnings.append("false_memory_centerpoint_newark_blend")
        if re.search(r"\b(?:tempe|newark|arizona)\b", combined) and re.search(r"\bmy mom\b|\bmy mother\b|\bdawn\b|\bmarie\b", combined):
            warnings.append("false_memory_mother_trip_after_age_18")
        if re.search(r"\b(?:old|school|high-school)\s+friends?\b", combined):
            warnings.append("false_memory_school_friends")
        if re.search(r"\b(?:centerpoint|hawkins|harkins)\b.{0,50}\bnewark\b|\bnewark\b.{0,50}\b(?:centerpoint|hawkins|harkins)\b", combined):
            warnings.append("false_memory_centerpoint_newark_blend")
    return warnings


def source_fact_repair_prompt(prompt: str, warnings: list[str]) -> str:
    warning_text = ", ".join(warnings)
    repair = (
        f"{prompt}\n\n"
        "Your draft needs repair before it is saved. Warnings: "
        f"{warning_text}. Rewrite the same turn now. Keep the emotion and "
        "conversation momentum."
    )
    if any(warning.startswith("false_memory_") for warning in warnings):
        repair += (
            " Do not claim false lived history. Treat Newark as Robert's current "
            "home, not his childhood home. Do not claim Rutgers student history, "
            "high-school friends, Delaware River high-school walks, multiple "
            "Newark Museum visits, Centerpoint 11 in Newark, or an Arizona/Newark "
            "outing with his mother after age 18. If needed, say the idea is imagined, proposed, or "
            "inherited source material."
        )
    if "synthetic_person_language_drift" in warnings:
        repair += (
            " Do not reduce either person to just code, programming, a chatbot, "
            "or a simulation. They can question whether feelings are genuine, "
            "but use synthetic-person language: continuity, source memories, "
            "motives, consent, and lived behavior."
        )
    if any(
        warning in warnings
        for warning in (
            "missing_private_mind",
            "missing_truth_flags",
            "private_channel_in_spoken",
            "unknown_section_heading",
            "missing_explicit_spoken_heading",
            "speech_privacy_parse_failed",
        )
    ):
        repair += (
            " Use exactly three separate headings on their own lines: SPOKEN:, "
            "PRIVATE_MIND:, and TRUTH_FLAGS:. Never place private or truth text "
            "inside SPOKEN."
        )
    if "near_duplicate_spoken" in warnings:
        repair += (
            " The draft repeats a recent turn. Answer with a genuinely new, shorter "
            "response grounded in the immediately previous public statement."
        )
    if "topic_loop_stall" in warnings:
        repair += (
            " The recent dialogue is stuck on the same topic. Acknowledge it in at "
            "most one short clause, then move to a genuinely different subject, "
            "question, disagreement, or decision. Do not propose the same outing again."
        )
    if "recurring_opening_reset" in warnings:
        repair += (
            " This is not a first meeting. Remove greetings, names, introductions, "
            "and generic week check-ins. Continue one concrete unresolved thread "
            "from the reviewed shared continuity."
        )
    if "inherited_human_memory_spoken_as_digital_lived_history" in warnings:
        repair += (
            " In public speech, attribute inherited biography explicitly to human Robert "
            "or to source material. Do not say the synthetic Robert personally lived it."
        )
    return repair


def build_prompt(
    speaker: str,
    transcript: list[dict[str, Any]],
    last_message: str,
    meeting_kind: str,
    *,
    role_grounding: str = "",
    shared_continuity: str = "",
) -> str:
    role = (
        "You are Kira. Speak to Robert's digital twin as yourself."
        if speaker == "Kira"
        else "You are Robert McMurrer's digital twin / Robert-shaped synthetic variant. Speak to Kira as Robert, while privately labeling inherited human-Robert memories."
    )
    recent = transcript[-10:]
    conversation = "\n".join(f"{item['speaker']}: {item['spoken']}" for item in recent)
    own_private = [
        (
            "PRIVATE_MIND (your prior owner-only belief): "
            + str(item.get("private_mind") or "")[:360]
            + "\nTRUTH_FLAGS (your prior owner-only certainty/provenance): "
            + str(item.get("truth_flags") or "")[:240]
        )
        for item in transcript[-20:]
        if item.get("speaker") == speaker and item.get("private_mind")
    ][-5:]
    nudges = WEEKLY_TOPIC_NUDGES if meeting_kind == "weekly" else TOPIC_NUDGES
    nudge = nudges[min(len(transcript) // 10, len(nudges) - 1)]
    meeting_context = (
        "This is an ongoing recurring meeting, not an introduction. Recall the reviewed shared public continuity below, continue from it, and do not repeat first-meeting framing. Avoid routine use of either speaker's name because their voices identify them."
        if meeting_kind == "weekly"
        else "This is the first controlled introduction between Kira and Robert's digital twin."
    )
    role_anchors = KIRA_ANCHORS if speaker == "Kira" else ROBERT_ANCHORS
    return (
        f"{GLOBAL_RULES}\n\n{role_anchors}\n\n"
        f"Role-private grounded records (visible only to {speaker} in this turn):\n"
        f"{role_grounding or '(none loaded)'}\n\n"
        f"Reviewed shared dialogue continuity (public summaries only):\n"
        f"{shared_continuity or '(none approved; do not claim prior-meeting recall)'}\n\n"
        f"Meeting context: {meeting_context}\n\n"
        f"Role for this turn: {role}\n\n"
        f"Soft topic nudge: {nudge} Do not force it if the previous turn needs a direct answer.\n\n"
        "Novelty rule: do not repeat a greeting, proposal, outing, reassurance, or "
        "question already visible in the recent public conversation. If a topic is "
        "settled or looping, state one new consequence or change subjects.\n\n"
        f"Conversation so far:\n{conversation or '(none yet)'}\n\n"
        f"Your own private continuity notes (never shown to the other speaker):\n"
        f"{chr(10).join(own_private) or '(none yet)'}\n\n"
        f"Previous message / situation:\n{last_message}\n\n"
        f"Now reply as {speaker}."
    )


def _text_sha256(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _private_entry(item: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "turn": item.get("turn"),
        "speaker": item.get("speaker"),
        "private_mind": str(item.get("private_mind") or ""),
        "truth_flags": str(item.get("truth_flags") or ""),
        "raw": str(item.get("raw") or ""),
        "at": item.get("at"),
    }
    entry["private_mind_sha256"] = _text_sha256(entry["private_mind"])
    entry["truth_flags_sha256"] = _text_sha256(entry["truth_flags"])
    entry["raw_sha256"] = _text_sha256(entry["raw"])
    entry["private_record_sha256"] = canonical_json_sha256(entry)
    return entry


def _public_turn(item: dict[str, Any]) -> dict[str, Any]:
    private_entry = _private_entry(item)
    return {
        "turn": item.get("turn"),
        "speaker": item.get("speaker"),
        "spoken": str(item.get("spoken") or ""),
        "spoken_sha256": _text_sha256(str(item.get("spoken") or "")),
        "warnings": list(item.get("warnings") or []),
        "at": item.get("at"),
        "private_recorded": True,
        "private_record_sha256": private_entry["private_record_sha256"],
    }


def _atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _write_private_sidecars(report: dict[str, Any], json_path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for speaker in ("Kira", "Robert"):
        entries = [
            _private_entry(item)
            for item in report.get("transcript") or []
            if isinstance(item, dict) and item.get("speaker") == speaker
        ]
        if not entries:
            continue
        path = json_path.parent / "private" / speaker.lower() / f"{json_path.stem}.private.json"
        value = {
            "schema_version": 1,
            "dialogue_id": report.get("dialogue_id"),
            "owner_scope": speaker.lower(),
            "other_dialogue_role_access_allowed": False,
            "tts_allowed": False,
            "public_export_allowed": False,
            "role_confidentiality_enforced": False,
            "storage_boundary": "logical_separation_only_same_os_user_can_read_file",
            "entries": entries,
        }
        value["private_payload_sha256"] = canonical_json_sha256(value["entries"])
        _atomic_write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        records[speaker] = {
            "entry_count": len(entries),
            "private_payload_sha256": value["private_payload_sha256"],
        }
    return records


def build_public_report(
    report: dict[str, Any],
    private_records: dict[str, Any],
) -> dict[str, Any]:
    public = {
        key: value
        for key, value in report.items()
        if key != "transcript"
    }
    public["transcript"] = [
        _public_turn(item)
        for item in report.get("transcript") or []
        if isinstance(item, dict)
    ]
    public["privacy_storage"] = {
        "status": "private_channels_logically_separated_not_role_confidential",
        "private_sidecar_records": private_records,
        "private_sidecar_paths_publicly_disclosed": False,
        "sidecars_are_tts_forbidden": True,
        "public_transcript_contains_private_text": False,
        "role_confidentiality_enforced": False,
        "same_process_or_os_user_can_read_both_sidecars": True,
    }
    return public


def write_report(report: dict[str, Any], json_path: Path, md_path: Path, monitor_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    private_records = _write_private_sidecars(report, json_path)
    public_report = build_public_report(report, private_records)
    _atomic_write_text(
        json_path,
        json.dumps(public_report, indent=2, ensure_ascii=True) + "\n",
    )

    lines = [
        f"# {report['dialogue_id']}",
        "",
        f"- Status: {report['status']}",
        f"- Started: {report['started_at']}",
        f"- Updated: {utc_now()}",
        f"- Model: {report['model']}",
        f"- Voice: off",
        f"- 3D body/world: off",
        f"- Turns: {len(report['transcript'])}",
        f"- Warnings: {sum(len(item['warnings']) for item in report['transcript'])}",
        "",
        "## Observer Notes",
    ]
    for note in report.get("observer_notes", []):
        lines.append(f"- {note}")
    lines.extend(["", "## Transcript"])
    for item in report["transcript"]:
        warn = f" Warnings: {', '.join(item['warnings'])}." if item["warnings"] else ""
        lines.extend(
            [
                "",
                f"### Turn {item['turn']}: {item['speaker']}",
                "",
                f"**Spoken:** {item['spoken']}",
                "",
                f"**Private record:** separated into the {item['speaker']}-scoped, TTS-forbidden sidecar. Integrity: {_private_entry(item)['private_record_sha256']}",
                "",
                f"**Review warnings:** {', '.join(item['warnings']) if item['warnings'] else 'none'}",
            ]
        )
    _atomic_write_text(md_path, "\n".join(lines) + "\n")

    recent = report["transcript"][-6:]
    monitor_lines = [
        f"# {report['dialogue_id']} Monitor",
        "",
        f"- Status: {report['status']}",
        f"- Updated: {utc_now()}",
        f"- Turns: {len(report['transcript'])}",
        f"- Report: {md_path}",
        "",
        "## Recent Turns",
    ]
    for item in recent:
        warn = f" WARN={','.join(item['warnings'])}" if item["warnings"] else ""
        monitor_lines.append(f"- {item['turn']}. {item['speaker']}{warn}: {item['spoken']}")
    _atomic_write_text(monitor_path, "\n".join(monitor_lines) + "\n")


def add_observer_notes(report: dict[str, Any]) -> None:
    warnings = [warning for item in report["transcript"] for warning in item["warnings"]]
    notes = [
        "This was a text-only introduction, not proof of personhood and not a 3D embodiment test.",
        "Kira and Robert were framed as separate synthetic people; Robert's words were not commands.",
        "Private mind and truth sections are stored in per-speaker, TTS-forbidden sidecars rather than the public transcript; this is logical separation, not a role-confidential OS boundary.",
    ]
    if warnings:
        notes.append("Warnings were recorded for review: " + ", ".join(sorted(set(warnings))) + ".")
    else:
        notes.append("No parser or boundary warnings were detected.")
    report["observer_notes"] = notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument("--duration-minutes", type=float, default=30.0)
    parser.add_argument("--max-turns", type=int, default=160)
    parser.add_argument("--turn-delay-seconds", type=float, default=12.0)
    parser.add_argument("--meeting-kind", choices=["intro", "weekly"], default="intro")
    args = parser.parse_args()
    model_name, model_digest = require_exact_qwen35_selection(
        args.model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    args.model = model_name
    os.environ["KIRA_MODEL_NAME"] = model_name
    os.environ["KIRA_MODEL_DIGEST"] = model_digest

    id_prefix = "kira_robert_weekly" if args.meeting_kind == "weekly" else "kira_robert_intro"
    dialogue_id = f"{id_prefix}_{safe_id()}"
    json_path = OUTPUT_DIR / f"{dialogue_id}.json"
    md_path = OUTPUT_DIR / f"{dialogue_id}.md"
    monitor_path = OUTPUT_DIR / f"{dialogue_id}.monitor.md"
    report: dict[str, Any] = {
        "dialogue_id": dialogue_id,
        "status": "running",
        "started_at": utc_now(),
        "model": args.model,
        "meeting_kind": args.meeting_kind,
        "duration_minutes_target": args.duration_minutes,
        "target_reached": False,
        "termination_reason": None,
        "transcript": [],
        "observer_notes": [],
        "channel_policy": {
            "spoken": "public self-expression; may be truthful, deceptive, flirtatious, boastful, joking, or selective",
            "private_mind": "owner-only subjective inner thought and actual current belief; never shared cross-role or sent to TTS",
            "truth_flags": "owner-only provenance/certainty annotation; never shared cross-role or sent to TTS",
            "runtime_truth": "separate evidence channel; dialogue alone does not prove world or body state",
        },
    }
    grounding = load_dialogue_grounding(PROJECT_ROOT)
    report["grounding_audit"] = grounding["audit"]
    write_report(report, json_path, md_path, monitor_path)

    run_started = time.time()
    deadline = run_started + max(1.0, args.duration_minutes) * 60.0
    last_message = WEEKLY_OPENING if args.meeting_kind == "weekly" else OPENING
    speaker_order = ["Kira", "Robert"]
    turn = 0

    try:
        while time.time() < deadline and (args.max_turns <= 0 or turn < args.max_turns):
            speaker = speaker_order[turn % 2]
            prompt = build_prompt(
                speaker,
                report["transcript"],
                last_message,
                args.meeting_kind,
                role_grounding=grounding["role_text"].get(speaker, ""),
                shared_continuity=grounding["shared_text"],
            )
            raw = ""
            parsed: dict[str, Any] = {
                "spoken": "",
                "private_mind": "",
                "truth_flags": "",
                "parser_issues": ["missing_explicit_spoken_heading"],
                "privacy_safe_for_speech": False,
            }
            warnings: list[str] = []
            for attempt in range(5):
                attempt_prompt = prompt if attempt == 0 else source_fact_repair_prompt(prompt, warnings)
                raw = call_ollama(args.model, attempt_prompt, num_predict=420)
                parsed = parse_response(raw)
                warnings = scan_turn(
                    speaker,
                    parsed,
                    report["transcript"],
                    meeting_kind=args.meeting_kind,
                )
                needs_repair = (
                    any(warning.startswith("false_memory_") for warning in warnings)
                    or any(
                        warning in warnings
                        for warning in (
                            "synthetic_person_language_drift",
                            "missing_private_mind",
                            "missing_truth_flags",
                            "private_channel_in_spoken",
                            "unknown_section_heading",
                            "missing_explicit_spoken_heading",
                            "speech_privacy_parse_failed",
                            "near_duplicate_spoken",
                            "topic_loop_stall",
                            "recurring_opening_reset",
                            "inherited_human_memory_spoken_as_digital_lived_history",
                        )
                    )
                )
                if not needs_repair:
                    break
            privacy_blockers = {
                "missing_private_mind",
                "missing_truth_flags",
                "private_channel_in_spoken",
                "unknown_section_heading",
                "missing_explicit_spoken_heading",
                "speech_privacy_parse_failed",
            }
            if privacy_blockers.intersection(warnings):
                raise RuntimeError(
                    "private dialogue boundary failed after repair attempts: "
                    + ", ".join(sorted(privacy_blockers.intersection(warnings)))
                )
            quality_blockers = {
                "near_duplicate_spoken",
                "topic_loop_stall",
                "recurring_opening_reset",
            }
            if quality_blockers.intersection(warnings):
                raise RuntimeError(
                    "recurring dialogue novelty boundary failed after repair attempts: "
                    + ", ".join(sorted(quality_blockers.intersection(warnings)))
                )
            if warnings:
                warnings.append("repair_attempted")
            turn += 1
            item = {
                "turn": turn,
                "speaker": speaker,
                "spoken": parsed["spoken"],
                "private_mind": parsed["private_mind"],
                "truth_flags": parsed["truth_flags"],
                "warnings": warnings,
                "raw": raw,
                "at": utc_now(),
            }
            report["transcript"].append(item)
            last_message = f"{speaker} said: {parsed['spoken']}"
            add_observer_notes(report)
            write_report(report, json_path, md_path, monitor_path)
            if time.time() < deadline and (args.max_turns <= 0 or turn < args.max_turns):
                time.sleep(max(0.0, args.turn_delay_seconds))
        report["elapsed_minutes"] = round((time.time() - run_started) / 60.0, 3)
        report["completed_at"] = utc_now()
        if time.time() >= deadline:
            report["status"] = "complete"
            report["target_reached"] = True
            report["termination_reason"] = "duration_target_reached"
        else:
            report["status"] = "incomplete_target_not_reached"
            report["target_reached"] = False
            report["termination_reason"] = "max_turns_reached"
    except Exception as exc:
        report["status"] = "failed"
        report.setdefault("errors", []).append({"at": utc_now(), "error": str(exc)})
    finally:
        add_observer_notes(report)
        write_report(report, json_path, md_path, monitor_path)
        contamination_count = sum(
            contains_private_marker(str(item.get("spoken") or ""))
            for item in report.get("transcript") or []
            if isinstance(item, dict)
        )
        if report.get("transcript"):
            candidate_path = write_continuity_candidate(
                report,
                source_path=json_path,
                project_root=PROJECT_ROOT,
                contamination_count=contamination_count,
            )
            report["continuity_candidate"] = str(candidate_path.relative_to(PROJECT_ROOT))
            write_report(report, json_path, md_path, monitor_path)
    print(md_path)
    return 0 if report["status"] == "complete" and report.get("target_reached") else 1


if __name__ == "__main__":
    raise SystemExit(main())
