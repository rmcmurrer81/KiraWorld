from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;WORK=HERE.parent;K=Path('@kira_root')
target=HERE/'candidate/tools';target.mkdir(parents=True,exist_ok=True)
original=K/'tools/world_builder_workspace.py';baseline=HERE/'baseline/tools/world_builder_workspace.py';baseline.parent.mkdir(parents=True);baseline.write_bytes(original.read_bytes());(target/original.name).write_bytes(original.read_bytes())
assets=target/'world_builder_engine/layout_package_assets';assets.mkdir(parents=True)
source=WORK/'world-authored-glb-public-backup-012/publishable/experimental/world-authored-glb-036'
for directory in ('source','vendor'):shutil.copytree(source/directory,assets/directory)
for name in ('authored_scene.mjs','build_glb.mjs','cpu_canvas.mjs'):shutil.copyfile(source/name,assets/name)
shutil.copyfile(WORK/'world-structural-owner-candidate-034/package/package_writer.py',assets/'source_bindings.py')
localpins=json.loads((WORK/'world-authored-glb-prototype-036/SOURCE-PINS.local.json').read_text(encoding='utf-8'))
external={k:{'sha256':v['sha256'],'bytes':v['bytes']} for k,v in localpins.items() if v.get('not_bundled')}
canvas=Path(localpins['canvas-package']['source']).parent
for name in ('index.js','js-binding.js','geometry.js','load-image.js'):
 raw=(canvas/name).read_bytes();external['canvas/'+name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
(HERE/'EXTERNAL-PINS.json').write_text(json.dumps(external,indent=2)+'\n',encoding='utf-8')
(HERE/'BASELINE.json').write_text(json.dumps({'path':str(original),'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'owner_data_writes':0},indent=2)+'\n',encoding='utf-8')
print('Staged isolated037; canonical sources unchanged')
