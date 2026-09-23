// CPU-only actual saved-layout audit. No fixture writes or position injection.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [geometryPath,expected,engine]=process.argv.slice(2);assert.ok(geometryPath&&expected&&engine);
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');const raw=fs.readFileSync(geometryPath);assert.equal(hash(raw),expected);
const g=JSON.parse(raw),original=JSON.stringify(g),imports={};
for(const [name,rel] of Object.entries({frontend:'walk_controller.mjs',portable:'layout_package_assets/source/walk_controller.mjs',navigation:'horizontal_navigation.mjs',dressing:'layout_package_assets/source/room_dressing_plan.mjs'}))imports[name]=await import(pathToFileURL(path.join(engine,rel)));
const {NAVIGATION_CONTRACT,checkHorizontalRoute,checkWalkSpawn}=imports.navigation;
const extra=imports.dressing.buildRoomDressing(g,imports.frontend.createDoorSystem(g).assemblies()).colliders;
const checks=[],walks=[],failures=[];
function test(name,fn){try{const detail=fn();checks.push({name,status:'pass',detail});}catch(e){failures.push({name,message:e.message,stack:e.stack});}}
function aim(c,yaw){for(let i=0;i<20&&Math.abs(c.snapshot().yaw-yaw)>1e-10;i++){const d=yaw-c.snapshot().yaw;c.look(Math.max(-500,Math.min(500,d/.002)),0);}assert.ok(Math.abs(c.snapshot().yaw-yaw)<1e-8);}
function lookAt(c,p){const q=c.snapshot().feet;aim(c,Math.atan2(p[0]-q[0],-(p[2]-q[2])));}
function go(c,p,{diagonal=false,attempt=false}={}){
 const origin=c.snapshot().feet;let steps=0;
 for(let i=0;i<500;i++){
  const q=c.snapshot().feet,dist=Math.hypot(p[0]-q[0],p[2]-q[2]);if(dist<1e-7)return {reached:true,steps,feet:q};
  let yaw=Math.atan2(p[0]-q[0],-(p[2]-q[2]));if(diagonal)yaw-=Math.PI/4;aim(c,yaw);
  const state=c.step(Math.min(i%2?.05:1/60,dist/2.2),{forward:true,right:diagonal});steps++;
  assert.equal(state.feet[1],origin[1]);assert.ok(imports.frontend.AVATAR.eye<imports.frontend.AVATAR.height);
  if(state.blocked){if(attempt)return {reached:false,steps,feet:state.feet,reason:state.blocked};throw new Error('Walking blocked '+state.blocked+' toward '+JSON.stringify(p)+' at '+JSON.stringify(state.feet));}
 }
 throw new Error('Walking did not converge');
}
function point(portal,signedDistance,tangentOffset=0){return portal.axis==='x'?[portal.coordinate+signedDistance,0,portal.center+tangentOffset]:[portal.center+tangentOffset,0,portal.coordinate+signedDistance];}
function center(portal){return point(portal,0);}
function animate(c){for(let i=0;i<12;i++)c.step(.05,{});}
function operate(c,portal,expectedState){lookAt(c,center(portal));assert.equal(c.snapshot().nearbyDoor?.id,portal.id);const result=c.toggleDoor();assert.equal(result.ok,true,result.reason);animate(c);assert.equal(c.doorStates().find(d=>d.id===portal.id).state,expectedState);}
for(const libName of ['frontend','portable'])test(libName+': continuous entry walk, six doors both ways and closed reblocking',()=>{
 const c=imports[libName].createWalkController(g,{extraColliders:extra});const visits=[],p1=g.portals[0],p2=g.portals[1];
 go(c,[1.5,0,-6.1]);operate(c,p1,'open');go(c,[1.5,0,-2],{diagonal:true});visits.push(c.snapshot().roomId);
 lookAt(c,center(p2));const denied=c.toggleDoor();assert.equal(denied.ok,false);assert.equal(denied.interlock.peerDoorId,p1.id);
 operate(c,p1,'closed');operate(c,p2,'open');go(c,[1.5,0,.9]);operate(c,p2,'closed');go(c,[1.5,0,6],{diagonal:true});visits.push(c.snapshot().roomId);
 const armResults=[];
 for(const portal of g.portals.slice(2)){
  const room=g.rooms.find(r=>r.id===portal.room_a),sign=Math.sign((portal.axis==='x'?room.x+room.width/2:room.z+room.depth/2)-portal.coordinate);
  const outside=point(portal,-sign*.9),inside=point(portal,sign*1.8);
  go(c,outside,{diagonal:true});const blocked=go(c,inside,{attempt:true,diagonal:true});assert.equal(blocked.reached,false);assert.equal(blocked.reason,'door_obstruction');
  assert.ok((c.snapshot().feet[portal.axis==='x'?0:2]-portal.coordinate)*sign<0,'Crossed a closed door');
  go(c,outside);operate(c,portal,'open');go(c,inside,{diagonal:true});assert.equal(c.snapshot().roomId,room.id);visits.push(room.id);
  operate(c,portal,'closed');const returnBlocked=go(c,outside,{attempt:true});assert.equal(returnBlocked.reached,false);assert.equal(returnBlocked.reason,'door_obstruction');
  go(c,inside);operate(c,portal,'open');go(c,outside);operate(c,portal,'closed');go(c,[1.5,0,6],{diagonal:true});
  armResults.push({door:portal.id,entered_and_returned:true,closed_blocked_both_directions:true});
 }
 go(c,[1.5,0,.9]);operate(c,p2,'open');go(c,[1.5,0,-2],{diagonal:true});operate(c,p2,'closed');operate(c,p1,'open');go(c,[1.5,0,-6.1]);operate(c,p1,'closed');go(c,[1.5,0,-6.5]);visits.push(c.snapshot().roomId);
 assert.ok(c.doorStates().every(d=>d.state==='closed'));assert.equal(c.snapshot().roomId,g.connectivity.entry_room_id);
 const result={controller:libName,rooms_visited:[...new Set(visits)],distance:c.snapshot().distance,armResults,final:c.snapshot()};walks.push(result);return result;
});
function route(a,b){return {id:'audit_segment',avatar_radius:.34,avatar_height:1.68,points:[a,b]};}
function nav(colliders){return {contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders};}
test('Actual six doorway centre and shallow diagonal paths block closed, pass open, and reblock closed',()=>{
 const results=[];
 for(const portal of g.portals){
  const rooms=g.rooms.find(r=>r.id===portal.room_b),n=portal.axis==='x'?0:2,sign=Math.sign((n===0?rooms.x+rooms.width/2:rooms.z+rooms.depth/2)-portal.coordinate),feet=point(portal,sign*.9);
  for(const libName of ['frontend','portable']){
   const d=imports[libName].createDoorSystem(g),segmentResults=[];
   const variants=[[-.9,0,.9,0],[-.9,-.1,.9,.1],[-.9,.1,.9,-.1]];
   for(let phase=0;phase<3;phase++){
    for(const [a,u,b,v] of variants)for(const reverse of [false,true]){
     const points=[point(portal,a,u),point(portal,b,v)];if(reverse)points.reverse();
     const checks=[g.colliders,d.colliders(),extra].map(c=>checkHorizontalRoute(route(...points),nav(c)));
     assert.equal(checks[0].status,'clear');assert.equal(checks[2].status,'clear');assert.equal(checks[1].status,phase===1?'clear':'blocked');segmentResults.push({phase,reverse,tangent:[u,v],status:checks[1].status});
    }
    if(phase<2){assert.equal(d.toggle(portal.id,feet).ok,true);for(let i=0;i<12;i++)d.advance(.05,feet);}
   }
   results.push({door:portal.id,controller:libName,segments:segmentResults.length});
  }
 }return results;
});
test('Thin closed-door crossing is blocked despite clear endpoints, including diagonal mid-segment contact',()=>{
 const result=[];
 for(const portal of g.portals){
  const d=imports.frontend.createDoorSystem(g),leaf=d.all().find(x=>x.id===portal.id).collider;
  const a=point(portal,-.6,-.08),b=point(portal,.6,.08),v=nav([leaf]);assert.equal(checkWalkSpawn(a,v).ok,true);assert.equal(checkWalkSpawn(b,v).ok,true);
  assert.equal(checkHorizontalRoute(route(a,b),v).status,'blocked');assert.equal(checkHorizontalRoute(route(b,a),v).status,'blocked');
  result.push({door:portal.id,endpoints_clear:true,midsegment_blocked:true});
 }return result;
});
test('Actual wall and closed-leaf corner clipping is blocked within one maximum normal step',()=>{
 const doors=imports.frontend.createDoorSystem(g),boxes=[...g.colliders.filter(c=>c.min[1]<1.68&&c.max[1]>0),...doors.colliders().filter(c=>c.id.endsWith('_leaf'))],cases=[];
 for(const box of boxes){
  const x=box.min[0]-.34,z=box.min[2]-.34,a=[x-.02,0,z+.05],b=[x+.05,0,z-.02];
  // Restrict to saved support: endpoint and midstep floor must be valid. The
  // selected actual collider is isolated only to expose endpoint-only misses.
  if(checkHorizontalRoute(route(a,b),nav([])).status!=='clear')continue;
  const v=nav([box]);assert.equal(checkWalkSpawn(a,v).ok,true);assert.equal(checkWalkSpawn(b,v).ok,true);
  assert.ok(Math.hypot(b[0]-a[0],b[2]-a[2])<.11);assert.equal(checkHorizontalRoute(route(a,b),v).status,'blocked');cases.push(box.id);
 }
 assert.ok(cases.length>=10);return {cases:cases.length,collider_ids:cases,step_metres:Math.hypot(.07,.07)};
});
test('Actual exterior and solid room partitions block long and oblique segments at normal walker height',()=>{
 const trials=[[[1.5,0,6],[1.5,0,13]],[[1.5,0,6],[-1,0,6.5]],[[1.5,0,6],[4,0,6]],[[1.5,0,-2],[4,0,-2]],[[1.5,0,1],[-1,0,1]],[[1.5,0,1],[4,0,1]],[[1.5,0,11.5],[3.8,0,11.5]]];
 return trials.map(([a,b])=>{const r=checkHorizontalRoute(route(a,b),nav(g.colliders));assert.equal(r.status,'blocked');return {a,b,reason:r.reason,collider:r.collider_id};});
});
test('Paired airlock opening reservations remain exclusive at zero angle, moving, held and open states',()=>{
 const result=[];
 for(const libName of ['frontend','portable']){
  const d=imports[libName].createDoorSystem(g);assert.equal(d.toggle('opening_1',[1.5,0,-6.1]).ok,true);
  const held0=d.toggle('opening_2',[1.5,0,-2]);assert.equal(held0.ok,false);assert.ok(held0.interlock);
  d.advance(.05,[1.5,0,-6.1]);assert.equal(d.toggle('opening_2',[1.5,0,-2]).ok,false);
  d.advance(.05,[1.5,0,-4.5]);assert.equal(d.all()[0].motionHeld,true);assert.equal(d.toggle('opening_2',[1.5,0,-2]).ok,false);
  for(let i=0;i<12;i++)d.advance(.05,[1.5,0,-2]);assert.equal(d.all()[0].state,'open');assert.equal(d.toggle('opening_2',[1.5,0,-2]).ok,false);
  assert.equal(d.toggle('opening_1',[1.5,0,-2]).ok,true);for(let i=0;i<12;i++)d.advance(.05,[1.5,0,-2]);assert.equal(d.toggle('opening_2',[1.5,0,-2]).ok,true);result.push(libName);
 }return result;
});
assert.equal(JSON.stringify(g),original);assert.equal(hash(fs.readFileSync(geometryPath)),expected);
const output={status:failures.length?'AUDIT_FAILURES_REQUIRE_CLASSIFICATION':'BOUNDED_ACTUAL_NAVIGATION_AUDIT_PASS_NO_NEW_DEFECT',checks,failures,geometry_sha256:expected,furniture_colliders:extra.length,walks,owner_geometry_changed:false,
 limits:['Actual saved geometry with authored static furniture and current conservative square avatar/collider model.','Camera eye1.56m and body1.68m; no head tracking, vertical movement, jumping, body physics or pressure simulation.','No UI or visual realism review; isolated per-collider corner tests supplement ordinary controller walks.'],models_gpu_ui:0};
fs.writeFileSync(new URL('./AUDIT-RESULT.json',import.meta.url),JSON.stringify(output,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:output.status,checks:checks.length,failures,walk_distances:walks.map(w=>w.distance)}));
if(failures.length)process.exitCode=1;
