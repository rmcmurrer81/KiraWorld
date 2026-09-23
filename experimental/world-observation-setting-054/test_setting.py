from pathlib import Path
import copy,hashlib,importlib.util,json,sys
H=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(H))
from baseline.engine.world_blueprint import compile_blueprint,BlueprintError
from baseline.engine.layout_recipe_profile import validate_recipe_profile
C=H/'candidate/tools/world_builder_engine'
spec=importlib.util.spec_from_file_location('candidate_preview054',C/'world_layout_preview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda b:hashlib.sha256(b).hexdigest()
def put(path,value):
 with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def data(prompt):
 brief={'brief_kind':'isolated_world_research_brief','schema_version':1,'research_mode':'analog_to_original','prompt':prompt,'subject':'Synthetic test; title is not authority'}
 digest=sha((json.dumps(brief,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode())
 packet={'brief_sha256':digest,'job_id':'world_research_'+digest[:20],'research_mode':'analog_to_original'}
 packet_sha=sha(m.canonical(packet));return brief,packet,packet_sha
cases=[
 ('direct Mars base','Build an original photorealistic Mars base. Later add the exterior approach.','mars_surface'),
 ('polite Mars habitat','Please create a new Mars surface habitat.','mars_surface'),
 ('content negative','Build an original Mars base with no weapons.','mars_surface'),
 ('on Mars','Design an original habitat on Mars.','mars_surface'),
 ('orbital','Build an original orbital habitat with an observation room.','unspecified'),
 ('Mars orbit','Build a Mars base in orbit, inside an orbital spacecraft.','unspecified'),
 ('Earth analog','Build an original Earth base. Research Mars500 analogs.','unspecified'),
 ('quoted source','The source says "Build an original Mars base". Design an orbital station.','unspecified'),
 ('quoted full command','"Build an original Mars base."','unspecified'),
 ('quoted title','Build a base titled “Mars base” inside a spacecraft.','unspecified'),
 ('negated','Do not build a Mars base.','unspecified'),
 ('ground denied','Build a Mars base, but do not add ground or exterior terrain.','unspecified'),
 ('unknown','Build a habitat with an observation room.','unspecified'),
 ('research request','Research an original Mars base.','unspecified'),
 ('near Mars','Build an original habitat near Mars.','unspecified')]
rows=[];jsCases=[]
for label,prompt,expected in cases:
 brief,packet,pin=data(prompt);value=m.presentation_setting(brief,packet,pin);assert value['setting']==expected,(label,value)
 assert 'prompt' not in json.dumps(value) and prompt not in json.dumps(value)
 rows.append({'case':label,'expected':expected,'actual':value['setting']});jsCases.append({'case':label,'presentation':value,'packet_sha256':pin})
brief,packet,pin=data(cases[0][1]);damaged=copy.deepcopy(brief);damaged['prompt']='Build an orbital habitat.'
try:m.presentation_setting(damaged,packet,pin)
except m.PreviewError:rows.append({'case':'tampered hash-bound brief','held':True})
else:raise AssertionError('Tampered brief accepted')
assert m.presentation_setting(None,None,None)['setting']=='unspecified'
rows.append({'case':'absent brief','setting':'unspecified'})
manifest={'inputs':{'research_packet':None,'backend':{'sha256':'0'*64}},'presentation_setting':m.presentation_setting(None,None,None),'presentation_source_brief':None}
assert m.verify_presentation(manifest)['setting']=='unspecified'
manifest['presentation_setting']=m.presentation_setting(brief,packet,pin)
try:m.verify_presentation(manifest)
except m.PreviewError:rows.append({'case':'claimed Mars without immutable source snapshot','held':True})
else:raise AssertionError('Unbound manifest scenery accepted')
fixture=json.loads((H/'fixtures/synthetic-habitat.json').read_bytes())
roomkeys=('id','name','purpose','x','z','width','depth','floor_y','height','dimension_basis','source_ids');portalkeys=('id','room_a','room_b','axis','coordinate','center','width','height')
compiled=[]
for title,prompt in [('Original Mars habitat','Build an original Mars base.'),('Orbital spacecraft habitat','Build an original orbital habitat with an observation room.')]:
 brief,packet,pin=data(prompt)
 bp={'contract':'dimensioned_world_blueprint_v1','research_packet_sha256':pin,'units':'meters','title':title,'entry_room_id':fixture['connectivity']['entry_room_id'],
     'rooms':[{k:r[k] for k in roomkeys} for r in fixture['rooms']],'openings':[{k:p[k] for k in portalkeys} for p in fixture['portals']]}
 g=compile_blueprint(bp,pin,'analog_to_original');g.update(functional_program=fixture['functional_program'],layout_template=fixture['layout_template'])
 result=validate_recipe_profile(g,bp,pin);assert result['eligibility_only'] is True
 compiled.append({'title':title,'geometry':g,'presentation':m.presentation_setting(brief,packet,pin),'profile':result})
 # Existing strict source schema does not claim an authoritative environment.
 invalid=copy.deepcopy(bp);invalid['environment']='mars_surface'
 try:compile_blueprint(invalid,pin,'analog_to_original')
 except BlueprintError:pass
 else:raise AssertionError('Expected strict installed blueprint schema')
put(H/'fixtures/setting-cases.json',jsCases);put(H/'fixtures/supported-layouts.json',compiled)
actual=None
if '--synthetic-only' not in sys.argv:
 job=Path('@kira_root/Data/world_research_jobs/world_research_c391ffbffc7352612392');p=job/'research_packet.json'
 actual_packet=m.load_json(m.read_exact(p));actual_brief=m.capture_presentation_brief(p);actual=m.presentation_setting(actual_brief,actual_packet,sha(p.read_bytes()))
 assert actual['setting']=='mars_surface';assert actual['source']['brief_sha256']=='c391ffbffc7352612392f65bbf3a004429c1e6bcb2ec1aa125ad0a2da289527d'
 put(H/'ACTUAL-PRESENTATION.json',actual)
put(H/'SETTING-TEST-RESULT.json',{'status':'054_BOUND_SETTING_TESTS_PASS','cases':rows,'synthetic_compatible_layouts':len(compiled),'actual_saved_brief_setting':actual,'original_brief_exported':False,'source_or_canonical_writes':False})
print(json.dumps({'status':'054_BOUND_SETTING_TESTS_PASS','cases':len(rows),'compatible_layouts':len(compiled),'actual_setting':actual['setting'] if actual else 'not_read_in_synthetic_only_test'}))
