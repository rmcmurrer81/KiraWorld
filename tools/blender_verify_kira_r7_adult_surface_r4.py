"""Reopen verifier for Kira's inactive R7 reconstructed-neck R4-v10 Blend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


OBJECT_NAME = "Kira_R7_Reconstructed_Neck_Surface_R4V10_Inactive"
TRANSITION_METHOD = "topological_erosion_arc_length_ruled_loft_neck_reconstruction"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    obj = bpy.data.objects.get(OBJECT_NAME)
    armatures = [item for item in bpy.data.objects if item.type == "ARMATURE" and len(item.data.bones) == 79]
    modifiers = [item for item in obj.modifiers if item.type == "ARMATURE"] if obj else []
    scene = bpy.context.scene
    record = {
        "object_found": obj is not None,
        "object_type": obj.type if obj else None,
        "vertices": len(obj.data.vertices) if obj else 0,
        "polygons": len(obj.data.polygons) if obj else 0,
        "defined_vertex_groups": len(obj.vertex_groups) if obj else 0,
        "armature_79_count": len(armatures),
        "armature_modifier_targets_79_joint_cage": bool(
            len(modifiers) == 1
            and modifiers[0].object is not None
            and len(modifiers[0].object.data.bones) == 79
        ),
        "transition_method": obj.get("transition_method") if obj else None,
        "bounded_body_neck_reconstruction": bool(obj.get("bounded_body_neck_reconstruction", False)) if obj else False,
        "finite_bounded_ruled_loft": bool(obj.get("circumferential_relaxation_boundary_fade", False)) if obj else False,
        "protected_r6_face_mouth_eye_cranium_coordinates_preserved": bool(obj.get("protected_r6_face_mouth_eye_cranium_coordinates_preserved", False)) if obj else False,
        "adult_surface_outside_bounded_transition_preserved": bool(obj.get("adult_surface_outside_bounded_transition_preserved", False)) if obj else False,
        "scene_flags": {
            "inactive_review_only": bool(scene.get("inactive_review_only", False)),
            "candidate_export_allowed": bool(scene.get("candidate_export_allowed", True)),
            "live_binding_allowed": bool(scene.get("live_binding_allowed", True)),
            "runtime_activation_allowed": bool(scene.get("runtime_activation_allowed", True)),
            "owner_approved": bool(scene.get("owner_approved", True)),
            "complete_adult_topology_proven": bool(scene.get("complete_adult_topology_proven", True)),
            "protected_r6_face_mouth_eye_cranium_coordinates_preserved": bool(scene.get("protected_r6_face_mouth_eye_cranium_coordinates_preserved", False)),
            "adult_surface_outside_bounded_transition_preserved": bool(scene.get("adult_surface_outside_bounded_transition_preserved", False)),
            "bounded_body_neck_reconstruction": bool(scene.get("bounded_body_neck_reconstruction", False)),
            "finite_bounded_ruled_loft": bool(scene.get("finite_bounded_ruled_loft", False)),
            "engineering_bounded_reconstruction_passed": bool(scene.get("engineering_bounded_reconstruction_passed", False)),
        },
    }
    record["passed"] = bool(
        record["object_found"]
        and record["vertices"] > 20000
        and record["polygons"] > 40000
        and record["defined_vertex_groups"] == 79
        and record["armature_79_count"] == 1
        and record["armature_modifier_targets_79_joint_cage"]
        and record["bounded_body_neck_reconstruction"]
        and record["finite_bounded_ruled_loft"]
        and record["protected_r6_face_mouth_eye_cranium_coordinates_preserved"]
        and record["adult_surface_outside_bounded_transition_preserved"]
        and record["transition_method"] == TRANSITION_METHOD
        and record["scene_flags"]["inactive_review_only"]
        and not record["scene_flags"]["candidate_export_allowed"]
        and not record["scene_flags"]["live_binding_allowed"]
        and not record["scene_flags"]["runtime_activation_allowed"]
        and not record["scene_flags"]["owner_approved"]
        and not record["scene_flags"]["complete_adult_topology_proven"]
        and record["scene_flags"]["protected_r6_face_mouth_eye_cranium_coordinates_preserved"]
        and record["scene_flags"]["adult_surface_outside_bounded_transition_preserved"]
        and record["scene_flags"]["bounded_body_neck_reconstruction"]
        and record["scene_flags"]["finite_bounded_ruled_loft"]
        and record["scene_flags"]["engineering_bounded_reconstruction_passed"]
    )
    output = Path(args.output).resolve()
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "passed": record["passed"], "output": str(output)}, indent=2))
    return 0 if record["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
