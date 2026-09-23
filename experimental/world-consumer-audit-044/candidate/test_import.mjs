import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import * as THREE from './vendor/three/build/three.module.js';
import {loadPackage,bindScene,PACKAGE_FILES} from './package_loader.mjs';
import {createDoorRuntime} from './runtime.mjs';
const H=path.dirname(fileURLToPath(import.meta.url));
const files=new Map(PACKAGE_FILES.map(n=>[n,new Uint8Array(fs.readFileSync(path.join(H,'sample-package',n)))]));
const [canvasModule,output]=process.argv.slice(2);assert.ok(canvasModule&&output,'Explicit local Canvas module and new output required');
const manifest=JSON.parse(new TextDecoder().decode(files.get('manifest.json'))),native=path.join(canvasModule,'..','canvas-win32-x64-msvc/skia.win32-x64-msvc.node');
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert.equal(digest(native),manifest.producer_digests.external['canvas-native'].sha256,'Unexpected native image decoder');
const canvas=createRequire(import.meta.url)(canvasModule);assert.equal(createRequire(import.meta.url)(canvasModule+'/package.json').version,'0.1.100');
globalThis.self=globalThis;
globalThis.createImageBitmap=async(blob,options)=>{assert.ok(blob instanceof Blob);assert.ok(!options?.imageOrientation||options.imageOrientation==='none');return canvas.loadImage(Buffer.from(await blob.arrayBuffer()));};
const originalFetch=globalThis.fetch;globalThis.fetch=(url,...args)=>{assert.ok(String(url).startsWith('blob:'),'Only embedded image blobs are allowed');return originalFetch(url,...args);};
const loaded=await loadPackage(files),m=loaded.metadata,scene=loaded.scene;
let meshes=0;const textures=new Set(),materials=new Set();scene.traverse(o=>{if(o.isMesh){meshes++;const list=Array.isArray(o.material)?o.material:[o.material];for(const material of list){materials.add(material);if(material.map){textures.add(material.map);assert.ok(material.map.image.width>0);assert.equal(material.map.colorSpace,THREE.SRGBColorSpace);}}}});
assert.equal(meshes,565);assert.equal(materials.size,97);assert.equal(textures.size,67);assert.equal(loaded.objects.size,141);assert.equal(m.colliders.length,134);assert.equal(loaded.hinges.size,6);
const close=(a,b)=>{assert.equal(a.length,b.length);a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<2e-6,`${v} differs from ${b[i]}`));};
const getBounds=o=>{const b=new THREE.Box3().setFromObject(o,true);return [...b.min.toArray(),...b.max.toArray()];};
const safeFeet=d=>{const middle=d.hinge.position.map((v,i)=>v+d.hinge.leaf_local_center[i]),size=m.nodes.find(n=>n.id===d.leaf_node_id).representation.size,axis=size[0]===.065?0:2;
 for(const sign of [-1,1]){const feet=[...middle];feet[1]=0;feet[axis]+=sign*1.05;if(!(feet[axis]+.34>=d.swing_bounds.min[axis]&&feet[axis]-.34<=d.swing_bounds.max[axis]))return feet;}throw Error('No safe position');};
const r=createDoorRuntime(m),poses=[],fixed=new Map(m.doors.flatMap(d=>d.frame_node_ids).map(id=>[id,getBounds(loaded.objects.get(id))]));
for(const d of m.doors){
 const feet=safeFeet(d),samples=[];
 for(const step of [0,4,8]){if(step===4){assert.ok(r.toggle(d.id,feet).ok);for(let i=0;i<4;i++)r.advance(.05,feet);}if(step===8)for(let i=0;i<4;i++)r.advance(.05,feet);
  loaded.applyDoorStates(r.all());const state=r.all().find(s=>s.id===d.id),leaf=loaded.leafObjects.get(d.id);close(leaf.getWorldPosition(new THREE.Vector3()).toArray(),state.center);close(getBounds(leaf),[...state.collider.min,...state.collider.max]);
  for(const [id,b] of fixed)close(getBounds(loaded.objects.get(id)),b);samples.push({angle:state.angle,center:state.center});
 }assert.ok(r.toggle(d.id,feet).ok);for(let i=0;i<8;i++)r.advance(.05,feet);loaded.applyDoorStates(r.all());poses.push({id:d.id,samples});
}
const negatives=[];
function reject(name,mutate,restore,pattern){mutate();assert.throws(()=>bindScene(scene,m),pattern);restore();bindScene(scene,m);negatives.push(name);}
const door=m.doors[0],pivot=loaded.hinges.get(door.id),leaf=loaded.leafObjects.get(door.id),owner=loaded.objects.get(m.colliders[0].owner_node_id),oldLinks=owner.userData.collider_ids;
reject('moved hinge rejected',()=>pivot.position.x+=.2,()=>pivot.position.x-=.2,/hinge\/local/);
reject('wrong owner links rejected',()=>owner.userData.collider_ids=['collider:missing'],()=>owner.userData.collider_ids=oldLinks,/owner differs/);
const oldPairs=pivot.userData.airlock_pair_ids;reject('hinge pairing rejected',()=>pivot.userData.airlock_pair_ids=[],()=>pivot.userData.airlock_pair_ids=oldPairs,/policy differs/);
const parent=leaf.parent;reject('leaf moved outside hinge rejected',()=>scene.add(leaf),()=>parent.add(leaf),/declared hinge/);
const result={status:'ACTUAL_GLB_PORTABLE_CONSUMER_IMPORT_BINDING_PASS',three_revision:THREE.REVISION,
 package_manifest_sha256:loaded.manifestSha256,glb_sha256:manifest.files['scene.glb'].sha256,
 counts:{meshes,materials:materials.size,textures:textures.size,semantic_nodes:loaded.objects.size,colliders:m.colliders.length,doors:loaded.hinges.size,rooms:m.rooms.length},
 checks:{real_embedded_pngs_decoded:true,all_collider_links_bound:true,door_closed_half_open_pose_samples:poses,fixed_frames_unchanged:true,negative_binding_cases:negatives},
 source_geometry_or_authored_builder_loaded:false,webgl_browser_gpu_model_calls:0,visual_or_owner_approval:false};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:result.status,counts:result.counts}));
