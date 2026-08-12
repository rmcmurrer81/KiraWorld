#!/usr/bin/env python3
"""Pure topology helpers for the read-only Kira R23 donor preflight.

This module intentionally has no Blender dependency.  The Blender worker uses
it to derive deterministic face regions and the ordinary Python test suite can
exercise the topology rules without opening a Blend file.
"""

from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
from typing import Iterable, Mapping, Sequence


Face = Sequence[int]
Edge = tuple[int, int]


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def canonical_index_sha256(values: Iterable[int]) -> str:
    return canonical_json_sha256(sorted({int(value) for value in values}))


def face_edges(face: Face) -> tuple[Edge, ...]:
    values = tuple(int(value) for value in face)
    if len(values) < 3:
        raise ValueError("a face must contain at least three vertices")
    return tuple(
        tuple(sorted((values[index], values[(index + 1) % len(values)])))
        for index in range(len(values))
    )


def edge_face_map(faces: Sequence[Face]) -> dict[Edge, tuple[int, ...]]:
    mapping: dict[Edge, list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for edge in face_edges(face):
            mapping[edge].append(int(face_index))
    return {edge: tuple(indices) for edge, indices in mapping.items()}


def face_adjacency(faces: Sequence[Face]) -> dict[int, set[int]]:
    adjacency = {index: set() for index in range(len(faces))}
    for indices in edge_face_map(faces).values():
        for first in indices:
            for second in indices:
                if first != second:
                    adjacency[first].add(second)
    return adjacency


def face_components(
    selected: Iterable[int], adjacency: Mapping[int, set[int]]
) -> list[list[int]]:
    remaining = {int(value) for value in selected}
    components: list[list[int]] = []
    while remaining:
        seed = min(remaining)
        queue = deque([seed])
        component: set[int] = set()
        while queue:
            current = queue.popleft()
            if current not in remaining:
                continue
            remaining.remove(current)
            component.add(current)
            queue.extend(sorted(adjacency.get(current, set()).intersection(remaining)))
        components.append(sorted(component))
    return sorted(components, key=lambda values: (-len(values), values[0]))


def boundary_edges_for_region(
    faces: Sequence[Face], selected: Iterable[int]
) -> set[Edge]:
    counts: dict[Edge, int] = defaultdict(int)
    for face_index in {int(value) for value in selected}:
        for edge in face_edges(faces[face_index]):
            counts[edge] += 1
    return {edge for edge, count in counts.items() if count == 1}


def ordered_boundary_cycles(edges: Iterable[Edge]) -> list[list[int]]:
    remaining = {tuple(sorted(map(int, edge))) for edge in edges}
    if not remaining:
        return []
    neighbors: dict[int, set[int]] = defaultdict(set)
    for first, second in remaining:
        neighbors[first].add(second)
        neighbors[second].add(first)
    if any(len(values) != 2 for values in neighbors.values()):
        raise ValueError("boundary is not a union of closed degree-two cycles")
    cycles: list[list[int]] = []
    while remaining:
        seed_edge = min(remaining)
        start = min(seed_edge)
        candidates: list[list[int]] = []
        for following in sorted(neighbors[start]):
            cycle = [start, following]
            previous, current = start, following
            while True:
                choices = sorted(neighbors[current].difference({previous}))
                if len(choices) != 1:
                    raise ValueError("boundary traversal is ambiguous")
                nxt = choices[0]
                if nxt == start:
                    break
                if nxt in cycle:
                    raise ValueError("boundary cycle repeated before closure")
                cycle.append(nxt)
                previous, current = current, nxt
            candidates.append(cycle)
        cycle = min(candidates)
        cycle_edges = {
            tuple(sorted((cycle[index], cycle[(index + 1) % len(cycle)])))
            for index in range(len(cycle))
        }
        if not cycle_edges.issubset(remaining):
            raise ValueError("boundary cycles overlap")
        remaining.difference_update(cycle_edges)
        cycles.append(cycle)
    return sorted(cycles, key=lambda values: (len(values), values))


def topology_record(
    faces: Sequence[Face], selected: Iterable[int]
) -> dict[str, object]:
    region = sorted({int(value) for value in selected})
    adjacency = face_adjacency(faces)
    components = face_components(region, adjacency)
    vertices = {
        int(vertex) for face_index in region for vertex in faces[face_index]
    }
    edges = {
        edge for face_index in region for edge in face_edges(faces[face_index])
    }
    boundary = boundary_edges_for_region(faces, region)
    boundary_error = None
    try:
        cycles = ordered_boundary_cycles(boundary)
    except ValueError as exc:
        cycles = []
        boundary_error = str(exc)
    euler_characteristic = len(vertices) - len(edges) + len(region)
    disk = (
        len(components) == 1
        and len(cycles) == 1
        and boundary_error is None
        and euler_characteristic == 1
    )
    return {
        "face_count": len(region),
        "vertex_count": len(vertices),
        "edge_count": len(edges),
        "triangle_count": sum(len(faces[index]) == 3 for index in region),
        "quad_count": sum(len(faces[index]) == 4 for index in region),
        "ngon_count": sum(len(faces[index]) > 4 for index in region),
        "component_count": len(components),
        "component_face_counts": [len(component) for component in components],
        "boundary_edge_count": len(boundary),
        "boundary_cycle_count": len(cycles),
        "boundary_cycle_lengths": [len(cycle) for cycle in cycles],
        "boundary_error": boundary_error,
        "euler_characteristic": euler_characteristic,
        "is_one_disk": disk,
        "face_index_sha256": canonical_index_sha256(region),
        "vertex_index_sha256": canonical_index_sha256(vertices),
        "edge_sha256": canonical_json_sha256(sorted([list(edge) for edge in edges])),
        "boundary_sha256": canonical_json_sha256(
            [cycle for cycle in cycles]
            if cycles
            else sorted([list(edge) for edge in boundary])
        ),
    }


def expand_face_rings(
    selected: Iterable[int],
    adjacency: Mapping[int, set[int]],
    rings: int,
    *,
    allowed: Iterable[int] | None = None,
) -> set[int]:
    if rings < 0:
        raise ValueError("rings must be nonnegative")
    result = {int(value) for value in selected}
    permitted = set(adjacency) if allowed is None else {int(value) for value in allowed}
    if not result.issubset(permitted):
        raise ValueError("selected face escaped the permitted region")
    frontier = set(result)
    for _ in range(rings):
        following = {
            neighbor
            for face_index in frontier
            for neighbor in adjacency.get(face_index, set())
            if neighbor in permitted and neighbor not in result
        }
        result.update(following)
        frontier = following
    return result


def shortest_path_union(
    adjacency: Mapping[int, set[int]],
    sources: Iterable[int],
    targets: Iterable[int],
    *,
    allowed: Iterable[int] | None = None,
) -> tuple[set[int], dict[int, int]]:
    source_set = {int(value) for value in sources}
    target_set = {int(value) for value in targets}
    permitted = set(adjacency) if allowed is None else {int(value) for value in allowed}
    if not source_set or not source_set.issubset(permitted):
        raise ValueError("source faces are empty or outside the permitted region")
    if not target_set.issubset(permitted):
        raise ValueError("target face escaped the permitted region")
    predecessor: dict[int, int | None] = {value: None for value in source_set}
    distance = {value: 0 for value in source_set}
    queue = deque(sorted(source_set))
    pending = set(target_set).difference(source_set)
    while queue and pending:
        current = queue.popleft()
        for neighbor in sorted(adjacency.get(current, set())):
            if neighbor not in permitted or neighbor in predecessor:
                continue
            predecessor[neighbor] = current
            distance[neighbor] = distance[current] + 1
            queue.append(neighbor)
            pending.discard(neighbor)
    if pending:
        raise ValueError(f"unreachable target faces: {sorted(pending)[:8]}")
    result = set(source_set)
    for target in sorted(target_set):
        current: int | None = target
        while current is not None:
            result.add(current)
            current = predecessor[current]
    return result, {target: distance.get(target, 0) for target in target_set}


def all_face_indices(faces: Sequence[Face]) -> set[int]:
    return set(range(len(faces)))

