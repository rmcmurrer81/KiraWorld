// Pure metadata projection: no files, network, renderer, geometry synthesis or models.
import {buildAirlockPolicy} from './airlock_policy.mjs';
export const SCENE_METADATA_CONTRACT='world_scene_metadata_v2';
const ID=/^[a-z][a-z0-9_]{0,95}$/;
const HASH=/^[0-9a-f]{64}$/;
function require(ok,message){if(!ok)throw new TypeError(message);}
function id(value){require(typeof value==='string'&&ID.test(value),'Invalid stable id');return value;}
function finite(n){require(typeof n==='number'&&Number.isFinite(n)&&Math.abs(n)<=1e6,'Invalid finite dimension');return n;}
function positive(n){finite(n);require(n>0,'Positive dimension required');return n;}
function vector(v){require(Array.isArray(v)&&v.length===3,'Three coordinates required');return [finite(v[0]),finite(v[1]),finite(v[2])];}
function size(v){return vector(v).map(positive);}
function label(value){require(typeof value==='string'&&value.length>0&&value.length<=200&&!/[\x00-\x1f]/.test(value)&&!/:\/\/|^[A-Za-z]:[\\/]|^\/|\\/.test(value),'Invalid label or local path');return value;}
function list(value,max){require(Array.isArray(value)&&value.length<=max,'Collection exceeds supported size');for(let i=0;i<value.length;i++)require(i in value,'Sparse collections unsupported');return value;}
function bounds(b){const min=vector(b.min),max=vector(b.max);require(min.every((v,i)=>v<max[i]),'Invalid bounds');return {min,max};}
function freeze(value){if(value&&typeof value==='object'){for(const v of Object.values(value))freeze(v);Object.freeze(value);}return value;}
function equal(a,b){return JSON.stringify(a)===JSON.stringify(b);}
function box(center,dimensions){return {min:center.map((n,i)=>n-dimensions[i]/2),max:center.map((n,i)=>n+dimensions[i]/2)};}
function sameBox(a,b){return ['min','max'].every(k=>a[k].every((v,i)=>Math.abs(v-b[k][i])<1e-7));}
function inside(a,b){return a.min.every((v,i)=>v>=b.min[i]-1e-7&&a.max[i]<=b.max[i]+1e-7);}
function hashBindings(value){
 require(value&&typeof value==='object'&&!Array.isArray(value),'Explicit digest provenance required');
 const allowed=new Set(['geometry','dressing_recipe','door_controller']);
 require(Object.keys(value).length===3&&Object.keys(value).every(k=>allowed.has(k)),'Only geometry, dressing_recipe and door_controller digests are accepted');
 return Object.fromEntries([...allowed].map(k=>{require(typeof value[k]==='string'&&HASH.test(value[k]),'Invalid source digest');return [k,value[k]];}));
}

