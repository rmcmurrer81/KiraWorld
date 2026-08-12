"""Promote the best existing rigged adult reference into an inactive neutral proof."""
from pathlib import Path
import bpy, json, math
ROOT=Path(r"C:\Users\robmc\Kira")
OUT=ROOT/"Avatar/avatar_builder/proofs/neutral_adult_foundation_20260728"
SOURCE=ROOT/"Assets/third_party/intake/3d_models_kira_world/avatar_builder_references/base_female_game_ready_rigged_low_poly_light.glb"
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
arm=next(o for o in bpy.data.objects if o.type=="ARMATURE");arm.name="NeutralAdult_StandardSkeleton"
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
body=max(meshes,key=lambda o:len(o.data.vertices));body.name="NeutralAdultBody_StandardTopology"
name_map={}
for obj in meshes:
 n=obj.name.casefold()
 if obj==body:name_map["body"]=obj
 elif "clothes" in n:name_map["clothing"]=obj
 elif "eyes" in n:name_map["eyes"]=obj
 elif "hair_extra" in n:name_map["hair_extra"]=obj
 elif "hair" in n:name_map["hair"]=obj
 elif "mouth" in n:name_map["mouth"]=obj
for key,obj in name_map.items():obj.name=f"NeutralAdult_{key.title()}"

# Add localized expression/viseme keys to the standard body topology.
if not body.data.shape_keys:body.shape_key_add(name="Basis")
for name in ("smile","frown","surprise","concern","anger","blink","viseme_AA","viseme_EE","viseme_OO","viseme_MBP"):
 key=body.shape_key_add(name=name)
 for i,v in enumerate(body.data.vertices):
  co=v.co
  if co.z<1.48:continue
  if name=="smile" and co.y<-.035 and 1.52<co.z<1.62:key.data[i].co.z+=.006
  elif name=="frown" and co.y<-.035 and 1.52<co.z<1.62:key.data[i].co.z-=.006
  elif name=="surprise" and co.y<-.035 and 1.52<co.z<1.63:key.data[i].co.z+=.010
  elif name=="concern" and co.z>1.63:key.data[i].co.x*=.995
  elif name=="anger" and co.z>1.63:key.data[i].co.z-=.003
  elif name=="blink" and co.y<-.04 and 1.62<co.z<1.69:key.data[i].co.z-=.007
  elif name=="viseme_AA" and co.y<-.04 and 1.52<co.z<1.62:key.data[i].co.z-=.010
  elif name=="viseme_EE" and co.y<-.04 and 1.52<co.z<1.62:key.data[i].co.x*=1.008
  elif name=="viseme_OO" and co.y<-.04 and 1.52<co.z<1.62:key.data[i].co.x*=.992
  elif name=="viseme_MBP" and co.y<-.04 and 1.52<co.z<1.62:key.data[i].co.z+=.003

def find(*tokens):
 return next(b for b in arm.pose.bones if all(t.casefold() in b.name.casefold() for t in tokens))
bones={"hips":find("Hips"),"spine":find("Spine2"),"head":find("Head"),
 "lua":find("Arm.L"),"rua":find("Arm.R"),"lfa":find("ForeArm.L"),"rfa":find("ForeArm.R"),
 "lul":find("UpLeg.L"),"rul":find("UpLeg.R"),"ll":find("Leg.L"),"rl":find("Leg.R")}
def action(name,keys):
 a=bpy.data.actions.new(name);arm.animation_data_create();arm.animation_data.action=a
 for frame,poses in keys:
  bpy.context.scene.frame_set(frame)
  for b in arm.pose.bones:
   b.rotation_mode="XYZ";b.rotation_euler=(0.0,0.0,0.0);b.location=(0.0,0.0,0.0);b.scale=(1.0,1.0,1.0)
  for k,rot in poses.items():
   b=bones[k];b.rotation_mode="XYZ";b.rotation_euler=[math.radians(x) for x in rot]
   b.keyframe_insert("rotation_euler",frame=frame)
 a.use_fake_user=True
