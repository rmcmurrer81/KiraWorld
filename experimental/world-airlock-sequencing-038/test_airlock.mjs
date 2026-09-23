import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {createDoorSystem,DOOR_CONTRACT,AIRLOCK_SEQUENCE_CONTRACT} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {createDoorSystem as baselineDoors} from './baseline/walk_controller.mjs';
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/synthetic_habitat.json',import.meta.url),'utf8'));
const original=JSON.stringify(fixture),checks=[],feet=[1.5,0,-2];
const step=(system,count,position=feet)=>{for(let i=0;i<count;i++)system.advance(.05,position);};
const pose=(system,id)=>system.all().find(d=>d.id===id);
const test=(name,body)=>{body();checks.push(name);};
for(const [first,second] of [['opening_1','opening_2'],['opening_2','opening_1']]){
 test(first+': same-frame pending opening blocks its peer at angle zero',()=>{
  const doors=createDoorSystem(fixture);assert.equal(doors.toggle(first,feet).ok,true);assert.equal(pose(doors,first).angle,0);
  const held=doors.toggle(second,feet);assert.equal(held.ok,false);assert.equal(held.interlock.peerDoorId,first);assert.equal(held.interlock.contract,AIRLOCK_SEQUENCE_CONTRACT);assert.match(held.reason,/fully closed and stopped/);
  assert.equal(pose(doors,second).state,'closed');
 });
 test(first+': opening and fully open peer block, then closing restores access',()=>{
  const doors=createDoorSystem(fixture);doors.toggle(first,feet);step(doors,4);assert.equal(pose(doors,first).state,'opening');assert.equal(doors.toggle(second,feet).ok,false);
  step(doors,4);assert.equal(pose(doors,first).state,'open');assert.equal(doors.toggle(second,feet).ok,false);
  assert.equal(doors.toggle(first,feet).ok,true);step(doors,4);assert.equal(pose(doors,first).state,'closing');assert.equal(doors.toggle(second,feet).ok,false);
  step(doors,4);assert.equal(pose(doors,first).state,'closed');assert.equal(doors.toggle(second,feet).ok,true);
 });
 test(first+': held opening at angle zero remains reserved',()=>{
  const doors=createDoorSystem(fixture);doors.toggle(first,feet);const box=doors.assemblies().find(a=>a.id===first).swingBounds;
  const occupied=[(box.min[0]+box.max[0])/2,0,(box.min[2]+box.max[2])/2];doors.advance(.05,occupied);
  assert.equal(pose(doors,first).angle,0);assert.equal(pose(doors,first).motionHeld,true);assert.equal(doors.toggle(second,feet).ok,false);
  step(doors,8);assert.equal(pose(doors,first).state,'open');assert.equal(pose(doors,second).state,'closed');
 });
 test(first+': closing still respects the existing occupied swing',()=>{
  const doors=createDoorSystem(fixture);doors.toggle(first,feet);step(doors,8);const box=doors.assemblies().find(a=>a.id===first).swingBounds;
  const occupied=[(box.min[0]+box.max[0])/2,0,(box.min[2]+box.max[2])/2];
  assert.equal(doors.toggle(first,occupied).ok,false);assert.equal(pose(doors,first).state,'open');
  assert.equal(doors.toggle(first,feet).ok,true);doors.advance(.05,occupied);assert.equal(pose(doors,first).motionHeld,true);assert.equal(doors.toggle(second,feet).ok,false);
  step(doors,8);assert.equal(pose(doors,first).state,'closed');assert.equal(doors.toggle(second,feet).ok,true);
 });
}
test('Explicit role works after the airlock is renamed',()=>{
 const g=structuredClone(fixture);g.rooms.find(r=>r.id==='airlock').id='transfer_chamber';g.rooms.find(r=>r.id==='transfer_chamber').name='Transfer chamber';
 for(const p of g.portals)for(const k of ['room_a','room_b'])if(p[k]==='airlock')p[k]='transfer_chamber';
 g.functional_program.transfer_chamber=g.functional_program.airlock;delete g.functional_program.airlock;
 const d=createDoorSystem(g);assert.equal(d.interlocks()[0].roomId,'transfer_chamber');d.toggle('opening_1',feet);assert.equal(d.toggle('opening_2',feet).ok,false);
});
test('Names and room IDs alone never imply an airlock interlock',()=>{
 const g=structuredClone(fixture);delete g.functional_program.airlock;const a=createDoorSystem(g),b=baselineDoors(g);assert.deepEqual(a.interlocks(),[]);
 for(const id of ['opening_1','opening_2'])assert.deepEqual(a.toggle(id,feet),b.toggle(id,feet));
 for(let i=0;i<8;i++)assert.deepEqual(a.advance(.05,feet),b.advance(.05,feet));assert.ok(a.all().slice(0,2).every(d=>d.state==='open'));
});
test('Authored airlock with one or more than two supported doors is rejected',()=>{
 for(const id of ['equipment_vestibule','circulation']){const g=structuredClone(fixture);delete g.functional_program.airlock;g.functional_program[id]='airlock';assert.throws(()=>createDoorSystem(g),/exactly two supported doors/);}
 const g=structuredClone(fixture);g.functional_program.missing_room='airlock';assert.throws(()=>createDoorSystem(g),/airlock room is unavailable/);
});
test('Malformed role map is rejected without guessing its meaning',()=>{
 for(const value of ['airlock',[],42]){const g=structuredClone(fixture);g.functional_program=value;assert.throws(()=>createDoorSystem(g),/authored room program/);}
});
test('Unrelated ordinary doors retain exact baseline poses and responses',()=>{
 const a=createDoorSystem(fixture),b=baselineDoors(fixture);a.toggle('opening_1',feet);b.toggle('opening_1',feet);step(a,8);step(b,8);
 const at=[1,0,3];assert.deepEqual(a.toggle('opening_3',at),b.toggle('opening_3',at));
 for(let i=0;i<8;i++)assert.deepEqual(a.advance(.05,at),b.advance(.05,at));
 assert.deepEqual(a.toggle('opening_3',at),b.toggle('opening_3',at));for(let i=0;i<8;i++)assert.deepEqual(a.advance(.05,at),b.advance(.05,at));
});
test('A shared door observes both explicitly authored airlock pairs',()=>{
 const rooms=Array.from({length:4},(_,i)=>({id:'room_'+i,name:'Room '+i,x:i*3,z:0,width:3,depth:3,height:2.8,floor_y:0,access:'walkable_layout'}));
 const portals=Array.from({length:3},(_,i)=>({id:'door_'+i,room_a:'room_'+i,room_b:'room_'+(i+1),axis:'x',coordinate:(i+1)*3,center:1.5,width:1.2,height:2.2,state:'open_passage'}));
 const g={rooms,portals,functional_program:{room_1:'airlock',room_2:'airlock'}};
 const d=createDoorSystem(g);assert.equal(d.interlocks().length,2);
 assert.equal(d.toggle('door_0',[4.05,0,1.5]).ok,true);step(d,8,[4.05,0,1.5]);assert.equal(d.toggle('door_1',[4.05,0,1.5]).ok,false);
 assert.equal(d.toggle('door_2',[7.05,0,1.5]).ok,true);step(d,8,[7.05,0,1.5]);assert.equal(d.toggle('door_1',[7.05,0,1.5]).ok,false);
 assert.equal(d.toggle('door_0',[4.05,0,1.5]).ok,true);step(d,8,[4.05,0,1.5]);const held=d.toggle('door_1',[7.05,0,1.5]);assert.equal(held.ok,false);assert.equal(held.interlock.peerDoorId,'door_2');
});
test('Peer reason names the adjacent destination and reaches the existing UI',()=>{
 const doors=createDoorSystem(fixture);doors.toggle('opening_1',feet);const result=doors.toggle('opening_2',feet);assert.match(result.reason,/Equipment Vestibule/);
 const viewer=fs.readFileSync(new URL('./baseline/viewer.mjs',import.meta.url),'utf8');
 const action=viewer.slice(viewer.indexOf('  function interactDoor(){'),viewer.indexOf("  doorButton.addEventListener('click',interactDoor)"));
 const display=viewer.slice(viewer.indexOf('    doorMessage.textContent=nearby?.motionHeld?'),viewer.indexOf('    camera.position.set(state.feet'));
 const get=new Function('controller','doorButton','performance','doorMessage','let doorNotice="",doorNoticeUntil=0;'+action+';interactDoor();const nearby={motionHeld:false,state:"closed"},now=1;'+display+';return doorMessage.textContent;');
 assert.equal(get({toggleDoor:()=>result},{blur(){}},{now:()=>0},{}),result.reason);
});
test('Contract and immutable pairing state are explicit, with no pressure model',()=>{
 const d=createDoorSystem(fixture);assert.equal(d.contract,DOOR_CONTRACT);assert.equal(d.contract,'preview_hinged_doors_v2');
 const pair=d.interlocks()[0];assert.deepEqual(pair.doorIds,['opening_1','opening_2']);assert.equal(pair.pressureSimulation,false);assert.equal(pair.statePersistence,'session_local');
 assert.throws(()=>pair.doorIds.push('bad'));assert.throws(()=>d.interlocks().push('bad'));assert.equal(JSON.stringify(fixture),original);
});
const report={status:'PAIRED_AIRLOCK_SEQUENCING_CPU_PASS',checks,checks_count:checks.length,geometry_mutated:false,models_gpu_browser_ui:0,
 source_hashes:{baseline:hash(fs.readFileSync(new URL('./baseline/walk_controller.mjs',import.meta.url))),candidate:hash(fs.readFileSync(new URL('./candidate/tools/world_builder_engine/walk_controller.mjs',import.meta.url)))},
 limitations:['Mutual exclusion of two explicitly authored room doors only.','Not a pressure seal, leak test, pressure cycle or exterior EVA connection.','No installation or visual review.']};
const serial=fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('AIRLOCK-RESULT')&&n.endsWith('.json')).length+1;
fs.writeFileSync(new URL('./AIRLOCK-RESULT-'+serial+'.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,checks:checks.length,receipt:'AIRLOCK-RESULT-'+serial+'.json'}));
