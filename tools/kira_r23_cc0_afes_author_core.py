#!/usr/bin/env python3
"""Pure deterministic helpers for the bounded R23 CC0-AFES author."""

from __future__ import annotations

import math
from collections import deque
from typing import Iterable, Mapping, Sequence


def cycle_parameters(points: Sequence[Sequence[float]]) -> list[float]:
    if len(points) < 3:
        raise ValueError("cycle requires at least three points")
    lengths = [0.0]
    total = 0.0
    for index in range(len(points)):
        a = points[index]
        b = points[(index + 1) % len(points)]
        total += math.dist(a, b)
        lengths.append(total)
    if total <= 1.0e-12:
        raise ValueError("cycle has zero perimeter")
    return [value / total for value in lengths[:-1]]


def sample_cycle(
    points: Sequence[Sequence[float]],
    parameters: Sequence[float],
    fraction: float,
) -> tuple[float, ...]:
    if len(points) != len(parameters):
        raise ValueError("cycle point/parameter count mismatch")
    value = float(fraction) % 1.0
    count = len(points)
    for index in range(count):
        start = parameters[index]
        end = parameters[index + 1] if index + 1 < count else 1.0
        if value <= end or index == count - 1:
            span = max(end - start, 1.0e-12)
            weight = (value - start) / span
            a = points[index]
            b = points[(index + 1) % count]
            return tuple(
                float(a[axis]) * (1.0 - weight) + float(b[axis]) * weight
                for axis in range(len(a))
            )
    raise AssertionError("cycle sample fell through")


def align_cycle(
    reference_points: Sequence[Sequence[float]],
    candidate_indices: Sequence[int],
    candidate_points_by_index: dict[int, Sequence[float]],
) -> tuple[list[int], dict[str, float | int | bool]]:
    reference_parameters = cycle_parameters(reference_points)
    best = None
    for reversed_order in (False, True):
        order = list(candidate_indices)
        if reversed_order:
            order = list(reversed(order))
        for offset in range(len(order)):
            rotated = order[offset:] + order[:offset]
            points = [candidate_points_by_index[index] for index in rotated]
            parameters = cycle_parameters(points)
            score = 0.0
            for reference, fraction in zip(reference_points, reference_parameters):
                sample = sample_cycle(points, parameters, fraction)
                score += math.dist(reference, sample) ** 2
            row = (score, reversed_order, offset, rotated, parameters)
            if best is None or row[:3] < best[:3]:
                best = row
    if best is None:
        raise ValueError("cycle alignment failed")
    score, reversed_order, offset, order, parameters = best
    return list(order), {
        "reversed": bool(reversed_order),
        "cyclic_offset": int(offset),
        "mean_squared_distance": float(score / len(reference_points)),
        "candidate_parameter_count": len(parameters),
    }


def zipper_bridge_parameterized(
    lower: Sequence[int],
    lower_parameters: Sequence[float],
    upper: Sequence[int],
    upper_parameters: Sequence[float],
) -> list[tuple[int, int, int]]:
    if len(lower) != len(lower_parameters) or len(upper) != len(upper_parameters):
        raise ValueError("zipper cycle/parameter count mismatch")
    n, m = len(lower), len(upper)
    faces: list[tuple[int, int, int]] = []
    i = j = 0
    while i < n or j < m:
        a0 = int(lower[i % n])
        b0 = int(upper[j % m])
        next_a = lower_parameters[i + 1] if i + 1 < n else (1.0 if i < n else math.inf)
        next_b = upper_parameters[j + 1] if j + 1 < m else (1.0 if j < m else math.inf)
        if abs(next_a - next_b) <= 1.0e-12:
            a1 = int(lower[(i + 1) % n])
            b1 = int(upper[(j + 1) % m])
            faces.extend(((a0, a1, b0), (a1, b1, b0)))
            i += 1
            j += 1
        elif next_a < next_b:
            a1 = int(lower[(i + 1) % n])
            faces.append((a0, a1, b0))
            i += 1
        else:
            b1 = int(upper[(j + 1) % m])
            faces.append((a0, b1, b0))
            j += 1
    if len(faces) != n + m:
        raise ValueError("unequal-cycle zipper face count drifted")
    return faces


