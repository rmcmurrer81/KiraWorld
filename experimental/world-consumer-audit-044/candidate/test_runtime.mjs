import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createDoorRuntime,createRuntime,validateMetadata} from './runtime.mjs';
import {verifyPackage,PACKAGE_FILES} from './package_loader.mjs';
const H=path.dirname(fileURLToPath(import.meta.url)),P=path.join(H,'sample-package');
const files=new Map(PACKAGE_FILES.map(n=>[n,new Uint8Array(fs.readFileSync(path.join(P,n)))]));
const verified=await verifyPackage(files),m=verified.metadata;
let count=0;const cases=[];
async function test(name,fn){await fn();cases.push(name);count++;}
const clone=()=>structuredClone(m),close=(a,b)=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<1e-7);
const safeFeet=d=>{const mid=d.hinge.position.map((v,i)=>v+d.hinge.leaf_local_center[i]),leaf=m.nodes.find(n=>n.id===d.leaf_node_id),axis=leaf.representation.size[0]===.065?0:2;
 for(const sign of [-1,1]){const feet=[...mid];feet[1]=0;feet[axis]+=sign*1.05;
  if(!(feet[axis]+.34>=d.swing_bounds.min[axis]&&feet[axis]-.34<=d.swing_bounds.max[axis]))return feet;}throw Error('No safe interaction side');};
