"""Saved, replayable original frame construction with optional verified world binding."""
from pathlib import Path
import json
import os
import tempfile

from .bed_frame import build_bed_frame, validate_recipe, glb_bytes, validate_spec, canonical, sha, require
from .component_io import job_lock, preserve_bytes

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
COMPONENT_ROOT = PROJECT / 'Data/world_original_components'
CONTRACT = 'saved_original_frame_component_v1'
CONSTRUCTOR_SHA = 'a616f8fbb5e9d465df00b9d72e599995948236f43c5e0631c36e77ff89ae1eb6'
THREE = PROJECT / 'third_party/three'
VENDOR = {
 'THREE-LICENSE.txt': ('LICENSE', 'bfe119ea4fd413f5f7ca3fcd63adb0c4a073ed39daa2fe7d3e6b769e21272601'),
 'three.module.js': ('build/three.module.js', 'c8211c69345d2e9949dc7a8ac969380497aa0600a5a8ac6a459c8cd02dd9cb8a'),
 'three.core.js': ('build/three.core.js', 'eb077d2417f61d3e6d9264c317cabc4ea35769ed6b0ab533067292a550784c20'),
 'addons/loaders/GLTFLoader.js': ('examples/jsm/loaders/GLTFLoader.js', '67ac5551fdafa6e349bd80c8f8e5e39c136d6b2fb1ad647db9abb21dc86f9e4a'),
 'addons/utils/BufferGeometryUtils.js': ('examples/jsm/utils/BufferGeometryUtils.js', 'fda7e946b8e0b5ab39b779206589e7a1079a22eb24efb89d7223e03fdfb1f751'),
 'addons/controls/OrbitControls.js': ('examples/jsm/controls/OrbitControls.js', 'b97879c748170baadeb3fb84cea1ffdf4674e283dc06042f34e2acb95a76042c')}
SOURCE_NAMES = ('bed_frame.py', 'component_jobs.py', 'component_io.py', 'preview_server.py', 'viewer.mjs', 'index.html', 'style.css')


