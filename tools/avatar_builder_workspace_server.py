from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.avatar_asset_library import (  # noqa: E402
    AvatarMaturityPolicyError,
    NORMAL_MARINETTE_CANDIDATE_ID,
    build_avatar_asset_library,
    hair_trial_report_path,
    infer_avatar_maturity_policy,
    run_hair_style_trials,
    write_avatar_builder_learning_plans,
)
from Core.avatar_builder_ai import (  # noqa: E402
    avatar_builder_chat,
    create_avatar_redo_job,
    load_adjustments,
    run_builder_review,
    save_adjustments,
)
from Core.temp_ai_avatar_pipeline import prepare_candidate_avatar_pipeline  # noqa: E402
from Core.kira_runtime_body_selection import (  # noqa: E402
    evaluate_kira_runtime_body_selection,
    resolve_kira_runtime_body_path,
)
from tools.create_temp_ai_avatar_build_brief import create_brief  # noqa: E402


PORT = int(os.environ.get("KIRA_AVATAR_BUILDER_PORT", "8770"))
RUNTIME_DIR = ROOT / "Data" / "runtime"
STATE_PATH = RUNTIME_DIR / "avatar_builder_workspace_state.json"
AVATAR_TEMP_DIR = ROOT / "Avatar" / "temp_ai"
AVATAR_STATE_DIR = ROOT / "Avatar" / "state" / "temp_ai"
TEMP_CANDIDATE_DIR = ROOT / "TemporaryAI" / "candidates"
AVATAR_BUILDER_DIR = ROOT / "Avatar" / "avatar_builder"
AVATAR_ONLY_VARIANTS_DIR = AVATAR_BUILDER_DIR / "avatar_only_variants"
COMPONENT_PRODUCTION_PLANS_DIR = AVATAR_BUILDER_DIR / "component_production" / "plans"
KIRA_CURRENT_OWNER_REVIEW_GALLERY = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "KIRA_ALL_CURRENT_BODY_IMAGES_GALLERY.html"
)
DESKTOP_ROOT = Path.home() / "Desktop"
DESKTOP_AVATAR_REFERENCES = DESKTOP_ROOT / "Downloads For Avatars"
THREE_ROOT = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "home_world"
    / "builds"
    / "home_world_main_house_20260630_223000"
    / "preview"
    / "node_modules"
    / "three"
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif"}
IMAGE_MIME_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}
MAX_REFERENCE_UPLOAD_BYTES = 25 * 1024 * 1024
MODEL_SUFFIXES = {".glb", ".gltf", ".bin", ".ktx2", ".png", ".jpg", ".jpeg", ".webp"}
LOG_LOCK = threading.Lock()
ARCHIVED_CANDIDATE_IDS = {
    "avatar_living_portrait_smoke",
    "ladybug_prompt_smoke",
}
SUPERSEDED_AUDIT_ONLY_CANDIDATE_IDS = {
    # The existing canonical Earth-65 Gwen profile now carries the reviewed
    # adult 18-20 version binding. Keep this older safety workaround on disk as
    # audit history, but never show it as a second actionable Gwen.
    "spider_gwen_adult_avatar_project_variant_20260716",
}
SUPERSEDED_CANDIDATE_REDIRECTS = {
    "spider_gwen_adult_avatar_project_variant_20260716": (
        "spider_gwen_spider_gwen_20260606_013325"
    ),
}
KIRA_STAGED_BROWN_EYE_RIG = (
    ROOT
    / "Avatar"
    / "models"
    / "staged"
    / "kira"
    / "eyes"
    / "kira_brown_eye_rig_v3_2"
    / "kira_brown_eye_rig_v3_2.glb"
)
KIRA_STAGED_BROWN_EYE_MANIFEST = KIRA_STAGED_BROWN_EYE_RIG.parent / "manifest.json"
KIRA_STAGED_BROWN_EYE_SHA256 = "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413"
COMPONENT_PRODUCTION_CANDIDATE_ALIASES = {
    # Robert's owner-presence profile predates the normalized production ID.
    # Keep this visible as an alias until canonical profile normalization is
    # complete; never create a second body or silently change either profile.
    "robert_mcmurrer_presence_ai": "robert_user_avatar_20260716",
}
BIOLOGICAL_USER_AVATAR_BODY_STATES = {
    "NO_BODY",
    "STATIC_REVIEW_CANDIDATE",
    "OWNER_APPROVED_BODY",
    "SAVED_INACTIVE",
    "VR_READY_LATER",
}


def now_stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default.copy() if isinstance(default, dict) else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def label_from_id(candidate_id: str) -> str:
    special = {"kira": "Kira", "lisa": "Lisa"}
    if candidate_id.lower() in special:
        return special[candidate_id.lower()]
    return " ".join(part.capitalize() for part in re.split(r"[_\s]+", candidate_id) if part) or candidate_id


def normalize_workspace_candidate_id(candidate_id: str) -> str:
    """Prevent superseded audit profiles from becoming actionable identities."""

    value = str(candidate_id or "").strip()
    return SUPERSEDED_CANDIDATE_REDIRECTS.get(value, value)


def avatar_body_state(profile: dict, state: dict, *, has_runtime_body: bool) -> str:
    """Return a truthful builder-body state without implying activation.

    Biological player avatars use the explicit owner-review state machine.
    Existing synthetic/person records retain their legacy body indicator.
    """

    person_body_type = str(profile.get("person_body_type") or "").strip()
    if person_body_type == "BIOLOGICAL_USER_AVATAR":
        value = str(
            state.get("body_state")
            or profile.get("body_state")
            or "NO_BODY"
        ).strip().upper()
        return value if value in BIOLOGICAL_USER_AVATAR_BODY_STATES else "NO_BODY"
    return "RUNTIME_BODY_LINKED" if has_runtime_body else "NO_BODY"


def avatar_only_variant_bindings() -> dict[str, list[str]]:
    """Return non-mind build variants grouped by their canonical subject.

    Avatar-only records are useful authoring targets, but a record whose
    ``source_candidate_id`` points at a real subject is not a second person.
    Keep the record selectable while presenting it beneath that subject.
    Standalone avatar-only records without a valid source binding remain
    ordinary top-level workspace entries.
    """

    bindings: dict[str, list[str]] = {}
    if not AVATAR_ONLY_VARIANTS_DIR.exists():
        return bindings
    for path in sorted(AVATAR_ONLY_VARIANTS_DIR.glob("*.json")):
        variant_id = path.stem
        if variant_id in ARCHIVED_CANDIDATE_IDS | SUPERSEDED_AUDIT_ONLY_CANDIDATE_IDS:
            continue
        profile = read_json(path, {})
        if not isinstance(profile, dict):
            continue
        source_id = str(profile.get("source_candidate_id") or "").strip()
        if not source_id or source_id == variant_id:
            continue
        bindings.setdefault(source_id, []).append(variant_id)
    for variant_ids in bindings.values():
        variant_ids.sort(key=lambda value: label_from_id(value).lower())
    return bindings


def load_profile(candidate_id: str) -> dict:
    temp_profile = read_json(TEMP_CANDIDATE_DIR / candidate_id / "temporary_ai_profile.json", {})
    avatar_only_profile = read_json(AVATAR_ONLY_VARIANTS_DIR / f"{candidate_id}.json", {})
    avatar_profile = read_json(AVATAR_TEMP_DIR / candidate_id / "avatar_profile.json", {})
    state = read_json(AVATAR_STATE_DIR / f"{candidate_id}.json", {})
    adjustments = load_adjustments(candidate_id)

    profile = temp_profile if temp_profile else avatar_only_profile if avatar_only_profile else {}
    if avatar_only_profile and profile is avatar_only_profile:
        profile.setdefault("ai_type", "avatar_only_inactive_variant")
        maturity = profile.get("maturity") if isinstance(profile.get("maturity"), dict) else {}
        maturity_lane = str(maturity.get("lane") or "").strip()
        if maturity_lane in {"adult", "non_adult_doll_safe"}:
            age_review = profile.get("age_review") if isinstance(profile.get("age_review"), dict) else {}
            age_review = dict(age_review)
            age_review.setdefault("maturity_class_override", maturity_lane)
            age_review.setdefault("reason", "Inactive avatar-only variant profile binding")
            age_review.setdefault("source", "Avatar Builder canonical preflight registry")
            profile["age_review"] = age_review
        elif maturity_lane == "adult_aged_up_variant":
            age_review = profile.get("age_review") if isinstance(profile.get("age_review"), dict) else {}
            age_review = dict(age_review)
            age_review.setdefault(
                "age_progression_presentation_label", "adult_aged_up_variant"
            )
            age_review.setdefault(
                "reason",
                "Inactive age-progressed presentation variant; exact maturity remains unresolved pending separate classification.",
            )
            age_review.setdefault("source", "Avatar Builder canonical preflight registry")
            profile["age_review"] = age_review
    if not profile and avatar_profile:
        profile = {
            "candidate_id": candidate_id,
            "display_name": avatar_profile.get("display_name") or label_from_id(candidate_id),
            "ai_type": avatar_profile.get("build_mode") or "avatar_builder_target",
            "visual_identity": {
                "forms": avatar_profile.get("visual_profile", {}).get("forms_or_variants", []) or ["default"],
            },
        }
    if not profile:
        profile = {
            "candidate_id": candidate_id,
            "display_name": label_from_id(candidate_id),
            "ai_type": "permanent_or_runtime_avatar",
            "visual_identity": {"forms": [str(state.get("form") or "default")]},
        }

    profile.setdefault("candidate_id", candidate_id)
    profile.setdefault("display_name", label_from_id(candidate_id))
    profile.setdefault("ai_type", "avatar_builder_target")
    profile.setdefault("visual_identity", {"forms": ["default"]})
    if adjustments.get("maturity_override"):
        age_review = profile.get("age_review") if isinstance(profile.get("age_review"), dict) else {}
        age_review = dict(age_review)
        age_review["maturity_class_override"] = adjustments.get("maturity_override")
        age_review["reason"] = adjustments.get("maturity_reason") or "Avatar Builder correction"
        age_review["source"] = "Avatar Builder Workspace"
        age_review["updated_at"] = adjustments.get("updated_at")
        exact_classification = adjustments.get(
            "confirmed_adult_classification_evidence"
        )
        if isinstance(exact_classification, dict):
            age_review["confirmed_adult_classification_evidence"] = dict(
                exact_classification
            )
        if adjustments.get("resident_adult_anatomy_choice_recorded") is True:
            age_review["resident_adult_anatomy_choice_recorded"] = True
        if adjustments.get("age_progression_presentation_label") == (
            "adult_aged_up_variant"
        ):
            age_review["age_progression_presentation_label"] = (
                "adult_aged_up_variant"
            )
        if isinstance(adjustments.get("age_progression_contract"), dict):
            age_review["age_progression_contract"] = dict(
                adjustments["age_progression_contract"]
            )
        profile["age_review"] = age_review
    return profile


def count_files(path: Path, suffixes: set[str]) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file() and item.suffix.lower() in suffixes)


def count_reference_files(path: Path) -> dict[str, int]:
    counts = {
        "all": 0,
        "approved": 0,
        "downloaded": 0,
        "desktop_intake": 0,
        "rejected": 0,
    }
    if not path.exists():
        return counts
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        counts["all"] += 1
        parts = {part.lower() for part in item.relative_to(path).parts}
        for bucket in ("approved", "downloaded", "desktop_intake", "rejected"):
            if bucket in parts:
                counts[bucket] += 1
    return counts


def component_blocker_categories(reasons: list[str]) -> list[str]:
    """Return compact, stable UI categories without hiding exact plan evidence."""

    categories: list[str] = []
    rules = (
        ("multiview evidence", ("multiview_",)),
        ("photo/identity inputs", ("photo_", "picture_", "reconstruction_")),
        ("authored components", ("component_",)),
        ("topology/anatomy", ("topology_",)),
        ("rig/deformation", ("rig_", "stable_rig_")),
        ("face/lip sync", ("face_",)),
        ("motion/contact", ("locomotion_", "motion_", "contact_")),
        ("identity authority/review", ("owner_", "identity_")),
        ("wearable clothing", ("wearable_", "garment_")),
    )
    for reason in reasons:
        value = str(reason or "").strip().lower()
        category = "other proof"
        for label, prefixes in rules:
            if value.startswith(prefixes):
                category = label
                break
        if category not in categories:
            categories.append(category)
    return categories


