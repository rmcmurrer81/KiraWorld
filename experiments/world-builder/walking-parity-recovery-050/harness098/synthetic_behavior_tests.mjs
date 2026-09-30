// SOURCE ONLY. No automatic invocation, component import, saved data or I/O.
// Root must separately review and bind the real factories before any execution.
const need=(ok,message)=>{if(!ok)throw new Error(message);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};

function fixture(kind='clear'){
 const rooms=Array.from({length:5},(_,i)=>({id:'room_'+i,name:'Synthetic room '+i,x:i*4,z:0,width:4,depth:6,height:3,floor_y:0,access:'walkable_layout'}));
 const portals=Array.from({length:4},(_,i)=>({id:'portal_'+i,room_a:'room_'+i,room_b:'room_'+(i+1),axis:'x',coordinate:(i+1)*4,center:3,width:1.2,height:2.5,state:'open_passage'}));
 const obstacle={id:'probe_obstacle',min:[2.42,0,2.8],max:[2.52,1.9,3.2]};
 const primitives=kind==='base'?[{id:obstacle.id,role:'wall',primitive:'box',position:[2.47,.95,3],size:[.1,1.9,.4]}]:[];
 const objects=kind==='furniture'?[{id:obstacle.id,room_id:'room_0',kind:'console',role:'equipment',center:[2.47,.95,3],localSize:[.1,1.9,.4],yaw:0,bounds:{min:[...obstacle.min],max:[...obstacle.max]}}]:[];
 const geometry={contract:'compiled_blueprint_geometry_v1',units:'meters',rooms,portals,primitives,
  colliders:kind==='base'?[structuredClone(obstacle)]:[],support_surfaces:[{id:'synthetic_floor',min_x:0,max_x:20,min_z:0,max_z:6,y:0}],
  connectivity:{entry_room_id:'room_0'},functional_program:{},routes:[{id:'synthetic_east',avatar_radius:.34,avatar_height:1.68,points:[[2,0,3],[3,0,3]]}]};
 const dressing={contract:'authored_habitat_equipment_plan_v1',objects,architecture:[],signs:[],colliders:kind==='furniture'?[structuredClone(obstacle)]:[]};
 return freeze({geometry,dressing});
}
function yawTo(runtime,yaw){
 let remaining=yaw-runtime.snapshot().yaw;
 // Use the actual bounded look API; no direct yaw or position assignment.
 for(let i=0;i<8&&Math.abs(remaining)>1e-12;i++){const dx=Math.max(-500,Math.min(500,remaining/.002));runtime.look(dx,0);remaining=yaw-runtime.snapshot().yaw;}
 need(Math.abs(remaining)<=1e-12,'Actual bounded look failed to reach the requested synthetic orientation');
}
function deepFrozen(value){return !value||typeof value!=='object'||Object.isFrozen(value)&&Object.values(value).every(deepFrozen);}
function rows(snapshot,category){const group=snapshot.collections.find(g=>g.category===category);need(group,'Missing actual private collection '+category);return group.chunks.flat();}
function immutability(runtime){
 const a=runtime.collisionCollections(),raw=JSON.stringify(a),b=runtime.collisionCollections();
 need(a!==b&&a.collections!==b.collections&&deepFrozen(a),'Diagnostic must be a fresh deeply frozen copy');
 let refused=0;
 try{a.collections.push({category:'injected',chunks:[]});}catch{refused++;}
 const row=a.collections.flatMap(g=>g.chunks.flat())[0];need(row,'Synthetic doors supply real diagnostic colliders');
 try{row.min[0]=999999;}catch{refused++;}
 try{row.id='injected';}catch{refused++;}
 need(refused===3&&JSON.stringify(runtime.collisionCollections())===raw,'Diagnostic mutation must be refused without changing actual colliders');
}

