import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import * as before from './preimages/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import * as next from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import * as frontend from './candidate/tools/world_builder_engine/walk_controller.mjs';
const [source,expected]=process.argv.slice(2),raw=fs.readFileSync(source),hash=r=>crypto.createHash('sha256').update(r).digest('hex');
assert.equal(hash(raw),expected);const g=JSON.parse(raw),checks=[];
const a=before.createDoorSystem(g),b=next.createDoorSystem(g),c=frontend.createDoorSystem(g);
assert.deepEqual(b.definitions(),a.definitions());checks.push('All six portable door definitions exactly preserved');
assert.deepEqual(b.interlocks(),a.interlocks());assert.deepEqual(b.interlocks(),c.interlocks());checks.push('Actual two-leaf airlock policy exactly preserved in frontend and portable controller');
for(const feet of [[1.5,0,-2],[1.5,0,2.74],[1.5,2,-2]])for(const yaw of [null,0,Math.PI/2,-Math.PI/2,Math.PI])assert.deepEqual(b.nearest(feet,yaw),c.nearest(feet,yaw));
checks.push('Frontend and portable target selection match both corridor directions, both airlock directions and invalid elevation');
const p=next.createWalkController(g),f=frontend.createWalkController(g);assert.deepEqual(p.snapshot(),f.snapshot());
for(let i=0;i<200;i++){
 if(i===3||i===53||i===108)assert.deepEqual(p.toggleDoor(),f.toggleDoor());
 if(i%13===0){p.look(80,0);f.look(80,0);}
 assert.deepEqual(p.step(.05,{forward:i%5!==0,left:i%17===0}),f.step(.05,{forward:i%5!==0,left:i%17===0}));
 assert.deepEqual(p.doorStates(),f.doorStates());
}
checks.push('200 deterministic input ticks preserve exact portable/frontend motion, obstruction and door state');
assert.equal(hash(fs.readFileSync(source)),expected);
const result={status:'PORTABLE_DEFINITIONS_POLICY_AND_FRONTEND_PARITY_PASS',checks,checks_count:checks.length,geometry_sha256:expected,owner_data_writes:0,ui_gpu_models:0,native_adapter_claim:false};
fs.writeFileSync(new URL('./PORTABLE-CONTRACT-RESULT.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
