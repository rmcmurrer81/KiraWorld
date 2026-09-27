import test from 'node:test';
import assert from 'node:assert/strict';
import {createAirlockHost} from '../candidate/airlock_host.mjs';

// Entirely invented metadata and synchronous runtime double. The pinned hash
// exercises host nomination ONLY: no package bytes or GLB have been admitted.
// This does not implement or prove real geometry, reach, navigation or collision.
function fixture(){
 const ids=['door:opening_2','door:opening_1'],room='demo:chamber',pair='airlock_pair:airlock';
 const metadata={contract:'world_scene_metadata_v2',scene_id:'demo:invented-host-scene',
  rooms:[{id:room,functional_role:'airlock',label:'Invented Airlock'},{id:'demo:habitat',label:'Invented Habitat'},{id:'demo:equipment',label:'Invented Equipment Vestibule'}],
  airlock_pairs:[{id:pair,room_id:room,contract:'paired_airlock_door_sequence_v1',pressure_simulation:false,state_persistence:'session_local',door_ids:ids,leaf_node_ids:ids.map(id=>id+'-leaf'),portal_ids:ids.map(id=>id+'-portal'),opening_policy:{requires_peer:'closed_and_stopped',blocked_peer_conditions:['nonzero_angle','moving','nonzero_target','motion_held']},closing_policy:'existing_reach_motion_and_occupancy_rules'}],
  doors:ids.map((id,i)=>({id,leaf_node_id:id+'-leaf',portal_id:id+'-portal',pressure_simulation:false,state_persistence:'session_local',initial_state:'closed',room_ids:[room,i?'demo:equipment':'demo:habitat'],interlock_pair_ids:[pair],interaction:{rules:['paired_airlock_peer_closed_stopped']},hinge:{closed_angle:0,open_angle:(i?-1:1)*Math.PI/2}}))};
 const doors=metadata.doors.map(d=>({id:d.id,angle:0,target:0,moving:false,motionHeld:false})),calls={reads:0,commands:[]};let roomId=room;
 const runtime={snapshot:()=>({roomId,nearbyDoor:roomId===room?{id:ids[1]}:null}),doorStates(){calls.reads++;return structuredClone(doors);},toggleDoor(id){calls.commands.push(id);const d=doors.find(d=>d.id===id),m=metadata.doors.find(d=>d.id===id);if(!d)return {ok:false,reason:'Artificial unknown door'};d.target=d.target===0?m.hinge.open_angle:0;d.moving=true;return {ok:true};}};
 const loaded={manifestSha256:'bf7f0934f473b5ad7b0a50f2577c50995f94d3880db30835b4bf0194bdd074cc',manifest:{files:{'scene.json':{sha256:'b'.repeat(64)}}},metadata,runtime};
 let current=loaded,next=0;const pending=new Map();
 const host=createAirlockHost(loaded,{requestFrame:f=>{pending.set(++next,f);return next;},cancelFrame:i=>pending.delete(i),getCurrent:()=>current});
 return {host,loaded,doors,calls,pending,runtime,replace(){current={...loaded};},leave(){roomId='demo:elsewhere';},tick(t){const [id,fn]=pending.entries().next().value;pending.delete(id);fn(t);},settle(i){doors[i].angle=doors[i].target;doors[i].moving=false;},seal(){assert.ok(host.acknowledge('inside').ok);assert.ok(host.acknowledge('outside').ok);},finish(){this.seal();assert.ok(host.begin('outside').ok);for(let i=0;i<=120;i++)this.tick(i*50);assert.equal(pending.size,0);}};
}

