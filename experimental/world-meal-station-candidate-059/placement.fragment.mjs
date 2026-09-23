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
