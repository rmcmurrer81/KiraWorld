"""Audit exact exported hair-to-scalp fit with evaluated geometry.

This is an engineering diagnostic, not an approval validator.  It imports the
exact GLB, finds the primary body and removable hair object, measures head and
hair ellipsoidal bounds, samples crown/rear scalp clearance against the actual
hair mesh, and renders two fit-space views.  It never edits or re-exports the
input artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--render-dir", required=True)
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def _evaluated_bvh(obj: bpy.types.Object) -> BVHTree:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
        return BVHTree.FromPolygons(vertices, polygons, all_triangles=False)
    finally:
        evaluated.to_mesh_clear()


def _bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = max(0.0, min(1.0, quantile)) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _sample_clearance(
    samples: list[Vector],
    center: Vector,
    radii: Vector,
    hair_bvh: BVHTree,
) -> dict[str, object]:
    rows = []
    for point in samples:
        found = hair_bvh.find_nearest(point)
        if found is None or found[0] is None:
            continue
        location, _normal, _index, distance = found
        normal = Vector(
            (
                (point.x - center.x) / max(radii.x * radii.x, 1e-10),
                (point.y - center.y) / max(radii.y * radii.y, 1e-10),
                (point.z - center.z) / max(radii.z * radii.z, 1e-10),
            )
        ).normalized()
        delta = location - point
        signed = float(delta.dot(normal))
        tangential = math.sqrt(max(0.0, float(distance) ** 2 - signed**2))
        covered = signed >= -0.002 and float(distance) <= 0.030 and tangential <= 0.020
        rows.append(
            {
                "signed_outward_clearance_m": signed,
                "nearest_distance_m": float(distance),
                "tangential_offset_m": tangential,
                "covered": covered,
            }
        )
    return {
        "sample_count": len(rows),
        "covered_count": sum(1 for row in rows if row["covered"]),
        "coverage_fraction": (
            sum(1 for row in rows if row["covered"]) / len(rows) if rows else 0.0
        ),
        "signed_clearance_m": {
            "minimum": min(
                (row["signed_outward_clearance_m"] for row in rows),
                default=0.0,
            ),
            "p10": _percentile(
                [row["signed_outward_clearance_m"] for row in rows], 0.10
            ),
            "median": _percentile(
                [row["signed_outward_clearance_m"] for row in rows], 0.50
            ),
            "p90": _percentile(
                [row["signed_outward_clearance_m"] for row in rows], 0.90
            ),
            "maximum": max(
                (row["signed_outward_clearance_m"] for row in rows),
                default=0.0,
            ),
        },
        "nearest_distance_m": {
            "median": _percentile(
                [row["nearest_distance_m"] for row in rows], 0.50
            ),
            "p90": _percentile(
                [row["nearest_distance_m"] for row in rows], 0.90
            ),
        },
    }


def _material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = color
        node.inputs["Roughness"].default_value = 0.52
    return material


def _look(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _render_fit_views(
    render_dir: Path,
    body: bpy.types.Object,
    hair: bpy.types.Object,
    head_center: Vector,
    head_high: Vector,
    head_size: Vector,
) -> dict[str, str]:
    render_dir.mkdir(parents=True, exist_ok=True)
    body.data.materials.clear()
    body.data.materials.append(_material("ScalpDiagnostic", (0.82, 0.24, 0.16, 1.0)))
    for material in hair.data.materials:
        if material is not None and material.use_nodes:
            node = material.node_tree.nodes.get("Principled BSDF")
            if node is not None:
                base = node.inputs.get("Base Color")
                if base is not None:
                    for link in list(base.links):
                        material.node_tree.links.remove(link)
                    base.default_value = (0.005, 0.004, 0.008, 1.0)
    for obj in bpy.context.scene.objects:
        obj.hide_render = obj not in {body, hair}
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.08, 0.09, 0.11)
    camera_data = bpy.data.cameras.new("HairFitDiagnosticCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(head_size) * 1.55
    camera = bpy.data.objects.new("HairFitDiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    for label, energy, offset in (
        ("Key", 950.0, (0.5, -0.7, 0.7)),
        ("Fill", 750.0, (-0.5, -0.4, 0.4)),
        ("Rear", 650.0, (0.0, 0.7, 0.6)),
    ):
        data = bpy.data.lights.new(label, "AREA")
        data.energy = energy
        data.size = 0.6
        light = bpy.data.objects.new(label, data)
        light.location = head_center + Vector(offset)
        bpy.context.collection.objects.link(light)
        _look(light, head_center)
    distance = max(head_size) * 3.2
    renders = {}
    for filename, location, target in (
        (
            "fit_space_crown.png",
            Vector((head_center.x, head_center.y, head_high.z + distance)),
            Vector((head_center.x, head_center.y, head_high.z - head_size.z * 0.40)),
        ),
        (
            "fit_space_rear.png",
            Vector((head_center.x, head_center.y + distance, head_center.z)),
            head_center,
        ),
    ):
        camera.location = location
        _look(camera, target)
        path = render_dir / filename
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders[filename] = str(path)
    return renders


def main() -> None:
    args = _args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    render_dir = Path(args.render_dir).resolve()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(input_path))
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    body = next(
        (
            obj
            for obj in meshes
            if bool(obj.get("rapid_body_primary_surface"))
            or "primary_surface" in obj.name.lower()
        ),
        None,
    )
    hair = next(
        (
            obj
            for obj in meshes
            if bool(obj.get("removable_review_hair"))
            or "removable" in obj.name.lower() and "hair" in obj.name.lower()
        ),
        None,
    )
    if body is None or hair is None:
        raise RuntimeError(
            f"could not identify body/hair among {[obj.name for obj in meshes]}"
        )
    body_points = _evaluated_vertices(body)
    hair_points = _evaluated_vertices(hair)
    body_low, body_high = _bounds(body_points)
    maximum_z = body_high.z
    head_points = [point for point in body_points if point.z >= maximum_z - 0.270]
    head_low, head_high = _bounds(head_points)
    head_center = (head_low + head_high) * 0.5
    head_size = head_high - head_low
    radii = head_size * 0.5
    crown = [
        point
        for index, point in enumerate(head_points)
        if index % 3 == 0 and point.z >= maximum_z - 0.105
    ]
    rear = [
        point
        for index, point in enumerate(head_points)
        if index % 3 == 0
        and point.y >= head_center.y + 0.018
        and point.z >= maximum_z - 0.220
    ]
    hair_bvh = _evaluated_bvh(hair)
    hair_low, hair_high = _bounds(hair_points)
    report = {
        "schema_version": 1,
        "status": "REJECTED_ENGINEERING_DIAGNOSTIC",
        "input": str(input_path),
        "input_sha256": _sha256(input_path),
        "input_modified": False,
        "body_object": body.name,
        "hair_object": hair.name,
        "anatomical_forward_axis": "-Y",
        "target_head_ellipsoid": {
            "center_m": [round(float(value), 8) for value in head_center],
            "radii_m": [round(float(value), 8) for value in radii],
            "bounds_low_m": [round(float(value), 8) for value in head_low],
            "bounds_high_m": [round(float(value), 8) for value in head_high],
        },
        "evaluated_hair_bounds": {
            "low_m": [round(float(value), 8) for value in hair_low],
            "high_m": [round(float(value), 8) for value in hair_high],
            "center_m": [
                round(float(value), 8) for value in (hair_low + hair_high) * 0.5
            ],
            "radii_m": [
                round(float(value), 8) for value in (hair_high - hair_low) * 0.5
            ],
        },
        "crown_clearance": _sample_clearance(crown, head_center, radii, hair_bvh),
        "rear_clearance": _sample_clearance(rear, head_center, radii, hair_bvh),
        "outer_aabb_overlap_is_not_coverage_proof": True,
        "renders": _render_fit_views(
            render_dir,
            body,
            hair,
            head_center,
            head_high,
            head_size,
        ),
        "owner_approved": False,
        "runtime_assignment_allowed": False,
        "truth_note": (
            "Nearest evaluated hair geometry is compared with sampled target "
            "scalp. Negative signed clearance means the closest hair lies "
            "inside the target scalp and is expected to be punched through."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
