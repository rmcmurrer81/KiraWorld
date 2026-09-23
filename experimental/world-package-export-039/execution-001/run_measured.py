from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
import psutil
H=Path(__file__).resolve().parent;W=H.parent;SRC=W/'world-package-039';K=Path('@kira_root')
JOB=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392'
MANIFEST=K/'Data/world_layout_previews/layout-174d4bddd3f8efcf689c7e40/manifest.json'
DIGEST='ef58d7b81e37182f86dd22defea9294ccfa4b1696fb7bb3810ca80069b85fe0a'
OUTPUT=H/'actual-package-001'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((SRC/'INSTALL-PLAN.json').read_bytes());protected=plan['protected_inputs']
assert sha(MANIFEST)==DIGEST and not OUTPUT.exists()
assert all(sha(p)==digest for p,digest in protected.items())
assert all(sha(row['after']['path'])==row['after']['sha256'] for row in plan['files'])
canonical={row['target']:sha(row['target']) if Path(row['target']).exists() else None for row in plan['files']}
before_memory=psutil.virtual_memory().available;started=datetime.datetime.now(datetime.UTC).isoformat()
args=['C:/Python314/python.exe',str(SRC/'run_real_api.py'),'--job',str(JOB),'--manifest',str(MANIFEST),'--manifest-sha256',DIGEST,'--output',str(OUTPUT)]
processes={};samples=0;family_peak=0;timed_out=False
with (H/'stdout.log').open('xb') as stdout,(H/'stderr.log').open('xb') as stderr:
 start=time.perf_counter();proc=subprocess.Popen(args,stdout=stdout,stderr=stderr,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},creationflags=subprocess.CREATE_NO_WINDOW)
 root=psutil.Process(proc.pid)
 while proc.poll() is None:
  family=[]
  try:family=[root,*root.children(recursive=True)]
  except psutil.NoSuchProcess:pass
  total=0
  for p in family:
   try:
    m=p.memory_info();rss=m.rss;total+=rss
    row=processes.setdefault(str(p.pid),{'name':p.name(),'max_observed_rss':0,'os_peak_working_set':0})
    row['max_observed_rss']=max(row['max_observed_rss'],rss);row['os_peak_working_set']=max(row['os_peak_working_set'],getattr(m,'peak_wset',rss))
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  family_peak=max(family_peak,total);samples+=1
  if time.perf_counter()-start>180:
   timed_out=True
   for p in reversed(family):
    try:p.terminate()
    except psutil.NoSuchProcess:pass
   break
  time.sleep(.01)
 proc.wait(timeout=10);elapsed=time.perf_counter()-start
assert all(sha(p)==digest for p,digest in protected.items())
assert all((sha(p) if Path(p).exists() else None)==digest for p,digest in canonical.items())
latest=sorted(SRC.glob('REAL-API-RESULT-*.json'),key=lambda p:p.stat().st_mtime_ns)[-1]
api=json.loads(latest.read_bytes())
result={'status':'MEASURED_REAL039_API_EXPORT_PASS' if proc.returncode==0 and api['status']=='REAL_API_EXPORT_PASS' else 'MEASURED_REAL039_API_EXPORT_HELD',
 'started_utc':started,'elapsed_seconds':elapsed,'returncode':proc.returncode,'timed_out':timed_out,
 'process_family_sampled_peak_rss_bytes':family_peak,'sample_interval_seconds':.01,'sample_count':samples,'processes':processes,
 'measurement_limits':'Concurrent family RSS is sampled and may miss a brief peak. Per-process OS peak working set was read while each process existed; the sum is not necessarily concurrent.',
 'available_ram_before_bytes':before_memory,'available_ram_after_bytes':psutil.virtual_memory().available,
 'runner_sha256':sha(SRC/'run_real_api.py'),'selected_manifest_sha256':DIGEST,'api_receipt':str(latest),'api_receipt_sha256':sha(latest),
 'output':str(OUTPUT),'protected_original_files_unchanged':len(protected),'canonical_files_unchanged':True,'installed':True,'models_gpu_browser_native_ui':0}
if (OUTPUT/'manifest.json').is_file():
 result['package_manifest_sha256']=sha(OUTPUT/'manifest.json');result['glb_sha256']=sha(OUTPUT/'scene.glb')
with (H/'MEASURED-RESULT.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result));raise SystemExit(proc.returncode)