def matching_cycle_triangles(
    outer: Sequence[int], inner: Sequence[int]
) -> list[tuple[int, int, int]]:
    if len(outer) != len(inner) or len(outer) < 3:
        raise ValueError("matching cycles must have equal nontrivial counts")
    faces = []
    for index in range(len(outer)):
        next_index = (index + 1) % len(outer)
        faces.extend(
            (
                (int(outer[index]), int(outer[next_index]), int(inner[index])),
                (
                    int(outer[next_index]),
                    int(inner[next_index]),
                    int(inner[index]),
                ),
            )
        )
    return faces


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def collar_point(
    outer: Sequence[float], inner: Sequence[float], fraction: float
) -> tuple[float, ...]:
    weight = smoothstep(fraction)
    return tuple(
        float(a) * (1.0 - weight) + float(b) * weight
        for a, b in zip(outer, inner)
    )


def barycentric_weights(
    point: Sequence[float],
    a: Sequence[float],
    b: Sequence[float],
    c: Sequence[float],
) -> tuple[float, float, float]:
    v0 = tuple(float(b[i]) - float(a[i]) for i in range(3))
    v1 = tuple(float(c[i]) - float(a[i]) for i in range(3))
    v2 = tuple(float(point[i]) - float(a[i]) for i in range(3))
    dot00 = sum(value * value for value in v0)
    dot01 = sum(v0[i] * v1[i] for i in range(3))
    dot11 = sum(value * value for value in v1)
    dot20 = sum(v2[i] * v0[i] for i in range(3))
    dot21 = sum(v2[i] * v1[i] for i in range(3))
    denominator = dot00 * dot11 - dot01 * dot01
    if abs(denominator) <= 1.0e-18:
        return (1.0, 0.0, 0.0)
    v = (dot11 * dot20 - dot01 * dot21) / denominator
    w = (dot00 * dot21 - dot01 * dot20) / denominator
    u = 1.0 - v - w
    values = [max(0.0, u), max(0.0, v), max(0.0, w)]
    total = sum(values)
    if total <= 1.0e-18:
        return (1.0, 0.0, 0.0)
    return tuple(value / total for value in values)


def top_four_normalized(weights: dict[str, float]) -> dict[str, float]:
    positive = sorted(
        ((float(value), str(name)) for name, value in weights.items() if value > 0.0),
        reverse=True,
    )[:4]
    total = sum(value for value, _name in positive)
    if total <= 1.0e-18:
        raise ValueError("new vertex has no positive native weight")
    return {name: value / total for value, name in positive}


def clinical_longitudinal_order_checks(
    centroids: Mapping[str, float], minimum_gap: float = 0.0
) -> dict[str, bool]:
    """Evaluate the bounded external landmark order in the authored frame.

    Positive chart-longitudinal values are anterior/superior in the sealed
    foundation frame.  These checks do not claim physiology; they only prevent
    a structurally reversed external chart from reaching a candidate save.
    """

    required = {
        "mons_anterior_to_paired_majora": (
            "AFES_LANDMARK__mons_pubis",
            "AFES_LANDMARK__labia_majora",
        ),
        "hood_anterior_to_urethral_opening": (
            "AFES_LANDMARK__clitoral_hood",
            "AFES_LANDMARK__urethral_opening",
        ),
        "clitoris_anterior_to_urethral_opening": (
            "AFES_LANDMARK__clitoris",
            "AFES_LANDMARK__urethral_opening",
        ),
        "urethral_opening_anterior_to_vaginal_opening": (
            "AFES_LANDMARK__urethral_opening",
            "AFES_LANDMARK__vaginal_opening",
        ),
        "vaginal_opening_anterior_to_fourchette": (
            "AFES_LANDMARK__vaginal_opening",
            "AFES_LANDMARK__fourchette",
        ),
        "vaginal_opening_anterior_to_perineum": (
            "AFES_LANDMARK__vaginal_opening",
            "AFES_LANDMARK__perineal_path",
        ),
        "anal_recess_posterior_and_separate_from_vaginal_opening": (
            "AFES_LANDMARK__vaginal_opening",
            "AFES_LANDMARK__perineal_path__anal_recess",
        ),
    }
    gap = max(0.0, float(minimum_gap))
    checks: dict[str, bool] = {}
    for relation, (anterior, posterior) in required.items():
        if anterior not in centroids or posterior not in centroids:
            checks[relation] = False
            continue
        checks[relation] = (
            float(centroids[anterior]) - float(centroids[posterior]) > gap
        )
    return checks


