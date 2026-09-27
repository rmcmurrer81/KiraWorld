import {buildPressureHatch} from './pressure_hatch.mjs';
import {buildHatchStructuralMesh,planHatchArchitecture} from './pressure_hatch_architecture.mjs';
import * as THREE from './three.module.js';
import {AVATAR,createWalkController,createDoorSystem} from './walk_controller.mjs';

import {greenhouseEnvelopeFor,createGreenhouseScenario,createGreenhouseAssets,buildGreenhouseEnvelope,buildHydroponicBed,buildNutrientReservoir,buildGreenhousePipe,setGreenhouseShade,createGreenhouseShadeController} from './greenhouse.mjs';
import {MARS_REFERENCE} from './mars_reference.mjs';
import {createRoomMonitorData,paintRoomMonitor,createRoomMonitorMaterial} from './room_monitors.mjs';
// Authored equipment, not a reconstruction or a pressure/life-support model.
const DRESSING_CONTRACT='authored_habitat_equipment_plan_v1';
const DR_ROLES={
  equipment_vestibule:{accent:'#c99158',floor:'#48535a',light:0xe3eff4,equipment:[['eva_lockers',1.45,.62,2.15],['gear_bench',1.3,.55,.62],['hose_station',.65,.4,1.6]]},
  airlock:{accent:'#c9af69',floor:'#46545a',light:0xeaf5ff,equipment:[['airlock_control',.72,.36,1.82],['filter_cylinders',.66,.45,1.68]]},
  operations:{accent:'#739aae',floor:'#414c59',light:0xdcecff,equipment:[['operations_console',1.9,1.38,1.52],['server_rack',.66,.65,2.12],['operations_console',1.55,1.38,1.52]]},
  habitat:{accent:'#c5a985',floor:'#686354',light:0xffdfb5,equipment:[['bunk',2.08,.9,2.12],['galley',1.42,.68,1.74],['personal_storage',.72,.6,1.86]]},
  laboratory:{accent:'#81b6b1',floor:'#536568',light:0xedfffa,equipment:[['glovebox',1.58,.8,1.9],['science_bench',1.52,.76,1.52],['sample_storage',.66,.52,1.88]]},
  observation:{accent:'#a5b993',floor:'#555f54',light:0xffe8c7,equipment:[['observation_seat',1.26,.78,1.08],['growing_rack',1.18,.59,1.9]]},
  greenhouse:{accent:'#92b27c',floor:'#546c5b',light:0xf0f5d5,equipment:[['hydroponic_bed',1.8,.92,1.28],['hydroponic_bed',1.8,.92,1.28],['hydroponic_bed',1.8,.92,1.28],['hydroponic_bed',1.8,.92,1.28],['nutrient_reservoir',1.2,.75,1.95]]},
  circulation:{accent:'#acbac0',floor:'#4c565d',light:0xe5f0ff,equipment:[]}
};
function DR_assert(ok,message){if(!ok)throw new TypeError(message);}
function DR_box(center,size){return {min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)};}
function DR_overlap(a,b,pad=0){return a.min.every((v,i)=>v<b.max[i]+pad&&a.max[i]>b.min[i]-pad);}
function DR_routeHits(route,box,padding=.49){
  for(let n=1;n<route.points.length;n++){
    const a=route.points[n-1],b=route.points[n];
    if(a[1]+1.68<=box.min[1]||a[1]>=box.max[1])continue;
    let lo=0,hi=1;
    for(const axis of [0,2]){
      const d=b[axis]-a[axis],low=box.min[axis]-padding,high=box.max[axis]+padding;
      if(Math.abs(d)<1e-12){if(a[axis]<low||a[axis]>high){lo=2;break;}}
      else{let u=(low-a[axis])/d,v=(high-a[axis])/d;if(u>v)[u,v]=[v,u];lo=Math.max(lo,u);hi=Math.min(hi,v);}
    }
    if(lo<=hi)return true;
  }
  return false;
}
function DR_freeze(value){if(value&&typeof value==='object'){for(const v of Object.values(value))DR_freeze(v);Object.freeze(value);}return value;}
function buildRoomDressing(geometry,doorAssemblies=[]){
  DR_assert(Array.isArray(geometry.rooms)&&Array.isArray(geometry.routes),'Missing room layout');
  const program=geometry.functional_program||{},known=Object.values(program).some(role=>role in DR_ROLES);
  const plan={contract:DRESSING_CONTRACT,enabled:known,objects:[],architecture:[],lights:[],signs:[],colliders:[],roomStyles:{},omitted:[],
    limitations:['Authored original habitat equipment inspired by room functions; not a measured reconstruction.','Equipment is visual/static; no working science, medical or life-support systems.','Appearance requires visual review; no photorealism claim.']};
  if(!known)return DR_freeze(plan);
  const sweeps=doorAssemblies.map(d=>d.swingBounds),occupied=[];
  const entry=geometry.rooms.find(r=>r.id===geometry.connectivity.entry_room_id);
  const spawn={min:[entry.x+entry.width/2-.6,entry.floor_y,entry.z+entry.depth/2-.6],max:[entry.x+entry.width/2+.6,entry.floor_y+1.8,entry.z+entry.depth/2+.6]};
  function clear(room,box,{routes=true,objects=true}={}){
    if(box.min[0]<room.x+.09||box.max[0]>room.x+room.width-.09||box.min[2]<room.z+.09||box.max[2]>room.z+room.depth-.09||box.min[1]<room.floor_y-1e-8||box.max[1]>room.floor_y+room.height+.01)return false;
    if(DR_overlap(box,spawn)||sweeps.some(s=>DR_overlap(box,s,.08)))return false;
    if(routes&&geometry.routes.some(r=>DR_routeHits(r,box)))return false;
    if(objects&&occupied.some(b=>DR_overlap(box,b,.08)))return false;
    return true;
  }
  function addCollider(id,box){DR_assert(plan.colliders.length<128,'Habitat collision budget exceeded');plan.colliders.push({id,min:[...box.min],max:[...box.max]});occupied.push(box);}
  function wallPlacement(room,w,d,h,wall,along){
    const inset=.2,half=w/2,span=wall==='north'||wall==='south'?room.width:room.depth;
    if(span<w+2*inset)return null;
    const coordinate=inset+half+along*(span-w-2*inset);
    let center,yaw,size;
    if(wall==='south'){center=[room.x+coordinate,room.floor_y+h/2,room.z+inset+d/2];yaw=0;size=[w,h,d];}
    if(wall==='north'){center=[room.x+coordinate,room.floor_y+h/2,room.z+room.depth-inset-d/2];yaw=Math.PI;size=[w,h,d];}
    if(wall==='west'){center=[room.x+inset+d/2,room.floor_y+h/2,room.z+coordinate];yaw=Math.PI/2;size=[d,h,w];}
    if(wall==='east'){center=[room.x+room.width-inset-d/2,room.floor_y+h/2,room.z+coordinate];yaw=-Math.PI/2;size=[d,h,w];}
    return {center,yaw,size,box:DR_box(center,size)};
  }
  for(const room of geometry.rooms){
    if(room.access!=='walkable_layout')continue;
    const role=program[room.id]||(room.id==='circulation'?'circulation':null),style=DR_ROLES[role];
    if(!style)continue;
    plan.roomStyles[room.id]={role,accent:style.accent,floor:style.floor};
    let objectIndex=0;
    for(const [kind,w,d,h] of style.equipment){
      let chosen=null;
      // Alternate preferred sides so each function acquires a usable workspace,
      // not a row of identical boxes down the room's center.
      const walls=objectIndex%2?['south','east','west','north']:['north','west','east','south'];
      for(const wall of walls){
        for(const along of [.18,.82,.5,0,1]){
          const p=wallPlacement(room,w,d,h,wall,along);
          if(p&&clear(room,p.box)){chosen=p;break;}
        }
        if(chosen)break;
      }
      const id='equipment_'+room.id+'_'+objectIndex++;
      if(chosen){plan.objects.push({id,room_id:room.id,kind,role,localSize:[w,h,d],center:chosen.center,yaw:chosen.yaw,bounds:chosen.box});addCollider(id,chosen.box);}
      else plan.omitted.push({room_id:room.id,kind,reason:'No placement preserving walking routes, entry, door sweep and equipment clearances.'});
    }
    // Wall ribs are real shallow solids; their bounds join the walker collision
    // scene. Door cuts, reserved approaches and equipment remain unobstructed.
    for(const wall of ['north','south','west','east']){
      const span=wall==='north'||wall==='south'?room.width:room.depth;
      const count=Math.max(1,Math.min(4,Math.floor(span/2.6)));
      for(let i=0;i<count;i++){
        const p=wallPlacement(room,.065,.15,(role==='greenhouse'?2.4:room.height)-.12,wall,(i+.5)/count);
        if(!p)continue;
        // Move ribs close to the inner wall face instead of furniture setback.
        const axis=wall==='north'||wall==='south'?2:0;
        p.center[axis]+=(wall==='north'||wall==='east'?.1:-.1);p.box=DR_box(p.center,p.size);
        if(clear(room,p.box)){
          const id='rib_'+room.id+'_'+wall+'_'+i;
          plan.architecture.push({id,kind:'rib',room_id:room.id,center:p.center,size:p.size,yaw:p.yaw,bounds:p.box});addCollider(id,p.box);
        }
      }
    }
    // Ceiling luminaires remain well above the avatar; one local task light per
    // room makes illumination legible without a bank of global shadow maps.
    const alongZ=room.depth>=room.width;
    const size=alongZ?[.19,.055,Math.min(room.depth-1,2.4)]:[Math.min(room.width-1,2.4),.055,.19];
    const center=[room.x+room.width/2,room.floor_y+(role==='greenhouse'?2.31:room.height-.065),room.z+room.depth/2];
    const id='ceiling_light_'+room.id,box=DR_box(center,size);
    plan.architecture.push({id,kind:'luminaire',room_id:room.id,center,size,bounds:box,color:style.light});addCollider(id,box);
    plan.lights.push({id:'task_light_'+room.id,room_id:room.id,position:[center[0],center[1]-.22,center[2]],color:style.light,intensity:Math.min(45,room.width*room.depth*1.3),distance:Math.hypot(room.width,room.depth)+1});
    // A small physical plaque by one doorway replaces a floating room banner.
    const opening=geometry.portals.find(p=>(p.room_a===room.id||p.room_b===room.id)&&p.state==='open_passage');
    if(opening){
      const normal=opening.axis==='x'?0:2,tangent=normal===0?2:0;
      const roomCenter=normal===0?room.x+room.width/2:room.z+room.depth/2;
      const sign=Math.sign(roomCenter-opening.coordinate),lo=tangent===0?room.x:room.z,hi=lo+(tangent===0?room.width:room.depth);
      const offset=opening.center+opening.width/2+.36;
      const along=offset+.25<hi-.12?offset:opening.center-opening.width/2-.36;
      if(along-.25>lo+.1&&along+.25<hi-.1){
        const p=[0,room.floor_y+1.77,0];p[normal]=opening.coordinate+sign*.105;p[tangent]=along;
        const size=normal===0?[.03,.18,.5]:[.5,.18,.03],b=DR_box(p,size);
        // Plaques may be close to a doorway but never intrude on the actual leaf
        // sweep or route footprint. Their small rigid volume is still collidable.
        if(clear(room,b,{objects:false})){
          const sid='plaque_'+room.id;plan.signs.push({id:sid,room_id:room.id,text:room.name,position:p,normal:normal===0?[sign,0,0]:[0,0,sign],size,bounds:b});addCollider(sid,b);
        }
      }
    }
  }
  // Add a small eating place only after the original furnishings, architecture
  // and signs are reserved. This preserves their existing IDs and placements.
  for(const room of geometry.rooms){
    if(room.access!=='walkable_layout'||program[room.id]!=='habitat')continue;
    const kind='meal_station',id='equipment_'+room.id+'_meal_station',w=1.30,d=1.30,h=1.04;
    if(plan.objects.length>=32||plan.colliders.length>=128){
      plan.omitted.push({room_id:room.id,kind,reason:'No remaining authored equipment/collider budget.'});continue;
    }
    let chosen=null;
    for(const wall of ['south','east','west','north']){
      for(const along of [.18,.82,.5,0,1]){
        const p=wallPlacement(room,w,d,h,wall,along);
        if(p&&clear(room,p.box)){chosen=p;break;}
      }
      if(chosen)break;
    }
    if(chosen){plan.objects.push({id,room_id:room.id,kind,role:'habitat',localSize:[w,h,d],center:chosen.center,yaw:chosen.yaw,bounds:chosen.box});addCollider(id,chosen.box);}
    else plan.omitted.push({room_id:room.id,kind,reason:'No meal-station placement preserving walking routes, entry, door sweep and existing furnishings.'});
  }
  // The crop module uses visible recirculation pipes. Each straight section has
  // its own conservative cylinder bounds; empty space inside the loop stays free.
  for(const room of geometry.rooms){
    if(program[room.id]!=='greenhouse')continue;
    const y=room.floor_y+2.31,x0=room.x+.16,x1=room.x+room.width-.16,z0=room.z+.16,z1=room.z+room.depth-.16;
    let index=0;
    function pipe(a,b){
      const min=a.map((v,i)=>Math.min(v,b[i])-.022),max=a.map((v,i)=>Math.max(v,b[i])+.022),center=min.map((v,i)=>(v+max[i])/2),size=min.map((v,i)=>max[i]-v);
      const id='irrigation_'+room.id+'_'+index++,bounds={min,max};
      DR_assert(min.every((v,i)=>v<max[i]),'Invalid pipe bounds');
      plan.architecture.push({id,kind:'greenhouse_irrigation',room_id:room.id,center,size,bounds,points:[a,b]});addCollider(id,bounds);
    }
    const corners=[[x0,y,z0],[x1,y,z0],[x1,y,z1],[x0,y,z1]];
    corners.forEach((a,i)=>pipe(a,corners[(i+1)%4]));
    for(const object of plan.objects.filter(o=>o.room_id===room.id)){
      // A rear service coupling sits inside the existing equipment footprint;
      // the horizontal link remains above the walker's1.68m clearance.
      const localZ=-object.localSize[2]*.32,point=[object.center[0]+Math.sin(object.yaw)*localZ,room.floor_y+(object.kind==='hydroponic_bed'?.91:1.33),object.center[2]+Math.cos(object.yaw)*localZ];
      const top=[point[0],y,point[2]],ends=[[x0,y,point[2]],[x1,y,point[2]],[point[0],y,z0],[point[0],y,z1]];
      ends.sort((a,b)=>Math.hypot(a[0]-top[0],a[2]-top[2])-Math.hypot(b[0]-top[0],b[2]-top[2]));
      pipe(point,top);pipe(top,ends[0]);
    }
  }
  // Add role-specific wall monitors only after all existing equipment, pipes,
  // routes and doorway approaches are reserved. Existing placements stay exact.
  for(const room of geometry.rooms){
    const role=program[room.id];if(!['equipment_vestibule','laboratory','habitat','observation'].includes(role))continue;
    const w=.94,h=.54,d=.045;let chosen=null;
    for(const wall of ['south','north','west','east']){
      for(const along of [.5,.2,.8,0,1]){
        const p=wallPlacement(room,w,d,h,wall,along);if(!p)continue;
        p.center[1]=room.floor_y+1.58;const axis=wall==='south'||wall==='north'?2:0;
        p.center[axis]+=(wall==='north'||wall==='east'?.1:-.1);p.box=DR_box(p.center,p.size);
        if(clear(room,p.box)){chosen=p;break;}
      }if(chosen)break;
    }
    if(chosen){const id='monitor_'+room.id;plan.architecture.push({id,kind:'room_monitor',room_id:room.id,monitor_role:role,center:chosen.center,size:chosen.size,localSize:[w,h,d],yaw:chosen.yaw,bounds:chosen.box});addCollider(id,chosen.box);}
    else plan.omitted.push({room_id:room.id,kind:'room_monitor',reason:'No wall placement preserving existing equipment, walking routes and door sweeps.'});
  }
  // Bound renderer complexity as well as collision complexity.
  DR_assert(plan.objects.length<=32&&plan.architecture.length<=96&&plan.lights.length<=12,'Dressing budget exceeded');
  return DR_freeze(plan);
}

