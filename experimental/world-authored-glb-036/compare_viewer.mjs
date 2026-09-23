// Execute only a hash-pinned static assembly block from the installed viewer.
// Never call start(), animate(), WebGLRenderer, browser events or owner writes.
import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import * as THREE from './vendor/three/build/three.module.js';
import {installCpuCanvas} from './cpu_canvas.mjs';
import {buildAuthoredScene} from './authored_scene.mjs';
import {createDressingMaterials,addRoomDressing} from './source/room_dressing_render.mjs';
import {buildRoomDressing} from './source/room_dressing_plan.mjs';
import {createWalkController,createDoorSystem} from './source/walk_controller.mjs';
const req=JSON.parse(fs.readFileSync(0,'utf8')),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const viewerRaw=fs.readFileSync(req.viewer),viewer=viewerRaw.toString('utf8');
assert.equal(hash(viewerRaw),'e6f101d016cd40b923c678f3db39b1ec7ec50b1c44684f255bcd1efb8b9fcfda');
assert.ok(viewer.includes(fs.readFileSync(new URL('./source/room_dressing_render.mjs',import.meta.url),'utf8').replaceAll('export function','function')));
const staticBlock=viewer.slice(viewer.indexOf('  const dressingMaterials=createDressingMaterials'),viewer.indexOf('  const keys=new Set();'));
const poseBlock=viewer.slice(viewer.indexOf('    for(const door of controller.doorStates()){'),viewer.indexOf('    const nearby=state.nearbyDoor'));
assert.ok(staticBlock.length>3000&&poseBlock.length>300);
const {canvasFactory}=installCpuCanvas(req.canvasModule,req.fontPaths),geometry=req.geometry;
const dressing=buildRoomDressing(geometry,createDoorSystem(geometry).assemblies()),controller=createWalkController(geometry,{extraColliders:dressing.colliders});
const baseline=new THREE.Scene();
new Function('THREE','geometry','dressing','controller','scene','createDressingMaterials','addRoomDressing',staticBlock+'\n'+poseBlock)(THREE,geometry,dressing,controller,baseline,createDressingMaterials,addRoomDressing);
const candidate=buildAuthoredScene(geometry,req.metadata,canvasFactory).scene;
const round=a=>a.map(n=>Math.round(n*1e8)/1e8);
function material(m){return {color:round(m.color.toArray()),emissive:round(m.emissive.toArray()),emissiveIntensity:m.emissiveIntensity,roughness:m.roughness,metalness:m.metalness,transparent:m.transparent,opacity:m.opacity,depthWrite:m.depthWrite,polygonOffset:m.polygonOffset,polygonOffsetFactor:m.polygonOffsetFactor,polygonOffsetUnits:m.polygonOffsetUnits,
  map:m.map?{pixels:hash(m.map.image.getContext('2d').getImageData(0,0,m.map.image.width,m.map.image.height).data),width:m.map.image.width,height:m.map.image.height,repeat:m.map.repeat.toArray(),wrapS:m.map.wrapS,wrapT:m.map.wrapT,colorSpace:m.map.colorSpace}:null};}
function summary(scene){
  scene.updateMatrixWorld(true);const rows=[],materials=new Set(),lights=[];
  scene.traverse(o=>{if(o.isPointLight)lights.push({position:round(o.getWorldPosition(new THREE.Vector3()).toArray()),color:round(o.color.toArray()),intensity:o.intensity,distance:o.distance,decay:o.decay});if(!o.isMesh)return;
    const box=new THREE.Box3().setFromObject(o,true),mat=material(o.material),matKey=JSON.stringify(mat);materials.add(matKey);
    const attrs=Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,v])=>[k,hash(Buffer.from(v.array.buffer,v.array.byteOffset,v.array.byteLength))]));
    rows.push({signature:JSON.stringify({matrix:round(o.matrixWorld.elements),attrs,index:hash(Buffer.from(o.geometry.index.array.buffer)),material:mat}),bounds:[...box.min.toArray(),...box.max.toArray()],material:matKey});});
  const rooms=geometry.rooms.map(r=>{const min=[r.x,r.floor_y,r.z],max=[r.x+r.width,r.floor_y+r.height,r.z+r.depth];
    const matches=rows.filter(row=>{const center=[0,1,2].map(i=>(row.bounds[i]+row.bounds[i+3])/2);return center.every((v,i)=>v>=min[i]-1e-7&&v<=max[i]+1e-7);});
    return {room_id:r.id,room_bounds:[...min,...max],meshes_with_center_inside:matches.length,distinct_material_parameters:new Set(matches.map(row=>row.material)).size,
      mesh_bounds:matches.length?[...([0,1,2].map(i=>Math.min(...matches.map(row=>row.bounds[i])))),...([3,4,5].map(i=>Math.max(...matches.map(row=>row.bounds[i]))))]:null};});
  return {meshes:rows.length,distinct_material_parameters:materials.size,signatures:rows.map(r=>r.signature).sort(),rooms,point_lights:lights.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))};
}
const a=summary(baseline),b=summary(candidate);assert.deepEqual(b,a,'Authored mesh/material/room assignment differs from installed viewer construction');
const report={status:'EXACT_PINNED_VIEWER_MESH_BASELINE_PASS',installed_viewer_sha256:hash(viewerRaw),extracted_static_block_sha256:hash(staticBlock),extracted_pose_block_sha256:hash(poseBlock),authored_renderer_embedded_exact:true,mesh_count:a.meshes,distinct_material_parameters:a.distinct_material_parameters,point_light_count:a.point_lights.length,room_comparisons:a.rooms,mesh_multiset_sha256:hash(JSON.stringify(a.signatures)),tolerance_world_matrix:1e-8,
  baseline_scope:'Exact installed static assembly and closed-door pose blocks; no WebGL, animation loop or UI. Mesh attribute/index bytes, world matrices, material values and texture pixels compared. Room counts use mesh centers and can include shared boundary meshes.',appearance_approved:false};
process.stdout.write(JSON.stringify(report,null,2));
