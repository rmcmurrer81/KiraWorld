from pathlib import Path
import json,tempfile,unittest
import install_exact as installer
H=Path(__file__).resolve().parent
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='world049-install-',dir=H);self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name);self.root=base/'kira';self.work=base/'candidate049'
        target=self.root/installer.RELATIVE;after=self.work/'candidate'/installer.RELATIVE;pre=self.work/'baseline/world_research.py'
        for path,text in [(target,'VALUE=1\n'),(pre,'VALUE=1\n'),(after,'VALUE=2\n')]:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        original=base/'original.txt';original.write_text('owner source')
        self.row={'relative_path':installer.RELATIVE,'target':str(target),'preimage':str(pre),'before_sha256':installer.sha(pre),'after':{'path':str(after),'sha256':installer.sha(after)}}
        self.plan={'files':[self.row],'protected_inputs':{str(original):installer.sha(original)}}
    def test_install_and_rollback(self):
        self.assertEqual(installer.apply(self.plan,self.root,self.work)['status'],'049_EXACT_ONE_FILE_INSTALL_PASS')
        self.assertEqual(installer.rollback(self.plan,self.root,self.work)['status'],'049_EXACT_ONE_FILE_ROLLBACK_PASS')
    def test_changed_candidate_rejected(self):
        Path(self.row['after']['path']).write_text('VALUE=9\n')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_changed_preimage_rejected(self):
        Path(self.row['preimage']).write_text('VALUE=9\n')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_changed_installed_source_rejected(self):
        Path(self.row['target']).write_text('VALUE=9\n')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_changed_original_rejected(self):
        Path(next(iter(self.plan['protected_inputs']))).write_text('changed')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_target_escape_rejected(self):
        outside=self.root.parent/'outside.py';self.row['target']=str(outside)
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
        self.assertFalse(outside.exists())
    def test_failure_before_write_preserves_preimage(self):
        def fail(path,raw):raise OSError('injected before-write failure')
        result=installer.apply(self.plan,self.root,self.work,fail);self.assertEqual(result['rollback']['status'],'already_before');installer.validate(self.plan,self.root,self.work)
    def test_failure_after_write_restores_preimage(self):
        def fail(path,raw):installer.atomic(path,raw);raise OSError('injected after-write failure')
        result=installer.apply(self.plan,self.root,self.work,fail);self.assertEqual(result['rollback']['status'],'restored');installer.validate(self.plan,self.root,self.work)
    def test_concurrent_change_during_failure_is_preserved(self):
        def fail(path,raw):installer.atomic(path,raw);path.write_text('OTHER=1');raise OSError('injected concurrent change')
        result=installer.apply(self.plan,self.root,self.work,fail);self.assertEqual(result['rollback']['status'],'held_for_review');self.assertEqual(Path(self.row['target']).read_text(),'OTHER=1')
    def test_rollback_refuses_concurrent_update(self):
        installer.apply(self.plan,self.root,self.work);Path(self.row['target']).write_text('OTHER=1')
        with self.assertRaises(AssertionError):installer.rollback(self.plan,self.root,self.work)
        self.assertEqual(Path(self.row['target']).read_text(),'OTHER=1')
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryTests))
    receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'temporary_fixtures_only':True,'canonical_writes':0}
    with (H/'INSTALLER-TEST-RESULT.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt));raise SystemExit(not result.wasSuccessful())
