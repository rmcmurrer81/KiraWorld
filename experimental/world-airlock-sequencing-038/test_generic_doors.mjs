import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createDoorSystem,createWalkController,AVATAR,DOOR_CONTRACT} from './candidate/tools/world_builder_engine/walk_controller.mjs';
import {checkHorizontalRoute,NAVIGATION_CONTRACT} from './candidate/tools/world_builder_engine/horizontal_navigation.mjs';

const checks=[];
function test(name,body){body();checks.push(name);}
const fixtures=['x_negative','x_positive','z_negative','z_positive'].map(name=>({name,g:JSON.parse(fs.readFileSync(new URL('./fixtures/'+name+'.json',import.meta.url)))}));
const body=(feet)=>({id:'test',avatar_radius:AVATAR.radius,avatar_height:AVATAR.height,points:feet});
for(const {name,g} of fixtures){
  const original=JSON.stringify(g),normal=g.portals[0].axis==='x'?0:2,sign=name.includes('negative')?-1:1;
  const feetAt=distance=>{const p=[0,0,0];p[normal]=sign*distance;return p;};
  const nav=doors=>({contract:NAVIGATION_CONTRACT,support_surfaces:g.support_surfaces,colliders:doors.colliders()});
  test(name+': closed leaf blocks passage in both directions',()=>{
    const doors=createDoorSystem(g);assert.equal(doors.contract,DOOR_CONTRACT);assert.equal(doors.all()[0].state,'closed');
    for(const points of [[feetAt(1),feetAt(-1)],[feetAt(-1),feetAt(1)]]){
      const result=checkHorizontalRoute(body(points),nav(doors));assert.equal(result.status,'blocked');assert.equal(result.collider_id,'door_opening_1_leaf');
    }
  });
  test(name+': visible pose and collision bounds agree throughout animation',()=>{
    const doors=createDoorSystem(g);assert.equal(doors.toggle('opening_1',feetAt(1.7)).ok,true);
    for(let i=0;i<9;i++){
      doors.advance(.05,feetAt(1.7));const pose=doors.all()[0];
      assert.ok(['opening','open'].includes(pose.state));
      for(const x of [-pose.size[0]/2,pose.size[0]/2])for(const z of [-pose.size[2]/2,pose.size[2]/2]){
        const actual=[pose.center[0]+x*Math.cos(pose.angle)+z*Math.sin(pose.angle),pose.center[2]-x*Math.sin(pose.angle)+z*Math.cos(pose.angle)];
        assert.ok(actual[0]>=pose.collider.min[0]-1e-12&&actual[0]<=pose.collider.max[0]+1e-12);
        assert.ok(actual[1]>=pose.collider.min[2]-1e-12&&actual[1]<=pose.collider.max[2]+1e-12);
      }
    }
    assert.equal(doors.all()[0].state,'open');assert.ok(Math.abs(Math.abs(doors.all()[0].angle)-Math.PI/2)<1e-12);
    assert.equal(checkHorizontalRoute(body([feetAt(1),feetAt(-1)]),nav(doors)).status,'clear');
  });
  test(name+': closing is refused across occupied sweep, then restores blocking',()=>{
    const doors=createDoorSystem(g);doors.toggle('opening_1',feetAt(1.7));for(let i=0;i<10;i++)doors.advance(.05,feetAt(1.7));
    assert.equal(doors.toggle('opening_1',feetAt(.5)).ok,false);assert.equal(doors.all()[0].state,'open');
    assert.equal(doors.toggle('opening_1',feetAt(-1)).ok,true);for(let i=0;i<10;i++)doors.advance(.05,feetAt(-1));
    assert.equal(doors.all()[0].state,'closed');assert.equal(checkHorizontalRoute(body([feetAt(1),feetAt(-1)]),nav(doors)).status,'blocked');
  });
  test(name+': motion pauses if the avatar enters the sweep',()=>{
    const doors=createDoorSystem(g);doors.toggle('opening_1',feetAt(1.7));doors.advance(.05,feetAt(1.7));const before=doors.all()[0].angle;
    doors.advance(.05,feetAt(.7));assert.equal(doors.all()[0].angle,before);assert.equal(doors.all()[0].motionHeld,true);
    doors.advance(.05,feetAt(1.7));assert.notEqual(doors.all()[0].angle,before);assert.equal(doors.all()[0].motionHeld,false);
  });
  test(name+': actual walking callback blocks, opens, crosses and returns',()=>{
    const blocked=createWalkController(g);for(let i=0;i<45;i++)blocked.step(.05,{forward:true});
    assert.equal(blocked.snapshot().blocked,'door_obstruction');assert.equal(blocked.snapshot().roomId,'entry');
    const walker=createWalkController(g);for(let i=0;i<3;i++)walker.step(.05,{forward:true});
    assert.equal(walker.toggleDoor().ok,true);for(let i=0;i<10;i++)walker.step(.05,{});
    for(let i=0;i<30;i++)walker.step(.05,{forward:true});
    assert.equal(walker.snapshot().roomId,'next_room');assert.ok(walker.snapshot().distance>3);
    for(let i=0;i<30;i++)walker.step(.05,{backward:true});assert.equal(walker.snapshot().roomId,'entry');
  });
  test(name+': out of reach, wrong elevation and unknown doors cannot toggle',()=>{
    const doors=createDoorSystem(g);assert.equal(doors.toggle('opening_1',feetAt(2.3)).ok,false);
    const upper=feetAt(1);upper[1]=2;assert.equal(doors.toggle('opening_1',upper).ok,false);
    assert.equal(doors.toggle('unknown',feetAt(1)).ok,false);assert.equal(doors.all()[0].state,'closed');
  });
  test(name+': source geometry and independent preview state stay unchanged',()=>{
    const a=createDoorSystem(g),b=createDoorSystem(g);a.toggle('opening_1',feetAt(1.7));a.advance(.05,feetAt(1.7));
    assert.equal(b.all()[0].state,'closed');assert.equal(JSON.stringify(g),original);
    const frame=a.assemblies()[0].frames[0];assert.throws(()=>{frame.min[0]=999;},TypeError);
    assert.throws(()=>{a.all()[0].center[0]=999;},TypeError);
  });
}
test('Malformed and locked portals cannot create an unguarded door',()=>{
  const g=fixtures[0].g;
  for(const patch of [{axis:'bad'},{width:NaN},{coordinate:123},{width:.2},{height:50},{center:20}]){
    const bad=structuredClone(g);Object.assign(bad.portals[0],patch);assert.throws(()=>createDoorSystem(bad),TypeError);
  }
  const duplicate=structuredClone(g);duplicate.portals.push({...duplicate.portals[0]});assert.throws(()=>createDoorSystem(duplicate),TypeError);
  const locked=structuredClone(g);locked.rooms[1].access='closed_locked_solid';assert.throws(()=>createDoorSystem(locked),TypeError);
  locked.portals[0].state='closed_locked_solid';assert.equal(createDoorSystem(locked).all().length,0);
});
test('Invalid input time and positions rejected, long animation step clamped',()=>{
  const doors=createDoorSystem(fixtures[0].g);assert.throws(()=>doors.advance(-1,[0,0,0]),TypeError);
  assert.throws(()=>doors.nearest([NaN,0,0]),TypeError);assert.throws(()=>doors.toggle('opening_1',[0,0,0],0),TypeError);
  doors.toggle('opening_1',[-1.7,0,0]);doors.advance(100,[-1.7,0,0]);assert.equal(doors.all()[0].state,'opening');assert.ok(Math.abs(doors.all()[0].angle)<.2);
});
test('Optional furnishings block movement without changing caller data',()=>{
  const g=fixtures[0].g,extra=[{id:'furniture_test',min:[-1.5,0,-.3],max:[-1.35,1.5,.3]}];
  const walker=createWalkController(g,{extraColliders:extra});extra[0].min[0]=99;extra[0].max[0]=100;
  for(let i=0;i<12;i++)walker.step(.05,{forward:true});
  assert.equal(walker.snapshot().blocked,'furniture_obstruction');assert.equal(walker.snapshot().roomId,'entry');
});
test('Furniture cannot overlap entry or borrow an existing collider identity',()=>{
  const g=fixtures[0].g;
  assert.throws(()=>createWalkController(g,{extraColliders:[{id:'entry_furniture',min:[-2.2,0,-.2],max:[-1.8,2,.2]}]}),/Entry position/);
  assert.throws(()=>createWalkController(g,{extraColliders:[{id:g.colliders[0].id,min:[-1.3,0,-.3],max:[-1.1,1,.3]}]}),TypeError);
});
test('Furniture cannot occupy a moving door sweep',()=>{
  const g=fixtures[0].g;
  assert.throws(()=>createWalkController(g,{extraColliders:[{id:'unsafe_table',min:[-.7,0,-.4],max:[-.3,1,.4]}]}),/door swing/);
  const sweep=createDoorSystem(g).assemblies()[0].swingBounds;assert.throws(()=>{sweep.min[0]=99;},TypeError);
});
const pins={};for(const name of ['walk_controller.mjs','viewer.mjs','index.html','style.css','horizontal_navigation.mjs']){
  const raw=fs.readFileSync(new URL('./candidate/tools/world_builder_engine/'+name,import.meta.url));pins[name]=crypto.createHash('sha256').update(raw).digest('hex');
}
const result={status:'PASS_DOOR_FUNCTIONAL_AND_COLLISION_CHECKS',at_utc:new Date().toISOString(),checks,source_pins:pins,fixtures:4,
  models_called:false,gpu_started:false,native_or_browser_review:false,owner_files_written:false,
  limits:['Door animation uses conservative axis-aligned leaf bounds and sweep rejection; not rigid-body dynamics.','Door states last for the current preview only.','This generic suite does not establish pressure seals, emergency egress or furnished-world acceptance. See AIRLOCK-RESULT for paired-door sequencing checks.']};
const serial=fs.readdirSync(new URL('.',import.meta.url)).filter(n=>n.startsWith('GENERIC-DOOR-RESULT')&&n.endsWith('.json')).length+1;
fs.writeFileSync(new URL('./GENERIC-DOOR-RESULT-'+serial+'.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,checks:checks.length}));
