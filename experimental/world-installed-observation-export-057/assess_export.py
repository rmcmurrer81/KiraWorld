"""Inspect actual imported package and compare exact mesh data with prior054."""
from pathlib import Path
import hashlib,json,struct
H=Path(__file__).resolve().parent;W=H.parent;N=H/'actual-001/package';B=W/'world-observation-setting-054/actual-001/package'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadglb(path):
 raw=path.read_bytes();magic,version,size=struct.unpack_from('<III',raw);assert magic==0x46546c67 and version==2 and size==len(raw)
 length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a;g=json.loads(raw[20:20+length])
 n,t=struct.unpack_from('<II',raw,20+length);assert t==0x004e4942;data=raw[28+length:28+length+n];assert len(data)==n
 return g,data
def accessor(g,data,i):
 a=g['accessors'][i];assert 'sparse' not in a;v=g['bufferViews'][a['bufferView']]
 size={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a['componentType']]*{'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
 start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',size)
 return b''.join(data[start+k*stride:start+k*stride+size] for k in range(a['count']))
def view(g,data,i):
 v=g['bufferViews'][i];start=v.get('byteOffset',0);return data[start:start+v['byteLength']]
a,ad=loadglb(B/'scene.glb');b,bd=loadglb(N/'scene.glb')
assert len(a['nodes'])==len(b['nodes']) and [n.get('name') for n in a['nodes']]==[n.get('name') for n in b['nodes']]
assert a['materials']==b['materials'] and a.get('textures')==b.get('textures')
assert len(a['images'])==len(b['images'])==70
assert all(view(a,ad,x['bufferView'])==view(b,bd,y['bufferView']) for x,y in zip(a['images'],b['images']))
changed=[]
for old,new in zip(a['nodes'],b['nodes']):
 props=[k for k in set(old)|set(new) if k!='mesh' and old.get(k)!=new.get(k)]
 attributes=[]
 if 'mesh' in old:
  op=a['meshes'][old['mesh']]['primitives'];np=b['meshes'][new['mesh']]['primitives'];assert len(op)==len(np)
  for x,y in zip(op,np):
   assert x.get('material')==y.get('material') and x.get('mode')==y.get('mode') and set(x['attributes'])==set(y['attributes'])
   assert accessor(a,ad,x['indices'])==accessor(b,bd,y['indices'])
   for key in x['attributes']:
    if accessor(a,ad,x['attributes'][key])!=accessor(b,bd,y['attributes'][key]):attributes.append(key)
 if props or attributes:changed.append({'name':old.get('name'),'node_fields':props,'geometry_attributes':attributes})
expected={f'observation_east_0_reveal_{orient}_{edge}' for orient in ('vertical','horizontal') for edge in (-1,1)}
assert {r['name'] for r in changed}==expected
assert all(r['node_fields']==['matrix'] and r['geometry_attributes']==['POSITION'] for r in changed)
assert (B/'scene.json').read_bytes()==(N/'scene.json').read_bytes()
report=json.loads((N/'ROUNDTRIP.json').read_bytes());prior=json.loads((B/'ROUNDTRIP.json').read_bytes());package=json.loads((N/'manifest.json').read_bytes())
assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS' and report['counts']==prior['counts']
assert report['checks']==prior['checks'] and report['scene_bounds']==prior['scene_bounds']
assert report['presentation_setting']==prior['presentation_setting']==package['presentation_setting']
assert report['glb_sha256']==sha(N/'scene.glb') and report['checks']['importer_door_poses']==18
supervisor=json.loads((H/'SUPERVISOR.json').read_bytes());assert supervisor['remaining_owned_pids']==[] and supervisor['status']=='INSTALLED056_CPU_EXPORT_PASS'
result={'status':'INSTALLED056_GLB_TRANSPORT_AND_TRIM_DATA_PASS','glb_sha256':sha(N/'scene.glb'),'glb_bytes':(N/'scene.glb').stat().st_size,
 'actual_importer_counts':report['counts'],'actual_importer_checks':report['checks'],'presentation':package['presentation_setting'],
 'relative_to_prior054':{'changed_nodes':changed,'all_other_mesh_attributes_indices_transforms_preserved':True,'material_parameters_and70_embedded_images_exact':True,
 'scene_metadata_exact':True,'colliders_room_bounds_door_and_airlock_metadata_exact':True,'old054_glb_sha256':sha(B/'scene.glb')},
 'source_api':'Installed056 export_saved_layout_package with explicit refreshed selected-project preview binding',
 'no_canonical_changes':True,'raw_source_brief_exported':False,'pressure_or_engine_runtime_claim':False,
 'limits':['Importer transport and metadata checks do not execute engine-native collision, pressure simulation or VR.','This export was not opened in native UI and is not owner visual approval.','The procedural appearance and root narrow trim review limits remain.']}
with (H/'ASSESSMENT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'glb_sha256':result['glb_sha256'],'bytes':result['glb_bytes'],'only_changed_meshes':len(changed),'unchanged_colliders':report['counts']['colliders'],'checked_door_poses':18}))
