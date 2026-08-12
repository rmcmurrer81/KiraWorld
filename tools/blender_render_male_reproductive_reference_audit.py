"""Render the authorized male reproductive reference for local-structure audit."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_reproductive_system_f5c19ef767.glb"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/anatomy_reference_audit/male_reproductive_system"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes = [
    min(
        (o for o in bpy.context.scene.objects if o.type == "MESH" and len(o.data.vertices) > 10),
        key=lambda obj: len(obj.data.vertices),
    )
]
for obj in meshes:
    mat = bpy.data.materials.new("Audit")
    mat.diffuse_color = (0.62, 0.31, 0.22, 1)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
center = sum(points, Vector()) / len(points)
extent = max(max(p[i] for p in points) - min(p[i] for p in points) for i in range(3))
ld = bpy.data.lights.new("Area", "AREA")
ld.energy, ld.shape, ld.size = 1200, "DISK", extent * 2
light = bpy.data.objects.new("Area", ld)
bpy.context.collection.objects.link(light)
light.location = center + Vector((extent, -extent, extent))
light.rotation_euler = (center-light.location).to_track_quat("-Z", "Y").to_euler()
cd = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", cd)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = extent * 1.2
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("AuditWorld")
scene.world.color = (0.04, 0.04, 0.04)
for label, offset in {
    "front": (0, -2, 0),
    "rear": (0, 2, 0),
    "left": (-2, 0, 0),
    "right": (2, 0, 0),
}.items():
    camera.location = center + Vector(offset) * extent
    camera.rotation_euler = (center-camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{label}.png")
    bpy.ops.render.render(write_still=True)
