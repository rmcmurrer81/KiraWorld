"""Fail-closed quality gate for exactly one inactive avatar body candidate.

This module is deliberately narrower than the positive-proof and two-subject
autobuild gates.  It can audit one exact GLB and one exact set of private
review renders, but it can never activate a body, infer owner approval, or
release a multi-profile queue.

The gate has two independent passes:

* pass 1 verifies artifact lineage, adult-lane authority, GLB/rig structure,
  hash-bound geometry/rig/anatomy evidence, eye controls, grounding, and
  complete render bindings;
* pass 2 verifies that an independent reviewer actually inspected those same
  rendered bytes and passed every required visual criterion.

Static structure is not treated as proof of deformation, anatomy, likeness,
eye seating, or visual quality.  Missing evidence is a failure, not a guess.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from Core.avatar_body_topology import (
    evaluate_body_candidate_readiness,
    inspect_glb_topology,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PROHIBITED_AUTHORING_METHODS = frozenset(
    {
        "procedural_eye_caps",
        "threshold_cut_body_surface_clothing",
        "body_surface_shell_garments",
        "primitive_slab_or_box_garments",
        "primitive_box_shoes",
        "re_rendering_known_rejected_candidate_bytes",
        "unmodified_reference_copy",
    }
)

REQUIRED_RENDER_VIEWS = (
    "neutral_front",
    "neutral_side",
    "neutral_back",
    "head_front",
    "eye_close",
    "stride_front",
    "reach_front",
    "seated_front",
    "bed_side",
)

HEAD_RENDER_VIEWS = frozenset({"head_front", "eye_close"})

REQUIRED_VISUAL_CRITERIA = (
    "adult_body_proportions",
    "continuous_body_surface",
    "hands_and_feet",
    "realistic_eye_materials",
    "eyes_seated_in_sockets",
    "neutral_ground_contact",
    "shoulder_elbow_wrist_deformation",
    "hand_and_finger_deformation",
    "hip_knee_ankle_deformation",
    "seated_contact_and_deformation",
    "bed_pose_contact_and_deformation",
    "subject_identity_not_generic_base",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("json_root_not_object")
    return data


def _project_file(project_root: Path, raw: Any) -> Path | None:
    """Resolve one ordinary file without permitting traversal or symlinks."""

    text = _text(raw)
    if not text:
        return None
    relative = Path(text)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    lexical = project_root
    for part in relative.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            return None
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _verify_file_binding(
    project_root: Path,
    binding: Any,
    label: str,
    failures: list[str],
    *,
    suffixes: tuple[str, ...] = (),
) -> tuple[Path | None, str]:
    if not isinstance(binding, Mapping):
        failures.append(f"{label}_binding_missing")
        return None, ""
    path = _project_file(project_root, binding.get("path"))
    expected = _text(binding.get("sha256")).lower()
    if path is None:
        failures.append(f"{label}_path_invalid")
        return None, expected
    if suffixes and path.suffix.lower() not in suffixes:
        failures.append(f"{label}_file_type_invalid")
    if not _valid_sha256(expected):
        failures.append(f"{label}_sha256_invalid")
        return path, expected
    actual = _sha256_file(path)
    if actual != expected:
        failures.append(f"{label}_sha256_mismatch")
    return path, actual


def _load_bound_json(
    project_root: Path,
    binding: Any,
    label: str,
    failures: list[str],
) -> tuple[dict[str, Any] | None, str]:
    path, digest = _verify_file_binding(
        project_root,
        binding,
        label,
        failures,
        suffixes=(".json",),
    )
    if path is None:
        return None, digest
    try:
        return _read_json(path), digest
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append(f"{label}_json_invalid")
        return None, digest


def render_occupancy_sanity(path: Path, *, head_view: bool) -> dict[str, Any]:
    """Reject blank, edge-filled, or badly cropped dark-backdrop renders.

    This is only a framing/legibility check.  A passing image is not a visual
    quality approval.
    """

    try:
        with Image.open(path) as source:
            image = source.convert("RGB")
            width, height = image.size
            pixels = image.load()
            y_limit = max(1, round(height * 0.93))
            points: list[tuple[int, int]] = []
            for y in range(y_limit):
                for x in range(width):
                    red, green, blue = pixels[x, y]
                    if max(red, green, blue) >= 92 and red + green + blue >= 260:
                        points.append((x, y))
    except (OSError, ValueError):
        return {"passed": False, "reason": "render_unreadable"}
    if not points:
        return {"passed": False, "reason": "no_lit_subject_pixels"}
    left = min(point[0] for point in points)
    right = max(point[0] for point in points)
    top = min(point[1] for point in points)
    bottom = max(point[1] for point in points)
    box_width = (right - left + 1) / width
    box_height = (bottom - top + 1) / height
    coverage = len(points) / (width * y_limit)
    if head_view:
        passed = (
            0.18 <= box_width <= 0.94
            and 0.32 <= box_height <= 0.96
            and top / height <= 0.34
            and coverage >= 0.025
        )
    else:
        passed = (
            0.08 <= box_width <= 0.82
            and 0.58 <= box_height <= 0.96
            and top / height <= 0.24
            and coverage >= 0.02
        )
    return {
        "passed": passed,
        "reason": "legible_bounded_subject" if passed else "render_crop_or_occupancy_failed",
        "lit_subject_bbox_px": [left, top, right, bottom],
        "bbox_width_fraction": round(box_width, 6),
        "bbox_height_fraction": round(box_height, 6),
        "top_margin_fraction": round(top / height, 6),
        "lit_pixel_coverage": round(coverage, 6),
        "head_view": head_view,
    }


def _authority_entry(
    catalog: Mapping[str, Any], source_digest: str
) -> Mapping[str, Any] | None:
    entries = catalog.get("entries")
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if (
            isinstance(entry, Mapping)
            and _text(entry.get("sha256")).lower() == source_digest
        ):
            return entry
    return None


def _evaluate_geometry_audit(
    audit: Mapping[str, Any] | None,
    candidate_digest: str,
    failures: list[str],
) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    if not isinstance(audit, Mapping):
        failures.append("geometry_audit_missing")
        return safe
    if _text(audit.get("candidate_sha256")).lower() != candidate_digest:
        failures.append("geometry_audit_candidate_sha256_mismatch")
    if _normalized(audit.get("audit_mode")) != "read_only_blender_geometry_v1":
        failures.append("geometry_audit_mode_invalid")

    body = audit.get("primary_body")
    if not isinstance(body, Mapping):
        failures.append("geometry_primary_body_missing")
        body = {}
    if body.get("present") is not True:
        failures.append("geometry_primary_body_not_present")
    for field, failure in (
        ("vertex_count", "body_vertex_count_invalid"),
        ("triangle_count", "body_triangle_count_invalid"),
    ):
        value = body.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            failures.append(failure)
    integer_zero_fields = {
        "unweighted_vertex_count": "body_has_unweighted_vertices",
        "weight_sum_out_of_tolerance_count": "body_weights_not_normalized",
        "degenerate_face_count": "body_has_degenerate_faces",
        "collapsed_face_count_after_positional_weld": "body_has_weld_collapsed_faces",
        "non_manifold_edge_count": "body_has_non_manifold_edges",
        "open_boundary_chain_count": "body_has_open_boundary_chains",
        "unused_vertex_count": "body_has_unused_vertices",
        "vertices_over_four_influences": "body_has_vertices_over_four_influences",
    }
    for field, failure in integer_zero_fields.items():
        value = body.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            failures.append(failure)
    islands = body.get("surface_island_count")
    if not isinstance(islands, int) or isinstance(islands, bool) or islands != 1:
        failures.append("body_surface_is_not_one_continuous_island")
    boundary_loops = body.get("boundary_loop_count")
    reviewed_loops = body.get("reviewed_intentional_boundary_loop_count")
    if (
        not isinstance(boundary_loops, int)
        or isinstance(boundary_loops, bool)
        or not isinstance(reviewed_loops, int)
        or isinstance(reviewed_loops, bool)
        or boundary_loops != reviewed_loops
    ):
        failures.append("body_boundary_loops_not_fully_reviewed")
    influences = body.get("maximum_positive_influences_per_vertex")
    if not isinstance(influences, int) or isinstance(influences, bool) or not 1 <= influences <= 4:
        failures.append("body_vertex_influence_limit_failed")

    axis = audit.get("neutral_axis_and_grounding")
    if not isinstance(axis, Mapping):
        failures.append("neutral_axis_and_grounding_missing")
        axis = {}
    if axis.get("finite_coordinates") is not True:
        failures.append("neutral_body_coordinates_not_finite")
    extent = axis.get("body_extent")
    if not (
        isinstance(extent, list)
        and len(extent) == 3
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in extent)
    ):
        failures.append("neutral_body_extent_invalid")
    else:
        width, depth, height = (float(value) for value in extent)
        if not (height > 0 and height > width * 1.35 and height > depth * 2.0):
            failures.append("neutral_body_axis_or_proportions_invalid")
    ground_offset = axis.get("lowest_body_z")
    if not isinstance(ground_offset, (int, float)) or isinstance(ground_offset, bool):
        failures.append("neutral_ground_offset_missing")
    elif abs(float(ground_offset)) > 0.015:
        failures.append("neutral_feet_not_within_ground_tolerance")
    if axis.get("ground_contact_dynamically_proven") is not True:
        failures.append("dynamic_ground_contact_not_proven")

    extras = audit.get("nonbody_geometry")
    if not isinstance(extras, Mapping):
        failures.append("nonbody_geometry_audit_missing")
        extras = {}
    for field, failure in (
        ("oversized_unclassified_mesh_count", "oversized_unclassified_geometry_present"),
        ("unclassified_mesh_count", "unclassified_geometry_present"),
    ):
        value = extras.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            failures.append(failure)

    materials = audit.get("materials")
    if not isinstance(materials, Mapping):
        failures.append("material_audit_missing")
        materials = {}
    if materials.get("all_renderable_meshes_have_materials") is not True:
        failures.append("renderable_geometry_has_missing_materials")
    if materials.get("body_has_principled_material") is not True:
        failures.append("body_principled_material_missing")
    if (
        materials.get("all_sclera_iris_pupil_components_have_principled_materials")
        is not True
    ):
        failures.append("eye_component_principled_materials_incomplete")
    if materials.get("eye_material_visual_realism_proven") is not True:
        failures.append("eye_material_visual_realism_not_proven")

    eyes = audit.get("eyes")
    if not isinstance(eyes, Mapping):
        failures.append("eye_geometry_audit_missing")
        eyes = {}
    role_counts = eyes.get("role_counts")
    if not isinstance(role_counts, Mapping):
        failures.append("eye_role_counts_missing")
        role_counts = {}
    for role in ("sclera", "iris", "pupil"):
        if role_counts.get(role) != 2:
            failures.append(f"eye_{role}_pair_missing")
    for role in ("eyelid_control", "gaze_control", "blink_control"):
        value = role_counts.get(role)
        if not isinstance(value, int) or isinstance(value, bool) or value < 2:
            failures.append(f"eye_{role}_pair_missing")
    if eyes.get("all_eye_components_bound_to_head_or_eye_controls") is not True:
        failures.append("eye_components_not_bound_to_head_or_eye_controls")
    if eyes.get("socket_fit_measurement_passed") is not True:
        failures.append("eye_socket_fit_not_measurement_proven")
    if eyes.get("bilateral_symmetry_sanity_passed") is not True:
        failures.append("eye_bilateral_symmetry_failed")

    safe.update(
        {
            "audit_mode": _text(audit.get("audit_mode")),
            "candidate_sha256": _text(audit.get("candidate_sha256")).lower(),
            "primary_body": dict(body),
            "neutral_axis_and_grounding": dict(axis),
            "nonbody_geometry": dict(extras),
            "materials": dict(materials),
            "eyes": dict(eyes),
        }
    )
    return safe


def _evaluate_render_bindings(
    project_root: Path,
    manifest: Mapping[str, Any],
    failures: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    review_dir_raw = manifest.get("review_run_directory")
    review_dir_text = _text(review_dir_raw)
    review_dir = project_root / review_dir_text if review_dir_text else None
    try:
        resolved_review_dir = review_dir.resolve(strict=True) if review_dir else None
        if resolved_review_dir is not None:
            resolved_review_dir.relative_to(project_root.resolve(strict=True))
            if not resolved_review_dir.is_dir():
                resolved_review_dir = None
    except (OSError, ValueError):
        resolved_review_dir = None
    if resolved_review_dir is None:
        failures.append("review_run_directory_invalid")

    renders = manifest.get("renders")
    if not isinstance(renders, Mapping):
        failures.append("render_bindings_missing")
        renders = {}
    bindings: dict[str, Any] = {}
    framing: dict[str, Any] = {}
    seen_paths: set[Path] = set()
    for view in REQUIRED_RENDER_VIEWS:
        local_failures: list[str] = []
        path, digest = _verify_file_binding(
            project_root,
            renders.get(view),
            f"render_{view}",
            local_failures,
            suffixes=(".png", ".jpg", ".jpeg", ".webp"),
        )
        failures.extend(local_failures)
        if path is None:
            continue
        if resolved_review_dir is not None:
            try:
                path.relative_to(resolved_review_dir)
            except ValueError:
                failures.append(f"render_{view}_escapes_exact_review_directory")
        if path in seen_paths:
            failures.append(f"render_{view}_duplicates_another_view")
        seen_paths.add(path)
        bindings[view] = {"sha256": digest, "path": _text(renders[view].get("path"))}
        sanity = render_occupancy_sanity(path, head_view=view in HEAD_RENDER_VIEWS)
        framing[view] = sanity
        if sanity.get("passed") is not True:
            failures.append(f"render_{view}_framing_failed")
    extra_views = sorted(set(renders) - set(REQUIRED_RENDER_VIEWS))
    return bindings, {"views": framing, "extra_views_ignored": extra_views}


def evaluate_objective_body_gate(
    project_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate pass 1 for one exact, inactive candidate."""

    root = Path(project_root).resolve(strict=True)
    failures: list[str] = []
    warnings: list[str] = []
    if manifest.get("schema_version") != 1:
        failures.append("manifest_schema_version_invalid")
    if _normalized(manifest.get("scope")) != "single_inactive_candidate":
        failures.append("manifest_scope_must_be_single_inactive_candidate")
    subject_id = _text(manifest.get("subject_id"))
    candidate_id = _text(manifest.get("candidate_id"))
    maturity = _normalized(manifest.get("subject_maturity"))
    if not subject_id:
        failures.append("subject_id_missing")
    if not candidate_id:
        failures.append("candidate_id_missing")
    if maturity not in {"adult", "confirmed_adult", "adult_confirmed"}:
        failures.append("candidate_not_in_adult_maturity_lane")

    candidate_path, candidate_digest = _verify_file_binding(
        root,
        manifest.get("candidate"),
        "candidate",
        failures,
        suffixes=(".glb",),
    )
    source_path, source_digest = _verify_file_binding(
        root,
        manifest.get("source"),
        "source",
        failures,
        suffixes=(".glb",),
    )
    if candidate_digest and source_digest and candidate_digest == source_digest:
        failures.append("candidate_is_unmodified_source_copy")

    authority, authority_digest = _load_bound_json(
        root,
        manifest.get("source_authority_catalog"),
        "source_authority_catalog",
        failures,
    )
    authority_entry = _authority_entry(authority or {}, source_digest)
    if authority_entry is None:
        failures.append("source_not_found_in_exact_authority_catalog")
        authority_entry = {}
    else:
        if _normalized(authority_entry.get("topology_lane")) != "confirmed_adult_topology":
            failures.append("source_not_confirmed_for_adult_topology_lane")
        maturity_authority = authority_entry.get("maturity_authority")
        if not isinstance(maturity_authority, Mapping) or maturity_authority.get("adult_only") is not True:
            failures.append("source_adult_only_authority_missing")
        if _normalized(authority_entry.get("allowed_use")) != "cage_fit_source_new_surface_required":
            failures.append("source_allowed_use_invalid")
        if authority_entry.get("copy_as_candidate_body_allowed") is not False:
            failures.append("source_copy_prohibition_missing")
        expected_path = _text(authority_entry.get("path"))
        if source_path is not None and expected_path:
            expected_source = _project_file(root, expected_path)
            if expected_source is None or expected_source != source_path:
                failures.append("source_path_does_not_match_authority_catalog")

    lineage = manifest.get("lineage")
    if not isinstance(lineage, Mapping):
        failures.append("lineage_missing")
        lineage = {}
    if _text(lineage.get("source_sha256")).lower() != source_digest:
        failures.append("lineage_source_sha256_mismatch")
    methods = lineage.get("authoring_methods")
    if not isinstance(methods, list):
        failures.append("lineage_authoring_methods_missing")
        methods = []
    prohibited = sorted(
        PROHIBITED_AUTHORING_METHODS.intersection(_normalized(value) for value in methods)
    )
    if prohibited:
        failures.extend(f"prohibited_authoring_method:{value}" for value in prohibited)

    anatomy_attestation, _ = _load_bound_json(
        root,
        manifest.get("anatomy_attestation"),
        "anatomy_attestation",
        failures,
    )
    rig_attestation, _ = _load_bound_json(
        root,
        manifest.get("rig_attestation"),
        "rig_attestation",
        failures,
    )
    topology = (
        inspect_glb_topology(
            candidate_path,
            artifact_id=candidate_id or "single_candidate",
            anatomy_attestation=anatomy_attestation,
            rig_attestation=rig_attestation,
        )
        if candidate_path is not None
        else {}
    )
    readiness = evaluate_body_candidate_readiness(
        topology,
        subject_id=subject_id,
        subject_maturity=maturity,
        lineage=lineage,
        request_complete_adult_anatomy=True,
    )
    failures.extend(_text(value) for value in readiness.get("failures", []) if _text(value))
    warnings.extend(_text(value) for value in readiness.get("warnings", []) if _text(value))

    geometry_audit, geometry_audit_digest = _load_bound_json(
        root,
        manifest.get("geometry_audit"),
        "geometry_audit",
        failures,
    )
    geometry = _evaluate_geometry_audit(geometry_audit, candidate_digest, failures)

    render_bindings, render_framing = _evaluate_render_bindings(root, manifest, failures)

    for key in ("runtime_activation_allowed", "public_export_allowed"):
        if manifest.get(key) is not False:
            failures.append(f"manifest_{key}_must_be_false")
    if manifest.get("ordinary_owner_review_is_clothed") is not True:
        failures.append("ordinary_owner_review_must_be_clothed")

    failures = _dedupe(failures)
    passed = not failures
    return {
        "schema_version": 1,
        "gate": "single_body_objective_quality_v1",
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "subject_maturity": maturity,
        "candidate_sha256": candidate_digest,
        "source_sha256": source_digest,
        "source_authority_catalog_sha256": authority_digest,
        "geometry_audit_sha256": geometry_audit_digest,
        "status": "objective_passed" if passed else "objective_blocked",
        "passed": passed,
        "failures": failures,
        "warnings": _dedupe(warnings),
        "topology": topology,
        "readiness": readiness,
        "geometry": geometry,
        "render_bindings": render_bindings,
        "render_framing": render_framing,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "owner_approval_inferred": False,
        "automatic_multi_profile_queue_allowed": False,
        "truth_note": (
            "Pass 1 proves only this exact inactive artifact and exact private review bytes "
            "met the declared objective gates. It cannot approve likeness or release runtime."
        ),
    }


