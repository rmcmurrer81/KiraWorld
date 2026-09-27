// CPU export-only surface lifetimes. Never resize borrowed source textures.
export function createCanvasLifetime(createCanvas){
  const temporary=new WeakSet();
  let tail=Promise.resolve(),firstFailure=null;
  function release(value){
    if(!temporary.has(value))return;
    // The completed PNG Blob owns its bytes. Reset only this exhausted scratch
    // surface, using a supported nonzero minimum; no source image is resized.
    temporary.delete(value);value.width=1;value.height=1;
  }
  function make(isTemporary){
    const value=createCanvas(1,1);
    Object.defineProperty(value,'data',{value:undefined});
    if(isTemporary)temporary.add(value);
    const encode=value.toBlob.bind(value);
    value.toBlob=(callback,mime)=>{
      if(typeof callback!=='function')throw new TypeError('PNG callback is required');
      const task=tail.then(()=>new Promise((resolve,reject)=>{
        let settled=false;
        const complete=(blob,error=null)=>{
          if(settled)return;settled=true;
          try{callback(blob);}catch(failure){error??=failure;}
          try{release(value);}catch(failure){error??=failure;}
          if(error)reject(error);else resolve();
        };
        if(firstFailure){complete(null,firstFailure);return;}
        try{encode(blob=>complete(blob,blob==null?new Error('CPU PNG encoder returned no Blob'):null),mime);}
        catch(error){complete(null,error);}
      }));
      // Observe rejections even when the browser-style caller ignores the
      // return value. A later drain rethrows; subsequent callbacks receive null
      // in request order rather than silently hanging on a poisoned queue.
      tail=task.catch(error=>{firstFailure??=error;});
      return task;
    };
    return value;
  }
  return {
    sourceCanvas:()=>make(false),temporaryCanvas:()=>make(true),
    // A synchronous scratch scope, used only by the synchronous pixel digest.
    withTemporaryCanvas(callback){const value=make(true);try{return callback(value);}finally{release(value);}},
    async drainPng(){await tail;if(firstFailure)throw firstFailure;},
  };
}
