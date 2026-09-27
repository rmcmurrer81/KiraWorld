import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {createDoorSystem} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {planHatchArchitecture,buildHatchStructuralMesh as repaired} from './candidate/tools/world_builder_engine/pressure_hatch_architecture.mjs';
import {buildHatchStructuralMesh as parent} from './preimages/tools/world_builder_engine/pressure_hatch_architecture.mjs';
const read=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const cases=()=>{
 const all=['base','renamed','wider','translated'].map(n=>read('fixtures/'+n+'.json')),rotated=structuredClone(all[0]);
 for(const r of rotated.rooms){[r.x,r.z]=[r.z,r.x];[r.width,r.depth]=[r.depth,r.width];}
 for(const p of rotated.portals)p.axis=p.axis==='x'?'z':'x';
 for(const p of rotated.primitives){[p.position[0],p.position[2]]=[p.position[2],p.position[0]];[p.size[0],p.size[2]]=[p.size[2],p.size[0]];}
 for(const c of rotated.colliders)for(const k of ['min','max'])[c[k][0],c[k][2]]=[c[k][2],c[k][0]];
 for(const s of rotated.support_surfaces){[s.min_x,s.min_z]=[s.min_z,s.min_x];[s.max_x,s.max_z]=[s.max_z,s.max_x];}
 for(const route of rotated.routes)for(const point of route.points)[point[0],point[2]]=[point[2],point[0]];
 const reverse=structuredClone(rotated);reverse.portals.forEach(p=>[p.room_a,p.room_b]=[p.room_b,p.room_a]);
 return all.concat([rotated,reverse,read('fixtures/base.json')]);
};
const close=(a,b,label)=>assert.ok(Math.abs(a-b)<3e-5,`${label}: ${a} vs ${b}`);
const dispose=root=>root.traverse(o=>o.geometry?.dispose());
function original(p,mod,sign){
 const geometry=sign===null?new THREE.BoxGeometry(...p.size).toNonIndexed():new THREE.PlaneGeometry(p.size[mod.planeAxes[0]],p.size[1]).toNonIndexed();
 const mesh=new THREE.Mesh(geometry);mesh.position.set(...p.position);
 if(sign!==null){mesh.position.setComponent(mod.normalAxis,p.position[mod.normalAxis]+sign*(p.size[mod.normalAxis]/2+.0008));
  mesh.rotation.y=mod.normalAxis===0?(sign>0?Math.PI/2:-Math.PI/2):(sign<0?Math.PI:0);}
 mesh.updateMatrixWorld(true);geometry.applyMatrix4(mesh.matrixWorld);return geometry;
}
// Derive the affine UV at a point from the actual old Three triangle attributes,
// not from a duplicate of the repaired face formula.
function oldUVAt(geometry,point,normal){
 const pos=geometry.attributes.position,norm=geometry.attributes.normal,uv=geometry.attributes.uv;
 for(let i=0;i<pos.count;i+=3){
  const normalOld=new THREE.Vector3().fromBufferAttribute(norm,i);
  if(normalOld.dot(normal)<.999999)continue;
  const a=new THREE.Vector3().fromBufferAttribute(pos,i),b=new THREE.Vector3().fromBufferAttribute(pos,i+1),c=new THREE.Vector3().fromBufferAttribute(pos,i+2);
  if(Math.abs(normalOld.dot(point.clone().sub(a)))>3e-5)continue;
  const bary=new THREE.Triangle(a,b,c).getBarycoord(point,new THREE.Vector3());
  return new THREE.Vector2().fromBufferAttribute(uv,i).multiplyScalar(bary.x)
   .add(new THREE.Vector2().fromBufferAttribute(uv,i+1).multiplyScalar(bary.y))
   .add(new THREE.Vector2().fromBufferAttribute(uv,i+2).multiplyScalar(bary.z));
 }
 return null;
}

test('cut floors/walls preserve every retained BoxGeometry face UV with unchanged material repeats',()=>{
 const seen=new Set();let witnesses=0;
 for(const g of cases()){
  const architecture=planHatchArchitecture(g,createDoorSystem(g).hatchPlans());
  for(const p of g.primitives){const mod=architecture.modifications[p.id];if(!mod)continue;
   const map=new THREE.Texture();map.repeat.set(Math.max(1,p.size[0]),Math.max(1,p.size[2]));map.updateMatrix();
   const material=new THREE.MeshStandardMaterial({map}),before=map.repeat.toArray();
   const root=repaired(THREE,p,material,architecture),actual=root.children[0].geometry,old=original(p,mod,null);
   assert.equal(root.children[0].material,material);assert.deepEqual(map.repeat.toArray(),before);
   for(let i=0;i<actual.attributes.position.count;i++){
    const point=new THREE.Vector3().fromBufferAttribute(actual.attributes.position,i),normal=new THREE.Vector3().fromBufferAttribute(actual.attributes.normal,i),expected=oldUVAt(old,point,normal);
    const uv=new THREE.Vector2().fromBufferAttribute(actual.attributes.uv,i);assert.ok(Number.isFinite(uv.x)&&Number.isFinite(uv.y));
    if(!expected)continue;witnesses++;seen.add(p.role+':'+normal.toArray().map(v=>Math.round(v)).join(','));
    close(uv.x,expected.x,p.id+' U');close(uv.y,expected.y,p.id+' V');
    uv.applyMatrix3(map.matrix);expected.applyMatrix3(map.matrix);close(uv.x,expected.x,'repeated U');close(uv.y,expected.y,'repeated V');
   }
   old.dispose();dispose(root);material.dispose();map.dispose();
  }
 }
 for(const key of ['floor:0,1,0','floor:0,-1,0','wall:1,0,0','wall:-1,0,0','wall:0,0,1','wall:0,0,-1'])assert.ok(seen.has(key),key);
 assert.ok(witnesses>10000);
});

