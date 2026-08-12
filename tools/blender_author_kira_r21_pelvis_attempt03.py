#!/usr/bin/env python3
"""Attempt 03 bootstrap: exact R19 transform for the verified R21 patch."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r21_pelvis_attempt01 as base  # noqa: E402


base.OUTPUT_DIR = ROOT / (
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_03"
)
base.EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_03"
)
base.OUTPUT_BLEND = (
    base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT03.blend"
)


def append_patch_attempt03() -> bpy.types.Object:
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(base.PATCH_BLEND), link=False) as (source, target):
        if base.PATCH_OBJECT_NAME not in source.objects:
            raise RuntimeError("reconstructed source patch object is absent")
        target.objects = [base.PATCH_OBJECT_NAME]
    appended = [obj for obj in bpy.data.objects if obj not in before]
    adult = next(
        (
            obj
            for obj in appended
            if obj.type == "MESH"
            and obj.name == base.PATCH_OBJECT_NAME
            and obj.data.name.startswith("Ariel_Mesh_Genitalia_0")
        ),
        None,
    )
    body = bpy.data.objects.get(base.BODY_NAME)
    if adult is None or body is None:
        raise RuntimeError("verified patch or exact R19 body is absent after append")
    adult.parent = None
    adult.matrix_parent_inverse.identity()
    adult.matrix_world = body.matrix_world.copy()
    for modifier in list(adult.modifiers):
        adult.modifiers.remove(modifier)
    for obj in appended:
        if obj is adult:
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
    if adult.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(adult)
    bpy.context.view_layer.update()
    return adult


base.append_patch = append_patch_attempt03


if __name__ == "__main__":
    raise SystemExit(base.main())
