"""Apply only the exact root-approved041 plan, with per-file atomic replacement."""
from pathlib import Path
import datetime,hashlib,json,os,tempfile
H=Path(__file__).resolve().parent;K=Path('@kira_root').resolve()
EXPECTED_PLAN='954b2ca088c46987ad6bb7963c97afff79664ad1f0680ca6d9d7dd5882f9636a'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(prefix='.codex041-',dir=path.parent,delete=False) as stream:
  temporary=Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
 try:os.replace(temporary,path)
 finally:
  if temporary.exists():temporary.unlink()

assert sha(H/'INSTALL-PLAN-REV3.json')==EXPECTED_PLAN
assert not (H/'INSTALLED.json').exists()
plan=json.loads((H/'INSTALL-PLAN-REV3.json').read_bytes());rows=plan['files'];assert len(rows)==5
for row in rows:
 target=Path(row['target']).resolve();assert target.is_relative_to(K) and target==K/row['relative_path']
 assert (sha(target) if target.exists() else None)==row['before_sha256'],'Installed preimage changed: '+str(target)
 assert sha(row['after']['path'])==row['after']['sha256']
 if row['before_sha256'] is not None:assert sha(row['preimage'])==row['before_sha256']
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
changed=[];rollback=[]
try:
 for row in rows:
  target=Path(row['target']).resolve()
  assert (sha(target) if target.exists() else None)==row['before_sha256'],'Concurrent preimage change'
  atomic(target,Path(row['after']['path']).read_bytes());changed.append(row)
  assert sha(target)==row['after']['sha256']
 assert all(sha(row['target'])==row['after']['sha256'] for row in rows)
 assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
except Exception:
 for row in reversed(changed):
  target=Path(row['target']).resolve();assert target.is_relative_to(K)
  if sha(target)!=row['after']['sha256']:rollback.append({'path':str(target),'status':'held_concurrent_change'});continue
  if row['before_sha256'] is None:target.unlink()
  else:atomic(target,Path(row['preimage']).read_bytes())
  rollback.append({'path':str(target),'status':'restored'})
 (H/'ROOT-EXECUTION-FAILED.json').write_text(json.dumps({'status':'041_INSTALL_FAILED_ROLLBACK_ATTEMPTED','rollback':rollback},indent=2)+'\n',encoding='utf-8')
 raise
receipt={'status':'041_EXACT_ROOT_APPROVED_INSTALL_PASS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'authorization':'Parent root explicitly approved exact five-file041 REV3 installation, atomic replacements, protected-original checks and API-only preview/export validation. No UI input authorized.',
 'install_plan_sha256':EXPECTED_PLAN,'files':rows,'installed_files':len(rows),'protected_original_files_unchanged':len(plan['protected_inputs']),
 'atomic_per_file':True,'rollback_needed':False,'saved_previews_modified':False,'native_ui_opened':False,'gpu_model_calls':0,
 'next':'Fresh installed API export/importer verification; native UI review remains pending.'}
(H/'INSTALLED.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:receipt[k] for k in ('status','installed_files','protected_original_files_unchanged','rollback_needed')}))
