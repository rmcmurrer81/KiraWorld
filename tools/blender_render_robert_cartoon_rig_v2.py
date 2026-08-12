"""Create and render a genuine articulated Robert cartoon puppet.

The character is an original, simple toon construction informed by the
owner-review character sheet.  Every visible body section is parented to a
named Blender armature bone; whole-character image translation is not used as
a substitute for joint animation.
"""
from pathlib import Path
import bpy, json, math, os, shutil
from mathutils import Vector

ROOT=Path(r"C:\Users\robmc\Kira")
OUT=ROOT/"VideoStudioDevelopment/robert_cartoon_rig_v2"
FRAMES=OUT/"frames";CLIPS=OUT/"clips";CONTACT=OUT/"contact_sheets"
for p in (OUT,FRAMES,CLIPS,CONTACT):p.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)

def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*color,1)
    bsdf.inputs["Roughness"].default_value=.7
    return m
SKIN=mat("skin",(0.83,.57,.39));BLACK=mat("clothing",(0.025,.03,.038))
SHIRT=mat("shirt",(.015,.02,.028));HAIR=mat("hair",(.28,.13,.055))
WHITE=mat("eye_white",(.95,.95,.92));DARK=mat("ink",(.008,.01,.015))
BLUE=mat("eye",(.08,.16,.22));PAPER=mat("paper",(.93,.9,.78))

# Armature contract.
bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,0))
arm=bpy.context.object;arm.name="RobertCartoonRigV2"
base=arm.data.edit_bones[0];base.name="root";base.head=(0,0,0);base.tail=(0,0,.25)
spec={
 "pelvis":((0,0,.75),(0,0,1.05),"root"),"torso":((0,0,1.0),(0,0,1.85),"pelvis"),
 "neck":((0,0,1.82),(0,0,2.05),"torso"),"head":((0,0,2.02),(0,0,2.62),"neck"),
 "eye.L":((-.13,-.08,2.42),(-.13,-.19,2.42),"head"),"eye.R":((.13,-.08,2.42),(.13,-.19,2.42),"head"),
 "eyelid.L":((-.13,-.1,2.47),(-.13,-.2,2.47),"head"),"eyelid.R":((.13,-.1,2.47),(.13,-.2,2.47),"head"),
 "mouth":((0,-.1,2.25),(0,-.2,2.25),"head"),
 "shoulder.L":((-.25,0,1.75),(-.48,0,1.72),"torso"),"upper_arm.L":((-.48,0,1.72),(-.82,0,1.38),"shoulder.L"),
 "lower_arm.L":((-.82,0,1.38),(-.9,0,.98),"upper_arm.L"),"wrist.L":((-.9,0,.98),(-.9,0,.86),"lower_arm.L"),
 "hand.L":((-.9,0,.86),(-.9,0,.66),"wrist.L"),
 "shoulder.R":((.25,0,1.75),(.48,0,1.72),"torso"),"upper_arm.R":((.48,0,1.72),(.82,0,1.38),"shoulder.R"),
 "lower_arm.R":((.82,0,1.38),(.9,0,.98),"upper_arm.R"),"wrist.R":((.9,0,.98),(.9,0,.86),"lower_arm.R"),
 "hand.R":((.9,0,.86),(.9,0,.66),"wrist.R"),
 "hip.L":((-.18,0,.85),(-.2,0,.72),"pelvis"),"upper_leg.L":((-.2,0,.72),(-.2,0,.14),"hip.L"),
 "lower_leg.L":((-.2,0,.14),(-.2,0,-.46),"upper_leg.L"),"ankle.L":((-.2,0,-.46),(-.2,0,-.56),"lower_leg.L"),
 "foot.L":((-.2,0,-.56),(-.2,-.28,-.56),"ankle.L"),
 "hip.R":((.18,0,.85),(.2,0,.72),"pelvis"),"upper_leg.R":((.2,0,.72),(.2,0,.14),"hip.R"),
 "lower_leg.R":((.2,0,.14),(.2,0,-.46),"upper_leg.R"),"ankle.R":((.2,0,-.46),(.2,0,-.56),"lower_leg.R"),
 "foot.R":((.2,0,-.56),(.2,-.28,-.56),"ankle.R")}
for name,(head,tail,parent) in spec.items():
 b=arm.data.edit_bones.new(name);b.head=head;b.tail=tail;b.parent=arm.data.edit_bones[parent]
bpy.ops.object.mode_set(mode="POSE")
for b in arm.pose.bones:b.rotation_mode="XYZ"
bpy.ops.object.mode_set(mode="OBJECT")

