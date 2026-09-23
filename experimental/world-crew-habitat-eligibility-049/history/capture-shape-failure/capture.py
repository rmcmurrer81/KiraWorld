"""Fresh-process parser selection; actual installed chat with inert worker."""
from pathlib import Path
import argparse,contextlib,hashlib,importlib.util,json,queue,socket,sys,tempfile
from unittest.mock import patch
H=Path(__file__).resolve().parent;K=Path('@kira_root')
args=argparse.ArgumentParser();args.add_argument('which',choices=['baseline','candidate']);options=args.parse_args()
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'));sys.path.insert(0,str(H/('baseline' if options.which=='baseline' else 'candidate/tools')))
import world_research as research
import world_research_workspace_adapter as adapter
import world_builder_workspace as workspace
from world_builder_engine import world_layout_v2 as planner,analog_case_index
from cases import CASES,ORIGINAL,REAL

def load_prior_harness():
    path=H.parent/'world-chat-delay-candidate-048/harness.py'
    spec=importlib.util.spec_from_file_location('fixture048',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
harness=load_prior_harness()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
sources=['https://example.org/alpha','https://example.net/beta','https://example.com/gamma']
def synthetic_fetch(url):
    name={'https://example.org/alpha':'Alpha Habitat','https://example.net/beta':'Beta Habitat','https://example.com/gamma':'Gamma Habitat'}[url]
    return {'final_url':url,'content_type':'text/html','data':('<title>'+name+'</title><p>'+name+' contains crew living rooms, equipment storage and a laboratory.</p><p>An airlock connects arrival rooms to shared circulation. A galley supports crew dining.</p>').encode()}
records=[]
with patch('socket.getaddrinfo',side_effect=AssertionError('No network permitted')):
    for name,prompt,expected in CASES:
        with tempfile.TemporaryDirectory(prefix='world049-',dir=H) as directory:
            root=Path(directory)/'Data/world_research_jobs';root.mkdir(parents=True)
            a=harness.app(workspace,root);a.chat_var.set(prompt);events=[]
            # Fix research inputs to three clearly synthetic documents, but
            # execute the actual adapter/brief/job methods and original prompt.
            def submit(value,**kwargs):return adapter.submit_research_prompt(value,**kwargs,source_urls=sources,max_queries=0,max_pages=3)
            with harness.boundaries(workspace,root,events),patch.object(workspace,'submit_research_prompt',side_effect=submit):a.send_world_builder_chat()
            selected=a._research_latest;record={'case':name,'prompt':prompt,'expected':expected,'queued_worker_boundary':bool(events),'messages':a.messages,'geometry_generated':False}
            if selected:
                brief=research.read_json(selected/'job.json')['brief'];record.update(mode=brief['research_mode'],original_generation_allowed=research.original_generation_allowed(brief),brief_prompt=brief['prompt'],research_task_ids=[r['id'] for r in research.task_plan(brief)])
                # Synchronous synthetic input ingestion only: no worker/network.
                research.run_job(selected,fetcher=synthetic_fetch)
                original=harness.snapshot(selected)
                try:
                    request=planner.plan_request(selected)
                    record['planner']={'status':'prepared','contract':request['contract'],'required_functions':request['required_functions'],'source_ids':sorted({r['source_id'] for r in request['evidence'].values()})}
                except Exception as error:record['planner']={'status':'held','error':str(error),'type':type(error).__name__}
                after=harness.snapshot(selected)
                # The planner resolves data only; no cached source/brief mutation.
                record['preserved_inputs_unchanged']=all(after.get(p)==v for p,v in original.items())
            else:record.update(mode=None,planner={'status':'not_called'},saved_directory_empty=not list(root.iterdir()))
            records.append(record)
    # A previously saved real-place brief must not be migrated by the new parser.
    with tempfile.TemporaryDirectory(prefix='world049-saved-',dir=H) as directory:
        job=research.create_job(research.brief_from_prompt('Build an original crew habitat.',mode=REAL,source_urls=sources,max_queries=0,max_pages=3),job_root=Path(directory))
        research.run_job(job,fetcher=synthetic_fetch);before=harness.snapshot(job);saved=research.read_json(job/'job.json')['brief']
        try:planner.plan_request(job);outcome='unexpected_prepared'
        except Exception as error:outcome=str(error)
        retained={'brief_mode':saved['research_mode'],'current_original_gate':research.original_generation_allowed(saved),'planner_outcome':outcome,'saved_bytes_unchanged':harness.snapshot(job)==before}
result={'which':options.which,'research_source_sha256':sha(research.__file__),'installed_workspace_sha256':sha(workspace.__file__),'installed_dispatcher_sha256':sha(K/'tools/world_chat_requests.py'),
    'cases':records,'saved_real_mode_preserved':retained,'models_workers_ui_network':0,'source_documents':'Authored synthetic fixture documents; no real facility facts or visual approval.'}
with (H/(options.which.upper()+'-CAPTURES.json')).open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'which':options.which,'cases':len(records),'planner_prepared':sum(r['planner']['status']=='prepared' for r in records)}))
