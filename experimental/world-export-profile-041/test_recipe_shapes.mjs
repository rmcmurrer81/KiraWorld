import fs from 'node:fs';import assert from 'node:assert/strict';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {exportSceneMetadata} from './candidate/tools/world_builder_engine/layout_package_assets/source/scene_metadata.mjs';
const shapes=[];
for(const variant of ['base','renamed','wider','translated']){
 const g=JSON.parse(fs.readFileSync(new URL('./fixtures/profile_'+variant+'.json',import.meta.url))),original=JSON.stringify(g);
 const doors=createDoorSystem(g),plan=buildRoomDressing(g,doors.assemblies()),walker=createWalkController(g,{extraColliders:plan.colliders});
 const metadata=exportSceneMetadata(g,plan,doors.definitions(),{sceneId:'shape_'+variant,sourceDigests:{geometry:'a'.repeat(64),dressing_recipe:'b'.repeat(64),door_controller:'c'.repeat(64)},doorInterlocks:doors.interlocks()});
 assert.equal(metadata.rooms.length,g.rooms.length);assert.equal(metadata.airlock_pairs.length,1);assert.ok(walker.snapshot().roomId);
 assert.equal(JSON.stringify(g),original);assert.ok(plan.enabled);assert.ok(metadata.colliders.every(c=>c.owner_node_id));
 shapes.push({variant,rooms:g.rooms.length,objects:plan.objects.length,architecture:plan.architecture.length,omitted_equipment:plan.omitted.length,
  metadata_nodes:metadata.nodes.length,colliders:metadata.colliders.length,door_pairs:metadata.airlock_pairs.length,
  real_glb_export:false,source_mutated:false,spawn_and_authored_clearance_checks:true});
}
const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/profile_base.json',import.meta.url)));
const malformed=structuredClone(fixture);malformed.portals[0].width=3.5;
assert.throws(()=>createDoorSystem(malformed));
const doors=createDoorSystem(fixture),plan=buildRoomDressing(fixture,doors.assemblies()),badPlan=structuredClone(plan);badPlan.colliders[0].max[0]+=.1;
assert.throws(()=>exportSceneMetadata(fixture,badPlan,doors.definitions(),{sceneId:'bad',sourceDigests:{geometry:'a'.repeat(64),dressing_recipe:'b'.repeat(64),door_controller:'c'.repeat(64)},doorInterlocks:doors.interlocks()}),/ownership/);
const report={status:'FOUR_RECOMPILED_SHAPES_PASS_AUTHORED_RECIPE_AND_METADATA_CHECKS',shapes,negative_cases:2,
 real_glb_exports:0,canvas_gpu_ui_models:0,limitations:['Pure recipe, spawn, collider ownership and metadata checks only.','Texture/GLB importer execution for these new shapes remains pending.','Omitted equipment is explicitly counted; no visual or owner approval.']};
fs.writeFileSync(new URL('./RECIPE-SHAPE-RESULT-'+(fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('RECIPE-SHAPE-RESULT')).length+1)+'.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report));
