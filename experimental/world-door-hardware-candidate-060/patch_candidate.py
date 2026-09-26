from pathlib import Path
import json,hashlib,difflib
H=Path(__file__).resolve().parent;C=H/'candidate/tools/world_builder_engine';P=H/'preimages/tools/world_builder_engine'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helper='''  // Local boxes enclose the rendered panels and each handle with its mounts.
  // Keep these separate: a full-depth slab would block empty space elsewhere.
  function hardwareBoxes(door){
    const normal=door.axis==='x'?0:2,along=normal===0?2:0,parts=[];
    for(const side of [-1,1]){
      const panelCenter=[0,0,0],panelSize=[0,door.height*.68,0];
      panelCenter[normal]=side*(DOOR_THICKNESS/2+.005);
      panelSize[normal]=.008;panelSize[along]=door.width*.77;
      parts.push({part:'panel_'+(side<0?'negative':'positive'),center:panelCenter,size:panelSize});
      // Mount normal extent .031..096; handle extent .0645..1105.
      const center=[0,-.12,0],size=[0,.27,0];
      center[normal]=side*.07075;center[along]=door.width*.34;
      size[normal]=.0795;size[along]=.075;
      parts.push({part:'handle_'+(side<0?'negative':'positive'),center,size});
    }
    return parts;
  }
  function hardwareColliders(door){
    const pose=poseOf(door),c=Math.cos(door.angle),s=Math.sin(door.angle);
    return hardwareBoxes(door).map(part=>{
      const p=part.center,z=part.size;
      const center=[pose.center[0]+c*p[0]+s*p[2],pose.center[1]+p[1],pose.center[2]-s*p[0]+c*p[2]];
      const size=[Math.abs(c)*z[0]+Math.abs(s)*z[2],z[1],Math.abs(s)*z[0]+Math.abs(c)*z[2]];
      return {id:'door_'+door.id+'_'+part.part,...bounds(center,size)};
    });
  }
'''
for rel in ('walk_controller.mjs','layout_package_assets/source/walk_controller.mjs'):
 p=C/rel;t=p.read_text(encoding='utf-8');marker='  function all(){';assert t.count(marker)==1;t=t.replace(marker,helper+marker)
 t=t.replace('const extent=door.width+DOOR_THICKNESS/2;','const hardwareHalfDepth=.1105;\n    // Hardware sits at .84 leaf-width from the hinge, so its outer radial\n    // reach is smaller than the leaf sweep. Do not pad the far jamb again.\n    const extent=Math.max(door.width+DOOR_THICKNESS/2,Math.hypot(door.width*.84+.0375,hardwareHalfDepth));')
 t=t.replace('hinge[0]-DOOR_THICKNESS/2,a.floor_y,hinge[2]-DOOR_THICKNESS/2','hinge[0]-hardwareHalfDepth,a.floor_y,hinge[2]-hardwareHalfDepth')
 t=t.replace('hinge[0]+DOOR_THICKNESS/2,a.floor_y+height,hinge[2]+DOOR_THICKNESS/2','hinge[0]+hardwareHalfDepth,a.floor_y+height,hinge[2]+hardwareHalfDepth')
 old='poseOf(d).collider]);}';assert t.count(old)==1;t=t.replace(old,'poseOf(d).collider,...hardwareColliders(d)]);}')
 old="  const doorNav=()=>({contract:NAVIGATION_CONTRACT,support_surfaces:geometry.support_surfaces,colliders:doors.colliders()});";assert t.count(old)==1
 t=t.replace(old,"""  // Navigation admits 128 colliders per check. Keep all 24 supported doors,
  // including attached hardware, without dropping parts or raising that bound.
  const doorScenes=()=>{
    const colliders=doors.colliders(),scenes=[];
    for(let i=0;i<colliders.length;i+=128)scenes.push({contract:NAVIGATION_CONTRACT,support_surfaces:geometry.support_surfaces,colliders:colliders.slice(i,i+128)});
    return scenes;
  };""")
 old="  if(!checkWalkSpawn(feet,doorNav(),AVATAR.radius,AVATAR.height).ok)throw new Error('Entry position intersects a door assembly.');";assert t.count(old)==1
 t=t.replace(old,"  if(doorScenes().some(nav=>!checkWalkSpawn(feet,nav,AVATAR.radius,AVATAR.height).ok))throw new Error('Entry position intersects a door assembly.');")
 old="      result=checkHorizontalRoute(route,doorNav());";assert t.count(old)==1
 t=t.replace(old,"      for(const scene of doorScenes()){result=checkHorizontalRoute(route,scene);if(result.status!=='clear')break;}")
 if 'source/' in rel:
  old="    collisionPolicy:'conservative_rotated_leaf_aabb_and_quarter_disc_sweep',";assert t.count(old)==1
  t=t.replace(old,"    hardwareLocalBoxes:freeze(hardwareBoxes(d).map(p=>freeze({part:p.part,center:freeze([...p.center]),size:freeze([...p.size])}))),\n"+old)
 p.write_text(t,encoding='utf-8',newline='\n')
