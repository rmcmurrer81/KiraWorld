from pathlib import Path
import ast,hashlib,json,os,re,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');O=W/'w054/p'
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='ba74f9b6a22e87bc6bab0be6af8d927c6eba3a20'
NAMES=['world-door-traversal-audit-052','world-observation-viewport-053','world-observation-setting-054'];PREFIXES=['experimental/'+n+'/' for n in NAMES]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def put(rel,raw):
 p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def scrub(text):
 for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
  for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
 return text
def git_read(path):return subprocess.run(['git','show',BASE+':'+path],cwd=CLONE,capture_output=True,check=True).stdout
assert not O.exists()
for name in NAMES:
 source=W/name;frozen=json.loads((source/'FROZEN-MANIFEST.json').read_bytes())
 assert all(sha((source/r).read_bytes())==v['sha256'] and (source/r).stat().st_size==v['bytes'] for r,v in frozen['files'].items())
for prefix in PREFIXES:assert not subprocess.run(['git','ls-tree','--name-only',BASE,'--',prefix.rstrip('/')],cwd=CLONE,capture_output=True,check=True).stdout
plan=json.loads((W/NAMES[2]/'INSTALL-PLAN.json').read_bytes());assert all(sha(Path(p).read_bytes())==v for p,v in plan['protected_inputs'].items())
base_map=[]
for row in plan['files']:
 assert sha(git_read(row['relative_path']))==row['before_sha256']==sha(Path(row['target']).read_bytes())
 base_map.append({'repository_path':row['relative_path'],'base_commit':BASE,'sha256':row['before_sha256'],'canonical_changed':False})
records=[];excluded=[]
for name,prefix in zip(NAMES,PREFIXES):
 source=W/name
 for path in sorted(source.rglob('*')):
  if not path.is_file() or '__pycache__' in path.parts:continue
  rel=path.relative_to(source).as_posix();raw=path.read_bytes()
  if rel.startswith('runtime_context/Data/'):
   excluded.append({'path':prefix+rel,'sha256':sha(raw),'bytes':len(raw),'reason':'Private immutable context: original source geometry and bound brief snapshot are not public backup content.'});continue
  binary=path.suffix.lower() in ('.glb','.png')
  public=raw if binary else scrub(raw.decode('utf-8')).encode('utf-8');put(prefix+rel,public)
  if rel.startswith(('candidate/','baseline/','preimages/')):assert public==raw,rel
  records.append({'path':prefix+rel,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if public==raw else 'local identity paths redacted'})
put(PREFIXES[2]+'test_public_closure.py',(H/'test_public_closure.py').read_bytes())
put(PREFIXES[2]+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf-8')).encode())
put(PREFIXES[2]+'CANONICAL-BASE-MAP.json',(json.dumps(base_map,indent=2)+'\n').encode())
put(PREFIXES[2]+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
put(PREFIXES[2]+'EXCLUDED-CONTEXT.json',(json.dumps(excluded,indent=2)+'\n').encode())
note='''# Experimental viewport recovery052–054 — not installed

No canonical files are changed by this backup. The current installed release is
051.052 is a CPU navigation audit which found no new traversal defect.053 builds
a real nontraversable window and procedural terrain, but its environment scope
was overbroad. Preserve053 as held history, not an installable recommendation.
054 fixes that scope by deriving the exterior setting only from the exact bound
original brief. The actual Mars request remains effective; compatible orbital or
unknown worlds keep the aperture with no invented ground. Corrupt provenance is
held. Existing immutable previews are preserved.

Both053 PNGs and its original derived GLB are retained. One uses prior interior
inspection lighting; the second uses explicitly disclosed diagnostic daylight
and a wider camera. They demonstrate procedural construction, not native viewer
illumination, owner approval or photorealism.054 actualGLB has the exact same
binary mesh/texture payload, differing only in minimal setting provenance. Its
full compact authored output is retained too. Neither prototype is installed.
Root requires native viewer inspection after the Studio GPU job closes.

Original owner geometry/research and the private immutable brief snapshot are
excluded with hashes. No raw brief appears in the exported GLB/package or local
presentation endpoint. The actual source digest/job identity is sufficient in
those derived outputs. This backup contains no weights, raw owner media, private
research cache, fonts or native dependency binaries. Three source/license is kept.

test_public_closure.py runs in fresh temporary folders using the already-public
synthetic habitat fixture. It checks052 navigation,053 geometry and054 source
grammar/setting behavior without reading owner worlds, starting a server/UI or
exporting/rendering. Actual owner/API/HTTP receipts are separate historical
evidence. Python and Node are required; KIRA_TEST_NODE can select Node. Source
and preimages remain exact; SOURCE-PROVENANCE records redacted receipt/script
hashes. CANONICAL-BASE-MAP pins the prior installed files at the public base.

Redacted local install/actual-export helpers are recovery references, not portable
commands to run blindly. Rebind explicit paths/dependencies, preserve source
digests and choose fresh destinations. Technical tests are not installation
approval. No game/VR engine runtime, pressure model or real Mars terrain is claimed.
'''
put(PREFIXES[2]+'PUBLIC-BACKUP.md',note.encode())
run=subprocess.run(['C:/Python314/python.exe','-B','test_public_closure.py'],cwd=O/PREFIXES[2],capture_output=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
assert run.returncode==0,(run.stdout.decode(),run.stderr.decode());check=json.loads(run.stdout)
put(PREFIXES[2]+'PUBLIC-CLOSURE-CHECK.json',(json.dumps(check,indent=2)+'\n').encode())
actual_prompt=json.loads((K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json').read_bytes())['brief']['prompt'].encode()
files=[]
for path in sorted(O.rglob('*')):
 if not path.is_file() or '__pycache__' in path.parts:continue
 rel=path.relative_to(O).as_posix();raw=path.read_bytes()
 assert actual_prompt not in raw,rel
 assert not re.search(rb'C:[/\\]+Users[/\\]+robmc',raw,re.I),rel
 assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})',raw),rel
 if path.suffix.lower() not in ('.png','.glb'):
  text=raw.decode('utf-8')
  if path.suffix=='.py':ast.parse(text)
  if path.suffix=='.json':json.loads(text)
 files.append({'path':rel,'file':str(path),'sha256':sha(raw),'bytes':len(raw),'before_sha256':None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-observation-025','reviewed':False,'allowed_prefixes':PREFIXES,
 'message':'Preserve navigation audit and source-bound observation-window prototypes with original geometry, tests and rendered evidence','files':files}
mf=W/'sep22-backups/world-observation-025.manifest.json'
with mf.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
delivery={'status':'EXPERIMENTAL052_053_054_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,'files':len(files),'bytes':sum(r['bytes'] for r in files),'canonical_files':0,'preserved_owner_inputs':116,'no_git_mutation':True,'raw_brief_or_source_geometry_included':False,'synthetic_public_closure':check['status'],'native_review_installation_pending':True}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(delivery,f,indent=2);f.write('\n')
print(json.dumps(delivery))
