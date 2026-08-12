"""Fail-closed body eligibility shared by the existing Kira World selector."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from Core.avatar_static_anatomy_quality import REQUIRED_VIEWS


BAD_STATUS_WORDS = (
    "rejected",
    "frozen",
    "placeholder",
    "review-blocked",
    "incomplete",
    "partial",
    "awaiting robert static likeness review",
)
APPROVED_RUNTIME_STATUSES = {
    "approved for manual runtime activation",
    "owner approved for runtime",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normal_status(value: object) -> str:
    return " ".join(
        str(value or "")
        .replace("_", " ")
        .replace("-", " ")
        .casefold()
        .split()
    )


def _resolve_review_file(root: Path, manifest_path: Path, value: object) -> Path | None:
    path_value = str(value or "").strip()
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    try:
        path = path.resolve(strict=True)
        path.relative_to(root)
    except (FileNotFoundError, ValueError):
        return None
    if not path.is_file():
        return None
    return path


def _validate_hash_bound_rendered_evidence(
    root: Path,
    manifest_path: Path,
    review: dict,
    body_sha256: str,
) -> list[str]:
    """Verify actual rendered files and bind every view to the body artifact.

    Self-written ``rendered_visual_review_passed`` booleans are not evidence.
    Runtime eligibility requires the review manifest to name the files Robert
    saw, their hashes, and the exact body hash from which they were rendered.
    """

    reasons: list[str] = []
    evidence = review.get("rendered_visual_evidence")
    if not isinstance(evidence, dict):
        return ["rendered_visual_evidence_missing"]

    candidate_hash = str(
        evidence.get("candidate_sha256")
        or evidence.get("candidate_body_sha256")
        or ""
    ).strip().lower()
    if candidate_hash != body_sha256:
        reasons.append("rendered_visual_evidence_body_hash_mismatch")

    decision = str(evidence.get("review_decision") or "").strip().upper()
    if decision != "APPROVED_BY_OWNER":
        reasons.append("rendered_visual_review_not_owner_approved")
    rejection_reasons = evidence.get("rejection_reasons")
    if not isinstance(rejection_reasons, list):
        reasons.append("rendered_visual_rejection_record_invalid")
    elif any(str(reason).strip() for reason in rejection_reasons):
        reasons.append("rendered_visual_rejection_recorded")
    if evidence.get("pelvis_open_or_spatial_gap_detected") is not False:
        reasons.append("pelvis_open_or_spatial_gap_not_cleared")
    if str(evidence.get("pelvis_attachment_status") or "").strip().upper() != (
        "ACCEPTED_BY_OWNER"
    ):
        reasons.append("pelvis_attachment_visual_acceptance_missing")

    views = evidence.get("views")
    if not isinstance(views, dict):
        return reasons + ["rendered_visual_view_records_missing"]
    missing_views = sorted(REQUIRED_VIEWS.difference(views))
    if missing_views:
        reasons.append("rendered_visual_required_views_missing")

    verified_hashes: list[str] = []
    for view in sorted(REQUIRED_VIEWS.intersection(views)):
        record = views.get(view)
        if not isinstance(record, dict):
            reasons.append(f"rendered_visual_view_record_invalid:{view}")
            continue
        if (
            str(
                record.get("candidate_sha256")
                or record.get("candidate_body_sha256")
                or ""
            ).strip().lower()
            != body_sha256
        ):
            reasons.append(f"rendered_visual_view_body_hash_mismatch:{view}")
        rendered_path = _resolve_review_file(
            root, manifest_path, record.get("path")
        )
        if rendered_path is None:
            reasons.append(f"rendered_visual_view_path_invalid:{view}")
            continue
        expected_hash = str(record.get("sha256") or "").strip().lower()
        actual_hash = _sha256(rendered_path).lower()
        if not expected_hash or expected_hash != actual_hash:
            reasons.append(f"rendered_visual_view_hash_mismatch:{view}")
            continue
        verified_hashes.append(actual_hash)
    if (
        len(verified_hashes) == len(REQUIRED_VIEWS)
        and len(set(verified_hashes)) != len(REQUIRED_VIEWS)
    ):
        reasons.append("rendered_visual_views_not_distinct")
    return reasons


def evaluate_body_runtime_eligibility(root: str | Path, person_record: dict) -> dict:
    """Validate a person's assigned body without trusting self-written booleans.

    New embodied people must name a hash-bound approval manifest.  A body file,
    ``has_body`` flag, or ``rigged_model_ready`` label alone is intentionally
    insufficient.
    """

    root = Path(root).resolve()
    manifest_value = str(
        person_record.get("body_approval_manifest")
        or person_record.get("runtime_body_manifest")
        or ""
    ).strip()
    reasons: list[str] = []
    if not manifest_value:
        return {"eligible": False, "reasons": ["body_approval_manifest_missing"]}
    manifest_path = Path(manifest_value)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    try:
        manifest_path = manifest_path.resolve(strict=True)
        manifest_path.relative_to(root)
    except (FileNotFoundError, ValueError):
        return {"eligible": False, "reasons": ["body_approval_manifest_invalid_or_outside_root"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"eligible": False, "reasons": ["body_approval_manifest_unreadable"]}

    status = _normal_status(manifest.get("status"))
    if any(word in status for word in BAD_STATUS_WORDS):
        reasons.append("body_status_not_eligible")
    if status not in APPROVED_RUNTIME_STATUSES:
        reasons.append("body_status_not_runtime_approved")
    if manifest.get("runtime_activation_allowed") is not True:
        reasons.append("runtime_activation_not_approved")
    review = manifest.get("review_state") if isinstance(manifest.get("review_state"), dict) else {}
    if review.get("owner_approved") is not True:
        reasons.append("owner_body_approval_missing")
    if review.get("rendered_visual_review_passed") is not True:
        reasons.append("rendered_visual_review_missing")
    if review.get("runtime_quality_gate_passed") is not True:
        reasons.append("runtime_quality_gate_missing")

    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        artifact = {}
    body_value = str(manifest.get("body_path") or artifact.get("path") or "").strip()
    if not body_value:
        reasons.append("body_path_missing")
        body_path = None
    else:
        body_path = Path(body_value)
        if not body_path.is_absolute():
            body_path = manifest_path.parent / body_path
        try:
            body_path = body_path.resolve(strict=True)
            body_path.relative_to(root)
        except (FileNotFoundError, ValueError):
            reasons.append("body_path_invalid_or_outside_root")
            body_path = None
        else:
            if not body_path.is_file():
                reasons.append("body_path_invalid_or_outside_root")
                body_path = None
    expected_hash = str(
        manifest.get("body_sha256")
        or artifact.get("sha256")
        or ""
    ).lower()
    actual_body_hash = _sha256(body_path).lower() if body_path else ""
    if body_path and (not expected_hash or actual_body_hash != expected_hash):
        reasons.append("body_hash_missing_or_mismatched")
    if body_path and expected_hash and actual_body_hash == expected_hash:
        reasons.extend(
            _validate_hash_bound_rendered_evidence(
                root,
                manifest_path,
                review,
                actual_body_hash,
            )
        )
    else:
        reasons.append("rendered_visual_evidence_cannot_bind_unverified_body")

    activation = person_record.get("activation_policy")
    if isinstance(activation, dict) and activation.get("body_world_life_loop_allowed") is False:
        reasons.append("person_body_activation_permission_blocked")
    return {
        "eligible": not reasons,
        "reasons": list(dict.fromkeys(reasons)),
        "manifest_path": str(manifest_path),
        "body_path": str(body_path) if body_path else "",
    }
