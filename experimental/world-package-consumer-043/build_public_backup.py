from pathlib import Path
import ast,hashlib,json,re,struct,subprocess
H=Path(__file__).resolve().parent;W=H.parent;S=W/'world-package-consumer-043';O=W/'w043/p'
CLONE=W/'kiraworld-shared-recall-publication-001/repo';BASE='15655e14a800a51d958982c2438680d96954d297';PREFIX='experimental/world-package-consumer-043/'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(rel,b):
 p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def scrub(text):
 for p,label in ((W.parent,'@workspace'),(Path('@kira_root'),'@kira_root'),(Path.home(),'@user_home')):
  for old in (str(p).replace('\\','\\\\'),str(p),p.as_posix()):text=text.replace(old,label)
 return text
def binary_check(b):
 assert struct.unpack_from('<4sII',b)==(b'glTF',2,len(b));n,k=struct.unpack_from('<II',b,12);assert k==0x4e4f534a
 text=b[20:20+n].decode('utf-8');d=json.loads(text);assert scrub(text)==text and not re.search(r'[A-Za-z]:[\\/]|file:/{2}',text)
 assert all('uri' not in x for x in d['buffers']) and all('uri' not in x and x['mimeType']=='image/png' for x in d['images'])
 return {'embedded_pngs':len(d['images']),'local_paths':False}
closure=json.loads((S/'SOURCE-CLOSURE.json').read_bytes())
for rel,pin in closure['files'].items():assert sha((S/rel).read_bytes())==pin['sha256']
existing=subprocess.run(['git','ls-tree','--name-only',BASE,'--',PREFIX.rstrip('/')],cwd=CLONE,capture_output=True,check=True);assert not existing.stdout
records=[];binaries=[]
for p in sorted(S.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 rel=p.relative_to(S).as_posix();b=p.read_bytes();public=b
 if p.suffix=='.glb':binaries.append({'path':PREFIX+rel,'sha256':sha(b),'bytes':len(b),**binary_check(b)})
 else:public=scrub(b.decode('utf-8')).encode('utf-8')
 # Runtime, vendor code and derived package bytes must remain exact.
 if rel in json.loads((S/'REVIEW-PLAN.json').read_bytes())['runtime_files'] or rel.startswith('sample-package/'):assert public==b
 put(PREFIX+rel,public);records.append({'path':PREFIX+rel,'original_sha256':sha(b),'public_sha256':sha(public),'transformation':'exact' if b==public else 'local historical paths replaced'})
put(PREFIX+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf-8')).encode())
put(PREFIX+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
put(PREFIX+'PUBLIC-BINARY-CHECK.json',(json.dumps({'status':'ORIGINAL_DERIVED_GLBS_REVIEWED_FOR_BACKUP','files':binaries,'raw_owner_geometry_research_memories_fonts_native_binaries':False},indent=2)+'\n').encode())
note='''# Public backup: first-person package consumer043

This additive experimental directory is not a canonical application installation.
It includes exact runtime modules, Three 0.180 with its MIT license, a complete
original derived Mars package and CPU tests. The GLB is imported as real meshes;
visible equipment is not recreated from metadata boxes. Portable package runtime
does not require the source world or research. Saved previews remain unchanged.

The final pre-read file-admission change has 12 tests. The relocated public runtime
test runs without Kira, source geometry, a browser, GPU or model. The local actual
importer test decoded embedded textures and bound all six door meshes/colliders;
separate original-controller comparison had zero numerical difference over 178
walking steps and 1,716 door pose comparisons. Browser input and visual review
remain pending. This is a Three first-person prototype, not Unity/Unreal/Godot or
VR readiness. No pressure simulation, working science equipment or realism claim.

Local staging/resource-monitor scripts have redacted path placeholders and are
historical engineering records. test_runtime.mjs and test_admission.mjs are
portable; test_import.mjs requires an explicitly provided pinned local Canvas
decoder. No native decoder/font binary is bundled or downloaded. Optional manual
serve.py binds only to loopback and never launches a browser. All code, histories
and source/public hash transformations are recorded in SOURCE-PROVENANCE.json.
'''
put(PREFIX+'PUBLIC-BACKUP.md',note.encode())
checks=[]
for name in ('test_admission.mjs','test_runtime.mjs'):
 proc=subprocess.run(['C:/Program Files/nodejs/node.exe',name],cwd=O/PREFIX,capture_output=True,timeout=15)
 assert proc.returncode==0,(proc.stdout.decode(),proc.stderr.decode());checks.append(json.loads(proc.stdout))
put(PREFIX+'PUBLIC-CLOSURE-CHECK.json',(json.dumps({'status':'RELOCATED_PUBLIC_CPU_TESTS_PASS','checks':checks,'native_kira_imports':0,'gpu_models_ui_servers':0},indent=2)+'\n').encode())
files=[]
for p in sorted(O.rglob('*')):
 if not p.is_file():continue
 b=p.read_bytes()
 if p.suffix=='.glb':binary_check(b)
 else:
  text=b.decode('utf-8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I)
  if p.suffix=='.py':ast.parse(text)
  if p.suffix=='.json':json.loads(text)
 files.append({'path':p.relative_to(O).as_posix(),'file':str(p),'sha256':sha(b),'bytes':len(b),'before_sha256':None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-package-consumer-018','reviewed':False,
 'allowed_prefixes':[PREFIX],'message':'Add isolated first-person consumer for exported habitat packages with collision and paired doors','files':files}
mf=W/'sep22-backups/world-package-consumer-018.manifest.json'
with mf.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
result={'status':'ISOLATED043_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,
 'review_plan_sha256':sha((S/'REVIEW-PLAN.json').read_bytes()),'files':len(files),'bytes':sum(r['bytes'] for r in files),'canonical_mappings':0,'git_mutations':0,
 'runtime_and_derived_sample_exact':True,'public_relocated_cpu_tests_pass':True,'ui_visual_owner_approval':False}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
