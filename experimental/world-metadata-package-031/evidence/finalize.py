from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;K=Path.home()/'Kira';C=H.parent/'world-scene-metadata-candidate-030'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(K/'tools/world_builder_engine/walk_controller.mjs')==sha(C/'baseline/walk_controller.mjs')
assert not (K/'tools/world_builder_engine/scene_metadata.mjs').exists()
proof=json.loads((H/'TEST-RESULT-2.json').read_text(encoding='utf-8'));assert proof['status']=='PASS'
example=H/'example/package';files=[{'path':p.relative_to(H).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(example.iterdir())]
value={'status':'031_METADATA_PACKAGE_PROTOTYPE_READY_NOT_INSTALLED','tests_passed':proof['tests'],'test_receipt_sha256':sha(H/'TEST-RESULT-2.json'),
 'files':[{'path':n,'sha256':sha(H/n),'bytes':(H/n).stat().st_size} for n in ('package_writer.py','render_metadata.mjs','CORE-PINS.json','test_package.py','make_example.py','README.md')],
 'synthetic_package':files,'source_binding_verification':'Actual SHA256 bytes plus geometry-blueprint-research/cache chain, before and after CPU projection.',
 'portable_without_original_files':True,'owner_data_used_or_changed':False,'canonical_files_changed':False,'model_network_gpu_visual_calls':0,
 'limitations':['Metadata only: no equipment meshes/materials, engine adapter, VR runtime or native export control.','Digests verify bytes, not source truth or visual/owner approval.']}
(H/'DELIVERY.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps(value))
