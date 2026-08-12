#!/usr/bin/env python3
"""Pure deterministic helpers for the bounded R23 localized patch repair.

This module deliberately has no Blender dependency.  It provides only the
small pieces of topology and interpolation math needed to prepare a later,
append-only pelvic patch repair without touching a body candidate.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import math
from numbers import Integral
from typing import Iterable, Mapping, Sequence


Vector = tuple[float, ...]
Face = tuple[int, ...]
Edge = tuple[int, int]


class PatchRepairError(ValueError):
    """Base class for deterministic patch-preparation failures."""


class OrientationConflictError(PatchRepairError):
    """Raised when face parity cannot satisfy every orientation constraint."""


@dataclass(frozen=True)
class OrientedDisk:
    """Result of orienting a connected manifold disk.

    ``face_flip_parity`` uses ``0`` for the input winding and ``1`` for the
    reversed winding.  Face ordering and each face's first vertex are retained
    so callers can bind the result deterministically to their source records.
    """

    faces: tuple[Face, ...]
    face_flip_parity: tuple[int, ...]
    flipped_face_indices: tuple[int, ...]
    boundary_edge_count: int


@dataclass(frozen=True)
class CubicCollarSample:
    """Point and parameter derivative on a cubic Hermite/Bezier collar."""

    point: Vector
    tangent: Vector
    bezier_control_points: tuple[Vector, Vector, Vector, Vector]


def minimum_variation_closed_cycle_choices(
    candidates_by_vertex: Sequence[Iterable[Sequence[float]]],
) -> tuple[Vector, ...]:
    """Choose exact loop values forming the least-discontinuous closed cycle.

    UV seams can give one mesh vertex several legitimate loop values.  This
    routine never averages or invents a value: it selects one exact supplied
    candidate at every cycle vertex while minimizing the summed squared jump
    around the closed cycle.  Sorting and full-path tie breaking make the
    result independent of mapping/set insertion order.
    """

    if not candidates_by_vertex:
        raise PatchRepairError("closed-cycle selection requires vertices")
    rows: list[tuple[Vector, ...]] = []
    dimensions: int | None = None
    for vertex_index, raw_candidates in enumerate(candidates_by_vertex):
        canonical: set[Vector] = set()
        for raw_candidate in raw_candidates:
            candidate = tuple(float(component) for component in raw_candidate)
            if not candidate:
                raise PatchRepairError(
                    f"cycle candidate at vertex {vertex_index} is empty"
                )
            if any(not math.isfinite(component) for component in candidate):
                raise PatchRepairError(
                    f"cycle candidate at vertex {vertex_index} is not finite"
                )
            if dimensions is None:
                dimensions = len(candidate)
            elif len(candidate) != dimensions:
                raise PatchRepairError("cycle candidate dimensions do not match")
            canonical.add(candidate)
        if not canonical:
            raise PatchRepairError(
                f"cycle vertex {vertex_index} has no exact candidates"
            )
        rows.append(tuple(sorted(canonical)))

    def squared_distance(first: Vector, second: Vector) -> float:
        return math.fsum(
            (first[axis] - second[axis]) ** 2 for axis in range(len(first))
        )

    def deterministic_minimum(
        options: Iterable[tuple[float, tuple[Vector, ...]]],
    ) -> tuple[float, tuple[Vector, ...]]:
        selected: tuple[float, tuple[Vector, ...]] | None = None
        for option in options:
            if selected is None:
                selected = option
                continue
            scale = max(1.0, abs(option[0]), abs(selected[0]))
            tolerance = 1.0e-14 * scale
            if option[0] < selected[0] - tolerance or (
                abs(option[0] - selected[0]) <= tolerance
                and option[1] < selected[1]
            ):
                selected = option
        assert selected is not None
        return selected

    best: tuple[float, tuple[Vector, ...]] | None = None
    for start in rows[0]:
        states: dict[Vector, tuple[float, tuple[Vector, ...]]] = {
            start: (0.0, (start,))
        }
        for row in rows[1:]:
            next_states: dict[Vector, tuple[float, tuple[Vector, ...]]] = {}
            for current in row:
                options = [
                    (
                        prior_cost + squared_distance(prior, current),
                        prior_path + (current,),
                    )
                    for prior, (prior_cost, prior_path) in states.items()
                ]
                next_states[current] = deterministic_minimum(options)
            states = next_states
        closed = [
            (
                cost + squared_distance(last, start),
                path,
            )
            for last, (cost, path) in states.items()
        ]
        candidate_best = deterministic_minimum(closed)
        if best is None:
            best = candidate_best
        else:
            best = deterministic_minimum((best, candidate_best))
    assert best is not None
    return best[1]


def _vertex_index(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{label} must be an integer vertex index")
    return int(value)


def _edge_key(a: int, b: int) -> Edge:
    return (a, b) if a < b else (b, a)


def _reverse_face_preserving_anchor(face: Face) -> Face:
    return (face[0], *reversed(face[1:]))


def orient_disk_faces_from_retained_boundary(
    faces: Sequence[Sequence[int]],
    retained_boundary_directed_edges: Iterable[Sequence[int]],
) -> OrientedDisk:
    """Orient an exact manifold disk from its retained-surface boundary.

    Each supplied directed edge is the direction used by the *retained* face
    beside that seam edge.  The returned patch face therefore traverses the
    same edge in the opposite direction.  The constraints must cover the
    patch's boundary exactly.  Interior face parity is propagated across the
    dual graph, and any boundary or propagation contradiction fails closed.
    """

    if not faces:
        raise PatchRepairError("an orientable disk requires at least one face")

    canonical_faces: list[Face] = []
    edge_incidence: dict[Edge, list[tuple[int, int, int]]] = defaultdict(list)
    vertices: set[int] = set()
    for face_index, raw_face in enumerate(faces):
        face = tuple(
            _vertex_index(value, f"face {face_index} vertex") for value in raw_face
        )
        if len(face) < 3:
            raise PatchRepairError(f"face {face_index} has fewer than three vertices")
        if len(set(face)) != len(face):
            raise PatchRepairError(f"face {face_index} repeats a vertex")
        canonical_faces.append(face)
        vertices.update(face)
        for corner, a in enumerate(face):
            b = face[(corner + 1) % len(face)]
            key = _edge_key(a, b)
            edge_incidence[key].append((face_index, a, b))
            if len(edge_incidence[key]) > 2:
                raise PatchRepairError(f"nonmanifold patch edge {key}")

    boundary_keys = {
        key for key, records in edge_incidence.items() if len(records) == 1
    }
    if not boundary_keys:
        raise PatchRepairError("patch has no boundary")

    retained_by_key: dict[Edge, Edge] = {}
    for constraint_index, raw_edge in enumerate(retained_boundary_directed_edges):
        edge = tuple(raw_edge)
        if len(edge) != 2:
            raise PatchRepairError(
                f"boundary constraint {constraint_index} is not a two-vertex edge"
            )
        a = _vertex_index(edge[0], f"boundary constraint {constraint_index}")
        b = _vertex_index(edge[1], f"boundary constraint {constraint_index}")
        if a == b:
            raise PatchRepairError(
                f"boundary constraint {constraint_index} is degenerate"
            )
        key = _edge_key(a, b)
        if key in retained_by_key:
            raise PatchRepairError(f"duplicate retained boundary constraint {key}")
        retained_by_key[key] = (a, b)

    supplied_keys = set(retained_by_key)
    if supplied_keys != boundary_keys:
        missing = sorted(boundary_keys.difference(supplied_keys))
        extra = sorted(supplied_keys.difference(boundary_keys))
        raise PatchRepairError(
            f"retained boundary constraints are not exact; missing={missing}, extra={extra}"
        )

    boundary_neighbors: dict[int, set[int]] = defaultdict(set)
    for a, b in boundary_keys:
        boundary_neighbors[a].add(b)
        boundary_neighbors[b].add(a)
    invalid_boundary_vertices = sorted(
        vertex
        for vertex, neighbors in boundary_neighbors.items()
        if len(neighbors) != 2
    )
    if invalid_boundary_vertices:
        raise PatchRepairError(
            "patch boundary is not one or more simple cycles at vertices "
            f"{invalid_boundary_vertices}"
        )

    boundary_start = min(boundary_neighbors)
    reached_boundary = {boundary_start}
    boundary_queue = deque([boundary_start])
    while boundary_queue:
        vertex = boundary_queue.popleft()
        for neighbor in sorted(boundary_neighbors[vertex]):
            if neighbor not in reached_boundary:
                reached_boundary.add(neighbor)
                boundary_queue.append(neighbor)
    if reached_boundary != set(boundary_neighbors):
        raise PatchRepairError("patch has more than one boundary cycle")

    euler_characteristic = (
        len(vertices) - len(edge_incidence) + len(canonical_faces)
    )
    if euler_characteristic != 1:
        raise PatchRepairError(
            "patch is not a topological disk; "
            f"Euler characteristic is {euler_characteristic}, expected 1"
        )

    # Adjacent faces must traverse their shared edge in opposite directions.
    # The parity relation is 1 when the input traversals agree, otherwise 0.
    dual_constraints: dict[int, list[tuple[int, int, Edge]]] = defaultdict(list)
    for key, records in edge_incidence.items():
        if len(records) != 2:
            continue
        first_face, first_a, first_b = records[0]
        second_face, second_a, second_b = records[1]
        same_direction = (first_a, first_b) == (second_a, second_b)
        relation = 1 if same_direction else 0
        dual_constraints[first_face].append((second_face, relation, key))
        dual_constraints[second_face].append((first_face, relation, key))

    pinned_parity: dict[int, int] = {}
    for key in sorted(boundary_keys):
        face_index, local_a, local_b = edge_incidence[key][0]
        retained_a, retained_b = retained_by_key[key]
        desired_patch_direction = (retained_b, retained_a)
        local_direction = (local_a, local_b)
        if local_direction == desired_patch_direction:
            required_parity = 0
        elif (local_b, local_a) == desired_patch_direction:
            required_parity = 1
        else:  # Defensive: the undirected-key equality should make this impossible.
            raise PatchRepairError(f"boundary direction does not match edge {key}")
        previous = pinned_parity.get(face_index)
        if previous is not None and previous != required_parity:
            raise OrientationConflictError(
                "retained boundary directions require contradictory parity on "
                f"face {face_index}"
            )
        pinned_parity[face_index] = required_parity

    parity = dict(pinned_parity)
    queue = deque(sorted(parity))
    while queue:
        face_index = queue.popleft()
        for neighbor, relation, edge in sorted(
            dual_constraints.get(face_index, ()), key=lambda row: (row[0], row[2])
        ):
            expected = parity[face_index] ^ relation
            if neighbor in parity:
                if parity[neighbor] != expected:
                    raise OrientationConflictError(
                        "face-orientation parity conflict across interior edge "
                        f"{edge} between faces {face_index} and {neighbor}"
                    )
                continue
            parity[neighbor] = expected
            queue.append(neighbor)

    if len(parity) != len(canonical_faces):
        missing_faces = sorted(set(range(len(canonical_faces))).difference(parity))
        raise PatchRepairError(
            f"patch face-dual graph is disconnected at faces {missing_faces}"
        )

    oriented = tuple(
        _reverse_face_preserving_anchor(face) if parity[index] else face
        for index, face in enumerate(canonical_faces)
    )

    # Verify the finished result independently of the propagation arithmetic.
    oriented_incidence: dict[Edge, list[tuple[int, int, int]]] = defaultdict(list)
    for face_index, face in enumerate(oriented):
        for corner, a in enumerate(face):
            b = face[(corner + 1) % len(face)]
            oriented_incidence[_edge_key(a, b)].append((face_index, a, b))
    for key, records in oriented_incidence.items():
        if len(records) == 2:
            if records[0][1:] != tuple(reversed(records[1][1:])):
                raise OrientationConflictError(
                    f"oriented faces do not oppose each other across {key}"
                )
            continue
        _face_index, patch_a, patch_b = records[0]
        retained_a, retained_b = retained_by_key[key]
        if (patch_a, patch_b) != (retained_b, retained_a):
            raise OrientationConflictError(
                f"oriented patch does not oppose retained boundary edge {key}"
            )

    flip_parity = tuple(parity[index] for index in range(len(canonical_faces)))
    return OrientedDisk(
        faces=oriented,
        face_flip_parity=flip_parity,
        flipped_face_indices=tuple(
            index for index, value in enumerate(flip_parity) if value
        ),
        boundary_edge_count=len(boundary_keys),
    )


def _canonical_adjacency(
    adjacency: Mapping[int, Iterable[int]],
) -> dict[int, tuple[int, ...]]:
    canonical: dict[int, tuple[int, ...]] = {}
    for raw_node, raw_neighbors in adjacency.items():
        node = _vertex_index(raw_node, "adjacency node")
        if node in canonical:
            raise PatchRepairError(f"duplicate canonical adjacency node {node}")
        neighbors = {
            _vertex_index(value, f"neighbor of node {node}")
            for value in raw_neighbors
        }
        if node in neighbors:
            raise PatchRepairError(f"adjacency contains self-edge at node {node}")
        canonical[node] = tuple(sorted(neighbors))
    if not canonical:
        raise PatchRepairError("harmonic interpolation requires a nonempty graph")
    nodes = set(canonical)
    for node, neighbors in canonical.items():
        for neighbor in neighbors:
            if neighbor not in nodes:
                raise PatchRepairError(
                    f"adjacency references unknown node {neighbor} from {node}"
                )
            if node not in canonical[neighbor]:
                raise PatchRepairError(
                    f"adjacency edge {(node, neighbor)} is not symmetric"
                )
    return canonical


def _conjugate_gradient_component(
    adjacency: Mapping[int, tuple[int, ...]],
    interior: Sequence[int],
    boundary: Mapping[int, Vector],
    component: int,
    tolerance: float,
    maximum_iterations: int,
) -> list[float]:
    interior_index = {node: index for index, node in enumerate(interior)}
    diagonal = [float(len(adjacency[node])) for node in interior]
    right_hand_side = [
        math.fsum(
            boundary[neighbor][component]
            for neighbor in adjacency[node]
            if neighbor in boundary
        )
        for node in interior
    ]

    def matrix_vector(values: Sequence[float]) -> list[float]:
        return [
            diagonal[row] * values[row]
            - math.fsum(
                values[interior_index[neighbor]]
                for neighbor in adjacency[node]
                if neighbor in interior_index
            )
            for row, node in enumerate(interior)
        ]

    solution = [0.0] * len(interior)
    residual = list(right_hand_side)
    scale = max(
        1.0,
        math.sqrt(math.fsum(value * value for value in right_hand_side)),
    )
    target = tolerance * scale
    residual_norm = math.sqrt(math.fsum(value * value for value in residual))
    if residual_norm <= target:
        return solution

    preconditioned = [
        residual[index] / diagonal[index] for index in range(len(interior))
    ]
    direction = list(preconditioned)
    residual_dot_preconditioned = math.fsum(
        residual[index] * preconditioned[index]
        for index in range(len(interior))
    )
    for _iteration in range(maximum_iterations):
        matrix_direction = matrix_vector(direction)
        denominator = math.fsum(
            direction[index] * matrix_direction[index]
            for index in range(len(interior))
        )
        if denominator <= 0.0 or not math.isfinite(denominator):
            raise PatchRepairError("harmonic solver lost positive definiteness")
        alpha = residual_dot_preconditioned / denominator
        solution = [
            solution[index] + alpha * direction[index]
            for index in range(len(interior))
        ]
        residual = [
            residual[index] - alpha * matrix_direction[index]
            for index in range(len(interior))
        ]
        residual_norm = math.sqrt(math.fsum(value * value for value in residual))
        if residual_norm <= target:
            return solution
        next_preconditioned = [
            residual[index] / diagonal[index] for index in range(len(interior))
        ]
        next_dot = math.fsum(
            residual[index] * next_preconditioned[index]
            for index in range(len(interior))
        )
        if residual_dot_preconditioned <= 0.0:
            raise PatchRepairError("harmonic solver residual became invalid")
        beta = next_dot / residual_dot_preconditioned
        direction = [
            next_preconditioned[index] + beta * direction[index]
            for index in range(len(interior))
        ]
        preconditioned = next_preconditioned
        residual_dot_preconditioned = next_dot

    raise PatchRepairError(
        "harmonic interpolation did not converge within "
        f"{maximum_iterations} iterations; residual={residual_norm:.17g}, "
        f"target={target:.17g}"
    )


def harmonic_interpolate_boundary_field(
    adjacency: Mapping[int, Iterable[int]],
    boundary_values: Mapping[int, Sequence[float]],
    *,
    tolerance: float = 1.0e-12,
    maximum_iterations: int | None = None,
) -> dict[int, Vector]:
    """Interpolate a multi-component boundary field over an arbitrary graph.

    The uniform graph Laplacian is solved on interior nodes with diagonally
    preconditioned conjugate gradients.  Boundary tuples are copied exactly
    into the result and never participate as mutable solver unknowns.  Every
    connected component must contain at least one boundary node.
    """

    graph = _canonical_adjacency(adjacency)
    if not boundary_values:
        raise PatchRepairError("harmonic interpolation requires boundary values")
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise PatchRepairError("harmonic tolerance must be finite and positive")

    boundary: dict[int, Vector] = {}
    dimensions: int | None = None
    for raw_node, raw_value in boundary_values.items():
        node = _vertex_index(raw_node, "boundary-value node")
        if node not in graph:
            raise PatchRepairError(f"boundary value references unknown node {node}")
        value = tuple(float(component) for component in raw_value)
        if not value:
            raise PatchRepairError("boundary field must have at least one component")
        if any(not math.isfinite(component) for component in value):
            raise PatchRepairError(f"boundary value at node {node} is not finite")
        if dimensions is None:
            dimensions = len(value)
        elif len(value) != dimensions:
            raise PatchRepairError("boundary field component counts do not match")
        boundary[node] = value
    assert dimensions is not None

    reached = set(boundary)
    queue = deque(sorted(boundary))
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    if reached != set(graph):
        missing = sorted(set(graph).difference(reached))
        raise PatchRepairError(
            f"graph component has no boundary constraint at nodes {missing}"
        )

    interior = tuple(sorted(set(graph).difference(boundary)))
    if not interior:
        return {node: boundary[node] for node in sorted(graph)}
    if any(len(graph[node]) == 0 for node in interior):
        raise PatchRepairError("interior harmonic node has zero degree")
    iteration_limit = (
        max(64, 8 * len(interior))
        if maximum_iterations is None
        else int(maximum_iterations)
    )
    if iteration_limit < 1:
        raise PatchRepairError("maximum_iterations must be positive")

    component_solutions = [
        _conjugate_gradient_component(
            graph,
            interior,
            boundary,
            component,
            tolerance,
            iteration_limit,
        )
        for component in range(dimensions)
    ]
    interior_index = {node: index for index, node in enumerate(interior)}
    return {
        node: (
            boundary[node]
            if node in boundary
            else tuple(
                component_solutions[component][interior_index[node]]
                for component in range(dimensions)
            )
        )
        for node in sorted(graph)
    }


def project_top_four_normalized_weights(
    weights: Mapping[str, float],
    *,
    negative_tolerance: float = 1.0e-12,
) -> dict[str, float]:
    """Keep the four strongest native weights and normalize deterministically.

    Equal values are ordered by ascending group name, independent of mapping
    insertion order.  Tiny negative solver noise may be clipped, but a
    materially negative or non-finite influence fails closed.
    """

    if not math.isfinite(negative_tolerance) or negative_tolerance < 0.0:
        raise PatchRepairError("negative_tolerance must be finite and nonnegative")
    positive: list[tuple[str, float]] = []
    for raw_name, raw_value in weights.items():
        if not isinstance(raw_name, str) or not raw_name:
            raise PatchRepairError("weight group names must be nonempty strings")
        value = float(raw_value)
        if not math.isfinite(value):
            raise PatchRepairError(f"weight for {raw_name!r} is not finite")
        if value < -negative_tolerance:
            raise PatchRepairError(f"weight for {raw_name!r} is negative: {value}")
        if value > 0.0:
            positive.append((raw_name, value))
    if not positive:
        raise PatchRepairError("weight projection has no positive influences")

    selected = sorted(positive, key=lambda row: (-row[1], row[0]))[:4]
    total = math.fsum(value for _name, value in selected)
    if total <= 0.0 or not math.isfinite(total):
        raise PatchRepairError("selected weight total is not positive and finite")
    normalized = {name: value / total for name, value in selected}
    correction = 1.0 - math.fsum(normalized.values())
    first_name = selected[0][0]
    normalized[first_name] += correction
    if normalized[first_name] <= 0.0:
        raise PatchRepairError("rounding correction invalidated the strongest weight")
    return normalized


def cubic_hermite_collar_sample(
    outer_endpoint: Sequence[float],
    source_inward_tangent: Sequence[float],
    donor_endpoint: Sequence[float],
    donor_inward_tangent: Sequence[float],
    fraction: float,
) -> CubicCollarSample:
    """Sample a tangent-preserving cubic collar from source to donor.

    Both tangent arguments are derivatives with respect to ``fraction``.  The
    source tangent points from the retained outer endpoint into the repair;
    the donor tangent points onward from the donor boundary into its interior.
    The equivalent Bezier controls are returned for deterministic inspection.
    """

    vectors = tuple(
        tuple(float(component) for component in vector)
        for vector in (
            outer_endpoint,
            source_inward_tangent,
            donor_endpoint,
            donor_inward_tangent,
        )
    )
    dimensions = len(vectors[0])
    if dimensions == 0 or any(len(vector) != dimensions for vector in vectors):
        raise PatchRepairError("collar vectors must have one matching dimension")
    if any(not math.isfinite(component) for vector in vectors for component in vector):
        raise PatchRepairError("collar vectors must be finite")
    parameter = float(fraction)
    if not math.isfinite(parameter) or not 0.0 <= parameter <= 1.0:
        raise PatchRepairError("collar fraction must be finite and inside [0, 1]")

    outer, source_tangent, donor, donor_tangent = vectors
    control_1 = tuple(
        outer[axis] + source_tangent[axis] / 3.0
        for axis in range(dimensions)
    )
    control_2 = tuple(
        donor[axis] - donor_tangent[axis] / 3.0
        for axis in range(dimensions)
    )
    controls = (outer, control_1, control_2, donor)

    if parameter == 0.0:
        return CubicCollarSample(outer, source_tangent, controls)
    if parameter == 1.0:
        return CubicCollarSample(donor, donor_tangent, controls)

    one_minus = 1.0 - parameter
    point = tuple(
        one_minus**3 * outer[axis]
        + 3.0 * one_minus**2 * parameter * control_1[axis]
        + 3.0 * one_minus * parameter**2 * control_2[axis]
        + parameter**3 * donor[axis]
        for axis in range(dimensions)
    )
    tangent = tuple(
        3.0
        * (
            one_minus**2 * (control_1[axis] - outer[axis])
            + 2.0
            * one_minus
            * parameter
            * (control_2[axis] - control_1[axis])
            + parameter**2 * (donor[axis] - control_2[axis])
        )
        for axis in range(dimensions)
    )
    return CubicCollarSample(point, tangent, controls)
