// Disposable inspection context only. This does not modify a saved world.
export function buildInspectionContext(THREE,plan,wallMaterial,floorMaterial){
  const group=new THREE.Group();group.name='isolated_inspection_context';
  const frame=plan.fixed.find(p=>p.id.endsWith('_structural_surround'))?.outer;
  const cut=plan.limits.flushSillFloorCutoutLocal;
  if(!frame||!plan.limits.requiresFlushSillFloorCutout||!cut)throw new Error('Missing reviewed context cutouts.');
  const wallHalf=2.7,wallHeight=2.8;
  if(frame.width/2>=wallHalf||frame.top>=wallHeight)throw new Error('Inspection frame exceeds this context.');
  const point=local=>{const n=plan.axis==='x'?0:2,t=n===0?2:0,p=[...plan.origin];p[t]+=local[0];p[1]+=local[1];p[n]+=plan.normalSign*local[2];return p;};
  function mesh(name,geometry,material,position=[0,0,0]){
    const object=new THREE.Mesh(geometry,material);object.name=name;
    // Both context shapes are symmetric across the portal normal and tangent.
    if(plan.axis==='x')object.rotation.y=Math.PI/2;
    object.position.set(...point(position));object.castShadow=true;object.receiveShadow=true;group.add(object);return object;
  }
  // The notch follows the exact outer frame curve, not the smaller passage.
  // This eliminates duplicate reveal surfaces inside the seat insert.
  const shape=new THREE.Shape(),half=frame.width/2,r=frame.radius,shoulder=frame.top-r;
  shape.moveTo(-wallHalf,0);shape.lineTo(-half,0);shape.lineTo(-half,shoulder);
  shape.absarc(-half+r,shoulder,r,Math.PI,Math.PI/2,true);
  shape.lineTo(half-r,frame.top);shape.absarc(half-r,shoulder,r,Math.PI/2,0,true);
  shape.lineTo(half,0);shape.lineTo(wallHalf,0);shape.lineTo(wallHalf,wallHeight);shape.lineTo(-wallHalf,wallHeight);shape.closePath();
  const wallGeometry=new THREE.ExtrudeGeometry(shape,{depth:.15,bevelEnabled:false,curveSegments:20});wallGeometry.translate(0,0,-.075);
  mesh('context_wall_with_frame_rebate',wallGeometry,wallMaterial);
  // The sill owns this small decorative-floor footprint at y=0. The walking
  // support remains continuous; this is mesh ownership, not a physical hole.
  const [left,back]=cut.min,[right,front]=cut.max;
  for(const [name,x0,x1,z0,z1] of [
    ['left',-4,left,-5,5],['right',right,4,-5,5],['back',left,right,-5,back],['front',left,right,front,5],
  ])mesh('context_floor_'+name,new THREE.BoxGeometry(x1-x0,.12,z1-z0),floorMaterial,[(x0+x1)/2,-.06,(z0+z1)/2]);
  group.updateMatrixWorld(true);return group;
}
