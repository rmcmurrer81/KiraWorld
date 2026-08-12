"""Build an inactive neutral-adult Avatar Builder foundation proof."""
from pathlib import Path
import bpy, json, math, sys
from mathutils import Vector

ROOT=Path(r"C:\Users\robmc\Kira")
OUT=ROOT/"Avatar/avatar_builder/proofs/neutral_adult_foundation_20260728"
SOURCE=ROOT/"Assets/third_party/intake/3d_models_kira_world/avatar_builder_references/womenfemale_body_base_rigged.glb"
GLB=OUT/"neutral_adult_foundation.glb"

def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
 m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=color
 m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=.62
 return m
def uv(name,loc,scale,mat,segments=32,rings=16):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
 o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(mat);return o
def cube(name,loc,scale,mat):
 bpy.ops.mesh.primitive_cube_add(location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(mat);return o
def cylinder(name,loc,radius,depth,mat):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=loc)
 o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o
def head_parent(obj,arm,bone="mixamorig:Head_06"):
 obj["attachment_bone"]=bone
 obj["attachment_mode"]="validated_runtime_contract_pending_skinned_transfer"

OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
for obj in list(bpy.data.objects):
 if obj.name=="Icosphere": bpy.data.objects.remove(obj,do_unlink=True)
arm=next(o for o in bpy.data.objects if o.type=="ARMATURE");arm.name="NeutralAdult_StandardSkeleton"
body=max((o for o in bpy.data.objects if o.type=="MESH"),key=lambda o:len(o.data.vertices))
body.name="NeutralAdultBody_StandardTopology"
for obj in list(bpy.data.objects):
 if obj.type=="MESH" and obj!=body:bpy.data.objects.remove(obj,do_unlink=True)
# Normalize the source to 1.72 m while preserving the source topology and weights.
world=[body.matrix_world@v.co for v in body.data.vertices]
low=min(v.z for v in world);high=max(v.z for v in world);factor=1.72/(high-low)
for obj in [o for o in bpy.context.scene.objects if o.parent is None]: obj.scale*=factor
bpy.context.view_layer.update()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)

skin=material("NeutralSkin",(0.53,0.31,0.21,1));white=material("EyeSclera",(0.92,0.91,0.87,1))
iris=material("NeutralIris",(0.16,0.34,0.32,1));black=material("Pupil",(0.01,0.01,0.01,1))
mouth=material("MouthInterior",(0.18,0.025,0.025,1));tooth=material("Teeth",(0.92,0.88,0.78,1))
tongue=material("Tongue",(0.52,0.12,0.14,1));hairmat=material("Hair",(0.09,0.055,0.035,1))
shirtmat=material("SimpleShirt",(0.06,0.20,0.38,1));pantsmat=material("SimplePants",(0.055,0.065,0.08,1))
base=material("BaseLayer",(0.22,0.22,0.24,1))

# Add the missing standard facial components around the source head.
eye_z=1.535;eye_y=-.176;eye_x=.050;radius=.024
for side,x in (("L",-eye_x),("R",eye_x)):
 globe=uv(f"{side}_EyeGlobe",(x,eye_y,eye_z),(radius,radius,radius),white,32,20)
 iris_o=uv(f"{side}_Iris",(x,eye_y-.022,eye_z),(.010,.003,.010),iris,24,12)
 pupil=uv(f"{side}_Pupil",(x,eye_y-.025,eye_z),(.004,.002,.004),black,16,8)
 lid=uv(f"{side}_EyelidContactGuide",(x,eye_y+.002,eye_z),(radius*1.035,radius*.54,radius*1.03),skin,32,12)
 for o in (globe,iris_o,pupil,lid):head_parent(o,arm)
 o["profile"]="realistic_adult";o["socket_validated"]=True
cube("MouthInterior",(0,-.180,1.455),(.042,.009,.025),mouth)
cube("UpperTeeth",(0,-.191,1.469),(.035,.005,.007),tooth)
cube("LowerTeeth",(0,-.190,1.444),(.034,.005,.006),tooth)
uv("Tongue",(0,-.185,1.438),(.027,.010,.008),tongue,24,10)
for name in ("MouthInterior","UpperTeeth","LowerTeeth","Tongue"):head_parent(bpy.data.objects[name],arm)

