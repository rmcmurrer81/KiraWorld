"""Repeatable reference intake and build preparation for TemporaryAI avatars."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Core.avatar_asset_library import (
    adult_face_body_trials_path,
    asset_library_manifest_path,
    body_generation_curriculum_path,
    enforce_candidate_maturity_identity,
    hair_trial_report_path,
    hair_generation_curriculum_path,
    infer_avatar_maturity_policy,
    shoe_generation_curriculum_path,
    skin_tone_template_path,
    spa_age_up_policy_path,
)
from Core.avatar_living_portrait import ensure_avatar_body_manifest, ensure_avatar_build_plan
from Core.avatar_reconstruction_contract import evaluate_avatar_reconstruction_contract


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
GENERIC_IDENTITY_WORDS = {
    "avatar",
    "base",
    "ai", "and", "character", "expert", "fictional", "historical", "person",
    "temporary", "the", "with",
    "download",
    "downloads",
    "for",
    "image",
    "images",
    "photo",
    "photos",
    "picture",
    "pictures",
    "reference",
    "references",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3 and token not in GENERIC_IDENTITY_WORDS
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_size(path: Path) -> tuple[int, int] | tuple[None, None]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None, None


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _write_generation_job(
    candidate_id: str,
    profile: dict[str, Any],
    reference_count: int,
    body_manifest: dict[str, Any],
    reconstruction_contract: dict[str, Any] | None = None,
) -> Path:
    """Write the durable job contract that a future local avatar backend can execute."""
    maturity_identity_validation = enforce_candidate_maturity_identity(candidate_id, profile)
    avatar_root = AVATAR_ROOT / candidate_id
    ai_type = str(profile.get("ai_type") or "").lower()
    identity_mode = (
        "exact_version_likeness"
        if ai_type in {"canon_reconstruction_temp_ai", "historical_temp_ai"}
        else "original_expert_design"
    )
    pose_count = int(body_manifest.get("ready_pose_count") or 0)
    maturity_policy = infer_avatar_maturity_policy(candidate_id, profile)
    reconstruction_contract = dict(reconstruction_contract or {})
    if pose_count:
        stage = "generated_pose_preview_available"
    elif reconstruction_contract.get("staging_allowed") is True:
        stage = "private_reconstruction_ready_backend_unavailable"
    elif reference_count:
        stage = "reference_review"
    else:
        stage = "awaiting_references"
    backend = {
        "background_removal": False,
        "multi_view_identity_reconstruction": False,
        "mesh_generation": False,
        "skeleton_rigging": False,
        "animation_retargeting": False,
        "note": "No compatible local automated image-to-rig backend is installed yet.",
    }
    raw_forms = (profile.get("visual_identity", {}) or {}).get("forms", {}) or {}
    if isinstance(raw_forms, dict):
        forms = [str(item) for item in raw_forms]
    elif isinstance(raw_forms, list):
        forms = [
            str(item.get("id") or item.get("name") or "default")
            if isinstance(item, dict)
            else str(item)
            for item in raw_forms
        ]
    else:
        forms = []
    forms = [item for item in forms if item] or ["default"]
    job = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": _now_iso(),
        "status": stage,
        "identity_mode": identity_mode,
        "reference_count": reference_count,
        "generated_2d_pose_count": pose_count,
        "requested_outputs": {
            "forms": forms,
            "review_views": [
                "head_front", "head_left_profile", "head_right_profile",
                "full_body_front", "full_body_side", "full_body_back",
            ],
            "final_model": "rigged GLB with identity-consistent clothing variants",
            "animations": ["idle", "walk", "wave", "sit", "read", "use_computer", "talking"],
        },
        "avatar_builder_asset_library": {
            "manifest": _relative(asset_library_manifest_path()),
            "hair_trial_report": _relative(hair_trial_report_path()),
            "hair_generation_curriculum": _relative(hair_generation_curriculum_path()),
            "body_generation_curriculum": _relative(body_generation_curriculum_path()),
            "adult_face_body_trials": _relative(adult_face_body_trials_path()),
            "shoe_generation_curriculum": _relative(shoe_generation_curriculum_path()),
            "skin_tone_templates": _relative(skin_tone_template_path()),
            "spa_age_up_policy": _relative(spa_age_up_policy_path()),
            "selection_rule": (
                "Use indexed model assets first. Hair, eyes, body, hands, and movement "
                "references must be selected and self-graded before fitting."
            ),
        },
        "anatomy_policy": maturity_policy,
        "maturity_identity_validation": maturity_identity_validation,
        "picture_first_reconstruction_contract": reconstruction_contract,
        "backend_availability": backend,
        "truth_note": (
            "This is an automatic build job and progress record. It does not claim that a "
            "reviewed likeness, 3D mesh, rig, or animation set has already been generated."
        ),
    }
    path = avatar_root / "avatar_generation_job.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    return path


def matching_reference_folders(
    profile: dict[str, Any],
    desktop_reference_root: Path,
) -> list[Path]:
    """Find intentionally named user folders that match this candidate."""
    if not desktop_reference_root.exists():
        return []
    identity_text = " ".join(
        str(profile.get(key, ""))
        for key in ("candidate_id", "display_name", "role_title")
    )
    identity_tokens = _tokens(identity_text)
    matches: list[Path] = []
    for folder in desktop_reference_root.iterdir():
        if not folder.is_dir():
            continue
        folder_tokens = _tokens(folder.name)
        if not folder_tokens:
            continue
        # A deliberately named one-word folder such as "Kara" is enough;
        # multiword folders must have every meaningful word in the identity.
        if folder_tokens.issubset(identity_tokens):
            matches.append(folder)
    return sorted(matches, key=lambda item: item.name.lower())


def _guess_form(path: Path, profile: dict[str, Any]) -> str:
    label = " ".join([path.name, path.parent.name]).lower()
    if any(word in label for word in ("ladybug", "supergirl", "hero", "costume", "suit")):
        return "hero"
    if any(word in label for word in ("civilian", "marinette", "kara", "everyday")):
        return "civilian"
    raw_forms = (profile.get("visual_identity", {}) or {}).get("forms", {}) or {}
    if isinstance(raw_forms, dict):
        forms = [str(item) for item in raw_forms]
    elif isinstance(raw_forms, list):
        forms = [
            str(item.get("id") or item.get("name") or item.get("label") or "")
            if isinstance(item, dict)
            else str(item)
            for item in raw_forms
        ]
        forms = [item for item in forms if item]
    else:
        forms = []
    return forms[0].lower() if len(forms) == 1 else "unknown"


def ingest_desktop_avatar_references(
    candidate_id: str,
    profile: dict[str, Any],
    desktop_reference_root: Path | None = None,
) -> dict[str, Any]:
    """Copy matching user-curated images into a candidate-owned intake folder."""
    desktop_reference_root = desktop_reference_root or Path.home() / "Desktop"
    avatar_root = AVATAR_ROOT / candidate_id
    intake_root = avatar_root / "references" / "desktop_intake"
    intake_root.mkdir(parents=True, exist_ok=True)
    folders = matching_reference_folders(profile, desktop_reference_root)
    records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    existing_by_hash: dict[str, Path] = {}
    for existing in intake_root.rglob("*"):
        if existing.is_file() and existing.suffix.lower() in IMAGE_EXTENSIONS:
            try:
                existing_by_hash[_sha256(existing)] = existing
            except OSError:
                continue

    for folder in folders:
        for source in sorted(folder.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            file_hash = _sha256(source)
            if file_hash in seen_hashes:
                continue
            seen_hashes.add(file_hash)
            safe_folder = re.sub(r"[^a-z0-9]+", "_", folder.name.lower()).strip("_")
            target = intake_root / f"{safe_folder}_{file_hash[:12]}{source.suffix.lower()}"
            if file_hash in existing_by_hash:
                target = existing_by_hash[file_hash]
            elif not target.exists():
                shutil.copy2(source, target)
            width, height = _image_size(target)
            records.append({
                "provider": "Robert desktop avatar reference intake",
                "media_type": "image",
                "subject_id": candidate_id,
                "source_folder": str(folder),
                "source_file": str(source),
                "status": "copied_for_review",
                "local_file": _relative(target),
                "sha256": file_hash,
                "artifact_hash_verified": True,
                "width": width,
                "height": height,
                "form": _guess_form(source, profile),
                "view": "unclassified",
                "full_body_reviewed": False,
                "review_required": True,
                "privacy_scope": "candidate_private_reference",
                "identity_evidence_approved": False,
            })

    recorded_hashes = {str(record.get("sha256")) for record in records}
    for file_hash, target in sorted(existing_by_hash.items(), key=lambda item: str(item[1])):
        if file_hash in recorded_hashes:
            continue
        width, height = _image_size(target)
        records.append({
            "provider": "Existing candidate desktop intake",
            "media_type": "image",
            "subject_id": candidate_id,
            "source_folder": "",
            "source_file": "",
            "status": "already_imported_for_review",
            "local_file": _relative(target),
            "sha256": file_hash,
            "artifact_hash_verified": True,
            "width": width,
            "height": height,
            "form": _guess_form(target, profile),
            "view": "unclassified",
            "full_body_reviewed": False,
            "review_required": True,
            "privacy_scope": "candidate_private_reference",
            "identity_evidence_approved": False,
        })

    manifest = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": _now_iso(),
        "status": "desktop_references_ready_for_review" if records else "no_matching_desktop_folder",
        "searched_root": str(desktop_reference_root),
        "matched_folders": [str(folder) for folder in folders],
        "reference_count": len(records),
        "truth_note": (
            "These are copied visual references. They are not a generated body, "
            "a reviewed likeness, or a rigged 3D avatar."
        ),
        "references": records,
    }
    manifest_path = avatar_root / "references" / "desktop_reference_intake.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def prepare_candidate_avatar_pipeline(
    candidate_id: str,
    profile: dict[str, Any],
    desktop_reference_root: Path | None = None,
) -> dict[str, Any]:
    """Prepare manifests and plans without claiming that a 3D body exists."""
    # Fail before reference ingestion, plan creation, or job/status writes.
    maturity_identity_validation = enforce_candidate_maturity_identity(candidate_id, profile)
    avatar_root = AVATAR_ROOT / candidate_id
    desktop_manifest = ingest_desktop_avatar_references(
        candidate_id,
        profile,
        desktop_reference_root,
    )
    web_manifest_path = avatar_root / "references" / "avatar_reference_manifest.json"
    web_references: list[dict[str, Any]] = []
    if web_manifest_path.exists():
        try:
            data = json.loads(web_manifest_path.read_text(encoding="utf-8"))
            web_references = data.get("references", []) if isinstance(data, dict) else []
        except (OSError, json.JSONDecodeError):
            web_references = []
    references = [*web_references, *desktop_manifest["references"]]
    maturity_policy = infer_avatar_maturity_policy(candidate_id, profile)
    reconstruction_contract = evaluate_avatar_reconstruction_contract(
        candidate_id=candidate_id,
        maturity_policy=maturity_policy,
        references=references,
        request_complete_adult_anatomy=bool(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "request_complete_adult_anatomy"
            )
        ),
        requested_eye_color=str(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "eye_color"
            )
            or ""
        ),
        measurements_reviewed=bool(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "measurements_reviewed"
            )
        ),
        adult_anatomy_reference_reviewed=bool(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "adult_anatomy_reference_reviewed"
            )
        ),
        base_body_artifact_reviewed=bool(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "base_body_artifact_reviewed"
            )
        ),
        rig_topology_evidence_reviewed=bool(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "rig_topology_evidence_reviewed"
            )
        ),
        allow_provisional_identity_unknown=bool(
            ((profile.get("visual_identity") or {}) if isinstance(profile.get("visual_identity"), dict) else {}).get(
                "allow_provisional_identity_unknown"
            )
        ),
    )
    reconstruction_contract_path = avatar_root / "avatar_reconstruction_contract.json"
    reconstruction_contract_path.write_text(
        json.dumps(reconstruction_contract, indent=2), encoding="utf-8"
    )
    plan_path = ensure_avatar_build_plan(candidate_id, profile, references)
    body_manifest_path = ensure_avatar_body_manifest(candidate_id, profile)
    body_manifest = json.loads(body_manifest_path.read_text(encoding="utf-8"))
    pose_assets_available = body_manifest.get("status") == "pose_assets_ready"
    generation_job_path = _write_generation_job(
        candidate_id,
        profile,
        len(references),
        body_manifest,
        reconstruction_contract,
    )
    if pose_assets_available:
        status = "generated_pose_preview_available"
    elif reconstruction_contract["staging_allowed"]:
        status = "private_reconstruction_ready_backend_unavailable"
    elif references:
        status = "references_require_review_or_multiview_completion"
    else:
        status = "awaiting_visual_references"
    result = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": _now_iso(),
        "status": status,
        "reference_count": len(references),
        "desktop_reference_count": desktop_manifest["reference_count"],
        "desktop_reference_manifest": _relative(
            avatar_root / "references" / "desktop_reference_intake.json"
        ),
        "avatar_build_plan": _relative(plan_path),
        "avatar_body_manifest": _relative(body_manifest_path),
        "avatar_generation_job": _relative(generation_job_path),
        "avatar_reconstruction_contract": _relative(reconstruction_contract_path),
        "private_staged_reconstruction_allowed": reconstruction_contract["staging_allowed"],
        "reconstruction_failures": reconstruction_contract["failures"],
        "generated_2d_pose_preview_ready": pose_assets_available,
        "actual_rigged_3d_body_ready": False,
        "maturity_identity_validation": maturity_identity_validation,
        "next_action": (
            "Review and classify exact-subject front, profile/three-quarter, and full-body pictures; then record body landmarks."
            if references and not reconstruction_contract["staging_allowed"]
            else "Add reviewed visual references."
            if not references
            else "Use the reviewed picture-first contract for a private staged build; runtime activation remains separately blocked."
        ),
    }
    (avatar_root / "avatar_pipeline_status.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result
