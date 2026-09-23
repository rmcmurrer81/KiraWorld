from pathlib import Path
import copy,hashlib,importlib.util,json,struct
H=Path(__file__).resolve().parent;E=Path('@kira_root/tools/world_builder_engine');C=H/'candidate/tools/world_builder_engine';S=H.parent/'world-observation-viewport-053'
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('preview054_compat',C/'world_layout_preview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Simulate this backend at its intended canonical path without writing there.
# All saved assets and source bindings are still read/verified from their real paths.
native_binding=m.binding;code=(C/'world_layout_preview.py').read_bytes();expected_file=E/'world_layout_preview.py'
def future_binding(path):
 if Path(path)==expected_file:return {'path':str(expected_file),'bytes':len(code),'sha256':sha(code)}
 return native_binding(path)
m.ROOT=E;m.NAVIGATION=E/'horizontal_navigation.mjs';m.__file__=str(expected_file);m.binding=future_binding
m.THREE_BUILD=E.parents[1]/'Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/node_modules/three/build'
old=Path('@kira_root/Data/world_layout_previews/layout-a37f864587b3ee075e21ccd1/manifest.json')
prior=m.verify_preview(old,sha(old.read_bytes()));assert 'presentation_setting' not in prior
assert m.verify_presentation(prior)['setting']=='unspecified'
current_path=Path(json.loads((H/'actual-001/PREVIEW-RESULT.json').read_bytes())['current']['manifest_path']);current=json.loads(current_path.read_bytes())
checks=[]
for kind in ('setting','brief','drop_binding'):
 damaged=copy.deepcopy(current)
 if kind=='setting':damaged['presentation_setting']['setting']='unspecified'
 elif kind=='brief':damaged['presentation_source_brief']['prompt']='Build an orbital spacecraft habitat.'
 else:
  del damaged['presentation_setting'];del damaged['presentation_source_brief']
 try:m.verify_presentation(damaged)
 except m.PreviewError:checks.append({'tamper':kind,'held':True})
 else:raise AssertionError('Tampered setting accepted: '+kind)
def glb(path):
 raw=path.read_bytes();size,kind=struct.unpack_from('<II',raw,12);data=json.loads(raw[20:20+size]);offset=20+size;length,kind=struct.unpack_from('<II',raw,offset);assert kind==0x004e4942;return data,raw[offset+8:offset+8+length]
before,bin_before=glb(S/'actual-001/package/scene.glb');after,bin_after=glb(H/'actual-001/package/scene.glb')
assert bin_before==bin_after
def without_presentation(value):
 if isinstance(value,dict):return {k:without_presentation(v) for k,v in value.items() if k!='presentation_setting'}
 if isinstance(value,list):return [without_presentation(v) for v in value]
 return value
assert without_presentation(before)==without_presentation(after)
report={'status':'054_LEGACY_PREVIEW_AND_EXACT_APPEARANCE_TRANSPORT_PASS','legacy_manifest_sha256':sha(old.read_bytes()),'legacy_existing_manifest_verified':True,
 'scope':'Candidate backend code simulated at canonical path using a read-only backend-binding substitution; all real legacy asset/source bindings were checked. No installation.',
 'tamper_cases':checks,'actual054_glb_binary_payload_identical_to053':True,'json_diff_only_minimal_presentation_provenance':True,'no_raw_brief_in_glb':True,
 '053_render_artifact_relevance':'Same exact geometry/material/texture/light payload;053 images remain diagnostic file renders, not054 native visual approval.','canonical_or_owner_writes':False}
with (H/'LEGACY-TRANSPORT-RESULT.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'status':report['status'],'legacy_existing_manifest_verified':True,'glb_binary_exact':True,'tamper_cases':len(checks)}))
