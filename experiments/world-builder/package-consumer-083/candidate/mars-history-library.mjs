/** Original, framework-neutral listening-library seam. No work on import. */
const SCHEMA='mars-history-library/v1';
const ID=/^[a-z][a-z0-9-]{0,79}$/;
const SHA=/^[a-f0-9]{64}$/;
const finite=n=>typeof n==='number'&&Number.isFinite(n);
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
const need=(ok,message)=>{if(!ok)throw new TypeError(message);};
const record=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
function fields(value,names,label){need(record(value)&&Object.keys(value).every(k=>names.includes(k)),label+' has unsupported fields');}
function text(value,max,label){need(typeof value==='string'&&value.trim().length>0&&value.length<=max,label+' must be nonempty text');return value;}
function id(value){need(typeof value==='string'&&ID.test(value),'Invalid stable identifier');return value;}
function date(value){need(typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value),'Use an ISO calendar date');const d=new Date(value+'T00:00:00Z');need(Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===value,'Invalid calendar date');return value;}
function officialURL(value){
 text(value,2048,'Official source URL');let url;try{url=new URL(value);}catch{throw new TypeError('Invalid official source URL');}
 const host=url.hostname.toLowerCase();need(url.protocol==='https:'&&!url.username&&!url.password&&(!url.port||url.port==='443')&&['nasa.gov','esa.int','jaxa.jp'].some(base=>host===base||host.endsWith('.'+base)),'Source must use the allowed official HTTPS domains');return url.href;
}
function mediaURL(value){
 text(value,240,'Audio path');need(value.startsWith('media/mars-history/')&&!/[\\%?#:\s]/.test(value),'Audio must use a bundled Mars-history path');
 const parts=value.split('/');need(parts.length>=3&&parts.every(p=>/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(p)&&p!=='.'&&p!=='..')&&/\.(mp3|wav|ogg|m4a)$/i.test(parts.at(-1)),'Unsafe or unsupported audio path');return value;
}
export function validateMarsHistoryManifest(raw){
 fields(raw,['schema','asOf','chapters','sources'],'Manifest');need(raw.schema===SCHEMA,'Unsupported library schema');date(raw.asOf);
 need(record(raw.sources)&&Object.keys(raw.sources).length>0&&Object.keys(raw.sources).length<=100,'Official sources are required');
 const sources={};for(const [key,value] of Object.entries(raw.sources)){
  id(key);fields(value,['title','url','checkedOn'],'Source');sources[key]={title:text(value.title,240,'Source title'),url:officialURL(value.url),checkedOn:date(value.checkedOn)};
 }
 need(Array.isArray(raw.chapters)&&raw.chapters.length>0&&raw.chapters.length<=50,'Provide one to fifty chapters');
 const seen=new Set();const chapters=raw.chapters.map(value=>{
  fields(value,['id','title','period','status','transcript','sourceIds','audio'],'Chapter');id(value.id);need(!seen.has(value.id),'Duplicate chapter identity');seen.add(value.id);
  need(['historical','current','planned'].includes(value.status),'Unknown chapter time status');
  need(Array.isArray(value.sourceIds)&&value.sourceIds.length>0&&new Set(value.sourceIds).size===value.sourceIds.length&&value.sourceIds.every(s=>typeof s==='string'&&Object.hasOwn(sources,s)),'Chapter sources must resolve exactly');
  let audio=null;if(value.audio!==null){
   fields(value.audio,['url','sha256','durationSeconds','reviewStatus'],'Audio');need(typeof value.audio.sha256==='string'&&SHA.test(value.audio.sha256),'Audio needs an exact SHA-256');need(finite(value.audio.durationSeconds)&&value.audio.durationSeconds>0&&value.audio.durationSeconds<=86400,'Audio duration must be finite positive seconds');need(['technical-only','owner-approved'].includes(value.audio.reviewStatus),'Audio review status is required');
   audio={url:mediaURL(value.audio.url),sha256:value.audio.sha256,durationSeconds:value.audio.durationSeconds,reviewStatus:value.audio.reviewStatus};
  }
  return {id:value.id,title:text(value.title,240,'Chapter title'),period:text(value.period,240,'Chapter period'),status:value.status,transcript:text(value.transcript,100000,'Transcript'),sourceIds:[...value.sourceIds],audio};
 });
 return freeze({schema:SCHEMA,asOf:raw.asOf,chapters,sources});
}

// A late promise from a disposed controller must not pause a new owner.
const owners=new WeakMap();
export function createMarsHistoryPlayer({manifest:raw,audio,onChange=()=>{}}={}){
 const manifest=validateMarsHistoryManifest(raw);need(audio&&['play','pause','load','addEventListener','removeEventListener','removeAttribute'].every(k=>typeof audio[k]==='function'),'An HTMLAudio-compatible adapter is required');need(typeof onChange==='function','onChange must be a function');
 owners.get(audio)?.destroy();const owner={destroy};owners.set(audio,owner);
 let selected=manifest.chapters[0],disposed=false,hidden=false,inRoom=true,intent=false,op=0,epoch=0,suppressPause=false;
 let phase='pending',duration=null,error='',notificationError='',pauseReason='initial';const listeners=[];
 const owns=()=>owners.get(audio)===owner;
 function currentTime(){const n=finite(audio.currentTime)?Math.max(0,audio.currentTime):0;return duration===null?n:Math.min(n,duration);}
 function status(){return freeze({chapterId:selected.id,phase,hasAudio:!!selected.audio,canPlay:!!selected.audio&&!disposed&&!hidden&&inRoom,playing:intent&&audio.paused===false,currentTime:currentTime(),duration,declaredDuration:selected.audio?.durationSeconds??null,seekEnabled:!!selected.audio&&duration!==null&&!disposed,volume:finite(audio.volume)?clamp(audio.volume,0,1):1,muted:audio.muted===true,hidden,inRoom,error,notificationError,pauseReason,destroyed:disposed});}
 function emit(){if(disposed||!owns())return;try{onChange(status());}catch{notificationError='The library display callback failed.';}}
 function nativePause(){if(!owns())return;suppressPause=true;try{audio.pause();}finally{suppressPause=false;}}
 function clearListeners(){for(const [event,fn] of listeners)audio.removeEventListener(event,fn);listeners.length=0;}
 function listen(event,fn){const generation=epoch;const wrapped=()=>{if(!disposed&&owns()&&generation===epoch)fn();};audio.addEventListener(event,wrapped);listeners.push([event,wrapped]);}
 function metadata(){duration=finite(audio.duration)&&audio.duration>0?audio.duration:null;if(!intent&&phase==='loading'&&duration!==null)phase='ready';emit();}
 function mediaFailure(){if(!audio.error)return;op++;intent=false;phase='error';const code=audio.error.code;error=code===3?'This narration could not be decoded. The transcript remains available.':code===4?'This narration format or file is unavailable. The transcript remains available.':'This narration could not load. The transcript remains available.';nativePause();emit();}
 function installListeners(){
  listen('loadedmetadata',metadata);listen('durationchange',metadata);listen('timeupdate',emit);listen('volumechange',emit);
  listen('playing',()=>{if(audio.paused)return;if(!intent||hidden||!inRoom){nativePause();return;}phase='playing';error='';emit();});
  listen('waiting',()=>{if(intent){phase='buffering';emit();}});
  listen('pause',()=>{if(suppressPause||audio.paused===false)return;op++;intent=false;pauseReason='media';if(phase!=='error')phase='paused';emit();});
  listen('ended',()=>{if(audio.ended!==true)return;op++;intent=false;phase='ended';emit();});listen('error',mediaFailure);
 }
 function select(chapterId){
  if(disposed||!owns())return false;const chapter=manifest.chapters.find(c=>c.id===chapterId);if(!chapter)return false;
  op++;epoch++;intent=false;clearListeners();nativePause();selected=chapter;duration=null;error='';pauseReason='selection';
  audio.removeAttribute('src');audio.load();phase=chapter.audio?'loading':'pending';
  if(chapter.audio){audio.src=chapter.audio.url;installListeners();audio.load();}
  emit();return true;
 }
 async function play(){
  if(disposed||!owns()||hidden||!inRoom||!selected.audio||intent)return false;
  const attempt=++op,generation=epoch;intent=true;phase='starting';error='';emit();
  // An observer may close/select/pause during the notification above.
  if(disposed||!owns()||attempt!==op||generation!==epoch||!intent)return false;
  try{
   await audio.play();
   if(disposed||!owns()||attempt!==op||generation!==epoch){if(owns()&&!intent)nativePause();return false;}
   if(!intent||hidden||!inRoom){nativePause();return false;}
   if(audio.paused){intent=false;phase='paused';error='Playback did not start. Select Play to try again.';emit();return false;}
   phase='playing';emit();return true;
  }catch(reason){
   if(disposed||!owns()||attempt!==op||generation!==epoch){if(owns()&&!intent)nativePause();return false;}
   intent=false;phase='error';error=reason?.name==='NotAllowedError'?'Your browser blocked playback. Select Play again to start narration.':'The narration could not start. Select Play to try again; the transcript remains available.';nativePause();emit();return false;
  }
 }
 function pause(reason='user'){
  if(disposed||!owns())return false;op++;intent=false;pauseReason=reason;nativePause();
  if(!selected.audio)phase='pending';else if(phase!=='error')phase=duration!==null&&currentTime()>=duration?'ended':'paused';emit();return true;
 }
 function seek(seconds){
  if(disposed||!owns()||!selected.audio||duration===null||!finite(seconds))return false;
  try{audio.currentTime=clamp(seconds,0,duration);error='';if(!intent)phase=currentTime()>=duration?'ended':'paused';emit();return true;}catch{error='That playback position is unavailable. Try again after loading.';emit();return false;}
 }
 function setVolume(value){if(disposed||!owns()||!finite(value))return false;audio.volume=clamp(value,0,1);emit();return true;}
 function setMuted(value){if(disposed||!owns()||typeof value!=='boolean')return false;audio.muted=value;emit();return true;}
 function setHidden(value){if(disposed||typeof value!=='boolean')return false;hidden=value;if(hidden)return pause('hidden');emit();return true;}
 function setInRoom(value){if(disposed||typeof value!=='boolean')return false;inRoom=value;if(!inRoom)return pause('room-exit');emit();return true;}
 function destroy(){
  if(disposed)return;disposed=true;op++;epoch++;intent=false;clearListeners();nativePause();
  // Retain weak ownership until replacement: a late resolution can still pause
  // this disposed element, but must never pause a newer controller's playback.
  if(owns()){audio.removeAttribute('src');audio.load();}phase='destroyed';
 }
 audio.autoplay=false;audio.loop=false;audio.preload='metadata';select(selected.id);
 return Object.freeze({manifest,status,select,play,pause,seek,setVolume,setMuted,setHidden,setInRoom,exit:()=>setInRoom(false),enter:()=>setInRoom(true),destroy});
}

function timeLabel(seconds){if(!finite(seconds))return 'not loaded';const whole=Math.max(0,Math.floor(seconds));return Math.floor(whole/60)+':'+String(whole%60).padStart(2,'0');}
export function mountMarsHistoryLibrary(container,{manifest:raw,audio=null,onInteractionChange=()=>{}}={}){
 need(container&&container.ownerDocument&&typeof container.append==='function','Provide a DOM container');need(typeof onInteractionChange==='function','Interaction hook must be a function');
 const manifest=validateMarsHistoryManifest(raw),doc=container.ownerDocument;
 const node=(tag,textContent,className)=>{const n=doc.createElement(tag);if(textContent!==undefined)n.textContent=textContent;if(className)n.className=className;return n;};
 const root=node('section',undefined,'mars-history-library');root.setAttribute('aria-label','Mars history listening library');root.tabIndex=-1;
 const header=node('header'),heading=node('h2','Mars history library'),dateLine=node('p','Content checked '+manifest.asOf),close=node('button','Close library');close.type='button';header.append(heading,dateLine,close);
 const layout=node('div',undefined,'mars-history-layout'),nav=node('nav');nav.setAttribute('aria-label','Mars history chapters');const list=node('ul');nav.append(list);
 const body=node('div',undefined,'mars-history-body'),title=node('h3'),badge=node('p',undefined,'mars-history-badge'),period=node('p'),availability=node('p');availability.setAttribute('role','status');availability.setAttribute('aria-live','polite');
 const controls=node('div',undefined,'mars-history-controls');controls.setAttribute('role','group');controls.setAttribute('aria-label','Narration controls');
 const play=node('button','Play narration'),pause=node('button','Pause'),seekLabel=node('label','Playback position'),seek=node('input'),position=node('output');seek.type='range';seek.min='0';seek.max='0';seek.step='1';seek.value='0';seek.setAttribute('aria-label','Playback position');seekLabel.append(seek,position);
 const volumeLabel=node('label','Volume'),volume=node('input');volume.type='range';volume.min='0';volume.max='1';volume.step='0.05';volume.setAttribute('aria-label','Narration volume');volumeLabel.append(volume);
 const mute=node('button','Mute');mute.setAttribute('aria-pressed','false');for(const b of [play,pause,mute])b.type='button';controls.append(play,pause,seekLabel,volumeLabel,mute);
 const transcript=node('details'),summary=node('summary','Read transcript'),prose=node('div',undefined,'mars-history-transcript');transcript.open=true;transcript.append(summary,prose);
 const sourceHeading=node('h4','Official sources'),sources=node('ul');body.append(title,badge,period,availability,controls,transcript,sourceHeading,sources);layout.append(nav,body);root.append(header,layout);container.append(root);
 const buttons=new Map(),handlers=[];let focusOwned=false,destroyed=false,player,renderedChapter=null;
 const on=(target,event,fn)=>{target.addEventListener(event,fn);handlers.push([target,event,fn]);};
 function movement(value){if(focusOwned===value)return;focusOwned=value;onInteractionChange(value);}
 function render(s){
  const chapter=manifest.chapters.find(c=>c.id===s.chapterId);
  if(renderedChapter!==chapter.id){
   renderedChapter=chapter.id;title.textContent=chapter.title;period.textContent=chapter.period;
   badge.textContent=chapter.status==='planned'?'Planned · proposals and schedules may change':chapter.status==='current'?'Current as of '+manifest.asOf:'Historical';
   prose.textContent=chapter.transcript;
   for(const [id,b] of buttons){if(id===chapter.id)b.setAttribute('aria-current','true');else b.removeAttribute('aria-current');}
   // Preserve focused transcript/source nodes during time and volume updates.
   // Every label is text; only validated official URLs become links.
   sources.replaceChildren();for(const id of chapter.sourceIds){const source=manifest.sources[id],li=node('li'),a=node('a',source.title);a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';li.append(a,node('span',' · checked '+source.checkedOn));sources.append(li);}
  }
  const review=chapter.audio?.reviewStatus==='owner-approved'?'Owner-reviewed narration':'Narration has technical checks only; listening review pending';
  availability.textContent=s.error||(chapter.audio?(s.phase==='playing'?'Playing. ':s.phase==='starting'||s.phase==='buffering'?'Loading narration. ':'')+review:'Narration pending. The transcript and official sources are available.');
  play.disabled=!s.canPlay||['playing','starting','buffering'].includes(s.phase);pause.disabled=!['playing','starting','buffering'].includes(s.phase);seek.disabled=!s.seekEnabled;seek.max=String(s.duration??0);seek.value=String(s.currentTime);seek.setAttribute('aria-valuetext',timeLabel(s.currentTime)+' of '+timeLabel(s.duration));position.textContent=timeLabel(s.currentTime)+' / '+timeLabel(s.duration);
  volume.value=String(s.volume);mute.setAttribute('aria-pressed',String(s.muted));mute.textContent=s.muted?'Unmute':'Mute';
 }
 for(const chapter of manifest.chapters){const li=node('li'),button=node('button',chapter.title);button.type='button';buttons.set(chapter.id,button);on(button,'click',()=>player.select(chapter.id));li.append(button);list.append(li);}
 const media=audio??doc.createElement('audio');player=createMarsHistoryPlayer({manifest,audio:media,onChange:render});render(player.status());
 on(play,'click',()=>{void player.play();});on(pause,'click',()=>player.pause());on(seek,'input',()=>player.seek(Number(seek.value)));on(volume,'input',()=>player.setVolume(Number(volume.value)));on(mute,'click',()=>player.setMuted(!player.status().muted));
 on(root,'focusin',()=>movement(true));on(root,'focusout',event=>{if(!event.relatedTarget||!root.contains(event.relatedTarget))movement(false);});
 // The host must also consult onInteractionChange before movement capture handlers.
 for(const event of ['keydown','keyup'])on(root,event,e=>{if(event==='keydown'&&(e.code==='Escape'||e.key==='Escape'))exit();e.stopPropagation();});
 on(doc,'visibilitychange',()=>player.setHidden(doc.hidden===true));player.setHidden(doc.hidden===true);
 function exit(){if(destroyed)return;player.exit();root.hidden=true;movement(false);}
 on(close,'click',exit);
 return Object.freeze({root,player,exit,enter(){if(destroyed)return;root.hidden=false;player.enter();root.focus();},destroy(){if(destroyed)return;destroyed=true;player.destroy();for(const [target,event,fn] of handlers)target.removeEventListener(event,fn);root.remove();movement(false);}});
}
