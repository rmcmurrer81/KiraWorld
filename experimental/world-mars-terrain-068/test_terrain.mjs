import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import * as THREE from '../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {GLTFExporter} from '../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/vendor/three/examples/jsm/exporters/GLTFExporter.js';
import {GLTFLoader} from '../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/vendor/three/examples/jsm/loaders/GLTFLoader.js';
import * as before from '../world-mars-displays-067/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import * as after from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import {buildRoomDressing} from '../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem} from '../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {exportSceneMetadata} from '../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';

globalThis.fetch=()=>{throw new Error('No network in CPU tests');};
const digest=b=>createHash('sha256').update(b).digest('hex');
const g=JSON.parse(readFileSync(new URL('./synthetic-layout.json',import.meta.url),'utf8'));
assert.equal(g.research_packet_sha256,'2'.repeat(64));assert.match(g.title,/Synthetic/);
const p={contract:'bound_original_exterior_presentation_v1',setting:'mars_surface',reason:'explicit_original_mars_base_request',source:{job_id:'world_research_'+'1'.repeat(20),brief_sha256:'1'.repeat(64),request_sha256:'3'.repeat(64),research_packet_sha256:g.research_packet_sha256}};
const doors=createDoorSystem(g),plan=buildRoomDressing(g,doors.assemblies()),vp=after.planObservationViewport(g,plan);
assert.ok(vp);
const clone=x=>structuredClone(x),norm=s=>s.replaceAll('export function ','function ').trim();
const viewer=readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');
const oldViewer=readFileSync(new URL('./before/viewer.mjs',import.meta.url),'utf8');
const inlineSource=viewer.slice(viewer.indexOf('function planObservationViewport('),viewer.indexOf('async function start(){'));
const inline=await import('data:text/javascript;base64,'+Buffer.from(inlineSource+'\nexport {buildOriginalMarsExterior,addObservationExterior};').toString('base64'));
const exterior=(module=after,view=vp,geometry=g,presentation=p)=>{const scene=new THREE.Scene();return {scene,root:module.addObservationExterior(THREE,scene,view,presentation,geometry)};};
const isExterior=o=>o.userData.kind==='procedural_exterior_scenery'||(o.parent&&isExterior(o.parent));
function signature(root,skipExterior=false){const rows=[];root.updateMatrixWorld(true);root.traverse(o=>{if(!o.isMesh||(skipExterior&&isExterior(o)))return;rows.push({name:/^object_\d+$/.test(o.name)?'unnamed_export_bookkeeping':o.name,transform:o.matrixWorld.toArray(),attrs:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])),indices:Array.from(o.geometry.index.array),material:{color:o.material.color.toArray(),emissive:o.material.emissive.toArray(),intensity:o.material.emissiveIntensity,roughness:o.material.roughness,metalness:o.material.metalness,side:o.material.side}});});return digest(JSON.stringify(rows));}
function counts(root){let meshes=0,vertices=0,triangles=0;root.traverse(o=>{if(o.isMesh){meshes++;vertices+=o.geometry.attributes.position.count;triangles+=o.geometry.index.count/3;}});return {meshes,vertices,triangles};}
function dispose(root){root.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});}
function canvas(){const ctx=new Proxy({},{get:(o,k)=>o[k]??(()=>{}),set:(o,k,v)=>(o[k]=v,true)});return {width:0,height:0,getContext:()=>ctx};}
function localPoint(view,d,a,y){const v=new THREE.Vector3();v.setComponent(view.axis,view.coordinate+view.sign*d);v.setComponent(view.along,view.center+a);v.y=y;return v;}

test('source gate remains exact and invalid/unrequested scenery adds nothing',()=>{
  const invalid=[null,{...p,setting:'earth'},{...p,reason:'guessed_from_name'},{...p,contract:'unknown'}];
  for(const patch of [{research_packet_sha256:'0'.repeat(64)},{brief_sha256:'bad'},{request_sha256:null},{job_id:'world_research_wrong'}])invalid.push({...p,source:{...p.source,...patch}});
  for(const value of invalid){const r=exterior(after,vp,g,value);assert.equal(r.root,null);assert.equal(r.scene.children.length,0);}
  assert.equal(exterior(after,null).root,null);
});

