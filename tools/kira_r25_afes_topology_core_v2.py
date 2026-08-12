#!/usr/bin/env python3
"""Compact, receipt-safe AFES topology evidence helpers for R25 Attempt 02.

The existing Attempt-01 topology classifier remains immutable and supplies the
in-memory semantic sets.  This module converts every explicit index/edge array
to one deduplicated, deterministic, big-endian unsigned-32-bit binary blob and
provides strict pure-Python decoders/validators for a future parent.

No function in this module opens Blender, edits geometry, persists a path, or
grants body-authoring authority.
"""

from __future__ import annotations

import base64
import binascii
from collections import defaultdict
import ctypes
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import math
import os
import struct
from typing import Any, Iterable, Mapping, Sequence

from tools.kira_r25_afes_topology_core import (
    AfesTopologyError,
    analyze_afes_topology,
    canonical_index_sha256,
    canonical_json_sha256,
    normalize_edges,
    normalize_faces,
)


UINT32_MAX = 2**32 - 1
SIGNED64_MIN = -(2**63)
SIGNED64_MAX = 2**63 - 1
NANOMETERS_PER_METER = 1_000_000_000
BLOB_CODEC = "uint32_big_endian_v1"
INDEX_SEMANTIC = "sorted_unique_index_json_sha256_v1"
EDGE_SEMANTIC = "sorted_unique_undirected_edge_pair_json_sha256_v1"
ROUNDING_RULE = "decimal_from_shortest_roundtrip_float_then_half_even_to_integer"
FILE_TYPE_PIPE = 3


class CompactAfesEvidenceError(ValueError):
    """Raised when compact evidence is ambiguous, corrupt, or inconsistent."""


def require_win32_pipe_handle(
    raw_handle: object,
    *,
    kernel32: object | None = None,
    platform_name: str | None = None,
) -> int:
    """Prove a caller-owned handle is a Win32 pipe before any adoption/write.

    ``kernel32`` and ``platform_name`` are injectable solely so ordinary
    Python tests can exercise the allow/deny boundary without opening a real
    handle.  Disk files, consoles, character devices, unknown handles, and all
    non-Windows platforms are rejected.
    """

    handle = _signed64(raw_handle, label="result handle")
    if handle <= 0:
        raise CompactAfesEvidenceError("result handle must be positive")
    platform = os.name if platform_name is None else str(platform_name)
    if platform != "nt":
        raise CompactAfesEvidenceError("result handle transport requires Windows")
    library = kernel32
    if library is None:
        library = ctypes.WinDLL("kernel32", use_last_error=True)
        library.GetFileType.argtypes = [ctypes.c_void_p]
        library.GetFileType.restype = ctypes.c_uint32
    try:
        file_type = int(library.GetFileType(ctypes.c_void_p(handle)))
    except (AttributeError, TypeError, ValueError, OSError) as exc:
        raise CompactAfesEvidenceError(
            f"could not classify inherited result handle: {exc}"
        ) from exc
    if file_type != FILE_TYPE_PIPE:
        raise CompactAfesEvidenceError(
            f"inherited result handle is not FILE_TYPE_PIPE: {file_type}"
        )
    return handle


def _u32(value: object, *, label: str) -> int:
    if type(value) is not int:
        raise CompactAfesEvidenceError(f"{label} must be an integer")
    result = int(value)
    if result < 0 or result > UINT32_MAX:
        raise CompactAfesEvidenceError(f"{label} is outside unsigned 32-bit range")
    return result


def _signed64(value: object, *, label: str) -> int:
    if type(value) is not int:
        raise CompactAfesEvidenceError(f"{label} must be an integer")
    result = int(value)
    if result < SIGNED64_MIN or result > SIGNED64_MAX:
        raise CompactAfesEvidenceError(f"{label} is outside signed 64-bit range")
    return result


