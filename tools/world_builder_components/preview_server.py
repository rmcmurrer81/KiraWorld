"""Read-only, exact-file inspection of one saved original component."""
from pathlib import Path
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from urllib.parse import urlsplit
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from world_builder_components.component_jobs import verify_component, exact, COMPONENT_ROOT

MAP = '{"imports":{"three":"/three.module.js"}}'
TYPES = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
         '.js': 'text/javascript; charset=utf-8', '.txt': 'text/plain; charset=utf-8', '.glb': 'model/gltf-binary', '.json': 'application/json; charset=utf-8'}


def make_server(path, expected, port=0, *, output_root=COMPONENT_ROOT):
    manifest, manifest_raw = verify_component(path, expected, output_root=output_root)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_HEAD(self):
            self.respond(False)

        def do_GET(self):
            self.respond(True)

        def respond(self, body):
            origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.headers.get_all('Host') != [origin[7:]] or self.headers.get_all('Origin', [origin]) != [origin]:
                self.send_error(403); return
            split = urlsplit(self.path)
            if split.scheme or split.netloc or split.query or split.fragment or '%' in self.path or '\\' in self.path:
                self.send_error(404); return
            name = '/index.html' if self.path == '/' else self.path
            row = manifest['assets'].get(name)
            if row is None:
                self.send_error(404); return
            try:
                if Path(path).read_bytes() != manifest_raw:
                    raise ValueError('Saved manifest changed')
                raw = exact(row)
            except (ValueError, OSError):
                self.send_error(409); return
            self.send_response(200)
            self.send_header('Content-Type', TYPES[Path(name).suffix])
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            digest = base64.b64encode(hashlib.sha256(MAP.encode()).digest()).decode()
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self' 'sha256-" + digest + "'; style-src 'self'; connect-src 'self' blob:; img-src 'self' blob: data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            if body:
                self.wfile.write(raw)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    server = make_server(args.manifest, args.sha256, args.port)
    print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port) + '/', 'manifest': args.manifest}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
