"""Assess existing, consumed checks and prepare a portable additive backup."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

H = Path(__file__).resolve().parent
W = H.parent.parent
OLD = H.parent / 'world-finite-top-domain-candidate-017'
P = H / 'portable-backup-001'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value):
    with p.open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(value, indent=2)+'\n')

plan = read(H/'PLAN.json')
assert all(sha(Path(r['path'])) == r['sha256'] for r in plan['sources'])
first = read(H/'PAIRED-RESULT.json')
reverse = read(H/'reversed-pilot-001/PAIRED-RESULT.json')
assert first['hold'] is None and reverse['hold'] is None
assert first['frames_each'] == reverse['frames_each'] == 12
assert all(r['p_prev_v_all_three_bodies_exact'] and r['all_domain_masks_history_and_primitive_certificates_exact'] for run in [first,reverse] for r in run['rows'])
assert first['rows'] == reverse['rows']
assert read(H/'KEY-EQUIVALENCE.json')['cases'] == 3040
assert read(H/'DOMAIN-TESTS.json')['tests'] == 20
assert read(H/'RELEASE-COMPARISON.json')['status'] == 'PASS_SCOPED_PATCH_COMPARISONS'
times = [{'order': order, 'candidate019_ms': r['candidate019_ms'], 'predecessor017_ms': r['predecessor017_ms'], 'candidate_runtime_reduction_percent': 100*(1-r['candidate019_ms']/r['predecessor017_ms'])} for order,r in [('candidate first',first),('predecessor first',reverse)]]
assessment = {
    'status': 'SCOPED_KEY_EQUIVALENCE_AND_PAIRED_TIMING_PASS_UNINSTALLED',
    'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'only_physics_source_change': 'finite_top_domain.mjs primitive key construction; scalar fast paths for dense one-, two- or three-integer arrays with original fallback',
    'helper_sha256': sha(H/'candidate/finite_top_domain.mjs'),
    'key_cases':3040, 'domain_groups':20, 'tiny_frames':33,
    'paired_full_size_frames_each_per_order':12,
    'exact_every_frame': ['cloth/mattress/pillow p, prev and v bytes','domain last-position bytes and masks','primitive certificates','all counters, metrics and holds'],
    'first_and_reverse_physical_observations_exact': True,
    'measured_timings':times,
    'source_inputs_unchanged':True,
    'installed':False, 'gpu_jobs':0,
    'limits':[
        'Two short opposite-order mixed processes; not a statistical benchmark or a general hardware claim.',
        'Only the first 12 default full-size frames were paired; the 1,110-frame trajectory belongs to predecessor017.',
        'Candidate019 has no long-run, visual, calibrated material, underside/side response or installation approval.',
        'Proxy/getter/species side effects are outside the owned dense-array contract; existing fallback is retained for ordinary other values/types.',
        'World015 and owner worlds were not edited by this isolated work.'
    ],
    'next': 'Isolate allocation removal in observeVertex/mask without changing observation frequency, finite checks, adjacency order, counters, certificates, hold reasons or solver state.'
}
write(H/'ASSESSMENT.json', assessment)
(H/'NEXT-OPTIMIZATION.md').write_text('''# Proposed World020: equivalent observation operations

World019 reduced observed runtime by 18.5–19.6% across two opposite-order short
paired pilots. Every state byte and recorded certificate matched017 per frame.
This is bounded performance evidence, not a long-run or visual acceptance.

The next isolated change can replace `q.ids.reduce(...)` inside observeVertex
with an explicit loop and replace the temporary `[x,y,z]` finite-check array
with three equivalent Number.isFinite calls. Profile018 identified observation
work as the largest sampled hotspot. Keep constructor behavior, call count,
adjacency order, counter increments, EPS, top checks and history updates exact.
Do not cache masks or skip observations: both would require a different proof.

First compare adversarial finite/nonfinite position mutations and every domain
field against019, then run the focused domain/tiny checks and one bounded
opposite-order paired pilot. A measured improvement is required before adding
complexity. If speed does not improve, retain that result and do not promote.
Long-run and visual review remain required before any canonical installation.
''', encoding='utf-8')

P.mkdir(exist_ok=False)
mapping = {}
entries = []
def redact(text):
    for value,alias in [(str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')]:
        text = text.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
    return text
def put(source, relative, transform=None):
    dest = P/relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    if transform:
        dest.write_text(transform(source.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    else:
        shutil.copy2(source,dest)
    mapping[str(source.resolve())] = relative
    entries.append({'source':source.relative_to(W).as_posix(),'original_sha256':sha(source),'backup_path':relative,'backup_sha256':sha(dest),'transformed':bool(transform)})
for name in ['candidate','baseline']:
    for f in sorted((H/name).glob('*.mjs')):put(f,name+'/'+f.name)
for f in sorted((OLD/'candidate').glob('*.mjs')):put(f,'reference017/candidate/'+f.name)
put(H.parent/'world-finite-top-domain-candidate-016/candidate/finite_top_domain.mjs','reference016/candidate/finite_top_domain.mjs')
put(Path(plan['fixture']['path']),'fixtures/wide.json')
def script_transform(text):
    return text.replace('../world-finite-top-domain-candidate-017/','./reference017/').replace('../world-finite-top-domain-candidate-016/','./reference016/').replace('../world-frame-contact-perf-candidate/fixtures/','./fixtures/')
for f in sorted(H.glob('check_*.mjs')):put(f,f.name,script_transform)
def runner_transform(text):
    text=text.replace('import psutil','import psutil,shutil\nnode=shutil.which("node");assert node,"Node.js must be on PATH"')
    text=text.replace('H=Path(__file__).resolve().parent','H=Path(__file__).resolve().parent\nos.chdir(H)')
    text=text.replace("['C:/Program Files/nodejs/node.exe',","[node,").replace('creationflags=subprocess.CREATE_NO_WINDOW','creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)')
    text=text.replace('owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)','owned.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS) if hasattr(psutil,"BELOW_NORMAL_PRIORITY_CLASS") else None')
    return text
put(H/'run_checks.py','run_checks.py',runner_transform)
reverse_dir = H/'reversed-pilot-001'
put(reverse_dir/'check_paired.mjs','reversed-pilot-001/check_paired.mjs',lambda text:text.replace('../../world-finite-top-domain-candidate-017/','../reference017/'))
put(reverse_dir/'run_checks.py','reversed-pilot-001/run_checks.py',runner_transform)
for local, target in [(H,P),(reverse_dir,P/'reversed-pilot-001')]:
    portable=read(local/'PLAN.json')
    for row in portable['sources']:
        dest=P/mapping[str(Path(row['path']).resolve())]
        row.update(path=os.path.relpath(dest,target).replace('\\','/'),sha256=sha(dest),bytes=dest.stat().st_size)
    portable['fixture']['path']=os.path.relpath(P/'fixtures/wide.json',target).replace('\\','/')
    portable['status']='PORTABLE_REPRODUCTION_PLAN_NOT_EXECUTED'
    write(target/'PLAN.json',portable)
for local, prefix in [(H,'evidence'),(reverse_dir,'evidence/reversed-pilot-001')]:
    for f in sorted(local.iterdir()):
        if f.is_file():put(f,prefix+'/'+f.name,redact)
(P/'README.md').write_text('''# World019 key optimization — isolated and uninstalled

Primitive keys for owned one-, two- and three-integer ID arrays use scalar
sorting; other ordinary inputs retain the prior implementation. No observation,
certificate, solver, finite-coordinate check or collision response was removed.

3,040 key cases, 20 domain groups and 33 tiny frames passed. Two independent
12+12-frame full-size comparisons used opposite evaluation orders. All p/prev/v
bytes, certificates, history, masks, counters and metrics matched017 each frame.
Observed runtime was 18.5–19.6% lower than017 in these two short runs. This does
not imply a general benchmark, a 1,110-frame019 pass, or visual/physical approval.
World015 remains installed. No owner files or canonical application were edited.

Recorded local receipts are preserved under evidence with identity paths
redacted; BACKUP-MANIFEST.json maps original and packaged hashes. Candidate and
reference source bytes are exact. Runnable plan paths and import paths were
adapted only for this package; packaged replays were not executed during backup.

With Node.js on PATH and Python plus psutil, use a fresh copy and run
`python run_checks.py keys`, `domain`, `release` and `paired` in sequence. Run
`python reversed-pilot-001/run_checks.py paired` for the opposite-order pilot.
Each child retains the 384MiB heap, 512MiB RSS and 30-second supervisor limits.
Preserve outputs instead of overwriting consumed runs. Installation requires
separate review; this directory is an experimental backup only.
''',encoding='utf-8')
files=[f for f in sorted(P.rglob('*')) if f.is_file()]
for f in files:
    text=f.read_text(encoding='utf-8')
    assert Path.home().name.lower() not in text.lower(),f
for f in sorted(P.rglob('*.mjs')):
    if 'evidence' not in f.parts:subprocess.run(['C:/Program Files/nodejs/node.exe','--check',str(f)],check=True,capture_output=True)
for f in [P/'run_checks.py',P/'reversed-pilot-001/run_checks.py']:
    compile(f.read_text(encoding='utf-8'),str(f),'exec')
for d in [P,P/'reversed-pilot-001']:
    pp=read(d/'PLAN.json')
    assert all(sha(d/r['path'])==r['sha256'] for r in pp['sources'])
manifest={'status':'PORTABLE_KEY_OPTIMIZATION_BACKUP_UNINSTALLED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'entries':entries,'files':[{'path':f.relative_to(P).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size} for f in files],'identity_paths_redacted':True,'portable_replay_executed':False,'static_plan_hash_and_syntax_checks_passed':True}
write(P/'BACKUP-MANIFEST.json',manifest)
print(json.dumps({'path':str(P),'manifest_sha256':sha(P/'BACKUP-MANIFEST.json'),'file_count':len(files)+1,'assessment_sha256':sha(H/'ASSESSMENT.json'),'timings':times}))
