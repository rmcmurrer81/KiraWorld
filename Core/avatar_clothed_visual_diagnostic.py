"""Integrity validation for inactive, private clothed-avatar turntables.

This gate proves that a diagnostic JSON record is bound to one exact GLB and
one exact set of PNGs inside the same inactive candidate.  It intentionally
does not infer visual quality, likeness, anatomy, garment behavior, or runtime
readiness from the presence of files.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
from typing import Any, Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_REST_VIEWS = frozenset(
    {"front", "front_three_quarter", "left_profile", "back"}
)
REQUIRED_ACTION_POSES = frozenset({"walk", "sit", "reach"})
REQUIRED_FALSE_TRUTH = (
    "garment_coverage_owner_reviewed",
    "garment_penetration_proven_absent",
    "stable_visual_deformation_proven",
    "identity_likeness_owner_approved",
    "wearable_dressing_behavior_proven",
    "runtime_activation_allowed",
    "public_export_allowed",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _valid_sha(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("visual diagnostic must be a JSON object")
    return value


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _candidate_root(project_root: Path, path: Path) -> Path | None:
    allowed_roots = (
        project_root / "Avatar" / "temp_ai",
        project_root / "Avatar" / "models" / "temp_ai",
        project_root / "Avatar" / "avatar_builder" / "candidate_sources",
    )
    for allowed_root in allowed_roots:
        try:
            relative = path.relative_to(allowed_root.resolve())
        except ValueError:
            continue
        if relative.parts:
            return allowed_root.resolve() / relative.parts[0]
    return None


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return (width, height) if width > 0 and height > 0 else None


def evaluate_clothed_visual_diagnostic(
    project_root: Path,
    proof_path: Path,
    *,
    expected_model_sha256: str = "",
) -> dict[str, Any]:
    root = project_root.resolve(strict=True)
    resolved_proof = proof_path.resolve(strict=True)
    failures: list[str] = []
    if not _regular_file(resolved_proof):
        raise ValueError("visual diagnostic proof must be a regular non-symlink file")
    try:
        resolved_proof.relative_to(root)
    except ValueError as exc:
        raise ValueError("visual diagnostic proof escapes the project") from exc
    candidate_root = _candidate_root(root, resolved_proof)
    if candidate_root is None:
        failures.append("proof_not_in_inactive_candidate_root")
    else:
        try:
            proof_relative = resolved_proof.relative_to(candidate_root)
        except ValueError:
            proof_relative = Path()
        if not proof_relative.parts or proof_relative.parts[0].lower() != "private_review":
            failures.append("proof_not_in_candidate_private_review")

    try:
        proof = _read_object(resolved_proof)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema_version": 1,
            "status": "blocked_integrity_failure",
            "integrity_verified": False,
            "failures": [f"proof_json_invalid:{type(exc).__name__}"],
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
    if proof.get("schema_version") != 1:
        failures.append("unsupported_schema_version")
    if _text(proof.get("artifact_type")) != "private_clothed_avatar_visual_diagnostic":
        failures.append("artifact_type_mismatch")
    try:
        datetime.fromisoformat(_text(proof.get("created_at")).replace("Z", "+00:00"))
    except ValueError:
        failures.append("created_at_invalid")

    model = proof.get("model")
    model = model if isinstance(model, Mapping) else {}
    model_relative = Path(_text(model.get("project_path")))
    model_path: Path | None = None
    if (
        not model_relative.parts
        or model_relative.is_absolute()
        or ".." in model_relative.parts
        or model_relative.suffix.lower() != ".glb"
        or "clothed" not in model_relative.stem.lower()
        or "review" not in model_relative.stem.lower()
    ):
        failures.append("model_path_invalid_or_not_clothed_review")
    else:
        try:
            model_path = (root / model_relative).resolve(strict=True)
            model_path.relative_to(root)
        except (FileNotFoundError, ValueError, OSError):
            failures.append("model_missing_or_escapes_project")
            model_path = None
    model_sha = _text(model.get("sha256")).lower()
    if not _valid_sha(model_sha):
        failures.append("model_sha256_invalid")
    if model_path is not None:
        if not _regular_file(model_path):
            failures.append("model_not_regular_file")
        elif model_path.read_bytes()[:4] != b"glTF":
            failures.append("model_not_binary_gltf")
        elif sha256_file(model_path) != model_sha:
            failures.append("model_sha256_mismatch")
        if candidate_root is None or _candidate_root(root, model_path) != candidate_root:
            failures.append("model_and_proof_candidate_mismatch")
        if model_path.parent != resolved_proof.parent:
            failures.append("model_is_not_retained_beside_visual_diagnostic")
    if model.get("byte_identical_private_snapshot") is not True:
        failures.append("model_private_snapshot_binding_missing")
    input_model = proof.get("input_model")
    input_model = input_model if isinstance(input_model, Mapping) else {}
    input_relative = Path(_text(input_model.get("project_path")))
    if (
        not input_relative.parts
        or input_relative.is_absolute()
        or ".." in input_relative.parts
        or input_relative.suffix.lower() != ".glb"
    ):
        failures.append("input_model_path_invalid")
    if _text(input_model.get("sha256_at_render_time")).lower() != model_sha:
        failures.append("input_model_render_time_hash_mismatch")
    if expected_model_sha256:
        if not _valid_sha(expected_model_sha256) or model_sha != expected_model_sha256.lower():
            failures.append("model_does_not_match_expected_sha256")

    inventory = proof.get("import_inventory")
    inventory = inventory if isinstance(inventory, Mapping) else {}
    for key in ("mesh_object_count", "body_mesh_count", "clothing_mesh_count", "armature_count"):
        if not isinstance(inventory.get(key), int) or inventory.get(key, 0) < 1:
            failures.append(f"inventory_{key}_invalid_or_empty")
    action_names = inventory.get("action_names")
    if not isinstance(action_names, list) or not all(isinstance(name, str) and name for name in action_names):
        failures.append("inventory_action_names_invalid")

    renders = proof.get("renders")
    renders = renders if isinstance(renders, list) else []
    rest_views: set[str] = set()
    action_poses: set[str] = set()
    render_paths: set[str] = set()
    render_hashes: set[str] = set()
    for index, record_value in enumerate(renders):
        record = record_value if isinstance(record_value, Mapping) else {}
        pose = _text(record.get("pose"))
        view = _text(record.get("view"))
        relative_name = Path(_text(record.get("path")))
        digest = _text(record.get("sha256")).lower()
        if (
            not relative_name.parts
            or relative_name.is_absolute()
            or len(relative_name.parts) != 1
            or relative_name.suffix.lower() != ".png"
        ):
            failures.append(f"render_{index}_path_invalid")
            continue
        if relative_name.as_posix() in render_paths:
            failures.append(f"render_{index}_path_duplicate")
        render_paths.add(relative_name.as_posix())
        if not _valid_sha(digest):
            failures.append(f"render_{index}_sha256_invalid")
        elif digest in render_hashes:
            failures.append(f"render_{index}_sha256_duplicate")
        render_hashes.add(digest)
        render_path = resolved_proof.parent / relative_name
        if not _regular_file(render_path):
            failures.append(f"render_{index}_missing_or_unsafe")
        else:
            if sha256_file(render_path) != digest:
                failures.append(f"render_{index}_sha256_mismatch")
            dimensions = _png_dimensions(render_path)
            if dimensions is None or dimensions[0] < 256 or dimensions[1] < 256:
                failures.append(f"render_{index}_png_invalid_or_too_small")
        if pose == "rest":
            rest_views.add(view)
        elif pose in REQUIRED_ACTION_POSES:
            action_poses.add(pose)
            if not _text(record.get("action")) or not isinstance(record.get("frame"), int):
                failures.append(f"render_{index}_action_binding_invalid")
    for view in sorted(REQUIRED_REST_VIEWS - rest_views):
        failures.append(f"required_rest_view_missing:{view}")
    for pose in sorted(REQUIRED_ACTION_POSES - action_poses):
        failures.append(f"required_action_pose_missing:{pose}")

    truth = proof.get("truth")
    truth = truth if isinstance(truth, Mapping) else {}
    if truth.get("private_clothed_diagnostic_only") is not True:
        failures.append("private_clothed_diagnostic_only_not_true")
    for key in REQUIRED_FALSE_TRUTH:
        if truth.get(key) is not False:
            failures.append(f"unsafe_or_missing_truth_flag:{key}")

    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 1,
        "status": (
            "integrity_verified_capabilities_unproven"
            if not failures
            else "blocked_integrity_failure"
        ),
        "integrity_verified": not failures,
        "proof_sha256": sha256_file(resolved_proof),
        "model_sha256": model_sha,
        "render_count": len(renders),
        "rest_views": sorted(rest_views),
        "action_poses": sorted(action_poses),
        "failures": failures,
        "visual_quality_proven": False,
        "owner_approval_proven": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "Exact file integrity does not prove likeness, anatomy, coverage, "
            "deformation quality, wearable behavior, owner approval, or readiness."
        ),
    }
