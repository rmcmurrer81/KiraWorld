#!/usr/bin/env python3
"""Bounded Blender-side repair wrapper for R23 Author Attempt 04.

The sealed Attempt01 worker, config, author core, and R19 source remain inputs.
This wrapper makes only the diagnosed topology correction:

* capture the exact source topology before mutation;
* identify selected-mask interior chords whose two endpoints are on the kept
  target seam;
* after the sealed FACES_ONLY deletion, require those exact chords to be the
  newly orphaned seam edges and delete only those edges;
* evaluate the final whole-body topology against the captured source boundary,
  loose-edge, component, and Euler invariants using stable vertex IDs.

It also emits fail-honest external-anatomy placeholder metadata. It does not
create canals, physiology, bathroom function, reproductive function, or any
other geometry. The wrapper remains inert unless the sealed worker receives
``--execute-authoring`` through the separately gated controller.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import json
import sys
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_author_kira_r23_cc0_afes_attempt01 as sealed_worker  # noqa: E402
from tools.kira_r23_cc0_afes_preflight_core import (  # noqa: E402
    edge_face_map,
    face_edges as topology_face_edges,
)


REPAIR_CONFIG = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_REPAIR_CONFIG.json"
)
CONFIGURED_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author/attempt_01"
)
EFFECTIVE_ATTEMPT04_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author/attempt_04"
)
EFFECTIVE_ATTEMPT04_CANDIDATE = (
    "kira_r23_cc0_afes_core_transfer_attempt_04.blend"
)


ORIGINAL_OUTPUT_PATHS = sealed_worker.output_paths
ORIGINAL_EXACT_DONOR_DISK = sealed_worker.exact_donor_disk
ORIGINAL_BMESH_FROZEN_SNAPSHOT = sealed_worker.bmesh_frozen_snapshot
ORIGINAL_APPLY_PATCH = sealed_worker.apply_patch
ORIGINAL_TOPOLOGY_GATE = sealed_worker.topology_gate
ORIGINAL_BMESH_MODULE = sealed_worker.bmesh

RUNTIME: dict[str, Any] = {}


def stable_source_vertex(index: int) -> str:
    return f"S:{int(index)}"


def stable_patch_vertex(index: int) -> str:
    return f"P:{int(index)}"


def canonical_edge(first: int, second: int) -> tuple[int, int]:
    return tuple(sorted((int(first), int(second))))


def stable_edge(first: str, second: str) -> tuple[str, str]:
    return tuple(sorted((str(first), str(second))))


def edge_rows(edges: Iterable[tuple[Any, Any]]) -> list[list[Any]]:
    return [[edge[0], edge[1]] for edge in sorted(set(edges))]


def edge_set_sha256(edges: Iterable[tuple[Any, Any]]) -> str:
    return sealed_worker.canonical_sha256(edge_rows(edges))


def verify_binding(label: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    path = sealed_worker.project_path(binding["path"])
    if not path.is_file():
        raise sealed_worker.R23AuthorError(f"missing Attempt04 binding {label}")
    size = path.stat().st_size
    digest = sealed_worker.sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise sealed_worker.R23AuthorError(
            f"Attempt04 binding drifted for {label}: bytes={size}, sha256={digest}"
        )
    return {"path": sealed_worker.relative(path), "bytes": size, "sha256": digest}


def verify_repair_config() -> tuple[dict[str, Any], dict[str, Any]]:
    path = sealed_worker.project_path(REPAIR_CONFIG)
    config = sealed_worker.read_json(path)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_repair.v1":
        raise sealed_worker.R23AuthorError("wrong Attempt04 repair schema")
    if config.get("status") != "PREPARED_NOT_RUN_EXPLICIT_EXECUTION_REQUIRED":
        raise sealed_worker.R23AuthorError("Attempt04 repair status drifted")
    verified: dict[str, Any] = {}
    for label, binding in config["bound_artifacts"].items():
        verified[label] = verify_binding(label, binding)
    for section in config["preserved_append_only_evidence"]:
        directory = sealed_worker.project_path(section["directory"])
        if not directory.is_dir():
            raise sealed_worker.R23AuthorError(
                f"missing preserved directory {section['label']}"
            )
        actual_names = sorted(path.name for path in directory.iterdir() if path.is_file())
        expected_names = sorted(section["files"])
        if actual_names != expected_names:
            raise sealed_worker.R23AuthorError(
                f"preserved directory drifted for {section['label']}: {actual_names}"
            )
        for name, binding in section["files"].items():
            verified[f"{section['label']}/{name}"] = verify_binding(
                f"{section['label']}/{name}",
                {**binding, "path": f"{section['directory']}/{name}"},
            )
    contract = config["repair_contract"]
    if int(contract["diagnosed_seam_chord_count"]) != 22:
        raise sealed_worker.R23AuthorError("Attempt04 diagnosed chord count drifted")
    if contract["configured_output_required"] != CONFIGURED_OUTPUT:
        raise sealed_worker.R23AuthorError("Attempt04 configured output contract drifted")
    if contract["effective_output"] != EFFECTIVE_ATTEMPT04_OUTPUT:
        raise sealed_worker.R23AuthorError("Attempt04 effective output contract drifted")
    if contract["effective_candidate"] != EFFECTIVE_ATTEMPT04_CANDIDATE:
        raise sealed_worker.R23AuthorError("Attempt04 candidate contract drifted")
    if sealed_worker.project_path(EFFECTIVE_ATTEMPT04_OUTPUT).exists():
        raise sealed_worker.R23AuthorError("append-only Attempt04 author output already exists")
    return config, verified


def attempt04_output_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    configured = str(config["output"]["directory"])
    if configured != CONFIGURED_OUTPUT:
        raise sealed_worker.R23AuthorError(
            f"sealed configured output drifted: {configured}"
        )
    effective = deepcopy(config)
    effective["output"]["directory"] = EFFECTIVE_ATTEMPT04_OUTPUT
    effective["output"]["candidate_blend"] = EFFECTIVE_ATTEMPT04_CANDIDATE
    return ORIGINAL_OUTPUT_PATHS(effective)


def attempt04_exact_donor_disk(
    donor: bpy.types.Object,
    preflight: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[set[int], set[int], list[int], dict[str, set[int]]]:
    result = ORIGINAL_EXACT_DONOR_DISK(donor, preflight, config)
    RUNTIME["donor_memberships"] = {
        str(name): {int(value) for value in values}
        for name, values in result[3].items()
    }
    return result


def capture_source_baseline(
    body: bpy.types.Object,
    selected_faces: set[int],
    target_cycle: Sequence[int],
    repair_config: Mapping[str, Any],
) -> dict[str, Any]:
    faces = sealed_worker.preflight_base.faces_of(body)
    all_faces = set(range(len(faces)))
    incidence = edge_face_map(faces)
    mesh_edge_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for edge in body.data.edges:
        pair = canonical_edge(edge.vertices[0], edge.vertices[1])
        mesh_edge_groups[pair].append(int(edge.index))
    duplicates = {
        pair: indices for pair, indices in mesh_edge_groups.items() if len(indices) != 1
    }
    if duplicates:
        raise sealed_worker.R23AuthorError(
            "source mesh contains duplicate edge records; bounded repair refused"
        )
    mesh_edges = set(mesh_edge_groups)
    face_derived_edges = set(incidence)
    boundary = {edge for edge, owners in incidence.items() if len(owners) == 1}
    overused = {edge for edge, owners in incidence.items() if len(owners) > 2}
    loose = mesh_edges.difference(face_derived_edges)
    seam = {int(value) for value in target_cycle}
    selected = {int(value) for value in selected_faces}
    selected_vertices = {
        int(vertex) for face_index in selected for vertex in faces[face_index]
    }
    removable_vertices = selected_vertices.difference(seam)
    selected_region_edges = {
        edge
        for face_index in selected
        for edge in topology_face_edges(faces[face_index])
    }
    region_boundary = sealed_worker.preflight_base.boundary_edges_for_region(
        faces, selected
    )
    seam_chords = {
        edge
        for edge in selected_region_edges
        if edge[0] in seam
        and edge[1] in seam
        and edge not in region_boundary
        and len(incidence.get(edge, ())) == 2
        and set(incidence[edge]).issubset(selected)
    }
    topology = sealed_worker.preflight_base.topology_record(faces, all_faces)
    selected_topology = sealed_worker.preflight_base.topology_record(faces, selected)
    contract = repair_config["repair_contract"]
    nominal = repair_config["nominal_source_baseline"]
    checks = {
        "source_vertices": len(body.data.vertices) == int(nominal["vertices"]),
        "source_mesh_edges": len(body.data.edges) == int(nominal["mesh_edges"]),
        "source_face_edges": len(face_derived_edges)
        == int(nominal["face_derived_edges"]),
        "source_faces": len(faces) == int(nominal["faces"]),
        "source_components": topology["component_count"] == int(nominal["components"]),
        "source_boundary": len(boundary) == int(nominal["boundary_edges"]),
        "source_boundary_cycles": topology["boundary_cycle_count"]
        == int(nominal["boundary_cycles"]),
        "source_boundary_cycle_lengths": topology["boundary_cycle_lengths"]
        == list(nominal["boundary_cycle_lengths"]),
        "source_overused_zero": len(overused) == int(nominal["overused_edges"]),
        "source_loose_zero": len(loose) == int(nominal["loose_edges"]),
        "source_face_euler": (
            len(body.data.vertices) - len(face_derived_edges) + len(faces)
        )
        == int(nominal["face_euler"]),
        "source_mesh_euler": (
            len(body.data.vertices) - len(body.data.edges) + len(faces)
        )
        == int(nominal["mesh_euler"]),
        "selected_is_one_disk": bool(selected_topology["is_one_disk"]),
        "selected_boundary_equals_target_seam": set(region_boundary)
        == {
            canonical_edge(target_cycle[index], target_cycle[(index + 1) % len(target_cycle)])
            for index in range(len(target_cycle))
        },
        "diagnosed_seam_chord_count": len(seam_chords)
        == int(contract["diagnosed_seam_chord_count"]),
        "removable_vertex_count": len(removable_vertices)
        == int(contract["removable_original_vertex_count"]),
        "seam_chords_not_source_loose": not seam_chords.intersection(loose),
        "seam_chords_not_source_boundary": not seam_chords.intersection(boundary),
    }
    expected_chord_hash = contract.get("diagnosed_seam_chord_stable_id_sha256")
    if expected_chord_hash:
        checks["diagnosed_seam_chord_hash"] = (
            edge_set_sha256(seam_chords) == expected_chord_hash
        )
    if not all(checks.values()):
        raise sealed_worker.R23AuthorError(
            f"Attempt04 source topology baseline failed: {checks}"
        )
    return {
        "vertices": len(body.data.vertices),
        "mesh_edges": len(body.data.edges),
        "face_derived_edges": len(face_derived_edges),
        "faces": len(faces),
        "components": topology["component_count"],
        "boundary_edges": len(boundary),
        "boundary_cycles": topology["boundary_cycle_count"],
        "boundary_cycle_lengths": topology["boundary_cycle_lengths"],
        "boundary_original_id_sha256": edge_set_sha256(boundary),
        "boundary_original_id_edges": edge_rows(boundary),
        "greater_than_two_face_edges": len(overused),
        "greater_than_two_original_id_sha256": edge_set_sha256(overused),
        "greater_than_two_original_id_edges": edge_rows(overused),
        "loose_edges": len(loose),
        "loose_original_id_sha256": edge_set_sha256(loose),
        "loose_original_id_edges": edge_rows(loose),
        "face_euler": len(body.data.vertices)
        - len(face_derived_edges)
        + len(faces),
        "mesh_euler": len(body.data.vertices) - len(body.data.edges) + len(faces),
        "selected_region": selected_topology,
        "selected_vertex_scope_sha256": sealed_worker.preflight_base.canonical_index_sha256(
            selected_vertices
        ),
        "removable_original_vertex_count": len(removable_vertices),
        "removable_original_vertex_sha256": sealed_worker.preflight_base.canonical_index_sha256(
            removable_vertices
        ),
        "target_seam_original_id_sha256": sealed_worker.preflight_base.canonical_index_sha256(
            seam
        ),
        "seam_chords": len(seam_chords),
        "seam_chord_original_id_sha256": edge_set_sha256(seam_chords),
        "seam_chord_original_id_edges": edge_rows(seam_chords),
        "checks": checks,
        "_boundary_set": boundary,
        "_overused_set": overused,
        "_loose_set": loose,
        "_seam_chord_set": seam_chords,
        "_selected_faces": selected,
        "_target_seam": seam,
        "_removable_vertices": removable_vertices,
    }


class Attempt04OpsProxy:
    """Delegate every BMesh op except the one diagnosed FACES_ONLY boundary."""

    def __init__(self, original_ops: Any, baseline: Mapping[str, Any]) -> None:
        self._original_ops = original_ops
        self._baseline = baseline
        self.faces_only_seen = False
        self.repair_evidence: dict[str, Any] | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original_ops, name)

    def delete(self, bm: Any, *, geom: Sequence[Any], context: str) -> Any:
        if context != "FACES_ONLY":
            return self._original_ops.delete(bm, geom=geom, context=context)
        if self.faces_only_seen:
            raise sealed_worker.R23AuthorError(
                "Attempt04 observed an unexpected second FACES_ONLY deletion"
            )
        self.faces_only_seen = True
        vertex_id = bm.verts.layers.int.get("__R23_ORIGINAL_VERTEX_ID_TRANSIENT")
        face_id = bm.faces.layers.int.get("__R23_ORIGINAL_FACE_ID_TRANSIENT")
        if vertex_id is None or face_id is None:
            raise sealed_worker.R23AuthorError(
                "Attempt04 transient stable-ID layers are absent at deletion boundary"
            )
        requested_faces = {int(face[face_id]) for face in geom if face.is_valid}
        if requested_faces != set(self._baseline["_selected_faces"]):
            raise sealed_worker.R23AuthorError(
                "Attempt04 FACES_ONLY scope is not the exact selected mask"
            )
        expected_chords = set(self._baseline["_seam_chord_set"])
        seam = set(self._baseline["_target_seam"])
        original_edge_rows: dict[tuple[int, int], list[Any]] = defaultdict(list)
        for edge in bm.edges:
            pair = canonical_edge(
                edge.verts[0][vertex_id], edge.verts[1][vertex_id]
            )
            original_edge_rows[pair].append(edge)
        if any(len(original_edge_rows[pair]) != 1 for pair in expected_chords):
            raise sealed_worker.R23AuthorError(
                "Attempt04 seam chord did not resolve to exactly one source BMesh edge"
            )
        result = self._original_ops.delete(bm, geom=geom, context=context)
        postdelete_seam_orphans: dict[tuple[int, int], list[Any]] = defaultdict(list)
        all_zero_face_original_edges: set[tuple[int, int]] = set()
        for edge in bm.edges:
            if not edge.is_valid or len(edge.link_faces) != 0:
                continue
            pair = canonical_edge(
                edge.verts[0][vertex_id], edge.verts[1][vertex_id]
            )
            all_zero_face_original_edges.add(pair)
            if pair[0] in seam and pair[1] in seam:
                postdelete_seam_orphans[pair].append(edge)
        actual_chords = set(postdelete_seam_orphans)
        checks = {
            "postdelete_seam_orphan_set_exact": actual_chords == expected_chords,
            "postdelete_seam_orphan_count_exact": len(actual_chords)
            == len(expected_chords),
            "each_orphan_has_one_mesh_edge": all(
                len(postdelete_seam_orphans[pair]) == 1 for pair in actual_chords
            ),
            "all_endpoints_inside_kept_target_seam": all(
                first in seam and second in seam for first, second in actual_chords
            ),
            "none_were_loose_in_source": not actual_chords.intersection(
                self._baseline["_loose_set"]
            ),
            "none_were_boundary_in_source": not actual_chords.intersection(
                self._baseline["_boundary_set"]
            ),
        }
        if not all(checks.values()):
            raise sealed_worker.R23AuthorError(
                f"Attempt04 diagnosed seam-orphan identity failed: {checks}"
            )
        exact_edges = [postdelete_seam_orphans[pair][0] for pair in sorted(actual_chords)]
        self._original_ops.delete(bm, geom=exact_edges, context="EDGES")
        remaining_pairs = {
            canonical_edge(edge.verts[0][vertex_id], edge.verts[1][vertex_id])
            for edge in bm.edges
            if edge.is_valid
        }
        checks["exact_chords_deleted"] = not actual_chords.intersection(remaining_pairs)
        if not checks["exact_chords_deleted"]:
            raise sealed_worker.R23AuthorError("Attempt04 seam-chord deletion was incomplete")
        self.repair_evidence = {
            "operation": "DELETE_EXACT_POST_FACES_ONLY_SEAM_CHORDS_ONLY",
            "count": len(actual_chords),
            "original_id_sha256": edge_set_sha256(actual_chords),
            "original_id_edges": edge_rows(actual_chords),
            "all_zero_face_original_edge_count_immediately_after_faces_only": len(
                all_zero_face_original_edges
            ),
            "all_zero_face_original_edge_sha256_immediately_after_faces_only": edge_set_sha256(
                all_zero_face_original_edges
            ),
            "delete_context": "EDGES",
            "global_weld_performed": False,
            "global_boundary_deletion_performed": False,
            "source_boundary_edge_deleted": False,
            "source_loose_edge_deleted": False,
            "checks": checks,
        }
        return result


class Attempt04BMeshProxy:
    def __init__(self, original: Any, ops_proxy: Attempt04OpsProxy) -> None:
        self._original = original
        self.ops = ops_proxy

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def attempt04_bmesh_frozen_snapshot(
    bm: bmesh.types.BMesh,
    vertex_id_layer: Any,
    face_id_layer: Any,
    loop_id_layer: Any,
    removable_original_vertices: set[int],
    selected_original_faces: set[int],
    group_names: Mapping[int, str],
) -> str:
    digest = ORIGINAL_BMESH_FROZEN_SNAPSHOT(
        bm,
        vertex_id_layer,
        face_id_layer,
        loop_id_layer,
        removable_original_vertices,
        selected_original_faces,
        group_names,
    )
    originals = [int(vertex[vertex_id_layer]) for vertex in bm.verts]
    if any(value < 0 for value in originals):
        local_id_layer = bm.verts.layers.int.get("__R23_LOCAL_PATCH_ID_TRANSIENT")
        if local_id_layer is None:
            raise sealed_worker.R23AuthorError(
                "Attempt04 local patch ID layer absent at final stable-map capture"
            )
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()
        global_to_token: dict[int, str] = {}
        token_to_global: dict[str, int] = {}
        for vertex in bm.verts:
            original = int(vertex[vertex_id_layer])
            local = int(vertex[local_id_layer])
            token = (
                stable_source_vertex(original)
                if original >= 0
                else stable_patch_vertex(local)
            )
            if original < 0 and local < 0:
                raise sealed_worker.R23AuthorError(
                    "Attempt04 encountered a new vertex without a stable local patch ID"
                )
            if token in token_to_global:
                raise sealed_worker.R23AuthorError(
                    f"Attempt04 stable vertex token duplicated: {token}"
                )
            global_to_token[int(vertex.index)] = token
            token_to_global[token] = int(vertex.index)
        RUNTIME["final_stable_vertex_map"] = {
            "global_to_token": global_to_token,
            "token_to_global": token_to_global,
            "global_to_token_sha256": sealed_worker.canonical_sha256(
                sorted(global_to_token.items())
            ),
        }
    return digest


def semantic_placeholder_record(
    semantic_id: str,
    source_group: str | None,
    status: str,
    donor_to_local: Mapping[int, int],
    token_to_global: Mapping[str, int],
) -> dict[str, Any]:
    if source_group is None:
        return {
            "semantic_id": semantic_id,
            "source_group": None,
            "extraction_status": status,
            "vertex_count": 0,
            "stable_vertex_token_sha256": sealed_worker.canonical_sha256([]),
            "stable_vertex_tokens": [],
            "current_global_vertex_indices": [],
            "geometry_created_for_semantic_label": False,
        }
    membership = RUNTIME["donor_memberships"].get(source_group)
    if not membership:
        raise sealed_worker.R23AuthorError(
            f"Attempt04 semantic source group is missing or empty: {source_group}"
        )
    missing = sorted(set(membership).difference(donor_to_local))
    if missing:
        raise sealed_worker.R23AuthorError(
            f"Attempt04 semantic source escaped prepared donor order: {source_group}"
        )
    tokens = sorted(stable_patch_vertex(donor_to_local[index]) for index in membership)
    global_indices = sorted(token_to_global[token] for token in tokens)
    return {
        "semantic_id": semantic_id,
        "source_group": source_group,
        "extraction_status": status,
        "donor_vertex_count": len(membership),
        "donor_vertex_index_sha256": sealed_worker.preflight_base.canonical_index_sha256(
            membership
        ),
        "vertex_count": len(tokens),
        "stable_vertex_token_sha256": sealed_worker.canonical_sha256(tokens),
        "stable_vertex_tokens": tokens,
        "current_global_vertex_index_sha256": sealed_worker.preflight_base.canonical_index_sha256(
            global_indices
        ),
        "current_global_vertex_indices": global_indices,
        "geometry_created_for_semantic_label": False,
    }


def build_semantic_placeholders(prepared: Mapping[str, Any]) -> dict[str, Any]:
    final_map = RUNTIME.get("final_stable_vertex_map")
    if not final_map or "donor_memberships" not in RUNTIME:
        raise sealed_worker.R23AuthorError(
            "Attempt04 lacks exact donor membership or final stable-map capture"
        )
    donor_to_local = {
        int(donor): int(prepared["donor_start"]) + offset
        for offset, donor in enumerate(prepared["donor_vertex_order"])
    }
    token_to_global = final_map["token_to_global"]
    definitions = [
        (
            "external_clitoral_glans_region_placeholder",
            "AFES_LANDMARK__clitoris",
            "EXACT_DONOR_REGION_PLACEHOLDER_ONLY_NOT_WHOLE_CLITORIS_NOT_RIM_PROOF",
        ),
        (
            "external_urethral_endpoint_or_rim_region_placeholder",
            "AFES_LANDMARK__urethral_opening",
            "EXACT_DONOR_REGION_PLACEHOLDER_ONLY_NOT_MEATUS_RIM_PATENCY_OR_ROUTE_PROOF",
        ),
        (
            "external_vaginal_endpoint_or_rim_region_placeholder",
            "AFES_LANDMARK__vaginal_opening",
            "EXACT_DONOR_REGION_PLACEHOLDER_ONLY_NOT_INTROITUS_RIM_PATENCY_OR_ROUTE_PROOF",
        ),
        (
            "external_anal_endpoint_or_rim_region_placeholder",
            "AFES_LANDMARK__perineal_path__anal_recess",
            "EXACT_ANAL_RECESS_REGION_PLACEHOLDER_ONLY_NOT_ANUS_ANAL_VERGE_RIM_PATENCY_OR_ROUTE_PROOF",
        ),
        (
            "fourchette_region_placeholder",
            "AFES_LANDMARK__fourchette",
            "EXACT_DONOR_REGION_PLACEHOLDER_ONLY_NOT_POSTERIOR_COMMISSURE_PROOF",
        ),
        (
            "posterior_labial_commissure_placeholder",
            None,
            "NOT_DETERMINISTICALLY_EXTRACTABLE_FROM_SEALED_DONOR_NO_SET_FABRICATED",
        ),
        (
            "external_perineal_body_placeholder",
            None,
            "NOT_DETERMINISTICALLY_EXTRACTABLE_FROM_BROAD_PERINEAL_PATH_NO_SET_FABRICATED",
        ),
    ]
    records = [
        semantic_placeholder_record(
            semantic_id, source_group, status, donor_to_local, token_to_global
        )
        for semantic_id, source_group, status in definitions
    ]
    return {
        "classification": "FAIL_HONEST_EXTERNAL_REGION_PLACEHOLDERS_ONLY",
        "records": records,
        "record_sha256": sealed_worker.canonical_sha256(records),
        "clinical_sources_bound_by_repair_config": RUNTIME["repair_config"][
            "clinical_semantics_contract"
        ]["bound_source_labels"],
        "gates": {
            "explicit_placeholder_records_present": len(records) == 7,
            "posterior_commissure_not_fabricated": records[5]["vertex_count"] == 0,
            "perineal_body_not_fabricated": records[6]["vertex_count"] == 0,
            "three_exact_disjoint_rims_proven": False,
            "vestibule_containment_and_adjacency_proven": False,
            "internal_canals_or_typed_routes_created": False,
            "bathroom_function_proven": False,
            "sexual_or_reproductive_function_proven": False,
        },
        "truth_boundary": {
            "external_visual_and_deformation_candidate_only": True,
            "region_placeholder_is_not_opening_or_rim_proof": True,
            "anal_recess_is_not_anus_or_anal_verge_proof": True,
            "clitoral_region_is_not_whole_clitoral_organ_proof": True,
            "no_internal_urinary_digestive_reproductive_or_pregnancy_system": True,
        },
    }


def attempt04_apply_patch(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    selected_faces: set[int],
    target_cycle: list[int],
    prepared: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    baseline = capture_source_baseline(
        body, selected_faces, target_cycle, RUNTIME["repair_config"]
    )
    RUNTIME["source_baseline"] = baseline
    ops_proxy = Attempt04OpsProxy(ORIGINAL_BMESH_MODULE.ops, baseline)
    sealed_worker.bmesh = Attempt04BMeshProxy(ORIGINAL_BMESH_MODULE, ops_proxy)
    try:
        result = ORIGINAL_APPLY_PATCH(
            body, rig, selected_faces, target_cycle, prepared, config
        )
    finally:
        sealed_worker.bmesh = ORIGINAL_BMESH_MODULE
    if not ops_proxy.faces_only_seen or ops_proxy.repair_evidence is None:
        raise sealed_worker.R23AuthorError(
            "Attempt04 did not observe and repair the exact FACES_ONLY boundary"
        )
    final_map = RUNTIME.get("final_stable_vertex_map")
    if not final_map:
        raise sealed_worker.R23AuthorError("Attempt04 final stable vertex map was not captured")
    public_baseline = {
        key: value for key, value in baseline.items() if not key.startswith("_")
    }
    result["attempt04_source_topology_baseline"] = public_baseline
    result["attempt04_exact_seam_chord_repair"] = ops_proxy.repair_evidence
    result["attempt04_final_stable_vertex_map_sha256"] = final_map[
        "global_to_token_sha256"
    ]
    result["attempt04_external_semantic_placeholders"] = build_semantic_placeholders(
        prepared
    )
    return result


def stable_edges_from_global(
    edges: Iterable[tuple[int, int]], global_to_token: Mapping[int, str]
) -> set[tuple[str, str]]:
    result = set()
    for first, second in edges:
        if int(first) not in global_to_token or int(second) not in global_to_token:
            raise sealed_worker.R23AuthorError(
                "Attempt04 topology references a vertex absent from stable map"
            )
        result.add(
            stable_edge(global_to_token[int(first)], global_to_token[int(second)])
        )
    return result


def source_stable_edges(edges: Iterable[tuple[int, int]]) -> set[tuple[str, str]]:
    return {
        stable_edge(stable_source_vertex(first), stable_source_vertex(second))
        for first, second in edges
    }


def attempt04_topology_gate(
    body: bpy.types.Object,
    patch_face_indices: Sequence[int],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    baseline = RUNTIME.get("source_baseline")
    final_map = RUNTIME.get("final_stable_vertex_map")
    if not baseline or not final_map:
        raise sealed_worker.R23AuthorError(
            "Attempt04 topology gate lacks source baseline or stable vertex map"
        )
    global_to_token = final_map["global_to_token"]
    if set(global_to_token) != set(range(len(body.data.vertices))):
        raise sealed_worker.R23AuthorError(
            "Attempt04 final stable vertex map does not cover the exact mesh"
        )
    faces = sealed_worker.preflight_base.faces_of(body)
    all_faces = set(range(len(faces)))
    patch_set = {int(value) for value in patch_face_indices}
    face_incidence = edge_face_map(faces)
    face_derived_edges = set(face_incidence)
    boundary = {edge for edge, owners in face_incidence.items() if len(owners) == 1}
    overused = {edge for edge, owners in face_incidence.items() if len(owners) > 2}
    mesh_edge_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for edge in body.data.edges:
        mesh_edge_groups[canonical_edge(edge.vertices[0], edge.vertices[1])].append(
            int(edge.index)
        )
    duplicate_mesh_edges = {
        edge: indices for edge, indices in mesh_edge_groups.items() if len(indices) != 1
    }
    mesh_edges = set(mesh_edge_groups)
    loose = mesh_edges.difference(face_derived_edges)
    stable_boundary = stable_edges_from_global(boundary, global_to_token)
    stable_overused = stable_edges_from_global(overused, global_to_token)
    stable_loose = stable_edges_from_global(loose, global_to_token)
    source_boundary = source_stable_edges(baseline["_boundary_set"])
    source_overused = source_stable_edges(baseline["_overused_set"])
    source_loose = source_stable_edges(baseline["_loose_set"])
    whole = sealed_worker.preflight_base.topology_record(faces, all_faces)
    patch = sealed_worker.preflight_base.topology_record(faces, patch_set)

    removed = int(config["selected_target_mask"]["removable_interior_vertex_count"])
    patch_vertices = int(config["expected_structural_result"]["replacement_patch_vertices"])
    seam_vertices = int(config["selected_target_mask"]["outer_seam_vertex_count"])
    selected_faces = int(config["selected_target_mask"]["face_count"])
    patch_faces = int(config["expected_structural_result"]["replacement_patch_faces"])
    expected_vertices = int(baseline["vertices"]) - removed + (
        patch_vertices - seam_vertices
    )
    expected_faces = int(baseline["faces"]) - selected_faces + patch_faces
    expected_face_euler = int(baseline["face_euler"])
    expected_face_edges = expected_vertices + expected_faces - expected_face_euler
    expected_mesh_euler = int(baseline["mesh_euler"])
    expected_mesh_edges = expected_vertices + expected_faces - expected_mesh_euler
    nominal = RUNTIME["repair_config"]["nominal_corrected_final"]
    expected = config["expected_structural_result"]
    missing_boundary = source_boundary.difference(stable_boundary)
    new_boundary = stable_boundary.difference(source_boundary)
    missing_overused = source_overused.difference(stable_overused)
    new_overused = stable_overused.difference(source_overused)
    missing_loose = source_loose.difference(stable_loose)
    new_loose = stable_loose.difference(source_loose)
    expected_vertex_tokens = {
        stable_source_vertex(index)
        for index in range(int(baseline["vertices"]))
        if index not in baseline["_removable_vertices"]
    }.union(
        {
            stable_patch_vertex(index)
            for index in range(seam_vertices, patch_vertices)
        }
    )
    actual_vertex_tokens = set(final_map["token_to_global"])
    checks = {
        "derived_vertices": len(body.data.vertices) == expected_vertices,
        "derived_face_edges": len(face_derived_edges) == expected_face_edges,
        "derived_mesh_edges": len(body.data.edges) == expected_mesh_edges,
        "derived_faces": len(faces) == expected_faces,
        "derived_face_euler": (
            len(body.data.vertices) - len(face_derived_edges) + len(faces)
        )
        == expected_face_euler,
        "derived_mesh_euler": (
            len(body.data.vertices) - len(body.data.edges) + len(faces)
        )
        == expected_mesh_euler,
        "nominal_vertices": len(body.data.vertices) == int(nominal["vertices"]),
        "nominal_face_edges": len(face_derived_edges)
        == int(nominal["face_derived_edges"]),
        "nominal_mesh_edges": len(body.data.edges) == int(nominal["mesh_edges"]),
        "nominal_faces": len(faces) == int(nominal["faces"]),
        "nominal_euler": expected_face_euler == int(nominal["euler"]),
        "stable_vertex_token_set_exact": actual_vertex_tokens
        == expected_vertex_tokens,
        "whole_components_preserved": whole["component_count"]
        == baseline["components"],
        "whole_boundary_count_preserved": len(boundary)
        == baseline["boundary_edges"],
        "whole_boundary_cycles_preserved": whole["boundary_cycle_count"]
        == baseline["boundary_cycles"],
        "whole_boundary_cycle_lengths_preserved": whole["boundary_cycle_lengths"]
        == baseline["boundary_cycle_lengths"],
        "stable_source_boundary_exact": stable_boundary == source_boundary,
        "zero_new_boundary": not new_boundary,
        "zero_missing_boundary": not missing_boundary,
        "zero_greater_than_two_face_edges": len(overused) == 0,
        "zero_new_greater_than_two_face_edges": not new_overused,
        "zero_missing_source_greater_than_two_face_edges": not missing_overused,
        "zero_loose_mesh_edges": len(loose) == 0,
        "zero_new_loose_mesh_edges": not new_loose,
        "zero_missing_source_loose_mesh_edges": not missing_loose,
        "zero_duplicate_mesh_edges": not duplicate_mesh_edges,
        "patch_vertices": patch["vertex_count"]
        == expected["replacement_patch_vertices"],
        "patch_faces": patch["face_count"] == expected["replacement_patch_faces"],
        "patch_edges": patch["edge_count"] == expected["replacement_patch_edges"],
        "patch_components": patch["component_count"]
        == expected["replacement_patch_components"],
        "patch_boundary_cycles": patch["boundary_cycle_count"]
        == expected["replacement_patch_boundary_cycles"],
        "patch_boundary_length": patch["boundary_cycle_lengths"]
        == [expected["replacement_patch_boundary_vertices"]],
        "patch_euler": patch["euler_characteristic"]
        == expected["replacement_patch_euler_characteristic"],
    }
    if not all(checks.values()):
        raise sealed_worker.R23AuthorError(
            f"Attempt04 source-preserving structural gate failed: {checks}"
        )
    return {
        "whole_body": whole,
        "replacement_patch": patch,
        "source_preserving_euler_derivation": {
            "source_vertices": baseline["vertices"],
            "source_mesh_edges": baseline["mesh_edges"],
            "source_face_derived_edges": baseline["face_derived_edges"],
            "source_faces": baseline["faces"],
            "source_face_euler": baseline["face_euler"],
            "source_mesh_euler": baseline["mesh_euler"],
            "removed_interior_vertices": removed,
            "replacement_new_vertices": patch_vertices - seam_vertices,
            "removed_disk_faces": selected_faces,
            "replacement_disk_faces": patch_faces,
            "removed_disk_euler": 1,
            "replacement_disk_euler": 1,
            "expected_vertices": expected_vertices,
            "expected_mesh_edges": expected_mesh_edges,
            "expected_face_derived_edges": expected_face_edges,
            "expected_faces": expected_faces,
            "expected_face_euler": expected_face_euler,
            "expected_mesh_euler": expected_mesh_euler,
            "closed_whole_body_assumed": False,
        },
        "stable_boundary_preservation": {
            "source_count": len(source_boundary),
            "final_count": len(stable_boundary),
            "source_sha256": edge_set_sha256(source_boundary),
            "final_sha256": edge_set_sha256(stable_boundary),
            "new_count": len(new_boundary),
            "new_sha256": edge_set_sha256(new_boundary),
            "missing_count": len(missing_boundary),
            "missing_sha256": edge_set_sha256(missing_boundary),
        },
        "greater_than_two_face_nonmanifold": {
            "source_count": len(source_overused),
            "final_count": len(stable_overused),
            "new_count": len(new_overused),
            "new_sha256": edge_set_sha256(new_overused),
        },
        "loose_edges": {
            "source_count": len(source_loose),
            "final_count": len(stable_loose),
            "new_count": len(new_loose),
            "new_sha256": edge_set_sha256(new_loose),
            "final_sha256": edge_set_sha256(stable_loose),
        },
        "duplicate_mesh_edge_group_count": len(duplicate_mesh_edges),
        "checks": checks,
    }


def bind_attempt04_runtime(repair_config: Mapping[str, Any]) -> None:
    RUNTIME.clear()
    RUNTIME["repair_config"] = repair_config
    sealed_worker.preflight_base.edge_face_map = edge_face_map
    sealed_worker.output_paths = attempt04_output_paths
    sealed_worker.exact_donor_disk = attempt04_exact_donor_disk
    sealed_worker.bmesh_frozen_snapshot = attempt04_bmesh_frozen_snapshot
    sealed_worker.apply_patch = attempt04_apply_patch
    sealed_worker.topology_gate = attempt04_topology_gate


def main() -> int:
    repair_config, verified = verify_repair_config()
    RUNTIME["verified_repair_inputs"] = verified
    bind_attempt04_runtime(repair_config)
    RUNTIME["verified_repair_inputs"] = verified
    return int(sealed_worker.main())


if __name__ == "__main__":
    raise SystemExit(main())
