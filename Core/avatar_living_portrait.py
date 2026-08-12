"""Small, deterministic helpers for TemporaryAI living portrait previews."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POSE_ORDER = (
    "neutral",
    "look_left",
    "look_right",
    "wave_1",
    "wave_2",
    "talking",
)

MOTION_POSES = {
    "idle": ("neutral", "neutral", "look_left", "neutral", "look_right", "neutral"),
    "greeting": ("wave_1", "wave_2", "wave_1", "wave_2", "neutral"),
    "talking": ("neutral", "talking", "neutral", "talking"),
}


def infer_emotion(text: str) -> str:
    lowered = text.lower()
    scores = {
        "joy": sum(lowered.count(word) for word in ("happy", "glad", "love", "wonderful", "great", "smile")),
        "excited": sum(lowered.count(word) for word in ("excited", "amazing", "can't wait", "idea!", "yes!")),
        "concern": sum(lowered.count(word) for word in ("worried", "concern", "careful", "problem", "afraid")),
        "sad": sum(lowered.count(word) for word in ("sad", "sorry", "lonely", "hurt", "miss you")),
    }
    emotion, score = max(scores.items(), key=lambda item: item[1])
    return emotion if score else "calm"


def begins_with_greeting(text: str) -> bool:
    return bool(re.match(r"^\s*(hi|hello|hey|good morning|good afternoon|good evening|i[' ]?m glad to see you)\b", text, re.I))


def speaking_seconds(text: str) -> float:
    words = len(re.findall(r"\b\w+\b", text))
    return max(1.5, min(24.0, words / 2.6))


def avatar_body_root(candidate_id: str) -> Path:
    return PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "generated_body"


def avatar_body_manifest_path(candidate_id: str) -> Path:
    return avatar_body_root(candidate_id) / "avatar_body_manifest.json"


def visual_forms(profile: dict[str, Any]) -> list[str]:
    raw_forms = (profile.get("visual_identity", {}) or {}).get("forms", {})
    if isinstance(raw_forms, dict):
        forms = [str(item) for item in raw_forms]
    elif isinstance(raw_forms, list):
        forms = [
            str(item.get("id") or item.get("label"))
            for item in raw_forms
            if isinstance(item, dict) and (item.get("id") or item.get("label"))
        ]
    else:
        forms = []
    return [item.lower() for item in forms] or ["default"]


def ensure_avatar_body_manifest(candidate_id: str, profile: dict[str, Any]) -> Path:
    """Create the generated-body contract without pretending a rig exists."""
    body_root = avatar_body_root(candidate_id)
    manifest_path = avatar_body_manifest_path(candidate_id)
    body_root.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    forms: dict[str, Any] = existing.get("forms", {}) if isinstance(existing.get("forms"), dict) else {}
    for form in visual_forms(profile):
        form_dir = body_root / form
        form_dir.mkdir(parents=True, exist_ok=True)
        pose_map = forms.setdefault(form, {}).setdefault("poses", {})
        for pose in POSE_ORDER:
            expected = form_dir / f"{pose}.png"
            current = pose_map.get(pose, {}) if isinstance(pose_map.get(pose), dict) else {}
            current_path = Path(str(current.get("file", ""))) if current.get("file") else expected
            if not current_path.is_absolute():
                current_path = PROJECT_ROOT / current_path
            pose_map[pose] = {
                "status": "ready" if current_path.exists() else "needed",
                "file": str(current_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            }

    ready_count = sum(
        1
        for form_data in forms.values()
        for pose_data in (form_data.get("poses", {}) or {}).values()
        if isinstance(pose_data, dict) and pose_data.get("status") == "ready"
    )
    expected_count = max(1, len(forms) * len(POSE_ORDER))
    coverage_status = (
        "complete" if ready_count >= expected_count else "partial" if ready_count else "none"
    )
    manifest = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pose_assets_ready" if ready_count else "awaiting_generated_pose_assets",
        "asset_type": "generated_full_body_pose_set",
        "coverage_status": coverage_status,
        "ready_pose_count": ready_count,
        "expected_pose_count": expected_count,
        "review_status": existing.get("review_status", "unreviewed"),
        "rigged_3d_body_ready": False,
        "pose_sheet_layout": {
            "columns": 3,
            "rows": 2,
            "order": list(POSE_ORDER),
        },
        "forms": forms,
        "motion_policy": {
            "starting_pose": "neutral",
            "idle": "occasionally look left or right; keep feet planted",
            "greeting": "alternate wave_1 and wave_2, then return to neutral",
            "talking": "alternate neutral and talking; future upgrade adds visemes",
        },
        "truth_note": "These are generated 2D pose images, not a reviewed likeness or a rigged 3D body. The UI only claims motions for poses that exist.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def resolve_avatar_pose_paths(
    candidate_id: str,
    profile: dict[str, Any],
    form: str = "auto",
) -> tuple[str, dict[str, Path]]:
    """Return the best available form and its real pose frames.

    A requested hero/civilian form may not be generated yet. In that case the
    live window should show another completed form instead of going blank.
    """
    manifest_path = ensure_avatar_body_manifest(candidate_id, profile)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    forms = manifest.get("forms", {}) if isinstance(manifest.get("forms"), dict) else {}
    requested = form.lower()
    preferred = str((profile.get("visual_identity", {}) or {}).get("preferred_chat_form", "")).lower()
    first_choice = preferred if requested == "auto" and preferred in forms else requested

    choices: list[str] = []
    for choice in (first_choice, "civilian", "default", "hero", *forms.keys()):
        if choice in forms and choice not in choices:
            choices.append(choice)

    for wanted in choices:
        pose_map = (forms.get(wanted, {}) or {}).get("poses", {}) or {}
        ready: dict[str, Path] = {}
        for pose, item in pose_map.items():
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("file", "")))
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if path.exists():
                ready[str(pose)] = path
        if ready:
            return wanted, ready
    return first_choice if first_choice in forms else next(iter(forms), "default"), {}


def load_avatar_pose_paths(candidate_id: str, profile: dict[str, Any], form: str = "auto") -> dict[str, Path]:
    _resolved_form, paths = resolve_avatar_pose_paths(candidate_id, profile, form)
    return paths


def pose_for_motion(motion: str, tick: int, available: set[str]) -> str:
    sequence = MOTION_POSES.get(motion, MOTION_POSES["idle"])
    desired = sequence[(tick // 5) % len(sequence)]
    if desired in available:
        return desired
    if "neutral" in available:
        return "neutral"
    return next(iter(sorted(available)), "")


def ensure_avatar_build_plan(candidate_id: str, profile: dict[str, Any], references: list[dict[str, Any]]) -> Path:
    avatar_root = PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id
    plan_path = avatar_root / "avatar_build_plan.json"
    avatar_root.mkdir(parents=True, exist_ok=True)
    required = []
    forms = visual_forms(profile)
    views = ["head_front", "head_left_three_quarter", "head_right_three_quarter", "head_left_profile", "head_right_profile", "full_body_front", "full_body_side"]
    for form in forms:
        for view in views:
            required.append({"form": form, "view": view, "status": "needed", "reference_files": []})
    for reference in references:
        raw = str(reference.get("local_file", ""))
        if not raw:
            continue
        form = str(reference.get("form", "unknown")).lower()
        view = str(reference.get("view", "unknown")).lower()
        if reference.get("full_body_reviewed") or view == "full_body":
            view = "full_body_front"
        for item in required:
            if item["form"] == form and item["view"] == view:
                item["status"] = "reference_available"
                item["reference_files"].append(raw)
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "goal": "An identity-reviewed, articulated civilian/hero avatar with idle, greeting, talking, and emotion motion.",
        "current_preview": "The UI prefers generated 2D full-body pose assets when available and otherwise falls back to a reference still. It is not yet a rigged 3D body or true lip sync.",
        "required_reference_views": required,
        "motion_targets": ["idle_breathing", "hello_wave", "talking", "joy", "excitement", "concern", "sadness"],
        "generated_body_manifest": str(avatar_body_manifest_path(candidate_id).relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "future_pipeline": ["review multi-angle references", "generate a consistent six-pose sheet", "review pose identity", "create/rig avatar", "map emotion states", "add phoneme or viseme lip sync"],
    }
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    ensure_avatar_body_manifest(candidate_id, profile)
    return plan_path
