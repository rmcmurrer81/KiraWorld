from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector


output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
obj = bpy.data.objects.get("Kira_R7_Bounded_Neck_Torso_R4V6_Inactive")
if obj is None or obj.type != "MESH":
    raise RuntimeError("R4-v6 review mesh missing")
obj.show_wire = True
obj.show_all_edges = True
scene = bpy.context.scene
scene.render.filepath = str(output)
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
camera = bpy.data.objects.get("R4V6OwnerReviewCamera")
if camera is None:
    raise RuntimeError("R4-v6 review camera missing")
scene.camera = camera
neck_center = Vector((-0.00003, 0.0272, 0.9921))
camera.data.type = "ORTHO"
camera.data.ortho_scale = 0.26
camera.location = Vector((neck_center.x, neck_center.y - 3.0, neck_center.z))
camera.rotation_euler = (neck_center - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.render.render(write_still=True)
print(f"WIRE_DIAGNOSTIC={output}")
