from pathlib import Path
import hashlib,json,difflib
H=Path(__file__).resolve().parent;K=Path.home()/'Kira';C=H/'candidate/tools/world_builder_engine'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(K/'tools/world_builder_engine/walk_controller.mjs')==sha(H/'baseline/walk_controller.mjs')
assert sha(K/'tools/world_builder_engine/horizontal_navigation.mjs')==sha(H/'baseline/horizontal_navigation.mjs')
assert not (K/'tools/world_builder_engine/scene_metadata.mjs').exists()
rows=[];patch=[]
for n in ('walk_controller.mjs','scene_metadata.mjs'):
 before=H/'baseline'/n;after=C/n
 rows.append({'relative_path':'tools/world_builder_engine/'+n,'before_sha256':sha(before) if before.exists() else None,'after_sha256':sha(after),'after_bytes':after.stat().st_size})
 patch.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(keepends=True) if before.exists() else [],after.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+n,tofile='b/'+n))
(H/'CHANGES.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
proof=json.loads((H/'TEST-RESULT-002.json').read_text())
assert proof['status']=='PASS_PURE_SCENE_METADATA_PROTOTYPE'
value={'status':'030_ISOLATED_METADATA_PROTOTYPE_READY_NOT_INSTALLED','files':rows,'test_groups':len(proof['checks']),
 'latest_test_receipt':'TEST-RESULT-002.json','latest_test_sha256':sha(H/'TEST-RESULT-002.json'),
 'latest_synthetic_export':'SYNTHETIC-METADATA-002.json','latest_synthetic_export_sha256':sha(H/'SYNTHETIC-METADATA-002.json'),
 'metadata_counts':{k:proof[k] for k in ('rooms','nodes','colliders','doors')},'canonical_files_changed':False,'owner_files_changed':False,
 'network_models_gpu_browser_started':False,'exported_mesh_files':0,'engine_or_vr_adapter':False,
 'next_requirement':'Root code review; production wiring/package writer and verified digest computation remain absent. Do not present as a usable game/VR exporter.'}
(H/'DELIVERY.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps(value))
