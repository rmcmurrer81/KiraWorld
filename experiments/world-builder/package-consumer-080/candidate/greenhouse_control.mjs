// Session-only control of declared exported pivots. This never writes a package.
const need=(v,m)=>{if(!v)throw new TypeError(m);};
const deepFreeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(deepFreeze);Object.freeze(v);}return v;};
export function bindGreenhouse(scene,metadata){
 const pivots=[];scene.traverse(o=>{if(o.userData?.greenhouse_shade_louver)pivots.push(o);});
 if(!metadata.greenhouse){need(pivots.length===0,'Undeclared greenhouse pivots');return null;}
 const g=metadata.greenhouse,s=g.scenario;
 need(s?.contract==='authored_controlled_greenhouse_v1'&&s.growth_simulated===false&&s.readings_are_simulated===true&&g.session_state_export===false&&g.radiation_or_pressure_validation===false,'Unsupported greenhouse scenario');
 need(metadata.rooms.some(r=>r.source_id===s.room_id&&r.functional_role==='greenhouse'),'Unknown greenhouse room');
 need(g.exported_shade_percent===40&&s.shade_percent===40&&Array.isArray(s.beds)&&s.beds.length===4,'Unsupported exported greenhouse state');
 need(pivots.length===24&&new Set(pivots.map(o=>o.name)).size===24,'Greenhouse pivot set differs');
 for(const o of pivots){const base=o.userData.base_angle,a=base+.6*Math.PI/2,q=o.quaternion;need(Number.isFinite(base)&&o.userData.room_id===s.room_id&&Math.abs(q.x)<1e-6&&Math.abs(q.y)<1e-6&&Math.abs(Math.abs(q.z*Math.sin(a/2)+q.w*Math.cos(a/2))-1)<1e-6,'Greenhouse initial pivot differs');}
 const scenario=deepFreeze(structuredClone(s));let shade=40;
 const snapshot=()=>deepFreeze({roomId:'room:'+s.room_id,shadePercent:shade,illustrativeCanopyLight:Math.round(180+320*(1-shade/100)),scenario,sessionLocal:true,liveSensors:false,irradianceOrGrowthSimulation:false,mountedPanels:'saved export snapshots at shade 40%'});
 return Object.freeze({snapshot,setShade(value,roomId){
  need(roomId==='room:'+s.room_id,'Enter the greenhouse to use its local control');need(typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=100,'Shade must be between 0 and 100 percent');
  shade=value;for(const o of pivots)o.rotation.z=o.userData.base_angle+(1-shade/100)*Math.PI/2;scene.updateMatrixWorld(true);return snapshot();
 }});
}