def load_component_production_plan(candidate_id: str) -> tuple[dict, Path | None]:
    plan_id = COMPONENT_PRODUCTION_CANDIDATE_ALIASES.get(candidate_id, candidate_id)
    path = COMPONENT_PRODUCTION_PLANS_DIR / f"{plan_id}.json"
    plan = read_json(path, {}) if path.is_file() else {}
    if not isinstance(plan, dict) or not plan:
        return {}, None
    recorded_id = str(plan.get("candidate_id") or "").strip()
    if recorded_id != plan_id:
        return {}, None
    # Generated plans that carry an orchestration binding must match the live
    # request exactly.  Showing a stale plan as current can hide newly failed
    # deformation evidence or make an old component set appear authoritative.
    expected_orchestration_sha = str(
        plan.get("orchestration_request_sha256") or ""
    ).strip().lower()
    if expected_orchestration_sha:
        orchestration_path = (
            ROOT
            / "Avatar"
            / "avatar_builder"
            / "orchestration_requests"
            / f"{plan_id}.json"
        )
        if (
            not re.fullmatch(r"[0-9a-f]{64}", expected_orchestration_sha)
            or orchestration_path.is_symlink()
            or not orchestration_path.is_file()
        ):
            return {}, None
        actual_sha = hashlib.sha256(orchestration_path.read_bytes()).hexdigest()
        if actual_sha != expected_orchestration_sha:
            return {}, None
    return plan, path


def local_file_for_url(url: str) -> Path | None:
    if not url.startswith("/"):
        return None
    target = (ROOT / unquote(url.lstrip("/"))).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return None
    if target.is_file():
        return target
    return None


