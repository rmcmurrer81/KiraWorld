// Original engineering fixture. XPBD distance constraints (Macklin et al., 2016).
// No downloaded geometry, pose swaps, generated textures, or person assets.
export const VERSION = 'original_bedding_xpbd_v1';
export const LIMITATIONS = Object.freeze({
  material_calibrated: false, cloth_self_collision: false, continuous_collision: false,
  pillow_volumetric_foam: false, pillow_bottom_fixed: true, head_is_kinematic_proxy: true,
  mattress_is_rigid_support: true, bed_frame_included: false, native_integration: false,
  cloth_pillow_coupling: false, body_proxy_beyond_spherical_head: false,
  collision_mesh: 'discrete particle contacts; triangle interiors and edge CCD are not validated',
  bending: 'compliant second-neighbour distance approximation, not dihedral bending',
  pillow: 'dynamic compliant height field with neighbouring elastic coupling; fixed supported base',
});
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
function need(ok, why) { if (!ok) throw new Error(why); }
function finite(v) { return typeof v === 'number' && Number.isFinite(v); }
const DIST = (p,a,b) => Math.hypot(p[3*a]-p[3*b],p[3*a+1]-p[3*b+1],p[3*a+2]-p[3*b+2]);

class Cloth {
  constructor(bed, {stretchCompliance=2e-7, bendCompliance=0.02}={}) {
    need(finite(stretchCompliance) && stretchCompliance>=0 && stretchCompliance<=0.1,'Invalid stretch compliance');
    need(finite(bendCompliance) && bendCompliance>=0 && bendCompliance<=10,'Invalid bend compliance');
    this.nx = 24; this.nz = 28; this.count=(this.nx+1)*(this.nz+1);
    this.width=bed.width+0.56; this.length=bed.length*0.81+0.30;
    this.centerZ=bed.length*0.25; this.margin=0.006;
    this.p=new Float64Array(this.count*3); this.prev=this.p.slice(); this.v=this.p.slice();
    this.invMass=new Float64Array(this.count); this.constraints=[]; this.triangles=[];
    const mass=0.6*this.width*this.length/this.count; // authored 0.6 kg/m^2, not measured fabric
    const id=(x,z)=>z*(this.nx+1)+x;
    for(let z=0;z<=this.nz;z++) for(let x=0;x<=this.nx;x++) {
      const i=id(x,z); this.p.set([(x/this.nx-.5)*this.width,bed.top+.13,(z/this.nz-.5)*this.length+this.centerZ],3*i);
      this.invMass[i]=1/mass;
      if(x<this.nx && z<this.nz) this.triangles.push(i,i+this.nx+1,i+1,i+1,i+this.nx+1,i+this.nx+2);
    }
    const add=(a,b,kind,c)=>this.constraints.push({a,b,rest:DIST(this.p,a,b),kind,compliance:c,lambda:0});
    for(let z=0;z<=this.nz;z++) for(let x=0;x<=this.nx;x++) {
      const i=id(x,z);
      if(x<this.nx)add(i,id(x+1,z),'stretch',stretchCompliance);
      if(z<this.nz)add(i,id(x,z+1),'stretch',stretchCompliance);
      if(x<this.nx && z<this.nz){add(i,id(x+1,z+1),'shear',stretchCompliance*2);add(id(x+1,z),id(x,z+1),'shear',stretchCompliance*2);}
      if(x<this.nx-1)add(i,id(x+2,z),'bend',bendCompliance);
      if(z<this.nz-1)add(i,id(x,z+2),'bend',bendCompliance);
    }
    this.initial=this.p.slice(); this.prev.set(this.p); this.grab=null;
  }
  predict(dt) {
    this.prev.set(this.p);
    const damping=Math.exp(-1.4*dt);
    for(let i=0;i<this.count;i++) {
      const k=i*3; this.v[k+1]-=9.81*dt;
      for(let a=0;a<3;a++){this.v[k+a]*=damping;this.p[k+a]+=this.v[k+a]*dt;}
    }
    for(const c of this.constraints)c.lambda=0;
    if(this.grab) {
      const g=this.grab; const d=Math.hypot(...g.target.map((v,a)=>v-g.current[a]));
      const t=d>0?Math.min(1,0.45*dt/d):0;
      for(let a=0;a<3;a++)g.current[a]+=(g.target[a]-g.current[a])*t;
    }
  }
  solve(dt, reverse) {
    const cs=this.constraints;
    for(let ci=0;ci<cs.length;ci++) {
      const c=cs[reverse?cs.length-1-ci:ci],a=3*c.a,b=3*c.b;
      const dx=this.p[a]-this.p[b],dy=this.p[a+1]-this.p[b+1],dz=this.p[a+2]-this.p[b+2];
      const length=Math.hypot(dx,dy,dz);if(length<1e-12)continue;
      const wa=this.grab?.index===c.a?0:this.invMass[c.a], wb=this.grab?.index===c.b?0:this.invMass[c.b];
      const alpha=c.compliance/(dt*dt), denom=wa+wb+alpha;if(denom===0)continue;
      const dl=(-(length-c.rest)-alpha*c.lambda)/denom;c.lambda+=dl;
      const s=dl/length;
      this.p[a]+=wa*s*dx;this.p[a+1]+=wa*s*dy;this.p[a+2]+=wa*s*dz;
      this.p[b]-=wb*s*dx;this.p[b+1]-=wb*s*dy;this.p[b+2]-=wb*s*dz;
    }
    if(this.grab)this.p.set(this.grab.current,3*this.grab.index);
  }
  collide(bed, head) {
    for(let i=0;i<this.count;i++) {
      const k=3*i,m=this.margin;
      // Sphere separation; then the static mattress/floor. Last projection is authoritative.
      const dx=this.p[k]-head.x,dy=this.p[k+1]-head.y,dz=this.p[k+2]-head.z;
      const d=Math.hypot(dx,dy,dz),r=head.radius+m;
      if(d<r){const s=r/(d||1);this.p[k]=head.x+dx*s;this.p[k+1]=head.y+(d?dy*s:r);this.p[k+2]=head.z+dz*s;}
      const lo=[-bed.width/2-m,bed.base-m,-bed.length/2-m],hi=[bed.width/2+m,bed.top+m,bed.length/2+m];
      if(this.p[k]>lo[0]&&this.p[k]<hi[0]&&this.p[k+1]>lo[1]&&this.p[k+1]<hi[1]&&this.p[k+2]>lo[2]&&this.p[k+2]<hi[2]) {
        let depth=Infinity,axis=0,side=0;
        for(let a=0;a<3;a++) for(const s of [0,1]) {
          const gap=s?hi[a]-this.p[k+a]:this.p[k+a]-lo[a];
          if(gap<depth){depth=gap;axis=a;side=s;}
        }
        this.p[k+axis]=side?hi[axis]:lo[axis];
      }
      if(this.p[k+1]<m)this.p[k+1]=m;
    }
  }
  finish(dt,bed) {
    for(let i=0;i<this.count;i++) {
      const k=3*i;
      for(let a=0;a<3;a++)this.v[k+a]=(this.p[k+a]-this.prev[k+a])/dt;
      const supported=(Math.abs(this.p[k+1]-bed.top-this.margin)<0.00001&&Math.abs(this.p[k])<=bed.width/2+this.margin&&Math.abs(this.p[k+2])<=bed.length/2+this.margin)||this.p[k+1]<=this.margin+1e-6;
      if(supported){const speed=Math.hypot(this.v[k],this.v[k+2]),scale=speed?Math.max(0,1-0.5*9.81*dt/speed):0;this.v[k]*=scale;this.v[k+2]*=scale;}
    }
  }
}

