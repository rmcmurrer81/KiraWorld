from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
pins={}
for name in ('walk_controller.mjs','horizontal_navigation.mjs','viewer.mjs','index.html','style.css'):
 raw=(K/'tools/world_builder_engine'/name).read_bytes();pins[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 for folder in ('baseline','candidate/tools/world_builder_engine'):
  p=H/folder/name;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(raw)
shutil.copytree(W/'world-working-doors-candidate-024/fixtures',H/'fixtures')
shutil.copyfile(W/'world-habitat-realism-025/fixtures/synthetic_habitat.json',H/'fixtures/synthetic_habitat.json')
test=(W/'world-working-doors-candidate-024/test_doors.mjs').read_text(encoding='utf-8')
test=test.replace("'./TEST-RESULT-003.json'","'./GENERIC-DOOR-RESULT.json'")
(H/'test_generic_doors.mjs').write_text(test,encoding='utf-8')
(H/'BASELINE-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
print('038 isolated sources staged; no installed source changed')
