"""Freeze additive native preparation. Does not start server or install."""
from pathlib import Path
import ast,difflib,hashlib,importlib.util,json,subprocess,sys
H=Path(__file__).resolve().parent;P=H.parent;B=P.parent/'world-observation-exclusion-055'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(p):return {'sha256':sha(p),'bytes':p.stat().st_size}
def put(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=json.loads((P/'CANDIDATE-CLOSURE.json').read_bytes());current=json.loads((H/'CANDIDATE-CLOSURE.json').read_bytes())
assert set(old)==set(current) and [r for r in current if current[r]!=old[r]]==['tools/world_builder_engine/layout_package_export.py']
def scrub(text):
 t=ast.parse(text)
 for node in t.body:
  if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='RENDERER' for x in node.targets):
   assert isinstance(node.value,ast.Dict)
   for k,v in zip(node.value.keys,node.value.values):
    if isinstance(k,ast.Constant) and k.value=='viewer.mjs':v.value='EXACT_VIEWER_PIN'
 return ast.dump(t,include_attributes=False)
rel='tools/world_builder_engine/layout_package_export.py'
assert scrub((P/'candidate'/rel).read_text())==scrub((H/'candidate'/rel).read_text())
parent=load('frozen056verify',P/'verify.py');integrity=parent.verify()
guard=load('successor056guard',H/'installation/install_exact.py');assert guard.check_candidate_closure()==22
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());guard.validate(plan,guard.K,H);guard.check_other_sources(plan)
checks={}
for name in ('install_exact.py','serve_review.py'):
 p=subprocess.run([sys.executable,'-B',str(H/'installation'/name)],capture_output=True,text=True,check=True)
 checks[name]=json.loads(p.stdout)
put(H/'READONLY-PREFLIGHTS.json',checks)
contract=json.loads((H/'installation/REVIEW-BINDING.json').read_bytes())
template={k:contract[k] for k in ('install_plan_sha256','source_diff_sha256','candidate_backend_sha256','preview_manifest_sha256')}
template.update(status='PENDING_ROOT_REVIEW_NOT_AUTHORIZATION',source_review_complete=False,gpu014_closed_and_cleanup_confirmed=False,native_preview_review_complete=False,owner_visual_approval=False,review_notes='Write a separate exact root-review receipt after reviewing source and native trim; this template is not authorization.')
put(H/'installation/ROOT-REVIEW-TEMPLATE.json',template)
put(H/'SOURCE-PROOF.json',{'status':'PASS','only_delta_from_frozen056':rel,'ast_equal_except_renderer_viewer_pin':True,
 'parent056_frozen_unchanged':integrity,'full_candidate_closure_verified':22,'canonical051_preimages_verified':7,'protected_originals':116,
 'native_visual_approval':False,'server_started':False,'installed':False})
depfiles=[P/'DELIVERY.json',P/'FROZEN-MANIFEST.json',P/'GEOMETRY-TESTS.json',P/'prepare_native.py',P/'prepare_successor.py',P/'prepare_review.py',P/'installation/install_exact.py',P/'installation/test_installer.py',P/'installation/INSTALLER-TEST-RESULT.json',B/'DELIVERY.json',B/'FROZEN-MANIFEST.json']
put(H/'DEPENDENCIES.json',{'files':{str(p):row(p) for p in depfiles},'private_runtime_context_excluded_from_public_backup':True,
 'recovery':'Frozen055 plus frozen056 geometry overlay and this successor export pin; includes full22 source inventory and seven canonical051 preimages.',
 'geometry_tests_reused':'The source export pin is the sole difference from the tested056 geometry;14 cases630 rays were not relabeled as a second run.'})
diff=[]
for name in ('install_exact.py','serve_review.py','test_installer.py'):
 diff.extend(difflib.unified_diff((B/'installation'/name).read_text().splitlines(True),(H/'installation'/name).read_text().splitlines(True),fromfile='055/installation/'+name,tofile='056-successor/installation/'+name))
(H/'INSTALLER-FROM055.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
files={p.relative_to(H).as_posix():row(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.relative_to(H).parts[0]!='runtime_context'}
put(H/'FROZEN-MANIFEST.json',{'status':'056_NATIVE_SUCCESSOR_UNINSTALLED','files':files,'private_runtime_context_excluded':True})
put(H/'DELIVERY.json',{'status':'READY_FOR_ROOT_NATIVE_REVIEW_NOT_INSTALLED','manifest':row(H/'FROZEN-MANIFEST.json'),'files':len(files),
 'plan':row(H/'INSTALL-PLAN.json'),'source_closure':row(H/'CANDIDATE-CLOSURE.json'),'installer':row(H/'installation/install_exact.py'),
 'preview_manifest_sha256':contract['preview_manifest_sha256'],'exact_canonical051_targets':7,'protected_originals':116,
 'installer_test_methods':14,'source_parent_preserved':True,'native_visual_checked':False,'server_started':False,'installed':False})
print(json.dumps({'status':'FROZEN056_NATIVE_SUCCESSOR','delivery_sha256':sha(H/'DELIVERY.json'),'manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'plan_sha256':sha(H/'INSTALL-PLAN.json'),'installer_sha256':sha(H/'installation/install_exact.py'),'preview_sha256':contract['preview_manifest_sha256'],'files':len(files)}))
