"""Independent read-only comparison of actual063 and059 packages, no renderer."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parent
OLD=W/'world-meal-station-candidate-059/actual-001/package';NEW=H/'actual-001/package'
AUDIT=W/'world-installed-observation-export-057-independent-review-001/check_package.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
assert sha(AUDIT)=='4f39cfdc434a608ce2333c17a959676e2cbe03043bb60f1320e32eae34220fb9'
spec=importlib.util.spec_from_file_location('package_audit063',AUDIT);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
checked=audit.check(NEW)
old,ob=audit.glb(OLD/'scene.glb');new,nb=audit.glb(NEW/'scene.glb')
assert ob==nb, 'All actual geometry and image buffer bytes must remain identical to059'
assert len(old['nodes'])==len(new['nodes'])
assert {k for k in set(old)|set(new) if old.get(k)!=new.get(k)}=={'nodes'}
old_s=read(OLD/'scene.json');new_s=read(NEW/'scene.json')
old_col={c['id']:c for c in old_s['colliders']};new_col={c['id']:c for c in new_s['colliders']}
assert all(new_col[k]==v for k,v in old_col.items()),'All prior static and leaf colliders preserved'
added=set(new_col)-set(old_col)
parts=('panel_negative','handle_negative','panel_positive','handle_positive')
expected={f'collider:door_opening_{i}_{part}' for i in range(1,7) for part in parts}
assert added==expected
for key in added:
    collider=new_col[key];door=key.rsplit('_',2)[0].replace('collider:door_','')
    assert collider['owner_node_id']=='node:door_'+door+'_leaf'
    assert collider['proxy']=='attached_hardware_rotated_aabb'
    assert collider['motion']=='kinematic'
changed_nodes=[]
for before,after in zip(old['nodes'],new['nodes'],strict=True):
    if before==after:continue
    assert {k for k in set(before)|set(after) if before.get(k)!=after.get(k)}=={'extras'}
    assert {k for k in set(before['extras'])|set(after['extras']) if before['extras'].get(k)!=after['extras'].get(k)}=={'collider_ids'}
    assert set(before['extras']['collider_ids']).issubset(after['extras']['collider_ids'])
    expected_ids={k for k in added if new_col[k]['owner_node_id']==after['extras']['metadata_node_id']}
    assert set(after['extras']['collider_ids'])-set(before['extras']['collider_ids'])==expected_ids
    assert len(expected_ids)==4
    changed_nodes.append(after['name'])
assert set(changed_nodes)=={f'door_opening_{i}_leaf' for i in range(1,7)}
assert {k for k in old_s if old_s[k]!=new_s[k]}=={'colliders','doors','provenance'}
for before,after in zip(old_s['doors'],new_s['doors'],strict=True):
    assert {k for k in set(before)|set(after) if before.get(k)!=after.get(k)}=={'swing_bounds'}
    a=before['swing_bounds'];b=after['swing_bounds']
    assert all(b['min'][i]<=a['min'][i] and b['max'][i]>=a['max'][i] for i in range(3))
assert {k for k in old_s['provenance'] if old_s['provenance'][k]!=new_s['provenance'][k]}=={'source_digests'}
before=old_s['provenance']['source_digests'];after=new_s['provenance']['source_digests']
assert {k for k in before if before[k]!=after[k]}=={'door_controller'}
assert after['door_controller']==sha(W/'world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs')
meal=next(n for n in new['nodes'] if n.get('name')=='equipment_habitat_meal_station')
assert len(meal['children'])==20 and all('mesh' in new['nodes'][i] for i in meal['children'])
assert meal['extras']['mealStationGeometry']['seatedAvatarInteraction'] is False
report=read(NEW/'ROUNDTRIP.json');prior=read(OLD/'ROUNDTRIP.json')
assert report['scene_bounds']==prior['scene_bounds']
assert report['checks']['door_controller_samples']==prior['checks']['door_controller_samples']
assert report['checks']['airlock_pairs']==prior['checks']['airlock_pairs']
result={'status':'ACTUAL063_COMBINED_GLB_DELTA_PASS','baseline059_glb_sha256':sha(OLD/'scene.glb'),'combined063_glb_sha256':sha(NEW/'scene.glb'),'combined_glb_bytes':(NEW/'scene.glb').stat().st_size,'baseline_counts':prior['counts'],'combined_counts':report['counts'],'all_geometry_and_embedded_image_buffer_bytes_identical_to059':True,'unchanged_materials_textures_lights_transforms_and_meshes':True,'meal_station_meshes_preserved':20,'added_hardware_colliders':len(added),'hardware_colliders_per_door':4,'changed_GLB_nodes_only_six_leaf_collider_links':changed_nodes,'all_prior_semantic_nodes_and_colliders_preserved':True,'only_door_metadata_change_is_enlarged_swing_bounds':True,'all18_export_import_door_poses_unchanged':True,'paired_airlock_policy_unchanged':True,'overall_scene_bounds_unchanged':True,'source_geometry_and_meal_recipe_digests_unchanged':True,'door_controller_digest_bound_to062':True,'independent_saved_package_audit':checked,'renderer_UI_GPU_models_install':0,'visual_or_owner_approval':False,'limit':'Saved GLB transport and metadata fidelity only. No rendered appearance, human scale, seating, comfort or engine-native/VR interaction approval.'}
with (H/'ACTUAL-DELTA-RESULT.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','combined063_glb_sha256','combined_glb_bytes','meal_station_meshes_preserved','added_hardware_colliders')}))
