import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {BeddingSimulation as Candidate,MattressSurface} from './candidate/mattress_physics.mjs';
import {BeddingSimulation as Baseline} from './baseline/mattress_physics.mjs';
import * as next from './candidate/surface_contacts.mjs';
import * as old from './baseline/surface_contacts.mjs';
const H=new URL('./',import.meta.url),frame=JSON.parse(readFileSync(new URL('wide.json',H))),results=[],failures=[];
const bed={width:1.6,length:2,base:.3,top:.565};
const surface=new MattressSurface(bed);
function cloth(points,previous=points){return {count:points.length,p:Float64Array.from(points.flat()),prev:Float64Array.from(previous.flat()),v:new Float64Array(3*points.length),invMass:new Float64Array(points.length).fill(1),triangles:[0,1,2],margin:.006,splitPositionStabilization:false};}
function bytes(a,b){for(const k of ['p','prev','v'])assert(Buffer.from(a[k].buffer).equals(Buffer.from(b[k].buffer)),k);}
function sameSurface(points,previous=points,{contacts=true}={}){
 const a=cloth(points,previous),b=cloth(points,previous),ra=next.solveSurfaceContacts(a,surface),rb=old.solveSurfaceContacts(b,surface);
 assert.deepEqual(ra,rb);bytes(a,b);assert.deepEqual(next.surfaceContactReport(a,surface),old.surfaceContactReport(b,surface));
 assert.equal(ra.count>0,contacts);return {count:ra.count};
}
function test(name,body){try{results.push({name,status:'PASS',...body()});}catch(error){failures.push({name,error:String(error.stack)});}}
test('current and previous primitive entirely below finite bottom is excluded',()=>{
 const a=cloth([[.1,.2,-.1],[.3,.2,-.1],[.2,.2,.1]]),before=Array.from(a.p);
 assert(next.belowFixedBottomAtBothEndpoints(a,surface,[0,1,2],a.margin));
 const result=next.solveSurfaceContacts(a,surface);assert.equal(result.count,0);assert.deepEqual(Array.from(a.p),before);
 assert.equal(next.surfaceContactReport(a,surface).contact_count,0);return {};
});
test('top-to-bottom crossing retains original edge and triangle corrections',()=>sameSurface(
 [[-.2,.2,-.2],[.2,.2,-.2],[0,.2,.2]],[[-.2,.7,-.2],[.2,.7,-.2],[0,.7,.2]]));
test('long edge crosses finite footprint while both endpoints lie outside',()=>sameSurface(
 [[-1,.50,0],[1,.50,0],[1,.50,.1]],[[-1,.7,0],[1,.7,0],[1,.7,.1]]));
test('triangle interior spans mattress although all vertices are outside footprint',()=>sameSurface(
 [[-2,.5,-2],[2,.5,-2],[0,.5,3]],[[-2,.7,-2],[2,.7,-2],[0,.7,3]]));
test('primitive outside footprint does not gain contacts',()=>sameSurface(
 [[2,.5,0],[2.2,.5,0],[2.1,.5,.2]],undefined,{contacts:false}));
test('mixed below and above-base vertices never exclude entire triangle',()=>{
 const points=[[.1,.2,-.1],[.3,.31,-.1],[.2,.2,.1]],c=cloth(points);
 assert(!next.belowFixedBottomAtBothEndpoints(c,surface,[0,1,2],c.margin));return sameSurface(points);
});
test('bottom skin and uncertain or nonfinite histories retain eligibility',()=>{
 for(const y of [.3-.006,.3-.006-1e-8]){const c=cloth([[.1,y,0],[.2,y,0],[.15,y,.1]]);assert(!next.belowFixedBottomAtBothEndpoints(c,surface,[0,1,2],0));}
 for(const edit of [c=>{c.prev=null},c=>{c.prev[1]=NaN},c=>{c.p[0]=Infinity},c=>{c.prev=new Float64Array(1)},c=>{c.margin=NaN}]){
  const c=cloth([[.1,.2,0],[.2,.2,0],[.15,.2,.1]]);edit(c);assert(!next.belowFixedBottomAtBothEndpoints(c,surface,[0,1,2],0));
 }return {};
});
test('rising underside into mattress still uses original fallback; bottom response unsupported',()=>sameSurface(
 [[.1,.32,-.1],[.3,.32,-.1],[.2,.32,.1]],[[.1,.2,-.1],[.3,.2,-.1],[.2,.2,.1]]));
