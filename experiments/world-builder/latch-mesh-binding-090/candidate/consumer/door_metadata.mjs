import {LATCH_HATCH_CONTRACT,validateLatchedDoor} from '../shared/latched_metadata.mjs';
// Consumer-side interpretation of exported collision boxes. No authoring code.
export const HATCH='authored_pressure_hatch_geometry_v1';
const EPS=1e-7;
const need=(v,m)=>{if(!v)throw new TypeError(m);};
const vec=v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite);
const same=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<EPS);
const box=(p,s)=>({min:p.map((v,i)=>v-s[i]/2),max:p.map((v,i)=>v+s[i]/2)});
export const sameBounds=(a,b)=>a&&b&&same(a.min,b.min)&&same(a.max,b.max);
export const unionBounds=boxes=>({min:[0,1,2].map(i=>Math.min(...boxes.map(b=>b.min[i]))),max:[0,1,2].map(i=>Math.max(...boxes.map(b=>b.max[i])))});
const corners=b=>[0,1].flatMap(x=>[0,1].flatMap(y=>[0,1].map(z=>[b[x?'max':'min'][0],b[y?'max':'min'][1],b[z?'max':'min'][2]])));
const rotate=(p,h,a)=>{const x=p[0]-h[0],z=p[2]-h[2],c=Math.cos(a),s=Math.sin(a);return[h[0]+c*x+s*z,p[1],h[2]-s*x+c*z];};
const pointBounds=ps=>({min:[0,1,2].map(i=>Math.min(...ps.map(p=>p[i]))),max:[0,1,2].map(i=>Math.max(...ps.map(p=>p[i])))});
export function rotateBounds(bounds,hinge,angle){return pointBounds(corners(bounds).map(p=>rotate(p,hinge,angle)));}
export function analyticSweep(boxes,hinge,openAngle){
 const lo=Math.min(0,openAngle),hi=Math.max(0,openAngle),points=[];
 for(const b of boxes)for(const p of corners(b)){
  const x=p[0]-hinge[0],z=p[2]-hinge[2],angles=[lo,hi];
  for(const phase of [Math.atan2(z,x),Math.atan2(-x,z)])for(let k=-2;k<=2;k++){const a=phase+k*Math.PI;if(a>lo&&a<hi)angles.push(a);}
  points.push(...angles.map(a=>rotate(p,hinge,a)));
 }return pointBounds(points);
}
export function movingForDoor(d,colliders){const ids=new Set([HATCH,LATCH_HATCH_CONTRACT].includes(d.variant)?d.kinematic_node_ids:[d.leaf_node_id]);return [...colliders.values()].filter(c=>ids.has(c.owner_node_id)&&c.motion==='kinematic');}
export function validateDoorShape(d,nodes,colliders,metadata){
 if(d.variant===LATCH_HATCH_CONTRACT)return validateLatchedDoor(d,nodes,colliders,metadata);
 const leaf=nodes.get(d.leaf_node_id),h=d.hinge;
 need(leaf?.kind==='door_leaf','Invalid leaf');
 if(d.variant===HATCH){
  need(d.collision_policy==='authored_hatch_part_aabbs_and_analytic_sweep'&&h.leaf_geometry_origin==='hinge_local','Unsupported hatch policy/origin');
  need(d.latch_simulation===false&&d.latch_state==='static_retracted','Unsupported latch behavior');
  const moving=d.kinematic_node_ids,fixed=d.frame_node_ids;
  need(Array.isArray(moving)&&moving.length>1&&moving.length<=128&&new Set(moving).size===moving.length&&moving.includes(leaf.id),'Invalid hatch moving parts');
  need(Array.isArray(fixed)&&fixed.length>1&&fixed.length<=128&&new Set(fixed).size===fixed.length&&!fixed.some(id=>moving.includes(id)),'Invalid hatch fixed parts');
  for(const [ids,motion] of [[moving,'kinematic'],[fixed,'static']])for(const id of ids){
   const n=nodes.get(id),linked=[...colliders.values()].filter(c=>c.owner_node_id===id);
   need(n?.motion===motion&&n.representation?.type==='authored_hatch_part_parameters'&&n.representation.recipe_contract===HATCH&&n.hatch_part_id===n.representation.parameters?.id,'Invalid hatch part provenance');
   need(n.transform?.origin===(motion==='kinematic'?'hatch_hinge':'hatch_origin')&&same(n.transform.scale,[1,1,1])&&n.transform.rotation_y_radians===0,'Invalid hatch part transform');
   need(linked.length>0&&linked.every(c=>c.motion===motion&&c.proxy===(motion==='kinematic'?'authored_hatch_rotated_part_aabb':'authored_hatch_static_part_bounds')&&typeof c.source_collider_id==='string'),'Hatch collision ownership differs');
   need(sameBounds(n.bounds,unionBounds(linked.map(c=>c.bounds))),'Hatch part bounds differ');
   if(motion==='kinematic')need(same(n.transform.position,h.position),'Moving hatch origin differs');
  }
  const movingBoxes=movingForDoor(d,colliders);
  need(sameBounds(d.swing_bounds,analyticSweep(movingBoxes.map(c=>c.bounds),h.position,h.open_angle)),'Hatch analytic sweep differs');
  const center=leaf.bounds.min.map((v,i)=>(v+leaf.bounds.max[i])/2);
  need(same(center,h.position.map((v,i)=>v+h.leaf_local_center[i])),'Hatch leaf center differs');
  return movingBoxes;
 }
 need(d.variant===undefined&&d.collision_policy==='conservative_rotated_leaf_aabb_and_quarter_disc_sweep','Unsupported door variant');
 const size=leaf.representation?.size;
 need(vec(size)&&size.every(v=>v>0),'Invalid ordinary leaf dimensions');
 const axis=Math.abs(size[0]-.065)<EPS?0:Math.abs(size[2]-.065)<EPS?2:-1,t=axis===0?2:0;
 need(axis>=0&&size[t]>=.86&&size[t]<=7.96&&Math.abs(h.leaf_local_center[axis])<EPS&&Math.abs(h.leaf_local_center[t]-size[t]/2)<EPS&&Math.abs(h.leaf_local_center[1]-(.0125+size[1]/2))<EPS,'Unsupported ordinary leaf pivot');
 const linked=[...colliders.values()].filter(c=>c.owner_node_id===leaf.id),center=h.position.map((v,i)=>v+h.leaf_local_center[i]);
 const body=linked.filter(c=>c.proxy===d.collision_policy),hardware=linked.filter(c=>c.proxy==='attached_hardware_rotated_aabb');
 need(body.length===1&&[1,5].includes(linked.length)&&linked.every(c=>c.motion==='kinematic')&&sameBounds(body[0].bounds,box(center,size)),'Ordinary leaf collision differs');
 if(linked.length===5){
  const expected=[];
  for(const sign of [-1,1]){
   const pc=[0,0,0],ps=[0,size[1]*.68,0];pc[axis]=sign*.0375;ps[axis]=.008;ps[t]=size[t]*.77;expected.push({center:pc,size:ps});
   const hc=[0,-.12,0],hs=[0,.27,0];hc[axis]=sign*.07075;hc[t]=size[t]*.34;hs[axis]=.0795;hs[t]=.075;expected.push({center:hc,size:hs});
  }
  need(hardware.length===4&&expected.every(e=>hardware.filter(c=>same(c.leaf_local_center,e.center)&&same(c.local_size,e.size)&&sameBounds(c.bounds,box(center.map((v,i)=>v+e.center[i]),e.size))).length===1),'Ordinary attached hardware differs');
 }
 const depth=hardware.length?.1105:.0325,extent=hardware.length?Math.max(size[t]+.0325,Math.hypot(size[t]*.84+.0375,depth)):size[t]+.0325;
 const sweep={min:[h.position[0]-depth,h.position[1],h.position[2]-depth],max:[h.position[0]+depth,h.position[1]+size[1]+.025,h.position[2]+depth]};
 sweep.max[t]=h.position[t]+extent;const sign=Math.sign(h.open_angle)*(axis===0?1:-1);if(sign>0)sweep.max[axis]=h.position[axis]+extent;else sweep.min[axis]=h.position[axis]-extent;
 need(sameBounds(sweep,d.swing_bounds),'Ordinary sweep differs');
 need(d.frame_node_ids?.length===3&&new Set(d.frame_node_ids).size===3&&d.frame_node_ids.every(id=>nodes.get(id)?.kind==='door_frame'),'Invalid ordinary frames');
 return linked;
}
