// Original089 source-only normalization. No package admission, pressure authority,
// model, animation timer, parser or permission to dispatch a hinge command.
import {describeLatchedHatchAuthoring,buildLatchedPressureHatch} from './pressure_hatch_latched.mjs';
import {LATCH_STATE_CONTRACT} from './latch_state.mjs';
export const BINDING_CONTRACT='normalized_latched_hatch_mesh_binding_v2';
const need=(v,m)=>{if(!v)throw new TypeError(m);};
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const canon=v=>Array.isArray(v)?v.map(canon):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canon(v[k])])):v;
const same=(a,b)=>JSON.stringify(canon(a))===JSON.stringify(canon(b));
const close=(a,b)=>a.length===b.length&&a.every((v,i)=>Number.isFinite(v)&&Math.abs(v-b[i])<2e-6);
const local=(plan,v)=>plan.axis==='x'?[plan.normalSign*v[2],v[1],v[0]]:[v[0],v[1],plan.normalSign*v[2]];
const determinant=plan=>plan.axis==='x'?-plan.normalSign:plan.normalSign;

export function describeNormalizedArticulation(plan){
 describeLatchedHatchAuthoring(plan); // Accept only exact locally authored086 plans.
 const parts=plan.parts.map(p=>{
  const r=p.representation,parent=p.motion==='static'?'fixed':'hinge';let articulation=null;
  if(r.shape==='translating_box')articulation={kind:'bolt_translation',axis:local(plan,r.axis),stroke:r.stroke};
  if(r.shape==='rotating_torus'||r.shape==='rotating_box')articulation={kind:'wheel_rotation',center:local(plan,r.center),axis:local(plan,r.axis).map(x=>x*determinant(plan)),angle:r.angle};
  if(r.shape==='variable_depth_ring')articulation={kind:'gasket_depth',axis:local(plan,[0,0,1]),anchor:local(plan,[0,0,r.back]),depth:r.depth};
  return {id:p.id,parent,motion:p.motion,articulation};
 });
 need(parts.filter(p=>p.articulation?.kind==='bolt_translation').length===3&&parts.filter(p=>p.articulation?.kind==='wheel_rotation').length===6&&parts.filter(p=>p.articulation?.kind==='gasket_depth').length===1,'Exact hardware articulation required');
 return freeze({contract:BINDING_CONTRACT,portalId:plan.portalId,variant:plan.contract,initialState:'released',initialMeshMatrix:'identity',fixedPosition:[...plan.origin],hingePosition:[...plan.hinge],openAngle:plan.openAngle,parts,collisionPolicy:plan.collisionPolicy,pressureSimulation:false,packageAdmission:false});
}

// Matrix4.applyMatrix4 transforms normals by inverse transpose. Negative bases
// must additionally reverse every triangle to preserve front-face orientation.
export function bakeGeometry(THREE,source,matrix){
 need(source?.isBufferGeometry&&matrix?.isMatrix4&&matrix.elements.every(Number.isFinite)&&Math.abs(matrix.determinant())>1e-12,'Finite nonsingular mesh bake required');
 const g=new THREE.BufferGeometry().copy(source);g.applyMatrix4(matrix);
 if(matrix.determinant()<0){
  if(g.index){for(let i=0;i<g.index.count;i+=3){const b=g.index.getX(i+1);g.index.setX(i+1,g.index.getX(i+2));g.index.setX(i+2,b);}}
  else for(const a of Object.values(g.attributes)){need(!a.isInterleavedBufferAttribute&&a.count%3===0,'Plain triangle attributes required');for(let i=0;i<a.count;i+=3)for(let k=0;k<a.itemSize;k++){const b=(i+1)*a.itemSize+k,c=(i+2)*a.itemSize+k,v=a.array[b];a.array[b]=a.array[c];a.array[c]=v;}}
 }
 // Parametric subclass JSON serializers otherwise reconstruct the unbaked
 // Box/Torus/Extrude parameters and silently lose baked vertices on round-trip.
 delete g.parameters;g.type='BufferGeometry';g.computeBoundingBox();g.computeBoundingSphere();return g;
}

