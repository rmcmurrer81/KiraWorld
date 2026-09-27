// Strict new door variant. Ordinary-door checks remain in scene_metadata.
import {planPressureHatch,hatchCollidersAt,hatchSwingBounds} from './pressure_hatch.mjs';
const require=(ok,message)=>{if(!ok)throw new TypeError(message);};
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export const hatchPartNodeKey=(portalId,partId)=>partId.endsWith('_reinforced_leaf')?'door_'+portalId+'_leaf':partId.replaceAll('-','negative_');
export function describePressureHatch(geometry,d,{node,addId,member}){
 const plan=planPressureHatch(geometry,d.portalId),portal=geometry.portals.find(p=>p.id===d.portalId);
 require(plan&&d.id===d.portalId&&d.kind==='pressure_hatch'&&equal(d.hatchPlan,plan),'Hatch definition differs from exact source recipe');
 require(d.roomAId===portal.room_a&&d.roomBId===portal.room_b,'Hatch room association differs');
 const n=plan.axis==='x'?0:2,t=n===0?2:0,size=[0,plan.leafHeight,0],center=[0,plan.localLeafCenter[1],0];
 size[n]=.065;size[t]=plan.leafWidth;center[n]=plan.normalSign*plan.localLeafCenter[2];center[t]=plan.localLeafCenter[0];
 require(equal(d.hinge,plan.hinge)&&equal(d.rotationAxis,[0,1,0])&&d.closedAngle===0&&d.openAngle===plan.openAngle&&equal(d.leafSize,size)&&equal(d.leafLocalCenter,center),'Hatch hinge/leaf geometry differs');
 require(equal(d.swingBounds,hatchSwingBounds(plan))&&d.collisionPolicy==='authored_hatch_part_aabbs_and_analytic_sweep','Hatch collision admission differs');
 require(d.angularSpeed===Math.PI*1.25&&d.maxStepSeconds===.05&&d.interactionReach===2.25,'Hatch interaction timing differs');
 require(d.initialState==='closed'&&d.statePersistence==='session_local'&&d.pressureSimulation===false&&d.latchSimulation===false&&d.latchState==='static_retracted'&&Array.isArray(d.frames)&&d.frames.length===0,'Unsupported hatch behavior');
 const initialColliders=hatchCollidersAt(plan,0),owners=new Map(),fixedIds=[],movingIds=[];
 for(const [parts,motion] of [[plan.fixed,'static'],[plan.moving,'kinematic']])for(const part of parts){
  const leaf=part.id.endsWith('_reinforced_leaf'),id=addId('node',hatchPartNodeKey(d.id,part.id));
  const colliders=initialColliders.filter(c=>c.owner===part.id);require(colliders.length>0,'Hatch part has no owned collider');
  const bounds={min:[0,1,2].map(i=>Math.min(...colliders.map(c=>c.min[i]))),max:[0,1,2].map(i=>Math.max(...colliders.map(c=>c.max[i])))};
  node({id,kind:leaf?'door_leaf':'pressure_hatch_part',hatch_part_id:part.id,motion,bounds,
   transform:{position:[...(motion==='static'?plan.origin:plan.hinge)],rotation_y_radians:0,scale:[1,1,1],origin:motion==='static'?'hatch_origin':'hatch_hinge'},
   representation:{type:'authored_hatch_part_parameters',recipe_contract:plan.contract,parameters:structuredClone(part)},
   behavior:'static_retracted_hardware_no_pressure_simulation'});
  owners.set(part.id,id);(motion==='static'?fixedIds:movingIds).push(id);
 }
 const colliders=initialColliders.map(c=>({id:addId('collider',c.owner.endsWith('_reinforced_leaf')?'door_'+d.id+'_leaf':c.id.replaceAll('-','negative_')),source_collider_id:c.id,owner_node_id:owners.get(c.owner),shape:'axis_aligned_box',
  bounds:{min:[...c.min],max:[...c.max]},motion:c.motion,proxy:c.motion==='static'?'authored_hatch_static_part_bounds':'authored_hatch_rotated_part_aabb'}));
 return {colliders,door:{id:addId('door',d.id),portal_id:d.portalId,room_ids:[member(d.roomAId),member(d.roomBId)],
  variant:plan.contract,leaf_node_id:'node:door_'+d.id+'_leaf',frame_node_ids:fixedIds,kinematic_node_ids:movingIds,
  hinge:{position:[...plan.hinge],axis:[0,1,0],leaf_local_center:center,leaf_geometry_origin:'hinge_local',closed_angle:0,open_angle:plan.openAngle},
  angular_speed_rad_s:d.angularSpeed,max_step_seconds:d.maxStepSeconds,swing_bounds:hatchSwingBounds(plan),
  interaction:{action:'toggle_door',maximum_reach_m:d.interactionReach,rules:['same_floor','adjacent_room','outside_occupied_swing','not_already_moving']},
  collision_policy:d.collisionPolicy,initial_state:'closed',state_persistence:'session_local',pressure_simulation:false,latch_simulation:false,latch_state:'static_retracted',
  aperture_limits:structuredClone(plan.limits)}};
}