def meters_float_to_nanometers(value: object) -> int:
    """Quantize a Blender meter coordinate with one documented exact rule.

    Python's shortest round-trip decimal spelling of the finite binary float is
    converted to ``Decimal``, multiplied by exactly 1,000,000,000, and rounded
    to an integer using ties-to-even.  Only the resulting signed-64-bit integer
    may enter a receipt payload.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompactAfesEvidenceError("meter coordinate must be a real scalar")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise CompactAfesEvidenceError("meter coordinate must be finite")
    decimal_value = Decimal(repr(numeric))
    quantized = int(
        (decimal_value * Decimal(NANOMETERS_PER_METER)).to_integral_value(
            rounding=ROUND_HALF_EVEN
        )
    )
    return _signed64(quantized, label="nanometer coordinate")


def quantize_bounds_to_nanometers(
    bounds_m: Mapping[str, Sequence[object]],
) -> dict[str, object]:
    if set(bounds_m) != {"minimum", "maximum"}:
        raise CompactAfesEvidenceError("bounds must contain exactly minimum and maximum")
    result: dict[str, list[int]] = {}
    for side in ("minimum", "maximum"):
        values = tuple(bounds_m[side])
        if len(values) != 3:
            raise CompactAfesEvidenceError(f"bounds {side} must have three coordinates")
        result[side] = [meters_float_to_nanometers(value) for value in values]
    return {
        "unit": "nanometer",
        "integer_units_per_meter": NANOMETERS_PER_METER,
        "rounding": ROUNDING_RULE,
        "minimum": result["minimum"],
        "maximum": result["maximum"],
    }


def analyze_foundation_topology_structure(
    *,
    vertex_count: int,
    edges: Iterable[Sequence[int]],
    faces: Iterable[Sequence[int]],
    transition_vertices: Iterable[int] = (),
) -> dict[str, object]:
    """Return deterministic whole-mesh structural metrics without Blender.

    Every polygon boundary edge must exist in the explicit mesh-edge table.
    Connected components include isolated vertices.  Duplicate polygons are
    detected independent of winding/rotation by their sorted vertex sets.
    """

    normalized_edges = normalize_edges(vertex_count, edges)
    normalized_faces = normalize_faces(vertex_count, faces)
    edge_set = set(normalized_edges)
    edge_face_incidence: dict[tuple[int, int], int] = {
        edge: 0 for edge in normalized_edges
    }
    missing_face_edges: set[tuple[int, int]] = set()
    for face in normalized_faces:
        for position, first in enumerate(face):
            second = face[(position + 1) % len(face)]
            edge = tuple(sorted((first, second)))
            if edge not in edge_set:
                missing_face_edges.add(edge)
            else:
                edge_face_incidence[edge] += 1

    adjacency: list[set[int]] = [set() for _ in range(vertex_count)]
    for first, second in normalized_edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    unvisited = set(range(vertex_count))
    component_count = 0
    isolated_vertex_count = 0
    while unvisited:
        component_count += 1
        seed = min(unvisited)
        if not adjacency[seed]:
            isolated_vertex_count += 1
        stack = [seed]
        unvisited.remove(seed)
        while stack:
            current = stack.pop()
            for neighbor in sorted(adjacency[current], reverse=True):
                if neighbor in unvisited:
                    unvisited.remove(neighbor)
                    stack.append(neighbor)

    face_keys = [tuple(sorted(face)) for face in normalized_faces]
    duplicate_face_record_count = len(face_keys) - len(set(face_keys))
    boundary_edges = tuple(
        edge for edge, count in sorted(edge_face_incidence.items()) if count == 1
    )
    nonmanifold_edges = tuple(
        edge for edge, count in sorted(edge_face_incidence.items()) if count > 2
    )
    loose_edges = tuple(
        edge for edge, count in sorted(edge_face_incidence.items()) if count == 0
    )
    transition_set = {
        _u32(value, label="transition vertex") for value in transition_vertices
    }
    if any(value >= vertex_count for value in transition_set):
        raise CompactAfesEvidenceError("transition vertex is outside the mesh")
    transition_loose_edges = tuple(
        edge
        for edge in loose_edges
        if edge[0] in transition_set or edge[1] in transition_set
    )
    topology_sha256 = canonical_json_sha256(
        {
            "vertex_count": vertex_count,
            "edges": [list(edge) for edge in normalized_edges],
            "faces": [list(face) for face in normalized_faces],
        }
    )
    return {
        "full_normalized_topology_sha256": topology_sha256,
        "connected_component_count": component_count,
        "isolated_vertex_count": isolated_vertex_count,
        "boundary_edge_count": len(boundary_edges),
        "nonmanifold_edge_count": len(nonmanifold_edges),
        "loose_edge_count": len(loose_edges),
        "face_boundary_edge_missing_from_mesh_count": len(missing_face_edges),
        "duplicate_face_record_count": duplicate_face_record_count,
        "transition_ring_loose_edge_incidence_count": len(transition_loose_edges),
    }


def analyze_afes_topology_v2(
    *,
    vertex_count: int,
    edges: Iterable[Sequence[int]],
    faces: Iterable[Sequence[int]],
    memberships: Mapping[str, Iterable[int]],
    required_group_names: Sequence[str],
    transition_ring_count: int = 2,
) -> dict[str, object]:
    """Run immutable Attempt-01 classification plus Attempt-02 structure audit."""

    edge_rows = tuple(tuple(edge) for edge in edges)
    face_rows = tuple(tuple(face) for face in faces)
    membership_rows = {
        str(name): tuple(values) for name, values in memberships.items()
    }
    analysis = analyze_afes_topology(
        vertex_count=vertex_count,
        edges=edge_rows,
        faces=face_rows,
        memberships=membership_rows,
        required_group_names=required_group_names,
        transition_ring_count=transition_ring_count,
    )
    transition_vertices = analysis["transition_rings"]["combined_vertex_indices"]
    structure = analyze_foundation_topology_structure(
        vertex_count=vertex_count,
        edges=edge_rows,
        faces=face_rows,
        transition_vertices=transition_vertices,
    )
    if analysis["whole_mesh"]["topology_sha256"] != structure[
        "full_normalized_topology_sha256"
    ]:
        raise CompactAfesEvidenceError("whole-topology digest computation drifted")
    result = dict(analysis)
    result["topology_structure"] = structure
    return result


def _normalize_indices(values: Iterable[int]) -> tuple[int, ...]:
    normalized = tuple(_u32(value, label="index") for value in values)
    if tuple(sorted(set(normalized))) != normalized:
        raise CompactAfesEvidenceError("index array must be strictly increasing and unique")
    return normalized


def _normalize_edges(values: Iterable[Sequence[int]]) -> tuple[tuple[int, int], ...]:
    edges: list[tuple[int, int]] = []
    for raw in values:
        pair = tuple(raw)
        if len(pair) != 2:
            raise CompactAfesEvidenceError("edge record must contain exactly two indices")
        first = _u32(pair[0], label="edge endpoint")
        second = _u32(pair[1], label="edge endpoint")
        if first >= second:
            raise CompactAfesEvidenceError("edge endpoints must be strictly increasing")
        edges.append((first, second))
    normalized = tuple(edges)
    if tuple(sorted(set(normalized))) != normalized:
        raise CompactAfesEvidenceError("edge array must be sorted and unique")
    return normalized


def _encode_u32(values: Sequence[int]) -> bytes:
    return b"".join(struct.pack(">I", _u32(value, label="encoded value")) for value in values)


class BinaryArrayTable:
    """Deduplicate exact raw arrays while preserving separate semantic refs."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, object]] = {}

    def _add_flat(self, values: Sequence[int]) -> str:
        raw = _encode_u32(values)
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        reference = f"sha256:{raw_sha256}"
        record = {
            "codec": BLOB_CODEC,
            "endianness": "big",
            "u32_count": len(values),
            "raw_bytes": len(raw),
            "raw_sha256": raw_sha256,
            "base64": base64.b64encode(raw).decode("ascii"),
        }
        existing = self._records.get(reference)
        if existing is not None and existing != record:
            raise CompactAfesEvidenceError("binary array SHA collision or record drift")
        self._records[reference] = record
        return reference

    def add_indices(self, values: Iterable[int]) -> dict[str, object]:
        normalized = _normalize_indices(values)
        return {
            "blob_ref": self._add_flat(normalized),
            "semantic": INDEX_SEMANTIC,
            "item_count": len(normalized),
            "semantic_sha256": canonical_index_sha256(normalized),
        }

    def add_edges(self, values: Iterable[Sequence[int]]) -> dict[str, object]:
        normalized = _normalize_edges(values)
        flat = tuple(component for edge in normalized for component in edge)
        return {
            "blob_ref": self._add_flat(flat),
            "semantic": EDGE_SEMANTIC,
            "item_count": len(normalized),
            "semantic_sha256": canonical_json_sha256(
                [list(edge) for edge in normalized]
            ),
        }

    def records(self) -> dict[str, dict[str, object]]:
        return {key: dict(self._records[key]) for key in sorted(self._records)}


