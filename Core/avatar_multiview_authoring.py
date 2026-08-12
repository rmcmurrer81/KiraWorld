"""Exact-hash evidence gate for multiview avatar likeness authoring.

This module is deliberately an authoring *input* gate.  It reopens every
enrolled image and every review artifact, verifies their SHA-256 bindings, and
checks that reviewed views, calibration, landmarks, scale, and the selected
base are complete before an authoring job can be queued.  It never suggests or
invents landmarks, fits a mesh, renders private material, or activates a body.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = 1
MANIFEST_TYPE = "avatar_multiview_likeness_evidence"
OUTPUT_RULE = "private_review_only_not_runtime"
QUEUE_ACTION = "author_new_subject_surface_from_reviewed_multiview_evidence"
TOPOLOGY_LANES = frozenset(
    {"confirmed_adult_topology", "non_adult_doll_safe_topology"}
)
IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"})
BASE_SUFFIXES = frozenset({".blend", ".fbx", ".glb", ".gltf", ".obj"})
MODEL_SUFFIXES = BASE_SUFFIXES | frozenset({".usdz"})
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,191}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

FRONT_VIEWS = frozenset(
    {"face_front", "front", "full_body_front", "head_front"}
)
DEPTH_VIEWS = frozenset(
    {
        "face_left_profile",
        "face_right_profile",
        "full_body_left",
        "full_body_right",
        "full_body_side",
        "head_left_profile",
        "head_right_profile",
        "left_profile",
        "profile",
        "right_profile",
        "side",
        "three_quarter",
        "three_quarter_left",
        "three_quarter_right",
    }
)
FULL_BODY_VIEWS = frozenset(
    {
        "full_body",
        "full_body_back",
        "full_body_front",
        "full_body_left",
        "full_body_right",
        "full_body_side",
    }
)
ALLOWED_VIEWS = FRONT_VIEWS | DEPTH_VIEWS | FULL_BODY_VIEWS | frozenset(
    {"face_three_quarter", "head_three_quarter"}
)
REQUIRED_LANDMARK_REGIONS = frozenset(
    {
        "face_outline",
        "brow",
        "eye_socket_rims",
        "nose",
        "lips",
        "chin",
        "ears",
        "neck",
        "shoulders",
        "chest",
        "waist",
        "hips",
        "elbows",
        "wrists",
        "hands",
        "knees",
        "ankles",
        "feet",
    }
)
CAMERA_MODELS = frozenset(
    {"pinhole", "perspective", "orthographic_approximation"}
)


class AvatarMultiviewError(ValueError):
    """A malformed path, manifest, or queue request."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


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


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarMultiviewError("invalid JSON artifact") from exc
    if not isinstance(value, dict):
        raise AvatarMultiviewError("JSON artifact must be an object")
    return value


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
    suffixes: Iterable[str] | None = None,
) -> Path:
    root = project_root.resolve(strict=True)
    raw_text = _text(raw_value)
    raw = Path(raw_text)
    if not raw_text or raw.is_absolute() or ".." in raw.parts:
        raise AvatarMultiviewError(f"{name} must be a safe project-relative path")
    unresolved = root / raw
    if _has_symlink_component(unresolved, root):
        raise AvatarMultiviewError(f"{name} contains a symlink")
    try:
        path = unresolved.resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AvatarMultiviewError(f"{name} is missing or escapes the project") from exc
    if not path.is_file():
        raise AvatarMultiviewError(f"{name} is not a regular file")
    if suffixes is not None and path.suffix.lower() not in set(suffixes):
        raise AvatarMultiviewError(f"{name} has an unsupported file type")
    return path


def _manifest_file(project_root: Path, manifest_path: Path) -> Path:
    root = project_root.resolve(strict=True)
    unresolved = manifest_path if manifest_path.is_absolute() else root / manifest_path
    if _has_symlink_component(unresolved, root):
        raise AvatarMultiviewError("manifest path contains a symlink")
    try:
        resolved = unresolved.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AvatarMultiviewError("manifest is missing or outside the project") from exc
    if not resolved.is_file():
        raise AvatarMultiviewError("manifest is not a regular file")
    return resolved


