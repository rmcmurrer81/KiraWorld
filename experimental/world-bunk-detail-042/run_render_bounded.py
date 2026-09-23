from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
import psutil
H=Path(__file__).resolve().parent;P=H/'actual-001/package';O=H/'cpu-review-001';B=Path('C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
assert B.is_file() and not O.exists();O.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source={str(p):sha(p) for p in (P/'scene.glb',P/'scene.json')};peak=0;samples=0;failure=None
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','HIP_VISIBLE_DEVICES':'','ONEAPI_DEVICE_SELECTOR':'*:cpu'}
with (O/'stdout.log').open('xb') as stdout,(O/'stderr.log').open('xb') as stderr:
 started=time.perf_counter();proc=subprocess.Popen([str(B),'--background','--factory-startup','--disable-autoexec','--threads','4','--python',str(H/'render_cpu.py'),'--',str(P/'scene.glb'),str(P/'scene.json'),str(O)],stdout=stdout,stderr=stderr,env=env,creationflags=subprocess.CREATE_NO_WINDOW);parent=psutil.Process(proc.pid)
 while proc.poll() is None:
  try:family=[parent,*parent.children(recursive=True)]
  except psutil.NoSuchProcess:family=[]
  rss=0
  for p in family:
   try:rss+=p.memory_info().rss
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  peak=max(peak,rss);samples+=1
  if rss>2*1024**3 or time.perf_counter()-started>=30:
   failure='memory_limit' if rss>2*1024**3 else 'time_limit'
   for p in reversed(family):
    try:p.kill()
    except psutil.NoSuchProcess:pass
   proc.wait(timeout=5);break
  time.sleep(.02)
 elapsed=time.perf_counter()-started
assert all(sha(p)==v for p,v in source.items())
png=O/'bunk-review.png';okay=not failure and proc.returncode==0 and png.is_file()
report={'status':'HEADLESS_CPU_REVIEW_PNG_CREATED' if okay else 'HEADLESS_CPU_RENDER_HELD','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'returncode':proc.returncode,'failure':failure,'elapsed_seconds':elapsed,'sampled_family_peak_rss_bytes':peak,'samples':samples,'limits':{'seconds':30,'rss_bytes':2*1024**3},'blender_path':str(B),'blender_sha256':sha(B),'source_glb_sha256':source[str(P/'scene.glb')],'png_sha256':sha(png) if png.exists() else None,'native_ui_browser_models':0,'render_device':'CPU','visual_review':'PENDING_ARTIFACT_INSPECTION','source_glb_unchanged':True,'installs':0}
with (H/'CPU-RENDER-RESULT.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report));raise SystemExit(not okay)
