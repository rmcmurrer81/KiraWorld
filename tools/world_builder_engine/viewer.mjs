import * as THREE from './three.module.js';
import {AVATAR,createWalkController} from './walk_controller.mjs';

async function start(){
  const response=await fetch('/geometry.json',{cache:'no-store'});
  if(!response.ok) throw new Error('The pinned layout could not be loaded.');
  const geometry=await response.json(), controller=createWalkController(geometry);
  document.querySelector('#title').textContent=geometry.title;
  const scene=new THREE.Scene();scene.background=new THREE.Color('#819698');
  const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  document.querySelector('#viewport').appendChild(renderer.domElement);
  const camera=new THREE.PerspectiveCamera(68,innerWidth/innerHeight,.045,250);
  camera.rotation.order='YXZ';
  scene.add(new THREE.HemisphereLight(0xedf5f2,0x8f8173,2.8));
  const fill=new THREE.DirectionalLight(0xfff0d0,1.2);fill.position.set(6,12,3);scene.add(fill);
  const colors={wall:0xe5ded1,ceiling:0xf0eee4,floor:0x7b9397,unknown_locked_boundary:0x5c6470};
  const materials=new Map();
  for(const primitive of geometry.primitives){
    const role=primitive.role;
    if(!materials.has(role)) materials.set(role,new THREE.MeshStandardMaterial({color:colors[role]||0xa3afb4,roughness:.93,metalness:0}));
    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...primitive.size),materials.get(role));
    mesh.position.set(...primitive.position);scene.add(mesh);
    if(role==='floor'){
      const grid=new THREE.GridHelper(Math.max(primitive.size[0],primitive.size[2]),Math.max(1,Math.round(Math.max(primitive.size[0],primitive.size[2]))),0x516a71,0x6b8387);
      // A room-sized plane avoids drawing grid beyond rectangular floor boundaries.
      grid.scale.set(primitive.size[0]/Math.max(primitive.size[0],primitive.size[2]),1,primitive.size[2]/Math.max(primitive.size[0],primitive.size[2]));
      grid.position.set(primitive.position[0],primitive.position[1]+primitive.size[1]/2+.003,primitive.position[2]);scene.add(grid);
    }
  }
  for(const room of geometry.rooms){
    if(room.access!=='walkable_layout') continue;
    const canvas=document.createElement('canvas');canvas.width=768;canvas.height=128;
    const context=canvas.getContext('2d');context.fillStyle='#1b3540';context.fillRect(0,0,768,128);
    context.fillStyle='#edecdf';context.textAlign='center';context.textBaseline='middle';
    context.font='500 42px Segoe UI, sans-serif';context.fillText(room.name,384,64,710);
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const sign=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:true}));
    sign.position.set(room.x+room.width/2,room.floor_y+Math.min(room.height-.35,2.35),room.z+room.depth/2);
    sign.scale.set(Math.min(2.8,room.width*.7),.46,1);scene.add(sign);
  }
  const keys=new Set();
  const supported=new Set(['KeyW','KeyA','KeyS','KeyD','ArrowLeft','ArrowRight','KeyQ','KeyE']);
  addEventListener('keydown',e=>{if(supported.has(e.code)&&!['INPUT','TEXTAREA','BUTTON'].includes(document.activeElement.tagName)){keys.add(e.code);e.preventDefault();}});
  addEventListener('keyup',e=>keys.delete(e.code));
  addEventListener('blur',()=>keys.clear());
  document.addEventListener('visibilitychange',()=>keys.clear());
  let stepAction=null,stepRemaining=0;
  for(const button of document.querySelectorAll('[data-walk]')){
    button.addEventListener('click',()=>{stepAction=button.dataset.walk;stepRemaining=.25;button.blur();});
  }
  const look=document.querySelector('#look');
  look.addEventListener('click',async()=>{try{await renderer.domElement.requestPointerLock();look.blur();}catch{look.textContent='Use keyboard turning';look.blur();}});
  document.addEventListener('pointerlockchange',()=>{look.textContent=document.pointerLockElement===renderer.domElement?'Mouse active · Esc to release':'Enable mouse look';});
  document.addEventListener('mousemove',e=>{if(document.pointerLockElement===renderer.domElement)controller.look(e.movementX,e.movementY);});
  addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
  const roomLabel=document.querySelector('#room'),movement=document.querySelector('#movement'),distance=document.querySelector('#distance');
  // The first animation timestamp can precede the setup's performance.now().
  // Start at zero elapsed time so the first rendered frame cannot reject it.
  let previous=null,lastStatus='';
  function frame(now){
    const input={forward:keys.has('KeyW'),backward:keys.has('KeyS'),left:keys.has('KeyA'),right:keys.has('KeyD'),turnLeft:keys.has('ArrowLeft')||keys.has('KeyQ'),turnRight:keys.has('ArrowRight')||keys.has('KeyE')};
    const elapsed=previous===null?0:Math.min(.05,Math.max(0,(now-previous)/1000));previous=now;
    if(stepRemaining>0){input[stepAction]=true;stepRemaining-=elapsed;}
    const state=controller.step(elapsed,input);
    camera.position.set(state.feet[0],state.feet[1]+AVATAR.eye,state.feet[2]);camera.rotation.set(state.pitch,-state.yaw,0);
    const status=state.roomName+'|'+state.blocked;
    if(status!==lastStatus){roomLabel.textContent=state.roomName;movement.textContent=state.blocked==='solid_obstruction'?'Wall or low ceiling — turn toward a passage':state.blocked?'No supported floor in that direction':'Walking inside the layout · unfinished materials';lastStatus=status;}
    distance.textContent='Distance walked: '+state.distance.toFixed(1)+' m';
    renderer.render(scene,camera);requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
start().catch(error=>{document.querySelector('#error').hidden=false;document.querySelector('#error').textContent='Preview could not start.\n'+error.message;document.querySelector('#movement').textContent='Preview unavailable';});
