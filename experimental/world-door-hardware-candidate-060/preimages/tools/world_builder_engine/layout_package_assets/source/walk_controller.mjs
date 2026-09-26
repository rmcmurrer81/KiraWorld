import {NAVIGATION_CONTRACT, checkWalkSpawn, checkHorizontalRoute} from './horizontal_navigation.mjs';

export const AVATAR = Object.freeze({radius: 0.34, height: 1.68, eye: 1.56});

// Preview-local moving doors. The immutable source geometry is never changed.
// Rendering and collision both use pose(); motion uses a conservative sweep
// volume so a door cannot close through the walker between animation frames.
export const DOOR_CONTRACT = 'preview_hinged_doors_v2';
export const AIRLOCK_SEQUENCE_CONTRACT = 'paired_airlock_door_sequence_v1';
const DOOR_THICKNESS=.065, FRAME_WIDTH=.07, FRAME_DEPTH=.21, REACH=2.25;
const freeze=value=>Object.freeze(value);
const vector=(v)=>Array.isArray(v)&&v.length===3&&v.every(n=>Number.isFinite(n)&&Math.abs(n)<1e6);
function ensure(ok,message){if(!ok)throw new TypeError(message);}
function bounds(center,size){return {min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)};}
function overlapAvatar(box,feet,radius,height){
  return feet[1]<box.max[1]&&feet[1]+height>box.min[1]&&
    feet[0]+radius>=box.min[0]&&feet[0]-radius<=box.max[0]&&
    feet[2]+radius>=box.min[2]&&feet[2]-radius<=box.max[2];
}
export function createDoorSystem(geometry){
  ensure(Array.isArray(geometry.rooms)&&Array.isArray(geometry.portals)&&geometry.portals.length<=24,'Invalid door geometry');
  const rooms=new Map(geometry.rooms.map(r=>[r.id,r])),doors=new Map(),seen=new Set();
  for(const portal of geometry.portals){
    ensure(typeof portal.id==='string'&&/^[a-z][a-z0-9_]{0,63}$/.test(portal.id)&&!seen.has(portal.id),'Invalid or duplicate door id');seen.add(portal.id);
    const a=rooms.get(portal.room_a),b=rooms.get(portal.room_b);
    ensure(a&&b&&a!==b,'Door rooms are unavailable');
    if(a.access!=='walkable_layout'||b.access!=='walkable_layout'){
      ensure(portal.state==='closed_locked_solid','Locked room cannot gain a door');continue;
    }
    ensure(portal.state==='open_passage'&&(portal.axis==='x'||portal.axis==='z'),'Unsupported door passage');
    const {axis,coordinate,center,width,height}=portal;
    ensure([coordinate,center,width,height,a.floor_y,b.floor_y].every(Number.isFinite)&&
      a.floor_y===b.floor_y&&width>=.9&&width<=8&&height>=1.9&&height<=Math.min(a.height,b.height),'Invalid door dimensions');
    const along=axis==='x'?'z':'x',length=axis==='x'?'depth':'width',normalSize=axis==='x'?'width':'depth';
    ensure((Math.abs(a[axis]+a[normalSize]-coordinate)<1e-8&&Math.abs(b[axis]-coordinate)<1e-8)||
      (Math.abs(b[axis]+b[normalSize]-coordinate)<1e-8&&Math.abs(a[axis]-coordinate)<1e-8),'Door is not on shared wall');
    ensure(center-width/2>=Math.max(a[along],b[along])+.15-1e-8&&
      center+width/2<=Math.min(a[along]+a[length],b[along]+b[length])-.15+1e-8,'Door exceeds shared wall');
    // Keep door travel smaller than the room into which it swings.
    const roomDepth=a[normalSize];
    ensure(width+.1<roomDepth,'Door swing exceeds its room');
    const sign=Math.sign(a[axis]+a[normalSize]/2-coordinate);
    const hinge=axis==='x'?[coordinate,a.floor_y,center-width/2+.02]:[center-width/2+.02,a.floor_y,coordinate];
    const frame=[];
    for(const [part,span,y,h] of [['left',center-width/2-FRAME_WIDTH/2,a.floor_y,height],
                                 ['right',center+width/2+FRAME_WIDTH/2,a.floor_y,height],
                                 ['head',center,a.floor_y+height,FRAME_WIDTH]]){
      const horizontal=part==='head'?width+2*FRAME_WIDTH:FRAME_WIDTH;
      const p=axis==='x'?[coordinate,y+h/2,span]:[span,y+h/2,coordinate];
      const size=axis==='x'?[FRAME_DEPTH,h,horizontal]:[horizontal,h,FRAME_DEPTH];
      const box=bounds(p,size);
      frame.push(freeze({id:'door_'+portal.id+'_'+part,center:freeze(p),size:freeze(size),min:freeze(box.min),max:freeze(box.max)}));
    }
    const door={id:portal.id,portal:{...portal},roomA:{...a},roomB:{...b},hinge,
      width:width-.04,height:height-.025,floor:a.floor_y,axis,targetAngle:sign*(axis==='x'?1:-1)*Math.PI/2,
      angle:0,target:0,moving:false,motionHeld:false,frames:frame};
    // A quarter-disc bounds every intermediate point of the rotating leaf.
    // Include thickness and the walker footprint; do not sample a few angles.
    const extent=door.width+DOOR_THICKNESS/2;
    const minimum=[hinge[0]-DOOR_THICKNESS/2,a.floor_y,hinge[2]-DOOR_THICKNESS/2];
    const maximum=[hinge[0]+DOOR_THICKNESS/2,a.floor_y+height,hinge[2]+DOOR_THICKNESS/2];
    const n=axis==='x'?0:2,t=axis==='x'?2:0;
    maximum[t]=hinge[t]+extent;
    if(sign>0)maximum[n]=hinge[n]+extent;else minimum[n]=hinge[n]-extent;
    door.sweep={min:minimum,max:maximum};doors.set(door.id,door);
  }
  // Only an explicit authored role opts in. Names, decorations and room IDs do
  // not imply an airlock. This is mutual exclusion, not pressure simulation.
  const airlockPairs=[],interlockedPeers=new Map();
  const program=geometry.functional_program;
  if(program!==undefined&&program!==null)ensure(typeof program==='object'&&!Array.isArray(program),'Invalid authored room program');
  for(const [roomId,role] of Object.entries(program||{})){
    if(role!=='airlock')continue;
    const room=rooms.get(roomId);ensure(room&&room.access==='walkable_layout','Authored airlock room is unavailable');
    const members=[...doors.values()].filter(d=>d.portal.room_a===roomId||d.portal.room_b===roomId);
    ensure(members.length===2,'Authored airlock must have exactly two supported doors: '+roomId);
    airlockPairs.push(freeze({roomId,doorIds:freeze(members.map(d=>d.id)),contract:AIRLOCK_SEQUENCE_CONTRACT,
      pressureSimulation:false,statePersistence:'session_local'}));
    for(const door of members){
      const peer=members.find(d=>d!==door),peerRoom=peer.portal.room_a===roomId?peer.roomB:peer.roomA;
      if(!interlockedPeers.has(door.id))interlockedPeers.set(door.id,[]);
      interlockedPeers.get(door.id).push({door:peer,roomId,destination:peerRoom.name});
    }
  }
  function interlocks(){return freeze([...airlockPairs]);}
  function poseOf(door){
    const c=Math.cos(door.angle),s=Math.sin(door.angle),tx=door.axis==='x'?s:c,tz=door.axis==='x'?c:-s;
    const nx=door.axis==='x'?c:s,nz=door.axis==='x'?-s:c;
    const center=[door.hinge[0]+tx*door.width/2,door.floor+.0125+door.height/2,door.hinge[2]+tz*door.width/2];
    const size=door.axis==='x'?[DOOR_THICKNESS,door.height,door.width]:[door.width,door.height,DOOR_THICKNESS];
    const aabbSize=[Math.abs(tx)*door.width+Math.abs(nx)*DOOR_THICKNESS,door.height,Math.abs(tz)*door.width+Math.abs(nz)*DOOR_THICKNESS];
    const state=door.moving?(door.target===0?'closing':'opening'):(door.angle===0?'closed':'open');
    return freeze({id:door.id,axis:door.axis,angle:door.angle,center:freeze(center),size:freeze(size),state,motionHeld:door.motionHeld,
      collider:freeze({id:'door_'+door.id+'_leaf',...bounds(center,aabbSize)})});
  }
  function all(){return freeze([...doors.values()].map(d=>poseOf(d)));}
  function assemblies(){return freeze([...doors.values()].map(d=>freeze({id:d.id,axis:d.axis,frames:freeze(d.frames),
    swingBounds:freeze({min:freeze([...d.sweep.min]),max:freeze([...d.sweep.max])}),roomA:d.roomA.name,roomB:d.roomB.name})));}
  function colliders(){return [...doors.values()].flatMap(d=>[...d.frames.map(f=>({id:f.id,min:[...f.min],max:[...f.max]})),poseOf(d).collider]);}
  function near(door,feet){
    if(Math.abs(feet[1]-door.floor)>1e-8)return false;
    const inside=r=>feet[0]>=r.x-1e-8&&feet[0]<=r.x+r.width+1e-8&&feet[2]>=r.z-1e-8&&feet[2]<=r.z+r.depth+1e-8;
    if(!inside(door.roomA)&&!inside(door.roomB))return false;
    const p=door.portal;const x=p.axis==='x'?p.coordinate:p.center,z=p.axis==='x'?p.center:p.coordinate;
    return Math.hypot(feet[0]-x,feet[2]-z)<=REACH;
  }
  function nearest(feet,yaw=null){
    ensure(vector(feet),'Invalid door interaction position');
    ensure(yaw===null||Number.isFinite(yaw),'Invalid door interaction direction');
    const candidates=[...doors.values()].filter(d=>{
      if(!near(d,feet))return false;
      if(yaw===null)return true; // Explicit low-level callers retain proximity queries.
      const dx=(d.axis==='x'?d.portal.coordinate:d.portal.center)-feet[0];
      const dz=(d.axis==='x'?d.portal.center:d.portal.coordinate)-feet[2];
      const distance=Math.hypot(dx,dz);
      // The walking camera looks along [sin(yaw),0,-cos(yaw)]. A door behind
      // the user must not win F/button selection merely because it is closer.
      return distance<1e-8||(dx*Math.sin(yaw)-dz*Math.cos(yaw))/distance>=.5;
    });
    candidates.sort((a,b)=>{
      const dist=d=>Math.hypot(feet[0]-(d.axis==='x'?d.portal.coordinate:d.portal.center),feet[2]-(d.axis==='x'?d.portal.center:d.portal.coordinate));
      return dist(a)-dist(b)||a.id.localeCompare(b.id);
    });
    return candidates.length?poseOf(candidates[0]):null;
  }
  function toggle(id,feet,radius=AVATAR.radius,height=AVATAR.height){
    ensure(vector(feet)&&Number.isFinite(radius)&&radius>=.2&&radius<=.6&&Number.isFinite(height)&&height>.5&&height<=3,'Invalid door interaction');
    const door=doors.get(id);
    if(!door||!near(door,feet))return freeze({ok:false,reason:'Move closer to the door.'});
    if(door.moving)return freeze({ok:false,reason:'Wait for the door to finish moving.'});
    if(overlapAvatar(door.sweep,feet,radius,height))return freeze({ok:false,reason:'Step back from the door swing before moving it.'});
    // Only opening is interlocked. Closing retains the original sweep/motion
    // rules, allowing the user to restore a closed pair. Moving/target/held also
    // reserve the peer at angle zero, so same-frame requests cannot open both.
    if(door.angle===0){
      const blocked=(interlockedPeers.get(id)||[]).find(p=>p.door.angle!==0||p.door.moving||p.door.target!==0||p.door.motionHeld);
      if(blocked)return freeze({ok:false,reason:'The door to '+blocked.destination+' must be fully closed and stopped before opening this airlock door.',
        interlock:freeze({contract:AIRLOCK_SEQUENCE_CONTRACT,roomId:blocked.roomId,peerDoorId:blocked.door.id})});
    }
    door.target=door.angle===0?door.targetAngle:0;door.moving=true;door.motionHeld=false;
    return freeze({ok:true,id,state:door.target===0?'closing':'opening'});
  }
  function advance(seconds,feet,radius=AVATAR.radius,height=AVATAR.height){
    ensure(Number.isFinite(seconds)&&seconds>=0&&vector(feet),'Invalid door time or position');
    for(const door of doors.values()){
      if(!door.moving)continue;
      door.motionHeld=overlapAvatar(door.sweep,feet,radius,height);
      if(door.motionHeld)continue;
      const step=Math.min(seconds,.05)*Math.PI*1.25,remaining=door.target-door.angle;
      if(Math.abs(remaining)<=step){door.angle=door.target;door.moving=false;door.motionHeld=false;}
      else door.angle+=Math.sign(remaining)*step;
    }
    return all();
  }
  // Authoring metadata only: independent of current session angles/state.
  // Export the same dimensions/hinges used by pose/collision, not inferred meshes.
  function definitions(){return freeze([...doors.values()].map(d=>freeze({
    id:d.id,portalId:d.id,roomAId:d.portal.room_a,roomBId:d.portal.room_b,
    hinge:freeze([...d.hinge]),rotationAxis:freeze([0,1,0]),closedAngle:0,openAngle:d.targetAngle,
    leafSize:freeze(d.axis==='x'?[DOOR_THICKNESS,d.height,d.width]:[d.width,d.height,DOOR_THICKNESS]),
    leafLocalCenter:freeze(d.axis==='x'?[0,.0125+d.height/2,d.width/2]:[d.width/2,.0125+d.height/2,0]),
    angularSpeed:Math.PI*1.25,maxStepSeconds:.05,interactionReach:REACH,
    frames:freeze(d.frames.map(f=>freeze({id:f.id,center:freeze([...f.center]),size:freeze([...f.size])}))),
    swingBounds:freeze({min:freeze([...d.sweep.min]),max:freeze([...d.sweep.max])}),
    collisionPolicy:'conservative_rotated_leaf_aabb_and_quarter_disc_sweep',
    initialState:'closed',statePersistence:'session_local',pressureSimulation:false
  })));}
  return freeze({contract:DOOR_CONTRACT,all,assemblies,definitions,colliders,nearest,toggle,advance,interlocks});
}

