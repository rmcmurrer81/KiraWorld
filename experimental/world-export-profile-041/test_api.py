import os
"""Lightweight mocked worker tests. Never invoke Node, Canvas, GPU or native UI."""
from pathlib import Path
import ast,copy,hashlib,io,json,queue,sys,tempfile,types,unittest
from unittest.mock import Mock,patch
H=Path(__file__).resolve().parent;K=Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'))
from world_builder_engine import pipeline
from fixture_builder import build_fixture
def load(path,name,package=''):
 m=types.ModuleType(name);m.__file__=str(path);m.__package__=package;exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
ASSETS=H/'candidate/tools/world_builder_engine/layout_package_assets'
bindings=load(ASSETS/'source_bindings.py','bindings039')
policy=load(K/'tools/world_builder_engine/layout_airlock_policy.py','world_builder_engine.layout_airlock_policy','world_builder_engine')
profile=load(H/'candidate/tools/world_builder_engine/layout_recipe_profile.py','world_builder_engine.layout_recipe_profile','world_builder_engine')
package=types.ModuleType('world_builder_engine.layout_package_assets');package.source_bindings=bindings
with patch.dict(sys.modules,{'world_builder_engine.layout_package_assets':package,'world_builder_engine.layout_airlock_policy':policy,'world_builder_engine.layout_recipe_profile':profile}):
 helper=load(H/'candidate/tools/world_builder_engine/layout_package_export.py','world_builder_engine.layout_package_export039','world_builder_engine')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()

class ApiTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='world039-',dir=H);self.root=Path(self.tmp.name).resolve()
  self.brief={'subject':'Synthetic habitat A'};canonical_brief=(json.dumps(self.brief,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();digest=hashlib.sha256(canonical_brief).hexdigest()
  self.job=self.root/'Data/world_research_jobs'/('world_research_'+digest[:20]);self.job.mkdir(parents=True)
  (self.job/'job.json').write_bytes(canonical({'schema_version':1,'job_kind':'isolated_world_research_job','job_id':self.job.name,'brief':self.brief,'brief_sha256':digest,'stage':'research_complete'}))
  self.packet=self.job/'research_packet.json';self.packet.write_bytes(canonical({'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original','sources':[]}))
  b,g=build_fixture(sha(self.packet));self.blueprint=self.job/'blueprint.json';self.blueprint.write_bytes(canonical(b))
  self.geometry=self.job/'geometry.json';self.geometry.write_bytes(canonical(g))
  self.manifest=self.root/'selected-preview.json';self.state={'contract':bindings.INPUT_CONTRACT,'source_mode':'source_bound_original_layout',
   'inputs':{role:bindings.binding(p) for role,p in [('geometry_source',self.geometry),('blueprint',self.blueprint),('research_packet',self.packet)]},'source_pins':{k:{'sha256':v} for k,v in helper.RENDERER.items()}}
  self.manifest.write_bytes(canonical(self.state));self.selection={'manifest_path':str(self.manifest),'manifest_sha256':sha(self.manifest)}
  self.assets=self.root/'exporter';self.assets.mkdir();files={}
  for name in ('source/room_dressing_plan.mjs','source/walk_controller.mjs','build_glb.mjs'):
   p=self.assets/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'mocked producer');files[name]={'sha256':sha(p),'bytes':p.stat().st_size}
  self.dep={};external={}
  for role in ('node','canvas-package','canvas-native','font-segoe-regular','font-segoe-semibold','font-monospace'):
   p=self.root/(role+'.test');p.write_bytes(role.encode());self.dep[role]=p;external[role]={'sha256':sha(p),'bytes':p.stat().st_size}
  (self.assets/'PRODUCER-PINS.json').write_bytes(canonical({'files':files,'external':external}))
  self.patches=[patch.object(helper,'PROJECT',self.root),patch.object(helper,'ASSETS',self.assets),patch.object(helper,'latest_preview',Mock(return_value=self.selection)),patch.object(helper,'verify_preview',Mock(side_effect=self.verify)),
   patch.object(helper.subprocess,'run',Mock(side_effect=self.worker)),patch.object(pipeline.LocalModelClient,'generate',side_effect=AssertionError('model queue forbidden'))]
  for p in self.patches:p.start()
  self.out=self.root/'Export-package';self.before={str(p):sha(p) for p in self.job.rglob('*') if p.is_file()}
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  assert self.root.parent==H.resolve() and self.root.name.startswith('world039-');self.tmp.cleanup()
 def verify(self,path,digest):
  if sha(path)!=digest:raise ValueError('Manifest changed')
  return json.loads(Path(path).read_bytes())
 def worker(self,args,*,input,**kwargs):
  req=json.loads(input);self.request=req;target=Path(req['output']);(target/'scene.glb').write_bytes(b'mocked worker output, not real GLB')
  pairs=policy.expected_airlock_pairs(req['geometry']);doors=[];nodes=[];colliders=[]
  for portal in req['geometry']['portals']:
   pid=portal['id'];did='door:'+pid;leaf='node:door_'+pid+'_leaf';pair_ids=[p['id'] for p in pairs if did in p['door_ids']]
   doors.append({'id':did,'portal_id':pid,'leaf_node_id':leaf,'room_ids':['room:'+portal['room_a'],'room:'+portal['room_b']],
    'interlock_pair_ids':pair_ids,'interaction':{'rules':['paired_airlock_peer_closed_stopped'] if pair_ids else []}})
   nodes.append({'id':leaf,'kind':'door_leaf'});colliders.append({'id':'collider:door_'+pid+'_leaf','owner_node_id':leaf,'motion':'kinematic'})
  scene={'contract':'world_scene_metadata_v2','scene_id':req['options']['sceneId'],'airlock_pairs':pairs,'doors':doors,'nodes':nodes,'colliders':colliders,
   'provenance':{'door_contract':'preview_hinged_doors_v2','source_digests':req['options']['sourceDigests']}}
  if hasattr(self,'corrupt_scene'):self.corrupt_scene(scene)
  (target/'scene.json').write_bytes(canonical(scene))
  (target/'ROUNDTRIP.json').write_bytes(canonical({'status':'CPU_AUTHORED_GLB_EXPORT_IMPORT_PASS','glb_sha256':sha(target/'scene.glb'),
   'checks':{'airlock_pair_metadata_preserved':not getattr(self,'bad_pair_roundtrip',False),'airlock_pairs':policy.expected_airlock_pairs(req['geometry'])}}))
  return types.SimpleNamespace(returncode=0,stdout=b'{}',stderr=b'')
 def run_export(self,**kwargs):return helper.export_saved_layout_package(self.job,self.out,dependencies=self.dep,**kwargs)
 def unchanged(self):self.assertTrue(all(sha(p)==v for p,v in self.before.items()))
 def test_explicit_selected_preview_and_sources_used_without_global_latest(self):
  result=self.run_export(preview_binding=self.selection);self.assertEqual(result['status'],'created');helper.latest_preview.assert_not_called();self.unchanged()
  self.assertEqual(self.request['options']['sourceDigests']['geometry'],sha(self.geometry));self.assertFalse(result['capabilities']['vr_runtime']);self.assertFalse(result['capabilities']['engine_native_collision'])
 def test_job_local_pointer_used_when_no_open_preview(self):
  result=self.run_export();self.assertEqual(result['status'],'created');self.assertTrue(all(c.args==(self.job,) for c in helper.latest_preview.call_args_list));self.unchanged()
 def test_new_controller_pin_and_explicit_policy_are_exported(self):
  self.assertEqual(helper.RENDERER['walk_controller.mjs'],'0884cce50d33a66e4a974a76fc7a0a15947bcb776f130b1b0a81b43adef76791')
  self.assertEqual(self.run_export()['status'],'created');manifest=json.loads((self.out/'manifest.json').read_bytes())
  self.assertEqual(len(manifest['airlock_pair_policy']),1);self.assertEqual(manifest['airlock_pair_policy'][0]['contract'],policy.PAIR_CONTRACT)
  self.assertFalse(manifest['airlock_pair_policy'][0]['engine_runtime_included']);self.unchanged()
 def test_old_controller_is_not_mislabeled_as_sequenced(self):
  self.state['source_pins']['walk_controller.mjs']['sha256']='5c81e5926690a7fee3dbfcd4ff41d40b6da9bc3fef2ae7cbc77dcd91c74a51a4'
  self.manifest.write_bytes(canonical(self.state));self.selection['manifest_sha256']=sha(self.manifest)
  self.assertEqual(self.run_export()['status'],'unsupported_preview');helper.subprocess.run.assert_not_called()
 def test_missing_pair_metadata_is_held(self):
  self.corrupt_scene=lambda s:s.pop('airlock_pairs');self.assertEqual(self.run_export()['status'],'airlock_policy_invalid');self.assertFalse((self.out/'manifest.json').exists());self.unchanged()
 def test_duplicate_leaf_association_is_held(self):
  self.corrupt_scene=lambda s:s['airlock_pairs'][0]['leaf_node_ids'].__setitem__(1,s['airlock_pairs'][0]['leaf_node_ids'][0])
  self.assertEqual(self.run_export()['status'],'airlock_policy_invalid');self.unchanged()
 def test_wrong_source_room_is_held(self):
  self.corrupt_scene=lambda s:s['doors'][0]['room_ids'].__setitem__(0,'room:unrelated')
  self.assertEqual(self.run_export()['status'],'airlock_policy_invalid');self.unchanged()
 def test_missing_pair_rule_is_held(self):
  self.corrupt_scene=lambda s:s['doors'][0]['interaction']['rules'].clear()
  self.assertEqual(self.run_export()['status'],'airlock_policy_invalid');self.unchanged()
 def test_wrong_leaf_collider_owner_is_held(self):
  self.corrupt_scene=lambda s:s['colliders'][0].__setitem__('owner_node_id','node:wrong')
  self.assertEqual(self.run_export()['status'],'airlock_policy_invalid');self.unchanged()
 def test_missing_importer_pair_check_is_held(self):
  self.bad_pair_roundtrip=True;self.assertEqual(self.run_export()['status'],'airlock_policy_invalid');self.unchanged()
 def test_mismatched_project_rejected_before_worker(self):
  helper.verify_preview.side_effect=lambda *a:{**self.state,'inputs':{**self.state['inputs'],'research_packet':{'path':str(self.root/'other/research_packet.json')}}}
  self.assertEqual(self.run_export(preview_binding=self.selection)['status'],'invalid_selection');helper.subprocess.run.assert_not_called();self.assertFalse(self.out.exists())
 def test_old_renderer_returns_open_current_preview_instruction(self):
  self.state['source_pins']['viewer.mjs']['sha256']='0'*64;self.manifest.write_bytes(canonical(self.state));self.selection['manifest_sha256']=sha(self.manifest)
  result=self.run_export(preview_binding=self.selection);self.assertEqual(result['status'],'unsupported_preview');self.assertIn('Open current preview',result['message']);helper.subprocess.run.assert_not_called()
 def test_unknown_functional_recipe_is_not_inferred_as_habitat(self):
  g=json.loads(self.geometry.read_bytes());g['functional_program']={k:'other' for k in g['functional_program']};self.geometry.write_bytes(canonical(g));self.state['inputs']['geometry_source']=bindings.binding(self.geometry);self.manifest.write_bytes(canonical(self.state));self.selection['manifest_sha256']=sha(self.manifest)
  self.assertEqual(self.run_export()['status'],'unsupported_recipe');helper.subprocess.run.assert_not_called()
 def test_missing_dependency_rejected_before_output(self):
  self.dep['font-monospace'].unlink();self.assertEqual(self.run_export()['status'],'dependency_missing');self.assertFalse(self.out.exists());helper.subprocess.run.assert_not_called();self.unchanged()
 def test_changed_structure_with_rebound_bytes_still_rejects_blueprint_mismatch(self):
  g=json.loads(self.geometry.read_bytes());g['primitives'][0]['size'][0]+=.1;self.geometry.write_bytes(canonical(g))
  self.state['inputs']['geometry_source']=bindings.binding(self.geometry);self.manifest.write_bytes(canonical(self.state));self.selection['manifest_sha256']=sha(self.manifest)
  self.assertEqual(self.run_export()['status'],'unsupported_layout');helper.subprocess.run.assert_not_called();self.assertFalse(self.out.exists())
 def test_new_supported_shape_is_eligible_without_a_fixture_hash(self):
  b,g=build_fixture(sha(self.packet),'wider');self.blueprint.write_bytes(canonical(b));self.geometry.write_bytes(canonical(g))
  for role,path in [('geometry_source',self.geometry),('blueprint',self.blueprint)]:self.state['inputs'][role]=bindings.binding(path)
  self.manifest.write_bytes(canonical(self.state));self.selection['manifest_sha256']=sha(self.manifest)
  self.assertNotEqual(sha(self.geometry),'1af9ae1254356f0523f722d284b140b8e34eb6af3bf236ceef91ad5f145a9d75')
  self.assertEqual(self.run_export()['status'],'created');self.assertTrue(json.loads((self.out/'manifest.json').read_bytes())['recipe_eligibility']['source_structure_recompiled'])
 def test_changed_dependency_rejected_before_output(self):
  self.dep['canvas-native'].write_bytes(b'changed');self.assertEqual(self.run_export()['status'],'dependency_changed');self.assertFalse(self.out.exists());helper.subprocess.run.assert_not_called()
 def test_changed_producer_rejected(self):
  (self.assets/'build_glb.mjs').write_bytes(b'changed');self.assertEqual(self.run_export()['status'],'producer_changed');helper.subprocess.run.assert_not_called()
 def test_existing_destination_never_overwritten(self):
  self.out.mkdir();(self.out/'mine.txt').write_text('keep');self.assertEqual(self.run_export()['status'],'destination_exists');self.assertEqual((self.out/'mine.txt').read_text(),'keep');helper.subprocess.run.assert_not_called()
 def test_destination_in_originals_rejected(self):
  self.out=self.job/'new-output';self.assertEqual(self.run_export()['status'],'invalid_destination');self.assertFalse(self.out.exists());self.unchanged()
 def test_tampered_geometry_binding_rejected(self):
  self.geometry.write_bytes(self.geometry.read_bytes()+b' ');self.assertEqual(self.run_export()['status'],'source_or_export_held');helper.subprocess.run.assert_not_called();self.assertFalse(self.out.exists())
 def test_missing_geometry_binding_rejected(self):
  self.geometry.unlink();self.assertEqual(self.run_export()['status'],'source_or_export_held');helper.subprocess.run.assert_not_called()
 def test_concurrent_pointer_change_retains_incomplete_not_ready(self):
  helper.latest_preview.side_effect=[self.selection,{'manifest_path':'new','manifest_sha256':'1'*64}]
  result=self.run_export();self.assertEqual(result['status'],'source_changed');self.assertFalse((self.out/'manifest.json').exists());self.assertTrue((self.out/'EXPORT-INCOMPLETE.json').exists());self.unchanged()
 def test_worker_failure_retains_incomplete_not_ready(self):
  helper.subprocess.run.return_value=types.SimpleNamespace(returncode=1);helper.subprocess.run.side_effect=None
  result=self.run_export();self.assertEqual(result['status'],'export_failed');self.assertFalse((self.out/'manifest.json').exists());self.assertTrue((self.out/'EXPORT-INCOMPLETE.json').exists());self.unchanged()
 def test_source_change_during_worker_holds_completion(self):
  run=self.worker
  def changed(*a,**kw):
   result=run(*a,**kw);p=self.job/'job.json';data=json.loads(p.read_bytes());data['stage']='changed';p.write_bytes(canonical(data));return result
  helper.subprocess.run.side_effect=changed;self.assertEqual(self.run_export()['status'],'source_changed');self.assertFalse((self.out/'manifest.json').exists())

class CallbackTests(unittest.TestCase):
 def setUp(self):
  source=(K/'tools/world_builder_workspace.py').read_text(encoding='utf-8');self.source=source;tree=ast.parse(source)
  wanted={'export_3d_package','_poll_3d_export','open_export_folder','_close_world_builder'}
  methods=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name in wanted]
  self.threads=[]
  def thread(**kwargs):
   value=types.SimpleNamespace(target=kwargs['target'],start=Mock());self.threads.append(value);return value
  self.ns={'Path':Path,'queue':queue,'datetime':__import__('datetime').datetime,'timezone':__import__('datetime').timezone,'threading':types.SimpleNamespace(Thread=thread),
   'filedialog':types.SimpleNamespace(askdirectory=Mock(return_value='C:/exports')),'export_saved_layout_package':Mock(return_value={'status':'created','output_dir':'C:/exports/result','message':'Ready'}),'open_path':Mock(),'close_preview':Mock()}
  exec(compile(ast.Module(body=methods,type_ignores=[]),'<actual-native039-methods>','exec'),self.ns)
  self.app=types.SimpleNamespace(_research_latest=Path('selected-job-A'),_layout_preview=types.SimpleNamespace(manifest={'manifest_path':'selected-preview-A','manifest_sha256':'a'*64}),_export_worker=None,_export_messages=queue.Queue(),_last_export_folder=None,_export_button=Mock(),log=Mock(),after=Mock(),_original_components_view=None,destroy=Mock())
  self.app._poll_3d_export=lambda:self.ns['_poll_3d_export'](self.app)
 def test_actual_callback_captures_selection_before_worker(self):
  self.ns['export_3d_package'](self.app);self.app._research_latest=Path('new-job-B');self.app._layout_preview=None;self.threads[0].target()
  args=self.ns['export_saved_layout_package'].call_args;self.assertEqual(args.args[0],Path('selected-job-A'));self.assertEqual(args.kwargs['preview_binding']['manifest_path'],'selected-preview-A')
  self.app._poll_3d_export();self.assertEqual(self.app._last_export_folder,Path('C:/exports/result'));self.assertEqual(self.app._research_latest,Path('new-job-B'));self.assertIsNone(self.app._export_worker)
 def test_missing_selection_and_cancel_do_not_queue(self):
  self.app._research_latest=None;self.ns['export_3d_package'](self.app);self.assertEqual(self.threads,[]);self.ns['filedialog'].askdirectory.assert_not_called()
  self.app._research_latest=Path('A');self.ns['filedialog'].askdirectory.return_value='';self.ns['export_3d_package'](self.app);self.assertEqual(self.threads,[])
 def test_duplicate_export_is_not_started(self):
  self.app._export_worker=object();self.ns['export_3d_package'](self.app);self.assertEqual(self.threads,[]);self.ns['filedialog'].askdirectory.assert_not_called()
 def test_held_result_does_not_offer_incomplete_export_as_ready(self):
  self.app._export_messages.put({'status':'unsupported_preview','message':'Open current preview','output_dir':None});self.app._poll_3d_export();self.assertIsNone(self.app._last_export_folder)
 def test_open_folder_is_explicit_and_uses_completed_output(self):
  self.ns['open_export_folder'](self.app);self.ns['open_path'].assert_not_called();self.app._last_export_folder=Path('C:/exports/approved');self.ns['open_export_folder'](self.app);self.ns['open_path'].assert_called_once_with(self.app._last_export_folder)
 def test_close_preserves_running_export_and_button_binds_actual_callback(self):
  self.app._export_worker=object();self.ns['_close_world_builder'](self.app);self.app.destroy.assert_not_called();self.assertIn('text="Export 3D package (experimental)", command=self.export_3d_package',self.source)

