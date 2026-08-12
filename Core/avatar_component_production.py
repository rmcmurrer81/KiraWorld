"""Immutable production queue for separated Avatar Builder component sets.

This module deliberately solves a narrower problem than likeness reconstruction:
it turns an already-authored, exact-hash body/hair/eyes/clothes set into an
immutable candidate package and extracts an exact body-bound rig descriptor.
It never invents a photo fit, approves topology, renders private material, or
activates an avatar.

Photo-only requests without authored components remain explicit production
blockers.  That distinction prevents a generic base mesh from being renamed as
the requested person while still giving licensed/generated component workers a
safe hand-off target.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
from typing import Any, Iterable, Mapping
import uuid

from Core.avatar_builder_orchestration import (
    COMPONENT_ROLES,
    CONFIRMED_ADULT_TOPOLOGY,
    LICENSED_SHAPE_PRESERVING_DERIVATIVE,
    NON_ADULT_DOLL_SAFE_TOPOLOGY,
    PHOTO_ONLY_RECONSTRUCTION,
    PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
    evaluate_avatar_builder_orchestration,
)
from Core.avatar_profile_preflight import (
    evaluate_orchestration_identity_preflight,
    identity_registry_available,
)


SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A
ACTION = "adopt_verified_separate_components"
TOPOLOGY_LANES = frozenset(
    {CONFIRMED_ADULT_TOPOLOGY, NON_ADULT_DOLL_SAFE_TOPOLOGY}
)
SOURCE_LANES = frozenset(
    {
        LICENSED_SHAPE_PRESERVING_DERIVATIVE,
        PHOTO_ONLY_RECONSTRUCTION,
        PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
    }
)


class AvatarProductionError(ValueError):
    """A fail-closed request, binding, or artifact validation error."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return _sha256_bytes(canonical_json_bytes(value))


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarProductionError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise AvatarProductionError(f"JSON artifact must be an object: {path}")
    return value


def _validate_id(value: Any, name: str) -> str:
    result = _text(value)
    if not SAFE_ID_RE.fullmatch(result):
        raise AvatarProductionError(f"{name} is not a safe identifier")
    return result


def _validate_sha(value: Any, name: str) -> str:
    result = _text(value).lower()
    if not SHA256_RE.fullmatch(result):
        raise AvatarProductionError(f"{name} is not a SHA-256 digest")
    return result


