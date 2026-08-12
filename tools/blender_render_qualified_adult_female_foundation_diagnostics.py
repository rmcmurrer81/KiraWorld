"""Render the exact qualified adult-female foundation without mutating it.

The source Blend is opened read-only for an append-only visual diagnostic.  The
renders are engineering evidence only: they do not create Kira, attach a rig,
approve anatomy, or change runtime state.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELATIVE = Path(
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend"
)
SOURCE_SHA256 = "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f"
ALLOWED_OUTPUT_PARENT = Path(
    "RecoverySprint/continuation_20260802/r19_foundation_visual_diagnostic"
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def _topology(obj: bpy.types.Object) -> dict[str, object]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unseen = set(bm.verts)
    components: list[int] = []
    while unseen:
        seed = unseen.pop()
        queue = [seed]
        size = 0
        while queue:
            vertex = queue.pop()
            size += 1
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
        components.append(size)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "connected_components": len(components),
        "component_vertex_counts": sorted(components, reverse=True),
        "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
        "nonmanifold_internal_edges": sum(
            not edge.is_manifold and not edge.is_boundary for edge in bm.edges
        ),
    }
    bm.free()
    return result


def _material(
    name: str, color: tuple[float, float, float, float], roughness: float
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        if "Subsurface Weight" in bsdf.inputs:
            bsdf.inputs["Subsurface Weight"].default_value = 0.045
    return material


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output: Path,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    _look_at(camera, target)
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = _args()
    source = (ROOT / SOURCE_RELATIVE).resolve(strict=True)
    if _sha256(source) != SOURCE_SHA256:
        raise RuntimeError("qualified foundation hash drifted")

    output = (ROOT / Path(args.output_dir)).resolve()
    allowed_parent = (ROOT / ALLOWED_OUTPUT_PARENT).resolve()
    if output.parent != allowed_parent or not output.name.startswith("attempt_"):
        raise RuntimeError("output must be an append-only attempt under the diagnostic root")
    if output.exists():
        raise RuntimeError("append-only diagnostic output already exists")
    output.mkdir(parents=True)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected exactly one mesh, got {[obj.name for obj in meshes]}")
    body = meshes[0]
    source_topology = _topology(body)

    for obj in list(bpy.context.scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    skin = _material("Foundation_Neutral_Warm_Skin", (0.48, 0.285, 0.215, 1.0), 0.56)
    body.data.materials.clear()
    body.data.materials.append(skin)
    for polygon in body.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.035, 0.055)
    scene.view_settings.look = "AgX - Medium High Contrast"

    minimum, maximum = _bounds(body)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    depth = maximum.y - minimum.y
    distance = max(height * 1.8, depth * 5.0)

    target = Vector((center.x, center.y, minimum.z + height * 0.51))
    for name, energy, location, size in (
        ("Key", 1050.0, (2.6, -4.2, 3.2), 4.2),
        ("Fill", 700.0, (-3.0, -2.7, 2.8), 3.8),
        ("Top", 750.0, (0.0, -0.4, 6.2), 4.0),
        ("Rear", 520.0, (1.5, 3.4, 3.6), 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

    camera_data = bpy.data.cameras.new("FoundationDiagnosticCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("FoundationDiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)

    pelvis = Vector((center.x, center.y - depth * 0.10, minimum.z + height * 0.485))
    face = Vector((center.x, center.y - depth * 0.12, minimum.z + height * 0.895))
    left_hand = Vector((minimum.x + (maximum.x - minimum.x) * 0.08, center.y, minimum.z + height * 0.56))
    right_hand = Vector((maximum.x - (maximum.x - minimum.x) * 0.08, center.y, minimum.z + height * 0.56))
    feet = Vector((center.x, center.y, minimum.z + height * 0.055))
    knees = Vector((center.x, center.y, minimum.z + height * 0.285))

    views = {
        "full_front.png": (Vector((center.x, minimum.y - distance, target.z)), target, height * 1.08),
        "full_left_three_quarter.png": (Vector((center.x - distance * 0.70, minimum.y - distance * 0.70, target.z)), target, height * 1.08),
        "full_side.png": (Vector((minimum.x - distance, center.y, target.z)), target, height * 1.08),
        "full_rear.png": (Vector((center.x, maximum.y + distance, target.z)), target, height * 1.08),
        "face_front.png": (Vector((face.x, minimum.y - distance, face.z)), face, height * 0.24),
        "pelvis_front.png": (Vector((pelvis.x, minimum.y - distance, pelvis.z)), pelvis, height * 0.28),
        "pelvis_left_three_quarter.png": (Vector((pelvis.x - distance * 0.70, minimum.y - distance * 0.70, pelvis.z)), pelvis, height * 0.28),
        "pelvis_side.png": (Vector((minimum.x - distance, pelvis.y, pelvis.z)), pelvis, height * 0.28),
        "pelvis_rear.png": (Vector((pelvis.x, maximum.y + distance, pelvis.z)), pelvis, height * 0.28),
        "hands_front.png": (Vector((center.x, minimum.y - distance, left_hand.z)), Vector((center.x, center.y, left_hand.z)), height * 0.34),
        "feet_front.png": (Vector((feet.x, minimum.y - distance, feet.z)), feet, height * 0.18),
        "knees_front.png": (Vector((knees.x, minimum.y - distance, knees.z)), knees, height * 0.27),
    }
    for filename, (location, view_target, scale) in views.items():
        _render(scene, camera, output / filename, location, view_target, scale)

    wire = body.copy()
    wire.data = body.data.copy()
    wire.name = "FoundationDiagnosticWire"
    bpy.context.collection.objects.link(wire)
    wire.data.materials.clear()
    wire.data.materials.append(_material("Foundation_Wire_Cyan", (0.01, 0.45, 0.58, 1.0), 0.30))
    modifier = wire.modifiers.new("FoundationTopologyWire", "WIREFRAME")
    modifier.thickness = max(height * 0.00075, 0.0008)
    modifier.offset = 1.0
    modifier.use_replace = True
    for filename, (location, view_target, scale) in {
        "pelvis_front_wire.png": views["pelvis_front.png"],
        "pelvis_left_three_quarter_wire.png": views["pelvis_left_three_quarter.png"],
        "knees_front_wire.png": views["knees_front.png"],
    }.items():
        _render(scene, camera, output / filename, location, view_target, scale)

    report = {
        "schema": "kira.avatar.qualified_adult_female_foundation_visual_diagnostic.v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "VISUAL_DIAGNOSTIC_ONLY_NOT_KIRA_NOT_APPROVED",
        "source": SOURCE_RELATIVE.as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_modified": False,
        "runtime_mutation_performed": False,
        "rendered_views": sorted(views) + [
            "pelvis_front_wire.png",
            "pelvis_left_three_quarter_wire.png",
            "knees_front_wire.png",
        ],
        "topology_observed": source_topology,
        "truth_note": (
            "These renders expose the exact qualified generic foundation for visual "
            "selection. They do not prove realism, Kira identity, rigging, movement, "
            "owner approval, or runtime readiness."
        ),
    }
    (output / "DIAGNOSTIC_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
