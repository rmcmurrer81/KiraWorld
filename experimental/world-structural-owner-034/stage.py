from pathlib import Path
import hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;W=H.parent
OLDCORE=W/'world-scene-metadata-candidate-030';OLDPACKAGE=W/'world-metadata-package-candidate-031'
pins=[]
def copy(source,target):
 data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(data)
 pins.append({'path':str(source),'sha256':hashlib.sha256(data).hexdigest(),'copy':target.relative_to(H).as_posix()})
for folder in ('candidate','baseline','fixtures'):
 for source in sorted((OLDCORE/folder).rglob('*')):
  if source.is_file():copy(source,H/'core'/source.relative_to(OLDCORE))
for name in ('room_dressing_plan.mjs','test_metadata.mjs'):copy(OLDCORE/name,H/'core'/name)
core=H/'core/candidate/tools/world_builder_engine/scene_metadata.mjs'
copy(core,H/'baseline/scene_metadata.mjs')
text=core.read_text(encoding='utf-8')
old="""  const owner=nodeMap.has('node:'+c.id+'_mesh')?'node:'+c.id+'_mesh':null;
  colliders.push({id:addId('collider',c.id),owner_node_id:owner,shape:'axis_aligned_box',bounds:bounds(c),motion:'static',proxy:'source_conservative_bounds'});"""
new="""  const exact=nodeMap.get('node:'+c.id),floor=nodeMap.get('node:'+c.id+'_mesh');
  // Walls/ceilings use their exact source id. The compiler names a floor's
  // display primitive with _mesh; that alias is valid only for an actual floor.
  const owners=[exact,floor?.role==='floor'?floor:null].filter(Boolean);
  require(owners.length===1,'Missing or ambiguous structural collider owner');
  const owner=owners[0],physical=bounds(c);
  require(owner.kind==='structural_primitive'&&owner.representation.type==='existing_box_parameters',
   'Structural collider must belong to a structural primitive');
  require(sameBox(physical,box(owner.transform.position,owner.representation.size)),
   'Structural collider owner bounds mismatch');
  colliders.push({id:addId('collider',c.id),owner_node_id:owner.id,shape:'axis_aligned_box',bounds:physical,motion:'static',proxy:'source_conservative_bounds'});"""
assert text.count(old)==1;text=text.replace(old,new);core.write_text(text,encoding='utf-8',newline='\n')
for name in ('package_writer.py','render_metadata.mjs','test_package.py','make_example.py'):
 copy(OLDPACKAGE/name,H/'package'/name)
writer=H/'package/package_writer.py';writer.write_text(writer.read_text(encoding='utf-8').replace("ROOT.parent/'world-scene-metadata-030'","ROOT.parent/'core'"),encoding='utf-8',newline='\n')
example=H/'package/make_example.py';example.write_text(example.read_text(encoding='utf-8').replace("H.parent/'world-scene-metadata-030'","H.parent/'core'"),encoding='utf-8',newline='\n')
test=H/'package/test_package.py';text=test.read_text(encoding='utf-8')
text=text.replace("H.parent/'world-scene-metadata-030'","H.parent/'core'").replace("if not CORE.is_dir():CORE=H.parent/'world-scene-metadata-candidate-030'","assert CORE.is_dir(), 'Explicit reviewed core directory required'")
test.write_text(text,encoding='utf-8',newline='\n')
oldpins=json.loads((OLDPACKAGE/'CORE-PINS.json').read_bytes())
newpins={name:hashlib.sha256((H/'core'/name).read_bytes()).hexdigest() for name in oldpins}
(H/'package/CORE-PINS.json').write_text(json.dumps(newpins,indent=2)+'\n',encoding='utf-8')
patch=[]
for before,after,label in [(H/'baseline/scene_metadata.mjs',core,'scene_metadata.mjs'),(OLDPACKAGE/'package_writer.py',writer,'package_writer.py'),(OLDPACKAGE/'test_package.py',test,'test_package.py'),(OLDPACKAGE/'make_example.py',example,'make_example.py')]:
 patch.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(),after.read_text(encoding='utf-8').splitlines(),fromfile='previous/'+label,tofile='034/'+label,lineterm=''))
(H/'CHANGES.patch').write_text('\n'.join(patch)+'\n',encoding='utf-8')
# Do not pin an intermediate034 copy as a protected historical original.
pins=[p for p in pins if not Path(p['path']).is_relative_to(H)]
(H/'HISTORICAL-SOURCE-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'034_ISOLATED_SUCCESSOR_STAGED','core_sha256':newpins['candidate/tools/world_builder_engine/scene_metadata.mjs'],'historical_sources':len(pins),'installed':False}))
