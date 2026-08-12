"""Attempt 02: no-save cross-boundary R19 pelvic surface fairing simulation.

Unlike Attempt 01, this does not preserve the rejected triangular interface as
a positional constraint.  It fairs the old insert and a broad surrounding
skin neighborhood together, then applies low-amplitude clinical landmarks to
that one continuous surface.  The exact R19 source is opened read-only and no
Blend is saved.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_broad_inplace_surface as base  # noqa: E402


SOURCE = base.SOURCE
SOURCE_SHA256 = base.SOURCE_SHA256
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_inplace_surface_simulation/attempt_02"
)

VARIANTS = (
    {
        "id": "a_cross_boundary_normal_fairing",
        "exterior_face_rings": 8,
        "iterations": 100,
        "normal_factor": 0.36,
        "tangent_factor": 0.025,
        "maximum_total_movement_m": 0.024,
        "relief_scale": 1.0,
        "catmull_render_levels": 1,
    },
    {
        "id": "b_cross_boundary_stronger_fairing",
        "exterior_face_rings": 10,
        "iterations": 145,
        "normal_factor": 0.40,
        "tangent_factor": 0.04,
        "maximum_total_movement_m": 0.028,
        "relief_scale": 1.18,
        "catmull_render_levels": 1,
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mesh_adjacency(mesh: bpy.types.Mesh):
    vertex_neighbors = [set() for _ in mesh.vertices]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    face_neighbors = [set() for _ in mesh.polygons]
    vertex_faces = [set() for _ in mesh.vertices]
    for polygon in mesh.polygons:
        face = int(polygon.index)
        vertices = list(map(int, polygon.vertices))
        for vertex in vertices:
            vertex_faces[vertex].add(face)
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            vertex_neighbors[first].add(second)
            vertex_neighbors[second].add(first)
            edge_faces[tuple(sorted((first, second)))].append(face)
    for faces in edge_faces.values():
        for first in faces:
            face_neighbors[first].update(second for second in faces if second != first)
    return vertex_neighbors, edge_faces, face_neighbors, vertex_faces


def expanded_patch_faces(mesh: bpy.types.Mesh, face_neighbors, rings: int):
    patch = {
        int(face.index)
        for face in mesh.polygons
        if int(face.material_index) == base.PATCH_MATERIAL_INDEX
    }
    distances = {face: 0 for face in patch}
    queue = deque(sorted(patch))
    while queue:
        current = queue.popleft()
        if distances[current] >= rings:
            continue
        for neighbor in face_neighbors[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return patch, set(distances), distances


def boundary_distance(vertex_neighbors, region_vertices: set[int], boundary: set[int]):
    distances = {vertex: 0 for vertex in boundary}
    queue = deque(sorted(boundary))
    while queue:
        current = queue.popleft()
        for neighbor in vertex_neighbors[current]:
            if neighbor not in region_vertices or neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)
    return distances


def feature_window(u: float, v: float) -> float:
    lateral = base.smoothstep((1.02 - abs(u)) / 0.24)
    longitudinal = base.smoothstep((0.94 - abs(v + 0.01)) / 0.22)
    return lateral * longitudinal


def fair_and_shape(body: bpy.types.Object, variant: dict[str, object]) -> dict[str, object]:
    mesh = body.data
    vertex_neighbors, edge_faces, face_neighbors, _vertex_faces = mesh_adjacency(mesh)
    patch_faces, region_faces, face_distances = expanded_patch_faces(
        mesh, face_neighbors, int(variant["exterior_face_rings"])
    )
    patch_vertices = {
        int(vertex) for face in patch_faces for vertex in mesh.polygons[face].vertices
    }
    region_vertices = {
        int(vertex) for face in region_faces for vertex in mesh.polygons[face].vertices
    }
    boundary = {
        vertex
        for edge, faces in edge_faces.items()
        if any(face in region_faces for face in faces)
        and (len(faces) == 1 or any(face not in region_faces for face in faces))
        for vertex in edge
    }
    distances = boundary_distance(vertex_neighbors, region_vertices, boundary)
    originals = {index: mesh.vertices[index].co.copy() for index in region_vertices}
    movable = sorted(region_vertices - boundary)
    peak_iteration_step = 0.0
    maximum_total = float(variant["maximum_total_movement_m"])
    for _iteration in range(int(variant["iterations"])):
        mesh.update()
        updates: dict[int, Vector] = {}
        for index in movable:
            neighbors = vertex_neighbors[index]
            if not neighbors:
                continue
            current = mesh.vertices[index].co.copy()
            average = sum((mesh.vertices[item].co for item in neighbors), Vector()) / len(neighbors)
            delta = average - current
            normal = mesh.vertices[index].normal.normalized()
            normal_delta = normal * delta.dot(normal)
            tangent_delta = delta - normal_delta
            fade = base.smoothstep(min(1.0, distances.get(index, 0) / 5.0))
            step = fade * (
                float(variant["normal_factor"]) * normal_delta
                + float(variant["tangent_factor"]) * tangent_delta
            )
            if step.length > 0.0012:
                step.normalize()
                step *= 0.0012
            proposed = current + step
            total = proposed - originals[index]
            if total.length > maximum_total:
                total.normalize()
                proposed = originals[index] + total * maximum_total
            updates[index] = proposed
            peak_iteration_step = max(peak_iteration_step, step.length)
        for index, coordinate in updates.items():
            mesh.vertices[index].co = coordinate

    mesh.update()
    inverse = body.matrix_world.inverted()
    feature_movements: dict[int, float] = {}
    for index in sorted(region_vertices):
        world = body.matrix_world @ mesh.vertices[index].co
        u, v, _w = base.local_chart(world)
        window = feature_window(u, v)
        if window <= 0.0:
            continue
        displacement = base.relief(u, v, float(variant["relief_scale"])) * window
        world += base.OUTWARD * displacement
        mesh.vertices[index].co = inverse @ world
        feature_movements[index] = displacement
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        if int(polygon.index) in patch_faces:
            polygon.material_index = 0
    mesh.update()

    original_max = max(
        ((mesh.vertices[index].co - originals[index]).length for index in region_vertices),
        default=0.0,
    )
    ring_counts = {
        str(ring): sum(distance == ring for distance in face_distances.values())
        for ring in range(int(variant["exterior_face_rings"]) + 1)
    }
    return {
        "old_patch_faces": len(patch_faces),
        "old_patch_vertices": len(patch_vertices),
        "expanded_region_faces": len(region_faces),
        "expanded_region_vertices": len(region_vertices),
        "fixed_outer_boundary_vertices": len(boundary),
        "movable_vertices": len(movable),
        "face_ring_counts": ring_counts,
        "iterations": int(variant["iterations"]),
        "maximum_iteration_step_m": peak_iteration_step,
        "maximum_final_region_control_movement_m": original_max,
        "maximum_positive_feature_relief_m": max(feature_movements.values(), default=0.0),
        "minimum_negative_feature_relief_m": min(feature_movements.values(), default=0.0),
        "old_patch_material_replaced_with_exact_torso_slot": True,
        "separate_objects_added": 0,
        "topology_changed_by_fairing": False,
    }


def run_variant(variant: dict[str, object]) -> dict[str, object]:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(base.BODY_NAME)
    rig = bpy.data.objects.get(base.RIG_NAME)
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact R19 body or rig is absent")
    base.clear_pose(rig)
    shaping = fair_and_shape(body, variant)
    subdivision = base.apply_simple_subdivision(body)
    body["r24_patch_uses_torso"] = True
    modifier = body.modifiers.new("R24_Attempt02_RenderContinuity", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = int(variant["catmull_render_levels"])
    modifier.render_levels = int(variant["catmull_render_levels"])
    variant_dir = OUTPUT / str(variant["id"])
    variant_dir.mkdir()
    rendered = base.render_variant(body, variant_dir)
    return {
        "variant": variant,
        "shaping": shaping,
        "subdivision": subdivision,
        "rendered": rendered,
        "blend_saved": False,
    }


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only attempt_02 already exists")
    OUTPUT.mkdir(parents=True)
    results = [run_variant(dict(variant)) for variant in VARIANTS]
    report = {
        "schema": "kira.avatar.r24_cross_boundary_fairing_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SAVE_VISUAL_SIMULATION_REQUIRES_REVIEW_AND_POSE_GATES",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256(SOURCE) == SOURCE_SHA256,
        "attempt_01_rejected_reason": (
            "preserving the inherited 34-vertex triangular boundary retained a visible recess"
        ),
        "method_family": "cross_boundary_normal_fairing_on_existing_connected_r19_surface",
        "results": results,
        "operations": {
            "blend_saved": False,
            "runtime_or_person_state_changed": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External visual/deformation simulation only; no internal route, physiology, "
            "elimination, reproduction, pregnancy, sensation, or owner approval is claimed."
        ),
    }
    (OUTPUT / "SIMULATION_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
