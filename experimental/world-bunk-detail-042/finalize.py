from pathlib import Path
import datetime,hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
pins=json.loads((H/'SOURCE-PINS.json').read_bytes());assert all(sha(E/r)==v for r,v in pins.items())
api=(E/'layout_package_export.py').read_text(encoding='utf-8');old_viewer=sha(E/'viewer.mjs');assert old_viewer in api
(C/'layout_package_export.py').write_text(api.replace(old_viewer,sha(C/'viewer.mjs')),encoding='utf-8',newline='\n')
scene=C/'layout_package_assets/authored_scene.mjs';text=scene.read_text(encoding='utf-8');text=text.replace('Equipment builder remains an exact025 byte copy.','Equipment builder includes isolated042 static bunk geometry detail.')
scene.write_text(text,encoding='utf-8',newline='\n')
producer=C/'layout_package_assets/PRODUCER-PINS.json';prod=json.loads(producer.read_bytes());prod['files']['authored_scene.mjs']={'sha256':sha(scene),'bytes':scene.stat().st_size};producer.write_text(json.dumps(prod,indent=2)+'\n',encoding='utf-8')
relative=['viewer.mjs','layout_package_export.py','layout_package_assets/source/room_dressing_render.mjs','layout_package_assets/authored_scene.mjs','layout_package_assets/PRODUCER-PINS.json']
rows=[];diff=[]
for rel in relative:
 target=E/rel;after=C/rel;preimage=H/'preimages/tools/world_builder_engine'/rel;preimage.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,preimage)
 rows.append({'relative_path':'tools/world_builder_engine/'+rel,'target':str(target),'before_sha256':sha(target),'preimage':str(preimage),'after':{'path':str(after),'sha256':sha(after),'bytes':after.stat().st_size}})
 diff.extend(difflib.unified_diff(target.read_text(encoding='utf-8').splitlines(True),after.read_text(encoding='utf-8').splitlines(True),fromfile='installed041/'+rel,tofile='candidate042/'+rel))
protected=json.loads((W/'world-export-profile-041/INSTALL-PLAN-REV3.json').read_bytes())['protected_inputs'];assert all(sha(p)==v for p,v in protected.items())
put(H/'INSTALL-PLAN.json',{'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':rows,'protected_inputs':protected,'required_before_install':['Root review','Real CPU GLB/importer check','Controlled visual review or explicit approval to defer'],'saved_previews':'Preserve all previous immutable builds; create a fresh bound preview only after explicit approval. Older appearance is intentionally not exported through the newer renderer.'})
(H/'COMBINED-CHANGES.patch').write_text(''.join(diff),encoding='utf-8')
closure={p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};put(H/'CANDIDATE-CLOSURE.json',closure)
readme='''# Static bunk geometry detail042 — isolated

The habitat bunk used box pillows and flat blankets, with no upper front guard.
This candidate authors rounded mattress/pillow meshes, a folded blanket surface
with dropped outer edges, connected upper guard members and a ladder-side access
bay. These are original deterministic meshes; no images or external assets were
copied. Dimensions are grounded in the existing authored assembly, not a claim
about a measured real spacecraft or a certified bunk design.

The assembly remains 2.08 m long, 0.90 m deep and 2.12 m high. Upper mattress top
is 1.42 m; guard top is 1.78 m. The front access bay is 0.523 m wide and contains
the existing ladder alignment. Guard posts reach the upper deck. Soft furnishings
fit the conservative existing bunk collider; mattress/deck and pillow/mattress
vertical support relations are checked. The ladder stiles now reach floor level.

Four synthetic layouts and the explicit saved Mars geometry pass CPU checks:
actual meshes inside the original collider; six routes clear in both directions;
six door sweep bounds clear; bunk footprint inside the room floor support; no
other furnishing overlaps; finite vertices/normals; 6,708 triangles per bunk;
15 other equipment groups unchanged. The module embedded in the native viewer
is byte-identical to the exporter module after removal of export keywords.
Actual authored exporter mesh assembly matches the viewer's bunk meshes.

The exporter-path geometry test uses inert Canvas placeholders only to reach
mesh assembly. It does not verify rasterized textures or a real GLB roundtrip.
No browser, native UI, model or GPU job was run. Static geometry establishes no
cloth physics, comfort, structural safety, standard compliance or visual approval.
The conservative collision box still prevents walking/climbing/sitting inside the
bunk; this change does not implement avatar resting interaction.

Five files would need to change together: viewer, shared renderer, producer pins,
the export assembly comment, and the API's exact viewer digest. Old immutable
previews remain intact and must not silently acquire the newer appearance.
Existing Open current preview would create/reuse a newly pinned build after any
approved installation. New exports must match that build, not the old viewer.

Nothing is installed. See INSTALL-PLAN.json for exact preimages and remaining
review requirements. Preview/visual appearance and real GLB checks remain pending.
'''
with (H/'README.md').open('x',encoding='utf-8') as f:f.write(readme)
delivery={'status':'042_ISOLATED_STATIC_BUNK_GEOMETRY_READY_FOR_REVIEW','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'install_plan_sha256':sha(H/'INSTALL-PLAN.json'),'changed_files':len(rows),'synthetic_shape_checks':4,'actual_saved_geometry_checks':1,'triangles_per_bunk':6708,'other_equipment_unchanged':15,'protected_original_files_unchanged':len(protected),'installed':False,'real_glb_exports':0,'native_ui_models_gpu':0,'visual_or_owner_approval':False,'pending':['Real GLB importer verification','Visual review','Root install decision']}
put(H/'DELIVERY.json',delivery);print(json.dumps(delivery))
