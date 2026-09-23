from pathlib import Path
import ast,datetime,hashlib,json,os
T=Path(__file__).resolve().parents[2];H=T/'work/world-chat-usability-audit-046'
K=Path('@kira_root').resolve()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(H/'REVIEW-PLAN.json')=='77d2cfd1ba46d64ef2ece0eca54b00356c6b8751f1b07ee108d5c41bf9eca042'
plan=json.loads((H/'REVIEW-PLAN.json').read_bytes());assert len(plan['files'])==1
row=plan['files'][0];target=Path(row['target']).resolve();after=Path(row['after']['path'])
assert target==K/'tools/world_builder_workspace.py' and target.is_relative_to(K)
assert sha(target)==sha(row['preimage'])==row['before_sha256']
assert sha(after)==row['after']['sha256']=='6f6b8076bca6fe1c1e5c17978bc71c8891f44d025c62222de1f981a7ff80db54'
assert not (H/'INSTALLED.json').exists()
for p,digest in plan['protected_inputs'].items():assert sha(p)==digest
for p,digest in json.loads((H/'SOURCE-PINS.json').read_bytes()).items():assert sha(K/p)==digest
tests=json.loads((H/'TEST-RESULT.json').read_bytes());assert tests['status']=='PASS' and tests['tests_run']==11
ast.parse(after.read_text(encoding='utf8'))
temp=target.with_name(target.name+'.reviewed046.tmp')
try:
    with temp.open('xb') as f:f.write(after.read_bytes());f.flush();os.fsync(f.fileno())
    assert sha(target)==row['before_sha256']
    os.replace(temp,target)
    assert sha(target)==row['after']['sha256']
    for p,digest in plan['protected_inputs'].items():assert sha(p)==digest
except BaseException:
    if sha(target)==row['after']['sha256']:
        rollback=target.with_name(target.name+'.rollback046.tmp')
        with rollback.open('xb') as f:f.write(Path(row['preimage']).read_bytes());f.flush();os.fsync(f.fileno())
        os.replace(rollback,target)
    raise
receipt={'status':'INSTALLED046_CHAT_CONTEXT_RESET','at_utc':datetime.datetime.now(datetime.UTC).isoformat(),
    'files':plan['files'],'plan_sha256':sha(H/'REVIEW-PLAN.json'),'protected_originals_unchanged':len(plan['protected_inputs']),
    'root_review':'Root read exact one-method delta, existing selector/context reset,15 request audit and11 callback/export-boundary tests. Same-job resume preserved; no command dispatcher or generation changes.',
    'model_calls':0,'native_UI_actions':0,'owner_approval':False,
    'remaining_gaps':'Natural edit/open/preview/export/question/negative requests still create research; separate dispatcher work required.',
    'rollback_preimage':row['preimage']}
with (H/'INSTALLED.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'status':receipt['status'],'sha256':sha(H/'INSTALLED.json'),'protected_originals':len(plan['protected_inputs'])}))
