from pathlib import Path
import hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;W=H.parent;S=W/'world-observation-viewport-053';K=Path('@kira_root');E=K/'tools/world_builder_engine';C=H/'candidate/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
assert not C.exists();shutil.copytree(S/'candidate',H/'candidate',ignore=shutil.ignore_patterns('__pycache__'))
old=(C/'layout_package_assets/source/room_dressing_render.mjs').read_text(encoding='utf-8')
new=old.replace('export function addObservationExterior(THREE,scene,viewport){\n  if(!viewport)return null;', '''export function addObservationExterior(THREE,scene,viewport,presentation=null,geometry=null){
  const source=presentation?.source;
  if(!viewport||presentation?.contract!=='bound_original_exterior_presentation_v1'||presentation.setting!=='mars_surface'||
     presentation.reason!=='explicit_original_mars_base_request'||!source||!geometry||
     source.research_packet_sha256!==geometry.research_packet_sha256||
     ![source.brief_sha256,source.request_sha256,source.research_packet_sha256].every(h=>typeof h==='string'&&/^[0-9a-f]{64}$/.test(h))||
     source.job_id!=='world_research_'+source.brief_sha256.slice(0,20))return null;''',1)
assert new!=old
new=new.replace("room_id:viewport.room_id,nontraversable:true,measured_terrain:false","room_id:viewport.room_id,nontraversable:true,measured_terrain:false,presentation_setting:presentation",1)
(C/'layout_package_assets/source/room_dressing_render.mjs').write_text(new,encoding='utf-8',newline='\n')
viewer=(C/'viewer.mjs').read_text(encoding='utf-8');embedded=old.replace('export function ','function ').strip();assert viewer.count(embedded)==1
viewer=viewer.replace(embedded,new.replace('export function ','function ').strip(),1)
viewer=viewer.replace("  const geometry=await response.json();", "  const geometry=await response.json();\n  const settingResponse=await fetch('/presentation.json',{cache:'no-store'});\n  if(!settingResponse.ok)throw new Error('The bound presentation setting could not be loaded.');\n  const presentation=await settingResponse.json();",1)
viewer=viewer.replace('  addObservationExterior(THREE,scene,viewport);','  addObservationExterior(THREE,scene,viewport,presentation,geometry);',1)
(C/'viewer.mjs').write_text(viewer,encoding='utf-8',newline='\n')
backend=(E/'world_layout_preview.py').read_text(encoding='utf-8')
backend=backend.replace("    CONTRACT: {", "    CONTRACT: {\n        '"+sha(E/'world_layout_preview.py')+"': "+str((E/'world_layout_preview.py').stat().st_size)+",",1)
backend=backend.replace('def verify_source(manifest):',(H/'presentation.fragment.py').read_text(encoding='utf-8')+'def verify_source(manifest):',1)
backend=backend.replace("    require(saved == pins, 'Frozen research provenance changed')", "    require(saved == pins, 'Frozen research provenance changed')\n    verify_presentation(manifest)",1)
backend=backend.replace("    inputs = {'geometry_source': binding(geometry_path)","    presentation_brief=capture_presentation_brief(research_packet_path)\n    packet=load_json(read_exact(research_packet_path)) if research_packet_path else None\n    presentation=presentation_setting(presentation_brief,packet,provenance.get('research_packet',{}).get('sha256'))\n    inputs = {'geometry_source': binding(geometry_path)",1)
backend=backend.replace("{'inputs':inputs,'sources':source_pins}","{'inputs':inputs,'sources':source_pins,'presentation':presentation}",1)
backend=backend.replace("'inputs':inputs,'source_pins':source_pins,'assets':assets,'preflight':evidence,","'inputs':inputs,'source_pins':source_pins,'assets':assets,'preflight':evidence,\n                'presentation_setting':presentation,'presentation_source_brief':presentation_brief,",1)
backend=backend.replace("    expected_id = 'layout-' + sha(canonical({'inputs':manifest['inputs'],'sources':manifest['source_pins']}))[:24]", "    identity={'inputs':manifest['inputs'],'sources':manifest['source_pins']}\n    if 'presentation_setting' in manifest:identity['presentation']=manifest['presentation_setting']\n    expected_id = 'layout-' + sha(canonical(identity))[:24]",1)
backend=backend.replace('    manifest_bytes = read_exact(manifest_path)','    manifest_bytes = read_exact(manifest_path)\n    presentation_bytes=canonical(verify_presentation(manifest))',1)
backend=backend.replace("            row = manifest['assets'].get(name)","            row = {'mime':'application/json; charset=utf-8'} if name=='/presentation.json' else manifest['assets'].get(name)",1)
backend=backend.replace('                payload = verify_binding(row)',"                payload = presentation_bytes if name=='/presentation.json' else verify_binding(row)",1)
(C/'world_layout_preview.py').write_text(backend,encoding='utf-8',newline='\n')
scene=C/'layout_package_assets/authored_scene.mjs';text=scene.read_text(encoding='utf-8').replace('buildAuthoredScene(geometry,metadata,canvasFactory){','buildAuthoredScene(geometry,metadata,canvasFactory,presentation=null){',1)
text=text.replace("scene.userData.airlock_pairs=metadata.airlock_pairs;","scene.userData.airlock_pairs=metadata.airlock_pairs;scene.userData.presentation_setting=presentation;",1)
text=text.replace('addObservationExterior(THREE,scene,viewport);','addObservationExterior(THREE,scene,viewport,presentation,geometry);',1);scene.write_text(text,encoding='utf-8',newline='\n')
build=C/'layout_package_assets/build_glb.mjs';text=build.read_text(encoding='utf-8').replace('buildAuthoredScene(req.geometry,req.metadata,canvasFactory)','buildAuthoredScene(req.geometry,req.metadata,canvasFactory,req.presentation??null)',1)
text=text.replace('  extensions:gltf.extensionsUsed,', '  presentation_setting:req.presentation??null,\n  extensions:gltf.extensionsUsed,',1);build.write_text(text,encoding='utf-8',newline='\n')
api=(E/'layout_package_export.py').read_text(encoding='utf-8');api=api.replace(sha(E/'viewer.mjs'),sha(C/'viewer.mjs'),1)
api=api.replace("'input_pin':input_pin,'eligibility':eligibility}","'input_pin':input_pin,'eligibility':eligibility,'presentation':manifest.get('presentation_setting')}",1)
api=api.replace("request={'geometry':prepared['geometry'],'options':opts,", "request={'geometry':prepared['geometry'],'presentation':prepared['presentation'],'options':opts,",1)
api=api.replace("  scene=bindings.parse(bindings.read(target/'scene.json'))", "  require(report.get('presentation_setting')==prepared['presentation'],'presentation_changed','The exported presentation does not match the selected immutable preview.')\n  scene=bindings.parse(bindings.read(target/'scene.json'))",1)
api=api.replace("'recipe_eligibility':prepared['eligibility'],", "'recipe_eligibility':prepared['eligibility'],'presentation_setting':prepared['presentation'],",1)
(C/'layout_package_export.py').write_text(api,encoding='utf-8',newline='\n')
pins=json.loads((C/'layout_package_assets/PRODUCER-PINS.json').read_bytes())
for r in ['source/room_dressing_render.mjs','authored_scene.mjs','build_glb.mjs']:
 p=C/'layout_package_assets'/r;pins['files'][r]={'sha256':sha(p),'bytes':p.stat().st_size}
