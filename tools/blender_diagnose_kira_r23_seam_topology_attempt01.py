#!/usr/bin/env python3
"""Blender-side R23 seam/topology diagnostic wrapper.

This reproduces the sealed in-memory patch, instruments topology_gate, writes
append-only diagnostics, and intentionally stops before donor removal, freeze,
save, render, export, or runtime use.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_author_kira_r23_cc0_afes_attempt01 as sealed_worker  # noqa: E402
from tools.kira_r23_cc0_afes_preflight_core import edge_face_map  # noqa: E402


CONFIGURED_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author/attempt_01"
)
DIAGNOSTIC_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_seam_topology_diagnostic/attempt_01"
)
DIAGNOSTIC_FILENAME = "TOPOLOGY_DIAGNOSTIC.json"


def canonical_edge(first: int, second: int) -> tuple[int, int]:
    return tuple(sorted((int(first), int(second))))


def edge_list_sha256(edges: Sequence[tuple[int, int]]) -> str:
    return sealed_worker.canonical_sha256(
        [[int(edge[0]), int(edge[1])] for edge in sorted(edges)]
    )


def diagnostic_output_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    configured = str(config["output"]["directory"])
    if configured != CONFIGURED_OUTPUT:
        raise sealed_worker.R23AuthorError(
            f"sealed configured output drifted: {configured}"
        )
    effective = deepcopy(config)
    effective["output"]["directory"] = DIAGNOSTIC_OUTPUT
    return ORIGINAL_OUTPUT_PATHS(effective)


ORIGINAL_OUTPUT_PATHS = sealed_worker.output_paths


def patch_face_regions(
    patch_face_indices: Sequence[int], config: Mapping[str, Any]
) -> dict[int, str]:
    target_count = int(config["selected_target_mask"]["outer_seam_vertex_count"])
    donor_boundary = int(config["qualified_donor_disk"]["outer_boundary_vertices"])
    outer_zipper = target_count + donor_boundary
    collar_bridge = donor_boundary * 2
    donor_faces = int(config["qualified_donor_disk"]["face_count"])
    expected = outer_zipper + collar_bridge + collar_bridge + donor_faces
    if len(patch_face_indices) != expected:
        raise sealed_worker.R23AuthorError(
            f"diagnostic patch face count drifted: {len(patch_face_indices)} != {expected}"
        )
    regions = {}
    for ordinal, face_index in enumerate(patch_face_indices):
        if ordinal < outer_zipper:
            region = "outer_unequal_cycle_zipper"
        elif ordinal < outer_zipper + collar_bridge:
            region = "outer_to_inner_collar_bridge"
        elif ordinal < outer_zipper + collar_bridge * 2:
            region = "inner_collar_to_donor_bridge"
        else:
            region = "donor_disk_interior"
        regions[int(face_index)] = region
    return regions


def edge_classification(
    edge: tuple[int, int],
    incident_faces: Sequence[int],
    patch_boundary: set[tuple[int, int]],
    outside_boundary: set[tuple[int, int]],
    patch_vertices: set[int],
    face_regions: Mapping[int, str],
    duplicate_mesh_edges: set[tuple[int, int]],
    duplicate_face_ids: set[int],
) -> dict[str, Any]:
    regions = sorted(
        {
            face_regions.get(int(face), "surviving_outside")
            for face in incident_faces
        }
    )
    if edge in duplicate_mesh_edges or any(
        int(face) in duplicate_face_ids for face in incident_faces
    ):
        label = "DUPLICATE_FACE_OR_EDGE"
    elif (
        edge in patch_boundary and edge in outside_boundary
    ) or (
        "surviving_outside" in regions
        and any(region != "surviving_outside" for region in regions)
    ):
        label = "TARGET_SEAM"
    elif all(region == "surviving_outside" for region in regions):
        if edge in outside_boundary and all(vertex in patch_vertices for vertex in edge):
            label = "TARGET_SEAM"
        else:
            label = "SURVIVING_OUTSIDE"
    elif all(region != "surviving_outside" for region in regions):
        label = "PATCH_INTERIOR_COLLAR_DONOR"
    else:
        label = "OTHER"
    return {"label": label, "face_regions": regions}


def diagnostic_topology_gate(
    body: bpy.types.Object,
    patch_face_indices: Sequence[int],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    faces = sealed_worker.preflight_base.faces_of(body)
    patch_set = {int(value) for value in patch_face_indices}
    all_face_indices = set(range(len(faces)))
    outside_set = all_face_indices.difference(patch_set)
    face_regions = patch_face_regions(patch_face_indices, config)
    whole_incidence = edge_face_map(faces)

    patch_incidence_count = {
        edge: sum(int(face) in patch_set for face in incident)
        for edge, incident in whole_incidence.items()
    }
    outside_incidence_count = {
        edge: sum(int(face) in outside_set for face in incident)
        for edge, incident in whole_incidence.items()
    }
    patch_boundary = {
        edge for edge, count in patch_incidence_count.items() if count == 1
    }
    outside_boundary = {
        edge for edge, count in outside_incidence_count.items() if count == 1
    }
    whole_boundary = {
        edge for edge, incident in whole_incidence.items() if len(incident) == 1
    }
    greater_than_two = {
        edge for edge, incident in whole_incidence.items() if len(incident) > 2
    }

    mesh_edge_rows = [
        {
            "mesh_edge_index": int(edge.index),
            "edge": list(
                canonical_edge(edge.vertices[0], edge.vertices[1])
            ),
        }
        for edge in body.data.edges
    ]
    mesh_edge_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for row in mesh_edge_rows:
        mesh_edge_groups[tuple(row["edge"])].append(row["mesh_edge_index"])
    duplicate_mesh_rows = [
        {"edge": list(edge), "mesh_edge_indices": sorted(indices)}
        for edge, indices in sorted(mesh_edge_groups.items())
        if len(indices) > 1
    ]
    duplicate_mesh_edges = {
        tuple(row["edge"]) for row in duplicate_mesh_rows
    }
    loose_edge_rows = [
        {
            "edge": list(edge),
            "mesh_edge_indices": sorted(indices),
            "mesh_occurrence_count": len(indices),
        }
        for edge, indices in sorted(mesh_edge_groups.items())
        if edge not in whole_incidence
    ]

    face_groups: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        face_groups[tuple(sorted(int(value) for value in face))].append(face_index)
    duplicate_face_rows = [
        {"vertex_set": list(vertices), "face_indices": sorted(indices)}
        for vertices, indices in sorted(face_groups.items())
        if len(indices) > 1
    ]
    duplicate_face_ids = {
        int(face)
        for row in duplicate_face_rows
        for face in row["face_indices"]
    }

    patch_vertices = {
        int(vertex)
        for face_index in patch_set
        for vertex in faces[face_index]
    }
    incidence_rows = []
    for edge, incident in sorted(whole_incidence.items()):
        classification = edge_classification(
            edge,
            incident,
            patch_boundary,
            outside_boundary,
            patch_vertices,
            face_regions,
            duplicate_mesh_edges,
            duplicate_face_ids,
        )
        incidence_rows.append(
            {
                "edge": list(edge),
                "face_count": len(incident),
                "face_indices": [int(value) for value in incident],
                "patch_face_count": patch_incidence_count[edge],
                "outside_face_count": outside_incidence_count[edge],
                "classification": classification,
            }
        )

    def defect_rows(edges: set[tuple[int, int]]) -> list[dict[str, Any]]:
        rows = []
        for edge in sorted(edges):
            incident = whole_incidence[edge]
            rows.append(
                {
                    "edge": list(edge),
                    "face_count": len(incident),
                    "face_indices": [int(value) for value in incident],
                    "classification": edge_classification(
                        edge,
                        incident,
                        patch_boundary,
                        outside_boundary,
                        patch_vertices,
                        face_regions,
                        duplicate_mesh_edges,
                        duplicate_face_ids,
                    ),
                }
            )
        return rows

    whole_topology = sealed_worker.preflight_base.topology_record(
        faces, all_face_indices
    )
    patch_topology = sealed_worker.preflight_base.topology_record(faces, patch_set)
    expected = config["expected_structural_result"]
    mesh_edge_count = len(body.data.edges)
    face_edge_count = len(whole_incidence)
    actual = {
        "vertices": len(body.data.vertices),
        "mesh_edges": mesh_edge_count,
        "face_derived_edges": face_edge_count,
        "faces": len(body.data.polygons),
        "components": whole_topology["component_count"],
        "boundary_edges": len(whole_boundary),
        "greater_than_two_face_edges": len(greater_than_two),
        "loose_mesh_edges": len(loose_edge_rows),
        "euler_using_mesh_edges": len(body.data.vertices)
        - mesh_edge_count
        + len(body.data.polygons),
        "euler_using_face_derived_edges": len(body.data.vertices)
        - face_edge_count
        + len(body.data.polygons),
    }
    expected_whole = {
        "vertices": int(expected["body_vertices"]),
        "mesh_edges": int(expected["body_edges"]),
        "face_derived_edges": int(expected["body_edges"]),
        "faces": int(expected["body_faces"]),
        "components": int(expected["whole_body_components"]),
        "boundary_edges": int(expected["whole_body_boundary_edges"]),
        "greater_than_two_face_edges": int(expected["whole_body_nonmanifold_edges"]),
        "loose_mesh_edges": 0,
        "euler_using_mesh_edges": 2,
        "euler_using_face_derived_edges": 2,
    }
    whole_deltas = {
        key: int(actual[key]) - int(expected_whole[key]) for key in expected_whole
    }
    patch_actual = {
        "vertices": patch_topology["vertex_count"],
        "edges": patch_topology["edge_count"],
        "faces": patch_topology["face_count"],
        "components": patch_topology["component_count"],
        "boundary_edges": patch_topology["boundary_edge_count"],
        "boundary_cycles": patch_topology["boundary_cycle_count"],
        "euler": patch_topology["euler_characteristic"],
    }
    patch_expected = {
        "vertices": int(expected["replacement_patch_vertices"]),
        "edges": int(expected["replacement_patch_edges"]),
        "faces": int(expected["replacement_patch_faces"]),
        "components": int(expected["replacement_patch_components"]),
        "boundary_edges": int(expected["replacement_patch_boundary_vertices"]),
        "boundary_cycles": int(expected["replacement_patch_boundary_cycles"]),
        "euler": int(expected["replacement_patch_euler_characteristic"]),
    }
    patch_deltas = {
        key: int(patch_actual[key]) - int(patch_expected[key])
        for key in patch_expected
    }

    classification_counts = Counter()
    for row in defect_rows(whole_boundary | greater_than_two):
        classification_counts[row["classification"]["label"]] += 1
    for row in loose_edge_rows:
        edge = tuple(row["edge"])
        if edge in duplicate_mesh_edges:
            label = "DUPLICATE_FACE_OR_EDGE"
        elif all(vertex in patch_vertices for vertex in edge):
            label = "PATCH_INTERIOR_COLLAR_DONOR"
        else:
            label = "SURVIVING_OUTSIDE"
        row["classification"] = {"label": label, "face_regions": []}
        classification_counts[label] += 1

    source = sealed_worker.project_path(
        config["inputs"]["r19_source_blend"]["path"]
    )
    diagnostic_dir = sealed_worker.project_path(DIAGNOSTIC_OUTPUT)
    diagnostic_path = diagnostic_dir / DIAGNOSTIC_FILENAME
    if diagnostic_path.exists():
        raise sealed_worker.R23AuthorError(
            "append-only topology diagnostic already exists"
        )
    candidate_path = diagnostic_dir / config["output"]["candidate_blend"]
    record = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R23_SEAM_TOPOLOGY_DIAGNOSTIC_ATTEMPT01",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DIAGNOSTIC_CAPTURE_COMPLETE_INTENTIONAL_STOP_BEFORE_SAVE",
        "configured_output": CONFIGURED_OUTPUT,
        "effective_diagnostic_output": DIAGNOSTIC_OUTPUT,
        "whole": {
            "actual": actual,
            "expected": expected_whole,
            "delta": whole_deltas,
            "topology_record": whole_topology,
        },
        "patch": {
            "actual": patch_actual,
            "expected": patch_expected,
            "delta": patch_deltas,
            "topology_record": patch_topology,
            "face_region_counts": dict(sorted(Counter(face_regions.values()).items())),
            "face_region_assignment_sha256": sealed_worker.canonical_sha256(
                sorted(face_regions.items())
            ),
        },
        "face_edge_incidence": {
            "edge_count": len(incidence_rows),
            "histogram": {
                str(count): sum(row["face_count"] == count for row in incidence_rows)
                for count in sorted({row["face_count"] for row in incidence_rows})
            },
            "rows_sha256": sealed_worker.canonical_sha256(incidence_rows),
            "rows": incidence_rows,
        },
        "seam_sets": {
            "patch_boundary_count": len(patch_boundary),
            "patch_boundary_sha256": edge_list_sha256(list(patch_boundary)),
            "patch_boundary_edges": [list(edge) for edge in sorted(patch_boundary)],
            "outside_boundary_count": len(outside_boundary),
            "outside_boundary_sha256": edge_list_sha256(list(outside_boundary)),
            "outside_boundary_edges": [list(edge) for edge in sorted(outside_boundary)],
            "matched_target_seam_count": len(patch_boundary & outside_boundary),
            "matched_target_seam_sha256": edge_list_sha256(
                list(patch_boundary & outside_boundary)
            ),
            "matched_target_seam_edges": [
                list(edge) for edge in sorted(patch_boundary & outside_boundary)
            ],
            "patch_only_boundary_count": len(patch_boundary - outside_boundary),
            "patch_only_boundary_sha256": edge_list_sha256(
                list(patch_boundary - outside_boundary)
            ),
            "patch_only_boundary_edges": [
                list(edge) for edge in sorted(patch_boundary - outside_boundary)
            ],
            "outside_only_boundary_count": len(outside_boundary - patch_boundary),
            "outside_only_boundary_sha256": edge_list_sha256(
                list(outside_boundary - patch_boundary)
            ),
            "outside_only_boundary_edges": [
                list(edge) for edge in sorted(outside_boundary - patch_boundary)
            ],
            "expected_target_seam_edge_count": int(
                config["selected_target_mask"]["outer_seam_vertex_count"]
            ),
        },
        "boundary_defects": {
            "count": len(whole_boundary),
            "edge_sha256": edge_list_sha256(list(whole_boundary)),
            "rows": defect_rows(whole_boundary),
        },
        "greater_than_two_face_nonmanifold": {
            "count": len(greater_than_two),
            "edge_sha256": edge_list_sha256(list(greater_than_two)),
            "rows": defect_rows(greater_than_two),
        },
        "loose_edges": {
            "count": len(loose_edge_rows),
            "sha256": sealed_worker.canonical_sha256(loose_edge_rows),
            "rows": loose_edge_rows,
        },
        "duplicates": {
            "mesh_edge_group_count": len(duplicate_mesh_rows),
            "mesh_edge_sha256": sealed_worker.canonical_sha256(duplicate_mesh_rows),
            "mesh_edge_rows": duplicate_mesh_rows,
            "face_group_count": len(duplicate_face_rows),
            "face_sha256": sealed_worker.canonical_sha256(duplicate_face_rows),
            "face_rows": duplicate_face_rows,
        },
        "defect_classification_counts": dict(sorted(classification_counts.items())),
        "source_and_stop_proof": {
            "loaded_blend": sealed_worker.relative(Path(bpy.data.filepath)),
            "source_path": sealed_worker.relative(source),
            "source_expected_sha256": config["inputs"]["r19_source_blend"]["sha256"],
            "source_actual_sha256": sealed_worker.sha256_file(source),
            "source_unchanged": sealed_worker.sha256_file(source)
            == config["inputs"]["r19_source_blend"]["sha256"],
            "candidate_path": sealed_worker.relative(candidate_path),
            "candidate_exists_before_intentional_stop": candidate_path.exists(),
            "save_called": False,
            "render_called": False,
            "export_called": False,
            "runtime_changed": False,
            "donor_present_before_intentional_stop": bpy.data.objects.get(
                config["qualified_donor_disk"]["object_name"]
            )
            is not None,
            "freeze_after_author_called": False,
        },
    }
    with diagnostic_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    raise sealed_worker.R23AuthorError(
        "DIAGNOSTIC_CAPTURE_COMPLETE_INTENTIONAL_STOP_BEFORE_DONOR_REMOVAL_FREEZE_SAVE"
    )


ORIGINAL_TOPOLOGY_GATE = sealed_worker.topology_gate


def bind_diagnostic_runtime() -> None:
    sealed_worker.preflight_base.edge_face_map = edge_face_map
    sealed_worker.output_paths = diagnostic_output_paths
    sealed_worker.topology_gate = diagnostic_topology_gate


def main() -> int:
    bind_diagnostic_runtime()
    return int(sealed_worker.main())


if __name__ == "__main__":
    raise SystemExit(main())
