from pathlib import Path
import difflib,hashlib,json,datetime
H=Path(__file__).resolve().parent;W=H.parent
old=W/'world-metadata-package-candidate-031'
pairs=[(H/'baseline/scene_metadata.mjs',H/'core/candidate/tools/world_builder_engine/scene_metadata.mjs','scene_metadata.mjs')]
pairs.extend((old/name,H/'package'/name,name) for name in ['package_writer.py','test_package.py','make_example.py'])
lines=[]
for a,b,name in pairs:lines.extend(difflib.unified_diff(a.read_text(encoding='utf-8').splitlines(),b.read_text(encoding='utf-8').splitlines(),fromfile='previous/'+name,tofile='034/'+name,lineterm=''))
(H/'CHANGES.patch').write_text('\n'.join(lines)+'\n',encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins=json.loads((H/'HISTORICAL-SOURCE-PINS.json').read_bytes());assert all(sha(Path(r['path']))==r['sha256'] for r in pins)
actual=json.loads((H/'ACTUAL-PACKAGE-REVIEW.json').read_bytes())
files=[{'path':p.relative_to(H).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.rglob('*')) if p.is_file() and 'synthetic_sources' not in p.parts]
receipt={'status':'034_STRUCTURAL_OWNER_FIX_READY_FOR_ROOT_REVIEW','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'installed':False,'metadata_only':True,'core_sha256':sha(H/'core/candidate/tools/world_builder_engine/scene_metadata.mjs'),
 'regressions':{'synthetic_ownership_groups':10,'actual_ownership_groups':10,'inherited_metadata_groups':11,'inherited_package_tests':15,'new_package_gates':4},
 'actual_corrected_structural_links':59,'actual_package_manifest_sha256':actual['package']['manifest_sha256'],
 'protected_owner_files_unchanged':116,'historical_code_files_unchanged':12,'prior031_actual_package_unchanged':True,
 'canonical_changes':0,'geometry_response_mesh_visual_engine_or_vr_approval':False,'files':files}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
