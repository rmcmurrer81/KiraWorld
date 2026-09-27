// Original fictional hatch authoring. No pressure, sealing or latch simulation.
// Shared recipe/builder for a future preview AND export integration, not enabled.
export const HATCH_CONTRACT='authored_pressure_hatch_geometry_v1';
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const require=(ok,message)=>{if(!ok)throw new TypeError(message);};
const box=(center,size)=>({min:center.map((v,i)=>v-size[i]/2),max:center.map((v,i)=>v+size[i]/2)});
const add=(a,b)=>a.map((v,i)=>v+b[i]);

export function pressureHatchIds(geometry){
  require(geometry?.contract==='compiled_blueprint_geometry_v1'&&geometry.units==='meters','Expected compiled meter-based geometry.');
  require(Array.isArray(geometry?.rooms)&&Array.isArray(geometry?.portals),'Invalid room/portal geometry.');
  require(geometry.functional_program===undefined||(geometry.functional_program&&typeof geometry.functional_program==='object'&&!Array.isArray(geometry.functional_program)),'Invalid functional program.');
  const rooms=new Map(geometry.rooms.map(r=>[r.id,r])),ids=new Set();
  for(const [id,role] of Object.entries(geometry.functional_program??{})){
    if(role!=='airlock')continue;
    require(rooms.get(id)?.access==='walkable_layout','Unavailable authored airlock.');
    const members=geometry.portals.filter(p=>p.room_a===id||p.room_b===id);
    require(members.length===2&&members.every(p=>p.state==='open_passage'&&rooms.get(p.room_a)?.access==='walkable_layout'&&rooms.get(p.room_b)?.access==='walkable_layout'),'Airlock needs exactly two supported passages.');
    members.forEach(p=>ids.add(p.id));
  }
  return Object.freeze([...ids]);
}

