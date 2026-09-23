from pathlib import Path
import ast,hashlib,json,os,re,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');O=W/'w048/p2'
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='6834ff2db0108fa048daa690a2c6dc664716f89d'
NAMES=['world-chat-dispatch-candidate-047','world-chat-delay-candidate-048'];PREFIXES=['experimental/'+n+'/' for n in NAMES]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def put(rel,raw):
    path=O/rel;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
def scrub(text):
    for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
        for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
    return text
assert not O.exists()
S=W/NAMES[1];plan=json.loads((S/'INSTALL-PLAN.json').read_bytes());installed=json.loads((S/'INSTALLED.json').read_bytes())
assert installed['status']=='048_EXACT_TWO_FILE_INSTALL_PASS' and installed['install_plan_sha256']=='3fedb5237a74155411c93453df700ecfeaca358bedd9b5dcdc2594409d713906'
assert all(sha(Path(p).read_bytes())==v for p,v in plan['protected_inputs'].items())
before={}
for row in plan['files']:
    relative=row['relative_path'];raw=Path(row['target']).read_bytes();assert sha(raw)==row['after']['sha256']
    old=subprocess.run(['git','show',BASE+':'+relative],cwd=CLONE,capture_output=True)
    if row['before_sha256'] is None:
        assert old.returncode!=0
        assert not subprocess.run(['git','ls-tree','--name-only',BASE,'--',relative],cwd=CLONE,capture_output=True,check=True).stdout
    else:assert old.returncode==0 and sha(old.stdout)==row['before_sha256']
    before[relative]=row['before_sha256'];put(relative,raw)