def evaluate_rendered_visual_gate(
    objective: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate pass 2 against the exact renders recorded by pass 1."""

    failures: list[str] = []
    if objective.get("passed") is not True:
        failures.append("objective_pass_must_succeed_before_visual_pass")
    if review.get("schema_version") != 1:
        failures.append("visual_review_schema_version_invalid")
    if _normalized(review.get("review_scope")) != "independent_rendered_candidate_review":
        failures.append("visual_review_scope_invalid")
    if _text(review.get("candidate_sha256")).lower() != _text(
        objective.get("candidate_sha256")
    ).lower():
        failures.append("visual_review_candidate_sha256_mismatch")
    reviewer = review.get("reviewer")
    if not isinstance(reviewer, Mapping):
        failures.append("visual_reviewer_missing")
        reviewer = {}
    if _normalized(reviewer.get("role")) not in {
        "codex_independent_visual_reviewer",
        "human_independent_visual_reviewer",
    }:
        failures.append("visual_reviewer_role_not_independent")
    if not _text(reviewer.get("id")) or not _text(review.get("reviewed_at")):
        failures.append("visual_reviewer_identity_or_time_missing")

    expected_renders = objective.get("render_bindings")
    reviewed_renders = review.get("render_sha256")
    if not isinstance(expected_renders, Mapping) or not isinstance(reviewed_renders, Mapping):
        failures.append("visual_review_render_hashes_missing")
    else:
        for view in REQUIRED_RENDER_VIEWS:
            expected = expected_renders.get(view)
            digest = _text(expected.get("sha256")) if isinstance(expected, Mapping) else ""
            if _text(reviewed_renders.get(view)).lower() != digest.lower():
                failures.append(f"visual_review_render_sha256_mismatch:{view}")

    criteria = review.get("criteria")
    if not isinstance(criteria, Mapping):
        failures.append("visual_review_criteria_missing")
        criteria = {}
    for name in REQUIRED_VISUAL_CRITERIA:
        record = criteria.get(name)
        if not isinstance(record, Mapping):
            failures.append(f"visual_criterion_missing:{name}")
            continue
        if _normalized(record.get("decision")) != "pass":
            failures.append(f"visual_criterion_not_passed:{name}")
        if not _text(record.get("observation")):
            failures.append(f"visual_criterion_observation_missing:{name}")
    if _normalized(review.get("overall_decision")) != "pass":
        failures.append("visual_review_overall_decision_not_pass")
    if review.get("owner_approval") is not False:
        failures.append("visual_review_must_not_self_create_owner_approval")

    failures = _dedupe(failures)
    passed = not failures
    return {
        "schema_version": 1,
        "gate": "single_body_rendered_visual_quality_v1",
        "candidate_id": _text(objective.get("candidate_id")),
        "candidate_sha256": _text(objective.get("candidate_sha256")).lower(),
        "status": "visual_passed" if passed else "visual_blocked",
        "passed": passed,
        "failures": failures,
        "owner_approval_inferred": False,
        "runtime_activation_allowed": False,
        "automatic_multi_profile_queue_allowed": False,
    }


def evaluate_two_pass_body_quality(
    project_root: Path,
    manifest: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    """Run both passes while keeping all release/activation routes locked."""

    objective = evaluate_objective_body_gate(project_root, manifest)
    visual = evaluate_rendered_visual_gate(objective, review)
    passed = objective["passed"] is True and visual["passed"] is True
    return {
        "schema_version": 1,
        "gate": "single_body_two_pass_quality_v1",
        "candidate_id": objective["candidate_id"],
        "candidate_sha256": objective["candidate_sha256"],
        "status": "two_pass_quality_passed" if passed else "two_pass_quality_blocked",
        "passed": passed,
        "objective": objective,
        "rendered_visual": visual,
        "owner_approval_inferred": False,
        "owner_approval_still_required": True,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "automatic_multi_profile_queue_allowed": False,
        "authoritative_batch_gate_unchanged": "avatar_two_distinct_subject_autobuild_gate_v2",
        "truth_note": (
            "Even a two-pass success is only a one-candidate private quality result. Owner "
            "approval and the existing distinct-two-subject release gate remain separate."
        ),
    }


__all__ = [
    "PROHIBITED_AUTHORING_METHODS",
    "REQUIRED_RENDER_VIEWS",
    "REQUIRED_VISUAL_CRITERIA",
    "evaluate_objective_body_gate",
    "evaluate_rendered_visual_gate",
    "evaluate_two_pass_body_quality",
    "render_occupancy_sanity",
]
