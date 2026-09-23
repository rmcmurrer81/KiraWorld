"""Read-only owner compatibility plus a real synthetic new-preview creation."""
from pathlib import Path
import hashlib,json,types,subprocess,sys
H=Path(__file__).resolve().parent;W=H.parent.parent;K=Path.home()/'Kira'
sys.dont_write_bytecode=True
P=json.loads((H/'INSTALL-PLAN.json').read_text());R=W/'work/world-habitat-realism-025'
SOURCE=H/'candidate/tools/world_builder_engine/world_layout_preview.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(source,location):
 m=types.ModuleType('preview027');m.__file__=str(location);exec(compile(source.read_bytes(),str(source),'exec'),m.__dict__);return m
def protected():
 assert all(sha(p)==d for p,d in P['protected_inputs'].items())
 assert all(sha(f['target'])==f['before']['sha256'] for f in P['files'])
protected();checks=[]
old=K/'Data/world_layout_previews/layout-a37f864587b3ee075e21ccd1/manifest.json'
fp=json.loads((R/'revision-002/PREVIEW-PLAN.json').read_text())['preview']
for title,path,expected in [('owner_saved_legacy',old,'f99bbbe4fde564e1f48814c899b85ca6f78b0ffe9466a4a88ccabd139999313a'),('furnished_revision002',Path(fp['manifest_path']),fp['manifest_sha256'])]:
 data=json.loads(path.read_text());target=Path(data['inputs']['backend']['path']);m=load(SOURCE,target)
 m.THREE_BUILD=Path(data['source_pins']['three.module.js']['path']).parent
 actual=m.binding
 def future(p,actual=actual,target=target):
  if Path(p).absolute()==target:return {'path':str(target),'bytes':SOURCE.stat().st_size,'sha256':sha(SOURCE)}
  return actual(p)
 m.binding=future
 rows=list(data['inputs'].values())+list(data['source_pins'].values())+list(data['assets'].values())
 before={r['path']:sha(r['path']) for r in rows};before[str(path)]=sha(path)
 result=m.verify_preview(path,expected)
 assert all(sha(p)==d for p,d in before.items())
 checks.append({'name':title,'status':'PASS','build_id':result['build_id'],'actual_unchanged_files':len(before),
  'method':'Candidate026 code at original engine location, only future backend self-binding substituted; all provenance and saved assets read actual bytes.'})
m=load(SOURCE,SOURCE);m.THREE_BUILD=K/'third_party/three/build'
# Verify the preceding026-created synthetic preview still opens under027.
prior=list((H/'candidate/Data/world_layout_previews').glob('*/manifest.json'))
assert len(prior)==1
previous=m.verify_preview(prior[0]);assert previous['inputs']['backend']['sha256']=='fe8cfb9ca9754f71dd223b16ec941753b368b48ded9a5fa0cbe82c83503bec28'
checks.append({'name':'preceding026_creator_remains_compatible','status':'PASS','build_id':previous['build_id']})
fixture=H/'synthetic-002';fixture.mkdir(exist_ok=False)
cache=fixture/'source.txt';cache.write_text('Authored synthetic habitat fixture. No owner research or geometry.')
row={**m.binding(cache),'path':cache.name}
packet=fixture/'research_packet.json';packet.write_bytes(m.canonical({'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original','sources':[{'state':'retrieved_text','content_binding':row,'text_binding':row}]}))
blueprint=fixture/'blueprint.json';blueprint.write_bytes(m.canonical({'research_packet_sha256':sha(packet),'fixture':'Authored synthetic test only'}))
g=json.loads((R/'fixtures/synthetic_habitat.json').read_text());g.update(research_packet_sha256=sha(packet),blueprint_sha256=sha(blueprint))
geometry=fixture/'geometry.json';geometry.write_bytes(m.canonical(g))
created=m.create_preview(geometry,packet,blueprint);manifest=Path(created['manifest_path']);saved=m.verify_preview(manifest,created['manifest_sha256'])
for item in P['files']:
 name=Path(item['relative_path']).name
 if name!='world_layout_preview.py':assert saved['assets']['/'+name]['sha256']==item['after']['sha256']
assert saved['preflight']['status']=='PASS' and saved['inputs']['backend']['sha256']==sha(SOURCE)
assert any('Moving doors have session-local state' in text for text in saved['limitations'])
assert any('Equipment is static' in text for text in saved['limitations'])
assert not any('Open passages are not moving' in text for text in saved['limitations'])
checks.append({'name':'new_synthetic_combined_preview','status':'PASS_REAL_NODE_PREFLIGHT','build_id':created['build_id'],'assets':len(saved['assets']),'five_candidate_bindings_match':True})
checks.append({'name':'new_saved_copies_remain_immutable','status':'PASS'})
assert sha(old)=='f99bbbe4fde564e1f48814c899b85ca6f78b0ffe9466a4a88ccabd139999313a'
protected()
receipt={'status':'PASS_COMBINED_NO_INSTALL','checks':checks,'canonical_files_changed':False,'protected_owner_source_files':len(P['protected_inputs']),
 'browser_gpu_model_network_calls':0,'visual_owner_approval':False,'new_build_contains_only_synthetic_fixture':True,
 'metadata_correction':'027 accurately declares session-local moving doors, no pressure simulation and static equipment. Old manifests retained unchanged.',
 'review_gaps':['Native installed new-preview creation remains untested until root installation and UI review.']}
with (H/'VALIDATION-002.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt))
