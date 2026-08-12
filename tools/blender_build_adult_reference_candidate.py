"""Blender worker for a licensed, shape-preserving adult avatar derivative.

Run only through ``tools/build_adult_reference_avatar_candidate.py``.  The
worker never renders and never writes a runtime/live avatar path.  It preserves
the licensed source surface geometry, removes duplicate outline shells and all
source materials, authors a new humanoid/finger rig plus weights, and generates
an ordinary outfit as separate skinned geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

TRUSTED_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(TRUSTED_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(TRUSTED_PROJECT_ROOT))

from Core.adult_reference_avatar_backend import authorize_adult_reference_worker_request

import bpy
from mathutils import Vector


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--validated-request-sha256", required=True)
    return parser.parse_args(argv)


def project_path(value: str, root: Path) -> Path:
    path = Path(value)
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def material_tokens(obj: bpy.types.Object) -> set[str]:
    return {
        re.sub(r"[^a-z0-9]+", "", material.name.lower())
        for material in obj.data.materials
        if material
    }


def apply_world_transform(obj: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def make_material(name: str, rgba: tuple[float, float, float, float], roughness: float = 0.65):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = roughness
    return material


def set_single_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True


def aggregate_bounds(objects: Iterable[bpy.types.Object]) -> tuple[Vector, Vector]:
    coords = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    if not coords:
        raise ValueError("no mesh coordinates available")
    return (
        Vector((min(point.x for point in coords), min(point.y for point in coords), min(point.z for point in coords))),
        Vector((max(point.x for point in coords), max(point.y for point in coords), max(point.z for point in coords))),
    )


def topology_fingerprint(objects: Iterable[bpy.types.Object]) -> str:
    """Name-independent surface fingerprint after transforms are applied."""
    digest = hashlib.sha256()
    records: list[bytes] = []
    for obj in objects:
        coords = [tuple(round(float(value), 7) for value in vertex.co) for vertex in obj.data.vertices]
        faces = [tuple(int(index) for index in polygon.vertices) for polygon in obj.data.polygons]
        payload = json.dumps({"vertices": coords, "faces": faces}, separators=(",", ":")).encode("utf-8")
        records.append(hashlib.sha256(payload).digest())
    for record in sorted(records):
        digest.update(record)
    return digest.hexdigest()


def rig_signature(armature: bpy.types.Object) -> str:
    records = []
    for bone in armature.data.bones:
        records.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else "",
                "head": [round(float(value), 7) for value in bone.head_local],
                "tail": [round(float(value), 7) for value in bone.tail_local],
                "deform": bool(bone.use_deform),
            }
        )
    encoded = json.dumps(sorted(records, key=lambda item: item["name"]), separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def create_armature(bounds_min: Vector, bounds_max: Vector, candidate_id: str) -> bpy.types.Object:
    floor = bounds_min.z
    height = max(0.5, bounds_max.z - floor)
    center_x = (bounds_min.x + bounds_max.x) * 0.5
    center_y = (bounds_min.y + bounds_max.y) * 0.5
    reach = max(abs(bounds_min.x - center_x), abs(bounds_max.x - center_x))
    front_y = bounds_min.y
    hips_z = floor + height * 0.50
    knee_z = floor + height * 0.275
    ankle_z = floor + height * 0.065
    shoulder_z = floor + height * 0.745
    neck_z = floor + height * 0.79
    shoulder_x = min(reach * 0.28, height * 0.12)
    elbow_x = shoulder_x + (reach - shoulder_x) * 0.48
    wrist_x = shoulder_x + (reach - shoulder_x) * 0.86
    hand_x = shoulder_x + (reach - shoulder_x) * 0.98
    hip_x = height * 0.063

    bpy.ops.object.armature_add(enter_editmode=False, location=(0, 0, 0))
    armature = bpy.context.object
    armature.name = f"{candidate_id}_canonical_rig"
    armature.data.name = f"{candidate_id}_canonical_skeleton"
    bpy.ops.object.mode_set(mode="EDIT")
    armature.data.edit_bones.remove(armature.data.edit_bones[0])

    def bone(name: str, head, tail, parent: str | None = None, *, deform: bool = True):
        item = armature.data.edit_bones.new(name)
        item.head = head
        item.tail = tail
        item.use_deform = deform
        if parent:
            item.parent = armature.data.edit_bones[parent]
            item.use_connect = False
        return item

    bone("root", (center_x, center_y, floor), (center_x, center_y, hips_z), deform=False)
    bone("pelvis", (center_x, center_y, hips_z - height * 0.035), (center_x, center_y, hips_z + height * 0.06), "root")
    bone("spine", (center_x, center_y, hips_z + height * 0.02), (center_x, center_y, floor + height * 0.65), "pelvis")
    bone("chest", (center_x, center_y, floor + height * 0.62), (center_x, center_y, shoulder_z), "spine")
    bone("neck", (center_x, center_y, shoulder_z), (center_x, center_y, neck_z + height * 0.025), "chest")
    bone("head", (center_x, center_y, neck_z), (center_x, center_y, bounds_max.z), "neck")

    for side, sign in (("left", 1.0), ("right", -1.0)):
        sx = center_x + sign * shoulder_x
        ex = center_x + sign * elbow_x
        wx = center_x + sign * wrist_x
        hx = center_x + sign * hand_x
        bone(f"{side}_clavicle", (center_x, center_y, shoulder_z), (sx, center_y, shoulder_z), "chest")
        bone(f"{side}_upper_arm", (sx, center_y, shoulder_z), (ex, center_y, shoulder_z), f"{side}_clavicle")
        bone(f"{side}_lower_arm", (ex, center_y, shoulder_z), (wx, center_y, shoulder_z), f"{side}_upper_arm")
        bone(f"{side}_hand", (wx, center_y, shoulder_z), (hx, center_y, shoulder_z), f"{side}_lower_arm")
        finger_y_offsets = {
            "thumb": -height * 0.025,
            "index": -height * 0.012,
            "middle": 0.0,
            "ring": height * 0.011,
            "pinky": height * 0.022,
        }
        for digit, y_offset in finger_y_offsets.items():
            start = Vector((wx, center_y + y_offset, shoulder_z))
            mid = Vector((wx + sign * (hand_x - wrist_x) * 0.55, center_y + y_offset, shoulder_z))
            end = Vector((hx, center_y + y_offset, shoulder_z))
            bone(f"{side}_{digit}_01", start, mid, f"{side}_hand")
            bone(f"{side}_{digit}_02", mid, end, f"{side}_{digit}_01")

        upper_leg_head = (center_x + sign * hip_x, center_y, hips_z)
        knee = (center_x + sign * hip_x, center_y, knee_z)
        ankle = (center_x + sign * hip_x, center_y, ankle_z)
        toe = (center_x + sign * hip_x, front_y, floor + height * 0.025)
        bone(f"{side}_upper_leg", upper_leg_head, knee, "pelvis")
        bone(f"{side}_lower_leg", knee, ankle, f"{side}_upper_leg")
        bone(f"{side}_foot", ankle, toe, f"{side}_lower_leg")
        bone(f"{side}_toe", toe, (toe[0], front_y - height * 0.025, toe[2]), f"{side}_foot")

    bpy.ops.object.mode_set(mode="OBJECT")
    armature.show_in_front = True
    armature["candidate_id"] = candidate_id
    armature["rig_purpose"] = "private_review_only_shape_preserving_derivative"
    armature["runtime_activation_allowed"] = False
    return armature


def _add_weight(groups: dict[str, bpy.types.VertexGroup], index: int, values: list[tuple[str, float]]) -> None:
    filtered = [(name, max(0.0, float(weight))) for name, weight in values if weight > 0.0 and name in groups]
    filtered = sorted(filtered, key=lambda item: item[1], reverse=True)[:4]
    total = sum(weight for _, weight in filtered) or 1.0
    for name, weight in filtered:
        groups[name].add([index], weight / total, "REPLACE")


def mark_all_vertices(obj: bpy.types.Object, marker_name: str) -> None:
    """Attach a temporary construction marker that survives a mesh join.

    The marker is consumed before skinning and is not exported.  It lets the
    joined trouser mesh keep an exact left-leg/right-leg/waistband distinction
    even where the opaque cloth envelopes meet at the crotch.
    """

    marker = obj.vertex_groups.new(name=marker_name)
    marker.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")


def skin_object(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    bounds_min: Vector,
    bounds_max: Vector,
    *,
    rigid_head: bool = False,
    skinning_profile: str = "body",
) -> dict[str, float | int]:
    pants_markers: dict[int, str] = {}
    if skinning_profile == "pants":
        for marker_name in (
            "diagnostic_pants_waistband",
            "diagnostic_pants_left_leg",
            "diagnostic_pants_right_leg",
        ):
            marker = obj.vertex_groups.get(marker_name)
            if marker is None:
                continue
            for vertex in obj.data.vertices:
                try:
                    if marker.weight(vertex.index) > 0.0:
                        pants_markers[vertex.index] = marker_name
                except RuntimeError:
                    continue
    obj.vertex_groups.clear()
    groups = {bone.name: obj.vertex_groups.new(name=bone.name) for bone in armature.data.bones if bone.use_deform}
    floor = bounds_min.z
    height = max(0.5, bounds_max.z - floor)
    center_x = (bounds_min.x + bounds_max.x) * 0.5
    reach = max(abs(bounds_min.x - center_x), abs(bounds_max.x - center_x))
    shoulder_x = min(reach * 0.28, height * 0.12)
    elbow_x = shoulder_x + (reach - shoulder_x) * 0.48
    wrist_x = shoulder_x + (reach - shoulder_x) * 0.86
    hips_z = floor + height * 0.50
    knee_z = floor + height * 0.275
    ankle_z = floor + height * 0.065
    shoulder_z = floor + height * 0.745
    neck_z = floor + height * 0.79
    y_min = bounds_min.y
    y_span = max(0.001, bounds_max.y - bounds_min.y)
    digit_order = ["thumb", "index", "middle", "ring", "pinky"]

    def leg_chain_weights(side_name: str, z: float) -> list[tuple[str, float]]:
        """Use compact blends at the knee/ankle instead of a shin-long blend."""

        knee_blend = height * 0.032
        ankle_blend = height * 0.022
        if z >= knee_z + knee_blend:
            return [(f"{side_name}_upper_leg", 1.0)]
        if z >= knee_z - knee_blend:
            lower = (knee_z + knee_blend - z) / max(knee_blend * 2.0, 1e-5)
            return [
                (f"{side_name}_upper_leg", 1.0 - lower),
                (f"{side_name}_lower_leg", lower),
            ]
        if z >= ankle_z + ankle_blend:
            return [(f"{side_name}_lower_leg", 1.0)]
        if z >= ankle_z - ankle_blend:
            foot = (ankle_z + ankle_blend - z) / max(ankle_blend * 2.0, 1e-5)
            return [
                (f"{side_name}_lower_leg", 1.0 - foot),
                (f"{side_name}_foot", foot),
            ]
        return [(f"{side_name}_foot", 1.0)]

    for vertex in obj.data.vertices:
        point = vertex.co
        if rigid_head:
            _add_weight(groups, vertex.index, [("head", 1.0)])
            continue
        relative_z = (point.z - floor) / height
        side = "left" if point.x >= center_x else "right"
        abs_x = abs(point.x - center_x)
        if skinning_profile == "shirt":
            # Joined torso/sleeve volumes need semantic weights.  The generic
            # bounding-box classifier previously treated the shirt sides and
            # even the trouser waist as arm geometry, which made walk/sit
            # diagnostics collapse into large flaps.
            sleeve_start = height * 0.165
            if abs_x >= sleeve_start and point.z >= floor + height * 0.64:
                if abs_x <= elbow_x:
                    t = (abs_x - sleeve_start) / max(elbow_x - sleeve_start, 1e-5)
                    weights = [
                        (f"{side}_clavicle", max(0.0, 0.45 * (1.0 - t))),
                        (f"{side}_upper_arm", 0.55 + 0.45 * t),
                    ]
                elif abs_x <= wrist_x:
                    t = (abs_x - elbow_x) / max(wrist_x - elbow_x, 1e-5)
                    weights = [
                        (f"{side}_upper_arm", 1.0 - t),
                        (f"{side}_lower_arm", t),
                    ]
                else:
                    weights = [(f"{side}_lower_arm", 1.0)]
            elif relative_z < 0.60:
                t = max(0.0, min(1.0, (relative_z - 0.49) / 0.11))
                weights = [("pelvis", 1.0 - t), ("spine", t)]
            else:
                t = max(0.0, min(1.0, (relative_z - 0.60) / 0.12))
                weights = [("spine", 1.0 - t), ("chest", t)]
        elif skinning_profile == "pants":
            marker = pants_markers.get(vertex.index, "")
            if marker == "diagnostic_pants_waistband":
                weights = [("pelvis", 1.0)]
            else:
                if marker == "diagnostic_pants_left_leg":
                    side = "left"
                elif marker == "diagnostic_pants_right_leg":
                    side = "right"
                hip_blend_low = floor + height * 0.395
                hip_blend_high = floor + height * 0.485
                if point.z >= hip_blend_low:
                    pelvis = min(
                        0.68,
                        max(
                            0.0,
                            (point.z - hip_blend_low)
                            / max(hip_blend_high - hip_blend_low, 1e-5)
                            * 0.68,
                        ),
                    )
                    weights = [
                        ("pelvis", pelvis),
                        (f"{side}_upper_leg", 1.0 - pelvis),
                    ]
                else:
                    weights = leg_chain_weights(side, point.z)
        elif skinning_profile == "shoes":
            weights = [(f"{side}_foot", 1.0)]
        elif skinning_profile == "collar":
            weights = [("chest", 0.65), ("neck", 0.35)]
        elif point.z >= neck_z:
            weights = [("head", 1.0)]
        elif point.z >= shoulder_z and abs_x <= shoulder_x * 1.05:
            blend = min(1.0, max(0.0, (point.z - shoulder_z) / max(height * 0.05, 1e-5)))
            weights = [("chest", 1.0 - blend), ("neck", blend)]
        elif point.z >= shoulder_z - height * 0.08 and abs_x >= shoulder_x * 0.82:
            if abs_x <= elbow_x:
                t = (abs_x - shoulder_x * 0.82) / max(elbow_x - shoulder_x * 0.82, 1e-5)
                weights = [(f"{side}_clavicle", max(0.0, 0.25 * (1.0 - t))), (f"{side}_upper_arm", 0.75 + 0.25 * t)]
            elif abs_x <= wrist_x:
                t = (abs_x - elbow_x) / max(wrist_x - elbow_x, 1e-5)
                weights = [(f"{side}_upper_arm", 1.0 - t), (f"{side}_lower_arm", t)]
            else:
                hand_t = min(1.0, max(0.0, (abs_x - wrist_x) / max(reach - wrist_x, 1e-5)))
                y_ratio = min(0.999, max(0.0, (point.y - y_min) / y_span))
                digit = digit_order[min(4, int(y_ratio * 5.0))]
                segment = "02" if hand_t > 0.68 else "01"
                finger_weight = min(0.92, max(0.12, (hand_t - 0.08) / 0.92))
                weights = [(f"{side}_hand", 1.0 - finger_weight), (f"{side}_{digit}_{segment}", finger_weight)]
        elif point.z < hips_z:
            if abs_x < height * 0.015:
                side = "left" if point.x >= center_x else "right"
            if point.z >= floor + height * 0.43:
                t = (hips_z - point.z) / max(height * 0.07, 1e-5)
                pelvis_weight = 0.85 - min(1.0, max(0.0, t)) * 0.60
                weights = [
                    ("pelvis", pelvis_weight),
                    (f"{side}_upper_leg", 1.0 - pelvis_weight),
                ]
            else:
                weights = leg_chain_weights(side, point.z)
        elif relative_z < 0.60:
            t = max(0.0, min(1.0, (relative_z - 0.49) / 0.11))
            weights = [("pelvis", 1.0 - t), ("spine", t)]
        elif relative_z < 0.71:
            t = max(0.0, min(1.0, (relative_z - 0.60) / 0.11))
            weights = [("spine", 1.0 - t), ("chest", t)]
        else:
            weights = [("chest", 1.0)]
        _add_weight(groups, vertex.index, weights)

    modifier = obj.modifiers.new(name="candidate_canonical_armature", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    obj.parent = armature
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    weighted = sum(1 for vertex in obj.data.vertices if vertex.groups)
    return {"vertex_count": len(obj.data.vertices), "weighted_vertex_count": weighted}


def create_surface_garment(
    name: str,
    source: bpy.types.Object,
    predicate: Callable[[Vector], bool],
    material: bpy.types.Material,
    offset: float,
    thickness: float,
    *,
    smooth_iterations: int = 6,
    smooth_factor: float = 0.32,
) -> bpy.types.Object:
    source.data.calc_loop_triangles()
    source.data.update()
    selected = [polygon for polygon in source.data.polygons if predicate(polygon.center)]
    if not selected:
        raise ValueError(f"no source faces selected for {name}")
    used = sorted({index for polygon in selected for index in polygon.vertices})
    mapping = {old: new for new, old in enumerate(used)}
    vertices = [
        tuple(source.data.vertices[index].co + source.data.vertices[index].normal * offset)
        for index in used
    ]
    faces = [tuple(mapping[index] for index in polygon.vertices) for polygon in selected]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    garment = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(garment)
    set_single_material(garment, material)

    # A garment copied directly from the body surface preserves every small
    # anatomical contour and lets separately-modelled body details protrude.
    # Smooth the review garment into its own cloth envelope before adding
    # thickness.  This does not alter the licensed body surface and keeps the
    # garment a genuinely separate mesh.
    if smooth_iterations > 0:
        smooth = garment.modifiers.new(name="cloth_envelope_smooth", type="SMOOTH")
        smooth.factor = smooth_factor
        smooth.iterations = smooth_iterations
        bpy.context.view_layer.objects.active = garment
        garment.select_set(True)
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        garment.select_set(False)

    solidify = garment.modifiers.new(name="garment_thickness", type="SOLIDIFY")
    solidify.thickness = thickness
    # Put all thickness away from the body.  A centred shell placed half its
    # thickness inward created avoidable intersections in the first Beth
    # diagnostic assembly.
    solidify.offset = 1.0
    solidify.use_rim = True
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    garment.select_set(False)
    return garment


def create_collar(
    bounds_min: Vector,
    bounds_max: Vector,
    material: bpy.types.Material,
) -> bpy.types.Object:
    height = bounds_max.z - bounds_min.z
    cx = (bounds_min.x + bounds_max.x) * 0.5
    front = bounds_min.y - height * 0.004
    z = bounds_min.z + height * 0.765
    width = height * 0.045
    drop = height * 0.026
    vertices = [
        (cx - width, front, z),
        (cx - height * 0.012, front - height * 0.004, z),
        (cx - height * 0.025, front - height * 0.008, z - drop),
        (cx + height * 0.012, front - height * 0.004, z),
        (cx + width, front, z),
        (cx + height * 0.025, front - height * 0.008, z - drop),
    ]
    mesh = bpy.data.meshes.new("ordinary_red_collar_mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2), (3, 4, 5)])
    mesh.update()
    obj = bpy.data.objects.new("ordinary_red_short_sleeve_collar", mesh)
    bpy.context.collection.objects.link(obj)
    set_single_material(obj, material)
    solidify = obj.modifiers.new(name="collar_thickness", type="SOLIDIFY")
    solidify.thickness = height * 0.003
    solidify.offset = 1.0
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    obj.select_set(False)
    return obj


def create_rounded_box_garment(
    name: str,
    *,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    material: bpy.types.Material,
    bevel: float,
) -> bpy.types.Object:
    """Create a simple independent cloth volume rather than a body-skin copy.

    The licensed Beth source contains separately modelled anatomical details.
    A garment cloned from only the largest body surface cannot reliably cover
    those parts, and it also reproduces fine body contours as if they were
    printed into the fabric.  A rounded, closed cloth volume is deliberately
    modest but gives the visual-review assembly honest opaque coverage while
    keeping the underlying body untouched and separately exported.
    """

    bpy.ops.mesh.primitive_cube_add(location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(max(0.001, value * 0.5) for value in size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new(name="cloth_volume_rounding", type="BEVEL")
    modifier.width = min(max(0.001, bevel), min(size) * 0.22)
    modifier.segments = 4
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    set_single_material(obj, material)
    return obj


def create_sleeve_garment(
    name: str,
    *,
    center: tuple[float, float, float],
    length: float,
    radius_y: float,
    radius_z: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=1.0,
        depth=max(0.01, length),
        end_fill_type="NGON",
        location=center,
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    # The cylinder's local X/Y cross-section becomes world Z/Y after the
    # rotation.  Scale before applying so the exported garment has ordinary
    # mesh coordinates and no hidden transform dependency.
    obj.scale = (max(0.005, radius_z), max(0.005, radius_y), 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new(name="sleeve_edge_rounding", type="BEVEL")
    bevel.width = min(radius_y, radius_z) * 0.12
    bevel.segments = 3
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj.select_set(False)
    set_single_material(obj, material)
    return obj


def create_crew_collar(
    *,
    center_x: float,
    center_y: float,
    z: float,
    height: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_segments=36,
        minor_segments=10,
        location=(center_x, center_y, z),
        major_radius=height * 0.047,
        minor_radius=height * 0.010,
    )
    obj = bpy.context.object
    obj.name = "ordinary_beth_red_crew_collar"
    obj.scale.y = 0.78
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_single_material(obj, material)
    return obj


def join_garment_parts(name: str, parts: list[bpy.types.Object]) -> bpy.types.Object:
    if not parts:
        raise ValueError(f"no garment parts supplied for {name}")
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name
    joined.data.name = f"{name}_mesh"
    joined.select_set(False)
    return joined


def create_profiled_tube_z(
    name: str,
    *,
    center_x: float,
    center_y: float,
    rings: list[tuple[float, float, float]],
    material: bpy.types.Material,
    thickness: float,
    segments: int = 32,
) -> bpy.types.Object:
    """Create a smooth elliptical cloth envelope along the vertical axis."""

    if len(rings) < 2 or segments < 8:
        raise ValueError(f"invalid profiled tube for {name}")
    vertices: list[tuple[float, float, float]] = []
    for z, radius_x, radius_y in rings:
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append(
                (
                    center_x + radius_x * math.cos(angle),
                    center_y + radius_y * math.sin(angle),
                    z,
                )
            )
    faces: list[tuple[int, int, int, int]] = []
    for ring_index in range(len(rings) - 1):
        start = ring_index * segments
        next_start = (ring_index + 1) * segments
        for index in range(segments):
            following = (index + 1) % segments
            faces.append((start + index, start + following, next_start + following, next_start + index))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    set_single_material(obj, material)
    solidify = obj.modifiers.new(name="cloth_thickness", type="SOLIDIFY")
    solidify.thickness = max(0.001, thickness)
    solidify.offset = 1.0
    solidify.use_rim = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    obj.select_set(False)
    return obj


def create_profiled_tube_x(
    name: str,
    *,
    center_y: float,
    center_z: float,
    rings: list[tuple[float, float, float]],
    material: bpy.types.Material,
    thickness: float,
    segments: int = 28,
) -> bpy.types.Object:
    """Create a tapered elliptical sleeve along the horizontal arm axis."""

    if len(rings) < 2 or segments < 8:
        raise ValueError(f"invalid sleeve tube for {name}")
    vertices: list[tuple[float, float, float]] = []
    for x, radius_y, radius_z in rings:
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append(
                (
                    x,
                    center_y + radius_y * math.cos(angle),
                    center_z + radius_z * math.sin(angle),
                )
            )
    faces: list[tuple[int, int, int, int]] = []
    for ring_index in range(len(rings) - 1):
        start = ring_index * segments
        next_start = (ring_index + 1) * segments
        for index in range(segments):
            following = (index + 1) % segments
            faces.append((start + index, start + following, next_start + following, next_start + index))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    set_single_material(obj, material)
    solidify = obj.modifiers.new(name="cloth_thickness", type="SOLIDIFY")
    solidify.thickness = max(0.001, thickness)
    solidify.offset = 1.0
    solidify.use_rim = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    obj.select_set(False)
    return obj


def create_trouser_gusset_half(
    name: str,
    *,
    center_x: float,
    center_y: float,
    floor: float,
    height: float,
    side_sign: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create one closed half of a modest front/back crotch bridge.

    Two independently marked halves meet on the center seam.  They close the
    diagnostic coverage gap without reintroducing a single rigid hip block.
    """

    seam_x = center_x + side_sign * height * 0.002
    outer_x = center_x + side_sign * height * 0.066
    lower_outer_x = center_x + side_sign * height * 0.033
    front_y = center_y - height * 0.093
    back_y = center_y + height * 0.093
    top_z = floor + height * 0.452
    lower_z = floor + height * 0.397
    vertices = [
        (seam_x, front_y, top_z),
        (outer_x, front_y, top_z),
        (lower_outer_x, front_y, lower_z),
        (seam_x, front_y, lower_z),
        (seam_x, back_y, top_z),
        (outer_x, back_y, top_z),
        (lower_outer_x, back_y, lower_z),
        (seam_x, back_y, lower_z),
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (3, 2, 6, 7),
        (1, 5, 6, 2),
        (0, 3, 7, 4),
    ]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    set_single_material(obj, material)
    bevel = obj.modifiers.new(name="gusset_edge_softening", type="BEVEL")
    bevel.width = height * 0.004
    bevel.segments = 2
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj.select_set(False)
    return obj