for prefix in PREFIXES:assert not subprocess.run(['git','ls-tree','--name-only',BASE,'--',prefix.rstrip('/')],cwd=CLONE,capture_output=True,check=True).stdout
records=[]
for name,prefix in zip(NAMES,PREFIXES):
    source=W/name
    for path in sorted(source.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts:continue
        relative=path.relative_to(source).as_posix();raw=path.read_bytes();text=raw.decode('utf8')
        if relative=='harness.py':
            text=text.replace('import contextlib,hashlib,importlib.util,json,queue,sys,tempfile','import contextlib,hashlib,importlib.util,json,queue,sys,tempfile,os')
            text=text.replace("K=Path('@kira_root')","K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))")
        public=scrub(text).encode('utf8');put(prefix+relative,public)
        if relative.startswith(('candidate/','baseline/','prior047/')):assert public==raw
        records.append({'path':prefix+relative,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if public==raw else 'local paths redacted; harness checkout configurable'})

runner='''"""Run historical callback fixtures in disposable copies; no owner-file claims."""
from pathlib import Path
import json,os,shutil,subprocess,sys,tempfile
H=Path(__file__).resolve().parent
checkout=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1]))).resolve()
previous=H.parent/'world-chat-usability-audit-046/test_context.py'
results=[]
with tempfile.TemporaryDirectory(prefix='world048-public-') as name:
    root=Path(name)
    prior=root/'world-chat-usability-audit-046';prior.mkdir();shutil.copyfile(previous,prior/'test_context.py')
    for package in ['world-chat-dispatch-candidate-047','world-chat-delay-candidate-048']:
        source=H.parent/package;dest=root/package;dest.mkdir()
        for item in ['candidate','baseline','prior047']:
            if (source/item).exists():shutil.copytree(source/item,dest/item)
        scripts=['harness.py','test_dispatch.py','test_retained_context.py']
        if package.endswith('048'):scripts+=['install_exact.py','test_installer.py']
        for script in scripts:shutil.copyfile(source/script,dest/script)
        for script in ['test_dispatch.py','test_retained_context.py']+(['test_installer.py'] if package.endswith('048') else []):
            result=subprocess.run([sys.executable,'-B',script],cwd=dest,env={**os.environ,'KIRA_TEST_ROOT':str(checkout),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=20)
            if result.returncode:raise RuntimeError(package+' '+script+' failed: '+result.stdout+result.stderr)
            results.append({'package':package,'test':script,'result':json.loads(result.stdout)})
print(json.dumps({'status':'PUBLIC_DISPOSABLE_CALLBACK_AND_RECOVERY_TESTS_PASS','results':results,'owner_original_recheck':False,'models_gpu_native_ui':0}))
'''
put(PREFIXES[1]+'test_public_closure.py',runner.encode())
put(PREFIXES[1]+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf8')).encode())
put(PREFIXES[1]+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
note='''# Installed World chat dispatcher048 and held047 history

Canonical tools/world_builder_workspace.py and tools/world_chat_requests.py are
the exact installed048 bytes. Root reviewed the full two-file delta,69 callback
fixtures,10 retained-context tests and10 installer tests before applying the
exact plan. All116 protected originals were unchanged. This fixes explicit
command dispatch and delays; it does not implement conversational room editing.

Frozen047 remains historical: its53 fixtures passed, but independent review found
four further delayed requests that still queued jobs.048 ROOT-REGRESSIONS.json
reproduces them and the correction through actual callbacks. Read both histories
as evidence, not interchangeable installation candidates. No native UI review or
owner approval is claimed. Stop does not cancel existing research workers.

Only source, synthetic test captures and technical receipts are included. No
owner world geometry, personal memory, media, font or native dependency binary is
bundled. Candidate/baseline source is exact. Historical local paths are redacted
with original/public hashes in SOURCE-PROVENANCE.json. Historical receipt hashes
refer to local originals; do not blindly run redacted installer/plans. Review and
rebind them to a checkout, retaining exact targets, preimages and protected inputs.

Run test_public_closure.py with KIRA_TEST_ROOT pointing to a complete checkout.
It uses disposable copies of047/048 tests plus the already published046 context
test source. Actual job/catalog callbacks execute in temporary state; model,
research worker, preview launch, destination chooser and export remain inert.
The portable test does not claim to recheck the original owner's116 files. All
temporary state is removed by its own TemporaryDirectory. Historical receipts
remain untouched. Existing command grammar is bounded; unsupported edits,
named/type-filtered world lookup and general conversation remain honest gaps.
'''
put(PREFIXES[1]+'PUBLIC-BACKUP.md',note.encode())
# The portable046 dependency is already on the reviewed base. Stage its exact
# published test locally for this closure run, but do not include a duplicate in
# the manifest or overwrite its public history.
dep='experimental/world-chat-usability-audit-046/test_context.py'
dep_raw=subprocess.run(['git','show',BASE+':'+dep],cwd=CLONE,capture_output=True,check=True).stdout
put(dep,dep_raw)
result=subprocess.run(['C:/Python314/python.exe','-B','test_public_closure.py'],cwd=O/PREFIXES[1],env={**os.environ,'KIRA_TEST_ROOT':str(K),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=30)
assert result.returncode==0,(result.stdout.decode(),result.stderr.decode())
checks=json.loads(result.stdout);checks.update({'dependency_path':dep,'dependency_base_commit':BASE,'dependency_sha256':sha(dep_raw)})
put(PREFIXES[1]+'PUBLIC-CLOSURE-CHECK.json',(json.dumps(checks,indent=2)+'\n').encode())
files=[]
for path in sorted(O.rglob('*')):
    if not path.is_file():continue
    relative=path.relative_to(O).as_posix()
    if relative==dep:continue
    raw=path.read_bytes();text=raw.decode('utf8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I)
    if path.suffix=='.py':ast.parse(text)
    if path.suffix=='.json':json.loads(text)
    files.append({'path':relative,'file':str(path),'sha256':sha(raw),'bytes':len(raw),'before_sha256':before.get(relative)})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-chat-delay-022','reviewed':False,
    'allowed_prefixes':PREFIXES+list(before),'message':'Route World chat commands without unwanted research and honor explicit request delays; preserve callback and recovery evidence','files':files}
mf=W/'sep22-backups/world-chat-delay-022.manifest.json'
with mf.open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
delivery={'status':'INSTALLED048_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,'files':len(files),'bytes':sum(r['bytes'] for r in files),'canonical_files':2,
    'portable_validation':'047 53 cases/5 groups +10 context;048 69 cases/6 groups +10 context +10 installer fixture tests','held047_failures_and_recovery_included':True,'protected_inputs_verified':116,'models_gpu_ui':0,'git_mutations':0}
with (H/'DELIVERY.json').open('x',encoding='utf8') as f:json.dump(delivery,f,indent=2);f.write('\n')
print(json.dumps(delivery))
