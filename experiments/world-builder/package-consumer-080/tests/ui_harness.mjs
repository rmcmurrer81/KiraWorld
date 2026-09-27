// Actual app + history host + library modules; inert DOM/audio/renderer adapters.
import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';
export const flush=()=>new Promise(resolve=>setImmediate(resolve));
export async function harness(root,{deferHistory=false}={}){
 const metrics={renderers:0,renders:[],disposedScenes:[],closedImages:[],rendererDisposals:0,loadCalls:0,cancelled:[],scheduled:new Map(),steps:[],looks:0,pointerReleases:[],audios:[],historyFetches:0};let sequence=0,document,clock=10;
 class Element{
  constructor(id,tag='BUTTON'){this.id=id;this.disabled=false;this._text='';this.files=[];this.handlers={};this.tagName=tag.toUpperCase();this.children=[];this.parent=null;this.attrs={};this.hidden=false;this.ownerDocument=document;}
  addEventListener(type,callback){(this.handlers[type]??=[]).push(callback);}
  removeEventListener(type,callback){this.handlers[type]=(this.handlers[type]||[]).filter(f=>f!==callback);}
  async dispatch(type,event={}){const e={target:this,preventDefault(){this.prevented=true;},stopPropagation(){this.stopped=true;},...event};for(let node=this;node;node=node.parent){for(const fn of [...node.handlers[type]||[]])await fn(e);if(e.stopped)break;}return e;}
  set innerHTML(_){throw Error('Unsafe HTML in inert DOM');}
  set textContent(v){this._text=String(v);for(const n of this.children)n.parent=null;this.children=[];}
  get textContent(){return this._text+this.children.map(n=>n.textContent).join('');}
  setAttribute(k,v){this.attrs[k]=String(v);}
  removeAttribute(k){delete this.attrs[k];}
  append(...nodes){for(const n of nodes){if(n.parent)n.parent.children=n.parent.children.filter(c=>c!==n);this.children.push(n);n.parent=this;}}
  replaceChildren(...nodes){this.textContent='';this.append(...nodes);}
  contains(n){return this===n||this.children.some(c=>c.contains(n));}
  closest(){for(let n=this;n;n=n.parent)if(['INPUT','BUTTON','SELECT','TEXTAREA','A','SUMMARY','DETAILS'].includes(n.tagName)||n.isContentEditable||n.attrs?.role==='button'||Object.hasOwn(n.attrs||{},'tabindex')||n.tabIndex!==undefined)return n;return null;}
  blur(){if(document.activeElement===this)document.activeElement=null;}
  focus(){document.activeElement=this;void this.dispatch('focusin');}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);this.parent=null;}
  getBoundingClientRect(){return {width:800,height:450};}
  setPointerCapture(id){this.capture=id;}
  releasePointerCapture(id){metrics.pointerReleases.push(id);this.capture=null;}
 }
 class Audio extends Element{
  constructor(){super('','AUDIO');this.paused=true;this.volume=1;this.muted=false;this.duration=NaN;this.currentTime=0;this.playCalls=0;this.pauseCalls=0;this.loads=0;this.src='';metrics.audios.push(this);}
  pause(){this.paused=true;this.pauseCalls++;for(const fn of [...this.handlers.pause||[]])fn({target:this});}
  play(){this.playCalls++;throw Error('Real playback is forbidden in this test');}
  load(){this.loads++;this.duration=NaN;this.currentTime=0;}
  removeAttribute(k){super.removeAttribute(k);if(k==='src')this.src='';}
 }
 const window=new Element('window','WINDOW');document=new Element('document','DOCUMENT');document.parent=window;document.hidden=false;document.activeElement=null;document.createElement=tag=>tag==='audio'?new Audio():new Element('',tag);
 const elements=Object.fromEntries(['stage','status','files','enter','pause','crop-panel','shade','crop-readout','history-entry','history-container','history-message','step-controls','current-room','nearby-door',...['forward','backward','left','right','turnLeft','turnRight','lookUp','lookDown'].map(n=>'step-'+n)].map(n=>[n,new Element(n,n==='files'||n==='shade'?'INPUT':n==='stage'?'MAIN':['crop-panel','step-controls'].includes(n)?'DETAILS':['status','history-container','history-message','crop-readout','current-room'].includes(n)?'DIV':'BUTTON')]));
 for(const n of Object.values(elements))document.append(n);elements['crop-panel'].hidden=true;elements['crop-panel'].append(elements.shade,elements['crop-readout']);document.getElementById=id=>elements[id];
 elements['step-controls'].append(elements['current-room'],...Object.entries(elements).filter(([id])=>id.startsWith('step-')&&id!=='step-controls').map(([,el])=>el),elements['nearby-door']);
 elements['step-controls'].hidden=true;for(const [id,el]of Object.entries(elements))if(id==='nearby-door'||id.startsWith('step-')&&id!=='step-controls')el.disabled=true;
 for(const [action,label]of Object.entries({forward:'Step forward',backward:'Step backward',left:'Step left',right:'Step right',turnLeft:'Turn left',turnRight:'Turn right',lookUp:'Look up',lookDown:'Look down'}))elements['step-'+action].textContent=label;
 const loaded=[],historyLoads=[];
 const THREE={WebGLRenderer:class{constructor(){metrics.renderers++;this.domElement=new Element('canvas','CANVAS');}setPixelRatio(){}setSize(){}clear(){metrics.renders.push('clear');}render(scene){metrics.renders.push(scene.id);}dispose(){metrics.rendererDisposals++;}},PerspectiveCamera:class{constructor(){this.position={set(){}};this.rotation={set(){}};}updateProjectionMatrix(){}},Color:class{},HemisphereLight:class{},ACESFilmicToneMapping:4};
 function packageValue(id){
  const image={close(){metrics.closedImages.push(id);}},texture={isTexture:true,image,dispose(){}},material={map:texture,dispose(){}},geometry={dispose(){metrics.disposedScenes.push(id);}};
  const scene={id,traverse(fn){fn({geometry,material});},add(){}};let steps=0;
  return {metadata:{rooms:[{id:'quarters',functional_role:'habitat'},{id:'greenhouse',functional_role:'greenhouse'},{id:'corridor',functional_role:'corridor'}]},scene,runtime:{snapshot:()=>({feet:[0,0,0],yaw:0,pitch:0,roomId:'quarters',roomName:id,nearbyDoor:null,blocked:null}),step(dt,input){steps++;metrics.steps.push({dt,input});},look(){metrics.looks++;},toggleDoor:()=>({ok:true,state:'opening'}),doorStates:()=>[]},applyDoorStates(){},get steps(){return steps;}};
 }
 const dependencies={'./vendor/three/build/three.module.js':THREE,'./package_loader.mjs':{loadPackage:()=>{metrics.loadCalls++;return new Promise((resolve,reject)=>loaded.push({resolve,reject}));}},'./file_admission.mjs':{readSelectedPackage:async s=>s},'./runtime.mjs':{AVATAR:{eye:1.56}}};
 const fixture=JSON.parse(fs.readFileSync(path.resolve(root,'history-library.json'),'utf8'));
 const context=vm.createContext({console,document,window,URL,devicePixelRatio:1,performance:{now:()=>clock},requestAnimationFrame:fn=>{const id=++sequence;metrics.scheduled.set(id,fn);return id;},cancelAnimationFrame:id=>{metrics.cancelled.push(id);metrics.scheduled.delete(id);},Map,Set,
  fetch:async()=>{metrics.historyFetches++;if(deferHistory)return new Promise((resolve,reject)=>historyLoads.push({resolve:v=>resolve({ok:true,json:async()=>v??fixture}),reject}));return {ok:true,json:async()=>fixture};}});
 const cache=new Map();
 async function moduleFor(specifier){if(cache.has(specifier))return cache.get(specifier);const values=dependencies[specifier];
  const mod=values?new vm.SyntheticModule(Object.keys(values),function(){for(const [k,v]of Object.entries(values))this.setExport(k,v);},{context}):new vm.SourceTextModule(fs.readFileSync(path.resolve(root,specifier),'utf8'),{context});cache.set(specifier,mod);if(!values)await mod.link(moduleFor);return mod;}
 const app=await moduleFor('./app.mjs');await app.evaluate();
 const walk=async(time,frameTime)=>{clock=time??clock+25;for(const [id,fn]of [...metrics.scheduled]){metrics.scheduled.delete(id);fn(frameTime??clock);}};
 return {metrics,elements,window,document,loaded,historyLoads,packageValue,walk};
}
