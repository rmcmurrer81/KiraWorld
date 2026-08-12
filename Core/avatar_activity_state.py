"""Shared action state for the local 3D avatar runtime."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = PROJECT_ROOT / "Avatar" / "state" / "temp_ai"


def _web_path(path: Path) -> str:
    return "/" + path.relative_to(PROJECT_ROOT).as_posix()


def _selected_runtime_model(candidate_id: str) -> Path | None:
    """Return the exact model an activity-state write is allowed to bind.

    Kira's reversible R6 review uses an independently hash-bound selector.  A
    life-loop/activity update must not rediscover the older generic
    ``Avatar/models/temp_ai/kira/avatar.glb`` and silently undo that binding.
    Other candidates retain the ordinary discovery behavior.
    """

    if candidate_id.lower() != "kira":
        return discover_rigged_model(candidate_id)
    try:
        # Import locally so the shared activity writer remains usable without
        # imposing Kira's review-selection module on other candidates.
        from Core.kira_runtime_body_selection import resolve_kira_runtime_body_path

        selected = resolve_kira_runtime_body_path(PROJECT_ROOT).resolve(strict=True)
        selected.relative_to(PROJECT_ROOT.resolve(strict=True))
        return selected if selected.is_file() else None
    except (OSError, ValueError, KeyError, TypeError):
        # Kira fails closed: do not substitute the older discovered body.
        return None


def discover_rigged_model(candidate_id: str) -> Path | None:
    roots = (
        PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "generated_body",
        PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / candidate_id,
    )
    preferred_names = ("avatar.glb", "model.glb", "avatar.gltf", "model.gltf")
    for root in roots:
        for name in preferred_names:
            path = root / name
            if path.exists():
                return path
    for root in roots:
        if root.exists():
            for pattern in ("*.glb", "*.gltf"):
                match = next(root.rglob(pattern), None)
                if match:
                    return match
    return None


def discover_outfit_catalog(candidate_id: str) -> Path | None:
    reference_root = PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "references"
    if not reference_root.exists():
        return None
    catalogs = sorted(reference_root.rglob("outfit_catalog.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return catalogs[0] if catalogs else None


def discover_pose_manifest(candidate_id: str) -> Path | None:
    manifest = (
        PROJECT_ROOT
        / "Avatar"
        / "temp_ai"
        / candidate_id
        / "generated_body"
        / "avatar_body_manifest.json"
    )
    if not manifest.exists():
        return None
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("status") != "pose_assets_ready":
        return None
    forms = payload.get("forms")
    if not isinstance(forms, dict):
        return None
    for form in forms.values():
        if not isinstance(form, dict):
            continue
        poses = form.get("poses")
        if not isinstance(poses, dict):
            continue
        for pose in poses.values():
            if not isinstance(pose, dict) or pose.get("status") != "ready":
                continue
            raw_path = str(pose.get("file") or "")
            if not raw_path:
                continue
            pose_path = Path(raw_path)
            if not pose_path.is_absolute():
                pose_path = PROJECT_ROOT / pose_path
            if pose_path.exists():
                return manifest
    return None


def infer_avatar_action(activity: str) -> str:
    text = (activity or "").lower()
    rules = (
        ("persistent_read", ("read_for_hours", "persistent read", "keep reading", "read all day")),
        ("creative_write", ("creative_write", "creative writing", "write on the tablet")),
        ("take_notes", ("take_notes", "leave a message", "write a note")),
        ("lie_on_couch", ("lie_on_couch", "rest on the couch", "lie on the couch")),
        ("use_computer", ("computer", "code", "program", "research online", "write email")),
        ("read_magazine", ("magazine", "fashion", "lookbook")),
        ("read_book", ("read", "book", "script", "study")),
        ("sit", ("rest", "reflect", "diary", "journal", "write")),
        ("walk", ("patrol", "walk", "pace", "explore")),
        ("wave", ("greet", "hello", "welcome")),
        ("talking", ("talking", "speaking", "chatting")),
    )
    for action, terms in rules:
        if any(term in text for term in terms):
            return action
    return "idle"


def infer_form(activity: str, suggested_form: str = "") -> str:
    combined = f"{suggested_form} {activity}".lower()
    if any(term in combined for term in ("ladybug", "hero", "supergirl", "patrol")):
        return "hero"
    if any(term in combined for term in ("pajama", "pyjama", "sleep", "bedtime", "nightwear")):
        return "sleepwear"
    return "civilian"


def write_avatar_activity_state(
    candidate_id: str,
    activity: str,
    suggested_form: str = "",
    source: str = "life_loop",
    mood: str = "calm",
    metadata: dict[str, Any] | None = None,
    action_override: str = "",
) -> Path:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    path = STATE_ROOT / f"{candidate_id}.json"
    model_path = _selected_runtime_model(candidate_id)
    outfit_catalog = discover_outfit_catalog(candidate_id)
    pose_manifest = discover_pose_manifest(candidate_id)
    payload = {
        "schema_version": 2,
        "candidate_id": candidate_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "action": re.sub(r"[^a-z0-9_\-]", "", action_override.lower()) if action_override else infer_avatar_action(activity),
        "activity": re.sub(r"\s+", " ", activity).strip(),
        "form": infer_form(activity, suggested_form),
        "mood": mood,
        "source": source,
        "model_status": (
            "rigged_model_ready"
            if model_path
            else "generated_pose_preview"
            if pose_manifest
            else "awaiting_avatar_assets"
        ),
        "model_url": _web_path(model_path) if model_path else "",
        "pose_manifest_url": _web_path(pose_manifest) if pose_manifest else "",
        "outfit_catalog_url": _web_path(outfit_catalog) if outfit_catalog else "",
        "metadata": metadata or {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
