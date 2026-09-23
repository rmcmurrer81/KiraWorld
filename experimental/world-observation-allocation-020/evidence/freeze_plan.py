from pathlib import Path
import datetime
import hashlib
import json
H=Path(__file__).resolve().parent
def row(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
files=[]
for folder in [H/'candidate',H/'baseline',H.parent/'world-finite-key-candidate-019/candidate']:
 files+=sorted(folder.glob('*.mjs'))
files+=[H.parent/'world-finite-top-domain-candidate-016/candidate/finite_top_domain.mjs',H.parent/'world-frame-contact-perf-candidate/fixtures/wide.json']
files+=sorted(H.glob('check_*.mjs'))+[H/'run_checks.py']
plan={'status':'ISOLATED_OBSERVATION_ALLOCATION_EQUIVALENCE_CHECKS','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':[row(p) for p in files],'fixture':row(H.parent/'world-frame-contact-perf-candidate/fixtures/wide.json'),'budget':{'node_processes':1,'heap_mib':384,'rss_mib':512,'wall_seconds_per_check':30,'minimum_free_gib':2,'gpu_models':0},'paired_frames_each':12,'physics_settings_unchanged':True,'order':'020 candidate first then019 predecessor each frame; preserve all observations and certificates.'}
with (H/'PLAN.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'plan_sha256':row(H/'PLAN.json')['sha256'],'inputs':len(files)}))
