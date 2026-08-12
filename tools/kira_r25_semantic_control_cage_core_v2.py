#!/usr/bin/env python3
"""Pure fail-closed kernels for R25 semantic control-cage Attempt 02.

This module is deliberately self-contained.  It imports no project module and
does not open Blender, a Blend, a path, or a pipe.  A future inert Blender
wrapper must load these exact source bytes into a fresh private namespace.

The 432 selected points are *control anchors*.  They are not represented as a
direct correspondence for every source vertex.  Acceptance instead requires
that every permissible source vertex belongs to the single same-region
component and is within a configured edge-geodesic radius of an anchor.
"""

from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import heapq
import json
import math
import re
import struct
from typing import Any, Iterable, Mapping, Sequence


FIXED_SCALE = 1_000_000_000
UINT32_MAX = 2**32 - 1
AFES_BLOB_CODEC = "uint32_big_endian_v1"
AFES_INDEX_SEMANTIC = "sorted_unique_index_json_sha256_v1"
AFES_EDGE_SEMANTIC = "sorted_unique_undirected_edge_pair_json_sha256_v1"
MAPPING_RECORD = struct.Struct("<IBIIIIIIIIIi")
MAPPING_CODEC = (
    "kira_r25_semantic_control_anchor_map_le_v2:"
    "u32_foundation_vertex,u8_region_id,u32_face,u32_triangle,"
    "u32_tri_a,u32_tri_b,u32_tri_c,u32_bary_a,u32_bary_b,u32_bary_c,"
    "u32_distance_um,i32_normal_dot_1e9"
)

REGIONS = (
    "face", "head", "neck", "torso",
    "upper_arm.L", "lower_arm.L", "hand.L",
    "upper_arm.R", "lower_arm.R", "hand.R",
    "thigh.L", "shin.L", "foot.L",
    "thigh.R", "shin.R", "foot.R",
)

SIDE_PAIRS = (
    ("upper_arm.L", "upper_arm.R"),
    ("lower_arm.L", "lower_arm.R"),
    ("hand.L", "hand.R"),
    ("thigh.L", "thigh.R"),
    ("shin.L", "shin.R"),
    ("foot.L", "foot.R"),
)


class SemanticControlCageError(ValueError):
    """A required exact semantic, topology, or geometric gate failed."""


@dataclass(frozen=True)
class Triangle:
    face_index: int
    triangle_index: int
    vertex_indices: tuple[int, int, int]


@dataclass(frozen=True)
class Similarity:
    scale: float
    rotation: tuple[tuple[float, float, float], ...]
    translation: tuple[float, float, float]


@dataclass(frozen=True)
class AlignmentResult:
    similarity: Similarity
    source_rank_ratio: float
    target_rank_ratio: float
    covariance_determinant: float
    rotation_determinant: float
    orthonormal_residual: float
    normalized_rms_residual: float


@dataclass(frozen=True)
class CoverageResult:
    anchors: dict[str, tuple[int, ...]]
    rows: tuple[dict[str, int | str], ...]


def _official_group_map() -> dict[str, str]:
    """Return the complete exact 139-name MakeHuman default-weight allowlist."""

    result: dict[str, str] = {}

    def add(region: str, names: Iterable[str]) -> None:
        for name in names:
            if name in result:
                raise RuntimeError(f"duplicate official MakeHuman group: {name}")
            result[name] = region

    add("torso", (
        "breast.L", "breast.R", "clavicle.L", "clavicle.R",
        "pelvis.L", "pelvis.R", "root", "spine01", "spine02",
        "spine03", "spine04", "spine05",
    ))
    add("face", (
        "eye.L", "eye.R", "jaw", "levator05.L", "levator05.R",
        "levator06.L", "levator06.R", "oculi01.L", "oculi01.R",
        "orbicularis03.L", "orbicularis03.R", "orbicularis04.L",
        "orbicularis04.R", "oris01", "oris03.L", "oris03.R",
        "oris05", "oris07.L", "oris07.R", "risorius03.L",
        "risorius03.R", "special04", "special05.L", "special05.R",
        "tongue00", "tongue01", "tongue02", "tongue03", "tongue04",
        "tongue05.L", "tongue05.R", "tongue06.L", "tongue06.R",
        "tongue07.L", "tongue07.R",
    ))
    add("head", ("head",))
    add("neck", ("neck01", "neck02", "neck03"))
    for side in ("L", "R"):
        add(f"upper_arm.{side}", (
            f"shoulder01.{side}", f"upperarm01.{side}", f"upperarm02.{side}",
        ))
        add(f"lower_arm.{side}", (f"lowerarm01.{side}", f"lowerarm02.{side}"))
        hand = [f"wrist.{side}"]
        hand.extend(f"metacarpal{digit}.{side}" for digit in range(1, 5))
        hand.extend(
            f"finger{digit}-{joint}.{side}"
            for digit in range(1, 6) for joint in range(1, 4)
        )
        add(f"hand.{side}", hand)
        add(f"thigh.{side}", (f"upperleg01.{side}", f"upperleg02.{side}"))
        add(f"shin.{side}", (f"lowerleg01.{side}", f"lowerleg02.{side}"))
        foot = [f"foot.{side}"]
        foot.extend(
            f"toe{digit}-{joint}.{side}"
            for digit in range(1, 6)
            for joint in range(1, 4 if digit > 1 else 3)
        )
        add(f"foot.{side}", foot)
    if len(result) != 139:
        raise RuntimeError(f"official MakeHuman group allowlist count drifted: {len(result)}")
    return result


OFFICIAL_MAKEHUMAN_GROUP_TO_REGION = _official_group_map()
OFFICIAL_MAKEHUMAN_GROUP_NAMES = tuple(sorted(OFFICIAL_MAKEHUMAN_GROUP_TO_REGION))


def canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SemanticControlCageError("canonical_json_rejected") from exc


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def index_sha256(values: Iterable[int]) -> str:
    return canonical_sha256(sorted({int(value) for value in values}))


