// Original procedural meshes and textures. No external photographs/assets.
export function createDressingMaterials(THREE,plan,{canvasFactory=()=>typeof document==='undefined'?null:document.createElement('canvas')}={}){
  const cache=new Map();
  function texture(kind,accent='#8ba0a9'){
    const canvas=canvasFactory();if(!canvas)return null;
    canvas.width=canvas.height=512;const ctx=canvas.getContext('2d');
    if(kind==='screen'){
      ctx.fillStyle='#0d2029';ctx.fillRect(0,0,512,512);ctx.strokeStyle='#447984';ctx.lineWidth=2;
      for(let y=75;y<480;y+=62){ctx.beginPath();ctx.moveTo(24,y);ctx.lineTo(488,y);ctx.stroke();}
      ctx.fillStyle='#9ed0c3';ctx.font='22px monospace';ctx.fillText('SYSTEM OVERVIEW',25,40);
      ctx.strokeStyle='#84cdb3';ctx.lineWidth=5;ctx.beginPath();
      for(let x=20;x<495;x+=4){const y=220+Math.sin(x*.028)*35+Math.sin(x*.087)*13;if(x===20)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.stroke();
      for(let i=0;i<5;i++){ctx.fillStyle=i%2?'#638891':'#8bbaad';ctx.fillRect(30+i*95,330,55,38+(i%3)*19);}
    }else if(kind==='floor'||kind==='grate'){
      ctx.fillStyle=kind==='grate'?'#445159':'#666d6e';ctx.fillRect(0,0,512,512);
      ctx.strokeStyle=kind==='grate'?'#19272c':'#525a5c';ctx.lineWidth=kind==='grate'?12:3;
      for(let i=0;i<512;i+=kind==='grate'?32:64){ctx.beginPath();ctx.moveTo(i,0);ctx.lineTo(i,512);ctx.stroke();
        if(kind==='grate'){ctx.beginPath();ctx.moveTo(0,i);ctx.lineTo(512,i);ctx.stroke();}}
      if(kind==='floor'){ctx.fillStyle='#747b7b';for(let y=16;y<512;y+=32)for(let x=16;x<512;x+=32){ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill();}}
    }else{
      ctx.fillStyle='#c0c3bb';ctx.fillRect(0,0,512,512);ctx.fillStyle='#aeb4ae';ctx.fillRect(8,8,496,496);
      ctx.fillStyle='#ccd0c8';ctx.fillRect(13,13,486,486);ctx.strokeStyle='#747f7c';ctx.lineWidth=3;ctx.strokeRect(9,9,494,494);
      ctx.fillStyle='#667371';for(const x of [26,486])for(const y of [26,486]){ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill();}
      ctx.fillStyle=accent;ctx.fillRect(18,469,476,9);
    }
    const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;map.wrapS=map.wrapT=THREE.RepeatWrapping;return map;
  }
  function mat(name,color,roughness=.55,metalness=.2,extra={}){
    if(!cache.has(name))cache.set(name,new THREE.MeshStandardMaterial({color,roughness,metalness,...extra}));return cache.get(name);
  }
  const basic={
    frame:mat('frame',0x42505a,.39,.73),metal:mat('metal',0xa9b1b2,.4,.7),ivory:mat('ivory',0xd4d7ce,.62,.15),
    dark:mat('dark',0x263139,.64,.28),rubber:mat('rubber',0x17222a,.91,.01),wood:mat('wood',0xad8d68,.79,.01),
    cloth:mat('cloth',0xc3c5b7,.96,0),seat:mat('seat',0x536875,.94,0),glass:mat('glass',0x8ec5c8,.2,.25,{transparent:true,opacity:.28,depthWrite:false}),
    green:mat('green',0x538b55,.85,0),leaf:mat('leaf',0x80a760,.92,0),soil:mat('soil',0x453d31,.99,0),
    amber:mat('amber',0xb79755,.6,.3),red:mat('red',0x986253,.68,.1),
    indicator:mat('indicator',0x83c6ac,.38,.1,{emissive:0x276f53,emissiveIntensity:.7}),
    screen:mat('screen',0xa4d6d8,.32,.2,{map:texture('screen'),emissive:0x2e646f,emissiveIntensity:.32}),
    lamp:mat('lamp',0xfff1d2,.35,.06,{emissive:0xffe1a2,emissiveIntensity:1.8})
  };
  function surface(role,roomId){
    const style=plan.roomStyles[roomId];
    if(role==='wall')return mat('basewall',0xc6cdc8,.84,.1);
    if(role==='ceiling')return mat('ceiling',0xc3c9c4,.88,.1);
    if(role==='floor')return mat('floor_'+(roomId||''),style?.floor||0x5a666b,.85,.12,{map:texture(style?.role==='airlock'?'grate':'floor')});
    return mat('locked',0x55636b,.9,.1);
  }
  function wallPanel(roomId,width,height){
    const map=texture('panel',plan.roomStyles[roomId]?.accent);if(map)map.repeat.set(Math.max(1,width/.95),Math.max(1,height/1.05));
    return new THREE.MeshStandardMaterial({color:0xffffff,map,roughness:.72,metalness:.17,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});
  }
  return {basic,surface,wallPanel,canvasFactory};
}

export function addRoomDressing(THREE,scene,geometry,plan,materials){
  const M=materials.basic,equipmentGroups=new Map(),geometryCache=new Map();
  function cached(key,make){if(!geometryCache.has(key))geometryCache.set(key,make());return geometryCache.get(key);}
  function box(group,x,y,z,w,h,d,material=M.metal){
    const geo=cached('b:'+w+','+h+','+d,()=>new THREE.BoxGeometry(w,h,d));const mesh=new THREE.Mesh(geo,material);mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;group.add(mesh);return mesh;
  }
  function cylinder(group,x,y,z,r,h,material=M.metal,rx=0,rz=0){
    const mesh=new THREE.Mesh(cached('c:'+r+','+h,()=>new THREE.CylinderGeometry(r,r,h,12)),material);mesh.position.set(x,y,z);mesh.rotation.set(rx,0,rz);mesh.castShadow=true;group.add(mesh);return mesh;
  }
  function sphere(group,x,y,z,r,material=M.ivory,scale=[1,1,1]){
    const mesh=new THREE.Mesh(cached('s:'+r,()=>new THREE.SphereGeometry(r,12,8)),material);mesh.position.set(x,y,z);mesh.scale.set(...scale);mesh.castShadow=true;group.add(mesh);return mesh;
  }
  function torus(group,x,y,z,r,t,material=M.metal,rx=0,ry=0){
    const mesh=new THREE.Mesh(cached('t:'+r+','+t,()=>new THREE.TorusGeometry(r,t,8,18)),material);mesh.position.set(x,y,z);mesh.rotation.set(rx,ry,0);group.add(mesh);return mesh;
  }
  // Rounded, authored soft forms. Geometry only: no cloth/contact simulation.
  function softBox(group,name,x,y,z,w,h,d,r,material){
    const key='soft:'+w+','+h+','+d+','+r;
    const geo=cached(key,()=>{
      const g=new THREE.BoxGeometry(w,h,d,14,4,8),p=g.attributes.position,n=g.attributes.normal;
      const half=[w/2,h/2,d/2],core=half.map(v=>Math.max(0,v-r));
      for(let i=0;i<p.count;i++){
        const a=[p.getX(i),p.getY(i),p.getZ(i)],q=a.map((v,j)=>Math.max(-core[j],Math.min(core[j],v))),delta=a.map((v,j)=>v-q[j]);
        const length=Math.hypot(...delta);for(let j=0;j<3;j++)delta[j]/=length;
        p.setXYZ(i,...q.map((v,j)=>v+delta[j]*r));n.setXYZ(i,...delta);
      }
      g.computeBoundingBox();return g;
    });
    const mesh=new THREE.Mesh(geo,material);mesh.name=name;mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;group.add(mesh);return mesh;
  }
  function blanket(group,name,x,y,z,w,d){
    // A real two-sided draped surface with a rolled hem. The folds stay inside
    // the mattress footprint and existing conservative bunk collision volume.
    const nx=24,nz=16,positions=[],uv=[],index=[];
    for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){
      const u=i/nx,v=j/nz,edge=Math.pow(Math.max(0,(Math.abs(2*v-1)-.88)/.12),2);
      const fold=.010*Math.sin(u*Math.PI*8+v*.6)*Math.sin(v*Math.PI);
      positions.push((u-.5)*w,fold-.07*edge,(v-.5)*d);uv.push(u,v);
    }
    for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i,b=a+1,c=a+nx+1,e=c+1;index.push(a,c,b,b,c,e);}
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geo.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geo.setIndex(index);geo.computeVertexNormals();geo.computeBoundingBox();
    const material=M.seat.clone();material.side=THREE.DoubleSide;
    const mesh=new THREE.Mesh(geo,material);mesh.name=name;mesh.position.set(x,y,z);mesh.castShadow=mesh.receiveShadow=true;group.add(mesh);
    softBox(group,name+'_folded_hem',x-w/2+.018,y+.018,z,.038,.038,d-.035,.017,M.seat);
  }
  function legs(group,w,d,h,material=M.frame){for(const x of [-w/2+.07,w/2-.07])for(const z of [-d/2+.07,d/2-.07])box(group,x,h/2,z,.055,h,.055,material);}
  function cabinet(group,w,h,d){
    const bodyDepth=d-.08;box(group,0,h/2,0,w,h,bodyDepth,M.frame);
    for(let i=0;i<3;i++){const y=.12+(h-.12)*(i+.5)/3;box(group,0,y,bodyDepth/2+.008,w-.075,(h-.18)/3,.016,M.ivory);box(group,w*.3,y,bodyDepth/2+.025,.09,.018,.025,M.dark);}
  }
  function smallScreen(group,x,y,z,w,h){box(group,x,y,z,w+.045,h+.045,.06,M.rubber);box(group,x,y,z+.033,w,h,.007,M.screen);}
  function chair(group,x,z){
    cylinder(group,x,.26,z,.055,.45,M.frame);box(group,x,.49,z,.44,.085,.43,M.seat);box(group,x,.74,z+.2,.43,.45,.065,M.seat);
    for(let i=0;i<4;i++){const a=i*Math.PI/2,c=Math.cos(a),s=Math.sin(a);const leg=box(group,x+c*.12,.065,z+s*.12,.24,.035,.035,M.frame);leg.rotation.y=-a;sphere(group,x+c*.22,.035,z+s*.22,.033,M.rubber);}
  }
  for(const object of plan.objects){
    const [w,h,d]=object.localSize,group=new THREE.Group();group.name=object.id;group.position.set(object.center[0],object.center[1]-h/2,object.center[2]);group.rotation.y=object.yaw;
    const kind=object.kind;
    if(kind==='eva_lockers'){
      box(group,0,h/2,-d/2+.035,w,h,.06,M.dark);for(const x of [-w/2+.025,0,w/2-.025])box(group,x,h/2,0,.045,h,d,M.frame);
      box(group,0,.075,0,w,.12,d,M.frame);box(group,0,h-.04,0,w,.07,d,M.frame);
      for(const x of [-w*.245,w*.245]){
        sphere(group,x,1.78,.02,.155,M.ivory);sphere(group,x,1.8,.128,.12,M.rubber,[1,.68,.5]);torus(group,x,1.615,.02,.09,.019,M.metal,Math.PI/2);
        sphere(group,x,1.31,0,.185,M.ivory,[1.04,1.48,.72]);box(group,x,1.32,.135,.22,.19,.07,M.frame);
        for(const side of [-1,1]){cylinder(group,x+side*.205,1.25,0,.05,.4,M.ivory,0,side*.13);cylinder(group,x+side*.09,.79,0,.071,.56,M.ivory);box(group,x+side*.09,.455,.055,.15,.11,.26,M.rubber);}
      }
    }else if(kind==='gear_bench'){
      legs(group,w-.1,d-.08,.43);box(group,0,.46,0,w,.085,d,M.wood);box(group,0,.14,-.04,w-.15,.04,d-.14,M.frame);
      for(const x of [-.32,-.1,.12,.34])box(group,x,.23,.03,.13,.13,.25,M.rubber);
    }else if(kind==='hose_station'){
      box(group,0,.82,-d/2+.035,w,1.5,.065,M.frame);
      for(let i=0;i<3;i++)torus(group,0,.4+i*.35,.01,.185,.022,M.rubber);
      for(const x of [-.2,.2]){cylinder(group,x,1.42,.025,.036,.17,M.metal);box(group,x,1.5,.08,.11,.045,.045,M.amber);}
    }else if(kind==='airlock_control'){
      box(group,0,h/2,-.03,w,h,d*.7,M.frame);smallScreen(group,0,1.28,d*.29,w*.78,.38);
      for(let i=0;i<4;i++){cylinder(group,-w*.29+i*w*.19,.86,d*.41,.027,.02,i===0?M.red:M.indicator,Math.PI/2);}
      box(group,0,.31,d*.31,w*.7,.23,.035,M.metal);for(let y=.22;y<.4;y+=.05)box(group,0,y,d*.34,w*.6,.011,.008,M.dark);
    }else if(kind==='filter_cylinders'){
      box(group,0,.045,0,w,.07,d,M.frame);for(const x of [-w*.235,w*.235]){
        cylinder(group,x,.79,0,.13,1.38,M.ivory);for(const y of [.26,1.25])torus(group,x,y,0,.133,.014,M.frame,Math.PI/2);
        cylinder(group,x,1.53,0,.035,.12,M.metal);box(group,x,1.6,.025,.13,.04,.075,M.amber);
      }
    }else if(kind==='operations_console'){
      const dd=d*.51,zz=-d*.22;for(const x of [-w/2+.1,w/2-.1])for(const z of [zz-dd/2+.07,zz+dd/2-.07])box(group,x,.375,z,.055,.75,.055,M.frame);box(group,0,.78,zz,w-.04,.075,dd,M.metal);
      box(group,-w*.38,.37,zz,w*.2,.66,dd-.07,M.frame);
      for(const x of [-w*.255,w*.255]){box(group,x,.98,-d*.39,.065,.35,.065,M.frame);smallScreen(group,x,1.23,-d*.35,w*.4,.38);}
      box(group,0,.835,-d*.065,w*.58,.026,.2,M.rubber);chair(group,0,d*.24);
    }else if(kind==='server_rack'){
      box(group,0,h/2,-d*.4,w,h,.08,M.frame);for(const x of [-w/2+.03,w/2-.03])box(group,x,h/2,0,.06,h,d,M.frame);
      for(let i=0;i<7;i++){const y=.16+i*.275;box(group,0,y,0,w-.1,.225,d-.06,M.dark);for(let v=0;v<4;v++)box(group,-w*.28+v*.035,y,d*.465,.012,.11,.008,M.frame);box(group,w*.27,y,d*.47,.047,.016,.01,i%2?M.indicator:M.amber);}
      box(group,0,h-.025,0,w,.04,d,M.frame);
    }else if(kind==='bunk'){
      // Dimensions use the existing 2.08m x .90m x 2.12m authored assembly.
      // These details are not a safety-standard, comfort or structural claim.
      for(const x of [-w/2+.055,w/2-.055])for(const z of [-d/2+.05,d/2-.05])box(group,x,h/2,z,.06,h,.06,M.frame);
      for(const [berth,y] of [['lower',.34],['upper',1.27]]){
        const deck=box(group,0,y,0,w-.05,.075,d-.04,M.frame);deck.name='bunk_'+berth+'_deck';
        const mattressTop=y+.15;
        softBox(group,'bunk_'+berth+'_mattress',0,y+.095,0,w-.16,.11,d-.12,.032,M.cloth);
        softBox(group,'bunk_'+berth+'_pillow',-w*.32,mattressTop+.048,0,.42,.096,d-.22,.046,M.ivory);
        blanket(group,'bunk_'+berth+'_blanket',w*.11,mattressTop+.018,.015,w*.60,d-.06);
      }
      // The upper front guard stops before the ladder; its open access bay is
      // dimensioned separately so decorative rails cannot silently seal it.
      const guardLeft=-w/2+.11,guardRight=w*.20,guardBottom=1.27,guardTop=1.78;
      for(const x of [guardLeft,guardRight]){const post=box(group,x,(guardBottom+guardTop)/2,d/2-.055,.03,guardTop-guardBottom,.03,M.metal);post.name='bunk_upper_guard_post';}
      for(const y of [1.57,guardTop]){const rail=cylinder(group,(guardLeft+guardRight)/2,y,d/2-.055,.016,guardRight-guardLeft,M.metal,0,Math.PI/2);rail.name='bunk_upper_front_guard';}
      for(const x of [-w/2+.055,w/2-.055]){const rail=cylinder(group,x,guardTop,0,.016,d-.12,M.metal,Math.PI/2);rail.name='bunk_upper_end_guard';}
      for(const x of [w*.27,w*.43]){const stile=box(group,x,.92,d/2-.025,.032,1.84,.04,M.metal);stile.name='bunk_ladder_stile';}
      for(let i=0;i<5;i++){const rung=box(group,w*.35,.22+i*.34,d/2-.022,w*.18,.028,.035,M.metal);rung.name='bunk_ladder_rung';}
      group.userData.bunkGeometry={contract:'authored_bunk_detail_v1',upperMattressTop:1.42,guardTop,
        frontAccessX:[guardRight+.016,w/2-.085],ladderStileX:[w*.27,w*.43],
        collision:'unchanged_conservative_assembly_bounds',physicsOrSafetyValidation:false};
    }else if(kind==='galley'){
      cabinet(group,w,.79,d-.035);box(group,0,.83,0,w,.055,d,M.metal);box(group,-w*.22,.862,.035,w*.32,.009,d*.52,M.dark);
      cylinder(group,-w*.22,.95,-d*.15,.012,.2,M.metal);torus(group,-w*.22,1.025,-d*.08,.057,.009,M.metal,0,Math.PI/2);
      box(group,0,1.48,-d*.15,w,.43,d*.65,M.ivory);box(group,0,1.48,d*.18,.012,.4,.014,M.frame);
      for(const x of [-w*.06,w*.06])box(group,x,1.47,d*.19,.02,.15,.025,M.dark);
    }else if(kind==='personal_storage'||kind==='sample_storage'){
      cabinet(group,w,h-.025,d-.035);if(kind==='sample_storage')for(let y=.2;y<h-.1;y+=.32)box(group,-w*.28,y,d/2-.004,.12,.065,.008,M.amber);
    }else if(kind==='glovebox'){
      cabinet(group,w,.79,d-.02);box(group,0,.85,0,w,.075,d,M.metal);
      const bottom=.92,top=1.76;
      for(const x of [-w*.47,w*.47])for(const z of [-d*.43,d*.43])box(group,x,(bottom+top)/2,z,.04,top-bottom,.04,M.frame);
      box(group,0,top,0,w,.045,d,M.frame);box(group,0,1.34,-d*.445,w-.075,.79,.025,M.ivory);box(group,0,1.34,d*.445,w-.075,.76,.012,M.glass);
      for(const x of [-w*.23,w*.23]){torus(group,x,1.25,d*.465,.10,.018,M.rubber);cylinder(group,x,1.23,d*.32,.058,.2,M.rubber,Math.PI/2);sphere(group,x,1.18,d*.16,.076,M.rubber,[.82,1,.82]);}
      box(group,w*.3,1.85,0,w*.3,.07,d*.52,M.frame);smallScreen(group,w*.3,1.845,d*.28,w*.22,.045);
    }else if(kind==='science_bench'){
      legs(group,w-.1,d-.1,.79);box(group,0,.82,0,w,.06,d,M.ivory);box(group,-w*.31,.45,0,w*.27,.66,d-.08,M.frame);
      const x=w*.21;box(group,x,.88,.02,.27,.035,.26,M.frame);cylinder(group,x,1.055,-.065,.034,.33,M.metal);box(group,x,1.12,.02,.24,.04,.2,M.dark);
      const tube=cylinder(group,x,1.28,.055,.03,.24,M.ivory);tube.rotation.x=-.3;cylinder(group,x,1.4,.019,.045,.055,M.rubber);
      for(let i=0;i<3;i++){const bx=-w*.25+i*.16;box(group,bx,.89,.035,.12,.06,.17,M.amber);cylinder(group,bx,.98,.035,.023,.13,M.glass);}
    }else if(kind==='observation_seat'){
      legs(group,w-.12,d-.1,.28);box(group,0,.35,0,w,.17,d,M.frame);box(group,0,.83,-d*.41,w,.45,.11,M.seat);
      for(const x of [-w*.25,w*.25])box(group,x,.5,.025,w*.44,.13,d*.75,M.seat);for(const x of [-w*.46,w*.46])box(group,x,.63,.01,.085,.31,d*.8,M.seat);
    }else if(kind==='growing_rack'){
      for(const x of [-w*.47,w*.47])for(const z of [-d*.45,d*.45])box(group,x,h/2,z,.035,h,.035,M.frame);
      for(const y of [.21,.76,1.31]){
        box(group,0,y,0,w,.04,d,M.metal);box(group,0,y+.065,0,w-.09,.085,d-.08,M.ivory);box(group,0,y+.113,0,w-.14,.012,d-.13,M.soil);
        for(let i=0;i<4;i++){const x=-w*.33+i*w*.22;cylinder(group,x,y+.22,0,.008,.2,M.green);for(const side of [-1,1]){const leaf=sphere(group,x+side*.06,y+.27,.025,.08,M.leaf,[.75,.34,1.1]);leaf.rotation.z=side*.4;}}
        box(group,0,y+.43,-d*.04,w-.12,.027,.07,M.lamp);
      }
    }
    scene.add(group);equipmentGroups.set(object.id,group);
  }
  for(const item of plan.architecture){
    const group=new THREE.Group();group.position.set(...item.center);group.name=item.id;
    box(group,0,0,0,...item.size,item.kind==='luminaire'?M.lamp:M.frame);scene.add(group);
  }
  for(const light of plan.lights){const point=new THREE.PointLight(light.color,light.intensity,light.distance,2);point.position.set(...light.position);scene.add(point);}
  // Apply panels to each room's inward wall face. Shared walls get separate
  // inner faces, avoiding conflicting materials on duplicate boundary boxes.
  for(const primitive of geometry.primitives){
    if(primitive.role!=='wall')continue;
    const room=geometry.rooms.find(r=>plan.roomStyles[r.id]&&primitive.id.startsWith(r.id+'_'));if(!room)continue;
    const side=primitive.id.slice(room.id.length+1).split('_')[0];
    const normal=side==='west'?[1,0,0]:side==='east'?[-1,0,0]:side==='south'?[0,0,1]:side==='north'?[0,0,-1]:null;if(!normal)continue;
    const axis=normal[0]?0:2,w=primitive.size[axis===0?2:0],h=primitive.size[1];
    const panel=new THREE.Mesh(new THREE.PlaneGeometry(w,h),materials.wallPanel(room.id,w,h));
    panel.position.set(...primitive.position);panel.position.setComponent(axis,panel.position.getComponent(axis)+normal[axis]*(primitive.size[axis]/2+.0008));
    panel.rotation.y=normal[0]===1?Math.PI/2:normal[0]===-1?-Math.PI/2:normal[2]===-1?Math.PI:0;panel.receiveShadow=true;scene.add(panel);
  }
  for(const sign of plan.signs){
    const plaque=new THREE.Group();plaque.name=sign.id;plaque.position.set(...sign.position);box(plaque,0,0,0,...sign.size,M.frame);
    const canvas=materials.canvasFactory();
    if(canvas){canvas.width=768;canvas.height=256;const ctx=canvas.getContext('2d');ctx.fillStyle='#283b43';ctx.fillRect(0,0,768,256);ctx.fillStyle=plan.roomStyles[sign.room_id].accent;ctx.fillRect(0,0,22,256);ctx.fillStyle='#e2e8df';ctx.font='600 42px Segoe UI,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(sign.text.slice(0,38),395,135,690);
      const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;const plane=new THREE.Mesh(new THREE.PlaneGeometry(.48,.165),new THREE.MeshStandardMaterial({map,roughness:.7,metalness:.1}));
      plane.position.set(sign.normal[0]*.016,0,sign.normal[2]*.016);plane.rotation.y=sign.normal[0]===1?Math.PI/2:sign.normal[0]===-1?-Math.PI/2:sign.normal[2]===-1?Math.PI:0;plaque.add(plane);
    }
    scene.add(plaque);
  }
  return {equipmentGroups,meshCount:[...scene.children].reduce((sum,child)=>{child.traverse(node=>{if(node.isMesh)sum++;});return sum;},0)};
}
