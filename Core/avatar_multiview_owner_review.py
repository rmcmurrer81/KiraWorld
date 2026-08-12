"""Local-only owner review authoring for multiview avatar evidence.

This module writes exact-hash review artifacts and updates their bindings in a
private multiview manifest.  It deliberately has no queue, mesh, render,
runtime, export, or activation operation.  Every approval requires explicit
owner-supplied confirmations and an optimistic manifest SHA-256 binding.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time
from typing import Any, Mapping

from Core import avatar_multiview_authoring as authoring
from Core.avatar_body_topology import inspect_glb_topology
from Core.avatar_profile_preflight import (
    AvatarProfilePreflightError,
    evaluate_avatar_profile_preflight,
    identity_registry_available,
)


OWNER_REVIEW_SCHEMA_VERSION = 1
OWNER_REVIEW_ROOT = Path(
    "Avatar/avatar_builder/multiview_authoring/private_reviews"
)
PRIVATE_MANIFEST_ROOT = Path(
    "Avatar/avatar_builder/multiview_authoring/manifests/private"
)
BASE_AUTHORITY_CATALOG_PATH = Path(
    "Avatar/avatar_builder/multiview_authoring/base_catalog/authority.json"
)
ASSET_LIBRARY_MANIFEST_PATH = Path(
    "Avatar/avatar_builder/asset_library/manifest.json"
)
BASE_LIBRARY_ROOT = Path(
    "Avatar/avatar_builder/asset_library/base_body_reference"
)
CANONICAL_GWEN_CANDIDATE_ID = "spider_gwen_spider_gwen_20260606_013325"
SUPERSEDED_GWEN_CANDIDATE_ID = (
    "spider_gwen_adult_avatar_project_variant_20260716"
)
MAX_NOTES_LENGTH = 4000
MAX_LANDMARKS_PER_SOURCE = 512
BASE_STRUCTURAL_METRICS = (
    "mesh_count",
    "primitive_count",
    "referenced_position_vertex_count",
    "indexed_or_sequential_triangle_count",
    "skin_count",
    "unique_joint_count",
    "maximum_joints_in_one_skin",
    "weighted_primitive_count",
    "weighted_skinned_primitive_count",
    "unweighted_skinned_primitive_count",
    "invalid_joint_reference_count",
    "invalid_accessor_reference_count",
    "invalid_attribute_layout_count",
    "triangle_element_remainder_count",
)


class AvatarOwnerReviewError(ValueError):
    """A fail-closed owner-review request error."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _notes(value: Any) -> str:
    notes = _text(value)
    if len(notes) > MAX_NOTES_LENGTH:
        raise AvatarOwnerReviewError("review notes are too long")
    return notes


def _require_true(payload: Mapping[str, Any], field: str) -> None:
    if payload.get(field) is not True:
        raise AvatarOwnerReviewError(f"explicit confirmation required: {field}")


def _require_exact(
    payload: Mapping[str, Any], field: str, expected: str
) -> None:
    if _text(payload.get(field)) != expected:
        raise AvatarOwnerReviewError(f"exact confirmation mismatch: {field}")


def _private_manifest_file(project_root: Path, manifest_path: Path) -> Path:
    """Resolve exactly one regular manifest below the documented private root."""

    root = project_root.resolve(strict=True)
    try:
        path = authoring._manifest_file(root, manifest_path)
        private_root = (root / PRIVATE_MANIFEST_ROOT).resolve(strict=True)
        path.relative_to(private_root)
    except (authoring.AvatarMultiviewError, OSError, ValueError) as exc:
        raise AvatarOwnerReviewError(
            "owner-review manifest must be a regular JSON file below "
            f"{PRIVATE_MANIFEST_ROOT.as_posix()}"
        ) from exc
    if path.suffix.lower() != ".json":
        raise AvatarOwnerReviewError("owner-review manifest must be JSON")
    return path


