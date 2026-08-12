#!/usr/bin/env python3
"""Audit an isolated Kira R7 Blender workspace without rendering or export."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

import bpy


def load_helpers():
    helper_path = Path(__file__).resolve().with_name(
        "blender_prepare_kira_r7_authoring_workspace.py"
    )
    spec = importlib.util.spec_from_file_location("kira_r7_workspace_helpers", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load workspace helpers: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_helpers()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--attestation", default="")
    return parser.parse_args(argv)


def index_hash(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in indices:
        digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def mask_snapshot(body: bpy.types.Object, name: str) -> dict[str, object]:
    attribute = body.data.attributes.get(name)
    if attribute is None:
        return {
            "present": False,
            "domain": None,
            "data_type": None,
            "value_count": 0,
            "nonzero_vertex_count": 0,
            "fractional_value_count": 0,
            "vertex_index_sha256": index_hash([]),
            "indices": [],
        }
    values = [float(item.value) for item in attribute.data]
    nonzero = [index for index, value in enumerate(values) if value >= 0.5]
    fractional = sum(value not in (0.0, 1.0) for value in values)
    return {
        "present": True,
        "domain": attribute.domain,
        "data_type": attribute.data_type,
        "value_count": len(values),
        "nonzero_vertex_count": len(nonzero),
        "fractional_value_count": fractional,
        "minimum_value": min(values, default=0.0),
        "maximum_value": max(values, default=0.0),
        "vertex_index_sha256": index_hash(nonzero),
        "indices": nonzero,
    }


def snapshot_matches_source(current: dict[str, object], source: dict[str, object]) -> dict[str, bool]:
    return {
        "object_and_data_names": (
            current["body_object_name"] == source["body_object_name"]
            and current["body_mesh_name"] == source["body_mesh_name"]
            and current["armature_object_name"] == source["armature_object_name"]
            and current["armature_data_name"] == source["armature_data_name"]
        ),
        "vertex_edge_polygon_loop_counts": all(
            current[key] == source[key]
            for key in ("vertex_count", "edge_count", "polygon_count", "loop_count")
        ),
        "face_index_topology": (
            current["topology_face_index_sha256"]
            == source["topology_face_index_sha256"]
        ),
        "mixed_surface_positions": (
            current["mixed_surface_position_sha256"]
            == source["mixed_surface_position_sha256"]
        ),
        "shape_keys": current["shape_keys"] == source["shape_keys"],
        "uv": current["uv"] == source["uv"],
        "skin_weights_and_vertex_groups": current["weights"] == source["weights"],
        "rig_names_order_parents_and_rest_matrices": current["rig"] == source["rig"],
        "object_transforms": (
            current["body_matrix_world"] == source["body_matrix_world"]
            and current["armature_matrix_world"] == source["armature_matrix_world"]
        ),
        "materials": (
            current["material_slot_count"] == source["material_slot_count"]
            and current["material_slot_names"] == source["material_slot_names"]
        ),
    }


def validate_attestation(
    path: str,
    *,
    workspace_id: str,
    source_sha256: str,
    snapshots: dict[str, dict[str, object]],
) -> dict[str, object]:
    if not path:
        return {
            "provided": False,
            "reviewed": False,
            "identity_matches": False,
            "mask_results": {},
            "all_declared_masks_match": False,
        }
    attestation_path = Path(path).resolve(strict=True)
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    identity_matches = (
        attestation.get("workspace_id") == workspace_id
        and str(attestation.get("source_sha256", "")).lower() == source_sha256.lower()
    )
    reviewed = bool(attestation.get("reviewed")) and bool(attestation.get("reviewer"))
    mask_results: dict[str, object] = {}
    for name, snapshot in snapshots.items():
        declared = attestation.get("masks", {}).get(name, {})
        mask_results[name] = {
            "meaning_confirmed": bool(declared.get("meaning_confirmed")),
            "vertex_count_matches": (
                declared.get("vertex_count") == snapshot["nonzero_vertex_count"]
            ),
            "vertex_index_sha256_matches": (
                declared.get("vertex_index_sha256") == snapshot["vertex_index_sha256"]
            ),
        }
    all_match = bool(mask_results) and all(
        value["meaning_confirmed"]
        and value["vertex_count_matches"]
        and value["vertex_index_sha256_matches"]
        for value in mask_results.values()
    )
    return {
        "provided": True,
        "path": str(attestation_path),
        "reviewed": reviewed,
        "identity_matches": identity_matches,
        "mask_results": mask_results,
        "all_declared_masks_match": all_match,
        "valid": reviewed and identity_matches and all_match,
    }


def main() -> int:
    args = parse_args()
    baseline_path = Path(args.baseline).resolve(strict=True)
    registry_path = Path(args.registry).resolve(strict=True)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    workspace_id = baseline["workspace_id"]
    source_sha256 = baseline["source"]["sha256"]
    source_snapshot = baseline["exact_import_snapshot"]

    working_bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    protected_bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "exact_full_surface_baseline"
    ]
    rigs = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE" and obj.get("r7_role") == "protected_exact_79_bone_rig"
    ]
    if len(working_bodies) != 1 or len(protected_bodies) != 1 or len(rigs) != 1:
        raise ValueError("workspace does not contain exactly one working body, baseline body, and protected rig")
    body = working_bodies[0]
    protected_body = protected_bodies[0]
    armature = rigs[0]

    current = helpers.object_snapshot(body, armature)
    preservation = snapshot_matches_source(current, source_snapshot)
    prepared_exact = all(preservation.values())

    protected_geometry = {
        "vertex_count_matches": len(protected_body.data.vertices) == source_snapshot["vertex_count"],
        "edge_count_matches": len(protected_body.data.edges) == source_snapshot["edge_count"],
        "polygon_count_matches": len(protected_body.data.polygons) == source_snapshot["polygon_count"],
        "face_index_topology_matches": (
            helpers.topology_hash(protected_body.data)
            == source_snapshot["topology_face_index_sha256"]
        ),
        "mixed_surface_positions_match": (
            helpers.hash_float_rows(helpers.mixed_position_rows(protected_body.data))
            == source_snapshot["mixed_surface_position_sha256"]
        ),
        "shape_keys_match": (
            helpers.shape_key_snapshot(protected_body.data) == source_snapshot["shape_keys"]
        ),
        "hidden_from_view_and_render": bool(
            protected_body.hide_viewport and protected_body.hide_render
        ),
        "selection_locked": bool(protected_body.hide_select),
    }

    expected_masks = [item["attribute"] for item in registry["masks"]]
    mask_snapshots = {name: mask_snapshot(body, name) for name in expected_masks}
    public_mask_snapshots = {
        name: {key: value for key, value in snapshot.items() if key != "indices"}
        for name, snapshot in mask_snapshots.items()
    }
    mask_scaffold_exact = all(
        snapshot["present"]
        and snapshot["domain"] == "POINT"
        and snapshot["data_type"] == "FLOAT"
        and snapshot["value_count"] == source_snapshot["vertex_count"]
        and snapshot["fractional_value_count"] == 0
        for snapshot in mask_snapshots.values()
    )
    all_masks_empty = all(
        snapshot["nonzero_vertex_count"] == 0 for snapshot in mask_snapshots.values()
    )

    attestation = validate_attestation(
        args.attestation,
        workspace_id=workspace_id,
        source_sha256=source_sha256,
        snapshots=mask_snapshots,
    )
    attested = bool(attestation.get("valid"))
    protected_name = "r7_mask_protected_head_existing_mouth"
    authorable_name = "r7_mask_authorable_body_below_protected_boundary"
    protected_indices = set(mask_snapshots[protected_name]["indices"])
    authorable_indices = set(mask_snapshots[authorable_name]["indices"])
    full_domain = set(range(source_snapshot["vertex_count"]))
    protection_partition = {
        "protected_nonempty": bool(protected_indices),
        "authorable_nonempty": bool(authorable_indices),
        "disjoint": protected_indices.isdisjoint(authorable_indices),
        "complete_vertex_domain_partition": (
            protected_indices | authorable_indices == full_domain
        ),
    }
    partition_valid = all(protection_partition.values())

    local_names = (
        "r7_mask_mammary_areola_left",
        "r7_mask_mammary_areola_right",
        "r7_mask_external_genital_surface",
    )
    local_sets = {name: set(mask_snapshots[name]["indices"]) for name in local_names}
    pairwise_disjoint = all(
        local_sets[first].isdisjoint(local_sets[second])
        for index, first in enumerate(local_names)
        for second in local_names[index + 1 :]
    )
    local_masks = {
        "all_nonempty": all(bool(indices) for indices in local_sets.values()),
        "pairwise_disjoint": pairwise_disjoint,
        "all_within_authorable_body": all(
            indices.issubset(authorable_indices) for indices in local_sets.values()
        ),
        "none_overlap_protected_head_or_existing_mouth": all(
            indices.isdisjoint(protected_indices) for indices in local_sets.values()
        ),
        "uv_raster_masks_created": False,
        "seam_and_bleed_test_passed": False,
        "owner_reviewed_region_swatches_bound": False,
    }

    geometry_authoring_allowed = (
        prepared_exact
        and mask_scaffold_exact
        and attested
        and partition_valid
        and attestation["mask_results"][protected_name]["meaning_confirmed"]
        and attestation["mask_results"][authorable_name]["meaning_confirmed"]
    )
    localized_coloration_allowed = False
    current_workspace = Path(bpy.data.filepath).resolve()
    workspace_recorded_source = str(bpy.context.scene.get("source_sha256", ""))
    no_candidate_exports = not any(current_workspace.parent.glob("*.glb"))

    next_operation = {
        "operation_id": "manual_reviewed_protected_boundary_selection",
        "automatic_selection_allowed": False,
        "instructions": [
            "Open the isolated Blender workspace and keep the exact geometry unchanged.",
            "Visually/topologically select the complete Kira head, every existing single-mouth/lip vertex, and the neck transition that must not move.",
            "Assign that reviewed selection to r7_mask_protected_head_existing_mouth.",
            "Assign the exact remaining vertex-domain complement to r7_mask_authorable_body_below_protected_boundary.",
            "Run this audit, copy the reported selection counts and index hashes into the attestation template, and obtain human review before setting reviewed=true.",
        ],
        "why_manual": "The exact R6 mesh has no authored semantic region map. Coordinates, UV guesses, bone weights, or another character's mesh cannot prove the head/mouth boundary.",
        "geometry_authoring_after_operation": "Only after the exact selection hashes are attested and this audit reports geometry_authoring_allowed=true.",
        "localized_coloration_after_operation": "Still blocked until each adult localized-color region is independently selected, attested, rasterized to UV space, and passes seam/bleed plus swatch review.",
    }

    audit = {
        "schema_version": 1,
        "audit_mode": "non_rendering_blender_workspace_structure_and_semantic_mask_gate",
        "workspace_id": workspace_id,
        "workspace_path": str(current_workspace),
        "source_sha256": source_sha256,
        "workspace_integrity": {
            "scene_workspace_id_matches": bpy.context.scene.get("workspace_id") == workspace_id,
            "scene_source_sha256_matches": workspace_recorded_source == source_sha256,
            "prepared_baseline_exact": prepared_exact,
            "working_body_preservation": preservation,
            "protected_full_surface_baseline": protected_geometry,
            "source_bone_count": current["rig"]["bone_count"],
            "maximum_positive_skin_influences": current["weights"]["maximum_positive_influences"],
            "existing_head_and_single_mouth_preserved_by_exact_whole_surface": (
                preservation["mixed_surface_positions"]
                and preservation["face_index_topology"]
                and preservation["shape_keys"]
            ),
            "second_mouth_created": False,
        },
        "semantic_mask_infrastructure": {
            "registry_path": str(registry_path),
            "scaffold_structure_valid": mask_scaffold_exact,
            "automated_body_region_selection_used": False,
            "all_masks_empty": all_masks_empty,
            "masks": public_mask_snapshots,
            "protection_partition": protection_partition,
            "localized_color_masks": local_masks,
            "attestation": attestation,
        },
        "output_safety": {
            "candidate_glb_present_in_workspace_directory": not no_candidate_exports,
            "runtime_binding_changed": False,
            "avatar_builder_binding_changed": False,
            "home_world_changed": False,
        },
        "gates": {
            "geometry_authoring_allowed": geometry_authoring_allowed,
            "localized_coloration_allowed": localized_coloration_allowed,
            "complete_adult_anatomy_proven": False,
            "stable_working_rig_proven": False,
            "owner_approved": False,
            "candidate_export_allowed": False,
            "runtime_activation_allowed": False,
            "autobuild_allowed": False,
        },
        "next_required_operation": next_operation,
        "truth_note": "This proves exact workspace preparation and gate behavior only. It does not identify anatomy, create an R7 body, prove deformation, approve coloration, or authorize activation.",
    }
    output_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output_path),
                "prepared_baseline_exact": prepared_exact,
                "mask_scaffold_structure_valid": mask_scaffold_exact,
                "all_masks_empty": all_masks_empty,
                "geometry_authoring_allowed": geometry_authoring_allowed,
                "localized_coloration_allowed": localized_coloration_allowed,
                "runtime_activation_allowed": False,
            },
            indent=2,
        )
    )
    if not prepared_exact or not mask_scaffold_exact:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
