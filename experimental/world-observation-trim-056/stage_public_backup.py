"""Stage frozen public proposals only. Wait for root's native/install outcome."""
from pathlib import Path
import ast,hashlib,json,os,re,subprocess,sys
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');O=Path('@user_home/.codex/world056-public026-stage')
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='ece863af2352fb4a872a8297333a1636cc63e4b6'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def dump(v):return (json.dumps(v,indent=2)+'\n').encode()
def put(rel,raw):
 p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def scrub(text):
 for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
  for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
 return text
def git_read(path):return subprocess.run(['git','show',BASE+':'+path],cwd=CLONE,capture_output=True,check=True).stdout
assert not O.exists();records=[]
packages=[('world-observation-exclusion-055',''),('world-observation-trim-056',''),('world-observation-trim-056','native-successor-001')]
for name,sub in packages:
 source=W/name/sub;frozen=json.loads((source/'FROZEN-MANIFEST.json').read_bytes())
 for rel,row in frozen['files'].items():
  p=source/rel;assert sha(p.read_bytes())==row['sha256'] and p.stat().st_size==row['bytes'],str(p)
 for rel in [*frozen['files'],'FROZEN-MANIFEST.json','DELIVERY.json']:
  p=source/rel;repo='experimental/'+name+'/'+(sub+'/' if sub else '')+rel
  raw=p.read_bytes();public=scrub(raw.decode('utf-8')).encode();put(repo,public)
  if rel.startswith(('candidate/','baseline/','preimages/','canonical-preimages/')):assert raw==public,rel
  records.append({'path':repo,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if raw==public else 'local identity paths redacted'})
name='world-observation-trim-056';prefix='experimental/'+name+'/'
extra=['prepare_native.py','prepare_successor.py','prepare_review.py','INSTALL-PLAN.json','SOURCE.diff','SOURCE-PINS.json','ACTUAL-PRESENTATION.json',
 'installation/install_exact.py','installation/test_installer.py','installation/serve_review.py','installation/INSTALLER-TEST-RESULT.json']
extra += [p.relative_to(W/name).as_posix() for p in sorted((W/name/'canonical-preimages').rglob('*')) if p.is_file()]
for rel in extra:
 p=W/name/rel;raw=p.read_bytes();public=scrub(raw.decode()).encode();put(prefix+rel,public)
 if rel.startswith('canonical-preimages/'):assert raw==public
 records.append({'path':prefix+rel,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if raw==public else 'local identity paths redacted'})
hold=W/'sep23-continuation/WORLD055-NATIVE-HOLD.json';raw=hold.read_bytes();public=scrub(raw.decode()).encode();put(prefix+'WORLD055-NATIVE-HOLD.json',public)
records.append({'path':prefix+'WORLD055-NATIVE-HOLD.json','original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'local identity paths redacted'})
put(prefix+'test_public_closure.py',(H/'test_public_closure.py').read_bytes())
put(prefix+'stage_public_backup.py',scrub(Path(__file__).read_text()).encode())
put(prefix+'SOURCE-PROVENANCE.staged.json',dump(records))
plan=json.loads((W/name/'native-successor-001/INSTALL-PLAN.json').read_bytes());base_rows=[]
for row in plan['files']:
 old=git_read(row['relative_path']);assert sha(old)==row['before_sha256']
 base_rows.append({'repository_path':row['relative_path'],'base_commit':BASE,'sha256':sha(old),
 'preserved_preimage_path':prefix+'native-successor-001/canonical-preimages/'+row['relative_path']})
put(prefix+'CANONICAL051-PREIMAGE-MAP.json',dump(base_rows))
test=subprocess.run([sys.executable,'-B','test_public_closure.py'],cwd=O/prefix,capture_output=True,text=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
assert test.returncode==0,test.stdout+test.stderr;check=json.loads(test.stdout);put(prefix+'PUBLIC-CLOSURE-CHECK.json',dump(check))
actual_prompt=json.loads((K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json').read_bytes())['brief']['prompt'].encode()
for p in O.rglob('*'):
 if not p.is_file():continue
 raw=p.read_bytes();assert actual_prompt not in raw,str(p)
 assert not re.search(rb'C:[/\\]+Users[/\\]+robmc',raw,re.I),str(p)
 assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})',raw),str(p)
 if p.suffix=='.py':ast.parse(raw.decode())
 if p.suffix=='.json':json.loads(raw)
status={'status':'STAGED_FROZEN_PUBLIC_SOURCES_WAITING_ROOT_NATIVE_INSTALL_OUTCOME','base_commit':BASE,'stage':str(O),
 'source_records':len(records),'canonical_rows_staged':0,'synthetic_closure':check,'no_git_mutations':True,'no_server_ui_models':True}
(H/'STAGED.json').write_bytes(dump(status));print(json.dumps(status))