// Derived architectural detail only. The original wall safety collider remains solid.
// No pressure rating, exterior traversal, measured Martian terrain or real sky model.
function planObservationViewport(geometry,plan){
  if(!plan.enabled)return null;
  const rooms=geometry.rooms.filter(r=>plan.roomStyles[r.id]?.role==='observation');
  if(rooms.length!==1)return null;
  const room=rooms[0],bottom=room.floor_y+.95,top=bottom+1.2;
  if(room.height<2.45)return null;
  for(const side of ['east','west','north','south']){
    const axis=['east','west'].includes(side)?0:2,along=axis===0?2:0,sign=['east','north'].includes(side)?1:-1;
    const wallCoordinate=axis===0?room.x+(sign>0?room.width:0):room.z+(sign>0?room.depth:0);
    const start=along===0?room.x:room.z,end=start+(along===0?room.width:room.depth);
    // Only an intact exterior wall; never erase a doorway or a shared partition.
    const wall=geometry.primitives.find(p=>p.id===room.id+'_'+side+'_0'&&p.role==='wall'&&Math.abs(p.position[axis]-wallCoordinate)<1e-7&&Math.abs(p.size[along]-(end-start))<1e-7&&Math.abs(p.size[1]-room.height)<1e-7);
    if(!wall||wall.size[axis]<.12||wall.size[axis]>.3)continue;
    const outside=wallCoordinate+sign*(wall.size[axis]/2+.02);
    if(geometry.rooms.some(r=>r!==room&&outside>(axis===0?r.x:r.z)-.01&&outside<(axis===0?r.x+r.width:r.z+r.depth)+.01&&Math.max(start,along===0?r.x:r.z)<Math.min(end,along===0?r.x+r.width:r.z+r.depth)))continue;
    if(geometry.portals.some(p=>p.axis===(axis===0?'x':'z')&&Math.abs(p.coordinate-wallCoordinate)<.16&&p.center>start&&p.center<end))continue;
    const collider=geometry.colliders.find(c=>c.id===wall.id&&c.min.every((v,i)=>Math.abs(v-(wall.position[i]-wall.size[i]/2))<1e-7)&&c.max.every((v,i)=>Math.abs(v-(wall.position[i]+wall.size[i]/2))<1e-7));
    if(!collider)continue;
    // Fit a real structural bay. Keep existing ribs, equipment and their colliders.
    let gaps=[[start+.2,end-.2]];
    for(const c of plan.colliders){
      if(c.max[1]<=bottom||c.min[1]>=top||c.max[axis]<wallCoordinate-.45||c.min[axis]>wallCoordinate+.45)continue;
      const lo=c.min[along]-.12,hi=c.max[along]+.12;
      gaps=gaps.flatMap(([a,b])=>hi<=a||lo>=b?[[a,b]]:[[a,Math.max(a,lo)],[Math.min(b,hi),b]].filter(([x,y])=>y-x>1e-6));
    }
    gaps.sort((a,b)=>(b[1]-b[0])-(a[1]-a[0])||a[0]-b[0]);
    const gap=gaps[0];if(!gap||gap[1]-gap[0]<1.3)continue;
    const width=Math.min(1.5,gap[1]-gap[0]),center=(gap[0]+gap[1])/2;
    return {contract:'authored_observation_viewport_v1',room_id:room.id,wall_id:wall.id,safety_collider_id:collider.id,side,axis,along,sign,coordinate:wallCoordinate,center,bottom,top,width,thickness:wall.size[axis],nontraversable:true,pressure_simulation:false};
  }
  return null;
}
function viewportWallPieces(primitive,viewport){
  if(!viewport||primitive.id!==viewport.wall_id)return [primitive];
  const {along,center,width,bottom,top}=viewport,lo=primitive.position[along]-primitive.size[along]/2,hi=primitive.position[along]+primitive.size[along]/2;
  const floor=primitive.position[1]-primitive.size[1]/2,ceiling=primitive.position[1]+primitive.size[1]/2;
  return [[lo,center-width/2,floor,ceiling],[center+width/2,hi,floor,ceiling],[center-width/2,center+width/2,floor,bottom],[center-width/2,center+width/2,top,ceiling]].map(([a,b,y,z],i)=>{
    const position=[...primitive.position],size=[...primitive.size];position[along]=(a+b)/2;size[along]=b-a;position[1]=(y+z)/2;size[1]=z-y;
    return {...primitive,id:primitive.id+'_surround_'+i,position,size};
  });
}
function createStructuralPrimitive(THREE,primitive,material,viewport,materials,hatchArchitecture=null){
  if(materials.greenhouseGeometry){const crop=buildGreenhouseEnvelope(THREE,primitive,materials.greenhouseGeometry,materials.greenhouse);if(crop)return crop;}
  if(hatchArchitecture){const cut=buildHatchStructuralMesh(THREE,primitive,material,hatchArchitecture);if(cut)return cut;}
  if(!viewport||primitive.id!==viewport.wall_id){const m=new THREE.Mesh(new THREE.BoxGeometry(...primitive.size),material);m.name=primitive.id;m.position.set(...primitive.position);m.receiveShadow=true;return m;}
  const group=new THREE.Group();group.name=primitive.id;group.position.set(...primitive.position);group.userData.observation_viewport=viewport;
  function box(name,size,world,mat){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),mat);m.name=name;m.position.set(...world.map((v,i)=>v-primitive.position[i]));m.receiveShadow=true;group.add(m);return m;}
  for(const p of viewportWallPieces(primitive,viewport))box(p.id,p.size,p.position,material);
  const {axis,along,sign,coordinate,center,bottom,top,width,thickness}=viewport,height=top-bottom;
  // Liners run through the wall; a front trim and recessed gasket surround glazing.
  function ring(label,border,depth,offset,w,h,mat){
    for(const edge of [-1,1]){
      const p=[...primitive.position],s=[.01,.01,.01];p[axis]=coordinate+offset;p[along]=center+edge*(w-border)/2;p[1]=(bottom+top)/2;s[axis]=depth;s[along]=border;s[1]=h;box(viewport.wall_id+'_'+label+'_vertical_'+edge,s,p,mat);
      p[along]=center;p[1]=(bottom+top)/2+edge*(h-border)/2;s[along]=w-2*border;s[1]=border;box(viewport.wall_id+'_'+label+'_horizontal_'+edge,s,p,mat);
    }
  }
  // The reveal starts at the frame's back, not at its coplanar front.
  // Both parts stay within the original wall bounds and meet without overlap.
  ring('reveal',.036,thickness-.026,sign*.013,width,height,materials.basic.metal);
  ring('inner_frame',.07,.026,-sign*(thickness/2-.013),width,height,materials.basic.ivory);
  ring('glazing_gasket',.016,.018,sign*(thickness/2-.028),width-.072,height-.072,materials.basic.rubber);
  const size=[.01,.01,.01],position=[...primitive.position];size[axis]=.008;size[along]=width-.10;size[1]=height-.10;position[axis]=coordinate+sign*(thickness/2-.028);position[along]=center;position[1]=(bottom+top)/2;
  const glass=new THREE.MeshStandardMaterial({color:0xc0d4d2,roughness:.16,metalness:0,transparent:true,opacity:.12,depthWrite:false,side:THREE.DoubleSide});
  box(viewport.wall_id+'_glazing',size,position,glass).userData={viewport_glazing:true,nontraversable:true};
  return group;
}
// Original fictional scenery, in meters. No surveyed terrain, live weather,
// pressure simulation, external artwork, texture downloads or traversal.
// This exact recipe is inlined into the existing viewer and shared module.
function buildOriginalMarsExterior(THREE,viewport,geometry){
  const {axis,along,sign,coordinate,center}=viewport;
  const room=geometry.rooms.find(r=>r.id===viewport.room_id);
  if(!room||!Number.isFinite(room.floor_y))return null;
  const floor=room.floor_y;
  const root=new THREE.Group();root.name='original_procedural_exterior_'+viewport.room_id;
  root.userData={kind:'procedural_exterior_scenery',recipe:'original_mars_landscape_v2',room_id:viewport.room_id,
    nontraversable:true,measured_terrain:false,live_weather:false,units:'meters'};
  function hash(x,z,seed=0){let n=Math.imul(x,374761393)^Math.imul(z,668265263)^Math.imul(seed+17,1442695041);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;}
  const mix=(a,b,t)=>a+(b-a)*t;
  function noise(x,z,seed=0){const ix=Math.floor(x),iz=Math.floor(z),tx=x-ix,tz=z-iz,u=tx*tx*(3-2*tx),v=tz*tz*(3-2*tz);return mix(mix(hash(ix,iz,seed),hash(ix+1,iz,seed),u),mix(hash(ix,iz+1,seed),hash(ix+1,iz+1,seed),u),v);}
  function fbm(x,z,seed=0){return .57*noise(x,z,seed)+.28*noise(x*2.13+9,z*2.13-4,seed+1)+.15*noise(x*4.37-7,z*4.37+3,seed+2);}
  function world(d,a,y){const p=[0,y,0];p[axis]=coordinate+sign*d;p[along]=center+a;return p;}
  function occupied(d,a,margin=0){const p=world(d,a,0);return geometry.rooms.some(r=>p[0]>=r.x-margin&&p[0]<=r.x+r.width+margin&&p[2]>=r.z-margin&&p[2]<=r.z+r.depth+margin);}
  function height(d,a){
    // Near-ground centimeter relief grades into irregular eroded ridge bands.
    // The bands' centers, widths and crest heights use different noise scales.
    const n=fbm(d*.095,a*.095,3),near=Math.min(1,Math.max(0,(d-1)/7));
    const ridge=(at,width,amplitude,seed)=>{
      const shift=(fbm(a*.034,seed,seed)-.5)*16;
      const shoulder=Math.abs((d-at-shift)/width);
      return Math.exp(-shoulder*shoulder*1.7)*amplitude*(.42+.85*fbm(a*.06,seed+5,seed+4));
    };
    const y=floor-.18+near*((n-.5)*.46+(noise(d*.9,a*.9,19)-.5)*.045)
      +ridge(35,8.5,3.7,11)+ridge(79,15,7.1,31);
    // Scenery never rises through another authored room in a different layout.
    return occupied(d,a,.2)?Math.min(y,floor-.18):y;
  }
  function mesh(name,positions,colors,indices,material,kind){
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.setIndex(indices);g.computeVertexNormals();
    const m=new THREE.Mesh(g,material);m.name=root.name+'_'+name;m.userData={exterior_part:kind,nontraversable:true,measured_terrain:false};root.add(m);return m;
  }
  const positions=[],colors=[],indices=[],nx=64,nz=72;
  for(let i=0;i<=nx;i++)for(let j=0;j<=nz;j++){
    const d=.18+.18*i+.025*i*i,t=j-nz/2,a=Math.sign(t)*(.25*Math.abs(t)+.055*t*t);
    positions.push(...world(d,a,height(d,a)));
    const tone=.78+.4*fbm(d*.7,a*.7,67),patch=fbm(d*.21,a*.21,83),haze=Math.min(.45,d/240);
    const soil=[.34+.10*patch,.17+.06*patch,.085+.035*patch],dust=[.53,.32,.19];
    colors.push(...soil.map((v,k)=>mix(v*tone,dust[k],haze)));
    if(i<nx&&j<nz){const k=i*(nz+1)+j;indices.push(k,k+nz+1,k+1,k+1,k+nz+1,k+nz+2);}
  }
  if((axis===0?sign:-sign)>0)for(let i=0;i<indices.length;i+=3)[indices[i+1],indices[i+2]]=[indices[i+2],indices[i+1]];
  mesh('regolith',positions,colors,indices,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0,side:THREE.DoubleSide}),'regolith_and_ridges');
  // Each rock has its own anisotropic shape, scale and weathered color. No
  // identical repeated primitive or painted flat billboard is used.
  for(let k=0;k<18;k++){
    const d=2.8+hash(k,3,7)*20,a=(hash(k,8,9)-.5)*Math.min(27,d*1.5),radius=.12+.42*hash(k,5,27);
    if(occupied(d,a,radius*1.5+.25))continue;
    const g=new THREE.SphereGeometry(1,16,10),p=g.getAttribute('position'),c=[];
    const sx=radius*(.9+.6*hash(k,1,21)),sy=radius*(.36+.42*hash(k,2,22)),sz=radius*(.75+.7*hash(k,3,23));
    for(let i=0;i<p.count;i++){
      const x=p.getX(i),y=p.getY(i),z=p.getZ(i);
      const irregular=.76+.37*fbm(x*2.9+k*7,z*2.9+y*1.8,103+k);
      // Angular shoulders with softened normals; upper and lower halves differ.
      p.setXYZ(i,(x*irregular+.085*y*z)*sx,y*(.83+.2*noise(x*3+k,z*3,121))*sy,(z*irregular+.12*x*y)*sz);
      const weather=.73+.35*noise(x*4+k,y*4+z,142),top=.025*Math.max(0,y);
      c.push(.235*weather+top,.16*weather+top*.65,.115*weather+top*.35);
    }
    g.setAttribute('color',new THREE.Float32BufferAttribute(c,3));g.computeVertexNormals();
    // SphereGeometry's unused pole seam vertices have no incident triangles.
    // Give those explicit valid normals, so GLTF does not silently repair them.
    const normals=g.getAttribute('normal');for(let i=0;i<normals.count;i++){
      const n=new THREE.Vector3().fromBufferAttribute(normals,i);
      if(n.lengthSq()<.5)n.fromBufferAttribute(p,i).normalize();
      normals.setXYZ(i,n.x,n.y,n.z);
    }
    const rock=new THREE.Mesh(g,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0}));
    rock.name=root.name+'_rock_'+String(k).padStart(2,'0');rock.position.set(...world(d,a,height(d,a)+sy*.25));rock.rotation.y=hash(k,9,53)*Math.PI*2;
    rock.userData={exterior_part:'weathered_rock',nontraversable:true,measured_terrain:false};root.add(rock);
  }
  // A curved, original dust-color sky volume behind the terrain, not a source
  // photograph or global background. It exports as the same geometry/material.
  // Radius180m lies inside the unchanged250m camera far plane; every vertex is
  // strictly in the exterior half-space. No interior light or fog is changed.
  const sp=[],sc=[],si=[],azimuthSteps=48,altitudes=[-.38,-.18,-.04,.015,.055,.14,.35,.7,1.1,1.48],radius=180;
  for(let v=0;v<altitudes.length;v++)for(let u=0;u<=azimuthSteps;u++){
    const altitude=altitudes[v],azimuth=-1.53+u/azimuthSteps*3.06,d=radius*Math.cos(altitude)*Math.cos(azimuth),a=radius*Math.cos(altitude)*Math.sin(azimuth);
    sp.push(...world(d,a,floor+1+radius*Math.sin(altitude)));
    const horizon=[.63,.395,.22],zenith=[.24,.215,.195],low=[.34,.19,.105];
    const col=altitude<0?horizon.map((x,k)=>mix(x,low[k],Math.min(1,-altitude/.38))):horizon.map((x,k)=>mix(x,zenith[k],Math.min(1,altitude/.85)));
    sc.push(...col);
    if(v<altitudes.length-1&&u<azimuthSteps){const n=v*(azimuthSteps+1)+u;si.push(n,n+1,n+azimuthSteps+1,n+1,n+azimuthSteps+2,n+azimuthSteps+1);}
  }
  // StandardMaterial keeps the existing importer contract.
  // Three's vertex color multiplies diffuse, not emissive: use neutral diffuse
  // with a modest common emission so the color gradient remains visible.
  mesh('dusty_sky',sp,sc,si,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0,emissive:0x51331e,emissiveIntensity:.42,side:THREE.DoubleSide}),'dusty_sky_shell');
  root.updateMatrixWorld(true);return root;
}

