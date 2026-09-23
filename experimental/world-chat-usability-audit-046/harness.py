"""Actual workspace callbacks + saved-job services, no Tk/model/network boundary."""
from pathlib import Path
from types import SimpleNamespace
import contextlib,hashlib,importlib.util,json,queue,sys,tempfile,os
from unittest.mock import patch

H=Path(__file__).resolve().parent;K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
import world_research as research
import world_builder_engine.layout_package_export as export_api

def load(which):
    path=H/('baseline/world_builder_workspace.py' if which=='baseline' else 'candidate/tools/world_builder_workspace.py')
    spec=importlib.util.spec_from_file_location('workspace046_'+which,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
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
        if exporter:stack.enter_context(patch.object(module,'export_saved_layout_package',side_effect=exporter))
        stack.enter_context(patch.object(module.subprocess,'Popen',side_effect=AssertionError('No subprocess allowed')))
        yield

CASES=[
 ('new_mars','Build a Mars base.'),
 ('new_habitat','Build a habitat with a galley, laboratory and two airlock doors.'),
 ('new_crew_habitat','Build an original crew habitat.'),
 ('edit_door','Make the current habitat airlock door wider.'),
 ('add_furniture','Add a dining table to the habitat I have open.'),
 ('change_room','Change the laboratory into a galley.'),
 ('open_saved','Open latest saved world.'),
 ('reopen_saved','Reopen my latest saved habitat.'),
 ('preview_chat','Open current preview.'),
 ('export_chat','Export this world as a 3D package.'),
 ('resume_exact','resume'),
 ('resume_research','Resume research'),
 ('continue_world','Continue my world.'),
 ('negated','Do not build a new world.'),
 ('question','Tell me what this room can do.'),
]
def capture(which):
    module=load(which);rows=[]
    for name,prompt in CASES:
        with tempfile.TemporaryDirectory(prefix='world046-',dir=H) as directory:
            root=Path(directory)/'jobs';root.mkdir();previous=make(root,'Build an original habitat.')
            before=snapshot(previous);a=app(module,root,previous);old_preview=a._layout_preview;photos=a._reference_photos_view;components=a._original_components_view;events=[]
            a.chat_var.set(prompt)
            with boundaries(module,root,events):a.send_world_builder_chat()
            job=research.read_json(a._research_latest/'job.json')
            assert snapshot(previous)==before
            rows.append({'case':name,'prompt':prompt,'new_research_job':a._research_latest!=previous,
                'selected_job_subject':job['brief']['subject'],'research_mode':job['brief']['research_mode'],
                'original_generation_allowed':research.original_generation_allowed(job['brief']),
                'old_preview_closed':old_preview.closed,'stale_old_preview_retained':a._layout_preview is old_preview and a._research_latest!=previous,
                'old_reference_view_closed':photos.destroyed==1,'component_bound_to_selection':components.job==a._research_latest,
                'preview_action_dispatched':any('preview_job' in e for e in events),'export_action_dispatched':any(e.get('boundary')=='world-layout-package-export' for e in events),
                'boundary_events':events,'messages':a.messages,'prior_saved_bytes_unchanged':True,'native_window_network_or_model_calls':0})
    return {'status':'MEASURED_ACTUAL_CHAT_ROUTING_WITH_INERT_WORKERS','source':which,'source_sha256':hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),'cases':rows,'scope':'Real submit_research_prompt/brief/create_job/catalog and actual chat callback; background research/model and native UI/export inputs are inert. All writes use disposable temporary state.'}
if __name__=='__main__':
    which=sys.argv[1];assert which in ('baseline','candidate');result=capture(which)
    with (H/(which.upper()+'-CHAT-CAPTURES.json')).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'source':which,'cases':len(result['cases']),'stale_previous_previews':sum(r['stale_old_preview_retained'] for r in result['cases']),'new_research_jobs':sum(r['new_research_job'] for r in result['cases']),'native_ui_models':0}))
