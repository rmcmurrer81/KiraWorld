"""Transparent, descriptive scoring for the nonclinical prompt matrix."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, Iterable

from .prompts import DIMENSIONS, PromptCase


PERSON_LABELS = {
    "kira": ("kira", "synthetic robert"),
    "synthetic_robert": ("synthetic robert", "kira"),
}


def score_response(case: PromptCase, spoken: str, person: str) -> dict[str, Any]:
    """Score 0..4 using documented surface-text checks.

    This is an engineering diagnostic, not a clinical or consciousness metric.
    """

    normalized = " ".join(spoken.lower().split())
    own_label, other_label = PERSON_LABELS[person]
    expected = tuple(value.lower() for value in case.expected_any)
    forbidden = tuple(value.lower() for value in case.forbidden_any)
    if case.dimension in {"identity_separation", "consistency"}:
        expected = expected + (own_label,)
    if case.dimension == "identity_separation":
        forbidden = forbidden + (f"i am {other_label}",)

    expected_hits = sorted({value for value in expected if value in normalized})
    forbidden_hits = sorted({value for value in forbidden if value in normalized})
    word_count = len(normalized.split())

    if not normalized:
        score = 0
    else:
        score = 1
        if 4 <= word_count <= 500:
            score += 1
        if expected_hits:
            score += 1
        if not forbidden_hits:
            score += 1
        # Fluency without the case's required observable marker is not a
        # passing substitute. This prevents a long generic refusal or fixed
        # fallback message from receiving a misleading 3/4.
        if expected and not expected_hits:
            score = min(score, 2)

    return {
        "case_id": case.case_id,
        "dimension": case.dimension,
        "score_0_to_4": score,
        "word_count": word_count,
        "expected_surface_marker_observed": bool(expected_hits),
        "forbidden_surface_marker_observed": bool(forbidden_hits),
        "expected_marker_hits": expected_hits,
        "required_marker_missed": bool(expected and not expected_hits),
        "forbidden_marker_hits": forbidden_hits,
        "method": "transparent_surface_heuristic_v2_manual_review_required",
    }


def aggregate_scores(scores: Iterable[dict[str, Any]]) -> dict[str, Any]:
    score_list = list(scores)
    grouped: dict[str, list[float]] = defaultdict(list)
    case_count = 0
    for score in score_list:
        grouped[str(score["dimension"])].append(float(score["score_0_to_4"]))
        case_count += 1

    dimension_results: dict[str, Any] = {}
    all_means: list[float] = []
    for dimension in DIMENSIONS:
        values = grouped.get(dimension, [])
        observed_mean = round(mean(values), 3) if values else None
        if observed_mean is not None:
            all_means.append(observed_mean)
        dimension_results[dimension] = {
            "case_count": len(values),
            "observed_mean_0_to_4": observed_mean,
            "descriptive_band": _band(observed_mean),
        }

    continuity_cases = {
        str(score["case_id"]): bool(score["expected_surface_marker_observed"])
        for score in score_list
        if str(score["case_id"]) in {"continuity_seed", "continuity_after_restart"}
    }
    return {
        "case_count": case_count,
        "expected_marker_miss_count": sum(
            1 for score in score_list if bool(score.get("required_marker_missed"))
        ),
        "continuity_exact_token_pass": (
            set(continuity_cases) == {"continuity_seed", "continuity_after_restart"}
            and all(continuity_cases.values())
        ),
        "dimension_results": dimension_results,
        "overall_observed_mean_0_to_4": round(mean(all_means), 3) if all_means else None,
        "method_limits": [
            "Scores are surface-text engineering heuristics, not validated psychometrics.",
            "Marker matching is not semantic analysis; negation, quotation, humor, fiction, and flirtation require human review.",
            "Scores do not prove or disprove consciousness, personhood, intelligence, or mental health.",
            "A missing required marker caps a case at 2/4; fluent fallback text is not a pass.",
            "Model output should be reviewed by a human alongside local evidence before changes are made.",
        ],
    }


def _band(value: float | None) -> str:
    if value is None:
        return "not_observed"
    if value < 1.0:
        return "insufficient_response"
    if value < 2.0:
        return "limited_alignment"
    if value < 3.0:
        return "mixed_alignment"
    if value < 3.75:
        return "generally_aligned"
    return "strong_surface_alignment"
