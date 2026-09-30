// Original session-local visual latch authority. No pressure or seal physics.
export const LATCH_STATE_CONTRACT='authored_latch_state_v2';
const need=(v,m)=>{if(!v)throw new TypeError(m);};
export function createLatchAuthority({id,openAngle,readDoor,isCurrent=()=>true}){
 need(typeof id==='string'&&id.length>0&&Number.isFinite(openAngle)&&Math.abs(Math.abs(openAngle)-Math.PI/2)<1e-9&&typeof readDoor==='function'&&typeof isCurrent==='function','Exact door ports required');
 let fraction=0,target=0,fault=null,disposed=false,revision=0,intent=null,locked=false;
 const holds=new Set(),fail=reason=>({ok:false,reason});
 const snapshot=()=>Object.freeze({contract:LATCH_STATE_CONTRACT,id,fraction,target,
  state:disposed?'disposed':fault?'fault':fraction===target?(fraction===0?'released':'engaged'):(target===1?'engaging':'releasing'),
  fault,paused:holds.size>0,pauseReasons:Object.freeze([...holds]),pendingOpen:intent!==null,
  physicalLatchSimulation:false,pressureSimulation:false,sealAcknowledgementAuthority:false});
 const invalidate=reason=>{fault=reason;intent=null;return fail(reason);};
 const closed=p=>p.angle===0&&p.target===0&&!p.moving&&!p.motionHeld;
 function observe(){
  if(disposed)return fail('Disposed latch session');
  if(fault)return fail(fault);
  const version=revision;let p,current;
  try{current=isCurrent();if(current===true)p=readDoor();}catch{return invalidate('Door observation unavailable');}
  if(disposed||version!==revision)return fail('Latch lifecycle changed during observation');
  let stillCurrent=false;try{stillCurrent=isCurrent();}catch{}
  if(disposed||version!==revision)return fail('Latch lifecycle changed during observation');
  if(current!==true||stillCurrent!==true)return invalidate('Door runtime is no longer current');
  if(!p||p.id!==id||!Number.isFinite(p.angle)||p.angle*openAngle<0||Math.abs(p.angle)>Math.abs(openAngle)||![0,openAngle].includes(p.target)||typeof p.moving!=='boolean'||typeof p.motionHeld!=='boolean')return invalidate('Invalid exact door observation');
  if(!closed(p)&&(fraction!==0||target!==0))return invalidate('Leaf moved before latch release');
  return {ok:true,closed:closed(p)};
 }
 function transaction(fn){
  if(locked)return fail('Reentrant latch command');
  locked=true;try{const o=observe();return o.ok?fn(o):o;}finally{locked=false;}
 }
 function canMove(){return transaction(()=>holds.size?fail('Latch motion is paused'):fraction!==0||target!==0?fail('Release the latch fully before moving the hatch'):{ok:true});}
 return Object.freeze({snapshot,canMove,
  request(engage){need(typeof engage==='boolean','Latch request must be boolean');return transaction(o=>{
   intent=null;if(holds.size)return fail('Latch motion is paused');
   if(engage&&!o.closed)return fail('Close and stop the hatch before engaging the latch');
   target=engage?1:0;return {ok:true};
  });},
  releaseForOpening(){return transaction(o=>{
   intent=null;if(holds.size)return fail('Latch motion is paused');
   if(!o.closed)return fail('Open intent requires an exactly closed, stopped hatch');
   target=0;intent=Object.freeze({revision});return {ok:true};
  });},
  takeOpenIntent(){return transaction(o=>{
   if(!intent)return {ok:true,ready:false};
   if(holds.size||!o.closed){intent=null;return fail('Pending opening no longer admissible');}
   if(fraction!==0||target!==0)return {ok:true,ready:false};
   intent=null;return {ok:true,ready:true};
  });},
  advance(seconds){need(typeof seconds==='number'&&Number.isFinite(seconds)&&seconds>=0&&seconds<=.05,'Latch step must be 0–0.05 seconds');return transaction(()=>{
   if(!holds.size&&fraction!==target){const d=seconds/.8;fraction=target>fraction?Math.min(target,fraction+d):Math.max(target,fraction-d);}
   return {ok:true,snapshot:snapshot()};
  });},
  cancelIntent(){intent=null;revision++;},
  pause(reason){need(typeof reason==='string'&&reason.length>0,'Pause reason required');if(!disposed){holds.add(reason);intent=null;revision++;}},
  resume(reason){need(typeof reason==='string'&&reason.length>0,'Pause reason required');if(!disposed){holds.delete(reason);revision++;}},
  dispose(){if(!disposed){disposed=true;intent=null;revision++;holds.clear();}},
 });
}
