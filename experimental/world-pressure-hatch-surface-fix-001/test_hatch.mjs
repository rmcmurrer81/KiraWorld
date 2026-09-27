import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {pressureHatchIds,planPressureHatch,buildPressureHatch,hatchCollidersAt,hatchSwingBounds} from './candidate/tools/world_builder_engine/pressure_hatch.mjs';
import * as exportRecipe from './candidate/tools/world_builder_engine/layout_package_assets/source/pressure_hatch.mjs';
import {createDoorSystem} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/horizontal_navigation.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
const read=name=>JSON.parse(readFileSync(new URL('fixtures/'+name+'.json',import.meta.url),'utf8'));
const fixtures=['base','renamed','wider','translated'];
const eps=2e-6;
const inside=(p,b)=>p.every((v,i)=>v>=b.min[i]-eps&&v<=b.max[i]+eps);
const points=mesh=>{const a=mesh.geometry.attributes.position,result=[];for(let i=0;i<a.count;i++)result.push(new THREE.Vector3().fromBufferAttribute(a,i).applyMatrix4(mesh.matrixWorld).toArray());return result;};
const dispose=scene=>{const materials=new Set();for(const m of scene.meshes.values()){m.geometry.dispose();materials.add(m.material);}materials.forEach(m=>m.dispose());};
function collisionParts(plan,angle){return new Map(hatchCollidersAt(plan,angle).map(c=>[c.id,c]));}

test('only explicit valid airlock pairs opt in; room names do not select a hatch',()=>{
  for(const name of fixtures){
    const geometry=read(name),ids=pressureHatchIds(geometry);
    assert.equal(ids.length,2);assert.deepEqual(ids,createDoorSystem(geometry).interlocks()[0].doorIds);
    for(const p of geometry.portals)assert.equal(planPressureHatch(geometry,p.id)!==null,ids.includes(p.id));
    const noRole=structuredClone(geometry);delete noRole.functional_program;
    assert.deepEqual(pressureHatchIds(noRole),[]);
    const broken=structuredClone(geometry);broken.portals=broken.portals.filter(p=>p.id!==ids[0]);
    assert.throws(()=>pressureHatchIds(broken),/exactly two/);
  }
});

test('the candidate and export copy are byte-exact shared recipes with detached frozen plans',()=>{
  const a=readFileSync(new URL('candidate/tools/world_builder_engine/pressure_hatch.mjs',import.meta.url));
  const b=readFileSync(new URL('candidate/tools/world_builder_engine/layout_package_assets/source/pressure_hatch.mjs',import.meta.url));
  assert.ok(a.equals(b));
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id);assert.deepEqual(plan,exportRecipe.planPressureHatch(g,id));
    assert.ok(Object.isFrozen(plan.colliders[0]));assert.equal(plan.capabilities.pressureSimulation,false);
    assert.equal(plan.capabilities.latchState,'static_retracted');assert.equal(plan.capabilities.enabledInViewer,false);
    g.title='changed caller data';assert.equal(plan.origin.length,3);
  }}
});

test('substantial frame, flush sill, continuous gasket and distinct bilateral controls are modeled',()=>{
  const g=read('base'),plan=planPressureHatch(g,pressureHatchIds(g)[0]);
  const gasket=plan.fixed.find(p=>p.id.endsWith('_continuous_gasket'));
  const surround=plan.fixed.find(p=>p.id.endsWith('_structural_surround'));
  assert.equal(gasket.shape,'ring');assert.equal(surround.shape,'ring');
  assert.ok(surround.outer.width-plan.aperture.width>.3);assert.ok(surround.size[2]>.17);
  assert.ok(surround.outer.radius>=.3);assert.ok(gasket.inner.bottom===0&&gasket.outer.bottom<0);
  assert.ok(plan.leafWidth>plan.aperture.width);assert.ok(plan.leafHeight>plan.aperture.top);
  assert.ok(plan.limits.centralStandingClearHeight>1.68);assert.equal(plan.limits.thresholdAboveFloor,0);
  for(const face of [-1,1]){
    for(const suffix of ['control_shaft_','control_wheel_','grab_bar_'])assert.ok(plan.moving.some(p=>p.id.endsWith(suffix+face)));
  }
  assert.equal(plan.moving.filter(p=>p.id.includes('_retracted_dog_')).length,3);
  assert.equal(plan.fixed.filter(p=>p.id.includes('_keeper_')&&!p.id.includes('support')).length,3);
  assert.equal(plan.moving.filter(p=>p.id.includes('_latch_rail_')).length,1);
});

