import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import * as previous from './preimages/tools/world_builder_engine/pressure_hatch.mjs';
import * as current from './candidate/tools/world_builder_engine/pressure_hatch.mjs';
import {buildInspectionContext} from './preview/assets/inspection_context.mjs';
const fixture=name=>JSON.parse(readFileSync(new URL('fixtures/'+name+'.json',import.meta.url),'utf8'));
const near=(a,b)=>Math.abs(a-b)<2e-6;
function create(recipe,geometry=fixture('base')){const id=recipe.pressureHatchIds(geometry)[0],plan=recipe.planPressureHatch(geometry,id),scene=recipe.buildPressureHatch(THREE,plan);scene.setAngle(0);return {plan,scene};}
function point(plan,p){const n=plan.axis==='x'?0:2,t=n===0?2:0,result=[...plan.origin];result[t]+=p[0];result[1]+=p[1];result[n]+=plan.normalSign*p[2];return new THREE.Vector3(...result);}
function firstOwners({plan,scene},start,direction,objects=[scene.fixed]){
 const ray=new THREE.Raycaster(point(plan,start),point(plan,direction).sub(point(plan,[0,0,0])).normalize(),0,10);
 const hits=ray.intersectObjects(objects,true);if(!hits.length)return [];
 return [...new Set(hits.filter(hit=>near(hit.distance,hits[0].distance)).map(hit=>hit.object.name))];
}
function dispose(scene){const materials=new Set();for(const mesh of scene.meshes.values()){mesh.geometry.dispose();materials.add(mesh.material);}for(const material of materials)material.dispose();}
const part=(plan,name)=>plan.fixed.find(p=>p.id.endsWith('_'+name));
const interval=p=>[p.center[2]-p.size[2]/2,p.center[2]+p.size[2]/2];

test('real ray intersections reproduce the old front/reveal/sill duplicate faces and resolve them in the successor',()=>{
 const old=create(previous),next=create(current),W=next.plan.aperture.width,H=next.plan.aperture.top;
 const samples=[
  {name:'flat front band',start:[W/2+.04,H*.40,.5],direction:[0,0,-1]},
  {name:'inner vertical reveal',start:[0,H*.40,.07],direction:[1,0,0]},
  {name:'flush sill',start:[0,.4,.075],direction:[0,-1,0]},
  {name:'top front band',start:[0,H+.04,.5],direction:[0,0,-1]},
  {name:'rounded front band',start:[W/2-.18+.22/Math.sqrt(2),H-.18+.22/Math.sqrt(2),.5],direction:[0,0,-1]},
 ];
 for(const sample of samples){assert.ok(firstOwners(old,sample.start,sample.direction).length>1,'Old defect not reproduced: '+sample.name);
  assert.equal(firstOwners(next,sample.start,sample.direction).length,1,'Unresolved duplicate: '+sample.name);}
 dispose(old.scene);dispose(next.scene);
});

test('surround and deep seat partition one ring; gasket and rear trim meet without depth penetration',()=>{
 for(const name of ['base','renamed','wider','translated']){
  const {plan,scene}=create(current,fixture(name)),frame=part(plan,'structural_surround'),seat=part(plan,'seat_flange'),gasket=part(plan,'continuous_gasket'),rear=part(plan,'rear_beveled_trim');
  assert.deepEqual(frame.inner,seat.outer);assert.deepEqual(seat.inner,plan.aperture);assert.deepEqual(interval(frame),interval(seat));
  assert.ok(near(interval(seat)[1],interval(gasket)[0]));assert.ok(near(interval(rear)[1],interval(frame)[0]));
  assert.ok(near(interval(gasket)[1],.0875),'Closed leaf contact plane must not move.');
  assert.ok(near(interval(frame)[1],.080),'Frame remains outside existing 75 mm wall face.');
  assert.ok(near(seat.inner.bottom,0)&&near(gasket.inner.bottom,0));
  dispose(scene);
 }
});

test('dense front band samples have exactly one nearest visible owner, including the rounded crown',()=>{
 const {plan,scene}=create(current),item={plan,scene},W=plan.aperture.width,H=plan.aperture.top;
 for(const side of [-1,1])for(let j=0;j<20;j++)for(const offset of [.016,.040,.090,.145]){
  assert.equal(firstOwners(item,[side*(W/2+offset),.01+(H-.21)*j/19,.5],[0,0,-1]).length,1);
 }
 for(let j=1;j<20;j++)for(const radial of [.016,.040,.090,.145]){
  const angle=j*Math.PI/40;
  for(const side of [-1,1])assert.equal(firstOwners(item,[side*(W/2-.18+(.18+radial)*Math.cos(angle)),H-.18+(.18+radial)*Math.sin(angle),.5],[0,0,-1]).length,1);
 }
 dispose(scene);
});

