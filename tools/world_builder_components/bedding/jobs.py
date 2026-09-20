"""Saved engineering studies: exact original frame and tested contact solver."""
import json
from pathlib import Path

from .. import component_jobs as frames
from ..bed_frame import canonical, sha, require, chamfer_box
from ..component_io import job_lock, preserve_bytes

ROOT = Path(__file__).resolve().parent
STUDY_ROOT = frames.PROJECT / 'Data/world_bedding_studies'
CONTRACT = 'original_frame_bedding_study_v1'
ASSET_NAMES = ('index.html', 'style.css', 'viewer.mjs', 'bedding_base.mjs',
               'mattress_physics.mjs', 'surface_contacts.mjs', 'frame_contacts.mjs', 'canvas_recording.mjs')
SOURCE_NAMES = (*ASSET_NAMES, '__init__.py', 'jobs.py', 'preview_server.py',
                'local_recordings.py', 'CONTACT-TEST-RESULT.json')
LIMITS = [
    'Contact smoke checks are not broad dynamic qualification. Release strain and under-mattress false lifts remain unresolved.',
    'Engineering preview; visual contact and fold quality await review. Not a finished or photoreal bed.',
    'Cloth contacts the exact original chamfered frame meshes using discrete triangle/convex contacts; no continuous collision.',
    'Mattress uses a fixed-bottom height field at the verified slat height, not discrete slat-pressure or calibrated foam.',
    'Cloth uses discrete one-way edge/triangle top-surface contact, not continuous or self collision.',
    'No cloth-pillow collision, two-way mattress forces, full-body behavior or world placement.',
]


def toolchain():
    sources = {name: frames.pin(ROOT / name) for name in SOURCE_NAMES}
    sources['component_io.py'] = frames.pin(ROOT.parent / 'component_io.py')
    for name in ('three.module.js', 'three.core.js'):
        relative, expected = frames.VENDOR[name]
        row = frames.pin(frames.THREE / relative)
        require(row['sha256'] == expected, 'Renderer library changed')
        sources[name] = row
    sources['THREE-LICENSE.txt'] = frames.pin(frames.THREE / 'LICENSE')
    report = json.loads(frames.exact(sources['CONTACT-TEST-RESULT.json']))
    require(report['status'] == 'PASS' and report.get('scope') == 'contact_smoke_only', 'Contact solver lacks source-bound contact smoke evidence')
    for key, name in [('base', 'bedding_base.mjs'), ('solver', 'mattress_physics.mjs'), ('contacts', 'surface_contacts.mjs'), ('frame_contacts', 'frame_contacts.mjs')]:
        require(report['source_pins'][key] == sources[name]['sha256'], 'Contact solver differs from tested source')
    return sources


def frame_input(path, expected, frame_root):
    manifest, _ = frames.verify_component(path, expected, output_root=frame_root)
    row = manifest['assets']['/frame.json']
    recipe = json.loads(frames.exact(row))
    interface = recipe['mattress_interface']
    shape = (interface['width'], interface['length'])
    require(shape in ((1.0, 2.0), (1.6, 2.1)),
            'Bedding study supports only 1.00 × 2.00 m or 1.60 × 2.10 m frames; existing frame is unchanged')
    require(abs(interface['base_y'] - .385) < 1e-9, 'Frame support height is incompatible with this study')
    return {'manifest': frames.pin(path), 'recipe': row, 'component_id': manifest['build_id'],
            'size': 'single' if shape == (1.0, 2.0) else 'wide'}, recipe


def planned_assets(binding, recipe, sources):
    data = {name: frames.exact(sources[name]) for name in (*ASSET_NAMES, 'three.module.js', 'three.core.js', 'THREE-LICENSE.txt')}
    # Exactly the same constructor and part dimensions as the original frame GLB.
    parts = [{'id': p['id'], 'position': p['position'], 'mesh': chamfer_box(p['size'], p['bevel'])}
             for p in recipe['parts']]
    data['study.json'] = canonical({'contract': CONTRACT, 'frame_id': binding['component_id'],
        'name': recipe['spec']['name'], 'size': binding['size'], 'interface': recipe['mattress_interface'],
        'parts': parts, 'limits': LIMITS, 'world_placement': 'not_placed', 'visual_acceptance': False})
    return data


