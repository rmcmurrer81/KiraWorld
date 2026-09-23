    }else if(kind==='meal_station'){
      // Original static two-seat meal station, not a seated-avatar/comfort model.
      // The footprint includes the bench and table so collision is conservative.
      for(const x of [-.53,.53])for(const z of [-.565,-.215]){
        const foot=cylinder(group,x,.01,z,.035,.02,M.rubber);foot.name='meal_bench_foot';
        const leg=box(group,x,.205,z,.038,.37,.038,M.frame);leg.name='meal_bench_leg';
      }
      const support=box(group,0,.385,-.39,1.17,.055,.44,M.frame);support.name='meal_bench_support';
      for(const side of [-1,1]){
        softBox(group,'meal_seat_'+side,side*.295,.455,-.39,.555,.085,.42,.025,M.seat);
        softBox(group,'meal_back_'+side,side*.295,.765,-.585,.555,.47,.075,.025,M.seat);
        const post=box(group,side*.565,.675,-.595,.035,.68,.035,M.frame);post.name='meal_back_post';
      }
      softBox(group,'meal_bench_top_rail',0,1.026,-.595,1.18,.028,.042,.012,M.frame);
      // A broad floor plate and pedestal visibly support the table; the actual
      // underside remains open instead of filling the furniture with a box.
      softBox(group,'meal_table_floor_plate',0,.025,.30,.65,.05,.42,.022,M.frame);
      const pedestal=cylinder(group,0,.3725,.30,.057,.645,M.metal);pedestal.name='meal_table_pedestal';
      const crossbar=box(group,0,.7075,.25,.92,.038,.095,M.frame);crossbar.name='meal_table_crossbar';
      softBox(group,'meal_tabletop',0,.7425,.25,1.20,.045,.62,.018,M.ivory);
      group.userData.mealStationGeometry={contract:'authored_static_meal_station_v1',seatCount:2,
        seatSurfaceY:.4975,tableSurfaceY:.765,frontApproachZ:.63,
        collision:'conservative_whole_assembly_bounds',seatedAvatarInteraction:false,
        ergonomicOrSafetyValidation:false,foodOrApplianceSimulation:false};
