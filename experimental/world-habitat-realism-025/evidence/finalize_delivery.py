"""Freeze025 implementation details; root owns research, UI review and publication."""
from pathlib import Path
import datetime,difflib,hashlib,json
H=Path(__file__).resolve().parent;R=H/'revision-002';E=R/'candidate/tools/world_builder_engine';K=Path.home()/'Kira'
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
files=[];diff=[]
for name in ('walk_controller.mjs','viewer.mjs','index.html','style.css'):
 baseline=H.parent/'world-working-doors-candidate-024/baseline'/name;resident=K/'tools/world_builder_engine'/name;after=E/name
 assert baseline.read_bytes()==resident.read_bytes()
 files.append({'relative_path':'tools/world_builder_engine/'+name,'before':pin(baseline),'after':pin(after)})
 diff.extend(difflib.unified_diff(baseline.read_text(encoding='utf-8-sig').splitlines(True),after.read_text(encoding='utf-8-sig').splitlines(True),fromfile='installed/'+name,tofile='025-revision002/'+name))
(H/'CHANGES-FROM-INSTALLED.patch').write_text(''.join(diff),encoding='utf-8',newline='\n')
result={'status':'FURNISHED_HABITAT025_REVISION002_STAGED_NOT_INSTALLED_OR_VISUALLY_APPROVED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'files':files,'authored_modules':[pin(H/'room_dressing_plan.mjs'),pin(H/'room_dressing_render.mjs')],
 'composition_script':pin(H/'integrate_viewer.py'),'reach_revision_script':pin(H/'prepare_revision002.py'),
 'synthetic_fixture_test':pin(H/'TEST-RESULT-002.json'),'existing_geometry_test':pin(H/'TEST-RESULT-003.json'),'step_reach_test':pin(R/'STEP-REACH-TEST.json'),
 'preview_plan':pin(R/'PREVIEW-PLAN.json'),'equipment_assemblies':16,'distinct_equipment_types':15,'extra_colliders':51,'authored_meshes':406,'omitted_equipment':0,
 'canonical_files_changed':False,'owner_files_changed':False,'models_gpu_browser_started':False,'protected_source_owner_files':121,
 'source_appearance_status':'Original authored procedural equipment; old Mars appearance remains owner-rejected; new visual inspection pending.',
 'installation_hold':'Integrate and review026 compatibility first so existing saved previews remain readable.',
 'limitations':['Static equipment has no simulated science, medical or life-support behavior.','No pressure airlock or door-state persistence.','Conservative AABB equipment bounds and door sweeps.','No photorealism or finished-world approval.'],
 'research_ownership':'Root maintains research/ and RESEARCH.md; this implementation did not edit them.'}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'sha256':pin(H/'DELIVERY.json')['sha256']}))
