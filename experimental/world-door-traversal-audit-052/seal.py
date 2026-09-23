"""Freeze read-only052 source/evidence; no product or owner-data writes."""
from pathlib import Path
import datetime,hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');E=K/'tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
prior=W/'world-door-targeting-candidate-051';plan=json.loads((prior/'INSTALL-PLAN.json').read_bytes());receipt=json.loads((prior/'INSTALLED.json').read_bytes())
assert receipt['status']=='051_EXACT_FIVE_FILE_INSTALL_PASS' and receipt['install_plan_sha256']=='acc62a7e35915eaf62ce3914b04f0cc14f144285f00c701fa1f7a11edc2d435c'
assert len(plan['protected_inputs'])==116 and all(sha(p)==v for p,v in plan['protected_inputs'].items())
expected=json.loads((prior/'SOURCE-PINS.json').read_bytes())
for row in plan['files']:
 rel=Path(row['target']).relative_to(E).as_posix();expected[rel]=row['after']['sha256']
assert all(sha(E/p)==v for p,v in expected.items())
source=[]
for rel in ('walk_controller.mjs','horizontal_navigation.mjs','layout_package_assets/source/walk_controller.mjs','layout_package_assets/source/horizontal_navigation.mjs','layout_package_assets/source/room_dressing_plan.mjs'):
 p=E/rel;q=H/'baseline/tools/world_builder_engine'/rel;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();shutil.copyfile(p,q);source.append({'path':rel,'sha256':sha(p),'bytes':p.stat().st_size})
result=json.loads((H/'AUDIT-RESULT.json').read_bytes());assert result['status']=='BOUNDED_ACTUAL_NAVIGATION_AUDIT_PASS_NO_NEW_DEFECT' and not result['failures']
assert len(result['checks'])==7 and len(result['walks'])==2
assert result['walks'][0]['distance']==result['walks'][1]['distance']
put(H/'SOURCE-PINS.json',{'installed051_receipt_sha256':sha(prior/'INSTALLED.json'),'sources':source,'all_engine_pins_checked':expected})
put(H/'PRESERVATION.json',{'status':'READ_ONLY_AUDIT_PRESERVATION_PASS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'protected_input_count':116,
 'protected_inputs_unchanged':True,'installed_engine_files_unchanged':len(expected),'canonical_edits':0,'owner_world_copies_or_writes':0,'geometry_sha256':result['geometry_sha256'],'models_ui_gpu':0})
closure={p.relative_to(H).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
put(H/'FROZEN-MANIFEST.json',{'files':closure})
delivery={'status':'052_BOUNDED_NAVIGATION_AUDIT_PASS_NO_NEW_DEFECT','frozen_manifest_sha256':sha(H/'FROZEN-MANIFEST.json'),'checks':7,'controller_walks':2,
 'metres_per_walk':result['walks'][0]['distance'],'doorway_segment_cases':216,'thin_leaf_cases':6,'sub_max_step_corner_cases':25,'closed_wall_exterior_cases':7,
 'protected_originals_unchanged':116,'product_source_changes':0,'model_ui_gpu_jobs':0,'next_gap':'Viewport Deck has no actual exterior viewport; bounded geometry proposal only.','realism_or_owner_approval':False}
put(H/'DELIVERY.json',delivery);print(json.dumps(delivery))
