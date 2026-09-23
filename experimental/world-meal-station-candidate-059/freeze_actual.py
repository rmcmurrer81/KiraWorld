"""Freeze the additive059 actual-export evidence without altering its original delivery."""
from pathlib import Path
import datetime,hashlib,json,psutil

H=Path(__file__).resolve().parent;K=Path('@kira_root')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
original=json.loads((H/'FROZEN-MANIFEST.json').read_bytes())['files']
for rel,row in original.items():assert sha(H/rel)==row['sha256'] and (H/rel).stat().st_size==row['bytes']
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes())
assert all(sha(Path(p))==v for p,v in plan['protected_inputs'].items())
assert all(sha(K/rel)==row['sha256'] for rel,row in json.loads((H/'SOURCE-PINS.json').read_bytes()).items())
supervisor=json.loads((H/'SUPERVISOR.json').read_bytes());assert supervisor['status']=='ISOLATED059_CPU_EXPORT_PASS'
assert not supervisor['remaining_owned_pids']
for identity in supervisor['owned_identities']:
 try:assert psutil.Process(identity['pid']).create_time()!=identity['create_time']
 except psutil.NoSuchProcess:pass
protected=json.loads((H/'actual-001/PROTECTED-DERIVED-FILES.json').read_bytes())['files']
assert all(sha(Path(p))==v for p,v in protected.items())
assert json.loads((H/'ACTUAL-DELTA-RESULT.json').read_bytes())['status']=='ACTUAL059_GLB_DELTA_PASS'
dependencies={'world-installed-observation-export-057-independent-review-001/check_package.py':None,
 'world-installed-observation-export-057/run_cpu_export.py':None,
 'world-galley-detail-045/run_cpu_export.py':None}
for rel in dependencies:
 p=H.parent/rel;dependencies[rel]={'sha256':sha(p),'bytes':p.stat().st_size}
put(H/'ACTUAL-DEPENDENCIES.json',{'files_relative_to_work':dependencies,'baseline_package':{'path':'world-installed-observation-export-057/actual-001/package',
 'glb_sha256':sha(H.parent/'world-installed-observation-export-057/actual-001/package/scene.glb')},
 'local_only_inputs':'The saved-job, research and private immutable-preview source bindings are required for an operational rerun. Do not bundle them in a public backup.'})
names=['run_cpu_export.py','check_actual_delta.py','SUPERVISOR.json','ACTUAL-DELTA-RESULT.json','ACTUAL-EXPORT.md','ACTUAL-DEPENDENCIES.json','freeze_actual.py']
names += [p.relative_to(H).as_posix() for folder in ('actual-001','actual-comparison-history') for p in sorted((H/folder).rglob('*')) if p.is_file()]
rows={name:{'sha256':sha(H/name),'bytes':(H/name).stat().st_size} for name in names}
put(H/'ACTUAL-FROZEN-MANIFEST.json',{'status':'059_ACTUAL_CPU_EXPORT_APPENDIX_FROZEN','files':rows,
 'original_delivery_sha256':sha(H/'DELIVERY.json'),'original_frozen69_preserved':True,
 'excluded':'runtime_context holds local source bindings and an exact copy of source geometry; no public backup authorization for those raw source files.'})
preview=json.loads((H/'actual-001/PREVIEW-RESULT.json').read_bytes())['current']
result={'status':'ISOLATED059_ACTUAL_EXPORT_READY_FOR_ROOT_REVIEW','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'original_delivery_sha256':sha(H/'DELIVERY.json'),'actual_manifest_sha256':sha(H/'ACTUAL-FROZEN-MANIFEST.json'),'files':len(rows),
 'glb_sha256':sha(H/'actual-001/package/scene.glb'),'glb_bytes':(H/'actual-001/package/scene.glb').stat().st_size,
 'package_manifest_sha256':sha(H/'actual-001/package/manifest.json'),'immutable_preview':preview,
 'actual_delta_sha256':sha(H/'ACTUAL-DELTA-RESULT.json'),'supervisor_sha256':sha(H/'SUPERVISOR.json'),
 'original116_canonical42_frozen69_previous34_unchanged':True,'owned_processes_remaining':0,
 'installed':False,'native_or_CPU_visual_review':False,'owner_approval':False,'next':'Coordinate one artifact/native visual inspection after Studio012 cleanup; installation remains unapproved.'}
put(H/'ACTUAL-DELIVERY.json',result);print(json.dumps(result))
