"""Disposable old/new preview integration and tamper tests; no owner writes or GPU.

Most cases use a fake preflight response and small inert Node/Three files to test
pin validation. One case runs the unchanged real Node navigation preflight.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,io,json,os,shutil,subprocess,sys,tempfile,threading,types,unittest
from unittest.mock import patch
H=Path(__file__).resolve().parent
ENGINE=H/'support/engine';CANDIDATE=H/'candidate/tools/world_builder_engine/world_layout_preview.py'
BASELINE=H/'baseline/world_layout_preview.py';GEOMETRY=H/'fixtures/SYNTHETIC-GEOMETRY-FIXTURE.json'
sys.dont_write_bytecode=True

def load(path,name):
    module=types.ModuleType(name);module.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__);return module
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
TEST_TEMP_BASE=Path(tempfile.gettempdir()).resolve()

class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='preview026-',dir=TEST_TEMP_BASE)
        self.root=Path(self.temp.name).resolve();assert self.root.parent==TEST_TEMP_BASE and self.root.name.startswith('preview026-')
        self.engine=self.root/'Kira/tools/world_builder_engine';self.engine.mkdir(parents=True)
        for name in ('index.html','style.css','viewer.mjs','walk_controller.mjs','horizontal_navigation.mjs','preflight.mjs'):
            (self.engine/name).write_bytes((ENGINE/name).read_bytes())
        self.backend=self.engine/'world_layout_preview.py';self.backend.write_bytes(BASELINE.read_bytes())
        self.three=self.root/'three';self.three.mkdir()
        for name in ('three.module.js','three.core.js'):(self.three/name).write_text('// inert fixture, not a renderer\n')
        self.node=self.root/'node-fixture.exe';self.node.write_bytes(b'inert Node identity fixture')
        self.legacy=load(self.backend,'legacy026');self.legacy.THREE_BUILD=self.three;self.legacy.NODE=self.node
        self.geometry=self.root/'geometry.json';self.geometry.write_bytes(GEOMETRY.read_bytes())
        self.packet=self.root/'research_packet.json';self.blueprint=self.root/'blueprint.json';self.cache=self.root/'source.txt'
        self.cache.write_text('Synthetic source content; not owner research.')
        cache={**self.legacy.binding(self.cache),'path':self.cache.name}
        packet={'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original',
                'sources':[{'state':'retrieved_text','content_binding':cache,'text_binding':cache}]}
        self.packet.write_bytes(self.legacy.canonical(packet))
        blueprint={'research_packet_sha256':sha(self.packet),'fixture':'not model generated'}
        self.blueprint.write_bytes(self.legacy.canonical(blueprint))
        geometry=self.legacy.load_json(self.geometry.read_bytes())
        geometry.update(research_packet_sha256=sha(self.packet),blueprint_sha256=self.legacy.sha(self.legacy.canonical(blueprint)))
        self.geometry.write_bytes(self.legacy.canonical(geometry))
        answer=subprocess.CompletedProcess([],0,b'{"status":"PASS","fixture_only":true}',b'')
        with patch.object(self.legacy.subprocess,'run',return_value=answer):
            self.saved=self.legacy.create_preview(self.geometry,self.packet,self.blueprint)
        self.path=Path(self.saved['manifest_path']);self.original=self.path.read_bytes()
        self.manifest=self.legacy.load_json(self.original)
        self.backend.write_bytes(CANDIDATE.read_bytes());self.new=load(self.backend,'new026');self.new.THREE_BUILD=self.three;self.new.NODE=self.node
    def tearDown(self):
        assert self.root.parent==TEST_TEMP_BASE and self.root.name.startswith('preview026-');self.temp.cleanup()
    def verify(self):return self.new.verify_preview(self.path,self.saved['manifest_sha256'])
    def reseal(self,value):
        value=copy.deepcopy(value)
        value['build_id']='layout-'+self.new.sha(self.new.canonical({'inputs':value['inputs'],'sources':value['source_pins']}))[:24]
        folder=self.path.parent.parent/value['build_id'];folder.mkdir(exist_ok=True)
        for url,row in value['assets'].items():
            if not url.startswith('/three.'):
                target=folder/url[1:];target.write_bytes(Path(row['path']).read_bytes());row['path']=str(target)
        body={k:v for k,v in value.items() if k!='receipt_sha256'};value['receipt_sha256']=self.new.sha(self.new.canonical(body))
        path=folder/'manifest.json';path.write_bytes(self.new.canonical(value));return path
    def test_old_manifest_reopens_after_backend_upgrade(self):
        with self.assertRaises(self.legacy.PreviewError):self.legacy.verify_preview(self.path)
        self.assertEqual(self.verify(),self.manifest);self.assertEqual(self.path.read_bytes(),self.original)
    def test_all_four_current_renderer_updates_leave_old_copies_exact(self):
        for name in self.new.COPIED_RENDERER_ASSETS:
            (self.engine/name).write_text('// new engine revision '+name)
        returned=self.verify();self.assertEqual(returned,self.manifest)
        for name in self.new.COPIED_RENDERER_ASSETS:
            self.assertEqual(sha(self.path.parent/name),self.manifest['source_pins'][name]['sha256'])
    def test_missing_original_renderer_files_do_not_discard_saved_copies(self):
        for name in self.new.COPIED_RENDERER_ASSETS:(self.engine/name).unlink()
        self.assertEqual(self.verify(),self.manifest)
    def test_saved_copy_tampering_rejected_even_after_current_engine_update(self):
        for name in self.new.COPIED_RENDERER_ASSETS:
            with self.subTest(asset=name):
                saved=self.path.parent/name;old=saved.read_bytes();(self.engine/name).write_text('updated engine')
                saved.write_bytes(old+b'\n// tampered saved bytes')
                with self.assertRaisesRegex(self.new.PreviewError,'Pinned preview file changed'):self.verify()
                saved.write_bytes(old)
    def test_missing_saved_copy_rejected_even_with_current_renderer_present(self):
        for name in self.new.COPIED_RENDERER_ASSETS:
            with self.subTest(asset=name):
                saved=self.path.parent/name;old=saved.read_bytes();saved.unlink()
                with self.assertRaisesRegex(self.new.PreviewError,'Missing or oversized'):self.verify()
                saved.write_bytes(old)
    def test_renderer_source_pin_path_and_digest_shape_rejected(self):
        for field,value in [('path',str(self.root/'other.mjs')),('sha256','invalid'),('bytes',True),('extra','unknown')]:
            changed=copy.deepcopy(self.manifest);changed['source_pins']['viewer.mjs'][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(self.new.PreviewError,'Invalid recorded'):
                self.new.verify_preview(self.reseal(changed))
    def test_renderer_copy_still_must_match_recorded_source_pin(self):
        changed=copy.deepcopy(self.manifest);changed['source_pins']['viewer.mjs']['sha256']='f'*64
        with self.assertRaisesRegex(self.new.PreviewError,'frozen source'):self.new.verify_preview(self.reseal(changed))
    def test_source_allowlist_cannot_gain_or_lose_entry(self):
        for action in ('add','remove'):
            changed=copy.deepcopy(self.manifest)
            if action=='add':changed['source_pins']['extra.mjs']=copy.deepcopy(changed['source_pins']['viewer.mjs'])
            else:del changed['source_pins']['viewer.mjs']
            with self.subTest(action=action),self.assertRaisesRegex(self.new.PreviewError,'source allowlist'):
                self.new.verify_preview(self.reseal(changed))
    def test_unknown_creator_hash_size_or_path_is_not_legacy_compatible(self):
        for field,value in [('sha256','b'*64),('bytes',22134),('path',str(self.root/'unknown.py'))]:
            changed=copy.deepcopy(self.manifest);changed['inputs']['backend'][field]=value
            with self.subTest(field=field),self.assertRaises(self.new.PreviewError):self.new.verify_preview(self.reseal(changed))
    def test_unknown_contract_rejected_even_for_known_backend(self):
        changed=copy.deepcopy(self.manifest);changed['contract']='isolated_world_layout_preview_future'
        with self.assertRaisesRegex(self.new.PreviewError,'manifest seal'):self.new.verify_preview(self.reseal(changed))
    def test_live_navigation_preflight_node_and_three_integrity_retained(self):
        for file in (self.engine/'horizontal_navigation.mjs',self.engine/'preflight.mjs',self.node,self.three/'three.module.js',self.three/'three.core.js'):
            with self.subTest(file=file.name):
                original=file.read_bytes();file.write_bytes(original+b'changed')
                with self.assertRaises(self.new.PreviewError):self.verify()
                file.write_bytes(original)
    def test_missing_live_node_three_navigation_and_preflight_rejected(self):
        for file in (self.node,self.three/'three.core.js',self.engine/'horizontal_navigation.mjs',self.engine/'preflight.mjs'):
            with self.subTest(file=file.name):
                original=file.read_bytes();file.unlink()
                with self.assertRaises(self.new.PreviewError):self.verify()
                file.write_bytes(original)
    def test_node_path_substitution_rejected_even_with_same_bytes(self):
        other=self.root/'other-node.exe';other.write_bytes(self.node.read_bytes());changed=copy.deepcopy(self.manifest)
        changed['inputs']['node']=self.new.binding(other)
        with self.assertRaisesRegex(self.new.PreviewError,'Node runtime path'):self.new.verify_preview(self.reseal(changed))
    def test_navigation_source_duplicates_must_still_agree(self):
        changed=copy.deepcopy(self.manifest);changed['inputs']['navigation_source']['sha256']='1'*64
        with self.assertRaisesRegex(self.new.PreviewError,'navigation provenance'):self.new.verify_preview(self.reseal(changed))
    def test_geometry_original_copy_and_research_files_remain_immutable(self):
        for file in (self.geometry,self.path.parent/'geometry.json',self.packet,self.blueprint,self.cache):
            with self.subTest(file=file.name):
                original=file.read_bytes();file.write_bytes(original+b'changed')
                with self.assertRaises(self.new.PreviewError):self.verify()
                file.write_bytes(original)
    def test_resealed_research_input_cannot_bypass_geometry_provenance(self):
        packet=json.loads(self.packet.read_bytes());packet['changed']=True;self.packet.write_bytes(self.new.canonical(packet))
        changed=copy.deepcopy(self.manifest);changed['inputs']['research_packet']=self.new.binding(self.packet)
        with self.assertRaisesRegex(self.new.PreviewError,'Research packet SHA'):self.new.verify_preview(self.reseal(changed))
    def test_resealed_invalid_geometry_still_fails_visible_collision_check(self):
        geometry=json.loads(self.geometry.read_bytes());geometry['colliders'][0]['max'][1]+=1;self.geometry.write_bytes(self.new.canonical(geometry))
        saved=self.path.parent/'geometry.json';saved.write_bytes(self.geometry.read_bytes())
        changed=copy.deepcopy(self.manifest);changed['inputs']['geometry_source']=self.new.binding(self.geometry)
        changed['assets']['/geometry.json']={**self.new.binding(saved),'mime':self.new.ASSETS['geometry.json']}
        with self.assertRaisesRegex(self.new.PreviewError,'does not match'):self.new.verify_preview(self.reseal(changed))
    def test_asset_allowlist_mime_and_path_not_relaxed(self):
        for kind in ('allowlist','mime','path'):
            changed=copy.deepcopy(self.manifest)
            if kind=='allowlist':del changed['assets']['/style.css']
            elif kind=='mime':changed['assets']['/style.css']['mime']='text/plain'
            # Use a live external asset, since reseal intentionally relocates copied assets.
            else:changed['assets']['/three.core.js']['path']=str(self.root/'outside.js')
            with self.subTest(kind=kind),self.assertRaises(self.new.PreviewError):self.new.verify_preview(self.reseal(changed))
    def test_expected_manifest_digest_and_seal_not_relaxed(self):
        changed=copy.deepcopy(self.manifest);changed['preflight']['untrusted']=True;self.path.write_bytes(self.new.canonical(changed))
        with self.assertRaisesRegex(self.new.PreviewError,'Exact preview manifest hash'):self.verify()
        with self.assertRaisesRegex(self.new.PreviewError,'manifest seal'):self.new.verify_preview(self.path)
    def test_new_backend_creates_distinct_preview_and_reuses_exact_revision(self):
        answer=subprocess.CompletedProcess([],0,b'{"status":"PASS","fixture_only":true}',b'')
        with patch.object(self.new.subprocess,'run',return_value=answer):
            created=self.new.create_preview(self.geometry,self.packet,self.blueprint)
            again=self.new.create_preview(self.geometry,self.packet,self.blueprint)
        self.assertNotEqual(created['build_id'],self.saved['build_id']);self.assertTrue(again['reused'])
        self.assertEqual(created['manifest_sha256'],again['manifest_sha256'])
        self.assertEqual(self.path.read_bytes(),self.original)
    def test_current_renderer_update_creates_new_build_without_rewriting_old(self):
        (self.engine/'viewer.mjs').write_bytes((self.engine/'viewer.mjs').read_bytes()+b'\n// new revision\n')
        answer=subprocess.CompletedProcess([],0,b'{"status":"PASS","fixture_only":true}',b'')
        with patch.object(self.new.subprocess,'run',return_value=answer):created=self.new.create_preview(self.geometry,self.packet,self.blueprint)
        self.assertNotEqual(created['build_id'],self.saved['build_id']);self.verify()
        self.assertNotEqual(sha(Path(created['manifest_path']).parent/'viewer.mjs'),sha(self.path.parent/'viewer.mjs'))
    def test_real_unchanged_node_preflight_works_with_candidate_creation(self):
        self.new.NODE=Path(os.environ.get('WORLD_PREVIEW_NODE') or shutil.which('node') or 'node').resolve()
        result=self.new.create_preview(self.geometry,self.packet,self.blueprint)
        manifest=self.new.verify_preview(result['manifest_path'],result['manifest_sha256'])
        self.assertEqual(manifest['preflight']['status'],'PASS');self.assertEqual(len(manifest['preflight']['routes']),3)
    def test_unmodified_geometry_research_and_http_functions(self):
        def functions(p):
            text=p.read_text();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        before=functions(BASELINE);after=functions(CANDIDATE)
        for name in ('read_exact','binding','verify_binding','validate_geometry','source_bindings','create_preview','make_server'):
            self.assertEqual(before[name],after[name],name)

if __name__=='__main__':
    original_hash=sha(ENGINE/'world_layout_preview.py')
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CompatibilityTests))
    assert sha(ENGINE/'world_layout_preview.py')==original_hash
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'output':stream.getvalue(),'candidate_sha256':sha(CANDIDATE),'test_source_sha256':sha(__file__),
        'canonical_backend_unchanged':True,'owner_data_writes':0,'network_model_gpu_browser_calls':0,
        'real_node_preflight_runs':1,'other_preflights':'fake CPU integrity fixtures; no semantic or visual approval'}
    target=H/('PORTABLE-TEST-RESULT-'+str(len(list(H.glob('PORTABLE-TEST-RESULT-*.json')))+1)+'.json');target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='output'}));print(stream.getvalue() if not result.wasSuccessful() else '')
    raise SystemExit(not result.wasSuccessful())
