export const PAIR_CONTRACT='paired_airlock_door_sequence_v1';
const require=(ok,message)=>{if(!ok)throw new TypeError(message);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

// Verify the controller's explicit pair definitions against authored rooms and
// the existing source-linked door/leaf nodes before describing the policy.
export function buildAirlockPolicy(geometry,doors,nodes,controllerPairs){
 require(Array.isArray(controllerPairs),'Explicit controller airlock pairs required');
 const authored=geometry.rooms.filter(r=>geometry.functional_program?.[r.id]==='airlock');
 require(authored.length===controllerPairs.length,'Airlock pair count differs from authored roles');
 const nodeMap=new Map(nodes.map(n=>[n.id,n]));
 return authored.map(room=>{
  const sourceDoors=geometry.portals.filter(p=>p.room_a===room.id||p.room_b===room.id);
  require(sourceDoors.length===2&&sourceDoors.every(p=>p.state==='open_passage'),'Airlock needs exactly two open source portals');
  const pairs=controllerPairs.filter(p=>p.roomId===room.id);require(pairs.length===1,'Missing or duplicate controller airlock pair');
  const pair=pairs[0],ids=sourceDoors.map(p=>p.id);
  require(pair.contract===PAIR_CONTRACT&&same(pair.doorIds,ids)&&pair.pressureSimulation===false&&pair.statePersistence==='session_local','Controller airlock policy differs from source');
  const described=sourceDoors.map(p=>{
   const found=doors.filter(d=>d.portal_id===p.id);require(found.length===1,'Missing or duplicate airlock door association');
   const d=found[0];require(d.id==='door:'+p.id&&d.leaf_node_id==='node:door_'+p.id+'_leaf'&&same(d.room_ids,['room:'+p.room_a,'room:'+p.room_b]),'Airlock door source association differs');
   require(nodeMap.get(d.leaf_node_id)?.kind==='door_leaf','Airlock leaf association is missing or not a door leaf');return d;
  });
  require(new Set(described.map(d=>d.leaf_node_id)).size===2,'Airlock must have two distinct leaves');
  return {id:'airlock_pair:'+room.id,contract:PAIR_CONTRACT,source_room_id:room.id,room_id:'room:'+room.id,
   door_ids:described.map(d=>d.id),portal_ids:ids,leaf_node_ids:described.map(d=>d.leaf_node_id),
   opening_policy:{requires_peer:'closed_and_stopped',blocked_peer_conditions:['nonzero_angle','moving','nonzero_target','motion_held']},
   closing_policy:'existing_reach_motion_and_occupancy_rules',runtime_implemented_in:'source_preview_controller_only',
   engine_runtime_included:false,pressure_simulation:false,state_persistence:'session_local'};
 });
}
