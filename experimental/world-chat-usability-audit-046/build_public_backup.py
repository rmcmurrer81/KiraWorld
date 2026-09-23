from pathlib import Path
import ast,hashlib,json,os,re,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');S=W/'world-chat-usability-audit-046';O=W/'w046/p'
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='f1f4eea0401bfa3e32effe45f6d8c104a4e78e5a';PREFIX='experimental/world-chat-usability-audit-046/'
sha=lambda b:hashlib.sha256(b).hexdigest()
def put(rel,b):
    p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def scrub(text):
    for p,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
        for old in (str(p).replace('\\','\\\\'),str(p),p.as_posix()):text=text.replace(old,label)
    return text
assert not O.exists()
plan=json.loads((S/'REVIEW-PLAN.json').read_bytes());row=plan['files'][0]
assert len(plan['files'])==1 and row['relative_path']=='tools/world_builder_workspace.py'
assert sha((S/'INSTALLED.json').read_bytes())=='d45b26c94ee02892e7447b3389060bfe0869a6c3e28e6073e3c2c170f7257669'
assert sha(Path(row['target']).read_bytes())==row['after']['sha256']
old=subprocess.run(['git','show',BASE+':'+row['relative_path']],cwd=CLONE,capture_output=True,check=True).stdout;assert sha(old)==row['before_sha256']
assert not subprocess.run(['git','ls-tree','--name-only',BASE,'--',PREFIX.rstrip('/')],cwd=CLONE,capture_output=True,check=True).stdout
assert all(sha(Path(p).read_bytes())==v for p,v in plan['protected_inputs'].items())
put(row['relative_path'],Path(row['target']).read_bytes());records=[]
for p in sorted(S.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts:continue
    rel=p.relative_to(S).as_posix();raw=p.read_bytes();text=raw.decode('utf-8')
    if rel=='harness.py':text=text.replace('import contextlib,hashlib,importlib.util,json,queue,sys,tempfile','import contextlib,hashlib,importlib.util,json,queue,sys,tempfile,os').replace("K=Path('@kira_root')","K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))")
    new=scrub(text).encode();put(PREFIX+rel,new)
    if rel.startswith(('candidate/','baseline/')):assert new==raw
    records.append({'path':PREFIX+rel,'original_sha256':sha(raw),'public_sha256':sha(new),'transformation':'exact' if new==raw else 'local paths redacted; harness root configurable'})
installer=W/'sep23-continuation/install_world046.py';raw=installer.read_bytes();new=scrub(raw.decode()).encode();put(PREFIX+'install_world046.py',new)
records.append({'path':PREFIX+'install_world046.py','original_sha256':sha(raw),'public_sha256':sha(new),'transformation':'historical root installer with local paths redacted'})
# Preserve the exact historical test source; add an explicitly portable wrapper
# which omits only machine-specific owner/preimage checks from its final block.
test=(S/'test_context.py').read_text(encoding='utf-8')
a=test.index("    plan=json.loads((H/'REVIEW-PLAN.json').read_bytes());sha=")
b=test.index("    receipt=",a)
test=test[:a]+"    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()\n"+test[b:]
test=test.replace("'protected_originals_unchanged':116","'owner_original_recheck':'not_applicable_to_portable_fixture_test'").replace("H/'TEST-RESULT.json'","H/('PUBLIC-TEST-RESULT-'+str(len(list(H.glob('PUBLIC-TEST*.json'))))+'.json')")
put(PREFIX+'test_public_context.py',scrub(test).encode())
put(PREFIX+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf-8')).encode())
put(PREFIX+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
note='''# Installed chat-context correction046

The exact one-file workspace update is installed. Root reviewed the delta and
11 focused callback/service tests; all116 protected original files were unchanged
when installed. The fixed transition selects a new chat-created job through the
existing context reset, closing old previews/photos and rebinding components.
Same-job resume stays intact. No parser or geometry/generation logic changes.

The15-case audit exposes remaining chat gaps: edit/open/export/status/questions
and negated requests still become new research; “original crew habitat” remains
real-place locked. The tested UI reports queued research rather than falsely
claiming those requested actions completed. ASSESSMENT.md and frozen DELIVERY
describe pre-install evidence; INSTALLED.json supersedes their installation flag.

Candidate and baseline source are exact. Local paths in historical receipts and
recovery scripts are placeholders, with original/public hashes in provenance.
The root installer and its rollback preimage are preserved; review/rebind local
paths before recovery rather than blindly running the historical helper.

Run test_public_context.py with KIRA_TEST_ROOT pointing to this complete checkout.
It exercises actual callbacks/services against disposable state with inert model,
research, native UI and export boundaries. Unlike the frozen local test, it does
not claim to recheck the original owner's116 files on another computer. Historical
captures/test receipts are preserved. No new native window, GPU/model job, preview
server or actual export was run for this backup; it does not prove new UI realism.
'''
put(PREFIX+'PUBLIC-BACKUP.md',note.encode())
result=subprocess.run(['C:/Python314/python.exe','-B','test_public_context.py'],cwd=O/PREFIX,env={**os.environ,'KIRA_TEST_ROOT':str(K),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=20)
assert result.returncode==0,(result.stdout.decode(),result.stderr.decode())
put(PREFIX+'PUBLIC-CLOSURE-CHECK.json',(json.dumps({'status':'PORTABLE_DISPOSABLE_CALLBACK_TESTS_PASS','result':json.loads(result.stdout),'owner_file_recheck':False,'models_gpu_ui':0},indent=2)+'\n').encode())
files=[]
for p in sorted(O.rglob('*')):
    if not p.is_file():continue
    raw=p.read_bytes();text=raw.decode('utf-8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I)
    if p.suffix=='.py':ast.parse(text)
    if p.suffix=='.json':json.loads(text)
    rel=p.relative_to(O).as_posix();files.append({'path':rel,'file':str(p),'sha256':sha(raw),'bytes':len(raw),'before_sha256':row['before_sha256'] if rel==row['relative_path'] else None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-chat-context-021','reviewed':False,'allowed_prefixes':[PREFIX,row['relative_path']],
    'message':'Keep chat-created World Builder jobs bound to their own preview and panels; preserve ordinary-chat audit','files':files}
mf=W/'sep22-backups/world-chat-context-021.manifest.json'
with mf.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
delivery={'status':'INSTALLED046_PUBLIC_BACKUP_READY','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,'files':len(files),'bytes':sum(r['bytes'] for r in files),'canonical_files':1,'recoverable_installer_and_preimage':True,'portable_callback_tests':11,'native_ui_models_gpu':0,'git_mutations':0}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(delivery,f,indent=2);f.write('\n')
print(json.dumps(delivery))
