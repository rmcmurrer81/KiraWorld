import * as THREE from './vendor/three/build/three.module.js';
import {GLTFLoader} from './vendor/three/examples/jsm/loaders/GLTFLoader.js';
import {validateMetadata,require,createRuntime} from './runtime.mjs';
export const PACKAGE_FILES=['manifest.json','scene.json','scene.glb','ROUNDTRIP.json','README.txt'];
const decoder=new TextDecoder('utf-8',{fatal:true}),close=(a,b)=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<2e-6);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const MAX_FILE=16*1024*1024;
const sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(n=>n.toString(16).padStart(2,'0')).join('');
export async function verifyPackage(files){
 require(files instanceof Map&&files.size===PACKAGE_FILES.length&&PACKAGE_FILES.every(n=>files.has(n)),'Select exactly the five files from one exported package');
 for(const [name,bytes] of files)require(bytes instanceof Uint8Array&&bytes.byteLength>0&&bytes.byteLength<=MAX_FILE,'Invalid or oversized package file: '+name);
 const manifest=JSON.parse(decoder.decode(files.get('manifest.json')));
 require(manifest.contract==='authored_saved_layout_package_v2'&&manifest.status==='created','Unsupported or incomplete package');
 require(manifest.recipe_eligibility?.contract==='bounded_authored_habitat_export_v1','Unsupported authoring recipe');
 require(manifest.preview_controller_sha256==='0884cce50d33a66e4a974a76fc7a0a15947bcb776f130b1b0a81b43adef76791','Unsupported controller producer');
 require(same(Object.keys(manifest.files||{}).sort(),PACKAGE_FILES.filter(n=>n!=='manifest.json').sort()),'Unexpected file binding');
 for(const [name,pin] of Object.entries(manifest.files)){const b=files.get(name);require(b.byteLength===pin.bytes&&await sha(b)===pin.sha256,'Package hash mismatch: '+name);}
 const metadata=JSON.parse(decoder.decode(files.get('scene.json')));validateMetadata(metadata);
 require(manifest.scene_id===metadata.scene_id&&same(manifest.airlock_pair_policy,metadata.airlock_pairs),'Package and metadata identity/policy differ');
 const bytes=files.get('scene.glb'),view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 require(bytes.byteLength>=28&&view.getUint32(0,true)===0x46546c67&&view.getUint32(4,true)===2&&view.getUint32(8,true)===bytes.byteLength,'Invalid GLB header');
 const n=view.getUint32(12,true);require(view.getUint32(16,true)===0x4e4f534a&&n>0&&20+n<=bytes.byteLength,'Invalid GLB JSON chunk');
 const json=JSON.parse(decoder.decode(bytes.subarray(20,20+n)));
 require(json.asset?.version==='2.0'&&json.buffers?.length===1&&!json.buffers[0].uri,'Only one embedded GLB buffer is supported');
 require(json.images?.length>0&&json.images.every(i=>!i.uri&&Number.isInteger(i.bufferView)&&i.mimeType==='image/png'),'Only embedded PNG textures are supported');
 const supported=new Set(['KHR_texture_transform','KHR_lights_punctual','KHR_materials_emissive_strength']);
 require((json.extensionsUsed||[]).every(e=>supported.has(e)),'Unsupported GLB extension');
 require((json.meshes?.length||0)<=4096&&(json.nodes?.length||0)<=8192,'Oversized GLB scene');
 return {manifest,metadata,glb:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),glbJSON:json,manifestSha256:await sha(files.get('manifest.json'))};
}
export function bindScene(scene,metadata){
 const {nodes,rooms}=validateMetadata(metadata),objects=new Map(),hinges=new Map(),roomObjects=new Map(),policy=[];
 scene.updateMatrixWorld(true);
 scene.traverse(o=>{
  if(o.userData.metadata_node_id){const id=o.userData.metadata_node_id;require(!objects.has(id),'Duplicate semantic object');objects.set(id,o);}
  if(o.userData.door_id){require(!hinges.has(o.userData.door_id),'Duplicate hinge');hinges.set(o.userData.door_id,o);}
  if(o.userData.room_id){require(!roomObjects.has(o.userData.room_id),'Duplicate room');roomObjects.set(o.userData.room_id,o);}
  if(Array.isArray(o.userData.airlock_pairs))policy.push(o.userData.airlock_pairs);
 });
 require(objects.size===nodes.size&&[...nodes.keys()].every(id=>objects.has(id)),'GLB semantic objects differ from metadata');
 require(roomObjects.size===rooms.size&&[...rooms].every(([id,r])=>same(roomObjects.get(id)?.userData.bounds,r.bounds)),'GLB room identity/bounds differ');
 require(policy.length===1&&same(policy[0],metadata.airlock_pairs),'GLB airlock pairing differs');
 const expectedLinks=new Map();for(const c of metadata.colliders){const list=expectedLinks.get(c.owner_node_id)||[];list.push(c.id);expectedLinks.set(c.owner_node_id,list);}
 for(const [id,o] of objects)require(same([...(o.userData.collider_ids||[])].sort(),(expectedLinks.get(id)||[]).sort()),'GLB collider owner differs: '+id);
 require(hinges.size===metadata.doors.length,'GLB hinge count differs');
 const fixedFrames=new Map(),leafObjects=new Map();
 for(const d of metadata.doors){
  const pivot=hinges.get(d.id),leaf=objects.get(d.leaf_node_id),h=d.hinge;
  require(pivot&&leaf?.isMesh&&leaf.parent?.parent===pivot,'Moving leaf is not bound to its declared hinge');
  require(close(pivot.position.toArray(),h.position)&&close(pivot.quaternion.toArray(),[0,0,0,1])&&close(pivot.scale.toArray(),[1,1,1])&&close(leaf.parent.position.toArray(),h.leaf_local_center),'GLB hinge/local transforms differ');
  require(close(leaf.position.toArray(),[0,0,0])&&close(leaf.quaternion.toArray(),[0,0,0,1])&&close(leaf.scale.toArray(),[1,1,1]),'GLB leaf local transform differs');
  require(pivot.userData.closed_angle===0&&pivot.userData.open_angle===h.open_angle&&same(pivot.userData.airlock_pair_ids,d.interlock_pair_ids),'GLB hinge policy differs');
  const b=new THREE.Box3().setFromObject(leaf,true),c=metadata.colliders.find(c=>c.owner_node_id===d.leaf_node_id);
  require(close([...b.min.toArray(),...b.max.toArray()],[...c.bounds.min,...c.bounds.max]),'GLB leaf geometry differs from collision');
  for(const id of d.frame_node_ids){const frame=objects.get(id);require(frame?.isMesh,'Missing fixed frame');for(let p=frame;p;p=p.parent)require(p!==pivot,'Fixed frame is attached to moving hinge');fixedFrames.set(id,[...frame.matrixWorld.elements]);}
  leafObjects.set(d.id,leaf);
 }
 function applyDoorStates(states){
  require(states.length===hinges.size,'Door state count mismatch');const seen=new Set();
  for(const s of states){require(hinges.has(s.id)&&!seen.has(s.id)&&Number.isFinite(s.angle),'Invalid door state');seen.add(s.id);hinges.get(s.id).rotation.y=s.angle;}
  scene.updateMatrixWorld(true);
  for(const [id,matrix] of fixedFrames)require(close(objects.get(id).matrixWorld.elements,matrix),'A fixed frame moved with the door');
 }
 return {scene,hinges,leafObjects,objects,applyDoorStates};
}
export async function loadPackage(files){
 const verified=await verifyPackage(files),loaded=await new GLTFLoader().parseAsync(verified.glb,'');
 const binding=bindScene(loaded.scene,verified.metadata),runtime=createRuntime(verified.metadata);
 binding.applyDoorStates(runtime.doorStates());
 return {...verified,...binding,runtime};
}
