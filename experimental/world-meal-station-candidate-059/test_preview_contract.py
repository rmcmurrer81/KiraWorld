"""Read-only saved056 compatibility and059 appearance admission; no export/render."""
from pathlib import Path
from unittest.mock import patch
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
sys.path.insert(0,str(K/'tools'))
import world_builder_engine.world_layout_preview as preview
from world_builder_engine.pipeline import latest_preview
import world_builder_engine.layout_package_export as installed
spec=importlib.util.spec_from_file_location('world_builder_engine.layout_package_export059',C/'layout_package_export.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
api.PROJECT=K
plan=read(H/'INSTALL-PLAN.json');source=read(H/'SOURCE-PINS.json')
for rel,row in source.items():assert sha(K/rel)==row['sha256']
for p,d in plan['protected_inputs'].items():assert sha(p)==d
job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';oldpointer=latest_preview(job)
refresh=read(W/'world-observation-trim-056/native-successor-001/installed-preview-001/REFRESH-RESULT.json')
selected={k:refresh['current'][k] for k in ('manifest_path','manifest_sha256')}
saved=preview.verify_preview(selected['manifest_path'],selected['manifest_sha256'])
eligible=installed.inspect_selected_layout(job,selected)
assert eligible['presentation']['setting']=='mars_surface'
try:api.inspect_selected_layout(job,selected)
except api.ExportHeld as exc:assert exc.status=='unsupported_preview'
else:raise AssertionError('Candidate must not export newer furniture from an old-viewer binding')
assert api.RENDERER['viewer.mjs']==sha(C/'viewer.mjs')
class PassedAppearanceGate(Exception):pass
fakejob={'job_dir':job,'job_id':job.name};bound={'manifest_path':str(H/'NOT_CREATED.json'),'manifest_sha256':'a'*64};checks=[]
for name,viewer,held in [('exact059',sha(C/'viewer.mjs'),False),('installed056',sha(K/'tools/world_builder_engine/viewer.mjs'),True),('tampered','0'*64,True)]:
    manifest={'source_mode':'source_bound_original_layout','inputs':{'research_packet':{'path':str(job/'research_packet.json')}},'source_pins':{k:{'sha256':v} for k,v in api.RENDERER.items()}}
    manifest['source_pins']['viewer.mjs']['sha256']=viewer
    with patch.object(api,'read_saved_research',return_value=fakejob),patch.object(api,'verify_preview',return_value=manifest),patch.object(api.bindings,'source_chain',side_effect=PassedAppearanceGate):
        try:api.inspect_selected_layout(job,bound)
        except api.ExportHeld as exc:assert held and exc.status=='unsupported_preview'
        except PassedAppearanceGate:assert not held
        else:raise AssertionError('Expected bounded appearance gate result')
    checks.append({'case':name,'held':held})
pins=read(C/'layout_package_assets/PRODUCER-PINS.json');before=read(K/'tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json')
assert pins['external']==before['external']
for rel,row in pins['files'].items():
    path=C/'layout_package_assets'/rel;assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
assert {r for r in pins['files'] if pins['files'][r]!=before['files'][r]}=={'source/room_dressing_plan.mjs','source/room_dressing_render.mjs','authored_scene.mjs'}
assert latest_preview(job)==oldpointer
for rel,row in source.items():assert sha(K/rel)==row['sha256']
for p,d in plan['protected_inputs'].items():assert sha(p)==d
result={'status':'PASS_INSTALLED056_SAVED_PREVIEW_AND059_APPEARANCE_BOUNDARY',
    'actual_saved056_preview_valid':True,'actual_saved056_installed_export_eligibility':True,
    'candidate059_requires_new_immutable_preview':True,'appearance_tests':checks,
    'producer_source_pins_verified':len(pins['files']),'external_dependencies_unchanged_not_rehashed':True,
    'owner_originals_unchanged':116,'installed_source_files_unchanged':42,'saved_pointer_unchanged':True,
    'new_previews_exports_models_UI_GPU':0,'limits':'059 appearance admission uses a mocked manifest boundary; actual059 immutable preview/export has not been created.056 compatibility is actual read-only source verification.'}
with (H/'PREVIEW-CONTRACT-RESULT.json').open('xb') as f:f.write((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(result))
