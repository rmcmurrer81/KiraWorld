from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[W/'world-film-layout-reference-040/NOTES.md',
 W/'world-installed-observation-export-057/actual-001/package/scene.json',
 W/'world-installed-observation-export-057/INSTALLED-SOURCE-CLOSURE.json',
 W/'world-observation-trim-056/native-successor-001/installation/ROOT-INSTALL-REVIEW.json',
 K/'tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs',
 K/'tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs']
def put(name,obj):
 with (H/name).open('xb') as f:f.write((json.dumps(obj,indent=2)+'\n').encode())
put('INPUT-PINS.json',{'files':[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in inputs],
 'private_original_inputs_copied':False,'implementation_changed':False})
files=[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.iterdir()) if p.is_file()]
put('DELIVERY.json',{'status':'FROZEN058_READ_ONLY_DINING_PROPOSAL','files':files,'source_worlds_changed':False,
 'canonical_changes':0,'models_GPU_UI_exports':0,'owner_approval':False,'implementation_started':False})
print(json.dumps({'delivery':str(H/'DELIVERY.json'),'sha256':sha(H/'DELIVERY.json'),'files':len(files)}))