test('both decorative cardinal wall panels match the actual old rotated PlaneGeometry UVs',()=>{
 const seen=new Set();
 for(const g of cases()){
  const architecture=planHatchArchitecture(g,createDoorSystem(g).hatchPlans());
  for(const p of g.primitives){const mod=architecture.modifications[p.id];if(!mod||p.role!=='wall')continue;
   for(const sign of [-1,1]){
    const map=new THREE.Texture();map.repeat.set(Math.max(1,p.size[mod.planeAxes[0]]/.95),Math.max(1,p.size[1]/1.05));
    const material=new THREE.MeshStandardMaterial({map}),before=map.repeat.toArray();
    const root=repaired(THREE,p,material,architecture,{panelNormal:sign,panelOffset:.0008}),actual=root.children[0].geometry,old=original(p,mod,sign);
    assert.equal(root.children[0].material,material);assert.deepEqual(map.repeat.toArray(),before);seen.add(mod.normalAxis+':'+sign);
    for(let i=0;i<actual.attributes.position.count;i++){
     const expected=oldUVAt(old,new THREE.Vector3().fromBufferAttribute(actual.attributes.position,i),new THREE.Vector3().fromBufferAttribute(actual.attributes.normal,i));
     assert.ok(expected,p.id);close(actual.attributes.uv.getX(i),expected.x,'panel U');close(actual.attributes.uv.getY(i),expected.y,'panel V');
    }
    old.dispose();dispose(root);material.dispose();map.dispose();
   }
  }
 }
 assert.deepEqual([...seen].sort(),['0:-1','0:1','2:-1','2:1']);
});

test('UV correction changes no geometry, normal, index, hatch transform, material or source plan',()=>{
 const material=new THREE.MeshStandardMaterial();
 for(const g of cases()){
  const before=JSON.stringify(g),architecture=planHatchArchitecture(g,createDoorSystem(g).hatchPlans()),saved=JSON.stringify(architecture);
  for(const p of g.primitives){const mod=architecture.modifications[p.id];if(!mod)continue;
   for(const options of p.role==='wall'?[{}, {panelNormal:-1,panelOffset:.0008},{panelNormal:1,panelOffset:.0008}]:[{}]){
    const a=parent(THREE,p,material,architecture,options),b=repaired(THREE,p,material,architecture,options);
    assert.equal(a.name,b.name);assert.deepEqual(a.userData,b.userData);assert.deepEqual(a.matrix.toArray(),b.matrix.toArray());
    assert.equal(a.children.length,b.children.length);
    for(let i=0;i<a.children.length;i++){
     const x=a.children[i],y=b.children[i];assert.equal(x.material,y.material);assert.equal(x.name,y.name);
     for(const key of Object.keys(x.geometry.attributes).filter(k=>k!=='uv'))assert.deepEqual(x.geometry.attributes[key].array,y.geometry.attributes[key].array,key);
     assert.deepEqual(x.geometry.index.array,y.geometry.index.array);assert.deepEqual(x.geometry.boundingBox,y.geometry.boundingBox);
    }
    dispose(a);dispose(b);
   }
  }
  assert.equal(JSON.stringify(g),before);assert.equal(JSON.stringify(architecture),saved);
 }
 material.dispose();
});

test('translation changes world positions while leaving normalized UV phase and texel scale invariant',()=>{
 const g=cases().at(-1),architecture=planHatchArchitecture(g,createDoorSystem(g).hatchPlans()),material=new THREE.MeshStandardMaterial(),offset=[17.125,3.5,-29.75];
 for(const p of g.primitives){const mod=architecture.modifications[p.id];if(!mod)continue;
  const shifted=structuredClone(architecture),m=shifted.modifications[p.id];
  m.polygons=m.polygons.map(poly=>poly.map(v=>v.map((x,i)=>x+offset[m.planeAxes[i]])));m.normalMin+=offset[m.normalAxis];m.normalMax+=offset[m.normalAxis];
  const moved={...p,position:p.position.map((x,i)=>x+offset[i])};
  for(const options of p.role==='wall'?[{}, {panelNormal:-1,panelOffset:.0008},{panelNormal:1,panelOffset:.0008}]:[{}]){
   const a=repaired(THREE,p,material,architecture,options),b=repaired(THREE,moved,material,shifted,options),uvA=a.children[0].geometry.attributes.uv,uvB=b.children[0].geometry.attributes.uv;
   assert.equal(uvA.count,uvB.count);for(let i=0;i<uvA.count;i++){close(uvA.getX(i),uvB.getX(i),'translated U');close(uvA.getY(i),uvB.getY(i),'translated V');}
   dispose(a);dispose(b);
  }
 }
 material.dispose();
});
