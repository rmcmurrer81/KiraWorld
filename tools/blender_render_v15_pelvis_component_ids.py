"""Render material-one face components with distinct colors."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v22_protected_bridge_rebuild/diagnostics"
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body=bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14"]
faces=[p for p in body.data.polygons if p.material_index==1]
vf={}
for p in faces:
    for vi in p.vertices: vf.setdefault(vi,set()).add(p.index)
fm={p.index:p for p in faces}; remaining=set(fm); comps=[]
while remaining:
    seed=remaining.pop(); stack=[seed]; members={seed}
    while stack:
        fid=stack.pop()
        for vi in fm[fid].vertices:
            for other in vf.get(vi,()):
                if other in remaining:
                    remaining.remove(other);members.add(other);stack.append(other)
    comps.append(members)
colors=[(.95,.1,.1,1),(.1,.95,.1,1)]
for color in colors:
    mat=bpy.data.materials.new("component");mat.diffuse_color=color;body.data.materials.append(mat)
for i,comp in enumerate(sorted(comps,key=len)):
    slot=len(body.data.materials)-2+i
    for fid in comp: fm[fid].material_index=slot
for p in body.data.polygons:
    if p.material_index not in {len(body.data.materials)-2,len(body.data.materials)-1}: p.material_index=0
scene=bpy.context.scene
for o in list(scene.objects):
    if o.type in {"CAMERA","LIGHT"}: bpy.data.objects.remove(o,do_unlink=True)
camd=bpy.data.cameras.new("cam");cam=bpy.data.objects.new("cam",camd);bpy.context.collection.objects.link(cam);scene.camera=cam
cam.location=(0,-1.25,.73);cam.rotation_euler=(Vector((0,0,.73))-cam.location).to_track_quat("-Z","Y").to_euler();cam.data.lens=72
scene.render.engine="BLENDER_WORKBENCH";scene.render.resolution_x=900;scene.render.resolution_y=900;scene.display.shading.color_type="MATERIAL";scene.display.shading.light="FLAT"
scene.render.filepath=str(OUT/"v15_material1_component_ids.png");bpy.ops.render.render(write_still=True)