function addObservationExterior(THREE,scene,viewport,presentation=null,geometry=null){
  const source=presentation?.source;
  if(!viewport||presentation?.contract!=='bound_original_exterior_presentation_v1'||presentation.setting!=='mars_surface'||
     presentation.reason!=='explicit_original_mars_base_request'||!source||!geometry||
     source.research_packet_sha256!==geometry.research_packet_sha256||
     ![source.brief_sha256,source.request_sha256,source.research_packet_sha256].every(h=>typeof h==='string'&&/^[0-9a-f]{64}$/.test(h))||
     source.job_id!=='world_research_'+source.brief_sha256.slice(0,20))return null;
  const exterior=buildOriginalMarsExterior(THREE,viewport,geometry);
  if(!exterior)return null;
  exterior.userData.presentation_setting=presentation;scene.add(exterior);return exterior;
}

function addGreenhouseMarsExterior(THREE,scene,geometry,presentation){
  if(!createMarsDisplayData(geometry,presentation))return null;
  const rooms=geometry.rooms.filter(r=>geometry.functional_program?.[r.id]==='greenhouse');if(rooms.length!==1)return null;
  const room=rooms[0],x=room.x+room.width/2,z=room.z+room.depth/2;
  // Reuse the reviewed original terrain recipe only beyond the westmost room.
  // Existing eastern Viewport Deck scenery remains byte-for-byte unchanged.
  const west={room_id:room.id,axis:0,along:2,sign:-1,coordinate:Math.min(...geometry.rooms.map(r=>r.x))-.16,center:z};
  const root=buildOriginalMarsExterior(THREE,west,geometry);if(!root)return null;
  for(const child of [...root.children])if(child.userData.exterior_part==='dusty_sky_shell'){root.remove(child);child.geometry.dispose();child.material.dispose();}
  root.name='greenhouse_original_mars_surround';root.userData.presentation_setting=presentation;root.userData.greenhouse_surround=true;
  // A remote, all-direction sky shell closes the roof's view. Its low ring is
  //160m from the crop-room center, so no surface can clip an authored interior.
  // This is original scene dressing, not a physical sky or measured environment.
  const positions=[],colors=[],indices=[],steps=48,radius=160,alts=[-.02,.06,.20,.5,.85,1.15,1.42];
  const color=alt=>{const t=Math.min(1,Math.max(0,alt/.95));return [.63*(1-t)+.24*t,.395*(1-t)+.215*t,.22*(1-t)+.195*t];};
  for(let row=0;row<alts.length;row++)for(let col=0;col<steps;col++){
    const alt=alts[row],az=2*Math.PI*col/steps;positions.push(x+radius*Math.cos(alt)*Math.cos(az),room.floor_y+radius*Math.sin(alt),z+radius*Math.cos(alt)*Math.sin(az));colors.push(...color(alt));
    if(row<alts.length-1){const a=row*steps+col,b=row*steps+(col+1)%steps;indices.push(a,b,a+steps,b,b+steps,a+steps);}
  }
  const tip=positions.length/3;positions.push(x,room.floor_y+radius,z);colors.push(...color(Math.PI/2));
  for(let col=0;col<steps;col++)indices.push((alts.length-1)*steps+col,(alts.length-1)*steps+(col+1)%steps,tip);
  const geometrySky=new THREE.BufferGeometry();geometrySky.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geometrySky.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));geometrySky.setIndex(indices);geometrySky.computeVertexNormals();
  const sky=new THREE.Mesh(geometrySky,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0,emissive:0x51331e,emissiveIntensity:.42,side:THREE.DoubleSide}));
  sky.name='greenhouse_original_mars_sky';sky.userData={exterior_part:'greenhouse_sky_shell',nontraversable:true,physical_sky:false,measured_terrain:false};root.add(sky);scene.add(root);return root;
}

