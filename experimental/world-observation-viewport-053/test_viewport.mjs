import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import * as detail from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import * as before from './preimages/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/layout_package_assets/source/horizontal_navigation.mjs';
import {exportSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {buildAuthoredScene} from './candidate/tools/world_builder_engine/layout_package_assets/authored_scene.mjs';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex'),raw=fs.readFileSync(process.argv[2]);assert.equal(sha(raw),process.argv[3]);
const g=JSON.parse(raw),unchanged=JSON.stringify(g),d=createDoorSystem(g),plan=buildRoomDressing(g,d.assemblies()),planUnchanged=JSON.stringify(plan);
const checks=[];function test(name,fn){const result=fn();checks.push({name,status:'pass',result});}
function canvas(){return {width:0,height:0,getContext:()=>new Proxy({},{get:()=>()=>{},set:()=>true})};}
const vp=detail.planObservationViewport(g,plan);assert.ok(vp);const wall=g.primitives.find(p=>p.id===vp.wall_id),collider=g.colliders.find(c=>c.id===vp.safety_collider_id);
const sourceDigests={geometry:sha(raw),dressing_recipe:sha(fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs',import.meta.url))),door_controller:sha(fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs',import.meta.url)))};
const meta=exportSceneMetadata(g,plan,d.definitions(),{sceneId:'viewport053',sourceDigests,doorInterlocks:d.interlocks()});
const built=buildAuthoredScene(g,meta,canvas),scene=built.scene;scene.updateMatrixWorld(true);
const oldScene=new THREE.Scene(),oldMaterials=before.createDressingMaterials(THREE,plan,{canvasFactory:canvas});
for(const p of g.primitives){const m=new THREE.Mesh(new THREE.BoxGeometry(...p.size),oldMaterials.surface(p.role,g.rooms.find(r=>p.id.startsWith(r.id+'_'))?.id));m.name=p.id;m.position.set(...p.position);oldScene.add(m);}before.addRoomDressing(THREE,oldScene,g,plan,oldMaterials);oldScene.updateMatrixWorld(true);
function cast(s,origin,direction,far=100){return new THREE.Raycaster(new THREE.Vector3(...origin),new THREE.Vector3(...direction).normalize(),.001,far).intersectObject(s,true);}
function point(normal,y,along){const p=[0,y,0];p[vp.axis]=vp.coordinate+vp.sign*normal;p[vp.along]=along;return p;}
const outward=[0,0,0];outward[vp.axis]=vp.sign;
test('Saved observation role selects a genuine unshared exterior bay',()=>{assert.equal(vp.room_id,'observation');assert.equal(vp.wall_id,'observation_east_0');assert.ok(vp.width>=1.3);const rib=plan.colliders.find(c=>c.id==='rib_observation_east_0');assert.ok(vp.center+vp.width/2<rib.min[vp.along]||vp.center-vp.width/2>rib.max[vp.along],'Window intersects existing rib');assert.equal(vp.nontraversable,true);return vp;});
test('Normal eye-height and varied aperture rays reach glazing with no opaque wall/panel/rib occlusion',()=>{
 const rows=[];for(const yf of [.25,.5,.75])for(const af of [-.3,0,.3]){
  const origin=point(-1.1,vp.bottom+(vp.top-vp.bottom)*yf,vp.center+vp.width*af),hits=cast(scene,origin,outward,3),oldHits=cast(oldScene,origin,outward,3);
  assert.ok(oldHits.length);assert.ok(!oldHits[0].object.material.transparent);assert.ok(hits.length);assert.equal(hits[0].object.userData.viewport_glazing,true,hits.map(h=>h.object.name).join(','));
  assert.ok(hits.every(h=>h.object.userData.viewport_glazing),'Opaque filler still spans the aperture');rows.push({origin,before:oldHits[0].object.name,after:hits[0].object.name});
 }
 const eye=point(-1.1,1.56,vp.center);assert.equal(cast(scene,eye,outward,3)[0].object.userData.viewport_glazing,true);return rows;
});
test('Camera through the real aperture sees the same shared original terrain geometry',()=>{
 const terrain=scene.getObjectByName('original_procedural_exterior_observation');assert.ok(terrain);assert.equal(terrain.userData.measured_terrain,false);
 const origin=point(-1.1,1.56,vp.center),direction=[...outward];direction[1]=-.045;const hits=cast(scene,origin,direction,100);
 assert.equal(hits[0].object.userData.viewport_glazing,true);const opaque=hits.find(h=>!h.object.material.transparent);assert.equal(opaque?.object,terrain);assert.ok(opaque.distance>10);return {terrain_hit_distance:opaque.distance,terrain_vertices:terrain.geometry.attributes.position.count,terrain_triangles:terrain.geometry.index.count/3};
});
test('Structural surround retains exact original full bounds and linked solid safety collider',()=>{
 const assembly=built.semantic.get('node:'+wall.id),b=new THREE.Box3().setFromObject(assembly,true);for(let i=0;i<3;i++){assert.ok(Math.abs(b.min.getComponent(i)-collider.min[i])<1e-6);assert.ok(Math.abs(b.max.getComponent(i)-collider.max[i])<1e-6);}
 const linked=meta.colliders.find(c=>c.owner_node_id==='node:'+wall.id);assert.ok(linked);assert.ok(assembly.userData.collider_ids.includes(linked.id));assert.ok(assembly.isGroup);return {owner_node_id:linked.owner_node_id,bounds:{min:b.min.toArray(),max:b.max.toArray()},collider_unchanged:true};
});
test('Recess has visible depth and opaque side/header/sill enclosure',()=>{
 const glass=scene.getObjectByName(wall.id+'_glazing'),near=vp.coordinate-vp.sign*vp.thickness/2,glassCenter=glass.getWorldPosition(new THREE.Vector3()).getComponent(vp.axis);assert.ok(Math.abs(glassCenter-near)>.08);
 const origin=point(-.1,(vp.bottom+vp.top)/2,vp.center);for(const [a,v] of [[vp.along,1],[vp.along,-1],[1,1],[1,-1]]){const direction=[0,0,0];direction[a]=v;const inside=point(.005,(vp.bottom+vp.top)/2,vp.center);const hits=cast(scene,inside,direction,2);assert.ok(hits.some(h=>!h.object.material.transparent));}
 return {recess_depth_metres:Math.abs(glassCenter-near),glass_opacity:glass.material.opacity};
});
test('Normal walker cannot pass through the glass despite the visible opening',()=>{
 const a=point(-.8,0,vp.center),b=point(-.01,0,vp.center),route={id:'viewport_block',avatar_radius:.34,avatar_height:1.68,points:[a,b]};
 const result=checkHorizontalRoute(route,{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:g.colliders});assert.equal(result.status,'blocked');return result;
});
test('All original equipment, door definitions, pairing, plan colliders and scene metadata remain unchanged',()=>{
 assert.equal(JSON.stringify(g),unchanged);assert.equal(JSON.stringify(plan),planUnchanged);assert.deepEqual(built.doors.definitions(),d.definitions());assert.deepEqual(built.doors.interlocks(),d.interlocks());
 for(const p of g.primitives.filter(p=>p.id!==wall.id)){const actual=built.semantic.get('node:'+p.id);assert.ok(actual.isMesh);assert.deepEqual(Array.from(actual.geometry.attributes.position.array),Array.from(new THREE.BoxGeometry(...p.size).attributes.position.array));assert.deepEqual(actual.position.toArray(),p.position);}
 const oldDressing=new THREE.Scene(),nowDressing=new THREE.Scene();before.addRoomDressing(THREE,oldDressing,g,plan,oldMaterials);detail.addRoomDressing(THREE,nowDressing,g,plan,detail.createDressingMaterials(THREE,plan,{canvasFactory:canvas}));
 function signature(o){const rows=[];o.traverse(m=>{if(m.isMesh)rows.push([m.name,m.position.toArray(),m.rotation.toArray(),Array.from(m.geometry.attributes.position.array)]);});return sha(JSON.stringify(rows));}
 for(const o of plan.objects)assert.equal(signature(oldDressing.getObjectByName(o.id)),signature(nowDressing.getObjectByName(o.id)));
 return {equipment:plan.objects.length,original_colliders:g.colliders.length,extra_colliders:plan.colliders.length,doors:d.definitions().length};
});
test('Viewer uses the exact shared authored builder, not an independent window approximation',()=>{
 const module=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',import.meta.url),'utf8').replaceAll('export function ','function ').trim();
 const viewer=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');assert.equal(viewer.split(module).length-1,1);assert.ok(viewer.includes('scene.add(createStructuralPrimitive(THREE,primitive,material,viewport,dressingMaterials))'));assert.ok(viewer.includes('addObservationExterior(THREE,scene,viewport)'));return true;
});
test('Window eligibility rejects missing solid collider, unsupported role and enclosed observation room',()=>{
 const missing=structuredClone(g);missing.colliders=missing.colliders.filter(c=>!c.id.startsWith('observation_'));assert.equal(detail.planObservationViewport(missing,plan),null);
 const p=structuredClone(plan);p.roomStyles.observation.role='laboratory';assert.equal(detail.planObservationViewport(g,p),null);
 const enclosed=structuredClone(g);enclosed.rooms.push({id:'enclosing',x:2,z:6,width:5,depth:6,floor_y:0,height:3});assert.equal(detail.planObservationViewport(enclosed,plan),null);
 return true;
});
test('No observation style means byte-identical structural primitive meshes and no exterior',()=>{
 const p=structuredClone(plan);p.enabled=false;assert.equal(detail.planObservationViewport(g,p),null);const s=new THREE.Scene();assert.equal(detail.addObservationExterior(THREE,s,null),null);assert.equal(s.children.length,0);
 const out=detail.createStructuralPrimitive(THREE,wall,oldMaterials.basic.metal,null,oldMaterials);assert.ok(out.isMesh);assert.deepEqual(Array.from(out.geometry.attributes.position.array),Array.from(new THREE.BoxGeometry(...wall.size).attributes.position.array));return true;
});
test('Renaming the observation room preserves geometric feature without requiring Mars title or fixed id',()=>{
 const renamed=structuredClone(g),p=structuredClone(plan),rename=s=>s.replaceAll('observation','lookout');renamed.title='Original research habitat';
 const r=renamed.rooms.find(r=>r.id==='observation');r.id='lookout';for(const item of [...renamed.primitives,...renamed.colliders])item.id=rename(item.id);
 p.roomStyles.lookout=p.roomStyles.observation;delete p.roomStyles.observation;assert.equal(detail.planObservationViewport(renamed,p)?.room_id,'lookout');return true;
});
test('Every new position/normal/color is finite; external terrain normals face upward',()=>{
 let meshes=0;scene.traverse(o=>{if(!o.isMesh)return;meshes++;for(const attr of Object.values(o.geometry.attributes))assert.ok(Array.from(attr.array).every(Number.isFinite));});const terrain=scene.getObjectByName('original_procedural_exterior_observation');const normal=terrain.geometry.attributes.normal;for(let i=0;i<normal.count;i++)assert.ok(normal.getY(i)>.8);return {meshes};
});
const report={status:'053_CPU_GEOMETRY_CONTRACT_PASS',checks,source_geometry_sha256:sha(raw),viewport:vp,world_or_source_modified:false,visual_review:false};
fs.writeFileSync(new URL('./GEOMETRY-RESULT.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,checks:checks.length,viewport:vp}));
