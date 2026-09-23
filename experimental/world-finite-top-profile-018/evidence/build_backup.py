from pathlib import Path
import json,hashlib,shutil,datetime
H=Path(__file__).resolve().parent;W=H.parent.parent;OLD=H.parent/'world-finite-top-domain-candidate-017';P=H/'portable-profile-addon-002'
assert not P.exists();P.mkdir();(P/'profile').mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def redact(t):
 for value,alias in [(str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')]:t=t.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
 return t
entries=[];mapping={}
def put(source,name,transform=None):
 target=P/name;target.parent.mkdir(parents=True,exist_ok=True)
 if transform:target.write_text(transform(source.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
 else:shutil.copy2(source,target)
 mapping[str(source.resolve())]=name
 entries.append({'source':str(source.relative_to(W)).replace('\\','/'),'original_sha256':sha(source),'backup_path':name,'backup_sha256':sha(target),'transformed':bool(transform)})
for folder in ['candidate','baseline']:
 for f in sorted((OLD/folder).glob('*.mjs')):put(f,'reference017/'+folder+'/'+f.name)
put(H.parent/'world-frame-contact-perf-candidate/fixtures/wide.json','fixtures/wide.json')
put(H/'check_full_pilot.mjs','check_full_pilot.mjs',lambda t:t.replace('../world-finite-top-domain-candidate-017/candidate','./reference017/candidate').replace('../world-finite-top-domain-candidate-017/baseline','./reference017/baseline'))
for f in sorted(H.iterdir()):
 if f.is_file():put(f,'evidence/'+f.name,redact)
put(H/'profile/world017.cpuprofile','evidence/world017.redacted.cpuprofile',redact)
plan=json.loads((H/'FULL-PILOT-PLAN.json').read_text())
for r in plan['sources']:
 r['path']=mapping[str(Path(r['path']).resolve())];r['sha256']=sha(P/r['path']);r['bytes']=(P/r['path']).stat().st_size
plan['fixture']['path']='fixtures/wide.json';plan['status']='PORTABLE_PROFILE_PLAN_NOT_EXECUTED'
(P/'FULL-PILOT-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
runner=(H/'run_profile.py').read_text(encoding='utf-8').replace('import psutil','import psutil,shutil\nnode=shutil.which("node");assert node,"Node.js must be on PATH"')
runner=runner.replace("['C:/Program Files/nodejs/node.exe',","[node,").replace('creationflags=subprocess.CREATE_NO_WINDOW','creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)').replace('owned=psutil.Process(proc.pid);owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)','owned=psutil.Process(proc.pid)\n        if hasattr(psutil,"BELOW_NORMAL_PRIORITY_CLASS"):owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)')
# Source paths in the plan are package-relative, so set only this runner's cwd.
runner=runner.replace('H=Path(__file__).resolve().parent','H=Path(__file__).resolve().parent\n__import__("os").chdir(H)')
(P/'run_profile.py').write_text(runner,encoding='utf-8')
(P/'README.md').write_text('''# World018 CPU profile addon — isolated and uninstalled

This is a measurement of the unchanged World017 source. One12+12-frame mixed
candidate/baseline profile preserved all prior per-frame observations exactly.
The helper accounts for49.28% of whole-run sampled self time; no optimization or
speedup was implemented. See evidence/PROFILE-ANALYSIS.json and
evidence/NEXT-OPTIMIZATION.md. World015 remains installed.

Exact source modules and fixture are copied for provenance. Recorded receipts
and the CPU profile are under evidence with local identity paths redacted.
Their embedded hashes describe the original local files; BACKUP-MANIFEST.json
records original and packaged hashes. The profile addon does not modify017's
published portable003 package.

To reproduce in a fresh package, install Node.js on PATH and Python with psutil,
then run `python run_profile.py`. The portable runner retains384MiB heap,
512MiB RSS and30s limits. Existing output/profile files should be preserved.
The portable replay was not executed during packaging; paths, hashes and syntax
were checked statically. Results do not establish finished physics or visual
acceptance, and they do not authorize installation.
''',encoding='utf-8')
files=[f for f in sorted(P.rglob('*')) if f.is_file()]
for f in files:assert Path.home().name.lower() not in f.read_text(encoding='utf-8').lower(),f
manifest={'status':'PORTABLE_PROFILE_ADDON_UNINSTALLED_NO_OPTIMIZATION','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'entries':entries,'files':[{'path':str(f.relative_to(P)).replace('\\','/'),'sha256':sha(f),'bytes':f.stat().st_size} for f in files],'identity_paths_redacted':True,'portable_replay_executed':False}
(P/'BACKUP-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(P),'manifest_sha256':sha(P/'BACKUP-MANIFEST.json'),'files':len(files)}))
