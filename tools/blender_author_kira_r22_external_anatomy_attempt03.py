#!/usr/bin/env python3
"""Attempt 03: preserve anatomy-module world transforms while rig binding."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r22_external_anatomy_attempt01 as base  # noqa: E402
from blender_author_kira_r22_external_anatomy_attempt02 import ray_surface_y_fixed  # noqa: E402
from blender_author_kira_r22_external_anatomy_runner import run_attempt  # noqa: E402


def bind_to_rig_preserving_world(
    obj: bpy.types.Object,
    body: bpy.types.Object,
    rig: bpy.types.Object,
) -> dict[str, Any]:
    tree = KDTree(len(body.data.vertices))
    for index, vertex in enumerate(body.data.vertices):
        tree.insert(body.matrix_world @ vertex.co, index)
    tree.balance()
    names = {group.index: group.name for group in body.vertex_groups}
    assigned = 0
    groups_used: set[str] = set()
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        _position, source_index, _distance = tree.find(world)
        weights = [
            (names[element.group], float(element.weight))
            for element in body.data.vertices[int(source_index)].groups
            if float(element.weight) > 1.0e-8
        ]
        if not weights:
            continue
        weights = sorted(weights, key=lambda item: (-item[1], item[0]))[:4]
        total = sum(value for _name, value in weights)
        for group_name, value in weights:
            group = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)
            group.add([vertex.index], value / total, "REPLACE")
            groups_used.add(group_name)
        assigned += 1
    modifier = obj.modifiers.new("KIRA_R22_NATIVE_RIG", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    # The armature modifier consumes the weights without a parent transform.
    # Leaving parent unset preserves the exact body-aligned matrix_world.
    obj.parent = None
    obj["private_review_only"] = True
    obj["owner_approved"] = False
    obj["runtime_activation_allowed"] = False
    obj["external_anatomy_surface_only"] = True
    return {
        "vertex_count": len(obj.data.vertices),
        "vertices_with_weights": assigned,
        "groups_used": sorted(groups_used),
        "armature": rig.name,
        "parent": None,
        "world_transform_preserved": True,
    }


base.ray_surface_y = ray_surface_y_fixed
base.bind_to_rig = bind_to_rig_preserving_world


if __name__ == "__main__":
    output_dir = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_03"
    evidence_dir = ROOT / (
        "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_03"
    )
    output_blend = output_dir / "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT03.blend"
    raise SystemExit(run_attempt(
        base,
        root=ROOT,
        attempt_number=3,
        output_dir=output_dir,
        evidence_dir=evidence_dir,
        output_blend=output_blend,
        prior_attempt_truth={
            "attempt_01": "failed before save because ray bound used the wrong coordinate scale",
            "attempt_02": "saved but visually rejected because rig parenting moved the module away from the body",
        },
        repair_summary=(
            "retain nearest-body weights and armature modifier while leaving parent unset so "
            "the exact body-aligned world transform remains unchanged"
        ),
    ))