function releasedTree(THREE,plan){
 const descriptor=describeNormalizedArticulation(plan),doorId='construction:'+plan.portalId,identity={};
 const reference=buildLatchedPressureHatch({THREE,plan,doorId,runtimeIdentity:identity,readDoor:()=>({runtimeIdentity:identity,id:doorId,angle:0,target:0,moving:false}),isCurrent:i=>i===identity});
 const root=new THREE.Group(),fixed=new THREE.Group(),hinge=new THREE.Group(),meshes=new Map(),materials=new Map();
 root.name=plan.id+'_normalized';fixed.name=plan.id+'_fixed_normalized';hinge.name=plan.id+'_hinge_normalized';
 root.add(fixed,hinge);fixed.position.set(...plan.origin);hinge.position.set(...plan.hinge);root.userData={normalizedHatch:descriptor};
 try{
  need(reference.syncDoor().ok,'Construction reference could not observe its closed released pose');reference.root.updateMatrixWorld(true);root.updateMatrixWorld(true);
  for(const p of descriptor.parts){
   const original=reference.meshes.get(p.id),parent=p.parent==='fixed'?fixed:hinge;
   need(original?.isMesh&&!Array.isArray(original.material)&&!original.geometry.morphAttributes?.position,'One ordinary mesh per authored part required');
   const relative=new THREE.Matrix4().copy(parent.matrixWorld).invert().multiply(original.matrixWorld);
   if(!materials.has(original.material))materials.set(original.material,original.material.clone());
   const m=new THREE.Mesh(bakeGeometry(THREE,original.geometry,relative),materials.get(original.material));m.name=p.id;
   m.userData=structuredClone(original.userData);m.userData.normalizedPart=p.id;m.castShadow=original.castShadow;m.receiveShadow=original.receiveShadow;
   parent.add(m);meshes.set(p.id,m);
  }root.updateMatrixWorld(true);return {root,fixed,hinge,meshes,descriptor};
 }catch(error){disposeTree(root,materials.values());throw error;}finally{reference.dispose();}
}
function disposeTree(root,extraMaterials=[]){const gs=new Set(),ms=new Set(extraMaterials);root.traverse(o=>{if(o.isMesh){gs.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material])ms.add(m);}});for(const g of gs)g.dispose();for(const m of ms)m.dispose();root.removeFromParent();root.clear();}
function identity(o){return close(o.position.toArray(),[0,0,0])&&close(o.quaternion.toArray(),[0,0,0,1])&&close(o.scale.toArray(),[1,1,1])&&close(o.matrix.elements,new o.matrix.constructor().elements);}
function sameGeometry(actual,expected){
 need(actual?.isBufferGeometry&&same(Object.keys(actual.attributes).sort(),Object.keys(expected.attributes).sort())&&same(actual.groups,expected.groups),'Geometry attribute/group closure differs');
 need(!Object.keys(actual.morphAttributes).length&&!Object.keys(expected.morphAttributes).length,'Morph geometry is unsupported');
 for(const [name,e] of Object.entries(expected.attributes)){
  const a=actual.attributes[name];need(!a.isInterleavedBufferAttribute&&a.itemSize===e.itemSize&&a.count===e.count&&a.normalized===e.normalized&&close(Array.from(a.array),Array.from(e.array)),'Baked geometry differs: '+name);
 }
 need(Boolean(actual.index)===Boolean(expected.index)&&(!actual.index||same(Array.from(actual.index.array),Array.from(expected.index.array))),'Baked triangle winding differs');
}

