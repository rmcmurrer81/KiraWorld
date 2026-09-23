// Original supported mattress study. The reviewed bedding base remains byte-identical.
import {BeddingSimulation as BaseSimulation,LIMITATIONS as BASE_LIMITS} from './bedding_base.mjs';
import {solveSurfaceContacts,surfaceContactReport,finishSurfaceContactVelocities} from './surface_contacts.mjs';
import {compileFrame,solveFrameContacts,finishFrameContactVelocities,frameContactReport} from './frame_contacts.mjs';
export const VERSION='original_supported_mattress_frame_contact_v3';
export const LIMITATIONS=Object.freeze({...BASE_LIMITS,mattress_is_rigid_support:false,bed_frame_included:true,native_integration:true,
  mattress:'original dynamic height field; fixed supported bottom, no lateral or volumetric foam response',
  mattress_load:'authored smoothly applied distributed force; not a calibrated person or measured pressure map',
  mattress_two_way_bedding_forces:false,pillow_bottom_fixed:false,
  frame_contact:'discrete triangle/convex chamfered-mesh contacts, one-way rigid response; no CCD or frame load deformation',
  pillow:'dynamic height field supported by the current mattress; no lateral or volumetric foam response',
  collision_mesh:'discrete particle and barycentric edge/triangle upper-surface contact with the same piecewise-planar mattress; no CCD or self-collision',
  mattress_contact_direction:'upper-surface height-field barrier extends down to the floor within its footprint; under-mattress cloth routing is not supported',
});
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function need(ok,message){if(!ok)throw Error(message);}
function finite(x){return typeof x==='number'&&Number.isFinite(x);}
function alignDrapeGrid(cloth,bed){
  // Author seam vertices at the initial supported rim so coarse elements can
  // bend there. This changes the flat construction grid, never a running pose.
  function axis(count,lo,hi,boundaries){
    const knots=[[0,lo],[count,hi]];
    for(const value of boundaries)if(value>lo&&value<hi){const i=Math.round((value-lo)/(hi-lo)*count);if(i>0&&i<count&&!knots.some(k=>k[0]===i))knots.push([i,value]);}
    knots.sort((a,b)=>a[0]-b[0]);return Array.from({length:count+1},(_,i)=>{const end=knots.findIndex(k=>k[0]>=i);if(end===0)return knots[0][1];const a=knots[end-1],b=knots[end];return a[1]+(b[1]-a[1])*(i-a[0])/(b[0]-a[0]);});
  }
  const m=cloth.margin,xknots=[-bed.width/2-m,bed.width/2+m],zknots=[-bed.length/2-m,bed.length/2+m];
  const xs=axis(cloth.nx,-cloth.width/2,cloth.width/2,xknots),zs=axis(cloth.nz,cloth.centerZ-cloth.length/2,cloth.centerZ+cloth.length/2,zknots);
  for(let z=0;z<=cloth.nz;z++)for(let x=0;x<=cloth.nx;x++){const i=z*(cloth.nx+1)+x;cloth.p[3*i]=xs[x];cloth.p[3*i+2]=zs[z];}
  for(const c of cloth.constraints)c.rest=Math.hypot(...[0,1,2].map(a=>cloth.p[3*c.a+a]-cloth.p[3*c.b+a]));
  cloth.prev.set(cloth.p);cloth.initial.set(cloth.p);
}

