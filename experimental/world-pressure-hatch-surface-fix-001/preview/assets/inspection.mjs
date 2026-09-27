import {buildInspectionContext} from './inspection_context.mjs';
import * as THREE from './three.module.js';
import {pressureHatchIds,planPressureHatch,buildPressureHatch,hatchCollidersAt} from './pressure_hatch.mjs';

let renderer=null,scene=null,camera=null,hatch=null,plan=null,frame=null,disposed=false;
let angleDegrees=0,cameraState={target:[0,1.16,0],yaw:.10,distance:4.3,elevation:.11};
let scaleGuide=null,boundsGroup=null;
const viewport=document.querySelector('#viewport'),status=document.querySelector('#status');
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
function fail(error){
  const box=document.querySelector('#error');box.textContent='The isolated hatch could not be displayed. '+(error?.message||'Reload this review page to retry.');box.hidden=false;
  status.textContent='Inspection failed · no owner world was modified.';
  document.querySelectorAll('fieldset').forEach(group=>group.disabled=true);
  dispose();
}
function point(local){const n=plan.axis==='x'?0:2,t=n===0?2:0,result=[...plan.origin];result[t]+=local[0];result[1]+=local[1];result[n]+=plan.normalSign*local[2];return new THREE.Vector3(...result);}
function moveCamera(){
  const {target,yaw,distance,elevation}=cameraState;
  const c=Math.cos(elevation),eye=[target[0]+Math.sin(yaw)*distance*c,target[1]+Math.sin(elevation)*distance,target[2]+Math.cos(yaw)*distance*c];
  camera.position.copy(point(eye));camera.lookAt(point(target));
}
function requestDraw(){
  if(disposed||frame!==null||document.hidden||!renderer)return;
  frame=requestAnimationFrame(()=>{frame=null;if(!disposed&&!document.hidden){moveCamera();renderer.render(scene,camera);}});
}
function refreshStatus(){
  status.textContent=`${angleDegrees===0?'Closed leaf':angleDegrees+'° open leaf'} · static retracted latch hardware · no pressure simulation · isolated geometry only`;
}
function updateBounds(){
  if(!boundsGroup)return;
  for(const helper of [...boundsGroup.children]){helper.geometry.dispose();helper.material.dispose();boundsGroup.remove(helper);}
  if(!document.querySelector('#colliders').checked)return;
  for(const bound of hatchCollidersAt(plan,plan.openAngle*angleDegrees/90)){
    const box=new THREE.Box3(new THREE.Vector3(...bound.min),new THREE.Vector3(...bound.max));
    const helper=new THREE.Box3Helper(box,bound.motion==='kinematic'?0xe7bb65:0x72c9cb);helper.material.depthTest=false;helper.material.transparent=true;helper.material.opacity=.55;helper.renderOrder=10;boundsGroup.add(helper);
  }
}
function setPose(degrees){
  angleDegrees=degrees;hatch.setAngle(plan.openAngle*degrees/90);updateBounds();
  document.querySelectorAll('[data-pose]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.pose)===degrees)));
  refreshStatus();requestDraw();
}
function setView(name){
  const views={front:{target:[0,1.16,.06],yaw:.08,distance:4.2,elevation:.10},back:{target:[0,1.16,0],yaw:Math.PI+.08,distance:4.2,elevation:.10},
    hinge:{target:[-plan.aperture.width/2-.045,1.1,.12],yaw:-.8,distance:1.8,elevation:.22},
    seal:{target:[plan.aperture.width/2+.04,1.12,.08],yaw:.9,distance:1.7,elevation:.20},
    wide:{target:[0,1.17,0],yaw:.5,distance:5.4,elevation:.13}};
  cameraState=structuredClone(views[name]??views.front);requestDraw();
}
function dispose(){
  if(disposed)return;disposed=true;if(frame!==null)cancelAnimationFrame(frame);
  const geometries=new Set(),materials=new Set();scene?.traverse(object=>{if(object.geometry)geometries.add(object.geometry);if(object.material)(Array.isArray(object.material)?object.material:[object.material]).forEach(m=>materials.add(m));});
  geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer?.dispose();
}
async function main(){
  const response=await fetch('/geometry.json',{cache:'no-store'});if(!response.ok)throw new Error('Pinned geometry could not be loaded.');
  const geometry=await response.json(),ids=pressureHatchIds(geometry);if(ids.length!==2)throw new Error('The review fixture must contain one two-door airlock.');
  plan=planPressureHatch(geometry,ids[0]);hatch=buildPressureHatch(THREE,plan);
  scene=new THREE.Scene();scene.background=new THREE.Color('#526068');
  camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.03,40);
  renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;viewport.appendChild(renderer.domElement);
  renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();fail(new Error('The graphics context was interrupted. Reload when resources are available.'));});
  scene.add(new THREE.HemisphereLight(0xe6eff2,0x515250,1.2));
  const key=new THREE.DirectionalLight(0xfff2dd,2);key.position.copy(point([-3,5,5]));key.target.position.copy(point([0,1,0]));key.castShadow=true;
  key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-4,right:4,top:4,bottom:-4,near:.1,far:20});key.shadow.bias=-.0003;scene.add(key,key.target);
  const fill=new THREE.DirectionalLight(0xd8e8ff,1);fill.position.copy(point([3,3,-4]));fill.target.position.copy(point([0,1,0]));scene.add(fill,fill.target);
  scene.add(hatch.fixed,hatch.pivot);
  const wallMaterial=new THREE.MeshStandardMaterial({color:0xa4aaa5,roughness:.87,metalness:.08});
  const floorMaterial=new THREE.MeshStandardMaterial({color:0x515b60,roughness:.92,metalness:.03});
  const w=plan.aperture.width;
  scene.add(buildInspectionContext(THREE,plan,wallMaterial,floorMaterial));
  scaleGuide=new THREE.Mesh(new THREE.BoxGeometry(.68,1.68,.68),new THREE.MeshBasicMaterial({color:0x97d8cb,wireframe:true}));
  scaleGuide.name='optional_1_68m_scale_guide';scaleGuide.position.copy(point([w/2+.80,.84,.7]));scaleGuide.visible=false;scene.add(scaleGuide);
  boundsGroup=new THREE.Group();scene.add(boundsGroup);
  document.querySelector('#details').textContent=`One synthetic test hatch · ${plan.aperture.width.toFixed(2)} m opening · ${plan.leafWidth.toFixed(2)} × ${plan.leafHeight.toFixed(2)} m leaf · ${hatch.meshes.size} authored parts. The saved Mars world is not loaded or changed.`;
  document.querySelectorAll('fieldset').forEach(group=>group.disabled=false);
  document.querySelectorAll('[data-pose]').forEach(button=>button.addEventListener('click',()=>setPose(Number(button.dataset.pose))));
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
  document.querySelector('#reset-view').addEventListener('click',()=>setView('front'));
  document.querySelectorAll('[data-camera]').forEach(button=>button.addEventListener('click',()=>{
    const action=button.dataset.camera;if(action==='left')cameraState.yaw-=Math.PI/12;if(action==='right')cameraState.yaw+=Math.PI/12;
    if(action==='closer')cameraState.distance=clamp(cameraState.distance-.3,.7,8);if(action==='farther')cameraState.distance=clamp(cameraState.distance+.3,.7,8);
    if(action==='up')cameraState.elevation=clamp(cameraState.elevation+.08,-.2,.65);if(action==='down')cameraState.elevation=clamp(cameraState.elevation-.08,-.2,.65);requestDraw();
  }));
  document.querySelector('#scale').addEventListener('change',event=>{scaleGuide.visible=event.target.checked;requestDraw();});
  document.querySelector('#colliders').addEventListener('change',()=>{updateBounds();requestDraw();});
  document.querySelector('#hide-controls').addEventListener('click',()=>{document.querySelector('#controls').hidden=true;document.querySelector('#show-controls').hidden=false;});
  document.querySelector('#show-controls').addEventListener('click',()=>{document.querySelector('#controls').hidden=false;document.querySelector('#show-controls').hidden=true;});
  addEventListener('resize',()=>{if(disposed)return;camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);requestDraw();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&frame!==null){cancelAnimationFrame(frame);frame=null;}else requestDraw();});
  addEventListener('pagehide',dispose,{once:true});
  setView('front');setPose(0);
}
main().catch(fail);
