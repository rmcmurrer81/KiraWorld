import * as THREE from './vendor/three/build/three.module.js';
import {loadPackage} from './package_loader.mjs';
import {AVATAR} from './runtime.mjs';
const stage=document.getElementById('stage'),status=document.getElementById('status'),picker=document.getElementById('files'),enter=document.getElementById('enter'),pause=document.getElementById('pause');
let renderer=null,camera=null,current=null,active=false,dragging=false,last=0,frame=0,note='',loading=false;
const keys=new Set();
function stop(){active=false;dragging=false;keys.clear();cancelAnimationFrame(frame);enter.textContent='Resume walking';pause.disabled=true;draw();}
function dispose(root){const geometries=new Set(),materials=new Set(),textures=new Set();root.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[]){materials.add(m);for(const v of Object.values(m))if(v?.isTexture)textures.add(v);}});geometries.forEach(g=>g.dispose());textures.forEach(t=>t.dispose());materials.forEach(m=>m.dispose());}
function draw(){if(!current||!renderer)return;const s=current.runtime.snapshot();current.applyDoorStates(current.runtime.doorStates());camera.position.set(s.feet[0],s.feet[1]+AVATAR.eye,s.feet[2]);camera.rotation.set(s.pitch,-s.yaw,0,'YXZ');renderer.render(current.scene,camera);status.textContent=`${s.roomName} · ${active?'walking':'paused'}${s.nearbyDoor?' · E: '+s.nearbyDoor.state+' door':''}\n${note||s.blocked||'Experimental package consumer — visual/input review pending.'}`;}
function tick(now){if(!active)return;const dt=Math.min((now-last)/1000,.05);last=now;current.runtime.step(dt,{forward:keys.has('KeyW'),backward:keys.has('KeyS'),left:keys.has('KeyA'),right:keys.has('KeyD'),turnLeft:keys.has('ArrowLeft'),turnRight:keys.has('ArrowRight')});draw();frame=requestAnimationFrame(tick);}
enter.addEventListener('click',()=>{if(!current||active)return;active=true;note='';enter.blur();last=performance.now();pause.disabled=false;frame=requestAnimationFrame(tick);});
pause.addEventListener('click',stop);
picker.addEventListener('change',async()=>{if(loading)return;loading=true;stop();enter.disabled=true;status.textContent='Verifying and importing the selected package…';
 try{const files=new Map();for(const file of picker.files){if(files.has(file.name))throw Error('Duplicate selected file: '+file.name);files.set(file.name,new Uint8Array(await file.arrayBuffer()));}
  const next=await loadPackage(files);if(current)dispose(current.scene);current=next;
  if(!renderer){renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;stage.append(renderer.domElement);camera=new THREE.PerspectiveCamera(64,1,.06,100);}
  current.scene.background=new THREE.Color(0x151c26);current.scene.add(new THREE.HemisphereLight(0xbcd3e5,0x2b211e,.35));
  note='Loaded real exported meshes. Lighting adds a disclosed hemisphere fill; source previews are unchanged.';enter.disabled=false;enter.textContent='Start walking';resize();
 }catch(e){if(current){dispose(current.scene);current=null;}if(renderer)renderer.clear();status.textContent='Package held: '+e.message;}finally{loading=false;}
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
window.addEventListener('pagehide',()=>{stop();if(current)dispose(current.scene);renderer?.dispose();});
