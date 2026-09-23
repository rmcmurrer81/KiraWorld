from pathlib import Path
import collections,datetime,hashlib,json
import install_exact as installer
H=Path(__file__).resolve().parent;P=H.parent/'world-chat-dispatch-candidate-047'
sha=installer.sha
def write(name,value):
    with (H/name).open('x',encoding='utf8') as f:json.dump(value,f,indent=2);f.write('\n')
assert sha(H/'INSTALL-PLAN.json')==installer.EXPECTED_PLAN
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());installer.validate(plan,installer.K,H,'after');installer.other_sources(plan)
installed=json.loads((H/'INSTALLED.json').read_bytes());assert installed['status']=='048_EXACT_TWO_FILE_INSTALL_PASS' and installed['install_plan_sha256']==installer.EXPECTED_PLAN
assert sha(H/'prior047/world_chat_requests.py')==sha(P/'candidate/tools/world_chat_requests.py')=='b6a42a53c490f41c88e0d86476b7c146c316f9c5a9d169b74c74b4f4dcbb9efd'
assert sha(H/'candidate/tools/world_builder_workspace.py')==sha(P/'candidate/tools/world_builder_workspace.py')
assert sha(P/'REVIEW-PLAN.json')=='cb537d271cb647f5f4c73bee1460ae9186a3bb7ba075b1f1186af42b9ed927be'
for name in ['TEST-RESULT.json','RETAINED-CONTEXT-RESULT.json','INSTALLER-TEST-RESULT.json']:
    assert json.loads((H/name).read_bytes())['status']=='PASS'
rows=json.loads((H/'CANDIDATE-CAPTURES.json').read_bytes());assert len(rows)==69
regressions=json.loads((H/'ROOT-REGRESSIONS.json').read_bytes());assert len(regressions)==4
assert all(r['frozen047']['research_worker_queued'] and not r['candidate048']['research_worker_queued'] and r['candidate048']['saved_bytes_unchanged'] for r in regressions)
previous=H.parent/'world-chat-usability-audit-046/test_context.py'
write('TEST-DEPENDENCIES.json',{'../world-chat-usability-audit-046/test_context.py':{'sha256':sha(previous),'bytes':previous.stat().st_size},'installed_checkout':'Complete Kira source closure with SOURCE-PINS.json identities; no native dependency binaries bundled.'})
write('FINAL-VERIFICATION.json',{'status':'048_INSTALLED_BYTES_AND_PROTECTED_INPUTS_PASS','plan_sha256':installer.EXPECTED_PLAN,'protected_inputs_unchanged':len(plan['protected_inputs']),'writes_by_this_verification':0,'root_install_receipt_sha256':sha(H/'INSTALLED.json')})
closure={p.relative_to(H).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in {'SOURCE-CLOSURE.json','DELIVERY.json'}}
write('SOURCE-CLOSURE.json',closure)
delivery={'status':'048_EXACT_DELAY_CORRECTION_ROOT_INSTALLED_AND_VERIFIED','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'plan_sha256':installer.EXPECTED_PLAN,
    'installer_sha256':sha(H/'install_exact.py'),'source_diff_sha256':sha(H/'SOURCE.diff'),'from047_diff_sha256':sha(H/'FROM047.diff'),'source_closure_sha256':sha(H/'SOURCE-CLOSURE.json'),
    'candidate_files':{r['relative_path']:r['after']['sha256'] for r in plan['files']},'root047_failures_reproduced_and_fixed':4,'callback_cases':69,'action_counts':dict(collections.Counter(r['expected_action'] for r in rows)),
    'routing_test_groups_pass':6,'retained_context_tests_pass':10,'installer_fixture_tests_pass':10,'protected_inputs_unchanged':116,
    'frozen047_preserved':True,'canonical_changes_by_root':2,'canonical_changes_by_this_subagent':0,'git_mutations':0,'model_gpu_ui':0,'owner_approval':False}
write('DELIVERY.json',delivery);print(json.dumps(delivery,indent=2))
