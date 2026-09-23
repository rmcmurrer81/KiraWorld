import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import * as before from '../world-observation-exclusion-055/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import * as after from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/layout_package_assets/source/horizontal_navigation.mjs';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex'),EPS=1e-6;
const out=new URL('./GEOMETRY-TESTS.json',import.meta.url);assert.ok(!fs.existsSync(out));
const inputs=JSON.parse(fs.readFileSync(new URL('./fixtures/supported-layouts.json',import.meta.url)));
const checks=[];let rays=0;
function signature(root){const rows=[];root.traverse(o=>{if(o.isMesh)rows.push({name:o.name,position:o.position.toArray(),size:Array.from(o.geometry.attributes.position.array),indices:Array.from(o.geometry.index.array),mat:[o.material.color.toArray(),o.material.opacity,o.material.transparent,o.material.depthWrite,o.material.side]});});return sha(JSON.stringify(rows));}
function bounds(o){return new THREE.Box3().setFromObject(o,true);}
function overlapFaces(a,b){const A=bounds(a),B=bounds(b),rows=[];
 for(let axis=0;axis<3;axis++)for(const sign of [-1,1]){
  const face=sign<0?'min':'max';if(Math.abs(A[face].getComponent(axis)-B[face].getComponent(axis))>EPS)continue;
  const spans=[0,1,2].filter(i=>i!==axis).map(i=>Math.min(A.max.getComponent(i),B.max.getComponent(i))-Math.max(A.min.getComponent(i),B.min.getComponent(i)));
  if(spans.every(x=>x>EPS))rows.push({axis,sign,area:spans[0]*spans[1]});
 }return rows;
}
function assembly(module,g,plan,vp){const materials=module.createDressingMaterials(THREE,plan,{canvasFactory:()=>null}),p=g.primitives.find(p=>p.id===vp.wall_id);
 const root=module.createStructuralPrimitive(THREE,p,materials.basic.ivory,vp,materials);root.updateMatrixWorld(true);return root;}