parts={}
def piece(name,bone,loc,scale,material,kind="sphere"):
    if kind=="cube":bpy.ops.mesh.primitive_cube_add(location=loc)
    else:bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    world=o.matrix_world.copy();o.parent=arm;o.parent_type="BONE";o.parent_bone=bone;o.matrix_world=world
    parts[name]=o;return o

# Narrower, respectful body; all parts are separate rig followers.
piece("pelvis","pelvis",(0,0,.82),(.31,.16,.27),BLACK)
piece("torso","torso",(0,0,1.43),(.49,.19,.64),BLACK)
piece("shirt","torso",(0,-.19,1.48),(.29,.035,.45),SHIRT,"cube")
piece("neck","neck",(0,0,1.96),(.12,.12,.16),SKIN)
piece("head","head",(0,0,2.32),(.34,.23,.39),SKIN)
piece("hair_main","head",(0,.03,2.59),(.36,.24,.18),HAIR)
piece("hair_side.L","head",(-.3,.01,2.43),(.09,.18,.24),HAIR)
piece("hair_side.R","head",(.3,.01,2.43),(.07,.16,.2),HAIR)
for side,x in (("L",-0.13),("R",0.13)):
 piece(f"eye.{side}",f"eye.{side}",(x,-.225,2.43),(.075,.025,.045),WHITE)
 piece(f"pupil.{side}",f"eye.{side}",(x,-.252,2.43),(.025,.01,.025),BLUE)
 piece(f"eyelid.{side}",f"eyelid.{side}",(x,-.266,2.47),(.086,.012,.018),SKIN)
 # glasses frames
 ring=piece(f"glasses.{side}","head",(x,-.285,2.44),(.11,.018,.075),DARK)
piece("glasses_bridge","head",(0,-.29,2.44),(.07,.012,.012),DARK,"cube")
piece("mouth","mouth",(0,-.255,2.22),(.12,.015,.035),DARK)

for side,s in (("L",-1),("R",1)):
 piece(f"upper_arm.{side}",f"upper_arm.{side}",(.61*s,0,1.52),(.19,.15,.36),BLACK)
 piece(f"lower_arm.{side}",f"lower_arm.{side}",(.84*s,0,1.17),(.16,.13,.34),BLACK)
 piece(f"hand.{side}",f"hand.{side}",(.9*s,0,.81),(.15,.1,.18),SKIN)
 piece(f"upper_leg.{side}",f"upper_leg.{side}",(.2*s,0,.42),(.2,.18,.43),BLACK)
 piece(f"lower_leg.{side}",f"lower_leg.{side}",(.2*s,0,-.2),(.17,.16,.39),BLACK)
 piece(f"foot.{side}",f"foot.{side}",(.2*s,-.13,-.57),(.18,.28,.11),BLACK)

# Props are separately controlled and revealed only for matching actions.
script=piece("script","hand.L",(-.72,-.18,1.25),(.28,.025,.38),PAPER,"cube")
paper=piece("writing_paper","root",(0,-.4,.56),(.55,.3,.025),PAPER,"cube")
keyboard=piece("keyboard","root",(0,-.43,.62),(.5,.22,.055),DARK,"cube")
pen=piece("pen","hand.R",(.58,-.31,.84),(.018,.018,.25),BLUE,"cube")
chair=piece("chair","root",(0,.22,.35),(.55,.42,.07),DARK,"cube")
for o in (script,paper,keyboard,pen,chair):o.hide_render=True

scene=bpy.context.scene;scene.render.engine="BLENDER_EEVEE";scene.render.resolution_x=720;scene.render.resolution_y=720
scene.render.resolution_percentage=100;scene.render.image_settings.file_format="PNG";scene.render.film_transparent=True
scene.render.fps=24;scene.frame_start=1;scene.frame_end=144
bpy.ops.object.camera_add(location=(0,-12,1.15));cam=bpy.context.object;cam.data.type="ORTHO";cam.data.ortho_scale=3.75
cam.rotation_euler=(math.radians(90),0,0);scene.camera=cam
world=bpy.data.worlds.new("transparent");world.color=(0,0,0);scene.world=world
bpy.ops.object.light_add(type="AREA",location=(0,-5,4))
key_light=bpy.context.object;key_light.data.energy=180;key_light.data.shape="DISK";key_light.data.size=5
key_light.rotation_euler=(math.radians(35),0,0)
bpy.ops.object.light_add(type="AREA",location=(-4,-3,2))
fill_light=bpy.context.object;fill_light.data.energy=70;fill_light.data.size=4
fill_light.rotation_euler=(math.radians(70),0,math.radians(-35))

