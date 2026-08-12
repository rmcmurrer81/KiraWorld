"""Render fail-closed V20 local-transition diagnostics.

This script never alters the saved owner candidate.  It opens the candidate,
renders neutral material passes, and makes temporary bisected duplicates for
cross-section inspection.
"""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v20_local_pelvis_rebuild"
BLEND = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V20_LOCAL_PELVIS_REBUILD.blend"
DIAG = OUT / "diagnostics"
DIAG.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V20_LOCAL_PELVIS_REBUILD")
camera = scene.camera
if body is None:
    raise SystemExit("V20 body missing")
if camera is None:
    camera_data = bpy.data.cameras.new("V20DiagnosticCamera")
    camera = bpy.data.objects.new("V20DiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.display.shading.light = "STUDIO"
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.display.shading.show_specular_highlight = False
scene.display.shading.background_type = "THEME"
scene.render.image_settings.file_format = "PNG"

def aim(location, lens=62):
    camera.location = location
    direction = body.location + Vector((0, 0, .82)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens

def render(name):
    scene.render.filepath = str(DIAG / f"{name}.png")
    bpy.ops.render.render(write_still=True)

aim((0, -3.0, .90), 72)
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_xray = False
body.show_wire = False
render("flat_shaded_front")

body.show_wire = True
body.show_all_edges = True
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.58, 0.68, 0.80)
render("wireframe_front")
body.show_wire = False

scene.display.shading.color_type = "MATERIAL"
render("material_id_front")

# Albedo-only: flat lighting, material color, no AO/cavity/shadows/specular.
scene.display.shading.light = "FLAT"
render("albedo_only_front")
aim((2.45, -1.05, .90), 72)
render("albedo_only_side")

# RGB normal-direction pass: world-space XYZ normals remapped to 0..1.
normal_material = bpy.data.materials.new("V20_DIAGNOSTIC_NORMAL_DIRECTION")
normal_material.use_nodes = True
nodes = normal_material.node_tree.nodes
links = normal_material.node_tree.links
nodes.clear()
geometry = nodes.new("ShaderNodeNewGeometry")
vector_math = nodes.new("ShaderNodeVectorMath")
vector_math.operation = "MULTIPLY_ADD"
vector_math.inputs[1].default_value = (.5, .5, .5)
vector_math.inputs[2].default_value = (.5, .5, .5)
emission = nodes.new("ShaderNodeEmission")
output = nodes.new("ShaderNodeOutputMaterial")
links.new(geometry.outputs["Normal"], vector_math.inputs[0])
links.new(vector_math.outputs["Vector"], emission.inputs["Color"])
links.new(emission.outputs["Emission"], output.inputs["Surface"])
saved_materials = [slot.material for slot in body.material_slots]
for slot in body.material_slots:
    slot.material = normal_material
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
aim((0, -3.0, .90), 72)
render("normal_direction_front")
aim((2.45, -1.05, .90), 72)
render("normal_direction_side")
for slot, material in zip(body.material_slots, saved_materials):
    slot.material = material
scene.render.engine = "BLENDER_WORKBENCH"

# Temporary geometric cross-sections.  The retained half is deliberately
# colored blue and the newly exposed cut is visible against a light ground.
def cross_section(name, cutter_location, cutter_scale, view_location):
    duplicate = body.copy()
    duplicate.data = body.data.copy()
    bpy.context.collection.objects.link(duplicate)
    body.hide_render = True
    bpy.ops.mesh.primitive_cube_add(location=cutter_location, scale=cutter_scale)
    cutter = bpy.context.object
    mod = duplicate.modifiers.new("diagnostic_bisect", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = duplicate
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    duplicate.color = (0.22, 0.52, 0.88, 1)
    scene.display.shading.color_type = "OBJECT"
    aim(view_location, 72)
    render(name)
    bpy.data.objects.remove(duplicate, do_unlink=True)
    body.hide_render = False

cross_section("front_cross_section", (0, -0.30, .78), (.70, .30, .55), (0, -3.0, .90))
cross_section("side_cross_section", (-0.40, 0, .78), (.40, .70, .55), (2.45, -1.05, .90))

print(DIAG)
