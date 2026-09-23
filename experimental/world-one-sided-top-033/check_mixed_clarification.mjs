import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {MattressSurface} from './candidate/mattress_physics.mjs';
import * as next from './candidate/surface_contacts.mjs';
import * as old from './baseline/surface_contacts.mjs';
const surface=new MattressSurface({width:1.6,length:2,base:.3,top:.565});
const make=()=>{const p=Float64Array.from([[.1,.2,-.1],[.3,.31,-.1],[.2,.2,.1]].flat());return {count:3,p,prev:p.slice(),v:new Float64Array(9),invMass:new Float64Array(3).fill(1),triangles:[0,1,2],margin:.006,splitPositionStabilization:false};};
const a=make(),b=make(),admitted={triangle:next.belowFixedBottomAtBothEndpoints(a,surface,[0,1,2],a.margin),edge01:next.belowFixedBottomAtBothEndpoints(a,surface,[0,1],a.margin),edge12:next.belowFixedBottomAtBothEndpoints(a,surface,[1,2],a.margin),edge02:next.belowFixedBottomAtBothEndpoints(a,surface,[0,2],a.margin)};
assert.deepEqual(admitted,{triangle:false,edge01:false,edge12:false,edge02:true});
const ra=next.solveSurfaceContacts(a,surface),rb=old.solveSurfaceContacts(b,surface);
assert(ra.count>0);assert.equal(ra.count,6);assert.equal(rb.count,8);
assert(a.surfaceActiveContacts.some(c=>c.ids.includes(1)));
const out={status:'EXPECTED_ASSERTION_CORRECTED_NO_SOURCE_CHANGE',initial_exclusions:admitted,candidate:ra,baseline:rb,
  candidate_positions:Array.from(a.p),baseline_positions:Array.from(b.p),
  explanation:'The initial triangle is not excluded. Its separate edge02 is wholly below bottom, so a whole-solve byte-equality assertion was invalid. The original12/13 receipt remains preserved; this clarification does not turn it into an untouched13/13 run.',
  installed:false,gpu:false};
writeFileSync(new URL('MIXED-CLARIFICATION.json',import.meta.url),JSON.stringify(out,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:out.status,initial_exclusions:admitted,candidate_count:ra.count,baseline_count:rb.count}));