function floorBoxes(plan,cut){
 const rects=cut?[[-4,cut.min[0],-5,5],[cut.max[0],4,-5,5],[cut.min[0],cut.max[0],-5,cut.min[1]],[cut.min[0],cut.max[0],cut.max[1],5]]:[[-4,4,-5,5]];
 return rects.map(([x0,x1,z0,z1],i)=>{const mesh=new THREE.Mesh(new THREE.BoxGeometry(x1-x0,.12,z1-z0),new THREE.MeshBasicMaterial());
  mesh.name='context_floor_'+i;mesh.position.copy(point(plan,[(x0+x1)/2,-.06,(z0+z1)/2]));if(plan.axis==='x')mesh.rotation.y=Math.PI/2;mesh.updateMatrixWorld(true);return mesh;});
}
test('the old context floor duplicates the sill; the explicit cutout preserves a flush surface without a hole',()=>{
 const next=create(current),oldFloor=floorBoxes(next.plan),context=buildInspectionContext(THREE,next.plan,new THREE.MeshBasicMaterial(),new THREE.MeshBasicMaterial());
 const newFloor=context.children.filter(m=>m.name.startsWith('context_floor_'));
 assert.equal(next.plan.limits.requiresFlushSillFloorCutout,true);
 for(const z of [-.08,0,.075,.084]){
  assert.equal(firstOwners(next,[0,.4,z],[0,-1,0],[next.scene.fixed,...oldFloor]).length,2);
  assert.equal(firstOwners(next,[0,.4,z],[0,-1,0],[next.scene.fixed,...newFloor]).length,1);
 }
 for(const z of [-.3,.15])assert.equal(firstOwners(next,[0,.4,z],[0,-1,0],[next.scene.fixed,...newFloor]).length,1);
 // Floor ownership changes only inside solid hatch material or the flush sill.
 for(const x of [-.6,0,.6])for(const z of [-.09,0,.085])assert.equal(firstOwners(next,[x,.3,z],[0,-1,0],[next.scene.fixed,...newFloor]).length,1);
 for(const mesh of [...oldFloor,...context.children]){mesh.geometry.dispose();mesh.material.dispose();}dispose(next.scene);
});

test('actual inspection wall follows the outer frame profile and cannot duplicate the inner reveal',()=>{
 const next=create(current),W=next.plan.aperture.width,H=next.plan.aperture.top;
 const context=buildInspectionContext(THREE,next.plan,new THREE.MeshBasicMaterial(),new THREE.MeshBasicMaterial());
 const oldWall=new THREE.Mesh(new THREE.BoxGeometry(1,2.8,.15),new THREE.MeshBasicMaterial());
 oldWall.name='old_context_right_wall';oldWall.position.copy(point(next.plan,[W/2+.5,1.4,0]));
 if(next.plan.axis==='x')oldWall.rotation.y=Math.PI/2;oldWall.updateMatrixWorld(true);
 assert.equal(firstOwners(next,[0,1,.07],[1,0,0],[next.scene.fixed,oldWall]).length,2);
 for(const side of [-1,1])for(const z of [-.07,0,.07]){
  assert.equal(firstOwners(next,[0,1,z],[side,0,0],[next.scene.fixed,context]).length,1);
  assert.equal(firstOwners(next,[0,1,z],[0,1,0],[next.scene.fixed,context]).length,1);
 }
 // Both normal directions see a continuous wall beyond the frame, not a gap.
 for(const side of [-1,1])for(const sample of [[W/2+.24,H*.5],[0,H+.25]]){
  assert.equal(firstOwners(next,[...sample,side*.5],[0,0,-side],[next.scene.fixed,context]).length,1);
 }
 for(const mesh of [oldWall,...context.children]){mesh.geometry.dispose();mesh.material.dispose();}dispose(next.scene);
});

test('leaf, hardware, aperture and exact moving swing remain byte-equivalent in plan data',()=>{
 for(const name of ['base','renamed','wider','translated'])for(const id of current.pressureHatchIds(fixture(name))){
  const old=previous.planPressureHatch(fixture(name),id),next=current.planPressureHatch(fixture(name),id);
  for(const key of ['aperture','moving','hinge','hingeLocal','openAngle','localLeafCenter','leafWidth','leafHeight'])assert.deepEqual(next[key],old[key]);
  assert.deepEqual(current.hatchSwingBounds(next),previous.hatchSwingBounds(old));
  assert.deepEqual(next.colliders.filter(c=>c.motion==='kinematic'),old.colliders.filter(c=>c.motion==='kinematic'));
 }
});

test('correction applies in both axes and room-A directions without changing materials or shadow bias',()=>{
 const base=fixture('base'),rotated=structuredClone(base);
 for(const r of rotated.rooms){[r.x,r.z]=[r.z,r.x];[r.width,r.depth]=[r.depth,r.width];}
 for(const p of rotated.portals)p.axis=p.axis==='x'?'z':'x';
 const variants=[base,rotated];for(const g of [base,rotated]){const swap=structuredClone(g);swap.portals.forEach(p=>[p.room_a,p.room_b]=[p.room_b,p.room_a]);variants.push(swap);}
 for(const g of variants){const next=create(current,g),W=next.plan.aperture.width;
  assert.equal(firstOwners(next,[W/2+.04,1,.5],[0,0,-1]).length,1);
  assert.equal(firstOwners(next,[0,1,.07],[1,0,0]).length,1);dispose(next.scene);}
 const before=readFileSync(new URL('preimages/inspection.mjs',import.meta.url),'utf8');
 const after=readFileSync(new URL('preview/assets/inspection.mjs',import.meta.url),'utf8');
 assert.equal(before.match(/key\.shadow\.bias=[^;]+/)[0],after.match(/key\.shadow\.bias=[^;]+/)[0]);
 const oldSource=readFileSync(new URL('preimages/tools/world_builder_engine/pressure_hatch.mjs',import.meta.url),'utf8');
 const newSource=readFileSync(new URL('candidate/tools/world_builder_engine/pressure_hatch.mjs',import.meta.url),'utf8');
 assert.equal(oldSource.slice(oldSource.indexOf('export function buildPressureHatch')),newSource.slice(newSource.indexOf('export function buildPressureHatch')));
});
