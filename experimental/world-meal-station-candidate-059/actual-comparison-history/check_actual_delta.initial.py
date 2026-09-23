"""Read-only actual059/057 GLB comparison; no rendering or source reconstruction."""
from pathlib import Path
import hashlib,importlib.util,json

H=Path(__file__).resolve().parent;W=H.parent
AUDIT=W/'world-installed-observation-export-057-independent-review-001/check_package.py'
assert hashlib.sha256(AUDIT.read_bytes()).hexdigest()=='4f39cfdc434a608ce2333c17a959676e2cbe03043bb60f1320e32eae34220fb9'
spec=importlib.util.spec_from_file_location('package_audit057',AUDIT);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
OLD=W/'world-installed-observation-export-057/actual-001/package';NEW=H/'actual-001/package'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean_extras(extras):return {k:v for k,v in extras.items() if k!='export_id'}
def mesh_signature(data,buffer,index):
 mesh=data['meshes'][index];primitives=[]
 for p in mesh['primitives']:
  row={k:v for k,v in p.items() if k not in ('indices','attributes')}
  row['indices']=hashlib.sha256(audit.attribute(data,buffer,p['indices'])).hexdigest()
  row['attributes']={k:hashlib.sha256(audit.attribute(data,buffer,v)).hexdigest() for k,v in p['attributes'].items()}
  primitives.append(row)
 return primitives
def tree(data,buffer,index,omit_meal=False):
 node=data['nodes'][index]
 if omit_meal and node.get('name')=='equipment_habitat_meal_station':return None
 row={k:v for k,v in node.items() if k not in ('children','mesh','extras')}
 if row.get('name')==node.get('extras',{}).get('export_id'):row.pop('name')
 row['extras']=clean_extras(node.get('extras',{}))
 if 'mesh' in node:row['mesh']=mesh_signature(data,buffer,node['mesh'])
 row['children']=[value for child in node.get('children',[]) if (value:=tree(data,buffer,child,omit_meal)) is not None]
 return row
def scene_signature(data,buffer,omit_meal=False):
 return [{**{k:v for k,v in scene.items() if k not in ('nodes','extras')},'extras':clean_extras(scene.get('extras',{})),
          'nodes':[tree(data,buffer,i,omit_meal) for i in scene['nodes']]} for scene in data['scenes']]
def main():
 audit_result=audit.check(NEW)
 old,ob=audit.glb(OLD/'scene.glb');new,nb=audit.glb(NEW/'scene.glb')
 assert old['materials']==new['materials'] and old['textures']==new['textures']
 assert old.get('samplers')==new.get('samplers') and old.get('extensions')==new.get('extensions')
 assert len(old['images'])==len(new['images'])==70
 assert all(audit.view(old,ob,a['bufferView'])==audit.view(new,nb,b['bufferView']) for a,b in zip(old['images'],new['images']))
 # Export IDs/resource indices shift after insertion. Compare actual attributes,
 # transforms, hierarchy, stable names, semantic extras and material references.
 assert scene_signature(old,ob)==scene_signature(new,nb,True),'Unexpected pre-existing GLB scene change'
 meal=[(i,n) for i,n in enumerate(new['nodes']) if n.get('name')=='equipment_habitat_meal_station']
 assert len(meal)==1
 meal_i,meal_node=meal[0];children=meal_node['children']
 assert len(children)==20 and all('mesh' in new['nodes'][i] for i in children)
 assert meal_node['extras']['mealStationGeometry']['seatedAvatarInteraction'] is False
 old_s=json.loads((OLD/'scene.json').read_bytes());new_s=json.loads((NEW/'scene.json').read_bytes())
 new_nodes={x['id']:x for x in new_s['nodes']};old_nodes={x['id']:x for x in old_s['nodes']}
 new_col={x['id']:x for x in new_s['colliders']};old_col={x['id']:x for x in old_s['colliders']}
 assert set(new_nodes)-set(old_nodes)=={'node:equipment_habitat_meal_station'}
 assert set(new_col)-set(old_col)=={'collider:equipment_habitat_meal_station'}
 assert all(new_nodes[k]==v for k,v in old_nodes.items())
 assert all(new_col[k]==v for k,v in old_col.items())
 for key in ('rooms','doors','airlock_pairs','navigation','coordinate_system','capabilities','scene_id','limitations'):
  assert old_s[key]==new_s[key],key
 # Provenance legitimately changes its dressing recipe digest; geometry/controller stay exact.
 old_p=old_s['provenance'];new_p=new_s['provenance']
 differences={k for k in set(old_p)|set(new_p) if old_p.get(k)!=new_p.get(k)}
 assert differences=={'source_digests'}
 a=old_p['source_digests'];b=new_p['source_digests']
 assert {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}=={'dressing_recipe'}
 report=json.loads((NEW/'ROUNDTRIP.json').read_bytes());before=json.loads((OLD/'ROUNDTRIP.json').read_bytes())
 assert report['scene_bounds']==before['scene_bounds']
 assert report['checks']['door_controller_samples']==before['checks']['door_controller_samples']
 result={'status':'ACTUAL059_GLB_DELTA_PASS','baseline_glb_sha256':sha(OLD/'scene.glb'),'candidate_glb_sha256':sha(NEW/'scene.glb'),
  'baseline_counts':before['counts'],'candidate_counts':report['counts'],'added_mesh_nodes':20,'added_static_assembly_nodes':1,
  'new_semantic_node_id':'node:equipment_habitat_meal_station','new_collider_id':'collider:equipment_habitat_meal_station',
  'all_previous_scene_hierarchy_transforms_geometry_attributes_and_semantic_extras_exact':True,
  'all102_materials_70_embedded_pngs_texture_parameters_and_lights_exact':True,
  'all141_previous_semantic_nodes_134_colliders_rooms_navigation_and_doors_exact':True,
  'overall_scene_bounds_unchanged':True,'all18_door_pose_samples_unchanged':True,
  'export_identifier_reindexing_ignored':True,'dressing_recipe_digest_changed_as_expected':True,
  'read_only_independent_package_audit':audit_result,'visual_or_owner_approval':False,
  'limit':'GLB structure/attributes and importer checks establish transport fidelity, not appearance in a renderer, seating interaction or realism.'}
 with (H/'ACTUAL-DELTA-RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ('status','candidate_glb_sha256','added_mesh_nodes','overall_scene_bounds_unchanged')}))
if __name__=='__main__':main()
