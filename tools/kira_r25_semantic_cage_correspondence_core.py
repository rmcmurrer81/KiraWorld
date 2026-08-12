"""Pure deterministic kernels for the R25 semantic-cage diagnostic.

This module does not import Blender and does not deform either mesh.  It
selects region-balanced geodesic anchors on the qualified foundation and
projects only those anchors to same-semantic-region R19 triangles outside the
explicit R20 rejected-face set.  All persisted evidence is integer/string
JSON; floating point is confined to transient calculations.
"""

from __future__ import annotations

import base64
import hashlib
import heapq
import json
import math
import re
import struct
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from tools import kira_r25_canonical_receipt as canonical_receipt


FIXED_SCALE = 1_000_000_000
MAX_CANONICAL_PAYLOAD_BYTES = canonical_receipt.MAX_RECEIPT_PAYLOAD_BYTES
MAPPING_RECORD = struct.Struct("<IBIIIIIIIIIi")
MAPPING_CODEC = "kira_r25_semantic_anchor_map_le_v1:u32_foundation_vertex,u8_region_id,u32_face,u32_triangle,u32_tri_a,u32_tri_b,u32_tri_c,u32_bary_a,u32_bary_b,u32_bary_c,u32_distance_um,i32_normal_dot_1e9"

REGIONS = (
    "face",
    "head",
    "neck",
    "torso",
    "upper_arm.L",
    "lower_arm.L",
    "hand.L",
    "upper_arm.R",
    "lower_arm.R",
    "hand.R",
    "thigh.L",
    "shin.L",
    "foot.L",
    "thigh.R",
    "shin.R",
    "foot.R",
)


class SemanticCageError(ValueError):
    """A fail-closed diagnostic boundary was not satisfied."""


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


def canonical_bytes(value: object) -> bytes:
    _require_integer_string_json(value)
    if not isinstance(value, dict):
        raise SemanticCageError("canonical_receipt_requires_top_level_object")
    try:
        return canonical_receipt.canonical_json_bytes(value)
    except canonical_receipt.ReceiptFrameError as exc:
        raise SemanticCageError(f"canonical_receipt_rejected:{exc.code}") from exc


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def encode_mapping_records(records: Sequence[Mapping[str, object]]) -> tuple[str, str]:
    packed = bytearray()
    for row in records:
        region = str(row["foundation_region"])
        if region != str(row["target_region"]) or region not in REGIONS:
            raise SemanticCageError("mapping_region_not_exact_or_unknown")
        triangle_vertices = row["r19_triangle_vertex_indices"]
        barycentric = row["barycentric_fixed_1e9"]
        if not isinstance(triangle_vertices, list) or len(triangle_vertices) != 3:
            raise SemanticCageError("mapping_triangle_vertices_invalid")
        if not isinstance(barycentric, list) or len(barycentric) != 3:
            raise SemanticCageError("mapping_barycentric_invalid")
        packed.extend(
            MAPPING_RECORD.pack(
                int(row["foundation_vertex_index"]),
                REGIONS.index(region),
                int(row["r19_face_index"]),
                int(row["r19_triangle_index"]),
                *(int(value) for value in triangle_vertices),
                *(int(value) for value in barycentric),
                int(row["distance_micrometers"]),
                int(row["normal_dot_fixed_1e9"]),
            )
        )
    raw = bytes(packed)
    return base64.b64encode(raw).decode("ascii"), hashlib.sha256(raw).hexdigest()


def decode_mapping_records(encoded: str, count: int) -> list[dict[str, object]]:
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise SemanticCageError("mapping_base64_invalid") from exc
    if len(raw) != count * MAPPING_RECORD.size:
        raise SemanticCageError("mapping_binary_size_mismatch")
    result: list[dict[str, object]] = []
    for offset in range(0, len(raw), MAPPING_RECORD.size):
        values = MAPPING_RECORD.unpack_from(raw, offset)
        if values[1] >= len(REGIONS):
            raise SemanticCageError("mapping_region_id_invalid")
        result.append(
            {
                "foundation_vertex_index": values[0],
                "foundation_region": REGIONS[values[1]],
                "target_region": REGIONS[values[1]],
                "r19_face_index": values[2],
                "r19_triangle_index": values[3],
                "r19_triangle_vertex_indices": list(values[4:7]),
                "barycentric_fixed_1e9": list(values[7:10]),
                "distance_micrometers": values[10],
                "normal_dot_fixed_1e9": values[11],
            }
        )
    return result


