import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../../package-consumer-083/candidate/vendor/three/build/three.module.js';
import {createLatchVisual,describeLatchVisual} from '../latch_visual.mjs';
import {artificialPlan as synthetic} from './artificial_plan.mjs';
const fixturePlan=synthetic('x',1),fixtureBytes=JSON.stringify(fixturePlan);
function make(plan=fixturePlan,extra={}){
 const identity={},doorId='door:'+plan.portalId;
 const state={runtimeIdentity:identity,id:doorId,angle:0,target:0,moving:false};
 const h={current:true,reads:0};
 const c=createLatchVisual({THREE,plan,doorId,runtimeIdentity:identity,readDoor:()=>{h.reads++;return state;},isCurrent:id=>h.current&&id===identity,...extra});
 return {c,state,h,identity};
}
const allMeshes=root=>{const out=[];root.traverse(o=>{if(o.isMesh)out.push(o);});return out;};
const finish=c=>{for(let i=0;i<18;i++)assert.equal(c.advance(.05).ok,true);};

test('artificial plan has three dogs, keeper alignment, and separate pressure/state semantics',()=>{
 const before=JSON.stringify(fixturePlan),r=describeLatchVisual(fixturePlan);
 assert.equal(r.mechanisms.length,3);assert.equal(r.requiresNewColliderAndMetadataReview,true);assert.equal(r.pressureProof,false);
 for(const d of r.mechanisms){
  assert.ok(d.stroke>.03&&d.stroke<.06);
  const tip=fixturePlan.hingeLocal[0]+d.engagedBounds.max[0],face=d.keeper.center[0]-d.keeper.size[0]/2;
  assert.ok(tip>face&&tip<d.keeper.center[0]+d.keeper.size[0]/2);
  assert.ok(d.proposedSupport.center[2]+d.proposedSupport.size[2]/2<=d.keeper.center[2]-d.keeper.size[2]/2+1e-12);
 }
 assert.equal(JSON.stringify(fixturePlan),before);assert.ok(Object.isFrozen(r.mechanisms[0].keeper));
 const second=describeLatchVisual(synthetic('z',-1));assert.equal(second.mechanisms.length,3);
});

test('both portal axes and normal directions preserve world placement and follow released door angle',()=>{
 for(const axis of ['x','z'])for(const sign of [-1,1]){
  const plan=synthetic(axis,sign),{c,state}=make(plan),r=c.recipe,bolt=c.root.getObjectByName(r.mechanisms[0].id+':bolt');
  c.syncDoor();const p=bolt.getWorldPosition(new THREE.Vector3()),d=r.mechanisms[0],n=axis==='x'?0:2,t=n===0?2:0;
  const expected=[...plan.hinge];expected[t]+=d.boltCenter[0];expected[1]+=d.boltCenter[1];expected[n]+=sign*d.boltCenter[2];
  assert.ok(p.distanceTo(new THREE.Vector3(...expected))<1e-9);
  state.angle=plan.openAngle;state.target=plan.openAngle;c.syncDoor();
  const local=new THREE.Vector3();local.setComponent(t,d.boltCenter[0]);local.y=d.boltCenter[1];local.setComponent(n,sign*d.boltCenter[2]);
  local.applyAxisAngle(new THREE.Vector3(0,1,0),plan.openAngle).add(new THREE.Vector3(...plan.hinge));
  assert.ok(bolt.getWorldPosition(new THREE.Vector3()).distanceTo(local)<1e-9);assert.equal(c.request(true).ok,false);c.dispose();
 }
});

test('engagement moves three bolts, both controls, and gasket front to the exact closed leaf contact plane',()=>{
 const {c}=make(),r=c.recipe,g=c.root.getObjectByName('fictional-gasket-contact');
 assert.equal(c.root.visible,false);assert.equal(c.syncDoor().ok,true);assert.equal(c.root.visible,true);
 assert.ok(g.position.z+g.scale.z<r.contact);assert.equal(c.request(true).ok,true);finish(c);
 assert.equal(c.snapshot().visualState,'engaged');assert.equal(c.snapshot().sealAcknowledgementChanged,false);
 assert.ok(Math.abs(g.position.z+g.scale.z-r.contact)<1e-10);
 for(const d of r.mechanisms){const b=c.root.getObjectByName(d.id+':bolt');assert.ok(Math.abs(b.position.x-(d.boltCenter[0]+d.stroke))<1e-10);}
 for(const w of r.wheels)assert.ok(Math.abs(c.root.getObjectByName(w.id+':rim').parent.rotation.z-Math.PI/2)<1e-10);
 c.request(false);finish(c);assert.equal(c.snapshot().visualState,'released');assert.ok(g.position.z+g.scale.z<r.contact);c.dispose();
});

test('keeper has an actual clear channel and support does not cover the engaged bolt',()=>{
 const {c}=make();
 for(const d of c.recipe.mechanisms){
  const keeper=c.root.children[0].children.filter(o=>o.name.startsWith(d.id+':keeper-'));assert.equal(keeper.length,4);
  const yc=d.dog.center[1],zc=fixturePlan.hingeLocal[2]+d.dog.center[2];
  for(const bar of keeper){bar.geometry.computeBoundingBox();const b=bar.geometry.boundingBox.clone().translate(bar.position);assert.equal(b.containsPoint(new THREE.Vector3(d.keeper.center[0],yc,zc)),false);}
 }
 c.dispose();
});

