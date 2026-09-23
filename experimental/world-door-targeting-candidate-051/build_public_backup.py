from pathlib import Path
import ast,hashlib,json,os,re,subprocess
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');O=W/'w051/p'
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='25d46d357a5e1bc06cfff34cc41536e0d52fc79b'
NAMES=['world-door-targeting-candidate-050','world-door-targeting-candidate-051'];PREFIXES=['experimental/'+n+'/' for n in NAMES]
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
S=W/NAMES[1];plan=json.loads((S/'INSTALL-PLAN.json').read_bytes());installed=json.loads((S/'INSTALLED.json').read_bytes())
assert sha((S/'INSTALL-PLAN.json').read_bytes())=='acc62a7e35915eaf62ce3914b04f0cc14f144285f00c701fa1f7a11edc2d435c'
assert installed['status']=='051_EXACT_FIVE_FILE_INSTALL_PASS' and installed['install_plan_sha256']==sha((S/'INSTALL-PLAN.json').read_bytes())
assert len(plan['protected_inputs'])==116 and all(sha(Path(p).read_bytes())==v for p,v in plan['protected_inputs'].items())
before={}
for row in plan['files']:
 rel=row['relative_path'];raw=Path(row['target']).read_bytes();assert sha(raw)==row['after']['sha256'] and sha(git_read(rel))==row['before_sha256']
 before[rel]=row['before_sha256'];put(rel,raw)
for prefix in PREFIXES:assert not subprocess.run(['git','ls-tree','--name-only',BASE,'--',prefix.rstrip('/')],cwd=CLONE,capture_output=True,check=True).stdout
records=[];excluded=[]
for name,prefix in zip(NAMES,PREFIXES):
 source=W/name
 for path in sorted(source.rglob('*')):
  if not path.is_file() or '__pycache__' in path.parts:continue
  rel=path.relative_to(source).as_posix();raw=path.read_bytes()
  # Original saved geometry/cache is not backup content. The identical authored
  # GLB is already public045; retain hashes/technical export receipts without
  # duplicating that binary or its derived scene metadata in this small backup.
  if rel.startswith('runtime_context/Data/') or rel in ('actual-001/package/scene.glb','actual-001/package/scene.json'):
   excluded.append({'path':prefix+rel,'sha256':sha(raw),'bytes':len(raw),'reason':'owner-derived immutable context excluded' if rel.startswith('runtime_context/Data/') else 'byte-identical GLB or semantic metadata already public045'});continue
  public=scrub(raw.decode('utf8')).encode('utf8');put(prefix+rel,public)
  if rel.startswith(('candidate/','baseline/','preimages/')):assert public==raw
  records.append({'path':prefix+rel,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if public==raw else 'local identity paths redacted'})
