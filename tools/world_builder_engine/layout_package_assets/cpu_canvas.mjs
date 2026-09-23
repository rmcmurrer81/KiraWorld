// CPU-only compatibility for the unmodified Three exporter/importer. No DOM,
// WebGL, network fetches or model runtime is provided.
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import fs from 'node:fs';
export function installCpuCanvas(modulePath,fontPaths){
  const canvas=createRequire(import.meta.url)(modulePath);
  assert.equal(createRequire(import.meta.url)(modulePath+'/package.json').version,'0.1.100');
  assert.deepEqual(fontPaths.map(v=>v[1]),['Segoe UI','Segoe UI','Consolas'],'Explicit regular, semibold and monospace fonts required');
  for(const [file] of fontPaths)assert.ok(fs.existsSync(file),'Required font file is missing');
  for(const [file,family] of fontPaths){assert.ok(canvas.GlobalFonts.registerFromPath(file,family),'Required font cannot be registered: '+family);assert.ok(canvas.GlobalFonts.has(family));}
  assert.ok(canvas.GlobalFonts.setAlias('Consolas','monospace'),'Missing monospace alias');
  assert.ok(canvas.GlobalFonts.setAlias('Segoe UI','sans-serif'),'Missing sans-serif alias');
  // napi Canvas has a nonbrowser data() method. The official exporter tests
  // image.data to distinguish DataTexture, so hide that method on our instances.
  // Otherwise it would silently export transparent PNGs instead of canvas pixels.
  // Native PNG tasks finish on worker threads out of order. Deliver callbacks
  // in request order so the official exporter's embedded buffer order is stable.
  let pngQueue=Promise.resolve();
  const makeCanvas=()=>{const value=canvas.createCanvas(1,1);Object.defineProperty(value,'data',{value:undefined});
    const toBlob=value.toBlob.bind(value);value.toBlob=(callback,mime)=>{pngQueue=pngQueue.then(()=>new Promise(resolve=>toBlob(blob=>{callback(blob);resolve();},mime)));};return value;};
  const probe=makeCanvas();
  globalThis.HTMLCanvasElement=probe.constructor;
  globalThis.ImageData=canvas.ImageData;
  globalThis.document={createElement(name){assert.equal(name,'canvas');return makeCanvas();}};
  globalThis.FileReader=class {
    readAsArrayBuffer(blob){blob.arrayBuffer().then(value=>{this.result=value;this.onloadend?.();}).catch(error=>this.onerror?.(error));}
    readAsDataURL(blob){blob.arrayBuffer().then(value=>{this.result='data:'+blob.type+';base64,'+Buffer.from(value).toString('base64');this.onloadend?.();}).catch(error=>this.onerror?.(error));}
  };
  globalThis.self=globalThis;
  globalThis.createImageBitmap=async function(blob,options){
    assert.ok(blob instanceof Blob,'Only local embedded Blob images are supported');
    assert.ok(!options?.imageOrientation||options.imageOrientation==='none','Unexpected importer image flip');
    return canvas.loadImage(Buffer.from(await blob.arrayBuffer()));
  };
  const localFetch=globalThis.fetch;
  globalThis.fetch=(url,...args)=>{assert.ok(String(url).startsWith('blob:'),'External fetch rejected');return localFetch(url,...args);};
  return {canvasFactory:makeCanvas,canvas};
}
