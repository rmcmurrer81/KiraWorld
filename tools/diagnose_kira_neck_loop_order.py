from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "blender_author_kira_r7_adult_surface_r4.py"
SPEC = importlib.util.spec_from_file_location("kira_r4_worker", WORKER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

evidence = json.loads((ROOT / "Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/measured_neck_bridge_r3/evidence.json").read_text(encoding="utf-8"))
obj = bpy.data.objects[MODULE.OBJECT_R3]
body_count = int(evidence["bridge"]["head_vertex_offset"])
points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
faces = [tuple(map(int, polygon.vertices)) for polygon in obj.data.polygons]
bridge_faces = [face for face in faces if any(index < body_count for index in face) and any(index >= body_count for index in face)]
body_set = {index for face in bridge_faces for index in face if index < body_count}
head_set = {index for face in bridge_faces for index in face if index >= body_count}
body = MODULE.ordered_loop(points, body_set)
head = MODULE.ordered_loop(points, head_set)


def summary(loop: list[int]) -> dict[str, object]:
    center = sum((points[index] for index in loop), Vector()) / len(loop)
    angles = [math.atan2(points[index].y - center.y, points[index].x - center.x) % math.tau for index in loop]
    signed = []
    for a, b in zip(angles, angles[1:] + angles[:1]):
        signed.append((b - a + math.pi) % math.tau - math.pi)
    return {
        "count": len(loop),
        "center": list(center),
        "first_angles_deg": [math.degrees(value) for value in angles[:8]],
        "last_angles_deg": [math.degrees(value) for value in angles[-8:]],
        "mean_signed_step_deg": math.degrees(sum(signed) / len(signed)),
        "positive_steps": sum(value > 0 for value in signed),
        "negative_steps": sum(value < 0 for value in signed),
        "minimum_abs_step_deg": math.degrees(min(abs(value) for value in signed)),
        "maximum_abs_step_deg": math.degrees(max(abs(value) for value in signed)),
    }


print("NECK_LOOP_DIAGNOSTIC=" + json.dumps({"body": summary(body), "head": summary(head)}, sort_keys=True))
