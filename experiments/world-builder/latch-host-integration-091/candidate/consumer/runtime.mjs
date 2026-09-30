import {HATCH,validateDoorShape,movingForDoor,rotateBounds,unionBounds} from './door_metadata.mjs';
import {createLatchAuthority} from './shared/latch_state.mjs';
import {LATCH_HATCH_CONTRACT} from './shared/latched_metadata.mjs';
// Runtime over portable metadata; v2 includes bounded numeric recipe inputs.
// No source-file lookup, model loading, package admission or rendering.
import {NAVIGATION_CONTRACT,checkWalkSpawn,checkHorizontalRoute} from './horizontal_navigation.mjs';
export const CONTRACT='portable_first_person_consumer_v1';
export const AVATAR=Object.freeze({radius:.34,height:1.68,eye:1.56});
const POLICY='paired_airlock_door_sequence_v1',EPS=1e-7;
export const require=(ok,message)=>{if(!ok)throw new TypeError(message);};
const num=n=>Number.isFinite(n)&&Math.abs(n)<1e6;
const vec=v=>Array.isArray(v)&&v.length===3&&v.every(num);
const box=b=>b&&vec(b.min)&&vec(b.max)&&b.min.every((v,i)=>v<b.max[i]);
const nearArray=(a,b)=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<EPS);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const bounds=(center,size)=>({min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)});
const sameBox=(a,b)=>nearArray(a.min,b.min)&&nearArray(a.max,b.max);
const overlap=(b,p)=>p[1]<b.max[1]&&p[1]+AVATAR.height>b.min[1]&&p[0]+AVATAR.radius>=b.min[0]&&p[0]-AVATAR.radius<=b.max[0]&&p[2]+AVATAR.radius>=b.min[2]&&p[2]-AVATAR.radius<=b.max[2];
function unique(rows,label,max){
 require(Array.isArray(rows)&&rows.length<=max,`Invalid ${label} collection`);const map=new Map();
 for(const r of rows){require(r&&typeof r.id==='string'&&r.id.length<180&&!map.has(r.id),`Duplicate or invalid ${label} id`);map.set(r.id,r);}return map;
}
export function validateMetadata(m){
 require(m?.contract==='world_scene_metadata_v2','Unsupported metadata contract');
 require(Object.entries({forward:'-Z',handedness:'right',rotation_angles:'radians',units:'meters',up:'+Y'}).every(([k,v])=>m.coordinate_system?.[k]===v),'Unsupported coordinates');
 const rooms=unique(m.rooms,'room',9),nodes=unique(m.nodes,'node',4096),colliders=unique(m.colliders,'collider',4096),doors=unique(m.doors,'door',24);
 require(rooms.size>=5,'Unsupported habitat size');
 for(const r of rooms.values())require(box(r.bounds)&&r.bounds.min[1]===0&&['walkable_layout','closed_locked_solid'].includes(r.access),'Invalid room bounds/access');
 for(const c of colliders.values())require(nodes.has(c.owner_node_id)&&c.shape==='axis_aligned_box'&&box(c.bounds)&&['static','kinematic'].includes(c.motion),'Invalid collider or owner');
 const leafOwners=new Set();
 for(const d of doors.values()){
  const leaf=nodes.get(d.leaf_node_id),h=d.hinge;
  require(leaf?.kind==='door_leaf'&&!leafOwners.has(leaf.id),'Invalid or duplicate leaf');leafOwners.add(leaf.id);
  require(Array.isArray(d.room_ids)&&d.room_ids.length===2&&d.room_ids[0]!==d.room_ids[1]&&d.room_ids.every(id=>rooms.get(id)?.access==='walkable_layout'),'Invalid adjacent rooms');
  require(h&&vec(h.position)&&vec(h.leaf_local_center)&&same(h.axis,[0,1,0])&&h.closed_angle===0&&Math.abs(Math.abs(h.open_angle)-Math.PI/2)<EPS,'Unsupported hinge');
  require(d.initial_state==='closed'&&d.state_persistence==='session_local'&&d.pressure_simulation===false,'Unsupported door behavior');
  require(d.angular_speed_rad_s===Math.PI*1.25&&d.max_step_seconds===.05&&box(d.swing_bounds),'Unsupported door motion bounds');
  validateDoorShape(d,nodes,colliders,m);
  require(d.interaction?.action==='toggle_door'&&d.interaction.maximum_reach_m===2.25&&same(d.interaction.rules.slice(0,4),['same_floor','adjacent_room','outside_occupied_swing','not_already_moving']),'Unsupported interaction policy');
 }
 const v2Owners=new Set([...doors.values()].filter(d=>d.variant===LATCH_HATCH_CONTRACT).flatMap(d=>[...d.frame_node_ids,...d.kinematic_node_ids]));
 for(const n of nodes.values())if(n.representation?.recipe_contract===LATCH_HATCH_CONTRACT)require(v2Owners.has(n.id),'Unclaimed v2 hatch part');
 const movingOwners=new Set();for(const d of doors.values())for(const c of movingForDoor(d,colliders)){require(!movingOwners.has(c.id),'Moving collider belongs to multiple doors');movingOwners.add(c.id);}
 require([...colliders.values()].filter(c=>c.motion==='kinematic').every(c=>movingOwners.has(c.id)),'Unsupported moving collider');
 const pairs=unique(m.airlock_pairs,'airlock pair',8),airlocks=[...rooms.values()].filter(r=>r.functional_role==='airlock');
 require(pairs.size===airlocks.length,'Missing authored airlock pairing');
 for(const room of airlocks){
  const matches=[...pairs.values()].filter(p=>p.room_id===room.id);require(matches.length===1,'Missing/ambiguous airlock pair');const p=matches[0];
  const members=[...doors.values()].filter(d=>d.room_ids.includes(room.id));
  require(members.length===2&&p.contract===POLICY&&p.pressure_simulation===false&&p.state_persistence==='session_local','Invalid airlock policy');
  require(same(p.door_ids,members.map(d=>d.id))&&same(p.leaf_node_ids,members.map(d=>d.leaf_node_id))&&same(p.portal_ids,members.map(d=>d.portal_id)),'Airlock source/leaf associations differ');
  require(p.opening_policy?.requires_peer==='closed_and_stopped'&&same(p.opening_policy.blocked_peer_conditions,['nonzero_angle','moving','nonzero_target','motion_held'])&&p.closing_policy==='existing_reach_motion_and_occupancy_rules','Unsupported paired-door policy');
 }
 for(const d of doors.values()){
  const expected=[...pairs.values()].filter(p=>p.door_ids.includes(d.id)).map(p=>p.id);
  require(same(d.interlock_pair_ids,expected),'Door pairing differs');
  require(same(d.interaction.rules.slice(4),expected.length?['paired_airlock_peer_closed_stopped']:[]),'Door rules differ');
 }
 const nav=m.navigation;require(nav?.kind==='horizontal_supported_walking'&&rooms.get(nav.entry_room_id)?.access==='walkable_layout'&&vec(nav.spawn_feet)&&nav.spawn_feet[1]===0,'Unsupported navigation/spawn');
 const entry=rooms.get(nav.entry_room_id),expected=entry.bounds.min.map((v,i)=>i===1?v:(v+entry.bounds.max[i])/2);
 require(nearArray(nav.spawn_feet,expected),'Spawn is not the declared entry center');
 require(Array.isArray(nav.support_surfaces)&&nav.support_surfaces.length<=128&&nav.support_surfaces.every(s=>s.y===0),'Unsupported support');
 require(Array.isArray(nav.authored_routes)&&nav.authored_routes.length<=128,'Invalid route list');
 return {rooms,nodes,colliders,doors,pairs};
}
export function createDoorRuntime(metadata,{isCurrent=()=>true}={}){
 require(typeof isCurrent==='function','Current runtime callback required');
 let disposed=false;const latchResults=new Map();
 function current(){let valid=false;try{valid=!disposed&&isCurrent()===true;}catch{}if(!valid){disposed=true;for(const s of states.values())s.latch?.dispose();}return valid;}
 const m=structuredClone(metadata),maps=validateMetadata(m),states=new Map([...maps.doors.values()].map(d=>[d.id,{d,angle:0,target:0,moving:false,held:false}]));
 for(const s of states.values())if(s.d.variant===LATCH_HATCH_CONTRACT)s.latch=createLatchAuthority({id:s.d.id,openAngle:s.d.hinge.open_angle,readDoor:()=>({id:s.d.id,angle:s.angle,target:s.target,moving:s.moving,motionHeld:s.held}),isCurrent:()=>!disposed&&isCurrent()===true});
 function pose(s){
  const h=s.d.hinge,p=h.leaf_local_center,c=Math.cos(s.angle),sin=Math.sin(s.angle);
  const center=[h.position[0]+c*p[0]+sin*p[2],h.position[1]+p[1],h.position[2]-sin*p[0]+c*p[2]];
  const colliders=movingForDoor(s.d,maps.colliders).map(c=>({id:c.id,ownerNodeId:c.owner_node_id,...rotateBounds(c.bounds,h.position,s.angle)}));
  const body=colliders.filter(c=>c.ownerNodeId===s.d.leaf_node_id);
  return freeze({id:s.d.id,angle:s.angle,target:s.target,moving:s.moving,motionHeld:s.held,state:s.moving?(s.target===0?'closing':'opening'):(s.angle===0?'closed':'open'),center,collider:{id:'runtime:'+s.d.id,...unionBounds(body)},colliders});
 }
 function adjacent(d,feet){return d.room_ids.some(id=>{const b=maps.rooms.get(id).bounds;return feet[1]===b.min[1]&&feet[0]>=b.min[0]-EPS&&feet[0]<=b.max[0]+EPS&&feet[2]>=b.min[2]-EPS&&feet[2]<=b.max[2]+EPS;});}
 function middle(d){return d.hinge.position.map((v,i)=>v+d.hinge.leaf_local_center[i]);}
 function distance(d,feet){const p=middle(d);return Math.hypot(feet[0]-p[0],feet[2]-p[2]);}
 function near(d,feet){return adjacent(d,feet)&&distance(d,feet)<=d.interaction.maximum_reach_m;}
 function all(){return freeze([...states.values()].map(pose));}
 function nearest(feet){require(vec(feet),'Invalid interaction position');const found=[...states.values()].filter(s=>near(s.d,feet)).sort((a,b)=>distance(a.d,feet)-distance(b.d,feet)||a.d.id.localeCompare(b.d.id));return found.length?pose(found[0]):null;}
 function toggle(id,feet){
  require(vec(feet),'Invalid interaction position');if(!current())return {ok:false,reason:'Door runtime is no longer current.'};const s=states.get(id);
  if(s?.latch){const gate=s.latch.canMove();if(!gate.ok)return gate;}
  if(!s||!near(s.d,feet))return {ok:false,reason:'Move closer to the door.'};
  if(s.moving)return {ok:false,reason:'Wait for the door to finish moving.'};
  if(overlap(s.d.swing_bounds,feet))return {ok:false,reason:'Step back from the door swing before moving it.'};
  if(s.angle===0)for(const pairId of s.d.interlock_pair_ids){const pair=maps.pairs.get(pairId),peer=states.get(pair.door_ids.find(k=>k!==id));
   if(peer.angle!==0||peer.moving||peer.target!==0||peer.held)return {ok:false,reason:'Close the other airlock door completely before opening this one.',interlock:{contract:POLICY,roomId:pair.room_id,peerDoorId:peer.d.id}};
  }
  s.target=s.angle===0?s.d.hinge.open_angle:0;s.moving=true;s.held=false;return {ok:true,id,state:s.target===0?'closing':'opening'};
 }
 function advance(seconds,feet){
  require(num(seconds)&&seconds>=0&&vec(feet),'Invalid simulation input');
  if(!current())return all();
  for(const s of states.values())if(s.latch){const result=s.latch.advance(Math.min(seconds,.05));if(result.ok){const intent=s.latch.takeOpenIntent();if(intent.ok&&intent.ready)latchResults.set(s.d.id,toggle(s.d.id,feet));}}
  for(const s of states.values())if(s.moving){if(s.latch&&!s.latch.canMove().ok){s.held=true;continue;}s.held=overlap(s.d.swing_bounds,feet);if(s.held)continue;
   const amount=Math.min(seconds,s.d.max_step_seconds)*s.d.angular_speed_rad_s,remaining=s.target-s.angle;
   if(Math.abs(remaining)<=amount){s.angle=s.target;s.moving=false;s.held=false;}else s.angle+=Math.sign(remaining)*amount;
  }return all();
 }
 function latchCommand(id,feet,action,value){
  require(vec(feet),'Invalid latch interaction position');if(!current())return {ok:false,reason:'Door runtime is no longer current.'};
  const s=states.get(id);if(!s?.latch||!near(s.d,feet))return {ok:false,reason:'Move closer to the nominated latched hatch.'};
  latchResults.delete(id);return action==='open'?s.latch.releaseForOpening():s.latch.request(value);
 }
 return Object.freeze({all,nearest,toggle,advance,colliders:()=>all().flatMap(p=>p.colliders),
  requestLatch:(id,value,feet)=>latchCommand(id,feet,'pose',value),releaseAndOpen:(id,feet)=>latchCommand(id,feet,'open'),
  latchStates:()=>freeze([...states.values()].filter(s=>s.latch).map(s=>({...s.latch.snapshot(),lastOpenResult:latchResults.get(s.d.id)??null}))),
  pauseLatches:reason=>{for(const s of states.values())s.latch?.pause(reason);},resumeLatches:reason=>{for(const s of states.values())s.latch?.resume(reason);},
  dispose(){if(!disposed){disposed=true;for(const s of states.values())s.latch?.dispose();}}});
}
export function createRuntime(metadata,{isCurrent=()=>true}={}){
 const m=structuredClone(metadata);validateMetadata(m);const doors=createDoorRuntime(m,{isCurrent});
 const fixed=m.colliders.filter(c=>c.motion==='static').map(c=>({id:c.id,...c.bounds}));
 // Existing support algorithm caps each scene at 128 colliders. Every chunk is
 // checked; chunking does not omit equipment or merge bounding boxes.
 const chunks=[];for(let i=0;i<fixed.length;i+=128)chunks.push(fixed.slice(i,i+128));
 const movingChunks=()=>{const all=doors.colliders(),out=[];for(let i=0;i<all.length;i+=128)out.push(all.slice(i,i+128));return out;};
 const nav=colliders=>({contract:NAVIGATION_CONTRACT,support_surfaces:m.navigation.support_surfaces,colliders});
 let feet=[...m.navigation.spawn_feet],yaw=0,pitch=0,blocked=null,distance=0;
 for(const colliders of [...chunks,...movingChunks()])require(checkWalkSpawn(feet,nav(colliders)).ok,'Spawn intersects a collider or unsupported floor');
 const first=m.navigation.authored_routes.find(r=>r.points.some(p=>nearArray(p,feet)));
 if(first){const i=first.points.findIndex(p=>nearArray(p,feet)),next=first.points[i+1]||first.points[i-1];if(next)yaw=Math.atan2(next[0]-feet[0],-(next[2]-feet[2]));}
 function snapshot(){const room=m.rooms.find(r=>r.access==='walkable_layout'&&feet[0]>=r.bounds.min[0]&&feet[0]<=r.bounds.max[0]&&feet[2]>=r.bounds.min[2]&&feet[2]<=r.bounds.max[2]);return freeze({feet:[...feet],yaw,pitch,blocked,distance,roomId:room?.id||null,roomName:room?.label||'Passage',nearbyDoor:doors.nearest(feet)});}
 function look(dx,dy){require(num(dx)&&num(dy),'Invalid look input');yaw+=Math.max(-500,Math.min(500,dx))*.002;pitch=Math.max(-1.2,Math.min(1.2,pitch-Math.max(-500,Math.min(500,dy))*.002));return snapshot();}
 function checkRoute(start,end){
  const route={id:'consumer_walk',avatar_radius:AVATAR.radius,avatar_height:AVATAR.height,points:[start,end]};
  for(const colliders of [...chunks,...movingChunks()]){const r=checkHorizontalRoute(route,nav(colliders));if(r.status!=='clear')return r;}return {status:'clear'};
 }
 function step(seconds,input={}){
  require(num(seconds)&&seconds>=0,'Invalid elapsed time');const dt=Math.min(seconds,.05);doors.advance(dt,feet);
  yaw+=((input.turnRight?1:0)-(input.turnLeft?1:0))*1.65*dt;
  const forward=(input.forward?1:0)-(input.backward?1:0),side=(input.right?1:0)-(input.left?1:0);if(!forward&&!side)return snapshot();
  const scale=2.2*dt/Math.max(1,Math.hypot(forward,side)),end=[feet[0]+(Math.sin(yaw)*forward+Math.cos(yaw)*side)*scale,feet[1],feet[2]+(-Math.cos(yaw)*forward+Math.sin(yaw)*side)*scale];
  const r=checkRoute(feet,end);blocked=r.status==='clear'?null:r.reason;
  if(!blocked){distance+=Math.hypot(end[0]-feet[0],end[2]-feet[2]);feet=end;}return snapshot();
 }
 return Object.freeze({contract:CONTRACT,snapshot,look,step,checkRoute,doorStates:doors.all,toggleDoor:id=>doors.toggle(id||doors.nearest(feet)?.id,feet),requestLatch:(id,value)=>doors.requestLatch(id,value,feet),releaseAndOpen:id=>doors.releaseAndOpen(id,feet),latchStates:doors.latchStates,pauseLatches:doors.pauseLatches,resumeLatches:doors.resumeLatches,dispose:doors.dispose});
}