class CrossLanguagePolicyTests(unittest.TestCase):
 def setUp(self):
  self.scene=json.loads((H/'SYNTHETIC-POLICY-METADATA.json').read_bytes());self.geometry=json.loads((H/'fixtures/synthetic_habitat.json').read_bytes())
  self.digests=self.scene['provenance']['source_digests']
 def test_actual_node_metadata_passes_independent_python_gate(self):
  self.assertEqual(policy.validate_airlock_metadata(self.scene,self.geometry,self.digests),self.scene['airlock_pairs'])
 def test_changed_source_binding_is_rejected(self):
  with self.assertRaises(ValueError):policy.validate_airlock_metadata(self.scene,self.geometry,{**self.digests,'door_controller':'d'*64})
 def test_duplicate_leaf_node_is_rejected(self):
  self.scene['nodes'].append(copy.deepcopy(self.scene['nodes'][0]))
  with self.assertRaises(ValueError):policy.validate_airlock_metadata(self.scene,self.geometry,self.digests)
 def test_source_pair_changed_after_metadata_is_rejected(self):
  self.geometry['functional_program'].pop('airlock')
  with self.assertRaises(ValueError):policy.validate_airlock_metadata(self.scene,self.geometry,self.digests)

if __name__=='__main__':
 before=sha(K/'tools/world_builder_workspace.py');stream=io.StringIO();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (ApiTests,CallbackTests,CrossLanguagePolicyTests));result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 assert sha(K/'tools/world_builder_workspace.py')==before
 report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue(),'worker_mocked':True,'real_glb_exports':0,'gpu_models_browser_native_ui':0,'canonical_unchanged':True,'owner_data_writes':0}
 path=H/('TEST-RESULT-'+str(len(list(H.glob('TEST-RESULT-*.json')))+1)+'.json');path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='output'}));print(stream.getvalue() if not result.wasSuccessful() else '')
 raise SystemExit(not result.wasSuccessful())
