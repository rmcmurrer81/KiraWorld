from pathlib import Path
import ast,hashlib,json,os,re,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');S=W/'world-crew-habitat-eligibility-049';O=W/'w049/p'
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='6b2f43ae42d8b72e06767edb20aa1bebb19e10ce';PREFIX='experimental/world-crew-habitat-eligibility-049/'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def put(relative,raw):
    path=O/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
def scrub(text):
    for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
        for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
    return text
assert not O.exists()
plan=json.loads((S/'REVIEW-PLAN.json').read_bytes());assert sha((S/'REVIEW-PLAN.json').read_bytes())=='c873f387989cdd7347f310194cfea1c3c475bc704db6694e86ccd8001bfe0696'
assert len(plan['files'])==1;row=plan['files'][0];relative=row['relative_path']
assert sha(Path(row['after']['path']).read_bytes())==row['after']['sha256']
assert all(sha(Path(p).read_bytes())==v for p,v in plan['protected_inputs'].items())
old=subprocess.run(['git','show',BASE+':'+relative],cwd=CLONE,capture_output=True,check=True).stdout;assert sha(old)==row['before_sha256']
assert not subprocess.run(['git','ls-tree','--name-only',BASE,'--',PREFIX.rstrip('/')],cwd=CLONE,capture_output=True,check=True).stdout
installed=(S/'INSTALLED.json').exists()
if installed:
    receipt=json.loads((S/'INSTALLED.json').read_bytes());assert receipt['status']=='049_EXACT_ONE_FILE_INSTALL_PASS' and receipt['plan_sha256']==sha((S/'REVIEW-PLAN.json').read_bytes())
    assert sha(Path(row['target']).read_bytes())==row['after']['sha256'];put(relative,Path(row['target']).read_bytes())
