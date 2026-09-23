import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [root,output]=process.argv.slice(2),{createRuntime}=await import(pathToFileURL(path.resolve(root,'runtime.mjs')));
const bytes=fs.readFileSync(path.resolve(root,'sample-package/scene.json'),'utf8'),m=JSON.parse(bytes),a=createRuntime(m),b=createRuntime(m);
for(let i=0;i<8;i++)a.step(.05,{forward:true});assert.ok(a.toggleDoor('door:opening_1').ok);for(let i=0;i<8;i++)a.step(.05);
assert.equal(a.doorStates()[0].state,'open');assert.ok(b.doorStates().every(s=>s.state==='closed'));assert.deepEqual(b.snapshot().feet,m.navigation.spawn_feet);
const reloaded=createRuntime(m);assert.ok(reloaded.doorStates().every(s=>s.state==='closed'));assert.deepEqual(reloaded.snapshot().feet,m.navigation.spawn_feet);assert.deepEqual(m,JSON.parse(bytes));
fs.writeFileSync(output,JSON.stringify({status:'SESSION_STATE_ISOLATION_AND_RELOAD_PASS',checks:['opening one session does not affect another','new session starts all leaves closed at declared spawn','portable metadata is unchanged'],physics_runtime_changed:false,ui_gpu_models:0},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:'SESSION_STATE_ISOLATION_AND_RELOAD_PASS',checks:3}));
