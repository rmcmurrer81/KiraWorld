import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from './preimages/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {buildAuthoredScene} from './preimages/tools/world_builder_engine/layout_package_assets/authored_scene.mjs';
import {buildRoomDressing} from './preimages/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem} from './preimages/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {exportSceneMetadata} from './preimages/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {NAVIGATION_CONTRACT,checkWalkSpawn} from './preimages/tools/world_builder_engine/horizontal_navigation.mjs';
const g=JSON.parse(fs.readFileSync(new URL('./fixtures/base.json',import.meta.url)));
const doors=createDoorSystem(g),plan=buildRoomDressing(g,doors.assemblies());
const metadata=exportSceneMetadata(g,plan,doors.definitions(),{sceneId:'hardware_reproduction',sourceDigests:{geometry:'1'.repeat(64),dressing_recipe:'2'.repeat(64),door_controller:'3'.repeat(64)},doorInterlocks:doors.interlocks()});
const canvas=()=>({width:0,height:0,getContext:()=>new Proxy({},{get:()=>()=>{},set:()=>true})});
const built=buildAuthoredScene(g,metadata,canvas);built.scene.updateMatrixWorld(true);
const evidence=[];
for(const def of doors.definitions()){
 const p=g.portals.find(p=>p.id===def.id),normal=p.axis==='x'?0:2,along=normal===0?2:0;
 const moving=built.hinges.get(def.id).getObjectByName('moving_'+def.id);
 for(const handle of moving.children.filter(m=>m.geometry?.type==='CylinderGeometry')){
  const box=new THREE.Box3().setFromObject(handle,true),center=handle.getWorldPosition(new THREE.Vector3()).toArray();
  const side=Math.sign(handle.position.getComponent(normal)),feet=[...center];feet[1]=def.hinge[1];feet[normal]=p.coordinate+side*(.34+.08);
  feet[along]=Math.max(p.center-p.width/2+.38,Math.min(p.center+p.width/2-.38,feet[along]));
  const avatar={min:feet.map((v,i)=>v-(i===1?0:.34)),max:feet.map((v,i)=>v+(i===1?1.68:.34))};
  const overlaps=avatar.min.every((v,i)=>v<box.max.getComponent(i)&&avatar.max[i]>box.min.getComponent(i));
  // Match the actual walker: structure, doors and furnishings are checked as
  // three bounded scenes rather than exceeding its per-scene collider limit.
  const allowed=[g.colliders,doors.colliders(),plan.colliders].every(colliders=>checkWalkSpawn(feet,{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders}).ok);
  evidence.push({door_id:def.id,axis:p.axis,side,handle_bounds:{min:box.min.toArray(),max:box.max.toArray()},feet,walking_allowed:allowed,visible_handle_overlap:overlaps,leaf_half_depth:.0325,hardware_normal_extent:Math.max(Math.abs(box.min.getComponent(normal)-p.coordinate),Math.abs(box.max.getComponent(normal)-p.coordinate))});
 }
}
const reproduced=evidence.filter(e=>e.walking_allowed&&e.visible_handle_overlap);
assert.ok(reproduced.length>0);assert.deepEqual([...new Set(reproduced.map(e=>e.axis))].sort(),['x','z']);
const result={status:'REPRODUCED_VISIBLE_HANDLE_PENETRATION',observations:evidence,allowed_overlaps:reproduced.length,model_gpu_ui_calls:0,geometry_or_owner_changes:false};
fs.writeFileSync(new URL('./REPRODUCTION.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,allowed_overlaps:reproduced.length,observations:evidence.length}));
