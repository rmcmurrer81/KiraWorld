from pathlib import Path
import datetime,hashlib,json,psutil

H=Path(__file__).resolve().parent;E=Path('@kira_root/tools/world_builder_engine')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes())
assert sha(H/'INSTALL-PLAN.json')=='8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71'
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
source=json.loads((H/'SOURCE-PINS.json').read_bytes());assert all(sha(E/p)==v for p,v in source.items())
for row in plan['files']:
    assert sha(row['target'])==sha(row['preimage'])==row['before_sha256']
    assert sha(row['after']['path'])==row['after']['sha256']
for p,pin in json.loads((H/'CANDIDATE-CLOSURE.json').read_bytes()).items():assert sha(H/'candidate'/p)==pin['sha256']
tests=json.loads((H/'TEST-RESULT.json').read_bytes());saved=json.loads((H/'TEST-RESULT-SAVED.json').read_bytes())
export=json.loads((H/'ACTUAL-EXPORT-RESULT.json').read_bytes());render=json.loads((H/'CPU-RENDER-RESULT.json').read_bytes())
assert len(tests['shapes'])==4 and len(saved['shapes'])==1
assert export['canonical_unchanged'] and export['protected_original_files_unchanged']==116
assert render['returncode']==0 and render['source_glb_unchanged']
assert not [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='blender.exe']
package=H/'actual-001/package';manifest=json.loads((package/'manifest.json').read_bytes())
for p,pin in manifest['files'].items():assert sha(package/p)==pin['sha256']
png=H/'cpu-review-001/galley-review.png';assert sha(png)==render['png_sha256']
before=json.loads((H.parent/'world-bunk-detail-042/installed-mars-001/package/ROUNDTRIP.json').read_bytes())
put(H/'BEFORE-AFTER.json',{'contract':'original_galley_static_geometry_045','same_assembly_size_m':[1.42,1.74,.68],
    'before':{'galley_meshes':15,'sink':'flat_dark_rectangle_over_solid_counter','package_counts':before['counts']},
    'after':{'galley_meshes':73,'galley_triangles':1560,'sink_clear_opening_m':[.436,.396],'basin_floor_y_m':.689,'counter_y_m':.89,'basin_depth_m':.201,'package_counts':export['counts']},
    'all_other_equipment_signatures_equal':15,'unchanged_collider_and_footprint':True,'unchanged_routes':6,'unchanged_doors':6,
    'source_role':'habitat','added_dining_furniture':False,'appliance_simulation':False,'dimensions_are_model_scale_not_real_spacecraft_measurements':True})
put(H/'AGENT-ARTIFACT-REVIEW.json',{'status':'LIMITED_STATIC_GEOMETRY_IMPROVEMENT_OBSERVED','png_sha256':sha(png),
    'observed':['Full cabinet within frame','Visible recessed basin','Clear preparation surface','Separate upper pantry and warming appliance with window/handle/dials','Distinct lower cupboard/drawers/closed food-compartment fronts'],
    'limits':['Faucet partly obscured by pantry from this review angle','Procedural materials','Lighting and raised camera differ from native preview','Only static appliance geometry, no utility simulation'],
    'root_review':'pending_separate_receipt','owner_approval':False,'whole_habitat_realism_approval':False})
files=['INSTALL-PLAN.json','CANDIDATE-CLOSURE.json','COMBINED-CHANGES.patch','TEST-RESULT.json','TEST-RESULT-SAVED.json','ACTUAL-EXPORT-RESULT.json','CPU-RENDER-RESULT.json','BEFORE-AFTER.json','AGENT-ARTIFACT-REVIEW.json','README.md']
put(H/'DELIVERY.json',{'status':'045_ISOLATED_REAL_GALLEY_GEOMETRY_READY_FOR_ROOT_REVIEW','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
    'files':{p:sha(H/p) for p in files},'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'candidate_files_changed':5,
    'geometry_cases':5,'actual_cpu_exports':1,'cpu_renders':1,'glb_sha256':export['glb_sha256'],'png_sha256':sha(png),
    'protected_originals_unchanged':116,'installed_source_files_unchanged':len(source),'canonical_install':False,'native_ui_models_gpu':0,
    'appliances_operational':False,'owner_approval':False,'pending':['Root artifact review','Exact root install authorization if appropriate','Native preview/owner review']})
print(json.dumps({'status':'045_FROZEN_READY','delivery_sha256':sha(H/'DELIVERY.json'),'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'protected_originals_unchanged':116,'installed_source_files_unchanged':len(source)}))
