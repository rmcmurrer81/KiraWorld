from pathlib import Path
import ast,hashlib,json,os,re,struct,subprocess

H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
S=W/'world-galley-detail-045';O=W/'w045/p';CLONE=W/'kiraworld-shared-recall-publication-001/repo'
BASE='4d59e8272af89d43d5c1966cba1a464b010a093e';PREFIX='experimental/world-galley-detail-045/'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def put(rel,raw):
    p=O/rel;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(raw)
def scrub(text):
    for p,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
        for old in (str(p).replace('\\','\\\\'),str(p),p.as_posix()):text=text.replace(old,label)
    return text
def binary_check(raw,suffix):
    if suffix=='.glb':
        assert struct.unpack_from('<4sII',raw)==(b'glTF',2,len(raw));length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
        text=raw[20:20+length].decode('utf-8');data=json.loads(text)
        assert scrub(text)==text and not re.search(r'[A-Za-z]:[\\/]|file:/{2}',text)
        assert all('uri' not in x for x in data['buffers'])
        assert all('uri' not in x and x['mimeType']=='image/png' and 'bufferView' in x for x in data['images'])
        return {'kind':'original_derived_glb','embedded_pngs':len(data['images'])}
    assert suffix=='.png' and raw[:8]==b'\x89PNG\r\n\x1a\n'
    return {'kind':'headless_cpu_artifact_png','size':list(struct.unpack_from('>II',raw,16))}

assert not O.exists()
existing=subprocess.run(['git','ls-tree','--name-only',BASE,'--',PREFIX.rstrip('/')],cwd=CLONE,capture_output=True,check=True);assert not existing.stdout
plan=json.loads((S/'INSTALL-PLAN.json').read_bytes())
assert sha((S/'INSTALL-PLAN.json').read_bytes())=='8d5160f30205936e015cf5938cbaa69e0caa68552553e1735b5db2f339a3ae71'
assert (S/'INSTALLED.json').exists()
execution=json.loads((S/'ROOT-EXECUTION.json').read_bytes())
assert execution['status']=='045_GALLEY_INSTALLED_ACTUAL_API_EXPORT_IMPORT_PASS'
canonical=[]
for row in plan['files']:
    rel=row['relative_path'];before=subprocess.run(['git','show',BASE+':'+rel],cwd=CLONE,capture_output=True,check=True).stdout
    assert sha(before)==row['before_sha256']
    assert sha(Path(row['target']).read_bytes())==row['after']['sha256']
    after=Path(row['after']['path']);assert sha(after.read_bytes())==row['after']['sha256']
    canonical.append({'path':rel,'file':str(after),'sha256':row['after']['sha256'],'bytes':after.stat().st_size,'before_sha256':row['before_sha256']})
    put(rel,Path(row['target']).read_bytes())