function checkCase(title,g,plan,full=false){const gs=JSON.stringify(g),ps=JSON.stringify(plan),vp=after.planObservationViewport(g,plan);assert.ok(vp,title);assert.deepEqual(vp,before.planObservationViewport(g,plan));
 const a=assembly(before,g,plan,vp),b=assembly(after,g,plan,vp),pairs=[];let oldArea=0;
 for(const orient of ['vertical','horizontal'])for(const edge of [-1,1]){
  const suffix=orient+'_'+edge,frame=a.getObjectByName(vp.wall_id+'_inner_frame_'+suffix),reveal=a.getObjectByName(vp.wall_id+'_reveal_'+suffix);
  const af=b.getObjectByName(frame.name),ar=b.getObjectByName(reveal.name),old=overlapFaces(frame,reveal),current=overlapFaces(af,ar);
  assert.ok(old.some(r=>r.axis===vp.axis&&r.sign===-vp.sign),title+' lacks reproduced facing-plane overlap');
  assert.equal(current.length,0,title+' still has positive-area equally oriented coplanar frame/reveal faces');oldArea+=old.filter(r=>r.axis===vp.axis&&r.sign===-vp.sign).reduce((x,r)=>x+r.area,0);
  const fb=bounds(af),rb=bounds(ar),front=vp.sign>0?'min':'max',back=vp.sign>0?'max':'min';
  assert.ok(Math.abs(fb[back].getComponent(vp.axis)-rb[front].getComponent(vp.axis))<EPS,'Frame back must meet reveal front');
  assert.ok(Math.abs(Math.abs(fb[front].getComponent(vp.axis)-rb[front].getComponent(vp.axis))-.026)<EPS,'26mm separated front faces');
  assert.equal(signature(frame),signature(af),'Frame itself changed');
  pairs.push({member:suffix,before_coincident_faces:old,after_coincident_faces:current});
  // Actual triangle intersections at multiple distances and oblique camera bearings.
  const target=af.getWorldPosition(new THREE.Vector3());target.setComponent(vp.axis,fb[front].getComponent(vp.axis));
  for(const distance of [.5,2,10])for(const bearing of [-.4,0,.4]){
   const origin=target.clone();origin.setComponent(vp.axis,origin.getComponent(vp.axis)-vp.sign*distance);origin.setComponent(vp.along,origin.getComponent(vp.along)+bearing*distance);
   const hit=new THREE.Raycaster(origin,target.clone().sub(origin).normalize(),.001,50).intersectObject(b,true);
   assert.ok(hit.length);assert.equal(hit[0].object.name,af.name,title+' front ray hits another surface');
   assert.ok(hit.filter(h=>Math.abs(h.distance-hit[0].distance)<EPS).every(h=>h.object===af),'Two materials occupy the same nearest depth');rays++;
  }
 }
 const aBounds=bounds(a),bBounds=bounds(b),wall=g.primitives.find(p=>p.id===vp.wall_id),collider=g.colliders.find(c=>c.id===vp.safety_collider_id);
 assert.deepEqual(aBounds.min.toArray(),bBounds.min.toArray());assert.deepEqual(aBounds.max.toArray(),bBounds.max.toArray());
 for(let i=0;i<3;i++){assert.ok(Math.abs(bBounds.min.getComponent(i)-collider.min[i])<EPS);assert.ok(Math.abs(bBounds.max.getComponent(i)-collider.max[i])<EPS);}
 for(const item of a.children)if(!item.name.includes('_reveal_'))assert.equal(signature(item),signature(b.getObjectByName(item.name)),item.name+' unexpectedly changed');
 // Center and quarter-aperture rays still hit only transparent glazing.
 for(const yf of [.25,.5,.75])for(const af of [-.3,0,.3]){
  const pos=new THREE.Vector3();pos.setComponent(vp.axis,vp.coordinate-vp.sign);pos.y=vp.bottom+(vp.top-vp.bottom)*yf;pos.setComponent(vp.along,vp.center+vp.width*af);
  const dir=new THREE.Vector3();dir.setComponent(vp.axis,vp.sign);const hit=new THREE.Raycaster(pos,dir,.001,2).intersectObject(b,true);
  assert.ok(hit.length);assert.ok(hit.every(h=>h.object.userData.viewport_glazing));rays++;
 }
 if(full){const point=d=>{let p=[0,0,0];p[vp.axis]=vp.coordinate+vp.sign*d;p[vp.along]=vp.center;return p;};
  const result=checkHorizontalRoute({id:'viewport056-safety',avatar_radius:.34,avatar_height:1.68,points:[point(-.8),point(-.01)]},{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:g.colliders});assert.equal(result.status,'blocked');
 }
 assert.equal(JSON.stringify(g),gs);assert.equal(JSON.stringify(plan),ps);
 checks.push({title,viewport:vp,front_overlap_area_before:oldArea,after:0,paired_faces:pairs,bounds_and_collider_unchanged:true,unchanged_nonreveal_meshes:a.children.length-4});
}
for(const f of inputs){const doors=createDoorSystem(f.geometry),plan=buildRoomDressing(f.geometry,doors.assemblies());checkCase(f.title,f.geometry,plan,true);
 const av=before.planObservationViewport(f.geometry,plan),bv=after.planObservationViewport(f.geometry,plan),a=new THREE.Scene(),b=new THREE.Scene();
 before.addObservationExterior(THREE,a,av,f.presentation,f.geometry);after.addObservationExterior(THREE,b,bv,f.presentation,f.geometry);assert.equal(signature(a),signature(b),'Scenery changed');
 const absent=after.createStructuralPrimitive(THREE,f.geometry.primitives[0],new THREE.MeshStandardMaterial(),null,null),prior=before.createStructuralPrimitive(THREE,f.geometry.primitives[0],new THREE.MeshStandardMaterial(),null,null);assert.equal(signature(absent),signature(prior));
}
for(const side of ['east','west','north','south'])for(const thickness of [.12,.15,.3]){
 const axis=['east','west'].includes(side)?0:2,along=axis===0?2:0,sign=['east','north'].includes(side)?1:-1;
 const room={id:'lookout',x:3,z:-7,width:6,depth:8,floor_y:2.3,height:3},coordinate=axis===0?room.x+(sign>0?room.width:0):room.z+(sign>0?room.depth:0);
 const position=[room.x+room.width/2,room.floor_y+room.height/2,room.z+room.depth/2],size=[room.width,room.height,room.depth];position[axis]=coordinate;size[axis]=thickness;
 const id='lookout_'+side+'_0',primitive={id,role:'wall',position,size},collider={id,min:position.map((x,i)=>x-size[i]/2),max:position.map((x,i)=>x+size[i]/2)};
 const g={rooms:[room],primitives:[primitive],colliders:[collider],portals:[]},plan={enabled:true,roomStyles:{lookout:{role:'observation'}},colliders:[]};checkCase(side+' '+thickness+'m wall shifted floor',g,plan);
}
const module=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',import.meta.url),'utf8').replaceAll('export function ','function ').trim(),viewer=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');assert.equal(viewer.split(module).length-1,1);
const report={status:'PASS',cases:checks.length,rays,checks,preview_export_share_exact_module:true,models_GPU_UI:0,visual_flicker_resolution_claim:false};fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,cases:checks.length,rays}));
