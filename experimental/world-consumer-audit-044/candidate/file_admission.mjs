export const PACKAGE_FILES=Object.freeze(['manifest.json','scene.json','scene.glb','ROUNDTRIP.json','README.txt']);
export const MAX_FILE_BYTES=16*1024*1024,MAX_PACKAGE_BYTES=32*1024*1024;
// Check the complete selection before invoking even the first arrayBuffer().
export function admitFiles(selection){
 const files=Array.from(selection||[]);
 if(files.length!==PACKAGE_FILES.length)throw new TypeError('Select exactly the five files from one exported package.');
 const seen=new Set();let total=0;
 for(const file of files){
  if(!file||!PACKAGE_FILES.includes(file.name)||seen.has(file.name))throw new TypeError('Unexpected or duplicate package filename.');
  if(!Number.isSafeInteger(file.size)||file.size<=0||file.size>MAX_FILE_BYTES)throw new TypeError('Each package file must be between 1 byte and 16 MiB.');
  if(typeof file.arrayBuffer!=='function')throw new TypeError('The selected item is not a readable file.');
  seen.add(file.name);total+=file.size;
 }
 if(total>MAX_PACKAGE_BYTES)throw new TypeError('The selected package exceeds 32 MiB.');
 return files;
}
export async function readSelectedPackage(selection){
 const admitted=admitFiles(selection),files=new Map();
 for(const file of admitted){const buffer=await file.arrayBuffer();if(!(buffer instanceof ArrayBuffer)||buffer.byteLength!==file.size)throw new TypeError('Selected file size changed while reading.');files.set(file.name,new Uint8Array(buffer));}
 return files;
}
