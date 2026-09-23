from pathlib import Path
import ast,datetime,difflib,hashlib,json,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');C=H/'candidate';A=C/'tools/world_builder_engine/layout_package_assets'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
pins=json.loads((H/'BASELINE-PINS.json').read_bytes());assert all(sha(K/rel)==digest for rel,digest in pins.items())
protected=json.loads((W/'world-package-039/INSTALL-PLAN.json').read_bytes())['protected_inputs'];assert all(sha(p)==v for p,v in protected.items())
contract_path=C/'tools/world_builder_engine/layout_package_contract.json';contract=json.loads(contract_path.read_bytes())
contract['validation_scope']='No exact geometry allowlist. A bounded authored habitat profile independently recompiles the bound blueprint, verifies supported roles/topology/dimensions and unambiguous structural room ownership. Eligibility is only permission to attempt the pinned builder/importer; readiness requires all actual checks.'
contract['eligibility_profile']='bounded_authored_habitat_export_v1';contract['candidate_status']='isolated_not_installed_pending_new_shape_actual_exports'
write(contract_path,contract)
producer=json.loads((A/'PRODUCER-PINS.json').read_bytes());producer['files']={p.relative_to(A).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(A.rglob('*')) if p.is_file() and p.name!='PRODUCER-PINS.json'};write(A/'PRODUCER-PINS.json',producer)
changes=[];diff=[];closure={}
for p in sorted(C.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(C);target=K/rel;digest=sha(p);closure[rel.as_posix()]={'sha256':digest,'bytes':p.stat().st_size}
 if p.suffix=='.py':ast.parse(p.read_text())
 if p.suffix=='.json':json.loads(p.read_bytes())
 before=sha(target) if target.exists() else None
 if before!=digest:
  baseline=H/'preimages'/rel
  if target.exists():baseline.parent.mkdir(parents=True,exist_ok=True);assert not baseline.exists();baseline.write_bytes(target.read_bytes())
  changes.append({'relative_path':rel.as_posix(),'target':str(target),'before_sha256':before,'preimage':str(baseline) if target.exists() else None,
   'after':{'path':str(p),'sha256':digest,'bytes':p.stat().st_size}})
  if p.name!='PRODUCER-PINS.json':diff.extend(difflib.unified_diff(target.read_text().splitlines(True) if target.exists() else [],p.read_text().splitlines(True),fromfile='installed039/'+rel.as_posix(),tofile='candidate041/'+rel.as_posix()))
subprocess.run(['C:/Program Files/nodejs/node.exe','--check',str(A/'authored_scene.mjs')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(H/'CHANGES.patch').write_text(''.join(diff),encoding='utf-8');write(H/'CANDIDATE-CLOSURE.json',closure)
plan={'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':changes,'protected_inputs':protected,
 'required_before_install':['Real GLB/importer checks on new supported shapes','Actual saved Mars regression through candidate API','Root review'],'native_ui_claim':False}
assert not (H/'INSTALL-PLAN.json').exists();write(H/'INSTALL-PLAN.json',plan)
delivery={'status':'041_PROFILE_CANDIDATE_READY_FOR_REVIEW_NOT_INSTALLED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'changed_install_files':len(changes),'candidate_closure_files':len(closure),'mocked_api_tests':35,'pure_profile_tests':15,'pure_recipe_shapes':4,'recipe_negative_cases':2,
 'actual_041_glb_exports':0,'saved_jobs_schema_inspected':2,'jobs_with_blueprints':1,'protected_originals_unchanged':len(protected),'canonical_unchanged':True,
 'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'gpu_model_ui_browser_calls':0,'engine_vr_pressure_runtime':False,
 'pending':'Actual new-shape and saved-Mars export/importer validation; root installation decision; separate native visual review.'}
write(H/'DELIVERY.json',delivery);print(json.dumps(delivery))
