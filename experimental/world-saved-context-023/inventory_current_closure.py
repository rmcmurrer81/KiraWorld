"""Inventory current owned World source/assets; preserve historical015 receipt."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
H=Path(__file__).resolve().parent;K=Path('@user_home/Kira');TOOLS=K/'tools'
OLD=H.parent/'world-portable-native-preview-candidate-015/INSTALLED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old_hash=sha(OLD);old=json.loads(OLD.read_text(encoding='utf-8'))
assert all(sha(Path(r['path']))==r['sha256'] for r in old['installed_files'])
files={Path(r['path']) for r in old['installed_files']}
files.update([K/'Start_Kira_World_Builder_Workspace.bat',TOOLS/'world_builder_workspace.py',TOOLS/'world_saved_research.py',TOOLS/'run_world_builder_school_loop_20260712.py'])
for folder in ['world_builder_engine','world_builder_components']:
 files.update(p for p in (TOOLS/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.mjs','.js','.css','.html','.json','.md','.txt'})
def resolve(stem):
 for p in [stem.with_suffix('.py'),stem/'__init__.py']:
  if p.is_file() and p.resolve().is_relative_to(K):return p.resolve()
 return None
pending=[p for p in files if p.suffix=='.py'];seen=set();edges=[];external=set()
while pending:
 source=pending.pop()
 if source in seen:continue
 seen.add(source);tree=ast.parse(source.read_text(encoding='utf-8-sig'),filename=str(source))
 for node in ast.walk(tree):
  candidates=[];module=None
  if isinstance(node,ast.Import):
   for name in node.names:
    module=name.name
    candidates.extend([TOOLS.joinpath(*module.split('.')),K.joinpath(*module.split('.'))])
  elif isinstance(node,ast.ImportFrom):
   module=node.module or ''
   if node.level:
    root=source.parent
    for _ in range(node.level-1):root=root.parent
    stem=root.joinpath(*module.split('.')) if module else root
    candidates.append(stem)
    candidates.extend(stem/name.name for name in node.names if name.name!='*')
   else:
    for root in [TOOLS,K]:
     stem=root.joinpath(*module.split('.'));candidates.append(stem)
     candidates.extend(stem/name.name for name in node.names if name.name!='*')
  else:continue
  resolved={p for stem in candidates if (p:=resolve(stem)) is not None}
  if not resolved and module:external.add(module)
  for p in resolved:
   edges.append({'source':source.relative_to(K).as_posix(),'dependency':p.relative_to(K).as_posix()})
   if p not in files:files.add(p);pending.append(p)
inventory=[{'path':p.relative_to(K).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)]
owners=json.loads((OLD.parent/'INSTALL-STARTED.json').read_text())['owner_inventory']
assert all(sha(K/path)==digest for path,digest in owners.items())
assert sha(OLD)==old_hash
result={'status':'CURRENT_WORLD_OWNED_SOURCE_CLOSURE_INVENTORIED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'installed_state':'World015 physics and component preview plus World023 saved research/context controls','historical015_receipt':{'path':str(OLD),'sha256':old_hash,'unchanged':True,'all36_installed_hashes_still_match':True},'files':inventory,'file_count':len(inventory),'static_local_import_edges':edges,'external_or_standard_import_names':sorted(external),'protected56_owner_files_unchanged':True,'scope':'All historical015 closure files plus current workspace launcher, both owned engine/component source-asset trees, school entry script and recursively resolved local Python imports. Model weights, interpreter packages and owner-created world/job data are excluded. Runtime-created artifact paths are validated separately by their existing manifests.','native_ui_review':False,'generation_or_physics_runs':False}
with (H/'CURRENT-WORLD-SOURCE-CLOSURE.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'files':len(inventory),'local_import_edges':len(edges),'historical015_unchanged':True,'owner56_unchanged':True,'sha256':sha(H/'CURRENT-WORLD-SOURCE-CLOSURE.json')}))
