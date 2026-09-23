"""Exact two-file 048 install/rollback; default mode only checks bytes."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os,tempfile
H=Path(__file__).resolve().parent;K=Path('@kira_root').resolve()
EXPECTED_PLAN='3fedb5237a74155411c93453df700ecfeaca358bedd9b5dcdc2594409d713906'
ORDER=['tools/world_chat_requests.py','tools/world_builder_workspace.py']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def current(path):return sha(path) if Path(path).exists() else None
def atomic(path,raw):
    with tempfile.NamedTemporaryFile(prefix='.codex048-',dir=path.parent,delete=False) as f:
        temporary=Path(f.name);f.write(raw);f.flush();os.fsync(f.fileno())
    try:os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()
def protected(plan):
    assert all(sha(p)==digest for p,digest in plan['protected_inputs'].items()),'Protected input changed'
def validate(plan,root,workspace,state='before'):
    root=Path(root).resolve();workspace=Path(workspace).resolve()
    assert [r['relative_path'] for r in plan['files']]==ORDER,'Unexpected file scope/order'
    for row in plan['files']:
        relative=Path(row['relative_path']);target=Path(row['target']).resolve();after=Path(row['after']['path']).resolve()
        assert target==root/relative and target.is_relative_to(root),'Unexpected target'
        assert after==workspace/'candidate'/relative and after.is_relative_to(workspace/'candidate'),'Unexpected candidate source'
        assert sha(after)==row['after']['sha256'],'Candidate changed';ast.parse(after.read_text(encoding='utf8'))
        if row['before_sha256'] is None:
            assert row['relative_path']==ORDER[0] and row['preimage'] is None,'Only the helper may be new'
        else:
            pre=Path(row['preimage']).resolve();assert pre==workspace/'baseline/world_builder_workspace.py'
            assert sha(pre)==row['before_sha256'],'Preimage changed'
        assert current(target)==(row['before_sha256'] if state=='before' else row['after']['sha256']),'Installed bytes changed'
    protected(plan)
def restore_row(row):
    target=Path(row['target'])
    assert current(target)==row['after']['sha256'],'Concurrent installed change: rollback held'
    if row['before_sha256'] is None:
        target.unlink()  # Exact new file, already scope/hash checked; no recursive deletion.
    else:
        raw=Path(row['preimage']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['before_sha256'],'Preimage changed'
        atomic(target,raw)
    assert current(target)==row['before_sha256']
def apply(plan,root,workspace,replace=atomic):
    validate(plan,root,workspace);attempted=[]
    try:
        for row in plan['files']:
            target=Path(row['target']);assert current(target)==row['before_sha256'],'Concurrent installed change'
            raw=Path(row['after']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['after']['sha256']
            attempted.append(row);replace(target,raw);assert sha(target)==row['after']['sha256']
        validate(plan,root,workspace,'after')
        return {'status':'048_EXACT_TWO_FILE_INSTALL_PASS','installed_files':2,'atomic_per_file':True,'protected_inputs_unchanged':len(plan['protected_inputs'])}
    except BaseException as error:
        restored=[]
        for row in reversed(attempted):
            try:
                if current(row['target'])==row['before_sha256']:state='already_before'
                else:restore_row(row);state='restored'
                restored.append({'relative_path':row['relative_path'],'status':state})
            except BaseException as failure:
                restored.append({'relative_path':row['relative_path'],'status':'rollback_held','error':str(failure)})
        return {'status':'048_INSTALL_FAILED_ROLLBACK_ATTEMPTED','error':str(error),'rollback':restored}
def rollback(plan,root,workspace):
    validate(plan,root,workspace,'after')
    for row in reversed(plan['files']):restore_row(row)
    validate(plan,root,workspace)
    return {'status':'048_EXACT_TWO_FILE_ROLLBACK_PASS','restored_files':2,'protected_inputs_unchanged':len(plan['protected_inputs'])}
def other_sources(plan):
    changed={r['relative_path'] for r in plan['files']}
    for relative,digest in json.loads((H/'SOURCE-PINS.json').read_bytes()).items():
        if relative not in changed:assert sha(K/relative)==digest,'Unrelated installed dependency changed'
def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--apply',metavar='ROOT_APPROVED_PLAN_SHA');group.add_argument('--rollback',metavar='ROOT_APPROVED_PLAN_SHA');args=parser.parse_args()
    assert sha(H/'INSTALL-PLAN.json')==EXPECTED_PLAN,'Plan changed'
    plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());other_sources(plan)
    if not args.apply and not args.rollback:
        validate(plan,K,H);print(json.dumps({'status':'048_READ_ONLY_PREFLIGHT_PASS','files':2,'protected_inputs':len(plan['protected_inputs']),'canonical_writes':0}));return
    assert (args.apply or args.rollback)==EXPECTED_PLAN,'Exact approved plan argument required'
    path=H/('INSTALLED.json' if args.apply else 'ROLLED-BACK.json');assert not path.exists(),'Preserve existing receipt'
    result=apply(plan,K,H) if args.apply else rollback(plan,K,H)
    result.update({'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'install_plan_sha256':EXPECTED_PLAN,'files':plan['files'],
        'operation':'apply' if args.apply else 'rollback','models_gpu_native_ui':0,'owner_approval':False,
        'authorization':'Explicit root authorization must precede invoking the exact-hash operation. A hash argument is not independent authorization.'})
    with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
    if 'FAILED' in result['status']:raise SystemExit(1)
if __name__=='__main__':main()
