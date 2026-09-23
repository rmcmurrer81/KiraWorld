import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createDoorSystem,createWalkController} from './revision-002/candidate/tools/world_builder_engine/walk_controller.mjs';
import {createWalkController as oldController} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {buildRoomDressing} from './room_dressing_plan.mjs';
const geometry=JSON.parse(fs.readFileSync(new URL('./fixtures/synthetic_habitat.json',import.meta.url)));
const plan=buildRoomDressing(geometry,createDoorSystem(geometry).assemblies());
const before=oldController(geometry,{extraColliders:plan.colliders}),after=createWalkController(geometry,{extraColliders:plan.colliders});
assert.equal(after.snapshot().nearbyDoor,null,'Spawn remains too far away to interact');
for(let i=0;i<5;i++){before.step(.05,{forward:true});after.step(.05,{forward:true});}
assert.equal(before.toggleDoor().ok,false,'Old click step skips its narrow interaction band');
assert.equal(after.toggleDoor().ok,true,'One click step should reach a safe interaction point');
for(let i=0;i<10;i++)after.step(.05,{});
assert.equal(after.doorStates()[0].state,'open');
for(let i=0;i<25;i++)after.step(.05,{forward:true});assert.equal(after.snapshot().roomId,'airlock');
assert.equal(after.toggleDoor('opening_1').ok,true);for(let i=0;i<10;i++)after.step(.05,{});
assert.equal(after.doorStates()[0].state,'closed');
const result={status:'PASS_STEP_BUTTON_DOOR_REACH_REGRESSION',checks:['Old0.55m click step reproduced the interaction gap.','New2.25m reach opens from a safe point after one click step.','Player crosses into airlock and can close the door from the opposite side.','Initial spawn is still outside interaction range.'],
walker_sha256:crypto.createHash('sha256').update(fs.readFileSync(new URL('./revision-002/candidate/tools/world_builder_engine/walk_controller.mjs',import.meta.url))).digest('hex'),gpu_or_browser_started:false};
fs.writeFileSync(new URL('./revision-002/STEP-REACH-TEST.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,checks:result.checks.length}));
