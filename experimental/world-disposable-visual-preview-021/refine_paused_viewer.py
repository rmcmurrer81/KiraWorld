from pathlib import Path
import hashlib
import json
import subprocess
H=Path(__file__).resolve().parent
assert not (H/'SERVER-STARTED.json').exists()
p=H/'assets/viewer.mjs'
t=p.read_text(encoding='utf-8')
assert 'displayDirty' not in t
t=t.replace('batchStartedAt=0;', 'batchStartedAt=0;let displayDirty=true;',1)
t=t.replace('function animate(now){const elapsed=', 'function animate(now){requestAnimationFrame(animate);if(paused&&!displayDirty){last=now;accumulator=0;return;}displayDirty=false;const elapsed=')
t=t.replace('renderer.render(scene,camera);requestAnimationFrame(animate);}', 'renderer.render(scene,camera);}')
t=t.replace('new ResizeObserver(()=>{const r=', 'document.addEventListener("click",()=>{displayDirty=true;});document.addEventListener("change",()=>{displayDirty=true;});\nnew ResizeObserver(()=>{displayDirty=true;const r=')
p.write_text(t,encoding='utf-8',newline='\n')
subprocess.run(['C:/Program Files/nodejs/node.exe','--check',str(p)],check=True)
planpath=H/'PLAN.json';plan=json.loads(planpath.read_text(encoding='utf-8'))
plan['assets']['viewer.mjs'].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
plan['paused_render_behavior']='No physics stepping, contact metric recomputation or rendering between UI and resize events while paused.'
planpath.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'plan_sha256':hashlib.sha256(planpath.read_bytes()).hexdigest(),'viewer_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'STATIC_READY_NOT_LAUNCHED'}))
