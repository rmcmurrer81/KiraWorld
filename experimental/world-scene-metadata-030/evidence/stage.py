from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;K=Path.home()/'Kira';W=H.parent.parent
engine=H/'candidate/tools/world_builder_engine';engine.mkdir(parents=True,exist_ok=False)
for name in ('walk_controller.mjs','horizontal_navigation.mjs'):
 source=K/'tools/world_builder_engine'/name;dest=engine/name;shutil.copyfile(source,dest)
 baseline=H/'baseline'/name;baseline.parent.mkdir(exist_ok=True);shutil.copyfile(source,baseline)
p=engine/'walk_controller.mjs';s=p.read_text(encoding='utf-8')
mark='  return freeze({contract:DOOR_CONTRACT,all,assemblies,colliders,nearest,toggle,advance});'
assert s.count(mark)==1
addition='''  // Authoring metadata only: independent of current session angles/state.
  // Export the same dimensions/hinges used by pose/collision, not inferred meshes.
  function definitions(){return freeze([...doors.values()].map(d=>freeze({
    id:d.id,portalId:d.id,roomAId:d.portal.room_a,roomBId:d.portal.room_b,
    hinge:freeze([...d.hinge]),rotationAxis:freeze([0,1,0]),closedAngle:0,openAngle:d.targetAngle,
    leafSize:freeze(d.axis==='x'?[DOOR_THICKNESS,d.height,d.width]:[d.width,d.height,DOOR_THICKNESS]),
    leafLocalCenter:freeze(d.axis==='x'?[0,.0125+d.height/2,d.width/2]:[d.width/2,.0125+d.height/2,0]),
    angularSpeed:Math.PI*1.25,maxStepSeconds:.05,interactionReach:REACH,
    frames:freeze(d.frames.map(f=>freeze({id:f.id,center:freeze([...f.center]),size:freeze([...f.size])}))),
    swingBounds:freeze({min:freeze([...d.sweep.min]),max:freeze([...d.sweep.max])}),
    collisionPolicy:'conservative_rotated_leaf_aabb_and_quarter_disc_sweep',
    initialState:'closed',statePersistence:'session_local',pressureSimulation:false
  })));}
  return freeze({contract:DOOR_CONTRACT,all,assemblies,definitions,colliders,nearest,toggle,advance});'''
p.write_text(s.replace(mark,addition),encoding='utf-8',newline='\n')
for name in ('room_dressing_plan.mjs','fixtures/synthetic_habitat.json'):
 source=W/'work/world-habitat-realism-025'/name;dest=H/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest)
print(json.dumps({'status':'030_ISOLATED_DEFINITION_EXTENSION_STAGED','canonical_changed':False,'walker_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