// Original display artwork and a declared fictional scenario, not mission telemetry.
function createMarsDisplayData(geometry,presentation,viewport=null){
  const source=presentation?.source;
  if(presentation?.contract!=='bound_original_exterior_presentation_v1'||presentation.setting!=='mars_surface'||
     presentation.reason!=='explicit_original_mars_base_request'||!source||!geometry||
     source.research_packet_sha256!==geometry.research_packet_sha256||
     ![source.brief_sha256,source.request_sha256,source.research_packet_sha256].every(h=>typeof h==='string'&&/^[0-9a-f]{64}$/.test(h))||
     source.job_id!=='world_research_'+source.brief_sha256.slice(0,20))return null;
  const rooms=geometry.rooms.map(r=>({id:r.id,name:r.name,x:r.x,z:r.z,width:r.width,depth:r.depth,role:geometry.functional_program?.[r.id]||(r.id==='circulation'?'circulation':'room')}));
  const view=rooms.find(r=>r.role==='observation'&&viewport?.contract==='authored_observation_viewport_v1'&&viewport.room_id===r.id);
  return Object.freeze({contract:'fictional_mars_display_snapshot_v1',mode:'REFERENCE / ARCHIVE · NOT LIVE',
    site:'Fictional Mars surface habitat',reference:MARS_REFERENCE,
    observation:view?view.name:null,rooms:Object.freeze(rooms.map(Object.freeze)),
    references:Object.freeze(['https://science.nasa.gov/mars/facts/','https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html']),
    provenance:'NASA facts and dated MEDA observations are references, not current habitat telemetry. The room plan comes from this exact generated layout.'});
}

function paintMarsDisplay(ctx,kind,data){
  if(!data||!['planet','weather','layout'].includes(kind))throw new TypeError('Unknown Mars display');
  if(kind!=='layout'){paintRoomMonitor(ctx,createRoomMonitorData(kind,{marsData:data}));return;}
  const W=1024,H=512;
  ctx.fillStyle='#091b25';ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#d3a077';ctx.fillRect(0,0,10,H);
  ctx.fillStyle='#f0e8da';ctx.font='600 40px Segoe UI,sans-serif';
  ctx.fillText(kind==='layout'?(data.observation?'HABITAT / MARS VIEW':'HABITAT / ROOM PLAN'):kind==='weather'?'MARS / OUTSIDE CONDITIONS':'MARS / SURFACE HABITAT',36,59);
  ctx.fillStyle='#e6b888';ctx.font='24px monospace';ctx.fillText(data.mode,36,99);
  ctx.strokeStyle='#4b6570';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(36,118);ctx.lineTo(988,118);ctx.stroke();
  if(kind==='layout'){
    const rooms=data.rooms,minX=Math.min(...rooms.map(r=>r.x)),maxX=Math.max(...rooms.map(r=>r.x+r.width)),
      minZ=Math.min(...rooms.map(r=>r.z)),maxZ=Math.max(...rooms.map(r=>r.z+r.depth));
    const scale=Math.min(590/Math.max(1,maxX-minX),305/Math.max(1,maxZ-minZ));
    for(const r of rooms){
      const x=46+(r.x-minX)*scale,y=445-(r.z-minZ+r.depth)*scale;
      ctx.fillStyle=r.role==='observation'?'#80b6ac':r.role==='airlock'?'#9b774c':'#284453';
      ctx.fillRect(x+2,y+2,r.width*scale-4,r.depth*scale-4);
      ctx.strokeStyle='#c7d9d9';ctx.lineWidth=2;ctx.strokeRect(x,y,r.width*scale,r.depth*scale);
      ctx.fillStyle=r.role==='observation'?'#112a30':'#edf0e8';ctx.font='600 21px Segoe UI,sans-serif';
      const label=r.role==='observation'&&data.observation?'MARS VIEW':r.role.replaceAll('_',' ').toUpperCase();
      ctx.fillText(label,x+8,y+Math.min(r.depth*scale/2+8,35),Math.max(10,r.width*scale-16));
    }
    ctx.fillStyle='#bfe0d6';ctx.font='600 31px Segoe UI,sans-serif';ctx.fillText(data.observation?'OBSERVATION':'ROOM PLAN',665,180);
    ctx.fillStyle='#eff1e9';ctx.font='27px Segoe UI,sans-serif';
    ctx.fillText(data.observation?'Window to the surface':'No surface window',665,226);ctx.fillText(data.observation?'Via main circulation':'in this preview',665,268);
    ctx.fillStyle='#b6c8cc';ctx.font='23px Segoe UI,sans-serif';ctx.fillText('Plan: current layout',665,330);
    ctx.fillText('Not a terrain survey',665,366);
  }
  ctx.fillStyle='#aec6cd';ctx.font='22px monospace';ctx.fillText('CURRENT GENERATED ROOM PLAN / NOT A SURVEY / NO LIVE SENSORS',36,489);
}

// Original procedural meshes and textures. No external photographs/assets.
function createDressingMaterials(THREE,plan,{canvasFactory=()=>typeof document==='undefined'?null:document.createElement('canvas'),displayData=null,greenhouseGeometry=null,doorStates=[]}={}){
  const cache=new Map(),monitorCache=new Map();
  let currentDoorStates=doorStates;
  function texture(kind,accent='#8ba0a9'){
    const canvas=canvasFactory();if(!canvas)return null;
    canvas.width=canvas.height=512;const ctx=canvas.getContext('2d');
    if(kind==='screen'){
      ctx.fillStyle='#0d2029';ctx.fillRect(0,0,512,512);ctx.fillStyle='#d1ded6';ctx.font='600 37px Segoe UI,sans-serif';ctx.fillText('DEVICE STANDBY',25,135);
      ctx.fillStyle='#c9ae7b';ctx.font='29px Segoe UI,sans-serif';ctx.fillText('NO SENSOR LINK',25,225);ctx.font='23px Segoe UI,sans-serif';ctx.fillText('No measurements available',25,305);
    }else if(kind==='floor'||kind==='grate'){
      ctx.fillStyle=kind==='grate'?'#445159':'#666d6e';ctx.fillRect(0,0,512,512);
      ctx.strokeStyle=kind==='grate'?'#19272c':'#525a5c';ctx.lineWidth=kind==='grate'?12:3;
      for(let i=0;i<512;i+=kind==='grate'?32:64){ctx.beginPath();ctx.moveTo(i,0);ctx.lineTo(i,512);ctx.stroke();
        if(kind==='grate'){ctx.beginPath();ctx.moveTo(0,i);ctx.lineTo(512,i);ctx.stroke();}}
      if(kind==='floor'){ctx.fillStyle='#747b7b';for(let y=16;y<512;y+=32)for(let x=16;x<512;x+=32){ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill();}}
    }else{
      ctx.fillStyle='#c0c3bb';ctx.fillRect(0,0,512,512);ctx.fillStyle='#aeb4ae';ctx.fillRect(8,8,496,496);
      ctx.fillStyle='#ccd0c8';ctx.fillRect(13,13,486,486);ctx.strokeStyle='#747f7c';ctx.lineWidth=3;ctx.strokeRect(9,9,494,494);
      ctx.fillStyle='#667371';for(const x of [26,486])for(const y of [26,486]){ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill();}
      ctx.fillStyle=accent;ctx.fillRect(18,469,476,9);
    }
    const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;map.wrapS=map.wrapT=THREE.RepeatWrapping;return map;
  }
  function mat(name,color,roughness=.55,metalness=.2,extra={}){
    if(!cache.has(name))cache.set(name,new THREE.MeshStandardMaterial({color,roughness,metalness,...extra}));return cache.get(name);
  }
  const basic={
    frame:mat('frame',0x42505a,.39,.73),metal:mat('metal',0xa9b1b2,.4,.7),ivory:mat('ivory',0xd4d7ce,.62,.15),
    dark:mat('dark',0x263139,.64,.28),rubber:mat('rubber',0x17222a,.91,.01),wood:mat('wood',0xad8d68,.79,.01),
    cloth:mat('cloth',0xc3c5b7,.96,0),seat:mat('seat',0x536875,.94,0),glass:mat('glass',0x8ec5c8,.2,.25,{transparent:true,opacity:.28,depthWrite:false}),
    green:mat('green',0x538b55,.85,0),leaf:mat('leaf',0x80a760,.92,0),soil:mat('soil',0x453d31,.99,0),
    amber:mat('amber',0xb79755,.6,.3),red:mat('red',0x986253,.68,.1),
    indicator:mat('indicator',0x83c6ac,.38,.1,{emissive:0x276f53,emissiveIntensity:.7}),
    screen:mat('screen',0xa4d6d8,.32,.2,{map:texture('screen'),emissive:0x2e646f,emissiveIntensity:.32}),
    lamp:mat('lamp',0xfff1d2,.35,.06,{emissive:0xffe1a2,emissiveIntensity:1.8})
  };
  function surface(role,roomId){
    const style=plan.roomStyles[roomId];
    if(role==='wall')return mat('basewall',0xc6cdc8,.84,.1);
    if(role==='ceiling')return mat('ceiling',0xc3c9c4,.88,.1);
    if(role==='floor')return mat('floor_'+(roomId||''),style?.floor||0x5a666b,.85,.12,{map:texture(style?.role==='airlock'?'grate':'floor')});
    return mat('locked',0x55636b,.9,.1);
  }
  function wallPanel(roomId,width,height){
    const map=texture('panel',plan.roomStyles[roomId]?.accent);if(map)map.repeat.set(Math.max(1,width/.95),Math.max(1,height/1.05));
    return new THREE.MeshStandardMaterial({color:0xffffff,map,roughness:.72,metalness:.17,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});
  }
  function screenFor(kind,roomId=null){
    if(kind!=='layout'){
      const key=kind+':'+(roomId||''),data=createRoomMonitorData(kind,{marsData:displayData,geometry:greenhouseGeometry,roomId,doorStates:currentDoorStates});
      if(!data)return basic.screen;
      if(!monitorCache.has(key))monitorCache.set(key,{...createRoomMonitorMaterial(THREE,data,canvasFactory),kind,roomId});
      return monitorCache.get(key).material;
    }
    if(!displayData)return basic.screen;
    const name='mars_'+kind;if(cache.has(name))return cache.get(name);
    const canvas=canvasFactory();if(!canvas)return basic.screen;
    canvas.width=1024;canvas.height=512;paintMarsDisplay(canvas.getContext('2d'),kind,displayData);
    const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
    const material=new THREE.MeshStandardMaterial({color:0xffffff,map,roughness:.6,metalness:0,emissive:0xffffff,emissiveMap:map,emissiveIntensity:.45});
    material.userData={kind:'mars_'+kind,mode:displayData.mode,contract:displayData.contract};cache.set(name,material);return material;
  }
  const greenhouse=createGreenhouseAssets(THREE,greenhouseGeometry?createGreenhouseScenario(greenhouseGeometry,plan):null,canvasFactory);
  function refreshDoorStates(states){
    currentDoorStates=states;
    for(const record of monitorCache.values())if(record.kind==='airlock')record.refresh(createRoomMonitorData(record.kind,{marsData:displayData,geometry:greenhouseGeometry,roomId:record.roomId,doorStates:states}));
  }
  return {basic,surface,wallPanel,canvasFactory,screenFor,displayData,greenhouse,greenhouseGeometry,refreshDoorStates,monitorSnapshots:()=>[...monitorCache.values()].map(record=>record.data)};
}

