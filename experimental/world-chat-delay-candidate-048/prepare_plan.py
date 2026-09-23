from pathlib import Path
import difflib,hashlib,json
H=Path(__file__).resolve().parent;P=H.parent/'world-chat-dispatch-candidate-047';K=Path('@kira_root')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'REVIEW-PLAN.json')=='cb537d271cb647f5f4c73bee1460ae9186a3bb7ba075b1f1186af42b9ed927be'
prior=json.loads((P/'REVIEW-PLAN.json').read_bytes())
rows=[]
# New helper first prevents the existing workspace importing an absent helper
# during the short interval between the two atomic file replacements.
for row in reversed(prior['files']):
    r=dict(row);r['after']=dict(row['after']);r['after']['path']=str(H/'candidate'/r['relative_path'])
    r['after']['sha256']=sha(r['after']['path']);r['after']['bytes']=Path(r['after']['path']).stat().st_size
    if r['preimage']:r['preimage']=str(H/'baseline/world_builder_workspace.py')
    assert (not Path(r['target']).exists()) if r['before_sha256'] is None else sha(r['target'])==sha(r['preimage'])==r['before_sha256']
    rows.append(r)
assert all(sha(p)==v for p,v in prior['protected_inputs'].items())
plan={'status':'048_EXACT_TWO_FILE_PLAN_NOT_INSTALLED','files':rows,'protected_inputs':prior['protected_inputs'],'previous_frozen_candidate_plan_sha256':sha(P/'REVIEW-PLAN.json')}
with (H/'INSTALL-PLAN.json').open('x',encoding='utf8') as f:json.dump(plan,f,indent=2);f.write('\n')
pins=json.loads((P/'SOURCE-PINS.json').read_bytes());assert all(sha(K/p)==v for p,v in pins.items())
with (H/'SOURCE-PINS.json').open('x',encoding='utf8') as f:json.dump(pins,f,indent=2);f.write('\n')
full='';delta=''
for row in rows:
    before=Path(row['preimage']).read_text(encoding='utf8') if row['preimage'] else ''
    after=Path(row['after']['path']).read_text(encoding='utf8')
    full+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='installed046/'+row['relative_path'],tofile='candidate048/'+row['relative_path']))
    old=(P/'candidate'/row['relative_path']).read_text(encoding='utf8')
    delta+=''.join(difflib.unified_diff(old.splitlines(True),after.splitlines(True),fromfile='frozen047/'+row['relative_path'],tofile='candidate048/'+row['relative_path']))
(H/'SOURCE.diff').write_text(full,encoding='utf8',newline='\n');(H/'FROM047.diff').write_text(delta,encoding='utf8',newline='\n')
print(json.dumps({'plan_sha256':sha(H/'INSTALL-PLAN.json'),'candidate_files':{r['relative_path']:r['after']['sha256'] for r in rows}}))
