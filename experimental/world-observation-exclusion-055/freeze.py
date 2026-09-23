from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;P=H.parent/'world-observation-setting-054';C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());assert sha(H/'INSTALL-PLAN.json')=='5e6384c3d1bb3d617d1f10e4bb71359e7ee1e50021654bf8096850145dcf7f43'
 assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
 assert all(sha(r['target'])==r['before_sha256'] and sha(r['after']['path'])==r['after']['sha256'] for r in plan['files'])
 changed=[r['relative_path'] for r in plan['files'] if sha(H/'candidate'/r['relative_path'])!=sha(P/'candidate'/r['relative_path'])]
 assert changed==['tools/world_builder_engine/world_layout_preview.py']
 before=load('held054',P/'candidate/tools/world_builder_engine/world_layout_preview.py');after=load('proposed055',C/'world_layout_preview.py');rows=[]
 for prompt in ('Build an original Mars base. Do not show a landscape beyond the window.','Build an original Mars base. Do not create outdoor scenery.'):
  brief={'brief_kind':'isolated_world_research_brief','schema_version':1,'research_mode':'analog_to_original','prompt':prompt,'subject':'Synthetic regression'}
  digest=hashlib.sha256((json.dumps(brief,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
  packet={'brief_sha256':digest,'job_id':'world_research_'+digest[:20],'research_mode':'analog_to_original'};pin=hashlib.sha256(after.canonical(packet)).hexdigest()
  b=before.presentation_setting(brief,packet,pin);a=after.presentation_setting(brief,packet,pin)
  assert b['setting']=='mars_surface' and a['setting']=='unspecified';rows.append({'synthetic_request':prompt,'054':b['setting'],'055':a['setting']})
 binding=json.loads((H/'installation/REVIEW-BINDING.json').read_bytes())
 template={k:binding[k] for k in ('install_plan_sha256','source_diff_sha256','candidate_backend_sha256','preview_manifest_sha256')}
 template.update(status='PENDING_ROOT_REVIEW_NOT_AUTHORIZATION',source_review_complete=False,gpu014_closed_and_cleanup_confirmed=False,native_preview_review_complete=False,owner_visual_approval=False,review_notes='Pending exact source and native preview review; preserve this template and write a separate receipt.')
 put(H/'installation/ROOT-REVIEW-TEMPLATE.json',template)
 proc=subprocess.run([sys.executable,str(H/'installation/install_exact.py')],capture_output=True,text=True,check=True)
 preflight=json.loads(proc.stdout);put(H/'installation/PREFLIGHT.json',preflight)
 put(H/'ASSESSMENT.json',{'status':'055_EXCLUSION_FIX_PREPARED_UNINSTALLED_NATIVE_REVIEW_PENDING','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
  'root_finding_source':{'path':str(H.parent/'world-public025-independent-review-001/REVIEW.json'),'sha256':sha(H.parent/'world-public025-independent-review-001/REVIEW.json')},
  'reproduced_before_after':rows,'only_production_delta_from054':changed,'all_other_six_files_exact054':True,'plan_sha256':sha(H/'INSTALL-PLAN.json'),
  'python_binding_checks':len(json.loads((H/'SETTING-TEST-RESULT.json').read_bytes())['cases']),'js_setting_cases':json.loads((H/'GEOMETRY-SETTING-RESULT.json').read_bytes())['setting_cases'],
  'temporary_installer_test_methods':12,'actual_preview_manifest_sha256':binding['preview_manifest_sha256'],'actual_export_repeated':False,
  'native_visual_review_pending':True,'owner_visual_approval':False,'canonical_or_original_writes':0,'protected_originals':116,'gpu_models_ui_server_launches':0})
 dependencies={'status':'FROZEN_SOURCE_RECOVERY_REFERENCES','installed_base':'public024 ba74f9b6a22e87bc6bab0be6af8d927c6eba3a20 / installed051',
  'prior_frozen054':{'path':str(P/'FROZEN-MANIFEST.json'),'sha256':sha(P/'FROZEN-MANIFEST.json')},
  'actual_transport_evidence_not_rerun':{'path':str(P/'ACTUAL-EXPORT-RESULT.json'),'sha256':sha(P/'ACTUAL-EXPORT-RESULT.json')},
  'test_geometry_reference053':{'path':str(H.parent/'world-observation-viewport-053/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs'),'sha256':sha(H.parent/'world-observation-viewport-053/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs')},
  'candidate_source_closure':'CANDIDATE-CLOSURE.json','unchanged_installed_dependencies':'SOURCE-PINS.json','private_local_review_only':'runtime_context/Data (raw source brief snapshot must not be public)'}
 put(H/'DEPENDENCIES.json',dependencies)
 inventory={}
 for p in sorted(H.rglob('*')):
  rel=p.relative_to(H)
  if not p.is_file() or '__pycache__' in rel.parts or rel.parts[0]=='runtime_context' or p.name in ('DELIVERY.json','FROZEN-MANIFEST.json'):continue
  inventory[rel.as_posix()]={'sha256':sha(p),'bytes':p.stat().st_size}
 put(H/'FROZEN-MANIFEST.json',{'status':'FROZEN055_UNINSTALLED','files':inventory,'excluded_private_runtime_context':True})
 put(H/'DELIVERY.json',{'status':'055_READY_FOR_ROOT_SOURCE_AND_NATIVE_REVIEW_NOT_INSTALLED','plan_sha256':sha(H/'INSTALL-PLAN.json'),
  'frozen_manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'files':len(inventory),'source_diff_sha256':sha(H/'SOURCE.diff'),'from054_diff_sha256':sha(H/'FROM054.diff'),
  'installer_sha256':sha(H/'installation/install_exact.py'),'preview_manifest_sha256':binding['preview_manifest_sha256'],'protected_originals_unchanged':116,
  'native_review_pending':True,'public025_unchanged':True,'models_gpu_ui_server_starts':0})
 print((H/'DELIVERY.json').read_text())
if __name__=='__main__':main()