test('every rendered vertex is enclosed by its declared owned collider at closed, partial and full poses',()=>{
  let vertices=0,parts=0,poses=0;
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id),scene=buildPressureHatch(THREE,plan);
    const owners=new Set([...plan.fixed,...plan.moving].map(p=>p.id));
    assert.equal(scene.meshes.size,owners.size);assert.equal(new Set(plan.colliders.map(c=>c.id)).size,plan.colliders.length);
    for(const c of plan.colliders){assert.ok(owners.has(c.owner));assert.ok(c.min.every((v,i)=>v<c.max[i]));}
    for(const fraction of [0,.25,.5,.75,1]){
      const angle=plan.openAngle*fraction;scene.setAngle(angle);const colliders=collisionParts(plan,angle);
      for(const mesh of scene.meshes.values()){
        const boxes=mesh.userData.colliderIds.map(id=>colliders.get(id));assert.ok(boxes.length&&boxes.every(Boolean));
        for(const point of points(mesh)){assert.ok(boxes.some(b=>inside(point,b)),`${name}/${id}/${mesh.name}/${fraction}: ${point}`);vertices++;}
        parts++;
      }
      poses++;
    }
    dispose(scene);
  }}
  assert.ok(vertices>500000);assert.equal(poses,40);assert.ok(parts>2000);
});

test('full continuous sweep mathematically encloses all rotated collider corners across 181 poses',()=>{
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id),sweep=hatchSwingBounds(plan);
    for(let step=0;step<=180;step++)for(const c of hatchCollidersAt(plan,plan.openAngle*step/180).filter(c=>c.motion==='kinematic')){
      assert.ok(inside(c.min,sweep));assert.ok(inside(c.max,sweep));
    }
  }}
});

test('fixed frame/glazing-free aperture has genuine through-space and a flush traversable floor',()=>{
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id),scene=buildPressureHatch(THREE,plan);scene.setAngle(0);
    const n=plan.axis==='x'?0:2,t=n===0?2:0;
    for(const side of [-1,1]){
      const origin=new THREE.Vector3(...plan.origin);origin.y+=1.1;origin.setComponent(n,origin.getComponent(n)+side*2);
      const direction=new THREE.Vector3();direction.setComponent(n,-side);
      const ray=new THREE.Raycaster(origin,direction,0,4);
      assert.equal(ray.intersectObject(scene.fixed,true).length,0,'Frame must have an open center.');
      assert.ok(ray.intersectObject(scene.pivot,true).length>0,'Closed hatch must block a ray from either side.');
    }
    const fixed=hatchCollidersAt(plan,0).filter(c=>c.motion==='static');
    const feet=[...plan.origin];feet[t]+=0;feet[1]=plan.origin[1];
    const capsuleBox={min:feet.map((v,i)=>v-(i===1?0:.34)),max:feet.map((v,i)=>v+(i===1?1.68:.34))};
    assert.ok(fixed.every(c=>!c.min.every((v,i)=>v<capsuleBox.max[i]&&c.max[i]>capsuleBox.min[i])),'Fixed threshold or frame blocks central standing passage.');
    dispose(scene);
  }}
});

test('closed leaf is in front of existing wall face and overlaps the gasket line from both sides',()=>{
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id),leaf=plan.moving.find(p=>p.id.endsWith('_reinforced_leaf'));
    assert.ok(plan.hingeLocal[2]-leaf.size[2]/2>.075);
    const gasket=plan.fixed.find(p=>p.id.endsWith('_continuous_gasket'));
    assert.ok(plan.hingeLocal[2]-leaf.size[2]/2<=gasket.center[2]+gasket.size[2]/2+eps);
    assert.ok(gasket.outer.width<leaf.size[0]);assert.ok(gasket.outer.top<plan.leafHeight);
    assert.ok(gasket.inner.bottom===0,'The sill contact line stays at floor height.');
  }}
});

test('ordinary source controllers remain unchanged; new motion is explicitly not admitted to them',()=>{
  const a=readFileSync(new URL('candidate/tools/world_builder_engine/walk_controller.mjs',import.meta.url));
  const b=readFileSync(new URL('preimages/tools/world_builder_engine/walk_controller.mjs',import.meta.url));assert.ok(a.equals(b));
  const g=read('base'),old=createDoorSystem(g).assemblies();
  for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id),current=old.find(a=>a.id===id),sweep=hatchSwingBounds(plan);
    assert.equal(plan.limits.requiresRevisedSwingAdmission,true);
    assert.notDeepEqual(sweep,current.swingBounds,'Expanded hatch must not silently inherit old bounds.');
  }
});

