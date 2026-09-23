"""Freeze candidate delivery; never installs or publishes."""
from pathlib import Path
import ast,difflib,hashlib,json
H=Path(__file__).resolve().parent;C=H/'candidate/tools/world_builder_engine/world_layout_preview.py';B=H/'baseline/world_layout_preview.py'
def pin(p):return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
before=B.read_text();after=C.read_text();ast.parse(after)
patch=H/'CHANGES.patch';assert not patch.exists();patch.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='installed/world_layout_preview.py',tofile='candidate026/world_layout_preview.py')))
test=json.loads((H/'TEST-RESULT-1.json').read_text());assert test['status']=='PASS' and test['tests']==23 and test['candidate_sha256']==pin(C)['sha256']
proof=json.loads((H/'READONLY-SAVED-PREVIEW-CHECK.json').read_text());assert proof['all_bytes_unchanged'] and proof['candidate_sha256']==pin(C)['sha256']
baseline=json.loads((H/'BASELINE.json').read_text());assert pin(Path(baseline['source']))['sha256']==baseline['sha256']
result={'status':'ISOLATED_CANDIDATE_READY_FOR_ROOT_REVIEW','files':[{'path':'tools/world_builder_engine/world_layout_preview.py',
 'file':str(C.resolve()),'sha256':pin(C)['sha256'],'bytes':C.stat().st_size,'before_sha256':baseline['sha256']}],
 'baseline':pin(B),'delta':pin(patch),'tests':pin(H/'TEST-RESULT-1.json'),'test_source':pin(H/'test_compatibility.py'),
 'readonly_saved_preview':pin(H/'READONLY-SAVED-PREVIEW-CHECK.json'),'readonly_check_source':pin(H/'check_saved_preview_readonly.py'),
 'readme':pin(H/'README.md'),'cpu_tests':23,'real_node_preflights':1,'source_contract':'isolated_world_layout_preview_v1',
 'legacy_creator_sha256':baseline['sha256'],'canonical_installed':False,'owner_files_modified':False,
 'network_model_gpu_browser_calls':0,'owner_quality_approved':False,'frontend_files_changed':[]}
with (H/'DELIVERY.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'delivery':pin(H/'DELIVERY.json'),'candidate':pin(C),'status':result['status']}))
