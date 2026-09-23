"""Exercise the installed saved-preview refresh without opening any window."""
from pathlib import Path
import hashlib,json,sys,datetime
H=Path(__file__).resolve().parent
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(row['target'])==row['after']['sha256'] for row in plan['files'])
assert all(sha(path)==digest for path,digest in plan['protected_inputs'].items())
sys.path.insert(0,'@user_home/Kira/tools')
from world_builder_engine.preview_refresh import refresh_saved_preview
from world_builder_engine.world_layout_preview import verify_preview
job=Path('@user_home/Kira/Data/world_research_jobs/world_research_c391ffbffc7352612392')
first=refresh_saved_preview(job)
second=refresh_saved_preview(job)
identity=('manifest_path','manifest_sha256','build_id')
assert all(first[k]==second[k] for k in identity) and second['reused'] is True
manifest=verify_preview(first['manifest_path'],first['manifest_sha256'])
assert all(sha(path)==digest for path,digest in plan['protected_inputs'].items())
receipt={'status':'INSTALLED_REFRESH_AND_REUSE_PASS','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preview':first,'second':second,'saved_original_files_unchanged':len(plan['protected_inputs']),'repeat_reuses_exact_manifest':True,'native_window_tested':False,'model_jobs':0,'visual_approval':False,'test_correction':'Initial harness compared complete replies, including the expected reused flag change. Corrected assertion checks stable manifest identity and second-call reuse.'}
with (H/'ROOT-INSTALLED-API-REVIEW.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'status':receipt['status'],'manifest_path':first['manifest_path'],'same_repeat':True}))
