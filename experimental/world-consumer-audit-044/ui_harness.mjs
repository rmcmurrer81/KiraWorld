// Evaluate actual app event handlers with fake DOM/renderer dependencies. No UI,
// browser, WebGL, server, package decoder or user input is invoked.
import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';
export const flush=()=>new Promise(resolve=>setImmediate(resolve));
export async function harness(root){
 const metrics={renderers:0,renders:[],disposedScenes:[],closedImages:[],rendererDisposals:0,loadCalls:0,cancelled:[],scheduled:new Map()};let sequence=0;
 class Element{
  constructor(id){this.id=id;this.disabled=false;this.textContent='';this.files=[];this.handlers={};this.tagName=id==='files'?'INPUT':id==='stage'?'MAIN':'BUTTON';}
  addEventListener(type,callback){(this.handlers[type]??=[]).push(callback);}
  async dispatch(type,event={}){for(const fn of this.handlers[type]||[])await fn(event);}
  blur(){document.activeElement=null;}
  append(){}getBoundingClientRect(){return {width:800,height:450};}setPointerCapture(){}
 }
 const elements=Object.fromEntries(['stage','status','files','enter','pause'].map(n=>[n,new Element(n)]));
 const window=new Element('window'),document=new Element('document');document.getElementById=id=>elements[id];document.hidden=false;document.activeElement=null;
 const loaded=[];
 const THREE={WebGLRenderer:class{constructor(){metrics.renderers++;this.domElement={};}setPixelRatio(){}setSize(){}clear(){metrics.renders.push('clear');}render(scene){metrics.renders.push(scene.id);}dispose(){metrics.rendererDisposals++;}},PerspectiveCamera:class{constructor(){this.position={set(){}};this.rotation={set(){}};}updateProjectionMatrix(){}},Color:class{},HemisphereLight:class{},ACESFilmicToneMapping:4};
 function packageValue(id){
  let image={close(){metrics.closedImages.push(id);}},texture={isTexture:true,image,dispose(){}},material={map:texture,dispose(){}},geometry={dispose(){metrics.disposedScenes.push(id);}};
  const scene={id,traverse(fn){fn({geometry,material});},add(){}};let steps=0;
  return {scene,runtime:{snapshot:()=>({feet:[0,0,0],yaw:0,pitch:0,roomName:id,nearbyDoor:null,blocked:null}),step(){steps++;},look(){},toggleDoor:()=>({ok:true,state:'opening'}),doorStates:()=>[]},applyDoorStates(){},get steps(){return steps;}};
 }
 const dependencies={
  './vendor/three/build/three.module.js':THREE,
  './package_loader.mjs':{loadPackage:()=>{metrics.loadCalls++;return new Promise((resolve,reject)=>loaded.push({resolve,reject}));}},
  './file_admission.mjs':{readSelectedPackage:async selection=>selection},
  './runtime.mjs':{AVATAR:{eye:1.56}}
 };
 // The new cleanup helper is real code too; only its scene objects are doubles.
 const disposal=path.resolve(root,'scene_disposal.mjs');
 if(fs.existsSync(disposal))dependencies['./scene_disposal.mjs']=await import('file:///'+disposal.replaceAll('\\','/'));
 const context=vm.createContext({console,document,window,devicePixelRatio:1,performance:{now:()=>10},requestAnimationFrame:fn=>{const id=++sequence;metrics.scheduled.set(id,fn);return id;},cancelAnimationFrame:id=>{metrics.cancelled.push(id);metrics.scheduled.delete(id);},Map,Set});
 const app=new vm.SourceTextModule(fs.readFileSync(path.resolve(root,'app.mjs'),'utf8'),{context});
 await app.link(async specifier=>{const values=dependencies[specifier];if(!values)throw Error('Unexpected application dependency '+specifier);return new vm.SyntheticModule(Object.keys(values),function(){for(const [name,value]of Object.entries(values))this.setExport(name,value);},{context});});await app.evaluate();
 return {metrics,elements,window,document,loaded,packageValue};
}
