"""Guarded five-file045 installation/rollback. Default operation is read-only."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,tempfile

H=Path(__file__).resolve().parent;K=Path('@kira_root').resolve()
EXPECTED_PLAN='8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71'
ALLOWED={
    'tools/world_builder_engine/viewer.mjs',
    'tools/world_builder_engine/layout_package_export.py',
    'tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',
    'tools/world_builder_engine/layout_package_assets/authored_scene.mjs',
    'tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json',
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(path,raw):
    with tempfile.NamedTemporaryFile(prefix='.codex045-',dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
    try:os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()
def protected(plan):
    assert all(sha(p)==v for p,v in plan['protected_inputs'].items()),'Protected original changed'
def validate(plan,root,workspace,state='before'):
    root=root.resolve();workspace=workspace.resolve();rows=plan['files']
    assert len(rows)==5 and {r['relative_path'] for r in rows}==ALLOWED,'Unexpected file scope'
    for row in rows:
        relative=Path(row['relative_path']);target=Path(row['target']).resolve()
        assert not relative.is_absolute() and '..' not in relative.parts
        assert target.is_relative_to(root) and target==root/relative,'Target outside exact installed file'
        after=Path(row['after']['path']).resolve();pre=Path(row['preimage']).resolve()
        assert after.is_relative_to(workspace/'candidate') and pre.is_relative_to(workspace/'preimages')
        assert sha(after)==row['after']['sha256'] and sha(pre)==row['before_sha256'],'Candidate or preimage changed'
        assert sha(target)==(row['before_sha256'] if state=='before' else row['after']['sha256']),'Installed bytes changed'
    protected(plan)
def apply(plan,root,workspace,replace=atomic):
    validate(plan,root,workspace);changed=[];restored=[]
    try:
        for row in plan['files']:
            target=Path(row['target'])
            assert sha(target)==row['before_sha256'],'Concurrent installed change'
            raw=Path(row['after']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['after']['sha256']
            replace(target,raw);changed.append(row);assert sha(target)==row['after']['sha256']
        validate(plan,root,workspace,'after')
        return {'status':'045_EXACT_FIVE_FILE_INSTALL_PASS','installed_files':5,'atomic_per_file':True,'rollback_needed':False,'protected_original_files_unchanged':len(plan['protected_inputs'])}
    except Exception as error:
        # Do not erase concurrent edits. Preserve their path in the failure
        # receipt for root review, rather than guessing which bytes to keep.
        for row in reversed(changed):
            target=Path(row['target'])
            if not target.exists() or sha(target)!=row['after']['sha256']:
                restored.append({'relative_path':row['relative_path'],'status':'held_concurrent_change'});continue
            raw=Path(row['preimage']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=row['before_sha256']:
                restored.append({'relative_path':row['relative_path'],'status':'held_preimage_change'});continue
            try:
                atomic(target,raw);assert sha(target)==row['before_sha256']
                restored.append({'relative_path':row['relative_path'],'status':'restored'})
            except Exception as rollback_error:
                restored.append({'relative_path':row['relative_path'],'status':'rollback_failed','error':str(rollback_error)})
        return {'status':'045_INSTALL_FAILED_ROLLBACK_ATTEMPTED','error':str(error),'rollback':restored}
def rollback(plan,root,workspace):
    validate(plan,root,workspace,'after')
    # Full preflight above prevents a partial rollback when another update has
    # already changed one of these five files. All old preview directories stay.
    for row in reversed(plan['files']):
        assert sha(row['target'])==row['after']['sha256'],'Concurrent change during rollback'
        atomic(Path(row['target']),Path(row['preimage']).read_bytes())
    validate(plan,root,workspace)
    return {'status':'045_EXACT_FIVE_FILE_ROLLBACK_PASS','restored_files':5,'protected_original_files_unchanged':len(plan['protected_inputs'])}
def check_other_sources(plan):
    changed={Path(r['target']).resolve() for r in plan['files']}
    for relative,digest in json.loads((H/'SOURCE-PINS.json').read_bytes()).items():
        target=K/'tools/world_builder_engine'/relative
        if target.resolve() not in changed:assert sha(target)==digest,'Unrelated installed source changed'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',metavar='EXACT_APPROVED_PLAN_SHA');parser.add_argument('--rollback',metavar='EXACT_APPROVED_PLAN_SHA');args=parser.parse_args()
    assert not (args.apply and args.rollback)
    assert sha(H/'INSTALL-PLAN.json')==EXPECTED_PLAN
    plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());check_other_sources(plan)
    if not args.apply and not args.rollback:
        validate(plan,K,H);print(json.dumps({'status':'045_READ_ONLY_INSTALL_PREFLIGHT_PASS','files':5,'protected_originals':len(plan['protected_inputs']),'canonical_writes':0}));return
    assert (args.apply or args.rollback)==EXPECTED_PLAN,'Exact root-approved plan argument required'
    target=H/('INSTALLED.json' if args.apply else 'ROLLED-BACK.json');assert not target.exists(),'Preserve existing execution receipt'
    result=apply(plan,K,H) if args.apply else rollback(plan,K,H)
    check_other_sources(plan)
    result.update({'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'install_plan_sha256':EXPECTED_PLAN,
        'explicit_operation':'apply' if args.apply else 'rollback','files':plan['files'],'saved_previews_modified':False,'native_ui_models_gpu':0,
        'authorization':'Explicit root authorization must precede invoking the exact-hash apply or rollback command; a hash argument is a guard, not independent authorization.'})
    with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
    if 'FAILED' in result['status']:raise SystemExit(1)
if __name__=='__main__':main()
