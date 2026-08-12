#!/usr/bin/env python3
"""Reopen and verify Kira R7's inactive same-mesh lip candidate.

This worker is intentionally read-only.  It never saves the loaded Blend file,
exports a model, touches runtime state, or changes an avatar binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import bpy


HIDDEN_VERTEX_COUNT = 207
HIDDEN_INDEX_SHA256 = (
    "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b"
)
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
    "KW_VISIBLE_LIP_OPEN_REVIEW",
    "KW_VISEME_O_REVIEW",
]
TRIAL_KEYS = EXPECTED_SHAPE_KEYS[-2:]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def index_sha256(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in sorted(indices):
        digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    components: list[list[int]] = []
    while remaining:
        seed = min(remaining)
        stack = [seed]
        found: set[int] = set()
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(adjacency[current] - found)
        remaining -= found
        components.append(sorted(found))
    return components


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("kw_trial_status") == "inactive_owner_review_only"
    ]
    if len(bodies) != 1:
        raise ValueError(f"expected one inactive lip trial body, found {len(bodies)}")
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
        raise ValueError(f"reopened candidate topology mismatch: {topology}")

    hidden_matches = [
        component
        for component in connected_components(mesh)
        if len(component) == HIDDEN_VERTEX_COUNT
        and index_sha256(component) == HIDDEN_INDEX_SHA256
    ]
    if len(hidden_matches) != 1:
        raise ValueError(f"expected one exact hidden backing component, got {len(hidden_matches)}")
    hidden = hidden_matches[0]

    if mesh.shape_keys is None:
        raise ValueError("reopened candidate has no shape keys")
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
        shape_key_records.append(
            {
                "name": name,
                "value_on_reopen": float(key.value),
                "moved_vertex_count": len(moved),
                "moved_vertex_index_sha256": index_sha256(moved),
                "hidden_backing_maximum_displacement_m": float(hidden_maximum),
            }
        )

    report = {
        "schema_version": 1,
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
            "vertex_index_sha256": index_sha256(hidden),
            "unchanged_in_every_trial_key": all(
                record["hidden_backing_maximum_displacement_m"] == 0.0
                for record in shape_key_records
            ),
        },
        "saved_candidate_policy": {
            "inactive_owner_review_only": body.get("kw_trial_status")
            == "inactive_owner_review_only",
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
