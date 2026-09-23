"""Isolate an endpoint-based eligibility experiment against installed015."""
from pathlib import Path
import hashlib
import json
import difflib

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
SOURCE=Path('@user_home/Kira/tools/world_builder_components/bedding')
NAMES=['bedding_base.mjs','frame_contacts.mjs','mattress_physics.mjs','surface_contacts.mjs']
pins=[]
for name in NAMES:
    data=(SOURCE/name).read_bytes()
    for group in ['baseline','candidate']:
        path=HERE/group/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
    pins.append({'path':str(SOURCE/name),'name':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})

surface=HERE/'candidate/surface_contacts.mjs'
text=surface.read_text(encoding='utf-8')
helper='''// A one-sided top surface cannot support an entire primitive that is below
// the fixed mattress bottom at both physical-step endpoints. A top-to-bottom
// crossing or a mixed edge/triangle remains eligible for the original response.
// This does not certify unobserved intermediate constraint paths or provide a
// bottom/side collision response. The mattress solver owns a fixed bottom and
// clamps its top above that bottom before these contact queries.
export function belowFixedBottomAtBothEndpoints(cloth,surface,ids,margin){
 const skin=cloth.margin,base=surface.base,previous=cloth.prev,current=cloth.p;
 if(!Number.isFinite(base)||!Number.isFinite(skin)||skin<0||!Number.isFinite(margin)||margin<0||margin>skin||!previous||previous.length!==current.length||!ids.length)return false;
 const boundary=base-skin-1e-8;
 for(const id of ids){
  if(!Number.isInteger(id)||id<0||id>=cloth.count)return false;
  const k=3*id;
  for(let axis=0;axis<3;axis++)if(!Number.isFinite(current[k+axis])||!Number.isFinite(previous[k+axis]))return false;
  if(current[k+1]>=boundary||previous[k+1]>=boundary)return false;
 }
 return true;
}
'''
text=text.replace('const caches=new WeakMap();','const caches=new WeakMap();\n'+helper)
text=text.replace('function edgeContact(cloth,surface,a,b,margin){','function edgeContact(cloth,surface,a,b,margin){\n if(belowFixedBottomAtBothEndpoints(cloth,surface,[a,b],margin))return null;')
text=text.replace('function interiorContact(cloth,surface,ids,margin){','function interiorContact(cloth,surface,ids,margin){\n if(belowFixedBottomAtBothEndpoints(cloth,surface,ids,margin))return null;')
text=text.replace('for(const c of current.values()){','for(const c of current.values()){\n  if(belowFixedBottomAtBothEndpoints(cloth,surface,c.ids,cloth.margin))continue;')
surface.write_text(text,encoding='utf-8',newline='\n')
mattress=HERE/'candidate/mattress_physics.mjs';text=mattress.read_text(encoding='utf-8')
text=text.replace('solveSurfaceContacts,surfaceContactReport,finishSurfaceContactVelocities}', 'solveSurfaceContacts,surfaceContactReport,finishSurfaceContactVelocities,belowFixedBottomAtBothEndpoints}')
text=text.replace("upper-surface height-field barrier extends down to the floor within its footprint; under-mattress cloth routing is not supported", "one-sided upper barrier excludes primitives below fixed bottom at both physical-step endpoints; intermediate constraint paths and underside/side response remain unsupported")
text=text.replace('if(inside){','if(inside&&!belowFixedBottomAtBothEndpoints(c,surface,[i],m)){')
mattress.write_text(text,encoding='utf-8',newline='\n')
parts=[]
for name in NAMES:
    a=(HERE/'baseline'/name).read_text(encoding='utf-8').splitlines()
    b=(HERE/'candidate'/name).read_text(encoding='utf-8').splitlines()
    parts.extend(difflib.unified_diff(a,b,fromfile='installed015/'+name,tofile='candidate033/'+name,lineterm=''))
(HERE/'CHANGES.normalized.patch').write_text('\n'.join(parts)+'\n',encoding='utf-8')
fixture=WORK/'world-frame-contact-perf-candidate/fixtures/wide.json'
(HERE/'wide.json').write_bytes(fixture.read_bytes())
plan={'status':'ISOLATED_EXPERIMENT_NOT_INSTALLABLE_YET','sources':pins,'installed':False,
      'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
      'budget':{'one_node_process':True,'heap_mib':384,'wall_seconds':30,'gpu':False},
      'limitations':['Only a current/physical-previous endpoint rule; no intermediate solver history certificate.',
                     'No underside or side collision response; known fixed-bottom mattress solver only.',
                     'No physics/visual/owner acceptance.']}
(HERE/'PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':plan['status'],'candidate_files_changed':2}))
