// Explicit recording and local save. A visible Blob link remains as a fallback.
export function attachCanvasRecorder(canvas, recordButton, stopButton, status, env=globalThis, downloadLink=null) {
  const MAX_BYTES=64*1024*1024, MAX_MS=90_000;
  let active=null, pending=null, saving=false;
  function stop(session){if(session&&!session.finished&&session.recorder.state!=='inactive')session.recorder.stop();}
  function buttons(){recordButton.disabled=Boolean(active)||saving;stopButton.disabled=saving||(!active&&!pending);
    stopButton.textContent=active?'Stop and save':'Save recording locally';}
  async function savePending(){
    if(!pending||saving)return;saving=true;buttons();
    const item=pending,abort=new env.AbortController(),timeout=env.setTimeout(()=>abort.abort(),35_000);
    status.textContent='Saving to this preview’s local recording-output folder…';
    try{
      const response=await env.fetch('/recordings',{method:'POST',headers:{'Content-Type':'video/webm'},body:item.blob,
        signal:abort.signal,redirect:'error',credentials:'omit',cache:'no-store'});
      if(response.status!==201)throw Error('Local server refused the recording ('+response.status+').');
      const result=await response.json();
      if(result.status!=='saved_verified'||!/^Kira-Mattress-Physics-Engineering-[0-9a-f]{32}\.webm$/.test(result.filename)||
        result.relative_path!=='recording-output/'+result.filename||result.bytes!==item.blob.size||!/^[0-9a-f]{64}$/.test(result.sha256))
        throw Error('The server did not confirm the exact saved recording.');
      status.textContent='Saved and byte-verified: '+result.relative_path+' ('+result.bytes+' bytes; SHA-256 '+result.sha256.slice(0,12)+'…). Video playback still needs review.';
      item.saved=true;
    }catch(error){status.textContent='Local save not confirmed: '+error.message+' The visible Download recording link remains available.';}
    finally{env.clearTimeout(timeout);saving=false;buttons();}
  }
  function finish(session){
    if(session.finished)return;session.finished=true;
    env.clearTimeout(session.timer);session.stream.getTracks().forEach(track=>track.stop());
    if(active===session)active=null;
    if(session.failure){status.textContent=session.failure;session.chunks=[];buttons();return;}
    if(!session.bytes){status.textContent='No video frames were recorded.';buttons();return;}
    const blob=new env.Blob(session.chunks,{type:session.recorder.mimeType||'video/webm'});session.chunks=[];
    if(pending)env.URL.revokeObjectURL(pending.url);
    pending={blob,url:env.URL.createObjectURL(blob),saved:false};
    if(downloadLink){downloadLink.href=pending.url;downloadLink.download='Kira-Mattress-Physics-Engineering-September-12.webm';downloadLink.hidden=false;
      downloadLink.textContent='Download recording (browser fallback)';}
    status.textContent='Recording retained in this page. Click Save recording locally, or use the visible download link.';buttons();
    if(session.saveRequested)void savePending();
  }
  recordButton.addEventListener('click',()=>{
    recordButton.blur();if(active||saving)return;
    if(typeof canvas.captureStream!=='function'||typeof env.MediaRecorder!=='function'){
      status.textContent='This browser cannot record the 3D view.';return;}
    let stream=null;
    try{
      const mime=['video/webm;codecs=vp8','video/webm;codecs=vp9','video/webm'].find(type=>env.MediaRecorder.isTypeSupported(type));
      if(!mime)throw Error('WebM recording is unavailable in this browser.');
      stream=canvas.captureStream(20);
      const recorder=new env.MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2_500_000});
      const session={recorder,stream,chunks:[],bytes:0,failure:null,finished:false,timer:null,saveRequested:false};active=session;
      recorder.ondataavailable=event=>{
        if(session.finished||session.failure||!event.data.size)return;
        if(session.bytes+event.data.size>MAX_BYTES){session.failure='Recording stopped at the 64 MiB limit. Try a shorter walkthrough.';stop(session);return;}
        session.chunks.push(event.data);session.bytes+=event.data.size;
      };
      recorder.onerror=()=>{session.failure='Video recording failed in this browser.';stop(session);if(recorder.state==='inactive')finish(session);};
      recorder.onstop=()=>finish(session);recorder.start(1000);
      session.timer=env.setTimeout(()=>stop(session),MAX_MS);buttons();
      status.textContent='Recording the 3D view only — up to 90 seconds. Stop and save writes to this local preview folder.';
    }catch(error){stream?.getTracks().forEach(track=>track.stop());active=null;buttons();status.textContent='Recording unavailable: '+error.message;}
  });
  stopButton.addEventListener('click',()=>{stopButton.blur();if(active){active.saveRequested=true;stop(active);}else void savePending();});
  env.addEventListener('pagehide',()=>{if(active){active.failure='Recording stopped because the preview closed.';stop(active);}if(pending)env.URL.revokeObjectURL(pending.url);});
  buttons();
}
