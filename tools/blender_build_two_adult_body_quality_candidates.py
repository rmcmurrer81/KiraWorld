"""Build two clothed, inactive adult Avatar Builder review candidates.

This Blender worker adapts the exact CC-BY-4.0 471903 adult cage for Kira
and adult Earth-65 Gwen.  It is deliberately a review lane: it never writes a
live model, never retains an unclothed render, and never releases an approval
or autobuild gate.  The worker records exact source lineage plus per-vertex
deformation deltas so a candidate cannot be mistaken for an unmodified copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree


HEAD = "Head_033"
LEFT_ARM = "Arm.L_014"
LEFT_FOREARM = "ForeArm.L_015"
LEFT_HAND = "Hand.L_016"
RIGHT_ARM = "Arm.R_035"
RIGHT_FOREARM = "ForeArm.R_036"
RIGHT_HAND = "Hand.R_037"
LEFT_THIGH = "UpLeg.L_02"
LEFT_SHIN = "Leg.L_03"
LEFT_FOOT = "Foot.L_04"
RIGHT_THIGH = "UpLeg.R_06"
RIGHT_SHIN = "Leg.R_07"
RIGHT_FOOT = "Foot.R_08"

SOURCE_PROVENANCE = {
    "title": "Base Female - Game Ready - Rigged - Low Poly",
    "author": "arte_art",
    "author_url": "https://sketchfab.com/arte_art",
    "source_url": (
        "https://sketchfab.com/3d-models/"
        "base-female-game-ready-rigged-low-poly-5fcef75a94be4ee3a996a0ea91106e4d"
    ),
    "license_id": "CC-BY-4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
}

SUBJECTS = {
    "kira": {
        "label": "Kira",
        "candidate_revision": "adult_quality_r4",
        "identity_evidence": "provisional_identity_waiver_no_exact_likeness_refs",
        "fit_basis": "Robert's thinner-body request plus a smooth adult silhouette envelope",
        "hair": (0.075, 0.035, 0.020, 1.0),
        "iris": (0.20, 0.065, 0.018, 1.0),
        "top": (0.025, 0.28, 0.33, 1.0),
        "leggings": (0.035, 0.045, 0.060, 1.0),
        "shoes": (0.20, 0.075, 0.030, 1.0),
        "controls": [
            (0.00, 0.98, 0.98),
            (0.10, 0.94, 0.96),
            (0.24, 0.92, 0.95),
            (0.38, 0.92, 0.94),
            (0.50, 0.86, 0.90),
            (0.58, 0.84, 0.89),
            (0.68, 0.89, 0.93),
            (0.77, 0.92, 0.95),
            (0.86, 0.97, 0.98),
            (1.00, 0.98, 0.98),
        ],
    },
    "gwen": {
        "label": "Gwen (adult Earth-65 review)",
        "candidate_revision": "adult_athletic_quality_r4",
        "identity_evidence": "reference_only_proportions_not_owner_reviewed_likeness",
        "fit_basis": (
            "smooth athletic dancer/superhero envelope informed by the enrolled "
            "reference-only Gwen proportion study"
        ),
        "hair": (0.86, 0.80, 0.64, 1.0),
        "iris": (0.20, 0.34, 0.46, 1.0),
        "top": (0.86, 0.80, 0.90, 1.0),
        "leggings": (0.11, 0.14, 0.20, 1.0),
        "shoes": (0.86, 0.18, 0.47, 1.0),
        "controls": [
            (0.00, 0.99, 0.99),
            (0.10, 0.99, 1.00),
            (0.24, 1.02, 1.02),
            (0.38, 1.03, 1.02),
            (0.50, 0.92, 0.95),
            (0.58, 0.91, 0.95),
            (0.68, 0.98, 0.99),
            (0.77, 1.035, 1.015),
            (0.86, 0.98, 0.98),
            (1.00, 0.98, 0.98),
        ],
    },
}

# glTF import may express its neutral coordinate conversion in pose-bone basis
# matrices.  Replacing those matrices with identity rotates/deforms this exact
# source, so each subject restores the captured imported neutral basis.
NEUTRAL_POSE_MATRICES: dict[str, dict[str, Matrix]] = {}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for blocks in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.curves,
    ):
        for block in list(blocks):
            if block.users == 0:
                blocks.remove(block)


def project_relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.65,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return material


def set_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True


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


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def vec(value: Vector) -> list[float]:
    return [round(float(component), 6) for component in value]


def role_for(obj: bpy.types.Object) -> str:
    token = f"{obj.name} {obj.data.name}".lower()
    for role in ("hair_extra", "body", "clothes", "eyes", "hair", "mouth"):
        if role in token:
            return role
    if len(obj.data.vertices) == 5909:
        return "body"
    if len(obj.data.vertices) == 698:
        return "clothes"
    if len(obj.data.vertices) == 226:
        return "eyes"
    if len(obj.data.vertices) == 5585:
        return "hair"
    if len(obj.data.vertices) == 392:
        return "hair_extra"
    if len(obj.data.vertices) == 1884:
        return "mouth"
    return "helper"


def classify_scene() -> tuple[dict[str, list[bpy.types.Object]], bpy.types.Object]:
    roles: dict[str, list[bpy.types.Object]] = {
        key: [] for key in ("body", "clothes", "eyes", "hair", "hair_extra", "mouth", "helper")
    }
    for obj in [item for item in bpy.context.scene.objects if item.type == "MESH"]:
        roles[role_for(obj)].append(obj)
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1 or len(roles["body"]) != 1 or len(roles["eyes"]) != 1:
        raise ValueError("exact 471903 component classification changed")
    return roles, armatures[0]


def interpolate_controls(controls: list[tuple[float, float, float]], height_norm: float) -> tuple[float, float]:
    value = min(1.0, max(0.0, height_norm))
    for index in range(len(controls) - 1):
        left, right = controls[index], controls[index + 1]
        if left[0] <= value <= right[0]:
            t = (value - left[0]) / max(1e-9, right[0] - left[0])
            t = t * t * (3.0 - 2.0 * t)
            return (
                left[1] + (right[1] - left[1]) * t,
                left[2] + (right[2] - left[2]) * t,
            )
    return controls[-1][1], controls[-1][2]


def make_warp(
    body_low: Vector,
    body_high: Vector,
    controls: list[tuple[float, float, float]],
):
    """Return a cage warp in the source's *authoring* coordinate system.

    The licensed glTF stores its undeformed mesh cage Y-up (X is lateral and
    Z is depth).  The imported neutral armature pose converts the evaluated
    result to Blender's Z-up review space.  Treating the raw cage as Z-up was
    the cause of the rejected 05:39 render: depth bands were mistaken for
    body-height bands.  Keep these two spaces explicit and never infer them
    from a combined assembly bound.
    """

    center_x = (body_low.x + body_high.x) * 0.5
    center_depth = (body_low.z + body_high.z) * 0.5
    height = body_high.y - body_low.y

    def warp(point: Vector) -> Vector:
        height_norm = (point.y - body_low.y) / max(height, 1e-9)
        scale_x, scale_depth = interpolate_controls(controls, height_norm)
        # A continuous envelope avoids hard band seams and uncontrolled bumps.
        return Vector(
            (
                center_x + (point.x - center_x) * scale_x,
                point.y,
                center_depth + (point.z - center_depth) * scale_depth,
            )
        )

    return warp


def point_fingerprint(points: list[Vector]) -> str:
    payload = [tuple(round(float(value), 7) for value in point) for point in points]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def delta_stats(before: list[Vector], after: list[Vector]) -> dict[str, object]:
    values = sorted((left - right).length for left, right in zip(after, before))
    count = len(values)

    def percentile(ratio: float) -> float:
        return values[min(count - 1, max(0, round((count - 1) * ratio)))] if values else 0.0

    return {
        "vertex_count": count,
        "moved_vertex_count_over_1e_6_m": sum(value > 0.000001 for value in values),
        "moved_vertex_fraction": round(sum(value > 0.000001 for value in values) / max(1, count), 6),
        "mean_delta_m": round(sum(values) / max(1, count), 7),
        "rms_delta_m": round(math.sqrt(sum(value * value for value in values) / max(1, count)), 7),
        "p50_delta_m": round(percentile(0.50), 7),
        "p95_delta_m": round(percentile(0.95), 7),
        "maximum_delta_m": round(max(values, default=0.0), 7),
        "source_world_point_fingerprint": point_fingerprint(before),
        "candidate_world_point_fingerprint": point_fingerprint(after),
        "point_fingerprints_differ": point_fingerprint(before) != point_fingerprint(after),
    }


def warp_mesh(obj: bpy.types.Object, warp) -> dict[str, object]:
    before = mesh_world_points(obj)
    inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        vertex.co = inverse @ warp(obj.matrix_world @ vertex.co)
    obj.data.update()
    after = mesh_world_points(obj)
    return delta_stats(before, after)


def warp_armature(armature: bpy.types.Object, warp) -> dict[str, object]:
    world = armature.matrix_world.copy()
    inverse = world.inverted()
    before: list[Vector] = []
    after: list[Vector] = []
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in armature.data.edit_bones:
        head_world = world @ bone.head
        tail_world = world @ bone.tail
        before.extend((head_world.copy(), tail_world.copy()))
        bone.head = inverse @ warp(head_world)
        bone.tail = inverse @ warp(tail_world)
        after.extend((world @ bone.head, world @ bone.tail))
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.select_set(False)
    return delta_stats(before, after)


def unchanged_armature_stats(armature: bpy.types.Object) -> dict[str, object]:
    """Record that the licensed inverse-bind/rest rig was intentionally fixed."""

    world = armature.matrix_world.copy()
    points = [
        point
        for bone in armature.data.bones
        for point in (world @ bone.head_local, world @ bone.tail_local)
    ]
    result = delta_stats(points, [point.copy() for point in points])
    result["rest_rig_intentionally_preserved"] = True
    result["reason"] = (
        "moving imported rest bones without recomputing the exact inverse-bind relationship "
        "failed visual deformation; the licensed 54-bone rest rig is retained for this cage-fit pass"
    )
    return result


def silhouette_metrics(body: bpy.types.Object, low: Vector, high: Vector) -> dict[str, object]:
    points = mesh_world_points(body)
    height = high.y - low.y
    result: dict[str, object] = {}
    for name, center in (("hip", 0.42), ("waist", 0.54), ("chest", 0.66), ("shoulder", 0.76)):
        samples = [
            point.x
            for point in points
            if abs(((point.y - low.y) / max(height, 1e-9)) - center) <= 0.018
        ]
        samples.sort()
        if len(samples) >= 4:
            left = samples[round((len(samples) - 1) * 0.03)]
            right = samples[round((len(samples) - 1) * 0.97)]
            result[name] = {
                "authoring_y_up_height_norm": center,
                "robust_width_m": round(right - left, 6),
                "sample_count": len(samples),
            }
    return result


def weighted_coverage(obj: bpy.types.Object) -> dict[str, object]:
    weighted = sum(1 for vertex in obj.data.vertices if vertex.groups)
    return {
        "vertex_count": len(obj.data.vertices),
        "weighted_vertex_count": weighted,
        "coverage": round(weighted / max(1, len(obj.data.vertices)), 6),
    }


def boundary_edge_count(mesh: bpy.types.Mesh) -> int:
    uses: dict[tuple[int, int], int] = {}
    for polygon in mesh.polygons:
        indices = [int(value) for value in polygon.vertices]
        for index, first in enumerate(indices):
            edge = tuple(sorted((first, indices[(index + 1) % len(indices)])))
            uses[edge] = uses.get(edge, 0) + 1
    return sum(value == 1 for value in uses.values())


def average_group_weight(
    source: bpy.types.Object,
    polygon: bpy.types.MeshPolygon,
    names: set[str],
) -> float:
    wanted = {group.index for group in source.vertex_groups if group.name in names}
    total = 0.0
    for vertex_index in polygon.vertices:
        total += sum(
            float(item.weight)
            for item in source.data.vertices[vertex_index].groups
            if item.group in wanted
        )
    return total / max(1, len(polygon.vertices))


def polygon_world_centroid(
    source: bpy.types.Object,
    polygon: bpy.types.MeshPolygon,
) -> Vector:
    """Compute a fresh centroid from vertices instead of stale polygon.center.

    Blender's imported polygon centers can remain cached in the source glTF's
    pre-conversion space after cage edits.  Wardrobe selection must follow the
    current raw Y-up cage, so derive the centroid directly from vertex data.
    """

    return sum(
        (source.matrix_world @ source.data.vertices[index].co for index in polygon.vertices),
        Vector((0.0, 0.0, 0.0)),
    ) / max(1, len(polygon.vertices))


def create_surface_piece(
    *,
    name: str,
    source: bpy.types.Object,
    armature: bpy.types.Object,
    selected: list[bpy.types.MeshPolygon],
    material: bpy.types.Material,
    offset: float,
    thickness: float,
) -> tuple[bpy.types.Object, dict[str, object]]:
    if not selected:
        raise ValueError(f"empty wardrobe selection for {name}")
    source_indices = sorted({int(index) for polygon in selected for index in polygon.vertices})
    mapping = {old: new for new, old in enumerate(source_indices)}
    imported_scale = sum(abs(value) for value in source.matrix_world.to_scale()) / 3.0
    local_offset = offset / max(imported_scale, 1e-9)
    local_thickness = thickness / max(imported_scale, 1e-9)
    vertices = [
        tuple(source.data.vertices[index].co + source.data.vertices[index].normal * local_offset)
        for index in source_indices
    ]
    faces = [tuple(mapping[int(index)] for index in polygon.vertices) for polygon in selected]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    piece = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(piece)
    groups = {
        group.name: piece.vertex_groups.new(name=group.name) for group in source.vertex_groups
    }
    for old_index, new_index in mapping.items():
        for membership in source.data.vertices[old_index].groups:
            source_group = source.vertex_groups[membership.group]
            groups[source_group.name].add([new_index], float(membership.weight), "REPLACE")
    set_material(piece, material)
    before_solidify_boundary_edges = boundary_edge_count(mesh)
    solidify = piece.modifiers.new(name="closed_opaque_shell", type="SOLIDIFY")
    solidify.thickness = local_thickness
    solidify.offset = 0.0
    solidify.use_rim = True
    solidify.use_quality_normals = True
    bpy.context.view_layer.objects.active = piece
    piece.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    piece.select_set(False)
    modifier = piece.modifiers.new(name="shared_adult_rig", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    piece.parent = source.parent
    piece.parent_type = source.parent_type
    piece.matrix_parent_inverse = source.matrix_parent_inverse.copy()
    piece.matrix_basis = source.matrix_basis.copy()
    # Preserve the source mesh's exact object-to-armature bind transform.  The
    # copied local coordinates and weights are only valid in this matrix.
    piece.matrix_world = source.matrix_world.copy()
    piece["separate_shareable_wardrobe_component"] = True
    piece["private_clothed_review_only"] = True
    piece["runtime_activation_allowed"] = False
    return piece, {
        "name": name,
        "source_face_count": len(selected),
        "closed_face_count": len(mesh.polygons),
        "boundary_edges_before_solidify": before_solidify_boundary_edges,
        "boundary_edges_after_solidify": boundary_edge_count(mesh),
        "closed_shell_mechanical_check": boundary_edge_count(mesh) == 0,
        "weight_coverage": weighted_coverage(piece),
        "requested_world_offset_m": offset,
        "requested_world_thickness_m": thickness,
    }


def ring_shell_geometry(
    rings: list[tuple[float, float, float, float, float]],
    *,
    segments: int = 32,
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    """Build an independent open garment shell in raw Y-up authoring space.

    Ring tuples are ``(y, center_x, center_z, radius_x, radius_z)``.  A later
    Solidify pass supplies thickness and watertight rims without copying body
    polygons or reproducing intimate surface contours.
    """

    vertices: list[Vector] = []
    for y, center_x, center_z, radius_x, radius_z in rings:
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append(
                Vector(
                    (
                        center_x + math.cos(angle) * radius_x,
                        y,
                        center_z + math.sin(angle) * radius_z,
                    )
                )
            )
    faces: list[tuple[int, ...]] = []
    for ring_index in range(len(rings) - 1):
        left = ring_index * segments
        right = (ring_index + 1) * segments
        for index in range(segments):
            following = (index + 1) % segments
            faces.append((left + index, left + following, right + following, right + index))
    return vertices, faces


def ellipsoid_geometry(
    center: Vector,
    radii: Vector,
    *,
    segments: int = 32,
    latitude_rings: int = 12,
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    """Build a closed Y-up ellipsoid used as a conservative shoe last."""

    vertices = [center + Vector((0.0, radii.y, 0.0))]
    for latitude in range(1, latitude_rings):
        phi = math.pi * latitude / latitude_rings
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append(
                center
                + Vector(
                    (
                        radii.x * math.sin(phi) * math.cos(angle),
                        radii.y * math.cos(phi),
                        radii.z * math.sin(phi) * math.sin(angle),
                    )
                )
            )
    bottom = len(vertices)
    vertices.append(center - Vector((0.0, radii.y, 0.0)))
    faces: list[tuple[int, ...]] = []
    first_ring = 1
    for index in range(segments):
        following = (index + 1) % segments
        faces.append((0, first_ring + following, first_ring + index))
    for latitude in range(latitude_rings - 2):
        current = 1 + latitude * segments
        following_ring = current + segments
        for index in range(segments):
            following = (index + 1) % segments
            faces.append(
                (
                    current + index,
                    current + following,
                    following_ring + following,
                    following_ring + index,
                )
            )
    final_ring = 1 + (latitude_rings - 2) * segments
    for index in range(segments):
        following = (index + 1) % segments
        faces.append((final_ring + index, final_ring + following, bottom))
    return vertices, faces


def box_geometry(low: Vector, high: Vector) -> tuple[list[Vector], list[tuple[int, ...]]]:
    """Build a closed authoring-space box for a conservative shoe last."""

    vertices = [
        Vector((x, y, z))
        for y in (low.y, high.y)
        for z in (low.z, high.z)
        for x in (low.x, high.x)
    ]
    # Index layout: y layer, then z row, then x column.
    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    return vertices, faces


def combine_geometry(
    parts: list[tuple[list[Vector], list[tuple[int, ...]]]],
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices: list[Vector] = []
    faces: list[tuple[int, ...]] = []
    for part_vertices, part_faces in parts:
        offset = len(vertices)
        vertices.extend(part_vertices)
        faces.extend(tuple(index + offset for index in face) for face in part_faces)
    return vertices, faces


def bind_parametric_piece(
    *,
    name: str,
    source: bpy.types.Object,
    armature: bpy.types.Object,
    world_vertices: list[Vector],
    faces: list[tuple[int, ...]],
    material: bpy.types.Material,
    thickness: float,
    rigid_group: str | None = None,
    weight_resolver=None,
    bevel_world_m: float = 0.0,
    subdivision_level: int = 0,
) -> tuple[bpy.types.Object, dict[str, object]]:
    """Author a separate garment and transfer only deformation weights.

    Geometry is independent and parametric.  Nearest-body lookup copies skin
    weights, never source surface positions/faces, so the garment remains a
    separate shareable component instead of a second skin.
    """

    inverse = source.matrix_world.inverted()
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(inverse @ point) for point in world_vertices], [], faces)
    mesh.update()
    piece = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(piece)
    piece.matrix_world = source.matrix_world.copy()
    set_material(piece, material)
    boundary_before = boundary_edge_count(mesh)
    if thickness > 0.0:
        imported_scale = sum(abs(value) for value in source.matrix_world.to_scale()) / 3.0
        solidify = piece.modifiers.new(name="closed_opaque_parametric_shell", type="SOLIDIFY")
        solidify.thickness = thickness / max(imported_scale, 1e-9)
        solidify.offset = 0.0
        solidify.use_rim = True
        solidify.use_quality_normals = True
        bpy.context.view_layer.objects.active = piece
        piece.select_set(True)
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        piece.select_set(False)
    if bevel_world_m > 0.0:
        imported_scale = sum(abs(value) for value in source.matrix_world.to_scale()) / 3.0
        bevel = piece.modifiers.new(name="closed_shoe_last_bevel", type="BEVEL")
        bevel.width = bevel_world_m / max(imported_scale, 1e-9)
        bevel.segments = 3
        bevel.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = piece
        piece.select_set(True)
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        piece.select_set(False)
    if subdivision_level > 0:
        subdivision = piece.modifiers.new(name="continuous_garment_subdivision", type="SUBSURF")
        subdivision.subdivision_type = "CATMULL_CLARK"
        subdivision.levels = subdivision_level
        subdivision.render_levels = subdivision_level
        bpy.context.view_layer.objects.active = piece
        piece.select_set(True)
        bpy.ops.object.modifier_apply(modifier=subdivision.name)
        piece.select_set(False)
    for polygon in piece.data.polygons:
        polygon.use_smooth = True

    if rigid_group:
        group = piece.vertex_groups.new(name=rigid_group)
        group.add(list(range(len(piece.data.vertices))), 1.0, "REPLACE")
    elif weight_resolver is not None:
        groups: dict[str, bpy.types.VertexGroup] = {}
        for vertex in piece.data.vertices:
            raw_world = piece.matrix_world @ vertex.co
            resolved = weight_resolver(raw_world)
            if not resolved or sum(resolved.values()) <= 0.0:
                raise ValueError(f"weight resolver returned no weights for {name}")
            total = sum(float(value) for value in resolved.values())
            for group_name, value in resolved.items():
                group = groups.get(group_name)
                if group is None:
                    group = piece.vertex_groups.new(name=group_name)
                    groups[group_name] = group
                group.add([vertex.index], float(value) / total, "REPLACE")
    else:
        groups = {
            group.name: piece.vertex_groups.new(name=group.name) for group in source.vertex_groups
        }
        tree = KDTree(len(source.data.vertices))
        for index, vertex in enumerate(source.data.vertices):
            tree.insert(vertex.co, index)
        tree.balance()
        for vertex in piece.data.vertices:
            _, source_index, _ = tree.find(vertex.co)
            for membership in source.data.vertices[source_index].groups:
                source_group = source.vertex_groups[membership.group]
                groups[source_group.name].add(
                    [vertex.index], float(membership.weight), "REPLACE"
                )

    modifier = piece.modifiers.new(name="shared_adult_rig", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    piece.parent = source.parent
    piece.parent_type = source.parent_type
    piece.matrix_parent_inverse = source.matrix_parent_inverse.copy()
    piece.matrix_basis = source.matrix_basis.copy()
    piece.matrix_world = source.matrix_world.copy()
    piece["separate_shareable_wardrobe_component"] = True
    piece["contains_body_surface_copy"] = False
    piece["geometry_origin"] = "independent_parametric_closed_outer_garment"
    piece["private_clothed_review_only"] = True
    piece["runtime_activation_allowed"] = False
    return piece, {
        "name": name,
        "geometry_origin": "independent_parametric_closed_outer_garment",
        "contains_body_surface_copy": False,
        "authored_vertex_count": len(world_vertices),
        "authored_face_count": len(faces),
        "closed_face_count": len(mesh.polygons),
        "boundary_edges_before_solidify": boundary_before,
        "boundary_edges_after_solidify": boundary_edge_count(mesh),
        "closed_shell_mechanical_check": boundary_edge_count(mesh) == 0,
        "weight_coverage": weighted_coverage(piece),
        "requested_world_thickness_m": thickness,
        "requested_world_bevel_m": bevel_world_m,
        "applied_continuous_garment_subdivision_level": subdivision_level,
        "rigid_foot_binding": rigid_group or "",
        "structured_weight_resolver_used": weight_resolver is not None,
    }


def group_weighted_world_points(
    body: bpy.types.Object,
    group_names: set[str],
    *,
    minimum_weight: float = 0.10,
) -> list[Vector]:
    wanted = {group.index for group in body.vertex_groups if group.name in group_names}
    return [
        body.matrix_world @ vertex.co
        for vertex in body.data.vertices
        if sum(item.weight for item in vertex.groups if item.group in wanted) >= minimum_weight
    ]


def create_full_coverage_outfit(
    subject: str,
    body: bpy.types.Object,
    armature: bpy.types.Object,
    low: Vector,
    high: Vector,
    materials: dict[str, bpy.types.Material],
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Create independent outer clothes; never duplicate body polygon bands."""

    # Source cage is authored Y-up; the neutral armature evaluates Z-up.
    height = high.y - low.y
    torso_points = group_weighted_world_points(
        body,
        {"Hips_00", "Spine.001_010", "Spine1_011", "Spine2_012"},
        minimum_weight=0.35,
    )
    if len(torso_points) < 32:
        raise ValueError("insufficient torso landmarks for parametric wardrobe")
    torso_low, torso_high = bounds(torso_points)
    hip_points = group_weighted_world_points(
        body,
        {"Hips_00", LEFT_THIGH, RIGHT_THIGH},
        minimum_weight=0.25,
    )
    left_leg_points = group_weighted_world_points(
        body, {LEFT_THIGH, LEFT_SHIN}, minimum_weight=0.25
    )
    right_leg_points = group_weighted_world_points(
        body, {RIGHT_THIGH, RIGHT_SHIN}, minimum_weight=0.25
    )
    if min(len(hip_points), len(left_leg_points), len(right_leg_points)) < 24:
        raise ValueError("insufficient hip/leg landmarks for parametric trousers")
    hip_low, hip_high = bounds(hip_points)
    left_leg_low, left_leg_high = bounds(left_leg_points)
    right_leg_low, right_leg_high = bounds(right_leg_points)
    center_x = (torso_low.x + torso_high.x) * 0.5
    center_z = (torso_low.z + torso_high.z) * 0.5
    width = torso_high.x - torso_low.x
    depth = torso_high.z - torso_low.z
    if not (0.20 <= width <= 0.70 and 0.12 <= depth <= 0.55):
        raise ValueError(
            f"torso landmark bounds are implausible in authoring space: width={width}, depth={depth}"
        )

    def y(norm: float) -> float:
        return low.y + height * norm

    top_geometry = ring_shell_geometry(
        [
            (y(0.54), center_x, center_z, width * 0.46, depth * 0.61),
            (y(0.60), center_x, center_z, width * 0.42, depth * 0.56),
            (y(0.68), center_x, center_z, width * 0.49, depth * 0.64),
            (y(0.75), center_x, center_z, width * 0.51, depth * 0.59),
            (y(0.79), center_x, center_z, width * 0.36, depth * 0.48),
            (y(0.82), center_x, center_z, width * 0.22, depth * 0.35),
        ]
    )
    hip_center_x = (hip_low.x + hip_high.x) * 0.5
    hip_center_z = (hip_low.z + hip_high.z) * 0.5
    hip_width = hip_high.x - hip_low.x
    hip_depth = hip_high.z - hip_low.z
    trouser_parts: list[tuple[list[Vector], list[tuple[int, ...]]]] = []
    for leg_low, leg_high in (
        (right_leg_low, right_leg_high),
        (left_leg_low, left_leg_high),
    ):
        leg_x = (leg_low.x + leg_high.x) * 0.5
        leg_z = (leg_low.z + leg_high.z) * 0.5
        leg_width = leg_high.x - leg_low.x
        leg_depth = leg_high.z - leg_low.z
        sign = 1.0 if leg_x >= hip_center_x else -1.0
        upper_center_x = hip_center_x + sign * hip_width * 0.12
        trouser_parts.append(
            ring_shell_geometry(
                [
                    (y(0.045), leg_x, leg_z, leg_width * 0.58, leg_depth * 0.58),
                    (y(0.18), leg_x, leg_z, leg_width * 0.60, leg_depth * 0.60),
                    (y(0.34), leg_x, leg_z, leg_width * 0.66, leg_depth * 0.66),
                    (
                        y(0.50),
                        (leg_x + upper_center_x) * 0.5,
                        (leg_z + hip_center_z) * 0.5,
                        max(leg_width * 0.80, hip_width * 0.40),
                        max(leg_depth * 0.74, hip_depth * 0.52),
                    ),
                    (
                        y(0.61),
                        upper_center_x,
                        hip_center_z,
                        hip_width * 0.48,
                        hip_depth * 0.60,
                    ),
                ]
            )
        )
    trousers_geometry = combine_geometry(trouser_parts)

    def tunic_weights(point: Vector) -> dict[str, float]:
        norm = (point.y - low.y) / max(height, 1e-9)
        if norm <= 0.62:
            ratio = min(1.0, max(0.0, (norm - 0.54) / 0.08))
            return {"Spine.001_010": 1.0 - ratio, "Spine1_011": ratio}
        ratio = min(1.0, max(0.0, (norm - 0.62) / 0.18))
        return {"Spine1_011": 1.0 - ratio, "Spine2_012": ratio}

    def trouser_weights(point: Vector) -> dict[str, float]:
        norm = (point.y - low.y) / max(height, 1e-9)
        upper_leg = LEFT_THIGH if point.x >= center_x else RIGHT_THIGH
        lower_leg = LEFT_SHIN if point.x >= center_x else RIGHT_SHIN
        if norm >= 0.47:
            return {"Hips_00": 1.0}
        if norm >= 0.37:
            ratio = (0.47 - norm) / 0.10
            return {"Hips_00": 1.0 - ratio, upper_leg: ratio}
        if norm >= 0.27:
            return {upper_leg: 1.0}
        if norm >= 0.19:
            ratio = (0.27 - norm) / 0.08
            return {upper_leg: 1.0 - ratio, lower_leg: ratio}
        return {lower_leg: 1.0}

    objects: list[bpy.types.Object] = []
    records: list[dict[str, object]] = []
    for name, geometry, material, thickness, resolver in (
        (
            f"{subject}_separate_opaque_crew_neck_tunic",
            top_geometry,
            materials["top"],
            0.0040,
            tunic_weights,
        ),
        (
            f"{subject}_separate_opaque_full_length_trousers",
            trousers_geometry,
            materials["leggings"],
            0.0040,
            trouser_weights,
        ),
    ):
        obj, record = bind_parametric_piece(
            name=name,
            source=body,
            armature=armature,
            world_vertices=geometry[0],
            faces=geometry[1],
            material=material,
            thickness=thickness,
            weight_resolver=resolver,
            subdivision_level=1,
        )
        objects.append(obj)
        records.append(record)

    body_points = mesh_world_points(body)
    shoe_specs = (("right", -1.0, RIGHT_FOOT), ("left", 1.0, LEFT_FOOT))
    for side, sign, rigid_group in shoe_specs:
        points = [
            point
            for point in body_points
            if (point.y - low.y) / max(height, 1e-9) <= 0.14
            and ((point.x - center_x) * sign) >= 0.0
        ]
        if len(points) < 8:
            raise ValueError(f"insufficient source foot landmarks for {side} shoe")
        foot_low, foot_high = bounds(points)
        shoe_geometry = box_geometry(
            foot_low - Vector((0.018, 0.008, 0.035)),
            foot_high + Vector((0.018, 0.020, 0.035)),
        )
        obj, record = bind_parametric_piece(
            name=f"{subject}_separate_{side}_closed_flat_shoe_last",
            source=body,
            armature=armature,
            world_vertices=shoe_geometry[0],
            faces=shoe_geometry[1],
            material=materials["shoes"],
            thickness=0.0,
            rigid_group=rigid_group,
            bevel_world_m=0.025,
        )
        objects.append(obj)
        records.append(record)
    return objects, {
        "ordinary_full_coverage_review_outfit": True,
        "source_bra_and_brief_removed": True,
        "outer_geometry_is_independent_from_body_surface": True,
        "body_polygon_band_duplication_used": False,
        "top_and_trouser_overlap_authored": True,
        "separate_component_count": len(objects),
        "components": records,
        "full_coverage_visual_owner_approved": False,
        "wearable_dressing_behavior_proven": False,
        "garment_penetration_proven_absent": False,
    }


