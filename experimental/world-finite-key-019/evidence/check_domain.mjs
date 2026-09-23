import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {FiniteTopDomain} from './candidate/finite_top_domain.mjs';
import {FiniteTopDomain as Predecessor016} from '../world-finite-top-domain-candidate-016/candidate/finite_top_domain.mjs';
import {solveSurfaceContacts,surfaceContactReport,finishSurfaceContactVelocities} from './candidate/surface_contacts.mjs';
import {solveSurfaceContacts as oldSolve} from './baseline/surface_contacts.mjs';
const results=[],start=performance.now();
function fixture(points,previous=points){
 const c={count:3,p:Float64Array.from(points.flat()),prev:Float64Array.from(previous.flat()),v:new Float64Array(9),invMass:new Float64Array([1,1,1]),triangles:[0,1,2],margin:.006,splitPositionStabilization:false};
 const s={base:.385,width:1,length:2,maximumHeight:.59,nx:1,nz:1,count:4,p:new Float64Array([-.5,.565,-1,.5,.565,-1,-.5,.565,1,.5,.565,1]),prev:new Float64Array([.565,.565,.565,.565]),sampleTop:()=>({height:.565,velocity:0})};
 const d=new FiniteTopDomain(c,s);c.finiteTopDomain=d;return {c,s,d};
}
function move(f,points){for(let i=0;i<3;i++){f.c.p.set(points[i],3*i);f.d.observeVertex(i);}}
const tri=y=>[[-.1,y,0],[.1,y,0],[0,y,.2]];
function test(name,run){try{const detail=run();results.push({name,status:'PASS',detail});}catch(e){results.push({name,status:'FAIL',error:String(e.stack)});}}
test('below slab has no false position velocity or report contact',()=>{
 const f=fixture(tri(.2));const before=Array.from(f.c.p),prev=Array.from(f.c.prev);assert(f.d.clear([0,1,2],.006));
 assert.equal(solveSurfaceContacts(f.c,f.s).count,0);assert.deepEqual(Array.from(f.c.p),before);assert.deepEqual(Array.from(f.c.prev),prev);
 f.c.surfaceActiveContacts=[{ids:[0,1,2],weights:[.3,.3,.4]}];f.c.v.fill(-.1);const v=Array.from(f.c.v);finishSurfaceContactVelocities(f.c,f.s,1/240);assert.deepEqual(Array.from(f.c.v),v);
 assert.equal(surfaceContactReport(f.c,f.s).contact_count,0);delete f.c.finiteTopDomain;assert(oldSolve(f.c,f.s).count>0);assert(Math.max(...f.c.p.filter((_,i)=>i%3===1))>.2);return f.d.snapshot();
});
test('supported cloth retains exact prior contact corrections',()=>{
 const f=fixture(tri(.56),tri(.58)),g=fixture(tri(.56),tri(.58));delete g.c.finiteTopDomain;
 assert(!f.d.clear([0,1,2],.006));const a=solveSurfaceContacts(f.c,f.s),b=oldSolve(g.c,g.s);assert.deepEqual(Array.from(f.c.p),Array.from(g.c.p));assert.deepEqual(a,b);return {contacts:a.count};
});
test('above-to-below crossing never rearms solely below bottom',()=>{
 const f=fixture(tri(.70));move(f,tri(.2));assert(!f.d.clear([0,1,2],.006));assert(!f.d.clear([0],.006));assert(solveSurfaceContacts(f.c,f.s).count>0);return f.d.snapshot();
});
test('uncertified pose can exit side then route beneath and reenter',()=>{
 const f=fixture(tri(.55));move(f,[[.8,.55,0],[1,.55,0],[.9,.55,.2]]);assert(f.d.clear([0,1,2],.006));
 move(f,[[.8,.2,0],[1,.2,0],[.9,.2,.2]]);move(f,tri(.2));assert(f.d.clear([0,1,2],.006));assert.equal(solveSurfaceContacts(f.c,f.s).count,0);return f.d.snapshot();
});
test('diagonal side-to-bottom jump without shared separator stays held',()=>{
 const f=fixture([[.8,.55,0],[1,.55,0],[.9,.55,.2]]);move(f,tri(.2));assert(!f.d.clear([0,1,2],.006));return f.d.snapshot();
});
test('mixed exterior vertices cannot certify a crossing triangle',()=>{
 const f=fixture([[-.8,.5,-.3],[.8,.5,-.3],[0,.5,1.3]]);assert(f.d.clear([0],.006));assert(f.d.clear([1],.006));assert(f.d.clear([2],.006));assert(!f.d.clear([0,1,2],.006));assert(solveSurfaceContacts(f.c,f.s).count>0);
});
test('bottom skin and epsilon touching remain held',()=>{for(const y of [.385-.006,.385-.006-1e-8,.385-.006+1e-10])assert(!fixture(tri(y)).d.clear([0,1,2],.006));});
test('one above vertex blocks whole-triangle exclusion',()=>{assert(!fixture([[-.1,.2,0],[.1,.2,0],[0,.4,.2]]).d.clear([0,1,2],.006));});
test('inverted winding gives identical certificate and correction',()=>{const f=fixture(tri(.2));f.c.triangles.reverse();assert(f.d.clear([2,1,0],.006));assert.equal(solveSurfaceContacts(f.c,f.s).count,0);});
test('moving top inside fixed box keeps underside certificate',()=>{const f=fixture(tri(.2));for(let i=0;i<4;i++){f.s.p[3*i+1]=.42;f.d.observeTop(i);}assert(f.d.clear([0,1,2],.006));});
test('moving top through base permanently disables exclusion',()=>{const f=fixture(tri(.2));f.s.p[1]=.3;f.d.observeTop(0);f.s.p[1]=.565;f.d.observeTop(0);assert(!f.d.clear([0,1,2],.006));assert.equal(f.d.reason,'TOP_OUTSIDE_FIXED_BOX_OR_XZ_CHANGED');});
test('unobserved position changes disable exclusion',()=>{const f=fixture(tri(.2));f.c.p[0]+=.01;assert(!f.d.clear([0,1,2],.006));assert.equal(f.d.reason,'UNOBSERVED_POSITION_WRITE');});
test('invalid geometry and changed base remain held',()=>{const f=fixture(tri(.2));f.s.base=.4;assert(!f.d.clear([0,1,2],.006));const g=fixture(tri(.2));g.c.p[0]=NaN;g.d.observeVertex(0);assert(!g.d.clear([0,1,2],.006));});
test('invalid finite dimensions and grid cardinality remain held',()=>{for(const patch of [{width:-1},{length:0},{nx:0},{count:3}]){const f=fixture(tri(.2));Object.assign(f.s,patch);const d=new FiniteTopDomain(f.c,f.s);assert(!d.clear([0,1,2],.006));assert(d.reason);}});