def local_preview_url_for_path(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    try:
        resolved = path.resolve()
        resolved.relative_to(ROOT.resolve())
    except Exception:
        return ""
    if not resolved.is_file():
        return ""
    return "/" + rel(resolved)


def select_active_preview(
    *,
    builder: tuple[str, Path | None],
    staged: tuple[str, Path | None],
    overlay: tuple[str, Path | None],
    runtime: tuple[str, Path | None],
) -> tuple[str, Path | None, str]:
    """Select a display-only preview without changing runtime activation state.

    Builder and staged real-model drafts are the primary review tier. The
    newest existing file in that tier wins; an older overlay is only a
    fallback. Rejected drafts remain visible for diagnosis but are never
    promoted into the runtime URL by this read-only selection.
    """
    review_candidates: list[tuple[str, Path, str, int]] = []
    for source, (url, path) in (("builder", builder), ("staged", staged)):
        if url and path:
            try:
                modified_ns = path.stat().st_mtime_ns
            except OSError:
                continue
            review_candidates.append((url, path, source, modified_ns))
    if review_candidates:
        url, path, source, _ = max(review_candidates, key=lambda item: item[3])
        return url, path, source
    if overlay[0] and overlay[1]:
        return overlay[0], overlay[1], "overlay"
    if runtime[0] and runtime[1]:
        return runtime[0], runtime[1], "runtime"
    return "", None, "none"


def kira_runtime_selection_binding(profile_model_url: str) -> dict:
    """Expose Kira's exact selected body and its bounded truth claims.

    The Avatar Builder is a review workspace, so it may show the selected R6
    artifact, but it must also say whether the live profile is bound to those
    same bytes.  It must never promote the older R5 preview merely because its
    adjustment timestamp is newer.
    """

    try:
        result = evaluate_kira_runtime_body_selection(ROOT)
        selected = resolve_kira_runtime_body_path(ROOT).resolve(strict=True)
        selected.relative_to(ROOT.resolve(strict=True))
        selected_url = "/" + rel(selected)
        profile_file = local_file_for_url(profile_model_url)
        profile_matches = bool(profile_file and profile_file.resolve() == selected)
        return {
            "valid": bool(result.get("selection_valid")) and selected.is_file(),
            "profile_matches_selection": profile_matches,
            "selected_model_url": selected_url,
            "selected_model_path": selected,
            "selected_model_sha256": str(result.get("selected_model_sha256") or ""),
            "decision": str(result.get("decision") or ""),
            "reversible_owner_review_trial": bool(result.get("reversible_owner_review_trial")),
            "permanent_candidate_allowed": bool(result.get("permanent_candidate_allowed")),
            "adult_external_form_trial": bool(result.get("reversible_owner_review_trial")),
            "complete_adult_anatomy_proven": bool(result.get("full_adult_anatomy_proven")),
            "eye_visual_fit_approved": bool(result.get("eye_visual_fit_approved")),
            "truth_note": str(result.get("truth_note") or ""),
            "reason": "exact_selected_body_and_profile_match" if profile_matches else "profile_and_selection_mismatch_fail_closed",
        }
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {
            "valid": False,
            "profile_matches_selection": False,
            "selected_model_url": "",
            "selected_model_path": None,
            "selected_model_sha256": "",
            "decision": "fail_closed",
            "reversible_owner_review_trial": False,
            "permanent_candidate_allowed": False,
            "adult_external_form_trial": False,
            "complete_adult_anatomy_proven": False,
            "eye_visual_fit_approved": False,
            "truth_note": "Kira's selected body could not be validated; no substitute preview is presented as live.",
            "reason": f"selection_invalid_fail_closed:{type(exc).__name__}",
        }


def kira_builder_eye_preview_binding() -> dict:
    """Return the exact staged eye component for read-only Builder inspection.

    Kira's selected R6 GLB is deliberately body-only.  The Builder may compose
    the independently staged v3.2 eye component for inspection, but this
    helper fails closed if its bytes or manifest no longer match.  It never
    rewrites the R6 body or implies that the composed result is an approved
    replacement avatar.
    """

    try:
        eye_file = KIRA_STAGED_BROWN_EYE_RIG.resolve(strict=True)
        eye_file.relative_to(ROOT.resolve(strict=True))
        manifest = read_json(KIRA_STAGED_BROWN_EYE_MANIFEST, {})
        digest = hashlib.sha256(eye_file.read_bytes()).hexdigest()
        manifest_digest = str(manifest.get("eye_rig_sha256") or "").strip().lower()
        expected_digest = KIRA_STAGED_BROWN_EYE_SHA256.lower()
        valid = digest == expected_digest and manifest_digest == expected_digest
        return {
            "valid": valid,
            "url": "/" + rel(eye_file) if valid else "",
            "sha256": digest,
            "version": str(manifest.get("asset_version") or "3.2"),
            "eye_color": str(manifest.get("eye_color") or "warm brown"),
            "status": (
                "exact-hash staged component available; Builder rendering disabled because R6 eyelid/socket visual fit is UNAPPROVED; R6 GLB unchanged"
                if valid
                else "blocked: staged eye component failed exact-hash validation"
            ),
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {
            "valid": False,
            "url": "",
            "sha256": "",
            "version": "3.2",
            "eye_color": "warm brown",
            "status": "blocked: staged eye component or manifest is unavailable",
        }


def desktop_reference_root() -> Path:
    return DESKTOP_AVATAR_REFERENCES if DESKTOP_AVATAR_REFERENCES.exists() else DESKTOP_ROOT


def candidate_ids() -> list[str]:
    ids: set[str] = set()
    for root in (AVATAR_TEMP_DIR, TEMP_CANDIDATE_DIR):
        if root.exists():
            ids.update(item.name for item in root.iterdir() if item.is_dir())
    if AVATAR_STATE_DIR.exists():
        ids.update(path.stem for path in AVATAR_STATE_DIR.glob("*.json"))
    if AVATAR_ONLY_VARIANTS_DIR.exists():
        ids.update(path.stem for path in AVATAR_ONLY_VARIANTS_DIR.glob("*.json"))
    # A derived avatar build record is nested under its canonical person when
    # that canonical subject is actually present. Nothing is deleted: the
    # nested record remains selectable through ``candidate_record.variants``.
    for source_id, variant_ids in avatar_only_variant_bindings().items():
        if source_id in ids:
            ids.difference_update(variant_ids)
    for archived_id in ARCHIVED_CANDIDATE_IDS | SUPERSEDED_AUDIT_ONLY_CANDIDATE_IDS:
        ids.discard(archived_id)
    return sorted(ids, key=lambda value: label_from_id(value).lower())


def candidate_record(candidate_id: str, *, include_variants: bool = True) -> dict:
    profile = load_profile(candidate_id)
    person_body_type = str(profile.get("person_body_type") or "").strip()
    is_biological_user_avatar = person_body_type == "BIOLOGICAL_USER_AVATAR"
    body_assignment = (
        profile.get("body_assignment")
        if isinstance(profile.get("body_assignment"), dict)
        else {}
    )
    avatar_root = AVATAR_TEMP_DIR / candidate_id
    references_root = avatar_root / "references"
    adjustments = load_adjustments(candidate_id)
    state_path = AVATAR_STATE_DIR / f"{candidate_id}.json"
    state = read_json(state_path, {})
    pipeline = read_json(avatar_root / "avatar_pipeline_status.json", {})
    body_manifest = read_json(avatar_root / "generated_body" / "avatar_body_manifest.json", {})
    generation_job = read_json(avatar_root / "avatar_generation_job.json", {})
    reconstruction_contract_path = avatar_root / "avatar_reconstruction_contract.json"
    configured_contract = str(adjustments.get("picture_first_reconstruction_contract") or "").strip()
    if configured_contract:
        configured_path = Path(configured_contract)
        if not configured_path.is_absolute():
            configured_path = ROOT / configured_path
        configured_path = configured_path.resolve()
        if configured_path.is_relative_to(ROOT.resolve()) and configured_path.is_file():
            reconstruction_contract_path = configured_path
    reconstruction_contract = read_json(reconstruction_contract_path, {})
    component_plan, component_plan_path = load_component_production_plan(candidate_id)
    multiview_authoring = component_plan.get("multiview_authoring")
    if not isinstance(multiview_authoring, dict):
        multiview_authoring = {}
    body_blockers = component_plan.get("body_blocking_reasons")
    if not isinstance(body_blockers, list):
        body_blockers = []
    garment_blockers = component_plan.get("garment_blocking_reasons")
    if not isinstance(garment_blockers, list):
        garment_blockers = []
    avatar_profile = read_json(avatar_root / "avatar_profile.json", {})
    model_url = str(state.get("model_url") or "")
    model_status = str(state.get("model_status") or "")
    historical_builder_preview_url = str(adjustments.get("builder_preview_model_url") or "")
    builder_preview_url = historical_builder_preview_url
    overlay_calibration_url = str(adjustments.get("builder_overlay_calibration_model_url") or "")
    latest_kira_eye_pass = adjustments.get("latest_kira_adult_body_eye_pass")
    staged_review_url = ""
    if isinstance(latest_kira_eye_pass, dict):
        staged_review_url = local_preview_url_for_path(str(latest_kira_eye_pass.get("review_model") or ""))
    if is_biological_user_avatar:
        staged_review_url = local_preview_url_for_path(
            str(body_assignment.get("preview_model_path") or "")
        )
    kira_selection = kira_runtime_selection_binding(model_url) if candidate_id == "kira" else {}
    if candidate_id == "kira" and kira_selection.get("valid"):
        # R6 is the exact selected review artifact. The old R5 builder preview
        # remains available as audit history but can no longer override it.
        builder_preview_url = str(kira_selection.get("selected_model_url") or "")
        if kira_selection.get("profile_matches_selection"):
            model_url = builder_preview_url
        else:
            model_url = ""
            model_status = "body_selection_profile_mismatch_fail_closed"
    has_runtime_body = bool(model_url or "rigged" in model_status.lower())
    if is_biological_user_avatar:
        # A player-avatar review assignment is never a synthetic-person
        # activation or runtime-body link.
        model_url = ""
        model_status = "saved_inactive_player_avatar"
        has_runtime_body = False
    preview_file = local_file_for_url(model_url)
    builder_preview_file = local_file_for_url(builder_preview_url)
    overlay_calibration_file = local_file_for_url(overlay_calibration_url)
    staged_review_file = local_file_for_url(staged_review_url)
    active_preview_url, active_preview_file, active_preview_source = select_active_preview(
        builder=(builder_preview_url, builder_preview_file),
        staged=(staged_review_url, staged_review_file),
        overlay=(overlay_calibration_url, overlay_calibration_file),
        runtime=(model_url, preview_file),
    )
    if candidate_id == "kira" and kira_selection.get("valid"):
        selected_file = kira_selection.get("selected_model_path")
        if isinstance(selected_file, Path) and selected_file.is_file():
            active_preview_url = str(kira_selection.get("selected_model_url") or "")
            active_preview_file = selected_file
            active_preview_source = (
                "runtime_selection"
                if kira_selection.get("profile_matches_selection")
                else "selected_review_candidate_runtime_blocked"
            )
    reference_counts = count_reference_files(references_root)
    maturity_policy = infer_avatar_maturity_policy(candidate_id, profile)
    pipeline_reference_count = int(pipeline.get("reference_count") or 0)
    pipeline_desktop_count = int(pipeline.get("desktop_reference_count") or 0)
    preview_skin_tone = str(adjustments.get("preview_skin_tone") or "").strip()
    preview_material_contract = str(adjustments.get("preview_material_contract") or "").strip()
    if candidate_id == "kira":
        # Match the pre-R6 live renderer exactly.  R6's dark color is baked
        # into a texture, so a tint alone cannot restore the earlier look.
        preview_skin_tone = "#e6c0a9"
        preview_material_contract = "pre_r6_live_light_untextured_v1"
    kira_eye_preview = kira_builder_eye_preview_binding() if candidate_id == "kira" else {}

    profile_scope = str(profile.get("profile_scope") or "").strip()
    canonical_subject_id = str(profile.get("source_candidate_id") or candidate_id).strip() or candidate_id
    is_build_variant = profile_scope == "avatar_only_inactive_variant" and canonical_subject_id != candidate_id

    record = {
        "id": candidate_id,
        "label": str(profile.get("display_name") or avatar_profile.get("display_name") or label_from_id(candidate_id)),
        "ai_type": str(profile.get("ai_type") or avatar_profile.get("build_mode") or ""),
        "person_body_type": person_body_type or "SYNTHETIC_OR_CHARACTER_AVATAR",
        "body_state": avatar_body_state(
            profile,
            state,
            has_runtime_body=has_runtime_body,
        ),
        "creates_temporary_ai_or_mind": profile.get("creates_temporary_ai_or_mind") is True,
        "included_in_synthetic_person_selector": (
            profile.get("included_in_synthetic_person_selector") is True
        ),
        "counts_as_active_synthetic_person": (
            profile.get("counts_as_active_synthetic_person") is True
        ),
        "autonomous_life_loop_allowed": (
            profile.get("autonomous_life_loop_allowed") is True
        ),
        "body_assignment_sha256": str(body_assignment.get("sha256") or ""),
        "body_assignment_manifest": str(body_assignment.get("manifest_path") or ""),
        "maturity_class": str(maturity_policy.get("maturity_class") or ""),
        "anatomy_allowed": bool(maturity_policy.get("adult_anatomy_assets_allowed")),
        "adult_external_form_trial": bool(kira_selection.get("adult_external_form_trial")),
        "complete_adult_anatomy_proven": bool(kira_selection.get("complete_adult_anatomy_proven")),
        "runtime_body_selection_valid": bool(kira_selection.get("valid")) if candidate_id == "kira" else None,
        "runtime_body_profile_matches_selection": bool(kira_selection.get("profile_matches_selection")) if candidate_id == "kira" else None,
        "runtime_body_selection_reason": str(kira_selection.get("reason") or "") if candidate_id == "kira" else "",
        "runtime_body_selection_decision": str(kira_selection.get("decision") or "") if candidate_id == "kira" else "",
        "runtime_body_selection_sha256": str(kira_selection.get("selected_model_sha256") or "") if candidate_id == "kira" else "",
        "runtime_body_truth_note": str(kira_selection.get("truth_note") or "") if candidate_id == "kira" else "",
        "base_body_policy": str(maturity_policy.get("required_base_body_policy") or ""),
        "builder_status": str(adjustments.get("approval_status") or "unreviewed"),
        "builder_adjustments_path": rel(adjustment_path) if (adjustment_path := (avatar_root / "avatar_builder_adjustments.json")).exists() else "",
        "redo_job_path": str(adjustments.get("redo_job_path") or ""),
        "adult_redo_job_path": str(adjustments.get("adult_redo_job_path") or ""),
        "reference_visual_audit": str(adjustments.get("reference_visual_audit") or ""),
        "chat_reference_batch": str(adjustments.get("chat_reference_batch") or ""),
        "spandex_wardrobe_plan": str(adjustments.get("spandex_wardrobe_plan") or ""),
        "eye_rebuild_plan": str(adjustments.get("eye_rebuild_plan") or ""),
        "paired_adult_test_candidate": str(adjustments.get("paired_adult_test_candidate") or ""),
        "preview_adjustments": adjustments.get("preview_adjustments") if isinstance(adjustments.get("preview_adjustments"), dict) else {},
        "correction_memory_count": len(adjustments.get("correction_memory_events") or []),
        "next_private_build_route": (
            adjustments.get("next_private_build_route")
            if isinstance(adjustments.get("next_private_build_route"), dict)
            else {}
        ),
        "correction_output_private": adjustments.get("candidate_build_visibility") == "private_owner_review_only",
        "correction_runtime_activation_allowed": adjustments.get("runtime_activation_allowed") is True,
        "preview_skin_tone": preview_skin_tone,
        "preview_material_contract": preview_material_contract,
        "preview_eye_component_url": str(kira_eye_preview.get("url") or ""),
        "preview_eye_component_valid": bool(kira_eye_preview.get("valid")),
        "preview_eye_component_sha256": str(kira_eye_preview.get("sha256") or ""),
        "preview_eye_component_version": str(kira_eye_preview.get("version") or ""),
        "preview_eye_component_color": str(kira_eye_preview.get("eye_color") or ""),
        "preview_eye_component_status": str(kira_eye_preview.get("status") or ""),
        # The exact-hash staged asset remains available for a later authored
        # fit, but the current component does not sit naturally behind R6's
        # eyelid apertures.  Fail closed visually: do not show protruding
        # spheres and do not imply that a structural asset audit is a fit.
        "preview_eye_component_display_enabled": False,
        "preview_eye_component_fit_status": (
            "UNAPPROVED: incompatible with current R6 eyelid/socket openings"
            if kira_eye_preview.get("valid")
            else "unavailable"
        ),
        "preview_eye_component_fit": {},
        "build_target_count": len(adjustments.get("build_targets") or []),
        "last_builder_reply": str(adjustments.get("last_reply") or ""),
        "runtime_model_status": model_status or "not linked",
        "has_runtime_body": has_runtime_body,
        "runtime_model_url": model_url,
        "builder_preview_model_url": builder_preview_url if builder_preview_file else "",
        "historical_builder_preview_model_url": historical_builder_preview_url if local_file_for_url(historical_builder_preview_url) else "",
        "builder_overlay_calibration_model_url": overlay_calibration_url if overlay_calibration_file else "",
        "staged_review_model_url": staged_review_url if staged_review_file else "",
        "silhouette_overlay_pass_manifest": str(adjustments.get("silhouette_overlay_pass_manifest") or ""),
        "avatar_builder_school_curriculum": str(adjustments.get("avatar_builder_school_curriculum") or ""),
        "avatar_builder_school_progress": str(adjustments.get("avatar_builder_school_progress") or ""),
        "avatar_builder_subject_school_status": str(adjustments.get("subject_school_status") or ""),
        "avatar_builder_subject_school_lesson": str(adjustments.get("subject_school_latest_lesson_title") or adjustments.get("subject_school_latest_lesson") or ""),
        "avatar_builder_subject_school_progress": str(adjustments.get("subject_school_progress") or ""),
        "avatar_builder_subject_school_assignment_index": str(adjustments.get("subject_school_assignment_index") or ""),
        "preview_model_url": active_preview_url if active_preview_file else "",
        "preview_model_bytes": int(active_preview_file.stat().st_size) if active_preview_file else 0,
        "preview_model_source": active_preview_source,
        "preview_review_only": bool(active_preview_file and active_preview_source not in {"runtime", "runtime_selection"}),
        "pipeline_status": str(pipeline.get("status") or "not prepared"),
        "pipeline_reference_count": pipeline_reference_count,
        "reference_count": max(pipeline_reference_count, reference_counts["all"]),
        "on_disk_reference_count": reference_counts["all"],
        "desktop_reference_count": max(pipeline_desktop_count, reference_counts["desktop_intake"]),
        "approved_reference_count": reference_counts["approved"],
        "downloaded_reference_count": reference_counts["downloaded"],
        "rejected_reference_count": reference_counts["rejected"],
        "pose_status": str(body_manifest.get("status") or "not prepared"),
        "ready_pose_count": int(body_manifest.get("ready_pose_count") or 0),
        "expected_pose_count": int(body_manifest.get("expected_pose_count") or 0),
        "generation_job_status": str(generation_job.get("status") or "not prepared"),
        "reconstruction_contract_status": str(reconstruction_contract.get("status") or "not prepared"),
        "reconstruction_staging_allowed": reconstruction_contract.get("staging_allowed") is True,
        "reconstruction_failure_count": len(reconstruction_contract.get("failures") or reconstruction_contract.get("blocking_reasons") or []),
        "reconstruction_contract_path": rel(reconstruction_contract_path) if reconstruction_contract_path.is_file() else "",
        "component_production_state": str(component_plan.get("production_state") or "not planned"),
        "component_set_authored": component_plan.get("authored_component_set_present") is True,
        "multiview_authoring_status": str(
            multiview_authoring.get("status") or "not prepared"
        ),
        "multiview_manifest_path": str(
            multiview_authoring.get("manifest_path") or ""
        ),
        "multiview_manifest_hash_verified": (
            multiview_authoring.get("manifest_exact_hash_verified") is True
        ),
        "multiview_source_count": int(
            multiview_authoring.get("source_count") or 0
        ),
        "multiview_exact_hash_source_count": int(
            multiview_authoring.get("exact_hash_source_count") or 0
        ),
        "multiview_reviewed_source_count": int(
            multiview_authoring.get("reviewed_source_count") or 0
        ),
        "multiview_front_ready": (
            multiview_authoring.get("front_view_ready") is True
        ),
        "multiview_depth_ready": (
            multiview_authoring.get("depth_view_ready") is True
        ),
        "multiview_full_body_ready": (
            multiview_authoring.get("full_body_view_ready") is True
        ),
        "multiview_calibration_ready": (
            multiview_authoring.get("single_calibration_frame_ready") is True
        ),
        "multiview_landmark_count": int(
            multiview_authoring.get("reviewed_landmark_count") or 0
        ),
        "multiview_missing_landmark_region_count": len(
            multiview_authoring.get("missing_landmark_regions") or []
        ),
        "multiview_scale_ready": (
            isinstance(multiview_authoring.get("scale_review"), dict)
            and multiview_authoring["scale_review"].get("ready") is True
        ),
        "multiview_base_ready": (
            isinstance(multiview_authoring.get("base_body_review"), dict)
            and multiview_authoring["base_body_review"].get("ready") is True
        ),
        "multiview_review_gap_count": len(
            multiview_authoring.get("review_gaps") or []
        ),
        "multiview_integrity_failure_count": len(
            multiview_authoring.get("integrity_failures") or []
        ),
        "multiview_authoring_queue_ready": (
            multiview_authoring.get("authoring_queue_ready") is True
        ),
        "multiview_author_backend_available": (
            multiview_authoring.get("author_backend_available") is True
        ),
        "body_private_review_ready": component_plan.get("body_private_review_ready") is True,
        "body_blocker_count": len(body_blockers),
        "body_blocker_categories": component_blocker_categories(body_blockers),
        "advanced_garment_ready": component_plan.get("advanced_garment_capability_ready") is True,
        "garment_blocker_count": len(garment_blockers),
        "garment_blocker_categories": component_blocker_categories(garment_blockers),
        "component_next_action": str(component_plan.get("next_action") or "not planned"),
        "component_plan_path": rel(component_plan_path) if component_plan_path else "",
        "avatar_folder": rel(avatar_root),
        "references_folder": rel(references_root),
        "pipeline_status_path": rel(avatar_root / "avatar_pipeline_status.json"),
        "generation_job_path": rel(avatar_root / "avatar_generation_job.json"),
        "state_path": rel(state_path) if state_path.exists() else "",
        "record_scope": "derived_avatar_build_variant" if is_build_variant else "canonical_subject",
        "canonical_subject_id": canonical_subject_id,
        "is_build_variant": is_build_variant,
        "variant_truth_note": str(profile.get("truth_note") or ""),
    }
    if include_variants:
        variant_ids = avatar_only_variant_bindings().get(candidate_id, [])
        record["variants"] = [
            candidate_record(variant_id, include_variants=False)
            for variant_id in variant_ids
        ]
    else:
        record["variants"] = []
    record["variant_count"] = len(record["variants"])
    return record


def asset_library_summary() -> dict:
    manifest_path = AVATAR_BUILDER_DIR / "asset_library" / "manifest.json"
    manifest = read_json(manifest_path, {})
    return {
        "manifest": rel(manifest_path),
        "exists": manifest_path.exists(),
        "asset_count": int(manifest.get("asset_count") or 0),
        "categories": manifest.get("categories") if isinstance(manifest.get("categories"), dict) else {},
    }


def load_state() -> dict:
    state = read_json(STATE_PATH, {})
    state.setdefault("last_action", "")
    state.setdefault("last_result", {})
    return state


def save_action(action: str, result: dict) -> None:
    state = load_state()
    state["last_action"] = action
    state["last_result"] = result
    state["updated_at"] = now_stamp()
    write_json(STATE_PATH, state)


def open_path(path: Path) -> dict:
    path.mkdir(parents=True, exist_ok=True) if path.suffix == "" else path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])
    return {"opened": rel(path)}


