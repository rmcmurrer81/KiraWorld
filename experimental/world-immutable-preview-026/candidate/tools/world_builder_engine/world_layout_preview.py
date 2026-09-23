"""Immutable private draft previews and exact loopback files; saved worlds stay unchanged."""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
NAVIGATION = ROOT / 'horizontal_navigation.mjs'
THREE_BUILD = ROOT.parents[1] / 'Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/node_modules/three/build'
NODE = Path('C:/Program Files/nodejs/node.exe')
CONTRACT = 'isolated_world_layout_preview_v1'
# These four files are served from immutable build copies. Their original engine
# files may be upgraded without changing a saved preview's renderer revision.
COPIED_RENDERER_ASSETS = frozenset(('index.html', 'style.css', 'viewer.mjs', 'walk_controller.mjs'))
# Compatibility is explicit per manifest contract and creator revision. A future
# backend must add a reviewed prior revision here; unknown creators fail closed.
COMPATIBLE_CREATOR_BACKENDS = {
    CONTRACT: {'2d5a27e7137011872a0d9645cbfdd96646e592334b44d9d6e800389518604cb9': 22133},
}
ASSETS = {'index.html':'text/html; charset=utf-8', 'style.css':'text/css; charset=utf-8',
          'viewer.mjs':'text/javascript; charset=utf-8', 'walk_controller.mjs':'text/javascript; charset=utf-8',
          'horizontal_navigation.mjs':'text/javascript; charset=utf-8', 'geometry.json':'application/json; charset=utf-8',
          'three.module.js':'text/javascript; charset=utf-8', 'three.core.js':'text/javascript; charset=utf-8'}


class PreviewError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise PreviewError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def read_exact(path, maximum=5_000_000):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if parent.exists():
            stat = parent.lstat()
            require(not parent.is_symlink() and not getattr(stat, 'st_file_attributes', 0) & 0x400,
                    'Preview files cannot follow reparse points: ' + str(parent))
    require(path.is_file() and 0 < path.stat().st_size <= maximum, 'Missing or oversized preview file: ' + str(path))
    data = path.read_bytes()
    require(0 < len(data) <= maximum, 'Preview file changed size')
    return data


def load_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result
    def bad(_):
        raise PreviewError('Nonfinite JSON number')
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique, parse_constant=bad)


def binding(path):
    if Path(path).absolute() == NODE:
        require(NODE.is_file() and 0 < NODE.stat().st_size < 150_000_000 and not NODE.is_symlink(), 'Node runtime unavailable')
        digest = hashlib.sha256()
        with NODE.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024), b''):
                digest.update(chunk)
        return {'path':str(NODE),'bytes':NODE.stat().st_size,'sha256':digest.hexdigest()}
    data = read_exact(path)
    return {'path': str(Path(path).absolute()), 'bytes':len(data), 'sha256':sha(data)}


def verify_binding(row):
    if Path(row['path']) == NODE:
        require(binding(NODE) == row, 'Pinned Node runtime changed')
        return b''
    data = read_exact(row['path'])
    require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'Pinned preview file changed: ' + row['path'])
    return data


def numeric(value):
    require(type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1_000_000, 'Invalid bounded coordinate')


def vector(value):
    require(isinstance(value, list) and len(value) == 3, 'Expected a three-coordinate vector')
    for item in value:
        numeric(item)


