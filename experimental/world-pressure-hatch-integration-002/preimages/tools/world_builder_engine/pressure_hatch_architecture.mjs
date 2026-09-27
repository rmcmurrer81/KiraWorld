// Pure source-preserving cutouts shared by browser and export integration.
// Walking supports and conservative source colliders remain unchanged.
export const HATCH_ARCHITECTURE_CONTRACT='pressure_hatch_architectural_cutouts_v1';
const EPS=1e-9;
const require=(ok,message)=>{if(!ok)throw new TypeError(message);};
const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const cross=(a,b,p)=>(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]);
export const polygonArea=p=>Math.abs(p.reduce((sum,a,i)=>{const b=p[(i+1)%p.length];return sum+a[0]*b[1]-a[1]*b[0];},0)/2);
function clean(poly){const out=poly.filter((p,i)=>i===0||Math.hypot(p[0]-poly[i-1][0],p[1]-poly[i-1][1])>EPS);
 if(out.length>1&&Math.hypot(out[0][0]-out.at(-1)[0],out[0][1]-out.at(-1)[1])<EPS)out.pop();
 return out.length>=3&&polygonArea(out)>EPS?out:[];}
function clip(poly,a,b,inside){
 const out=[];if(!poly.length)return out;
 for(let i=0;i<poly.length;i++){
  const p=poly[i],q=poly[(i+1)%poly.length],dp=cross(a,b,p),dq=cross(a,b,q);
  const keepP=inside?dp>=-EPS:dp<=EPS,keepQ=inside?dq>=-EPS:dq<=EPS;
  if(keepP)out.push([...p]);
  if(keepP!==keepQ){const factor=dp/(dp-dq);out.push([p[0]+factor*(q[0]-p[0]),p[1]+factor*(q[1]-p[1])]);}
 }
 return clean(out);
}
// Subtract one convex cut without holes: emit the remainder outside each edge,
// then clip what remains to its inside. Pieces have disjoint positive areas.
export function subtractConvex(subject,cut){
 let remaining=clean(subject),pieces=[];
 for(let i=0;i<cut.length&&remaining.length;i++){
  const a=cut[i],b=cut[(i+1)%cut.length],outside=clip(remaining,a,b,false);
  if(outside.length)pieces.push(outside);remaining=clip(remaining,a,b,true);
 }
 return pieces;
}
function rectangle(x0,x1,y0,y1){return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]];}
export function hatchOuterProfilePoints(profile){
 const {width,bottom,top,radius:r}=profile;
 require([width,bottom,top,r].every(Number.isFinite)&&width>2*r&&top-bottom>r&&r>0,'Unsupported frame profile');
 const points=[[-width/2,bottom],[width/2,bottom],[width/2,top-r]];
 // ExtrudeGeometry(curveSegments:20) samples an EllipseCurve at 40 intervals.
 // These points reproduce the corrected recipe's two quarter arcs exactly.
 for(let i=1;i<=40;i++){const a=Math.PI/2*i/40;points.push([width/2-r+r*Math.cos(a),top-r+r*Math.sin(a)]);}
 points.push([-width/2+r,top]);
 for(let i=1;i<=40;i++){const a=Math.PI/2+Math.PI/2*i/40;points.push([-width/2+r+r*Math.cos(a),top-r+r*Math.sin(a)]);}
 return points;
}
export function planHatchArchitecture(geometry,hatchPlans){
 require(Array.isArray(geometry?.primitives)&&geometry.primitives.length<=4096&&Array.isArray(hatchPlans)&&hatchPlans.length<=24,'Invalid architectural input');
 const ids=new Set();for(const plan of hatchPlans){require(plan?.contract==='authored_pressure_hatch_geometry_v1'&&!ids.has(plan.portalId),'Invalid hatch plan');ids.add(plan.portalId);}
 const modifications={},primitiveIds=new Set();
 for(const primitive of geometry.primitives){
  require(typeof primitive.id==='string'&&!primitiveIds.has(primitive.id),'Ambiguous primitive identity');primitiveIds.add(primitive.id);
  if(!['wall','floor'].includes(primitive.role))continue;
  const position=primitive.position,size=primitive.size;
  require(primitive.primitive==='box'&&position?.length===3&&size?.length===3&&position.every(Number.isFinite)&&size.every(x=>Number.isFinite(x)&&x>0),'Unsupported structural primitive');
  const cuts=[];let normal=null,axes=null;
  for(const plan of hatchPlans){
   const n=plan.axis==='x'?0:2,t=n===0?2:0;
   if(primitive.role==='wall'){
    if(Math.abs(position[n]-plan.origin[n])>EPS||size[n]>.3)continue;
    const profile=plan.fixed.find(p=>p.id.endsWith('_structural_surround'))?.outer;require(profile,'Missing outer frame');
    const points=hatchOuterProfilePoints(profile).map(([u,v])=>[plan.origin[t]+u,plan.origin[1]+v]);
    if(points.every(p=>p[0]<position[t]-size[t]/2-EPS)||points.every(p=>p[0]>position[t]+size[t]/2+EPS)||points.every(p=>p[1]<position[1]-size[1]/2-EPS)||points.every(p=>p[1]>position[1]+size[1]/2+EPS))continue;
    require(normal===null||normal===n,'Ambiguous wall orientation');normal=n;axes=[t,1];cuts.push({portalId:plan.portalId,polygon:points});
   }else{
    if(Math.abs(position[1]+size[1]/2-plan.origin[1])>EPS)continue;
    const cut=plan.limits.flushSillFloorCutoutLocal;require(plan.limits.requiresFlushSillFloorCutout&&cut,'Missing flush sill cutout');
    const points=[];
    for(const u of [cut.min[0],cut.max[0]])for(const v of [cut.min[1],cut.max[1]]){const p=[...plan.origin];p[t]+=u;p[n]+=plan.normalSign*v;points.push([p[0],p[2]]);}
    const x0=Math.min(...points.map(p=>p[0])),x1=Math.max(...points.map(p=>p[0])),z0=Math.min(...points.map(p=>p[1])),z1=Math.max(...points.map(p=>p[1]));
    if(x1<=position[0]-size[0]/2+EPS||x0>=position[0]+size[0]/2-EPS||z1<=position[2]-size[2]/2+EPS||z0>=position[2]+size[2]/2-EPS)continue;
    normal=1;axes=[0,2];cuts.push({portalId:plan.portalId,polygon:rectangle(x0,x1,z0,z1)});
   }
  }
  if(!cuts.length)continue;
  const original=rectangle(position[axes[0]]-size[axes[0]]/2,position[axes[0]]+size[axes[0]]/2,position[axes[1]]-size[axes[1]]/2,position[axes[1]]+size[axes[1]]/2);
  let polygons=[original];for(const cut of cuts){polygons=polygons.flatMap(poly=>subtractConvex(poly,cut.polygon));require(polygons.length<=512,'Cutout exceeds bounded complexity');}
  const removedArea=polygonArea(original)-polygons.reduce((sum,poly)=>sum+polygonArea(poly),0);
  if(removedArea<=EPS)continue;
  modifications[primitive.id]={sourcePrimitiveId:primitive.id,role:primitive.role,normalAxis:normal,planeAxes:axes,
   normalMin:position[normal]-size[normal]/2,normalMax:position[normal]+size[normal]/2,
   polygons,removedArea,sourceArea:polygonArea(original),cutPortalIds:cuts.map(c=>c.portalId),
   sourceCollisionPolicy:'unchanged_conservative_source_bounds',supportSurfaceChanged:false};
 }
 return freeze({contract:HATCH_ARCHITECTURE_CONTRACT,modifications,sourceGeometryChanged:false});
}