// All dimensions below use local [across opening, up, toward room A].
// The leaf sits outside the wall face so its overlap cannot clip the old wall.
export function planPressureHatch(geometry,portalId){
  if(!pressureHatchIds(geometry).includes(portalId))return null;
  const p=geometry.portals.find(p=>p.id===portalId),a=geometry.rooms.find(r=>r.id===p.room_a),b=geometry.rooms.find(r=>r.id===p.room_b);
  const n=p.axis==='x'?0:2,t=n===0?2:0;
  require((p.axis==='x'||p.axis==='z')&&[p.width,p.height,p.center,p.coordinate,a.floor_y,b.floor_y].every(Number.isFinite)
    &&p.width>=.9&&p.width<=3&&p.height>=1.9&&p.height<=3.2&&a.floor_y===b.floor_y,'Hatch recipe needs a supported level passage.');
  const W=p.width,H=p.height,sign=Math.sign(a[p.axis]+a[p.axis==='x'?'width':'depth']/2-p.coordinate);
  require(Math.abs(sign)===1,'Hatch opening has no interior side.');
  const along=p.axis==='x'?'z':'x',span=p.axis==='x'?'depth':'width';
  require(H+.18<=Math.min(a.height,b.height)&&p.center-W/2-.18>=Math.max(a[along],b[along])
    &&p.center+W/2+.18<=Math.min(a[along]+a[span],b[along]+b[span]),'The substantial hatch surround does not fit the adjacent rooms.');
  const origin=n===0?[p.coordinate,a.floor_y,p.center]:[p.center,a.floor_y,p.coordinate];
  const hingeLocal=[-W/2-.075,0,.12],leafWidth=W+.08,leafHeight=H+.04,leafCenterX=.035+leafWidth/2;
  const toWorld=v=>{const out=[...origin];out[t]+=v[0];out[1]+=v[1];out[n]+=sign*v[2];return out;};
  const fixed=[],moving=[];
  const part=(list,name,shape,center,size,material,extra={})=>{const value={id:'hatch_'+portalId+'_'+name,shape,center,size,material,...extra};list.push(value);return value;};
  const fixedRing=(name,outer,inner,depth,z,material)=>part(fixed,name,'ring',[0,0,z],[outer.width,outer.top-outer.bottom,depth],material,{outer,inner});
  const aperture={width:W,bottom:0,top:H,radius:.18};
  // Partition the frame at the deep seat insert: never stack two front faces
  // or two aperture reveals in the same space. Shared boundaries are internal.
  const seatOuter={width:W+.13,bottom:-.018,top:H+.065,radius:.245};
  fixedRing('structural_surround',{width:W+.36,bottom:-.035,top:H+.18,radius:.36},seatOuter,.175,-.0075,'structure');
  // Rear trim meets the frame at z=-.095 instead of penetrating its last 9 mm.
  fixedRing('rear_beveled_trim',{width:W+.29,bottom:-.025,top:H+.145,radius:.325},{width:W+.025,bottom:-.003,top:H+.0125,radius:.1925},.018,-.104,'trim');
  fixedRing('seat_flange',seatOuter,aperture,.175,-.0075,'seat');
  // A continuous strip across the flush floor line and up both sides/top.
  // Its front face meets the closed leaf back face; this is geometry only.
  fixedRing('continuous_gasket',{width:W+.046,bottom:-.016,top:H+.023,radius:.203},
    {width:W+.018,bottom:0,top:H+.009,radius:.189},.0075,.08375,'gasket');
  const localLeafCenter=[leafCenterX,leafHeight/2,0];
  part(moving,'reinforced_leaf','solid',localLeafCenter,[leafWidth,leafHeight,.065],'leaf',
    {profile:{width:leafWidth,bottom:-leafHeight/2,top:leafHeight/2,radius:.22},bevel:.008});
  // Raised, beveled reinforcement covers both leaf faces. It is smaller than
  // the aperture on the rear side to leave the stationary gasket seat clear.
  for(const face of [-1,1]){
    const skinWidth=face<0?W-.12:W-.025,skinHeight=H-.16;
    part(moving,'skin_'+face,'solid',[leafCenterX,leafHeight/2,face*.043],[skinWidth,skinHeight,.021],'panel',
      {profile:{width:skinWidth,bottom:-skinHeight/2,top:skinHeight/2,radius:.15},bevel:.004});
    const wheelY=H*.53,depth=face*.079;
    part(moving,'control_shaft_'+face,'cylinder',[leafCenterX,wheelY,face*.049],[.032,.032,.068],'metal',{radius:.016,length:.068,axis:'z'});
    part(moving,'control_wheel_'+face,'wheel',[leafCenterX,wheelY,depth],[.224,.224,.018],'control',{radius:.103,tube:.009});
    for(const angle of [0,Math.PI/3,2*Math.PI/3]){
      const c=Math.cos(angle)*.096,s=Math.sin(angle)*.096;
      part(moving,'wheel_spoke_'+face+'_'+Math.round(angle*100),'rod',null,null,'metal',
        {from:[leafCenterX-c,wheelY-s,depth],to:[leafCenterX+c,wheelY+s,depth],radius:.007});
    }
    // A separate grab bar with two standoffs, not an unlatching control.
    const gx=leafCenterX+W*.22;
    part(moving,'grab_bar_'+face,'rod',null,null,'grab',
      {from:[gx,H*.39,face*.094],to:[gx,H*.54,face*.094],radius:.014});
    for(const y of [H*.39,H*.54])part(moving,'grab_mount_'+face+'_'+Math.round(y*1000),'rod',null,null,'metal',
      {from:[gx,y,face*.033],to:[gx,y,face*.094],radius:.010});
  }
  // One distributed dog train, actuated from either side by the through shaft.
  // Dogs are modeled retracted. There is deliberately no fake LATCHED state.
  // Three dogs along the free jamb. No keeper protrudes into the hinge sweep.
  for(const side of [1]){
    const rail=leafCenterX+side*W*.39,edge=leafCenterX+side*(W/2+.014);
    part(moving,'latch_rail_'+side,'rod',null,null,'metal',
      {from:[rail,H*.24,.070],to:[rail,H*.76,.070],radius:.009});
    part(moving,'actuator_link_'+side,'rod',null,null,'metal',
      {from:[leafCenterX,H*.53,.070],to:[rail,H*.53,.070],radius:.009});
    for(const y of [H*.25,H*.50,H*.75]){
      const suffix=side+'_'+Math.round(y*1000);
      part(moving,'dog_link_'+suffix,'rod',null,null,'metal',
        {from:[rail,y,.070],to:[edge-side*.023,y,.070],radius:.008});
      part(moving,'dog_housing_'+suffix,'box',[edge-side*.018,y,.071],[.047,.088,.043],'structure');
      part(moving,'retracted_dog_'+suffix,'box',[edge,y,.072],[.020,.039,.021],'metal');
      // The matching keeper is mechanically supported back to the seat.
      const keeperX=side*(W/2+.080),keeperZ=.192;
      part(fixed,'keeper_support_'+suffix,'box',[keeperX,y,.132],[.043,.102,.122],'structure');
      part(fixed,'keeper_'+suffix,'box',[keeperX,y,keeperZ],[.042,.084,.040],'metal');
    }
  }
  for(const y of [H*.22,H*.79]){
    const suffix=Math.round(y*1000),axisX=hingeLocal[0],axisZ=hingeLocal[2];
    part(fixed,'hinge_anchor_'+suffix,'box',[axisX-.048,y,.033],[.102,.20,.13],'structure');
    for(const dy of [-.066,.066]){
      part(fixed,'hinge_bridge_'+suffix+'_'+Math.round(dy*1000),'box',[axisX-.027,y+dy,.110],[.055,.050,.070],'metal');
      part(fixed,'hinge_knuckle_'+suffix+'_'+Math.round(dy*1000),'cylinder',[axisX,y+dy,axisZ],[.042,.063,.042],'metal',{radius:.021,length:.063,axis:'y'});
    }
    part(moving,'hinge_knuckle_'+suffix,'cylinder',[0,y,0],[.042,.062,.042],'metal',{radius:.021,length:.062,axis:'y'});
    part(moving,'hinge_leaf_bridge_'+suffix,'box',[.030,y,0],[.060,.044,.028],'metal');
  }
  const id='pressure_hatch:'+portalId;
  function localBox(item){
    if(item.shape==='rod'){
      const min=item.from.map((v,i)=>Math.min(v,item.to[i])-item.radius),max=item.from.map((v,i)=>Math.max(v,item.to[i])+item.radius);
      return {min,max};
    }
    if(item.shape==='ring')return null;
    return box(item.center,item.size);
  }
  const colliders=[];
  for(const list of [fixed,moving])for(const item of list){
    if(item.shape==='ring'){
      const o=item.outer,i=item.inner,depth=item.size[2],middle=(o.bottom+i.top-i.radius)/2;
      // Partition the ring proxy; never fill its doorway with one solid AABB.
      const pieces=[
        ['left',[-(o.width+i.width)/4,middle,item.center[2]],[(o.width-i.width)/2,i.top-i.radius-o.bottom,depth]],
        ['right',[(o.width+i.width)/4,middle,item.center[2]],[(o.width-i.width)/2,i.top-i.radius-o.bottom,depth]],
        ['head',[0,(o.top+i.top-i.radius)/2,item.center[2]],[o.width,o.top-i.top+i.radius,depth]],
        ['sill',[0,(o.bottom+i.bottom)/2,item.center[2]],[i.width,i.bottom-o.bottom,depth]],
      ];
      for(const [suffix,center,size] of pieces)if(size.every(v=>v>0))colliders.push({id:item.id+'_'+suffix,owner:item.id,motion:'static',...box(center,size)});
    }else colliders.push({id:item.id,owner:item.id,motion:list===moving?'kinematic':'static',...localBox(item)});
  }
  const hinge=toWorld(hingeLocal),openAngle=sign*(p.axis==='x'?1:-1)*Math.PI/2;
  const result={contract:HATCH_CONTRACT,id,portalId,axis:p.axis,normalSign:sign,origin,hinge,hingeLocal,openAngle,
    aperture,leafWidth,leafHeight,localLeafCenter,fixed,moving,colliders,
    provenance:{originalAuthoredGeometry:true,externalTextures:false},
    capabilities:{pressureSimulation:false,sealCertification:false,latchSimulation:false,latchState:'static_retracted',enabledInViewer:false},
    limits:{clearWidth:W,centralStandingClearHeight:H-.18,thresholdAboveFloor:0,requiresRevisedSwingAdmission:true,
      // Cut this small region out of the decorative floor mesh, not the walking
      // support surface. Otherwise y=0 floor and flush sill top z-fight.
      requiresFlushSillFloorCutout:true,flushSillFloorCutoutLocal:{min:[-(W+.018)/2,-.095],max:[(W+.018)/2,.0875]}}};
  return freeze(result);
}