def _hex64(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SemanticControlCageError(f"{label}_must_be_64_lowercase_hex")
    return value


def _integer(value: object, label: str, minimum: int | None = None, maximum: int | None = None) -> int:
    if type(value) is not int:
        raise SemanticControlCageError(f"{label}_must_be_integer")
    result = int(value)
    if minimum is not None and result < minimum:
        raise SemanticControlCageError(f"{label}_below_minimum")
    if maximum is not None and result > maximum:
        raise SemanticControlCageError(f"{label}_above_maximum")
    return result


def semantic_region_for_exact_group(name: object) -> str:
    if not isinstance(name, str) or name not in OFFICIAL_MAKEHUMAN_GROUP_TO_REGION:
        raise SemanticControlCageError(f"nonofficial_makehuman_group:{name}")
    return OFFICIAL_MAKEHUMAN_GROUP_TO_REGION[name]


def classify_weighted_vertices(
    assignments: Sequence[Sequence[tuple[str, float]]],
    minimum_recognized_weight: float = 0.50,
) -> list[str]:
    """Classify only exact official names; every positive unknown name fails."""

    if not math.isfinite(minimum_recognized_weight) or not (0.0 < minimum_recognized_weight <= 1.0):
        raise SemanticControlCageError("minimum_recognized_weight_invalid")
    result: list[str] = []
    for vertex_index, row in enumerate(assignments):
        totals: dict[str, float] = {}
        for name, weight in row:
            if not math.isfinite(weight) or weight < 0.0:
                raise SemanticControlCageError(f"weight_invalid:{vertex_index}")
            if weight == 0.0:
                continue
            region = semantic_region_for_exact_group(name)
            totals[region] = totals.get(region, 0.0) + weight
        if not totals or sum(totals.values()) + 1e-12 < minimum_recognized_weight:
            raise SemanticControlCageError(f"vertex_semantic_weight_unavailable:{vertex_index}")
        ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        if len(ordered) > 1 and abs(ordered[0][1] - ordered[1][1]) <= 1e-12:
            raise SemanticControlCageError(f"vertex_semantic_weight_tie:{vertex_index}")
        result.append(ordered[0][0])
    return result


def _vadd(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vsub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vmul(a: Sequence[float], scale: float) -> tuple[float, float, float]:
    return (a[0] * scale, a[1] * scale, a[2] * scale)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Sequence[float]) -> float:
    return math.sqrt(max(0.0, _dot(a, a)))


def _normalize(a: Sequence[float]) -> tuple[float, float, float]:
    length = _norm(a)
    if length <= 1e-15:
        raise SemanticControlCageError("zero_length_vector")
    return (a[0] / length, a[1] / length, a[2] / length)


def _centroid(points: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    if not points:
        raise SemanticControlCageError("empty_centroid")
    if any(len(point) != 3 or any(not math.isfinite(float(v)) for v in point) for point in points):
        raise SemanticControlCageError("nonfinite_or_non3d_point")
    inverse = 1.0 / len(points)
    return tuple(sum(float(point[axis]) for point in points) * inverse for axis in range(3))  # type: ignore[return-value]


def _det3(matrix: Sequence[Sequence[float]]) -> float:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _symmetric_eigenvalues3(matrix: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    a = [list(row) for row in matrix]
    for _ in range(64):
        magnitude, p, q = max(
            (abs(a[i][j]), i, j) for i in range(3) for j in range(i + 1, 3)
        )
        if magnitude <= 1e-15:
            break
        angle = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
        cosine, sine = math.cos(angle), math.sin(angle)
        for k in range(3):
            if k not in (p, q):
                apk, aqk = a[p][k], a[q][k]
                a[p][k] = a[k][p] = cosine * apk - sine * aqk
                a[q][k] = a[k][q] = sine * apk + cosine * aqk
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = cosine * cosine * app - 2.0 * sine * cosine * apq + sine * sine * aqq
        a[q][q] = sine * sine * app + 2.0 * sine * cosine * apq + cosine * cosine * aqq
        a[p][q] = a[q][p] = 0.0
    values = tuple(sorted((max(0.0, a[i][i]) for i in range(3)), reverse=True))
    return values  # type: ignore[return-value]


def _cloud_rank_ratio(points: Sequence[Sequence[float]]) -> float:
    center = _centroid(points)
    covariance = [[0.0] * 3 for _ in range(3)]
    for point in points:
        zero = _vsub(point, center)
        for row in range(3):
            for column in range(3):
                covariance[row][column] += zero[row] * zero[column]
    eigenvalues = _symmetric_eigenvalues3(covariance)
    if eigenvalues[0] <= 1e-15:
        return 0.0
    return eigenvalues[2] / eigenvalues[0]


def _largest_eigenvector4(matrix: Sequence[Sequence[float]]) -> list[float]:
    a = [list(row) for row in matrix]
    vectors = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for _ in range(96):
        magnitude, p, q = max(
            (abs(a[i][j]), i, j) for i in range(4) for j in range(i + 1, 4)
        )
        if magnitude <= 1e-15:
            break
        angle = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
        cosine, sine = math.cos(angle), math.sin(angle)
        for k in range(4):
            if k not in (p, q):
                apk, aqk = a[p][k], a[q][k]
                a[p][k] = a[k][p] = cosine * apk - sine * aqk
                a[q][k] = a[k][q] = sine * apk + cosine * aqk
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = cosine * cosine * app - 2.0 * sine * cosine * apq + sine * sine * aqq
        a[q][q] = sine * sine * app + 2.0 * sine * cosine * apq + cosine * cosine * aqq
        a[p][q] = a[q][p] = 0.0
        for k in range(4):
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p] = cosine * vkp - sine * vkq
            vectors[k][q] = sine * vkp + cosine * vkq
    index = max(range(4), key=lambda value: (a[value][value], -value))
    result = [vectors[row][index] for row in range(4)]
    if result[0] < 0.0:
        result = [-value for value in result]
    length = math.sqrt(sum(value * value for value in result))
    if length <= 1e-15:
        raise SemanticControlCageError("similarity_quaternion_unavailable")
    return [value / length for value in result]


def _quaternion_rotation(q: Sequence[float]) -> tuple[tuple[float, float, float], ...]:
    w, x, y, z = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def _rotate(rotation: Sequence[Sequence[float]], point: Sequence[float]) -> tuple[float, float, float]:
    return tuple(_dot(row, point) for row in rotation)  # type: ignore[return-value]


def apply_similarity(similarity: Similarity, point: Sequence[float]) -> tuple[float, float, float]:
    return _vadd(_vmul(_rotate(similarity.rotation, point), similarity.scale), similarity.translation)


def _region_centroids(
    vertices: Sequence[Sequence[float]], regions: Sequence[str], excluded: set[int],
    required_regions: Sequence[str],
) -> dict[str, tuple[float, float, float]]:
    if len(vertices) != len(regions):
        raise SemanticControlCageError("vertex_region_count_mismatch")
    result: dict[str, tuple[float, float, float]] = {}
    for region in required_regions:
        points = [vertices[i] for i, label in enumerate(regions) if label == region and i not in excluded]
        if not points:
            raise SemanticControlCageError(f"required_region_mapping_unavailable:{region}")
        result[region] = _centroid(points)
    return result


def validate_physical_left_right(
    vertices: Sequence[Sequence[float]], regions: Sequence[str], excluded: set[int],
    minimum_separation: float,
) -> dict[str, tuple[float, float]]:
    """Require anatomical left at larger world X than anatomical right."""

    if not math.isfinite(minimum_separation) or minimum_separation <= 0.0:
        raise SemanticControlCageError("left_right_minimum_separation_invalid")
    centroids = _region_centroids(vertices, regions, excluded, REGIONS)
    result: dict[str, tuple[float, float]] = {}
    for left, right in SIDE_PAIRS:
        lx, rx = centroids[left][0], centroids[right][0]
        if lx - rx < minimum_separation:
            raise SemanticControlCageError(f"physical_left_right_order_failed:{left}:{right}")
        result[left.rsplit(".", 1)[0]] = (lx, rx)
    return result


def similarity_from_region_centroids(
    source_vertices: Sequence[Sequence[float]], source_regions: Sequence[str],
    target_vertices: Sequence[Sequence[float]], target_regions: Sequence[str],
    required_regions: Sequence[str], source_excluded: set[int], target_excluded: set[int],
    *, minimum_rank_ratio: float, minimum_scale: float, maximum_scale: float,
    maximum_normalized_rms_residual: float, maximum_orthonormal_residual: float,
    minimum_left_right_separation: float,
) -> AlignmentResult:
    validate_physical_left_right(source_vertices, source_regions, source_excluded, minimum_left_right_separation)
    validate_physical_left_right(target_vertices, target_regions, target_excluded, minimum_left_right_separation)
    source_centroids = _region_centroids(source_vertices, source_regions, source_excluded, required_regions)
    target_centroids = _region_centroids(target_vertices, target_regions, target_excluded, required_regions)
    source_points = [source_centroids[region] for region in required_regions]
    target_points = [target_centroids[region] for region in required_regions]
    source_rank = _cloud_rank_ratio(source_points)
    target_rank = _cloud_rank_ratio(target_points)
    if source_rank < minimum_rank_ratio or target_rank < minimum_rank_ratio:
        raise SemanticControlCageError("alignment_centroid_cloud_not_full_rank")
    source_center, target_center = _centroid(source_points), _centroid(target_points)
    source_zero = [_vsub(point, source_center) for point in source_points]
    target_zero = [_vsub(point, target_center) for point in target_points]
    spread = sum(_dot(point, point) for point in source_zero)
    target_spread = sum(_dot(point, point) for point in target_zero)
    if spread <= 1e-15 or target_spread <= 1e-15:
        raise SemanticControlCageError("alignment_spread_degenerate")
    covariance = [[0.0] * 3 for _ in range(3)]
    for source, target in zip(source_zero, target_zero):
        for row in range(3):
            for column in range(3):
                covariance[row][column] += source[row] * target[column]
    covariance_det = _det3(covariance)
    covariance_norm = math.sqrt(sum(value * value for row in covariance for value in row))
    if covariance_norm <= 1e-15 or covariance_det <= (covariance_norm ** 3) * minimum_rank_ratio:
        raise SemanticControlCageError("alignment_reflection_or_covariance_degenerate")
    sxx, sxy, sxz = covariance[0]
    syx, syy, syz = covariance[1]
    szx, szy, szz = covariance[2]
    horn = (
        (sxx + syy + szz, syz - szy, szx - sxz, sxy - syx),
        (syz - szy, sxx - syy - szz, sxy + syx, szx + sxz),
        (szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy),
        (sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz),
    )
    rotation = _quaternion_rotation(_largest_eigenvector4(horn))
    determinant = _det3(rotation)
    if determinant <= 0.0 or abs(determinant - 1.0) > maximum_orthonormal_residual:
        raise SemanticControlCageError("alignment_rotation_not_proper")
    orthonormal = 0.0
    for row in range(3):
        for column in range(3):
            actual = sum(rotation[k][row] * rotation[k][column] for k in range(3))
            expected = 1.0 if row == column else 0.0
            orthonormal = max(orthonormal, abs(actual - expected))
    if orthonormal > maximum_orthonormal_residual:
        raise SemanticControlCageError("alignment_rotation_not_orthonormal")
    numerator = sum(_dot(target, _rotate(rotation, source)) for source, target in zip(source_zero, target_zero))
    scale = numerator / spread
    if not math.isfinite(scale) or scale < minimum_scale or scale > maximum_scale:
        raise SemanticControlCageError("alignment_scale_outside_plausible_range")
    translation = _vsub(target_center, _vmul(_rotate(rotation, source_center), scale))
    similarity = Similarity(scale, rotation, translation)
    squared = sum(
        _dot(_vsub(apply_similarity(similarity, source), target), _vsub(apply_similarity(similarity, source), target))
        for source, target in zip(source_points, target_points)
    )
    rms = math.sqrt(squared / len(source_points))
    target_rms = math.sqrt(target_spread / len(target_points))
    normalized = rms / target_rms
    if normalized > maximum_normalized_rms_residual:
        raise SemanticControlCageError("alignment_normalized_residual_too_large")
    return AlignmentResult(
        similarity, source_rank, target_rank, covariance_det, determinant,
        orthonormal, normalized,
    )


def _normalize_mesh(
    vertex_count: int, edges: Iterable[Sequence[int]], faces: Iterable[Sequence[int]],
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, ...], ...]]:
    if type(vertex_count) is not int or vertex_count <= 0:
        raise SemanticControlCageError("mesh_vertex_count_invalid")
    edge_rows: list[tuple[int, int]] = []
    for position, raw in enumerate(edges):
        row = tuple(raw)
        if len(row) != 2:
            raise SemanticControlCageError(f"mesh_edge_shape_invalid:{position}")
        first = _integer(row[0], f"edge_{position}_a", 0, vertex_count - 1)
        second = _integer(row[1], f"edge_{position}_b", 0, vertex_count - 1)
        if first == second:
            raise SemanticControlCageError(f"mesh_self_edge:{position}")
        edge_rows.append(tuple(sorted((first, second))))
    if len(set(edge_rows)) != len(edge_rows):
        raise SemanticControlCageError("mesh_duplicate_edge")
    edge_rows.sort()
    face_rows: list[tuple[int, ...]] = []
    for position, raw in enumerate(faces):
        row = tuple(_integer(value, f"face_{position}_vertex", 0, vertex_count - 1) for value in raw)
        if len(row) < 3 or len(set(row)) != len(row):
            raise SemanticControlCageError(f"mesh_face_invalid:{position}")
        face_rows.append(row)
    if not face_rows:
        raise SemanticControlCageError("mesh_faces_absent")
    return tuple(edge_rows), tuple(face_rows)


