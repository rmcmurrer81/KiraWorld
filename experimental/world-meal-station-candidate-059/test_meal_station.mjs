import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import * as render from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import * as oldRender from './preimages/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {buildRoomDressing as oldPlan} from './preimages/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute,checkWalkSpawn} from './candidate/tools/world_builder_engine/layout_package_assets/source/horizontal_navigation.mjs';
import {exportSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {buildAuthoredScene} from './candidate/tools/world_builder_engine/layout_package_assets/authored_scene.mjs';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const overlap=(a,b,pad=0)=>a.min.every((v,i)=>v<b.max[i]+pad&&a.max[i]>b.min[i]-pad);
function signature(group){const rows=[];group.traverse(o=>{if(!o.isMesh)return;const m=o.material;
  rows.push({name:o.name,p:o.position.toArray(),r:o.rotation.toArray(),s:o.scale.toArray(),
    attrs:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),index:o.geometry.index?Array.from(o.geometry.index.array):null,
    material:[m.color.toArray(),m.roughness,m.metalness,m.opacity,m.side]});});return sha(JSON.stringify(rows));}
function draw(module,g,plan){const scene=new THREE.Scene(),materials=module.createDressingMaterials(THREE,plan,{canvasFactory:()=>null});const result=module.addRoomDressing(THREE,scene,g,plan,materials);scene.updateMatrixWorld(true);return {scene,...result};}
function geometryOnlyCanvas(){const ctx=new Proxy({},{get:()=>()=>{},set:()=>true});return {width:0,height:0,getContext:()=>ctx};}
function ray(group,origin,direction,far=Infinity){const r=new THREE.Raycaster(group.localToWorld(new THREE.Vector3(...origin)),new THREE.Vector3(...direction).transformDirection(group.matrixWorld),0,far);
  return r.intersectObject(group,true).map(hit=>({name:hit.object.name,distance:hit.distance,point:group.worldToLocal(hit.point.clone()).toArray()}));}
