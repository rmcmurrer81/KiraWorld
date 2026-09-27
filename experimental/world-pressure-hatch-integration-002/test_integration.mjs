import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {createDoorSystem as originalDoors} from './baseline062/walk_controller.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {buildPressureHatch,hatchCollidersAt} from './candidate/tools/world_builder_engine/pressure_hatch.mjs';
import {planHatchArchitecture,buildHatchStructuralMesh,hatchOuterProfilePoints,polygonArea,subtractConvex} from './candidate/tools/world_builder_engine/pressure_hatch_architecture.mjs';
const read=name=>JSON.parse(readFileSync(new URL('fixtures/'+name+'.json',import.meta.url),'utf8'));
const saved=()=>read('base'); // Public synthetic fixture; owner geometry is intentionally excluded.
const geometryCases=()=>['base','renamed','wider','translated'].map(read).concat([saved()]);
const overlap=(a,b)=>a.min.every((v,i)=>v<b.max[i]&&a.max[i]>b.min[i]);
function safeFeet(g,plan){const p=g.portals.find(p=>p.id===plan.portalId),n=p.axis==='x'?0:2;const feet=[...plan.origin];feet[n]-=plan.normalSign*1.1;return feet;}
function dispose(group){const materials=new Set();group.traverse(o=>{o.geometry?.dispose();if(o.material)materials.add(o.material);});materials.forEach(m=>m.dispose());}
function world(plan,p){const result=[...plan.origin],n=plan.axis==='x'?0:2,t=n===0?2:0;result[t]+=p[0];result[1]+=p[1];result[n]+=plan.normalSign*p[2];return new THREE.Vector3(...result);}
function nearest(objects,plan,p,d){objects.forEach(o=>o.updateMatrixWorld(true));const direction=world(plan,d).sub(world(plan,[0,0,0])).normalize();const hits=new THREE.Raycaster(world(plan,p),direction,0,20).intersectObjects(objects,true);if(!hits.length)return [];
 return [...new Set(hits.filter(h=>Math.abs(h.distance-hits[0].distance)<2e-6).map(h=>h.object.name))];}

test('paired hatches use corrected motion while every ordinary definition/pose/collider stays identical',()=>{
 for(const g of geometryCases()){
  const before=JSON.stringify(g),old=originalDoors(g),next=createDoorSystem(g),ids=new Set(next.hatchPlans().map(p=>p.portalId));assert.equal(ids.size,2);
  const ordinary=d=>!ids.has(d.id);
  assert.deepEqual(next.all().filter(ordinary),old.all().filter(ordinary));assert.deepEqual(next.definitions().filter(ordinary),old.definitions().filter(ordinary));
  assert.deepEqual(next.assemblies().filter(ordinary),old.assemblies().filter(ordinary));
  const ownerOrdinary=c=>[...g.portals.filter(ordinary)].some(p=>c.id.startsWith('door_'+p.id+'_'));
  assert.deepEqual(next.colliders().filter(ownerOrdinary),old.colliders().filter(ownerOrdinary));
  assert.deepEqual(next.interlocks(),old.interlocks());assert.equal(JSON.stringify(g),before);
  assert.ok(next.colliders().length>128,'Both complete assemblies must survive batching');
 }
});

test('synthetic two hatch placements enforce interlock, held motion, closing and fresh-session recovery',()=>{
 for(const g of geometryCases()){
  const system=createDoorSystem(g),[a,b]=system.hatchPlans(),feetA=safeFeet(g,a),feetB=safeFeet(g,b);
  assert.equal(system.toggle(a.portalId,feetA).ok,true);
  assert.equal(system.toggle(b.portalId,feetB).ok,false,'Same-frame opening must reserve peer');
  system.advance(.05,a.origin);assert.equal(system.all().find(d=>d.id===a.portalId).motionHeld,true);
  assert.equal(system.toggle(b.portalId,feetB).ok,false,'Held angle-zero opening must still reserve peer');
  for(let i=0;i<8;i++)system.advance(.05,feetA);assert.equal(system.all().find(d=>d.id===a.portalId).state,'open');
  assert.equal(system.toggle(b.portalId,feetB).ok,false);
  assert.equal(system.toggle(a.portalId,feetA).ok,true);system.advance(.05,a.origin);
  assert.equal(system.all().find(d=>d.id===a.portalId).state,'closing');assert.equal(system.all().find(d=>d.id===a.portalId).motionHeld,true);
  for(let i=0;i<8;i++)system.advance(.05,feetA);assert.equal(system.all().find(d=>d.id===a.portalId).state,'closed');
  assert.equal(system.toggle(b.portalId,feetB).ok,true);for(let i=0;i<8;i++)system.advance(.05,feetB);
  assert.equal(system.all().find(d=>d.id===b.portalId).state,'open');
  assert.equal(createDoorSystem(g).all().every(d=>d.state==='closed'),true);
 }
});

