import * as THREE from './three.module.js';
import {BeddingSimulation,LIMITATIONS} from './mattress_physics.mjs';
// Recording is disabled in this read-only disposable inspection.
const studyResponse=await fetch('/study.json');
if(!studyResponse.ok)throw Error('Saved study is unavailable');
const study=await studyResponse.json();
const $=id=>document.getElementById(id),canvas=$('scene'),view=$('view');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene();scene.background=new THREE.Color('#182b2c');scene.fog=new THREE.Fog('#182b2c',5,12);
const camera=new THREE.PerspectiveCamera(38,1,.02,30);let cameraView='angle';
// Recorded with the actual scene; no geometry is hidden or moved by this label.
const hudCanvas=document.createElement('canvas');hudCanvas.width=1200;hudCanvas.height=150;const hudContext=hudCanvas.getContext('2d');
const hudTexture=new THREE.CanvasTexture(hudCanvas),hud=new THREE.Sprite(new THREE.SpriteMaterial({map:hudTexture,depthTest:false,depthWrite:false}));hud.renderOrder=999;camera.add(hud);scene.add(camera);
function updateHUD(m){hudContext.clearRect(0,0,1200,150);hudContext.fillStyle='rgba(10,23,30,.88)';hudContext.fillRect(0,0,1200,150);hudContext.fillStyle='#f1f6fa';hudContext.font='bold 32px sans-serif';hudContext.fillText('BLANKET CONTACT · ENGINEERING TEST',24,39);hudContext.fillStyle=cloth.visible?'#79bbff':'#ffca77';hudContext.font='27px sans-serif';hudContext.fillText((cloth.visible?'BLUE BLANKET VISIBLE':'BLANKET HIDDEN — physics stays active')+' · '+m.mattress_load_newtons.toFixed(0)+' N load · '+m.time_s.toFixed(1)+' s',24,80);hudContext.fillStyle='#e3ebef';hudContext.font='24px sans-serif';hudContext.fillText('Mesh overlap '+(m.surface_mesh_contact.max_penetration_m*1000).toFixed(2)+' mm · '+$('status').textContent.slice(0,70),24,122);hudTexture.needsUpdate=true;const h=2*Math.tan(camera.fov*Math.PI/360)*3,w=h*camera.aspect;hud.scale.set(Math.min(w*.94,3.1),Math.min(w*.94,3.1)/8,1);hud.position.set(0,h/2-hud.scale.y/2-.025,-3);}
scene.add(new THREE.HemisphereLight(0xd9f5e9,0x273b37,2));
const key=new THREE.DirectionalLight(0xffefda,4);key.position.set(-2,4,2);key.castShadow=true;key.shadow.mapSize.set(2048,2048);key.shadow.camera.left=-3;key.shadow.camera.right=3;key.shadow.camera.top=3;key.shadow.camera.bottom=-3;key.shadow.bias=-.0003;scene.add(key);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(30,30),new THREE.MeshStandardMaterial({color:0x223b38,roughness:1}));floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;scene.add(floor);
let sim,group,cloth,pillow,head,mattress,loadArrow,paused=true,frames=0,lastFrameMs=0,runUntilFrame=0,batchStartedAt=0;let displayDirty=true;
function mesh(geometry,material){const m=new THREE.Mesh(geometry,material);m.castShadow=true;m.receiveShadow=true;group.add(m);return m;}
function dynamicGeometry(positions,triangles){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setIndex(triangles);g.computeVertexNormals();return g;}
function supportedShell(m){
 const pos=Array.from(m.p),tris=m.triangles.slice();for(let i=0;i<m.count;i++)pos.push(m.p[3*i],m.base,m.p[3*i+2]);
 const edge=[];for(let x=0;x<=m.nx;x++)edge.push(x);for(let z=1;z<=m.nz;z++)edge.push(z*(m.nx+1)+m.nx);for(let x=m.nx-1;x>=0;x--)edge.push(m.nz*(m.nx+1)+x);for(let z=m.nz-1;z>0;z--)edge.push(z*(m.nx+1));
 for(let i=0;i<edge.length;i++){const a=edge[i],b=edge[(i+1)%edge.length];tris.push(a,b,a+m.count,b,b+m.count,a+m.count);}
 for(let i=0;i<m.triangles.length;i+=3)tris.push(m.triangles[i]+m.count,m.triangles[i+2]+m.count,m.triangles[i+1]+m.count);
 return dynamicGeometry(pos,tris);
}
function setView(kind){cameraView=kind;const b=sim.bed;if(kind==='top')camera.position.set(.01,4.9,.0);else if(kind==='side')camera.position.set(3.9,1.0,.05);else camera.position.set(2.85,2.15,3.05);camera.lookAt(0,.38,0);camera.updateProjectionMatrix();}
$('size').value=study.size;$('size').disabled=true;
$('frame-name').textContent=study.name+' · '+study.frame_id;
function reset(){
 if(group){scene.remove(group);group.traverse(o=>{o.geometry?.dispose();if(o.material)for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();});}
 sim=new BeddingSimulation({size:$('size').value,frameParts:study.parts});group=new THREE.Group();scene.add(group);frames=0;
 const b=sim.bed;if(b.width!==study.interface.width||b.length!==study.interface.length||Math.abs(b.base-study.interface.base_y)>1e-9)throw Error('Saved frame and support do not match');mattress=mesh(supportedShell(sim.mattress),new THREE.MeshStandardMaterial({color:0xa5a99a,roughness:.96,side:THREE.DoubleSide}));mattress.frustumCulled=false;loadArrow=new THREE.ArrowHelper(new THREE.Vector3(0,-1,0),new THREE.Vector3(0,1.2,.2),.28,0xeabd54,.075,.04);group.add(loadArrow);
 for(const part of study.parts){const g=dynamicGeometry(part.mesh.vertices.flat(),part.mesh.indices);g.setAttribute('normal',new THREE.Float32BufferAttribute(part.mesh.normals.flat(),3));const beam=mesh(g,new THREE.MeshStandardMaterial({color:0x897052,roughness:.85}));beam.position.set(...part.position);beam.name=part.id;}
 const cg=dynamicGeometry(sim.cloth.p,sim.cloth.triangles),colors=[];
 for(let z=0;z<=sim.cloth.nz;z++)for(let x=0;x<=sim.cloth.nx;x++){const tone=(z%7===0||x%6===0)?1:.84;colors.push(.045*tone,.25*tone,.72*tone);}
 cg.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));cloth=mesh(cg,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.93,side:THREE.DoubleSide}));cloth.frustumCulled=false;
 // Closed original display shell: dynamic top, fixed supported bottom, deforming side quads.
 const p=sim.pillow,pos=Array.from(p.p),tris=p.triangles.slice();for(let i=0;i<p.count;i++)pos.push(p.p[3*i],p.base,p.p[3*i+2]);
 const edge=[];for(let x=0;x<=p.nx;x++)edge.push(x);for(let z=1;z<=p.nz;z++)edge.push(z*(p.nx+1)+p.nx);for(let x=p.nx-1;x>=0;x--)edge.push(p.nz*(p.nx+1)+x);for(let z=p.nz-1;z>0;z--)edge.push(z*(p.nx+1));
 for(let i=0;i<edge.length;i++){const a=edge[i],bb=edge[(i+1)%edge.length];tris.push(a,bb,a+p.count,bb,bb+p.count,a+p.count);}
 for(let i=0;i<p.triangles.length;i+=3)tris.push(p.triangles[i]+p.count,p.triangles[i+2]+p.count,p.triangles[i+1]+p.count);
 pillow=mesh(dynamicGeometry(pos,tris),new THREE.MeshStandardMaterial({color:0xe1d8bd,roughness:1,side:THREE.DoubleSide}));pillow.frustumCulled=false;
 head=mesh(new THREE.SphereGeometry(sim.head.radius,32,24),new THREE.MeshStandardMaterial({color:0xc78250,roughness:.55,transparent:true,opacity:.88}));
 $('across').disabled=true;$('loadsite').disabled=false;$('showcloth').checked=true;paused=true;runUntilFrame=0;batchStartedAt=0;$('pause').textContent='Run 12 frames';$('status').textContent='Paused disposable019 preview. Up to 120 actual solver frames; no saved world is changed.';setView(cameraView);updateMeshes();
}
function updateMeshes(){
 cloth.geometry.attributes.position.array.set(sim.cloth.p);cloth.geometry.attributes.position.needsUpdate=true;cloth.geometry.computeVertexNormals();
 const p=sim.pillow,pa=pillow.geometry.attributes.position.array;pa.set(p.p,0);for(let i=0;i<p.count;i++)pa[3*(i+p.count)+1]=p.support[i];pillow.geometry.attributes.position.needsUpdate=true;pillow.geometry.computeVertexNormals();
 mattress.geometry.attributes.position.array.set(sim.mattress.p,0);mattress.geometry.attributes.position.needsUpdate=true;mattress.geometry.computeVertexNormals();
 head.position.set(sim.head.x,sim.head.y,sim.head.z);loadArrow.visible=sim.mattress.load.newtons>.01;loadArrow.position.set(sim.mattress.load.x,1.2,sim.mattress.load.z);
}

