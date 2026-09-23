    }else if(kind==='galley'){
      // Original static food-preparation fixtures inside the existing galley
      // volume. Appliances stay closed; no water, heating or refrigeration is
      // simulated. The sink is a cavity, not a dark decal over a solid slab.
      const part=(name,x,y,z,bw,bh,bd,material=M.metal)=>{
        const mesh=box(group,x,y,z,bw,bh,bd,material);mesh.name='galley_'+name;return mesh;
      };
      const front=d/2-.055,back=-d/2+.025,counterTop=.89;
      part('plinth',0,.055,-.015,w-.07,.11,d-.09,M.dark);
      part('base_floor',0,.125,-.015,w-.055,.04,d-.07,M.frame);
      part('base_back',0,.49,back,w-.035,.69,.025,M.frame);
      for(const x of [-w/2+.023,w/2-.023])part('side_panel',x,.49,-.015,.035,.70,d-.06,M.ivory);
      // Left utility cupboard, narrow drawers and a distinct sealed food-cold
      // compartment. A gasket, pull and toe grille provide physical cues.
      part('utility_door',-w*.255,.46,front,w*.465,.65,.027,M.ivory);
      part('utility_pull',-w*.085,.49,front+.027,.022,.18,.023,M.frame);
      for(let i=0;i<3;i++){
        part('drawer_'+i,w*.065,.248+i*.213,front,w*.14,.196,.027,M.ivory);
        part('drawer_pull_'+i,w*.065,.278+i*.213,front+.024,w*.09,.017,.022,M.frame);
      }
      const coldX=w*.328,coldW=w*.302;
      part('cold_gasket',coldX,.461,front-.002,coldW+.02,.682,.02,M.rubber);
      part('cold_door',coldX,.461,front+.012,coldW,.656,.025,M.metal);
      part('cold_pull',coldX+coldW*.32,.53,front+.039,.023,.265,.024,M.frame);
      for(let i=0;i<4;i++)part('cold_vent_'+i,coldX,.039+i*.019,front-.015,coldW-.055,.007,.012,M.metal);
      // Build the counter as four strips around the basin opening. There is
      // deliberately no full-width solid countertop crossing the sink mouth.
      const sinkX=-w*.25,sinkZ=.04,sinkW=.46,sinkD=.42;
      const sx0=sinkX-sinkW/2,sx1=sinkX+sinkW/2,sz0=sinkZ-sinkD/2,sz1=sinkZ+sinkD/2;
      part('counter_left',(-w/2+sx0)/2,.87,0,sx0+w/2,.04,d,M.metal);
      part('counter_prep',(sx1+w/2)/2,.87,0,w/2-sx1,.04,d,M.metal);
      part('counter_rear',sinkX,.87,(-d/2+sz0)/2,sinkW,.04,sz0+d/2,M.metal);
      part('counter_front',sinkX,.87,(sz1+d/2)/2,sinkW,.04,d/2-sz1,M.metal);
      const basinFloor=.689,wallTop=.89,wallBottom=.684;
      part('sink_bottom',sinkX,basinFloor-.006,sinkZ,sinkW,.012,sinkD,M.metal);
      for(const x of [sx0+.006,sx1-.006])part('sink_side',x,(wallTop+wallBottom)/2,sinkZ,.012,wallTop-wallBottom,sinkD,M.metal);
      for(const z of [sz0+.006,sz1-.006])part('sink_end',sinkX,(wallTop+wallBottom)/2,z,sinkW-.024,wallTop-wallBottom,.012,M.metal);
      for(const x of [sx0,sx1])part('sink_rim_side',x,.891,sinkZ,.022,.012,sinkD+.022,M.metal);
      for(const z of [sz0,sz1])part('sink_rim_end',sinkX,.891,z,sinkW-.022,.012,.022,M.metal);
      const drain=cylinder(group,sinkX,basinFloor+.003,sinkZ,.024,.006,M.dark);drain.name='galley_sink_drain';
      for(const x of [-.012,0,.012])part('drain_slot',sinkX+x,basinFloor+.0065,sinkZ,.003,.001,.025,M.metal);
      // One continuous curved spout reaches the open basin. TubeGeometry keeps
      // the bend volumetric, including when imported through the GLB path.
      const path=new THREE.CatmullRomCurve3([
        new THREE.Vector3(sinkX,.90,sz0-.055),new THREE.Vector3(sinkX,1.115,sz0-.055),
        new THREE.Vector3(sinkX,1.185,sz0+.025),new THREE.Vector3(sinkX,1.115,sinkZ-.025)
      ]);
      const spout=new THREE.Mesh(new THREE.TubeGeometry(path,24,.012,10,false),M.metal);spout.name='galley_faucet_spout';spout.castShadow=true;group.add(spout);
      const base=cylinder(group,sinkX,.902,sz0-.055,.031,.024,M.frame);base.name='galley_faucet_base';
      const valve=cylinder(group,sx1+.062,.914,sz0-.045,.021,.049,M.metal);valve.name='galley_faucet_valve';
      part('faucet_lever',sx1+.062,.943,sz0-.020,.016,.014,.076,M.frame);
      part('backsplash',0,1.055,back,w-.018,.33,.028,M.ivory);
      // Upper pantry and enclosed warming appliance share a supported carcass.
      // The appliance has a real cavity/turntable behind a transparent door.
      const upperBottom=1.28,upperTop=1.71,upperBack=-d/2+.018,upperFront=.135;
      part('upper_back',0,(upperBottom+upperTop)/2,upperBack,w-.03,upperTop-upperBottom,.025,M.frame);
      part('upper_shelf',0,upperBottom+.016,(upperBack+upperFront)/2,w-.03,.032,upperFront-upperBack,M.frame);
      part('upper_roof',0,upperTop-.018,(upperBack+upperFront)/2,w-.03,.036,upperFront-upperBack,M.ivory);
      for(const x of [-w/2+.025,-w*.115,w/2-.025])part('upper_side',x,(upperBottom+upperTop)/2,(upperBack+upperFront)/2,.026,upperTop-upperBottom,upperFront-upperBack,M.ivory);
      const pantryW=w*.335,pantryX=-w*.305;
      part('pantry_gasket',pantryX,1.495,upperFront-.012,pantryW+.025,.38,.022,M.rubber);
      part('pantry_door',pantryX,1.495,upperFront+.003,pantryW,.357,.022,M.ivory);
      part('pantry_latch',pantryX+pantryW*.34,1.47,upperFront+.029,.025,.12,.025,M.frame);
      for(const y of [1.365,1.625])part('pantry_hinge',pantryX-pantryW*.49,y,upperFront+.019,.025,.046,.025,M.metal);
      const ovenX=w*.19,ovenW=w*.57,windowX=ovenX-.054,windowW=ovenW-.23,windowH=.263;
      const doorY=1.493,doorZ=upperFront+.027;
      for(const y of [doorY-.157,doorY+.157])part('warming_door_horizontal',ovenX,y,doorZ,ovenW,.044,.031,M.dark);
      for(const x of [ovenX-ovenW/2+.022,ovenX+ovenW/2-.022])part('warming_door_side',x,doorY,doorZ,.044,.27,.031,M.dark);
      part('warming_controls',ovenX+ovenW/2-.089,doorY,doorZ,.09,.272,.031,M.metal);
      part('warming_window',windowX,doorY,doorZ+.002,windowW,windowH,.008,M.glass);
      part('warming_handle',windowX+windowW/2+.021,doorY,doorZ+.041,.022,.264,.025,M.ivory);
      for(const y of [doorY-.10,doorY+.10])part('warming_handle_mount',windowX+windowW/2+.021,y,doorZ+.020,.022,.022,.028,M.ivory);
      for(const y of [doorY-.069,doorY+.066]){
        const dial=cylinder(group,ovenX+ovenW/2-.088,y,doorZ+.025,.027,.024,M.frame,Math.PI/2);dial.name='galley_warming_dial';
        part('warming_dial_marker',ovenX+ovenW/2-.088,y+.013,doorZ+.039,.004,.012,.004,M.ivory);
      }
      const tray=cylinder(group,windowX,upperBottom+.046,-.05,.128,.017,M.ivory);tray.name='galley_warming_tray';
      for(let i=0;i<5;i++)part('warming_vent_'+i,ovenX-.22+i*.055,upperTop-.052,upperFront+.011,.034,.008,.009,M.dark);
      part('task_strip',0,upperBottom-.009,-.045,w-.16,.013,.028,M.lamp);
      group.userData.galleyGeometry={contract:'authored_galley_detail_v1',counterTop,
        basin:{openingMin:[sx0+.012,sz0+.012],openingMax:[sx1-.012,sz1-.012],floorY:basinFloor,depth:counterTop-basinFloor},
        prepSurface:{min:[sx1+.012,-d/2],max:[w/2,d/2]},
        staticComponents:['recessed_sink','curved_faucet','utility_cupboard','drawers','cold_food_compartment','pantry','warming_appliance'],
        collision:'unchanged_conservative_assembly_bounds',applianceSimulation:false,pressureOrLifeSupportClaim:false};
