"""Durable at-most-two-attempt original layout pipeline; no automatic replay."""
from __future__ import annotations
from contextlib import contextmanager
import copy,hashlib,json,uuid
from pathlib import Path

from world_research import atomic_json,job_lock,read_json,ResearchError,original_generation_allowed
from . import world_layout_v2 as planner
from .world_layout_job import load_research,MODEL
from .model_client import LocalModelClient
from .analog_case_index import prepare_case_index, CaseEvidenceRequired

ENGINE=Path(__file__).resolve().parent
PROJECT=ENGINE.parents[1]
CONTRACT='native_original_layout_pipeline_v1'
MAX_MODEL_ATTEMPTS=2


def file_pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def verify_pin(row):
    if file_pin(row['path'])!=row:raise ValueError('Preserved pipeline artifact changed: '+row['path'])


def identity():
    result={p.name:file_pin(p)['sha256'] for p in sorted(ENGINE.iterdir()) if p.suffix in {'.py','.mjs','.html','.css','.json'}}
    result.update({'installed_'+key:value for key,value in planner.toolchain().items() if key in {'research','research_selector'}})
    return result


def save(path,state):
    state={k:v for k,v in state.items() if k!='receipt_sha256'}
    state['receipt_sha256']=planner.digest(state);atomic_json(Path(path),state)
    # A prepared recovery revision is mutable while it runs; keep its selected
    # state pin current. A crash between these writes fails closed on reopening.
    if state.get('job_dir'):
        pointer=Path(state['job_dir'])/'latest-layout-pipeline.json'
        if pointer.exists() and Path(read_json(pointer)['state']['path']).resolve()==Path(path).resolve():
            atomic_json(pointer,{'state':file_pin(path),'stage':state['stage'],'preview':state.get('preview')})


def saved(path):
    value=read_json(Path(path))
    if planner.digest({k:v for k,v in value.items() if k!='receipt_sha256'})!=value.get('receipt_sha256'):
        raise ValueError('Pipeline state seal changed')
    for row in value.get('artifacts',[]):verify_pin(row)
    for key in ('reused_program','cpu_request'):
        if value.get(key):verify_pin(value[key])
    if value.get('repair_authorization'):
        for key in ('predecessor_state','prior_request','prior_response','prepared_request'):
            verify_pin(value['repair_authorization'][key])
    for attempt in value.get('attempts',[]):
        for key in ('request','response'):
            if attempt.get(key):verify_pin(attempt[key])
    return value


def immutable(path,value):
    with Path(path).open('xb') as stream:stream.write(planner.canonical(value))
    return file_pin(path)


def parse_program(raw):
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>300_000:raise ValueError('Model program missing or beyond response bound')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate model JSON field: '+key)
            result[key]=value
        return result
    def bad(_):raise ValueError('Nonfinite model JSON value')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=bad)


def call_accounting(state):
    dispatched=0;undispatched=0;uncertain=0
    for attempt in state.get('attempts',[]):
        outcome=read_json(Path(attempt['response']['path'])) if attempt.get('response') else None
        if outcome is not None and outcome.get('dispatched') is False:
            if attempt.get('status')!='not_dispatched':raise ValueError('Undispatched admission receipt conflicts with state')
            undispatched+=1
        elif outcome is not None and outcome.get('dispatched') is True:dispatched+=1
        else:
            if attempt.get('status')=='not_dispatched':raise ValueError('Undispatched claim has no exact receipt')
            uncertain+=1
    return {'dispatched_model_calls':dispatched,'undispatched_admission_checks':undispatched,
            'uncertain_model_calls':uncertain,'model_attempts':dispatched+uncertain}


def view(state,path=None):
    return {'contract':CONTRACT,'stage':state['stage'],'message':state.get('message',''),
            'job_dir':state.get('job_dir'),'state_path':str(path) if path else None,
            **call_accounting(state),
            'preview':state.get('preview'),'geometry_generated':bool(state.get('compiled_result')),
            'case_index':state.get('case_index'),
            'world_ready':False,'real_rooms_unlocked':False,'resident_worlds_modified':False}


def check_job_path(job_dir):
    job_dir=Path(job_dir).resolve()
    if job_dir.parent!=PROJECT/'Data'/'world_research_jobs' or not job_dir.name.startswith('world_research_'):
        raise ValueError('Pipeline requires this installation’s saved research job directory')
    return job_dir


