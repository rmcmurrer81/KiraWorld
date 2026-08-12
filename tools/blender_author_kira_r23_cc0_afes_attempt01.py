#!/usr/bin/env python3
"""Prepared bounded R23 CC0-AFES author Attempt 01.

This file is intentionally inert unless ``--execute-authoring`` is supplied.
It reproduces the passed Attempt 04 preflight, replaces only the exact selected
two-ring disk, uses the qualified donor solely as a structural chart, adds two
generated transition collars plus bounded clinically ordered relief, assigns
only R19-native weights, and saves only an inactive private candidate.

Preparation of this worker is not authorization to run it.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as preflight_base  # noqa: E402
from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask_attempt03 as preflight03  # noqa: E402
from tools.kira_r23_blender51_action_serializer import actions_sha256  # noqa: E402
from tools.kira_r23_cc0_afes_author_core import (  # noqa: E402
    align_cycle,
    barycentric_weights,
    blend_feathered_scalar_field,
    blend_feathered_vector_field,
    clinical_longitudinal_order_checks,
    collar_point,
    cycle_parameters,
    feathered_influences,
    matching_cycle_triangles,
    maximum_adjacent_delta,
    sample_cycle,
    top_four_normalized,
    zipper_bridge_parameterized,
)


DEFAULT_CONFIG = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt01_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT01_CONFIG.json"
)


class R23AuthorError(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG.as_posix())
    parser.add_argument("--execute-authoring", action="store_true")
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise R23AuthorError(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise R23AuthorError(f"path escaped project: {raw}") from exc
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
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_inputs(config: Mapping[str, Any]) -> dict[str, Any]:
    result = {}
    for name, binding in config["inputs"].items():
        path = project_path(binding["path"])
        if not path.is_file():
            raise R23AuthorError(f"missing input {name}: {relative(path)}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != int(binding["bytes"]) or digest != binding["sha256"]:
            raise R23AuthorError(
                f"input binding drifted for {name}: bytes={size}, sha256={digest}"
            )
        result[name] = {"path": relative(path), "bytes": size, "sha256": digest}
    return result


def output_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    output = config["output"]
    directory = project_path(output["directory"])
    if directory.exists():
        raise FileExistsError(f"append-only author output exists: {relative(directory)}")
    return {
        "directory": directory,
        "candidate": directory / output["candidate_blend"],
        "evidence": directory / output["build_evidence"],
        "failure": directory / output["failure_evidence"],
    }


def reproduce_passed_preflight(
    config: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base_config_path = project_path(
        config["inputs"]["sealed_base_preflight_config"]["path"]
    )
    sealed = read_json(base_config_path)
    effective = deepcopy(sealed)
    effective["alignment_and_mask"]["maximum_expanded_mask_world_extent_m"] = (
        config["selected_target_mask"]["maximum_world_extent_m"]
    )
    differences = preflight03.leaf_differences(sealed, effective)
    if differences != [
        {
            "path": "alignment_and_mask.maximum_expanded_mask_world_extent_m",
            "before": 0.38,
            "after": 0.4,
        }
    ]:
        raise R23AuthorError(f"effective preflight config drifted: {differences}")
    original_hasher = preflight_base.actions_sha256
    preflight_base.actions_sha256 = lambda: actions_sha256(bpy.data.actions)
    try:
        report, captured = preflight03.run_base_with_selected_mask_capture(
            effective, base_config_path
        )
    finally:
        preflight_base.actions_sha256 = original_hasher
    sealed_report = read_json(
        project_path(config["inputs"]["passed_attempt04_preflight"]["path"])
    )
    for key in (
        "r19_old_patch",
        "qualified_cc0_donor",
        "donor_to_r19_projection",
        "expanded_r19_mask",
        "fresh_freeze_ledger",
        "integrity",
    ):
        if canonical_sha256(report[key]) != canonical_sha256(sealed_report[key]):
            raise R23AuthorError(f"reproduced preflight section drifted: {key}")
    selected_faces = {int(value) for value in captured.get("chosen", set())}
    selected_cycle = [int(value) for value in captured.get("chosen_cycle", [])]
    selected = config["selected_target_mask"]
    if (
        preflight_base.canonical_index_sha256(selected_faces)
        != selected["face_index_sha256"]
        or preflight_base.canonical_json_sha256(selected_cycle)
        != selected["ordered_outer_seam_sha256"]
    ):
        raise R23AuthorError("reproduced exact target mask or seam drifted")
    return report, captured, effective


def donor_memberships(donor: bpy.types.Object) -> dict[str, set[int]]:
    groups = {int(group.index): group.name for group in donor.vertex_groups}
    result: dict[str, set[int]] = defaultdict(set)
    for vertex in donor.data.vertices:
        for item in vertex.groups:
            if float(item.weight) <= 0.0:
                continue
            name = groups[int(item.group)]
            if name.startswith("AFES_LANDMARK__"):
                result[name].add(int(vertex.index))
    return dict(result)


def exact_donor_disk(
    donor: bpy.types.Object,
    preflight: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[set[int], set[int], list[int], dict[str, set[int]]]:
    memberships = donor_memberships(donor)
    union = set().union(*memberships.values())
    faces = preflight_base.faces_of(donor)
    disk = {
        index
        for index, face in enumerate(faces)
        if any(vertex in union for vertex in face)
    }
    vertices = {vertex for face in disk for vertex in faces[face]}
    cycles = preflight_base.ordered_boundary_cycles(
        preflight_base.boundary_edges_for_region(faces, disk)
    )
    if len(cycles) != 1:
        raise R23AuthorError("qualified donor disk lost its one boundary")
    cycle = cycles[0]
    contract = config["qualified_donor_disk"]
    checks = {
        "face_count": len(disk) == contract["face_count"],
        "vertex_count": len(vertices) == contract["vertex_count"],
        "boundary_count": len(cycle) == contract["outer_boundary_vertices"],
        "face_hash": preflight_base.canonical_index_sha256(disk)
        == contract["face_index_sha256"],
        "vertex_hash": preflight_base.canonical_index_sha256(vertices)
        == contract["vertex_index_sha256"],
        "boundary_hash": preflight_base.canonical_json_sha256(cycle)
        == contract["ordered_boundary_sha256"],
    }
    if not all(checks.values()):
        raise R23AuthorError(f"qualified donor disk drifted: {checks}")
    if canonical_sha256(preflight["qualified_cc0_donor"]["groups"]) != canonical_sha256(
        read_json(project_path(config["inputs"]["passed_attempt04_preflight"]["path"]))[
            "qualified_cc0_donor"
        ]["groups"]
    ):
        raise R23AuthorError("qualified donor membership hashes drifted")
    return disk, vertices, cycle, memberships


def map_and_relieve_donor(
    donor: bpy.types.Object,
    donor_disk: set[int],
    donor_vertices: set[int],
    memberships: Mapping[str, set[int]],
    projection: Mapping[str, Any],
    frame: Mapping[str, Any],
    relief: Mapping[str, Any],
) -> tuple[
    dict[int, Vector],
    dict[int, tuple[float, float, float]],
    dict[int, tuple[float, float, float]],
    dict[str, Any],
]:
    donor_origin = Vector(tuple(frame["origin"]))
    dl = Vector(tuple(frame["lateral_axis"])).normalized()
    dv = Vector(tuple(frame["longitudinal_axis"])).normalized()
    dw = Vector(tuple(frame["outward_axis"])).normalized()
    half_width = float(frame["half_width_m"])
    half_length = float(frame["half_length_m"])
    max_offset = float(frame["max_surface_offset_m"])
    target_origin = Vector(tuple(projection["target_origin_world_m"]))
    tl = Vector(tuple(projection["target_axes_world"]["lateral"]))
    tv = Vector(tuple(projection["target_axes_world"]["longitudinal"]))
    tw = Vector(tuple(projection["target_axes_world"]["outward"]))
    scales = projection["target_scales_m"]
    chart = {}
    points = {}
    priorities = list(relief["priority_order"])
    displacements = relief["relief_m_by_group"]
    for index in sorted(donor_vertices):
        delta = donor.data.vertices[index].co - donor_origin
        uvw = (
            float(delta.dot(dl) / half_width),
            float(delta.dot(dv) / half_length),
            float(delta.dot(dw) / max_offset),
        )
        chart[index] = uvw

    donor_faces = preflight_base.faces_of(donor)
    adjacency: dict[int, set[int]] = {
        int(index): set() for index in donor_vertices
    }
    for face_index in sorted(donor_disk):
        face = donor_faces[face_index]
        for offset, vertex in enumerate(face):
            neighbor = face[(offset + 1) % len(face)]
            if vertex in adjacency and neighbor in adjacency:
                adjacency[int(vertex)].add(int(neighbor))
                adjacency[int(neighbor)].add(int(vertex))
    if any(not neighbors for neighbors in adjacency.values()):
        raise R23AuthorError("qualified donor disk contains an isolated vertex")
    influence_fields = feathered_influences(
        adjacency,
        memberships,
        priorities,
        int(relief["feather_rings"]),
    )
    relief_values = blend_feathered_scalar_field(
        donor_vertices,
        influence_fields,
        priorities,
        displacements,
        0.0,
    )
    tint_values = blend_feathered_vector_field(
        donor_vertices,
        influence_fields,
        priorities,
        relief["tint_rgb_by_group"],
        relief["base_tint_rgb"],
    )
    tint_min = tuple(
        float(value)
        for value in relief["material_tint_limits_linear_rgba"]["minimum_rgb"]
    )
    tint_max = tuple(
        float(value)
        for value in relief["material_tint_limits_linear_rgba"]["maximum_rgb"]
    )
    tint_values = {
        index: tuple(
            min(tint_max[axis], max(tint_min[axis], float(color[axis])))
            for axis in range(3)
        )
        for index, color in tint_values.items()
    }
    maximum_relief_edge_delta = maximum_adjacent_delta(adjacency, relief_values)
    maximum_tint_edge_delta = maximum_adjacent_delta(adjacency, tint_values)
    if maximum_relief_edge_delta > float(relief["maximum_adjacent_relief_delta_m"]):
        raise R23AuthorError(
            "feathered relief exceeds the adjacent-edge continuity gate"
        )
    if maximum_tint_edge_delta > float(relief["maximum_adjacent_tint_rgb_distance"]):
        raise R23AuthorError("feathered tint exceeds the adjacent-edge continuity gate")

    for index in sorted(donor_vertices):
        uvw = chart[index]
        mapped = (
            target_origin
            + tl * (uvw[0] * float(scales["half_width"]))
            + tv * (uvw[1] * float(scales["half_length"]))
            + tw * (uvw[2] * float(scales["maximum_outward_offset"]))
        )
        value = float(relief_values[index])
        value = min(float(relief["maximum_relief_m"]), max(float(relief["minimum_relief_m"]), value))
        if abs(value) > float(relief["maximum_absolute_additional_relief_m"]):
            raise R23AuthorError("bounded clinical relief exceeded its hard limit")
        points[index] = mapped + tw * value
        relief_values[index] = value
    centroid_v = {}
    for name, values in memberships.items():
        present = [chart[index][1] for index in values if index in chart]
        if present:
            centroid_v[name] = sum(present) / len(present)
    clinical_checks = clinical_longitudinal_order_checks(
        centroid_v, float(relief["minimum_longitudinal_separation_chart"])
    )
    if not all(clinical_checks.values()):
        raise R23AuthorError(
            f"qualified structural chart violates clinical landmark order: {clinical_checks}"
        )
    return points, chart, tint_values, {
        "method": "qualified_structural_chart_plus_topology_distance_feathered_clinically_ordered_relief_and_tint",
        "feather_rings": int(relief["feather_rings"]),
        "relief_value_sha256": canonical_sha256(
            [[index, relief_values[index]] for index in sorted(relief_values)]
        ),
        "influence_fields_sha256": canonical_sha256(
            {
                name: [[index, field[index]] for index in sorted(field)]
                for name, field in sorted(influence_fields.items())
            }
        ),
        "tint_value_sha256": canonical_sha256(
            [[index, tint_values[index]] for index in sorted(tint_values)]
        ),
        "minimum_relief_m": min(relief_values.values()),
        "maximum_relief_m": max(relief_values.values()),
        "maximum_adjacent_relief_delta_m": maximum_relief_edge_delta,
        "maximum_adjacent_relief_delta_gate_m": float(
            relief["maximum_adjacent_relief_delta_m"]
        ),
        "maximum_adjacent_tint_rgb_distance": maximum_tint_edge_delta,
        "maximum_adjacent_tint_rgb_distance_gate": float(
            relief["maximum_adjacent_tint_rgb_distance"]
        ),
        "topology_distance_feathering_passed": True,
        "landmark_centroid_longitudinal_chart": dict(sorted(centroid_v.items())),
        "clinical_longitudinal_order_checks": clinical_checks,
        "clinical_longitudinal_order_passed": all(clinical_checks.values()),
        "source_chart_order_preserved_by_outward_only_relief": True,
        "donor_visual_form_accepted_without_relief": False,
        "forbidden_visual_forms_not_claimed_as_machine_proven": relief[
            "forbidden_visual_forms"
        ],
    }


def source_weights(body: bpy.types.Object, vertex_index: int) -> dict[str, float]:
    names = {int(group.index): group.name for group in body.vertex_groups}
    return {
        names[int(item.group)]: float(item.weight)
        for item in body.data.vertices[int(vertex_index)].groups
        if float(item.weight) > 0.0
    }


def weight_interpolator(
    body: bpy.types.Object, selected_faces: set[int]
) -> tuple[Any, list[int], list[Vector], list[tuple[int, ...]]]:
    world_vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    face_indices = sorted(selected_faces)
    polygons = [tuple(int(value) for value in body.data.polygons[index].vertices) for index in face_indices]
    tree = BVHTree.FromPolygons(world_vertices, polygons, all_triangles=False)
    return tree, face_indices, world_vertices, polygons


def interpolated_native_weights(
    body: bpy.types.Object,
    point: Vector,
    interpolator: tuple[Any, list[int], list[Vector], list[tuple[int, ...]]],
) -> tuple[dict[str, float], float]:
    tree, _face_indices, world_vertices, polygons = interpolator
    location, _normal, local_face_index, distance = tree.find_nearest(point, 0.08)
    if location is None or local_face_index is None:
        raise R23AuthorError("new patch vertex lacks a bounded R19 weight source")
    face = polygons[int(local_face_index)]
    if len(face) != 3:
        raise R23AuthorError("R19 selected weight source is no longer triangular")
    bary = barycentric_weights(
        tuple(location),
        tuple(world_vertices[face[0]]),
        tuple(world_vertices[face[1]]),
        tuple(world_vertices[face[2]]),
    )
    combined: dict[str, float] = defaultdict(float)
    for coefficient, index in zip(bary, face):
        for name, weight in source_weights(body, index).items():
            combined[name] += float(coefficient) * float(weight)
    return top_four_normalized(dict(combined)), float(distance)


def mean_removed_patch_uvs(
    body: bpy.types.Object, selected_faces: set[int]
) -> tuple[dict[str, dict[int, tuple[float, float]]], dict[str, list[float]]]:
    result = {}
    bounds = {}
    for layer in body.data.uv_layers:
        samples: dict[int, list[tuple[float, float]]] = defaultdict(list)
        for face_index in selected_faces:
            face = body.data.polygons[face_index]
            for loop_index in face.loop_indices:
                vertex = int(body.data.loops[loop_index].vertex_index)
                uv = layer.data[loop_index].uv
                samples[vertex].append((float(uv.x), float(uv.y)))
        means = {
            index: (
                sum(value[0] for value in values) / len(values),
                sum(value[1] for value in values) / len(values),
            )
            for index, values in samples.items()
        }
        result[layer.name] = means
        all_values = list(means.values())
        bounds[layer.name] = [
            min(value[0] for value in all_values),
            max(value[0] for value in all_values),
            min(value[1] for value in all_values),
            max(value[1] for value in all_values),
        ]
    return result, bounds


def prepare_patch(
    body: bpy.types.Object,
    donor: bpy.types.Object,
    selected_faces: set[int],
    target_cycle: list[int],
    donor_disk: set[int],
    donor_vertices: set[int],
    donor_cycle: list[int],
    memberships: Mapping[str, set[int]],
    preflight: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    frame_config = read_json(
        project_path(
            read_json(project_path(config["inputs"]["sealed_base_preflight_config"]["path"]))[
                "inputs"
            ]["foundation_authoring_frame"]["path"]
        )
    )
    mapped, donor_chart, donor_tint, relief_evidence = map_and_relieve_donor(
        donor,
        donor_disk,
        donor_vertices,
        memberships,
        preflight["donor_to_r19_projection"],
        frame_config["frame"],
        config["bounded_clinical_relief"],
    )
    target_world = [body.matrix_world @ body.data.vertices[index].co for index in target_cycle]
    aligned_cycle, alignment = align_cycle(
        [tuple(value) for value in target_world], donor_cycle, {index: tuple(mapped[index]) for index in donor_cycle}
    )
    target_parameters = cycle_parameters([tuple(value) for value in target_world])
    donor_boundary_world = [mapped[index] for index in aligned_cycle]
    donor_parameters = cycle_parameters([tuple(value) for value in donor_boundary_world])
    sampled_target_world = [
        Vector(sample_cycle([tuple(value) for value in target_world], target_parameters, fraction))
        for fraction in donor_parameters
    ]
    collar1_world = [
        Vector(collar_point(tuple(outer), tuple(inner), 1.0 / 3.0))
        for outer, inner in zip(sampled_target_world, donor_boundary_world)
    ]
    collar2_world = [
        Vector(collar_point(tuple(outer), tuple(inner), 2.0 / 3.0))
        for outer, inner in zip(sampled_target_world, donor_boundary_world)
    ]
    donor_order = sorted(donor_vertices)
    local_target = list(range(len(target_cycle)))
    collar1_start = len(local_target)
    local_collar1 = list(range(collar1_start, collar1_start + len(aligned_cycle)))
    collar2_start = local_collar1[-1] + 1
    local_collar2 = list(range(collar2_start, collar2_start + len(aligned_cycle)))
    donor_start = local_collar2[-1] + 1
    donor_to_local = {index: donor_start + offset for offset, index in enumerate(donor_order)}
    local_donor_boundary = [donor_to_local[index] for index in aligned_cycle]
    target_world_positions = list(target_world)
    all_world = target_world_positions + collar1_world + collar2_world + [mapped[index] for index in donor_order]
    faces = []
    faces.extend(
        zipper_bridge_parameterized(local_target, target_parameters, local_collar1, donor_parameters)
    )
    faces.extend(matching_cycle_triangles(local_collar1, local_collar2))
    faces.extend(matching_cycle_triangles(local_collar2, local_donor_boundary))
    donor_faces = preflight_base.faces_of(donor)
    faces.extend(tuple(donor_to_local[index] for index in donor_faces[face]) for face in sorted(donor_disk))
    outward = Vector(tuple(preflight["donor_to_r19_projection"]["target_axes_world"]["outward"]))
    normal_sum = Vector()
    for face in faces:
        if len(face) < 3:
            continue
        normal_sum += (all_world[face[1]] - all_world[face[0]]).cross(
            all_world[face[2]] - all_world[face[0]]
        )
    winding_reversed = normal_sum.dot(outward) < 0.0
    if winding_reversed:
        faces = [tuple(reversed(face)) for face in faces]
    expected = config["expected_structural_result"]
    if len(all_world) != expected["replacement_patch_vertices"] or len(faces) != expected["replacement_patch_faces"]:
        raise R23AuthorError("prepared replacement patch counts drifted")

    interpolator = weight_interpolator(body, selected_faces)
    new_weights = {}
    maximum_weight_distance = 0.0
    for local_index in range(len(target_cycle), len(all_world)):
        record, distance = interpolated_native_weights(body, all_world[local_index], interpolator)
        new_weights[local_index] = record
        maximum_weight_distance = max(maximum_weight_distance, distance)

    seam_uv, uv_bounds = mean_removed_patch_uvs(body, selected_faces)
    uv_fields = {}
    inverse = body.matrix_world.inverted()
    positions_local = [tuple(inverse @ point) for point in all_world]
    projection = preflight["donor_to_r19_projection"]
    origin = Vector(tuple(projection["target_origin_world_m"]))
    lateral = Vector(tuple(projection["target_axes_world"]["lateral"]))
    longitudinal = Vector(tuple(projection["target_axes_world"]["longitudinal"]))
    half_width = float(projection["target_scales_m"]["half_width"])
    half_length = float(projection["target_scales_m"]["half_length"])
    for layer_name, values in seam_uv.items():
        u0, u1, v0, v1 = uv_bounds[layer_name]
        field = []
        for local_index, point in enumerate(all_world):
            if local_index < len(target_cycle):
                field.append(values[target_cycle[local_index]])
                continue
            delta = point - origin
            u = min(
                1.0,
                max(
                    0.0,
                    0.5
                    + 0.5
                    * float(delta.dot(lateral) / max(half_width, 1.0e-12)),
                ),
            )
            v = min(
                1.0,
                max(
                    0.0,
                    0.5
                    + 0.5
                    * float(delta.dot(longitudinal) / max(half_length, 1.0e-12)),
                ),
            )
            field.append((u0 + (u1 - u0) * u, v0 + (v1 - v0) * v))
        uv_fields[layer_name] = field

    base_tint = tuple(
        float(value)
        for value in config["bounded_clinical_relief"]["base_tint_rgb"]
    )
    donor_boundary_tint = [donor_tint[index] for index in aligned_cycle]
    collar1_tint = [
        collar_point(base_tint, color, 1.0 / 3.0)
        for color in donor_boundary_tint
    ]
    collar2_tint = [
        collar_point(base_tint, color, 2.0 / 3.0)
        for color in donor_boundary_tint
    ]
    tint_rgb = (
        [base_tint for _index in target_cycle]
        + collar1_tint
        + collar2_tint
        + [donor_tint[index] for index in donor_order]
    )
    tint = [tuple(float(value) for value in color) + (1.0,) for color in tint_rgb]
    return {
        "positions_body_local": positions_local,
        "positions_world": [tuple(point) for point in all_world],
        "faces": faces,
        "target_seam_count": len(target_cycle),
        "collar_ring_count": 2,
        "collar_ring_size": len(aligned_cycle),
        "donor_start": donor_start,
        "donor_vertex_order": donor_order,
        "donor_boundary_order": aligned_cycle,
        "alignment": alignment,
        "winding_reversed": winding_reversed,
        "new_weights": new_weights,
        "maximum_weight_source_distance_m": maximum_weight_distance,
        "uv_fields": uv_fields,
        "tint_rgba": tint,
        "relief_evidence": relief_evidence,
        "topology_sha256": canonical_sha256([list(face) for face in faces]),
        "position_sha256": canonical_sha256(positions_local),
        "weight_sha256": canonical_sha256(new_weights),
        "uv_sha256": canonical_sha256(uv_fields),
        "tint_sha256": canonical_sha256(tint),
    }


def bmesh_frozen_snapshot(
    bm: bmesh.types.BMesh,
    vertex_id_layer: Any,
    face_id_layer: Any,
    loop_id_layer: Any,
    removable_original_vertices: set[int],
    selected_original_faces: set[int],
    group_names: Mapping[int, str],
) -> str:
    deform = bm.verts.layers.deform.active
    vertices = []
    for vertex in bm.verts:
        original = int(vertex[vertex_id_layer])
        if original < 0 or original in removable_original_vertices:
            continue
        weights = []
        if deform is not None:
            weights = sorted(
                [group_names[int(index)], float(weight)]
                for index, weight in vertex[deform].items()
                if float(weight) > 0.0
            )
        vertices.append([original, *preflight_base.vector_record(vertex.co), weights])
    faces = []
    loops = []
    uv_layers = [
        (name, bm.loops.layers.uv.get(name)) for name in bm.loops.layers.uv.keys()
    ]
    for face in bm.faces:
        original_face = int(face[face_id_layer])
        if original_face < 0 or original_face in selected_original_faces:
            continue
        faces.append(
            [
                original_face,
                [int(loop.vert[vertex_id_layer]) for loop in face.loops],
                int(face.material_index),
            ]
        )
        for loop in face.loops:
            loops.append(
                [
                    int(loop[loop_id_layer]),
                    original_face,
                    int(loop.vert[vertex_id_layer]),
                    [
                        [name, float(loop[layer].uv.x), float(loop[layer].uv.y)]
                        for name, layer in uv_layers
                    ],
                ]
            )
    return canonical_sha256(
        {
            "vertices": sorted(vertices),
            "faces": sorted(faces),
            "loops": sorted(loops),
        }
    )


def make_tint_material(body: bpy.types.Object) -> tuple[bpy.types.Material, int]:
    source = body.data.materials[0]
    if source is None:
        raise R23AuthorError("body lacks a skin-derived source material")
    material = source.copy()
    material.name = "Kira_R23_AFES_SkinDerived_BoundedTint"
    material["r23_skin_derived"] = True
    material["r23_no_dark_cavity"] = True
    if material.use_nodes and material.node_tree is not None:
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
        if principled is not None:
            base_color = principled.inputs.get("Base Color")
            tint_node = nodes.new("ShaderNodeVertexColor")
            tint_node.name = "R23_AFES_BoundedTint_Attribute"
            tint_node.layer_name = "R23_AFES_Tint"
            mix = nodes.new("ShaderNodeMixRGB")
            mix.name = "R23_AFES_BoundedTint_Mix"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 0.28
            if base_color is not None:
                prior = base_color.links[0].from_socket if base_color.is_linked else None
                if prior is not None:
                    links.remove(base_color.links[0])
                    links.new(prior, mix.inputs[1])
                else:
                    mix.inputs[1].default_value = base_color.default_value
                links.new(tint_node.outputs["Color"], mix.inputs[2])
                links.new(mix.outputs["Color"], base_color)
    body.data.materials.append(material)
    return material, len(body.data.materials) - 1


def apply_patch(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    selected_faces: set[int],
    target_cycle: list[int],
    prepared: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    selected_vertices = {
        int(value)
        for face in selected_faces
        for value in body.data.polygons[face].vertices
    }
    seam = set(target_cycle)
    removable = selected_vertices.difference(seam)
    if len(removable) != config["selected_target_mask"]["removable_interior_vertex_count"]:
        raise R23AuthorError("exact removable target vertex set drifted")
    material, material_index = make_tint_material(body)
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        vertex_id = bm.verts.layers.int.new("__R23_ORIGINAL_VERTEX_ID_TRANSIENT")
        face_id = bm.faces.layers.int.new("__R23_ORIGINAL_FACE_ID_TRANSIENT")
        loop_id = bm.loops.layers.int.new("__R23_ORIGINAL_LOOP_ID_TRANSIENT")
        local_id = bm.verts.layers.int.new("__R23_LOCAL_PATCH_ID_TRANSIENT")
        for vertex in bm.verts:
            vertex[vertex_id] = int(vertex.index)
            vertex[local_id] = -1
        original_loop_counter = 0
        for face in bm.faces:
            face[face_id] = int(face.index)
            for loop in face.loops:
                loop[loop_id] = original_loop_counter
                original_loop_counter += 1
        group_names = {int(group.index): group.name for group in body.vertex_groups}
        frozen_before = bmesh_frozen_snapshot(
            bm, vertex_id, face_id, loop_id, removable, selected_faces, group_names
        )
        original_vertices = {int(vertex[vertex_id]): vertex for vertex in bm.verts}
        original_faces = {int(face[face_id]): face for face in bm.faces}
        seam_vertices = [original_vertices[index] for index in target_cycle]
        for index, vertex in enumerate(seam_vertices):
            vertex[local_id] = index
        bmesh.ops.delete(
            bm,
            geom=[original_faces[index] for index in selected_faces],
            context="FACES_ONLY",
        )
        bmesh.ops.delete(
            bm,
            geom=[original_vertices[index] for index in removable],
            context="VERTS",
        )
        local_vertices = list(seam_vertices)
        for local_index, coordinate in enumerate(
            prepared["positions_body_local"][len(target_cycle) :],
            start=len(target_cycle),
        ):
            vertex = bm.verts.new(Vector(coordinate))
            vertex[vertex_id] = -1
            vertex[local_id] = local_index
            local_vertices.append(vertex)
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()
        new_faces = []
        for indices in prepared["faces"]:
            face = bm.faces.new([local_vertices[int(index)] for index in indices])
            face[face_id] = -1
            face.material_index = material_index
            face.smooth = True
            for loop in face.loops:
                loop[loop_id] = -1
            new_faces.append(face)
        deform = bm.verts.layers.deform.active
        if deform is None:
            raise R23AuthorError("primary surface lacks deform weights")
        group_indices = {group.name: int(group.index) for group in body.vertex_groups}
        rig_bones = {bone.name for bone in rig.data.bones}
        for local_index, record in prepared["new_weights"].items():
            vertex = local_vertices[int(local_index)]
            for name, weight in record.items():
                if name not in group_indices or name not in rig_bones:
                    raise R23AuthorError(f"new weight references non-native group: {name}")
                vertex[deform][group_indices[name]] = float(weight)
        for layer_name, field in prepared["uv_fields"].items():
            layer = bm.loops.layers.uv.get(layer_name)
            if layer is None:
                raise R23AuthorError(f"required UV layer disappeared: {layer_name}")
            for face in new_faces:
                for loop in face.loops:
                    loop[layer].uv = field[int(loop.vert[local_id])]
        bm.normal_update()
        frozen_after = bmesh_frozen_snapshot(
            bm, vertex_id, face_id, loop_id, removable, selected_faces, group_names
        )
        if frozen_before != frozen_after:
            raise R23AuthorError("surviving R19 coordinates/topology/weights/UVs changed")
        bm.verts.index_update()
        bm.faces.index_update()
        local_to_global = {
            int(vertex[local_id]): int(vertex.index)
            for vertex in bm.verts
            if int(vertex[local_id]) >= 0
        }
        patch_face_indices = [int(face.index) for face in new_faces]
        bm.verts.layers.int.remove(vertex_id)
        bm.verts.layers.int.remove(local_id)
        bm.faces.layers.int.remove(face_id)
        bm.loops.layers.int.remove(loop_id)
        bm.to_mesh(body.data)
    finally:
        bm.free()
    body.data.update(calc_edges=True, calc_edges_loose=True)
    color = body.data.color_attributes.get("R23_AFES_Tint")
    if color is not None:
        body.data.color_attributes.remove(color)
    color = body.data.color_attributes.new(
        name="R23_AFES_Tint", type="FLOAT_COLOR", domain="CORNER"
    )
    global_to_local = {value: key for key, value in local_to_global.items()}
    for face_index in patch_face_indices:
        face = body.data.polygons[face_index]
        for loop_index in face.loop_indices:
            vertex_index = int(body.data.loops[loop_index].vertex_index)
            color.data[loop_index].color = prepared["tint_rgba"][global_to_local[vertex_index]]
    body.name = "Kira_R23_CC0_AFES_CoreTransfer_Primary_Surface"
    body.data.name = "Kira_R23_CC0_AFES_CoreTransfer_Primary_Surface_Mesh"
    for key, value in {
        "r23_candidate_id": "R23_CC0_AFES_CORE_TRANSFER_A",
        "r23_private_owner_review_only": True,
        "r23_inactive": True,
        "r23_unassigned": True,
        "r23_unpublished": True,
        "r23_runtime_eligible": False,
        "r23_owner_approved": False,
        "r23_bald_low_resource_body": True,
        "r23_donor_visual_form_sufficient": False,
    }.items():
        body[key] = value
    return {
        "material": material.name,
        "material_index": material_index,
        "frozen_surviving_state_sha256_before": frozen_before,
        "frozen_surviving_state_sha256_after": frozen_after,
        "frozen_surviving_state_exact": frozen_before == frozen_after,
        "local_to_global_sha256": canonical_sha256(sorted(local_to_global.items())),
        "target_seam_global_indices": [
            int(local_to_global[index]) for index in range(len(target_cycle))
        ],
        "patch_face_index_sha256": preflight_base.canonical_index_sha256(patch_face_indices),
        "patch_face_indices": patch_face_indices,
    }


def topology_gate(
    body: bpy.types.Object,
    patch_face_indices: Sequence[int],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    faces = preflight_base.faces_of(body)
    whole = preflight_base.topology_record(faces, set(range(len(faces))))
    patch = preflight_base.topology_record(faces, set(int(value) for value in patch_face_indices))
    edge_faces = preflight_base.edge_face_map(faces)
    nonmanifold_edges = sum(len(values) != 2 for values in edge_faces.values())
    expected = config["expected_structural_result"]
    checks = {
        "vertices": len(body.data.vertices) == expected["body_vertices"],
        "edges": len(body.data.edges) == expected["body_edges"],
        "faces": len(body.data.polygons) == expected["body_faces"],
        "whole_components": whole["component_count"] == expected["whole_body_components"],
        "whole_boundary": whole["boundary_edge_count"] == expected["whole_body_boundary_edges"],
        "whole_nonmanifold": nonmanifold_edges
        == expected["whole_body_nonmanifold_edges"],
        "patch_vertices": patch["vertex_count"] == expected["replacement_patch_vertices"],
        "patch_faces": patch["face_count"] == expected["replacement_patch_faces"],
        "patch_edges": patch["edge_count"] == expected["replacement_patch_edges"],
        "patch_components": patch["component_count"] == expected["replacement_patch_components"],
        "patch_boundary_cycles": patch["boundary_cycle_count"]
        == expected["replacement_patch_boundary_cycles"],
        "patch_boundary_length": patch["boundary_cycle_lengths"]
        == [expected["replacement_patch_boundary_vertices"]],
        "patch_euler": patch["euler_characteristic"]
        == expected["replacement_patch_euler_characteristic"],
    }
    if not all(checks.values()):
        raise R23AuthorError(f"structural author gate failed: {checks}")
    return {
        "whole_body": whole,
        "replacement_patch": patch,
        "nonmanifold_edge_count": nonmanifold_edges,
        "checks": checks,
    }


def post_author_freeze_gate(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    original_target_cycle: Sequence[int],
    seam_global_indices: Sequence[int],
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    expected = preflight["fresh_freeze_ledger"]
    if len(original_target_cycle) != len(seam_global_indices):
        raise R23AuthorError("target seam mapping count drifted")
    seam_payload = []
    for original, current in zip(original_target_cycle, seam_global_indices):
        seam_payload.append(
            {
                "vertex": int(original),
                "coordinate": preflight_base.vector_record(
                    body.data.vertices[int(current)].co
                ),
                "weights": preflight_base.weight_rows(body, [int(current)])[0][1],
            }
        )
    seam_hash = preflight_base.canonical_json_sha256(seam_payload)

    nonbody_records = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj == body or obj.type != "MESH":
            continue
        nonbody_records.append(
            {
                "object": obj.name,
                "mesh": obj.data.name,
                "full_state_sha256": preflight_base.mesh_full_state_sha256(obj),
            }
        )
    existing_material_count = int(expected["body_materials"]["count"])
    existing_materials = [
        preflight_base.material_graph_record(material)
        for material in list(body.data.materials)[:existing_material_count]
    ]
    action_hash = actions_sha256(bpy.data.actions)
    checks = {
        "outer_seam_exact": seam_hash
        == expected["outer_seam"]["canonical_state_sha256"],
        "nonbody_count_exact": len(nonbody_records)
        == expected["nonbody_mesh_objects"]["count"],
        "nonbody_ledger_exact": preflight_base.canonical_json_sha256(nonbody_records)
        == expected["nonbody_mesh_objects"]["ledger_sha256"],
        "existing_material_count_exact": len(existing_materials)
        == existing_material_count,
        "existing_material_graphs_exact": preflight_base.canonical_json_sha256(
            existing_materials
        )
        == expected["body_materials"]["ledger_sha256"],
        "exactly_one_new_skin_derived_material": len(body.data.materials)
        == existing_material_count + 1,
        "rig_rest_exact": preflight_base.rig_rest_sha256(rig)
        == expected["rig"]["rest_structure_sha256"],
        "all_actions_exact": action_hash == expected["actions_sha256"],
    }
    if not all(checks.values()):
        raise R23AuthorError(f"post-author freeze ledger failed: {checks}")
    return {
        "checks": checks,
        "outer_seam_canonical_state_sha256": seam_hash,
        "nonbody_ledger_sha256": preflight_base.canonical_json_sha256(
            nonbody_records
        ),
        "existing_material_graph_ledger_sha256": (
            preflight_base.canonical_json_sha256(existing_materials)
        ),
        "rig_rest_structure_sha256": preflight_base.rig_rest_sha256(rig),
        "actions_sha256": action_hash,
    }


def main() -> int:
    args = arguments()
    config_path = project_path(args.config)
    config = read_json(config_path)
    if config.get("schema") != "kira.avatar.r23_cc0_afes_author_attempt01.v1":
        raise R23AuthorError("wrong R23 author config schema")
    if not args.execute_authoring:
        raise R23AuthorError(
            "authoring is prepared but not authorized; --execute-authoring is required"
        )
    paths = output_paths(config)
    paths["directory"].mkdir(parents=True, exist_ok=False)
    source = project_path(config["inputs"]["r19_source_blend"]["path"])
    try:
        verified_inputs = verify_inputs(config)
        if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != source.resolve():
            raise R23AuthorError("exact R19 source Blend is not loaded")
        source_hash_before = sha256_file(source)
        preflight, captured, _effective = reproduce_passed_preflight(config)
        body = bpy.data.objects.get("Kira_R19_BlackProject_Radial_Patch_Primary_Surface")
        rig = bpy.data.objects.get("Kira_R19_BlackProject_Native_188_Rig")
        donor = bpy.data.objects.get(config["qualified_donor_disk"]["object_name"])
        if body is None or rig is None or donor is None:
            raise R23AuthorError("exact body, rig, or in-memory qualified donor is absent")
        selected_faces = {int(value) for value in captured["chosen"]}
        target_cycle = [int(value) for value in captured["chosen_cycle"]]
        donor_disk, donor_vertices, donor_cycle, memberships = exact_donor_disk(
            donor, preflight, config
        )
        prepared = prepare_patch(
            body,
            donor,
            selected_faces,
            target_cycle,
            donor_disk,
            donor_vertices,
            donor_cycle,
            memberships,
            preflight,
            config,
        )
        apply_evidence = apply_patch(
            body, rig, selected_faces, target_cycle, prepared, config
        )
        topology = topology_gate(body, apply_evidence["patch_face_indices"], config)
        bpy.data.objects.remove(donor, do_unlink=True)
        if bpy.data.objects.get(config["qualified_donor_disk"]["object_name"]) is not None:
            raise R23AuthorError("qualified donor object remained in candidate scene")
        if sha256_file(source) != source_hash_before:
            raise R23AuthorError("sealed R19 source file changed before candidate save")
        freeze_after = post_author_freeze_gate(
            body,
            rig,
            target_cycle,
            apply_evidence["target_seam_global_indices"],
            preflight,
        )
        bpy.ops.wm.save_as_mainfile(filepath=str(paths["candidate"]))
        evidence = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
            "config": {"path": relative(config_path), "sha256": sha256_file(config_path)},
            "verified_inputs": verified_inputs,
            "source_blend": {
                "path": relative(source),
                "sha256_before": source_hash_before,
                "sha256_after": sha256_file(source),
                "unchanged": sha256_file(source) == source_hash_before,
            },
            "passed_preflight_reproduced": {
                "selected_face_sha256": preflight["expanded_r19_mask"]["selected_face_index_sha256"],
                "selected_outer_seam_sha256": preflight["expanded_r19_mask"]["ordered_outer_seam_sha256"],
                "freeze_ledger_sha256": canonical_sha256(preflight["fresh_freeze_ledger"]),
            },
            "prepared_patch": {key: value for key, value in prepared.items() if key not in {"positions_body_local", "positions_world", "faces", "new_weights", "uv_fields", "tint_rgba", "donor_vertex_order", "donor_boundary_order"}},
            "localized_application": {
                key: value
                for key, value in apply_evidence.items()
                if key not in {"patch_face_indices", "target_seam_global_indices"}
            },
            "topology": topology,
            "post_author_freeze_ledger": freeze_after,
            "candidate": {
                "path": relative(paths["candidate"]),
                "bytes": paths["candidate"].stat().st_size,
                "sha256": sha256_file(paths["candidate"]),
                "inactive": True,
                "unassigned": True,
                "unpublished": True,
                "runtime_eligible": False,
                "owner_approved": False,
            },
            "postsave_audits_required_not_run": config["postsave_required_audits_before_owner_review"],
            "truth_boundary": config["truth_boundary"],
            "operations": {
                "source_blend_written": False,
                "candidate_blend_written": True,
                "render_performed": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "candidate_activated": False,
            },
        }
        paths["evidence"].write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": evidence["status"], "candidate": evidence["candidate"], "evidence": relative(paths["evidence"]), "evidence_sha256": sha256_file(paths["evidence"])}, indent=2))
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01_FAILURE",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "AUTHOR_NO_GO_NO_CANDIDATE_ACCEPTED",
            "config": {"path": relative(config_path), "sha256": sha256_file(config_path)},
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "source_blend": {
                "path": relative(source),
                "sha256_after": sha256_file(source) if source.is_file() else None,
                "expected_sha256": config["inputs"]["r19_source_blend"]["sha256"],
            },
            "candidate_file_exists": paths["candidate"].exists(),
            "render_performed": False,
            "export_performed": False,
            "runtime_mutation_performed": False,
        }
        paths["failure"].write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": failure["status"], "failure": relative(paths["failure"]), "sha256": sha256_file(paths["failure"])}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
