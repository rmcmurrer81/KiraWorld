// Original fictional latch/contact artwork. This component has NO door, pressure,
// collision, package-admission, or simulated-seal-acknowledgement authority.
const need=(v,m)=>{if(!v)throw new TypeError(m);};
const finite3=v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite);
const frozen=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(frozen);Object.freeze(v);}return v;};
const exact=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const box=(center,size)=>({min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)});

export function describeLatchVisual(plan){
 need(plan?.contract==='authored_pressure_hatch_geometry_v1'&&['x','z'].includes(plan.axis)&&[-1,1].includes(plan.normalSign),'Unsupported authored hatch');
 need(finite3(plan.origin)&&finite3(plan.hinge)&&finite3(plan.hingeLocal)&&Number.isFinite(plan.openAngle)&&Math.abs(Math.abs(plan.openAngle)-Math.PI/2)<1e-9,'Invalid hatch basis');
 need(plan.capabilities?.latchState==='static_retracted'&&plan.capabilities.latchSimulation===false,'Expected unchanged static hatch source');
 const part=(list,suffix)=>{const a=list.filter(p=>p.id===`hatch_${plan.portalId}_${suffix}`);need(a.length===1,'Missing unique hatch part: '+suffix);return structuredClone(a[0]);};
 const solids=p=>{need(p.shape==='box'&&finite3(p.center)&&finite3(p.size)&&p.size.every(v=>v>0),'Invalid box part');return p;};
 const gasket=part(plan.fixed,'continuous_gasket');
 need(gasket.shape==='ring'&&finite3(gasket.center)&&finite3(gasket.size)&&gasket.size[2]>0,'Invalid gasket');
 for(const profile of [gasket.outer,gasket.inner])need(profile&&['width','bottom','top','radius'].every(k=>Number.isFinite(profile[k]))&&profile.width>2*profile.radius&&profile.top-profile.bottom>profile.radius&&profile.radius>0,'Invalid gasket contour');
 need(gasket.outer.width>gasket.inner.width&&gasket.outer.bottom<gasket.inner.bottom&&gasket.outer.top>gasket.inner.top,'Invalid gasket ring');
 const leaf=part(plan.moving,'reinforced_leaf');
 need(finite3(leaf.center)&&finite3(leaf.size),'Invalid leaf contact plane');
 const contact=plan.hingeLocal[2]+leaf.center[2]-leaf.size[2]/2;
 need(Math.abs(contact-(gasket.center[2]+gasket.size[2]/2))<1e-9,'Gasket contact does not meet the original closed leaf');
 const dogs=plan.moving.filter(p=>p.id.startsWith(`hatch_${plan.portalId}_retracted_dog_`));
 need(dogs.length===3,'Expected exactly three authored dogs');
 const mechanisms=dogs.map(raw=>{
  const dog=solids(structuredClone(raw)),suffix=dog.id.split('_retracted_dog_')[1];
  const housing=solids(part(plan.moving,'dog_housing_'+suffix)),keeper=solids(part(plan.fixed,'keeper_'+suffix)),support=solids(part(plan.fixed,'keeper_support_'+suffix));
  need(Math.abs(dog.center[1]-keeper.center[1])<1e-9&&Math.abs(plan.hingeLocal[2]+dog.center[2]-keeper.center[2])<1e-9,'Dog and keeper do not align');
  need(keeper.size[1]>dog.size[1]+.004&&keeper.size[2]>dog.size[2]+.002,'Keeper aperture too small');
  const initialTip=plan.hingeLocal[0]+dog.center[0]+dog.size[0]/2,keeperFace=keeper.center[0]-keeper.size[0]/2;
  const stroke=keeperFace+Math.min(.015,keeper.size[0]/3)-initialTip;
  need(stroke>.01&&stroke<.10,'Unsupported engagement stroke');
  const supportBack=support.center[2]-support.size[2]/2,keeperBack=keeper.center[2]-keeper.size[2]/2;
  need(keeperBack>supportBack,'Invalid keeper support');
  const proposedSupport={center:[support.center[0],support.center[1],(supportBack+keeperBack)/2],size:[support.size[0],support.size[1],keeperBack-supportBack]};
  // A telescoping bolt has the source dog's same retracted tip. The longer tail
  // stays behind its housing. At full stroke the tip enters a hollow keeper.
  const boltSize=[dog.size[0]+stroke,dog.size[1],dog.size[2]],boltCenter=[dog.center[0]-stroke/2,dog.center[1],dog.center[2]];
  return {id:dog.id,dog,housing,keeper,support,proposedSupport,stroke,boltSize,boltCenter,
   retractedBounds:box(boltCenter,boltSize),engagedBounds:box([boltCenter[0]+stroke,boltCenter[1],boltCenter[2]],boltSize)};
 });
 const wheels=[-1,1].map(face=>{
  const p=part(plan.moving,'control_wheel_'+face);
  need(p.shape==='wheel'&&finite3(p.center)&&p.radius>0&&p.tube>0,'Invalid control wheel');return p;
 });
 return frozen({contract:'fictional_latch_contact_visual_v1',portalId:plan.portalId,axis:plan.axis,normalSign:plan.normalSign,
  origin:[...plan.origin],hinge:[...plan.hinge],openAngle:plan.openAngle,gasket,contact,mechanisms,wheels,
  requiresNewColliderAndMetadataReview:true,pressureProof:false,modifiesSourcePackage:false});
}

