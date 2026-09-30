import * as THREE from './vendor/three/build/three.module.js';
import {loadPackage} from './package_loader.mjs';
import {readSelectedPackage} from './file_admission.mjs';
import {AVATAR} from './runtime.mjs';
import {disposeScene} from './scene_disposal.mjs';
import {createHistoryHost,isInteractiveTarget} from './history_host.mjs';
import {discreteAction,createDoorMotionSequence,describeNearbyDoor} from './discrete_controls.mjs';
import {createAirlockHost} from './airlock_host.mjs';
import {createLatchHost} from './latch_host.mjs';
const stage=document.getElementById('stage'),status=document.getElementById('status'),picker=document.getElementById('files'),enter=document.getElementById('enter'),pause=document.getElementById('pause');
let renderer=null,camera=null,current=null,active=false,dragging=false,pointerId=null,last=null,walkingRevision=0,frame=0,note='',loading=false,closed=false,generation=0;
let airlock=null,latches=null;
const latchPanel=document.getElementById('latch-panel'),latchReadout=document.getElementById('latch-readout'),latchEngage=document.getElementById('latch-engage'),latchRelease=document.getElementById('latch-release');
function disposeLoaded(value){value?.dispose?.();if(value)disposeScene(value.scene);}
const airlockPanel=document.getElementById('airlock-panel'),airlockReadout=document.getElementById('airlock-readout');
const cycleButtons=new Map(['seal-inside','seal-outside','begin-inside','begin-outside','resume','cancel'].map(a=>[a,document.getElementById('airlock-'+a)]));
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
function updateLatch(){const s=latches?.update();if(latchPanel)latchPanel.hidden=!s?.doorId||closed||loading;if(!s?.doorId)return;const state=s.states.find(v=>v.id===s.doorId);latchReadout.textContent=state?'Visual hardware: '+state.state+' · '+Math.round(state.fraction*100)+'%'+(state.paused?' · paused':''):'Latch observation unavailable';latchEngage.disabled=!state||!!state.fault;latchRelease.disabled=!state||!!state.fault;}
for(const [button,engage]of [[latchEngage,true],[latchRelease,false]])button?.addEventListener('click',()=>{if(closed||loading||!latches)return;stop('interaction');history.close();const id=latches.update()?.doorId;if(!id)return;const r=latches.command(id,engage);note=r.ok?'Visual latch '+(engage?'engaging':'releasing')+'. Geometric closure and simulated seal remain separate.':r.reason;if(r.ok)doorMotion.start(current.runtime);draw();});
function updateAirlock(){
 if(!airlockPanel)return;const show=!closed&&!loading&&airlock&&airlock.inRange();airlockPanel.hidden=!show;
 if(!airlock)return;const s=airlock.update();if(!show)return;
 const lines=['Fictional paired-side simulation · six seconds of active time.'];
 for(const side of ['inside','outside']){const d=s.doors?.[side],geometry=!s.observationValid?'unavailable (last observation retained)':d?.moving?'moving':d?.angle===0?'closed':'open';lines.push(`${s.labels[side]}: door ${geometry} · simulated seal ${s.simulatedSealAcknowledged[side]?'acknowledged':'not acknowledged'}`);}
 const side=s.simulatedPressure==='habitat'?'inside':s.simulatedPressure==='mars'?'outside':null;
 lines.push(`Symbolic pressure side: ${side?s.labels[side]:'unknown'} · ${s.phase}${s.target?' · '+s.elapsedSeconds.toFixed(1)+' / '+s.authoredCycleSeconds+' s':''}`);
 if(s.reason)lines.push(s.reason);if(s.pauseReasons.length&&s.phase==='paused')lines.push('Paused: '+s.pauseReasons.join(', '));
 airlockReadout.textContent=lines.join('\n');
 for(const side of ['inside','outside']){const seal=cycleButtons.get('seal-'+side),begin=cycleButtons.get('begin-'+side);seal.textContent='Acknowledge simulated seal · '+s.labels[side];begin.textContent='Cycle toward '+s.labels[side];seal.disabled=['cycling','paused'].includes(s.phase)||!s.observationValid;begin.disabled=['cycling','paused'].includes(s.phase);}
 cycleButtons.get('resume').disabled=s.phase!=='paused';cycleButtons.get('cancel').disabled=!['cycling','paused'].includes(s.phase);
}
for(const [action,button]of cycleButtons)button?.addEventListener('click',()=>{
 if(closed||loading||!airlock||!airlock.inRange())return;
 stop('interaction');history.close();document.activeElement?.blur();
 try{const result=action.startsWith('seal-')?airlock.acknowledge(action.slice(5)):action.startsWith('begin-')?airlock.begin(action.slice(6)):airlock[action]();note=result.ok?'Fictional airlock simulation updated. Walking stays paused.':result.reason;}catch(e){note=e.message;}draw();
});
function commandDoor(id){if(latches?.hasDoor(id)){const ready=latches.ready();if(!ready.ok)return ready;}return airlock?.hasDoor(id)?airlock.command(id):current.runtime.toggleDoor(id);}
function updateStepControls(){
 const ready=!closed&&!loading&&!!current;for(const b of actionButtons.values())if(b)b.disabled=!ready;
 if(stepPanel)stepPanel.hidden=!ready;
 const s=ready?current.runtime.snapshot():null,room=s?'Current room: '+s.roomName:'Select a package to explore.';
 if(roomLabel&&roomLabel.textContent!==room)roomLabel.textContent=room;
 if(doorButton){doorButton.disabled=!ready||!s.nearbyDoor;doorButton.textContent=describeNearbyDoor(current?.metadata,s)?.button||'No door within reach';}
 pause.disabled=!active&&!doorMotion.isRunning()&&!airlock?.isRunning();
}
function stop(reason='manual'){active=false;walkingRevision++;last=null;dragging=false;keys.clear();doorMotion.cancel();airlock?.pause(typeof reason==='string'?reason:'manual');latches?.pause(typeof reason==='string'?reason:'manual');if(pointerId!==null){try{stage.releasePointerCapture(pointerId);}catch{}pointerId=null;}cancelAnimationFrame(frame);enter.textContent='Resume walking';pause.disabled=true;draw();}
function draw(){history.update();updateAirlock();updateLatch();updateStepControls();if(closed||!current||!renderer)return;const s=current.runtime.snapshot(),doorLabel=describeNearbyDoor(current.metadata,s);current.applyDoorStates(current.runtime.doorStates(),current.runtime.latchStates?.()??[]);updateCrop(s.roomId);camera.position.set(s.feet[0],s.feet[1]+AVATAR.eye,s.feet[2]);camera.rotation.set(s.pitch,-s.yaw,0,'YXZ');renderer.render(current.scene,camera);status.textContent=`${s.roomName} · ${active?'walking':'paused'}${doorLabel?' · '+doorLabel.target+': '+doorLabel.state:''}\n${note||s.blocked||'Experimental package consumer — visual/input review pending.'}`;}
for(const [action,button]of actionButtons)button?.addEventListener('click',()=>{
 if(closed||loading||!current)return;stop();history.close();
 try{const result=discreteAction(current.runtime,action);note=result.after.blocked&&['forward','backward','left','right'].includes(action)?'Step blocked: '+result.after.blocked:'One '+button.textContent.toLowerCase()+'. Walking is paused.';}catch(e){note=e.message;}draw();
});
doorButton?.addEventListener('click',()=>{
 if(closed||loading||!current)return;stop();history.close();
 const runtime=current.runtime,near=runtime.snapshot().nearbyDoor;if(!near){note='Move closer to a door.';draw();return;}
 const target=describeNearbyDoor(current.metadata,runtime.snapshot()).target;
 const result=airlock?.hasDoor(near.id)?commandDoor(near.id):near.moving?{ok:true,state:near.state}:commandDoor(near.id);
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
enter.addEventListener('click',()=>{if(closed||loading||!current||active)return;latches?.clear('manual');latches?.clear('interaction');latches?.clear('focus');airlock?.pause('interaction');doorMotion.cancel();history.close();active=true;note='';document.activeElement?.blur();last=null;const revision=++walkingRevision;pause.disabled=false;frame=requestAnimationFrame(time=>tick(time,revision));});
pause.addEventListener('click',stop);
picker.addEventListener('change',async()=>{if(loading||closed)return;const requested=++generation;loading=true;airlock?.dispose();airlock=null;latches?.dispose();latches=null;current?.runtime.pauseLatches?.('replacement');history.reset();picker.disabled=true;if(cropPanel)cropPanel.hidden=true;stop();enter.disabled=true;status.textContent='Verifying and importing the selected package…';
 try{const files=await readSelectedPackage(picker.files);
  if(closed||requested!==generation)return;
  const next=await loadPackage(files,{isCurrent:()=>!closed&&requested===generation});if(closed||requested!==generation){disposeLoaded(next);return;}disposeLoaded(current);current=next;airlock=createAirlockHost(next,{requestFrame:requestAnimationFrame,cancelFrame:cancelAnimationFrame,onChange:draw,getCurrent:()=>current});latches=createLatchHost(next,{getCurrent:()=>current,getCycle:()=>airlock?.snapshot()??null});
  if(!renderer){renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;stage.append(renderer.domElement);camera=new THREE.PerspectiveCamera(64,1,.06,250);}
  current.scene.background=new THREE.Color(0x151c26);current.scene.add(new THREE.HemisphereLight(0xbcd3e5,0x2b211e,.35));
  note='Loaded real exported meshes. Lighting adds a disclosed hemisphere fill; source previews are unchanged.';enter.disabled=false;enter.textContent='Start walking';resize();
 }catch(e){if(closed||requested!==generation)return;airlock?.dispose();airlock=null;latches?.dispose();latches=null;if(current){disposeLoaded(current);current=null;}if(renderer)renderer.clear();if(cropPanel)cropPanel.hidden=true;status.textContent='Package held: '+e.message;}finally{if(requested===generation){loading=false;if(!closed)picker.disabled=false;draw();}}
});
function resize(){if(!renderer)return;const r=stage.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();draw();}
window.addEventListener('resize',resize);
document.addEventListener('focusin',e=>{if(panelFocus(e.target))stop('focus');});
window.addEventListener('blur',()=>{stop('blur');history.pause('window-blur');});window.addEventListener('focus',()=>{airlock?.clear('blur');latches?.clear('blur');draw();});document.addEventListener('visibilitychange',()=>{if(document.hidden){stop('hidden');history.pause('hidden');}else{airlock?.clear('hidden');latches?.clear('hidden');draw();}});
window.addEventListener('keydown',e=>{if(e.code==='Escape'){stop();history.close();return;}if(!active)return;if(panelFocus(e.target)||panelFocus(document.activeElement)){stop();return;}
 if(['KeyW','KeyA','KeyS','KeyD','ArrowLeft','ArrowRight','KeyE'].includes(e.code))e.preventDefault();keys.add(e.code);
 if(e.code==='KeyE'&&!e.repeat){const near=current.runtime.snapshot().nearbyDoor,target=describeNearbyDoor(current.metadata,current.runtime.snapshot())?.target||'Nearby door';const result=commandDoor(near?.id);note=result.ok?target+' '+result.state+'.':target+': '+result.reason;draw();}
});window.addEventListener('keyup',e=>keys.delete(e.code));
stage.addEventListener('pointerdown',e=>{if(active&&!panelFocus(e.target)){dragging=true;pointerId=e.pointerId;stage.setPointerCapture(pointerId);document.activeElement?.blur();}});
function releaseDrag(){dragging=false;if(pointerId!==null){try{stage.releasePointerCapture(pointerId);}catch{}pointerId=null;}}
stage.addEventListener('pointerup',releaseDrag);stage.addEventListener('pointercancel',releaseDrag);stage.addEventListener('lostpointercapture',()=>{dragging=false;pointerId=null;});
stage.addEventListener('pointermove',e=>{if(active&&dragging)current.runtime.look(e.movementX,e.movementY);});
window.addEventListener('pagehide',()=>{generation++;closed=true;loading=false;airlock?.dispose();airlock=null;history.reset();if(cropPanel)cropPanel.hidden=true;stop();latches?.dispose();latches=null;if(current){disposeLoaded(current);current=null;}renderer?.dispose();renderer?.domElement.remove?.();renderer=null;camera=null;enter.disabled=true;picker.disabled=true;picker.value='';});
window.addEventListener('pageshow',event=>{if(!event.persisted)return;closed=false;note='';picker.disabled=false;enter.disabled=true;enter.textContent='Start walking';status.textContent='Session reset after returning to this page. Select the exported package files again.';});