function contains(box,bounds){for(let i=0;i<3;i++){assert.ok(box.min.getComponent(i)>=bounds.min[i]-1e-6,'below assembly bounds');assert.ok(box.max.getComponent(i)<=bounds.max[i]+1e-6,'above assembly bounds');}}
const selected=process.argv[2]?[{variant:'actual_saved_mars',path:process.argv[2],expected:process.argv[3]}]:['base','renamed','wider','translated'].map(variant=>({variant,path:new URL('./fixtures/'+variant+'.json',import.meta.url)}));
const shapes=[];
for(const item of selected){
 const raw=fs.readFileSync(item.path);if(item.expected)assert.equal(sha(raw),item.expected);const g=JSON.parse(raw),beforeG=JSON.stringify(g);
 const doors=createDoorSystem(g),old=oldPlan(g,doors.assemblies()),plan=buildRoomDressing(g,doors.assemblies());
 const meals=plan.objects.filter(o=>o.kind==='meal_station');assert.equal(meals.length,1);
 const meal=meals[0],room=g.rooms.find(r=>r.id===meal.room_id),support=g.support_surfaces.find(s=>s.id===room.id+'_floor');
 assert.equal(g.functional_program[room.id],'habitat');assert.equal(meal.id,'equipment_'+room.id+'_meal_station');
 assert.deepEqual(plan.objects.filter(o=>o.kind!=='meal_station'),old.objects);
 assert.deepEqual(plan.colliders.filter(c=>c.id!==meal.id),old.colliders);
 for(const key of ['architecture','lights','signs','roomStyles','omitted'])assert.deepEqual(plan[key],old[key],key+' unchanged');
 assert.equal(meal.bounds.min[1],support.y);assert.ok(meal.bounds.min[0]>=support.min_x&&meal.bounds.max[0]<=support.max_x&&meal.bounds.min[2]>=support.min_z&&meal.bounds.max[2]<=support.max_z);
 for(const d of doors.assemblies())assert.equal(overlap(meal.bounds,d.swingBounds,.08),false,'door swing protected');
 for(const c of old.colliders)assert.equal(overlap(meal.bounds,c,.08),false,'old equipment/architecture remains');
 const current=draw(render,g,plan),prior=draw(oldRender,g,old),group=current.equipmentGroups.get(meal.id);
 const box=new THREE.Box3().setFromObject(group);contains(box,meal.bounds);
 assert.ok(Math.abs(box.min.y-support.y)<1e-7,'feet supported at floor');
 for(const o of old.objects)assert.equal(signature(current.equipmentGroups.get(o.id)),signature(prior.equipmentGroups.get(o.id)),o.kind+' mesh unchanged');
 let vertices=0,triangles=0;
 group.traverse(o=>{if(!o.isMesh)return;for(const a of Object.values(o.geometry.attributes))assert.ok(Array.from(a.array).every(Number.isFinite));vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;});
 assert.ok(group.children.length<32&&triangles<12000);
 const detail=group.userData.mealStationGeometry;assert.equal(detail.seatCount,2);assert.equal(detail.seatedAvatarInteraction,false);assert.equal(detail.ergonomicOrSafetyValidation,false);
 const seats=[];
 for(const side of [-1,1]){const hits=ray(group,[side*.295,.8,-.39],[0,-1,0]);assert.equal(hits[0].name,'meal_seat_'+side);assert.ok(Math.abs(hits[0].point[1]-.4975)<1e-6);seats.push(hits[0]);
   const backs=ray(group,[side*.295,.85,.3],[0,0,-1]);assert.equal(backs[0].name,'meal_back_'+side);}
 const table=ray(group,[0,1.1,.25],[0,-1,0]);assert.equal(table[0].name,'meal_tabletop');assert.ok(Math.abs(table[0].point[1]-.765)<1e-6);
 assert.equal(ray(group,[.3,.6,.6],[0,0,-1],.75).length,0,'open leg space is real geometry');
 const pedestal=group.getObjectByName('meal_table_pedestal'),plate=group.getObjectByName('meal_table_floor_plate');assert.ok(pedestal&&plate);
 const nav={contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:[...g.colliders,...plan.colliders]};
 for(const route of g.routes){assert.equal(checkHorizontalRoute(route,nav).status,'clear',route.id);assert.equal(checkHorizontalRoute({...route,points:[...route.points].reverse()},nav).status,'clear');}
 const center=[meal.center[0],room.floor_y,meal.center[2]];assert.equal(checkWalkSpawn(center,nav).ok,false,'furniture body cannot be occupied');
 const front=group.localToWorld(new THREE.Vector3(0,0,1.2)).toArray(),back=group.localToWorld(new THREE.Vector3(0,0,-1.2)).toArray();
 const crossed=checkHorizontalRoute({id:'meal_midstep',points:[front,back],avatar_radius:.34,avatar_height:1.68},nav);assert.notEqual(crossed.status,'clear');
 const walker=createWalkController(g,{extraColliders:plan.colliders});assert.equal(walker.snapshot().roomId,g.connectivity.entry_room_id);
 const assets=new URL('./candidate/tools/world_builder_engine/layout_package_assets/',import.meta.url);
 const metadata=exportSceneMetadata(g,plan,doors.definitions(),{sceneId:'meal_'+item.variant,sourceDigests:{geometry:sha(raw),dressing_recipe:sha(fs.readFileSync(new URL('source/room_dressing_plan.mjs',assets))),door_controller:sha(fs.readFileSync(new URL('source/walk_controller.mjs',assets)))},doorInterlocks:doors.interlocks()});
 const authored=buildAuthoredScene(g,metadata,geometryOnlyCanvas);assert.equal(signature(authored.scene.getObjectByName(meal.id)),signature(group));
 const mc=metadata.colliders.find(c=>c.owner_node_id==='node:'+meal.id);assert.equal(mc.id,'collider:'+meal.id);assert.deepEqual(mc.bounds,meal.bounds);
 const semantic=metadata.nodes.find(n=>n.id==='node:'+meal.id);assert.equal(semantic.kind,'meal_station');assert.equal(semantic.behavior,'static_visual_equipment');assert.deepEqual(semantic.interactions,[]);
 assert.deepEqual(authored.doors.definitions(),doors.definitions());assert.deepEqual(authored.doors.interlocks(),doors.interlocks());
 // Reserve the complete crew-room floor with legitimate within-room route
 // segments: the optional assembly must omit rather than move old furniture,
 // occupy a route or pick a different room because its label sounds suitable.
 const crowded=structuredClone(g);
 for(let z=room.z+.4;z<room.z+room.depth-.2;z+=.65)crowded.routes.push({id:'reserved_'+z,avatar_height:1.68,avatar_radius:.34,points:[[room.x+.4,room.floor_y,z],[room.x+room.width-.4,room.floor_y,z]]});
 const crowdedPlan=buildRoomDressing(crowded,doors.assemblies());assert.equal(crowdedPlan.objects.some(o=>o.kind==='meal_station'),false);
 assert.ok(crowdedPlan.omitted.some(o=>o.kind==='meal_station'&&o.reason.includes('preserving')));
 const unknown=structuredClone(g);delete unknown.functional_program[room.id];assert.equal(buildRoomDressing(unknown,doors.assemblies()).objects.some(o=>o.kind==='meal_station'),false);
 assert.equal(JSON.stringify(g),beforeG);assert.equal(fs.readFileSync(item.path).compare(raw),0);
 shapes.push({variant:item.variant,placement:{room_id:meal.room_id,center:meal.center,yaw:meal.yaw,bounds:meal.bounds},meshes:group.children.length,vertices,triangles,seat_rays:seats,old_equipment_unchanged:old.objects.length,old_colliders_preserved:old.colliders.length,route_count:g.routes.length,door_count:doors.definitions().length,crowded_omission:true,unknown_role_not_inferred:true,exporter_geometry_identical:true,real_GLB_or_visual_review:false});
}
const read=p=>fs.readFileSync(new URL(p,import.meta.url),'utf8'),embed=s=>s.replaceAll('export function ','function ').replaceAll('export const ','const ').trim();
let oldViewer=read('./preimages/tools/world_builder_engine/viewer.mjs'),viewer=read('./candidate/tools/world_builder_engine/viewer.mjs');
for(const rel of ['room_dressing_plan.mjs','room_dressing_render.mjs']){
 const current=read('./candidate/tools/world_builder_engine/layout_package_assets/source/'+rel),old=read('./preimages/tools/world_builder_engine/layout_package_assets/source/'+rel);
 assert.ok(viewer.includes(embed(current)));assert.ok(oldViewer.includes(embed(old)));
 viewer=viewer.replace(embed(current),rel);oldViewer=oldViewer.replace(embed(old),rel);
}
assert.equal(viewer,oldViewer,'only shared plan/render embedding changes viewer');
const result={status:'PASS_MEAL_GEOMETRY_PLACEMENT_OMISSION_AND_SHARED_EXPORT',shapes,models_GPU_UI:0,
 limits:['Static original furniture; not seated-avatar, comfort or safety validation.','No actual GLB export or image/native visual review in this geometry-only suite.','Canvas is inert for exporter assembly geometry checks; texture transport is not checked.']};
console.log(JSON.stringify(result));
