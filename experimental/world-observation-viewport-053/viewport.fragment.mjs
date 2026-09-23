// Derived architectural detail only. The original wall safety collider remains solid.
// No pressure rating, exterior traversal, measured Martian terrain or real sky model.
export function planObservationViewport(geometry,plan){
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
export function viewportWallPieces(primitive,viewport){
  if(!viewport||primitive.id!==viewport.wall_id)return [primitive];
  const {along,center,width,bottom,top}=viewport,lo=primitive.position[along]-primitive.size[along]/2,hi=primitive.position[along]+primitive.size[along]/2;
  const floor=primitive.position[1]-primitive.size[1]/2,ceiling=primitive.position[1]+primitive.size[1]/2;
  return [[lo,center-width/2,floor,ceiling],[center+width/2,hi,floor,ceiling],[center-width/2,center+width/2,floor,bottom],[center-width/2,center+width/2,top,ceiling]].map(([a,b,y,z],i)=>{
    const position=[...primitive.position],size=[...primitive.size];position[along]=(a+b)/2;size[along]=b-a;position[1]=(y+z)/2;size[1]=z-y;
    return {...primitive,id:primitive.id+'_surround_'+i,position,size};
  });
}
export function createStructuralPrimitive(THREE,primitive,material,viewport,materials){
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
  ring('reveal',.036,thickness,0,width,height,materials.basic.metal);
  ring('inner_frame',.07,.026,-sign*(thickness/2-.013),width,height,materials.basic.ivory);
  ring('glazing_gasket',.016,.018,sign*(thickness/2-.028),width-.072,height-.072,materials.basic.rubber);
  const size=[.01,.01,.01],position=[...primitive.position];size[axis]=.008;size[along]=width-.10;size[1]=height-.10;position[axis]=coordinate+sign*(thickness/2-.028);position[along]=center;position[1]=(bottom+top)/2;
  const glass=new THREE.MeshStandardMaterial({color:0xc0d4d2,roughness:.16,metalness:0,transparent:true,opacity:.12,depthWrite:false,side:THREE.DoubleSide});
  box(viewport.wall_id+'_glazing',size,position,glass).userData={viewport_glazing:true,nontraversable:true};
  return group;
}
export function addObservationExterior(THREE,scene,viewport){
  if(!viewport)return null;
  const {axis,along,sign,coordinate,center}=viewport;
  const positions=[],colors=[],indices=[],nx=32,nz=40;
  for(let i=0;i<=nx;i++)for(let j=0;j<=nz;j++){
    const d=.18+i*2,a=(j/nz-.5)*92,p=[0,0,0];p[axis]=coordinate+sign*d;p[along]=center+a;
    const ridge=Math.exp(-(((d-42)/9)**2))*(2.8+1.1*Math.sin(a*.105)+.45*Math.sin(a*.41));
    p[1]=-.16+Math.min(1,d/12)*(.09*Math.sin(d*.28+a*.2)+.07*Math.cos(a*.38))+ridge;
    positions.push(...p);const tone=.88+.07*Math.sin(d*.24+a*.15);colors.push(.38*tone,.235*tone,.16*tone);
    if(i<nx&&j<nz){const k=i*(nz+1)+j;indices.push(k,k+nz+1,k+1,k+1,k+nz+1,k+nz+2);}
  }
  if((axis===0?sign:-sign)>0)for(let i=0;i<indices.length;i+=3)[indices[i+1],indices[i+2]]=[indices[i+2],indices[i+1]];
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.setIndex(indices);g.computeVertexNormals();
  const mesh=new THREE.Mesh(g,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0,side:THREE.DoubleSide}));mesh.name='original_procedural_exterior_'+viewport.room_id;
  mesh.userData={kind:'procedural_exterior_scenery',room_id:viewport.room_id,nontraversable:true,measured_terrain:false};mesh.receiveShadow=true;scene.add(mesh);return mesh;
}