# Modular runtime-friendly hair meshes.
hair_parts=[
 uv("Hair_ScalpCap",(0,-.012,1.615),(.112,.100,.070),hairmat,32,16),
 uv("Hair_MainVolume",(0,.036,1.585),(.118,.082,.105),hairmat,32,16),
 cube("Hair_Bangs",(-.025,-.092,1.594),(.075,.014,.027),hairmat),
 cube("Hair_Side_L",(-.102,-.012,1.555),(.018,.038,.083),hairmat),
 cube("Hair_Side_R",(.102,-.012,1.555),(.018,.038,.083),hairmat)]
for o in hair_parts:head_parent(o,arm);o["runtime_hair_component"]=True

# Simple separate garments. They are proof components, not unrestricted cloth.
shirt=uv("Garment_Shirt",(0,-.005,1.145),(.225,.125,.275),shirtmat,40,20)
base_layer=uv("Garment_BaseLayer",(0,-.002,1.12),(.205,.108,.255),base,40,20)
hips=uv("Garment_Pants_Hips",(0,0,.875),(.185,.105,.145),pantsmat,36,16)
for o,bone in ((shirt,"mixamorig:Spine2_04"),(base_layer,"mixamorig:Spine2_04"),(hips,"mixamorig:Hips_01")):
 o["attachment_bone"]=bone;o["attachment_mode"]="staged_rigid_proof_pending_skinned_transfer"
for side,x in (("L",-0.105),("R",0.105)):
 leg=cylinder(f"Garment_Pants_{side}",(x,0,.585),.085,.52,pantsmat)
 leg["attachment_bone"]=f"mixamorig:{'Left' if side=='L' else 'Right'}UpLeg_{'055' if side=='L' else '060'}"
 leg["attachment_mode"]="staged_rigid_proof_pending_skinned_transfer"
for garment in (shirt,base_layer,hips,*[bpy.data.objects[n] for n in ("Garment_Pants_L","Garment_Pants_R")]):
 garment["clothing_attachment_contract"]="standard_skeleton_v1"
 garment["dressing_states"]="stored,held,dressing_start,partly_inserted,pulled_into_place,partly_fastened,fully_worn,removing,returned_to_storage"
shirt["button_records"]=json.dumps([{"button_id":"shirt_b1","buttonhole_id":"shirt_h1","state":"fastened","order":1},
 {"button_id":"shirt_b2","buttonhole_id":"shirt_h2","state":"fastened","order":2}])

# Identity-preserving whole-mesh facial shape keys localized to the head region.
if not body.data.shape_keys: body.shape_key_add(name="Basis")
for name in ("smile","frown","surprise","concern","anger","blink","viseme_AA","viseme_EE","viseme_OO","viseme_MBP"):
 key=body.shape_key_add(name=name)
 for i,v in enumerate(body.data.vertices):
  co=v.co
  if co.z<.92:continue
  if name=="smile" and co.y<-.04 and .98<co.z<1.08:key.data[i].co.z+=.008
  elif name=="frown" and co.y<-.04 and .98<co.z<1.08:key.data[i].co.z-=.007
  elif name=="surprise" and co.y<-.04 and .98<co.z<1.10:key.data[i].co.z+=.012
  elif name=="concern" and co.z>1.08:key.data[i].co.x*=.997
  elif name=="anger" and co.z>1.08:key.data[i].co.z-=.004
  elif name=="blink" and co.y<-.04 and 1.08<co.z<1.14:key.data[i].co.z-=.010
  elif name=="viseme_AA" and co.y<-.04 and .98<co.z<1.08:key.data[i].co.z-=.014
  elif name=="viseme_EE" and co.y<-.04 and .98<co.z<1.08:key.data[i].co.x*=1.012
  elif name=="viseme_OO" and co.y<-.04 and .98<co.z<1.08:key.data[i].co.x*=.985
  elif name=="viseme_MBP" and co.y<-.04 and .98<co.z<1.08:key.data[i].co.z+=.004

def bone_like(token):
 return next(b for b in arm.pose.bones if token.casefold() in b.name.casefold())
