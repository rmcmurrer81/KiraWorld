#!/usr/bin/env python3
"""Fail-closed adjudication for one private Kira R5 *body component*.

This tool can pass only the bounded engineering component made of the adult
surface cage, skin material, preserved humanoid rig, diagnostic poses, and
measured floor/seat contact.  It cannot approve likeness, anatomy, eyes, hair,
clothes, a full avatar, runtime activation, owner review, or autobuild.

Visual review is never inferred from file existence.  A separate exact-hash
attestation is required and every visual check must be explicitly true.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_provisional_body_r5"
).resolve()
REQUIRED_VISUAL_CHECKS = (
    "continuous_skin_without_black_patchwork",
    "neutral_body_surface_and_pose_acceptable_as_provisional",
    "reach_deformation_acceptable_as_provisional",
    "stride_support_sole_visibly_planted",
    "seated_both_soles_visibly_planted",
    "seated_pelvis_visibly_supported_without_deep_intersection",
    "no_obvious_mesh_explosion_or_ground_penetration",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def bool_path(value: Any, *keys: str) -> bool:
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return False
        value = value[key]
    return value is True


def texture_is_nonzero(path: Path) -> bool:
    from PIL import Image

    with Image.open(path) as image:
        extrema = image.convert("RGBA").getextrema()
    return any(channel[1] > 0 for channel in extrema[:3]) and extrema[3][1] > 0


def hash_bound_file(path_value: Any, allowed_root: Path) -> tuple[str | None, str | None]:
    """Return the resolved path and current hash, or a fail-closed pair of Nones."""
    try:
        path = Path(str(path_value))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path = path.resolve(strict=True)
        path.relative_to(allowed_root)
        return str(path), sha256_file(path)
    except (FileNotFoundError, OSError, ValueError):
        return None, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--visual-attestation", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--update-manifest", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve(strict=True)
    attestation_path = Path(args.visual_attestation).resolve(strict=True)
    output_path = Path(args.output).resolve()
    run_dir = manifest_path.parent.resolve()
    run_dir.relative_to(ALLOWED_ROOT)
    attestation_path.relative_to(run_dir)
    output_path.relative_to(run_dir)
    manifest = load_json(manifest_path)
    attestation = load_json(attestation_path)
    candidate_path = Path(str(manifest.get("model", {}).get("path", ""))).resolve(strict=True)
    candidate_path.relative_to(run_dir)
    candidate_sha = sha256_file(candidate_path)

    exact_hash_guards = manifest.get("exact_hash_guards", {})
    source_current_path, source_current_sha = hash_bound_file(
        exact_hash_guards.get("source_project_path"), PROJECT_ROOT
    )
    live_current_path, live_current_sha = hash_bound_file(
        exact_hash_guards.get("live_model_project_path"), PROJECT_ROOT
    )

    structural_record = manifest.get("independent_audits", {}).get("structural", {})
    geometry_record = manifest.get("independent_audits", {}).get("geometry", {})
    structural_path = Path(str(structural_record.get("path", ""))).resolve(strict=True)
    geometry_path = Path(str(geometry_record.get("path", ""))).resolve(strict=True)
    structural_path.relative_to(run_dir)
    geometry_path.relative_to(run_dir)
    structural = load_json(structural_path)
    geometry = load_json(geometry_path)

    texture_records = manifest.get("skin_surface", {}).get("textures", {})
    texture_checks: dict[str, bool] = {}
    for role in ("albedo", "roughness", "normal"):
        record = texture_records.get(role, {}) if isinstance(texture_records, dict) else {}
        try:
            texture_path = Path(str(record.get("path", ""))).resolve(strict=True)
            texture_path.relative_to(run_dir)
            texture_checks[role] = (
                sha256_file(texture_path) == record.get("sha256")
                and texture_is_nonzero(texture_path)
            )
        except (FileNotFoundError, ValueError):
            texture_checks[role] = False

    renders = manifest.get("renders", {})
    render_hashes = {
        key: record.get("sha256")
        for key, record in renders.items()
        if isinstance(record, dict)
    }
    attested_render_hashes = attestation.get("render_sha256", {})
    expected_render_keys = {
        "neutral_front",
        "neutral_side",
        "neutral_back",
        "reach_front_three_quarter",
        "stride_front_three_quarter",
        "stride_side",
        "seated_front_three_quarter",
        "seated_side",
    }
    actual_render_hashes: dict[str, str | None] = {}
    render_paths_inside_run = True
    for key in expected_render_keys:
        record = renders.get(key, {}) if isinstance(renders, dict) else {}
        path_value = record.get("path") if isinstance(record, dict) else None
        resolved_path, current_sha = hash_bound_file(path_value, run_dir)
        if resolved_path is None:
            render_paths_inside_run = False
        actual_render_hashes[key] = current_sha

    contact_sheet_record = manifest.get("contact_sheet", {})
    contact_sheet_path, contact_sheet_current_sha = hash_bound_file(
        contact_sheet_record.get("path") if isinstance(contact_sheet_record, dict) else None,
        run_dir,
    )
    visual_checks = attestation.get("checks", {})
    pose_metrics = manifest.get("pose_metrics", {})
    seated_contact = pose_metrics.get("seated", {}).get("foot_contact", {})
    stride_contact = pose_metrics.get("stride", {}).get("foot_contact", {})
    seat_support = pose_metrics.get("seated", {}).get("seat_support", {})
    topology = manifest.get("seam_and_topology_audit", {}).get("after_topology", {})
    weights = manifest.get("seam_and_topology_audit", {}).get("after_weights", {})
    criteria: dict[str, bool] = {
        "candidate_exact_hash_matches_manifest": candidate_sha == manifest.get("model", {}).get("sha256"),
        "candidate_is_transformed_derivative": bool_path(
            manifest, "exact_hash_guards", "candidate_differs_from_source"
        ),
        "source_hash_guard_current_and_unchanged": (
            source_current_path is not None
            and bool_path(manifest, "exact_hash_guards", "source_unchanged")
            and source_current_sha == exact_hash_guards.get("source_sha256_before")
            and source_current_sha == exact_hash_guards.get("source_sha256_after")
            and source_current_sha == manifest.get("source", {}).get("sha256")
        ),
        "live_avatar_hash_guard_current_and_unchanged": (
            live_current_path is not None
            and bool_path(manifest, "exact_hash_guards", "live_model_unchanged")
            and live_current_sha == exact_hash_guards.get("live_model_sha256_before")
            and live_current_sha == exact_hash_guards.get("live_model_sha256_after")
        ),
        "safe_weld_uv_preserved": bool_path(
            manifest, "seam_and_topology_audit", "uv_multiset_preserved"
        ),
        "single_positional_surface_island": topology.get("surface_island_count") == 1,
        "no_nonmanifold_or_collapsed_faces": (
            topology.get("non_manifold_edge_count") == 0
            and topology.get("collapsed_face_count") == 0
        ),
        "skin_weights_complete": (
            weights.get("unweighted_vertex_count") == 0
            and weights.get("weight_sum_out_of_tolerance_count") == 0
        ),
        "exact_79_joint_rig_preserved": (
            manifest.get("rig", {}).get("bone_count") == 79
            and bool_path(manifest, "rig", "bone_order_and_names_exactly_preserved")
            and bool_path(manifest, "rig", "required_core_bones_present")
        ),
        "structural_glb_audit_exact_hash": (
            structural.get("sha256") == candidate_sha
            and sha256_file(structural_path) == structural_record.get("sha256")
        ),
        "structural_humanoid_rig_ready": structural.get("humanoid_rig_structurally_ready") is True,
        "reversible_morph_and_four_pose_actions_exported": (
            structural.get("topology_metrics", {}).get("morph_target_count") == 1
            and structural.get("topology_metrics", {}).get("animation_count") == 4
        ),
        "geometry_audit_exact_hash": (
            geometry.get("candidate_sha256") == candidate_sha
            and sha256_file(geometry_path) == geometry_record.get("sha256")
        ),
        "principled_body_material_present": bool_path(
            geometry, "materials", "body_has_principled_material"
        ),
        "all_pbr_texture_files_hash_bound_and_nonzero": all(texture_checks.values()),
        "all_four_pose_metrics_finite": all(
            pose_metrics.get(name, {}).get("finite_coordinates") is True
            for name in ("neutral", "reach", "stride", "seated")
        ),
        "stride_support_foot_full_sole_contact": bool_path(
            stride_contact, "right", "full_sole_contact_sanity"
        ),
        "seated_both_feet_full_sole_contact": (
            bool_path(seated_contact, "left", "full_sole_contact_sanity")
            and bool_path(seated_contact, "right", "full_sole_contact_sanity")
        ),
        "seated_pelvis_stable_support_sanity": seat_support.get("stable_support_sanity") is True,
        "visual_attestation_candidate_hash_matches": attestation.get("candidate_sha256") == candidate_sha,
        "visual_attestation_contact_sheet_hash_matches": (
            contact_sheet_path is not None
            and contact_sheet_current_sha == manifest.get("contact_sheet", {}).get("sha256")
            and
            attestation.get("contact_sheet_sha256")
            == manifest.get("contact_sheet", {}).get("sha256")
        ),
        "visual_attestation_all_render_hashes_match": (
            set(render_hashes) == expected_render_keys
            and set(attested_render_hashes) == expected_render_keys
            and render_hashes == attested_render_hashes
            and render_paths_inside_run
            and actual_render_hashes == render_hashes
        ),
        "all_required_visual_checks_explicitly_passed": (
            isinstance(visual_checks, dict)
            and all(visual_checks.get(name) is True for name in REQUIRED_VISUAL_CHECKS)
        ),
        "candidate_remains_private_inactive_unapproved": (
            bool_path(manifest, "privacy_and_activation", "private_body_builder_review_only")
            and manifest.get("privacy_and_activation", {}).get("runtime_activation_allowed") is False
            and manifest.get("privacy_and_activation", {}).get("owner_approved") is False
            and manifest.get("privacy_and_activation", {}).get("autobuild_gate_passed_subjects") == 0
        ),
    }
    passed = all(criteria.values())
    report = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_sha256": candidate_sha,
        "scope": "provisional_body_component_only",
        "provisional_body_component_passed": passed,
        "criteria": criteria,
        "failed_criteria": [name for name, value in criteria.items() if not value],
        "contact_evidence": {
            "stride_support_right": stride_contact.get("right", {}),
            "seated_left": seated_contact.get("left", {}),
            "seated_right": seated_contact.get("right", {}),
            "seat_support": seat_support,
        },
        "visual_attestation": {
            "path": str(attestation_path),
            "sha256": sha256_file(attestation_path),
            "reviewer": attestation.get("reviewer"),
            "checks": visual_checks,
        },
        "current_hash_evidence": {
            "source_path": source_current_path,
            "source_sha256": source_current_sha,
            "live_avatar_path": live_current_path,
            "live_avatar_sha256": live_current_sha,
            "contact_sheet_path": contact_sheet_path,
            "contact_sheet_sha256": contact_sheet_current_sha,
            "render_sha256": actual_render_hashes,
        },
        "explicit_nonclaims": {
            "likeness_passed": False,
            "anatomical_completeness_passed": False,
            "eyes_passed": False,
            "hair_passed": False,
            "clothing_passed": False,
            "full_avatar_passed": False,
            "stable_runtime_locomotion_proven": False,
            "owner_approved": False,
            "runtime_activation_allowed": False,
            "autobuild_unlocked": False,
        },
        "truth_note": (
            "A true result approves only this exact hash as a provisional body engineering component. "
            "It never converts the candidate into a complete Kira avatar or unlocks activation/autobuild."
        ),
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.update_manifest:
        manifest["body_component_verdict"] = {
            "path": str(output_path),
            "sha256": sha256_file(output_path),
            "candidate_sha256": candidate_sha,
            "scope": report["scope"],
            "provisional_body_component_passed": passed,
            "owner_approved": False,
            "autobuild_unlocked": False,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 4


if __name__ == "__main__":
    raise SystemExit(main())
