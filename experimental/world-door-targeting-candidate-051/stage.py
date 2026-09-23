"""Stage coordinated051 from frozen050; installed files are read-only."""
from pathlib import Path
import difflib,hashlib,json,shutil

H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');E=K/'tools/world_builder_engine'
F=W/'world-door-targeting-candidate-050';C=H/'candidate/tools/world_builder_engine'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,value):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
assert sha(F/'REVIEW-PLAN.json')=='d3363d1e43fac45655548ee3fed1b6b993f55d293821352b8e01ca08cf351caa'
C.mkdir(parents=True,exist_ok=False)
shutil.copytree(E/'layout_package_assets',C/'layout_package_assets',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('walk_controller.mjs','viewer.mjs'):
 shutil.copyfile(F/'candidate/tools/world_builder_engine'/name,C/name)
shutil.copyfile(E/'horizontal_navigation.mjs',C/'horizontal_navigation.mjs')
base=(E/'walk_controller.mjs').read_text(encoding='utf-8');next=(C/'walk_controller.mjs').read_text(encoding='utf-8')
portable=C/'layout_package_assets/source/walk_controller.mjs';text=portable.read_text(encoding='utf-8')
# Apply exactly050's three changed regions, retaining portable definitions().
for start,end in [('  function nearest(', '    candidates.sort('),
                  ('      roomId:current?.id', '\n  function look('),
                  ('  function toggleDoor(', '\n  return Object.freeze({snapshot')]:
 old=base[base.index(start):base.index(end,base.index(start))]
 new=next[next.index(start):next.index(end,next.index(start))]
 assert text.count(old)==1,(start,'source divergence')
 text=text.replace(old,new,1)
assert 'function definitions()' in text
portable.write_text(text,encoding='utf-8',newline='\n')
api=(E/'layout_package_export.py').read_text(encoding='utf-8')
for name in ('viewer.mjs','walk_controller.mjs'):
 assert api.count(sha(E/name))==1
 api=api.replace(sha(E/name),sha(C/name))
(C/'layout_package_export.py').write_text(api,encoding='utf-8',newline='\n')
producer=C/'layout_package_assets/PRODUCER-PINS.json';pins=json.loads(producer.read_bytes())
pins['files']['source/walk_controller.mjs']={'sha256':sha(portable),'bytes':portable.stat().st_size}
producer.write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')
rows=[];diff=[]
for r in ('walk_controller.mjs','viewer.mjs','layout_package_export.py','layout_package_assets/source/walk_controller.mjs','layout_package_assets/PRODUCER-PINS.json'):
 p=E/r;q=C/r;pre=H/'preimages/tools/world_builder_engine'/r;pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,pre)
 rows.append({'relative_path':'tools/world_builder_engine/'+r,'target':str(p),'before_sha256':sha(p),'preimage':str(pre),'after':{'path':str(q),'sha256':sha(q),'bytes':q.stat().st_size}})
 diff.extend(difflib.unified_diff(p.read_text(encoding='utf-8').splitlines(True),q.read_text(encoding='utf-8').splitlines(True),fromfile='installed/'+r,tofile='candidate051/'+r))
protected=json.loads((F/'REVIEW-PLAN.json').read_bytes())['protected_inputs']
assert len(protected)==116 and all(sha(Path(p))==v for p,v in protected.items())
put(H/'SOURCE-PINS.json',{p.relative_to(E).as_posix():sha(p) for p in E.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
put(H/'INSTALL-PLAN.json',{'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':rows,'protected_inputs':protected,
 'required_before_install':['Paired portable/frontend mechanics and definitions tests','Actual immutable preview and CPU GLB export/import validation','Root exact-plan review and authorization'],
 'old_previews':'Preserve all existing immutable previews and saved job pointers. Refresh/Open current preview after installation creates or reuses a separate build; old previews retain their previous controls.',
 'limitations':['Horizontal facing selection only; no pixel picking or occlusion raycasts.','Native game-engine controls and VR remain unimplemented; metadata packages do not execute JavaScript.','Independent experimental package consumer043/044 is unchanged.']})
(H/'SOURCE.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
put(H/'CANDIDATE-CLOSURE.json',{p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file() and '__pycache__' not in p.parts})
print(json.dumps({'status':'051_STAGED','files_changed':len(rows),'plan_sha256':sha(H/'INSTALL-PLAN.json'),'canonical_changes':0}))