def split_source_eye_parts(
    eye: bpy.types.Object,
    subject: str,
    materials: dict[str, bpy.types.Material],
) -> tuple[list[bpy.types.Object], list[bpy.types.Object], list[dict[str, object]]]:
    """Name and recolor the source's already-skinned eye islands.

    The licensed eye mesh contains a seated sclera, iris and pupil island for
    each eye.  Keeping those islands preserves the exact armature modifier,
    inverse bind and socket placement.  The rejected generated-eye approach
    bone-parented world-space spheres and moved them onto the source Y axis,
    corrupting both the render and aggregate bounds.
    """

    bpy.ops.object.select_all(action="DESELECT")
    eye.select_set(True)
    bpy.context.view_layer.objects.active = eye
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if len(parts) != 6:
        raise ValueError(f"expected six source eye islands, found {len(parts)}")
    centered = sorted(
        (
            sum((point.x for point in mesh_world_points(obj)), 0.0)
            / max(1, len(obj.data.vertices)),
            obj,
        )
        for obj in parts
    )
    side_groups = {
        "right": [obj for _, obj in centered[:3]],
        "left": [obj for _, obj in centered[3:]],
    }
    sclerae: list[bpy.types.Object] = []
    detail_parts: list[bpy.types.Object] = []
    records: list[dict[str, object]] = []
    for side, group in side_groups.items():
        group.sort(key=lambda obj: len(obj.data.vertices), reverse=True)
        sclera, iris, pupil = group
        per_side: dict[str, object] = {"side": side, "source_island_vertex_counts": {}}
        for obj, role in ((sclera, "sclera"), (iris, "iris"), (pupil, "pupil")):
            obj.name = f"{subject}_{side}_{'seated_' if role == 'sclera' else ''}{role}"
            obj.data.name = f"{obj.name}_mesh"
            set_material(obj, materials[role])
            obj["eye_component"] = role
            obj["socket_fit_source"] = "licensed_base_pre_skinned_eye_island"
            obj["private_clothed_review_only"] = True
            obj["runtime_activation_allowed"] = False
            low, high = bounds(mesh_world_points(obj))
            per_side[role] = {
                "name": obj.name,
                "authoring_y_up_bounds_low": vec(low),
                "authoring_y_up_bounds_high": vec(high),
            }
            per_side["source_island_vertex_counts"][role] = len(obj.data.vertices)
        sclerae.append(sclera)
        detail_parts.extend((iris, pupil))
        records.append(per_side)
    return sclerae, detail_parts, records


