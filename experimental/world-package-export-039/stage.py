from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;W=H.parent;old=W/'world-package-api-candidate-037';door=W/'world-airlock-sequencing-candidate-038'
shutil.copytree(old/'candidate',H/'candidate');shutil.copytree(old/'baseline',H/'baseline')
shutil.copytree(door/'fixtures',H/'fixtures')
for name in ('test_api.py','run_real_api.py','EXTERNAL-PINS.json'):shutil.copyfile(old/name,H/name)
for folder in ('baseline/exporter','baseline/native038'):(H/folder).mkdir(parents=True)
assets=H/'candidate/tools/world_builder_engine/layout_package_assets'
for name in ('source/walk_controller.mjs','source/scene_metadata.mjs','build_glb.mjs','authored_scene.mjs'):
 p=H/'baseline/exporter'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(assets/name,p)
controller=(door/'candidate/tools/world_builder_engine/walk_controller.mjs').read_text(encoding='utf-8')
shutil.copyfile(door/'candidate/tools/world_builder_engine/walk_controller.mjs',H/'baseline/native038/walk_controller.mjs')
shutil.copyfile(door/'baseline/horizontal_navigation.mjs',H/'baseline/native038/horizontal_navigation.mjs')
oldcontroller=(assets/'source/walk_controller.mjs').read_text(encoding='utf-8')
definitions=oldcontroller[oldcontroller.index('  // Authoring metadata only:'):oldcontroller.index('  return freeze({contract:DOOR_CONTRACT')]
newcontroller=controller.replace('  return freeze({contract:DOOR_CONTRACT,all,assemblies,colliders,nearest,toggle,advance,interlocks});',definitions+'  return freeze({contract:DOOR_CONTRACT,all,assemblies,definitions,colliders,nearest,toggle,advance,interlocks});')
assert newcontroller!=controller
(assets/'source/walk_controller.mjs').write_text(newcontroller,encoding='utf-8')
shutil.copyfile(door/'candidate/tools/world_builder_engine/walk_controller.mjs',H/'candidate/tools/world_builder_engine/walk_controller.mjs')
api=H/'candidate/tools/world_builder_engine/layout_package_export.py'
s=api.read_text().replace("CONTRACT='authored_saved_layout_package_v1'","CONTRACT='authored_saved_layout_package_v2'")
s=s.replace('5c81e5926690a7fee3dbfcd4ff41d40b6da9bc3fef2ae7cbc77dcd91c74a51a4','0884cce50d33a66e4a974a76fc7a0a15947bcb776f130b1b0a81b43adef76791');api.write_text(s,encoding='utf-8')
test=H/'test_api.py';s=test.read_text().replace('037','039').replace("H.parent/'world-habitat-realism-025/fixtures/synthetic_habitat.json'","H/'fixtures/synthetic_habitat.json'");test.write_text(s,encoding='utf-8')
pins={'037_install_plan_sha256':hashlib.sha256((old/'INSTALL-PLAN.json').read_bytes()).hexdigest(),
 '038_install_plan_sha256':hashlib.sha256((door/'INSTALL-PLAN.json').read_bytes()).hexdigest(),
 '038_native_controller_sha256':hashlib.sha256((door/'candidate/tools/world_builder_engine/walk_controller.mjs').read_bytes()).hexdigest(),
 'files_037':{str(p.relative_to(old/'candidate')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (old/'candidate').rglob('*') if p.is_file()}}
(H/'INPUT-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
print('039 isolated merge staged; no install, preview creation, real export or source writes')
