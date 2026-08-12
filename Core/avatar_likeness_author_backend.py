"""Fail-closed backend contract for reviewed multiview likeness authoring.

This module is the deliberately narrow bridge between the immutable reviewed
multiview queue and the existing separated-component production queue.  It can
prepare a deterministic, content-addressed work order for an explicitly
reviewed Blender author capability and can audit that worker's private output.

It does not estimate landmarks, copy a reference surface, run an unreviewed
tool, claim likeness/anatomy/deformation quality, or activate an avatar.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
from typing import Any, Iterable, Mapping
import zlib

from Core.avatar_component_production import (
    AvatarProductionError,
    build_rig_descriptor,
    read_glb_json,
)
from Core.avatar_multiview_authoring import (
    OUTPUT_RULE,
    QUEUE_ACTION,
    canonical_json_bytes,
    evaluate_multiview_manifest,
    sha256_file,
)
from Core.avatar_profile_preflight import (
    AvatarProfilePreflightError,
    evaluate_avatar_profile_preflight,
    identity_registry_available,
)


SCHEMA_VERSION = 1
PROTOCOL = "reviewed_multiview_new_surface_v1"
CAPABILITY_TYPE = "avatar_likeness_author_tool_capability"
WORK_ORDER_TYPE = "avatar_likeness_author_work_order"
WORKER_RESULT_TYPE = "avatar_likeness_author_worker_result"
SURFACE_DECLARATION_TYPE = "avatar_new_surface_worker_declaration"
REPROJECTION_TYPE = "avatar_landmark_reprojection_metrics"
RIG_SMOKE_TYPE = "avatar_rig_mechanical_smoke"
DEFAULT_BACKEND_ROOT = Path("Avatar/avatar_builder/likeness_authoring")
DEFAULT_CANDIDATE_SOURCE_ROOT = Path("Avatar/avatar_builder/candidate_sources")
DEFAULT_CAPABILITY_PATH = (
    DEFAULT_BACKEND_ROOT / "tooling" / "active_capability.json"
)
EXPECTED_WORKER_PATH = Path("tools/blender_fit_reviewed_multiview_surface.py")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,191}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMPONENT_ROLES = ("body", "hair", "eyes", "clothes", "clothed_review")
DECLARATION_ROLES = (
    "surface_authorship",
    "landmark_reprojection",
    "rig_mechanical_smoke",
)
REVIEW_RENDER_ROLES = (
    "clothed_front",
    "clothed_profile",
    "clothed_back",
    "clothed_three_quarter",
    "face_closeup",
    "hands",
)
REQUIRED_CAPABILITIES = (
    "consumes_only_reviewed_landmarks",
    "authors_new_surface_from_cage",
    "forbids_reference_surface_copy",
    "exports_separate_components",
    "exports_landmark_reprojection_metrics",
    "exports_rig_mechanical_smoke",
    "renders_clothed_private_review_views",
)
MAX_COMPONENT_GLB_BYTES = 512 * 1024 * 1024
MAX_POSITION_VERTEX_COUNT = 10_000_000
MAX_ABSOLUTE_POSITION = 10_000.0


class AvatarLikenessAuthorError(ValueError):
    """A queue, tool, work-order, output, or proof contract failed closed."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _valid_sha(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _safe_id(value: Any) -> bool:
    return bool(SAFE_ID_RE.fullmatch(_text(value)))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _read_json(path: Path, *, name: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarLikenessAuthorError(f"{name} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise AvatarLikenessAuthorError(f"{name} must be a JSON object")
    return value


def _has_symlink_component(path: Path, stop: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == stop or current.parent == current:
            return False
        current = current.parent


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _project_file(
    project_root: Path,
    raw_value: Any,
    *,
    name: str,
    allowed_root: Path | None = None,
    suffixes: Iterable[str] | None = None,
) -> Path:
    root = project_root.resolve(strict=True)
    raw_text = _text(raw_value)
    raw = Path(raw_text)
    if not raw_text or raw.is_absolute() or ".." in raw.parts:
        raise AvatarLikenessAuthorError(f"{name} must be project-relative")
    unresolved = root / raw
    if _has_symlink_component(unresolved, root):
        raise AvatarLikenessAuthorError(f"{name} contains a symlink")
    try:
        path = unresolved.resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AvatarLikenessAuthorError(f"{name} is missing or unsafe") from exc
    if not path.is_file():
        raise AvatarLikenessAuthorError(f"{name} is not a regular file")
    if allowed_root is not None and not _inside(path, allowed_root):
        raise AvatarLikenessAuthorError(f"{name} is outside its allowed root")
    if suffixes is not None and path.suffix.lower() not in set(suffixes):
        raise AvatarLikenessAuthorError(f"{name} has an unsupported suffix")
    return path


def _project_output_path(
    project_root: Path,
    raw_value: Any,
    *,
    name: str,
    allowed_root: Path,
) -> Path:
    root = project_root.resolve(strict=True)
    raw_text = _text(raw_value)
    raw = Path(raw_text)
    if not raw_text or raw.is_absolute() or ".." in raw.parts:
        raise AvatarLikenessAuthorError(f"{name} must be project-relative")
    unresolved = root / raw
    if _has_symlink_component(unresolved, root):
        raise AvatarLikenessAuthorError(f"{name} contains a symlink")
    resolved = unresolved.resolve()
    if not _inside(resolved, allowed_root):
        raise AvatarLikenessAuthorError(f"{name} is outside its allowed root")
    return resolved


def _relative(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _write_exclusive(
    project_root: Path,
    path: Path,
    value: Mapping[str, Any],
    *,
    allowed_root: Path,
    name: str,
) -> bool:
    """Write immutable JSON only after pre/post-create confinement checks."""

    root = project_root.resolve(strict=True)
    unresolved_allowed = allowed_root if allowed_root.is_absolute() else root / allowed_root
    unresolved_path = path if path.is_absolute() else root / path
    if _has_symlink_component(unresolved_allowed, root) or _has_symlink_component(
        unresolved_path, root
    ):
        raise AvatarLikenessAuthorError(f"{name} path contains a symlink")
    allowed = unresolved_allowed.resolve()
    target = unresolved_path.resolve()
    try:
        allowed.relative_to(root)
        target.relative_to(allowed)
    except ValueError as exc:
        raise AvatarLikenessAuthorError(
            f"{name} path is outside its allowed root"
        ) from exc
    encoded = canonical_json_bytes(value) + b"\n"
    unresolved_path.parent.mkdir(parents=True, exist_ok=True)
    if _has_symlink_component(unresolved_path, root):
        raise AvatarLikenessAuthorError(
            f"{name} path gained a symlink before write"
        )
    try:
        parent = unresolved_path.parent.resolve(strict=True)
        parent.relative_to(allowed)
    except (OSError, ValueError) as exc:
        raise AvatarLikenessAuthorError(
            f"{name} parent is outside its allowed root"
        ) from exc
    target = parent / unresolved_path.name
    if target.exists() and target.is_symlink():
        raise AvatarLikenessAuthorError(f"{name} target is a symlink")
    try:
        with target.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except FileExistsError:
        if target.is_symlink() or not target.is_file() or target.read_bytes() != encoded:
            raise AvatarLikenessAuthorError(
                f"immutable {name} already contains different data"
            )
        return False


def _exact_bound_file(
    project_root: Path,
    binding: Mapping[str, Any],
    *,
    name: str,
    expected_path: str | None = None,
    allowed_root: Path | None = None,
    suffixes: Iterable[str] | None = None,
) -> tuple[Path, str]:
    if not isinstance(binding, Mapping):
        raise AvatarLikenessAuthorError(f"{name} binding is missing")
    if expected_path is not None and _text(binding.get("path")) != expected_path:
        raise AvatarLikenessAuthorError(f"{name} path does not match the contract")
    path = _project_file(
        project_root,
        binding.get("path"),
        name=f"{name}.path",
        allowed_root=allowed_root,
        suffixes=suffixes,
    )
    expected_sha = _text(binding.get("sha256")).lower()
    if not _valid_sha(expected_sha) or sha256_file(path) != expected_sha:
        raise AvatarLikenessAuthorError(f"{name} hash mismatch")
    return path, expected_sha


def _canonical_identity_preflight(
    project_root: Path, job: Mapping[str, Any]
) -> dict[str, Any]:
    """Require canonical identity authority and bind the selected version.

    Version-required profiles must exactly match the canonical profile value.
    When a profile intentionally has no canonical version field (for example,
    an owner reference-set build), the exact reviewed manifest/queue version is
    recorded as the authority instead of being mislabeled as a canonical match.
    """

    root = project_root.resolve(strict=True)
    if not identity_registry_available(root):
        raise AvatarLikenessAuthorError(
            "canonical identity registry is unavailable; likeness authoring fails closed"
        )
    requested_maturity = (
        "adult"
        if _text(job.get("topology_lane")) == "confirmed_adult_topology"
        else "non_adult_doll_safe"
    )
    try:
        preflight = evaluate_avatar_profile_preflight(
            root,
            _text(job.get("candidate_id")),
            requested_subject_id=_text(job.get("subject_id")),
            requested_maturity_class=requested_maturity,
        )
    except AvatarProfilePreflightError as exc:
        raise AvatarLikenessAuthorError(
            "canonical identity/version/maturity preflight could not be validated"
        ) from exc
    identity = preflight.get("identity")
    maturity = preflight.get("maturity")
    if not isinstance(identity, Mapping) or not isinstance(maturity, Mapping):
        raise AvatarLikenessAuthorError(
            "canonical identity/version/maturity preflight is incomplete"
        )
    selected_version = _text(identity.get("selected_version"))
    queued_version = _text(job.get("selected_version_id"))
    version_required = identity.get("version_required") is True
    version_locked = identity.get("version_locked") is True
    if (
        preflight.get("authoring_allowed") is not True
        or _text(maturity.get("safety_topology_lane"))
        != _text(job.get("topology_lane"))
        or (version_required and (not version_locked or not selected_version))
        or (selected_version and selected_version != queued_version)
    ):
        raise AvatarLikenessAuthorError(
            "queued evidence no longer passes canonical identity/version/maturity preflight"
        )
    result = dict(preflight)
    result["likeness_author_version_binding"] = {
        "selected_version_id": queued_version,
        "canonical_selected_version": selected_version,
        "version_required_by_canonical_profile": version_required,
        "binding_mode": (
            "canonical_profile_exact"
            if selected_version
            else "reviewed_manifest_exact_optional_canonical_version"
        ),
        "exact_binding_verified": True,
    }
    return result


def validate_queued_evidence_job(
    project_root: Path, queued_job_path: Path
) -> dict[str, Any]:
    """Revalidate an immutable queue job and every reviewed source binding."""

    root = project_root.resolve(strict=True)
    queue_root = root / DEFAULT_BACKEND_ROOT.parent / "multiview_authoring" / "queued"
    raw = queued_job_path if queued_job_path.is_absolute() else root / queued_job_path
    if _has_symlink_component(raw, root):
        raise AvatarLikenessAuthorError("queued evidence job contains a symlink")
    try:
        path = raw.resolve(strict=True)
    except OSError as exc:
        raise AvatarLikenessAuthorError("queued evidence job is missing") from exc
    if not path.is_file() or not _inside(path, queue_root):
        raise AvatarLikenessAuthorError("queued evidence job is outside the queue")
    job = _read_json(path, name="queued evidence job")
    job_id = _text(job.get("job_id")).lower()
    if not _valid_sha(job_id) or path.name != f"{job_id}.json":
        raise AvatarLikenessAuthorError("queued evidence job identity is invalid")
    unhashed = dict(job)
    unhashed.pop("job_id", None)
    if canonical_sha256(unhashed) != job_id:
        raise AvatarLikenessAuthorError("queued evidence job content hash mismatch")
    if (
        job.get("schema_version") != SCHEMA_VERSION
        or _text(job.get("action")) != QUEUE_ACTION
        or _text(job.get("output_rule")) != OUTPUT_RULE
        or job.get("runtime_activation_requested") is not False
        or job.get("public_export_requested") is not False
    ):
        raise AvatarLikenessAuthorError("queued evidence job policy contract is invalid")
    for field in ("candidate_id", "subject_id", "selected_version_id"):
        if not _safe_id(job.get(field)):
            raise AvatarLikenessAuthorError(f"queued evidence job {field} is invalid")
    manifest_binding = job.get("manifest")
    if not isinstance(manifest_binding, Mapping):
        raise AvatarLikenessAuthorError("queued evidence job lost its manifest")
    manifest_path, manifest_sha = _exact_bound_file(
        root,
        manifest_binding,
        name="queued manifest",
        allowed_root=root / DEFAULT_BACKEND_ROOT.parent / "multiview_authoring" / "manifests",
        suffixes={".json"},
    )
    evaluation = evaluate_multiview_manifest(
        root,
        manifest_path,
        expected_candidate_id=_text(job.get("candidate_id")),
        expected_subject_id=_text(job.get("subject_id")),
        expected_topology_lane=_text(job.get("topology_lane")),
        expected_manifest_sha256=manifest_sha,
    )
    if (
        evaluation.get("authoring_queue_ready") is not True
        or _text(evaluation.get("status")) != "ready_for_likeness_authoring_queue"
        or evaluation.get("runtime_activation_allowed") is not False
    ):
        raise AvatarLikenessAuthorError(
            "queued multiview evidence is no longer fully reviewed and valid"
        )
    manifest = _read_json(manifest_path, name="reviewed multiview manifest")
    identity_preflight = _canonical_identity_preflight(root, job)
    return {
        "path": path,
        "job": job,
        "job_id": job_id,
        "manifest_path": manifest_path,
        "manifest_sha256": manifest_sha,
        "manifest": manifest,
        "evaluation": evaluation,
        "identity_preflight": identity_preflight,
        "identity_preflight_sha256": canonical_sha256(identity_preflight),
    }


def inspect_author_tooling(
    project_root: Path,
    capability_path: Path | None = None,
) -> dict[str, Any]:
    """Inspect an exact worker capability without invoking Blender."""

    root = project_root.resolve(strict=True)
    configured = capability_path or DEFAULT_CAPABILITY_PATH
    raw = configured if configured.is_absolute() else root / configured
    blockers: list[str] = []
    if not raw.exists():
        return {
            "status": "blocked_required_author_tooling_missing",
            "ready": False,
            "blocking_reasons": ["reviewed_author_capability_descriptor_missing"],
            "runtime_activation_allowed": False,
        }
    try:
        capability_file = _project_file(
            root,
            _relative(raw, root),
            name="author capability",
            allowed_root=root / DEFAULT_BACKEND_ROOT / "tooling",
            suffixes={".json"},
        )
        capability = _read_json(capability_file, name="author capability")
    except (AvatarLikenessAuthorError, ValueError):
        return {
            "status": "blocked_required_author_tooling_invalid",
            "ready": False,
            "blocking_reasons": ["reviewed_author_capability_descriptor_invalid"],
            "runtime_activation_allowed": False,
        }
    if (
        capability.get("schema_version") != SCHEMA_VERSION
        or _text(capability.get("artifact_type")) != CAPABILITY_TYPE
        or _text(capability.get("protocol")) != PROTOCOL
        or _text(capability.get("status")) != "operator_approved_available"
        or capability.get("operator_approved") is not True
        or not _text(capability.get("reviewed_by"))
        or not _text(capability.get("reviewed_at"))
        or capability.get("runtime_activation_allowed") is not False
        or capability.get("public_export_allowed") is not False
    ):
        blockers.append("author_capability_policy_or_review_invalid")
    features = capability.get("capabilities")
    if not isinstance(features, Mapping) or any(
        features.get(name) is not True for name in REQUIRED_CAPABILITIES
    ):
        blockers.append("required_author_capability_missing")
    worker = capability.get("worker")
    if not isinstance(worker, Mapping):
        blockers.append("worker_binding_missing")
        worker_path = None
    else:
        try:
            if Path(_text(worker.get("path"))).as_posix() != EXPECTED_WORKER_PATH.as_posix():
                raise AvatarLikenessAuthorError("unexpected worker path")
            worker_path, _ = _exact_bound_file(
                root,
                worker,
                name="author worker",
                expected_path=EXPECTED_WORKER_PATH.as_posix(),
                allowed_root=root / "tools",
                suffixes={".py"},
            )
        except AvatarLikenessAuthorError:
            blockers.append("reviewed_blender_author_worker_missing_or_changed")
            worker_path = None
    blender = capability.get("blender")
    blender_path: Path | None = None
    if not isinstance(blender, Mapping):
        blockers.append("blender_binding_missing")
    else:
        raw_blender = Path(_text(blender.get("executable_path")))
        expected_sha = _text(blender.get("sha256")).lower()
        try:
            blender_path = raw_blender.resolve(strict=True)
        except OSError:
            blender_path = None
        if (
            not raw_blender.is_absolute()
            or blender_path is None
            or not blender_path.is_file()
            or blender_path.is_symlink()
            or blender_path.name.lower() not in {"blender", "blender.exe"}
            or not _valid_sha(expected_sha)
            or sha256_file(blender_path) != expected_sha
        ):
            blockers.append("exact_blender_executable_missing_or_changed")
    blockers = list(dict.fromkeys(blockers))
    return {
        "status": "ready" if not blockers else "blocked_required_author_tooling_invalid",
        "ready": not blockers,
        "blocking_reasons": blockers,
        "capability_path": _relative(capability_file, root),
        "capability_sha256": sha256_file(capability_file),
        "worker_path": _relative(worker_path, root) if worker_path else "",
        "worker_sha256": sha256_file(worker_path) if worker_path else "",
        "blender_sha256": sha256_file(blender_path) if blender_path else "",
        "algorithm_id": _text(capability.get("algorithm_id")),
        "runtime_activation_allowed": False,
    }


def _review_bindings(
    project_root: Path, manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    root = project_root.resolve(strict=True)
    review_root = root / DEFAULT_BACKEND_ROOT.parent / "multiview_authoring"
    bindings: list[dict[str, Any]] = []
    for source in manifest.get("source_images", []):
        if not isinstance(source, Mapping):
            continue
        review = source.get("review_artifact")
        if not isinstance(review, Mapping):
            continue
        review_path, review_sha = _exact_bound_file(
            root,
            review,
            name=f"review artifact {_text(source.get('source_id'))}",
            allowed_root=review_root,
            suffixes={".json"},
        )
        review_document = _read_json(review_path, name="source review artifact")
        landmarks = review_document.get("landmarks")
        if (
            not isinstance(landmarks, list)
            or not landmarks
            or any(
                not isinstance(item, Mapping) or item.get("reviewed") is not True
                for item in landmarks
            )
        ):
            raise AvatarLikenessAuthorError(
                "source review landmark coverage is invalid"
            )
        bindings.append(
            {
                "source_id": _text(source.get("source_id")),
                "source_sha256": _text(source.get("sha256")).lower(),
                "source_review_sha256": review_sha,
                "reviewed_landmark_count": len(landmarks),
            }
        )
    return sorted(bindings, key=lambda item: item["source_id"])


def _required_outputs(
    project_root: Path, candidate_id: str, author_job_id: str
) -> dict[str, Any]:
    run_root = (
        project_root
        / DEFAULT_CANDIDATE_SOURCE_ROOT
        / candidate_id
        / "likeness_authoring"
        / author_job_id
    )
    rel = lambda *parts: _relative(run_root.joinpath(*parts), project_root)
    return {
        "run_root": _relative(run_root, project_root),
        "worker_result": rel("worker_result.json"),
        "components": {
            role: rel("components", f"{role}.glb") for role in COMPONENT_ROLES
        },
        "worker_declarations": {
            "surface_authorship": rel("worker_declarations", "surface_authorship.json"),
            "landmark_reprojection": rel("worker_declarations", "landmark_reprojection.json"),
            "rig_mechanical_smoke": rel("worker_declarations", "rig_mechanical_smoke.json"),
        },
        "review_renders": {
            role: rel("review_renders", f"{role}.png") for role in REVIEW_RENDER_ROLES
        },
        "backend_proofs": {
            "component_integrity": rel("backend_proofs", "component_integrity.json"),
            "rig_structure": rel("backend_proofs", "rig_structure.json"),
            "component_authority": rel(
                "backend_proofs", "component_authority.json"
            ),
            "review_candidate_manifest": rel(
                "backend_proofs", "review_candidate_manifest.json"
            ),
        },
    }


def prepare_likeness_author_work_order(
    project_root: Path,
    queued_job_path: Path,
    *,
    capability_path: Path | None = None,
) -> dict[str, Any]:
    """Prepare an immutable author work order; never run the worker itself."""

    root = project_root.resolve(strict=True)
    validated = validate_queued_evidence_job(root, queued_job_path)
    tooling = inspect_author_tooling(root, capability_path)
    if tooling.get("ready") is not True:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": tooling["status"],
            "candidate_id": validated["job"]["candidate_id"],
            "queued_job_id": validated["job_id"],
            "reviewed_evidence_verified": True,
            "work_order_created": False,
            "blocking_reasons": tooling["blocking_reasons"],
            "runtime_activation_allowed": False,
            "truth_note": "Reviewed evidence passed, but no unreviewed or missing tool may author a body.",
        }
    identity = {
        "protocol": PROTOCOL,
        "queued_job_id": validated["job_id"],
        "manifest_sha256": validated["manifest_sha256"],
        "capability_sha256": tooling["capability_sha256"],
        "worker_sha256": tooling["worker_sha256"],
        "blender_sha256": tooling["blender_sha256"],
        "algorithm_id": tooling["algorithm_id"],
        "candidate_id": validated["job"]["candidate_id"],
        "subject_id": validated["job"]["subject_id"],
        "selected_version_id": validated["job"]["selected_version_id"],
        "topology_lane": validated["job"]["topology_lane"],
        "identity_preflight_sha256": validated["identity_preflight_sha256"],
    }
    if not identity["algorithm_id"]:
        raise AvatarLikenessAuthorError("approved author capability has no algorithm_id")
    author_job_id = canonical_sha256(identity)
    backend_root = root / DEFAULT_BACKEND_ROOT
    outputs = _required_outputs(root, identity["candidate_id"], author_job_id)
    review_bindings = _review_bindings(root, validated["manifest"])
    if sum(item["reviewed_landmark_count"] for item in review_bindings) != int(
        validated["evaluation"]["reviewed_landmark_count"]
    ):
        raise AvatarLikenessAuthorError(
            "reviewed landmark counts do not match the evidence summary"
        )
    work_order = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": WORK_ORDER_TYPE,
        "protocol": PROTOCOL,
        "author_job_id": author_job_id,
        "identity": identity,
        "queued_evidence_job": {
            "path": _relative(validated["path"], root),
            "sha256": sha256_file(validated["path"]),
        },
        "reviewed_manifest": {
            "path": _relative(validated["manifest_path"], root),
            "sha256": validated["manifest_sha256"],
        },
        "reviewed_source_bindings": review_bindings,
        "evidence_summary": {
            "reviewed_source_count": validated["evaluation"]["reviewed_source_count"],
            "reviewed_landmark_count": validated["evaluation"]["reviewed_landmark_count"],
            "covered_views": validated["evaluation"]["covered_views"],
            "single_calibration_frame_ready": True,
            "scale_review": validated["evaluation"]["scale_review"],
            "base_body_review": validated["evaluation"]["base_body_review"],
            "identity_preflight": validated["identity_preflight"],
        },
        "author_capability": {
            "path": tooling["capability_path"],
            "sha256": tooling["capability_sha256"],
        },
        "deterministic_authoring": {
            "algorithm_id": tooling["algorithm_id"],
            "seed_hex": author_job_id[:32],
            "new_candidate_surface_required": True,
            "base_may_be_used_as_cage_only": True,
            "reference_surface_copy_allowed": False,
            "reference_material_or_texture_copy_allowed": False,
        },
        "required_outputs": outputs,
        "runtime_activation_requested": False,
        "public_export_requested": False,
        "automatic_likeness_approval_allowed": False,
        "automatic_anatomy_approval_allowed": False,
        "truth_note": (
            "This deterministic work order authorizes only an inactive private attempt. "
            "It is not a body, likeness proof, anatomy proof, rig proof, owner approval, or activation."
        ),
    }
    work_order_path = (
        backend_root
        / "work_orders"
        / identity["candidate_id"]
        / f"{author_job_id}.json"
    )
    created = _write_exclusive(
        root,
        work_order_path,
        work_order,
        allowed_root=backend_root / "work_orders",
        name="likeness author work order",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "prepared_inactive_author_work_order" if created else "already_prepared_verified",
        "candidate_id": identity["candidate_id"],
        "author_job_id": author_job_id,
        "work_order_path": _relative(work_order_path, root),
        "work_order_sha256": sha256_file(work_order_path),
        "reviewed_evidence_verified": True,
        "work_order_created": created,
        "body_candidate_created": False,
        "runtime_activation_allowed": False,
    }


def validate_likeness_author_work_order(
    project_root: Path, work_order_path: Path
) -> dict[str, Any]:
    root = project_root.resolve(strict=True)
    raw = work_order_path if work_order_path.is_absolute() else root / work_order_path
    if _has_symlink_component(raw, root):
        raise AvatarLikenessAuthorError("work order contains a symlink")
    try:
        path = raw.resolve(strict=True)
    except OSError as exc:
        raise AvatarLikenessAuthorError("work order is missing") from exc
    work_root = root / DEFAULT_BACKEND_ROOT / "work_orders"
    if not path.is_file() or not _inside(path, work_root):
        raise AvatarLikenessAuthorError("work order is outside its immutable root")
    order = _read_json(path, name="likeness author work order")
    identity = order.get("identity")
    if (
        order.get("schema_version") != SCHEMA_VERSION
        or _text(order.get("artifact_type")) != WORK_ORDER_TYPE
        or _text(order.get("protocol")) != PROTOCOL
        or not isinstance(identity, Mapping)
        or order.get("runtime_activation_requested") is not False
        or order.get("public_export_requested") is not False
        or order.get("automatic_likeness_approval_allowed") is not False
        or order.get("automatic_anatomy_approval_allowed") is not False
    ):
        raise AvatarLikenessAuthorError("work order policy contract is invalid")
    author_job_id = _text(order.get("author_job_id")).lower()
    if not _valid_sha(author_job_id) or canonical_sha256(identity) != author_job_id:
        raise AvatarLikenessAuthorError("work order identity hash mismatch")
    candidate_id = _text(identity.get("candidate_id"))
    if path.name != f"{author_job_id}.json" or path.parent.name != candidate_id:
        raise AvatarLikenessAuthorError("work order path does not match its identity")
    queued_binding = order.get("queued_evidence_job")
    queue_path, queue_sha = _exact_bound_file(
        root,
        queued_binding,
        name="work order queued evidence",
        expected_path=_text(queued_binding.get("path")) if isinstance(queued_binding, Mapping) else None,
        allowed_root=root / DEFAULT_BACKEND_ROOT.parent / "multiview_authoring" / "queued",
        suffixes={".json"},
    )
    validated_queue = validate_queued_evidence_job(root, queue_path)
    if (
        queue_sha != _text(queued_binding.get("sha256")).lower()
        or validated_queue["job_id"] != _text(identity.get("queued_job_id"))
        or validated_queue["manifest_sha256"] != _text(identity.get("manifest_sha256"))
    ):
        raise AvatarLikenessAuthorError("work order evidence binding changed")
    capability_binding = order.get("author_capability")
    capability_path, capability_sha = _exact_bound_file(
        root,
        capability_binding,
        name="work order author capability",
        allowed_root=root / DEFAULT_BACKEND_ROOT / "tooling",
        suffixes={".json"},
    )
    tooling = inspect_author_tooling(root, capability_path)
    if tooling.get("ready") is not True or capability_sha != _text(identity.get("capability_sha256")):
        raise AvatarLikenessAuthorError("approved author tooling is no longer exact and available")
    expected_identity = {
        "protocol": PROTOCOL,
        "queued_job_id": validated_queue["job_id"],
        "manifest_sha256": validated_queue["manifest_sha256"],
        "capability_sha256": tooling["capability_sha256"],
        "worker_sha256": tooling["worker_sha256"],
        "blender_sha256": tooling["blender_sha256"],
        "algorithm_id": tooling["algorithm_id"],
        "candidate_id": validated_queue["job"]["candidate_id"],
        "subject_id": validated_queue["job"]["subject_id"],
        "selected_version_id": validated_queue["job"]["selected_version_id"],
        "topology_lane": validated_queue["job"]["topology_lane"],
        "identity_preflight_sha256": validated_queue["identity_preflight_sha256"],
    }
    if dict(identity) != expected_identity:
        raise AvatarLikenessAuthorError("work order identity no longer matches evidence and tooling")
    reviewed_manifest = order.get("reviewed_manifest")
    expected_manifest_binding = {
        "path": _relative(validated_queue["manifest_path"], root),
        "sha256": validated_queue["manifest_sha256"],
    }
    if reviewed_manifest != expected_manifest_binding:
        raise AvatarLikenessAuthorError("work order reviewed manifest binding changed")
    expected_review_bindings = _review_bindings(root, validated_queue["manifest"])
    if sum(item["reviewed_landmark_count"] for item in expected_review_bindings) != int(
        validated_queue["evaluation"]["reviewed_landmark_count"]
    ):
        raise AvatarLikenessAuthorError(
            "reviewed landmark counts no longer match the evidence summary"
        )
    if order.get("reviewed_source_bindings") != expected_review_bindings:
        raise AvatarLikenessAuthorError("work order reviewed source bindings changed")
    expected_evidence_summary = {
        "reviewed_source_count": validated_queue["evaluation"]["reviewed_source_count"],
        "reviewed_landmark_count": validated_queue["evaluation"]["reviewed_landmark_count"],
        "covered_views": validated_queue["evaluation"]["covered_views"],
        "single_calibration_frame_ready": True,
        "scale_review": validated_queue["evaluation"]["scale_review"],
        "base_body_review": validated_queue["evaluation"]["base_body_review"],
        "identity_preflight": validated_queue["identity_preflight"],
    }
    if order.get("evidence_summary") != expected_evidence_summary:
        raise AvatarLikenessAuthorError("work order evidence summary changed")
    expected_authoring = {
        "algorithm_id": tooling["algorithm_id"],
        "seed_hex": author_job_id[:32],
        "new_candidate_surface_required": True,
        "base_may_be_used_as_cage_only": True,
        "reference_surface_copy_allowed": False,
        "reference_material_or_texture_copy_allowed": False,
    }
    if order.get("deterministic_authoring") != expected_authoring:
        raise AvatarLikenessAuthorError("work order deterministic authoring contract changed")
    expected_outputs = _required_outputs(root, candidate_id, author_job_id)
    if order.get("required_outputs") != expected_outputs:
        raise AvatarLikenessAuthorError("work order output contract changed")
    return {
        "path": path,
        "sha256": sha256_file(path),
        "order": order,
        "identity": dict(identity),
        "author_job_id": author_job_id,
        "validated_queue": validated_queue,
        "tooling": tooling,
    }


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    if len(payload) < 45 or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AvatarLikenessAuthorError("review render is not a PNG")
    offset = 8
    chunks: list[tuple[bytes, bytes]] = []
    while offset + 12 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        if length > 128 * 1024 * 1024 or offset + 12 + length > len(payload):
            raise AvatarLikenessAuthorError("review render PNG chunk is invalid")
        kind = payload[offset + 4 : offset + 8]
        data = payload[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", payload[offset + 8 + length : offset + 12 + length])[0]
        if zlib.crc32(kind + data) & 0xFFFFFFFF != expected_crc:
            raise AvatarLikenessAuthorError("review render PNG CRC is invalid")
        chunks.append((kind, data))
        offset += 12 + length
        if kind == b"IEND":
            break
    if (
        not chunks
        or chunks[0][0] != b"IHDR"
        or len(chunks[0][1]) != 13
        or not any(kind == b"IDAT" and data for kind, data in chunks)
        or chunks[-1] != (b"IEND", b"")
        or offset != len(payload)
    ):
        raise AvatarLikenessAuthorError("review render PNG structure is incomplete")
    width, height = struct.unpack(">II", chunks[0][1][:8])
    if width < 64 or height < 64:
        raise AvatarLikenessAuthorError("review render is too small for review")
    return width, height


_GLB_JSON_CHUNK = 0x4E4F534A
_GLB_BIN_CHUNK = 0x004E4942
_ACCESSOR_COMPONENT_BYTES = {
    5120: 1,
    5121: 1,
    5122: 2,
    5123: 2,
    5125: 4,
    5126: 4,
}
_ACCESSOR_TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def _bounded_integer(
    value: Any, *, minimum: int, maximum: int, name: str
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise AvatarLikenessAuthorError(f"{name} is out of bounds")
    return value


def _read_self_contained_glb(
    path: Path,
) -> tuple[dict[str, Any], bytes]:
    try:
        document = read_glb_json(path)
    except AvatarProductionError as exc:
        raise AvatarLikenessAuthorError("component GLB structure is invalid") from exc
    size = path.stat().st_size
    if size < 32 or size > MAX_COMPONENT_GLB_BYTES:
        raise AvatarLikenessAuthorError("component GLB size is outside the review bound")
    payload = path.read_bytes()
    try:
        magic, version, declared_length = struct.unpack("<4sII", payload[:12])
    except struct.error as exc:
        raise AvatarLikenessAuthorError("component GLB header is invalid") from exc
    if magic != b"glTF" or version != 2 or declared_length != len(payload):
        raise AvatarLikenessAuthorError("component GLB header binding is invalid")
    offset = 12
    chunks: list[tuple[int, bytes]] = []
    while offset < len(payload):
        if offset + 8 > len(payload):
            raise AvatarLikenessAuthorError("component GLB chunk header is truncated")
        length, kind = struct.unpack("<II", payload[offset : offset + 8])
        offset += 8
        if length % 4 or offset + length > len(payload):
            raise AvatarLikenessAuthorError("component GLB chunk is invalid")
        chunks.append((kind, payload[offset : offset + length]))
        offset += length
    if (
        len(chunks) != 2
        or chunks[0][0] != _GLB_JSON_CHUNK
        or chunks[1][0] != _GLB_BIN_CHUNK
        or not chunks[1][1]
    ):
        raise AvatarLikenessAuthorError(
            "component GLB must contain exactly one JSON and one embedded BIN chunk"
        )
    buffers = document.get("buffers")
    if not isinstance(buffers, list) or len(buffers) != 1:
        raise AvatarLikenessAuthorError(
            "component GLB must declare exactly one embedded buffer"
        )
    buffer_record = buffers[0]
    if not isinstance(buffer_record, Mapping) or "uri" in buffer_record:
        raise AvatarLikenessAuthorError(
            "component GLB external buffer dependencies are forbidden"
        )
    declared_bytes = _bounded_integer(
        buffer_record.get("byteLength"),
        minimum=1,
        maximum=MAX_COMPONENT_GLB_BYTES,
        name="component GLB buffer byteLength",
    )
    binary = chunks[1][1]
    if declared_bytes > len(binary) or len(binary) - declared_bytes > 3:
        raise AvatarLikenessAuthorError("component GLB BIN length is invalid")
    images = document.get("images", [])
    if not isinstance(images, list):
        raise AvatarLikenessAuthorError("component GLB images must be a list")
    buffer_views = document.get("bufferViews")
    if not isinstance(buffer_views, list) or not buffer_views:
        raise AvatarLikenessAuthorError("component GLB has no embedded buffer views")
    for index, view in enumerate(buffer_views):
        if not isinstance(view, Mapping) or view.get("buffer") != 0:
            raise AvatarLikenessAuthorError(
                f"component GLB bufferView {index} is invalid"
            )
        view_offset = _bounded_integer(
            view.get("byteOffset", 0),
            minimum=0,
            maximum=declared_bytes,
            name=f"component GLB bufferView {index} byteOffset",
        )
        view_length = _bounded_integer(
            view.get("byteLength"),
            minimum=1,
            maximum=declared_bytes,
            name=f"component GLB bufferView {index} byteLength",
        )
        if view_offset + view_length > declared_bytes:
            raise AvatarLikenessAuthorError(
                f"component GLB bufferView {index} exceeds the embedded buffer"
            )
    for image in images:
        if (
            not isinstance(image, Mapping)
            or "uri" in image
            or not isinstance(image.get("bufferView"), int)
            or isinstance(image.get("bufferView"), bool)
            or not 0 <= int(image["bufferView"]) < len(buffer_views)
        ):
            raise AvatarLikenessAuthorError(
                "component GLB image is not an embedded exact-hash dependency"
            )
    return document, binary


def _accessor_layout(
    document: Mapping[str, Any],
    binary: bytes,
    accessor_index: Any,
    *,
    name: str,
) -> dict[str, Any]:
    accessors = document.get("accessors")
    views = document.get("bufferViews")
    if not isinstance(accessors, list) or not isinstance(views, list):
        raise AvatarLikenessAuthorError(f"{name} accessor tables are missing")
    index = _bounded_integer(
        accessor_index,
        minimum=0,
        maximum=len(accessors) - 1,
        name=f"{name} accessor index",
    )
    accessor = accessors[index]
    if not isinstance(accessor, Mapping) or "sparse" in accessor:
        raise AvatarLikenessAuthorError(f"{name} accessor is invalid or sparse")
    view_index = _bounded_integer(
        accessor.get("bufferView"),
        minimum=0,
        maximum=len(views) - 1,
        name=f"{name} bufferView index",
    )
    view = views[view_index]
    if not isinstance(view, Mapping) or view.get("buffer") != 0:
        raise AvatarLikenessAuthorError(f"{name} bufferView is invalid")
    component_type = accessor.get("componentType")
    accessor_type = _text(accessor.get("type"))
    component_bytes = _ACCESSOR_COMPONENT_BYTES.get(component_type)
    component_count = _ACCESSOR_TYPE_COMPONENTS.get(accessor_type)
    if component_bytes is None or component_count is None:
        raise AvatarLikenessAuthorError(f"{name} accessor format is unsupported")
    count = _bounded_integer(
        accessor.get("count"),
        minimum=1,
        maximum=MAX_POSITION_VERTEX_COUNT,
        name=f"{name} accessor count",
    )
    element_bytes = component_bytes * component_count
    view_offset = _bounded_integer(
        view.get("byteOffset", 0),
        minimum=0,
        maximum=len(binary),
        name=f"{name} bufferView byteOffset",
    )
    view_length = _bounded_integer(
        view.get("byteLength"),
        minimum=1,
        maximum=len(binary),
        name=f"{name} bufferView byteLength",
    )
    accessor_offset = _bounded_integer(
        accessor.get("byteOffset", 0),
        minimum=0,
        maximum=view_length,
        name=f"{name} accessor byteOffset",
    )
    stride = view.get("byteStride", element_bytes)
    stride = _bounded_integer(
        stride,
        minimum=element_bytes,
        maximum=252,
        name=f"{name} byteStride",
    )
    if stride % component_bytes:
        raise AvatarLikenessAuthorError(f"{name} byteStride alignment is invalid")
    start = view_offset + accessor_offset
    end = start + (count - 1) * stride + element_bytes
    if view_offset + view_length > len(binary) or end > view_offset + view_length:
        raise AvatarLikenessAuthorError(f"{name} accessor exceeds its exact bufferView")
    return {
        "accessor": accessor,
        "index": index,
        "component_type": component_type,
        "accessor_type": accessor_type,
        "component_count": component_count,
        "component_bytes": component_bytes,
        "count": count,
        "element_bytes": element_bytes,
        "start": start,
        "stride": stride,
    }


def _position_summary(
    document: Mapping[str, Any], binary: bytes, accessor_index: Any, *, role: str
) -> dict[str, Any]:
    layout = _accessor_layout(
        document, binary, accessor_index, name=f"{role} POSITION"
    )
    if (
        layout["component_type"] != 5126
        or layout["accessor_type"] != "VEC3"
        or layout["count"] < 3
    ):
        raise AvatarLikenessAuthorError(
            f"{role} POSITION must be a float VEC3 with at least three vertices"
        )
    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    distinct: set[tuple[float, float, float]] = set()
    for item_index in range(layout["count"]):
        offset = layout["start"] + item_index * layout["stride"]
        values = struct.unpack_from("<fff", binary, offset)
        if any(
            not math.isfinite(value) or abs(value) > MAX_ABSOLUTE_POSITION
            for value in values
        ):
            raise AvatarLikenessAuthorError(
                f"{role} POSITION contains non-finite or unbounded geometry"
            )
        if len(distinct) < 3:
            distinct.add(values)
        for axis, value in enumerate(values):
            minimum[axis] = min(minimum[axis], value)
            maximum[axis] = max(maximum[axis], value)
    extents = [maximum[index] - minimum[index] for index in range(3)]
    required_axes = 3 if role == "body" else 2
    if len(distinct) < 3 or sum(value > 1e-6 for value in extents) < required_axes:
        raise AvatarLikenessAuthorError(
            f"{role} POSITION geometry is degenerate"
        )
    return {
        "accessor_index": layout["index"],
        "vertex_count": layout["count"],
        "bounds_min": minimum,
        "bounds_max": maximum,
    }


def _accessor_tuple(
    binary: bytes, layout: Mapping[str, Any], item_index: int
) -> tuple[float | int, ...]:
    format_character = {
        5120: "b",
        5121: "B",
        5122: "h",
        5123: "H",
        5125: "I",
        5126: "f",
    }.get(layout["component_type"])
    if format_character is None:
        raise AvatarLikenessAuthorError("accessor component format is unsupported")
    offset = int(layout["start"]) + item_index * int(layout["stride"])
    return struct.unpack_from(
        "<" + format_character * int(layout["component_count"]),
        binary,
        offset,
    )


def _validate_skin_binding(
    document: Mapping[str, Any],
    binary: bytes,
    *,
    node: Mapping[str, Any],
    primitives: list[Any],
    reachable_nodes: set[int],
) -> dict[str, Any]:
    skins = document.get("skins")
    if not isinstance(skins, list) or not skins:
        raise AvatarLikenessAuthorError("body component has no exported skin")
    skin_index = _bounded_integer(
        node.get("skin"),
        minimum=0,
        maximum=len(skins) - 1,
        name="body scene-node skin index",
    )
    skin = skins[skin_index]
    nodes = document.get("nodes")
    if not isinstance(skin, Mapping) or not isinstance(nodes, list):
        raise AvatarLikenessAuthorError("body skin record is invalid")
    joints = skin.get("joints")
    if (
        not isinstance(joints, list)
        or not joints
        or len(set(joints)) != len(joints)
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or item < 0
            or item >= len(nodes)
            or item not in reachable_nodes
            for item in joints
        )
    ):
        raise AvatarLikenessAuthorError(
            "body skin joints are invalid or outside the active scene"
        )
    skeleton = skin.get("skeleton")
    if skeleton is not None and (
        isinstance(skeleton, bool)
        or not isinstance(skeleton, int)
        or skeleton not in reachable_nodes
    ):
        raise AvatarLikenessAuthorError("body skeleton root is outside the active scene")
    inverse = _accessor_layout(
        document,
        binary,
        skin.get("inverseBindMatrices"),
        name="body inverse bind matrices",
    )
    if (
        inverse["component_type"] != 5126
        or inverse["accessor_type"] != "MAT4"
        or inverse["count"] != len(joints)
    ):
        raise AvatarLikenessAuthorError(
            "body inverse bind matrices do not match the exported joints"
        )
    for primitive in primitives:
        if not isinstance(primitive, Mapping):
            raise AvatarLikenessAuthorError("body mesh primitive is invalid")
        attributes = primitive.get("attributes")
        if not isinstance(attributes, Mapping):
            raise AvatarLikenessAuthorError("body mesh attributes are invalid")
        position = _accessor_layout(
            document, binary, attributes.get("POSITION"), name="body POSITION"
        )
        joints_layout = _accessor_layout(
            document, binary, attributes.get("JOINTS_0"), name="body JOINTS_0"
        )
        weights_layout = _accessor_layout(
            document, binary, attributes.get("WEIGHTS_0"), name="body WEIGHTS_0"
        )
        if (
            joints_layout["accessor_type"] != "VEC4"
            or joints_layout["component_type"] not in {5121, 5123}
            or weights_layout["accessor_type"] != "VEC4"
            or not (
                weights_layout["component_type"] == 5126
                or (
                    weights_layout["component_type"] in {5121, 5123}
                    and weights_layout["accessor"].get("normalized") is True
                )
            )
            or joints_layout["count"] != position["count"]
            or weights_layout["count"] != position["count"]
        ):
            raise AvatarLikenessAuthorError(
                "body skin attributes do not cover every POSITION vertex"
            )
        integer_weight_max = {
            5121: 255.0,
            5123: 65535.0,
        }.get(weights_layout["component_type"])
        for vertex_index in range(position["count"]):
            joint_values = _accessor_tuple(binary, joints_layout, vertex_index)
            weight_values = _accessor_tuple(binary, weights_layout, vertex_index)
            if any(int(value) < 0 or int(value) >= len(joints) for value in joint_values):
                raise AvatarLikenessAuthorError(
                    "body JOINTS_0 references a joint outside the bound skin"
                )
            normalized_weights = [
                float(value) / integer_weight_max
                if integer_weight_max is not None
                else float(value)
                for value in weight_values
            ]
            if (
                any(
                    not math.isfinite(value) or value < 0.0 or value > 1.0
                    for value in normalized_weights
                )
                or not 0.99 <= sum(normalized_weights) <= 1.01
            ):
                raise AvatarLikenessAuthorError(
                    "body WEIGHTS_0 is not finite and normalized per vertex"
                )
    return {"skin_index": skin_index, "joint_count": len(joints)}


def _validate_component_geometry(path: Path, *, role: str) -> dict[str, Any]:
    """Prove a component is self-contained and has active-scene geometry."""

    document, binary = _read_self_contained_glb(path)
    nodes = document.get("nodes")
    scenes = document.get("scenes")
    meshes = document.get("meshes")
    if (
        not isinstance(nodes, list)
        or not nodes
        or not isinstance(scenes, list)
        or not scenes
        or not isinstance(meshes, list)
        or not meshes
    ):
        raise AvatarLikenessAuthorError(
            f"{role} component lacks nodes, scenes, or meshes"
        )
    scene_index = _bounded_integer(
        document.get("scene"),
        minimum=0,
        maximum=len(scenes) - 1,
        name=f"{role} active scene index",
    )
    scene = scenes[scene_index]
    roots = scene.get("nodes") if isinstance(scene, Mapping) else None
    if not isinstance(roots, list) or not roots:
        raise AvatarLikenessAuthorError(f"{role} active scene has no root nodes")
    reachable: set[int] = set()
    visiting: set[int] = set()

    def validate_transform(node: Mapping[str, Any]) -> None:
        if "matrix" in node and any(
            field in node for field in ("translation", "rotation", "scale")
        ):
            raise AvatarLikenessAuthorError(
                f"{role} scene node mixes matrix and TRS transforms"
            )
        for field, length, absolute_limit in (
            ("matrix", 16, MAX_ABSOLUTE_POSITION),
            ("translation", 3, MAX_ABSOLUTE_POSITION),
            ("rotation", 4, 2.0),
            ("scale", 3, 1_000.0),
        ):
            if field not in node:
                continue
            values = node.get(field)
            if (
                not isinstance(values, list)
                or len(values) != length
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or abs(float(value)) > absolute_limit
                    for value in values
                )
                or (
                    field == "scale"
                    and any(abs(float(value)) < 1e-8 for value in values)
                )
            ):
                raise AvatarLikenessAuthorError(
                    f"{role} scene-node {field} transform is invalid or unbounded"
                )

    def visit(raw_index: Any) -> None:
        index = _bounded_integer(
            raw_index,
            minimum=0,
            maximum=len(nodes) - 1,
            name=f"{role} scene node index",
        )
        if index in visiting:
            raise AvatarLikenessAuthorError(f"{role} scene node graph contains a cycle")
        if index in reachable:
            return
        node = nodes[index]
        if not isinstance(node, Mapping):
            raise AvatarLikenessAuthorError(f"{role} scene node is invalid")
        validate_transform(node)
        visiting.add(index)
        children = node.get("children", [])
        if not isinstance(children, list):
            raise AvatarLikenessAuthorError(f"{role} scene-node children are invalid")
        for child in children:
            visit(child)
        visiting.remove(index)
        reachable.add(index)

    for root_index in roots:
        visit(root_index)
    referenced_meshes: set[int] = set()
    geometry_summaries: list[dict[str, Any]] = []
    body_skin_summaries: list[dict[str, Any]] = []
    total_vertices = 0
    for node_index in sorted(reachable):
        node = nodes[node_index]
        assert isinstance(node, Mapping)
        if "mesh" not in node:
            continue
        mesh_index = _bounded_integer(
            node.get("mesh"),
            minimum=0,
            maximum=len(meshes) - 1,
            name=f"{role} mesh index",
        )
        referenced_meshes.add(mesh_index)
        mesh = meshes[mesh_index]
        primitives = mesh.get("primitives") if isinstance(mesh, Mapping) else None
        if not isinstance(primitives, list) or not primitives:
            raise AvatarLikenessAuthorError(f"{role} mesh has no primitives")
        for primitive in primitives:
            if not isinstance(primitive, Mapping):
                raise AvatarLikenessAuthorError(f"{role} primitive is invalid")
            mode = primitive.get("mode", 4)
            if mode not in {4, 5, 6}:
                raise AvatarLikenessAuthorError(
                    f"{role} primitive is not a triangle surface"
                )
            attributes = primitive.get("attributes")
            if not isinstance(attributes, Mapping) or "POSITION" not in attributes:
                raise AvatarLikenessAuthorError(
                    f"{role} primitive has no POSITION geometry"
                )
            summary = _position_summary(
                document, binary, attributes["POSITION"], role=role
            )
            draw_count = summary["vertex_count"]
            if "indices" in primitive:
                indices = _accessor_layout(
                    document,
                    binary,
                    primitive.get("indices"),
                    name=f"{role} triangle indices",
                )
                if (
                    indices["accessor_type"] != "SCALAR"
                    or indices["component_type"] not in {5121, 5123, 5125}
                    or any(
                        int(_accessor_tuple(binary, indices, item_index)[0])
                        >= summary["vertex_count"]
                        for item_index in range(indices["count"])
                    )
                ):
                    raise AvatarLikenessAuthorError(
                        f"{role} triangle indices are invalid"
                    )
                draw_count = indices["count"]
            if draw_count < 3 or (mode == 4 and draw_count % 3):
                raise AvatarLikenessAuthorError(
                    f"{role} triangle draw count is invalid"
                )
            total_vertices += summary["vertex_count"]
            if total_vertices > MAX_POSITION_VERTEX_COUNT:
                raise AvatarLikenessAuthorError(
                    f"{role} component exceeds the vertex review bound"
                )
            geometry_summaries.append(summary)
        if role == "body":
            body_skin_summaries.append(
                _validate_skin_binding(
                    document,
                    binary,
                    node=node,
                    primitives=primitives,
                    reachable_nodes=reachable,
                )
            )
    if not geometry_summaries or referenced_meshes != set(range(len(meshes))):
        raise AvatarLikenessAuthorError(
            f"{role} component has missing or inactive-scene mesh geometry"
        )
    if role == "body" and not body_skin_summaries:
        raise AvatarLikenessAuthorError(
            "body component has no active-scene skinned geometry"
        )
    return {
        "self_contained_glb": True,
        "active_scene_index": scene_index,
        "active_scene_node_count": len(reachable),
        "mesh_count": len(referenced_meshes),
        "primitive_count": len(geometry_summaries),
        "position_vertex_count": total_vertices,
        "position_bounds": geometry_summaries,
        "skin_count": len(body_skin_summaries),
        "joint_count": sum(item["joint_count"] for item in body_skin_summaries),
    }


def _validate_surface_declaration(
    declaration: Mapping[str, Any],
    *,
    identity: Mapping[str, Any],
    author_job_id: str,
    base_sha256: str,
    body_sha256: str,
) -> None:
    if (
        declaration.get("schema_version") != SCHEMA_VERSION
        or _text(declaration.get("artifact_type")) != SURFACE_DECLARATION_TYPE
        or _text(declaration.get("protocol")) != PROTOCOL
        or _text(declaration.get("author_job_id")) != author_job_id
        or _text(declaration.get("candidate_id")) != _text(identity.get("candidate_id"))
        or _text(declaration.get("subject_id")) != _text(identity.get("subject_id"))
        or _text(declaration.get("base_body_sha256")).lower() != base_sha256
        or _text(declaration.get("candidate_body_sha256")).lower() != body_sha256
        or _text(declaration.get("method"))
        != "reviewed_multiview_cage_lattice_sculpt"
        or declaration.get("new_surface_authored") is not True
        or declaration.get("base_used_as_cage_only") is not True
        or declaration.get("reference_surface_copied") is not False
        or declaration.get("reference_material_or_texture_copied") is not False
        or declaration.get("identity_likeness_proven") is not False
        or declaration.get("anatomical_completeness_proven") is not False
        or declaration.get("runtime_activation_allowed") is not False
    ):
        raise AvatarLikenessAuthorError("surface authorship declaration is invalid")


def _validate_reprojection(
    report: Mapping[str, Any],
    *,
    order: Mapping[str, Any],
    body_sha256: str,
) -> None:
    if (
        report.get("schema_version") != SCHEMA_VERSION
        or _text(report.get("artifact_type")) != REPROJECTION_TYPE
        or _text(report.get("protocol")) != PROTOCOL
        or _text(report.get("author_job_id")) != _text(order.get("author_job_id"))
        or _text(report.get("candidate_body_sha256")).lower() != body_sha256
        or report.get("automatic_acceptance_allowed") is not False
        or report.get("owner_review_required") is not True
        or report.get("runtime_activation_allowed") is not False
    ):
        raise AvatarLikenessAuthorError("landmark reprojection report is invalid")
    expected = {
        item["source_id"]: {
            "source_review_sha256": item["source_review_sha256"],
            "reviewed_landmark_count": item["reviewed_landmark_count"],
        }
        for item in order.get("reviewed_source_bindings", [])
        if isinstance(item, Mapping)
    }
    records = report.get("source_results")
    if not isinstance(records, list) or len(records) != len(expected):
        raise AvatarLikenessAuthorError("reprojection report source coverage is incomplete")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise AvatarLikenessAuthorError("reprojection result is invalid")
        source_id = _text(record.get("source_id"))
        expected_record = expected.get(source_id)
        mean_error = record.get("mean_error_px")
        max_error = record.get("max_error_px")
        values = (mean_error, max_error)
        if (
            source_id in seen
            or not isinstance(expected_record, Mapping)
            or _text(record.get("source_review_sha256")).lower()
            != expected_record.get("source_review_sha256")
            or not isinstance(record.get("compared_landmark_count"), int)
            or isinstance(record.get("compared_landmark_count"), bool)
            or int(record.get("compared_landmark_count"))
            != int(expected_record.get("reviewed_landmark_count") or 0)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
                for value in values
            )
            or float(mean_error) > float(max_error)
        ):
            raise AvatarLikenessAuthorError("reprojection result binding or metric is invalid")
        seen.add(source_id)
    if seen != set(expected):
        raise AvatarLikenessAuthorError("reprojection report did not cover every reviewed source")


def _validate_rig_smoke(
    report: Mapping[str, Any], *, author_job_id: str, body_sha256: str
) -> None:
    if (
        report.get("schema_version") != SCHEMA_VERSION
        or _text(report.get("artifact_type")) != RIG_SMOKE_TYPE
        or _text(report.get("protocol")) != PROTOCOL
        or _text(report.get("author_job_id")) != author_job_id
        or _text(report.get("candidate_body_sha256")).lower() != body_sha256
        or report.get("finite_bounded_mechanical_smoke_completed") is not True
        or report.get("stable_working_rig_proven") is not False
        or report.get("visual_deformation_quality_proven") is not False
        or report.get("runtime_activation_allowed") is not False
    ):
        raise AvatarLikenessAuthorError("rig mechanical smoke declaration is invalid")


def finalize_likeness_author_outputs(
    project_root: Path, work_order_path: Path
) -> dict[str, Any]:
    """Audit worker output and stage an inactive, owner-reviewable candidate."""

    root = project_root.resolve(strict=True)
    validated = validate_likeness_author_work_order(root, work_order_path)
    order = validated["order"]
    identity = validated["identity"]
    outputs = order["required_outputs"]
    run_root = _project_output_path(
        root,
        outputs["run_root"],
        name="author run root",
        allowed_root=root / DEFAULT_CANDIDATE_SOURCE_ROOT,
    )
    worker_result_path = _project_file(
        root,
        outputs["worker_result"],
        name="worker result",
        allowed_root=run_root,
        suffixes={".json"},
    )
    worker_result = _read_json(worker_result_path, name="worker result")
    if (
        worker_result.get("schema_version") != SCHEMA_VERSION
        or _text(worker_result.get("artifact_type")) != WORKER_RESULT_TYPE
        or _text(worker_result.get("protocol")) != PROTOCOL
        or _text(worker_result.get("author_job_id")) != validated["author_job_id"]
        or _text(worker_result.get("work_order_sha256")).lower() != validated["sha256"]
        or _text(worker_result.get("capability_sha256")).lower()
        != _text(identity.get("capability_sha256"))
        or worker_result.get("runtime_activation_allowed") is not False
        or worker_result.get("public_export_allowed") is not False
    ):
        raise AvatarLikenessAuthorError("worker result binding is invalid")
    artifact_bindings = worker_result.get("artifacts")
    if not isinstance(artifact_bindings, Mapping):
        raise AvatarLikenessAuthorError("worker result has no artifact bindings")

    component_paths: dict[str, Path] = {}
    component_hashes: dict[str, str] = {}
    component_geometry: dict[str, dict[str, Any]] = {}
    for role in COMPONENT_ROLES:
        path, digest = _exact_bound_file(
            root,
            artifact_bindings.get(role),
            name=f"worker component {role}",
            expected_path=outputs["components"][role],
            allowed_root=run_root,
            suffixes={".glb"},
        )
        component_geometry[role] = _validate_component_geometry(path, role=role)
        component_paths[role] = path
        component_hashes[role] = digest
    if len(set(component_hashes.values())) != len(COMPONENT_ROLES):
        raise AvatarLikenessAuthorError("worker component artifacts are not byte-distinct")
    base_sha = _text(order["evidence_summary"]["base_body_review"].get("sha256")).lower()
    if not _valid_sha(base_sha) or component_hashes["body"] == base_sha:
        raise AvatarLikenessAuthorError("candidate body is not byte-distinct from the reviewed base")

    declarations: dict[str, dict[str, Any]] = {}
    declaration_hashes: dict[str, str] = {}
    for role in DECLARATION_ROLES:
        path, digest = _exact_bound_file(
            root,
            artifact_bindings.get(role),
            name=f"worker declaration {role}",
            expected_path=outputs["worker_declarations"][role],
            allowed_root=run_root,
            suffixes={".json"},
        )
        declarations[role] = _read_json(path, name=f"worker declaration {role}")
        declaration_hashes[role] = digest
    _validate_surface_declaration(
        declarations["surface_authorship"],
        identity=identity,
        author_job_id=validated["author_job_id"],
        base_sha256=base_sha,
        body_sha256=component_hashes["body"],
    )
    _validate_reprojection(
        declarations["landmark_reprojection"],
        order=order,
        body_sha256=component_hashes["body"],
    )
    _validate_rig_smoke(
        declarations["rig_mechanical_smoke"],
        author_job_id=validated["author_job_id"],
        body_sha256=component_hashes["body"],
    )

    render_hashes: dict[str, str] = {}
    render_dimensions: dict[str, dict[str, int]] = {}
    for role in REVIEW_RENDER_ROLES:
        path, digest = _exact_bound_file(
            root,
            artifact_bindings.get(role),
            name=f"worker review render {role}",
            expected_path=outputs["review_renders"][role],
            allowed_root=run_root,
            suffixes={".png"},
        )
        width, height = _png_dimensions(path)
        render_hashes[role] = digest
        render_dimensions[role] = {"width": width, "height": height}
    if len(set(render_hashes.values())) != len(REVIEW_RENDER_ROLES):
        raise AvatarLikenessAuthorError("review renders are not distinct")

    try:
        body_document = read_glb_json(component_paths["body"])
        rig_structure = build_rig_descriptor(
            body_document, body_sha256=component_hashes["body"]
        )
    except AvatarProductionError as exc:
        raise AvatarLikenessAuthorError(
            "body rig structure could not be validated"
        ) from exc
    rig_structure.update(
        {
            "artifact_type": "avatar_backend_rig_structure_proof",
            "author_job_id": validated["author_job_id"],
            "structural_skin_and_joint_export_proven": True,
            "stable_working_rig_proven": False,
            "visual_deformation_quality_proven": False,
            "runtime_activation_allowed": False,
        }
    )
    component_proof = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "avatar_backend_component_integrity_proof",
        "author_job_id": validated["author_job_id"],
        "candidate_id": identity["candidate_id"],
        "component_sha256": component_hashes,
        "component_geometry": component_geometry,
        "exact_hashes_verified": True,
        "separate_files_and_distinct_bytes_proven": True,
        "self_contained_active_scene_position_geometry_proven": True,
        "body_scene_skin_binding_proven": True,
        "semantic_component_role_visual_review_proven": False,
        "body_byte_distinct_from_reviewed_base": True,
        "new_surface_authorship_proven": False,
        "identity_likeness_proven": False,
        "runtime_activation_allowed": False,
    }
    backend_paths = outputs["backend_proofs"]
    component_proof_path = _project_output_path(
        root,
        backend_paths["component_integrity"],
        name="component proof output",
        allowed_root=run_root,
    )
    rig_proof_path = _project_output_path(
        root,
        backend_paths["rig_structure"],
        name="rig proof output",
        allowed_root=run_root,
    )
    _write_exclusive(
        root,
        component_proof_path,
        component_proof,
        allowed_root=run_root,
        name="component integrity proof",
    )
    _write_exclusive(
        root,
        rig_proof_path,
        rig_structure,
        allowed_root=run_root,
        name="rig structure proof",
    )
    component_authority = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "avatar_likeness_author_component_authority",
        "author_job_id": validated["author_job_id"],
        "candidate_id": identity["candidate_id"],
        "subject_id": identity["subject_id"],
        "topology_lane": identity["topology_lane"],
        "artifact_generation_succeeded": True,
        "body_sha256": component_hashes["body"],
        "hair_sha256": component_hashes["hair"],
        "eyes_sha256": component_hashes["eyes"],
        "clothes_sha256": component_hashes["clothes"],
        "clothed_review_sha256": component_hashes["clothed_review"],
        "component_integrity_sha256": sha256_file(component_proof_path),
        "rig_structure_sha256": sha256_file(rig_proof_path),
        "identity_likeness_proven": False,
        "anatomical_completeness_proven": False,
        "stable_working_rig_proven": False,
        "owner_visual_approval_proven": False,
        "adoption_requires_orchestration_hash_binding": True,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
    }
    component_authority_path = _project_output_path(
        root,
        backend_paths["component_authority"],
        name="component authority output",
        allowed_root=run_root,
    )
    _write_exclusive(
        root,
        component_authority_path,
        component_authority,
        allowed_root=run_root,
        name="component authority",
    )
    review_manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "avatar_private_owner_review_candidate_manifest",
        "protocol": PROTOCOL,
        "author_job_id": validated["author_job_id"],
        "candidate_id": identity["candidate_id"],
        "subject_id": identity["subject_id"],
        "selected_version_id": identity["selected_version_id"],
        "topology_lane": identity["topology_lane"],
        "work_order_sha256": validated["sha256"],
        "worker_result_sha256": sha256_file(worker_result_path),
        "component_sha256": component_hashes,
        "component_geometry": component_geometry,
        "worker_declaration_sha256": declaration_hashes,
        "review_render_sha256": render_hashes,
        "review_render_dimensions": render_dimensions,
        "backend_proofs": {
            "component_integrity_sha256": sha256_file(component_proof_path),
            "rig_structure_sha256": sha256_file(rig_proof_path),
            "component_authority_sha256": sha256_file(component_authority_path),
        },
        "private_owner_review_ready": True,
        "owner_visual_approval_proven": False,
        "new_surface_worker_declared": True,
        "new_surface_authorship_proven": False,
        "landmark_metrics_present_not_approved": True,
        "identity_likeness_proven": False,
        "anatomical_completeness_proven": False,
        "stable_working_rig_proven": False,
        "visual_deformation_quality_proven": False,
        "facial_and_lip_sync_controls_proven": False,
        "wearable_behavior_proven": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "Exact output hashes, file separation, a structural skin, reviewed-input bindings, "
            "reported reprojection metrics, and clothed review views are present. The worker's "
            "new-surface declaration is not independent proof of likeness, anatomy, deformation, "
            "clothing behavior, or owner approval. Nothing may activate."
        ),
    }
    review_manifest_path = _project_output_path(
        root,
        backend_paths["review_candidate_manifest"],
        name="review candidate manifest output",
        allowed_root=run_root,
    )
    created = _write_exclusive(
        root,
        review_manifest_path,
        review_manifest,
        allowed_root=run_root,
        name="private review candidate manifest",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "staged_for_private_owner_review_not_approved" if created else "already_staged_verified",
        "candidate_id": identity["candidate_id"],
        "author_job_id": validated["author_job_id"],
        "review_candidate_manifest": _relative(review_manifest_path, root),
        "review_candidate_manifest_sha256": sha256_file(review_manifest_path),
        "private_owner_review_ready": True,
        "identity_likeness_proven": False,
        "stable_working_rig_proven": False,
        "runtime_activation_allowed": False,
    }


__all__ = [
    "AvatarLikenessAuthorError",
    "DEFAULT_CAPABILITY_PATH",
    "PROTOCOL",
    "finalize_likeness_author_outputs",
    "inspect_author_tooling",
    "prepare_likeness_author_work_order",
    "validate_likeness_author_work_order",
    "validate_queued_evidence_job",
]