def add_subdivision(obj: bpy.types.Object, *, level: int = 1) -> None:
    modifier = obj.modifiers.new(name="safe_review_surface_subdivision", type="SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = level
    modifier.render_levels = level
    modifier.show_only_control_edges = True
    # Smooth the cage before the armature deformation.
    while obj.modifiers.find(modifier.name) > 0:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_move_up(modifier=modifier.name)


def reset_pose(armature: bpy.types.Object) -> None:
    if armature.animation_data:
        armature.animation_data.action = None
    neutral = NEUTRAL_POSE_MATRICES.get(armature.name)
    if not neutral:
        raise ValueError("imported neutral pose basis was not captured")
    for bone in armature.pose.bones:
        bone.matrix_basis = neutral[bone.name].copy()
    bpy.context.view_layer.update()


def rotate_bone_toward(armature: bpy.types.Object, name: str, target_world: Vector) -> None:
    bone = armature.pose.bones.get(name)
    if bone is None:
        raise ValueError(f"missing pose bone {name}")
    target = armature.matrix_world.inverted() @ target_world
    current = (bone.tail - bone.head).normalized()
    desired = (target - bone.head).normalized()
    delta = current.rotation_difference(desired)
    pivot = bone.head.copy()
    bone.matrix = Matrix.Translation(pivot) @ delta.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ bone.matrix
    bpy.context.view_layer.update()


def arm_target(
    armature: bpy.types.Object,
    side: str,
    pose: str,
    low: Vector,
    height: float,
) -> None:
    names = (LEFT_ARM, LEFT_FOREARM, LEFT_HAND) if side == "left" else (RIGHT_ARM, RIGHT_FOREARM, RIGHT_HAND)
    upper = armature.pose.bones[names[0]]
    sign = 1.0 if (armature.matrix_world @ upper.head).x >= 0.0 else -1.0
    shoulder = armature.matrix_world @ upper.head
    if pose == "reach" and side == "right":
        elbow = shoulder + Vector((sign * height * 0.07, -height * 0.16, -height * 0.04))
        hand = shoulder + Vector((sign * height * 0.04, -height * 0.33, -height * 0.07))
    elif pose == "stride":
        phase = 1.0 if side == "left" else -1.0
        elbow = shoulder + Vector((sign * height * 0.08, phase * height * 0.05, -height * 0.14))
        hand = shoulder + Vector((sign * height * 0.10, phase * height * 0.10, -height * 0.28))
    else:
        return
    rotate_bone_toward(armature, names[0], elbow)
    rotate_bone_toward(armature, names[1], hand)


def apply_pose(armature: bpy.types.Object, pose: str, low: Vector, high: Vector) -> None:
    reset_pose(armature)
    height = high.z - low.z
    if pose in {"stride", "reach"}:
        arm_target(armature, "left", pose, low, height)
        arm_target(armature, "right", pose, low, height)
    if pose == "stride":
        left_thigh = armature.pose.bones[LEFT_THIGH]
        hip = armature.matrix_world @ left_thigh.head
        rotate_bone_toward(armature, LEFT_THIGH, hip + Vector((0.0, -height * 0.11, -height * 0.20)))
        left_shin = armature.pose.bones[LEFT_SHIN]
        knee = armature.matrix_world @ left_shin.head
        rotate_bone_toward(armature, LEFT_SHIN, knee + Vector((0.0, height * 0.07, -height * 0.18)))
    bpy.context.view_layer.update()


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_view(
    path: Path,
    camera: bpy.types.Object,
    center: Vector,
    direction: Vector,
    ortho_scale: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    camera.location = center + direction.normalized() * max(2.0, ortho_scale * 3.0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    look_at(camera, center)
    bpy.context.scene.render.filepath = str(path.resolve())
    bpy.ops.render.render(write_still=True)
    if not path.is_file():
        raise RuntimeError(f"render did not materialize: {path}")


def finite_metrics(objects: list[bpy.types.Object]) -> dict[str, object]:
    points = [point for obj in objects if obj.type == "MESH" for point in mesh_world_points(obj, evaluated=True)]
    low, high = bounds(points)
    return {
        "evaluated_vertex_count": len(points),
        "finite_coordinates": all(math.isfinite(value) for point in points for value in point),
        "bounds_low": vec(low),
        "bounds_high": vec(high),
        "extent": vec(high - low),
    }


def export_selected(path: Path, objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path.resolve()),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=False,
        export_yup=True,
        export_morph=False,
        export_extras=True,
    )


def build_subject(
    *,
    subject: str,
    definition: dict[str, object],
    source: Path,
    source_hash: str,
    project_root: Path,
    run_dir: Path,
    render_mode: str,
) -> dict[str, object]:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    bpy.context.view_layer.update()
    roles, armature = classify_scene()
    for obj in [*roles["helper"], *roles["clothes"]]:
        bpy.data.objects.remove(obj, do_unlink=True)
    body = roles["body"][0]
    body.name = f"{subject}_adult_adapted_body_cage"
    body.data.name = f"{body.name}_mesh"
    armature.name = f"{subject}_adult_54_bone_review_rig"
    armature.data.name = f"{subject}_adult_54_bone_review_skeleton"
    NEUTRAL_POSE_MATRICES[armature.name] = {
        bone.name: bone.matrix_basis.copy() for bone in armature.pose.bones
    }
    all_adapted = [body, *roles["eyes"], *roles["hair"], *roles["hair_extra"], *roles["mouth"]]
    source_body_points = mesh_world_points(body)
    source_low, source_high = bounds(source_body_points)
    source_silhouette = silhouette_metrics(body, source_low, source_high)
    warp = make_warp(source_low, source_high, definition["controls"])
    component_deltas = {role_for(obj): warp_mesh(obj, warp) for obj in all_adapted}
    rig_deltas = unchanged_armature_stats(armature)
    candidate_low, candidate_high = bounds(mesh_world_points(body))
    candidate_silhouette = silhouette_metrics(body, candidate_low, candidate_high)

    materials = {
        "sclera": make_material(f"{subject}_warm_sclera", (0.92, 0.91, 0.87, 1.0), roughness=0.32),
        "iris": make_material(f"{subject}_iris", definition["iris"], roughness=0.30),
        "pupil": make_material(f"{subject}_pupil", (0.004, 0.002, 0.002, 1.0), roughness=0.20),
        "hair": make_material(f"{subject}_hair", definition["hair"], roughness=0.62),
        "top": make_material(f"{subject}_opaque_top", definition["top"], roughness=0.79),
        "leggings": make_material(f"{subject}_opaque_trousers", definition["leggings"], roughness=0.82),
        "shoes": make_material(f"{subject}_opaque_shoes", definition["shoes"], roughness=0.70),
        "ground": make_material(f"{subject}_review_ground", (0.16, 0.18, 0.21, 1.0), roughness=0.92),
    }
    for obj in [*roles["hair"], *roles["hair_extra"]]:
        obj.name = f"{subject}_{role_for(obj)}"
        set_material(obj, materials["hair"])
    for obj in roles["mouth"]:
        obj.name = f"{subject}_licensed_mouth_surface"
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    # The licensed body cage is segmented at several joints. Catmull-Clark
    # shrinks each disconnected boundary independently and visibly opens the
    # shoulder/elbow/knee/finger seams, so retain the authored cage and apply
    # smooth shading only. Segmented topology remains explicitly unproven.
    for obj in roles["hair"]:
        add_subdivision(obj, level=1)

    sclerae, eye_details, eye_records = split_source_eye_parts(
        roles["eyes"][0], subject, materials
    )
    garments, clothing = create_full_coverage_outfit(
        subject, body, armature, candidate_low, candidate_high, materials
    )
    review_objects = [
        body,
        *roles["hair"],
        *roles["hair_extra"],
        *roles["mouth"],
        *sclerae,
        *eye_details,
        *garments,
    ]
    for obj in [armature, *review_objects]:
        obj["candidate_id"] = subject
        obj["maturity_policy"] = "adult"
        obj["source_license"] = "CC-BY-4.0"
        obj["source_author"] = SOURCE_PROVENANCE["author"]
        obj["source_url"] = SOURCE_PROVENANCE["source_url"]
        obj["adaptation_notice"] = "continuous silhouette deformation, smooth shading, named source eye islands, and full-coverage wardrobe"
        obj["private_inactive_review_only"] = True
        obj["runtime_activation_allowed"] = False

    pre_reset_body_points = mesh_world_points(body, evaluated=True)
    apply_pose(armature, "neutral", candidate_low, candidate_high)
    neutral_restore_delta = delta_stats(
        pre_reset_body_points, mesh_world_points(body, evaluated=True)
    )
    neutral_axis_preflight = finite_metrics(review_objects)
    neutral_body_axis_preflight = finite_metrics([body])
    preflight_extent = neutral_axis_preflight["extent"]
    body_preflight_extent = neutral_body_axis_preflight["extent"]
    per_object_axis_preflight = {
        obj.name: finite_metrics([obj]) for obj in review_objects if obj.type == "MESH"
    }
    if not (
        preflight_extent[2] > 1.25
        and preflight_extent[2] > preflight_extent[0] * 1.35
        and preflight_extent[2] > preflight_extent[1] * 2.0
        and body_preflight_extent[2] > body_preflight_extent[0] * 2.2
        and body_preflight_extent[2] > body_preflight_extent[1] * 3.0
    ):
        raise ValueError(
            "neutral imported pose is not a bounded Z-up standing assembly; "
            f"evaluated extent={preflight_extent}; objects="
            f"{json.dumps({name: {'low': value['bounds_low'], 'high': value['bounds_high'], 'extent': value['extent']} for name, value in per_object_axis_preflight.items()})}"
        )

    # All framing and world-space pose targets use the evaluated Z-up review
    # assembly.  The raw candidate bounds above remain Y-up and are only valid
    # for cage deformation and wardrobe selection.
    neutral_eval_low = Vector(neutral_axis_preflight["bounds_low"])
    neutral_eval_high = Vector(neutral_axis_preflight["bounds_high"])

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.024, 0.032)
    scene.view_settings.exposure = -0.8
    height = neutral_eval_high.z - neutral_eval_low.z
    full_center = Vector(
        (
            (neutral_eval_low.x + neutral_eval_high.x) * 0.5,
            (neutral_eval_low.y + neutral_eval_high.y) * 0.5,
            neutral_eval_low.z + height * 0.52,
        )
    )
    head_center = Vector((full_center.x, full_center.y, neutral_eval_low.z + height * 0.905))
    bpy.ops.mesh.primitive_cube_add(location=(full_center.x, full_center.y, neutral_eval_low.z - 0.012))
    ground = bpy.context.object
    ground.name = f"{subject}_private_review_ground_not_exported"
    ground.scale = (height * 0.75, height * 0.75, 0.012)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_material(ground, materials["ground"])
    for index, (offset, energy, size) in enumerate(
        (
            (Vector((-0.72, -1.15, 1.12)), 430.0, 3.0),
            (Vector((0.92, -0.45, 0.76)), 230.0, 2.4),
            (Vector((0.15, 0.92, 1.25)), 290.0, 2.6),
        ),
        start=1,
    ):
        bpy.ops.object.light_add(type="AREA", location=full_center + offset * height)
        light = bpy.context.object
        light.name = f"{subject}_private_review_light_{index}"
        light.data.energy = energy
        light.data.size = size
        look_at(light, full_center)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = f"{subject}_private_review_camera"
    scene.camera = camera

    subject_dir = run_dir / subject
    subject_dir.mkdir(parents=True, exist_ok=True)
    renders: dict[str, dict[str, str]] = {}
    pose_metrics: dict[str, object] = {}
    poses = ("neutral",) if render_mode == "diagnostic_neutral_only" else ("neutral", "stride", "reach")
    for pose in poses:
        apply_pose(armature, pose, neutral_eval_low, neutral_eval_high)
        pose_metrics[pose] = finite_metrics(review_objects)
        view_specs = (
            {"front": Vector((0.0, -1.0, 0.035))}
            if render_mode == "diagnostic_neutral_only"
            else
            {
                "front": Vector((0.0, -1.0, 0.035)),
                "front_three_quarter": Vector((0.66, -1.0, 0.06)),
                "left_profile": Vector((1.0, 0.0, 0.035)),
                "back": Vector((0.0, 1.0, 0.035)),
            }
            if pose == "neutral"
            else {"front_three_quarter": Vector((0.66, -1.0, 0.06))}
        )
        for view_name, direction in view_specs.items():
            key = f"{pose}_{view_name}"
            path = subject_dir / f"{key}.png"
            render_view(path, camera, full_center, direction, height * 1.10)
            renders[key] = {
                "path": project_relative(path, project_root),
                "sha256": sha256_file(path),
            }
    apply_pose(armature, "neutral", neutral_eval_low, neutral_eval_high)
    head_views = (
        {"head_front": Vector((0.0, -1.0, 0.02))}
        if render_mode == "diagnostic_neutral_only"
        else {
            "head_front": Vector((0.0, -1.0, 0.02)),
            "head_three_quarter": Vector((0.66, -1.0, 0.03)),
            "head_profile": Vector((1.0, 0.0, 0.02)),
        }
    )
    for view_name, direction in head_views.items():
        path = subject_dir / f"{view_name}.png"
        render_view(path, camera, head_center, direction, height * 0.29)
        renders[view_name] = {
            "path": project_relative(path, project_root),
            "sha256": sha256_file(path),
        }

    model_path = subject_dir / f"{subject}_adult_clothed_quality_r4_review.glb"
    export_selected(model_path, [armature, *review_objects])
    if not model_path.is_file():
        raise RuntimeError("candidate export missing")
    body_after = mesh_world_points(body)
    body_delta = delta_stats(source_body_points, body_after)
    if body_delta["point_fingerprints_differ"] is not True:
        raise RuntimeError("candidate body cage is an unmodified copy")
    source_vs_candidate_hashes = {
        "source_glb_sha256": source_hash,
        "candidate_review_glb_sha256": sha256_file(model_path),
        "byte_identical": source_hash == sha256_file(model_path),
    }
    derivative = {
        "schema_version": 1,
        "artifact_type": "cc_by_adult_cage_derivative_lineage",
        "created_at": now_iso(),
        "candidate_id": subject,
        "source": {
            "path": project_relative(source, project_root),
            "sha256": source_hash,
            "embedded_asset_extras": SOURCE_PROVENANCE,
        },
        "adaptation_authority": {
            "license_id": "CC-BY-4.0",
            "license_url": SOURCE_PROVENANCE["license_url"],
            "adaptation_allowed": True,
            "attribution_required": True,
            "copy_as_unmodified_candidate_allowed": False,
        },
        "source_vs_candidate_hashes": source_vs_candidate_hashes,
        "body_cage_deformation": body_delta,
        "component_deformations": component_deltas,
        "rig_rest_landmark_deformation": rig_deltas,
        "source_body_silhouette": source_silhouette,
        "candidate_body_silhouette": candidate_silhouette,
        "adaptation_changes": [
            "continuous smooth landmark-envelope deformation of the source cage while preserving the licensed 54-bone rest rig",
            "source bra and brief removed from review assembly",
            "independent parametric opaque crew-neck tunic, overlapping trousers, and closed shoe lasts authored without copied body faces",
            "the six pre-skinned source eye islands retained and named as seated sclera, iris, and pupil pairs",
            "smooth shading applied to the segmented body cage without Catmull-Clark; one review subdivision level retained on hair only",
        ],
        "wholly_new_source_surface_claimed": False,
        "licensed_source_surface_incorporated": True,
        "anatomical_completeness_proven": False,
        "runtime_activation_allowed": False,
    }
    derivative_path = subject_dir / f"{subject}_derivative_lineage.json"
    derivative_path.write_text(json.dumps(derivative, indent=2), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": subject,
        "label": definition["label"],
        "candidate_revision": definition["candidate_revision"],
        "status": (
            "private_inactive_clothed_axis_diagnostic_not_owner_review_candidate"
            if render_mode == "diagnostic_neutral_only"
            else "private_inactive_clothed_visual_review_owner_approval_required"
        ),
        "render_mode": render_mode,
        "model": {
            "path": project_relative(model_path, project_root),
            "sha256": sha256_file(model_path),
        },
        "derivative_lineage": {
            "path": project_relative(derivative_path, project_root),
            "sha256": sha256_file(derivative_path),
        },
        "body": {
            "maturity_policy": "adult",
            "fit_basis": definition["fit_basis"],
            "identity_evidence": definition["identity_evidence"],
            "likeness_claimed": False,
            "adult_topology_lane": "confirmed_adult_topology",
            "anatomical_completeness_proven": False,
            "source_cage_has_segmented_joint_boundaries": True,
            "watertight_topology_proven": False,
            "body_catmull_clark_used": False,
            "body_cage_deformation": body_delta,
            "source_silhouette": source_silhouette,
            "candidate_silhouette": candidate_silhouette,
        },
        "eyes": {
            "seated_source_sclera_count": len(sclerae),
            "named_iris_count": len([obj for obj in eye_details if obj.name.endswith("_iris")]),
            "named_pupil_count": len([obj for obj in eye_details if obj.name.endswith("_pupil")]),
            "socket_fit_records": eye_records,
            "source_pre_skinned_eye_islands_retained": True,
            "eyelids_integrated_in_head_surface_not_separate": True,
            "blink_control_proven": False,
            "gaze_control_proven": False,
        },
        "clothing": clothing,
        "rig": {
            "bone_count": len(armature.data.bones),
            "body_weight_coverage": weighted_coverage(body),
            "pose_articulation_samples": pose_metrics,
            "neutral_z_up_axis_preflight": neutral_axis_preflight,
            "neutral_body_z_up_axis_preflight": neutral_body_axis_preflight,
            "per_object_axis_preflight": per_object_axis_preflight,
            "coordinate_contract": {
                "raw_authoring_space": "Y-up; X lateral; Z depth",
                "neutral_evaluated_review_space": "Z-up; X lateral; Y depth",
                "raw_bounds_used_only_for_cage_and_wardrobe": True,
                "evaluated_bounds_used_for_camera_ground_and_world_pose_targets": True,
            },
            "neutral_pose_restore_delta": neutral_restore_delta,
            "stable_working_rig_proven": False,
            "motion_sequence_proven": False,
        },
        "renders": renders,
        "truth": {
            "ordinary_review_is_clothed": True,
            "unclothed_render_created_or_retained": False,
            "live_runtime_model_modified": False,
            "identity_likeness_owner_approved": False,
            "anatomical_completeness_proven": False,
            "stable_visual_deformation_proven": False,
            "garment_behavior_proven": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
            "positive_proof_gate_released": False,
            "two_subject_autobuild_released": False,
        },
    }
    manifest_path = subject_dir / f"{subject}_quality_r4_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "candidate_id": subject,
        "manifest": project_relative(manifest_path, project_root),
        "model": project_relative(model_path, project_root),
        "lineage": project_relative(derivative_path, project_root),
    }


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = Path(config["source_model"]).resolve(strict=True)
    source_hash = str(config["source_sha256"]).lower()
    if sha256_file(source) != source_hash:
        raise ValueError("471903 source hash mismatch")
    run_dir = Path(config["output_dir"]).resolve()
    allowed = (
        project_root
        / "Avatar"
        / "avatar_builder"
        / "candidate_sources"
        / "two_body_quality_r4"
        / "private_review"
    ).resolve()
    run_dir.relative_to(allowed)
    run_dir.mkdir(parents=True, exist_ok=True)
    requested_subjects = config.get("subjects", list(SUBJECTS))
    if not isinstance(requested_subjects, list) or not requested_subjects:
        raise ValueError("subjects must be a non-empty list")
    unknown_subjects = sorted(set(requested_subjects) - set(SUBJECTS))
    if unknown_subjects:
        raise ValueError(f"unknown bounded subjects: {unknown_subjects}")
    render_mode = str(config.get("render_mode", "full_private_review"))
    if render_mode not in {"full_private_review", "diagnostic_neutral_only"}:
        raise ValueError(f"unsupported render mode: {render_mode}")
    if render_mode == "diagnostic_neutral_only" and requested_subjects != ["kira"]:
        raise ValueError("axis diagnostic is deliberately bounded to Kira only")
    results = [
        build_subject(
            subject=subject,
            definition=definition,
            source=source,
            source_hash=source_hash,
            project_root=project_root,
            run_dir=run_dir,
            render_mode=render_mode,
        )
        for subject in requested_subjects
        for definition in (SUBJECTS[subject],)
    ]
    print(json.dumps({"ok": True, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