def _canonical_route_preflight(
    project_root: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind the manifest route to the canonical identity registry and profile."""

    root = project_root.resolve(strict=True)
    candidate_id = _text(manifest.get("candidate_id"))
    subject_id = _text(manifest.get("subject_id"))
    version_id = _text(manifest.get("selected_version_id"))
    topology_lane = _text(manifest.get("topology_lane"))
    requested_maturity = {
        "confirmed_adult_topology": "adult",
        "non_adult_doll_safe_topology": "non_adult_doll_safe",
    }.get(topology_lane, "")
    if not identity_registry_available(root):
        raise AvatarOwnerReviewError(
            "canonical candidate identity registry is unavailable"
        )
    try:
        result = evaluate_avatar_profile_preflight(
            root,
            candidate_id,
            requested_subject_id=subject_id,
            requested_maturity_class=requested_maturity,
        )
    except AvatarProfilePreflightError as exc:
        raise AvatarOwnerReviewError(
            f"canonical candidate preflight could not be verified: {exc}"
        ) from exc
    failures = result.get("failures")
    if result.get("authoring_allowed") is not True:
        failure_text = ", ".join(str(item) for item in failures or [])
        raise AvatarOwnerReviewError(
            "canonical candidate preflight blocked owner review"
            + (f": {failure_text}" if failure_text else "")
        )
    identity = result.get("identity")
    maturity = result.get("maturity")
    registry = result.get("registry")
    profile = result.get("canonical_profile")
    if not all(
        isinstance(item, Mapping)
        for item in (identity, maturity, registry, profile)
    ):
        raise AvatarOwnerReviewError("canonical candidate preflight is incomplete")
    if _text(identity.get("subject_id")) != subject_id:
        raise AvatarOwnerReviewError("canonical subject route does not match manifest")
    if _text(maturity.get("safety_topology_lane")) != topology_lane:
        raise AvatarOwnerReviewError(
            "canonical maturity topology route does not match manifest"
        )
    version_required = identity.get("version_required") is True
    canonical_version = _text(identity.get("selected_version"))
    if version_required and canonical_version != version_id:
        raise AvatarOwnerReviewError(
            "canonical selected version does not match manifest"
        )
    registry_sha = _text(registry.get("sha256")).lower()
    profile_sha = _text(profile.get("sha256")).lower()
    if not all(
        authoring.SHA256_RE.fullmatch(value)
        for value in (registry_sha, profile_sha)
    ):
        raise AvatarOwnerReviewError("canonical route hashes are invalid")
    return {
        "requested_candidate_id": candidate_id,
        "canonical_candidate_id": _text(result.get("canonical_candidate_id")),
        "candidate_alias_used": result.get("candidate_alias_used") is True,
        "canonical_subject_id": _text(identity.get("subject_id")),
        "canonical_selected_version_id": canonical_version,
        "version_required": version_required,
        "canonical_maturity_lane": _text(maturity.get("lane")),
        "canonical_topology_lane": _text(maturity.get("safety_topology_lane")),
        "registry_sha256": registry_sha,
        "canonical_profile_sha256": profile_sha,
        "runtime_activation_allowed": False,
    }


def _load_manifest(
    project_root: Path,
    manifest_path: Path,
    *,
    expected_manifest_sha256: str = "",
) -> tuple[Path, dict[str, Any], str, dict[str, Any]]:
    root = project_root.resolve(strict=True)
    try:
        path = _private_manifest_file(root, manifest_path)
        digest = authoring.sha256_file(path)
        manifest = authoring._read_json_object(path)
    except (authoring.AvatarMultiviewError, AvatarOwnerReviewError) as exc:
        raise AvatarOwnerReviewError(str(exc)) from exc
    expected = _text(expected_manifest_sha256).lower()
    if expected and (
        not authoring.SHA256_RE.fullmatch(expected) or digest != expected
    ):
        raise AvatarOwnerReviewError(
            "manifest changed since the review page was loaded; refresh before saving"
        )
    _validate_private_review_manifest(manifest)
    canonical_route = _canonical_route_preflight(root, manifest)
    return path, manifest, digest, canonical_route


def _validate_private_review_manifest(manifest: Mapping[str, Any]) -> None:
    candidate_id = _text(manifest.get("candidate_id"))
    subject_id = _text(manifest.get("subject_id"))
    version_id = _text(manifest.get("selected_version_id"))
    topology_lane = _text(manifest.get("topology_lane"))
    if manifest.get("schema_version") != authoring.SCHEMA_VERSION:
        raise AvatarOwnerReviewError("unsupported multiview manifest schema")
    if _text(manifest.get("manifest_type")) != authoring.MANIFEST_TYPE:
        raise AvatarOwnerReviewError("manifest is not multiview likeness evidence")
    if not all(authoring.SAFE_ID_RE.fullmatch(item) for item in (
        candidate_id,
        subject_id,
        version_id,
    )):
        raise AvatarOwnerReviewError("candidate, subject, or version ID is invalid")
    if topology_lane not in authoring.TOPOLOGY_LANES:
        raise AvatarOwnerReviewError("topology lane is invalid")
    if _text(manifest.get("output_rule")) != authoring.OUTPUT_RULE:
        raise AvatarOwnerReviewError("manifest is not private-review-only")
    if manifest.get("runtime_activation_requested") is not False:
        raise AvatarOwnerReviewError("runtime activation must remain false")
    if manifest.get("public_export_allowed") is not False:
        raise AvatarOwnerReviewError("public export must remain false")
    if "private" not in _normalized(manifest.get("visibility")):
        raise AvatarOwnerReviewError("manifest visibility is not private")
    if (
        candidate_id == SUPERSEDED_GWEN_CANDIDATE_ID
        or _normalized(manifest.get("authoring_status"))
        == "superseded_audit_only"
        or manifest.get("queue_eligible") is False
    ):
        raise AvatarOwnerReviewError(
            "superseded audit manifest cannot be owner-reviewed; use canonical Gwen "
            f"{CANONICAL_GWEN_CANDIDATE_ID}"
        )


def _catalog_file(project_root: Path, relative: Path, *, name: str) -> Path:
    try:
        return authoring._project_file(
            project_root,
            relative.as_posix(),
            name=name,
            suffixes={".json"},
        )
    except authoring.AvatarMultiviewError as exc:
        raise AvatarOwnerReviewError(str(exc)) from exc


def _load_audited_base_catalog(
    project_root: Path, topology_lane: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load exact catalog/asset bindings and live-audit every selectable base."""

    root = project_root.resolve(strict=True)
    catalog_path = _catalog_file(
        root, BASE_AUTHORITY_CATALOG_PATH, name="base authority catalog"
    )
    catalog_sha = authoring.sha256_file(catalog_path)
    try:
        catalog = authoring._read_json_object(catalog_path)
    except authoring.AvatarMultiviewError as exc:
        raise AvatarOwnerReviewError(str(exc)) from exc
    if (
        catalog.get("schema_version") != 1
        or _text(catalog.get("artifact_type"))
        != "avatar_multiview_base_authority_catalog"
        or _text(catalog.get("catalog_status"))
        != "active_structural_and_maturity_audit"
    ):
        raise AvatarOwnerReviewError("base authority catalog header is invalid")
    asset_binding = catalog.get("asset_library_manifest")
    if not isinstance(asset_binding, Mapping):
        raise AvatarOwnerReviewError("base catalog asset-library binding is missing")
    if _text(asset_binding.get("path")) != ASSET_LIBRARY_MANIFEST_PATH.as_posix():
        raise AvatarOwnerReviewError("base catalog asset-library path is not canonical")
    asset_manifest_path = _catalog_file(
        root, ASSET_LIBRARY_MANIFEST_PATH, name="asset library manifest"
    )
    asset_manifest_sha = authoring.sha256_file(asset_manifest_path)
    expected_asset_sha = _text(asset_binding.get("sha256")).lower()
    if (
        not authoring.SHA256_RE.fullmatch(expected_asset_sha)
        or asset_manifest_sha != expected_asset_sha
    ):
        raise AvatarOwnerReviewError("asset library manifest exact hash changed")
    try:
        asset_manifest = authoring._read_json_object(asset_manifest_path)
    except authoring.AvatarMultiviewError as exc:
        raise AvatarOwnerReviewError(str(exc)) from exc
    records = asset_manifest.get("records")
    entries = catalog.get("entries")
    if not isinstance(records, list) or not isinstance(entries, list):
        raise AvatarOwnerReviewError("base catalog or asset records are invalid")
    if len(entries) > 64:
        raise AvatarOwnerReviewError("base authority catalog is too large")

    options: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise AvatarOwnerReviewError(f"base catalog entry {index} is invalid")
        base_id = _text(entry.get("base_id"))
        entry_lane = _text(entry.get("topology_lane"))
        relative_path = _text(entry.get("path"))
        expected_sha = _text(entry.get("sha256")).lower()
        asset_record_id = _text(entry.get("asset_library_record_id"))
        if (
            not authoring.SAFE_ID_RE.fullmatch(base_id)
            or base_id in seen_ids
            or entry_lane not in authoring.TOPOLOGY_LANES
            or not authoring.SHA256_RE.fullmatch(expected_sha)
            or not asset_record_id
            or len(asset_record_id) > 512
        ):
            raise AvatarOwnerReviewError(f"base catalog entry {index} identity is invalid")
        raw_path = Path(relative_path)
        try:
            raw_path.relative_to(BASE_LIBRARY_ROOT)
        except ValueError as exc:
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} is outside the base-body library"
            ) from exc
        if relative_path in seen_paths:
            raise AvatarOwnerReviewError("base catalog path is duplicated")
        try:
            base_path = authoring._project_file(
                root,
                relative_path,
                name=f"base catalog entry {base_id}",
                suffixes={".glb"},
            )
        except authoring.AvatarMultiviewError as exc:
            raise AvatarOwnerReviewError(str(exc)) from exc
        actual_sha = authoring.sha256_file(base_path)
        if actual_sha != expected_sha:
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} exact hash changed"
            )
        if (
            _text(entry.get("allowed_use"))
            != "cage_fit_source_new_surface_required"
            or entry.get("copy_as_candidate_body_allowed") is not False
            or entry.get("stable_working_rig_proven") is not False
            or entry.get("anatomical_completeness_proven") is not False
        ):
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} overstates its allowed use or proof"
            )

        matches = [
            record
            for record in records
            if isinstance(record, Mapping)
            and _text(record.get("id")) == asset_record_id
            and _text(record.get("local_file")) == relative_path
            and _text(record.get("sha256")).lower() == expected_sha
            and _text(record.get("category")) == "base_body_reference"
        ]
        if len(matches) != 1:
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} lacks one exact asset-library authority"
            )
        asset_record = matches[0]
        maturity = entry.get("maturity_authority")
        if not isinstance(maturity, Mapping):
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} maturity authority is missing"
            )
        maturity_adult_only = maturity.get("adult_only")
        maturity_non_adult = maturity.get("allowed_for_non_adult")
        record_adult_only = asset_record.get("adult_only")
        record_non_adult = asset_record.get("allowed_for_non_adult")
        if (
            not all(
                isinstance(value, bool)
                for value in (
                    maturity_adult_only,
                    maturity_non_adult,
                    record_adult_only,
                    record_non_adult,
                )
            )
            or record_adult_only != maturity_adult_only
            or record_non_adult != maturity_non_adult
        ):
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} maturity authority changed"
            )
        adult_only = maturity_adult_only is True
        allowed_for_non_adult = maturity_non_adult is True
        if entry_lane == "confirmed_adult_topology":
            maturity_ready = adult_only and not allowed_for_non_adult
        else:
            maturity_ready = not adult_only and allowed_for_non_adult
        if not maturity_ready:
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} is not authorized for its maturity lane"
            )

        audit = entry.get("structural_audit")
        expected_metrics = audit.get("metrics") if isinstance(audit, Mapping) else None
        if (
            not isinstance(audit, Mapping)
            or _text(audit.get("method")) != "non_rendering_glb_structure_v1"
            or _text(audit.get("minimum_gate")) != "weighted_skinned_cage_v1"
            or audit.get("valid_glb") is not True
            or not isinstance(expected_metrics, Mapping)
        ):
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} structural audit is invalid"
            )
        report = inspect_glb_topology(base_path, artifact_id=base_id)
        metrics = report.get("topology_metrics")
        if (
            not isinstance(metrics, Mapping)
            or report.get("valid_glb") is not True
            or _text(report.get("sha256")).lower() != expected_sha
        ):
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} is not a valid audited GLB"
            )
        for metric in BASE_STRUCTURAL_METRICS:
            expected_value = expected_metrics.get(metric)
            if (
                not isinstance(expected_value, int)
                or isinstance(expected_value, bool)
                or metrics.get(metric) != expected_value
            ):
                raise AvatarOwnerReviewError(
                    f"base catalog entry {base_id} structural metric changed: {metric}"
                )
        structural_ready = bool(
            metrics.get("mesh_count", 0) >= 1
            and metrics.get("primitive_count", 0) >= 1
            and metrics.get("referenced_position_vertex_count", 0) >= 100
            and metrics.get("indexed_or_sequential_triangle_count", 0) >= 100
            and metrics.get("skin_count", 0) >= 1
            and metrics.get("unique_joint_count", 0) >= 15
            and metrics.get("maximum_joints_in_one_skin", 0) >= 15
            and metrics.get("weighted_primitive_count", 0) >= 1
            and metrics.get("weighted_skinned_primitive_count", 0) >= 1
            and metrics.get("unweighted_skinned_primitive_count", 0) == 0
            and all(metrics.get(name, 0) == 0 for name in (
                "invalid_joint_reference_count",
                "invalid_accessor_reference_count",
                "invalid_attribute_layout_count",
                "triangle_element_remainder_count",
            ))
        )
        if not structural_ready:
            raise AvatarOwnerReviewError(
                f"base catalog entry {base_id} no longer passes the weighted cage gate"
            )
        public = {
            "base_id": base_id,
            "project_relative_path": relative_path,
            "sha256": expected_sha,
            "topology_lane": entry_lane,
            "asset_library_record_id": asset_record_id,
            "usage_policy": _text(asset_record.get("usage_policy")),
            "structural_proof": {
                "gate": "weighted_skinned_cage_v1",
                "gate_passed": True,
                "metrics": {name: metrics[name] for name in BASE_STRUCTURAL_METRICS},
                "humanoid_rig_structurally_ready": report.get(
                    "humanoid_rig_structurally_ready"
                ) is True,
                "stable_working_rig_proven": False,
                "anatomical_completeness_proven": False,
            },
            "maturity_authority": {
                "adult_only": adult_only,
                "allowed_for_non_adult": allowed_for_non_adult,
                "topology_lane": entry_lane,
                "lane_match": entry_lane == topology_lane,
            },
            "copy_as_candidate_body_allowed": False,
        }
        seen_ids.add(base_id)
        seen_paths.add(relative_path)
        if entry_lane == topology_lane:
            options[base_id] = {**public, "_path": base_path}

    public_options = [
        {key: value for key, value in option.items() if key != "_path"}
        for _, option in sorted(options.items())
    ]
    return {
        "status": (
            "ready" if public_options else "no_audited_base_for_topology_lane"
        ),
        "catalog_sha256": catalog_sha,
        "asset_library_manifest_sha256": asset_manifest_sha,
        "topology_lane": topology_lane,
        "options": public_options,
        "stable_working_rig_proven": False,
        "anatomical_completeness_proven": False,
    }, options