function worldLocal(plan,v){
  const n=plan.axis==='x'?0:2,t=n===0?2:0,out=[0,v[1],0];out[t]=v[0];out[n]=plan.normalSign*v[2];return out;
}
function rotate(v,a){const c=Math.cos(a),s=Math.sin(a);return [c*v[0]+s*v[2],v[1],-s*v[0]+c*v[2]];}
const corners=b=>[0,1].flatMap(x=>[0,1].flatMap(y=>[0,1].map(z=>[b[x?'max':'min'][0],b[y?'max':'min'][1],b[z?'max':'min'][2]])));
const bound=points=>({min:[0,1,2].map(i=>Math.min(...points.map(p=>p[i]))),max:[0,1,2].map(i=>Math.max(...points.map(p=>p[i])))});
export function hatchCollidersAt(plan,angle=0){
  require(plan?.contract===HATCH_CONTRACT&&Number.isFinite(angle)&&Math.abs(angle)<=Math.PI/2+1e-8&&angle*plan.openAngle>=-1e-8,'Invalid hatch pose.');
  return plan.colliders.map(c=>({id:c.id,owner:c.owner,motion:c.motion,...bound(corners(c).map(p=>c.motion==='kinematic'
    ?add(plan.hinge,rotate(worldLocal(plan,p),angle)):add(plan.origin,worldLocal(plan,p))))}));
}
export function hatchSwingBounds(plan){
  // Analytic extrema of each box corner over the full hinge arc; not a sample.
  const lo=Math.min(0,plan.openAngle),hi=Math.max(0,plan.openAngle),points=[];
  for(const c of plan.colliders.filter(c=>c.motion==='kinematic'))for(const point of corners(c)){
    const p=worldLocal(plan,point),angles=[lo,hi];
    for(const phase of [Math.atan2(p[2],p[0]),Math.atan2(-p[0],p[2])])for(let k=-2;k<=2;k++){
      const a=phase+k*Math.PI;if(a>lo&&a<hi)angles.push(a);
    }
    for(const a of angles)points.push(add(plan.hinge,rotate(p,a)));
  }
  return freeze(bound(points));
}

