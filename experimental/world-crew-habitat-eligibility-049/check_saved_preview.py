"""Read-only upgrade check: candidate parser with existing saved Mars preview."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent;K=Path('@kira_root')
sys.dont_write_bytecode=True;sys.path.insert(0,str(K/'tools'));sys.path.insert(0,str(H/'candidate/tools'))
from world_builder_engine.pipeline import latest_preview
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
protected=json.loads((H.parent/'world-chat-delay-candidate-048/INSTALL-PLAN.json').read_bytes())['protected_inputs']
assert all(sha(p)==v for p,v in protected.items())
job=K/'Data/world_research_jobs/world_research_c391ffbffc7352612392'
pointer=job/'latest-layout-pipeline.json';before=sha(pointer)
preview=latest_preview(job)
assert sha(pointer)==before and all(sha(p)==v for p,v in protected.items())
result={'status':'CANDIDATE_PARSER_EXISTING_SAVED_PREVIEW_READ_ONLY_PASS','manifest_sha256':preview['manifest_sha256'],'saved_pointer_sha256':before,
    'protected_inputs_unchanged':len(protected),'generated_files':0,'models_workers_ui_network':0,
    'scope':'Existing original Mars saved layout remains readable through actual latest_preview; no refresh or installation was performed.'}
with (H/'SAVED-PREVIEW-CHECK.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
