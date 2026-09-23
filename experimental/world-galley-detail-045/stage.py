from pathlib import Path
import hashlib,json,shutil,difflib,sys

H=Path(__file__).resolve().parent;W=H.parent
K=Path('@kira_root');E=K/'tools/world_builder_engine'
C=H/'candidate/tools/world_builder_engine'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')

if len(sys.argv)>1:
    label=sys.argv[1];assert label.isalnum() and label.startswith('rev')
    history=H/'history'/label;history.mkdir(parents=True,exist_ok=False)
    # Move only this isolated candidate's files, with explicit resolved-boundary
    # checks. The original installed files and owner input trees are read-only.
    for name in ['candidate','baseline','preimages','fixtures','SOURCE-PINS.json','INSTALL-PLAN.json','COMBINED-CHANGES.patch','CANDIDATE-CLOSURE.json']:
        p=H/name;destination=history/name
        assert p.resolve().is_relative_to(H.resolve()) and destination.resolve().is_relative_to(H.resolve())
        p.rename(destination)
C.mkdir(parents=True,exist_ok=False)
shutil.copytree(E/'layout_package_assets',C/'layout_package_assets',ignore=shutil.ignore_patterns('__pycache__'))
rel='layout_package_assets/source/room_dressing_render.mjs'
old=(E/rel).read_text(encoding='utf-8')
a=old.index("    }else if(kind==='galley'){")
b=old.index("    }else if(kind==='personal_storage'",a)
new=old[:a]+(H/'galley.fragment.mjs').read_text(encoding='utf-8')+old[b:]
(C/rel).write_text(new,encoding='utf-8',newline='\n')
viewer=(E/'viewer.mjs').read_text(encoding='utf-8')
embedded=old.replace('export function ','function ').strip()
assert viewer.count(embedded)==1
(C/'viewer.mjs').write_text(viewer.replace(embedded,new.replace('export function ','function ').strip(),1),encoding='utf-8',newline='\n')
api=(E/'layout_package_export.py').read_text(encoding='utf-8')
assert api.count(sha(E/'viewer.mjs'))==1
(C/'layout_package_export.py').write_text(api.replace(sha(E/'viewer.mjs'),sha(C/'viewer.mjs')),encoding='utf-8',newline='\n')
scene=C/'layout_package_assets/authored_scene.mjs'
text=scene.read_text(encoding='utf-8')
assert 'includes isolated042 static bunk geometry detail.' in text
scene.write_text(text.replace('includes isolated042 static bunk geometry detail.','includes static bunk and galley geometry details042/045.'),encoding='utf-8',newline='\n')
producer=C/'layout_package_assets/PRODUCER-PINS.json'
pins=json.loads(producer.read_bytes())
for r in ['source/room_dressing_render.mjs','authored_scene.mjs']:
    p=C/'layout_package_assets'/r;pins['files'][r]={'sha256':sha(p),'bytes':p.stat().st_size}
producer.write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')

(H/'baseline').mkdir()
shutil.copyfile(E/rel,H/'baseline/room_dressing_render.mjs')
shutil.copyfile(E/'viewer.mjs',H/'baseline/viewer.mjs')
rows=[];diff=[]
for r in ['viewer.mjs','layout_package_export.py',rel,'layout_package_assets/authored_scene.mjs','layout_package_assets/PRODUCER-PINS.json']:
    p=E/r;q=C/r;pre=H/'preimages/tools/world_builder_engine'/r;pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,pre)
    rows.append({'relative_path':'tools/world_builder_engine/'+r,'target':str(p),'before_sha256':sha(p),'preimage':str(pre),'after':{'path':str(q),'sha256':sha(q),'bytes':q.stat().st_size}})
    diff.extend(difflib.unified_diff(p.read_text(encoding='utf-8').splitlines(True),q.read_text(encoding='utf-8').splitlines(True),fromfile='installed042/'+r,tofile='candidate045/'+r))
protected=json.loads((W/'world-bunk-detail-042/INSTALL-PLAN.json').read_bytes())['protected_inputs']
assert len(protected)==116 and all(sha(Path(p))==v for p,v in protected.items())
put(H/'SOURCE-PINS.json',{str(p.relative_to(E)).replace('\\','/'):sha(p) for p in E.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
put(H/'INSTALL-PLAN.json',{'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':rows,'protected_inputs':protected,'required_before_install':['Targeted geometry/route/support tests','Actual CPU export/importer validation','Root artifact review and exact install authorization'],'old_previews':'Preserve all existing immutable previews and owner pointers.'})
(H/'COMBINED-CHANGES.patch').write_text(''.join(diff),encoding='utf-8',newline='\n')
put(H/'CANDIDATE-CLOSURE.json',{p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file() and '__pycache__' not in p.parts})
(H/'fixtures').mkdir()
for kind in ['base','renamed','wider','translated']:shutil.copyfile(W/'world-bunk-detail-042/fixtures'/(kind+'.json'),H/'fixtures'/(kind+'.json'))
print(json.dumps({'status':'045_STAGED_ISOLATED','files_changed':len(rows),'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'protected_inputs':len(protected),'canonical_changes':0}))