test('open hatches preserve forward/reverse standing passage and closed leaves block it',()=>{
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id),n=plan.axis==='x'?0:2,a=[...plan.origin],b=[...plan.origin];a[n]-=.7;b[n]+=.7;
    for(const [angle,expected] of [[0,'blocked'],[plan.openAngle,'clear']])for(const points of [[a,b],[b,a]]){
      const result=checkHorizontalRoute({id:'hatch_passage',points,avatar_radius:.34,avatar_height:1.68},
        {contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:hatchCollidersAt(plan,angle)});
      if(expected==='clear')assert.equal(result.status,'clear');else assert.notEqual(result.status,'clear');
    }
  }}
});

test('free-jamb keepers do not occupy moving hardware bounds through the complete swing',()=>{
  for(const name of fixtures){const g=read(name);for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id);
    for(let step=0;step<=180;step++){
      const colliders=hatchCollidersAt(plan,plan.openAngle*step/180),keepers=colliders.filter(c=>c.owner.includes('_keeper'));
      for(const moving of colliders.filter(c=>c.motion==='kinematic'))for(const keeper of keepers){
        assert.ok(!moving.min.every((v,i)=>v<keeper.max[i]-1e-6&&moving.max[i]>keeper.min[i]+1e-6),`${moving.id} crosses ${keeper.id}`);
      }
    }
  }}
});

test('larger reserved swing leaves existing furniture placements intact',()=>{
  for(const name of fixtures){const g=read(name),before=JSON.stringify(g),dressing=buildRoomDressing(g,createDoorSystem(g).assemblies());
    for(const id of pressureHatchIds(g)){
      const sweep=hatchSwingBounds(planPressureHatch(g,id));
      assert.ok(dressing.colliders.every(c=>!c.min.every((v,i)=>v<sweep.max[i]&&c.max[i]>sweep.min[i])));
    }
    assert.equal(JSON.stringify(g),before);
  }
});

test('opposite swing direction, invalid units and invalid program are rejected',()=>{
  const g=read('base'),plan=planPressureHatch(g,pressureHatchIds(g)[0]);
  assert.throws(()=>hatchCollidersAt(plan,-plan.openAngle));
  const mesh=buildPressureHatch(THREE,plan);assert.throws(()=>mesh.setAngle(-plan.openAngle));dispose(mesh);
  assert.throws(()=>pressureHatchIds({...g,units:'feet'}));assert.throws(()=>pressureHatchIds({...g,functional_program:[]}));
});

test('both portal axes and both swing directions have bounded mirrored assemblies',()=>{
  const base=read('base');
  const cases=[];
  for(const name of fixtures)cases.push(read(name));
  // Swapping adjacency reverses the room-A hinge side without changing the room program.
  const swapped=structuredClone(base);swapped.portals.forEach(p=>[p.room_a,p.room_b]=[p.room_b,p.room_a]);cases.push(swapped);
  // Rotate the synthetic layout 90 degrees around Y; no owner geometry is changed.
  const rotated=structuredClone(base);
  for(const r of rotated.rooms){[r.x,r.z]=[r.z,r.x];[r.width,r.depth]=[r.depth,r.width];}
  for(const p of rotated.portals)p.axis=p.axis==='x'?'z':'x';cases.push(rotated);
  const rotatedSwapped=structuredClone(rotated);rotatedSwapped.portals.forEach(p=>[p.room_a,p.room_b]=[p.room_b,p.room_a]);cases.push(rotatedSwapped);
  const modes=new Set();
  for(const g of cases)for(const id of pressureHatchIds(g)){
    const plan=planPressureHatch(g,id);modes.add(plan.axis+'/'+Math.sign(plan.openAngle));
    const scene=buildPressureHatch(THREE,plan);scene.setAngle(plan.openAngle);
    const collision=collisionParts(plan,plan.openAngle);
    for(const mesh of scene.meshes.values())for(const point of points(mesh))assert.ok(mesh.userData.colliderIds.some(id=>inside(point,collision.get(id))));
    dispose(scene);
  }
  assert.equal(modes.size,4);
});
