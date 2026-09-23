"""Stage exact public057 evidence and a sanitized current checkpoint; never commit."""
from pathlib import Path
import ast, hashlib, json, re, subprocess, sys
H=Path(__file__).resolve().parent; W=H.parent; K=Path('@kira_root')
S=W/'world-installed-observation-export-057'; A=W/'world-installed-observation-export-057-independent-review-001'
O=Path('@user_home/.codex/world057-public027-stage')
BASE='31643796a39ef591337fae5225feba0bcd2bdf79'; CLONE=W/'kiraworld-shared-recall-publication-001/repo'
P='experimental/world-installed-observation-export-057/'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
load=lambda p:json.loads(p.read_bytes())
dump=lambda x:(json.dumps(x,indent=2)+'\n').encode()
def scrub(text):
    for path,label in ((W.parent,'@workspace'),(K,'@kira_root'),(Path.home(),'@user_home')):
        for old in (str(path).replace('\\','\\\\\\\\'),str(path).replace('\\','\\\\'),str(path),path.as_posix()):text=text.replace(old,label)
    return text
def put(rel,raw):
    target=O/rel; target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
def git_read(path):
    return subprocess.run(['git','show',BASE+':'+path],cwd=CLONE,check=True,capture_output=True).stdout
def main():
    assert not O.exists()
    records=[]; frozen=load(S/'FROZEN-MANIFEST.json')
    assert sha((S/'DELIVERY.json').read_bytes())=='e38f05fe0249f008c3c7b012c831ef33ca18a2c1baa86180912a5a5678f7ad66'
    for rel,row in frozen['files'].items():
        raw=(S/rel).read_bytes(); assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    def capture(source,rel,exact=False):
        raw=source.read_bytes(); public=raw if exact else scrub(raw.decode('utf-8')).encode()
        put(rel,public); records.append({'path':rel,'original_sha256':sha(raw),'public_sha256':sha(public),
            'transformation':'exact' if raw==public else 'identity paths redacted; original digest retained'})
    for rel in [*frozen['files'],'FROZEN-MANIFEST.json','DELIVERY.json','BACKUP-PLAN.json']:
        capture(S/rel,P+rel,exact=rel.startswith('actual-001/package/'))
    review=load(A/'REVIEW.json'); assert review['status']=='INDEPENDENT057_SOURCE_PACKAGE_REVIEW_PASS'
    for rel in ('check_package.py','review.py','REVIEW.json'):capture(A/rel,P+'independent-review-001/'+rel)
    closure=load(S/'INSTALLED-SOURCE-CLOSURE.json'); rows=[]
    for rel,row in closure.items():
        assert sha(git_read(rel))==row['sha256'] and sha((K/rel).read_bytes())==row['sha256']
        rows.append({'repository_path':rel,'commit':BASE,**row})
    deps=[]
    for rawpath,row in load(S/'DEPENDENCIES.json')['external_reference_files'].items():
        path=Path(rawpath); assert sha(path.read_bytes())==row['sha256']
        rel='experimental/'+path.relative_to(W).as_posix(); prior=git_read(rel)
        assert prior==scrub(path.read_text(encoding='utf-8')).encode() or prior==scrub(path.read_bytes().decode()).encode()
        deps.append({'repository_path':rel,'commit':BASE,'public_sha256':sha(prior),'original_local_sha256':row['sha256']})
    prior='experimental/world-observation-setting-054/actual-001/package/'
    previous=[]
    for name in ('scene.glb','scene.json','manifest.json','ROUNDTRIP.json','README.txt'):
        raw=git_read(prior+name); assert raw==(W/'world-observation-setting-054/actual-001/package'/name).read_bytes()
        previous.append({'repository_path':prior+name,'commit':BASE,'sha256':sha(raw),'bytes':len(raw)})
    put(P+'RECOVERY-MAP.json',dump({'status':'EXACT_EXISTING_PUBLIC_SOURCE_CLOSURE_NO_PROMOTION','installed_release':'056',
        'source_files':rows,'external_receipts':deps,'comparison_package':previous,
        'private_source_dependencies':'Original world geometry, research and raw brief are excluded. Operational reproduction needs owner local inputs; the package checker does not.',
        'external_native_dependencies':'Exact Node, canvas and fonts are pinned by producer source; native binaries are not bundled.'}))
    checkpoint=W/'sep23-continuation/history/20260923T161310787163Z/RECEIPT.json'; cp=load(checkpoint); copies=[]
    for i,row in enumerate(cp['files'],1):
        raw=Path(row['path']).read_bytes(); before=Path(row['backup']).read_bytes()
        assert sha(raw)==row['sha256'] and len(raw)==row['bytes'] and sha(before)==row['before_sha256']
        copies.append({'ordinal':i,'document':Path(row['path']).name,'current_sha256':sha(raw),'bytes':len(raw),
            'historical_before_sha256':sha(before),'historical_snapshot_is_current':False})
    text=Path(cp['files'][0]['path']).read_text(encoding='utf-8')
    start=text.index('### Latest continuation checkpoint036'); end=text.index('<!-- current-continuation:end -->',start)
    excerpt=text[start:end].strip()+'\n'
    put(P+'checkpoint036/CURRENT-EXCERPT.md',scrub(excerpt).encode())
    put(P+'checkpoint036/SNAPSHOT-RECEIPT.json',dump({'status':'TEN_CURRENT_DOCUMENTS_VERIFIED_CHECKPOINT036','at_utc':cp['at_utc'],
        'source_receipt_sha256':sha(checkpoint.read_bytes()),'documents':copies,
        'scope':'Only the latest technical checkpoint is public here; complete documents and historical private context are excluded.',
        'excerpt_utf8_lf_sha256':sha(excerpt.encode()),'source_body_sha256':cp['body_sha256']}))
    capture(Path(__file__),P+'stage_public_backup.py')
    put(P+'PUBLIC-BACKUP.md',('''# Installed observation-window export057

This increment preserves one actual CPU export from installed056 and its exact self-contained authored GLB, metadata,70 PNG textures, material definitions, six door hierarchies and134 collider links. Source and dependency recovery refer to immutable public commit31643796a39ef591337fae5225feba0bcd2bdf79. No canonical source is changed by this increment. Prior exports, previews, public026 and owner worlds remain unchanged.

The independent standard-library checker reads the package without graphics or model dependencies:

    python independent-review-001/check_package.py --package actual-001/package

For the exact four-reveal-mesh comparison add `--prior ../world-observation-setting-054/actual-001/package` from this directory. The test checks byte hashes, manifest seal, bounded GLB buffers/accessors, embedded PNG headers, collider ownership and preserved metadata. The producer's saved importer evidence covers18 door poses; this checker does not run the interaction engine or hostile-file sandboxing.

The export completed in2.56 seconds with a sampled635.5MiB child-family RSS peak. Sampling excludes the supervisor and may miss short peaks. These are transport/source preservation results, not a new visual review, realism approval, pressure simulation or engine/VR integration. Appearance remains procedural; native trim review is preserved in the prior public026 increment.

Original brief, local world/research inputs, runtimeData, personal memories, native dependencies and media are excluded. The derived fictional Mars package contains only minimal setting source IDs/hashes; its bytes are unmodified. Local identity paths in operational scripts/receipts are redacted; these scripts require local rebinding and private input access to rerun. Original/public digests are both recorded. The portable checker needs neither private source nor those operational scripts.

Checkpoint036 is an as-of technical excerpt, accompanied by hash validation of all ten local current handoff/status documents. Historical beforeimages are explicitly distinguished. Full unrelated historical handoffs are retained privately rather than repeated publicly.
''').encode())
    put(P+'SOURCE-PROVENANCE.json',dump(records))
    result=subprocess.run([sys.executable,'-B','independent-review-001/check_package.py','--package','actual-001/package'],cwd=O/P,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    put(P+'PUBLIC-PACKAGE-CHECK.json',dump(json.loads(result.stdout)))
    prompt=load(K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json')['brief']['prompt'].encode()
    files=[]
    for path in sorted(O.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(O).as_posix(); raw=path.read_bytes()
        assert 'runtime_context/' not in rel and 'runtimeData/' not in rel and prompt not in raw,rel
        assert not re.search(rb'C:[/\\]+Users[/\\]+robmc',raw,re.I),rel
        assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})',raw),rel
        if path.suffix=='.py':ast.parse(raw.decode())
        if path.suffix=='.json':json.loads(raw)
        if path.suffix=='.jsonl':
            for line in raw.splitlines():json.loads(line)
        existing=subprocess.run(['git','cat-file','-e',BASE+':'+rel],cwd=CLONE,capture_output=True)
        assert existing.returncode!=0,'This incremental backup must be additive: '+rel
        files.append({'path':rel,'file':str(path),'sha256':sha(raw),'bytes':len(raw),'before_sha256':None})
    manifest={'repository':'rmcmurrer81/KiraWorld','clone':str(CLONE),'base_commit':BASE,'receipt_prefix':'world-export-027',
        'reviewed':False,'allowed_prefixes':[P],'message':'Preserve installed window export, independent package checks and checkpoint036','files':files}
    mp=W/'sep22-backups/world-export-027.manifest.json'
    with mp.open('xb') as f:f.write(dump(manifest))
    delivery={'status':'PUBLIC027_STAGED_FOR_ROOT_REVIEW_NO_PUSH','manifest':str(mp),'manifest_sha256':sha(mp.read_bytes()),
        'files':len(files),'bytes':sum(row['bytes'] for row in files),'base_commit':BASE,'source_recovery_files':len(rows),
        'protected_originals_verified':116,'prior_derived_verified':29,'current_handoffs_verified':10,
        'canonical_promotions':0,'raw_owner_context_included':False,'public_checker':'PASS','git_mutations':0,
        'independent_review_sha256':sha((A/'REVIEW.json').read_bytes())}
    with (H/'DELIVERY.json').open('xb') as f:f.write(dump(delivery))
    print(json.dumps(delivery))
if __name__=='__main__':main()