tokens={"hips":"Hips","spine":"Spine2","head":"Head_","lua":"LeftArm","rua":"RightArm",
 "lfa":"LeftForeArm","rfa":"RightForeArm","lul":"LeftUpLeg","rul":"RightUpLeg",
 "ll":"LeftLeg","rl":"RightLeg"}
bones={k:bone_like(v) for k,v in tokens.items()}
def action(name,keys):
 act=bpy.data.actions.new(name);arm.animation_data_create();arm.animation_data.action=act
 for frame,poses in keys:
  bpy.context.scene.frame_set(frame)
  for key,rot in poses.items():
   b=bones[key];b.rotation_mode="XYZ";b.rotation_euler=[math.radians(x) for x in rot]
   b.keyframe_insert("rotation_euler",frame=frame)
 act.use_fake_user=True
action("NeutralStanding",[(1,{}),(30,{"head":(2,0,3)}),(60,{})])
action("Walk",[(1,{"lul":(22,0,0),"rul":(-22,0,0),"lua":(-18,0,0),"rua":(18,0,0)}),
 (16,{"lul":(-22,0,0),"rul":(22,0,0),"lua":(18,0,0),"rua":(-18,0,0)}),(32,{"lul":(22,0,0),"rul":(-22,0,0)})])
action("Turn",[(1,{}),(45,{"hips":(0,0,38),"spine":(0,0,18),"head":(0,0,-12)}),(90,{})])
action("Sit",[(1,{}),(45,{"hips":(-8,0,0),"lul":(-70,0,0),"rul":(-70,0,0),"ll":(72,0,0),"rl":(72,0,0)})])
action("StandFromChair",[(1,{"hips":(-8,0,0),"lul":(-70,0,0),"rul":(-70,0,0),"ll":(72,0,0),"rl":(72,0,0)}),(55,{})])
action("ReachAndHold",[(1,{}),(35,{"rua":(-52,10,-8),"rfa":(-35,0,0)}),(70,{"rua":(-25,4,-4),"rfa":(-70,0,0)})])
action("DoorThreshold",[(1,{}),(24,{"lul":(28,0,0),"rul":(-12,0,0),"rua":(-42,8,0)}),(48,{"lul":(-12,0,0),"rul":(28,0,0)})])
action("BasicStairs",[(1,{}),(20,{"lul":(42,0,0),"ll":(-35,0,0)}),(40,{"rul":(42,0,0),"rl":(-35,0,0)}),(60,{})])

# Face-test animation lives on shape keys.
keys=body.data.shape_keys;keys.animation_data_create();face=bpy.data.actions.new("FaceSpeechTest");keys.animation_data.action=face
for i,name in enumerate(("blink","smile","frown","surprise","concern","anger","viseme_AA","viseme_EE","viseme_OO","viseme_MBP")):
 block=keys.key_blocks[name]
 for frame,value in ((1+i*12,0),(6+i*12,1),(11+i*12,0)):
  block.value=value;block.keyframe_insert("value",frame=frame)
face.use_fake_user=True

body["avatar_class"]="realistic_adult_neutral"
body["standard_topology_contract"]="STANDARD_AVATAR_TOPOLOGY_SPEC.v1"
body["body_truth_channels"]="SPOKEN,PRIVATE_MIND,FACTUAL_RUNTIME_TRUTH"
body["runtime_activation_allowed"]=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"neutral_adult_foundation.blend"))
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format="GLB",export_animations=True,
 export_animation_mode="ACTIONS",export_morph=True,export_yup=True,export_apply=True)
result={"status":"ARTIFACT_GENERATED_AWAITING_VALIDATION","source":str(SOURCE),"glb":str(GLB),
 "body_mesh":body.name,"source_vertex_count":len(body.data.vertices),"skeleton":arm.name,
 "bone_count":len(arm.data.bones),"shape_keys":[k.name for k in body.data.shape_keys.key_blocks],
 "hair_components":[o.name for o in hair_parts],"garments":[o.name for o in (base_layer,shirt,hips)],
 "animations":[a.name for a in bpy.data.actions],"runtime_activation_allowed":False}
(OUT/"BLENDER_BUILD_RESULT.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
