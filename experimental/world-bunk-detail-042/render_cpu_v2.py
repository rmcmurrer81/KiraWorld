"""Run by installed Blender in background: actual GLB to one review PNG, CPU only."""
from pathlib import Path
import bpy,json,math,sys
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];glb,metadata_path,output=map(Path,args)
metadata=json.loads(metadata_path.read_bytes())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(glb))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.cycles.denoiser='OPENIMAGEDENOISE';scene.cycles.denoising_use_gpu=False
scene.cycles.max_bounces=2;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=1;scene.cycles.transmission_bounces=1
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.filepath=str(output/'bunk-review.png')
scene.render.film_transparent=False
scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.12,.14,.16,1);scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.18
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.3
room=next(r for r in metadata['rooms'] if r['functional_role']=='habitat')
bunk=next(n for n in metadata['nodes'] if n['kind']=='bunk' and n['room_id']==room['id'])
lo,hi=room['bounds']['min'],room['bounds']['max'];base=bunk['transform']['position']
target=Vector((base[0],-base[2],1.10));center=Vector(((lo[0]+hi[0])/2,-(lo[2]+hi[2])/2,1.55))
direction=(center-Vector((base[0],-base[2],1.55))).normalized();side=Vector((-direction.y,direction.x,0))
position=Vector((base[0],-base[2],1.55))+direction*2.55+side*.35
position.x=max(lo[0]+.3,min(hi[0]-.3,position.x));position.y=max(-hi[2]+.3,min(-lo[2]-.3,position.y))
camera_data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',camera_data);scene.collection.objects.link(camera)
camera.location=position;camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler();camera_data.lens=27;camera_data.clip_start=.05;scene.camera=camera
# Explicit neutral artifact-review fill supplements the original imported lights.
# It does not alter the GLB and is not a claim about native preview illumination.
light_data=bpy.data.lights.new('Review fill','AREA');light_data.energy=90;light_data.shape='DISK';light_data.size=1.6
light=bpy.data.objects.new('Review fill',light_data);scene.collection.objects.link(light);light.location=Vector((position.x,position.y,2.45));light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
details={'engine':'CYCLES','device':scene.cycles.device,'samples':16,'denoiser':'CPU_OPENIMAGEDENOISE','threads':4,'resolution':[640,480],'imported_glb':glb.name,'room_id':room['id'],'bunk_id':bunk['id'],'camera_location':list(position),'camera_target':list(target),'review_area_fill_watts':90,'native_preview_lighting_equivalent':False,'source_mesh_or_texture_modified':False,'native_ui_opened':False}
with (output/'RENDER-DETAILS.json').open('x',encoding='utf-8') as f:json.dump(details,f,indent=2);f.write('\n')
bpy.ops.render.render(write_still=True)