def decode_blob(reference: str, record: Mapping[str, Any]) -> tuple[int, ...]:
    required = {
        "codec",
        "endianness",
        "u32_count",
        "raw_bytes",
        "raw_sha256",
        "base64",
    }
    if set(record) != required:
        raise CompactAfesEvidenceError("binary array record keys drifted")
    if record["codec"] != BLOB_CODEC or record["endianness"] != "big":
        raise CompactAfesEvidenceError("binary array codec or endianness drifted")
    count = _u32(record["u32_count"], label="declared u32 count")
    raw_bytes = _u32(record["raw_bytes"], label="declared raw byte count")
    if raw_bytes != count * 4:
        raise CompactAfesEvidenceError("binary array byte/count relationship drifted")
    encoded = record["base64"]
    if not isinstance(encoded, str):
        raise CompactAfesEvidenceError("binary array base64 is not text")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise CompactAfesEvidenceError(f"binary array base64 is invalid: {exc}") from exc
    if len(raw) != raw_bytes:
        raise CompactAfesEvidenceError("decoded binary array length drifted")
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise CompactAfesEvidenceError("binary array base64 is not canonical")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    if record["raw_sha256"] != raw_sha256 or reference != f"sha256:{raw_sha256}":
        raise CompactAfesEvidenceError("binary array raw SHA or reference drifted")
    if not raw:
        return ()
    return tuple(value[0] for value in struct.iter_unpack(">I", raw))


