// Authored equipment, not a reconstruction or a pressure/life-support model.
export const DRESSING_CONTRACT='authored_habitat_equipment_plan_v1';
const DR_ROLES={
  equipment_vestibule:{accent:'#c99158',floor:'#48535a',light:0xe3eff4,equipment:[['eva_lockers',1.45,.62,2.15],['gear_bench',1.3,.55,.62],['hose_station',.65,.4,1.6]]},
  airlock:{accent:'#c9af69',floor:'#46545a',light:0xeaf5ff,equipment:[['airlock_control',.72,.36,1.82],['filter_cylinders',.66,.45,1.68]]},
  operations:{accent:'#739aae',floor:'#414c59',light:0xdcecff,equipment:[['operations_console',1.9,1.38,1.52],['server_rack',.66,.65,2.12],['operations_console',1.55,1.38,1.52]]},
  habitat:{accent:'#c5a985',floor:'#686354',light:0xffdfb5,equipment:[['bunk',2.08,.9,2.12],['galley',1.42,.68,1.74],['personal_storage',.72,.6,1.86]]},
  laboratory:{accent:'#81b6b1',floor:'#536568',light:0xedfffa,equipment:[['glovebox',1.58,.8,1.9],['science_bench',1.52,.76,1.52],['sample_storage',.66,.52,1.88]]},
  observation:{accent:'#a5b993',floor:'#555f54',light:0xffe8c7,equipment:[['observation_seat',1.26,.78,1.08],['growing_rack',1.18,.59,1.9]]},
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
export function buildRoomDressing(geometry,doorAssemblies=[]){
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
        const p=wallPlacement(room,.065,.15,room.height-.12,wall,(i+.5)/count);
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
    const center=[room.x+room.width/2,room.floor_y+room.height-.065,room.z+room.depth/2];
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
  // Bound renderer complexity as well as collision complexity.
  DR_assert(plan.objects.length<=32&&plan.architecture.length<=96&&plan.lights.length<=12,'Dressing budget exceeded');
  return DR_freeze(plan);
}
