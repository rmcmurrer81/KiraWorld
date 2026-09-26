"""Read-only combined preview admission and source preservation; never export."""
from pathlib import Path
from unittest.mock import patch
import hashlib, importlib.util, json, sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parent;K=Path('C:/Users/robmc/Kira');C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
sys.path.insert(0,str(K/'tools'))
from world_builder_engine.pipeline import latest_preview
from world_builder_engine.world_layout_preview import PreviewError
import world_builder_engine.layout_package_export as installed
spec=importlib.util.spec_from_file_location('world_builder_engine.layout_package_export062',C/'layout_package_export.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api);api.PROJECT=K
source=read(H/'SOURCE-PINS.json');protected=read(H/'OWNER-PRESERVATION.local.json');closure=read(H/'CANDIDATE-CLOSURE.json')
def preserved():
    assert len(source)==42 and len(protected)==116 and len(closure)==42
    assert all(sha(K/r)==v['sha256'] for r,v in source.items())
    assert all(sha(H/'preimages'/r)==v['sha256'] for r,v in source.items())
    assert all(sha(H/'candidate'/r)==v['sha256'] for r,v in closure.items())
    assert all(sha(p)==v for p,v in protected.items())
preserved()
job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';pointer=latest_preview(job)
refresh=read(W/'world-observation-trim-056/native-successor-001/installed-preview-001/REFRESH-RESULT.json')
selected={k:refresh['current'][k] for k in ('manifest_path','manifest_sha256')}
assert installed.inspect_selected_layout(job,selected)['presentation']['setting']=='mars_surface'
actual_cases=[]
for name,binding in [('installed056',selected),('separate059',read(W/'world-meal-station-candidate-059/ACTUAL-DELIVERY.json')['immutable_preview'])]:
    selected_binding={k:binding[k] for k in ('manifest_path','manifest_sha256')}
    try:api.inspect_selected_layout(job,selected_binding)
    except api.ExportHeld as exc:
        assert name=='installed056' and exc.status=='unsupported_preview';reason=exc.status
    except PreviewError as exc:
        assert name=='separate059' and str(exc)=='Serve only an isolated candidate build';reason='foreign_preview_scope'
    else:raise AssertionError('Old saved preview may not be relabelled as combined062')
    actual_cases.append({'case':name,'held':reason})

class PassedAppearanceGate(Exception):pass
cases=[]
for view_name,view_pin in [('combined',sha(C/'viewer.mjs')),('installed',sha(K/'tools/world_builder_engine/viewer.mjs')),('tampered','0'*64)]:
    for walk_name,walk_pin in [('combined',sha(C/'walk_controller.mjs')),('installed',sha(K/'tools/world_builder_engine/walk_controller.mjs')),('tampered','1'*64)]:
        held=not(view_name=='combined' and walk_name=='combined')
        manifest={'source_mode':'source_bound_original_layout','inputs':{'research_packet':{'path':str(job/'research_packet.json')}},'source_pins':{k:{'sha256':v} for k,v in api.RENDERER.items()}}
        manifest['source_pins']['viewer.mjs']['sha256']=view_pin;manifest['source_pins']['walk_controller.mjs']['sha256']=walk_pin
        with patch.object(api,'read_saved_research',return_value={'job_dir':job}),patch.object(api,'verify_preview',return_value=manifest),patch.object(api.bindings,'source_chain',side_effect=PassedAppearanceGate):
            try:api.inspect_selected_layout(job,{'manifest_path':str(H/'NOT_CREATED.json'),'manifest_sha256':'a'*64})
            except api.ExportHeld as exc:assert held and exc.status=='unsupported_preview'
            except PassedAppearanceGate:assert not held
            else:raise AssertionError('Unexpected combined admission result')
        cases.append({'viewer':view_name,'walker':walk_name,'held':held})

pins=read(C/'layout_package_assets/PRODUCER-PINS.json');prior=read(K/'tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json')
assert pins['external']==prior['external']
assert set(pins['files'])==set(prior['files'])
for rel,row in pins['files'].items():
    path=C/'layout_package_assets'/rel;assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
expected={'authored_scene.mjs','source/room_dressing_plan.mjs','source/room_dressing_render.mjs','source/scene_metadata.mjs','source/walk_controller.mjs'}
assert {r for r in pins['files'] if pins['files'][r]!=prior['files'][r]}==expected
assert api.RENDERER['viewer.mjs']==sha(C/'viewer.mjs') and api.RENDERER['walk_controller.mjs']==sha(C/'walk_controller.mjs')
assert {r for r in api.RENDERER if api.RENDERER[r]!=installed.RENDERER[r]}=={'viewer.mjs','walk_controller.mjs'}
# A verified preview must never be silently repaired or rebound by this check.
assert latest_preview(job)==pointer;preserved()
result={'status':'PASS_COMBINED_READ_ONLY_ADMISSION_AND_PRESERVATION','installed056_saved_preview_still_eligible':True,'actual_old_previews_held':actual_cases,'combined_admission_cases':cases,'producer_files_verified':len(pins['files']),'producer_changes':sorted(expected),'external_dependencies_unchanged_not_rehashed':True,'owner_originals_unchanged':116,'canonical_closure_unchanged':42,'candidate_closure_verified':42,'selected_job_pointer_unchanged':True,'new_previews_exports_models_UI_GPU_install':0,'limits':'Combined exact-manifest admission is an isolated mocked boundary. No new preview, GLB, renderer, installation or visual approval is implied.'}
with (H/'CONTRACT-RESULT.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
