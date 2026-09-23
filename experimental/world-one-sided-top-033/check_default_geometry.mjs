import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BeddingSimulation as Candidate} from './diagnostic/candidate/mattress_physics.mjs';
import {BeddingSimulation as Baseline} from './diagnostic/baseline/mattress_physics.mjs';
const H=new URL('./',import.meta.url),fixture=JSON.parse(readFileSync(new URL('wide.json',H))),saved=JSON.parse(readFileSync(new URL('DEFAULT-RESULT.json',H)));
const sha=b=>createHash('sha256').update(b).digest('hex');
const pins=JSON.parse(readFileSync(new URL('DIAGNOSTIC-PINS.json',H)));
for(const row of pins){assert.equal(sha(readFileSync(row.source)),row.source_sha256);assert.equal(sha(readFileSync(new URL(row.copy,H))),row.sha256);}
const hash=s=>Object.fromEntries(['cloth','mattress','pillow'].map(owner=>[owner,Object.fromEntries(['p','prev','v'].map(k=>{const v=s[owner][k];return[k,sha(Buffer.from(v.buffer,v.byteOffset,v.byteLength))];}))]));
function full(s){return Object.fromEntries(['cloth','mattress','pillow'].map(owner=>[owner,Object.fromEntries(['p','prev','v'].map(k=>[k,Array.from(s[owner][k])]))]));}
// Independent rectangle clipping: it neither queries nor trusts the changed
// surface contact eligibility/reporting implementation.
function clippedFootprint(points,hx,hz){
 let polygon=points.map(p=>p.slice());
 for(const [axis,sign,limit] of [[0,1,hx],[0,-1,hx],[2,1,hz],[2,-1,hz]]){
  if(!polygon.length)break;
  if(polygon.length===1){if(sign*polygon[0][axis]>limit)polygon=[];continue;}
  const next=[];
  for(let i=0;i<polygon.length;i++){
   const a=polygon[i],b=polygon[(i+1)%polygon.length],da=sign*a[axis]-limit,db=sign*b[axis]-limit;
   if(da<=0)next.push(a);if((da<=0)!==(db<=0)){const t=da/(da-db);next.push(a.map((v,k)=>v+t*(b[k]-v)));}
  }polygon=next;
 }return polygon;
}
const events={baseline:[],candidate:[]};let frame=0;
globalThis.captureTopDiagnostic=(owner,stage,cloth,surface,ids,extra)=>{
 if(frame!==26||events[owner].length>=12)return;
 const p=ids.map(id=>Array.from(cloth.p.slice(3*id,3*id+3))),previous=ids.map(id=>Array.from(cloth.prev.slice(3*id,3*id+3)));
 const skin=cloth.margin,bottom=surface.base;
 if(!p.every(v=>v[1]<bottom-skin-1e-8)||!previous.every(v=>v[1]<bottom-skin-1e-8))return;
 const intersection=clippedFootprint(p,surface.width/2+skin,surface.length/2+skin);if(!intersection.length)return;
 const topHeights=Array.from({length:surface.count},(_,i)=>surface.p[3*i+1]);
 assert(topHeights.every(y=>Number.isFinite(y)&&y>=bottom));
 const maxEndpointY=Math.max(...p.map(v=>v[1]),...previous.map(v=>v[1]));
 const pointPathClear=ids.map((_,i)=>Math.max(p[i][1],previous[i][1])<bottom-skin);
 const correctionCrossesSlab=owner==='baseline'&&ids.length===1&&p[0][1]<bottom&&extra.destinationY>bottom&&Math.abs(p[0][0])<surface.width/2&&Math.abs(p[0][2])<surface.length/2;
 events[owner].push({stage,ids:ids.slice(),p,physical_previous:previous,skin,bottom,footprint:{width:surface.width,length:surface.length},
  finite_top_min:Math.min(...topHeights),finite_top_max:Math.max(...topHeights),clipped_footprint:intersection,
  max_endpoint_y:maxEndpointY,positive_bottom_clearance:bottom-skin-maxEndpointY,
  vertex_linear_segments_clear_of_finite_slab:pointPathClear,
  whole_convex_primitive_linear_interpolation_clear:maxEndpointY<bottom-skin,
  baseline_proposed_upward_correction_crosses_finite_slab:correctionCrossesSlab,...extra});
};
const a=new Candidate({size:'wide',frameParts:fixture.parts}),b=new Baseline({size:'wide',frameParts:fixture.parts});let before;
for(frame=1;frame<=26;frame++){
 if(frame===26)before={candidate:full(a),baseline:full(b)};
 a.step(1);b.step(1);
 assert.deepEqual(hash(a),saved.records[0].rows[frame-1].body_state_sha256,'candidate saved frame'+frame);
 if(frame<26)assert.deepEqual(hash(a),hash(b),'baseline saved frame'+frame);
}
assert.deepEqual(hash(b),saved.difference.baseline,'baseline saved frame26');
const changes=[];
for(let id=0;id<a.cloth.count;id++){
 const ap=Array.from(a.cloth.p.slice(3*id,3*id+3)),bp=Array.from(b.cloth.p.slice(3*id,3*id+3));
 const d=ap.map((v,k)=>v-bp[k]);if(d.some(v=>v!==0))changes.push({id,candidate:ap,baseline:bp,delta:d,distance:Math.hypot(...d),before_frame26:before.candidate.cloth.p.slice(3*id,3*id+3)});
}
changes.sort((x,y)=>y.distance-x.distance);
assert(events.baseline.some(row=>row.baseline_proposed_upward_correction_crosses_finite_slab));
assert(events.candidate.some(row=>row.whole_convex_primitive_linear_interpolation_clear));
assert(pins.every(row=>sha(readFileSync(row.source))===row.source_sha256));
const out={status:'FRAME26_INCLUDES_SPURIOUS015_UPWARD_PROJECTION',frame:26,first25_frames_byte_exact:true,
  instrumented_states_match_uninstrumented_saved_result:true,events,changed_cloth_vertices:changes.length,largest_position_differences:changes.slice(0,15),
  before,after:{candidate:full(a),baseline:full(b)},source_unchanged:true,installed:false,gpu:false,
  limits:'The independent below-plane separation establishes only these captured endpoint-to-endpoint linear paths. It cannot exclude intermediate constraint excursions or all missed legitimate contacts in the rest of the coupled step. No general contact or visual approval.'};
writeFileSync(new URL('DEFAULT-GEOMETRY-DIAGNOSIS.json',H),JSON.stringify(out,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:out.status,baseline_events:events.baseline.length,candidate_events:events.candidate.length,first_baseline:events.baseline[0],changed_cloth_vertices:changes.length,largest:changes[0]}));
