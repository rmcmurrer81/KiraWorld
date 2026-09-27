import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {createDoorSystem} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {buildAuthoredScene} from './candidate/tools/world_builder_engine/layout_package_assets/authored_scene.mjs';
import {exportSceneMetadata,canonicalSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {buildPressureHatch} from './candidate/tools/world_builder_engine/pressure_hatch.mjs';
import {buildHatchStructuralMesh,planHatchArchitecture} from './candidate/tools/world_builder_engine/pressure_hatch_architecture.mjs';
const fixture=()=>JSON.parse(readFileSync(new URL('fixtures/base.json',import.meta.url),'utf8'));
const opts=doors=>({sceneId:'cpu_hatch_integration',sourceDigests:{geometry:'1'.repeat(64),dressing_recipe:'2'.repeat(64),door_controller:'3'.repeat(64)},doorInterlocks:doors.interlocks()});
const factory=()=>{const ctx=Object.fromEntries(['arc','beginPath','fill','fillRect','fillText','lineTo','moveTo','stroke','strokeRect'].map(name=>[name,()=>{}]));return {width:1,height:1,getContext:()=>ctx};};
const prepare=g=>{const doors=createDoorSystem(g),plan=buildRoomDressing(g,createDoorSystem(g,{hatchGeometry:false}).assemblies()),metadata=exportSceneMetadata(g,plan,doors.definitions(),opts(doors));return {doors,plan,metadata};};
function dispose(root){const material=new Set(),texture=new Set();root.traverse(o=>{o.geometry?.dispose();if(o.material){material.add(o.material);if(o.material.map)texture.add(o.material.map);}});texture.forEach(t=>t.dispose());material.forEach(m=>m.dispose());}
const bounds=object=>{const b=new THREE.Box3().setFromObject(object,true);return [...b.min.toArray(),...b.max.toArray()];};
const near=(a,b)=>a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<3e-6,`${v} != ${b[i]}`));

test('strict metadata binds both hatch leaves, every part collider, structural cuts and original pair identities',()=>{
 const g=fixture(),{doors,metadata}=prepare(g),hatches=metadata.doors.filter(d=>d.variant);
 assert.equal(hatches.length,2);assert.equal(metadata.airlock_pairs.length,1);
 for(const d of hatches){
  assert.equal(d.variant,'authored_pressure_hatch_geometry_v1');assert.equal(d.pressure_simulation,false);assert.equal(d.latch_simulation,false);
  const nodes=metadata.nodes.filter(n=>[...d.frame_node_ids,...d.kinematic_node_ids].includes(n.id));assert.equal(nodes.length,54);
  const colliders=metadata.colliders.filter(c=>nodes.some(n=>n.id===c.owner_node_id));assert.equal(colliders.length,66);
  assert.equal(colliders.find(c=>c.id==='collider:door_'+d.portal_id+'_leaf').owner_node_id,d.leaf_node_id);
  assert.equal(nodes.find(n=>n.id===d.leaf_node_id).kind,'door_leaf');
  assert.deepEqual(d.interlock_pair_ids,[metadata.airlock_pairs[0].id]);
  assert.equal(metadata.airlock_pairs[0].leaf_node_ids.includes(d.leaf_node_id),true);
 }
 assert.ok(metadata.nodes.some(n=>n.representation?.type==='source_box_with_authored_hatch_cutouts'));
 assert.deepEqual(JSON.parse(canonicalSceneMetadata(metadata)),JSON.parse(JSON.stringify(metadata)));
 const plain=metadata.doors.filter(d=>!d.variant);assert.equal(plain.length,doors.definitions().length-2);assert.ok(plain.every(d=>d.collision_policy==='conservative_rotated_leaf_aabb_and_quarter_disc_sweep'));
});