def create_ordinary_outfit_volumes(
    *,
    body_bounds_min: Vector,
    body_bounds_max: Vector,
    overall_bounds_max: Vector,
    red_top: bpy.types.Material,
    blue_pants: bpy.types.Material,
    simple_shoes: bpy.types.Material,
) -> list[bpy.types.Object]:
    """Build an opaque, separate, deliberately simple Beth review outfit."""

    floor = body_bounds_min.z
    height = max(0.5, overall_bounds_max.z - floor)
    center_x = (body_bounds_min.x + body_bounds_max.x) * 0.5
    center_y = (body_bounds_min.y + body_bounds_max.y) * 0.5

    torso = create_profiled_tube_z(
        "ordinary_beth_red_short_sleeve_top_torso",
        center_x=center_x,
        center_y=center_y,
        rings=[
            (floor + height * 0.49, height * 0.115, height * 0.095),
            (floor + height * 0.56, height * 0.110, height * 0.100),
            (floor + height * 0.64, height * 0.128, height * 0.112),
            (floor + height * 0.70, height * 0.145, height * 0.118),
            (floor + height * 0.765, height * 0.155, height * 0.105),
        ],
        material=red_top,
        thickness=height * 0.003,
    )
    sleeves = [
        create_profiled_tube_x(
            f"ordinary_beth_red_short_sleeve_{side}",
            center_y=center_y,
            center_z=floor + height * 0.727,
            rings=[
                (center_x + sign * height * 0.135, height * 0.058, height * 0.055),
                (center_x + sign * height * 0.215, height * 0.052, height * 0.050),
                (center_x + sign * height * 0.290, height * 0.047, height * 0.046),
            ],
            material=red_top,
            thickness=height * 0.003,
        )
        for side, sign in (("left", 1.0), ("right", -1.0))
    ]
    collar = create_crew_collar(
        center_x=center_x,
        center_y=center_y,
        z=floor + height * 0.765,
        height=height,
        material=red_top,
    )

    # R6 replaces the single rigid hip box with one fitted waistband envelope
    # and two side-locked leg envelopes.  The parts meet at center without
    # crossing it, so opaque diagnostic coverage is retained while each thigh
    # can follow its own upper-leg bone.  This is still deliberately simple
    # diagnostic clothing, not cloth simulation or wearable-behavior proof.
    waistband = create_profiled_tube_z(
        "ordinary_beth_blue_pants_waistband",
        center_x=center_x,
        center_y=center_y,
        rings=[
            (floor + height * 0.418, height * 0.125, height * 0.096),
            (floor + height * 0.452, height * 0.143, height * 0.112),
            (floor + height * 0.487, height * 0.139, height * 0.108),
            (floor + height * 0.512, height * 0.126, height * 0.098),
        ],
        material=blue_pants,
        thickness=height * 0.0035,
    )
    mark_all_vertices(waistband, "diagnostic_pants_waistband")
    leg_center_offset = height * 0.065
    legs = [
        create_profiled_tube_z(
            f"ordinary_beth_blue_pants_{side}_leg",
            center_x=center_x + sign * leg_center_offset,
            center_y=center_y,
            rings=[
                (floor + height * 0.075, height * 0.052, height * 0.065),
                (floor + height * 0.175, height * 0.055, height * 0.069),
                (floor + height * 0.245, height * 0.057, height * 0.071),
                (floor + height * 0.300, height * 0.060, height * 0.074),
                (floor + height * 0.355, height * 0.064, height * 0.082),
                (floor + height * 0.405, height * 0.068, height * 0.092),
                (floor + height * 0.445, height * 0.065, height * 0.101),
                (floor + height * 0.478, height * 0.065, height * 0.105),
            ],
            material=blue_pants,
            thickness=height * 0.0035,
        )
        for side, sign in (("left", 1.0), ("right", -1.0))
    ]
    for leg, (side, _sign) in zip(legs, (("left", 1.0), ("right", -1.0))):
        mark_all_vertices(leg, f"diagnostic_pants_{side}_leg")
    gussets = []
    for side, sign in (("left", 1.0), ("right", -1.0)):
        gusset = create_trouser_gusset_half(
            f"ordinary_beth_blue_pants_{side}_gusset",
            center_x=center_x,
            center_y=center_y,
            floor=floor,
            height=height,
            side_sign=sign,
            material=blue_pants,
        )
        mark_all_vertices(gusset, f"diagnostic_pants_{side}_leg")
        gussets.append(gusset)

    shoes = [
        create_rounded_box_garment(
            f"ordinary_beth_simple_brown_shoe_{side}",
            center=(center_x + sign * height * 0.069, center_y - height * 0.060, floor + height * 0.041),
            size=(height * 0.136, height * 0.232, height * 0.094),
            material=simple_shoes,
            bevel=height * 0.018,
        )
        for side, sign in (("left", 1.0), ("right", -1.0))
    ]
    top = join_garment_parts(
        "ordinary_beth_red_short_sleeve_top",
        [torso, *sleeves],
    )
    pants = join_garment_parts(
        "ordinary_beth_blue_pants",
        [waistband, *gussets, *legs],
    )
    shoe_pair = join_garment_parts("ordinary_beth_simple_shoes", shoes)
    return [top, pants, shoe_pair, collar]


