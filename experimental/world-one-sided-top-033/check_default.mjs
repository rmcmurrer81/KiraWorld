import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BeddingSimulation as Candidate} from './candidate/mattress_physics.mjs';
import {BeddingSimulation as Baseline} from './baseline/mattress_physics.mjs';
const H=new URL('./',import.meta.url),plan=JSON.parse(readFileSync(new URL('PLAN.json',H)));
const sha=b=>createHash('sha256').update(b).digest('hex');
for(const p of plan.sources)assert.equal(sha(readFileSync(p.path)),p.sha256);
const fixture=JSON.parse(readFileSync(new URL('wide.json',H)));
const hash=s=>Object.fromEntries(['cloth','mattress','pillow'].map(owner=>[owner,Object.fromEntries(['p','prev','v'].map(k=>{const v=s[owner][k];return[k,sha(Buffer.from(v.buffer,v.byteOffset,v.byteLength))];}))]));
const metrics=s=>{const {limitations,...rest}=s.metrics();return rest;};
const records=[];let difference=null;
for(const order of ['candidate_first','baseline_first']){
 const a=new Candidate({size:'wide',frameParts:fixture.parts}),b=new Baseline({size:'wide',frameParts:fixture.parts});
 const timing={candidate_ms:0,baseline_ms:0,candidate_worst_frame_ms:0,baseline_worst_frame_ms:0},rows=[];
 for(let frame=1;frame<=60;frame++){
  let ma,mb;
  for(const who of order==='candidate_first'?['candidate','baseline']:['baseline','candidate']){
   const now=performance.now(),m=(who==='candidate'?a:b).step(1),elapsed=performance.now()-now;
   timing[who+'_ms']+=elapsed;timing[who+'_worst_frame_ms']=Math.max(timing[who+'_worst_frame_ms'],elapsed);
   if(who==='candidate')ma=m;else mb=m;
  }
  const ah=hash(a),bh=hash(b),exact=JSON.stringify(ah)===JSON.stringify(bh);
  const row={frame,exact,body_state_sha256:ah,candidate:{stretch:ma.maximum_stretch_fraction,rms_speed_mps:ma.cloth_rms_speed_mps,frame_pairs:ma.frame_contact.intersecting_triangle_part_pairs,surface_depth_m:ma.surface_mesh_contact.max_penetration_m}};rows.push(row);
  if(!exact){difference={order,frame,candidate:ah,baseline:bh,candidate_metrics:ma,baseline_metrics:mb};break;}
  assert.deepEqual(metrics(a),metrics(b));assert(ma.finite);assert.equal(ma.frame_contact.intersecting_triangle_part_pairs,0);
 }
 records.push({order,...timing,rows});if(difference)break;
}
const unchanged=plan.sources.every(p=>sha(readFileSync(p.path))===p.sha256);assert(unchanged);
const out={status:difference?'HOLD_DEFAULT_TRAJECTORY_CHANGED':'PASS_60_FRAME_DEFAULT_EXACT_IN_BOTH_ORDERS',difference,records,source_unchanged:unchanged,installed:false,gpu:false,
  limits:'Short default settle comparison only, not full1110-frame trajectory, statistical speed guarantee or visual/physical approval. Maximum recorded CPU frame time is an observation, not a mathematical worst-case bound.'};
writeFileSync(new URL('DEFAULT-RESULT.json',H),JSON.stringify(out,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:out.status,first_difference_frame:difference?.frame??null,records:records.map(({rows,...rest})=>({...rest,frames:rows.length})),source_unchanged:unchanged}));