class Pillow {
  constructor(bed) {
    this.nx=16;this.nz=10;this.width=Math.min(.66,bed.width*.74);this.length=.42;this.z=-bed.length/2+.32;
    this.base=bed.top;this.height=.135;this.count=(this.nx+1)*(this.nz+1);
    this.p=new Float64Array(this.count*3);this.rest=new Float64Array(this.count);this.v=new Float64Array(this.count);
    this.prev=this.v.slice();this.lambda=this.v.slice();this.links=[];this.triangles=[];
    this.mass=.65/this.count;this.invMass=1/this.mass;this.compliance=.012;
    const id=(x,z)=>z*(this.nx+1)+x;
    for(let z=0;z<=this.nz;z++)for(let x=0;x<=this.nx;x++) {
      const i=id(x,z),u=x/this.nx,v=z/this.nz;
      // Original rounded rest profile. The evolving height, not an animation key, is rendered.
      this.rest[i]=this.base+.045+.09*Math.pow(Math.sin(Math.PI*u)*Math.sin(Math.PI*v),.42);
      this.p.set([(u-.5)*this.width,this.rest[i],(v-.5)*this.length+this.z],3*i);
      if(x<this.nx)this.links.push({a:i,b:id(x+1,z),rest:0,lambda:0});
      if(z<this.nz)this.links.push({a:i,b:id(x,z+1),rest:0,lambda:0});
      if(x<this.nx&&z<this.nz)this.triangles.push(i,i+this.nx+1,i+1,i+1,i+this.nx+1,i+this.nx+2);
    }
    for(const c of this.links)c.rest=this.rest[c.a]-this.rest[c.b];
  }
  predict(dt) {
    for(let i=0;i<this.count;i++){this.prev[i]=this.p[3*i+1];this.v[i]=(this.v[i]-9.81*dt)*Math.exp(-8*dt);this.p[3*i+1]+=this.v[i]*dt;this.lambda[i]=0;}
    for(const c of this.links)c.lambda=0;
  }
  solve(dt,head) {
    const alpha=this.compliance/(dt*dt),w=this.invMass;
    for(let i=0;i<this.count;i++) {
      const k=3*i,C=this.p[k+1]-this.rest[i],dl=(-C-alpha*this.lambda[i])/(w+alpha);
      this.lambda[i]+=dl;this.p[k+1]+=w*dl;
    }
    const lateralAlpha=.006/(dt*dt);
    for(const c of this.links){const C=this.p[3*c.a+1]-this.p[3*c.b+1]-c.rest,dl=(-C-lateralAlpha*c.lambda)/(2*w+lateralAlpha);c.lambda+=dl;this.p[3*c.a+1]+=w*dl;this.p[3*c.b+1]-=w*dl;}
    for(let i=0;i<this.count;i++) {
      const k=3*i,dx=this.p[k]-head.x,dz=this.p[k+2]-head.z,rr=head.radius*head.radius-dx*dx-dz*dz;
      if(rr>0)this.p[k+1]=Math.min(this.p[k+1],head.y-Math.sqrt(rr)-.002);
      this.p[k+1]=Math.max(this.base+.012,this.p[k+1]);
    }
  }
  finish(dt){for(let i=0;i<this.count;i++)this.v[i]=(this.p[3*i+1]-this.prev[i])/dt;}
}

