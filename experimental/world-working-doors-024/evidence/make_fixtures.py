"""Compile four synthetic door orientations using the unchanged installed compiler."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
K=Path.home()/'Kira'
sys.path.insert(0,str(K/'tools'))
from world_builder_engine.world_blueprint import compile_blueprint
source=K/'tools/world_builder_engine/world_blueprint.py'
before=hashlib.sha256(source.read_bytes()).hexdigest()
folder=H/'fixtures';folder.mkdir(exist_ok=False)
for axis in ('x','z'):
 for sign in (-1,1):
  rooms=[]
  for name,side in [('entry',sign),('next_room',-sign)]:
   x=(-4 if side<0 else 0) if axis=='x' else -2
   z=(-4 if side<0 else 0) if axis=='z' else -2
   rooms.append({'id':name,'name':name,'purpose':'Synthetic door passage fixture','x':x,'z':z,'width':4,'depth':4,'floor_y':0,'height':3,'dimension_basis':'original_design','source_ids':[]})
  blueprint={'contract':'dimensioned_world_blueprint_v1','research_packet_sha256':'1'*64,'units':'meters','title':'Synthetic two-room door check','entry_room_id':'entry','rooms':rooms,'openings':[{'id':'opening_1','room_a':'entry','room_b':'next_room','axis':axis,'coordinate':0,'center':0,'width':1.2,'height':2.2}]}
  geometry=compile_blueprint(blueprint,'1'*64,'analog_to_original')
  (folder/(axis+('_negative' if sign<0 else '_positive')+'.json')).write_text(json.dumps(geometry,indent=2)+'\n',encoding='utf-8')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print(json.dumps({'fixtures':4,'compiler_unchanged':True,'compiler_sha256':before,'owner_files_written':False}))
