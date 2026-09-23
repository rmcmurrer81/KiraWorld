"""Root-authorized isolated candidate preview and real CPU export; no installation."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
import psutil
H=Path(__file__).resolve().parent;K=Path('@kira_root');E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine';O=H/'actual-001';R=H/'runtime_context/tools/world_builder_engine'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def originals(plan):
 assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
 assert all(sha(E/r)==v for r,v in json.loads((H/'SOURCE-PINS.json').read_bytes()).items())
 assert all(sha(r['target'])==r['before_sha256'] and sha(r['after']['path'])==r['after']['sha256'] for r in plan['files'])
def child():
 import world_builder_engine.world_layout_preview as installed_preview
 from world_builder_engine.pipeline import latest_preview
 job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392';previous=latest_preview(job)
 old=installed_preview.verify_preview(previous['manifest_path'],previous['manifest_sha256'])
 assert not R.exists();R.mkdir(parents=True)
 context={}
 for name in ('world_layout_preview.py','index.html','style.css','viewer.mjs','walk_controller.mjs','horizontal_navigation.mjs','preflight.mjs'):
  source=C/name if name in ('viewer.mjs','walk_controller.mjs') else E/name;shutil.copyfile(source,R/name);context[name]={'sha256':sha(source),'source':str(source)}
 preview=load('world_builder_engine.world_layout_preview',R/'world_layout_preview.py')
 preview.THREE_BUILD=installed_preview.THREE_BUILD
 assert sha(R/'world_layout_preview.py')==sha(E/'world_layout_preview.py')
 i=old['inputs'];prepared=preview.create_preview(i['geometry_source']['path'],i['research_packet']['path'],i['blueprint']['path'])
 frozen=preview.verify_preview(prepared['manifest_path'],prepared['manifest_sha256'])
 repeat=preview.create_preview(i['geometry_source']['path'],i['research_packet']['path'],i['blueprint']['path'])
 assert repeat['reused'] is True and repeat['manifest_sha256']==prepared['manifest_sha256']
 assert all(frozen['source_pins'][name]['sha256']==sha(C/name) for name in ('viewer.mjs','walk_controller.mjs'))
 for key,row in i.items():
  if key in ('geometry_source','research_packet','blueprint') or key.startswith('research_cache_'):assert frozen['inputs'][key]==row
 put(O/'PREVIEW-RESULT.json',{'status':'ISOLATED_IMMUTABLE051_PREVIEW_CREATED','current':prepared,'context':context,'backend_bytes_identical_to_installed':True,'renderer_sha256':sha(C/'viewer.mjs'),'preview_server_or_ui_started':False,'new_immutable_preview_reused_on_repeat':True,'previous_pointer':previous})
 api=load('world_builder_engine.layout_package_export051',C/'layout_package_export.py');api.PROJECT=K
 assert api.verify_preview is preview.verify_preview
 result=api.export_saved_layout_package(job,O/'package',preview_binding={'manifest_path':prepared['manifest_path'],'manifest_sha256':prepared['manifest_sha256']})
 put(O/'API-RESULT.json',{'result':result,'installed':False,'candidate_api_sha256':sha(C/'layout_package_export.py')})
 assert result['status']=='created',result
 sys.modules['world_builder_engine.world_layout_preview']=installed_preview
 assert latest_preview(job)==previous
 installed_preview.verify_preview(previous['manifest_path'],previous['manifest_sha256'])
 print(json.dumps({'status':'051_ISOLATED_REAL_CPU_EXPORT_CREATED','preview_manifest_sha256':prepared['manifest_sha256']}))
def main():
 if '--child' in sys.argv:return child()
 plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());assert sha(H/'INSTALL-PLAN.json')=='acc62a7e35915eaf62ce3914b04f0cc14f144285f00c701fa1f7a11edc2d435c';originals(plan)
 assert not O.exists();O.mkdir();peak=0;samples=0;processes={}
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
    raise RuntimeError('Owned export exceeded bounded CPU resources')
   time.sleep(.01)
  elapsed=time.perf_counter()-started
 originals(plan);assert proc.returncode==0,(O/'stderr.log').read_text(encoding='utf-8')
 package=O/'package';manifest=json.loads((package/'manifest.json').read_bytes());report=json.loads((package/'ROUNDTRIP.json').read_bytes())
 assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS' and report['glb_sha256']==sha(package/'scene.glb')
 assert report['checks']['airlock_pair_metadata_preserved'] is True
 assert report['checks']['airlock_pairs']==manifest['airlock_pair_policy']
 for name,pin in manifest['files'].items():assert sha(package/name)==pin['sha256'] and (package/name).stat().st_size==pin['bytes']
 result={'status':'051_ACTUAL_CPU_GLB_EXPORT_IMPORT_PASS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'installed':False,'elapsed_seconds':elapsed,'sampled_family_peak_rss_bytes':peak,'samples':samples,'processes':processes,
  'sample_interval_seconds':.01,'sampling_limit':'Supervisor excluded; transient peaks may be missed.','package_manifest_sha256':sha(package/'manifest.json'),'glb_sha256':sha(package/'scene.glb'),'glb_bytes':(package/'scene.glb').stat().st_size,
  'counts':report['counts'],'actual_importer_checks':report['checks'],'protected_original_files_unchanged':len(plan['protected_inputs']),'canonical_unchanged':True,'saved_pointer_unchanged':True,'native_ui_gpu_models':0,'visual_or_owner_approval':False}
 put(H/'ACTUAL-EXPORT-RESULT.json',result);print(json.dumps({k:result[k] for k in ('status','elapsed_seconds','sampled_family_peak_rss_bytes','glb_sha256','glb_bytes','canonical_unchanged')}))
if __name__=='__main__':main()
