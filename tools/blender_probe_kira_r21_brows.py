"""Read-only inventory for the accepted-face Kira R21 eyebrow correction.

Run with Blender in background mode against the R21 attempt-08 review Blend.
The script writes only a JSON report; it never saves or mutates the Blend.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


PROJECT = Path(r"C:\Users\robmc\Kira")
OUT = PROJECT / "RecoverySprint" / "continuation_20260802" / "kira_r21_brow_only_correction" / "preflight_02"
BROW_NAME = "Kira_R19_Accepted_Brows01"
BODY_NAMES = (
    "Kira_R21_Bald_Private_Inactive_Pelvis_Attempt01",
    "Kira_R19_BlackProject_Radial_Patch_Primary_Surface",
)
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def mesh_geometry_sha(obj: bpy.types.Object) -> str:
    h = hashlib.sha256()
    mesh = obj.data
    for vertex in mesh.vertices:
        h.update(struct.pack("<I3d", vertex.index, *map(float, vertex.co)))
    for polygon in mesh.polygons:
        h.update(struct.pack("<II", polygon.index, int(polygon.material_index)))
        h.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            h.update(struct.pack("<I", int(index)))
    return h.hexdigest()


def object_matrix(obj: bpy.types.Object) -> list[list[float]]:
    return [[float(v) for v in row] for row in obj.matrix_world]


def local_components(obj: bpy.types.Object) -> list[dict]:
    mesh = obj.data
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen = set(range(len(mesh.vertices)))
    components = []
    while unseen:
        seed = min(unseen)
        stack = [seed]
        unseen.remove(seed)
        indices = []
        while stack:
            current = stack.pop()
            indices.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        points = [mesh.vertices[index].co for index in indices]
        components.append(
            {
                "vertex_count": len(indices),
                "min": [min(float(p[axis]) for p in points) for axis in range(3)],
                "max": [max(float(p[axis]) for p in points) for axis in range(3)],
                "centroid": [sum(float(p[axis]) for p in points) / len(points) for axis in range(3)],
            }
        )
    return sorted(components, key=lambda item: item["centroid"][0])


def closest_body_distance(body: bpy.types.Object, brow: bpy.types.Object) -> dict:
    body_world_vertices = [body.matrix_world @ v.co for v in body.data.vertices]
    body_faces = [[int(i) for i in p.vertices] for p in body.data.polygons]
    tree = BVHTree.FromPolygons(body_world_vertices, body_faces, all_triangles=False)
    distances = []
    for vertex in brow.data.vertices:
        world = brow.matrix_world @ vertex.co
        _hit, _normal, _face, distance = tree.find_nearest(world)
        if distance is not None and math.isfinite(distance):
            distances.append(float(distance))
    return {
        "sample_count": len(distances),
        "minimum_m": min(distances) if distances else None,
        "median_m": sorted(distances)[len(distances) // 2] if distances else None,
        "maximum_m": max(distances) if distances else None,
    }


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise RuntimeError("empty percentile input")
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def brow_body_local_summary(body: bpy.types.Object, brow: bpy.types.Object) -> dict:
    inverse = body.matrix_world.inverted()
    points = [inverse @ (brow.matrix_world @ vertex.co) for vertex in brow.data.vertices]
    result = {}
    for label, selected in (
        ("negative_x", [point for point in points if point.x < 0.0]),
        ("positive_x", [point for point in points if point.x > 0.0]),
    ):
        if not selected:
            raise RuntimeError(f"old brow has no {label} points")
        result[label] = {
            "point_count": len(selected),
            "x_p01": percentile([float(p.x) for p in selected], 0.01),
            "x_p50": percentile([float(p.x) for p in selected], 0.50),
            "x_p99": percentile([float(p.x) for p in selected], 0.99),
            "y_p01": percentile([float(p.y) for p in selected], 0.01),
            "y_p50": percentile([float(p.y) for p in selected], 0.50),
            "y_p99": percentile([float(p.y) for p in selected], 0.99),
            "z_p01": percentile([float(p.z) for p in selected], 0.01),
            "z_p50": percentile([float(p.z) for p in selected], 0.50),
            "z_p99": percentile([float(p.z) for p in selected], 0.99),
        }
    return result


def main() -> None:
    source = Path(bpy.data.filepath)
    brow = bpy.data.objects.get(BROW_NAME)
    body = next((bpy.data.objects.get(name) for name in BODY_NAMES if bpy.data.objects.get(name)), None)
    rig = bpy.data.objects.get(RIG_NAME)
    if brow is None or brow.type != "MESH":
        raise RuntimeError(f"missing eyebrow mesh object {BROW_NAME!r}")
    if body is None or body.type != "MESH":
        raise RuntimeError(f"missing body mesh object from {BODY_NAMES!r}")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"missing armature {RIG_NAME!r}")

    materials = []
    for material in brow.data.materials:
        materials.append(
            {
                "name": material.name if material else None,
                "diffuse_color": list(material.diffuse_color) if material else None,
                "use_nodes": bool(material.use_nodes) if material else None,
            }
        )
    record = {
        "status": "READ_ONLY_PREFLIGHT_COMPLETE",
        "source_blend": source.relative_to(PROJECT).as_posix(),
        "source_blend_sha256": sha256_file(source),
        "source_saved_or_mutated": False,
        "brow": {
            "object": brow.name,
            "mesh": brow.data.name,
            "geometry_sha256": mesh_geometry_sha(brow),
            "vertex_count": len(brow.data.vertices),
            "edge_count": len(brow.data.edges),
            "polygon_count": len(brow.data.polygons),
            "connected_components": local_components(brow),
            "world_matrix": object_matrix(brow),
            "parent": brow.parent.name if brow.parent else None,
            "parent_type": brow.parent_type,
            "parent_bone": brow.parent_bone,
            "modifiers": [
                {
                    "name": modifier.name,
                    "type": modifier.type,
                    "object": modifier.object.name if getattr(modifier, "object", None) else None,
                }
                for modifier in brow.modifiers
            ],
            "vertex_groups": [group.name for group in brow.vertex_groups],
            "materials": materials,
            "nearest_body_surface_distance": closest_body_distance(body, brow),
            "body_local_robust_bounds": brow_body_local_summary(body, brow),
        },
        "protected_components": {
            "body": {"object": body.name, "geometry_sha256": mesh_geometry_sha(body)},
            "rig": {"object": rig.name, "bone_count": len(rig.data.bones)},
            "eye_like_objects": [
                {"object": obj.name, "mesh": obj.data.name, "geometry_sha256": mesh_geometry_sha(obj)}
                for obj in sorted(bpy.data.objects, key=lambda item: item.name)
                if obj.type == "MESH" and any(token in obj.name.casefold() for token in ("eye", "iris", "pupil", "sclera", "lash", "lid"))
            ],
        },
        "authorization": {
            "replace_only_exact_brow_object": BROW_NAME,
            "face_body_eyes_rig_frozen": True,
            "pelvis_nails_hair_out_of_scope": True,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "PREFLIGHT.json"
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(target), "status": record["status"]}))


if __name__ == "__main__":
    main()