def validate_geometry(g):
    require(isinstance(g, dict) and g.get('contract') == 'compiled_blueprint_geometry_v1' and g.get('units') == 'meters', 'Expected compiled layout geometry in meters')
    require(g.get('quality_status') == 'layout_prototype_not_visual_acceptance' and
            all(g.get(k) is False for k in ('photorealism_verified', 'world_ready', 'source_facts_validated')),
            'This viewer accepts unfinished layout prototypes only')
    require(isinstance(g.get('title'), str) and 0 < len(g['title']) <= 200, 'Invalid layout title')
    for field in ('research_packet_sha256', 'blueprint_sha256'):
        require(isinstance(g.get(field), str) and re.fullmatch('[0-9a-f]{64}', g[field]), 'Missing layout provenance')
    for name, maximum in [('rooms', 20), ('primitives', 160), ('colliders', 128), ('support_surfaces', 128), ('routes', 64), ('portals', 64)]:
        require(isinstance(g.get(name), list) and len(g[name]) <= maximum, 'Invalid geometry collection: ' + name)
        ids = set()
        for row in g[name]:
            require(isinstance(row, dict) and isinstance(row.get('id'), str) and re.fullmatch('[A-Za-z0-9_-]{1,120}', row['id']) and row['id'] not in ids, 'Invalid or duplicate geometry id')
            ids.add(row['id'])
    require(g['rooms'] and g['primitives'] and isinstance(g.get('connectivity'), dict), 'Incomplete layout')
    for r in g['rooms']:
        require(isinstance(r.get('name'), str) and 0 < len(r['name']) <= 160, 'Invalid room label')
        for field in ('x', 'z', 'width', 'depth', 'floor_y', 'height'):
            numeric(r.get(field))
        require(r['width'] > 0 and r['depth'] > 0 and r['height'] > 0, 'Nonpositive room dimensions')
        require(r.get('access') in ('walkable_layout', 'closed_locked_solid'), 'Unknown room access')
    solids = {c['id']: c for c in g['colliders']}
    for c in solids.values():
        vector(c.get('min')); vector(c.get('max'))
        require(all(a < b for a, b in zip(c['min'], c['max'])), 'Invalid solid volume')
    visible_solids = set()
    floors = []
    for p in g['primitives']:
        require(p.get('primitive') == 'box' and p.get('role') in ('floor', 'wall', 'ceiling', 'unknown_locked_boundary'), 'Unsupported visual primitive')
        vector(p.get('position')); vector(p.get('size'))
        require(all(v > 0 for v in p['size']), 'Invalid primitive size')
        low = [a-b/2 for a,b in zip(p['position'], p['size'])]
        high = [a+b/2 for a,b in zip(p['position'], p['size'])]
        if p['role'] != 'floor':
            c = solids.get(p['id'])
            require(c and all(abs(a-b) < 1e-7 for a,b in zip(low+high, c['min']+c['max'])), 'Visible solid does not match navigation collider')
            visible_solids.add(p['id'])
        else:
            floors.append((low, high))
    require(visible_solids == set(solids), 'Invisible navigation solid')
    for support in g['support_surfaces']:
        for field in ('min_x', 'max_x', 'min_z', 'max_z', 'y'):
            numeric(support.get(field))
        require(support['min_x'] < support['max_x'] and support['min_z'] < support['max_z'], 'Invalid support surface')
        target = [support['min_x'], support['max_x'], support['min_z'], support['max_z'], support['y']]
        require(any(all(abs(a-b) < 1e-7 for a,b in zip(target, [lo[0],hi[0],lo[2],hi[2],hi[1]])) for lo,hi in floors), 'Walking support has no matching visible floor')
    for r in g['routes']:
        require(r.get('avatar_radius') == .34 and r.get('avatar_height') == 1.68 and isinstance(r.get('points'), list) and 2 <= len(r['points']) <= 320, 'Unsupported route avatar or points')
        for p in r['points']:
            vector(p)
    entry = next((r for r in g['rooms'] if r['id'] == g['connectivity'].get('entry_room_id')), None)
    require(entry and entry['access'] == 'walkable_layout', 'No supported walkable entry room')
    room_map = {r['id']:r for r in g['rooms']}
    walkable = {r['id'] for r in g['rooms'] if r['access'] == 'walkable_layout'}
    locked = set(room_map)-walkable
    support_map = {s['id']:s for s in g['support_surfaces']}
    require(set(support_map) == {rid+'_floor' for rid in walkable}, 'Locked or unknown room retains a walking floor')
    primitive_map = {p['id']:p for p in g['primitives']}
    for rid,r in room_map.items():
        if rid in locked:
            solid = solids.get(rid+'_unknown')
            mesh = primitive_map.get(rid+'_unknown')
            expected = [r['x'],r['floor_y'],r['z'],r['x']+r['width'],r['floor_y']+r['height'],r['z']+r['depth']]
            require(solid and mesh and mesh['role'] == 'unknown_locked_boundary' and
                    all(abs(a-b)<1e-7 for a,b in zip(expected,solid['min']+solid['max'])), 'Locked room lacks its full solid boundary')
            require(rid+'_floor_mesh' not in primitive_map, 'Locked room retains a visible floor')
        else:
            s = support_map[rid+'_floor']
            expected = [r['x'],r['x']+r['width'],r['z'],r['z']+r['depth'],r['floor_y']]
            require(all(abs(a-b)<1e-7 for a,b in zip(expected,[s[k] for k in ('min_x','max_x','min_z','max_z','y')])), 'Room support changed bounds')
    graph = {rid:set() for rid in walkable}; open_ids=set()
    for p in g['portals']:
        a,b = p.get('room_a'),p.get('room_b')
        require(a in room_map and b in room_map and a != b, 'Portal references invalid rooms')
        if a in locked or b in locked:
            require(p.get('state') == 'closed_locked_solid', 'Locked room retains an open passage')
        else:
            require(p.get('state') == 'open_passage', 'Unknown walkable passage state')
            graph[a].add(b);graph[b].add(a);open_ids.add(p['id'])
    require({r['id'] for r in g['routes']} == open_ids, 'Routes disagree with open passages')
    reached=set();pending=[entry['id']]
    while pending:
        rid=pending.pop()
        if rid not in reached:
            reached.add(rid);pending.extend(graph[rid]-reached)
    require(reached == walkable and g['connectivity'].get('reachable_rooms') == sorted(reached) and
            g['connectivity'].get('locked_rooms') == sorted(locked) and g['connectivity'].get('bidirectional_graph') is True,
            'Saved connectivity does not match accessible rooms')