def _valid_sha(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _safe_id(value: Any) -> bool:
    return bool(SAFE_ID_RE.fullmatch(_text(value)))


def _image_dimensions(path: Path) -> tuple[int, int]:
    """Read native encoded dimensions without decoding or rendering an image."""

    with path.open("rb") as handle:
        header = handle.read(32)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
            return struct.unpack(">II", header[16:24])
        if header[:6] in {b"GIF87a", b"GIF89a"} and len(header) >= 10:
            return struct.unpack("<HH", header[6:10])
        if header.startswith(b"BM") and len(header) >= 26:
            width, height = struct.unpack("<ii", header[18:26])
            return abs(width), abs(height)
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            kind = header[12:16]
            if kind == b"VP8X" and len(header) >= 30:
                width = 1 + int.from_bytes(header[24:27], "little")
                height = 1 + int.from_bytes(header[27:30], "little")
                return width, height
            if kind == b"VP8L" and len(header) >= 25 and header[20] == 0x2F:
                bits = int.from_bytes(header[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if kind == b"VP8 " and len(header) >= 30 and header[23:26] == b"\x9d\x01\x2a":
                width, height = struct.unpack("<HH", header[26:30])
                return width & 0x3FFF, height & 0x3FFF
        if not header.startswith(b"\xff\xd8"):
            raise AvatarMultiviewError("unsupported or malformed image envelope")

        handle.seek(2)
        while True:
            byte = handle.read(1)
            if not byte:
                break
            if byte != b"\xff":
                continue
            while byte == b"\xff":
                byte = handle.read(1)
            if not byte:
                break
            marker = byte[0]
            if marker in {0x01, *range(0xD0, 0xDA)}:
                continue
            length_raw = handle.read(2)
            if len(length_raw) != 2:
                break
            length = struct.unpack(">H", length_raw)[0]
            if length < 2:
                break
            if marker in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                payload = handle.read(length - 2)
                if len(payload) < 5:
                    break
                height, width = struct.unpack(">HH", payload[1:5])
                return width, height
            handle.seek(length - 2, 1)
    raise AvatarMultiviewError("image dimensions could not be verified")


def _binding_artifact(
    project_root: Path,
    binding: Mapping[str, Any],
    *,
    name: str,
) -> tuple[Path, dict[str, Any], str]:
    path = _project_file(
        project_root,
        binding.get("path"),
        name=f"{name}.path",
        suffixes={".json"},
    )
    expected = _text(binding.get("sha256")).lower()
    if not _valid_sha(expected):
        raise AvatarMultiviewError(f"{name}.sha256 is invalid")
    actual = sha256_file(path)
    if actual != expected:
        raise AvatarMultiviewError(f"{name} hash mismatch")
    return path, _read_json_object(path), actual


def _reviewed_source(
    *,
    project_root: Path,
    manifest: Mapping[str, Any],
    source: Mapping[str, Any],
    source_path: Path,
    source_sha256: str,
    width: int,
    height: int,
) -> tuple[dict[str, Any] | None, str | None]:
    source_id = _text(source.get("source_id"))
    binding = source.get("review_artifact")
    if not isinstance(binding, Mapping):
        return None, f"source_review_missing:{source_id}"
    _, review, review_sha = _binding_artifact(
        project_root, binding, name=f"source_images.{source_id}.review_artifact"
    )
    expected_common = {
        "artifact_type": "avatar_multiview_source_review",
        "candidate_id": _text(manifest.get("candidate_id")),
        "subject_id": _text(manifest.get("subject_id")),
        "selected_version_id": _text(manifest.get("selected_version_id")),
        "source_id": source_id,
        "source_sha256": source_sha256,
    }
    for field, expected in expected_common.items():
        if _text(review.get(field)) != expected:
            raise AvatarMultiviewError(
                f"source review binding mismatch for {source_id}: {field}"
            )
    if (
        _normalized(review.get("review_status")) != "approved"
        or not _text(review.get("reviewed_by"))
        or not _text(review.get("reviewed_at"))
        or review.get("same_subject_and_version_confirmed") is not True
    ):
        raise AvatarMultiviewError(f"source review is not approved: {source_id}")
    declared_dimensions = review.get("source_dimensions")
    if not isinstance(declared_dimensions, Mapping) or (
        declared_dimensions.get("width") != width
        or declared_dimensions.get("height") != height
    ):
        raise AvatarMultiviewError(f"source review dimensions mismatch: {source_id}")
    view_label = _normalized(review.get("view_label"))
    if view_label not in ALLOWED_VIEWS:
        raise AvatarMultiviewError(f"source review view label is invalid: {source_id}")
    crop = review.get("crop_pixels")
    if not isinstance(crop, Mapping):
        raise AvatarMultiviewError(f"source review crop is missing: {source_id}")
    try:
        crop_x = int(crop.get("x"))
        crop_y = int(crop.get("y"))
        crop_width = int(crop.get("width"))
        crop_height = int(crop.get("height"))
    except (TypeError, ValueError) as exc:
        raise AvatarMultiviewError(f"source review crop is invalid: {source_id}") from exc
    if (
        crop_x < 0
        or crop_y < 0
        or crop_width < 1
        or crop_height < 1
        or crop_x + crop_width > width
        or crop_y + crop_height > height
    ):
        raise AvatarMultiviewError(f"source review crop is out of bounds: {source_id}")
    calibration = review.get("calibration")
    if not isinstance(calibration, Mapping) or (
        _normalized(calibration.get("status")) != "reviewed"
        or _normalized(calibration.get("camera_model")) not in CAMERA_MODELS
        or not _safe_id(calibration.get("coordinate_frame_id"))
    ):
        raise AvatarMultiviewError(
            f"source review calibration is incomplete: {source_id}"
        )
    landmarks = review.get("landmarks")
    if not isinstance(landmarks, list) or not landmarks:
        raise AvatarMultiviewError(f"source review landmarks are missing: {source_id}")
    regions: set[str] = set()
    names: set[str] = set()
    for index, landmark in enumerate(landmarks):
        if not isinstance(landmark, Mapping):
            raise AvatarMultiviewError(f"source review landmark is invalid: {source_id}")
        name = _text(landmark.get("name"))
        region = _normalized(landmark.get("region"))
        if not name or name in names or region not in REQUIRED_LANDMARK_REGIONS:
            raise AvatarMultiviewError(
                f"source review landmark name/region is invalid: {source_id}:{index}"
            )
        names.add(name)
        if landmark.get("reviewed") is not True:
            raise AvatarMultiviewError(
                f"source review landmark is not human-confirmed: {source_id}:{name}"
            )
        try:
            x = float(landmark.get("x"))
            y = float(landmark.get("y"))
        except (TypeError, ValueError) as exc:
            raise AvatarMultiviewError(
                f"source review landmark coordinate is invalid: {source_id}:{name}"
            ) from exc
        if not (0.0 <= x < width and 0.0 <= y < height):
            raise AvatarMultiviewError(
                f"source review landmark is out of bounds: {source_id}:{name}"
            )
        regions.add(region)
    if (
        _normalized(review.get("landmark_origin")) == "automatic_suggestion"
        and review.get("automatic_suggestions_confirmed_by_reviewer") is not True
    ):
        raise AvatarMultiviewError(
            f"automatic landmark suggestions are not confirmed: {source_id}"
        )
    return {
        "source_id": source_id,
        "source_review_sha256": review_sha,
        "view_label": view_label,
        "coordinate_frame_id": _text(calibration.get("coordinate_frame_id")),
        "landmark_regions": sorted(regions),
        "landmark_count": len(landmarks),
    }, None


def _scale_review(
    project_root: Path,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], str | None]:
    binding = manifest.get("scale_review_artifact")
    if not isinstance(binding, Mapping):
        return {"ready": False, "mode": "pending"}, "scale_review_artifact_missing"
    _, review, digest = _binding_artifact(
        project_root, binding, name="scale_review_artifact"
    )
    for field in ("candidate_id", "subject_id", "selected_version_id"):
        if _text(review.get(field)) != _text(manifest.get(field)):
            raise AvatarMultiviewError(f"scale review binding mismatch: {field}")
    if (
        _text(review.get("artifact_type")) != "avatar_multiview_scale_review"
        or _normalized(review.get("review_status")) != "approved"
        or not _text(review.get("reviewed_by"))
        or not _text(review.get("reviewed_at"))
    ):
        raise AvatarMultiviewError("scale review is not approved")
    mode = _normalized(review.get("scale_mode"))
    if mode not in {"reviewed_metric", "scale_unknown_review_only"}:
        raise AvatarMultiviewError("scale review mode is invalid")
    target_height = review.get("target_height_m")
    if mode == "reviewed_metric":
        if not isinstance(target_height, (int, float)) or not 0.5 <= float(target_height) <= 2.8:
            raise AvatarMultiviewError("reviewed metric height is invalid")
    elif target_height not in {None, ""}:
        raise AvatarMultiviewError("unknown-scale review cannot declare target height")
    return {
        "ready": True,
        "mode": mode,
        "target_height_m": float(target_height) if mode == "reviewed_metric" else None,
        "review_sha256": digest,
    }, None


def _base_review(
    project_root: Path,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], str | None]:
    binding = manifest.get("base_body")
    if not isinstance(binding, Mapping) or _normalized(binding.get("status")).startswith(
        "pending"
    ):
        return {"ready": False}, "selected_base_body_and_review_missing"
    path = _project_file(
        project_root,
        binding.get("path"),
        name="base_body.path",
        suffixes=BASE_SUFFIXES,
    )
    expected = _text(binding.get("sha256")).lower()
    if not _valid_sha(expected) or sha256_file(path) != expected:
        raise AvatarMultiviewError("base body hash mismatch")
    topology_lane = _text(manifest.get("topology_lane"))
    if (
        _text(binding.get("topology_lane")) != topology_lane
        or _text(binding.get("allowed_use"))
        != "cage_fit_source_new_surface_required"
        or binding.get("copy_as_candidate_body_allowed") is not False
    ):
        raise AvatarMultiviewError("base body use/topology declaration is invalid")
    review_binding = binding.get("review_artifact")
    if not isinstance(review_binding, Mapping):
        return {"ready": False, "sha256": expected}, "selected_base_body_review_missing"
    _, review, review_sha = _binding_artifact(
        project_root, review_binding, name="base_body.review_artifact"
    )
    if (
        _text(review.get("artifact_type")) != "avatar_multiview_base_review"
        or _text(review.get("candidate_id")) != _text(manifest.get("candidate_id"))
        or _text(review.get("subject_id")) != _text(manifest.get("subject_id"))
        or _text(review.get("selected_version_id"))
        != _text(manifest.get("selected_version_id"))
        or _text(review.get("base_body_sha256")).lower() != expected
        or _text(review.get("topology_lane")) != topology_lane
        or _normalized(review.get("review_status")) != "approved"
        or not _text(review.get("reviewed_by"))
        or not _text(review.get("reviewed_at"))
        or review.get("rig_compatible_cage_source_confirmed") is not True
        or review.get("new_candidate_surface_required") is not True
    ):
        raise AvatarMultiviewError("base body review binding is invalid")
    return {"ready": True, "sha256": expected, "review_sha256": review_sha}, None


def _reference_model_reviews(
    project_root: Path,
    manifest: Mapping[str, Any],
) -> tuple[int, list[str]]:
    models = manifest.get("reference_models", [])
    if not isinstance(models, list):
        raise AvatarMultiviewError("reference_models must be a list")
    if len(models) > 16:
        raise AvatarMultiviewError("too many reference models")
    verified = 0
    digests: set[str] = set()
    for index, binding in enumerate(models):
        if not isinstance(binding, Mapping):
            raise AvatarMultiviewError("reference model binding is invalid")
        path = _project_file(
            project_root,
            binding.get("path"),
            name=f"reference_models.{index}.path",
            suffixes=MODEL_SUFFIXES,
        )
        digest = _text(binding.get("sha256")).lower()
        if not _valid_sha(digest) or sha256_file(path) != digest or digest in digests:
            raise AvatarMultiviewError("reference model hash is invalid or duplicated")
        digests.add(digest)
        if (
            _text(binding.get("allowed_use"))
            != "measurement_and_topology_guidance_only"
            or binding.get("reference_only") is not True
            or binding.get("copy_surface_as_candidate_allowed") is not False
            or binding.get("copy_materials_or_textures_allowed") is not False
        ):
            raise AvatarMultiviewError("reference model allowed-use boundary is invalid")
        review_binding = binding.get("review_artifact")
        if not isinstance(review_binding, Mapping):
            raise AvatarMultiviewError("reference model review artifact is missing")
        _, review, _ = _binding_artifact(
            project_root,
            review_binding,
            name=f"reference_models.{index}.review_artifact",
        )
        if (
            _text(review.get("artifact_type"))
            != "avatar_multiview_reference_model_review"
            or _text(review.get("candidate_id")) != _text(manifest.get("candidate_id"))
            or _text(review.get("subject_id")) != _text(manifest.get("subject_id"))
            or _text(review.get("selected_version_id"))
            != _text(manifest.get("selected_version_id"))
            or _text(review.get("model_sha256")).lower() != digest
            or _text(review.get("allowed_use"))
            != "measurement_and_topology_guidance_only"
            or _normalized(review.get("review_status")) != "approved"
        ):
            raise AvatarMultiviewError("reference model review binding is invalid")
        verified += 1
    return verified, []


def evaluate_multiview_manifest(
    project_root: Path,
    manifest_path: Path,
    *,
    expected_candidate_id: str = "",
    expected_subject_id: str = "",
    expected_topology_lane: str = "",
    expected_manifest_sha256: str = "",
) -> dict[str, Any]:
    """Evaluate one private manifest and return a path-free readiness summary."""

    failures: list[str] = []
    review_gaps: list[str] = []
    try:
        path = _manifest_file(project_root, manifest_path)
        manifest_sha = sha256_file(path)
        manifest = _read_json_object(path)
        if expected_manifest_sha256 and (
            not _valid_sha(expected_manifest_sha256)
            or manifest_sha != expected_manifest_sha256.lower()
        ):
            failures.append("manifest_sha256_binding_mismatch")
        candidate_id = _text(manifest.get("candidate_id"))
        subject_id = _text(manifest.get("subject_id"))
        version_id = _text(manifest.get("selected_version_id"))
        topology_lane = _text(manifest.get("topology_lane"))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            failures.append("unsupported_manifest_schema")
        if _text(manifest.get("manifest_type")) != MANIFEST_TYPE:
            failures.append("invalid_manifest_type")
        if not _safe_id(candidate_id) or not _safe_id(subject_id) or not _safe_id(version_id):
            failures.append("candidate_subject_or_version_id_invalid")
        if expected_candidate_id and candidate_id != expected_candidate_id:
            failures.append("manifest_candidate_id_mismatch")
        if expected_subject_id and subject_id != expected_subject_id:
            failures.append("manifest_subject_id_mismatch")
        if topology_lane not in TOPOLOGY_LANES:
            failures.append("manifest_topology_lane_invalid")
        if expected_topology_lane and topology_lane != expected_topology_lane:
            failures.append("manifest_topology_lane_mismatch")
        if _text(manifest.get("output_rule")) != OUTPUT_RULE:
            failures.append("private_review_only_output_rule_missing")
        if (
            _normalized(manifest.get("authoring_status"))
            == "superseded_audit_only"
            or manifest.get("queue_eligible") is False
        ):
            failures.append("manifest_superseded_audit_only")
        if manifest.get("runtime_activation_requested") is not False:
            failures.append("runtime_activation_must_be_false")
        if manifest.get("public_export_allowed") is not False:
            failures.append("public_export_must_be_false")

        sources = manifest.get("source_images")
        if not isinstance(sources, list) or len(sources) > 64:
            failures.append("source_images_must_be_bounded_list")
            sources = []
        source_ids: set[str] = set()
        source_hashes: set[str] = set()
        exact_hash_count = 0
        reviewed: list[dict[str, Any]] = []
        for index, source in enumerate(sources):
            if not isinstance(source, Mapping):
                failures.append(f"source_record_invalid:{index}")
                continue
            source_id = _text(source.get("source_id"))
            if not _safe_id(source_id) or source_id in source_ids:
                failures.append(f"source_id_invalid_or_duplicate:{index}")
                continue
            source_ids.add(source_id)
            try:
                source_path = _project_file(
                    project_root,
                    source.get("source_path"),
                    name=f"source_images.{source_id}.source_path",
                    suffixes=IMAGE_SUFFIXES,
                )
                expected_sha = _text(source.get("sha256")).lower()
                actual_sha = sha256_file(source_path)
                if not _valid_sha(expected_sha) or actual_sha != expected_sha:
                    raise AvatarMultiviewError("source image hash mismatch")
                if actual_sha in source_hashes:
                    raise AvatarMultiviewError("duplicate source image hash")
                source_hashes.add(actual_sha)
                width, height = _image_dimensions(source_path)
                dimensions = source.get("dimensions")
                if not isinstance(dimensions, Mapping) or (
                    dimensions.get("width") != width
                    or dimensions.get("height") != height
                ):
                    raise AvatarMultiviewError("source image dimensions mismatch")
                exact_hash_count += 1
                reviewed_source, gap = _reviewed_source(
                    project_root=project_root,
                    manifest=manifest,
                    source=source,
                    source_path=source_path,
                    source_sha256=actual_sha,
                    width=width,
                    height=height,
                )
                if reviewed_source:
                    reviewed.append(reviewed_source)
                if gap:
                    review_gaps.append(gap)
            except AvatarMultiviewError as exc:
                failures.append(f"source_integrity_or_review_invalid:{source_id}:{exc}")

        if len(sources) < 3:
            review_gaps.append("minimum_three_exact_hash_sources_missing")
        views = {item["view_label"] for item in reviewed}
        has_front = bool(views & FRONT_VIEWS)
        has_depth = bool(views & DEPTH_VIEWS)
        has_full_body = bool(views & FULL_BODY_VIEWS)
        if len(reviewed) < 3:
            review_gaps.append("minimum_three_reviewed_sources_missing")
        if not has_front:
            review_gaps.append("reviewed_front_identity_view_missing")
        if not has_depth:
            review_gaps.append("reviewed_profile_or_three_quarter_view_missing")
        if not has_full_body:
            review_gaps.append("reviewed_full_body_view_missing")
        frames = {item["coordinate_frame_id"] for item in reviewed}
        if reviewed and len(frames) != 1:
            review_gaps.append("reviewed_views_not_in_one_calibration_frame")
        all_regions = {
            region for item in reviewed for region in item["landmark_regions"]
        }
        missing_regions = sorted(REQUIRED_LANDMARK_REGIONS - all_regions)
        if missing_regions:
            review_gaps.append("required_landmark_region_coverage_incomplete")
        scale, scale_gap = _scale_review(project_root, manifest)
        if scale_gap:
            review_gaps.append(scale_gap)
        base, base_gap = _base_review(project_root, manifest)
        if base_gap:
            review_gaps.append(base_gap)
        reference_model_count, model_gaps = _reference_model_reviews(
            project_root, manifest
        )
        review_gaps.extend(model_gaps)
    except AvatarMultiviewError as exc:
        candidate_id = ""
        subject_id = ""
        version_id = ""
        topology_lane = ""
        manifest_sha = ""
        sources = []
        exact_hash_count = 0
        reviewed = []
        views = set()
        frames = set()
        all_regions = set()
        missing_regions = sorted(REQUIRED_LANDMARK_REGIONS)
        scale = {"ready": False, "mode": "pending"}
        base = {"ready": False}
        reference_model_count = 0
        failures.append(f"manifest_unreadable_or_unsafe:{exc}")

    failures = list(dict.fromkeys(failures))
    review_gaps = list(dict.fromkeys(review_gaps))
    ready = not failures and not review_gaps
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "selected_version_id": version_id,
        "topology_lane": topology_lane,
        "manifest_sha256": manifest_sha,
        "manifest_exact_hash_verified": bool(manifest_sha) and not any(
            item == "manifest_sha256_binding_mismatch" for item in failures
        ),
        "source_count": len(sources),
        "exact_hash_source_count": exact_hash_count,
        "reviewed_source_count": len(reviewed),
        "covered_views": sorted(views),
        "front_view_ready": bool(views & FRONT_VIEWS),
        "depth_view_ready": bool(views & DEPTH_VIEWS),
        "full_body_view_ready": bool(views & FULL_BODY_VIEWS),
        "single_calibration_frame_ready": bool(reviewed) and len(frames) == 1,
        "calibration_frame_count": len(frames),
        "reviewed_landmark_count": sum(
            int(item.get("landmark_count") or 0) for item in reviewed
        ),
        "covered_landmark_regions": sorted(all_regions),
        "missing_landmark_regions": missing_regions,
        "scale_review": scale,
        "base_body_review": base,
        "reviewed_reference_model_count": reference_model_count,
        "authoring_queue_ready": ready,
        "status": (
            "ready_for_likeness_authoring_queue"
            if ready
            else "blocked_manifest_integrity_or_identity"
            if failures
            else "blocked_review_incomplete"
        ),
        "integrity_failures": failures,
        "review_gaps": review_gaps,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "A passing manifest permits an inactive private authoring job to be queued. "
            "It does not create a mesh or prove likeness, topology, rigging, motion, "
            "clothing, owner visual approval, or runtime readiness."
        ),
    }