def notify(callback,stage,message):
    if callback:callback({'stage':stage,'message':message})


def current_state(job_dir,packet_sha):
    base=job_dir/('layout_pipeline_'+packet_sha[:20])
    pointer=job_dir/'latest-layout-pipeline.json'
    if pointer.exists():
        item=read_json(pointer);target=Path(item['state']['path']).resolve()
        if target.is_relative_to(base.resolve()):
            verify_pin(item['state']);return target
    return base/'state.json'


def prepare_preview(job_dir,folder,path,state,builder,progress):
    notify(progress,'Preparing preview','Building the isolated layout preview; materials remain unfinished.')
    try:
        if builder is None:
            from .world_layout_preview import create_preview
            builder=create_preview
        state['preview']=builder(folder/'compiled_geometry.json',job_dir/'research_packet.json',folder/'blueprint.json')
        state.update(stage='preview_ready',message='Original layout preview ready. Open Layout Preview to explore; materials and visual detail remain unfinished.')
    except Exception as exc:
        state.update(stage='preview_preparation_held',message='Layout preserved; preview preparation needs attention: '+str(exc))
    save(path,state)
    atomic_json(job_dir/'latest-layout-pipeline.json',{'state':file_pin(path),'stage':state['stage'],'preview':state.get('preview')})
    notify(progress,state['stage'],state['message'])
    return view(state,path)


def complete_saved_response(state):
    """Only a durably returned exact-model response with observed cleanup is reusable."""
    if not state.get('attempts'):return None
    attempt=state['attempts'][-1]
    if attempt.get('status') not in {'returned','validated'} or not attempt.get('response'):return None
    verify_pin(attempt['response']);outcome=read_json(Path(attempt['response']['path']))
    response=outcome.get('response')
    if (outcome.get('cleanup_verified') is True and not outcome.get('error') and
        isinstance(response,dict) and response.get('model')==MODEL and response.get('done') is True):
        return response
    return None


def cpu_revalidate(job_dir,prior,packet_sha,request,builder,progress,reusable_response=None):
    """Reuse successful saved program; fresh CPU validation, no model client call."""
    notify(progress,'Revalidating saved layout','Rechecking the preserved room program and rebuilding its preview without a model call.')
    pin=next((p for p in prior['artifacts'] if Path(p['path']).name=='room_program.json'),None)
    response=None
    if pin:verify_pin(pin)
    else:
        response=reusable_response or complete_saved_response(prior)
        if response is None:raise ValueError('No complete cleanup-verified saved program is available for CPU recovery')
    # This lane is already locked. Short serial folders also support installations
    # whose parent paths approach the Windows legacy path-length limit.
    base=job_dir/('layout_pipeline_'+packet_sha[:20]);serial=1
    while (base/('r'+str(serial))).exists():serial+=1
    folder=base/('r'+str(serial));folder.mkdir()
    path=folder/'state.json';state={**copy.deepcopy(prior),'engine_identity':identity(),'stage':'cpu_revalidation_running',
                                  'preview':None,'reused_program':pin,'cpu_revision':True,'artifacts':[]}
    state['cpu_request']=immutable(folder/'cpu-request.json',request);save(path,state)
    try:
        if response and response.get('done_reason')=='length':raise ValueError('Saved response exceeded the model response length; no automatic model retry.')
        program=parse_program(Path(pin['path']).read_text(encoding='utf-8') if pin else response.get('message',{}).get('content'))
        compiled=planner.validate_and_compile(program,request)
    except (ValueError,KeyError,TypeError) as exc:
        state.update(stage='cpu_revalidation_held',message='Saved program preserved; CPU validation requires a correction: '+str(exc),artifacts=copy.deepcopy(prior['artifacts']))
        save(path,state);return view(state,path)
    for name,value in [('room_program.json',program),('blueprint.json',compiled['blueprint']),('compiled_geometry.json',compiled['compiled_geometry']),
                       ('navigation_result.json',compiled['navigation_result']),('compiled_result.json',compiled)]:
        state['artifacts'].append(immutable(folder/name,value))
    state['compiled_result']=state['artifacts'][-1]
    return prepare_preview(job_dir,folder,path,state,builder,progress)


