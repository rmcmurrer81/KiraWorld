import fs from 'node:fs';import assert from 'node:assert/strict';import {harness,flush} from './ui_harness.mjs';
const [root,mode,output]=process.argv.slice(2);assert.ok(root&&['reproduce','fixed'].includes(mode)&&output);const cases=[];
const h=await harness(root),picker=h.elements.files;picker.files=['package A'];const pending=picker.dispatch('change');await flush();assert.equal(h.metrics.loadCalls,1);
if(mode==='fixed')assert.equal(picker.disabled,true);else assert.equal(picker.disabled,false);
cases.push({name:'picker disabled during pending import',actual:picker.disabled});
await h.window.dispatch('pagehide');const late=h.packageValue('late');h.loaded[0].resolve(late);await pending;
if(mode==='fixed'){assert.equal(h.metrics.renderers,0);assert.deepEqual(h.metrics.disposedScenes,['late']);assert.deepEqual(h.metrics.closedImages,['late']);assert.equal(h.metrics.scheduled.size,0);}else assert.equal(h.metrics.renderers,1);
cases.push({name:'late completed import after pagehide does not create renderer',actual:h.metrics.renderers===0});
if(mode==='fixed'){
 const s=await harness(root);s.elements.files.files=['A'];let load=s.elements.files.dispatch('change');await flush();s.loaded[0].resolve(s.packageValue('A'));await load;
 assert.equal(s.elements.files.disabled,false);assert.equal(s.elements.enter.disabled,false);assert.ok(s.metrics.renders.includes('A'));
 await s.elements.enter.dispatch('click');assert.equal(s.metrics.scheduled.size,1);await s.elements.enter.dispatch('click');assert.equal(s.metrics.scheduled.size,1);
 await s.window.dispatch('keydown',{code:'Escape'});assert.equal(s.metrics.scheduled.size,0);assert.equal(s.elements.pause.disabled,true);cases.push({name:'start twice schedules once; Escape cancels loop',actual:true});
 s.elements.files.files=['B'];load=s.elements.files.dispatch('change');await flush();assert.equal(s.elements.enter.disabled,true);assert.equal(s.elements.files.disabled,true);s.loaded[1].resolve(s.packageValue('B'));await load;
 assert.deepEqual(s.metrics.disposedScenes,['A']);assert.deepEqual(s.metrics.closedImages,['A']);assert.equal(s.metrics.renders.at(-1),'B');assert.equal(s.metrics.scheduled.size,0);cases.push({name:'package switch releases A and loads B paused',actual:true});
 s.elements.files.files=['bad'];load=s.elements.files.dispatch('change');await flush();s.loaded[2].reject(Error('malformed package'));await load;
 assert.deepEqual(s.metrics.disposedScenes,['A','B']);assert.deepEqual(s.metrics.closedImages,['A','B']);assert.equal(s.metrics.renders.at(-1),'clear');assert.equal(s.elements.enter.disabled,true);assert.equal(s.elements.files.disabled,false);assert.match(s.elements.status.textContent,/Package held: malformed package/);cases.push({name:'failed load clears stale scene and allows a new selection',actual:true});
 s.elements.files.files=['C'];load=s.elements.files.dispatch('change');await flush();s.loaded[3].resolve(s.packageValue('C'));await load;assert.equal(s.elements.enter.disabled,false);assert.equal(s.metrics.renders.at(-1),'C');cases.push({name:'load recovers after prior failure',actual:true});
 await s.window.dispatch('pagehide');assert.deepEqual(s.metrics.disposedScenes,['A','B','C']);assert.equal(s.metrics.rendererDisposals,1);assert.equal(s.metrics.scheduled.size,0);
 await s.elements.files.dispatch('change');await flush();assert.equal(s.metrics.loadCalls,4);cases.push({name:'closed app ignores later load requests',actual:true});
 const b=await harness(root);b.elements.files.files=['old'];const old=b.elements.files.dispatch('change');await flush();await b.window.dispatch('pagehide');await b.window.dispatch('pageshow',{persisted:true});
 assert.equal(b.elements.files.disabled,false);assert.equal(b.elements.enter.disabled,true);assert.equal(b.elements.files.value,'');
 b.elements.files.files=['fresh'];const fresh=b.elements.files.dispatch('change');await flush();assert.equal(b.metrics.loadCalls,2);
 b.loaded[0].resolve(b.packageValue('stale'));await old;assert.equal(b.metrics.renderers,0);assert.equal(b.elements.files.disabled,true);assert.deepEqual(b.metrics.disposedScenes,['stale']);
 b.loaded[1].resolve(b.packageValue('fresh'));await fresh;assert.equal(b.metrics.renders.at(-1),'fresh');assert.equal(b.elements.files.disabled,false);assert.equal(b.metrics.scheduled.size,0);cases.push({name:'back-forward restored page resets; old import cannot replace or unlock fresh request',actual:true});
}
const result={status:mode==='fixed'?'CPU_ACTUAL_APP_LIFECYCLE_PASS':'BASELINE043_PENDING_SELECTION_AND_LATE_RENDER_REPRODUCED',cases,real_app_event_handlers:true,dom_and_renderer_test_doubles:true,ui_browser_webgl_server_model_gpu_calls:0};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({mode,cases}));
