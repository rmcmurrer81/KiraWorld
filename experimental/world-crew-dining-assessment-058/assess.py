"""Read-only gap/clearance proposal against actual exported saved Mars layout."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
package=W/'world-installed-observation-export-057/actual-001/package/scene.json'
scene=load(package);closure=load(W/'world-installed-observation-export-057/INSTALLED-SOURCE-CLOSURE.json')
plan=load(W/'world-observation-trim-056/native-successor-001/INSTALL-PLAN.json')
for rel,row in closure.items():assert sha(K/rel)==row['sha256']
for name,digest in plan['protected_inputs'].items():assert sha(Path(name))==digest
room=next(r for r in scene['rooms'] if r['id']=='room:habitat')
items=[n for n in scene['nodes'] if n.get('room_id')==room['id'] and n.get('behavior')=='static_visual_equipment']
assert {n['kind'] for n in items}=={'bunk','galley','personal_storage'}
# Dimensions are a provisional original furniture design, not an ergonomic standard.
proposal={'min':[5.5,0,.2],'max':[6.8,1.04,1.5]}
def overlap(a,b,pad=0):return all(a['min'][i]<b['max'][i]+pad and a['max'][i]>b['min'][i]-pad for i in range(3))
def segment_hit(a,b,box,radius=.49,height=1.68):
    if min(a[1],b[1])+height<=box['min'][1] or min(a[1],b[1])>=box['max'][1]:return False
    low,high=0.,1.
    for axis in (0,2):
        lo=box['min'][axis]-radius;hi=box['max'][axis]+radius;d=b[axis]-a[axis]
        if abs(d)<1e-12:
            if a[axis]<lo or a[axis]>hi:return False
        else:
            x,y=(lo-a[axis])/d,(hi-a[axis])/d
            if x>y:x,y=y,x
            low=max(low,x);high=min(high,y)
            if low>high:return False
    return True
assert all(proposal['min'][i]>=room['bounds']['min'][i] and proposal['max'][i]<=room['bounds']['max'][i] for i in range(3))
object_hits=[n['id'] for n in items if overlap(proposal,n['bounds'],.08)]
collider_hits=[c['id'] for c in scene['colliders'] if overlap(proposal,c['bounds'])]
swing_hits=[d['id'] for d in scene['doors'] if overlap(proposal,d['swing_bounds'],.08)]
route_hits=[r['id'] for r in scene['navigation']['authored_routes'] if any(segment_hit(a,b,proposal) for a,b in zip(r['points'],r['points'][1:]))]
approach=[[5,0,2.5],[6.1,0,2.05]]
approach_hits=[c['id'] for c in scene['colliders'] if segment_hit(*approach,c['bounds'],radius=.34)]
assert not any((object_hits,collider_hits,swing_hits,route_hits,approach_hits))
assert not segment_hit(*approach,proposal,radius=.34)
for rel,row in closure.items():assert sha(K/rel)==row['sha256']
for name,digest in plan['protected_inputs'].items():assert sha(Path(name))==digest
result={'status':'READ_ONLY058_CONCRETE_DINING_GAP_WITH_PROVISIONAL_CLEARANCE','source_scene_sha256':sha(package),
    'installed_source_files_unchanged':len(closure),'owner_originals_unchanged':len(plan['protected_inputs']),
    'existing_room_dimensions_m':[4,2.9,5],'existing_equipment_kinds':[n['kind'] for n in items],
    'gap':'No dining surface or crew eating seat in the actual saved habitat room; galley cabinet, bunk and storage are present.',
    'proposed_assembly':'One original static two-seat meal station, with recognizable table, support and padded bench geometry.',
    'provisional_bounds_m':proposal,'dimensions_m':[1.3,1.04,1.3],
    'checks':{'existing_equipment_hits_padded_08m':object_hits,'solid_collider_hits':collider_hits,'door_swing_hits_padded_08m':swing_hits,
    'authored_route_hits_padded_49m':route_hits,'standing_approach_hits_radius_34m':approach_hits,'standing_approach':approach},
    'preserve':['All existing equipment placements and stable IDs','All doors, airlock policy and immutable old previews','Original room/wall geometry','Shared preview/export assembly and matching new collider metadata'],
    'implementation_recommendation':'Append optional habitat equipment after existing3 items; use existing general clearance placement and omit explicitly when no room is safe. Do not hardcode the saved fixture coordinates.',
    'not_done':['No furniture code or metadata schema changed','No preview or export was regenerated','No native/renderer view or model run','No sitting interaction or comfort/ergonomic validation','No photorealism or owner approval'],
    'evidence_limits':'Provisional conservative box and standing approach fit this actual saved layout numerically; final authored meshes, visibility and usable placement still need independent tests and visual inspection.'}
with (H/'ASSESSMENT.json').open('xb') as f:f.write((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k in ('status','gap','checks','installed_source_files_unchanged','owner_originals_unchanged')}))
