#!/usr/bin/env python3
"""Attempt 04 bootstrap: Blender-5.1-compatible seam weld accounting."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r21_pelvis_attempt03 as previous  # noqa: E402


base = previous.base
base.OUTPUT_DIR = ROOT / (
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_04"
)
base.EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_04"
)
base.OUTPUT_BLEND = (
    base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT04.blend"
)


def join_and_weld_attempt04(
    body: bpy.types.Object,
    adult: bpy.types.Object,
    rig: bpy.types.Object,
) -> dict[str, Any]:
    approved_material = body.data.materials[base.PATCH_SLOT]
    adult.data.materials.clear()
    adult.data.materials.append(approved_material)
    for polygon in adult.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    before_join = len(body.data.vertices) + len(adult.data.vertices)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    adult.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    before_weld = len(body.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.remove_doubles(
        bm,
        verts=list(bm.verts),
        dist=base.WELD_TOLERANCE_LOCAL,
    )
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    after_weld = len(body.data.vertices)
    for polygon in body.data.polygons:
        if int(polygon.material_index) == base.PATCH_SLOT:
            polygon.use_smooth = True
    modifier = next((item for item in body.modifiers if item.type == "ARMATURE"), None)
    if modifier is None:
        modifier = body.modifiers.new("KIRA_R21_NATIVE_188_RIG", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    return {
        "joined_vertex_count_before_weld": before_join,
        "bmesh_vertex_count_before_weld": before_weld,
        "final_vertex_count": after_weld,
        "expected_boundary_merge_count": 34,
        "actual_vertex_reduction": before_weld - after_weld,
        "weld_result_source": "direct before/after BMesh vertex counts",
        "weld_tolerance_body_local": base.WELD_TOLERANCE_LOCAL,
    }


base.join_and_weld = join_and_weld_attempt04


if __name__ == "__main__":
    raise SystemExit(base.main())
