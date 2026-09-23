from pathlib import Path
import contextlib,hashlib,importlib.util,json,os,tempfile,unittest
from unittest.mock import patch
from harness import H,K,load,make,app,boundaries,snapshot,Preview
candidate=load('candidate');baseline=load('baseline')

CASES=[
 ('review_wait','Build a Mars base but wait before starting.','no_job'),
 ('review_negated_yet','Build a Mars base, but do not build a new world yet.','no_job'),
 ('review_home','Build a Mars base after I get home.','no_job'),
 ('review_not_now','Build a Mars base later, not now.','no_job'),
 ('polite_wait','Could you build a Mars base, but please wait until I return?','no_job'),
 ('hold_off','Build a habitat; hold off for now.','no_job'),
 ('negated_creation_yet',"Build a Mars base, but don't create the world yet.",'no_job'),
 ('return_deferred','Build a Mars base when I come back.','no_job'),
 ('not_right_now','Please build a habitat, not right now.','no_job'),
 ('no_weapons','Build a Mars base with no weapons.','research'),
 ('negative_content','Build a Mars base but do not build a laboratory.','research'),
 ('quoted_wait','Build a habitat with the sign "wait before starting".','research'),
 ('quoted_deferred','Build a habitat called "after I get home".','research'),
 ('quoted_not_now','Build a habitat called "not now".','research'),
 ('quoted_negated_yet','Build a habitat with a sign "do not build a new world yet".','research'),
 ('quoted_delayed_source','The source says "Build a Mars base after I get home."','no_job'),
 ('new_mars','Build a Mars base.','research'),
 ('polite_creation','Can you build a Mars base?','research'),
 ('please_creation','Please make a habitat.','research'),
 ('polite_research','Could you research the Louvre courtyard?','research'),
 ('new_rooms','Build a habitat with a galley, laboratory and two airlock doors.','research'),
 ('negative_room_constraint','Build a habitat, but do not build a laboratory.','research'),
 ('quoted_title','Build a habitat called "Do not build".','research'),
 ('quoted_target','Research "Mars habitats".','research'),
 ('original_crew_limit','Build an original crew habitat.','research'),
 ('negative','Do not build a new world.','no_job'),
 ('polite_negative',"Please don't research anything.",'no_job'),
 ('stop','Stop.','no_job'),
 ('plan','Plan a Mars habitat before building it.','no_job'),
 ('polite_plan','Can you plan a habitat?','no_job'),
 ('discuss','Discuss a galley layout with me.','no_job'),
 ('conditional','Build a Mars base if I approve.','no_job'),
 ('conditional_you','Build a habitat once you confirm.','no_job'),
 ('approval_noun','Build a habitat after my approval.','no_job'),
 ('approved_passive','Build a habitat once approved.','no_job'),
 ('later','Build a Mars base tomorrow.','no_job'),
 ('negative_later_clause',"Build a habitat, but don't start yet.",'no_job'),
 ('negative_it_clause','Build a habitat but do not build it yet.','no_job'),
 ('question_capability','Can this build a Mars base?','no_job'),
 ('question_how','How would you build a Mars base?','no_job'),
 ('room_question','Tell me what this room can do.','no_job'),
 ('quoted_only','"Build a Mars base."','no_job'),
 ('source_quote','The note says: "Export this world."','no_job'),
 ('quoted_source_single',"The script says 'Build a new habitat.'",'no_job'),
 ('compound','Build a habitat and then export it.','no_job'),
 ('ambiguous','Mars habitat','no_job'),
 ('edit_door','Make the current habitat airlock door wider.','no_job'),
 ('edit_color','Make the airlock door red.','no_job'),
 ('add_table','Add a dining table to this world.','no_job'),
 ('change_role','Change the laboratory into a galley.','no_job'),
 ('create_inside_current','Create a new room in my current habitat.','no_job'),
 ('build_existing_door','Build a door inside the existing habitat.','no_job'),
 ('research_edit_topic','Research doors for my current habitat.','research'),
 ('new_analog','Build an original habitat like my existing base.','research'),
 ('status','Show status.','status'),
 ('status_question',"What's the status?",'status'),
 ('status_project','Show me the status of my world.','status'),
 ('latest','Open latest saved world.','open_latest'),
 ('latest_polite','Please reopen my last saved habitat.','no_job'),
 ('latest_project','Reopen my latest saved project.','open_latest'),
 ('preview','Open current preview.','preview'),
 ('preview_polite','Could you show me the layout preview?','preview'),
 ('export','Export this world as a 3D package.','export'),
 ('export_polite','Can you export the selected world?','export'),
 ('export_package','Export a 3D package.','export'),
 ('resume','resume','resume'),
 ('resume_polite','Please resume research.','resume'),
 ('continue','Continue my world.','resume'),
 ('resume_quoted','The file says "resume research".','no_job'),
]