export class MattressSurface {
  constructor(bed,{compliance=.012}={}){
    need(finite(compliance)&&compliance>=.001&&compliance<=.04,'Mattress compliance must be within .001..04');
    this.width=bed.width;this.length=bed.length;this.base=bed.base;this.top=bed.top;
    this.nx=20;this.nz=30;this.count=(this.nx+1)*(this.nz+1);
    this.p=new Float64Array(this.count*3);this.v=new Float64Array(this.count);this.prev=new Float64Array(this.count);
    this.rest=new Float64Array(this.count);this.invMass=new Float64Array(this.count);this.compliance=new Float64Array(this.count);
    this.lambda=new Float64Array(this.count);this.weights=new Float64Array(this.count);this.triangles=[];this.links=[];
    this.minimumThickness=.03;this.maximumHeight=this.top+.025;
    const dx=this.width/this.nx,dz=this.length/this.nz,referenceArea=(1/20)*(2/30);
    const id=(x,z)=>z*(this.nx+1)+x;
    for(let z=0;z<=this.nz;z++)for(let x=0;x<=this.nx;x++){
      const i=id(x,z),area=dx*dz*((x===0||x===this.nx)? .5:1)*((z===0||z===this.nz)? .5:1),mass=10*area;
      this.invMass[i]=1/mass;this.compliance[i]=compliance*referenceArea/area;
      // An authored support preload balances mattress self-weight at the stated unloaded top.
      this.rest[i]=this.top+mass*9.81*this.compliance[i];
      this.p.set([(x/this.nx-.5)*this.width,this.top,(z/this.nz-.5)*this.length],3*i);this.prev[i]=this.top;
      if(x<this.nx)this.links.push({a:i,b:id(x+1,z),lambda:0});
      if(z<this.nz)this.links.push({a:i,b:id(x,z+1),lambda:0});
      if(x<this.nx&&z<this.nz)this.triangles.push(i,i+this.nx+1,i+1,i+1,i+this.nx+1,i+this.nx+2);
    }
    this.load={site:'center',newtons:0,target:0,x:0,z:.20,rx:Math.min(.32,this.width*.34),rz:.38};this.updateWeights();
  }
  updateWeights(){
    let total=0;const l=this.load;
    for(let i=0;i<this.count;i++){
      const r=((this.p[3*i]-l.x)/l.rx)**2+((this.p[3*i+2]-l.z)/l.rz)**2;
      this.weights[i]=r<1?(1-r)**2:0;total+=this.weights[i];
    }
    need(total>0,'Load footprint misses mattress');for(let i=0;i<this.count;i++)this.weights[i]/=total;
  }
  setLoad({loaded,site=this.load.site,force=220}={}){
    need(typeof loaded==='boolean'&&['center','pillow'].includes(site)&&finite(force)&&force>=0&&force<=300,'Invalid bounded mattress load');
    need(site===this.load.site||this.load.newtons<.01,'Remove the mattress load before changing its site');
    this.load.site=site;this.load.z=site==='pillow'?-this.length/2+.32:.20;this.load.target=loaded?force:0;this.updateWeights();
  }
  predict(dt){
    const l=this.load;l.newtons+=clamp(l.target-l.newtons,-220*dt,220*dt);
    for(let i=0;i<this.count;i++){
      this.prev[i]=this.p[3*i+1];
      this.v[i]=(this.v[i]-(9.81+l.newtons*this.weights[i]*this.invMass[i])*dt)*Math.exp(-9*dt);
      this.p[3*i+1]+=this.v[i]*dt;this.lambda[i]=0;
    }
    for(const c of this.links)c.lambda=0;
  }
  solve(dt){
    for(let i=0;i<this.count;i++){
      const a=this.compliance[i]/(dt*dt),w=this.invMass[i];
      const dl=(-(this.p[3*i+1]-this.rest[i])-a*this.lambda[i])/(w+a);
      this.lambda[i]+=dl;this.p[3*i+1]+=w*dl;
    }
    const a=.004/(dt*dt);
    for(const c of this.links){
      const wa=this.invMass[c.a],wb=this.invMass[c.b];
      const dl=(-(this.p[3*c.a+1]-this.p[3*c.b+1])-a*c.lambda)/(wa+wb+a);
      c.lambda+=dl;this.p[3*c.a+1]+=wa*dl;this.p[3*c.b+1]-=wb*dl;
    }
    for(let i=0;i<this.count;i++)this.p[3*i+1]=clamp(this.p[3*i+1],this.base+this.minimumThickness,this.maximumHeight);
  }
  finish(dt){for(let i=0;i<this.count;i++)this.v[i]=(this.p[3*i+1]-this.prev[i])/dt;}
  sampleTop(x,z){
    need(finite(x)&&finite(z),'Surface query must be finite');
    if(Math.abs(x)>this.width/2+1e-10||Math.abs(z)>this.length/2+1e-10)return null;
    const u=clamp((x/this.width+.5)*this.nx,0,this.nx),v=clamp((z/this.length+.5)*this.nz,0,this.nz);
    const ix=Math.min(this.nx-1,Math.floor(u)),iz=Math.min(this.nz-1,Math.floor(v)),fx=u-ix,fz=v-iz;
    const a=iz*(this.nx+1)+ix,b=a+1,c=a+this.nx+1,d=c+1;
    const ids=fx+fz<=1?[a,b,c]:[b,c,d],weights=fx+fz<=1?[1-fx-fz,fx,fz]:[1-fz,1-fx,fx+fz-1];
    let height=0,velocity=0;
    for(let n=0;n<3;n++){height+=weights[n]*this.p[3*ids[n]+1];velocity+=weights[n]*this.v[ids[n]];}
    const hx=fx+fz<=1?this.p[3*b+1]-this.p[3*a+1]:this.p[3*d+1]-this.p[3*c+1];
    const hz=fx+fz<=1?this.p[3*c+1]-this.p[3*a+1]:this.p[3*d+1]-this.p[3*b+1];
    const normal=[-hx/(this.width/this.nx),1,-hz/(this.length/this.nz)],length=Math.hypot(...normal);
    return {height,normal:normal.map(v=>v/length),velocity,indices:ids,weights};
  }
}