def decode_index_reference(
    reference: Mapping[str, Any], blobs: Mapping[str, Mapping[str, Any]]
) -> tuple[int, ...]:
    if set(reference) != {"blob_ref", "semantic", "item_count", "semantic_sha256"}:
        raise CompactAfesEvidenceError("index reference keys drifted")
    if reference["semantic"] != INDEX_SEMANTIC:
        raise CompactAfesEvidenceError("index semantic codec drifted")
    blob_ref = reference["blob_ref"]
    if not isinstance(blob_ref, str) or blob_ref not in blobs:
        raise CompactAfesEvidenceError("index reference points to an absent blob")
    values = decode_blob(blob_ref, blobs[blob_ref])
    values = _normalize_indices(values)
    item_count = _u32(reference["item_count"], label="index semantic item count")
    if len(values) != item_count:
        raise CompactAfesEvidenceError("index semantic count drifted")
    if not isinstance(reference["semantic_sha256"], str) or canonical_index_sha256(
        values
    ) != reference["semantic_sha256"]:
        raise CompactAfesEvidenceError("index semantic digest drifted")
    return values


def decode_edge_reference(
    reference: Mapping[str, Any], blobs: Mapping[str, Mapping[str, Any]]
) -> tuple[tuple[int, int], ...]:
    if set(reference) != {"blob_ref", "semantic", "item_count", "semantic_sha256"}:
        raise CompactAfesEvidenceError("edge reference keys drifted")
    if reference["semantic"] != EDGE_SEMANTIC:
        raise CompactAfesEvidenceError("edge semantic codec drifted")
    blob_ref = reference["blob_ref"]
    if not isinstance(blob_ref, str) or blob_ref not in blobs:
        raise CompactAfesEvidenceError("edge reference points to an absent blob")
    flat = decode_blob(blob_ref, blobs[blob_ref])
    if len(flat) % 2:
        raise CompactAfesEvidenceError("edge blob has an odd u32 count")
    edges = _normalize_edges(zip(flat[0::2], flat[1::2]))
    item_count = _u32(reference["item_count"], label="edge semantic item count")
    if len(edges) != item_count:
        raise CompactAfesEvidenceError("edge semantic count drifted")
    if not isinstance(reference["semantic_sha256"], str) or canonical_json_sha256(
        [list(edge) for edge in edges]
    ) != reference["semantic_sha256"]:
        raise CompactAfesEvidenceError("edge semantic digest drifted")
    return edges


