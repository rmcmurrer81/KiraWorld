// Strict v2 descriptor only. This does not admit a GLB or any package hash.
import {planLatchedPressureHatch,latchHatchCollidersAt,LATCH_HATCH_CONTRACT,LATCH_COLLISION_POLICY} from './pressure_hatch_latched.mjs';
export {LATCH_HATCH_CONTRACT};
export const LATCH_METADATA_CONTRACT='latched_hatch_controller_metadata_v2';
const need=(v,m)=>{if(!v)throw new TypeError(m);};
const canon=v=>Array.isArray(v)?v.map(canon):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canon(v[k])])):v;
const same=(a,b)=>JSON.stringify(canon(a))===JSON.stringify(canon(b));
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const id=v=>typeof v==='string'&&/^[a-z][a-z0-9_]{0,63}$/.test(v);
const keys=(v,ks)=>v&&typeof v==='object'&&!Array.isArray(v)&&same(Object.keys(v).sort(),[...ks].sort());
const finite=v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<1e6;
const roomKeys=['id','x','z','width','depth','height','floor_y','access'];
const portalKeys=['id','room_a','room_b','axis','coordinate','center','width','height','state'];
export function authoringInput(geometry){
 need(geometry?.contract==='compiled_blueprint_geometry_v1'&&geometry.units==='meters','Explicit compiled meter-based authoring input required');
 const g={contract:'compiled_blueprint_geometry_v1',units:'meters',rooms:geometry.rooms.map(r=>Object.fromEntries(roomKeys.map(k=>[k,r[k]]))),
  portals:geometry.portals.map(p=>Object.fromEntries(portalKeys.map(k=>[k,p[k]]))),functional_program:structuredClone(geometry.functional_program??{})};
 validateInput(g);return freeze(g);
}
function validateInput(g){
 need(keys(g,['contract','units','rooms','portals','functional_program'])&&g.contract==='compiled_blueprint_geometry_v1'&&g.units==='meters','Invalid v2 recipe input');
 need(Array.isArray(g.rooms)&&g.rooms.length>=3&&g.rooms.length<=9&&Array.isArray(g.portals)&&g.portals.length<=24,'Invalid v2 input size');
 const rooms=new Map(),ports=new Set();
 for(const r of g.rooms){need(keys(r,roomKeys)&&id(r.id)&&!rooms.has(r.id)&&['x','z','width','depth','height','floor_y'].every(k=>finite(r[k]))&&r.width>0&&r.depth>0&&r.height>0&&r.floor_y===0&&['walkable_layout','closed_locked_solid'].includes(r.access),'Invalid v2 room');rooms.set(r.id,r);}
 need(g.functional_program&&typeof g.functional_program==='object'&&!Array.isArray(g.functional_program)&&Object.entries(g.functional_program).every(([k,v])=>rooms.has(k)&&id(v)),'Invalid v2 roles');
 for(const p of g.portals){
  need(keys(p,portalKeys)&&id(p.id)&&!ports.has(p.id)&&rooms.has(p.room_a)&&rooms.has(p.room_b)&&p.room_a!==p.room_b&&['x','z'].includes(p.axis)&&['coordinate','center','width','height'].every(k=>finite(p[k])),'Invalid v2 portal');ports.add(p.id);
  const a=rooms.get(p.room_a),b=rooms.get(p.room_b),axis=p.axis,n=axis==='x'?'width':'depth',t=axis==='x'?'z':'x',span=axis==='x'?'depth':'width';
  need((Math.abs(a[axis]+a[n]-p.coordinate)<1e-8&&Math.abs(b[axis]-p.coordinate)<1e-8)||(Math.abs(b[axis]+b[n]-p.coordinate)<1e-8&&Math.abs(a[axis]-p.coordinate)<1e-8),'V2 portal is not on a shared wall');
  need(p.width>=.9&&p.width<=8&&p.height>=1.9&&p.height<=Math.min(a.height,b.height)&&p.width+.1<a[n]&&p.center-p.width/2>=Math.max(a[t],b[t])+.15-1e-8&&p.center+p.width/2<=Math.min(a[t]+a[span],b[t]+b[span])-.15+1e-8,'V2 portal exceeds source room');
  need(p.state===(a.access==='walkable_layout'&&b.access==='walkable_layout'?'open_passage':'closed_locked_solid'),'V2 portal access differs');
 }
 return g;
}
const nodeKey=(portal,part)=>part.endsWith('_reinforced_leaf')?'node:door_'+portal+'_leaf':'node:'+part.replaceAll('-','negative_');
const union=rows=>({min:[0,1,2].map(i=>Math.min(...rows.map(c=>c.min[i]))),max:[0,1,2].map(i=>Math.max(...rows.map(c=>c.max[i])))});
export function describeLatchedDoor(geometry,portalId){
 const input=authoringInput(geometry),plan=planLatchedPressureHatch(input,portalId);need(plan,'Expected paired v2 hatch');
 const portal=input.portals.find(p=>p.id===portalId),initial=latchHatchCollidersAt(plan,0);
 const nodes=plan.parts.map(p=>({id:nodeKey(portalId,p.id),kind:p.id.endsWith('_reinforced_leaf')?'door_leaf':'pressure_hatch_part',hatch_part_id:p.id,motion:p.motion,
  bounds:union(initial.filter(c=>c.owner===p.id)),transform:{position:[...(p.motion==='static'?plan.origin:plan.hinge)],rotation_y_radians:0,scale:[1,1,1],origin:p.motion==='static'?'hatch_origin':'hatch_hinge'},
  representation:{type:'authored_latched_hatch_parameters_v2',recipe_contract:plan.contract,parameters:structuredClone(p)}}));
 const colliders=initial.map(c=>({id:'collider:'+(c.owner.endsWith('_reinforced_leaf')?'door_'+portalId+'_leaf':c.id.replaceAll('-','negative_')),
  source_collider_id:c.id,owner_node_id:nodeKey(portalId,c.owner),shape:'axis_aligned_box',bounds:{min:[...c.min],max:[...c.max]},motion:c.motion,
  proxy:c.motion==='static'?'latched_hatch_static_all_pose_bounds_v2':'latched_hatch_rotated_all_pose_bounds_v2'}));
 const n=plan.axis==='x'?0:2,t=n===0?2:0,local=[0,plan.localLeafCenter[1],0];local[n]=plan.normalSign*plan.localLeafCenter[2];local[t]=plan.localLeafCenter[0];
 const pairRooms=input.rooms.filter(r=>input.functional_program[r.id]==='airlock'&&[portal.room_a,portal.room_b].includes(r.id));
 const door={id:'door:'+portalId,portal_id:portalId,room_ids:['room:'+portal.room_a,'room:'+portal.room_b],variant:plan.contract,
  leaf_node_id:nodeKey(portalId,plan.parts.find(p=>p.id.endsWith('_reinforced_leaf')).id),frame_node_ids:nodes.filter(p=>p.motion==='static').map(p=>p.id),kinematic_node_ids:nodes.filter(p=>p.motion==='kinematic').map(p=>p.id),
  hinge:{position:[...plan.hinge],axis:[0,1,0],leaf_local_center:local,leaf_geometry_origin:'hinge_local',closed_angle:0,open_angle:plan.openAngle},
  angular_speed_rad_s:Math.PI*1.25,max_step_seconds:.05,swing_bounds:structuredClone(plan.swingBounds),collision_policy:LATCH_COLLISION_POLICY,
  interaction:{action:'toggle_door',maximum_reach_m:2.25,rules:['same_floor','adjacent_room','outside_occupied_swing','not_already_moving',...(pairRooms.length?['paired_airlock_peer_closed_stopped']:[])]},
  interlock_pair_ids:pairRooms.map(r=>'airlock_pair:'+r.id),initial_state:'closed',state_persistence:'session_local',pressure_simulation:false,
  latch:{contract:'authored_latch_state_v2',initial_state:'released',duration_seconds:.8,max_step_seconds:.05,hinge_requires:'released_stopped',physical_simulation:false,seal_acknowledgement_authority:false},
  authoring:{contract:LATCH_METADATA_CONTRACT,input,replaced_part_ids:[...plan.replacedPartIds]}};
 return freeze({door,nodes,colliders});
}
export function validateLatchedDoor(d,nodes,colliders,metadata){
 need(d?.variant===LATCH_HATCH_CONTRACT&&d.authoring?.contract===LATCH_METADATA_CONTRACT,'Expected strict v2 latch metadata');
 const expected=describeLatchedDoor(d.authoring.input,d.portal_id);
 need(same(d,expected.door),'V2 door differs from exact authored descriptor');
 // Cross-bind every recipe room/portal to the actual portable scene, not a private shadow layout.
 need(metadata&&Array.isArray(metadata.rooms)&&Array.isArray(metadata.doors)&&metadata.rooms.length===d.authoring.input.rooms.length&&metadata.doors.length===d.authoring.input.portals.filter(p=>p.state==='open_passage').length,'V2 source/scene collection differs');
 for(const r of d.authoring.input.rooms){const found=metadata.rooms.filter(x=>x.id==='room:'+r.id);need(found.length===1,'V2 source room missing');const m=found[0];
  need(same(m.bounds,{min:[r.x,r.floor_y,r.z],max:[r.x+r.width,r.floor_y+r.height,r.z+r.depth]})&&m.access===r.access&&m.functional_role===(d.authoring.input.functional_program[r.id]??null),'V2 source room differs from scene');}
 for(const p of d.authoring.input.portals.filter(p=>p.state==='open_passage')){const found=metadata.doors.filter(x=>x.portal_id===p.id);need(found.length===1&&same(found[0].room_ids,['room:'+p.room_a,'room:'+p.room_b]),'V2 portal association differs');
  if(planLatchedPressureHatch(d.authoring.input,p.id))need(found[0].variant===LATCH_HATCH_CONTRACT&&same(found[0].authoring?.input,d.authoring.input),'Paired v2 hatches require one exact source recipe');}
 for(const row of expected.nodes)need(same(nodes.get(row.id),row),'V2 mesh metadata differs');
 const expectedIds=new Set(expected.colliders.map(c=>c.id)),owners=new Set(expected.nodes.map(n=>n.id));
 need([...nodes.values()].filter(n=>n.hatch_part_id?.startsWith('hatch_'+d.portal_id+'_')).length===expected.nodes.length,'Unexpected v2 hatch part');
 need([...colliders.values()].filter(c=>owners.has(c.owner_node_id)).length===expected.colliders.length,'V2 collider ownership differs');
 for(const row of expected.colliders)need(same(colliders.get(row.id),row)&&expectedIds.has(row.id),'V2 collider differs');
 return expected.colliders.filter(c=>c.motion==='kinematic');
}
