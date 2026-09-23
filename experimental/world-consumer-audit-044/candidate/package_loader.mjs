import * as THREE from './vendor/three/build/three.module.js';
import {GLTFLoader} from './vendor/three/examples/jsm/loaders/GLTFLoader.js';
import {validateMetadata,require,createRuntime} from './runtime.mjs';
import {PACKAGE_FILES,MAX_FILE_BYTES,MAX_PACKAGE_BYTES} from './file_admission.mjs';
import {disposeScene} from './scene_disposal.mjs';
export {PACKAGE_FILES} from './file_admission.mjs';
const decoder=new TextDecoder('utf-8',{fatal:true}),close=(a,b)=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<2e-6);
// JSON property order has no semantic meaning. GLB extras retain producer order
// while the portable sidecar uses canonical sorted keys.
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const same=(a,b)=>JSON.stringify(canonical(a))===JSON.stringify(canonical(b));
const sha=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(n=>n.toString(16).padStart(2,'0')).join('');
export async function verifyPackage(files){
 require(files instanceof Map&&files.size===PACKAGE_FILES.length&&PACKAGE_FILES.every(n=>files.has(n)),'Select exactly the five files from one exported package');
 let total=0;for(const [name,bytes] of files){require(bytes instanceof Uint8Array&&bytes.byteLength>0&&bytes.byteLength<=MAX_FILE_BYTES,'Invalid or oversized package file: '+name);total+=bytes.byteLength;}
 require(total<=MAX_PACKAGE_BYTES,'Package exceeds 32 MiB');
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
 require(json.asset?.version==='2.0'&&json.buffers?.length===1&&!Object.hasOwn(json.buffers[0],'uri'),'Only one embedded GLB buffer is supported');
 require(json.images?.length>0&&json.images.length<=128&&json.images.every(i=>!Object.hasOwn(i,'uri')&&Number.isInteger(i.bufferView)&&i.mimeType==='image/png'),'Only embedded PNG textures are supported');
 // Compressed file size is not a decoded-image memory bound. Inspect each PNG
 // header within the actual embedded BIN range before the image decoder runs.
 const binHeader=20+n;require(binHeader+8<=bytes.byteLength&&view.getUint32(binHeader+4,true)===0x004e4942,'Missing embedded GLB BIN chunk');
 const binLength=view.getUint32(binHeader,true),binStart=binHeader+8,declared=json.buffers[0].byteLength;
 require(binStart+binLength===bytes.byteLength&&Number.isSafeInteger(declared)&&declared>0&&binLength>=declared&&binLength-declared<=3,'Embedded GLB buffer length differs');
 let imagePixels=0;
 for(const image of json.images){
  const b=json.bufferViews?.[image.bufferView],offset=b?.byteOffset??0,length=b?.byteLength;
  require(b?.buffer===0&&Number.isSafeInteger(offset)&&offset>=0&&Number.isSafeInteger(length)&&length>=33&&offset+length<=declared,'PNG bufferView exceeds embedded data');
  const start=binStart+offset;
  require([137,80,78,71,13,10,26,10].every((v,i)=>bytes[start+i]===v)&&view.getUint32(start+8,false)===13&&view.getUint32(start+12,false)===0x49484452,'Missing PNG/IHDR header');
  require(bytes[start+24]===8&&bytes[start+25]===6&&bytes[start+26]===0&&bytes[start+27]===0&&bytes[start+28]===0,'Unsupported authored PNG format; expected noninterlaced 8-bit RGBA');
  const width=view.getUint32(start+16,false),height=view.getUint32(start+20,false);
  require(width>0&&height>0&&width<=2048&&height<=2048,'Embedded PNG exceeds 2048px dimension budget');
  imagePixels+=width*height;require(imagePixels<=32*1024*1024,'Embedded PNGs exceed 32-megapixel decode budget');
 }
 const supported=new Set(['KHR_texture_transform','KHR_lights_punctual','KHR_materials_emissive_strength']);
 require((json.extensionsUsed||[]).every(e=>supported.has(e)),'Unsupported GLB extension');
 require((json.meshes?.length||0)<=4096&&(json.nodes?.length||0)<=8192,'Oversized GLB scene');
 return {manifest,metadata,glb:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),glbJSON:json,embeddedImageBudget:{images:json.images.length,pixels:imagePixels},manifestSha256:await sha(files.get('manifest.json'))};
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
 try{const binding=bindScene(loaded.scene,verified.metadata),runtime=createRuntime(verified.metadata);
  binding.applyDoorStates(runtime.doorStates());return {...verified,...binding,runtime};
 }catch(error){disposeScene(loaded.scene);throw error;}
}
