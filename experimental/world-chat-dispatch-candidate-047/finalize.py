from pathlib import Path
import collections,datetime,difflib,hashlib,json

H=Path(__file__).resolve().parent
K=Path('@kira_root')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    with (H/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2);f.write('\n')

plan_path=H/'REVIEW-PLAN.json'
plan=json.loads(plan_path.read_bytes())
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
for row in plan['files']:
    target=Path(row['target'])
    if row['before_sha256'] is None:
        assert not target.exists()
    else:
        assert sha(target)==row['before_sha256']==sha(row['preimage'])
    candidate=Path(row['after']['path'])
    row['after'].update(sha256=sha(candidate),bytes=candidate.stat().st_size)
assert not (H/'DELIVERY.json').exists()
plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
old=(H/'baseline/world_builder_workspace.py').read_text(encoding='utf-8')
new=(H/'candidate/tools/world_builder_workspace.py').read_text(encoding='utf-8')
helper=(H/'candidate/tools/world_chat_requests.py').read_text(encoding='utf-8')
diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='installed046/tools/world_builder_workspace.py',tofile='candidate047/tools/world_builder_workspace.py'))
diff+=''.join(difflib.unified_diff([],helper.splitlines(True),fromfile='/dev/null',tofile='candidate047/tools/world_chat_requests.py'))
(H/'SOURCE.diff').write_text(diff,encoding='utf-8',newline='\n')
pins=json.loads((H.parent/'world-chat-usability-audit-046/SOURCE-PINS.json').read_bytes())
pins['tools/world_builder_workspace.py']=sha(K/'tools/world_builder_workspace.py')
assert all(sha(K/p)==v for p,v in pins.items())
write('SOURCE-PINS.json',pins)
previous=H.parent/'world-chat-usability-audit-046/test_context.py'
write('TEST-DEPENDENCIES.json',{'../world-chat-usability-audit-046/test_context.py':{'sha256':sha(previous),'bytes':previous.stat().st_size},'canonical_runtime':'Complete Kira checkout with SOURCE-PINS.json identities; no local native dependency binaries bundled.'})
b=json.loads((H/'BASELINE-CAPTURES.json').read_bytes());c=json.loads((H/'CANDIDATE-CAPTURES.json').read_bytes())
test=json.loads((H/'TEST-RESULT.json').read_bytes());retained=json.loads((H/'RETAINED-CONTEXT-RESULT.json').read_bytes())
assert len(b)==len(c)==53 and test['status']==retained['status']=='PASS' and test['tests_run']==5 and retained['tests_run']==10
assert retained['prior_source_sha256']==sha(previous)
for row in c:
    if row['expected_action']=='research':assert row['brief_prompt']==row['prompt'] and row['new_research_job']
    else:assert not row['new_research_job']
closure={p.relative_to(H).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in {'SOURCE-CLOSURE.json','DELIVERY.json'}}
write('SOURCE-CLOSURE.json',closure)
delivery={'status':'047_ISOLATED_DISPATCHER_READY_FOR_ROOT_REVIEW','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
    'review_plan_sha256':sha(plan_path),'source_diff_sha256':sha(H/'SOURCE.diff'),'source_closure_sha256':sha(H/'SOURCE-CLOSURE.json'),
    'candidate_files':{r['relative_path']:r['after']['sha256'] for r in plan['files']},'callback_fixture_count':len(c),'action_counts':dict(collections.Counter(r['expected_action'] for r in c)),
    'baseline_unwanted_jobs':sum(r['new_research_job'] for r in b if r['expected_action'] not in ('research','resume')),'candidate_unwanted_jobs':0,
    'baseline_resume_newjobs':sum(r['new_research_job'] for r in b if r['expected_action']=='resume'),'candidate_resume_newjobs':0,
    'test_groups_pass':5,'retained_context_tests_pass':10,'protected_inputs_unchanged':len(plan['protected_inputs']),
    'canonical_changes':0,'git_mutations':0,'models_gpu_native_ui_browser':0,'owner_approval':False,
    'inert_boundaries':['research/model worker','preview launch','destination chooser','export generation'],
    'remaining_gaps':['General conversation and planning','Existing room/door/furniture edits','Named or type-filtered saved-world selection','Original crew-habitat parser modifier','Cancel already-running research worker']}
write('DELIVERY.json',delivery)
print(json.dumps(delivery,indent=2))
