// Artificial metadata and a synchronous double. These are NOT an admitted world,
// a GLB fixture, a physical airlock, or a collision/navigation implementation.
import {bindAirlockCycle, createAirlockCycle} from '../candidate/airlock_cycle.mjs';

export function artificialMetadata() {
  const ids = ['demo:inner', 'demo:outer'];
  return {
    contract: 'world_scene_metadata_v2', scene_id: 'demo:synthetic-scene',
    rooms: [
      {id:'demo:chamber', functional_role:'airlock'},
      {id:'demo:interior-room', functional_role:'habitat'},
      {id:'demo:exterior-proxy', functional_role:'demonstration'},
    ],
    airlock_pairs: [{
      id:'demo:pair', room_id:'demo:chamber', contract:'paired_airlock_door_sequence_v1',
      pressure_simulation:false, state_persistence:'session_local', door_ids:ids,
      leaf_node_ids:ids.map(id=>id+'-leaf'), portal_ids:ids.map(id=>id+'-portal'),
      opening_policy:{requires_peer:'closed_and_stopped', blocked_peer_conditions:['nonzero_angle','moving','nonzero_target','motion_held']},
      closing_policy:'existing_reach_motion_and_occupancy_rules',
    }],
    doors: ids.map((id,i)=>({
      id, leaf_node_id:id+'-leaf', portal_id:id+'-portal',
      pressure_simulation:false, state_persistence:'session_local', initial_state:'closed',
      room_ids:['demo:chamber',i===0?'demo:interior-room':'demo:exterior-proxy'],
      interlock_pair_ids:['demo:pair'], interaction:{rules:['paired_airlock_peer_closed_stopped']},
      hinge:{closed_angle:0, open_angle:(i===0?1:-1)*Math.PI/2},
    })),
  };
}

export function artificialOptions() {
  return {manifestSha256:'a'.repeat(64), sceneSha256:'b'.repeat(64), pairId:'demo:pair',
    insideDoorId:'demo:inner', outsideDoorId:'demo:outer', roleAssignment:'explicit_fictional_habitat_mars'};
}

export function fixture() {
  const metadata=artificialMetadata(), options=artificialOptions();
  const binding=bindAirlockCycle(metadata,options), runtimeIdentity=Object.freeze({});
  const doors=metadata.doors.map(d=>({id:d.id,angle:0,target:0,moving:false,motionHeld:false}));
  const controls={readFailure:null,readPatch:null,command:null,reads:0,commands:[]};
  function readDoors() {
    controls.reads++;
    if(controls.readFailure) throw new Error(controls.readFailure);
    const value={runtimeIdentity, manifestSha256:options.manifestSha256,
      sceneSha256:options.sceneSha256, sceneId:metadata.scene_id,doors:structuredClone(doors)};
    return controls.readPatch ? controls.readPatch(value) : value;
  }
  function toggleDoor(id) {
    controls.commands.push(id);
    if(controls.command) return controls.command(id);
    const row=doors.find(d=>d.id===id), source=metadata.doors.find(d=>d.id===id);
    row.target=row.target===0?source.hinge.open_angle:0;row.moving=true;
    return {ok:true};
  }
  const cycle=createAirlockCycle({binding,runtimeIdentity,readDoors,toggleDoor,cycleSeconds:2});
  return {metadata,options,binding,runtimeIdentity,doors,controls,cycle,readDoors,toggleDoor,
    settle(side) {const row=doors[side==='inside'?0:1];row.angle=row.target;row.moving=false;},
    seal() {return ['inside','outside'].map(side=>cycle.acknowledgeSimulatedSeal(side));},
    finish(token) {let result;for(let i=0;i<8;i++) result=cycle.advance(token,.25);return result;},
  };
}