def reset():
    for b in arm.pose.bones:b.rotation_euler=(0,0,0);b.location=(0,0,0);b.scale=(1,1,1)
    for o in (script,paper,keyboard,pen,chair):o.hide_render=True;o.hide_viewport=True
def show(*objects):
    for o in objects:o.hide_render=False;o.hide_viewport=False
def key(frame,bones=None,root_x=None,root_z=None,mouth=.25,blink=1):
    scene.frame_set(frame);bones=bones or {}
    if root_x is not None:arm.pose.bones["root"].location.x=root_x
    if root_z is not None:arm.pose.bones["root"].location.z=root_z
    for name,rot in bones.items():arm.pose.bones[name].rotation_euler=[math.radians(v) for v in rot]
    for b in arm.pose.bones:
        b.keyframe_insert("rotation_euler",frame=frame);b.keyframe_insert("location",frame=frame)
    parts["mouth"].scale.z=mouth;parts["mouth"].keyframe_insert("scale",frame=frame)
    for side in ("L","R"):
        parts[f"eyelid.{side}"].scale.z=blink;parts[f"eyelid.{side}"].keyframe_insert("scale",frame=frame)
def clear_action():
    if arm.animation_data:arm.animation_data_clear()
    for o in parts.values():
        if o.animation_data:o.animation_data_clear()