export function runSyntheticWalkingCases({createWalkController,createDoorSystem,createRuntime,createDoorRuntime,exportSceneMetadata}){
 for(const fn of [createWalkController,createDoorSystem,createRuntime,createDoorRuntime,exportSceneMetadata])need(typeof fn==='function','Exact real factory required');
 const observations=[],owned=[];let primaryFailed=false,primaryFailure;
 function pair(kind='clear'){
  const f=fixture(kind),authorDoors=createDoorSystem(f.geometry);owned.push(authorDoors);
  const definitions=authorDoors.definitions(),metadata=exportSceneMetadata(f.geometry,f.dressing,definitions,{sceneId:'synthetic097',sourceDigests:{geometry:'0'.repeat(64),dressing_recipe:'1'.repeat(64),door_controller:'2'.repeat(64)},doorInterlocks:authorDoors.interlocks()});
  const a=createWalkController(f.geometry,{extraColliders:f.dressing.colliders});owned.push(a);
  const b=createRuntime(metadata);owned.push(b);
  return {a,b,metadata,geometry:f.geometry};
 }
 try{
  {
   const {a,b}=pair();
   for(const w of [a,b]){need(w.snapshot().nearbyDoor?.id.endsWith('portal_0'),'Initial real route yaw must face the reachable door');yawTo(w,-Math.PI/2);need(w.snapshot().nearbyDoor===null,'Facing away must clear ordinary nearby selection');
    const result=w.toggleDoor();need(result.ok===false&&result.reason==='Face a nearby door to open or close it.','Implicit facing-away command must refuse without moving');need(w.doorStates().every(d=>d.angle===0&&d.target===0&&!d.moving),'Refusal must preserve actual door state');}
   observations.push({case:'ordinary_snapshot_and_implicit_refusal',producer:a.snapshot(),consumer:b.snapshot()});
  }
  {
   const {a,b}=pair();for(const w of [a,b]){yawTo(w,-Math.PI/2);const id=w.doorStates().find(d=>d.id.endsWith('portal_0')).id;need(w.toggleDoor(id).ok===true,'Explicit nominated ID retains actual reach/sweep policy while facing away');}
   observations.push({case:'explicit_id_policy_preserved',producer:a.doorStates(),consumer:b.doorStates()});
  }
  {
   const {a,b}=pair();for(const w of [a,b]){yawTo(w,Math.PI/2+1);need(w.snapshot().nearbyDoor,'Inside the producer cone must select');yawTo(w,Math.PI/2+1.1);need(w.snapshot().nearbyDoor===null,'Outside the producer cone must refuse');yawTo(w,Math.PI/2);need(w.toggleDoor().ok===true,'In-cone implicit command must use the actual toggle guard');}
   observations.push({case:'cone_and_real_toggle',producer:a.doorStates(),consumer:b.doorStates()});
  }
  {
   const p=pair(),a=createDoorSystem(p.geometry);owned.push(a);
   const b=createDoorRuntime(p.metadata);owned.push(b);
   for(const d of [a,b]){need(d.nearest([1.75,0,3],Math.PI/2),'Exact2.25m reach must select');need(d.nearest([1.749,0,3],Math.PI/2)===null,'Beyond reach must refuse');need(d.nearest([2,0,3],-Math.PI/2)===null,'Low-level yaw filter must reject behind');need(d.nearest([2,0,3]),'Omitted yaw retains low-level proximity query');need(d.nearest([2,1,3],Math.PI/2)===null,'Wrong floor must refuse');let threw=false;try{d.nearest([2,0,3],NaN);}catch{threw=true;}need(threw,'Non-finite yaw must reject');}
   observations.push({case:'actual_low_level_reach_floor_direction'});
  }
  for(const kind of ['base','furniture','clear']){
   const {a,b}=pair(kind),expected=kind==='base'?'solid_obstruction':kind==='furniture'?'furniture_obstruction':'door_obstruction';
   for(const w of [a,b]){
    let state;for(let i=0;i<25;i++){state=w.step(.05,{forward:true});if(state.blocked)break;}
    need(state.blocked===expected,'Raw actual obstruction cause differs for '+kind+': '+state.blocked);
    const diagnostics=w.collisionCollections();need(diagnostics.contract==='ordinary_walking_collision_collections_v1','Exact defensive diagnostic contract required');
    const ids=Object.values(diagnostics.collections).flatMap(g=>g.chunks.flat().map(c=>c.id));need(ids.length===new Set(ids).size,'Each actual collider must occur in exactly one collection');
    if(kind!=='clear')need(rows(diagnostics,kind==='base'?'base':'furniture').some(c=>c.id.endsWith('probe_obstacle')),'Real classified collection must contain the actual obstruction');
    immutability(w);
   }
   observations.push({case:'real_raw_'+expected,producer:a.snapshot(),consumer:b.snapshot(),producer_collections:a.collisionCollections(),consumer_collections:b.collisionCollections()});
  }
  return {contract:'world097_synthetic_observations_v1',synthetic_only:true,normal_success:false,observations,limits:['No saved world, GLB, all-pose export, native host, physical pressure or headset proof.','Factory binding, source/import closure and execution authority must be reviewed separately.']};
 }catch(error){primaryFailed=true;primaryFailure=error;throw error;}
 finally{const cleanupFailures=[];for(const value of owned.reverse())try{value.dispose();}catch(error){cleanupFailures.push(error);}
  if(cleanupFailures.length)throw new AggregateError(primaryFailed?[primaryFailure,...cleanupFailures]:cleanupFailures,primaryFailed?'Synthetic primary failure and owned cleanup held':'Synthetic owned cleanup held');}
}