test('controller exposes every actual part collider, with vertices contained throughout the complete opening cycle',()=>{
 const g=saved(),system=createDoorSystem(g);
 for(const plan of system.hatchPlans()){
  const built=buildPressureHatch(THREE,plan),feet=safeFeet(g,plan);assert.equal(system.toggle(plan.portalId,feet).ok,true);
  for(let step=0;step<=8;step++){
   const state=system.all().find(d=>d.id===plan.portalId);built.setAngle(state.angle);
   const colliders=system.colliders().filter(c=>c.id.startsWith('hatch_'+plan.portalId+'_'));
   assert.deepEqual(colliders,hatchCollidersAt(plan,state.angle));assert.equal(colliders.length,66);
   for(const mesh of built.meshes.values())for(let i=0;i<mesh.geometry.attributes.position.count;i++){
    const point=new THREE.Vector3().fromBufferAttribute(mesh.geometry.attributes.position,i).applyMatrix4(mesh.matrixWorld).toArray();
    assert.ok(colliders.filter(c=>c.owner===mesh.name).some(c=>point.every((v,j)=>v>=c.min[j]-2e-6&&v<=c.max[j]+2e-6)));
   }
   if(step<8)system.advance(.05,feet);
  }
  assert.equal(system.toggle(plan.portalId,feet).ok,true);for(let i=0;i<8;i++)system.advance(.05,feet);dispose(built.fixed);dispose(built.pivot);
 }
});

test('walking and reserved furnishing checks admit the complete hatch collider batches without altering source',()=>{
 for(const g of geometryCases()){
  const oldPlan=buildRoomDressing(g,originalDoors(g).assemblies()),system=createDoorSystem(g);
  for(const assembly of system.assemblies())assert.ok(oldPlan.colliders.every(c=>!overlap(c,assembly.swingBounds)),'Existing authored furnishing enters revised sweep');
  const controller=createWalkController(g,{extraColliders:oldPlan.colliders});assert.equal(controller.doorHatchPlans().length,2);
  const oldState=controller.snapshot();controller.step(0);assert.deepEqual(controller.snapshot(),oldState);
 }
});

test('cutout planner preserves source/support and does not touch ordinary-door-only architecture',()=>{
 for(const g of geometryCases()){
  const before=JSON.stringify(g),system=createDoorSystem(g),plan=planHatchArchitecture(g,system.hatchPlans());
  assert.equal(plan.sourceGeometryChanged,false);assert.ok(Object.values(plan.modifications).filter(m=>m.role==='wall').length>=6);
  assert.ok(Object.values(plan.modifications).filter(m=>m.role==='floor').length>=2);
  for(const mod of Object.values(plan.modifications)){assert.ok(mod.removedArea>0&&mod.removedArea<mod.sourceArea);assert.equal(mod.supportSurfaceChanged,false);assert.ok(mod.cutPortalIds.every(id=>system.hatchPlans().some(p=>p.portalId===id)));}
  assert.equal(JSON.stringify(g),before);assert.deepEqual(planHatchArchitecture(g,[]).modifications,{});
 }
});

test('outer contour matches the actual Three extrusion samples rather than approximating a rectangle',()=>{
 const plan=createDoorSystem(read('base')).hatchPlans()[0],p=plan.fixed.find(p=>p.id.endsWith('_structural_surround')).outer;
 const shape=new THREE.Shape();shape.moveTo(-p.width/2,p.bottom);shape.lineTo(p.width/2,p.bottom);shape.lineTo(p.width/2,p.top-p.radius);
 shape.absarc(p.width/2-p.radius,p.top-p.radius,p.radius,0,Math.PI/2,false);shape.lineTo(-p.width/2+p.radius,p.top);shape.absarc(-p.width/2+p.radius,p.top-p.radius,p.radius,Math.PI/2,Math.PI,false);shape.closePath();
 const actual=shape.extractPoints(20).shape.slice(0,-1).map(p=>p.toArray()),expected=hatchOuterProfilePoints(p);assert.equal(actual.length,expected.length);
 actual.forEach((p,i)=>p.forEach((v,j)=>assert.ok(Math.abs(v-expected[i][j])<1e-12)));
});

