#!/usr/bin/env python3
"""Deterministic, Blender-free AFES topology diagnostics for Kira R25.

This module only classifies existing mesh indices.  It does not author,
deform, save, render, or otherwise mutate a body.  The Blender-side reader
supplies exact vertex-group memberships plus the existing edge/face topology;
ordinary Python tests can exercise every classification rule without opening
a Blend file.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Iterable, Mapping, Sequence


Edge = tuple[int, int]
Face = tuple[int, ...]


class AfesTopologyError(ValueError):
    """Raised when input cannot produce an exact, deterministic diagnostic."""


def canonical_json_bytes(value: object) -> bytes:
    """Return the same compact/sorted JSON encoding used by the sealed R23 audit."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_index_sha256(values: Iterable[int]) -> str:
    return canonical_json_sha256(sorted({int(value) for value in values}))


def _index(value: object, *, vertex_count: int, label: str) -> int:
    if type(value) is not int:  # bool is intentionally rejected.
        raise AfesTopologyError(f"{label} must be an integer")
    result = int(value)
    if result < 0 or result >= vertex_count:
        raise AfesTopologyError(
            f"{label} {result} is outside vertex range 0..{vertex_count - 1}"
        )
    return result


def normalize_edges(vertex_count: int, raw_edges: Iterable[Sequence[int]]) -> tuple[Edge, ...]:
    if type(vertex_count) is not int or vertex_count <= 0:
        raise AfesTopologyError("vertex_count must be a positive integer")
    edges: list[Edge] = []
    for position, raw in enumerate(raw_edges):
        values = tuple(raw)
        if len(values) != 2:
            raise AfesTopologyError(f"edge {position} does not contain two vertices")
        first = _index(values[0], vertex_count=vertex_count, label=f"edge {position}")
        second = _index(values[1], vertex_count=vertex_count, label=f"edge {position}")
        if first == second:
            raise AfesTopologyError(f"edge {position} is a self edge")
        edges.append(tuple(sorted((first, second))))
    if len(set(edges)) != len(edges):
        raise AfesTopologyError("duplicate mesh edge")
    return tuple(sorted(edges))


def normalize_faces(vertex_count: int, raw_faces: Iterable[Sequence[int]]) -> tuple[Face, ...]:
    faces: list[Face] = []
    for position, raw in enumerate(raw_faces):
        values = tuple(
            _index(value, vertex_count=vertex_count, label=f"face {position}")
            for value in raw
        )
        if len(values) < 3:
            raise AfesTopologyError(f"face {position} has fewer than three vertices")
        if len(set(values)) != len(values):
            raise AfesTopologyError(f"face {position} repeats a vertex")
        faces.append(values)
    if not faces:
        raise AfesTopologyError("mesh has no faces")
    return tuple(faces)


def normalize_memberships(
    vertex_count: int,
    raw_memberships: Mapping[str, Iterable[int]],
    required_group_names: Sequence[str],
) -> dict[str, tuple[int, ...]]:
    required = tuple(sorted(str(name) for name in required_group_names))
    if len(set(required)) != len(required) or not required:
        raise AfesTopologyError("required group names are empty or duplicated")
    actual = tuple(sorted(str(name) for name in raw_memberships))
    if actual != required:
        missing = sorted(set(required).difference(actual))
        unexpected = sorted(set(actual).difference(required))
        raise AfesTopologyError(
            f"AFES group-key mismatch: missing={missing}, unexpected={unexpected}"
        )
    result: dict[str, tuple[int, ...]] = {}
    for name in required:
        raw_values = tuple(raw_memberships[name])
        values = tuple(
            _index(value, vertex_count=vertex_count, label=f"group {name}")
            for value in raw_values
        )
        if len(set(values)) != len(values):
            raise AfesTopologyError(f"group {name} repeats a vertex")
        if not values:
            raise AfesTopologyError(f"group {name} is empty")
        result[name] = tuple(sorted(values))
    return result


