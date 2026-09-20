"""Disposable exact frame/bedding save and loopback serving; no UI, GPU or solver steps."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile,threading,time,unittest,urllib.request,urllib.error
H=Path(__file__).resolve().parent;SOURCE=H.parent;T=tempfile.TemporaryDirectory(prefix='world-portable-')
ROOT=Path(T.name)/'checkout'
for relative in ['tools/world_builder_components','third_party/three']:
    shutil.copytree(SOURCE/relative,ROOT/relative)
sys.path.insert(0,str(ROOT/'tools'))
from world_builder_components import component_jobs as frames
from world_builder_components import preview_server as frame_server
from world_builder_components import component_io
from world_builder_components.bedding import jobs,preview_server as study_server
from world_builder_components.workspace_adapter import OriginalComponentsView

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(server,path,headers=None):
    base='http://127.0.0.1:'+str(server.server_port)
    request=urllib.request.Request(base+path,headers=headers or {})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=3) as response:return response.status,response.read(),dict(response.headers)
class Portable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame=frames.save_frame({'name':'Portable engineering fixture','mattress_width':1.0,'mattress_length':2.0,'slat_max_gap':.07})
        cls.study=jobs.save_study(cls.frame['manifest'],cls.frame['sha256'])
    def serve(self,server):
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(3)))
        return server
    def test_relocated_native_import_and_paths_need_no_resident_modules(self):
        self.assertTrue(issubclass(OriginalComponentsView,__import__('tkinter').Toplevel))
        self.assertEqual(frames.PROJECT,ROOT);self.assertEqual(frames.THREE,ROOT/'third_party/three')
        self.assertNotIn('world_research',sys.modules);self.assertNotIn('adaptive_source_selection',sys.modules)
        self.assertEqual(frames.CONSTRUCTOR_SHA,sha(ROOT/'tools/world_builder_components/bed_frame.py'))
    def test_build_reuse_and_exact_original_bedding_sources(self):
        second=frames.save_frame({'name':'Portable engineering fixture','mattress_width':1.0,'mattress_length':2.0,'slat_max_gap':.07})
        self.assertEqual(second,self.frame);self.assertEqual(jobs.save_study(second['manifest'],second['sha256']),self.study)
        m,_=jobs.verify_study(self.study['manifest'],self.study['sha256'])
        self.assertFalse(m['worlds_modified']);self.assertEqual(m['model_calls'],0)
        for n in ['bedding_base.mjs','mattress_physics.mjs','frame_contacts.mjs','surface_contacts.mjs']:
            self.assertEqual(m['sources'][n]['sha256'],sha(SOURCE/'tools/world_builder_components/bedding'/n))
    def test_frame_exact_assets_and_license_served(self):
        server=self.serve(frame_server.make_server(self.frame['manifest'],self.frame['sha256']))
        for name in ['/','/frame.glb','/three.module.js','/three.core.js','/addons/loaders/GLTFLoader.js','/THREE-LICENSE.txt']:
            status,body,headers=get(server,name);self.assertEqual(status,200);self.assertTrue(body);self.assertIn('Content-Security-Policy',headers)
        self.assertIn(b'MIT',get(server,'/THREE-LICENSE.txt')[1])
    def test_bedding_exact_assets_and_origin_path_guards(self):
        server=self.serve(study_server.make_server(self.study['manifest'],self.study['sha256']))
        manifest=json.loads(Path(self.study['manifest']).read_bytes())
        for name in ['/','/study.json','/mattress_physics.mjs','/three.module.js','/THREE-LICENSE.txt']:
            status,body,_=get(server,name);row=manifest['assets']['/index.html' if name=='/' else name]
            self.assertEqual(status,200);self.assertEqual(hashlib.sha256(body).hexdigest(),row['sha256'])
        for path,headers,code in [('/study.json',{'Origin':'http://foreign.invalid'},403),('/%2e%2e/private',{},404),('/study.json?x=1',{},404)]:
            with self.assertRaises(urllib.error.HTTPError) as e:get(server,path,headers)
            self.assertEqual(e.exception.code,code)
    def test_missing_or_modified_vendor_holds_before_build(self):
        path=frames.THREE/'build/three.core.js';raw=path.read_bytes();moved=path.with_suffix('.saved')
        path.rename(moved)
        try:
            with self.assertRaises(ValueError):frames.toolchain()
        finally:moved.rename(path)
        path.write_bytes(raw+b'\n')
        try:
            with self.assertRaises(ValueError):frames.toolchain()
        finally:path.write_bytes(raw)
    def test_saved_asset_tamper_is_rejected(self):
        p=Path(self.study['manifest']).parent/'study.json';raw=p.read_bytes();p.write_bytes(raw+b'\n')
        try:
            with self.assertRaises(ValueError):jobs.verify_study(self.study['manifest'],self.study['sha256'])
        finally:p.write_bytes(raw)
    def test_local_persistence_and_lock_preserve_existing_bytes(self):
        folder=ROOT/'lock-test';folder.mkdir();p=folder/'artifact'
        with component_io.job_lock(folder):
            component_io.preserve_bytes(p,b'one');component_io.preserve_bytes(p,b'one')
            with self.assertRaises(component_io.ComponentIOError):component_io.preserve_bytes(p,b'two')
            with self.assertRaises(component_io.ComponentIOError):
                with component_io.job_lock(folder):pass
        self.assertEqual(p.read_bytes(),b'one')
    def test_smoke_qualification_is_scoped_and_source_bound(self):
        p=ROOT/'tools/world_builder_components/bedding/CONTACT-TEST-RESULT.json';raw=p.read_bytes();report=json.loads(raw)
        self.assertEqual(report['scope'],'contact_smoke_only');self.assertEqual(len(report['checks']),13)
        report['source_pins']['solver']='0'*64;p.write_text(json.dumps(report))
        try:
            with self.assertRaises(ValueError):jobs.toolchain()
        finally:p.write_bytes(raw)
    def test_held_history_does_not_hide_current_frames(self):
        bad=frames.COMPONENT_ROOT/'frame-historical-invalid';bad.mkdir()
        manifest=bad/'manifest.json';manifest.write_bytes(b'{invalid')
        try:
            rows=frames.list_components()
            self.assertTrue(any(r['status']=='current' for r in rows))
            held=[r for r in rows if r['status']=='held']
            self.assertEqual(len(held),1);self.assertIsNone(held[0]['spec']);self.assertTrue(held[0]['hold_reason'])
            self.assertEqual(manifest.read_bytes(),b'{invalid')
        finally:manifest.unlink();bad.rmdir()
if __name__=='__main__':
    started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Portable))
    out={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'seconds':time.monotonic()-started,'errors':[(str(t),e) for t,e in result.errors+result.failures],
         'scope':'Relocated disposable native imports, source-bound build/reuse and exact loopback serving; no Tk window/browser, model/GPU, solver step or dynamic run.',
         'test_sha256':sha(Path(__file__)),'canonical_or_owner_writes':False}
    print(json.dumps(out))
    T.cleanup();raise SystemExit(not result.wasSuccessful())
