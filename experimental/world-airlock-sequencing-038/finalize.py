from pathlib import Path
import datetime,difflib,hashlib,json
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value):
 p=H/name;assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
pins=json.loads((H/'BASELINE-PINS.json').read_bytes())
assert all(sha(K/'tools/world_builder_engine'/n)==v['sha256'] for n,v in pins.items())
changed=[]
for n,pin in pins.items():
 assert sha(H/'baseline'/n)==pin['sha256']
 if sha(H/'candidate/tools/world_builder_engine'/n)!=pin['sha256']:changed.append(n)
assert changed==['walk_controller.mjs']
protected=json.loads((W/'world-preview-refresh-candidate-028/INSTALL-PLAN.json').read_bytes())['protected_inputs']
assert all(sha(p)==v for p,v in protected.items())
target=K/'tools/world_builder_engine/walk_controller.mjs';candidate=H/'candidate/tools/world_builder_engine/walk_controller.mjs'
plan={'status':'PROPOSED_NOT_INSTALLED_ROOT_REVIEW_REQUIRED','files':[{'relative_path':'tools/world_builder_engine/walk_controller.mjs',
 'target':str(target),'before_sha256':sha(target),'preimage':str(H/'baseline/walk_controller.mjs'),
 'after':{'path':str(candidate),'sha256':sha(candidate),'bytes':candidate.stat().st_size}}],
 'protected_originals':{'count':len(protected),'receipt':'../world-preview-refresh-candidate-028/INSTALL-PLAN.json','unchanged':True},
 'pending':['Root code review','Coordinated new immutable preview and UI check','Explicit successor to037 before exporting new sequencing behavior']}
write('INSTALL-PLAN.json',plan)
diff=''.join(difflib.unified_diff((H/'baseline/walk_controller.mjs').read_text().splitlines(True),candidate.read_text().splitlines(True),fromfile='installed/walk_controller.mjs',tofile='candidate/walk_controller.mjs'))
(H/'CONTROLLER-CHANGES.patch').write_text(diff,encoding='utf-8')
write('DELIVERY.json',{'status':'038_PAIRED_DOORS_CPU_VALIDATED_NOT_INSTALLED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'candidate_sha256':sha(candidate),'baseline_sha256':sha(target),'changed_files':changed,
 'sequencing_checks':16,'generic_checks':33,'actual_saved_geometry_checks':3,
 'installed_frontend_unchanged':True,'protected_original_files_unchanged':len(protected),'gpu_model_browser_native_ui_jobs':0,
 'pressure_simulation':False,'exterior_eva_portal':False,'visual_approval':False,
 'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'frozen036_037_changed':False})
print((H/'DELIVERY.json').read_text())