def compact_afes_analysis(
    analysis: Mapping[str, Any], bounds_object_nm: Mapping[str, Any]
) -> dict[str, object]:
    """Replace every explicit Attempt-01 array with one referenced binary blob."""

    table = BinaryArrayTable()
    groups: dict[str, dict[str, object]] = {}
    for name in sorted(analysis["groups"]):
        row = analysis["groups"][name]
        reference = table.add_indices(row["vertex_indices"])
        if reference["item_count"] != row["vertex_count"] or reference[
            "semantic_sha256"
        ] != row["vertex_index_sha256"]:
            raise CompactAfesEvidenceError(f"group semantic drift before compaction: {name}")
        groups[name] = {"vertex_indices": reference}
    union = analysis["afes_union"]
    compact_union = {
        "vertex_indices": table.add_indices(union["vertex_indices"]),
        "incident_face_indices": table.add_indices(union["incident_face_indices"]),
        "internal_face_indices": table.add_indices(union["internal_face_indices"]),
        "primary_connection_edges": table.add_edges(union["connection_edges"]),
    }
    expected_union_fields = {
        "vertex_indices": (union["vertex_count"], union["vertex_index_sha256"]),
        "incident_face_indices": (
            union["incident_face_count"],
            union["incident_face_index_sha256"],
        ),
        "internal_face_indices": (
            union["internal_face_count"],
            union["internal_face_index_sha256"],
        ),
        "primary_connection_edges": (
            union["primary_connection_edge_count"],
            union["connection_edge_sha256"],
        ),
    }
    for name, (count, digest) in expected_union_fields.items():
        if compact_union[name]["item_count"] != count or compact_union[name][
            "semantic_sha256"
        ] != digest:
            raise CompactAfesEvidenceError(f"AFES union semantic drift: {name}")
    compact_rings = []
    for row in analysis["transition_rings"]["rings"]:
        reference = table.add_indices(row["vertex_indices"])
        if reference["item_count"] != row["vertex_count"] or reference[
            "semantic_sha256"
        ] != row["vertex_index_sha256"]:
            raise CompactAfesEvidenceError("transition ring semantic drift")
        compact_rings.append(
            {"ring_number": int(row["ring_number"]), "vertex_indices": reference}
        )
    combined = table.add_indices(
        analysis["transition_rings"]["combined_vertex_indices"]
    )
    if combined["item_count"] != analysis["transition_rings"][
        "combined_vertex_count"
    ] or combined["semantic_sha256"] != analysis["transition_rings"][
        "combined_vertex_index_sha256"
    ]:
        raise CompactAfesEvidenceError("combined transition-ring semantic drift")
    result = {
        "whole_mesh": dict(analysis["whole_mesh"]),
        "topology_structure": dict(analysis["topology_structure"]),
        "groups": groups,
        "afes_union": compact_union,
        "transition_rings": {
            "ring_count": int(analysis["transition_rings"]["ring_count"]),
            "rings": compact_rings,
            "combined_vertex_indices": combined,
            "disjoint_from_afes_union": bool(
                analysis["transition_rings"]["disjoint_from_afes_union"]
            ),
        },
        "bounds_object_nm": dict(bounds_object_nm),
        "binary_arrays": table.records(),
    }
    validate_compact_afes_analysis(result)
    return result


