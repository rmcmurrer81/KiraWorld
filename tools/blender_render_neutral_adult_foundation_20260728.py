from pathlib import Path
import bpy, math, os
from mathutils import Vector
ROOT=Path(r"C:\Users\robmc\Kira")
proof=ROOT/"Avatar/avatar_builder/proofs/neutral_adult_foundation_20260728"
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
source=Path(os.environ.get("AVATAR_RENDER_GLB",str(proof/"neutral_adult_foundation.glb")))
bpy.ops.import_scene.gltf(filepath=str(source))
for armature in [o for o in bpy.context.scene.objects if o.type=="ARMATURE"]:
 if armature.animation_data:armature.animation_data_clear()
 armature.data.pose_position="REST"
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
mins=Vector((1e9,1e9,1e9));maxs=Vector((-1e9,-1e9,-1e9))
for o in meshes:
 for c in o.bound_box:
  p=o.matrix_world@Vector(c)
  mins.x=min(mins.x,p.x);mins.y=min(mins.y,p.y);mins.z=min(mins.z,p.z)
  maxs.x=max(maxs.x,p.x);maxs.y=max(maxs.y,p.y);maxs.z=max(maxs.z,p.z)
center=(mins+maxs)*.5;height=maxs.z-mins.z
world=bpy.data.worlds.new("ReviewWorld");bpy.context.scene.world=world
world.color=(.025,.035,.055)
bpy.ops.object.light_add(type="AREA",location=(2,-3,3));bpy.context.object.data.energy=900;bpy.context.object.data.shape="DISK";bpy.context.object.data.size=3
bpy.ops.object.light_add(type="AREA",location=(-2,-1,2));bpy.context.object.data.energy=500;bpy.context.object.data.size=2
bpy.ops.mesh.primitive_plane_add(size=8,location=(center.x,center.y,mins.z-.01))
floor=bpy.context.object;floor.name="ReviewFloor"
mat=bpy.data.materials.new("Floor");mat.diffuse_color=(.04,.06,.09,1);floor.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine="BLENDER_EEVEE";scene.render.resolution_x=700;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG";scene.render.film_transparent=False
def point(camera,target):
 camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
for name,angle in (("front",0),("three_quarter",35),("side",90),("back",180)):
 rad=math.radians(angle);distance=height*1.55
 bpy.ops.object.camera_add(location=(center.x+math.sin(rad)*distance,center.y-math.cos(rad)*distance,center.z+height*.03))
 cam=bpy.context.object;point(cam,center);scene.camera=cam;scene.render.filepath=str(proof/"renders"/f"neutral_adult_{name}.png")
 Path(scene.render.filepath).parent.mkdir(parents=True,exist_ok=True);bpy.ops.render.render(write_still=True)
 bpy.data.objects.remove(cam,do_unlink=True)
