// Small user-requested commands over the unchanged portable runtime.
import {HATCH} from './door_metadata.mjs';
import {LATCH_HATCH_CONTRACT} from './shared/latched_metadata.mjs';
export const STEP_METERS=.33;
export const TURN_RADIANS=Math.PI/12;
const finite=n=>typeof n==='number'&&Number.isFinite(n);
const inputs=Object.freeze({forward:'forward',backward:'backward',left:'left',right:'right',turnLeft:'turnLeft',turnRight:'turnRight'});
export function describeNearbyDoor(metadata,snapshot){
 const near=snapshot?.nearbyDoor;if(!near)return null;
 const door=metadata?.doors?.find(d=>d.id===near.id),kind=[HATCH,LATCH_HATCH_CONTRACT].includes(door?.variant)?'hatch':'door';
 const label=id=>metadata?.rooms?.find(r=>r.id===id)?.label||id;
 let target='nearby '+kind;
 if(door?.room_ids?.includes(snapshot.roomId))target=kind+' to '+label(door.room_ids.find(id=>id!==snapshot.roomId));
 else if(door?.room_ids?.length===2)target=kind+' between '+door.room_ids.map(label).join(' and ');
 return Object.freeze({id:near.id,target,state:near.state,button:near.moving?'Continue '+target:(near.state==='closed'?'Open ':'Close ')+target});
}
export function discreteAction(runtime,action){
 if(!runtime||typeof runtime.step!=='function'||typeof runtime.snapshot!=='function')throw new TypeError('A portable runtime is required.');
 if(typeof action!=='string')throw new TypeError('Unknown step control.');
 const before=runtime.snapshot();
 if(action==='lookUp'||action==='lookDown'){
  if(typeof runtime.look!=='function')throw new TypeError('Look control unavailable.');
  runtime.look(0,action==='lookUp'?-100:100);
 }else{
  if(!Object.hasOwn(inputs,action))throw new TypeError('Unknown step control.');
  const turn=action==='turnLeft'||action==='turnRight';
  let remaining=turn?TURN_RADIANS/1.65:STEP_METERS/2.2;
  // Every slice uses ordinary floor, equipment, door and swept-route checks.
  for(let count=0;remaining>1e-10&&count<4;count++){
   const dt=Math.min(.05,remaining);runtime.step(dt,{[inputs[action]]:true});remaining-=dt;
   if(!turn&&runtime.snapshot().blocked)break;
  }
 }
 return Object.freeze({action,before,after:runtime.snapshot()});
}

// Animate stationary door motion separately from keyboard locomotion. No timer
// or request is scheduled on import, construction, cancellation or completion.
export function createDoorMotionSequence({requestFrame,cancelFrame,now,onFrame=()=>{},onDone=()=>{}}){
 if([requestFrame,cancelFrame,now,onFrame,onDone].some(f=>typeof f!=='function'))throw new TypeError('Frame callbacks are required.');
 const moving=runtime=>runtime.doorStates().some(d=>d.moving)||(runtime.latchStates?.()??[]).some(s=>!s.fault&&!s.paused&&s.fraction!==s.target);
 let revision=0,handle=null,running=false;
 function cancel(){revision++;running=false;if(handle!==null)cancelFrame(handle);handle=null;}
 function start(runtime){
  cancel();if(!runtime||typeof runtime.step!=='function'||typeof runtime.doorStates!=='function')throw new TypeError('A door runtime is required.');
  if(!moving(runtime))return false;
  const started=now();if(!finite(started))throw new TypeError('A finite monotonic clock is required.');
  const token=revision;let last=null,frames=0;running=true;
  function finish(reason){if(token!==revision)return;running=false;handle=null;onDone({runtime,reason});}
  function tick(time){
   if(token!==revision||!running)return;handle=null;
   // The frame timestamp can precede performance.now() sampled in the click.
   // Establish its own baseline once; later frames must remain monotonic.
   const current=now();
   if(!finite(time)||!finite(current)||current<started||(last!==null&&time<last)||Math.max(current,time)-started>2000||frames++>=120){finish('interrupted');return;}
   try{runtime.step(Math.min(Math.max(0,(time-(last??started))/1000),.05),{});last=time;onFrame({runtime});}
   catch(error){finish('error');return;}
   if(token!==revision||!running)return;
   const doors=runtime.doorStates();
   if(doors.some(d=>d.moving&&d.motionHeld)){finish('occupied');return;}
   if(!moving(runtime)){finish('settled');return;}
   handle=requestFrame(tick);
  }
  handle=requestFrame(tick);return true;
 }
 return Object.freeze({start,cancel,isRunning:()=>running});
}