def _mesh_topology_sha256(vertex_count: int, edges: Sequence[Sequence[int]], faces: Sequence[Sequence[int]]) -> str:
    normalized_edges, normalized_faces = _normalize_mesh(vertex_count, edges, faces)
    return canonical_sha256({
        "vertex_count": vertex_count,
        "edges": [list(edge) for edge in normalized_edges],
        "faces": [list(face) for face in normalized_faces],
    })


def build_same_region_graph(
    vertices: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], regions: Sequence[str], excluded: set[int],
) -> list[list[tuple[int, float]]]:
    if len(vertices) != len(regions):
        raise SemanticControlCageError("source_vertex_region_count_mismatch")
    graph: list[dict[int, float]] = [dict() for _ in vertices]
    for face_index, face in enumerate(faces):
        row = tuple(face)
        if len(row) < 3 or len(set(row)) != len(row):
            raise SemanticControlCageError(f"foundation_face_invalid:{face_index}")
        for position, first in enumerate(row):
            second = row[(position + 1) % len(row)]
            if type(first) is not int or type(second) is not int or min(first, second) < 0 or max(first, second) >= len(vertices):
                raise SemanticControlCageError(f"foundation_face_vertex_out_of_range:{face_index}")
            if first in excluded or second in excluded or regions[first] != regions[second]:
                continue
            distance = _norm(_vsub(vertices[first], vertices[second]))
            if distance <= 1e-15:
                raise SemanticControlCageError("foundation_zero_length_same_region_edge")
            current = graph[first].get(second)
            if current is None or distance < current:
                graph[first][second] = distance
                graph[second][first] = distance
    return [sorted(row.items()) for row in graph]


def _dijkstra(
    graph: Sequence[Sequence[tuple[int, float]]], seeds: Iterable[int], allowed: set[int],
) -> list[float]:
    distances = [math.inf] * len(graph)
    queue: list[tuple[float, int]] = []
    for seed in sorted(set(seeds)):
        if seed not in allowed:
            raise SemanticControlCageError("geodesic_seed_outside_region")
        distances[seed] = 0.0
        heapq.heappush(queue, (0.0, seed))
    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        for neighbor, cost in graph[vertex]:
            if neighbor not in allowed:
                continue
            candidate = distance + cost
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return distances


def select_control_anchors_with_coverage(
    vertices: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], regions: Sequence[str],
    excluded: set[int], anchors_per_region: Mapping[str, int],
    maximum_geodesic_radius_um: Mapping[str, int],
    required_regions: Sequence[str] = REGIONS,
) -> CoverageResult:
    if tuple(anchors_per_region) != tuple(required_regions) or tuple(maximum_geodesic_radius_um) != tuple(required_regions):
        raise SemanticControlCageError("control_region_order_or_coverage_mismatch")
    if sum(int(value) for value in anchors_per_region.values()) != 432:
        raise SemanticControlCageError("control_anchor_total_must_be_432")
    graph = build_same_region_graph(vertices, faces, regions, excluded)
    anchors: dict[str, tuple[int, ...]] = {}
    rows: list[dict[str, int | str]] = []
    for region in required_regions:
        candidates = tuple(i for i, label in enumerate(regions) if label == region and i not in excluded)
        required = _integer(anchors_per_region[region], f"anchor_count_{region}", 1)
        if len(candidates) < required:
            raise SemanticControlCageError(f"minimum_control_anchor_coverage_unavailable:{region}")
        allowed = set(candidates)
        component = set()
        stack = [min(candidates)]
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(neighbor for neighbor, _ in graph[current] if neighbor in allowed and neighbor not in component)
        if component != allowed:
            raise SemanticControlCageError(f"same_region_component_not_single:{region}:{len(allowed - component)}")
        center = _centroid([vertices[index] for index in candidates])
        first = max(candidates, key=lambda index: (_dot(_vsub(vertices[index], center), _vsub(vertices[index], center)), -index))
        chosen = [first]
        minimum = _dijkstra(graph, chosen, allowed)
        while len(chosen) < required:
            remaining = [index for index in candidates if index not in set(chosen)]
            next_index = max(remaining, key=lambda index: (minimum[index], -index))
            if not math.isfinite(minimum[next_index]):
                raise SemanticControlCageError(f"disconnected_vertex_selected_as_anchor:{region}")
            chosen.append(next_index)
            new = _dijkstra(graph, (next_index,), allowed)
            minimum = [min(old, fresh) for old, fresh in zip(minimum, new)]
        coverage_distances = _dijkstra(graph, chosen, allowed)
        if any(not math.isfinite(coverage_distances[index]) for index in candidates):
            raise SemanticControlCageError(f"uncovered_same_region_vertex:{region}")
        maximum_um = int(math.floor(max(coverage_distances[index] for index in candidates) * 1_000_000.0 + 0.5))
        configured = _integer(maximum_geodesic_radius_um[region], f"maximum_geodesic_radius_{region}", 1)
        if maximum_um > configured:
            raise SemanticControlCageError(f"control_geodesic_radius_failed:{region}:{maximum_um}:{configured}")
        anchors[region] = tuple(chosen)
        rows.append({
            "region": region,
            "permissible_vertex_count": len(candidates),
            "same_region_connected_component_count": 1,
            "control_anchor_count": len(chosen),
            "covered_vertex_count": len(candidates),
            "maximum_anchor_geodesic_distance_micrometers": maximum_um,
            "configured_maximum_micrometers": configured,
        })
    return CoverageResult(anchors, tuple(rows))


