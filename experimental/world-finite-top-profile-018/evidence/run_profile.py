from pathlib import Path
import hashlib,json,time,datetime,subprocess
import psutil
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((H/'FULL-PILOT-PLAN.json').read_text())
assert all(sha(r['path'])==r['sha256'] for r in plan['sources'])
assert not (H/'PROFILE-SUPERVISOR.json').exists()
available=psutil.virtual_memory().available;assert available>=2*2**30
running=[]
for p in psutil.process_iter(['name','cmdline']):
    if p.pid==__import__('os').getpid():continue
    name=(p.info['name'] or '').lower();cmd=' '.join(p.info['cmdline'] or [])
    if name in ['python.exe','ffmpeg.exe'] or (name=='node.exe' and 'Codex' not in cmd and 'codex' not in cmd):running.append({'pid':p.pid,'name':name,'command':cmd})
assert not running, 'Competing execution found: '+json.dumps(running)
start=time.monotonic();peak=0;reason=None;proc=None;code=None
try:
    with (H/'profile.stdout.txt').open('x',encoding='utf-8') as out,(H/'profile.stderr.txt').open('x',encoding='utf-8') as err:
        proc=subprocess.Popen(['C:/Program Files/nodejs/node.exe','--max-old-space-size=384','--cpu-prof','--cpu-prof-interval=1000','--cpu-prof-dir='+str(H/'profile'),'--cpu-prof-name=world017.cpuprofile',str(H/'check_full_pilot.mjs')],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
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
    result=json.loads((H/'FULL-PILOT-RESULT.json').read_text()) if (H/'FULL-PILOT-RESULT.json').exists() else None
    out={'status':'PROCESS_COMPLETED' if code==0 and unchanged else 'HELD_OR_FAILED','result_status':result['status'] if result else None,'exit_code':code,'reason':reason,'seconds':time.monotonic()-start,'peak_rss_bytes':peak,'available_start_bytes':available,'heap_mib':384,'rss_mib':512,'wall_limit_seconds':30,'cpu_profile_interval_us':1000,'source_unchanged':unchanged,'owned_node_exited':proc is None or proc.poll() is not None,'installed':False,'models_gpu':0,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (H/'PROFILE-SUPERVISOR.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
raise SystemExit(0 if out['status']=='PROCESS_COMPLETED' else 1)
