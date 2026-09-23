import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import assert from 'node:assert/strict';import {webcrypto} from 'node:crypto';import {pathToFileURL} from 'node:url';
const [root,output]=process.argv.slice(2);assert.ok(root&&output);
const disposal=await import(pathToFileURL(path.resolve(root,'scene_disposal.mjs'))),runtime=await import(pathToFileURL(path.resolve(root,'runtime.mjs'))),admission=await import(pathToFileURL(path.resolve(root,'file_admission.mjs')));
function scene(){const calls={geometry:0,material:0,texture:0,image:0},image={close(){calls.image++;}},texture={isTexture:true,image,dispose(){calls.texture++;}},material={map:texture,emissiveMap:texture,dispose(){calls.material++;}},geometry={dispose(){calls.geometry++;}},object={geometry,material:[material,material],userData:{}};
 return {calls,root:{updateMatrixWorld(){},traverse(fn){fn(object);fn(object);}}};}
const direct=scene();disposal.disposeScene(direct.root);assert.deepEqual(direct.calls,{geometry:1,material:1,texture:1,image:1});
const failure=scene(),context=vm.createContext({console,TextDecoder,Uint8Array,ArrayBuffer,DataView,Map,Set,crypto:webcrypto});
const modules={
 './vendor/three/build/three.module.js':{},
 './vendor/three/examples/jsm/loaders/GLTFLoader.js':{GLTFLoader:class{async parseAsync(){return {scene:failure.root};}}},
 './runtime.mjs':runtime,'./file_admission.mjs':admission,'./scene_disposal.mjs':disposal
};
const module=new vm.SourceTextModule(fs.readFileSync(path.resolve(root,'package_loader.mjs'),'utf8'),{context});
await module.link(async name=>{const values=modules[name];assert.ok(values,name);return new vm.SyntheticModule(Object.keys(values),function(){for(const [k,v]of Object.entries(values))this.setExport(k,v);},{context});});await module.evaluate();
const files=new Map(admission.PACKAGE_FILES.map(n=>[n,new Uint8Array(fs.readFileSync(path.resolve(root,'sample-package',n)))]));
await assert.rejects(()=>module.namespace.loadPackage(files),/semantic objects differ/);assert.deepEqual(failure.calls,{geometry:1,material:1,texture:1,image:1});
const result={status:'SHARED_RESOURCE_AND_REJECTED_IMPORT_CLEANUP_PASS',checks:['shared geometry/material/texture/ImageBitmap each disposed once','actual loader catch releases decoded scene after binding failure'],
 real_loader_catch_executed:true,parser_and_scene_test_doubles:true,file_hash_bindings_verified:true,publisher_identity_authenticated:false,ui_browser_webgl_server_gpu_model_calls:0};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:result.status,checks:2}));
