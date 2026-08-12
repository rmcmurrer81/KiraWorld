"""Corrected world-space/high-resolution continuation of R24 Attempt 02.

The earlier cross-boundary fairing used object-local step limits on a body
whose object transform converts metres to much larger local coordinates.  It
therefore moved the surface far less than documented.  This no-save simulation
performs the same bounded method entirely in world metres, applies clinical
relief only after shape-preserving subdivision, and masks the incompatible
legacy texture/normal island with a feathered torso-derived surface response.
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
from tools import blender_simulate_kira_r24_cross_boundary_fairing as fair  # noqa: E402
from tools import blender_simulate_kira_r24_attempt02_uv_repair as uvfix  # noqa: E402
from tools import blender_simulate_kira_r24_attempt02_surface_shading_repair as shading  # noqa: E402


SOURCE = base.SOURCE
SOURCE_SHA256 = base.SOURCE_SHA256
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_inplace_surface_simulation/attempt_02_worldspace_highres"
)
EXTERIOR_FACE_RINGS = 8
FAIRING_ITERATIONS = 92
MAXIMUM_WORLD_STEP_M = 0.0011
MAXIMUM_WORLD_MOVEMENT_M = 0.022


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expanded_faces_from_patch(mesh: bpy.types.Mesh, patch_faces: set[int], rings: int):
    _vertex_neighbors, edge_faces, face_neighbors, _vertex_faces = fair.mesh_adjacency(mesh)
    distance = {int(face): 0 for face in patch_faces}
    queue = deque(sorted(patch_faces))
    while queue:
        current = queue.popleft()
        if distance[current] >= rings:
            continue
        for neighbor in face_neighbors[current]:
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    return set(distance), distance, edge_faces


def worldspace_fair(body: bpy.types.Object, patch_faces: set[int]) -> dict[str, object]:
    mesh = body.data
    vertex_neighbors, _edge_faces_all, _face_neighbors, _vertex_faces = fair.mesh_adjacency(mesh)
    region_faces, face_distance, edge_faces = expanded_faces_from_patch(
        mesh, patch_faces, EXTERIOR_FACE_RINGS
    )
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
    distances = fair.boundary_distance(vertex_neighbors, region_vertices, boundary)
    originals = {
        index: body.matrix_world @ mesh.vertices[index].co for index in region_vertices
    }
    inverse = body.matrix_world.inverted()
    normal_matrix = body.matrix_world.to_3x3()
    movable = sorted(region_vertices - boundary)
    maximum_step = 0.0
    for _iteration in range(FAIRING_ITERATIONS):
        mesh.update()
        world = {
            index: body.matrix_world @ mesh.vertices[index].co for index in region_vertices
        }
        updates: dict[int, Vector] = {}
        for index in movable:
            neighbors = [item for item in vertex_neighbors[index] if item in world]
            if not neighbors:
                continue
            current = world[index]
            average = sum((world[item] for item in neighbors), Vector()) / len(neighbors)
            delta = average - current
            normal = (normal_matrix @ mesh.vertices[index].normal).normalized()
            normal_delta = normal * delta.dot(normal)
            tangent_delta = delta - normal_delta
            fade = base.smoothstep(min(1.0, distances.get(index, 0) / 5.0))
            step = fade * (0.42 * normal_delta + 0.035 * tangent_delta)
            if step.length > MAXIMUM_WORLD_STEP_M:
                step.normalize()
                step *= MAXIMUM_WORLD_STEP_M
            proposed = current + step
            total = proposed - originals[index]
            if total.length > MAXIMUM_WORLD_MOVEMENT_M:
                total.normalize()
                proposed = originals[index] + total * MAXIMUM_WORLD_MOVEMENT_M
            updates[index] = proposed
            maximum_step = max(maximum_step, step.length)
        for index, coordinate in updates.items():
            mesh.vertices[index].co = inverse @ coordinate
    mesh.update()
    movements = [
        ((body.matrix_world @ mesh.vertices[index].co) - originals[index]).length
        for index in region_vertices
    ]
    return {
        "space": "world_metres",
        "iterations": FAIRING_ITERATIONS,
        "old_patch_faces": len(patch_faces),
        "expanded_region_faces": len(region_faces),
        "expanded_region_vertices": len(region_vertices),
        "fixed_outer_boundary_vertices": len(boundary),
        "movable_vertices": len(movable),
        "maximum_iteration_step_m": maximum_step,
        "maximum_final_world_movement_m": max(movements, default=0.0),
        "configured_maximum_world_movement_m": MAXIMUM_WORLD_MOVEMENT_M,
        "face_ring_counts": {
            str(ring): sum(value == ring for value in face_distance.values())
            for ring in range(EXTERIOR_FACE_RINGS + 1)
        },
    }


def high_resolution_relief(u: float, v: float) -> float:
    value = 0.0
    value += 0.0018 * base.gaussian(u, v, 0.00, 0.55, 0.60, 0.34)  # mons
    value += 0.0060 * base.gaussian(u, v, -0.31, -0.02, 0.17, 0.45)  # left majus
    value += 0.0056 * base.gaussian(u, v, 0.32, -0.025, 0.18, 0.44)  # right majus
    value += 0.0030 * base.gaussian(u, v, -0.105, 0.015, 0.052, 0.31)  # left minus
    value += 0.0027 * base.gaussian(u, v, 0.112, 0.005, 0.055, 0.30)  # right minus
    value -= 0.0020 * base.gaussian(u, v, 0.00, 0.01, 0.125, 0.29)  # vestibule
    value += 0.0020 * base.gaussian(u, v, 0.00, 0.36, 0.16, 0.10)  # hood
    value += 0.0009 * base.gaussian(u, v, -0.006, 0.285, 0.052, 0.045)  # glans
    value += 0.00055 * base.elliptical_ring(u, v, 0.00, 0.14, 0.034, 0.042, 0.24)
    value -= 0.00095 * base.gaussian(u, v, 0.00, 0.14, 0.023, 0.028)  # meatus
    value += 0.00105 * base.elliptical_ring(u, v, 0.00, -0.10, 0.082, 0.122, 0.20)
    value -= 0.0028 * base.gaussian(u, v, 0.00, -0.10, 0.060, 0.090)  # introitus
    value += 0.00075 * base.gaussian(u, v, 0.00, -0.36, 0.115, 0.065)  # fourchette
    value += 0.00040 * base.gaussian(u, v, 0.00, -0.49, 0.22, 0.18)  # perineum
    value += 0.00070 * base.elliptical_ring(u, v, 0.00, -0.64, 0.080, 0.070, 0.23)
    value -= 0.00160 * base.gaussian(u, v, 0.00, -0.64, 0.052, 0.046)  # anal recess
    return max(-0.0032, min(0.0068, value))


def apply_high_resolution_relief(
    body: bpy.types.Object, patch_faces: set[int]
) -> dict[str, object]:
    mesh = body.data
    region_faces, _distance, _edge_faces = expanded_faces_from_patch(mesh, patch_faces, 24)
    region_vertices = {
        int(vertex) for face in region_faces for vertex in mesh.polygons[face].vertices
    }
    inverse = body.matrix_world.inverted()
    movements = {}
    for index in sorted(region_vertices):
        world = body.matrix_world @ mesh.vertices[index].co
        u, v, _w = base.local_chart(world)
        window = fair.feature_window(u, v)
        if window <= 0.0:
            continue
        displacement = high_resolution_relief(u, v) * window
        mesh.vertices[index].co = inverse @ (world + base.OUTWARD * displacement)
        movements[index] = displacement
    for face in patch_faces:
        mesh.polygons[face].material_index = 0
        mesh.polygons[face].use_smooth = True
    mesh.update()
    return {
        "region_faces": len(region_faces),
        "region_vertices": len(region_vertices),
        "moved_vertices": len(movements),
        "maximum_positive_relief_m": max(movements.values(), default=0.0),
        "minimum_negative_relief_m": min(movements.values(), default=0.0),
        "relief_applied_after_shape_preserving_subdivision": True,
        "clinically_ordered_external_landmark_formula": True,
    }


def mask_normal_and_roughness(body: bpy.types.Object) -> dict[str, object]:
    material = body.material_slots[0].material
    if material is None or material.node_tree is None:
        raise RuntimeError("torso material tree absent")
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    attribute = nodes.get("R24_BoundedSurfaceColorAttribute")
    bsdf = nodes.get("Principled BSDF")
    normal_map = nodes.get("Normal Map")
    roughness = nodes.get("KIRA_R19_ATTEMPT05_BOUNDED_SKIN_ROUGHNESS")
    if attribute is None or bsdf is None or normal_map is None or roughness is None:
        raise RuntimeError("exact R19 shading chain or bounded attribute is absent")
    for link in list(links):
        if link.to_node == bsdf and link.to_socket.name in {"Normal", "Roughness"}:
            links.remove(link)
    one_minus = nodes.new("ShaderNodeMath")
    one_minus.name = "R24_SurfaceMaskOneMinus"
    one_minus.operation = "SUBTRACT"
    one_minus.inputs[0].default_value = 1.0
    links.new(attribute.outputs["Alpha"], one_minus.inputs[1])
    geometry = nodes.new("ShaderNodeNewGeometry")
    geometry.name = "R24_SurfaceGeometricNormal"
    texture_scale = nodes.new("ShaderNodeVectorMath")
    texture_scale.name = "R24_TextureNormalOutsideScale"
    texture_scale.operation = "SCALE"
    links.new(normal_map.outputs["Normal"], texture_scale.inputs[0])
    links.new(one_minus.outputs["Value"], texture_scale.inputs[3])
    geometry_scale = nodes.new("ShaderNodeVectorMath")
    geometry_scale.name = "R24_GeometricNormalInsideScale"
    geometry_scale.operation = "SCALE"
    links.new(geometry.outputs["Normal"], geometry_scale.inputs[0])
    links.new(attribute.outputs["Alpha"], geometry_scale.inputs[3])
    normal_add = nodes.new("ShaderNodeVectorMath")
    normal_add.name = "R24_BoundedNormalBlend"
    normal_add.operation = "ADD"
    links.new(texture_scale.outputs["Vector"], normal_add.inputs[0])
    links.new(geometry_scale.outputs["Vector"], normal_add.inputs[1])
    links.new(normal_add.outputs["Vector"], bsdf.inputs["Normal"])
    rough_outside = nodes.new("ShaderNodeMath")
    rough_outside.name = "R24_TextureRoughnessOutsideScale"
    rough_outside.operation = "MULTIPLY"
    links.new(roughness.outputs["Value"], rough_outside.inputs[0])
    links.new(one_minus.outputs["Value"], rough_outside.inputs[1])
    rough_inside = nodes.new("ShaderNodeMath")
    rough_inside.name = "R24_ClinicalSurfaceRoughnessInsideScale"
    rough_inside.operation = "MULTIPLY"
    rough_inside.inputs[0].default_value = 0.52
    links.new(attribute.outputs["Alpha"], rough_inside.inputs[1])
    rough_add = nodes.new("ShaderNodeMath")
    rough_add.name = "R24_BoundedRoughnessBlend"
    rough_add.operation = "ADD"
    links.new(rough_outside.outputs["Value"], rough_add.inputs[0])
    links.new(rough_inside.outputs["Value"], rough_add.inputs[1])
    links.new(rough_add.outputs["Value"], bsdf.inputs["Roughness"])
    return {
        "normal_texture_retained_outside_mask": True,
        "geometric_normal_used_inside_mask": True,
        "roughness_texture_retained_outside_mask": True,
        "bounded_inside_roughness": 0.52,
    }


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only world-space output exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(base.BODY_NAME)
    rig = bpy.data.objects.get(base.RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or rig absent")
    base.clear_pose(rig)
    original_patch_faces = {
        int(face.index)
        for face in body.data.polygons
        if int(face.material_index) == base.PATCH_MATERIAL_INDEX
    }
    raw_skin, texture_sampling = shading.exact_boundary_texture_mean(
        body, original_patch_faces
    )
    fairing = worldspace_fair(body, original_patch_faces)
    subdivision = base.apply_simple_subdivision(body)
    highres_patch_faces = {
        int(face.index)
        for face in body.data.polygons
        if int(face.material_index) == base.PATCH_MATERIAL_INDEX
    }
    relief = apply_high_resolution_relief(body, highres_patch_faces)
    uv_repair = uvfix.repair_patch_uv(body, highres_patch_faces)
    surface_shading = shading.install_feathered_surface_shading(
        body, highres_patch_faces, raw_skin, 24
    )
    normal_roughness = mask_normal_and_roughness(body)
    body["r24_patch_uses_torso"] = True
    modifier = body.modifiers.new("R24_Attempt02WorldSpace_RenderContinuity", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = 1
    modifier.render_levels = 1
    directory = OUTPUT / "worldspace_highres_integrated_surface"
    directory.mkdir()
    rendered = base.render_variant(body, directory)
    report = {
        "schema": "kira.avatar.r24_attempt02_worldspace_highres_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SAVE_VISUAL_SIMULATION_REQUIRES_REVIEW_AND_POSE_GATES",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256(SOURCE) == SOURCE_SHA256,
        "same_cross_boundary_method_as_attempt_02": True,
        "corrected_defect": "object-local quantities mislabeled as metres",
        "texture_sampling": texture_sampling,
        "worldspace_fairing": fairing,
        "shape_preserving_subdivision": subdivision,
        "high_resolution_relief": relief,
        "uv_repair": uv_repair,
        "surface_shading": surface_shading,
        "normal_and_roughness_mask": normal_roughness,
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
