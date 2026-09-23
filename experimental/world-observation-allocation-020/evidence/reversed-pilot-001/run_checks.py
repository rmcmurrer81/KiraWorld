from pathlib import Path
import sys,json,hashlib,time,datetime,subprocess,os
import psutil
H=Path(__file__).resolve().parent
mode=sys.argv[1];assert mode in ['mutations','domain','release','paired']
script=H/('check_'+mode+'.mjs')
label=mode.upper()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((H/'PLAN.json').read_text());assert all(sha(r['path'])==r['sha256'] for r in plan['sources'])
assert not (H/(label+'-SUPERVISOR.json')).exists()
available=psutil.virtual_memory().available;assert available>=2*2**30
competing=[]
for p in psutil.process_iter(['name','cmdline']):
 if p.pid==os.getpid():continue
 name=(p.info['name'] or '').lower();cmd=' '.join(p.info['cmdline'] or [])
 if name in ['python.exe','ffmpeg.exe'] or (name=='node.exe' and 'Codex' not in cmd and 'codex' not in cmd):competing.append({'pid':p.pid,'name':name})
assert not competing,'Competing execution: '+json.dumps(competing)
start=time.monotonic();peak=0;reason=None;code=None;proc=None
try:
 with (H/(mode+'.stdout.txt')).open('x',encoding='utf-8') as out,(H/(mode+'.stderr.txt')).open('x',encoding='utf-8') as err:
  proc=subprocess.Popen(['C:/Program Files/nodejs/node.exe','--max-old-space-size=384',str(script)],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
  owned=psutil.Process(proc.pid);owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
  while proc.poll() is None:
   try:peak=max(peak,owned.memory_info().rss)
   except psutil.NoSuchProcess:pass
   if peak>512*2**20 or time.monotonic()-start>30:reason='512_MIB_RSS_OR_30_SECOND_LIMIT';proc.kill();break
   time.sleep(.05)
  code=proc.wait(timeout=5)
except BaseException as e:reason=repr(e)
finally:
 if proc is not None and proc.poll() is None:proc.kill();proc.wait(timeout=5)
 unchanged=all(sha(r['path'])==r['sha256'] for r in plan['sources'])
 out={'status':'PROCESS_COMPLETED' if code==0 and unchanged else 'HELD_OR_FAILED','mode':mode,'exit_code':code,'reason':reason,'seconds':time.monotonic()-start,'peak_rss_bytes':peak,'heap_mib':384,'rss_mib':512,'wall_seconds':30,'available_at_start_bytes':available,'source_unchanged':unchanged,'owned_node_exited':proc is None or proc.poll() is not None,'installed':False,'gpu_models':0,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (H/(label+'-SUPERVISOR.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
raise SystemExit(0 if out['status']=='PROCESS_COMPLETED' else 1)
