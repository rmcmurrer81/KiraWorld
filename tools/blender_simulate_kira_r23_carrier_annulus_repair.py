#!/usr/bin/env python3
"""No-save localized R23 transition-remesh and pose-weight simulation.

This worker preserves the exact R19 outer seam, the exact mapped CC0 donor
core, rig/actions, materials, and semantic memberships.  It replaces only the
failed fixed two-ring transition with a four-ring annulus lifted from a convex
harmonic chart of the original R19 selected carrier surface.  It never saves,
renders, exports, or activates a body.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
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

EXPECTED_ARTIFACT_KIND = "KIRA_R23_CARRIER_ANNULUS_REPAIR_SIMULATION_CONFIG"
EXPECTED_BOUND_STATUS = "BOUND_NOT_RUN_EXPLICIT_READONLY_SIMULATION_REQUIRED"
EXPECTED_CONFIG_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_carrier_annulus_repair_simulation_preparation/"
    "KIRA_R23_CARRIER_ANNULUS_REPAIR_SIMULATION_CONFIG.json"
)
EXPECTED_BINDING_LABELS = {
    "worker",
    "localized_simulation_worker",
    "repair_core",
    "r19_source",
    "attempt05_candidate",
    "author_config",
    "attempt05_repair_overlay",
    "verification_config",
    "attempt08_failed_hermite_grid",
    "focused_exact_localization",
}
EXPECTED_BINDING_PATHS = {
    "worker": "tools/blender_simulate_kira_r23_carrier_annulus_repair.py",
    "localized_simulation_worker": "tools/blender_simulate_kira_r23_localized_patch_repair.py",
    "repair_core": "tools/kira_r23_localized_patch_repair_core.py",
    "r19_source": (
        "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
        "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
    ),
    "attempt05_candidate": (
        "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author/attempt_05/"
        "kira_r23_cc0_afes_core_transfer_attempt_05.blend"
    ),
    "author_config": (
        "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author_attempt01_preparation/"
        "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT01_CONFIG.json"
    ),
    "attempt05_repair_overlay": (
        "RecoverySprint/continuation_20260803/"
        "kira_r23_cc0_afes_author_attempt05_reseal_v4_preparation/"
        "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_RESEAL_V4_REPAIR_OVERLAY.json"
    ),
    "verification_config": (
        "RecoverySprint/continuation_20260803/"
        "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_attempt02_preparation/"
        "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_ATTEMPT02_CONFIG.json"
    ),
    "attempt08_failed_hermite_grid": (
        "RecoverySprint/continuation_20260803/kira_r23_localized_patch_repair_simulation/"
        "attempt_08/SIMULATION_EVIDENCE.json"
    ),
    "focused_exact_localization": (
        "RecoverySprint/continuation_20260803/kira_r23_localized_best_variant_diagnostic/"
        "attempt_01/EXACT_LOCALIZATION.json"
    ),
}
EXPECTED_PARAMETER_GRID = {
    "ring_count": 4,
    "inner_radius": [0.25, 0.35, 0.45],
    "blend_power": [1.0, 2.0, 3.0],
}
EXPECTED_EXECUTION_RESTRICTIONS = {
    "one_heavy_blender_process_at_a_time": True,
    "read_only_source_and_attempt05": True,
    "blend_save_forbidden": True,
    "render_forbidden": True,
    "export_forbidden": True,
    "runtime_mutation_forbidden": True,
    "activation_assignment_publication_forbidden": True,
}
EXPECTED_OUTPUT = {
    "directory": (
        "RecoverySprint/continuation_20260803/"
        "kira_r23_carrier_annulus_repair_simulation/attempt_01"
    ),
    "filename": "ANNULUS_SIMULATION_EVIDENCE.json",
    "append_only": True,
}
EXPECTED_TRUTH_BOUNDARY = {
    "external_mesh_rig_deformation_and_contact_proxy_evidence_only": True,
    "owner_visual_approval": False,
    "internal_biological_function": False,
    "bathroom_function": False,
    "pregnancy_or_reproductive_function": False,
    "subjective_sensation_or_experience": False,
    "privacy_or_memory_acceptance": False,
    "author_candidate_created": False,
}


class AnnulusError(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--execute-readonly-simulation", action="store_true")
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AnnulusError(f"JSON root is not an object: {path}")
    return value


def require_binding(row: Mapping[str, Any], label: str) -> Path:
    if set(row) != {"path", "bytes", "sha256"}:
        raise AnnulusError(f"{label} binding fields are not exact")
    path = project_path(row["path"])
    if not path.is_file() or path.is_symlink():
        raise AnnulusError(f"{label} is absent or linked")
    if path.stat().st_size != int(row["bytes"]) or sha256_file(path) != row["sha256"]:
        raise AnnulusError(f"{label} drifted")
    return path


def validate_config(config: Mapping[str, Any]) -> None:
    expected_top_level = {
        "schema_version",
        "artifact_kind",
        "status",
        "bindings",
        "parameter_grid",
        "execution_restrictions",
        "output",
        "truth_boundary",
    }
    if set(config) != expected_top_level:
        raise AnnulusError("annulus config top-level fields are not exact")
    if config.get("schema_version") != 1:
        raise AnnulusError("annulus config schema_version is not exactly 1")
    if config.get("artifact_kind") != EXPECTED_ARTIFACT_KIND:
        raise AnnulusError("annulus config artifact_kind is not exact")
    if config.get("status") != EXPECTED_BOUND_STATUS:
        raise AnnulusError("annulus config status is not the required bound-not-run status")
    bindings = config.get("bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != EXPECTED_BINDING_LABELS:
        raise AnnulusError("annulus config binding labels are not exact")
    for label, row in bindings.items():
        if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
            raise AnnulusError(f"annulus config binding is malformed: {label}")
        if not isinstance(row["path"], str) or not row["path"]:
            raise AnnulusError(f"annulus config binding path is invalid: {label}")
        if row["path"] != EXPECTED_BINDING_PATHS[label]:
            raise AnnulusError(f"annulus config binding path is not exact: {label}")
        if type(row["bytes"]) is not int or int(row["bytes"]) < 0:
            raise AnnulusError(f"annulus config binding bytes are invalid: {label}")
        digest = row["sha256"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise AnnulusError(f"annulus config binding SHA-256 is invalid: {label}")
    if config.get("parameter_grid") != EXPECTED_PARAMETER_GRID:
        raise AnnulusError("annulus parameter grid is not the exact reviewed grid")
    if config.get("execution_restrictions") != EXPECTED_EXECUTION_RESTRICTIONS:
        raise AnnulusError("annulus execution restrictions are not exact")
    if config.get("output") != EXPECTED_OUTPUT:
        raise AnnulusError("annulus append-only output binding is not exact")
    if config.get("truth_boundary") != EXPECTED_TRUTH_BOUNDARY:
        raise AnnulusError("annulus truth boundary is not exact")


def face_edges(face: Sequence[int]) -> set[tuple[int, int]]:
    return {
        tuple(sorted((int(face[index]), int(face[(index + 1) % len(face)]))))
        for index in range(len(face))
    }


def smoothstep(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def barycentric_2d(
    point: Sequence[float],
    first: Sequence[float],
    second: Sequence[float],
    third: Sequence[float],
) -> tuple[float, float, float]:
    ax, ay = map(float, first)
    bx, by = map(float, second)
    cx, cy = map(float, third)
    px, py = map(float, point)
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(denominator) <= 1.0e-15:
        raise AnnulusError("harmonic carrier contains a degenerate chart triangle")
    u = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
    v = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
    return u, v, 1.0 - u - v


def build_carrier(
    design: Mapping[str, Any], repair_core: Any, author: Any
) -> dict[str, Any]:
    from mathutils import Vector

    body = design["body"]
    selected_faces = design["selected_faces"]
    target_cycle = design["target_cycle"]
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    selected_vertices = sorted(
        {vertex for face_index in selected_faces for vertex in faces[face_index]}
    )
    selected_set = set(selected_vertices)
    adjacency: dict[int, set[int]] = {index: set() for index in selected_vertices}
    for face_index in selected_faces:
        for edge in face_edges(faces[face_index]):
            adjacency[edge[0]].add(edge[1])
            adjacency[edge[1]].add(edge[0])
    target_world = [body.matrix_world @ body.data.vertices[index].co for index in target_cycle]
    target_parameters = author.cycle_parameters([tuple(value) for value in target_world])
    boundary = {
        vertex: (
            math.cos(2.0 * math.pi * target_parameters[offset]),
            math.sin(2.0 * math.pi * target_parameters[offset]),
        )
        for offset, vertex in enumerate(target_cycle)
    }
    chart = repair_core.harmonic_interpolate_boundary_field(
        adjacency, boundary, tolerance=1.0e-12
    )
    triangles = []
    signs = []
    for face_index in sorted(selected_faces):
        face = faces[face_index]
        if len(face) != 3:
            raise AnnulusError("R19 selected carrier is no longer triangulated")
        coordinates = [chart[index] for index in face]
        signed = 0.5 * (
            (coordinates[1][0] - coordinates[0][0])
            * (coordinates[2][1] - coordinates[0][1])
            - (coordinates[1][1] - coordinates[0][1])
            * (coordinates[2][0] - coordinates[0][0])
        )
        if abs(signed) <= 1.0e-14:
            raise AnnulusError("harmonic carrier produced a zero-area triangle")
        signs.append(signed)
        triangles.append((face_index, face, coordinates))
    positive = sum(value > 0.0 for value in signs)
    negative = sum(value < 0.0 for value in signs)
    if positive and negative:
        raise AnnulusError("harmonic carrier chart folded")

    source_weights = {
        index: author.source_weights(body, index) for index in selected_vertices
    }

    def locate(point: tuple[float, float]) -> tuple[int, tuple[int, int, int], tuple[float, float, float]]:
        best = None
        for face_index, face, coordinates in triangles:
            bary = barycentric_2d(point, *coordinates)
            minimum = min(bary)
            if minimum >= -1.0e-9:
                return face_index, face, bary
            if best is None or minimum > best[0]:
                best = (minimum, face_index, face, bary)
        raise AnnulusError(
            "chart point is not strictly contained by a carrier triangle: "
            f"point={point}, best={best}"
        )

    def lift(point: tuple[float, float]) -> dict[str, Any]:
        face_index, face, bary = locate(point)
        world = sum(
            (
                (body.matrix_world @ body.data.vertices[vertex].co)
                * float(coefficient)
                for vertex, coefficient in zip(face, bary)
            ),
            Vector(),
        )
        combined: dict[str, float] = defaultdict(float)
        for vertex, coefficient in zip(face, bary):
            for name, value in source_weights[vertex].items():
                combined[name] += float(coefficient) * float(value)
        return {
            "world": world,
            "face_index": face_index,
            "face_vertices": face,
            "barycentric": bary,
            "weights": dict(combined),
        }

    return {
        "chart": chart,
        "target_parameters": target_parameters,
        "lift": lift,
        "selected_vertex_count": len(selected_set),
        "selected_face_count": len(selected_faces),
        "chart_sha256": canonical_sha256(
            [[index, *chart[index]] for index in sorted(chart)]
        ),
        "chart_signed_area_minimum": min(abs(value) for value in signs),
        "chart_orientation": "positive" if positive else "negative",
    }


def prepare_annulus(
    design: Mapping[str, Any],
    carrier: Mapping[str, Any],
    variant: Mapping[str, Any],
    repair_core: Any,
    author: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from mathutils import Vector

    base = design["prepared"]
    body = design["body"]
    target_cycle = design["target_cycle"]
    target_count = len(target_cycle)
    ring_size = int(base["collar_ring_size"])
    ring_count = int(variant["ring_count"])
    inner_radius = float(variant["inner_radius"])
    blend_power = float(variant["blend_power"])
    if not 0.1 <= inner_radius <= 0.65 or ring_count < 3:
        raise AnnulusError("annulus variant is outside its bounded contract")
    old_donor_start = int(base["donor_start"])
    donor_order = [int(value) for value in base["donor_vertex_order"]]
    old_donor_to_local = {
        donor_index: old_donor_start + offset
        for offset, donor_index in enumerate(donor_order)
    }
    aligned_cycle = [int(value) for value in base["donor_boundary_order"]]
    donor_parameters = author.cycle_parameters(
        [
            tuple(design["base_world"][old_donor_to_local[index]])
            for index in aligned_cycle
        ]
    )
    new_donor_start = target_count + ring_count * ring_size
    new_donor_to_local = {
        donor_index: new_donor_start + offset
        for offset, donor_index in enumerate(donor_order)
    }
    local_rings = [
        list(
            range(
                target_count + ring * ring_size,
                target_count + (ring + 1) * ring_size,
            )
        )
        for ring in range(ring_count)
    ]
    local_donor_boundary = [new_donor_to_local[index] for index in aligned_cycle]
    positions_world: list[Any] = [
        body.matrix_world @ body.data.vertices[index].co for index in target_cycle
    ]
    carrier_records: dict[tuple[int, int], dict[str, Any]] = {}
    inner_carrier = []
    for parameter in donor_parameters:
        angle = 2.0 * math.pi * float(parameter)
        point = (inner_radius * math.cos(angle), inner_radius * math.sin(angle))
        inner_carrier.append(carrier["lift"](point))
    donor_boundary_world = [
        design["base_world"][old_donor_to_local[index]] for index in aligned_cycle
    ]
    for ring in range(ring_count):
        t = float(ring + 1) / float(ring_count + 1)
        radius = 1.0 - t * (1.0 - inner_radius)
        blend = smoothstep(t) ** blend_power
        for offset, parameter in enumerate(donor_parameters):
            angle = 2.0 * math.pi * float(parameter)
            carrier_point = carrier["lift"](
                (radius * math.cos(angle), radius * math.sin(angle))
            )
            delta = donor_boundary_world[offset] - inner_carrier[offset]["world"]
            positions_world.append(carrier_point["world"] + delta * blend)
            carrier_records[(ring, offset)] = carrier_point
    for donor_index in donor_order:
        positions_world.append(design["base_world"][old_donor_to_local[donor_index]])

    faces = []
    faces.extend(
        author.zipper_bridge_parameterized(
            list(range(target_count)),
            carrier["target_parameters"],
            local_rings[0],
            donor_parameters,
        )
    )
    for first, second in zip(local_rings, local_rings[1:]):
        faces.extend(author.matching_cycle_triangles(first, second))
    faces.extend(author.matching_cycle_triangles(local_rings[-1], local_donor_boundary))
    old_local_to_donor = {value: key for key, value in old_donor_to_local.items()}
    old_donor_local_set = set(old_local_to_donor)
    donor_faces = [
        tuple(map(int, face))
        for face in base["faces"]
        if set(map(int, face)).issubset(old_donor_local_set)
    ]
    if len(donor_faces) != 2488:
        raise AnnulusError(
            "dynamic donor-core face derivation no longer returns the exact "
            f"accepted 2488 faces: {len(donor_faces)}"
        )
    donor_face_sha256 = canonical_sha256(donor_faces)
    for old_face in donor_faces:
        faces.append(
            tuple(new_donor_to_local[old_local_to_donor[int(value)]] for value in old_face)
        )
    oriented = repair_core.orient_disk_faces_from_retained_boundary(
        faces, design["retained_directed_edges"]
    )
    faces = [tuple(face) for face in oriented.faces]
    inverse = body.matrix_world.inverted()
    positions_local = [tuple(inverse @ value) for value in positions_world]

    # Stable pose-aware palette: collar weights start from the exact R19
    # carrier and continuously transfer to pelvis; the clean donor core is
    # rigidly pelvis-owned so internal detail does not shear across thigh bones.
    new_weights: dict[int, dict[str, float]] = {}
    for ring in range(ring_count):
        t = float(ring + 1) / float(ring_count + 1)
        transfer = smoothstep(t) ** blend_power
        for offset in range(ring_size):
            raw = carrier_records[(ring, offset)]["weights"]
            blended = {
                name: (1.0 - transfer) * float(value)
                for name, value in raw.items()
                if float(value) > 0.0
            }
            blended["pelvis_04"] = blended.get("pelvis_04", 0.0) + transfer
            new_weights[local_rings[ring][offset]] = (
                repair_core.project_top_four_normalized_weights(blended)
            )
    for local_index in range(new_donor_start, len(positions_local)):
        new_weights[local_index] = {"pelvis_04": 1.0}

    # Preserve one exact source UV branch at every seam vertex and the exact
    # donor-core planar UV field.  Interpolate only the annulus between them.
    source = design["source_snapshot"]
    uv_fields = {}
    uv_choice_evidence = {}
    for layer_name, old_field in sorted(base["uv_fields"].items()):
        candidates = [source["seam"][vertex]["uv"][layer_name] for vertex in target_cycle]
        chosen = repair_core.minimum_variation_closed_cycle_choices(candidates)
        exact_choice_errors = [
            min(
                math.dist(tuple(map(float, selected)), tuple(map(float, candidate)))
                for candidate in candidates[index]
            )
            for index, selected in enumerate(chosen)
        ]
        uv_choice_evidence[layer_name] = {
            "chosen_exact_cycle_sha256": canonical_sha256(chosen),
            "maximum_exact_source_choice_error": max(exact_choice_errors, default=0.0),
            "all_choices_exact_at_1e_12": all(
                error <= 1.0e-12 for error in exact_choice_errors
            ),
        }
        field: list[tuple[float, float]] = [(0.0, 0.0)] * len(positions_local)
        for index, value in enumerate(chosen):
            field[index] = tuple(map(float, value))
        for donor_index in donor_order:
            field[new_donor_to_local[donor_index]] = tuple(
                map(float, old_field[old_donor_to_local[donor_index]])
            )
        transition_nodes = set(range(target_count, new_donor_start)).union(
            range(target_count)
        ).union(local_donor_boundary)
        adjacency: dict[int, set[int]] = {index: set() for index in transition_nodes}
        for face in faces:
            for edge in face_edges(face):
                if edge[0] in transition_nodes and edge[1] in transition_nodes:
                    adjacency[edge[0]].add(edge[1])
                    adjacency[edge[1]].add(edge[0])
        fixed = {index: field[index] for index in range(target_count)}
        fixed.update({index: field[index] for index in local_donor_boundary})
        solved = repair_core.harmonic_interpolate_boundary_field(
            adjacency, fixed, tolerance=1.0e-12
        )
        for index, value in solved.items():
            field[index] = tuple(map(float, value))
        uv_fields[layer_name] = field

    # Use the already sealed base field, avoiding dependence on mutable defaults.
    base_tint = tuple(float(value) for value in base["tint_rgba"][0][:3])
    donor_boundary_tint = [
        tuple(map(float, base["tint_rgba"][old_donor_to_local[index]][:3]))
        for index in aligned_cycle
    ]
    tint = [base_tint + (1.0,) for _index in target_cycle]
    for ring in range(ring_count):
        t = smoothstep(float(ring + 1) / float(ring_count + 1)) ** blend_power
        for color in donor_boundary_tint:
            tint.append(
                tuple((1.0 - t) * base_tint[axis] + t * color[axis] for axis in range(3))
                + (1.0,)
            )
    for donor_index in donor_order:
        tint.append(tuple(map(float, base["tint_rgba"][old_donor_to_local[donor_index]])))

    prepared = dict(base)
    prepared.update(
        {
            "positions_body_local": positions_local,
            "positions_world": [tuple(value) for value in positions_world],
            "faces": faces,
            "collar_ring_count": ring_count,
            "collar_ring_size": ring_size,
            "donor_start": new_donor_start,
            "new_weights": new_weights,
            "uv_fields": uv_fields,
            "tint_rgba": tint,
            "topology_sha256": canonical_sha256(faces),
            "position_sha256": canonical_sha256(positions_local),
            "weight_sha256": canonical_sha256(new_weights),
            "uv_sha256": canonical_sha256(uv_fields),
            "tint_sha256": canonical_sha256(tint),
        }
    )
    expected_patch_edges = len(set().union(*(face_edges(face) for face in faces)))
    return prepared, {
        "ring_count": ring_count,
        "ring_size": ring_size,
        "inner_radius": inner_radius,
        "blend_power": blend_power,
        "patch_vertices": len(positions_local),
        "patch_faces": len(faces),
        "patch_edges": expected_patch_edges,
        "patch_euler": len(positions_local) - expected_patch_edges + len(faces),
        "orientation_flip_count": len(oriented.flipped_face_indices),
        "donor_face_derivation": {
            "method": "all_base_faces_whose_vertices_are_all_in_dynamic_donor_local_set",
            "count": len(donor_faces),
            "sha256": donor_face_sha256,
        },
        "weight_field_hypothesis": (
            "CARRIER_TO_RIGID_PELVIS_BLEND_NOT_HARMONIC; "
            "eligibility_requires_the_separate_source-envelope_gradient_gate"
        ),
        "harmonic_weight_field_claimed": False,
        "uv_exact_source_choices": uv_choice_evidence,
        "topology_sha256": prepared["topology_sha256"],
        "position_sha256": prepared["position_sha256"],
        "weight_sha256": prepared["weight_sha256"],
        "uv_sha256": prepared["uv_sha256"],
    }


def dynamic_topology_gate(
    body: Any,
    patch_faces: set[int],
    prepared: Mapping[str, Any],
    topology: Any,
    source_topology: Mapping[str, Any],
    attempt04: Any,
) -> dict[str, Any]:
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    whole = topology.topology_record(faces, range(len(faces)))
    patch = topology.topology_record(faces, patch_faces)
    edge_faces = topology.edge_face_map(faces)
    mesh_edge_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for edge in body.data.edges:
        key = tuple(sorted(map(int, edge.vertices)))
        mesh_edge_groups[key].append(int(edge.index))
    duplicate_mesh_edges = {
        edge: indices for edge, indices in mesh_edge_groups.items() if len(indices) != 1
    }
    mesh_edges = set(mesh_edge_groups)
    face_edges_set = set(edge_faces)
    boundary = {edge for edge, owners in edge_faces.items() if len(owners) == 1}
    baseline = attempt04.RUNTIME.get("source_baseline")
    final_map = attempt04.RUNTIME.get("final_stable_vertex_map")
    if not baseline or not final_map:
        raise AnnulusError("dynamic topology gate lacks Attempt04 stable source state")
    global_to_token = final_map.get("global_to_token")
    if not isinstance(global_to_token, Mapping) or set(global_to_token) != set(
        range(len(body.data.vertices))
    ):
        raise AnnulusError("Attempt04 stable vertex map does not cover the exact candidate")
    stable_boundary = attempt04.stable_edges_from_global(boundary, global_to_token)
    source_boundary = attempt04.source_stable_edges(baseline["_boundary_set"])
    new_boundary = stable_boundary.difference(source_boundary)
    missing_boundary = source_boundary.difference(stable_boundary)
    checks = {
        "whole_one_component": whole["component_count"] == 1,
        "whole_boundary_preserved": whole["boundary_edge_count"]
        == source_topology["whole"]["boundary_edge_count"],
        "whole_boundary_cycles_preserved": whole["boundary_cycle_lengths"]
        == source_topology["whole"]["boundary_cycle_lengths"],
        "zero_overused_edges": not any(len(owners) > 2 for owners in edge_faces.values()),
        "zero_loose_mesh_edges": mesh_edges == face_edges_set,
        "zero_duplicate_mesh_edges": not duplicate_mesh_edges,
        "stable_source_boundary_exact": stable_boundary == source_boundary,
        "zero_new_stable_boundary_edges": not new_boundary,
        "zero_missing_stable_boundary_edges": not missing_boundary,
        "patch_vertex_count": patch["vertex_count"]
        == len(prepared["positions_body_local"]),
        "patch_face_count": patch["face_count"] == len(prepared["faces"]),
        "patch_one_disk": bool(patch["is_one_disk"]),
        "patch_boundary_91": patch["boundary_cycle_lengths"] == [91],
        "patch_euler_one": patch["euler_characteristic"] == 1,
    }
    return {
        "whole": whole,
        "patch": patch,
        "stable_boundary_preservation": {
            "source_count": len(source_boundary),
            "candidate_count": len(stable_boundary),
            "source_sha256": attempt04.edge_set_sha256(source_boundary),
            "candidate_sha256": attempt04.edge_set_sha256(stable_boundary),
            "new_count": len(new_boundary),
            "new_sha256": attempt04.edge_set_sha256(new_boundary),
            "missing_count": len(missing_boundary),
            "missing_sha256": attempt04.edge_set_sha256(missing_boundary),
        },
        "duplicate_mesh_edge_group_count": len(duplicate_mesh_edges),
        "duplicate_mesh_edge_group_sha256": canonical_sha256(
            [[list(edge), indices] for edge, indices in sorted(duplicate_mesh_edges.items())]
        ),
        "checks": checks,
        "passed": all(checks.values()),
    }


def weight_map(body: Any, vertex: int) -> dict[str, float]:
    return {
        body.vertex_groups[int(item.group)].name: float(item.weight)
        for item in body.data.vertices[int(vertex)].groups
        if float(item.weight) > 0.0
    }


def source_weight_gradient_envelope(
    design: Mapping[str, Any], simulation: Any
) -> dict[str, Any]:
    body = design["body"]
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    selected_edges = {
        edge
        for face_index in design["selected_faces"]
        for edge in face_edges(faces[int(face_index)])
    }
    named = {
        int(vertex.index): weight_map(body, int(vertex.index))
        for vertex in body.data.vertices
    }
    deltas = [
        simulation.weight_distance(named[first], named[second])
        for first, second in selected_edges
    ]
    if not deltas:
        raise AnnulusError("immutable R19 selected region has no weight-gradient edges")
    return {
        "source": "exact immutable R19 selected-mask edge field",
        "edge_count": len(selected_edges),
        "edge_sha256": canonical_sha256([list(edge) for edge in sorted(selected_edges)]),
        "weight_delta_p99": simulation.percentile(deltas, 0.99),
        "weight_delta_maximum": max(deltas),
    }


def patch_weight_gradient_gate(
    body: Any,
    patch_faces: set[int],
    source_envelope: Mapping[str, Any],
    simulation: Any,
) -> dict[str, Any]:
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    patch_edges = {
        edge
        for face_index in patch_faces
        for edge in face_edges(faces[int(face_index)])
    }
    patch_vertices = sorted({index for edge in patch_edges for index in edge})
    named = {index: weight_map(body, index) for index in patch_vertices}
    deltas = [
        simulation.weight_distance(named[first], named[second])
        for first, second in patch_edges
    ]
    if not deltas:
        raise AnnulusError("candidate replacement patch has no weight-gradient edges")
    patch_p99 = simulation.percentile(deltas, 0.99)
    patch_maximum = max(deltas)
    checks = {
        "patch_p99_not_above_exact_r19_selected_p99": patch_p99
        <= float(source_envelope["weight_delta_p99"]) + 1.0e-12,
        "patch_max_not_above_exact_r19_selected_max": patch_maximum
        <= float(source_envelope["weight_delta_maximum"]) + 1.0e-12,
    }
    return {
        "weight_field_hypothesis": (
            "CARRIER_TO_RIGID_PELVIS_BLEND_NOT_HARMONIC; this gate tests only "
            "the exact patch-edge gradient against the immutable R19 envelope"
        ),
        "harmonic_weight_field_claimed": False,
        "source_envelope": dict(source_envelope),
        "patch_edge_count": len(patch_edges),
        "patch_edge_sha256": canonical_sha256(
            [list(edge) for edge in sorted(patch_edges)]
        ),
        "patch_weight_delta_p99": patch_p99,
        "patch_weight_delta_maximum": patch_maximum,
        "checks": checks,
        "passed": all(checks.values()),
    }


def applied_uv_seam_choice_metrics(
    body: Any,
    patch_faces: set[int],
    source_snapshot: Mapping[str, Any],
    source_cycle: Sequence[int],
    candidate_cycle: Sequence[int],
    prepared: Mapping[str, Any],
) -> dict[str, Any]:
    if len(source_cycle) != len(candidate_cycle):
        raise AnnulusError("source and candidate seam cycles have different lengths")
    candidate_to_offset = {
        int(candidate_vertex): offset
        for offset, candidate_vertex in enumerate(candidate_cycle)
    }
    if len(candidate_to_offset) != len(candidate_cycle):
        raise AnnulusError("candidate seam cycle repeats a vertex")
    rows = {}
    for layer_name in sorted(prepared["uv_fields"]):
        layer = body.data.uv_layers.get(layer_name)
        if layer is None:
            raise AnnulusError(f"candidate lacks expected UV layer {layer_name}")
        loop_values: dict[int, list[tuple[float, float]]] = defaultdict(list)
        for face_index in patch_faces:
            polygon = body.data.polygons[int(face_index)]
            for loop_index in polygon.loop_indices:
                vertex = int(body.data.loops[int(loop_index)].vertex_index)
                if vertex in candidate_to_offset:
                    uv = layer.data[int(loop_index)].uv
                    loop_values[vertex].append((float(uv.x), float(uv.y)))
        source_choice_errors = []
        prescribed_choice_errors = []
        loop_sample_count = 0
        for candidate_vertex, offset in candidate_to_offset.items():
            values = loop_values.get(candidate_vertex, [])
            if not values:
                raise AnnulusError(
                    f"patch has no {layer_name} seam loop for vertex {candidate_vertex}"
                )
            source_vertex = int(source_cycle[offset])
            candidates = source_snapshot["seam"][source_vertex]["uv"][layer_name]
            prescribed = tuple(map(float, prepared["uv_fields"][layer_name][offset]))
            for value in values:
                source_choice_errors.append(
                    min(
                        math.dist(value, tuple(map(float, candidate)))
                        for candidate in candidates
                    )
                )
                prescribed_choice_errors.append(math.dist(value, prescribed))
                loop_sample_count += 1
        rows[layer_name] = {
            "seam_vertex_count": len(candidate_cycle),
            "patch_seam_loop_sample_count": loop_sample_count,
            "maximum_actual_exact_source_choice_error": max(source_choice_errors),
            "maximum_actual_prescribed_choice_error": max(prescribed_choice_errors),
            "passed": bool(source_choice_errors)
            and max(source_choice_errors) <= 1.0e-12
            and max(prescribed_choice_errors) <= 1.0e-12,
        }
    return rows


def install_capture_animation_guard(
    verifier: Any, state: dict[str, Any]
) -> tuple[Any, Any]:
    original = verifier.suspend_rig_action

    def guarded(rig: Any) -> None:
        if state.get("captured"):
            if state.get("rig") is not rig:
                raise AnnulusError("capture attempted to suspend more than one rig")
            original(rig)
            animation = rig.animation_data
            if animation is not None:
                for track, _mute in state["tracks"]:
                    track.mute = True
            assert_animation_isolated(rig)
            return
        animation = rig.animation_data
        state["captured"] = True
        state["rig"] = rig
        state["action"] = animation.action if animation is not None else None
        state["tracks"] = (
            [(track, bool(track.mute)) for track in animation.nla_tracks]
            if animation is not None
            else []
        )
        original(rig)
        if animation is not None:
            for track, _mute in state["tracks"]:
                track.mute = True
            if animation.action is not None or any(
                not bool(track.mute) for track, _mute in state["tracks"]
            ):
                raise AnnulusError("action/NLA isolation did not take effect during capture")
        state["public"] = {
            "active_action_was_present": state["action"] is not None,
            "nla_track_count": len(state["tracks"]),
            "nla_tracks_muted_for_capture_and_all_evaluation": True,
            "restored_after_evaluation": False,
        }

    return original, guarded


def assert_animation_isolated(rig: Any) -> None:
    animation = rig.animation_data
    if animation is None:
        return
    if animation.action is not None:
        raise AnnulusError("rig action became active during isolated evaluation")
    if any(not bool(track.mute) for track in animation.nla_tracks):
        raise AnnulusError("an NLA track became active during isolated evaluation")


def restore_animation_state(state: Mapping[str, Any]) -> None:
    if not state.get("captured"):
        return
    rig = state["rig"]
    animation = rig.animation_data
    if animation is None:
        if state.get("action") is not None or state.get("tracks"):
            raise AnnulusError("rig animation data disappeared before restoration")
        public = state.get("public")
        if isinstance(public, dict):
            public["restored_after_evaluation"] = True
        return
    animation.action = state.get("action")
    for track, mute in state.get("tracks", []):
        track.mute = bool(mute)
    public = state.get("public")
    if isinstance(public, dict):
        public["restored_after_evaluation"] = True


def source_seam_pose_stretch(
    config: Mapping[str, Any],
    body: Any,
    rig: Any,
    seam_cycle: Sequence[int],
    verifier: Any,
    bpy: Any,
) -> dict[str, Any]:
    assert_animation_isolated(rig)
    seam_edges = {
        tuple(sorted((int(seam_cycle[index]), int(seam_cycle[(index + 1) % len(seam_cycle)]))))
        for index in range(len(seam_cycle))
    }
    if len(seam_edges) != len(seam_cycle):
        raise AnnulusError("R19 seam cycle contains a duplicate edge")
    verifier.apply_pose(rig, {})
    bpy.context.view_layer.update()
    neutral_points = verifier.evaluated_points(body, bpy)
    neutral_lengths = verifier.edge_lengths(neutral_points, seam_edges)
    rows = {}
    try:
        for pose in config["poses"]:
            pose_id = str(pose["id"])
            if pose_id in rows:
                raise AnnulusError(f"duplicate verification pose id: {pose_id}")
            assert_animation_isolated(rig)
            verifier.apply_pose(rig, pose["rotations_degrees"])
            bpy.context.view_layer.update()
            points = verifier.evaluated_points(body, bpy)
            rows[pose_id] = {
                "maximum_seam_edge_stretch_ratio": verifier.ratio_maximum(
                    verifier.edge_lengths(points, seam_edges), neutral_lengths
                )
            }
    finally:
        verifier.apply_pose(rig, {})
        bpy.context.view_layer.update()
    if set(rows) != {str(pose["id"]) for pose in config["poses"]}:
        raise AnnulusError("exact R19 seam pose baseline is incomplete")
    return {
        "source": "live exact immutable R19 evaluation under isolated action/NLA state",
        "seam_edge_count": len(seam_edges),
        "seam_edge_sha256": canonical_sha256([list(edge) for edge in sorted(seam_edges)]),
        "poses": rows,
    }


def bound_file_state(source: Path, candidate: Path) -> dict[str, Any]:
    return {
        "source": {"bytes": source.stat().st_size, "sha256": sha256_file(source)},
        "candidate": {
            "bytes": candidate.stat().st_size,
            "sha256": sha256_file(candidate),
        },
    }


def evaluate_variant(
    config: Mapping[str, Any],
    variant: Mapping[str, Any],
    prepared: Mapping[str, Any],
    preparation: Mapping[str, Any],
    design: Mapping[str, Any],
    author_config: Mapping[str, Any],
    overlay: Mapping[str, Any],
    modules: Mapping[str, Any],
    exact_neutral: bool,
    exact_poses: bool,
) -> dict[str, Any]:
    bpy = modules["bpy"]
    bmesh = modules["bmesh"]
    attempt04 = modules["attempt04"]
    author = modules["author"]
    verifier = modules["verifier"]
    topology = modules["topology"]
    exact_module = modules["exact_module"]
    body = design["body"]
    rig = design["rig"]
    assert_animation_isolated(rig)
    source_mesh = modules["source_mesh"]
    body.data = source_mesh.copy()
    modified_mesh = body.data
    body.name = config["objects"]["r19_body"]
    base_materials = modules["base_materials"]
    properties = modules["source_properties"]
    try:
        attempt04.bind_attempt04_runtime(overlay)
        attempt04.RUNTIME["donor_memberships"] = design["donor_memberships"]
        applied = attempt04.attempt04_apply_patch(
            body,
            rig,
            design["selected_faces"],
            design["target_cycle"],
            prepared,
            author_config,
        )
        assert_animation_isolated(rig)
        body.data.update(calc_edges=True, calc_edges_loose=True)
        bpy.context.view_layer.update()
        patch_faces = {int(value) for value in applied["patch_face_indices"]}
        topology_result = dynamic_topology_gate(
            body,
            patch_faces,
            prepared,
            topology,
            design["source_snapshot"]["topology"],
            attempt04,
        )
        freeze = author.post_author_freeze_gate(
            body,
            rig,
            design["target_cycle"],
            applied["target_seam_global_indices"],
            design["preflight"],
        )
        body.data.update(calc_edges=True, calc_edges_loose=True)
        bpy.context.view_layer.update()
        continuity = verifier.seam_continuity(
            body,
            design["source_snapshot"],
            patch_faces,
            topology,
            config["continuity_thresholds"],
        )
        weights = verifier.patch_weights(
            body,
            patch_faces,
            {
                "maximum_positive_weights_per_patch_vertex": 4,
                "minimum_positive_weight_sum": 0.999999,
                "maximum_positive_weight_sum": 1.000001,
            },
            bpy,
        )
        weight_gradient = patch_weight_gradient_gate(
            body,
            patch_faces,
            modules["source_weight_gradient_envelope"],
            modules["simulation"],
        )
        uv_geometry = {
            layer_name: modules["simulation"].uv_geometry_metrics(
                body, patch_faces, layer_name
            )
            for layer_name in sorted(prepared["uv_fields"])
        }
        uv_choice = preparation["uv_exact_source_choices"]
        applied_uv_choice = applied_uv_seam_choice_metrics(
            body,
            patch_faces,
            design["source_snapshot"],
            design["target_cycle"],
            applied["target_seam_global_indices"],
            prepared,
        )
        uv_checks = {
            "at_least_one_uv_layer": bool(uv_geometry),
            "all_expected_layers_evaluated": set(uv_geometry)
            == set(prepared["uv_fields"])
            == set(uv_choice)
            == set(applied_uv_choice),
            "all_exact_seam_source_choices": all(
                bool(value["all_choices_exact_at_1e_12"])
                and float(value["maximum_exact_source_choice_error"]) <= 1.0e-12
                for value in uv_choice.values()
            ),
            "all_applied_patch_seam_loops_use_exact_source_choice": all(
                bool(value["passed"]) for value in applied_uv_choice.values()
            ),
            "zero_internal_zero_area_patch_faces": all(
                int(value["zero_area_count_at_1e_14"]) == 0
                for value in uv_geometry.values()
            ),
            "zero_internal_uv_fold_faces": all(
                int(value["opposite_dominant_sign_count"]) == 0
                for value in uv_geometry.values()
            ),
            "every_layer_covers_exact_patch_face_count": all(
                int(value["face_count"]) == len(patch_faces)
                for value in uv_geometry.values()
            ),
        }
        uv_gate = {
            "prepared_exact_seam_source_choice": uv_choice,
            "applied_exact_seam_source_choice": applied_uv_choice,
            "per_layer_patch_geometry": uv_geometry,
            "checks": uv_checks,
            "passed": all(uv_checks.values()),
        }
        stretch = modules["simulation"].cheap_pose_stretch(
            config,
            body,
            rig,
            patch_faces,
            applied["target_seam_global_indices"],
            verifier,
            topology,
            bpy,
        )
        source_seam = modules["source_seam_stretch"]["poses"]
        if set(stretch) != set(source_seam):
            raise AnnulusError("candidate and exact R19 seam pose sets differ")
        seam_nonregression = {
            pose_id: {
                "candidate_maximum_seam_edge_stretch_ratio": float(
                    stretch[pose_id]["maximum_seam_edge_stretch_ratio"]
                ),
                "exact_r19_maximum_seam_edge_stretch_ratio": float(
                    source_seam[pose_id]["maximum_seam_edge_stretch_ratio"]
                ),
                "absolute_delta": float(
                    stretch[pose_id]["maximum_seam_edge_stretch_ratio"]
                )
                - float(source_seam[pose_id]["maximum_seam_edge_stretch_ratio"]),
                "passed": float(stretch[pose_id]["maximum_seam_edge_stretch_ratio"])
                <= float(source_seam[pose_id]["maximum_seam_edge_stretch_ratio"])
                + 1.0e-12,
            }
            for pose_id in sorted(stretch)
        }
        broad_pairs = modules["simulation"].broad_patch_pairs(
            body, patch_faces, verifier, exact_module, bpy, bmesh
        )
        worst_new = max(
            value["maximum_new_patch_edge_stretch_ratio"] for value in stretch.values()
        )
        hard = {
            "dynamic_topology": topology_result["passed"],
            "freeze": all(freeze["checks"].values()),
            "seam_continuity": all(continuity["checks"].values()),
            "weights": bool(weights["passed"]),
            "patch_weight_gradient_nonregression": bool(weight_gradient["passed"]),
            "uv_geometry_and_exact_seam_choice": bool(uv_gate["passed"]),
            "exact_r19_seam_pose_nonregression": all(
                value["passed"] for value in seam_nonregression.values()
            ),
            "new_edge_stretch_at_or_below_1_35": worst_new
            <= config["continuity_thresholds"]["maximum_pose_patch_edge_stretch_ratio"],
        }
        row: dict[str, Any] = {
            "id": variant["id"],
            "variant": dict(variant),
            "topology": topology_result,
            "freeze_checks": freeze["checks"],
            "continuity": continuity,
            "weights": weights,
            "weight_gradient": weight_gradient,
            "uv_gate": uv_gate,
            "pose_stretch": stretch,
            "exact_r19_seam_pose_nonregression": seam_nonregression,
            "broad_phase": broad_pairs,
            "worst_new_patch_edge_stretch_ratio": worst_new,
            "hard_checks": hard,
            "hard_gate_fail_count": sum(not value for value in hard.values()),
        }
        if exact_neutral or exact_poses:
            exact = verifier.exact_intersections(body, bpy, bmesh, exact_module)
            pairs = {tuple(value) for value in exact["genuine_index_pairs"]}
            patch_pairs = sorted(
                [list(pair) for pair in pairs if any(index in patch_faces for index in pair)]
            )
            source_pairs = Counter(
                tuple(value)
                for value in design["source_snapshot"]["exact_intersections"]["genuine_geometry_pairs"]
            )
            candidate_pairs = Counter(tuple(value) for value in exact["genuine_geometry_pairs"])
            new_pairs = candidate_pairs - source_pairs
            exact_checks = {
                "candidate_not_above_inherited_count": len(pairs) <= 29,
                "zero_patch_pairs": not patch_pairs,
                "zero_new_geometry_pairs": not new_pairs,
            }
            row["exact_neutral"] = {
                "genuine_pair_count": len(pairs),
                "patch_pair_count": len(patch_pairs),
                "patch_pairs": patch_pairs,
                "new_geometry_pair_count": sum(new_pairs.values()),
                "checks": exact_checks,
                "passed": all(exact_checks.values()),
            }
            if exact_poses:
                poses, _points = verifier.deformation_series(
                    config,
                    body,
                    rig,
                    patch_faces,
                    applied["target_seam_global_indices"],
                    exact,
                    bpy,
                    bmesh,
                    exact_module,
                    topology,
                )
                condensed = {}
                for pose_id, pose in poses.items():
                    repairable = dict(pose["checks"])
                    legacy_seam = repairable.pop("seam_edge_stretch_bounded")
                    repairable.pop("patch_edge_stretch_bounded")
                    repairable["new_patch_edge_stretch_bounded"] = (
                        stretch[pose_id]["maximum_new_patch_edge_stretch_ratio"]
                        <= config["continuity_thresholds"]["maximum_pose_patch_edge_stretch_ratio"]
                    )
                    source_seam_ratio = float(
                        source_seam[pose_id]["maximum_seam_edge_stretch_ratio"]
                    )
                    exact_seam_ratio = float(pose["maximum_seam_edge_stretch_ratio"])
                    repairable["exact_r19_seam_pose_nonregression"] = (
                        exact_seam_ratio <= source_seam_ratio + 1.0e-12
                    )
                    condensed[pose_id] = {
                        "exact_pair_count": pose["exact_genuine_pair_count"],
                        "new_pair_count": len(pose["new_exact_pairs_vs_candidate_neutral"]),
                        "patch_pair_count": len(pose["patch_involving_exact_pairs"]),
                        "maximum_new_patch_edge_stretch_ratio": stretch[pose_id]["maximum_new_patch_edge_stretch_ratio"],
                        "maximum_seam_edge_stretch_ratio": pose["maximum_seam_edge_stretch_ratio"],
                        "exact_r19_maximum_seam_edge_stretch_ratio": source_seam_ratio,
                        "seam_stretch_delta_vs_exact_r19": exact_seam_ratio
                        - source_seam_ratio,
                        "legacy_seam_gate": legacy_seam,
                        "repairable_checks": repairable,
                        "repairable_passed": all(repairable.values()),
                        "contact_proxy": pose["contact_proxy"],
                    }
                row["exact_poses"] = condensed
                row["all_repairable_pose_gates_passed"] = all(
                    value["repairable_passed"] for value in condensed.values()
                )
        return row
    finally:
        verifier.apply_pose(rig, {})
        bpy.context.view_layer.update()
        body.data = source_mesh
        body.name = config["objects"]["r19_body"]
        for key in list(body.keys()):
            if key not in properties:
                del body[key]
        for key, value in properties.items():
            body[key] = value
        if modified_mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(modified_mesh)
        for material in list(bpy.data.materials):
            if material not in base_materials and material.users == 0:
                bpy.data.materials.remove(material)
        attempt04.RUNTIME.clear()


def run(config_path: Path, execute: bool) -> int:
    if not execute:
        raise AnnulusError("explicit --execute-readonly-simulation is required")
    expected_config_path = project_path(EXPECTED_CONFIG_RELATIVE_PATH)
    if (
        not config_path.is_file()
        or config_path.is_symlink()
        or config_path.resolve() != expected_config_path.resolve()
    ):
        raise AnnulusError("the exact reviewed annulus config path is required")
    config = read_json(config_path)
    validate_config(config)
    paths = {
        label: require_binding(value, label)
        for label, value in config["bindings"].items()
    }
    if paths["worker"].resolve() != Path(__file__).resolve():
        raise AnnulusError("configured worker differs from executing worker")
    output_dir = project_path(config["output"]["directory"])
    output_path = output_dir / config["output"]["filename"]
    expected_output_dir = project_path(EXPECTED_OUTPUT["directory"])
    if output_dir.resolve() != expected_output_dir.resolve():
        raise AnnulusError("annulus output escaped its exact append-only root")
    if output_dir.exists():
        raise AnnulusError("append-only annulus output exists")
    source = paths["r19_source"]
    candidate = paths["attempt05_candidate"]
    before = bound_file_state(source, candidate)
    output_dir.mkdir(parents=True, exist_ok=False)
    animation_state: dict[str, Any] = {}
    try:
        import bmesh
        import bpy
        from tools import blender_author_kira_r23_cc0_afes_attempt01 as author
        from tools import blender_author_kira_r23_cc0_afes_attempt04_wrapper as attempt04
        from tools import blender_exact_mesh_intersections as exact_module
        from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as preflight_module
        from tools import blender_simulate_kira_r23_localized_patch_repair as simulation
        from tools import blender_verify_kira_r23_postsave_fresh_reopen as verifier
        from tools import kira_r23_blender51_action_serializer as actions_module
        from tools import kira_r23_cc0_afes_preflight_core as topology
        from tools import kira_r23_localized_patch_repair_core as repair_core

        if Path(simulation.__file__).resolve() != paths[
            "localized_simulation_worker"
        ].resolve():
            raise AnnulusError("imported localized simulation worker differs from binding")
        if Path(repair_core.__file__).resolve() != paths["repair_core"].resolve():
            raise AnnulusError("imported repair core differs from binding")

        author_config = read_json(paths["author_config"])
        verification = read_json(paths["verification_config"])
        overlay = read_json(paths["attempt05_repair_overlay"])
        original_suspend, guarded_suspend = install_capture_animation_guard(
            verifier, animation_state
        )
        original_reproduce_preflight = author.reproduce_passed_preflight

        def reproduce_preflight_with_isolated_animation(
            sealed_author_config: Mapping[str, Any],
        ) -> Any:
            rig = bpy.data.objects.get(verification["objects"]["rig"])
            if rig is None:
                raise AnnulusError("rig is absent immediately before design capture")
            guarded_suspend(rig)
            return original_reproduce_preflight(sealed_author_config)

        verifier.suspend_rig_action = guarded_suspend
        author.reproduce_passed_preflight = reproduce_preflight_with_isolated_animation
        try:
            design = simulation.capture_design(
                author_config,
                verification,
                overlay,
                bpy,
                bmesh,
                author,
                attempt04,
                verifier,
                preflight_module,
                actions_module,
                exact_module,
                topology,
            )
        finally:
            verifier.suspend_rig_action = original_suspend
            author.reproduce_passed_preflight = original_reproduce_preflight
        if not animation_state.get("captured"):
            raise AnnulusError("capture did not pass through the action/NLA isolation guard")
        assert_animation_isolated(design["rig"])
        source_weight_envelope = source_weight_gradient_envelope(design, simulation)
        source_seam_stretch = source_seam_pose_stretch(
            verification,
            design["body"],
            design["rig"],
            design["target_cycle"],
            verifier,
            bpy,
        )
        carrier = build_carrier(design, repair_core, author)
        prepared_variants = {}
        preparation_rows = {}
        variants = []
        for inner_radius in config["parameter_grid"]["inner_radius"]:
            for blend_power in config["parameter_grid"]["blend_power"]:
                variant = {
                    "id": f"r{float(inner_radius):.2f}_p{float(blend_power):.2f}",
                    "ring_count": int(config["parameter_grid"]["ring_count"]),
                    "inner_radius": float(inner_radius),
                    "blend_power": float(blend_power),
                }
                prepared, preparation = prepare_annulus(
                    design, carrier, variant, repair_core, author
                )
                prepared_variants[variant["id"]] = prepared
                preparation_rows[variant["id"]] = preparation
                variants.append(variant)
        variant_ids = [str(value["id"]) for value in variants]
        expected_variant_ids = [
            f"r{float(inner_radius):.2f}_p{float(blend_power):.2f}"
            for inner_radius in EXPECTED_PARAMETER_GRID["inner_radius"]
            for blend_power in EXPECTED_PARAMETER_GRID["blend_power"]
        ]
        if variant_ids != expected_variant_ids or len(set(variant_ids)) != len(variant_ids):
            raise AnnulusError("annulus variant IDs are not exact and unique")
        donor = design["donor"]
        bpy.data.objects.remove(donor, do_unlink=True)
        modules = {
            "bpy": bpy,
            "bmesh": bmesh,
            "author": author,
            "attempt04": attempt04,
            "verifier": verifier,
            "topology": topology,
            "exact_module": exact_module,
            "simulation": simulation,
            "source_mesh": design["body"].data,
            "base_materials": set(bpy.data.materials),
            "source_properties": {key: design["body"][key] for key in design["body"].keys()},
            "source_weight_gradient_envelope": source_weight_envelope,
            "source_seam_stretch": source_seam_stretch,
        }
        stage_a = [
            evaluate_variant(
                verification,
                variant,
                prepared_variants[variant["id"]],
                preparation_rows[variant["id"]],
                design,
                author_config,
                overlay,
                modules,
                exact_neutral=False,
                exact_poses=False,
            )
            for variant in variants
        ]
        ranked = sorted(
            stage_a,
            key=lambda row: (
                row["hard_gate_fail_count"],
                row["broad_phase"]["patch_involving_bvh_pair_count"],
                row["worst_new_patch_edge_stretch_ratio"],
                -row["continuity"]["minimum_patch_retained_normal_dot"],
                row["variant"]["inner_radius"],
                row["variant"]["blend_power"],
            ),
        )
        shortlist = [row["id"] for row in ranked[:4]]
        by_id = {value["id"]: value for value in variants}
        stage_b = [
            evaluate_variant(
                verification,
                by_id[variant_id],
                prepared_variants[variant_id],
                preparation_rows[variant_id],
                design,
                author_config,
                overlay,
                modules,
                exact_neutral=True,
                exact_poses=False,
            )
            for variant_id in shortlist
        ]
        neutral_pass = [row for row in stage_b if row["exact_neutral"]["passed"]]
        neutral_pass.sort(
            key=lambda row: (
                row["hard_gate_fail_count"],
                row["worst_new_patch_edge_stretch_ratio"],
                row["id"],
            )
        )
        stage_c = [
            evaluate_variant(
                verification,
                by_id[row["id"]],
                prepared_variants[row["id"]],
                preparation_rows[row["id"]],
                design,
                author_config,
                overlay,
                modules,
                exact_neutral=True,
                exact_poses=True,
            )
            for row in neutral_pass[:2]
        ]
        eligible = [
            row
            for row in stage_c
            if row["hard_gate_fail_count"] == 0
            and row["exact_neutral"]["passed"]
            and row.get("all_repairable_pose_gates_passed") is True
        ]
        eligible.sort(key=lambda row: (row["worst_new_patch_edge_stretch_ratio"], row["id"]))
        selected = eligible[0]["id"] if eligible else None
        restore_animation_state(animation_state)
        after = bound_file_state(source, candidate)
        if before != after:
            raise AnnulusError("bound source or Attempt05 candidate changed")
        result = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_CARRIER_ANNULUS_REPAIR_READONLY_SIMULATION",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": (
                "READONLY_CARRIER_ANNULUS_HYPOTHESIS_PASSED_ALL_ADDED_GATES_NOT_AUTHOR_SAVE_AUTHORIZATION"
                if selected
                else "NO_CARRIER_ANNULUS_VARIANT_PASSED_ALL_ADDED_FAIL_CLOSED_GATES"
            ),
            "selected_variant_id": selected,
            "all_added_gates_passed": selected is not None,
            "validated_execution_contract": {
                "config_path": relative(config_path),
                "config_bytes": config_path.stat().st_size,
                "config_sha256": sha256_file(config_path),
                "bound_status": config["status"],
                "parameter_grid": config["parameter_grid"],
                "execution_restrictions": config["execution_restrictions"],
                "output": config["output"],
                "variant_ids_exact_and_unique": True,
            },
            "carrier": {key: value for key, value in carrier.items() if key != "lift" and key != "chart"},
            "exact_r19_weight_gradient_envelope": source_weight_envelope,
            "exact_r19_seam_pose_baseline": source_seam_stretch,
            "animation_isolation": animation_state.get("public", {}),
            "variant_preparation": preparation_rows,
            "stage_a": stage_a,
            "stage_a_ranked_variant_ids": [row["id"] for row in ranked],
            "stage_a_ranking_order": [
                "hard_gate_fail_count",
                "broad_phase.patch_involving_bvh_pair_count",
                "worst_new_patch_edge_stretch_ratio",
                "negative_continuity.minimum_patch_retained_normal_dot",
                "inner_radius",
                "blend_power",
            ],
            "stage_b_shortlist_variant_ids": shortlist,
            "stage_b_exact_neutral": stage_b,
            "stage_c_exact_poses": stage_c,
            "immutability": {"before": before, "after": after, "unchanged": before == after},
            "operations": {
                "blend_saved": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_or_person_state_mutated": False,
                "candidate_created": False,
            },
            "truth_boundary": [
                "External topology, geometry, UV, skinning, intersection, deformation, and contact-proxy evidence only.",
                "Not owner visual approval and not internal physiology, bathroom function, pregnancy, sensation, privacy-memory, or biological-function evidence."
            ]
        }
        with output_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(json.dumps({"status": result["status"], "selected": selected, "output": relative(output_path)}))
        return 0
    except Exception:
        caught = sys.exc_info()[1]
        caught_traceback = traceback.format_exc()
        restoration_error = None
        try:
            restore_animation_state(animation_state)
        except Exception:
            restoration_error = {
                "exception_type": type(sys.exc_info()[1]).__name__,
                "exception": str(sys.exc_info()[1]),
                "traceback": traceback.format_exc(),
            }
        failure_after = bound_file_state(source, candidate)
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_CARRIER_ANNULUS_REPAIR_SIMULATION_FAILURE",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(caught).__name__,
            "exception": str(caught),
            "traceback": caught_traceback,
            "bound_file_immutability": {
                "before": before,
                "after_failure": failure_after,
                "unchanged": before == failure_after,
            },
            "animation_isolation": animation_state.get("public", {}),
            "animation_restoration_error": restoration_error,
            "operations": {"blend_saved": False, "render_performed": False, "export_performed": False}
        }
        with (output_dir / "FAILURE_EVIDENCE.json").open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(failure, handle, indent=2, sort_keys=True)
            handle.write("\n")
        raise


def main() -> int:
    parsed = arguments()
    return run(project_path(parsed.config), bool(parsed.execute_readonly_simulation))


if __name__ == "__main__":
    raise SystemExit(main())
