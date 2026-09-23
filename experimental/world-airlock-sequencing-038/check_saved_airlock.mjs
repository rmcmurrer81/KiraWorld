// Read-only audit of an explicit saved geometry; no preview or source writes.
import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {createDoorSystem as installedDoors} from './baseline/walk_controller.mjs';
import {createDoorSystem} from './candidate/tools/world_builder_engine/walk_controller.mjs';
const [source,expected]=process.argv.slice(2);if(!source||!expected)throw new Error('Supply geometry path and exact SHA256');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(source);assert.equal(hash(raw),expected);
const geometry=JSON.parse(raw),feet=[1.5,0,-2],checks=[],before=JSON.stringify(geometry);
const old=installedDoors(geometry),current=createDoorSystem(geometry);
assert.equal(old.toggle('opening_1',feet).ok,true);assert.equal(old.toggle('opening_2',feet).ok,true);
for(let i=0;i<8;i++)old.advance(.05,feet);
assert.ok(old.all().filter(d=>['opening_1','opening_2'].includes(d.id)).every(d=>d.state==='open'));
checks.push('Installed baseline permits both actual airlock doors to open together');
assert.equal(current.toggle('opening_1',feet).ok,true);let held=current.toggle('opening_2',feet);assert.equal(held.ok,false);assert.equal(held.interlock.peerDoorId,'opening_1');
for(let i=0;i<8;i++)current.advance(.05,feet);assert.equal(current.toggle('opening_2',feet).ok,false);
assert.equal(current.toggle('opening_1',feet).ok,true);for(let i=0;i<8;i++)current.advance(.05,feet);assert.equal(current.toggle('opening_2',feet).ok,true);
checks.push('Candidate refuses peer while pending/open and allows it after first door closes');
assert.equal(JSON.stringify(geometry),before);assert.equal(hash(fs.readFileSync(source)),expected);checks.push('Source object and original geometry bytes unchanged');
const room=geometry.rooms.find(r=>geometry.functional_program?.[r.id]==='airlock');
const report={status:'ACTUAL_SAVED_AIRLOCK_READ_ONLY_PASS',geometry_sha256:expected,checks,checks_count:checks.length,
 room:{id:room.id,name:room.name,width:room.width,depth:room.depth,height:room.height},
 pairs:current.interlocks(),blocked_reason:held.reason,installed_both_open:true,candidate_sequencing_pass:true,
 model_gpu_ui_preview_jobs:0,source_modified:false,limitations:['Only door sequencing was tested. No pressure or seal simulation, exterior EVA access, visual review, or installation.']};
fs.writeFileSync(new URL('./ACTUAL-AIRLOCK-RESULT.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:report.status,checks:checks.length,source_modified:false}));
