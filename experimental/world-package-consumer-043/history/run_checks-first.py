"""Headless import only, with finite CPU resource bounds and source checks."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
import psutil
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
 with (H/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
plan=json.loads((H.parent/'world-bunk-detail-042/INSTALL-PLAN.json').read_bytes())
protected=plan['protected_inputs'];assert len(protected)==116
assert all(sha(p)==s for p,s in protected.items())
canonical={r['target']:sha(r['target']) for r in plan['files']}
preview=Path('@kira_root/Data/world_layout_previews/layout-4b8661bcb27e70cc774276e5/manifest.json')
preview_sha=sha(preview)
sample={p.name:sha(p) for p in (H/'sample-package').iterdir()}
canvas=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas'
command=['C:/Program Files/nodejs/node.exe',str(H/'test_import.mjs'),str(canvas),str(H/'TEST-IMPORT.json')]
processes={};peak=0;samples=0;failure=None
with (H/'import.stdout.log').open('xb') as out,(H/'import.stderr.log').open('xb') as err:
 start=time.perf_counter();p=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW);owner=psutil.Process(p.pid)
 while p.poll() is None:
  try:family=[owner,*owner.children(recursive=True)]
  except psutil.NoSuchProcess:family=[]
  rss=0
  for proc in family:
   try:
    mem=proc.memory_info();rss+=mem.rss;row=processes.setdefault(str(proc.pid),{'name':proc.name(),'observed_rss':0,'os_peak_working_set':0});row['observed_rss']=max(row['observed_rss'],mem.rss);row['os_peak_working_set']=max(row['os_peak_working_set'],getattr(mem,'peak_wset',mem.rss))
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  peak=max(peak,rss);samples+=1
  if rss>1024**3 or time.perf_counter()-start>30:
   failure='Owned importer exceeded 1GiB/30-second bounds'
   for proc in reversed(family):
    try:proc.terminate()
    except psutil.NoSuchProcess:pass
   break
  time.sleep(.01)
 p.wait(timeout=5);elapsed=time.perf_counter()-start
unchanged=all(sha(p)==s for p,s in protected.items()) and all(sha(p)==s for p,s in canonical.items()) and sha(preview)==preview_sha and all(sha(H/'sample-package'/n)==s for n,s in sample.items())
write('CHECK-RESULT.json',{'status':'PASS' if p.returncode==0 and unchanged and not failure else 'HELD','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'returncode':p.returncode,'failure':failure,'elapsed_seconds':elapsed,'sampled_family_peak_rss_bytes':peak,'samples':samples,'processes':processes,
 'protected_original_files':116,'protected_originals_canonical_five_current_preview_and_sample_unchanged':unchanged,'native_ui_opened':False,'servers_started':0,'models_gpu_calls':0,'visual_or_owner_approval':False,
 'measurement_limit':'Sampled owned process-family RSS may miss brief peaks; Python supervisor excluded.'})
assert p.returncode==0 and unchanged and not failure,(H/'import.stderr.log').read_text(encoding='utf-8')
print(json.dumps({'status':'PASS','seconds':elapsed,'peak_rss_bytes':peak,'unchanged':unchanged}))
