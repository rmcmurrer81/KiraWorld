import os
from pathlib import Path
import copy,json,sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(os.environ.get('KIRA_TEST_ROOT',str(H.parents[1])))/'tools'))
from world_builder_engine.world_blueprint import compile_blueprint
ROOM_KEYS=('id','name','purpose','x','z','width','depth','floor_y','height','dimension_basis','source_ids')
PORTAL_KEYS=('id','room_a','room_b','axis','coordinate','center','width','height')

def build_fixture(packet_sha='2'*64,variant='base'):
 source=json.loads((H/'fixtures/synthetic_habitat.json').read_bytes());program=copy.deepcopy(source['functional_program'])
 blueprint={'contract':'dimensioned_world_blueprint_v1','research_packet_sha256':packet_sha,'units':'meters','title':'Synthetic authored habitat '+variant,
  'entry_room_id':source['connectivity']['entry_room_id'],'rooms':[{k:r[k] for k in ROOM_KEYS} for r in source['rooms']],
  'openings':[{k:p[k] for k in PORTAL_KEYS} for p in source['portals']]}
 if variant in ('renamed','ambiguous'):
  mapping={r['id']:'module_'+str(i) for i,r in enumerate(blueprint['rooms']) if r['id']!='circulation'}
  if variant=='ambiguous':mapping.update(operations='lab',laboratory='lab_annex')
  for room in blueprint['rooms']:room['id']=mapping.get(room['id'],room['id'])
  for p in blueprint['openings']:
   for key in ('room_a','room_b'):p[key]=mapping.get(p[key],p[key])
  program={mapping.get(key,key):value for key,value in program.items()};blueprint['entry_room_id']=mapping.get(blueprint['entry_room_id'],blueprint['entry_room_id'])
 if variant=='wider':
  r=next(r for r in blueprint['rooms'] if r['id']=='operations');r['x']-=1;r['width']+=1
 if variant=='translated':
  for r in blueprint['rooms']:r['x']+=11;r['z']-=7
  for p in blueprint['openings']:p['coordinate']+=11 if p['axis']=='x' else -7;p['center']+=-7 if p['axis']=='x' else 11
 geometry=compile_blueprint(blueprint,packet_sha,'analog_to_original')
 geometry.update(functional_program=program,layout_template='single_level_entry_chain_and_corridor_branches_v2')
 return blueprint,geometry
