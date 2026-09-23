import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {FiniteTopDomain as Candidate020} from './candidate/finite_top_domain.mjs';
import {FiniteTopDomain as Predecessor019} from './reference019/candidate/finite_top_domain.mjs';

const plan=JSON.parse(readFileSync(new URL('PLAN.json',import.meta.url)));
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
for(const row of plan.sources)assert.equal(sha(row.path),row.sha256,row.path);
const start=performance.now();let stateComparisons=0,queryComparisons=0,mutationSteps=0,cases=0;
function fixture(Type,points){
 const c={count:4,p:Float64Array.from(points.flat()),prev:Float64Array.from(points.flat()),v:new Float64Array(12),invMass:new Float64Array([1,1,1,1]),triangles:[0,1,2,1,3,2],margin:.006};
 const s={base:.385,width:1,length:2,maximumHeight:.59,nx:1,nz:1,count:4,p:new Float64Array([-.5,.565,-1,.5,.565,-1,-.5,.565,1,.5,.565,1]),prev:new Float64Array([.565,.565,.565,.565])};
 return {c,s,d:new Type(c,s)};
}
function pair(points=[[-.1,.7,0],[.1,.7,0],[-.1,.7,.2],[.1,.7,.2]]){cases++;return [fixture(Candidate020,points),fixture(Predecessor019,points)];}
function same(a,b,label){
 assert.deepEqual(a.d.snapshot(),b.d.snapshot(),label+':counts/reason');
 assert.deepEqual(a.d.primitives,b.d.primitives,label+':certificates');
 for(const field of ['last','masks'])assert.deepEqual(a.d[field],b.d[field],label+':'+field);
 for(const field of ['p','prev','v'])assert.deepEqual(a.c[field],b.c[field],label+':'+field);
 stateComparisons++;
}
const ids=[[0],[1],[3],[0,1],[1,0],[1,3],[2,3,1],[0,1,2],[2,1,0]];
function queries(a,b,label){for(const index of ids){assert.equal(a.d.clear(index,.006),b.d.clear(index,.006),label);queryComparisons++;}same(a,b,label);}
let seed=0x91e10da5;
const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/2**32;};
const boundary=[-.50600001,-.506,.506,.50600001,.37899999,.379,.596,.59600001,-1.00600001,1.00600001,0,-0];
for(let trial=0;trial<96;trial++){
 const [a,b]=pair();same(a,b,'initial');
 for(let step=0;step<40;step++){
  const i=Math.floor(random()*4),values=[(random()-.5)*2,(random()-.2), (random()-.5)*3];
  if(step%5===0)values[step%3]=boundary[Math.floor(random()*boundary.length)];
  for(const f of [a,b]){f.c.p.set(values,3*i);f.d.observeVertex(i);}
  mutationSteps++;queries(a,b,`trial${trial}/step${step}`);
 }
}
for(const value of [NaN,Infinity,-Infinity])for(let axis=0;axis<3;axis++)for(let vertex=0;vertex<4;vertex++){
 const [a,b]=pair();for(const f of [a,b]){f.c.p[3*vertex+axis]=value;f.d.observeVertex(vertex);}mutationSteps++;queries(a,b,'nonfinite');
 assert.equal(a.d.reason,'NONFINITE_CLOTH');
 for(const f of [a,b]){f.c.p[3*vertex+axis]=0;f.d.observeVertex(vertex);}mutationSteps++;queries(a,b,'restored but permanently held');
}
for(const index of [-1,4,1.5,NaN,Infinity]){
 const [a,b]=pair();for(const f of [a,b])f.d.observeVertex(index);mutationSteps++;same(a,b,'invalid vertex');assert.equal(a.d.reason,'INVALID_VERTEX');
}
for(const axis of [0,1,2]){
 const [a,b]=pair();for(const f of [a,b])f.c.p[axis]+=.1;queries(a,b,'unobserved write');assert.equal(a.d.reason,'UNOBSERVED_POSITION_WRITE');
}
const unchanged=plan.sources.every(r=>sha(r.path)===r.sha256);
assert(unchanged);
const result={status:'PASS_EXACT020_VS019_MUTATION_EQUIVALENCE',cases,mutation_steps:mutationSteps,state_comparisons:stateComparisons,query_comparisons:queryComparisons,seed:'0x91e10da5',elapsed_ms:performance.now()-start,source_unchanged:unchanged,scope:'Deterministic owned dense-array transitions, epsilon boundaries, nonfinite positions, invalid vertex calls and unobserved writes. No arbitrary accessor/proxy contract or physical-quality acceptance.',installed:false,gpu_models:0};
writeFileSync(new URL('MUTATION-EQUIVALENCE.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(result));
