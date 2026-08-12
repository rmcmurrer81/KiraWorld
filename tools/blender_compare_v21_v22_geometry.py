"""Compare V21 engineering baseline and V22 by stable vertex index."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
V21=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v21_bounded_local_repair/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V21_BOUNDED_LOCAL_REPAIR.blend"
OUT=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v22_protected_bridge_rebuild"
V22=OUT/"BIOLOGICAL_ROBERT_STATIC_LIKENESS_V22_PROTECTED_BRIDGE_REBUILD.blend"
bpy.ops.wm.open_mainfile(filepath=str(V21))
a=max((o for o in bpy.data.objects if o.type=="MESH" and o.name.startswith("BIOLOGICAL_ROBERT")),key=lambda o:len(o.data.vertices))
base=[v.co.copy() for v in a.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(V22))
b=bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V22_PROTECTED_BRIDGE_REBUILD"]
zones={"head_face_neck":[],"hands_fingers_wrists_forearms":[],"lower_legs_feet":[],"protected_thighs":[]}
for i,(old,new) in enumerate(zip(base,b.data.vertices)):
    co=old;delta=(new.co-old).length
    if co.z>1.52: zones["head_face_neck"].append(delta)
    if abs(co.x)>.255 and .82<co.z<1.48: zones["hands_fingers_wrists_forearms"].append(delta)
    if co.z<.48: zones["lower_legs_feet"].append(delta)
    if .48<=co.z<=.98 and abs(co.x)>.15: zones["protected_thighs"].append(delta)
summary={name:{"maximum_delta":max(values,default=0.0),"changed_count":sum(v>1e-9 for v in values)} for name,values in zones.items()}
status="PASS" if all(item["maximum_delta"]<=1e-9 for item in summary.values()) else "FAIL"
(OUT/"V21_V22_GEOMETRY_DELTA_REPORT.json").write_text(json.dumps({
 "schema_version":1,"status":status,"tolerance":1e-9,"vertex_count_v21":len(base),"vertex_count_v22":len(b.data.vertices),
 "protected_regions":summary,"interpretation":"V21 is used only as protected-region baseline; local anatomy geometry is not preserved."
},indent=2)+"\n",encoding="utf-8")
print(status,summary)