fixture='experimental/world-galley-detail-045/fixtures/base.json';fixture_raw=git_read(fixture)
assert json.loads(fixture_raw)['title']=='Synthetic authored habitat base'
put(PREFIXES[1]+'fixtures/synthetic-habitat.json',fixture_raw)
put(PREFIXES[1]+'test_public_closure.py',(H/'test_public_closure.py').read_bytes())
put(PREFIXES[1]+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf8')).encode())
put(PREFIXES[1]+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
put(PREFIXES[1]+'EXCLUDED-CONTEXT.json',(json.dumps({'files':excluded,'synthetic_fixture_source':fixture,'synthetic_fixture_base_commit':BASE,'synthetic_fixture_sha256':sha(fixture_raw),
 'existing_identical_glb_path':'experimental/world-galley-detail-045/installed-mars-001/package/scene.glb','existing_identical_glb_sha256':'0b6ee808519f83e73a3ff5b9df336d456e76f7fce91fe493e797702ba226531b'},indent=2)+'\n').encode())
assert sha(git_read('experimental/world-galley-detail-045/installed-mars-001/package/scene.glb'))=='0b6ee808519f83e73a3ff5b9df336d456e76f7fce91fe493e797702ba226531b'
note='''# Installed facing-aware door selection051; frozen050 history

The five canonical files are the exact root-installed051 revision. It fixes F
selecting a nearer door behind the user while facing another door. Preview and
authored export controllers share the correction. Definitions, meshes, collision
rules and paired-airlock sequencing remain unchanged.051 updates exact renderer
and producer pins so a refreshed immutable preview can still export correctly.

Frozen050 is retained as the preliminary two-file proposal, which could not be
installed alone because its export pins were not coordinated. Its promotion hold
is resolved by051.051 README and DELIVERY preserve the pre-install history;
INSTALLED.json records root's later exact five-file installation. No native051
UI review or owner realism approval is claimed. The CPU package was generated
before installation, not represented as a new installed API trial.

Both actual-Mars controller paths passed7 mechanics checks, plus4 definition and
parity checks,7 export-pin checks and8 installer fixtures. One actual immutable
preview/export/import completed in2.33 seconds,776MiB sampled family peak. Old
previews,116 protected originals and the saved pointer were checked unchanged.
The exported GLB was byte-identical to the existing public045 package; its path
and hash are recorded in EXCLUDED-CONTEXT.json. No owner saved geometry, raw
media, private research, font or native dependency binary is included here.

The portable test_public_closure.py runs050/051 mechanics on a previously public
synthetic habitat fixture, plus viewer callback and recovery fixtures, all in
temporary folders. It does not read or verify the owner's original worlds. Frozen
actual-Mars receipts remain separate historical evidence. The portable script
requires Python and Node only, with optional KIRA_TEST_NODE override; it launches
no renderer, browser, model, server or GLB export. Three's existing vendored source
license is preserved in the candidate closure.

Historical paths are redacted; SOURCE-PROVENANCE records local/public hashes.
Local install-plan hashes and receipt pointers refer to original records. Do not
blindly run redacted installation/actual-export scripts: review and rebind paths
to a checkout, retain exact source/preimage hashes and choose explicit sources.
The default installer is read-only; a matching argument is not authorization.
Protected116 path hashes are historical evidence, not a portable owner-data set.

Old immutable previews retain previous controls. After installation, opening the
current preview creates/reuses a separate build; old packages are never rewritten.
Facing uses a horizontal60-degree half-angle, not pixel picking or occlusion.
Explicit IDs retain proximity/occupancy/interlock rules. The independent043/044
consumer is unchanged. GLB metadata does not execute JS or provide game/VR native
controls. No pressure, exterior EVA or operational habitat simulation is implied.
'''
put(PREFIXES[1]+'PUBLIC-BACKUP.md',note.encode())
test=subprocess.run(['C:/Python314/python.exe','-B','test_public_closure.py'],cwd=O/PREFIXES[1],capture_output=True,timeout=30,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
assert test.returncode==0,(test.stdout.decode(),test.stderr.decode())
check=json.loads(test.stdout);put(PREFIXES[1]+'PUBLIC-CLOSURE-CHECK.json',(json.dumps(check,indent=2)+'\n').encode())
files=[]
for path in sorted(O.rglob('*')):
 if not path.is_file() or '__pycache__' in path.parts:continue
 rel=path.relative_to(O).as_posix();raw=path.read_bytes();text=raw.decode('utf8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I),rel
 if path.suffix=='.py':ast.parse(text)
 if path.suffix=='.json':json.loads(text)
 files.append({'path':rel,'file':str(path),'sha256':sha(raw),'bytes':len(raw),'before_sha256':before.get(rel)})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-door-targeting-024','reviewed':False,'allowed_prefixes':PREFIXES+list(before),
 'message':'Target faced doors consistently in world previews and authored export controls; preserve immutable builds, tests and recovery','files':files}
mf=W/'sep22-backups/world-door-targeting-024.manifest.json'
with mf.open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
delivery={'status':'INSTALLED051_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,'files':len(files),'bytes':sum(r['bytes'] for r in files),
 'canonical_files':5,'frozen050_preserved':True,'portable_synthetic_controller_checks':21,'portable_definition_parity_checks':4,'portable_recovery_tests':8,'preserved_original_inputs':116,'git_mutations':0,'ui_gpu_models':0}
with (H/'DELIVERY.json').open('x',encoding='utf8') as f:json.dump(delivery,f,indent=2);f.write('\n')
print(json.dumps(delivery))
