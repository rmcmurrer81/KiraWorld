"""Localize the new rest intersections from Kira R18 attempt 03 in memory."""

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
    "kira_r18_bounded_bald_authoring/ATTEMPT_03_INTERSECTION_DIAGNOSIS.json"
)


def main() -> None:
    if REPORT.exists():
        raise RuntimeError(f"append-only diagnosis already exists: {REPORT}")
    source = (ROOT / worker.R17_BLEND_RELATIVE).resolve(strict=True)
    foundation = (ROOT / worker.FOUNDATION_RELATIVE).resolve(strict=True)
    source_hash_before = worker.sha256_file(source)
    package_rows_before, package_digest_before = worker.package_inventory(source.parent)
    live_before = worker.capture_live_kira_state_hashes(ROOT)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
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
    _f1, _f2, target_sets, prepared_source = worker._target_sets(body)  # noqa: SLF001

    stages = []
    baseline = worker._rest_intersections(body)  # noqa: SLF001

    def snapshot(name: str, operation_report=None):
        pairs = worker._rest_intersections(body)  # noqa: SLF001
        stages.append(
            {
                "stage": name,
                "pair_count": len(pairs),
                "new_vs_r17_count": len(pairs.difference(baseline)),
                "removed_from_r17_count": len(baseline.difference(pairs)),
                "pairs": [list(pair) for pair in sorted(pairs)],
                "operation_report": operation_report,
            }
        )
        return pairs

    snapshot("R17_INHERITED")
    face_report = worker._apply_face_targets(body, prepared_source, target_sets)  # noqa: SLF001
    post_face_pairs = snapshot("AFTER_F1_F2_FACE_TARGETS", face_report)
    p1_report = worker._apply_p1_reference_transfer(  # noqa: SLF001
        body, masks["P1"], adjacency, foundation, 1.0, post_face_pairs
    )
    snapshot("AFTER_P1_STRENGTH_1_0", p1_report)

    smooth_specs = (
        ("S", 2, 0.10, 0.0012),
        ("K_L", 1, 0.045, 0.00055),
        ("K_R", 1, 0.045, 0.00055),
        ("H_L", 1, 0.018, 0.00020),
        ("H_R", 1, 0.018, 0.00020),
        ("T_L", 1, 0.018, 0.00020),
        ("T_R", 1, 0.018, 0.00020),
    )
    for name, iterations, alpha, maximum in smooth_specs:
        operation = worker._smooth_mask(  # noqa: SLF001
            body,
            masks[name],
            adjacency,
            iterations=iterations,
            alpha=alpha,
            maximum_total_m=maximum,
        )
        snapshot(f"AFTER_{name}_FAIRING", operation)

    final_pairs = worker._rest_intersections(body)  # noqa: SLF001
    new_pairs = sorted(final_pairs.difference(baseline))
    mask_names_by_vertex = {
        index: [name for name, values in masks.items() if index in values]
        for pair in new_pairs
        for face_index in pair
        for index in body.data.polygons[face_index].vertices
    }
    localized = []
    for left, right in new_pairs:
        left_face = body.data.polygons[left]
        right_face = body.data.polygons[right]
        left_vertices = [int(value) for value in left_face.vertices]
        right_vertices = [int(value) for value in right_face.vertices]
        localized.append(
            {
                "pair": [left, right],
                "left_vertices": left_vertices,
                "right_vertices": right_vertices,
                "left_mask_membership": {
                    str(index): mask_names_by_vertex[index] for index in left_vertices
                },
                "right_mask_membership": {
                    str(index): mask_names_by_vertex[index] for index in right_vertices
                },
                "left_center": [float(value) for value in left_face.center],
                "right_center": [float(value) for value in right_face.center],
            }
        )

    source_hash_after = worker.sha256_file(source)
    package_rows_after, package_digest_after = worker.package_inventory(source.parent)
    live_after = worker.capture_live_kira_state_hashes(ROOT)
    if not (source_hash_before == source_hash_after == worker.R17_BLEND_SHA256):
        raise RuntimeError("R17 Blend changed during in-memory diagnosis")
    if not (
        package_digest_before
        == package_digest_after
        == worker.R17_PACKAGE_INVENTORY_SHA256
    ):
        raise RuntimeError("R17 package changed during in-memory diagnosis")
    if live_after != live_before:
        raise RuntimeError("live Kira state changed during in-memory diagnosis")

    report = {
        "schema_version": 1,
        "artifact_type": "kira_r18_attempt_03_intersection_localization",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "DIAGNOSIS_ONLY_NO_BLEND_SAVE_NO_LIVE_CHANGE",
        "attempt_03_failure": "34_NEW_REST_NONADJACENT_INTERSECTIONS",
        "stages": stages,
        "new_pair_localization": localized,
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
        "KIRA_R18_ATTEMPT_03_INTERSECTION_DIAGNOSIS="
        + json.dumps(
            {
                "report": REPORT.relative_to(ROOT).as_posix(),
                "sha256": worker.sha256_file(REPORT),
                "stage_counts": [
                    [row["stage"], row["pair_count"], row["new_vs_r17_count"]]
                    for row in stages
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
