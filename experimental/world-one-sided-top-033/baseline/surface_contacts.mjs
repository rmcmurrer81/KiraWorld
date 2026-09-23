// Discrete upper-surface contacts for the *simulation* cloth mesh.
// Candidate extrema come from the exact projected triangle overlay: cloth edge
// crossings of grid/diagonal lines, and mattress vertices inside cloth triangles.
// Nothing here clips, offsets, hides, or replaces the rendered cloth geometry.
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const caches=new WeakMap();
function topology(cloth){
 let value=caches.get(cloth);if(value)return value;
 const seen=new Set(),edges=[];
 for(let t=0;t<cloth.triangles.length;t+=3)for(let k=0;k<3;k++){
  let a=cloth.triangles[t+k],b=cloth.triangles[t+(k+1)%3];if(a>b)[a,b]=[b,a];
  const key=a+':'+b;if(!seen.has(key)){seen.add(key);edges.push([a,b]);}
 }
 value={edges};caches.set(cloth,value);return value;
}
export function surfaceHeight(surface,x,z){
 const u=clamp((x/surface.width+.5)*surface.nx,0,surface.nx),v=clamp((z/surface.length+.5)*surface.nz,0,surface.nz);
 const ix=Math.min(surface.nx-1,Math.floor(u)),iz=Math.min(surface.nz-1,Math.floor(v)),fx=u-ix,fz=v-iz;
 const a=iz*(surface.nx+1)+ix,b=a+1,c=a+surface.nx+1,d=c+1,p=surface.p;
 return fx+fz<=1?(1-fx-fz)*p[3*a+1]+fx*p[3*b+1]+fz*p[3*c+1]:(1-fz)*p[3*b+1]+(1-fx)*p[3*c+1]+(fx+fz-1)*p[3*d+1];
}
function clipInterval(ax,az,dx,dz,hx,hz){
 let lo=0,hi=1;
 for(const [p,d,h] of [[ax,dx,hx],[az,dz,hz]]){
  if(Math.abs(d)<1e-14){if(p < -h||p>h)return null;continue;}
  let t0=(-h-p)/d,t1=(h-p)/d;if(t0>t1)[t0,t1]=[t1,t0];lo=Math.max(lo,t0);hi=Math.min(hi,t1);if(lo>hi)return null;
 }
 return [lo,hi];
}
function edgeContact(cloth,surface,a,b,margin){
 const p=cloth.p,ax=p[3*a],ay=p[3*a+1],az=p[3*a+2],dx=p[3*b]-ax,dy=p[3*b+1]-ay,dz=p[3*b+2]-az;
 const range=clipInterval(ax,az,dx,dz,surface.width/2+margin,surface.length/2+margin);if(!range)return null;
 let worst=null;
 const inspect=t=>{
  if(t<range[0]-1e-10||t>range[1]+1e-10)return;
  t=clamp(t,0,1);const x=ax+dx*t,y=ay+dy*t,z=az+dz*t;
  const depth=surfaceHeight(surface,x,z)+margin-y;
  if(depth>1e-9&&(!worst||depth>worst.depth))worst={ids:[a,b],weights:[1-t,t],depth,point:[x,y,z],kind:'edge'};
 };
 inspect(range[0]);inspect(range[1]);
 const crossing=(offset,rate,start,end)=>{
  if(Math.abs(rate)<1e-14)return;
  const r0=offset+rate*range[0],r1=offset+rate*range[1];
  const first=Math.max(start,Math.ceil(Math.min(r0,r1)-1e-10)),last=Math.min(end,Math.floor(Math.max(r0,r1)+1e-10));
  for(let line=first;line<=last;line++)inspect((line-offset)/rate);
 };
 const u=(ax/surface.width+.5)*surface.nx,v=(az/surface.length+.5)*surface.nz,du=dx/surface.width*surface.nx,dv=dz/surface.length*surface.nz;
 crossing(u,du,0,surface.nx);crossing(v,dv,0,surface.nz);
 // Every actual cell diagonal lies on an integer u+v line. Additional crossings
 // at cell corners are harmless; taking them avoids finite point sampling gaps.
 crossing(u+v,du+dv,0,surface.nx+surface.nz);
 return worst;
}
function interiorContact(cloth,surface,ids,margin){
 const p=cloth.p,[a,b,c]=ids,ax=p[3*a],az=p[3*a+2],bx=p[3*b],bz=p[3*b+2],cx=p[3*c],cz=p[3*c+2];
 const det=(bz-cz)*(ax-cx)+(cx-bx)*(az-cz);if(Math.abs(det)<1e-14)return null;
 const xmin=Math.max(-surface.width/2,Math.min(ax,bx,cx)),xmax=Math.min(surface.width/2,Math.max(ax,bx,cx));
 const zmin=Math.max(-surface.length/2,Math.min(az,bz,cz)),zmax=Math.min(surface.length/2,Math.max(az,bz,cz));
 if(xmin>xmax||zmin>zmax)return null;
 const ix0=Math.max(0,Math.ceil((xmin/surface.width+.5)*surface.nx-1e-10)),ix1=Math.min(surface.nx,Math.floor((xmax/surface.width+.5)*surface.nx+1e-10));
 const iz0=Math.max(0,Math.ceil((zmin/surface.length+.5)*surface.nz-1e-10)),iz1=Math.min(surface.nz,Math.floor((zmax/surface.length+.5)*surface.nz+1e-10));
 let worst=null;
 for(let iz=iz0;iz<=iz1;iz++)for(let ix=ix0;ix<=ix1;ix++){
  const si=iz*(surface.nx+1)+ix,x=surface.p[3*si],z=surface.p[3*si+2];
  let wa=((bz-cz)*(x-cx)+(cx-bx)*(z-cz))/det,wb=((cz-az)*(x-cx)+(ax-cx)*(z-cz))/det,wc=1-wa-wb;
  if(Math.min(wa,wb,wc)<-1e-9)continue;
  wa=Math.max(0,wa);wb=Math.max(0,wb);wc=Math.max(0,wc);const sum=wa+wb+wc;wa/=sum;wb/=sum;wc/=sum;
  const y=wa*p[3*a+1]+wb*p[3*b+1]+wc*p[3*c+1];
  const depth=surface.p[3*si+1]+margin-y;
  if(depth>1e-9&&(!worst||depth>worst.depth))worst={ids,weights:[wa,wb,wc],depth,point:[x,y,z],kind:'triangle_interior'};
 }
 return worst;
}
function project(cloth,contact){
 let denominator=0;const w=contact.ids.map((id,i)=>{const value=cloth.grab?.index===id?0:cloth.invMass[id];denominator+=value*contact.weights[i]**2;return value;});
 if(denominator<1e-14)return false;
 // A hard geometric inequality distributed to the actual triangle vertices.
 // Cap one correction to prevent a near-fixed barycentric corner from jumping.
 const changes=w.map((mass,i)=>mass*contact.weights[i]*contact.depth/denominator);
 const scale=Math.min(1,.025/Math.max(...changes));
 for(let i=0;i<contact.ids.length;i++){
  const index=3*contact.ids[i]+1,delta=changes[i]*scale;cloth.p[index]+=delta;
  // Split position stabilization: removing overlap must not launch the blanket.
  // Velocity contact is solved separately below against the same virtual point.
  if(cloth.prev&&cloth.splitPositionStabilization!==false)cloth.prev[index]+=delta;
 }
 return true;
}
export function solveSurfaceContacts(cloth,surface,{passes=2,reset=true}={}){
 if(!Number.isInteger(passes)||passes<1||passes>12)throw Error('Contact passes must be 1..12');
 let count=0,maxDepth=0;if(reset)cloth.surfaceActiveContacts=[];
 for(let pass=0;pass<passes;pass++){
  for(const [a,b] of topology(cloth).edges){const c=edgeContact(cloth,surface,a,b,cloth.margin);if(c){maxDepth=Math.max(maxDepth,c.depth);if(project(cloth,c)){count++;cloth.surfaceActiveContacts.push(c);}}}
  for(let t=0;t<cloth.triangles.length;t+=3){const c=interiorContact(cloth,surface,cloth.triangles.slice(t,t+3),cloth.margin);if(c){maxDepth=Math.max(maxDepth,c.depth);if(project(cloth,c)){count++;cloth.surfaceActiveContacts.push(c);}}}
 }
 return {count,max_correction_depth_m:maxDepth};
}
export function finishSurfaceContactVelocities(cloth,surface,dt){
 const current=new Map();for(const c of cloth.surfaceActiveContacts??[])current.set(c.ids.join(','),c);
 for(const c of current.values()){
  const point=[0,1,2].map(a=>c.ids.reduce((sum,id,i)=>sum+c.weights[i]*cloth.p[3*id+a],0));
  if(Math.abs(point[0])>surface.width/2+cloth.margin||Math.abs(point[2])>surface.length/2+cloth.margin)continue;
  const sampled=surface.sampleTop(clamp(point[0],-surface.width/2,surface.width/2),clamp(point[2],-surface.length/2,surface.length/2));
  if(point[1]>sampled.height+cloth.margin+.002)continue;
  let vy=0,vx=0,vz=0,denominator=0;
  const masses=c.ids.map((id,i)=>{const w=cloth.grab?.index===id?0:cloth.invMass[id];denominator+=w*c.weights[i]**2;vy+=c.weights[i]*cloth.v[3*id+1];vx+=c.weights[i]*cloth.v[3*id];vz+=c.weights[i]*cloth.v[3*id+2];return w;});
  if(denominator<1e-14)continue;
  const impulse=Math.max(0,sampled.velocity-vy),speed=Math.hypot(vx,vz),friction=speed?Math.min(1,.5*Math.max(impulse,9.81*dt)/speed):0;
  for(let i=0;i<c.ids.length;i++){const factor=masses[i]*c.weights[i]/denominator,k=3*c.ids[i];cloth.v[k+1]+=factor*impulse;cloth.v[k]-=factor*vx*friction;cloth.v[k+2]-=factor*vz*friction;}
 }
}
export function surfaceContactReport(cloth,surface){
 let max=0,edge=0,interior=0,worst=null,count=0;
 const take=c=>{if(!c)return;count++;if(c.depth>max){max=c.depth;worst=c;}if(c.kind==='edge')edge=Math.max(edge,c.depth);else interior=Math.max(interior,c.depth);};
 for(const [a,b] of topology(cloth).edges)take(edgeContact(cloth,surface,a,b,0));
 for(let t=0;t<cloth.triangles.length;t+=3)take(interiorContact(cloth,surface,cloth.triangles.slice(t,t+3),0));
 return {max_penetration_m:max,edge_penetration_m:edge,triangle_interior_penetration_m:interior,contact_count:count,worst};
}
