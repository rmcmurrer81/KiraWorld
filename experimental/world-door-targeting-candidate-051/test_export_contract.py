"""Real producer pins plus isolated appearance dispatch: no world/model writes."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,sys,tempfile
from unittest.mock import patch
H=Path(__file__).resolve().parent;K=Path(os.environ.get('KIRA_TEST_ROOT','@kira_root'));C=H/'candidate/tools/world_builder_engine'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
spec=importlib.util.spec_from_file_location('world_builder_engine.layout_package_export051',C/'layout_package_export.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for name in ('viewer.mjs','walk_controller.mjs'):assert api.RENDERER[name]==sha(C/name)
class PassedAppearanceGate(Exception):pass
job={'job_dir':K/'Data/world_research_jobs/world_research_fixture','job_id':'world_research_fixture'}
bound={'manifest_path':str(H/'not_created_manifest.json'),'manifest_sha256':'a'*64}
for case,changes,held in [('new051',{},False),
 ('old_viewer',{'viewer.mjs':sha(H/'preimages/tools/world_builder_engine/viewer.mjs')},True),
 ('old_controller',{'walk_controller.mjs':sha(H/'preimages/tools/world_builder_engine/walk_controller.mjs')},True),
 ('changed_controller',{'walk_controller.mjs':'0'*64},True)]:
 manifest={'source_mode':'source_bound_original_layout','inputs':{'research_packet':{'path':str(job['job_dir']/'research_packet.json')}},'source_pins':{k:{'sha256':v} for k,v in {**api.RENDERER,**changes}.items()}}
 with patch.object(api,'read_saved_research',return_value=job),patch.object(api,'verify_preview',return_value=manifest),patch.object(api.bindings,'source_chain',side_effect=PassedAppearanceGate):
  try:api.inspect_selected_layout(job['job_dir'],bound)
  except api.ExportHeld as exc:assert held and exc.status=='unsupported_preview'
  except PassedAppearanceGate:assert not held
  else:raise AssertionError('Expected bounded gate result')
 checks.append({'case':case,'held':held})
dependencies=api.verify_dependencies();assert dependencies['pins']['files']['source/walk_controller.mjs']['sha256']==sha(C/'layout_package_assets/source/walk_controller.mjs')
checks.append({'case':'real_current_producer_and_external_dependency_pins','held':False})
with tempfile.TemporaryDirectory(prefix='world051-producer-') as temp:
 assets=Path(temp)/'assets';shutil.copytree(C/'layout_package_assets',assets)
 controller=assets/'source/walk_controller.mjs';original=controller.read_bytes()
 with patch.object(api,'ASSETS',assets):
  for name,raw in [('modified',original+b'\n// changed'),('missing',None)]:
   if raw is None:controller.unlink()
   else:controller.write_bytes(raw)
   try:api.verify_dependencies()
   except api.ExportHeld as exc:assert exc.status=='producer_changed'
   else:raise AssertionError('Tampered producer accepted')
   checks.append({'case':name+'_portable_controller','held':True})
result={'status':'051_EXACT_PREVIEW_AND_PRODUCER_PINS_PASS','checks':checks,'check_count':len(checks),
 'scope':'Appearance dispatch uses mocked source verification; producer and external dependency hashes are real. Actual preview/export is separate.','owner_and_installed_writes':0,'ui_gpu_models':0}
with (H/'EXPORT-CONTRACT-RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
