"""Isolate exact installed056 sources; do not modify canonical or saved worlds."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent;K=Path('C:/Users/robmc/Kira')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
closure=json.loads((W/'world-installed-observation-export-057/INSTALLED-SOURCE-CLOSURE.json').read_bytes())
protected=json.loads((W/'world-observation-trim-056/native-successor-001/INSTALL-PLAN.json').read_bytes())['protected_inputs']
assert len(closure)==42 and len(protected)==116
assert all(sha(K/p)==v['sha256'] for p,v in closure.items())
assert all(sha(Path(p))==v for p,v in protected.items())
for rel in closure:
 for tree in ('preimages','candidate'):
  to=H/tree/rel;to.parent.mkdir(parents=True,exist_ok=True);assert not to.exists();shutil.copyfile(K/rel,to)
for name in ('base','renamed','wider','translated'):
 p=H/'fixtures'/(name+'.json');p.parent.mkdir(exist_ok=True);shutil.copyfile(W/'world-meal-station-candidate-059/fixtures'/(name+'.json'),p)
(H/'SOURCE-PINS.json').write_text(json.dumps(closure,indent=2)+'\n',encoding='utf-8')
(H/'OWNER-PRESERVATION.local.json').write_text(json.dumps(protected,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'isolated_sources':len(closure),'protected_owner_files':len(protected),'canonical_modified':False}))
