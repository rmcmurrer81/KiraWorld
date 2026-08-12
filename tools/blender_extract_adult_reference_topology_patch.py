"""Extract only the authorized reference's local adult topology for fitting tests.

This deliberately excludes the source person's body, face, proportions, skin,
and identity. The output is construction evidence and not an owner deliverable.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_nude_2_1_f117148577.glb"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/anatomy_reference_audit/local_topology_patch"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
source = bpy.data.objects.get("Object003_Object003_mtl_0")
if source is None:
    raise SystemExit("authorized high-resolution body reference mesh missing")

world_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
selected_faces = []
selected_indices = set()
for polygon in source.data.polygons:
    points = [world_points[index] for index in polygon.vertices]
    # Require every corner to remain inside the local crop. Using only a face
    # center admitted long boundary triangles from adjacent body regions.
    if all(
        0.4 <= point.x <= 3.8
        and 26.8 <= point.z <= 33.2
        and 4.8 <= point.y <= 6.3
        for point in points
    ):
        selected_faces.append(tuple(polygon.vertices))
        selected_indices.update(polygon.vertices)

index_map = {old: new for new, old in enumerate(sorted(selected_indices))}
vertices = [world_points[index] for index in sorted(selected_indices)]
faces = [tuple(index_map[index] for index in face) for face in selected_faces]
mesh = bpy.data.meshes.new("Authorized_Local_Adult_Topology_Patch")
mesh.from_pydata(vertices, [], faces)
mesh.update()
patch = bpy.data.objects.new("Authorized_Local_Adult_Topology_Patch", mesh)
bpy.context.collection.objects.link(patch)

for obj in list(bpy.context.scene.objects):
    if obj != patch:
        bpy.data.objects.remove(obj, do_unlink=True)

material = bpy.data.materials.new("TopologyInspection")
material.diffuse_color = (0.54, 0.28, 0.18, 1.0)
patch.data.materials.append(material)
for polygon in patch.data.polygons:
    polygon.use_smooth = True

xs = [vertex.co.x for vertex in patch.data.vertices]
ys = [vertex.co.y for vertex in patch.data.vertices]
zs = [vertex.co.z for vertex in patch.data.vertices]
center = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
extent = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))

light_data = bpy.data.lights.new("Area", "AREA")
light_data.energy = 700
light_data.shape = "DISK"
light_data.size = extent * 2
light = bpy.data.objects.new("Area", light_data)
bpy.context.collection.objects.link(light)
light.location = center + Vector((extent, extent, extent))
light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = extent * 1.35

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
if scene.world is None:
    scene.world = bpy.data.worlds.new("InspectionWorld")
scene.world.color = (0.08, 0.08, 0.08)
for label, location in (
    ("front", center + Vector((0, extent * 2, 0))),
    ("rear", center + Vector((0, -extent * 2, 0))),
    ("left", center + Vector((-extent * 2, 0, 0))),
    ("right", center + Vector((extent * 2, 0, 0))),
):
    camera.location = location
    camera.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{label}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "AUTHORIZED_LOCAL_TOPOLOGY_PATCH.blend"))
print({
    "vertices": len(vertices),
    "faces": len(faces),
    "bounds": [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]],
})