@contextmanager
def _manifest_process_lock(path: Path, *, timeout_seconds: float = 10.0):
    """Serialize cooperative writers across processes using a sibling lock file."""

    lock_path = path.parent / f".{path.name}.owner-review.lock"
    if lock_path.is_symlink():
        raise AvatarOwnerReviewError("manifest lock path cannot be a symlink")
    handle = lock_path.open("a+b")
    acquired = False
    try:
        if lock_path.is_symlink():
            raise AvatarOwnerReviewError("manifest lock path cannot be a symlink")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        deadline = time.monotonic() + timeout_seconds
        while not acquired:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise AvatarOwnerReviewError(
                        "timed out waiting for the manifest save lock"
                    ) from exc
                time.sleep(0.02)
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _verified_source(
    project_root: Path,
    manifest: Mapping[str, Any],
    source_id: str,
) -> tuple[dict[str, Any], Path, str, int, int]:
    sources = manifest.get("source_images")
    if not isinstance(sources, list) or len(sources) > 64:
        raise AvatarOwnerReviewError("source image list is invalid")
    matches = [
        item
        for item in sources
        if isinstance(item, dict) and _text(item.get("source_id")) == source_id
    ]
    if len(matches) != 1:
        raise AvatarOwnerReviewError("source ID is missing or duplicated")
    source = matches[0]
    try:
        path = authoring._project_file(
            project_root,
            source.get("source_path"),
            name=f"source_images.{source_id}.source_path",
            suffixes=authoring.IMAGE_SUFFIXES,
        )
        actual_sha = authoring.sha256_file(path)
        expected_sha = _text(source.get("sha256")).lower()
        if (
            not authoring.SHA256_RE.fullmatch(expected_sha)
            or actual_sha != expected_sha
        ):
            raise AvatarOwnerReviewError("source image exact hash changed")
        width, height = authoring._image_dimensions(path)
    except authoring.AvatarMultiviewError as exc:
        raise AvatarOwnerReviewError(str(exc)) from exc
    dimensions = source.get("dimensions")
    if not isinstance(dimensions, Mapping) or (
        dimensions.get("width") != width
        or dimensions.get("height") != height
    ):
        raise AvatarOwnerReviewError("source image native dimensions changed")
    return source, path, actual_sha, width, height


