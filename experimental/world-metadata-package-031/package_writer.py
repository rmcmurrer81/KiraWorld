"""Portable scene metadata packages from explicit verified saved-source bindings.

CPU/metadata only. No owner lookup, rendering, model call, research fetch or source
write. An existing output directory is always refused, including empty folders.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parent
INPUT_CONTRACT='world_scene_export_input_bindings_v1'
PACKAGE_CONTRACT='world_scene_metadata_package_v1'
MAX_BYTES=5_000_000
ROLES=('geometry_source','blueprint','research_packet')
README=('World scene metadata prototype. No equipment meshes, materials, engine adapter or VR runtime are included.\n'
        'Sources and producer code bytes were verified during package creation. This does not establish source truth, visual quality or owner approval.\n'
        'This package contains semantic/structural metadata only. It contains no source documents, cached research, personal memory files, media or local source paths.\n'
        'Doors describe session-local conservative interaction/collision policy, not pressure simulation or an engine-native physics implementation.\n')

class PackageError(ValueError):pass
def require(ok,message):
    if not ok:raise PackageError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def parse(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'Duplicate JSON key');result[key]=value
        return result
    def bad(_):raise PackageError('Nonfinite JSON number')
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=bad)
def local_path(value):
    p=Path(value).absolute()
    require(not str(p).startswith(('\\\\','//')),'Network paths are unsupported')
    for item in (p,*p.parents):
        if item.exists():
            require(not item.is_symlink() and not getattr(item.lstat(),'st_file_attributes',0)&0x400,'Linked paths are unsupported')
    return p
def read(path,maximum=MAX_BYTES):
    p=local_path(path);require(p.is_file() and 0<p.stat().st_size<=maximum,'Missing or oversized input')
    raw=p.read_bytes();require(0<len(raw)<=maximum,'Input changed size');return raw
def binding(path):
    p=local_path(path);raw=read(p);return {'path':str(p),'bytes':len(raw),'sha256':sha(raw)}
def exact(row):
    require(isinstance(row,dict) and set(row)=={'path','bytes','sha256'},'Exact file binding required')
    require(isinstance(row['path'],str) and Path(row['path']).is_absolute(),'Explicit absolute input path required')
    require(type(row['bytes']) is int and 0<row['bytes']<=MAX_BYTES,'Invalid binding size')
    require(isinstance(row['sha256'],str) and re.fullmatch('[0-9a-f]{64}',row['sha256']),'Invalid binding digest')
    raw=read(row['path']);require(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'Bound source bytes changed');return raw
def source_chain(manifest_path,expected_sha256):
    raw=read(manifest_path);require(sha(raw)==expected_sha256,'Input manifest hash changed');saved=parse(raw)
    require(isinstance(saved,dict) and saved.get('contract') in (INPUT_CONTRACT,'isolated_world_layout_preview_v1'),'Unsupported source binding contract')
    rows=saved.get('inputs');require(isinstance(rows,dict) and all(k in rows for k in ROLES),'Required source binding missing')
    if saved['contract']=='isolated_world_layout_preview_v1':
        body={k:v for k,v in saved.items() if k!='receipt_sha256'}
        require(saved.get('receipt_sha256')==sha(canonical(body)),'Saved preview manifest seal changed')
    require(all(isinstance(rows[name],dict) for name in ROLES),'Malformed source binding')
    verified={name:dict(rows[name]) for name in ROLES};sources={name:parse(exact(verified[name])) for name in ROLES}
    g,b,p=(sources[name] for name in ROLES)
    require(all(isinstance(v,dict) for v in (g,b,p)),'Source documents must be JSON objects')
    require(g.get('research_packet_sha256')==verified['research_packet']['sha256'],'Geometry research digest differs')
    require(g.get('blueprint_sha256')==sha(canonical(b)),'Geometry canonical blueprint digest differs')
    require(b.get('research_packet_sha256')==verified['research_packet']['sha256'],'Blueprint research digest differs')
    require(p.get('packet_kind')=='world_public_text_research_packet' and p.get('research_mode')=='analog_to_original','Original-layout analog research required')
    sources_list=p.get('sources');require(isinstance(sources_list,list) and len(sources_list)<=8,'Invalid research source collection')
    folder=Path(verified['research_packet']['path']).parent
    for index,item in enumerate(sources_list):
        require(isinstance(item,dict),'Invalid research source')
        if item.get('state')!='retrieved_text':continue
        for kind in ('content_binding','text_binding','capture_binding'):
            row=item.get(kind)
            if kind=='capture_binding' and row is None:continue
            require(isinstance(row,dict) and isinstance(row.get('path'),str),'Research cache binding missing')
            relative=row['path'];parts=relative.split('/')
            require('\\' not in relative and ':' not in relative and all(x not in ('','.','..') for x in parts),'Research cache escapes packet directory')
            pin={'path':str(folder.joinpath(*parts)),'bytes':row.get('bytes'),'sha256':row.get('sha256')}
            exact(pin);key='research_cache_'+str(index)+'_'+kind;verified[key]=pin
            if key in rows:require(rows[key]==pin,'Saved cache pin differs from research packet')
    require(not any(k.startswith('research_cache_') and k not in verified for k in rows),'Unknown saved cache binding')
    return g,verified,{'path':str(local_path(manifest_path)),'bytes':len(raw),'sha256':sha(raw)}
def producer(core_root):
    core=local_path(core_root);pins=parse(read(ROOT/'CORE-PINS.json'));result={}
    for relative,expected in pins.items():
        path=core.joinpath(*relative.split('/'));row=binding(path)
        require(row['sha256']==expected,'Reviewed metadata core changed');result[relative]=row
    for name in ('package_writer.py','render_metadata.mjs','CORE-PINS.json'):
        result['writer/'+name]=binding(ROOT/name)
    return result
def portable_pins(rows):return {k:{'bytes':v['bytes'],'sha256':v['sha256']} for k,v in rows.items()}
def no_local_paths(value):
    if isinstance(value,str):
        require(not re.search(r'[A-Za-z]:[\\/]|\\\\|(?:^|\s)/[^\s/]',value),'A metadata label contains an absolute local path')
    elif isinstance(value,list):
        for item in value:no_local_paths(item)
    elif isinstance(value,dict):
        for key,item in value.items():no_local_paths(key);no_local_paths(item)
def build_package(manifest_path,expected_sha256,output,*,scene_id,core_root,node=None):
    output=local_path(output);require(not output.exists(),'Output already exists; never overwrite a package or source folder')
    require(output.parent.is_dir(),'Output parent must already exist')
    geometry,sources,input_pin=source_chain(manifest_path,expected_sha256)
    producers=producer(core_root)
    options={'sceneId':scene_id,'sourceDigests':{'geometry':sources['geometry_source']['sha256'],
        'dressing_recipe':producers['room_dressing_plan.mjs']['sha256'],
        'door_controller':producers['candidate/tools/world_builder_engine/walk_controller.mjs']['sha256']}}
    executable=Path(node or shutil.which('node') or 'node').absolute();require(executable.is_file(),'Node runtime unavailable')
    request=canonical({'geometry':geometry,'options':options})
    run=subprocess.run([str(executable),str(ROOT/'render_metadata.mjs'),str(local_path(core_root))],input=request,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=False)
    require(run.returncode==0,'Metadata projection rejected the source: '+run.stderr.decode('utf-8',errors='replace')[-1500:])
    require(0<len(run.stdout)<=MAX_BYTES,'Metadata output exceeded its size bound');scene=parse(run.stdout)
    require(scene.get('contract')=='world_scene_metadata_v1' and scene.get('scene_id')==scene_id,'Unexpected metadata output')
    require(scene.get('provenance',{}).get('binding_verification')=='actual_bound_bytes_verified_by_package_writer','Metadata verification label missing')
    no_local_paths(scene)
    # No absolute paths are emitted: digests replace local provenance locations.
    scene_raw=run.stdout+b'\n'
    for row in [input_pin,*sources.values(),*producers.values()]:exact(row)
    files={'scene.json':scene_raw,'README.txt':README.encode('utf-8')}
    manifest={'contract':PACKAGE_CONTRACT,'scene_contract':scene['contract'],'scene_id':scene_id,
      'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in files.items()},
      'source_bindings_manifest_sha256':input_pin['sha256'],'verified_source_digests':portable_pins(sources),
      'producer_digests':portable_pins(producers),
      'verification_scope':'Actual source/producer bytes and geometry-blueprint-research/cache digest chain at creation; not factual, visual or physics certification.',
      'metadata_only':True,'mesh_files_included':False,'engine_or_vr_adapter':False,'owner_sources_modified':False}
    manifest['receipt_sha256']=sha(canonical(manifest));files['manifest.json']=canonical(manifest)+b'\n'
    # All validation precedes the only write location. Exclusive creation refuses
    # both an existing directory and any concurrent claimant; sources are read-only.
    output.mkdir(exist_ok=False)
    for name,data in files.items():
        with (output/name).open('xb') as stream:stream.write(data)
    verify_package(output)
    return {'status':'METADATA_PACKAGE_CREATED','manifest_sha256':sha(files['manifest.json']),'files':list(files),'metadata_only':True}
def verify_package(folder):
    folder=local_path(folder);raw=read(folder/'manifest.json');manifest=parse(raw)
    require(manifest.get('contract')==PACKAGE_CONTRACT,'Unsupported package contract')
    body={k:v for k,v in manifest.items() if k!='receipt_sha256'};require(manifest.get('receipt_sha256')==sha(canonical(body)),'Package manifest seal changed')
    require(set(manifest.get('files',{}))=={'scene.json','README.txt'},'Unexpected package file list')
    require({p.name for p in folder.iterdir()}=={'scene.json','README.txt','manifest.json'},'Unexpected file in metadata package')
    for name,pin in manifest['files'].items():
        data=read(folder/name);require(set(pin)=={'bytes','sha256'} and type(pin['bytes']) is int and len(data)==pin['bytes'] and sha(data)==pin['sha256'],'Package file digest mismatch')
    scene=parse(read(folder/'scene.json'));require(scene.get('contract')==manifest['scene_contract'] and scene.get('scene_id')==manifest['scene_id'],'Package scene identity differs')
    return {'status':'METADATA_PACKAGE_INTEGRITY_PASS','manifest_sha256':sha(raw),'scene_id':scene['scene_id'],'metadata_only':True}
def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    build=sub.add_parser('build');build.add_argument('--bindings',required=True);build.add_argument('--bindings-sha256',required=True);build.add_argument('--output',required=True);build.add_argument('--scene-id',required=True)
    build.add_argument('--core-root',default=str(ROOT.parent/'world-scene-metadata-030'));build.add_argument('--node')
    verify=sub.add_parser('verify');verify.add_argument('--package',required=True)
    args=parser.parse_args()
    try:
        result=verify_package(args.package) if args.mode=='verify' else build_package(args.bindings,args.bindings_sha256,args.output,scene_id=args.scene_id,core_root=args.core_root,node=args.node)
        print(json.dumps(result));return 0
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({'status':'METADATA_PACKAGE_HELD','message':str(exc)}),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
