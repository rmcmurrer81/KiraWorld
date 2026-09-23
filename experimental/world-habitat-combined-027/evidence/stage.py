"""Stage an exact five-file installation proposal. Never installs anything."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent.parent;K=Path.home()/'Kira'
R=W/'work/world-habitat-realism-025';C=W/'work/world-immutable-preview-candidate-026'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(p):return {'path':str(p),'sha256':digest(p),'bytes':p.stat().st_size}
assert digest(R/'DELIVERY.json')=='e34cc4516c239a73f28aabdf9f3b511939ab05d772811b11b80b4f2e425c5fdf'
delivery=json.loads((R/'DELIVERY.json').read_text())
files=[]
for item in delivery['files']:
 name=Path(item['relative_path']).name;target=K/item['relative_path'];source=Path(item['after']['path'])
 assert digest(target)==item['before']['sha256'] and digest(source)==item['after']['sha256']
 before=H/'preimages'/name;after=H/'candidate'/item['relative_path']
 before.parent.mkdir(exist_ok=True);after.parent.mkdir(parents=True,exist_ok=True)
 assert not before.exists() and not after.exists();shutil.copyfile(target,before);shutil.copyfile(source,after)
 files.append({'relative_path':item['relative_path'],'target':str(target),'before':row(before),'after':row(after)})
rel='tools/world_builder_engine/world_layout_preview.py';source=C/'candidate'/rel;target=K/rel
assert digest(source)=='fe8cfb9ca9754f71dd223b16ec941753b368b48ded9a5fa0cbe82c83503bec28'
assert digest(target)=='2d5a27e7137011872a0d9645cbfdd96646e592334b44d9d6e800389518604cb9'
before=H/'preimages/world_layout_preview.py';after=H/'candidate'/rel
shutil.copyfile(target,before);shutil.copyfile(source,after)
files.append({'relative_path':rel,'target':str(target),'before':row(before),'after':row(after)})
dependencies=[]
for name in ('horizontal_navigation.mjs','preflight.mjs'):
 source=K/'tools/world_builder_engine'/name;after=H/'candidate/tools/world_builder_engine'/name
 shutil.copyfile(source,after);dependencies.append({'source':row(source),'staged':row(after)})
plan025=json.loads((R/'revision-002/PREVIEW-PLAN.json').read_text())
targets={str(Path(f['target'])) for f in files}
protected={p:d for p,d in plan025['protected_inputs'].items() if str(Path(p)) not in targets}
assert all(digest(p)==d for p,d in protected.items())
plan={'status':'PROPOSED_NOT_INSTALLED','package':'combined-habitat025-preview026-027',
 'public_base_commit':'4044d66d9e95757cd4b54012c49ccd91b4abe235','canonical_root':str(K),
 'files':files,'unchanged_dependencies':dependencies,'protected_inputs':protected,
 'source_delivery':row(R/'DELIVERY.json'),'furnished_preview_plan':row(R/'revision-002/PREVIEW-PLAN.json'),
 'scope':'Five existing engine files only. Original world saves, preview assets and research inputs remain byte-exact.',
 'limitations':['New appearance and session-local doors apply to newly created previews; saved immutable previews keep prior appearance.',
 'Procedural prototype, static equipment, no physical pressure or door-state persistence.',
 'Native installed flow and owner visual approval remain pending.']}
with (H/'INSTALL-PLAN.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'status':plan['status'],'files':len(files),'protected_inputs':len(protected),'plan_sha256':digest(H/'INSTALL-PLAN.json')}))
