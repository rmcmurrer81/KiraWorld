from pathlib import Path
import hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;K=Path('@kira_root');E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
assert not C.exists();C.mkdir(parents=True)
shutil.copytree(E/'layout_package_assets',C/'layout_package_assets',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copyfile(E/'walk_controller.mjs',C/'walk_controller.mjs')
rel='layout_package_assets/source/room_dressing_render.mjs';old=(E/rel).read_text(encoding='utf-8')
fragment=(H/'viewport.fragment.mjs').read_text(encoding='utf-8');new=fragment+'\n'+old
anchor="  for(const primitive of geometry.primitives){\n    if(primitive.role!=='wall')continue;"
assert new.count(anchor)==1
new=new.replace(anchor,"  const viewport=planObservationViewport(geometry,plan);\n  for(const sourcePrimitive of geometry.primitives){\n   for(const primitive of viewportWallPieces(sourcePrimitive,viewport)){\n    if(primitive.role!=='wall')continue;",1)
tail="panel.receiveShadow=true;scene.add(panel);\n  }"
assert new.count(tail)==1;new=new.replace(tail,"panel.receiveShadow=true;scene.add(panel);\n   }\n  }",1)
# A split panel still belongs to the source room/side; its suffix is harmless.
(C/rel).write_text(new,encoding='utf-8',newline='\n')
viewer=(E/'viewer.mjs').read_text(encoding='utf-8');embedded=old.replace('export function ','function ').strip();assert viewer.count(embedded)==1
viewer=viewer.replace(embedded,new.replace('export function ','function ').strip(),1)
needle='  const dressingMaterials=createDressingMaterials(THREE,dressing);';assert viewer.count(needle)==1
viewer=viewer.replace(needle,needle+'\n  const viewport=planObservationViewport(geometry,dressing);',1)
needle='    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...primitive.size),material);\n    mesh.position.set(...primitive.position);mesh.receiveShadow=true;scene.add(mesh);';assert viewer.count(needle)==1
viewer=viewer.replace(needle,'    scene.add(createStructuralPrimitive(THREE,primitive,material,viewport,dressingMaterials));',1)
viewer=viewer.replace('  addRoomDressing(THREE,scene,geometry,dressing,dressingMaterials);','  addRoomDressing(THREE,scene,geometry,dressing,dressingMaterials);\n  addObservationExterior(THREE,scene,viewport);',1)
(C/'viewer.mjs').write_text(viewer,encoding='utf-8',newline='\n')
scene=C/'layout_package_assets/authored_scene.mjs';text=scene.read_text(encoding='utf-8')
text=text.replace('createDressingMaterials,addRoomDressing}','createDressingMaterials,addRoomDressing,planObservationViewport,createStructuralPrimitive,addObservationExterior}',1)
text=text.replace("  const materials=createDressingMaterials(THREE,plan,{canvasFactory});","  const materials=createDressingMaterials(THREE,plan,{canvasFactory});\n  const viewport=planObservationViewport(geometry,plan);scene.userData.observation_viewport=viewport;",1)
needle='    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...p.size),mat);mesh.name=p.id;mesh.position.set(...p.position);mesh.receiveShadow=true;';assert text.count(needle)==1
text=text.replace(needle,'    const mesh=createStructuralPrimitive(THREE,p,mat,viewport,materials);',1)
text=text.replace('  addRoomDressing(THREE,dressingRoot,geometry,plan,materials);','  addRoomDressing(THREE,dressingRoot,geometry,plan,materials);\n  addObservationExterior(THREE,scene,viewport);',1)
scene.write_text(text,encoding='utf-8',newline='\n')
api=(E/'layout_package_export.py').read_text(encoding='utf-8');assert api.count(sha(E/'viewer.mjs'))==1
(C/'layout_package_export.py').write_text(api.replace(sha(E/'viewer.mjs'),sha(C/'viewer.mjs')),encoding='utf-8',newline='\n')
pins=json.loads((C/'layout_package_assets/PRODUCER-PINS.json').read_bytes())
for r in ['source/room_dressing_render.mjs','authored_scene.mjs']:
 p=C/'layout_package_assets'/r;pins['files'][r]={'sha256':sha(p),'bytes':p.stat().st_size}
(C/'layout_package_assets/PRODUCER-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')
rows=[];diff=[]
for r in ['viewer.mjs',rel,'layout_package_assets/authored_scene.mjs','layout_package_export.py','layout_package_assets/PRODUCER-PINS.json']:
 p=E/r;q=C/r;pre=H/'preimages/tools/world_builder_engine'/r;pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,pre)
 rows.append({'relative_path':'tools/world_builder_engine/'+r,'target':str(p),'before_sha256':sha(p),'preimage':str(pre),'after':{'path':str(q),'sha256':sha(q),'bytes':q.stat().st_size}})
 diff.extend(difflib.unified_diff(p.read_text(encoding='utf-8').splitlines(True),q.read_text(encoding='utf-8').splitlines(True),fromfile='installed051/'+r,tofile='candidate053/'+r))
protected=json.loads((H.parent/'world-door-targeting-candidate-051/INSTALL-PLAN.json').read_bytes())['protected_inputs'];assert len(protected)==116 and all(sha(Path(p))==v for p,v in protected.items())
put(H/'SOURCE-PINS.json',{p.relative_to(E).as_posix():sha(p) for p in E.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
put(H/'INSTALL-PLAN.json',{'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':rows,'protected_inputs':protected,'required_before_install':['CPU viewport/collision/source tests','Actual CPU export/import','Root inspection of actual rendered artifact','Separate exact installation authorization'],'old_previews':'Retain all original saved previews/pointers; only new immutable previews can show this candidate.'})
(H/'SOURCE.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
put(H/'CANDIDATE-CLOSURE.json',{p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file() and '__pycache__' not in p.parts})
print(json.dumps({'status':'053_ISOLATED_STAGED','changed_files':len(rows),'plan_sha256':sha(H/'INSTALL-PLAN.json')}))
