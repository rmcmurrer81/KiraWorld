"""Render V15/V21 preservation comparisons and V21 diagnostic evidence."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
V15 = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
V21_DIR = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v21_bounded_local_repair"
V21 = V21_DIR / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V21_BOUNDED_LOCAL_REPAIR.blend"
OUT = V21_DIR / "diagnostics"
OUT.mkdir(parents=True, exist_ok=True)

views = {
    "hands_front": ((0, -2.0, 1.08), (0, 0, 1.08), 86),
    "hands_rear": ((0, 2.0, 1.08), (0, 0, 1.08), 86),
    "upper_thighs_front": ((0, -1.65, .68), (0, 0, .68), 78),
    "upper_thighs_rear": ((0, 1.65, .68), (0, 0, .68), 78),
    "upper_thighs_side": ((1.45, -.45, .68), (0, 0, .68), 78),
}

def setup(source):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    body = max((o for o in scene.objects if o.type == "MESH" and o.name.startswith("BIOLOGICAL_ROBERT")), key=lambda o: len(o.data.vertices))
    for obj in list(scene.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)
    camera_data = bpy.data.cameras.new("EvidenceCamera")
    camera = bpy.data.objects.new("EvidenceCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    return scene, body, camera

def aim(camera, position, target, lens):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens

for label, source in (("v15", V15), ("v21", V21)):
    scene, body, camera = setup(source)
    for name, (position, target, lens) in views.items():
        aim(camera, position, target, lens)
        scene.render.filepath = str(OUT / f"{label}_{name}.png")
        bpy.ops.render.render(write_still=True)

# V21 local diagnostic passes.
scene, body, camera = setup(V21)
aim(camera, (0, -1.45, .73), (0, 0, .73), 78)
body.show_wire = True
body.show_all_edges = True
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (.58, .70, .88)
scene.render.filepath = str(OUT / "v21_local_wireframe.png")
bpy.ops.render.render(write_still=True)
body.show_wire = False
scene.render.filepath = str(OUT / "v21_local_flat_shaded.png")
bpy.ops.render.render(write_still=True)

scene.display.shading.color_type = "MATERIAL"
scene.display.shading.light = "FLAT"
scene.render.filepath = str(OUT / "v21_albedo_only.png")
bpy.ops.render.render(write_still=True)
scene.display.shading.color_type = "MATERIAL"
scene.render.filepath = str(OUT / "v21_material_id.png")
bpy.ops.render.render(write_still=True)

# The inherited skin uses one roughness setting across the local surface. This
# grayscale diagnostic is deliberately flat: any apparent variation in the
# neutral render therefore comes from geometry/lighting or the inherited maps.
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (.48, .48, .48)
scene.render.filepath = str(OUT / "v21_roughness_only.png")
bpy.ops.render.render(write_still=True)

# Vertex-delta map: red = authorized local changes; blue = byte-for-byte
# coordinate preservation relative to V15.
bpy.ops.wm.open_mainfile(filepath=str(V15))
source_body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
source_coords = [v.co.copy() for v in source_body.data.vertices]
scene, body, camera = setup(V21)
colors = body.data.color_attributes.get("V21_GEOMETRY_DELTA")
if colors is None:
    colors = body.data.color_attributes.new(name="V21_GEOMETRY_DELTA", type="BYTE_COLOR", domain="POINT")
for datum, vertex, before in zip(colors.data, body.data.vertices, source_coords):
    changed = (vertex.co - before).length > 1e-9
    datum.color = (1.0, .02, .02, 1.0) if changed else (.02, .12, 1.0, 1.0)
scene.display.shading.color_type = "VERTEX"
scene.display.shading.light = "FLAT"
aim(camera, (0, -3.1, 1.0), (0, 0, .98), 62)
scene.render.filepath = str(OUT / "v15_v21_geometry_delta.png")
bpy.ops.render.render(write_still=True)
print(OUT)
