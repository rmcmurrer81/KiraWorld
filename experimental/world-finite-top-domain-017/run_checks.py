from pathlib import Path
import sys,shutil,subprocess,time,json
import psutil
H=Path(__file__).resolve().parent
mode=sys.argv[1] if len(sys.argv)>1 else 'domain'
scripts={'domain':'check_domain.mjs','release':'check_release.mjs','pilot':'check_full_pilot.mjs','trajectory':'check_full_trajectory.mjs'}
assert mode in scripts
assert mode!='trajectory' or '--run-long' in sys.argv, 'Long trajectory requires explicit --run-long'
node=shutil.which('node');assert node, 'Install Node.js and put node on PATH'
assert psutil.virtual_memory().available>=2*2**30, 'At least2GiB available required'
limit=420 if mode=='trajectory' else 120
receipt=H/(mode+'-portable-supervisor.json');assert not receipt.exists(), 'Preserve existing replay; use a fresh backup copy'
start=time.monotonic();peak=0;reason=None
p=subprocess.Popen([node,'--max-old-space-size=384',str(H/scripts[mode])],cwd=H,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
 owned=psutil.Process(p.pid)
 if hasattr(psutil,'BELOW_NORMAL_PRIORITY_CLASS'):owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
 while p.poll() is None:
  try:peak=max(peak,owned.memory_info().rss)
  except psutil.NoSuchProcess:pass
  if peak>512*2**20 or time.monotonic()-start>limit:reason='RESOURCE_LIMIT';p.kill();break
  time.sleep(.1)
finally:
 if p.poll() is None:p.kill()
 code=p.wait(timeout=5)
 receipt.write_text(json.dumps({'process_exit_code':code,'reason':reason,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':peak,'physics_status':'Read the separate result file; process completion is not physical acceptance.'},indent=2)+'\n')
raise SystemExit(code)
