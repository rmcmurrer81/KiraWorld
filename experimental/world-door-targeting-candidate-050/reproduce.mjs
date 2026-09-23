import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
import {createWalkController} from './baseline/walk_controller.mjs';
const [source,expected]=process.argv.slice(2),raw=fs.readFileSync(source);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');assert.equal(sha(raw),expected);
const g=JSON.parse(raw),c=createWalkController(g);
for(let i=0;i<3;i++)c.step(.05,{forward:true});
assert.equal(c.toggleDoor().ok,true);for(let i=0;i<10;i++)c.step(.05,{});
for(let i=0;i<37;i++)c.step(.05,{forward:true});
const facingExit=c.snapshot();assert.equal(facingExit.roomId,'airlock');
for(let i=0;i<4;i++)c.look(Math.PI/(4*.002),0);
const facingEntry=c.snapshot();
const report={status:'BASELINE_ACTUAL_SAVED_AIRLOCK_DIRECTION_IGNORED',geometry_sha256:expected,
 facingExit,facingEntry,looking_direction_changed:Math.abs(facingExit.yaw-facingEntry.yaw)>3,
 same_target_after_half_turn:facingExit.nearbyDoor.id===facingEntry.nearbyDoor.id,
 source_unchanged:sha(fs.readFileSync(source))===expected,models_gpu_ui:0};
assert.equal(report.same_target_after_half_turn,true);
fs.writeFileSync(new URL('./BASELINE-TARGET-REPRODUCTION.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report));
