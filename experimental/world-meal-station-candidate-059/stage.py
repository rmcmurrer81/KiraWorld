"""Isolated059 geometry/source staging; installed056 and owner data remain read-only."""
from pathlib import Path
import hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write((json.dumps(value,indent=2)+'\n').encode())
assert not C.exists()
closure=json.loads((W/'world-installed-observation-export-057/INSTALLED-SOURCE-CLOSURE.json').read_bytes())
for rel,row in closure.items():assert sha(K/rel)==row['sha256']
shutil.copytree(E,C,ignore=shutil.ignore_patterns('__pycache__'))
renderrel='layout_package_assets/source/room_dressing_render.mjs';planrel='layout_package_assets/source/room_dressing_plan.mjs'
oldrender=(E/renderrel).read_text(encoding='utf-8');oldplan=(E/planrel).read_text(encoding='utf-8')
marker="    }else if(kind==='personal_storage'||kind==='sample_storage'){";assert oldrender.count(marker)==1
newrender=oldrender.replace(marker,(H/'meal_station.fragment.mjs').read_text(encoding='utf-8')+marker,1)
marker='  // Bound renderer complexity as well as collision complexity.';assert oldplan.count(marker)==1
newplan=oldplan.replace(marker,(H/'placement.fragment.mjs').read_text(encoding='utf-8')+marker,1)
(C/renderrel).write_bytes(newrender.encode());(C/planrel).write_bytes(newplan.encode())
viewer=(E/'viewer.mjs').read_text(encoding='utf-8')
def embed(text):return text.replace('export function ','function ').replace('export const ','const ').strip()
assert viewer.count(embed(oldrender))==viewer.count(embed(oldplan))==1
viewer=viewer.replace(embed(oldrender),embed(newrender),1).replace(embed(oldplan),embed(newplan),1)
(C/'viewer.mjs').write_bytes(viewer.encode())
api=(E/'layout_package_export.py').read_text(encoding='utf-8');assert api.count(sha(E/'viewer.mjs'))==1
(C/'layout_package_export.py').write_bytes(api.replace(sha(E/'viewer.mjs'),sha(C/'viewer.mjs')).encode())
scene=C/'layout_package_assets/authored_scene.mjs';text=scene.read_text(encoding='utf-8')
text=text.replace('includes static bunk and galley geometry details042/045.','includes static bunk, galley and meal-station geometry details042/045/059.')
scene.write_bytes(text.encode())
producer=C/'layout_package_assets/PRODUCER-PINS.json';pins=json.loads(producer.read_bytes())
for rel in ('source/room_dressing_plan.mjs','source/room_dressing_render.mjs','authored_scene.mjs'):
    path=C/'layout_package_assets'/rel;pins['files'][rel]={'sha256':sha(path),'bytes':path.stat().st_size}
producer.write_bytes((json.dumps(pins,indent=2)+'\n').encode())
changed=['viewer.mjs','layout_package_export.py',planrel,renderrel,'layout_package_assets/authored_scene.mjs','layout_package_assets/PRODUCER-PINS.json']
rows=[];diff=[]
for rel in changed:
    before=E/rel;after=C/rel;pre=H/'preimages/tools/world_builder_engine'/rel;pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(before,pre)
    rows.append({'relative_path':'tools/world_builder_engine/'+rel,'target':str(before),'before_sha256':sha(before),'preimage':str(pre),
                 'after':{'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}})
    diff.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(True),after.read_text(encoding='utf-8').splitlines(True),fromfile='installed056/'+rel,tofile='candidate059/'+rel))
protected=json.loads((W/'world-observation-trim-056/native-successor-001/INSTALL-PLAN.json').read_bytes())['protected_inputs']
assert len(protected)==116 and all(sha(Path(p))==v for p,v in protected.items())
put(H/'SOURCE-PINS.json',{r:dict(v) for r,v in closure.items()})
put(H/'INSTALL-PLAN.json',{'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':rows,'protected_inputs':protected,
    'required_before_install':['Targeted geometry/route/support and omission tests','Preview/export shared-source checks','Root visual review and exact installation authorization'],
    'old_previews':'Remain immutable and valid with their saved renderer; new appearance requires new preview, never old-copy overwrite.'})
(H/'SOURCE.diff').write_bytes(''.join(diff).encode())
put(H/'CANDIDATE-CLOSURE.json',{p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file()})
fixtures=H/'fixtures';fixtures.mkdir()
for variant in ('base','renamed','wider','translated'):shutil.copyfile(W/'world-bunk-detail-042/fixtures'/(variant+'.json'),fixtures/(variant+'.json'))
job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json';brief=json.loads(job.read_bytes())['brief']['prompt']
assert 'original' in brief.lower() and 'mars base' in brief.lower() and 'habitat' in brief.lower()
put(H/'BRIEF-RESEARCH-BASIS.json',{'saved_job_id':'world_research_c391ffbffc7352612392','job_sha256':sha(job),
    'request_sha256':hashlib.sha256(brief.encode()).hexdigest(),'explicit_original_mars_habitat_request_read':True,
    'owner_dimensions_are_design_decisions':True,'raw_brief_copied':False,
    'research':{'path':str(W/'world-film-layout-reference-040/NOTES.md'),'sha256':sha(W/'world-film-layout-reference-040/NOTES.md')},
    'design_inference':'A meal surface with crew seating makes the habitat function visible. Dimensions and meshes are original prototype decisions, not copied or certified.'})
print(json.dumps({'status':'ISOLATED059_STAGED','changed_files':len(rows),'source_files':len(closure),'protected_originals':len(protected),'canonical_changes':0}))
