import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [root,mode,output]=process.argv.slice(2);assert.ok(root&&['reproduce','fixed'].includes(mode)&&output);
const {verifyPackage,PACKAGE_FILES}=await import(pathToFileURL(path.resolve(root,'package_loader.mjs')));
const original=new Map(PACKAGE_FILES.map(n=>[n,new Uint8Array(fs.readFileSync(path.resolve(root,'sample-package',n)))]));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex'),text=b=>new TextDecoder().decode(b);
function changedGLB(change){
 const files=new Map(original),b=Buffer.from(files.get('scene.glb')),length=b.readUInt32LE(12),json=JSON.parse(b.subarray(20,20+length).toString());change(json);
 let string=JSON.stringify(json);string+=' '.repeat((4-Buffer.byteLength(string)%4)%4);const chunk=Buffer.from(string),rest=b.subarray(20+length),out=Buffer.alloc(20+chunk.length+rest.length);
 b.copy(out,0,0,20);out.writeUInt32LE(out.length,8);out.writeUInt32LE(chunk.length,12);chunk.copy(out,20);rest.copy(out,20+chunk.length);files.set('scene.glb',new Uint8Array(out));
 const manifest=JSON.parse(text(files.get('manifest.json')));manifest.files['scene.glb']={bytes:out.length,sha256:digest(out)};files.set('manifest.json',new TextEncoder().encode(JSON.stringify(manifest)));return files;
}
const cases=[['empty buffer URI',j=>j.buffers[0].uri=''],['null buffer URI',j=>j.buffers[0].uri=null],['empty image URI plus bufferView',j=>j.images[0].uri=''],['external buffer URI',j=>j.buffers[0].uri='https://example.invalid/forbidden.bin'],['external image URI',j=>j.images[0].uri='https://example.invalid/forbidden.png']];
const results=[];
for(const [name,change] of cases){let accepted=false,error=null;try{await verifyPackage(changedGLB(change));accepted=true;}catch(e){error=e.message;}
 results.push({name,accepted,error});if(mode==='fixed')assert.equal(accepted,false,name);
}
await verifyPackage(original);
if(mode==='reproduce')assert.deepEqual(results.map(x=>x.accepted),[true,true,true,false,false]);
fs.writeFileSync(output,JSON.stringify({status:mode==='fixed'?'EMBEDDED_ONLY_URI_ADMISSION_PASS':'BASELINE043_FALSY_URI_ADMISSION_REPRODUCED',results,original_package_accepted:true,network_fetches:0,models_gpu_ui:0},null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({mode,results}));
