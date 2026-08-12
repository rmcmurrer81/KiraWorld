"""Temporary read-only console probe for the V1 modifier/material pipeline."""
from pathlib import Path
from collections import Counter
import bpy

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
bpy.ops.wm.open_mainfile(filepath=str(SRC))
obj = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
for polygon in obj.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1
print("BEFORE", [(i, m.name if m else None) for i, m in enumerate(obj.data.materials)], Counter(p.material_index for p in obj.data.polygons))
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
for modifier in list(obj.modifiers):
    bpy.ops.object.modifier_apply(modifier=modifier.name)
print("AFTER", len(obj.data.polygons), [(i, m.name if m else None) for i, m in enumerate(obj.data.materials)], Counter(p.material_index for p in obj.data.polygons))
