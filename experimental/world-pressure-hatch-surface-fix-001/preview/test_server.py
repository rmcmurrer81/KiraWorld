"""No server construction, thread, socket, browser or renderer in these tests."""
from pathlib import Path
import copy
import hashlib
import json
import tempfile
import unittest
import preview_server as server

class AdmissionTests(unittest.TestCase):
    def admit(self, target='/', method='GET', host=None, origins=None, site=None):
        return server.admit_request(method, target, ['127.0.0.1:54321'] if host is None else host,
                                    [] if origins is None else origins, 54321, site)

    def test_get_and_head_only_exact_known_assets(self):
        for method in ('GET', 'HEAD'):
            self.assertEqual(self.admit(method=method), (200, 'index.html'))
            for name in server.ASSETS:
                self.assertEqual(self.admit('/'+name, method), (200, name))
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'):
            self.assertEqual(self.admit(method=method)[0], 405)

    def test_host_origin_and_cross_site_guard(self):
        for host in ([], ['localhost:54321'], ['127.0.0.1:80'], ['evil.example'], ['127.0.0.1:54321']*2):
            self.assertEqual(self.admit(host=host)[0], 403)
        for origin in (['null'], ['https://example.com'], ['http://127.0.0.1:12345'], ['http://127.0.0.1:54321']*2):
            self.assertEqual(self.admit(origins=origin)[0], 403)
        self.assertEqual(self.admit(origins=['http://127.0.0.1:54321'])[0], 200)
        self.assertEqual(self.admit(site='cross-site')[0], 403)

    def test_no_traversal_queries_remote_urls_or_unlisted_files(self):
        for path in ('/../preview_server.py', '/%2e%2e/secrets', '/geometry.json?x=1', '/geometry.json#x', '/assets/',
                     '/geometry.json/', '/BUNDLE-MANIFEST.json', '/pressure_hatch.mjs/../geometry.json',
                     '//example.com/geometry.json', 'http://127.0.0.1:54321/geometry.json', '/\\geometry.json', 'geometry.json'):
            self.assertNotEqual(self.admit(path)[0], 200, path)

    def test_bound_assets_reject_changed_bytes_and_unsafe_manifest_paths(self):
        with tempfile.TemporaryDirectory(prefix='hatch-review-test-') as temp:
            root = Path(temp)
            (root/'assets').mkdir()
            assets = {}
            for name,mime in server.ASSETS.items():
                data = name.encode()
                (root/'assets'/name).write_bytes(data)
                assets[name] = {'path':name,'mime':mime,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            manifest = {'contract':'isolated_hatch_visual_review_v1','assets':assets,'ownerWorldLoaded':False,'pressureSimulation':False}
            def seal(value):
                data = json.dumps(value).encode()
                (root/'BUNDLE-MANIFEST.json').write_bytes(data)
                return hashlib.sha256(data).hexdigest()
            digest = seal(manifest)
            server.verify_bundle(digest, root)
            with self.assertRaises(ValueError):
                server.verify_bundle('a'*64, root)
            bad = copy.deepcopy(manifest)
            bad['assets']['index.html']['path'] = '../preview_server.py'
            with self.assertRaises(ValueError):
                server.verify_bundle(seal(bad), root)
            digest = seal(manifest)
            (root/'assets'/'geometry.json').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                server.verify_bundle(digest, root)

if __name__ == '__main__':
    unittest.main(verbosity=2)
