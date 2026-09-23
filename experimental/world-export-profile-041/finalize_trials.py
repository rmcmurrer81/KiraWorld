from pathlib import Path
import datetime,difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;K=Path('@kira_root')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
plan=json.loads((H/'INSTALL-PLAN-REV2.json').read_bytes())
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
assert all(sha(K/p)==v for p,v in json.loads((H/'BASELINE-PINS.json').read_bytes()).items())
for row in plan['files']:
 assert sha(row['after']['path'])==row['after']['sha256']
 assert (sha(row['target']) if Path(row['target']).exists() else None)==row['before_sha256']
trial=json.loads((H/'ACTUAL-TRIAL-RESULT.json').read_bytes());assert trial['status']=='THREE_ACTUAL041_EXPORT_IMPORT_TRIALS_PASS'
shutil.copyfile(H/'PROPOSAL.md',H/'history/PROPOSAL-before-trials.md')
text=(H/'PROPOSAL.md').read_text()
text=text.replace('No Canvas, texture\nrasterization, GLB generation, native UI, browser or model was run for041.','Those initial shape checks used no Canvas or GLB generation. The subsequent\nroot-authorized trials below used CPU texture rasterization and real GLB export/import.')
start=text.index('Before installation: coordinate real CPU-only GLB exports/importer checks')
text=text[:start]+'''Three actual CPU export/importer trials now pass: renamed synthetic, wider
synthetic and the saved Mars API regression. Each preserved7 rooms,6 doors,
134 colliders and67 embedded PNGs, with exact independent airlock metadata and
imported hinge/geometry/material/texture checks. Elapsed times were1.27s,1.26s
and1.39s respectively; sampled process-family peak RSS was765,637 and631 MiB.
See ACTUAL-TRIAL-RESULT.json and the per-package ROUNDTRIP.json receipts.
Sampling every10ms may miss brief peaks; the supervisory process was excluded.

All116 protected originals and installed039 baseline bytes remain unchanged.
Current proposed installation is INSTALL-PLAN-REV2.json (five files). The old
plan/contract/proposal and pretrial delivery remain as historical evidence.
Installation still needs root review;041 is not installed. Native use/visual
review remains separate and pending. There is only one real saved habitat;
synthetic shape trials do not establish support for arbitrary layouts.
This candidate establishes no game-engine runtime, pressure simulation, VR support
or visual realism approval. Eligibility is recorded separately from actual success.
'''
(H/'PROPOSAL.md').write_text(text,encoding='utf-8')
diff=[]
for row in plan['files']:
 old=Path(row['preimage']).read_text().splitlines(True) if row['preimage'] else []
 new=Path(row['after']['path']).read_text().splitlines(True)
 diff.extend(difflib.unified_diff(old,new,fromfile='installed039/'+row['relative_path'],tofile='candidate041/'+row['relative_path']))
with (H/'CHANGES-REV2.patch').open('x',encoding='utf-8') as f:f.write(''.join(diff))
delivery={'status':'041_ACTUAL_TRIALS_PASS_READY_FOR_ROOT_INSTALL_REVIEW','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),
 'changed_install_files':len(plan['files']),'mocked_api_tests':35,'pure_profile_tests':15,'pure_recipe_shapes':4,
 'actual_041_glb_exports':3,'actual_trial_receipt_sha256':sha(H/'ACTUAL-TRIAL-RESULT.json'),
 'install_plan':'INSTALL-PLAN-REV2.json','install_plan_sha256':sha(H/'INSTALL-PLAN-REV2.json'),
 'old_plan_preserved':True,'protected_originals_unchanged':116,'installed039_unchanged':True,'installed041':False,
 'gpu_model_ui_browser_calls':0,'engine_vr_pressure_runtime':False,
 'pending':['Root installation decision','Native action and visual review','Additional independent real saved habitat coverage'],
 'eligibility_is_not_export_success':True}
put(H/'TRIAL-DELIVERY.json',delivery);print(json.dumps(delivery))
