"""Read-only inventory of nail components in the R21 private review blend.

This script never saves the opened Blend. It writes only an append-only JSON
preflight record under RecoverySprint.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_08_review/KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT08_REVIEW.blend"
OUTPUT = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/NAIL_PREFLIGHT.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_nail(obj: bpy.types.Object) -> bool:
    if obj.type != "MESH":
        return False
    terms = " ".join(
        [obj.name, obj.data.name]
        + [slot.material.name for slot in obj.material_slots if slot.material]
    ).lower()
    return bool(obj.get("nail_component")) or "nail" in terms


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source_hash_before = sha256_file(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    nails = []
    for obj in sorted((item for item in bpy.data.objects if is_nail(item)), key=lambda item: item.name):
        world_points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        low = [min(float(point[axis]) for point in world_points) for axis in range(3)]
        high = [max(float(point[axis]) for point in world_points) for axis in range(3)]
        groups = []
        for group in obj.vertex_groups:
            total = 0.0
            count = 0
            for vertex in obj.data.vertices:
                try:
                    weight = float(group.weight(vertex.index))
                except RuntimeError:
                    continue
                if weight > 0.0:
                    total += weight
                    count += 1
            if count:
                groups.append({"name": group.name, "positive_vertex_count": count, "weight_sum": total})
        nails.append(
            {
                "object": obj.name,
                "mesh": obj.data.name,
                "vertex_count": len(obj.data.vertices),
                "polygon_count": len(obj.data.polygons),
                "world_bounds_min_m": low,
                "world_bounds_max_m": high,
                "world_dimensions_m": [high[i] - low[i] for i in range(3)],
                "world_centroid_m": [sum(float(point[i]) for point in world_points) / len(world_points) for i in range(3)],
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
                "parent": obj.parent.name if obj.parent else None,
                "parent_type": obj.parent_type,
                "modifiers": [
                    {
                        "name": modifier.name,
                        "type": modifier.type,
                        "object": getattr(modifier, "object", None).name if getattr(modifier, "object", None) else None,
                    }
                    for modifier in obj.modifiers
                ],
                "vertex_groups": groups,
                "custom_properties": {str(key): obj[key] for key in obj.keys() if key != "_RNA_UI" and isinstance(obj[key], (str, int, float, bool))},
            }
        )
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    record = {
        "schema": "kira_r21_nail_preflight_v1",
        "source_project_relative": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256_before": source_hash_before,
        "source_sha256_after_open": sha256_file(SOURCE),
        "source_file_unchanged": source_hash_before == sha256_file(SOURCE),
        "blender_version": bpy.app.version_string,
        "scene_object_count": len(bpy.data.objects),
        "mesh_object_count": len(meshes),
        "armatures": [
            {"object": obj.name, "bone_count": len(obj.data.bones), "pose_position": obj.data.pose_position}
            for obj in armatures
        ],
        "nail_component_count": len(nails),
        "nails": nails,
        "read_only": True,
        "blend_saved": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "nails": len(nails), "source_unchanged": record["source_file_unchanged"]}, indent=2))


if __name__ == "__main__":
    main()