export function buildHatchStructuralMesh(THREE,primitive,material,architecture,{panelNormal=null,panelOffset=0}={}){
 require(architecture?.contract===HATCH_ARCHITECTURE_CONTRACT,'Invalid architecture plan');
 const mod=architecture.modifications[primitive.id];if(!mod)return null;
 require(panelNormal===null||panelNormal===1||panelNormal===-1,'Invalid panel normal');
 require(Number.isFinite(panelOffset)&&Math.abs(panelOffset)<=.01,'Invalid panel offset');
 const group=new THREE.Group();group.name=primitive.id+(panelNormal===null?'':'_panel_'+(panelNormal>0?'positive':'negative'));group.userData={hatch_cutouts:mod.cutPortalIds,source_primitive_id:primitive.id,support_surface_changed:false};
 const n=mod.normalAxis,[u,v]=mod.planeAxes,parts=[];
 for(const poly of mod.polygons){
  const shape=new THREE.Shape();shape.moveTo(...poly[0]);for(const p of poly.slice(1))shape.lineTo(...p);shape.closePath();
  let geometry=panelNormal===null?new THREE.ExtrudeGeometry(shape,{depth:mod.normalMax-mod.normalMin,bevelEnabled:false}):new THREE.ShapeGeometry(shape);
  if(geometry.index)geometry=geometry.toNonIndexed();
  const position=geometry.attributes.position,sourceNormal=geometry.attributes.normal;
  for(let i=0;i<position.count;i++){
    const p=[0,0,0],normal=[0,0,0];p[u]=position.getX(i);p[v]=position.getY(i);
    p[n]=panelNormal===null?mod.normalMin+position.getZ(i):(panelNormal>0?mod.normalMax:mod.normalMin)+panelNormal*panelOffset;
    normal[u]=sourceNormal.getX(i);normal[v]=sourceNormal.getY(i);normal[n]=sourceNormal.getZ(i)*(panelNormal??1);
    position.setXYZ(i,...p);sourceNormal.setXYZ(i,...normal);
  }
  // Odd axis permutations and negative-facing panels reverse winding.
  const parity=n===2?1:-1;if(parity*(panelNormal??1)<0)for(const attr of Object.values(geometry.attributes))for(let i=0;i<attr.count;i+=3)for(let k=0;k<attr.itemSize;k++){
    const a=(i+1)*attr.itemSize+k,b=(i+2)*attr.itemSize+k,value=attr.array[a];attr.array[a]=attr.array[b];attr.array[b]=value;
  }
  parts.push(geometry);
 }
  if(parts.length){
  const merged=new THREE.BufferGeometry();
  for(const key of Object.keys(parts[0].attributes)){
    const size=parts[0].attributes[key].itemSize,arrays=parts.map(p=>p.attributes[key].array),data=new Float32Array(arrays.reduce((n,a)=>n+a.length,0));
    let offset=0;for(const a of arrays){data.set(a,offset);offset+=a.length;}merged.setAttribute(key,new THREE.BufferAttribute(data,size));
  }
  const count=merged.attributes.position.count;require(count<=500000,'Structural mesh exceeds bounded complexity');
  // Keep explicit indices for the existing strict exporter/importer contract.
  merged.setIndex(Array.from({length:count},(_,i)=>i));merged.computeBoundingBox();
  const mesh=new THREE.Mesh(merged,material);mesh.name=group.name+'_hatch_cut_mesh';mesh.receiveShadow=true;mesh.castShadow=true;group.add(mesh);
 }
 parts.forEach(p=>p.dispose());return group;
}
