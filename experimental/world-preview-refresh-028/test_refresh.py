"""Disposable synthetic source integration and actual native callback tests."""
from pathlib import Path
import ast,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,types,unittest
from unittest.mock import patch,Mock
H=Path(__file__).resolve().parent;W=H.parent.parent;K=H/'support';ENGINE=K/'tools/world_builder_engine'
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
from world_builder_engine import pipeline
def load(source,name,location=None):
 m=types.ModuleType(name);m.__file__=str(location or source);m.__package__='world_builder_engine' if '.' in name else ''
 exec(compile(source.read_bytes(),str(source),'exec'),m.__dict__);return m
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
helper=H/'candidate/tools/world_builder_engine/preview_refresh.py'
class RefreshTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='world028-',dir=Path(tempfile.gettempdir()).resolve());self.root=Path(self.temp.name).resolve()
  self.engine=self.root/'tools/world_builder_engine';self.engine.mkdir(parents=True)
  for n in ('horizontal_navigation.mjs','preflight.mjs'):(self.engine/n).write_bytes((ENGINE/n).read_bytes())
  for n in ('viewer.mjs','walk_controller.mjs','index.html','style.css','world_layout_preview.py'):
   (self.engine/n).write_bytes((H.parent/'world-habitat-combined-027/preimages'/n).read_bytes())
  self.old=load(self.engine/'world_layout_preview.py','old028');self.old.THREE_BUILD=K/'third_party/three/build';self.old.NODE=Path(os.environ.get('WORLD_PREVIEW_NODE') or shutil.which('node') or 'node').resolve()
  brief={'subject':'Synthetic original habitat'};digest=hashlib.sha256((json.dumps(brief,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
  self.job=self.root/'Data/world_research_jobs'/('world_research_'+digest[:20]);self.job.mkdir(parents=True)
  (self.job/'job.json').write_text(json.dumps({'schema_version':1,'job_kind':'isolated_world_research_job','job_id':self.job.name,'brief':brief,'brief_sha256':digest,'stage':'research_complete'}))
  self.cache=self.job/'source.txt';self.cache.write_text('Authored test data; no owner research.')
  cache={**self.old.binding(self.cache),'path':self.cache.name}
  self.packet=self.job/'research_packet.json';self.packet.write_bytes(self.old.canonical({'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original','sources':[{'state':'retrieved_text','content_binding':cache,'text_binding':cache}]}))
  self.blueprint=self.job/'blueprint.json';self.blueprint.write_bytes(self.old.canonical({'research_packet_sha256':sha(self.packet),'fixture':True}))
  self.geometry=self.job/'geometry.json';g=json.loads((H.parent/'world-habitat-realism-025/fixtures/synthetic_habitat.json').read_text())
  g.update(research_packet_sha256=sha(self.packet),blueprint_sha256=sha(self.blueprint));self.geometry.write_bytes(self.old.canonical(g))
  self.saved=self.old.create_preview(self.geometry,self.packet,self.blueprint)
  (self.job/'latest-layout-pipeline.json').write_text(json.dumps({'fixture_selected_preview':self.saved}))
  for n in ('viewer.mjs','walk_controller.mjs','index.html','style.css','world_layout_preview.py'):(self.engine/n).write_bytes((ENGINE/n).read_bytes())
  self.new=load(self.engine/'world_layout_preview.py','new028');self.new.THREE_BUILD=self.old.THREE_BUILD;self.new.NODE=self.old.NODE
  self.h=load(helper,'world_builder_engine.preview_refresh028');self.h.PROJECT=self.root
  self.h.latest_preview=Mock(return_value=self.saved);self.h.create_preview=Mock(wraps=self.new.create_preview);self.h.verify_preview=self.new.verify_preview
  self.before={str(p):sha(p) for p in [*self.job.rglob('*'),*Path(self.saved['manifest_path']).parent.rglob('*')] if p.is_file()}
 def tearDown(self):
  assert self.root.parent==Path(tempfile.gettempdir()).resolve() and self.root.name.startswith('world028-');self.temp.cleanup()
 def unchanged(self):self.assertTrue(all(sha(p)==d for p,d in self.before.items()))
 def test_current_assets_create_distinct_preserved_preview_without_models(self):
  with patch.object(pipeline,'run',side_effect=AssertionError('model pipeline forbidden'),create=True),patch.object(pipeline.LocalModelClient,'generate',side_effect=AssertionError('model forbidden')):
   result=self.h.refresh_saved_preview(self.job)
  self.assertNotEqual(result['manifest_path'],self.saved['manifest_path']);self.assertFalse(result['research_regenerated']);self.assertEqual(result['model_jobs'],0)
  current=self.new.verify_preview(result['manifest_path'],result['manifest_sha256'])
  self.assertEqual(current['assets']['/viewer.mjs']['sha256'],sha(ENGINE/'viewer.mjs'));self.unchanged()
 def test_repeated_open_reuses_stable_build_and_no_new_job_state(self):
  first=self.h.refresh_saved_preview(self.job);files={str(p):sha(p) for p in self.root.rglob('*') if p.is_file()}
  second=self.h.refresh_saved_preview(self.job);self.assertEqual(first['manifest_path'],second['manifest_path']);self.assertTrue(second['reused'])
  self.assertEqual(files,{str(p):sha(p) for p in self.root.rglob('*') if p.is_file()});self.unchanged()
 def test_invalid_or_external_job_rejected_before_builder(self):
  for path in (self.root,self.root/'missing',self.job.parent):
   with self.subTest(path=path),self.assertRaises((ValueError,OSError)):self.h.refresh_saved_preview(path)
  self.h.create_preview.assert_not_called();self.unchanged()
 def test_damaged_job_metadata_rejected(self):
  (self.job/'job.json').write_text('{}')
  with self.assertRaises(ValueError):self.h.refresh_saved_preview(self.job)
  self.h.latest_preview.assert_not_called();self.h.create_preview.assert_not_called()
 def test_saved_manifest_tamper_rejected_before_build(self):
  p=Path(self.saved['manifest_path']);p.write_bytes(p.read_bytes()+b' ')
  with self.assertRaises(ValueError):self.h.refresh_saved_preview(self.job)
  self.h.create_preview.assert_not_called()
 def test_changed_geometry_and_research_are_not_reinterpreted(self):
  for p in (self.geometry,self.packet,self.cache):
   with self.subTest(path=p):
    raw=p.read_bytes();p.write_bytes(raw+b' ')
    with self.assertRaises(ValueError):self.h.refresh_saved_preview(self.job)
    self.h.create_preview.assert_not_called();p.write_bytes(raw)
  self.unchanged()
 def test_mismatched_research_job_rejected(self):
  real=self.h.verify_preview
  def altered(*args):
   data=copy.deepcopy(real(*args));data['inputs']['research_packet']['path']=str(self.root/'wrong/research_packet.json');return data
  self.h.verify_preview=altered
  with self.assertRaisesRegex(ValueError,'different research job'):self.h.refresh_saved_preview(self.job)
  self.h.create_preview.assert_not_called();self.unchanged()
 def test_builder_failure_preserves_old_data(self):
  self.h.create_preview.side_effect=ValueError('Controlled preflight failure')
  with self.assertRaisesRegex(ValueError,'Controlled'):self.h.refresh_saved_preview(self.job)
  self.unchanged()
 def test_concurrent_pointer_change_is_held_without_repair(self):
  self.h.latest_preview.side_effect=[self.saved,{**self.saved,'manifest_sha256':'0'*64}]
  with self.assertRaisesRegex(ValueError,'selection changed'):self.h.refresh_saved_preview(self.job)
  self.unchanged()
 def test_concurrent_metadata_change_is_held(self):
  actual=self.h.create_preview
  def build(*args):
   result=actual(*args);p=self.job/'job.json';data=json.loads(p.read_text());data['stage']='changed_elsewhere';p.write_text(json.dumps(data));return result
  self.h.create_preview=build
  with self.assertRaisesRegex(ValueError,'research changed'):self.h.refresh_saved_preview(self.job)
 def test_new_result_cannot_substitute_different_source(self):
  actual=self.h.verify_preview;calls=0
  def altered(*args):
   nonlocal calls
   result=actual(*args);calls+=1
   if calls==2:result=copy.deepcopy(result);result['inputs']['geometry_source']['sha256']='f'*64
   return result
  self.h.verify_preview=altered
  with self.assertRaisesRegex(ValueError,'changed a saved layout source'):self.h.refresh_saved_preview(self.job)
  self.unchanged()

class CallbackTests(unittest.TestCase):
 def test_owned_server_calls_refresh_then_serves_exact_result(self):
  fake=types.ModuleType('world_builder_engine.preview_refresh');fake.refresh_saved_preview=Mock(return_value={'manifest_path':'exact.json','manifest_sha256':'a'*64})
  with patch.dict(sys.modules,{'world_builder_engine.preview_refresh':fake}):m=load(H/'candidate/tools/world_builder_engine/preview_server.py','world_builder_engine.server028')
  server=Mock(server_port=9000);m.make_server=Mock(return_value=server)
  with patch.object(sys,'argv',['preview_server.py','--job','saved-job']),patch('sys.stdout',new=io.StringIO()) as stream:m.main()
  fake.refresh_saved_preview.assert_called_once_with('saved-job');m.make_server.assert_called_once_with('exact.json',0,'a'*64)
  server.serve_forever.assert_called_once();server.server_close.assert_called_once();self.assertEqual(json.loads(stream.getvalue())['url'],'http://127.0.0.1:9000/')
 def test_actual_workspace_callback_reports_current_presentation(self):
  source=(H/'candidate/tools/world_builder_workspace.py').read_text(encoding='utf-8');tree=ast.parse(source)
  method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='open_layout_preview')
  ns={'open_preview':Mock(return_value='owned-new-session')};exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual-native-method>','exec'),ns)
  app=types.SimpleNamespace(_research_latest=Path('saved-job'),_layout_preview='old-session',log=Mock())
  ns['open_layout_preview'](app);ns['open_preview'].assert_called_once_with(Path('saved-job'),'old-session');self.assertEqual(app._layout_preview,'owned-new-session')
  self.assertIn('current presentation',app.log.call_args.args[0]);self.assertIn('text="Open current preview", command=self.open_layout_preview',source)
 def test_adapter_allows_real_preflight_bound_without_other_changes(self):
  path='tools/world_builder_engine/workspace_adapter.py';before=(H/'baseline'/path).read_text(encoding='utf-8');after=(H/'candidate'/path).read_text(encoding='utf-8')
  self.assertEqual(after,before.replace('ready.get(timeout=12)','ready.get(timeout=32)'))

if __name__=='__main__':
 before={str(p):sha(p) for p in (K/'tools/world_builder_workspace.py',ENGINE/'workspace_adapter.py',ENGINE/'preview_server.py',ENGINE/'world_layout_preview.py')}
 stream=io.StringIO();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (RefreshTests,CallbackTests)])
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 assert all(sha(p)==d for p,d in before.items())
 receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue(),
  'portable_support_sources_unchanged':True,'owner_data_writes':0,'gpu_model_network_browser_calls':0,'synthetic_preview_builds_only':True,'three_assets':'inert identity fixtures, no graphics','pipeline_selection':'test double; real native saved selection validated separately by root','native_callbacks_executed_headless':True}
 out=H/('TEST-RESULT-'+str(len(list(H.glob('TEST-RESULT-*.json')))+1)+'.json');out.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in receipt.items() if k!='output'}));print(stream.getvalue() if not result.wasSuccessful() else '')
 raise SystemExit(not result.wasSuccessful())
