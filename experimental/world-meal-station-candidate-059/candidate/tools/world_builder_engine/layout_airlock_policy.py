"""Read-only verification of exported pair policy against the selected geometry."""
PAIR_CONTRACT='paired_airlock_door_sequence_v1'

def expected_airlock_pairs(geometry):
 pairs=[]
 for room in geometry['rooms']:
  if geometry.get('functional_program',{}).get(room['id'])!='airlock':continue
  portals=[p for p in geometry['portals'] if room['id'] in (p['room_a'],p['room_b'])]
  if len(portals)!=2 or any(p['state']!='open_passage' for p in portals):raise ValueError('Airlock needs exactly two source doors')
  ids=[p['id'] for p in portals]
  if len(set(ids))!=2:raise ValueError('Airlock source doors must be distinct')
  pairs.append({'id':'airlock_pair:'+room['id'],'contract':PAIR_CONTRACT,'source_room_id':room['id'],'room_id':'room:'+room['id'],
   'door_ids':['door:'+i for i in ids],'portal_ids':ids,'leaf_node_ids':['node:door_'+i+'_leaf' for i in ids],
   'opening_policy':{'requires_peer':'closed_and_stopped','blocked_peer_conditions':['nonzero_angle','moving','nonzero_target','motion_held']},
   'closing_policy':'existing_reach_motion_and_occupancy_rules','runtime_implemented_in':'source_preview_controller_only',
   'engine_runtime_included':False,'pressure_simulation':False,'state_persistence':'session_local'})
 return pairs

def validate_airlock_metadata(scene,geometry,source_digests):
 def require(ok,message):
  if not ok:raise ValueError(message)
 require(scene.get('contract')=='world_scene_metadata_v2','Unexpected scene metadata contract')
 provenance=scene.get('provenance',{})
 require(provenance.get('door_contract')=='preview_hinged_doors_v2','Unexpected door controller contract')
 require(provenance.get('source_digests')==source_digests,'Scene controller/geometry provenance differs')
 expected=expected_airlock_pairs(geometry)
 require(scene.get('airlock_pairs')==expected,'Airlock pairing metadata differs from selected source')
 nodes=scene.get('nodes',[]);doors=scene.get('doors',[])
 require(len({n['id'] for n in nodes})==len(nodes),'Duplicate node identity')
 require(len({d['id'] for d in doors})==len(doors),'Duplicate door identity')
 node_map={n['id']:n for n in nodes};door_map={d['id']:d for d in doors}
 for pair in expected:
  for i,portal_id in enumerate(pair['portal_ids']):
   matches=[p for p in geometry['portals'] if p['id']==portal_id]
   require(len(matches)==1,'Source portal identity is ambiguous');portal=matches[0]
   door=door_map.get(pair['door_ids'][i],{})
   require(door.get('portal_id')==portal_id and door.get('room_ids')==['room:'+portal['room_a'],'room:'+portal['room_b']],'Door-to-source association differs')
   require(door.get('leaf_node_id')==pair['leaf_node_ids'][i] and node_map.get(door.get('leaf_node_id'),{}).get('kind')=='door_leaf','Airlock leaf association differs')
   colliders=[c for c in scene.get('colliders',[]) if c.get('id')=='collider:door_'+portal_id+'_leaf']
   require(len(colliders)==1 and colliders[0].get('owner_node_id')==door['leaf_node_id'] and colliders[0].get('motion')=='kinematic','Airlock collider owner differs')
 for door in doors:
  ids=[p['id'] for p in expected if door['id'] in p['door_ids']]
  require(door.get('interlock_pair_ids')==ids,'Door pair references differ')
  rules=door.get('interaction',{}).get('rules',[])
  require(('paired_airlock_peer_closed_stopped' in rules)==bool(ids),'Door opening rule differs')
 return expected
