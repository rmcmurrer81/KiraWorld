// Discrete triangle/convex-frame contact. Planes come from the actual authored
// chamfered meshes; AABBs reject distant pairs, never substitute for the shape.
const EPS=1e-10;
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
function need(ok,message){if(!ok)throw Error(message);}
function point(p,id){return [p[3*id],p[3*id+1],p[3*id+2]];}
function bounds(points){return {min:[Math.min(points[0][0],points[1][0],points[2][0]),Math.min(points[0][1],points[1][1],points[2][1]),Math.min(points[0][2],points[1][2],points[2][2])],max:[Math.max(points[0][0],points[1][0],points[2][0]),Math.max(points[0][1],points[1][1],points[2][1]),Math.max(points[0][2],points[1][2],points[2][2])]};}
// Reuse only broad-phase scratch storage. Read current positions on every
// triangle and after every correction; never cache moving geometry or contacts.
function triangleBounds(p,triangles,t,out){
 const a=3*triangles[t],b=3*triangles[t+1],c=3*triangles[t+2];
 for(let axis=0;axis<3;axis++){out.min[axis]=Math.min(p[a+axis],p[b+axis],p[c+axis]);out.max[axis]=Math.max(p[a+axis],p[b+axis],p[c+axis]);}
 return out;
}
function overlaps(a,b,m){return a.min[0]<=b.max[0]+m&&a.max[0]>=b.min[0]-m&&a.min[1]<=b.max[1]+m&&a.max[1]>=b.min[1]-m&&a.min[2]<=b.max[2]+m&&a.max[2]>=b.min[2]-m;}
function interpolate(values,weights){return [0,1,2].map(a=>values.reduce((v,p,i)=>v+p[a]*weights[i],0));}

export function compileFrame(parts){
 need(Array.isArray(parts)&&parts.length>0&&parts.length<=64,'Bounded authored frame parts required');
 const result=parts.map(part=>{
  const vertices=part.mesh.vertices.map(v=>v.map((x,a)=>x+part.position[a]));
  need(vertices.length>0&&vertices.length<512&&vertices.every(v=>v.length===3&&v.every(Number.isFinite)),'Invalid frame vertices');
  const planes=[],keys=new Set();
  for(let i=0;i<vertices.length;i++){
   const normal=part.mesh.normals[i];need(normal?.length===3&&normal.every(Number.isFinite)&&Math.abs(Math.hypot(...normal)-1)<1e-8,'Frame normal is not unit length');
   const d=dot(normal,vertices[i]),key=[...normal,d].map(x=>Math.round(x*1e10)).join(':');
   if(!keys.has(key)){keys.add(key);planes.push({n:normal.slice(),d});}
  }
  need(planes.length===26&&planes.every(q=>vertices.every(v=>dot(q.n,v)<=q.d+1e-9)),'Expected exact convex chamfered frame mesh');
  const min=[0,1,2].map(a=>Math.min(...vertices.map(v=>v[a]))),max=[0,1,2].map(a=>Math.max(...vertices.map(v=>v[a])));
  return {id:part.id,planes,min,max};
 });
 result.bounds={min:[0,1,2].map(a=>Math.min(...result.map(p=>p.min[a]))),max:[0,1,2].map(a=>Math.max(...result.map(p=>p.max[a])))};return result;
}

function clippedIntersection(points,part,margin,bound=bounds(points)){
 if(!overlaps(bound,part,margin))return null;
 let poly=points.map((p,i)=>({p,w:[0,1,2].map(j=>i===j?1:0)}));
 for(const {n,d} of part.planes){
  const next=[];
  for(let i=0;i<poly.length;i++){
   const a=poly[i],b=poly[(i+1)%poly.length],da=dot(n,a.p)-d-margin,db=dot(n,b.p)-d-margin;
   if(da<=EPS)next.push(a);
   if((da>EPS)!==(db>EPS)){
    const t=Math.max(0,Math.min(1,da/(da-db)));next.push({p:a.p.map((x,k)=>x+t*(b.p[k]-x)),w:a.w.map((x,k)=>x+t*(b.w[k]-x))});
   }
  }
  poly=next;if(!poly.length)return null;
 }
 // The polygon boundary often has zero depth despite crossing the solid.
 // A convex combination of its interior establishes actual volume overlap.
 const w=[0,1,2].map(a=>poly.reduce((sum,p)=>sum+p.w[a],0)/poly.length),p=interpolate(points,w);
 const gaps=part.planes.map(q=>q.d+margin-dot(q.n,p));
 if(Math.min(...gaps)<=EPS)return null;
 return {poly,p,w,gaps};
}

