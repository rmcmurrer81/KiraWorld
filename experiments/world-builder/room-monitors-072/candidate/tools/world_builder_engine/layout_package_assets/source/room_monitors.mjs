import {MARS_REFERENCE,referencePanel} from './mars_reference.mjs';
const freeze=o=>{if(o&&typeof o==='object'){Object.values(o).forEach(freeze);Object.freeze(o);}return o;};
const row=(label,value)=>({label,value});
export function createRoomMonitorData(kind,{marsData=null,geometry=null,roomId=null,doorStates=[]}={}){
 if(kind==='planet'||kind==='weather'){
  if(!marsData)return null;
  const panel=referencePanel(kind);
  return freeze({...panel,contract:'authored_room_monitor_v1',kind,rows:panel.rows.map(r=>({...r})),sources:panel.sourceIds.map(id=>MARS_REFERENCE.sources[id]),current_local_conditions:false});
 }
 if(kind==='airlock'){
  const room=geometry?.rooms.find(r=>r.id===roomId&&geometry.functional_program?.[r.id]==='airlock');if(!room)return null;
  const portals=geometry.portals.filter(p=>[p.room_a,p.room_b].includes(room.id)),known=new Map(doorStates.map(d=>[d.id,d]));
  const rows=portals.map(p=>{const other=geometry.rooms.find(r=>r.id===(p.room_a===room.id?p.room_b:p.room_a)),state=known.get(p.id);return row(other?.name||p.id,state?(state.motionHeld?'HELD / ': '')+String(state.state).toUpperCase():'UNAVAILABLE');});
  return freeze({contract:'authored_room_monitor_v1',kind,title:'AIRLOCK / LOCAL DOORS',badge:'ACTUAL PREVIEW STATE · NO PRESSURE SENSOR',rows:[...rows,row('Pressure / leak test','UNAVAILABLE / NOT SIMULATED'),row('Closed door means','Closed geometry only')],sources:[],sourceIds:[],live:false,local_preview_state:true,physical_pressure_simulated:false,airtightness_validated:false});
 }
 const panels={
  equipment_vestibule:{title:'EVA / EQUIPMENT CHECK',rows:[row('Suit inspection','DEMO CHECKLIST · pending'),row('Oxygen supply','Sensor unavailable'),row('Battery / suit link','Not connected'),row('Readiness','No safety certification')]},
  laboratory:{title:'LAB / SAMPLE WORKBENCH',rows:[row('Sample queue','DEMO A-01 · not analyzed'),row('Instrument link','Not connected'),row('Containment sensor','Unavailable'),row('Analysis results','No generated measurements')]},
  habitat:{title:'HABITAT / SYSTEMS',rows:[row('Room temperature','Sensor unavailable'),row('Water / power','Not connected'),row('Air quality','No sensor data'),row('Resident activity','Not simulated')]},
  observation:{title:'OBSERVATION / OUTSIDE',rows:[row('Environment source','No bound Mars request'),row('Local weather','Sensor unavailable'),row('Exterior equipment','Not connected'),row('Current conditions','Unknown')]}
 };
 if(kind==='observation'&&marsData)return createRoomMonitorData('weather',{marsData});
 const panel=panels[kind];if(!panel)throw new TypeError('Unsupported room monitor role');
 return freeze({...panel,contract:'authored_room_monitor_v1',kind,badge:'AUTHORED DEMO · SENSORS UNAVAILABLE',sources:[],sourceIds:[],live:false,current_local_conditions:false});
}
export function paintRoomMonitor(ctx,data){
 if(!data)throw new TypeError('Missing monitor data');
 ctx.fillStyle='#091c24';ctx.fillRect(0,0,1024,512);ctx.fillStyle='#89ada2';ctx.fillRect(0,0,10,512);
 ctx.fillStyle='#edf0df';ctx.font='600 38px Segoe UI,sans-serif';ctx.fillText(data.title,30,54,962);
 ctx.fillStyle='#edc797';ctx.font='23px Segoe UI,sans-serif';ctx.fillText(data.badge,30,94,962);
 if(data.subtitle){ctx.fillStyle='#c6d7db';ctx.font='24px Segoe UI,sans-serif';ctx.fillText(data.subtitle,30,132,960);}
 ctx.strokeStyle='#36505a';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(30,145);ctx.lineTo(994,145);ctx.stroke();
 for(const [i,r] of data.rows.entries()){
  const y=191+i*55;ctx.fillStyle='#aabfc2';ctx.font='26px Segoe UI,sans-serif';ctx.fillText(r.label,30,y,448);
  ctx.fillStyle='#f0f1df';ctx.font='600 27px Segoe UI,sans-serif';ctx.fillText((r.approximate?'~ ':'')+String(r.value)+(r.unit?' '+r.unit:''),490,y,500);
 }
 ctx.fillStyle='#adc7ca';ctx.font='21px Segoe UI,sans-serif';
 const source=data.sources.map(s=>s.title).join(' / ');ctx.fillText(source?source:'Local authored preview · no physical telemetry',30,454,960);
 ctx.fillStyle='#d9b88d';ctx.font='21px Segoe UI,sans-serif';ctx.fillText(data.kind==='weather'?'Archived observations at Jezero; not current habitat weather.':data.kind==='planet'?'Planet reference facts; not measurements at this fictional base.':'Scenario display; no operational science or life-support claim.',30,492,960);
}
export function createRoomMonitorMaterial(THREE,data,canvasFactory){
 const canvas=canvasFactory();if(!canvas)throw new TypeError('Room monitor requires a canvas');canvas.width=1024;canvas.height=512;paintRoomMonitor(canvas.getContext('2d'),data);
 const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
 const material=new THREE.MeshStandardMaterial({color:0xffffff,map,roughness:.6,metalness:0,emissive:0xffffff,emissiveMap:map,emissiveIntensity:.4});
 material.userData={contract:'authored_room_monitor_v1',monitor_data:data};
 return {material,canvas,data,key:JSON.stringify(data),refresh(next){const key=JSON.stringify(next);if(key===this.key)return false;paintRoomMonitor(canvas.getContext('2d'),next);map.needsUpdate=true;this.key=key;this.data=next;material.userData.monitor_data=next;return true;}};
}