test('window, displays, rooms, lights, camera and source data retain their original code and values',()=>{
  for(const name of ['planObservationViewport','viewportWallPieces','createStructuralPrimitive','createMarsDisplayData','paintMarsDisplay','createDressingMaterials','addRoomDressing'])assert.equal(after[name].toString(),before[name].toString(),name);
  assert.equal(viewer.slice(viewer.indexOf('async function start(){')),oldViewer.slice(oldViewer.indexOf('async function start(){')));
  const original=JSON.stringify(g),r=exterior();assert.equal(JSON.stringify(g),original);assert.deepEqual(vp,before.planObservationViewport(g,plan));dispose(r.root);
});

test('deterministic shared viewer/export geometry and materials are identical',()=>{
  const helper=readFileSync(new URL('./mars_exterior.mjs',import.meta.url),'utf8');
  assert.ok(norm(viewer).includes(norm(helper)));
  for(const name of ['buildOriginalMarsExterior','addObservationExterior'])assert.equal(norm(inline[name].toString()),norm(after[name].toString()));
  const a=exterior(),b=exterior(),c=exterior(inline);assert.equal(signature(a.root),signature(b.root));assert.equal(signature(a.root),signature(c.root));for(const s of [a,b,c])dispose(s.root);
});

test('explicit mesh/vertex/triangle budget and real near-rock scale',()=>{
  const {root}=exterior(),n=counts(root);assert.ok(n.meshes<=24&&n.vertices<12000&&n.triangles<20000,JSON.stringify(n));
  const rocks=root.children.filter(m=>m.userData.exterior_part==='weathered_rock');assert.ok(rocks.length>=12&&rocks.length<=18);
  const shapes=new Set();for(const rock of rocks){const b=new THREE.Box3().setFromObject(rock,true),s=b.getSize(new THREE.Vector3());assert.ok(s.y>.06&&s.y<.85);assert.ok(s.x<1.8&&s.z<1.8);shapes.add(digest(Buffer.from(rock.geometry.attributes.position.array.buffer)));}
  assert.equal(shapes.size,rocks.length,'No repeated rock mesh');assert.equal(root.userData.measured_terrain,false);assert.equal(root.userData.nontraversable,true);dispose(root);
});

test('all four outward orientations and translated floor stay outside wall within camera far plane',()=>{
  for(const axis of [0,2])for(const sign of [-1,1]){
    const view={...vp,axis,along:axis===0?2:0,sign,coordinate:14,center:-23};
    const geometry=clone(g);geometry.rooms=geometry.rooms.map(r=>({...r,floor_y:9}));
    const {root}=exterior(after,view,geometry);let closest=Infinity,furthest=0;
    root.traverse(o=>{if(!o.isMesh)return;const a=o.geometry.attributes.position;for(let i=0;i<a.count;i++){const v=new THREE.Vector3().fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld);const d=(v.getComponent(axis)-view.coordinate)*sign;closest=Math.min(closest,d);furthest=Math.max(furthest,v.distanceTo(localPoint(view,-2,0,10.6)));assert.ok(Number.isFinite(v.x)&&Number.isFinite(v.y)&&Number.isFinite(v.z));}});
    assert.ok(closest>view.thickness/2+.05,closest);assert.ok(furthest<225,furthest);
    const terrain=root.children.find(o=>o.userData.exterior_part==='regolith_and_ridges');assert.ok(new THREE.Box3().setFromObject(terrain).min.y>8.5);dispose(root);
  }
});