def _safe_review_artifact(
    project_root: Path,
    binding: Any,
) -> dict[str, Any] | None:
    if not isinstance(binding, Mapping):
        return None
    try:
        _, artifact, _ = authoring._binding_artifact(
            project_root, binding, name="owner_review_artifact"
        )
    except authoring.AvatarMultiviewError:
        return None
    return artifact


def _source_review_summary(
    project_root: Path,
    source: Mapping[str, Any],
) -> dict[str, Any] | None:
    artifact = _safe_review_artifact(project_root, source.get("review_artifact"))
    if not artifact:
        return None
    crop = artifact.get("crop_pixels")
    calibration = artifact.get("calibration")
    landmarks = artifact.get("landmarks")
    return {
        "review_status": _text(artifact.get("review_status")),
        "reviewed_by": _text(artifact.get("reviewed_by")),
        "reviewed_at": _text(artifact.get("reviewed_at")),
        "view_label": _text(artifact.get("view_label")),
        "crop_pixels": dict(crop) if isinstance(crop, Mapping) else None,
        "calibration": dict(calibration)
        if isinstance(calibration, Mapping)
        else None,
        "landmarks": [dict(item) for item in landmarks if isinstance(item, Mapping)]
        if isinstance(landmarks, list)
        else [],
        "review_notes": _text(artifact.get("review_notes")),
    }


