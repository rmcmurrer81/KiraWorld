import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {buildRoomDressing} from './room_dressing_plan.mjs';
import {createDressingMaterials,addRoomDressing} from './room_dressing_render.mjs';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/horizontal_navigation.mjs';
const geometryPath=process.argv[2]||new URL('./fixtures/synthetic_habitat.json',import.meta.url);
const raw=fs.readFileSync(geometryPath),geometry=JSON.parse(raw),doors=createDoorSystem(geometry),plan=buildRoomDressing(geometry,doors.assemblies());
const checks=[];function test(name,fn){fn();checks.push(name);}
test('Pure deterministic plan preserves source and carries all six roles',()=>{
 assert.deepEqual(plan,buildRoomDressing(geometry,doors.assemblies()));assert.equal(fs.readFileSync(geometryPath).compare(raw),0);
 for(const role of ['equipment_vestibule','airlock','operations','habitat','laboratory','observation'])assert.ok(plan.objects.some(o=>o.role===role),role);
 assert.equal(new Set(plan.objects.map(o=>o.kind)).size,15);
});
test('Unknown unrelated functions do not become a habitat',()=>{
 const unrelated=structuredClone(geometry);unrelated.functional_program={room:'retail'};
 const p=buildRoomDressing(unrelated,doors.assemblies());assert.equal(p.enabled,false);assert.equal(p.objects.length,0);assert.equal(p.colliders.length,0);
});
test('Entry, walking routes and all opened door routes remain usable with furnishings',()=>{
 const controller=createWalkController(geometry,{extraColliders:plan.colliders});assert.equal(controller.snapshot().roomId,geometry.connectivity.entry_room_id);
 const nav={contract:NAVIGATION_CONTRACT,support_surfaces:geometry.support_surfaces,colliders:plan.colliders};
 for(const route of geometry.routes){assert.equal(checkHorizontalRoute(route,nav).status,'clear',route.id);assert.equal(checkHorizontalRoute({...route,points:[...route.points].reverse()},nav).status,'clear');}
 for(const d of doors.assemblies())for(const c of plan.colliders)assert.ok(!c.min.every((v,i)=>v<d.swingBounds.max[i]&&c.max[i]>d.swingBounds.min[i]),d.id+'/'+c.id);
});
test('All equipment stays in its room and equipment footprints do not overlap',()=>{
 for(const o of plan.objects){const r=geometry.rooms.find(r=>r.id===o.room_id);assert.ok(o.bounds.min[0]>=r.x+.09&&o.bounds.max[0]<=r.x+r.width-.09);assert.ok(o.bounds.min[2]>=r.z+.09&&o.bounds.max[2]<=r.z+r.depth-.09);assert.ok(o.bounds.max[1]<=r.floor_y+r.height);}
 for(let i=0;i<plan.objects.length;i++)for(let j=i+1;j<plan.objects.length;j++){const a=plan.objects[i].bounds,b=plan.objects[j].bounds;assert.ok(!a.min.every((v,k)=>v<b.max[k]&&a.max[k]>b.min[k]));}
 assert.ok(plan.colliders.length<=128);assert.ok(Object.isFrozen(plan.objects[0].bounds.min));
});
const THREE=await import(pathToFileURL(process.env.WORLD_THREE_MODULE||path.join(os.homedir(),'Kira/third_party/three/build/three.module.js')).href);
const scene=new THREE.Scene(),materials=createDressingMaterials(THREE,plan,{canvasFactory:()=>null});
const rendered=addRoomDressing(THREE,scene,geometry,plan,materials);scene.updateMatrixWorld(true);
test('Actual multi-part rendered equipment fits collision bounds',()=>{
 const failures=[];
 for(const o of plan.objects){
  const group=rendered.equipmentGroups.get(o.id);assert.ok(group.children.length>=7,o.kind+' should be shaped equipment');
  const b=new THREE.Box3().setFromObject(group);const lo=b.min.toArray(),hi=b.max.toArray();
  for(let i=0;i<3;i++)if(!(lo[i]>=o.bounds.min[i]-1e-6&&hi[i]<=o.bounds.max[i]+1e-6))failures.push({kind:o.kind,axis:i,actual:[lo[i],hi[i]],bound:[o.bounds.min[i],o.bounds.max[i]]});
 }
 assert.deepEqual(failures,[]);
});
test('Lighting, modest physical signs and authored materials replace floating banners',()=>{
 assert.equal(plan.lights.length,7);assert.ok(plan.signs.length>=4);
 assert.ok(scene.children.filter(o=>o.isPointLight).every(o=>!o.castShadow));assert.equal(scene.children.filter(o=>o.isSprite).length,0);
 assert.ok(rendered.meshCount<1100);assert.ok(Object.values(materials.basic).every(m=>m.isMeshStandardMaterial));
});
const result={status:'PASS_AUTHORED_DRESSING_AND_PHYSICAL_CLEARANCES',checks,objects:plan.objects.map(o=>({id:o.id,role:o.role,kind:o.kind})),
 collider_count:plan.colliders.length,meshes:rendered.meshCount,omitted:plan.omitted,architecture:plan.architecture.length,
 gpu_or_browser_started:false,owner_source_unchanged:fs.readFileSync(geometryPath).compare(raw)===0,visual_approval:false};
const receipt=process.argv[3]||'TEST-RESULT-002.json';assert.match(receipt,/^TEST-RESULT[-0-9]*\.json$/);
fs.writeFileSync(new URL('./'+receipt,import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,checks:checks.length,objects:plan.objects.length,colliders:plan.colliders.length,meshes:rendered.meshCount,omitted:plan.omitted}));
