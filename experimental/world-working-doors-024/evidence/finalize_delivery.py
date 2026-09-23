"""Freeze the working-door candidate evidence; no install or publication."""
from pathlib import Path
import datetime,difflib,hashlib,json
H=Path(__file__).resolve().parent;K=Path.home()/'Kira';E=H/'candidate/tools/world_builder_engine'
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
files=[];diff=[]
for name in ('walk_controller.mjs','viewer.mjs','index.html','style.css'):
 old=H/'baseline'/name;new=E/name;resident=K/'tools/world_builder_engine'/name
 assert old.read_bytes()==resident.read_bytes()
 files.append({'relative_path':'tools/world_builder_engine/'+name,'before':pin(old),'after':pin(new)})
 diff.extend(difflib.unified_diff(old.read_text(encoding='utf-8-sig').splitlines(True),new.read_text(encoding='utf-8-sig').splitlines(True),fromfile='installed/'+name,tofile='candidate/'+name))
(H/'CHANGES.patch').write_text(''.join(diff),encoding='utf-8',newline='\n')
result={'status':'WORKING_DOORS_STAGED_NOT_INSTALLED_OR_VISUALLY_REVIEWED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'files':files,'test_result':pin(H/'TEST-RESULT-003.json'),'existing_layout_test':pin(H/'EXISTING-LAYOUT-DOOR-CHECK.json'),
 'preview_plan':pin(H/'PREVIEW-PLAN.json'),'owner_files_preserved':121,'installed':False,'models_or_gpu_started':False,
 'compatibility_hold':'Root separately reviews026 immutable-preview compatibility before replacing current renderer assets.',
 'owner_quality_status':'Existing Mars appearance rejected. Doors require visual review. No room realism, pressure simulation or finished-world acceptance.',
 'furnishing_interface':'createWalkController(geometry, {extraColliders: plan.colliders}); createDoorSystem(geometry).assemblies() exposes swingBounds.',
 'limitations':['Conservative AABB leaf collision and quarter-disc sweep; not rigid-body dynamics.','Door states are session-local.','No pressure seals, operational airlock, furniture realism or world completion.']}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'delivery_sha256':pin(H/'DELIVERY.json')['sha256'],'files':len(files)}))
