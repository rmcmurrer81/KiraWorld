import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../../package-consumer-083/candidate/vendor/three/build/three.module.js';
import {planPressureHatch,buildPressureHatch,hatchCollidersAt} from '../src/legacy/pressure_hatch.mjs';
import {planHatchArchitecture} from '../src/legacy/pressure_hatch_architecture.mjs';
import {validateDoorShape} from '../../package-consumer-083/candidate/door_metadata.mjs';
import {LATCH_HATCH_CONTRACT,planLatchedPressureHatch,buildLatchedPressureHatch,latchHatchCollidersAt,describeLatchedHatchAuthoring,validateLatchedHatchPlan} from '../src/pressure_hatch_latched.mjs';
function fixture(axis='x',sign=1){
 const n=axis==='x'?'x':'z',t=axis==='x'?'z':'x';
 const room=(id,c)=>({id,[n]:c,[t]:0,width:4,depth:4,height:3,floor_y:0,access:'walkable_layout'});
 const rooms=sign>0?[room('a',0),room('b',-4),room('c',4)]:[room('a',-4),room('b',0),room('c',-8)];
 const p=(id,b,coordinate)=>({id,room_a:'a',room_b:b,axis,coordinate,center:2,width:1.2,height:2.2,state:'open_passage'});
 return {contract:'compiled_blueprint_geometry_v1',units:'meters',rooms,primitives:[],portals:[p('one','b',0),p('two','c',sign*4)],functional_program:{a:'airlock'}};
}
function make(g=fixture(),portal='one'){
 const plan=planLatchedPressureHatch(g,portal),identity={},state={runtimeIdentity:identity,id:'door:'+portal,angle:0,target:0,moving:false};
 let reads=0,current=true;
 const h=buildLatchedPressureHatch({THREE,plan,doorId:state.id,runtimeIdentity:identity,readDoor:()=>{reads++;return state;},isCurrent:i=>current&&i===identity});
 h.syncDoor();return {plan,state,h,get reads(){return reads;},invalidate(){current=false;}};
}
function contains(bounds,p,eps=2e-6){return p.every((v,i)=>v>=bounds.min[i]-eps&&v<=bounds.max[i]+eps);}
function union(bs){return {min:[0,1,2].map(i=>Math.min(...bs.map(b=>b.min[i]))),max:[0,1,2].map(i=>Math.max(...bs.map(b=>b.max[i])))};}
function checkMeshes(h,angle){
 const cs=latchHatchCollidersAt(h.plan,angle);h.root.updateMatrixWorld(true);
 for(const [id,m] of h.meshes){
  const bounds=union(cs.filter(c=>c.owner===id)),attr=m.geometry.getAttribute('position');
  for(let i=0;i<attr.count;i++)assert.ok(contains(bounds,new THREE.Vector3().fromBufferAttribute(attr,i).applyMatrix4(m.matrixWorld).toArray()),'Mesh outside all-pose collider: '+id);
 }
}
test('exact21 old hardware parts replaced by28 uniquely owned meshes; retained leaf/frame unchanged',()=>{
 const g=fixture(),before=JSON.stringify(g),old=planPressureHatch(g,'one'),p=planLatchedPressureHatch(g,'one');
 assert.equal(p.contract,LATCH_HATCH_CONTRACT);assert.equal(p.replacedPartIds.length,21);assert.equal(p.hardware.length,28);
 for(const k of ['hinge','hingeLocal','openAngle','origin','aperture','leafWidth','leafHeight','localLeafCenter','limits'])assert.deepEqual(p[k],old[k]);
 const removed=new Set(p.replacedPartIds);
 assert.deepEqual(p.retained.fixed,old.fixed.filter(x=>!removed.has(x.id)));assert.deepEqual(p.retained.moving,old.moving.filter(x=>!removed.has(x.id)));
 for(const part of p.parts){assert.ok(!removed.has(part.id));assert.ok(p.colliders.some(c=>c.owner===part.id));}
 assert.equal(JSON.stringify(g),before);assert.ok(Object.isFrozen(p.hardware[0].representation));
 const {h}=make(g);let count=0;h.root.traverse(o=>{if(o.isMesh)count++;});assert.equal(count,p.parts.length);assert.equal(h.meshes.size,count);h.dispose();
});
test('all hardware meshes stay within analytic all-pose bounds for both axes and normal signs',()=>{
 for(const axis of ['x','z'])for(const sign of [-1,1]){
  const {h,plan}=make(fixture(axis,sign));assert.equal(h.request(true).ok,true);
  checkMeshes(h,0);
  for(let i=0;i<16;i++){assert.equal(h.advance(.05).ok,true);checkMeshes(h,0);}
  assert.equal(h.snapshot().fraction,1);assert.equal(h.snapshot().sealAcknowledgementChanged,false);h.dispose();
 }
});
test('released hardware follows the unchanged hinge through its full arc within conservative sweep',()=>{
 for(const axis of ['x','z'])for(const sign of [-1,1]){
  const {h,plan,state}=make(fixture(axis,sign));
  for(const t of [0,.25,.5,.75,1]){
   state.angle=plan.openAngle*t;state.target=plan.openAngle;state.moving=t<1;
   assert.equal(h.syncDoor().ok,true);checkMeshes(h,state.angle);
   for(const c of latchHatchCollidersAt(plan,state.angle).filter(c=>c.motion==='kinematic'))assert.ok(contains(plan.swingBounds,c.min)&&contains(plan.swingBounds,c.max));
  }h.dispose();
 }
});
test('hollow keeper retains a bolt channel; fixed hardware does not fill the central standing passage',()=>{
 const {plan,h}=make(),old=planPressureHatch(fixture(),'one');
 for(let i=0;i<3;i++){
  const parts=plan.hardware.filter(p=>p.id.includes('_keeper_'+(i+1)+'_'));assert.equal(parts.length,4);
  const raw=old.fixed.find(p=>p.id===`hatch_one_keeper_1_${Math.round(old.aperture.top*[.25,.5,.75][i]*1000)}`);
  for(const p of parts)assert.equal(contains(p.allPoseLocalBounds,raw.center,0),false);
 }
 for(const c of plan.colliders.filter(c=>c.motion==='static'))assert.equal(contains(c,[0,1,0],0),false);
 h.dispose();
});
test('export-ready records cover every mesh and collider; do not claim admitted package or pressure',()=>{
 const {plan,h}=make(),meta=describeLatchedHatchAuthoring(plan),expected=new Set(plan.parts.map(p=>p.id));
 assert.equal(meta.variant,LATCH_HATCH_CONTRACT);assert.equal(meta.completeWorldPackage,false);assert.equal(meta.requiresNewProducerAndConsumer,true);
 assert.equal(meta.pressureSimulation,false);assert.equal(meta.sealAcknowledgementAuthority,false);
 assert.equal(meta.initialVisualState,'released');assert.equal(meta.parts.length,h.meshes.size);
 for(const c of meta.colliders)assert.ok(expected.has(c.owner));
 for(const p of meta.parts)assert.deepEqual(p.colliderIds,meta.colliders.filter(c=>c.owner===p.id).map(c=>c.id));
 const copy=JSON.parse(JSON.stringify(plan));assert.equal(validateLatchedHatchPlan(copy,fixture(),'one').contract,LATCH_HATCH_CONTRACT);
 copy.hardware[0].representation.size[0]*=2;assert.throws(()=>validateLatchedHatchPlan(copy,fixture(),'one'),/differs/);h.dispose();
});
test('old073 authoring, architectural and083 consumer contracts reject new variant without relaxation',()=>{
 const g=fixture(),p=planLatchedPressureHatch(g,'one');
 assert.throws(()=>buildPressureHatch(THREE,p),/Unsupported hatch/);assert.throws(()=>hatchCollidersAt(p,0),/Invalid hatch/);
 assert.throws(()=>planHatchArchitecture(g,[p]),/Invalid hatch/);
 const d={variant:LATCH_HATCH_CONTRACT,leaf_node_id:'leaf',hinge:{}};
 assert.throws(()=>validateDoorShape(d,new Map([['leaf',{kind:'door_leaf'}]]),new Map()),/Unsupported door variant/);
 assert.throws(()=>buildLatchedPressureHatch({THREE,plan:JSON.parse(JSON.stringify(p))}),/exact locally authored/);
});
test('pause/fault/dispose keep visual motion separate from door permission and release owned resources',()=>{
 const x=make(),{h,state}=x;h.request(true);h.advance(.05);const fraction=h.snapshot().fraction;
 h.pause('hidden');h.pause('manual');h.advance(.05);assert.equal(h.snapshot().fraction,fraction);
 h.resume('hidden');h.advance(.05);assert.equal(h.snapshot().fraction,fraction);h.resume('manual');
 state.target=x.plan.openAngle;state.moving=true;assert.equal(h.syncDoor().ok,false);assert.equal(h.root.visible,false);
 assert.equal(h.snapshot().fault,'Door left the closed stationary pose; latch artwork reset');
 state.target=0;state.moving=false;assert.equal(h.reset().ok,true);
 x.invalidate();assert.equal(h.syncDoor().ok,false);assert.equal(h.root.visible,false);
 const gs=new Set(),ms=new Set();h.root.traverse(o=>{if(o.isMesh){gs.add(o.geometry);ms.add(o.material);}});
 let gc=0,mc=0;for(const g of gs)g.addEventListener('dispose',()=>gc++);for(const m of ms)m.addEventListener('dispose',()=>mc++);
 const reads=x.reads;h.dispose();h.dispose();h.syncDoor();h.advance(.01);assert.equal(x.reads,reads);assert.equal(h.root.children.length,0);
 assert.equal(gc,gs.size);assert.equal(mc,ms.size);
});
test('two opposite airlock placements are independent; ordinary door is not authored into a hatch',()=>{
 const g=fixture(),a=make(g,'one'),b=make(g,'two');a.h.request(true);a.h.advance(.05);assert.equal(b.h.snapshot().fraction,0);
 assert.equal(a.plan.normalSign,-b.plan.normalSign);assert.notDeepEqual(a.plan.hinge,b.plan.hinge);
 const ordinary={...g,functional_program:{}};assert.equal(planLatchedPressureHatch(ordinary,'one'),null);a.h.dispose();b.h.dispose();
});
