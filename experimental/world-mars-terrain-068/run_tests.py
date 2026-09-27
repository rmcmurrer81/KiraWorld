"""Bounded CPU-only Node tests/export, never a renderer/server/model."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
import psutil
P=Path(__file__).resolve().parent;W=P.parent;K=Path.home()/'Kira'
node=Path('C:/Program Files/nodejs/node.exe')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snapshot(root):return {str(p):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in {'.py','.mjs','.json','.html','.css'} and '__pycache__' not in p.parts}
run=sys.argv[1] if len(sys.argv)==2 else 'cpu-001'
assert run.startswith('cpu-') and run.replace('-','').isalnum()
out=P/run;assert not out.exists();out.mkdir()
for p in psutil.process_iter(['pid','name','cmdline']):
 if 'node' in (p.info['name'] or '').lower():
  cmd=' '.join(p.info['cmdline'] or [])
  assert not any(s in cmd for s in ['build_glb.mjs','test_terrain.mjs','world-combined-export-063']),f'Duplicate exporter/test PID{p.pid}'
assert psutil.virtual_memory().available>=5*1024**3,'5GiB free admission'
protected=snapshot(K/'tools/world_builder_engine')
protected.update(snapshot(W/'world-mars-displays-067'))
protected.update(snapshot(W/'world-mars-displays-preview-067-v3'))
inputs={str(p.relative_to(P)):sha(p) for p in [P/'test_terrain.mjs',P/'run_tests.py',P/'mars_exterior.mjs',P/'synthetic-layout.json',*sorted((P/'candidate').rglob('*.mjs'))]}
started=time.monotonic();reason=None;peak=0;minimum=psutil.virtual_memory().available;observed={}
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr,(out/'RESOURCES.jsonl').open('x',encoding='utf-8') as trace:
 proc=subprocess.Popen([str(node),'--test','--test-concurrency=1',str(P/'test_terrain.mjs')],cwd=str(P),stdout=stdout,stderr=stderr,env={**os.environ,'TERRAIN_EVIDENCE_DIR':str(out)},creationflags=subprocess.CREATE_NO_WINDOW)
 parent=psutil.Process(proc.pid);observed[proc.pid]=parent.create_time()
 while True:
  rss=0;live=[]
  for pid,born in list(observed.items()):
   try:
    p=psutil.Process(pid)
    if p.create_time()!=born:continue
    for child in p.children(recursive=True):observed[child.pid]=child.create_time()
    rss+=p.memory_info().rss;live.append(pid)
   except psutil.NoSuchProcess:pass
  free=psutil.virtual_memory().available;elapsed=time.monotonic()-started;peak=max(peak,rss);minimum=min(minimum,free)
  trace.write(json.dumps({'seconds':elapsed,'rss':rss,'available':free,'owned_pids':live})+'\n')
  if rss>1024**3 or free<3*1024**3 or elapsed>90:
   reason='CPU test exceeded1GiB RSS/3GiB reserve/90seconds'
   for pid,born in reversed(list(observed.items())):
    try:
     p=psutil.Process(pid)
     if p.create_time()==born:p.kill()
    except psutil.NoSuchProcess:pass
   break
  if proc.poll() is not None and not live:break
  time.sleep(.02)
 code=proc.wait(timeout=5)
remaining=[]
for pid,born in observed.items():
 try:
  if psutil.Process(pid).create_time()==born:remaining.append(pid)
 except psutil.NoSuchProcess:pass
unchanged=all(sha(p)==h for p,h in protected.items());assert unchanged
assert all(sha(P/p)==h for p,h in inputs.items()),'Tested source changed during CPU run'
result={'status':'PASS' if code==0 and reason is None and not remaining else 'FAILED','exit_code':code,'reason':reason,'elapsed_seconds':time.monotonic()-started,'sampled_peak_rss_bytes':peak,'minimum_available_bytes':minimum,'rss_cap_bytes':1024**3,'ram_reserve_bytes':3*1024**3,'deadline_seconds':90,'owned_identities':observed,'remaining_owned_pids':remaining,'protected_source_files_unchanged':len(protected),'canonical_or_owner_writes':False,'render_or_UI_or_model_calls':0,'visual_approval':False,'sample_limit':'20ms sampling can miss transient peaks'}
result['tested_sources']=inputs
(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));sys.exit(0 if result['status']=='PASS' else 1)
