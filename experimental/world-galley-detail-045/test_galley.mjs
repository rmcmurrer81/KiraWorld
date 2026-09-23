import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import * as current from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import * as before from './baseline/room_dressing_render.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/layout_package_assets/source/horizontal_navigation.mjs';
import {exportSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {buildAuthoredScene} from './candidate/tools/world_builder_engine/layout_package_assets/authored_scene.mjs';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const overlap=(a,b)=>a.min.every((v,i)=>v<b.max[i]&&a.max[i]>b.min[i]);
function signature(group){
 const rows=[];group.traverse(o=>{if(!o.isMesh)return;
  const m=o.material;rows.push({name:o.name,p:o.position.toArray(),r:o.rotation.toArray(),s:o.scale.toArray(),
   attrs:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),index:o.geometry.index?Array.from(o.geometry.index.array):null,
   material:[m.color.toArray(),m.roughness,m.metalness,m.opacity,m.side]});
 });return sha(JSON.stringify(rows));
}
function render(module,g,plan){const scene=new THREE.Scene(),materials=module.createDressingMaterials(THREE,plan,{canvasFactory:()=>null});const result=module.addRoomDressing(THREE,scene,g,plan,materials);scene.updateMatrixWorld(true);return {scene,...result};}
function geometryOnlyCanvas(){const ctx=new Proxy({},{get:()=>()=>{},set:()=>true});return {width:0,height:0,getContext:()=>ctx};}
function localRay(group,origin,direction){
 const ray=new THREE.Raycaster(group.localToWorld(new THREE.Vector3(...origin)),new THREE.Vector3(...direction).transformDirection(group.matrixWorld));
 return ray.intersectObject(group,true).map(hit=>({name:hit.object.name,distance:hit.distance,point:group.worldToLocal(hit.point.clone()).toArray()}));
}
function contains(b,outer){for(let i=0;i<3;i++){assert.ok(b.min.getComponent(i)>=outer.min[i]-1e-6,`Below bounds axis${i}`);assert.ok(b.max.getComponent(i)<=outer.max[i]+1e-6,`Above bounds axis${i}`);}}
const selected=process.argv[2]?[{variant:'explicit_saved_layout',url:pathToFileURL(process.argv[2]),expected:process.argv[3]}]:['base','renamed','wider','translated'].map(variant=>({variant,url:new URL('./fixtures/'+variant+'.json',import.meta.url)}));
const shapes=[];
for(const {variant,url,expected} of selected){
 const raw=fs.readFileSync(url),g=JSON.parse(raw),unchanged=JSON.stringify(g);if(expected)assert.equal(sha(raw),expected);
 const doors=createDoorSystem(g),plan=buildRoomDressing(g,doors.assemblies()),planBefore=JSON.stringify(plan);
 const old=render(before,g,plan),now=render(current,g,plan),galley=plan.objects.find(o=>o.kind==='galley');assert.ok(galley);
 const room=g.rooms.find(r=>r.id===galley.room_id),support=g.support_surfaces.find(s=>s.id===room.id+'_floor');assert.ok(support);
 assert.equal(galley.bounds.min[1],support.y);assert.ok(galley.bounds.min[0]>=support.min_x&&galley.bounds.max[0]<=support.max_x&&galley.bounds.min[2]>=support.min_z&&galley.bounds.max[2]<=support.max_z);
 const group=now.equipmentGroups.get(galley.id),detail=group.userData.galleyGeometry;assert.ok(detail);
 assert.equal(detail.applianceSimulation,false);assert.equal(detail.pressureOrLifeSupportClaim,false);
 let unchangedGroups=0,vertices=0,triangles=0;
 for(const o of plan.objects){contains(new THREE.Box3().setFromObject(now.equipmentGroups.get(o.id)),o.bounds);if(o.id!==galley.id){assert.equal(signature(now.equipmentGroups.get(o.id)),signature(old.equipmentGroups.get(o.id)));unchangedGroups++;}}
 group.traverse(o=>{if(!o.isMesh)return;for(const attr of Object.values(o.geometry.attributes))assert.ok(Array.from(attr.array).every(Number.isFinite));vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;});
 assert.ok(triangles<5000&&group.children.length<110);assert.notEqual(signature(group),signature(old.equipmentGroups.get(galley.id)));
 for(const name of ['sink_bottom','sink_drain','faucet_spout','counter_prep','cold_door','cold_pull','pantry_door','warming_window','warming_tray','warming_handle'])assert.ok(group.getObjectByName('galley_'+name),name);
 const [sx0,sz0]=detail.basin.openingMin,[sx1,sz1]=detail.basin.openingMax;
 const samples=[];
 // Cast into multiple points of the actual open sink from below the upper
 // cabinets. This catches an accidental solid counter/cabinet filler below.
 for(const fx of [.25,.75])for(const fz of [.25,.75]){
  const x=sx0+(sx1-sx0)*fx,z=sz0+(sz1-sz0)*fz;
  const hits=localRay(group,[x,1.02,z],[0,-1,0]);assert.ok(hits.length);
  assert.equal(hits[0].name,'galley_sink_bottom');assert.ok(Math.abs(hits[0].point[1]-detail.basin.floorY)<1e-6);
  const oldHits=localRay(old.equipmentGroups.get(galley.id),[x,1.02,z],[0,-1,0]);
  assert.ok(oldHits[0].point[1]>.85);samples.push({x,z,before_top_y:oldHits[0].point[1],after_top_y:hits[0].point[1]});
 }
 assert.ok(detail.basin.depth>=.19&&detail.basin.depth<=.21);
 // The recess is enclosed laterally; the ray must hit a basin wall instead of
 // continuing through an omitted side. Sample halfway above the basin floor.
 for(const direction of [[1,0,0],[-1,0,0],[0,0,1],[0,0,-1]]){
  const hits=localRay(group,[(sx0+sx1)/2,.77,(sz0+sz1)/2],direction);assert.ok(hits.length);assert.match(hits[0].name,/galley_sink_(side|end)/);
 }
 const prep=detail.prepSurface;assert.ok(prep.max[0]-prep.min[0]>.8);
 const prepHits=localRay(group,[(prep.max[0]+prep.min[0])/2,1.1,.15],[0,-1,0]);assert.equal(prepHits[0].name,'galley_counter_prep');assert.ok(Math.abs(prepHits[0].point[1]-.89)<1e-6);
 const spout=group.getObjectByName('galley_faucet_spout');assert.ok(spout.geometry.attributes.position.count>200);assert.equal(spout.geometry.type,'TubeGeometry');
 const window=group.getObjectByName('galley_warming_window');assert.equal(window.material.transparent,true);
 const ovenHits=localRay(group,[window.position.x,window.position.y,.30],[0,0,-1]);
 assert.equal(ovenHits[0].name,'galley_warming_window');assert.ok(ovenHits.some(h=>h.name==='galley_upper_back'));assert.ok(ovenHits.find(h=>h.name==='galley_upper_back').distance-ovenHits[0].distance>.4);
 const nav={contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:[...g.colliders,...plan.colliders]};
 for(const route of g.routes){assert.equal(checkHorizontalRoute(route,nav).status,'clear',route.id);assert.equal(checkHorizontalRoute({...route,points:[...route.points].reverse()},nav).status,'clear');}
 for(const d of doors.assemblies())assert.equal(overlap(galley.bounds,d.swingBounds),false);
 for(const other of plan.objects.filter(o=>o.id!==galley.id))assert.equal(overlap(galley.bounds,other.bounds),false);
 const walker=createWalkController(g,{extraColliders:plan.colliders});assert.equal(walker.snapshot().roomId,g.connectivity.entry_room_id);
 const assets=new URL('./candidate/tools/world_builder_engine/layout_package_assets/',import.meta.url);
 const options={sceneId:'galley_'+variant,sourceDigests:{geometry:sha(raw),dressing_recipe:sha(fs.readFileSync(new URL('source/room_dressing_plan.mjs',assets))),door_controller:sha(fs.readFileSync(new URL('source/walk_controller.mjs',assets)))},doorInterlocks:doors.interlocks()};
 const metadata=exportSceneMetadata(g,plan,doors.definitions(),options),authored=buildAuthoredScene(g,metadata,geometryOnlyCanvas);
 assert.equal(signature(authored.scene.getObjectByName(galley.id)),signature(group));
 assert.equal(metadata.colliders.find(c=>c.owner_node_id==='node:'+galley.id).id,'collider:'+galley.id);
 assert.equal(JSON.stringify(g),unchanged);assert.equal(JSON.stringify(plan),planBefore);assert.equal(fs.readFileSync(url).compare(raw),0);
 shapes.push({variant,galley_meshes:group.children.length,galley_vertices:vertices,galley_triangles:triangles,before_meshes:old.equipmentGroups.get(galley.id).children.length,basin_depth_m:detail.basin.depth,basin_ray_samples:samples,unchanged_other_equipment:unchangedGroups,route_count:g.routes.length,door_count:doors.definitions().length,exporter_geometry_identical:true,real_glb_export:false});
}
const source=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',import.meta.url),'utf8'),viewer=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');
const oldSource=fs.readFileSync(new URL('./baseline/room_dressing_render.mjs',import.meta.url),'utf8'),oldViewer=fs.readFileSync(new URL('./baseline/viewer.mjs',import.meta.url),'utf8');
assert.ok(viewer.includes(source.replaceAll('export function ','function ').trim()));
assert.equal(viewer.replace(source.replaceAll('export function ','function ').trim(),'DRESSING'),oldViewer.replace(oldSource.replaceAll('export function ','function ').trim(),'DRESSING'));
// Ensure no renderer branch outside galley changed, including the installed bunk.
const withoutGalley=s=>s.replace(/    }else if\(kind==='galley'\)\{[\s\S]*?(?=    }else if\(kind==='personal_storage')/,'GALLEY\n');assert.equal(withoutGalley(source),withoutGalley(oldSource));
const result={status:'PASS_GALLEY_GEOMETRY_ROUTES_SUPPORT_AND_EXPORT_ASSEMBLY',shapes,native_exporter_source_consistent:true,unchanged_plan_colliders:true,models_gpu_ui:0,limits:['Static authored geometry; visual review pending.','Appliances do not operate. No water/heat/cold-food or life-support simulation.','Inert Canvas exporter assembly is not a GLB or texture roundtrip.','No new dining furniture or room-layout correction.']};
const receipt=process.argv[4]||('TEST-RESULT-'+(fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('TEST-RESULT')).length+1)+'.json');assert.match(receipt,/^TEST-RESULT[-A-Z0-9]*\.json$/);fs.writeFileSync(new URL('./'+receipt,import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
