"""In-memory P1 strength scan after Kira R18 attempt 03 intersections."""

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
    "kira_r18_bounded_bald_authoring/ATTEMPT_04_P1_STRENGTH_SCAN.json"
)


def evaluate(strength: float) -> dict:
    source = (ROOT / worker.R17_BLEND_RELATIVE).resolve(strict=True)
    foundation = (ROOT / worker.FOUNDATION_RELATIVE).resolve(strict=True)
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
    inherited = worker._rest_intersections(body)  # noqa: SLF001
    face_report = worker._apply_face_targets(body, prepared_source, target_sets)  # noqa: SLF001
    after_face = worker._rest_intersections(body)  # noqa: SLF001
    p1_report = worker._apply_p1_reference_transfer(  # noqa: SLF001
        body, masks["P1"], adjacency, foundation, strength, after_face
    )
    after_p1 = worker._rest_intersections(body)  # noqa: SLF001
    return {
        "strength": strength,
        "inherited_count": len(inherited),
        "after_face_count": len(after_face),
        "after_p1_count": len(after_p1),
        "new_after_p1_count": len(after_p1.difference(inherited)),
        "new_after_p1_pairs": [
            list(pair) for pair in sorted(after_p1.difference(inherited))
        ],
        "face_report": face_report,
        "p1_report": p1_report,
    }


def main() -> None:
    if REPORT.exists():
        raise RuntimeError(f"append-only scan already exists: {REPORT}")
    source = (ROOT / worker.R17_BLEND_RELATIVE).resolve(strict=True)
    source_hash_before = worker.sha256_file(source)
    package_rows_before, package_digest_before = worker.package_inventory(source.parent)
    live_before = worker.capture_live_kira_state_hashes(ROOT)
    rows = [evaluate(value) for value in (0.65, 0.75, 0.85, 1.0)]
    source_hash_after = worker.sha256_file(source)
    package_rows_after, package_digest_after = worker.package_inventory(source.parent)
    live_after = worker.capture_live_kira_state_hashes(ROOT)
    if not (source_hash_before == source_hash_after == worker.R17_BLEND_SHA256):
        raise RuntimeError("R17 Blend changed during P1 scan")
    if not (
        package_digest_before
        == package_digest_after
        == worker.R17_PACKAGE_INVENTORY_SHA256
    ):
        raise RuntimeError("R17 package changed during P1 scan")
    if live_after != live_before:
        raise RuntimeError("live Kira state changed during P1 scan")
    report = {
        "schema_version": 1,
        "artifact_type": "kira_r18_attempt_04_p1_strength_scan",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "DIAGNOSTIC_ONLY_NO_BLEND_SAVE_NO_LIVE_CHANGE",
        "results": rows,
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
        "KIRA_R18_P1_STRENGTH_SCAN="
        + json.dumps(
            {
                "report": REPORT.relative_to(ROOT).as_posix(),
                "sha256": worker.sha256_file(REPORT),
                "counts": [
                    [row["strength"], row["after_p1_count"], row["new_after_p1_count"]]
                    for row in rows
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
