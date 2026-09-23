"""Exact one-file049 install/rollback; no arguments means read-only preflight."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os,tempfile
H=Path(__file__).resolve().parent;K=Path('@kira_root').resolve()
EXPECTED_PLAN='c873f387989cdd7347f310194cfea1c3c475bc704db6694e86ccd8001bfe0696'
RELATIVE='tools/world_research.py'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path,raw):
    with tempfile.NamedTemporaryFile(prefix='.codex049-',dir=path.parent,delete=False) as f:
        temporary=Path(f.name);f.write(raw);f.flush();os.fsync(f.fileno())
    try:os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()
def validate(plan,root,workspace,state='before'):
    root=Path(root).resolve();workspace=Path(workspace).resolve()
    assert len(plan['files'])==1 and plan['files'][0]['relative_path']==RELATIVE,'Unexpected scope'
    row=plan['files'][0];target=Path(row['target']).resolve();after=Path(row['after']['path']).resolve();pre=Path(row['preimage']).resolve()
    assert target==root/RELATIVE and target.is_relative_to(root),'Unexpected target'
    assert after==workspace/'candidate'/RELATIVE and pre==workspace/'baseline/world_research.py','Unexpected source/preimage'
    assert sha(after)==row['after']['sha256'] and sha(pre)==row['before_sha256'],'Source or preimage changed'
    ast.parse(after.read_text(encoding='utf8'))
    assert sha(target)==(row['before_sha256'] if state=='before' else row['after']['sha256']),'Installed bytes changed'
    assert all(sha(p)==v for p,v in plan['protected_inputs'].items()),'Protected input changed'
def apply(plan,root,workspace,replace=atomic):
    validate(plan,root,workspace);row=plan['files'][0];target=Path(row['target'])
    try:
        assert sha(target)==row['before_sha256'],'Concurrent installed change'
        raw=Path(row['after']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['after']['sha256']
        replace(target,raw);validate(plan,root,workspace,'after')
        return {'status':'049_EXACT_ONE_FILE_INSTALL_PASS','installed_files':1,'atomic_per_file':True,'protected_inputs_unchanged':len(plan['protected_inputs'])}
    except BaseException as error:
        restored={'status':'held_for_review'}
        try:
            if sha(target)==row['before_sha256']:restored={'status':'already_before'}
            else:
                assert sha(target)==row['after']['sha256'],'Concurrent installed change: rollback held'
                raw=Path(row['preimage']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['before_sha256'],'Preimage changed'
                atomic(target,raw);assert sha(target)==row['before_sha256'];restored={'status':'restored'}
        except BaseException as failure:restored['error']=str(failure)
        return {'status':'049_INSTALL_FAILED_ROLLBACK_ATTEMPTED','error':str(error),'rollback':restored}
def rollback(plan,root,workspace):
    validate(plan,root,workspace,'after');row=plan['files'][0];target=Path(row['target'])
    assert sha(target)==row['after']['sha256'],'Concurrent installed change'
    raw=Path(row['preimage']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['before_sha256']
    atomic(target,raw);validate(plan,root,workspace)
    return {'status':'049_EXACT_ONE_FILE_ROLLBACK_PASS','restored_files':1,'protected_inputs_unchanged':len(plan['protected_inputs'])}
def other_sources():
    for relative,digest in json.loads((H/'SOURCE-PINS.json').read_bytes()).items():
        if relative!=RELATIVE:assert sha(K/relative)==digest,'Unrelated source changed'
def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--apply',metavar='ROOT_APPROVED_PLAN_SHA');group.add_argument('--rollback',metavar='ROOT_APPROVED_PLAN_SHA');args=parser.parse_args()
    assert sha(H/'REVIEW-PLAN.json')==EXPECTED_PLAN,'Plan changed';plan=json.loads((H/'REVIEW-PLAN.json').read_bytes());other_sources()
    if not args.apply and not args.rollback:
        validate(plan,K,H);print(json.dumps({'status':'049_READ_ONLY_PREFLIGHT_PASS','files':1,'protected_inputs':len(plan['protected_inputs']),'canonical_writes':0}));return
    assert (args.apply or args.rollback)==EXPECTED_PLAN,'Exact root-approved plan argument required'
    path=H/('INSTALLED.json' if args.apply else 'ROLLED-BACK.json');assert not path.exists(),'Preserve existing receipt'
    result=apply(plan,K,H) if args.apply else rollback(plan,K,H)
    result.update({'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'plan_sha256':EXPECTED_PLAN,'files':plan['files'],'operation':'apply' if args.apply else 'rollback',
        'models_ui_network':0,'visual_or_owner_approval':False,'authorization':'Explicit root authorization must precede the exact-hash operation; the hash is only an execution guard.'})
    with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
    if 'FAILED' in result['status']:raise SystemExit(1)
if __name__=='__main__':main()