def build_action(name):
    clear_action();reset()
    if name=="opening_wave":
        for f,x in ((1,-2.4),(36,-1.2),(62,0)):
            phase=1 if (f//18)%2 else -1
            key(f,{"upper_leg.L":(25*phase,0,0),"upper_leg.R":(-25*phase,0,0),
                   "upper_arm.L":(-20*phase,0,0),"upper_arm.R":(20*phase,0,0)},root_x=x)
        key(84,{"upper_arm.R":(0,0,-105),"lower_arm.R":(0,0,-55)},root_x=0)
        key(104,{"upper_arm.R":(0,0,-105),"lower_arm.R":(0,0,-20)},root_x=0,mouth=.8)
        key(124,{"upper_arm.R":(0,0,-105),"lower_arm.R":(0,0,-60)},root_x=0,blink=.1)
        key(144,{"upper_arm.R":(0,0,-70)},root_x=0)
    elif name=="walk":
        for f in range(1,145,12):
            phase=1 if ((f-1)//12)%2==0 else -1;x=-2.6+5.2*(f-1)/143
            key(f,{"upper_leg.L":(32*phase,0,0),"lower_leg.L":(-18*max(phase,0),0,0),
                   "upper_leg.R":(-32*phase,0,0),"lower_leg.R":(-18*max(-phase,0),0,0),
                   "upper_arm.L":(-28*phase,0,0),"upper_arm.R":(28*phase,0,0),
                   "torso":(0,0,3*phase)},root_x=x,root_z=.035*(1 if phase>0 else 0),mouth=.45)
    elif name=="acting_script":
        show(script)
        for f,turn in ((1,-8),(36,6),(72,-4),(108,8),(144,0)):
            key(f,{"torso":(0,turn,0),"head":(0,-turn*.6,0),
                   "upper_arm.L":(0,0,55),"lower_arm.L":(0,0,70),
                   "upper_arm.R":(0,0,-58+turn),"lower_arm.R":(0,0,-68)},mouth=.75 if f%72 else .25)
    elif name=="writing":
        show(paper,pen,chair)
        for f in (1,24,48,72,96,120,144):
            w=8 if (f//24)%2 else -8
            key(f,{"pelvis":(-18,0,0),"upper_leg.L":(-72,0,0),"upper_leg.R":(-72,0,0),
                   "lower_leg.L":(70,0,0),"lower_leg.R":(70,0,0),"torso":(12,0,0),"head":(12,0,0),
                   "upper_arm.R":(0,0,-65),"lower_arm.R":(0,w,-72),
                   "upper_arm.L":(0,0,55),"lower_arm.L":(0,0,65)},root_z=-.22,mouth=.3)
    elif name=="typing":
        show(keyboard,chair)
        for f in range(1,145,12):
            w=10 if (f//12)%2 else -10
            key(f,{"pelvis":(-18,0,0),"upper_leg.L":(-72,0,0),"upper_leg.R":(-72,0,0),
                   "lower_leg.L":(70,0,0),"lower_leg.R":(70,0,0),"torso":(8,0,0),"head":(-4,0,0),
                   "upper_arm.L":(0,0,58),"lower_arm.L":(w,0,68),
                   "upper_arm.R":(0,0,-58),"lower_arm.R":(-w,0,-68)},root_z=-.22,mouth=.5,blink=.15 if f in (48,120) else 1)
    elif name=="sit":
        show(chair)
        key(1,{});key(42,{"head":(0,0,12),"torso":(0,0,8)})
        key(80,{"pelvis":(-12,0,0),"upper_leg.L":(-45,0,0),"upper_leg.R":(-45,0,0),
                "lower_leg.L":(35,0,0),"lower_leg.R":(35,0,0)},root_z=-.12)
        key(120,{"pelvis":(-18,0,0),"upper_leg.L":(-72,0,0),"upper_leg.R":(-72,0,0),
                 "lower_leg.L":(70,0,0),"lower_leg.R":(70,0,0)},root_z=-.22)
        key(144,{"pelvis":(-18,0,0),"upper_leg.L":(-72,0,0),"upper_leg.R":(-72,0,0),
                 "lower_leg.L":(70,0,0),"lower_leg.R":(70,0,0)},root_z=-.22)
    elif name=="stand":
        show(chair)
        key(1,{"pelvis":(-18,0,0),"upper_leg.L":(-72,0,0),"upper_leg.R":(-72,0,0),
               "lower_leg.L":(70,0,0),"lower_leg.R":(70,0,0)},root_z=-.22)
        key(58,{"pelvis":(-10,0,0),"upper_leg.L":(-42,0,0),"upper_leg.R":(-42,0,0),
                "lower_leg.L":(30,0,0),"lower_leg.R":(30,0,0),"torso":(10,0,0)},root_z=-.1)
        key(110,{},root_z=0);key(144,{},root_z=0)
    elif name=="gesture":
        for f,a in ((1,20),(36,85),(72,35),(108,100),(144,20)):
            key(f,{"upper_arm.R":(0,0,-a),"lower_arm.R":(0,0,-55),
                   "head":(0,0,-5 if f%72 else 5),"torso":(0,0,3)},mouth=.85 if f%72 else .25,blink=.1 if f==108 else 1)
    elif name=="idle":
        for f,a in ((1,0),(36,3),(72,-3),(108,2),(144,0)):
            key(f,{"head":(0,0,a),"torso":(0,0,-a*.25)},mouth=.7 if f in (36,108) else .25,blink=.1 if f==72 else 1)
    else:raise ValueError(name)
    action=bpy.data.actions.new(name);arm.animation_data_create();old=arm.animation_data.action
    # Keyframes already live in the automatically created action. Rename it.
    if old: old.name=name

actions=["opening_wave","acting_script","writing","walk","sit","typing","gesture","stand","idle"]
requested=os.environ.get("ROBERT_RIG_ACTIONS","").strip()
if requested:actions=[name.strip() for name in requested.split(",") if name.strip()]
result=[]
for name in actions:
    build_action(name)
    if os.environ.get("ROBERT_RIG_PREVIEW_ONLY")=="1":
        scene.frame_start=62;scene.frame_end=62
    else:
        scene.frame_start=1;scene.frame_end=144
    folder=FRAMES/name
    if folder.exists():shutil.rmtree(folder)
    folder.mkdir(parents=True)
    scene.render.filepath=str(folder/"frame_")
    bpy.ops.render.render(animation=True)
    result.append({"clip":name,"frames":144,"fps":24,"duration_seconds":6.0,
                   "root_motion":name in {"opening_wave","walk","sit","stand"},
                   "bone_tracks":["root","pelvis","torso","neck","head","eyelids","mouth","arms","hands","legs","feet"]})

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"ROBERT_CARTOON_RIG_V2.blend"))
(OUT/"ROBERT_CARTOON_RIG_SPEC.json").write_text(json.dumps({
 "status":"AWAITING_ROBERT_CHARACTER_REVIEW","armature":arm.name,
 "bones":[b.name for b in arm.data.bones],"required_actions":actions,
 "separate_controls":["root","pelvis","torso","neck","head","eyes","eyelids","mouth","shoulders","upper arms","lower arms","wrists","hands","hips","upper legs","lower legs","ankles","feet"],
 "character_sheet":"ROBERT_CARTOON_CHARACTER_SHEET_V2.png","locked":False},indent=2)+"\n")
(OUT/"ROBERT_CARTOON_RIG_VALIDATION.json").write_text(json.dumps({
 "status":"RENDERED_AWAITING_VISUAL_VALIDATION","flattened_png_primary_method":False,
 "bone_count":len(arm.data.bones),"actions":result,"identity":"original respectful Robert cartoon",
 "owner_approved":False,"locked":False},indent=2)+"\n")
print(json.dumps({"output":str(OUT),"actions":result},indent=2))