test('stale below-bottom surface contact adds no new velocity impulse',()=>{
 const c=cloth([[.1,.2,-.1],[.3,.2,-.1],[.2,.2,.1]]);c.v.fill(-.1);
 c.surfaceActiveContacts=[{ids:[0,1,2],weights:[.3,.3,.4],depth:.365}];const before=Array.from(c.v);
 next.finishSurfaceContactVelocities(c,surface,1/240);assert.deepEqual(Array.from(c.v),before);return {};
});
function patch(Type,{y=.2,x=.22,vx=0,pin=false}={}){
 const sim=new Type({size:'wide',frameParts:frame.parts}),c=sim.cloth;
 c.count=9;c.nx=2;c.nz=2;c.width=.16;c.length=.16;c.centerZ=0;c.margin=.006;
 c.p=new Float64Array(27);c.prev=new Float64Array(27);c.v=new Float64Array(27);c.invMass=new Float64Array(9).fill(9/(.6*.16*.16));c.triangles=[];c.constraints=[];
 const id=(i,j)=>3*j+i;
 for(let j=0;j<3;j++)for(let i=0;i<3;i++){const n=id(i,j);c.p.set([x+i*.08,y,-.08+j*.08],3*n);c.v[3*n]=vx;if(i<2&&j<2)c.triangles.push(n,n+3,n+1,n+1,n+3,n+4);}
 const add=(a,b,kind,compliance)=>c.constraints.push({a,b,kind,compliance,lambda:0,rest:Math.hypot(...[0,1,2].map(k=>c.p[3*a+k]-c.p[3*b+k]))});
 for(let j=0;j<3;j++)for(let i=0;i<3;i++){const a=id(i,j);if(i<2)add(a,a+1,'stretch',2e-7);if(j<2)add(a,a+3,'stretch',2e-7);if(i<2&&j<2){add(a,a+4,'shear',4e-7);add(a+1,a+3,'shear',4e-7);}if(i<1)add(a,a+2,'bend',.02);if(j<1)add(a,a+6,'bend',.02);}
 c.initial=c.p.slice();c.prev.set(c.p);c.grab=pin?{index:2,current:Array.from(c.p.slice(6,9)),target:Array.from(c.p.slice(6,9))}:null;
 assert.equal(sim.iterations,40);assert.equal(sim.substeps,4);assert.equal(sim.metrics().frame_contact.intersecting_triangle_part_pairs,0);return sim;
}
test('coupled supported top drop stays exact for six frames',()=>{
 const a=patch(Candidate,{y:.578}),b=patch(Baseline,{y:.578});for(let i=0;i<6;i++){a.step(1);b.step(1);for(const body of ['cloth','mattress','pillow'])bytes(a[body],b[body]);}return {frames_each:6};
});
test('coupled underside pin/release removes old upward teleport',()=>{
 const a=patch(Candidate,{pin:true}),b=patch(Baseline,{pin:true}),rows=[];
 const oldMetric=b.step(1);assert(oldMetric.cloth_max_y_m>.5);
 for(let i=0;i<10;i++){if(i===2)a.releaseGrab();const m=a.step(1);assert(m.finite);assert(m.cloth_max_y_m<=.200000001);assert.equal(m.frame_contact.intersecting_triangle_part_pairs,0);assert.equal(m.surface_mesh_contact.contact_count,0);rows.push({frame:i+1,max_y_m:m.cloth_max_y_m,speed_mps:m.cloth_rms_speed_mps});}
 return {rows,baseline_one_frame_max_y:oldMetric.cloth_max_y_m};
});
test('coupled below-bottom lateral entry remains below mattress',()=>{
 const a=patch(Candidate,{x:.91,vx:-.9});for(let i=0;i<10;i++){const m=a.step(1);assert(m.finite);assert(m.cloth_max_y_m<=.200000001);assert.equal(m.frame_contact.intersecting_triangle_part_pairs,0);assert.equal(m.surface_mesh_contact.contact_count,0);}
 assert(Math.min(...Array.from(a.cloth.p).filter((_,i)=>i%3===0))<.8);return {frames:10};
});
test('counterexample: intermediate upward-and-return excursion is not observed',()=>{
 const c=cloth([[.1,.2,-.1],[.3,.2,-.1],[.2,.2,.1]]);const before=next.belowFixedBottomAtBothEndpoints(c,surface,[0,1,2],c.margin);
 c.p[1]=.7;c.p[1]=.2;
 const after=next.belowFixedBottomAtBothEndpoints(c,surface,[0,1,2],c.margin);assert.equal(before,true);assert.equal(after,true);
 return {known_limitation:true,requires_review:true,claim:'This endpoint predicate is not an intermediate-history certificate.'};
});
const out={status:failures.length?'HOLD_TEST_FAILURE':'PASS_SCOPED_CASES_WITH_EXPLICIT_HISTORY_LIMIT',results,failures,installed:false,gpu:false};
writeFileSync(new URL('CONTACT-RESULT.json',H),JSON.stringify(out,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:out.status,passed:results.length,failed:failures.length,failures}));if(failures.length)process.exitCode=1;
