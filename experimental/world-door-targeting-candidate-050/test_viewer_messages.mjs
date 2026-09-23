import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8');
const start=source.indexOf('    const nearby=state.nearbyDoor,');
const end=source.indexOf('    camera.position.set(',start);assert.ok(start>0&&end>start);
const update=source.slice(start,end),checks=[];
for(const [nearby,disabled,caption] of [[null,true,'Face a nearby door · F'],[{state:'closed'},false,'Open door · F'],[{state:'open'},false,'Close door · F'],[{state:'opening'},true,'Door moving…']]){
 const context={state:{nearbyDoor:nearby},doorButton:{},doorMessage:{},now:10,doorNoticeUntil:0,doorNotice:''};
 vm.runInNewContext(update,context,{timeout:100});assert.equal(context.doorButton.disabled,disabled);assert.equal(context.doorButton.textContent,caption);checks.push(caption);
}
const callbackStart=source.indexOf('  function interactDoor(){'),callbackEnd=source.indexOf('  doorButton.addEventListener',callbackStart);
assert.ok(callbackStart>0&&callbackEnd>callbackStart);
const result={ok:false,reason:'Face a nearby door to open or close it.'};let calls=0;
const context={controller:{toggleDoor(){calls++;return result;}},performance:{now:()=>5},doorButton:{blur(){}},doorNotice:'',doorNoticeUntil:0};
vm.runInNewContext(source.slice(callbackStart,callbackEnd)+'\ninteractDoor();',context,{timeout:100});
assert.equal(calls,1);assert.equal(context.doorNotice,result.reason);assert.equal(context.doorNoticeUntil,3505);
const receipt={status:'ACTUAL_VIEWER_CALLBACK_AND_LABEL_CODE_PASS',state_cases:checks.length,callback_invocations:calls,real_dom_or_ui:false,
 limits:'Evaluated trusted own-source callback and message code in a Node context with inert UI objects; no visual or browser behavior approval.'};
fs.writeFileSync(new URL('./VIEWER-MESSAGE-RESULT.json',import.meta.url),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(receipt));