function showMetrics(){const m=sim.metrics();$('indent').textContent=(m.pillow_center_indentation_m*1000).toFixed(1)+' mm';$('motion').textContent=m.cloth_rms_speed_mps.toFixed(3)+' m/s';$('stretch').textContent=(m.maximum_stretch_fraction*100).toFixed(1)+'%';$('frameoverlap').textContent=String(m.frame_contact.intersecting_triangle_part_pairs);$('time').textContent=m.time_s.toFixed(1)+' s';if(!m.finite){paused=true;$('status').textContent='Stopped: non-finite state. Reset required.';}$('compression').textContent=(m.mattress_max_compression_m*1000).toFixed(1)+' mm';$('loadforce').textContent=m.mattress_load_newtons.toFixed(0)+' N';$('loadsite').disabled=m.mattress_load_newtons>.01||sim.mattress.load.target>0;updateHUD(m);window.beddingReview={frame_id:study.frame_id,frame_parts:study.parts.length,metrics:m,limitations:LIMITATIONS,frames,paused,last_step_ms:lastFrameMs,blanket_visible:cloth.visible};}
function command(fn,message){try{fn();$('status').textContent=message;}catch(e){$('status').textContent=e.message;}}
$('load').onclick=()=>command(()=>sim.setHead({site:'pillow',loaded:true}),'The head lowers continuously; the pillow yields locally.');
$('lift').onclick=()=>command(()=>sim.setHead({loaded:false}),'The head lifts; the elastic surface recovers over time.');
$('overblanket').onclick=()=>command(()=>sim.setHead({site:'blanket',loaded:true}),'The head lifts clear before moving to the blanket.');
$('grab').onclick=()=>command(()=>{sim.grabCorner();$('across').disabled=false;},'A single held corner lifts the connected cloth mesh.');
$('release').onclick=()=>command(()=>{sim.releaseGrab();$('across').disabled=true;},'The same cloth mesh is released to gravity.');
$('across').onclick=()=>command(()=>sim.moveGrabAcross(),'The held corner moves across. Self-collision is not implemented.');
$('mattressload').onclick=()=>command(()=>sim.setMattressLoad({loaded:true,site:$('loadsite').value,force:220}),'Authored 220 N test load ramps onto this mattress region.');
$('mattressunload').onclick=()=>command(()=>sim.setMattressLoad({loaded:false}),'External mattress load ramps down; the support recovers.');
$('showcloth').onchange=()=>{cloth.visible=$('showcloth').checked;$('status').textContent=cloth.visible?'Blue blanket visible; physics uses the displayed vertices.':'Blanket hidden for mattress inspection; cloth physics stays active.';showMetrics();};
$('pause').onclick=()=>{if(!paused){paused=true;$('pause').textContent='Run 12 frames';return;}if(frames>=120){$('status').textContent='120-frame review limit reached. Preserve this result.';return;}runUntilFrame=Math.min(frames+12,120);batchStartedAt=performance.now();paused=false;$('pause').textContent='Pause';};$('reset').onclick=reset;$('size').onchange=reset;
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>setView(b.dataset.view);
document.addEventListener("click",()=>{displayDirty=true;});document.addEventListener("change",()=>{displayDirty=true;});
new ResizeObserver(()=>{displayDirty=true;const r=view.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}).observe(view);
reset();$('record').disabled=true;$('stop').disabled=true;$('record-status').textContent='Read-only review: recording and saving are disabled.';let last=performance.now(),accumulator=0;
function animate(now){requestAnimationFrame(animate);if(paused&&!displayDirty){last=now;accumulator=0;return;}displayDirty=false;const elapsed=Math.min((now-last)/1000,.08);last=now;if(!paused){accumulator+=elapsed;let count=0;while(accumulator>=sim.fixedDt&&count<3){const start=performance.now();sim.step();lastFrameMs=performance.now()-start;accumulator-=sim.fixedDt;frames++;count++;if(frames>=runUntilFrame||performance.now()-batchStartedAt>15000){paused=true;$('pause').textContent='Run 12 frames';$('status').textContent='Paused after actual solver frame '+frames+'. No world or owner study has been saved.';break;}}if(count===3)accumulator=0;updateMeshes();}else accumulator=0;if(frames%6===0||paused)showMetrics();renderer.render(scene,camera);}
requestAnimationFrame(animate);