def source_bindings(geometry, research_packet_path, blueprint_path):
    require((research_packet_path is None) == (blueprint_path is None), 'Research packet and blueprint must be supplied together')
    if research_packet_path is None:
        require('analog_comparison' not in geometry, 'Model-produced layout requires both source provenance files')
        return 'synthetic_fixture', {}
    packet_path, blueprint_path = Path(research_packet_path).absolute(),Path(blueprint_path).absolute()
    packet_raw=read_exact(packet_path); packet=load_json(packet_raw)
    blueprint_raw=read_exact(blueprint_path); blueprint=load_json(blueprint_raw)
    require(sha(packet_raw) == geometry['research_packet_sha256'], 'Research packet SHA differs from compiled geometry')
    require(sha(canonical(blueprint)) == geometry['blueprint_sha256'], 'Canonical blueprint SHA differs from compiled geometry')
    require(isinstance(blueprint,dict) and blueprint.get('research_packet_sha256') == geometry['research_packet_sha256'], 'Blueprint research binding differs')
    require(isinstance(packet,dict) and packet.get('packet_kind') == 'world_public_text_research_packet' and
            packet.get('research_mode') == 'analog_to_original', 'This source-bound preview requires original-layout analog research')
    sources=packet.get('sources');require(isinstance(sources,list) and len(sources)<=8, 'Invalid research source collection')
    pins={'research_packet':binding(packet_path),'blueprint':binding(blueprint_path)}
    for index,source in enumerate(sources):
        require(isinstance(source,dict), 'Invalid research source')
        if source.get('state') != 'retrieved_text':continue
        for key in ('content_binding','text_binding','capture_binding'):
            row=source.get(key)
            if key == 'capture_binding' and row is None:continue
            require(isinstance(row,dict) and isinstance(row.get('path'),str), 'Research cache binding missing')
            relative=row['path']
            require('\\' not in relative and ':' not in relative and not relative.startswith('/') and
                    all(part not in ('','.','..') for part in relative.split('/')), 'Research cache escaped the packet folder')
            path=packet_path.parent.joinpath(*relative.split('/'))
            pin=binding(path)
            require(all(pin[k] == row.get(k) for k in ('bytes','sha256')), 'Research cache bytes changed')
            pins['research_cache_'+str(index)+'_'+key]=pin
    return 'source_bound_original_layout',pins


