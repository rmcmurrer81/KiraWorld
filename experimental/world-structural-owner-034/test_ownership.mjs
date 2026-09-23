import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createDoorSystem} from './core/candidate/tools/world_builder_engine/walk_controller.mjs';
import {buildRoomDressing} from './core/room_dressing_plan.mjs';
import {exportSceneMetadata,canonicalSceneMetadata} from './core/candidate/tools/world_builder_engine/scene_metadata.mjs';
import {exportSceneMetadata as previousExport} from './baseline/scene_metadata.mjs';
const H=new URL('./',import.meta.url),raw=fs.readFileSync(process.argv[2]||new URL('core/fixtures/synthetic_habitat.json',H));
const geometry=JSON.parse(raw),checks=[],hash=data=>crypto.createHash('sha256').update(data).digest('hex');
const options={sceneId:'structural_owner_test',sourceDigests:{geometry:hash(raw),dressing_recipe:hash(fs.readFileSync(new URL('core/room_dressing_plan.mjs',H))),door_controller:hash(fs.readFileSync(new URL('core/candidate/tools/world_builder_engine/walk_controller.mjs',H)))}};
const doors=createDoorSystem(geometry),dressing=buildRoomDressing(geometry,doors.assemblies()),definitions=doors.definitions();
const make=(g=geometry)=>exportSceneMetadata(g,dressing,definitions,options),before=JSON.stringify({geometry,dressing,definitions});
const scene=make(),old=previousExport(geometry,dressing,definitions,options);
const box=node=>({min:node.transform.position.map((n,i)=>n-node.representation.size[i]/2),max:node.transform.position.map((n,i)=>n+node.representation.size[i]/2)});
function sameBox(a,b){for(const bound of ['min','max'])for(let i=0;i<3;i++)assert(Math.abs(a[bound][i]-b[bound][i])<1e-7);}
function test(name,fn){fn();checks.push(name);}
test('Every structural collider has one intended structural owner with equivalent bounds',()=>{
 for(const c of geometry.colliders){
  const out=scene.colliders.find(x=>x.id==='collider:'+c.id);assert(out?.owner_node_id);
  const node=scene.nodes.find(n=>n.id===out.owner_node_id);assert.equal(node.kind,'structural_primitive');
  const exact=geometry.primitives.find(p=>p.id===c.id),floor=geometry.primitives.find(p=>p.id===c.id+'_mesh'&&p.role==='floor');
  assert.equal([exact,floor].filter(Boolean).length,1);assert.equal(node.id,'node:'+(exact??floor).id);sameBox(out.bounds,box(node));
 }
});
test('Existing geometry, all other fields and input values remain unchanged',()=>{
 const expected=structuredClone(old);
 for(const c of expected.colliders){const actual=scene.colliders.find(x=>x.id===c.id);c.owner_node_id=actual.owner_node_id;}
 assert.deepEqual(scene,expected);assert.equal(JSON.stringify({geometry,dressing,definitions}),before);
 assert.equal(canonicalSceneMetadata(scene),canonicalSceneMetadata(make()));
 assert.equal(canonicalSceneMetadata(JSON.parse(canonicalSceneMetadata(scene))),canonicalSceneMetadata(scene));
});
const floor=geometry.primitives.find(p=>p.role==='floor'&&p.id.endsWith('_mesh'));assert(floor);
function floorCase(){const g=structuredClone(geometry),id=floor.id.slice(0,-5);g.colliders.push({id,...box({transform:{position:floor.position},representation:{size:floor.size}})});return {g,id};}
test('Floor collider resolves the compiler floor_mesh alias and exact dimensions',()=>{
 const {g,id}=floorCase(),s=make(g),c=s.colliders.find(c=>c.id==='collider:'+id);
 assert.equal(c.owner_node_id,'node:'+floor.id);sameBox(c.bounds,box(s.nodes.find(n=>n.id===c.owner_node_id)));
});
test('Two valid names are ambiguous even if their bounds agree',()=>{
 const {g,id}=floorCase();g.primitives.push({...structuredClone(floor),id});
 assert.throws(()=>make(g),/ambiguous structural collider owner/);
});
test('Ambiguous names are not silently disambiguated by one different box',()=>{
 const {g,id}=floorCase();const p={...structuredClone(floor),id};p.position[0]+=.2;g.primitives.push(p);
 assert.throws(()=>make(g),/ambiguous structural collider owner/);
});
test('Missing name never falls back to some unrelated same-bounds object',()=>{
 const g=structuredClone(geometry);g.colliders[0].id='missing_structural_owner';
 assert.throws(()=>make(g),/Missing or ambiguous structural collider owner/);
});
test('Exact name with mismatched box is rejected',()=>{
 const g=structuredClone(geometry);g.colliders[0].min[0]-=.01;
 assert.throws(()=>make(g),/owner bounds mismatch/);
});
test('Floor alias with mismatched box is rejected',()=>{
 const {g}=floorCase();g.colliders.at(-1).max[2]+=.01;
 assert.throws(()=>make(g),/owner bounds mismatch/);
});
test('Non-floor mesh-suffix alias is not accepted',()=>{
 const g=structuredClone(geometry),c=g.colliders[0],p=g.primitives.find(p=>p.id===c.id);assert(p);p.id+='_mesh';
 assert.throws(()=>make(g),/Missing or ambiguous structural collider owner/);
});
test('Matching equipment name cannot own a structural collider',()=>{
 const g=structuredClone(geometry),item=dressing.objects[0];g.colliders.push({id:item.id,min:item.bounds.min,max:item.bounds.max});
 assert.throws(()=>make(g),/must belong to a structural primitive/);
});
const corrected=scene.colliders.filter(c=>old.colliders.find(o=>o.id===c.id)?.owner_node_id!==c.owner_node_id).length;
const result={status:'PASS_STRUCTURAL_COLLIDER_OWNERSHIP',checks,source_sha256:hash(raw),structural_colliders:geometry.colliders.length,
 all_structural_owner_ids_nonnull:true,all_structural_owner_bounds_equivalent:true,corrected_owner_links:corrected,
 counts:Object.fromEntries(['rooms','nodes','colliders','doors'].map(k=>[k,scene[k].length])),input_unchanged:true,
 scene_sha256:hash(canonicalSceneMetadata(scene)),historical_export_changed:false,installed:false,metadata_only:true,gpu_models:0};
const output=process.argv[3]||new URL('OWNERSHIP-RESULT.json',H);
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({...result,checks:checks.length}));
