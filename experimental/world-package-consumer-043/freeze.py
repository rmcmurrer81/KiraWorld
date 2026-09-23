from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
def pin(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(name,v):
 with (H/name).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
checks=json.loads((H/'CHECK-RESULT-003.json').read_bytes())
assert checks['status']=='PASS' and checks['protected_originals_canonical_five_current_preview_and_sample_unchanged']
for name in ['TEST-ADMISSION.json','TEST-RUNTIME-FINAL.json','TEST-IMPORT-003.json','TEST-REFERENCE-3.json']:
 assert 'PASS' in json.loads((H/name).read_bytes())['status']
runtime=['index.html','app.mjs','file_admission.mjs','package_loader.mjs','runtime.mjs','horizontal_navigation.mjs','serve.py']
runtime+=sorted(p.relative_to(H).as_posix() for p in (H/'vendor').rglob('*') if p.is_file())
plan={'contract':'isolated_package_consumer_review_plan_v1','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'purpose':'Independent first-person Three consumer of an explicit exported package; code review only, no installation or UI launch.',
 'canonical_changes':[],'runtime_files':{n:pin(H/n) for n in runtime},
 'sample_package':{p.name:pin(p) for p in sorted((H/'sample-package').iterdir())},
 'actual_fixture':'Installed042 authored Mars derived package','source_geometry_required_at_runtime':False,
 'native_game_engine_adapter':False,'vr_runtime':False,'pressure_simulation':False,'visual_owner_approval':False,
 'validation':{n:pin(H/n) for n in ['TEST-ADMISSION.json','TEST-RUNTIME-FINAL.json','TEST-IMPORT-003.json','TEST-REFERENCE-3.json','CHECK-RESULT-003.json']},
 'pending':['Root review of final file admission patch and closure','Browser visual/input review when authorized','Additional supported export fixtures before wider compatibility claims']}
write('REVIEW-PLAN.json',plan)
write('CURRENT-STATUS.json',{'status':'ISOLATED_PACKAGE_CONSUMER_CPU_VERIFIED_NOT_INSTALLED','review_plan_sha256':pin(H/'REVIEW-PLAN.json')['sha256'],
 'first_person_package_runtime_prototype':True,'native_engine_or_vr':False,'canonical_writes':0,'source_worlds_modified':False,'gpu_models_browser_servers':0,
 'admission_tests':12,'runtime_tests':20,'actual_meshes':565,'actual_embedded_textures':67,'colliders':134,'doors':6,
 'reference_walk_steps':178,'reference_door_pose_comparisons':1716,'maximum_numerical_difference':0,
 'final_importer_elapsed_seconds':checks['elapsed_seconds'],'final_importer_sampled_peak_rss_bytes':checks['sampled_family_peak_rss_bytes'],
 'protected_originals_unchanged':116,'visual_review':'PENDING','owner_approval':False})
files={p.relative_to(H).as_posix():pin(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write('SOURCE-CLOSURE.json',{'contract':'frozen_package_consumer_source_closure_v1','files':files,'canonical_or_owner_files_modified':False})
print(json.dumps({'plan_sha256':pin(H/'REVIEW-PLAN.json')['sha256'],'closure_sha256':pin(H/'SOURCE-CLOSURE.json')['sha256'],'files':len(files),'bytes':sum(p['bytes'] for p in files.values())}))