def validate_recorded_binding(row, expected_path):
    require(isinstance(row, dict) and set(row) == {'path', 'bytes', 'sha256'} and
            isinstance(row.get('path'), str) and Path(row['path']) == Path(expected_path) and
            type(row.get('bytes')) is int and 0 < row['bytes'] <= 5_000_000 and
            isinstance(row.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', row['sha256']),
            'Invalid recorded preview source binding')


def verify_creator(manifest):
    row = manifest['inputs']['backend']
    validate_recorded_binding(row, Path(__file__).absolute())
    current = binding(__file__)
    compatible = COMPATIBLE_CREATOR_BACKENDS.get(manifest.get('contract'), {})
    require(row == current or compatible.get(row['sha256']) == row['bytes'],
            'Unsupported preview creator revision')


def verify_source(manifest):
    verify_creator(manifest)
    require(set(manifest['source_pins']) == set(ASSETS)-{'geometry.json'}, 'Preview source allowlist changed')
    require(Path(manifest['inputs']['node']['path']) == NODE, 'Pinned Node runtime path changed')
    require(Path(manifest['inputs']['preflight']['path']) == ROOT/'preflight.mjs', 'Preview preflight path changed')
    require(manifest['inputs']['navigation_source'] == manifest['source_pins']['horizontal_navigation.mjs'],
            'Preview navigation provenance changed')
    for name, row in manifest['inputs'].items():
        if name != 'backend':
            verify_binding(row)
    for name, row in manifest['source_pins'].items():
        expected = THREE_BUILD/name if name.startswith('three.') else ROOT/name
        validate_recorded_binding(row, expected)
        if name not in COPIED_RENDERER_ASSETS:
            verify_binding(row)
    geometry=load_json(verify_binding(manifest['inputs']['geometry_source']))
    research=manifest['inputs'].get('research_packet');blueprint=manifest['inputs'].get('blueprint')
    mode,pins=source_bindings(geometry,research['path'] if research else None,blueprint['path'] if blueprint else None)
    require(mode == manifest.get('source_mode'), 'Preview source mode changed')
    saved={k:v for k,v in manifest['inputs'].items() if k in ('research_packet','blueprint') or k.startswith('research_cache_')}
    require(saved == pins, 'Frozen research provenance changed')


def create_preview(geometry_path, research_packet_path=None, blueprint_path=None):
    """Create a private draft in Data/world_layout_previews; never overwrite a build."""
    geometry_path = Path(geometry_path).absolute()
    raw = read_exact(geometry_path, 2_000_000)
    geometry = load_json(raw)
    validate_geometry(geometry)
    source_mode,provenance = source_bindings(geometry,research_packet_path,blueprint_path)
    inputs = {'geometry_source': binding(geometry_path), 'navigation_source': binding(NAVIGATION),
              'backend': binding(__file__), 'preflight': binding(ROOT/'preflight.mjs'),
              'node': binding(NODE),**provenance}
    sources = {name:ROOT/name for name in ('index.html','style.css','viewer.mjs','walk_controller.mjs')}
    sources['horizontal_navigation.mjs'] = NAVIGATION
    sources['three.module.js'] = THREE_BUILD/'three.module.js'
    sources['three.core.js'] = THREE_BUILD/'three.core.js'
    source_pins = {name:binding(path) for name,path in sources.items()}
    preflight = subprocess.run([str(NODE),str(ROOT/'preflight.mjs'),str(geometry_path),str(NAVIGATION)],
                              capture_output=True, timeout=20, check=False)
    require(preflight.returncode == 0, 'Navigation preflight failed: ' + preflight.stderr.decode('utf-8', errors='replace')[:1800])
    evidence = load_json(preflight.stdout)
    require(evidence.get('status') == 'PASS', 'Navigation preflight did not pass')
    for row in [*inputs.values(), *source_pins.values()]:
        verify_binding(row)
    build_id = 'layout-' + sha(canonical({'inputs':inputs,'sources':source_pins}))[:24]
    build_dir = ROOT.parents[1]/'Data'/'world_layout_previews'/build_id
    manifest_path = build_dir/'manifest.json'
    if build_dir.exists():
        manifest = verify_preview(manifest_path)
        return {'manifest_path':str(manifest_path),'build_id':build_id,'reused':True,'manifest_sha256':sha(read_exact(manifest_path))}
    build_dir.mkdir(parents=True)
    assets = {}
    for name,source in sources.items():
        if name.startswith('three.'):
            assets['/'+name] = {**source_pins[name],'mime':ASSETS[name]}
        else:
            target = build_dir/name
            with target.open('xb') as output:
                output.write(verify_binding(source_pins[name]))
            assets['/'+name] = {**binding(target),'mime':ASSETS[name]}
    with (build_dir/'geometry.json').open('xb') as output:
        output.write(raw)
    assets['/geometry.json'] = {**binding(build_dir/'geometry.json'),'mime':ASSETS['geometry.json']}
    manifest = {'contract':CONTRACT,'build_id':build_id,'status':'layout_prototype_not_visual_acceptance','source_mode':source_mode,
                'inputs':inputs,'source_pins':source_pins,'assets':assets,'preflight':evidence,
                'draft_preview_artifacts_created':True,'resident_worlds_modified':False,'owner_originals_modified':False,
                'model_jobs':0,'network_fetches':0,
                'limitations':['Horizontal supported walking only; no stairs, fly mode or teleport.',
                               'Simple layout materials and lighting; appearance is unfinished.',
                               'Open passages are not moving or pressure-controlled doors.']}
    manifest['receipt_sha256'] = sha(canonical(manifest))
    with manifest_path.open('xb') as output:
        output.write(json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    verify_preview(manifest_path)
    return {'manifest_path':str(manifest_path),'build_id':build_id,'reused':False,'manifest_sha256':sha(read_exact(manifest_path))}


def verify_preview(manifest_path, expected_manifest_sha256=None):
    path = Path(manifest_path).absolute()
    require(path.parent.parent == ROOT.parents[1]/'Data'/'world_layout_previews' and path.name == 'manifest.json', 'Serve only an isolated candidate build')
    raw = read_exact(path)
    if expected_manifest_sha256 is not None:
        require(sha(raw) == expected_manifest_sha256, 'Exact preview manifest hash changed')
    manifest = load_json(raw)
    body = {k:v for k,v in manifest.items() if k != 'receipt_sha256'}
    require(manifest.get('contract') == CONTRACT and manifest.get('build_id') == path.parent.name and sha(canonical(body)) == manifest.get('receipt_sha256'), 'Preview manifest seal changed')
    expected_id = 'layout-' + sha(canonical({'inputs':manifest['inputs'],'sources':manifest['source_pins']}))[:24]
    require(manifest['build_id'] == expected_id, 'Preview input binding changed')
    require(set(manifest.get('assets', {})) == {'/'+name for name in ASSETS}, 'Preview file allowlist changed')
    verify_source(manifest)
    for url,row in manifest['assets'].items():
        expected = THREE_BUILD/url[1:] if url.startswith('/three.') else path.parent/url[1:]
        require(Path(row['path']) == expected and row.get('mime') == ASSETS[url[1:]], 'Preview asset path changed')
        source_pin = manifest['inputs']['geometry_source'] if url == '/geometry.json' else manifest['source_pins'][url[1:]]
        require(all(row[k] == source_pin[k] for k in ('bytes','sha256')), 'Preview asset no longer matches its frozen source')
        verify_binding(row)
    validate_geometry(load_json(verify_binding(manifest['assets']['/geometry.json'])))
    return manifest


def make_server(manifest_path, port=0, expected_manifest_sha256=None):
    """Return an unstarted loopback HTTP server; caller owns lifetime and close."""
    manifest = verify_preview(manifest_path, expected_manifest_sha256)
    manifest_bytes = read_exact(manifest_path)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_HEAD(self):
            self.respond(False)

        def do_GET(self):
            self.respond(True)

        def respond(self, send_body):
            origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.headers.get('Host') != origin.removeprefix('http://') or self.headers.get('Origin', origin) != origin:
                self.send_error(403); return
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or '%' in self.path or '\\' in self.path:
                self.send_error(404); return
            name = '/index.html' if parsed.path == '/' else parsed.path
            row = manifest['assets'].get(name)
            if row is None:
                self.send_error(404); return
            try:
                require(read_exact(manifest_path) == manifest_bytes, 'Manifest changed during serving')
                payload = verify_binding(row)
            except (ValueError, OSError):
                self.send_error(409, 'Pinned preview bytes changed'); return
            self.send_response(200)
            self.send_header('Content-Type',row['mime']); self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header('Referrer-Policy','no-referrer'); self.end_headers()
            if send_body:
                self.wfile.write(payload)
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    build = sub.add_parser('build'); build.add_argument('--geometry', required=True)
    build.add_argument('--research-packet');build.add_argument('--blueprint')
    verify = sub.add_parser('verify'); verify.add_argument('--manifest', required=True); verify.add_argument('--manifest-sha256')
    serve = sub.add_parser('serve'); serve.add_argument('--manifest', required=True); serve.add_argument('--port', type=int, default=0)
    serve.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    if args.mode == 'build':
        print(json.dumps(create_preview(args.geometry,args.research_packet,args.blueprint), indent=2))
    elif args.mode == 'verify':
        result = verify_preview(args.manifest, args.manifest_sha256)
        print(json.dumps({'status':'PASS','build_id':result['build_id'],'assets':len(result['assets'])}))
    else:
        server = make_server(args.manifest, args.port, args.manifest_sha256)
        print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port)+'/','manifest_path':args.manifest}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
