"""Actual workspace callbacks + saved-job services, no Tk/model/network boundary."""
from pathlib import Path
from types import SimpleNamespace
import contextlib,hashlib,importlib.util,json,queue,sys,tempfile,os
from unittest.mock import patch

H=Path(__file__).resolve().parent;K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'));sys.path.insert(0,str(H/'candidate/tools'))
import world_research as research
import world_builder_engine.layout_package_export as export_api

def load(which):
    path=H/('baseline/world_builder_workspace.py' if which=='baseline' else 'candidate/tools/world_builder_workspace.py')
    spec=importlib.util.spec_from_file_location('workspace048_'+which,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def snapshot(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
class Var:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value
class Choice:
    def __init__(self):self.index=-1;self.values=[];self.text=''
    def configure(self,**kw):self.values=kw['values']
    def current(self,index=None):
        if index is not None:self.index=index
        return self.index
    def set(self,text):self.text=text;self.index=-1
class Child:
    def __init__(self,job):self.job=job;self.live=True;self.destroyed=0;self.bound=[]
    def winfo_exists(self):return self.live
    def destroy(self):self.live=False;self.destroyed+=1
    def set_world_job(self,job):self.job=job;self.bound.append(job)
class Preview:
    def __init__(self,job):self.job=job;self.closed=False;self.manifest={'manifest_path':str(job/'preview.json'),'manifest_sha256':'a'*64}
    def close(self):self.closed=True
class Button:
    def __init__(self):self.state='normal'
    def configure(self,**kw):self.state=kw['state']

def make(root,prompt):return research.create_job(research.brief_from_prompt(prompt,max_queries=0),job_root=root)
def app(module,root,job=None):
    a=object.__new__(module.WorldBuilderWorkspace)
    a.chat_var=Var();a.messages=[];a.log=a.messages.append
    a._research_latest=job;a.latest_folder=job;a.latest_request=Path('previous-notebook-request.json') if job else None
    a._saved_research_items=[];a.saved_research_choice=Choice();a._research_pending=[];a._research_worker=None;a._research_messages=queue.Queue()
    a._layout_preview=Preview(job) if job else None;a._reference_photos_view=Child(job) if job else None;a._original_components_view=Child(job)
    a._export_worker=None;a._export_messages=queue.Queue();a._last_export_folder=None;a._export_button=Button();a.scheduled=[];a.after=lambda ms,fn:a.scheduled.append(fn.__name__)
    return a
@contextlib.contextmanager
def boundaries(module,root,events,exporter=None):
    class InertThread:
        def __init__(self,*,target,daemon,name):self.target=target;self.name=name
        def start(self):
            events.append({'boundary':self.name})
            # Research and geometry/model execution are deliberately inert.
            # Export's worker is allowed only into the supplied inert exporter.
            if self.name=='world-layout-package-export':self.target()
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(module,'DEFAULT_JOB_ROOT',root))
        stack.enter_context(patch.object(module.threading,'Thread',InertThread))
        stack.enter_context(patch.object(module,'run_job',side_effect=AssertionError('Research boundary must stay inert')))
        stack.enter_context(patch.object(module,'run_pipeline_after_research',side_effect=AssertionError('Model boundary must stay inert')))
        stack.enter_context(patch.object(module.filedialog,'askdirectory',return_value=str(root.parent)))
        stack.enter_context(patch.object(module,'open_preview',side_effect=lambda job,current:(events.append({'preview_job':job.name}),Preview(job))[1]))
        stack.enter_context(patch.object(module,'export_saved_layout_package',side_effect=exporter or (lambda *a,**kw:{'status':'audit_inert','message':'Export boundary stopped before any file output.'})))
        stack.enter_context(patch.object(module.subprocess,'Popen',side_effect=AssertionError('No subprocess allowed')))
        yield

