"""Append-only R20 Attempt 05 patch-wide metric repair.

This module deliberately leaves the sealed Attempt 04 contract byte-for-byte
unchanged.  It captures that contract's final external-surface constructor and
then moves only its 740 generated vertices, tangentially and within bounded
regional caps.  The exact 34 source seam vertices, topology, candidate
parameters, and external-feature scalar field are unchanged.

There is no Blender import and no file, render, runtime, or GPU operation here.
The surface remains external review geometry; this module does not implement
internal urinary, digestive, reproductive, pregnancy, or hospital physiology.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Sequence

from Core import kira_r20_curvilinear_pelvic_patch as _sealed


METHOD_ID = "KIRA_R20_ATTEMPT05_BOUNDED_TANGENTIAL_METRIC_REPAIR_V1"
_SEALED_BUILD_POSITIONS = _sealed.build_positions

EXPECTED_SEAM_INPUT_SHA256 = "305b3becb6d011cc597f4e1855ad4c08ed63f064f4b5b606d49f69469cb78c9c"
EXPECTED_EXTERIOR_1_INPUT_SHA256 = "52ff29c68ab35366ea36da0a09493669be45cbf2d1d359ad6b8d0e68d515adb3"
EXPECTED_EXTERIOR_2_INPUT_SHA256 = "fec13652c6ab71cca3831771f1a93177c38fc6f31f12323ac78031e19e7eab23"
EXPECTED_NORMAL_INPUT_SHA256 = "4fa274e21cf513c205e615a38381ca5da253a09d706868bbf594585abe262440"

MAXIMUM_SWEEPS = 2048
ADAM_LEARNING_RATE_M = 5.0e-5
ADAM_BETA_1 = 0.9
ADAM_BETA_2 = 0.999
ADAM_EPSILON = 1.0e-8
EDGE_BARRIER_RATIO = 2.70
INTERNAL_ACCEPTANCE_RATIO = 2.90
SIGNED_TRIANGLE_MARGIN_M2 = 2.0e-7
MUTUAL_TRIANGLE_COSINE_TARGET = 0.05
MINIMUM_FACE_AREA_M2 = 1.0e-10
MAXIMUM_FROZEN_NORMAL_DRIFT_M = 1.0e-12
MAXIMUM_LANDMARK_CENTROID_DRIFT_EDGE_FRACTION = 0.10
LANDMARK_CENTROID_PENALTY_WEIGHT = 0.10

COLLAR_1_CAP_EDGE_FRACTION = 0.12
COLLAR_2_CAP_EDGE_FRACTION = 0.18
CORE_PERIMETER_CAP_EDGE_FRACTION = 0.30
# This is deliberately tighter than the originally proposed 0.35e general
# interior cap.  Every core-interior point, not merely a selected peak, stays
# within the clinical-region 0.20e bound measured by the strict prototype.
CORE_INTERIOR_CAP_EDGE_FRACTION = 0.20

Vec3 = tuple[float, float, float]


def __getattr__(name: str) -> Any:
    """Delegate every unchanged public contract member to sealed Attempt 04."""

    return getattr(_sealed, name)


def _v3(value: Sequence[float]) -> Vec3:
    if len(value) != 3:
        raise ValueError("R20 Attempt 05 requires three-coordinate positions")
    result = tuple(float(component) for component in value)
    if not all(math.isfinite(component) for component in result):
        raise ValueError("R20 Attempt 05 received a non-finite coordinate")
    return result  # type: ignore[return-value]


def _add(first: Vec3, second: Vec3) -> Vec3:
    return tuple(first[axis] + second[axis] for axis in range(3))  # type: ignore[return-value]


def _sub(first: Vec3, second: Vec3) -> Vec3:
    return tuple(first[axis] - second[axis] for axis in range(3))  # type: ignore[return-value]


def _scale(value: Vec3, scalar: float) -> Vec3:
    return tuple(value[axis] * scalar for axis in range(3))  # type: ignore[return-value]


def _dot(first: Vec3, second: Vec3) -> float:
    return sum(first[axis] * second[axis] for axis in range(3))


def _cross(first: Vec3, second: Vec3) -> Vec3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _length(value: Vec3) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: Vec3, label: str) -> Vec3:
    magnitude = _length(value)
    if magnitude <= 1.0e-12:
        raise ValueError(f"{label} collapsed")
    return _scale(value, 1.0 / magnitude)


def _mean(values: Iterable[Vec3]) -> Vec3:
    rows = tuple(values)
    if not rows:
        raise ValueError("cannot average an empty position set")
    return tuple(sum(row[axis] for row in rows) / len(rows) for axis in range(3))  # type: ignore[return-value]


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _input_sha256(values: Sequence[Sequence[float]]) -> str:
    return _canonical_sha256([[float(component) for component in row] for row in values])


def _add_scaled(target: list[list[float]], index: int, value: Vec3, scalar: float) -> None:
    for axis in range(3):
        target[index][axis] += scalar * value[axis]


def _triangle_gradient(
    gradient: list[list[float]],
    positions: Sequence[Vec3],
    indices: tuple[int, int, int],
    vector_derivative: Vec3,
    coefficient: float,
) -> None:
    first, second, third = indices
    _add_scaled(
        gradient,
        first,
        _cross(_sub(positions[second], positions[third]), vector_derivative),
        coefficient,
    )
    _add_scaled(
        gradient,
        second,
        _cross(_sub(positions[third], positions[first]), vector_derivative),
        coefficient,
    )
    _add_scaled(
        gradient,
        third,
        _cross(_sub(positions[first], positions[second]), vector_derivative),
        coefficient,
    )


def _reference_frames(
    positions: Sequence[Vec3], faces: Sequence[tuple[int, int, int, int]]
) -> tuple[tuple[Vec3, ...], tuple[Vec3, ...]]:
    face_normals: list[Vec3] = []
    vertex_sums = [[0.0, 0.0, 0.0] for _ in positions]
    for face_index, face in enumerate(faces):
        first, second, third, fourth = (positions[index] for index in face)
        triangle_1 = _cross(_sub(second, first), _sub(third, first))
        triangle_2 = _cross(_sub(third, first), _sub(fourth, first))
        normal = _normalize(_add(triangle_1, triangle_2), f"reference face {face_index} normal")
        face_normals.append(normal)
        for vertex_index in face:
            _add_scaled(vertex_sums, vertex_index, normal, 1.0)
    vertex_normals = tuple(
        _normalize(tuple(value), f"reference vertex {index} normal")
        for index, value in enumerate(vertex_sums)
    )
    return tuple(face_normals), vertex_normals


def _strict_metrics(
    positions: Sequence[Vec3],
    faces: Sequence[tuple[int, int, int, int]],
    reference_face_normals: Sequence[Vec3],
) -> dict[str, Any]:
    ratios: list[float] = []
    areas: list[float] = []
    signed_1: list[float] = []
    signed_2: list[float] = []
    mutual_dots: list[float] = []
    mutual_cosines: list[float] = []
    minimum_edge = math.inf
    for face, reference_normal in zip(faces, reference_face_normals):
        first, second, third, fourth = (positions[index] for index in face)
        edge_vectors = (
            _sub(second, first),
            _sub(third, second),
            _sub(fourth, third),
            _sub(first, fourth),
        )
        lengths = tuple(_length(value) for value in edge_vectors)
        face_minimum = min(lengths)
        minimum_edge = min(minimum_edge, face_minimum)
        ratios.append(max(lengths) / face_minimum if face_minimum > 0.0 else math.inf)
        triangle_1 = _cross(_sub(second, first), _sub(third, first))
        triangle_2 = _cross(_sub(third, first), _sub(fourth, first))
        length_1 = _length(triangle_1)
        length_2 = _length(triangle_2)
        areas.append(0.5 * (length_1 + length_2))
        signed_1.append(_dot(triangle_1, reference_normal))
        signed_2.append(_dot(triangle_2, reference_normal))
        mutual = _dot(triangle_1, triangle_2)
        mutual_dots.append(mutual)
        mutual_cosines.append(mutual / max(length_1 * length_2, 1.0e-24))
    exact_duplicate_count = len(positions) - len(set(positions))
    return {
        "face_count": len(faces),
        "maximum_quad_edge_ratio": max(ratios),
        "edge_ratio_violation_count_at_3": sum(value > 3.0 for value in ratios),
        "minimum_edge_length_m": minimum_edge,
        "minimum_face_area_m2": min(areas),
        "degenerate_face_count_at_1e_10_m2": sum(value <= MINIMUM_FACE_AREA_M2 for value in areas),
        "triangle_1_nonpositive_signed_count": sum(value <= 0.0 for value in signed_1),
        "triangle_2_nonpositive_signed_count": sum(value <= 0.0 for value in signed_2),
        "mutual_triangle_negative_dot_count": sum(value < 0.0 for value in mutual_dots),
        "minimum_triangle_1_signed_area2_m2": min(signed_1),
        "minimum_triangle_2_signed_area2_m2": min(signed_2),
        "minimum_mutual_triangle_cosine": min(mutual_cosines),
        "exact_duplicate_position_count": exact_duplicate_count,
        "all_756_edge_ratios": ratios,
        "all_756_face_areas_m2": areas,
    }


def _hard_pass(metrics: dict[str, Any]) -> bool:
    return (
        metrics["maximum_quad_edge_ratio"] <= INTERNAL_ACCEPTANCE_RATIO
        and metrics["edge_ratio_violation_count_at_3"] == 0
        and metrics["minimum_face_area_m2"] > MINIMUM_FACE_AREA_M2
        and metrics["degenerate_face_count_at_1e_10_m2"] == 0
        and metrics["triangle_1_nonpositive_signed_count"] == 0
        and metrics["triangle_2_nonpositive_signed_count"] == 0
        and metrics["mutual_triangle_negative_dot_count"] == 0
        and metrics["exact_duplicate_position_count"] == 0
    )


def _movement_caps(edge_scale: float) -> tuple[float, ...]:
    perimeter = set(_sealed.core_perimeter_indices())
    caps = [0.0 for _index in range(_sealed.TOTAL_PATCH_INCIDENT_VERTICES)]
    for index in range(_sealed.COLLAR_1_OFFSET, _sealed.COLLAR_2_OFFSET):
        caps[index] = COLLAR_1_CAP_EDGE_FRACTION * edge_scale
    for index in range(_sealed.COLLAR_2_OFFSET, _sealed.CORE_OFFSET):
        caps[index] = COLLAR_2_CAP_EDGE_FRACTION * edge_scale
    for index in range(_sealed.CORE_OFFSET, _sealed.TOTAL_PATCH_INCIDENT_VERTICES):
        fraction = (
            CORE_PERIMETER_CAP_EDGE_FRACTION
            if index in perimeter
            else CORE_INTERIOR_CAP_EDGE_FRACTION
        )
        caps[index] = fraction * edge_scale
    return tuple(caps)


def _landmark_centroid_drift(
    before: Sequence[Vec3], after: Sequence[Vec3]
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    maximum = 0.0
    for name, indices in sorted(_sealed.landmark_vertex_sets().items()):
        source = _mean(before[index] for index in indices)
        repaired = _mean(after[index] for index in indices)
        drift = _length(_sub(repaired, source))
        maximum = max(maximum, drift)
        records[name] = {
            "before_project_m": list(source),
            "after_project_m": list(repaired),
            "drift_m": drift,
        }
    return {"maximum_drift_m": maximum, "landmarks": records}


def _feature_scalar_record(candidate: Any) -> dict[str, Any]:
    vertices: list[dict[str, Any]] = []
    for row in range(_sealed.CORE_ROWS):
        for column in range(_sealed.CORE_COLUMNS):
            taper = _sealed._feature_taper(row, column)
            raw_terms = _sealed.external_feature_components(
                _sealed.U_STATIONS[column],
                _sealed.V_STATIONS[row],
                asymmetry=candidate.asymmetry,
            )
            terms = {
                name: candidate.feature_scale * value * taper
                for name, value in sorted(raw_terms.items())
            }
            vertices.append(
                {
                    "vertex_index": _sealed.core_index(row, column),
                    "row": row,
                    "column": column,
                    "u": _sealed.U_STATIONS[column],
                    "v": _sealed.V_STATIONS[row],
                    "taper": taper,
                    "terms_m": terms,
                    "total_m": sum(terms.values()),
                }
            )
    order_v: list[tuple[str, float]] = []
    order_terms = {
        "clitoral_hood_and_restrained_glans": ("clitoral_hood_and_restrained_glans",),
        "external_urethral_meatus": ("urethral_meatus_rim", "urethral_meatus_blind_cap"),
        "vaginal_opening_introitus": ("vaginal_opening_rim", "vaginal_opening_blind_cap"),
        "posterior_fourchette": ("posterior_fourchette",),
        "continuous_perineum": ("continuous_perineum",),
        "separate_anal_region": ("anal_rim", "anal_blind_cap"),
    }
    for name in _sealed.EXTERNAL_LANDMARK_ORDER:
        keys = order_terms[name]
        weighted = [
            (record["v"], sum(abs(record["terms_m"][key]) for key in keys))
            for record in vertices
        ]
        denominator = sum(weight for _v, weight in weighted)
        if denominator <= 0.0:
            raise ValueError(f"external feature scalar field is empty for {name}")
        order_v.append((name, sum(v * weight for v, weight in weighted) / denominator))
    if [name for name, _value in order_v] != list(_sealed.EXTERNAL_LANDMARK_ORDER):
        raise AssertionError("external landmark name order drifted")
    if any(first[1] >= second[1] for first, second in zip(order_v, order_v[1:])):
        raise ValueError("external landmark longitudinal scalar order failed")
    payload = {
        "candidate_id": candidate.candidate_id,
        "vertices": vertices,
        "longitudinal_weighted_v_order": [
            {"name": name, "weighted_v": value} for name, value in order_v
        ],
    }
    return {"sha256": _canonical_sha256(payload), "payload": payload}


def _bounded_metric_repair(
    initial_positions: Sequence[Vec3],
    candidate: Any,
) -> tuple[tuple[Vec3, ...], dict[str, Any]]:
    faces = tuple(_sealed.build_quad_topology(reverse_winding=False))
    reference = tuple(_v3(value) for value in initial_positions)
    reference_face_normals, reference_vertex_normals = _reference_frames(reference, faces)
    edge_scale = _sealed.closed_cycle_median_edge_scale(reference[: _sealed.SEAM_COUNT])
    caps = _movement_caps(edge_scale)
    landmark_groups = tuple(sorted(_sealed.landmark_vertex_sets().items()))
    landmark_drift_limit = edge_scale * MAXIMUM_LANDMARK_CENTROID_DRIFT_EDGE_FRACTION
    positions = [list(value) for value in reference]
    first_moment = [[0.0, 0.0, 0.0] for _value in reference]
    second_moment = [[0.0, 0.0, 0.0] for _value in reference]
    journal: list[dict[str, Any]] = []
    feature_record = _feature_scalar_record(candidate)
    pre_metrics = _strict_metrics(reference, faces, reference_face_normals)
    accepted_metrics: dict[str, Any] | None = None
    accepted_sweep: int | None = None

    for sweep in range(1, MAXIMUM_SWEEPS + 1):
        current = tuple(tuple(value) for value in positions)  # type: ignore[arg-type]
        gradient = [[0.0, 0.0, 0.0] for _value in current]
        face_count = len(faces)

        for face_index, (face, reference_normal) in enumerate(zip(faces, reference_face_normals)):
            indices = tuple(face)
            points = tuple(current[index] for index in indices)
            edge_vectors = tuple(
                _sub(points[(slot + 1) % 4], points[slot]) for slot in range(4)
            )
            edge_lengths = tuple(max(_length(vector), 1.0e-9) for vector in edge_vectors)
            edge_logs = tuple(math.log(value) for value in edge_lengths)
            mean_log = sum(edge_logs) / 4.0
            log_gradient = [
                2.0 * (value - mean_log) / (4.0 * face_count) for value in edge_logs
            ]
            maximum_slot = max(range(4), key=lambda slot: (edge_logs[slot], -slot))
            minimum_slot = min(range(4), key=lambda slot: (edge_logs[slot], slot))
            spread = edge_logs[maximum_slot] - edge_logs[minimum_slot]
            barrier_excess = spread - math.log(EDGE_BARRIER_RATIO)
            if barrier_excess > 0.0:
                coefficient = 200.0 * barrier_excess / face_count
                log_gradient[maximum_slot] += coefficient
                log_gradient[minimum_slot] -= coefficient
            for slot in range(4):
                first_index = indices[slot]
                second_index = indices[(slot + 1) % 4]
                derivative = _scale(
                    edge_vectors[slot],
                    -log_gradient[slot] / (edge_lengths[slot] * edge_lengths[slot]),
                )
                _add_scaled(gradient, first_index, derivative, 1.0)
                _add_scaled(gradient, second_index, derivative, -1.0)

            first, second, third, fourth = points
            triangle_1 = _cross(_sub(second, first), _sub(third, first))
            triangle_2 = _cross(_sub(third, first), _sub(fourth, first))
            signed_1 = _dot(triangle_1, reference_normal)
            signed_2 = _dot(triangle_2, reference_normal)
            if signed_1 < SIGNED_TRIANGLE_MARGIN_M2:
                coefficient = (
                    -200.0
                    * (SIGNED_TRIANGLE_MARGIN_M2 - signed_1)
                    / (face_count * 1.0e-10)
                )
                _triangle_gradient(
                    gradient,
                    current,
                    (indices[0], indices[1], indices[2]),
                    reference_normal,
                    coefficient,
                )
            if signed_2 < SIGNED_TRIANGLE_MARGIN_M2:
                coefficient = (
                    -200.0
                    * (SIGNED_TRIANGLE_MARGIN_M2 - signed_2)
                    / (face_count * 1.0e-10)
                )
                _triangle_gradient(
                    gradient,
                    current,
                    (indices[0], indices[2], indices[3]),
                    reference_normal,
                    coefficient,
                )

            length_1 = max(_length(triangle_1), 1.0e-12)
            length_2 = max(_length(triangle_2), 1.0e-12)
            cosine = _dot(triangle_1, triangle_2) / (length_1 * length_2)
            if cosine < MUTUAL_TRIANGLE_COSINE_TARGET:
                coefficient = (
                    -40.0
                    * (MUTUAL_TRIANGLE_COSINE_TARGET - cosine)
                    / face_count
                )
                derivative_1 = _sub(
                    _scale(triangle_2, 1.0 / (length_1 * length_2)),
                    _scale(triangle_1, cosine / (length_1 * length_1)),
                )
                derivative_2 = _sub(
                    _scale(triangle_1, 1.0 / (length_1 * length_2)),
                    _scale(triangle_2, cosine / (length_2 * length_2)),
                )
                _triangle_gradient(
                    gradient,
                    current,
                    (indices[0], indices[1], indices[2]),
                    derivative_1,
                    coefficient,
                )
                _triangle_gradient(
                    gradient,
                    current,
                    (indices[0], indices[2], indices[3]),
                    derivative_2,
                    coefficient,
                )

        for index in range(_sealed.SEAM_COUNT, len(current)):
            displacement = _sub(current[index], reference[index])
            tether_scale = 0.004 / (caps[index] * caps[index] * _sealed.NEW_VERTEX_COUNT)
            _add_scaled(gradient, index, displacement, tether_scale)

        # Preserve the already accepted clinical feature locations as groups,
        # while still allowing bounded within-group tangential redistribution.
        for _name, indices in landmark_groups:
            drift = _sub(
                _mean(current[index] for index in indices),
                _mean(reference[index] for index in indices),
            )
            coefficient = (
                2.0
                * LANDMARK_CENTROID_PENALTY_WEIGHT
                / (len(landmark_groups) * len(indices) * landmark_drift_limit**2)
            )
            for index in indices:
                _add_scaled(gradient, index, drift, coefficient)

        for index in range(len(current)):
            normal = reference_vertex_normals[index]
            projected = _sub(tuple(gradient[index]), _scale(normal, _dot(tuple(gradient[index]), normal)))
            if index < _sealed.SEAM_COUNT:
                projected = (0.0, 0.0, 0.0)
            for axis in range(3):
                first_moment[index][axis] = (
                    ADAM_BETA_1 * first_moment[index][axis]
                    + (1.0 - ADAM_BETA_1) * projected[axis]
                )
                second_moment[index][axis] = (
                    ADAM_BETA_2 * second_moment[index][axis]
                    + (1.0 - ADAM_BETA_2) * projected[axis] * projected[axis]
                )
                corrected_first = first_moment[index][axis] / (1.0 - ADAM_BETA_1**sweep)
                corrected_second = second_moment[index][axis] / (1.0 - ADAM_BETA_2**sweep)
                positions[index][axis] -= (
                    ADAM_LEARNING_RATE_M
                    * corrected_first
                    / (math.sqrt(corrected_second) + ADAM_EPSILON)
                )

        for index in range(len(current)):
            if index < _sealed.SEAM_COUNT:
                positions[index] = list(reference[index])
                continue
            displacement = _sub(tuple(positions[index]), reference[index])
            normal = reference_vertex_normals[index]
            displacement = _sub(displacement, _scale(normal, _dot(displacement, normal)))
            magnitude = _length(displacement)
            if magnitude > caps[index]:
                displacement = _scale(displacement, caps[index] / magnitude)
            positions[index] = list(_add(reference[index], displacement))

        if sweep % 8 == 0 or sweep == MAXIMUM_SWEEPS:
            current = tuple(tuple(value) for value in positions)  # type: ignore[arg-type]
            metrics = _strict_metrics(current, faces, reference_face_normals)
            if sweep % 128 == 0 or _hard_pass(metrics):
                journal.append(
                    {
                        "sweep": sweep,
                        "maximum_quad_edge_ratio": metrics["maximum_quad_edge_ratio"],
                        "edge_ratio_violation_count_at_3": metrics[
                            "edge_ratio_violation_count_at_3"
                        ],
                        "minimum_face_area_m2": metrics["minimum_face_area_m2"],
                        "triangle_1_nonpositive_signed_count": metrics[
                            "triangle_1_nonpositive_signed_count"
                        ],
                        "triangle_2_nonpositive_signed_count": metrics[
                            "triangle_2_nonpositive_signed_count"
                        ],
                        "mutual_triangle_negative_dot_count": metrics[
                            "mutual_triangle_negative_dot_count"
                        ],
                        "minimum_mutual_triangle_cosine": metrics[
                            "minimum_mutual_triangle_cosine"
                        ],
                    }
                )
            if _hard_pass(metrics):
                accepted_sweep = sweep
                accepted_metrics = metrics
                break

    if accepted_sweep is None or accepted_metrics is None:
        final = tuple(tuple(value) for value in positions)  # type: ignore[arg-type]
        failure_metrics = _strict_metrics(final, faces, reference_face_normals)
        raise ValueError(
            "Attempt 05 bounded metric repair did not converge within "
            f"{MAXIMUM_SWEEPS} sweeps: {failure_metrics}"
        )

    repaired = tuple(tuple(value) for value in positions)  # type: ignore[arg-type]
    if repaired[: _sealed.SEAM_COUNT] != reference[: _sealed.SEAM_COUNT]:
        raise AssertionError("Attempt 05 changed an immutable seam position")
    cap_violations = []
    displacement_records = []
    maximum_normal_drift = 0.0
    for index, (before, after, cap, normal) in enumerate(
        zip(reference, repaired, caps, reference_vertex_normals)
    ):
        displacement = _sub(after, before)
        magnitude = _length(displacement)
        normal_component = _dot(displacement, normal)
        maximum_normal_drift = max(maximum_normal_drift, abs(normal_component))
        if magnitude > cap + 1.0e-12:
            cap_violations.append(index)
        displacement_records.append(
            {
                "vertex_index": index,
                "vector_project_m": list(displacement),
                "magnitude_m": magnitude,
                "frozen_normal_component_m": normal_component,
                "cap_m": cap,
            }
        )
    if cap_violations:
        raise AssertionError(f"Attempt 05 displacement cap failed: {cap_violations[:8]}")
    if maximum_normal_drift > MAXIMUM_FROZEN_NORMAL_DRIFT_M:
        raise AssertionError("Attempt 05 altered the frozen-normal feature component")

    landmark_drift = _landmark_centroid_drift(reference, repaired)
    landmark_limit = edge_scale * MAXIMUM_LANDMARK_CENTROID_DRIFT_EDGE_FRACTION
    if landmark_drift["maximum_drift_m"] > landmark_limit:
        raise ValueError(
            "Attempt 05 landmark centroid drift exceeded the bounded clinical limit: "
            f"{landmark_drift['maximum_drift_m']} > {landmark_limit}"
        )

    evidence = {
        "repair_method_id": METHOD_ID,
        "candidate_id": candidate.candidate_id,
        "sweeps_used": accepted_sweep,
        "maximum_sweeps": MAXIMUM_SWEEPS,
        "optimizer": {
            "type": "deterministic analytic Adam with frozen-tangent projection",
            "learning_rate_m": ADAM_LEARNING_RATE_M,
            "beta_1": ADAM_BETA_1,
            "beta_2": ADAM_BETA_2,
            "epsilon": ADAM_EPSILON,
            "edge_barrier_ratio": EDGE_BARRIER_RATIO,
            "internal_acceptance_ratio": INTERNAL_ACCEPTANCE_RATIO,
            "signed_triangle_margin_m2": SIGNED_TRIANGLE_MARGIN_M2,
            "mutual_triangle_cosine_target": MUTUAL_TRIANGLE_COSINE_TARGET,
            "landmark_centroid_penalty_weight": LANDMARK_CENTROID_PENALTY_WEIGHT,
            "iteration_order": "sweep, face index, edge slot, vertex index",
            "randomness_used": False,
        },
        "edge_scale_m": edge_scale,
        "regional_caps_m": {
            "collar_1": COLLAR_1_CAP_EDGE_FRACTION * edge_scale,
            "collar_2": COLLAR_2_CAP_EDGE_FRACTION * edge_scale,
            "core_perimeter": CORE_PERIMETER_CAP_EDGE_FRACTION * edge_scale,
            "all_core_interior_clinical": CORE_INTERIOR_CAP_EDGE_FRACTION * edge_scale,
        },
        "input_positions_sha256": _canonical_sha256(reference),
        "output_positions_sha256": _canonical_sha256(repaired),
        "feature_scalar_field_sha256": feature_record["sha256"],
        "feature_scalar_field": feature_record["payload"],
        "feature_scalar_values_or_station_order_changed": False,
        "frozen_normal_feature_component_preserved": True,
        "maximum_absolute_frozen_normal_drift_m": maximum_normal_drift,
        "landmark_centroid_drift": landmark_drift,
        "landmark_centroid_drift_limit_m": landmark_limit,
        "pre_repair_strict_metrics": pre_metrics,
        "post_repair_strict_metrics": accepted_metrics,
        "iteration_journal": journal,
        "all_774_displacement_records": displacement_records,
        "exact_34_seam_positions_preserved": True,
        "new_vertex_count": _sealed.NEW_VERTEX_COUNT,
        "face_count": _sealed.REPLACEMENT_FACE_COUNT,
        "connectivity_sha256": _sealed.topology_contract()["connectivity_sha256"],
        "bmesh_called": False,
        "mesh_edited": False,
        "blend_saved": False,
    }
    return repaired, evidence


def build_positions(
    seam_points: Sequence[Sequence[float]],
    exterior_ring_1: Sequence[Sequence[float]],
    exterior_ring_2: Sequence[Sequence[float]],
    seam_normals: Sequence[Sequence[float]],
    candidate: Any,
) -> tuple[tuple[Vec3, ...], dict[str, Any]]:
    """Build the sealed final surface, then apply the bounded tangent repair."""

    input_hashes = {
        "seam": _input_sha256(seam_points),
        "exterior_ring_1": _input_sha256(exterior_ring_1),
        "exterior_ring_2": _input_sha256(exterior_ring_2),
        "seam_normals": _input_sha256(seam_normals),
    }
    expected = {
        "seam": EXPECTED_SEAM_INPUT_SHA256,
        "exterior_ring_1": EXPECTED_EXTERIOR_1_INPUT_SHA256,
        "exterior_ring_2": EXPECTED_EXTERIOR_2_INPUT_SHA256,
        "seam_normals": EXPECTED_NORMAL_INPUT_SHA256,
    }
    if input_hashes != expected:
        raise ValueError(
            "Attempt 05 is licensed only for the exact hash-bound R19 construction inputs: "
            f"{input_hashes}"
        )
    sealed_positions, sealed_evidence = _SEALED_BUILD_POSITIONS(
        seam_points,
        exterior_ring_1,
        exterior_ring_2,
        seam_normals,
        candidate,
    )
    repaired, repair_evidence = _bounded_metric_repair(sealed_positions, candidate)
    return repaired, {
        "method_id": METHOD_ID,
        "sealed_attempt04_constructor_method_id": sealed_evidence.get("method_id"),
        "sealed_attempt04_geometry_construction": sealed_evidence,
        "exact_construction_input_sha256": input_hashes,
        "patchwide_quality_repair": repair_evidence,
        "candidate_parameters_changed": False,
        "topology_changed": False,
        "seam_changed": False,
        "acceptance_threshold_changed": False,
        "external_surface_only": True,
        "internal_physiology_claimed": False,
    }
