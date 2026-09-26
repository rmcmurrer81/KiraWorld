import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import {buildAuthoredScene} from './candidate/tools/world_builder_engine/layout_package_assets/authored_scene.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {exportSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
import {NAVIGATION_CONTRACT,checkWalkSpawn,checkHorizontalRoute} from './candidate/tools/world_builder_engine/horizontal_navigation.mjs';
import {buildRoomDressing as mealPlan} from '../world-meal-station-candidate-059/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
const canvas=()=>({width:0,height:0,getContext:()=>new Proxy({},{get:()=>()=>{},set:()=>true})});
const close=(a,b,tol=2e-6)=>{assert.equal(a.length,b.length);a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<tol));};
const contains=(point,b)=>point.every((v,i)=>v>=b.min[i]-2e-7&&v<=b.max[i]+2e-7);
const overlaps=(a,b)=>a.min.every((v,i)=>v<b.max[i]&&a.max[i]>b.min[i]);
const configurations=['base','renamed','wider','translated'].map(name=>({name,path:new URL('./fixtures/'+name+'.json',import.meta.url)}));
if(process.argv[2])configurations.push({name:'actual_saved_mars',path:process.argv[2]});
const reports=[];let checks=0;
function checked(value,why){assert.ok(value,why);checks++;}
for(const spec of configurations){
 const g=JSON.parse(fs.readFileSync(spec.path)),before=JSON.stringify(g),consumers=[];
 for(const relative of ['walk_controller.mjs','layout_package_assets/source/walk_controller.mjs']){
  const candidate=await import(new URL('./candidate/tools/world_builder_engine/'+relative,import.meta.url));
  const baseline=await import(new URL('./preimages/tools/world_builder_engine/'+relative,import.meta.url));
  const next=candidate.createDoorSystem(g),old=baseline.createDoorSystem(g),plan=buildRoomDressing(g,next.assemblies()),priorPlan=buildRoomDressing(g,old.assemblies());
  const names=['objects','architecture','lights','signs','colliders','omitted'];
  const placementChanges=names.filter(k=>JSON.stringify(plan[k])!==JSON.stringify(priorPlan[k]));
  checked(placementChanges.length===0,'installed056 room equipment, signs and routes retain their placement');
  assert.deepEqual(mealPlan(g,next.assemblies()),mealPlan(g,old.assemblies()));checks++;
  const walker=candidate.createWalkController(g,{extraColliders:plan.colliders});checked(walker.snapshot().roomId===g.connectivity.entry_room_id,'spawn');
  for(const r of g.routes)for(const points of [r.points,[...r.points].reverse()]){
   checked(checkHorizontalRoute({...r,points},{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:[...g.colliders,...plan.colliders]}).status==='clear','authored route');
  }
  // Metadata and all physical meshes come from the actual shared authored builder.
  const portable=await import(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs',import.meta.url));
  const defs=portable.createDoorSystem(g),metadata=exportSceneMetadata(g,plan,defs.definitions(),{sceneId:'hardware_'+spec.name,sourceDigests:{geometry:'1'.repeat(64),dressing_recipe:'2'.repeat(64),door_controller:'3'.repeat(64)},doorInterlocks:defs.interlocks()});
  const built=buildAuthoredScene(g,metadata,canvas);let vertices=0,avoidedSlabBlocks=0,passages=0,poses=0;
  const hardwareMetadata=metadata.colliders.filter(c=>c.proxy==='attached_hardware_rotated_aabb');checked(hardwareMetadata.length===g.portals.length*4,'four hardware boxes per door');
  if(relative.startsWith('layout_package_assets')){
   for(const change of ['missing','size','order']){
    const bad=structuredClone(defs.definitions());
    if(change==='missing')delete bad[0].hardwareLocalBoxes;
    if(change==='size')bad[0].hardwareLocalBoxes[0].size[0]+=.01;
    if(change==='order')bad[0].hardwareLocalBoxes.reverse();
    assert.throws(()=>exportSceneMetadata(g,plan,bad,{sceneId:'bad_hardware',sourceDigests:{geometry:'1'.repeat(64)},doorInterlocks:defs.interlocks()}));checks++;
   }
  }
  for(const def of defs.definitions()){
   const portal=g.portals.find(p=>p.id===def.id),normal=portal.axis==='x'?0:2,along=normal===0?2:0;
   const sweep=next.assemblies().find(x=>x.id===def.id).swingBounds;
   const middle=normal===0?[portal.coordinate,def.hinge[1],portal.center]:[portal.center,def.hinge[1],portal.coordinate];
   let safe;for(const sign of [-1,1]){const p=[...middle];p[normal]+=sign*1.05;if(p[normal]+.34<sweep.min[normal]||p[normal]-.34>sweep.max[normal]){safe=p;break;}}
   checked(!!safe,'safe interaction position');
   for(let frame=0;frame<=8;frame++){
    if(frame===1){checked(next.toggle(def.id,safe).ok&&old.toggle(def.id,safe).ok,'open');}
    if(frame){next.advance(.05,safe);old.advance(.05,safe);}
    const actual=next.all().find(x=>x.id===def.id),was=old.all().find(x=>x.id===def.id);assert.deepEqual(actual,was);checks++;
    built.hinges.get(def.id).rotation.y=actual.angle;built.scene.updateMatrixWorld(true);
    const moving=built.hinges.get(def.id).getObjectByName('moving_'+def.id);
    const colliders=next.colliders().filter(c=>c.id.startsWith('door_'+def.id+'_')&&!['left','right','head'].some(k=>c.id.endsWith('_'+k)));
    moving.traverse(o=>{if(!o.isMesh)return;const p=o.geometry.attributes.position;
     for(let i=0;i<p.count;i++){const v=new THREE.Vector3().fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).toArray();checked(colliders.some(b=>contains(v,b)),'rendered door vertex enclosed');checked(contains(v,sweep),'all door vertices inside reserved sweep');vertices++;}
    });
    if(frame===0){
     for(const c of hardwareMetadata.filter(c=>c.id.startsWith('collider:door_'+def.id+'_'))){const actual=next.colliders().find(x=>'collider:'+x.id===c.id);close(actual.min,c.bounds.min);close(actual.max,c.bounds.max);checks++;}
     // A point 8cm off the broad slab, away from its handle, must stay free.
     // The actual square walking footprint does not overlap panels or handles.
     for(const side of [-1,1]){
      const feet=[...middle];feet[normal]+=side*(.34+.08);feet[along]-=.1;
      const nav={contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:next.colliders()};
      const leaf=actual.collider,slab={id:'uniform_depth_alternative',min:[...leaf.min],max:[...leaf.max]};slab.min[normal]=portal.coordinate-.1105;slab.max[normal]=portal.coordinate+.1105;
      const free=checkWalkSpawn(feet,nav).ok,slabBlocks=!checkWalkSpawn(feet,{...nav,colliders:[slab]}).ok;
      if(free&&slabBlocks)avoidedSlabBlocks++;
     }
    }
    if(frame===8){
     const a=[...middle],b=[...middle];a[normal]-=.7;b[normal]+=.7;
     for(const points of [[a,b],[b,a]]){checked(checkHorizontalRoute({id:'door_passage',points,avatar_radius:.34,avatar_height:1.68},{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:next.colliders()}).status==='clear','fully open doorway remains passable');passages++;}
    }
    poses++;
   }
   checked(next.toggle(def.id,safe).ok&&old.toggle(def.id,safe).ok,'close');for(let i=0;i<8;i++){next.advance(.05,safe);old.advance(.05,safe);}
   checked(next.all().find(x=>x.id===def.id).state==='closed','closed again');
  }
  checked(avoidedSlabBlocks>0,'separate boxes avoid uniform slab false blocking');
  // Retain airlock mutual exclusion including two requests in one frame.
  for(const pair of next.interlocks()){
   const chosen=pair.doorIds.map(id=>{const p=g.portals.find(p=>p.id===id),n=p.axis==='x'?0:2,sw=next.assemblies().find(x=>x.id===id).swingBounds;const m=n===0?[p.coordinate,0,p.center]:[p.center,0,p.coordinate];
    for(const side of [-1,1]){const feet=[...m];feet[n]+=side*1.05;if(feet[n]+.34<sw.min[n]||feet[n]-.34>sw.max[n])return {id,feet};}});
   checked(next.toggle(chosen[0].id,chosen[0].feet).ok,'first airlock claim');checked(!next.toggle(chosen[1].id,chosen[1].feet).ok,'same frame interlock');
  }
  consumers.push({relative,door_poses:poses,mesh_vertices_checked:vertices,forward_reverse_passages:passages,uniform_slab_false_blocks_avoided:avoidedSlabBlocks,placement_changes:placementChanges,metadata_hardware_colliders:hardwareMetadata.length});
 }
 checked(JSON.stringify(g)===before,'source geometry unchanged');reports.push({fixture:spec.name,consumers});
}
const reproduction=JSON.parse(fs.readFileSync(new URL('./REPRODUCTION.json',import.meta.url))),g=JSON.parse(fs.readFileSync(new URL('./fixtures/base.json',import.meta.url)));
for(const relative of ['walk_controller.mjs','layout_package_assets/source/walk_controller.mjs']){
 const mod=await import(new URL('./candidate/tools/world_builder_engine/'+relative,import.meta.url)),oldMod=await import(new URL('./preimages/tools/world_builder_engine/'+relative,import.meta.url)),doors=mod.createDoorSystem(g);
 for(const row of reproduction.observations.filter(r=>r.walking_allowed&&r.visible_handle_overlap)){
  checked(!checkWalkSpawn(row.feet,{contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:doors.colliders()}).ok,'previous visible handle penetration now blocked');
  const old=oldMod.createDoorSystem(g),next=mod.createDoorSystem(g),before=old.toggle(row.door_id,row.feet);
  checked(!next.toggle(row.door_id,row.feet).ok,'occupied hardware swing cannot begin');
  if(before.ok){
   const p=g.portals.find(p=>p.id===row.door_id),n=p.axis==='x'?0:2,sw=next.assemblies().find(x=>x.id===p.id).swingBounds;
   const safe=[...row.feet];safe[n]=p.coordinate+(row.feet[n]>p.coordinate?1:-1)*1.05;
   checked(next.toggle(row.door_id,safe).ok,'unoccupied hardware permits start');
   const angle=next.all().find(d=>d.id===p.id).angle;next.advance(.05,row.feet);const now=next.all().find(d=>d.id===p.id);
   checked(now.angle===angle&&now.motionHeld,'advance pauses before sweeping through visible hardware occupant');
  }
 }
}
// The pre-existing 24-door limit must remain usable with added hardware.
const maximum={rooms:Array.from({length:25},(_,i)=>({id:'room_'+i,name:'Room '+i,x:i*4,z:0,width:4,depth:4,floor_y:0,height:3,access:'walkable_layout'})),
 portals:Array.from({length:24},(_,i)=>({id:'portal_'+i,room_a:'room_'+i,room_b:'room_'+(i+1),axis:'x',coordinate:(i+1)*4,center:2,width:1.2,height:2.3,state:'open_passage'})),
 support_surfaces:[{id:'floor',min_x:0,max_x:100,min_z:0,max_z:4,y:0}],colliders:[],connectivity:{entry_room_id:'room_0'},routes:[{id:'walk',points:[[2,0,2],[3,0,2]]}]};
