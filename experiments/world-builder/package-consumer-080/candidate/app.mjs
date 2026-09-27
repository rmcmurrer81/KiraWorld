import * as THREE from './vendor/three/build/three.module.js';
import {loadPackage} from './package_loader.mjs';
import {readSelectedPackage} from './file_admission.mjs';
import {AVATAR} from './runtime.mjs';
import {disposeScene} from './scene_disposal.mjs';
import {createHistoryHost,isInteractiveTarget} from './history_host.mjs';
import {discreteAction,createDoorMotionSequence,describeNearbyDoor} from './discrete_controls.mjs';
const stage=document.getElementById('stage'),status=document.getElementById('status'),picker=document.getElementById('files'),enter=document.getElementById('enter'),pause=document.getElementById('pause');
let renderer=null,camera=null,current=null,active=false,dragging=false,pointerId=null,last=null,walkingRevision=0,frame=0,note='',loading=false,closed=false,generation=0;
const keys=new Set();
const stepPanel=document.getElementById('step-controls'),roomLabel=document.getElementById('current-room'),doorButton=document.getElementById('nearby-door');
const actionButtons=new Map(['forward','backward','left','right','turnLeft','turnRight','lookUp','lookDown'].map(action=>[action,document.getElementById('step-'+action)]));
const doorMotion=createDoorMotionSequence({requestFrame:requestAnimationFrame,cancelFrame:cancelAnimationFrame,now:()=>performance.now(),
 onFrame:({runtime})=>{if(!closed&&!loading&&current?.runtime===runtime)draw();},
 onDone:({runtime,reason})=>{if(closed||loading||current?.runtime!==runtime)return;note=reason==='settled'?'Door motion finished. Walking is paused.':reason==='occupied'?'Door motion held: step out of its swing, then continue.':'Door motion paused. Use Continue door motion to try again.';draw();}});
const cropPanel=document.getElementById('crop-panel'),shade=document.getElementById('shade'),cropReadout=document.getElementById('crop-readout');
const historyContainer=document.getElementById('history-container');
const history=createHistoryHost({entry:document.getElementById('history-entry'),container:historyContainer,message:document.getElementById('history-message'),
 getContext:()=>({current,loading,closed}),stopWalking:stop,
 loadManifest:async()=>{const response=await fetch('./history-library.json',{cache:'no-store'});if(!response.ok)throw Error('The bundled chapter file could not load.');return response.json();}});
