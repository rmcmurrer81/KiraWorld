#!/usr/bin/env python3
"""Read-only reopen verification for Kira's inactive five-viseme candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bpy

import blender_author_kira_r7_visible_lip_visemes as base


EXPECTED_TOPOLOGY = {
    "vertices": 57745,
    "edges": 165776,
    "polygons": 108080,
    "objects": 4,
    "mesh_objects": 3,
}
EXPECTED_SHAPE_KEYS = [
    "Basis",
    "Kira_Adult_External_Form_R6",
    "KW_VISEME_AH_OPEN_REVIEW",
    "KW_VISEME_EE_REVIEW",
    "KW_VISEME_O_REVIEW",
    "KW_VISEME_MBP_REVIEW",
    "KW_VISEME_FV_REVIEW",
]
TRIAL_KEYS = EXPECTED_SHAPE_KEYS[2:]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.get("kw_trial_status") == "inactive_owner_review_only"
        and obj.get("kw_trial_version") == "r7_visible_lip_viseme_v2"
    ]
    if len(bodies) != 1:
        raise ValueError(f"expected one inactive v2 lip body, found {len(bodies)}")
    body = bodies[0]
    mesh = body.data
    mesh.update()
    topology = {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "objects": len(bpy.data.objects),
        "mesh_objects": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
    }
    if topology != EXPECTED_TOPOLOGY:
        raise ValueError(f"reopened topology mismatch: {topology}")

    hidden_matches = [
        component
        for component in base.connected_components(mesh)
        if len(component) == base.HIDDEN_VERTEX_COUNT
        and base.index_sha256(component) == base.HIDDEN_INDEX_SHA256
    ]
    if len(hidden_matches) != 1:
        raise ValueError(f"expected exact protected backing, got {len(hidden_matches)}")
    hidden = hidden_matches[0]

    if mesh.shape_keys is None:
        raise ValueError("candidate has no shape keys")
    keys = mesh.shape_keys.key_blocks
    names = [key.name for key in keys]
    if names != EXPECTED_SHAPE_KEYS:
        raise ValueError(f"unexpected shape-key stack: {names}")
    basis = keys["Basis"]
    shape_key_records = []
    for name in TRIAL_KEYS:
        key = keys[name]
        moved = [
            index
            for index in range(len(mesh.vertices))
            if (key.data[index].co - basis.data[index].co).length > 1e-10
        ]
        hidden_maximum = max(
            (key.data[index].co - basis.data[index].co).length for index in hidden
        )
        shape_key_records.append({
            "name": name,
            "value_on_reopen": float(key.value),
            "moved_vertex_count": len(moved),
            "moved_vertex_index_sha256": base.index_sha256(moved),
            "hidden_backing_maximum_displacement_m": float(hidden_maximum),
        })

    report = {
        "schema_version": 2,
        "mode": "read_only_reopen_verification",
        "loaded_candidate": str(Path(bpy.data.filepath).resolve()),
        "body_object": body.name,
        "body_mesh": mesh.name,
        "topology": topology,
        "topology_matches_pinned_r7": topology == EXPECTED_TOPOLOGY,
        "shape_key_names": names,
        "shape_keys": shape_key_records,
        "hidden_backing": {
            "vertex_count": len(hidden),
            "vertex_index_sha256": base.index_sha256(hidden),
            "unchanged_in_every_trial_key": all(
                record["hidden_backing_maximum_displacement_m"] == 0.0
                for record in shape_key_records
            ),
        },
        "saved_candidate_policy": {
            "inactive_owner_review_only": body.get("kw_trial_status") == "inactive_owner_review_only",
            "version": body.get("kw_trial_version"),
            "second_mouth_created": bool(body.get("kw_second_mouth_created")),
            "runtime_export_allowed": bool(body.get("kw_runtime_export_allowed")),
        },
        "safety": {
            "blend_saved": False,
            "model_exported": False,
            "runtime_binding_touched": False,
            "activation_attempted": False,
        },
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
