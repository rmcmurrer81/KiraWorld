"""Preserve frozen056; refresh the export's exact viewer pin in a successor."""
from pathlib import Path
import difflib,hashlib,json,shutil
import verify
P=Path(__file__).resolve().parent;H=P/'native-successor-001';B=P.parent/'world-observation-exclusion-055'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
def write(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
verify.verify();assert not H.exists();H.mkdir()
shutil.copytree(P/'candidate',H/'candidate');shutil.copytree(P/'canonical-preimages',H/'canonical-preimages')
for n in ('SOURCE-PINS.json','ACTUAL-PRESENTATION.json'):shutil.copyfile(P/n,H/n)
rel='tools/world_builder_engine/layout_package_export.py';path=H/'candidate'/rel
old=path.read_text(encoding='utf-8');oldpin='f8b14f8cf1fec001541b3719246fa603d5985a5b45c0b86a62e67eb1601c405c';newpin=sha(H/'candidate/tools/world_builder_engine/viewer.mjs')
assert old.count(oldpin)==1;new=old.replace(oldpin,newpin);path.write_text(new,encoding='utf-8',newline='\n')
write(H/'FROM-FROZEN056.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen056/'+rel,tofile='successor056/'+rel)))
closure={p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((H/'candidate').rglob('*')) if p.is_file()}
put(H/'CANDIDATE-CLOSURE.json',closure)
plan=json.loads((P/'INSTALL-PLAN.json').read_bytes());diff=[]
for row in plan['files']:
 rel=row['relative_path'];pre=H/'canonical-preimages'/rel;after=H/'candidate'/rel
 row['preimage']=str(pre);row['after']={'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}
 assert sha(pre)==sha(row['target'])==row['before_sha256']
 diff.extend(difflib.unified_diff(pre.read_text(encoding='utf-8').splitlines(True),after.read_text(encoding='utf-8').splitlines(True),fromfile='installed051/'+rel,tofile='candidate056-successor/'+rel))
put(H/'INSTALL-PLAN.json',plan);write(H/'SOURCE.diff',''.join(diff))
for name in ('install_exact.py','test_installer.py','serve_review.py'):
 s=(P/'installation'/name).read_text(encoding='utf-8')
 s=s.replace(sha(P/'INSTALL-PLAN.json'),sha(H/'INSTALL-PLAN.json')).replace(sha(P/'CANDIDATE-CLOSURE.json'),sha(H/'CANDIDATE-CLOSURE.json'))
 write(H/'installation'/name,s)
s=(P/'prepare_review.py').read_text(encoding='utf-8').replace("H.parent/'world-observation-exclusion-055/", "H.parents[1]/'world-observation-exclusion-055/")
write(H/'prepare_review.py',s)
put(H/'PRIOR-PREPARATION-HOLD.json',{'status':'FROZEN056_NATIVE_PREPARATION_HELD','original_delivery_sha256':sha(P/'DELIVERY.json'),
 'command':'C:/Python314/python.exe -X utf8 -B work/world-observation-trim-056/prepare_review.py','exit_code':1,
 'observed_error':'ExportHeld: This saved preview uses an unsupported appearance version. Open current preview, then export again.',
 'cause':'layout_package_export.RENDERER retained the old viewer digest while056 changed the copied viewer. No guard was bypassed; the successor refreshes only that constant.',
 'original_candidate_modified':False,'server_started':False,'installed':False})
verify.verify();print(json.dumps({'status':'056_SUCCESSOR_STAGED','plan_sha256':sha(H/'INSTALL-PLAN.json'),'closure_sha256':sha(H/'CANDIDATE-CLOSURE.json'),'export_sha256':sha(path)}))
