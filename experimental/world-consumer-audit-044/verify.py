from pathlib import Path
import datetime,hashlib,json,subprocess,time
import psutil
H=Path(__file__).resolve().parent;C=H/'candidate';W=H.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(name,v):
 with (H/name).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
plan=json.loads((W/'world-bunk-detail-042/INSTALL-PLAN.json').read_bytes())
baseline=json.loads((W/'world-package-consumer-043/SOURCE-CLOSURE.json').read_bytes())
def preserved():
 assert len(plan['protected_inputs'])==116 and all(sha(p)==s for p,s in plan['protected_inputs'].items())
 assert all(sha(r['target'])==r['after']['sha256'] for r in plan['files'])
 assert all(sha(W/'world-package-consumer-043'/p)==pin['sha256'] for p,pin in baseline['files'].items())
 for name in ['runtime.mjs','horizontal_navigation.mjs','file_admission.mjs','index.html','serve.py']:
  assert sha(C/name)==sha(W/'world-package-consumer-043'/name)
 for p in (C/'sample-package').iterdir():assert sha(p)==sha(W/'world-package-consumer-043/sample-package'/p.name)
preserved()
canvas=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas'
cmd=['C:/Program Files/nodejs/node.exe',str(C/'test_import.mjs'),str(canvas),str(H/'ACTUAL-IMPORT-PASS.json')]
peak=0;samples=0;processes={};failure=None
with (H/'import.stdout.log').open('xb') as out,(H/'import.stderr.log').open('xb') as err:
 start=time.perf_counter();proc=subprocess.Popen(cmd,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW);owner=psutil.Process(proc.pid)
 while proc.poll() is None:
  try:family=[owner,*owner.children(recursive=True)]
  except psutil.NoSuchProcess:family=[]
  rss=0
  for p in family:
   try:
    m=p.memory_info();rss+=m.rss;row=processes.setdefault(str(p.pid),{'name':p.name(),'observed_rss':0,'os_peak_working_set':0});row['observed_rss']=max(row['observed_rss'],m.rss);row['os_peak_working_set']=max(row['os_peak_working_set'],getattr(m,'peak_wset',m.rss))
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  peak=max(peak,rss);samples+=1
  if rss>1024**3 or time.perf_counter()-start>30:
   failure='Owned importer exceeded 1GiB/30 seconds'
   for p in reversed(family):
    try:p.terminate()
    except psutil.NoSuchProcess:pass
   break
  time.sleep(.01)
 proc.wait(timeout=5);elapsed=time.perf_counter()-start
preserved()
put('CHECK-RESULT.json',{'status':'PASS' if not failure and proc.returncode==0 else 'HELD','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'returncode':proc.returncode,'failure':failure,'elapsed_seconds':elapsed,'sampled_family_peak_rss_bytes':peak,'samples':samples,'processes':processes,
 'protected_originals_unchanged':116,'canonical_five_unchanged':True,'frozen043_closure_unchanged':True,'physics_navigation_file_admission_index_server_unchanged':True,'derived_sample_package_unchanged':True,
 'gpu_models_servers_ui':0,'measurement_limit':'10ms sampled owned process-family RSS; supervisor excluded; brief peaks may be missed.','visual_or_owner_approval':False})
assert proc.returncode==0 and not failure,(H/'import.stderr.log').read_text(encoding='utf-8')
print(json.dumps({'status':'PASS','seconds':elapsed,'peak_rss_bytes':peak,'protected_originals':116}))
