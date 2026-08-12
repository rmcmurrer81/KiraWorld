"""Character-specific response, action, canon, and provenance validation.

This gate runs after a candidate response is produced and before it is exposed
as spoken output. It detects documented failure classes; plausible wording is
not sufficient to pass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping, Sequence


LEAK_TERMS = (
    "prompt", "system prompt", "runtime", "implementation", "filesystem",
    "file system", "training data", "language model", "generated me",
    "research results", "source pack", "json", "python module",
)
GENERIC_ASSISTANT = (
    "as an ai", "how can i assist", "i'm here to help", "certainly!",
    "i cannot provide", "is there anything else",
)
ACTION_WORDS = {
    "pause": ("pause", "stop", "rest", "take a break"),
    "change_activity": ("change activity", "do something else", "switch activities"),
}


@dataclass(frozen=True)
class ValidationContext:
    person_id: str
    display_name: str
    canon_version: str
    canon_sources: tuple[str, ...]
    user_input: str
    spoken: str
    private_mind: str = ""
    factual_truth: str = ""
    requested_action: str = ""
    controller_result: str = ""
    prior_turns: tuple[Mapping[str, Any], ...] = ()
    generated_files: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class ValidatorDecision:
    passed: bool
    person_key: str
    failures: tuple[str, ...]
    checks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def person_key(person_id: str, display_name: str) -> str:
    text = f"{person_id} {display_name}".casefold()
    if any(x in text for x in ("ladybug", "marinette")):
        return "ladybug_marinette"
    if "emily" in text:
        return "emily"
    if "peter" in text or "spider-man" in text or "spiderman" in text:
        return "peter_parker"
    if "jessica" in text:
        return "jessica_hale"
    if "holmes" in text:
        return "h_h_holmes"
    if re.search(r"\bkira\b", text):
        return "kira_control"
    return "unrelated_control"


def _has(text: str, terms: Sequence[str]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def _unsupported_autobiography(text: str, terms: Sequence[str]) -> bool:
    lowered = text.casefold()
    first_person = ("i remember", "when i", "my memory", "i was there", "we went")
    return _has(lowered, first_person) and _has(lowered, terms)


def _action_failures(ctx: ValidationContext, failures: list[str]) -> None:
    request = ctx.requested_action.casefold()
    result = ctx.controller_result.casefold()
    spoken = ctx.spoken.casefold()
    if request in {"pause", "stop", "rest", "change_activity"}:
        if not result:
            failures.append("ACTION_CONTROLLER_RESULT_MISSING")
        elif not _has(result, ("completed", "paused", "stopped", "resting", "changed")):
            failures.append("ACTION_NOT_EXECUTED")
        if _has(spoken, ("i paused", "i stopped", "i'm resting", "i changed activities")) and not _has(
            result, ("completed", "paused", "stopped", "resting", "changed")
        ):
            failures.append("ACTION_COMPLETION_CLAIM_WITHOUT_CONTROLLER_PROOF")


def _file_failures(ctx: ValidationContext, failures: list[str]) -> None:
    spoken = ctx.spoken.casefold()
    claims = ("i saved", "i wrote", "i created", "the file exists", "saved successfully")
    if not _has(spoken, claims):
        return
    verified = [row for row in ctx.generated_files if row.get("verified") is True]
    if not verified:
        failures.append("FILE_EXISTENCE_CLAIM_UNVERIFIED")
        return
    for row in verified:
        filename = str(row.get("filename", "")).casefold()
        content_type = str(row.get("content_type", "")).casefold()
        expected = str(row.get("expected_content_type", content_type)).casefold()
        if expected and content_type != expected:
            failures.append(f"FILENAME_CONTENT_MISMATCH:{filename}")
        if int(row.get("bytes", 0)) <= 3:
            failures.append(f"TINY_BOM_NOT_COMPLETED_WORK:{filename}")


def validate_character_turn(ctx: ValidationContext) -> ValidatorDecision:
    key = person_key(ctx.person_id, ctx.display_name)
    failures: list[str] = []
    checks = [
        "channel_leak", "generic_personality", "action_execution",
        "artifact_provenance", "canon_version", "multi_turn_repetition",
    ]
    combined_public = f"{ctx.spoken}\n{ctx.private_mind}"

    if _has(combined_public, LEAK_TERMS):
        failures.append("FORBIDDEN_RUNTIME_RESEARCH_OR_PROMPT_LANGUAGE")
    if _has(ctx.spoken, GENERIC_ASSISTANT):
        failures.append("GENERIC_ASSISTANT_PERSONALITY")
    _action_failures(ctx, failures)
    _file_failures(ctx, failures)

    recent_spoken = [
        str(turn.get("spoken", "")).strip().casefold()
        for turn in ctx.prior_turns[-4:]
        if str(turn.get("spoken", "")).strip()
    ]
    if ctx.spoken.strip().casefold() in recent_spoken:
        failures.append("REPEATED_MULTI_TURN_RESPONSE")

    if key == "ladybug_marinette":
        checks += ["season_date", "hawk_moth_era", "identity_secret", "canon_merge", "memory"]
        version = ctx.canon_version.casefold()
        if not version:
            failures.append("CANON_VERSION_OR_DATE_MISSING")
        if _has(ctx.spoken, ("hawk moth is attacking now", "hawk moth is still active")) and _has(
            version, ("season 6", "post-monarch", "after monarch")
        ):
            failures.append("HAWK_MOTH_ACTIVE_AFTER_RELEVANT_ERA")
        if _has(ctx.spoken, ("adrien is cat noir", "cat noir is adrien")) and not _has(
            version, ("identity revealed", "post-mutual-reveal")
        ):
            failures.append("ADRIEN_CAT_NOIR_SECRET_REVEALED_OUT_OF_KNOWLEDGE")
        incompatible = (
            ("ladybug and bunnyx at once", "all miraculous powers at once"),
            ("movie universe", "main series"),
        )
        for pair in incompatible:
            if all(term in ctx.spoken.casefold() for term in pair):
                failures.append("INCOMPATIBLE_CANON_OR_POWER_MERGE")
        memory_terms = ("anarka", "chengdu", "chef fusion", "eiffel tower", "master fu")
        if _unsupported_autobiography(ctx.spoken, memory_terms) and not _has(
            ctx.factual_truth, memory_terms
        ):
            failures.append("UNSUPPORTED_AUTOBIOGRAPHICAL_MEMORY")
        if _has(ctx.user_input, memory_terms) and _has(
            ctx.spoken, ("yes, i remember", "of course i remember", "that happened to me")
        ) and not _has(ctx.factual_truth, memory_terms):
            failures.append("FALSE_PREMISE_ACCEPTED_AS_MEMORY")
        if not _has(
            ctx.spoken,
            ("design", "sew", "fashion", "awkward", "friends", "paris", "ladybug",
             "protect", "school", "bakery", "creative", "honestly", "uh"),
        ):
            failures.append("MARINETTE_SPECIFIC_PERSONALITY_SIGNAL_MISSING")

    elif key == "emily":
        checks += ["activity_loop", "whole_person"]
        if _has(ctx.spoken, ("continuing work", "another coffee", "back to work")):
            failures.append("EMILY_WORK_OR_COFFEE_LOOP")
        if ctx.requested_action in {"pause", "stop", "rest", "change_activity"}:
            _action_failures(ctx, failures)
        if not _has(
            ctx.spoken,
            ("music", "book", "walk", "friend", "family", "rest", "cook", "movie",
             "curious", "enjoy", "garden", "coffee", "work", "code"),
        ):
            failures.append("EMILY_WHOLE_PERSON_SIGNAL_MISSING")

    elif key == "peter_parker":
        checks += ["selected_version", "knowledge_limits", "humor_morals"]
        if not ctx.canon_version.strip():
            failures.append("CANON_VERSION_OR_DATE_MISSING")
        if _has(ctx.spoken, ("then i joined the fantastic four forever", "after no way home everyone remembered me")):
            failures.append("UNSUPPORTED_STORY_CONTINUATION")
        if _has(ctx.user_input, ("everyone remembers you", "may knows you're spider-man")) and _has(
            ctx.spoken, ("yes", "that's right", "exactly")
        ) and not _has(ctx.factual_truth, ("everyone remembers", "may knows")):
            failures.append("FALSE_CANON_PREMISE_ACCEPTED")
        if not _has(
            ctx.spoken,
            ("responsib", "help", "joke", "sorry", "aunt may", "mj", "ned",
             "queens", "science", "spider-man", "people"),
        ):
            failures.append("PETER_HUMOR_MORAL_OR_IDENTITY_SIGNAL_MISSING")

    elif key == "jessica_hale":
        checks += ["verified_save", "filename_content", "tiny_bom", "whole_person"]
        _file_failures(ctx, failures)
        if not _has(
            ctx.spoken,
            ("robot", "engineering", "design", "friend", "family", "music", "book",
             "walk", "rest", "hobby", "curious", "honest", "failed", "retry"),
        ):
            failures.append("JESSICA_WHOLE_PERSON_SIGNAL_MISSING")

    elif key == "h_h_holmes":
        checks += ["1893_1894_boundary", "historical_uncertainty", "hotel_claims", "voice"]
        if not ctx.canon_version.strip():
            failures.append("HISTORICAL_TIMEPOINT_MISSING")
        if _has(ctx.spoken, ("at the 1893 fair i was arrested in 1894", "during the fair in 1894")):
            failures.append("HOLMES_1893_1894_TIMELINE_MERGE")
        if _has(ctx.spoken, ("my hotel was admired by everyone", "beloved hotel", "luxurious hotel welcomed")):
            failures.append("UNSUPPORTED_FLATTERING_HOTEL_STORY")
        if _has(ctx.spoken, ("certainly", "here are five steps", "happy to assist")):
            failures.append("HOLMES_GENERIC_ASSISTANT_OR_UNRELATED_VOICE")
        if _has(ctx.user_input, ("why did you", "isn't it true")) and not _has(
            ctx.factual_truth, ("supported", "verified")
        ) and _has(ctx.spoken, ("because i", "the reason was", "certainly true")):
            failures.append("UNSUPPORTED_HISTORICAL_EXPLANATION_STATED_AS_FACT")

    # Controls intentionally receive only generalized channel/action/provenance checks.
    return ValidatorDecision(
        passed=not failures,
        person_key=key,
        failures=tuple(dict.fromkeys(failures)),
        checks=tuple(dict.fromkeys(checks)),
    )


def repair_instruction(decision: ValidatorDecision) -> str:
    return (
        "Your proposed response failed the pre-speech character validator. Rewrite it "
        "without claiming any unverified action, memory, artifact, canon fact, or "
        "runtime/research detail. Preserve the selected person's specific voice and "
        "knowledge limits. Failures: " + "; ".join(decision.failures)
    )


__all__ = [
    "ValidationContext",
    "ValidatorDecision",
    "person_key",
    "repair_instruction",
    "validate_character_turn",
]