def validate_compact_afes_analysis(compact: Mapping[str, Any]) -> dict[str, object]:
    """Decode and cross-check every blob/reference; return reconstructed sets."""

    if set(compact) != {
        "whole_mesh",
        "topology_structure",
        "groups",
        "afes_union",
        "transition_rings",
        "bounds_object_nm",
        "binary_arrays",
    }:
        raise CompactAfesEvidenceError("compact AFES top-level keys drifted")
    whole = compact.get("whole_mesh")
    if not isinstance(whole, Mapping) or set(whole) != {
        "vertex_count",
        "edge_count",
        "face_count",
        "topology_sha256",
    }:
        raise CompactAfesEvidenceError("whole-mesh record drifted")
    vertex_count = _signed64(whole["vertex_count"], label="mesh vertex count")
    edge_count = _signed64(whole["edge_count"], label="mesh edge count")
    face_count = _signed64(whole["face_count"], label="mesh face count")
    if min(vertex_count, edge_count, face_count) <= 0:
        raise CompactAfesEvidenceError("whole-mesh counts must be positive")
    topology_digest = whole["topology_sha256"]
    if not isinstance(topology_digest, str) or len(topology_digest) != 64:
        raise CompactAfesEvidenceError("whole-mesh topology digest drifted")
    structure = compact.get("topology_structure")
    structural_count_keys = {
        "connected_component_count",
        "isolated_vertex_count",
        "boundary_edge_count",
        "nonmanifold_edge_count",
        "loose_edge_count",
        "face_boundary_edge_missing_from_mesh_count",
        "duplicate_face_record_count",
        "transition_ring_loose_edge_incidence_count",
    }
    if not isinstance(structure, Mapping) or set(structure) != structural_count_keys | {
        "full_normalized_topology_sha256"
    }:
        raise CompactAfesEvidenceError("whole-mesh structural record drifted")
    if structure["full_normalized_topology_sha256"] != topology_digest:
        raise CompactAfesEvidenceError("full normalized topology digest drifted")
    structural_counts = {
        key: _signed64(structure[key], label=f"structural metric {key}")
        for key in structural_count_keys
    }
    if any(value < 0 for value in structural_counts.values()):
        raise CompactAfesEvidenceError("structural metrics cannot be negative")
    if structural_counts["connected_component_count"] != 1 or any(
        structural_counts[key] != 0
        for key in structural_count_keys
        if key != "connected_component_count"
    ):
        raise CompactAfesEvidenceError("foundation structural acceptance metrics failed")

    blobs = compact.get("binary_arrays")
    if not isinstance(blobs, Mapping):
        raise CompactAfesEvidenceError("binary array table is absent")
    decoded_blob_hashes: set[str] = set()
    for reference in sorted(blobs):
        if not isinstance(reference, str) or not isinstance(blobs[reference], Mapping):
            raise CompactAfesEvidenceError("binary array table entry is invalid")
        decode_blob(reference, blobs[reference])
        raw_hash = str(blobs[reference]["raw_sha256"])
        if raw_hash in decoded_blob_hashes:
            raise CompactAfesEvidenceError("duplicate raw binary array was stored")
        decoded_blob_hashes.add(raw_hash)
    referenced: set[str] = set()

    def index_values(ref: Mapping[str, Any]) -> tuple[int, ...]:
        values = decode_index_reference(ref, blobs)
        referenced.add(str(ref["blob_ref"]))
        return values

    groups = compact.get("groups")
    if not isinstance(groups, Mapping) or not groups:
        raise CompactAfesEvidenceError("compact AFES groups are absent")
    decoded_groups = {
        str(name): index_values(row["vertex_indices"])
        for name, row in sorted(groups.items())
    }
    union_row = compact["afes_union"]
    union = index_values(union_row["vertex_indices"])
    incident = index_values(union_row["incident_face_indices"])
    internal = index_values(union_row["internal_face_indices"])
    edges = decode_edge_reference(union_row["primary_connection_edges"], blobs)
    referenced.add(str(union_row["primary_connection_edges"]["blob_ref"]))
    reconstructed_union = tuple(
        sorted({value for values in decoded_groups.values() for value in values})
    )
    if reconstructed_union != union:
        raise CompactAfesEvidenceError("group union differs from compact AFES union")
    if union and union[-1] >= vertex_count:
        raise CompactAfesEvidenceError("AFES union index exceeds mesh vertex count")
    if incident and incident[-1] >= face_count:
        raise CompactAfesEvidenceError("incident-face index exceeds mesh face count")
    if internal and internal[-1] >= face_count:
        raise CompactAfesEvidenceError("internal-face index exceeds mesh face count")
    if edges and max(component for edge in edges for component in edge) >= vertex_count:
        raise CompactAfesEvidenceError("connection edge exceeds mesh vertex count")
    rings_row = compact["transition_rings"]
    ring_rows = rings_row["rings"]
    if rings_row["ring_count"] != len(ring_rows) or len(ring_rows) != 2:
        raise CompactAfesEvidenceError("compact transition ring count drifted")
    rings: list[tuple[int, ...]] = []
    for expected_number, row in enumerate(ring_rows, start=1):
        if row["ring_number"] != expected_number:
            raise CompactAfesEvidenceError("transition ring order drifted")
        rings.append(index_values(row["vertex_indices"]))
    if any(ring and ring[-1] >= vertex_count for ring in rings):
        raise CompactAfesEvidenceError("transition-ring index exceeds mesh vertex count")
    if set(rings[0]).intersection(rings[1]):
        raise CompactAfesEvidenceError("transition rings overlap each other")
    combined = index_values(rings_row["combined_vertex_indices"])
    reconstructed_combined = tuple(sorted({value for ring in rings for value in ring}))
    if combined != reconstructed_combined:
        raise CompactAfesEvidenceError("combined transition-ring array drifted")
    if set(union).intersection(combined) or not rings_row["disjoint_from_afes_union"]:
        raise CompactAfesEvidenceError("transition rings overlap the AFES union")
    if referenced != set(blobs):
        raise CompactAfesEvidenceError("binary array table contains an unreferenced blob")
    bounds = compact["bounds_object_nm"]
    if bounds.get("unit") != "nanometer" or bounds.get(
        "integer_units_per_meter"
    ) != NANOMETERS_PER_METER or bounds.get("rounding") != ROUNDING_RULE:
        raise CompactAfesEvidenceError("integer bounds codec drifted")
    for side in ("minimum", "maximum"):
        values = bounds.get(side)
        if not isinstance(values, list) or len(values) != 3:
            raise CompactAfesEvidenceError("integer bounds shape drifted")
        for value in values:
            _signed64(value, label="integer bound")
    return {
        "groups": decoded_groups,
        "afes_union": union,
        "incident_faces": incident,
        "internal_faces": internal,
        "connection_edges": edges,
        "transition_rings": tuple(rings),
        "combined_transition_vertices": combined,
    }


__all__ = [
    "AfesTopologyError",
    "BLOB_CODEC",
    "BinaryArrayTable",
    "CompactAfesEvidenceError",
    "EDGE_SEMANTIC",
    "INDEX_SEMANTIC",
    "NANOMETERS_PER_METER",
    "ROUNDING_RULE",
    "FILE_TYPE_PIPE",
    "analyze_afes_topology_v2",
    "analyze_foundation_topology_structure",
    "analyze_afes_topology",
    "compact_afes_analysis",
    "decode_blob",
    "decode_edge_reference",
    "decode_index_reference",
    "meters_float_to_nanometers",
    "quantize_bounds_to_nanometers",
    "require_win32_pipe_handle",
    "validate_compact_afes_analysis",
]
