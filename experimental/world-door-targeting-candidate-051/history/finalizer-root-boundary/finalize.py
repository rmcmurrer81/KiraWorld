"""Read-only preservation/compatibility checks and local evidence closure."""
from pathlib import Path
import datetime,hashlib,json,sys
import psutil
H=Path(__file__).resolve().parent;K=Path('@kira_root');E=K/'tools/world_builder_engine';W=H.parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());assert sha(H/'INSTALL-PLAN.json')=='acc62a7e35915eaf62ce3914b04f0cc14f144285f00c701fa1f7a11edc2d435c'
assert len(plan['protected_inputs'])==116 and all(sha(p)==v for p,v in plan['protected_inputs'].items())
pins=json.loads((H/'SOURCE-PINS.json').read_bytes());assert all(sha(E/p)==v for p,v in pins.items())
for row in plan['files']:
 assert sha(row['target'])==row['before_sha256'] and sha(row['preimage'])==row['before_sha256'] and sha(row['after']['path'])==row['after']['sha256']
from world_builder_engine.world_layout_preview import verify_preview
from world_builder_engine.pipeline import latest_preview
old=json.loads((W/'world-galley-detail-045/ROOT-EXECUTION.json').read_bytes())['verified_unchanged_previews']
verified=[]
for row in old:
 path=K/'Data/world_layout_previews'/row['id']/'manifest.json';verify_preview(path,row['manifest_sha256']);verified.append(row)
fresh=json.loads((H/'actual-001/PREVIEW-RESULT.json').read_bytes());verify_preview(fresh['current']['manifest_path'],fresh['current']['manifest_sha256'])
job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';assert latest_preview(job)==fresh['previous_pointer']
package=H/'actual-001/package';prior=W/'world-galley-detail-045/installed-mars-001/package'
assert (package/'scene.glb').read_bytes()==(prior/'scene.glb').read_bytes()
a=json.loads((package/'scene.json').read_bytes());b=json.loads((prior/'scene.json').read_bytes())
assert a.pop('provenance')!=b.pop('provenance') and a==b
actual=json.loads((H/'ACTUAL-EXPORT-RESULT.json').read_bytes())
left=[]
for pid in actual['processes']:
 try:
  p=psutil.Process(int(pid))
  # PID reuse is not a remaining owned process; require the candidate command.
  if any(str(H).lower() in arg.lower() for arg in p.cmdline()):left.append(int(pid))
 except (psutil.NoSuchProcess,psutil.AccessDenied):pass
assert not left,left
result={'status':'051_PRESERVATION_AND_IMMUTABLE_COMPATIBILITY_PASS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'protected_original_files_unchanged':116,'canonical_engine_files_unchanged':len(pins),'old_previews_verified':verified,
 'candidate_preview_manifest_sha256':fresh['current']['manifest_sha256'],'candidate_preview_reused_on_repeat':True,'saved_job_pointer_unchanged':True,
 'glb_byte_identical_to_installed045':True,'scene_metadata_identical_except_provenance':True,'no_owned_export_processes_remaining':True,
 'native_ui_models_gpu':0,'installed':False,'visual_or_owner_approval':False}
put(H/'COMPATIBILITY-RESULT.json',result)
closure={p.relative_to(H).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and not p.is_relative_to(H/'runtime_context/Data')}
put(H/'SOURCE-CLOSURE.json',closure)
delivery={'status':'051_FIVE_FILE_CANDIDATE_READY_FOR_ROOT_REVIEW_NOT_INSTALLED','install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'diff_sha256':sha(H/'SOURCE.diff'),
 'installer_sha256':sha(H/'install_exact.py'),'closure_sha256':sha(H/'SOURCE-CLOSURE.json'),'actual_export_receipt_sha256':sha(H/'ACTUAL-EXPORT-RESULT.json'),
 'compatibility_receipt_sha256':sha(H/'COMPATIBILITY-RESULT.json'),'changed_files':5,'preserved_original_files':116,
 'frontend_door_checks':7,'portable_door_checks':7,'definition_policy_parity_checks':4,'export_contract_checks':7,'installer_fixture_tests':8,
 'visual_review':'Pending; no UI opened. Geometry and GLB appearance unchanged from045.','promotion':'Requires root exact-plan authorization; no install or Git mutation.'}
put(H/'DELIVERY.json',delivery);print(json.dumps(delivery))
