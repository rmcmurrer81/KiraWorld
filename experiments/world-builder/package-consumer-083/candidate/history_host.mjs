import {mountMarsHistoryLibrary} from './mars-history-library.mjs';

// Admission is against the selected package's validated room metadata, never a
// room label, chapter content, URL parameter or a remembered previous package.
export function isCrewQuarters(current){
 const roomId=current?.runtime.snapshot().roomId;
 return !!roomId&&current.metadata?.rooms?.some(room=>room.id===roomId&&room.functional_role==='habitat')===true;
}
export function isInteractiveTarget(target){
 if(!target)return false;
 if(target.isContentEditable)return true;
 return typeof target.closest==='function'&&!!target.closest('input,button,select,textarea,a,summary,details,[contenteditable="true"],[role="button"],[tabindex]');
}
export function createHistoryHost({entry,container,message,getContext,stopWalking,loadManifest,mount=mountMarsHistoryLibrary}){
 let view=null,epoch=0,busy=false,disposed=false;
 const allowed=()=>{const c=getContext();return !disposed&&!c.loading&&!c.closed&&isCrewQuarters(c.current);};
 function update(){
  const eligible=allowed();if(!eligible&&busy){epoch++;busy=false;}entry.hidden=!eligible;entry.disabled=!eligible||busy;
  if(!eligible&&view&&!view.root.hidden)view.exit();
  if(!eligible)message.textContent='';
 }
 async function open(){
  if(!allowed()||busy)return false;
  stopWalking();
  if(view){view.enter();return true;}
  const requested=epoch;busy=true;message.textContent='Opening Mars history…';update();
  try{
   const manifest=await loadManifest();
   if(disposed||requested!==epoch||!allowed())return false;
   view=mount(container,{manifest,onInteractionChange:focused=>{if(focused)stopWalking();}});
   message.textContent='';view.enter();return true;
  }catch(error){
   if(!disposed&&requested===epoch&&allowed())message.textContent='Mars history unavailable: '+error.message;
   return false;
  }finally{if(requested===epoch){busy=false;update();}}
 }
 function pause(reason='host-pause'){view?.player.pause(reason);}
 function close(){epoch++;busy=false;message.textContent='';view?.exit();update();}
 function reset(){epoch++;busy=false;view?.destroy();view=null;message.textContent='';update();}
 function destroy(){if(disposed)return;disposed=true;reset();entry.removeEventListener('click',open);}
 entry.addEventListener('click',open);update();
 return Object.freeze({update,open,pause,close,reset,destroy,isOpen:()=>!!view&&!view.root.hidden});
}
