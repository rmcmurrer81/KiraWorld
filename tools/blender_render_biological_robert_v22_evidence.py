"""Render V22 diagnostics, protected hands/nails, hair, and material passes."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v22_protected_bridge_rebuild"
BLEND=BASE/"BIOLOGICAL_ROBERT_STATIC_LIKENESS_V22_PROTECTED_BRIDGE_REBUILD.blend"
OUT=BASE/"diagnostics";OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene=bpy.context.scene
body=bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V22_PROTECTED_BRIDGE_REBUILD"]
for obj in list(scene.objects):
    if obj.type=="CAMERA": bpy.data.objects.remove(obj,do_unlink=True)
camd=bpy.data.cameras.new("V22EvidenceCamera");cam=bpy.data.objects.new("V22EvidenceCamera",camd);bpy.context.collection.objects.link(cam);scene.camera=cam
scene.render.engine="BLENDER_WORKBENCH";scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.display.shading.light="STUDIO";scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.render.image_settings.file_format="PNG"
def render(name,pos,target,lens=76,color="MATERIAL",light="STUDIO"):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler();cam.data.lens=lens
    scene.display.shading.color_type=color;scene.display.shading.light=light;scene.render.filepath=str(OUT/f"{name}.png");bpy.ops.render.render(write_still=True)
render("local_front_flat",(0,-1.25,.79),(0,0,.79))
render("local_side_flat",(1.0,-.62,.79),(0,-.08,.79))
render("local_three_quarter_flat",(.85,-.95,.79),(0,-.02,.79))
render("local_rear_perineal",(0,1.25,.72),(0,0,.72))
body.show_wire=True;body.show_all_edges=True
render("local_wireframe",(0,-1.25,.79),(0,0,.79),color="SINGLE")
body.show_wire=False
render("albedo_only",(0,-1.25,.79),(0,0,.79),color="MATERIAL",light="FLAT")
scene.display.shading.single_color=(.47,.47,.47)
render("roughness_only",(0,-1.25,.79),(0,0,.79),color="SINGLE",light="FLAT")
render("material_id",(0,-1.25,.79),(0,0,.79),color="MATERIAL",light="FLAT")
# Normal-direction diagnostic using world-space normals remapped to RGB.
normal=bpy.data.materials.new("V22_NORMAL_DIRECTION");normal.use_nodes=True
nodes=normal.node_tree.nodes;links=normal.node_tree.links;nodes.clear()
geom=nodes.new("ShaderNodeNewGeometry");math=nodes.new("ShaderNodeVectorMath");math.operation="MULTIPLY_ADD";math.inputs[1].default_value=(.5,.5,.5);math.inputs[2].default_value=(.5,.5,.5)
emit=nodes.new("ShaderNodeEmission");output=nodes.new("ShaderNodeOutputMaterial")
links.new(geom.outputs["Normal"],math.inputs[0]);links.new(math.outputs["Vector"],emit.inputs["Color"]);links.new(emit.outputs["Emission"],output.inputs["Surface"])
saved=[slot.material for slot in body.material_slots]
for slot in body.material_slots: slot.material=normal
scene.render.engine="BLENDER_EEVEE"
render("normal_direction",(0,-1.25,.79),(0,0,.79))
for slot,material in zip(body.material_slots,saved): slot.material=material
scene.render.engine="BLENDER_WORKBENCH"
render("hair_front",(0,-1.5,1.68),(0,0,1.68),lens=72)
render("hair_side",(1.35,-.30,1.69),(0,0,1.68),lens=72)
render("hair_three_quarter",(.95,-1.0,1.69),(0,0,1.68),lens=72)
render("hands_nails_front",(0,-2.0,1.07),(0,0,1.07),lens=88)
render("hands_nails_rear",(0,2.0,1.07),(0,0,1.07),lens=88)
print(OUT)
