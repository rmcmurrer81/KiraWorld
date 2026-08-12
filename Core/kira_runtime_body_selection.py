"""Fail-closed, reversible runtime-body selection for Kira.

This resolver deliberately separates a private Avatar Builder review artifact
from the model that Home World is allowed to load.  A body-component pass is
not a full-avatar/runtime pass, and an adult-proportioned cage is not evidence
of anatomically complete adult topology.

The resolver never copies or edits a GLB.  Permanent promotion still requires
complete exact evidence and Kira's exact-candidate choice.  Schema v2 also
supports a narrower owner-requested *reversible live review trial*: the exact
candidate must have passed isolated browser compatibility checks, an exact
rollback manifest must be bound, and all remaining visual/anatomy limitations
must stay explicit.  A trial is not permanent acceptance or anatomy proof.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


DEFAULT_SELECTION_PATH = Path("Avatar/state/body_selections/kira_runtime_body_selection.json")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("json_root_not_object")
    return data


def _project_file(project_root: Path, raw: Any) -> Path | None:
    text = _text(raw)
    if not text:
        return None
    relative = Path(text)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    lexical = project_root
    for part in relative.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            return None
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _bound_file(
    project_root: Path,
    binding: Any,
    label: str,
    failures: list[str],
) -> tuple[Path | None, str]:
    if not isinstance(binding, Mapping):
        failures.append(f"{label}_binding_missing")
        return None, ""
    expected = _text(binding.get("sha256")).lower()
    if not SHA256_RE.fullmatch(expected):
        failures.append(f"{label}_sha256_invalid")
    path = _project_file(project_root, binding.get("path"))
    if path is None:
        failures.append(f"{label}_path_invalid")
        return None, expected
    actual = _sha256_file(path)
    if actual != expected:
        failures.append(f"{label}_sha256_mismatch")
    return path, actual


def _bound_json(
    project_root: Path,
    binding: Any,
    label: str,
    failures: list[str],
) -> tuple[dict[str, Any], str]:
    path, digest = _bound_file(project_root, binding, label, failures)
    if path is None:
        return {}, digest
    try:
        return _read_json(path), digest
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append(f"{label}_json_invalid")
        return {}, digest


def evaluate_kira_runtime_body_selection(
    project_root: Path,
    selection_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate one selection file without mutating any model or runtime state."""

    root = project_root.resolve(strict=True)
    source_path = selection_path or (root / DEFAULT_SELECTION_PATH)
    if not source_path.is_absolute():
        source_path = root / source_path
    selection = _read_json(source_path)
    failures: list[str] = []
    trial_blockers: list[str] = []
    permanent_blockers: list[str] = []

    schema_version = int(selection.get("schema_version") or 0)
    if schema_version not in {1, 2}:
        failures.append("selection_schema_version_invalid")
    if _text(selection.get("candidate_id")).lower() != "kira":
        failures.append("selection_candidate_not_kira")

    current = selection.get("current_runtime")
    review = selection.get("review_candidate")
    current_path, current_sha = _bound_file(root, current, "current_runtime", failures)
    review_path, review_sha = _bound_file(root, review, "review_candidate", failures)

    evidence = selection.get("evidence") if isinstance(selection.get("evidence"), Mapping) else {}
    manifest, _ = _bound_json(root, evidence.get("candidate_manifest"), "candidate_manifest", failures)
    verdict: dict[str, Any] = {}
    structural: dict[str, Any] = {}
    readiness: dict[str, Any] = {}
    browser_evidence: dict[str, Any] = {}
    rollback_manifest: dict[str, Any] = {}
    if schema_version == 1:
        verdict, _ = _bound_json(root, evidence.get("body_component_verdict"), "body_component_verdict", failures)
        structural, _ = _bound_json(root, evidence.get("structural_audit"), "structural_audit", failures)
        readiness, _ = _bound_json(root, evidence.get("adult_body_readiness"), "adult_body_readiness", failures)
    else:
        browser_evidence, _ = _bound_json(
            root,
            evidence.get("runtime_browser_evidence"),
            "runtime_browser_evidence",
            failures,
        )
        rollback_manifest, _ = _bound_json(
            root,
            evidence.get("rollback_manifest"),
            "rollback_manifest",
            failures,
        )

    manifest_candidate_sha = _text(
        (manifest.get("model") or {}).get("sha256") if isinstance(manifest.get("model"), Mapping) else ""
    ).lower()
    if review_sha and manifest_candidate_sha != review_sha:
        failures.append("candidate_manifest_candidate_sha256_mismatch")
    if schema_version == 1:
        verdict_candidate_sha = _text(verdict.get("candidate_sha256")).lower()
        structural_candidate_sha = _text(structural.get("sha256")).lower()
        if review_sha and verdict_candidate_sha != review_sha:
            failures.append("body_component_verdict_candidate_sha256_mismatch")
        if review_sha and structural_candidate_sha != review_sha:
            failures.append("structural_audit_candidate_sha256_mismatch")
    else:
        browser_candidate_sha = _text(browser_evidence.get("exact_candidate_sha256")).lower()
        if review_sha and browser_candidate_sha != review_sha:
            failures.append("runtime_browser_evidence_candidate_sha256_mismatch")
        rollback_live = (
            rollback_manifest.get("original_live_asset")
            if isinstance(rollback_manifest.get("original_live_asset"), Mapping)
            else {}
        )
        rollback_live_sha = _text(rollback_live.get("sha256")).lower()
        if current_sha and rollback_live_sha != current_sha:
            failures.append("rollback_manifest_current_runtime_sha256_mismatch")

    privacy_activation = (
        manifest.get("privacy_and_activation")
        if isinstance(manifest.get("privacy_and_activation"), Mapping)
        else {}
    )
    nonclaims = verdict.get("explicit_nonclaims") if isinstance(verdict.get("explicit_nonclaims"), Mapping) else {}
    compatibility = (
        selection.get("runtime_compatibility")
        if isinstance(selection.get("runtime_compatibility"), Mapping)
        else {}
    )
    choice = selection.get("subject_choice") if isinstance(selection.get("subject_choice"), Mapping) else {}

    # Permanent selection remains deliberately strict.  A passed provisional
    # body component or live-review trial cannot satisfy these gates by
    # implication.
    evidence_runtime_ready = bool(
        privacy_activation.get("runtime_activation_allowed") is True
        and privacy_activation.get("owner_approved") is True
        and privacy_activation.get("anatomy_approved") is True
        and structural.get("runtime_activation_allowed") is True
        and structural.get("stable_working_rig_proven") is True
        and structural.get("anatomical_completeness_proven") is True
        and nonclaims.get("full_avatar_passed") is True
        and nonclaims.get("runtime_activation_allowed") is True
    )
    if not evidence_runtime_ready:
        permanent_blockers.append("exact_evidence_does_not_approve_a_complete_runtime_avatar")

    required_compatibility = (
        "stable_runtime_locomotion_proven",
        "existing_mouth_lipsync_proven_without_new_mouth_mesh",
        "staged_eye_rig_fit_proven",
        "normal_clothed_presentation_ready",
    )
    missing_compatibility = [key for key in required_compatibility if compatibility.get(key) is not True]

    accepted_exact_candidate = bool(
        _text(choice.get("decision")).lower() == "accepted"
        and _text(choice.get("exact_candidate_sha256")).lower() == review_sha
        and review_sha
    )
    if not accepted_exact_candidate:
        permanent_blockers.append("kira_choice_not_recorded_for_exact_candidate")

    requested = _text(selection.get("requested_active_body")).lower()
    candidate_requested = requested in {"review_candidate", "candidate", "r5", "r6"}
    permanent_candidate_allowed = bool(
        not failures
        and candidate_requested
        and evidence_runtime_ready
        and not missing_compatibility
        and accepted_exact_candidate
    )

    trial = selection.get("trial_authorization") if isinstance(selection.get("trial_authorization"), Mapping) else {}
    essential_browser_checks = (
        "exact_r6_hash_loaded",
        "procedural_humanoid_rig_usable",
        "initial_bounds_finite",
        "walk_started_and_displaced",
        "walk_bounds_finite",
        "walk_ground_contact_not_failed",
        "sit_started_and_deformed",
        "gradual_turn_evidence",
        "front_door_reach_completed_without_failure",
        "eye_structural_complete_and_head_bound",
        "playback_boundary_deformed_and_restored_mouth",
        "no_second_mouth_created",
        "no_runtime_errors",
    )
    browser_checks = browser_evidence.get("checks") if isinstance(browser_evidence.get("checks"), Mapping) else {}
    missing_browser_checks = [key for key in essential_browser_checks if browser_checks.get(key) is not True]
    manifest_source = manifest.get("source") if isinstance(manifest.get("source"), Mapping) else {}
    manifest_rig = manifest.get("rig") if isinstance(manifest.get("rig"), Mapping) else {}
    manifest_absences = (
        manifest.get("explicit_absences")
        if isinstance(manifest.get("explicit_absences"), Mapping)
        else {}
    )
    trial_hash_bound = bool(
        review_sha
        and _text(trial.get("exact_candidate_sha256")).lower() == review_sha
        and _text(trial.get("mode")).lower() == "owner_requested_reversible_live_review"
    )
    trial_evidence_ready = bool(
        schema_version == 2
        and not failures
        and candidate_requested
        and trial.get("direct_user_request_recorded") is True
        and trial.get("rollback_required") is True
        and trial_hash_bound
        and browser_evidence.get("status") == "passed_inactive_technical_compatibility_only"
        and not missing_browser_checks
        and manifest.get("candidate_id") == "kira"
        and manifest.get("candidate_revision") == "provisional_body_r6"
        and _text(manifest_source.get("sha256")).lower() == current_sha
        and manifest_rig.get("bone_order_and_names_exactly_preserved") is True
        and manifest_rig.get("required_core_bones_present") is True
        and compatibility.get("exact_79_joint_names_preserved") is True
        and compatibility.get("isolated_runtime_browser_checks_passed") is True
        and compatibility.get("existing_mouth_lipsync_without_new_mouth_mesh") is True
        and compatibility.get("external_eye_rig_structural_attachment_passed") is True
        and compatibility.get("clothing_is_separate_not_baked") is True
        and bool(manifest_absences.get("clothes"))
    )
    if schema_version == 2 and candidate_requested and not trial_evidence_ready:
        trial_blockers.extend(f"trial_browser_check_not_proven:{key}" for key in missing_browser_checks)
        if not trial_hash_bound:
            trial_blockers.append("trial_authorization_not_bound_to_exact_candidate")
        trial_blockers.append("reversible_live_review_trial_evidence_incomplete")

    selection_mode = _text(selection.get("selection_mode")).lower()
    trial_selected = selection_mode == "reversible_owner_review_trial" and trial_evidence_ready
    candidate_runtime_allowed = permanent_candidate_allowed or trial_selected
    if not trial_selected and missing_compatibility:
        permanent_blockers.extend(f"runtime_compatibility_not_proven:{key}" for key in missing_compatibility)

    selected_path = review_path if candidate_runtime_allowed else current_path
    selected_sha = review_sha if candidate_runtime_allowed else current_sha
    claims = selection.get("claims") if isinstance(selection.get("claims"), Mapping) else {}
    full_adult_anatomy_proven = bool(
        claims.get("complete_adult_anatomy_proven") is True
        and structural.get("anatomical_completeness_proven") is True
        and privacy_activation.get("anatomy_approved") is True
    )

    return {
        "schema_version": schema_version,
        "candidate_id": "kira",
        "selection_valid": not failures,
        "selection_failures": list(dict.fromkeys(failures)),
        "requested_active_body": requested or "current_runtime",
        "candidate_runtime_allowed": candidate_runtime_allowed,
        "decision": (
            "reversible_r6_owner_review_trial_selected"
            if trial_selected
            else "review_candidate_selected"
            if permanent_candidate_allowed
            else "retain_current_runtime_body"
        ),
        "selected_model_path": str(selected_path) if selected_path else "",
        "selected_model_sha256": selected_sha,
        "current_runtime_model_unchanged": bool(selected_path == current_path),
        "original_live_asset_file_unchanged": bool(
            current_path and current_sha and _sha256_file(current_path) == current_sha
        ),
        "review_candidate_path": str(review_path) if review_path else "",
        "review_candidate_sha256": review_sha,
        "review_candidate_scope": _text(verdict.get("scope")),
        "provisional_body_component_passed": verdict.get("provisional_body_component_passed") is True,
        "full_adult_anatomy_proven": full_adult_anatomy_proven,
        "stable_working_rig_proven": structural.get("stable_working_rig_proven") is True,
        "kira_accepted_exact_candidate": accepted_exact_candidate,
        "reversible_owner_review_trial": trial_selected,
        "permanent_candidate_allowed": permanent_candidate_allowed,
        "technical_runtime_compatibility_passed": trial_evidence_ready,
        "eye_visual_fit_approved": compatibility.get("eye_visual_fit_approved") is True,
        "clothing_is_separate_not_baked": compatibility.get("clothing_is_separate_not_baked") is True,
        # Runtime blockers describe only the selected mode.  Permanent gates
        # remain visible separately so a successful reversible trial is not
        # mislabeled as blocked merely because it is not a permanent approval.
        "runtime_blockers": list(dict.fromkeys(trial_blockers if selection_mode == "reversible_owner_review_trial" else permanent_blockers)),
        "permanent_promotion_blockers": list(dict.fromkeys(permanent_blockers)),
        "readiness_contract_status": _text(readiness.get("status")),
        "truth_note": (
            "R6 is selected only as a reversible owner-review live trial of an adult external-form "
            "candidate. Clothing remains separate. Complete adult anatomy, final likeness, long-duration "
            "natural motion, and visually correct eye fit are not proven; permanent promotion is blocked."
            if trial_selected
            else "R5 may be described only as an adult-proportioned provisional body component. "
            "It is not proven complete adult anatomy and is not selected for Home World."
        ),
    }


def resolve_kira_runtime_body_path(
    project_root: Path,
    selection_path: Path | None = None,
) -> Path:
    """Return the only exact body this selection currently authorizes."""

    result = evaluate_kira_runtime_body_selection(project_root, selection_path)
    selected = Path(result["selected_model_path"])
    if not result["selection_valid"] or not selected.is_file():
        raise ValueError("kira_runtime_body_selection_invalid_fail_closed")
    return selected
