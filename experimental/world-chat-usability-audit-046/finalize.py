from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;K=Path('@kira_root')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((H/'REVIEW-PLAN.json').read_bytes())
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
assert all(sha(K/r)==v for r,v in json.loads((H/'SOURCE-PINS.json').read_bytes()).items())
for row in plan['files']:assert sha(row['target'])==row['before_sha256'] and sha(row['after']['path'])==row['after']['sha256']
b=json.loads((H/'BASELINE-CHAT-CAPTURES.json').read_bytes());c=json.loads((H/'CANDIDATE-CHAT-CAPTURES.json').read_bytes());test=json.loads((H/'TEST-RESULT.json').read_bytes())
assert len(b['cases'])==len(c['cases'])==15 and test['status']=='PASS' and test['tests_run']==11
assert c['source_sha256']==test['source_sha256']==plan['files'][0]['after']['sha256']
fields=['case','prompt','new_research_job','selected_job_subject','research_mode','original_generation_allowed','preview_action_dispatched','export_action_dispatched','boundary_events','messages','prior_saved_bytes_unchanged','native_window_network_or_model_calls']
for old,new in zip(b['cases'],c['cases']):
    assert all(old[k]==new[k] for k in fields)
    if new['new_research_job']:
        assert old['stale_old_preview_retained'] and not new['stale_old_preview_retained']
        assert new['old_preview_closed'] and new['old_reference_view_closed'] and new['component_bound_to_selection']
    else:assert not new['old_preview_closed'] and not new['old_reference_view_closed']
files=['candidate/tools/world_builder_workspace.py','baseline/world_builder_workspace.py','harness.py','test_context.py','stage.py','revise.py','finalize.py','CHANGES.patch','ASSESSMENT.md','BASELINE-CHAT-CAPTURES.json','CANDIDATE-CHAT-CAPTURES.json','TEST-RESULT.json','REVIEW-PLAN.json','SOURCE-PINS.json']
closure={p:{'sha256':sha(H/p),'bytes':(H/p).stat().st_size} for p in files}
with (H/'SOURCE-CLOSURE.json').open('x',encoding='utf-8') as f:json.dump(closure,f,indent=2);f.write('\n')
result={'status':'046_ISOLATED_CHAT_SELECTION_FIX_AND_MEASURED_USABILITY_GAPS_READY','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'review_plan_sha256':sha(H/'REVIEW-PLAN.json'),'candidate_sha256':c['source_sha256'],'source_closure_sha256':sha(H/'SOURCE-CLOSURE.json'),'changed_canonical_files_proposed':1,
    'actual_chat_cases':15,'context_switch_cases':13,'baseline_stale_previews':13,'candidate_stale_previews':0,'focused_tests_pass':11,
    'actual_services_executed':['brief parser','saved job creation in disposable state','saved catalog/selection','export selection guard'],'inert_boundaries':['research and model worker','preview opening','destination chooser','export generation'],
    'all_other_captured_routing_outcomes_identical':True,'protected_originals_unchanged':116,'canonical_edits':0,'git_mutations':0,'models_gpu_browser_native_ui':0,
    'remaining_gaps':['Chat room/door editing','Chat open/reopen/preview/export dispatch','Chat questions and negations submit research','Original crew-habitat modifier grammar'],'native_ui_or_owner_approval':False}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
