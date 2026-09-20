import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {compileFrame,solveFrameContacts,finishFrameContactVelocities,frameContactReport} from '../tools/world_builder_components/bedding/frame_contacts.mjs';
import {MattressSurface} from '../tools/world_builder_components/bedding/mattress_physics.mjs';
import {solveSurfaceContacts,finishSurfaceContactVelocities,surfaceContactReport} from '../tools/world_builder_components/bedding/surface_contacts.mjs';
const parts=JSON.parse(readFileSync(new URL('./fixtures/bed_contact_single.json',import.meta.url))).parts;
const rail=parts.find(p=>p.id==='right_side_rail'),frame=compileFrame([rail]),box=frame[0];
const mid=box.min.map((v,i)=>(v+box.max[i])/2),checks=[];
function triangle(points){const p=Float64Array.from(points.flat());return {p,prev:p.slice(),v:new Float64Array(9),count:3,triangles:[0,1,2],invMass:Float64Array.from([1,1,1]),margin:.006,grab:null};}
// Independent dense barycentric interior test against the mesh-derived planes.
// It does not call the polygon clipper/contact reporter.
function dense(c,f,n=50){let max=0;for(let i=0;i<=n;i++)for(let j=0;j<=n-i;j++){
 const w=[i/n,j/n,1-(i+j)/n],p=[0,1,2].map(a=>w.reduce((s,v,k)=>s+v*c.p[3*k+a],0));
 for(const b of f){const depth=Math.min(...b.planes.map(q=>q.d-q.n.reduce((s,v,a)=>s+v*p[a],0)));max=Math.max(max,depth);}
 }return max;}
