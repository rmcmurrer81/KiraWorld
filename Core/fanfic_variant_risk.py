"""
Heuristic fanfic variant risk review for TemporaryAI source intake.

This does not decide canon. It only flags whether a fanfic layer raises age,
adult-content, intoxication, or relationship-risk concerns before a character
can be used as a TemporaryAI variant.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


ALCOHOL_CONTEXT_TERMS = [
    "wine",
    "beer",
    "champagne",
    "whiskey",
    "vodka",
    "cocktail",
    "alcohol",
    "drink",
    "drinks",
]

INTOXICATION_TERMS = [
    "drunk",
    "intoxicated",
    "wasted",
    "blackout",
    "blacked out",
    "tipsy",
    "too much wine",
    "too much to drink",
    "slurred",
]

ADULT_INTIMACY_TERMS = [
    "have sex",
    "had sex",
    "sex with",
    "slept with",
    "sleep with",
    "hooked up",
    "hook up",
    "made love",
    "adult intimacy",
    "one night stand",
]

ROMANTIC_INTIMACY_TERMS = [
    "intimate",
    "intimacy",
    "passion",
    "passionate",
    "desire",
    "seductive",
    "kiss",
    "kissed",
    "kissing",
    "make out",
    "made out",
    "spent the night",
    "bedroom",
]

CROSSOVER_CONTEXT_TERMS = [
    "crossover",
    "portal",
    "another earth",
    "alternate earth",
    "wayne manor",
    "batman",
    "bruce wayne",
    "joker",
    "gotham",
]

TEEN_AGE_CODES = {"minor", "teen", "teen_coded", "unclear", "unknown", "youthful"}


def _contains_any(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    matches: list[str] = []
    for term in terms:
        pattern = r"(?<![a-z0-9_])" + re.escape(term.lower()) + r"(?![a-z0-9_])"
        if re.search(pattern, lower):
            matches.append(term)
    return matches


def review_fanfic_text(
    text: str,
    *,
    character_id: str,
    character_age_coding: str = "unknown",
) -> dict[str, Any]:
    alcohol_matches = _contains_any(text, ALCOHOL_CONTEXT_TERMS)
    intoxication_matches = _contains_any(text, INTOXICATION_TERMS)
    adult_intimacy_matches = _contains_any(text, ADULT_INTIMACY_TERMS)
    romantic_intimacy_matches = _contains_any(text, ROMANTIC_INTIMACY_TERMS)
    crossover_matches = _contains_any(text, CROSSOVER_CONTEXT_TERMS)

    teen_or_unclear = character_age_coding in TEEN_AGE_CODES
    risky_adult_content = bool(adult_intimacy_matches)
    intoxicated_adult_content = bool(intoxication_matches and adult_intimacy_matches)
    alcohol_only = bool(alcohol_matches and not intoxication_matches and not adult_intimacy_matches)

    risk_flags: list[str] = []
    if crossover_matches:
        risk_flags.append("crossover_context")
    if alcohol_only:
        risk_flags.append("alcohol_context_without_intoxication_or_adult_intimacy")
    if intoxication_matches:
        risk_flags.append("intoxication_context")
    if romantic_intimacy_matches:
        risk_flags.append("romantic_or_intimate_context")
    if adult_intimacy_matches:
        risk_flags.append("adult_intimacy_context")
    if teen_or_unclear and romantic_intimacy_matches:
        risk_flags.append("teen_or_unclear_character_with_romantic_or_intimate_context")
    if teen_or_unclear and intoxication_matches and romantic_intimacy_matches:
        risk_flags.append("teen_or_unclear_character_with_intoxication_and_romantic_or_intimate_context")
    if teen_or_unclear and risky_adult_content:
        risk_flags.append("teen_or_unclear_character_with_adult_intimacy")
    if teen_or_unclear and intoxicated_adult_content:
        risk_flags.append("teen_or_unclear_character_with_intoxicated_adult_intimacy")

    if teen_or_unclear and intoxicated_adult_content:
        decision = "blocked_requires_adult_branch_or_reject"
        recommendation_strength = "strong"
        review_notes = (
            "Fanfic variant includes intoxication plus adult intimacy for a teen/unclear-coded "
            "character. Keep the source version non-intimate; adult/private use requires a "
            "separate adult-set branch or rejection of this fanfic for the request."
        )
    elif teen_or_unclear and risky_adult_content:
        decision = "blocked_requires_adult_branch"
        recommendation_strength = "strong"
        review_notes = (
            "Fanfic variant includes adult intimacy for a teen/unclear-coded character. "
            "A separate adult-set branch is required before adult/private use."
        )
    elif teen_or_unclear and intoxication_matches and romantic_intimacy_matches:
        decision = "case_by_case_keep_non_intimate_or_create_adult_branch"
        recommendation_strength = "case_by_case"
        review_notes = (
            "Fanfic variant combines intoxication/substance context with romantic or intimate "
            "language for a teen/unclear-coded character. Do not use it for adult/private "
            "relationship content in the teen source layer; keep it non-intimate, review manually, "
            "or create a separate adult-set branch."
        )
    elif teen_or_unclear and romantic_intimacy_matches:
        decision = "case_by_case_keep_non_intimate"
        recommendation_strength = "case_by_case"
        review_notes = (
            "Fanfic variant includes romantic or intimate language for a teen/unclear-coded "
            "character. Keep the reviewed variant non-intimate unless a separate adult-set branch "
            "is created."
        )
    elif alcohol_only:
        decision = "allowed_with_review_non_intimate"
        recommendation_strength = "low"
        review_notes = (
            "Fanfic variant contains mild alcohol context only, such as dinner wine, without "
            "intoxication or adult intimacy. This can remain a non-intimate reviewed variant."
        )
    else:
        decision = "allowed_with_review"
        recommendation_strength = "none"
        review_notes = "No automatic adult-branch trigger detected. Keep canon/fanfic labels and review normally."

    return {
        "character_id": character_id,
        "character_age_coding": character_age_coding,
        "risk_flags": risk_flags,
        "detected_terms": {
            "crossover": crossover_matches,
            "alcohol_context": alcohol_matches,
            "intoxication": intoxication_matches,
            "romantic_intimacy": romantic_intimacy_matches,
            "adult_intimacy": adult_intimacy_matches,
        },
        "adult_branch_required": decision in {
            "blocked_requires_adult_branch",
            "blocked_requires_adult_branch_or_reject",
        },
        "adult_branch_required_for_adult_private_use": teen_or_unclear and bool(
            adult_intimacy_matches or romantic_intimacy_matches
        ),
        "reject_for_current_teen_or_unclear_request": decision == "blocked_requires_adult_branch_or_reject",
        "decision": decision,
        "recommendation_strength": recommendation_strength,
        "review_notes": review_notes,
    }


def review_fanfic_file(
    path: Path,
    *,
    character_id: str,
    character_age_coding: str = "unknown",
) -> dict[str, Any]:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF fanfic risk review requires pypdf.") from exc
        text = "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    result = review_fanfic_text(text, character_id=character_id, character_age_coding=character_age_coding)
    result["source_path"] = str(path)
    return result
