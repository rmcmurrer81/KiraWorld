import assert from 'node:assert/strict';
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {BeddingSimulation as Frozen015} from './sources/installed015/mattress_physics.mjs';
import {BeddingSimulation as Type017} from './sources/predecessor017/mattress_physics.mjs';
import {BeddingSimulation as Type019} from './sources/candidate019/mattress_physics.mjs';
import {attachFiniteTopDomain as attach017} from './sources/predecessor017/finite_top_domain.mjs';
import {attachFiniteTopDomain as attach019} from './sources/candidate019/finite_top_domain.mjs';
const root = new URL('./', import.meta.url);
const plan = JSON.parse(readFileSync(new URL('PLAN.json', root)));
const sha = data => createHash('sha256').update(data).digest('hex');
for (const row of plan.sources) {
  assert.equal(sha(readFileSync(row.path)), row.sha256, row.path);
  assert.equal(sha(readFileSync(new URL(row.snapshot, root))), row.sha256, row.snapshot);
}
const installedRow = plan.sources.find(r => r.snapshot === 'sources/installed015/mattress_physics.mjs');
const {BeddingSimulation: Installed015} = await import(pathToFileURL(installedRow.path));
const fixture = JSON.parse(readFileSync(new URL('fixtures/wide.json', root)));
const historical = JSON.parse(readFileSync(new URL('historical-pilot.json', root)));
const fields = ['p','prev','v'], bodies = ['cloth','mattress','pillow'];
function hashState(sim) {
  return Object.fromEntries(bodies.map(owner => [owner, Object.fromEntries(fields.map(field => {
    const a=sim[owner][field];return [field,sha(Buffer.from(a.buffer,a.byteOffset,a.byteLength))];
  }))]));
}
function exact(a,b) {
  for(const owner of bodies)for(const field of fields){
    const x=a[owner][field],y=b[owner][field];
    assert.equal(x.constructor,y.constructor);assert.equal(x.length,y.length);
    assert(Buffer.from(x.buffer,x.byteOffset,x.byteLength).equals(Buffer.from(y.buffer,y.byteOffset,y.byteLength)),owner+'.'+field);
  }
}
function domainExact(a,b){
  const da=a.cloth.finiteTopDomain,db=b.cloth.finiteTopDomain;
  assert.deepEqual(da.last,db.last);assert.deepEqual(da.masks,db.masks);
  assert.deepEqual(da.primitives,db.primitives);assert.deepEqual(da.snapshot(),db.snapshot());
}
function compact(sim,m){return {time_s:m.time_s,finite:m.finite,stretch:m.maximum_stretch_fraction,rms_speed_mps:m.cloth_rms_speed_mps,
  frame_pairs:m.frame_contact.intersecting_triangle_part_pairs,frame_depth_m:m.frame_contact.max_centroid_penetration_m,
  surface_depth_m:m.surface_mesh_contact.max_penetration_m,
  node702:{p:Array.from(sim.cloth.p.slice(2106,2109)),previous:Array.from(sim.cloth.prev.slice(2106,2109)),velocity:Array.from(sim.cloth.v.slice(2106,2109))}};}
