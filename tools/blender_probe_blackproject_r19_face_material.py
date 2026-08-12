#!/usr/bin/env python3
"""Append-only R19 face, brow, and warm textured-skin diagnostic.

The worker imports the exact enrolled CC-BY-4.0 BlackProject source, removes
all scalp-hair meshes, renders each eyebrow option separately, then creates
derived material copies that retain the packed albedo/roughness/normal graph
while adding one bounded warm tint before the Principled base-color input.
It never writes the source or any runtime/assigned avatar package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r7_adult_surface_trial as helpers  # noqa: E402


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
SKIN_MATERIAL_NAMES = {"Torso", "Arms", "Legs", "Face", "Ears", "Genitalia"}


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


def node_inventory(material: bpy.types.Material) -> dict[str, object]:
    if not material.use_nodes or material.node_tree is None:
        return {"uses_nodes": False, "nodes": [], "links": []}
    nodes = []
    for node in material.node_tree.nodes:
        record: dict[str, object] = {
            "name": node.name,
            "label": node.label,
            "type": node.bl_idname,
        }
        if node.bl_idname == "ShaderNodeTexImage" and node.image is not None:
            record["image"] = {
                "name": node.image.name,
                "size": [int(node.image.size[0]), int(node.image.size[1])],
                "packed": node.image.packed_file is not None,
                "colorspace": node.image.colorspace_settings.name,
            }
        nodes.append(record)
    links = [
        {
            "from_node": link.from_node.name,
            "from_socket": link.from_socket.name,
            "to_node": link.to_node.name,
            "to_socket": link.to_socket.name,
        }
        for link in material.node_tree.links
    ]
    return {"uses_nodes": True, "nodes": nodes, "links": links}


def clone_with_warm_tint(
    material: bpy.types.Material,
    *,
    tint: tuple[float, float, float, float],
    strength: float,
) -> tuple[bpy.types.Material, dict[str, object]]:
    derived = material.copy()
    derived.name = f"R19_WarmTexture_{material.name}"
    if not derived.use_nodes or derived.node_tree is None:
        raise RuntimeError(f"skin material {material.name} has no node graph")
    nodes = derived.node_tree.nodes
    links = derived.node_tree.links
    principals = [node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"]
    if len(principals) != 1:
        raise RuntimeError(
            f"skin material {material.name} expected one Principled node, got {len(principals)}"
        )
    principal = principals[0]
    base = principal.inputs.get("Base Color")
    if base is None:
        raise RuntimeError(f"skin material {material.name} has no Base Color socket")
    incoming = list(base.links)
    if len(incoming) != 1:
        raise RuntimeError(
            f"skin material {material.name} expected one Base Color link, got {len(incoming)}"
        )
    source_socket = incoming[0].from_socket
    links.remove(incoming[0])
    mix = nodes.new("ShaderNodeMixRGB")
    mix.name = "R19_Bounded_Warm_Texture_Tint"
    mix.label = "R19 bounded warm tint; source texture retained"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = float(strength)
    mix.inputs[2].default_value = tint
    links.new(source_socket, mix.inputs[1])
    links.new(mix.outputs[0], base)
    return derived, {
        "source_material": material.name,
        "derived_material": derived.name,
        "blend": "MULTIPLY",
        "strength": float(strength),
        "tint_linear_rgba": [float(value) for value in tint],
        "source_base_color_link_retained": True,
        "other_graph_links_unchanged": True,
    }


def add_area_light(scene, name, location, energy, size, target=(0.0, 0.0, 1.0)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(scene, camera, path: Path, location, target, ortho_scale):
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def set_brow_visibility(brows: list[bpy.types.Object], selected: bpy.types.Object | None):
    for brow in brows:
        visible = brow is selected
        brow.hide_render = not visible
        brow.hide_viewport = not visible
        brow.hide_set(not visible)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve(strict=True)
    source = (root / config["source_path"]).resolve(strict=True)
    output_dir = (root / config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    if sha256_file(source) != SOURCE_SHA256:
        raise RuntimeError("enrolled source SHA-256 mismatch")

    helpers.clear_scene()
    imported = helpers.import_glb(source)
    removed_hair = []
    for obj in list(imported):
        mesh_name = obj.data.name if obj.type == "MESH" else ""
        if obj.type == "MESH" and mesh_name.startswith("Hair_"):
            removed_hair.append(mesh_name)
            bpy.data.objects.remove(obj, do_unlink=True)

    # Objects deleted above leave invalid RNA references in the original
    # importer return list. Rebuild the live mesh inventory from bpy.data.
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    brows = sorted(
        [obj for obj in meshes if obj.data.name.startswith("Eye_Brows_")],
        key=lambda obj: (obj.data.name, obj.name),
    )
    skin_materials = sorted(
        [material for material in bpy.data.materials if material.name in SKIN_MATERIAL_NAMES],
        key=lambda material: material.name,
    )
    if not brows:
        raise RuntimeError("no BlackProject eyebrow candidates found")
    if len(skin_materials) < 5:
        raise RuntimeError(f"incomplete skin material set: {[m.name for m in skin_materials]}")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(config.get("resolution", 900))
    scene.render.resolution_y = int(config.get("resolution", 900))
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.009, 0.014, 0.022)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = float(config.get("exposure", -0.65))
    add_area_light(scene, "R19_Key", (-2.0, -2.8, 2.6), 650.0, 2.1, (0.0, 0.0, 1.2))
    add_area_light(scene, "R19_Fill", (2.4, -1.8, 1.8), 330.0, 2.0, (0.0, 0.0, 1.15))
    add_area_light(scene, "R19_Rim", (0.0, 2.3, 2.2), 420.0, 1.7, (0.0, 0.0, 1.3))
    camera_data = bpy.data.cameras.new("R19_FACE_MATERIAL_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_FACE_MATERIAL_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    set_brow_visibility(brows, None)
    render(
        scene,
        camera,
        output_dir / "source_texture_no_brows_face.png",
        (0.0, -2.5, 1.52),
        (0.0, 0.0, 1.52),
        0.54,
    )
    brow_renders = []
    for index, brow in enumerate(brows, start=1):
        set_brow_visibility(brows, brow)
        filename = f"source_texture_brow_{index:02d}_{brow.data.name}.png".replace(".001", "_001")
        render(scene, camera, output_dir / filename, (0.0, -2.5, 1.52), (0.0, 0.0, 1.52), 0.54)
        brow_renders.append({"object": brow.name, "mesh": brow.data.name, "render": filename})

    selected_index = int(config.get("selected_brow_index", 1))
    if not 0 <= selected_index < len(brows):
        raise ValueError("selected_brow_index is outside the discovered brow list")
    selected_brow = brows[selected_index]
    set_brow_visibility(brows, selected_brow)

    material_before = {material.name: node_inventory(material) for material in skin_materials}
    derived_records = []
    tint = tuple(float(value) for value in config["warm_tint_linear_rgba"])
    strength = float(config["warm_tint_strength"])
    mapping: dict[bpy.types.Material, bpy.types.Material] = {}
    for material in skin_materials:
        derived, record = clone_with_warm_tint(material, tint=tint, strength=strength)
        mapping[material] = derived
        derived_records.append(record)
    rebound_slots = []
    for obj in meshes:
        for slot_index, slot in enumerate(obj.material_slots):
            if slot.material in mapping:
                original = slot.material
                slot.material = mapping[original]
                rebound_slots.append(
                    {
                        "object": obj.name,
                        "mesh": obj.data.name,
                        "slot": int(slot_index),
                        "source_material": original.name,
                        "derived_material": slot.material.name,
                    }
                )

    render(scene, camera, output_dir / "warm_texture_face_front.png", (0.0, -2.5, 1.52), (0.0, 0.0, 1.52), 0.54)
    render(scene, camera, output_dir / "warm_texture_face_left_three_quarter.png", (-0.38, -2.2, 1.52), (0.0, 0.0, 1.52), 0.54)
    render(scene, camera, output_dir / "warm_texture_body_front.png", (0.0, -3.0, 0.88), (0.0, 0.0, 0.88), 1.82)

    blend_path = output_dir / "r19_face_material_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    report = {
        "schema_version": 1,
        "status": "PRIVATE_INACTIVE_DIAGNOSTIC_OWNER_REVIEW_REQUIRED",
        "source": {
            "path": str(source.relative_to(root)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
            "license": "CC BY 4.0",
            "unchanged_after_probe": sha256_file(source) == SOURCE_SHA256,
        },
        "scalp_hair": {
            "removed_meshes": sorted(removed_hair),
            "runtime_dependency_created": False,
        },
        "brows": {
            "inventory": brow_renders,
            "selected_for_warm_comparison": {
                "index": selected_index,
                "object": selected_brow.name,
                "mesh": selected_brow.data.name,
            },
            "visual_selection_is_not_owner_approval": True,
        },
        "materials": {
            "source_graph_inventory": material_before,
            "derived_tint_records": derived_records,
            "rebound_slots": rebound_slots,
            "packed_source_texture_graph_retained": True,
            "flat_single_color_replacement_used": False,
        },
        "outputs": {
            "blend": blend_path.name,
            "blend_sha256": sha256_file(blend_path),
            "renders": sorted(path.name for path in output_dir.glob("*.png")),
        },
        "runtime_or_assignment_changed": False,
        "candidate_built": False,
        "owner_approval_claimed": False,
    }
    report_path = output_dir / "FACE_MATERIAL_PROBE.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
