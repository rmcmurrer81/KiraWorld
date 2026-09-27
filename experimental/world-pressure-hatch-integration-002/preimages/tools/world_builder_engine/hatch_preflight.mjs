import {readFileSync} from 'node:fs';
import {createDoorSystem,createWalkController} from './walk_controller.mjs';
import {planHatchArchitecture} from './pressure_hatch_architecture.mjs';
import {buildRoomDressing} from './layout_package_assets/source/room_dressing_plan.mjs';
if(process.argv.length!==3)throw new Error('Expected one exact geometry path');
const geometry=JSON.parse(readFileSync(process.argv[2],'utf8').replace(/^\uFEFF/,''));
const doors=createDoorSystem(geometry),dressing=buildRoomDressing(geometry,createDoorSystem(geometry,{hatchGeometry:false}).assemblies());
createWalkController(geometry,{extraColliders:dressing.colliders});
const architecture=planHatchArchitecture(geometry,doors.hatchPlans());
process.stdout.write(JSON.stringify({status:'PASS',contract:'paired_hatch_geometry_preflight_v1',hatches:doors.hatchPlans().length,
 colliders:doors.colliders().length,architecturalCutouts:Object.keys(architecture.modifications).length,sourceGeometryChanged:false,
 retainedDressingObjects:dressing.objects.length,retainedSigns:dressing.signs.length,modelJobs:0,rendererCalls:0}));
