"""Package the negative performance result; never promote this candidate."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

H=Path(__file__).resolve().parent
W=H.parent.parent
P=H/'portable-backup-001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(obj,indent=2)+'\n')
plan=read(H/'PLAN.json')
assert all(sha(Path(r['path']))==r['sha256'] for r in plan['sources'])
first=read(H/'PAIRED-RESULT.json');reverse=read(H/'reversed-pilot-001/PAIRED-RESULT.json')
assert first['rows']==reverse['rows'] and first['hold'] is None and reverse['hold'] is None
mutation=read(H/'MUTATION-EQUIVALENCE.json')
assert mutation['status']=='PASS_EXACT020_VS019_MUTATION_EQUIVALENCE'
times=[{'order':order,'candidate020_ms':r['candidate020_ms'],'predecessor019_ms':r['predecessor019_ms'],'runtime_increase_percent':100*(r['candidate020_ms']/r['predecessor019_ms']-1)} for order,r in [('candidate first',first),('predecessor first',reverse)]]
assessment={'status':'BEHAVIOR_EQUIVALENT_PERFORMANCE_REGRESSION_HOLD','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'only_change':'Temporary finite-check array and per-primitive reduce callback replaced by direct finite checks and a loop. All observation calls and certificates retained.','helper_sha256':sha(H/'candidate/finite_top_domain.mjs'),'mutation_cases':mutation['cases'],'mutation_steps':mutation['mutation_steps'],'query_comparisons':mutation['query_comparisons'],'domain_groups':20,'tiny_frames':33,'paired_frames_each_per_order':12,'all_state_history_and_certificates_exact_each_frame':True,'physical_observations_exact_across_orders':True,'timings':times,'source_inputs_unchanged':True,'installed':False,'gpu_jobs':0,'decision':'Hold020; keep019 as the better isolated candidate. The slower source is preserved as negative evidence, not installed.','next':'Obtain actual visual evidence through a disposable copy of the existing local World preview. Investigate remaining observation cost only with measurements; do not weaken finite checks or skip mutations.','limits':['Only two short opposite-order mixed runs; no universal benchmark claim.','No long020 trajectory is justified by this performance regression.','Numerical equivalence is not complete collision, calibrated material, visual or installation approval.']}
write(H/'ASSESSMENT.json',assessment)
P.mkdir(exist_ok=False)
mapping={};entries=[]
def redact(t):
 for value,alias in [(str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')]:t=t.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
 return t
def put(source,relative,transform=None):
 dest=P/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 if transform:dest.write_text(transform(source.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
 else:shutil.copy2(source,dest)
 mapping[str(source.resolve())]=relative
 entries.append({'source':source.relative_to(W).as_posix(),'original_sha256':sha(source),'backup_path':relative,'backup_sha256':sha(dest),'transformed':bool(transform)})
for folder in ['candidate','baseline']:
 for f in sorted((H/folder).glob('*.mjs')):put(f,folder+'/'+f.name)
for f in sorted((H.parent/'world-finite-key-candidate-019/candidate').glob('*.mjs')):put(f,'reference019/candidate/'+f.name)
put(H.parent/'world-finite-top-domain-candidate-016/candidate/finite_top_domain.mjs','reference016/candidate/finite_top_domain.mjs')
put(Path(plan['fixture']['path']),'fixtures/wide.json')
def script_transform(t):return t.replace('../world-finite-key-candidate-019/','./reference019/').replace('../world-finite-top-domain-candidate-016/','./reference016/').replace('../world-frame-contact-perf-candidate/fixtures/','./fixtures/')
for f in sorted(H.glob('check_*.mjs')):put(f,f.name,script_transform)
def runner_transform(t):
 t=t.replace('import psutil','import psutil,shutil\nnode=shutil.which("node");assert node,"Node.js must be on PATH"')
 t=t.replace('H=Path(__file__).resolve().parent','H=Path(__file__).resolve().parent\nos.chdir(H)')
 t=t.replace("['C:/Program Files/nodejs/node.exe',","[node,").replace('creationflags=subprocess.CREATE_NO_WINDOW','creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)')
 return t.replace('owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)','owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS) if hasattr(psutil,"BELOW_NORMAL_PRIORITY_CLASS") else None')
put(H/'run_checks.py','run_checks.py',runner_transform)
R=H/'reversed-pilot-001'
put(R/'check_paired.mjs','reversed-pilot-001/check_paired.mjs',lambda t:t.replace('../../world-finite-key-candidate-019/','../reference019/'))
put(R/'run_checks.py','reversed-pilot-001/run_checks.py',runner_transform)
for local,target in [(H,P),(R,P/'reversed-pilot-001')]:
 pp=read(local/'PLAN.json')
 for row in pp['sources']:
  dest=P/mapping[str(Path(row['path']).resolve())]
  row.update(path=os.path.relpath(dest,target).replace('\\','/'),sha256=sha(dest),bytes=dest.stat().st_size)
 pp['fixture']['path']=os.path.relpath(P/'fixtures/wide.json',target).replace('\\','/')
 pp['status']='PORTABLE_NEGATIVE_RESULT_REPRODUCTION_PLAN_NOT_EXECUTED'
 write(target/'PLAN.json',pp)
for local,prefix in [(H,'evidence'),(R,'evidence/reversed-pilot-001')]:
 for f in sorted(local.iterdir()):
  if f.is_file():put(f,prefix+'/'+f.name,redact)
(P/'README.md').write_text('''# World020 observation allocation experiment — HELD

This experiment removed two temporary allocations while preserving all position
observations, finite checks, adjacency order, counters and certificate updates.
140 deterministic mutation cases, 20 domain groups, 33 tiny frames and two
opposite-order 12+12-frame comparisons matched019 exactly in recorded state.

Runtime INCREASED by 9.0–10.5% in these short pilots. The experiment is held;
019 remains the better isolated candidate and015 remains installed. This
negative result is backed up so it will not be mistaken for an untried speedup.
No long020 trajectory, visual pass or canonical installation is claimed.

Source/fixture bytes are preserved. Recorded evidence has local identity paths
redacted with hash mappings in BACKUP-MANIFEST.json. Portable imports and plans
were adapted and checked statically; no duplicate packaged replay was launched.
For reproduction in a fresh package with Node.js and Python plus psutil, run
`python run_checks.py mutations`, then `domain`, `release`, `paired`, followed by
`python reversed-pilot-001/run_checks.py paired`. Preserve consumed outputs.
Each process retains a 384MiB heap, 512MiB RSS and 30-second supervisor limit.
''',encoding='utf-8')
files=[f for f in sorted(P.rglob('*')) if f.is_file()]
for f in files:assert Path.home().name.lower() not in f.read_text(encoding='utf-8').lower(),f
for f in sorted(P.rglob('*.mjs')):
 if 'evidence' not in f.parts:subprocess.run(['C:/Program Files/nodejs/node.exe','--check',str(f)],check=True,capture_output=True)
for f in [P/'run_checks.py',P/'reversed-pilot-001/run_checks.py']:compile(f.read_text(encoding='utf-8'),str(f),'exec')
for d in [P,P/'reversed-pilot-001']:
 pp=read(d/'PLAN.json');assert all(sha(d/r['path'])==r['sha256'] for r in pp['sources'])
manifest={'status':'PORTABLE020_BEHAVIOR_EQUIVALENT_PERFORMANCE_REGRESSION_HOLD','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'entries':entries,'files':[{'path':f.relative_to(P).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size} for f in files],'identity_paths_redacted':True,'portable_replay_executed':False,'static_plan_hash_and_syntax_checks_passed':True}
write(P/'BACKUP-MANIFEST.json',manifest)
print(json.dumps({'directory':str(P),'manifest_sha256':sha(P/'BACKUP-MANIFEST.json'),'file_count':len(files)+1,'assessment_sha256':sha(H/'ASSESSMENT.json'),'timings':times}))
