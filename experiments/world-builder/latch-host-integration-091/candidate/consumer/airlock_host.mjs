import {bindAirlockCycle,createAirlockCycle} from './airlock_cycle.mjs';
import {reviewedLatchedPackage} from './reviewed_latched_packages.mjs';
// These explicit nominations describe the two already admitted packages, not a
// generic guess from room order/name. "mars" is an internal081 symbolic enum;
// this UI ALWAYS calls that side Equipment Vestibule, never Mars exterior.
const nominations=new Map([
 ['bf7f0934f473b5ad7b0a50f2577c50995f94d3880db30835b4bf0194bdd074cc',{pairId:'airlock_pair:airlock',insideDoorId:'door:opening_2',outsideDoorId:'door:opening_1'}]
]);
// Legacy package has no UI nomination; its underlying paired-door interlock is
// preserved. This sidecar does not widen loader/source admission.
export function createAirlockHost(loaded,{requestFrame,cancelFrame,onChange=()=>{},getCurrent=()=>loaded}={}){
 const reviewed=reviewedLatchedPackage(loaded?.manifestSha256);
 const nomination=nominations.get(loaded?.manifestSha256)??reviewed?.airlock_nomination;
 if(reviewed&&!nomination)throw new TypeError('New v2 package requires exact reviewed side nomination');
 if(!nomination)return null;
 const runtime=loaded.runtime,metadata=loaded.metadata;
 const binding=bindAirlockCycle(metadata,{...nomination,manifestSha256:loaded.manifestSha256,sceneSha256:loaded.manifest.files['scene.json'].sha256,roleAssignment:'explicit_fictional_habitat_mars'});
 const labels=Object.fromEntries(Object.entries(binding.ports).map(([side,port])=>[side,metadata.rooms.find(r=>r.id===port.adjacentRoomId).label]));
 const sides=new Map(Object.entries(binding.ports).map(([side,port])=>[port.doorId,side]));
 let observationValid=true,disposed=false,revision=0,frame=null,last=null,frames=0,token=null;
 const holds=new Set(['manual']);
 const cycle=createAirlockCycle({binding,runtimeIdentity:runtime,
  readDoors(){observationValid=false;if(disposed||getCurrent()!==loaded)throw Error('Loaded package changed');const all=runtime.doorStates(),doors=[...sides.keys()].map(id=>all.find(d=>d.id===id));if(doors.some(d=>!d))throw Error('Door observation unavailable');for(const d of doors){const p=binding.ports[sides.get(d.id)];if(!Number.isFinite(d.angle)||d.angle*p.openAngle<0||Math.abs(d.angle)>Math.abs(p.openAngle)||![0,p.openAngle].includes(d.target)||typeof d.moving!=='boolean'||typeof d.motionHeld!=='boolean')throw Error('Door observation invalid');}observationValid=true;return {runtimeIdentity:runtime,manifestSha256:loaded.manifestSha256,sceneSha256:loaded.manifest.files['scene.json'].sha256,sceneId:metadata.scene_id,doors};},
  toggleDoor:id=>runtime.toggleDoor(id)});
 function snapshot(){const s=cycle.snapshot();return {...s,labels:{...labels},observationValid:!disposed&&observationValid,pauseReasons:[...holds],running:token!==null};}
 function revoke(){revision++;if(frame!==null)cancelFrame(frame);frame=null;token=null;last=null;frames=0;}
 function pause(reason='manual'){if(disposed)return;holds.add(reason);revoke();cycle.pause();}
 function clear(reason){holds.delete(reason);}
 function inRange(){const s=runtime.snapshot();return s.roomId===binding.roomId||sides.has(s.nearbyDoor?.id);}
 function update(){if(disposed)return null;if(!inRange())pause('room');else clear('room');return snapshot();}
 function schedule(runToken){
  revoke();token=runToken;const mine=revision;
  function tick(time){
   if(disposed||mine!==revision||!token)return;frame=null;
   if(getCurrent()!==loaded||!inRange()){pause('room');onChange();return;}
   if(typeof time!=='number'||!Number.isFinite(time)||time<0||(last!==null&&time<last)||frames++>=1800){pause('clock');onChange();return;}
   const dt=last===null?0:Math.min((time-last)/1000,.05);last=time;
   const result=cycle.advance(token,dt);
   if(!result.ok||result.complete){revoke();onChange();return;}
   onChange();if(!disposed&&mine===revision&&token)frame=requestFrame(tick);
  }
  frame=requestFrame(tick);
 }
 function explicitReady(){
  update();if(disposed)return {ok:false,reason:'Disposed airlock session'};
  // Clear only acknowledgement-level holds. Hidden/blur/room holds require
  // their actual lifecycle event to clear, and never auto-resume the clock.
  for(const reason of ['manual','focus','clock','interaction'])clear(reason);
  return holds.size?{ok:false,reason:'Resume unavailable: '+[...holds].join(', ')}:{ok:true};
 }
 function begin(side){const ready=explicitReady();if(!ready.ok)return ready;const result=cycle.begin(side==='inside'?'habitat':side==='outside'?'mars':side);if(result.ok)schedule(result.token);return result;}
 function resume(){const ready=explicitReady();if(!ready.ok)return ready;const result=cycle.resume();if(result.ok)schedule(result.token);return result;}
 function command(doorId){
  if(disposed||getCurrent()!==loaded)return {ok:false,reason:'This airlock session is no longer current.'};
  // The app owns ordinary-door dispatch. Never forward an unbound ID: the
  // runtime treats undefined as a nearest-door command, which bypassed this gate.
  const side=sides.get(doorId);if(!side)return {ok:false,reason:'Door is not part of this airlock pair.'};
  const s=update();if(disposed||holds.has('hidden')||holds.has('blur')||holds.has('room'))return {ok:false,reason:'Airlock interaction is paused.'};
  if(['cycling','paused'].includes(s.phase))return {ok:false,reason:'Cancel the fictional cycle before moving a hatch.'};
  const d=s.doors?.[side];if(!s.observationValid||!d)return {ok:false,reason:'Current door observation unavailable.'};
  if(s.phase==='fault')return {ok:false,reason:s.reason||'Airlock state is faulted; no door motion was authorized.'};
  if(d.moving)return {ok:true,state:d.target===0?'closing':'opening',continueMotion:true};
  const result=d.angle===0?cycle.open(side):cycle.close(side);
  return result.ok?{...result,state:result.action||'closed'}:result;
 }
 return Object.freeze({binding,labels,hasDoor:id=>sides.has(id),snapshot,update,inRange,pause,clear,begin,resume,command,
  acknowledge(side){const ready=explicitReady();return ready.ok?cycle.acknowledgeSimulatedSeal(side):ready;},
  cancel(){revoke();const result=cycle.cancel();holds.add('manual');return result;},
  isRunning:()=>token!==null,
  dispose(){if(disposed)return;revoke();disposed=true;cycle.dispose();}
 });
}
