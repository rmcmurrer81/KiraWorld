"""Pinned read-only hatch inspection. Import/verify never binds a socket."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
ASSETS = {
    'index.html': 'text/html; charset=utf-8',
    'style.css': 'text/css; charset=utf-8',
    'inspection.mjs': 'text/javascript; charset=utf-8',
    'inspection_context.mjs': 'text/javascript; charset=utf-8',
    'pressure_hatch.mjs': 'text/javascript; charset=utf-8',
    'geometry.json': 'application/json; charset=utf-8',
    'three.module.js': 'text/javascript; charset=utf-8',
    'three.core.js': 'text/javascript; charset=utf-8',
}
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read_bound(path, row):
    require(type(row.get('bytes')) is int and 0 <= row['bytes'] <= 12_000_000, 'Invalid asset length')
    require(isinstance(row.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Invalid asset hash')
    data = path.read_bytes()
    require(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Pinned asset changed')
    return data

def verify_bundle(expected_sha256, root=ROOT):
    require(isinstance(expected_sha256, str) and re.fullmatch('[0-9a-f]{64}', expected_sha256), 'Expected manifest hash required')
    raw = (root / 'BUNDLE-MANIFEST.json').read_bytes()
    require(digest(raw) == expected_sha256, 'Bundle manifest changed')
    manifest = json.loads(raw)
    require(manifest.get('contract') == 'isolated_hatch_visual_review_v1', 'Unsupported review bundle')
    require(set(manifest.get('assets', {})) == set(ASSETS), 'Asset allowlist changed')
    for name, mime in ASSETS.items():
        row = manifest['assets'][name]
        require(row.get('path') == name and row.get('mime') == mime, 'Asset path or MIME changed')
        read_bound(root / 'assets' / name, row)
    require(manifest.get('ownerWorldLoaded') is False and manifest.get('pressureSimulation') is False, 'Unexpected review capability')
    return manifest, raw

def admit_request(method, target, hosts, origins, port, fetch_site=None):
    """Exact shared handler admission; pure so it can be tested without a socket."""
    if method not in ('GET', 'HEAD'):
        return 405, None
    origin = 'http://127.0.0.1:' + str(port)
    if hosts != [origin.removeprefix('http://')] or len(origins) > 1 or (origins and origins[0] != origin):
        return 403, None
    if fetch_site == 'cross-site':
        return 403, None
    try:
        parsed = urlsplit(target)
    except ValueError:
        return 404, None
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or '%' in target or '\\' in target:
        return 404, None
    name = 'index.html' if parsed.path == '/' else parsed.path.removeprefix('/')
    if parsed.path != '/' and parsed.path != '/' + name:
        return 404, None
    if name not in ASSETS:
        return 404, None
    return 200, name

def make_server(expected_sha256, port=0):
    """Bind only when explicitly called. Caller owns serve/close lifetime."""
    require(type(port) is int and 0 <= port <= 65535, 'Invalid loopback port')
    manifest, frozen = verify_bundle(expected_sha256)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_HEAD(self):
            self.respond(False)

        def do_GET(self):
            self.respond(True)

        def do_POST(self):
            self.send_error(405)

        do_PUT = do_POST
        do_DELETE = do_POST
        do_PATCH = do_POST
        do_OPTIONS = do_POST

        def respond(self, body):
            code, name = admit_request(self.command, self.path, self.headers.get_all('Host', []),
                                       self.headers.get_all('Origin', []), self.server.server_port,
                                       self.headers.get('Sec-Fetch-Site'))
            if code != 200:
                self.send_error(code)
                return
            try:
                require((ROOT / 'BUNDLE-MANIFEST.json').read_bytes() == frozen, 'Manifest changed during serving')
                row = manifest['assets'][name]
                payload = read_bound(ROOT / 'assets' / name, row)
            except (ValueError, OSError):
                self.send_error(409, 'Pinned review bytes changed')
                return
            self.send_response(200)
            self.send_header('Content-Type', row['mime'])
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', CSP)
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            if body:
                self.wfile.write(payload)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify', 'serve'))
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    if args.mode == 'verify':
        manifest, _ = verify_bundle(args.manifest_sha256)
        print(json.dumps({'status': 'verified', 'assets': len(manifest['assets']), 'serviceStarted': False}))
        return
    server = make_server(args.manifest_sha256, args.port)
    print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port) + '/', 'mode': 'isolated_static_hatch_inspection'}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
