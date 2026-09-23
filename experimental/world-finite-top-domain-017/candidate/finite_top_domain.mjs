// Isolated fixed-box exterior-path certificate, not a contact response or CCD.
// Every query concerns the actual particle, edge or full triangle. A shared
// strict separating plane proves its entire linear mutation stays outside.
const EPS=1e-8, SIDE=1|2|4|8, BOTTOM=16, ABOVE=32;
const key=ids=>ids.length+':'+ids.slice().sort((a,b)=>a-b).join(',');
export class FiniteTopDomain {
 constructor(cloth,surface){
  this.c=cloth;this.s=surface;this.p=cloth.p;this.mp=surface.p;
  this.shape=[surface.base,surface.width,surface.length,surface.maximumHeight,surface.nx,surface.nz,cloth.margin];
  this.reason=null;this.last=Float64Array.from(cloth.p);this.masks=new Uint8Array(cloth.count);
  this.primitives=[];this.byKey=new Map();this.adj=Array.from({length:cloth.count},()=>[]);
  this.counts={observations:0,queries:0,suppressed:0,lost:0,lateral_reanchors:0};
  if(this.shape.some(v=>!Number.isFinite(v))||surface.base>=surface.maximumHeight||surface.width<=0||surface.length<=0||!Number.isInteger(surface.nx)||surface.nx<1||!Number.isInteger(surface.nz)||surface.nz<1||surface.count!==(surface.nx+1)*(surface.nz+1)||surface.p.length!==surface.count*3||surface.prev?.length!==surface.count||!Number.isInteger(cloth.count)||cloth.count<1||cloth.margin<0||cloth.margin>.02||cloth.p.length!==cloth.count*3||cloth.prev.length!==cloth.p.length)this.hold('INVALID_SHAPE');
  const prior=[];
  for(let i=0;i<cloth.count;i++){this.masks[i]=this.mask(cloth.p,3*i);prior[i]=this.mask(cloth.prev,3*i);}
  const add=ids=>{
   const k=key(ids);if(this.byKey.has(k))return;
   if(ids.some(i=>!Number.isInteger(i)||i<0||i>=cloth.count)){this.hold('INVALID_TOPOLOGY');return;}
   const mask=ids.reduce((v,i)=>v&this.masks[i],63),before=ids.reduce((v,i)=>v&prior[i],63);
   const q={ids:ids.slice(),mask,certified:!!(mask&before)};this.byKey.set(k,q);this.primitives.push(q);
   for(const i of ids)this.adj[i].push(q);
  };
  for(let i=0;i<cloth.count;i++)add([i]);
  if(cloth.triangles.length%3)this.hold('INVALID_TOPOLOGY');
  for(let t=0;t<cloth.triangles.length;t+=3){const ids=cloth.triangles.slice(t,t+3);add(ids);for(let j=0;j<3;j++)add([ids[j],ids[(j+1)%3]]);}
  for(let i=0;i<surface.count;i++)this.observeTop(i);
  for(const y of surface.prev??[])if(!Number.isFinite(y)||y<surface.base-EPS||y>surface.maximumHeight+EPS)this.hold('TOP_PREVIOUS_OUTSIDE_FIXED_BOX');
 }
 hold(reason){this.reason??=reason;}
 mask(p,k){
  const x=p[k],y=p[k+1],z=p[k+2],s=this.s,m=this.shape[6]+EPS;
  if(![x,y,z].every(Number.isFinite)){this.hold('NONFINITE_CLOTH');return 0;}
  return (x< -s.width/2-m?1:0)|(x>s.width/2+m?2:0)|(z< -s.length/2-m?4:0)|(z>s.length/2+m?8:0)|(y<s.base-m?BOTTOM:0)|(y>s.maximumHeight+m?ABOVE:0);
 }
 observeVertex(i){
  this.counts.observations++;
  if(!Number.isInteger(i)||i<0||i>=this.c.count){this.hold('INVALID_VERTEX');return;}
  const k=3*i;this.masks[i]=this.mask(this.p,k);
  for(const q of this.adj[i]){
   const mask=q.ids.reduce((v,j)=>v&this.masks[j],63);
   // Never rearm merely because a top-origin primitive emerges below the slab.
   // A wholly lateral exterior pose is a safe new anchor for subsequent motion.
   const retained=q.certified&&!!(q.mask&mask);
   if(q.certified&&!retained)this.counts.lost++;
   if(!retained&&(mask&SIDE))this.counts.lateral_reanchors++;
   q.certified=retained||!!(mask&SIDE);q.mask=mask;
  }
  this.last[k]=this.p[k];this.last[k+1]=this.p[k+1];this.last[k+2]=this.p[k+2];
 }
 observeTop(i){
  const s=this.s,k=3*i,x=(i%(s.nx+1)/s.nx-.5)*s.width,z=(Math.floor(i/(s.nx+1))/s.nz-.5)*s.length;
  if(!Number.isFinite(s.p[k])||!Number.isFinite(s.p[k+1])||!Number.isFinite(s.p[k+2])||s.p[k+1]<s.base-EPS||s.p[k+1]>s.maximumHeight+EPS||Math.abs(s.p[k]-x)>EPS||Math.abs(s.p[k+2]-z)>EPS)this.hold('TOP_OUTSIDE_FIXED_BOX_OR_XZ_CHANGED');
 }
 bindings(){
  const s=this.s,c=this.c;
  if(c.p!==this.p||s.p!==this.mp||[s.base,s.width,s.length,s.maximumHeight,s.nx,s.nz,c.margin].some((v,i)=>v!==this.shape[i]))this.hold('BINDING_CHANGED');
 }
 verifyOwnedPositions(){this.bindings();for(let i=0;i<this.last.length;i++)if(!Object.is(this.last[i],this.p[i])){this.hold('UNOBSERVED_POSITION_WRITE');break;}}
 clear(ids,margin,kind='unknown'){
  this.counts.queries++;this.bindings();
  const q=this.byKey.get(key(ids));
  for(const i of ids)for(let a=0;a<3;a++)if(!Object.is(this.last[3*i+a],this.p[3*i+a]))this.hold('UNOBSERVED_POSITION_WRITE');
  // Keep the configured skin even for zero-margin reporting; touching stays held.
  const clear=!this.reason&&Number.isFinite(margin)&&margin>=0&&margin<=this.shape[6]&&q?.certified&&!!(q.mask&(SIDE|BOTTOM));
  if(clear){this.counts.suppressed++;this.counts[kind]=(this.counts[kind]??0)+1;}
  return !!clear;
 }
 snapshot(){return {valid:!this.reason,reason:this.reason,...this.counts,primitive_count:this.primitives.length,epsilon_m:EPS,scope:'Owned discrete solver mutations; no arbitrary external array aliases, general CCD, underside/side collision response or physical quality approval.'};}
}

export function attachFiniteTopDomain(sim){
 if(sim.steps!==0)throw Error('Initial authored state only; no running-history reset');
 const domain=new FiniteTopDomain(sim.cloth,sim.mattress);sim.cloth.finiteTopDomain=domain;sim.mattress.finiteTopDomain=domain;return domain;
}
