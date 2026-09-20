import * as THREE from './three.module.js';
import {GLTFLoader} from './addons/loaders/GLTFLoader.js';
import {OrbitControls} from './addons/controls/OrbitControls.js';
const el=id=>document.getElementById(id);
async function exact(url,hash){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Missing pinned file: '+url);const raw=await r.arrayBuffer();
 const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');if(hash&&actual!==hash)throw Error('Changed pinned file: '+url);return raw;}
const decode=raw=>JSON.parse(new TextDecoder().decode(raw));
async function start(){
 const catalog=decode(await exact('/frames.json'));if(catalog.contract!=='original_frame_specimens_v1'||catalog.imported_geometry_bytes!==0)throw Error('Original frame contract required');
 const scene=new THREE.Scene();scene.background=new THREE.Color('#e4e9ea');
 const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;el('viewport').append(renderer.domElement);
 const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,.01,50),orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.target.set(0,.23,0);
 scene.add(new THREE.HemisphereLight(0xffffff,0x757c7c,2.4));const light=new THREE.DirectionalLight(0xfff6e7,2.1);light.position.set(3,6,4);scene.add(light);
 const grid=new THREE.GridHelper(5,50,0x85939b,0xbdc8ce);scene.add(grid);
 let model=null,recipe=null,parts=new Map(),outline=null,generation=0;
 const select=el('variant');for(const v of catalog.variants){const o=document.createElement('option');o.value=v.id;o.textContent=v.name;select.append(o);}
 function view(name){const extent=recipe?recipe.spec.mattress_length:2,center=new THREE.Vector3(0,.23,0);camera.up.set(0,1,0);
   const poses={perspective:[extent*1.05,extent*.8,extent*1.25],above:[0,extent*1.7,.001],side:[extent*1.7,.4,0],end:[0,.4,extent*1.7],below:[extent*.6,-extent,extent*.7]};camera.position.set(...poses[name]);orbit.target.copy(center);orbit.update();}
 function update(){if(!recipe)return;const stage=Number(el('stage').value),selected=el('part').value,only=el('isolate').checked,explode=el('explode').checked;
   for(const part of recipe.parts){const node=parts.get(part.id);node.visible=part.stage<=stage&&(!only||!selected||selected===part.id);node.position.set(...part.position);
     if(explode){node.position.y+=(part.stage-1)*.16;if(part.role==='side_rail'||part.role==='slat_ledger')node.position.x+=Math.sign(part.position[0])*.18;if(part.role==='end_rail')node.position.z+=Math.sign(part.position[2])*.18;}
   }
   const step=recipe.construction_order[stage-1];el('step').textContent=stage+'. '+step.name+'. '+step.purpose;
   const p=recipe.parts.find(p=>p.id===selected),links=p?recipe.connections.filter(c=>c.child===p.id||c.parent===p.id):[];
   el('part-info').textContent=p?p.name+' · '+p.size.map(v=>(v*1000).toFixed(0)).join(' × ')+' mm · '+links.length+' verified face contacts.':recipe.parts.length+' separate original parts. Select a part to inspect its dimensions and connections.';
   el('mode').textContent=explode?'Exploded inspection: parts are deliberately separated.':'Assembled frame: components meet at verified faces.';
   if(outline)scene.remove(outline);outline=null;if(p&&parts.get(p.id).visible){model.updateMatrixWorld(true);outline=new THREE.Box3Helper(new THREE.Box3().setFromObject(parts.get(p.id),true),0x216f99);scene.add(outline);}
 }
 async function load(){const token=++generation,v=catalog.variants.find(v=>v.id===select.value);el('status').textContent='Checking original meshes…';if(model){scene.remove(model);model=null;}if(outline){scene.remove(outline);outline=null;}parts.clear();
   const r=decode(await exact(v.recipe,v.recipe_sha256)),raw=await exact(v.glb,v.glb_sha256);if(r.reference_geometry_imported||r.imported_geometry_bytes!==0||r.acceptance.complete_bed)throw Error('Invalid original frame provenance');
   const result=await new GLTFLoader().parseAsync(raw,'');if(token!==generation)return;
   if((result.parser.json.images||[]).length||(result.parser.json.textures||[]).length)throw Error('Unexpected imported texture');
   const parsed=new Map();result.scene.traverse(n=>{if(n.isMesh){if(!n.userData.newly_authored_geometry||parsed.has(n.userData.part_id))throw Error('Invalid original part identity');parsed.set(n.userData.part_id,n);}});
   if(parsed.size!==r.parts.length)throw Error('Constructed part count differs');result.scene.updateMatrixWorld(true);
   for(const p of r.parts){const n=parsed.get(p.id);if(!n)throw Error('Missing original part: '+p.id);const b=new THREE.Box3().setFromObject(n,true);for(const k of ['min','max'])if(b[k].toArray().some((x,i)=>Math.abs(x-p.bounds[k][i])>1e-5))throw Error('Original part rendered at wrong dimensions: '+p.id);}
   model=result.scene;recipe=r;parts=parsed;scene.add(model);el('part').replaceChildren(new Option('All components',''));for(const p of recipe.parts)el('part').append(new Option(p.name,p.id));
   el('stage').value='4';el('isolate').checked=false;el('explode').checked=false;el('title').textContent=v.name;
   el('status').textContent=recipe.parts.length+' original meshes verified · '+v.triangles+' triangles · '+recipe.mattress_interface.slat_count+' supported slats · 6 feet';
   el('dimensions').textContent='Authored mattress footprint: '+recipe.spec.mattress_width.toFixed(2)+' × '+recipe.spec.mattress_length.toFixed(2)+' m. Slat support top: '+recipe.mattress_interface.base_y.toFixed(3)+' m. Mattress not built.';
   view('perspective');update();
 }
 for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>view(b.dataset.view));
 for(const id of ['stage','part','isolate','explode'])el(id).addEventListener('input',update);select.addEventListener('change',()=>load().catch(fail));
 addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
 function frame(){orbit.update();renderer.render(scene,camera);requestAnimationFrame(frame);}frame();await load();
}
function fail(error){el('error').hidden=false;el('error').textContent='Frame inspection unavailable: '+error.message;el('status').textContent='Preview validation failed';}
start().catch(fail);