test('hatch tampering fails closed and ordinary slab assertions are retained',()=>{
 const g=fixture(),{doors,plan}=prepare(g),base=doors.definitions(),index=base.findIndex(d=>d.kind==='pressure_hatch');
 const changes=[d=>{d.hinge[0]+=.1;},d=>{d.leafSize[0]+=.02;},d=>{d.swingBounds.max[0]-=.02;},d=>{d.hatchPlan.fixed[0].center[2]+=.02;},d=>{d.latchSimulation=true;},d=>{d.kind='magic_hatch';},d=>{d.maxStepSeconds=.5;}];
 for(const change of changes){const altered=structuredClone(base);change(altered[index]);assert.throws(()=>exportSceneMetadata(g,plan,altered,opts(doors)));}
 const ordinary=base.findIndex(d=>!d.kind),altered=structuredClone(base);altered[ordinary].leafSize[1]+=.1;assert.throws(()=>exportSceneMetadata(g,plan,altered,opts(doors)),/leaf differs/);
});

test('actual CPU scene meshes match strict metadata and actual controller at every closed/partial/open pose',()=>{
 const g=fixture(),{metadata}=prepare(g),built=buildAuthoredScene(g,metadata,factory,null);
 assert.equal(built.semantic.size,metadata.nodes.length);
 for(const c of metadata.colliders)assert.ok(built.semantic.get(c.owner_node_id).userData.collider_ids.includes(c.id));
 for(const plan of built.doors.hatchPlans()){
  const def=built.doors.definitions().find(d=>d.id===plan.portalId),feet=[...plan.origin],n=plan.axis==='x'?0:2;feet[n]-=plan.normalSign*1.1;
  const staticIds=metadata.doors.find(d=>d.portal_id===plan.portalId).frame_node_ids,initial=staticIds.map(id=>bounds(built.semantic.get(id)));
  assert.ok(built.doors.toggle(plan.portalId,feet).ok);
  for(let i=0;i<=8;i++){
   const state=built.doors.all().find(d=>d.id===plan.portalId);built.hinges.get(plan.portalId).rotation.y=state.angle;built.scene.updateMatrixWorld(true);
   const leaf=built.leafMeshes.get(plan.portalId),actualBounds=bounds(leaf);
   for(let j=0;j<3;j++){assert.ok(actualBounds[j]>=state.collider.min[j]-3e-6);assert.ok(actualBounds[j+3]<=state.collider.max[j]+3e-6);}
   near(new THREE.Box3().setFromObject(leaf,true).getCenter(new THREE.Vector3()).toArray(),state.center);
   assert.equal(leaf.parent,built.hinges.get(plan.portalId));staticIds.forEach((id,j)=>near(bounds(built.semantic.get(id)),initial[j]));
   if(i<8)built.doors.advance(.05,feet);
  }
  assert.ok(built.doors.toggle(plan.portalId,feet).ok);for(let i=0;i<8;i++)built.doors.advance(.05,feet);built.hinges.get(plan.portalId).rotation.y=0;
 }
 // Preserve all prior furniture and signs via unchanged placement inputs.
 assert.equal(built.plan.signs.length,7);assert.equal(built.plan.objects.length,17);
 dispose(built.scene);
});

test('actual preview helper functions produce identical cut structural geometry to the export helper',()=>{
 const source=readFileSync(new URL('candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');
 const prefix=source.slice(0,source.indexOf('async function start()')).replace(/^import .*;\r?\n/gm,'');
 const helper=new Function('THREE','buildHatchStructuralMesh','planHatchArchitecture','buildPressureHatch',prefix+'; return {createStructuralPrimitive,createDressingMaterials,buildRoomDressing};')(THREE,buildHatchStructuralMesh,planHatchArchitecture,buildPressureHatch);
 const g=fixture(),{doors,plan,metadata}=prepare(g),architecture=planHatchArchitecture(g,doors.hatchPlans());
 assert.deepEqual(helper.buildRoomDressing(g,createDoorSystem(g,{hatchGeometry:false}).assemblies()),plan);
 const materials=helper.createDressingMaterials(THREE,plan,{canvasFactory:factory});
 for(const p of g.primitives.filter(p=>architecture.modifications[p.id])){
  const material=materials.surface(p.role),actual=helper.createStructuralPrimitive(THREE,p,material,null,materials,architecture),expected=buildHatchStructuralMesh(THREE,p,material,architecture);
  assert.equal(actual.children.length,expected.children.length);
  for(let i=0;i<actual.children.length;i++)for(const name of ['position','normal','uv'])assert.deepEqual(actual.children[i].geometry.attributes[name].array,expected.children[i].geometry.attributes[name].array);
  dispose(actual);dispose(expected);
 }
});
