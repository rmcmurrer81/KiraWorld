from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;C=H/'candidate/tools/world_builder_engine';history=H/'history';history.mkdir()
contract=C/'layout_package_contract.json';shutil.copyfile(contract,history/'contract-before-scope-correction.json');shutil.copyfile(H/'INSTALL-PLAN.json',history/'INSTALL-PLAN-first.json')
v=json.loads(contract.read_bytes());v['supported_recipe']='Pinned authored_habitat_equipment_plan_v1 meshes/materials, preview_hinged_doors_v2 and explicit paired_airlock_door_sequence_v1 policy, with bounded authored geometry eligibility rather than a single Mars fixture digest.'
contract.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
plan=json.loads((H/'INSTALL-PLAN.json').read_bytes());plan['supersedes_plan_sha256']=hashlib.sha256((H/'INSTALL-PLAN.json').read_bytes()).hexdigest()
for row in plan['files']:
 if row['relative_path'].endswith('/layout_package_contract.json'):row['after'].update(sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),bytes=contract.stat().st_size)
(H/'INSTALL-PLAN-REV2.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
closure=json.loads((H/'CANDIDATE-CLOSURE.json').read_bytes());closure['tools/world_builder_engine/layout_package_contract.json']={'sha256':hashlib.sha256(contract.read_bytes()).hexdigest(),'bytes':contract.stat().st_size}
(H/'CANDIDATE-CLOSURE-REV2.json').write_text(json.dumps(closure,indent=2)+'\n',encoding='utf-8')
print('Contract corrected; original plan and contract preserved; no installation')