function collideCloth(c,bed,head,surface){
  for(let i=0;i<c.count;i++){
    const k=3*i,m=c.margin,dx=c.p[k]-head.x,dy=c.p[k+1]-head.y,dz=c.p[k+2]-head.z,d=Math.hypot(dx,dy,dz),r=head.radius+m;
    if(d<r){const t=r/(d||1);c.p[k]=head.x+dx*t;c.p[k+1]=head.y+(d?dy*t:r);c.p[k+2]=head.z+dz*t;}
    const x=c.p[k],y=c.p[k+1],z=c.p[k+2],inside=Math.abs(x)<bed.width/2+m&&Math.abs(z)<bed.length/2+m;
    if(inside){
      const sample=surface.sampleTop(clamp(x,-bed.width/2,bed.width/2),clamp(z,-bed.length/2,bed.length/2));
      if(y<sample.height+m){
        // This top-drape fixture is an upper height-field barrier. Choosing a
        // nearest underside face could tunnel vertices below the mattress.
        c.p[k+1]=sample.height+m;
      }
    }
    if(c.p[k+1]<m)c.p[k+1]=m;
  }
}
function finishCloth(c,dt,surface){
  for(let i=0;i<c.count;i++){
    const k=3*i;for(let a=0;a<3;a++)c.v[k+a]=(c.p[k+a]-c.prev[k+a])/dt;
    const top=surface.sampleTop(c.p[k],c.p[k+2]);
    if((top&&Math.abs(c.p[k+1]-top.height-c.margin)<1e-5)||c.p[k+1]<=c.margin+1e-6){
      const speed=Math.hypot(c.v[k],c.v[k+2]),scale=speed?Math.max(0,1-.5*9.81*dt/speed):0;c.v[k]*=scale;c.v[k+2]*=scale;
    }
  }
}