function contour(THREE,p){
 const s=new THREE.Shape(),r=p.radius;
 s.moveTo(-p.width/2,p.bottom);s.lineTo(p.width/2,p.bottom);s.lineTo(p.width/2,p.top-r);
 s.absarc(p.width/2-r,p.top-r,r,0,Math.PI/2,false);s.lineTo(-p.width/2+r,p.top);
 s.absarc(-p.width/2+r,p.top-r,r,Math.PI/2,Math.PI,false);s.closePath();return s;
}

export function createLatchVisual({THREE,plan,doorId,runtimeIdentity,readDoor,isCurrent}){
 const recipe=describeLatchVisual(plan);
 need(typeof doorId==='string'&&doorId.length>0&&runtimeIdentity&&typeof readDoor==='function'&&typeof isCurrent==='function','An exact host identity and door observation are required');
 const root=new THREE.Group(),fixed=new THREE.Group(),moving=new THREE.Group();
 root.name='fictional-latch-contact:'+doorId;root.userData={fictionalLatchVisual:true,pressureProof:false};root.add(fixed,moving);
 const geometries=new Set(),materials=new Set(),bolts=[],wheelGroups=[];
 let disposed=false,epoch=0,fraction=0,target=0,fault=null,observation=null;
 const holds=new Set();
 const geometry=g=>(geometries.add(g),g);
 const material=options=>{const m=new THREE.MeshStandardMaterial(options);materials.add(m);return m;};
 function clean(){for(const g of geometries)g.dispose();for(const m of materials)m.dispose();root.removeFromParent();root.clear();}
 try{
  const metal=material({color:0xb9bbb5,roughness:.42,metalness:.58}),structure=material({color:0x3d4b50,roughness:.55,metalness:.42});
  const control=material({color:0xb77d39,roughness:.5,metalness:.3}),rubber=material({color:0x161d1f,roughness:.92,metalness:0});
  function mesh(g,m,parent,name,center=[0,0,0]){const o=new THREE.Mesh(geometry(g),m);o.name=name;o.position.set(...center);parent.add(o);return o;}
  const makeBox=(p,m,parent,name)=>mesh(new THREE.BoxGeometry(...p.size),m,parent,name,p.center);
  for(const d of recipe.mechanisms){
   makeBox(d.housing,structure,moving,d.id+':housing');makeBox(d.proposedSupport,structure,fixed,d.id+':support');
   const bolt=makeBox({size:d.boltSize,center:d.boltCenter},metal,moving,d.id+':bolt');bolts.push([bolt,d]);
   // Four bars leave a real opening along the bolt's travel axis. Their outer
   // envelope matches the original solid keeper; no painted-on aperture.
   const k=d.keeper,innerY=d.dog.size[1]+.004,innerZ=d.dog.size[2]+.002;
   for(const sign of [-1,1]){
    makeBox({center:[k.center[0],k.center[1]+sign*(k.size[1]+innerY)/4,k.center[2]],size:[k.size[0],(k.size[1]-innerY)/2,k.size[2]]},metal,fixed,d.id+':keeper-y:'+sign);
    makeBox({center:[k.center[0],k.center[1],k.center[2]+sign*(k.size[2]+innerZ)/4],size:[k.size[0],innerY,(k.size[2]-innerZ)/2]},metal,fixed,d.id+':keeper-z:'+sign);
   }
  }
  for(const w of recipe.wheels){
   const g=new THREE.Group();g.position.set(...w.center);moving.add(g);wheelGroups.push(g);
   mesh(new THREE.TorusGeometry(w.radius,w.tube,8,32),control,g,w.id+':rim');
   mesh(new THREE.BoxGeometry(w.radius*1.7,.012,.012),metal,g,w.id+':cross-x');
   mesh(new THREE.BoxGeometry(.012,w.radius*1.7,.012),metal,g,w.id+':cross-y');
  }
  const shape=contour(THREE,recipe.gasket.outer);shape.holes.push(contour(THREE,recipe.gasket.inner));
  const gasket=mesh(new THREE.ExtrudeGeometry(shape,{depth:1,bevelEnabled:false,curveSegments:16}),rubber,fixed,'fictional-gasket-contact');
  // Original proposed contact motion, not a material/pressure calculation.
  const gasketBack=recipe.gasket.center[2]-recipe.gasket.size[2]/2;
  gasket.position.z=gasketBack;
  const basis=new THREE.Matrix4();
  if(recipe.axis==='x')basis.set(0,0,recipe.normalSign,0,0,1,0,0,1,0,0,0,0,0,0,1);
  else basis.set(1,0,0,0,0,1,0,0,0,0,recipe.normalSign,0,0,0,0,1);
  fixed.matrixAutoUpdate=false;moving.matrixAutoUpdate=false;
  fixed.matrix.copy(basis).setPosition(...recipe.origin);
  function pose(){
   root.visible=!fault&&!disposed&&observation!==null;
   const p=fraction*fraction*(3-2*fraction);
   for(const [bolt,d] of bolts)bolt.position.x=d.boltCenter[0]+d.stroke*p;
   for(const w of wheelGroups)w.rotation.z=p*Math.PI/2;
   // Contact is approached in the final half of the visual bolt movement.
   const contactProgress=Math.max(0,(p-.5)*2);
   gasket.scale.z=recipe.gasket.size[2]*(.55+.45*contactProgress);
   moving.matrix.makeRotationY(observation?.angle??0).multiply(basis).setPosition(...recipe.hinge);
   root.updateMatrixWorld(true);
  }
  const snapshot=()=>frozen({disposed,doorId,visualState:disposed?'disposed':fault?'unavailable':fraction===target?(fraction===1?'engaged':'released'):(target===1?'engaging':'releasing'),
   fraction,target,pauseReasons:[...holds],fault,doorObservation:observation?{...observation}:null,
   fictional:true,pressureProof:false,sealAcknowledgementChanged:false});
  function fail(reason){fault=reason;fraction=target=0;observation=null;pose();return {ok:false,reason};}
  function observe(){
   if(disposed)return {ok:false,reason:'Disposed visual component'};
   const mine=epoch;let current,raw;
   try{current=isCurrent(runtimeIdentity);if(current)raw=readDoor(doorId);}
   catch{return disposed?{ok:false,reason:'Disposed visual component'}:fail('Door observation unavailable');}
   if(disposed||mine!==epoch)return {ok:false,reason:'Visual lifecycle changed during observation'};
   let stillCurrent=false;try{stillCurrent=isCurrent(runtimeIdentity);}catch{}
   if(disposed||mine!==epoch)return {ok:false,reason:'Visual lifecycle changed during observation'};
   if(!current||!stillCurrent)return fail('Loaded runtime identity changed');
   if(!raw||raw.runtimeIdentity!==runtimeIdentity||raw.id!==doorId||typeof raw.angle!=='number'||!Number.isFinite(raw.angle)||raw.angle*recipe.openAngle<0||Math.abs(raw.angle)>Math.abs(recipe.openAngle)||![0,recipe.openAngle].includes(raw.target)||typeof raw.moving!=='boolean')return fail('Invalid exact-door observation');
   const closed=raw.angle===0&&raw.target===0&&!raw.moving;
   observation={angle:raw.angle,target:raw.target,moving:raw.moving};
   if(!closed&&(fraction>0||target>0))return fail('Door left the closed stationary pose; latch artwork reset');
   pose();return {ok:true,closed};
  }
  pose();
  return Object.freeze({root,recipe,snapshot,
   syncDoor:observe,
   request(value){need(typeof value==='boolean','Engagement request must be boolean');const s=observe();if(!s.ok)return s;if(fault)return {ok:false,reason:'Reset the faulted visual component first'};if(value&&!s.closed)return {ok:false,reason:'Close and stop the door before the fictional latch pose'};target=value?1:0;return {ok:true,snapshot:snapshot()};},
   advance(seconds){need(typeof seconds==='number'&&Number.isFinite(seconds)&&seconds>=0&&seconds<=.05,'Visual step must be 0–0.05 seconds');const s=observe();if(!s.ok)return s;if(fault)return {ok:false,reason:fault};if(!holds.size&&fraction!==target){const delta=seconds/.8;fraction=target>fraction?Math.min(target,fraction+delta):Math.max(target,fraction-delta);pose();}return {ok:true,snapshot:snapshot()};},
   pause(reason){need(typeof reason==='string'&&reason.length>0,'Pause reason required');if(!disposed)holds.add(reason);return snapshot();},
   resume(reason){need(typeof reason==='string'&&reason.length>0,'Resume reason required');if(!disposed)holds.delete(reason);return snapshot();},
   reset(){if(disposed)return {ok:false,reason:'Disposed visual component'};epoch++;fraction=target=0;fault=null;observation=null;pose();return observe();},
   dispose(){if(disposed)return;disposed=true;epoch++;fraction=target=0;holds.clear();observation=null;clean();}
  });
 }catch(error){clean();throw error;}
}