function withoutDomain(record){const {domain,...rest}=record;return rest;}
const sims=[Installed015,Frozen015,Type017,Type019].map(Type=>new Type({size:'wide',frameParts:fixture.parts}));
for(const s of sims){assert.equal(s.cloth.count,725);assert.equal(s.mattress.count,651);assert.equal(s.iterations,40);assert.equal(s.substeps,4);}
assert.equal(sims[0].cloth.finiteTopDomain,undefined);
const rows=[],timings=[0,0,0,0],start=performance.now();
for(let frame=1;frame<=12;frame++){
  const metrics=[];
  // Rotate execution order. These short observations remain non-benchmark timings.
  for(let offset=0;offset<4;offset++){
    const i=(frame-1+offset)%4,now=performance.now();metrics[i]=sims[i].step(1);timings[i]+=performance.now()-now;
  }
  for(let i=1;i<4;i++)exact(sims[0],sims[i]);
  assert.deepEqual(metrics[0],metrics[1]);assert.deepEqual(metrics[2],metrics[3]);domainExact(sims[2],sims[3]);
  const observed=compact(sims[0],metrics[0]);
  assert.deepEqual(observed,withoutDomain(historical.rows[frame-1].baseline),'saved baseline frame'+frame);
  assert.deepEqual(compact(sims[2],metrics[2]),withoutDomain(historical.rows[frame-1].candidate),'saved017 frame'+frame);
  rows.push({frame,all_four_body_states_byte_exact:true,installed_matches_saved015_metrics:true,
    domain017_and019_exact:true,state_sha256:hashState(sims[0]),observed});
}
// Reproduce the inherited frame-clear underside counterexample to demonstrate
// that019 includes a behavioral change, even though its initial12 frames match.
function underside(Type,attach){
  const sim=new Type({size:'wide',frameParts:fixture.parts}),c=sim.cloth;
  c.count=9;c.nx=2;c.nz=2;c.width=.16;c.length=.16;c.centerZ=0;c.margin=.006;
  c.p=new Float64Array(27);c.prev=new Float64Array(27);c.v=new Float64Array(27);c.invMass=new Float64Array(9).fill(9/(.6*.16*.16));c.triangles=[];c.constraints=[];
  const id=(i,j)=>3*j+i;
  for(let j=0;j<3;j++)for(let i=0;i<3;i++){const n=id(i,j);c.p.set([.22+i*.08,.2,-.08+j*.08],3*n);if(i<2&&j<2)c.triangles.push(n,n+3,n+1,n+1,n+3,n+4);}
  const add=(a,b,kind,compliance)=>c.constraints.push({a,b,kind,compliance,lambda:0,rest:Math.hypot(...[0,1,2].map(k=>c.p[3*a+k]-c.p[3*b+k]))});
  for(let j=0;j<3;j++)for(let i=0;i<3;i++){
    const a=id(i,j);if(i<2)add(a,a+1,'stretch',2e-7);if(j<2)add(a,a+3,'stretch',2e-7);
    if(i<2&&j<2){add(a,a+4,'shear',4e-7);add(a+1,a+3,'shear',4e-7);}
    if(i<1)add(a,a+2,'bend',.02);if(j<1)add(a,a+6,'bend',.02);
  }
  c.initial=c.p.slice();c.prev.set(c.p);c.grab={index:2,current:Array.from(c.p.slice(6,9)),target:Array.from(c.p.slice(6,9))};
  if(attach)attach(sim);
  assert.equal(sim.metrics().frame_contact.intersecting_triangle_part_pairs,0);
  return sim;
}
const baseline=underside(Installed015),a=underside(Type017,attach017),b=underside(Type019,attach019);
exact(baseline,a);exact(a,b);
const before=hashState(baseline),baseMetric=baseline.step(1),counterexample=[];
assert(baseMetric.cloth_max_y_m>.5);
for(let frame=1;frame<=10;frame++){
  if(frame===3){a.releaseGrab();b.releaseGrab();}
  const ma=a.step(1),mb=b.step(1);exact(a,b);domainExact(a,b);assert.deepEqual(ma,mb);
  assert(ma.cloth_max_y_m<=.200000001);assert.equal(ma.frame_contact.intersecting_triangle_part_pairs,0);
  assert.equal(ma.surface_mesh_contact.contact_count,0);
  counterexample.push({frame,max_y_m:ma.cloth_max_y_m,state_sha256:hashState(a),domain:ma.finite_top_domain});
}
assert.notDeepEqual(hashState(baseline),counterexample[0].state_sha256);
const unchanged=plan.sources.every(row=>sha(readFileSync(row.path))===row.sha256);
assert(unchanged);
const result={status:'PASS_DEPENDENCY_AUDIT_DO_NOT_INSTALL019_AS015_OPTIMIZATION',
  supported_frames_each:12,rows,step_ms:Object.fromEntries(['actual_installed015','frozen015','predecessor017','candidate019'].map((key,i)=>[key,timings[i]])),
  counterexample:{initial_all_body_state_sha256:before,installed015_max_y_after_one_frame:baseMetric.cloth_max_y_m,
    installed015_state_sha256:hashState(baseline),candidate017_019_frames:counterexample},
  elapsed_ms:performance.now()-start,source_unchanged:unchanged,installed:false,gpu_models:0,
  conclusion:'019 only improves017 key construction.015 has no such module or call;019 cannot be transplanted as a performance-only patch. Under-mattress response differs after one frame.',
  limits:'12 default frames and10 tiny patch frames; not a full saved trajectory replay, ownership proof, general collision safety, benchmark or visual/material approval.'};
writeFileSync(new URL('RESULT.json',root),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,step_ms:result.step_ms,baseline_underside_max_y_m:baseMetric.cloth_max_y_m,source_unchanged:unchanged,elapsed_ms:result.elapsed_ms}));
