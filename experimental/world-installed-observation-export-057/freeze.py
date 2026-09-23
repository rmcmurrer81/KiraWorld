from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');P=W/'world-observation-trim-056/native-successor-001'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(p):return {'sha256':sha(p),'bytes':p.stat().st_size}
def put(name,value):
 with (H/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
plan=json.loads((P/'INSTALL-PLAN.json').read_bytes());assert all(sha(p)==s for p,s in plan['protected_inputs'].items())
assert all(sha(r['target'])==r['after']['sha256'] for r in plan['files'])
supervisor=json.loads((H/'SUPERVISOR.json').read_bytes());assert supervisor['exit_code']==0 and supervisor['remaining_owned_pids']==[]
source={}
for r in json.loads((P/'SOURCE-PINS.json').read_bytes()):
 p=K/'tools/world_builder_engine'/r;source['tools/world_builder_engine/'+r]=row(p)
for r,expected in json.loads((P/'CANDIDATE-CLOSURE.json').read_bytes()).items():assert row(K/r)==expected
put('INSTALLED-SOURCE-CLOSURE.json',source)
refs=[P/'INSTALL-PLAN.json',P/'INSTALLED.json',P/'CANDIDATE-CLOSURE.json',P/'installed-preview-001/REFRESH-RESULT.json',W/'world-observation-setting-054/ACTUAL-EXPORT-RESULT.json']
put('DEPENDENCIES.json',{'source_inventory':'INSTALLED-SOURCE-CLOSURE.json','installed_release':'056','external_reference_files':{str(p):row(p) for p in refs},
 'runtime_dependencies':'Exact external node/canvas/fonts verified by canonical layout_package_export.verify_dependencies; native binaries not bundled.',
 'comparison_export':'Prior054 full package is already preserved in public025. This run does not modify it.',
 'owner_source_files':'Original selected-job brief/geometry/research are private dependencies, not backup payload.'})
preview=json.loads((P/'installed-preview-001/REFRESH-RESULT.json').read_bytes())['current'];private=json.loads(Path(preview['manifest_path']).read_bytes())['presentation_source_brief']['prompt'].encode()
files={}
for p in sorted(H.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 raw=p.read_bytes();assert private not in raw
 assert p.suffix in ('.py','.json','.jsonl','.md','.log','.glb','.txt')
 files[p.relative_to(H).as_posix()]=row(p)
put('FROZEN-MANIFEST.json',{'status':'CLOSED_INSTALLED056_CPU_EXPORT057','files':files})
put('BACKUP-PLAN.json',{'status':'PUBLIC_BACKUP_PROPOSAL_NOT_PUBLISHED','prefix':'experimental/world-installed-observation-export-057/',
 'include_frozen_files':list(files),'include_receipts':['FROZEN-MANIFEST.json','DELIVERY.json','BACKUP-PLAN.json'],
 'binary_allowlist':['actual-001/package/scene.glb'],'glb_sha256':sha(H/'actual-001/package/scene.glb'),
 'raw_brief_original_geometry_or_research_included':False,'derived_geometry_metadata_included':True,
 'text_identity_paths':'Redact local workspace and user-home paths, retain exact binary/code/preimage bytes where appropriate and record original/public digests.',
 'canonical_source_promotion':False,'requires_root_payload_review':True})
put('DELIVERY.json',{'status':'INSTALLED056_CPU_EXPORT057_COMPLETE','frozen_manifest':row(H/'FROZEN-MANIFEST.json'),'files':len(files),
 'bytes':sum(r['bytes'] for r in files.values()),'glb_sha256':sha(H/'actual-001/package/scene.glb'),'assessment':row(H/'ASSESSMENT.json'),
 'elapsed_seconds':supervisor['elapsed_seconds'],'sampled_family_peak_rss_bytes':supervisor['sampled_family_peak_rss_bytes'],
 'remaining_owned_pids':[],'protected_originals':116,'prior_derived_files':29,'native_UI_GPU_models_exports_additional':0,
 'real_exports':1,'new_visual_or_owner_approval':False,'backup_prepared_only':True})
print(json.dumps({'status':'FROZEN057','delivery_sha256':sha(H/'DELIVERY.json'),'manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'files':len(files),'bytes':sum(r['bytes'] for r in files.values())}))