export class BeddingSimulation {
  constructor({size='single',stretchCompliance=2e-7,bendCompliance=.02}={}) {
    need(['single','wide'].includes(size),'Unknown bed size');
    this.size=size;this.bed={width:size==='single'?1:1.6,length:size==='single'?2:2.1,base:.385,top:.565};
    this.cloth=new Cloth(this.bed,{stretchCompliance,bendCompliance});this.pillow=new Pillow(this.bed);
    this.head={x:0,y:1.02,z:this.pillow.z,radius:.12};this.headTarget={...this.head};
    this.time=0;this.steps=0;this.fixedDt=1/60;this.substeps=4;this.iterations=10;
  }
  setHead({site='pillow',loaded=false,x=0}={}) {
    need(['pillow','blanket'].includes(site)&&typeof loaded==='boolean'&&finite(x),'Invalid head command');
    const z=site==='pillow'?this.pillow.z:.20;
    // Lift before traversing to another site. The head never teleports through bedding.
    const targetY=loaded?(site==='pillow'?this.bed.top+.19:this.bed.top+.126):1.02;
    this.headTarget={x:clamp(x,-this.pillow.width*.3,this.pillow.width*.3),y:targetY,z,radius:.12};
  }
  grabCorner() {
    const index=this.cloth.nx;const p=Array.from(this.cloth.p.slice(3*index,3*index+3));
    this.cloth.grab={index,current:p.slice(),target:[p[0],Math.max(.98,p[1]),p[2]]};
  }
  moveGrabAcross(){need(this.cloth.grab,'Grab the corner first');const g=this.cloth.grab;g.target=[-this.bed.width*.30,1.08,g.target[2]+.18];}
  releaseGrab(){this.cloth.grab=null;}
  step(frames=1) {
    need(Number.isInteger(frames)&&frames>=0&&frames<=1200,'Use 0..1200 fixed frames');
    const dt=this.fixedDt/this.substeps;
    for(let f=0;f<frames;f++)for(let s=0;s<this.substeps;s++) {
      const h=this.head,t=this.headTarget, horizontal=Math.hypot(h.x-t.x,h.z-t.z);
      let target=horizontal>.003&&h.y<1.019?[h.x,1.02,h.z]:horizontal>.003?[t.x,1.02,t.z]:[t.x,t.y,t.z];
      const d=Math.hypot(target[0]-h.x,target[1]-h.y,target[2]-h.z),q=d?Math.min(1,.22*dt/d):0;
      h.x+=(target[0]-h.x)*q;h.y+=(target[1]-h.y)*q;h.z+=(target[2]-h.z)*q;
      this.cloth.predict(dt);this.pillow.predict(dt);
      for(let it=0;it<this.iterations;it++){this.pillow.solve(dt,h);this.cloth.solve(dt,it%2===0);this.cloth.collide(this.bed,h);}
      this.cloth.finish(dt,this.bed);this.pillow.finish(dt);this.time+=dt;this.steps++;
    }
    return this.metrics();
  }
  metrics() {
    const c=this.cloth,p=this.pillow,b=this.bed;
    let speed2=0,stretch=0,lo=Infinity,hi=-Infinity,penetration=0,headPenetration=0,headContacts=0,minPillow=Infinity,maxPillowIndent=0;
    for(let i=0;i<c.count;i++) {
      const k=3*i,x=c.p[k],y=c.p[k+1],z=c.p[k+2];
      speed2+=c.v[k]**2+c.v[k+1]**2+c.v[k+2]**2;lo=Math.min(lo,y);hi=Math.max(hi,y);
      if(Math.abs(x)<b.width/2&&y>b.base&&Math.abs(z)<b.length/2)penetration=Math.max(penetration,b.top-y);
      const headDistance=Math.hypot(x-this.head.x,y-this.head.y,z-this.head.z);
      headPenetration=Math.max(headPenetration,this.head.radius-headDistance);
      if(headDistance<=this.head.radius+c.margin+.0001)headContacts++;
    }
    for(const q of c.constraints)if(q.kind==='stretch')stretch=Math.max(stretch,DIST(c.p,q.a,q.b)/q.rest-1);
    for(let i=0;i<p.count;i++){minPillow=Math.min(minPillow,p.p[3*i+1]);maxPillowIndent=Math.max(maxPillowIndent,p.rest[i]-p.p[3*i+1]);}
    const center=Math.floor(p.nz/2)*(p.nx+1)+Math.floor(p.nx/2);
    const centerHeight=p.p[3*center+1];
    return {version:VERSION,time_s:this.time,finite:[...c.p,...c.v,...p.p,...p.v].every(Number.isFinite),cloth_nodes:c.count,
      cloth_rms_speed_mps:Math.sqrt(speed2/c.count),cloth_min_y_m:lo,cloth_max_y_m:hi,cloth_height_span_m:hi-lo,
      maximum_stretch_fraction:stretch,mattress_penetration_m:Math.max(0,penetration),head_penetration_m:Math.max(0,headPenetration),head_contact_nodes:headContacts,
      pillow_center_height_m:centerHeight,pillow_center_indentation_m:p.rest[center]-centerHeight,pillow_max_indentation_m:maxPillowIndent,
      pillow_min_y_m:minPillow,grab_active:!!c.grab,head:{...this.head},limitations:LIMITATIONS};
  }
}
