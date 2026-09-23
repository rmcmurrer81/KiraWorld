from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

H=Path(__file__).resolve().parent
K=Path('@user_home/Kira')
sys.path.insert(0,str(K/'tools'))
sys.path.insert(0,str(H/'candidate/tools'))
import world_saved_research as saved

spec=importlib.util.spec_from_file_location('candidate023_workspace',H/'candidate/tools/world_builder_workspace.py')
workspace=importlib.util.module_from_spec(spec);spec.loader.exec_module(workspace)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def payload(subject='A small original observatory'):
    brief={'subject':subject,'prompt':'Build an original observatory','research_mode':'original_world'}
    raw=(json.dumps(brief,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    digest=hashlib.sha256(raw).hexdigest()
    return {'schema_version':1,'job_kind':'isolated_world_research_job','job_id':'world_research_'+digest[:20],
            'brief':brief,'brief_sha256':digest,'stage':'geometry_ready'}

def make(root,subject='A small original observatory'):
    data=payload(subject);folder=root/data['job_id'];folder.mkdir(parents=True)
    (folder/'job.json').write_text(json.dumps(data),encoding='utf-8');return folder

class Choice:
    def __init__(self):self.index=-1;self.text='';self.values=[]
    def configure(self,**kw):self.values=kw['values']
    def current(self,index=None):
        if index is not None:self.index=index
        return self.index
    def set(self,text):self.text=text;self.index=-1

class ChildView:
    def __init__(self,exists=True):self.exists=exists;self.destroyed=0;self.bound_jobs=[]
    def winfo_exists(self):return self.exists
    def destroy(self):self.destroyed+=1;self.exists=False
    def set_world_job(self,job):self.bound_jobs.append(job)

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='world023-',dir=H)
        self.root=Path(self.temp.name)/'world_research_jobs';self.root.mkdir()
    def tearDown(self):self.temp.cleanup()
    def app(self):
        a=object.__new__(workspace.WorldBuilderWorkspace)
        a._research_latest=None;a._saved_research_items=[];a.latest_folder=None;a.latest_request=None
        a._layout_preview='previous-preview';a.saved_research_choice=Choice();a.messages=[];a.log=a.messages.append
        a._reference_photos_view=None;a._original_components_view=None
        return a
    def test_empty_missing_root_does_not_create_folder(self):
        missing=self.root/'absent';self.assertEqual(saved.list_saved_research(missing),[]);self.assertFalse(missing.exists())
    def test_valid_metadata_does_not_change_any_bytes(self):
        folder=make(self.root);before=(folder/'job.json').read_bytes()
        result=saved.list_saved_research(self.root)
        self.assertEqual(len(result),1);self.assertTrue(result[0]['available']);self.assertEqual(result[0]['job_dir'],folder)
        self.assertEqual((folder/'job.json').read_bytes(),before)
    def test_corrupt_job_is_visible_and_preserved(self):
        folder=make(self.root);(folder/'job.json').write_text('{broken',encoding='utf-8')
        items=saved.list_saved_research(self.root);self.assertEqual(len(items),1);self.assertFalse(items[0]['available'])
        self.assertEqual((folder/'job.json').read_text(),'{broken')
    def test_identity_mismatch_is_not_selected(self):
        folder=make(self.root);data=json.loads((folder/'job.json').read_text());data['job_id']='another job'
        (folder/'job.json').write_text(json.dumps(data));self.assertFalse(saved.list_saved_research(self.root)[0]['available'])
    def test_changed_brief_is_not_selected(self):
        folder=make(self.root);data=json.loads((folder/'job.json').read_text());data['brief']['subject']='Changed silently'
        (folder/'job.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'no longer matches'):saved.read_saved_research(folder,job_root=self.root)
    def test_foreign_root_is_rejected(self):
        outside=Path(self.temp.name)/'other';folder=make(outside)
        with self.assertRaises(ValueError):saved.read_saved_research(folder,job_root=self.root)
    def test_oversized_metadata_is_held(self):
        folder=make(self.root);(folder/'job.json').write_bytes(b'x'*(saved.MAX_JOB_BYTES+1))
        with self.assertRaisesRegex(ValueError,'size'):saved.read_saved_research(folder,job_root=self.root)
    def test_directory_link_is_rejected(self):
        outside=Path(self.temp.name)/'outside';target=make(outside);link=self.root/target.name
        try:link.symlink_to(target,target_is_directory=True)
        except OSError as exc:self.skipTest('Windows did not allow a disposable symlink: '+str(exc))
        self.assertFalse(saved.list_saved_research(self.root)[0]['available'])
    def test_metadata_link_is_rejected(self):
        folder=make(self.root);source=folder/'job.json';external=Path(self.temp.name)/'external.json';source.replace(external)
        try:source.symlink_to(external)
        except OSError as exc:self.skipTest('Windows did not allow a disposable symlink: '+str(exc))
        with self.assertRaisesRegex(ValueError,'linked'):saved.read_saved_research(folder,job_root=self.root)
    def test_selection_reopens_context_without_running_research_or_models(self):
        folder=make(self.root);a=self.app()
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview') as close,patch.object(workspace,'run_job',side_effect=AssertionError('Research must not run')),patch.object(workspace,'submit_research_prompt',side_effect=AssertionError('No submission')),patch.object(workspace,'run_pipeline_after_research',side_effect=AssertionError('No model')):
            a.refresh_saved_research();a.saved_research_choice.current(0);a.select_saved_research()
        self.assertEqual(a._research_latest,folder);self.assertEqual(a.latest_folder,folder);self.assertIsNone(a.latest_request)
        self.assertIsNone(a._layout_preview);close.assert_called_once_with('previous-preview')
        self.assertIn('No research or generation was started.',a.messages[-1])
    def test_selected_layout_preview_uses_exact_saved_job(self):
        folder=make(self.root);a=self.app()
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview'),patch.object(workspace,'open_preview',return_value='new-preview') as preview:
            a.refresh_saved_research();a.saved_research_choice.current(0);a.select_saved_research();a.open_layout_preview()
        preview.assert_called_once_with(folder,None);self.assertEqual(a._layout_preview,'new-preview')
    def test_selection_reads_current_stage_after_background_completion(self):
        folder=make(self.root);a=self.app()
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview'):
            a.refresh_saved_research();data=json.loads((folder/'job.json').read_text());data['stage']='text_research_ready_visual_review_pending'
            (folder/'job.json').write_text(json.dumps(data));a.saved_research_choice.current(0);a.select_saved_research()
        self.assertIn('text_research_ready_visual_review_pending',a.messages[0])
    def test_invalid_selection_clears_previous_context(self):
        folder=make(self.root);a=self.app();a._research_latest=folder;a.latest_folder=folder
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview') as close:
            a.refresh_saved_research();(folder/'job.json').write_text('{}');a.saved_research_choice.current(0);a.select_saved_research()
        self.assertIsNone(a._research_latest);self.assertIsNone(a.latest_folder);self.assertIsNone(a._layout_preview);close.assert_called_once()
    def test_refresh_preserves_selected_job_without_reopening_or_generation(self):
        chosen=make(self.root,'Older study');make(self.root,'Newer study');a=self.app();a._research_latest=chosen
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview',side_effect=AssertionError('Refresh is read only')):
            a.refresh_saved_research()
        index=a.saved_research_choice.current();self.assertGreaterEqual(index,0);self.assertEqual(a._saved_research_items[index]['job_dir'],chosen)
    def test_unselected_callback_is_noop(self):
        a=self.app();a.select_saved_research();self.assertEqual(a.messages,[])
    def test_missing_job_after_catalog_clears_previous_context(self):
        folder=make(self.root);a=self.app();a._research_latest=folder
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview'):
            a.refresh_saved_research();(folder/'job.json').unlink();folder.rmdir()
            a.saved_research_choice.current(0);a.select_saved_research()
        self.assertIsNone(a._research_latest);self.assertIsNone(a._layout_preview)
        self.assertIn('could not be opened',a.messages[-1])
    def test_duplicate_subjects_keep_distinct_selection_and_preview_targets(self):
        first=make(self.root,'Same owner title')
        data=payload('Same owner title');data['brief']['prompt']='A different request with the same title'
        raw=(json.dumps(data['brief'],ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
        data['brief_sha256']=hashlib.sha256(raw).hexdigest();data['job_id']='world_research_'+data['brief_sha256'][:20]
        second=self.root/data['job_id'];second.mkdir();(second/'job.json').write_text(json.dumps(data))
        a=self.app()
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview'),patch.object(workspace,'open_preview',return_value='opened') as preview:
            a.refresh_saved_research();self.assertEqual(len(set(a.saved_research_choice.values)),2)
            for folder in [second,first]:
                index=next(i for i,item in enumerate(a._saved_research_items) if item['job_dir']==folder)
                a.saved_research_choice.current(index);a.select_saved_research();a.open_layout_preview()
                self.assertEqual(preview.call_args.args[0],folder)
    def test_real_combobox_is_wired_to_selection_callback(self):
        text=(H/'candidate/tools/world_builder_workspace.py').read_text();tree=ast.parse(text)
        bindings=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='bind' and ast.unparse(node.func.value)=='self.saved_research_choice']
        self.assertEqual(len(bindings),1);self.assertEqual(ast.literal_eval(bindings[0].args[0]),'<<ComboboxSelected>>')
        self.assertEqual(ast.unparse(bindings[0].args[1]),'self.select_saved_research')
    def test_valid_selection_closes_previous_photos_and_rebinds_open_components(self):
        folder=make(self.root);a=self.app();photos=ChildView();components=ChildView()
        a._reference_photos_view=photos;a._original_components_view=components
        before=(folder/'job.json').read_bytes()
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview') as close,patch.object(workspace,'run_job',side_effect=AssertionError('No research')),patch.object(workspace,'run_pipeline_after_research',side_effect=AssertionError('No model')):
            a.refresh_saved_research();a.saved_research_choice.current(0);a.select_saved_research()
        self.assertEqual(photos.destroyed,1);self.assertIsNone(a._reference_photos_view)
        self.assertEqual(components.bound_jobs,[folder]);self.assertIs(a._original_components_view,components)
        self.assertEqual((folder/'job.json').read_bytes(),before);close.assert_called_once_with('previous-preview')
    def test_failed_selection_closes_previous_photos_and_unbinds_components(self):
        folder=make(self.root);a=self.app();photos=ChildView();components=ChildView()
        a._reference_photos_view=photos;a._original_components_view=components
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview'),patch.object(workspace,'submit_research_prompt',side_effect=AssertionError('No submission')):
            a.refresh_saved_research();(folder/'job.json').write_text('{damaged')
            a.saved_research_choice.current(0);a.select_saved_research()
        self.assertEqual(photos.destroyed,1);self.assertIsNone(a._reference_photos_view)
        self.assertEqual(components.bound_jobs,[None]);self.assertIsNone(a._research_latest)
        self.assertEqual((folder/'job.json').read_text(),'{damaged')
    def test_already_closed_children_are_not_called_again(self):
        a=self.app();photos=ChildView(False);components=ChildView(False)
        a._reference_photos_view=photos;a._original_components_view=components
        with patch.object(workspace,'close_preview'):a.set_saved_research_context(None)
        self.assertEqual(photos.destroyed,0);self.assertEqual(components.bound_jobs,[])
        self.assertIsNone(a._reference_photos_view)
    def test_switching_selected_job_updates_component_binding_each_time(self):
        first=make(self.root,'First study');second=make(self.root,'Second study');a=self.app();components=ChildView();a._original_components_view=components
        with patch.object(workspace,'DEFAULT_JOB_ROOT',self.root),patch.object(workspace,'close_preview'):
            a.refresh_saved_research()
            for folder in [first,second]:
                a.saved_research_choice.current(next(i for i,item in enumerate(a._saved_research_items) if item['job_dir']==folder))
                a.select_saved_research()
        self.assertEqual(components.bound_jobs,[first,second]);self.assertEqual(a.latest_folder,second)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':[str(e) for e in result.failures], 'errors':[str(e) for e in result.errors],'skipped':[(str(t),reason) for t,reason in result.skipped],'actual_candidate_callback_execution':True,'real_tk_window_opened':False,'browser_or_model_calls':0,'owner_data_written':False,'installed':False}
    with (H/'TEST-RESULT.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
