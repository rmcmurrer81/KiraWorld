"""Freeze exact additive public manifest; never writes a Git object or owner file."""
from pathlib import Path,PurePosixPath
import ast,difflib,hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;W=H.parents[1];RAW=H/'payload';OUT=H/'publishable-002';OUT.mkdir(exist_ok=False)
BASE='c085f491a5329111f1f33ae1b5b45cb681e04422';REPO=W/'work/kiraworld-shared-recall-publication-001/repo'
prefixes=['experimental/world-working-doors-024/','experimental/world-immutable-preview-026/','experimental/world-habitat-realism-025/']
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def redact(raw):
    text=raw.decode('utf-8-sig')
    for value,alias in ((str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')):
        text=text.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
    return re.sub(r'C:[\\/]+Users[\\/]+'+re.escape(Path.home().name),'@user_home',text,flags=re.I).encode('utf-8')
inventory=json.loads((H/'SOURCE-INVENTORY.json').read_text());chosen={r['path']:RAW/r['path'] for r in inventory['files']}
fresh=['experimental/world-working-doors-024/PORTABLE-TEST-RESULT.json',
       'experimental/world-immutable-preview-026/PORTABLE-TEST-RESULT-1.json','experimental/world-immutable-preview-026/PORTABLE-TEST-RESULT-2.json']
for rel in fresh:chosen[rel]=RAW/rel
door=json.loads(chosen[fresh[0]].read_text());compat=json.loads(chosen[fresh[2]].read_text());failed=json.loads(chosen[fresh[1]].read_text())
assert len(door['checks'])==33 and compat['status']=='PASS' and compat['tests']==23
assert failed['status']=='FAIL' and failed['errors']==23 and 'filename or extension is too long' in failed['output']
for rel in ('build.py','fix_portable_paths.py','finalize.py','SOURCE-INVENTORY.json'):
    chosen['experimental/world-immutable-preview-026/recovery/'+rel]=H/rel
mapping=[]
for rel,source in sorted(chosen.items()):
    raw=source.read_bytes();data=redact(raw);target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    mapping.append({'path':rel,'original_sha256':sha(raw),'sha256':sha(data),'bytes':len(data),'identity_paths_redacted':data!=raw})
# Show exactly how portable runners differ from their historical tests.
for prefix,name in [('experimental/world-working-doors-024/','test_doors.mjs'),('experimental/world-immutable-preview-026/','test_compatibility.py')]:
    before=(OUT/prefix/'evidence'/name).read_text();after=(OUT/prefix/name).read_text()
    target=OUT/prefix/'PORTABLE-TEST-ADAPTATION.patch';target.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='historical/'+name,tofile='portable/'+name)))
    data=target.read_bytes();mapping.append({'path':target.relative_to(OUT).as_posix(),'original_sha256':None,'sha256':sha(data),'bytes':len(data),'identity_paths_redacted':False})
proof={'status':'PORTABLE_CPU_RECOVERY_VERIFIED_NOT_INSTALLED','base_commit':BASE,'files':mapping,
 'source_code_exact':'Five proposed024/026 installation files preserve exact frozen candidate bytes; public runtime tools are untouched.',
 'fresh_cpu_checks':{'door_checks':33,'compatibility_tests':23,'real_node_preflight_runs':1,'model_gpu_browser_calls':0},
 'first_portable_failure':'026 run1 failed all23 setup stages because the staging path exceeded Windows path limits. No behavioral assertion or real Node preflight ran in that failed attempt, despite the historical hardcoded preflight count field. The portable runner now checks a uniquely named OS-temp root; run2 passed23.',
 'exclusions':['Generated previews and owner geometry','Server helpers/runtime receipts','PREVIEW-PLAN owner-state inventory','Model binaries/weights','Reference artwork/PDFs','Unfrozen025 room-dressing code','Canonical tools changes','Handoff mutations'],
 'research_only025':True,'original_historical_receipts_unchanged':True,'git_mutations':False,'owner_data_writes':False}
proofrel='experimental/world-immutable-preview-026/PUBLIC-BACKUP-REVIEW.json';save(OUT/proofrel,proof)
paths=[r['path'] for r in mapping]+[proofrel]
assert len(paths)==len(set(paths))
files=[]
for rel in sorted(paths):
    target=OUT/rel;raw=target.read_bytes();text=raw.decode('utf-8-sig');pp=PurePosixPath(rel)
    assert not pp.is_absolute() and '..' not in pp.parts and any(rel.startswith(p) for p in prefixes)
    assert Path.home().name.lower() not in text.lower(),rel
    assert not re.search(r'(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',text),rel
    assert not re.search(r'https?://[^/\s:@]+:[^/\s@]+@',text),rel
    if target.suffix=='.py':ast.parse(text)
    assert not subprocess.check_output(['git','-C',str(REPO),'ls-tree',BASE,'--',rel]).strip(),rel
    files.append({'path':rel,'file':str(target),'sha256':sha(raw),'bytes':len(raw),'before_sha256':None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(REPO),'base_commit':BASE,'receipt_prefix':'world-door-preview-006','reviewed':False,
 'allowed_prefixes':prefixes,'message':'Back up isolated door and preview compatibility experiments with portable tests and habitat reference notes','files':files}
manifest_path=W/'work/sep22-backups/world-door-preview-006.manifest.json';save(manifest_path,manifest)
delivery={'status':'PUBLIC_ADDITIVE_MANIFEST_READY_FOR_ROOT_REVIEW_NOT_PUSHED','manifest':{'path':str(manifest_path),'sha256':sha(manifest_path.read_bytes())},
 'base_commit':BASE,'file_count':len(files),'bytes':sum(r['bytes'] for r in files),'new_experimental_paths_only':True,
 'portable_cpu_checks':56,'model_gpu_calls':0,'owner_state_or_canonical_writes':False,'git_mutations':False,'025_code_included':False,
 'review':{'path':str(OUT/proofrel),'sha256':sha((OUT/proofrel).read_bytes())},'original_inventory':{'path':str(H/'SOURCE-INVENTORY.json'),'sha256':sha((H/'SOURCE-INVENTORY.json').read_bytes())}}
save(H/'DELIVERY.json',delivery);print(json.dumps(delivery))