test('closed stationary observation is required; angle-zero with an opening target or moving flag is held',()=>{
 for(const mutate of [s=>s.target=fixturePlan.openAngle,s=>s.moving=true,s=>{s.angle=.1*Math.sign(fixturePlan.openAngle);s.target=fixturePlan.openAngle;}]){
  const {c,state}=make();mutate(state);assert.equal(c.request(true).ok,false);assert.equal(c.snapshot().fraction,0);c.dispose();
 }
});

test('pause reasons aggregate and no callback or wall-clock advances the pose',()=>{
 const {c}=make();c.request(true);c.advance(.05);const p=c.snapshot().fraction;
 c.pause('manual');c.pause('hidden');c.advance(.05);assert.equal(c.snapshot().fraction,p);
 c.resume('manual');c.advance(.05);assert.equal(c.snapshot().fraction,p);
 c.resume('hidden');c.advance(.05);assert.ok(c.snapshot().fraction>p);c.dispose();
});

test('moving a door during engagement faults, hides reset artwork, and never calls door or pressure actions',()=>{
 const {c,state}=make();c.request(true);c.advance(.05);state.target=fixturePlan.openAngle;state.moving=true;
 assert.equal(c.advance(.01).ok,false);assert.equal(c.root.visible,false);assert.equal(c.snapshot().visualState,'unavailable');assert.equal(c.snapshot().fraction,0);
 state.target=0;state.moving=false;assert.equal(c.request(true).ok,false);assert.equal(c.reset().ok,true);assert.equal(c.root.visible,true);assert.equal(c.request(true).ok,true);c.dispose();
});

test('wrong identity/door, invalid numeric observation, and lost current identity cannot display engaged artwork',()=>{
 for(const mutation of [(s,h)=>s.runtimeIdentity={},(s,h)=>s.id='different',(s,h)=>s.angle=NaN,(s,h)=>s.target=.2,(s,h)=>s.moving='false',(s,h)=>h.current=false]){
  const {c,state,h}=make();c.request(true);finish(c);mutation(state,h);assert.equal(c.syncDoor().ok,false);assert.equal(c.root.visible,false);assert.equal(c.snapshot().visualState,'unavailable');c.dispose();
 }
});

test('invalid time steps and nonboolean requests fail before state mutation',()=>{
 const {c}=make();c.request(true);c.advance(.05);const before=c.snapshot();
 for(const v of [-.1,.051,Infinity,NaN,'0.01'])assert.throws(()=>c.advance(v),TypeError);
 for(const v of ['true',1,null,{}])assert.throws(()=>c.request(v),TypeError);
 assert.deepEqual(c.snapshot(),before);c.dispose();
});

test('reset or disposal inside an observer invalidates the pending mutation',()=>{
 let c,once=true;const identity={},state={runtimeIdentity:identity,id:'d',angle:0,target:0,moving:false};
 c=createLatchVisual({THREE,plan:fixturePlan,doorId:'d',runtimeIdentity:identity,isCurrent:()=>true,readDoor:()=>{if(once){once=false;c.reset();}return state;}});
 assert.equal(c.request(true).ok,false);assert.equal(c.snapshot().target,0);c.dispose();
 let d;d=createLatchVisual({THREE,plan:fixturePlan,doorId:'d',runtimeIdentity:identity,isCurrent:()=>true,readDoor:()=>{d.dispose();return state;}});
 assert.equal(d.request(true).ok,false);assert.equal(d.snapshot().disposed,true);assert.equal(d.root.children.length,0);
});

test('finite unit geometry normals and disposal exactly once; caller parent and unrelated geometry survive',()=>{
 const {c,h}=make(),parent=new THREE.Group(),other=new THREE.Mesh(new THREE.BoxGeometry(),new THREE.MeshBasicMaterial());parent.add(c.root,other);
 const geometries=new Set(),materials=new Set();let gd=0,md=0,otherDisposed=0;
 other.geometry.addEventListener('dispose',()=>otherDisposed++);
 for(const m of allMeshes(c.root)){
  const n=m.geometry.getAttribute('normal');for(let i=0;i<n.count;i++){const v=new THREE.Vector3().fromBufferAttribute(n,i);assert.ok(Number.isFinite(v.length())&&Math.abs(v.length()-1)<1e-5);}
  geometries.add(m.geometry);materials.add(m.material);
 }
 for(const g of geometries)g.addEventListener('dispose',()=>gd++);for(const m of materials)m.addEventListener('dispose',()=>md++);
 const reads=h.reads;c.dispose();c.dispose();c.syncDoor();c.advance(.01);c.request(true);
 assert.equal(gd,geometries.size);assert.equal(md,materials.size);assert.equal(h.reads,reads);assert.equal(otherDisposed,0);assert.deepEqual(parent.children,[other]);
 other.geometry.dispose();other.material.dispose();
});

test('invalid recipe fails before allocation and artificial input remains unchanged',()=>{
 const broken=structuredClone(fixturePlan);broken.moving=broken.moving.filter(p=>!p.id.includes('retracted_dog_'));
 assert.throws(()=>describeLatchVisual(broken),/three/);assert.equal(JSON.stringify(fixturePlan),fixtureBytes);
});
