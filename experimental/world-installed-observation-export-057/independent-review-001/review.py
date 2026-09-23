"""Independent read-only receipt/source verification; no export or graphics calls."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
from check_package import check
H=Path(__file__).resolve().parent; W=H.parent
K=Path('@kira_root'); S=W/'world-installed-observation-export-057'
BASE='31643796a39ef591337fae5225feba0bcd2bdf79'
CLONE=W/'kiraworld-shared-recall-publication-001/repo'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
load=lambda p:json.loads(p.read_bytes())
def main():
    assert sha((S/'DELIVERY.json').read_bytes())=='e38f05fe0249f008c3c7b012c831ef33ca18a2c1baa86180912a5a5678f7ad66'
    delivery=load(S/'DELIVERY.json'); frozen=load(S/'FROZEN-MANIFEST.json')
    assert sha((S/'FROZEN-MANIFEST.json').read_bytes())==delivery['frozen_manifest']['sha256']
    for name,row in frozen['files'].items():
        raw=(S/name).read_bytes(); assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    deps=load(S/'DEPENDENCIES.json')
    for name,row in deps['external_reference_files'].items():
        raw=Path(name).read_bytes(); assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    closure=load(S/'INSTALLED-SOURCE-CLOSURE.json')
    for rel,row in closure.items():
        raw=(K/rel).read_bytes(); assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
        public=subprocess.run(['git','show',BASE+':'+rel],cwd=CLONE,check=True,capture_output=True).stdout
        assert public==raw,rel
    plan=load(W/'world-observation-trim-056/native-successor-001/INSTALL-PLAN.json')
    protected=plan['protected_inputs']; prior=load(S/'actual-001/PROTECTED-DERIVED-FILES.json')['files']
    for name,digest in [*protected.items(),*prior.items()]:assert sha(Path(name).read_bytes())==digest
    assert len(protected)==116 and len(prior)==29
    package=check(S/'actual-001/package',W/'world-observation-setting-054/actual-001/package')
    supervisor=load(S/'SUPERVISOR.json'); assert supervisor['remaining_owned_pids']==[]
    api=load(S/'actual-001/API-RESULT.json')
    assert api['installed_api_sha256']==closure['tools/world_builder_engine/layout_package_export.py']['sha256']
    assert api['result']['manifest_sha256']==sha((S/'actual-001/package/manifest.json').read_bytes())
    brief=load(K/'Data/world_research_jobs/world_research_c391ffbffc7352612392/job.json')['brief']['prompt'].encode()
    assert all(brief not in p.read_bytes() and b'presentation_source_brief' not in p.read_bytes() for p in (S/'actual-001/package').iterdir())
    result={'status':'INDEPENDENT057_SOURCE_PACKAGE_REVIEW_PASS','at_utc':datetime.now(timezone.utc).isoformat(),
        'delivery_sha256':sha((S/'DELIVERY.json').read_bytes()),'frozen_files_verified':len(frozen['files']),
        'external_receipt_hashes_verified':len(deps['external_reference_files']),
        'installed_sources_exact_at_public_base':len(closure),'public_base':BASE,'protected_originals_unchanged':116,
        'previous_derived_files_unchanged':29,'package':package,'raw_brief_excluded':True,
        'runtime_evidence':{'source':'Previously closed supervisor receipt; no model/export relaunched','elapsed_seconds':delivery['elapsed_seconds'],
        'sampled_family_peak_rss_bytes':delivery['sampled_family_peak_rss_bytes'],'remaining_owned_pids':[]},
        'new_UI_GPU_models_exports':0,'canonical_or_owner_writes':0,'blockers':[],
        'limits':['No new visual inspection: transport checks do not establish habitat realism or owner approval.',
        'Source/importer records verify18 door poses; this read-only audit does not execute native interaction, collision, pressure simulation or VR.',
        'Peak RSS excludes the supervisor;10ms sampling may miss transient peaks.',
        'Known authored package only; this checker is not a sandbox for hostile files.'],
        'audit_harness_history':['Initial count assertion treated shared glTF mesh resources as instantiated meshes; corrected to node mesh instances.',
        'Initial manifest lookup used airlock_pairs; corrected to actual airlock_pair_policy schema. No product/source change.']}
    with (H/'REVIEW.json').open('xb') as f:f.write((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k not in ('package','audit_harness_history','limits')}))
if __name__=='__main__':main()
