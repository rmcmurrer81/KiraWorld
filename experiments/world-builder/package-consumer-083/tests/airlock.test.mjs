import test from 'node:test';
import assert from 'node:assert/strict';
import {bindAirlockCycle,createAirlockCycle} from '../candidate/airlock_cycle.mjs';
import {artificialMetadata,artificialOptions,fixture} from './artificial_fixture.mjs';

test('synthetic binding requires explicit sides and exact door/leaf/portal associations',()=>{
  for(const mutate of [
    (m,o)=>delete o.roleAssignment,
    (m,o)=>o.outsideDoorId=o.insideDoorId,
    m=>m.doors[0].leaf_node_id='demo:wrong-leaf',
    m=>m.doors[1].portal_id='demo:wrong-portal',
    m=>m.airlock_pairs[0].opening_policy.requires_peer='open',
    m=>m.rooms.push({...m.rooms[0]}),
  ]) {const m=artificialMetadata(),o=artificialOptions();mutate(m,o);assert.throws(()=>bindAirlockCycle(m,o),TypeError);}
  const f=fixture();assert.equal(f.binding.ports.outside.openAngle,-Math.PI/2);
});

test('a cloned binding is not an admitted component association',()=>{
  const f=fixture();assert.throws(()=>createAirlockCycle({binding:structuredClone(f.binding),
    runtimeIdentity:f.runtimeIdentity,readDoors:f.readDoors,toggleDoor:f.toggleDoor}),/exact binding/);
});

test('geometric closure alone does not acknowledge fictional seals or establish pressure',()=>{
  const f=fixture();assert.equal(f.cycle.snapshot().simulatedPressure,'unknown');
  assert.equal(f.cycle.begin('habitat').ok,false);assert.equal(f.cycle.open('inside').ok,false);
  assert.ok(f.seal().every(r=>r.ok));assert.equal(f.cycle.snapshot().simulatedPressure,'unknown');
});

test('completed symbolic cycle permits only its side and delegates normal door commands',()=>{
  const f=fixture();f.seal();const token=f.cycle.begin('habitat').token;
  assert.equal(f.finish(token).complete,true);assert.equal(f.cycle.open('outside').ok,false);
  assert.equal(f.cycle.open('inside').ok,true);assert.deepEqual(f.controls.commands,['demo:inner']);
  assert.equal(f.cycle.snapshot().simulatedSealAcknowledged.inside,false);
  assert.equal(f.cycle.close('inside').ok,false); // Mock still reports motion.
  f.settle('inside');assert.equal(f.cycle.close('inside').ok,true);f.settle('inside');
  assert.equal(f.cycle.begin('mars').ok,false);f.seal();
  assert.equal(f.finish(f.cycle.begin('mars').token).complete,true);
  assert.equal(f.cycle.open('outside').ok,true);f.settle('outside');
  assert.equal(f.doors[1].angle,-Math.PI/2);assert.equal(f.cycle.open('inside').ok,false);
});

test('pause retains progress, revokes token, and requires a fresh explicit resume',()=>{
  const f=fixture();f.seal();const old=f.cycle.begin('mars').token;
  f.cycle.advance(old,.25);assert.equal(f.cycle.pause().ok,true);
  const reads=f.controls.reads;assert.equal(f.cycle.advance(old,.25).ok,false);assert.equal(f.controls.reads,reads);
  assert.equal(f.cycle.snapshot().elapsedSeconds,.25);assert.equal(f.cycle.open('inside').ok,false);
  const next=f.cycle.resume().token;assert.notEqual(next,old);assert.equal(f.cycle.advance(old,.25).ok,false);
  assert.equal(f.cycle.advance(next,.25).ok,true);assert.equal(f.cycle.snapshot().elapsedSeconds,.5);
});

test('cancel loses progress and symbolic pressure, and cannot revive old callbacks',()=>{
  const f=fixture();f.seal();const old=f.cycle.begin('mars').token;f.cycle.advance(old,.25);
  assert.equal(f.cycle.cancel().ok,true);const s=f.cycle.snapshot();
  assert.equal(s.elapsedSeconds,0);assert.equal(s.simulatedPressure,'unknown');assert.equal(s.target,null);
  assert.equal(f.cycle.resume().ok,false);assert.equal(f.cycle.advance(old,.25).ok,false);
  const next=f.cycle.begin('mars').token;assert.notEqual(next,old);assert.equal(f.cycle.snapshot().elapsedSeconds,0);
});

test('invalid active time never silently completes a cycle',()=>{
  const f=fixture();f.seal();const token=f.cycle.begin('mars').token;
  for(const dt of [-.001,.251,NaN,Infinity,'0.25']) assert.throws(()=>f.cycle.advance(token,dt),/bounded active-time/);
  assert.equal(f.cycle.snapshot().elapsedSeconds,0);assert.equal(f.cycle.advance(token,0).ok,true);
});

