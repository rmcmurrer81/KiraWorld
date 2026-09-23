// Optional local equivalence check. These explicit source paths are used only by
// this engineering test; the consumer and its shipped sample need neither.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {createDoorRuntime,createRuntime} from './runtime.mjs';
const [enginePath,geometryPath,output]=process.argv.slice(2);assert.ok(enginePath&&geometryPath&&output);
const geometry=JSON.parse(fs.readFileSync(geometryPath,'utf8'));
const {createDoorSystem,createWalkController}=await import(pathToFileURL(path.join(enginePath,'walk_controller.mjs')));
const {buildRoomDressing}=await import(pathToFileURL(path.join(enginePath,'layout_package_assets/source/room_dressing_plan.mjs')));
const H=path.dirname(fileURLToPath(import.meta.url)),m=JSON.parse(fs.readFileSync(path.join(H,'sample-package/scene.json'),'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert.equal(hash(geometryPath),m.provenance.source_digests.geometry);
const sourceDoor=createDoorSystem(geometry),portableDoor=createDoorRuntime(m);let comparisons=0,maxDelta=0;
function close(a,b){assert.equal(a.length,b.length);a.forEach((v,i)=>{maxDelta=Math.max(maxDelta,Math.abs(v-b[i]));assert.ok(Math.abs(v-b[i])<1e-12);});}
function compareDoors(a,b){assert.equal(a.length,b.length);for(let i=0;i<a.length;i++){assert.equal('door:'+a[i].id,b[i].id);assert.equal(a[i].state,b[i].state);assert.equal(a[i].motionHeld,b[i].motionHeld);close([a[i].angle,...a[i].center,...a[i].collider.min,...a[i].collider.max],[b[i].angle,...b[i].center,...b[i].collider.min,...b[i].collider.max]);comparisons++;}}
function safe(d){const p=geometry.portals.find(p=>p.id===d.portal_id),axis=p.axis==='x'?0:2,feet=[p.axis==='x'?p.coordinate:p.center,0,p.axis==='x'?p.center:p.coordinate];for(const sign of [-1,1]){const trial=[...feet];trial[axis]+=sign*1.05;if(!(trial[axis]+.34>=d.swing_bounds.min[axis]&&trial[axis]-.34<=d.swing_bounds.max[axis]))return trial;}throw Error('No safe point');}
for(const d of m.doors){const feet=safe(d);compareDoors(sourceDoor.all(),portableDoor.all());assert.equal(sourceDoor.toggle(d.portal_id,feet).ok,portableDoor.toggle(d.id,feet).ok);
 for(let i=0;i<8;i++){sourceDoor.advance(.05,feet);portableDoor.advance(.05,feet);compareDoors(sourceDoor.all(),portableDoor.all());}
 assert.equal(sourceDoor.toggle(d.portal_id,feet).ok,portableDoor.toggle(d.id,feet).ok);
 for(let i=0;i<8;i++){sourceDoor.advance(.05,feet);portableDoor.advance(.05,feet);compareDoors(sourceDoor.all(),portableDoor.all());}
}
const plan=buildRoomDressing(geometry,sourceDoor.assemblies()),reference=createWalkController(geometry,{extraColliders:plan.colliders}),consumer=createRuntime(m);let steps=0,toggles=0;
const history=[];
function compareWalk(){const a=reference.snapshot(),b=consumer.snapshot();close([...a.feet,a.yaw,a.pitch,a.distance],[...b.feet,b.yaw,b.pitch,b.distance]);assert.equal('room:'+a.roomId,b.roomId);assert.equal(!!a.blocked,!!b.blocked);compareDoors(reference.doorStates(),consumer.doorStates());history.push({feet:b.feet,room:b.roomId,blocked:b.blocked});}
function step(n,input={}){for(let i=0;i<n;i++){reference.step(.05,input);consumer.step(.05,input);steps++;compareWalk();}}
function toggle(portal){const a=reference.toggleDoor(portal),b=consumer.toggleDoor('door:'+portal);assert.equal(a.ok,b.ok);assert.ok(a.ok,JSON.stringify({a,b}));toggles++;compareWalk();}
compareWalk();step(30,{forward:true});assert.ok(consumer.snapshot().blocked);step(12,{backward:true});
toggle('opening_1');step(8);step(33,{forward:true});assert.equal(consumer.snapshot().roomId,'room:airlock');toggle('opening_1');step(8);
step(2,{forward:true});toggle('opening_2');step(8);step(29,{forward:true});assert.equal(consumer.snapshot().roomId,m.doors.find(d=>d.portal_id==='opening_2').room_ids.find(id=>id!=='room:airlock'));toggle('opening_2');step(8);
reference.look(300,-120);consumer.look(300,-120);compareWalk();step(40,{right:true});assert.ok(consumer.snapshot().blocked);
const result={status:'SOURCE_CONTROLLER_AND_PORTABLE_CONSUMER_EQUIVALENCE_PASS',
 source_geometry_sha256:hash(geometryPath),source_controller_sha256:hash(path.join(enginePath,'walk_controller.mjs')),
 portable_runtime_sha256:hash(path.join(H,'runtime.mjs')),door_pose_comparisons:comparisons,walk_steps:steps,successful_toggle_intents:toggles,
 maximum_numerical_difference:maxDelta,tolerance:1e-12,walk_history:history,
 source_only_used_for_reference_test:true,package_consumer_requires_source_geometry:false,installed_or_owner_data_changed:false,ui_gpu_model_calls:0};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:result.status,steps,maxDelta,comparisons}));
