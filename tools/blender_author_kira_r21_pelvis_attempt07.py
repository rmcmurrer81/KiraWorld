#!/usr/bin/env python3
"""Attempt 07: edge-plane fit for only seam-adjacent patch vertices."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r21_pelvis_attempt04 as previous  # noqa: E402


base = previous.base
base.OUTPUT_DIR = ROOT / (
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_07"
)
base.EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_07"
)
base.OUTPUT_BLEND = (
    base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT07.blend"
)


def exterior_corner_normal(mesh: bpy.types.Mesh, face_index: int, vertices: set[int]) -> Vector:
    polygon = mesh.polygons[face_index]
    values = []
    for loop_index in range(polygon.loop_start, polygon.loop_start + polygon.loop_total):
        if int(mesh.loops[loop_index].vertex_index) in vertices:
            values.append(Vector(base.r20._corner_normal(mesh, loop_index)))
    if not values:
        values = [polygon.normal.copy()]
    normal = sum(values, Vector())
    if normal.length <= 1.0e-12:
        raise RuntimeError(f"exterior corner normal collapsed for face {face_index}")
    return normal.normalized()


def fit_patch_faces_to_exterior_edge_planes(body: bpy.types.Object) -> dict[str, Any]:
    mesh = body.data
    patch_faces = {
        int(polygon.index)
        for polygon in mesh.polygons
        if int(polygon.material_index) == base.PATCH_SLOT
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, first in enumerate(vertices):
            edge_faces[tuple(sorted((first, vertices[(index + 1) % len(vertices)])))].append(
                int(polygon.index)
            )
    interface = {
        edge: faces
        for edge, faces in edge_faces.items()
        if len(faces) == 2 and sum(face in patch_faces for face in faces) == 1
    }
    seam = {vertex for edge in interface for vertex in edge}
    moved: set[int] = set()
    original: dict[int, Vector] = {}
    passes = 3
    strength = 0.985
    for _pass in range(passes):
        mesh.update()
        targets: dict[int, list[Vector]] = defaultdict(list)
        for edge, faces in interface.items():
            patch_face = next(face for face in faces if face in patch_faces)
            exterior_face = next(face for face in faces if face not in patch_faces)
            first, second = edge
            a = mesh.vertices[first].co.copy()
            b = mesh.vertices[second].co.copy()
            edge_direction = b - a
            if edge_direction.length <= 1.0e-12:
                raise RuntimeError(f"seam edge collapsed: {edge}")
            edge_direction.normalize()
            desired = exterior_corner_normal(mesh, exterior_face, set(edge))
            desired = desired - edge_direction * desired.dot(edge_direction)
            if desired.length <= 1.0e-12:
                raise RuntimeError(f"seam edge normal collapsed: {edge}")
            desired.normalize()
            for vertex in mesh.polygons[patch_face].vertices:
                index = int(vertex)
                if index in seam:
                    continue
                point = mesh.vertices[index].co.copy()
                target = point - desired * (point - a).dot(desired)
                targets[index].append(target)
        for index, values in targets.items():
            if index not in original:
                original[index] = mesh.vertices[index].co.copy()
            target = sum(values, Vector()) / len(values)
            mesh.vertices[index].co = mesh.vertices[index].co.lerp(target, strength)
            moved.add(index)
    mesh.update()
    displacement = [
        float((mesh.vertices[index].co - original[index]).length) for index in moved
    ]
    return {
        "method": "patch_side_seam_adjacent_edge_plane_fit_v1",
        "interface_edge_count": len(interface),
        "interface_vertex_count": len(seam),
        "moved_patch_vertex_count": len(moved),
        "passes": passes,
        "strength": strength,
        "maximum_patch_vertex_movement_body_local": max(displacement, default=0.0),
        "maximum_patch_vertex_movement_world_m": max(displacement, default=0.0)
        * abs(float(body.matrix_world.to_scale().x)),
        "seam_vertices_moved": false,
        "nonpatch_vertices_moved": false,
    }


def join_and_weld_attempt07(
    body: bpy.types.Object,
    adult: bpy.types.Object,
    rig: bpy.types.Object,
) -> dict[str, Any]:
    record = previous.join_and_weld_attempt04(body, adult, rig)
    record["seam_edge_plane_repair"] = fit_patch_faces_to_exterior_edge_planes(body)
    return record


base.join_and_weld = join_and_weld_attempt07
false = False


if __name__ == "__main__":
    raise SystemExit(base.main())
