import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {createDoorSystem} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {createDoorSystem as nativeDoors} from './baseline/native038/walk_controller.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {exportSceneMetadata,canonicalSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {buildAirlockPolicy} from './candidate/tools/world_builder_engine/layout_package_assets/source/airlock_policy.mjs';
const geometry=JSON.parse(fs.readFileSync(new URL('./fixtures/synthetic_habitat.json',import.meta.url),'utf8'));
const original=JSON.stringify(geometry),doors=createDoorSystem(geometry),plan=buildRoomDressing(geometry,doors.assemblies());
const options={sceneId:'synthetic_habitat',sourceDigests:{geometry:'a'.repeat(64),dressing_recipe:'b'.repeat(64),door_controller:'c'.repeat(64)},doorInterlocks:doors.interlocks()};
const scene=exportSceneMetadata(geometry,plan,doors.definitions(),options),checks=[];
const test=(name,fn)=>{fn();checks.push(name);};
test('Pair metadata binds the exact source room, portals, door IDs and two distinct leaves',()=>{
 assert.equal(scene.contract,'world_scene_metadata_v2');assert.equal(scene.provenance.door_contract,'preview_hinged_doors_v2');
 const p=scene.airlock_pairs[0];assert.equal(p.source_room_id,'airlock');assert.deepEqual(p.door_ids,['door:opening_1','door:opening_2']);
 assert.deepEqual(p.leaf_node_ids,['node:door_opening_1_leaf','node:door_opening_2_leaf']);assert.equal(p.engine_runtime_included,false);assert.equal(p.pressure_simulation,false);
 assert.deepEqual(p.opening_policy.blocked_peer_conditions,['nonzero_angle','moving','nonzero_target','motion_held']);
});
test('Door back references and opening rules match membership only',()=>{
 for(const door of scene.doors){const paired=['opening_1','opening_2'].includes(door.portal_id);assert.equal(door.interlock_pair_ids.length,paired?1:0);assert.equal(door.interaction.rules.includes('paired_airlock_peer_closed_stopped'),paired);}
});
for(const [label,mutate] of [
 ['missing pair',p=>p.pop()],['wrong room',p=>p[0].roomId='operations'],['one door',p=>p[0].doorIds.pop()],
 ['duplicated door',p=>p[0].doorIds[1]=p[0].doorIds[0]],['unrelated door',p=>p[0].doorIds[1]='opening_3'],
 ['invented pressure',p=>p[0].pressureSimulation=true],['wrong policy',p=>p[0].contract='none']
])test('Rejects '+label+' from controller metadata',()=>{const p=structuredClone(options.doorInterlocks);mutate(p);assert.throws(()=>exportSceneMetadata(geometry,plan,doors.definitions(),{...options,doorInterlocks:p}));});
test('Rejects wrong leaf type or shared leaf association',()=>{
 const nodes=structuredClone(scene.nodes);nodes.find(n=>n.id===scene.airlock_pairs[0].leaf_node_ids[0]).kind='structural_primitive';
 assert.throws(()=>buildAirlockPolicy(geometry,scene.doors,nodes,doors.interlocks()),/leaf association/);
 const described=structuredClone(scene.doors);described[1].leaf_node_id=described[0].leaf_node_id;
 assert.throws(()=>buildAirlockPolicy(geometry,described,scene.nodes,doors.interlocks()),/association differs/);
});
test('Export controller behavior exactly matches native038 across pending, moving, open, closing and closed states',()=>{
 const a=createDoorSystem(geometry),b=nativeDoors(geometry),feet=[1.5,0,-2];
 const both=id=>assert.deepEqual(a.toggle(id,feet),b.toggle(id,feet));
 both('opening_1');both('opening_2');
 for(let i=0;i<8;i++){assert.deepEqual(a.advance(.05,feet),b.advance(.05,feet));both('opening_2');}
 both('opening_1');for(let i=0;i<8;i++)assert.deepEqual(a.advance(.05,feet),b.advance(.05,feet));both('opening_2');
 assert.deepEqual(a.interlocks(),b.interlocks());
});
test('Every door pose sample closes before another is sampled, without disabling interlocks',()=>{
 const d=createDoorSystem(geometry);for(const def of d.definitions()){
  const portal=geometry.portals.find(p=>p.id===def.id),normal=portal.axis==='x'?0:2;
  const middle=normal===0?[portal.coordinate,def.hinge[1],portal.center]:[portal.center,def.hinge[1],portal.coordinate];let feet=null;
  for(const sign of [-1,1]){const trial=[...middle];trial[normal]+=sign*1.05;if(!(trial[normal]+.34>=def.swingBounds.min[normal]&&trial[normal]-.34<=def.swingBounds.max[normal])){feet=trial;break;}}
  assert.ok(feet);assert.equal(d.toggle(def.id,feet).ok,true);for(let i=0;i<8;i++)d.advance(.05,feet);assert.equal(d.all().find(p=>p.id===def.id).state,'open');
  assert.equal(d.toggle(def.id,feet).ok,true);for(let i=0;i<8;i++)d.advance(.05,feet);assert.equal(d.all().find(p=>p.id===def.id).state,'closed');
 }
});
test('Canonical roundtrip is deterministic and leaves source inputs unchanged',()=>{
 const encoded=canonicalSceneMetadata(scene);assert.equal(canonicalSceneMetadata(JSON.parse(encoded)),encoded);assert.equal(JSON.stringify(geometry),original);
 assert.equal(canonicalSceneMetadata(exportSceneMetadata(geometry,plan,doors.definitions(),options)),encoded);
});
const metadata=canonicalSceneMetadata(scene),hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const serial=fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('POLICY-TEST-RESULT')).length+1;
fs.writeFileSync(new URL('./SYNTHETIC-POLICY-METADATA-'+serial+'.json',import.meta.url),metadata+'\n',{flag:'wx'});
const report={status:'EXPLICIT_PAIR_METADATA_AND_NATIVE038_EQUIVALENCE_PASS',checks_count:checks.length,checks,
 metadata_sha256:hash(metadata+'\n'),real_glb_export:false,canvas_graphics_models_ui:0,installed:false};
fs.writeFileSync(new URL('./POLICY-TEST-RESULT-'+serial+'.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,checks:checks.length}));
