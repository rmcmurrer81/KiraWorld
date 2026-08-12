#!/usr/bin/env python3
"""Read-only R23 preflight for a localized CC0 AFES topology transfer.

Run this script only with the exact sealed R19 Blend already loaded.  It may
append the exact qualified CC0 foundation into memory for inspection, but it
does not alter the R19 mesh, create a candidate, render, export, or write a
Blend.  Its only output is one append-only JSON evidence record.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.kira_r23_cc0_afes_preflight_core import (  # noqa: E402
    boundary_edges_for_region,
    canonical_index_sha256,
    canonical_json_sha256,
    expand_face_rings,
    face_adjacency,
    ordered_boundary_cycles,
    shortest_path_union,
    topology_record,
)


DEFAULT_CONFIG = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_preparation/"
    "KIRA_R23_CC0_AFES_EXPANDED_MASK_PREFLIGHT_CONFIG.json"
)
ALLOWED_OUTPUT_ROOT = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask"
)


class R23PreflightError(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG.as_posix())
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise R23PreflightError(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise R23PreflightError(f"path escaped the project: {raw}") from exc
    return resolved


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise R23PreflightError(f"JSON root must be an object: {relative(path)}")
    return value


def verify_inputs(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    inputs = config.get("inputs")
    if not isinstance(inputs, Mapping) or not inputs:
        raise R23PreflightError("config inputs are absent")
    for name, raw in inputs.items():
        if not isinstance(raw, Mapping):
            raise R23PreflightError(f"invalid input binding: {name}")
        path = project_path(str(raw.get("path") or ""))
        expected_hash = str(raw.get("sha256") or "").lower()
        expected_bytes = int(raw.get("bytes", -1))
        if not path.is_file():
            raise R23PreflightError(f"input is missing: {relative(path)}")
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        if actual_hash != expected_hash or actual_bytes != expected_bytes:
            raise R23PreflightError(
                f"input binding mismatch: {name}: hash={actual_hash}, bytes={actual_bytes}"
            )
        records[str(name)] = {
            "path": relative(path),
            "sha256": actual_hash,
            "bytes": actual_bytes,
        }
    return records


def vector_record(value: Vector) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def bounds(points: Iterable[Vector]) -> dict[str, list[float]]:
    values = list(points)
    if not values:
        raise R23PreflightError("cannot measure empty point set")
    low = Vector(tuple(min(point[axis] for point in values) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in values) for axis in range(3)))
    return {"minimum": vector_record(low), "maximum": vector_record(high)}


def bounds_match(
    actual: Mapping[str, Sequence[float]],
    expected: Mapping[str, Sequence[float]],
    tolerance: float = 1.0e-8,
) -> bool:
    return all(
        abs(float(actual[key][axis]) - float(expected[key][axis])) <= tolerance
        for key in ("minimum", "maximum")
        for axis in range(3)
    )


def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise R23PreflightError("nonfinite material or geometry value")
        return value
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    try:
        return [json_value(item) for item in value]
    except TypeError:
        return str(value)


def faces_of(obj: bpy.types.Object) -> list[tuple[int, ...]]:
    return [tuple(int(value) for value in face.vertices) for face in obj.data.polygons]


def mesh_full_state_sha256(obj: bpy.types.Object) -> str:
    uv_layers = []
    for layer in obj.data.uv_layers:
        uv_layers.append(
            {
                "name": layer.name,
                "values": [
                    [float(item.uv.x), float(item.uv.y)] for item in layer.data
                ],
            }
        )
    groups = {int(group.index): group.name for group in obj.vertex_groups}
    weights = [
        sorted(
            [
                [groups[int(item.group)], float(item.weight)]
                for item in vertex.groups
                if float(item.weight) > 0.0
            ],
            key=lambda row: row[0],
        )
        for vertex in obj.data.vertices
    ]
    value = {
        "vertices": [vector_record(vertex.co) for vertex in obj.data.vertices],
        "faces": faces_of(obj),
        "material_indices": [int(face.material_index) for face in obj.data.polygons],
        "uv_layers": uv_layers,
        "weights": weights,
        "matrix_world": [[float(item) for item in row] for row in obj.matrix_world],
        "modifiers": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "object": getattr(getattr(modifier, "object", None), "name", None),
                "vertex_group": str(getattr(modifier, "vertex_group", "")),
            }
            for modifier in obj.modifiers
        ],
    }
    return canonical_json_sha256(value)


def weight_rows(obj: bpy.types.Object, indices: Iterable[int]) -> list[list[Any]]:
    group_names = {int(group.index): group.name for group in obj.vertex_groups}
    return [
        [
            int(index),
            sorted(
                [
                    [group_names[int(item.group)], float(item.weight)]
                    for item in obj.data.vertices[int(index)].groups
                    if float(item.weight) > 0.0
                ],
                key=lambda row: row[0],
            ),
        ]
        for index in sorted({int(value) for value in indices})
    ]


def material_graph_record(material: bpy.types.Material | None) -> dict[str, Any]:
    if material is None:
        return {"name": None, "sha256": canonical_json_sha256(None)}
    nodes: list[dict[str, Any]] = []
    links: list[list[str]] = []
    if material.use_nodes and material.node_tree is not None:
        for node in sorted(material.node_tree.nodes, key=lambda item: item.name):
            inputs = []
            for socket in node.inputs:
                if hasattr(socket, "default_value"):
                    inputs.append([socket.name, json_value(socket.default_value)])
            row = {
                "name": node.name,
                "type": node.bl_idname,
                "label": node.label,
                "inputs": inputs,
            }
            image = getattr(node, "image", None)
            if image is not None:
                image_path = Path(bpy.path.abspath(image.filepath)).resolve() if image.filepath else None
                row["image"] = {
                    "name": image.name,
                    "filepath": str(image.filepath),
                    "project_file_sha256": (
                        sha256_file(image_path)
                        if image_path is not None
                        and image_path.is_file()
                        and ROOT.resolve() in image_path.parents
                        else None
                    ),
                    "packed_bytes": (
                        len(image.packed_file.data) if image.packed_file is not None else 0
                    ),
                }
            nodes.append(row)
        links = sorted(
            [
                [
                    link.from_node.name,
                    link.from_socket.name,
                    link.to_node.name,
                    link.to_socket.name,
                ]
                for link in material.node_tree.links
            ]
        )
    payload = {
        "name": material.name,
        "use_nodes": bool(material.use_nodes),
        "blend_method": str(getattr(material, "surface_render_method", "")),
        "nodes": nodes,
        "links": links,
    }
    return {"name": material.name, "sha256": canonical_json_sha256(payload)}


def rig_rest_sha256(rig: bpy.types.Object) -> str:
    rows = []
    for bone in sorted(rig.data.bones, key=lambda item: item.name):
        rows.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "head_local": vector_record(bone.head_local),
                "tail_local": vector_record(bone.tail_local),
                "matrix_local": [
                    [float(value) for value in row] for row in bone.matrix_local
                ],
                "use_deform": bool(bone.use_deform),
            }
        )
    return canonical_json_sha256(rows)


def actions_sha256() -> str:
    rows = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        curves = []
        for curve in sorted(
            action.fcurves,
            key=lambda item: (item.data_path, int(item.array_index)),
        ):
            curves.append(
                {
                    "data_path": curve.data_path,
                    "array_index": int(curve.array_index),
                    "keyframes": [
                        [
                            float(point.co.x),
                            float(point.co.y),
                            str(point.interpolation),
                        ]
                        for point in curve.keyframe_points
                    ],
                }
            )
        rows.append({"name": action.name, "fcurves": curves})
    return canonical_json_sha256(rows)


def old_patch_record(
    body: bpy.types.Object, contract: Mapping[str, Any]
) -> tuple[set[int], set[int], list[int], dict[str, Any]]:
    faces = faces_of(body)
    slot = int(contract["old_patch_material_slot"])
    selected = {
        int(face.index)
        for face in body.data.polygons
        if int(face.material_index) == slot
    }
    topology = topology_record(faces, selected)
    boundary_edges = boundary_edges_for_region(faces, selected)
    cycles = ordered_boundary_cycles(boundary_edges)
    if len(cycles) != 1:
        raise R23PreflightError("old R19 patch is not one boundary cycle")
    cycle = cycles[0]
    vertices = {
        int(value) for face_index in selected for value in faces[face_index]
    }
    points = [body.matrix_world @ body.data.vertices[index].co for index in vertices]
    measured_bounds = bounds(points)
    material_name = (
        body.data.materials[slot].name
        if 0 <= slot < len(body.data.materials) and body.data.materials[slot]
        else None
    )
    checks = {
        "body_vertices": len(body.data.vertices) == int(contract["expected_body_vertices"]),
        "body_edges": len(body.data.edges) == int(contract["expected_body_edges"]),
        "body_faces": len(body.data.polygons) == int(contract["expected_body_faces"]),
        "material_name": material_name == contract["old_patch_material_name"],
        "patch_faces": len(selected) == int(contract["expected_old_patch_faces"]),
        "patch_vertices": len(vertices)
        == int(contract["expected_old_patch_incident_vertices"]),
        "interface_vertices": len(cycle)
        == int(contract["expected_old_patch_interface_vertices"]),
        "interface_edges": len(boundary_edges)
        == int(contract["expected_old_patch_interface_edges"]),
        "bounds": bounds_match(
            measured_bounds, contract["expected_old_patch_bounds_world_m"]
        ),
        "one_disk": topology["is_one_disk"] is True,
    }
    if not all(checks.values()):
        raise R23PreflightError(f"R19 old patch contract failed: {checks}")
    centroid = sum(points, Vector()) / len(points)
    return selected, vertices, cycle, {
        "material_slot": slot,
        "material_name": material_name,
        "topology": topology,
        "bounds_world_m": measured_bounds,
        "centroid_world_m": vector_record(centroid),
        "face_indices_sha256": canonical_index_sha256(selected),
        "incident_vertex_indices_sha256": canonical_index_sha256(vertices),
        "ordered_interface_cycle": cycle,
        "ordered_interface_cycle_sha256": canonical_json_sha256(cycle),
        "checks": checks,
    }


def verify_foundation_authority(
    config: Mapping[str, Any], inputs: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    reconciliation = config["r20_rule_reconciliation"]
    registry = read_json(project_path(inputs["adult_foundation_registry"]["path"]))
    donor_id = reconciliation["only_allowed_geometry_donor_id"]
    matches = [
        row
        for row in registry.get("entries", [])
        if isinstance(row, Mapping) and row.get("foundation_id") == donor_id
    ]
    if len(matches) != 1:
        raise R23PreflightError("qualified CC0 foundation registry entry is not unique")
    entry = matches[0]
    candidate_use = entry.get("candidate_use", {})
    license_record = entry.get("license", {})
    checks = {
        "qualified": entry.get("qualified") is True,
        "adaptable_foundation": entry.get("foundation_role") == "adaptable_foundation",
        "copy_as_candidate_body_allowed": candidate_use.get("copy_as_candidate_body_allowed")
        is True,
        "new_surface_derivative_allowed": candidate_use.get("new_surface_derivative_allowed")
        is True,
        "license": license_record.get("id") == reconciliation["license_required"],
        "adaptation_allowed": license_record.get("adaptation_allowed") is True,
        "foundation_use_allowed": license_record.get("foundation_use_allowed") is True,
        "source_hash": entry.get("source_artifact", {}).get("sha256")
        == inputs["qualified_cc0_foundation_blend"]["sha256"],
    }
    qualification = read_json(
        project_path(inputs["foundation_qualification_result"]["path"])
    )
    topology_audit = read_json(
        project_path(inputs["foundation_topology_audit"]["path"])
    )
    relationship_audit = read_json(
        project_path(inputs["foundation_relationship_audit"]["path"])
    )
    donor_contract = config["donor_contract"]
    checks.update(
        {
            "qualification_status": qualification.get("status") == "QUALIFIED_INACTIVE",
            "qualification_adult": qualification.get("adult_eligible") is True,
            "qualification_topology": qualification.get("complete_adult_topology_proven")
            is True,
            "topology_audit_passed": topology_audit.get("passed") is True,
            "topology_audit_exact_artifact": topology_audit.get("artifact_sha256")
            == inputs["qualified_cc0_foundation_blend"]["sha256"],
            "topology_audit_one_component": topology_audit.get("metrics", {}).get(
                "primary_surface_components"
            )
            == int(donor_contract["expected_primary_components"]),
            "topology_audit_zero_boundary": topology_audit.get("metrics", {}).get(
                "boundary_edges"
            )
            == int(donor_contract["expected_boundary_edges"]),
            "topology_audit_zero_nonmanifold": topology_audit.get("metrics", {}).get(
                "nonmanifold_edges"
            )
            == int(donor_contract["expected_nonmanifold_edges"]),
            "topology_audit_zero_intersections": topology_audit.get("metrics", {}).get(
                "nonadjacent_self_intersection_pairs"
            )
            == int(donor_contract["expected_exact_intersection_pairs"]),
            "relationship_audit_passed": relationship_audit.get("passed") is True,
            "relationship_audit_exact_artifact": relationship_audit.get("artifact_sha256")
            == inputs["qualified_cc0_foundation_blend"]["sha256"],
            "relationship_audit_connected": relationship_audit.get(
                "authored_landmark_union_integration", {}
            ).get("connected_to_primary_surface")
            is True,
            "relationship_audit_not_painted": relationship_audit.get(
                "authored_landmark_union_integration", {}
            ).get("not_painted_only")
            is True,
        }
    )
    if not all(checks.values()):
        raise R23PreflightError(f"qualified donor authority failed: {checks}")
    return {
        "foundation_id": donor_id,
        "registry_entry_sha256": canonical_json_sha256(entry),
        "license": license_record,
        "topology_audit_sha256": inputs["foundation_topology_audit"]["sha256"],
        "relationship_audit_sha256": inputs["foundation_relationship_audit"]["sha256"],
        "checks": checks,
        "r20_preservation": {
            "files_verified_exact": [
                inputs["preserved_r20_method_report"],
                inputs["preserved_r20_plan"],
                inputs["preserved_r20_donor_ledger"],
            ],
            "old_zero_donor_rule_retained_for_r20": True,
            "new_owner_directed_cc0_evaluation_is_r23_only": True,
            "r20_reinterpreted_or_overwritten": False,
        },
        "reference_only_or_unlicensed_geometry_loaded": False,
    }


def verify_r19_evidence_contract(
    config: Mapping[str, Any], inputs: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    contract = config["r19_contract"]
    evidence = read_json(project_path(inputs["r19_build_evidence"]["path"]))
    state = evidence.get("immutable_component_verification", {}).get(
        "immutable_mesh_states", {}
    ).get(contract["body_object"], {})
    immutable = evidence.get("immutable_component_verification", {})
    checks = {
        "geometry_uv_sha256": state.get("geometry_uv_sha256")
        == contract["geometry_uv_sha256"],
        "positive_weight_sha256": state.get("positive_weight_assignment_sha256")
        == contract["positive_weight_sha256"],
        "body_vertex_count": state.get("vertex_count")
        == int(contract["expected_body_vertices"]),
        "body_face_count": state.get("polygon_count")
        == int(contract["expected_body_faces"]),
        "rig_rest_before": immutable.get("native_rig_rest_structure_sha256_before")
        == contract["rig_rest_sha256"],
        "rig_rest_after": immutable.get("native_rig_rest_structure_sha256_after")
        == contract["rig_rest_sha256"],
        "neutral_pair_count": evidence.get("neutral_exact_self_intersection_baseline")
        == int(contract["neutral_inherited_exact_pair_count"]),
        "source_meshes_unchanged": immutable.get(
            "all_source_mesh_geometry_uv_weights_transforms_modifiers_unchanged"
        )
        is True,
    }
    if not all(checks.values()):
        raise R23PreflightError(f"R19 evidence contract failed: {checks}")
    return {
        "evidence_sha256": inputs["r19_build_evidence"]["sha256"],
        "checks": checks,
        "geometry_uv_sha256": contract["geometry_uv_sha256"],
        "positive_weight_sha256": contract["positive_weight_sha256"],
        "rig_rest_sha256": contract["rig_rest_sha256"],
        "neutral_inherited_exact_pair_count": contract[
            "neutral_inherited_exact_pair_count"
        ],
    }


def append_donor(path: Path, object_name: str) -> bpy.types.Object:
    with bpy.data.libraries.load(str(path), link=False) as (available, requested):
        if object_name not in available.objects:
            raise R23PreflightError(f"qualified donor object absent: {object_name}")
        requested.objects = [object_name]
    donor = requested.objects[0]
    if donor is None or donor.type != "MESH":
        raise R23PreflightError("qualified donor did not append as a mesh")
    collection = bpy.data.collections.new("R23_READ_ONLY_CC0_AFES_DONOR_PROBE")
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(donor)
    return donor


def donor_record(
    donor: bpy.types.Object, contract: Mapping[str, Any]
) -> tuple[set[int], set[int], list[int], dict[str, Any]]:
    if len(donor.data.vertices) != int(contract["expected_vertices"]):
        raise R23PreflightError("qualified donor vertex count drifted")
    if len(donor.data.edges) != int(contract["expected_edges"]):
        raise R23PreflightError("qualified donor edge count drifted")
    if len(donor.data.polygons) != int(contract["expected_faces"]):
        raise R23PreflightError("qualified donor face count drifted")
    groups = {int(group.index): group.name for group in donor.vertex_groups}
    required = list(contract["required_landmark_groups"])
    missing = sorted(set(required).difference(groups.values()))
    if missing:
        raise R23PreflightError(f"qualified donor AFES groups missing: {missing}")
    afes_group_indices = {
        index for index, name in groups.items() if name.startswith("AFES_LANDMARK__")
    }
    memberships: dict[str, set[int]] = {name: set() for name in required}
    union: set[int] = set()
    for vertex in donor.data.vertices:
        for item in vertex.groups:
            group_index = int(item.group)
            if group_index in afes_group_indices and float(item.weight) > 0.0:
                union.add(int(vertex.index))
            name = groups.get(group_index)
            if name in memberships and float(item.weight) > 0.0:
                memberships[name].add(int(vertex.index))
    if len(union) != int(contract["expected_landmark_union_vertices"]):
        raise R23PreflightError(
            f"qualified donor landmark union drifted: {len(union)}"
        )
    faces = faces_of(donor)
    incident = {
        index
        for index, face in enumerate(faces)
        if any(vertex in union for vertex in face)
    }
    internal = {
        index
        for index, face in enumerate(faces)
        if all(vertex in union for vertex in face)
    }
    connection_edges = {
        tuple(sorted((int(edge.vertices[0]), int(edge.vertices[1]))))
        for edge in donor.data.edges
        if (int(edge.vertices[0]) in union) != (int(edge.vertices[1]) in union)
    }
    if len(incident) != int(contract["expected_landmark_incident_faces"]):
        raise R23PreflightError(
            f"qualified donor incident-face count drifted: {len(incident)}"
        )
    if len(internal) != int(contract["expected_landmark_internal_faces"]):
        raise R23PreflightError(
            f"qualified donor internal-face count drifted: {len(internal)}"
        )
    if len(connection_edges) != int(contract["expected_primary_connection_edges"]):
        raise R23PreflightError(
            f"qualified donor connection-edge count drifted: {len(connection_edges)}"
        )
    union_bounds = bounds([donor.data.vertices[index].co for index in union])
    if not bounds_match(
        union_bounds,
        contract["expected_landmark_union_bounds_object_m"],
        tolerance=1.0e-7,
    ):
        raise R23PreflightError("qualified donor AFES union bounds drifted")
    adjacency = face_adjacency(faces)
    disk_attempts = []
    selected_disk: set[int] | None = None
    selected_rings: int | None = None
    for rings in contract["disk_search_face_rings"]:
        selected = expand_face_rings(incident, adjacency, int(rings))
        topology = topology_record(faces, selected)
        disk_attempts.append({"rings": int(rings), "topology": topology})
        if topology["is_one_disk"] is True:
            selected_disk = selected
            selected_rings = int(rings)
            break
    if selected_disk is None:
        raise R23PreflightError(
            "qualified donor AFES incident region could not be isolated as one disk"
        )
    cycles = ordered_boundary_cycles(boundary_edges_for_region(faces, selected_disk))
    cycle = cycles[0]
    armature_modifier_count = sum(
        modifier.type == "ARMATURE" for modifier in donor.modifiers
    )
    if bool(armature_modifier_count) != bool(contract["source_armature_expected"]):
        raise R23PreflightError("qualified donor armature contract drifted")
    record = {
        "object": donor.name,
        "mesh": donor.data.name,
        "whole_mesh": {
            "vertices": len(donor.data.vertices),
            "edges": len(donor.data.edges),
            "faces": len(donor.data.polygons),
            "armature_modifier_count": armature_modifier_count,
        },
        "AFES_union": {
            "vertex_count": len(union),
            "incident_face_count": len(incident),
            "internal_face_count": len(internal),
            "primary_connection_edge_count": len(connection_edges),
            "bounds_object_m": union_bounds,
            "vertex_index_sha256": canonical_index_sha256(union),
            "incident_face_index_sha256": canonical_index_sha256(incident),
            "internal_face_index_sha256": canonical_index_sha256(internal),
            "connection_edge_sha256": canonical_json_sha256(
                sorted([list(edge) for edge in connection_edges])
            ),
        },
        "groups": {
            name: {
                "vertex_count": len(values),
                "vertex_index_sha256": canonical_index_sha256(values),
            }
            for name, values in sorted(memberships.items())
        },
        "disk_search": disk_attempts,
        "selected_disk_face_rings": selected_rings,
        "selected_disk_topology": topology_record(faces, selected_disk),
        "selected_disk_face_index_sha256": canonical_index_sha256(selected_disk),
        "selected_disk_ordered_boundary": cycle,
        "selected_disk_ordered_boundary_sha256": canonical_json_sha256(cycle),
        "provenance": {
            "copy_source": "exact qualified CC0 foundation only",
            "reference_only_geometry_copied": False,
            "source_material_uv_or_weights_authorized_for_copy": False,
            "source_topology_and_AFES_memberships_only": True,
        },
    }
    return union, selected_disk, cycle, record


def normalized_axes(body: bpy.types.Object, frame: Mapping[str, Any]) -> tuple[Vector, Vector, Vector]:
    matrix = body.matrix_world.to_3x3()
    axes = []
    for name in ("lateral_axis", "longitudinal_axis", "outward_axis"):
        axis = matrix @ Vector(tuple(float(value) for value in frame[name]))
        if axis.length <= 1.0e-12:
            raise R23PreflightError(f"target frame axis collapsed: {name}")
        axes.append(axis.normalized())
    lateral, longitudinal, outward = axes
    if abs(lateral.dot(longitudinal)) > 1.0e-5 or abs(lateral.dot(outward)) > 1.0e-5:
        raise R23PreflightError("target authored frame axes are not orthogonal")
    return lateral, longitudinal, outward


def project_donor_landmarks(
    body: bpy.types.Object,
    donor: bpy.types.Object,
    donor_union: set[int],
    old_patch_vertices: set[int],
    frame_config: Mapping[str, Any],
    mask_config: Mapping[str, Any],
    required_groups: Sequence[str],
) -> tuple[set[int], dict[str, Any], dict[int, tuple[float, float, float]]]:
    frame = frame_config["frame"]
    lateral, longitudinal, outward = normalized_axes(body, frame)
    target_origin = sum(
        (body.matrix_world @ body.data.vertices[index].co for index in old_patch_vertices),
        Vector(),
    ) / len(old_patch_vertices)
    donor_origin = Vector(tuple(float(value) for value in frame["origin"]))
    donor_lateral = Vector(tuple(float(value) for value in frame["lateral_axis"])).normalized()
    donor_longitudinal = Vector(
        tuple(float(value) for value in frame["longitudinal_axis"])
    ).normalized()
    donor_outward = Vector(tuple(float(value) for value in frame["outward_axis"])).normalized()
    half_width = float(frame["half_width_m"])
    half_length = float(frame["half_length_m"])
    max_offset = float(frame["max_surface_offset_m"])
    donor_chart: dict[int, tuple[float, float, float]] = {}
    for index in donor_union:
        relative_point = donor.data.vertices[index].co - donor_origin
        donor_chart[index] = (
            float(relative_point.dot(donor_lateral) / half_width),
            float(relative_point.dot(donor_longitudinal) / half_length),
            float(relative_point.dot(donor_outward) / max_offset),
        )
    donor_abs_u = max(abs(row[0]) for row in donor_chart.values())
    old_world = [body.matrix_world @ body.data.vertices[index].co for index in old_patch_vertices]
    old_half_width = max(abs((point - target_origin).dot(lateral)) for point in old_world)
    lateral_scale = old_half_width / (half_width * donor_abs_u)
    target_half_width = half_width * lateral_scale
    target_half_length = half_length * lateral_scale
    target_max_offset = max_offset * lateral_scale
    mapped = {
        index: target_origin
        + lateral * (row[0] * target_half_width)
        + longitudinal * (row[1] * target_half_length)
        + outward * (row[2] * target_max_offset)
        for index, row in donor_chart.items()
    }
    body_world = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    body_faces = faces_of(body)
    tree = BVHTree.FromPolygons(body_world, body_faces, all_triangles=False)
    group_indices = {group.name: int(group.index) for group in donor.vertex_groups}
    vertex_groups: dict[int, set[str]] = defaultdict(set)
    for name in required_groups:
        group_index = group_indices[name]
        for vertex in donor.data.vertices:
            if any(
                int(item.group) == group_index and float(item.weight) > 0.0
                for item in vertex.groups
            ):
                vertex_groups[int(vertex.index)].add(name)
    hits: dict[int, int] = {}
    distances: dict[int, float] = {}
    per_group_faces: dict[str, set[int]] = {name: set() for name in required_groups}
    per_group_distances: dict[str, list[float]] = {name: [] for name in required_groups}
    maximum = float(mask_config["projection_maximum_distance_m"])
    for index, point in mapped.items():
        location, _normal, face_index, distance = tree.find_nearest(point, maximum)
        if location is None or face_index is None:
            continue
        hits[index] = int(face_index)
        distances[index] = float(distance)
        for name in vertex_groups.get(index, set()):
            per_group_faces[name].add(int(face_index))
            per_group_distances[name].append(float(distance))
    hit_fraction = len(hits) / len(donor_union)
    group_records = {}
    for name in required_groups:
        values = per_group_distances[name]
        group_records[name] = {
            "hit_count": len(values),
            "face_count": len(per_group_faces[name]),
            "projected_face_indices": sorted(per_group_faces[name]),
            "face_index_sha256": canonical_index_sha256(per_group_faces[name]),
            "mean_distance_m": sum(values) / len(values) if values else None,
            "maximum_distance_m": max(values) if values else None,
            "has_hits": bool(values),
        }
    if hit_fraction < float(mask_config["projection_minimum_hit_fraction"]):
        raise R23PreflightError(
            f"donor projection hit fraction too low: {hit_fraction:.6f}"
        )
    if any(not row["has_hits"] for row in group_records.values()):
        raise R23PreflightError("one or more required AFES groups had no target hit")
    hit_faces = set(hits.values())
    record = {
        "method": mask_config["mapping"],
        "global_ICP_used": False,
        "Y_only_transfer_used": False,
        "target_origin_world_m": vector_record(target_origin),
        "target_axes_world": {
            "lateral": vector_record(lateral),
            "longitudinal": vector_record(longitudinal),
            "outward": vector_record(outward),
        },
        "target_scales_m": {
            "half_width": target_half_width,
            "half_length": target_half_length,
            "maximum_outward_offset": target_max_offset,
            "uniform_scale": lateral_scale,
        },
        "donor_chart_bounds": {
            "u": [min(row[0] for row in donor_chart.values()), max(row[0] for row in donor_chart.values())],
            "v": [min(row[1] for row in donor_chart.values()), max(row[1] for row in donor_chart.values())],
            "w": [min(row[2] for row in donor_chart.values()), max(row[2] for row in donor_chart.values())],
        },
        "donor_chart_sha256": canonical_json_sha256(
            [[index, *donor_chart[index]] for index in sorted(donor_chart)]
        ),
        "mapped_position_sha256": canonical_json_sha256(
            [[index, *vector_record(mapped[index])] for index in sorted(mapped)]
        ),
        "hit_vertex_count": len(hits),
        "donor_landmark_vertex_count": len(donor_union),
        "hit_fraction": hit_fraction,
        "projected_face_count": len(hit_faces),
        "projected_face_index_sha256": canonical_index_sha256(hit_faces),
        "mean_projection_distance_m": sum(distances.values()) / len(distances),
        "maximum_projection_distance_m": max(distances.values()),
        "groups": group_records,
    }
    return hit_faces, record, donor_chart


def target_chart_coordinates(
    body: bpy.types.Object,
    projection: Mapping[str, Any],
) -> dict[int, tuple[float, float, float]]:
    origin = Vector(tuple(projection["target_origin_world_m"]))
    axes = projection["target_axes_world"]
    lateral = Vector(tuple(axes["lateral"]))
    longitudinal = Vector(tuple(axes["longitudinal"]))
    outward = Vector(tuple(axes["outward"]))
    scales = projection["target_scales_m"]
    half_width = float(scales["half_width"])
    half_length = float(scales["half_length"])
    max_offset = float(scales["maximum_outward_offset"])
    result = {}
    for face in body.data.polygons:
        world = body.matrix_world @ face.center
        delta = world - origin
        result[int(face.index)] = (
            float(delta.dot(lateral) / half_width),
            float(delta.dot(longitudinal) / half_length),
            float(delta.dot(outward) / max_offset),
        )
    return result


def expanded_mask_record(
    body: bpy.types.Object,
    old_patch: set[int],
    hit_faces: set[int],
    projection: Mapping[str, Any],
    donor_chart: Mapping[int, tuple[float, float, float]],
    mask_config: Mapping[str, Any],
) -> tuple[set[int], list[int], dict[str, Any]]:
    faces = faces_of(body)
    adjacency = face_adjacency(faces)
    old_hit_fraction = len(hit_faces.intersection(old_patch)) / max(1, len(hit_faces))
    group_old_records = {}
    minimum_old_fraction = float(mask_config["old_mask_fit_minimum_face_hit_fraction"])
    for name, row in projection["groups"].items():
        group_faces = {int(value) for value in row["projected_face_indices"]}
        fraction = len(group_faces.intersection(old_patch)) / max(1, len(group_faces))
        group_old_records[name] = {
            "projected_face_count": len(group_faces),
            "inside_old_patch_face_count": len(group_faces.intersection(old_patch)),
            "inside_old_patch_fraction": fraction,
            "passed": bool(group_faces) and fraction >= minimum_old_fraction,
        }
    old_mask_fit = (
        old_hit_fraction >= minimum_old_fraction
        and all(row["passed"] for row in group_old_records.values())
    )
    chart = target_chart_coordinates(body, projection)
    u_min = min(value[0] for value in donor_chart.values()) - float(mask_config["chart_margin_u"])
    u_max = max(value[0] for value in donor_chart.values()) + float(mask_config["chart_margin_u"])
    v_min = min(value[1] for value in donor_chart.values()) - float(mask_config["chart_margin_v"])
    v_max = max(value[1] for value in donor_chart.values()) + float(mask_config["chart_margin_v"])
    w_limit = float(mask_config["chart_maximum_abs_w"])
    allowed = {
        face_index
        for face_index, (u_value, v_value, w_value) in chart.items()
        if u_min <= u_value <= u_max
        and v_min <= v_value <= v_max
        and abs(w_value) <= w_limit
    }
    allowed.update(old_patch)
    allowed.update(hit_faces)
    path_union, target_distances = shortest_path_union(
        adjacency,
        old_patch,
        hit_faces,
        allowed=allowed,
    )
    attempts = []
    chosen: set[int] | None = None
    chosen_cycle: list[int] | None = None
    chosen_rings: int | None = None
    for rings in mask_config["expanded_mask_exterior_ring_candidates"]:
        region = expand_face_rings(path_union, adjacency, int(rings), allowed=allowed)
        topology = topology_record(faces, region)
        region_vertices = {
            int(value) for face_index in region for value in faces[face_index]
        }
        world_points = [body.matrix_world @ body.data.vertices[index].co for index in region_vertices]
        measured_bounds = bounds(world_points)
        minimum = Vector(tuple(measured_bounds["minimum"]))
        maximum = Vector(tuple(measured_bounds["maximum"]))
        extent = (maximum - minimum).length
        origin = Vector(tuple(projection["target_origin_world_m"]))
        lateral = Vector(tuple(projection["target_axes_world"]["lateral"]))
        lateral_half = max(abs((point - origin).dot(lateral)) for point in world_points)
        dominant_groups = set()
        unexpected_dominant = set()
        group_names = {int(group.index): group.name for group in body.vertex_groups}
        allowed_groups = set(mask_config["allowed_dominant_rig_groups"])
        for index in region_vertices:
            choices = sorted(
                [
                    (float(item.weight), group_names[int(item.group)])
                    for item in body.data.vertices[index].groups
                    if float(item.weight) > 0.0
                ],
                reverse=True,
            )
            if choices:
                dominant_groups.add(choices[0][1])
                if choices[0][1] not in allowed_groups:
                    unexpected_dominant.add(choices[0][1])
        gates = {
            "one_disk": topology["is_one_disk"] is True,
            "face_count_bounded": topology["face_count"]
            <= int(mask_config["maximum_expanded_mask_faces"]),
            "world_extent_bounded": extent
            <= float(mask_config["maximum_expanded_mask_world_extent_m"]),
            "lateral_half_extent_bounded": lateral_half
            <= float(mask_config["maximum_expanded_mask_lateral_half_extent_m"]),
            "outer_seam_count_bounded": int(mask_config["minimum_outer_seam_vertices"])
            <= (topology["boundary_cycle_lengths"][0] if topology["boundary_cycle_lengths"] else 0)
            <= int(mask_config["maximum_outer_seam_vertices"]),
            "old_patch_fully_contained": old_patch.issubset(region),
            "projected_hits_fully_contained": hit_faces.issubset(region),
            "dominant_rig_groups_local": not unexpected_dominant,
        }
        attempts.append(
            {
                "exterior_rings": int(rings),
                "topology": topology,
                "bounds_world_m": measured_bounds,
                "world_extent_m": extent,
                "lateral_half_extent_m": lateral_half,
                "dominant_rig_groups": sorted(dominant_groups),
                "unexpected_dominant_rig_groups": sorted(unexpected_dominant),
                "gates": gates,
            }
        )
        if all(gates.values()):
            chosen = region
            chosen_cycle = ordered_boundary_cycles(
                boundary_edges_for_region(faces, region)
            )[0]
            chosen_rings = int(rings)
            break
    if chosen is None or chosen_cycle is None:
        raise R23PreflightError("no expanded R19 mask passed the deterministic disk gates")
    return chosen, chosen_cycle, {
        "old_mask_fit": {
            "projected_hit_face_fraction_inside_old_patch": old_hit_fraction,
            "minimum_required": minimum_old_fraction,
            "per_required_AFES_group": group_old_records,
            "passed": old_mask_fit,
            "expanded_mask_was_still_computed": True,
        },
        "allowed_chart_face_count": len(allowed),
        "allowed_chart_face_index_sha256": canonical_index_sha256(allowed),
        "path_union_face_count": len(path_union),
        "path_union_face_index_sha256": canonical_index_sha256(path_union),
        "maximum_shortest_path_edges": max(target_distances.values(), default=0),
        "attempts": attempts,
        "selected_exterior_rings": chosen_rings,
        "selected_topology": topology_record(faces, chosen),
        "selected_face_index_sha256": canonical_index_sha256(chosen),
        "ordered_outer_seam": chosen_cycle,
        "ordered_outer_seam_sha256": canonical_json_sha256(chosen_cycle),
    }


def freeze_ledger(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    mask_faces: set[int],
    seam_cycle: Sequence[int],
    objects_before_donor: Sequence[bpy.types.Object],
) -> dict[str, Any]:
    faces = faces_of(body)
    mask_vertices = {
        int(value) for face_index in mask_faces for value in faces[face_index]
    }
    seam_vertices = {int(value) for value in seam_cycle}
    removable = mask_vertices.difference(seam_vertices)
    surviving = set(range(len(body.data.vertices))).difference(removable)
    outside_faces = set(range(len(faces))).difference(mask_faces)
    outside_payload = {
        "coordinates": [
            [index, *vector_record(body.data.vertices[index].co)]
            for index in sorted(surviving)
        ],
        "weights": weight_rows(body, surviving),
        "faces": [
            [index, list(faces[index]), int(body.data.polygons[index].material_index)]
            for index in sorted(outside_faces)
        ],
        "uv_layers": [
            {
                "name": layer.name,
                "outside_loops": [
                    [
                        int(face.index),
                        int(loop_index),
                        int(body.data.loops[loop_index].vertex_index),
                        float(layer.data[loop_index].uv.x),
                        float(layer.data[loop_index].uv.y),
                    ]
                    for face in body.data.polygons
                    if int(face.index) in outside_faces
                    for loop_index in face.loop_indices
                ],
            }
            for layer in body.data.uv_layers
        ],
    }
    seam_payload = [
        {
            "vertex": int(index),
            "coordinate": vector_record(body.data.vertices[int(index)].co),
            "weights": weight_rows(body, [int(index)])[0][1],
        }
        for index in seam_cycle
    ]
    nonbody_records = []
    for obj in sorted(objects_before_donor, key=lambda item: item.name):
        if obj == body or obj.type != "MESH":
            continue
        nonbody_records.append(
            {
                "object": obj.name,
                "mesh": obj.data.name,
                "full_state_sha256": mesh_full_state_sha256(obj),
            }
        )
    materials = [material_graph_record(material) for material in body.data.materials]
    return {
        "mask": {
            "face_count": len(mask_faces),
            "incident_vertex_count": len(mask_vertices),
            "removable_interior_vertex_count": len(removable),
            "outer_seam_vertex_count": len(seam_vertices),
            "face_index_sha256": canonical_index_sha256(mask_faces),
            "incident_vertex_sha256": canonical_index_sha256(mask_vertices),
            "removable_vertex_sha256": canonical_index_sha256(removable),
        },
        "surviving_primary_surface": {
            "vertex_count": len(surviving),
            "face_count": len(outside_faces),
            "vertex_index_sha256": canonical_index_sha256(surviving),
            "face_index_sha256": canonical_index_sha256(outside_faces),
            "canonical_state_sha256": canonical_json_sha256(outside_payload),
        },
        "outer_seam": {
            "ordered_vertex_count": len(seam_cycle),
            "canonical_state_sha256": canonical_json_sha256(seam_payload),
        },
        "nonbody_mesh_objects": {
            "count": len(nonbody_records),
            "records": nonbody_records,
            "ledger_sha256": canonical_json_sha256(nonbody_records),
        },
        "body_materials": {
            "count": len(materials),
            "records": materials,
            "ledger_sha256": canonical_json_sha256(materials),
        },
        "rig": {
            "object": rig.name,
            "rest_structure_sha256": rig_rest_sha256(rig),
        },
        "actions_sha256": actions_sha256(),
    }


def preflight(config: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    inputs = verify_inputs(config)
    source_path = project_path(inputs["r19_source_blend"]["path"])
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != source_path.resolve():
        raise R23PreflightError("exact R19 source Blend is not loaded")
    body = bpy.data.objects.get(config["r19_contract"]["body_object"])
    rig = bpy.data.objects.get(config["r19_contract"]["rig_object"])
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise R23PreflightError("exact R19 body or rig object is absent")
    source_hash_before = sha256_file(source_path)
    body_state_before = mesh_full_state_sha256(body)
    objects_before_donor = list(bpy.data.objects)
    r19_evidence_contract = verify_r19_evidence_contract(config, inputs)
    old_faces, old_vertices, old_cycle, old_record = old_patch_record(
        body, config["r19_contract"]
    )
    authority = verify_foundation_authority(config, inputs)
    donor_path = project_path(inputs["qualified_cc0_foundation_blend"]["path"])
    donor = append_donor(donor_path, config["donor_contract"]["object_name"])
    donor_union, donor_disk, donor_cycle, donor_evidence = donor_record(
        donor, config["donor_contract"]
    )
    body_state_after_donor_append = mesh_full_state_sha256(body)
    if body_state_after_donor_append != body_state_before:
        raise R23PreflightError("R19 body changed while appending read-only donor")
    frame_config = read_json(project_path(inputs["foundation_authoring_frame"]["path"]))
    hit_faces, projection, donor_chart = project_donor_landmarks(
        body,
        donor,
        donor_union,
        old_vertices,
        frame_config,
        config["alignment_and_mask"],
        config["donor_contract"]["required_landmark_groups"],
    )
    expanded_faces, expanded_cycle, expanded_evidence = expanded_mask_record(
        body,
        old_faces,
        hit_faces,
        projection,
        donor_chart,
        config["alignment_and_mask"],
    )
    ledger = freeze_ledger(
        body,
        rig,
        expanded_faces,
        expanded_cycle,
        objects_before_donor,
    )
    source_hash_after = sha256_file(source_path)
    body_state_after = mesh_full_state_sha256(body)
    integrity = {
        "source_blend_hash_before": source_hash_before,
        "source_blend_hash_after": source_hash_after,
        "source_blend_exact": source_hash_before == source_hash_after,
        "r19_body_state_before": body_state_before,
        "r19_body_state_after": body_state_after,
        "r19_body_exact": body_state_before == body_state_after,
        "donor_appended_in_memory_only": True,
        "candidate_created": False,
        "source_blend_written": False,
    }
    if not integrity["source_blend_exact"] or not integrity["r19_body_exact"]:
        raise R23PreflightError("read-only integrity gate failed")
    return {
        "schema_version": 1,
        "artifact_kind": "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PREFLIGHT_PASS_AUTHORING_NOT_STARTED",
        "config": {
            "path": relative(config_path),
            "sha256": sha256_file(config_path),
        },
        "verified_inputs": inputs,
        "authority_and_r20_reconciliation": authority,
        "r19_source_evidence_contract": r19_evidence_contract,
        "r19_old_patch": old_record,
        "qualified_cc0_donor": donor_evidence,
        "donor_to_r19_projection": projection,
        "expanded_r19_mask": expanded_evidence,
        "fresh_freeze_ledger": ledger,
        "future_authoring_attempts_not_run": config["bounded_future_attempts"],
        "future_authoring_gates_not_run": config[
            "future_authoring_gates_recorded_but_not_executed"
        ],
        "truth_boundary": config["truth_boundary"],
        "integrity": integrity,
        "operations": {
            "mesh_mutation_performed": False,
            "candidate_created": False,
            "blend_written": False,
            "render_performed": False,
            "export_performed": False,
            "runtime_mutation_performed": False,
            "reference_only_asset_loaded": False,
        },
        "implementation_note": {
            "donor_disk_faces_available_for_a_later_authoring_attempt": len(donor_disk),
            "donor_disk_boundary_vertices": len(donor_cycle),
            "expanded_mask_faces_available_for_a_later_authoring_attempt": len(expanded_faces),
            "expanded_mask_outer_seam_vertices": len(expanded_cycle),
            "this_preflight_does_not_authorize_or_execute_that_attempt": True,
        },
    }


def output_directory(config: Mapping[str, Any]) -> Path:
    output = config.get("output", {})
    directory = project_path(str(output.get("directory") or ""))
    allowed = project_path(ALLOWED_OUTPUT_ROOT)
    try:
        directory.relative_to(allowed)
    except ValueError as exc:
        raise R23PreflightError("output escaped the exact R23 evidence root") from exc
    if directory.exists():
        raise FileExistsError(f"append-only preflight output already exists: {relative(directory)}")
    return directory


def main() -> int:
    args = arguments()
    config_path = project_path(args.config)
    config = read_json(config_path)
    if config.get("schema") != "kira.avatar.r23_cc0_afes_expanded_mask_preflight.v1":
        raise R23PreflightError("wrong R23 preflight config schema")
    directory = output_directory(config)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        report = preflight(config, config_path)
        filename = str(config["output"]["pass_file"])
        result = 0
    except Exception as exc:  # evidence must survive a bounded no-go
        source_binding = config.get("inputs", {}).get("r19_source_blend", {})
        source_path = project_path(str(source_binding.get("path") or ""))
        report = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT_FAILURE",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PREFLIGHT_NO_GO_NO_CANDIDATE",
            "config": {
                "path": relative(config_path),
                "sha256": sha256_file(config_path),
            },
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "source_blend": {
                "path": relative(source_path) if source_path.is_file() else str(source_path),
                "sha256_after": sha256_file(source_path) if source_path.is_file() else None,
                "expected_sha256": source_binding.get("sha256"),
            },
            "operations": {
                "candidate_created": False,
                "blend_written": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "reference_only_asset_loaded": False,
            },
        }
        filename = str(config["output"]["failure_file"])
        result = 2
    evidence_path = directory / filename
    if evidence_path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {relative(evidence_path)}")
    evidence_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "evidence": relative(evidence_path),
                "sha256": sha256_file(evidence_path),
                "candidate_created": False,
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