test('new rock bounds never overlap the authored rooms and no colliders are created',()=>{
  const original=JSON.stringify(g.colliders),{root}=exterior();
  for(const rock of root.children.filter(o=>o.userData.exterior_part==='weathered_rock')){const b=new THREE.Box3().setFromObject(rock);for(const room of g.rooms)assert.ok(b.max.x<room.x||b.min.x>room.x+room.width||b.max.z<room.z||b.min.z>room.z+room.depth,rock.name);assert.equal(rock.userData.collider,undefined);}
  assert.equal(JSON.stringify(g.colliders),original);dispose(root);
});

test('actual unobstructed aperture rays reach near ground, rocks and curved sky at eye height',()=>{
  const {root}=exterior(),eye=localPoint(vp,-.7,0,1.6),ray=new THREE.Raycaster();
  function cast(direction){ray.set(eye,direction.normalize());return ray.intersectObject(root,true)[0];}
  for(const [pitch,part] of [[-.16,'regolith_and_ridges'],[.24,'dusty_sky_shell']]){const direction=localPoint(vp,1,0,1.6+pitch).sub(localPoint(vp,0,0,1.6));const hit=cast(direction);assert.ok(hit);assert.equal(hit.object.userData.exterior_part,part);}
  let seen=0;for(const rock of root.children.filter(o=>o.userData.exterior_part==='weathered_rock')){const target=new THREE.Box3().setFromObject(rock).getCenter(new THREE.Vector3()),dir=target.clone().sub(eye);const t=.7/((target.getComponent(vp.axis)-eye.getComponent(vp.axis))*vp.sign);const atWall=eye.clone().addScaledVector(dir,t);if(Math.abs(atWall.getComponent(vp.along)-vp.center)>vp.width/2-.08||atWall.y<vp.bottom+.08||atWall.y>vp.top-.08)continue;const hit=cast(dir);if(hit?.object===rock)seen++;}
  assert.ok(seen>=3,'At least three real rocks visible through aperture: '+seen);dispose(root);
});

test('terrain has distinct near-ground centimeter relief and irregular middle/distant crests',()=>{
  const {root}=exterior(),a=root.children.find(o=>o.userData.exterior_part==='regolith_and_ridges').geometry.attributes.position;
  const bands={near:[],middle:[],far:[]};for(let i=0;i<a.count;i++){const d=(a.getComponent(i,vp.axis)-vp.coordinate)*vp.sign,lat=a.getComponent(i,vp.along)-vp.center;if(Math.abs(lat)>20)continue;const b=d<8?'near':d>25&&d<50?'middle':d>60&&d<95?'far':null;if(b)bands[b].push(a.getY(i));}
  assert.ok(Math.max(...bands.near)<.4);assert.ok(Math.max(...bands.middle)>2);assert.ok(Math.max(...bands.far)>4);assert.ok(new Set(bands.far.map(v=>v.toFixed(2))).size>30);dispose(root);
});

