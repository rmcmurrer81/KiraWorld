import * as THREE from './vendor/three/build/three.module.js';
import {loadPackage} from './package_loader.mjs';
import {readSelectedPackage} from './file_admission.mjs';
import {AVATAR} from './runtime.mjs';
import {disposeScene} from './scene_disposal.mjs';
const stage=document.getElementById('stage'),status=document.getElementById('status'),picker=document.getElementById('files'),enter=document.getElementById('enter'),pause=document.getElementById('pause');
let renderer=null,camera=null,current=null,active=false,dragging=false,last=0,frame=0,note='',loading=false,closed=false,generation=0;
const keys=new Set();
function stop(){active=false;dragging=false;keys.clear();cancelAnimationFrame(frame);enter.textContent='Resume walking';pause.disabled=true;draw();}
function draw(){if(closed||!current||!renderer)return;const s=current.runtime.snapshot();current.applyDoorStates(current.runtime.doorStates());camera.position.set(s.feet[0],s.feet[1]+AVATAR.eye,s.feet[2]);camera.rotation.set(s.pitch,-s.yaw,0,'YXZ');renderer.render(current.scene,camera);status.textContent=`${s.roomName} · ${active?'walking':'paused'}${s.nearbyDoor?' · E: '+s.nearbyDoor.state+' door':''}\n${note||s.blocked||'Experimental package consumer — visual/input review pending.'}`;}
function tick(now){if(!active)return;const dt=Math.min((now-last)/1000,.05);last=now;current.runtime.step(dt,{forward:keys.has('KeyW'),backward:keys.has('KeyS'),left:keys.has('KeyA'),right:keys.has('KeyD'),turnLeft:keys.has('ArrowLeft'),turnRight:keys.has('ArrowRight')});draw();frame=requestAnimationFrame(tick);}
enter.addEventListener('click',()=>{if(closed||loading||!current||active)return;active=true;note='';enter.blur();last=performance.now();pause.disabled=false;frame=requestAnimationFrame(tick);});
pause.addEventListener('click',stop);
picker.addEventListener('change',async()=>{if(loading||closed)return;const requested=generation;loading=true;picker.disabled=true;stop();enter.disabled=true;status.textContent='Verifying and importing the selected package…';
 try{const files=await readSelectedPackage(picker.files);
  if(closed||requested!==generation)return;
  const next=await loadPackage(files);if(closed||requested!==generation){disposeScene(next.scene);return;}if(current)disposeScene(current.scene);current=next;
  if(!renderer){renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;stage.append(renderer.domElement);camera=new THREE.PerspectiveCamera(64,1,.06,100);}
  current.scene.background=new THREE.Color(0x151c26);current.scene.add(new THREE.HemisphereLight(0xbcd3e5,0x2b211e,.35));
  note='Loaded real exported meshes. Lighting adds a disclosed hemisphere fill; source previews are unchanged.';enter.disabled=false;enter.textContent='Start walking';resize();
 }catch(e){if(closed||requested!==generation)return;if(current){disposeScene(current.scene);current=null;}if(renderer)renderer.clear();status.textContent='Package held: '+e.message;}finally{if(requested===generation){loading=false;if(!closed)picker.disabled=false;}}
});
function resize(){if(!renderer)return;const r=stage.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();draw();}
window.addEventListener('resize',resize);
window.addEventListener('blur',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
window.addEventListener('keydown',e=>{if(e.code==='Escape'){stop();return;}if(!active||['INPUT','BUTTON'].includes(document.activeElement?.tagName))return;
 if(['KeyW','KeyA','KeyS','KeyD','ArrowLeft','ArrowRight','KeyE'].includes(e.code))e.preventDefault();keys.add(e.code);
 if(e.code==='KeyE'&&!e.repeat){const result=current.runtime.toggleDoor();note=result.ok?'Door '+result.state+'.':result.reason;draw();}
});window.addEventListener('keyup',e=>keys.delete(e.code));
stage.addEventListener('pointerdown',e=>{if(active){dragging=true;stage.setPointerCapture(e.pointerId);document.activeElement?.blur();}});
stage.addEventListener('pointerup',()=>dragging=false);stage.addEventListener('pointercancel',()=>dragging=false);
stage.addEventListener('pointermove',e=>{if(active&&dragging)current.runtime.look(e.movementX,e.movementY);});
window.addEventListener('pagehide',()=>{generation++;closed=true;loading=false;stop();if(current){disposeScene(current.scene);current=null;}renderer?.dispose();renderer?.domElement.remove?.();renderer=null;camera=null;enter.disabled=true;picker.disabled=true;picker.value='';});
window.addEventListener('pageshow',event=>{if(!event.persisted)return;closed=false;note='';picker.disabled=false;enter.disabled=true;enter.textContent='Start walking';status.textContent='Session reset after returning to this page. Select the exported package files again.';});