def queue_multiview_authoring_manifest(
    project_root: Path,
    manifest_path: Path,
    *,
    expected_candidate_id: str = "",
    expected_subject_id: str = "",
    expected_topology_lane: str = "",
    expected_manifest_sha256: str = "",
    queue_root: Path | None = None,
) -> dict[str, Any]:
    """Queue a passing evidence set without invoking a mesh author."""

    root = project_root.resolve(strict=True)
    path = _manifest_file(root, manifest_path)
    result = evaluate_multiview_manifest(
        root,
        path,
        expected_candidate_id=expected_candidate_id,
        expected_subject_id=expected_subject_id,
        expected_topology_lane=expected_topology_lane,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if result["authoring_queue_ready"] is not True:
        raise AvatarMultiviewError(
            "multiview evidence is not ready for the authoring queue"
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "action": QUEUE_ACTION,
        "candidate_id": result["candidate_id"],
        "subject_id": result["subject_id"],
        "selected_version_id": result["selected_version_id"],
        "topology_lane": result["topology_lane"],
        "manifest": {
            "path": path.relative_to(root).as_posix(),
            "sha256": result["manifest_sha256"],
        },
        "output_rule": OUTPUT_RULE,
        "author_backend_available": False,
        "runtime_activation_requested": False,
        "public_export_requested": False,
    }
    job_id = _sha256_bytes(canonical_json_bytes(payload))
    payload["job_id"] = job_id
    destination_root = queue_root or (
        root / "Avatar" / "avatar_builder" / "multiview_authoring"
    )
    if not destination_root.is_absolute():
        destination_root = root / destination_root
    if _has_symlink_component(destination_root, root):
        raise AvatarMultiviewError("authoring queue path contains a symlink")
    destination_root = destination_root.resolve()
    try:
        destination_root.relative_to(root)
    except ValueError as exc:
        raise AvatarMultiviewError("authoring queue path escapes the project") from exc
    job_path = destination_root / "queued" / f"{job_id}.json"
    job_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json_bytes(payload) + b"\n"
    try:
        with job_path.open("xb") as handle:
            handle.write(encoded)
        status = "queued_waiting_for_likeness_author_backend"
    except FileExistsError:
        if job_path.is_symlink() or not job_path.is_file() or job_path.read_bytes() != encoded:
            raise AvatarMultiviewError("immutable authoring queue path changed")
        status = "already_queued_waiting_for_likeness_author_backend"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "job_id": job_id,
        "job_path": job_path.relative_to(root).as_posix(),
        "manifest_sha256": result["manifest_sha256"],
        "author_backend_available": False,
        "runtime_activation_allowed": False,
        "truth_note": (
            "The reviewed input contract is queued, but no likeness mesh author ran."
        ),
    }