test('convex subtraction conserves area with disjoint rectangles and no phantom passage',()=>{
 const base=[[0,0],[4,0],[4,4],[0,4]],cut=[[1,1],[3,1],[3,3],[1,3]],parts=subtractConvex(base,cut);
 assert.equal(parts.length,4);assert.equal(parts.reduce((n,p)=>n+polygonArea(p),0),12);
 assert.deepEqual(subtractConvex(base,[[-1,-1],[5,-1],[5,5],[-1,5]]),[]);
 assert.equal(subtractConvex(base,[[5,5],[6,5],[6,6],[5,6]]).reduce((n,p)=>n+polygonArea(p),0),16);
});

test('synthetic wall/floor meshes and decorative panels share the corrected frame cut without duplicate reveals',()=>{
 const g=saved(),plans=createDoorSystem(g).hatchPlans(),architecture=planHatchArchitecture(g,plans);
 const material=new THREE.MeshBasicMaterial(),structures=[];
 for(const p of g.primitives){const mesh=buildHatchStructuralMesh(THREE,p,material,architecture);if(mesh){structures.push(mesh);
   if(p.role==='wall')for(const sign of [-1,1])structures.push(buildHatchStructuralMesh(THREE,p,material,architecture,{panelNormal:sign,panelOffset:.0008}));}}
 for(const plan of plans){const built=buildPressureHatch(THREE,plan);built.setAngle(plan.openAngle);
  const all=[...structures,built.fixed],W=plan.aperture.width;
  for(const side of [-1,1])for(const z of [-.07,0,.07])assert.equal(nearest(all,plan,[0,1,z],[side,0,0]).length,1);
  for(const z of [-.08,0,.075,.084])assert.equal(nearest(all,plan,[0,.4,z],[0,-1,0]).length,1);
  for(const side of [-1,1])assert.equal(nearest(all,plan,[0,1,side*.5],[0,0,-side]).length,0,'Open fixed assembly/structure must leave a real passage');
  // Frame front remains visible and free of the old surrounding wall overlap.
  assert.equal(nearest(all,plan,[W/2+.04,1,.5],[0,0,-1]).length,1);dispose(built.fixed);dispose(built.pivot);
 }
 structures.forEach(dispose);
});

test('architectural and motion seams remain valid for both axes and both room-A normal directions',()=>{
 const base=read('base'),rotated=structuredClone(base);
 for(const r of rotated.rooms){[r.x,r.z]=[r.z,r.x];[r.width,r.depth]=[r.depth,r.width];}
 for(const p of rotated.portals)p.axis=p.axis==='x'?'z':'x';
 for(const p of rotated.primitives){[p.position[0],p.position[2]]=[p.position[2],p.position[0]];[p.size[0],p.size[2]]=[p.size[2],p.size[0]];}
 for(const c of rotated.colliders)for(const key of ['min','max'])[c[key][0],c[key][2]]=[c[key][2],c[key][0]];
 for(const s of rotated.support_surfaces){[s.min_x,s.min_z]=[s.min_z,s.min_x];[s.max_x,s.max_z]=[s.max_z,s.max_x];}
 for(const route of rotated.routes)for(const point of route.points)[point[0],point[2]]=[point[2],point[0]];
 const variants=[base,rotated];for(const g of [base,rotated]){const copy=structuredClone(g);copy.portals.forEach(p=>[p.room_a,p.room_b]=[p.room_b,p.room_a]);variants.push(copy);}
 const modes=new Set();
 for(const g of variants){const doors=createDoorSystem(g),architecture=planHatchArchitecture(g,doors.hatchPlans()),material=new THREE.MeshBasicMaterial();
  const structures=g.primitives.map(p=>buildHatchStructuralMesh(THREE,p,material,architecture)).filter(Boolean);
  for(const plan of doors.hatchPlans()){
   modes.add(plan.axis+'/'+plan.normalSign);const built=buildPressureHatch(THREE,plan);built.setAngle(0);
   for(const side of [-1,1])assert.equal(nearest([...structures,built.fixed],plan,[0,1,.06],[side,0,0]).length,1);
   assert.equal(nearest([...structures,built.fixed],plan,[0,.4,.075],[0,-1,0]).length,1);
   assert.ok(doors.toggle(plan.portalId,safeFeet(g,plan)).ok);for(let i=0;i<8;i++)doors.advance(.05,safeFeet(g,plan));
   assert.equal(doors.all().find(d=>d.id===plan.portalId).state,'open');assert.ok(doors.toggle(plan.portalId,safeFeet(g,plan)).ok);for(let i=0;i<8;i++)doors.advance(.05,safeFeet(g,plan));
   dispose(built.fixed);dispose(built.pivot);
  }
  structures.forEach(dispose);
 }
 assert.equal(modes.size,4);
});
