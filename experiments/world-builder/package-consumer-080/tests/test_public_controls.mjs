// Portable tests use invented inert adapters, never a private exported world.
import test from 'node:test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {harness,flush} from './ui_harness.mjs';
import {createDoorMotionSequence,describeNearbyDoor,discreteAction} from '../candidate/discrete_controls.mjs';
import {HATCH} from '../candidate/door_metadata.mjs';
const root=fileURLToPath(new URL('../candidate/',import.meta.url));
async function loaded(){
 const h=await harness(root),pkg=h.packageValue('Synthetic test room');
 const step=pkg.runtime.step;pkg.runtime.step=(dt,input)=>{assert.equal(typeof dt,'number');assert.ok(Number.isFinite(dt)&&dt>=0&&dt<=.05);step(dt,input);};
 h.elements.files.files=['inert test input'];const p=h.elements.files.dispatch('change');await flush();h.loaded[0].resolve(pkg);await p;return {h,pkg};
}
async function start(h){await h.elements.enter.dispatch('click');await h.window.dispatch('keydown',{code:'KeyW'});}
test('walking first frame establishes its own baseline and later gaps remain bounded',async()=>{
 const {h}=await loaded();await start(h);await h.walk(20,5);assert.equal(h.metrics.steps[0].dt,0);
 await h.walk(40,25);assert.equal(h.metrics.steps[1].dt,.02);await h.walk(10000,9999);assert.equal(h.metrics.steps[2].dt,.05);await h.window.dispatch('pagehide');
});
test('reversed or invalid walking clocks pause without passing bad elapsed time',async()=>{
 for(const value of [4,NaN,Infinity,-1,'6']){const {h}=await loaded();await start(h);await h.walk(20,5);await h.walk(40,value);assert.equal(h.metrics.steps.length,1);assert.equal(h.metrics.scheduled.size,0);assert.equal(h.elements.pause.disabled,true);assert.match(h.elements.status.textContent,/animation clock was invalid/);await h.window.dispatch('pagehide');}
});
test('cancelled walking callback cannot join a new resumed loop',async()=>{
 const {h}=await loaded();await start(h);const stale=[...h.metrics.scheduled.values()][0];await h.elements.pause.dispatch('click');await start(h);const fresh=[...h.metrics.scheduled.values()][0];stale(200);assert.equal(h.metrics.steps.length,0);assert.equal(h.metrics.scheduled.size,1);assert.equal([...h.metrics.scheduled.values()][0],fresh);await h.walk(20,5);assert.equal(h.metrics.steps[0].dt,0);await h.window.dispatch('pagehide');
});
function door(){
 let clock=105,id=0;const tasks=new Map(),steps=[],done=[];const runtime={doorStates:()=>[{moving:true,motionHeld:false}],step:(dt,input)=>steps.push({dt,input})};
 const sequence=createDoorMotionSequence({requestFrame:fn=>{tasks.set(++id,fn);return id;},cancelFrame:id=>tasks.delete(id),now:()=>clock,onDone:x=>done.push(x.reason)});
 return {sequence,tasks,steps,done,start:()=>sequence.start(runtime),frame(now,time){clock=now;const pending=[...tasks.values()];tasks.clear();for(const fn of pending)fn(time);}};
}
test('door first frame may precede the click-time sample, later reversal stops it',()=>{
 const d=door();d.start();d.frame(110,100);assert.equal(d.steps[0].dt,0);assert.equal(d.sequence.isRunning(),true);d.frame(126,116);assert.equal(d.steps[1].dt,.016);assert.deepEqual(d.steps[1].input,{});d.frame(130,115);assert.equal(d.steps.length,2);assert.deepEqual(d.done,['interrupted']);assert.equal(d.tasks.size,0);
});
test('door animation retains both wall-clock and frame-count limits',()=>{
 const d=door();d.start();d.frame(2106,100);assert.equal(d.steps.length,0);assert.deepEqual(d.done,['interrupted']);
 const f=door();f.start();for(let n=0;n<121;n++)f.frame(110,100);assert.equal(f.steps.length,120);assert.deepEqual(f.done,['interrupted']);assert.equal(f.tasks.size,0);
});
test('cancelled door callback never advances an inert runtime',()=>{
 const d=door();d.start();const stale=[...d.tasks.values()][0];d.sequence.cancel();stale(100);assert.equal(d.steps.length,0);assert.equal(d.tasks.size,0);assert.equal(d.sequence.isRunning(),false);
});
test('door labels derive from the selected ID and connected room without retargeting',()=>{
 const metadata={rooms:[{id:'a',label:'Test lobby'},{id:'b',label:'Test workshop'}],doors:[{id:'test-hatch',variant:HATCH,room_ids:['a','b']}]};
 const near={id:'test-hatch',state:'closed',moving:false};
 assert.deepEqual(describeNearbyDoor(metadata,{roomId:'a',nearbyDoor:near}),{id:'test-hatch',target:'hatch to Test workshop',state:'closed',button:'Open hatch to Test workshop'});
 assert.equal(describeNearbyDoor(metadata,{roomId:'b',nearbyDoor:{...near,moving:true}}).button,'Continue hatch to Test lobby');assert.equal(describeNearbyDoor(metadata,{nearbyDoor:null}),null);
});
test('discrete steps use bounded slices and stop after the runtime reports obstruction',()=>{
 const steps=[];let blocked=null;const runtime={snapshot:()=>({blocked}),step(dt,input){steps.push({dt,input});if(steps.length===2)blocked='Synthetic barrier';}};
 const result=discreteAction(runtime,'forward');assert.equal(steps.length,2);assert.ok(steps.every(x=>x.dt<=.05&&x.input.forward));assert.equal(result.after.blocked,'Synthetic barrier');assert.throws(()=>discreteAction(runtime,'teleport'),/Unknown step control/);
});
