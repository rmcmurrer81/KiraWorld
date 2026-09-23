"""Preserve the first025 snapshot and improve door reach in a new review build."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
H=Path(__file__).resolve().parent;R=H/'revision-002';E=R/'candidate/tools/world_builder_engine'
R.mkdir(exist_ok=False);shutil.copytree(H/'candidate/tools',R/'candidate/tools')
walker=E/'walk_controller.mjs';text=walker.read_text(encoding='utf-8');assert text.count('REACH=1.8;')==1
walker.write_text(text.replace('REACH=1.8;','REACH=2.25;'),encoding='utf-8',newline='\n')
def pin(p):return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest(),'bytes':Path(p).stat().st_size}
old=json.loads((H/'PREVIEW-PLAN.json').read_text());assert all(pin(p)['sha256']==digest for p,digest in old['protected_inputs'].items())
manifest=json.loads(Path(old['preview']['manifest_path']).read_text())
spec=importlib.util.spec_from_file_location('world025_revision002',E/'world_layout_preview.py');backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend);backend.THREE_BUILD=Path(old['three_build'])
preview=backend.create_preview(manifest['inputs']['geometry_source']['path'],manifest['inputs']['research_packet']['path'],manifest['inputs']['blueprint']['path'])
shutil.copyfile(H/'serve_preview.py',R/'serve_preview.py')
plan={**old,'status':'FURNISHED_HABITAT_REVISION002_STAGED_NOT_VISUALLY_REVIEWED','preview':preview,'backend':pin(E/'world_layout_preview.py'),'server':pin(R/'serve_preview.py')}
plan['candidate_sources']={name:pin(E/name) for name in ('walk_controller.mjs','viewer.mjs','index.html','style.css','horizontal_navigation.mjs')}
plan['candidate_sources'].update({name:pin(H/name) for name in ('room_dressing_plan.mjs','room_dressing_render.mjs')})
plan['revision_note']='Interaction reach2.25m allows a0.55m button step to reach a safe position outside the occupied swing volume. Swing and collision bounds are unchanged.'
with (R/'PREVIEW-PLAN.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'status':plan['status'],'plan_sha256':pin(R/'PREVIEW-PLAN.json')['sha256']}))