def prepare_repair_revision(job_dir,expected_state_sha256,*,preview_builder=None,on_progress=None):
    """Explicit authorization for one remaining repair; preparation performs CPU work only.

    Ordinary resume never calls this function. The predecessor is preserved and
    every historical dispatch/unknown claim remains in the successor budget.
    """
    job_dir=check_job_path(job_dir);_,packet_sha,_,_=load_research(job_dir)
    prepare_case_index(job_dir)
    request=planner.plan_request(job_dir)
    base=job_dir/('layout_pipeline_'+packet_sha[:20]);lane=job_dir.parent/'.original-layout-lane';lane.mkdir(exist_ok=True)
    with job_lock(lane):
        with job_lock(base):
            path=current_state(job_dir,packet_sha)
            if file_pin(path)['sha256']!=expected_state_sha256:raise ValueError('The selected held state changed; explicit recovery must name its exact current hash')
            prior=saved(path);account=call_accounting(prior)
            if prior.get('repair_authorization'):raise ValueError('This packet already has an explicit recovery revision; use its existing resume path')
            if prior.get('compiled_result'):raise ValueError('Use normal CPU preview resume for a successful saved layout')
            if account['dispatched_model_calls']!=1 or account['uncertain_model_calls']:
                raise ValueError('Explicit repair requires exactly one known dispatched call and no uncertain calls')
            if any(a['status'] not in {'invalid','not_dispatched'} for a in prior['attempts']):
                raise ValueError('Only a known validation failure with undispatched admission checks can be repaired')
            actual=next(a for a in prior['attempts'] if a['status']=='invalid')
            outcome=read_json(Path(actual['response']['path']));response=outcome.get('response')
            if (outcome.get('dispatched') is not True or outcome.get('cleanup_verified') is not True or outcome.get('error')
                or not isinstance(response,dict) or response.get('model')!=MODEL or response.get('done') is not True):
                raise ValueError('Recovery requires an exact complete response with confirmed cleanup')
            original=read_json(Path(actual['request']['path']))
            if (original['request']['research_packet_sha256']!=packet_sha or original['model_payload']['model']!=MODEL
                or original['model_payload']['messages']!=original['request']['messages']):
                raise ValueError('Preserved request does not match this packet and exact local model')
            try:
                if response.get('done_reason')=='length':raise ValueError('The saved program reached its response limit; return a concise complete room program.')
                program=parse_program(response.get('message',{}).get('content'))
                planner.validate_and_compile(program,request)
            except (ValueError,KeyError,TypeError) as exc:feedback=str(exc)[:1600]
            else:
                return cpu_revalidate(job_dir,prior,packet_sha,request,preview_builder,on_progress,reusable_response=response)
            request=planner.plan_request(job_dir,feedback)
            serial=1
            while (base/('r'+str(serial))).exists():serial+=1
            folder=base/('r'+str(serial));folder.mkdir();new_path=folder/'state.json'
            authorization={'kind':'explicit_one_remaining_repair','maximum_dispatched_calls':MAX_MODEL_ATTEMPTS,
                           'predecessor_state':file_pin(path),'prior_request':actual['request'],'prior_response':actual['response'],
                           'prepared_request':immutable(folder/'repair-request.json',request)}
            state={**copy.deepcopy(prior),'engine_identity':identity(),'stage':'repair_ready',
                   'message':'One remaining repair is explicitly prepared from the preserved response. Resume this job to run it after fresh capacity checks.',
                   'repair_authorization':authorization,'preview':None}
            save(new_path,state)
            atomic_json(job_dir/'latest-layout-pipeline.json',{'state':file_pin(new_path),'stage':state['stage'],'preview':None})
            return view(state,new_path)


