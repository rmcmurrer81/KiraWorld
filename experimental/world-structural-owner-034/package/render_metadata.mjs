// Owned CPU adapter: explicit JSON input; no dynamic source/data-driven evaluation.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const core=path.resolve(process.argv[2]);
const {createDoorSystem}=await import(pathToFileURL(path.join(core,'candidate/tools/world_builder_engine/walk_controller.mjs')).href);
const {buildRoomDressing}=await import(pathToFileURL(path.join(core,'room_dressing_plan.mjs')).href);
const {exportSceneMetadata,canonicalSceneMetadata}=await import(pathToFileURL(path.join(core,'candidate/tools/world_builder_engine/scene_metadata.mjs')).href);
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const doors=createDoorSystem(input.geometry),plan=buildRoomDressing(input.geometry,doors.assemblies());
const result=exportSceneMetadata(input.geometry,plan,doors.definitions(),input.options);
// The wrapper verifies actual bound source bytes and this exact core revision
// before and after this call. This labels those byte checks, not source truth.
const output={...result,provenance:{...result.provenance,
 binding_verification:'actual_bound_bytes_verified_by_package_writer',
 source_chain_verification:'geometry_to_blueprint_to_research_packet_and_cache_digests',
 factual_or_visual_approval:false}};
process.stdout.write(canonicalSceneMetadata(output));