function contour(THREE,p){
  const shape=new THREE.Shape(),r=p.radius;
  shape.moveTo(-p.width/2,p.bottom);shape.lineTo(p.width/2,p.bottom);shape.lineTo(p.width/2,p.top-r);
  shape.absarc(p.width/2-r,p.top-r,r,0,Math.PI/2,false);shape.lineTo(-p.width/2+r,p.top);
  shape.absarc(-p.width/2+r,p.top-r,r,Math.PI/2,Math.PI,false);shape.closePath();return shape;
}
export function buildPressureHatch(THREE,plan){
  require(plan?.contract===HATCH_CONTRACT,'Unsupported hatch recipe.');
  const materials={structure:0x3d4b50,trim:0xa6aaa3,seat:0x7d8585,gasket:0x161d1f,leaf:0xb4b5a9,panel:0x727f7b,metal:0xb9bbb5,control:0xb77d39,grab:0x727c76};
  const mats=Object.fromEntries(Object.entries(materials).map(([key,color])=>[key,new THREE.MeshStandardMaterial({color,roughness:key==='gasket'?.9:.47,metalness:key==='gasket'?0:.52})]));
  const fixed=new THREE.Group(),pivot=new THREE.Group();fixed.name=plan.id+'_fixed';pivot.name=plan.id+'_hinge';
  fixed.position.set(...plan.origin);pivot.position.set(...plan.hinge);
  const meshes=new Map();
  for(const [parts,root] of [[plan.fixed,fixed],[plan.moving,pivot]])for(const part of parts){
    let geometry;
    if(part.shape==='ring'){
      const shape=contour(THREE,part.outer),hole=contour(THREE,part.inner);shape.holes.push(hole);
      geometry=new THREE.ExtrudeGeometry(shape,{depth:part.size[2],bevelEnabled:false,curveSegments:20});geometry.translate(0,0,-part.size[2]/2);
    }else if(part.shape==='solid'){
      const b=part.bevel,profile=part.profile;
      const shape=contour(THREE,{width:profile.width-2*b,bottom:profile.bottom+b,top:profile.top-b,radius:profile.radius-b});
      geometry=new THREE.ExtrudeGeometry(shape,{depth:part.size[2]-2*b,bevelEnabled:true,bevelSize:b,bevelThickness:b,bevelSegments:2,curveSegments:20});geometry.translate(0,0,-part.size[2]/2+b);
    }else if(part.shape==='box')geometry=new THREE.BoxGeometry(...part.size);
    else if(part.shape==='wheel')geometry=new THREE.TorusGeometry(part.radius,part.tube,10,40);
    else if(part.shape==='cylinder'){
      geometry=new THREE.CylinderGeometry(part.radius,part.radius,part.length,20);if(part.axis==='z')geometry.rotateX(Math.PI/2);
    }else if(part.shape==='rod'){
      const start=new THREE.Vector3(...part.from),end=new THREE.Vector3(...part.to),delta=end.clone().sub(start);
      geometry=new THREE.CylinderGeometry(part.radius,part.radius,delta.length(),12);
      geometry.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),delta.clone().normalize()));
      geometry.translate(...start.add(end).multiplyScalar(.5).toArray());
    }else throw new TypeError('Unknown hatch shape.');
    if(part.center)geometry.translate(...part.center);
    // Reflect the normal where necessary, then rotate local across/up/normal
    // into the portal axis. Reflection also flips triangle winding.
    const reflect=plan.axis==='x'?-plan.normalSign:plan.normalSign;
    if(reflect<0){geometry.scale(1,1,-1);const index=geometry.index;
      if(index){for(let i=0;i<index.count;i+=3){const x=index.getX(i+1);index.setX(i+1,index.getX(i+2));index.setX(i+2,x);}}
      else {for(const attr of Object.values(geometry.attributes)){for(let i=0;i<attr.count;i+=3)for(let k=0;k<attr.itemSize;k++){
        const a=(i+1)*attr.itemSize+k,b=(i+2)*attr.itemSize+k,v=attr.array[a];attr.array[a]=attr.array[b];attr.array[b]=v;}}}
    }
    if(plan.axis==='x')geometry.rotateY(-Math.PI/2);
    geometry.computeVertexNormals();geometry.computeBoundingBox();
    const mesh=new THREE.Mesh(geometry,mats[part.material]);mesh.name=part.id;
    mesh.userData={hatchPart:part.id,collisionOwner:part.id,colliderIds:plan.colliders.filter(c=>c.owner===part.id).map(c=>c.id),motion:root===pivot?'kinematic':'static',latchState:'static_retracted'};
    mesh.castShadow=true;mesh.receiveShadow=true;root.add(mesh);meshes.set(part.id,mesh);
  }
  return {fixed,pivot,meshes,setAngle(angle){require(Number.isFinite(angle)&&Math.abs(angle)<=Math.PI/2+1e-8&&angle*plan.openAngle>=-1e-8,'Invalid hatch angle.');pivot.rotation.y=angle;fixed.updateMatrixWorld(true);pivot.updateMatrixWorld(true);}};
}
