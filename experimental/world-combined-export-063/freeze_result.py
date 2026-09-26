"""Close and freeze the sole actual063 export; no new rendering or mutation."""
from pathlib import Path
import hashlib,importlib.util,json,sys
import psutil
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parent;F=W/'world-combined-followup-062';K=Path('C:/Users/robmc/Kira')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
pin=lambda p:{'sha256':sha(p),'bytes':Path(p).stat().st_size}
def put(name,data):
    with (H/name).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,indent=2)+'\n')
source=read(F/'SOURCE-PINS.json');protected=read(F/'OWNER-PRESERVATION.local.json');frozen=read(F/'FROZEN-MANIFEST.json')
assert all(pin(K/r)==row for r,row in source.items())
assert all(sha(p)==value for p,value in protected.items())
assert all(pin(F/r)==row for r,row in frozen['files'].items())
derived=read(H/'actual-001/PROTECTED-DERIVED-FILES.local.json')['files'];assert all(sha(p)==value for p,value in derived.items())
supervisor=read(H/'SUPERVISOR.json');assert supervisor['status']=='ISOLATED063_CPU_EXPORT_PASS' and supervisor['remaining_owned_pids']==[]
for row in supervisor['owned_identities']:
    try:assert psutil.Process(row['pid']).create_time()!=row['create_time']
    except psutil.NoSuchProcess:pass
sys.path.insert(0,str(K/'tools'))
from world_builder_engine.pipeline import latest_preview
preview=read(H/'actual-001/PREVIEW-RESULT.json')
assert latest_preview(K/'Data/world_research_jobs/world_research_c391ffbffc7352612392')==preview['previous_pointer']
delta=read(H/'ACTUAL-DELTA-RESULT.json');assert delta['status']=='ACTUAL063_COMBINED_GLB_DELTA_PASS'
report=read(H/'actual-001/package/ROUNDTRIP.json');preflight=read(H/'actual-001/PREFLIGHT.json')
summary={'status':'ISOLATED063_ACTUAL_COMBINED_EXPORT_IMPORT_PASS','source_candidate_frozen_sha256':sha(F/'FROZEN-MANIFEST.json'),'actual_exports':1,'glb':pin(H/'actual-001/package/scene.glb'),'counts':report['counts'],'meal_station_meshes':20,'added_kinematic_hardware_colliders':24,'hardware_colliders_per_door':4,'all_geometry_and_image_buffer_bytes_identical_to059':True,'prior_materials_textures_lights_transforms_and_semantic_nodes_preserved':True,'only_GLTF_node_changes_six_leaf_collider_link_lists':True,'prior_colliders_preserved':True,'door_swing_bounds_expanded_as_intended':True,'airlock_policy_and18_door_pose_samples_preserved':True,'geometry_and_meal_recipe_provenance_unchanged':True,'new_controller_bound_to062':True,'elapsed_seconds':supervisor['elapsed_seconds'],'exit_code':supervisor['exit_code'],'sampled_family_peak_rss_bytes':supervisor['sampled_family_peak_rss_bytes'],'rss_cap_bytes':supervisor['rss_cap_bytes'],'minimum_available_ram_bytes':supervisor['minimum_available_ram_bytes'],'ram_reserve_bytes':supervisor['ram_reserve_bytes'],'deadline_seconds':supervisor['deadline_seconds'],'owned_processes_remaining':0,'owner_originals_unchanged':116,'installed_source_files_unchanged':42,'frozen062_files_unchanged':110,'previous_derived_files_unchanged':len(derived),'selected_pointer_unchanged':True,'source_producer_files_verified':preflight['source_producer_files_verified'],'external_dependency_files_verified':preflight['external_dependencies_verified'],'new_UI_image_render_GPU_models_install':0,'visual_or_owner_approval':False,'remaining':['Independent source/package review','Native visual and traversal inspection','Guarded installation only after review'],'sampling_limit':supervisor['sampling_limit']}
put('TECHNICAL-SUMMARY.json',summary)
put('DEPENDENCIES.json',{'files_relative_to_work':{str(p.relative_to(W)).replace('\\','/'):pin(p) for p in [F/'FROZEN-MANIFEST.json',F/'CANDIDATE-CLOSURE.json',W/'world-installed-observation-export-057-independent-review-001/check_package.py',W/'world-meal-station-candidate-059/run_cpu_export.py',W/'world-meal-station-candidate-059/actual-001/package/scene.glb']},'supervisor_runtime':'Existing Python3.14 with psutil7.2.2; no installation','private_runtime_bindings':'Required for operational rerun; not bundled publicly'})
files={p.relative_to(H).as_posix():pin(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('FROZEN-MANIFEST.json','PUBLIC-BACKUP-MANIFEST.json')}
put('FROZEN-MANIFEST.json',{'schema':'world063-actual-combined-export.v1','files':files,'status':'TECHNICAL_EXPORT_PASS_NOT_INSTALLED','visual_or_owner_approval':False})
public_names=['README.md','TECHNICAL-SUMMARY.json','ACTUAL-DELTA-RESULT.json','DEPENDENCIES.json','prepare_harness.py','run_cpu_export.py','check_actual_delta.py','freeze_result.py','HARNESS-FROM059.diff','HARNESS-PREPARATION.json']
put('PUBLIC-BACKUP-MANIFEST.json',{'schema':'world063-public-technical-evidence.v1','destination_prefix':'experimental/world-combined-export-063/','files':{name:pin(H/name) for name in public_names},'excluded_scopes':['actual-001/','runtime_context/','SUPERVISOR.json','FROZEN-MANIFEST.json'],'private_frozen_manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'raw_owner_state_or_absolute_path_inventory_included':False,'resource_process_logs_included':False,'glb_included':False,'visual_or_owner_approval':False})
print(json.dumps({'status':'CLOSED_AND_FROZEN','frozen_manifest':pin(H/'FROZEN-MANIFEST.json'),'public_manifest':pin(H/'PUBLIC-BACKUP-MANIFEST.json'),'public_files':len(public_names),'summary':pin(H/'TECHNICAL-SUMMARY.json')}))