def static_path_for_request(request_path: str) -> Path | None:
    decoded = unquote(request_path)
    if decoded.startswith("/vendor/three/"):
        target = (THREE_ROOT / decoded.removeprefix("/vendor/three/")).resolve()
        try:
            target.relative_to(THREE_ROOT.resolve())
        except ValueError:
            return None
        return target if target.is_file() else None

    if not decoded.startswith(("/Avatar/", "/Assets/", "/Data/")):
        return None
    target = (ROOT / decoded.lstrip("/")).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return None
    if target.suffix.lower() not in MODEL_SUFFIXES | IMAGE_SUFFIXES | {".json"}:
        return None
    return target if target.is_file() else None


def content_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".glb":
        return "model/gltf-binary"
    if suffix == ".gltf":
        return "model/gltf+json"
    if suffix == ".js":
        return "text/javascript; charset=utf-8"
    if suffix == ".wasm":
        return "application/wasm"
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"


def clean_upload_name(name: str, fallback_suffix: str) -> str:
    original = Path(name or "").name
    cleaned = re.sub(r"[^A-Za-z0-9_. -]+", "_", original).strip(" ._-")
    if not cleaned:
        cleaned = "reference"
    suffix = Path(cleaned).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        cleaned = f"{Path(cleaned).stem or 'reference'}{fallback_suffix}"
    return cleaned


def unique_child_path(parent: Path, filename: str) -> Path:
    target = parent / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    for index in range(2, 1000):
        candidate = parent / f"{stem}_{index:03d}{suffix}"
        if not candidate.exists():
            return candidate
    raise ValueError("Too many duplicate upload filenames")


def decode_uploaded_image(file_info: dict) -> tuple[bytes, str, str]:
    name = str(file_info.get("name") or "reference")
    mime_type = str(file_info.get("type") or "").lower().strip()
    data_url = str(file_info.get("data_url") or "")
    payload = ""
    header_mime = ""
    if data_url.startswith("data:"):
        match = re.match(r"data:([^;,]+)?;base64,(.*)$", data_url, flags=re.S)
        if not match:
            raise ValueError(f"{name}: unsupported upload data URL")
        header_mime = (match.group(1) or "").lower().strip()
        payload = match.group(2)
    else:
        payload = str(file_info.get("data") or "")
    mime_type = mime_type or header_mime
    suffix = IMAGE_MIME_SUFFIXES.get(mime_type, Path(name).suffix.lower())
    if suffix == ".jpeg":
        suffix = ".jpg"
    if suffix not in IMAGE_SUFFIXES or mime_type and mime_type not in IMAGE_MIME_SUFFIXES:
        raise ValueError(f"{name}: upload must be a raster image file")
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{name}: could not decode uploaded image") from exc
    if not data:
        raise ValueError(f"{name}: uploaded image was empty")
    if len(data) > MAX_REFERENCE_UPLOAD_BYTES:
        raise ValueError(f"{name}: image is larger than 25 MB")
    return data, mime_type or mimetypes.guess_type(name)[0] or "image/*", suffix


def save_uploaded_references(candidate_id: str, files: list[dict]) -> dict:
    if not candidate_id:
        raise ValueError("Missing candidate")
    avatar_root = (AVATAR_TEMP_DIR / candidate_id).resolve()
    try:
        avatar_root.relative_to(AVATAR_TEMP_DIR.resolve())
    except ValueError as exc:
        raise ValueError("Invalid candidate") from exc
    if not isinstance(files, list) or not files:
        raise ValueError("No image files were uploaded")

    batch_name = time.strftime("chat_uploads_%Y%m%d_%H%M%S")
    batch_root = avatar_root / "references" / "chat_uploads" / batch_name
    batch_root.mkdir(parents=True, exist_ok=True)
    saved: list[dict] = []
    for file_info in files:
        if not isinstance(file_info, dict):
            continue
        raw, mime_type, fallback_suffix = decode_uploaded_image(file_info)
        filename = clean_upload_name(str(file_info.get("name") or "reference"), fallback_suffix)
        target = unique_child_path(batch_root, filename)
        target.write_bytes(raw)
        saved.append({
            "media_type": "image",
            "subject_id": candidate_id,
            "source_name": str(file_info.get("name") or filename),
            "saved_path": rel(target),
            "mime_type": mime_type,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "artifact_hash_verified": True,
            "status": "uploaded_for_private_review",
            "view": "unclassified",
            "identity_evidence_approved": False,
            "privacy_scope": "candidate_private_reference",
        })
    if not saved:
        raise ValueError("No valid image files were uploaded")

    manifest_path = batch_root / "upload_manifest.json"
    manifest = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "created_at": now_stamp(),
        "purpose": "Robert uploaded visual references through Avatar Builder Workspace chat.",
        "rule": "These pictures are reference-only evidence. They must not be copied as the avatar body.",
        "status": "private_review_and_view_classification_required",
        "picture_first_gate": "An upload count is not approval. Each picture must be exact-subject reviewed and classified as front, profile/three-quarter, or full-body evidence before reconstruction.",
        "saved_count": len(saved),
        "files": saved,
    }
    write_json(manifest_path, manifest)

    adjustments = load_adjustments(candidate_id)
    adjustments["chat_reference_batch"] = rel(manifest_path)
    adjustments["reference_upload_latest"] = rel(manifest_path)
    adjustments["approval_status"] = "references_uploaded_builder_pass_required"
    targets = adjustments.setdefault("build_targets", [])
    targets.append({
        "kind": "uploaded_visual_references",
        "path": rel(manifest_path),
        "count": len(saved),
        "created_at": now_stamp(),
        "required_use": "hold for exact-subject review and view classification; only approved/hash-bound pictures may drive landmark fitting; never copy a reference mesh as the final body",
    })
    notes = adjustments.setdefault("learning_notes", [])
    notes.append(
        f"Robert uploaded {len(saved)} picture reference(s) for {candidate_id}. "
        "They remain private and unapproved until exact-subject review and camera-view classification."
    )
    save_adjustments(candidate_id, adjustments)
    return {"manifest": rel(manifest_path), "saved": saved}