/** Export static authoring metadata. Digests are caller-supplied bindings, not a verification claim. */
export function exportSceneMetadata(geometry,dressing,doorDefinitions,{sceneId,sourceDigests,doorInterlocks}={}){
 id(sceneId);const provenance=hashBindings(sourceDigests);
 require(geometry?.contract==='compiled_blueprint_geometry_v1'&&geometry.units==='meters','Unsupported source geometry');
 require(dressing?.contract==='authored_habitat_equipment_plan_v1','Unsupported dressing plan');
 const seen=new Set(),addId=(prefix,value)=>{const key=prefix+':'+id(value);require(!seen.has(key),'Duplicate entity id: '+key);seen.add(key);return key;};
 const rooms=list(geometry.rooms,256).map(r=>({id:addId('room',r.id),source_id:r.id,label:label(r.name),
  functional_role:geometry.functional_program?.[r.id]?id(geometry.functional_program[r.id]):null,
  bounds:box([finite(r.x)+positive(r.width)/2,finite(r.floor_y)+positive(r.height)/2,finite(r.z)+positive(r.depth)/2],[r.width,r.height,r.depth]),
  access:r.access==='walkable_layout'?'walkable_layout':r.access==='closed_locked_solid'?'closed_locked_solid':null}));
 require(rooms.length>0&&rooms.every(r=>r.access!==null),'Missing rooms or unknown access');
 const roomMap=new Map(rooms.map(r=>[r.source_id,r]));
 const member=value=>{require(roomMap.has(value),'Unknown room reference');return 'room:'+value;};
 const nodes=[],nodeMap=new Map();
 function node(value){require(!nodeMap.has(value.id),'Duplicate node id');nodes.push(value);nodeMap.set(value.id,value);return value;}
 for(const p of list(geometry.primitives,4096)){
  require(p.primitive==='box','Only existing structural boxes can be described');
  node({id:addId('node',p.id),kind:'structural_primitive',role:id(p.role),
   transform:{position:vector(p.position),rotation_y_radians:0,scale:[1,1,1]},
   representation:{type:'existing_box_parameters',size:size(p.size)}});
 }
 const extraOwners=new Map();
 for(const o of list(dressing.objects,128)){
  const b=bounds(o.bounds),room=roomMap.get(o.room_id);require(room&&inside(b,room.bounds),'Equipment outside its room');
  const center=vector(o.center),dimensions=size(o.localSize),yaw=finite(o.yaw),c=Math.abs(Math.cos(yaw)),s=Math.abs(Math.sin(yaw));
  require(sameBox(b,box(center,[c*dimensions[0]+s*dimensions[2],dimensions[1],s*dimensions[0]+c*dimensions[2]])),'Equipment transform/bounds mismatch');
  const value=node({id:addId('node',o.id),room_id:member(o.room_id),kind:id(o.kind),functional_role:id(o.role),
   transform:{position:[center[0],center[1]-dimensions[1]/2,center[2]],rotation_y_radians:yaw,scale:[1,1,1],origin:'base_center'},
   dimensions:size(o.localSize),bounds:b,
   representation:{type:'semantic_assembly_metadata_only',mesh_included:false,material_data_included:false},
   interactions:[],behavior:'static_visual_equipment'});
  extraOwners.set(o.id,{owner:value.id,bounds:b});
 }
 for(const a of list(dressing.architecture,128)){
  const b=bounds(a.bounds),room=roomMap.get(a.room_id);require(room&&inside(b,room.bounds),'Architecture outside its room');
  const value=node({id:addId('node',a.id),room_id:member(a.room_id),kind:id(a.kind),bounds:b,
   transform:{position:vector(a.center),rotation_y_radians:0,scale:[1,1,1]},
   dimensions:size(a.size),representation:{type:'semantic_architecture_metadata_only',mesh_included:false}});
  extraOwners.set(a.id,{owner:value.id,bounds:b});
 }
 // Signs have separate physical bounds in the authored plan; text is explicitly projected.
 for(const s of list(dressing.signs,128)){
  const b=bounds(s.bounds);member(s.room_id);require(inside(b,roomMap.get(s.room_id).bounds),'Sign outside its room');
  const value=node({id:addId('node',s.id),room_id:member(s.room_id),kind:'mounted_sign',bounds:b,label:label(s.text),
   position:vector(s.position),normal:vector(s.normal),dimensions:size(s.size),representation:{type:'semantic_sign_metadata_only',mesh_included:false}});
  extraOwners.set(s.id,{owner:value.id,bounds:b});
 }
 const colliders=[];
 for(const c of list(geometry.colliders,4096)){
  const exact=nodeMap.get('node:'+c.id),floor=nodeMap.get('node:'+c.id+'_mesh');
  // Walls/ceilings use their exact source id. The compiler names a floor's
  // display primitive with _mesh; that alias is valid only for an actual floor.
  const owners=[exact,floor?.role==='floor'?floor:null].filter(Boolean);
  require(owners.length===1,'Missing or ambiguous structural collider owner');
  const owner=owners[0],physical=bounds(c);
  require(owner.kind==='structural_primitive'&&owner.representation.type==='existing_box_parameters',
   'Structural collider must belong to a structural primitive');
  require(sameBox(physical,box(owner.transform.position,owner.representation.size)),
   'Structural collider owner bounds mismatch');
  colliders.push({id:addId('collider',c.id),owner_node_id:owner.id,shape:'axis_aligned_box',bounds:physical,motion:'static',proxy:'source_conservative_bounds'});
 }
 for(const c of list(dressing.colliders,128)){
  const owned=extraOwners.get(c.id);require(owned&&sameBox(bounds(c),owned.bounds),'Equipment collider ownership/bounds mismatch');
  colliders.push({id:addId('collider',c.id),owner_node_id:owned.owner,shape:'axis_aligned_box',bounds:bounds(c),motion:'static',proxy:'conservative_assembly_bounds'});
 }
 require(dressing.colliders.length===extraOwners.size,'Missing authored object collider');
 const portalMap=new Map();
 for(const p of list(geometry.portals,256)){
  id(p.id);require(!portalMap.has(p.id),'Duplicate portal');member(p.room_a);member(p.room_b);portalMap.set(p.id,p);
 }
 const doors=list(doorDefinitions,24).map(d=>{
  const portal=portalMap.get(d.portalId);require(portal&&d.id===d.portalId&&portal.state==='open_passage','Door portal unavailable');
  require(d.roomAId===portal.room_a&&d.roomBId===portal.room_b,'Door room membership changed');
  require(d.initialState==='closed'&&d.statePersistence==='session_local'&&d.pressureSimulation===false,'Unsupported door capability');
  require(equal(vector(d.rotationAxis),[0,1,0])&&d.closedAngle===0&&Math.abs(Math.abs(finite(d.openAngle))-Math.PI/2)<1e-9,'Unsupported hinge rotation');
  require(d.collisionPolicy==='conservative_rotated_leaf_aabb_and_quarter_disc_sweep','Unknown door collision policy');
  const hinge=vector(d.hinge),leafSize=size(d.leafSize),local=vector(d.leafLocalCenter),leafId=addId('node','door_'+d.id+'_leaf');
  require(portal.axis==='x'||portal.axis==='z','Unsupported door axis');
  const axis=portal.axis==='x'?0:2,tangent=axis===0?2:0;
  require(Math.abs(hinge[axis]-portal.coordinate)<1e-8&&Math.abs(hinge[tangent]-(portal.center-portal.width/2+.02))<1e-8&&
   Math.abs(hinge[1]-roomMap.get(d.roomAId).bounds.min[1])<1e-8,'Door hinge differs from portal');
  require(Math.abs(leafSize[axis]-.065)<1e-8&&Math.abs(leafSize[tangent]-(portal.width-.04))<1e-8&&Math.abs(leafSize[1]-(portal.height-.025))<1e-8,'Door leaf differs from portal');
  require(Math.abs(local[axis])<1e-8&&Math.abs(local[tangent]-leafSize[tangent]/2)<1e-8&&Math.abs(local[1]-(.0125+leafSize[1]/2))<1e-8,'Door pivot differs from authoring definition');
  const initial=hinge.map((v,i)=>v+local[i]);
  node({id:leafId,kind:'door_leaf',transform:{position:initial,rotation_y_radians:0,scale:[1,1,1]},
    representation:{type:'existing_box_parameters',size:leafSize}});
  colliders.push({id:addId('collider','door_'+d.id+'_leaf'),owner_node_id:leafId,shape:'axis_aligned_box',bounds:box(initial,leafSize),motion:'kinematic',proxy:d.collisionPolicy});
  const frames=list(d.frames,3).map(f=>{
   const center=vector(f.center),dimensions=size(f.size),n=node({id:addId('node',f.id),kind:'door_frame',transform:{position:center,rotation_y_radians:0,scale:[1,1,1]},representation:{type:'existing_box_parameters',size:dimensions}});
   colliders.push({id:addId('collider',f.id),owner_node_id:n.id,shape:'axis_aligned_box',bounds:box(center,dimensions),motion:'static',proxy:'frame_box'});return n.id;
  });
  require(frames.length===3,'Door frame incomplete');
  return {id:addId('door',d.id),portal_id:d.portalId,room_ids:[member(d.roomAId),member(d.roomBId)],leaf_node_id:leafId,frame_node_ids:frames,
   hinge:{position:hinge,axis:vector(d.rotationAxis),leaf_local_center:local,closed_angle:0,open_angle:d.openAngle},
   angular_speed_rad_s:positive(d.angularSpeed),max_step_seconds:positive(d.maxStepSeconds),swing_bounds:bounds(d.swingBounds),
   interaction:{action:'toggle_door',maximum_reach_m:positive(d.interactionReach),rules:['same_floor','adjacent_room','outside_occupied_swing','not_already_moving']},
   collision_policy:d.collisionPolicy,initial_state:'closed',state_persistence:'session_local',pressure_simulation:false};
 });
 const requiredDoors=[...portalMap.values()].filter(p=>p.state==='open_passage'&&roomMap.get(p.room_a).access==='walkable_layout'&&roomMap.get(p.room_b).access==='walkable_layout');
 require(requiredDoors.length===doors.length&&requiredDoors.every(p=>doors.some(d=>d.portal_id===p.id)),'Door definitions do not cover the source portals');
 const airlockPairs=buildAirlockPolicy(geometry,doors,nodes,doorInterlocks);
 for(const door of doors){door.interlock_pair_ids=airlockPairs.filter(p=>p.door_ids.includes(door.id)).map(p=>p.id);if(door.interlock_pair_ids.length)door.interaction.rules.push('paired_airlock_peer_closed_stopped');}
 const entry=member(geometry.connectivity?.entry_room_id),entryRoom=roomMap.get(geometry.connectivity.entry_room_id);require(entryRoom.access==='walkable_layout','Entry room is locked');
 const result={contract:SCENE_METADATA_CONTRACT,scene_id:sceneId,coordinate_system:{units:'meters',handedness:'right',up:'+Y',forward:'-Z',rotation_angles:'radians'},
  rooms,nodes,colliders,doors,airlock_pairs:airlockPairs,
  navigation:{kind:'horizontal_supported_walking',entry_room_id:entry,spawn_feet:[(entryRoom.bounds.min[0]+entryRoom.bounds.max[0])/2,entryRoom.bounds.min[1],(entryRoom.bounds.min[2]+entryRoom.bounds.max[2])/2],
   support_surfaces:list(geometry.support_surfaces,512).map(s=>{require(s.min_x<s.max_x&&s.min_z<s.max_z,'Invalid support extent');return {id:id(s.id),min_x:finite(s.min_x),max_x:finite(s.max_x),min_z:finite(s.min_z),max_z:finite(s.max_z),y:finite(s.y)};}),
   authored_routes:list(geometry.routes,512).map(r=>{require(r.points?.length>=2,'Route needs endpoints');return {id:id(r.id),avatar_radius:positive(r.avatar_radius),avatar_height:positive(r.avatar_height),points:list(r.points,512).map(vector)};})},
  provenance:{source_digests:provenance,binding_verification:'caller_supplied_not_independently_verified',source_geometry_contract:geometry.contract,dressing_contract:dressing.contract,door_contract:'preview_hinged_doors_v2'},
  capabilities:{metadata_only:true,airlock_pair_policy_metadata:true,structural_box_parameters:true,semantic_equipment:true,equipment_meshes:false,materials_or_textures:false,engine_adapter:false,vr_runtime:false,session_state_export:false},
  limitations:['Semantic equipment metadata does not contain its multipart meshes or materials.','Door metadata requires an adapter implementing the specified conservative controller policy.','Static equipment has no science, medical or life-support behavior.','No pressure simulation, persisted door state, rigid-body certification or VR support.','Appearance remains a procedural prototype; no owner or realism approval.']};
 return freeze(result);
}

// Canonical property ordering is stable; inputs themselves are never reordered.
export function canonicalSceneMetadata(scene){
 require(scene?.contract===SCENE_METADATA_CONTRACT,'Unsupported metadata contract');
 const active=new Set();let count=0;
 function sorted(v,depth=0){
  require(++count<100000&&depth<24,'Metadata exceeds serialization bounds');
  if(v===null||typeof v==='string'||typeof v==='boolean')return v;
  if(typeof v==='number'){finite(v);return v;}
  require(v&&typeof v==='object'&&!active.has(v),'Non-JSON or cyclic metadata');active.add(v);
  require(Array.isArray(v)||Object.getPrototypeOf(v)===Object.prototype,'Plain JSON metadata required');
  const result=Array.isArray(v)?v.map(x=>sorted(x,depth+1)):Object.fromEntries(Object.keys(v).sort().map(k=>[k,sorted(v[k],depth+1)]));active.delete(v);return result;
 }
 return JSON.stringify(sorted(scene));
}
