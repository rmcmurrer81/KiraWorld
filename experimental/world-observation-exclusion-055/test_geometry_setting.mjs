import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import * as THREE from './candidate/tools/world_builder_engine/layout_package_assets/vendor/three/build/three.module.js';
import * as before from '../world-observation-viewport-053/candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import * as after from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs';
import {buildRoomDressing} from './candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_plan.mjs';
import {createDoorSystem} from './candidate/tools/world_builder_engine/layout_package_assets/source/walk_controller.mjs';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const fixtures=JSON.parse(fs.readFileSync(new URL('./fixtures/supported-layouts.json',import.meta.url))),cases=JSON.parse(fs.readFileSync(new URL('./fixtures/setting-cases.json',import.meta.url)));
function signature(root){const rows=[];root.traverse(o=>{if(o.isMesh)rows.push({name:o.name,position:o.position.toArray(),attrs:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,a])=>[k,Array.from(a.array)])),indices:Array.from(o.geometry.index.array),material:[o.material.color.toArray(),o.material.roughness,o.material.metalness,o.material.opacity,o.material.transparent,o.material.side]});});return sha(JSON.stringify(rows));}
const result=[];
for(const f of fixtures){
 const g=f.geometry,original=JSON.stringify(g),d=createDoorSystem(g),plan=buildRoomDressing(g,d.assemblies()),vp=after.planObservationViewport(g,plan),oldVp=before.planObservationViewport(g,plan);assert.ok(vp);assert.deepEqual(vp,oldVp);
 const oldScene=new THREE.Scene(),newScene=new THREE.Scene();before.addObservationExterior(THREE,oldScene,oldVp);after.addObservationExterior(THREE,newScene,vp,f.presentation,g);
 assert.equal(oldScene.children.length,1);const expected=f.presentation.setting==='mars_surface';assert.equal(newScene.children.length,expected?1:0);
 if(expected)assert.equal(signature(oldScene),signature(newScene));
 const p=g.primitives.find(p=>p.id===vp.wall_id),oldM=before.createDressingMaterials(THREE,plan,{canvasFactory:()=>null}),newM=after.createDressingMaterials(THREE,plan,{canvasFactory:()=>null});
 assert.equal(signature(before.createStructuralPrimitive(THREE,p,oldM.basic.ivory,oldVp,oldM)),signature(after.createStructuralPrimitive(THREE,p,newM.basic.ivory,vp,newM)));
 assert.equal(JSON.stringify(g),original);result.push({case:f.title,export_profile_eligible:true,before_rusty_exterior:true,after_rusty_exterior:expected,aperture_and_safety_unchanged:true});
}
const g=fixtures[0].geometry,d=createDoorSystem(g),plan=buildRoomDressing(g,d.assemblies()),vp=after.planObservationViewport(g,plan);
for(const row of cases){const geometry={...g,research_packet_sha256:row.packet_sha256},scene=new THREE.Scene();after.addObservationExterior(THREE,scene,vp,row.presentation,geometry);assert.equal(scene.children.length,row.presentation.setting==='mars_surface'?1:0);}
for(const name of ['missing','wrong_packet','wrong_job','wrong_brief_digest','wrong_contract','claimed_without_authority']){
 const p=structuredClone(fixtures[0].presentation);let input=p;
 if(name==='missing')input=null;if(name==='wrong_packet')p.source.research_packet_sha256='0'.repeat(64);if(name==='wrong_job')p.source.job_id='world_research_other';if(name==='wrong_brief_digest')p.source.brief_sha256='not-a-hash';if(name==='wrong_contract')p.contract='unknown';if(name==='claimed_without_authority')p.reason='guessed_from_room_label';
 const scene=new THREE.Scene();after.addObservationExterior(THREE,scene,vp,input,g);assert.equal(scene.children.length,0);result.push({case:name,exterior_absent:true});
}
const viewer=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/viewer.mjs',import.meta.url),'utf8'),shared=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/layout_package_assets/source/room_dressing_render.mjs',import.meta.url),'utf8').replaceAll('export function ','function ').trim();
assert.equal(viewer.split(shared).length-1,1);assert.ok(viewer.includes("fetch('/presentation.json'"));assert.ok(viewer.includes('addObservationExterior(THREE,scene,viewport,presentation,geometry)'));
const report={status:'055_SHARED_SETTING_GEOMETRY_PASS',reproduced053_orbital_misapplication:true,setting_cases:cases.length,checks:result,preview_export_shared_source:true,no_model_ui_gpu:true};
fs.writeFileSync(new URL('./GEOMETRY-SETTING-RESULT.json',import.meta.url),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:report.status,setting_cases:cases.length,checks:result.length}));
