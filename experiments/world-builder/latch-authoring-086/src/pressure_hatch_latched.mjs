// Original086 authoring successor. No pressure authority or old-package admission.
import {planPressureHatch,buildPressureHatch,hatchCollidersAt,hatchSwingBounds} from './legacy/pressure_hatch.mjs';
import {describeLatchVisual,createLatchVisual} from './latch_visual.mjs';
export const LATCH_HATCH_CONTRACT='authored_pressure_hatch_latch_geometry_v2';
export const LATCH_COLLISION_POLICY='all_visual_pose_part_aabbs_and_analytic_hinge_sweep_v2';
const need=(v,m)=>{if(!v)throw new TypeError(m);};
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const box=(center,size)=>({min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)});
const union=bs=>({min:[0,1,2].map(i=>Math.min(...bs.map(b=>b.min[i]))),max:[0,1,2].map(i=>Math.max(...bs.map(b=>b.max[i])))});
const own=new WeakMap();
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const same=(a,b)=>JSON.stringify(canonical(a))===JSON.stringify(canonical(b));

export function planLatchedPressureHatch(geometry,portalId){
 const legacy=planPressureHatch(geometry,portalId);if(!legacy)return null;
 const visual=describeLatchVisual(legacy),removed=new Set([visual.gasket.id]);
 for(const m of visual.mechanisms)for(const p of [m.dog,m.housing,m.keeper,m.support])removed.add(p.id);
 for(const w of visual.wheels){removed.add(w.id);for(const p of legacy.moving)if(p.id.startsWith(`hatch_${portalId}_wheel_spoke_${w.id.endsWith('_-1')?-1:1}_`))removed.add(p.id);}
 need(removed.size===21,'Exact legacy hardware replacement requires21 parts');
 const fixed=legacy.fixed.filter(p=>!removed.has(p.id)),moving=legacy.moving.filter(p=>!removed.has(p.id));
 const retainedColliders=legacy.colliders.filter(c=>!removed.has(c.owner));
 const hardware=[],colliders=[...retainedColliders];
 function part(suffix,meshName,motion,representation,bounds,proxyParts=null){
  const id=`hatch_${portalId}_latch_v2_${suffix}`;
  hardware.push({id,meshName,motion,representation,allPoseLocalBounds:bounds});
  const pieces=proxyParts??[{id,bounds}];
  for(const p of pieces)colliders.push({id:p.id,owner:id,motion,...p.bounds});
 }
 for(const [index,m] of visual.mechanisms.entries()){
  const n=index+1;
  part(`housing_${n}`,m.id+':housing','kinematic',{shape:'box',center:m.housing.center,size:m.housing.size},box(m.housing.center,m.housing.size));
  part(`bolt_${n}`,m.id+':bolt','kinematic',{shape:'translating_box',center:m.boltCenter,size:m.boltSize,axis:[1,0,0],stroke:m.stroke,progress:'smoothstep(fraction)'},union([m.retractedBounds,m.engagedBounds]));
  const s=m.proposedSupport;part(`support_${n}`,m.id+':support','static',{shape:'box',...s},box(s.center,s.size));
  const k=m.keeper,iy=m.dog.size[1]+.004,iz=m.dog.size[2]+.002;
  for(const sign of [-1,1]){
   const yc=[k.center[0],k.center[1]+sign*(k.size[1]+iy)/4,k.center[2]],ys=[k.size[0],(k.size[1]-iy)/2,k.size[2]];
   part(`keeper_${n}_y_${sign}`,m.id+':keeper-y:'+sign,'static',{shape:'box',center:yc,size:ys},box(yc,ys));
   const zc=[k.center[0],k.center[1],k.center[2]+sign*(k.size[2]+iz)/4],zs=[k.size[0],iy,(k.size[2]-iz)/2];
   part(`keeper_${n}_z_${sign}`,m.id+':keeper-z:'+sign,'static',{shape:'box',center:zc,size:zs},box(zc,zs));
  }
 }
 for(const [index,w] of visual.wheels.entries()){
  const n=index+1,r=w.radius+w.tube;
  part(`wheel_${n}_rim`,w.id+':rim','kinematic',{shape:'rotating_torus',center:w.center,radius:w.radius,tube:w.tube,axis:[0,0,1],angle:[0,Math.PI/2]},box(w.center,[2*r,2*r,2*w.tube]));
  const extent=Math.hypot(w.radius*.85,.006);
  for(const axis of ['x','y'])part(`wheel_${n}_cross_${axis}`,w.id+':cross-'+axis,'kinematic',
   {shape:'rotating_box',center:w.center,size:axis==='x'?[w.radius*1.7,.012,.012]:[.012,w.radius*1.7,.012],axis:[0,0,1],angle:[0,Math.PI/2]},box(w.center,[2*extent,2*extent,.012]));
 }
 const gasketParts=legacy.colliders.filter(c=>c.owner===visual.gasket.id).map((c,i)=>({id:`hatch_${portalId}_latch_v2_gasket_${i}`,bounds:{min:c.min,max:c.max}}));
 part('gasket','fictional-gasket-contact','static',{shape:'variable_depth_ring',outer:visual.gasket.outer,inner:visual.gasket.inner,
  back:visual.gasket.center[2]-visual.gasket.size[2]/2,depth:[visual.gasket.size[2]*.55,visual.gasket.size[2]],contactPlane:visual.contact},union(gasketParts.map(p=>p.bounds)),gasketParts);
 const retainedPlan={...legacy,fixed,moving,colliders:retainedColliders};
 const colliderPlan={...legacy,colliders};
 const parts=[...fixed.map(p=>({id:p.id,motion:'static',representation:p})),...moving.map(p=>({id:p.id,motion:'kinematic',representation:p})),...hardware];
 need(new Set(parts.map(p=>p.id)).size===parts.length,'Duplicate part ownership');
 need(new Set(colliders.map(c=>c.id)).size===colliders.length,'Duplicate collider ownership');
 const plan=freeze({contract:LATCH_HATCH_CONTRACT,id:legacy.id,portalId,axis:legacy.axis,normalSign:legacy.normalSign,origin:legacy.origin,
  hinge:legacy.hinge,hingeLocal:legacy.hingeLocal,openAngle:legacy.openAngle,aperture:legacy.aperture,leafWidth:legacy.leafWidth,leafHeight:legacy.leafHeight,
  localLeafCenter:legacy.localLeafCenter,retained:{fixed,moving},replacedPartIds:[...removed].sort(),hardware,parts,colliders,
  collisionPolicy:LATCH_COLLISION_POLICY,swingBounds:hatchSwingBounds(colliderPlan),limits:legacy.limits,
  visual:{contract:visual.contract,initialState:'released',fraction:[0,1],durationSeconds:.8,maxStepSeconds:.05,hingeMovementRequiresReleased:true},
  capabilities:{pressureSimulation:false,sealCertification:false,latchVisual:true,physicalLatchSimulation:false,sealAcknowledgementAuthority:false},
  provenance:{originalAuthoredGeometry:true,legacyContract:legacy.contract,visualContract:visual.contract,legacyPartsReplaced:true,installed:false,packageAdmission:false}});
 own.set(plan,{legacy,visual,retainedPlan,colliderPlan});return plan;
}

