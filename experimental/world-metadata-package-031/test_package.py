from pathlib import Path
import copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
import package_writer as writer
H=Path(__file__).resolve().parent
CORE=Path(os.environ.get('WORLD_METADATA_CORE') or H.parent/'world-scene-metadata-030')
if not CORE.is_dir():CORE=H.parent/'world-scene-metadata-candidate-030'
NODE=shutil.which('node')
class PackageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='worldmeta031-');self.root=Path(self.temp.name).resolve();self.folder=self.root/'sources';self.folder.mkdir()
  self.cache=self.folder/'source.txt';self.cache.write_text('Synthetic reference text. This content must not appear in an export.')
  cache=writer.binding(self.cache);cache['path']=self.cache.name
  self.packet=self.folder/'research_packet.json';self.packet.write_bytes(writer.canonical({'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original','private_memory':'Never include this family story','sources':[{'state':'retrieved_text','content_binding':cache,'text_binding':cache}]}))
  self.blueprint=self.folder/'blueprint.json';self.blueprint.write_bytes(writer.canonical({'research_packet_sha256':writer.sha(self.packet.read_bytes()),'fixture':'Synthetic only'}))
  self.geometry=self.folder/'geometry.json';g=json.loads((CORE/'fixtures/synthetic_habitat.json').read_text(encoding='utf-8'))
  g.update(research_packet_sha256=writer.sha(self.packet.read_bytes()),blueprint_sha256=writer.sha(writer.canonical(json.loads(self.blueprint.read_bytes()))),private_memory='Never include this biography',media_path=str(self.root/'personal_photo.jpg'))
  self.geometry.write_bytes(writer.canonical(g));self.bindings=self.folder/'bindings.json';self.save_bindings()
  self.before={p.name:writer.sha(p.read_bytes()) for p in self.folder.iterdir()}
 def tearDown(self):
  assert self.root.parent==Path(tempfile.gettempdir()).resolve() and self.root.name.startswith('worldmeta031-');self.temp.cleanup()
 def save_bindings(self,contract=writer.INPUT_CONTRACT):
  data={'contract':contract,'inputs':{name:writer.binding(path) for name,path in [('geometry_source',self.geometry),('blueprint',self.blueprint),('research_packet',self.packet)]}}
  if contract=='isolated_world_layout_preview_v1':data['receipt_sha256']=writer.sha(writer.canonical(data))
  self.bindings.write_bytes(writer.canonical(data));self.expected=writer.sha(self.bindings.read_bytes())
 def build(self,name='package',**kw):return writer.build_package(self.bindings,self.expected,self.root/name,scene_id='synthetic_habitat',core_root=CORE,node=NODE,**kw)
 def assert_unchanged(self):self.assertEqual(self.before,{p.name:writer.sha(p.read_bytes()) for p in self.folder.iterdir()})
 def test_actual_byte_chain_and_portable_self_contained_package(self):
  result=self.build();self.assertEqual(result['status'],'METADATA_PACKAGE_CREATED');self.assert_unchanged()
  folder=self.root/'package';scene=json.loads((folder/'scene.json').read_bytes());manifest=json.loads((folder/'manifest.json').read_bytes())
  self.assertEqual(scene['provenance']['binding_verification'],'actual_bound_bytes_verified_by_package_writer')
  self.assertEqual(manifest['verified_source_digests']['geometry_source']['sha256'],writer.sha(self.geometry.read_bytes()))
  self.assertEqual(len(scene['doors']),6);self.assertFalse(manifest['mesh_files_included']);self.assertEqual(set(p.name for p in folder.iterdir()),{'scene.json','manifest.json','README.txt'})
  # Metadata integrity remains checkable after original sources are unavailable.
  self.cache.rename(self.cache.with_suffix('.unavailable'));self.assertEqual(writer.verify_package(folder)['status'],'METADATA_PACKAGE_INTEGRITY_PASS')
  moved=self.root/'relocated';shutil.copytree(folder,moved);self.assertEqual(writer.verify_package(moved)['manifest_sha256'],result['manifest_sha256'])
 def test_repeat_build_in_new_location_has_identical_bytes(self):
  one=self.build('one');two=self.build('two');self.assertEqual(one,two)
  for p in (self.root/'one').iterdir():self.assertEqual(p.read_bytes(),(self.root/'two'/p.name).read_bytes())
  self.assert_unchanged()
 def test_no_source_text_memory_media_paths_or_absolute_paths_bundled(self):
  self.build();text='\n'.join(p.read_text(encoding='utf-8') for p in (self.root/'package').iterdir())
  for forbidden in ('Never include this family story','Never include this biography','This content must not appear',str(self.root),'personal_photo.jpg','private_memory'):
   self.assertNotIn(forbidden,text)
  for p in (self.root/'package').glob('*.json'):writer.no_local_paths(json.loads(p.read_bytes()))
 def test_changed_bindings_manifest_held_before_output(self):
  self.bindings.write_bytes(self.bindings.read_bytes()+b' ')
  with self.assertRaisesRegex(writer.PackageError,'manifest hash'):self.build()
  self.assertFalse((self.root/'package').exists())
 def test_changed_or_missing_source_bytes_held(self):
  for p in (self.geometry,self.blueprint,self.packet,self.cache):
   with self.subTest(p=p.name):
    raw=p.read_bytes();p.write_bytes(raw+b'changed')
    with self.assertRaises(writer.PackageError):self.build()
    p.write_bytes(raw);p.rename(p.with_suffix(p.suffix+'.missing'))
    with self.assertRaises(writer.PackageError):self.build()
    p.with_suffix(p.suffix+'.missing').rename(p)
  self.assertFalse((self.root/'package').exists());self.assert_unchanged()
 def test_missing_malformed_or_unknown_contract_binding_held(self):
  original=json.loads(self.bindings.read_bytes())
  for mutate in (lambda x:x['inputs'].pop('blueprint'),lambda x:x['inputs'].__setitem__('blueprint',None),lambda x:x.__setitem__('contract','unknown')):
   value=copy.deepcopy(original);mutate(value);self.bindings.write_bytes(writer.canonical(value));self.expected=writer.sha(self.bindings.read_bytes())
   with self.assertRaises(writer.PackageError):self.build()
  self.assertFalse((self.root/'package').exists())
 def test_rebound_but_inconsistent_geometry_blueprint_chain_held(self):
  g=json.loads(self.geometry.read_bytes());g['blueprint_sha256']='f'*64;self.geometry.write_bytes(writer.canonical(g));self.save_bindings()
  with self.assertRaisesRegex(writer.PackageError,'blueprint digest'):self.build()
  self.assertFalse((self.root/'package').exists())
 def test_cache_escape_and_changed_cache_pin_held(self):
  packet=json.loads(self.packet.read_bytes());packet['sources'][0]['content_binding']['path']='../outside.txt'
  self.packet.write_bytes(writer.canonical(packet));b=json.loads(self.blueprint.read_bytes());b['research_packet_sha256']=writer.sha(self.packet.read_bytes());self.blueprint.write_bytes(writer.canonical(b))
  g=json.loads(self.geometry.read_bytes());g['research_packet_sha256']=writer.sha(self.packet.read_bytes());g['blueprint_sha256']=writer.sha(writer.canonical(b));self.geometry.write_bytes(writer.canonical(g));self.save_bindings()
  with self.assertRaisesRegex(writer.PackageError,'escapes'):self.build()
  self.assertFalse((self.root/'package').exists())
 def test_existing_output_and_source_directory_never_overwritten(self):
  self.build();before={p.name:p.read_bytes() for p in (self.root/'package').iterdir()}
  with self.assertRaisesRegex(writer.PackageError,'already exists'):self.build()
  self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'package').iterdir()})
  with self.assertRaisesRegex(writer.PackageError,'already exists'):writer.build_package(self.bindings,self.expected,self.folder,scene_id='synthetic_habitat',core_root=CORE,node=NODE)
  self.assert_unchanged()
 def test_package_tamper_and_missing_asset_detected(self):
  self.build();p=self.root/'package/scene.json';raw=p.read_bytes();p.write_bytes(raw+b' ')
  with self.assertRaisesRegex(writer.PackageError,'digest mismatch'):writer.verify_package(self.root/'package')
  p.write_bytes(raw);p.unlink()
  with self.assertRaisesRegex(writer.PackageError,'Unexpected file'):writer.verify_package(self.root/'package')
 def test_existing_preview_binding_shape_and_seal_supported(self):
  self.save_bindings('isolated_world_layout_preview_v1');self.build();value=json.loads(self.bindings.read_bytes());value['receipt_sha256']='f'*64
  self.bindings.write_bytes(writer.canonical(value));self.expected=writer.sha(self.bindings.read_bytes())
  with self.assertRaisesRegex(writer.PackageError,'seal'):self.build('changed')
 def test_core_code_tamper_rejected_before_node(self):
  altered=self.root/'core';shutil.copytree(CORE/'candidate',altered/'candidate');shutil.copyfile(CORE/'room_dressing_plan.mjs',altered/'room_dressing_plan.mjs')
  p=altered/'room_dressing_plan.mjs';p.write_bytes(p.read_bytes()+b'\n// changed\n')
  with patch.object(writer.subprocess,'run',side_effect=AssertionError('Node must not start')):
   with self.assertRaisesRegex(writer.PackageError,'core changed'):writer.build_package(self.bindings,self.expected,self.root/'package',scene_id='synthetic_habitat',core_root=altered,node=NODE)
 def test_source_change_after_projection_detected_before_output(self):
  actual=writer.subprocess.run
  def run(*args,**kwargs):
   result=actual(*args,**kwargs);self.cache.write_bytes(b'changed elsewhere');return result
  with patch.object(writer.subprocess,'run',side_effect=run):
   with self.assertRaisesRegex(writer.PackageError,'Bound source'):self.build()
  self.assertFalse((self.root/'package').exists())
 def test_local_path_hidden_inside_label_is_held(self):
  g=json.loads(self.geometry.read_bytes());g['rooms'][0]['name']='Notes at C:/private/home';self.geometry.write_bytes(writer.canonical(g));self.save_bindings()
  with self.assertRaisesRegex(writer.PackageError,'absolute local path'):self.build()
  self.assertFalse((self.root/'package').exists())
 def test_cli_build_and_verify_roundtrip(self):
  command=[sys.executable,'-B',str(H/'package_writer.py'),'build','--bindings',str(self.bindings),'--bindings-sha256',self.expected,'--output',str(self.root/'cli'),'--scene-id','synthetic_habitat','--core-root',str(CORE),'--node',NODE]
  result=subprocess.run(command,capture_output=True,check=False);self.assertEqual(result.returncode,0,result.stderr.decode());self.assertEqual(json.loads(result.stdout)['status'],'METADATA_PACKAGE_CREATED')
  verify=subprocess.run([sys.executable,'-B',str(H/'package_writer.py'),'verify','--package',str(self.root/'cli')],capture_output=True,check=False)
  self.assertEqual(verify.returncode,0,verify.stderr.decode());self.assertEqual(json.loads(verify.stdout)['status'],'METADATA_PACKAGE_INTEGRITY_PASS');self.assert_unchanged()

if __name__=='__main__':
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackageTests))
 receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue(),
  'actual_source_hashes_verified':True,'model_network_gpu_visual_calls':0,'owner_data_used_or_changed':False,'metadata_only':True,'installation':False}
 n=len(list(H.glob('TEST-RESULT-*.json')))+1;(H/('TEST-RESULT-'+str(n)+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in receipt.items() if k!='output'}));print(stream.getvalue() if not result.wasSuccessful() else '')
 raise SystemExit(not result.wasSuccessful())