function addRoomDressing(THREE,scene,geometry,plan,materials,hatchArchitecture=null){
  const M=materials.basic,equipmentGroups=new Map(),geometryCache=new Map();
  function cached(key,make){if(!geometryCache.has(key))geometryCache.set(key,make());return geometryCache.get(key);}
  function box(group,x,y,z,w,h,d,material=M.metal){
    const geo=cached('b:'+w+','+h+','+d,()=>new THREE.BoxGeometry(w,h,d));const mesh=new THREE.Mesh(geo,material);mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;group.add(mesh);return mesh;
  }
  function cylinder(group,x,y,z,r,h,material=M.metal,rx=0,rz=0){
    const mesh=new THREE.Mesh(cached('c:'+r+','+h,()=>new THREE.CylinderGeometry(r,r,h,12)),material);mesh.position.set(x,y,z);mesh.rotation.set(rx,0,rz);mesh.castShadow=true;group.add(mesh);return mesh;
  }
  function sphere(group,x,y,z,r,material=M.ivory,scale=[1,1,1]){
    const mesh=new THREE.Mesh(cached('s:'+r,()=>new THREE.SphereGeometry(r,12,8)),material);mesh.position.set(x,y,z);mesh.scale.set(...scale);mesh.castShadow=true;group.add(mesh);return mesh;
  }
  function torus(group,x,y,z,r,t,material=M.metal,rx=0,ry=0){
    const mesh=new THREE.Mesh(cached('t:'+r+','+t,()=>new THREE.TorusGeometry(r,t,8,18)),material);mesh.position.set(x,y,z);mesh.rotation.set(rx,ry,0);group.add(mesh);return mesh;
  }
  // Rounded, authored soft forms. Geometry only: no cloth/contact simulation.
  function softBox(group,name,x,y,z,w,h,d,r,material){
    const key='soft:'+w+','+h+','+d+','+r;
    const geo=cached(key,()=>{
      const g=new THREE.BoxGeometry(w,h,d,14,4,8),p=g.attributes.position,n=g.attributes.normal;
      const half=[w/2,h/2,d/2],core=half.map(v=>Math.max(0,v-r));
      for(let i=0;i<p.count;i++){
        const a=[p.getX(i),p.getY(i),p.getZ(i)],q=a.map((v,j)=>Math.max(-core[j],Math.min(core[j],v))),delta=a.map((v,j)=>v-q[j]);
        const length=Math.hypot(...delta);for(let j=0;j<3;j++)delta[j]/=length;
        p.setXYZ(i,...q.map((v,j)=>v+delta[j]*r));n.setXYZ(i,...delta);
      }
      g.computeBoundingBox();return g;
    });
    const mesh=new THREE.Mesh(geo,material);mesh.name=name;mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;group.add(mesh);return mesh;
  }
  function blanket(group,name,x,y,z,w,d){
    // A real two-sided draped surface with a rolled hem. The folds stay inside
    // the mattress footprint and existing conservative bunk collision volume.
    const nx=24,nz=16,positions=[],uv=[],index=[];
    for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){
      const u=i/nx,v=j/nz,edge=Math.pow(Math.max(0,(Math.abs(2*v-1)-.88)/.12),2);
      const fold=.010*Math.sin(u*Math.PI*8+v*.6)*Math.sin(v*Math.PI);
      positions.push((u-.5)*w,fold-.07*edge,(v-.5)*d);uv.push(u,v);
    }
    for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i,b=a+1,c=a+nx+1,e=c+1;index.push(a,c,b,b,c,e);}
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geo.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geo.setIndex(index);geo.computeVertexNormals();geo.computeBoundingBox();
    const material=M.seat.clone();material.side=THREE.DoubleSide;
    const mesh=new THREE.Mesh(geo,material);mesh.name=name;mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;group.add(mesh);
    softBox(group,name+'_folded_hem',x-w/2+.018,y+.018,z,.038,.038,d-.035,.017,M.seat);
  }
  function legs(group,w,d,h,material=M.frame){for(const x of [-w/2+.07,w/2-.07])for(const z of [-d/2+.07,d/2-.07])box(group,x,h/2,z,.055,h,.055,material);}
  function cabinet(group,w,h,d){
    const bodyDepth=d-.08;box(group,0,h/2,0,w,h,bodyDepth,M.frame);
    for(let i=0;i<3;i++){const y=.12+(h-.12)*(i+.5)/3;box(group,0,y,bodyDepth/2+.008,w-.075,(h-.18)/3,.016,M.ivory);box(group,w*.3,y,bodyDepth/2+.025,.09,.018,.025,M.dark);}
  }
  function smallScreen(group,x,y,z,w,h,kind=null,roomId=null){box(group,x,y,z,w+.045,h+.045,.06,M.rubber);const face=box(group,x,y,z+.033,w,h,.007,kind?materials.screenFor(kind,roomId):M.screen);if(kind)face.userData={display_kind:kind,monitor_room:roomId,mode:face.material.userData.monitor_data?.badge||materials.displayData?.mode||'LOCAL PREVIEW'};}
  function chair(group,x,z){
    cylinder(group,x,.26,z,.055,.45,M.frame);box(group,x,.49,z,.44,.085,.43,M.seat);box(group,x,.74,z+.2,.43,.45,.065,M.seat);
    for(let i=0;i<4;i++){const a=i*Math.PI/2,c=Math.cos(a),s=Math.sin(a);const leg=box(group,x+c*.12,.065,z+s*.12,.24,.035,.035,M.frame);leg.rotation.y=-a;sphere(group,x+c*.22,.035,z+s*.22,.033,M.rubber);}
  }
  for(const object of plan.objects){
    const [w,h,d]=object.localSize,group=new THREE.Group();group.name=object.id;group.position.set(object.center[0],object.center[1]-h/2,object.center[2]);group.rotation.y=object.yaw;
    const kind=object.kind;
    if(kind==='eva_lockers'){
      box(group,0,h/2,-d/2+.035,w,h,.06,M.dark);for(const x of [-w/2+.025,0,w/2-.025])box(group,x,h/2,0,.045,h,d,M.frame);
      box(group,0,.075,0,w,.12,d,M.frame);box(group,0,h-.04,0,w,.07,d,M.frame);
      for(const x of [-w*.245,w*.245]){
        sphere(group,x,1.78,.02,.155,M.ivory);sphere(group,x,1.8,.128,.12,M.rubber,[1,.68,.5]);torus(group,x,1.615,.02,.09,.019,M.metal,Math.PI/2);
        sphere(group,x,1.31,0,.185,M.ivory,[1.04,1.48,.72]);box(group,x,1.32,.135,.22,.19,.07,M.frame);
        for(const side of [-1,1]){cylinder(group,x+side*.205,1.25,0,.05,.4,M.ivory,0,side*.13);cylinder(group,x+side*.09,.79,0,.071,.56,M.ivory);box(group,x+side*.09,.455,.055,.15,.11,.26,M.rubber);}
      }
    }else if(kind==='gear_bench'){
      legs(group,w-.1,d-.08,.43);box(group,0,.46,0,w,.085,d,M.wood);box(group,0,.14,-.04,w-.15,.04,d-.14,M.frame);
      for(const x of [-.32,-.1,.12,.34])box(group,x,.23,.03,.13,.13,.25,M.rubber);
    }else if(kind==='hose_station'){
      box(group,0,.82,-d/2+.035,w,1.5,.065,M.frame);
      for(let i=0;i<3;i++)torus(group,0,.4+i*.35,.01,.185,.022,M.rubber);
      for(const x of [-.2,.2]){cylinder(group,x,1.42,.025,.036,.17,M.metal);box(group,x,1.5,.08,.11,.045,.045,M.amber);}
    }else if(kind==='airlock_control'){
      box(group,0,h/2,-.03,w,h,d*.7,M.frame);smallScreen(group,0,1.28,d*.29,w*.78,.38,'airlock',object.room_id);
      for(let i=0;i<4;i++){cylinder(group,-w*.29+i*w*.19,.86,d*.41,.027,.02,i===0?M.red:M.indicator,Math.PI/2);}
      box(group,0,.31,d*.31,w*.7,.23,.035,M.metal);for(let y=.22;y<.4;y+=.05)box(group,0,y,d*.34,w*.6,.011,.008,M.dark);
    }else if(kind==='filter_cylinders'){
      box(group,0,.045,0,w,.07,d,M.frame);for(const x of [-w*.235,w*.235]){
        cylinder(group,x,.79,0,.13,1.38,M.ivory);for(const y of [.26,1.25])torus(group,x,y,0,.133,.014,M.frame,Math.PI/2);
        cylinder(group,x,1.53,0,.035,.12,M.metal);box(group,x,1.6,.025,.13,.04,.075,M.amber);
      }
    }else if(kind==='operations_console'){
      const dd=d*.51,zz=-d*.22;for(const x of [-w/2+.1,w/2-.1])for(const z of [zz-dd/2+.07,zz+dd/2-.07])box(group,x,.375,z,.055,.75,.055,M.frame);box(group,0,.78,zz,w-.04,.075,dd,M.metal);
      box(group,-w*.38,.37,zz,w*.2,.66,dd-.07,M.frame);
      for(const x of [-w*.255,w*.255]){box(group,x,.98,-d*.39,.065,.35,.065,M.frame);smallScreen(group,x,1.23,-d*.35,w*.4,.38,x<0?'planet':'layout',object.room_id);}
      box(group,0,.835,-d*.065,w*.58,.026,.2,M.rubber);chair(group,0,d*.24);
    }else if(kind==='server_rack'){
      box(group,0,h/2,-d*.4,w,h,.08,M.frame);for(const x of [-w/2+.03,w/2-.03])box(group,x,h/2,0,.06,h,d,M.frame);
      for(let i=0;i<7;i++){const y=.16+i*.275;box(group,0,y,0,w-.1,.225,d-.06,M.dark);for(let v=0;v<4;v++)box(group,-w*.28+v*.035,y,d*.465,.012,.11,.008,M.frame);box(group,w*.27,y,d*.47,.047,.016,.01,i%2?M.indicator:M.amber);}
      box(group,0,h-.025,0,w,.04,d,M.frame);
    }else if(kind==='bunk'){
      // Dimensions use the existing 2.08m x .90m x 2.12m authored assembly.
      // These details are not a safety-standard, comfort or structural claim.
      for(const x of [-w/2+.055,w/2-.055])for(const z of [-d/2+.05,d/2-.05])box(group,x,h/2,z,.06,h,.06,M.frame);
      for(const [berth,y] of [['lower',.34],['upper',1.27]]){
        const deck=box(group,0,y,0,w-.05,.075,d-.04,M.frame);deck.name='bunk_'+berth+'_deck';
        const mattressTop=y+.15;
        softBox(group,'bunk_'+berth+'_mattress',0,y+.095,0,w-.16,.11,d-.12,.032,M.cloth);
        softBox(group,'bunk_'+berth+'_pillow',-w*.32,mattressTop+.048,0,.42,.096,d-.22,.046,M.ivory);
        blanket(group,'bunk_'+berth+'_blanket',w*.11,mattressTop+.018,.015,w*.60,d-.06);
      }
      // The upper front guard stops before the ladder; its open access bay is
      // dimensioned separately so decorative rails cannot silently seal it.
      const guardLeft=-w/2+.11,guardRight=w*.20,guardBottom=1.27,guardTop=1.78;
      for(const x of [guardLeft,guardRight]){const post=box(group,x,(guardBottom+guardTop)/2,d/2-.055,.03,guardTop-guardBottom,.03,M.metal);post.name='bunk_upper_guard_post';}
      for(const y of [1.57,guardTop]){const rail=cylinder(group,(guardLeft+guardRight)/2,y,d/2-.055,.016,guardRight-guardLeft,M.metal,0,Math.PI/2);rail.name='bunk_upper_front_guard';}
      for(const x of [-w/2+.055,w/2-.055]){const rail=cylinder(group,x,guardTop,0,.016,d-.12,M.metal,Math.PI/2);rail.name='bunk_upper_end_guard';}
      for(const x of [w*.27,w*.43]){const stile=box(group,x,.92,d/2-.025,.032,1.84,.04,M.metal);stile.name='bunk_ladder_stile';}
      for(let i=0;i<5;i++){const rung=box(group,w*.35,.22+i*.34,d/2-.022,w*.18,.028,.035,M.metal);rung.name='bunk_ladder_rung';}
      group.userData.bunkGeometry={contract:'authored_bunk_detail_v1',upperMattressTop:1.42,guardTop,
        frontAccessX:[guardRight+.016,w/2-.085],ladderStileX:[w*.27,w*.43],
        collision:'unchanged_conservative_assembly_bounds',physicsOrSafetyValidation:false};
    }else if(kind==='galley'){
      // Original static food-preparation fixtures inside the existing galley
      // volume. Appliances stay closed; no water, heating or refrigeration is
      // simulated. The sink is a cavity, not a dark decal over a solid slab.
      const part=(name,x,y,z,bw,bh,bd,material=M.metal)=>{
        const mesh=box(group,x,y,z,bw,bh,bd,material);mesh.name='galley_'+name;return mesh;
      };
      const front=d/2-.055,back=-d/2+.025,counterTop=.89;
      part('plinth',0,.055,-.015,w-.07,.11,d-.09,M.dark);
      part('base_floor',0,.125,-.015,w-.055,.04,d-.07,M.frame);
      part('base_back',0,.49,back,w-.035,.69,.025,M.frame);
      for(const x of [-w/2+.023,w/2-.023])part('side_panel',x,.49,-.015,.035,.70,d-.06,M.ivory);
      // Left utility cupboard, narrow drawers and a distinct sealed food-cold
      // compartment. A gasket, pull and toe grille provide physical cues.
      part('utility_door',-w*.255,.46,front,w*.465,.65,.027,M.ivory);
      part('utility_pull',-w*.085,.49,front+.027,.022,.18,.023,M.frame);
      for(let i=0;i<3;i++){
        part('drawer_'+i,w*.065,.248+i*.213,front,w*.14,.196,.027,M.ivory);
        part('drawer_pull_'+i,w*.065,.278+i*.213,front+.024,w*.09,.017,.022,M.frame);
      }
      const coldX=w*.328,coldW=w*.302;
      part('cold_gasket',coldX,.461,front-.002,coldW+.02,.682,.02,M.rubber);
      part('cold_door',coldX,.461,front+.012,coldW,.656,.025,M.metal);
      part('cold_pull',coldX+coldW*.32,.53,front+.039,.023,.265,.024,M.frame);
      for(let i=0;i<4;i++)part('cold_vent_'+i,coldX,.039+i*.019,front-.015,coldW-.055,.007,.012,M.metal);
      // Build the counter as four strips around the basin opening. There is
      // deliberately no full-width solid countertop crossing the sink mouth.
      const sinkX=-w*.25,sinkZ=.04,sinkW=.46,sinkD=.42;
      const sx0=sinkX-sinkW/2,sx1=sinkX+sinkW/2,sz0=sinkZ-sinkD/2,sz1=sinkZ+sinkD/2;
      part('counter_left',(-w/2+sx0)/2,.87,0,sx0+w/2,.04,d,M.metal);
      part('counter_prep',(sx1+w/2)/2,.87,0,w/2-sx1,.04,d,M.metal);
      part('counter_rear',sinkX,.87,(-d/2+sz0)/2,sinkW,.04,sz0+d/2,M.metal);
      part('counter_front',sinkX,.87,(sz1+d/2)/2,sinkW,.04,d/2-sz1,M.metal);
      const basinFloor=.689,wallTop=.89,wallBottom=.684;
      part('sink_bottom',sinkX,basinFloor-.006,sinkZ,sinkW,.012,sinkD,M.metal);
      for(const x of [sx0+.006,sx1-.006])part('sink_side',x,(wallTop+wallBottom)/2,sinkZ,.012,wallTop-wallBottom,sinkD,M.metal);
      for(const z of [sz0+.006,sz1-.006])part('sink_end',sinkX,(wallTop+wallBottom)/2,z,sinkW-.024,wallTop-wallBottom,.012,M.metal);
      for(const x of [sx0,sx1])part('sink_rim_side',x,.891,sinkZ,.022,.012,sinkD+.022,M.metal);
      for(const z of [sz0,sz1])part('sink_rim_end',sinkX,.891,z,sinkW-.022,.012,.022,M.metal);
      const drain=cylinder(group,sinkX,basinFloor+.003,sinkZ,.024,.006,M.dark);drain.name='galley_sink_drain';
      for(const x of [-.012,0,.012])part('drain_slot',sinkX+x,basinFloor+.0065,sinkZ,.003,.001,.025,M.metal);
      // One continuous curved spout reaches the open basin. TubeGeometry keeps
      // the bend volumetric, including when imported through the GLB path.
      const path=new THREE.CatmullRomCurve3([
        new THREE.Vector3(sinkX,.90,sz0-.055),new THREE.Vector3(sinkX,1.115,sz0-.055),
        new THREE.Vector3(sinkX,1.185,sz0+.025),new THREE.Vector3(sinkX,1.115,sinkZ-.025)
      ]);
      const spout=new THREE.Mesh(new THREE.TubeGeometry(path,24,.012,10,false),M.metal);spout.name='galley_faucet_spout';spout.castShadow=true;group.add(spout);
      const base=cylinder(group,sinkX,.902,sz0-.055,.031,.024,M.frame);base.name='galley_faucet_base';
      const valve=cylinder(group,sx1+.062,.914,sz0-.045,.021,.049,M.metal);valve.name='galley_faucet_valve';
      part('faucet_lever',sx1+.062,.943,sz0-.020,.016,.014,.076,M.frame);
      part('backsplash',0,1.055,back,w-.018,.33,.028,M.ivory);
      // Upper pantry and enclosed warming appliance share a supported carcass.
      // The appliance has a real cavity/turntable behind a transparent door.
      const upperBottom=1.28,upperTop=1.71,upperBack=-d/2+.018,upperFront=.135;
      part('upper_back',0,(upperBottom+upperTop)/2,upperBack,w-.03,upperTop-upperBottom,.025,M.frame);
      part('upper_shelf',0,upperBottom+.016,(upperBack+upperFront)/2,w-.03,.032,upperFront-upperBack,M.frame);
      part('upper_roof',0,upperTop-.018,(upperBack+upperFront)/2,w-.03,.036,upperFront-upperBack,M.ivory);
      for(const x of [-w/2+.025,-w*.115,w/2-.025])part('upper_side',x,(upperBottom+upperTop)/2,(upperBack+upperFront)/2,.026,upperTop-upperBottom,upperFront-upperBack,M.ivory);
      const pantryW=w*.335,pantryX=-w*.305;
      part('pantry_gasket',pantryX,1.495,upperFront-.012,pantryW+.025,.38,.022,M.rubber);
      part('pantry_door',pantryX,1.495,upperFront+.003,pantryW,.357,.022,M.ivory);
      part('pantry_latch',pantryX+pantryW*.34,1.47,upperFront+.029,.025,.12,.025,M.frame);
      for(const y of [1.365,1.625])part('pantry_hinge',pantryX-pantryW*.49,y,upperFront+.019,.025,.046,.025,M.metal);
      const ovenX=w*.19,ovenW=w*.57,windowX=ovenX-.054,windowW=ovenW-.23,windowH=.263;
      const doorY=1.493,doorZ=upperFront+.027;
      for(const y of [doorY-.157,doorY+.157])part('warming_door_horizontal',ovenX,y,doorZ,ovenW,.044,.031,M.dark);
      for(const x of [ovenX-ovenW/2+.022,ovenX+ovenW/2-.022])part('warming_door_side',x,doorY,doorZ,.044,.27,.031,M.dark);
      part('warming_controls',ovenX+ovenW/2-.089,doorY,doorZ,.09,.272,.031,M.metal);
      part('warming_window',windowX,doorY,doorZ+.002,windowW,windowH,.008,M.glass);
      part('warming_handle',windowX+windowW/2+.021,doorY,doorZ+.041,.022,.264,.025,M.ivory);
      for(const y of [doorY-.10,doorY+.10])part('warming_handle_mount',windowX+windowW/2+.021,y,doorZ+.020,.022,.022,.028,M.ivory);
      for(const y of [doorY-.069,doorY+.066]){
        const dial=cylinder(group,ovenX+ovenW/2-.088,y,doorZ+.025,.027,.024,M.frame,Math.PI/2);dial.name='galley_warming_dial';
        part('warming_dial_marker',ovenX+ovenW/2-.088,y+.013,doorZ+.039,.004,.012,.004,M.ivory);
      }
      const tray=cylinder(group,windowX,upperBottom+.046,-.05,.128,.017,M.ivory);tray.name='galley_warming_tray';
      for(let i=0;i<5;i++)part('warming_vent_'+i,ovenX-.22+i*.055,upperTop-.052,upperFront+.011,.034,.008,.009,M.dark);
      part('task_strip',0,upperBottom-.009,-.045,w-.16,.013,.028,M.lamp);
      group.userData.galleyGeometry={contract:'authored_galley_detail_v1',counterTop,
        basin:{openingMin:[sx0+.012,sz0+.012],openingMax:[sx1-.012,sz1-.012],floorY:basinFloor,depth:counterTop-basinFloor},
        prepSurface:{min:[sx1+.012,-d/2],max:[w/2,d/2]},
        staticComponents:['recessed_sink','curved_faucet','utility_cupboard','drawers','cold_food_compartment','pantry','warming_appliance'],
        collision:'unchanged_conservative_assembly_bounds',applianceSimulation:false,pressureOrLifeSupportClaim:false};
    }else if(kind==='meal_station'){
      // Original static two-seat meal station, not a seated-avatar/comfort model.
      // The footprint includes the bench and table so collision is conservative.
      for(const x of [-.53,.53])for(const z of [-.565,-.215]){
        const foot=cylinder(group,x,.01,z,.035,.02,M.rubber);foot.name='meal_bench_foot';
        const leg=box(group,x,.205,z,.038,.37,.038,M.frame);leg.name='meal_bench_leg';
      }
      const support=box(group,0,.385,-.39,1.17,.055,.44,M.frame);support.name='meal_bench_support';
      for(const side of [-1,1]){
        softBox(group,'meal_seat_'+side,side*.295,.455,-.39,.555,.085,.42,.025,M.seat);
        softBox(group,'meal_back_'+side,side*.295,.765,-.585,.555,.47,.075,.025,M.seat);
        const post=box(group,side*.565,.675,-.595,.035,.68,.035,M.frame);post.name='meal_back_post';
      }
      softBox(group,'meal_bench_top_rail',0,1.026,-.595,1.18,.028,.042,.012,M.frame);
      // A broad floor plate and pedestal visibly support the table; the actual
      // underside remains open instead of filling the furniture with a box.
      softBox(group,'meal_table_floor_plate',0,.025,.30,.65,.05,.42,.022,M.frame);
      const pedestal=cylinder(group,0,.3725,.30,.057,.645,M.metal);pedestal.name='meal_table_pedestal';
      const crossbar=box(group,0,.7075,.25,.92,.038,.095,M.frame);crossbar.name='meal_table_crossbar';
      softBox(group,'meal_tabletop',0,.7425,.25,1.20,.045,.62,.018,M.ivory);
      group.userData.mealStationGeometry={contract:'authored_static_meal_station_v1',seatCount:2,
        seatSurfaceY:.4975,tableSurfaceY:.765,frontApproachZ:.63,
        collision:'conservative_whole_assembly_bounds',seatedAvatarInteraction:false,
        ergonomicOrSafetyValidation:false,foodOrApplianceSimulation:false};
    }else if(kind==='personal_storage'||kind==='sample_storage'){
      cabinet(group,w,h-.025,d-.035);if(kind==='sample_storage')for(let y=.2;y<h-.1;y+=.32)box(group,-w*.28,y,d/2-.004,.12,.065,.008,M.amber);
    }else if(kind==='glovebox'){
      cabinet(group,w,.79,d-.02);box(group,0,.85,0,w,.075,d,M.metal);
      const bottom=.92,top=1.76;
      for(const x of [-w*.47,w*.47])for(const z of [-d*.43,d*.43])box(group,x,(bottom+top)/2,z,.04,top-bottom,.04,M.frame);
      box(group,0,top,0,w,.045,d,M.frame);box(group,0,1.34,-d*.445,w-.075,.79,.025,M.ivory);box(group,0,1.34,d*.445,w-.075,.76,.012,M.glass);
      for(const x of [-w*.23,w*.23]){torus(group,x,1.25,d*.465,.10,.018,M.rubber);cylinder(group,x,1.23,d*.32,.058,.2,M.rubber,Math.PI/2);sphere(group,x,1.18,d*.16,.076,M.rubber,[.82,1,.82]);}
      box(group,w*.3,1.85,0,w*.3,.07,d*.52,M.frame);smallScreen(group,w*.3,1.845,d*.28,w*.22,.045);
    }else if(kind==='science_bench'){
      legs(group,w-.1,d-.1,.79);box(group,0,.82,0,w,.06,d,M.ivory);box(group,-w*.31,.45,0,w*.27,.66,d-.08,M.frame);
      const x=w*.21;box(group,x,.88,.02,.27,.035,.26,M.frame);cylinder(group,x,1.055,-.065,.034,.33,M.metal);box(group,x,1.12,.02,.24,.04,.2,M.dark);
      const tube=cylinder(group,x,1.28,.055,.03,.24,M.ivory);tube.rotation.x=-.3;cylinder(group,x,1.4,.019,.045,.055,M.rubber);
      for(let i=0;i<3;i++){const bx=-w*.25+i*.16;box(group,bx,.89,.035,.12,.06,.17,M.amber);cylinder(group,bx,.98,.035,.023,.13,M.glass);}
    }else if(kind==='observation_seat'){
      legs(group,w-.12,d-.1,.28);box(group,0,.35,0,w,.17,d,M.frame);box(group,0,.83,-d*.41,w,.45,.11,M.seat);
      for(const x of [-w*.25,w*.25])box(group,x,.5,.025,w*.44,.13,d*.75,M.seat);for(const x of [-w*.46,w*.46])box(group,x,.63,.01,.085,.31,d*.8,M.seat);
    }else if(kind==='hydroponic_bed'){
      buildHydroponicBed(THREE,group,object,materials.greenhouse);
    }else if(kind==='nutrient_reservoir'){
      buildNutrientReservoir(THREE,group,object,materials.greenhouse);
    }else if(kind==='growing_rack'){
      for(const x of [-w*.47,w*.47])for(const z of [-d*.45,d*.45])box(group,x,h/2,z,.035,h,.035,M.frame);
      for(const y of [.21,.76,1.31]){
        box(group,0,y,0,w,.04,d,M.metal);box(group,0,y+.065,0,w-.09,.085,d-.08,M.ivory);box(group,0,y+.113,0,w-.14,.012,d-.13,M.soil);
        for(let i=0;i<4;i++){const x=-w*.33+i*w*.22;cylinder(group,x,y+.22,0,.008,.2,M.green);for(const side of [-1,1]){const leaf=sphere(group,x+side*.06,y+.27,.025,.08,M.leaf,[.75,.34,1.1]);leaf.rotation.z=side*.4;}}
        box(group,0,y+.43,-d*.04,w-.12,.027,.07,M.lamp);
      }
    }
    scene.add(group);equipmentGroups.set(object.id,group);
  }
  for(const item of plan.architecture){
    const group=new THREE.Group();group.position.set(...item.center);group.name=item.id;
    if(item.kind==='room_monitor'){
      const faceRoot=new THREE.Group();faceRoot.rotation.y=item.yaw;group.add(faceRoot);const [w,h,d]=item.localSize;
      box(faceRoot,0,0,0,w,h,d-.006,M.rubber);
      const face=box(faceRoot,0,0,d/2-.001,w-.035,h-.035,.001,materials.screenFor(item.monitor_role,item.room_id));
      face.userData={room_monitor:true,functional_role:item.monitor_role,monitor_room:item.room_id};
    }else if(item.kind==='greenhouse_irrigation')buildGreenhousePipe(THREE,group,item,materials.greenhouse);
    else box(group,0,0,0,...item.size,item.kind==='luminaire'?M.lamp:M.frame);scene.add(group);
  }
  for(const light of plan.lights){const point=new THREE.PointLight(light.color,light.intensity,light.distance,2);point.position.set(...light.position);scene.add(point);}
  // Apply panels to each room's inward wall face. Shared walls get separate
  // inner faces, avoiding conflicting materials on duplicate boundary boxes.
  const viewport=planObservationViewport(geometry,plan);
  for(const sourcePrimitive of geometry.primitives){
   for(let primitive of viewportWallPieces(sourcePrimitive,viewport)){
    if(primitive.role!=='wall')continue;
    const room=geometry.rooms.find(r=>plan.roomStyles[r.id]&&primitive.id.startsWith(r.id+'_'));if(!room)continue;
    const side=primitive.id.slice(room.id.length+1).split('_')[0];
    const normal=side==='west'?[1,0,0]:side==='east'?[-1,0,0]:side==='south'?[0,0,1]:side==='north'?[0,0,-1]:null;if(!normal)continue;
    if(plan.roomStyles[room.id].role==='greenhouse'){
      const low=primitive.position[1]-primitive.size[1]/2,top=Math.min(primitive.position[1]+primitive.size[1]/2,room.floor_y+2.4);
      if(top<=low)continue;primitive={...primitive,position:[primitive.position[0],(low+top)/2,primitive.position[2]],size:[primitive.size[0],top-low,primitive.size[2]]};
    }
    const axis=normal[0]?0:2,w=primitive.size[axis===0?2:0],h=primitive.size[1];
    if(hatchArchitecture){
      const cut=buildHatchStructuralMesh(THREE,primitive,materials.wallPanel(room.id,w,h),hatchArchitecture,{panelNormal:normal[axis],panelOffset:.0008});
      if(cut){scene.add(cut);continue;}
    }
    const panel=new THREE.Mesh(new THREE.PlaneGeometry(w,h),materials.wallPanel(room.id,w,h));
    panel.position.set(...primitive.position);panel.position.setComponent(axis,panel.position.getComponent(axis)+normal[axis]*(primitive.size[axis]/2+.0008));
    panel.rotation.y=normal[0]===1?Math.PI/2:normal[0]===-1?-Math.PI/2:normal[2]===-1?Math.PI:0;panel.receiveShadow=true;scene.add(panel);
   }
  }
  for(const sign of plan.signs){
    const plaque=new THREE.Group();plaque.name=sign.id;plaque.position.set(...sign.position);box(plaque,0,0,0,...sign.size,M.frame);
    const canvas=materials.canvasFactory();
    if(canvas){canvas.width=768;canvas.height=256;const ctx=canvas.getContext('2d');ctx.fillStyle='#283b43';ctx.fillRect(0,0,768,256);ctx.fillStyle=plan.roomStyles[sign.room_id].accent;ctx.fillRect(0,0,22,256);ctx.fillStyle='#e2e8df';ctx.font='600 42px Segoe UI,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText((materials.displayData?.observation&&plan.roomStyles[sign.room_id].role==='observation'?'Observation / Mars view':sign.text).slice(0,38),395,135,690);
      const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;const plane=new THREE.Mesh(new THREE.PlaneGeometry(.48,.165),new THREE.MeshStandardMaterial({map,roughness:.7,metalness:.1}));
      plane.position.set(sign.normal[0]*.016,0,sign.normal[2]*.016);plane.rotation.y=sign.normal[0]===1?Math.PI/2:sign.normal[0]===-1?-Math.PI/2:sign.normal[2]===-1?Math.PI:0;plaque.add(plane);
    }
    scene.add(plaque);
  }
  return {equipmentGroups,meshCount:[...scene.children].reduce((sum,child)=>{child.traverse(node=>{if(node.isMesh)sum++;});return sum;},0)};
}
async function start(){
  const response=await fetch('/geometry.json',{cache:'no-store'});
  if(!response.ok) throw new Error('The pinned layout could not be loaded.');
  const geometry=await response.json();
  const settingResponse=await fetch('/presentation.json',{cache:'no-store'});
  if(!settingResponse.ok)throw new Error('The bound presentation setting could not be loaded.');
  const presentation=await settingResponse.json();
  const dressing=buildRoomDressing(geometry,createDoorSystem(geometry,{hatchGeometry:false}).assemblies());
  const controller=createWalkController(geometry,{extraColliders:dressing.colliders});
  const hatchArchitecture=planHatchArchitecture(geometry,controller.doorHatchPlans());
  document.querySelector('#title').textContent=geometry.title;
  const scene=new THREE.Scene();scene.background=new THREE.Color('#303d44');
  const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
  document.querySelector('#viewport').appendChild(renderer.domElement);
  const camera=new THREE.PerspectiveCamera(68,innerWidth/innerHeight,.045,250);
  camera.rotation.order='YXZ';
  scene.add(new THREE.HemisphereLight(0xe3edf2,0x60574b,.62));
  const fill=new THREE.DirectionalLight(0xfff0d0,.25);fill.position.set(6,12,3);scene.add(fill);
  const viewport=planObservationViewport(geometry,dressing);
  const displayData=createMarsDisplayData(geometry,presentation,viewport);
  const dressingMaterials=createDressingMaterials(THREE,dressing,{displayData,greenhouseGeometry:geometry,doorStates:controller.doorStates()});
  if(displayData){
    const destination=displayData.observation||'Observation';
    document.querySelector('#description').textContent=displayData.observation?'Explore the habitat. The surface window is in '+destination+', reached through main circulation. Monitors show sourced Mars reference facts and dated archives, not live local weather.':'Explore the habitat. Monitors show sourced references and dated archives; this layout has no surface window.';
  }
  for(const primitive of geometry.primitives){
    const room=geometry.rooms.find(r=>primitive.id.startsWith(r.id+'_'));
    const material=dressingMaterials.surface(primitive.role,room?.id);
    if(primitive.role==='floor'&&material.map)material.map.repeat.set(Math.max(1,primitive.size[0]),Math.max(1,primitive.size[2]));
    scene.add(createStructuralPrimitive(THREE,primitive,material,viewport,dressingMaterials,hatchArchitecture));
  }
  addRoomDressing(THREE,scene,geometry,dressing,dressingMaterials,hatchArchitecture);
  addObservationExterior(THREE,scene,viewport,presentation,geometry);
  addGreenhouseMarsExterior(THREE,scene,geometry,presentation);
  const doorMeshes=new Map();
  const frameMaterial=new THREE.MeshStandardMaterial({color:0x344955,roughness:.48,metalness:.65});
  const leafMaterial=new THREE.MeshStandardMaterial({color:0xa9babc,roughness:.45,metalness:.52});
  const panelMaterial=new THREE.MeshStandardMaterial({color:0x4f7585,roughness:.51,metalness:.37});
  const handleMaterial=new THREE.MeshStandardMaterial({color:0xe1d9ae,roughness:.3,metalness:.75});
  const initialDoors=new Map(controller.doorStates().map(d=>[d.id,d]));
  for(const assembly of controller.doorAssemblies()){
    if(assembly.kind==='pressure_hatch'){
      const hatch=buildPressureHatch(THREE,assembly.hatchPlan);hatch.setAngle(0);scene.add(hatch.fixed,hatch.pivot);
      doorMeshes.set(assembly.id,{hatch});continue;
    }
    for(const frame of assembly.frames){
      const mesh=new THREE.Mesh(new THREE.BoxGeometry(...frame.size),frameMaterial);
      mesh.position.set(...frame.center);scene.add(mesh);
    }
    const initial=initialDoors.get(assembly.id),group=new THREE.Group();
    const leaf=new THREE.Mesh(new THREE.BoxGeometry(...initial.size),leafMaterial);group.add(leaf);
    const normal=assembly.axis==='x'?0:2,along=normal===0?2:0;
    for(const side of [-1,1]){
      const size=[...initial.size];size[normal]=.008;size[along]*=.77;size[1]*=.68;
      const panel=new THREE.Mesh(new THREE.BoxGeometry(...size),panelMaterial);
      panel.position.setComponent(normal,side*(initial.size[normal]/2+.005));group.add(panel);
      const handle=new THREE.Mesh(new THREE.CylinderGeometry(.023,.023,.27,10),handleMaterial);
      handle.position.setComponent(normal,side*(initial.size[normal]/2+.055));
      handle.position.setComponent(along,initial.size[along]*.34);handle.position.y=-.12;group.add(handle);
      // Mounts visibly connect the handles to both sides of the leaf.
      for(const y of [-.23,-.01]){
        const mountingSize=[.075,.025,.075];mountingSize[normal]=.065;
        const mount=new THREE.Mesh(new THREE.BoxGeometry(...mountingSize),handleMaterial);
        mount.position.copy(handle.position);mount.position.y=y;mount.position.setComponent(normal,side*(initial.size[normal]/2+.031));group.add(mount);
      }
    }
    const head=assembly.frames.find(f=>f.id.endsWith('_head'));
    const indicatorSize=assembly.axis==='x'?[.225,.033,.22]:[.22,.033,.225];
    const indicatorMaterial=new THREE.MeshStandardMaterial({color:0xd28360,emissive:0x3f1205,roughness:.5});
    const indicator=new THREE.Mesh(new THREE.BoxGeometry(...indicatorSize),indicatorMaterial);
    indicator.position.set(...head.center);scene.add(indicator);scene.add(group);
    doorMeshes.set(assembly.id,{group,indicatorMaterial});
  }
  const cropPanel=document.querySelector('#greenhouse-control'),cropDetails=document.querySelector('#crop-details'),cropSelect=document.querySelector('#crop-bed'),cropInput=document.querySelector('#crop-shade');
  let cropControl=null,selectedBed=0,cropVisible=false;
  if(dressingMaterials.greenhouse){
    const assets=dressingMaterials.greenhouse;
    for(const [i,bed] of assets.data.beds.entries()){const option=document.createElement('option');option.value=String(i);option.textContent=bed.label+' / '+bed.crop;cropSelect.appendChild(option);}
    const refresh=shade=>{
      const data=createGreenhouseScenario(geometry,dressing,shade);setGreenhouseShade(scene,shade);assets.refresh(data,selectedBed);
      document.querySelector('#crop-shade-value').textContent=shade+'%';cropInput.value=String(shade);
      const bed=data.beds[selectedBed];document.querySelector('#crop-description').textContent=bed.stage+' · '+bed.health+' · planted '+bed.planted;
      document.querySelector('#crop-readings').textContent=data.temperature_c+' °C · '+data.relative_humidity_percent+'% RH · '+data.co2_ppm+' ppm CO₂ · water '+data.water_level_percent+'% · light '+data.canopy_light_umol_m2_s+' μmol m⁻² s⁻¹';
    };
    cropControl=createGreenhouseShadeController(40,state=>refresh(state.shade_percent));refresh(40);
    cropInput.addEventListener('input',()=>cropControl.set(Number(cropInput.value)));
    cropSelect.addEventListener('change',()=>{selectedBed=Number(cropSelect.value);refresh(cropControl.snapshot().shade_percent);});
  }
  const keys=new Set();
  const supported=new Set(['KeyW','KeyA','KeyS','KeyD','ArrowLeft','ArrowRight','KeyQ','KeyE']);
  addEventListener('keydown',e=>{if(supported.has(e.code)&&!['INPUT','TEXTAREA','BUTTON','SELECT','SUMMARY'].includes(document.activeElement.tagName)){keys.add(e.code);e.preventDefault();}});
  addEventListener('keyup',e=>keys.delete(e.code));
  const doorButton=document.querySelector('#door-toggle'),doorMessage=document.querySelector('#door-message');
  let doorNotice='',doorNoticeUntil=0;
  function interactDoor(){
    const result=controller.toggleDoor();
    doorNotice=result.ok?(result.state==='opening'?'Opening door…':'Closing door…'):result.reason;
    doorNoticeUntil=performance.now()+3500;doorButton.blur();
  }
  doorButton.addEventListener('click',interactDoor);
  addEventListener('keydown',e=>{if(e.code==='KeyF'&&!e.repeat&&!['INPUT','TEXTAREA','SELECT','SUMMARY'].includes(document.activeElement.tagName)){interactDoor();e.preventDefault();}});
  addEventListener('blur',()=>keys.clear());
  document.addEventListener('focusin',e=>{if(['INPUT','TEXTAREA','BUTTON','SELECT','SUMMARY'].includes(e.target.tagName)){keys.clear();stepRemaining=0;}});
  document.addEventListener('visibilitychange',()=>keys.clear());
  let stepAction=null,stepRemaining=0;
  for(const button of document.querySelectorAll('[data-walk]')){
    button.addEventListener('click',()=>{stepAction=button.dataset.walk;stepRemaining=.25;button.blur();});
  }
  const look=document.querySelector('#look');
  look.addEventListener('click',async()=>{try{await renderer.domElement.requestPointerLock();look.blur();}catch{look.textContent='Use keyboard turning';look.blur();}});
  document.addEventListener('pointerlockchange',()=>{look.textContent=document.pointerLockElement===renderer.domElement?'Mouse active · Esc to release':'Enable mouse look';});
  document.addEventListener('mousemove',e=>{if(document.pointerLockElement===renderer.domElement)controller.look(e.movementX,e.movementY);});
  addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
  const roomLabel=document.querySelector('#room'),movement=document.querySelector('#movement'),distance=document.querySelector('#distance');
  // The first animation timestamp can precede the setup's performance.now().
  // Start at zero elapsed time so the first rendered frame cannot reject it.
  let previous=null,lastStatus='';
  function frame(now){
    const input={forward:keys.has('KeyW'),backward:keys.has('KeyS'),left:keys.has('KeyA'),right:keys.has('KeyD'),turnLeft:keys.has('ArrowLeft')||keys.has('KeyQ'),turnRight:keys.has('ArrowRight')||keys.has('KeyE')};
    const elapsed=previous===null?0:Math.min(.05,Math.max(0,(now-previous)/1000));previous=now;
    if(stepRemaining>0){input[stepAction]=true;stepRemaining-=elapsed;}
    const state=controller.step(elapsed,input);
    for(const door of controller.doorStates()){
      const visual=doorMeshes.get(door.id);
      if(visual.hatch){visual.hatch.setAngle(door.angle);continue;}
      visual.group.position.set(...door.center);visual.group.rotation.y=door.angle;
      visual.indicatorMaterial.color.setHex(door.state==='open'?0x72b494:door.state==='closed'?0xd28360:0xe9c66d);
      visual.indicatorMaterial.emissive.setHex(door.state==='open'?0x123621:door.state==='closed'?0x3f1205:0x48330c);
    }
    if(cropControl){
      const room=geometry.rooms.find(r=>r.id===dressingMaterials.greenhouse.data.room_id),p=state.feet;
      const visible=p[0]>=room.x&&p[0]<=room.x+room.width&&p[2]>=room.z&&p[2]<=room.z+room.depth;
      if(visible!==cropVisible){cropVisible=visible;cropPanel.hidden=!visible;if(!visible)cropDetails.open=false;}
    }
    dressingMaterials.refreshDoorStates(controller.doorStates());
    const nearby=state.nearbyDoor,moving=nearby&&(nearby.state==='opening'||nearby.state==='closing');
    doorButton.disabled=!nearby||moving;
    doorButton.textContent=!nearby?'Face a nearby door · F':moving?'Door moving…':nearby.state==='closed'?'Open door · F':'Close door · F';
    doorMessage.textContent=nearby?.motionHeld?'Door paused — step away from its swing.':
      now<doorNoticeUntil?doorNotice:nearby?'Door '+nearby.state+'. Leave room for it to swing.':'Face a nearby framed door and press F to open or close it.';
    camera.position.set(state.feet[0],state.feet[1]+AVATAR.eye,state.feet[2]);camera.rotation.set(state.pitch,-state.yaw,0);
    const status=state.roomName+'|'+state.blocked;
    if(status!==lastStatus){roomLabel.textContent=state.roomName;movement.textContent=state.blocked==='door_obstruction'?'Door or frame blocks the way — open it with F':state.blocked==='furniture_obstruction'?'Furniture blocks the way — walk around it':state.blocked==='solid_obstruction'?'Wall or low ceiling — turn toward a passage':state.blocked?'No supported floor in that direction':'Walking inside the layout · unfinished materials';lastStatus=status;}
    distance.textContent='Distance walked: '+state.distance.toFixed(1)+' m';
    renderer.render(scene,camera);requestAnimationFrame(frame);
  }
  addEventListener('pagehide',event=>{if(!event.persisted)cropControl?.dispose();});
  requestAnimationFrame(frame);
}
start().catch(error=>{document.querySelector('#error').hidden=false;document.querySelector('#error').textContent='Preview could not start.\n'+error.message;document.querySelector('#movement').textContent='Preview unavailable';});
