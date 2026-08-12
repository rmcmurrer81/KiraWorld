"""No-save visual simulation for a broad in-place Kira pelvic repair.

This deliberately avoids every failed graft family used by R19-R23.  It keeps
the existing connected R19 primary surface, adds resolution with a shape-
preserving SIMPLE subdivision, reconstructs the rejected insert against its
own three-dimensional body-frame boundary, and adds bounded analytic external
landmark relief.  The source Blend is never saved or overwritten.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_inplace_surface_simulation/attempt_01"
)
BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
PATCH_MATERIAL_INDEX = 5

ORIGIN = Vector((0.000039145594200817868, -0.056884899735450745, 0.8824364542961121))
LATERAL = Vector((0.9999999403953552, 0.0, 0.0)).normalized()
LONGITUDINAL = Vector((0.0, -0.3000001609325409, 0.9539390802383423)).normalized()
OUTWARD = Vector((0.0, -0.9539390802383423, -0.3000001609325409)).normalized()
HALF_WIDTH = 0.061189649039131856
HALF_LENGTH = 0.1376767103380467

VARIANTS = (
    {
        "id": "a_continuous_original_material",
        "relief_scale": 1.00,
        "replace_patch_material_with_torso": False,
        "catmull_render_levels": 1,
    },
    {
        "id": "b_continuous_torso_material",
        "relief_scale": 1.18,
        "replace_patch_material_with_torso": True,
        "catmull_render_levels": 1,
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def local_chart(world: Vector) -> tuple[float, float, float]:
    delta = world - ORIGIN
    return (
        float(delta.dot(LATERAL) / HALF_WIDTH),
        float(delta.dot(LONGITUDINAL) / HALF_LENGTH),
        float(delta.dot(OUTWARD)),
    )


def gaussian(u: float, v: float, uc: float, vc: float, su: float, sv: float) -> float:
    return math.exp(-0.5 * (((u - uc) / su) ** 2 + ((v - vc) / sv) ** 2))


def elliptical_ring(
    u: float,
    v: float,
    uc: float,
    vc: float,
    su: float,
    sv: float,
    width: float,
) -> float:
    radius = math.sqrt(((u - uc) / su) ** 2 + ((v - vc) / sv) ** 2)
    return math.exp(-0.5 * ((radius - 1.0) / width) ** 2)


def relief(u: float, v: float, scale: float) -> float:
    # All values are metres and remain a shallow external surface treatment.
    value = 0.0
    value += 0.00135 * gaussian(u, v, 0.00, 0.52, 0.55, 0.34)  # mons
    value += 0.00355 * gaussian(u, v, -0.34, -0.01, 0.16, 0.46)  # left majus
    value += 0.00335 * gaussian(u, v, 0.35, -0.02, 0.16, 0.45)  # right majus
    value += 0.00185 * gaussian(u, v, -0.115, 0.015, 0.055, 0.33)  # left minus
    value += 0.00168 * gaussian(u, v, 0.120, 0.005, 0.058, 0.32)  # right minus
    value -= 0.00110 * gaussian(u, v, 0.00, 0.01, 0.115, 0.27)  # vestibule
    value += 0.00125 * gaussian(u, v, 0.00, 0.35, 0.15, 0.105)  # hood
    value += 0.00055 * gaussian(u, v, -0.005, 0.278, 0.050, 0.047)  # glans
    value += 0.00042 * elliptical_ring(u, v, 0.00, 0.137, 0.035, 0.045, 0.25)
    value -= 0.00072 * gaussian(u, v, 0.00, 0.137, 0.024, 0.030)  # urethral meatus
    value += 0.00072 * elliptical_ring(u, v, 0.00, -0.095, 0.075, 0.120, 0.22)
    value -= 0.00155 * gaussian(u, v, 0.00, -0.095, 0.055, 0.088)  # introitus
    value += 0.00048 * gaussian(u, v, 0.00, -0.355, 0.105, 0.072)  # fourchette
    value += 0.00030 * gaussian(u, v, 0.00, -0.475, 0.20, 0.19)  # perineum
    value += 0.00052 * elliptical_ring(u, v, 0.00, -0.620, 0.078, 0.070, 0.24)
    value -= 0.00105 * gaussian(u, v, 0.00, -0.620, 0.052, 0.047)  # anal recess
    return max(-0.0024, min(0.0048, value * float(scale)))


def polynomial_terms(u: float, v: float, degree: int = 4) -> list[float]:
    return [u**i * v**j for total in range(degree + 1) for i in range(total + 1) for j in [total - i]]


def topology(mesh: bpy.types.Mesh) -> tuple[list[set[int]], list[list[int]], set[int], set[int]]:
    adjacency = [set() for _ in mesh.vertices]
    incident = [[] for _ in mesh.vertices]
    patch_faces: set[int] = set()
    nonpatch_faces: set[int] = set()
    for polygon in mesh.polygons:
        face = int(polygon.index)
        is_patch = int(polygon.material_index) == PATCH_MATERIAL_INDEX
        (patch_faces if is_patch else nonpatch_faces).add(face)
        vertices = list(map(int, polygon.vertices))
        for vertex in vertices:
            incident[vertex].append(face)
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            adjacency[first].add(second)
            adjacency[second].add(first)
    return adjacency, incident, patch_faces, nonpatch_faces


def bfs(adjacency: list[set[int]], seeds: set[int], allowed: set[int] | None = None) -> dict[int, int]:
    distances = {int(seed): 0 for seed in seeds}
    queue = deque(sorted(seeds))
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if allowed is not None and neighbor not in allowed:
                continue
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)
    return distances


def apply_simple_subdivision(body: bpy.types.Object) -> dict[str, int]:
    before = {"vertices": len(body.data.vertices), "faces": len(body.data.polygons)}
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    modifier = body.modifiers.new("R24_ShapePreservingResolution", "SUBSURF")
    modifier.subdivision_type = "SIMPLE"
    modifier.levels = 1
    modifier.render_levels = 1
    while body.modifiers.find(modifier.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    body.data.update()
    return {
        **{f"before_{key}": value for key, value in before.items()},
        "after_vertices": len(body.data.vertices),
        "after_faces": len(body.data.polygons),
    }


def fit_and_shape(body: bpy.types.Object, variant: dict[str, object]) -> dict[str, object]:
    mesh = body.data
    adjacency, incident, patch_faces, _nonpatch_faces = topology(mesh)
    patch_vertices = {
        int(vertex)
        for face in patch_faces
        for vertex in mesh.polygons[face].vertices
    }
    seam = {
        vertex
        for vertex in patch_vertices
        if any(face not in patch_faces for face in incident[vertex])
    }
    patch_interior = patch_vertices - seam
    inside_distance = bfs(adjacency, seam, patch_vertices)
    outside_distance = bfs(adjacency, seam)

    sample_indices = [
        index
        for index, distance in outside_distance.items()
        if 1 <= distance <= 18 and index not in patch_interior
    ]
    sample_indices.extend(sorted(seam) * 5)
    rows: list[list[float]] = []
    targets: list[float] = []
    kept_samples: list[int] = []
    for index in sample_indices:
        u, v, w = local_chart(body.matrix_world @ mesh.vertices[index].co)
        if abs(u) > 2.6 or abs(v) > 2.25:
            continue
        rows.append(polynomial_terms(u, v))
        targets.append(w)
        kept_samples.append(index)
    if len(rows) < 80:
        raise RuntimeError(f"insufficient three-dimensional body-frame samples: {len(rows)}")
    matrix = np.asarray(rows, dtype=np.float64)
    target = np.asarray(targets, dtype=np.float64)
    ridge = 2.0e-5
    lhs = np.vstack((matrix, math.sqrt(ridge) * np.eye(matrix.shape[1])))
    rhs = np.concatenate((target, np.zeros(matrix.shape[1], dtype=np.float64)))
    coefficients, *_ = np.linalg.lstsq(lhs, rhs, rcond=None)
    predicted = matrix @ coefficients
    residual = predicted - target

    inverse = body.matrix_world.inverted()
    moved: dict[int, float] = {}
    relief_values: dict[int, float] = {}
    for index in sorted(patch_vertices):
        world = body.matrix_world @ mesh.vertices[index].co
        u, v, current_w = local_chart(world)
        distance = inside_distance.get(index, 0)
        alpha = smoothstep(min(1.0, float(distance) / 5.0))
        if index in seam:
            alpha = 0.0
        baseline_w = float(np.dot(np.asarray(polynomial_terms(u, v)), coefficients))
        feature = relief(u, v, float(variant["relief_scale"])) * alpha
        target_w = baseline_w + feature
        delta = (target_w - current_w) * alpha
        delta = max(-0.018, min(0.018, delta))
        new_world = world + OUTWARD * delta
        mesh.vertices[index].co = inverse @ new_world
        moved[index] = abs(delta)
        relief_values[index] = feature
    mesh.update()
    for polygon in mesh.polygons:
        if int(polygon.index) in patch_faces:
            polygon.use_smooth = True
            if bool(variant["replace_patch_material_with_torso"]):
                polygon.material_index = 0

    return {
        "patch_face_count": len(patch_faces),
        "patch_vertex_count": len(patch_vertices),
        "seam_vertex_count": len(seam),
        "fit_sample_record_count": len(rows),
        "fit_unique_vertex_count": len(set(kept_samples)),
        "fit_basis_count": int(matrix.shape[1]),
        "fit_rms_m": float(np.sqrt(np.mean(residual**2))),
        "fit_maximum_absolute_residual_m": float(np.max(np.abs(residual))),
        "maximum_control_vertex_movement_m": max(moved.values(), default=0.0),
        "maximum_positive_relief_m": max(relief_values.values(), default=0.0),
        "minimum_negative_relief_m": min(relief_values.values(), default=0.0),
        "seam_vertices_moved": sum(moved.get(index, 0.0) > 1.0e-12 for index in seam),
        "method": "shape_preserving_subdivision_plus_body_frame_polynomial_and_bounded_analytic_relief",
    }


def clear_pose(rig: bpy.types.Object) -> None:
    if rig.animation_data:
        rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.36
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.08
    return result


def render_variant(body: bpy.types.Object, variant_dir: Path) -> list[str]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.011, 0.018)
    scene.view_settings.look = "AgX - Medium High Contrast"
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    patch_vertices = {
        int(vertex)
        for polygon in body.data.polygons
        if int(polygon.material_index) in ({0} if body.get("r24_patch_uses_torso") else {5})
        for vertex in polygon.vertices
        if abs(local_chart(body.matrix_world @ body.data.vertices[int(vertex)].co)[0]) < 1.4
        and abs(local_chart(body.matrix_world @ body.data.vertices[int(vertex)].co)[1]) < 1.25
    }
    pelvis = (
        sum((body.matrix_world @ body.data.vertices[index].co for index in patch_vertices), Vector())
        / max(1, len(patch_vertices))
    )
    for name, location, energy, size in (
        ("R24_Key", (2.2, -3.2, 2.8), 900.0, 4.0),
        ("R24_Fill", (-2.4, -2.2, 1.7), 520.0, 3.2),
        ("R24_Rear", (1.0, 2.8, 2.5), 700.0, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        look_at(light, pelvis)
    camera_data = bpy.data.cameras.new("R24DiagnosticCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R24DiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    views = {
        "full_front.png": (Vector((center.x, minimum.y - 3.0, center.z)), center, height * 1.08),
        "pelvis_front.png": (Vector((pelvis.x, pelvis.y - 1.6, pelvis.z)), pelvis, 0.32),
        "pelvis_left_three_quarter.png": (Vector((pelvis.x - 0.85, pelvis.y - 1.25, pelvis.z)), pelvis, 0.32),
        "pelvis_side.png": (Vector((pelvis.x - 1.6, pelvis.y, pelvis.z)), pelvis, 0.32),
        "pelvis_rear.png": (Vector((pelvis.x, pelvis.y + 1.6, pelvis.z)), pelvis, 0.32),
        "pelvis_inferior_front.png": (Vector((pelvis.x, pelvis.y - 0.72, pelvis.z - 0.72)), pelvis, 0.29),
    }
    rendered: list[str] = []
    for filename, (location, target, scale) in views.items():
        camera.location = location
        camera.data.ortho_scale = scale
        look_at(camera, target)
        scene.render.filepath = str(variant_dir / filename)
        bpy.ops.render.render(write_still=True)
        rendered.append(filename)

    wire = body.copy()
    wire.data = body.data.copy()
    wire.name = "R24DiagnosticWire"
    bpy.context.collection.objects.link(wire)
    wire.data.materials.clear()
    wire.data.materials.append(material("R24WireCyan", (0.0, 0.42, 0.58, 1.0)))
    for polygon in wire.data.polygons:
        polygon.material_index = 0
    for modifier in list(wire.modifiers):
        wire.modifiers.remove(modifier)
    wireframe = wire.modifiers.new("R24Wireframe", "WIREFRAME")
    wireframe.thickness = 0.00045
    wireframe.offset = 1.0
    wireframe.use_replace = True
    camera.location = Vector((pelvis.x, pelvis.y - 1.6, pelvis.z))
    camera.data.ortho_scale = 0.32
    look_at(camera, pelvis)
    scene.render.filepath = str(variant_dir / "pelvis_front_wire.png")
    bpy.ops.render.render(write_still=True)
    rendered.append("pelvis_front_wire.png")
    bpy.data.objects.remove(wire, do_unlink=True)
    return rendered


def run_variant(variant: dict[str, object]) -> dict[str, object]:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact R19 body or rig is absent")
    clear_pose(rig)
    before_nonbody = sorted(obj.name for obj in bpy.data.objects if obj != body)
    subdivision = apply_simple_subdivision(body)
    shaping = fit_and_shape(body, variant)
    body["r24_patch_uses_torso"] = bool(variant["replace_patch_material_with_torso"])
    modifier = body.modifiers.new("R24_RenderSurfaceContinuity", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = int(variant["catmull_render_levels"])
    modifier.render_levels = int(variant["catmull_render_levels"])
    modifier.show_only_control_edges = False
    variant_dir = OUTPUT / str(variant["id"])
    variant_dir.mkdir()
    rendered = render_variant(body, variant_dir)
    after_nonbody = sorted(obj.name for obj in bpy.data.objects if obj != body and obj.name != "R24DiagnosticWire")
    return {
        "variant": variant,
        "subdivision": subdivision,
        "shaping": shaping,
        "rendered": rendered,
        "body_control_vertices": len(body.data.vertices),
        "body_control_faces": len(body.data.polygons),
        "nonbody_inventory_preserved_before_diagnostic_lights": set(before_nonbody).issubset(set(after_nonbody)),
        "blend_saved": False,
    }


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only simulation output already exists")
    OUTPUT.mkdir(parents=True)
    results = [run_variant(dict(variant)) for variant in VARIANTS]
    report = {
        "schema": "kira.avatar.r24_broad_inplace_surface_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SAVE_VISUAL_SIMULATION_REQUIRES_REVIEW_AND_STRUCTURAL_POSE_GATES",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256(SOURCE) == SOURCE_SHA256,
        "method_family": "broad_inplace_continuous_surface_no_graft_no_collar_no_donor",
        "disqualified_methods_not_used": [
            "fixed_two_ring_Hermite_graft",
            "concentric_harmonic_carrier_annulus",
            "source_or_donor_patch_copy",
            "Boolean_union",
            "separate_anatomy_objects",
        ],
        "results": results,
        "operations": {
            "blend_saved": False,
            "runtime_or_person_state_changed": False,
            "activation_assignment_export_publication": False,
        },
        "truth": "External visual simulation only; no internal route, physiology, elimination, reproduction, pregnancy, sensation, or owner approval is claimed.",
    }
    (OUTPUT / "SIMULATION_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
