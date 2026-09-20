"""Original parameterized frame construction. No model imports or learned weights.

Dimensions are authored engineering choices. This demonstrates a reusable recipe,
not certified structural strength or a completed bed. Mattress/cloth are absent.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct

CONTRACT='original_bed_frame_recipe_v1'
EPS=1e-8

def require(ok,message):
    if not ok:raise ValueError(message)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()

def validate_spec(spec):
    require(set(spec)=={'name','mattress_width','mattress_length','slat_max_gap'},'Exact frame specification fields required')
    require(isinstance(spec['name'],str) and 1<=len(spec['name'])<=80,'Short authored name required')
    for key,low,high in [('mattress_width',.7,1.8),('mattress_length',1.8,2.2),('slat_max_gap',.04,.07)]:
        v=spec[key];require(type(v)in(int,float) and math.isfinite(v) and low<=v<=high,'Unsupported authored dimension: '+key)

def chamfer_box(size,bevel):
    """Closed convex mesh, generated from six faces, twelve bevels, eight corners."""
    half=[s/2 for s in size];require(0<bevel<min(half)/2,'Bevel does not fit beam')
    corners={}
    for signs in itertools.product((-1,1),repeat=3):
        for full in range(3):corners[signs,full]=[signs[i]*(half[i] if i==full else half[i]-bevel) for i in range(3)]
    faces=[]
    for axis in range(3):
        others=[i for i in range(3) if i!=axis]
        for sign in (-1,1):
            points=[]
            for a,b in ((-1,-1),(1,-1),(1,1),(-1,1)):
                signs=[0,0,0];signs[axis]=sign;signs[others[0]]=a;signs[others[1]]=b;points.append(corners[tuple(signs),axis])
            faces.append(points)
    for parallel in range(3):
        a,b=[i for i in range(3) if i!=parallel]
        for sa,sb in itertools.product((-1,1),repeat=2):
            points=[]
            for sp,full in ((-1,a),(1,a),(1,b),(-1,b)):
                signs=[0,0,0];signs[parallel]=sp;signs[a]=sa;signs[b]=sb;points.append(corners[tuple(signs),full])
            faces.append(points)
    for signs in itertools.product((-1,1),repeat=3):faces.append([corners[signs,i] for i in range(3)])
    vertices=[];normals=[];indices=[]
    for face in faces:
        def normal(points):
            a=[points[1][i]-points[0][i] for i in range(3)];b=[points[2][i]-points[0][i] for i in range(3)]
            return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        n=normal(face);center=[sum(p[i] for p in face)/len(face) for i in range(3)]
        if sum(n[i]*center[i] for i in range(3))<0:face=list(reversed(face));n=normal(face)
        length=math.sqrt(sum(v*v for v in n));require(length>EPS,'Degenerate authored face')
        n=[v/length for v in n];base=len(vertices);vertices.extend(face);normals.extend([n]*len(face))
        for i in range(1,len(face)-1):indices.extend([base,base+i,base+i+1])
    return {'vertices':vertices,'normals':normals,'indices':indices}

def box_part(ident,label,role,center,size,stage):
    return {'id':ident,'name':label,'role':role,'position':center,'size':size,'stage':stage,
            'bevel':min(.003,min(size)*.12),'material':'authored_frame_finish',
            'bounds':{'min':[center[i]-size[i]/2 for i in range(3)],'max':[center[i]+size[i]/2 for i in range(3)]}}

def flat_contact(a,b):
    """Find a nonzero plane patch on the actual chamfered main faces."""
    for axis in range(3):
        for left,right in ((a,b),(b,a)):
            plane=left['bounds']['max'][axis]
            if abs(plane-right['bounds']['min'][axis])>EPS:continue
            axes=[i for i in range(3) if i!=axis];spans=[]
            for i in axes:
                lo=max(left['bounds']['min'][i]+left['bevel'],right['bounds']['min'][i]+right['bevel'])
                hi=min(left['bounds']['max'][i]-left['bevel'],right['bounds']['max'][i]-right['bevel'])
                spans.append([lo,hi])
            if all(hi-lo>EPS for lo,hi in spans):
                return {'axis':axis,'plane':plane,'in_plane_axes':axes,'spans':spans,'area_m2':math.prod(hi-lo for lo,hi in spans)}
    return None

def build_bed_frame(spec):
    validate_spec(spec);w=spec['mattress_width'];length=spec['mattress_length']
    clearance=.02;inner_w=w+2*clearance;inner_l=length+2*clearance
    rail_t=.055;rail_h=.18;rail_bottom=.24;rail_top=rail_bottom+rail_h
    ledger_w=.035;ledger_h=.035;support_top=.365;slat_t=.020;slat_w=.08
    parts=[];relations=[]
    def add(*args):p=box_part(*args);parts.append(p);return p
    def join(child,parent,kind,description):
        require(flat_contact(child,parent) is not None,'Authored joint lacks real face contact: '+child['id']+' / '+parent['id'])
        relations.append({'child':child['id'],'parent':parent['id'],'kind':kind,'description':description,'contact':flat_contact(child,parent)})
    rails={}
    for sign,label in ((-1,'left'),(1,'right')):
        rails[label]=add(label+'_side_rail',label.title()+' side rail','side_rail',[sign*(inner_w+rail_t)/2,rail_bottom+rail_h/2,0],[rail_t,rail_h,inner_l],1)
    for sign,label in ((-1,'foot'),(1,'head')):
        rails[label]=add(label+'_end_rail',label.title()+' end rail','end_rail',[0,rail_bottom+rail_h/2,sign*(inner_l+rail_t)/2],[inner_w+2*rail_t,rail_h,rail_t],1)
        for side in ('left','right'):join(rails[side],rails[label],'butt_joint','Rail ends meet end-rail face. Rigid screwed/bonded connection is an explicit construction assumption; fasteners and strength are not simulated.')
    ledgers=[]
    for sign,label in ((-1,'left'),(1,'right')):
        p=add(label+'_slat_ledger',label.title()+' internal slat ledge','slat_ledger',[sign*(inner_w-ledger_w)/2,support_top-ledger_h/2,0],[ledger_w,ledger_h,inner_l],2)
        join(p,rails[label],'attached_ledge','Ledge rests against side rail; its top supports every slat. Connection is an authored screw/bond assumption.');ledgers.append(p)
    beam=add('center_support_rail','Longitudinal center support','center_support',[0,support_top-.12/2,0],[.055,.12,inner_l],2)
    for end in ('foot','head'):join(beam,rails[end],'end_butt_joint','Center support ends meet end rails; center feet provide direct floor support.')
    for signx,side in ((-1,'left'),(1,'right')):
        for signz,end in ((-1,'foot'),(1,'head')):
            p=add(side+'_'+end+'_leg',side.title()+' '+end+' leg','corner_leg',[signx*(inner_w+rail_t)/2,rail_bottom/2,signz*(inner_l+rail_t)/2],[.08,rail_bottom,.08],3)
            join(rails[end],p,'vertical_bearing','End rail bears on leg top; rigid fixing prevents lateral separation.')
    for sign,label in ((-1,'foot'),(1,'head')):
        height=support_top-.12
        p=add('center_'+label+'_leg','Center '+label+' support leg','center_leg',[0,height/2,sign*inner_l*.28],[.07,height,.07],3)
        join(beam,p,'vertical_bearing','Center rail bears directly on leg top.')
    # Outer slat edges match the authored mattress footprint; every gap is bounded.
    count=math.ceil((length-slat_w)/(slat_w+spec['slat_max_gap']))+1
    pitch=(length-slat_w)/(count-1)
    for i in range(count):
        p=add('slat_'+str(i+1).zfill(2),'Slat '+str(i+1),'slat',[0,support_top+slat_t/2,-length/2+slat_w/2+i*pitch],[inner_w,slat_t,slat_w],4)
        for support in [*ledgers,beam]:join(p,support,'vertical_bearing','Flat slat underside rests on side ledges and center rail; gaps are intentional mattress ventilation/support spacing.')
    recipe={'contract':CONTRACT,'name':spec['name'],'spec':dict(spec),'dimension_basis':'authored_design_not_measured_reference',
      'reference_geometry_imported':False,'imported_geometry_bytes':0,'imported_materials_or_textures':False,'model_weight_training':False,
      'construction_method':'New chamfered beam meshes computed from authored dimensions; no source-mesh copy or template asset.',
      'parts':parts,'connections':relations,'construction_order':[
        {'stage':1,'depends_on_stages':[],'name':'Assemble side and end rails','purpose':'Establish the mattress opening and four butt joints.'},
        {'stage':2,'depends_on_stages':[1],'name':'Attach ledges and center rail','purpose':'Provide continuous bearing under the slats.'},
        {'stage':3,'depends_on_stages':[2],'name':'Fit four corner feet and two center feet','purpose':'Provide floor contact below end rails and center rail.'},
        {'stage':4,'depends_on_stages':[3],'name':'Place individual slats','purpose':'Span left and right ledges with center support; preserve bounded gaps.'}],
      'mattress_interface':{'width':w,'length':length,'base_y':support_top+slat_t,'side_clearance':clearance,'end_clearance':clearance,'slat_count':count,'slat_gap':pitch-slat_w,'mattress_geometry_present':False},
      'physics':{'frame':'rigid connection graph; dynamic rigid-body and load-strength simulation not implemented','mattress':'separate next component, not built','sheet_blanket':'must be flexible cloth; not built','pillow':'must compress under head and recover; not built'},
      'acceptance':{'geometry_checks_only':True,'visual_review_passed':False,'complete_bed':False,'photorealism_verified':False,'structural_strength_certified':False,'learned_model_weights':False}}
    validate_recipe(recipe);return recipe

def validate_recipe(recipe):
    require(recipe.get('contract')==CONTRACT,'Frame contract required');validate_spec(recipe['spec'])
    parts=recipe['parts'];byid={p['id']:p for p in parts};require(len(parts)==len(byid),'Duplicate component identity')
    require(recipe['imported_geometry_bytes']==0 and recipe['reference_geometry_imported']is False,'Original construction required')
    graph={p['id']:set() for p in parts}
    for p in parts:
        require(all(math.isfinite(v)for v in p['position']+p['size']) and min(p['size'])>0,'Invalid part size')
        expected=box_part(p['id'],p['name'],p['role'],p['position'],p['size'],p['stage'])
        require(p==expected,'Part bounds, bevel or material differs from authored recipe')
        require(p['bounds']['min'][1]>=-EPS,'Part penetrates floor')
    for a,b in itertools.combinations(parts,2):
        require(not all(min(a['bounds']['max'][i],b['bounds']['max'][i])-max(a['bounds']['min'][i],b['bounds']['min'][i])>EPS for i in range(3)),'Constructed parts intersect instead of joining at their faces')
    for r in recipe['connections']:
        a=byid[r['child']];b=byid[r['parent']];contact=flat_contact(a,b)
        require(contact is not None and r['contact']==contact,'Missing or altered physical face contact')
        graph[a['id']].add(b['id']);graph[b['id']].add(a['id'])
    seen=set();todo=[parts[0]['id']]
    while todo:
        ident=todo.pop()
        if ident in seen:continue
        seen.add(ident);todo.extend(graph[ident]-seen)
    require(len(seen)==len(parts),'Disconnected constructed part')
    feet=[p for p in parts if p['role']in('corner_leg','center_leg')]
    require(len(feet)==6 and all(abs(p['bounds']['min'][1])<EPS for p in feet),'Six supported feet required')
    slats=sorted((p for p in parts if p['role']=='slat'),key=lambda p:p['position'][2]);interface=recipe['mattress_interface']
    require(len(slats)==interface['slat_count']>=2,'Slat count mismatch')
    for key in ('width','length'):require(interface[key]==recipe['spec']['mattress_'+key],'Mattress interface differs from authored specification')
    require(interface['side_clearance']==.02 and interface['end_clearance']==.02,'Authored mattress clearance changed')
    supports={'left_slat_ledger','right_slat_ledger','center_support_rail'}
    for p in slats:
        parents={r['parent']for r in recipe['connections']if r['child']==p['id'] and r['kind']=='vertical_bearing'}
        require(parents==supports,'Slat requires both side ledges and center support')
        require(abs(p['bounds']['max'][1]-interface['base_y'])<EPS,'Uneven mattress support plane')
    for a,b in zip(slats,slats[1:]):
        gap=b['bounds']['min'][2]-a['bounds']['max'][2]
        require(0<gap<=recipe['spec']['slat_max_gap']+EPS,'Unsupported mattress gap')
    require(abs(slats[0]['bounds']['min'][2]+interface['length']/2)<EPS and abs(slats[-1]['bounds']['max'][2]-interface['length']/2)<EPS,'Mattress end support mismatch')
    return {'status':'PASS','connected_parts':len(parts),'slats':len(slats),'feet':len(feet),'positive_face_contacts':len(recipe['connections'])}

def glb_bytes(recipe):
    validate_recipe(recipe);binary=bytearray();views=[];accessors=[];meshes=[];nodes=[]
    def data(values,component_type,kind,minimum=None,maximum=None):
        while len(binary)%4:binary.append(0)
        start=len(binary);fmt='f'if component_type==5126 else 'I';flat=[v for row in values for v in row] if isinstance(values[0],list)else values
        binary.extend(struct.pack('<'+fmt*len(flat),*flat));vi=len(views);views.append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start})
        a={'bufferView':vi,'componentType':component_type,'count':len(values),'type':kind}
        if minimum is not None:a['min']=minimum;a['max']=maximum
        ai=len(accessors);accessors.append(a);return ai
    for p in recipe['parts']:
        mesh=chamfer_box(p['size'],p['bevel']);half=[v/2 for v in p['size']]
        pos=data(mesh['vertices'],5126,'VEC3',[-v for v in half],half);norm=data(mesh['normals'],5126,'VEC3');idx=data(mesh['indices'],5125,'SCALAR')
        meshes.append({'name':p['name'],'primitives':[{'attributes':{'POSITION':pos,'NORMAL':norm},'indices':idx,'material':0,'mode':4}]})
        nodes.append({'name':p['name'],'translation':p['position'],'mesh':len(meshes)-1,'extras':{'part_id':p['id'],'role':p['role'],'construction_stage':p['stage'],'newly_authored_geometry':True}})
    doc={'asset':{'version':'2.0','generator':'Kira original bed frame constructor v1'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],
         'nodes':nodes,'meshes':meshes,'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(binary)}],
         'materials':[{'name':'Authored neutral wood-tone engineering finish','pbrMetallicRoughness':{'baseColorFactor':[.48,.31,.17,1],'metallicFactor':0,'roughnessFactor':.68}}],
         'extras':{'recipe_sha256':sha(canonical(recipe)),'reference_meshes_imported':False,'textures_imported':False,'complete_bed':False}}
    raw=canonical(doc)
    while len(raw)%4:raw+=b' '
    while len(binary)%4:binary.append(0)
    return struct.pack('<4sII',b'glTF',2,28+len(raw)+len(binary))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary
