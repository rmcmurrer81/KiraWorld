import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [root,mode,output]=process.argv.slice(2),{verifyPackage,PACKAGE_FILES}=await import(pathToFileURL(path.resolve(root,'package_loader.mjs')));
const original=new Map(PACKAGE_FILES.map(n=>[n,new Uint8Array(fs.readFileSync(path.resolve(root,'sample-package',n)))]));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function mutated(change){const f=new Map(original),b=Buffer.from(f.get('scene.glb')),n=b.readUInt32LE(12),j=JSON.parse(b.subarray(20,20+n).toString()),bin=Buffer.from(b.subarray(28+n));change(j,bin);
 let text=JSON.stringify(j);text+=' '.repeat((4-Buffer.byteLength(text)%4)%4);const chunk=Buffer.from(text),out=Buffer.alloc(28+chunk.length+bin.length);b.copy(out,0,0,20);out.writeUInt32LE(out.length,8);out.writeUInt32LE(chunk.length,12);chunk.copy(out,20);out.writeUInt32LE(bin.length,20+chunk.length);out.writeUInt32LE(0x004e4942,24+chunk.length);bin.copy(out,28+chunk.length);
 f.set('scene.glb',new Uint8Array(out));const manifest=JSON.parse(new TextDecoder().decode(f.get('manifest.json')));manifest.files['scene.glb']={bytes:out.length,sha256:sha(out)};f.set('manifest.json',new TextEncoder().encode(JSON.stringify(manifest)));return f;}
const first=(j)=>j.bufferViews[j.images[0].bufferView].byteOffset||0;
const mutations=[
 ['huge PNG width',(j,b)=>b.writeUInt32BE(8192,first(j)+16)],
 ['maximum unsigned width',(j,b)=>b.writeUInt32BE(0xffffffff,first(j)+16)],
 ['zero PNG width',(j,b)=>b.writeUInt32BE(0,first(j)+16)],
 ['zero PNG height',(j,b)=>b.writeUInt32BE(0,first(j)+20)],
 ['aggregate decoded pixel budget',(j,b)=>{for(const image of j.images){const o=j.bufferViews[image.bufferView].byteOffset||0;b.writeUInt32BE(1024,o+16);b.writeUInt32BE(1024,o+20);}}],
 ['image view outside BIN',(j)=>j.bufferViews[j.images[0].bufferView].byteOffset=j.buffers[0].byteLength+4],
 ['unsafe offset integer',(j)=>j.bufferViews[j.images[0].bufferView].byteOffset=2**53],
 ['range sum beyond safe integer',(j)=>{const v=j.bufferViews[j.images[0].bufferView];v.byteOffset=Number.MAX_SAFE_INTEGER-10;v.byteLength=100;}],
 ['fractional image offset',(j)=>j.bufferViews[j.images[0].bufferView].byteOffset=.5],
 ['truncated IHDR view',(j)=>j.bufferViews[j.images[0].bufferView].byteLength=32],
 ['bad IHDR length',(j,b)=>b.writeUInt32BE(12,first(j)+8)],
 ['bad IHDR type',(j,b)=>b.writeUInt32BE(0x49444154,first(j)+12)],
 ['unsupported PNG bit depth',(j,b)=>b[first(j)+24]=16],
 ['unsupported PNG color type',(j,b)=>b[first(j)+25]=0],
 ['invalid PNG filter method',(j,b)=>b[first(j)+27]=1],
 ['PNG signature missing',(j,b)=>b[first(j)]=0],
 ['declared buffer exceeds BIN',(j)=>j.buffers[0].byteLength+=8],
 ['duplicate references still count toward aggregate',(j,b)=>{const image={...j.images[0]};b.writeUInt32BE(768,first(j)+16);b.writeUInt32BE(768,first(j)+20);j.images=Array.from({length:128},()=>({...image}));}],
 ['too many duplicate image references',(j)=>{const image={...j.images[0]};j.images=Array.from({length:129},()=>({...image}));}],
 ['negative image bufferView',(j)=>j.images[0].bufferView=-1]
];
const results=[];for(const [name,change]of mutations){let accepted=false,error=null;try{await verifyPackage(mutated(change));accepted=true;}catch(e){error=e.message;}results.push({name,accepted,error});assert.equal(accepted,mode==='reproduce',name);}
const valid=await verifyPackage(original);if(mode==='fixed')assert.deepEqual(valid.embeddedImageBudget,{images:67,pixels:17104896});
const result={status:mode==='fixed'?'PNG_PREDECODE_RESOURCE_ADMISSION_PASS':'BASELINE043_UNBOUNDED_PNG_HEADER_ADMISSION_REPRODUCED',results,valid_package_images:67,valid_package_pixels:17104896,image_decodes:0,network_ui_gpu_models:0};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:result.status,cases:results.length}));