def capture_case(module,prompt,expected):
    with tempfile.TemporaryDirectory(prefix='world048-',dir=H) as directory:
        root=Path(directory)/'Data/world_research_jobs';root.mkdir(parents=True)
        prior=make(root,'Build an original habitat.');before=snapshot(root);a=app(module,root,prior);p=a._layout_preview;photos=a._reference_photos_view;components=a._original_components_view;events=[];exports=[]
        def inert_export(job,destination,*,preview_binding):
            exports.append({'job_id':job.name,'preview_job_id':Path(preview_binding['manifest_path']).parent.name if preview_binding else None})
            return {'status':'audit_inert','message':'Export audit boundary; no output created.'}
        a.chat_var.set(prompt)
        with boundaries(module,root,events,inert_export):a.send_world_builder_chat()
        after=snapshot(root);started=any(e.get('boundary')=='world-public-research' for e in events)
        opened=[e for e in events if 'preview_job' in e]
        selected=a._research_latest;job=json.loads((selected/'job.json').read_bytes()) if selected else None
        result={'prompt':prompt,'expected_action':expected,'new_research_job':selected!=prior,'research_worker_queued':started,
            'saved_bytes_unchanged':before==after,'preview_actions':opened,'export_actions':exports,'selected_job_id':selected.name if selected else None,
            'previous_preview_closed':p.closed,'same_preview_retained':a._layout_preview is p,'same_photos_retained':a._reference_photos_view is photos,'component_job_matches_selection':components.job==selected,
            'research_mode':job['brief']['research_mode'] if job else None,'brief_prompt':job['brief']['prompt'] if job else None,'messages':a.messages,'ui_models_network_exports':0}
        return result