function panelFocus(target){return cropPanel?.contains(target)||historyContainer?.contains(target)||isInteractiveTarget(target);}
function updateCrop(roomId){if(!cropPanel)return;const control=current?.greenhouse,show=!loading&&!closed&&control&&control.snapshot().roomId===roomId;cropPanel.hidden=!show;if(!show)return;
 const s=control.snapshot();shade.value=String(s.shadePercent);cropReadout.textContent=`Local louvers: ${s.shadePercent}% · illustrative canopy light: ${s.illustrativeCanopyLight} µmol m−2 s−1. Saved scenario: ${s.scenario.temperature_c} °C, ${s.scenario.relative_humidity_percent}% RH, CO₂ ${s.scenario.co2_ppm} ppm, water ${s.scenario.water_level_percent}%.\n`+s.scenario.beds.map(b=>`${b.label}: ${b.crop} — ${b.stage}`).join('\n');
}
shade?.addEventListener('input',()=>{if(loading||closed||!current?.greenhouse)return;try{current.greenhouse.setShade(Number(shade.value),current.runtime.snapshot().roomId);note='Local louver coverage changed. Mounted screens retain the saved export snapshot.';}catch(e){note=e.message;}draw();});
function updateStepControls(){
 const ready=!closed&&!loading&&!!current;for(const b of actionButtons.values())if(b)b.disabled=!ready;
 if(stepPanel)stepPanel.hidden=!ready;
 const s=ready?current.runtime.snapshot():null,room=s?'Current room: '+s.roomName:'Select a package to explore.';
 if(roomLabel&&roomLabel.textContent!==room)roomLabel.textContent=room;
 if(doorButton){doorButton.disabled=!ready||!s.nearbyDoor;doorButton.textContent=describeNearbyDoor(current?.metadata,s)?.button||'No door within reach';}
 pause.disabled=!active&&!doorMotion.isRunning();
}
function stop(){active=false;walkingRevision++;last=null;dragging=false;keys.clear();doorMotion.cancel();if(pointerId!==null){try{stage.releasePointerCapture(pointerId);}catch{}pointerId=null;}cancelAnimationFrame(frame);enter.textContent='Resume walking';pause.disabled=true;draw();}
function draw(){history.update();updateStepControls();if(closed||!current||!renderer)return;const s=current.runtime.snapshot(),doorLabel=describeNearbyDoor(current.metadata,s);current.applyDoorStates(current.runtime.doorStates());updateCrop(s.roomId);camera.position.set(s.feet[0],s.feet[1]+AVATAR.eye,s.feet[2]);camera.rotation.set(s.pitch,-s.yaw,0,'YXZ');renderer.render(current.scene,camera);status.textContent=`${s.roomName} · ${active?'walking':'paused'}${doorLabel?' · '+doorLabel.target+': '+doorLabel.state:''}\n${note||s.blocked||'Experimental package consumer — visual/input review pending.'}`;}
for(const [action,button]of actionButtons)button?.addEventListener('click',()=>{
 if(closed||loading||!current)return;stop();history.close();
 try{const result=discreteAction(current.runtime,action);note=result.after.blocked&&['forward','backward','left','right'].includes(action)?'Step blocked: '+result.after.blocked:'One '+button.textContent.toLowerCase()+'. Walking is paused.';}catch(e){note=e.message;}draw();
});
doorButton?.addEventListener('click',()=>{
 if(closed||loading||!current)return;stop();history.close();
 const runtime=current.runtime,near=runtime.snapshot().nearbyDoor;if(!near){note='Move closer to a door.';draw();return;}
 const target=describeNearbyDoor(current.metadata,runtime.snapshot()).target;
 const result=near.moving?{ok:true,state:near.state}:runtime.toggleDoor(near.id);
 if(!result.ok){note=target+': '+result.reason;draw();return;}
 note=target+' '+result.state+'. Walking is paused.';doorMotion.start(runtime);draw();
});
function tick(now,revision){
 if(!active||revision!==walkingRevision||closed||loading||!current)return;
 if(panelFocus(document.activeElement)){stop();return;}
 if(typeof now!=='number'||!Number.isFinite(now)||now<0||(last!==null&&now<last)){
  note='Walking paused: the animation clock was invalid. Resume walking to continue.';stop();return;
 }
 // The first frame establishes the RAF baseline; click-time samples are not
 // interchangeable with a frame timestamp. Never feed negative elapsed time.
 const dt=last===null?0:Math.min((now-last)/1000,.05);last=now;
 current.runtime.step(dt,{forward:keys.has('KeyW'),backward:keys.has('KeyS'),left:keys.has('KeyA'),right:keys.has('KeyD'),turnLeft:keys.has('ArrowLeft'),turnRight:keys.has('ArrowRight')});draw();
 if(active&&revision===walkingRevision)frame=requestAnimationFrame(time=>tick(time,revision));
}
enter.addEventListener('click',()=>{if(closed||loading||!current||active)return;doorMotion.cancel();history.close();active=true;note='';document.activeElement?.blur();last=null;const revision=++walkingRevision;pause.disabled=false;frame=requestAnimationFrame(time=>tick(time,revision));});
pause.addEventListener('click',stop);
picker.addEventListener('change',async()=>{if(loading||closed)return;const requested=generation;loading=true;history.reset();picker.disabled=true;if(cropPanel)cropPanel.hidden=true;stop();enter.disabled=true;status.textContent='Verifying and importing the selected package…';
 try{const files=await readSelectedPackage(picker.files);
  if(closed||requested!==generation)return;
  const next=await loadPackage(files);if(closed||requested!==generation){disposeScene(next.scene);return;}if(current)disposeScene(current.scene);current=next;
  if(!renderer){renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;stage.append(renderer.domElement);camera=new THREE.PerspectiveCamera(64,1,.06,250);}
  current.scene.background=new THREE.Color(0x151c26);current.scene.add(new THREE.HemisphereLight(0xbcd3e5,0x2b211e,.35));
  note='Loaded real exported meshes. Lighting adds a disclosed hemisphere fill; source previews are unchanged.';enter.disabled=false;enter.textContent='Start walking';resize();
 }catch(e){if(closed||requested!==generation)return;if(current){disposeScene(current.scene);current=null;}if(renderer)renderer.clear();if(cropPanel)cropPanel.hidden=true;status.textContent='Package held: '+e.message;}finally{if(requested===generation){loading=false;if(!closed)picker.disabled=false;history.update();updateStepControls();}}
});
function resize(){if(!renderer)return;const r=stage.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();draw();}
window.addEventListener('resize',resize);
document.addEventListener('focusin',e=>{if(panelFocus(e.target))stop();});
window.addEventListener('blur',()=>{stop();history.pause('window-blur');});document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();history.pause('hidden');}});
window.addEventListener('keydown',e=>{if(e.code==='Escape'){stop();history.close();return;}if(!active)return;if(panelFocus(e.target)||panelFocus(document.activeElement)){stop();return;}
 if(['KeyW','KeyA','KeyS','KeyD','ArrowLeft','ArrowRight','KeyE'].includes(e.code))e.preventDefault();keys.add(e.code);
 if(e.code==='KeyE'&&!e.repeat){const near=current.runtime.snapshot().nearbyDoor,target=describeNearbyDoor(current.metadata,current.runtime.snapshot())?.target||'Nearby door';const result=current.runtime.toggleDoor(near?.id);note=result.ok?target+' '+result.state+'.':target+': '+result.reason;draw();}
});window.addEventListener('keyup',e=>keys.delete(e.code));
stage.addEventListener('pointerdown',e=>{if(active&&!panelFocus(e.target)){dragging=true;pointerId=e.pointerId;stage.setPointerCapture(pointerId);document.activeElement?.blur();}});
function releaseDrag(){dragging=false;if(pointerId!==null){try{stage.releasePointerCapture(pointerId);}catch{}pointerId=null;}}
stage.addEventListener('pointerup',releaseDrag);stage.addEventListener('pointercancel',releaseDrag);stage.addEventListener('lostpointercapture',()=>{dragging=false;pointerId=null;});
stage.addEventListener('pointermove',e=>{if(active&&dragging)current.runtime.look(e.movementX,e.movementY);});
window.addEventListener('pagehide',()=>{generation++;closed=true;loading=false;history.reset();if(cropPanel)cropPanel.hidden=true;stop();if(current){disposeScene(current.scene);current=null;}renderer?.dispose();renderer?.domElement.remove?.();renderer=null;camera=null;enter.disabled=true;picker.disabled=true;picker.value='';});
window.addEventListener('pageshow',event=>{if(!event.persisted)return;closed=false;note='';picker.disabled=false;enter.disabled=true;enter.textContent='Start walking';status.textContent='Session reset after returning to this page. Select the exported package files again.';});
