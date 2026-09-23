"""Freeze a read-only dependency audit; never modify the installed runtime."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CANONICAL = Path('@user_home/Kira/tools/world_builder_components/bedding')
NAMES = ['bedding_base.mjs', 'frame_contacts.mjs', 'mattress_physics.mjs', 'surface_contacts.mjs']
SOURCE = {'installed015': CANONICAL,
          'predecessor017': WORK / 'world-finite-top-domain-candidate-017/candidate',
          'candidate019': WORK / 'world-finite-key-candidate-019/candidate'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save(name, data):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)

pins = []
texts = {}
for group, source in SOURCE.items():
    names = NAMES + ([] if group == 'installed015' else ['finite_top_domain.mjs'])
    for name in names:
        path = source / name
        data = path.read_bytes()
        save(f'sources/{group}/{name}', data)
        pins.append({'path': str(path), 'snapshot': f'sources/{group}/{name}',
                     'sha256': digest(data), 'bytes': len(data)})
        texts[group, name] = data.decode('utf-8').splitlines()
for name in NAMES:
    assert (CANONICAL / name).read_bytes() == (WORK / 'world-finite-key-candidate-019/baseline' / name).read_bytes()
assert not (CANONICAL / 'finite_top_domain.mjs').exists()
assert all('finiteTopDomain' not in (CANONICAL / name).read_text(encoding='utf-8') for name in NAMES)
assert all(texts['predecessor017', name] == texts['candidate019', name] for name in NAMES)
for a, b in [('installed015', 'candidate019'), ('predecessor017', 'candidate019')]:
    chunks = []
    for name in NAMES + ['finite_top_domain.mjs']:
        chunks.extend(difflib.unified_diff(texts.get((a, name), []), texts.get((b, name), []),
                                         fromfile=f'{a}/{name}', tofile=f'{b}/{name}', lineterm=''))
    save(f'{a}-to-{b}.normalized.patch', ('\n'.join(chunks) + '\n').encode('utf-8'))
fixture = WORK / 'world-frame-contact-perf-candidate/fixtures/wide.json'
data = fixture.read_bytes()
save('fixtures/wide.json', data)
pins.append({'path': str(fixture), 'snapshot': 'fixtures/wide.json', 'sha256': digest(data), 'bytes': len(data)})
historical = WORK / 'world-finite-top-domain-candidate-017/FULL-PILOT-RESULT.json'
data = historical.read_bytes()
save('historical-pilot.json', data)
pins.append({'path': str(historical), 'snapshot': 'historical-pilot.json', 'sha256': digest(data), 'bytes': len(data)})
plan = {'status': 'READ_ONLY_DEPENDENCY_AUDIT', 'sources': pins,
        'canonical_physics_unchanged_from_019_baseline': True,
        'canonical_has_finite_top_domain_module_or_references': False,
        '019_four_existing_modules_equal_017': True,
        'budget': {'one_node_process': True, 'heap_mib': 384, 'wall_seconds': 30, 'gpu': False},
        'installation_proposed': False,
        'limits': 'No physics quality, ownership, general contact or visual approval. This audit does not create a performance candidate for015.'}
save('PLAN.json', (json.dumps(plan, indent=2) + '\n').encode())
print(json.dumps({'snapshots': len(pins), 'output': str(HERE), 'status': plan['status']}))
