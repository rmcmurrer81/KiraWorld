"""Portable additive public evidence snapshot; no install, owner writes or Git mutation."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;W=H.parents[1];OUT=H/'payload';OUT.mkdir(exist_ok=False)
BASE='c085f491a5329111f1f33ae1b5b45cb681e04422'
D=W/'work/world-working-doors-candidate-024';P=W/'work/world-immutable-preview-candidate-026';R=W/'work/world-habitat-realism-025'
prefixes={'024':'experimental/world-working-doors-024','026':'experimental/world-immutable-preview-026','025':'experimental/world-habitat-realism-025'}
inventory=[]
def sha(data):return hashlib.sha256(data).hexdigest()
def redact(raw):
    text=raw.decode('utf-8-sig')
    for value,alias in ((str(W),'@workspace'),(W.as_posix(),'@workspace'),(str(Path.home()),'@user_home'),(Path.home().as_posix(),'@user_home')):
        text=text.replace(json.dumps(value)[1:-1],alias).replace(value,alias)
    text=re.sub(r'C:[\\/]+Users[\\/]+'+re.escape(Path.home().name),'@user_home',text,flags=re.I)
    return text.encode('utf-8')
def add(group,rel,source=None,data=None,adaptation=None):
    raw=Path(source).read_bytes() if source else data
    payload=redact(raw) if data is None else data
    target=OUT/prefixes[group]/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
    inventory.append({'path':target.relative_to(OUT).as_posix(),'sha256':sha(payload),'bytes':len(payload),
        'source':str(Path(source).relative_to(W).as_posix()) if source and Path(source).is_relative_to(W) else None,
        'original_sha256':sha(raw),'identity_paths_redacted':payload!=raw and adaptation is None,'adaptation':adaptation})
    return target
def require_pin(row):
    data=Path(row['path']).read_bytes();assert sha(data)==row['sha256'] and len(data)==row['bytes']
delivery=json.loads((D/'DELIVERY.json').read_text())
for row in delivery['files']:
    require_pin(row['before']);require_pin(row['after'])
    add('024','baseline/'+Path(row['relative_path']).name,source=row['before']['path'])
    add('024','candidate/'+row['relative_path'],source=row['after']['path'])
add('024','candidate/tools/world_builder_engine/horizontal_navigation.mjs',source=D/'candidate/tools/world_builder_engine/horizontal_navigation.mjs')
for fixture in sorted((D/'fixtures').glob('*.json')):add('024','fixtures/'+fixture.name,source=fixture)
for name in ('DELIVERY.json','README.md','CHANGES.patch','TEST-RESULT.json','TEST-RESULT-002.json','TEST-RESULT-003.json','EXISTING-LAYOUT-DOOR-CHECK.json',
             'test_doors.mjs','make_fixtures.py','check_existing_layout.mjs','finalize_delivery.py'):
    add('024','evidence/'+name,source=D/name)
test=(D/'test_doors.mjs').read_text().replace("'./TEST-RESULT-003.json'","'./PORTABLE-TEST-RESULT.json'")
add('024','test_doors.mjs',source=D/'test_doors.mjs',data=test.encode(),adaptation='Only output path changed to a fresh portable receipt; tests and renderer inputs unchanged.')
add('024','README.md',data=b'''# World024 door experiment recovery

This is an uninstalled four-asset candidate with33 recorded CPU checks and a separate read-only six-portal check against Robert's existing Mars layout. The old room appearance was rejected; neither door visual quality nor finished-world quality is approved. Door states are session-local and use conservative AABB/sweep collision, without pressure simulation.

The five candidate files include four exact proposed frontend assets and their unchanged navigation dependency. Four synthetic fixtures and baseline source are included. From this directory, run `node test_doors.mjs` to create a fresh PORTABLE-TEST-RESULT.json; preserve it before a deliberate repeat. The output filename is the only test adaptation. Historical receipts and original test/setup sources are under evidence/. Local paths in those receipts use @workspace/@user_home and require deliberate relocation; they are not a fresh runnable review plan.

Generated owner-layout copies, preview servers, server receipts and PREVIEW-PLAN owner-file inventory are excluded. Historical DELIVERY.json still references that excluded local visual plan; it is not required for CPU recovery. Do not try to replay a consumed server. World026 is the separate proposed compatibility change needed before current renderer updates can preserve old saved previews. None of this package replaces canonical tools files.
''')
pd=json.loads((P/'DELIVERY.json').read_text());row=pd['files'][0]
raw=Path(row['file']).read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
add('026','candidate/tools/world_builder_engine/world_layout_preview.py',source=row['file'])
add('026','baseline/world_layout_preview.py',source=P/'baseline/world_layout_preview.py')
for name in ('BASELINE.json','CHANGES.patch','DELIVERY.json','README.md','TEST-RESULT-1.json','READONLY-SAVED-PREVIEW-CHECK.json',
             'prepare.py','finalize.py','test_compatibility.py','check_saved_preview_readonly.py'):
    add('026','evidence/'+name,source=P/name)
# Preserve exactly the public-base renderer dependencies used by the tests.
repo=W/'work/kiraworld-shared-recall-publication-001/repo'
dependencies=[]
for name in ('index.html','style.css','viewer.mjs','walk_controller.mjs','horizontal_navigation.mjs','preflight.mjs','world_layout_preview.py'):
    rel='tools/world_builder_engine/'+name
    raw=subprocess.check_output(['git','-C',str(repo),'show',BASE+':'+rel])
    add('026','support/engine/'+name,data=raw)
    dependencies.append({'path':rel,'sha256':sha(raw),'public_base':BASE})
add('026','support/PUBLIC-BASE-DEPENDENCIES.json',data=(json.dumps(dependencies,indent=2)+'\n').encode())
add('026','fixtures/SYNTHETIC-GEOMETRY-FIXTURE.json',source=W/'work/world-blueprint-candidate/SYNTHETIC-GEOMETRY-FIXTURE.json')
test=(P/'test_compatibility.py').read_text()
test=test.replace('import ast,copy,hashlib,importlib.util,io,json,subprocess,sys,tempfile,threading,types,unittest',
                  'import ast,copy,hashlib,importlib.util,io,json,os,shutil,subprocess,sys,tempfile,threading,types,unittest')
test=test.replace("H=Path(__file__).resolve().parent;K=Path('@user_home/Kira')", "H=Path(__file__).resolve().parent")
test=test.replace("ENGINE=K/'tools/world_builder_engine'", "ENGINE=H/'support/engine'")
test=test.replace("GEOMETRY=H.parent/'world-blueprint-candidate/SYNTHETIC-GEOMETRY-FIXTURE.json'", "GEOMETRY=H/'fixtures/SYNTHETIC-GEOMETRY-FIXTURE.json'")
test=test.replace("self.new.NODE=Path('C:/Program Files/nodejs/node.exe')", "self.new.NODE=Path(os.environ.get('WORLD_PREVIEW_NODE') or shutil.which('node') or 'node').resolve()")
test=test.replace("def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()", "def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()\nTEST_TEMP_BASE=Path(tempfile.gettempdir()).resolve()")
test=test.replace("TemporaryDirectory(prefix='preview026-',dir=H)", "TemporaryDirectory(prefix='preview026-',dir=TEST_TEMP_BASE)")
test=test.replace("self.root.is_relative_to(H.resolve())", "self.root.parent==TEST_TEMP_BASE and self.root.name.startswith('preview026-')")
test=test.replace("H/('TEST-RESULT-'", "H/('PORTABLE-TEST-RESULT-'").replace("H.glob('TEST-RESULT-*.json')", "H.glob('PORTABLE-TEST-RESULT-*.json')")
add('026','test_compatibility.py',source=P/'test_compatibility.py',data=test.encode(),
    adaptation='Dependency locations, Node discovery, short disposable OS temp root and fresh result filename changed; original23 behavioral assertions unchanged.')
add('026','README.md',data=b'''# World026 immutable preview compatibility recovery

This isolated, uninstalled candidate allows the four immutable renderer copies in a saved v1 preview to outlive updates to their original engine files. It explicitly recognizes the previously installed creator hash; unknown creator revisions fail closed. Geometry, source research, blueprint/cache files, Node, navigation/preflight and live Three integrity remain enforced. It does not upgrade the old preview's appearance or grant visual approval.

Candidate and baseline backend bytes are exact. Historical23-test results, diff and the read-only saved-Mars compatibility simulation are under evidence/. No owner geometry, original media, model data, current project state or generated preview is included. Setup/check source in evidence/ has historical local paths redacted and is not a ready-to-run owner-project operation.

Run `python -B test_compatibility.py` from this directory with Python3.10+ and Node.js available on PATH, or set WORLD_PREVIEW_NODE to the Node executable. It uses included synthetic geometry and the exact published-base dependencies in support/engine, creates disposable test-only directories under this package, and records a new PORTABLE-TEST-RESULT-N.json. One unchanged real Node preflight runs; all other preflight responses/Node/Three contents are explicit inert integrity fixtures. No model, GPU, browser, live owner state or canonical file is required. Portable changes only relocate fixture/dependency paths, discover Node and separate fresh receipts; historical tests remain distinct.

Installation still requires root review and preserved canonical preimages. This backup adds only experimental repository paths and installs nothing.
''')
add('025','RESEARCH.md',source=R/'RESEARCH.md')
add('025','README.md',data=b'''# World025 reference notes only

RESEARCH.md records primary/reference source inspection for an original Mars-habitat appearance experiment. This snapshot includes no025 implementation: room dressing was still changing and had no frozen delivery/tests when packaged. Referenced photographs, PDF pages and other artwork are not included or redistributed. Source reference links are not endorsements of final physical or visual correctness. No generated world or owner approval is claimed.
''')
for row in inventory:
    text=(OUT/row['path']).read_text(encoding='utf-8-sig')
    assert Path.home().name.lower() not in text.lower(),row['path']
    assert not re.search(r'(?:ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN .*PRIVATE KEY)',text),row['path']
    assert not re.search(r'https?://[^/\s:@]+:[^/\s@]+@',text),row['path']
    if row['path'].endswith('.py'):ast.parse(text)
with (H/'SOURCE-INVENTORY.json').open('x',encoding='utf-8') as f:json.dump({'base_commit':BASE,'files':inventory,'canonical_owner_or_git_mutations':False},f,indent=2);f.write('\n')
print(json.dumps({'status':'PUBLIC_EXPERIMENT_PAYLOAD_PREPARED','files':len(inventory),'model_calls':0,'git_mutations':False}))
