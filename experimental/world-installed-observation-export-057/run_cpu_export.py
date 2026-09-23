"""One root-authorized installed056 CPU export, protected source/preview checks."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
import psutil
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');P=W/'world-observation-trim-056/native-successor-001';O=H/'actual-001'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
def inventory(folder):return {str(p):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def source_check(plan):
 assert all(sha(p)==s for p,s in plan['protected_inputs'].items())
 assert all(sha(r['target'])==r['after']['sha256'] for r in plan['files'])
 for rel,row in json.loads((P/'CANDIDATE-CLOSURE.json').read_bytes()).items():assert sha(K/rel)==row['sha256']
def child():
 from world_builder_engine.pipeline import latest_preview
 from world_builder_engine.world_layout_preview import verify_preview
 from world_builder_engine.layout_package_export import inspect_selected_layout,export_saved_layout_package,verify_dependencies
 job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392'
 refreshed=json.loads((P/'installed-preview-001/REFRESH-RESULT.json').read_bytes());binding=refreshed['current']
 assert binding['manifest_sha256']=='b8c1173842f01d2a39d41c5e8d848eed4aedcc84be458770231c7a75609f440f'
 frozen=verify_preview(binding['manifest_path'],binding['manifest_sha256']);previous=latest_preview(job)
 prepared=inspect_selected_layout(job,preview_binding=binding);verify_dependencies()
 assert prepared['presentation']==refreshed['presentation'] and prepared['eligibility']['eligibility_only']
 result=export_saved_layout_package(job,O/'package',preview_binding=binding)
 put(O/'API-RESULT.json',{'result':result,'installed_api_sha256':sha(K/'tools/world_builder_engine/layout_package_export.py'),
  'preview_manifest_sha256':binding['manifest_sha256'],'presentation':prepared['presentation']})
 assert result['status']=='created',result
 package=json.loads((O/'package/manifest.json').read_bytes());report=json.loads((O/'package/ROUNDTRIP.json').read_bytes())
 assert package['presentation_setting']==report['presentation_setting']==frozen['presentation_setting']
 assert report['status']=='CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS' and report['glb_sha256']==sha(O/'package/scene.glb')
 assert report['checks']['airlock_pair_metadata_preserved'] is True
 assert report['checks']['airlock_pairs']==package['airlock_pair_policy']
 for pair in package['airlock_pair_policy']:assert pair['pressure_simulation'] is False and pair['engine_runtime_included'] is False
 for name,pin in package['files'].items():assert sha(O/'package'/name)==pin['sha256'] and (O/'package'/name).stat().st_size==pin['bytes']
 # Raw brief snapshot is private; minimal setting/digests may be exported.
 prompt=frozen['presentation_source_brief']['prompt'].encode()
 for path in (O/'package').iterdir():
  raw=path.read_bytes();assert prompt not in raw and b'presentation_source_brief' not in raw,path
 assert inspect_selected_layout(job,preview_binding=binding)==prepared and latest_preview(job)==previous
 assert verify_preview(binding['manifest_path'],binding['manifest_sha256'])==frozen
 put(O/'SOURCE-CONSISTENCY.json',{'status':'PASS','selected_job_id':job.name,'preview_manifest_sha256':binding['manifest_sha256'],
  'source_chain_and_presentation_rechecked':True,'selected_pointer_unchanged':True,'exported_raw_brief':False,
  'package_source_digests':package['verified_source_digests'],'counts':report['counts'],
  'pressure_simulation':False,'engine_native_controls':False,'visual_or_owner_approval':False})
 print(json.dumps({'status':'INSTALLED056_CPU_EXPORT_CREATED','glb_sha256':report['glb_sha256']}))
def main():
 if '--child' in sys.argv:return child()
 plan=json.loads((P/'INSTALL-PLAN.json').read_bytes());source_check(plan)
 assert json.loads((P/'INSTALLED.json').read_bytes())['status']=='056_EXACT_SEVEN_FILE_INSTALL_PASS'
 assert psutil.virtual_memory().available>4*1024**3,'Need export budget plus3GiB reserve'
 assert not O.exists();O.mkdir()
 refresh=json.loads((P/'installed-preview-001/REFRESH-RESULT.json').read_bytes())
 protected={}
 for key in ('current','previous'):protected.update(inventory(Path(refresh[key]['manifest_path']).parent))
 for name in ('world-observation-viewport-053','world-observation-setting-054','world-door-targeting-candidate-051'):
  folder=W/name/'actual-001/package'
  if folder.exists():protected.update(inventory(folder))
 put(O/'PROTECTED-DERIVED-FILES.json',{'files':protected,'originals_inventory_sha256':sha(P/'INSTALL-PLAN.json')})
 peak=0;samples=0;owned={};reason=None;started=time.monotonic()
 with (O/'stdout.log').open('xb') as stdout,(O/'stderr.log').open('xb') as stderr,(O/'RESOURCES.jsonl').open('x',encoding='utf-8') as trace:
  proc=subprocess.Popen([sys.executable,'-B',str(Path(__file__)), '--child'],stdout=stdout,stderr=stderr,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},creationflags=subprocess.CREATE_NO_WINDOW)
  parent=psutil.Process(proc.pid);owned[proc.pid]=parent.create_time()
  while True:
   family=[]
   for pid,born in list(owned.items()):
    try:
     p=psutil.Process(pid)
     if p.create_time()!=born:continue
     family.append(p)
     for q in p.children(recursive=True):
      if q.pid not in owned:owned[q.pid]=q.create_time();family.append(q)
    except (psutil.NoSuchProcess,psutil.AccessDenied):continue
   live={p.pid:p for p in family};rss=0;identities=[]
   for p in live.values():
    try:
     m=p.memory_info();rss+=m.rss;identities.append({'pid':p.pid,'create_time':owned[p.pid],'name':p.name(),'rss':m.rss,'os_peak':getattr(m,'peak_wset',m.rss)})
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
   free=psutil.virtual_memory().available;elapsed=time.monotonic()-started;peak=max(peak,rss);samples+=1
   trace.write(json.dumps({'seconds':elapsed,'family_rss':rss,'free_ram':free,'identities':identities})+'\n')
   if rss>.8*1024**3 or free<3*1024**3 or elapsed>180:
    reason='Owned export resource/deadline limit exceeded'
    for pid,born in reversed(list(owned.items())):
     try:
      p=psutil.Process(pid)
      if p.create_time()==born:p.kill()
     except psutil.NoSuchProcess:pass
    proc.wait(timeout=5);break
   if proc.poll() is not None and not live:break
   time.sleep(.01)
  proc.wait(timeout=5)
 remaining=[]
 for pid,born in owned.items():
  try:
   if psutil.Process(pid).create_time()==born:remaining.append(pid)
  except psutil.NoSuchProcess:pass
 source_check(plan);assert all(sha(p)==s for p,s in protected.items())
 result={'status':'INSTALLED056_CPU_EXPORT_PASS' if not reason and proc.returncode==0 and not remaining else 'HELD_CPU_EXPORT',
  'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'elapsed_seconds':time.monotonic()-started,'exit_code':proc.returncode,
  'sampled_family_peak_rss_bytes':peak,'samples':samples,'rss_cap_bytes':int(.8*1024**3),'ram_reserve_bytes':3*1024**3,'deadline_seconds':180,
  'owned_identities':[{'pid':p,'create_time':t} for p,t in owned.items()],'remaining_owned_pids':remaining,'failure':reason,
  'protected_originals_unchanged':116,'previous_derived_files_unchanged':len(protected),'canonical_unchanged':True,
  'native_UI_GPU_models':0,'visual_or_owner_approval':False,'sampling_limit':'Supervisor excluded;10ms sampling can miss transient peaks.'}
 put(H/'SUPERVISOR.json',result);print(json.dumps(result))
 if result['status']!='INSTALLED056_CPU_EXPORT_PASS':raise SystemExit(1)
if __name__=='__main__':main()
