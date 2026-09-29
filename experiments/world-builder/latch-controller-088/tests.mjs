import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createDoorSystem as producer,createWalkController} from './candidate/producer/walk_controller.mjs';
import {createDoorSystem as oldProducer} from './before/producer/walk_controller.mjs';
import {createDoorRuntime as consumer,validateMetadata} from './candidate/consumer/runtime.mjs';
import {createDoorRuntime as oldConsumer,validateMetadata as oldValidate} from './before/consumer/runtime.mjs';
import {exportSceneMetadata} from '../world-room-monitors-073/candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {createLatchAuthority} from './candidate/shared/latch_state.mjs';
import {describeLatchedDoor} from './candidate/shared/latched_metadata.mjs';
import {buildRoomDressing} from '../world-room-monitors-073/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';

function geometry(axis='x',sign=1){
 const n=axis==='x'?'x':'z',t=axis==='x'?'z':'x';
 const room=(id,v)=>({id,name:id,[n]:v,[t]:0,width:4,depth:4,height:3,floor_y:0,access:'walkable_layout'});
 const rooms=sign>0?[room('a',0),room('b',-4),room('c',4),room('d',8),room('e',12)]:[room('a',-4),room('b',0),room('c',-8),room('d',-12),room('e',-16)];
 const p=(id,a,b,c)=>({id,room_a:a,room_b:b,axis,coordinate:c,center:2,width:1.2,height:2.2,state:'open_passage'});
 return {contract:'compiled_blueprint_geometry_v1',units:'meters',rooms,portals:[p('one','a','b',0),p('two','a','c',sign*4),p('three','c','d',sign*8),p('four','d','e',sign*12)],primitives:[],colliders:[],functional_program:{a:'airlock'},connectivity:{entry_room_id:'e'},
  support_surfaces:rooms.map(r=>({id:'floor_'+r.id,min_x:r.x,max_x:r.x+r.width,min_z:r.z,max_z:r.z+r.depth,y:0})),routes:[]};
}
const emptyDressing={contract:'authored_habitat_equipment_plan_v1',objects:[],architecture:[],signs:[],colliders:[]};
function metadata(g,v2=true){
 const old=oldProducer(g),m=structuredClone(exportSceneMetadata(g,emptyDressing,old.definitions(),{sceneId:'inert_fixture',sourceDigests:{geometry:'a'.repeat(64),dressing_recipe:'b'.repeat(64),door_controller:'c'.repeat(64)},doorInterlocks:old.interlocks()}));
 if(v2)for(const d of [...m.doors].filter(d=>d.variant)){
  const projected=describeLatchedDoor(g,d.portal_id),ids=new Set([...d.frame_node_ids,...d.kinematic_node_ids]);
  m.nodes=m.nodes.filter(n=>!ids.has(n.id)).concat(projected.nodes);m.colliders=m.colliders.filter(c=>!ids.has(c.owner_node_id)).concat(projected.colliders);
  m.doors[m.doors.findIndex(x=>x.id===d.id)]=projected.door;
 }
 return m;
}
function harness(kind,{axis='x',sign=1}={}){
 const g=geometry(axis,sign);let current=true;
 const runtime=kind==='producer'?producer(g,{hatchVariant:'latched_v2',isCurrent:()=>current}):consumer(metadata(g),{isCurrent:()=>current});
 const id=n=>kind==='producer'?n:'door:'+n;
 const feet=(portal='one')=>{const p=g.portals.find(p=>p.id===portal),a=g.rooms.find(r=>r.id===p.room_a),n=axis==='x'?0:2,t=n===0?2:0,side=Math.sign(a[axis]+a[axis==='x'?'width':'depth']/2-p.coordinate),v=[0,0,0];v[n]=p.coordinate+side*2;v[t]=2;return v;};
 const tick=(count=16,pos=feet())=>{for(let i=0;i<count;i++)runtime.advance(.05,pos);};
 return {g,runtime,id,feet,tick,pose:n=>runtime.all().find(d=>d.id===id(n)),latch:n=>runtime.latchStates().find(d=>d.id===id(n)),stale(){current=false;},restore(){current=true;}};
}
for(const kind of ['producer','consumer']){
 test(kind+': actual low-level toggle cannot bypass engaged or releasing hardware',()=>{
  const h=harness(kind),{runtime:r,id,feet,tick}=h;assert.equal(r.requestLatch(id('one'),true,feet()).ok,true);tick();assert.equal(h.latch('one').fraction,1);
  assert.equal(r.toggle(id('one'),feet()).ok,false);assert.equal(h.pose('one').angle,0);
  assert.equal(r.requestLatch(id('one'),false,feet()).ok,true);tick(8);assert.equal(h.latch('one').fraction,.5);assert.equal(r.toggle(id('one'),feet()).ok,false);tick(8);
  assert.equal(r.toggle(id('one'),feet()).ok,true);assert.equal(h.pose('one').angle,0);assert.equal(r.requestLatch(id('one'),true,feet()).ok,false);tick();assert.notEqual(h.pose('one').angle,0);assert.equal(r.requestLatch(id('one'),true,feet()).ok,false);
  assert.equal(r.requestLatch(undefined,true,feet()).ok,false);assert.equal(r.requestLatch(id('three'),true,feet('three')).ok,false);
 });
 test(kind+': release-before-open commits once and rechecks peer/swing/position',()=>{
  const h=harness(kind),{runtime:r,id,feet,tick}=h;r.requestLatch(id('one'),true,feet());tick();r.releaseAndOpen(id('one'),feet());tick();assert.equal(h.pose('one').state,'opening');
  tick(30);const settled=h.pose('one').angle;tick(30);assert.equal(h.pose('one').angle,settled);assert.equal(h.latch('one').pendingOpen,false);
  assert.equal(r.toggle(id('two'),feet('two')).ok,false);assert.equal(r.requestLatch(id('one'),true,feet()).ok,false);
  const other=harness(kind);other.runtime.requestLatch(other.id('one'),true,other.feet());other.tick();other.runtime.releaseAndOpen(other.id('one'),other.feet());
  const insideSwing=[...other.feet()];insideSwing[0]=.5;other.tick(16,insideSwing);assert.equal(other.pose('one').angle,0);assert.equal(other.latch('one').lastOpenResult.ok,false);
  other.tick(20);assert.equal(other.pose('one').angle,0,'Failed completion must not replay');
  const away=harness(kind);away.runtime.requestLatch(away.id('one'),true,away.feet());away.tick();away.runtime.releaseAndOpen(away.id('one'),away.feet());away.tick(16,[14,0,2]);assert.equal(away.pose('one').angle,0);assert.equal(away.latch('one').lastOpenResult.ok,false);
  const race=harness(kind);race.runtime.requestLatch(race.id('one'),true,race.feet());race.tick();race.runtime.releaseAndOpen(race.id('one'),race.feet());assert.equal(race.runtime.toggle(race.id('two'),race.feet('two')).ok,true);race.tick();assert.equal(race.pose('one').angle,0);assert.equal(race.latch('one').lastOpenResult.ok,false);
 });
 test(kind+': pause, stale session and dispose revoke pending opening',()=>{
  const h=harness(kind),{runtime:r,id,feet,tick}=h;r.requestLatch(id('one'),true,feet());tick();r.releaseAndOpen(id('one'),feet());tick(4);const fraction=h.latch('one').fraction;
  r.pauseLatches('hidden');r.pauseLatches('manual');tick(8);assert.equal(h.latch('one').fraction,fraction);assert.equal(h.latch('one').pendingOpen,false);
  r.resumeLatches('hidden');tick(8);assert.equal(h.latch('one').fraction,fraction);r.resumeLatches('manual');tick(20);assert.equal(h.pose('one').angle,0);assert.equal(h.latch('one').fraction,0);
  r.releaseAndOpen(id('one'),feet());h.stale();tick(20);h.restore();tick(20);assert.equal(h.pose('one').angle,0);assert.equal(r.toggle(id('one'),feet()).ok,false);assert.equal(h.latch('one').state,'disposed');
  r.dispose();assert.equal(r.requestLatch(id('one'),true,feet()).ok,false);assert.equal(r.releaseAndOpen(id('one'),feet()).ok,false);
 });
 test(kind+': four orientations preserve conservative ownership and peer reservations',()=>{
  for(const axis of ['x','z'])for(const sign of [-1,1]){
   const h=harness(kind,{axis,sign}),r=h.runtime;assert.equal(r.requestLatch(h.id('one'),true,h.feet()).ok,true);h.tick();assert.equal(h.latch('one').fraction,1);
   assert.equal(r.releaseAndOpen(h.id('one'),h.feet()).ok,true);h.tick();assert.equal(h.pose('one').state,'opening');
   assert.equal(r.toggle(h.id('two'),h.feet('two')).ok,false);h.tick(30);assert.equal(h.pose('one').state,'open');
   assert.equal(r.toggle(h.id('one'),h.feet()).ok,true);h.tick(30);assert.equal(h.pose('one').state,'closed');
  }
 });
}
test('strict descriptor rejects bounds/recipe/owner/room/part tampering and old validator rejects new variant',()=>{
 assert.throws(()=>describeLatchedDoor({...geometry(),units:'inches'},'one'),/meter-based/);
 const m=metadata(geometry());assert.equal(validateMetadata(m).doors.size,4);assert.throws(()=>oldValidate(m),/Unsupported door variant/);
 for(const change of [m=>m.doors[0].latch.duration_seconds=.1,m=>m.doors[0].authoring.input.rooms[0].width=9,m=>m.doors[0].swing_bounds.max[0]+=.01,m=>m.nodes.find(n=>n.hatch_part_id?.includes('latch_v2_bolt')).representation.parameters.representation.stroke+=.01,m=>m.colliders.find(c=>c.proxy.includes('latched')).bounds.min[0]-=.01,m=>m.rooms[0].bounds.max[0]+=1,m=>m.nodes.push({...structuredClone(m.nodes.find(n=>n.hatch_part_id?.includes('latch_v2_bolt'))),id:'node:extra',hatch_part_id:'hatch_one_extra'})]){
  const bad=structuredClone(m);change(bad);assert.throws(()=>validateMetadata(bad));
 }
});
test('actual073 paired placements retain source bytes and admit both conservative v2 swings',()=>{
 const locator=JSON.parse(readFileSync(new URL('../world-room-monitors-preview-073/PREVIEW.json',import.meta.url))),manifestBytes=readFileSync(locator.manifest_path);
 assert.equal(createHash('sha256').update(manifestBytes).digest('hex'),locator.manifest_sha256);
 const pin=JSON.parse(manifestBytes).inputs.geometry_source,raw=readFileSync(pin.path);assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);
 const g=JSON.parse(raw),before=JSON.stringify(g),r=producer(g,{hatchVariant:'latched_v2'}),defs=r.definitions().filter(d=>d.variant);
 assert.equal(defs.length,2);for(const d of defs)assert.deepEqual(d.latchMetadata,describeLatchedDoor(g,d.id));
 const dressing=buildRoomDressing(g,producer(g,{hatchGeometry:false}).assemblies());createWalkController(g,{extraColliders:dressing.colliders,hatchVariant:'latched_v2'});
 const m=JSON.parse(readFileSync(new URL('../world-package-consumer-083/candidate/sample-package/scene.json',import.meta.url)));
 for(const def of defs){const old=m.doors.find(d=>d.portal_id===def.id),ids=new Set([...old.frame_node_ids,...old.kinematic_node_ids]),v=def.latchMetadata;m.nodes=m.nodes.filter(n=>!ids.has(n.id)).concat(v.nodes);m.colliders=m.colliders.filter(c=>!ids.has(c.owner_node_id)).concat(v.colliders);m.doors[m.doors.indexOf(old)]=v.door;}
 assert.equal(validateMetadata(m).doors.size,7);assert.equal(consumer(m).latchStates().length,2);
 assert.equal(JSON.stringify(g),before);assert.deepEqual(readFileSync(pin.path),raw);
});
test('ordinary and v1 default source controllers remain byte-equivalent in state and definitions',()=>{
 const g=geometry(),a=producer(g),b=oldProducer(g);assert.deepEqual(a.definitions(),b.definitions());assert.deepEqual(a.colliders(),b.colliders());
 const feet=[10,0,2];assert.deepEqual(a.toggle('three',feet),b.toggle('three',feet));for(let i=0;i<25;i++)assert.deepEqual(a.advance(.05,feet),b.advance(.05,feet));
 assert.deepEqual(a.toggle('three',feet),b.toggle('three',feet));for(let i=0;i<25;i++)assert.deepEqual(a.advance(.05,feet),b.advance(.05,feet));
 const m=metadata(g,false),c=consumer(m),d=oldConsumer(m);assert.deepEqual(c.toggle('door:three',feet),d.toggle('door:three',feet));for(let i=0;i<25;i++)assert.deepEqual(c.advance(.05,feet),d.advance(.05,feet));
});
test('both existing exact package metadata inputs still validate with no v2 behavior',()=>{
 const fixtures=[['../world-package-consumer-083/candidate/sample-package/','bf7f0934f473b5ad7b0a50f2577c50995f94d3880db30835b4bf0194bdd074cc'],['../world-package-consumer-043/sample-package/','9ca7416c9e6b45d23b009cf070964ca56462b60392520370cd525a90df01c40e']];
 for(const [path,hash] of fixtures){
  const bytes=readFileSync(new URL(path+'manifest.json',import.meta.url));assert.equal(createHash('sha256').update(bytes).digest('hex'),hash);
  const manifest=JSON.parse(bytes),scene=readFileSync(new URL(path+'scene.json',import.meta.url));assert.equal(createHash('sha256').update(scene).digest('hex'),manifest.files['scene.json'].sha256);
  const m=JSON.parse(scene);assert.equal(validateMetadata(m).doors.size,oldValidate(m).doors.size);
  const a=consumer(m),b=oldConsumer(m);assert.deepEqual(a.all(),b.all());assert.deepEqual(a.latchStates(),[]);
 }
});
test('pure authority enforces exact stopped pose, finite time and lifecycle reentry',()=>{
 const pose={id:'one',angle:0,target:0,moving:false,motionHeld:false};let h;
 h=createLatchAuthority({id:'one',openAngle:Math.PI/2,readDoor:()=>pose});
 pose.target=Math.PI/2;assert.equal(h.request(true).ok,false);pose.target=0;pose.motionHeld=true;assert.equal(h.request(true).ok,false);pose.motionHeld=false;
 assert.equal(h.request(true).ok,true);assert.throws(()=>h.advance(NaN));assert.throws(()=>h.advance(.051));h.advance(.05);assert.equal(h.canMove().ok,false);
 let reenter=false;const stale=createLatchAuthority({id:'one',openAngle:Math.PI/2,readDoor:()=>{if(reenter)stale.dispose();return pose;}});reenter=true;assert.equal(stale.request(true).ok,false);assert.equal(stale.snapshot().state,'disposed');
});
