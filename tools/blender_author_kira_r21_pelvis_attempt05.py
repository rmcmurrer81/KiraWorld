#!/usr/bin/env python3
"""Attempt 05: patch-side seam-collar tangent continuity repair."""

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
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_05"
)
base.EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_05"
)
base.OUTPUT_BLEND = (
    base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT05.blend"
)


def relax_patch_side_collar(body: bpy.types.Object) -> dict[str, Any]:
    mesh = body.data
    patch_faces = {
        int(polygon.index)
        for polygon in mesh.polygons
        if int(polygon.material_index) == base.PATCH_SLOT
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    vertex_neighbors: dict[int, set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, first in enumerate(vertices):
            second = vertices[(index + 1) % len(vertices)]
            edge = tuple(sorted((first, second)))
            edge_faces[edge].append(int(polygon.index))
            vertex_neighbors[first].add(second)
            vertex_neighbors[second].add(first)
    interface_edges = {
        edge
        for edge, faces in edge_faces.items()
        if len(faces) == 2 and sum(face in patch_faces for face in faces) == 1
    }
    seam = {vertex for edge in interface_edges for vertex in edge}
    patch_vertices = {
        int(vertex)
        for face in patch_faces
        for vertex in mesh.polygons[face].vertices
    }
    first_collar = {
        neighbor
        for vertex in seam
        for neighbor in vertex_neighbors[vertex]
        if neighbor in patch_vertices and neighbor not in seam
    }
    original = {index: mesh.vertices[index].co.copy() for index in first_collar}
    iterations = 4
    strength = 0.92
    for _iteration in range(iterations):
        mesh.update()
        exterior_normals: dict[int, Vector] = {}
        for vertex in seam:
            values = [
                mesh.polygons[face].normal.copy()
                for edge in interface_edges
                if vertex in edge
                for face in edge_faces[edge]
                if face not in patch_faces
            ]
            if not values:
                raise RuntimeError(f"no exterior seam normal for vertex {vertex}")
            normal = sum(values, Vector())
            if normal.length <= 1.0e-12:
                raise RuntimeError(f"exterior seam normal collapsed for vertex {vertex}")
            exterior_normals[vertex] = normal.normalized()
        targets: dict[int, list[Vector]] = defaultdict(list)
        for seam_vertex in seam:
            seam_point = mesh.vertices[seam_vertex].co.copy()
            normal = exterior_normals[seam_vertex]
            for neighbor in vertex_neighbors[seam_vertex]:
                if neighbor not in first_collar:
                    continue
                point = mesh.vertices[neighbor].co.copy()
                displacement = point - seam_point
                tangent_target = point - normal * displacement.dot(normal)
                targets[neighbor].append(tangent_target)
        pending = {}
        for index, values in targets.items():
            target = sum(values, Vector()) / len(values)
            current = mesh.vertices[index].co.copy()
            pending[index] = current.lerp(target, strength)
        for index, value in pending.items():
            mesh.vertices[index].co = value
    mesh.update()
    movements = {
        index: float((mesh.vertices[index].co - original[index]).length)
        for index in first_collar
    }
    seam_delta = 0.0
    return {
        "method": "patch_side_first_collar_projection_to_frozen_exterior_tangent_planes_v1",
        "interface_vertex_count": len(seam),
        "first_collar_vertex_count": len(first_collar),
        "iterations": iterations,
        "strength": strength,
        "maximum_first_collar_movement_body_local": max(movements.values(), default=0.0),
        "maximum_first_collar_movement_world_m": max(movements.values(), default=0.0)
        * abs(float(body.matrix_world.to_scale().x)),
        "seam_vertex_maximum_delta": seam_delta,
        "nonpatch_vertex_movement_allowed": false,
    }


def join_and_weld_attempt05(
    body: bpy.types.Object,
    adult: bpy.types.Object,
    rig: bpy.types.Object,
) -> dict[str, Any]:
    record = previous.join_and_weld_attempt04(body, adult, rig)
    record["seam_collar_tangent_repair"] = relax_patch_side_collar(body)
    return record


base.join_and_weld = join_and_weld_attempt05


if __name__ == "__main__":
    raise SystemExit(base.main())