def _has_symlink_component(path: Path, stop: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == stop or current.parent == current:
            return False
        current = current.parent


def _project_file(
    project_root: Path,
    raw_value: Any,
    *,
    name: str,
    allowed_roots: Iterable[Path] | None = None,
) -> Path:
    raw = Path(_text(raw_value))
    if not _text(raw_value) or raw.is_absolute() or ".." in raw.parts:
        raise AvatarProductionError(f"{name} must be a safe project-relative path")
    root = project_root.resolve(strict=True)
    unresolved = root / raw
    if _has_symlink_component(unresolved, root):
        raise AvatarProductionError(f"{name} contains a symlink")
    try:
        path = unresolved.resolve(strict=True)
    except OSError as exc:
        raise AvatarProductionError(f"{name} does not exist") from exc
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AvatarProductionError(f"{name} escapes the project") from exc
    if not path.is_file():
        raise AvatarProductionError(f"{name} is not a regular file")
    if allowed_roots is not None:
        accepted = False
        for allowed_root in allowed_roots:
            try:
                path.relative_to(allowed_root.resolve())
                accepted = True
                break
            except ValueError:
                continue
        if not accepted:
            raise AvatarProductionError(f"{name} is outside the candidate source roots")
    return path


def _relative(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _write_exclusive(path: Path, payload: bytes) -> bool:
    """Write once.  Identical existing content is idempotent; other content fails."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
        return True
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise AvatarProductionError(f"immutable path already contains different data: {path}")
        return False


def read_glb_json(path: Path) -> dict[str, Any]:
    """Read and structurally validate the JSON chunk of one GLB 2.0 artifact."""

    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) != 12:
            raise AvatarProductionError(f"truncated GLB: {path}")
        magic, version, declared_length = struct.unpack("<4sII", header)
        if magic != GLB_MAGIC or version != 2:
            raise AvatarProductionError(f"not a GLB 2.0 artifact: {path}")
        actual_length = path.stat().st_size
        if declared_length != actual_length:
            raise AvatarProductionError(f"GLB declared length mismatch: {path}")
        chunk_header = handle.read(8)
        if len(chunk_header) != 8:
            raise AvatarProductionError(f"GLB JSON chunk is missing: {path}")
        chunk_length, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != GLB_JSON_CHUNK or chunk_length > declared_length - 20:
            raise AvatarProductionError(f"invalid GLB JSON chunk: {path}")
        chunk = handle.read(chunk_length)
    try:
        document = json.loads(chunk.rstrip(b" \t\r\n\x00").decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarProductionError(f"invalid GLB JSON document: {path}") from exc
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise AvatarProductionError(f"unsupported GLB asset document: {path}")
    if not isinstance(document.get("meshes"), list) or not document["meshes"]:
        raise AvatarProductionError(f"GLB has no mesh: {path}")
    return document


def build_rig_descriptor(document: Mapping[str, Any], *, body_sha256: str) -> dict[str, Any]:
    """Extract a deterministic skeleton descriptor bound to the exact body GLB.

    It is an interchange/index artifact, not a deformation-quality attestation.
    """

    skins = document.get("skins") if isinstance(document.get("skins"), list) else []
    nodes = document.get("nodes") if isinstance(document.get("nodes"), list) else []
    if not skins:
        raise AvatarProductionError("body GLB has no skin to describe")
    child_to_parent: dict[int, int] = {}
    for parent_index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            continue
        for child in node.get("children", []):
            if isinstance(child, int):
                child_to_parent[child] = parent_index
    normalized_skins: list[dict[str, Any]] = []
    joint_union: set[int] = set()
    for skin_index, skin in enumerate(skins):
        if not isinstance(skin, Mapping):
            raise AvatarProductionError("body GLB contains an invalid skin")
        joints = skin.get("joints")
        if not isinstance(joints, list) or not joints or not all(
            isinstance(item, int) and 0 <= item < len(nodes) for item in joints
        ):
            raise AvatarProductionError("body GLB skin has invalid joints")
        joint_union.update(joints)
        normalized_skins.append(
            {
                "skin_index": skin_index,
                "name": _text(skin.get("name")),
                "skeleton_node": skin.get("skeleton") if isinstance(skin.get("skeleton"), int) else None,
                "inverse_bind_matrices_accessor": (
                    skin.get("inverseBindMatrices")
                    if isinstance(skin.get("inverseBindMatrices"), int)
                    else None
                ),
                "joint_indices": joints,
            }
        )
    normalized_joints: list[dict[str, Any]] = []
    for joint_index in sorted(joint_union):
        node = nodes[joint_index]
        if not isinstance(node, Mapping):
            raise AvatarProductionError("body GLB joint node is invalid")
        record: dict[str, Any] = {
            "node_index": joint_index,
            "name": _text(node.get("name")),
            "parent_node_index": child_to_parent.get(joint_index),
        }
        for field, expected_length in (
            ("matrix", 16),
            ("translation", 3),
            ("rotation", 4),
            ("scale", 3),
        ):
            value = node.get(field)
            if isinstance(value, list) and len(value) == expected_length:
                record[field] = value
        normalized_joints.append(record)
    return {
        "schema_version": 1,
        "artifact_role": "rig_skeleton_descriptor",
        "body_glb_sha256": body_sha256,
        "skin_count": len(normalized_skins),
        "joint_count": len(normalized_joints),
        "skins": normalized_skins,
        "joints": normalized_joints,
        "stable_deformation_proven": False,
        "runtime_activation_allowed": False,
        "truth_note": (
            "This exact-body-bound descriptor records exported skin/joint structure. "
            "It does not prove bone placement, weights, visual deformation, motion, or likeness."
        ),
    }


def plan_orchestration_request(
    request: Mapping[str, Any],
    *,
    identity_preflight: Mapping[str, Any] | None = None,
    multiview_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the truthful next production state without authoring artifacts."""

    decision = evaluate_avatar_builder_orchestration(
        request, identity_preflight=identity_preflight
    )
    candidate_id = _text(decision.get("candidate_id"))
    component_gate = decision.get("capability_gates", {}).get("component_integrity", {})
    route = decision.get("route", {})
    source_lane = _text(route.get("reconstruction_source_lane"))
    route_valid = _text(route.get("status")) == "selected_and_valid"
    route_failures = {
        _text(item) for item in route.get("failures", []) if _text(item)
    }
    photo_route_prerequisite_failures = {
        "photo_reconstruction_contract_not_ready",
        "photo_only_multiview_identity_set_missing",
        "photo_primary_multiview_identity_set_missing",
        "photo_primary_reference_model_measurement_contract_not_ready",
    }
    photo_lane = source_lane in {
        PHOTO_ONLY_RECONSTRUCTION,
        PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
    }
    photo_route_waiting_for_evidence_only = bool(
        photo_lane
        and not route_valid
        and route_failures
        and route_failures <= photo_route_prerequisite_failures
    )
    identity_gate = decision.get("identity_preflight", {})
    identity_enforced = identity_gate.get("enforced") is True
    identity_passed = identity_gate.get("passed") is True
    if identity_enforced and not identity_passed:
        state = "blocked_identity_version_or_maturity_preflight"
        next_action = "repair_canonical_profile_or_create_separate_variant"
    elif not route_valid and not photo_route_waiting_for_evidence_only:
        state = "blocked_route_or_source_authority_invalid"
        next_action = "repair_exact_route_evidence_before_authoring"
    elif photo_lane:
        evidence = multiview_evidence if isinstance(multiview_evidence, Mapping) else {}
        evidence_status = _text(evidence.get("status"))
        evidence_bound = bool(evidence)
        evidence_identity_matches = bool(
            evidence_bound
            and _text(evidence.get("candidate_id")) == candidate_id
            and _text(evidence.get("subject_id")) == _text(decision.get("subject_id"))
            and _text(evidence.get("topology_lane")) == _text(route.get("topology_lane"))
        )
        if not evidence_bound:
            state = "blocked_multiview_evidence_manifest_missing"
            next_action = "create_exact_hash_multiview_manifest_then_review_inputs"
        elif not evidence_identity_matches or evidence_status == "blocked_manifest_integrity_or_identity":
            state = "blocked_multiview_evidence_invalid"
            next_action = "repair_multiview_manifest_identity_or_hash_bindings"
        elif evidence.get("authoring_queue_ready") is not True:
            state = "blocked_multiview_evidence_review_incomplete"
            next_action = "review_views_landmarks_calibration_scale_and_base"
        elif component_gate.get("passed") is True:
            if route_valid:
                state = "component_set_authored_ready_for_immutable_adoption"
                next_action = ACTION
            else:
                state = "blocked_photo_contract_binding_update_required"
                next_action = "bind_passing_manifest_into_photo_reconstruction_contract"
        else:
            state = "blocked_multiview_likeness_author_backend_missing"
            next_action = "run_new_surface_likeness_author_when_backend_is_installed"
    elif component_gate.get("passed") is True:
        state = "component_set_authored_ready_for_immutable_adoption"
        next_action = ACTION
    else:
        state = "blocked_separate_component_set_missing"
        next_action = "run_authorized_component_author_then_queue_adoption"
    multiview = (
        dict(multiview_evidence)
        if isinstance(multiview_evidence, Mapping)
        else {}
    )
    body_blockers = list(decision.get("body_blocking_reasons", []))
    if photo_lane:
        review_gaps = [str(item) for item in multiview.get("review_gaps", [])]
        integrity_failures = [
            str(item) for item in multiview.get("integrity_failures", [])
        ]
        if not multiview:
            body_blockers.append("multiview_evidence_manifest_missing")
        elif integrity_failures:
            body_blockers.append("multiview_evidence_integrity_invalid")
        else:
            if any("source_review" in item or "reviewed_sources" in item for item in review_gaps):
                body_blockers.append("multiview_source_review_incomplete")
            if any("view_missing" in item for item in review_gaps):
                body_blockers.append("multiview_view_coverage_incomplete")
            if any("calibration" in item for item in review_gaps):
                body_blockers.append("multiview_calibration_incomplete")
            if any("landmark" in item for item in review_gaps):
                body_blockers.append("multiview_landmark_coverage_incomplete")
            if any("scale_review" in item for item in review_gaps):
                body_blockers.append("multiview_scale_review_incomplete")
            if any("base_body" in item for item in review_gaps):
                body_blockers.append("multiview_base_body_review_incomplete")
        if (
            multiview.get("authoring_queue_ready") is True
            and component_gate.get("passed") is not True
        ):
            body_blockers.append("multiview_likeness_author_backend_missing")
    body_blockers = list(dict.fromkeys(body_blockers))
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "subject_id": _text(decision.get("subject_id")),
        "canonical_candidate_id": _text(identity_gate.get("canonical_candidate_id")),
        "candidate_alias_used": identity_gate.get("candidate_alias_used") is True,
        "identity_preflight_status": _text(identity_gate.get("status")),
        "identity_preflight_blocking_reasons": list(
            identity_gate.get("failures", [])
        ),
        "topology_lane": _text(route.get("topology_lane")),
        "source_lane": source_lane,
        "production_state": state,
        "next_action": next_action,
        "orchestration_status": _text(decision.get("status")),
        "orchestration_blocking_reasons": list(decision.get("blocking_reasons", [])),
        "body_private_review_ready": decision.get("body_private_review_ready") is True,
        "body_blocking_reasons": body_blockers,
        "advanced_garment_capability_ready": (
            decision.get("advanced_garment_capability_ready") is True
        ),
        "garment_blocking_reasons": list(decision.get("garment_blocking_reasons", [])),
        "authored_component_set_present": component_gate.get("passed") is True,
        "multiview_authoring": {
            "status": _text(multiview.get("status")) or "not_prepared",
            "manifest_sha256": _text(multiview.get("manifest_sha256")),
            "manifest_exact_hash_verified": (
                multiview.get("manifest_exact_hash_verified") is True
            ),
            "source_count": int(multiview.get("source_count") or 0),
            "exact_hash_source_count": int(
                multiview.get("exact_hash_source_count") or 0
            ),
            "reviewed_source_count": int(
                multiview.get("reviewed_source_count") or 0
            ),
            "front_view_ready": multiview.get("front_view_ready") is True,
            "depth_view_ready": multiview.get("depth_view_ready") is True,
            "full_body_view_ready": multiview.get("full_body_view_ready") is True,
            "single_calibration_frame_ready": (
                multiview.get("single_calibration_frame_ready") is True
            ),
            "reviewed_landmark_count": int(
                multiview.get("reviewed_landmark_count") or 0
            ),
            "missing_landmark_regions": list(
                multiview.get("missing_landmark_regions", [])
            ),
            "scale_review": dict(multiview.get("scale_review", {}))
            if isinstance(multiview.get("scale_review"), Mapping)
            else {"ready": False, "mode": "pending"},
            "base_body_review": dict(multiview.get("base_body_review", {}))
            if isinstance(multiview.get("base_body_review"), Mapping)
            else {"ready": False},
            "integrity_failures": list(multiview.get("integrity_failures", [])),
            "review_gaps": list(multiview.get("review_gaps", [])),
            "authoring_queue_ready": (
                multiview.get("authoring_queue_ready") is True
            ),
            "author_backend_available": False,
        },
        "activation_requested": False,
        "activation_allowed": False,
        "truth_note": (
            "A production plan is not a body, likeness, topology review, stable rig proof, "
            "or activation authorization."
        ),
    }


@dataclass(frozen=True)
class ValidatedProductionRequest:
    request: dict[str, Any]
    request_path: Path
    request_sha256: str
    orchestration_path: Path
    orchestration_sha256: str
    orchestration: dict[str, Any]
    candidate_id: str
    subject_id: str
    topology_lane: str
    source_lane: str
    source_paths: dict[str, Path]
    source_hashes: dict[str, str]
    authority_path: Path
    authority_sha256: str


def validate_production_request_file(
    project_root: Path, request_path: Path
) -> ValidatedProductionRequest:
    root = project_root.resolve(strict=True)
    if _has_symlink_component(request_path, root):
        raise AvatarProductionError("production request path contains a symlink")
    resolved_request = request_path.resolve(strict=True)
    if not resolved_request.is_file():
        raise AvatarProductionError("production request is not a regular file")
    request = _read_json_object(resolved_request)
    request_sha = sha256_file(resolved_request)
    if request.get("schema_version") != 1 or _text(request.get("action")) != ACTION:
        raise AvatarProductionError("unsupported production request schema or action")
    candidate_id = _validate_id(request.get("candidate_id"), "candidate_id")
    subject_id = _validate_id(request.get("subject_id"), "subject_id")
    if request.get("runtime_activation_requested") is not False:
        raise AvatarProductionError("runtime activation must be explicitly false")
    if request.get("public_export_requested") is not False:
        raise AvatarProductionError("public export must be explicitly false")

    topology_lane = _text(request.get("topology_lane"))
    source_lane = _text(request.get("source_lane"))
    if topology_lane not in TOPOLOGY_LANES or source_lane not in SOURCE_LANES:
        raise AvatarProductionError("invalid topology or reconstruction-source lane")

    orchestration_binding = request.get("orchestration_binding")
    if not isinstance(orchestration_binding, Mapping):
        raise AvatarProductionError("orchestration binding is missing")
    orchestration_path = _project_file(
        root,
        orchestration_binding.get("path"),
        name="orchestration_binding.path",
        allowed_roots=[root / "Avatar" / "avatar_builder" / "orchestration_requests"],
    )
    orchestration_sha = _validate_sha(
        orchestration_binding.get("sha256"), "orchestration_binding.sha256"
    )
    if sha256_file(orchestration_path) != orchestration_sha:
        raise AvatarProductionError("orchestration request hash mismatch")
    orchestration = _read_json_object(orchestration_path)
    identity_preflight = (
        evaluate_orchestration_identity_preflight(root, orchestration)
        if identity_registry_available(root)
        else None
    )
    decision = evaluate_avatar_builder_orchestration(
        orchestration, identity_preflight=identity_preflight
    )
    route = decision.get("route", {})
    if (
        _text(decision.get("candidate_id")) != candidate_id
        or _text(decision.get("subject_id")) != subject_id
    ):
        raise AvatarProductionError("orchestration identity binding mismatch")
    if _text(route.get("status")) != "selected_and_valid":
        raise AvatarProductionError("orchestration route is not valid for production")
    if (
        _text(route.get("topology_lane")) != topology_lane
        or _text(route.get("reconstruction_source_lane")) != source_lane
    ):
        raise AvatarProductionError("production lane does not match orchestration route")
    component_gate = decision.get("capability_gates", {}).get("component_integrity", {})
    if component_gate.get("passed") is not True:
        raise AvatarProductionError("orchestration has no verified separated component set")
    expected_hashes = component_gate.get("component_sha256", {})

    candidate_source_roots = [
        root / "Avatar" / "temp_ai" / candidate_id,
        root / "Avatar" / "models" / "temp_ai" / candidate_id,
        root / "Avatar" / "avatar_builder" / "candidate_sources" / candidate_id,
    ]
    components = request.get("source_components")
    if not isinstance(components, Mapping) or set(components) != set(COMPONENT_ROLES):
        raise AvatarProductionError("source_components must contain body, hair, eyes, and clothes")
    source_paths: dict[str, Path] = {}
    source_hashes: dict[str, str] = {}
    for role in COMPONENT_ROLES:
        binding = components.get(role)
        if not isinstance(binding, Mapping):
            raise AvatarProductionError(f"source component binding is invalid: {role}")
        if _text(binding.get("artifact_role")) != role:
            raise AvatarProductionError(f"source component role mismatch: {role}")
        path = _project_file(
            root,
            binding.get("path"),
            name=f"source_components.{role}.path",
            allowed_roots=candidate_source_roots,
        )
        if path.suffix.lower() != ".glb":
            raise AvatarProductionError(f"source component is not GLB: {role}")
        digest = _validate_sha(binding.get("sha256"), f"source_components.{role}.sha256")
        if sha256_file(path) != digest:
            raise AvatarProductionError(f"source component hash mismatch: {role}")
        if _text(expected_hashes.get(role)).lower() != digest:
            raise AvatarProductionError(f"source component is not orchestration-bound: {role}")
        read_glb_json(path)
        source_paths[role] = path
        source_hashes[role] = digest
    if len(set(source_paths.values())) != len(COMPONENT_ROLES):
        raise AvatarProductionError("component source paths must be distinct")
    if len(set(source_hashes.values())) != len(COMPONENT_ROLES):
        raise AvatarProductionError("component source hashes must be distinct")

    authority = request.get("component_authority")
    if not isinstance(authority, Mapping):
        raise AvatarProductionError("component authority binding is missing")
    authority_path = _project_file(
        root,
        authority.get("path"),
        name="component_authority.path",
        allowed_roots=candidate_source_roots,
    )
    authority_sha = _validate_sha(authority.get("sha256"), "component_authority.sha256")
    if sha256_file(authority_path) != authority_sha:
        raise AvatarProductionError("component authority hash mismatch")
    authority_data = _read_json_object(authority_path)
    if (
        _text(authority_data.get("candidate_id")) != candidate_id
        or _text(authority_data.get("subject_id")) != subject_id
        or authority_data.get("artifact_generation_succeeded") is not True
        or authority_data.get("runtime_activation_allowed") is not False
    ):
        raise AvatarProductionError("component authority does not authorize this inactive artifact set")
    for role in COMPONENT_ROLES:
        if _text(authority_data.get(f"{role}_sha256")).lower() != source_hashes[role]:
            raise AvatarProductionError(f"component authority hash mismatch: {role}")

    # The queue may package either lane, but it may not promote a lane claim.
    # Non-adult packages require the already-reviewed orchestration route and
    # remain explicitly doll-safe; adult packages remain adult-only.
    if topology_lane == NON_ADULT_DOLL_SAFE_TOPOLOGY and request.get("adult_anatomy_requested") is not False:
        raise AvatarProductionError("non-adult lane must explicitly reject adult anatomy")
    if topology_lane == CONFIRMED_ADULT_TOPOLOGY and request.get("adult_anatomy_requested") is not True:
        raise AvatarProductionError("adult lane must explicitly request adult topology")

    return ValidatedProductionRequest(
        request=dict(request),
        request_path=resolved_request,
        request_sha256=request_sha,
        orchestration_path=orchestration_path,
        orchestration_sha256=orchestration_sha,
        orchestration=orchestration,
        candidate_id=candidate_id,
        subject_id=subject_id,
        topology_lane=topology_lane,
        source_lane=source_lane,
        source_paths=source_paths,
        source_hashes=source_hashes,
        authority_path=authority_path,
        authority_sha256=authority_sha,
    )


def _job_payload(validated: ValidatedProductionRequest, project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    return {
        "schema_version": 1,
        "action": ACTION,
        "candidate_id": validated.candidate_id,
        "subject_id": validated.subject_id,
        "topology_lane": validated.topology_lane,
        "source_lane": validated.source_lane,
        "production_request": {
            "path": _relative(validated.request_path, root),
            "sha256": validated.request_sha256,
        },
        "orchestration_binding": {
            "path": _relative(validated.orchestration_path, root),
            "sha256": validated.orchestration_sha256,
        },
        "component_authority": {
            "path": _relative(validated.authority_path, root),
            "sha256": validated.authority_sha256,
        },
        "source_components": {
            role: {
                "path": _relative(validated.source_paths[role], root),
                "sha256": validated.source_hashes[role],
            }
            for role in COMPONENT_ROLES
        },
        "runtime_activation_requested": False,
        "public_export_requested": False,
    }


def queue_production_request(
    project_root: Path,
    request_path: Path,
    *,
    queue_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve(strict=True)
    validated = validate_production_request_file(root, request_path)
    payload = _job_payload(validated, root)
    job_id = canonical_sha256(payload)
    payload["job_id"] = job_id
    destination_root = queue_root or (
        root / "Avatar" / "avatar_builder" / "component_production"
    )
    job_path = destination_root / "queued" / f"{job_id}.json"
    created = _write_exclusive(job_path, canonical_json_bytes(payload) + b"\n")
    return {
        "schema_version": 1,
        "status": "queued" if created else "already_queued",
        "job_id": job_id,
        "job_path": _relative(job_path, root),
        "candidate_id": validated.candidate_id,
        "activation_allowed": False,
    }


def _validate_existing_package(package_root: Path, manifest: Mapping[str, Any]) -> None:
    if manifest.get("runtime_activation_allowed") is not False:
        raise AvatarProductionError("existing package has unsafe activation state")
    if manifest.get("public_export_allowed") is not False:
        raise AvatarProductionError("existing package has unsafe public export state")
    for claim in (
        "body_likeness_proven",
        "topology_review_proven",
        "stable_rig_proven",
        "face_and_lip_sync_proven",
        "wearable_behavior_proven",
        "owner_review_proven",
    ):
        if manifest.get(claim) is not False:
            raise AvatarProductionError(f"existing package has unsafe proof claim: {claim}")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise AvatarProductionError("existing package manifest is missing artifacts")
    for role in (*COMPONENT_ROLES, "rig"):
        binding = artifacts.get(role)
        if not isinstance(binding, Mapping):
            raise AvatarProductionError(f"existing package is missing {role}")
        relative = Path(_text(binding.get("filename")))
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
            raise AvatarProductionError("existing package contains an unsafe artifact path")
        artifact = package_root / relative
        expected = _validate_sha(binding.get("sha256"), f"existing {role} hash")
        if artifact.is_symlink() or not artifact.is_file() or sha256_file(artifact) != expected:
            raise AvatarProductionError(f"existing package artifact changed: {role}")


def _validate_completed_job(
    root: Path,
    destination_root: Path,
    job: Mapping[str, Any],
    expected_job_id: str,
) -> dict[str, Any] | None:
    """Validate a completed immutable job without consulting its mutable request path.

    Production requests are authoring pointers and may legitimately advance to a
    newer exact-hash component set.  A completed job must remain independently
    auditable from its canonical queue record, package manifest, result, and
    copied artifacts.  An unprocessed job still revalidates every live input in
    ``process_job`` below and fails closed if any binding changed.
    """

    candidate_id = _validate_id(job.get("candidate_id"), "candidate_id")
    subject_id = _validate_id(job.get("subject_id"), "subject_id")
    topology_lane = _text(job.get("topology_lane"))
    source_lane = _text(job.get("source_lane"))
    if topology_lane not in TOPOLOGY_LANES or source_lane not in SOURCE_LANES:
        raise AvatarProductionError("completed job contains an invalid production lane")

    package_root = destination_root / "artifacts" / candidate_id / expected_job_id
    manifest_path = package_root / "component_package_manifest.json"
    result_path = destination_root / "results" / f"{expected_job_id}.json"
    package_present = package_root.exists()
    result_present = result_path.exists()
    if not package_present and not result_present:
        return None
    if package_present != result_present:
        raise AvatarProductionError("partial completed job record exists")
    if package_root.is_symlink() or not package_root.is_dir():
        raise AvatarProductionError("completed package root is unsafe")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise AvatarProductionError("completed package manifest is missing or unsafe")
    if result_path.is_symlink() or not result_path.is_file():
        raise AvatarProductionError("completed result is missing or unsafe")

    manifest = _read_json_object(manifest_path)
    identity_checks = {
        "job_id": expected_job_id,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "topology_lane": topology_lane,
        "source_lane": source_lane,
    }
    for key, expected in identity_checks.items():
        if _text(manifest.get(key)) != expected:
            raise AvatarProductionError(f"existing package {key} binding changed")
    if _text(manifest.get("status")) != "staged_separate_component_set_capability_review_required":
        raise AvatarProductionError("existing package status changed")

    orchestration_binding = job.get("orchestration_binding")
    authority_binding = job.get("component_authority")
    source_components = job.get("source_components")
    if not isinstance(orchestration_binding, Mapping):
        raise AvatarProductionError("completed job lost orchestration binding")
    if not isinstance(authority_binding, Mapping):
        raise AvatarProductionError("completed job lost component authority binding")
    if not isinstance(source_components, Mapping) or set(source_components) != set(COMPONENT_ROLES):
        raise AvatarProductionError("completed job lost source component bindings")
    orchestration_sha = _validate_sha(
        orchestration_binding.get("sha256"), "completed orchestration binding"
    )
    authority_sha = _validate_sha(
        authority_binding.get("sha256"), "completed component authority binding"
    )
    if _text(manifest.get("orchestration_sha256")).lower() != orchestration_sha:
        raise AvatarProductionError("existing package orchestration binding changed")
    if _text(manifest.get("component_authority_sha256")).lower() != authority_sha:
        raise AvatarProductionError("existing package component authority binding changed")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise AvatarProductionError("existing package manifest is missing artifacts")
    for role in COMPONENT_ROLES:
        source_binding = source_components.get(role)
        artifact_binding = artifacts.get(role)
        if not isinstance(source_binding, Mapping) or not isinstance(artifact_binding, Mapping):
            raise AvatarProductionError(f"completed job component binding is invalid: {role}")
        expected_sha = _validate_sha(
            source_binding.get("sha256"), f"completed source component {role}"
        )
        if _text(artifact_binding.get("artifact_role")) != role:
            raise AvatarProductionError(f"existing package component role changed: {role}")
        if _text(artifact_binding.get("sha256")).lower() != expected_sha:
            raise AvatarProductionError(f"existing package source binding changed: {role}")
        if artifact_binding.get("separate_artifact") is not True:
            raise AvatarProductionError(f"existing package component is no longer separate: {role}")
        if artifact_binding.get("byte_identical_to_authorized_source_component") is not True:
            raise AvatarProductionError(f"existing package component identity claim changed: {role}")
    rig = artifacts.get("rig")
    if not isinstance(rig, Mapping):
        raise AvatarProductionError("existing package rig binding is missing")
    body_sha = _validate_sha(
        source_components["body"].get("sha256"), "completed source component body"
    )
    if _text(rig.get("artifact_role")) != "rig_skeleton_descriptor":
        raise AvatarProductionError("existing package rig role changed")
    if _text(rig.get("body_glb_sha256")).lower() != body_sha:
        raise AvatarProductionError("existing package rig body binding changed")
    if rig.get("stable_deformation_proven") is not False:
        raise AvatarProductionError("existing package rig has an unsafe stability claim")

    _validate_existing_package(package_root, manifest)
    manifest_sha = sha256_file(manifest_path)
    result = _read_json_object(result_path)
    if _text(result.get("job_id")) != expected_job_id:
        raise AvatarProductionError("existing result belongs to another job")
    if _text(result.get("candidate_id")) != candidate_id or _text(result.get("subject_id")) != subject_id:
        raise AvatarProductionError("existing result identity binding changed")
    if _text(result.get("package_manifest")) != _relative(manifest_path, root):
        raise AvatarProductionError("existing result package path changed")
    if _text(result.get("package_manifest_sha256")).lower() != manifest_sha:
        raise AvatarProductionError("existing result package hash changed")
    if result.get("component_set_available") is not True or result.get("capability_review_required") is not True:
        raise AvatarProductionError("existing result capability state changed")
    if result.get("runtime_activation_allowed") is not False or result.get("public_export_allowed") is not False:
        raise AvatarProductionError("existing result has unsafe publication state")
    verified = dict(result)
    verified["status"] = "already_processed_verified"
    return verified


def process_job(
    project_root: Path,
    job_path: Path,
    *,
    queue_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve(strict=True)
    destination_root = queue_root or (
        root / "Avatar" / "avatar_builder" / "component_production"
    )
    job = _read_json_object(job_path)
    expected_job_id = _validate_sha(job.get("job_id"), "job_id")
    job_without_id = dict(job)
    job_without_id.pop("job_id", None)
    if canonical_sha256(job_without_id) != expected_job_id:
        raise AvatarProductionError("queued job content hash mismatch")
    if job_path.name != f"{expected_job_id}.json":
        raise AvatarProductionError("queued job filename does not match its content hash")
    completed = _validate_completed_job(root, destination_root, job, expected_job_id)
    if completed is not None:
        return completed
    request_binding = job.get("production_request")
    if not isinstance(request_binding, Mapping):
        raise AvatarProductionError("queued job lost its production request binding")
    request_path = _project_file(
        root, request_binding.get("path"), name="production_request.path"
    )
    if sha256_file(request_path) != _validate_sha(
        request_binding.get("sha256"), "production_request.sha256"
    ):
        raise AvatarProductionError("production request changed after queueing")
    validated = validate_production_request_file(root, request_path)
    if _job_payload(validated, root) != job_without_id:
        raise AvatarProductionError("queued job no longer matches validated request")

    package_root = (
        destination_root
        / "artifacts"
        / validated.candidate_id
        / expected_job_id
    )
    manifest_path = package_root / "component_package_manifest.json"
    result_path = destination_root / "results" / f"{expected_job_id}.json"
    if package_root.exists() or result_path.exists():
        raise AvatarProductionError("partial or unsafe immutable package already exists")

    temp_parent = destination_root / "artifacts" / validated.candidate_id
    temp_parent.mkdir(parents=True, exist_ok=True)
    temp_root = temp_parent / f".{expected_job_id}.tmp-{uuid.uuid4().hex}"
    temp_root.mkdir()
    try:
        output_bindings: dict[str, dict[str, Any]] = {}
        for role in COMPONENT_ROLES:
            digest = validated.source_hashes[role]
            filename = f"{role}_{digest[:16]}.glb"
            destination = temp_root / filename
            with destination.open("xb") as handle:
                with validated.source_paths[role].open("rb") as source:
                    shutil.copyfileobj(source, handle, length=1024 * 1024)
            if sha256_file(destination) != digest:
                raise AvatarProductionError(f"copied artifact hash mismatch: {role}")
            output_bindings[role] = {
                "artifact_role": role,
                "filename": filename,
                "sha256": digest,
                "separate_artifact": True,
                "byte_identical_to_authorized_source_component": True,
            }

        body_document = read_glb_json(temp_root / output_bindings["body"]["filename"])
        rig_descriptor = build_rig_descriptor(
            body_document, body_sha256=validated.source_hashes["body"]
        )
        rig_payload = canonical_json_bytes(rig_descriptor) + b"\n"
        rig_sha = _sha256_bytes(rig_payload)
        rig_filename = f"rig_{rig_sha[:16]}.json"
        (temp_root / rig_filename).write_bytes(rig_payload)
        output_bindings["rig"] = {
            "artifact_role": "rig_skeleton_descriptor",
            "filename": rig_filename,
            "sha256": rig_sha,
            "body_glb_sha256": validated.source_hashes["body"],
            "stable_deformation_proven": False,
            "separate_artifact": True,
        }

        manifest = {
            "schema_version": 1,
            "job_id": expected_job_id,
            "candidate_id": validated.candidate_id,
            "subject_id": validated.subject_id,
            "topology_lane": validated.topology_lane,
            "source_lane": validated.source_lane,
            "status": "staged_separate_component_set_capability_review_required",
            "artifacts": output_bindings,
            "orchestration_sha256": validated.orchestration_sha256,
            "component_authority_sha256": validated.authority_sha256,
            "body_likeness_proven": False,
            "topology_review_proven": False,
            "stable_rig_proven": False,
            "face_and_lip_sync_proven": False,
            "wearable_behavior_proven": False,
            "owner_review_proven": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
            "truth_note": (
                "These are immutable copies of an already-authored separated component set. "
                "Packaging proves file identity and separation only; it does not prove visual "
                "quality, anatomy, likeness, deformation, clothing behavior, or readiness."
            ),
        }
        manifest_payload = canonical_json_bytes(manifest) + b"\n"
        (temp_root / "component_package_manifest.json").write_bytes(manifest_payload)
        if package_root.exists():
            raise AvatarProductionError("immutable package appeared during processing")
        os.rename(temp_root, package_root)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    manifest_sha = sha256_file(manifest_path)
    result = {
        "schema_version": 1,
        "status": "processed_component_set_staged",
        "job_id": expected_job_id,
        "candidate_id": validated.candidate_id,
        "subject_id": validated.subject_id,
        "package_manifest": _relative(manifest_path, root),
        "package_manifest_sha256": manifest_sha,
        "component_set_available": True,
        "capability_review_required": True,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
    }
    _write_exclusive(result_path, canonical_json_bytes(result) + b"\n")
    return result


def process_queue(
    project_root: Path,
    *,
    queue_root: Path | None = None,
    max_jobs: int = 4,
) -> list[dict[str, Any]]:
    if not isinstance(max_jobs, int) or not 1 <= max_jobs <= 16:
        raise AvatarProductionError("max_jobs must be between 1 and 16")
    root = project_root.resolve(strict=True)
    destination_root = queue_root or (
        root / "Avatar" / "avatar_builder" / "component_production"
    )
    queued_root = destination_root / "queued"
    if not queued_root.exists():
        return []
    results: list[dict[str, Any]] = []
    for job_path in sorted(queued_root.glob("*.json")):
        job_id = job_path.stem
        if (destination_root / "results" / f"{job_id}.json").is_file():
            # Completed jobs are not trusted merely because a result filename
            # exists. Revalidate the immutable package and every artifact hash.
            process_job(root, job_path, queue_root=destination_root)
            continue
        results.append(
            process_job(root, job_path, queue_root=destination_root)
        )
        if len(results) >= max_jobs:
            break
    return results
