"""Root-approved installed API-only export at a fresh destination, with RSS sampling."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
import psutil
H=Path(__file__).resolve().parent;K=Path('@kira_root');O=H/'installed-mars-001'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
EXPECTED_PLAN='954b2ca088c46987ad6bb7963c97afff79664ad1f0680ca6d9d7dd5882f9636a'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def check_inputs(plan):
 assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
 assert all(sha(row['target'])==row['after']['sha256'] for row in plan['files'])
def child():
 import world_builder_engine.layout_package_export as api
 assert Path(api.__file__).resolve()==K/'tools/world_builder_engine/layout_package_export.py'
 manifest=K/'Data/world_layout_previews/layout-174d4bddd3f8efcf689c7e40/manifest.json'
 result=api.export_saved_layout_package(K/'Data/world_research_jobs/world_research_c391ffbffc7352612392',O/'package',preview_binding={'manifest_path':str(manifest),'manifest_sha256':'ef58d7b81e37182f86dd22defea9294ccfa4b1696fb7bb3810ca80069b85fe0a'})
 put(O/'API-RESULT.json',{'installed_api_path':str(Path(api.__file__).resolve()),'installed_api_sha256':sha(api.__file__),'result':result,'installed':True})
 assert result['status']=='created',result
 print(json.dumps({'status':result['status'],'installed_api':True}))
def main():
 if '--child' in sys.argv:return child()
 assert sha(H/'INSTALL-PLAN-REV3.json')==EXPECTED_PLAN
 plan=json.loads((H/'INSTALL-PLAN-REV3.json').read_bytes());check_inputs(plan)
 assert not O.exists();O.mkdir()
 from world_builder_engine.pipeline import latest_preview
 from world_builder_engine.world_layout_preview import verify_preview
 job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';pointer=latest_preview(job)
 bound=[pointer,{'manifest_path':str(K/'Data/world_layout_previews/layout-174d4bddd3f8efcf689c7e40/manifest.json'),'manifest_sha256':'ef58d7b81e37182f86dd22defea9294ccfa4b1696fb7bb3810ca80069b85fe0a'},
  {'manifest_path':str(K/'Data/world_layout_previews/layout-40b38c14f718490a13b88a87/manifest.json'),'manifest_sha256':'67a54c4362c46b64d27a5d362defef878796b357adfb092d1827b3d25832a301'}]
 for b in bound:verify_preview(b['manifest_path'],b['manifest_sha256'])
 peak=0;samples=0;processes={}
 with (O/'stdout.log').open('xb') as stdout,(O/'stderr.log').open('xb') as stderr:
  started=time.perf_counter();proc=subprocess.Popen([sys.executable,str(Path(__file__)), '--child'],stdout=stdout,stderr=stderr,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},creationflags=subprocess.CREATE_NO_WINDOW);parent=psutil.Process(proc.pid)
  while proc.poll() is None:
   try:family=[parent,*parent.children(recursive=True)]
   except psutil.NoSuchProcess:family=[]
   rss=0
   for p in family:
    try:
     m=p.memory_info();rss+=m.rss;row=processes.setdefault(str(p.pid),{'name':p.name(),'observed_rss':0,'os_peak_working_set':0});row['observed_rss']=max(row['observed_rss'],m.rss);row['os_peak_working_set']=max(row['os_peak_working_set'],getattr(m,'peak_wset',m.rss))
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
   peak=max(peak,rss);samples+=1
   if rss>1024**3 or time.perf_counter()-started>180:
    for p in reversed(family):
     try:p.terminate()
     except psutil.NoSuchProcess:pass
    raise RuntimeError('Owned export exceeded the approved CPU memory/time envelope')
   time.sleep(.01)
  elapsed=time.perf_counter()-started
 check_inputs(plan);assert latest_preview(job)==pointer
 assert proc.returncode==0,(O/'stderr.log').read_text()
 package=O/'package';manifest=json.loads((package/'manifest.json').read_bytes());report=json.loads((package/'ROUNDTRIP.json').read_bytes())
 assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS'
 assert report['glb_sha256']==sha(package/'scene.glb')
 for name,pin in manifest['files'].items():assert sha(package/name)==pin['sha256'] and (package/name).stat().st_size==pin['bytes']
 assert report['checks']['airlock_pair_metadata_preserved'] is True
 assert report['checks']['airlock_pairs']==manifest['airlock_pair_policy']
 assert manifest['recipe_eligibility']['eligibility_only'] is True
 assert len(manifest['airlock_pair_policy'])==1
 result={'status':'041_REV3_INSTALLED_ACTUAL_API_EXPORT_IMPORT_PASS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'installed':True,'installed_files':5,
  'authorization':'Root approved exact REV3 plan and fresh installed API-only export/import; no UI or models.',
  'install_plan_sha256':EXPECTED_PLAN,'install_receipt_sha256':sha(H/'INSTALLED.json'),'real_package_manifest_sha256':sha(package/'manifest.json'),
  'real_glb_sha256':sha(package/'scene.glb'),'real_glb_bytes':(package/'scene.glb').stat().st_size,'elapsed_seconds':elapsed,
  'sampled_family_peak_rss_bytes':peak,'samples':samples,'sample_interval_seconds':.01,'processes':processes,
  'measurement_scope':'Launched process family only, supervisor excluded; sampled RSS may miss brief peaks.',
  'actual_importer_checks':report['checks'],'counts':report['counts'],'protected_original_files_unchanged':116,'saved_job_pointer_unchanged':True,
  'verified_unchanged_previews':[{'id':Path(b['manifest_path']).parent.name,'manifest_sha256':b['manifest_sha256']} for b in bound],
  'native_ui_review':'PENDING_NO_UI_OPENED','visual_or_owner_approval':False,'gpu_models_browser_ui':0,'no_pressure_engine_or_vr_runtime':True}
 put(H/'ROOT-EXECUTION.json',result)
 print(json.dumps({k:result[k] for k in ('status','elapsed_seconds','sampled_family_peak_rss_bytes','real_glb_sha256','protected_original_files_unchanged','saved_job_pointer_unchanged')}))
if __name__=='__main__':main()