const owned=plan=>{const data=own.get(plan);need(data&&plan.contract===LATCH_HATCH_CONTRACT,'Expected exact locally authored086 plan');return data;};
export function latchHatchCollidersAt(plan,angle=0){return hatchCollidersAt(owned(plan).colliderPlan,angle);}
export function validateLatchedHatchPlan(plan,geometry,portalId){
 const expected=planLatchedPressureHatch(geometry,portalId);need(expected&&same(plan,expected),'Latched hatch plan differs from exact086 authoring recipe');return expected;
}
// Export-ready records, not an admitted complete world package. A new producer
// must bind this source and adapt its node hierarchy and strict consumer first.
export function describeLatchedHatchAuthoring(plan){
 owned(plan);const initial=latchHatchCollidersAt(plan,0);
 return freeze({contract:'latched_hatch_authoring_metadata_v2',variant:plan.contract,portalId:plan.portalId,collisionPolicy:plan.collisionPolicy,
  initialVisualState:'released',pressureSimulation:false,sealAcknowledgementAuthority:false,hinge:plan.hinge,openAngle:plan.openAngle,
  parts:plan.parts.map(p=>({id:p.id,motion:p.motion,representation:structuredClone(p.representation),
   colliderIds:initial.filter(c=>c.owner===p.id).map(c=>c.id),allPoseBounds:union(initial.filter(c=>c.owner===p.id))})),
  colliders:initial,swingBounds:plan.swingBounds,visual:plan.visual,replacedPartIds:plan.replacedPartIds,
  requiresNewProducerAndConsumer:true,completeWorldPackage:false});
}

export function buildLatchedPressureHatch({THREE,plan,doorId,runtimeIdentity,readDoor,isCurrent}){
 const data=owned(plan),root=new THREE.Group();root.name=plan.id+'_v2_assembly';
 let legacy=null,visual=null,disposed=false;
 const meshes=new Map(),legacyMaterials=new Set();
 function dispose(){
  if(disposed)return;disposed=true;visual?.dispose();
  const gs=new Set(),ms=new Set(legacyMaterials);for(const o of legacy?.meshes.values()??[]){gs.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material])ms.add(m);}
  for(const g of gs)g.dispose();for(const m of ms)m.dispose();root.removeFromParent();root.clear();
 }
 try{
  const trackedThree={...THREE,MeshStandardMaterial:class extends THREE.MeshStandardMaterial {constructor(...args){super(...args);legacyMaterials.add(this);}}};
  legacy=buildPressureHatch(trackedThree,data.retainedPlan);root.add(legacy.fixed,legacy.pivot);
  visual=createLatchVisual({THREE,plan:data.legacy,doorId,runtimeIdentity,readDoor,isCurrent});root.add(visual.root);
  for(const [id,m] of legacy.meshes)meshes.set(id,m);
  for(const p of plan.hardware){const m=visual.root.getObjectByName(p.meshName);need(m?.isMesh&&!meshes.has(p.id),'Missing unique084 mesh '+p.id);meshes.set(p.id,m);}
  for(const [id,m] of meshes){const part=plan.parts.find(p=>p.id===id);m.userData={...m.userData,hatchPart:id,collisionOwner:id,
   colliderIds:plan.colliders.filter(c=>c.owner===id).map(c=>c.id),motion:part.motion,recipeContract:plan.contract,visualStateContract:plan.visual.contract};delete m.userData.latchState;}
  root.userData={recipeContract:plan.contract,pressureSimulation:false,sealAcknowledgementAuthority:false};
  function apply(result){
   const state=visual.snapshot();root.visible=!disposed&&!state.fault&&state.doorObservation!==null;
   if(!disposed&&result.ok&&state.doorObservation)legacy.setAngle(state.doorObservation.angle);
   root.updateMatrixWorld(true);return result;
  }
  root.visible=false;
  return Object.freeze({root,meshes,plan,snapshot:visual.snapshot,
   syncDoor:()=>apply(visual.syncDoor()),request:value=>apply(visual.request(value)),advance:seconds=>apply(visual.advance(seconds)),
   pause:visual.pause,resume:visual.resume,reset:()=>apply(visual.reset()),dispose});
 }catch(error){dispose();throw error;}
}