action("NeutralStanding",[(1,{}),(30,{"head":(2,0,3)}),(60,{})])
action("Walk",[(1,{"lul":(22,0,0),"rul":(-22,0,0),"lua":(-18,0,0),"rua":(18,0,0)}),
 (16,{"lul":(-22,0,0),"rul":(22,0,0),"lua":(18,0,0),"rua":(-18,0,0)}),(32,{})])
action("Turn",[(1,{}),(45,{"hips":(0,0,35),"spine":(0,0,16),"head":(0,0,-10)}),(90,{})])
action("Sit",[(1,{}),(45,{"hips":(-8,0,0),"lul":(-68,0,0),"rul":(-68,0,0),"ll":(70,0,0),"rl":(70,0,0)})])
action("StandFromChair",[(1,{"hips":(-8,0,0),"lul":(-68,0,0),"rul":(-68,0,0),"ll":(70,0,0),"rl":(70,0,0)}),(55,{})])
action("ReachAndHold",[(1,{}),(35,{"rua":(-50,10,-8),"rfa":(-34,0,0)}),(70,{"rua":(-25,4,-4),"rfa":(-68,0,0)})])
action("DoorThreshold",[(1,{}),(24,{"lul":(28,0,0),"rul":(-12,0,0),"rua":(-42,8,0)}),(48,{"lul":(-12,0,0),"rul":(28,0,0)})])
action("BasicStairs",[(1,{}),(20,{"lul":(42,0,0),"ll":(-35,0,0)}),(40,{"rul":(42,0,0),"rl":(-35,0,0)}),(60,{})])
keys=body.data.shape_keys;keys.animation_data_create();face=bpy.data.actions.new("FaceSpeechTest");keys.animation_data.action=face
for i,name in enumerate(("blink","smile","frown","surprise","concern","anger","viseme_AA","viseme_EE","viseme_OO","viseme_MBP")):
 block=keys.key_blocks[name]
 for f,v in ((1+i*12,0),(6+i*12,1),(11+i*12,0)):block.value=v;block.keyframe_insert("value",frame=f)
face.use_fake_user=True

for obj in meshes:
 obj["avatar_class"]="realistic_adult_neutral";obj["runtime_activation_allowed"]=False
body["standard_topology_contract"]="STANDARD_AVATAR_TOPOLOGY_SPEC.v1"
body["body_truth_channels"]="SPOKEN,PRIVATE_MIND,FACTUAL_RUNTIME_TRUTH"
if "clothing" in name_map:
 name_map["clothing"]["garment_states"]="stored,held,dressing-start,partly-inserted,pulled-into-place,partly-fastened,fully-worn,removing,returned-to-storage"
 name_map["clothing"]["button_state_contract"]="button_id,buttonhole_id,fastened_state,permitted_order,morph_or_bone_response"

# Export the asset from its bind/rest pose.  Creating the action library above
# leaves the armature on the final sampled action frame unless it is explicitly
# reset; exporting that evaluated pose corrupts the apparent neutral body.
arm.animation_data.action=None
arm.data.pose_position="REST"
for pose_bone in arm.pose.bones:
 pose_bone.rotation_mode="QUATERNION"
 pose_bone.rotation_quaternion=(1.0,0.0,0.0,0.0)
 pose_bone.location=(0.0,0.0,0.0)
 pose_bone.scale=(1.0,1.0,1.0)
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"neutral_adult_foundation.blend"))
glb=OUT/"neutral_adult_foundation.glb"
bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",export_animations=False,
 export_animation_mode="ACTIONS",export_morph=True,export_yup=True,export_apply=False,
 export_reset_pose_bones=True,export_rest_position_armature=True)
result={"status":"ARTIFACT_GENERATED_AWAITING_RUNTIME_VALIDATION","source":str(SOURCE),
 "glb":str(glb),"source_body_vertices":len(body.data.vertices),"skeleton_bones":len(arm.data.bones),
 "meshes":{k:v.name for k,v in name_map.items()},"shape_keys":[k.name for k in body.data.shape_keys.key_blocks],
 "animations":[a.name for a in bpy.data.actions],"height_m":1.78235,
 "runtime_activation_allowed":False,"Kira_body_replaced":False}
(OUT/"BLENDER_BUILD_RESULT.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
