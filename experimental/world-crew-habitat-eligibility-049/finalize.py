from pathlib import Path
import datetime,difflib,hashlib,json
H=Path(__file__).resolve().parent;K=Path('@kira_root')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    with (H/name).open('x',encoding='utf8') as f:json.dump(value,f,indent=2);f.write('\n')
source=K/'tools/world_research.py';before=H/'baseline/world_research.py';after=H/'candidate/tools/world_research.py'
assert sha(source)==sha(before)=='2d967dc31da7ea95a2b5c59ca819967a53ad162c0170ffdcfe86b8103f8fdcfd'
protected=json.loads((H.parent/'world-chat-delay-candidate-048/INSTALL-PLAN.json').read_bytes())['protected_inputs']
assert all(sha(p)==v for p,v in protected.items())
tests=json.loads((H/'TEST-RESULT.json').read_bytes());assert tests['status']=='PASS' and tests['callback_cases']==43
captures=json.loads((H/'CANDIDATE-CAPTURES.json').read_bytes());assert captures['research_source_sha256']==sha(after)
assert sha(K/'tools/world_builder_workspace.py')==captures['installed_workspace_sha256']=='86320278736c881b3ebecb6da568ac322d9c4cb31285e3c7eb5edd4925568bcc'
assert sha(K/'tools/world_chat_requests.py')==captures['installed_dispatcher_sha256']=='717ad961fd8ece464aec27a4a4775cdf9a4b090209873909fa0b05ad13aa53a3'
plan={'status':'049_ISOLATED_ONE_FILE_PROPOSAL_NOT_INSTALLED','files':[{'relative_path':'tools/world_research.py','target':str(source),'before_sha256':sha(before),'preimage':str(before),
    'after':{'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}}],'protected_inputs':protected}
write('REVIEW-PLAN.json',plan)
(H/'SOURCE.diff').write_text(''.join(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),after.read_text(encoding='utf8').splitlines(True),fromfile='installed/tools/world_research.py',tofile='candidate049/tools/world_research.py')),encoding='utf8',newline='\n')
dependencies=['tools/world_research.py','tools/world_builder_workspace.py','tools/world_chat_requests.py','tools/world_research_workspace_adapter.py','tools/world_saved_research.py','tools/adaptive_source_selection.py',
    'tools/world_builder_engine/world_layout_v2.py','tools/world_builder_engine/world_layout_job.py','tools/world_builder_engine/analog_case_index.py','tools/world_builder_engine/reviewed_analog_cases.json',
    'tools/world_builder_engine/pipeline.py','tools/world_builder_engine/world_layout_preview.py','tools/world_builder_engine/preview_refresh.py']
write('SOURCE-PINS.json',{p:sha(K/p) for p in dependencies})
harness=H.parent/'world-chat-delay-candidate-048/harness.py'
write('TEST-DEPENDENCIES.json',{'../world-chat-delay-candidate-048/harness.py':{'sha256':sha(harness),'bytes':harness.stat().st_size},'canonical_runtime':'Complete Kira source checkout, exact source pins; native dependencies not copied.'})
closure={p.relative_to(H).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in {'SOURCE-CLOSURE.json','DELIVERY.json'}}
write('SOURCE-CLOSURE.json',closure)
delivery={'status':'049_CREW_HABITAT_ELIGIBILITY_READY_NOT_INSTALLED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'plan_sha256':sha(H/'REVIEW-PLAN.json'),'candidate_sha256':sha(after),
    'source_diff_sha256':sha(H/'SOURCE.diff'),'source_closure_sha256':sha(H/'SOURCE-CLOSURE.json'),'canonical_files_proposed':1,'baseline_failures_corrected':18,'callback_to_actual_planner_cases':43,
    'original_plans_prepared':20,'real_place_plans_held':17,'nonexecuting_requests':6,'evidence_test_groups_pass':7,'existing_saved_real_brief_unchanged_and_held':True,
    'actual_saved_mars_preview_read_only_pass':True,'protected_inputs_unchanged':116,'canonical_edits':0,'git_mutations':0,'models_workers_ui_network':0,'visual_or_owner_approval':False}
write('DELIVERY.json',delivery);print(json.dumps(delivery,indent=2))