def _require_integer_string_json(value: object, where: str = "$") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, float):
        raise SemanticCageError(f"non_integer_string_json_at:{where}")
    if isinstance(value, (str, int)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_integer_string_json(item, f"{where}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SemanticCageError(f"non_string_key_at:{where}")
            _require_integer_string_json(item, f"{where}.{key}")
        return
    raise SemanticCageError(f"unsupported_json_type_at:{where}")


def _compact(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _side(name: str) -> str | None:
    lower = name.lower()
    compact = _compact(name)
    left = (
        "left" in compact
        or bool(re.search(r"(?:^|[._:\-])l(?:$|[._:\-])", lower))
        or lower.endswith(".l")
        or lower.endswith("_l")
    )
    right = (
        "right" in compact
        or bool(re.search(r"(?:^|[._:\-])r(?:$|[._:\-])", lower))
        or lower.endswith(".r")
        or lower.endswith("_r")
    )
    if left == right:
        return None
    return "L" if left else "R"


def semantic_region_for_group(name: str) -> str | None:
    """Map exact weight-group semantics to one high-level body region.

    Unknown or side-ambiguous names are deliberately not inferred from vertex
    coordinates.  This supports the MakeHuman default rig and common Mixamo
    names used by the R19 lineage while failing closed on an unknown rig.
    """

    compact = _compact(name)
    side = _side(name)

    if any(
        token in compact
        for token in (
            "finger",
            "thumb",
            "metacarpal",
            "wrist",
            "lefthand",
            "righthand",
        )
    ):
        return f"hand.{side}" if side else None
    if "foot" in compact or "toe" in compact:
        return f"foot.{side}" if side else None
    if any(token in compact for token in ("lowerarm", "forearm")):
        return f"lower_arm.{side}" if side else None
    if any(token in compact for token in ("upperarm", "leftarm", "rightarm")):
        return f"upper_arm.{side}" if side else None
    if "shoulder" in compact and side:
        return f"upper_arm.{side}"
    if any(token in compact for token in ("lowerleg", "shin", "calf")):
        return f"shin.{side}" if side else None
    if side and (
        compact.startswith("mixamorigleftleg")
        or compact.startswith("mixamorigrightleg")
    ) and not any(token in compact for token in ("upleg", "upperleg")):
        return f"shin.{side}"
    if any(token in compact for token in ("upperleg", "upleg", "thigh")):
        return f"thigh.{side}" if side else None
    if any(
        token in compact
        for token in (
            "jaw",
            "eye",
            "oculi",
            "orbicular",
            "oris",
            "levator",
            "risorius",
            "tongue",
            "special04",
            "special05",
        )
    ):
        return "face"
    if "head" in compact:
        return "head"
    if "neck" in compact:
        return "neck"
    if any(
        token in compact
        for token in ("spine", "root", "hips", "pelvis", "breast", "clavicle")
    ):
        return "torso"
    return None


def semantic_region_for_weights(
    assignments: Iterable[tuple[str, float]], minimum_recognized_weight: float = 0.50
) -> str:
    totals: dict[str, float] = {}
    for name, weight in assignments:
        if not math.isfinite(weight) or weight <= 0.0:
            continue
        region = semantic_region_for_group(str(name))
        if region is not None:
            totals[region] = totals.get(region, 0.0) + float(weight)
    recognized = sum(totals.values())
    if recognized + 1e-12 < minimum_recognized_weight or not totals:
        raise SemanticCageError("vertex_semantic_weight_unavailable")
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    if len(ordered) > 1 and abs(ordered[0][1] - ordered[1][1]) <= 1e-12:
        raise SemanticCageError("vertex_semantic_weight_tie")
    return ordered[0][0]


def classify_weighted_vertices(
    assignments: Sequence[Sequence[tuple[str, float]]],
    minimum_recognized_weight: float = 0.50,
) -> list[str]:
    regions: list[str] = []
    failures: list[int] = []
    for index, row in enumerate(assignments):
        try:
            regions.append(
                semantic_region_for_weights(row, minimum_recognized_weight)
            )
        except SemanticCageError:
            failures.append(index)
            regions.append("")
    if failures:
        sample = ",".join(str(value) for value in failures[:16])
        raise SemanticCageError(f"vertex_semantic_classification_failed:{sample}")
    return regions


def validate_lock_input(
    lock_receipt: Mapping[str, object], foundation_vertex_count: int
) -> tuple[set[int], dict[str, object]]:
    if lock_receipt.get("status") != "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY":
        raise SemanticCageError("afes_lock_status_not_accepted_for_diagnostic")
    union = lock_receipt.get("afes_union")
    rings = lock_receipt.get("transition_rings")
    if not isinstance(union, dict) or not isinstance(rings, list) or len(rings) < 2:
        raise SemanticCageError("afes_lock_or_two_rings_missing")
    indices = union.get("vertex_indices")
    if not isinstance(indices, list) or len(indices) != 1169:
        raise SemanticCageError("afes_union_indices_missing_or_wrong_count")
    union_set = _validated_indices(indices, foundation_vertex_count, "afes_union")
    if _index_digest(union_set) != (
        "e176a908e76fbca6f7bf2b843e3745fe9bc51cf4c46add2fa6dcd384fd413195"
    ):
        raise SemanticCageError("afes_union_index_digest_mismatch")
    locked = set(union_set)
    ring_summaries: list[dict[str, object]] = []
    prior = set(union_set)
    for ring_index, ring in enumerate(rings):
        if not isinstance(ring, dict) or not isinstance(ring.get("vertex_indices"), list):
            raise SemanticCageError("transition_ring_indices_missing")
        current = _validated_indices(
            ring["vertex_indices"], foundation_vertex_count, f"ring_{ring_index + 1}"
        )
        if not current or current & prior:
            raise SemanticCageError("transition_ring_empty_or_not_disjoint")
        prior.update(current)
        locked.update(current)
        ring_summaries.append(
            {
                "ring_number": ring_index + 1,
                "vertex_count": len(current),
                "vertex_index_sha256": _index_digest(current),
            }
        )
    summary: dict[str, object] = {
        "afes_vertex_count": len(union_set),
        "afes_vertex_index_sha256": _index_digest(union_set),
        "ring_count": len(ring_summaries),
        "rings": ring_summaries,
        "locked_vertex_count": len(locked),
        "locked_vertex_index_sha256": _index_digest(locked),
    }
    return locked, summary


def _validated_indices(values: Sequence[object], count: int, label: str) -> set[int]:
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise SemanticCageError(f"{label}_contains_non_integer")
    result = set(int(value) for value in values)
    if len(result) != len(values) or any(value < 0 or value >= count for value in result):
        raise SemanticCageError(f"{label}_duplicate_or_out_of_range")
    return result


def _index_digest(values: Iterable[int]) -> str:
    payload = json.dumps(
        sorted({int(value) for value in values}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _vadd(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vsub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vmul(a: Sequence[float], value: float) -> tuple[float, float, float]:
    return (a[0] * value, a[1] * value, a[2] * value)


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
        raise SemanticCageError("zero_length_normal")
    return (a[0] / length, a[1] / length, a[2] / length)


def _centroid(points: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    if not points:
        raise SemanticCageError("empty_centroid")
    inv = 1.0 / len(points)
    return (
        sum(point[0] for point in points) * inv,
        sum(point[1] for point in points) * inv,
        sum(point[2] for point in points) * inv,
    )


def _jacobi_largest_eigenvector(matrix: Sequence[Sequence[float]]) -> list[float]:
    a = [list(row) for row in matrix]
    vectors = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for _ in range(96):
        pairs = [(abs(a[i][j]), i, j) for i in range(4) for j in range(i + 1, 4)]
        magnitude, p, q = max(pairs, key=lambda item: (item[0], -item[1], -item[2]))
        if magnitude <= 1e-15:
            break
        angle = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(angle), math.sin(angle)
        for k in range(4):
            if k not in (p, q):
                apk, aqk = a[p][k], a[q][k]
                a[p][k] = a[k][p] = c * apk - s * aqk
                a[q][k] = a[k][q] = s * apk + c * aqk
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for k in range(4):
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p] = c * vkp - s * vkq
            vectors[k][q] = s * vkp + c * vkq
    eigen_index = max(range(4), key=lambda index: (a[index][index], -index))
    result = [vectors[row][eigen_index] for row in range(4)]
    if result[0] < 0.0:
        result = [-value for value in result]
    length = math.sqrt(sum(value * value for value in result))
    if length <= 1e-15:
        raise SemanticCageError("similarity_quaternion_unavailable")
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


def similarity_from_region_centroids(
    source_vertices: Sequence[Sequence[float]],
    source_regions: Sequence[str],
    target_vertices: Sequence[Sequence[float]],
    target_regions: Sequence[str],
    required_regions: Sequence[str],
    source_excluded: set[int],
    target_excluded: set[int],
) -> Similarity:
    source_points: list[tuple[float, float, float]] = []
    target_points: list[tuple[float, float, float]] = []
    for region in required_regions:
        sp = [source_vertices[i] for i, value in enumerate(source_regions) if value == region and i not in source_excluded]
        tp = [target_vertices[i] for i, value in enumerate(target_regions) if value == region and i not in target_excluded]
        if not sp or not tp:
            raise SemanticCageError(f"required_region_mapping_unavailable:{region}")
        source_points.append(_centroid(sp))
        target_points.append(_centroid(tp))
    source_center, target_center = _centroid(source_points), _centroid(target_points)
    source_zero = [_vsub(point, source_center) for point in source_points]
    target_zero = [_vsub(point, target_center) for point in target_points]
    spread = sum(_dot(point, point) for point in source_zero)
    if spread <= 1e-15:
        raise SemanticCageError("similarity_source_spread_degenerate")
    s = [[0.0] * 3 for _ in range(3)]
    for xpoint, ypoint in zip(source_zero, target_zero):
        for row in range(3):
            for col in range(3):
                s[row][col] += xpoint[row] * ypoint[col]
    sxx, sxy, sxz = s[0]
    syx, syy, syz = s[1]
    szx, szy, szz = s[2]
    n = (
        (sxx + syy + szz, syz - szy, szx - sxz, sxy - syx),
        (syz - szy, sxx - syy - szz, sxy + syx, szx + sxz),
        (szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy),
        (sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz),
    )
    rotation = _quaternion_rotation(_jacobi_largest_eigenvector(n))
    numerator = sum(_dot(ypoint, _rotate(rotation, xpoint)) for xpoint, ypoint in zip(source_zero, target_zero))
    scale = numerator / spread
    if not math.isfinite(scale) or scale <= 1e-12:
        raise SemanticCageError("similarity_scale_nonpositive")
    translation = _vsub(target_center, _vmul(_rotate(rotation, source_center), scale))
    return Similarity(scale, rotation, translation)


def apply_similarity(similarity: Similarity, point: Sequence[float]) -> tuple[float, float, float]:
    return _vadd(_vmul(_rotate(similarity.rotation, point), similarity.scale), similarity.translation)


def build_surface_graph(
    vertices: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], excluded: set[int]
) -> list[list[tuple[int, float]]]:
    graph: list[dict[int, float]] = [dict() for _ in vertices]
    for face in faces:
        if len(face) < 3:
            raise SemanticCageError("foundation_face_has_fewer_than_three_vertices")
        for index, first in enumerate(face):
            second = face[(index + 1) % len(face)]
            if first in excluded or second in excluded:
                continue
            if first < 0 or second < 0 or first >= len(vertices) or second >= len(vertices):
                raise SemanticCageError("foundation_face_vertex_out_of_range")
            distance = _norm(_vsub(vertices[first], vertices[second]))
            if distance <= 1e-15:
                raise SemanticCageError("foundation_zero_length_edge")
            current = graph[first].get(second)
            if current is None or distance < current:
                graph[first][second] = graph[second][first] = distance
    return [sorted(row.items()) for row in graph]


def _dijkstra(graph: Sequence[Sequence[tuple[int, float]]], seed: int) -> list[float]:
    distances = [math.inf] * len(graph)
    distances[seed] = 0.0
    queue = [(0.0, seed)]
    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        for neighbor, cost in graph[vertex]:
            candidate = distance + cost
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return distances


def select_geodesic_anchors(
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    regions: Sequence[str],
    excluded: set[int],
    anchors_per_region: Mapping[str, int],
) -> dict[str, list[int]]:
    graph = build_surface_graph(vertices, faces, excluded)
    result: dict[str, list[int]] = {}
    for region in anchors_per_region:
        required = int(anchors_per_region[region])
        candidates = [i for i, value in enumerate(regions) if value == region and i not in excluded]
        if required <= 0 or len(candidates) < required:
            raise SemanticCageError(f"minimum_anchor_coverage_unavailable:{region}")
        center = _centroid([vertices[index] for index in candidates])
        first = max(candidates, key=lambda index: (_dot(_vsub(vertices[index], center), _vsub(vertices[index], center)), -index))
        chosen = [first]
        minimum = _dijkstra(graph, first)
        while len(chosen) < required:
            remaining = [index for index in candidates if index not in set(chosen)]
            next_index = max(
                remaining,
                key=lambda index: (
                    1 if math.isinf(minimum[index]) else 0,
                    minimum[index] if not math.isinf(minimum[index]) else 0.0,
                    -index,
                ),
            )
            chosen.append(next_index)
            new_distances = _dijkstra(graph, next_index)
            minimum = [min(old, new) for old, new in zip(minimum, new_distances)]
        result[region] = chosen
    return result


def _closest_point_barycentric(
    point: Sequence[float], a: Sequence[float], b: Sequence[float], c: Sequence[float]
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    ab, ac, ap = _vsub(b, a), _vsub(c, a), _vsub(point, a)
    d1, d2 = _dot(ab, ap), _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return (tuple(a), (1.0, 0.0, 0.0))  # type: ignore[arg-type]
    bp = _vsub(point, b)
    d3, d4 = _dot(ab, bp), _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return (tuple(b), (0.0, 1.0, 0.0))  # type: ignore[arg-type]
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return (_vadd(a, _vmul(ab, v)), (1.0 - v, v, 0.0))
    cp = _vsub(point, c)
    d5, d6 = _dot(ab, cp), _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return (tuple(c), (0.0, 0.0, 1.0))  # type: ignore[arg-type]
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return (_vadd(a, _vmul(ac, w)), (1.0 - w, 0.0, w))
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        bc = _vsub(c, b)
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (_vadd(b, _vmul(bc, w)), (0.0, 1.0 - w, w))
    denominator = va + vb + vc
    if abs(denominator) <= 1e-18:
        raise SemanticCageError("target_triangle_degenerate")
    v, w = vb / denominator, vc / denominator
    return (_vadd(a, _vadd(_vmul(ab, v), _vmul(ac, w))), (1.0 - v - w, v, w))


def _fixed_barycentric(values: Sequence[float]) -> list[int]:
    cleaned = [0.0 if abs(value) <= 1e-12 else value for value in values]
    if any(value < 0.0 or value > 1.0 + 1e-10 for value in cleaned):
        raise SemanticCageError("barycentric_out_of_range")
    total = sum(cleaned)
    if abs(total - 1.0) > 1e-8:
        raise SemanticCageError("barycentric_sum_invalid")
    scaled = [max(0.0, min(1.0, value)) * FIXED_SCALE for value in cleaned]
    result = [int(math.floor(value)) for value in scaled]
    remainder = FIXED_SCALE - sum(result)
    order = sorted(range(3), key=lambda index: (-(scaled[index] - result[index]), index))
    for index in order[:remainder]:
        result[index] += 1
    if sum(result) != FIXED_SCALE:
        raise SemanticCageError("fixed_barycentric_sum_invalid")
    return result


def map_anchors_to_target(
    anchors: Mapping[str, Sequence[int]],
    source_vertices: Sequence[Sequence[float]],
    source_normals: Sequence[Sequence[float]],
    target_vertices: Sequence[Sequence[float]],
    target_triangles: Sequence[Triangle],
    target_regions: Sequence[str],
    excluded_target_faces: set[int],
    similarity: Similarity,
    max_distance_um: Mapping[str, int],
    min_normal_dot_fixed: Mapping[str, int],
) -> list[dict[str, object]]:
    by_region: dict[str, list[Triangle]] = {region: [] for region in anchors}
    for triangle in target_triangles:
        if triangle.face_index in excluded_target_faces:
            continue
        labels = {target_regions[index] for index in triangle.vertex_indices}
        if len(labels) == 1:
            label = next(iter(labels))
            if label in by_region:
                by_region[label].append(triangle)
    records: list[dict[str, object]] = []
    for region in anchors:
        triangles = sorted(
            by_region.get(region, []),
            key=lambda value: (value.face_index, value.triangle_index, value.vertex_indices),
        )
        if not triangles:
            raise SemanticCageError(f"same_region_target_faces_unavailable:{region}")
        if region not in max_distance_um or region not in min_normal_dot_fixed:
            raise SemanticCageError(f"geometric_gate_missing:{region}")
        for anchor_index in anchors[region]:
            point = apply_similarity(similarity, source_vertices[anchor_index])
            normal = _normalize(_rotate(similarity.rotation, source_normals[anchor_index]))
            best: tuple[float, int, int, tuple[int, int, int], tuple[float, float, float], float] | None = None
            for triangle in triangles:
                ia, ib, ic = triangle.vertex_indices
                a, b, c = target_vertices[ia], target_vertices[ib], target_vertices[ic]
                triangle_normal = _normalize(_cross(_vsub(b, a), _vsub(c, a)))
                normal_dot = _dot(normal, triangle_normal)
                if int(round(normal_dot * FIXED_SCALE)) < int(min_normal_dot_fixed[region]):
                    continue
                closest, bary = _closest_point_barycentric(point, a, b, c)
                distance_sq = _dot(_vsub(point, closest), _vsub(point, closest))
                key = (distance_sq, triangle.face_index, triangle.triangle_index, triangle.vertex_indices, bary, normal_dot)
                if best is None or key[:4] < best[:4]:
                    best = key
            if best is None:
                raise SemanticCageError(f"normal_compatible_target_unavailable:{region}:{anchor_index}")
            distance_um = int(math.floor(math.sqrt(best[0]) * 1_000_000.0 + 0.5))
            if distance_um > int(max_distance_um[region]):
                raise SemanticCageError(f"target_distance_gate_failed:{region}:{anchor_index}")
            records.append(
                {
                    "foundation_vertex_index": int(anchor_index),
                    "foundation_region": region,
                    "target_region": region,
                    "r19_face_index": int(best[1]),
                    "r19_triangle_index": int(best[2]),
                    "r19_triangle_vertex_indices": [int(value) for value in best[3]],
                    "barycentric_fixed_1e9": _fixed_barycentric(best[4]),
                    "distance_micrometers": distance_um,
                    "normal_dot_fixed_1e9": int(round(best[5] * FIXED_SCALE)),
                }
            )
    return sorted(records, key=lambda row: (str(row["foundation_region"]), int(row["foundation_vertex_index"])))


def _similarity_receipt(value: Similarity) -> dict[str, object]:
    return {
        "scale_fixed_1e9": int(round(value.scale * FIXED_SCALE)),
        "rotation_fixed_1e9": [
            [int(round(component * FIXED_SCALE)) for component in row]
            for row in value.rotation
        ],
        "translation_micrometers": [
            int(round(component * 1_000_000.0)) for component in value.translation
        ],
    }


def build_correspondence_receipt(
    *,
    source_vertices: Sequence[Sequence[float]],
    source_normals: Sequence[Sequence[float]],
    source_faces: Sequence[Sequence[int]],
    source_regions: Sequence[str],
    target_vertices: Sequence[Sequence[float]],
    target_regions: Sequence[str],
    target_triangles: Sequence[Triangle],
    excluded_target_faces: set[int],
    locked_source_vertices: set[int],
    lock_summary: Mapping[str, object],
    anchors_per_region: Mapping[str, int],
    max_distance_um: Mapping[str, int],
    min_normal_dot_fixed: Mapping[str, int],
    bindings: Mapping[str, str],
    required_regions: Sequence[str] = REGIONS,
) -> dict[str, object]:
    if len(source_vertices) != len(source_normals) or len(source_vertices) != len(source_regions):
        raise SemanticCageError("foundation_vertex_normal_region_count_mismatch")
    if len(target_vertices) != len(target_regions):
        raise SemanticCageError("target_vertex_region_count_mismatch")
    if tuple(anchors_per_region) != tuple(required_regions):
        raise SemanticCageError("anchor_region_order_or_coverage_mismatch")
    target_excluded_vertices = {
        vertex
        for triangle in target_triangles
        if triangle.face_index in excluded_target_faces
        for vertex in triangle.vertex_indices
    }
    similarity = similarity_from_region_centroids(
        source_vertices,
        source_regions,
        target_vertices,
        target_regions,
        required_regions,
        locked_source_vertices,
        target_excluded_vertices,
    )
    anchors = select_geodesic_anchors(
        source_vertices, source_faces, source_regions, locked_source_vertices, anchors_per_region
    )
    if any(vertex in locked_source_vertices for values in anchors.values() for vertex in values):
        raise SemanticCageError("afes_or_transition_lock_selected_as_anchor")
    mappings = map_anchors_to_target(
        anchors,
        source_vertices,
        source_normals,
        target_vertices,
        target_triangles,
        target_regions,
        excluded_target_faces,
        similarity,
        max_distance_um,
        min_normal_dot_fixed,
    )
    if any(int(row["r19_face_index"]) in excluded_target_faces for row in mappings):
        raise SemanticCageError("r20_rejected_face_entered_mapping")
    coverage = [
        {
            "region": region,
            "required_anchor_count": int(anchors_per_region[region]),
            "mapped_anchor_count": sum(1 for row in mappings if row["foundation_region"] == region),
        }
        for region in required_regions
    ]
    mapping_digest = canonical_sha256({"mappings": mappings})
    mapping_base64, mapping_binary_digest = encode_mapping_records(mappings)
    receipt: dict[str, object] = {
        "schema": "kira.r25.semantic_cage_correspondence_diagnostic.v1",
        "status": "DIAGNOSTIC_MAP_COMPUTED_NOT_AN_ACCEPTED_CAGE",
        "bindings": dict(sorted((str(key), str(value)) for key, value in bindings.items())),
        "truth_boundary": [
            "READ_ONLY_DIAGNOSTIC_ONLY",
            "NO_DEFORMATION",
            "NO_CANDIDATE",
            "NO_PELVIC_OR_AFES_TARGET_FIT",
            "NO_BLENDER_AUTHORING_AUTHORITY",
            "NOT_OWNER_ACCEPTED",
        ],
        "required_regions": list(required_regions),
        "r20_excluded_target_face_count": len(excluded_target_faces),
        "r20_excluded_target_face_index_sha256": _index_digest(excluded_target_faces),
        "foundation_lock": dict(lock_summary),
        "global_similarity_alignment": _similarity_receipt(similarity),
        "coverage": coverage,
        "mapping_count": len(mappings),
        "mapping_sha256": mapping_digest,
        "mapping_codec": MAPPING_CODEC,
        "mapping_record_bytes": MAPPING_RECORD.size,
        "mapping_binary_sha256": mapping_binary_digest,
        "mapping_records_base64": mapping_base64,
        "failures": [],
    }
    frame = canonical_receipt.encode_receipt_frame(receipt)
    if canonical_receipt.decode_receipt_frame(frame).payload != receipt:
        raise SemanticCageError("canonical_receipt_roundtrip_failed")
    return receipt
