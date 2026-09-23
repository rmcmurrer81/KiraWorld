import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
import * as old from './baseline/walk_controller.mjs';
import * as next from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/horizontal_navigation.mjs';
const [source,expected,engine]=process.argv.slice(2);assert.ok(source&&expected&&engine);
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex'),raw=fs.readFileSync(source);assert.equal(hash(raw),expected);
const g=JSON.parse(raw),before=JSON.stringify(g),checks=[],captures={};
const dressingPath=path.join(engine,'layout_package_assets/source/room_dressing_plan.mjs');
const {buildRoomDressing}=await import(pathToFileURL(dressingPath));
const plan=buildRoomDressing(g,next.createDoorSystem(g).assemblies());
const extra=plan.colliders;
function test(name,fn){fn();checks.push(name);}
function aim(c,yaw){let difference=yaw-c.snapshot().yaw;while(Math.abs(difference)>1e-10){const step=Math.max(-1,Math.min(1,difference));c.look(step/.002,0);difference=yaw-c.snapshot().yaw;}}
function toAirlock(lib){
 const c=lib.createWalkController(g,{extraColliders:extra});for(let i=0;i<3;i++)c.step(.05,{forward:true});
 assert.equal(c.toggleDoor().id,'opening_1');for(let i=0;i<10;i++)c.step(.05,{});
 for(let i=0;i<37;i++)c.step(.05,{forward:true});assert.equal(c.snapshot().roomId,'airlock');
 return c;
}
function closeEntry(c){aim(c,0);assert.equal(c.toggleDoor().state,'closing');for(let i=0;i<10;i++)c.step(.05,{});aim(c,Math.PI);}
test('Actual furnished airlock: F selects the faced exit, not the closer closed door behind',()=>{
 const a=toAirlock(old),b=toAirlock(next);closeEntry(a);closeEntry(b);
 assert.deepEqual(a.snapshot().feet,b.snapshot().feet);assert.equal(a.snapshot().nearbyDoor.id,'opening_1');assert.equal(b.snapshot().nearbyDoor.id,'opening_2');
 const previous=a.toggleDoor(),corrected=b.toggleDoor();assert.equal(previous.id,'opening_1');assert.equal(corrected.id,'opening_2');
 captures.airlock={feet:b.snapshot().feet,yaw:b.snapshot().yaw,baseline_target:previous.id,candidate_target:corrected.id};
});
test('Actual airlock: looking at exit cannot bypass an open paired entry',()=>{
 const c=toAirlock(next);assert.equal(c.snapshot().nearbyDoor.id,'opening_2');const held=c.toggleDoor();
 assert.equal(held.ok,false);assert.equal(held.interlock.peerDoorId,'opening_1');assert.equal(c.doorStates().find(d=>d.id==='opening_2').state,'closed');
 captures.interlock=held;
});
test('Actual airlock: turning sideways yields no target or hidden door mutation',()=>{
 const c=toAirlock(next);aim(c,Math.PI/2);assert.equal(c.snapshot().nearbyDoor,null);const before=JSON.stringify(c.doorStates());
 assert.deepEqual(c.toggleDoor(),{ok:false,reason:'Face a nearby door to open or close it.'});assert.equal(JSON.stringify(c.doorStates()),before);
});
test('Actual furnished corridor: looking west targets Operations and east targets Crew Living',()=>{
 const states=[];
 for(const lib of [old,next]){
  const c=toAirlock(lib);closeEntry(c);assert.equal(c.toggleDoor('opening_2').ok,true);for(let i=0;i<10;i++)c.step(.05,{});
  for(let i=0;i<44;i++)c.step(.05,{forward:true});assert.equal(c.snapshot().roomId,'circulation');
  aim(c,-Math.PI/2);const west=c.snapshot();aim(c,Math.PI/2);const east=c.snapshot();states.push({feet:east.feet,west:west.nearbyDoor?.id,east:east.nearbyDoor?.id});
 }
 assert.deepEqual(states[0].feet,states[1].feet);assert.equal(states[0].west,states[0].east);
 assert.deepEqual([states[1].west,states[1].east],['opening_3','opening_4']);captures.corridor={baseline:states[0],candidate:states[1]};
});
test('All six actual doors retain exact poses, frames, collisions and open/closed routes',()=>{
 captures.routes=[];
 for(const portal of g.portals){
  const a=old.createDoorSystem(g),b=next.createDoorSystem(g),roomB=g.rooms.find(r=>r.id===portal.room_b),n=portal.axis==='x'?0:2;
  const feet=portal.axis==='x'?[portal.coordinate,roomB.floor_y,portal.center]:[portal.center,roomB.floor_y,portal.coordinate];
  feet[n]+=Math.sign((n===0?roomB.x+roomB.width/2:roomB.z+roomB.depth/2)-portal.coordinate)*.9;
  const route=g.routes.find(r=>r.id===portal.id);
  // The actual controller validates three bounded collider sets. Combining
  // them would exceed the independent128-item limit without testing a fault.
  const check=(route,d)=>[g.colliders,d.colliders(),extra].map(colliders=>checkHorizontalRoute(route,{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders})).find(r=>r.status!=='clear')||{status:'clear'};
  assert.equal(check(route,b).status,'blocked');assert.deepEqual(a.assemblies(),b.assemblies());
  assert.equal(a.toggle(portal.id,feet).ok,true);assert.equal(b.toggle(portal.id,feet).ok,true);
  for(let i=0;i<10;i++){a.advance(.05,feet);b.advance(.05,feet);assert.deepEqual(a.all(),b.all());assert.deepEqual(a.colliders(),b.colliders());}
  assert.equal(check(route,b).status,'clear');assert.equal(check({...route,points:[...route.points].reverse()},b).status,'clear');
  assert.equal(a.toggle(portal.id,feet).ok,true);assert.equal(b.toggle(portal.id,feet).ok,true);
  for(let i=0;i<10;i++){a.advance(.05,feet);b.advance(.05,feet);assert.deepEqual(a.all(),b.all());}
  assert.equal(check(route,b).status,'blocked');captures.routes.push({id:portal.id,closed:'blocked',open_both_directions:'clear',reclosed:'blocked'});
 }
});
test('Low-level explicit proximity queries and targeted actions remain compatible',()=>{
 const a=old.createDoorSystem(g),b=next.createDoorSystem(g),feet=[1.5,0,-2];
 assert.deepEqual(a.nearest(feet),b.nearest(feet));assert.throws(()=>b.nearest(feet,NaN),TypeError);
 assert.equal(b.nearest(feet,0).id,'opening_1');assert.equal(b.nearest(feet,Math.PI).id,'opening_2');
 assert.equal(b.nearest(feet,Math.PI/2),null);assert.equal(b.nearest([1.5,2,-2],0),null);
 assert.deepEqual(a.toggle('opening_1',feet),b.toggle('opening_1',feet));
});
test('Actual saved geometry and caller object remain unchanged',()=>{assert.equal(JSON.stringify(g),before);assert.equal(hash(fs.readFileSync(source)),expected);});
const result={status:'ACTUAL_SAVED_MARS_FACING_AND_DOOR_MECHANICS_PASS',checks,checks_count:checks.length,captures,geometry_sha256:expected,
 dressing_source_sha256:hash(fs.readFileSync(dressingPath)),furniture_colliders:extra.length,room_equipment:plan.objects.map(o=>({room_id:o.room_id,kind:o.kind})),
 models_gpu_ui:0,owner_geometry_copied_or_modified:false,visual_or_owner_approval:false,
 limits:['Targets use a horizontal60-degree facing cone, not pixel picking or occlusion raycasts.','Low-level explicit door IDs retain their proximity/sweep/interlock contract.','Conservative collision, session-local door states, no pressure or exterior EVA simulation remain unchanged.','No new visual review, renderer/export refresh or installation.']};
fs.writeFileSync(new URL('./ACTUAL-DOOR-TEST-RESULT.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,checks:checks.length,captures,extra_colliders:extra.length}));