(C/'layout_package_assets/PRODUCER-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')
rows=[];diff=[];delta=[]
for r in ['viewer.mjs','world_layout_preview.py','layout_package_assets/source/room_dressing_render.mjs','layout_package_assets/authored_scene.mjs','layout_package_assets/build_glb.mjs','layout_package_export.py','layout_package_assets/PRODUCER-PINS.json']:
 p=E/r;q=C/r;pre=H/'preimages/tools/world_builder_engine'/r;pre.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,pre)
 rows.append({'relative_path':'tools/world_builder_engine/'+r,'target':str(p),'before_sha256':sha(p),'preimage':str(pre),'after':{'path':str(q),'sha256':sha(q),'bytes':q.stat().st_size}})
 diff.extend(difflib.unified_diff(p.read_text(encoding='utf-8').splitlines(True),q.read_text(encoding='utf-8').splitlines(True),fromfile='installed051/'+r,tofile='candidate054/'+r))
 s=S/'candidate/tools/world_builder_engine'/r
 if not s.exists():s=p
 delta.extend(difflib.unified_diff(s.read_text(encoding='utf-8').splitlines(True),q.read_text(encoding='utf-8').splitlines(True),fromfile='candidate053/'+r,tofile='candidate054/'+r))
protected=json.loads((S/'INSTALL-PLAN.json').read_bytes())['protected_inputs'];assert len(protected)==116 and all(sha(p)==v for p,v in protected.items())
put(H/'SOURCE-PINS.json',json.loads((S/'SOURCE-PINS.json').read_bytes()))
put(H/'INSTALL-PLAN.json',{'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':rows,'protected_inputs':protected,'required_before_install':['Bound setting and adversarial source tests','Actual preview/export binding check','Root native preview review after014 closes','Separate exact installation authorization']})
(H/'SOURCE.diff').write_text(''.join(diff),encoding='utf-8',newline='\n');(H/'FROM053.diff').write_text(''.join(delta),encoding='utf-8',newline='\n')
put(H/'CANDIDATE-CLOSURE.json',{p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(C.rglob('*')) if p.is_file() and '__pycache__' not in p.parts})
(H/'baseline/engine').mkdir(parents=True)
for r in ('world_blueprint.py','layout_recipe_profile.py'):shutil.copyfile(E/r,H/'baseline/engine'/r)
(H/'fixtures').mkdir();shutil.copyfile(W/'world-bunk-detail-042/fixtures/base.json',H/'fixtures/synthetic-habitat.json')
print(json.dumps({'status':'054_ISOLATED_STAGED','files':len(rows),'plan_sha256':sha(H/'INSTALL-PLAN.json')}))
