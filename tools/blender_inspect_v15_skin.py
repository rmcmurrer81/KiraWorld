from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
material = bpy.data.materials.get("MBLab_skin3")
print("material", material.name, "nodes", material.use_nodes)
for node in material.node_tree.nodes:
    values = []
    for socket in node.outputs:
        if hasattr(socket, "default_value"):
            values.append((socket.name, socket.default_value))
    print(node.name, node.bl_idname, values)
for link in material.node_tree.links:
    print("LINK", link.from_node.name, link.from_socket.name, "->", link.to_node.name, link.to_socket.name)
