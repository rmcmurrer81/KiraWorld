import bpy

print(sorted(bpy.ops.export_scene.gltf.get_rna_type().properties.keys()))
