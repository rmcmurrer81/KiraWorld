"""Create an original synthetic functional-layout fixture, without owner data."""
from pathlib import Path
import json,sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(Path.home()/'Kira/tools'))
from world_builder_engine.world_blueprint import compile_blueprint
specs=[('equipment_vestibule',-.5,-9,4,5,3),('airlock',0,-4,3,4,2.8),('operations',-5,0,5,6,3.2),('habitat',3,0,4,5,2.9),('laboratory',-4,7,4,5,3),('observation',3,7,3,4,2.7),('circulation',0,0,3,12,3.2)]
rooms=[{'id':name,'name':name.replace('_',' ').title(),'purpose':'Authored synthetic functional room for equipment/collision tests','x':x,'z':z,'width':w,'depth':d,'floor_y':0,'height':h,'dimension_basis':'original_design','source_ids':[]} for name,x,z,w,d,h in specs]
openings=[]
for a,b,axis,coordinate,center in [('equipment_vestibule','airlock','z',-4,1.5),('airlock','circulation','z',0,1.5),('operations','circulation','x',0,3),('habitat','circulation','x',3,2.5),('laboratory','circulation','x',0,9.5),('observation','circulation','x',3,9)]:
 openings.append({'id':'opening_'+str(len(openings)+1),'room_a':a,'room_b':b,'axis':axis,'coordinate':coordinate,'center':center,'width':1.2,'height':2.2})
blueprint={'contract':'dimensioned_world_blueprint_v1','research_packet_sha256':'2'*64,'units':'meters','title':'Synthetic habitat equipment fixture','entry_room_id':'equipment_vestibule','rooms':rooms,'openings':openings}
geometry=compile_blueprint(blueprint,'2'*64,'analog_to_original');geometry['functional_program']={r['id']:r['id'] for r in rooms if r['id']!='circulation'}
folder=H/'fixtures';folder.mkdir(exist_ok=False)
(folder/'synthetic_habitat.json').write_text(json.dumps(geometry,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'SYNTHETIC_FIXTURE_CREATED','rooms':len(rooms),'owner_data_read':False}))
