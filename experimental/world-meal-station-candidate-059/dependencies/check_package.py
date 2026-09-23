"""Read-only, standard-library audit of a saved authored package; no renderer required."""
from pathlib import Path
import argparse, hashlib, json, struct

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def glb(path):
    raw=path.read_bytes()
    assert struct.unpack_from('<III',raw)==(0x46546C67,2,len(raw))
    chunks=[]; offset=12
    while offset<len(raw):
        size,kind=struct.unpack_from('<II',raw,offset); offset+=8
        assert size%4==0 and offset+size<=len(raw)
        chunks.append((kind,raw[offset:offset+size])); offset+=size
    assert [k for k,_ in chunks]==[0x4E4F534A,0x004E4942]
    data=json.loads(chunks[0][1]); buffer=chunks[1][1]
    assert len(data['buffers'])==1 and 'uri' not in data['buffers'][0]
    assert 0<=len(buffer)-data['buffers'][0]['byteLength']<=3
    for view in data['bufferViews']:
        assert view['buffer']==0 and view.get('byteOffset',0)>=0
        assert view.get('byteOffset',0)+view['byteLength']<=len(buffer)
    for node in data['nodes']:
        assert all(0<=i<len(data['nodes']) for i in node.get('children',[]))
    return data,buffer

def view(data,buffer,i):
    v=data['bufferViews'][i]; start=v.get('byteOffset',0)
    return buffer[start:start+v['byteLength']]

def attribute(data,buffer,i):
    a=data['accessors'][i]; assert 'sparse' not in a
    v=data['bufferViews'][a['bufferView']]
    width={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a['componentType']]
    size=width*{'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT2':4,'MAT3':9,'MAT4':16}[a['type']]
    stride=v.get('byteStride',size); start=a.get('byteOffset',0)
    assert a['count']>0 and start>=0 and stride>=size
    b=view(data,buffer,a['bufferView'])
    assert start+(a['count']-1)*stride+size<=len(b)
    return b''.join(b[start+j*stride:start+j*stride+size] for j in range(a['count']))

def check(package, prior=None):
    m=json.loads((package/'manifest.json').read_bytes())
    assert set(m['files'])=={'README.txt','ROUNDTRIP.json','scene.glb','scene.json'}
    for name,row in m['files'].items():
        raw=(package/name).read_bytes()
        assert digest(raw)==row['sha256'] and len(raw)==row['bytes'],name
    unsigned={k:v for k,v in m.items() if k!='receipt_sha256'}
    seal=digest(json.dumps(unsigned,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
    assert seal==m['receipt_sha256']
    report=json.loads((package/'ROUNDTRIP.json').read_bytes())
    scene=json.loads((package/'scene.json').read_bytes())
    assert report['glb_sha256']==digest((package/'scene.glb').read_bytes())
    assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS'
    data,buffer=glb(package/'scene.glb')
    # glTF shares mesh resources; the importer reports instantiated Mesh nodes.
    assert sum('mesh' in node for node in data['nodes'])==report['counts']['meshes']
    assert len(data['materials'])==report['counts']['materials']
    assert len(data['images'])==report['counts']['embedded_pngs']==70
    dimensions=[]
    for img in data['images']:
        assert 'uri' not in img and img['mimeType']=='image/png'
        png=view(data,buffer,img['bufferView'])
        assert png[:8]==b'\x89PNG\r\n\x1a\n' and png[12:16]==b'IHDR'
        w,h=struct.unpack_from('>II',png,16); assert 0<w<=4096 and 0<h<=4096
        dimensions.append([w,h])
    attrs=0
    for mesh in data['meshes']:
        for p in mesh['primitives']:
            for a in [p['indices'],*p['attributes'].values()]:
                attribute(data,buffer,a); attrs+=1
    nodes={x['id']:x for x in scene['nodes']}; assert len(nodes)==len(scene['nodes'])
    for collider in scene['colliders']:
        assert collider['owner_node_id'] in nodes,collider['id']
        b=collider['bounds']; assert all(x<y for x,y in zip(b['min'],b['max']))
    assert len(scene['doors'])==6 and len(scene['airlock_pairs'])==1
    assert all(d['id'] in {x['id'] for x in scene['doors']} for pair in scene['airlock_pairs'] for d in [{'id':i} for i in pair['door_ids']])
    assert scene['airlock_pairs']==m['airlock_pair_policy']==report['checks']['airlock_pairs']
    assert m['presentation_setting']==report['presentation_setting']
    for flag in ('engine_native_interaction','engine_native_collision','pressure_simulation','vr_runtime','visual_or_owner_approval'):
        assert m['capabilities'][flag] is False
    result={'status':'READ_ONLY_PACKAGE_AUDIT_PASS','glb_sha256':report['glb_sha256'],
        'counts':report['counts'],'checked_accessors':attrs,'embedded_png_dimensions':dimensions,
        'manifest_seal_and_files_verified':True,'external_buffer_or_image_URIs':0,'all_collider_owner_nodes_present':True}
    if prior:
        old,ob=glb(prior/'scene.glb'); changes=[]
        assert old['materials']==data['materials'] and old['textures']==data['textures']
        assert old.get('extensions')==data.get('extensions')
        assert len(old['nodes'])==len(data['nodes'])
        assert all(view(old,ob,a['bufferView'])==view(data,buffer,b['bufferView']) for a,b in zip(old['images'],data['images']))
        for a,b in zip(old['nodes'],data['nodes']):
            assert a.get('name')==b.get('name')
            props=sorted(k for k in set(a)|set(b) if k!='mesh' and a.get(k)!=b.get(k)); changed=[]
            if 'mesh' in a:
                ap=old['meshes'][a['mesh']]['primitives']; bp=data['meshes'][b['mesh']]['primitives']; assert len(ap)==len(bp)
                for x,y in zip(ap,bp):
                    assert x.get('material')==y.get('material') and x.get('mode')==y.get('mode')
                    assert set(x['attributes'])==set(y['attributes'])
                    assert attribute(old,ob,x['indices'])==attribute(data,buffer,y['indices'])
                    changed += [k for k in x['attributes'] if attribute(old,ob,x['attributes'][k])!=attribute(data,buffer,y['attributes'][k])]
            if props or changed: changes.append({'name':a['name'],'node_fields':props,'attributes':changed})
        expected={f'observation_east_0_reveal_{axis}_{side}' for axis in ('horizontal','vertical') for side in (-1,1)}
        assert {c['name'] for c in changes}==expected
        assert all(c['node_fields']==['matrix'] and c['attributes']==['POSITION'] for c in changes)
        assert (prior/'scene.json').read_bytes()==(package/'scene.json').read_bytes()
        result.update(prior_comparison=changes,scene_metadata_unchanged=True,materials_textures_and_other_geometry_unchanged=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--package',type=Path,required=True); p.add_argument('--prior',type=Path)
    a=p.parse_args(); print(json.dumps(check(a.package,a.prior),indent=2))
