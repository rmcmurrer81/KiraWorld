"""Build one private, inactive Kira provisional body R5 candidate.

This Blender worker is deliberately narrow:

* it derives from the exact enrolled 3ec62 adult cage;
* it merges only exact duplicate-position vertices whose skin-weight signatures
  agree, while preserving per-corner UVs;
* it authors a modest reversible body-proportion shape key and a textured skin
  material;
* it keeps the original 79-joint rig and finger chains;
* it renders neutral, reach, stride, and seated deformation evidence; and
* it exports only a body and armature into a caller-supplied private R5 folder.

It never reads or writes Kira's live runtime avatar and it authors no eyes,
hair, clothes, shoes, anatomical attestation, likeness approval, activation,
or autobuild approval.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT_BONE = "_rootJoint"
HIPS = "mixamorig:Hips_01"
SPINE = "mixamorig:Spine_02"
SPINE1 = "mixamorig:Spine1_03"
SPINE2 = "mixamorig:Spine2_04"
NECK = "mixamorig:Neck_05"
HEAD = "mixamorig:Head_06"
LEFT_ARM = "mixamorig:LeftArm_09"
LEFT_FOREARM = "mixamorig:LeftForeArm_010"
LEFT_HAND = "mixamorig:LeftHand_011"
LEFT_SHOULDER = "mixamorig:LeftShoulder_08"
RIGHT_ARM = "mixamorig:RightArm_033"
RIGHT_FOREARM = "mixamorig:RightForeArm_034"
RIGHT_HAND = "mixamorig:RightHand_035"
RIGHT_SHOULDER = "mixamorig:RightShoulder_032"
LEFT_THIGH = "mixamorig:LeftUpLeg_055"
LEFT_SHIN = "mixamorig:LeftLeg_056"
LEFT_FOOT = "mixamorig:LeftFoot_057"
RIGHT_THIGH = "mixamorig:RightUpLeg_060"
RIGHT_SHIN = "mixamorig:RightLeg_061"
RIGHT_FOOT = "mixamorig:RightFoot_062"

REQUIRED_BONES = (
    ROOT_BONE,
    HIPS,
    SPINE,
    SPINE1,
    SPINE2,
    NECK,
    HEAD,
    LEFT_ARM,
    LEFT_FOREARM,
    LEFT_HAND,
    RIGHT_ARM,
    RIGHT_FOREARM,
    RIGHT_HAND,
    LEFT_THIGH,
    LEFT_SHIN,
    LEFT_FOOT,
    RIGHT_THIGH,
    RIGHT_SHIN,
    RIGHT_FOOT,
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def primary_body_and_armature() -> tuple[bpy.types.Object, bpy.types.Object]:
    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and len(obj.data.vertices) > 1000
    ]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes or len(armatures) != 1:
        raise ValueError("expected one enrolled body mesh and exactly one armature")
    return max(meshes, key=lambda obj: len(obj.data.vertices)), armatures[0]


def remove_source_helpers(body: bpy.types.Object) -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.context.scene.objects):
        if obj is body or obj.type != "MESH":
            continue
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def vector_list(value: Vector) -> list[float]:
    return [round(float(component), 7) for component in value]


def mesh_world_points(obj: bpy.types.Object, *, evaluated: bool = False) -> list[Vector]:
    if not evaluated:
        return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    instance = obj.evaluated_get(depsgraph)
    mesh = instance.to_mesh()
    try:
        return [instance.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        instance.to_mesh_clear()


def bounds_for_points(points: list[Vector]) -> tuple[Vector, Vector]:
    if not points:
        raise ValueError("no mesh points available")
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def bounds_for_body(body: bpy.types.Object, *, evaluated: bool = False) -> tuple[Vector, Vector]:
    return bounds_for_points(mesh_world_points(body, evaluated=evaluated))


def foot_contact_metrics(
    body: bpy.types.Object,
    *,
    floor_z: float,
    body_height: float,
) -> dict[str, object]:
    """Measure toe/heel contact independently for both geometric feet.

    The low foot band is split by body center X and then by the front/back
    thirds of each foot's Y extent.  Negative Y is the enrolled body's front.
    This intentionally does not turn one lowest toe vertex into a whole-foot
    contact claim.
    """

    points = mesh_world_points(body, evaluated=True)
    center_x = (min(point.x for point in points) + max(point.x for point in points)) * 0.5
    low_band = floor_z + body_height * 0.115
    tolerance = 0.004
    result: dict[str, object] = {
        "method": "low geometric foot band; side split by X; toe/heel split by Y thirds",
        "floor_z_m": round(float(floor_z), 7),
        "contact_tolerance_m": tolerance,
        "negative_y_is_front": True,
    }
    for side, predicate in (
        ("left", lambda point: point.x > center_x + body_height * 0.004),
        ("right", lambda point: point.x < center_x - body_height * 0.004),
    ):
        foot_points = [point for point in points if predicate(point) and point.z <= low_band]
        if not foot_points:
            result[side] = {"present": False}
            continue
        y_low = min(point.y for point in foot_points)
        y_high = max(point.y for point in foot_points)
        y_span = max(y_high - y_low, 1e-9)
        toe_points = [point for point in foot_points if point.y <= y_low + y_span * 0.34]
        heel_points = [point for point in foot_points if point.y >= y_high - y_span * 0.34]
        toe_gap = min(point.z for point in toe_points) - floor_z
        heel_gap = min(point.z for point in heel_points) - floor_z
        contact_points = [point for point in foot_points if abs(point.z - floor_z) <= tolerance]
        contact_y_span = (
            max(point.y for point in contact_points) - min(point.y for point in contact_points)
            if len(contact_points) >= 2
            else 0.0
        )
        result[side] = {
            "present": True,
            "sample_count": len(foot_points),
            "toe_sample_count": len(toe_points),
            "heel_sample_count": len(heel_points),
            "toe_minimum_gap_m": round(float(toe_gap), 7),
            "heel_minimum_gap_m": round(float(heel_gap), 7),
            "minimum_gap_m": round(float(min(point.z for point in foot_points) - floor_z), 7),
            "contact_vertex_count_within_4mm": len(contact_points),
            "contact_y_span_m": round(float(contact_y_span), 7),
            "full_sole_contact_sanity": (
                abs(toe_gap) <= tolerance
                and abs(heel_gap) <= tolerance
                and contact_y_span >= body_height * 0.035
            ),
        }
    return result


def seat_support_metrics(body: bpy.types.Object, seat: bpy.types.Object) -> dict[str, object]:
    """Measure pelvis support against the diagnostic seat, without approval."""

    points = mesh_world_points(body, evaluated=True)
    group = body.vertex_groups.get(HIPS)
    if group is None or len(points) != len(body.data.vertices):
        return {"measured": False, "reason": "pelvis group or stable evaluated indexing unavailable"}
    seat_points = [seat.matrix_world @ Vector(corner) for corner in seat.bound_box]
    seat_low, seat_high = bounds_for_points(seat_points)
    pelvis_points: list[Vector] = []
    for vertex, point in zip(body.data.vertices, points):
        weight = max(
            (
                float(item.weight)
                for item in vertex.groups
                if int(item.group) == group.index
            ),
            default=0.0,
        )
        if (
            weight >= 0.25
            and seat_low.x <= point.x <= seat_high.x
            and seat_low.y <= point.y <= seat_high.y
        ):
            pelvis_points.append(point)
    if not pelvis_points:
        return {
            "measured": False,
            "reason": "no sufficiently pelvis-weighted surface samples fall over seat footprint",
            "seat_bounds_low": vector_list(seat_low),
            "seat_bounds_high": vector_list(seat_high),
        }
    ordered_y = sorted(point.y for point in pelvis_points)
    median_y = ordered_y[len(ordered_y) // 2]
    # Seat contact belongs under the posterior half of the pelvis.  Excluding
    # the anterior half prevents a low crotch/front sample from being mistaken
    # for the butt/seat support surface.
    posterior_points = [point for point in pelvis_points if point.y >= median_y]
    pelvis_low_z = min(point.z for point in posterior_points)
    gap = pelvis_low_z - seat_high.z
    near_top = [point for point in posterior_points if abs(point.z - seat_high.z) <= 0.010]
    return {
        "measured": True,
        "method": "vertices with pelvis-group weight >=0.25 inside seat XY footprint",
        "seat_bounds_low": vector_list(seat_low),
        "seat_bounds_high": vector_list(seat_high),
        "pelvis_sample_count": len(pelvis_points),
        "posterior_pelvis_sample_count": len(posterior_points),
        "pelvis_near_seat_top_within_10mm_count": len(near_top),
        "pelvis_low_to_seat_top_gap_m": round(float(gap), 7),
        "pelvis_median_y_m": round(float(median_y), 7),
        "front_support_margin_m": round(float(median_y - seat_low.y), 7),
        "back_support_margin_m": round(float(seat_high.y - median_y), 7),
        "stable_support_sanity": (
            abs(gap) <= 0.010
            and median_y - seat_low.y >= 0.020
            and seat_high.y - median_y >= 0.020
            and len(near_top) >= 8
        ),
        "truth_limit": "Diagnostic geometric contact only; not comfort, anatomy, or owner approval.",
    }


def local_bounds(body: bpy.types.Object) -> tuple[Vector, Vector]:
    return bounds_for_points([vertex.co.copy() for vertex in body.data.vertices])


def weight_signature(vertex: bpy.types.MeshVertex) -> tuple[tuple[int, int], ...]:
    return tuple(
        sorted(
            (int(item.group), int(round(float(item.weight) * 1_000_000)))
            for item in vertex.groups
            if float(item.weight) > 1e-8
        )
    )


def weight_health(mesh: bpy.types.Mesh) -> dict[str, int | float]:
    unweighted = 0
    bad_sum = 0
    maximum = 0
    over_four = 0
    positive_total = 0
    for vertex in mesh.vertices:
        weights = [float(item.weight) for item in vertex.groups if float(item.weight) > 1e-8]
        if not weights:
            unweighted += 1
            continue
        positive_total += len(weights)
        maximum = max(maximum, len(weights))
        over_four += int(len(weights) > 4)
        bad_sum += int(abs(sum(weights) - 1.0) > 1e-3)
    return {
        "vertex_count": len(mesh.vertices),
        "unweighted_vertex_count": unweighted,
        "weight_sum_out_of_tolerance_count": bad_sum,
        "maximum_positive_influences": maximum,
        "vertices_over_four_influences": over_four,
        "positive_weight_assignment_count": positive_total,
    }


def uv_multiset_hash(mesh: bpy.types.Mesh) -> dict[str, object]:
    if not mesh.uv_layers:
        return {"present": False, "corner_count": 0, "sha256": ""}
    layer = mesh.uv_layers.active or mesh.uv_layers[0]
    values = sorted(
        (
            int(round(float(item.uv.x) * 10_000_000)),
            int(round(float(item.uv.y) * 10_000_000)),
        )
        for item in layer.data
    )
    digest = hashlib.sha256()
    for u_value, v_value in values:
        digest.update(struct.pack("<ii", u_value, v_value))
    return {
        "present": True,
        "layer_count": len(mesh.uv_layers),
        "corner_count": len(values),
        "sha256": digest.hexdigest(),
        "quantization": "1e-7 UV units; sorted corner multiset",
    }


def topology_counts(mesh: bpy.types.Mesh) -> dict[str, int]:
    parent = list(range(len(mesh.vertices)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    edge_use: collections.Counter[tuple[int, int]] = collections.Counter()
    used: set[int] = set()
    collapsed_faces = 0
    for polygon in mesh.polygons:
        vertices = [int(index) for index in polygon.vertices]
        if len(set(vertices)) < 3:
            collapsed_faces += 1
            continue
        used.update(vertices)
        for index in vertices[1:]:
            union(vertices[0], index)
        for position, first in enumerate(vertices):
            edge = tuple(sorted((first, vertices[(position + 1) % len(vertices)])))
            edge_use[edge] += 1
    boundary_edges = [edge for edge, count in edge_use.items() if count == 1]
    adjacency: dict[int, set[int]] = {}
    for left, right in boundary_edges:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    seen: set[int] = set()
    loops = 0
    chains = 0
    for seed in adjacency:
        if seed in seen:
            continue
        stack = [seed]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency.get(current, ()))
        seen.update(component)
        if component and all(len(adjacency.get(index, ())) == 2 for index in component):
            loops += 1
        else:
            chains += 1
    return {
        "vertex_count": len(mesh.vertices),
        "triangle_count": sum(max(0, len(polygon.vertices) - 2) for polygon in mesh.polygons),
        "surface_island_count": len({find(index) for index in used}),
        "boundary_edge_count": len(boundary_edges),
        "boundary_loop_count": loops,
        "open_boundary_chain_count": chains,
        "non_manifold_edge_count": sum(1 for count in edge_use.values() if count > 2),
        "collapsed_face_count": collapsed_faces,
        "unused_vertex_count": len(mesh.vertices) - len(used),
    }


def weld_exact_safe_seams(body: bpy.types.Object) -> dict[str, object]:
    mesh = body.data
    before_topology = topology_counts(mesh)
    before_weights = weight_health(mesh)
    before_uv = uv_multiset_hash(mesh)
    groups: dict[tuple[float, float, float], list[bpy.types.MeshVertex]] = collections.defaultdict(list)
    for vertex in mesh.vertices:
        groups[tuple(float(value) for value in vertex.co)].append(vertex)
    duplicate_groups = [group for group in groups.values() if len(group) > 1]
    safe_groups = [
        group for group in duplicate_groups if len({weight_signature(vertex) for vertex in group}) == 1
    ]
    unsafe_groups = [
        group for group in duplicate_groups if len({weight_signature(vertex) for vertex in group}) != 1
    ]
    if unsafe_groups:
        raise ValueError(
            f"refusing seam weld: {len(unsafe_groups)} exact duplicate groups have conflicting weights"
        )
    safe_indices = sorted({vertex.index for group in safe_groups for vertex in group})
    expected_reduction = sum(len(group) - 1 for group in safe_groups)
    bmesh_value = bmesh.new()
    bmesh_value.from_mesh(mesh)
    bmesh_value.verts.ensure_lookup_table()
    bmesh_value.verts.layers.deform.verify()
    bmesh.ops.remove_doubles(
        bmesh_value,
        verts=[bmesh_value.verts[index] for index in safe_indices],
        dist=1e-9,
    )
    bmesh_value.to_mesh(mesh)
    bmesh_value.free()
    mesh.update(calc_edges=True)
    after_topology = topology_counts(mesh)
    after_weights = weight_health(mesh)
    after_uv = uv_multiset_hash(mesh)
    actual_reduction = before_topology["vertex_count"] - after_topology["vertex_count"]
    if actual_reduction != expected_reduction:
        raise ValueError(
            f"safe seam weld reduced {actual_reduction} vertices; expected {expected_reduction}"
        )
    if before_uv["sha256"] != after_uv["sha256"]:
        raise ValueError("safe seam weld changed the per-corner UV multiset")
    if after_weights["unweighted_vertex_count"] or after_weights["weight_sum_out_of_tolerance_count"]:
        raise ValueError("safe seam weld damaged required skin-weight coverage")
    return {
        "method": "exact duplicate positions; merge only groups with identical 1e-6-quantized weight signatures",
        "bmesh_merge_distance_local_units": 1e-9,
        "duplicate_group_count": len(duplicate_groups),
        "safe_duplicate_group_count": len(safe_groups),
        "unsafe_duplicate_group_count": len(unsafe_groups),
        "expected_and_actual_vertex_reduction": actual_reduction,
        "before_topology": before_topology,
        "after_topology": after_topology,
        "before_weights": before_weights,
        "after_weights": after_weights,
        "uv_before": before_uv,
        "uv_after": after_uv,
        "uv_multiset_preserved": before_uv["sha256"] == after_uv["sha256"],
        "truth_limit": (
            "The remaining boundary loops are preserved for later semantic review; this pass does not "
            "claim anatomical completeness or close ambiguous openings."
        ),
    }


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return float(value >= edge1)
    amount = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return amount * amount * (3.0 - 2.0 * amount)


def group_weight(vertex: bpy.types.MeshVertex, group_indices: set[int]) -> float:
    return max(
        (float(item.weight) for item in vertex.groups if int(item.group) in group_indices),
        default=0.0,
    )


def author_provisional_shape_key(body: bpy.types.Object) -> dict[str, object]:
    mesh = body.data
    low, high = local_bounds(body)
    extent = high - low
    center_x = (low.x + high.x) * 0.5
    center_y = (low.y + high.y) * 0.5
    group_index = {group.name: group.index for group in body.vertex_groups}
    names = {HEAD, NECK, SPINE, SPINE1, SPINE2, HIPS}
    if not names.issubset(group_index):
        raise ValueError("required semantic vertex groups are missing before proportion authoring")
    head_groups = {group_index[HEAD]}
    neck_groups = {group_index[NECK]}
    torso_groups = {group_index[name] for name in (SPINE, SPINE1, SPINE2)}
    hip_groups = {group_index[HIPS]}
    basis = body.shape_key_add(name="Basis", from_mix=False)
    key = body.shape_key_add(name="Kira_Provisional_R5", from_mix=False)
    key.value = 1.0
    key.slider_min = 0.0
    key.slider_max = 1.0
    moved = 0
    sum_displacement = 0.0
    max_displacement = 0.0
    region_counts: collections.Counter[str] = collections.Counter()
    for vertex in mesh.vertices:
        original = basis.data[vertex.index].co.copy()
        target = original.copy()
        z_ratio = (original.z - low.z) / max(extent.z, 1e-9)
        head_weight = group_weight(vertex, head_groups)
        neck_weight = group_weight(vertex, neck_groups)
        torso_weight = group_weight(vertex, torso_groups)
        hip_weight = group_weight(vertex, hip_groups)

        if head_weight > 1e-5:
            # A restrained design delta: slightly narrower cranial width,
            # slightly more facial depth, and a soft lower-face taper.  This is
            # explicitly a generic provisional design, not measured likeness.
            lower_face = 1.0 - smoothstep(0.925, 0.985, z_ratio)
            x_scale = 1.0 - head_weight * (0.018 + 0.010 * lower_face)
            y_scale = 1.0 + head_weight * (0.032 + 0.010 * lower_face)
            target.x = center_x + (target.x - center_x) * x_scale
            target.y = center_y + (target.y - center_y) * y_scale
            # A sub-millimetric world-space chin/cheek settling delta.
            if z_ratio < 0.947:
                target.z -= extent.z * 0.0017 * head_weight * lower_face
            region_counts["head"] += 1

        if neck_weight > 1e-5:
            target.x = center_x + (target.x - center_x) * (1.0 + 0.035 * neck_weight)
            target.y = center_y + (target.y - center_y) * (1.0 + 0.040 * neck_weight)
            region_counts["neck"] += 1

        if torso_weight > 1e-5:
            shoulder_band = smoothstep(0.70, 0.82, z_ratio)
            waist_band = math.exp(-((z_ratio - 0.565) / 0.075) ** 2)
            x_scale = 1.0 - torso_weight * (0.010 * shoulder_band + 0.014 * waist_band)
            y_scale = 1.0 + torso_weight * (0.018 - 0.006 * waist_band)
            target.x = center_x + (target.x - center_x) * x_scale
            target.y = center_y + (target.y - center_y) * y_scale
            region_counts["torso"] += 1

        if hip_weight > 1e-5:
            hip_band = math.exp(-((z_ratio - 0.48) / 0.09) ** 2)
            target.x = center_x + (target.x - center_x) * (1.0 + 0.014 * hip_weight * hip_band)
            target.y = center_y + (target.y - center_y) * (1.0 + 0.020 * hip_weight * hip_band)
            region_counts["hips"] += 1

        displacement = (target - original).length
        if displacement > 1e-9:
            moved += 1
            sum_displacement += displacement
            max_displacement = max(max_displacement, displacement)
        key.data[vertex.index].co = target
    body.active_shape_key_index = 1
    body.show_only_shape_key = False
    world_scale = sum(abs(float(body.matrix_world[axis][axis])) for axis in range(3)) / 3.0
    return {
        "shape_key": key.name,
        "default_value": float(key.value),
        "reversible_to_basis": True,
        "moved_vertex_count": moved,
        "mean_local_displacement": round(sum_displacement / max(moved, 1), 8),
        "maximum_local_displacement": round(max_displacement, 8),
        "mean_world_displacement_m": round(sum_displacement / max(moved, 1) * world_scale, 8),
        "maximum_world_displacement_m": round(max_displacement * world_scale, 8),
        "region_vertex_visits": dict(region_counts),
        "design_deltas": [
            "restrained head-width reduction and facial-depth increase",
            "modest neck volume support",
            "subtle shoulder/waist/hip proportion shaping",
            "hands and feet receive no direct sculpt operation",
        ],
        "likeness_claimed": False,
        "anatomical_completeness_claimed": False,
        "truth_note": "Provisional Kira-specific design direction only; no owner-approved likeness measurements exist.",
    }


def save_texture(
    output: Path,
    name: str,
    pixels: "object",
    *,
    colorspace: str,
) -> bpy.types.Image:
    height, width, channels = pixels.shape
    if channels != 4:
        raise ValueError("texture array must be RGBA")
    image = bpy.data.images.new(name=name, width=width, height=height, alpha=True)
    # Blender 5.1 reinitializes the image buffer when the color space changes.
    # Set it before populating pixels; setting it afterward silently produced
    # zeroed black PNGs in the first failed R5 review revisions.
    image.colorspace_settings.name = colorspace
    image.pixels.foreach_set(pixels.astype("float32").ravel())
    # foreach_set writes Blender's RNA buffer directly.  The explicit update
    # is required before save(), otherwise Blender 5.1 can write a zeroed PNG
    # even though the in-memory sequence was populated.
    image.update()
    image.filepath_raw = str(output)
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def author_skin_material(output_dir: Path) -> tuple[bpy.types.Material, dict[str, object]]:
    import numpy as np

    texture_dir = output_dir / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)
    size = 512
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    u = xx / float(size - 1)
    v = yy / float(size - 1)
    grain = (
        0.55 * np.sin(u * 41.0 + v * 17.0)
        + 0.30 * np.sin(u * 101.0 - v * 63.0)
        + 0.15 * np.sin(u * 223.0 + v * 191.0)
    )
    grain /= 1.0
    warm = 0.010 * np.sin(v * math.tau * 3.0) + 0.006 * grain
    albedo = np.zeros((size, size, 4), dtype=np.float32)
    albedo[..., 0] = np.clip(0.655 + warm, 0.0, 1.0)
    albedo[..., 1] = np.clip(0.435 + warm * 0.72, 0.0, 1.0)
    albedo[..., 2] = np.clip(0.330 + warm * 0.48, 0.0, 1.0)
    albedo[..., 3] = 1.0
    roughness_value = np.clip(0.56 + 0.045 * grain + 0.020 * np.sin(v * 37.0), 0.42, 0.72)
    roughness = np.stack(
        (roughness_value, roughness_value, roughness_value, np.ones_like(roughness_value)), axis=-1
    ).astype(np.float32)
    height_field = 0.40 * grain + 0.18 * np.sin(u * 311.0) * np.sin(v * 277.0)
    grad_y, grad_x = np.gradient(height_field)
    strength = 0.19
    nx = -grad_x * strength
    ny = -grad_y * strength
    nz = np.ones_like(nx)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack(
        (nx / norm * 0.5 + 0.5, ny / norm * 0.5 + 0.5, nz / norm * 0.5 + 0.5, np.ones_like(nx)),
        axis=-1,
    ).astype(np.float32)
    paths = {
        "albedo": texture_dir / "kira_provisional_skin_albedo_r5.png",
        "roughness": texture_dir / "kira_provisional_skin_roughness_r5.png",
        "normal": texture_dir / "kira_provisional_skin_normal_r5.png",
    }
    images = {
        "albedo": save_texture(paths["albedo"], "Kira_R5_Skin_Albedo", albedo, colorspace="sRGB"),
        "roughness": save_texture(paths["roughness"], "Kira_R5_Skin_Roughness", roughness, colorspace="Non-Color"),
        "normal": save_texture(paths["normal"], "Kira_R5_Skin_Normal", normal, colorspace="Non-Color"),
    }
    material = bpy.data.materials.new("Kira_Provisional_Skin_PBR_R5")
    material.use_nodes = True
    material.diffuse_color = (0.655, 0.435, 0.330, 1.0)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (620, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = 0.56
    bsdf.inputs["Metallic"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.42
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.32
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.045
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.44, 0.24)
    albedo_node = nodes.new("ShaderNodeTexImage")
    albedo_node.name = "R5_Skin_Albedo"
    albedo_node.image = images["albedo"]
    albedo_node.location = (-380, 150)
    roughness_node = nodes.new("ShaderNodeTexImage")
    roughness_node.name = "R5_Skin_Roughness"
    roughness_node.image = images["roughness"]
    roughness_node.location = (-380, -30)
    normal_texture = nodes.new("ShaderNodeTexImage")
    normal_texture.name = "R5_Skin_Normal"
    normal_texture.image = images["normal"]
    normal_texture.location = (-380, -220)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (0, -210)
    normal_map.inputs["Strength"].default_value = 0.08
    links.new(albedo_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(roughness_node.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])
    records = {
        key: {
            "path": str(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for key, path in paths.items()
    }
    return material, {
        "material": material.name,
        "workflow": "Principled PBR with deterministic albedo, roughness, and tangent-space normal textures",
        "textures": records,
        "texture_resolution": [size, size],
        "metallic": 0.0,
        "roughness_nominal": 0.56,
        "subsurface_weight": 0.045,
        "truth_note": "Surface-look improvement only; not anatomical or identity evidence.",
    }


def assign_single_material(body: bpy.types.Object, material: bpy.types.Material) -> None:
    body.data.materials.clear()
    body.data.materials.append(material)
    for polygon in body.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True


def make_material(name: str, color: tuple[float, float, float, float], roughness: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return material


def reset_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_create()
    armature.animation_data.action = None
    for bone in armature.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
        bone.rotation_mode = "QUATERNION"
    bpy.context.view_layer.update()


def rotate_pose_bone_toward(
    armature: bpy.types.Object,
    bone_name: str,
    target_world: Vector,
) -> None:
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        raise ValueError(f"missing pose bone: {bone_name}")
    target_local = armature.matrix_world.inverted() @ target_world
    current = (bone.tail - bone.head).normalized()
    desired = (target_local - bone.head).normalized()
    delta = current.rotation_difference(desired)
    pivot = bone.head.copy()
    bone.matrix = (
        Matrix.Translation(pivot)
        @ delta.to_matrix().to_4x4()
        @ Matrix.Translation(-pivot)
        @ bone.matrix
    )
    bpy.context.view_layer.update()


def pose_arm(
    armature: bpy.types.Object,
    *,
    side: str,
    low: Vector,
    height: float,
    pose: str,
) -> None:
    if side == "left":
        names = (LEFT_ARM, LEFT_FOREARM, LEFT_HAND)
    else:
        names = (RIGHT_ARM, RIGHT_FOREARM, RIGHT_HAND)
    upper = armature.pose.bones[names[0]]
    shoulder = armature.matrix_world @ upper.head
    sign = 1.0 if shoulder.x >= 0.0 else -1.0
    if pose == "reach" and side == "right":
        elbow = shoulder + Vector((sign * height * 0.030, -height * 0.145, -height * 0.018))
        hand = shoulder + Vector((sign * height * 0.022, -height * 0.302, -height * 0.025))
    elif pose == "stride":
        phase = 1.0 if side == "left" else -1.0
        elbow = shoulder + Vector((sign * height * 0.040, phase * height * 0.040, -height * 0.145))
        hand = Vector((sign * height * 0.145, phase * height * 0.070, low.z + height * 0.450))
    elif pose == "seated":
        elbow = shoulder + Vector((sign * height * 0.035, -height * 0.040, -height * 0.135))
        hand = shoulder + Vector((sign * height * 0.015, -height * 0.165, -height * 0.245))
    else:
        elbow = shoulder + Vector((sign * height * 0.035, height * 0.008, -height * 0.145))
        hand = Vector((sign * height * 0.150, -height * 0.006, low.z + height * 0.430))
    rotate_pose_bone_toward(armature, names[0], elbow)
    rotate_pose_bone_toward(armature, names[1], hand)
    if pose == "reach" and side == "right":
        hand_tip = hand + Vector((0.0, -0.065 * height, -0.002 * height))
    elif pose == "seated":
        hand_tip = hand + Vector((0.0, -0.020 * height, -0.045 * height))
    else:
        hand_tip = hand + Vector((0.0, -0.006 * height, -0.052 * height))
    rotate_pose_bone_toward(armature, names[2], hand_tip)


def translate_bone_world(armature: bpy.types.Object, bone_name: str, delta_world: Vector) -> None:
    bone = armature.pose.bones[bone_name]
    local_delta = armature.matrix_world.inverted().to_3x3() @ delta_world
    bone.matrix = Matrix.Translation(local_delta) @ bone.matrix
    bpy.context.view_layer.update()


def apply_pose(
    armature: bpy.types.Object,
    body: bpy.types.Object,
    pose: str,
    neutral_low: Vector,
    neutral_high: Vector,
) -> dict[str, object]:
    reset_pose(armature)
    height = neutral_high.z - neutral_low.z
    pose_arm(armature, side="left", low=neutral_low, height=height, pose=pose)
    pose_arm(armature, side="right", low=neutral_low, height=height, pose=pose)
    if pose == "stride":
        # Keep the right leg in its enrolled rest alignment as a visibly
        # planted support leg.  Only the left swing leg is advanced and bent;
        # this avoids the previous airborne double-leg diagnostic pose.
        thigh = armature.pose.bones[LEFT_THIGH]
        hip = armature.matrix_world @ thigh.head
        knee = hip + Vector((height * 0.012, -height * 0.105, -height * 0.235))
        rotate_pose_bone_toward(armature, LEFT_THIGH, knee)
        shin = armature.pose.bones[LEFT_SHIN]
        knee_world = armature.matrix_world @ shin.head
        ankle = knee_world + Vector((0.0, height * 0.030, -height * 0.205))
        rotate_pose_bone_toward(armature, LEFT_SHIN, ankle)
        rotate_pose_bone_toward(
            armature, LEFT_FOOT, ankle + Vector((0.0, -height * 0.080, -height * 0.008))
        )
    elif pose == "seated":
        translate_bone_world(armature, HIPS, Vector((0.0, 0.0, -height * 0.235)))
        for side, thigh_name, shin_name, foot_name in (
            ("left", LEFT_THIGH, LEFT_SHIN, LEFT_FOOT),
            ("right", RIGHT_THIGH, RIGHT_SHIN, RIGHT_FOOT),
        ):
            thigh = armature.pose.bones[thigh_name]
            hip = armature.matrix_world @ thigh.head
            lateral = height * 0.018 * (1.0 if side == "left" else -1.0)
            knee = hip + Vector((lateral, -height * 0.245, -height * 0.015))
            rotate_pose_bone_toward(armature, thigh_name, knee)
            shin = armature.pose.bones[shin_name]
            knee_world = armature.matrix_world @ shin.head
            ankle = knee_world + Vector((0.0, -height * 0.010, -height * 0.245))
            rotate_pose_bone_toward(armature, shin_name, ankle)
            rotate_pose_bone_toward(
                armature, foot_name, ankle + Vector((0.0, -height * 0.090, -height * 0.048))
            )
    bpy.context.view_layer.update()
    # Bring the lowest evaluated point to the neutral floor without moving the
    # object transform or altering the exported rest cage.
    current_low, _ = bounds_for_body(body, evaluated=True)
    delta_z = neutral_low.z - current_low.z
    if abs(delta_z) > 1e-7:
        translate_bone_world(armature, HIPS, Vector((0.0, 0.0, delta_z)))
    evaluated_low, evaluated_high = bounds_for_body(body, evaluated=True)
    pelvis_world = armature.matrix_world @ armature.pose.bones[HIPS].head
    return {
        "pose": pose,
        "finite_coordinates": all(
            math.isfinite(component)
            for point in mesh_world_points(body, evaluated=True)
            for component in point
        ),
        "bounds_low": vector_list(evaluated_low),
        "bounds_high": vector_list(evaluated_high),
        "extent": vector_list(evaluated_high - evaluated_low),
        "floor_target_z": round(float(neutral_low.z), 7),
        "minimum_ground_gap_m": round(float(evaluated_low.z - neutral_low.z), 7),
        "pelvis_world": vector_list(pelvis_world),
        "foot_contact": foot_contact_metrics(
            body,
            floor_z=neutral_low.z,
            body_height=height,
        ),
        "active_pose_bone_count": sum(
            1
            for bone in armature.pose.bones
            if any(
                abs(float(bone.matrix_basis[row][column] - Matrix.Identity(4)[row][column])) > 1e-7
                for row in range(4)
                for column in range(4)
            )
        ),
    }


def create_action(
    armature: bpy.types.Object,
    body: bpy.types.Object,
    *,
    name: str,
    pose: str,
    low: Vector,
    high: Vector,
) -> bpy.types.Action:
    apply_pose(armature, body, pose, low, high)
    action = bpy.data.actions.new(name)
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame in (1, 24):
        for bone in armature.pose.bones:
            bone.rotation_mode = "QUATERNION"
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=bone.name)
            bone.keyframe_insert(data_path="location", frame=frame, group=bone.name)
            bone.keyframe_insert(data_path="scale", frame=frame, group=bone.name)
    action["private_inactive_review_only"] = True
    action["pose_label"] = pose
    return action


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_lighting(center: Vector, height: float) -> None:
    specs = (
        (Vector((-0.70, -1.15, 1.05)), 360.0, 3.0),
        (Vector((0.85, -0.35, 0.65)), 180.0, 2.8),
        (Vector((0.20, 0.95, 1.20)), 260.0, 3.0),
    )
    for index, (direction, energy, size) in enumerate(specs, start=1):
        bpy.ops.object.light_add(type="AREA", location=center + direction * height)
        light = bpy.context.object
        light.name = f"R5_Private_Review_Light_{index}_Not_Exported"
        light.data.energy = energy
        light.data.size = size
        light["private_diagnostic_helper"] = True
        look_at(light, center)


def add_ground(low: Vector, high: Vector) -> bpy.types.Object:
    height = high.z - low.z
    material = make_material("R5_Private_Review_Ground", (0.10, 0.12, 0.15, 1.0), 0.88)
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, low.z - height * 0.008))
    ground = bpy.context.object
    ground.name = "R5_Private_Review_Ground_Not_Exported"
    ground.scale = (height * 0.75, height * 0.75, height * 0.008)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ground.data.materials.append(material)
    ground["private_diagnostic_helper"] = True
    return ground


def add_seat_helper(height: float) -> bpy.types.Object:
    material = make_material("R5_Private_Review_Seat", (0.18, 0.22, 0.26, 1.0), 0.74)
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.120 * height, 0.223 * height))
    seat = bpy.context.object
    seat.name = "R5_Private_Review_Seat_Not_Exported"
    seat.scale = (0.23 * height, 0.150 * height, 0.025 * height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    seat.data.materials.append(material)
    seat.hide_render = True
    seat["private_diagnostic_helper"] = True
    return seat


def render_view(
    output: Path,
    *,
    body: bpy.types.Object,
    camera: bpy.types.Object,
    direction: Vector,
) -> dict[str, object]:
    low, high = bounds_for_body(body, evaluated=True)
    extent = high - low
    center = (low + high) * 0.5
    center.z += extent.z * 0.015
    aspect = bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y
    ortho_scale = max(extent.z * 1.14, max(extent.x, extent.y) / max(aspect, 1e-6) * 1.12)
    camera.location = center + direction.normalized() * max(2.0, ortho_scale * 3.2)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    look_at(camera, center)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return {
        "path": str(output),
        "sha256": sha256_file(output),
        "size_bytes": output.stat().st_size,
        "camera_direction": vector_list(direction.normalized()),
        "evaluated_bounds_low": vector_list(low),
        "evaluated_bounds_high": vector_list(high),
        "orthographic_scale": round(float(ortho_scale), 6),
    }


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = Path(config["source_model"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve()
    allowed_root = (
        project_root
        / "Avatar"
        / "avatar_builder"
        / "candidate_sources"
        / "kira_provisional_body_r5"
    ).resolve()
    output_dir.relative_to(allowed_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(source) != config["source_sha256"]:
        raise ValueError("exact enrolled cage SHA-256 mismatch")
    if bool(config.get("runtime_activation_requested")):
        raise ValueError("R5 worker refuses runtime activation requests")

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    body, armature = primary_body_and_armature()
    removed_helpers = remove_source_helpers(body)
    original_bones = [bone.name for bone in armature.data.bones]
    original_vertex_group_names = [group.name for group in body.vertex_groups]
    if len(original_bones) != 79 or not set(REQUIRED_BONES).issubset(original_bones):
        raise ValueError("source rig is not the expected 79-joint humanoid rig")
    body.name = "Kira_Provisional_Body_R5_Private_Inactive"
    body.data.name = "Kira_Provisional_Body_R5_Mesh"
    armature.name = "Kira_79_Joint_Rig_R5_Private_Inactive"
    armature.data.name = "Kira_79_Joint_Rig_R5_Skeleton"
    for owner in (body, armature):
        owner["candidate_id"] = "kira"
        owner["candidate_revision"] = "provisional_body_r5"
        owner["maturity_policy"] = "adult"
        owner["private_inactive_review_only"] = True
        owner["runtime_activation_allowed"] = False
        owner["owner_approved"] = False
        owner["autobuild_approved"] = False
        owner["likeness_approved"] = False
        owner["anatomy_approved"] = False
    seam_audit = weld_exact_safe_seams(body)
    sculpt_audit = author_provisional_shape_key(body)
    skin_material, pbr_audit = author_skin_material(output_dir)
    assign_single_material(body, skin_material)

    neutral_low, neutral_high = bounds_for_body(body, evaluated=True)
    height = neutral_high.z - neutral_low.z
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.016, 0.024)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.45
    ground = add_ground(neutral_low, neutral_high)
    seat = add_seat_helper(height)
    add_lighting((neutral_low + neutral_high) * 0.5, height)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "R5_Private_Review_Camera_Not_Exported"
    camera["private_diagnostic_helper"] = True
    scene.camera = camera

    render_specs = (
        ("neutral_front", "neutral", Vector((0.0, -1.0, 0.035)), False),
        ("neutral_side", "neutral", Vector((1.0, 0.0, 0.025)), False),
        ("neutral_back", "neutral", Vector((0.0, 1.0, 0.035)), False),
        ("reach_front_three_quarter", "reach", Vector((0.68, -1.0, 0.075)), False),
        ("stride_front_three_quarter", "stride", Vector((0.68, -1.0, 0.075)), False),
        ("stride_side", "stride", Vector((1.0, 0.0, 0.035)), False),
        ("seated_front_three_quarter", "seated", Vector((0.68, -1.0, 0.070)), True),
        ("seated_side", "seated", Vector((1.0, 0.0, 0.035)), True),
    )
    renders: dict[str, object] = {}
    pose_metrics: dict[str, object] = {}
    for label, pose, direction, show_seat in render_specs:
        pose_metrics[pose] = apply_pose(armature, body, pose, neutral_low, neutral_high)
        seat.hide_render = not show_seat
        if show_seat:
            pose_metrics[pose]["seat_support"] = seat_support_metrics(body, seat)
        render_path = output_dir / "renders" / f"{label}.png"
        renders[label] = render_view(render_path, body=body, camera=camera, direction=direction)
    seat.hide_render = True

    actions = [
        create_action(
            armature,
            body,
            name=f"Kira_R5_{pose.title()}_Evidence",
            pose=pose,
            low=neutral_low,
            high=neutral_high,
        )
        for pose in ("neutral", "reach", "stride", "seated")
    ]
    reset_pose(armature)
    # Keep the reversible authored morph in the exported GLB.  Object's
    # shape_key_clear() removes the key blocks entirely, so values are managed
    # directly instead.
    if body.data.shape_keys and body.data.shape_keys.key_blocks.get("Kira_Provisional_R5"):
        body.data.shape_keys.key_blocks["Kira_Provisional_R5"].value = 1.0
    bpy.context.view_layer.update()

    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    body.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    model_path = output_dir / "kira_provisional_body_r5.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(model_path),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
        export_yup=True,
        export_morph=True,
        export_extras=True,
    )
    if not model_path.is_file():
        raise RuntimeError("Blender exporter did not create the R5 candidate GLB")
    final_bones = [bone.name for bone in armature.data.bones]
    final_vertex_group_names = [group.name for group in body.vertex_groups]
    rig_preserved = original_bones == final_bones and original_vertex_group_names == final_vertex_group_names
    if not rig_preserved:
        raise ValueError("R5 authoring changed the required rig or vertex-group ordering")
    manifest = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": "kira",
        "candidate_revision": "provisional_body_r5",
        "status": "private_inactive_reversible_review_candidate",
        "source": {
            "project_path": config["source_project_path"],
            "sha256": config["source_sha256"],
            "removed_source_helpers": removed_helpers,
        },
        "model": {
            "path": str(model_path),
            "sha256": sha256_file(model_path),
            "size_bytes": model_path.stat().st_size,
            "genuinely_transformed_derivative": sha256_file(model_path) != config["source_sha256"],
        },
        "seam_and_topology_audit": seam_audit,
        "provisional_shape_design": sculpt_audit,
        "skin_surface": pbr_audit,
        "rig": {
            "bone_count": len(final_bones),
            "bone_order_and_names_exactly_preserved": original_bones == final_bones,
            "vertex_group_order_and_names_exactly_preserved": (
                original_vertex_group_names == final_vertex_group_names
            ),
            "required_core_bones_present": all(name in final_bones for name in REQUIRED_BONES),
            "finger_bone_count": sum(1 for name in final_bones if "Hand" in name and name not in (LEFT_HAND, RIGHT_HAND)),
            "actions": [action.name for action in actions],
            "stable_working_rig_proven": False,
        },
        "pose_metrics": pose_metrics,
        "renders": renders,
        "explicit_absences": {
            "eyes": "not authored; separate eye-rig lane",
            "hair": "not authored",
            "clothes": "not authored",
            "shoes": "not authored",
            "primitive_wearables": False,
        },
        "privacy_and_activation": {
            "private_body_builder_review_only": True,
            "runtime_activation_allowed": False,
            "live_avatar_targeted": False,
            "owner_approved": False,
            "likeness_approved": False,
            "anatomy_approved": False,
            "autobuild_gate_passed_subjects": 0,
            "autobuild_gate_required_subjects": 2,
        },
        "truth_note": (
            "R5 proves a transformed, welded, weighted, renderable provisional adult cage and several "
            "finite diagnostic poses. It does not prove Kira likeness, complete anatomy, final deformation, "
            "owner approval, runtime safety, or permission to autobuild other bodies."
        ),
    }
    manifest_path = output_dir / "kira_provisional_body_r5_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "candidate": str(model_path),
                "candidate_sha256": manifest["model"]["sha256"],
                "manifest": str(manifest_path),
                "welded_vertices": seam_audit["expected_and_actual_vertex_reduction"],
                "bone_count": len(final_bones),
                "renders": len(renders),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
