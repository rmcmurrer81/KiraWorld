"""Dry-check by default. Root may use --install after exact plan review.

Writes only the five allowlisted existing engine files. Does not create models,
worlds, previews, shortcuts or projects. Each preimage is retained in this package.
"""
from pathlib import Path
import argparse,hashlib,json,os,tempfile,datetime
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--expected-plan-sha256',required=True);ap.add_argument('--install',action='store_true');a=ap.parse_args()
plan=H/'INSTALL-PLAN.json';assert sha(plan)==a.expected_plan_sha256,'Plan changed'
p=json.loads(plan.read_text());root=Path(p['canonical_root']).resolve()
allow={f'tools/world_builder_engine/{n}' for n in ('viewer.mjs','walk_controller.mjs','index.html','style.css','world_layout_preview.py')}
assert len(p['files'])==5 and {f['relative_path'] for f in p['files']}==allow
assert not (H/'INSTALLED.json').exists(),'Install receipt already exists'
for f in p['files']:
 target=Path(f['target']);assert target.resolve()==root/f['relative_path'] and target.is_file()
 for entry in ('before','after'):
  source=Path(f[entry]['path']);assert source.resolve().is_relative_to(H.resolve()) and sha(source)==f[entry]['sha256']
 for current in (target,*target.parents):assert not current.is_symlink() and not getattr(current.lstat(),'st_file_attributes',0)&0x400
 assert sha(target)==f['before']['sha256'],'Canonical changed before install'
assert all(sha(path)==digest for path,digest in p['protected_inputs'].items())
for d in p['unchanged_dependencies']:assert sha(d['source']['path'])==d['source']['sha256']
if not a.install:
 print(json.dumps({'status':'PASS_DRY_CHECK_ONLY','files':5,'owner_source_files':len(p['protected_inputs']),'installed':False}));raise SystemExit
def atomic(target,content):
 fd,name=tempfile.mkstemp(prefix='.habitat027-',suffix='.tmp',dir=target.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(content);f.flush();os.fsync(f.fileno())
  os.replace(name,target)
 finally:
  if Path(name).exists():Path(name).unlink()
changed=[]
try:
 for f in p['files']:
  target=Path(f['target']);assert sha(target)==f['before']['sha256'];atomic(target,Path(f['after']['path']).read_bytes());changed.append(f)
 assert all(sha(f['target'])==f['after']['sha256'] for f in p['files'])
 assert all(sha(path)==digest for path,digest in p['protected_inputs'].items())
except BaseException:
 for f in reversed(changed):
  # Never overwrite a third-party change during rollback.
  if sha(f['target'])==f['after']['sha256']:atomic(Path(f['target']),Path(f['before']['path']).read_bytes())
 raise
receipt={'status':'INSTALLED_FIVE_FILES_OWNER_SOURCE_BYTES_UNCHANGED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'plan_sha256':sha(plan),'files':p['files'],'protected_owner_source_files':len(p['protected_inputs']),
 'saved_previews_rewritten':False,'models_browser_gpu_started':False,'visual_owner_approval':False}
with (H/'INSTALLED.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'status':receipt['status'],'files':5}))
