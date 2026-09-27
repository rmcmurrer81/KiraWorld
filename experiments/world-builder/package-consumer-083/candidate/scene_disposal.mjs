// Release each shared resource once, including CPU ImageBitmaps behind textures.
export function disposeScene(root){
 const geometries=new Set(),materials=new Set(),textures=new Set(),images=new Set();
 root.traverse(o=>{
  if(o.geometry)geometries.add(o.geometry);
  for(const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[]){materials.add(m);for(const v of Object.values(m))if(v?.isTexture)textures.add(v);}
 });
 for(const texture of textures)if(texture.image?.close)images.add(texture.image);
 geometries.forEach(g=>g.dispose());textures.forEach(t=>t.dispose());materials.forEach(m=>m.dispose());images.forEach(i=>i.close());
}
