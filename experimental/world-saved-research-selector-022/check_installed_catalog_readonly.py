from pathlib import Path
import hashlib
import json
import sys
H=Path(__file__).resolve().parent;K=Path('@user_home/Kira')
sys.path.insert(0,str(H/'candidate/tools'))
from world_saved_research import list_saved_research
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
roots=[K/'Data/world_research_jobs',K/'Data/world_original_components',K/'Data/world_bedding_studies']
def inventory():return {str(p.relative_to(K)).replace('\\','/'):sha(p) for root in roots for p in sorted(root.rglob('*')) if p.is_file()}
before=inventory();installed=sha(K/'tools/world_builder_workspace.py')
items=list_saved_research(roots[0]);after=inventory()
assert before==after and installed==sha(K/'tools/world_builder_workspace.py')
assert len(items)==2 and all(item['available'] for item in items)
out={'status':'PASS_READONLY_EXISTING_CATALOG','jobs':len(items),'available':sum(bool(i['available']) for i in items),'owner_research_and_component_files_checked':len(before),'all_bytes_unchanged':True,'installed_workspace_unchanged':True,'models_network_ui_browser_or_installation':False,'states':[{'job_id':i['job_id'],'stage':i['stage']} for i in items]}
with (H/'READONLY-INSTALLED-CATALOG.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out))
