"""Create/reuse one isolated immutable review copy; no server, export, GPU or UI."""
from pathlib import Path
import copy,hashlib,importlib.util,json,shutil,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;K=Path('@kira_root');E=K/'tools/world_builder_engine'
C=H/'candidate/tools/world_builder_engine';R=H/'runtime_context/tools/world_builder_engine'
sys.path.insert(0,str(K/'tools'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def unchanged(plan):
 assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
 assert all(sha(E/r)==v for r,v in json.loads((H/'SOURCE-PINS.json').read_bytes()).items())
 assert all(sha(r['target'])==r['before_sha256'] and sha(r['after']['path'])==r['after']['sha256'] for r in plan['files'])
def main():
 plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());unchanged(plan)
 import world_builder_engine.world_layout_preview as original
 from world_builder_engine.pipeline import latest_preview
 job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';previous=latest_preview(job)
 old=original.verify_preview(previous['manifest_path'],previous['manifest_sha256'])
 assert not R.exists();R.mkdir(parents=True)
 for name in ('world_layout_preview.py','index.html','style.css','viewer.mjs','walk_controller.mjs','horizontal_navigation.mjs','preflight.mjs'):
  source=C/name if (C/name).exists() else E/name;shutil.copyfile(source,R/name)
 module=load('world_builder_engine.world_layout_preview',R/'world_layout_preview.py');module.THREE_BUILD=original.THREE_BUILD
 inputs=old['inputs'];prepared=module.create_preview(inputs['geometry_source']['path'],inputs['research_packet']['path'],inputs['blueprint']['path'])
 manifest=module.verify_preview(prepared['manifest_path'],prepared['manifest_sha256'])
 repeated=module.create_preview(inputs['geometry_source']['path'],inputs['research_packet']['path'],inputs['blueprint']['path'])
 assert repeated['reused'] and repeated['manifest_sha256']==prepared['manifest_sha256']
 assert manifest['presentation_setting']==json.loads((H/'ACTUAL-PRESENTATION.json').read_bytes())
 prior=json.loads((H.parent/'world-observation-exclusion-055/PREVIEW-PREPARATION.json').read_bytes())
 prior_manifest=json.loads(Path(prior['current']['manifest_path']).read_bytes())
 assert manifest['presentation_source_brief']==prior_manifest['presentation_source_brief']
 assert manifest['presentation_setting']==prior_manifest['presentation_setting']
 assert [name for name,row in prior_manifest['source_pins'].items() if manifest['source_pins'][name]['sha256']!=row['sha256']]==['viewer.mjs']
 api=load('world_builder_engine.layout_package_export056',C/'layout_package_export.py');api.PROJECT=K
 checked=api.inspect_selected_layout(job,preview_binding=prepared)
 assert checked['presentation']==manifest['presentation_setting'];assert checked['eligibility']['eligibility_only'] is True
 held=[]
 for kind in ('setting','brief','drop_binding'):
  damaged=copy.deepcopy(manifest)
  if kind=='setting':damaged['presentation_setting']['setting']='unspecified'
  elif kind=='brief':damaged['presentation_source_brief']['prompt']='Build an original Mars base. Do not show a landscape beyond the window.'
  else:del damaged['presentation_setting'];del damaged['presentation_source_brief']
  try:module.verify_presentation(damaged)
  except module.PreviewError:held.append(kind)
  else:raise AssertionError('Corrupted immutable binding accepted: '+kind)
 # Verify legacy compatibility at the intended path, without replacing canonical bytes.
 future=load('candidate056_legacy_check',C/'world_layout_preview.py');native_binding=future.binding;code=(C/'world_layout_preview.py').read_bytes()
 def future_binding(path):
  if Path(path)==E/'world_layout_preview.py':return {'path':str(path),'bytes':len(code),'sha256':hashlib.sha256(code).hexdigest()}
  return native_binding(path)
 future.ROOT=E;future.NAVIGATION=E/'horizontal_navigation.mjs';future.THREE_BUILD=original.THREE_BUILD;future.__file__=str(E/'world_layout_preview.py');future.binding=future_binding
 assert future.verify_preview(previous['manifest_path'],previous['manifest_sha256'])==old
 sys.modules['world_builder_engine.world_layout_preview']=original
 assert latest_preview(job)==previous;original.verify_preview(previous['manifest_path'],previous['manifest_sha256']);unchanged(plan)
 binding={'status':'NATIVE_REVIEW_PENDING_NOT_INSTALL_AUTHORIZATION','install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'source_diff_sha256':sha(H/'SOURCE.diff'),
  'candidate_backend_sha256':sha(C/'world_layout_preview.py'),'preview_manifest_path':prepared['manifest_path'],'preview_manifest_sha256':prepared['manifest_sha256'],
  'job_id':manifest['presentation_setting']['source']['job_id'],'presentation_setting':manifest['presentation_setting']}
 put(H/'installation/REVIEW-BINDING.json',binding)
 put(H/'PREVIEW-PREPARATION.json',{'status':'056_ISOLATED_IMMUTABLE_PREVIEW_READY_NATIVE_REVIEW_PENDING','current':prepared,'previous':previous,'reuse_verified':True,
  'actual_original_brief_and_presentation_identical_to055':True,'only_viewer_pin_changed_from055':True,'selected_job_export_eligibility_passed':True,
  'actual_export_repeated':False,'scope':'Only reveal mesh dimensions and matching source pin change from055. Actual brief/setting and geometry remain exact055. No GLB export or native visual test is claimed.',
  'tamper_cases_held':held,'legacy_compatibility_verified_read_only_simulation':True,'protected_originals_unchanged':len(plan['protected_inputs']),
  'canonical_unchanged':True,'pointer_unchanged':True,'server_ui_model_gpu_actions':0,'visual_or_owner_approval':False})
 print(json.dumps({'status':'056_REVIEW_PREVIEW_READY','manifest_sha256':prepared['manifest_sha256'],'setting':checked['presentation']['setting'],'protected_originals':len(plan['protected_inputs'])}))
if __name__=='__main__':main()
