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
const box=o=>new THREE.Box3().setFromObject(o);
function contains(b,outer){for(let i=0;i<3;i++){assert.ok(b.min.getComponent(i)>=outer.min[i]-1e-6);assert.ok(b.max.getComponent(i)<=outer.max[i]+1e-6);}}
function signature(group){
 const rows=[];group.traverse(o=>{if(!o.isMesh)return;
  const m=o.material;rows.push({p:o.position.toArray(),r:o.rotation.toArray(),s:o.scale.toArray(),
   attrs:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),index:o.geometry.index?Array.from(o.geometry.index.array):null,
   material:[m.color.toArray(),m.roughness,m.metalness,m.opacity,m.side]});
 });return sha(JSON.stringify(rows));
}
function render(module,g,plan){const scene=new THREE.Scene(),materials=module.createDressingMaterials(THREE,plan,{canvasFactory:()=>null});const result=module.addRoomDressing(THREE,scene,g,plan,materials);scene.updateMatrixWorld(true);return {scene,...result};}
// Geometry-only exporter-path check: Canvas drawing calls are deliberately inert.
// This supplies texture placeholders to reach mesh assembly; it is NOT texture,
// visual or GLB importer evidence and is never saved as a rendered image.
function geometryOnlyCanvas(){const ctx=new Proxy({},{get:()=>()=>{},set:()=>true});return {width:0,height:0,getContext:()=>ctx};}
const shapes=[];
const selected=process.argv[2]?[{variant:'explicit_saved_layout',url:pathToFileURL(process.argv[2]),expected:process.argv[3]}]:['base','renamed','wider','translated'].map(variant=>({variant,url:new URL('./fixtures/'+variant+'.json',import.meta.url)}));
for(const {variant,url,expected} of selected){
 const raw=fs.readFileSync(url),g=JSON.parse(raw),unchanged=JSON.stringify(g);if(expected)assert.equal(sha(raw),expected);
 const doors=createDoorSystem(g),plan=buildRoomDressing(g,doors.assemblies());
 const old=render(before,g,plan),now=render(current,g,plan);let unchangedGroups=0;
 const bunk=plan.objects.find(o=>o.kind==='bunk');assert.ok(bunk);const room=g.rooms.find(r=>r.id===bunk.room_id);
 const support=g.support_surfaces.find(s=>s.id===room.id+'_floor');assert.ok(support);
 assert.ok(bunk.bounds.min[0]>=support.min_x&&bunk.bounds.max[0]<=support.max_x&&bunk.bounds.min[2]>=support.min_z&&bunk.bounds.max[2]<=support.max_z);assert.equal(bunk.bounds.min[1],support.y);
 for(const o of plan.objects){contains(box(now.equipmentGroups.get(o.id)),o.bounds);if(o.id!==bunk.id){assert.equal(signature(now.equipmentGroups.get(o.id)),signature(old.equipmentGroups.get(o.id)));unchangedGroups++;}}
 const group=now.equipmentGroups.get(bunk.id),detail=group.userData.bunkGeometry;assert.ok(detail);assert.equal(detail.physicsOrSafetyValidation,false);
 let vertices=0,triangles=0;group.traverse(o=>{if(o.isMesh){for(const attr of Object.values(o.geometry.attributes))assert.ok(Array.from(attr.array).every(Number.isFinite));vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;}});
 assert.ok(triangles<10000);assert.notEqual(signature(group),signature(old.equipmentGroups.get(bunk.id)));
 for(const level of ['lower','upper']){
  const mattress=group.getObjectByName('bunk_'+level+'_mattress'),pillow=group.getObjectByName('bunk_'+level+'_pillow'),deck=group.getObjectByName('bunk_'+level+'_deck'),blanket=group.getObjectByName('bunk_'+level+'_blanket');
  assert.ok(mattress.geometry.attributes.position.count>100&&pillow.geometry.attributes.position.count>100);
  // Vertical support relationships are checked in the unrotated assembly frame.
  mattress.geometry.computeBoundingBox();pillow.geometry.computeBoundingBox();deck.geometry.computeBoundingBox();
  const deckTop=deck.position.y+deck.geometry.boundingBox.max.y,mattressBottom=mattress.position.y+mattress.geometry.boundingBox.min.y,mattressTop=mattress.position.y+mattress.geometry.boundingBox.max.y,pillowBottom=pillow.position.y+pillow.geometry.boundingBox.min.y;
  assert.ok(Math.abs(mattressBottom-deckTop)<.003);assert.ok(Math.abs(pillowBottom-mattressTop)<1e-6);
  const pos=blanket.geometry.attributes.position,ys=Array.from({length:pos.count},(_,i)=>pos.getY(i));assert.ok(Math.max(...ys)-Math.min(...ys)>.06,'Blanket must contain actual folds/drop');
  for(let i=0;i<pos.count;i++){const z=blanket.position.z+pos.getZ(i),y=blanket.position.y+pos.getY(i);if(Math.abs(z)<.34)assert.ok(y>=mattressTop-.001,'Central blanket penetrates mattress');}
 }
 const [left,right]=detail.frontAccessX,[ladderLeft,ladderRight]=detail.ladderStileX;
 assert.ok(right-left>.5&&left<ladderLeft-.016&&right>ladderRight+.016);
 for(const child of group.children.filter(o=>o.name==='bunk_upper_guard_post')){assert.ok(child.position.y-child.geometry.parameters.height/2<=1.3075);assert.ok(child.position.y+child.geometry.parameters.height/2>=detail.guardTop-1e-6);}
 const nav={contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:[...g.colliders,...plan.colliders]};
 for(const route of g.routes){assert.equal(checkHorizontalRoute(route,nav).status,'clear',route.id);assert.equal(checkHorizontalRoute({...route,points:[...route.points].reverse()},nav).status,'clear');}
 for(const d of doors.assemblies())assert.equal(overlap(bunk.bounds,d.swingBounds),false);
 for(const other of plan.objects.filter(o=>o.id!==bunk.id))assert.equal(overlap(bunk.bounds,other.bounds),false);
 const walker=createWalkController(g,{extraColliders:plan.colliders});assert.equal(walker.snapshot().roomId,g.connectivity.entry_room_id);
 const options={sceneId:'bunk_'+variant,sourceDigests:{geometry:sha(raw),dressing_recipe:sha(fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs',import.meta.url))),door_controller:sha(fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs',import.meta.url)))},doorInterlocks:doors.interlocks()};
 const metadata=exportSceneMetadata(g,plan,doors.definitions(),options),authored=buildAuthoredScene(g,metadata,geometryOnlyCanvas);
 assert.equal(signature(authored.scene.getObjectByName(bunk.id)),signature(group));
 assert.equal(metadata.colliders.find(c=>c.owner_node_id==='node:'+bunk.id).id,'collider:'+bunk.id);
 assert.equal(JSON.stringify(g),unchanged);assert.equal(fs.readFileSync(url).compare(raw),0);
 shapes.push({variant,bunk_meshes:group.children.length,bunk_vertices:vertices,bunk_triangles:triangles,unchanged_other_equipment:unchangedGroups,route_count:g.routes.length,door_count:doors.definitions().length,front_access_width_metres:right-left,exporter_geometry_identical:true,real_glb_export:false});
}
const source=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',import.meta.url),'utf8');
const viewer=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');assert.ok(viewer.includes(source.replaceAll('export function ','function ').trim()));
const baselineViewer=fs.readFileSync(new URL('./baseline/viewer.mjs',import.meta.url),'utf8'),baselineSource=fs.readFileSync(new URL('./baseline/room_dressing_render.mjs',import.meta.url),'utf8');
assert.equal(viewer.replace(source.replaceAll('export function ','function ').trim(),'DRESSING'),baselineViewer.replace(baselineSource.replaceAll('export function ','function ').trim(),'DRESSING'));
const result={status:'PASS_BUNK_GEOMETRY_ROUTES_SUPPORT_AND_EXPORT_ASSEMBLY',shapes,native_exporter_source_consistent:true,unchanged_plan_colliders:true,models_gpu_ui:0,
 limits:['Experimental static authored geometry; visual review pending.','No physics, comfort, structural safety or standard-compliance assertion.','Exporter comparison assembles actual meshes with inert Canvas placeholders; no GLB/texture roundtrip was performed.']};
const receipt=process.argv[4]||('TEST-RESULT-'+(fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('TEST-RESULT')).length+1)+'.json');assert.match(receipt,/^TEST-RESULT[-A-Z0-9]*\.json$/);
fs.writeFileSync(new URL('./'+receipt,import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
