#!/usr/bin/env python3
"""Audit a supplied Louvre USDZ/GLB in Blender and optionally make a review LOD.

Run through Blender, for example::

    blender --background --python tools/audit_optimize_louvre_asset_blender.py -- \
      --input model.usdz --report audit.json --render audit.png

The report stores the source filename and hash, not the source directory.  This
keeps owner-only intake locations out of browser assets and review packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--render")
    parser.add_argument("--export-glb")
    parser.add_argument("--target-triangles", type=int, default=0)
    parser.add_argument("--max-texture-edge", type=int, default=2048)
    parser.add_argument("--render-width", type=int, default=1280)
    parser.add_argument("--render-height", type=int, default=720)
    parser.add_argument("--render-azimuth", type=float, default=-52.0)
    parser.add_argument("--render-elevation", type=float, default=0.62)
    parser.add_argument("--camera-position", nargs=3, type=float)
    parser.add_argument("--camera-target", nargs=3, type=float)
    parser.add_argument("--probe-xy", nargs=2, type=float)
    parser.add_argument("--probe-radius", type=float, default=2.0)
    parser.add_argument("--analyze-xy", nargs=2, type=float)
    parser.add_argument("--analyze-radius", type=float, default=1.0)
    parser.add_argument("--cutout-center-xy", nargs=2, type=float)
    parser.add_argument("--cutout-radius", type=float, default=0.0)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def import_asset(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix in {".usd", ".usda", ".usdc", ".usdz"}:
        bpy.ops.wm.usd_import(filepath=str(path), import_cameras=False, import_lights=False)
    elif suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    else:
        raise ValueError(f"Unsupported asset format: {suffix}")


def mesh_objects() -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def triangle_count(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        return Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0))
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def image_inventory() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for image in bpy.data.images:
        width, height = (int(image.size[0]), int(image.size[1])) if image.size else (0, 0)
        records.append(
            {
                "name": image.name,
                "width": width,
                "height": height,
                "estimated_rgba_bytes": width * height * 4,
                "packed": image.packed_file is not None,
            }
        )
    return records


def scene_metrics(import_seconds: float) -> dict[str, object]:
    objects = mesh_objects()
    bounds_min, bounds_max = world_bounds(objects)
    images = image_inventory()
    return {
        "import_seconds": round(import_seconds, 3),
        "mesh_objects": len(objects),
        "triangles": sum(triangle_count(obj) for obj in objects),
        "vertices": sum(len(obj.data.vertices) for obj in objects),
        "materials": len(bpy.data.materials),
        "images": images,
        "estimated_texture_rgba_bytes": sum(int(item["estimated_rgba_bytes"]) for item in images),
        "bounds_min": [round(value, 6) for value in bounds_min],
        "bounds_max": [round(value, 6) for value in bounds_max],
        "dimensions": [round(value, 6) for value in (bounds_max - bounds_min)],
        "animations": len(bpy.data.actions),
        "armatures": sum(obj.type == "ARMATURE" for obj in bpy.context.scene.objects),
        "mesh_inventory": [
            {
                "name": obj.name,
                "triangles": triangle_count(obj),
                "bounds_min": [round(value, 6) for value in world_bounds([obj])[0]],
                "bounds_max": [round(value, 6) for value in world_bounds([obj])[1]],
            }
            for obj in objects
        ],
    }


def probe_vertices(xy: list[float] | None, radius: float) -> dict[str, object] | None:
    if not xy:
        return None
    center = Vector((xy[0], xy[1], 0.0))
    samples: list[Vector] = []
    object_counts: dict[str, int] = {}
    for obj in mesh_objects():
        count = 0
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            if math.hypot(world.x - center.x, world.y - center.y) <= radius:
                samples.append(world)
                count += 1
        if count:
            object_counts[obj.name] = count
    return {
        "xy": [float(xy[0]), float(xy[1])],
        "radius": radius,
        "vertex_count": len(samples),
        "z_min": min((point.z for point in samples), default=None),
        "z_max": max((point.z for point in samples), default=None),
        "objects": object_counts,
    }


def percentile(sorted_values: list[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = max(0.0, min(1.0, fraction)) * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def analyze_local_region(xy: list[float] | None, radius: float) -> dict[str, object] | None:
    """Measure a small source-space region without recording its private path.

    This is useful for aligning a photogrammetry landmark with metric review
    geometry.  It deliberately reports evidence, not a claim that the scan is
    exact or survey-grade.
    """

    if not xy:
        return None
    samples: list[Vector] = []
    for obj in mesh_objects():
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            if math.hypot(world.x - xy[0], world.y - xy[1]) <= radius:
                samples.append(world)
    z_values = sorted(float(point.z) for point in samples)
    if not samples:
        return {
            "xy": [float(xy[0]), float(xy[1])],
            "radius": radius,
            "vertex_count": 0,
        }

    z_max = z_values[-1]
    top_band = [point for point in samples if point.z >= z_max - 0.03]
    top_percentile = percentile(z_values, 0.99)
    top_one_percent = [point for point in samples if point.z >= float(top_percentile)]

    def centroid(points: list[Vector]) -> list[float] | None:
        if not points:
            return None
        center = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
        return [round(float(value), 7) for value in center]

    fractions = (0.0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0)
    return {
        "xy": [float(xy[0]), float(xy[1])],
        "radius": radius,
        "vertex_count": len(samples),
        "z_percentiles": {
            f"p{int(round(fraction * 100)):03d}": round(float(percentile(z_values, fraction)), 7)
            for fraction in fractions
        },
        "top_band_threshold": round(z_max - 0.03, 7),
        "top_band_count": len(top_band),
        "top_band_centroid": centroid(top_band),
        "top_one_percent_count": len(top_one_percent),
        "top_one_percent_centroid": centroid(top_one_percent),
    }


def cutout_horizontal_region(xy: list[float] | None, radius: float) -> dict[str, object] | None:
    """Remove only faces whose world-space centers fall inside a circular cutout.

    The cutout lets a context scan surround independently validated entrance
    geometry.  It is not a boolean volume and must not be described as an exact
    architectural opening.
    """

    if not xy or radius <= 0.0:
        return None
    before = sum(triangle_count(obj) for obj in mesh_objects())
    affected: list[dict[str, object]] = []
    for obj in mesh_objects():
        mesh = obj.data
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()
            remove = []
            for face in bm.faces:
                world = obj.matrix_world @ face.calc_center_median()
                if math.hypot(world.x - xy[0], world.y - xy[1]) < radius:
                    remove.append(face)
            if not remove:
                continue
            source_faces = len(bm.faces)
            bmesh.ops.delete(bm, geom=remove, context="FACES")
            bm.to_mesh(mesh)
            mesh.update()
            affected.append(
                {
                    "object": obj.name,
                    "source_faces": source_faces,
                    "removed_faces": len(remove),
                    "result_faces": len(mesh.polygons),
                }
            )
        finally:
            bm.free()
    after = sum(triangle_count(obj) for obj in mesh_objects())
    return {
        "shape": "circular_face_center_cutout",
        "center_xy": [float(xy[0]), float(xy[1])],
        "radius": radius,
        "source_triangles": before,
        "result_triangles": after,
        "removed_triangles": before - after,
        "affected_objects": affected,
        "exact_boolean_or_survey_cutout": False,
    }


def optimize_meshes(target_triangles: int, max_texture_edge: int) -> dict[str, object]:
    objects = mesh_objects()
    before = sum(triangle_count(obj) for obj in objects)
    ratio = min(1.0, target_triangles / before) if target_triangles > 0 and before else 1.0
    applied: list[dict[str, object]] = []
    if ratio < 0.999:
        for obj in objects:
            source_triangles = triangle_count(obj)
            if source_triangles < 200:
                continue
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            modifier = obj.modifiers.new(name="Review_LOD_Decimate", type="DECIMATE")
            modifier.decimate_type = "COLLAPSE"
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                applied.append(
                    {
                        "object": obj.name,
                        "source_triangles": source_triangles,
                        "result_triangles": triangle_count(obj),
                    }
                )
            finally:
                obj.select_set(False)

    resized: list[dict[str, object]] = []
    for image in bpy.data.images:
        width, height = int(image.size[0]), int(image.size[1])
        longest = max(width, height)
        if longest <= max_texture_edge or longest == 0:
            continue
        scale = max_texture_edge / longest
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        image.scale(new_width, new_height)
        resized.append(
            {
                "name": image.name,
                "source": [width, height],
                "result": [new_width, new_height],
            }
        )
    after = sum(triangle_count(obj) for obj in objects)
    return {
        "requested_target_triangles": target_triangles,
        "global_decimate_ratio": ratio,
        "source_triangles": before,
        "result_triangles": after,
        "objects_decimated": applied,
        "textures_resized": resized,
    }


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_scene(
    path: Path,
    width: int,
    height: int,
    azimuth_degrees: float,
    elevation_factor: float,
    camera_position: list[float] | None,
    camera_target: list[float] | None,
) -> None:
    objects = mesh_objects()
    bounds_min, bounds_max = world_bounds(objects)
    center = (bounds_min + bounds_max) * 0.5
    dimensions = bounds_max - bounds_min
    horizontal = max(dimensions.x, dimensions.y, 1.0)
    vertical = max(dimensions.z, 1.0)

    camera_data = bpy.data.cameras.new("AuditCamera")
    camera = bpy.data.objects.new("AuditCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera_data.lens = 50
    camera_data.clip_end = max(horizontal, vertical) * 20
    azimuth = math.radians(azimuth_degrees)
    radius = horizontal * 1.34
    if camera_position:
        camera.location = Vector(camera_position)
    else:
        camera.location = center + Vector(
            (
                math.cos(azimuth) * radius,
                math.sin(azimuth) * radius,
                max(vertical * elevation_factor, horizontal * 0.06),
            )
        )
    target = Vector(camera_target) if camera_target else center + Vector((0.0, 0.0, vertical * 0.02))
    point_camera(camera, target)
    bpy.context.scene.camera = camera

    sun_data = bpy.data.lights.new("AuditSun", type="SUN")
    sun_data.energy = 2.0
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new("AuditSun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(34), math.radians(-22), math.radians(-28))

    world = bpy.context.scene.world or bpy.data.worlds.new("AuditWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.32, 0.42, 0.58, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.resolution_percentage = 100
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def export_glb(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects():
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_image_format="AUTO",
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
    )


def main() -> None:
    args = parse_args()
    source = Path(args.input).resolve()
    report_path = Path(args.report).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    reset_scene()
    started = time.perf_counter()
    import_asset(source)
    imported_seconds = time.perf_counter() - started
    imported = scene_metrics(imported_seconds)

    local_region_analysis = analyze_local_region(args.analyze_xy, args.analyze_radius)
    cutout = cutout_horizontal_region(args.cutout_center_xy, args.cutout_radius)

    optimization = None
    if args.target_triangles > 0 or args.export_glb:
        optimization = optimize_meshes(args.target_triangles, args.max_texture_edge)

    render_seconds = None
    if args.render:
        started = time.perf_counter()
        render_scene(
            Path(args.render).resolve(),
            args.render_width,
            args.render_height,
            args.render_azimuth,
            args.render_elevation,
            args.camera_position,
            args.camera_target,
        )
        render_seconds = round(time.perf_counter() - started, 3)

    export_record = None
    if args.export_glb:
        export_path = Path(args.export_glb).resolve()
        started = time.perf_counter()
        export_glb(export_path)
        export_record = {
            "filename": export_path.name,
            "bytes": export_path.stat().st_size,
            "sha256": sha256_file(export_path),
            "export_seconds": round(time.perf_counter() - started, 3),
        }

    report = {
        "schema_version": 1,
        "tool": "audit_optimize_louvre_asset_blender",
        "source": {
            "filename": source.name,
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
            "private_source_directory_redacted": True,
        },
        "imported": imported,
        "optimization": optimization,
        "cutout": cutout,
        "post_optimization": scene_metrics(imported_seconds) if optimization else None,
        "vertex_probe": probe_vertices(args.probe_xy, args.probe_radius),
        "local_region_analysis": local_region_analysis,
        "render_seconds": render_seconds,
        "export": export_record,
        "truth": {
            "visual_reference_asset_only": True,
            "exact_scan_claim_allowed": False,
            "working_doors_or_vertical_transport_proven": False,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
