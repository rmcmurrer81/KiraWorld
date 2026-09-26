"""Exact isolated 059+060 merge onto installed056; no preview, export or install."""
from pathlib import Path
import difflib, hashlib, json, shutil

H=Path(__file__).resolve().parent; W=H.parent; K=Path('C:/Users/robmc/Kira')
M=W/'world-meal-station-candidate-059'; D=W/'world-door-hardware-candidate-060'
PREFIX='tools/world_builder_engine/'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def write(name,value):
    with (H/name).open('x',encoding='utf-8',newline='\n') as f: f.write(json.dumps(value,indent=2)+'\n')
def checked_copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists(),target
    shutil.copyfile(source,target)

assert not (H/'candidate').exists(), 'Refuse to overwrite an earlier candidate'
assert sha(M/'FROZEN-MANIFEST.json')=='639e22c573191ae7e226614be914e94d6addcec4cf5ef7eb4b3e9a5de9bb8c57'
assert sha(D/'FROZEN-MANIFEST.json')=='cbbc4a547647dab32a6d0574cd080ff9d8e2f2c65f6af26c00d07acbd3c195d7'
source=read(D/'SOURCE-PINS.json'); protected=read(D/'OWNER-PRESERVATION.local.json')
assert source==read(M/'SOURCE-PINS.json')
assert len(source)==42 and len(protected)==116
assert all(sha(K/r)==v['sha256'] and (K/r).stat().st_size==v['bytes'] for r,v in source.items())
assert all(sha(p)==v for p,v in protected.items())
for origin in (M,D):
    frozen=read(origin/'FROZEN-MANIFEST.json')['files']
    for rel in source:
        path=origin/'candidate'/rel; pin=frozen['candidate/'+rel]
        assert sha(path)==pin['sha256'] and path.stat().st_size==pin['bytes'],path
for rel in source:
    for tree in ('preimages','candidate'): checked_copy(K/rel,H/tree/rel)
meal=['viewer.mjs','layout_package_assets/authored_scene.mjs','layout_package_assets/source/room_dressing_plan.mjs','layout_package_assets/source/room_dressing_render.mjs']
hardware=['walk_controller.mjs','layout_package_assets/source/walk_controller.mjs','layout_package_assets/source/scene_metadata.mjs']
for origin, paths in ((M,meal),(D,hardware)):
    for rel in paths:
        (H/'candidate'/PREFIX/rel).write_bytes((origin/'candidate'/PREFIX/rel).read_bytes())
C=H/'candidate'/PREFIX
exporter=(C/'layout_package_export.py').read_bytes()
for rel in ('viewer.mjs','walk_controller.mjs'):
    old=source[PREFIX+rel]['sha256'].encode(); new=sha(C/rel).encode()
    assert exporter.count(old)==1
    exporter=exporter.replace(old,new)
(C/'layout_package_export.py').write_bytes(exporter)
pins=read(C/'layout_package_assets/PRODUCER-PINS.json'); oldpins=read(C/'layout_package_assets/PRODUCER-PINS.json')
changed_pins=['authored_scene.mjs','source/room_dressing_plan.mjs','source/room_dressing_render.mjs','source/scene_metadata.mjs','source/walk_controller.mjs']
for rel in changed_pins:
    p=C/'layout_package_assets'/rel; pins['files'][rel]={'sha256':sha(p),'bytes':p.stat().st_size}
(C/'layout_package_assets/PRODUCER-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')
assert pins['external']==oldpins['external']
assert {p for p in pins['files'] if pins['files'][p]!=oldpins['files'][p]}==set(changed_pins)
closure={rel:{'sha256':sha(H/'candidate'/rel),'bytes':(H/'candidate'/rel).stat().st_size} for rel in source}
changed=[r for r in source if source[r]!=closure[r]]
assert set(changed)=={PREFIX+r for r in meal+hardware+['layout_package_export.py','layout_package_assets/PRODUCER-PINS.json']}
write('SOURCE-PINS.json',source); write('OWNER-PRESERVATION.local.json',protected);write('CANDIDATE-CLOSURE.json',closure)
diff=''.join(''.join(difflib.unified_diff((H/'preimages'/r).read_text(encoding='utf-8').splitlines(True),(H/'candidate'/r).read_text(encoding='utf-8').splitlines(True),fromfile='installed056/'+r,tofile='combined062/'+r)) for r in changed)
with (H/'SOURCE.diff').open('x',encoding='utf-8',newline='\n') as f:f.write(diff)
for name in ('base','renamed','wider','translated'):checked_copy(D/'fixtures'/(name+'.json'),H/'fixtures'/(name+'.json'))
checked_copy(D/'REPRODUCTION.json',H/'REPRODUCTION.json')
test=(M/'test_meal_station.mjs').read_text(encoding='utf-8')
with (H/'test_meal_station.mjs').open('x',encoding='utf-8',newline='\n') as f:f.write(test)
test=(D/'test_hardware.mjs').read_text(encoding='utf-8')
test=test.replace("'../world-meal-station-candidate-059/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs'","'./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs'")
test=test.replace("'./TEST-RESULT.json'","'./HARDWARE-TEST-RESULT.json'")
with (H/'test_hardware.mjs').open('x',encoding='utf-8',newline='\n') as f:f.write(test)
write('MERGE-PROVENANCE.json',{'status':'ISOLATED_COMBINATION_STAGED_NOT_INSTALLED','parent_frozen_manifests':{str(p.relative_to(W)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in (M/'FROZEN-MANIFEST.json',D/'FROZEN-MANIFEST.json')},'exact_meal_files':meal,'exact_hardware_files':hardware,'deliberate_merges':['layout_package_export.py','layout_package_assets/PRODUCER-PINS.json'],'changed_producer_pins':changed_pins,'changed_files':changed,'source_closure_files':42,'owner_originals_verified':116,'test_adaptation':'059 meal suite copied unchanged;060 hardware suite imports the actual combined meal planner and writes a separate result filename. No assertions removed.','preview_export_renderer_model_ui_install_calls':0})
print(json.dumps({'status':'STAGED','source_closure':42,'changed_files':len(changed),'protected_owner_files':116}))