def save_study(frame_manifest, expected, *, output_root=STUDY_ROOT, frame_root=frames.COMPONENT_ROOT):
    binding, recipe = frame_input(frame_manifest, expected, frame_root)
    sources = toolchain()
    identity = {'contract': CONTRACT, 'frame': binding, 'sources': sources}
    ident = 'bedding-' + sha(canonical(identity))[:24]
    output_root = frames.no_links(output_root)
    require(output_root.name == 'world_bedding_studies', 'Use a dedicated bedding studies folder')
    folder = output_root / ident
    folder.mkdir(parents=True, exist_ok=True)
    frames.no_links(folder)
    data = planned_assets(binding, recipe, sources)
    with job_lock(folder):
        for name, raw in data.items():
            preserve_bytes(folder / name, raw)
        manifest = {**identity, 'build_id': ident, 'assets': {'/' + name: frames.pin(folder / name) for name in data},
                    'status': 'engineering_study_pending_visual_review', 'worlds_modified': False,
                    'model_calls': 0, 'downloaded_geometry_imported': False, 'limits': LIMITS}
        manifest['receipt_sha256'] = sha(canonical(manifest))
        path = folder / 'manifest.json'
        preserve_bytes(path, canonical(manifest))
        digest = sha(path.read_bytes())
        verify_study(path, digest, output_root=output_root, frame_root=frame_root)
    return {'manifest': str(path), 'sha256': digest, 'component_file': str(folder / 'study.json'),
            'component_id': ident, 'size': binding['size'], 'status': manifest['status']}


def verify_study(path, expected, *, output_root=STUDY_ROOT, frame_root=frames.COMPONENT_ROOT):
    path = frames.no_links(path)
    require(path.name == 'manifest.json' and path.parent.parent == Path(output_root).absolute(), 'Study escaped its saved root')
    raw = path.read_bytes()
    require(sha(raw) == expected, 'Study manifest changed')
    manifest = json.loads(raw)
    require(set(manifest) == {'contract', 'frame', 'sources', 'build_id', 'assets', 'status', 'worlds_modified',
                             'model_calls', 'downloaded_geometry_imported', 'limits', 'receipt_sha256'}, 'Unexpected study fields')
    require(manifest['contract'] == CONTRACT and manifest['status'] == 'engineering_study_pending_visual_review'
            and manifest['worlds_modified'] is False and manifest['model_calls'] == 0
            and manifest['downloaded_geometry_imported'] is False and manifest['limits'] == LIMITS, 'Unsupported study claims')
    require(sha(canonical({k: v for k, v in manifest.items() if k != 'receipt_sha256'})) == manifest['receipt_sha256'], 'Study seal changed')
    bound = manifest['frame']['manifest']
    frames.exact(bound)
    binding, recipe = frame_input(bound['path'], bound['sha256'], frame_root)
    sources = toolchain()
    require(manifest['frame'] == binding and manifest['sources'] == sources, 'Study source changed; preserve this result and create a new revision')
    ident = 'bedding-' + sha(canonical({'contract': CONTRACT, 'frame': binding, 'sources': sources}))[:24]
    require(manifest['build_id'] == path.parent.name == ident, 'Study identity changed')
    data = planned_assets(binding, recipe, sources)
    require(set(manifest['assets']) == {'/' + name for name in data}, 'Unexpected study assets')
    for name, expected_raw in data.items():
        row = manifest['assets']['/' + name]
        require(Path(row['path']) == path.parent / name, 'Study asset escaped its folder')
        require(frames.exact(row) == expected_raw, 'Derived study asset changed')
    return manifest, raw
