"""Build V23 from intact V1 with directly extruded local anatomy topology."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
HAIR_SOURCE=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v23_direct_local_topology"
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body=bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
for obj in list(bpy.context.scene.objects):
    if "External_Anatomy_ESTIMATED" in obj.name or "Separate_Brown_Iris" in obj.name or "Separate_Pupil" in obj.name:
        bpy.data.objects.remove(obj,do_unlink=True)

# Named, locally centered, smoothly blended torso slimming. No hands, feet,
# face, anatomy, or joint/global-origin scaling.
torso_group=body.vertex_groups.new(name="V23_TORSO_SLIMMING_MASK")
torso_ids=[]
for v in body.data.vertices:
    co=v.co
    if .84<co.z<1.46 and abs(co.x)<.29:
        lower=min(1.0,max(0.0,(co.z-.84)/.12))
        upper=min(1.0,max(0.0,(1.46-co.z)/.12))
        w=lower*upper
        co.x*=1.0-.035*w
        co.y*=1.0-.025*w
        torso_ids.append(v.index)
if torso_ids: torso_group.add(torso_ids,1.0,"REPLACE")

# V1 hand topology and nails are retained but the palms/fingers are made
# modestly wider and finger length is reduced around each local wrist center.
hand_group=body.vertex_groups.new(name="V23_HAND_PROPORTION_MASK")
hand_ids=[]
for v in body.data.vertices:
    co=v.co
    if abs(co.x)>.315 and .74<co.z<1.03:
        center_x=.355 if co.x>0 else -.355
        co.x=center_x+(co.x-center_x)*1.075
        co.y*=1.035
        if co.z<.925:
            co.z=.925+(co.z-.925)*.955
        hand_ids.append(v.index)
if hand_ids: hand_group.add(hand_ids,1.0,"REPLACE")

bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()

def selected_faces(predicate):
    return [f for f in bm.faces if predicate(f.calc_center_median())]

def extrude_steps(faces, steps):
    current=list(faces)
    all_new=[]
    for translation,scale_xyz in steps:
        result=bmesh.ops.extrude_face_region(bm,geom=current,use_keep_orig=False)
        verts=[element for element in result["geom"] if isinstance(element,bmesh.types.BMVert)]
        new_faces=[element for element in result["geom"] if isinstance(element,bmesh.types.BMFace)]
        if not verts or not new_faces:
            raise RuntimeError("local topology extrusion produced no geometry")
        center=sum((v.co for v in verts),Vector())/len(verts)
        sx,sy,sz=scale_xyz
        for v in verts:
            d=v.co-center
            v.co=Vector((center.x+d.x*sx,center.y+d.y*sy,center.z+d.z*sz))+Vector(translation)
        current=[f for f in new_faces if all(v in verts for v in f.verts)]
        all_new.extend(new_faces)
    return current,all_new

# Shaft/root: a compact midline pubic face group is extruded forward and
# downward in five connected stages. The distal stages flare into the glans.
shaft_base=selected_faces(lambda c: abs(c.x)<.020 and -.095<c.y<-.035 and .748<c.z<.810)
shaft_cap,shaft_faces=extrude_steps(shaft_base,[
    ((0,-.020,-.006),(1.00,1.00,.98)),
    ((0,-.026,-.020),(.94,.98,.96)),
    ((0,-.025,-.024),(.92,.98,.95)),
    ((0,-.020,-.020),(1.08,1.05,1.05)),
    ((0,-.012,-.012),(1.12,1.06,1.08)),
])

# Paired scrotal sacs are extruded from lower-left/right pubic faces. They
# descend behind the shaft, meet medially without sharing an intersecting
# hidden shell, and preserve a visible central raphe valley.
scrotal_faces=[]
for side in (-1,1):
    base=selected_faces(lambda c,s=side: s*c.x>.010 and s*c.x<.052 and -.070<c.y<-.018 and .675<c.z<.746)
    cap,new_faces=extrude_steps(base,[
        ((side*.004,-.010,-.018),(1.03,1.02,1.00)),
        ((side*.006,-.010,-.022),(1.08,1.04,1.08)),
        ((side*.004,-.004,-.018),(1.05,1.02,1.10)),
    ])
    scrotal_faces.extend(new_faces)

bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.00001)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
bm.to_mesh(body.data);bm.free();body.data.update()
for p in body.data.polygons: p.use_smooth=True

# New faces inherit the same authored V1 skin material. Preserve V1 albedo,
# lip/areola/nail/roughness/subsurface maps rather than replacing them with a
# flat procedural shader.
skin=bpy.data.materials.get("MBLab_skin3")
if skin is None: raise RuntimeError("V1 authored skin missing")
for p in body.data.polygons:
    if abs(p.center.x)<.12 and -.30<p.center.y<.08 and .56<p.center.z<.88:
        p.material_index=1

# Append the removable V15 layered hair meshes and fit a fuller dark-blonde
# static silhouette. Head geometry remains untouched.
with bpy.data.libraries.load(str(HAIR_SOURCE),link=False) as (data_from,data_to):
    data_to.objects=[name for name in ("Object_6","Object_7") if name in data_from.objects]
for hair in data_to.objects:
    if hair is None: continue
    bpy.context.collection.objects.link(hair)
    hair.scale.x*=1.16;hair.scale.y*=1.18;hair.scale.z*=1.10
    hair.location.y-=.020;hair.location.z-=.012
    for slot in hair.material_slots:
        if slot.material:
            material=slot.material.copy();material.name="Robert_V23_Removable_Dark_Blonde_Hair"
            material.diffuse_color=(.43,.29,.13,1)
            if material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type=="BSDF_PRINCIPLED":
                        node.inputs["Base Color"].default_value=(.43,.29,.13,1)
                        node.inputs["Roughness"].default_value=.44
            slot.material=material
    hair["runtime_groom_complete"]=False

body.name="BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_DIRECT_LOCAL_TOPOLOGY"
body["status"]="V23 ENGINEERING CANDIDATE — REQUIRES VISUAL GATE"
body["source_v1_sha256"]=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
body["anatomy_method"]="DIRECT FACE-REGION EXTRUSION FROM RETAINED V1 BODY"
body["global_scaling_used"]=False;body["boolean_union_used"]=False;body["runtime_activation_allowed"]=False
blend=OUT/"BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_DIRECT_LOCAL_TOPOLOGY.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
(OUT/"BUILD_REPORT.json").write_text(json.dumps({
 "schema_version":1,"status":body["status"],"base":"intact V1 likeness body",
 "separate_primitive_anatomy_removed":True,"shaft_base_face_count":len(shaft_base),
 "shaft_new_face_count":len(shaft_faces),"scrotal_new_face_count":len(scrotal_faces),
 "global_scaling_used":False,"boolean_union_used":False,"reference_surface_transferred":False,
 "movement":"not started","runtime_attachment":"prohibited"
},indent=2)+"\n",encoding="utf-8")
print(blend)