def run_pipeline(job_dir,*,client=None,preview_builder=None,on_progress=None):
    job_dir=check_job_path(job_dir)
    packet,packet_sha,brief,_=load_research(job_dir)
    if packet['research_mode']!='analog_to_original' or not original_generation_allowed(brief):
        return view({'stage':'real_place_research_only','job_dir':str(job_dir),
                     'message':'Real places remain in research. Photos and plans need inspection before any accessible reconstruction.'})
    case_index=prepare_case_index(job_dir)
    try:request=planner.plan_request(job_dir)
    except CaseEvidenceRequired as exc:
        return view({'stage':'more_distinct_analog_cases_needed','job_dir':str(job_dir),
                     'message':str(exc),'case_index':case_index})
    except (ValueError,KeyError,TypeError) as exc:
        return view({'stage':'more_usable_analog_sources_needed','job_dir':str(job_dir),'message':str(exc)})
    folder=job_dir/('layout_pipeline_'+packet_sha[:20]);folder.mkdir(exist_ok=True)
    # One cooperative local model lane across all native builder jobs.
    lane=job_dir.parent/'.original-layout-lane';lane.mkdir(exist_ok=True)
    try:
        with job_lock(lane):
            with job_lock(folder):
                path=current_state(job_dir,packet_sha)
                return _run(job_dir,path.parent,path,packet_sha,request,client or LocalModelClient(),preview_builder,on_progress)
    except ResearchError as exc:
        if 'already running' not in str(exc):raise
        return view({'stage':'model_lane_busy','job_dir':str(job_dir),'message':'Another original-layout worker owns the model lane; no model was dispatched.'})