for(const relative of ['walk_controller.mjs','layout_package_assets/source/walk_controller.mjs']){
 const mod=await import(new URL('./candidate/tools/world_builder_engine/'+relative,import.meta.url)),doors=mod.createDoorSystem(maximum),walker=mod.createWalkController(maximum);
 checked(doors.colliders().length===192,'all 24 doors retain all eight collision parts');
 for(let i=0;i<30;i++)walker.step(.05,{forward:true});
 checked(walker.snapshot().blocked==='door_obstruction'&&walker.snapshot().feet[0]<4,'bounded batches block first closed door');
 const far={...maximum,connectivity:{entry_room_id:'room_24'},routes:[{id:'back',points:[[98,0,2],[97,0,2]]}]},farWalker=mod.createWalkController(far);
 for(let i=0;i<30;i++)farWalker.step(.05,{forward:true});
 checked(farWalker.snapshot().blocked==='door_obstruction'&&farWalker.snapshot().feet[0]>96,'second collision batch blocks last closed door');
}
const result={status:'PASS_CPU_HARDWARE_COLLISION',checks,reports,original_penetrations_blocked:reproduction.allowed_overlaps*2,canonical_or_owner_changes:false,model_gpu_ui_calls:0,rendered_visual_approval:false};
fs.writeFileSync(new URL('./TEST-RESULT.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,checks,fixtures:reports.length}));
