from pathlib import Path
import hashlib,importlib.util,json,os,sys
from unittest.mock import patch
H=Path(__file__).resolve().parent;K=Path(os.environ.get('KIRA_TEST_ROOT','@kira_root'));C=H/'candidate/tools/world_builder_engine'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
spec=importlib.util.spec_from_file_location('world_builder_engine.layout_package_export042',C/'layout_package_export.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert api.RENDERER['viewer.mjs']==sha(C/'viewer.mjs')
class PassedAppearanceGate(Exception):pass
job={'job_dir':K/'Data/world_research_jobs/world_research_fixture','job_id':'world_research_fixture'}
bound={'manifest_path':str(H/'not_created_manifest.json'),'manifest_sha256':'a'*64}
checks=[]
for case,viewer,held in [('new042',sha(C/'viewer.mjs'),False),('old041',sha(K/'tools/world_builder_engine/viewer.mjs'),True),('changed_viewer','0'*64,True)]:
 manifest={'source_mode':'source_bound_original_layout','inputs':{'research_packet':{'path':str(job['job_dir']/'research_packet.json')}},'source_pins':{k:{'sha256':v} for k,v in api.RENDERER.items()}}
 manifest['source_pins']['viewer.mjs']['sha256']=viewer
 with patch.object(api,'read_saved_research',return_value=job),patch.object(api,'verify_preview',return_value=manifest),patch.object(api.bindings,'source_chain',side_effect=PassedAppearanceGate):
  try:api.inspect_selected_layout(job['job_dir'],bound)
  except api.ExportHeld as exc:assert held and exc.status=='unsupported_preview'
  except PassedAppearanceGate:assert not held
  else:raise AssertionError('Expected bounded gate result')
 checks.append({'case':case,'appearance_held':held})
result={'status':'NEW_APPEARANCE_PIN_ACCEPTED_OLD_OR_CHANGED_APPEARANCE_HELD','checks':checks,'scope':'Mocks saved-job and immutable verification, tests appearance dispatch only; no created preview or real export.','owner_data_writes':0,'native_ui_models_gpu':0}
with (H/'PREVIEW-CONTRACT-RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
