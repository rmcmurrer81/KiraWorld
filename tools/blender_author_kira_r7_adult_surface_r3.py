"""Build Kira's sealed, inactive R7 measured-neck R3 review artifact.

The R2 Blend is the immutable parent.  This worker retains the R2 adult
external surface and exact 79-joint cage, cuts a fresh copy of the exact R6
head at the pre-measured 35% neck-to-head plane, and creates one explicit
triangulated bridge between the two measured rings.  It does not export a GLB,
change an Avatar Builder binding, or touch Kira World's runtime state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


LIGHT_SKIN_HEX = "#e6c0a9"
LIGHT_SKIN_RGBA = (230 / 255, 192 / 255, 169 / 255, 1.0)
UNIFIED_OBJECT = "Kira_R7_Measured_Neck_Bridge_R3_Inactive"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vertex_weight_rows(obj: bpy.types.Object) -> list[dict[str, float]]:
    names = {group.index: group.name for group in obj.vertex_groups}
    return [
        {
            names[assignment.group]: float(assignment.weight)
            for assignment in vertex.groups
            if assignment.weight > 1e-8
        }
        for vertex in obj.data.vertices
    ]


def make_world_rest_copy(
    source: bpy.types.Object,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Copy exact R6 rest coordinates and deform weights into world space."""
    world = source.matrix_world.copy()
    points = [world @ vertex.co for vertex in source.data.vertices]
    faces = [tuple(map(int, polygon.vertices)) for polygon in source.data.polygons]
    rows = vertex_weight_rows(source)
    mesh = bpy.data.meshes.new("EXACT_KIRA_R6_HEAD_R3_WORK_MESH")
    mesh.from_pydata([tuple(point) for point in points], [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Exact_Kira_R6_Head_R3_Work", mesh)
    collection.objects.link(obj)
    groups = {
        group.name: obj.vertex_groups.new(name=group.name)
        for group in source.vertex_groups
    }
    for index, row in enumerate(rows):
        for name, weight in row.items():
            groups[name].add([index], weight, "REPLACE")
    obj.matrix_world = Matrix.Identity(4)
    obj["source_role"] = "exact_r6_head_rest_geometry_work_copy"
    return obj


def bisect_keep_above(obj: bpy.types.Object, cut_z: float) -> dict[str, int]:
    before_vertices = len(obj.data.vertices)
    before_polygons = len(obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-7,
        plane_co=Vector((0.0, 0.0, cut_z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=True,
        clear_outer=False,
    )
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "vertices_before": before_vertices,
        "vertices_after": len(obj.data.vertices),
        "polygons_before": before_polygons,
        "polygons_after": len(obj.data.polygons),
    }


def make_sealed_r2_head_copy(
    source: bpy.types.Object,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Copy the exact-R6 head derivative already sealed in the R2 parent.

    The raw pinned R6 mesh contains a mixed shape-key coordinate space.  R2's
    exact head derivative is the measured identity surface used by the R3
    probe, so R3 copies that sealed geometry instead of guessing which raw
    shape-key coordinates represent the current face.
    """
    obj = source.copy()
    obj.data = source.data.copy()
    collection.objects.link(obj)
    obj.name = "Exact_Kira_R6_Head_R3_Work"
    obj.data.name = "EXACT_KIRA_R6_HEAD_R3_WORK_MESH"
    obj.hide_viewport = False
    obj.hide_render = True
    obj.hide_select = False
    obj.matrix_world = source.matrix_world.copy()
    obj["source_role"] = "sealed_r2_exact_r6_head_derivative_work_copy"
    return obj


def assign_temporary_head_neck_weights(
    obj: bpy.types.Object,
    cut_z: float,
) -> dict[str, object]:
    """Give the identity shell a minimal rigid-head/neck transition.

    R2's identity derivative deliberately contains no deform groups.  Only the
    short new neck band is blended; all face and mouth coordinates remain
    untouched.  This is a temporary engineering weighting, not a lip rig.
    """
    obj.vertex_groups.clear()
    neck = obj.vertex_groups.new(name="mixamorig:Neck_05")
    head = obj.vertex_groups.new(name="mixamorig:Head_06")
    transition_top = cut_z + 0.035
    neck_weighted = 0
    rigid_head = 0
    for vertex in obj.data.vertices:
        z = float((obj.matrix_world @ vertex.co).z)
        t = max(0.0, min(1.0, (z - cut_z) / max(1e-9, transition_top - cut_z)))
        # The cut ring begins at 60% neck / 40% head and reaches rigid head
        # weighting over only 35 mm.  No vertex coordinates are changed.
        neck_value = 0.60 * (1.0 - t)
        head_value = 1.0 - neck_value
        if neck_value > 1e-8:
            neck.add([vertex.index], neck_value, "REPLACE")
            neck_weighted += 1
        else:
            rigid_head += 1
        head.add([vertex.index], head_value, "REPLACE")
    return {
        "method": "temporary_35mm_neck_to_rigid_head_blend",
        "cut_ring_neck_weight": 0.60,
        "cut_ring_head_weight": 0.40,
        "transition_height_m": 0.035,
        "neck_blended_vertices": neck_weighted,
        "rigid_head_vertices": rigid_head,
        "face_or_mouth_coordinates_changed": False,
        "claim_limit": "temporary pose-test weights; not a facial or lip rig",
    }


def boundary_cycles(obj: bpy.types.Object) -> list[list[int]]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    for polygon in obj.data.polygons:
        values = list(map(int, polygon.vertices))
        for index, a in enumerate(values):
            b = values[(index + 1) % len(values)]
            edge_use[tuple(sorted((a, b)))] += 1
    graph: defaultdict[int, list[int]] = defaultdict(list)
    for (a, b), count in edge_use.items():
        if count == 1:
            graph[a].append(b)
            graph[b].append(a)
    seen: set[int] = set()
    cycles: list[list[int]] = []
    for start in sorted(graph):
        if start in seen:
            continue
        component: list[int] = []
        todo = deque([start])
        seen.add(start)
        while todo:
            current = todo.popleft()
            component.append(current)
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        if component and all(len(graph[index]) == 2 for index in component):
            cycles.append(component)
    return cycles


def cycle_measure(obj: bpy.types.Object, indices: list[int]) -> dict[str, object]:
    points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
    center = sum(points, Vector()) / len(points)
    radii = [math.hypot(point.x - center.x, point.y - center.y) for point in points]
    return {
        "vertex_count": len(indices),
        "center_m": [round(float(value), 9) for value in center],
        "z_min_m": round(min(point.z for point in points), 9),
        "z_max_m": round(max(point.z for point in points), 9),
        "radial_mean_m": round(sum(radii) / len(radii), 9),
        "radial_min_m": round(min(radii), 9),
        "radial_max_m": round(max(radii), 9),
    }


def ordered_by_angle(obj: bpy.types.Object, indices: list[int]) -> list[int]:
    points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
    center = sum(points, Vector()) / len(points)
    return sorted(
        indices,
        key=lambda index: math.atan2(
            (obj.matrix_world @ obj.data.vertices[index].co).y - center.y,
            (obj.matrix_world @ obj.data.vertices[index].co).x - center.x,
        ),
    )


def rotate_to_nearest(
    reference: list[int],
    moving: list[int],
    body_points: list[Vector],
    head_points: list[Vector],
) -> list[int]:
    anchor = body_points[reference[0]]
    offset = min(
        range(len(moving)),
        key=lambda index: (head_points[moving[index]] - anchor).length_squared,
    )
    return moving[offset:] + moving[:offset]


def zipper_bridge(body: list[int], head: list[int], head_offset: int) -> list[tuple[int, int, int]]:
    """Triangulate two unequal closed rings without adding or moving vertices."""
    n, m = len(body), len(head)
    faces: list[tuple[int, int, int]] = []
    i = j = 0
    while i < n or j < m:
        a0 = body[i % n]
        b0 = head_offset + head[j % m]
        next_a = (i + 1) / n if i < n else math.inf
        next_b = (j + 1) / m if j < m else math.inf
        if abs(next_a - next_b) <= 1e-12:
            a1 = body[(i + 1) % n]
            b1 = head_offset + head[(j + 1) % m]
            faces.append((a0, a1, b0))
            faces.append((a1, b1, b0))
            i += 1
            j += 1
        elif next_a < next_b:
            a1 = body[(i + 1) % n]
            faces.append((a0, a1, b0))
            i += 1
        else:
            b1 = head_offset + head[(j + 1) % m]
            faces.append((a0, b1, b0))
            j += 1
    if len(faces) != n + m:
        raise RuntimeError(f"bridge triangle invariant failed: {len(faces)} != {n + m}")
    return faces


def smooth_pair_band(
    obj: bpy.types.Object,
    first: str,
    second: str,
    z_low: float,
    z_high: float,
    side_sign: int,
) -> dict[str, object]:
    """Apply the single narrow R3 probe repair; never iterate or widen it."""
    groups = {group.name: group for group in obj.vertex_groups}
    a_group = groups[first]
    b_group = groups[second]
    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)

    def pair_value(index: int) -> tuple[float, float, float]:
        values = {
            obj.vertex_groups[assignment.group].name: float(assignment.weight)
            for assignment in obj.data.vertices[index].groups
        }
        a = values.get(first, 0.0)
        b = values.get(second, 0.0)
        total = a + b
        return ((a / total) if total > 1e-8 else 0.0, total, min(a, b))

    eligible = [
        vertex.index
        for vertex in obj.data.vertices
        if z_low <= (obj.matrix_world @ vertex.co).z <= z_high
        and (obj.matrix_world @ vertex.co).x * side_sign >= -1e-6
        and pair_value(vertex.index)[1] > 0.90
        and pair_value(vertex.index)[2] > 1e-5
    ]
    previous = {index: pair_value(index)[:2] for index in eligible}
    updates: dict[int, tuple[float, float]] = {}
    maximum_delta = 0.0
    for index in eligible:
        own, total = previous[index]
        neighbors = [neighbor for neighbor in adjacency[index] if neighbor in previous]
        if not neighbors:
            continue
        mean = sum(previous[neighbor][0] for neighbor in neighbors) / len(neighbors)
        value = own * 0.5 + mean * 0.5
        updates[index] = (value, total)
        maximum_delta = max(maximum_delta, abs(value - own))
    for index, (value, total) in updates.items():
        a_group.add([index], value * total, "REPLACE")
        b_group.add([index], (1.0 - value) * total, "REPLACE")
    return {
        "groups": [first, second],
        "z_band_m": [z_low, z_high],
        "side_sign": side_sign,
        "iterations": 1,
        "strength": 0.5,
        "eligible_vertices": len(eligible),
        "updated_vertices": len(updates),
        "max_normalized_pair_delta": round(maximum_delta, 9),
    }


def coordinate_digest(points: list[Vector]) -> str:
    digest = hashlib.sha256()
    for point in points:
        digest.update(struct.pack("<3d", float(point.x), float(point.y), float(point.z)))
    return digest.hexdigest()


def create_unified_object(
    body: bpy.types.Object,
    head: bpy.types.Object,
    body_ring: list[int],
    head_ring: list[int],
    armature: bpy.types.Object,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, object]]:
    body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    head_points = [head.matrix_world @ vertex.co for vertex in head.data.vertices]
    ordered_body = ordered_by_angle(body, body_ring)
    ordered_head = ordered_by_angle(head, head_ring)
    ordered_head = rotate_to_nearest(ordered_body, ordered_head, body_points, head_points)
    body_faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    offset = len(body_points)
    head_faces = [tuple(offset + int(index) for index in polygon.vertices) for polygon in head.data.polygons]
    bridge_faces = zipper_bridge(ordered_body, ordered_head, offset)
    mesh = bpy.data.meshes.new("KIRA_R7_MEASURED_NECK_BRIDGE_R3_MESH")
    mesh.from_pydata(
        [tuple(point) for point in body_points + head_points],
        [],
        body_faces + head_faces + bridge_faces,
    )
    mesh.update()
    obj = bpy.data.objects.new(UNIFIED_OBJECT, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.color = LIGHT_SKIN_RGBA

    valid_names = [bone.name for bone in armature.data.bones]
    groups = {name: obj.vertex_groups.new(name=name) for name in valid_names}
    body_rows = vertex_weight_rows(body)
    head_rows = vertex_weight_rows(head)
    for index, row in enumerate(body_rows + head_rows):
        positive = [(name, weight) for name, weight in row.items() if name in groups and weight > 1e-8]
        positive.sort(key=lambda item: (-item[1], item[0]))
        positive = positive[:4]
        total = sum(weight for _, weight in positive)
        if total <= 1e-12:
            continue
        for name, weight in positive:
            groups[name].add([index], weight / total, "REPLACE")

    modifier = obj.modifiers.new("EXACT_KIRA_R6_79_JOINT_CAGE", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    obj["inactive_review_only"] = True
    obj["candidate_component"] = False
    obj["skin_tone_srgb_hex"] = LIGHT_SKIN_HEX
    obj["exact_r6_head_vertices_moved"] = False
    obj["bridge_method"] = "measured_35pct_head_cut_plus_unequal_cycle_zipper"
    return obj, {
        "body_vertices": len(body_points),
        "head_vertices": len(head_points),
        "unified_vertices": len(obj.data.vertices),
        "body_ring_vertices": len(body_ring),
        "head_ring_vertices": len(head_ring),
        "bridge_triangles": len(bridge_faces),
        "expected_bridge_triangles": len(body_ring) + len(head_ring),
        "head_vertex_offset": offset,
        "head_coordinate_digest_before": coordinate_digest(head_points),
    }


def topology_record(obj: bpy.types.Object) -> dict[str, object]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    for polygon in obj.data.polygons:
        values = list(map(int, polygon.vertices))
        for index, a in enumerate(values):
            b = values[(index + 1) % len(values)]
            edge_use[tuple(sorted((a, b)))] += 1
    seen: set[int] = set()
    sizes: list[int] = []
    for start in range(len(obj.data.vertices)):
        if start in seen:
            continue
        todo = deque([start])
        seen.add(start)
        size = 0
        while todo:
            current = todo.popleft()
            size += 1
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        sizes.append(size)
    cycles = boundary_cycles(obj)
    areas = [float(polygon.area) for polygon in obj.data.polygons]
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "polygons": len(obj.data.polygons),
        "connected_components": len(sizes),
        "component_sizes": sorted(sizes, reverse=True),
        "boundary_connected_parts": len(cycles),
        "boundary_closed_cycle_count": len(cycles),
        "boundary_cycles": [cycle_measure(obj, cycle) for cycle in cycles],
        "overused_edge_count": sum(count > 2 for count in edge_use.values()),
        "minimum_face_area_m2": round(min(areas, default=0.0), 12),
        "degenerate_face_count_under_1e_12_m2": sum(area <= 1e-12 for area in areas),
    }


def weight_record(obj: bpy.types.Object, valid: set[str]) -> dict[str, object]:
    names = {group.index: group.name for group in obj.vertex_groups}
    sums: list[float] = []
    maximum = 0
    invalid: set[str] = set()
    for vertex in obj.data.vertices:
        positive = [assignment for assignment in vertex.groups if assignment.weight > 1e-8]
        maximum = max(maximum, len(positive))
        sums.append(sum(float(assignment.weight) for assignment in positive))
        invalid.update(names[assignment.group] for assignment in positive if names[assignment.group] not in valid)
    unweighted = sum(total <= 1e-8 for total in sums)
    return {
        "vertex_count": len(obj.data.vertices),
        "weighted_vertex_count": len(obj.data.vertices) - unweighted,
        "unweighted_vertex_count": unweighted,
        "maximum_positive_groups_per_vertex": maximum,
        "invalid_target_groups": sorted(invalid),
        "weight_sum_minimum": round(min(sums, default=0.0), 9),
        "weight_sum_maximum": round(max(sums, default=0.0), 9),
        "defined_vertex_group_count": len(obj.vertex_groups),
    }


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[round((len(ordered) - 1) * fraction)]


def reset_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def apply_pose(armature: bpy.types.Object, name: str) -> dict[str, list[float]]:
    reset_pose(armature)
    values: dict[str, tuple[float, float, float]] = {}
    if name == "upper_limb":
        values = {
            "mixamorig:LeftArm_09": (0.0, math.radians(-25), math.radians(38)),
            "mixamorig:LeftForeArm_010": (0.0, math.radians(68), 0.0),
            "mixamorig:LeftHand_011": (math.radians(10), 0.0, math.radians(-8)),
        }
    elif name == "hip_knee":
        values = {
            "mixamorig:LeftUpLeg_055": (math.radians(42), 0.0, math.radians(8)),
            "mixamorig:LeftLeg_056": (math.radians(-62), 0.0, 0.0),
            "mixamorig:LeftFoot_057": (math.radians(18), 0.0, 0.0),
        }
    elif name == "spine":
        values = {
            "mixamorig:Spine_02": (0.0, math.radians(10), 0.0),
            "mixamorig:Spine1_03": (0.0, math.radians(13), 0.0),
            "mixamorig:Spine2_04": (math.radians(-5), math.radians(9), 0.0),
        }
    elif name == "bilateral_squat":
        values = {
            "mixamorig:LeftUpLeg_055": (math.radians(34), 0.0, math.radians(5)),
            "mixamorig:RightUpLeg_060": (math.radians(34), 0.0, math.radians(-5)),
            "mixamorig:LeftLeg_056": (math.radians(-55), 0.0, 0.0),
            "mixamorig:RightLeg_061": (math.radians(-55), 0.0, 0.0),
            "mixamorig:Spine_02": (math.radians(-12), 0.0, 0.0),
        }
    for bone_name, rotation in values.items():
        armature.pose.bones[bone_name].rotation_euler = rotation
    bpy.context.view_layer.update()
    return {bone: [round(math.degrees(v), 3) for v in rotation] for bone, rotation in values.items()}


def evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def deformation_record(obj: bpy.types.Object, rest: list[Vector]) -> dict[str, object]:
    current = evaluated_vertices(obj)
    ratios: list[float] = []
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        base = (rest[a] - rest[b]).length
        if base > 1e-9:
            ratios.append((current[a] - current[b]).length / base)
    count = max(1, len(ratios))
    return {
        "all_coordinates_finite": all(math.isfinite(value) for point in current for value in point),
        "edge_stretch_ratio": {
            "minimum": round(min(ratios, default=0.0), 9),
            "p05": round(quantile(ratios, 0.05), 9),
            "p95": round(quantile(ratios, 0.95), 9),
            "maximum": round(max(ratios, default=0.0), 9),
            "edges_under_half": sum(value < 0.5 for value in ratios),
            "edges_over_2x": sum(value > 2.0 for value in ratios),
            "fraction_under_half": round(sum(value < 0.5 for value in ratios) / count, 9),
            "fraction_over_2x": round(sum(value > 2.0 for value in ratios) / count, 9),
        },
    }


def bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [float(value) for value in low],
        "high": [float(value) for value in high],
        "size": [float(value) for value in high - low],
    }


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    look_at(camera, target)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    config_path = Path(parse_args().config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if config.get("candidate_glb_export_requested") or config.get("live_binding_change_requested"):
        raise ValueError("R3 worker is review-only; export and binding are forbidden")

    parent_paths = {
        name: Path(value).resolve(strict=True)
        for name, value in config["parent_artifacts"].items()
    }
    actual_parent_hashes = {name: sha256_file(path) for name, path in parent_paths.items()}
    if actual_parent_hashes != config["parent_hashes"]:
        raise ValueError(f"sealed R2 parent mismatch: {actual_parent_hashes}")

    surface = bpy.data.objects.get("Kira_R7_Adult_Surface_Trial")
    if surface is None or surface.type != "MESH":
        raise RuntimeError("R2 adult review surface is missing")
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE" and len(obj.data.bones) == 79]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one exact R6 79-joint cage, found {len(armatures)}")
    armature = armatures[0]
    sealed_head_source = bpy.data.objects.get("Exact_Kira_R6_Head_Reference_Only")
    if sealed_head_source is None or sealed_head_source.type != "MESH":
        raise RuntimeError("sealed R2 exact-R6 head derivative is missing")
    reset_pose(armature)

    review = bpy.data.collections.get("INACTIVE_KIRA_R7_ADULT_SURFACE_REVIEW")
    if review is None:
        review = bpy.data.collections.new("INACTIVE_KIRA_R7_ADULT_SURFACE_REVIEW")
        bpy.context.scene.collection.children.link(review)

    repairs: list[dict[str, object]] = []
    for side, suffix, sign in (("Left", "055", 1), ("Right", "060", -1)):
        leg_suffix = "056" if side == "Left" else "061"
        repairs.append(smooth_pair_band(surface, f"mixamorig:{side}UpLeg_{suffix}", f"mixamorig:{side}Leg_{leg_suffix}", 0.27, 0.38, sign))
        repairs.append(smooth_pair_band(surface, "mixamorig:Hips_01", f"mixamorig:{side}UpLeg_{suffix}", 0.50, 0.60, sign))

    neck = armature.matrix_world @ armature.data.bones["mixamorig:Neck_05"].head_local
    head_bone = armature.matrix_world @ armature.data.bones["mixamorig:Head_06"].head_local
    fraction = float(config["head_cut_fraction_neck_to_head"])
    cut_z = float(neck.z + (head_bone.z - neck.z) * fraction)
    if abs(cut_z - float(config["measured_head_cut_z_m"])) > 1e-8:
        raise RuntimeError(f"measured head cut drifted: {cut_z}")

    head = make_sealed_r2_head_copy(sealed_head_source, review)
    head_cut = bisect_keep_above(head, cut_z)
    head_weighting = assign_temporary_head_neck_weights(head, cut_z)
    body_cycles = boundary_cycles(surface)
    head_cycles = boundary_cycles(head)
    if len(body_cycles) != 1:
        raise RuntimeError(f"expected one R2 body neck boundary, found {len(body_cycles)}")
    body_ring = body_cycles[0]
    head_ring = min(
        head_cycles,
        key=lambda cycle: abs(sum(head.data.vertices[index].co.z for index in cycle) / len(cycle) - cut_z),
    )
    body_measure = cycle_measure(surface, body_ring)
    head_measure = cycle_measure(head, head_ring)
    if len(body_ring) != int(config["expected_body_ring_vertices"]):
        raise RuntimeError(f"body ring count changed: {len(body_ring)}")
    if len(head_ring) != int(config["expected_head_ring_vertices"]):
        raise RuntimeError(
            "head ring count changed: "
            f"{len(head_ring)}; all cycles={json.dumps([cycle_measure(head, cycle) for cycle in head_cycles])}"
        )
    if abs(head_measure["z_min_m"] - cut_z) > 1e-6 or abs(head_measure["z_max_m"] - cut_z) > 1e-6:
        raise RuntimeError("selected head boundary is not the measured neck cut ring")

    material = bpy.data.materials.get("KIRA_PRE_R6_LIGHT_SKIN_UNTEXTURED")
    if material is None:
        material = bpy.data.materials.new("KIRA_PRE_R6_LIGHT_SKIN_UNTEXTURED")
    material.diffuse_color = LIGHT_SKIN_RGBA
    unified, bridge = create_unified_object(surface, head, body_ring, head_ring, armature, review, material)
    surface.hide_render = True
    surface.hide_viewport = True
    head.hide_render = True
    head.hide_viewport = True
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj != unified:
            obj.hide_render = True

    offset = int(bridge["head_vertex_offset"])
    original_head_points = [head.matrix_world @ vertex.co for vertex in head.data.vertices]
    unified_head_points = [unified.matrix_world @ unified.data.vertices[offset + index].co for index in range(len(head.data.vertices))]
    deltas = [(after - before).length for before, after in zip(original_head_points, unified_head_points)]
    identity = {
        "retained_exact_r6_head_vertex_count": len(original_head_points),
        "retained_exact_r6_head_maximum_coordinate_delta_m": max(deltas, default=0.0),
        "head_coordinate_digest_before": bridge["head_coordinate_digest_before"],
        "head_coordinate_digest_after": coordinate_digest(unified_head_points),
        "face_and_mouth_vertices_smoothed_or_moved": False,
        "source_materials_or_textures_copied": False,
        "eye_socket_note": "Exact R6 eye sockets remain open; eye components are a separate inactive task.",
        "mouth_note": "The exact R6 mouth surface is retained; no second mouth was added.",
        "head_weighting": head_weighting,
    }
    identity_pass = (
        identity["retained_exact_r6_head_maximum_coordinate_delta_m"] <= 1e-8
        and identity["head_coordinate_digest_before"] == identity["head_coordinate_digest_after"]
    )

    topology = topology_record(unified)
    weights = weight_record(unified, {bone.name for bone in armature.data.bones})
    neck_boundaries = [
        cycle for cycle in topology["boundary_cycles"]
        if float(body_measure["center_m"][2]) - 0.005 <= float(cycle["center_m"][2]) <= cut_z + 0.005
    ]
    topology_pass = (
        topology["connected_components"] == 1
        and topology["overused_edge_count"] == 0
        and topology["degenerate_face_count_under_1e_12_m2"] == 0
        and len(neck_boundaries) == 0
        and bridge["bridge_triangles"] == bridge["expected_bridge_triangles"]
    )
    weights_pass = (
        weights["unweighted_vertex_count"] == 0
        and weights["maximum_positive_groups_per_vertex"] <= 4
        and not weights["invalid_target_groups"]
        and weights["weight_sum_minimum"] > 0.999
        and weights["weight_sum_maximum"] < 1.001
        and weights["defined_vertex_group_count"] == 79
    )

    rest = evaluated_vertices(unified)
    poses: dict[str, dict[str, object]] = {}
    for pose_name in ("rest", "upper_limb", "hip_knee", "spine", "bilateral_squat"):
        rotations = {} if pose_name == "rest" else apply_pose(armature, pose_name)
        poses[pose_name] = {
            "rotations_degrees_xyz": rotations,
            "metrics": deformation_record(unified, rest),
        }
    reset_pose(armature)
    pose_gate_results = {}
    for name, record in poses.items():
        metric = record["metrics"]
        stretch = metric["edge_stretch_ratio"]
        pose_gate_results[name] = (
            metric["all_coordinates_finite"]
            and stretch["p05"] >= 0.70
            and stretch["p95"] <= 1.30
            and stretch["fraction_under_half"] <= 0.001
            and stretch["fraction_over_2x"] <= 0.001
        )
    deformation_pass = all(pose_gate_results.values())

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    scene.world.color = (0.025, 0.035, 0.05)
    camera_data = bpy.data.cameras.new("R3OwnerReviewCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R3OwnerReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    rest_bounds = bounds(rest)
    low = Vector(rest_bounds["low"])
    high = Vector(rest_bounds["high"])
    center = (low + high) * 0.5
    front_scale = max(rest_bounds["size"][0], rest_bounds["size"][2]) * 1.22
    side_scale = max(rest_bounds["size"][1], rest_bounds["size"][2]) * 1.22
    renders: dict[str, str] = {}
    for name, location, scale in (
        ("neutral_front", Vector((center.x, center.y - 3.0, center.z)), front_scale),
        ("neutral_back", Vector((center.x, center.y + 3.0, center.z)), front_scale),
        ("neutral_left", Vector((center.x + 3.0, center.y, center.z)), side_scale),
        ("neutral_right", Vector((center.x - 3.0, center.y, center.z)), side_scale),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, center, scale)
        renders[name] = path.name

    neck_center = (Vector(body_measure["center_m"]) + Vector(head_measure["center_m"])) * 0.5
    for name, location in (
        ("neck_closeup_front", Vector((neck_center.x, neck_center.y - 3.0, neck_center.z))),
        ("neck_closeup_left", Vector((neck_center.x + 3.0, neck_center.y, neck_center.z))),
        ("neck_closeup_right", Vector((neck_center.x - 3.0, neck_center.y, neck_center.z))),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, neck_center, 0.24)
        renders[name] = path.name

    head_bounds = bounds(original_head_points)
    head_center = (Vector(head_bounds["low"]) + Vector(head_bounds["high"])) * 0.5
    head_scale = max(head_bounds["size"]) * 1.22
    for name, location in (
        ("identity_front", Vector((head_center.x, head_center.y - 3.0, head_center.z))),
        ("identity_left_profile", Vector((head_center.x + 3.0, head_center.y, head_center.z))),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, head_center, head_scale)
        renders[name] = path.name
    non_neck_cycles = [cycle for cycle in head_cycles if cycle is not head_ring]
    mouth_cycle = max(non_neck_cycles, key=len)
    mouth_points = [head.data.vertices[index].co.copy() for index in mouth_cycle]
    mouth_center = sum(mouth_points, Vector()) / len(mouth_points)
    mouth_path = output_dir / "identity_mouth_closeup.png"
    render_view(scene, camera, mouth_path, Vector((mouth_center.x, mouth_center.y - 3.0, mouth_center.z)), mouth_center, 0.115)
    renders["identity_mouth_closeup"] = mouth_path.name

    for pose_name, side in (("upper_limb", False), ("hip_knee", False), ("spine", True), ("bilateral_squat", False)):
        apply_pose(armature, pose_name)
        posed = evaluated_vertices(unified)
        posed_bounds = bounds(posed)
        posed_center = (Vector(posed_bounds["low"]) + Vector(posed_bounds["high"])) * 0.5
        scale = max(posed_bounds["size"][1 if side else 0], posed_bounds["size"][2]) * 1.28
        location = Vector((posed_center.x + 3.0, posed_center.y, posed_center.z)) if side else Vector((posed_center.x, posed_center.y - 3.0, posed_center.z))
        path = output_dir / f"pose_{pose_name}.png"
        render_view(scene, camera, path, location, posed_center, scale)
        renders[f"pose_{pose_name}"] = path.name
    reset_pose(armature)

    engineering_bridge_pass = topology_pass and weights_pass and identity_pass and deformation_pass
    decision = {
        "status": "rejected_complete_adult_topology_and_owner_visual_approval_not_proven_no_candidate",
        "engineering_measured_neck_bridge_passed": engineering_bridge_pass,
        "inactive_review_blend_created": True,
        "candidate_glb_created": False,
        "live_binding_changed": False,
        "runtime_activation_allowed": False,
        "avatar_builder_promotion_allowed": False,
        "why": [
            "R3 is an inactive engineering review of one measured neck bridge, not a candidate or live body.",
            "The exact retained R6 head coordinates are tested separately from the new bridge; no face or mouth smoothing is allowed.",
            "The external adult reference surface does not by itself prove complete adult topology or internal anatomy.",
            "Exact R6 eye sockets remain a separate unapproved component task.",
            "Owner visual approval has not been given for this R3 artifact.",
        ],
    }
    if not engineering_bridge_pass:
        decision["why"].append("At least one measured engineering gate failed, so even the R3 bridge trial is rejected.")

    evidence = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "mode": config["mode"],
        "parent_artifacts": {name: {"path": str(path), "sha256": actual_parent_hashes[name]} for name, path in parent_paths.items()},
        "head_cut": {
            "fraction_neck_to_head": fraction,
            "cut_z_m": cut_z,
            "neck_bone_head_z_m": float(neck.z),
            "head_bone_head_z_m": float(head_bone.z),
            "operation": head_cut,
        },
        "measured_rings": {"body": body_measure, "head": head_measure},
        "bridge": bridge,
        "identity_preservation": identity,
        "narrow_weight_repairs": repairs,
        "topology": topology,
        "weights": weights,
        "deformation": poses,
        "pose_gate_results": pose_gate_results,
        "renders": renders,
        "gates": {
            "single_cohesive_surface_without_neck_boundary": topology_pass,
            "exact_79_joint_weights": weights_pass,
            "exact_r6_head_coordinates_preserved": identity_pass,
            "fixed_pose_deformation": deformation_pass,
            "engineering_measured_neck_bridge_passed": engineering_bridge_pass,
            "complete_adult_topology_proven": False,
            "owner_visual_review_approved": False,
            "candidate_export_allowed": False,
            "live_binding_allowed": False,
        },
        "skin": {"srgb_hex": LIGHT_SKIN_HEX, "material": material.name, "untextured": True},
        "truth_limits": {
            "complete_adult_topology_proven": False,
            "internal_anatomy_proven": False,
            "eyes_completed": False,
            "lip_sync_completed": False,
            "natural_long_duration_motion_proven": False,
        },
        "decision": decision,
    }
    (output_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    scene["inactive_review_only"] = True
    scene["candidate_export_allowed"] = False
    scene["live_binding_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["owner_approved"] = False
    scene["complete_adult_topology_proven"] = False
    scene["identity_head_coordinates_preserved"] = identity_pass
    scene["measured_neck_bridge_engineering_passed"] = engineering_bridge_pass
    readme = bpy.data.texts.get("READ_ME_KIRA_R7_MEASURED_NECK_R3.txt") or bpy.data.texts.new("READ_ME_KIRA_R7_MEASURED_NECK_R3.txt")
    readme.clear()
    readme.write(
        "KIRA R7 MEASURED NECK BRIDGE R3 - INACTIVE OWNER REVIEW ONLY\n\n"
        "This file joins the R2 adult external surface to a fresh exact-R6 head copy with\n"
        "one measured triangulated neck bridge. Exact retained R6 face/mouth coordinates\n"
        "were not smoothed or moved. The original #e6c0a9 untextured skin contract is\n"
        "retained. Eye components and lip sync remain separate unfinished work.\n\n"
        "This is not complete-adult-topology proof, not an exported candidate, not a live\n"
        "binding, and not authorized for activation or promotion.\n"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(config["review_blend"])))
    print(json.dumps({"ok": True, "status": decision["status"], "engineering_bridge_pass": engineering_bridge_pass}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
