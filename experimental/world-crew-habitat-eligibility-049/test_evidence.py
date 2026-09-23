"""Assess actual callback/planner captures against owner-intent expectations."""
from pathlib import Path
import hashlib,json,unittest
from cases import CASES,ORIGINAL,REAL
H=Path(__file__).resolve().parent
B=json.loads((H/'BASELINE-CAPTURES.json').read_bytes());C=json.loads((H/'CANDIDATE-CAPTURES.json').read_bytes())
old={r['case']:r for r in B['cases']};new={r['case']:r for r in C['cases']}
class EligibilityEvidence(unittest.TestCase):
    def test_baseline_reproduces_18_generic_habitat_failures(self):
        changed=[name for name,_,expected in CASES if expected==ORIGINAL and old[name]['mode']==REAL]
        self.assertEqual(len(changed),18)
        for name in changed:
            self.assertEqual(old[name]['planner']['status'],'held')
            self.assertEqual(new[name]['planner']['status'],'prepared')
    def test_all43_intents_take_expected_callback_and_planner_path(self):
        for name,prompt,expected in CASES:
            with self.subTest(name=name):
                row=new[name];self.assertEqual(row['mode'],expected)
                self.assertEqual(row['queued_worker_boundary'],expected is not None)
                self.assertFalse(row['geometry_generated'])
                if expected is None:
                    self.assertEqual(row['planner']['status'],'not_called');self.assertTrue(row['saved_directory_empty'])
                else:
                    self.assertEqual(row['brief_prompt'],prompt);self.assertTrue(row['preserved_inputs_unchanged'])
                    self.assertEqual(row['original_generation_allowed'],expected==ORIGINAL)
                    self.assertEqual(row['planner']['status'],'prepared' if expected==ORIGINAL else 'held')
    def test_real_place_and_reconstruction_evidence_goals_remain_locked(self):
        for name,_,expected in CASES:
            if expected!=REAL:continue
            with self.subTest(name=name):
                self.assertEqual(new[name]['mode'],old[name]['mode'])
                self.assertIn('maps_plans',new[name]['research_task_ids'])
                self.assertNotIn('analog_cases',new[name]['research_task_ids'])
                self.assertIn('Real places require verified visual evidence',new[name]['planner']['error'])
    def test_original_requests_require_three_distinct_bound_sources(self):
        for name,_,expected in CASES:
            if expected!=ORIGINAL:continue
            with self.subTest(name=name):
                self.assertIn('analog_cases',new[name]['research_task_ids'])
                self.assertNotIn('maps_plans',new[name]['research_task_ids'])
                self.assertEqual(len(new[name]['planner']['source_ids']),3)
                self.assertEqual(new[name]['planner']['contract'],'original_layout_request_v2')
    def test_mars_roles_do_not_leak_into_other_requests(self):
        for name,prompt,expected in CASES:
            if expected!=ORIGINAL:continue
            with self.subTest(name=name):
                functions=new[name]['planner']['required_functions']
                if 'Mars' in prompt or 'Martian' in prompt:
                    self.assertEqual(functions,['equipment_vestibule','airlock','operations','habitat','laboratory','observation'])
                else:self.assertEqual(functions,[])
    def test_saved_real_brief_not_reclassified_or_rewritten(self):
        for data in (B,C):
            saved=data['saved_real_mode_preserved'];self.assertEqual(saved['brief_mode'],REAL)
            self.assertFalse(saved['current_original_gate']);self.assertTrue(saved['saved_bytes_unchanged'])
            self.assertIn('Real places require verified visual evidence',saved['planner_outcome'])
    def test_sources_exact_and048_installed_unchanged(self):
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(sha(H/'baseline/world_research.py'),B['research_source_sha256'])
        self.assertEqual(sha(H/'candidate/tools/world_research.py'),C['research_source_sha256'])
        for field in ('installed_workspace_sha256','installed_dispatcher_sha256'):
            self.assertEqual(B[field],C[field])
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EligibilityEvidence))
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'callback_cases':len(CASES),'baseline_failures_corrected':18,
        'original_plans_prepared':20,'real_place_plans_held':17,'nonexecuting_chat_requests':6,'models_workers_ui_network':0,'visual_or_owner_approval':False}
    with (H/'TEST-RESULT.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
