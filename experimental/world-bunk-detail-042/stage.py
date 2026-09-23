from pathlib import Path
import hashlib,json,shutil,difflib
H=Path(__file__).resolve().parent;W=H.parent;K=Path('@kira_root');E=K/'tools/world_builder_engine'
C=H/'candidate/tools/world_builder_engine';C.mkdir(parents=True,exist_ok=False)
shutil.copytree(E/'layout_package_assets',C/'layout_package_assets',ignore=shutil.ignore_patterns('__pycache__'))
R=C/'layout_package_assets/source/room_dressing_render.mjs';old=R.read_text(encoding='utf-8')
helper='''  // Rounded, authored soft forms. Geometry only: no cloth/contact simulation.
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
'''
needle='  function legs(group,w,d,h,material=M.frame)'
assert old.count(needle)==1;new=old.replace(needle,helper+needle)
a=new.index("    }else if(kind==='bunk'){");b=new.index("    }else if(kind==='galley'){",a)
replacement='''    }else if(kind==='bunk'){
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
'''
new=new[:a]+replacement+new[b:];R.write_text(new,encoding='utf-8',newline='\n')
viewer=(E/'viewer.mjs').read_text(encoding='utf-8');start=viewer.index('// Original procedural meshes and textures.');end=viewer.index('async function start(){',start)
assert viewer[start:end].strip()==old.replace('export function ','function ').strip()
viewer=viewer.replace(old.replace('export function ','function ').strip(),new.replace('export function ','function ').strip(),1)
(C/'viewer.mjs').write_text(viewer,encoding='utf-8',newline='\n')
(H/'baseline').mkdir();(H/'baseline/room_dressing_render.mjs').write_text(old,encoding='utf-8',newline='\n');shutil.copyfile(E/'viewer.mjs',H/'baseline/viewer.mjs')
pins=json.loads((C/'layout_package_assets/PRODUCER-PINS.json').read_bytes());pins['files']['source/room_dressing_render.mjs']={'sha256':hashlib.sha256(R.read_bytes()).hexdigest(),'bytes':R.stat().st_size}
(C/'layout_package_assets/PRODUCER-PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
source={str(p.relative_to(E)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [E/'viewer.mjs',E/'layout_package_assets/source/room_dressing_render.mjs',E/'layout_package_assets/source/room_dressing_plan.mjs',E/'layout_package_assets/authored_scene.mjs',E/'layout_package_assets/PRODUCER-PINS.json']}
(H/'SOURCE-PINS.json').write_text(json.dumps(source,indent=2)+'\n',encoding='utf-8')
fixtures=H/'fixtures';fixtures.mkdir()
for kind in ('base','renamed','wider','translated'):shutil.copyfile(W/'world-export-profile-041/fixtures'/('profile_'+kind+'.json'),fixtures/(kind+'.json'))
(H/'CHANGES.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='installed041/room_dressing_render.mjs',tofile='candidate042/room_dressing_render.mjs')),encoding='utf-8')
print(json.dumps({'status':'042_ISOLATED_GEOMETRY_STAGED','renderer_sha256':hashlib.sha256(R.read_bytes()).hexdigest(),'canonical_changes':0,'viewer_and_export_share_identical_dressing_source':True}))