def load_owner_review_session(
    project_root: Path,
    manifest_path: Path,
    *,
    reviewer_id: str,
) -> dict[str, Any]:
    """Return a local-UI session summary without filesystem source paths."""

    root = project_root.resolve(strict=True)
    if not authoring.SAFE_ID_RE.fullmatch(_text(reviewer_id)):
        raise AvatarOwnerReviewError("reviewer ID is invalid")
    path, manifest, digest, canonical_route = _load_manifest(root, manifest_path)
    sources = manifest.get("source_images")
    if not isinstance(sources, list):
        raise AvatarOwnerReviewError("source image list is invalid")
    source_summaries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for raw_source in sources:
        if not isinstance(raw_source, Mapping):
            raise AvatarOwnerReviewError("source image record is invalid")
        source_id = _text(raw_source.get("source_id"))
        if (
            not authoring.SAFE_ID_RE.fullmatch(source_id)
            or source_id in seen_ids
        ):
            raise AvatarOwnerReviewError("source image ID is invalid or duplicated")
        source, _, source_sha, width, height = _verified_source(
            root, manifest, source_id
        )
        if source_sha in seen_hashes:
            raise AvatarOwnerReviewError("source image exact hash is duplicated")
        seen_ids.add(source_id)
        seen_hashes.add(source_sha)
        source_summaries.append(
            {
                "source_id": source_id,
                "sha256": source_sha,
                "dimensions": {"width": width, "height": height},
                "media_type": _media_type_for_suffix(
                    Path(_text(source.get("source_path"))).suffix
                ),
                "review": _source_review_summary(root, source),
            }
        )
    evaluation = authoring.evaluate_multiview_manifest(root, path)
    scale_artifact = _safe_review_artifact(
        root, manifest.get("scale_review_artifact")
    )
    base = manifest.get("base_body")
    base_summary: dict[str, Any] | None = None
    if isinstance(base, Mapping) and not _normalized(base.get("status")).startswith(
        "pending"
    ):
        base_summary = {
            "status": _text(base.get("status")),
            "sha256": _text(base.get("sha256")),
            "topology_lane": _text(base.get("topology_lane")),
            "project_relative_path": _text(base.get("path")),
            "base_authority_id": _text(base.get("base_authority_id")),
            "review_bound": isinstance(base.get("review_artifact"), Mapping),
        }
    try:
        base_catalog, _ = _load_audited_base_catalog(
            root, _text(manifest.get("topology_lane"))
        )
    except AvatarOwnerReviewError as exc:
        base_catalog = {
            "status": "not_ready",
            "reason": str(exc),
            "catalog_sha256": "",
            "asset_library_manifest_sha256": "",
            "topology_lane": _text(manifest.get("topology_lane")),
            "options": [],
            "stable_working_rig_proven": False,
            "anatomical_completeness_proven": False,
        }
    return {
        "schema_version": OWNER_REVIEW_SCHEMA_VERSION,
        "mode": "local_owner_review_only",
        "candidate_id": _text(manifest.get("candidate_id")),
        "subject_id": _text(manifest.get("subject_id")),
        "selected_version_id": _text(manifest.get("selected_version_id")),
        "topology_lane": _text(manifest.get("topology_lane")),
        "reviewer_id": reviewer_id,
        "manifest_sha256": digest,
        "canonical_route": canonical_route,
        "allowed_views": sorted(authoring.ALLOWED_VIEWS),
        "camera_models": sorted(authoring.CAMERA_MODELS),
        "required_landmark_regions": sorted(
            authoring.REQUIRED_LANDMARK_REGIONS
        ),
        "source_images": source_summaries,
        "scale_review": {
            "status": _text(scale_artifact.get("review_status"))
            if scale_artifact
            else "pending",
            "mode": _text(scale_artifact.get("scale_mode"))
            if scale_artifact
            else "pending",
            "target_height_m": scale_artifact.get("target_height_m")
            if scale_artifact
            else None,
            "review_notes": _text(scale_artifact.get("review_notes"))
            if scale_artifact
            else "",
        },
        "base_body_review": base_summary,
        "base_authority_catalog": base_catalog,
        "evaluation": evaluation,
        "queue_operation_available": False,
        "mesh_operation_available": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "This session can only create exact-hash owner review artifacts. "
            "It cannot queue, build, render, export, or activate an avatar."
        ),
    }


