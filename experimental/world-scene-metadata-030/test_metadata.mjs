import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {createDoorSystem as oldDoorSystem,createWalkController as oldController} from './baseline/walk_controller.mjs';
import {buildRoomDressing} from './room_dressing_plan.mjs';
import {exportSceneMetadata,canonicalSceneMetadata,SCENE_METADATA_CONTRACT} from './candidate/tools/world_builder_engine/scene_metadata.mjs';
const geometry=JSON.parse(fs.readFileSync(new URL('./fixtures/synthetic_habitat.json',import.meta.url)));
const hash=path=>crypto.createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex');
const options={sceneId:'synthetic_habitat',sourceDigests:{geometry:hash('./fixtures/synthetic_habitat.json'),dressing_recipe:hash('./room_dressing_plan.mjs'),door_controller:hash('./candidate/tools/world_builder_engine/walk_controller.mjs')}};
const doors=createDoorSystem(geometry),plan=buildRoomDressing(geometry,doors.assemblies()),definitions=doors.definitions();
const initial=JSON.stringify({geometry,plan,definitions}),checks=[];
function test(name,fn){fn();checks.push(name);}
const make=(g=geometry,p=plan,d=definitions,o=options)=>exportSceneMetadata(g,p,d,o);
const scene=make();
test('Pure deterministic projection and JSON round trip preserve inputs',()=>{
 assert.equal(canonicalSceneMetadata(scene),canonicalSceneMetadata(make()));
 assert.equal(canonicalSceneMetadata(JSON.parse(canonicalSceneMetadata(scene))),canonicalSceneMetadata(scene));
 assert.equal(JSON.stringify({geometry,plan,definitions}),initial);
 assert.ok(Object.isFrozen(scene.nodes[0].transform.position));assert.equal(scene.contract,SCENE_METADATA_CONTRACT);
});
test('All source rooms, structural boxes, equipment and colliders remain represented',()=>{
 assert.equal(scene.rooms.length,geometry.rooms.length);assert.equal(scene.doors.length,6);
 assert.equal(scene.nodes.filter(n=>n.kind==='structural_primitive').length,geometry.primitives.length);
 const equipment=scene.nodes.filter(n=>n.behavior==='static_visual_equipment');assert.equal(equipment.length,16);
 assert.equal(new Set(equipment.map(n=>n.kind)).size,15);
 assert.equal(scene.colliders.length,geometry.colliders.length+plan.colliders.length+doors.colliders().length);
 for(const c of scene.colliders)if(c.owner_node_id)assert.ok(scene.nodes.some(n=>n.id===c.owner_node_id));
});
test('Equipment uses actual renderer base-centre transform and exact physical bounds',()=>{
 for(const o of plan.objects){const n=scene.nodes.find(n=>n.id==='node:'+o.id);
  assert.deepEqual(n.transform.position,[o.center[0],o.center[1]-o.localSize[1]/2,o.center[2]]);assert.equal(n.transform.rotation_y_radians,o.yaw);
  assert.deepEqual(n.bounds,o.bounds);assert.deepEqual(n.interactions,[]);assert.equal(n.representation.mesh_included,false);
 }
 for(const a of plan.architecture){const n=scene.nodes.find(n=>n.id==='node:'+a.id);assert.equal(n.transform.rotation_y_radians,0);assert.deepEqual(n.transform.position,a.center);assert.deepEqual(n.dimensions,a.size);}
});
test('Door metadata comes from core definitions and matches initial pose/colliders',()=>{
 for(const d of scene.doors){const raw=definitions.find(r=>'door:'+r.id===d.id),pose=doors.all().find(p=>p.id===raw.id);
  assert.deepEqual(d.hinge.position,raw.hinge);assert.deepEqual(d.room_ids,[`room:${raw.roomAId}`,`room:${raw.roomBId}`]);
  const leaf=scene.nodes.find(n=>n.id===d.leaf_node_id);assert.deepEqual(leaf.transform.position,pose.center);assert.deepEqual(leaf.representation.size,pose.size);
  const c=scene.colliders.find(c=>c.owner_node_id===d.leaf_node_id);assert.deepEqual(c.bounds,{min:pose.collider.min,max:pose.collider.max});
 }
});
test('Definition extension does not alter live door or walker behavior',()=>{
 const before=oldController(geometry,{extraColliders:plan.colliders}),after=createWalkController(geometry,{extraColliders:plan.colliders});
 for(let i=0;i<5;i++){before.step(.05,{forward:true});after.step(.05,{forward:true});assert.deepEqual(after.snapshot(),before.snapshot());}
 assert.deepEqual(after.toggleDoor(),before.toggleDoor());
 for(let i=0;i<40;i++){before.step(.05,i>9?{forward:true}:{});after.step(.05,i>9?{forward:true}:{});assert.deepEqual(after.snapshot(),before.snapshot());assert.deepEqual(after.doorStates(),before.doorStates());}
 assert.deepEqual(after.toggleDoor('opening_1'),before.toggleDoor('opening_1'));
 for(let i=0;i<10;i++){before.step(.05,{});after.step(.05,{});assert.deepEqual(after.doorStates(),before.doorStates());}
 const d=createDoorSystem(geometry),original=JSON.stringify(d.definitions());const feet=[1.5,0,-4.9];
 d.toggle('opening_1',feet);for(let i=0;i<10;i++)d.advance(.05,feet);assert.equal(JSON.stringify(d.definitions()),original);
});
test('Mesh materials, VR, pressure and persistence claims remain explicitly unsupported',()=>{
 for(const key of ['equipment_meshes','materials_or_textures','engine_adapter','vr_runtime','session_state_export'])assert.equal(scene.capabilities[key],false);
 assert.ok(scene.doors.every(d=>d.pressure_simulation===false&&d.state_persistence==='session_local'&&d.initial_state==='closed'));
 assert.equal(scene.provenance.binding_verification,'caller_supplied_not_independently_verified');
});
test('Only projected source fields cross the export boundary',()=>{
 const g=structuredClone(geometry);g.private_notes='Never export this';g.research_packet_path='C:/owner/private.json';g.rooms[0].memory='Private biography';
 const text=canonicalSceneMetadata(make(g));assert.ok(!text.includes('Never export')&&!text.includes('private.json')&&!text.includes('Private biography'));
 const bad={...options,sourceDigests:{...options.sourceDigests,path:'secret'}};assert.throws(()=>make(geometry,plan,definitions,bad),/Only geometry/);
 g.rooms[0].name='C:/owner/private';assert.throws(()=>make(g),/label|path/);
});
test('Duplicate ids and bad room/collider ownership are rejected',()=>{
 const g=structuredClone(geometry);g.rooms.push(g.rooms[0]);assert.throws(()=>make(g),/Duplicate/);
 const p=structuredClone(plan);p.objects[0].room_id='missing';assert.throws(()=>make(geometry,p),/Equipment/);
 const q=structuredClone(plan);q.colliders[0].min[0]+=.03;assert.throws(()=>make(geometry,q),/collider/);
 const r=structuredClone(plan);r.colliders.pop();assert.throws(()=>make(geometry,r),/Missing/);
});
test('Altered hinges, pivots, portal associations and missing definitions fail',()=>{
 for(const change of [d=>d[0].hinge[0]+=.2,d=>d[0].leafLocalCenter[1]+=.2,d=>d[0].roomAId='habitat',d=>d.pop()]){
  const d=structuredClone(definitions);change(d);assert.throws(()=>make(geometry,plan,d),/Door/);
 }
});
test('Nonfinite, sparse and oversized source data and unknown contracts fail',()=>{
 const g=structuredClone(geometry);g.rooms[0].width=NaN;assert.throws(()=>make(g),/finite/);
 const p=structuredClone(plan);p.objects[0].center=new Array(3);assert.throws(()=>make(geometry,p),/finite/);
 const big=structuredClone(geometry);big.rooms=Array(257).fill(big.rooms[0]);assert.throws(()=>make(big),/size/);
 assert.throws(()=>make({...geometry,contract:'future'}),/Unsupported/);
 assert.throws(()=>canonicalSceneMetadata({...scene,extra:NaN}),/finite/);
 const cyclic={...scene};cyclic.extra=cyclic;assert.throws(()=>canonicalSceneMetadata(cyclic),/cyclic/);
});
test('Equipment transform mismatches and invalid navigation extents fail',()=>{
 const p=structuredClone(plan);p.objects[0].center[0]+=.2;assert.throws(()=>make(geometry,p),/transform/);
 const g=structuredClone(geometry);g.support_surfaces[0].max_x=g.support_surfaces[0].min_x;assert.throws(()=>make(g),/support/);
 const q=structuredClone(geometry);q.routes[0].points=[];assert.throws(()=>make(q),/endpoints/);
});
const result={status:'PASS_PURE_SCENE_METADATA_PROTOTYPE',checks,rooms:scene.rooms.length,nodes:scene.nodes.length,colliders:scene.colliders.length,doors:scene.doors.length,
 exported_mesh_files:0,renderer_engine_vr_adapter:false,canonical_owner_files_changed:false,model_gpu_network_browser_calls:0,
 scene_sha256:crypto.createHash('sha256').update(canonicalSceneMetadata(scene)).digest('hex')};
const suffix=process.argv[2]||'';assert.match(suffix,/^(-[0-9]+)?$/);
const receipt=new URL('./TEST-RESULT'+suffix+'.json',import.meta.url);fs.writeFileSync(receipt,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
fs.writeFileSync(new URL('./SYNTHETIC-METADATA'+suffix+'.json',import.meta.url),canonicalSceneMetadata(scene)+'\n',{flag:'wx'});
console.log(JSON.stringify({...result,checks:checks.length}));
