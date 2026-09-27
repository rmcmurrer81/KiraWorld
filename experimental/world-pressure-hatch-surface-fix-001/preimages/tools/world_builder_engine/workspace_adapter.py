"""Small native bridge: fresh worker, durable results, button-owned preview."""
from pathlib import Path
import hashlib,json,queue,subprocess,sys,threading,time,uuid,webbrowser

ENGINE=Path(__file__).resolve().parent
PROJECT=ENGINE.parents[1]


def require_job(job_dir):
    job_dir=Path(job_dir).resolve()
    if job_dir.parent!=PROJECT/'Data'/'world_research_jobs' or not job_dir.name.startswith('world_research_'):
        raise ValueError('Choose a saved research job from this installation')
    return job_dir


def command(script,*args):
    executable=Path(sys.executable)
    if executable.name.lower()=='pythonw.exe':
        console=executable.with_name('python.exe')
        if not console.is_file():raise ValueError('The console Python sibling is required for worker progress')
        executable=console
    return [str(executable),'-I','-B','-X','utf8',str(ENGINE/script),*map(str,args)]


def run_pipeline_after_research(job_dir,*,on_progress=None):
    """Called once in the existing native background worker after research returns."""
    job_dir=require_job(job_dir)
    receipt=job_dir/('layout-bridge-'+uuid.uuid4().hex+'.json')
    args=command('worker.py','--job',job_dir)
    result=None;stdout='';stderr='';exit_code=None;process=None
    try:
        process=subprocess.Popen(args,cwd=PROJECT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        messages=queue.Queue();readers=[]
        def read_stream(name,stream,limit):
            try:
                total=0
                while True:
                    line=stream.readline(limit+1)
                    if not line:break
                    total+=len(line)
                    if total>limit:messages.put(('error',name+' exceeded its output bound'));break
                    messages.put((name,line))
            except Exception as exc:messages.put(('error',str(exc)))
            finally:messages.put(('eof',name))
        for name,stream,limit in [('stdout',process.stdout,350000),('stderr',process.stderr,16000)]:
            reader=threading.Thread(target=read_stream,args=(name,stream,limit),daemon=True);reader.start();readers.append(reader)
        deadline=time.monotonic()+430;closed=set()
        while len(closed)<2:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired(args,430)
            try:kind,line=messages.get(timeout=min(.25,remaining))
            except queue.Empty:continue
            if kind=='eof':closed.add(line);continue
            if kind=='error':raise ValueError(line)
            if kind=='stderr':stderr+=line;continue
            stdout+=line;event=json.loads(line)
            if event.get('kind')=='progress' and isinstance(event.get('value'),dict):
                if on_progress:on_progress(event['value'])
            elif event.get('kind')=='finished' and isinstance(event.get('value'),dict) and result is None:
                result=event['value']
            else:raise ValueError('Unexpected layout worker protocol message')
        exit_code=process.wait(timeout=max(.1,deadline-time.monotonic()))
        if exit_code!=0 or result is None:raise ValueError('Layout worker exited before a complete result')
    except subprocess.TimeoutExpired:
        result={'stage':'pipeline_worker_timeout','message':'The owned worker timed out. Any claimed model attempt remains consumed; cleanup is unknown and no automatic replay is permitted.',
                'geometry_generated':False,'world_ready':False,'cleanup_verified':False}
    except Exception as exc:
        result={'stage':'pipeline_worker_held','message':str(exc),'geometry_generated':False,'world_ready':False}
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            exit_code=process.returncode
            for stream in (process.stdout,process.stderr):
                if stream:stream.close()
    with receipt.open('x',encoding='utf-8') as stream:
        json.dump({'command':args,'worker_sha256':hashlib.sha256((ENGINE/'worker.py').read_bytes()).hexdigest(),
                   'exit_code':exit_code,'stdout':stdout[:350000],'stderr':stderr[:16000],'result':result},stream,indent=2)
    return {**result,'bridge_receipt':str(receipt)}


class PreviewSession:
    def __init__(self,process,url,manifest):self.process,self.url,self.manifest=process,url,manifest
    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
        for stream in (self.process.stdout,self.process.stderr):
            if stream:stream.close()


def open_preview(job_dir,current=None):
    """Only called by the native Open Layout Preview button; never on research completion."""
    job_dir=require_job(job_dir)
    # A fresh server verifies the current state, packet and all input pins even
    # when a previous preview window remains open after an app restart/resume.
    if current:current.close()
    process=subprocess.Popen(command('preview_server.py','--job',job_dir),
                             cwd=PROJECT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    ready=queue.Queue()
    threading.Thread(target=lambda:ready.put(process.stdout.readline()),daemon=True).start()
    session=PreviewSession(process,None,None)
    try:
        line=ready.get(timeout=32);value=json.loads(line)
        url=value['url']
        if not isinstance(url,str) or not url.startswith('http://127.0.0.1:'):raise ValueError('Unexpected preview URL')
        session.url=url;session.manifest=value['manifest'];webbrowser.open(url);return session
    except Exception:
        session.close();raise ValueError('The verified preview server could not start; preserved layout files remain available')


def close_preview(session):
    if session:session.close()
