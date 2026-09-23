from pathlib import Path
import datetime,hashlib,json,sys
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
from world_builder_engine.world_layout_preview import verify_preview
from world_builder_engine.pipeline import latest_preview
from world_builder_engine.preview_refresh import refresh_saved_preview
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());installed=json.loads((H/'INSTALLED.json').read_bytes());refresh=json.loads((H/'ROOT-API-PREVIEW-RESULT.json').read_bytes())
assert installed['install_plan_sha256']==sha(H/'INSTALL-PLAN.json')
assert all(sha(row['target'])==row['after']['sha256'] for row in plan['files'])
assert all(sha(p)==value for p,value in plan['protected_inputs'].items())
proof=[]
bindings=[refresh['previous'],refresh['current'],{'manifest_path':str(K/'Data/world_layout_previews/layout-40b38c14f718490a13b88a87/manifest.json'),
 'manifest_sha256':'67a54c4362c46b64d27a5d362defef878796b357adfb092d1827b3d25832a301'}]
for bound in bindings:
 verify_preview(bound['manifest_path'],bound['manifest_sha256']);proof.append({'build_id':Path(bound['manifest_path']).parent.name,'manifest_sha256':bound['manifest_sha256'],'verified':True})
assert latest_preview(Path(refresh['job']))==refresh['previous']
repeat=refresh_saved_preview(refresh['job']);assert repeat['reused'] is True and repeat['manifest_sha256']==refresh['current']['manifest_sha256']
assert latest_preview(Path(refresh['job']))==refresh['previous']
assert all(sha(p)==value for p,value in plan['protected_inputs'].items())
folder=W/'world-package-real-api-039-001/actual-package-001';report=json.loads((folder/'ROUNDTRIP.json').read_bytes());manifest=json.loads((folder/'manifest.json').read_bytes())
assert report['checks']['airlock_pair_metadata_preserved'] is True and len(report['checks']['airlock_pairs'])==1
assert report['checks']['airlock_pairs']==manifest['airlock_pair_policy']
result={'status':'039_INSTALLED_API_REFRESH_AND_REAL_EXPORT_VERIFIED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'installed':True,'installed_files':23,'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'install_receipt_sha256':sha(H/'INSTALLED.json'),
 'preview_verification':proof,'current_preview_reused_on_second_refresh':True,'saved_job_pointer_unchanged':True,
 'real_package_manifest_sha256':sha(folder/'manifest.json'),'real_glb_sha256':sha(folder/'scene.glb'),'real_glb_bytes':(folder/'scene.glb').stat().st_size,
 'actual_importer_checks':report['checks'],'counts':report['counts'],'protected_original_files_unchanged':len(plan['protected_inputs']),
 'native_ui_review':'PENDING_NO_UI_OPENED','visual_or_owner_approval':False,'gpu_models_browser_ui':0,
 'receipt_correction':'The frozen prepared run_real_api.py labels its local receipt installed:false. That legacy field is superseded here by exact INSTALLED.json and live target hashes. The API export ran after the approved039 installation. No code/plan was rewritten to hide that historical label.',
 'no_pressure_engine_or_vr_runtime':True}
p=H/'ROOT-EXECUTION.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('status','installed_files','current_preview_reused_on_second_refresh','saved_job_pointer_unchanged','protected_original_files_unchanged','native_ui_review')}))
