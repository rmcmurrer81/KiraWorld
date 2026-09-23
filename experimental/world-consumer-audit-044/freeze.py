from pathlib import Path
import datetime,difflib,hashlib,json
H=Path(__file__).resolve().parent;C=H/'candidate';B=H.parent/'world-package-consumer-043'
def pin(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def put(name,v):
 with (H/name).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
protected=json.loads((H.parent/'world-bunk-detail-042/INSTALL-PLAN.json').read_bytes())
assert len(protected['protected_inputs'])==116 and all(pin(Path(p))['sha256']==s for p,s in protected['protected_inputs'].items())
assert all(pin(Path(r['target']))['sha256']==r['after']['sha256'] for r in protected['files'])
preview=Path('@kira_root/Data/world_layout_previews/layout-4b8661bcb27e70cc774276e5/manifest.json')
assert pin(preview)['sha256']=='f6f6dd4545527be33eded699ca560ab184ca225b76a866dada975383cef1ceac'
baseline=json.loads((B/'SOURCE-CLOSURE.json').read_bytes());assert all(pin(B/p)['sha256']==v['sha256'] for p,v in baseline['files'].items())
changed=[];patch=[]
for p in sorted(C.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(C).as_posix();old=B/rel
 if old.exists() and pin(old)==pin(p):continue
 changed.append({'relative_path':rel,'before':pin(old) if old.exists() else None,'after':pin(p)})
 patch.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True) if old.exists() else [],p.read_text(encoding='utf-8').splitlines(True),fromfile='baseline043/'+rel,tofile='candidate044/'+rel))
assert {r['relative_path'] for r in changed}=={'app.mjs','package_loader.mjs','scene_disposal.mjs'}
with (H/'CHANGES.patch').open('x',encoding='utf-8') as f:f.write(''.join(patch))
evidence=['UI-LIFECYCLE-PASS-2.json','GLB-ADMISSION-FINAL.json','PNG-ADMISSION-FINAL.json','DISPOSAL-FINAL.json','SESSION-RESET-PASS.json','RUNTIME-REGRESSION-PASS.json','ACTUAL-IMPORT-PASS.json','CHECK-RESULT.json']
for name in evidence:assert 'PASS' in json.loads((H/name).read_bytes())['status']
plan={'contract':'isolated_consumer_audit_review_plan_v1','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'base_public_commit':'2ad6feef562ae87c443499415520ba5c97684c67',
 'canonical_changes':[],'changed_candidate_files':changed,'runtime_closure':{p.relative_to(C).as_posix():pin(p) for p in sorted(C.rglob('*')) if p.is_file()},
 'validation':{n:pin(H/n) for n in evidence},'source_worlds_unchanged':116,'current_preview_manifest_unchanged':True,'baseline043_frozen_unchanged':True,
 'physics_navigation_unchanged':True,'native_game_engine_or_vr':False,'ui_visual_owner_approval':False,'installed':False}
put('REVIEW-PLAN.json',plan)
put('CURRENT-STATUS.json',{'status':'ISOLATED044_CPU_VERIFIED_NOT_INSTALLED','review_plan_sha256':pin(H/'REVIEW-PLAN.json')['sha256'],'changed_candidate_files':3,
 'ui_lifecycle_mock_cases':8,'uri_admission_cases':5,'png_predecode_negative_cases':20,'cleanup_cases':2,'session_reset_cases':3,'retained_runtime_tests':20,
 'actual_glb_import_pass':True,'preserved_originals':116,'canonical_five_and_current_preview_manifest_unchanged':True,'frozen043_unchanged':True,
 'browser_ui_servers_models_gpu_calls':0,'visual_or_owner_approval':False,'not_a_hostile_file_sandbox':True})
put('SOURCE-CLOSURE.json',{'files':{p.relative_to(H).as_posix():pin(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}})
print(json.dumps({'status':'FROZEN','review_plan_sha256':pin(H/'REVIEW-PLAN.json')['sha256'],'closure_sha256':pin(H/'SOURCE-CLOSURE.json')['sha256'],'changed':changed}))