def no_links(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.exists():
            require(not part.is_symlink() and not getattr(part.lstat(), 'st_file_attributes', 0) & 0x400,
                    'Linked or junction paths are not accepted')
    return path


def pin(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= 128 * 1024 * 1024, 'Missing or oversized bound file')
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def exact(row):
    require(isinstance(row, dict) and set(row) == {'path', 'bytes', 'sha256'}, 'Exact file binding required')
    path = no_links(row['path'])
    require(path.is_file() and path.stat().st_size <= 128 * 1024 * 1024, 'Missing or oversized bound file')
    raw = path.read_bytes()
    require(str(path) == row['path'] and len(raw) == row['bytes'] and sha(raw) == row['sha256'],
            'Bound file changed: ' + str(row.get('path')))
    return raw


def bind_world_job(job_dir):
    """Read-only existing native validator: never dispatches a model or revises a layout."""
    from world_builder_engine.pipeline import latest_preview
    item = latest_preview(job_dir)
    manifest_path = Path(item['manifest_path'])
    manifest = json.loads(manifest_path.read_bytes())
    result = {'preview_manifest': pin(manifest_path), 'research_job': str(Path(job_dir).resolve()),
              'geometry_source': manifest['inputs']['geometry_source'], 'blueprint': manifest['inputs']['blueprint'],
              'research_packet': manifest['inputs']['research_packet'], 'placement_status': 'not_placed'}
    verify_world_binding(result)
    return result


def verify_world_binding(binding):
    if binding is None:
        return
    require(set(binding) == {'preview_manifest', 'research_job', 'geometry_source', 'blueprint', 'research_packet', 'placement_status'},
            'Exact original-world binding required')
    require(binding['placement_status'] == 'not_placed', 'Component preparation cannot claim world placement')
    from world_builder_engine.world_layout_preview import verify_preview
    row = binding['preview_manifest']
    manifest = json.loads(exact(row))
    verify_preview(row['path'], row['sha256'])
    require(manifest['source_mode'] == 'source_bound_original_layout', 'Only verified original worlds may bind a frame')
    for key in ('geometry_source', 'blueprint', 'research_packet'):
        require(binding[key] == manifest['inputs'][key], 'World input binding changed')
        exact(binding[key])
    require(Path(binding['research_packet']['path']).parent == Path(binding['research_job']), 'Research job differs from packet')


def toolchain():
    result = {name: pin(ROOT / name) for name in SOURCE_NAMES}
    require(result['bed_frame.py']['sha256'] == CONSTRUCTOR_SHA, 'Reviewed original constructor changed')
    for name, (relative, expected) in VENDOR.items():
        row = pin(THREE / relative)
        require(row['sha256'] == expected, 'Renderer library changed: ' + name)
        result['vendor_' + name] = row
    return result


def component_definition(recipe, recipe_raw, geometry_raw):
    return {'contract': 'original_world_component_asset_v1', 'component_kind': 'rigid_bed_frame',
            'units': 'metres', 'dimension_basis': 'authored_not_reference_measurement',
            'spec': recipe['spec'], 'recipe_sha256': sha(recipe_raw), 'glb_sha256': sha(geometry_raw),
            'recipe': 'frame.json', 'geometry': 'frame.glb',
            'part_colliders': [{'id': p['id'], 'bounds': p['bounds'], 'shape': 'conservative_axis_aligned_bounds'} for p in recipe['parts']],
            'mattress_interface': recipe['mattress_interface'], 'construction_order': recipe['construction_order'],
            'default_walkable_surface': False, 'downloaded_meshes_or_textures_used': False,
            'model_weight_training': False, 'world_placement': 'not_placed', 'complete_bed': False,
            'limits': ['Rigid frame only; no compliant mattress, cloth or pillow.',
                       'Face-contact joints assume rigid fastening; certified strength is not established.',
                       'Neutral authored finish; photorealism is not established.']}


def planned_assets(spec, world_binding, sources):
    recipe = build_bed_frame(spec)
    checks = validate_recipe(recipe)
    recipe_raw, geometry_raw = canonical(recipe), glb_bytes(recipe)
    entry = {'id': 'frame', 'name': spec['name'], 'glb': '/frame.glb', 'glb_sha256': sha(geometry_raw),
             'recipe': '/frame.json', 'recipe_sha256': sha(recipe_raw), 'checks': checks,
             'triangles': len(recipe['parts']) * 44, 'bytes': len(geometry_raw)}
    request = {'contract': CONTRACT, 'spec': spec, 'world_binding': world_binding,
               'constructor_sha256': CONSTRUCTOR_SHA, 'authored_size': True, 'model_calls': 0}
    data = {'frame.json': recipe_raw, 'frame.glb': geometry_raw,
            'request.json': canonical(request), 'component.json': canonical(component_definition(recipe, recipe_raw, geometry_raw)),
            'frames.json': canonical({'contract': 'original_frame_specimens_v1', 'variants': [entry],
                         'imported_geometry_bytes': 0, 'model_weight_training': False, 'complete_bed': False})}
    for name in ('viewer.mjs', 'index.html', 'style.css'):
        data[name] = exact(sources[name])
    for name in VENDOR:
        data[name] = exact(sources['vendor_' + name])
    return request, data, entry


def save_frame(spec, *, world_job=None, output_root=COMPONENT_ROOT):
    validate_spec(spec)
    world_binding = bind_world_job(world_job) if world_job is not None else None
    sources = toolchain()
    request, data, entry = planned_assets(spec, world_binding, sources)
    ident = 'frame-' + sha(canonical({'request': request, 'sources': sources}))[:24]
    output_root = no_links(output_root)
    require(output_root.name == 'world_original_components', 'Use a dedicated original-components folder')
    folder = output_root / ident
    folder.mkdir(parents=True, exist_ok=True)
    no_links(folder)
    with job_lock(folder):
        for name, raw in data.items():
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            no_links(target)
            preserve_bytes(target, raw)
        for row in sources.values():
            exact(row)
        verify_world_binding(world_binding)
        manifest = {'contract': CONTRACT, 'build_id': ident, 'request': request, 'sources': sources,
                    'assets': {'/' + name: pin(folder / name) for name in data}, 'variant': entry,
                    'status': 'original_frame_ready_for_inspection', 'worlds_modified': False,
                    'model_calls': 0, 'model_weight_training': False, 'downloaded_geometry_imported': False}
        manifest['receipt_sha256'] = sha(canonical(manifest))
        path = folder / 'manifest.json'
        preserve_bytes(path, canonical(manifest))
        result = {'manifest': str(path), 'sha256': sha(path.read_bytes()), 'component_id': ident,
                  'component_file': str(folder / 'component.json'), 'world_bound': world_binding is not None,
                  'status': manifest['status'], 'model_calls': 0, 'world_placement': 'not_placed'}
        verify_component(path, result['sha256'], output_root=output_root)
        return result


def verify_component(path, expected, *, output_root=COMPONENT_ROOT):
    path = no_links(path)
    require(path.name == 'manifest.json' and path.parent.parent == Path(output_root).absolute(), 'Component manifest escaped its saved root')
    raw = path.read_bytes()
    require(sha(raw) == expected, 'Component manifest changed')
    manifest = json.loads(raw)
    require(set(manifest) == {'contract', 'build_id', 'request', 'sources', 'assets', 'variant', 'status', 'worlds_modified', 'model_calls', 'model_weight_training', 'downloaded_geometry_imported', 'receipt_sha256'}, 'Unexpected component manifest fields')
    require(manifest['status'] == 'original_frame_ready_for_inspection' and manifest['worlds_modified'] is False
            and manifest['model_calls'] == 0 and manifest['model_weight_training'] is False
            and manifest['downloaded_geometry_imported'] is False, 'Unsupported component result claim')
    require(manifest.get('contract') == CONTRACT and manifest['build_id'] == path.parent.name, 'Saved component contract changed')
    require(sha(canonical({k: v for k, v in manifest.items() if k != 'receipt_sha256'})) == manifest['receipt_sha256'], 'Component seal changed')
    sources = toolchain()
    require(manifest['sources'] == sources, 'Component toolchain changed; preserve this result and build a new revision')
    request = manifest['request']; verify_world_binding(request['world_binding'])
    rebuilt, data, entry = planned_assets(request['spec'], request['world_binding'], sources)
    require(rebuilt == request and manifest['variant'] == entry, 'Component request or derived metadata changed')
    ident = 'frame-' + sha(canonical({'request': request, 'sources': sources}))[:24]
    require(ident == manifest['build_id'] and set(manifest['assets']) == {'/' + name for name in data}, 'Component identity or asset set changed')
    for name, payload in data.items():
        row = manifest['assets']['/' + name]
        require(Path(row['path']) == path.parent / name and exact(row) == payload, 'Derived component asset changed: ' + name)
    return manifest, raw


def list_components(*, output_root=COMPONENT_ROOT):
    root = no_links(output_root)
    if not root.is_dir():
        return []
    result = []
    for path in sorted(root.glob('frame-*/manifest.json')):
        row = None
        try:
            row = pin(path)
            manifest, _ = verify_component(path, row['sha256'], output_root=root)
            result.append({'manifest': str(path), 'sha256': row['sha256'], 'name': manifest['request']['spec']['name'],
                           'spec': manifest['request']['spec'], 'world_bound': manifest['request']['world_binding'] is not None,
                           'status': 'current', 'hold_reason': None})
        except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
            # Retain an explicit non-actionable row. One historical or invalid
            # manifest must not hide other verified current components.
            result.append({'manifest': str(path), 'sha256': row['sha256'] if row else None,
                           'name': path.parent.name, 'spec': None, 'world_bound': None,
                           'status': 'held', 'hold_reason': str(exc)[:500]})
    return result
