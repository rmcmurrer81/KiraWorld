"""Stage exact, redacted public evidence; no install, render or Git mutation."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

W = Path(__file__).resolve().parents[2]
K = Path.home() / 'Kira'
H = Path(__file__).resolve().parent
BASE = '6e33101be637eed21ef68dde3b750dcdef3c2d06'
REPO = W / 'work/kiraworld-shared-recall-publication-001/repo'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(obj, stream, indent=2)
        stream.write('\n')


def redact(data):
    text = data.decode('utf-8-sig')
    for value, alias in ((str(W), '@workspace'), (W.as_posix(), '@workspace'),
                         (str(Path.home()), '@user_home'), (Path.home().as_posix(), '@user_home')):
        text = text.replace(json.dumps(value)[1:-1], alias).replace(value, alias)
    text = re.sub(r'C:[\\/]+Users[\\/]+' + re.escape(Path.home().name),
                  '@user_home', text, flags=re.I)
    assert Path.home().name.lower() not in text.lower()
    return text.encode('utf-8')


def package(out, inputs, readme, status):
    out.mkdir(exist_ok=False)
    rows = []
    for rel, source in sorted(inputs.items()):
        raw = source.read_bytes()
        data = redact(raw)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        rows.append({'path': rel, 'sha256': sha(data), 'bytes': len(data),
                     'original_sha256': sha(raw), 'identity_paths_redacted': data != raw})
    data = readme.encode('utf-8')
    (out / 'README.md').write_bytes(data)
    rows.append({'path': 'README.md', 'sha256': sha(data), 'bytes': len(data),
                 'original_sha256': None, 'identity_paths_redacted': False})
    save(out / 'BACKUP-MANIFEST.json', {
        'status': status, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'files': sorted(rows, key=lambda row: row['path']),
        'identity_paths_redacted': True, 'owner_data_included': False,
        'instructions': 'Evidence snapshot. Redacted @workspace/@user_home paths require relocation; do not rerun consumed receipts or treat recorded tests as a fresh validation.',
    })
    return out


V = W / 'work/world-disposable-visual-preview-021'
vinputs = {}
for source in V.rglob('*'):
    if source.is_file() and not any(part.startswith('public-') or part == '__pycache__' for part in source.relative_to(V).parts):
        rel = source.relative_to(V).as_posix()
        vinputs['evidence/ORIGINAL-README.md' if rel == 'README.md' else rel] = source
vinputs['evidence/prepare_visual_preview.py'] = W / 'work/world-finite-key-candidate-019/prepare_visual_preview.py'
vout = package(V / 'public-backup-001', vinputs, '''# World019 disposable visual inspection, closed run

The root agent inspected120 actual solver frames in the isolated021 viewer: initial12, settle to60, lift to96 and release to120, with angle and side views. Cloth draped over the sides and responded to lift/release; sampled final views showed no obvious top penetration. The final UI reported0 intersections,0.094m/s speed and2.3% stretch. Broad gridlike waves and simplified material remain engineering limitations. See ROOT-VISUAL-REVIEW.json for the full assessment and its limits.

This is early visual evidence only. It does not approve019 for installation or establish480-frame settling, the0171110-frame trajectory, mattress/head loading, across-frame dragging, general contact or physical ownership guarantees. World015 physics stays installed. Owner approval and native workspace review are not claimed.

The browser closed, viewport reset and read-only loopback server closed at its300-second cap. SERVER-CLOSED.json records unchanged input/assets/owner files. The run is consumed; do not restart the original server or overwrite its receipts. Source assets are included with third-party license files. Local identity paths in historical plans and setup code have been replaced by @workspace/@user_home; this is a recovery/evidence snapshot rather than a ready-to-rerun fresh plan.
''', 'CLOSED_EARLY_VISUAL_INSPECTION_NOT_INSTALL_APPROVAL')

inputs = {}
for rel in ('BASELINE.json', 'CHANGES-FROM-022.patch', 'CHANGES-FROM-INSTALLED.patch',
            'DELIVERY.json', 'INSTALLED.json', 'INSTALLED-CONTEXT-CHECK.json',
            'CURRENT-WORLD-SOURCE-CLOSURE.json', 'TEST-RESULT.json', 'ROOT-NATIVE-UI-REVIEW.json',
            'prepare_candidate.py', 'finalize_delivery.py', 'test_saved_research.py',
            'check_installed_context.py', 'inventory_current_closure.py', 'package_public_delivery.py'):
    inputs[rel] = H / rel
inputs['evidence/PREINSTALL-README.md'] = H / 'README.md'
inputs['evidence/PREINSTALL-BACKUP-MANIFEST.json'] = H / 'public-backup-001/BACKUP-MANIFEST.json'
for directory in ('baseline', 'candidate', 'installed-preimages'):
    for source in (H / directory).rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts:
            inputs[source.relative_to(H).as_posix()] = source
hout = package(H / 'public-backup-002', inputs, '''# Installed World023 saved research and context controls

The canonical World Builder workspace now has a Saved research/layouts selector and Refresh saved control. Reopening existing research restores its context without queueing a research, model or layout job. Selecting another job, or a failed selection, closes stale reference-photo/layout views and rebinds the existing original-components view to the selected job or no job.

Metadata is validated against the expected immediate job directory, schema, canonical-brief digest and identifier. Invalid or ambiguous selections clear stale state; malformed entries remain visible as Needs attention rather than being deleted. The implementation preserves owner research, notebook worlds and original files.

Root installed the two canonical tools files after reviewing022 and023 changes. INSTALLED.json retains the source and previous hashes,20 successful callback tests and two skipped Windows symlink tests. The later INSTALLED-CONTEXT-CHECK.json imports the actual installed files, exercises real callbacks with headless view doubles, and verifies104 owner files unchanged with no model, research, GPU or preview call. Root subsequently opened the installed native workspace, selected the saved Original Mars base and used Open Layout Preview. ROOT-NATIVE-UI-REVIEW.json records the visible Mars Surface Habitat Prototype with Primary Airlock and Main circulation corridor labels, then closure of the owned preview and native window. The saved layout is still an unfinished appearance, not a finished or photorealistic world; new generation was not tested in that session.

CURRENT-WORLD-SOURCE-CLOSURE.json inventories67 current owned source/asset files and53 local import edges. The historical015 receipt and all36 historical installed files remain unchanged, and all56 protected owner frame/study files still match. World015 physics/components remain installed. Experimental019 remains uninstalled;020 was rejected for slower runtime. Nothing here promotes either solver.

Candidate/preinstall receipts are historical and preserved beside the installed receipt. Identity paths in evidence/setup scripts use @workspace/@user_home; they require relocation before deliberate reuse. Do not rerun consumed receipt writers. The two actual canonical tools files are also backed up at their normal repository paths by the exact publication manifest.
''', 'WORLD023_INSTALLED_CALLBACK_AND_SAVED_REOPEN_UI_VERIFIED')


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


closure = json.loads((H / 'CURRENT-WORLD-SOURCE-CLOSURE.json').read_text())
comparison = []
for row in closure['files']:
    rel = row['path']
    old = git('ls-tree', BASE, '--', rel).strip()
    before = sha(git('show', BASE + ':' + rel)) if old else None
    comparison.append({'path': rel, 'local_sha256': row['sha256'], 'base_sha256': before,
                       'matches_base': before == row['sha256']})
save(H / 'PUBLIC-BASE-CLOSURE-COMPARISON.json', {
    'base_commit': BASE, 'files': comparison,
    'matching_files': sum(row['matches_base'] for row in comparison),
    'different_or_missing': [row for row in comparison if not row['matches_base']],
})

packages = [
    ('experimental/world-observation-allocation-020/', W / 'work/world-observation-allocation-candidate-020/portable-backup-001'),
    ('experimental/world-disposable-visual-preview-021/', vout),
    ('experimental/world-saved-research-selector-022/', W / 'work/world-saved-research-selector-candidate-022/public-backup-002'),
    ('experimental/world-saved-context-023/', hout),
]
files = []
for rel in ('tools/world_builder_workspace.py', 'tools/world_saved_research.py'):
    data = (K / rel).read_bytes()
    assert data == (H / 'candidate' / rel).read_bytes()
    old = git('ls-tree', BASE, '--', rel).strip()
    before = sha(git('show', BASE + ':' + rel)) if old else None
    files.append({'path': rel, 'file': str(K / rel), 'sha256': sha(data), 'bytes': len(data), 'before_sha256': before})
for prefix, directory in packages:
    assert not git('ls-tree', '-r', BASE, '--', prefix).strip(), prefix
    manifest = json.loads((directory / 'BACKUP-MANIFEST.json').read_text())
    rows = manifest['files'] + [{'path': 'BACKUP-MANIFEST.json'}]
    for row in rows:
        source = directory / row['path']
        data = source.read_bytes()
        assert Path.home().name.lower() not in data.decode('utf-8-sig').lower(), str(source)
        if 'sha256' in row:
            assert row['sha256'] == sha(data) and row['bytes'] == len(data), str(source)
        files.append({'path': prefix + row['path'], 'file': str(source), 'sha256': sha(data), 'bytes': len(data), 'before_sha256': None})
assert len({row['path'] for row in files}) == len(files)
manifest_path = W / 'work/sep22-backups/world-saved-context-003.manifest.json'
save(manifest_path, {
    'repository': 'rmcmurrer81/KiraWorld', 'clone': str(REPO), 'base_commit': BASE,
    'receipt_prefix': 'world-saved-context-003', 'reviewed': False,
    'allowed_prefixes': ['tools/world_builder_workspace.py', 'tools/world_saved_research.py'] + [prefix for prefix, _ in packages],
    'message': 'Install saved World research context controls and preserve measured experiments and early visual review',
    'files': files,
})
print(json.dumps({'manifest': str(manifest_path), 'sha256': sha(manifest_path.read_bytes()),
                  'files': len(files), 'closure_matches_base': sum(row['matches_base'] for row in comparison),
                  'closure_differences': [row['path'] for row in comparison if not row['matches_base']],
                  'reviewed': False, 'git_mutations': False}, indent=2))
