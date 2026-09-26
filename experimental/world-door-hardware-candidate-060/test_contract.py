"""Read-only source, original-state and preview/export boundary verification."""
from pathlib import Path
from unittest.mock import patch
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parent;K=Path('C:/Users/robmc/Kira');C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
sys.path.insert(0,str(K/'tools'))
from world_builder_engine.pipeline import latest_preview
import world_builder_engine.layout_package_export as installed
spec=importlib.util.spec_from_file_location('world_builder_engine.layout_package_export060',C/'layout_package_export.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api);api.PROJECT=K
source=read(H/'SOURCE-PINS.json');protected=read(H/'OWNER-PRESERVATION.local.json')
assert len(source)==42 and len(protected)==116
for rel,row in source.items():assert sha(K/rel)==row['sha256']
for p,d in protected.items():assert sha(p)==d
job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';pointer=latest_preview(job)
refresh=read(W/'world-observation-trim-056/native-successor-001/installed-preview-001/REFRESH-RESULT.json')
binding={k:refresh['current'][k] for k in ('manifest_path','manifest_sha256')}
assert installed.inspect_selected_layout(job,binding)['presentation']['setting']=='mars_surface'
try:api.inspect_selected_layout(job,binding)
except api.ExportHeld as exc:assert exc.status=='unsupported_preview'
else:raise AssertionError('Old preview must not silently export newer collision behavior')
class PassedAppearanceGate(Exception):pass
checks=[]
for name,pin,held in [('exact060',sha(C/'walk_controller.mjs'),False),('installed056',sha(K/'tools/world_builder_engine/walk_controller.mjs'),True),('tampered','0'*64,True)]:
 manifest={'source_mode':'source_bound_original_layout','inputs':{'research_packet':{'path':str(job/'research_packet.json')}},'source_pins':{k:{'sha256':v} for k,v in api.RENDERER.items()}}
 manifest['source_pins']['walk_controller.mjs']['sha256']=pin
 with patch.object(api,'read_saved_research',return_value={'job_dir':job}),patch.object(api,'verify_preview',return_value=manifest),patch.object(api.bindings,'source_chain',side_effect=PassedAppearanceGate):
  try:api.inspect_selected_layout(job,{'manifest_path':str(H/'NOT_CREATED'),'manifest_sha256':'a'*64})
  except api.ExportHeld as exc:assert held and exc.status=='unsupported_preview'
  except PassedAppearanceGate:assert not held
  else:raise AssertionError('Unexpected admission result')
 checks.append({'case':name,'held':held})
pins=read(C/'layout_package_assets/PRODUCER-PINS.json');prior=read(K/'tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json')
assert pins['external']==prior['external']
for rel,row in pins['files'].items():
 p=C/'layout_package_assets'/rel;assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert {r for r in pins['files'] if pins['files'][r]!=prior['files'][r]}=={'source/walk_controller.mjs','source/scene_metadata.mjs'}
assert api.RENDERER['walk_controller.mjs']==sha(C/'walk_controller.mjs')
assert latest_preview(job)==pointer
assert all(sha(K/rel)==row['sha256'] for rel,row in source.items())
assert all(sha(p)==d for p,d in protected.items())
result={'status':'PASS_READ_ONLY_PREVIEW_AND_PRESERVATION','actual_saved056_export_eligible':True,'candidate_requires_new_immutable_preview':True,'admission_cases':checks,'producer_pins_verified':len(pins['files']),'owner_files_unchanged':116,'canonical_closure_unchanged':42,'saved_pointer_unchanged':True,'external_dependencies_unchanged_not_rehashed':True,'new_previews_exports_models_UI_GPU':0,'limits':'Exact new-controller admission uses a mocked boundary; no new immutable preview or GLB was created.'}
(H/'CONTRACT-RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