// Strict in-memory binding against regenerated authored geometry. This is not
// the portable package loader and never changes its two exact admitted hashes.
export function bindNormalizedHatch({THREE,root,plan,doorId,isCurrent}){
 need(root?.isGroup&&typeof doorId==='string'&&doorId.length>0&&typeof isCurrent==='function','Exact isolated scene and current-session callback required');
 const descriptor=describeNormalizedArticulation(plan);need(same(root.userData.normalizedHatch,descriptor),'Articulation descriptor differs from exact recipe');
 root.updateMatrixWorld(true);need(identity(root)&&root.children.length===2,'Normalized root transform/hierarchy differs');
 const fixed=root.children.find(o=>o.name===plan.id+'_fixed_normalized'),hinge=root.children.find(o=>o.name===plan.id+'_hinge_normalized');
 need(fixed?.isGroup&&hinge?.isGroup&&close(fixed.position.toArray(),plan.origin)&&close(hinge.position.toArray(),plan.hinge)&&[fixed,hinge].every(o=>close(o.quaternion.toArray(),[0,0,0,1])&&close(o.scale.toArray(),[1,1,1])),'Exact fixed/hinge parent frames required');
 const expected=releasedTree(THREE,plan),meshes=new Map();
 try{
  need(fixed.children.length+hinge.children.length===descriptor.parts.length,'Extra or missing authored part');
  for(const p of descriptor.parts){
   const parent=p.parent==='fixed'?fixed:hinge,found=parent.children.filter(o=>o.name===p.id);need(found.length===1,'Missing/duplicate direct parent part: '+p.id);
   const m=found[0],ref=expected.meshes.get(p.id);need(m.isMesh&&m.children.length===0&&identity(m)&&same(m.userData,ref.userData),'Part initial ownership/transform differs');sameGeometry(m.geometry,ref.geometry);meshes.set(p.id,m);
  }
 }finally{disposeTree(expected.root);}
 let retired=false,disposed=false,applying=false;root.visible=false;
 const fail=reason=>{retired=true;root.visible=false;return {ok:false,reason};};
 const apply=(snapshot,pose)=>{
  if(disposed||retired)return {ok:false,reason:'Retired mesh binding'};
  let current=false;try{current=isCurrent()===true;}catch{}if(!current)return fail('Mesh session is no longer current');
  if(disposed||retired)return {ok:false,reason:'Mesh lifecycle changed during observation'};
  const f=snapshot?.fraction,t=snapshot?.target,state=snapshot?.state;
  if(snapshot?.contract!==LATCH_STATE_CONTRACT||snapshot.id!==doorId||snapshot.fault!==null||!Number.isFinite(f)||f<0||f>1||![0,1].includes(t)||typeof snapshot.paused!=='boolean'||state!==(f===t?(f===0?'released':'engaged'):(t===1?'engaging':'releasing')))return fail('Invalid exact latch snapshot');
  if(pose?.id!==doorId||!Number.isFinite(pose.angle)||pose.angle*plan.openAngle<0||Math.abs(pose.angle)>Math.abs(plan.openAngle)||![0,plan.openAngle].includes(pose.target)||typeof pose.moving!=='boolean'||typeof pose.motionHeld!=='boolean')return fail('Invalid exact hinge observation');
  const closed=pose.angle===0&&pose.target===0&&!pose.moving&&!pose.motionHeld;
  if(!closed&&(f!==0||t!==0))return fail('Leaf motion requires released stopped hardware');
  const progress=f*f*(3-2*f),commands=[];
  for(const p of descriptor.parts){const a=p.articulation,m=new THREE.Matrix4();
   if(a?.kind==='bolt_translation')m.makeTranslation(...a.axis.map(v=>v*a.stroke*progress));
   if(a?.kind==='wheel_rotation'){const c=new THREE.Vector3(...a.center);m.makeTranslation(...c.toArray()).multiply(new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(...a.axis),a.angle[1]*progress)).multiply(new THREE.Matrix4().makeTranslation(...c.multiplyScalar(-1).toArray()));}
   if(a?.kind==='gasket_depth'){
    const ratio=(a.depth[0]+(a.depth[1]-a.depth[0])*Math.max(0,(progress-.5)*2))/a.depth[0],x=a.anchor;
    const k=ratio-1,e=m.elements;for(let row=0;row<3;row++)for(let col=0;col<3;col++)e[col*4+row]=(row===col?1:0)+k*a.axis[row]*a.axis[col];
    const shift=new THREE.Vector3(...x).sub(new THREE.Vector3(...x).applyMatrix4(m));m.setPosition(shift);
   }commands.push([meshes.get(p.id),m]);
  }
  // One atomic rendering application; no elapsed-time argument or second clock.
  for(const [mesh,matrix] of commands){mesh.matrixAutoUpdate=false;mesh.matrix.copy(matrix);}
  hinge.rotation.y=pose.angle;root.updateMatrixWorld(true);root.visible=true;return {ok:true};
 };
 return Object.freeze({root,meshes,descriptor,apply(snapshot,pose){
  if(applying)return fail('Reentrant mesh application');applying=true;try{return apply(snapshot,pose);}finally{applying=false;}
 },dispose(){if(!disposed){disposed=true;retired=true;disposeTree(root);}}});
}
export function buildNormalizedHatch({THREE,plan,doorId,isCurrent}){
 const built=releasedTree(THREE,plan);try{return bindNormalizedHatch({THREE,root:built.root,plan,doorId,isCurrent});}catch(error){disposeTree(built.root);throw error;}
}
