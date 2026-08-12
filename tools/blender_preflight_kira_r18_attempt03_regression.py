"""Read-only Blender 5.1 regression gate before Kira R18 attempt 03.

The two earlier append-only execution folders stopped before authoring because
of Blender API compatibility errors.  This harness exhaustively exercises the
prepared worker's frozen-source, mask, immutable-digest, intersection and
qualified-foundation read paths.  It never saves a Blend or changes live Kira.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.blender_author_kira_r18_bounded_bald_candidate as worker


REPORT = (
    ROOT
    / "RecoverySprint/continuation_20260802/"
    "kira_r18_bounded_bald_authoring/PRE_ATTEMPT_03_REGRESSION.json"
)


def immutable_state(body, armature):
    return {
        "coordinate_sha256": worker._coordinate_digest(body),  # noqa: SLF001
        "topology_sha256": worker._topology_digest(body),  # noqa: SLF001
        "deform_weight_sha256": worker._weight_digest(body),  # noqa: SLF001
        "attribute_sha256": worker._attribute_digest(body),  # noqa: SLF001
        "material_index_sha256": worker._material_index_digest(body),  # noqa: SLF001
        "armature_sha256": worker.masks._armature_digest(armature),  # noqa: SLF001
        "actions_sha256": worker._action_digest(),  # noqa: SLF001
        "protected_object_geometry": worker._protected_object_geometry(),  # noqa: SLF001
    }


def main() -> None:
    if REPORT.exists():
        raise RuntimeError(f"append-only regression report already exists: {REPORT}")
    source = (ROOT / worker.R17_BLEND_RELATIVE).resolve(strict=True)
    foundation = (ROOT / worker.FOUNDATION_RELATIVE).resolve(strict=True)
    source_validation = worker.validate_sources(ROOT)
    if worker.sha256_file(source) != worker.R17_BLEND_SHA256:
        raise RuntimeError("exact R17 Blend hash drifted")
    if worker.sha256_file(ROOT / worker.PLAN_RELATIVE) != worker.PLAN_SHA256:
        raise RuntimeError("exact R18 authoring plan hash drifted")
    if worker.sha256_file(foundation) != worker.FOUNDATION_SHA256:
        raise RuntimeError("qualified foundation hash drifted")

    source_hash_before = worker.sha256_file(source)
    package_rows_before, package_digest_before = worker.package_inventory(source.parent)
    live_before = worker.capture_live_kira_state_hashes(ROOT)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    if str(scene.get("candidate_id") or "") != worker.R17_CANDIDATE_ID:
        raise RuntimeError("in-Blend R17 candidate identity drifted")
    body = next(
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and bool(obj.get("primary_surface"))
    )
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    worker.reset_pose_v1(armature)
    worker.r17._remove_private_pose_props()  # noqa: SLF001

    adjacency = worker._adjacency(body)  # noqa: SLF001
    exact_masks = worker._derive_masks(body)  # noqa: SLF001
    f1, f2, _target_sets, _prepared_source = worker._target_sets(body)  # noqa: SLF001
    if f1 != exact_masks["F1"] or f2 != exact_masks["F2"]:
        raise RuntimeError("face target/mask reconstruction mismatch")
    boundary_distances = worker._boundary_distance(  # noqa: SLF001
        exact_masks["P1"], set(worker.P1_BOUNDARY), adjacency
    )
    inherited_pairs = worker._rest_intersections(body)  # noqa: SLF001
    if len(inherited_pairs) != 16:
        raise RuntimeError(f"expected 16 inherited rest intersections, got {len(inherited_pairs)}")

    immutable_before = immutable_state(body, armature)
    action_names_before = sorted(action.name for action in bpy.data.actions)
    foundation_object, temporary_objects = worker._append_foundation_objects(  # noqa: SLF001
        foundation
    )
    try:
        _tree, group_trees, dominant_groups, foundation_report = (
            worker._foundation_reference_bvhs(foundation_object, body)  # noqa: SLF001
        )
        foundation_report = {
            **foundation_report,
            "group_tree_count": len(group_trees),
            "body_dominant_group_vertex_count": len(dominant_groups),
        }
    finally:
        worker._remove_foundation_objects(temporary_objects)  # noqa: SLF001

    immutable_after_foundation_round_trip = immutable_state(body, armature)
    if immutable_after_foundation_round_trip != immutable_before:
        raise RuntimeError("qualified-foundation read round trip changed immutable state")
    action_names_after = sorted(action.name for action in bpy.data.actions)
    if action_names_after != action_names_before:
        raise RuntimeError("qualified-foundation round trip left action datablocks behind")

    source_hash_after = worker.sha256_file(source)
    package_rows_after, package_digest_after = worker.package_inventory(source.parent)
    live_after = worker.capture_live_kira_state_hashes(ROOT)
    if not (source_hash_before == source_hash_after == worker.R17_BLEND_SHA256):
        raise RuntimeError("R17 Blend changed during read-only regression")
    if not (
        package_digest_before
        == package_digest_after
        == worker.R17_PACKAGE_INVENTORY_SHA256
    ):
        raise RuntimeError("R17 package changed during read-only regression")
    if live_after != live_before:
        raise RuntimeError("live Kira state changed during read-only regression")

    report = {
        "schema_version": 1,
        "artifact_type": "kira_r18_pre_attempt_03_blender_51_read_only_regression",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS_READ_ONLY_NO_MESH_MUTATION_NO_BLEND_SAVE",
        "attempt_classification": {
            "attempt_01": "MECHANICAL_PRE_AUTHORING_FAILURE_NO_MESH_MUTATION_OR_RENDER",
            "attempt_02": "MECHANICAL_PRE_AUTHORING_FAILURE_NO_MESH_MUTATION_OR_RENDER",
            "attempt_03": "AUTHORIZED_FIRST_BOUNDED_VISIBLE_SURFACE_ATTEMPT_AFTER_THIS_GATE",
        },
        "source_validation": source_validation,
        "r17_blend_sha256_before": source_hash_before,
        "r17_blend_sha256_after": source_hash_after,
        "r17_package_file_count_before": len(package_rows_before),
        "r17_package_file_count_after": len(package_rows_after),
        "r17_package_inventory_sha256_before": package_digest_before,
        "r17_package_inventory_sha256_after": package_digest_after,
        "live_state_before": live_before,
        "live_state_after": live_after,
        "immutable_digests": immutable_before,
        "authorized_masks": {
            name: {
                "vertex_count": len(indices),
                "index_set_sha256": worker.index_set_sha256(indices),
            }
            for name, indices in sorted(exact_masks.items())
        },
        "p1_boundary_vertex_count": len(worker.P1_BOUNDARY),
        "p1_boundary_sha256": worker.index_set_sha256(worker.P1_BOUNDARY),
        "p1_boundary_distance_coverage": len(boundary_distances),
        "inherited_intersection_count": len(inherited_pairs),
        "inherited_intersection_pairs": [list(pair) for pair in sorted(inherited_pairs)],
        "qualified_foundation_read_test": foundation_report,
        "action_names": action_names_before,
        "blender_version": bpy.app.version_string,
        "blend_saved": False,
        "mesh_mutated": False,
        "runtime_or_selection_changed": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(worker._json_safe(report), stream, indent=2, sort_keys=True)  # noqa: SLF001
        stream.write("\n")
    print(
        "KIRA_R18_PRE_ATTEMPT_03_REGRESSION="
        + json.dumps(
            {
                "status": report["status"],
                "report": REPORT.relative_to(ROOT).as_posix(),
                "sha256": worker.sha256_file(REPORT),
                "intersection_count": len(inherited_pairs),
                "mask_count": len(exact_masks),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
