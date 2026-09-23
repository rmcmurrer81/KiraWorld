"""Assemble exact proposed World closure without touching a Git index or owner data."""
from pathlib import Path
import hashlib,json,subprocess,sys
H=Path(__file__).resolve().parent;W=H.parents[1]
manifest=json.loads((W/'work/sep22-backups/world-saved-context-004.manifest.json').read_text())
closure=json.loads((H/'CURRENT-WORLD-SOURCE-CLOSURE.json').read_text())
by_path={row['path']:row for row in manifest['files']}
out=H/'public-checkout-check-001';out.mkdir(exist_ok=False)
assembled=[]
for row in closure['files']:
    rel=row['path'];payload=by_path.get(rel)
    data=Path(payload['file']).read_bytes() if payload else subprocess.check_output(['git','-C',manifest['clone'],'show',manifest['base_commit']+':'+rel])
    digest=hashlib.sha256(data).hexdigest()
    assert digest==(payload['sha256'] if payload else row['sha256'])
    target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assembled.append({'path':rel,'sha256':digest,'from':'proposed_manifest' if payload else 'public_base'})
script='''import sys,json
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root/'tools'))
import world_builder_workspace,world_saved_research
assert Path(world_builder_workspace.__file__).resolve()==root/'tools/world_builder_workspace.py'
assert Path(world_saved_research.__file__).resolve()==root/'tools/world_saved_research.py'
origins=[]
for name,module in sys.modules.copy().items():
    p=getattr(module,'__file__',None)
    if p and (name.startswith('world_') or name in ('adaptive_source_selection','create_world_notebook_request','validate_notebook_world_request')):
        path=Path(p).resolve();assert path.is_relative_to(root),(name,str(path));origins.append({'module':name,'path':path.relative_to(root).as_posix()})
print(json.dumps({'status':'PASS_IMPORTS_FROM_PROPOSED_PUBLIC_CLOSURE','origins':origins,'ui_started':False,'model_calls':False}))
'''
run=subprocess.run([sys.executable,'-B','-c',script,str(out)],capture_output=True,text=True,timeout=20)
assert run.returncode==0,run.stderr
result=json.loads(run.stdout)
result.update(assembled_files=assembled,public_manifest_sha256=hashlib.sha256((W/'work/sep22-backups/world-saved-context-004.manifest.json').read_bytes()).hexdigest(),canonical_writes=False,git_mutations=False,owner_data_copied=False)
with (H/'PUBLIC-CHECKOUT-IMPORT-CHECK.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'files':len(assembled),'owned_imports':len(result['origins']),'ui_models_gpu':False}))
