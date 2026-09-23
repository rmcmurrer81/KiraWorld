"""Stage a new furnished preview of existing layout bytes; no model/server/UI."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,shutil
H=Path(__file__).resolve().parent;K=Path.home()/'Kira';E=H/'candidate/tools/world_builder_engine'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return {'path':str(Path(p).resolve()),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def save(p,obj):
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n')
protected={}
for name in ('world_research_jobs','world_original_components','world_bedding_studies'):
 for p in (K/'Data'/name).rglob('*'):
  if p.is_file():protected[str(p)]=sha(p)
for name in ('walk_controller.mjs','viewer.mjs','index.html','style.css'):
 p=K/'tools/world_builder_engine'/name
 assert sha(p)==sha(H.parent/'world-working-doors-candidate-024/baseline'/name)
 protected[str(p)]=sha(p)
manifest_path=K/'Data/world_layout_previews/layout-a37f864587b3ee075e21ccd1/manifest.json'
assert sha(manifest_path)=='f99bbbe4fde564e1f48814c899b85ca6f78b0ffe9466a4a88ccabd139999313a'
source=json.loads(manifest_path.read_text());protected[str(manifest_path)]=sha(manifest_path)
for row in [*source['inputs'].values(),*source['assets'].values()]:protected[row['path']]=sha(row['path'])
spec=importlib.util.spec_from_file_location('isolated_world025_preview',E/'world_layout_preview.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.THREE_BUILD=Path(source['assets']['/three.module.js']['path']).parent
preview=module.create_preview(source['inputs']['geometry_source']['path'],source['inputs']['research_packet']['path'],source['inputs']['blueprint']['path'])
assert all(sha(p)==digest for p,digest in protected.items())
shutil.copyfile(H.parent/'world-working-doors-candidate-024/serve_preview.py',H/'serve_preview.py')
sources={name:pin(E/name) for name in ('walk_controller.mjs','viewer.mjs','index.html','style.css','horizontal_navigation.mjs')}
sources.update({name:pin(H/name) for name in ('room_dressing_plan.mjs','room_dressing_render.mjs')})
plan={'status':'FURNISHED_HABITAT_STAGED_NOT_VISUALLY_REVIEWED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'preview':preview,'backend':pin(E/'world_layout_preview.py'),'server':pin(H/'serve_preview.py'),'three_build':str(module.THREE_BUILD),
 'protected_inputs':protected,'candidate_sources':sources,'test_result':pin(H/'TEST-RESULT-003.json'),
 'purpose':'Review authored distinct equipment rooms, physical doors, mounted signs, wall panels and task lighting. The existing base appearance was owner-rejected; this new presentation has not been visually accepted.',
 'installed':False,'models_called':0,'gpu_started':False,'owner_files_unchanged':True,'saved_job_pointer_changed':False,'runtime_limit_seconds':300,
 'limits':['Procedural authored prototype; no claim of photorealism, true pressure airlock or functional life-support/science equipment.','026 compatibility is needed before any renderer installation.']}
save(H/'PREVIEW-PLAN.json',plan)
print(json.dumps({'status':plan['status'],'plan_sha256':sha(H/'PREVIEW-PLAN.json'),'manifest_path':preview['manifest_path'],'protected_files':len(protected)}))
