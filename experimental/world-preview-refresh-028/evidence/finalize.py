from pathlib import Path
import difflib,hashlib,json
H=Path(__file__).resolve().parent;W=H.parent.parent;K=Path.home()/'Kira'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
baselines=json.loads((H/'BASELINES.json').read_text());files=[];patches=[]
for item in [*baselines,{'relative_path':'tools/world_builder_engine/preview_refresh.py','before_sha256':None}]:
 rel=item['relative_path'];target=K/rel;before=H/'baseline'/rel;after=H/'candidate'/rel
 if item['before_sha256'] is None:assert not target.exists();a=[]
 else:assert sha(target)==item['before_sha256'];a=before.read_text(encoding='utf-8').splitlines(keepends=True)
 files.append({'relative_path':rel,'target':str(target),'before_sha256':item['before_sha256'],'preimage':str(before) if before.exists() else None,'after':{'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}})
 patches.extend(difflib.unified_diff(a,after.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
protected=json.loads((W/'work/world-habitat-combined-install-027/INSTALL-PLAN.json').read_text())['protected_inputs']
assert all(sha(p)==d for p,d in protected.items())
dependencies={str(K/'tools'/name):sha(K/'tools'/name) for name in ('world_saved_research.py','world_builder_engine/pipeline.py','world_builder_engine/world_layout_preview.py')}
plan={'status':'PROPOSED_NOT_INSTALLED','files':files,'protected_inputs':protected,'required_dependencies':dependencies,
 'scope':'Explicit Open current preview builds/reuses a separate immutable presentation from exact saved sources. No model/research dispatch or saved-job/pipeline pointer updates.',
 'test_receipt':str(H/'TEST-RESULT-1.json'),'test_receipt_sha256':sha(H/'TEST-RESULT-1.json'),
 'limits':['Headless native callbacks verified; installed native visual review pending.','Existing preview rendering copies remain unchanged.','Preview geometry, reference/research source provenance and physical scope are unchanged.']}
(H/'INSTALL-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
(H/'CHANGES.patch').write_text(''.join(patches),encoding='utf-8',newline='\n')
delivery={'status':'028_READY_FOR_ROOT_REVIEW_NO_INSTALL','files':4,'new_files':1,'tests':14,'canonical_files_unchanged':True,'protected_owner_source_bindings':len(protected),
 'plan_sha256':sha(H/'INSTALL-PLAN.json'),'patch_sha256':sha(H/'CHANGES.patch'),'models_gpu_browser_started':False}
(H/'DELIVERY.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8');print(json.dumps(delivery))