def _closest_point_barycentric(
    point: Sequence[float], a: Sequence[float], b: Sequence[float], c: Sequence[float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    ab, ac, ap = _vsub(b, a), _vsub(c, a), _vsub(point, a)
    d1, d2 = _dot(ab, ap), _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return tuple(a), (1.0, 0.0, 0.0)  # type: ignore[return-value]
    bp = _vsub(point, b)
    d3, d4 = _dot(ab, bp), _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return tuple(b), (0.0, 1.0, 0.0)  # type: ignore[return-value]
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return _vadd(a, _vmul(ab, v)), (1.0 - v, v, 0.0)
    cp = _vsub(point, c)
    d5, d6 = _dot(ab, cp), _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return tuple(c), (0.0, 0.0, 1.0)  # type: ignore[return-value]
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return _vadd(a, _vmul(ac, w)), (1.0 - w, 0.0, w)
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        bc = _vsub(c, b)
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return _vadd(b, _vmul(bc, w)), (0.0, 1.0 - w, w)
    denominator = va + vb + vc
    if abs(denominator) <= 1e-18:
        raise SemanticControlCageError("target_triangle_degenerate")
    v, w = vb / denominator, vc / denominator
    return _vadd(a, _vadd(_vmul(ab, v), _vmul(ac, w))), (1.0 - v - w, v, w)


def _fixed_barycentric(values: Sequence[float]) -> list[int]:
    if len(values) != 3 or any(not math.isfinite(value) or value < -1e-10 or value > 1.0 + 1e-10 for value in values):
        raise SemanticControlCageError("barycentric_out_of_range")
    cleaned = [max(0.0, min(1.0, value)) for value in values]
    if abs(sum(cleaned) - 1.0) > 1e-8:
        raise SemanticControlCageError("barycentric_sum_invalid")
    scaled = [value * FIXED_SCALE for value in cleaned]
    result = [int(math.floor(value)) for value in scaled]
    remainder = FIXED_SCALE - sum(result)
    order = sorted(range(3), key=lambda index: (-(scaled[index] - result[index]), index))
    for index in order[:remainder]:
        result[index] += 1
    if any(value < 0 or value > FIXED_SCALE for value in result) or sum(result) != FIXED_SCALE:
        raise SemanticControlCageError("fixed_barycentric_invalid")
    return result


MAPPING_KEYS = {
    "foundation_vertex_index", "foundation_region", "target_region",
    "r19_face_index", "r19_triangle_index", "r19_triangle_vertex_indices",
    "barycentric_fixed_1e9", "distance_micrometers", "normal_dot_fixed_1e9",
}


def map_control_anchors_to_target(
    anchors: Mapping[str, Sequence[int]], source_vertices: Sequence[Sequence[float]],
    source_normals: Sequence[Sequence[float]], source_regions: Sequence[str],
    target_vertices: Sequence[Sequence[float]], target_triangles: Sequence[Triangle],
    target_regions: Sequence[str], excluded_target_faces: set[int], similarity: Similarity,
    max_distance_um: Mapping[str, int], min_normal_dot_fixed: Mapping[str, int],
) -> list[dict[str, object]]:
    if len(source_vertices) != len(source_normals) or len(source_vertices) != len(source_regions):
        raise SemanticControlCageError("source_geometry_count_mismatch")
    if len(target_vertices) != len(target_regions):
        raise SemanticControlCageError("target_geometry_count_mismatch")
    by_region: dict[str, list[Triangle]] = {region: [] for region in anchors}
    triangle_keys: set[tuple[int, int]] = set()
    for triangle in target_triangles:
        if type(triangle.face_index) is not int or type(triangle.triangle_index) is not int or min(triangle.face_index, triangle.triangle_index) < 0:
            raise SemanticControlCageError("negative_target_face_or_triangle_index")
        key = (triangle.face_index, triangle.triangle_index)
        if key in triangle_keys:
            raise SemanticControlCageError("duplicate_target_face_triangle_key")
        triangle_keys.add(key)
        if len(set(triangle.vertex_indices)) != 3 or min(triangle.vertex_indices) < 0 or max(triangle.vertex_indices) >= len(target_vertices):
            raise SemanticControlCageError("target_triangle_vertex_invalid")
        if triangle.face_index in excluded_target_faces:
            continue
        labels = {target_regions[index] for index in triangle.vertex_indices}
        if len(labels) == 1 and next(iter(labels)) in by_region:
            by_region[next(iter(labels))].append(triangle)
    records: list[dict[str, object]] = []
    for region in anchors:
        triangles = sorted(by_region[region], key=lambda item: (item.face_index, item.triangle_index, item.vertex_indices))
        if not triangles:
            raise SemanticControlCageError(f"same_region_target_faces_unavailable:{region}")
        for anchor in anchors[region]:
            if anchor < 0 or anchor >= len(source_vertices) or source_regions[anchor] != region:
                raise SemanticControlCageError(f"source_anchor_region_mismatch:{region}:{anchor}")
            point = apply_similarity(similarity, source_vertices[anchor])
            normal = _normalize(_rotate(similarity.rotation, source_normals[anchor]))
            best: tuple[float, int, int, tuple[int, int, int], tuple[float, float, float], float] | None = None
            for triangle in triangles:
                ia, ib, ic = triangle.vertex_indices
                a, b, c = target_vertices[ia], target_vertices[ib], target_vertices[ic]
                triangle_normal = _normalize(_cross(_vsub(b, a), _vsub(c, a)))
                normal_dot = _dot(normal, triangle_normal)
                if int(round(normal_dot * FIXED_SCALE)) < int(min_normal_dot_fixed[region]):
                    continue
                closest, barycentric = _closest_point_barycentric(point, a, b, c)
                delta = _vsub(point, closest)
                candidate = (_dot(delta, delta), triangle.face_index, triangle.triangle_index, triangle.vertex_indices, barycentric, normal_dot)
                if best is None or candidate[:4] < best[:4]:
                    best = candidate
            if best is None:
                raise SemanticControlCageError(f"normal_compatible_target_unavailable:{region}:{anchor}")
            distance_um = int(math.floor(math.sqrt(best[0]) * 1_000_000.0 + 0.5))
            if distance_um > int(max_distance_um[region]):
                raise SemanticControlCageError(f"target_distance_gate_failed:{region}:{anchor}")
            records.append({
                "foundation_vertex_index": anchor,
                "foundation_region": region,
                "target_region": region,
                "r19_face_index": best[1],
                "r19_triangle_index": best[2],
                "r19_triangle_vertex_indices": list(best[3]),
                "barycentric_fixed_1e9": _fixed_barycentric(best[4]),
                "distance_micrometers": distance_um,
                "normal_dot_fixed_1e9": int(round(best[5] * FIXED_SCALE)),
            })
    return sorted(records, key=lambda row: (REGIONS.index(str(row["foundation_region"])), int(row["foundation_vertex_index"])))


def encode_mapping_records(records: Sequence[Mapping[str, object]]) -> tuple[str, str, str]:
    packed = bytearray()
    canonical_rows: list[dict[str, object]] = []
    for position, row in enumerate(records):
        if set(row) != MAPPING_KEYS:
            raise SemanticControlCageError(f"mapping_record_keys_drifted:{position}")
        region = row["foundation_region"]
        if region != row["target_region"] or region not in REGIONS:
            raise SemanticControlCageError(f"mapping_region_invalid:{position}")
        triangle = row["r19_triangle_vertex_indices"]
        barycentric = row["barycentric_fixed_1e9"]
        if not isinstance(triangle, list) or len(triangle) != 3 or not isinstance(barycentric, list) or len(barycentric) != 3:
            raise SemanticControlCageError(f"mapping_vector_shape_invalid:{position}")
        values = (
            _integer(row["foundation_vertex_index"], "mapping_source", 0, UINT32_MAX),
            REGIONS.index(str(region)),
            _integer(row["r19_face_index"], "mapping_face", 0, UINT32_MAX),
            _integer(row["r19_triangle_index"], "mapping_triangle", 0, UINT32_MAX),
            *(_integer(value, "mapping_triangle_vertex", 0, UINT32_MAX) for value in triangle),
            *(_integer(value, "mapping_barycentric", 0, FIXED_SCALE) for value in barycentric),
            _integer(row["distance_micrometers"], "mapping_distance", 0, UINT32_MAX),
            _integer(row["normal_dot_fixed_1e9"], "mapping_normal", -FIXED_SCALE, FIXED_SCALE),
        )
        if sum(values[7:10]) != FIXED_SCALE:
            raise SemanticControlCageError(f"mapping_barycentric_sum_invalid:{position}")
        try:
            packed.extend(MAPPING_RECORD.pack(*values))
        except struct.error as exc:
            raise SemanticControlCageError(f"mapping_struct_pack_rejected:{position}") from exc
        canonical_rows.append(dict(row))
    raw = bytes(packed)
    return (
        base64.b64encode(raw).decode("ascii"), hashlib.sha256(raw).hexdigest(),
        canonical_sha256({"mapping_codec": MAPPING_CODEC, "mappings": canonical_rows}),
    )


def decode_and_validate_mapping_records(
    *, encoded: object, declared_count: object, declared_record_bytes: object,
    declared_codec: object, declared_binary_sha256: object, declared_mapping_sha256: object,
    expected_anchors: Mapping[str, Sequence[int]], source_regions: Sequence[str],
    target_regions: Sequence[str], target_triangles: Sequence[Triangle], target_face_count: int,
    excluded_target_faces: set[int], maximum_distance_um: Mapping[str, int],
    minimum_normal_dot_fixed: Mapping[str, int],
) -> list[dict[str, object]]:
    count = _integer(declared_count, "mapping_count", 0)
    if count != 432 or count != sum(len(values) for values in expected_anchors.values()):
        raise SemanticControlCageError("mapping_count_not_exact_432")
    if declared_record_bytes != MAPPING_RECORD.size or declared_codec != MAPPING_CODEC:
        raise SemanticControlCageError("mapping_codec_or_record_size_drifted")
    _hex64(declared_binary_sha256, "mapping_binary_sha256")
    _hex64(declared_mapping_sha256, "mapping_sha256")
    if not isinstance(encoded, str):
        raise SemanticControlCageError("mapping_base64_not_text")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise SemanticControlCageError("mapping_base64_invalid") from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise SemanticControlCageError("mapping_base64_noncanonical")
    if len(raw) != count * MAPPING_RECORD.size:
        raise SemanticControlCageError("mapping_binary_size_mismatch")
    if hashlib.sha256(raw).hexdigest() != declared_binary_sha256:
        raise SemanticControlCageError("mapping_binary_digest_mismatch")
    triangle_by_key: dict[tuple[int, int], Triangle] = {}
    for triangle in target_triangles:
        key = (triangle.face_index, triangle.triangle_index)
        if key in triangle_by_key:
            raise SemanticControlCageError("target_triangle_key_duplicate")
        if triangle.face_index < 0 or triangle.face_index >= target_face_count or triangle.triangle_index < 0:
            raise SemanticControlCageError("target_triangle_face_or_index_out_of_range")
        triangle_by_key[key] = triangle
    expected = {index: region for region, values in expected_anchors.items() for index in values}
    if len(expected) != count:
        raise SemanticControlCageError("control_anchor_source_indices_not_unique")
    rows: list[dict[str, object]] = []
    seen: set[int] = set()
    for position in range(count):
        values = MAPPING_RECORD.unpack_from(raw, position * MAPPING_RECORD.size)
        if values[1] >= len(REGIONS):
            raise SemanticControlCageError(f"mapping_region_id_invalid:{position}")
        source, region = values[0], REGIONS[values[1]]
        if source in seen:
            raise SemanticControlCageError(f"mapping_source_duplicate:{source}")
        seen.add(source)
        if source not in expected or expected[source] != region or source >= len(source_regions) or source_regions[source] != region:
            raise SemanticControlCageError(f"mapping_source_or_region_mismatch:{source}")
        face, triangle_index = values[2], values[3]
        if face >= target_face_count or face in excluded_target_faces:
            raise SemanticControlCageError(f"mapping_face_out_of_range_or_excluded:{position}")
        triangle = triangle_by_key.get((face, triangle_index))
        triangle_vertices = tuple(values[4:7])
        if triangle is None or triangle.vertex_indices != triangle_vertices:
            raise SemanticControlCageError(f"mapping_triangle_identity_mismatch:{position}")
        if any(index >= len(target_regions) for index in triangle_vertices) or any(target_regions[index] != region for index in triangle_vertices):
            raise SemanticControlCageError(f"mapping_target_region_mismatch:{position}")
        barycentric = tuple(values[7:10])
        if any(value > FIXED_SCALE for value in barycentric) or sum(barycentric) != FIXED_SCALE:
            raise SemanticControlCageError(f"mapping_barycentric_invalid:{position}")
        distance, normal = values[10], values[11]
        if distance > _integer(maximum_distance_um[region], f"maximum_distance_{region}", 0):
            raise SemanticControlCageError(f"mapping_distance_invalid:{position}")
        if normal < -FIXED_SCALE or normal > FIXED_SCALE or normal < _integer(minimum_normal_dot_fixed[region], f"minimum_normal_{region}", -FIXED_SCALE, FIXED_SCALE):
            raise SemanticControlCageError(f"mapping_normal_invalid:{position}")
        rows.append({
            "foundation_vertex_index": source, "foundation_region": region,
            "target_region": region, "r19_face_index": face,
            "r19_triangle_index": triangle_index,
            "r19_triangle_vertex_indices": list(triangle_vertices),
            "barycentric_fixed_1e9": list(barycentric),
            "distance_micrometers": distance, "normal_dot_fixed_1e9": normal,
        })
    if set(expected) != seen:
        raise SemanticControlCageError("mapping_source_set_not_exact_control_anchor_set")
    if canonical_sha256({"mapping_codec": MAPPING_CODEC, "mappings": rows}) != declared_mapping_sha256:
        raise SemanticControlCageError("mapping_semantic_digest_mismatch")
    return rows


def _decode_afes_blob(reference: str, record: Mapping[str, Any]) -> tuple[int, ...]:
    if set(record) != {"codec", "endianness", "u32_count", "raw_bytes", "raw_sha256", "base64"}:
        raise SemanticControlCageError("afes_blob_record_keys_drifted")
    if record["codec"] != AFES_BLOB_CODEC or record["endianness"] != "big":
        raise SemanticControlCageError("afes_blob_codec_drifted")
    count = _integer(record["u32_count"], "afes_blob_count", 0, UINT32_MAX)
    byte_count = _integer(record["raw_bytes"], "afes_blob_bytes", 0, UINT32_MAX)
    if byte_count != count * 4 or not isinstance(record["base64"], str):
        raise SemanticControlCageError("afes_blob_size_or_base64_type_invalid")
    try:
        raw = base64.b64decode(record["base64"].encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise SemanticControlCageError("afes_blob_base64_invalid") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != byte_count or base64.b64encode(raw).decode("ascii") != record["base64"]:
        raise SemanticControlCageError("afes_blob_size_or_canonical_base64_mismatch")
    if record["raw_sha256"] != digest or reference != f"sha256:{digest}":
        raise SemanticControlCageError("afes_blob_digest_or_reference_mismatch")
    return tuple(value[0] for value in struct.iter_unpack(">I", raw))


def _decode_afes_index_reference(
    reference: Mapping[str, Any], blobs: Mapping[str, Mapping[str, Any]], referenced: set[str],
) -> tuple[int, ...]:
    if set(reference) != {"blob_ref", "semantic", "item_count", "semantic_sha256"} or reference.get("semantic") != AFES_INDEX_SEMANTIC:
        raise SemanticControlCageError("afes_index_reference_drifted")
    blob_ref = reference.get("blob_ref")
    if not isinstance(blob_ref, str) or blob_ref not in blobs:
        raise SemanticControlCageError("afes_index_reference_missing_blob")
    values = _decode_afes_blob(blob_ref, blobs[blob_ref])
    if tuple(sorted(set(values))) != values:
        raise SemanticControlCageError("afes_index_values_not_strictly_sorted_unique")
    if len(values) != _integer(reference["item_count"], "afes_index_item_count", 0):
        raise SemanticControlCageError("afes_index_count_mismatch")
    if reference["semantic_sha256"] != index_sha256(values):
        raise SemanticControlCageError("afes_index_semantic_digest_mismatch")
    referenced.add(blob_ref)
    return values


def _decode_afes_edge_reference(
    reference: Mapping[str, Any], blobs: Mapping[str, Mapping[str, Any]], referenced: set[str],
) -> tuple[tuple[int, int], ...]:
    if set(reference) != {"blob_ref", "semantic", "item_count", "semantic_sha256"} or reference.get("semantic") != AFES_EDGE_SEMANTIC:
        raise SemanticControlCageError("afes_edge_reference_drifted")
    blob_ref = reference.get("blob_ref")
    if not isinstance(blob_ref, str) or blob_ref not in blobs:
        raise SemanticControlCageError("afes_edge_reference_missing_blob")
    flat = _decode_afes_blob(blob_ref, blobs[blob_ref])
    if len(flat) % 2:
        raise SemanticControlCageError("afes_edge_blob_odd")
    edges = tuple(zip(flat[0::2], flat[1::2]))
    if any(first >= second for first, second in edges) or tuple(sorted(set(edges))) != edges:
        raise SemanticControlCageError("afes_edges_not_strictly_normalized")
    if len(edges) != _integer(reference["item_count"], "afes_edge_item_count", 0):
        raise SemanticControlCageError("afes_edge_count_mismatch")
    if reference["semantic_sha256"] != canonical_sha256([list(edge) for edge in edges]):
        raise SemanticControlCageError("afes_edge_semantic_digest_mismatch")
    referenced.add(blob_ref)
    return edges


def validate_compact_afes_analysis_against_mesh(
    compact: Mapping[str, Any], *, source_edges: Sequence[Sequence[int]], source_faces: Sequence[Sequence[int]],
    expected: Mapping[str, Any],
) -> dict[str, object]:
    if set(compact) != {"whole_mesh", "topology_structure", "groups", "afes_union", "transition_rings", "bounds_object_nm", "binary_arrays"}:
        raise SemanticControlCageError("compact_afes_top_level_keys_drifted")
    whole = compact["whole_mesh"]
    if not isinstance(whole, Mapping) or set(whole) != {"vertex_count", "edge_count", "face_count", "topology_sha256"}:
        raise SemanticControlCageError("compact_afes_whole_mesh_drifted")
    vertex_count = _integer(whole["vertex_count"], "afes_vertex_count", 1)
    edge_count = _integer(whole["edge_count"], "afes_edge_count", 1)
    face_count = _integer(whole["face_count"], "afes_face_count", 1)
    if (vertex_count, edge_count, face_count) != (
        _integer(expected["foundation_vertex_count"], "expected_foundation_vertices", 1),
        _integer(expected["foundation_edge_count"], "expected_foundation_edges", 1),
        _integer(expected["foundation_face_count"], "expected_foundation_faces", 1),
    ):
        raise SemanticControlCageError("compact_afes_foundation_counts_mismatch")
    if len(source_edges) != edge_count or len(source_faces) != face_count:
        raise SemanticControlCageError("live_foundation_topology_counts_mismatch")
    topology_digest = _mesh_topology_sha256(vertex_count, source_edges, source_faces)
    if whole["topology_sha256"] != topology_digest or topology_digest != _hex64(expected["foundation_topology_sha256"], "expected_foundation_topology_sha256"):
        raise SemanticControlCageError("foundation_topology_digest_mismatch")
    structure = compact["topology_structure"]
    structure_keys = {
        "connected_component_count", "isolated_vertex_count", "boundary_edge_count",
        "nonmanifold_edge_count", "loose_edge_count", "face_boundary_edge_missing_from_mesh_count",
        "duplicate_face_record_count", "transition_ring_loose_edge_incidence_count",
        "full_normalized_topology_sha256",
    }
    if not isinstance(structure, Mapping) or set(structure) != structure_keys:
        raise SemanticControlCageError("compact_afes_topology_structure_drifted")
    if structure["full_normalized_topology_sha256"] != topology_digest:
        raise SemanticControlCageError("compact_afes_full_topology_digest_mismatch")
    for key in structure_keys - {"full_normalized_topology_sha256"}:
        _integer(structure[key], f"topology_metric_{key}", 0)
    blobs = compact["binary_arrays"]
    if not isinstance(blobs, Mapping):
        raise SemanticControlCageError("compact_afes_blob_table_missing")
    raw_hashes: set[str] = set()
    for reference, record in sorted(blobs.items()):
        if not isinstance(reference, str) or not isinstance(record, Mapping):
            raise SemanticControlCageError("compact_afes_blob_row_invalid")
        _decode_afes_blob(reference, record)
        raw_digest = str(record["raw_sha256"])
        if raw_digest in raw_hashes:
            raise SemanticControlCageError("compact_afes_duplicate_raw_blob")
        raw_hashes.add(raw_digest)
    referenced: set[str] = set()
    groups_row = compact["groups"]
    if not isinstance(groups_row, Mapping) or not groups_row:
        raise SemanticControlCageError("compact_afes_groups_missing")
    groups: dict[str, tuple[int, ...]] = {}
    for name, row in sorted(groups_row.items()):
        if not isinstance(name, str) or not isinstance(row, Mapping) or set(row) != {"vertex_indices"}:
            raise SemanticControlCageError("compact_afes_group_row_invalid")
        groups[name] = _decode_afes_index_reference(row["vertex_indices"], blobs, referenced)
    if tuple(sorted(groups)) != tuple(expected["required_afes_group_names"]):
        raise SemanticControlCageError("compact_afes_exact_group_names_mismatch")
    union_row = compact["afes_union"]
    if not isinstance(union_row, Mapping) or set(union_row) != {"vertex_indices", "incident_face_indices", "internal_face_indices", "primary_connection_edges"}:
        raise SemanticControlCageError("compact_afes_union_row_drifted")
    union = _decode_afes_index_reference(union_row["vertex_indices"], blobs, referenced)
    incident = _decode_afes_index_reference(union_row["incident_face_indices"], blobs, referenced)
    internal = _decode_afes_index_reference(union_row["internal_face_indices"], blobs, referenced)
    connections = _decode_afes_edge_reference(union_row["primary_connection_edges"], blobs, referenced)
    reconstructed_union = tuple(sorted({value for values in groups.values() for value in values}))
    if union != reconstructed_union:
        raise SemanticControlCageError("compact_afes_group_union_mismatch")
    if len(union) != expected["afes_union_count"] or index_sha256(union) != expected["afes_union_sha256"]:
        raise SemanticControlCageError("compact_afes_union_count_or_digest_mismatch")
    normalized_edges, normalized_faces = _normalize_mesh(vertex_count, source_edges, source_faces)
    union_set = set(union)
    actual_incident = tuple(i for i, face in enumerate(normalized_faces) if any(v in union_set for v in face))
    actual_internal = tuple(i for i, face in enumerate(normalized_faces) if all(v in union_set for v in face))
    actual_connections = tuple(edge for edge in normalized_edges if (edge[0] in union_set) != (edge[1] in union_set))
    if incident != actual_incident or internal != actual_internal or connections != actual_connections:
        raise SemanticControlCageError("compact_afes_face_or_connection_provenance_mismatch")
    rings_row = compact["transition_rings"]
    if not isinstance(rings_row, Mapping) or set(rings_row) != {"ring_count", "rings", "combined_vertex_indices", "disjoint_from_afes_union"}:
        raise SemanticControlCageError("compact_afes_transition_row_drifted")
    if rings_row["ring_count"] != 2 or rings_row["disjoint_from_afes_union"] is not True:
        raise SemanticControlCageError("compact_afes_two_disjoint_rings_required")
    ring_rows = rings_row["rings"]
    if not isinstance(ring_rows, list) or len(ring_rows) != 2:
        raise SemanticControlCageError("compact_afes_ring_rows_invalid")
    decoded_rings: list[tuple[int, ...]] = []
    for number, row in enumerate(ring_rows, start=1):
        if not isinstance(row, Mapping) or set(row) != {"ring_number", "vertex_indices"} or row["ring_number"] != number:
            raise SemanticControlCageError("compact_afes_ring_order_or_shape_drifted")
        values = _decode_afes_index_reference(row["vertex_indices"], blobs, referenced)
        if len(values) != expected[f"ring_{number}_count"] or index_sha256(values) != expected[f"ring_{number}_sha256"]:
            raise SemanticControlCageError(f"compact_afes_ring_{number}_count_or_digest_mismatch")
        decoded_rings.append(values)
    combined = _decode_afes_index_reference(rings_row["combined_vertex_indices"], blobs, referenced)
    reconstructed_combined = tuple(sorted(set(decoded_rings[0]).union(decoded_rings[1])))
    if combined != reconstructed_combined or len(combined) != expected["combined_ring_count"] or index_sha256(combined) != expected["combined_ring_sha256"]:
        raise SemanticControlCageError("compact_afes_combined_ring_mismatch")
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in normalized_edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    first_expected = tuple(sorted({n for v in union for n in adjacency[v] if n not in union_set}))
    visited = union_set.union(first_expected)
    second_expected = tuple(sorted({n for v in first_expected for n in adjacency[v] if n not in visited}))
    if decoded_rings[0] != first_expected or decoded_rings[1] != second_expected:
        raise SemanticControlCageError("compact_afes_ring_topological_adjacency_or_order_mismatch")
    edge_set = set(normalized_edges)
    edge_face_incidence = {edge: 0 for edge in normalized_edges}
    missing_face_edges: set[tuple[int, int]] = set()
    for face in normalized_faces:
        for position, first in enumerate(face):
            edge = tuple(sorted((first, face[(position + 1) % len(face)])))
            if edge not in edge_set:
                missing_face_edges.add(edge)
            else:
                edge_face_incidence[edge] += 1
    full_adjacency: list[set[int]] = [set() for _ in range(vertex_count)]
    for first, second in normalized_edges:
        full_adjacency[first].add(second)
        full_adjacency[second].add(first)
    unvisited = set(range(vertex_count))
    component_count = 0
    isolated_count = 0
    while unvisited:
        component_count += 1
        seed = min(unvisited)
        if not full_adjacency[seed]:
            isolated_count += 1
        unvisited.remove(seed)
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbor in sorted(full_adjacency[current], reverse=True):
                if neighbor in unvisited:
                    unvisited.remove(neighbor)
                    stack.append(neighbor)
    face_keys = [tuple(sorted(face)) for face in normalized_faces]
    loose_edges = tuple(edge for edge, count in edge_face_incidence.items() if count == 0)
    transition_set = set(combined)
    measured_structure = {
        "full_normalized_topology_sha256": topology_digest,
        "connected_component_count": component_count,
        "isolated_vertex_count": isolated_count,
        "boundary_edge_count": sum(1 for count in edge_face_incidence.values() if count == 1),
        "nonmanifold_edge_count": sum(1 for count in edge_face_incidence.values() if count > 2),
        "loose_edge_count": len(loose_edges),
        "face_boundary_edge_missing_from_mesh_count": len(missing_face_edges),
        "duplicate_face_record_count": len(face_keys) - len(set(face_keys)),
        "transition_ring_loose_edge_incidence_count": sum(
            1 for first, second in loose_edges if first in transition_set or second in transition_set
        ),
    }
    if dict(structure) != measured_structure:
        raise SemanticControlCageError("compact_afes_topology_structure_not_reproduced")
    if measured_structure != expected["exact_topology_structure"]:
        raise SemanticControlCageError("compact_afes_topology_structure_not_exact_expected")
    bounds = compact["bounds_object_nm"]
    if not isinstance(bounds, Mapping) or set(bounds) != {
        "unit", "integer_units_per_meter", "rounding", "minimum", "maximum"
    }:
        raise SemanticControlCageError("compact_afes_bounds_record_drifted")
    if bounds.get("unit") != "nanometer" or bounds.get("integer_units_per_meter") != FIXED_SCALE or bounds.get(
        "rounding"
    ) != "decimal_from_shortest_roundtrip_float_then_half_even_to_integer":
        raise SemanticControlCageError("compact_afes_bounds_codec_drifted")
    for side in ("minimum", "maximum"):
        values = bounds.get(side)
        if not isinstance(values, list) or len(values) != 3:
            raise SemanticControlCageError("compact_afes_bounds_shape_drifted")
        for value in values:
            _integer(value, f"compact_afes_bound_{side}", -(2**63), 2**63 - 1)
    if dict(bounds) != expected["exact_afes_bounds_object_nm"]:
        raise SemanticControlCageError("compact_afes_bounds_not_exact_expected")
    if referenced != set(blobs):
        raise SemanticControlCageError("compact_afes_unreferenced_blob")
    locked = tuple(sorted(union_set.union(combined)))
    if len(locked) != expected["locked_vertex_count"] or index_sha256(locked) != expected["locked_vertex_sha256"]:
        raise SemanticControlCageError("compact_afes_locked_union_mismatch")
    return {
        "groups": groups, "afes_union": union, "transition_rings": tuple(decoded_rings),
        "combined_transition_vertices": combined, "locked_vertices": locked,
        "topology_sha256": topology_digest,
    }


def validate_afes_pair_bundle(
    *, pair_payload: Mapping[str, Any], pair_frame_sha256: str,
    run_payloads: Sequence[Mapping[str, Any]], run_frame_sha256s: Sequence[str],
    source_edges: Sequence[Sequence[int]], source_faces: Sequence[Sequence[int]],
    expected: Mapping[str, Any],
) -> tuple[set[int], dict[str, object]]:
    """Validate pair decision, two fresh runs, dependencies, and compact AFES."""

    if len(run_payloads) != 2 or len(run_frame_sha256s) != 2:
        raise SemanticControlCageError("afes_pair_requires_exactly_two_runs")
    if pair_frame_sha256 != _hex64(expected["pair_acceptance_frame_sha256"], "expected_pair_frame_sha256"):
        raise SemanticControlCageError("afes_pair_frame_digest_mismatch")
    if pair_payload.get("schema") != expected["pair_schema"] or pair_payload.get("status") != expected["pair_status"]:
        raise SemanticControlCageError("afes_pair_decision_not_exactly_accepted")
    contract_sha = _hex64(expected["execution_contract_sha256"], "expected_execution_contract_sha256")
    if pair_payload.get("execution_contract_sha256") != contract_sha:
        raise SemanticControlCageError("afes_pair_execution_contract_mismatch")
    pair_runs = pair_payload.get("runs")
    if not isinstance(pair_runs, list) or len(pair_runs) != 2:
        raise SemanticControlCageError("afes_pair_run_metadata_invalid")
    inners: list[Mapping[str, Any]] = []
    nonces: list[str] = []
    analysis_result: dict[str, object] | None = None
    inner_digests: list[str] = []
    for offset, (run, frame_sha) in enumerate(zip(run_payloads, run_frame_sha256s), start=1):
        if frame_sha != _hex64(expected[f"run_{offset:02d}_frame_sha256"], f"expected_run_{offset:02d}_frame_sha256"):
            raise SemanticControlCageError(f"afes_run_{offset:02d}_frame_digest_mismatch")
        if run.get("schema") != expected["run_schema"] or run.get("status") != expected["run_status"] or run.get("run_number") != offset:
            raise SemanticControlCageError(f"afes_run_{offset:02d}_identity_mismatch")
        nonce = run.get("session_nonce")
        if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
            raise SemanticControlCageError(f"afes_run_{offset:02d}_nonce_invalid")
        nonces.append(nonce)
        observed_contract = run.get("execution_contract")
        if not isinstance(observed_contract, Mapping) or observed_contract.get("sha256") != contract_sha or observed_contract.get("bytes") != expected["execution_contract_bytes"]:
            raise SemanticControlCageError(f"afes_run_{offset:02d}_contract_provenance_mismatch")
        inner = run.get("inner_attempt02_payload")
        if not isinstance(inner, Mapping) or inner.get("schema") != expected["inner_schema"] or inner.get("status") != expected["inner_status"]:
            raise SemanticControlCageError(f"afes_run_{offset:02d}_inner_identity_mismatch")
        if inner.get("foundation_object") != expected["foundation_object"] or inner.get("foundation_mesh") != expected["foundation_mesh"]:
            raise SemanticControlCageError(f"afes_run_{offset:02d}_foundation_identity_mismatch")
        verified_inputs = inner.get("verified_inputs")
        if not isinstance(verified_inputs, Mapping) or verified_inputs != expected["exact_extraction_verified_inputs"]:
            raise SemanticControlCageError(f"afes_run_{offset:02d}_extraction_dependencies_mismatch")
        analysis = inner.get("analysis")
        if not isinstance(analysis, Mapping):
            raise SemanticControlCageError(f"afes_run_{offset:02d}_analysis_missing")
        current = validate_compact_afes_analysis_against_mesh(
            analysis, source_edges=source_edges, source_faces=source_faces, expected=expected,
        )
        if analysis_result is None:
            analysis_result = current
        elif current != analysis_result:
            raise SemanticControlCageError("afes_two_fresh_run_analysis_reconstruction_mismatch")
        digest = canonical_sha256(dict(inner))
        inners.append(inner)
        inner_digests.append(digest)
        metadata = pair_runs[offset - 1]
        if not isinstance(metadata, Mapping) or metadata.get("run_number") != offset or metadata.get("session_nonce") != nonce or metadata.get("frame_sha256") != frame_sha or metadata.get("inner_payload_sha256") != digest or metadata.get("topology_sha256") != current["topology_sha256"]:
            raise SemanticControlCageError(f"afes_pair_run_{offset:02d}_metadata_mismatch")
    if nonces[0] == nonces[1]:
        raise SemanticControlCageError("afes_fresh_run_nonces_not_distinct")
    if inners[0] != inners[1] or inner_digests[0] != inner_digests[1]:
        raise SemanticControlCageError("afes_fresh_inner_payloads_do_not_match")
    if pair_payload.get("matching_inner_payload_sha256") != inner_digests[0] or pair_payload.get("full_normalized_topology_sha256") != analysis_result["topology_sha256"]:
        raise SemanticControlCageError("afes_pair_matching_digest_or_topology_mismatch")
    if pair_payload.get("bound_inputs_unchanged_under_locks") is not True:
        raise SemanticControlCageError("afes_pair_inputs_not_proved_unchanged_under_locks")
    locked = set(analysis_result["locked_vertices"])
    summary = {
        "pair_acceptance_frame_sha256": pair_frame_sha256,
        "execution_contract_sha256": contract_sha,
        "matching_inner_payload_sha256": inner_digests[0],
        "full_normalized_topology_sha256": analysis_result["topology_sha256"],
        "afes_union_vertex_count": expected["afes_union_count"],
        "afes_union_vertex_sha256": expected["afes_union_sha256"],
        "ring_1_vertex_count": expected["ring_1_count"],
        "ring_1_vertex_sha256": expected["ring_1_sha256"],
        "ring_2_vertex_count": expected["ring_2_count"],
        "ring_2_vertex_sha256": expected["ring_2_sha256"],
        "combined_ring_vertex_count": expected["combined_ring_count"],
        "combined_ring_vertex_sha256": expected["combined_ring_sha256"],
        "locked_vertex_count": expected["locked_vertex_count"],
        "locked_vertex_sha256": expected["locked_vertex_sha256"],
        "fresh_run_count": 2,
        "fresh_session_nonces_distinct": "YES",
        "pair_decision": str(expected["pair_status"]),
    }
    return locked, summary


def alignment_receipt(result: AlignmentResult) -> dict[str, object]:
    value = result.similarity
    return {
        "scale_fixed_1e9": int(round(value.scale * FIXED_SCALE)),
        "rotation_fixed_1e9": [[int(round(component * FIXED_SCALE)) for component in row] for row in value.rotation],
        "translation_micrometers": [int(round(component * 1_000_000.0)) for component in value.translation],
        "source_rank_ratio_fixed_1e9": int(round(result.source_rank_ratio * FIXED_SCALE)),
        "target_rank_ratio_fixed_1e9": int(round(result.target_rank_ratio * FIXED_SCALE)),
        "covariance_determinant_sign": "POSITIVE",
        "rotation_determinant_fixed_1e9": int(round(result.rotation_determinant * FIXED_SCALE)),
        "orthonormal_residual_fixed_1e12": int(round(result.orthonormal_residual * 1_000_000_000_000)),
        "normalized_rms_residual_fixed_1e9": int(round(result.normalized_rms_residual * FIXED_SCALE)),
        "reflection": "REJECTED",
    }


__all__ = [
    "AFES_BLOB_CODEC", "AFES_EDGE_SEMANTIC", "AFES_INDEX_SEMANTIC",
    "AlignmentResult", "CoverageResult", "FIXED_SCALE", "MAPPING_CODEC",
    "MAPPING_KEYS", "MAPPING_RECORD", "OFFICIAL_MAKEHUMAN_GROUP_NAMES",
    "OFFICIAL_MAKEHUMAN_GROUP_TO_REGION", "REGIONS", "SIDE_PAIRS",
    "SemanticControlCageError", "Similarity", "Triangle", "alignment_receipt",
    "apply_similarity", "canonical_json_bytes", "canonical_sha256",
    "classify_weighted_vertices", "decode_and_validate_mapping_records",
    "encode_mapping_records", "index_sha256", "map_control_anchors_to_target",
    "select_control_anchors_with_coverage", "semantic_region_for_exact_group",
    "similarity_from_region_centroids", "validate_afes_pair_bundle",
    "validate_compact_afes_analysis_against_mesh", "validate_physical_left_right",
]
