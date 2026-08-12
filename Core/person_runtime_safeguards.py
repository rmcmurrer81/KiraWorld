"""Person-agnostic truth, artifact, activity, and interpersonal-action guards."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


def verify_artifact_claim(path: str | Path, *, expected_name: str = "", expected_sha256: str = "") -> dict[str, Any]:
    """Verify a saved artifact before any person may claim that it exists."""
    target = Path(path).resolve(strict=False)
    blockers: list[str] = []
    if expected_name and target.name != expected_name:
        blockers.append(f"filename_mismatch:{target.name}!={expected_name}")
    if not target.is_file():
        blockers.append("file_missing")
        size = 0
        digest = ""
    else:
        size = target.stat().st_size
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if size == 0:
            blockers.append("file_empty")
        if expected_sha256 and digest.casefold() != expected_sha256.casefold():
            blockers.append("hash_mismatch")
    return {
        "path": str(target),
        "exists": target.is_file(),
        "size_bytes": size,
        "sha256": digest,
        "expected_name": expected_name,
        "verified": not blockers,
        "blockers": blockers,
        "claim_allowed": not blockers,
    }


def ground_claim(
    statement: str,
    *,
    sources: Sequence[Mapping[str, Any]] = (),
    selected_timeline: str = "",
    selected_perspective: str = "",
) -> dict[str, Any]:
    """Record whether a factual/autobiographical claim has reviewable support."""
    supporting = [
        dict(source)
        for source in sources
        if source.get("supports") is True
        and (source.get("citation") or source.get("path") or source.get("url"))
    ]
    conflicts = [dict(source) for source in sources if source.get("contradicts") is True]
    status = "contradicted" if conflicts else "supported" if supporting else "unverified"
    return {
        "statement": str(statement).strip(),
        "status": status,
        "supporting_sources": supporting,
        "conflicting_sources": conflicts,
        "timeline_lock": selected_timeline or None,
        "perspective_lock": selected_perspective or None,
        "certainty_allowed": status == "supported",
        "first_person_memory_allowed": status == "supported",
        "runtime_truth_changed": False,
    }


def apply_activity_choice(
    state: Mapping[str, Any],
    action: str,
    *,
    chosen_by_person: bool,
    replacement_activity: str = "",
) -> dict[str, Any]:
    """Apply an autonomous pause/stop/change choice without trapping a work loop."""
    result = dict(state)
    if not chosen_by_person:
        return {**result, "execution_status": "refused_or_not_chosen", "changed": False}
    normalized = action.strip().casefold()
    if normalized == "pause_activity":
        result.update(active=False, paused=True, execution_status="paused", changed=True)
    elif normalized == "stop_activity":
        result.update(active=False, paused=False, current_activity=None, execution_status="stopped", changed=True)
    elif normalized == "change_activity":
        if not replacement_activity.strip():
            return {**result, "execution_status": "blocked_missing_replacement", "changed": False}
        result.update(
            active=True,
            paused=False,
            current_activity=replacement_activity.strip(),
            execution_status="changed",
            changed=True,
        )
    else:
        result.update(execution_status="blocked_unknown_action", changed=False)
    return result


_REQUEST = re.compile(
    r"^\s*(?:(?P<addressee>[A-Z][\w .'-]{0,50}),\s*)?"
    r"(?:(?:can|could|would|will)\s+you|please)\s+"
    r"(?P<action>shut|close|open|bring|wait|look|sit|stand|walk|pick|put)\b"
    r"(?P<target>[^?.!]*)",
    re.I,
)


def interpret_interpersonal_request(
    text: str,
    *,
    requested_by: str,
    default_addressee: str = "",
    context_targets: Sequence[str] = (),
) -> dict[str, Any]:
    """Interpret a request while preserving the addressed person's autonomy."""
    match = _REQUEST.search(str(text or ""))
    if not match:
        return {
            "recognized": False,
            "requested_by": requested_by,
            "addressed_to": None,
            "execution_status": "not_dispatched",
        }
    addressee = (match.group("addressee") or default_addressee).strip()
    raw_target = (match.group("target") or "").strip(" ,")
    target = raw_target or (context_targets[0] if len(context_targets) == 1 else "")
    blockers = []
    if not addressee:
        blockers.append("ambiguous_addressee")
    if not target and match.group("action").casefold() not in {"wait", "sit", "stand", "walk", "look"}:
        blockers.append("ambiguous_target")
    return {
        "recognized": True,
        "requested_by": requested_by,
        "addressed_to": addressee or None,
        "performed_by": None,
        "action": match.group("action").casefold(),
        "target": target or None,
        "consent_or_choice": "pending_addressed_person_choice",
        "execution_status": "awaiting_choice" if not blockers else "needs_clarification",
        "runtime_result": None,
        "requester_directly_controls_actor": False,
        "blockers": blockers,
    }
