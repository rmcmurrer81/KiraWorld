import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import * as THREE from './vendor/three/build/three.module.js';
import {GLTFExporter} from './vendor/three/examples/jsm/exporters/GLTFExporter.js';
import {GLTFLoader} from './vendor/three/examples/jsm/loaders/GLTFLoader.js';
import {installCpuCanvas} from './cpu_canvas.mjs';
import {buildAuthoredScene} from './authored_scene.mjs';
import {buildRoomDressing} from './source/room_dressing_plan.mjs';
import {createDoorSystem} from './source/walk_controller.mjs';
import {exportSceneMetadata,canonicalSceneMetadata} from './source/scene_metadata.mjs';

const req=JSON.parse(fs.readFileSync(0,'utf8'));
assert.ok(req.options&&!req.metadata,'Only source-bound metadata generation is accepted');
const definedDoors=createDoorSystem(req.geometry),definedPlan=buildRoomDressing(req.geometry,definedDoors.assemblies());
const described=exportSceneMetadata(req.geometry,definedPlan,definedDoors.definitions(),{...req.options,doorInterlocks:definedDoors.interlocks()});
req.metadata={...described,provenance:{...described.provenance,binding_verification:'actual_bound_bytes_verified_by_package_writer',
 source_chain_verification:'geometry_to_blueprint_to_research_packet_and_cache_digests',factual_or_visual_approval:false}};
