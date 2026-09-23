"""Compose authored habitat functions into a COPY of frozen024 frontend assets."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent
S=H.parent/'world-working-doors-candidate-024/candidate/tools/world_builder_engine'
O=H/'candidate/tools/world_builder_engine';O.mkdir(parents=True,exist_ok=False)
for name in ('walk_controller.mjs','viewer.mjs','index.html','style.css','horizontal_navigation.mjs','world_layout_preview.py','preflight.mjs'):
 shutil.copyfile(S/name,O/name)
viewer=(S/'viewer.mjs').read_text(encoding='utf-8')
viewer=viewer.replace('{AVATAR,createWalkController}','{AVATAR,createWalkController,createDoorSystem}')
viewer=viewer.replace('  const geometry=await response.json(), controller=createWalkController(geometry);',
 '''  const geometry=await response.json();
  const dressing=buildRoomDressing(geometry,createDoorSystem(geometry).assemblies());
  const controller=createWalkController(geometry,{extraColliders:dressing.colliders});''')
viewer=viewer.replace('  renderer.outputColorSpace=THREE.SRGBColorSpace;',
 '''  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;''')
viewer=viewer.replace("scene.background=new THREE.Color('#819698')","scene.background=new THREE.Color('#303d44')")
viewer=viewer.replace('scene.add(new THREE.HemisphereLight(0xedf5f2,0x8f8173,2.8));','scene.add(new THREE.HemisphereLight(0xe3edf2,0x60574b,.62));')
viewer=viewer.replace('new THREE.DirectionalLight(0xfff0d0,1.2)','new THREE.DirectionalLight(0xfff0d0,.25)')
start=viewer.index('  const colors=');end=viewer.index('  const doorMeshes=',start)
replacement='''  const dressingMaterials=createDressingMaterials(THREE,dressing);
  for(const primitive of geometry.primitives){
    const room=geometry.rooms.find(r=>primitive.id.startsWith(r.id+'_'));
    const material=dressingMaterials.surface(primitive.role,room?.id);
    if(primitive.role==='floor'&&material.map)material.map.repeat.set(Math.max(1,primitive.size[0]),Math.max(1,primitive.size[2]));
    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...primitive.size),material);
    mesh.position.set(...primitive.position);mesh.receiveShadow=true;scene.add(mesh);
  }
  addRoomDressing(THREE,scene,geometry,dressing,dressingMaterials);
'''
viewer=viewer[:start]+replacement+viewer[end:]
parts=[]
for name in ('room_dressing_plan.mjs','room_dressing_render.mjs'):
 parts.append((H/name).read_text(encoding='utf-8').replace('export const ','const ').replace('export function ','function '))
viewer=viewer.replace('async function start(){','\n'.join(parts)+'\n\nasync function start(){',1)
(O/'viewer.mjs').write_text(viewer,encoding='utf-8',newline='\n')
html=(O/'index.html').read_text(encoding='utf-8').replace('Layout prototype · unfinished appearance','Original habitat · procedural preview').replace('Explore room scale and working doors. Room appearance remains unfinished; this is not a verified reconstruction.','Explore distinct equipment spaces and working doors. This authored habitat is still a procedural preview, not a verified reconstruction.')
(O/'index.html').write_text(html,encoding='utf-8',newline='\n')
print(json.dumps({'status':'025_ISOLATED_VIEWER_ASSEMBLED','canonical_files_changed':False,'viewer_sha256':hashlib.sha256((O/'viewer.mjs').read_bytes()).hexdigest()}))
