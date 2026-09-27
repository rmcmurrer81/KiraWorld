"""Narrow eligibility to attempt the exact authored habitat export recipe.

This replaces fixture identity with independently recompiled structural data.
Eligibility is not export success; the pinned builder/importer must still pass.
"""
from pathlib import Path
import hashlib
from .world_blueprint import compile_blueprint
PROFILE='bounded_authored_habitat_export_v1'
ROLES={'equipment_vestibule','airlock','operations','habitat','laboratory','observation','circulation'}
STRUCTURE=('contract','units','title','research_packet_sha256','blueprint_sha256','rooms','primitives','colliders','support_surfaces','portals','routes','connectivity',
 'quality_status','photorealism_verified','world_ready','source_facts_validated')

class RecipeUnsupported(ValueError):
 def __init__(self,status,message):super().__init__(message);self.status=status

def validate_recipe_profile(geometry,blueprint,packet_sha256):
 def need(ok,status,message):
  if not ok:raise RecipeUnsupported(status,message)
 need(geometry.get('layout_template')=='single_level_entry_chain_and_corridor_branches_v2','unsupported_layout','Export supports only the authored single-level habitat layout template.')
 rooms=geometry.get('rooms',[]);program=geometry.get('functional_program')
 need(isinstance(program,dict) and bool(program) and 5<=len(rooms)<=9,'unsupported_recipe','Export needs5..9 declared rooms and an explicit supported habitat room program.')
 ids={r['id'] for r in rooms}
 need(set(program)<=ids and all((program.get(r['id']) or ('circulation' if r['id']=='circulation' else None)) in ROLES for r in rooms),
  'unsupported_recipe','Every room must explicitly use a supported habitat role. Unknown or unrelated room programs are preserved but not exported.')
 need(all(r['access']=='walkable_layout' and r['floor_y']==0 and 2.5<=r['height']<=4 for r in rooms),
  'unsupported_layout','Export supports fully authored walkable rooms on one ground level,2.5..4m high. Locked or vertical layouts are unsupported.')
 for room in rooms:
  corridor=(program.get(room['id']) or ('circulation' if room['id']=='circulation' else None))=='circulation'
  need(3<=room['width']<=12 and 3<=room['depth']<=(80 if corridor else 12),'unsupported_layout','Room dimensions exceed the bounded authored habitat recipe.')
 try:rebuilt=compile_blueprint(blueprint,packet_sha256,'analog_to_original')
 except (ValueError,KeyError,TypeError) as exc:raise RecipeUnsupported('unsupported_layout','The bound blueprint could not be independently recompiled.') from exc
 need(all(geometry.get(key)==rebuilt.get(key) for key in STRUCTURE),'unsupported_layout','The saved geometry differs from its bound blueprint. It was preserved; export was not started.')
 corridors=[r['id'] for r in rooms if (program.get(r['id']) or ('circulation' if r['id']=='circulation' else None))=='circulation']
 need(corridors==['circulation'],'unsupported_layout','The supported branch template needs one explicit circulation corridor.')
 graph={rid:set() for rid in ids};edges=set()
 for p in geometry['portals']:
  graph[p['room_a']].add(p['room_b']);graph[p['room_b']].add(p['room_a']);edges.add(frozenset((p['room_a'],p['room_b'])))
 entry=geometry['connectivity']['entry_room_id'];chain=[];previous=None;cursor=entry
 while cursor!='circulation':
  need(cursor not in chain and len(chain)<2,'unsupported_layout','Entry chain exceeds the supported two-room sequence.')
  chain.append(cursor);forward=graph[cursor]-({previous} if previous else set())
  need(len(forward)==1,'unsupported_layout','Entry sequence branches before its circulation corridor.')
  previous,cursor=cursor,next(iter(forward))
 expected={frozenset((a,b)) for a,b in zip(chain+['circulation'],(chain+['circulation'])[1:])}
 expected.update(frozenset((rid,'circulation')) for rid in ids-set(chain)-{'circulation'})
 need(edges==expected and len(edges)==len(geometry['portals']),'unsupported_layout','Openings differ from the supported entry-chain and corridor-branch topology.')
 # The installed renderer finds room ownership by prefix. Reject ambiguity,
 # rather than assigning another room's style/group by list order.
 for primitive in geometry['primitives']:
  owners=[r['id'] for r in rooms if primitive['id'].startswith(r['id']+'_')]
  need(len(owners)==1,'unsupported_layout','Structural room identity is ambiguous for this renderer. Use an explicitly supported room naming scheme.')
 airlocks=[r for r in rooms if program.get(r['id'])=='airlock']
 for room in airlocks:
  attached=[p for p in geometry['portals'] if room['id'] in (p['room_a'],p['room_b'])]
  need(len(attached)==2 and all(p['state']=='open_passage' for p in attached),'unsupported_layout','Each authored airlock must have exactly two open source portals.')
 return {'contract':PROFILE,'room_count':len(rooms),'source_structure_recompiled':True,'explicit_supported_roles':True,
  'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'blueprint_compiler_sha256':hashlib.sha256(Path(compile_blueprint.__code__.co_filename).read_bytes()).hexdigest(),
  'unambiguous_structural_room_ownership':True,'airlock_count':len(airlocks),'eligibility_only':True,
  'export_requires_pinned_builder_and_importer_pass':True,'visual_or_owner_approval':False,'engine_or_vr_runtime':False}
