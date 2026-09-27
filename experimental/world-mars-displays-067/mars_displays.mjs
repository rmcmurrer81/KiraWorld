// Original display artwork and a declared fictional scenario, not mission telemetry.
export function createMarsDisplayData(geometry,presentation,viewport=null){
  const source=presentation?.source;
  if(presentation?.contract!=='bound_original_exterior_presentation_v1'||presentation.setting!=='mars_surface'||
     presentation.reason!=='explicit_original_mars_base_request'||!source||!geometry||
     source.research_packet_sha256!==geometry.research_packet_sha256||
     ![source.brief_sha256,source.request_sha256,source.research_packet_sha256].every(h=>typeof h==='string'&&/^[0-9a-f]{64}$/.test(h))||
     source.job_id!=='world_research_'+source.brief_sha256.slice(0,20))return null;
  const rooms=geometry.rooms.map(r=>({id:r.id,name:r.name,x:r.x,z:r.z,width:r.width,depth:r.depth,role:geometry.functional_program?.[r.id]||(r.id==='circulation'?'circulation':'room')}));
  const view=rooms.find(r=>r.role==='observation'&&viewport?.contract==='authored_observation_viewport_v1'&&viewport.room_id===r.id);
  return Object.freeze({contract:'fictional_mars_display_snapshot_v1',mode:'AUTHORED SCENARIO · NOT LIVE',
    site:'Fictional Mars surface habitat',sol:'042',localTime:'14:20',temperatureC:-58,pressurePa:650,
    dust:'Moderate',visibility:'Hazy horizon',pressureCycle:'Not simulated',power:'Not connected',
    observation:view?view.name:null,rooms:Object.freeze(rooms.map(Object.freeze)),
    references:Object.freeze(['https://science.nasa.gov/mars/facts/','https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html']),
    provenance:'Scenario readings are authored values. The plan comes from this exact layout; it is not a surveyed Martian site.'});
}

export function paintMarsDisplay(ctx,kind,data){
  if(!data||!['planet','weather','layout'].includes(kind))throw new TypeError('Unknown Mars display');
  const W=1024,H=512;
  ctx.fillStyle='#091b25';ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#d3a077';ctx.fillRect(0,0,10,H);
  ctx.fillStyle='#f0e8da';ctx.font='600 40px Segoe UI,sans-serif';
  ctx.fillText(kind==='layout'?(data.observation?'HABITAT / MARS VIEW':'HABITAT / ROOM PLAN'):kind==='weather'?'MARS / OUTSIDE CONDITIONS':'MARS / SURFACE HABITAT',36,59);
  ctx.fillStyle='#e6b888';ctx.font='24px monospace';ctx.fillText(data.mode,36,99);
  ctx.strokeStyle='#4b6570';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(36,118);ctx.lineTo(988,118);ctx.stroke();
  if(kind==='layout'){
    const rooms=data.rooms,minX=Math.min(...rooms.map(r=>r.x)),maxX=Math.max(...rooms.map(r=>r.x+r.width)),
      minZ=Math.min(...rooms.map(r=>r.z)),maxZ=Math.max(...rooms.map(r=>r.z+r.depth));
    const scale=Math.min(590/Math.max(1,maxX-minX),305/Math.max(1,maxZ-minZ));
    for(const r of rooms){
      const x=46+(r.x-minX)*scale,y=445-(r.z-minZ+r.depth)*scale;
      ctx.fillStyle=r.role==='observation'?'#80b6ac':r.role==='airlock'?'#9b774c':'#284453';
      ctx.fillRect(x+2,y+2,r.width*scale-4,r.depth*scale-4);
      ctx.strokeStyle='#c7d9d9';ctx.lineWidth=2;ctx.strokeRect(x,y,r.width*scale,r.depth*scale);
      ctx.fillStyle=r.role==='observation'?'#112a30':'#edf0e8';ctx.font='600 21px Segoe UI,sans-serif';
      const label=r.role==='observation'&&data.observation?'MARS VIEW':r.role.replaceAll('_',' ').toUpperCase();
      ctx.fillText(label,x+8,y+Math.min(r.depth*scale/2+8,35),Math.max(10,r.width*scale-16));
    }
    ctx.fillStyle='#bfe0d6';ctx.font='600 31px Segoe UI,sans-serif';ctx.fillText(data.observation?'OBSERVATION':'ROOM PLAN',665,180);
    ctx.fillStyle='#eff1e9';ctx.font='27px Segoe UI,sans-serif';
    ctx.fillText(data.observation?'Window to the surface':'No surface window',665,226);ctx.fillText(data.observation?'Via main circulation':'in this preview',665,268);
    ctx.fillStyle='#b6c8cc';ctx.font='23px Segoe UI,sans-serif';ctx.fillText('Plan: current layout',665,330);
    ctx.fillText('Not a terrain survey',665,366);
  }else{
    // Stylized planet icon; it deliberately contains no invented geographic labels.
    const cx=186,cy=290,r=120;
    ctx.fillStyle='#b76d43';ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle='#e3a372';ctx.lineWidth=2;
    for(const dy of [-55,0,55]){const a=Math.sqrt(r*r-dy*dy);ctx.beginPath();ctx.moveTo(cx-a,cy+dy);ctx.lineTo(cx+a,cy+dy);ctx.stroke();}
    ctx.beginPath();ctx.ellipse(cx,cy,58,r,0,0,Math.PI*2);ctx.stroke();
    ctx.fillStyle='#e8d4bd';ctx.font='21px monospace';ctx.fillText('ILLUSTRATED MARS',80,447);
    ctx.fillStyle='#f4efe5';ctx.font='600 42px Segoe UI,sans-serif';ctx.fillText('SOL '+data.sol+'  /  '+data.localTime,360,186);
    ctx.font='37px Segoe UI,sans-serif';ctx.fillText(data.temperatureC+' °C   /   '+data.pressurePa+' Pa',360,252);
    ctx.fillStyle='#c0d4d5';ctx.font='30px Segoe UI,sans-serif';ctx.fillText('Dust: '+data.dust,360,306);
    ctx.fillText('Visibility: '+data.visibility,360,352);
    ctx.fillStyle='#e6b888';ctx.font='23px Segoe UI,sans-serif';
    ctx.fillText(kind==='weather'?'Pressure cycling: NOT SIMULATED':'Cold, rocky world · thin atmosphere',360,409);
  }
  ctx.fillStyle='#aec6cd';ctx.font='22px monospace';ctx.fillText('FICTIONAL SITE  /  SNAPSHOT  /  NO LIVE SENSORS',36,489);
}
