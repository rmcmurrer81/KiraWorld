"""Copy pinned local runtime dependencies and a derived package into isolation."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent
K=Path('@kira_root/tools/world_builder_engine')
P=H.parent/'world-bunk-detail-042/installed-mars-001/package'
def pin(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
sources={}
for rel in ['build/three.core.js','build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/utils/BufferGeometryUtils.js','package.json','LICENSE']:
 src=K/'layout_package_assets/vendor/three'/rel;dst=H/'vendor/three'/rel
 dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();shutil.copy2(src,dst)
 sources['vendor/three/'+rel]=pin(src)
src=K/'horizontal_navigation.mjs';shutil.copy2(src,H/'horizontal_navigation.mjs');sources['horizontal_navigation.mjs']=pin(src)
(H/'sample-package').mkdir(exist_ok=False)
for src in sorted(P.iterdir()):
 if src.is_file():shutil.copy2(src,H/'sample-package'/src.name);sources['sample-package/'+src.name]=pin(src)
sources['installed_contract']=pin(K/'layout_package_contract.json')
sources['installed_door_controller']=pin(K/'walk_controller.mjs')
(H/'SOURCE-PINS.json').write_text(json.dumps({'contract':'isolated_package_consumer_pins_v1','files':sources,'canonical_writes':False,'downloads':0},indent=2)+'\n',encoding='utf-8')
