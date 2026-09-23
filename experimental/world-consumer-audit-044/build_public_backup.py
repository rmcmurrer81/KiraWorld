from pathlib import Path
import ast,hashlib,json,re,struct,subprocess
H=Path(__file__).resolve().parent;W=H.parent;S=W/'world-consumer-audit-044';O=W/'w044/p';CLONE=W/'kiraworld-shared-recall-publication-001/repo'
BASE='2ad6feef562ae87c443499415520ba5c97684c67';PREFIX='experimental/world-consumer-audit-044/'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(rel,b):
 p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def scrub(text):
 for p,label in ((W.parent,'@workspace'),(Path('@kira_root'),'@kira_root'),(Path.home(),'@user_home')):
  for old in (str(p).replace('\\','\\\\'),str(p),p.as_posix()):text=text.replace(old,label)
 return text
def glbcheck(b):
 assert struct.unpack_from('<4sII',b)==(b'glTF',2,len(b));n,k=struct.unpack_from('<II',b,12);assert k==0x4e4f534a
 text=b[20:20+n].decode();j=json.loads(text);assert scrub(text)==text and not re.search(r'[A-Za-z]:[\\/]|file:/{2}',text)
 assert all('uri' not in v for v in j['buffers']) and all('uri' not in v and v['mimeType']=='image/png' for v in j['images']);return len(j['images'])
closure=json.loads((S/'SOURCE-CLOSURE.json').read_bytes());assert all(sha((S/p).read_bytes())==v['sha256'] for p,v in closure['files'].items())
check=subprocess.run(['git','ls-tree','--name-only',BASE,'--',PREFIX.rstrip('/')],cwd=CLONE,capture_output=True,check=True);assert not check.stdout
records=[];binary=[]
for p in sorted(S.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 rel=p.relative_to(S).as_posix();raw=p.read_bytes();public=raw
 if p.suffix=='.glb':binary.append({'path':PREFIX+rel,'sha256':sha(raw),'bytes':len(raw),'embedded_images':glbcheck(raw)})
 else:public=scrub(raw.decode('utf-8')).encode('utf-8')
 if rel.startswith(('candidate/','baseline/')):assert public==raw
 put(PREFIX+rel,public);records.append({'path':PREFIX+rel,'original_sha256':sha(raw),'public_sha256':sha(public),'transformation':'exact' if raw==public else 'local historical paths replaced'})
put(PREFIX+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf-8')).encode())
put(PREFIX+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
put(PREFIX+'PUBLIC-BINARY-CHECK.json',(json.dumps({'status':'UNCHANGED_ORIGINAL_DERIVED_GLB_BACKUP','files':binary,'owner_raw_research_geometry_memories_fonts_native_binaries':False},indent=2)+'\n').encode())
put(PREFIX+'PUBLIC-BACKUP.md',b'''# Consumer044 public backup

Additive isolated successor of043. Only app.mjs, package_loader.mjs and the new
scene_disposal.mjs differ; canonical application paths are untouched. Exact
candidate/baseline code, original derived GLB and pinned MIT Three runtime are
included. No native decoder/font binary, raw owner world or research is bundled.

The actual app handlers are tested with DOM/renderer doubles. No browser was
opened, and these tests do not grant visual/input/owner approval. Runtime physics
is byte-identical to043. The valid package still imports through the real CPU
GLTFLoader; file hash consistency is not publisher authentication. Embedded PNG
budgets are specific to the authored recipe, not a hostile-file sandbox.

Historical local helper paths are placeholders. Focused Node tests in README
work in this checkout and write new receipts to fresh destinations. VM Modules
is experimental only for the audit harness; it is not a browser dependency.
No installation, Git mutation, models, GPU work, server or UI was performed here.
''')
checks=[]
commands=[['test_glb_admission.mjs','candidate','fixed','PUBLIC-URI-CHECK.json'],['test_png_admission.mjs','candidate','fixed','PUBLIC-PNG-CHECK.json'],['--experimental-vm-modules','test_ui_lifecycle.mjs','candidate','fixed','PUBLIC-UI-CHECK.json'],['--experimental-vm-modules','test_disposal.mjs','candidate','PUBLIC-CLEANUP-CHECK.json'],['test_session_reset.mjs','candidate','PUBLIC-SESSION-CHECK.json']]
for args in commands:
 result=subprocess.run(['C:/Program Files/nodejs/node.exe',*args],cwd=O/PREFIX,capture_output=True,timeout=15)
 assert result.returncode==0,(result.stdout.decode(),result.stderr.decode());checks.append({'command':args,'summary':json.loads(result.stdout)})
put(PREFIX+'PUBLIC-CLOSURE-CHECK.json',(json.dumps({'status':'RELOCATED_PUBLIC_FOCUSED_TESTS_PASS','checks':checks,'ui_gpu_models_servers':0},indent=2)+'\n').encode())
files=[]
for p in sorted(O.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes()
 if p.suffix=='.glb':glbcheck(raw)
 else:
  text=raw.decode('utf-8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I)
  if p.suffix=='.py':ast.parse(text)
  if p.suffix=='.json':json.loads(text)
 files.append({'path':p.relative_to(O).as_posix(),'file':str(p),'sha256':sha(raw),'bytes':len(raw),'before_sha256':None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-consumer-audit-019','reviewed':False,'allowed_prefixes':[PREFIX],
 'message':'Harden experimental world-package loading lifecycle and embedded PNG admission','files':files}
mf=W/'sep22-backups/world-consumer-audit-019.manifest.json'
with mf.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
result={'status':'ISOLATED044_PUBLIC_BACKUP_READY_FOR_ROOT_REVIEW','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,
 'review_plan_sha256':sha((S/'REVIEW-PLAN.json').read_bytes()),'files':len(files),'bytes':sum(f['bytes'] for f in files),'canonical_mappings':0,
 'portable_focused_tests_pass':True,'candidate_baseline_and_derived_glb_exact':True,'source_worlds_modified':False,'ui_visual_owner_approval':False,'git_mutations':0}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
