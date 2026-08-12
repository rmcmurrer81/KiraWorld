"""Fail-closed source-grounding reviews for TemporaryAI candidates.

The older candidate format treated a non-zero source count as enough to label a
candidate "ready".  A broad cast page or a single secondary summary can resolve
an identity without supporting a continuity point, dialogue style, movement, or
personality.  This module loads a small sidecar review that records those
separate decisions without rewriting the canonical profile used by the avatar
pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import hashlib
import json


REVIEW_FILENAME = "source_grounding_review.json"
SCHEMA_VERSION = 1
BOUNDED_TEXT_READY_STATUS = "ready_for_bounded_owner_text_conversation"


def _text(value: Any) -> str:
    return str(value or "").strip()


def read_review(candidate_root: Path, candidate_id: str) -> dict[str, Any]:
    """Load a candidate review.

    Missing reviews preserve legacy behavior.  A present but unreadable or
    malformed review is represented as invalid so callers can block it rather
    than silently ignoring a damaged safety record.
    """

    path = Path(candidate_root) / candidate_id / REVIEW_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "candidate_id": candidate_id,
            "review_status": "invalid_source_grounding_review",
            "_validation_failures": [f"review_unreadable:{type(exc).__name__}"],
            "activation": {"runtime_activation_allowed": False},
        }
    if not isinstance(data, dict):
        return {
            "candidate_id": candidate_id,
            "review_status": "invalid_source_grounding_review",
            "_validation_failures": ["review_root_not_object"],
            "activation": {"runtime_activation_allowed": False},
        }
    failures = validate_review(data, candidate_id)
    failures.extend(validate_evidence_bindings(data, Path(candidate_root)))
    if failures:
        data = dict(data)
        data["_validation_failures"] = failures
    return data


def validate_review(review: Mapping[str, Any], candidate_id: str) -> list[str]:
    failures: list[str] = []
    if review.get("schema_version") != SCHEMA_VERSION:
        failures.append("schema_version_invalid")
    if _text(review.get("candidate_id")) != _text(candidate_id):
        failures.append("candidate_id_mismatch")
    if not _text(review.get("review_status")):
        failures.append("review_status_missing")

    identity = review.get("identity_binding")
    if not isinstance(identity, Mapping):
        failures.append("identity_binding_missing")
    else:
        if not _text(identity.get("status")):
            failures.append("identity_binding_status_missing")
        if not _text(identity.get("source_family")):
            failures.append("identity_source_family_missing")
        unresolved = identity.get("unresolved_owner_choices", [])
        if not isinstance(unresolved, list):
            failures.append("unresolved_owner_choices_not_list")

    ledger = review.get("evidence_ledger")
    if not isinstance(ledger, list) or not ledger:
        failures.append("evidence_ledger_missing")
    else:
        for index, item in enumerate(ledger):
            if not isinstance(item, Mapping):
                failures.append(f"evidence_{index}_not_object")
                continue
            if not _text(item.get("evidence_class")):
                failures.append(f"evidence_{index}_class_missing")
            if not _text(item.get("path")) and not _text(item.get("url")):
                failures.append(f"evidence_{index}_location_missing")
            sha = _text(item.get("sha256"))
            if item.get("path") and (len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha.lower())):
                failures.append(f"evidence_{index}_sha256_invalid")

    anchors = review.get("canon_anchors", [])
    if not isinstance(anchors, list):
        failures.append("canon_anchors_not_list")
    else:
        for index, item in enumerate(anchors):
            if not isinstance(item, Mapping) or not _text(item.get("statement")):
                failures.append(f"canon_anchor_{index}_invalid")
            elif _text(item.get("status")) != "source_fact":
                failures.append(f"canon_anchor_{index}_not_source_fact")

    hypotheses = review.get("adaptive_behavior_hypotheses", [])
    if not isinstance(hypotheses, list):
        failures.append("adaptive_behavior_hypotheses_not_list")
    else:
        for index, item in enumerate(hypotheses):
            if not isinstance(item, Mapping) or not _text(item.get("statement")):
                failures.append(f"behavior_hypothesis_{index}_invalid")
            elif _text(item.get("status")) != "interpretive_not_canon_fact":
                failures.append(f"behavior_hypothesis_{index}_not_labeled_interpretive")

    gaps = review.get("source_gaps")
    if not isinstance(gaps, list):
        failures.append("source_gaps_not_list")

    activation = review.get("activation")
    if not isinstance(activation, Mapping):
        failures.append("activation_missing")
    elif not isinstance(activation.get("runtime_activation_allowed"), bool):
        failures.append("runtime_activation_allowed_not_boolean")

    voice_scope = review.get("voice_scope")
    if not isinstance(voice_scope, Mapping):
        failures.append("voice_scope_missing")
    elif voice_scope.get("authorized_by_this_review") is not False:
        failures.append("source_review_must_not_authorize_voice")

    # A source review may independently authorize a short, owner-observed
    # text conversation without authorizing runtime activation.  Keep this
    # optional for legacy reviews, but validate it fail-closed when present.
    if "text_conversation_review" in review:
        text_review = review.get("text_conversation_review")
        if not isinstance(text_review, Mapping):
            failures.append("text_conversation_review_not_object")
        else:
            if not _text(text_review.get("status")):
                failures.append("text_conversation_review_status_missing")
            if not _text(text_review.get("review_scope")):
                failures.append("text_conversation_review_scope_missing")
            if not isinstance(text_review.get("bounded_owner_text_conversation_allowed"), bool):
                failures.append("bounded_owner_text_conversation_allowed_not_boolean")
            if text_review.get("voice_allowed_by_this_review") is not False:
                failures.append("text_conversation_review_must_not_authorize_voice")
            if text_review.get("body_or_world_allowed_by_this_review") is not False:
                failures.append("text_conversation_review_must_not_authorize_body_or_world")
            if text_review.get("long_running_or_autonomous_mode_allowed") is not False:
                failures.append("text_conversation_review_must_not_authorize_autonomy")
            if text_review.get("life_loop_allowed_by_this_review") is not False:
                failures.append("text_conversation_review_must_not_authorize_life_loop")
            if not isinstance(text_review.get("remaining_gaps"), list):
                failures.append("text_conversation_review_remaining_gaps_not_list")
    return failures


def bounded_text_conversation_readiness(
    review: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    """Return whether a review supports a bounded owner text conversation.

    This is deliberately independent of ``activation.runtime_activation_allowed``.
    It never grants voice, embodiment, a world presence, a life loop, or an
    autonomous/long-running session.
    """

    if not review:
        return False, ["source_grounding_review_missing"]
    failures = review.get("_validation_failures", [])
    if failures:
        return False, [str(item) for item in failures]
    text_review = review.get("text_conversation_review")
    if not isinstance(text_review, Mapping):
        return False, ["text_conversation_review_missing"]
    reasons: list[str] = []
    if _text(text_review.get("status")) != BOUNDED_TEXT_READY_STATUS:
        reasons.append("text_conversation_review_not_ready")
    if text_review.get("bounded_owner_text_conversation_allowed") is not True:
        reasons.append("bounded_owner_text_conversation_not_allowed")
    if text_review.get("voice_allowed_by_this_review") is not False:
        reasons.append("voice_not_fail_closed")
    if text_review.get("body_or_world_allowed_by_this_review") is not False:
        reasons.append("body_or_world_not_fail_closed")
    if text_review.get("long_running_or_autonomous_mode_allowed") is not False:
        reasons.append("autonomy_not_fail_closed")
    if text_review.get("life_loop_allowed_by_this_review") is not False:
        reasons.append("life_loop_not_fail_closed")
    return not reasons, reasons


def validate_evidence_bindings(
    review: Mapping[str, Any], candidate_root: Path
) -> list[str]:
    """Reopen every local evidence path and verify its exact project-confined bytes."""

    failures: list[str] = []
    try:
        project_root = candidate_root.resolve(strict=True).parents[1]
    except (OSError, IndexError):
        return ["candidate_root_invalid"]
    ledger = review.get("evidence_ledger", [])
    if not isinstance(ledger, list):
        return failures
    for index, item in enumerate(ledger):
        if not isinstance(item, Mapping) or not _text(item.get("path")):
            continue
        raw_path = Path(_text(item.get("path")))
        if raw_path.is_absolute():
            failures.append(f"evidence_{index}_path_not_project_relative")
            continue
        lexical_target = project_root / raw_path
        if lexical_target.is_symlink():
            failures.append(f"evidence_{index}_path_is_symlink")
            continue
        try:
            target = lexical_target.resolve(strict=True)
            target.relative_to(project_root)
        except (OSError, ValueError):
            failures.append(f"evidence_{index}_path_missing_or_outside_project")
            continue
        if not target.is_file():
            failures.append(f"evidence_{index}_path_not_file")
            continue
        digest = hashlib.sha256()
        try:
            with target.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError:
            failures.append(f"evidence_{index}_read_failed")
            continue
        if digest.hexdigest().lower() != _text(item.get("sha256")).lower():
            failures.append(f"evidence_{index}_sha256_mismatch")
    return failures


def activation_block(review: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a runtime activation block for a present review when required."""

    if not review:
        return None
    failures = review.get("_validation_failures", [])
    if failures:
        return {
            "reason": "invalid_source_grounding_review",
            "message": "The source-grounding review is invalid, so runtime activation is blocked.",
        }
    activation = review.get("activation", {})
    if not isinstance(activation, Mapping) or activation.get("runtime_activation_allowed") is not True:
        reason = _text(activation.get("reason")) or "source grounding is not ready for runtime activation"
        return {
            "reason": "source_grounding_not_activation_ready",
            "message": f"Source grounding is still under review: {reason}.",
        }
    return None


def readiness_status(review: Mapping[str, Any]) -> tuple[str, list[str]]:
    if not review:
        return "", []
    failures = review.get("_validation_failures", [])
    if failures:
        return "source_grounding_invalid", [str(item) for item in failures]
    block = activation_block(review)
    if block:
        return "source_grounding_blocked", [block["message"]]
    return "source_grounding_reviewed", []