class DispatcherTests(unittest.TestCase):
    def test_root_reported_failures_against_frozen047(self):
        spec=importlib.util.spec_from_file_location('prior047_helper',H/'prior047/world_chat_requests.py')
        prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
        old_workspace=load('candidate');old_workspace.classify_world_chat=prior.classify_world_chat
        records=[]
        for name,prompt,expected in CASES[:4]:
            with self.subTest(name=name):
                old=capture_case(old_workspace,prompt,expected);new=capture_case(candidate,prompt,expected)
                self.assertTrue(old['new_research_job']);self.assertTrue(old['research_worker_queued'])
                self.assertFalse(new['new_research_job']);self.assertFalse(new['research_worker_queued'])
                self.assertTrue(new['saved_bytes_unchanged']);self.assertTrue(new['same_preview_retained']);self.assertTrue(new['same_photos_retained'])
                records.append({'case':name,'frozen047':old,'candidate048':new})
        with (H/'ROOT-REGRESSIONS.json').open('x',encoding='utf-8') as f:json.dump(records,f,indent=2);f.write('\n')
    def test_owner_intents_through_actual_callback(self):
        records=[]
        for name,prompt,expected in CASES:
            with self.subTest(name=name):
                row=capture_case(candidate,prompt,expected);row['case']=name;records.append(row)
                if expected=='research':
                    self.assertTrue(row['new_research_job']);self.assertTrue(row['research_worker_queued']);self.assertFalse(row['preview_actions']);self.assertFalse(row['export_actions']);self.assertEqual(row['brief_prompt'],prompt)
                elif expected=='resume':
                    self.assertFalse(row['new_research_job']);self.assertTrue(row['research_worker_queued']);self.assertTrue(row['saved_bytes_unchanged']);self.assertTrue(row['same_preview_retained']);self.assertTrue(row['same_photos_retained'])
                else:
                    self.assertFalse(row['new_research_job']);self.assertFalse(row['research_worker_queued']);self.assertTrue(row['saved_bytes_unchanged'])
                    self.assertEqual(bool(row['preview_actions']),expected=='preview');self.assertEqual(bool(row['export_actions']),expected=='export')
                    if expected not in ('preview','open_latest'):self.assertTrue(row['same_preview_retained']);self.assertTrue(row['same_photos_retained'])
                if expected=='status':self.assertIn('saved research state',row['messages'][0])
                if expected=='open_latest':self.assertIn('Opened saved research',row['messages'][0])
                if name=='original_crew_limit':self.assertEqual(row['research_mode'],'real_place_reconstruction')
        with (H/'CANDIDATE-CAPTURES.json').open('x',encoding='utf-8') as f:json.dump(records,f,indent=2);f.write('\n')
    def test_latest_selection_uses_catalog_order_and_preserves_files(self):
        with tempfile.TemporaryDirectory(prefix='world048-latest-',dir=H) as directory:
            root=Path(directory)/'jobs';root.mkdir();first=make(root,'Build a Mars base.');second=make(root,'Build a habitat.')
            os.utime(first/'job.json',ns=(1000000000,1000000000));os.utime(second/'job.json',ns=(2000000000,2000000000))
            before=snapshot(root);a=app(candidate,root,first);a.chat_var.set('Open latest saved world.');events=[]
            with boundaries(candidate,root,events):a.send_world_builder_chat()
            self.assertEqual(a._research_latest,second);self.assertEqual(snapshot(root),before);self.assertEqual(events,[])
    def test_damaged_latest_does_not_silently_open_older_world(self):
        with tempfile.TemporaryDirectory(prefix='world048-damaged-',dir=H) as directory:
            root=Path(directory)/'jobs';root.mkdir();first=make(root,'Build a Mars base.');second=make(root,'Build a habitat.')
            (second/'job.json').write_text('{damaged');os.utime(first/'job.json',ns=(1000000000,1000000000));os.utime(second/'job.json',ns=(2000000000,2000000000))
            before=snapshot(root);a=app(candidate,root,first);a.chat_var.set('Open latest saved world.');events=[]
            with boundaries(candidate,root,events):a.send_world_builder_chat()
            self.assertIsNone(a._research_latest);self.assertIn('could not be opened',a.messages[-1]);self.assertEqual(snapshot(root),before);self.assertEqual(events,[])
    def test_missing_selection_commands_do_not_create_jobs(self):
        for prompt in ['Show status.','Open latest saved world.','Open current preview.','Export this world.']:
            with self.subTest(prompt=prompt),tempfile.TemporaryDirectory(prefix='world048-empty-',dir=H) as directory:
                root=Path(directory)/'jobs';root.mkdir();a=app(candidate,root,None);a.chat_var.set(prompt);events=[]
                with boundaries(candidate,root,events):a.send_world_builder_chat()
                self.assertIsNone(a._research_latest);self.assertEqual(snapshot(root),{});self.assertEqual(events,[]);self.assertTrue(a.messages)
    def test_stop_message_does_not_claim_existing_worker_cancelled(self):
        with tempfile.TemporaryDirectory(prefix='world048-stop-',dir=H) as directory:
            root=Path(directory)/'jobs';root.mkdir();prior=make(root,'Build a Mars base.');a=app(candidate,root,prior);running=object();a._research_worker=running;a.chat_var.set('Stop.');events=[]
            with boundaries(candidate,root,events):a.send_world_builder_chat()
            self.assertIs(a._research_worker,running);self.assertIn('does not cancel a worker',a.messages[0]);self.assertEqual(events,[])

if __name__=='__main__':
    baseline_rows=[]
    for name,prompt,expected in CASES:
        row=capture_case(baseline,prompt,expected);row['case']=name;baseline_rows.append(row)
    with (H/'BASELINE-CAPTURES.json').open('x',encoding='utf-8') as f:json.dump(baseline_rows,f,indent=2);f.write('\n')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DispatcherTests))
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'command_cases':len(CASES),'failures':[str(e) for e in result.failures],'errors':[str(e) for e in result.errors],'actual_workspace_callbacks':True,'actual_disposable_saved_services':True,'research_models_preview_export_boundaries':'inert','canonical_ui_gpu_model_changes':0}
    with (H/'TEST-RESULT.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
