"""Render non-destructive V23 static-likeness diagnostic passes.

Usage:
    blender --background --python \
      tools/blender_render_biological_robert_v23_diagnostics.py -- \
      path/to/candidate.blend [optional/output/directory]

The opened candidate is never saved.  The script renders:

* close pelvis flat-material, single-color wireframe, world-normal, and
  albedo-only passes from front, side, and three-quarter views;
* material and wireframe hair/head-silhouette views; and
* material and wireframe hand/nail views from the front and rear.

The renderer intentionally separates material, geometry, and lighting evidence
so a visually bad transition cannot pass merely because a topology count did.
It also emits binary silhouette masks.  Those masks let a separate validator
measure real background tunnels in the encoded image instead of mistaking dark
skin shading for an open spatial gap.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


def parse_arguments() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise SystemExit("Expected: -- <candidate.blend> [output-directory]")
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if not arguments:
        raise SystemExit("Missing candidate .blend path")
    source = Path(arguments[0]).resolve()
    if not source.is_file():
        raise SystemExit(f"Candidate does not exist: {source}")
    output = (
        Path(arguments[1]).resolve()
        if len(arguments) > 1
        else source.parent / "diagnostics_v23"
    )
    return source, output


SOURCE, OUTPUT = parse_arguments()
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
if not mesh_objects:
    raise SystemExit("Candidate contains no mesh objects")

# The body is the dominant mesh in every current V23 static branch.  This is
# safer than depending on a version-specific object name.
body = max(mesh_objects, key=lambda obj: len(obj.data.vertices))
body_min = min((body.matrix_world @ Vector(corner)).z for corner in body.bound_box)
body_max = max((body.matrix_world @ Vector(corner)).z for corner in body.bound_box)
body_height = body_max - body_min
if body_height <= 0:
    raise SystemExit("Body has invalid bounds")

hair_objects = []
for obj in mesh_objects:
    if obj == body:
        continue
    world_center = obj.matrix_world @ Vector(
        (
            sum(corner[0] for corner in obj.bound_box) / 8.0,
            sum(corner[1] for corner in obj.bound_box) / 8.0,
            sum(corner[2] for corner in obj.bound_box) / 8.0,
        )
    )
    if world_center.z >= body_min + body_height * 0.78:
        hair_objects.append(obj)

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.frame_set(1)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000

world = scene.world or bpy.data.worlds.new("V23DiagnosticWorld")
scene.world = world
world.color = (0.035, 0.038, 0.045)

camera_data = bpy.data.cameras.new("V23DiagnosticCamera")
camera = bpy.data.objects.new("V23DiagnosticCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

pelvis_z = body_min + body_height * 0.402
face_z = body_min + body_height * 0.915
hand_z = body_min + body_height * 0.462
unit = body_height

# Locate the hands from the fingernail material when it is available.  This is
# more reliable than a hard-coded proportion because older failed branches
# moved or globally scaled the limbs.
nail_material_indices = {
    index
    for index, material in enumerate(body.data.materials)
    if material and "nail" in material.name.lower()
}
nail_vertex_indices: set[int] = set()
for polygon in body.data.polygons:
    if polygon.material_index in nail_material_indices:
        nail_vertex_indices.update(polygon.vertices)
fingernail_points = [
    body.matrix_world @ body.data.vertices[index].co
    for index in nail_vertex_indices
    if (body.matrix_world @ body.data.vertices[index].co).z
    > body_min + body_height * 0.32
]
if fingernail_points:
    positive = [point for point in fingernail_points if point.x > 0]
    negative = [point for point in fingernail_points if point.x < 0]
    hand_x = (
        (
            sum(point.x for point in positive) / len(positive)
            - sum(point.x for point in negative) / len(negative)
        )
        / 2.0
        if positive and negative
        else body_height * 0.175
    )
    hand_z = sum(point.z for point in fingernail_points) / len(fingernail_points)
else:
    hand_x = body_height * 0.175

views = {
    "pelvis_front": (
        (0.0, -0.69 * unit, pelvis_z + 0.01 * unit),
        (0.0, -0.015 * unit, pelvis_z),
        72,
    ),
    "pelvis_side": (
        (0.56 * unit, -0.34 * unit, pelvis_z + 0.01 * unit),
        (0.0, -0.045 * unit, pelvis_z),
        72,
    ),
    "pelvis_three_quarter": (
        (0.47 * unit, -0.52 * unit, pelvis_z + 0.02 * unit),
        (0.0, -0.02 * unit, pelvis_z),
        72,
    ),
    "hair_front": (
        (0.0, -0.84 * unit, face_z),
        (0.0, 0.0, face_z),
        76,
    ),
    "hair_left_profile": (
        (-0.84 * unit, 0.0, face_z),
        (0.0, 0.0, face_z),
        76,
    ),
    "hair_right_profile": (
        (0.84 * unit, 0.0, face_z),
        (0.0, 0.0, face_z),
        76,
    ),
    "hand_left_front": (
        (-hand_x, -0.48 * unit, hand_z),
        (-hand_x, -0.045 * unit, hand_z),
        84,
    ),
    "hand_right_front": (
        (hand_x, -0.48 * unit, hand_z),
        (hand_x, -0.045 * unit, hand_z),
        84,
    ),
    "hand_left_rear": (
        (-hand_x, 0.48 * unit, hand_z),
        (-hand_x, -0.045 * unit, hand_z),
        84,
    ),
    "hand_right_rear": (
        (hand_x, 0.48 * unit, hand_z),
        (hand_x, -0.045 * unit, hand_z),
        84,
    ),
}

rendered: list[str] = []


def position_camera(view_name: str) -> None:
    location, target, lens = views[view_name]
    camera.location = location
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens


def render(name: str, view_name: str) -> None:
    position_camera(view_name)
    destination = OUTPUT / f"{name}.png"
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    rendered.append(str(destination))


def configure_workbench(*, light: str, color_type: str) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = light
    scene.display.shading.color_type = color_type
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.display.shading.show_specular_highlight = False
    scene.display.shading.show_xray = False
    scene.display.shading.background_type = "THEME"


def set_wire(objects: list[bpy.types.Object], enabled: bool) -> None:
    for obj in objects:
        obj.show_wire = enabled
        obj.show_all_edges = enabled


def make_emission_output(
    material: bpy.types.Material,
    color_output: bpy.types.NodeSocket,
) -> None:
    emission = material.node_tree.nodes.new("ShaderNodeEmission")
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(color_output, emission.inputs["Color"])
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])


def build_albedo_material(source: bpy.types.Material | None, index: int) -> bpy.types.Material:
    """Build an unlit approximation of a source material's base color."""
    name = source.name if source else f"slot_{index}"
    material = bpy.data.materials.new(f"V23_DIAGNOSTIC_ALBEDO_{index}_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()

    image_node = None
    principled = None
    if source and source.use_nodes and source.node_tree:
        for node in source.node_tree.nodes:
            lowered = node.name.lower()
            if node.bl_idname == "ShaderNodeTexImage" and "albedo" in lowered:
                image_node = node
                break
        principled = next(
            (
                node
                for node in source.node_tree.nodes
                if node.bl_idname == "ShaderNodeBsdfPrincipled"
            ),
            None,
        )

    if image_node and image_node.image:
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image_node.image
        texture.interpolation = image_node.interpolation
        texture.projection = image_node.projection
        texture.extension = image_node.extension
        make_emission_output(material, texture.outputs["Color"])
    else:
        rgb = nodes.new("ShaderNodeRGB")
        if principled:
            rgb.outputs["Color"].default_value = principled.inputs[
                "Base Color"
            ].default_value
        elif source:
            rgb.outputs["Color"].default_value = source.diffuse_color
        else:
            rgb.outputs["Color"].default_value = (0.55, 0.55, 0.55, 1.0)
        make_emission_output(material, rgb.outputs["Color"])
    return material


def replace_materials_with_albedo() -> dict[str, list[bpy.types.Material | None]]:
    saved: dict[str, list[bpy.types.Material | None]] = {}
    cache: dict[int, bpy.types.Material] = {}
    for obj in mesh_objects:
        saved[obj.name] = [slot.material for slot in obj.material_slots]
        for index, slot in enumerate(obj.material_slots):
            source = slot.material
            key = source.as_pointer() if source else -(index + 1)
            if key not in cache:
                cache[key] = build_albedo_material(source, len(cache))
            slot.material = cache[key]
    return saved


def restore_materials(saved: dict[str, list[bpy.types.Material | None]]) -> None:
    for object_name, materials in saved.items():
        obj = bpy.data.objects.get(object_name)
        if not obj:
            continue
        for slot, material in zip(obj.material_slots, materials):
            slot.material = material


# Flat-material close pelvis diagnostics retain simple studio form shading while
# disabling AO, cavity, shadows, and specular.
configure_workbench(light="STUDIO", color_type="MATERIAL")
for view_name in ("pelvis_front", "pelvis_side", "pelvis_three_quarter"):
    render(f"flat_material_{view_name}", view_name)

# One-color wireframes isolate geometric continuity from texture and skin color.
# A shader wireframe is used because object.show_wire is not included in
# background Workbench renders in current Blender versions.
wire_material = bpy.data.materials.new("V23_DIAGNOSTIC_SINGLE_COLOR_WIREFRAME")
wire_material.use_nodes = True
wire_nodes = wire_material.node_tree.nodes
wire_links = wire_material.node_tree.links
wire_nodes.clear()
wireframe = wire_nodes.new("ShaderNodeWireframe")
wireframe.use_pixel_size = True
wireframe.inputs["Size"].default_value = 0.65
wire_ramp = wire_nodes.new("ShaderNodeValToRGB")
wire_ramp.color_ramp.elements[0].position = 0.20
wire_ramp.color_ramp.elements[0].color = (0.58, 0.68, 0.80, 1.0)
wire_ramp.color_ramp.elements[1].position = 0.55
wire_ramp.color_ramp.elements[1].color = (0.018, 0.022, 0.028, 1.0)
wire_emission = wire_nodes.new("ShaderNodeEmission")
wire_output = wire_nodes.new("ShaderNodeOutputMaterial")
wire_links.new(wireframe.outputs["Fac"], wire_ramp.inputs["Factor"])
wire_links.new(wire_ramp.outputs["Color"], wire_emission.inputs["Color"])
wire_links.new(wire_emission.outputs["Emission"], wire_output.inputs["Surface"])
scene.render.engine = "BLENDER_EEVEE"
scene.view_layers[0].material_override = wire_material
for view_name in ("pelvis_front", "pelvis_side", "pelvis_three_quarter"):
    render(f"single_color_wireframe_{view_name}", view_name)
scene.view_layers[0].material_override = None

# Albedo-only uses the source albedo image or Principled base color through an
# emission shader.  This removes lighting/AO while retaining the real skin,
# nail, and hair color instead of Workbench's gray display color.
saved_materials = replace_materials_with_albedo()
scene.render.engine = "BLENDER_EEVEE"
for view_name in ("pelvis_front", "pelvis_side", "pelvis_three_quarter"):
    render(f"albedo_only_{view_name}", view_name)

# World-space normal direction, remapped from [-1, 1] to [0, 1].  A material
# override makes the pass independent of the candidate's shader graph.
normal_material = bpy.data.materials.new("V23_DIAGNOSTIC_WORLD_NORMAL")
normal_material.use_nodes = True
nodes = normal_material.node_tree.nodes
links = normal_material.node_tree.links
nodes.clear()
geometry = nodes.new("ShaderNodeNewGeometry")
multiply_add = nodes.new("ShaderNodeVectorMath")
multiply_add.operation = "MULTIPLY_ADD"
multiply_add.inputs[1].default_value = (0.5, 0.5, 0.5)
multiply_add.inputs[2].default_value = (0.5, 0.5, 0.5)
emission = nodes.new("ShaderNodeEmission")
output = nodes.new("ShaderNodeOutputMaterial")
links.new(geometry.outputs["Normal"], multiply_add.inputs[0])
links.new(multiply_add.outputs["Vector"], emission.inputs["Color"])
links.new(emission.outputs["Emission"], output.inputs["Surface"])
scene.render.engine = "BLENDER_EEVEE"
scene.view_layers[0].material_override = normal_material
for view_name in ("pelvis_front", "pelvis_side", "pelvis_three_quarter"):
    render(f"normal_direction_{view_name}", view_name)
scene.view_layers[0].material_override = None

# Binary silhouette/object-coverage evidence.  White is any rendered mesh and
# black is background.  Unlike a lit material pass this cannot confuse an
# underside normal, AO, or a cast shadow with a true hole through the surface.
silhouette_material = bpy.data.materials.new(
    "V23_DIAGNOSTIC_BINARY_SILHOUETTE"
)
silhouette_material.use_nodes = True
silhouette_nodes = silhouette_material.node_tree.nodes
silhouette_nodes.clear()
silhouette_emission = silhouette_nodes.new("ShaderNodeEmission")
silhouette_emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
silhouette_output = silhouette_nodes.new("ShaderNodeOutputMaterial")
silhouette_material.node_tree.links.new(
    silhouette_emission.outputs["Emission"],
    silhouette_output.inputs["Surface"],
)
saved_world_color = tuple(world.color)
world.color = (0.0, 0.0, 0.0)
scene.render.engine = "BLENDER_EEVEE"
scene.view_layers[0].material_override = silhouette_material
for view_name in ("pelvis_front", "pelvis_side", "pelvis_three_quarter"):
    render(f"silhouette_mask_{view_name}", view_name)
scene.view_layers[0].material_override = None
world.color = saved_world_color

# Hair/head-silhouette evidence.  Render the body and removable review hair
# together in albedo and neutral geometry, then add a wireframe view.
configure_workbench(light="STUDIO", color_type="MATERIAL")
for view_name in ("hair_front", "hair_left_profile", "hair_right_profile"):
    render(f"flat_material_{view_name}", view_name)
scene.render.engine = "BLENDER_EEVEE"
for view_name in ("hair_front", "hair_left_profile", "hair_right_profile"):
    render(f"albedo_only_{view_name}", view_name)
if hair_objects:
    scene.view_layers[0].material_override = wire_material
    for view_name in ("hair_left_profile", "hair_right_profile"):
        render(f"single_color_wireframe_{view_name}", view_name)
    scene.view_layers[0].material_override = None

# Hands are shown from the front and rear so finger proportions and nail plates
# cannot be hidden by a favorable view.
hand_views = (
    "hand_left_front",
    "hand_right_front",
    "hand_left_rear",
    "hand_right_rear",
)
configure_workbench(light="STUDIO", color_type="MATERIAL")
for view_name in hand_views:
    render(f"flat_material_{view_name}", view_name)
scene.render.engine = "BLENDER_EEVEE"
for view_name in hand_views:
    render(f"albedo_only_{view_name}", view_name)
scene.view_layers[0].material_override = wire_material
for view_name in hand_views:
    render(f"single_color_wireframe_{view_name}", view_name)
scene.view_layers[0].material_override = None
restore_materials(saved_materials)

manifest = {
    "schema": "kira.avatar.biological_robert.v23.diagnostic_render.v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "source_blend": str(SOURCE),
    "candidate_body_object": body.name,
    "hair_objects": [obj.name for obj in hair_objects],
    "body_vertex_count": len(body.data.vertices),
    "diagnostic_only": True,
    "candidate_modified_or_saved": False,
    "passes": {
        "pelvis": [
            "flat material",
            "single-color wireframe",
            "world-normal direction",
            "albedo-only",
            "binary silhouette/object coverage",
        ],
        "hair": ["flat material", "single-color wireframe"],
        "hands": ["flat material", "single-color wireframe"],
    },
    "rendered_files": rendered,
}
(OUTPUT / "DIAGNOSTIC_RENDER_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)
print(OUTPUT)