test('entire authored habitat outside exterior stays geometrically unchanged with all collider/door links',async()=>{
  const b=new URL('../world-combined-followup-062/candidate/tools/world_builder_engine/layout_package_assets/',import.meta.url);
  const path=new URL('../world-mars-displays-067/candidate/tools/world_builder_engine/layout_package_assets/authored_scene.mjs',import.meta.url);
  const modules=[];for(const choice of ['before','after']){let source=readFileSync(path,'utf8');for(const rel of ['./vendor/three/build/three.module.js','./source/room_dressing_render.mjs','./source/room_dressing_plan.mjs','./source/walk_controller.mjs']){const url=rel.endsWith('room_dressing_render.mjs')?new URL(choice==='after'?'./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs':'../world-mars-displays-067/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',import.meta.url):new URL(rel,b);source=source.replace(`'${rel}'`,JSON.stringify(url.href));}modules.push(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')));}
  const metadata=exportSceneMetadata(g,plan,doors.definitions(),{sceneId:'synthetic_terrain_068',sourceDigests:{geometry:digest(JSON.stringify(g)),dressing_recipe:'4'.repeat(64),door_controller:'5'.repeat(64)},doorInterlocks:doors.interlocks()});
  const a=modules[0].buildAuthoredScene(g,metadata,canvas,p),bld=modules[1].buildAuthoredScene(g,metadata,canvas,p);
  assert.equal(signature(a.scene,true),signature(bld.scene,true));assert.deepEqual(a.plan,bld.plan);assert.deepEqual(a.doors.definitions(),bld.doors.definitions());assert.deepEqual([...a.semantic.keys()],[...bld.semantic.keys()]);
  for(const [id,o] of a.semantic)assert.deepEqual(o.userData.collider_ids,bld.semantic.get(id).userData.collider_ids);
  dispose(a.scene);dispose(bld.scene);
});

test('real texture-free GLB export/import preserves every exterior attribute, transform and standard material',async()=>{
  globalThis.FileReader=class{readAsArrayBuffer(blob){blob.arrayBuffer().then(result=>{this.result=result;this.onloadend?.();});}};
  const {scene,root}=exterior();const glb=await new GLTFExporter().parseAsync(scene,{binary:true,onlyVisible:true});assert.ok(glb instanceof ArrayBuffer);
  const imported=await new GLTFLoader().parseAsync(glb,''),restored=imported.scene.getObjectByName(root.name);assert.ok(restored);
  root.updateMatrixWorld(true);imported.scene.updateMatrixWorld(true);
  const near=(a,b)=>{assert.equal(a.length,b.length);for(let i=0;i<a.length;i++)assert.ok(Math.abs(a[i]-b[i])<2e-6,`${a[i]} != ${b[i]}`);};
  root.traverse(o=>{if(!o.isMesh)return;const r=restored.getObjectByName(o.name);assert.ok(r);near(o.matrixWorld.elements,r.matrixWorld.elements);assert.deepEqual(Object.keys(o.geometry.attributes),Object.keys(r.geometry.attributes));
    for(const key of Object.keys(o.geometry.attributes))assert.deepEqual(Array.from(o.geometry.attributes[key].array),Array.from(r.geometry.attributes[key].array),o.name+':'+key);
    assert.deepEqual(Array.from(o.geometry.index.array),Array.from(r.geometry.index.array));
    near(o.material.color.toArray(),r.material.color.toArray());near(o.material.emissive.toArray().map(v=>v*o.material.emissiveIntensity),r.material.emissive.toArray().map(v=>v*r.material.emissiveIntensity));near([o.material.roughness,o.material.metalness],[r.material.roughness,r.material.metalness]);assert.equal(o.material.side,r.material.side);
    const data={...r.userData};if('name' in data){assert.equal(data.name,o.name);delete data.name;}assert.deepEqual(data,o.userData);
  });
  assert.deepEqual(counts(restored),counts(root));const rootData={...restored.userData};if('name' in rootData){assert.equal(rootData.name,root.name);delete rootData.name;}assert.deepEqual(rootData,root.userData);
  const raw=Buffer.from(glb),n=raw.readUInt32LE(12),json=JSON.parse(raw.subarray(20,20+n).toString('utf8'));
  assert.equal(json.images,undefined);assert.equal(json.textures,undefined);assert.ok(!json.buffers.some(b=>b.uri));
  const out=process.env.TERRAIN_EVIDENCE_DIR;assert.ok(out,'Bounded runner supplies new owned output');
  writeFileSync(new URL('exterior-synthetic.glb','file:///'+out.replaceAll('\\','/')+'/'),raw,{flag:'wx'});
  writeFileSync(new URL('ROUNDTRIP.json','file:///'+out.replaceAll('\\','/')+'/'),JSON.stringify({status:'CPU_EXTERIOR_GLB_ROUNDTRIP_PASS',glb_sha256:digest(raw),bytes:raw.length,counts:counts(root),textures:0,external_uris:0,synthetic_fixture:true,whole_owner_package_export:false,visual_approval:false},null,2)+'\n',{flag:'wx'});
  dispose(scene);dispose(imported.scene);
});