export function createWalkController(geometry,{extraColliders=[]}={}) {
  const nav = {contract:NAVIGATION_CONTRACT, support_surfaces:geometry.support_surfaces, colliders:geometry.colliders};
  const doors=createDoorSystem(geometry);
  const doorNav=()=>({contract:NAVIGATION_CONTRACT,support_surfaces:geometry.support_surfaces,colliders:doors.colliders()});
  ensure(Array.isArray(extraColliders)&&extraColliders.length<=128,'Invalid extra collider collection');
  const occupiedIds=new Set([...geometry.colliders,...doors.colliders()].map(c=>c.id));
  const extra=extraColliders.map(c=>{
    ensure(c&&typeof c.id==='string'&&c.id&&!occupiedIds.has(c.id)&&vector(c.min)&&vector(c.max)&&c.min.every((v,i)=>v<c.max[i]),'Invalid or duplicate extra collider');
    occupiedIds.add(c.id);return freeze({id:c.id,min:freeze([...c.min]),max:freeze([...c.max])});
  });
  const furnitureNav={contract:NAVIGATION_CONTRACT,support_surfaces:geometry.support_surfaces,colliders:extra};
  for(const assembly of doors.assemblies())for(const collider of extra){
    const sweep=assembly.swingBounds;
    ensure(!collider.min.every((v,i)=>v<sweep.max[i]&&collider.max[i]>sweep.min[i]),'Furniture blocks a door swing: '+collider.id);
  }
  const room = geometry.rooms.find(r => r.id === geometry.connectivity.entry_room_id);
  if (!room || room.access !== 'walkable_layout') throw new Error('The entry room is unavailable for walking.');
  let feet = [room.x + room.width / 2, room.floor_y, room.z + room.depth / 2];
  const spawn = checkWalkSpawn(feet, nav, AVATAR.radius, AVATAR.height);
  if (!spawn.ok) throw new Error('No supported entry position: ' + spawn.reason);
  if(!checkWalkSpawn(feet,doorNav(),AVATAR.radius,AVATAR.height).ok)throw new Error('Entry position intersects a door assembly.');
  if(extra.length&&!checkWalkSpawn(feet,furnitureNav,AVATAR.radius,AVATAR.height).ok)throw new Error('Entry position intersects furnished geometry.');
  let yaw = 0, pitch = 0, blocked = null, distance = 0;
  const first = geometry.routes.find(r => r.points.some(p => p.every((v,i) => v === feet[i])));
  if (first) {
    const index = first.points.findIndex(p => p.every((v,i) => v === feet[i]));
    const next = first.points[index + 1] || first.points[index - 1];
    if (next) yaw = Math.atan2(next[0] - feet[0], -(next[2] - feet[2]));
  }
  function snapshot() {
    const current = geometry.rooms.find(r => r.access === 'walkable_layout' && r.floor_y === feet[1] &&
      feet[0] >= r.x && feet[0] <= r.x+r.width && feet[2] >= r.z && feet[2] <= r.z+r.depth);
    return Object.freeze({feet:Object.freeze([...feet]), yaw, pitch, blocked, distance,
      roomId:current?.id || null, roomName:current?.name || 'Passage',nearbyDoor:doors.nearest(feet,yaw)});
  }
  function look(dx,dy) {
    if (!Number.isFinite(dx) || !Number.isFinite(dy)) throw new TypeError('Invalid look input');
    yaw += Math.max(-500,Math.min(500,dx))*0.002;
    pitch = Math.max(-1.2, Math.min(1.2,pitch-Math.max(-500,Math.min(500,dy))*0.002));
    return snapshot();
  }
  function step(seconds,input={}) {
    if (!Number.isFinite(seconds) || seconds < 0) throw new TypeError('Invalid elapsed time');
    const dt=Math.min(seconds,0.05);
    doors.advance(dt,feet);
    yaw += ((input.turnRight ? 1:0)-(input.turnLeft ? 1:0))*1.65*dt;
    const forward=(input.forward ? 1:0)-(input.backward ? 1:0);
    const side=(input.right ? 1:0)-(input.left ? 1:0);
    if (!forward && !side) return snapshot();
    blocked=null;
    const scale=2.2*dt/Math.max(1,Math.hypot(forward,side));
    const end=[feet[0]+(Math.sin(yaw)*forward+Math.cos(yaw)*side)*scale,feet[1],
      feet[2]+(-Math.cos(yaw)*forward+Math.sin(yaw)*side)*scale];
    const route={id:'interactive_walk',avatar_radius:AVATAR.radius,avatar_height:AVATAR.height,points:[feet,end]};
    let result=checkHorizontalRoute(route,nav);
    if(result.status==='clear'){
      result=checkHorizontalRoute(route,doorNav());
      if(result.status!=='clear'&&result.reason==='solid_obstruction')result={...result,reason:'door_obstruction'};
    }
    if(result.status==='clear'&&extra.length){
      result=checkHorizontalRoute(route,furnitureNav);
      if(result.status!=='clear'&&result.reason==='solid_obstruction')result={...result,reason:'furniture_obstruction'};
    }
    if (result.status === 'clear') {distance+=Math.hypot(end[0]-feet[0],end[2]-feet[2]);feet=end;}
    else blocked=result.reason;
    return snapshot();
  }
  // No direct-position setter, fly mode, level snapping, or teleport route.
  function toggleDoor(id){
    const selected=id||doors.nearest(feet,yaw)?.id;
    if(!selected)return freeze({ok:false,reason:'Face a nearby door to open or close it.'});
    return doors.toggle(selected,feet);
  }
  return Object.freeze({snapshot,step,look,toggleDoor,doorAssemblies:doors.assemblies,doorStates:doors.all});
}