def graph_distances(
    adjacency: Mapping[int, Iterable[int]], sources: Iterable[int]
) -> dict[int, int]:
    """Return deterministic unweighted shortest-path distances."""

    nodes = {int(node) for node in adjacency}
    queue = deque(sorted({int(node) for node in sources if int(node) in nodes}))
    distances = {node: 0 for node in queue}
    while queue:
        node = queue.popleft()
        for neighbor in sorted(int(value) for value in adjacency[node]):
            if neighbor not in nodes or neighbor in distances:
                continue
            distances[neighbor] = distances[node] + 1
            queue.append(neighbor)
    return distances


def feathered_membership_influence(
    adjacency: Mapping[int, Iterable[int]],
    members: Iterable[int],
    feather_rings: int,
) -> dict[int, float]:
    """Build a continuous graph-distance field across a membership boundary.

    The inside and immediately adjacent outside boundary both evaluate to 0.5.
    Influence approaches 1.0 toward a sufficiently deep topological core and
    fades to 0.0 across the requested number of outside rings. Small features
    remain softly expressed instead of forcing a one-edge center spike.
    """

    nodes = {int(node) for node in adjacency}
    selected = {int(node) for node in members if int(node) in nodes}
    rings = int(feather_rings)
    if rings < 1:
        raise ValueError("feather_rings must be at least one")
    if not selected:
        return {node: 0.0 for node in sorted(nodes)}
    outside = nodes.difference(selected)
    distance_to_selected = graph_distances(adjacency, selected)
    distance_to_outside = graph_distances(adjacency, outside) if outside else {}
    result: dict[int, float] = {}
    for node in sorted(nodes):
        if node in selected:
            if not outside:
                result[node] = 1.0
                continue
            distance = max(1, distance_to_outside.get(node, rings + 1))
            fraction = min(1.0, max(0.0, (distance - 1) / rings))
            result[node] = 0.5 + 0.5 * smoothstep(fraction)
            continue
        distance = distance_to_selected.get(node)
        if distance is None or distance > rings + 1:
            result[node] = 0.0
            continue
        fraction = min(1.0, max(0.0, (distance - 1) / rings))
        result[node] = 0.5 * (1.0 - smoothstep(fraction))
    return result


def feathered_influences(
    adjacency: Mapping[int, Iterable[int]],
    memberships: Mapping[str, Iterable[int]],
    priority_order: Sequence[str],
    feather_rings: int,
) -> dict[str, dict[int, float]]:
    return {
        str(name): feathered_membership_influence(
            adjacency, memberships.get(str(name), ()), feather_rings
        )
        for name in priority_order
    }


def blend_feathered_scalar_field(
    nodes: Iterable[int],
    influences: Mapping[str, Mapping[int, float]],
    priority_order: Sequence[str],
    targets: Mapping[str, float],
    base: float = 0.0,
) -> dict[int, float]:
    """Blend broad-to-specific so the first priority wins smoothly."""

    field = {int(node): float(base) for node in nodes}
    for name in reversed([str(value) for value in priority_order]):
        target = float(targets.get(name, base))
        influence = influences[name]
        for node in field:
            weight = min(1.0, max(0.0, float(influence.get(node, 0.0))))
            field[node] = field[node] * (1.0 - weight) + target * weight
    return field


def blend_feathered_vector_field(
    nodes: Iterable[int],
    influences: Mapping[str, Mapping[int, float]],
    priority_order: Sequence[str],
    targets: Mapping[str, Sequence[float]],
    base: Sequence[float],
) -> dict[int, tuple[float, ...]]:
    ordered_nodes = [int(node) for node in nodes]
    dimensions = len(base)
    components = []
    for axis in range(dimensions):
        components.append(
            blend_feathered_scalar_field(
                ordered_nodes,
                influences,
                priority_order,
                {
                    name: float(value[axis])
                    for name, value in targets.items()
                },
                float(base[axis]),
            )
        )
    return {
        node: tuple(component[node] for component in components)
        for node in ordered_nodes
    }


def maximum_adjacent_delta(
    adjacency: Mapping[int, Iterable[int]],
    field: Mapping[int, float | Sequence[float]],
) -> float:
    maximum = 0.0
    for node in sorted(int(value) for value in adjacency):
        for neighbor in adjacency[node]:
            neighbor = int(neighbor)
            if neighbor <= node or neighbor not in field:
                continue
            a = field[node]
            b = field[neighbor]
            if isinstance(a, (tuple, list)):
                delta = math.dist(a, b)  # type: ignore[arg-type]
            else:
                delta = abs(float(a) - float(b))
            maximum = max(maximum, float(delta))
    return maximum