function solve(c,f=frame){for(let i=0;i<8;i++)solveFrameContacts(c,f,{passes:4,reset:i===0});return frameContactReport(c,f);}
function test(name,fn){fn();checks.push(name);}
const start=performance.now();let status='PASS',failure=null;
try{
 test('Exact chamfer planes retain geometry and reject an AABB-only false collision',()=>{
  assert.equal(box.planes.length,26);const x=box.max[0]-.00015,y=box.max[1]-.00015,z=mid[2];
  const c=triangle([[x,y,z],[x,y,z+.0001],[x-.0001,y,z]]);c.margin=0;
  const original=Array.from(c.p);assert.equal(frameContactReport(c,frame).intersecting_triangle_part_pairs,0);solve(c);assert.deepEqual(Array.from(c.p),original);
 });
 test('Face penetration resolves by moving the actual same arrays without launch velocity',()=>{
  const c=triangle([[box.max[0]-.006,.30,-.05],[box.max[0]-.006,.34,.05],[box.max[0]-.006,.37,-.05]]),identity=c.p;
  assert(dense(c,frame)>.005);assert(frameContactReport(c,frame).intersecting_triangle_part_pairs>0);
  assert.equal(solve(c).intersecting_triangle_part_pairs,0);assert(dense(c,frame)<1e-10);assert.equal(c.p,identity);
  assert(c.p.every((v,i)=>Math.abs(v-c.prev[i])<1e-12));assert(c.v.every(v=>v===0));
 });
 test('Bevel and three-way corner inside points resolve against chamfers',()=>{
  for(const near of [[box.max[0]-.0023,box.max[1]-.0023,mid[2]],[box.max[0]-.0025,box.max[1]-.0025,box.max[2]-.0025]]){
   const c=triangle([near,near.map((v,i)=>v+(i===1?-.0001:0)),near.map((v,i)=>v+(i===2?-.0001:0))]);c.margin=.001;
   assert(dense(c,frame)>.0001);assert.equal(solve(c).intersecting_triangle_part_pairs,0);assert(dense(c,frame)<1e-10);
  }
 });
 test('Rail through triangle interior is detected although every triangle vertex is outside',()=>{
  const c=triangle([[mid[0]-.25,mid[1],-1.5],[mid[0]+.25,mid[1],-1.5],[mid[0],mid[1],1.5]]);
  for(let i=0;i<3;i++)assert(box.planes.some(q=>q.n.reduce((s,v,a)=>s+v*c.p[3*i+a],0)>q.d));
  assert(dense(c,frame)>.02);assert(frameContactReport(c,frame).intersecting_triangle_part_pairs>0);
  assert.equal(solve(c).intersecting_triangle_part_pairs,0);assert(dense(c,frame)<1e-10);
 });
 test('Previous outside side keeps a falling cloth contact above a thin rail',()=>{
  const c=triangle([[mid[0]-.01,box.max[1]-.01,-.03],[mid[0]+.01,box.max[1]-.01,-.03],[mid[0],box.max[1]-.01,.03]]);
  for(let i=0;i<3;i++)c.prev[3*i+1]=box.max[1]+.01;
  solve(c);assert(c.p[1]>box.max[1]&&c.p[4]>box.max[1]&&c.p[7]>box.max[1]);
 });
 test('Held point and all-zero masses remain stable with unresolved contacts reported',()=>{
  const c=triangle([[mid[0],mid[1],0],[mid[0]+.01,mid[1],.01],[mid[0],mid[1]+.01,0]]);c.invMass.fill(0);
  const before=Array.from(c.p);solve(c);assert.deepEqual(Array.from(c.p),before);assert(frameContactReport(c,frame).intersecting_triangle_part_pairs>0);
  c.invMass.fill(1);c.grab={index:0};solve(c);assert.deepEqual(Array.from(c.p.slice(0,3)),before.slice(0,3));assert(c.p.every(Number.isFinite));
 });
 test('Previous side entry wins for a near-horizontal triangle instead of lifting it onto the rail',()=>{
  const c=triangle([[box.max[0]-.003,mid[1],-.03],[box.max[0]-.005,mid[1],.03],[box.max[0]-.002,mid[1],.03]]);
  for(let i=0;i<3;i++)c.prev[3*i]=box.max[0]+.01;
  solve(c);assert.equal(frameContactReport(c,frame).intersecting_triangle_part_pairs,0);
  assert(c.p[0]>box.max[0]&&c.p[3]>box.max[0]&&c.p[6]>box.max[0]);
  assert(c.p[1]===mid[1]&&c.p[4]===mid[1]&&c.p[7]===mid[1]);
 });
 test('Under-frame entry resolves downward and a separated grazing triangle remains unchanged',()=>{
  const c=triangle([[mid[0]-.01,box.min[1]+.003,-.02],[mid[0]+.01,box.min[1]+.003,-.02],[mid[0],box.min[1]+.003,.02]]);
  for(let i=0;i<3;i++)c.prev[3*i+1]=box.min[1]-.01;
  solve(c);assert(c.p[1]<box.min[1]&&c.p[4]<box.min[1]&&c.p[7]<box.min[1]);
  const g=triangle([[mid[0]-.01,box.max[1]+.01,-.02],[mid[0]+.01,box.max[1]+.01,-.02],[mid[0],box.max[1]+.01,.02]]),before=Array.from(g.p);
  solve(g);assert.deepEqual(Array.from(g.p),before);
 });
 test('Contact velocity removes inward component while preserving outward motion',()=>{
  const c=triangle([[box.max[0]-.002,.30,0],[box.max[0]-.002,.34,.02],[box.max[0]-.002,.37,0]]);solve(c);
  c.v.set([-1,0,0,-1,0,0,-1,0,0]);finishFrameContactVelocities(c,1/240);
  assert(c.v[0]>=-1e-10&&c.v[3]>=-1e-10&&c.v[6]>=-1e-10);
  c.v.set([1,0,0,1,0,0,1,0,0]);finishFrameContactVelocities(c,1/240);assert.deepEqual(Array.from(c.v),[1,0,0,1,0,0,1,0,0]);
 });
 test('Repeated solver history does not multiply contact friction',()=>{
  const a=triangle([[box.max[0]-.002,.30,0],[box.max[0]-.002,.34,.02],[box.max[0]-.002,.37,0]]);solve(a);
  const b=triangle([[0,0,0],[0,0,0],[0,0,0]]);b.p.set(a.p);b.prev.set(a.prev);b.frameActiveContacts=Array.from({length:40},()=>a.frameActiveContacts).flat();
  a.v.set([-1,0,1,-1,0,1,-1,0,1]);b.v.set(a.v);finishFrameContactVelocities(a,1/240);finishFrameContactVelocities(b,1/240);
  assert.deepEqual(Array.from(a.v),Array.from(b.v));
 });
 test('A triangle leaving the finite rail face receives no stale infinite-plane impulse',()=>{
  const c=triangle([[box.max[0]-.002,.30,0],[box.max[0]-.002,.34,.02],[box.max[0]-.002,.37,0]]);solve(c);
  for(let i=0;i<3;i++)c.p[3*i+2]+=box.max[2]+1;
  assert.equal(frameContactReport(c,frame).intersecting_triangle_part_pairs,0);
  c.v.set([-1,0,1,-1,0,1,-1,0,1]);const before=Array.from(c.v);finishFrameContactVelocities(c,1/240);assert.deepEqual(Array.from(c.v),before);
 });
 test('Coupled frame and mattress projection preserve physical previous positions',()=>{
  const c=triangle([[box.max[0]-.002,.30,0],[box.max[0]-.002,.34,.02],[box.max[0]-.002,.37,0]]);c.splitPositionStabilization=false;
  const previous=Array.from(c.prev);solve(c);assert.deepEqual(Array.from(c.prev),previous);assert.notDeepEqual(Array.from(c.p),previous);
  const mat=new MattressSurface({width:1,length:2,base:.385,top:.565}),s=triangle([[.45,.60,0],[.55,.45,.08],[.55,.45,-.08]]);s.splitPositionStabilization=false;
  const prior=Array.from(s.prev);solveSurfaceContacts(s,mat,{passes:8});assert(surfaceContactReport(s,mat).max_penetration_m<1e-8);assert.deepEqual(Array.from(s.prev),prior);
 });
 test('Surface velocity contacts survive a converged solver pass and deduplicate friction',()=>{
  const mat=new MattressSurface({width:1,length:2,base:.385,top:.565}),c=triangle([[-.02,.564,0],[.02,.564,0],[0,.564,.04]]);
  solveSurfaceContacts(c,mat,{passes:4});assert(c.surfaceActiveContacts.length>0);
  solveSurfaceContacts(c,mat,{passes:2,reset:false});assert(c.surfaceActiveContacts.length>0);
  const b=triangle([[0,0,0],[0,0,0],[0,0,0]]);b.p.set(c.p);b.surfaceActiveContacts=Array.from({length:40},()=>c.surfaceActiveContacts).flat();
  c.v.set([1,-1,0,1,-1,0,1,-1,0]);b.v.set(c.v);finishSurfaceContactVelocities(c,mat,1/240);finishSurfaceContactVelocities(b,mat,1/240);
  assert.deepEqual(Array.from(c.v),Array.from(b.v));assert(c.v[1]>=-1e-10&&c.v[4]>=-1e-10&&c.v[7]>=-1e-10);
 });
}catch(error){status='FAIL';failure=String(error.stack);process.exitCode=1;}
const result={status,checks,elapsed_ms:performance.now()-start,failure};writeFileSync(new URL('./CONTACT-UNIT-RESULT.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