const allClosed=()=>{const r=createDoorRuntime(m);return r;};
await test('all five package files verified before import',()=>assert.equal(verified.manifestSha256,'9ca7416c9e6b45d23b009cf070964ca56462b60392520370cd525a90df01c40e'));
await test('missing file held',()=>{const f=new Map(files);f.delete('scene.glb');return assert.rejects(()=>verifyPackage(f),/five files/);});
await test('tampered GLB held by digest',()=>{const f=new Map(files),b=new Uint8Array(f.get('scene.glb'));b[b.length-1]^=1;f.set('scene.glb',b);return assert.rejects(()=>verifyPackage(f),/hash mismatch/);});
await test('unsupported metadata contract held',()=>{const c=clone();c.contract='unknown';assert.throws(()=>validateMetadata(c),/contract/);});
await test('unknown collider owner held',()=>{const c=clone();c.colliders[0].owner_node_id='node:missing';assert.throws(()=>validateMetadata(c),/owner/);});
await test('missing authored pair held',()=>{const c=clone();c.airlock_pairs=[];assert.throws(()=>validateMetadata(c),/pairing/);});
await test('swapped pair leaf held',()=>{const c=clone();c.airlock_pairs[0].leaf_node_ids.reverse();assert.throws(()=>validateMetadata(c),/associations/);});
await test('unlisted paired door held',()=>{const c=clone();c.doors[0].interlock_pair_ids=[];assert.throws(()=>validateMetadata(c),/pairing/);});
await test('changed leaf collision bounds held',()=>{const c=clone();c.colliders.find(x=>x.motion==='kinematic').bounds.max[0]+=.1;assert.throws(()=>validateMetadata(c),/bounds mismatch/);});
await test('unsupported spawn held',()=>{const c=clone();c.navigation.spawn_feet[1]=.1;assert.throws(()=>validateMetadata(c),/spawn/);});
const samples=[];
await test('six doors closed half and fully open; all frames remain metadata-static',()=>{
 const r=allClosed();for(const d of m.doors){const feet=safeFeet(d),before=JSON.stringify(m.nodes.filter(n=>d.frame_node_ids.includes(n.id)));assert.ok(r.toggle(d.id,feet).ok);
  for(let i=0;i<4;i++)r.advance(.05,feet);const half=r.all().find(s=>s.id===d.id);assert.ok(Math.abs(half.angle-d.hinge.open_angle/2)<1e-8);
  for(let i=0;i<4;i++)r.advance(.05,feet);const full=r.all().find(s=>s.id===d.id);assert.equal(full.angle,d.hinge.open_angle);assert.equal(full.state,'open');
  assert.equal(JSON.stringify(m.nodes.filter(n=>d.frame_node_ids.includes(n.id))),before);samples.push({door_id:d.id,half:half.center,open:full.center});
  assert.ok(r.toggle(d.id,feet).ok);for(let i=0;i<8;i++)r.advance(.05,feet);assert.equal(r.all().find(s=>s.id===d.id).state,'closed');
 }
});
await test('peer pending at zero angle denies simultaneous opening',()=>{const r=allClosed(),[a,b]=m.airlock_pairs[0].door_ids.map(id=>m.doors.find(d=>d.id===id));assert.ok(r.toggle(a.id,safeFeet(a)).ok);const result=r.toggle(b.id,safeFeet(b));assert.equal(result.ok,false);assert.equal(result.interlock.peerDoorId,a.id);assert.equal(r.all().find(s=>s.id===a.id).angle,0);});
await test('occupied swing holds zero-angle motion and keeps peer reserved',()=>{const r=allClosed(),[a,b]=m.airlock_pairs[0].door_ids.map(id=>m.doors.find(d=>d.id===id));assert.ok(r.toggle(a.id,safeFeet(a)).ok);const occupied=a.swing_bounds.min.map((v,i)=>i===1?0:(v+a.swing_bounds.max[i])/2);r.advance(.05,occupied);const s=r.all().find(s=>s.id===a.id);assert.equal(s.angle,0);assert.equal(s.motionHeld,true);assert.equal(r.toggle(b.id,safeFeet(b)).ok,false);});
await test('closing allowed with peer fully closed; then peer opens',()=>{const r=allClosed(),[a,b]=m.airlock_pairs[0].door_ids.map(id=>m.doors.find(d=>d.id===id));const p=safeFeet(a);assert.ok(r.toggle(a.id,p).ok);for(let i=0;i<8;i++)r.advance(.05,p);assert.ok(!r.toggle(b.id,safeFeet(b)).ok);assert.ok(r.toggle(a.id,p).ok);for(let i=0;i<8;i++)r.advance(.05,p);assert.ok(r.toggle(b.id,safeFeet(b)).ok);});
await test('reach, moving and swing occupancy requests rejected',()=>{const r=allClosed(),d=m.doors[0];assert.equal(r.toggle(d.id,[999,0,999]).ok,false);const occupied=d.swing_bounds.min.map((v,i)=>i===1?0:(v+d.swing_bounds.max[i])/2);assert.match(r.toggle(d.id,occupied).reason,/Step back/);assert.ok(r.toggle(d.id,safeFeet(d)).ok);assert.match(r.toggle(d.id,safeFeet(d)).reason,/finish moving/);});
await test('no direct teleport setter and long frame is bounded',()=>{const r=createRuntime(m),p=r.snapshot().feet;r.step(10,{forward:true});assert.ok(Math.hypot(...r.snapshot().feet.map((v,i)=>v-p[i]))<=.1100001);assert.equal(r.teleport,undefined);assert.throws(()=>r.step(-1),/elapsed/);});
await test('closed door blocks continuous route; open door allows passage',()=>{const r=createRuntime(m),a=m.doors[0],middle=a.hinge.position.map((v,i)=>i===1?0:v+a.hinge.leaf_local_center[i]);assert.equal(r.checkRoute([middle[0],0,middle[2]-1],[middle[0],0,middle[2]+1]).status,'blocked');
 // Walk from the actual entry toward its first door, stop outside the swing,
 // then open and traverse using only ordinary step/toggle intents.
 for(let i=0;i<8;i++)r.step(.05,{forward:true});assert.ok(r.toggleDoor(a.id).ok);for(let i=0;i<8;i++)r.step(.05);
 assert.equal(r.checkRoute([middle[0],0,middle[2]-1],[middle[0],0,middle[2]+1]).status,'clear');
 for(let i=0;i<32;i++)r.step(.05,{forward:true});assert.equal(r.snapshot().roomId,'room:airlock');assert.ok(r.snapshot().feet[2]>-4);
 assert.ok(r.toggleDoor(a.id).ok);for(let i=0;i<8;i++)r.step(.05);assert.equal(r.doorStates().find(s=>s.id===a.id).state,'closed');
 for(let i=0;i<2;i++)r.step(.05,{forward:true});assert.ok(r.toggleDoor(m.doors[1].id).ok);
});
await test('room wall and unsupported world edge block walking',()=>{const r=createRuntime(m);assert.equal(r.checkRoute(m.navigation.spawn_feet,[100,0,m.navigation.spawn_feet[2]]).status,'blocked');const room=m.rooms[0];assert.equal(r.checkRoute(m.navigation.spawn_feet,[room.bounds.min[0]-.1,0,m.navigation.spawn_feet[2]]).status,'blocked');});
await test('all 134 actual collider records accepted; second static chunk also checked',()=>{
 const baseline=createRuntime(m),a=[1.5,0,-6.5],b=[1.5,0,-5.9];assert.equal(baseline.checkRoute(a,b).status,'clear');assert.equal(m.colliders.length,134);
 const c=clone();c.nodes.push({id:'node:synthetic_late_obstruction',kind:'synthetic_test_box'});
 c.colliders.push({id:'collider:synthetic_late_obstruction',owner_node_id:'node:synthetic_late_obstruction',motion:'static',shape:'axis_aligned_box',bounds:{min:[1.4,0,-6.05],max:[1.6,1,-5.95]}});
 assert.equal(c.colliders.filter(x=>x.motion==='static').length,129);assert.equal(createRuntime(c).checkRoute(a,b).status,'blocked');
});
await test('metadata remains byte-identical after session actions',()=>assert.deepEqual(m,JSON.parse(fs.readFileSync(path.join(P,'scene.json'),'utf8'))));
const result={status:'PORTABLE_CONSUMER_CPU_RUNTIME_PASS',tests:count,cases,door_pose_samples:samples,source_geometry_used:false,webgl_browser_gpu_model_calls:0,native_ui_review:false,owner_approval:false};
const output=process.argv[2];if(output)fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:result.status,tests:count}));