test('unrecognized package has no host; artificial nominated package is explicitly distinct from byte admission',()=>{
 assert.equal(createAirlockHost({manifestSha256:'a'.repeat(64)}),null);
 const f=fixture();assert.match(f.host.labels.outside,/Equipment Vestibule/);assert.equal(f.host.snapshot().capabilities.pressurePhysics,false);f.host.dispose();
});
test('unbound/coercible IDs never call nearest-door runtime shorthand',()=>{
 const f=fixture();for(const id of [undefined,null,'','ordinary',['door:opening_1'],{toString:()=> 'door:opening_1'}])assert.equal(f.host.command(id).ok,false);
 assert.deepEqual(f.calls.commands,[]);f.host.dispose();
});
test('unknown pressure holds; explicit seals and six active seconds authorize one exact side',()=>{
 const f=fixture();assert.equal(f.host.command('door:opening_1').ok,false);assert.equal(f.host.begin('outside').ok,false);f.finish();
 assert.equal(f.host.command('door:opening_2').ok,false);assert.equal(f.host.command('door:opening_1').ok,true);assert.deepEqual(f.calls.commands,['door:opening_1']);
 assert.equal(f.host.command('door:opening_1').continueMotion,true);assert.equal(f.calls.commands.length,1);assert.equal(f.host.begin('inside').ok,false);f.host.dispose();
});
test('closure is separate from fictional seal acknowledgment',()=>{
 const f=fixture();f.finish();f.host.command('door:opening_1');f.settle(1);assert.ok(f.host.command('door:opening_1').ok);f.settle(1);
 assert.equal(f.host.snapshot().doors.outside.angle,0);assert.equal(f.host.snapshot().simulatedSealAcknowledged.outside,false);assert.equal(f.host.begin('inside').ok,false);f.host.dispose();
});
test('external bypass faults; moving continuation cannot be authorized',()=>{
 const f=fixture();f.runtime.toggleDoor('door:opening_1');const before=f.calls.commands.length;const r=f.host.command('door:opening_1');
 assert.equal(r.ok,false);assert.equal(r.continueMotion,undefined);assert.equal(f.calls.commands.length,before);assert.equal(f.host.snapshot().phase,'fault');f.host.dispose();
});
test('replaced/disposed hosts reject before runtime observation or dispatch',()=>{
 for(const action of ['replace','dispose']){const f=fixture();if(action==='replace')f.replace();else f.host.dispose();const before=JSON.stringify(f.calls);
  for(const id of [undefined,'ordinary','door:opening_1'])assert.equal(f.host.command(id).ok,false);assert.equal(JSON.stringify(f.calls),before);f.host.dispose();}
});
test('hidden and blur pause reasons aggregate; return requires explicit resume and no catch-up',()=>{
 const f=fixture();f.seal();f.host.begin('outside');f.tick(10);f.tick(60);const stale=[...f.pending.values()][0];f.host.pause('hidden');f.host.pause('blur');stale(8000);assert.equal(f.pending.size,0);
 f.host.clear('hidden');assert.equal(f.host.resume().ok,false);f.host.clear('blur');assert.equal(f.pending.size,0);assert.ok(f.host.resume().ok);f.tick(10000);assert.equal(f.host.snapshot().elapsedSeconds,.05);f.host.dispose();
});
test('room exit and disposal cancel callbacks; stale frame cannot restart',()=>{
 const f=fixture();f.seal();f.host.begin('outside');const stale=[...f.pending.values()][0];f.leave();f.host.update();assert.equal(f.pending.size,0);stale(60);assert.equal(f.pending.size,0);assert.equal(f.host.command('door:opening_1').ok,false);f.host.dispose();stale(90);assert.equal(f.pending.size,0);
});
test('first frame sets baseline; large gaps clamp and reversed time pauses',()=>{
 const f=fixture();f.seal();f.host.begin('outside');f.tick(2);assert.equal(f.host.snapshot().elapsedSeconds,0);f.tick(20000);assert.equal(f.host.snapshot().elapsedSeconds,.05);f.tick(19999);assert.equal(f.pending.size,0);assert.equal(f.host.snapshot().phase,'paused');f.host.dispose();
});
