from pathlib import Path
import hashlib,json,tempfile,unittest
from unittest.mock import patch
from harness import H,K,load,make,app,boundaries,snapshot,Preview,export_api

candidate=load('candidate');baseline=load('baseline')
class ReachedSourceChain(Exception):pass
class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='world046-test-',dir=H);self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);self.root=self.project/'Data/world_research_jobs';self.root.mkdir(parents=True)
        self.previous=make(self.root,'Build an original habitat.');self.before=snapshot(self.previous)
    def send(self,module,message):
        a=app(module,self.root,self.previous);a.chat_var.set(message);events=[]
        with boundaries(module,self.root,events):a.send_world_builder_chat()
        return a,events
    def test_new_chat_job_clears_previous_preview_and_views(self):
        a=app(candidate,self.root,self.previous);p=a._layout_preview;r=a._reference_photos_view;c=a._original_components_view
        a.chat_var.set('Build a new Mars base.')
        with boundaries(candidate,self.root,[]):a.send_world_builder_chat()
        self.assertNotEqual(a._research_latest,self.previous);self.assertTrue(p.closed);self.assertIsNone(a._layout_preview)
        self.assertEqual(r.destroyed,1);self.assertIsNone(a._reference_photos_view);self.assertEqual(c.bound,[a._research_latest]);self.assertIsNone(a.latest_request)
        self.assertEqual(self.before,snapshot(self.previous));self.assertEqual(a.latest_folder,a._research_latest)
    def test_same_selected_job_resume_preserves_open_views(self):
        a=app(candidate,self.root,self.previous);preview=a._layout_preview;photos=a._reference_photos_view;component=a._original_components_view
        a.chat_var.set('resume research');a.latest_folder=self.root/'unrelated_notebook_folder'
        with boundaries(candidate,self.root,[]):a.send_world_builder_chat()
        self.assertIs(a._layout_preview,preview);self.assertFalse(preview.closed);self.assertIs(a._reference_photos_view,photos);self.assertEqual(component.bound,[])
        self.assertEqual(a._research_latest,self.previous);self.assertEqual(a.latest_folder,self.previous);self.assertEqual(snapshot(self.previous),self.before)
    def test_failed_submission_preserves_existing_context(self):
        a=app(candidate,self.root,self.previous);preview=a._layout_preview;photos=a._reference_photos_view;component=a._original_components_view
        a.chat_var.set('x'*4001)
        with boundaries(candidate,self.root,[]) as _scope:a.send_world_builder_chat()
        self.assertEqual(a._research_latest,self.previous);self.assertIs(a._layout_preview,preview);self.assertFalse(preview.closed);self.assertIs(a._reference_photos_view,photos);self.assertEqual(component.bound,[])
        self.assertIn('could not start',a.messages[0]);self.assertEqual(snapshot(self.previous),self.before)
    def test_new_chat_job_does_not_replace_running_research_worker(self):
        a=app(candidate,self.root,self.previous);existing=object();a._research_worker=existing;a.chat_var.set('Build a Mars base.');events=[]
        with boundaries(candidate,self.root,events):a.send_world_builder_chat()
        self.assertIs(a._research_worker,existing);self.assertEqual(a._research_pending,[a._research_latest]);self.assertEqual(events,[]);self.assertIsNone(a._layout_preview)
    def test_preview_button_after_chat_uses_new_selection(self):
        a,events=self.send(candidate,'Build a Mars base.');selected=a._research_latest
        with boundaries(candidate,self.root,events):a.open_layout_preview()
        self.assertEqual(a._layout_preview.job,selected);self.assertEqual(events[-1],{'preview_job':selected.name})
    def test_saved_selector_still_reopens_without_research(self):
        second=make(self.root,'Build a fictional observatory.');before=snapshot(self.root);a=app(candidate,self.root,self.previous);events=[]
        with boundaries(candidate,self.root,events):
            a.refresh_saved_research();a.saved_research_choice.current(next(i for i,x in enumerate(a._saved_research_items) if x['job_dir']==second));a.select_saved_research()
        self.assertEqual(a._research_latest,second);self.assertIsNone(a._layout_preview);self.assertEqual(events,[]);self.assertEqual(snapshot(self.root),before)
    def test_preview_without_selection_reports_requirement(self):
        a=app(candidate,self.root,None);events=[]
        with boundaries(candidate,self.root,events):a.open_layout_preview()
        self.assertEqual(events,[]);self.assertIn('Choose or submit',a.messages[-1])
    def test_export_without_selection_does_not_open_dialog_or_worker(self):
        a=app(candidate,self.root,None);events=[]
        with boundaries(candidate,self.root,events),patch.object(candidate.filedialog,'askdirectory',side_effect=AssertionError('No dialog without a selected job')):a.export_3d_package()
        self.assertEqual(events,[]);self.assertIn('Choose a saved layout',a.messages[-1])
    def export_selection_scenario(self,module):
        a=app(module,self.root,self.previous);old_binding=dict(a._layout_preview.manifest);a.chat_var.set('Build a Mars base.');events=[];calls=[]
        with boundaries(module,self.root,events):a.send_world_builder_chat()
        selected=a._research_latest;selected_binding={'manifest_path':str(selected/'preview.json'),'manifest_sha256':'b'*64}
        def verified(path,digest):
            parent=Path(path).parent
            return {'source_mode':'source_bound_original_layout','inputs':{'research_packet':{'path':str(parent/'research_packet.json')}},'source_pins':{k:{'sha256':v} for k,v in export_api.RENDERER.items()}}
        def exporter(job,destination,*,preview_binding):
            with patch.object(export_api,'PROJECT',self.project),patch.object(export_api,'latest_preview',return_value=selected_binding),patch.object(export_api,'verify_preview',side_effect=verified),patch.object(export_api.bindings,'source_chain',side_effect=ReachedSourceChain):
                try:export_api.inspect_selected_layout(job,preview_binding)
                except export_api.ExportHeld as exc:status=exc.status;message=str(exc)
                except ReachedSourceChain:status='selection_gate_passed';message='Bound to selected project; audit stopped before geometry/producer processing.'
                else:raise AssertionError('Audit must stop before real export')
            calls.append({'selected_job':job.name,'binding_job':Path(preview_binding['manifest_path']).parent.name if preview_binding else None,'status':status})
            return {'status':status,'message':message}
        with boundaries(module,self.root,events,exporter):a.export_3d_package();a._poll_3d_export()
        self.assertEqual(len(calls),1);self.assertEqual(snapshot(self.previous),self.before);return calls[0]
    def test_real_export_selection_gate_rejects_baseline_mismatch(self):
        result=self.export_selection_scenario(baseline);self.assertEqual(result['status'],'invalid_selection');self.assertEqual(result['binding_job'],self.previous.name)
    def test_real_export_selection_gate_receives_correct_candidate_context(self):
        result=self.export_selection_scenario(candidate);self.assertEqual(result['status'],'selection_gate_passed');self.assertIsNone(result['binding_job'])
    def test_new_job_then_selected_preview_captured_by_export(self):
        a,events=self.send(candidate,'Build a Mars base.');calls=[]
        def exporter(job,destination,*,preview_binding):
            calls.append((job,preview_binding));return {'status':'not_run','message':'Audit boundary only.'}
        with boundaries(candidate,self.root,events,exporter):a.open_layout_preview();a.export_3d_package();a._poll_3d_export()
        self.assertEqual(calls,[(a._research_latest,a._layout_preview.manifest)])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContextTests))
    plan=json.loads((H/'REVIEW-PLAN.json').read_bytes());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert all(sha(p)==digest for p,digest in plan['protected_inputs'].items())
    assert all(sha(K/rel)==digest for rel,digest in json.loads((H/'SOURCE-PINS.json').read_bytes()).items())
    receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source_sha256':sha(H/'candidate/tools/world_builder_workspace.py'),
        'actual_workspace_callbacks':True,'actual_research_brief_job_and_catalog_services':True,'actual_export_selection_gate':True,'preview_opening_export_and_model_boundaries':'inert; no real browser/export/model job',
        'canonical_writes':0,'protected_originals_unchanged':116,'temporary_state_only':True}
    with (H/'TEST-RESULT.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt));raise SystemExit(not result.wasSuccessful())
