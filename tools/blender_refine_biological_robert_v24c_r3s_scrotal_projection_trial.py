"""Test a bounded forward scrotal-envelope refinement on rejected R3.

R3's shaft/root direction improved, but its scrotal/perineal branch was
recessed into the body.  This non-promotable diagnostic moves only authored
zone-20/21 vertices forward in proportion to their stored graft mix, with a
small bilateral widening and shallow midline recess.  It does not alter the
body, shaft, face, hair, hands, or topology.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_r3_symmetric_root_graft/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_R3_SYMMETRIC_ROOT_GRAFT.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_r3s_scrotal_projection_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_SOURCE = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_R3_SYMMETRIC_ROOT_GRAFT"
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_R3S_"
    "SCROTAL_PROJECTION_TRIAL"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24C_R3S_SCROTAL_PROJECTION_REPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE)
if body is None:
    raise RuntimeError("R3 body not found")
mesh = body.data
zone_attribute = mesh.attributes.get("Adult_Anatomy_Zone")
mix_attribute = mesh.attributes.get("V24C_R3_Regional_Mix")
if zone_attribute is None or mix_attribute is None:
    raise RuntimeError(
        f"required graft attributes missing: {list(mesh.attributes.keys())}"
    )

changed = []
for vertex in mesh.vertices:
    zone = int(zone_attribute.data[vertex.index].value)
    if zone not in {20, 21}:
        continue
    mix = max(0.0, min(1.0, float(mix_attribute.data[vertex.index].value)))
    before = tuple(vertex.co)
    # Move the distal envelope clear of the body; retain a bounded root blend.
    forward = 0.026 * mix
    vertex.co.y -= forward
    if zone == 21:
        vertex.co.x *= 1.0 + 0.10 * mix
        vertex.co.z -= 0.0030 * mix
        # Preserve a shallow median raphe/cleft rather than one fused sphere.
        if abs(vertex.co.x) <= 0.006:
            vertex.co.y += 0.0040 * mix
            vertex.co.z += 0.0015 * mix
    changed.append(
        {
            "index": vertex.index,
            "zone": zone,
            "mix": mix,
            "before": list(before),
            "after": list(vertex.co),
        }
    )

mesh.update()
body.name = BODY_NAME
body["status"] = (
    "REJECTED DIAGNOSTIC TRIAL — VISUAL AND INTERSECTION REVIEW REQUIRED"
)
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24c.r3s.projection.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "changed_vertex_count": len(changed),
    "changed_zones": [20, 21],
    "maximum_requested_forward_m": 0.026,
    "topology_changed": False,
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "required": [
            "neutral front/side/three-quarter review",
            "nonadjacent self-intersection audit",
            "retained-body intersection audit",
        ],
    },
    "scope": {
        "static_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(BLEND_PATH)
print(REPORT_PATH)
print(json.dumps(report, indent=2))