test('unexpected door motion or motion hold faults a running cycle',()=>{
  for(const mutate of [d=>d.moving=true,d=>d.motionHeld=true,d=>d.target=Math.PI/2]) {
    const f=fixture();f.seal();const token=f.cycle.begin('habitat').token;mutate(f.doors[0]);
    assert.equal(f.cycle.advance(token,.25).ok,false);const s=f.cycle.snapshot();
    assert.equal(s.phase,'fault');assert.equal(s.simulatedPressure,'unknown');
    assert.deepEqual(s.simulatedSealAcknowledged,{inside:false,outside:false});
  }
});

test('changed runtime instance or byte identities invalidate even a same-scene session',()=>{
  for(const patch of [v=>({...v,runtimeIdentity:{}}),v=>({...v,manifestSha256:'c'.repeat(64)}),
    v=>({...v,sceneSha256:'d'.repeat(64)}),v=>({...v,sceneId:'demo:replacement'})]) {
    const f=fixture();f.seal();const token=f.cycle.begin('mars').token;f.controls.readPatch=patch;
    assert.equal(f.cycle.advance(token,.25).ok,false);assert.equal(f.cycle.snapshot().phase,'fault');
    assert.equal(f.controls.commands.length,0);
  }
});

test('missing, duplicate or invalid observed poses fail closed',()=>{
  for(const patch of [v=>({...v,doors:[v.doors[0]]}),v=>({...v,doors:[v.doors[0],v.doors[0]]}),
    v=>({...v,doors:v.doors.map((d,i)=>i?d:{...d,angle:-.1})}),
    v=>({...v,doors:v.doors.map((d,i)=>i?d:{...d,moving:'false'})})]) {
    const f=fixture();f.controls.readPatch=patch;assert.equal(f.cycle.snapshot().phase,'fault');
    assert.equal(f.cycle.begin('habitat').ok,false);
  }
});

test('synchronous command refusal is preserved without inventing a successful door movement',()=>{
  const f=fixture();f.seal();f.finish(f.cycle.begin('habitat').token);
  f.controls.command=()=>({ok:false,reason:'artificial occupied-swing refusal'});
  assert.deepEqual(f.cycle.open('inside'),{ok:false,reason:'artificial occupied-swing refusal'});
  assert.equal(f.doors[0].target,0); // This does not test the real collision runtime.
});

test('unknown, asynchronous or unobserved command success faults instead of claiming opening',()=>{
  for(const command of [()=>undefined,()=>Promise.resolve({ok:true}),()=>({ok:true}),()=>{throw new Error('mock failure');}]) {
    const f=fixture();f.seal();f.finish(f.cycle.begin('habitat').token);f.controls.command=command;
    assert.equal(f.cycle.open('inside').ok,false);assert.equal(f.cycle.snapshot().phase,'fault');
    assert.equal(f.cycle.snapshot().simulatedPressure,'unknown');
  }
});

test('asynchronous observations and callback reentry cannot advance state',()=>{
  const f=fixture();f.controls.readPatch=v=>Promise.resolve(v);
  assert.equal(f.cycle.snapshot().phase,'fault');
  f.controls.readPatch=()=>f.cycle.begin('habitat');
  const s=f.cycle.snapshot();assert.equal(s.phase,'fault');assert.match(s.reason,/Reentrant/);
});

test('observation failure retains last poses only as stale display data (documented advisory)',()=>{
  const f=fixture();const before=f.cycle.snapshot().doors;f.controls.readFailure='artificial observation unavailable';
  const after=f.cycle.snapshot();assert.equal(after.phase,'fault');assert.equal(after.simulatedPressure,'unknown');
  assert.deepEqual(after.doors,before);assert.match(after.reason,/unavailable/);
  assert.equal(f.cycle.open('inside').ok,false);assert.equal(f.cycle.begin('habitat').ok,false);
  // A host must mark this stale/unavailable. This assertion does not endorse a live display.
});

test('foreign tokens and disposed callbacks cannot read or command captured runtime',()=>{
  const f=fixture(),other=fixture();f.seal();other.seal();const old=f.cycle.begin('mars').token;
  const foreign=other.cycle.begin('mars').token;let reads=f.controls.reads;
  assert.equal(f.cycle.advance(foreign,.25).ok,false);assert.equal(f.controls.reads,reads);
  f.cycle.dispose();f.cycle.dispose();reads=f.controls.reads;
  assert.equal(f.cycle.advance(old,.25).ok,false);assert.equal(f.cycle.open('outside').ok,false);
  assert.equal(f.cycle.snapshot().phase,'disposed');assert.equal(f.controls.reads,reads);
  assert.deepEqual(f.controls.commands,[]);
});

test('snapshot cannot mutate future state and keeps fictional capability labels',()=>{
  const f=fixture();const s=f.cycle.snapshot();assert.throws(()=>s.doors.inside.angle=1,TypeError);
  assert.throws(()=>s.binding.ports.inside.doorId='demo:wrong',TypeError);
  assert.equal(s.capabilities.fictionalStateOnly,true);assert.equal(s.capabilities.pressurePhysics,false);
  assert.equal(s.capabilities.liveTelemetry,false);assert.equal(f.cycle.snapshot().doors.inside.angle,0);
});