p=C/'layout_package_assets/source/scene_metadata.mjs';t=p.read_text(encoding='utf-8')
old="  const frames=list(d.frames,3).map(f=>{";assert t.count(old)==1
extra='''  // Attached hardware shares the leaf hinge but has distinct local boxes;
  // do not inflate the entire door into a slab or omit visible handle volume.
  const hardware=list(d.hardwareLocalBoxes,4);require(hardware.length===4,'Missing door hardware collision boxes');
  const expected=[];
  for(const side of [-1,1]){
    const pc=[0,0,0],ps=[0,leafSize[1]*.68,0];pc[axis]=side*(.065/2+.005);ps[axis]=.008;ps[tangent]=leafSize[tangent]*.77;
    expected.push({part:'panel_'+(side<0?'negative':'positive'),center:pc,size:ps});
    const hc=[0,-.12,0],hs=[0,.27,0];hc[axis]=side*.07075;hc[tangent]=leafSize[tangent]*.34;hs[axis]=.0795;hs[tangent]=.075;
    expected.push({part:'handle_'+(side<0?'negative':'positive'),center:hc,size:hs});
  }
  hardware.forEach((part,index)=>{
    const wanted=expected[index];require(part.part===wanted.part&&equal(vector(part.center),wanted.center)&&equal(size(part.size),wanted.size),'Door hardware differs from rendered assembly');
    const offset=vector(part.center),dimensions=size(part.size);
    colliders.push({id:addId('collider','door_'+d.id+'_'+part.part),owner_node_id:leafId,shape:'axis_aligned_box',
      bounds:box(initial.map((v,i)=>v+offset[i]),dimensions),motion:'kinematic',proxy:'attached_hardware_rotated_aabb',
      leaf_local_center:offset,local_size:dimensions});
  });
'''
t=t.replace(old,extra+old);p.write_text(t,encoding='utf-8',newline='\n')
p=C/'layout_package_assets/PRODUCER-PINS.json';pins=json.loads(p.read_bytes())
for rel in ('source/walk_controller.mjs','source/scene_metadata.mjs'):
 q=C/'layout_package_assets'/rel;pins['files'][rel]={'sha256':sha(q),'bytes':q.stat().st_size}
p.write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
p=C/'layout_package_export.py';t=p.read_text(encoding='utf-8');before=sha(P/'walk_controller.mjs');assert t.count(before)==1
p.write_text(t.replace(before,sha(C/'walk_controller.mjs')),encoding='utf-8',newline='\n')
changed=[p.relative_to(C).as_posix() for p in C.rglob('*') if p.is_file() and sha(p)!=sha(P/p.relative_to(C))]
diff=[]
for rel in changed:diff.extend(difflib.unified_diff((P/rel).read_text().splitlines(True),(C/rel).read_text().splitlines(True),fromfile='installed056/'+rel,tofile='candidate060/'+rel))
(H/'SOURCE.diff').write_text(''.join(diff),encoding='utf-8')
(H/'CANDIDATE-CLOSURE.json').write_text(json.dumps({p.relative_to(H/'candidate').as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in C.rglob('*') if p.is_file()},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed_files':changed}))
