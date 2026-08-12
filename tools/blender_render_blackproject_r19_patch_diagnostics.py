#!/usr/bin/env python3
"""Render an immutable diagnostic of the licensed BlackProject body interface.

The worker validates the exact enrolled GLB, imports it into an empty temporary
Blender scene, removes no source file and saves no Blend.  It writes only
append-only diagnostic PNG/JSON evidence supplied by ``--config``.  The goal is
to expose the 34-vertex adult-region boundary, source topology, UV/material
state, and central self-intersection locality before an R19 derivative is
authored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r7_adult_surface_trial as helpers  # noqa: E402
from blender_build_kira_temporary_functional_body_blackproject import (  # noqa: E402
    ordered_boundary_cycles,
)
from blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"
BODY_MESH_NAMES = (
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Face_0",
    "Ariel_Mesh_Ears_0",
)


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


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def material_record(obj: bpy.types.Object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for slot_index, slot in enumerate(obj.material_slots):
        material = slot.material
        images: list[dict[str, object]] = []
        if material is not None and material.use_nodes and material.node_tree is not None:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    image = node.image
                    images.append(
                        {
                            "name": image.name,
                            "source": image.source,
                            "packed": image.packed_file is not None,
                            "filepath": image.filepath,
                            "size": [int(image.size[0]), int(image.size[1])],
                        }
                    )
        rows.append(
            {
                "slot": slot_index,
                "material": material.name if material else None,
                "uses_nodes": bool(material and material.use_nodes),
                "images": images,
            }
        )
    return rows


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, Vector(target))
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def add_wire_duplicate(obj: bpy.types.Object) -> bpy.types.Object:
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    duplicate.name = "R19_DIAGNOSTIC_ADULT_PATCH_WIRE"
    bpy.context.scene.collection.objects.link(duplicate)
    duplicate.data.materials.clear()
    material = bpy.data.materials.new("R19_DIAGNOSTIC_WIRE_CYAN")
    material.diffuse_color = (0.0, 0.8, 1.0, 1.0)
    duplicate.data.materials.append(material)
    for polygon in duplicate.data.polygons:
        polygon.material_index = 0
    modifier = duplicate.modifiers.new("R19_DIAGNOSTIC_WIREFRAME", "WIREFRAME")
    # The imported GLB carries a 0.01 object scale, so this local thickness is
    # approximately 0.35 mm in the rendered world.  A meter-scale value made
    # attempt_01's wire evidence nearly invisible.
    modifier.thickness = 0.035
    modifier.use_replace = True
    modifier.use_even_offset = True
    duplicate.show_in_front = True
    duplicate["diagnostic_only"] = True
    return duplicate


def main() -> int:
    args = parse_args()
    config = json.loads(Path(args.config).resolve(strict=True).read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = (project_root / config["source_path"]).resolve(strict=True)
    output_dir = (project_root / config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("BlackProject source SHA-256 mismatch")

    helpers.clear_scene()
    imported = helpers.import_glb(source)
    meshes = {obj.data.name: obj for obj in imported if obj.type == "MESH"}
    if ADULT_MESH_NAME not in meshes:
        raise ValueError("licensed adult-region mesh missing")
    adult = meshes[ADULT_MESH_NAME]
    cycles = ordered_boundary_cycles(adult)
    if len(cycles) != 1 or len(cycles[0]) != 34:
        raise ValueError(f"unexpected adult boundary cycles: {[len(row) for row in cycles]}")

    adult_bm = bmesh.new()
    adult_bm.from_mesh(adult.data)
    intersection = exact_nonadjacent_intersection_report(adult_bm)
    adult_bm.free()
    source_report = {
        "schema_version": 1,
        "mode": "R19_BLACKPROJECT_SOURCE_PATCH_IMMUTABLE_DIAGNOSTIC",
        "source": {
            "project_relative_path": str(source.relative_to(project_root)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
            "unchanged": True,
        },
        "adult_patch": {
            "object": adult.name,
            "mesh": adult.data.name,
            "vertices": len(adult.data.vertices),
            "edges": len(adult.data.edges),
            "polygons": len(adult.data.polygons),
            "uv_layers": [layer.name for layer in adult.data.uv_layers],
            "boundary_cycles": [len(row) for row in cycles],
            "boundary_indices": cycles[0],
            "materials": material_record(adult),
            "exact_nonadjacent_intersections": intersection,
        },
        "body_materials": {
            name: material_record(meshes[name]) for name in BODY_MESH_NAMES if name in meshes
        },
        "truth": {
            "candidate_authored": False,
            "blend_saved": False,
            "runtime_changed": False,
            "source_modified": False,
        },
    }
    report_path = output_dir / "SOURCE_PATCH_DIAGNOSTIC.json"
    report_path.write_text(json.dumps(source_report, indent=2) + "\n", encoding="utf-8")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.025, 0.035)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    camera_data = bpy.data.cameras.new("R19_DIAGNOSTIC_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_DIAGNOSTIC_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    hair_tokens = ("Hair_", "Cap")
    for obj in imported:
        if obj.type == "MESH" and any(token in obj.data.name for token in hair_tokens):
            obj.hide_render = True

    render(
        scene,
        camera,
        output_dir / "source_body_bald_front.png",
        (0.0, -3.0, 0.90),
        (0.0, 0.0, 0.90),
        1.78,
    )
    render(
        scene,
        camera,
        output_dir / "source_adult_patch_front.png",
        (0.0, -2.0, 0.865),
        (0.0, -0.025, 0.865),
        0.19,
    )
    render(
        scene,
        camera,
        output_dir / "source_adult_patch_three_quarter.png",
        (0.22, -0.34, 0.87),
        (0.0, -0.02, 0.865),
        0.19,
    )
    render(
        scene,
        camera,
        output_dir / "source_adult_patch_side.png",
        (0.30, 0.0, 0.865),
        (0.0, -0.01, 0.865),
        0.19,
    )

    for obj in imported:
        if obj.type == "MESH":
            obj.hide_render = obj != adult
    wire = add_wire_duplicate(adult)
    # Overlay the wire on the original surface so topology and silhouette are
    # readable together.
    adult.hide_render = False
    render(
        scene,
        camera,
        output_dir / "source_adult_patch_wire_front.png",
        (0.0, -2.0, 0.865),
        (0.0, -0.025, 0.865),
        0.19,
    )
    render(
        scene,
        camera,
        output_dir / "source_adult_patch_wire_three_quarter.png",
        (0.22, -0.34, 0.87),
        (0.0, -0.02, 0.865),
        0.19,
    )
    wire.hide_render = True
    adult.hide_render = False

    after_hash = sha256_file(source)
    if after_hash != SOURCE_SHA256:
        raise RuntimeError("source changed during read-only diagnostic")
    source_report["source"]["sha256_after"] = after_hash
    source_report["outputs"] = sorted(path.name for path in output_dir.glob("*.png"))
    report_path.write_text(json.dumps(source_report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
