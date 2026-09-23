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
  const doorMeshes=new Map();
  const frameMaterial=new THREE.MeshStandardMaterial({color:0x344955,roughness:.48,metalness:.65});
  const leafMaterial=new THREE.MeshStandardMaterial({color:0xa9babc,roughness:.45,metalness:.52});
  const panelMaterial=new THREE.MeshStandardMaterial({color:0x4f7585,roughness:.51,metalness:.37});
  const handleMaterial=new THREE.MeshStandardMaterial({color:0xe1d9ae,roughness:.3,metalness:.75});
  const initialDoors=new Map(controller.doorStates().map(d=>[d.id,d]));
  for(const assembly of controller.doorAssemblies()){
    for(const frame of assembly.frames){
      const mesh=new THREE.Mesh(new THREE.BoxGeometry(...frame.size),frameMaterial);
      mesh.position.set(...frame.center);scene.add(mesh);
    }
    const initial=initialDoors.get(assembly.id),group=new THREE.Group();
    const leaf=new THREE.Mesh(new THREE.BoxGeometry(...initial.size),leafMaterial);group.add(leaf);
    const normal=assembly.axis==='x'?0:2,along=normal===0?2:0;
    for(const side of [-1,1]){
      const size=[...initial.size];size[normal]=.008;size[along]*=.77;size[1]*=.68;
      const panel=new THREE.Mesh(new THREE.BoxGeometry(...size),panelMaterial);
      panel.position.setComponent(normal,side*(initial.size[normal]/2+.005));group.add(panel);
      const handle=new THREE.Mesh(new THREE.CylinderGeometry(.023,.023,.27,10),handleMaterial);
      handle.position.setComponent(normal,side*(initial.size[normal]/2+.055));
      handle.position.setComponent(along,initial.size[along]*.34);handle.position.y=-.12;group.add(handle);
      // Mounts visibly connect the handles to both sides of the leaf.
      for(const y of [-.23,-.01]){
        const mountingSize=[.075,.025,.075];mountingSize[normal]=.065;
        const mount=new THREE.Mesh(new THREE.BoxGeometry(...mountingSize),handleMaterial);
        mount.position.copy(handle.position);mount.position.y=y;mount.position.setComponent(normal,side*(initial.size[normal]/2+.031));group.add(mount);
      }
    }
    const head=assembly.frames.find(f=>f.id.endsWith('_head'));
    const indicatorSize=assembly.axis==='x'?[.225,.033,.22]:[.22,.033,.225];
    const indicatorMaterial=new THREE.MeshStandardMaterial({color:0xd28360,emissive:0x3f1205,roughness:.5});
    const indicator=new THREE.Mesh(new THREE.BoxGeometry(...indicatorSize),indicatorMaterial);
    indicator.position.set(...head.center);scene.add(indicator);scene.add(group);
    doorMeshes.set(assembly.id,{group,indicatorMaterial});
  }
  const keys=new Set();
  const supported=new Set(['KeyW','KeyA','KeyS','KeyD','ArrowLeft','ArrowRight','KeyQ','KeyE']);
  addEventListener('keydown',e=>{if(supported.has(e.code)&&!['INPUT','TEXTAREA','BUTTON'].includes(document.activeElement.tagName)){keys.add(e.code);e.preventDefault();}});
  addEventListener('keyup',e=>keys.delete(e.code));
  const doorButton=document.querySelector('#door-toggle'),doorMessage=document.querySelector('#door-message');
  let doorNotice='',doorNoticeUntil=0;
  function interactDoor(){
    const result=controller.toggleDoor();
    doorNotice=result.ok?(result.state==='opening'?'Opening door…':'Closing door…'):result.reason;
    doorNoticeUntil=performance.now()+3500;doorButton.blur();
  }
  doorButton.addEventListener('click',interactDoor);
  addEventListener('keydown',e=>{if(e.code==='KeyF'&&!e.repeat&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){interactDoor();e.preventDefault();}});
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
    for(const door of controller.doorStates()){
      const visual=doorMeshes.get(door.id);visual.group.position.set(...door.center);visual.group.rotation.y=door.angle;
      visual.indicatorMaterial.color.setHex(door.state==='open'?0x72b494:door.state==='closed'?0xd28360:0xe9c66d);
      visual.indicatorMaterial.emissive.setHex(door.state==='open'?0x123621:door.state==='closed'?0x3f1205:0x48330c);
    }
    const nearby=state.nearbyDoor,moving=nearby&&(nearby.state==='opening'||nearby.state==='closing');
    doorButton.disabled=!nearby||moving;
    doorButton.textContent=!nearby?'Approach a door · F':moving?'Door moving…':nearby.state==='closed'?'Open door · F':'Close door · F';
    doorMessage.textContent=nearby?.motionHeld?'Door paused — step away from its swing.':
      now<doorNoticeUntil?doorNotice:nearby?'Door '+nearby.state+'. Leave room for it to swing.':'Framed doors open and close. Press F when nearby.';
    camera.position.set(state.feet[0],state.feet[1]+AVATAR.eye,state.feet[2]);camera.rotation.set(state.pitch,-state.yaw,0);
    const status=state.roomName+'|'+state.blocked;
    if(status!==lastStatus){roomLabel.textContent=state.roomName;movement.textContent=state.blocked==='door_obstruction'?'Door or frame blocks the way — open it with F':state.blocked==='furniture_obstruction'?'Furniture blocks the way — walk around it':state.blocked==='solid_obstruction'?'Wall or low ceiling — turn toward a passage':state.blocked?'No supported floor in that direction':'Walking inside the layout · unfinished materials';lastStatus=status;}
    distance.textContent='Distance walked: '+state.distance.toFixed(1)+' m';
    renderer.render(scene,camera);requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
start().catch(error=>{document.querySelector('#error').hidden=false;document.querySelector('#error').textContent='Preview could not start.\n'+error.message;document.querySelector('#movement').textContent='Preview unavailable';});
