"""Stage only preview verification compatibility; never install or open owner jobs."""
from pathlib import Path
import hashlib,json,difflib
H=Path(__file__).resolve().parent
source=Path('@user_home/Kira/tools/world_builder_engine/world_layout_preview.py')
expected='2d5a27e7137011872a0d9645cbfdd96646e592334b44d9d6e800389518604cb9'
raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
baseline=H/'baseline/world_layout_preview.py';candidate=H/'candidate/tools/world_builder_engine/world_layout_preview.py'
for p in (baseline,candidate):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(raw)
with (H/'BASELINE.json').open('x',encoding='utf-8') as f:json.dump({'source':str(source),'sha256':expected,'bytes':len(raw),'candidate_installed':False,'owner_data_modified':False},f,indent=2)
print(json.dumps({'status':'ISOLATED_BASELINE_PREPARED','sha256':expected}))
