"""Run retained046 transition tests against047, without duplicating their source."""
from pathlib import Path
import hashlib,importlib.util,json,unittest
import harness
H=Path(__file__).resolve().parent;previous=H.parent/'world-chat-usability-audit-046/test_context.py'
spec=importlib.util.spec_from_file_location('retained046',previous);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
excluded={
    'test_real_export_selection_gate_rejects_baseline_mismatch':'The047 baseline is already-installed046, where this historical mismatch is fixed.',
    'test_failed_submission_preserves_existing_context':'Bare unrecognized text no longer submits research; explicit invalid creation is checked separately below.',
}
names=[n for n in unittest.defaultTestLoader.getTestCaseNames(m.ContextTests) if n not in excluded]
class Extra(m.ContextTests):
    def test_invalid_direct_creation_preserves_selected_context(self):
        a=harness.app(m.candidate,self.root,self.previous);preview=a._layout_preview;photos=a._reference_photos_view;a.chat_var.set('Build '+'x'*4001);events=[]
        with harness.boundaries(m.candidate,self.root,events):a.send_world_builder_chat()
        self.assertEqual(a._research_latest,self.previous);self.assertIs(a._layout_preview,preview);self.assertIs(a._reference_photos_view,photos)
        self.assertEqual(events,[]);self.assertIn('could not start',a.messages[0]);self.assertEqual(harness.snapshot(self.previous),self.before)
suite=unittest.TestSuite([m.ContextTests(n) for n in names]+[Extra('test_invalid_direct_creation_preserves_selected_context')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'prior_source_sha256':hashlib.sha256(previous.read_bytes()).hexdigest(),'retained_tests':names,'excluded_historical_cases':excluded,'additional_test':'explicit invalid creation preserves selection and source','model_ui_gpu_owner_writes':0}
with (H/'RETAINED-CONTEXT-RESULT.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
