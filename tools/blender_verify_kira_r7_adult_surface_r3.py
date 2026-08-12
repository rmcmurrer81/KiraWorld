"""Reopen verifier for Kira's inactive R7 measured-neck R3 Blend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


OBJECT_NAME = "Kira_R7_Measured_Neck_Bridge_R3_Inactive"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    obj = bpy.data.objects.get(OBJECT_NAME)
    armatures = [item for item in bpy.data.objects if item.type == "ARMATURE" and len(item.data.bones) == 79]
    modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"] if obj else []
    material = obj.data.materials[0] if obj and obj.data.materials else None
    record = {
        "object_found": obj is not None,
        "object_type": obj.type if obj else None,
        "vertices": len(obj.data.vertices) if obj else 0,
        "polygons": len(obj.data.polygons) if obj else 0,
        "defined_vertex_groups": len(obj.vertex_groups) if obj else 0,
        "armature_79_count": len(armatures),
        "armature_modifier_count": len(modifiers),
        "armature_modifier_targets_79_joint_cage": bool(
            len(modifiers) == 1
            and modifiers[0].object is not None
            and len(modifiers[0].object.data.bones) == 79
        ),
        "skin_material": material.name if material else None,
        "skin_diffuse_rgba": list(material.diffuse_color) if material else None,
        "scene_flags": {
            "inactive_review_only": bool(bpy.context.scene.get("inactive_review_only", False)),
            "candidate_export_allowed": bool(bpy.context.scene.get("candidate_export_allowed", True)),
            "live_binding_allowed": bool(bpy.context.scene.get("live_binding_allowed", True)),
            "runtime_activation_allowed": bool(bpy.context.scene.get("runtime_activation_allowed", True)),
            "owner_approved": bool(bpy.context.scene.get("owner_approved", True)),
            "complete_adult_topology_proven": bool(bpy.context.scene.get("complete_adult_topology_proven", True)),
            "identity_head_coordinates_preserved": bool(bpy.context.scene.get("identity_head_coordinates_preserved", False)),
            "measured_neck_bridge_engineering_passed": bool(bpy.context.scene.get("measured_neck_bridge_engineering_passed", False)),
        },
    }
    record["passed"] = bool(
        record["object_found"]
        and record["vertices"] > 0
        and record["polygons"] > 0
        and record["defined_vertex_groups"] == 79
        and record["armature_79_count"] == 1
        and record["armature_modifier_targets_79_joint_cage"]
        and record["scene_flags"]["inactive_review_only"]
        and not record["scene_flags"]["candidate_export_allowed"]
        and not record["scene_flags"]["live_binding_allowed"]
        and not record["scene_flags"]["runtime_activation_allowed"]
        and not record["scene_flags"]["owner_approved"]
        and not record["scene_flags"]["complete_adult_topology_proven"]
    )
    output = Path(args.output).resolve()
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "passed": record["passed"], "output": str(output)}, indent=2))
    return 0 if record["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
