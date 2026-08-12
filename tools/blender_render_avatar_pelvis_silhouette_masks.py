"""Render fast binary pelvis-coverage masks for a static avatar candidate.

Usage:
    blender --background --python \
      tools/blender_render_avatar_pelvis_silhouette_masks.py -- \
      CANDIDATE.blend OUTPUT_DIRECTORY

The opened candidate is never saved.  White pixels are rendered mesh coverage;
black pixels are background.  The masks are intended for
``validate_avatar_pelvis_silhouette_masks.py`` and prevent dark shading from
being mistaken for a geometric tunnel.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


if "--" not in sys.argv:
    raise SystemExit(__doc__)
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) != 2:
    raise SystemExit(__doc__)
source = Path(arguments[0]).resolve(strict=True)
output = Path(arguments[1]).resolve()
output.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(source))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise SystemExit("candidate contains no mesh")
body = max(meshes, key=lambda obj: len(obj.data.vertices))
body_min = min((body.matrix_world @ Vector(corner)).z for corner in body.bound_box)
body_max = max((body.matrix_world @ Vector(corner)).z for corner in body.bound_box)
body_height = body_max - body_min
pelvis_z = body_min + body_height * 0.402

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

world = scene.world or bpy.data.worlds.new("AvatarSilhouetteWorld")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (
    0.0,
    0.0,
    0.0,
    1.0,
)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0

mask = bpy.data.materials.new("AvatarBinarySilhouette")
mask.use_nodes = True
nodes = mask.node_tree.nodes
nodes.clear()
emission = nodes.new("ShaderNodeEmission")
emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
emission.inputs["Strength"].default_value = 1.0
material_output = nodes.new("ShaderNodeOutputMaterial")
mask.node_tree.links.new(emission.outputs["Emission"], material_output.inputs["Surface"])
scene.view_layers[0].material_override = mask

camera_data = bpy.data.cameras.new("AvatarSilhouetteCamera")
camera = bpy.data.objects.new("AvatarSilhouetteCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
unit = body_height
views = {
    "front": (
        (0.0, -0.69 * unit, pelvis_z + 0.01 * unit),
        (0.0, -0.015 * unit, pelvis_z),
        72,
    ),
    "side": (
        (0.56 * unit, -0.34 * unit, pelvis_z + 0.01 * unit),
        (0.0, -0.045 * unit, pelvis_z),
        72,
    ),
    "three_quarter": (
        (0.47 * unit, -0.52 * unit, pelvis_z + 0.02 * unit),
        (0.0, -0.02 * unit, pelvis_z),
        72,
    ),
}

rendered = {}
for name, (location, target, lens) in views.items():
    camera.location = location
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    destination = output / f"silhouette_mask_pelvis_{name}.png"
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    rendered[name] = {
        "path": str(destination),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    }

manifest = {
    "schema": "kira.avatar.pelvis_silhouette_render.v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "source": str(source),
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "candidate_body": body.name,
    "candidate_modified_or_saved": False,
    "rendered": rendered,
}
(output / "SILHOUETTE_RENDER_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)
print(output)

