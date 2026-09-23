from pathlib import Path
import datetime,hashlib,json,psutil
H=Path(__file__).resolve().parent;E=Path('@kira_root/tools/world_builder_engine')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());pins=json.loads((H/'SOURCE-PINS.json').read_bytes())
assert len(plan['protected_inputs'])==116 and all(sha(p)==v for p,v in plan['protected_inputs'].items())
assert all(sha(E/r)==v for r,v in pins.items())
assert all(sha(r['target'])==r['before_sha256'] and sha(r['after']['path'])==r['after']['sha256'] for r in plan['files'])
assert not [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='blender.exe']
for name in ['GEOMETRY-RESULT.json','ACTUAL-EXPORT-RESULT.json','CPU-RENDER-RESULT.json','CPU-RENDER-RESULT-002.json']:assert (H/name).is_file()
assert sha(H/'actual-001/package/scene.glb')=='97567b738b58b90f6b1232a87981b71489d4519dd0f497d94c67ebc48a40dabb'
put(H/'ASSESSMENT.json',{'status':'ISOLATED053_TECHNICAL_PASS_NATIVE_VISUAL_REVIEW_PENDING','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'installed':False,'protected_originals_unchanged':116,'installed_engine_files_unchanged':len(pins),'owner_approval':False,'native_preview_review':False,'root_artifact_review':'pending',
 'agent_actual_artifact_review':{'first':'Visible recessed frame; exterior faint gray under reused interior-focused inspection lighting. Held as a useful vista.','diagnostic_second':'Wider actual inside-through-aperture view shows retained rib/frame and muted brown terrain/horizon. Geometry reads as a window. Materials/terrain remain visibly procedural; diagnostic illumination differs from native viewer.','same_glb_meshes_materials_both':True,'pressure_claim':False,'finished_realism_claim':False},
 'technical':{'geometry_cases':12,'appearance_gate_cases':3,'actual_export_roundtrip':True,'repeated_new_immutable_preview_reused':True,'solid_safety_collider_unchanged':True,'door_pair_policy_unchanged':True},
 'resource_evidence':{'no_new_gpu_or_model_job':True,'owned_blender_processes_after':0,'free_ram_bytes':psutil.virtual_memory().available,'studio014_observed_progress':'16/30 before; 17/30 after. No source/control writes to Studio014.'},
 'next_required':'Root artifact review, then native preview inspection after014 releases GPU; separate installation authorization. Do not install from technical tests alone.'})
files={}
for p in sorted(H.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts or p.name in ('DELIVERY.json','FROZEN-MANIFEST.json'):continue
 files[p.relative_to(H).as_posix()]={'sha256':sha(p),'bytes':p.stat().st_size}
put(H/'FROZEN-MANIFEST.json',{'status':'FROZEN_ISOLATED_NOT_INSTALLED','files':files})
put(H/'DELIVERY.json',{'status':'053_READY_FOR_ROOT_REVIEW_NOT_INSTALLED','files':len(files),'manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'changed_canonical_files_if_later_approved':5,'source_diff_sha256':sha(H/'SOURCE.diff'),'protected_originals_unchanged':116,
 'first_artifact':str(H/'cpu-review-001/viewport-review.png'),'diagnostic_artifact':str(H/'cpu-review-002/viewport-review.png'),'actual_glb':str(H/'actual-001/package/scene.glb'),'source_glb_sha256':sha(H/'actual-001/package/scene.glb'),
 'important_limit':'Native preview illumination/view has not been reviewed. Diagnostic lighting is not a product change or owner approval. Root requires native review before visual acceptance/installation.',
 'public_backup_omissions':'A later portable backup must omit original-source geometry copies inside runtime_context and redact machine paths in technical receipts. Preserve authored modules, exact pins/diff, tests, derived fictional GLB and both render artifacts.'})
print(json.dumps(json.loads((H/'DELIVERY.json').read_bytes())))
