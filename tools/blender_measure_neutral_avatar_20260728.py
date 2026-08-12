from pathlib import Path
import bpy, json
from mathutils import Vector

ROOT=Path(r"C:\Users\robmc\Kira")
SOURCE=ROOT/"Assets/third_party/intake/3d_models_kira_world/avatar_builder_references/base_female_game_ready_rigged_low_poly_light.glb"
OUT=ROOT/"Avatar/avatar_builder/proofs/neutral_adult_foundation_20260728"
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
def bounds(o):
    pts=[o.matrix_world@Vector(c) for c in o.bound_box]
    lo=[min(p[i] for p in pts) for i in range(3)]
    hi=[max(p[i] for p in pts) for i in range(3)]
    return {"min_m":lo,"max_m":hi,"dimensions_m":[hi[i]-lo[i] for i in range(3)]}
by_vertices=sorted(meshes,key=lambda o:len(o.data.vertices),reverse=True)
roles={"body":by_vertices[0],"hair":by_vertices[1],"mouth":by_vertices[2],
       "clothing":by_vertices[3],"hair_extra":by_vertices[4],"eyes":by_vertices[5]}
result={"status":"MEASURED_FROM_SELECTED_SOURCE","roles":{
    k:{"object":v.name,"vertices":len(v.data.vertices),**bounds(v)} for k,v in roles.items()
}}
(OUT/"SOURCE_GEOMETRY_MEASUREMENTS.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
