import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,appendFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {BeddingSimulation} from './candidate/mattress_physics.mjs';
const H=new URL('./',import.meta.url),plan=JSON.parse(readFileSync(new URL('FULL-TRAJECTORY-PLAN.json',H)));
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
for(const row of plan.sources)assert.equal(sha(row.path),row.sha256,row.path);
const fixture=JSON.parse(readFileSync(plan.fixture.path));
const historical=readFileSync(plan.historical_dense.path,'utf8').trim().split('\n').map(JSON.parse);
const historicalSampled=JSON.parse(readFileSync(plan.historical_sampled.path)).rows.filter(r=>r.size==='wide');
const sim=new BeddingSimulation({size:'wide',frameParts:fixture.parts});
assert.equal(sim.cloth.count,725);assert.equal(sim.mattress.count,651);assert.equal(sim.iterations,40);assert.equal(sim.substeps,4);assert.equal(sim.fixedDt,1/60);assert.equal(sim.cloth.splitPositionStabilization,false);
const start=performance.now(),rows=[],summaries=[],nodeMutations=[];let phase='initial',frame=0,globalFrame=0,hold=null,firstDifference=null;
const domain=sim.cloth.finiteTopDomain,observe=domain.observeVertex.bind(domain);
let lastNode=Array.from(sim.cloth.p.slice(2106,2109));
// Read-only recorder around the existing observation boundary. No state arrays,
// masks, certificates, velocities or response results are changed by this wrapper.
// It identifies observed node702 mutations, not the solver stage that caused them.
domain.observeVertex=function(i){
 if(i===702){
  const after=Array.from(sim.cloth.p.slice(2106,2109)),dy=after[1]-lastNode[1];
  if((phase==='across'||phase==='release')&&dy>0&&(nodeMutations.length<20||dy>nodeMutations.at(-1).delta_y_m)){
   nodeMutations.push({phase,frame,global_frame:globalFrame+1,time_s:sim.time,delta_y_m:dy,before:lastNode,after,physical_previous:Array.from(sim.cloth.prev.slice(2106,2109)),velocity:Array.from(sim.cloth.v.slice(2106,2109)),prior_point_certificate:{...domain.byKey.get('1:702'),ids:[702]}});
   nodeMutations.sort((a,b)=>b.delta_y_m-a.delta_y_m);nodeMutations.length=Math.min(20,nodeMutations.length);
  }
  lastNode=after;
 }
 return observe(i);
};
function compact(m){return {time_s:m.time_s,finite:m.finite,stretch:m.maximum_stretch_fraction,rms_speed_mps:m.cloth_rms_speed_mps,frame_pairs:m.frame_contact.intersecting_triangle_part_pairs,frame_depth_m:m.frame_contact.max_centroid_penetration_m,surface_depth_m:m.surface_mesh_contact.max_penetration_m,frame_worst:m.frame_contact.worst,compression_m:m.mattress_center_compression_m};}
function node(){return {p:Array.from(sim.cloth.p.slice(2106,2109)),previous:Array.from(sim.cloth.prev.slice(2106,2109)),velocity:Array.from(sim.cloth.v.slice(2106,2109))};}
function fullState(){return {cloth_positions:Array.from(sim.cloth.p),cloth_previous:Array.from(sim.cloth.prev),cloth_velocities:Array.from(sim.cloth.v),mattress_positions:Array.from(sim.mattress.p),mattress_previous:Array.from(sim.mattress.prev),mattress_velocities:Array.from(sim.mattress.v),grab:sim.cloth.grab,domain:domain.snapshot()};}
function progress(){writeFileSync(new URL('FULL-TRAJECTORY-PROGRESS.json',H),JSON.stringify({status:'RUNNING',phase,phase_frame:frame,global_frames:globalFrame,elapsed_ms:performance.now()-start,last:rows.at(-1)??null,summaries},null,2)+'\n');console.log(JSON.stringify({phase,phase_frame:frame,global_frames:globalFrame,elapsed_ms:performance.now()-start}));}
const initial=compact(sim.metrics());
writeFileSync(new URL('FULL-TRAJECTORY-INITIAL.json',H),JSON.stringify({initial,state:fullState()},null,2)+'\n',{flag:'wx'});
if(!initial.finite||initial.frame_pairs||!domain.snapshot().valid)hold='INVALID_INITIAL_FIXTURE';
try{
 for(const stage of plan.stages){
  if(hold)break;phase=stage.action;frame=0;
  if(phase==='load')sim.setMattressLoad({loaded:true,site:'center',force:220});
  if(phase==='unload')sim.setMattressLoad({loaded:false});
  if(phase==='grab')sim.grabCorner();
  if(phase==='across')sim.moveGrabAcross();
  if(phase==='release'){
   const before=fullState();sim.releaseGrab();
   assert.equal(sim.cloth.grab,null);assert.deepEqual(Array.from(sim.cloth.p),before.cloth_positions);assert.deepEqual(Array.from(sim.cloth.prev),before.cloth_previous);assert.deepEqual(Array.from(sim.cloth.v),before.cloth_velocities);
   writeFileSync(new URL('FULL-TRAJECTORY-BEFORE-RELEASE.json',H),JSON.stringify({state:before,release_clears_only_grab:true},null,2)+'\n',{flag:'wx'});
  }
  const summary={action:phase,frames:0,max_stretch:0,max_rms_speed_mps:0,max_frame_pairs:0,max_surface_depth_m:0,sampled_at30:{maxStretch:0,maxSpeed:0,framePairs:0,depth:0,surface:0}};
  for(frame=1;frame<=stage.frames;frame++){
   const m=sim.step(1);globalFrame++;summary.frames++;
   const record={action:phase,stage_frame:frame,global_frame:globalFrame,...compact(m),node702:node(),domain:domain.snapshot()};
   summary.max_stretch=Math.max(summary.max_stretch,record.stretch);summary.max_rms_speed_mps=Math.max(summary.max_rms_speed_mps,record.rms_speed_mps);summary.max_frame_pairs=Math.max(summary.max_frame_pairs,record.frame_pairs);summary.max_surface_depth_m=Math.max(summary.max_surface_depth_m,record.surface_depth_m);
   if(frame%30===0){const q=summary.sampled_at30;q.maxStretch=Math.max(q.maxStretch,record.stretch);q.maxSpeed=Math.max(q.maxSpeed,record.rms_speed_mps);q.framePairs=Math.max(q.framePairs,record.frame_pairs);q.depth=Math.max(q.depth,record.frame_depth_m);q.surface=Math.max(q.surface,record.surface_depth_m);}
   if(phase==='across'||phase==='release'){
    const expected=historical.find(r=>r.action===phase&&r.stage_frame===frame);assert(expected,'Missing historical comparison row');
    record.historical_differences=Object.fromEntries(Object.keys(compact(m)).filter(k=>typeof record[k]==='number').map(k=>[k,record[k]-expected[k]]));
    if(!firstDifference&&Object.values(record.historical_differences).some(v=>v!==0))firstDifference={...record};
   }
   rows.push(record);appendFileSync(new URL('FULL-TRAJECTORY-FRAMES.jsonl',H),JSON.stringify(record)+'\n');
   if(!record.finite)hold='NONFINITE';else if(!record.domain.valid)hold='DOMAIN_INVALID';else if(record.frame_pairs>0)hold='FRAME_INTERSECTION';
   if(hold){writeFileSync(new URL('FULL-TRAJECTORY-FIRST-HOLD.json',H),JSON.stringify({hold,record,state:fullState()},null,2)+'\n',{flag:'wx'});break;}
   if(frame%30===0)progress();
  }
  const expected=historicalSampled.find(r=>r.action===phase),last=rows.at(-1);
  if(phase!=='release'&&summary.frames===stage.frames){
   const actual={size:'wide',action:phase,time:last.time_s,...summary.sampled_at30,restStretch:last.stretch,restSpeed:last.rms_speed_mps,compression:last.compression_m};
   summary.historical30_frame_aggregate=expected;summary.actual30_frame_aggregate=actual;summary.sampled_exact=isDeepStrictEqual(actual,expected);
  }
  summaries.push(summary);progress();
 }
}catch(e){hold='EXCEPTION';writeFileSync(new URL('FULL-TRAJECTORY-ERROR.json',H),JSON.stringify({error:String(e.stack),phase,frame,globalFrame,state:fullState()},null,2)+'\n',{flag:'wx'});}
const sourceUnchanged=plan.sources.every(row=>sha(row.path)===row.sha256);
const out={status:hold?'HOLD':'COMPLETED_NUMERICAL_OBSERVATION_REQUIRES_REVIEW',hold,global_frames:globalFrame,target_frames:1110,initial,summaries,first_historical_dense_difference:firstDifference,largest_observed_node702_positive_mutations:nodeMutations,final:rows.at(-1)??null,final_state:fullState(),source_unchanged:sourceUnchanged,elapsed_ms:performance.now()-start,installed:false,models_gpu:0,limits:plan.interpretation_limits};
writeFileSync(new URL('FULL-TRAJECTORY-RESULT.json',H),JSON.stringify(out,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:out.status,hold,global_frames:globalFrame,elapsed_ms:out.elapsed_ms,source_unchanged:sourceUnchanged}));
if(hold||!sourceUnchanged||globalFrame!==1110)process.exitCode=1;
