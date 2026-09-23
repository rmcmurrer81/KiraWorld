// Structure and door mesh dimensions/materials transcribed from source-pinned
// installed viewer e6f101d0. Equipment builder remains an exact025 byte copy.
// Extra hierarchy/IDs are export bookkeeping; no geometry is approximated from
// equipment metadata boxes. Door pivots preserve the existing controller poses.
import * as THREE from './vendor/three/build/three.module.js';
import {createDressingMaterials,addRoomDressing} from './source/room_dressing_render.mjs';
import {buildRoomDressing} from './source/room_dressing_plan.mjs';
import {createDoorSystem} from './source/walk_controller.mjs';
import assert from 'node:assert/strict';
export function buildAuthoredScene(geometry,metadata,canvasFactory){
  const doors=createDoorSystem(geometry),plan=buildRoomDressing(geometry,doors.assemblies());
  const scene=new THREE.Scene();scene.name='Original_Mars_authored_scene';
  const groups=new Map(),semantic=new Map(),hinges=new Map(),leafMeshes=new Map();
  for(const room of metadata.rooms){const g=new THREE.Group();g.name='room_'+room.source_id;g.userData={room_id:room.id,bounds:room.bounds,functional_role:room.functional_role};scene.add(g);groups.set(room.source_id,g);}
  const materials=createDressingMaterials(THREE,plan,{canvasFactory});
  assert.ok(materials.basic.screen.map,'Missing authored screen map');
  function bind(object,id){assert.ok(!semantic.has(id));object.userData.metadata_node_id=id;semantic.set(id,object);}
  function roomOf(id){return geometry.rooms.find(r=>id.startsWith(r.id+'_'));}
  for(const p of geometry.primitives){
    const room=roomOf(p.id),mat=materials.surface(p.role,room?.id);
    if(p.role==='floor'){assert.ok(mat.map,'Missing floor map');mat.map.repeat.set(Math.max(1,p.size[0]),Math.max(1,p.size[2]));}
    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...p.size),mat);mesh.name=p.id;mesh.position.set(...p.position);mesh.receiveShadow=true;
    (groups.get(room?.id)||scene).add(mesh);bind(mesh,'node:'+p.id);
  }
  const dressingRoot=new THREE.Group();dressingRoot.name='authored_dressing';scene.add(dressingRoot);
  addRoomDressing(THREE,dressingRoot,geometry,plan,materials);
  for(const node of metadata.nodes){if(['structural_primitive','door_leaf','door_frame'].includes(node.kind))continue;
    const object=dressingRoot.getObjectByName(node.id.slice(5));assert.ok(object,'Missing authored assembly '+node.id);bind(object,node.id);
  }
  // Mounted signs and wall panels must contain real maps, not a headless blank.
  for(const sign of plan.signs){const g=dressingRoot.getObjectByName(sign.id);assert.equal(g.children.length,2,'Missing sign face');assert.ok(g.children[1].material.map);}
  const doorMaterials={frame:new THREE.MeshStandardMaterial({color:0x344955,roughness:.48,metalness:.65}),
    leaf:new THREE.MeshStandardMaterial({color:0xa9babc,roughness:.45,metalness:.52}),
    panel:new THREE.MeshStandardMaterial({color:0x4f7585,roughness:.51,metalness:.37}),
    handle:new THREE.MeshStandardMaterial({color:0xe1d9ae,roughness:.3,metalness:.75})};
  for(const def of doors.definitions()){
    const axis=geometry.portals.find(p=>p.id===def.id).axis,normal=axis==='x'?0:2,along=normal===0?2:0;
    for(const frame of def.frames){const mesh=new THREE.Mesh(new THREE.BoxGeometry(...frame.size),doorMaterials.frame);mesh.name=frame.id;mesh.position.set(...frame.center);scene.add(mesh);bind(mesh,'node:'+frame.id);}
    const pivot=new THREE.Group();pivot.name='hinge_'+def.id;pivot.position.set(...def.hinge);pivot.userData={door_id:'door:'+def.id,closed_angle:0,open_angle:def.openAngle};scene.add(pivot);hinges.set(def.id,pivot);
    const moving=new THREE.Group();moving.name='moving_'+def.id;moving.position.set(...def.leafLocalCenter);pivot.add(moving);
    const size=def.leafSize,leaf=new THREE.Mesh(new THREE.BoxGeometry(...size),doorMaterials.leaf);leaf.name='door_'+def.id+'_leaf';moving.add(leaf);leafMeshes.set(def.id,leaf);bind(leaf,'node:'+leaf.name);
    for(const side of [-1,1]){
      const panelSize=[...size];panelSize[normal]=.008;panelSize[along]*=.77;panelSize[1]*=.68;
      const panel=new THREE.Mesh(new THREE.BoxGeometry(...panelSize),doorMaterials.panel);panel.position.setComponent(normal,side*(size[normal]/2+.005));moving.add(panel);
      const handle=new THREE.Mesh(new THREE.CylinderGeometry(.023,.023,.27,10),doorMaterials.handle);handle.position.setComponent(normal,side*(size[normal]/2+.055));handle.position.setComponent(along,size[along]*.34);handle.position.y=-.12;moving.add(handle);
      for(const y of [-.23,-.01]){const mountSize=[.075,.025,.075];mountSize[normal]=.065;const mount=new THREE.Mesh(new THREE.BoxGeometry(...mountSize),doorMaterials.handle);mount.position.copy(handle.position);mount.position.y=y;mount.position.setComponent(normal,side*(size[normal]/2+.031));moving.add(mount);}
    }
    const head=def.frames.find(f=>f.id.endsWith('_head'));
    const indicator=new THREE.Mesh(new THREE.BoxGeometry(...(axis==='x'?[.225,.033,.22]:[.22,.033,.225])),new THREE.MeshStandardMaterial({color:0xd28360,emissive:0x3f1205,roughness:.5}));indicator.name='indicator_'+def.id;indicator.position.set(...head.center);scene.add(indicator);
  }
  // The original directional fill aims from(6,12,3) at the origin. glTF lights
  // point along -Z; orient this export-only light to retain that direction.
  const fill=new THREE.DirectionalLight(0xfff0d0,.25);fill.name='directional_fill';fill.position.set(6,12,3);fill.lookAt(0,0,0);fill.target.position.set(0,0,-1);fill.add(fill.target);scene.add(fill);
  // Hemisphere, ACES exposure and background are disclosed sidecar limitations.
  let index=0;scene.traverse(object=>{object.userData.export_id='object_'+String(index++).padStart(4,'0');if(!object.name)object.name=object.userData.export_id;});
  for(const c of metadata.colliders){const object=semantic.get(c.owner_node_id);assert.ok(object,'Unmapped collider owner '+c.id);(object.userData.collider_ids??=[]).push(c.id);}
  assert.equal(semantic.size,metadata.nodes.length,'Not every semantic node was exported');
  scene.updateMatrixWorld(true);
  return {scene,doors,plan,semantic,hinges,leafMeshes};
}