def reset_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def evaluated_coords(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def mechanical_rig_tests(
    armature: bpy.types.Object,
    body_objects: list[bpy.types.Object],
) -> tuple[dict[str, str], dict[str, dict[str, float | bool | int]]]:
    reset_pose(armature)
    rest = {obj.name: evaluated_coords(obj) for obj in body_objects}
    all_rest = [point for values in rest.values() for point in values]
    rest_extent = max(
        max(point[i] for point in all_rest) - min(point[i] for point in all_rest)
        for i in range(3)
    )

    weighted_total = 0
    vertex_total = 0
    for obj in body_objects:
        vertex_total += len(obj.data.vertices)
        weighted_total += sum(1 for vertex in obj.data.vertices if vertex.groups)
    coverage = weighted_total / max(1, vertex_total)
    results: dict[str, str] = {
        "weight_deformation": "passed" if coverage >= 0.999 else "failed"
    }
    metrics: dict[str, dict[str, float | bool | int]] = {
        "weight_deformation": {
            "weighted_vertex_count": weighted_total,
            "vertex_count": vertex_total,
            "coverage": round(coverage, 6),
        }
    }

    tests = {
        "shoulder_elbow_wrist": {
            "left_upper_arm": (math.radians(-42), 0.0, math.radians(-12)),
            "left_lower_arm": (math.radians(-28), 0.0, 0.0),
            "left_hand": (math.radians(8), 0.0, 0.0),
        },
        "hand_and_finger": {
            "left_index_01": (0.0, math.radians(42), 0.0),
            "left_middle_01": (0.0, math.radians(48), 0.0),
            "left_ring_02": (0.0, math.radians(38), 0.0),
            "right_thumb_01": (math.radians(25), 0.0, math.radians(18)),
        },
        "hip_knee_ankle": {
            "left_upper_leg": (math.radians(28), 0.0, 0.0),
            "left_lower_leg": (math.radians(-38), 0.0, 0.0),
            "left_foot": (math.radians(14), 0.0, 0.0),
        },
        "seated_pose": {
            "pelvis": (math.radians(-5), 0.0, 0.0),
            "left_upper_leg": (math.radians(-72), 0.0, 0.0),
            "right_upper_leg": (math.radians(-72), 0.0, 0.0),
            "left_lower_leg": (math.radians(68), 0.0, 0.0),
            "right_lower_leg": (math.radians(68), 0.0, 0.0),
        },
        "bed_pose": {"root": (math.radians(90), 0.0, 0.0)},
        "locomotion": {
            "left_upper_leg": (math.radians(25), 0.0, 0.0),
            "right_upper_leg": (math.radians(-25), 0.0, 0.0),
            "left_upper_arm": (math.radians(-64), 0.0, math.radians(-10)),
            "right_upper_arm": (math.radians(-64), 0.0, math.radians(-10)),
        },
    }
    for test_name, rotations in tests.items():
        reset_pose(armature)
        for bone_name, rotation in rotations.items():
            bone = armature.pose.bones.get(bone_name)
            if bone is not None:
                bone.rotation_mode = "XYZ"
                bone.rotation_euler = rotation
        bpy.context.view_layer.update()
        moved = 0
        maximum = 0.0
        finite = True
        posed_points: list[Vector] = []
        for obj in body_objects:
            posed = evaluated_coords(obj)
            posed_points.extend(posed)
            for before, after in zip(rest[obj.name], posed):
                distance = (after - before).length
                maximum = max(maximum, distance)
                if distance > 1e-5:
                    moved += 1
                finite = finite and all(math.isfinite(value) for value in after)
        posed_extent = max(
            max(point[i] for point in posed_points) - min(point[i] for point in posed_points)
            for i in range(3)
        )
        bounded = rest_extent * 0.25 <= posed_extent <= rest_extent * 2.5
        passed = finite and bounded and moved > 0 and maximum > 1e-4
        results[test_name] = "passed" if passed else "failed"
        metrics[test_name] = {
            "finite": finite,
            "bounded": bounded,
            "moved_vertex_count": moved,
            "maximum_displacement_m": round(maximum, 6),
            "posed_to_rest_extent_ratio": round(posed_extent / max(rest_extent, 1e-6), 6),
        }
    reset_pose(armature)
    return results, metrics


def create_actions(
    armature: bpy.types.Object,
    bounds_min: Vector,
    bounds_max: Vector,
) -> None:
    height = max(0.5, bounds_max.z - bounds_min.z)
    origin = (0.0, 0.0, 0.0)
    arms_down = {
        "left_upper_arm": (math.radians(-68), 0.0, 0.0),
        "right_upper_arm": (math.radians(-68), 0.0, 0.0),
        "left_lower_arm": (math.radians(-8), 0.0, 0.0),
        "right_lower_arm": (math.radians(-8), 0.0, 0.0),
    }
    action_specs = {
        "ordinary_idle": [
            (1, dict(arms_down), {"root": origin}),
            (30, {**arms_down, "chest": (math.radians(1.5), 0.0, 0.0)}, {"root": origin}),
            (60, dict(arms_down), {"root": origin}),
        ],
        "ordinary_walk": [
            (
                1,
                {
                    **arms_down,
                    "left_upper_arm": (math.radians(-66), 0.0, math.radians(-9)),
                    "right_upper_arm": (math.radians(-66), 0.0, math.radians(9)),
                    "left_upper_leg": (math.radians(13), 0.0, 0.0),
                    "right_upper_leg": (math.radians(-13), 0.0, 0.0),
                    "left_lower_leg": (math.radians(-14), 0.0, 0.0),
                    "right_lower_leg": (math.radians(5), 0.0, 0.0),
                },
                {"root": (0.0, 0.0, height * 0.006)},
            ),
            (
                18,
                {
                    **arms_down,
                    "left_upper_arm": (math.radians(-66), 0.0, math.radians(9)),
                    "right_upper_arm": (math.radians(-66), 0.0, math.radians(-9)),
                    "left_upper_leg": (math.radians(-13), 0.0, 0.0),
                    "right_upper_leg": (math.radians(13), 0.0, 0.0),
                    "left_lower_leg": (math.radians(5), 0.0, 0.0),
                    "right_lower_leg": (math.radians(-14), 0.0, 0.0),
                },
                {"root": (0.0, 0.0, height * 0.012)},
            ),
            (
                36,
                {
                    **arms_down,
                    "left_upper_arm": (math.radians(-66), 0.0, math.radians(-9)),
                    "right_upper_arm": (math.radians(-66), 0.0, math.radians(9)),
                    "left_upper_leg": (math.radians(13), 0.0, 0.0),
                    "right_upper_leg": (math.radians(-13), 0.0, 0.0),
                    "left_lower_leg": (math.radians(-14), 0.0, 0.0),
                    "right_lower_leg": (math.radians(5), 0.0, 0.0),
                },
                {"root": (0.0, 0.0, height * 0.006)},
            ),
        ],
        "ordinary_sit": [
            (1, dict(arms_down), {"root": origin}),
            (
                35,
                {
                    **arms_down,
                    "pelvis": (math.radians(-3), 0.0, 0.0),
                    "spine": (math.radians(4), 0.0, 0.0),
                    "left_upper_leg": (math.radians(-70), 0.0, 0.0),
                    "right_upper_leg": (math.radians(-70), 0.0, 0.0),
                    "left_lower_leg": (math.radians(72), 0.0, 0.0),
                    "right_lower_leg": (math.radians(72), 0.0, 0.0),
                    "left_lower_arm": (math.radians(-24), 0.0, 0.0),
                    "right_lower_arm": (math.radians(-24), 0.0, 0.0),
                },
                {
                    "root": (
                        0.0,
                        height * 0.028,
                        -height * 0.175,
                    )
                },
            ),
        ],
        "ordinary_reach": [
            (1, dict(arms_down), {"root": origin}),
            (
                30,
                {
                    **arms_down,
                    "right_upper_arm": (
                        math.radians(-32),
                        0.0,
                        math.radians(48),
                    ),
                    "right_lower_arm": (math.radians(-42), 0.0, 0.0),
                },
                {"root": origin},
            ),
            (60, dict(arms_down), {"root": origin}),
        ],
    }
    armature.animation_data_create()
    for action_name, frames in action_specs.items():
        action = bpy.data.actions.new(action_name)
        action.use_fake_user = True
        armature.animation_data.action = action
        reset_pose(armature)
        for frame, pose, locations in frames:
            reset_pose(armature)
            for bone_name, rotation in pose.items():
                bone = armature.pose.bones.get(bone_name)
                if bone:
                    bone.rotation_mode = "XYZ"
                    bone.rotation_euler = rotation
            for bone_name, location in locations.items():
                bone = armature.pose.bones.get(bone_name)
                if bone:
                    bone.location = location
            for bone in armature.pose.bones:
                bone.keyframe_insert("rotation_euler", frame=frame, group=bone.name)
                bone.keyframe_insert("location", frame=frame, group=bone.name)
        reset_pose(armature)
    armature.animation_data.action = None


def export_selected(path: Path, objects: list[bpy.types.Object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
        export_yup=True,
        export_morph=False,
        export_extras=True,
    )


def main() -> None:
    args = parse_args()
    # This check is intentionally inside the Blender worker and happens before
    # scene mutation, import, directory creation, or artifact writes.  A direct
    # invocation cannot use a crafted project root or output escape to bypass
    # the wrapper's preflight.
    authorization = authorize_adult_reference_worker_request(
        args.request,
        project_root=TRUSTED_PROJECT_ROOT,
        expected_request_sha256=args.validated_request_sha256,
    )
    request_path = authorization["request_path"]
    request = authorization["request"]
    authorized_request_sha256 = authorization["request_sha256"]
    project_root = authorization["trusted_project_root"]
    source_path = project_path(request["source"]["path"], project_root)
    expected_source_hash = str(request["source"]["expected_sha256"]).lower()
    if sha256_file(source_path) != expected_source_hash:
        raise ValueError("source hash changed after preflight")
    outputs = request["outputs"]
    body_output = project_path(outputs["body_glb"], project_root)
    hair_output = project_path(outputs["hair_glb"], project_root)
    eyes_output = project_path(outputs["eyes_glb"], project_root)
    clothes_output = project_path(outputs["clothes_glb"], project_root)
    review_output = project_path(outputs["clothed_review_glb"], project_root)
    evidence_output = project_path(outputs["build_evidence"], project_root)
    rig_output = project_path(outputs["rig_attestation"], project_root)
    attribution_output = project_path(outputs["attribution"], project_root)

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source_path))
    imported_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    role_binding = request["policy_evidence"]["source_role_map_evidence"]
    role_path = project_path(role_binding["path"], project_root)
    if sha256_file(role_path) != str(role_binding["sha256"]).lower():
        raise ValueError("source role-map evidence changed after preflight")
    role_evidence = json.loads(role_path.read_text(encoding="utf-8"))
    license_binding = request["policy_evidence"]["license_evidence"]
    license_path = project_path(license_binding["path"], project_root)
    if sha256_file(license_path) != str(license_binding["sha256"]).lower():
        raise ValueError("license evidence changed after preflight")
    license_evidence = json.loads(license_path.read_text(encoding="utf-8"))
    verified_license_id = str(license_evidence["license"]["id"])
    role_materials: dict[str, set[str]] = {
        "discard": set(),
        "body": set(),
        "hair": set(),
        "eyes": set(),
    }
    for record in role_evidence["verified_source_roles"]:
        token = re.sub(r"[^a-z0-9]+", "", str(record["source_material"]).lower())
        role = str(record["candidate_role"])
        if role == "duplicate_outline_shells":
            role_materials["discard"].add(token)
        elif role in {"licensed_adult_body_surface", "licensed_head_and_face_surfaces"}:
            role_materials["body"].add(token)
        elif role == "licensed_hair_surface":
            role_materials["hair"].add(token)
        elif role == "licensed_eye_surface":
            role_materials["eyes"].add(token)
        else:
            raise ValueError("unrecognized source role-map entry")
    discarded: list[bpy.types.Object] = []
    body_objects: list[bpy.types.Object] = []
    hair_objects: list[bpy.types.Object] = []
    eye_objects: list[bpy.types.Object] = []
    observed_role_counts: dict[str, int] = {}
    for obj in imported_meshes:
        tokens = material_tokens(obj)
        if len(tokens) != 1:
            raise ValueError("source mesh must have one exact audited material role")
        if tokens & role_materials["discard"]:
            discarded.append(obj)
            role_name = "discard"
        elif tokens & role_materials["eyes"]:
            eye_objects.append(obj)
            role_name = "eyes"
        elif tokens & role_materials["hair"]:
            hair_objects.append(obj)
            role_name = "hair"
        elif tokens & role_materials["body"]:
            body_objects.append(obj)
            role_name = "body_surface"
        else:
            raise ValueError("source mesh material is not present in exact role-map evidence")
        material_name_hash = hashlib.sha256(next(iter(tokens)).encode("utf-8")).hexdigest()
        observed_role_counts[f"{role_name}:{material_name_hash}"] = (
            observed_role_counts.get(f"{role_name}:{material_name_hash}", 0) + 1
        )
    if not body_objects or not hair_objects or not eye_objects:
        raise ValueError("source role classification did not produce body, hair, and eye parts")
    expected_counts = request["derivative_plan"].get("expected_component_counts", {})
    actual_counts = {
        "discard": len(discarded),
        "body_surface": len(body_objects),
        "hair": len(hair_objects),
        "eyes": len(eye_objects),
    }
    if expected_counts and any(int(expected_counts.get(key, -1)) != value for key, value in actual_counts.items()):
        raise ValueError("exact source component classification changed; review required")
    for obj in discarded:
        bpy.data.objects.remove(obj, do_unlink=True)
    retained = [*body_objects, *hair_objects, *eye_objects]
    for obj in retained:
        apply_world_transform(obj)

    source_surface_fingerprint = topology_fingerprint(body_objects)
    source_vertex_count = sum(len(obj.data.vertices) for obj in body_objects)
    source_face_count = sum(len(obj.data.polygons) for obj in body_objects)
    bounds_min, bounds_max = aggregate_bounds(retained)
    body_bounds_min, body_bounds_max = aggregate_bounds(body_objects)
    candidate_id = request["candidate_id"]
    armature = create_armature(bounds_min, bounds_max, candidate_id)

    neutral_skin = make_material("ordinary_beth_private_neutral_skin", (0.89, 0.64, 0.51, 1.0), 0.72)
    blonde_hair = make_material("ordinary_beth_blonde_hair", (0.78, 0.60, 0.20, 1.0), 0.58)
    neutral_eyes = make_material("ordinary_beth_neutral_eyes", (0.92, 0.94, 0.90, 1.0), 0.38)
    red_top = make_material("ordinary_beth_red_collared_top", (0.62, 0.055, 0.045, 1.0), 0.7)
    blue_pants = make_material("ordinary_beth_blue_pants", (0.08, 0.22, 0.52, 1.0), 0.72)
    simple_shoes = make_material("ordinary_beth_simple_brown_shoes", (0.24, 0.105, 0.045, 1.0), 0.58)
    for index, obj in enumerate(body_objects, start=1):
        obj.name = f"{candidate_id}_body_surface_{index:02d}"
        set_single_material(obj, neutral_skin)
    for index, obj in enumerate(hair_objects, start=1):
        obj.name = f"{candidate_id}_ordinary_blonde_hair_{index:02d}"
        set_single_material(obj, blonde_hair)
    for index, obj in enumerate(eye_objects, start=1):
        obj.name = f"{candidate_id}_eyes_{index:02d}"
        set_single_material(obj, neutral_eyes)

    clothes_objects = create_ordinary_outfit_volumes(
        body_bounds_min=body_bounds_min,
        body_bounds_max=body_bounds_max,
        overall_bounds_max=bounds_max,
        red_top=red_top,
        blue_pants=blue_pants,
        simple_shoes=simple_shoes,
    )

    skinning_metrics = {}
    for obj in body_objects:
        skinning_metrics[obj.name] = skin_object(obj, armature, bounds_min, bounds_max)
    for obj in hair_objects:
        skinning_metrics[obj.name] = skin_object(obj, armature, bounds_min, bounds_max, rigid_head=True)
    for obj in eye_objects:
        skinning_metrics[obj.name] = skin_object(obj, armature, bounds_min, bounds_max, rigid_head=True)
    clothing_profiles = {
        "ordinary_beth_red_short_sleeve_top": "shirt",
        "ordinary_beth_blue_pants": "pants",
        "ordinary_beth_simple_shoes": "shoes",
        "ordinary_beth_red_crew_collar": "collar",
    }
    for obj in clothes_objects:
        skinning_metrics[obj.name] = skin_object(
            obj,
            armature,
            bounds_min,
            bounds_max,
            skinning_profile=clothing_profiles.get(obj.name, "body"),
        )

    candidate_surface_fingerprint = topology_fingerprint(body_objects)
    if candidate_surface_fingerprint != source_surface_fingerprint:
        raise ValueError("shape-preserving body topology changed before export")
    test_results, test_metrics = mechanical_rig_tests(
        armature, [*body_objects, *hair_objects, *eye_objects, *clothes_objects]
    )
    create_actions(armature, bounds_min, bounds_max)
    shared_rig_signature = rig_signature(armature)

    attribution = request["source"]["attribution"]
    for key, value in {
        "source_title": attribution["title"],
        "source_author": attribution["author"],
        "source_url": attribution["source_url"],
        "license_id": verified_license_id,
        "license_url": attribution["license_url"],
        "adaptation_notice": "Outline shells/materials removed; canonical rig/weights and separate ordinary clothing authored.",
        "ordinary_variant_only": True,
        "diagnostic_motion_revision": "r6_in_place_walk_supported_seat",
        "walk_root_translation_xy_m": 0.0,
        "walk_ground_contact_proven": False,
        "seat_contact_proven": False,
        "shared_rig_signature": shared_rig_signature,
        "runtime_activation_allowed": False,
    }.items():
        armature[key] = value
    body_export_objects = [armature, *body_objects]
    hair_export_objects = [armature, *hair_objects]
    eyes_export_objects = [armature, *eye_objects]
    clothes_export_objects = [armature, *clothes_objects]
    review_export_objects = [armature, *body_objects, *hair_objects, *eye_objects, *clothes_objects]
    export_selected(body_output, body_export_objects)
    export_selected(hair_output, hair_export_objects)
    export_selected(eyes_output, eyes_export_objects)
    export_selected(clothes_output, clothes_export_objects)
    export_selected(review_output, review_export_objects)

    body_hash = sha256_file(body_output)
    hair_hash = sha256_file(hair_output)
    eyes_hash = sha256_file(eyes_output)
    clothes_hash = sha256_file(clothes_output)
    review_hash = sha256_file(review_output)
    rig_attestation = {
        "schema_version": 1,
        "artifact_sha256": body_hash,
        "exact_artifact_hash_verified": True,
        "review_status": "provisional_smoke_only_not_stable_rig_proof",
        "reviewed_by": "deterministic_blender_mechanical_validator_v1",
        "reviewed_at": now_iso(),
        "review_scope": "non-rendering finite/bounded deformation smoke tests only; stable working rig not proven",
        "test_results": {
            name: "not_proven_visual_and_behavioral_validation_pending"
            for name in (
                "weight_deformation",
                "shoulder_elbow_wrist",
                "hand_and_finger",
                "hip_knee_ankle",
                "seated_pose",
                "bed_pose",
                "locomotion",
            )
        },
        "mechanical_smoke_results": test_results,
        "mechanical_smoke_metrics": test_metrics,
        "shared_rig_signature": shared_rig_signature,
        "stable_working_rig_proven": False,
        "visual_deformation_quality_proven": False,
        "identity_likeness_proven": False,
        "foot_contact_and_sliding_proven": False,
        "garment_penetration_and_detachment_proven": False,
        "collision_safe_locomotion_proven": False,
        "complete_exported_lie_rise_turn_stop_action_set": False,
        "runtime_activation_allowed": False,
    }
    evidence = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "subject_id": request["subject_id"],
        "variant": request["variant"],
        "created_at": now_iso(),
        "artifact_bindings": {
            "request_sha256": authorized_request_sha256,
            "source_sha256": expected_source_hash,
            "body_sha256": body_hash,
            "hair_sha256": hair_hash,
            "eyes_sha256": eyes_hash,
            "clothes_sha256": clothes_hash,
            "clothed_review_sha256": review_hash,
        },
        "license_id": verified_license_id,
        "policy_evidence_sha256": {
            key: str(value["sha256"]).lower()
            for key, value in request["policy_evidence"].items()
        },
        "source_role_map_evidence_sha256": str(role_binding["sha256"]).lower(),
        "observed_source_role_material_hash_counts": observed_role_counts,
        "licensed_source_surface_incorporated": True,
        "source_surface_shape_preserved": candidate_surface_fingerprint == source_surface_fingerprint,
        "source_surface_topology_fingerprint": source_surface_fingerprint,
        "candidate_surface_topology_fingerprint": candidate_surface_fingerprint,
        "source_body_vertex_count": source_vertex_count,
        "candidate_body_vertex_count": sum(len(obj.data.vertices) for obj in body_objects),
        "source_body_face_count": source_face_count,
        "candidate_body_face_count": sum(len(obj.data.polygons) for obj in body_objects),
        "discarded_duplicate_outline_mesh_count": len(discarded),
        "source_artifact_byte_copied": False,
        "new_body_surface_authored": False,
        "reference_surface_mesh_incorporated": True,
        "source_materials_and_textures_exported": False,
        "source_space_labelled_common_body_component_incorporated": True,
        "space_beth_material_or_outfit_exported": False,
        "ordinary_variant_only": True,
        "new_rig_and_skinning_authored": True,
        "body_hair_eyes_and_clothes_are_separate_artifacts": True,
        "generated_ordinary_clothing": [
            "red_short_sleeve_collared_top",
            "blue_fitted_diagnostic_waistband_and_split_leg_trousers",
            "simple_brown_shoes",
        ],
        "diagnostic_motion_revision": "r6_in_place_walk_supported_seat",
        "grounded_walk_contact_proven": False,
        "supported_seat_contact_proven": False,
        "rig_bone_count": len(armature.data.bones),
        "shared_rig_signature": shared_rig_signature,
        "skinning_metrics": skinning_metrics,
        "mechanical_test_results": test_results,
        "stable_working_rig_proven": False,
        "facial_control_inventory": {
            "morph_target_count": 0,
            "jaw_control": False,
            "eye_look_controls": False,
            "blink_controls": False,
            "viseme_or_lip_sync_controls": False,
        },
        "heuristic_weighting_and_rig_placement": True,
        "visual_review_required": True,
        "renders_created": False,
        "intimate_render_retained": False,
        "runtime_activation_allowed": False,
    }
    attribution_record = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "source_title": attribution["title"],
        "source_author": attribution["author"],
        "source_url": attribution["source_url"],
        "license_id": verified_license_id,
        "license_url": attribution["license_url"],
        "changes": [
            "discarded duplicate outline shells",
            "removed all source materials and textures including Space-labelled material",
            "authored canonical humanoid/finger rig and deterministic weights",
            "generated separate ordinary red collared top, fitted opaque diagnostic blue trousers, and simple brown shoes",
            "replaced the rigid hip box with a waistband and separately weighted left/right trouser envelopes",
            "added in-place walk and lowered seated diagnostic actions without claiming contact or stability",
            "exported separate body, hair, eyes, clothing, and clothed-review assembly artifacts",
        ],
        "public_distribution_reviewed": False,
        "runtime_activation_allowed": False,
    }
    attribution_output.parent.mkdir(parents=True, exist_ok=True)
    attribution_output.write_text(json.dumps(attribution_record, indent=2), encoding="utf-8")
    evidence["artifact_bindings"]["attribution_sha256"] = sha256_file(attribution_output)
    for path, payload in (
        (rig_output, rig_attestation),
        (evidence_output, evidence),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": "worker_complete", "candidate_id": candidate_id, "tests": test_results}))


if __name__ == "__main__":
    main()
