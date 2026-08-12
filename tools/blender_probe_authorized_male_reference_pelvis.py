"""Read-only coordinate probe of the authorized adult male reference pelvis.

The output is structural guidance only.  It does not export or transfer the
reference person's body, identity, proportions, face, or skin.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/"
    "male_nude_2_1_f117148577.glb"
)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))

center_x = 1.69
samples = []
by_object = defaultdict(list)
for obj in (item for item in bpy.context.scene.objects if item.type == "MESH"):
    matrix = obj.matrix_world
    for vertex in obj.data.vertices:
        co = matrix @ vertex.co
        if (
            abs(co.x - center_x) <= 0.85
            and 24.0 <= co.z <= 36.0
        ):
            samples.append((co.x, co.y, co.z, obj.name, vertex.index))
            by_object[obj.name].append((co.x, co.y, co.z))

print("SOURCE", SOURCE)
print("SAMPLE_COUNT", len(samples))
print(
    "BOUNDS",
    {
        "x": [min(x for x, *_ in samples), max(x for x, *_ in samples)],
        "y": [min(y for _x, y, *_ in samples), max(y for _x, y, *_ in samples)],
        "z": [min(z for _x, _y, z, *_ in samples), max(z for _x, _y, z, *_ in samples)],
    },
)
for name, values in sorted(by_object.items(), key=lambda item: len(item[1]), reverse=True):
    print(
        "OBJECT",
        name,
        len(values),
        {
            "x": [min(v[0] for v in values), max(v[0] for v in values)],
            "y": [min(v[1] for v in values), max(v[1] for v in values)],
            "z": [min(v[2] for v in values), max(v[2] for v in values)],
        },
    )

for z0 in [24.0 + index * 0.5 for index in range(24)]:
    band = [
        item
        for item in samples
        if z0 <= item[2] < z0 + 0.5
    ]
    if not band:
        continue
    print(
        "ZBIN",
        round(z0, 2),
        len(band),
        round(min(item[1] for item in band), 4),
        round(max(item[1] for item in band), 4),
    )

# Print the most anterior central vertices.  Positive-Y is the visible front in
# the existing neutral-detail render.
front = sorted(samples, key=lambda item: item[1], reverse=True)[:100]
print("FRONT_SAMPLE")
for item in front:
    print(
        tuple(round(value, 5) if isinstance(value, float) else value for value in item)
    )