function contact(cloth,ids,part,margin,points,bound){
 const intersection=clippedIntersection(points,part,margin,bound);
 if(!intersection)return null;
 const previous=interpolate(ids.map(id=>point(cloth.prev??cloth.p,id)),intersection.w);
 const entry=part.planes.map((q,i)=>dot(q.n,previous)>q.d+margin-EPS?i:-1).filter(i=>i>=0);
 const e1=points[1].map((v,a)=>v-points[0][a]),e2=points[2].map((v,a)=>v-points[0][a]);
 const tn=[e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]],length=Math.hypot(...tn);
 let facing=part.planes.map((_,i)=>i);
 if(length>1e-14){
  for(let a=0;a<3;a++)tn[a]/=length;
  const previousCenter=interpolate(ids.map(id=>point(cloth.prev??cloth.p,id)),[1/3,1/3,1/3]);
  if(dot(tn,previousCenter.map((v,a)=>v-(part.min[a]+part.max[a])/2))<0)for(let a=0;a<3;a++)tn[a]*=-1;
  facing=facing.filter(i=>dot(part.planes[i].n,tn)>1e-5);
 }
 const candidates=entry.length?entry:facing;
 let chosen=candidates[0];for(const i of candidates)if(intersection.gaps[i]<intersection.gaps[chosen])chosen=i;
 const plane=part.planes[chosen];
 // Use the deepest point of the intersection along the coherent entry normal,
 // including its centroid. This resolves face-interior and crossing triangles.
 let vertex={p:intersection.p,w:intersection.w},depth=intersection.gaps[chosen];
 for(const v of intersection.poly){const gap=plane.d+margin-dot(plane.n,v.p);if(gap>depth){depth=gap;vertex=v;}}
 return {ids,weights:vertex.w,normal:plane.n,plane_d:plane.d,margin,depth,part:part.id,hull:part};
}

function project(cloth,c,maxCorrection){
 const masses=c.ids.map(id=>cloth.grab?.index===id?0:cloth.invMass[id]);
 const denominator=masses.reduce((s,m,i)=>s+m*c.weights[i]**2,0);if(denominator<EPS)return false;
 const delta=masses.map((m,i)=>m*c.weights[i]*c.depth/denominator),scale=Math.min(1,maxCorrection/Math.max(...delta));
 for(let i=0;i<c.ids.length;i++){for(let a=0;a<3;a++){
  const k=3*c.ids[i]+a,d=delta[i]*scale*c.normal[a];cloth.p[k]+=d;if(cloth.prev&&cloth.splitPositionStabilization!==false)cloth.prev[k]+=d;
 }cloth.finiteTopDomain?.observeVertex(c.ids[i]);}
 return true;
}

export function solveFrameContacts(cloth,frame,{passes=2,maxCorrection=.025,reset=true}={}){
 need(Number.isInteger(passes)&&passes>0&&passes<=16&&maxCorrection>0&&maxCorrection<=.05,'Bounded frame contact settings required');
 if(reset)cloth.frameActiveContacts=[];let corrected=0,maxDepth=0;const bound={min:[0,0,0],max:[0,0,0]};
 for(let pass=0;pass<passes;pass++)for(let t=0;t<cloth.triangles.length;t+=3){
  triangleBounds(cloth.p,cloth.triangles,t,bound);let ids=null,points=null;
  if(frame.bounds&&!overlaps(bound,frame.bounds,cloth.margin))continue;
  for(const part of frame){
   if(!overlaps(bound,part,cloth.margin))continue;
   if(!ids){ids=cloth.triangles.slice(t,t+3);points=ids.map(id=>point(cloth.p,id));}
   const c=contact(cloth,ids,part,cloth.margin,points,bound);
   if(c&&project(cloth,c,maxCorrection)){corrected++;maxDepth=Math.max(maxDepth,c.depth);cloth.frameActiveContacts.push(c);points=ids.map(id=>point(cloth.p,id));triangleBounds(cloth.p,cloth.triangles,t,bound);}
  }
 }
 return {corrected_constraints:corrected,max_correction_depth_m:maxDepth};
}

export function finishFrameContactVelocities(cloth,dt){
 const current=new Map();for(const c of cloth.frameActiveContacts??[])current.set(c.part+":"+c.ids.join(","),c);
 for(const c of current.values()){
  const position=interpolate(c.ids.map(id=>point(cloth.p,id)),c.weights);
  if(dot(c.normal,position)-c.plane_d-c.margin>.002)continue;
  if(c.hull.planes.some(q=>dot(q.n,position)>q.d+c.margin+.002))continue;
  const masses=c.ids.map(id=>cloth.grab?.index===id?0:cloth.invMass[id]);
  const denominator=masses.reduce((s,m,i)=>s+m*c.weights[i]**2,0);if(denominator<EPS)continue;
  const velocity=interpolate(c.ids.map(id=>point(cloth.v,id)),c.weights),vn=dot(velocity,c.normal),impulse=Math.max(0,-vn);
  const tangent=velocity.map((v,a)=>v-vn*c.normal[a]),speed=Math.hypot(...tangent);
  const friction=speed?Math.min(1,.35*Math.max(impulse,9.81*dt)/speed):0;
  for(let i=0;i<c.ids.length;i++)for(let a=0;a<3;a++)cloth.v[3*c.ids[i]+a]+=masses[i]*c.weights[i]/denominator*(impulse*c.normal[a]-friction*tangent[a]);
 }
}

export function frameContactReport(cloth,frame,{margin=0}={}){
 let intersections=0,maximum=0,worst=null;const bound={min:[0,0,0],max:[0,0,0]};
 for(let t=0;t<cloth.triangles.length;t+=3){triangleBounds(cloth.p,cloth.triangles,t,bound);let points=null;if(frame.bounds&&!overlaps(bound,frame.bounds,margin))continue;
  for(const part of frame){if(!overlaps(bound,part,margin))continue;if(!points)points=cloth.triangles.slice(t,t+3).map(id=>point(cloth.p,id));const value=clippedIntersection(points,part,margin,bound);if(value){intersections++;const depth=Math.min(...value.gaps);if(depth>maximum){maximum=depth;worst={part:part.id,triangle:t/3};}}}
 }
 return {intersecting_triangle_part_pairs:intersections,max_centroid_penetration_m:maximum,worst};
}