def _run(job_dir,folder,path,packet_sha,request,client,preview_builder,progress):
    chain=identity()
    if path.exists():
        state=saved(path)
        if state['research_packet_sha256']!=packet_sha:
            return view({**state,'stage':'source_revalidation_required','message':'Research or engine code changed; preserved layout requires review.'},path)
        if state.get('compiled_result') and (state['engine_identity']!=chain or state['stage']!='preview_ready'):
            return cpu_revalidate(job_dir,state,packet_sha,request,preview_builder,progress)
        if not state.get('compiled_result') and complete_saved_response(state) is not None:
            return cpu_revalidate(job_dir,state,packet_sha,request,preview_builder,progress)
        if state['engine_identity']!=chain:
            return view({**state,'stage':'source_revalidation_required','message':'Engine code changed before a successful room program; existing model attempts remain held.'},path)
        if state['stage']=='preview_ready':
            from .world_layout_preview import verify_preview
            verify_preview(state['preview']['manifest_path'],state['preview']['manifest_sha256'])
            return view(state,path)
        # A previous dispatched/returned/interrupted attempt is never dispatched
        # again by re-entering this function, including an unfinished repair.
        account=call_accounting(state)
        explicitly_prepared=bool(state.get('repair_authorization')) and account['model_attempts']<MAX_MODEL_ATTEMPTS
        if explicitly_prepared:
            authorization=state['repair_authorization']
            if (authorization.get('kind')!='explicit_one_remaining_repair' or authorization.get('maximum_dispatched_calls')!=2
                or account['dispatched_model_calls']!=1 or account['uncertain_model_calls']):
                raise ValueError('Explicit recovery dispatch budget is invalid')
            request=read_json(Path(authorization['prepared_request']['path']))
        elif any(a.get('status')!='not_dispatched' for a in state['attempts']):
            if state['stage']=='layout_model_running':
                state.update(stage='interrupted_attempt_held',message='A prior worker ended without completing this claimed attempt. Dispatch/cleanup is uncertain; no automatic replay.')
                save(path,state)
            return view({**state,'message':state.get('message','')+' Automatic model replay is held; prior attempts remain consumed.'},path)
    else:
        state={'contract':CONTRACT,'job_dir':str(job_dir),'research_packet_sha256':packet_sha,'engine_identity':chain,
               'stage':'ready','attempts':[],'artifacts':[],'world_ready':False,'resident_worlds_modified':False}
        save(path,state)
    notify(progress,'Checking local capacity','Checking model availability, free RAM and VRAM before planning.')
    admission=client.inspect()
    if not admission.get('available'):
        state.update(stage=admission.get('hold_stage') or ('model_busy' if admission.get('busy') else 'model_unavailable'),
                     message=admission.get('message','Local model unavailable'),admission=admission)
        save(path,state);return view(state,path)
    for model_attempt in range(call_accounting(state)['model_attempts']+1,MAX_MODEL_ATTEMPTS+1):
        if identity()!=chain:raise ValueError('Engine changed before model dispatch')
        fresh=planner.plan_request(job_dir,request.get('feedback'))
        if fresh!=request:raise ValueError('Research changed before model dispatch')
        serial=len(state['attempts'])+1;prefix=folder/('attempt-'+str(serial))
        payload=client.payload(request['messages'])
        attempt={'serial':serial,'model_attempt':model_attempt,'status':'dispatch_claimed',
                 'request':immutable(Path(str(prefix)+'-request.json'),{'request':request,'model_payload':payload})}
        state['attempts'].append(attempt);state.update(stage='layout_model_running',message='Writing an original room program; attempt '+str(model_attempt)+' of 2.')
        save(path,state)
        notify(progress,'Checking generation admission','Checking capacity for attempt '+str(model_attempt)+' of 2; it has not been dispatched yet.')
        try:outcome=client.generate(payload,allow_repair_resample=model_attempt>1,on_progress=progress)
        except BaseException as exc:
            # A killed process leaves the prior dispatch_claimed receipt. Neither
            # transport uncertainty nor a missing response permits an automatic retry.
            state.update(stage='model_dispatch_uncertain',message='Model dispatch outcome is uncertain: '+str(exc))
            attempt['status']='dispatch_uncertain';save(path,state);return view(state,path)
        attempt['response']=immutable(Path(str(prefix)+'-response.json'),outcome)
        if outcome.get('dispatched') is False:
            attempt['status']='not_dispatched';admission=outcome.get('admission',{})
            stage=admission.get('hold_stage') or ('model_busy' if admission.get('busy') else 'capacity_held')
            state.update(stage=stage,message=admission.get('message','Capacity could not be admitted.')+' No model call was dispatched by this admission check.')
            save(path,state);return view(state,path)
        response=outcome.get('response')
        if outcome.get('cleanup_verified') is not True:
            attempt['status']='cleanup_unverified';state.update(stage='model_cleanup_unverified',message='Local model cleanup is not verified. The response and attempt are preserved; no retry.')
            save(path,state);return view(state,path)
        if outcome.get('error') or not isinstance(response,dict) or response.get('model')!=MODEL or response.get('done') is not True:
            attempt['status']='returned_incomplete';state.update(stage='model_response_held',message='No complete, exact model response. No automatic retry.')
            save(path,state);return view(state,path)
        attempt['status']='returned';save(path,state)
        try:
            notify(progress,'Validating and compiling','Checking evidence, required rooms, connections and supported walking routes.')
            if response.get('done_reason')=='length':raise ValueError('The room program exceeded the model response length; make the program concise.')
            program=parse_program(response.get('message',{}).get('content'))
            compiled=planner.validate_and_compile(program,request)
        except (ValueError,KeyError,TypeError) as exc:
            attempt.update(status='invalid',validation_error=str(exc)[:1600])
            state.update(stage='layout_validation_failed',message=attempt['validation_error'])
            save(path,state)
            if model_attempt==MAX_MODEL_ATTEMPTS:return view(state,path)
            # Exactly one repair inside this uninterrupted run, carrying explicit
            # validation feedback. A later process does not resume this loop.
            notify(progress,'Validation retry','One repair remains: '+attempt['validation_error'])
            request=planner.plan_request(job_dir,attempt['validation_error']);continue
        attempt['status']='validated'
        for name,value in [('room_program.json',program),('blueprint.json',compiled['blueprint']),
                           ('compiled_geometry.json',compiled['compiled_geometry']),('navigation_result.json',compiled['navigation_result']),('compiled_result.json',compiled)]:
            state['artifacts'].append(immutable(folder/name,value))
        state.update(stage='layout_ready',compiled_result=state['artifacts'][-1],message='Original room layout compiled; appearance is unfinished.')
        save(path,state)
        return prepare_preview(job_dir,folder,path,state,preview_builder,progress)


def latest_preview(job_dir):
    job_dir=check_job_path(job_dir)
    _,packet_sha,brief,_=load_research(job_dir)
    if not original_generation_allowed(brief):raise ValueError('Real-place research cannot open an original-layout preview')
    path=current_state(job_dir,packet_sha)
    state=saved(path)
    # Viewing a preserved result does not generate a new world. Its exact
    # manifest/source/asset pins below remain authoritative even after a planner
    # or case-gate upgrade; changed preview assets still fail verification.
    if state['stage']!='preview_ready' or state['research_packet_sha256']!=packet_sha:
        raise ValueError('No current verified layout preview is ready')
    from .world_layout_preview import verify_preview
    verify_preview(state['preview']['manifest_path'],state['preview']['manifest_sha256'])
    return state['preview']