else:assert sha(Path(row['target']).read_bytes())==row['before_sha256']
records=[]
for path in sorted(S.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts:continue
    rel=path.relative_to(S).as_posix();raw=path.read_bytes();text=raw.decode('utf8')
    if rel=='capture.py':
        text=text.replace('import argparse,contextlib,hashlib,importlib.util,json,queue,socket,sys,tempfile','import argparse,contextlib,hashlib,importlib.util,json,queue,socket,sys,tempfile,os')
        text=text.replace("K=Path('@kira_root')","K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))")
    public=scrub(text).encode('utf8');put(PREFIX+rel,public)
    if rel.startswith(('candidate/','baseline/')):assert public==raw
    records.append({'path':PREFIX+rel,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if public==raw else 'local paths redacted; capture checkout configurable'})
runner='''"""Portable parser/callback/planner + installer fixtures; no owner state reads."""
from pathlib import Path
import json,os,shutil,subprocess,sys,tempfile
H=Path(__file__).resolve().parent;checkout=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1]))).resolve()
results=[]
with tempfile.TemporaryDirectory(prefix='world049-public-') as name:
    root=Path(name);dest=root/H.name;dest.mkdir();prior=root/'world-chat-delay-candidate-048';prior.mkdir()
    shutil.copyfile(H.parent/'world-chat-delay-candidate-048/harness.py',prior/'harness.py')
    for part in ['candidate','baseline']:shutil.copytree(H/part,dest/part)
    for script in ['capture.py','cases.py','test_evidence.py','install_exact.py','test_installer.py']:shutil.copyfile(H/script,dest/script)
    for args in [['capture.py','baseline'],['capture.py','candidate'],['test_evidence.py'],['test_installer.py']]:
        result=subprocess.run([sys.executable,'-B',*args],cwd=dest,env={**os.environ,'KIRA_TEST_ROOT':str(checkout),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=20)
        if result.returncode:raise RuntimeError(str(args)+' failed: '+result.stdout+result.stderr)
        results.append({'command':args,'result':json.loads(result.stdout)})
print(json.dumps({'status':'PUBLIC_CALLBACK_PLANNER_AND_RECOVERY_CLOSURE_PASS','results':results,'owner_original_recheck':False,'models_workers_ui_network':0}))
'''
put(PREFIX+'test_public_closure.py',runner.encode());put(PREFIX+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf8')).encode())
put(PREFIX+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
note='''# Crew-habitat eligibility049 backup

The proposed research parser normalizes a bounded crew/crewed habitat noun phrase,
optionally Mars/Martian. It retains the existing named-place, reconstruction and
location boundaries.43 actual chat-to-planner fixtures include18 corrected generic
habitat failures,17 held real-place requests and6 nonexecuting chat requests.
The20 original plans use three synthetic source documents; no geometry or visual
quality is generated or approved. Existing real-mode saved briefs stay locked.

README and DELIVERY preserve pre-install evidence. If INSTALLED.json is present,
it supersedes the earlier installation flag and the canonical parser is included
at tools/world_research.py with the exact installed bytes. Otherwise this backup
is experimental only. No original owner worlds, private research, media, fonts or
native binaries are included. The source/world boundaries are unchanged apart
from the explicit bounded generic-habitat eligibility correction.

Candidate and baseline source are exact. Historical machine paths are redacted
with original/public hashes recorded in SOURCE-PROVENANCE.json. Exact installer
plan hashes refer to original local records; review and rebind historical scripts
and plans before recovery. install_exact.py supports a read-only preflight and
explicit exact-hash apply/rollback; root authorization is a separate requirement.
Ten temporary fixture tests cover rollback, tampering and concurrent changes.

Run test_public_closure.py with KIRA_TEST_ROOT pointing to a complete checkout.
It copies tests to temporary folders and reuses the published048 harness. Actual
chat and saved-job services run with inert worker/model/UI boundaries; synthetic
research ingestion prepares actual planner messages without network or geometry.
It does not recheck the original owner's116 files or open their saved preview.
Historical local read-only preview evidence is preserved separately. No nativeUI,
owner realism or game/VR readiness claim follows from a grammar correction.
'''
put(PREFIX+'PUBLIC-BACKUP.md',note.encode())
dependency='experimental/world-chat-delay-candidate-048/harness.py'
dep_raw=subprocess.run(['git','show',BASE+':'+dependency],cwd=CLONE,capture_output=True,check=True).stdout;put(dependency,dep_raw)
test=subprocess.run(['C:/Python314/python.exe','-B','test_public_closure.py'],cwd=O/PREFIX,env={**os.environ,'KIRA_TEST_ROOT':str(K),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=30)
assert test.returncode==0,(test.stdout.decode(),test.stderr.decode())
check=json.loads(test.stdout);check.update({'dependency_path':dependency,'dependency_sha256':sha(dep_raw),'dependency_base_commit':BASE})
put(PREFIX+'PUBLIC-CLOSURE-CHECK.json',(json.dumps(check,indent=2)+'\n').encode())
files=[]
for path in sorted(O.rglob('*')):
    if not path.is_file():continue
    rel=path.relative_to(O).as_posix()
    if rel==dependency:continue
    raw=path.read_bytes();text=raw.decode('utf8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I)
    if path.suffix=='.py':ast.parse(text)
    if path.suffix=='.json':json.loads(text)
    files.append({'path':rel,'file':str(path),'sha256':sha(raw),'bytes':len(raw),'before_sha256':row['before_sha256'] if rel==relative else None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-crew-habitat-023','reviewed':False,
    'allowed_prefixes':[PREFIX]+([relative] if installed else []),'message':'Recognize generic crew and Mars habitat creation while preserving real-place research boundaries; retain tests and recovery','files':files}
mf=W/'sep22-backups/world-crew-habitat-023.manifest.json'
with mf.open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
delivery={'status':'049_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','installed':installed,'canonical_files':int(installed),'manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,
    'files':len(files),'bytes':sum(r['bytes'] for r in files),'portable_callback_planner_cases':43,'portable_evidence_tests':7,'portable_recovery_tests':10,'protected_inputs_verified':116,'models_ui_network_git_mutations':0}
with (H/'DELIVERY.json').open('x',encoding='utf8') as f:json.dump(delivery,f,indent=2);f.write('\n')
print(json.dumps(delivery))
