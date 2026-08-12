"""Narrow UV completion of R24 cross-boundary fairing Attempt 02.

The geometry method is unchanged.  This repairs the measured 34-vertex UV
split between the inherited insert and surrounding torso by solving a harmonic
UV field from the exact torso-side boundary values.  It is a no-save visual
simulation and preserves all earlier evidence.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_broad_inplace_surface as base  # noqa: E402
from tools import blender_simulate_kira_r24_cross_boundary_fairing as fair  # noqa: E402


SOURCE = base.SOURCE
SOURCE_SHA256 = base.SOURCE_SHA256
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_inplace_surface_simulation/attempt_02_uv_repair"
)
VARIANT = dict(fair.VARIANTS[0])
VARIANT["id"] = "a_cross_boundary_normal_fairing_harmonic_uv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def average(values: list[Vector]) -> Vector:
    return sum(values, Vector((0.0, 0.0))) / len(values)


def repair_patch_uv(body: bpy.types.Object, patch_faces: set[int]) -> dict[str, object]:
    mesh = body.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("R19 active UV layer is absent")
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    patch_neighbors: dict[int, set[int]] = defaultdict(set)
    patch_vertices: set[int] = set()
    for face_index in sorted(patch_faces):
        polygon = mesh.polygons[face_index]
        vertices = list(map(int, polygon.vertices))
        patch_vertices.update(vertices)
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            patch_neighbors[first].add(second)
            patch_neighbors[second].add(first)
    for polygon in mesh.polygons:
        vertices = list(map(int, polygon.vertices))
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            edge_faces[tuple(sorted((first, second)))].append(int(polygon.index))
    boundary = {
        vertex
        for edge, faces in edge_faces.items()
        if any(face in patch_faces for face in faces)
        and any(face not in patch_faces for face in faces)
        for vertex in edge
    }
    torso_values: dict[int, list[Vector]] = defaultdict(list)
    patch_values: dict[int, list[Vector]] = defaultdict(list)
    for polygon in mesh.polygons:
        is_patch = int(polygon.index) in patch_faces
        for loop_index in polygon.loop_indices:
            vertex = int(mesh.loops[loop_index].vertex_index)
            if vertex not in patch_vertices:
                continue
            value = uv_layer.data[loop_index].uv.copy()
            (patch_values if is_patch else torso_values)[vertex].append(value)
    missing = sorted(vertex for vertex in boundary if not torso_values[vertex])
    if missing:
        raise RuntimeError(f"torso-side UV authority missing for patch boundary: {missing}")
    pre_deltas = [
        (average(patch_values[vertex]) - average(torso_values[vertex])).length
        for vertex in sorted(boundary)
    ]
    solved: dict[int, Vector] = {
        vertex: average(torso_values[vertex]) for vertex in sorted(boundary)
    }
    boundary_average = average(list(solved.values()))
    for vertex in sorted(patch_vertices - boundary):
        solved[vertex] = boundary_average.copy()
    maximum_iteration_change = 0.0
    iterations = 600
    for _iteration in range(iterations):
        updates: dict[int, Vector] = {}
        for vertex in sorted(patch_vertices - boundary):
            values = [solved[neighbor] for neighbor in patch_neighbors[vertex] if neighbor in solved]
            if values:
                updates[vertex] = average(values)
        if not updates:
            break
        maximum_iteration_change = max(
            maximum_iteration_change,
            max((updates[vertex] - solved[vertex]).length for vertex in updates),
        )
        solved.update(updates)
    for face_index in sorted(patch_faces):
        polygon = mesh.polygons[face_index]
        for loop_index in polygon.loop_indices:
            vertex = int(mesh.loops[loop_index].vertex_index)
            uv_layer.data[loop_index].uv = solved[vertex]
    post_deltas = []
    for vertex in sorted(boundary):
        patch_after = [
            uv_layer.data[loop_index].uv.copy()
            for face_index in patch_faces
            for loop_index in mesh.polygons[face_index].loop_indices
            if int(mesh.loops[loop_index].vertex_index) == vertex
        ]
        post_deltas.append((average(patch_after) - average(torso_values[vertex])).length)
    return {
        "uv_layer": uv_layer.name,
        "patch_faces": len(patch_faces),
        "patch_vertices": len(patch_vertices),
        "boundary_vertices": len(boundary),
        "pre_mean_boundary_uv_delta": sum(pre_deltas) / len(pre_deltas),
        "pre_maximum_boundary_uv_delta": max(pre_deltas),
        "post_mean_boundary_uv_delta": sum(post_deltas) / len(post_deltas),
        "post_maximum_boundary_uv_delta": max(post_deltas),
        "harmonic_iterations": iterations,
        "maximum_iteration_change": maximum_iteration_change,
        "torso_material_or_texture_changed": False,
    }


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only Attempt 02 UV output already exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(base.BODY_NAME)
    rig = bpy.data.objects.get(base.RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or rig is absent")
    base.clear_pose(rig)
    patch_faces = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == base.PATCH_MATERIAL_INDEX
    }
    shaping = fair.fair_and_shape(body, VARIANT)
    uv_repair = repair_patch_uv(body, patch_faces)
    subdivision = base.apply_simple_subdivision(body)
    body["r24_patch_uses_torso"] = True
    modifier = body.modifiers.new("R24_Attempt02UV_RenderContinuity", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = int(VARIANT["catmull_render_levels"])
    modifier.render_levels = int(VARIANT["catmull_render_levels"])
    variant_dir = OUTPUT / str(VARIANT["id"])
    variant_dir.mkdir()
    rendered = base.render_variant(body, variant_dir)
    report = {
        "schema": "kira.avatar.r24_attempt02_harmonic_uv_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SAVE_VISUAL_SIMULATION_REQUIRES_REVIEW_AND_POSE_GATES",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256(SOURCE) == SOURCE_SHA256,
        "same_geometry_repair_as_attempt_02": True,
        "narrow_additional_defect": "34-vertex patch-to-torso UV discontinuity",
        "variant": VARIANT,
        "shaping": shaping,
        "uv_repair": uv_repair,
        "subdivision": subdivision,
        "rendered": rendered,
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
