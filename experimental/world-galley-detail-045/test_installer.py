"""Temporary fixtures only: installed engine and owner inputs are never touched."""
from pathlib import Path
import hashlib,importlib.util,json,tempfile,unittest

H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('installer045',H/'install_exact.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='world045-installer-');self.addCleanup(self.tmp.cleanup)
        self.h=Path(self.tmp.name);self.root=self.h/'installed';self.work=self.h/'candidate_work';self.rows=[]
        for i,rel in enumerate(sorted(api.ALLOWED)):
            target=self.root/rel;after=self.work/'candidate'/rel;pre=self.work/'preimages'/rel
            for p in (target,after,pre):p.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('before '+str(i));pre.write_bytes(target.read_bytes());after.write_text('after '+str(i))
            self.rows.append({'relative_path':rel,'target':str(target),'before_sha256':sha(target),'preimage':str(pre),'after':{'path':str(after),'sha256':sha(after)}})
        self.original=self.root/'Data/source.json';self.original.parent.mkdir();self.original.write_text('owner original')
        self.plan={'files':self.rows,'protected_inputs':{str(self.original):sha(self.original)}}
    def assert_before(self):
        for r in self.rows:self.assertEqual(sha(Path(r['target'])),r['before_sha256'])
    def test_success_and_explicit_rollback(self):
        result=api.apply(self.plan,self.root,self.work);self.assertEqual(result['status'],'045_EXACT_FIVE_FILE_INSTALL_PASS')
        result=api.rollback(self.plan,self.root,self.work);self.assertEqual(result['restored_files'],5);self.assert_before()
    def test_source_tampering_rejects_before_any_mutation(self):
        Path(self.rows[2]['after']['path']).write_text('unexpected')
        with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
        self.assert_before()
    def test_target_tampering_rejects_before_any_mutation(self):
        Path(self.rows[2]['target']).write_text('owner edit');before=[Path(r['target']).read_bytes() for r in self.rows]
        with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
        self.assertEqual(before,[Path(r['target']).read_bytes() for r in self.rows])
    def test_partial_write_failure_restores_completed_files(self):
        calls=[]
        def fail_third(path,raw):
            calls.append(path)
            if len(calls)==3:raise OSError('injected atomic replacement failure')
            api.atomic(path,raw)
        result=api.apply(self.plan,self.root,self.work,replace=fail_third)
        self.assertIn('FAILED',result['status']);self.assertEqual([r['status'] for r in result['rollback']],['restored','restored']);self.assert_before()
    def test_concurrent_change_is_preserved_on_failure(self):
        calls=[]
        def change_during_third(path,raw):
            calls.append(path)
            if len(calls)==3:
                Path(self.rows[0]['target']).write_text('concurrent owner update');raise OSError('injected')
            api.atomic(path,raw)
        result=api.apply(self.plan,self.root,self.work,replace=change_during_third)
        self.assertEqual(Path(self.rows[0]['target']).read_text(),'concurrent owner update')
        self.assertIn('held_concurrent_change',[r['status'] for r in result['rollback']])
    def test_exact_path_scope_rejects_tampered_target(self):
        self.rows[0]['target']=str(self.root/'different.txt')
        with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
    def test_protected_input_change_blocks_install(self):
        self.original.write_text('new owner input')
        with self.assertRaises(AssertionError):api.apply(self.plan,self.root,self.work)
        self.assert_before()
    def test_manual_rollback_refuses_changed_installed_file(self):
        api.apply(self.plan,self.root,self.work);Path(self.rows[3]['target']).write_text('later update')
        before=[Path(r['target']).read_bytes() for r in self.rows]
        with self.assertRaises(AssertionError):api.rollback(self.plan,self.root,self.work)
        self.assertEqual(before,[Path(r['target']).read_bytes() for r in self.rows])
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InstallerTests))
    receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'canonical_and_owner_writes':0,'temporary_fixture_only':True}
    with (H/('INSTALLER-TEST-PUBLIC-'+str(len(list(H.glob('INSTALLER-TEST*.json'))))+'.json')).open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt));raise SystemExit(not result.wasSuccessful())
