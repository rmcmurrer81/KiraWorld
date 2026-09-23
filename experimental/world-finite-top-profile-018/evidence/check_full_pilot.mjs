import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BeddingSimulation as Candidate} from '../world-finite-top-domain-candidate-017/candidate/mattress_physics.mjs';
import {BeddingSimulation as Baseline} from '../world-finite-top-domain-candidate-017/baseline/mattress_physics.mjs';
const H=new URL('./',import.meta.url),plan=JSON.parse(readFileSync(new URL('FULL-PILOT-PLAN.json',H)));
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
for(const row of plan.sources)assert.equal(sha(row.path),row.sha256,row.path);
const fixture=JSON.parse(readFileSync(plan.fixture.path));
const start=performance.now(),a=new Candidate({size:'wide',frameParts:fixture.parts}),b=new Baseline({size:'wide',frameParts:fixture.parts});
for(const s of [a,b]){assert.equal(s.cloth.count,725);assert.equal(s.mattress.count,651);assert.equal(s.iterations,40);assert.equal(s.substeps,4);assert.equal(s.fixedDt,1/60);assert.equal(s.cloth.splitPositionStabilization,false);}
function maxdiff(x,y){assert.equal(x.length,y.length);let max=0;for(let i=0;i<x.length;i++)max=Math.max(max,Math.abs(x[i]-y[i]));return max;}
function state(s,m){const c=s.cloth;return {time_s:m.time_s,finite:m.finite,stretch:m.maximum_stretch_fraction,rms_speed_mps:m.cloth_rms_speed_mps,frame_pairs:m.frame_contact.intersecting_triangle_part_pairs,frame_depth_m:m.frame_contact.max_centroid_penetration_m,surface_depth_m:m.surface_mesh_contact.max_penetration_m,domain:m.finite_top_domain??null,node702:{p:Array.from(c.p.slice(2106,2109)),previous:Array.from(c.prev.slice(2106,2109)),velocity:Array.from(c.v.slice(2106,2109))}};}
function difference(){return Object.fromEntries(['p','prev','v'].map(k=>[k,maxdiff(a.cloth[k],b.cloth[k])]));}
const rows=[],initial={candidate:state(a,a.metrics()),baseline:state(b,b.metrics()),maximum_absolute_difference:difference()};
writeFileSync(new URL('FULL-PILOT-INITIAL.json',H),JSON.stringify({initial,cloth_positions:Array.from(a.cloth.p),cloth_triangles:a.cloth.triangles,frame_parts:a.frame.length},null,2)+'\n',{flag:'wx'});
let hold=null,firstDifference=null,candidateMs=0,baselineMs=0;
if(initial.candidate.frame_pairs||initial.baseline.frame_pairs)hold='INITIAL_FRAME_INTERSECTION';
for(let i=1;i<=plan.frames_each&&!hold;i++){
 let now=performance.now();const ma=a.step(1);candidateMs+=performance.now()-now;
 now=performance.now();const mb=b.step(1);baselineMs+=performance.now()-now;
 const row={frame:i,candidate:state(a,ma),baseline:state(b,mb),maximum_absolute_difference:difference()};rows.push(row);
 if(!firstDifference&&Object.values(row.maximum_absolute_difference).some(v=>v!==0))firstDifference=row;
 if(!ma.finite||!mb.finite)hold='NONFINITE';
 else if(!ma.finite_top_domain.valid)hold='DOMAIN_INVALID';
 else if(row.candidate.frame_pairs||row.baseline.frame_pairs)hold='FRAME_INTERSECTION';
}
const sourcesUnchanged=plan.sources.every(row=>sha(row.path)===row.sha256);
const out={status:hold?'HOLD':firstDifference?'COMPLETED_DIFFERENCE_REQUIRES_REVIEW':'PASS_12_FRAME_FULL_CLOTH_REGRESSION_ONLY',hold,initial,frames_each:rows.length,rows,first_difference:firstDifference,candidate_ms:candidateMs,baseline_ms:baselineMs,elapsed_ms:performance.now()-start,source_unchanged:sourcesUnchanged,iterations:40,substeps:4,cloth_nodes:725,mattress_nodes:651,installed:false,models_gpu:0,limits:'Twelve frames from default authored pose only; not the historical Node702 warm/load/grab/across/release trajectory, general collision safety, or physics/visual acceptance.'};
writeFileSync(new URL('FULL-PILOT-RESULT.json',H),JSON.stringify(out,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:out.status,hold,frames_each:rows.length,first_difference_frame:firstDifference?.frame??null,candidate_ms:candidateMs,baseline_ms:baselineMs,source_unchanged:sourcesUnchanged}));
if(hold||!sourcesUnchanged)process.exitCode=1;
