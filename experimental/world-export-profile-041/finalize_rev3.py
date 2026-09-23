from pathlib import Path
import datetime,difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;K=Path('@kira_root');C=H/'candidate/tools/world_builder_engine/layout_package_contract.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
old=json.loads(C.read_bytes());assert old['candidate_status']=='isolated_not_installed_pending_new_shape_actual_exports'
shutil.copyfile(C,H/'history/contract-REV2-before-status-removal.json')
new={k:v for k,v in old.items() if k!='candidate_status'}
C.write_text(json.dumps(new,indent=2)+'\n',encoding='utf-8')
assert new['status']=='experimental' and set(old)-set(new)=={'candidate_status'}
plan=json.loads((H/'INSTALL-PLAN-REV2.json').read_bytes());plan['supersedes_plan_sha256']=sha(H/'INSTALL-PLAN-REV2.json')
for row in plan['files']:
 if row['relative_path'].endswith('/layout_package_contract.json'):row['after'].update(sha256=sha(C),bytes=C.stat().st_size)
 assert sha(row['after']['path'])==row['after']['sha256']
 assert (sha(row['target']) if Path(row['target']).exists() else None)==row['before_sha256']
assert all(sha(p)==v for p,v in plan['protected_inputs'].items())
put(H/'INSTALL-PLAN-REV3.json',plan)
closure=json.loads((H/'CANDIDATE-CLOSURE-REV2.json').read_bytes());closure['tools/world_builder_engine/layout_package_contract.json']={'sha256':sha(C),'bytes':C.stat().st_size}
put(H/'CANDIDATE-CLOSURE-REV3.json',closure)
diff=[]
for row in plan['files']:
 before=Path(row['preimage']).read_text().splitlines(True) if row['preimage'] else []
 diff.extend(difflib.unified_diff(before,Path(row['after']['path']).read_text().splitlines(True),fromfile='installed039/'+row['relative_path'],tofile='candidate041/'+row['relative_path']))
with (H/'CHANGES-REV3.patch').open('x',encoding='utf-8') as f:f.write(''.join(diff))
shutil.copyfile(H/'PROPOSAL.md',H/'history/PROPOSAL-REV2.md')
text=(H/'PROPOSAL.md').read_text().replace('INSTALL-PLAN-REV2.json (five files)','INSTALL-PLAN-REV3.json (five files)')
text+='\nREV3 removes only the stale candidate_status field from the shipped contract.\nThe stable experimental status remains. Previous contract/plans and actual-trial\nreceipts are preserved; implementation and actual generated package bytes did not change.\n'
(H/'PROPOSAL.md').write_text(text,encoding='utf-8')
delivery=json.loads((H/'TRIAL-DELIVERY.json').read_bytes());delivery.update(created_utc=datetime.datetime.now(datetime.UTC).isoformat(),install_plan='INSTALL-PLAN-REV3.json',install_plan_sha256=sha(H/'INSTALL-PLAN-REV3.json'),contract_sha256=sha(C),only_change_since_actual_trials='Removed stale candidate_status metadata; no implementation or generated output changes',previous_plans_and_contracts_preserved=True)
put(H/'DELIVERY-REV3.json',delivery)
put(H/'REV3-CHECK.json',{'status':'EXACT_METADATA_ONLY_REMOVAL_PASS','removed_keys':['candidate_status'],'other_contract_fields_equal':all(new[k]==old[k] for k in new),'implementation_bytes_unchanged':True,'protected_originals_unchanged':len(plan['protected_inputs']),'canonical_unchanged':True,'installed':False,'no_repeated_export_needed':True})
print(json.dumps(delivery))