def geodesic_vertex_rings(
    vertex_count: int,
    edges: Iterable[Sequence[int]],
    seeds: Iterable[int],
    *,
    ring_count: int,
) -> tuple[tuple[int, ...], ...]:
    """Return exact edge-geodesic rings outside ``seeds``.

    Ring 1 contains previously unseen vertices one mesh edge from the AFES
    union.  Ring 2 is one additional edge away, and so on.  A requested empty
    ring is a hard failure because it cannot serve as transition evidence.
    """

    if type(ring_count) is not int or ring_count < 2:
        raise AfesTopologyError("at least two geodesic transition rings are required")
    normalized_edges = normalize_edges(vertex_count, edges)
    seed_values = tuple(
        _index(value, vertex_count=vertex_count, label="AFES seed") for value in seeds
    )
    if len(set(seed_values)) != len(seed_values) or not seed_values:
        raise AfesTopologyError("AFES seeds are empty or duplicated")
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in normalized_edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    visited = set(seed_values)
    frontier = set(seed_values)
    rings: list[tuple[int, ...]] = []
    for ring_number in range(1, ring_count + 1):
        following = {
            neighbor
            for current in frontier
            for neighbor in adjacency.get(current, set())
            if neighbor not in visited
        }
        if not following:
            raise AfesTopologyError(f"geodesic transition ring {ring_number} is empty")
        ring = tuple(sorted(following))
        rings.append(ring)
        visited.update(following)
        frontier = following
    return tuple(rings)


def analyze_afes_topology(
    *,
    vertex_count: int,
    edges: Iterable[Sequence[int]],
    faces: Iterable[Sequence[int]],
    memberships: Mapping[str, Iterable[int]],
    required_group_names: Sequence[str],
    transition_ring_count: int = 2,
) -> dict[str, object]:
    """Classify an existing foundation mesh without changing it."""

    normalized_edges = normalize_edges(vertex_count, edges)
    normalized_faces = normalize_faces(vertex_count, faces)
    groups = normalize_memberships(vertex_count, memberships, required_group_names)
    union = tuple(sorted({vertex for values in groups.values() for vertex in values}))
    union_set = set(union)
    incident_faces = tuple(
        index
        for index, face in enumerate(normalized_faces)
        if any(vertex in union_set for vertex in face)
    )
    internal_faces = tuple(
        index
        for index, face in enumerate(normalized_faces)
        if all(vertex in union_set for vertex in face)
    )
    connection_edges = tuple(
        edge
        for edge in normalized_edges
        if (edge[0] in union_set) != (edge[1] in union_set)
    )
    rings = geodesic_vertex_rings(
        vertex_count,
        normalized_edges,
        union,
        ring_count=transition_ring_count,
    )
    transition_union = tuple(sorted({vertex for ring in rings for vertex in ring}))
    if union_set.intersection(transition_union):
        raise AfesTopologyError("transition rings overlap the AFES union")
    group_records = {
        name: {
            "vertex_count": len(values),
            "vertex_indices": list(values),
            "vertex_index_sha256": canonical_index_sha256(values),
        }
        for name, values in groups.items()
    }
    ring_records = [
        {
            "ring_number": number,
            "vertex_count": len(values),
            "vertex_indices": list(values),
            "vertex_index_sha256": canonical_index_sha256(values),
        }
        for number, values in enumerate(rings, start=1)
    ]
    return {
        "whole_mesh": {
            "vertex_count": vertex_count,
            "edge_count": len(normalized_edges),
            "face_count": len(normalized_faces),
            "topology_sha256": canonical_json_sha256(
                {
                    "vertex_count": vertex_count,
                    "edges": [list(edge) for edge in normalized_edges],
                    "faces": [list(face) for face in normalized_faces],
                }
            ),
        },
        "groups": group_records,
        "afes_union": {
            "vertex_count": len(union),
            "vertex_indices": list(union),
            "vertex_index_sha256": canonical_index_sha256(union),
            "incident_face_count": len(incident_faces),
            "incident_face_indices": list(incident_faces),
            "incident_face_index_sha256": canonical_index_sha256(incident_faces),
            "internal_face_count": len(internal_faces),
            "internal_face_indices": list(internal_faces),
            "internal_face_index_sha256": canonical_index_sha256(internal_faces),
            "primary_connection_edge_count": len(connection_edges),
            "connection_edges": [list(edge) for edge in connection_edges],
            "connection_edge_sha256": canonical_json_sha256(
                [list(edge) for edge in connection_edges]
            ),
        },
        "transition_rings": {
            "ring_count": len(ring_records),
            "rings": ring_records,
            "combined_vertex_count": len(transition_union),
            "combined_vertex_indices": list(transition_union),
            "combined_vertex_index_sha256": canonical_index_sha256(transition_union),
            "disjoint_from_afes_union": True,
        },
    }

