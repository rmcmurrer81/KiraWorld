"""Freeze the completed isolated proposal. Refuses existing delivery evidence."""
from pathlib import Path
import hashlib,json
import verify
H=Path(__file__).resolve().parent;B=H.parent/'world-observation-exclusion-055'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(p):return {'sha256':sha(p),'bytes':p.stat().st_size}
def save(name,value):
    with (H/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
save('INTEGRITY.json',verify.verify())
dependency_names=['DELIVERY.json','FROZEN-MANIFEST.json','CANDIDATE-CLOSURE.json','INSTALL-PLAN.json','SOURCE-PINS.json']
save('DEPENDENCIES.json',{'base':'../world-observation-exclusion-055','files':{n:row(B/n) for n in dependency_names},
    'baseline_module':{'path':'../world-observation-exclusion-055/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',**row(B/'candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs')},
    'node':{'path':'C:/Program Files/nodejs/node.exe',**row(Path('C:/Program Files/nodejs/node.exe'))},
    'recovery':'Frozen055 full 22-file candidate plus the three056 overlay files recreates this candidate; no runtime_context, private brief, owner geometry or copied preview is required for CPU tests.'})
files={p.relative_to(H).as_posix():row(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
save('FROZEN-MANIFEST.json',{'status':'FROZEN056_ISOLATED_NOT_INSTALLED','files':files})
save('DELIVERY.json',{'status':'READY_FOR_ROOT_REVIEW_NATIVE_VISUAL_PENDING','manifest':row(H/'FROZEN-MANIFEST.json'),
    'source_closure':row(H/'CANDIDATE-CLOSURE.json'),'diff':row(H/'FROM055.diff'),
    'geometry_tests':row(H/'GEOMETRY-TESTS.json'),'integrity':row(H/'INTEGRITY.json'),
    'files':len(files),'changed_source_files':3,'geometry_cases':14,'actual_rays':630,
    'protected_originals':116,'canonical_installed':False,'native_visual_checked':False,
    'owner_approval':False,'model_gpu_ui_calls':0})
print(json.dumps({'status':'FROZEN056','delivery_sha256':sha(H/'DELIVERY.json'),'manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'source_sha256':sha(H/'CANDIDATE-CLOSURE.json'),'files':len(files)}))
