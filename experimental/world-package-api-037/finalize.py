from pathlib import Path
import ast,datetime,difflib,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;K=Path('@kira_root');C=HERE/'candidate';A=C/'tools/world_builder_engine/layout_package_assets'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
external=json.loads((HERE/'EXTERNAL-PINS.json').read_text(encoding='utf-8'))
node=Path('C:/Program Files/nodejs/node.exe');external['node']={'sha256':sha(node),'bytes':node.stat().st_size}
files={p.relative_to(A).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(A.rglob('*')) if p.is_file() and p.name!='PRODUCER-PINS.json' and '__pycache__' not in p.parts}
(A/'PRODUCER-PINS.json').write_text(json.dumps({'contract':'layout_package_producer_pins_v1','files':files,'external':external},indent=2)+'\n',encoding='utf-8')
for p in C.rglob('*.py'):ast.parse(p.read_bytes())
for name in ('build_glb.mjs','authored_scene.mjs','cpu_canvas.mjs'):
 result=subprocess.run([str(node),'--check',str(A/name)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10);assert result.returncode==0,result.stderr.decode()
original=K/'tools/world_builder_workspace.py';assert sha(original)==json.loads((HERE/'BASELINE.json').read_text())['sha256']
changes=''.join(difflib.unified_diff((HERE/'baseline/tools/world_builder_workspace.py').read_text(encoding='utf-8').splitlines(True),(C/'tools/world_builder_workspace.py').read_text(encoding='utf-8').splitlines(True),fromfile='installed/world_builder_workspace.py',tofile='candidate037/world_builder_workspace.py'))
(HERE/'WORKSPACE-CHANGES.patch').write_text(changes,encoding='utf-8')
rows=[]
for p in sorted(C.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 rel=p.relative_to(C).as_posix();target=K/rel
 rows.append({'relative_path':rel,'target':str(target),'before_sha256':sha(target) if target.exists() else None,'after':{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}})
protected=json.loads((HERE.parent/'world-preview-refresh-candidate-028/INSTALL-PLAN.json').read_text())['protected_inputs']
assert all(sha(p)==s for p,s in protected.items())
plan={'status':'HELD_FOR_REAL_API_EXPORT_AND_NATIVE_UI_REVIEW','reviewed':False,'canonical_changes':0,'files':rows,'protected_inputs':protected,'real_api_exports_this_candidate':0,'mock_tests':22}
(HERE/'INSTALL-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
delivery={'status':'037_CODE_AND_MOCKED_CALLBACK_TESTS_READY_REAL_EXPORT_PENDING','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'candidate_files':len(rows),'candidate_bytes':sum(r['after']['bytes'] for r in rows),'api_sha256':sha(C/'tools/world_builder_engine/layout_package_export.py'),'workspace_sha256':sha(C/'tools/world_builder_workspace.py'),'install_plan_sha256':sha(HERE/'INSTALL-PLAN.json'),'mock_tests':22,'real_glb_exports':0,'native_ui_opened':False,'installed':False,'canonical_unchanged':True,'protected_original_files_unchanged':len(protected),'gpu_model_browser_jobs':0,'pending':['Root review of API and source closure','Coordinated real selected saved Mars API export after Studio render','Native button and output-folder review before installation'],'unsupported_other_layouts_explicit':True}
(HERE/'DELIVERY.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8');print(json.dumps(delivery))
