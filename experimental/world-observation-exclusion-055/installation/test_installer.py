"""Temporary seven-file transactions and review/path guards; never touch Kira."""
from pathlib import Path
import copy,hashlib,importlib.util,json,tempfile,unittest,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('installer055',H/'install_exact.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='world055-installer-');self.addCleanup(self.tmp.cleanup)
  self.h=Path(self.tmp.name);self.root=self.h/'installed';self.work=self.h/'proposal';self.rows=[]
  for i,rel in enumerate(sorted(api.ALLOWED)):
   target=self.root/rel;after=self.work/'candidate'/rel;pre=self.work/'preimages'/rel
   for p in (target,after,pre):p.parent.mkdir(parents=True,exist_ok=True)
   target.write_text('before '+str(i));pre.write_bytes(target.read_bytes());after.write_text('after '+str(i))
   self.rows.append({'relative_path':rel,'target':str(target),'before_sha256':sha(target),'preimage':str(pre),'after':{'path':str(after),'sha256':sha(after)}})
  original=self.root/'Data/source.json';original.parent.mkdir();original.write_text('unchanged original')
  self.plan={'files':self.rows,'protected_inputs':{str(original):sha(original)}}
  self.contract={k:'a'*64 for k in ('install_plan_sha256','source_diff_sha256','candidate_backend_sha256','preview_manifest_sha256')}
  self.review={**self.contract,'status':'ROOT_APPROVED_055_INSTALL','source_review_complete':True,'gpu014_closed_and_cleanup_confirmed':True,'native_preview_review_complete':True,'review_notes':'Synthetic approval fixture only'}
 def assert_before(self):
  for r in self.rows:self.assertEqual(sha(Path(r['target'])),r['before_sha256'])
 def test_success_and_explicit_rollback(self):
  self.assertEqual(api.apply(self.plan,self.root,self.work)['installed_files'],7)
  self.assertEqual(api.rollback(self.plan,self.root,self.work)['restored_files'],7);self.assert_before()
 def test_changed_candidate_and_wrong_target_reject_before_writes(self):
  path=Path(self.rows[2]['after']['path']);raw=path.read_bytes();path.write_text('tampered')
  with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
  self.assert_before();path.write_bytes(raw);self.rows[2]['target']=str(self.root/'outside-scope.txt')
  with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
 def test_failure_before_and_after_atomic_replace_restores_exact_before(self):
  for after_write in (False,True):
   with self.subTest(after_write=after_write):
    calls=[]
    def fail_third(path,raw):
     calls.append(path)
     if len(calls)==3 and not after_write:raise OSError('injected before replace')
     api.atomic(path,raw)
     if len(calls)==3:raise OSError('injected after replace')
    result=api.apply(self.plan,self.root,self.work,replace=fail_third)
    self.assertIn('FAILED',result['status']);self.assert_before()
 def test_concurrent_edit_is_never_rolled_back(self):
  calls=[]
  def changed(path,raw):
   calls.append(path)
   if len(calls)==3:
    Path(self.rows[0]['target']).write_text('concurrent owner update');raise OSError('injected')
   api.atomic(path,raw)
  result=api.apply(self.plan,self.root,self.work,replace=changed)
  self.assertEqual(Path(self.rows[0]['target']).read_text(),'concurrent owner update')
  self.assertIn('held_concurrent_change',[r['status'] for r in result['rollback']])
 def test_protected_input_edit_blocks_install(self):
  Path(next(iter(self.plan['protected_inputs']))).write_text('new original')
  with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
  self.assert_before()
 def test_manual_rollback_preserves_later_updates(self):
  api.apply(self.plan,self.root,self.work);Path(self.rows[3]['target']).write_text('later update')
  before=[Path(r['target']).read_bytes() for r in self.rows]
  with self.assertRaises(AssertionError):api.rollback(self.plan,self.root,self.work)
  self.assertEqual(before,[Path(r['target']).read_bytes() for r in self.rows])
 def save_review(self):
  path=self.h/'review.json';path.write_text(json.dumps(self.review));return path
 def test_exact_review_is_accepted_only_for_its_operation(self):
  p=self.save_review();self.assertEqual(api.review_binding(p,sha(p),'apply',self.contract)['status'],'ROOT_APPROVED_055_INSTALL')
  with self.assertRaises(AssertionError):api.review_binding(p,sha(p),'rollback',self.contract)
 def test_stale_review_digest_or_different_plan_is_rejected(self):
  p=self.save_review()
  with self.assertRaises(AssertionError):api.review_binding(p,'0'*64,'apply',self.contract)
  self.review['install_plan_sha256']='b'*64;p=self.save_review()
  with self.assertRaises(AssertionError):api.review_binding(p,sha(p),'apply',self.contract)
 def test_review_pending_or_gpu_active_cannot_authorize_install(self):
  for field in ('source_review_complete','gpu014_closed_and_cleanup_confirmed','native_preview_review_complete'):
   with self.subTest(field=field):
    self.review[field]=False;p=self.save_review()
    with self.assertRaises(AssertionError):api.review_binding(p,sha(p),'apply',self.contract)
    self.review[field]=True
 def source_manifest(self):
  job=self.root/'Data/world_research_jobs/world_research_test'
  return {'inputs':{role:{'path':str(job/relative)} for role,relative in [('research_packet','research_packet.json'),('geometry_source','pipeline/r2/compiled_geometry.json'),('blueprint','pipeline/r2/blueprint.json')]}}
 def test_selected_job_is_retained(self):
  value=api.selected_source_paths(self.source_manifest(),self.root,'world_research_test')
  self.assertEqual(value,self.root/'Data/world_research_jobs/world_research_test')
 def test_other_job_or_escape_in_each_bound_source_rejected(self):
  for role in ('research_packet','geometry_source','blueprint'):
   with self.subTest(role=role):
    m=self.source_manifest();m['inputs'][role]['path']=str(self.root/'Data/world_research_jobs/world_research_other/unrelated.json')
    with self.assertRaises(AssertionError):api.selected_source_paths(m,self.root,'world_research_test')
  with self.assertRaises(AssertionError):api.selected_source_paths(self.source_manifest(),self.root,'../../outside')
 def test_review_manifest_path_cannot_escape_isolated_preview_root(self):
  folder=self.work/'installation';folder.mkdir();(folder/'REVIEW-BINDING.json').write_text(json.dumps({'preview_manifest_path':str(self.h/'outside/manifest.json')}))
  with self.assertRaises(AssertionError):api.verify_presentation_path(self.root,self.work)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InstallerTests))
 value={'status':'055_INSTALLER_TEMP_FIXTURES_PASS' if result.wasSuccessful() else 'FAIL','test_methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'canonical_or_owner_writes':0,'real_installation':False}
 with (H/'INSTALLER-TEST-RESULT.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
 print(json.dumps(value));raise SystemExit(not result.wasSuccessful())
