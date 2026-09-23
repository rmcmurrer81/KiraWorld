"""Guarded seven-file056 installation/rollback. Default operation is read-only."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,os,sys,tempfile
sys.dont_write_bytecode=True

H=Path(__file__).resolve().parent.parent;K=Path('@kira_root').resolve()
EXPECTED_PLAN='aac304b936d23771afd8f41e39660b04808b3317d75b12e8c638febcff61ce2c'
ALLOWED={
    'tools/world_builder_engine/viewer.mjs',
    'tools/world_builder_engine/world_layout_preview.py',
    'tools/world_builder_engine/layout_package_export.py',
    'tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',
    'tools/world_builder_engine/layout_package_assets/authored_scene.mjs',
    'tools/world_builder_engine/layout_package_assets/build_glb.mjs',
    'tools/world_builder_engine/layout_package_assets/PRODUCER-PINS.json',
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(path,raw):
    with tempfile.NamedTemporaryFile(prefix='.codex056-',dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
    try:os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()
def protected(plan):
    assert all(sha(p)==v for p,v in plan['protected_inputs'].items()),'Protected original changed'
def validate(plan,root,workspace,state='before'):
    root=root.resolve();workspace=workspace.resolve();rows=plan['files']
    assert len(rows)==7 and {r['relative_path'] for r in rows}==ALLOWED,'Unexpected file scope'
    for row in rows:
        relative=Path(row['relative_path']);target=Path(row['target']).resolve()
        assert not relative.is_absolute() and '..' not in relative.parts
        assert target.is_relative_to(root) and target==root/relative,'Target outside exact installed file'
        after=Path(row['after']['path']).resolve();pre=Path(row['preimage']).resolve()
        assert after.is_relative_to(workspace/'candidate') and pre.is_relative_to(workspace/'canonical-preimages')
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
            changed.append(row);replace(target,raw);assert sha(target)==row['after']['sha256']
        validate(plan,root,workspace,'after')
        return {'status':'056_EXACT_SEVEN_FILE_INSTALL_PASS','installed_files':7,'atomic_per_file':True,'rollback_needed':False,'protected_original_files_unchanged':len(plan['protected_inputs'])}
    except Exception as error:
        # Do not erase concurrent edits. Preserve their path in the failure
        # receipt for root review, rather than guessing which bytes to keep.
        for row in reversed(changed):
            target=Path(row['target'])
            if target.exists() and sha(target)==row['before_sha256']:
                restored.append({'relative_path':row['relative_path'],'status':'unchanged_before_failed_replace'});continue
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
        return {'status':'056_INSTALL_FAILED_ROLLBACK_ATTEMPTED','error':str(error),'rollback':restored}
def rollback(plan,root,workspace):
    validate(plan,root,workspace,'after')
    # Full preflight above prevents a partial rollback when another update has
    # already changed one of these seven files. All old preview directories stay.
    for row in reversed(plan['files']):
        assert sha(row['target'])==row['after']['sha256'],'Concurrent change during rollback'
        atomic(Path(row['target']),Path(row['preimage']).read_bytes())
    validate(plan,root,workspace)
    return {'status':'056_EXACT_SEVEN_FILE_ROLLBACK_PASS','restored_files':7,'protected_original_files_unchanged':len(plan['protected_inputs'])}
def check_other_sources(plan):
    changed={Path(r['target']).resolve() for r in plan['files']}
    for relative,digest in json.loads((H/'SOURCE-PINS.json').read_bytes()).items():
        target=K/'tools/world_builder_engine'/relative
        if target.resolve() not in changed:assert sha(target)==digest,'Unrelated installed source changed'

def check_candidate_closure(workspace=H):
    closure=workspace/'CANDIDATE-CLOSURE.json'
    assert sha(closure)=='4f1ce062e3a557fd2cdbe4d3363545b22e2dc23b729d76821a14f8c38278304c','Unexpected source closure'
    rows=json.loads(closure.read_bytes());assert len(rows)==22
    for rel,row in rows.items():
        p=workspace/'candidate'/rel
        assert p.resolve().is_relative_to((workspace/'candidate').resolve())
        assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'Candidate closure changed'
    assets=workspace/'candidate/tools/world_builder_engine/layout_package_assets'
    pins=json.loads((assets/'PRODUCER-PINS.json').read_bytes())
    for rel,row in pins['files'].items():
        p=assets/rel;assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'Producer source changed'
    return len(rows)

def selected_source_paths(manifest,root,job_id):
    job=(root/'Data/world_research_jobs'/job_id).resolve()
    assert job.parent==(root/'Data/world_research_jobs').resolve(),'Invalid selected job path'
    assert Path(manifest['inputs']['research_packet']['path']).resolve()==job/'research_packet.json','Research packet belongs to another selected job'
    for role in ('geometry_source','blueprint'):
        assert Path(manifest['inputs'][role]['path']).resolve().is_relative_to(job),'Preview source belongs to another saved job'
    return job

def verify_presentation_path(root=K,workspace=H):
    """Validate the exact private preview/source binding without serving it."""
    contract=json.loads((workspace/'installation/REVIEW-BINDING.json').read_bytes())
    preview=Path(contract['preview_manifest_path']).resolve()
    assert preview.is_relative_to((workspace/'runtime_context/Data/world_layout_previews').resolve()) and preview.name=='manifest.json'
    assert sha(preview)==contract['preview_manifest_sha256'],'Reviewed immutable preview changed'
    runtime=workspace/'runtime_context/tools/world_builder_engine/world_layout_preview.py'
    candidate=workspace/'candidate/tools/world_builder_engine/world_layout_preview.py'
    assert sha(runtime)==sha(candidate)==contract['candidate_backend_sha256']
    spec=importlib.util.spec_from_file_location('installer056_preview',runtime);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.THREE_BUILD=root/'Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/node_modules/three/build'
    manifest=module.verify_preview(preview,contract['preview_manifest_sha256'])
    job=selected_source_paths(manifest,root,contract['job_id'])
    actual=module.presentation_setting(module.capture_presentation_brief(job/'research_packet.json'),module.load_json(module.read_exact(job/'research_packet.json')),manifest['inputs']['research_packet']['sha256'])
    assert actual==manifest['presentation_setting']==contract['presentation_setting'],'Current brief differs from reviewed setting provenance'
    return {'preview_manifest_sha256':contract['preview_manifest_sha256'],'job_id':contract['job_id'],'brief_sha256':actual['source']['brief_sha256'],'setting':actual['setting'],'raw_brief_returned':False}

def review_binding(path,expected_digest,operation,contract):
    path=Path(path);assert path.is_file() and not path.is_symlink()
    assert expected_digest and sha(path)==expected_digest,'Exact root-review receipt required'
    value=json.loads(path.read_bytes())
    assert value.get('status')==('ROOT_APPROVED_056_INSTALL' if operation=='apply' else 'ROOT_APPROVED_056_ROLLBACK')
    for key in ('install_plan_sha256','source_diff_sha256','candidate_backend_sha256','preview_manifest_sha256'):
        assert value.get(key)==contract[key],'Review does not bind exact '+key
    assert value.get('source_review_complete') is True
    assert value.get('gpu014_closed_and_cleanup_confirmed') is True
    if operation=='apply':assert value.get('native_preview_review_complete') is True,'Native preview review is still pending'
    assert isinstance(value.get('review_notes'),str) and value['review_notes'].strip()
    return {'path':str(path),'sha256':expected_digest,'status':value['status']}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',metavar='EXACT_APPROVED_PLAN_SHA');parser.add_argument('--rollback',metavar='EXACT_APPROVED_PLAN_SHA');parser.add_argument('--review');parser.add_argument('--review-sha256');args=parser.parse_args()
    assert not (args.apply and args.rollback)
    assert sha(H/'INSTALL-PLAN.json')==EXPECTED_PLAN
    plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());check_candidate_closure();check_other_sources(plan)
    assert len(plan['protected_inputs'])==116,'Expected complete116-input preservation inventory'
    provenance=verify_presentation_path()
    if not args.apply and not args.rollback:
        validate(plan,K,H);print(json.dumps({'status':'056_READ_ONLY_INSTALL_PREFLIGHT_PASS','files':7,'protected_originals':len(plan['protected_inputs']),'canonical_writes':0,'presentation_provenance':provenance}));return
    assert (args.apply or args.rollback)==EXPECTED_PLAN,'Exact root-approved plan argument required'
    contract=json.loads((H/'installation/REVIEW-BINDING.json').read_bytes())
    assert contract['install_plan_sha256']==EXPECTED_PLAN and contract['source_diff_sha256']==sha(H/'SOURCE.diff')
    assert args.review,'Separate root review receipt is required'
    reviewed=review_binding(args.review,args.review_sha256,'apply' if args.apply else 'rollback',contract)
    target=H/('INSTALLED.json' if args.apply else 'ROLLED-BACK.json');assert not target.exists(),'Preserve existing execution receipt'
    result=apply(plan,K,H) if args.apply else rollback(plan,K,H)
    check_other_sources(plan)
    result.update({'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'install_plan_sha256':EXPECTED_PLAN,
        'explicit_operation':'apply' if args.apply else 'rollback','files':plan['files'],'saved_previews_modified':False,'native_ui_models_gpu':0,
        'root_review':reviewed,'presentation_provenance':provenance,
        'authorization':'Explicit root authorization must precede invoking the exact-hash apply or rollback command; matching arguments and receipts are guards, not independent authorization.'})
    with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
    if 'FAILED' in result['status']:raise SystemExit(1)
if __name__=='__main__':main()