export class BeddingSimulation extends BaseSimulation {
  constructor({size='single',mattressCompliance=.012,frameParts=null,...clothOptions}={}){
    super({size,...clothOptions});this.mattress=new MattressSurface(this.bed,{compliance:mattressCompliance});
    this.frame=frameParts?compileFrame(frameParts):[];alignDrapeGrid(this.cloth,this.bed);
    // Coupled XPBD contacts participate in the same position solve as distance
    // constraints. Keep the physical previous position intact so velocity is
    // the net displacement, not the sum of iterative stabilization corrections.
    if(this.frame.length)this.cloth.splitPositionStabilization=false;
    this.iterations=this.frame.length?40:20;
    const p=this.pillow;p.support=new Float64Array(p.count);p.restOffset=Float64Array.from(p.rest,v=>v-this.bed.top);
    this.updatePillowSupport();
  }
  setMattressLoad(options){this.mattress.setLoad(options);}
  updatePillowSupport(){
    const p=this.pillow;
    for(let i=0;i<p.count;i++){
      const top=this.mattress.sampleTop(p.p[3*i],p.p[3*i+2]);need(top,'Pillow support leaves mattress');
      p.support[i]=top.height;p.rest[i]=top.height+p.restOffset[i];
    }
    for(const c of p.links)c.rest=p.rest[c.a]-p.rest[c.b];
  }
  solvePillow(dt){
    const p=this.pillow,alpha=p.compliance/(dt*dt),w=p.invMass,h=this.head;
    for(let i=0;i<p.count;i++){
      const k=3*i,dl=(-(p.p[k+1]-p.rest[i])-alpha*p.lambda[i])/(w+alpha);p.lambda[i]+=dl;p.p[k+1]+=w*dl;
    }
    const a=.006/(dt*dt);
    for(const c of p.links){const dl=(-(p.p[3*c.a+1]-p.p[3*c.b+1]-c.rest)-a*c.lambda)/(2*w+a);c.lambda+=dl;p.p[3*c.a+1]+=w*dl;p.p[3*c.b+1]-=w*dl;}
    for(let i=0;i<p.count;i++){
      const k=3*i,dx=p.p[k]-h.x,dz=p.p[k+2]-h.z,rr=h.radius*h.radius-dx*dx-dz*dz;
      if(rr>0)p.p[k+1]=Math.min(p.p[k+1],h.y-Math.sqrt(rr)-.002);
      p.p[k+1]=Math.max(p.support[i]+.012,p.p[k+1]);
    }
  }
  step(frames=1){
    need(Number.isInteger(frames)&&frames>=0&&frames<=1200,'Use 0..1200 fixed frames');const dt=this.fixedDt/this.substeps;
    for(let f=0;f<frames;f++)for(let s=0;s<this.substeps;s++){
      const h=this.head,t=this.headTarget,horizontal=Math.hypot(h.x-t.x,h.z-t.z);
      const target=horizontal>.003&&h.y<1.019?[h.x,1.02,h.z]:horizontal>.003?[t.x,1.02,t.z]:[t.x,t.y,t.z];
      const d=Math.hypot(target[0]-h.x,target[1]-h.y,target[2]-h.z),q=d?Math.min(1,.22*dt/d):0;
      h.x+=(target[0]-h.x)*q;h.y+=(target[1]-h.y)*q;h.z+=(target[2]-h.z)*q;
      this.mattress.predict(dt);this.cloth.predict(dt);this.pillow.predict(dt);this.cloth.frameActiveContacts=[];this.cloth.surfaceActiveContacts=[];
      for(let i=0;i<this.iterations;i++){
        this.mattress.solve(dt);this.updatePillowSupport();this.solvePillow(dt);
        this.cloth.solve(dt,i%2===0);collideCloth(this.cloth,this.bed,h,this.mattress);
        if(this.frame.length&&i%2===1){solveSurfaceContacts(this.cloth,this.mattress,{passes:1,reset:false});solveFrameContacts(this.cloth,this.frame,{passes:1,reset:false});}
      }
      this.lastSurfaceContacts=solveSurfaceContacts(this.cloth,this.mattress,{passes:2,reset:false});
      if(this.frame.length)for(let pass=0;pass<2;pass++){solveFrameContacts(this.cloth,this.frame,{passes:2,reset:false});this.lastSurfaceContacts=solveSurfaceContacts(this.cloth,this.mattress,{passes:2,reset:false});}
      this.mattress.finish(dt);finishCloth(this.cloth,dt,this.mattress);finishSurfaceContactVelocities(this.cloth,this.mattress,dt);finishFrameContactVelocities(this.cloth,dt);this.pillow.finish(dt);this.time+=dt;this.steps++;
    }
    return this.metrics();
  }
  metrics(){
    const m=super.metrics();if(!this.mattress)return m;
    const mat=this.mattress;let compression=0,min=Infinity,penetration=0;
    for(let i=0;i<mat.count;i++){compression=Math.max(compression,mat.top-mat.p[3*i+1]);min=Math.min(min,mat.p[3*i+1]-mat.base);}
    for(let i=0;i<this.cloth.count;i++){
      const k=3*i,top=mat.sampleTop(this.cloth.p[k],this.cloth.p[k+2]);
      if(top&&this.cloth.p[k+1]>mat.base)penetration=Math.max(penetration,top.height-this.cloth.p[k+1]);
    }
    return {...m,version:VERSION,limitations:{...LIMITATIONS,bed_frame_included:!!this.frame?.length},finite:m.finite&&[...mat.p,...mat.v].every(Number.isFinite),
      mattress_penetration_m:Math.max(0,penetration),mattress_center_compression_m:Math.max(0,mat.top-mat.sampleTop(0,.20).height),
      mattress_max_compression_m:compression,mattress_min_thickness_m:min,mattress_load_newtons:mat.load.newtons,
      mattress_load_site:mat.load.site,mattress_nodes:mat.count,
      frame_contact:this.frame?frameContactReport(this.cloth,this.frame):null,frame_parts:this.frame?.length??0,
      surface_mesh_contact:surfaceContactReport(this.cloth,mat),last_surface_constraints:this.lastSurfaceContacts??null};
  }
}
