"""Full in-memory zero-intersection regression before final R18 attempt 04."""

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
    "kira_r18_bounded_bald_authoring/PRE_ATTEMPT_04_ZERO_INTERSECTION_REGRESSION.json"
)
CANDIDATE_ID = "kira_profiled_adult_candidate_r18_bald_targeted_preflight_attempt04"


def main() -> None:
    if REPORT.exists():
        raise RuntimeError(f"append-only regression report already exists: {REPORT}")
    source = (ROOT / worker.R17_BLEND_RELATIVE).resolve(strict=True)
    foundation = (ROOT / worker.FOUNDATION_RELATIVE).resolve(strict=True)
    source_validation = worker.validate_sources(ROOT)
    source_hash_before = worker.sha256_file(source)
    package_rows_before, package_digest_before = worker.package_inventory(source.parent)
    live_before = worker.capture_live_kira_state_hashes(ROOT)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body = next(
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and bool(obj.get("primary_surface"))
    )
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    worker.reset_pose_v1(armature)
    worker.r17._remove_private_pose_props()  # noqa: SLF001
    adjacency = worker._adjacency(body)  # noqa: SLF001
    masks = worker._derive_masks(body)  # noqa: SLF001
    f1, f2, target_sets, prepared_source = worker._target_sets(body)  # noqa: SLF001
    if f1 != masks["F1"] or f2 != masks["F2"]:
        raise RuntimeError("face target/mask reconstruction mismatch")
    before_coordinates = [vertex.co.copy() for vertex in body.data.vertices]
    immutable_before = {
        "topology_sha256": worker._topology_digest(body),  # noqa: SLF001
        "deform_weight_sha256": worker._weight_digest(body),  # noqa: SLF001
        "attribute_sha256": worker._attribute_digest(body),  # noqa: SLF001
        "material_index_sha256": worker._material_index_digest(body),  # noqa: SLF001
        "armature_sha256": worker.masks._armature_digest(armature),  # noqa: SLF001
        "actions_sha256": worker._action_digest(),  # noqa: SLF001
        "protected_object_geometry": worker._protected_object_geometry(),  # noqa: SLF001
    }
    inherited_pairs = worker._rest_intersections(body)  # noqa: SLF001
    if len(inherited_pairs) != 16:
        raise RuntimeError(f"expected 16 inherited pairs, got {len(inherited_pairs)}")

    face_report = worker._apply_face_targets(body, prepared_source, target_sets)  # noqa: SLF001
    post_face_pairs = worker._rest_intersections(body)  # noqa: SLF001
    if post_face_pairs:
        raise RuntimeError(f"face repair left {len(post_face_pairs)} pairs")
    p1_report = worker._apply_p1_reference_transfer(  # noqa: SLF001
        body, masks["P1"], adjacency, foundation, 1.0, post_face_pairs
    )
    if p1_report["pinned_boundary_exact"] is not True:
        raise RuntimeError("P1 boundary moved")
    if p1_report["collision_safe_backoff"]["final_new_pair_count"] != 0:
        raise RuntimeError("P1 collision backoff did not reach zero")

    component_reports = {}
    specs = (
        ("S_rear_scalp", "S", 2, 0.10, 0.0012),
        ("K_left", "K_L", 1, 0.045, 0.00055),
        ("K_right", "K_R", 1, 0.045, 0.00055),
        ("H_left", "H_L", 1, 0.018, 0.00020),
        ("H_right", "H_R", 1, 0.018, 0.00020),
        ("T_left", "T_L", 1, 0.018, 0.00020),
        ("T_right", "T_R", 1, 0.018, 0.00020),
    )
    for report_name, mask_name, iterations, alpha, maximum in specs:
        component_reports[report_name] = worker._smooth_mask(  # noqa: SLF001
            body,
            masks[mask_name],
            adjacency,
            iterations=iterations,
            alpha=alpha,
            maximum_total_m=maximum,
        )

    brow_report = worker._replace_brows(body, armature, CANDIDATE_ID)  # noqa: SLF001
    nail_report = worker._refine_nail_presentation(CANDIDATE_ID)  # noqa: SLF001
    candidate_objects = worker._retag_candidate(CANDIDATE_ID, body, armature)  # noqa: SLF001
    if len([obj for obj in candidate_objects if bool(obj.get("nail_component"))]) != 20:
        raise RuntimeError("retagged nail inventory drifted")
    _policy, policy_report = worker.r16._validate_delivery_policy()  # noqa: SLF001
    zero_hair = worker.r16._zero_scalp_hair_inventory(  # noqa: SLF001
        body=body, candidate_objects=candidate_objects, policy_report=policy_report
    )
    if zero_hair.get("passed") is not True:
        raise RuntimeError("zero scalp-hair dependency failed")

    changed_indices = {
        index
        for index, before in enumerate(before_coordinates)
        if (body.data.vertices[index].co - before).length > 1.0e-10
    }
    authorized_union = set().union(*(masks[name] for name in masks))
    escaped = changed_indices.difference(authorized_union)
    if escaped:
        raise RuntimeError(f"coordinate changes escaped authorized masks: {len(escaped)}")
    if any(
        (body.data.vertices[index].co - before_coordinates[index]).length > 1.0e-12
        for index in worker.P1_BOUNDARY
    ):
        raise RuntimeError("P1 pinned boundary changed")

    immutable_after = {
        "topology_sha256": worker._topology_digest(body),  # noqa: SLF001
        "deform_weight_sha256": worker._weight_digest(body),  # noqa: SLF001
        "attribute_sha256": worker._attribute_digest(body),  # noqa: SLF001
        "material_index_sha256": worker._material_index_digest(body),  # noqa: SLF001
        "armature_sha256": worker.masks._armature_digest(armature),  # noqa: SLF001
        "actions_sha256": worker._action_digest(),  # noqa: SLF001
        "protected_object_geometry": worker._protected_object_geometry(),  # noqa: SLF001
    }
    if immutable_after != immutable_before:
        differences = [
            name for name in immutable_before if immutable_before[name] != immutable_after[name]
        ]
        raise RuntimeError("immutable digests changed: " + ", ".join(differences))
    final_pairs = worker._rest_intersections(body)  # noqa: SLF001
    if final_pairs:
        raise RuntimeError(f"final rest intersection count is {len(final_pairs)}, not zero")
    topology = worker.r16.r15._mesh_topology_counts(body)  # noqa: SLF001
    if (
        topology["surface_components"] != 1
        or topology["boundary_edges"] != 0
        or topology["nonmanifold_edges"] != 0
    ):
        raise RuntimeError("primary surface is not one closed manifold")

    source_hash_after = worker.sha256_file(source)
    package_rows_after, package_digest_after = worker.package_inventory(source.parent)
    live_after = worker.capture_live_kira_state_hashes(ROOT)
    if not (source_hash_before == source_hash_after == worker.R17_BLEND_SHA256):
        raise RuntimeError("R17 Blend changed during attempt 04 regression")
    if not (
        package_digest_before
        == package_digest_after
        == worker.R17_PACKAGE_INVENTORY_SHA256
    ):
        raise RuntimeError("R17 package changed during attempt 04 regression")
    if live_after != live_before:
        raise RuntimeError("live Kira state changed during attempt 04 regression")

    report = {
        "schema_version": 1,
        "artifact_type": "kira_r18_pre_attempt_04_full_in_memory_regression",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS_ZERO_INTERSECTIONS_ALL_IMMUTABLE_GATES_NO_BLEND_SAVE",
        "attempt_classification": {
            "attempt_01": "MECHANICAL_PRE_AUTHORING_FAILURE",
            "attempt_02": "MECHANICAL_PRE_AUTHORING_FAILURE",
            "attempt_03": "FIRST_BOUNDED_VISIBLE_REPAIR_FAILED_34_NEW_P1_INTERSECTIONS",
            "attempt_04": "AUTHORIZED_SECOND_AND_FINAL_BOUNDED_REPAIR_AFTER_THIS_GATE",
        },
        "source_validation": source_validation,
        "inherited_intersection_count": len(inherited_pairs),
        "post_face_intersection_count": len(post_face_pairs),
        "final_intersection_count": len(final_pairs),
        "p1_report": p1_report,
        "face_report": face_report,
        "component_reports": component_reports,
        "brow_report": brow_report,
        "nail_report": nail_report,
        "changed_vertex_count": len(changed_indices),
        "changed_index_set_sha256": worker.index_set_sha256(changed_indices),
        "escaped_vertex_count": len(escaped),
        "immutable_before": immutable_before,
        "immutable_after": immutable_after,
        "topology": topology,
        "zero_scalp_hair_dependency": zero_hair,
        "r17_blend_sha256_before": source_hash_before,
        "r17_blend_sha256_after": source_hash_after,
        "r17_package_file_count_before": len(package_rows_before),
        "r17_package_file_count_after": len(package_rows_after),
        "r17_package_inventory_sha256_before": package_digest_before,
        "r17_package_inventory_sha256_after": package_digest_after,
        "live_state_before": live_before,
        "live_state_after": live_after,
        "blend_saved": False,
    }
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(worker._json_safe(report), stream, indent=2, sort_keys=True)  # noqa: SLF001
        stream.write("\n")
    print(
        "KIRA_R18_PRE_ATTEMPT_04="
        + json.dumps(
            {
                "status": report["status"],
                "report": REPORT.relative_to(ROOT).as_posix(),
                "sha256": worker.sha256_file(REPORT),
                "final_intersections": len(final_pairs),
                "p1_backoff_vertices": p1_report["collision_safe_backoff"][
                    "backoff_vertex_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
