import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {BeddingSimulation as Candidate} from './candidate/mattress_physics.mjs';
import {BeddingSimulation as Baseline} from './baseline/mattress_physics.mjs';
import {attachFiniteTopDomain} from './candidate/finite_top_domain.mjs';
import {frameContactReport} from './baseline/frame_contacts.mjs';
const frame=JSON.parse(readFileSync(new URL('../world-frame-contact-perf-candidate/fixtures/wide.json',import.meta.url)));
const start=performance.now(),results=[],failures=[];
function patch(Type,{y,x=.22,vx=0,pin=false}){
 const sim=new Type({size:'wide',frameParts:frame.parts}),c=sim.cloth;
 c.count=9;c.nx=2;c.nz=2;c.width=.16;c.length=.16;c.centerZ=0;c.margin=.006;
 c.p=new Float64Array(27);c.prev=new Float64Array(27);c.v=new Float64Array(27);c.invMass=new Float64Array(9).fill(9/(.6*.16*.16));c.triangles=[];c.constraints=[];
 const id=(i,j)=>3*j+i;
 for(let j=0;j<3;j++)for(let i=0;i<3;i++){const n=id(i,j);c.p.set([x+i*.08,y,-.08+j*.08],3*n);c.v[3*n]=vx;if(i<2&&j<2)c.triangles.push(n,n+3,n+1,n+1,n+3,n+4);}
 const add=(a,b,kind,compliance)=>c.constraints.push({a,b,kind,compliance,lambda:0,rest:Math.hypot(...[0,1,2].map(k=>c.p[3*a+k]-c.p[3*b+k]))});
 for(let j=0;j<3;j++)for(let i=0;i<3;i++){
  const a=id(i,j);if(i<2)add(a,a+1,'stretch',2e-7);if(j<2)add(a,a+3,'stretch',2e-7);
  if(i<2&&j<2){add(a,a+4,'shear',4e-7);add(a+1,a+3,'shear',4e-7);}
  if(i<1)add(a,a+2,'bend',.02);if(j<1)add(a,a+6,'bend',.02);
 }
 c.initial=c.p.slice();c.prev.set(c.p);c.grab=pin?{index:2,current:Array.from(c.p.slice(6,9)),target:Array.from(c.p.slice(6,9))}:null;
 if(Type===Candidate)attachFiniteTopDomain(sim);
 assert.equal(sim.iterations,40);assert.equal(sim.substeps,4);assert.equal(c.splitPositionStabilization,false);
 assert.equal(frameContactReport(c,sim.frame).intersecting_triangle_part_pairs,0,'Authored initial fixture intersects frame');
 return sim;
}
function snap(s){const m=s.metrics();return {time_s:s.time,positions:Array.from(s.cloth.p),previous:Array.from(s.cloth.prev),velocities:Array.from(s.cloth.v),metrics:m,peak_speed_mps:Math.max(...Array.from({length:s.cloth.count},(_,i)=>Math.hypot(...s.cloth.v.slice(3*i,3*i+3)))),net_velocity_error:Math.max(...Array.from({length:s.cloth.p.length},(_,i)=>Math.abs(s.cloth.v[i]-(s.cloth.p[i]-s.cloth.prev[i])/(s.fixedDt/s.substeps))))};}
function run(s,frames,{releaseAfter=0,maxStrain=.1}={}){
 const rows=[snap(s)];for(let i=0;i<frames;i++){if(i===releaseAfter)s.releaseGrab();s.step(1);const r=snap(s);rows.push(r);
  if(!r.metrics.finite||r.metrics.maximum_stretch_fraction>maxStrain||r.metrics.frame_contact.intersecting_triangle_part_pairs>0)return {rows,stopped_early:true,reason:'NONFINITE_STRAIN_OR_FRAME_OVERLAP'};
 }return {rows,stopped_early:false};
}
function test(name,f){try{results.push({name,status:'PASS',...f()});}catch(e){failures.push({name,error:String(e.stack)});}}
test('normal supported patch remains byte-identical for six frames',()=>{
 const a=patch(Candidate,{y:.578}),b=patch(Baseline,{y:.578}),ra=run(a,6),rb=run(b,6);
 // Save actual rows before any expectation assertions in the final receipt.
 results.push({name:'normal_supported_observation',candidate:ra,baseline:rb});
 assert(!ra.stopped_early&&!rb.stopped_early);assert.deepEqual(Array.from(a.cloth.p),Array.from(b.cloth.p));assert.deepEqual(Array.from(a.cloth.prev),Array.from(b.cloth.prev));assert.deepEqual(Array.from(a.cloth.v),Array.from(b.cloth.v));assert(a.cloth.finiteTopDomain.snapshot().valid);
 return {frames_each:6,position_previous_velocity_exact:true,final_domain:a.cloth.finiteTopDomain.snapshot()};
});
test('frame-clear underside pin and release has no false upward lift',()=>{
 const a=patch(Candidate,{y:.2,pin:true}),b=patch(Baseline,{y:.2,pin:true});
 const ra=run(a,10,{releaseAfter:2}),rb=run(b,1,{releaseAfter:2,maxStrain:.1});
 results.push({name:'underside_observation',candidate:ra,baseline:rb});
 assert(!ra.stopped_early);assert(a.cloth.finiteTopDomain.snapshot().valid);assert(ra.rows.every(r=>r.metrics.cloth_max_y_m<=.200000001));assert(ra.rows.every(r=>r.metrics.surface_mesh_contact.contact_count===0));assert(a.cloth.finiteTopDomain.snapshot().suppressed>0);
 const last=ra.rows.at(-1);assert(last.net_velocity_error<1e-10);assert(rb.rows.at(-1).metrics.cloth_max_y_m>.5,'Baseline must reproduce upward artifact');
 return {frames_candidate:10,frames_baseline:1,baseline_early_hold:rb.stopped_early,baseline_max_y_m:rb.rows.at(-1).metrics.cloth_max_y_m,candidate_max_y_m:Math.max(...ra.rows.map(r=>r.metrics.cloth_max_y_m)),candidate_peak_release_speed_mps:Math.max(...ra.rows.slice(3).map(r=>r.peak_speed_mps)),physical_previous_net_velocity_error:last.net_velocity_error,final_domain:a.cloth.finiteTopDomain.snapshot()};
});
test('below-bottom lateral entry retains finite frame-clear release',()=>{
 const a=patch(Candidate,{y:.2,x:.91,vx:-.9}),ra=run(a,10);results.push({name:'lateral_entry_observation',candidate:ra});
 assert(!ra.stopped_early);assert(a.cloth.finiteTopDomain.snapshot().valid);assert(Math.min(...Array.from(a.cloth.p).filter((_,i)=>i%3===0))<.8);assert(ra.rows.every(r=>r.metrics.cloth_max_y_m<=.200000001));assert(a.metrics().surface_mesh_contact.contact_count===0);
 return {frames:10,final_domain:a.cloth.finiteTopDomain.snapshot(),peak_speed_mps:Math.max(...ra.rows.map(r=>r.peak_speed_mps))};
});
const out={status:failures.length?'HOLD':'PASS_SCOPED_PATCH_COMPARISONS',results,failures,elapsed_ms:performance.now()-start,actual_cloth_nodes:9,iterations:40,substeps:4,full_matress_and_frame:true,not_full_original_cloth_or_node702_replay:true,installed:false,gpu:false};
writeFileSync(new URL('RELEASE-COMPARISON.json',import.meta.url),JSON.stringify(out,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:out.status,elapsed_ms:out.elapsed_ms,failures,summary:results.filter(r=>r.status==='PASS')}));if(failures.length)process.exitCode=1;
