"""Read-only actual metadata review; only writes this technical receipt."""
from pathlib import Path
import hashlib,json,re
import package_writer as writer
H=Path(__file__).resolve().parent;W=H.parent.parent
expected='2093234a044eb5c6e8e41b7891d75a5c97947921d3f2b14632e466ebb3d17611'
folder=H/'actual-mars-001';manifest=folder/'manifest.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(manifest)==expected
verified=writer.verify_package(folder);assert verified['manifest_sha256']==expected
scene=json.loads((folder/'scene.json').read_bytes());writer.no_local_paths(scene)
writer.no_local_paths(json.loads(manifest.read_bytes()))
plan=json.loads((W/'work/world-preview-refresh-candidate-028/INSTALL-PLAN.json').read_bytes())
assert len(plan['protected_inputs'])==116
assert all(sha(path)==digest for path,digest in plan['protected_inputs'].items())
allowed={'Equipment Vestibule','Primary Airlock','Mission Operations Center','Crew Living Quarters','Science Lab','Viewport Deck','Main circulation corridor'}
assert {r['label'] for r in scene['rooms']}==allowed
assert {n['label'] for n in scene['nodes'] if 'label' in n}==allowed
for p in folder.iterdir():
 text=p.read_text(encoding='utf-8')
 assert not re.search(re.escape(Path.home().name)+r'|https?://|data:image',text,re.I)
for key in ('equipment_meshes','materials_or_textures','engine_adapter','vr_runtime','session_state_export'):
 assert scene['capabilities'][key] is False
receipt={'status':'ACTUAL_SAVED_MARS_METADATA_PACKAGE_REVIEW_PASS','manifest_sha256':expected,
 'scope':'Root created this metadata-only package from the installed028 saved preview source bindings. Subagent verified package integrity, structural counts, labels and protected-source hashes without changing package/source files.',
 'counts':{key:len(scene[key]) for key in ('rooms','nodes','colliders','doors')},'room_labels':sorted(allowed),
 'protected_original_files_unchanged':116,'absolute_paths_or_personal_memory_media_bundled':False,
 'source_documents_or_raw_geometry_bundled':False,'derived_mars_layout_metadata_bundled':True,
 'public_copy_review':'Safe authored habitat labels and projected geometry/interaction metadata; root authorized including this reviewed derived package. No source research text, original geometry file or owner memory/media files.',
 'metadata_only':True,'meshes_materials_engine_vr_adapter':False,'visual_or_owner_approval':False,
 'root_created_package':True,'this_check_model_network_gpu_visual_calls':0}
with (H/'ROOT-ACTUAL-PACKAGE-REVIEW.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt))
