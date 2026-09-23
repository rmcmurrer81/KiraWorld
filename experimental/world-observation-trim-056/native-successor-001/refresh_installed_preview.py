"""Use the installed refresh API once, then prove reuse; no browser or export."""
from pathlib import Path
import hashlib,json,sys,time
H=Path(__file__).resolve().parent;K=Path('@kira_root');sys.path.insert(0,str(K/'tools'));sys.dont_write_bytecode=True
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 out=H/'installed-preview-001';assert not out.exists();out.mkdir()
 plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());installed=json.loads((H/'INSTALLED.json').read_bytes())
 assert installed['status']=='056_EXACT_SEVEN_FILE_INSTALL_PASS'
 assert installed['install_plan_sha256']==sha(H/'INSTALL-PLAN.json')
 def unchanged():
  assert all(sha(p)==s for p,s in plan['protected_inputs'].items())
  assert all(sha(r['target'])==r['after']['sha256'] for r in plan['files'])
 unchanged()
 from world_builder_engine.pipeline import latest_preview
 from world_builder_engine.world_layout_preview import verify_preview
 from world_builder_engine.preview_refresh import refresh_saved_preview
 from world_builder_engine.layout_package_export import inspect_selected_layout
 job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392'
 prior=latest_preview(job);old=verify_preview(prior['manifest_path'],prior['manifest_sha256']);oldroot=Path(prior['manifest_path']).parent
 oldfiles={str(p):sha(p) for p in oldroot.rglob('*') if p.is_file()}
 started=time.monotonic();current=refresh_saved_preview(job);manifest=verify_preview(current['manifest_path'],current['manifest_sha256'])
 assert current['presentation_refreshed'] and current['model_jobs']==0 and current['saved_layout_state_modified'] is False
 repeated=refresh_saved_preview(job);assert repeated['reused'] and repeated['manifest_sha256']==current['manifest_sha256']
 assert latest_preview(job)==prior and verify_preview(prior['manifest_path'],prior['manifest_sha256'])==old
 assert all(sha(p)==s for p,s in oldfiles.items())
 checked=inspect_selected_layout(job,preview_binding=current);assert checked['eligibility']['eligibility_only'] is True
 assert manifest['presentation_setting']==json.loads((H/'installation/REVIEW-BINDING.json').read_bytes())['presentation_setting']
 assert manifest['source_pins']['viewer.mjs']['sha256']==sha(K/'tools/world_builder_engine/viewer.mjs')
 unchanged()
 receipt={'status':'INSTALLED056_CANONICAL_IMMUTABLE_PREVIEW_REFRESH_PASS','seconds':time.monotonic()-started,
  'current':current,'previous':prior,'reused_on_second_call':True,'selected_job_pointer_unchanged':True,
  'previous_preview_files_unchanged':len(oldfiles),'protected_originals_unchanged':len(plan['protected_inputs']),
  'installed_seven_files_unchanged':True,'selected_source_export_eligibility_passed':True,
  'presentation':manifest['presentation_setting'],'raw_brief_or_geometry_in_receipt':False,
  'browser_GPU_models_exports':0,'new_native_visual_review':False,'owner_approval':False}
 with (out/'REFRESH-RESULT.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps({'status':receipt['status'],'manifest_sha256':current['manifest_sha256'],'reused_second':True,'old_preview_files_unchanged':len(oldfiles),'protected':len(plan['protected_inputs']),'seconds':receipt['seconds']}))
if __name__=='__main__':main()
