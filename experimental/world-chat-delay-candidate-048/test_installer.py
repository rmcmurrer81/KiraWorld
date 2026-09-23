from pathlib import Path
import hashlib,json,tempfile,unittest
import install_exact as installer
H=Path(__file__).resolve().parent
class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='world048-install-',dir=H);self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name);self.root=self.home/'kira';self.work=self.home/'candidate048'
        self.plan={'files':[],'protected_inputs':{}}
        for index,relative in enumerate(installer.ORDER):
            target=self.root/relative;after=self.work/'candidate'/relative
            target.parent.mkdir(parents=True,exist_ok=True);after.parent.mkdir(parents=True,exist_ok=True);after.write_text(f'VALUE={index+10}\n')
            pre=None;before=None
            if index:
                target.write_text('VALUE=1\n');pre=self.work/'baseline/world_builder_workspace.py';pre.parent.mkdir();pre.write_bytes(target.read_bytes());before=installer.sha(pre)
            self.plan['files'].append({'relative_path':relative,'target':str(target),'preimage':str(pre) if pre else None,'before_sha256':before,'after':{'path':str(after),'sha256':installer.sha(after)}})
        original=self.home/'original.txt';original.write_text('owner source');self.plan['protected_inputs'][str(original)]=installer.sha(original)
    def test_install_and_rollback_new_helper_and_existing_workspace(self):
        self.assertEqual(installer.apply(self.plan,self.root,self.work)['status'],'048_EXACT_TWO_FILE_INSTALL_PASS')
        installer.validate(self.plan,self.root,self.work,'after')
        self.assertEqual(installer.rollback(self.plan,self.root,self.work)['status'],'048_EXACT_TWO_FILE_ROLLBACK_PASS')
        self.assertFalse(Path(self.plan['files'][0]['target']).exists())
    def test_existing_new_helper_not_overwritten(self):
        target=Path(self.plan['files'][0]['target']);target.write_text('UNRELATED=1')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
        self.assertEqual(target.read_text(),'UNRELATED=1')
    def test_changed_candidate_rejected(self):
        Path(self.plan['files'][0]['after']['path']).write_text('TAMPER=1')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_changed_preimage_rejected(self):
        Path(self.plan['files'][1]['preimage']).write_text('TAMPER=1')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_changed_protected_input_rejected(self):
        Path(next(iter(self.plan['protected_inputs']))).write_text('changed source')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
    def test_outside_target_rejected(self):
        self.plan['files'][0]['target']=str(self.home/'outside.py')
        with self.assertRaises(AssertionError):installer.apply(self.plan,self.root,self.work)
        self.assertFalse((self.home/'outside.py').exists())
    def test_failure_before_second_write_removes_new_helper(self):
        def fail(path,raw):
            if path.name=='world_builder_workspace.py':raise OSError('injected failure')
            installer.atomic(path,raw)
        self.assertIn('FAILED',installer.apply(self.plan,self.root,self.work,fail)['status'])
        installer.validate(self.plan,self.root,self.work)
    def test_failure_after_second_write_restores_both(self):
        def fail(path,raw):
            installer.atomic(path,raw)
            if path.name=='world_builder_workspace.py':raise OSError('injected postwrite failure')
        self.assertIn('FAILED',installer.apply(self.plan,self.root,self.work,fail)['status'])
        installer.validate(self.plan,self.root,self.work)
    def test_concurrent_change_during_failure_is_preserved(self):
        def fail(path,raw):
            installer.atomic(path,raw)
            if path.name=='world_builder_workspace.py':
                path.write_text('OTHER_UPDATE=1');raise OSError('injected concurrent update')
        result=installer.apply(self.plan,self.root,self.work,fail)
        self.assertEqual(result['rollback'][0]['status'],'rollback_held')
        self.assertEqual(Path(self.plan['files'][1]['target']).read_text(),'OTHER_UPDATE=1')
        self.assertEqual(result['rollback'][1]['status'],'retained_dependency_for_held_workspace')
        self.assertTrue(Path(self.plan['files'][0]['target']).exists())
    def test_rollback_preflight_prevents_partial_restore(self):
        installer.apply(self.plan,self.root,self.work);target=Path(self.plan['files'][1]['target']);target.write_text('OTHER_UPDATE=1')
        with self.assertRaises(AssertionError):installer.rollback(self.plan,self.root,self.work)
        self.assertTrue(Path(self.plan['files'][0]['target']).exists())
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InstallationTests))
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'temporary_fixture_only':True,'canonical_writes':0}
    with (H/'INSTALLER-TEST-RESULT.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
