import test from 'node:test';import assert from 'node:assert/strict';
import {createMarsHistoryPlayer} from '../candidate/mars-history-library.mjs';
const manifest={schema:'mars-history-library/v1',asOf:'2026-09-26',sources:{nasa:{title:'CPU fixture only',url:'https://science.nasa.gov/mars/',checkedOn:'2026-09-26'}},chapters:[{id:'fixture',title:'Inert queued event test',period:'CPU test',status:'historical',transcript:'No real audio file is created or loaded.',sourceIds:['nasa'],audio:{url:'media/mars-history/nonexistent-test.wav',sha256:'a'.repeat(64),durationSeconds:20,reviewStatus:'technical-only'}}]};
class QueuedAudio{
 constructor(){this.listeners=new Map();this.queue=[];this.paused=true;this.currentTime=0;this.duration=NaN;this.volume=1;this.muted=false;this.calls=0;}
 addEventListener(e,f){if(!this.listeners.has(e))this.listeners.set(e,new Set());this.listeners.get(e).add(f);}
 removeEventListener(e,f){this.listeners.get(e)?.delete(f);}
 emit(e){for(const fn of [...this.listeners.get(e)||[]])fn();}
 pause(){if(!this.paused){this.paused=true;this.queue.push('pause');}}
 play(){this.calls++;this.paused=false;this.queue.push('playing');return Promise.resolve();}
 flush(){while(this.queue.length)this.emit(this.queue.shift());}
 removeAttribute(){}load(){}
}
test('task-queued old pause cannot cancel newer explicit Play in same chapter',async()=>{const audio=new QueuedAudio(),p=createMarsHistoryPlayer({manifest,audio});await p.play();audio.flush();p.pause();assert.equal(audio.paused,true);await p.play();assert.equal(audio.paused,false);audio.flush();assert.equal(p.status().phase,'playing');assert.equal(p.status().playing,true);assert.equal(audio.calls,2);p.destroy();});
test('genuine native pause still cancels intent after queued event',async()=>{const audio=new QueuedAudio(),p=createMarsHistoryPlayer({manifest,audio});await p.play();audio.flush();audio.pause();audio.flush();assert.equal(p.status().phase,'paused');assert.equal(p.status().playing,false);assert.equal(p.status().pauseReason,'media');p.destroy();});
test('delayed playing while currently paused does not report false playing',async()=>{const audio=new QueuedAudio(),states=[],p=createMarsHistoryPlayer({manifest,audio,onChange:s=>states.push(s.phase)});await p.play();audio.pause();const count=states.length;assert.equal(audio.queue.shift(),'playing');audio.emit('playing');assert.equal(states.length,count);audio.flush();assert.equal(p.status().phase,'paused');p.destroy();});
test('late queued events after destroy cannot revive disposed playback',async()=>{const audio=new QueuedAudio(),p=createMarsHistoryPlayer({manifest,audio});await p.play();p.destroy();audio.flush();assert.equal(audio.paused,true);assert.equal(p.status().destroyed,true);assert.equal(await p.play(),false);assert.equal(audio.calls,1);});