// Reproduce the held predecessor without editing its files. Test particles,
// edges and full triangles because all exclusion gates share this certificate.
function invalidTop(Type,axis,value,when){
 const f=fixture(tri(.2)),original=f.s.p[axis];
 if(when==='initial')f.s.p[axis]=value;
 const d=new Type(f.c,f.s);
 if(when==='mutation'){f.s.p[axis]=value;d.observeTop(0);}
 const invalid=d.snapshot(),skips=[[0],[0,1],[0,1,2]].map(ids=>d.clear(ids,.006));
 f.s.p[axis]=original;d.observeTop(0);
 return {invalid,skips,after_restore:d.snapshot(),skip_after_restore:d.clear([0,1,2],.006)};
}
for(const when of ['initial','mutation'])for(const [label,axis] of [['X',0],['Z',2]]){
 test(`${when} NaN top ${label} reproduces016 false certificate and017 holds`,()=>{
  const old=invalidTop(Predecessor016,axis,NaN,when),next=invalidTop(FiniteTopDomain,axis,NaN,when);
  assert(old.invalid.valid);assert(old.skips.every(Boolean));
  assert(!next.invalid.valid);assert(next.skips.every(v=>!v));
  assert.equal(next.invalid.reason,'TOP_OUTSIDE_FIXED_BOX_OR_XZ_CHANGED');
  assert(!next.after_restore.valid);assert(!next.skip_after_restore);
  return {axis:label,value:'NaN',when,predecessor016:old,successor017:next};
 });
}
for(const when of ['initial','mutation']){
 test(`${when} nonfinite top XYZ always disables exclusion`,()=>{
  const cases=[];
  for(const [axis,label] of [[0,'X'],[1,'Y'],[2,'Z']])for(const value of [NaN,Infinity,-Infinity]){
   const out=invalidTop(FiniteTopDomain,axis,value,when);
   assert(!out.invalid.valid);assert(out.skips.every(v=>!v));assert(!out.after_restore.valid);assert(!out.skip_after_restore);
   cases.push({axis:label,value:String(value),reason:out.invalid.reason});
  }
  return cases;
 });
}

const out={status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',tests:results.length,results,elapsed_ms:performance.now()-start,scope:'Actual surface solver calls and conservative finite-domain cases; no full coupled replay or installed edit.'};
writeFileSync(new URL('DOMAIN-TESTS.json',import.meta.url),JSON.stringify(out,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(out));if(out.status!=='PASS')process.exitCode=1;
