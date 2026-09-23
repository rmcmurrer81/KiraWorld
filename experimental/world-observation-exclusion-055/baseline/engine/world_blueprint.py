"""Compile a dimensioned room layout into auditable geometry, without world writes.

This is a layout-stage candidate, not a photorealistic renderer. Research collection
does not certify visual coverage. A real-place room stays solid unless a separately
verified visual-coverage decision is supplied by the next inspection stage.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re

# Tighter than the navigation helper's 1e-8 coverage tolerance. Accepted room
# boundaries must never create a floor gap that the actual walker rejects.
EPS = 1e-9
CONTRACT = 'dimensioned_world_blueprint_v1'
MODES = {'real_place_reconstruction', 'analog_to_original'}


class BlueprintError(ValueError):
    pass


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise BlueprintError(message)


def numeric(value, name, low=-1000, high=1000):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
            name + ' must be a finite bounded number in meters')
    return float(value)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}', value), 'Invalid id')
    return value


def validate_blueprint(blueprint, packet_binding, research_mode):
    """Pure schema/topology validation; does not upgrade any source-evidence claim."""
    require(research_mode in MODES, 'Unknown research mode')
    require(isinstance(blueprint, dict) and blueprint.get('contract') == CONTRACT, 'Unknown blueprint contract')
    require(set(blueprint) == {'contract','research_packet_sha256','units','title','rooms','openings','entry_room_id'},
            'Unexpected or missing blueprint fields')
    require(blueprint['research_packet_sha256'] == packet_binding and
            isinstance(packet_binding, str) and re.fullmatch(r'[a-f0-9]{64}', packet_binding),
            'Blueprint does not bind the exact research packet')
    require(blueprint['units'] == 'meters', 'Blueprint units must be meters')
    require(isinstance(blueprint['title'], str) and 1 <= len(blueprint['title']) <= 160, 'Invalid title')
    require(isinstance(blueprint['rooms'], list) and 1 <= len(blueprint['rooms']) <= 12, 'Use 1..12 rooms per layout slice')
    rooms = {}
    for room in blueprint['rooms']:
        require(isinstance(room, dict) and set(room) ==
                {'id','name','purpose','x','z','width','depth','floor_y','height','dimension_basis','source_ids'},
                'Unexpected or missing room fields')
        rid = identifier(room['id']); require(rid not in rooms, 'Duplicate room id')
        for field in ('name','purpose'):
            require(isinstance(room[field], str) and 1 <= len(room[field]) <= 300, 'Invalid room ' + field)
        for field in ('x','z','floor_y'):
            numeric(room[field], field)
        for field in ('width','depth'):
            numeric(room[field], field, 1.2, 80)
        numeric(room['height'], 'height', 2, 20)
        require(isinstance(room['source_ids'], list) and all(isinstance(s,str) and s for s in room['source_ids']),
                'Room requires source ids list')
        if research_mode == 'analog_to_original':
            require(room['dimension_basis'] == 'original_design', 'Original dimensions must remain original design')
        else:
            require(room['dimension_basis'] in {'source_measured','source_derived','unknown'}, 'Invalid real-place dimension basis')
            if room['dimension_basis'] != 'unknown':
                require(room['source_ids'], 'Real-place dimensions need source references')
        rooms[rid] = copy.deepcopy(room)
    for index, a in enumerate(rooms.values()):
        for b in list(rooms.values())[index+1:]:
            overlap_x = min(a['x']+a['width'], b['x']+b['width']) - max(a['x'],b['x'])
            overlap_z = min(a['z']+a['depth'], b['z']+b['depth']) - max(a['z'],b['z'])
            overlap_y = min(a['floor_y']+a['height'], b['floor_y']+b['height']) - max(a['floor_y'],b['floor_y'])
            require(not (overlap_x > EPS and overlap_z > EPS and overlap_y > EPS),
                    'Room volumes overlap: ' + a['id'] + '/' + b['id'])
    require(blueprint['entry_room_id'] in rooms, 'Entry room is missing')
    require(isinstance(blueprint['openings'], list) and len(blueprint['openings']) <= 24, 'Invalid openings')
    openings = []
    seen = set()
    intervals = {}
    for opening in blueprint['openings']:
        require(isinstance(opening,dict) and set(opening) == {'id','room_a','room_b','axis','coordinate','center','width','height'},
                'Unexpected or missing opening fields')
        oid = identifier(opening['id']); require(oid not in seen, 'Duplicate opening id'); seen.add(oid)
        a = rooms.get(opening['room_a']); b = rooms.get(opening['room_b'])
        require(a is not None and b is not None and a is not b, 'Opening must connect two distinct declared rooms')
        require(a['floor_y'] == b['floor_y'], 'Vertical room connections require an explicit connector; no automatic snapping')
        require(opening['axis'] in ('x','z'), 'Opening axis must be x or z')
        for field in ('coordinate','center'):
            numeric(opening[field], field)
        width = numeric(opening['width'],'opening width',.9,8)
        height = numeric(opening['height'],'opening height',1.9,min(a['height'],b['height']))
        axis = opening['axis']; size = 'width' if axis == 'x' else 'depth'
        along = 'z' if axis == 'x' else 'x'; length = 'depth' if axis == 'x' else 'width'
        coordinate = opening['coordinate']
        sides = ((abs(a[axis]+a[size]-coordinate) <= EPS and abs(b[axis]-coordinate) <= EPS) or
                 (abs(b[axis]+b[size]-coordinate) <= EPS and abs(a[axis]-coordinate) <= EPS))
        require(sides, 'Opening is not on the shared room boundary: ' + oid)
        start, end = opening['center']-width/2, opening['center']+width/2
        low, high = max(a[along], b[along]), min(a[along]+a[length],b[along]+b[length])
        require(start >= low+.15-EPS and end <= high-.15+EPS, 'Opening exceeds shared wall or leaves no corner support')
        # Coordinates within tolerance identify the same physical shared wall.
        # Group by that wall, not by a caller's slightly different float.
        key = (tuple(sorted((a['id'],b['id']))),axis)
        for s,e in intervals.setdefault(key,[]):
            require(end <= s-EPS or start >= e+EPS, 'Openings overlap')
        intervals[key].append((start,end))
        openings.append(copy.deepcopy(opening))
    return rooms, openings


def compile_blueprint(blueprint, packet_binding, research_mode, visual_style='photorealistic', coverage_decisions=None):
    """Compile after schema checks; coverage decisions come from a separate verified inspection stage.

    At this milestone the collector has no visual inspection stage, so the caller
    passes no real-place coverage. All such rooms remain locked and solid.
    """
    rooms, openings = validate_blueprint(blueprint, packet_binding, research_mode)
    require(visual_style in {'photorealistic','cartoon','stylized','animated','hybrid'}, 'Unknown appearance target')
    coverage_decisions = coverage_decisions or {}
    require(isinstance(coverage_decisions, dict) and set(coverage_decisions) <= set(rooms), 'Unknown coverage room')
    accessible = {}
    for rid, room in rooms.items():
        if research_mode == 'analog_to_original':
            accessible[rid] = True
        else:
            decision = coverage_decisions.get(rid, {})
            require(isinstance(decision, dict), 'Invalid visual-coverage decision')
            # No ordinary caller can open a real room using this layout-only module.
            # A future version must validate decoded visual evidence before doing so.
            require(not decision or decision.get('status') == 'unknown_locked',
                    'Verified visual-evidence integration is required before opening real-place rooms')
            accessible[rid] = False
    geometry = {'contract':'compiled_blueprint_geometry_v1','research_packet_sha256':packet_binding,
                'blueprint_sha256':canonical_sha(blueprint),'title':blueprint['title'],'units':'meters',
                'visual_style_target':visual_style,'quality_status':'layout_prototype_not_visual_acceptance',
                'photorealism_verified':False,'world_ready':False,'source_facts_validated':False,
                'rooms':[], 'primitives':[],
                'colliders':[], 'support_surfaces':[], 'portals':[], 'routes':[], 'limitations':[
                    'Rectangular room layout only; visual assets/materials/lighting remain unfinished.',
                    'Real-place visual coverage and vertical connectors are not implemented in this compiler.',
                    'Open passages are not a stateful airlock or door simulation.']}
    def solid(sid, minimum, maximum, role):
        geometry['primitives'].append({'id':sid,'primitive':'box','position':[(a+b)/2 for a,b in zip(minimum,maximum)],
                                       'size':[b-a for a,b in zip(minimum,maximum)],'role':role})
        geometry['colliders'].append({'id':sid,'min':minimum,'max':maximum})
    for rid, room in rooms.items():
        x,z,w,d,y,h = (room[k] for k in ('x','z','width','depth','floor_y','height'))
        geometry['rooms'].append({**room,'access':'walkable_layout' if accessible[rid] else 'closed_locked_solid',
                                  'dimension_claim_status':'authored_design' if research_mode == 'analog_to_original'
                                  else 'unknown' if room['dimension_basis'] == 'unknown' else 'unverified_source_claim'})
        if not accessible[rid]:
            solid(rid+'_unknown',[x,y,z],[x+w,y+h,z+d],'unknown_locked_boundary')
            continue
        geometry['support_surfaces'].append({'id':rid+'_floor','min_x':x,'max_x':x+w,'min_z':z,'max_z':z+d,'y':y})
        geometry['primitives'].append({'id':rid+'_floor_mesh','primitive':'box','position':[x+w/2,y-.05,z+d/2],
                                       'size':[w,.1,d],'role':'floor'})
        solid(rid+'_ceiling',[x,y+h,z],[x+w,y+h+.1,z+d],'ceiling')
        for axis, coordinate, low, high, side in [('x',x,z,z+d,'west'),('x',x+w,z,z+d,'east'),
                                                  ('z',z,x,x+w,'south'),('z',z+d,x,x+w,'north')]:
            cuts = sorted((o['center']-o['width']/2,o['center']+o['width']/2,o['height']) for o in openings
                          if rid in (o['room_a'],o['room_b']) and o['axis']==axis and abs(o['coordinate']-coordinate)<=EPS
                          and accessible[o['room_a']] and accessible[o['room_b']])
            spans = []; cursor=low
            for start,end,door_height in cuts:
                spans.append((cursor,start,y,y+h))
                if door_height < h-EPS: spans.append((start,end,y+door_height,y+h))
                cursor=end
            spans.append((cursor,high,y,y+h))
            for index,(start,end,bottom,top) in enumerate(spans):
                if end-start <= EPS: continue
                minimum = [coordinate-.075,bottom,start] if axis=='x' else [start,bottom,coordinate-.075]
                maximum = [coordinate+.075,top,end] if axis=='x' else [end,top,coordinate+.075]
                solid(rid+'_'+side+'_'+str(index),minimum,maximum,'wall')
    graph = {rid:set() for rid in rooms if accessible[rid]}
    for opening in openings:
        clear = accessible[opening['room_a']] and accessible[opening['room_b']]
        geometry['portals'].append({**opening,'state':'open_passage' if clear else 'closed_locked_solid'})
        if clear:
            a,b = (rooms[opening[k]] for k in ('room_a','room_b'))
            graph[a['id']].add(b['id']); graph[b['id']].add(a['id'])
            centers = [[r['x']+r['width']/2,r['floor_y'],r['z']+r['depth']/2] for r in (a,b)]
            threshold = [opening['coordinate'],a['floor_y'],opening['center']] if opening['axis']=='x' else [opening['center'],a['floor_y'],opening['coordinate']]
            approaches = []
            for room in (a,b):
                point = list(threshold)
                axis = 0 if opening['axis']=='x' else 2
                center = room['x']+room['width']/2 if axis==0 else room['z']+room['depth']/2
                point[axis] += .6 if center > opening['coordinate'] else -.6
                approaches.append(point)
            geometry['routes'].append({'id':opening['id'],'avatar_radius':.34,'avatar_height':1.68,
                                       'points':[centers[0],approaches[0],threshold,approaches[1],centers[1]]})
    reached = set(); frontier=[blueprint['entry_room_id']] if blueprint['entry_room_id'] in graph else []
    while frontier:
        room = frontier.pop()
        if room in reached: continue
        reached.add(room); frontier.extend(graph[room]-reached)
    unreachable = sorted(set(graph)-reached)
    require(not unreachable, 'Accessible rooms disconnected from entry: '+', '.join(unreachable))
    geometry['connectivity'] = {'entry_room_id':blueprint['entry_room_id'],'reachable_rooms':sorted(reached),
                                'locked_rooms':sorted(r for r in rooms if not accessible[r]),'bidirectional_graph':True}
    require(len(geometry['primitives'])<=160 and len(geometry['colliders'])<=128, 'Compiled geometry exceeds prototype budget')
    return geometry
