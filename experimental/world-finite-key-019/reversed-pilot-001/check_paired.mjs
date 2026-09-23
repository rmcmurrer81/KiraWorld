import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BeddingSimulation as Candidate019} from '../candidate/mattress_physics.mjs';
import {BeddingSimulation as Predecessor017} from '../reference017/candidate/mattress_physics.mjs';
const H=new URL('./',import.meta.url),plan=JSON.parse(readFileSync(new URL('PLAN.json',H)));
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
for(const r of plan.sources)assert.equal(sha(r.path),r.sha256,r.path);
const fixture=JSON.parse(readFileSync(plan.fixture.path)),a=new Candidate019({size:'wide',frameParts:fixture.parts}),b=new Predecessor017({size:'wide',frameParts:fixture.parts});
for(const s of [a,b]){assert.equal(s.cloth.count,725);assert.equal(s.mattress.count,651);assert.equal(s.iterations,40);assert.equal(s.substeps,4);assert.equal(s.fixedDt,1/60);assert.equal(s.cloth.splitPositionStabilization,false);}
function bytes(x,y,label){assert.equal(x.length,y.length,label);assert(Buffer.from(x.buffer,x.byteOffset,x.byteLength).equals(Buffer.from(y.buffer,y.byteOffset,y.byteLength)),label);}
function exact(label){
 for(const owner of ['cloth','mattress','pillow'])for(const field of ['p','prev','v'])bytes(a[owner][field],b[owner][field],label+':'+owner+'.'+field);
 const da=a.cloth.finiteTopDomain,db=b.cloth.finiteTopDomain;bytes(da.last,db.last,label+':domain.last');bytes(da.masks,db.masks,label+':domain.masks');
 assert.deepEqual(da.snapshot(),db.snapshot(),label+':domain.snapshot');
 assert.deepEqual(da.primitives,db.primitives,label+':primitive.certificates');
}
const start=performance.now(),rows=[];let fastMs=0,oldMs=0,hold=null;
const initialA=a.metrics(),initialB=b.metrics();assert.deepEqual(initialA,initialB);assert.equal(initialA.frame_contact.intersecting_triangle_part_pairs,0);exact('initial');
try{
 for(let frame=1;frame<=12;frame++){
  let now=performance.now();const mb=b.step(1);oldMs+=performance.now()-now;
  now=performance.now();const ma=a.step(1);fastMs+=performance.now()-now;
  assert.deepEqual(ma,mb,'frame metrics'+frame);exact('frame'+frame);assert(ma.finite);assert(ma.finite_top_domain.valid);assert.equal(ma.frame_contact.intersecting_triangle_part_pairs,0);
  rows.push({frame,time_s:ma.time_s,stretch:ma.maximum_stretch_fraction,rms_speed_mps:ma.cloth_rms_speed_mps,frame_pairs:ma.frame_contact.intersecting_triangle_part_pairs,surface_depth_m:ma.surface_mesh_contact.max_penetration_m,domain:ma.finite_top_domain,p_prev_v_all_three_bodies_exact:true,all_domain_masks_history_and_primitive_certificates_exact:true});
 }
}catch(e){hold=String(e.stack);}
const unchanged=plan.sources.every(r=>sha(r.path)===r.sha256),out={status:hold?'HOLD':'PASS_12_FRAME_EXACT019_VS017_COMPARISON',hold,frames_each:rows.length,rows,candidate019_ms:fastMs,predecessor017_ms:oldMs,observed_predecessor_over_candidate:oldMs/fastMs,elapsed_ms:performance.now()-start,source_unchanged:unchanged,installed:false,gpu_models:0,limits:'One predecessor-first short mixed-process timing; startup/JIT/order effects are not controlled. No general speedup, long-trajectory, physical or visual-quality acceptance.'};
writeFileSync(new URL('PAIRED-RESULT.json',H),JSON.stringify(out,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:out.status,hold,frames_each:rows.length,candidate019_ms:fastMs,predecessor017_ms:oldMs,observed_ratio:oldMs/fastMs,source_unchanged:unchanged}));if(hold||!unchanged)process.exitCode=1;