const {canvasFactory}=installCpuCanvas(req.canvasModule,req.fontPaths);
assert.equal(THREE.REVISION,'180');
const built=buildAuthoredScene(req.geometry,req.metadata,canvasFactory);
const {scene,doors,plan}=built;
const recreated=exportSceneMetadata(req.geometry,plan,doors.definitions(),{sceneId:req.metadata.scene_id,sourceDigests:req.metadata.provenance.source_digests,doorInterlocks:doors.interlocks()});
assert.equal(canonicalSceneMetadata({...req.metadata,provenance:recreated.provenance}),canonicalSceneMetadata(recreated),'034 sidecar is not this exact authored scene');
const close=(a,b,tol=2e-6)=>{assert.equal(a.length,b.length);for(let i=0;i<a.length;i++)assert.ok(Math.abs(a[i]-b[i])<tol,`Numeric mismatch ${a[i]} / ${b[i]}`);};
const bounds=obj=>{const b=new THREE.Box3().setFromObject(obj,true);return [...b.min.toArray(),...b.max.toArray()];};
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const arraysEqual=(a,b)=>{assert.equal(a.length,b.length);for(let i=0;i<a.length;i++)assert.equal(a[i],b[i]);};
function pixelDigest(image,flip=false){const canvas=canvasFactory();canvas.width=image.width;canvas.height=image.height;const ctx=canvas.getContext('2d');if(flip){ctx.translate(0,image.height);ctx.scale(1,-1);}ctx.drawImage(image,0,0);return digest(ctx.getImageData(0,0,image.width,image.height).data);}
function inventory(root){const map=new Map();root.updateMatrixWorld(true);root.traverse(object=>{if(object.userData.export_id)map.set(object.userData.export_id,object);});return map;}
// Test hinge parent hierarchy against the actual controller at closed, halfway,
// and fully open. Safe interaction positions come from the opposite room side.
const doorEvidence=[];
for(const def of doors.definitions()){
  const portal=req.geometry.portals.find(p=>p.id===def.id),normal=portal.axis==='x'?0:2;
  const middle=normal===0?[portal.coordinate,def.hinge[1],portal.center]:[portal.center,def.hinge[1],portal.coordinate];
  const sweep=def.swingBounds;let feet=null;
  for(const sign of [-1,1]){const trial=[...middle];trial[normal]+=sign*1.05;
    if(!(trial[normal]+.34>=sweep.min[normal]&&trial[normal]-.34<=sweep.max[normal])){feet=trial;break;}}
  assert.ok(feet);const originalFrames=def.frames.map(f=>bounds(built.semantic.get('node:'+f.id)));
  const samples=[];
  for(const step of [0,4,8]){
    if(step===4){assert.ok(doors.toggle(def.id,feet).ok);for(let i=0;i<4;i++)doors.advance(.05,feet);}
    if(step===8)for(let i=0;i<4;i++)doors.advance(.05,feet);
    const actual=doors.all().find(d=>d.id===def.id);built.hinges.get(def.id).rotation.y=actual.angle;scene.updateMatrixWorld(true);
    const leaf=built.leafMeshes.get(def.id);close(leaf.getWorldPosition(new THREE.Vector3()).toArray(),actual.center);
    close(bounds(leaf),[...actual.collider.min,...actual.collider.max]);
    def.frames.forEach((f,i)=>close(bounds(built.semantic.get('node:'+f.id)),originalFrames[i]));
    samples.push({angle:actual.angle,center:actual.center});
  }
  close([samples[1].angle],[def.openAngle/2]);close([samples[2].angle],[def.openAngle]);
  // Close the real controller before sampling the next door. Keeping the prior
  // leaf open would correctly prevent its airlock peer from opening.
  assert.ok(doors.toggle(def.id,feet).ok);for(let i=0;i<8;i++)doors.advance(.05,feet);
  assert.equal(doors.all().find(d=>d.id===def.id).state,'closed');
  built.hinges.get(def.id).rotation.y=0;doorEvidence.push({door_id:def.id,samples,frames_static:true,closed_after_sample:true});
}
scene.updateMatrixWorld(true);
const before=inventory(scene),beforeBounds=bounds(scene);
const uniqueMaterials=new Set(),uniqueTextures=new Set();let meshCount=0;
for(const object of before.values())if(object.isMesh){meshCount++;const ms=Array.isArray(object.material)?object.material:[object.material];for(const m of ms){uniqueMaterials.add(m);if(m.map){assert.equal(m.map.colorSpace,THREE.SRGBColorSpace);assert.ok(m.map.image.width>0);uniqueTextures.add(m.map);}}}
const glb=await new GLTFExporter().parseAsync(scene,{binary:true,onlyVisible:true});
assert.ok(glb instanceof ArrayBuffer);
const binary=Buffer.from(glb),jsonLength=binary.readUInt32LE(12),gltf=JSON.parse(binary.subarray(20,20+jsonLength).toString('utf8'));
assert.equal(gltf.asset.version,'2.0');assert.ok(gltf.images.length>0);assert.ok(gltf.images.every(i=>i.mimeType==='image/png'&&Number.isInteger(i.bufferView)&&!i.uri));
assert.ok(gltf.extensionsUsed.includes('KHR_texture_transform'));assert.ok(gltf.extensionsUsed.includes('KHR_lights_punctual'));
const imported=await new GLTFLoader().parseAsync(glb,''),after=inventory(imported.scene);
assert.equal(before.size,after.size,'Object count changed in importer');close(bounds(imported.scene),beforeBounds);
let attributeComparisons=0,textureComparisons=0,materialComparisons=0,lightComparisons=0;
const checkedMaterials=new Set(),checkedTexturePairs=new Set();
for(const [id,original] of before){
  const restored=after.get(id);assert.ok(restored,'Object lost during import '+id);close(restored.matrixWorld.elements,original.matrixWorld.elements);
  const importedData={...restored.userData};if('name' in importedData){assert.equal(importedData.name,original.name);delete importedData.name;}
  assert.deepEqual(importedData,original.userData,'Semantic/collider identity differs');
  if(original.isLight){assert.equal(restored.type,original.type);close(restored.color.toArray(),original.color.toArray());close([restored.intensity],[original.intensity]);
    if(original.isPointLight)close([restored.decay,restored.distance],[original.decay,original.distance]);
    if(original.isDirectionalLight){const direction=l=>l.target.getWorldPosition(new THREE.Vector3()).sub(l.getWorldPosition(new THREE.Vector3())).normalize().toArray();close(direction(restored),direction(original));}lightComparisons++;}
  if(!original.isMesh)continue;
  assert.ok(restored.isMesh);assert.deepEqual(Object.keys(restored.geometry.attributes).sort(),Object.keys(original.geometry.attributes).sort());
  for(const key of Object.keys(original.geometry.attributes)){arraysEqual(original.geometry.attributes[key].array,restored.geometry.attributes[key].array);attributeComparisons++;}
  arraysEqual(original.geometry.index.array,restored.geometry.index.array);close(bounds(original),bounds(restored));
  const a=original.material,b=restored.material;assert.ok(!Array.isArray(a)&&!Array.isArray(b));
  if(!checkedMaterials.has(a.uuid)){checkedMaterials.add(a.uuid);materialComparisons++;
    close(a.color.toArray(),b.color.toArray());close([a.roughness,a.metalness,a.opacity],[b.roughness,b.metalness,b.opacity]);assert.equal(a.transparent,b.transparent);
    const emitted=m=>m.emissive.toArray().map(v=>v*m.emissiveIntensity);close(emitted(a),emitted(b));}
  assert.equal(!!a.map,!!b.map,'Texture omitted');
  if(a.map&&!checkedTexturePairs.has(a.map.uuid)){
    checkedTexturePairs.add(a.map.uuid);textureComparisons++;assert.equal(a.map.colorSpace,b.map.colorSpace);assert.equal(a.map.wrapS,b.map.wrapS);assert.equal(a.map.wrapT,b.map.wrapT);
    close(a.map.repeat.toArray(),b.map.repeat.toArray());close(a.map.offset.toArray(),b.map.offset.toArray());close([a.map.rotation],[b.map.rotation]);
    assert.equal(a.map.image.width,b.map.image.width);assert.equal(a.map.image.height,b.map.image.height);assert.equal(pixelDigest(a.map.image,a.map.flipY!==b.map.flipY),pixelDigest(b.map.image),'Effective texture pixels changed in PNG/import');
  }
}
const roundtripSemantic=new Map([...after.values()].filter(o=>o.userData.metadata_node_id).map(o=>[o.userData.metadata_node_id,o]));
const policyObjects=[...after.values()].filter(o=>Array.isArray(o.userData.airlock_pairs));
assert.equal(policyObjects.length,1);assert.deepEqual(policyObjects[0].userData.airlock_pairs,req.metadata.airlock_pairs);
for(const pair of req.metadata.airlock_pairs){
  assert.equal(pair.leaf_node_ids.length,2);assert.equal(new Set(pair.leaf_node_ids).size,2);
  for(let i=0;i<2;i++){
    const leaf=roundtripSemantic.get(pair.leaf_node_ids[i]),pivot=leaf?.parent?.parent;
    assert.ok(leaf&&pivot);assert.equal(pivot.userData.door_id,pair.door_ids[i]);assert.ok(pivot.userData.airlock_pair_ids.includes(pair.id));
  }
}
for(const c of req.metadata.colliders){assert.ok(roundtripSemantic.get(c.owner_node_id)?.userData.collider_ids.includes(c.id),'Collider link lost');}
for(const room of req.metadata.rooms){const restored=[...after.values()].find(o=>o.userData.room_id===room.id);assert.ok(restored);assert.deepEqual(restored.userData.bounds,room.bounds);}
for(const d of req.metadata.doors){const pivot=[...after.values()].find(o=>o.userData.door_id===d.id),leaf=roundtripSemantic.get(d.leaf_node_id);assert.ok(pivot&&leaf);assert.equal(leaf.parent.parent,pivot);close(pivot.position.toArray(),d.hinge.position);close(leaf.parent.position.toArray(),d.hinge.leaf_local_center);
  for(const angle of [0,d.hinge.open_angle/2,d.hinge.open_angle]){pivot.rotation.y=angle;imported.scene.updateMatrixWorld(true);built.hinges.get(d.portal_id).rotation.y=angle;scene.updateMatrixWorld(true);close(bounds(leaf),bounds(built.leafMeshes.get(d.portal_id)));}
  pivot.rotation.y=0;built.hinges.get(d.portal_id).rotation.y=0;
}
const report={status:'CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS',three_revision:THREE.REVISION,glb_sha256:digest(binary),glb_bytes:binary.length,
  counts:{objects:before.size,meshes:meshCount,materials:uniqueMaterials.size,textures:uniqueTextures.size,embedded_pngs:gltf.images.length,rooms:req.metadata.rooms.length,semantic_nodes:roundtripSemantic.size,colliders:req.metadata.colliders.length,doors:doorEvidence.length},
  scene_bounds:beforeBounds,checks:{geometry_attributes_exact:attributeComparisons,index_arrays_exact:meshCount,material_parameter_pairs:materialComparisons,texture_effective_pixels_repeat_wrap_colorspace:textureComparisons,punctual_light_parameters_and_direction:lightComparisons,door_controller_samples:doorEvidence,importer_door_poses:18,all_collider_links:true,room_bounds_preserved:true,airlock_pair_metadata_preserved:true,airlock_pairs:req.metadata.airlock_pairs},
  extensions:gltf.extensionsUsed,webgl_gpu_browser_calls:0,installed:false,visual_or_owner_approval:false,
  limits:['No engine-native interaction/collision implementation or VR adapter.','CPU font rasterization is not browser-pixel-identical.','Hemisphere fill, background, ACES tone mapping/exposure, polygon offset, depthWrite and dynamic indicator colors are not glTF appearance guarantees.','Static equipment remains procedural. No pressure, science or medical simulation.']};
fs.writeFileSync(path.join(req.output,'scene.json'),canonicalSceneMetadata(req.metadata)+'\n',{flag:'wx'});
fs.writeFileSync(path.join(req.output,'scene.glb'),binary,{flag:'wx'});
fs.writeFileSync(path.join(req.output,'ROUNDTRIP.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({status:report.status,sha256:report.glb_sha256,bytes:report.glb_bytes,counts:report.counts}));
