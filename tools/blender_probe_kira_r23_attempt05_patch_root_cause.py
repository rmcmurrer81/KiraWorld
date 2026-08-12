#!/usr/bin/env python3
"""Narrow read-only root-cause probe for Kira R23 Attempt 05.

The accepted diagnostic already proves the R23 patch fails its neutral
intersection, seam-continuity, and deformation gates.  This probe does not
repeat the expensive exact-intersection sweep.  It binds that evidence, opens
the exact immutable source and candidate, and localizes:

* face-winding consistency by generated patch section;
* the already-proven neutral intersection pairs by patch section;
* the exact patch and seam edges with the largest deformation ratios; and
* whether seam stretch is inherited from the unchanged R19 boundary.

It never renders, saves a Blend, exports, activates, assigns, or publishes.
Only one new append-only JSON evidence file is written.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXECUTION_FLAG = "--execute-readonly-root-cause-probe"
BOUND_STATUS = "BOUND_NOT_RUN_EXPLICIT_READONLY_ROOT_CAUSE_AUTHORIZATION_REQUIRED"


class ProbeError(RuntimeError):
    """Fail-closed binding or measurement error."""


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(EXECUTION_FLAG, action="store_true")
    return parser.parse_args(raw)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProbeError(f"JSON root is not an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(raw: str | Path) -> Path:
    value = Path(raw)
    return value if value.is_absolute() else ROOT / value


def require_binding(binding: Mapping[str, Any], label: str) -> Path:
    path = project_path(str(binding["path"]))
    if not path.is_file():
        raise ProbeError(f"{label} is absent: {path}")
    actual_bytes = path.stat().st_size
    actual_sha = sha256_file(path)
    if actual_bytes != int(binding["bytes"]) or actual_sha != str(binding["sha256"]):
        raise ProbeError(
            f"{label} drifted: bytes={actual_bytes}, sha256={actual_sha}"
        )
    return path


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def face_edges(vertices: Sequence[int]) -> list[tuple[int, int]]:
    return [
        tuple(sorted((int(vertices[index]), int(vertices[(index + 1) % len(vertices)]))))
        for index in range(len(vertices))
    ]


def directed_edge_sign(vertices: Sequence[int], edge: tuple[int, int]) -> int:
    first, second = edge
    for index, value in enumerate(vertices):
        following = int(vertices[(index + 1) % len(vertices)])
        if int(value) == first and following == second:
            return 1
        if int(value) == second and following == first:
            return -1
    raise ProbeError(f"face does not contain edge {edge}")


def weight_distance(first: Mapping[str, float], second: Mapping[str, float]) -> float:
    return max(
        (abs(float(first.get(name, 0.0)) - float(second.get(name, 0.0)))
         for name in set(first).union(second)),
        default=0.0,
    )


def section_for_ordinal(ordinal: int, sections: Sequence[Mapping[str, Any]]) -> str:
    for section in sections:
        if int(section["start_ordinal"]) <= ordinal < int(section["end_ordinal_exclusive"]):
            return str(section["id"])
    raise ProbeError(f"patch face ordinal is outside every section: {ordinal}")


def section_contract(patch_face_count: int) -> list[dict[str, Any]]:
    counts = (
        ("outer_91_to_154_zipper", 245),
        ("first_154_ring_bridge", 308),
        ("second_154_ring_bridge", 308),
        ("mapped_cc0_donor_disk", 2488),
    )
    result = []
    start = 0
    for name, count in counts:
        result.append(
            {
                "id": name,
                "start_ordinal": start,
                "end_ordinal_exclusive": start + count,
                "face_count": count,
            }
        )
        start += count
    if start != patch_face_count:
        raise ProbeError(
            f"section counts total {start}, expected patch count {patch_face_count}"
        )
    return result


def reproduce_patch_creation_data(
    verification_config: Mapping[str, Any], bpy: Any
) -> dict[str, Any]:
    """Recompute the sealed preparation in memory without applying or saving it."""

    from tools import blender_author_kira_r23_cc0_afes_attempt01 as author

    binding = verification_config["fixed_inputs"]["r23_author_config"]
    config_path = require_binding(binding, "sealed R23 author config")
    author_config = read_json(config_path)
    preflight, captured, _effective = author.reproduce_passed_preflight(author_config)
    body = bpy.data.objects.get("Kira_R19_BlackProject_Radial_Patch_Primary_Surface")
    donor = bpy.data.objects.get(author_config["qualified_donor_disk"]["object_name"])
    if body is None or donor is None:
        raise ProbeError("sealed preparation did not expose the exact body and donor")
    selected_faces = {int(value) for value in captured["chosen"]}
    target_cycle = [int(value) for value in captured["chosen_cycle"]]
    donor_disk, donor_vertices, donor_cycle, memberships = author.exact_donor_disk(
        donor, preflight, author_config
    )
    prepared = author.prepare_patch(
        body,
        donor,
        selected_faces,
        target_cycle,
        donor_disk,
        donor_vertices,
        donor_cycle,
        memberships,
        preflight,
        author_config,
    )
    return {
        "target_cycle": target_cycle,
        "positions_body_local": [list(map(float, value)) for value in prepared["positions_body_local"]],
        "faces": [list(map(int, value)) for value in prepared["faces"]],
        "collar_ring_size": int(prepared["collar_ring_size"]),
        "donor_start": int(prepared["donor_start"]),
        "prepared_topology_sha256": str(prepared["topology_sha256"]),
        "prepared_position_sha256": str(prepared["position_sha256"]),
        "author_config": dict(binding),
    }


def recover_saved_creation_mapping(
    body: Any,
    patch_faces: set[int],
    diagnostic: Mapping[str, Any],
    creation: Mapping[str, Any],
) -> dict[str, Any]:
    """Map sealed local author IDs to the saved BMesh indices by exact geometry."""

    from mathutils import Vector
    from mathutils.kdtree import KDTree

    candidate_cycle = [
        int(value)
        for value in diagnostic["continuity_full_localization"]["candidate_cycle"]
    ]
    mapped_source_cycle = [
        int(value)
        for value in diagnostic["continuity_full_localization"]["mapped_source_cycle"]
    ]
    source_to_candidate = dict(zip(mapped_source_cycle, candidate_cycle))
    target_cycle = [int(value) for value in creation["target_cycle"]]
    local_to_global: dict[int, int] = {}
    for local_index, source_index in enumerate(target_cycle):
        if source_index not in source_to_candidate:
            raise ProbeError("saved seam mapping omitted a sealed target vertex")
        local_to_global[local_index] = source_to_candidate[source_index]

    patch_vertices = sorted(
        {
            int(value)
            for face_index in patch_faces
            for value in body.data.polygons[face_index].vertices
        }
    )
    seam_vertices = set(candidate_cycle)
    interior_candidates = [value for value in patch_vertices if value not in seam_vertices]
    tree = KDTree(len(interior_candidates))
    for value in interior_candidates:
        tree.insert(body.data.vertices[value].co, value)
    tree.balance()
    used = set(local_to_global.values())
    maximum_error = 0.0
    for local_index in range(len(target_cycle), len(creation["positions_body_local"])):
        coordinate = Vector(creation["positions_body_local"][local_index])
        matches = tree.find_n(coordinate, 12)
        selected = next(
            ((int(index), float(distance)) for _point, index, distance in matches if int(index) not in used),
            None,
        )
        if selected is None or selected[1] > 1.0e-6:
            raise ProbeError(
                f"sealed local vertex {local_index} lacks a unique saved match: {selected}"
            )
        global_index, distance = selected
        local_to_global[local_index] = global_index
        used.add(global_index)
        maximum_error = max(maximum_error, distance)
    if used != set(patch_vertices):
        raise ProbeError("local-to-saved vertex map does not cover the exact patch")

    canonical_face: dict[tuple[int, ...], int] = {}
    for face_index in patch_faces:
        key = tuple(sorted(map(int, body.data.polygons[face_index].vertices)))
        if key in canonical_face:
            raise ProbeError("saved patch contains duplicate canonical faces")
        canonical_face[key] = int(face_index)
    ordinal_to_face: dict[int, int] = {}
    for ordinal, local_face in enumerate(creation["faces"]):
        key = tuple(sorted(local_to_global[int(value)] for value in local_face))
        face_index = canonical_face.get(key)
        if face_index is None:
            raise ProbeError(f"sealed prepared face {ordinal} is absent from the candidate")
        ordinal_to_face[ordinal] = face_index
    if set(ordinal_to_face.values()) != set(patch_faces):
        raise ProbeError("prepared-to-saved face mapping does not cover the exact patch")

    collar_size = int(creation["collar_ring_size"])
    donor_start = int(creation["donor_start"])
    local_vertex_region = {}
    for local_index in range(len(creation["positions_body_local"])):
        if local_index < len(target_cycle):
            region = "target_seam"
        elif local_index < len(target_cycle) + collar_size:
            region = "first_collar_ring"
        elif local_index < donor_start:
            region = "second_collar_ring"
        else:
            region = "mapped_cc0_donor_disk"
        local_vertex_region[local_index] = region
    global_to_local = {value: key for key, value in local_to_global.items()}
    return {
        "local_to_global": local_to_global,
        "global_to_local": global_to_local,
        "ordinal_to_face": ordinal_to_face,
        "maximum_coordinate_match_error_m": maximum_error,
        "local_vertex_region": local_vertex_region,
        "checks": {
            "all_patch_vertices_mapped_once": len(local_to_global) == len(patch_vertices),
            "all_patch_faces_mapped_once": len(ordinal_to_face) == len(patch_faces),
            "prepared_topology_sha256_matches_attempt05": creation["prepared_topology_sha256"]
            == "8a30a63adcd431145f25308ea8d87c86782d0e11a3ed307a3ec431085351617c",
            "prepared_position_sha256_matches_attempt05": creation["prepared_position_sha256"]
            == "737a955c0701fa2fe87ff8de7e972716ec7e94731897abadaa107d7d3d2321b6",
        },
    }


def patch_topology_localization(
    body: Any,
    patch_faces: set[int],
    diagnostic: Mapping[str, Any],
    creation_mapping: Mapping[str, Any],
) -> dict[str, Any]:
    ordered_patch = sorted(patch_faces)
    sections = section_contract(len(ordered_patch))
    ordinal = {
        int(face_index): int(value)
        for value, face_index in creation_mapping["ordinal_to_face"].items()
    }
    section = {
        face_index: section_for_ordinal(index, sections)
        for face_index, index in ordinal.items()
    }
    edge_incidence: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for face in body.data.polygons:
        for edge in face_edges(tuple(map(int, face.vertices))):
            edge_incidence[edge].append(int(face.index))

    internal_rows = []
    seam_rows = []
    for edge, incident in sorted(edge_incidence.items()):
        patch_incident = [value for value in incident if value in patch_faces]
        retained_incident = [value for value in incident if value not in patch_faces]
        if len(patch_incident) == 2:
            first, second = patch_incident
            first_sign = directed_edge_sign(tuple(map(int, body.data.polygons[first].vertices)), edge)
            second_sign = directed_edge_sign(tuple(map(int, body.data.polygons[second].vertices)), edge)
            internal_rows.append(
                {
                    "edge": list(edge),
                    "faces": [first, second],
                    "sections": [section[first], section[second]],
                    "directed_signs": [first_sign, second_sign],
                    "opposite_direction_passed": first_sign == -second_sign,
                }
            )
        elif len(patch_incident) == 1 and len(retained_incident) == 1:
            patch_face = patch_incident[0]
            retained_face = retained_incident[0]
            patch_sign = directed_edge_sign(
                tuple(map(int, body.data.polygons[patch_face].vertices)), edge
            )
            retained_sign = directed_edge_sign(
                tuple(map(int, body.data.polygons[retained_face].vertices)), edge
            )
            seam_rows.append(
                {
                    "edge": list(edge),
                    "patch_face": patch_face,
                    "patch_section": section[patch_face],
                    "retained_face": retained_face,
                    "directed_signs": [patch_sign, retained_sign],
                    "opposite_direction_passed": patch_sign == -retained_sign,
                    "normal_dot": float(
                        body.data.polygons[patch_face].normal.dot(
                            body.data.polygons[retained_face].normal
                        )
                    ),
                }
            )

    exact_pairs = diagnostic["intersections"]["r23_neutral_full"]["exact_report"]["pairs"]
    pair_rows = []
    section_pair_counts: Counter[tuple[str, str]] = Counter()
    for record in exact_pairs:
        face_pair = [int(value) for value in record["face_indices"]]
        labels = [section.get(value, "retained_r19") for value in face_pair]
        labels = sorted(labels)
        section_pair_counts[tuple(labels)] += 1
        if any(value in patch_faces for value in face_pair):
            pair_rows.append(
                {
                    "face_indices": face_pair,
                    "sections": labels,
                    "topology_edge_hops": int(record["topology_edge_hops"]),
                    "center_distance_m": float(record["center_distance_m"]),
                    "maximum_intersection_segment_length_m": max(
                        float(value.get("intersection_segment_length_m", 0.0))
                        for value in record["triangle_pair_classifications"]
                    ),
                }
            )

    internal_bad = [row for row in internal_rows if not row["opposite_direction_passed"]]
    seam_bad = [row for row in seam_rows if not row["opposite_direction_passed"]]
    return {
        "patch_face_count": len(ordered_patch),
        "minimum_patch_face_index": min(ordered_patch),
        "maximum_patch_face_index": max(ordered_patch),
        "patch_faces_are_contiguous": ordered_patch
        == list(range(min(ordered_patch), max(ordered_patch) + 1)),
        "patch_face_index_sha256": canonical_sha256(ordered_patch),
        "saved_creation_mapping": {
            "maximum_coordinate_match_error_m": creation_mapping[
                "maximum_coordinate_match_error_m"
            ],
            "checks": creation_mapping["checks"],
            "local_to_global_sha256": canonical_sha256(
                sorted(creation_mapping["local_to_global"].items())
            ),
            "ordinal_to_face_sha256": canonical_sha256(
                sorted(creation_mapping["ordinal_to_face"].items())
            ),
        },
        "sections": sections,
        "internal_patch_edge_count": len(internal_rows),
        "internal_same_direction_edge_count": len(internal_bad),
        "internal_same_direction_edges": internal_bad,
        "seam_edge_count": len(seam_rows),
        "seam_same_direction_edge_count": len(seam_bad),
        "seam_same_direction_edges": seam_bad,
        "seam_normal_failure_count_at_0_7": sum(
            float(row["normal_dot"]) < 0.7 for row in seam_rows
        ),
        "neutral_exact_pair_counts_by_section": [
            {"sections": list(key), "count": count}
            for key, count in sorted(section_pair_counts.items())
        ],
        "neutral_patch_involving_pairs": pair_rows,
        "face_section_by_index": {
            str(face_index): section[face_index] for face_index in ordered_patch
        },
    }


def all_patch_edges(body: Any, patch_faces: Iterable[int]) -> tuple[set[tuple[int, int]], dict[tuple[int, int], list[int]]]:
    edges: set[tuple[int, int]] = set()
    incidence: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index in patch_faces:
        face = body.data.polygons[int(face_index)]
        for edge in face_edges(tuple(map(int, face.vertices))):
            edges.add(edge)
            incidence[edge].append(int(face_index))
    return edges, dict(incidence)


def evaluated_points(body: Any, bpy: Any) -> list[Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def lengths(points: Sequence[Any], edges: Iterable[tuple[int, int]]) -> dict[tuple[int, int], float]:
    return {
        edge: float((points[edge[0]] - points[edge[1]]).length)
        for edge in edges
    }


def ratio_rows(
    base: Mapping[tuple[int, int], float],
    current: Mapping[tuple[int, int], float],
) -> list[tuple[float, tuple[int, int]]]:
    result = []
    for edge, base_length in base.items():
        ratio = 1.0 if base_length <= 1.0e-12 else current[edge] / base_length
        result.append((float(ratio), edge))
    return sorted(result, key=lambda value: (-value[0], value[1]))


def apply_pose(rig: Any, rotations: Mapping[str, Sequence[float]], bpy: Any) -> None:
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    for name, degrees in rotations.items():
        bone = rig.pose.bones.get(name)
        if bone is None:
            raise ProbeError(f"pose bone is absent: {name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = tuple(math.radians(float(value)) for value in degrees)
    bpy.context.view_layer.update()


def suspend_action(rig: Any) -> None:
    if rig.animation_data is not None:
        rig.animation_data.action = None
        for track in rig.animation_data.nla_tracks:
            track.mute = True


def source_seam_deformation(
    source_path: Path,
    verification_config: Mapping[str, Any],
    diagnostic: Mapping[str, Any],
    bpy: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    names = verification_config["objects"]
    body = bpy.data.objects.get(names["r19_body"])
    rig = bpy.data.objects.get(names["rig"])
    if body is None or rig is None:
        raise ProbeError("R19 source body or rig is absent")
    creation = reproduce_patch_creation_data(verification_config, bpy)
    suspend_action(rig)
    seam = [
        int(value)
        for value in diagnostic["continuity_full_localization"]["mapped_source_cycle"]
    ]
    seam_edges = {
        tuple(sorted((seam[index], seam[(index + 1) % len(seam)])))
        for index in range(len(seam))
    }
    apply_pose(rig, {}, bpy)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    neutral = lengths(evaluated_points(body, bpy), seam_edges)
    result = {}
    for pose in verification_config["poses"]:
        apply_pose(rig, pose["rotations_degrees"], bpy)
        current = lengths(evaluated_points(body, bpy), seam_edges)
        rows = ratio_rows(neutral, current)
        result[str(pose["id"])] = {
            "maximum_seam_edge_stretch_ratio": rows[0][0],
            "top_10_edges": [
                {
                    "edge": list(edge),
                    "ratio": ratio,
                    "neutral_length_m": neutral[edge],
                    "posed_length_m": current[edge],
                }
                for ratio, edge in rows[:10]
            ],
        }
    apply_pose(rig, {}, bpy)
    return result, creation


def candidate_deformation(
    candidate_path: Path,
    verification_config: Mapping[str, Any],
    diagnostic: Mapping[str, Any],
    creation: Mapping[str, Any],
    bpy: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from tools import blender_verify_kira_r23_postsave_fresh_reopen as verifier

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=str(candidate_path), load_ui=False)
    names = verification_config["objects"]
    body = bpy.data.objects.get(names["r23_body"])
    rig = bpy.data.objects.get(names["rig"])
    if body is None or rig is None:
        raise ProbeError("R23 candidate body or rig is absent")
    suspend_action(rig)
    patch_faces, _material_index = verifier.patch_face_indices(
        body, names["r23_patch_material"]
    )
    creation_mapping = recover_saved_creation_mapping(
        body, patch_faces, diagnostic, creation
    )
    topology = patch_topology_localization(
        body, patch_faces, diagnostic, creation_mapping
    )
    patch_edges, incidence = all_patch_edges(body, patch_faces)
    seam = [
        int(value)
        for value in diagnostic["continuity_full_localization"]["candidate_cycle"]
    ]
    seam_edges = {
        tuple(sorted((seam[index], seam[(index + 1) % len(seam)])))
        for index in range(len(seam))
    }
    section_by_face = {
        int(key): value for key, value in topology["face_section_by_index"].items()
    }
    global_to_local = {
        int(key): int(value) for key, value in creation_mapping["global_to_local"].items()
    }
    local_vertex_region = {
        int(key): value for key, value in creation_mapping["local_vertex_region"].items()
    }
    apply_pose(rig, {}, bpy)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    neutral_points = evaluated_points(body, bpy)
    neutral_patch = lengths(neutral_points, patch_edges)
    neutral_seam = lengths(neutral_points, seam_edges)
    result = {}
    for pose in verification_config["poses"]:
        apply_pose(rig, pose["rotations_degrees"], bpy)
        points = evaluated_points(body, bpy)
        patch_current = lengths(points, patch_edges)
        seam_current = lengths(points, seam_edges)
        patch_rows = ratio_rows(neutral_patch, patch_current)
        seam_rows = ratio_rows(neutral_seam, seam_current)
        result[str(pose["id"])] = {
            "maximum_patch_edge_stretch_ratio": patch_rows[0][0],
            "maximum_seam_edge_stretch_ratio": seam_rows[0][0],
            "top_25_patch_edges": [
                {
                    "edge": list(edge),
                    "ratio": ratio,
                    "neutral_length_m": neutral_patch[edge],
                    "posed_length_m": patch_current[edge],
                    "incident_patch_faces": incidence[edge],
                    "sections": sorted(
                        {section_by_face[index] for index in incidence[edge]}
                    ),
                    "local_vertex_ids": [global_to_local[edge[0]], global_to_local[edge[1]]],
                    "local_vertex_regions": [
                        local_vertex_region[global_to_local[edge[0]]],
                        local_vertex_region[global_to_local[edge[1]]],
                    ],
                    "first_weights": verifier.weight_map(body, edge[0]),
                    "second_weights": verifier.weight_map(body, edge[1]),
                    "maximum_weight_delta": weight_distance(
                        verifier.weight_map(body, edge[0]),
                        verifier.weight_map(body, edge[1]),
                    ),
                }
                for ratio, edge in patch_rows[:25]
            ],
            "top_10_seam_edges": [
                {
                    "edge": list(edge),
                    "ratio": ratio,
                    "neutral_length_m": neutral_seam[edge],
                    "posed_length_m": seam_current[edge],
                }
                for ratio, edge in seam_rows[:10]
            ],
        }
    apply_pose(rig, {}, bpy)
    return topology, result


def run(config_path: Path, explicit_execution: bool) -> int:
    if not explicit_execution:
        raise ProbeError(f"explicit {EXECUTION_FLAG} flag is required")
    config = read_json(config_path)
    if config.get("status") != BOUND_STATUS:
        raise ProbeError("probe config has the wrong status")
    worker_path = require_binding(config["worker"], "exact root-cause worker")
    if worker_path.resolve() != Path(__file__).resolve():
        raise ProbeError("configured worker is not the executing worker")
    execution = config.get("execution", {})
    required_true = (
        "read_only_source_and_candidate",
        "render_forbidden",
        "blend_save_forbidden",
        "export_forbidden",
        "runtime_mutation_forbidden",
        "activation_assignment_publication_forbidden",
    )
    if any(execution.get(key) is not True for key in required_true):
        raise ProbeError("probe execution restrictions were weakened")

    verification_path = require_binding(config["verification_config"], "verification config")
    diagnostic_path = require_binding(config["accepted_diagnostic"], "accepted diagnostic")
    source_path = require_binding(config["r19_source"], "R19 source")
    candidate_path = require_binding(config["r23_candidate"], "R23 candidate")
    verification_config = read_json(verification_path)
    diagnostic = read_json(diagnostic_path)
    if diagnostic.get("status") != "DIAGNOSTIC_METRICS_CAPTURED_NOT_ACCEPTANCE_NOT_OWNER_APPROVAL":
        raise ProbeError("accepted diagnostic status drifted")
    output_directory = project_path(config["output"]["directory"])
    output_path = output_directory / str(config["output"]["filename"])
    if output_directory.exists():
        raise ProbeError("append-only root-cause output already exists")

    source_before = {"bytes": source_path.stat().st_size, "sha256": sha256_file(source_path)}
    candidate_before = {
        "bytes": candidate_path.stat().st_size,
        "sha256": sha256_file(candidate_path),
    }
    output_directory.mkdir(parents=True, exist_ok=False)
    try:
        import bpy

        if bpy.data.filepath:
            raise ProbeError("probe was not launched from factory-empty Blender")
        source_deformation, creation = source_seam_deformation(
            source_path, verification_config, diagnostic, bpy
        )
        topology, candidate_deformation_rows = candidate_deformation(
            candidate_path, verification_config, diagnostic, creation, bpy
        )
        source_after = {
            "bytes": source_path.stat().st_size,
            "sha256": sha256_file(source_path),
        }
        candidate_after = {
            "bytes": candidate_path.stat().st_size,
            "sha256": sha256_file(candidate_path),
        }
        result = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_ATTEMPT05_PATCH_ROOT_CAUSE_PROBE",
            "created_utc": utc_now(),
            "status": "READ_ONLY_ROOT_CAUSE_METRICS_NOT_ACCEPTANCE_NOT_OWNER_APPROVAL",
            "bindings": {
                "config": {
                    "path": config_path.relative_to(ROOT).as_posix(),
                    "bytes": config_path.stat().st_size,
                    "sha256": sha256_file(config_path),
                },
                "verification_config": dict(config["verification_config"]),
                "accepted_diagnostic": dict(config["accepted_diagnostic"]),
                "r19_source": dict(config["r19_source"]),
                "r23_candidate": dict(config["r23_candidate"]),
            },
            "patch_topology_and_neutral_pair_localization": topology,
            "r19_exact_seam_pose_stretch": source_deformation,
            "r23_patch_and_exact_seam_pose_stretch": candidate_deformation_rows,
            "immutability": {
                "source_before": source_before,
                "source_after": source_after,
                "source_unchanged": source_before == source_after,
                "candidate_before": candidate_before,
                "candidate_after": candidate_after,
                "candidate_unchanged": candidate_before == candidate_after,
            },
            "operations": {
                "render_performed": False,
                "blend_saved": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "candidate_activated_assigned_or_published": False,
                "append_only_json_written": True,
            },
            "truth_boundary": [
                "This probe localizes already-proven engineering failures only.",
                "It is not visual approval, anatomy acceptance, movement acceptance, or biological-function evidence.",
                "The exact R19 source and Attempt05 candidate remain immutable.",
            ],
        }
        if not result["immutability"]["source_unchanged"] or not result["immutability"]["candidate_unchanged"]:
            raise ProbeError("source or candidate changed during read-only probe")
        with output_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(json.dumps({"status": result["status"], "output": str(output_path)}))
        return 0
    except Exception:
        failure_path = output_directory / "FAILURE_EVIDENCE.json"
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_ATTEMPT05_PATCH_ROOT_CAUSE_PROBE_FAILURE",
            "created_utc": utc_now(),
            "exception_type": type(sys.exc_info()[1]).__name__,
            "exception": str(sys.exc_info()[1]),
            "traceback": traceback.format_exc(),
            "operations": {
                "render_performed": False,
                "blend_saved": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
            },
        }
        with failure_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(failure, handle, indent=2, sort_keys=True)
            handle.write("\n")
        raise


def main() -> int:
    args = arguments()
    return run(project_path(args.config), bool(getattr(args, EXECUTION_FLAG[2:].replace("-", "_"))))


if __name__ == "__main__":
    raise SystemExit(main())
