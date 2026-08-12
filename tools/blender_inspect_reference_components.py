"""List connected components in the authorized reference body mesh."""

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_nude_2_1_f117148577.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))

for object_name in ("Object003_Object003_mtl_0", "Object003_Object003_mtl_0.001"):
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        continue
    adjacency = [set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen = set(range(len(obj.data.vertices)))
    components = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    print(f"OBJECT {object_name} COMPONENTS {len(components)}")
    for component in sorted(components, key=len, reverse=True):
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in component]
        xs, ys, zs = ([p[axis] for p in points] for axis in range(3))
        if object_name == "Object003_Object003_mtl_0" and not (
            max(zs) >= 26 and min(zs) <= 34
            and max(ys) >= 4.0
            and max(xs) >= -1 and min(xs) <= 4
        ):
            continue
        print(
            len(component),
            f"x={min(xs):.3f}..{max(xs):.3f}",
            f"y={min(ys):.3f}..{max(ys):.3f}",
            f"z={min(zs):.3f}..{max(zs):.3f}",
        )
