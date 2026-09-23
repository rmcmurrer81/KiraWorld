"""Prepare bounded read-only visual inspection of019 without touching owner data."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess

H=Path(__file__).resolve().parent
D=H.parent/'world-disposable-visual-preview-021'
K=Path('@user_home/Kira')
S=K/'tools/world_builder_components/bedding'
OLD=K/'Data/world_bedding_studies/bedding-2a98988111c91b6201326647'
fixture=H.parent/'world-frame-contact-perf-candidate/fixtures/wide.json'
D.mkdir(exist_ok=False);A=D/'assets';A.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
originals=[]
for name in ['index.html','style.css','viewer.mjs']:
 originals.append(row(S/name));shutil.copy2(S/name,A/name)
for name in ['three.module.js','three.core.js','THREE-LICENSE.txt','canvas_recording.mjs']:
 originals.append(row(OLD/name));shutil.copy2(OLD/name,A/name)
for p in sorted((H/'candidate').glob('*.mjs')):
 originals.append(row(p));shutil.copy2(p,A/p.name)
originals.append(row(fixture));data=json.loads(fixture.read_text(encoding='utf-8'))
data.update(contract='isolated_world019_visual_fixture',frame_id='review-wide-fixture-019',name='Disposable World019 wide-frame inspection',visual_acceptance=False,world_placement='not_placed')
(A/'study.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
viewer=(A/'viewer.mjs').read_text(encoding='utf-8')
viewer=viewer.replace("import {attachCanvasRecorder} from './canvas_recording.mjs';",'// Recording is disabled in this read-only disposable inspection.')
viewer=viewer.replace('paused=false,frames=0,lastFrameMs=0;', 'paused=true,frames=0,lastFrameMs=0,runUntilFrame=0,batchStartedAt=0;')
viewer=viewer.replace('batchStartedAt=0;', 'batchStartedAt=0;let displayDirty=true;',1)
before="paused=false;$('pause').textContent='Pause';$('status').textContent='Gravity is settling the original cloth mesh.';"
after="paused=true;runUntilFrame=0;batchStartedAt=0;$('pause').textContent='Run 12 frames';$('status').textContent='Paused disposable019 preview. Up to 120 actual solver frames; no saved world is changed.';"
assert before in viewer;viewer=viewer.replace(before,after)
old="$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'Resume':'Pause';};"
new="$('pause').onclick=()=>{if(!paused){paused=true;$('pause').textContent='Run 12 frames';return;}if(frames>=120){$('status').textContent='120-frame review limit reached. Preserve this result.';return;}runUntilFrame=Math.min(frames+12,120);batchStartedAt=performance.now();paused=false;$('pause').textContent='Pause';};"
assert old in viewer;viewer=viewer.replace(old,new)
old="reset();attachCanvasRecorder(canvas,$('record'),$('stop'),$('record-status'),globalThis,$('download'));let last=performance.now(),accumulator=0;"
new="reset();$('record').disabled=true;$('stop').disabled=true;$('record-status').textContent='Read-only review: recording and saving are disabled.';let last=performance.now(),accumulator=0;"
assert old in viewer;viewer=viewer.replace(old,new)
old='frames++;count++;}'
new="frames++;count++;if(frames>=runUntilFrame||performance.now()-batchStartedAt>15000){paused=true;$('pause').textContent='Run 12 frames';$('status').textContent='Paused after actual solver frame '+frames+'. No world or owner study has been saved.';break;}}"
assert old in viewer;viewer=viewer.replace(old,new)
viewer=viewer.replace('function animate(now){const elapsed=', 'function animate(now){requestAnimationFrame(animate);if(paused&&!displayDirty){last=now;accumulator=0;return;}displayDirty=false;const elapsed=')
viewer=viewer.replace('renderer.render(scene,camera);requestAnimationFrame(animate);}', 'renderer.render(scene,camera);}')
viewer=viewer.replace('new ResizeObserver(()=>{const r=', 'document.addEventListener("click",()=>{displayDirty=true;});document.addEventListener("change",()=>{displayDirty=true;});\nnew ResizeObserver(()=>{displayDirty=true;const r=')
(A/'viewer.mjs').write_text(viewer,encoding='utf-8',newline='\n')
html=(A/'index.html').read_text(encoding='utf-8').replace('Original geometry · compliant support','Isolated019 · not installed · paused review')
html=html.replace('<title>World Builder · original frame and bedding study</title>','<title>World019 · disposable bounded visual inspection</title>')
(A/'index.html').write_text(html,encoding='utf-8',newline='\n')
owner={str(p.relative_to(K)).replace('\\','/'):sha(p) for folder in ['Data/world_bedding_studies','Data/world_original_components'] for p in sorted((K/folder).rglob('*')) if p.is_file()}
plan={'status':'STATIC_READY_NOT_LAUNCHED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':'019 exact physics modules; display-only pause/recording controls adapted','max_frames':120,'frames_per_click':12,'batch_wall_cap_seconds':15,'owner_files_before':owner,'inputs':originals,'assets':{f.name:row(f) for f in sorted(A.iterdir()) if f.is_file()},'no_owner_or_canonical_writes':True,'recording_disabled':True,'server_not_started':True,'browser_not_opened':True,'limits':'Early-state/contact inspection only. No 480-frame settled state, long019 trajectory, complete physics, appearance or installation approval.'}
for p in A.glob('*.mjs'):subprocess.run(['C:/Program Files/nodejs/node.exe','--check',str(p)],check=True,capture_output=True)
(D/'PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'directory':str(D),'plan_sha256':sha(D/'PLAN.json'),'owner_files':len(owner),'assets':len(plan['assets'])}))