assert all(sha(Path(p).read_bytes())==v for p,v in plan['protected_inputs'].items())
records=[];binaries=[]
for p in sorted(S.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts:continue
    rel=p.relative_to(S).as_posix()
    # This tree contains a bound private immutable copy of the owner's geometry.
    # Exact context dependencies are already in the pinned public source closure.
    if rel.startswith('runtime_context/'):continue
    raw=p.read_bytes();mode='exact'
    if p.suffix in ('.glb','.png'):
        new=raw;binaries.append({'path':PREFIX+rel,'sha256':sha(raw),'bytes':len(raw),**binary_check(raw,p.suffix)})
    else:
        text=raw.decode('utf-8')
        if rel=='test_preview_contract.py':
            text=text.replace("'@kira_root'","str(H.parents[1])");mode='portable checkout default for mock test'
        if rel=='test_galley.mjs':
            text=text.replace("process.argv[4]||'TEST-RESULT.json'","process.argv[4]||('TEST-RESULT-'+(fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('TEST-RESULT')).length+1)+'.json')");mode='preserve archived geometry receipts'
        if rel=='test_installer.py':
            text=text.replace("H/'INSTALLER-TEST-RESULT.json'","H/('INSTALLER-TEST-PUBLIC-'+str(len(list(H.glob('INSTALLER-TEST*.json'))))+'.json')");mode='preserve archived temporary-fixture receipts'
        text=scrub(text);new=text.encode('utf-8')
        if raw!=new and mode=='exact':mode='local identity paths replaced in historical evidence'
    if rel.startswith(('candidate/','baseline/','preimages/')) or '/package/' in rel:assert raw==new
    put(PREFIX+rel,new);records.append({'path':PREFIX+rel,'original_sha256':sha(raw),'public_sha256':sha(new),'transformation':mode})
put(PREFIX+'build_public_backup.py',scrub(Path(__file__).read_text(encoding='utf-8')).encode('utf-8'))
put(PREFIX+'SOURCE-PROVENANCE.json',(json.dumps(records,indent=2)+'\n').encode())
put(PREFIX+'PUBLIC-BINARY-CHECK.json',(json.dumps({'status':'EXACT_ORIGINAL_DERIVED_OUTPUTS_REVIEWED_FOR_BACKUP','files':binaries,'fonts_native_binaries_raw_owner_geometry_research_memories':False},indent=2)+'\n').encode())
note='''# Installed static galley detail045 backup

Five exact canonical files are installed and mapped in this backup. It preserves
candidate/preimage code, failed first bounds-test history, source pins, tests,
two actual derived GLB packages, one CPU artifact PNG and guarded recovery helpers.
Root viewed the image and accepted a limited static geometric improvement only.
All116 protected originals and the saved-job pointer remain unchanged. The old042
and earlier immutable previews still verify. Repeated installed preview refresh
reuses the new045 build. There is no appliance simulation, native-view or owner
realism claim. The installed export/import passed in1.90seconds at a sampled
762.6MiB family peak; its GLB is byte-identical to the isolated reviewed export.

The preferred image is cpu-review-001/galley-review.png. It uses actual exported
meshes/materials with disclosed review fill lighting and a raised camera, not a
native preview screenshot. The sink is physically recessed; the cold-food and
warming appliances are static original forms. No copyrighted design image,
downloaded asset, font/native binary, private research or raw owner geometry is
bundled. runtime_context is excluded because it contains an immutable source
geometry copy. Its code hashes remain in the historical preview receipt.

Public backup files replace local private path prefixes; original/public hashes
are in SOURCE-PROVENANCE.json. Candidate/preimage and exported package bytes are
exact. Staging/install/export/render helpers are local historical recovery
records; their machine-specific path placeholders must be reviewed before use.
The installer hash argument does not independently authorize installation.
Root separately reviewed and applied the exact five-file plan; INSTALLED.json
and ROOT-EXECUTION.json record installation and subsequent API-only validation.
Preparing this backup performs no additional installation or Git mutation.

Pure Node geometry tests use the bundled MIT-licensed Three source. The temporary
installer tests create their own disposable files. Python mocked appearance-gate
tests require KIRA_TEST_ROOT pointing to the existing code checkout; they do not
export or inspect owner data. Public wrappers preserve historical result files.
The exact current base has the remaining canonical Python import dependencies.

Five canonical mappings include exact before hashes verified against the public
base. Original frozen pre-install receipts remain historical; CURRENT-STATUS.json
records the installed result. Runtime/owner data were not copied into the repo.
'''
put(PREFIX+'PUBLIC-BACKUP.md',note.encode())

checks=[];env={**os.environ,'KIRA_TEST_ROOT':str(K),'PYTHONDONTWRITEBYTECODE':'1'}
for args in (['C:/Program Files/nodejs/node.exe','test_galley.mjs'],['C:/Python314/python.exe','-B','test_preview_contract.py'],['C:/Python314/python.exe','-B','test_installer.py']):
    result=subprocess.run(args,cwd=O/PREFIX,env=env,capture_output=True,timeout=20)
    assert result.returncode==0,(result.stdout.decode(),result.stderr.decode());checks.append({'test':args[-1],'status':'pass','result':json.loads(result.stdout)})
put(PREFIX+'PUBLIC-CLOSURE-CHECK.json',(json.dumps({'status':'RELOCATED_PUBLIC_CPU_TESTS_PASS','checks':checks,'new_real_exports_or_renders':0,'canonical_owner_writes_ui_models_gpu':0},indent=2)+'\n').encode())
files=[]
for p in sorted(O.rglob('*')):
    if not p.is_file():continue
    raw=p.read_bytes()
    if p.suffix in ('.glb','.png'):binary_check(raw,p.suffix)
    else:
        text=raw.decode('utf-8');assert not re.search(r'C:[/\\]+Users[/\\]+robmc',text,re.I)
        if p.suffix=='.py':ast.parse(text)
        if p.suffix=='.json':json.loads(text)
    relative=p.relative_to(O).as_posix();canonical_row=next((r for r in canonical if r['path']==relative),None)
    files.append({'path':relative,'file':str(p),'sha256':sha(raw),'bytes':len(raw),'before_sha256':canonical_row['before_sha256'] if canonical_row else None})
manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-galley-detail-020','reviewed':False,'allowed_prefixes':[PREFIX,*[r['path'] for r in canonical]],
    'message':'Improve authored galley geometry with preserved previews and verified CPU asset review','files':files}
mf=W/'sep22-backups/world-galley-detail-020.manifest.json'
with mf.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
mapping={'status':'INSTALLED_CANONICAL_MAPPINGS_INCLUDED_IN_MANIFEST','base_commit':BASE,'exact_before_hashes_verified':True,'files':canonical}
with (H/'CANONICAL-MAPPINGS.json').open('x',encoding='utf-8') as f:json.dump(mapping,f,indent=2);f.write('\n')
result={'status':'INSTALLED045_PUBLIC_BACKUP_READY','manifest':str(mf),'manifest_sha256':sha(mf.read_bytes()),'base_commit':BASE,'files':len(files),'bytes':sum(r['bytes'] for r in files),
    'canonical_mappings_in_manifest':5,'exact_glbs':2,'exact_pngs':1,'public_cpu_tests_pass':True,'root_static_artifact_accepted':True,'installed':True,'native_ui_owner_approval':False,'git_mutations':0}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