def resolve_exact_source_image(
    project_root: Path,
    manifest_path: Path,
    *,
    source_id: str,
    expected_manifest_sha256: str,
    expected_source_sha256: str,
) -> tuple[Path, str, int]:
    """Resolve one enrolled source after rechecking manifest and source hashes."""

    root = project_root.resolve(strict=True)
    _, manifest, _, _ = _load_manifest(
        root,
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    _, source_path, source_sha, _, _ = _verified_source(
        root, manifest, source_id
    )
    if source_sha != _text(expected_source_sha256).lower():
        raise AvatarOwnerReviewError("source image hash binding mismatch")
    return source_path, _media_type_for_suffix(source_path.suffix), source_path.stat().st_size


def _media_type_for_suffix(suffix: str) -> str:
    return {
        ".bmp": "image/bmp",
        ".gif": "image/gif",
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix.lower(), "application/octet-stream")


def _write_immutable_artifact(
    project_root: Path,
    *,
    candidate_id: str,
    artifact_kind: str,
    artifact: Mapping[str, Any],
) -> dict[str, str]:
    root = project_root.resolve(strict=True)
    if not authoring.SAFE_ID_RE.fullmatch(candidate_id):
        raise AvatarOwnerReviewError("candidate ID is unsafe")
    if not authoring.SAFE_ID_RE.fullmatch(artifact_kind):
        raise AvatarOwnerReviewError("artifact kind is unsafe")
    encoded = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    digest = hashlib.sha256(encoded).hexdigest()
    relative = OWNER_REVIEW_ROOT / candidate_id / artifact_kind / f"{digest}.json"
    destination = root / relative
    if authoring._has_symlink_component(destination, root):
        raise AvatarOwnerReviewError("review artifact destination contains a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        resolved_parent = destination.parent.resolve(strict=True)
        resolved_parent.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AvatarOwnerReviewError(
            "review artifact destination escapes the project"
        ) from exc
    try:
        with destination.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if (
            destination.is_symlink()
            or not destination.is_file()
            or destination.read_bytes() != encoded
        ):
            raise AvatarOwnerReviewError(
                "immutable owner review artifact path changed"
            )
    return {"path": relative.as_posix(), "sha256": digest}


def _commit_manifest(
    project_root: Path,
    manifest_path: Path,
    *,
    expected_manifest_sha256: str,
    manifest: Mapping[str, Any],
    expected_canonical_route: Mapping[str, Any],
) -> str:
    root = project_root.resolve(strict=True)
    path = _private_manifest_file(root, manifest_path)
    with _manifest_process_lock(path):
        path = _private_manifest_file(root, path)
        if (
            path.is_symlink()
            or authoring.sha256_file(path) != expected_manifest_sha256
        ):
            raise AvatarOwnerReviewError(
                "manifest changed before commit; review artifact was not bound"
            )
        _validate_private_review_manifest(manifest)
        canonical_route = _canonical_route_preflight(root, manifest)
        if dict(expected_canonical_route) != canonical_route:
            raise AvatarOwnerReviewError(
                "canonical registry/profile route changed before commit"
            )
        encoded = json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ).encode("utf-8") + b"\n"
        encoded_sha = hashlib.sha256(encoded).hexdigest()
        temporary = path.parent / f".{path.name}.{secrets.token_hex(12)}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        if authoring.sha256_file(path) != encoded_sha:
            raise AvatarOwnerReviewError(
                "manifest changed during commit; refresh before continuing"
            )
        return encoded_sha


def _save_result(
    project_root: Path,
    manifest_path: Path,
    *,
    artifact_sha256: str,
) -> dict[str, Any]:
    root = project_root.resolve(strict=True)
    path = _private_manifest_file(root, manifest_path)
    evaluation = authoring.evaluate_multiview_manifest(root, path)
    return {
        "status": "owner_review_artifact_saved_and_hash_bound",
        "artifact_sha256": artifact_sha256,
        "manifest_sha256": authoring.sha256_file(path),
        "evaluation": evaluation,
        "body_queued": False,
        "mesh_created": False,
        "runtime_activation_allowed": False,
    }


def save_source_owner_review(
    project_root: Path,
    manifest_path: Path,
    *,
    reviewer_id: str,
    expected_manifest_sha256: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Save one explicit identity/view/crop/calibration/landmark review."""

    root = project_root.resolve(strict=True)
    path, manifest, manifest_sha, canonical_route = _load_manifest(
        root,
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if not authoring.SAFE_ID_RE.fullmatch(_text(reviewer_id)):
        raise AvatarOwnerReviewError("reviewer ID is invalid")
    candidate_id = _text(manifest.get("candidate_id"))
    subject_id = _text(manifest.get("subject_id"))
    version_id = _text(manifest.get("selected_version_id"))
    source_id = _text(payload.get("source_id"))
    source, _, source_sha, width, height = _verified_source(
        root, manifest, source_id
    )
    _require_exact(payload, "confirm_candidate_id", candidate_id)
    _require_exact(payload, "confirm_subject_id", subject_id)
    _require_exact(payload, "confirm_selected_version_id", version_id)
    _require_exact(payload, "confirm_source_sha256", source_sha)
    for field in (
        "same_subject_confirmed",
        "selected_version_confirmed",
        "confirm_crop",
        "confirm_calibration",
        "confirm_landmarks",
        "approve_source_review",
    ):
        _require_true(payload, field)
    view_label = _normalized(payload.get("view_label"))
    if view_label not in authoring.ALLOWED_VIEWS:
        raise AvatarOwnerReviewError("view label is invalid")
    crop = payload.get("crop_pixels")
    if not isinstance(crop, Mapping):
        raise AvatarOwnerReviewError("review crop is missing")
    try:
        crop_values = {
            "x": int(crop.get("x")),
            "y": int(crop.get("y")),
            "width": int(crop.get("width")),
            "height": int(crop.get("height")),
        }
    except (TypeError, ValueError) as exc:
        raise AvatarOwnerReviewError("review crop is invalid") from exc
    if (
        crop_values["x"] < 0
        or crop_values["y"] < 0
        or crop_values["width"] < 1
        or crop_values["height"] < 1
        or crop_values["x"] + crop_values["width"] > width
        or crop_values["y"] + crop_values["height"] > height
    ):
        raise AvatarOwnerReviewError("review crop is out of source bounds")
    calibration = payload.get("calibration")
    if not isinstance(calibration, Mapping):
        raise AvatarOwnerReviewError("calibration review is missing")
    camera_model = _normalized(calibration.get("camera_model"))
    coordinate_frame_id = _text(calibration.get("coordinate_frame_id"))
    if (
        camera_model not in authoring.CAMERA_MODELS
        or not authoring.SAFE_ID_RE.fullmatch(coordinate_frame_id)
    ):
        raise AvatarOwnerReviewError("calibration review is invalid")
    landmarks = payload.get("landmarks")
    if (
        not isinstance(landmarks, list)
        or not landmarks
        or len(landmarks) > MAX_LANDMARKS_PER_SOURCE
    ):
        raise AvatarOwnerReviewError("landmark review must be a bounded nonempty list")
    reviewed_landmarks: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, landmark in enumerate(landmarks):
        if not isinstance(landmark, Mapping):
            raise AvatarOwnerReviewError(f"landmark {index} is invalid")
        name = _text(landmark.get("name"))
        region = _normalized(landmark.get("region"))
        if (
            not name
            or len(name) > 120
            or name in names
            or region not in authoring.REQUIRED_LANDMARK_REGIONS
            or landmark.get("reviewed") is not True
        ):
            raise AvatarOwnerReviewError(
                f"landmark {index} lacks a unique name, valid region, or explicit review"
            )
        try:
            x = float(landmark.get("x"))
            y = float(landmark.get("y"))
        except (TypeError, ValueError) as exc:
            raise AvatarOwnerReviewError(
                f"landmark {index} coordinates are invalid"
            ) from exc
        if not (0.0 <= x < width and 0.0 <= y < height):
            raise AvatarOwnerReviewError(
                f"landmark {index} is outside the exact source image"
            )
        names.add(name)
        reviewed_landmarks.append(
            {"name": name, "region": region, "x": x, "y": y, "reviewed": True}
        )
    artifact = {
        "schema_version": OWNER_REVIEW_SCHEMA_VERSION,
        "artifact_type": "avatar_multiview_source_review",
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "selected_version_id": version_id,
        "canonical_route": canonical_route,
        "source_id": source_id,
        "source_sha256": source_sha,
        "source_dimensions": {"width": width, "height": height},
        "review_status": "approved",
        "reviewed_by": reviewer_id,
        "reviewed_at": _utc_now(),
        "same_subject_confirmed": True,
        "selected_version_confirmed": True,
        "same_subject_and_version_confirmed": True,
        "view_label": view_label,
        "crop_pixels": crop_values,
        "calibration": {
            "status": "reviewed",
            "camera_model": camera_model,
            "coordinate_frame_id": coordinate_frame_id,
        },
        "landmark_origin": "manual_owner_entry",
        "automatic_suggestions_confirmed_by_reviewer": False,
        "landmarks": reviewed_landmarks,
        "review_notes": _notes(payload.get("review_notes")),
        "safety_boundary": {
            "private_review_only": True,
            "body_queue_requested": False,
            "runtime_activation_requested": False,
        },
    }
    binding = _write_immutable_artifact(
        root,
        candidate_id=candidate_id,
        artifact_kind=f"source_{source_id}",
        artifact=artifact,
    )
    source["review_status"] = "approved_human_review_artifact_hash_bound"
    source["review_artifact"] = binding
    _commit_manifest(
        root,
        path,
        expected_manifest_sha256=manifest_sha,
        manifest=manifest,
        expected_canonical_route=canonical_route,
    )
    return _save_result(
        root, path, artifact_sha256=binding["sha256"]
    )


def save_scale_owner_review(
    project_root: Path,
    manifest_path: Path,
    *,
    reviewer_id: str,
    expected_manifest_sha256: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Save an explicit metric-height or unknown-scale owner decision."""

    root = project_root.resolve(strict=True)
    path, manifest, manifest_sha, canonical_route = _load_manifest(
        root,
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if not authoring.SAFE_ID_RE.fullmatch(_text(reviewer_id)):
        raise AvatarOwnerReviewError("reviewer ID is invalid")
    candidate_id = _text(manifest.get("candidate_id"))
    subject_id = _text(manifest.get("subject_id"))
    version_id = _text(manifest.get("selected_version_id"))
    _require_exact(payload, "confirm_candidate_id", candidate_id)
    _require_exact(payload, "confirm_subject_id", subject_id)
    _require_exact(payload, "confirm_selected_version_id", version_id)
    _require_true(payload, "confirm_identity_and_version")
    _require_true(payload, "approve_scale_review")
    mode = _normalized(payload.get("scale_mode"))
    target_height: float | None
    if mode == "reviewed_metric":
        _require_true(payload, "confirm_metric_height")
        try:
            target_height = float(payload.get("target_height_m"))
        except (TypeError, ValueError) as exc:
            raise AvatarOwnerReviewError("reviewed metric height is invalid") from exc
        if not 0.5 <= target_height <= 2.8:
            raise AvatarOwnerReviewError("reviewed metric height is out of range")
    elif mode == "scale_unknown_review_only":
        _require_true(payload, "confirm_no_height_inference")
        if payload.get("target_height_m") not in {None, ""}:
            raise AvatarOwnerReviewError(
                "unknown-scale review cannot include a target height"
            )
        target_height = None
    else:
        raise AvatarOwnerReviewError("scale review mode is invalid")
    artifact = {
        "schema_version": OWNER_REVIEW_SCHEMA_VERSION,
        "artifact_type": "avatar_multiview_scale_review",
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "selected_version_id": version_id,
        "canonical_route": canonical_route,
        "review_status": "approved",
        "reviewed_by": reviewer_id,
        "reviewed_at": _utc_now(),
        "scale_mode": mode,
        "target_height_m": target_height,
        "review_notes": _notes(payload.get("review_notes")),
        "no_height_inference_when_unknown": mode == "scale_unknown_review_only",
        "runtime_activation_requested": False,
    }
    binding = _write_immutable_artifact(
        root,
        candidate_id=candidate_id,
        artifact_kind="scale",
        artifact=artifact,
    )
    manifest["scale_review"] = {
        "status": "approved_human_review_artifact_hash_bound",
        "mode": mode,
    }
    manifest["scale_review_artifact"] = binding
    _commit_manifest(
        root,
        path,
        expected_manifest_sha256=manifest_sha,
        manifest=manifest,
        expected_canonical_route=canonical_route,
    )
    return _save_result(root, path, artifact_sha256=binding["sha256"])


def save_base_owner_review(
    project_root: Path,
    manifest_path: Path,
    *,
    reviewer_id: str,
    expected_manifest_sha256: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind an explicitly reviewed topology-compatible cage/base source."""

    root = project_root.resolve(strict=True)
    path, manifest, manifest_sha, canonical_route = _load_manifest(
        root,
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if not authoring.SAFE_ID_RE.fullmatch(_text(reviewer_id)):
        raise AvatarOwnerReviewError("reviewer ID is invalid")
    candidate_id = _text(manifest.get("candidate_id"))
    subject_id = _text(manifest.get("subject_id"))
    version_id = _text(manifest.get("selected_version_id"))
    topology_lane = _text(manifest.get("topology_lane"))
    _require_exact(payload, "confirm_candidate_id", candidate_id)
    _require_exact(payload, "confirm_subject_id", subject_id)
    _require_exact(payload, "confirm_selected_version_id", version_id)
    _require_exact(payload, "confirm_topology_lane", topology_lane)
    for field in (
        "confirm_identity_version_and_topology_lane",
        "confirm_exact_base_file",
        "rig_compatible_cage_source_confirmed",
        "new_candidate_surface_required",
        "confirm_surface_copy_forbidden",
        "approve_base_review",
    ):
        _require_true(payload, field)
    if payload.get("copy_as_candidate_body_allowed") is not False:
        raise AvatarOwnerReviewError(
            "copy_as_candidate_body_allowed must be explicitly false"
        )
    if "base_body_path" in payload:
        raise AvatarOwnerReviewError(
            "free-form base paths are forbidden; select an audited catalog authority"
        )
    catalog, options = _load_audited_base_catalog(root, topology_lane)
    if catalog.get("status") != "ready" or not options:
        raise AvatarOwnerReviewError(
            "no audited structural and maturity-lane base is ready"
        )
    _require_exact(
        payload,
        "confirm_base_authority_catalog_sha256",
        _text(catalog.get("catalog_sha256")),
    )
    base_authority_id = _text(payload.get("base_authority_id"))
    option = options.get(base_authority_id)
    if option is None:
        raise AvatarOwnerReviewError(
            "selected base authority is unavailable for this topology lane"
        )
    base_path = option["_path"]
    if not isinstance(base_path, Path):
        raise AvatarOwnerReviewError("selected base authority path is invalid")
    base_sha = _text(option.get("sha256"))
    _require_exact(payload, "confirm_base_sha256", base_sha)
    base_authority = {
        "base_id": base_authority_id,
        "catalog_path": BASE_AUTHORITY_CATALOG_PATH.as_posix(),
        "catalog_sha256": _text(catalog.get("catalog_sha256")),
        "asset_library_manifest_path": ASSET_LIBRARY_MANIFEST_PATH.as_posix(),
        "asset_library_manifest_sha256": _text(
            catalog.get("asset_library_manifest_sha256")
        ),
        "asset_library_record_id": _text(option.get("asset_library_record_id")),
        "structural_proof": option.get("structural_proof"),
        "maturity_authority": option.get("maturity_authority"),
        "stable_working_rig_proven": False,
        "anatomical_completeness_proven": False,
    }
    artifact = {
        "schema_version": OWNER_REVIEW_SCHEMA_VERSION,
        "artifact_type": "avatar_multiview_base_review",
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "selected_version_id": version_id,
        "canonical_route": canonical_route,
        "base_body_sha256": base_sha,
        "base_authority": base_authority,
        "topology_lane": topology_lane,
        "review_status": "approved",
        "reviewed_by": reviewer_id,
        "reviewed_at": _utc_now(),
        "rig_compatible_cage_source_confirmed": True,
        "new_candidate_surface_required": True,
        "copy_as_candidate_body_allowed": False,
        "allowed_use": "cage_fit_source_new_surface_required",
        "review_notes": _notes(payload.get("review_notes")),
        "runtime_activation_requested": False,
    }
    review_binding = _write_immutable_artifact(
        root,
        candidate_id=candidate_id,
        artifact_kind="base",
        artifact=artifact,
    )
    manifest["base_body"] = {
        "status": "reviewed",
        "path": _text(option.get("project_relative_path")),
        "sha256": base_sha,
        "topology_lane": topology_lane,
        "base_authority_id": base_authority_id,
        "base_authority": base_authority,
        "allowed_use": "cage_fit_source_new_surface_required",
        "copy_as_candidate_body_allowed": False,
        "review_artifact": review_binding,
    }
    _commit_manifest(
        root,
        path,
        expected_manifest_sha256=manifest_sha,
        manifest=manifest,
        expected_canonical_route=canonical_route,
    )
    return _save_result(
        root, path, artifact_sha256=review_binding["sha256"]
    )


def build_owner_review_report(
    project_root: Path,
    manifest_path: Path,
    *,
    reviewer_id: str,
) -> str:
    """Build a path-free Markdown report for the owner review session."""

    session = load_owner_review_session(
        project_root, manifest_path, reviewer_id=reviewer_id
    )
    evaluation = session["evaluation"]
    canonical_route = session["canonical_route"]
    base_catalog = session["base_authority_catalog"]
    lines = [
        "# Avatar multiview owner review",
        "",
        "> Private local review summary. Source filesystem paths and image bytes are not embedded.",
        "",
        f"- Candidate: `{session['candidate_id']}`",
        f"- Subject: `{session['subject_id']}`",
        f"- Selected version: `{session['selected_version_id']}`",
        f"- Topology lane: `{session['topology_lane']}`",
        f"- Reviewer: `{session['reviewer_id']}`",
        f"- Manifest SHA-256: `{session['manifest_sha256']}`",
        f"- Canonical candidate: `{canonical_route['canonical_candidate_id']}`",
        f"- Canonical registry SHA-256: `{canonical_route['registry_sha256']}`",
        f"- Canonical profile SHA-256: `{canonical_route['canonical_profile_sha256']}`",
        f"- Audited base catalog: `{base_catalog['status']}`",
        f"- Current status: `{evaluation['status']}`",
        "- Queue/build/render/export/activation operations: unavailable",
        "",
        "## Exact enrolled sources",
        "",
        "| Source ID | Native dimensions | Exact SHA-256 | Review | View | Landmark count |",
        "|---|---:|---|---|---|---:|",
    ]
    for source in session["source_images"]:
        review = source.get("review") or {}
        lines.append(
            "| `{}` | {} x {} | `{}` | {} | `{}` | {} |".format(
                source["source_id"],
                source["dimensions"]["width"],
                source["dimensions"]["height"],
                source["sha256"],
                review.get("review_status") or "pending",
                review.get("view_label") or "pending",
                len(review.get("landmarks") or []),
            )
        )
    lines.extend(
        [
            "",
            "## Remaining review gates",
            "",
        ]
    )
    gaps = evaluation.get("review_gaps") or []
    failures = evaluation.get("integrity_failures") or []
    if not gaps and not failures:
        lines.append("- The evidence contract passes, but no body was queued or built.")
    for item in failures:
        lines.append(f"- Integrity: `{item}`")
    for item in gaps:
        lines.append(f"- Review: `{item}`")
    lines.extend(
        [
            "",
            "## Safety boundary",
            "",
            "- Images are available only through exact-hash source tokens on the loopback review server.",
            "- Every artifact requires explicit owner confirmation and a current manifest hash.",
            "- The workflow cannot queue a likeness job, author a mesh, export media, or activate anyone.",
            "",
        ]
    )
    return "\n".join(lines)
