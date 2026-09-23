"""Verify existing saved bindings, then create a separate corrected metadata package."""
from pathlib import Path
import argparse,copy,hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'package'))
import package_writer as writer

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--bindings',required=True);parser.add_argument('--old-package',required=True)
 parser.add_argument('--protection-plan',required=True);parser.add_argument('--node',required=True)
 args=parser.parse_args();old=Path(args.old_package);bindings=Path(args.bindings)
 prior_files={p.name:sha(p) for p in old.iterdir()};prior_manifest=json.loads((old/'manifest.json').read_bytes())
 assert sha(bindings)==prior_manifest['source_bindings_manifest_sha256']
 protections=json.loads(Path(args.protection_plan).read_bytes())['protected_inputs'];assert len(protections)==116
 assert all(sha(path)==digest for path,digest in protections.items())
 rows=json.loads((H/'HISTORICAL-SOURCE-PINS.json').read_bytes());assert all(sha(r['path'])==r['sha256'] for r in rows)
 geometry,sources,_=writer.source_chain(bindings,sha(bindings));geometry_path=sources['geometry_source']['path']
 run=subprocess.run([args.node,'--max-old-space-size=384',str(H/'test_ownership.mjs'),geometry_path,str(H/'ACTUAL-OWNERSHIP-RESULT.json')],capture_output=True,text=True,timeout=30)
 assert run.returncode==0,(run.stdout,run.stderr)
 result=writer.build_package(bindings,sha(bindings),H/'actual-mars-001',scene_id=prior_manifest['scene_id'],core_root=H/'core',node=args.node)
 assert writer.verify_package(H/'actual-mars-001')['manifest_sha256']==result['manifest_sha256']
 previous=json.loads((old/'scene.json').read_bytes());scene=json.loads((H/'actual-mars-001/scene.json').read_bytes())
 expected=copy.deepcopy(previous);changed=[]
 for c in expected['colliders']:
  actual=next(x for x in scene['colliders'] if x['id']==c['id'])
  if c['owner_node_id']!=actual['owner_node_id']:changed.append({'collider':c['id'],'previous_owner':c['owner_node_id'],'owner':actual['owner_node_id']})
  c['owner_node_id']=actual['owner_node_id']
 assert scene==expected,'Unexpected scene change beyond corrected ownership'
 assert len(changed)==len(geometry['colliders'])==59
 assert all(sha(path)==digest for path,digest in protections.items())
 assert {p.name:sha(p) for p in old.iterdir()}==prior_files
 assert all(sha(r['path'])==r['sha256'] for r in rows)
 writer.no_local_paths(scene);writer.no_local_paths(json.loads((H/'actual-mars-001/manifest.json').read_bytes()))
 assert {r['label'] for r in scene['rooms']}=={'Equipment Vestibule','Primary Airlock','Mission Operations Center','Crew Living Quarters','Science Lab','Viewport Deck','Main circulation corridor'}
 receipt={'status':'ACTUAL_MARS_STRUCTURAL_OWNERSHIP_CORRECTED_AND_VERIFIED','package':result,
  'counts':{key:len(scene[key]) for key in ['rooms','nodes','colliders','doors']},'corrected_links':changed,
  'source_geometry_sha256':sources['geometry_source']['sha256'],'protected_original_files_unchanged':116,
  'historical_source_files_unchanged':len(rows),'historical031_package_unchanged':prior_files,
  'only_scene_changes':'59 null structural collider owners now point to their exact authored structural box nodes with matching bounds.',
  'metadata_only':True,'source_geometry_or_research_documents_bundled':False,'meshes_materials_engine_vr_adapter':False,
  'installed':False,'gpu_models':0,'visual_or_owner_approval':False}
 with (H/'ACTUAL-PACKAGE-REVIEW.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in receipt.items() if k not in ['corrected_links','historical031_package_unchanged']}))

if __name__=='__main__':main()
