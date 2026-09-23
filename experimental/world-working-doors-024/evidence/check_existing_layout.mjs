import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createDoorSystem,createWalkController} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {NAVIGATION_CONTRACT,checkHorizontalRoute} from './candidate/tools/world_builder_engine/horizontal_navigation.mjs';
const root=path.join(os.homedir(),'Kira');
const manifestPath=path.join(root,'Data/world_layout_previews/layout-a37f864587b3ee075e21ccd1/manifest.json');
const manifestRaw=fs.readFileSync(manifestPath),manifest=JSON.parse(manifestRaw);
const geometryPath=manifest.assets['/geometry.json'].path,raw=fs.readFileSync(geometryPath),g=JSON.parse(raw);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
assert.equal(sha(raw),manifest.assets['/geometry.json'].sha256);
assert.equal(sha(manifestRaw),'f99bbbe4fde564e1f48814c899b85ca6f78b0ffe9466a4a88ccabd139999313a');
const outcomes=[];
for(const portal of g.portals.filter(p=>p.state==='open_passage')){
 const doors=createDoorSystem(g),route=g.routes.find(r=>r.id===portal.id);
 const nav=()=>({contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:doors.colliders()});
 assert.equal(checkHorizontalRoute(route,nav()).status,'blocked');
 const roomB=g.rooms.find(r=>r.id===portal.room_b),normal=portal.axis==='x'?0:2;
 const center=portal.axis==='x'?roomB.x+roomB.width/2:roomB.z+roomB.depth/2;
 const foot=portal.axis==='x'?[portal.coordinate,roomB.floor_y,portal.center]:[portal.center,roomB.floor_y,portal.coordinate];
 foot[normal]+=Math.sign(center-portal.coordinate)*.9;
 assert.equal(doors.toggle(portal.id,foot).ok,true);
 for(let i=0;i<10;i++)doors.advance(.05,foot);
 assert.equal(doors.all().find(d=>d.id===portal.id).state,'open');
 const forward=checkHorizontalRoute(route,nav()),reverse=checkHorizontalRoute({...route,points:[...route.points].reverse()},nav());
 assert.equal(forward.status,'clear');assert.equal(reverse.status,'clear');
 outcomes.push({portal_id:portal.id,closed_route:'blocked',open_forward:forward.status,open_reverse:reverse.status});
}
const walker=createWalkController(g);assert.ok(walker.snapshot().roomId);
assert.equal(sha(fs.readFileSync(geometryPath)),sha(raw));assert.equal(sha(fs.readFileSync(manifestPath)),sha(manifestRaw));
const result={status:'PASS_EXISTING_LAYOUT_DOOR_ROUTES_READ_ONLY',layout_manifest_sha256:sha(manifestRaw),geometry_sha256:sha(raw),
 doors:outcomes,spawn_supported:true,source_files_unchanged:true,owner_geometry_copied_or_written:false,
 models_gpu_ui_started:false,visual_quality:'Owner rejected the existing Mars appearance. This check validates door behavior only; it is not visual approval.'};
fs.writeFileSync(new URL('./EXISTING-LAYOUT-DOOR-CHECK.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,doors:outcomes.length,owner_files_unchanged:true}));
