// Original crop-room geometry and explicit illustrative controls. No live sensors,
// measured solar/thermal model, crop-care recommendation or radiation rating.
export const GREENHOUSE_CONTRACT='authored_controlled_greenhouse_v1';
export const GREENHOUSE_DEFAULT_SHADE=40;
const clampShade=value=>{if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>100)throw new TypeError('Shade must be a finite percentage from0 to100');return value;};
export function greenhouseRooms(geometry){return geometry.rooms.filter(r=>geometry.functional_program?.[r.id]==='greenhouse');}
export function greenhouseEnvelopeFor(geometry,primitive){
 const room=greenhouseRooms(geometry).find(r=>primitive.id.startsWith(r.id+'_'));
 if(!room||!['wall','ceiling'].includes(primitive.role))return null;
 if(room.width<6||room.width>12||room.depth<8||room.depth>12||room.height!==4)throw new TypeError('Greenhouse dome needs a supported6..12m by8..12m room,4m high');
 return {contract:GREENHOUSE_CONTRACT,room_id:room.id,wall_height:2.4,roof_peak:room.height-Math.max(.30,room.width*Math.PI*.94/96+.09),
  original_primitive:primitive.id,original_role:primitive.role,source_conservative_collision:true,
  minimum_clear_height:2.4,pressure_or_radiation_validation:false};
}
export function createGreenhouseScenario(geometry,plan,shade=GREENHOUSE_DEFAULT_SHADE){
 shade=clampShade(shade);const rooms=greenhouseRooms(geometry);if(!rooms.length)return null;
 if(rooms.length!==1)throw new TypeError('This greenhouse recipe supports one crop module');
 const room=rooms[0],beds=plan.objects.filter(o=>o.room_id===room.id&&o.kind==='hydroponic_bed');
 if(beds.length!==4||plan.objects.filter(o=>o.room_id===room.id&&o.kind==='nutrient_reservoir').length!==1)throw new TypeError('The crop recipe needs four placed beds and one reservoir with clear approaches');
 const kinds=[['Leaf lettuce','Young vegetative'],['Basil','Established vegetative'],['Radish greens','Early leaf stage'],['Leaf lettuce','Harvest-size study']];
 return {contract:GREENHOUSE_CONTRACT,room_id:room.id,room_name:room.name,mode:'ILLUSTRATIVE SCENARIO / NO LIVE SENSORS',
  shade_percent:shade,temperature_c:21.2,relative_humidity_percent:58,co2_ppm:1000,water_level_percent:74,
  canopy_light_umol_m2_s:Math.round(180+320*(1-shade/100)),led_contribution_umol_m2_s:180,photoperiod_hours:16,
  water_system:'Recirculation shown; flow not simulated',shielding:'Separate concept; no radiation protection validated',
  beds:beds.map((bed,i)=>({id:bed.id,label:'BED '+String(i+1).padStart(2,'0'),crop:kinds[i%4][0],stage:kinds[i%4][1],
   health:'Illustrative normal appearance',planted:'Scenario day '+String(42-[9,18,7,28][i%4]).padStart(2,'0'),scenario_day:42})),
  readings_are_simulated:true,agronomy_recommendation:false,growth_simulated:false};
}
export function createGreenhouseShadeController(initial=GREENHOUSE_DEFAULT_SHADE,onChange=()=>{}){
 let shade=clampShade(initial),disposed=false,revision=0;
 return {snapshot:()=>({shade_percent:shade,revision,session_local:true}),set(value){
  if(disposed)throw new Error('Greenhouse control is disposed');const next=clampShade(value);if(next===shade)return this.snapshot();
  shade=next;revision++;const snapshot=this.snapshot();onChange(snapshot);return snapshot;
 },reset(){return this.set(initial);},dispose(){disposed=true;revision++;}};
}
function mesh(THREE,group,name,geometry,material,position=[0,0,0]){const object=new THREE.Mesh(geometry,material);object.name=name;object.position.set(...position);object.receiveShadow=true;group.add(object);return object;}
function box(THREE,group,name,size,position,material){return mesh(THREE,group,name,new THREE.BoxGeometry(...size),material,position);}
function tube(THREE,group,name,points,radius,material){const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)),false,'centripetal');return mesh(THREE,group,name,new THREE.TubeGeometry(curve,Math.max(8,(points.length-1)*10),radius,7,false),material);}
export function paintGreenhousePanel(ctx,data,selected=0){
 const bed=data.beds[selected]??data.beds[0];ctx.fillStyle='#102722';ctx.fillRect(0,0,1024,512);ctx.fillStyle='#e5f1d9';ctx.font='600 38px Segoe UI,sans-serif';ctx.fillText('CONTROLLED CROP MODULE',28,49);
 ctx.fillStyle='#d9c78d';ctx.font='23px monospace';ctx.fillText(data.mode,28,85);
 const fields=[['AIR',data.temperature_c+' C / '+data.relative_humidity_percent+'% RH'],['CO2',data.co2_ppm+' ppm'],['WATER',data.water_level_percent+'% / scenario'],['LIGHT',data.canopy_light_umol_m2_s+' umol m-2 s-1'],['SHADE',data.shade_percent+'% / session control']];
 ctx.font='29px Segoe UI,sans-serif';for(let i=0;i<fields.length;i++){ctx.fillStyle='#9dbea8';ctx.fillText(fields[i][0],30,137+i*52);ctx.fillStyle='#f0f3df';ctx.fillText(fields[i][1],155,137+i*52);}
 if(bed){ctx.fillStyle='#ace0a2';ctx.font='600 29px Segoe UI,sans-serif';ctx.fillText(bed.label+' / '+bed.crop,540,137,455);ctx.font='25px Segoe UI,sans-serif';ctx.fillText(bed.stage,540,186,450);ctx.fillText(bed.health,540,235,450);ctx.fillText('Planted: '+bed.planted,540,284,450);ctx.fillText('No live growth forecast',540,333,450);}
 ctx.fillStyle='#d9c78d';ctx.font='22px Segoe UI,sans-serif';ctx.fillText('Illustrative values; not crop-care instructions.',28,435);ctx.fillText('Shade controls daylight. Radiation shielding is separate.',28,478);
}
export function createGreenhouseAssets(THREE,data,canvasFactory){
 if(!data)return null;const frame=new THREE.MeshStandardMaterial({color:0xa3b0a8,roughness:.42,metalness:.6}),tray=new THREE.MeshStandardMaterial({color:0xc2cdb6,roughness:.55,metalness:.15}),dark=new THREE.MeshStandardMaterial({color:0x283d38,roughness:.7}),water=new THREE.MeshStandardMaterial({color:0x638d91,roughness:.22,metalness:0}),leaf=new THREE.MeshStandardMaterial({color:0x4c8841,roughness:.8,side:THREE.DoubleSide,vertexColors:true}),stem=new THREE.MeshStandardMaterial({color:0x6f9a45,roughness:.75}),glass=new THREE.MeshStandardMaterial({color:0xc9dfd0,roughness:.25,metalness:0,transparent:true,opacity:.26,depthWrite:false,side:THREE.DoubleSide}),shade=new THREE.MeshStandardMaterial({color:0xb7b9a0,roughness:.72,metalness:.25,side:THREE.DoubleSide});
 const panelCanvas=canvasFactory();if(!panelCanvas)throw new TypeError('Greenhouse panel requires a canvas');panelCanvas.width=1024;panelCanvas.height=512;paintGreenhousePanel(panelCanvas.getContext('2d'),data);
 const panelMap=new THREE.CanvasTexture(panelCanvas);panelMap.colorSpace=THREE.SRGBColorSpace;
 const panel=new THREE.MeshStandardMaterial({color:0xffffff,map:panelMap,emissive:0xffffff,emissiveMap:panelMap,emissiveIntensity:.25,roughness:.65});
 const labelCanvas=canvasFactory();labelCanvas.width=1024;labelCanvas.height=512;const ctx=labelCanvas.getContext('2d');ctx.fillStyle='#19362b';ctx.fillRect(0,0,1024,512);
 data.beds.forEach((bed,i)=>{ctx.fillStyle='#d7e7bc';ctx.font='600 31px Segoe UI,sans-serif';ctx.fillText(bed.label+' / '+bed.crop,24,i*128+43);ctx.fillStyle='#b7cdb6';ctx.font='25px Segoe UI,sans-serif';ctx.fillText(bed.stage+' / authored scenario',24,i*128+86);});
 const labelMap=new THREE.CanvasTexture(labelCanvas);labelMap.colorSpace=THREE.SRGBColorSpace;const labels=new THREE.MeshStandardMaterial({color:0xffffff,map:labelMap,roughness:.8});
 return {frame,tray,dark,water,leaf,stem,glass,shade,panel,labels,panelMap,labelMap,panelCanvas,data,refresh(next,selected=0){paintGreenhousePanel(panelCanvas.getContext('2d'),next,selected);panelMap.needsUpdate=true;this.data=next;}};
}
export function buildGreenhouseEnvelope(THREE,primitive,geometry,assets){
 const spec=greenhouseEnvelopeFor(geometry,primitive);if(!spec)return null;if(!assets)throw new TypeError('Greenhouse materials missing');
 const room=geometry.rooms.find(r=>r.id===spec.room_id),group=new THREE.Group();group.name=primitive.id;group.position.set(...primitive.position);group.userData.greenhouse_envelope=spec;
 const local=p=>p.map((v,i)=>v-primitive.position[i]);
 if(primitive.role==='wall'){
  const low=primitive.position[1]-primitive.size[1]/2,top=Math.min(primitive.position[1]+primitive.size[1]/2,room.floor_y+spec.wall_height);
  if(top>low+1e-7)box(THREE,group,primitive.id+'_retained_base',[primitive.size[0],top-low,primitive.size[2]],local([primitive.position[0],(low+top)/2,primitive.position[2]]),assets.tray);
  return group;
 }
 const cx=room.x+room.width/2,base=room.floor_y+spec.wall_height,rise=spec.roof_peak-spec.wall_height;
 const point=(theta,z,offset=0)=>[cx+(room.width/2+offset)*Math.cos(theta),base+(rise+offset)*Math.sin(theta),z];
 const surface=(t0,t1,z0,z1,offset=0)=>{
  const positions=[],indices=[];for(let n=0;n<=12;n++){const t=t0+(t1-t0)*n/12;for(const z of [z0,z1])positions.push(...local(point(t,z,offset)));if(n<12){const a=n*2;indices.push(a,a+1,a+2,a+1,a+3,a+2);}}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setIndex(indices);g.computeVertexNormals();return g;
 };
 mesh(THREE,group,primitive.id+'_daylight_glazing',surface(0,Math.PI,room.z,room.z+room.depth),assets.glass).userData={daylight_aperture:true,radiation_rating:false};
 for(let i=0;i<=5;i++){const z=room.z+room.depth*i/5,pts=Array.from({length:21},(_,j)=>local(point(Math.PI*j/20,z,.018)));tube(THREE,group,primitive.id+'_rib_'+i,pts,.026,assets.frame);}
 for(const t of [0,Math.PI/4,Math.PI/2,3*Math.PI/4,Math.PI])tube(THREE,group,primitive.id+'_purlin_'+t,[local(point(t,room.z,.018)),local(point(t,room.z+room.depth,.018))],.020,assets.frame);
 for(const z of [room.z,room.z+room.depth]){
  const shape=new THREE.Shape();shape.moveTo(-room.width/2,0);for(let i=0;i<=24;i++){const t=Math.PI-Math.PI*i/24;shape.lineTo(room.width/2*Math.cos(t),rise*Math.sin(t));}shape.closePath();
  mesh(THREE,group,primitive.id+'_gable_'+z,new THREE.ShapeGeometry(shape,24),assets.glass,local([cx,base,z])).userData={daylight_aperture:true,radiation_rating:false};
 }
 // One louver per narrow cross-roof band. Rotation changes visible coverage.
 for(let i=0;i<24;i++){
  const theta=Math.PI*(i+.5)/24,position=point(theta,room.z+room.depth/2,.055),pivot=new THREE.Group();pivot.name=primitive.id+'_shade_pivot_'+i;pivot.position.set(...local(position));group.add(pivot);
  const tangent=[-room.width/2*Math.sin(theta),rise*Math.cos(theta)],baseAngle=Math.atan2(tangent[1],tangent[0]);
  const blade=box(THREE,pivot,primitive.id+'_louver_'+i,[Math.hypot(...tangent)*Math.PI/24*.94,.018,room.depth-.05],[0,0,0],assets.shade);
  pivot.userData={greenhouse_shade_louver:true,base_angle:baseAngle,room_id:room.id};blade.userData={shade_not_radiation_shield:true};
 }
 setGreenhouseShade(group,assets.data.shade_percent);return group;
}
export function setGreenhouseShade(root,value){value=clampShade(value);root.traverse(o=>{if(o.userData.greenhouse_shade_louver)o.rotation.z=o.userData.base_angle+(1-value/100)*Math.PI/2;});}
export function buildHydroponicBed(THREE,group,object,assets){
 const [w,h,d]=object.localSize,prefix=object.id,bedIndex=Math.max(0,assets.data.beds.findIndex(b=>b.id===object.id));
 for(const x of [-w/2+.07,w/2-.07])for(const z of [-d/2+.07,d/2-.07])box(THREE,group,prefix+'_leg',[.045,.76,.045],[x,.38,z],assets.frame);
 // Tray front is recessed behind its label; both remain in the declared bed bounds.
 box(THREE,group,prefix+'_tray',[w,.15,d-.04],[0,.80,0],assets.tray);box(THREE,group,prefix+'_water',[w-.10,.015,d-.10],[0,.87,0],assets.water);
 for(const z of [-d*.27,d*.27]){box(THREE,group,prefix+'_channel',[w-.12,.06,.15],[0,.91,z],assets.tray);tube(THREE,group,prefix+'_return',[[-w/2+.07,.69,z],[w/2-.07,.69,z]],.018,assets.dark);}
 const positions=[],colors=[],indices=[];
 for(let n=0;n<8;n++){
  const px=-w*.34+(n%4)*w*.226,pz=n<4?-d*.24:d*.24;
  mesh(THREE,group,prefix+'_net_cup_'+n,new THREE.CylinderGeometry(.048,.04,.085,10),assets.dark,[px,.947,pz]);
  mesh(THREE,group,prefix+'_stem_'+n,new THREE.CylinderGeometry(.007,.010,.145,7),assets.stem,[px,1.035,pz]);
  for(let leaf=0;leaf<6;leaf++){
   const angle=leaf*Math.PI/3+n*.63,scale=.83+.17*Math.sin(n*2.31+leaf),length=(bedIndex===1?.20:.23)*scale,wide=(bedIndex===1?.067:.105)*scale,start=positions.length/3;
   // Single base/tip vertices and indexed fans avoid collapsed endpoint quads.
   positions.push(px,1.02,pz);colors.push(.9,.9,.83);
   for(let u=1;u<=5;u++)for(let v=0;v<=4;v++){
    const t=u/6,s=(v-2)/2,width=wide*Math.sin(Math.PI*t),a=length*t,b=width*s;
    positions.push(px+Math.cos(angle)*a-Math.sin(angle)*b,1.02+.14*t+.035*Math.sin(Math.PI*t)-.035*s*s,pz+Math.sin(angle)*a+Math.cos(angle)*b);
    const tone=.84+.14*Math.sin(n+leaf*2+t*3);colors.push(tone,tone*(bedIndex===2?.95:1),tone*.92);
    if(u<5&&v<4){const i=start+1+(u-1)*5+v;indices.push(i,i+5,i+1,i+1,i+5,i+6);}
   }
   const tip=positions.length/3;positions.push(px+Math.cos(angle)*length,1.16,pz+Math.sin(angle)*length);colors.push(.9,.9,.83);
   for(let v=0;v<4;v++){indices.push(start,start+1+v,start+2+v);const last=start+21+v;indices.push(last,tip,last+1);}
  }
 }
 const leaves=new THREE.BufferGeometry();leaves.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));leaves.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));leaves.setIndex(indices);leaves.computeVertexNormals();
 mesh(THREE,group,prefix+'_curved_leaves',leaves,assets.leaf).userData={authored_crop:assets.data.beds[bedIndex],living_plant_simulation:false};
 const plaque=new THREE.PlaneGeometry(w-.12,.17),uv=plaque.attributes.uv;for(let i=0;i<uv.count;i++)uv.setY(i,(3-bedIndex+uv.getY(i))/4);
 mesh(THREE,group,prefix+'_bed_label',plaque,assets.labels,[0,.78,d/2-.008]).userData={crop_bed_id:object.id,scenario_label:true};
}
export function buildNutrientReservoir(THREE,group,object,assets){
 const [w,h,d]=object.localSize,prefix=object.id;
 box(THREE,group,prefix+'_base',[w,.09,d],[0,.045,0],assets.frame);
 box(THREE,group,prefix+'_water',[w-.13,.70,d-.13],[0,.44,0],assets.water);
 box(THREE,group,prefix+'_tank',[w-.07,1.10,d-.07],[0,.62,0],assets.glass);
 box(THREE,group,prefix+'_lid',[w-.03,.055,d-.03],[0,1.195,0],assets.tray);
 box(THREE,group,prefix+'_pump',[.22,.22,.19],[w*.28,.20,0],assets.dark);
 for(const x of [-w*.22,w*.22])tube(THREE,group,prefix+'_service_pipe',[[x,.32,0],[x,1.33,0],[x,1.33,-d*.4]],.021,assets.frame);
 // Place the reading face ahead of the rear irrigation riser, inside the unchanged equipment footprint.
 box(THREE,group,prefix+'_display_back',[w-.08,.56,.048],[0,1.62,d*.27],assets.frame);
 mesh(THREE,group,prefix+'_readings',new THREE.PlaneGeometry(w-.10,.54),assets.panel,[0,1.62,d*.27+.025]).userData={greenhouse_readings:true,mode:assets.data.mode};
}
export function buildGreenhousePipe(THREE,group,item,assets){
 tube(THREE,group,item.id+'_tube',item.points.map(p=>p.map((v,i)=>v-item.center[i])),.020,assets.frame).userData={recirculation_path:true,fluid_simulation:false};
}
