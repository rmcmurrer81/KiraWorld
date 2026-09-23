from pathlib import Path
import ast,hashlib,json
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');C=H/'candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
def pin(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def put(name,value):
    with (H/name).open('xb') as f:f.write((json.dumps(value,indent=2)+'\n').encode())
assert not (H/'DELIVERY.json').exists()
base=read(H/'SOURCE-PINS.json');candidate=read(H/'CANDIDATE-CLOSURE.json');plan=read(H/'INSTALL-PLAN.json')
assert len(base)==len(candidate)==42 and len(plan['files'])==6
for rel,row in base.items():assert sha(K/rel)==row['sha256']
for rel,row in candidate.items():assert sha(C/rel)==row['sha256'] and (C/rel).stat().st_size==row['bytes']
changed={r for r in candidate if candidate[r]['sha256']!=base[r]['sha256']}
assert changed=={r['relative_path'] for r in plan['files']}
for row in plan['files']:
    assert sha(row['target'])==sha(row['preimage'])==row['before_sha256']
    assert sha(row['after']['path'])==row['after']['sha256']
assert len(plan['protected_inputs'])==116
for path,digest in plan['protected_inputs'].items():assert sha(path)==digest
synthetic=read(H/'TEST-RESULT.json');actual=read(H/'TEST-RESULT-SAVED.json');compat=read(H/'PREVIEW-CONTRACT-RESULT.json')
assert synthetic['status']==actual['status']=='PASS_MEAL_GEOMETRY_PLACEMENT_OMISSION_AND_SHARED_EXPORT'
assert len(synthetic['shapes'])==4 and len(actual['shapes'])==1
assert compat['status']=='PASS_INSTALLED056_SAVED_PREVIEW_AND059_APPEARANCE_BOUNDARY'
dependencies=[W/'world-crew-dining-assessment-058/DELIVERY.json',W/'world-film-layout-reference-040/NOTES.md',
    W/'world-installed-observation-export-057/INSTALLED-SOURCE-CLOSURE.json',
    W/'world-observation-trim-056/native-successor-001/INSTALLED.json',
    W/'world-observation-trim-056/native-successor-001/installed-preview-001/REFRESH-RESULT.json',
    K/'tools/world_saved_research.py']
put('DEPENDENCIES.json',{'files':[pin(p) for p in dependencies],
    'actual_geometry_binding':{'path':str(K/'Data/world_layout_previews/layout-c49fdd7e0af7439783fa6330/geometry.json'),
    'sha256':'1af9ae1254356f0523f722d284b140b8e34eb6af3bf236ceef91ad5f145a9d75'},
    'owner_source_files_copied':False,'synthetic_fixtures_included':True,'canonical_source_and_Three_closure_included':True})
put('BEFORE-AFTER.json',{'status':'ISOLATED059_FUNCTIONAL_GEOMETRY_CANDIDATE_NOT_INSTALLED','before_equipment_count':16,'after_equipment_count':17,
    'old_dressing_colliders':51,'new_dressing_colliders':52,'new_meshes':20,'new_vertices':4142,'new_triangles':5936,
    'prior_equipment_and_architecture_unchanged':True,'source_rooms_or_doors_changed':False,'exact_shared_geometry':True,
    'new_actual_export':False,'new_visual_review':False,'owner_approval':False})
files={}
for p in sorted(H.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts:continue
    if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'))
    files[p.relative_to(H).as_posix()]={'sha256':sha(p),'bytes':p.stat().st_size}
put('FROZEN-MANIFEST.json',{'status':'ISOLATED059_FROZEN_FOR_ROOT_REVIEW','files':files})
put('DELIVERY.json',{'status':'ISOLATED059_READY_FOR_ROOT_SOURCE_REVIEW_VISUAL_PENDING','frozen':pin(H/'FROZEN-MANIFEST.json'),
    'source_diff':pin(H/'SOURCE.diff'),'plan':pin(H/'INSTALL-PLAN.json'),'candidate_source':pin(H/'CANDIDATE-CLOSURE.json'),
    'synthetic_tests':pin(H/'TEST-RESULT.json'),'actual_saved_geometry_tests':pin(H/'TEST-RESULT-SAVED.json'),
    'preview_compatibility':pin(H/'PREVIEW-CONTRACT-RESULT.json'),'changed_files':6,'source_files':42,
    'owner_originals_unchanged':116,'models_GPU_UI_new_exports':0,'installed':False,'visual_or_owner_approval':False,
    'remaining':['Root source review','Actual isolated059 immutable preview and CPU GLB/importer check','Visual inspection before promotion']})
print(json.dumps({'delivery':pin(H/'DELIVERY.json'),'source_diff':pin(H/'SOURCE.diff'),'plan':pin(H/'INSTALL-PLAN.json'),'frozen_files':len(files)}))