def html() -> bytes:
    return b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kira Avatar Builder Workspace</title>
  <style>
    :root { color-scheme: dark; font-family: Segoe UI, Arial, sans-serif; }
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; }
    body { margin: 0; background: #07111c; color: #edf7ff; overflow: hidden; }
    #app { height: 100vh; display: grid; grid-template-columns: 340px minmax(0, 1fr); }
    aside { border-right: 1px solid #1f3d5c; background: #0b1724; padding: 10px; min-width: 0; overflow: hidden; display: grid; grid-template-rows: auto auto minmax(0, 1fr); gap: 8px; }
    main { min-width: 0; overflow: hidden; display: grid; grid-template-rows: auto minmax(0, 1fr) 210px; gap: 8px; padding: 10px; }
    h1 { font-size: 18px; margin: 0; }
    h2 { font-size: 14px; margin: 0 0 8px; }
    .status { color: #a8c7dc; font-size: 12px; line-height: 1.35; }
    select, input, button { font: inherit; }
    select, input { width: 100%; background: #07111c; color: #edf7ff; border: 1px solid #315b80; border-radius: 3px; padding: 7px; }
    button { background: #17365a; color: #ecf7ff; border: 1px solid #2d71a8; padding: 7px 9px; cursor: pointer; border-radius: 3px; }
    button:hover { background: #214a76; }
    button.secondary { background: #10283f; }
    button.warn { background: #522027; border-color: #9a4652; }
    .row { display: flex; flex-wrap: wrap; gap: 6px; }
    .row > button { flex: 1 1 auto; }
    #list { overflow: auto; border: 1px solid #203a56; background: #07111c; }
    .item { padding: 8px; border-bottom: 1px solid #162c43; cursor: pointer; }
    .item:hover, .item.active { background: #10243a; }
    .item.variant { padding-left: 26px; background: #091725; border-left: 3px solid #315b80; }
    .item.variant strong::before { content: "Build variant: "; color: #7eb8dd; font-weight: 500; }
    .item strong { display: block; font-size: 13px; }
    .item span { display: block; color: #abc8dc; font-size: 11px; margin-top: 2px; }
    .panel { border: 1px solid #315b80; background: #081321; padding: 10px; min-width: 0; overflow: auto; }
    #workArea { min-width: 0; min-height: 0; display: grid; grid-template-columns: minmax(420px, 1.15fr) minmax(360px, 0.85fr); gap: 8px; }
    #previewPanel { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; gap: 8px; overflow: hidden; }
    #previewTools { display: flex; flex-wrap: wrap; gap: 6px; }
    #previewTools button { flex: 1 1 110px; }
    #viewport { position: relative; min-height: 0; border: 1px solid #1c3550; background: #050b12; overflow: hidden; }
    #previewCanvas { width: 100%; height: 100%; display: block; }
    #previewStatus { position: absolute; left: 10px; right: 10px; bottom: 10px; color: #cde7f7; background: rgba(5, 13, 22, 0.82); border: 1px solid #294c70; padding: 6px 8px; font-size: 12px; pointer-events: none; overflow-wrap: anywhere; }
    #previewMeta { color: #a8c7dc; font-size: 12px; min-height: 16px; overflow-wrap: anywhere; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 8px; }
    .metric { border: 1px solid #1c3550; background: #0b1a2a; padding: 8px; min-height: 62px; }
    .metric b { display: block; font-size: 12px; color: #9bc8e9; margin-bottom: 4px; }
    .metric span { overflow-wrap: anywhere; }
    #builderChatPanel { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; gap: 6px; overflow: hidden; }
    #log { white-space: pre-wrap; overflow: auto; font-size: 12px; }
    #builderMessage { flex: 1 1 360px; }
    @media (max-width: 1250px) { #app { grid-template-columns: 280px minmax(0, 1fr); } #workArea { grid-template-columns: 1fr; } .grid { grid-template-columns: repeat(2, minmax(180px, 1fr)); } }
  </style>
</head>
<body>
  <div id="app">
    <aside>
      <section>
        <h1>Avatar Builder Workspace</h1>
        <div class="status">No Home World, avatar runtime, AI chat, Ollama request, webcam, microphone, or voice model is started here. This local construction review assumes the exact subject and biological Robert only; it does not provide remote identity authentication, export permission, or resharing permission. Non-adult and uncertain subjects stay doll-safe.</div>
      </section>
      <section>
        <input id="filter" placeholder="Filter avatars..." autocomplete="off" />
      </section>
      <section id="list"></section>
    </aside>
    <main>
      <section class="panel">
        <div class="row">
          <select id="candidate"></select>
          <button id="prepare">Prepare Pipeline</button>
          <button id="brief">Build Brief</button>
          <button id="scanAssets" class="secondary">Scan Assets</button>
          <button id="refresh" class="secondary">Refresh</button>
        </div>
        <div class="row" style="margin-top: 8px;">
          <button id="openAvatar" class="secondary">Avatar Folder</button>
          <button id="openRefs" class="secondary">References</button>
          <button id="openDesktop" class="secondary">Desktop References</button>
          <button id="uploadRefs" class="secondary">Upload Pictures</button>
          <button id="openLibrary" class="secondary">Asset Library</button>
          <button id="openKiraGallery" class="secondary">Kira Review Gallery</button>
          <button id="close" class="warn">Close</button>
          <input id="referenceFiles" type="file" accept="image/*" multiple hidden />
        </div>
      </section>
      <section id="workArea">
        <section class="panel" id="previewPanel">
          <div class="row">
            <h2 id="previewTitle" style="flex: 1 1 220px;">3D Preview</h2>
            <div id="previewTools">
              <button id="frameBody" class="secondary">Body</button>
              <button id="frameHead" class="secondary">Head</button>
              <button id="frameFace" class="secondary">Face</button>
              <button id="inspectEyes" class="secondary">Eyes (asset)</button>
              <button id="toggleWire" class="secondary">Wire</button>
              <button id="toggleGuides" class="secondary">Guides</button>
            </div>
          </div>
          <div id="viewport">
            <canvas id="previewCanvas"></canvas>
            <div id="previewStatus">Select an avatar with a linked GLB.</div>
          </div>
          <div id="previewMeta"></div>
        </section>
        <section class="panel">
          <h2 id="title">Select an avatar</h2>
          <div class="grid" id="details"></div>
        </section>
      </section>
      <section class="panel" id="builderChatPanel">
        <div class="row">
          <h2 style="flex: 1 1 220px; margin: 0;">Avatar Builder Chat</h2>
          <button id="runBuilderPass" class="secondary">Run Builder Pass</button>
        </div>
        <div id="log"></div>
        <div class="row">
          <input id="builderMessage" placeholder="Tell Avatar Builder what is wrong: head too big, eyes outside sockets, wrong hair, adult/non-adult correction..." autocomplete="off" />
          <button id="sendBuilder">Send</button>
        </div>
      </section>
    </main>
  </div>
  <script type="importmap">
    {
      "imports": {
        "three": "/vendor/three/build/three.module.js",
        "three/addons/": "/vendor/three/examples/jsm/"
      }
    }
  </script>
  <script type="module">
    import * as THREE from "three";
    import { OrbitControls } from "three/addons/controls/OrbitControls.js";
    import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

    let state = {};
    const initialCandidate = new URLSearchParams(location.search).get("candidate") || "";
    const supersededCandidateRedirects = {
      "spider_gwen_adult_avatar_project_variant_20260716": "spider_gwen_spider_gwen_20260606_013325",
    };
    let selected = supersededCandidateRedirects[initialCandidate] || initialCandidate;
    const listEl = document.querySelector("#list");
    const candidateEl = document.querySelector("#candidate");
    const detailsEl = document.querySelector("#details");
    const titleEl = document.querySelector("#title");
    const logEl = document.querySelector("#log");
    const filterEl = document.querySelector("#filter");
    const canvas = document.querySelector("#previewCanvas");
    const viewport = document.querySelector("#viewport");
    const previewStatus = document.querySelector("#previewStatus");
    const previewMeta = document.querySelector("#previewMeta");
    const previewTitle = document.querySelector("#previewTitle");
    const builderMessageEl = document.querySelector("#builderMessage");
    const referenceFilesEl = document.querySelector("#referenceFiles");
    let renderer;
    let scene;
    let camera;
    let controls;
    let loader;
    let modelRoot;
    let previewEyeRoot;
    let overlayRoot;
    let guideRoot;
    let modelBox;
    let currentModelUrl = "";
    let currentAdjustmentKey = "";
    let previewLoadToken = 0;
    let frameMode = "body";
    let previewContentMode = "body";
    let wireEnabled = false;
    let guidesEnabled = true;

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }
    function log(line) {
      const stamp = new Date().toLocaleTimeString();
      logEl.textContent += `[${stamp}] ${line}\n`;
      logEl.scrollTop = logEl.scrollHeight;
    }
    function setPreviewStatus(text) {
      previewStatus.textContent = text;
    }
    function initPreview() {
      if (renderer) return;
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "low-power" });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.setClearColor(0x050b12, 1);
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(38, 1, 0.01, 500);
      camera.position.set(0, 1.45, 4.2);
      controls = new OrbitControls(camera, canvas);
      controls.enableDamping = true;
      controls.target.set(0, 1.0, 0);
      loader = new GLTFLoader();
      const hemi = new THREE.HemisphereLight(0xdff4ff, 0x1d2430, 2.0);
      scene.add(hemi);
      const key = new THREE.DirectionalLight(0xffffff, 2.4);
      key.position.set(2.2, 4.5, 3.5);
      scene.add(key);
      const fill = new THREE.DirectionalLight(0x9dc8ff, 0.9);
      fill.position.set(-3, 2, -2);
      scene.add(fill);
      const grid = new THREE.GridHelper(4, 16, 0x2c5b7a, 0x173047);
      grid.position.y = -0.01;
      scene.add(grid);
      guideRoot = new THREE.Group();
      scene.add(guideRoot);
      new ResizeObserver(resizePreview).observe(viewport);
      resizePreview();
      animatePreview();
    }
    function resizePreview() {
      if (!renderer || !camera) return;
      const rect = viewport.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    function clearPreview() {
      previewLoadToken += 1;
      if (modelRoot) {
        scene.remove(modelRoot);
        modelRoot.traverse(obj => {
          if (obj.geometry) obj.geometry.dispose?.();
          if (obj.material) {
            const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
            materials.forEach(mat => mat.dispose?.());
          }
        });
      }
      modelRoot = null;
      previewEyeRoot = null;
      modelBox = null;
      clearOverlay();
      clearGuides();
    }
    function clearOverlay() {
      if (!overlayRoot) return;
      scene.remove(overlayRoot);
      overlayRoot.traverse(obj => {
        obj.geometry?.dispose?.();
        obj.material?.dispose?.();
      });
      overlayRoot = null;
    }
    function clearGuides() {
      if (!guideRoot) return;
      while (guideRoot.children.length) {
        const child = guideRoot.children.pop();
        child.geometry?.dispose?.();
        child.material?.dispose?.();
      }
    }
    function applyWireframe() {
      if (!modelRoot) return;
      modelRoot.traverse(obj => {
        if (!obj.isMesh || !obj.material) return;
        const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
        materials.forEach(mat => { mat.wireframe = wireEnabled; });
      });
    }
    function addGuideLine(points, color = 0x48d1ff) {
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 });
      const line = new THREE.Line(geometry, material);
      guideRoot.add(line);
      return line;
    }
    function addFaceGuides(box, eyeObjects, item = {}) {
      clearGuides();
      if (!box) return;
      const adj = item.preview_adjustments || {};
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      box.getSize(size);
      box.getCenter(center);
      const eyeYRatio = Number(adj.eye_guide_y || 0.82);
      const eyeY = box.min.y + size.y * eyeYRatio;
      const mouthY = box.min.y + size.y * 0.72;
      const widthRatio = Number(adj.eye_guide_width || 0.32);
      const headHalf = Math.max(size.x * widthRatio * 0.5, 0.08);
      const frontZ = box.max.z + Math.max(size.z * 0.02, 0.015);
      addGuideLine([
        new THREE.Vector3(center.x - headHalf, eyeY, frontZ),
        new THREE.Vector3(center.x + headHalf, eyeY, frontZ),
      ], 0x49bfff);
      addGuideLine([
        new THREE.Vector3(center.x, eyeY + size.y * 0.06, frontZ),
        new THREE.Vector3(center.x, mouthY - size.y * 0.04, frontZ),
      ], 0xffd166);
      const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xff6b6b, transparent: true, opacity: 0.8 });
      for (const x of [-headHalf * 0.45, headHalf * 0.45]) {
        const marker = new THREE.Mesh(new THREE.RingGeometry(headHalf * 0.10, headHalf * 0.14, 24), markerMaterial.clone());
        marker.position.set(center.x + x, eyeY, frontZ + 0.002);
        marker.rotation.y = Math.PI;
        guideRoot.add(marker);
      }
      for (const obj of eyeObjects) {
        const helper = new THREE.BoxHelper(obj, 0x7df9ff);
        guideRoot.add(helper);
      }
      guideRoot.visible = guidesEnabled;
    }
    function applyBuilderPreviewAdjustments(item) {
      if (!modelRoot) return [];
      const applied = [];
      const adj = item.preview_adjustments || {};
      const headScale = Number(adj.head_scale || 1);
      if (Math.abs(headScale - 1) > 0.001) {
        const headNodes = [];
        modelRoot.traverse(obj => {
          const name = obj.name || "";
          if (/(^|[:_\\s.-])Head(_|\\b)|mixamorig[:_]?Head(?!Top)|\\bhead\\b/i.test(name) && !/HeadTop|headtop/i.test(name)) {
            headNodes.push(obj);
          }
        });
        if (headNodes.length) {
          for (const node of headNodes.slice(0, 2)) {
            node.scale.setScalar(headScale);
          }
          applied.push(`head scale ${headScale}`);
        } else {
          applied.push("head scale requested but no named head node found");
        }
      }
      const skinTone = String(item.preview_skin_tone || "").trim();
      if (skinTone) {
        const skinColor = new THREE.Color(skinTone);
        const exactPreR6Contract = item.preview_material_contract === "pre_r6_live_light_untextured_v1";
        modelRoot.traverse(obj => {
          if (!obj.isMesh || !obj.material) return;
          if (/(eye|eyelid|iris|pupil|sclera|catchlight)/i.test(obj.name || "")) return;
          const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
          materials.forEach(mat => {
            if (exactPreR6Contract) {
              for (const textureSlot of [
                "map", "normalMap", "roughnessMap", "metalnessMap", "aoMap",
                "emissiveMap", "bumpMap", "displacementMap", "alphaMap",
              ]) {
                if (textureSlot in mat) mat[textureSlot] = null;
              }
              if ("roughness" in mat) mat.roughness = 0.6;
              if ("metalness" in mat) mat.metalness = 0;
              mat.side = THREE.DoubleSide;
              mat.vertexColors = false;
              mat.transparent = false;
              mat.opacity = 1;
              mat.alphaTest = 0;
            }
            if (mat.color) mat.color.copy(skinColor);
            if (!exactPreR6Contract && "roughness" in mat) mat.roughness = Math.max(Number(mat.roughness || 0), 0.58);
            mat.needsUpdate = true;
          });
        });
        applied.push(exactPreR6Contract ? "pre-R6 live light material (untextured)" : "preview skin tone");
      }
      return applied;
    }
    function composeKiraPreviewEyeComponent(item, loadToken, bodyEyeObjects, applied) {
      const eyeUrl = String(item.preview_eye_component_url || "").trim();
      if (!eyeUrl || !item.preview_eye_component_valid || !item.preview_eye_component_display_enabled || !modelRoot) {
        return Promise.resolve({ eyeObjects: bodyEyeObjects, composed: false });
      }
      return new Promise(resolve => {
        loader.load(eyeUrl, gltf => {
          if (loadToken !== previewLoadToken || !modelRoot) {
            resolve({ eyeObjects: bodyEyeObjects, composed: false });
            return;
          }
          const eyeRoot = gltf.scene || gltf.scenes?.[0];
          if (!eyeRoot) {
            resolve({ eyeObjects: bodyEyeObjects, composed: false });
            return;
          }
          eyeRoot.name = "Kira Builder separate brown-eye preview component v3.2";
          eyeRoot.userData.builderPreviewOnly = true;
          eyeRoot.userData.sourceBodyModified = false;
          eyeRoot.userData.completeAdultAnatomyProof = false;
          applyKiraPreviewEyeFit(eyeRoot, item.preview_eye_component_fit || {});
          const eyeObjects = [];
          eyeRoot.traverse(obj => {
            if (/(eye|eyelid|iris|pupil|sclera|cornea|limbal)/i.test(obj.name || "")) eyeObjects.push(obj);
            if (!obj.isMesh) return;
            obj.frustumCulled = false;
            const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
            materials.filter(Boolean).forEach(mat => {
              mat.wireframe = wireEnabled;
              mat.needsUpdate = true;
            });
          });
          previewEyeRoot = eyeRoot;
          modelRoot.add(previewEyeRoot);
          modelRoot.updateMatrixWorld(true);
          applied.push("separate staged warm-brown eye component v3.2 (visual fit unapproved; preview only; R6 unchanged)");
          resolve({ eyeObjects: [...bodyEyeObjects, ...eyeObjects], composed: true });
        }, undefined, () => resolve({ eyeObjects: bodyEyeObjects, composed: false }));
      });
    }
    function applyKiraPreviewEyeFit(eyeRoot, requested = {}) {
      if (!eyeRoot) return false;
      const vertical = THREE.MathUtils.clamp(Number(requested.vertical_offset || 0), -0.03, 0.03);
      const forward = THREE.MathUtils.clamp(Number(requested.forward_offset || 0), -0.03, 0.03);
      const horizontal = THREE.MathUtils.clamp(Number(requested.horizontal_offset || 0), -0.03, 0.03);
      const commonHorizontal = THREE.MathUtils.clamp(Number(requested.common_horizontal_offset || 0), -0.01, 0.01);
      const diameterScale = THREE.MathUtils.clamp(Number(requested.diameter_scale || 1), 0.55, 1.10);
      for (const [name, sign] of [["KiraLeftEyePivot", -1], ["KiraRightEyePivot", 1]]) {
        const pivot = eyeRoot.getObjectByName(name);
        if (!pivot) continue;
        if (!Array.isArray(pivot.userData.builderPreviewBasePosition)) {
          pivot.userData.builderPreviewBasePosition = pivot.position.toArray();
        }
        if (!Array.isArray(pivot.userData.builderPreviewBaseScale)) {
          pivot.userData.builderPreviewBaseScale = pivot.scale.toArray();
        }
        pivot.position.fromArray(pivot.userData.builderPreviewBasePosition);
        pivot.scale.fromArray(pivot.userData.builderPreviewBaseScale).multiplyScalar(diameterScale);
        pivot.position.x += horizontal * sign + commonHorizontal;
        pivot.position.y += vertical;
        pivot.position.z += forward;
      }
      eyeRoot.updateMatrixWorld(true);
      eyeRoot.userData.builderPreviewFit = { vertical, forward, horizontal, commonHorizontal, diameterScale };
      return true;
    }
    function kiraPreviewEyeDiagnostics() {
      const names = [
        "KiraLeftEyePivot", "KiraRightEyePivot",
        "KiraLeftIris", "KiraRightIris",
        "KiraLeftPupil", "KiraRightPupil",
        "KiraLeftSclera", "KiraRightSclera",
      ];
      const nodes = {};
      for (const name of names) {
        const node = previewEyeRoot?.getObjectByName(name);
        if (!node) continue;
        const position = node.getWorldPosition(new THREE.Vector3());
        const box = new THREE.Box3().setFromObject(node);
        nodes[name] = {
          world: position.toArray(),
          bounds: { min: box.min.toArray(), max: box.max.toArray() },
        };
      }
      return {
        fit: previewEyeRoot?.userData?.builderPreviewFit || null,
        nodes,
        camera: camera ? camera.position.toArray() : null,
        target: controls ? controls.target.toArray() : null,
      };
    }
    function addNonAdultReviewGarment(box) {
      clearOverlay();
      if (!box) return;
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      box.getSize(size);
      box.getCenter(center);
      overlayRoot = new THREE.Group();
      scene.add(overlayRoot);
      const material = new THREE.MeshStandardMaterial({
        color: 0x244b78,
        roughness: 0.88,
        metalness: 0.02,
        transparent: false,
        depthTest: false,
      });
      const trimMaterial = new THREE.MeshStandardMaterial({
        color: 0x8fc7f0,
        roughness: 0.85,
        metalness: 0.01,
      });
      const torso = new THREE.Mesh(
        new THREE.BoxGeometry(Math.max(size.x * 0.48, 0.22), Math.max(size.y * 0.22, 0.22), Math.max(size.z * 0.44, 0.12)),
        material,
      );
      torso.position.set(center.x, box.min.y + size.y * 0.61, center.z);
      torso.renderOrder = 900;
      overlayRoot.add(torso);
      const shorts = new THREE.Mesh(
        new THREE.BoxGeometry(Math.max(size.x * 0.52, 0.24), Math.max(size.y * 0.11, 0.12), Math.max(size.z * 0.44, 0.12)),
        material.clone(),
      );
      shorts.position.set(center.x, box.min.y + size.y * 0.46, center.z);
      shorts.renderOrder = 901;
      overlayRoot.add(shorts);
      const collar = new THREE.Mesh(
        new THREE.TorusGeometry(Math.max(size.x * 0.14, 0.07), 0.008, 8, 36),
        trimMaterial,
      );
      collar.position.set(center.x, box.min.y + size.y * 0.74, center.z);
      collar.rotation.x = Math.PI / 2;
      collar.renderOrder = 902;
      overlayRoot.add(collar);
    }
    function framePreview(mode = frameMode) {
      if (!modelBox || !camera || !controls) return;
      frameMode = mode;
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      modelBox.getSize(size);
      modelBox.getCenter(center);
      const target = center.clone();
      let radius = Math.max(size.x, size.y, size.z) * 0.62;
      if (mode === "head") {
        target.y = modelBox.min.y + size.y * 0.80;
        radius = Math.max(size.x, size.y * 0.28, size.z) * 0.42;
      } else if (mode === "face") {
        // A real face-review framing is intentionally separate from the
        // broader head/torso view.  It makes both sockets large enough to
        // judge iris colour and seating instead of accepting metadata alone.
        target.y = modelBox.min.y + size.y * 0.885;
        radius = Math.max(size.x * 0.18, size.y * 0.12, size.z * 0.35) * 0.48;
      } else if (mode === "eyes") {
        // The isolated eye rig is only a few centimetres wide.  The normal
        // body-view minimum distance makes it almost invisible, so this
        // framing is deliberately component-scale.  It still does not seat
        // or compose the component with R6.
        radius = Math.max(size.x, size.y, size.z) * 0.72;
      }
      const minimumDistance = mode === "eyes" ? 0.055 : mode === "face" ? 0.32 : 0.7;
      const distance = Math.max(minimumDistance, radius / Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)));
      camera.near = Math.max(0.005, distance / 100);
      camera.far = Math.max(50, distance * 20);
      camera.position.set(target.x, target.y + radius * 0.05, modelBox.max.z + distance * 1.05);
      camera.updateProjectionMatrix();
      controls.target.copy(target);
      controls.update();
    }
    function loadPreview(item) {
      initPreview();
      previewContentMode = "body";
      const url = item.preview_model_url || "";
      const adjustmentKey = JSON.stringify({
        adjustments: item.preview_adjustments || {},
        skinTone: item.preview_skin_tone || "",
        materialContract: item.preview_material_contract || "",
        eyeComponent: item.preview_eye_component_url || "",
        eyeComponentSha256: item.preview_eye_component_sha256 || "",
        eyeComponentFit: item.preview_eye_component_fit || {},
      });
      previewTitle.textContent = item.label ? `3D Preview: ${item.label}` : "3D Preview";
      if (!url) {
        currentModelUrl = "";
        currentAdjustmentKey = "";
        clearPreview();
        previewMeta.textContent = "";
        setPreviewStatus("No linked local GLB for this avatar yet.");
        return;
      }
      if (url === currentModelUrl && adjustmentKey === currentAdjustmentKey && modelRoot) {
        framePreview(frameMode);
        return;
      }
      currentModelUrl = url;
      currentAdjustmentKey = adjustmentKey;
      clearPreview();
      const loadToken = previewLoadToken;
      setPreviewStatus(`Loading ${url}`);
      loader.load(url, gltf => {
        modelRoot = gltf.scene || gltf.scenes?.[0];
        if (!modelRoot) {
          setPreviewStatus("Model loaded without a scene.");
          return;
        }
        scene.add(modelRoot);
        modelBox = new THREE.Box3().setFromObject(modelRoot);
        const size = new THREE.Vector3();
        const center = new THREE.Vector3();
        modelBox.getSize(size);
        modelBox.getCenter(center);
        modelRoot.position.sub(center);
        modelBox = new THREE.Box3().setFromObject(modelRoot);
        const eyeObjects = [];
        const eyePattern = /(eye|eyelid|iris|pupil|sclera)/i;
        modelRoot.traverse(obj => {
          if (eyePattern.test(obj.name || "")) eyeObjects.push(obj);
          if (obj.isMesh) {
            obj.frustumCulled = false;
            if (obj.material) {
              const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
              materials.forEach(mat => {
                mat.wireframe = wireEnabled;
                mat.needsUpdate = true;
              });
            }
          }
        });
        const applied = applyBuilderPreviewAdjustments(item);
        modelBox = new THREE.Box3().setFromObject(modelRoot);
        const useReviewGarment = !item.anatomy_allowed && item.preview_adjustments?.non_adult_review_garment === true;
        if (useReviewGarment) addNonAdultReviewGarment(modelBox);
        else clearOverlay();
        composeKiraPreviewEyeComponent(item, loadToken, eyeObjects, applied).then(result => {
          if (loadToken !== previewLoadToken || !modelRoot) return;
          addFaceGuides(modelBox, result.eyeObjects, item);
          framePreview(frameMode);
          const bytes = item.preview_model_bytes ? `${(item.preview_model_bytes / 1024 / 1024).toFixed(1)} MB` : "";
          previewMeta.textContent = `${url} ${bytes} | eye-like nodes: ${result.eyeObjects.length ? result.eyeObjects.map(obj => obj.name || "(unnamed)").slice(0, 8).join(", ") : "none named"}${applied.length ? " | applied: " + applied.join(", ") : ""}`;
          setPreviewStatus(
            item.id === "kira" && result.composed
              ? "Loaded exact R6 body with a reversible separate staged brown-eye preview component. Visual fit is UNAPPROVED. Complete adult anatomy is NOT PROVEN."
              : item.id === "kira" && item.preview_eye_component_valid && !item.preview_eye_component_display_enabled
                ? "Loaded exact R6 body with the restored pre-R6 light material. The staged brown-eye component is hidden because its R6 eyelid/socket visual fit is UNAPPROVED. Complete adult anatomy is NOT PROVEN."
              : item.anatomy_allowed
                ? "Loaded."
                : useReviewGarment
                  ? "Loaded. Non-adult-safe review garment applied."
                  : "Loaded. Non-adult doll-safe preview; no anatomy overlay."
          );
        });
      }, undefined, err => {
        clearPreview();
        setPreviewStatus(`3D preview failed: ${err.message || err}`);
      });
    }
    function inspectEyeComponent(item) {
      initPreview();
      const eyeUrl = String(item.preview_eye_component_url || "").trim();
      previewTitle.textContent = item.label ? `Eye Component Review: ${item.label}` : "Eye Component Review";
      if (item.id !== "kira" || !eyeUrl || !item.preview_eye_component_valid) {
        currentModelUrl = "";
        currentAdjustmentKey = "";
        previewContentMode = "body";
        clearPreview();
        previewMeta.textContent = "";
        setPreviewStatus("No exact-hash-verified standalone eye component is available for this avatar.");
        return;
      }
      previewContentMode = "eyes";
      const isolatedKey = `isolated-eye:${item.preview_eye_component_sha256 || ""}`;
      if (currentModelUrl === eyeUrl && currentAdjustmentKey === isolatedKey && modelRoot) {
        framePreview("eyes");
        return;
      }
      currentModelUrl = eyeUrl;
      currentAdjustmentKey = isolatedKey;
      clearPreview();
      const loadToken = previewLoadToken;
      setPreviewStatus("Loading exact eye component in isolation...");
      loader.load(eyeUrl, gltf => {
        if (loadToken !== previewLoadToken || previewContentMode !== "eyes") return;
        modelRoot = gltf.scene || gltf.scenes?.[0];
        if (!modelRoot) {
          setPreviewStatus("Eye component loaded without a scene.");
          return;
        }
        modelRoot.name = "Kira standalone brown-eye asset inspection";
        modelRoot.userData.standaloneInspectionOnly = true;
        modelRoot.userData.seatedInR6 = false;
        modelRoot.userData.completeAdultAnatomyProof = false;
        scene.add(modelRoot);
        modelBox = new THREE.Box3().setFromObject(modelRoot);
        const center = modelBox.getCenter(new THREE.Vector3());
        modelRoot.position.sub(center);
        modelRoot.updateMatrixWorld(true);
        modelBox = new THREE.Box3().setFromObject(modelRoot);
        const namedEyeNodes = [];
        modelRoot.traverse(obj => {
          if (/(eye|iris|pupil|sclera|cornea|limbal)/i.test(obj.name || "")) namedEyeNodes.push(obj.name || "(unnamed)");
          if (!obj.isMesh || !obj.material) return;
          obj.frustumCulled = false;
          const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
          materials.filter(Boolean).forEach(mat => {
            mat.wireframe = wireEnabled;
            mat.needsUpdate = true;
          });
        });
        clearOverlay();
        clearGuides();
        framePreview("eyes");
        const digest = String(item.preview_eye_component_sha256 || "unknown hash");
        previewMeta.textContent = `${eyeUrl} | SHA-256 ${digest} | standalone component nodes: ${namedEyeNodes.slice(0, 12).join(", ") || "none named"}`;
        setPreviewStatus("Exact staged warm-brown eye component shown by itself. It is NOT seated in R6, NOT an approved body+eye fit, and does not modify Kira's body.");
      }, undefined, err => {
        if (loadToken !== previewLoadToken) return;
        clearPreview();
        setPreviewStatus(`Standalone eye-component preview failed: ${err.message || err}`);
      });
    }
    function showBodyFrame(mode) {
      const item = current();
      frameMode = mode;
      if (previewContentMode === "eyes") {
        currentModelUrl = "";
        currentAdjustmentKey = "";
        loadPreview(item);
        return;
      }
      framePreview(mode);
    }
    function animatePreview() {
      requestAnimationFrame(animatePreview);
      controls?.update();
      renderer?.render(scene, camera);
    }
    async function api(path, body) {
      const res = await fetch(path, {
        method: body ? "POST" : "GET",
        headers: body ? { "content-type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const text = await res.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (err) {
        throw new Error(`HTTP ${res.status}: ${text.slice(0, 700) || err.message}`);
      }
      if (!res.ok || data.ok === false) {
        throw new Error(data.message || data.error || text || `HTTP ${res.status}`);
      }
      return data;
    }
    function allItems() {
      return (state.candidates || []).flatMap(item => [item, ...(item.variants || [])]);
    }
    function current() {
      return allItems().find(item => item.id === selected) || allItems()[0] || {};
    }
    function renderList() {
      const filter = filterEl.value.trim().toLowerCase();
      const groups = (state.candidates || []).filter(item => {
        if (!filter) return true;
        if (`${item.label} ${item.id}`.toLowerCase().includes(filter)) return true;
        return (item.variants || []).some(variant => `${variant.label} ${variant.id}`.toLowerCase().includes(filter));
      });
      const row = (item, variant = false) => `
          <div class="item ${variant ? "variant" : ""} ${item.id === selected ? "active" : ""}" data-id="${esc(item.id)}">
            <strong>${esc(item.label)}</strong>
            <span>${esc(item.body_state || "NO_BODY")} | ${esc(item.component_production_state || item.pipeline_status)} | ${item.component_set_authored ? "components authored" : (item.preview_model_url ? "3D preview only" : "no authored body")} | ${item.reference_count || 0} refs</span>
          </div>`;
      listEl.innerHTML = groups.map(item => {
        const variants = (item.variants || []).filter(variant => !filter || `${item.label} ${item.id} ${variant.label} ${variant.id}`.toLowerCase().includes(filter));
        return row(item) + variants.map(variant => row(variant, true)).join("");
      }).join("");
      listEl.querySelectorAll(".item").forEach(node => node.onclick = () => {
        selected = node.dataset.id;
        candidateEl.value = selected;
        render();
      });
    }
    function metric(label, value) {
      return `<div class="metric"><b>${esc(label)}</b><span>${esc(value || "none")}</span></div>`;
    }
    function render() {
      if (!allItems().some(item => item.id === selected)) {
        selected = allItems()[0]?.id || "";
      }
      const item = current();
      if (!selected && item.id) selected = item.id;
      titleEl.textContent = item.label || "Select an avatar";
      candidateEl.innerHTML = (state.candidates || []).map(c => {
        const variants = (c.variants || []).map(variant => `<option value="${esc(variant.id)}">&#8627; Build variant: ${esc(variant.label)}</option>`).join("");
        return `<option value="${esc(c.id)}">${esc(c.label)}</option>${variants}`;
      }).join("");
      if (selected) candidateEl.value = selected;
      detailsEl.innerHTML = [
        metric("Candidate ID", item.id),
        metric("Workspace Record", item.is_build_variant ? "derived avatar build variant (not a second person)" : "canonical subject"),
        metric("Canonical Subject", item.canonical_subject_id || item.id),
        metric("Build Variants", item.is_build_variant ? "selected variant" : `${item.variant_count || 0} nested`),
        metric("Variant Boundary", item.variant_truth_note || (item.is_build_variant ? "Avatar authoring record only; no separate mind, voice, or activation." : "none")),
        metric("AI Type", item.ai_type),
        metric("Person / Body Type", item.person_body_type),
        metric("Body State", item.body_state),
        metric("Synthetic-Person Selector", item.included_in_synthetic_person_selector ? "included" : "not included"),
        metric("Active Synthetic Count", item.counts_as_active_synthetic_person ? "counted" : "not counted"),
        metric("Autonomous Life Loop", item.autonomous_life_loop_allowed ? "eligible" : "not eligible"),
        metric("Maturity Policy", item.maturity_class),
        metric("Adult Asset Policy", item.anatomy_allowed ? "allowed by age; this is not anatomy proof" : "blocked / non-adult safe"),
        metric("Selected Body Binding", item.id === "kira" ? `${item.runtime_body_selection_valid && item.runtime_body_profile_matches_selection ? "exact R6 live/profile match" : "FAIL CLOSED"} | ${item.runtime_body_selection_reason || "no selector"}` : "ordinary candidate state"),
        metric("Body Candidate Scope", item.id === "kira" ? (item.adult_external_form_trial ? "R6 adult external-form owner-review trial" : "not selected") : "candidate-specific"),
        metric("Complete Adult Anatomy", item.id === "kira" ? (item.complete_adult_anatomy_proven ? "proven" : "NOT PROVEN") : "not evaluated here"),
        metric("Body Truth", item.runtime_body_truth_note || "no bounded body-selection note"),
        metric("Eye Preview Component", item.id === "kira" ? (item.preview_eye_component_status || "not composed") : "not applicable"),
        metric("Eye Preview Render", item.id === "kira" ? (item.preview_eye_component_display_enabled ? "enabled for reversible review" : (item.preview_eye_component_fit_status || "disabled")) : "not applicable"),
        metric("Runtime Body", item.has_runtime_body ? item.runtime_model_status : "not linked"),
        metric("3D Preview", item.preview_model_url || "not linked"),
        metric("Builder Preview", item.builder_preview_model_url || "runtime model"),
        metric("Staged Review", item.staged_review_model_url || "none"),
        metric("Overlay Calibration", item.builder_overlay_calibration_model_url || "none"),
        metric("Silhouette Pass", item.silhouette_overlay_pass_manifest || "none"),
        metric("Builder School", item.avatar_builder_school_curriculum || "none"),
        metric("School Progress", item.avatar_builder_school_progress || "none"),
        metric("Subject School", item.avatar_builder_subject_school_status || "none"),
        metric("Subject Lesson", item.avatar_builder_subject_school_lesson || "none"),
        metric("Subject Progress", item.avatar_builder_subject_school_progress || "none"),
        metric("Subject Assignments", item.avatar_builder_subject_school_assignment_index || "none"),
        metric("Builder Status", `${item.builder_status || "unreviewed"} | ${item.build_target_count || 0} targets`),
        metric("Redo Job", item.redo_job_path || "not queued"),
        metric("Adult Redo Job", item.adult_redo_job_path || "not queued"),
        metric("Reference Audit", item.reference_visual_audit || "none"),
        metric("Chat Refs", item.chat_reference_batch || "none"),
        metric("Eye Plan", item.eye_rebuild_plan || "none"),
        metric("Wardrobe Plan", item.spandex_wardrobe_plan || "none"),
        metric("Adult Test Pair", item.paired_adult_test_candidate || "none"),
        metric("Pipeline", item.pipeline_status),
        metric("References", `${item.reference_count || 0} actual | ${item.pipeline_reference_count || 0} pipeline | ${item.downloaded_reference_count || 0} downloaded`),
        metric("Desktop Intake", item.desktop_reference_count || 0),
        metric("Pose Assets", `${item.ready_pose_count || 0}/${item.expected_pose_count || 0} ready`),
        metric("Generation Job", item.generation_job_status),
        metric("Picture-First Contract", `${item.reconstruction_contract_status || "not prepared"} | ${item.reconstruction_failure_count || 0} blockers | staging ${item.reconstruction_staging_allowed ? "allowed" : "blocked"}`),
        metric("Multiview Evidence", `${item.multiview_authoring_status || "not prepared"} | manifest hash ${item.multiview_manifest_hash_verified ? "verified" : "not verified"} | sources ${item.multiview_exact_hash_source_count || 0}/${item.multiview_source_count || 0} exact, ${item.multiview_reviewed_source_count || 0} reviewed`),
        metric("Multiview Manifest", item.multiview_manifest_path || "not prepared"),
        metric("View / Calibration", `front ${item.multiview_front_ready ? "ready" : "missing"} | depth ${item.multiview_depth_ready ? "ready" : "missing"} | full body ${item.multiview_full_body_ready ? "ready" : "missing"} | one frame ${item.multiview_calibration_ready ? "ready" : "missing"}`),
        metric("Landmarks / Scale / Base", `${item.multiview_landmark_count || 0} reviewed landmarks | ${item.multiview_missing_landmark_region_count || 0} regions missing | scale ${item.multiview_scale_ready ? "ready" : "missing"} | base ${item.multiview_base_ready ? "ready" : "missing"}`),
        metric("Likeness Author Queue", `${item.multiview_authoring_queue_ready ? "evidence ready" : "blocked"} | ${item.multiview_review_gap_count || 0} review gaps | ${item.multiview_integrity_failure_count || 0} integrity failures | backend ${item.multiview_author_backend_available ? "available" : "not installed"}`),
        metric("Body Production", `${item.component_production_state || "not planned"} | authored components ${item.component_set_authored ? "yes" : "no"}`),
        metric("Body Proof", `${item.body_private_review_ready ? "private review ready" : "not ready"} | ${item.body_blocker_count || 0} blockers | ${(item.body_blocker_categories || []).join(", ") || "none"}`),
        metric("Advanced Garment", `${item.advanced_garment_ready ? "ready" : "not ready"} | ${item.garment_blocker_count || 0} blockers | ${(item.garment_blocker_categories || []).join(", ") || "none"}`),
        metric("Next Production Action", item.component_next_action || "not planned"),
        metric("Component Plan", item.component_plan_path || "not planned"),
        metric("Avatar Folder", item.avatar_folder),
        metric("References Folder", item.references_folder),
        metric("Asset Library", `${state.asset_library?.asset_count || 0} indexed assets`),
        metric("Mode", "workspace only"),
      ].join("");
      renderList();
      loadPreview(item);
    }
    async function refresh() {
      state = await api("/api/state");
      if (!selected && state.candidates?.length) selected = state.candidates[0].id;
      render();
    }
    async function action(path, body, label) {
      try {
        log(`${label}...`);
        const result = await api(path, body);
        log(`${label}: ${result.message || "done"}`);
        if (result.output) log(JSON.stringify(result.output, null, 2));
        await refresh();
      } catch (err) {
        log(`${label} failed: ${err.message}`);
      }
    }
    async function sendBuilderMessage() {
      const message = builderMessageEl.value.trim();
      if (!message || !selected) return;
      builderMessageEl.value = "";
      try {
        log(`Robert: ${message}`);
        const result = await api("/api/builder-chat", { candidate: selected, message });
        log(`Avatar Builder: ${result.reply || result.message || "saved"}`);
        await refresh();
      } catch (err) {
        log(`Avatar Builder failed: ${err.message}`);
      }
    }
    function readReferenceFile(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve({
          name: file.name,
          type: file.type,
          size: file.size,
          data_url: String(reader.result || ""),
        });
        reader.onerror = () => reject(reader.error || new Error(`Could not read ${file.name}`));
        reader.readAsDataURL(file);
      });
    }
    function chooseReferenceUpload() {
      if (!selected) {
        log("Upload pictures failed: select an avatar first");
        return;
      }
      referenceFilesEl.value = "";
      referenceFilesEl.click();
    }
    async function uploadReferenceFiles() {
      const files = Array.from(referenceFilesEl.files || []);
      if (!files.length) return;
      try {
        log(`Uploading ${files.length} picture reference(s)...`);
        const payloadFiles = await Promise.all(files.map(readReferenceFile));
        const result = await api("/api/upload-references", { candidate: selected, files: payloadFiles });
        log(`Upload pictures: ${result.message || "saved"}`);
        if (result.output?.manifest) log(`Reference batch: ${result.output.manifest}`);
        await refresh();
      } catch (err) {
        log(`Upload pictures failed: ${err.message}`);
      } finally {
        referenceFilesEl.value = "";
      }
    }
    candidateEl.onchange = () => { selected = candidateEl.value; render(); };
    filterEl.oninput = renderList;
    document.querySelector("#prepare").onclick = () => action("/api/prepare", { candidate: selected }, "Prepare pipeline");
    document.querySelector("#brief").onclick = () => action("/api/brief", { candidate: selected }, "Build brief");
    document.querySelector("#scanAssets").onclick = () => action("/api/scan-assets", {}, "Scan avatar assets");
    document.querySelector("#refresh").onclick = refresh;
    document.querySelector("#openAvatar").onclick = () => action("/api/open-folder", { candidate: selected, kind: "avatar" }, "Open avatar folder");
    document.querySelector("#openRefs").onclick = () => action("/api/open-folder", { candidate: selected, kind: "references" }, "Open references folder");
    document.querySelector("#openDesktop").onclick = () => action("/api/open-folder", { kind: "desktop_references" }, "Open desktop references");
    document.querySelector("#uploadRefs").onclick = chooseReferenceUpload;
    referenceFilesEl.addEventListener("change", uploadReferenceFiles);
    document.querySelector("#openLibrary").onclick = () => action("/api/open-folder", { kind: "asset_library" }, "Open asset library");
    document.querySelector("#openKiraGallery").onclick = () => {
      if (selected !== "kira") {
        log("Kira Review Gallery is available only when Kira is selected.");
        return;
      }
      action("/api/open-folder", { candidate: selected, kind: "kira_owner_review_gallery" }, "Open Kira review gallery");
    };
    document.querySelector("#runBuilderPass").onclick = () => action("/api/run-builder-pass", { candidate: selected }, "Run builder pass");
    document.querySelector("#sendBuilder").onclick = sendBuilderMessage;
    builderMessageEl.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendBuilderMessage();
      }
    });
    document.querySelector("#frameBody").onclick = () => showBodyFrame("body");
    document.querySelector("#frameHead").onclick = () => showBodyFrame("head");
    document.querySelector("#frameFace").onclick = () => showBodyFrame("face");
    document.querySelector("#inspectEyes").onclick = () => inspectEyeComponent(current());
    document.querySelector("#toggleWire").onclick = () => { wireEnabled = !wireEnabled; applyWireframe(); };
    document.querySelector("#toggleGuides").onclick = () => { guidesEnabled = !guidesEnabled; if (guideRoot) guideRoot.visible = guidesEnabled; };
    document.querySelector("#close").onclick = async () => { await api("/api/safe-close", { reason: "Robert closed Avatar Builder Workspace" }); window.close(); };
    initPreview();
    // Local review diagnostics.  The setter affects only the separately
    // composed preview-eye component and never writes either source GLB.
    window.__avatarBuilderPreviewDebug = {
      eyeDiagnostics: () => kiraPreviewEyeDiagnostics(),
      setKiraEyeFit: fit => applyKiraPreviewEyeFit(previewEyeRoot, fit || {}),
    };
    refresh().catch(err => log(err.message));
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AvatarBuilderWorkspace/1.0"

    def log_message(self, fmt: str, *args) -> None:
        with LOG_LOCK:
            print(f"[{now_stamp()}] {fmt % args}")

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("content-length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def _file(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self._json(404, {"ok": False, "message": "File not found"})
            return
        self.send_response(200)
        self.send_header("content-type", content_type_for(path))
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            page = html()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        static_path = static_path_for_request(path)
        if static_path:
            self._file(static_path)
            return
        if path == "/api/state":
            candidates = [candidate_record(candidate_id) for candidate_id in candidate_ids()]
            self._json(200, {
                "ok": True,
                "mode": "avatar_builder_workspace",
                "active_label": "",
                "world_url": "",
                "avatar_url": "",
                "candidates": candidates,
                "asset_library": asset_library_summary(),
                "last": load_state(),
            })
            return
        self._json(404, {"ok": False, "message": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._body()
        candidate_id = normalize_workspace_candidate_id(
            str(body.get("candidate") or "").strip()
        )
        try:
            if path == "/api/prepare":
                if not candidate_id:
                    self._json(400, {"ok": False, "message": "Missing candidate"})
                    return
                output = prepare_candidate_avatar_pipeline(
                    candidate_id,
                    load_profile(candidate_id),
                    desktop_reference_root=desktop_reference_root(),
                )
                result = {"ok": True, "message": f"Prepared {candidate_id}", "output": output}
                save_action("prepare", result)
                self._json(200, result)
                return
            if path == "/api/brief":
                if not candidate_id:
                    self._json(400, {"ok": False, "message": "Missing candidate"})
                    return
                output = create_brief(candidate_id)
                result = {"ok": True, "message": f"Created brief for {candidate_id}", "output": output}
                save_action("brief", result)
                self._json(200, result)
                return
            if path == "/api/scan-assets":
                manifest = build_avatar_asset_library(copy_assets=False)
                report = run_hair_style_trials(manifest)
                learning_plans = write_avatar_builder_learning_plans(manifest)
                output = {
                    "asset_count": manifest.get("asset_count", 0),
                    "categories": manifest.get("categories", {}),
                    "manifest": "Avatar/avatar_builder/asset_library/manifest.json",
                    "hair_trials": rel(hair_trial_report_path()),
                    "learning_plans": learning_plans,
                    "hair_grades": {
                        key: value.get("grade")
                        for key, value in (report.get("trials") or {}).items()
                        if isinstance(value, dict)
                    },
                    "copy_assets": False,
                }
                result = {"ok": True, "message": "Scanned avatar assets without copying models", "output": output}
                save_action("scan_assets", result)
                self._json(200, result)
                return
            if path == "/api/run-builder-pass":
                if not candidate_id:
                    self._json(400, {"ok": False, "message": "Missing candidate"})
                    return
                output = run_builder_review(candidate_id, load_profile(candidate_id))
                if not output.get("ok", False):
                    self._json(409, {
                        "ok": False,
                        "status": output.get("status") or "blocked_maturity_identity_policy",
                        "message": output.get("message") or "Avatar Builder review was blocked",
                        "output": output,
                    })
                    return
                if candidate_id.strip().lower() == NORMAL_MARINETTE_CANDIDATE_ID:
                    output["redo_job"] = create_avatar_redo_job(
                        candidate_id,
                        str(body.get("adult_test_candidate") or "spider_gwen_spider_gwen_20260606_013325"),
                        "Robert requested a Marinette redo because the current hair, head shape, and body shape failed review.",
                    )
                result = {"ok": True, "message": f"Ran Avatar Builder pass for {candidate_id}", "output": output}
                save_action("run_builder_pass", result)
                self._json(200, result)
                return
            if path == "/api/upload-references":
                if not candidate_id:
                    self._json(400, {"ok": False, "message": "Missing candidate"})
                    return
                files = body.get("files")
                output = save_uploaded_references(candidate_id, files if isinstance(files, list) else [])
                result = {
                    "ok": True,
                    "message": f"Saved {len(output.get('saved', []))} picture reference(s) for {candidate_id}",
                    "output": output,
                }
                save_action("upload_references", result)
                self._json(200, result)
                return
            if path == "/api/builder-chat":
                if not candidate_id:
                    self._json(400, {"ok": False, "message": "Missing candidate"})
                    return
                message = str(body.get("message") or "").strip()
                if not message:
                    self._json(400, {"ok": False, "message": "Missing message"})
                    return
                output = avatar_builder_chat(candidate_id, message, load_profile(candidate_id))
                if not output.get("ok", False):
                    result = {
                        "ok": False,
                        "status": output.get("status") or "blocked_maturity_identity_policy",
                        "message": "Avatar Builder blocked the incompatible maturity change",
                        "reply": output.get("reply", ""),
                        "output": output,
                    }
                    self._json(409, result)
                    return
                result = {
                    "ok": True,
                    "message": "Avatar Builder saved the correction",
                    "reply": output.get("reply", ""),
                    "output": output,
                }
                save_action("builder_chat", result)
                self._json(200, result)
                return
            if path == "/api/open-folder":
                kind = str(body.get("kind") or "").strip()
                if kind == "avatar" and candidate_id:
                    result = open_path(AVATAR_TEMP_DIR / candidate_id)
                elif kind == "references" and candidate_id:
                    result = open_path(AVATAR_TEMP_DIR / candidate_id / "references")
                elif kind == "desktop_references":
                    result = open_path(desktop_reference_root())
                elif kind == "asset_library":
                    result = open_path(AVATAR_BUILDER_DIR)
                elif (
                    kind == "kira_owner_review_gallery"
                    and candidate_id == "kira"
                    and KIRA_CURRENT_OWNER_REVIEW_GALLERY.is_file()
                ):
                    result = open_path(KIRA_CURRENT_OWNER_REVIEW_GALLERY)
                else:
                    self._json(400, {"ok": False, "message": "Unknown folder target"})
                    return
                self._json(200, {"ok": True, "message": "Opened folder", "output": result})
                return
            if path == "/api/safe-close":
                self._json(200, {"ok": True, "message": "Avatar Builder Workspace closing"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
        except AvatarMaturityPolicyError as exc:
            self._json(409, {
                "ok": False,
                "status": "blocked_maturity_identity_policy",
                "message": str(exc),
                "policy_validation": exc.validation,
            })
            return
        except Exception as exc:
            self._json(500, {"ok": False, "message": str(exc)})
            return
        self._json(404, {"ok": False, "message": "Not found"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Lightweight Avatar Builder Workspace server.")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Avatar Builder Workspace running at http://127.0.0.1:{PORT}/")
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
