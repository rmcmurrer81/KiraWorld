"""Read-only registration gate for completed Temporary Creator people.

The creator may prepare many draft workspaces.  Existing conversation and world
surfaces must not discover those drafts.  This module exposes a person only
after one readiness record binds every reviewed result, the final founder
activation decision, capacity evidence, and the exact profile/runtime files.

Registration is deliberately read-only.  It neither builds nor activates a
person and it cannot promote a temporary person to permanent status.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from Core.temporary_creator_person_pipeline import (
    _validate_v4_evidence as validate_v4_evidence,
)


READINESS_KIND = "temporary_creator_shared_person_readiness_v1"
MANIFEST_KIND = "temporary_creator_shared_person_manifest_v1"
REGISTRY_KIND = "temporary_creator_existing_surface_registry_v1"

SURFACE_KEYS = frozenset({"kira_text_voice_chat", "kira_world_shell"})
EVIDENCE_KEYS = frozenset(
    {
        "v4_static_gate_ready",
        "mind_knowledge_reviewed_result",
        "avatar_builder_reviewed_result",
        "voice_generator_reviewed_result",
        "final_founder_activation_review",
        "ram_capacity_verified",
        "residency_capacity_verified",
    }
)
RESULT_BINDING_KINDS = {
    "mind_knowledge": "temporary_creator_mind_knowledge_reviewed_result_v1",
    "avatar_builder": "temporary_creator_avatar_builder_reviewed_result_v1",
    "voice_generator": "temporary_creator_voice_generator_reviewed_result_v1",
    "final_activation": "temporary_creator_final_activation_review_v1",
    "ram_capacity": "temporary_creator_ram_capacity_evidence_v1",
    "residency_capacity": "temporary_creator_residency_capacity_evidence_v1",
    "activation_receipt": "temporary_creator_activation_receipt_v1",
    "residency_receipt": "temporary_creator_residency_receipt_v1",
}
PACKAGE_BINDING_KEYS = frozenset({"candidate_profile", "avatar_runtime_state"})
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _load_object(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_path(root: Path, raw: object) -> Path | None:
    value = _text(raw).replace("\\", "/")
    pure = PurePosixPath(value)
    if (
        not value
        or pure.is_absolute()
        or value != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or ":" in pure.parts[0]
    ):
        return None
    try:
        root_resolved = root.resolve(strict=True)
        path = (root_resolved / Path(*pure.parts)).resolve(strict=True)
        path.relative_to(root_resolved)
    except (OSError, ValueError):
        return None
    current = path
    while True:
        if current.is_symlink():
            return None
        if current == root_resolved:
            break
        if current == current.parent:
            return None
        current = current.parent
    return path if path.is_file() else None


def _bound_object(
    root: Path,
    binding: object,
    *,
    expected_kind: str | None,
    person_id: str,
) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(binding, Mapping):
        return None, "binding_missing"
    relative = _text(binding.get("relative_path")).replace("\\", "/")
    expected_hash = _text(binding.get("sha256")).casefold()
    if SHA_RE.fullmatch(expected_hash) is None:
        return None, "binding_hash_invalid"
    path = _safe_relative_path(root, relative)
    if path is None:
        return None, "binding_path_invalid"
    try:
        actual_hash = _hash_file(path)
    except OSError:
        return None, "binding_file_unreadable"
    if actual_hash != expected_hash:
        return None, "binding_hash_mismatch"
    value = _load_object(path)
    if value is None:
        return None, "binding_json_invalid"
    if _text(value.get("person_id") or value.get("candidate_id")).casefold() != person_id:
        return None, "binding_person_mismatch"
    if expected_kind is not None and _text(value.get("record_kind")) != expected_kind:
        return None, "binding_kind_mismatch"
    return value, ""


def _ready_result_record(key: str, value: Mapping[str, Any]) -> bool:
    if _text(value.get("status")).casefold() != "ready":
        return False
    if key == "mind_knowledge":
        return value.get("reviewed_ready") is True and value.get("mind_knowledge_built") is True
    if key == "avatar_builder":
        return (
            value.get("reviewed_ready") is True
            and value.get("avatar_runtime_ready") is True
            and value.get("body_created") is True
        )
    if key == "voice_generator":
        return (
            value.get("reviewed_ready") is True
            and value.get("voice_runtime_ready") is True
            and value.get("voice_assigned") is True
            and value.get("v4_static_gate_ready") is True
        )
    if key == "final_activation":
        reviewer = value.get("reviewed_by")
        return (
            value.get("approved") is True
            and isinstance(reviewer, Mapping)
            and _text(reviewer.get("authority_class")).casefold() == "founder"
            and reviewer.get("authenticated") is True
        )
    if key in {"ram_capacity", "residency_capacity"}:
        return value.get("verified") is True and value.get("sufficient") is True
    if key == "activation_receipt":
        return value.get("activation_performed") is True
    if key == "residency_receipt":
        return (
            value.get("residency_record_created") is True
            and value.get("person_present_in_kira_world") is True
        )
    return False


def _workspace_record(project_root: Path, workspace: Path) -> tuple[str, dict[str, Any] | None]:
    manifest = _load_object(workspace / "person_manifest.json")
    readiness = _load_object(workspace / "shared_person_readiness.json")
    if manifest is None:
        return "", None
    person_id = _text(manifest.get("person_id")).casefold()
    if ID_RE.fullmatch(person_id) is None:
        return "", None
    if readiness is None:
        return person_id, None
    if (
        manifest.get("schema_version") != 1
        or readiness.get("schema_version") != 1
        or _text(manifest.get("record_kind")) != MANIFEST_KIND
        or _text(readiness.get("record_kind")) != READINESS_KIND
        or _text(readiness.get("person_id")).casefold() != person_id
        or _text(readiness.get("bundle_id")) != _text(manifest.get("bundle_id"))
    ):
        return person_id, None
    if (
        _text(readiness.get("status")).casefold() != "ready"
        or readiness.get("ready_for_existing_surface_registration") is not True
        or readiness.get("draft_or_failed_people_must_remain_hidden") is not True
        or readiness.get("activation_allowed") is not True
        or readiness.get("person_present_in_kira_world") is not True
        or readiness.get("permanent_promotion_allowed") is not False
        or manifest.get("temporary_by_default") is not True
        or manifest.get("activation_allowed") is not True
        or manifest.get("person_present_in_kira_world") is not True
        or manifest.get("permanent_promotion_allowed") is not False
    ):
        return person_id, None

    surfaces = readiness.get("existing_surfaces")
    if not isinstance(surfaces, Mapping) or set(surfaces) != SURFACE_KEYS:
        return person_id, None
    for surface in SURFACE_KEYS:
        row = surfaces.get(surface)
        if (
            not isinstance(row, Mapping)
            or set(row) != {"discoverable", "registration_performed"}
            or row.get("discoverable") is not True
            or row.get("registration_performed") is not True
        ):
            return person_id, None

    exact = readiness.get("required_exact_result_evidence")
    if not isinstance(exact, Mapping) or set(exact) != EVIDENCE_KEYS:
        return person_id, None
    if any(exact.get(key) is not True for key in EVIDENCE_KEYS):
        return person_id, None

    subject_or_domain = _text(manifest.get("subject_or_domain"))
    creator_type = _text(manifest.get("creator_type")).casefold()
    display_name = _text(manifest.get("display_name"))
    if not subject_or_domain or not display_name:
        return person_id, None
    v4_evidence = readiness.get("v4_evidence")
    if not isinstance(v4_evidence, Mapping):
        return person_id, None
    try:
        v4_summary, v4_blockers = validate_v4_evidence(
            project_root,
            v4_evidence,
            {
                "person_id": person_id,
                "display_name": display_name,
                "creator_type": creator_type,
                "subject_or_domain": subject_or_domain,
            },
        )
    except (OSError, ValueError, TypeError, KeyError):
        return person_id, None
    if v4_summary is None or v4_blockers:
        return person_id, None

    results = readiness.get("result_bindings")
    if not isinstance(results, Mapping) or set(results) != set(RESULT_BINDING_KINDS):
        return person_id, None
    for key, kind in RESULT_BINDING_KINDS.items():
        value, _reason = _bound_object(
            project_root,
            results.get(key),
            expected_kind=kind,
            person_id=person_id,
        )
        if value is None or not _ready_result_record(key, value):
            return person_id, None

    package = readiness.get("identity_package_bindings")
    if not isinstance(package, Mapping) or set(package) != PACKAGE_BINDING_KEYS:
        return person_id, None
    profile, _reason = _bound_object(
        project_root,
        package.get("candidate_profile"),
        expected_kind=None,
        person_id=person_id,
    )
    runtime_state, _reason = _bound_object(
        project_root,
        package.get("avatar_runtime_state"),
        expected_kind=None,
        person_id=person_id,
    )
    if profile is None or runtime_state is None:
        return person_id, None

    profile_rel = _text(package["candidate_profile"].get("relative_path")).replace("\\", "/")
    state_rel = _text(package["avatar_runtime_state"].get("relative_path")).replace("\\", "/")
    if profile_rel != f"TemporaryAI/candidates/{person_id}/temporary_ai_profile.json":
        return person_id, None
    if state_rel != f"Avatar/state/temp_ai/{person_id}.json":
        return person_id, None
    activation = profile.get("activation_policy")
    if (
        _text(profile.get("status")).casefold() != "ready"
        or profile.get("chat_activation_allowed") is not True
        or profile.get("runtime_chat_ready") is not True
        or not isinstance(activation, Mapping)
        or _text(activation.get("current_status")).casefold() != "ready"
        or activation.get("text_voice_chat_allowed") is not True
        or activation.get("body_world_life_loop_allowed") is not True
    ):
        return person_id, None

    return person_id, {
        "id": person_id,
        "label": display_name,
        "bundle_id": _text(manifest.get("bundle_id")),
        "creator_type": creator_type,
        "profile_relative_path": profile_rel,
        "runtime_state_relative_path": state_rel,
        "temporary_by_default": True,
        "ready_for_text_voice_chat": True,
        "ready_for_kira_world_shell": True,
        "activation_allowed": True,
        "person_present_in_kira_world": True,
        "ram_capacity_verified": True,
        "residency_capacity_verified": True,
        "permanent_promotion_allowed": False,
    }


def surface_registry_snapshot(project_root: Path) -> dict[str, Any]:
    """Return enrolled IDs and only the fully registered ready people."""

    root = Path(project_root).resolve()
    workspaces = root / "TemporaryAI" / "creator_work_orders"
    enrolled: set[str] = set()
    ready: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    if workspaces.is_dir() and not workspaces.is_symlink():
        try:
            entries = sorted(workspaces.iterdir(), key=lambda path: path.name.casefold())
        except OSError:
            entries = []
        for workspace in entries:
            if not workspace.is_dir() or workspace.is_symlink():
                continue
            person_id, record = _workspace_record(root, workspace)
            if person_id:
                enrolled.add(person_id)
            if record is None or person_id in conflicts:
                continue
            prior = ready.get(person_id)
            if prior is not None and prior.get("bundle_id") != record.get("bundle_id"):
                ready.pop(person_id, None)
                conflicts.add(person_id)
                continue
            ready[person_id] = record
    return {
        "schema_version": 1,
        "record_kind": REGISTRY_KIND,
        "enrolled_person_ids": sorted(enrolled),
        "ready_people": [ready[key] for key in sorted(ready)],
    }


__all__ = [
    "EVIDENCE_KEYS",
    "MANIFEST_KIND",
    "PACKAGE_BINDING_KEYS",
    "READINESS_KIND",
    "REGISTRY_KIND",
    "RESULT_BINDING_KINDS",
    "SURFACE_KEYS",
    "surface_registry_snapshot",
]
