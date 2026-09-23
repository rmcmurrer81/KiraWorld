"""Close the current source backup gap, with no canonical or Git writes."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import re
import subprocess

H = Path(__file__).resolve().parent
W = H.parents[1]
K = Path.home() / 'Kira'
BASE = '6e33101be637eed21ef68dde3b750dcdef3c2d06'
R = W / 'work/kiraworld-shared-recall-publication-001/repo'
O = H / 'closure-supplement-002'
O.mkdir(exist_ok=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def redact(data):
    text = data.decode('utf-8-sig')
    for value, alias in ((str(W), '@workspace'), (W.as_posix(), '@workspace'),
                         (str(Path.home()), '@user_home'), (Path.home().as_posix(), '@user_home')):
        text = text.replace(json.dumps(value)[1:-1], alias).replace(value, alias)
    text = re.sub(r'C:[\\/]+Users[\\/]+' + re.escape(Path.home().name), '@user_home', text, flags=re.I)
    assert Path.home().name.lower() not in text.lower()
    return text.encode('utf-8')


def git(*args):
    return subprocess.check_output(['git', '-C', str(R), *args])


comparison = json.loads((H / 'PUBLIC-BASE-CLOSURE-LOCATIONS.json').read_text())
prior = json.loads((W / 'work/sep22-backups/world-saved-context-003.manifest.json').read_text())
assert prior['base_commit'] == BASE and prior['reviewed'] is False
already = {row['path'] for row in prior['files']}
selected = [row for row in comparison['different_or_missing'] if row['path'] not in already]
assert len(selected) == 26

# Read prior technical receipts only. Preserve them and report exact digest
# occurrences without presenting an old pass as a new execution.
receipts = []
for folder in ('world-research-integration', 'world-builder-pipeline-candidate',
               'world-reference-images-candidate', 'world-analog-cases-candidate',
               'world-repair-candidate', 'world-portable-native-preview-candidate-015'):
    for name in ('INSTALLED.json', 'DELIVERY.json', 'INSTALL-PLAN.json', 'integration-manifest.json'):
        path = W / 'work' / folder / name
        if path.is_file():
            raw = path.read_bytes()
            receipts.append((path.relative_to(W).as_posix(), sha(raw), json.loads(raw)))


def occurrences(obj, digest, path='$'):
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.extend(occurrences(value, digest, path + '.' + key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found.extend(occurrences(value, digest, path + '[' + str(index) + ']'))
    elif obj == digest:
        found.append(path)
    return found


assessment = []
for row in selected:
    rel = row['path']
    source = K / rel
    original = source.read_bytes()
    assert sha(original) == row['local_sha256']
    redacted_proof = rel == 'tools/world_builder_components/bedding/PHYSICS-TEST-RESULT.json'
    data = redact(original) if redacted_proof else original
    text = data.decode('utf-8-sig')
    # These are owned code/assets and technical proof only, no saved owner jobs.
    assert rel.startswith('tools/') and '/Data/' not in rel
    assert Path.home().name.lower() not in text.lower(), rel
    assert not re.search(r'(?i)(?:api[_-]?key|password|access[_-]?token|secret)\s*[:=]\s*[\"\'][A-Za-z0-9_+/=-]{16,}[\"\']', text), rel
    assert not re.search(r'https?://[^/\s:@]+:[^/\s@]+@', text), rel
    target = O / 'source' / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    check = 'text_asset'
    if source.suffix == '.py':
        ast.parse(text, filename=rel)
        check = 'python_ast_parse'
    elif source.suffix in ('.mjs', '.js'):
        subprocess.run(['C:/Program Files/nodejs/node.exe', '--check', str(target)], check=True, capture_output=True)
        check = 'node_syntax_check'
    elif source.suffix == '.json':
        json.loads(text)
        check = 'json_parse'
    historical = []
    for rp, rh, obj in receipts:
        found = occurrences(obj, row['local_sha256'])
        if found:
            historical.append({'receipt': rp, 'receipt_sha256': rh, 'digest_fields': found})
    assessment.append({'path': rel, 'sha256': sha(data), 'original_sha256': sha(original),
                       'identity_paths_redacted': data != original, 'bytes': len(data),
                       'before_sha256': row['base_sha256'], 'validation': check,
                       'historical_digest_occurrences': historical})
    old = git('ls-tree', BASE, '--', rel).strip()
    before = sha(git('show', BASE + ':' + rel)) if old else None
    assert before == row['base_sha256']
    prior['files'].append({'path': rel, 'file': str(target), 'sha256': sha(data),
                           'bytes': len(data), 'before_sha256': before})
    prior['allowed_prefixes'].append(rel)

summary = {
    'status': 'CURRENT_WORLD_DEPENDENCY_BACKUP_SUPPLEMENT_REVIEWED_NO_GIT_WRITE',
    'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'base_commit': BASE, 'additional_files': assessment,
    'scope': '25 exact current owned code/assets and1 technical proof with identity paths redacted;25 absent and1 stale on public main, plus the already proposed2 installed023 files. No owner jobs, media or memories added by this supplement.',
    'privacy_review': 'The PHYSICS-TEST-RESULT technical proof contained11 local evidence paths; only those are redacted. No local username/path or literal secret assignment pattern or authenticated URL found in the final26 payload files. Technical JSON includes historical numerical results and reviewed public-source identities, not private owner job contents.',
    'prior_receipt_interpretation': 'Digest occurrences are provenance crossreferences only; prior tests were not rerun and historical proof is not new acceptance.',
    'canonical_files_changed': False, 'gpu_model_ui_started': False,
    'closure_total': 67, 'already_exact_on_base': 39, 'actual_canonical_source_changes_in_manifest': 28,
    'native_ui_review': 'ROOT-NATIVE-UI-REVIEW.json validates saved reopening only; world generation/quality remains unfinished.',
}
save(O / 'CLOSURE-SUPPLEMENT-REVIEW.json', summary)
for rel in ('PUBLIC-BASE-CLOSURE-COMPARISON.json', 'PUBLIC-BASE-CLOSURE-LOCATIONS.json', 'complete_public_closure.py'):
    (O / rel).write_bytes(redact((H / rel).read_bytes()))
readme = '''# Current World source closure backup supplement

The original023 publication plan added the two updated workspace/helper files. Comparing the67-file current owned World source closure with public main also found26 existing local dependencies or technical proofs missing or stale. This supplement preserves25 exact current code/asset files and one technical proof with its11 local evidence paths redacted at their normal tools/ paths so a checkout contains the imports used by the installed workspace. It changes no canonical file, saved owner job or physics implementation.

The supplement includes25 paths absent from public main and one older school scheduler replaced by its current local version. Python and JavaScript syntax plus JSON decoding were checked without running models, generation, UI or physics. Historical digest occurrences are recorded as provenance, not a claim that tests have been rerun. No literal secret assignments, authenticated URLs or local identity paths remain in the26 public payload files. The original technical-proof hash is recorded; numerical results and source pins are unchanged by redaction.

World015 physics remains installed. The installed023 saved-reopen controls have callback and native saved-reopen checks; new world construction and finished appearance remain incomplete. The020 performance experiment remains rejected, and021 is limited early visual evidence for uninstalled019. Preserve those distinctions when recovering this work.
'''
(O / 'README.md').write_text(readme, encoding='utf-8', newline='\n')
evidence_prefix = 'experimental/world-saved-context-023/closure-supplement/'
for path in sorted(O.iterdir()):
    if path.is_file():
        data = path.read_bytes()
        assert Path.home().name.lower() not in data.decode('utf-8-sig').lower()
        prior['files'].append({'path': evidence_prefix + path.name, 'file': str(path),
                               'sha256': sha(data), 'bytes': len(data), 'before_sha256': None})
assert len({row['path'] for row in prior['files']}) == len(prior['files'])
prior['receipt_prefix'] = 'world-saved-context-004'
prior['message'] = 'Back up installed World workspace with complete current source dependencies and reviewed experiments'
target_manifest = W / 'work/sep22-backups/world-saved-context-004.manifest.json'
save(target_manifest, prior)
print(json.dumps({'manifest': str(target_manifest), 'sha256': sha(target_manifest.read_bytes()),
                  'files': len(prior['files']), 'additional_source_files': len(selected),
                  'historical_receipt_crossreferences': sum(bool(row['historical_digest_occurrences']) for row in assessment),
                  'reviewed': prior['reviewed'], 'git_mutations': False}, indent=2))
