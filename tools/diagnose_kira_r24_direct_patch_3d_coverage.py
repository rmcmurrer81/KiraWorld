"""Read-only 3D domain/coverage diagnosis for the exact embedded R19 patch."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r24_patch_chart_diagnostic/"
    "attempt_02/PATCH_CHART_DIAGNOSTIC.json"
)
INPUT_SHA256 = "fac55acd2e980a16c87f0a82b709c6cb2f7016111d0fef41ce85acda32aaceef"
OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r24_direct_subdivision_surface/"
    "domain_coverage_diagnostic"
)

TARGETS = (
    ("clitoral_hood_glans", 0.285, 0.060),
    ("urethral_meatus", 0.390, 0.045),
    ("vaginal_introitus", 0.550, 0.085),
    ("posterior_fourchette", 0.680, 0.055),
    ("external_perineum", 0.780, 0.080),
    ("anal_verge", 0.900, 0.060),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def allocate_output() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 100):
        candidate = OUTPUT_ROOT / f"attempt_{number:02d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("no append-only 3D-coverage diagnostic slot remains")


def add(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(first[index] + second[index] for index in range(3))


def subtract(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(first[index] - second[index] for index in range(3))


def multiply(value: tuple[float, float, float], scalar: float) -> tuple[float, float, float]:
    return tuple(component * scalar for component in value)


def dot(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return sum(first[index] * second[index] for index in range(3))


def length(value: tuple[float, float, float]) -> float:
    return math.sqrt(dot(value, value))


def distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return length(subtract(first, second))


def weighted_vector(records: list[dict], weights: list[float], key: str) -> tuple[float, float, float]:
    total = sum(weights)
    if total <= 1.0e-12:
        raise RuntimeError("zero coverage-diagnostic weight")
    return tuple(
        sum(float(record[key][axis]) * weight for record, weight in zip(records, weights)) / total
        for axis in range(3)
    )


def nearest_polyline_parameter(
    point: tuple[float, float, float],
    controls: list[tuple[float, float, float]],
    cumulative: list[float],
) -> tuple[float, float]:
    best: tuple[float, float] | None = None
    total = cumulative[-1]
    for index in range(len(controls) - 1):
        first, second = controls[index], controls[index + 1]
        segment = subtract(second, first)
        denominator = max(dot(segment, segment), 1.0e-18)
        alpha = max(0.0, min(1.0, dot(subtract(point, first), segment) / denominator))
        closest = add(first, multiply(segment, alpha))
        separation = distance(point, closest)
        path = cumulative[index] + alpha * (cumulative[index + 1] - cumulative[index])
        candidate = (separation, path / total)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise RuntimeError("3D centerline has no segment")
    return best


def point_on_polyline(
    parameter: float,
    controls: list[tuple[float, float, float]],
    cumulative: list[float],
) -> tuple[float, float, float]:
    target = max(0.0, min(1.0, parameter)) * cumulative[-1]
    for index in range(len(controls) - 1):
        if target <= cumulative[index + 1] or index == len(controls) - 2:
            span = max(cumulative[index + 1] - cumulative[index], 1.0e-18)
            alpha = (target - cumulative[index]) / span
            return add(controls[index], multiply(subtract(controls[index + 1], controls[index]), alpha))
    return controls[-1]


def main() -> None:
    if not INPUT.is_file() or sha256(INPUT) != INPUT_SHA256:
        raise RuntimeError("bound patch-chart diagnostic drifted")
    output = allocate_output()
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    records = []
    for item in source["vertex_records"]:
        records.append(
            {
                "vertex": int(item["vertex"]),
                "world": tuple(map(float, item["world"])),
                "normal_world": tuple(map(float, item["normal_world"])),
                "u": float(item["chart"]["u"]),
                "v": float(item["chart"]["v"]),
                "seam": bool(item["seam"]),
            }
        )
    v_min = min(record["v"] for record in records)
    v_max = max(record["v"] for record in records)
    for record in records:
        record["projection_t"] = (v_max - record["v"]) / (v_max - v_min)

    anchors = [index / 12.0 for index in range(13)]
    controls = []
    control_records = []
    for anchor in anchors:
        selected = [
            record
            for record in records
            if abs(record["projection_t"] - anchor) <= 0.16 and abs(record["u"]) <= 0.40
        ]
        weights = [
            math.exp(-0.5 * ((record["projection_t"] - anchor) / 0.060) ** 2)
            * math.exp(-0.5 * (record["u"] / 0.20) ** 2)
            for record in selected
        ]
        controls.append(weighted_vector(selected, weights, "world"))
        control_records.append(
            {
                "initial_projection_t": anchor,
                "sample_count": len(selected),
                "world": [round(value, 12) for value in controls[-1]],
            }
        )
    cumulative = [0.0]
    for first, second in zip(controls, controls[1:]):
        cumulative.append(cumulative[-1] + distance(first, second))
    if cumulative[-1] <= 0.06:
        raise RuntimeError("qualified 3D centerline is shorter than 60 mm")

    for record in records:
        separation, arc_t = nearest_polyline_parameter(record["world"], controls, cumulative)
        record["centerline_distance_m"] = separation
        record["arc_t"] = arc_t

    feature_records = {}
    for name, center_t, width_t in TARGETS:
        selected = [
            record
            for record in records
            if abs(record["arc_t"] - center_t) <= width_t * 2.0 and abs(record["u"]) <= 0.32
        ]
        weights = [
            math.exp(-0.5 * ((record["arc_t"] - center_t) / width_t) ** 2)
            * math.exp(-0.5 * (record["u"] / 0.13) ** 2)
            for record in selected
        ]
        world = weighted_vector(selected, weights, "world")
        normal = weighted_vector(selected, weights, "normal_world")
        normal_length = max(length(normal), 1.0e-18)
        normal = tuple(value / normal_length for value in normal)
        feature_records[name] = {
            "target_centerline_arc_t": center_t,
            "sample_count": len(selected),
            "weighted_world_centroid_m": [round(value, 12) for value in world],
            "weighted_world_normal": [round(value, 12) for value in normal],
            "front_facing_component_negative_y": round(-normal[1], 12),
            "posterior_facing_component_positive_y": round(normal[1], 12),
            "centerline_world_target_m": [
                round(value, 12) for value in point_on_polyline(center_t, controls, cumulative)
            ],
        }

    ordered_names = [name for name, _center, _width in TARGETS]
    separations = {}
    for first, second in zip(ordered_names, ordered_names[1:]):
        first_world = tuple(feature_records[first]["weighted_world_centroid_m"])
        second_world = tuple(feature_records[second]["weighted_world_centroid_m"])
        separations[f"{first}__to__{second}"] = {
            "euclidean_m": distance(first_world, second_world),
            "posterior_delta_y_m": second_world[1] - first_world[1],
            "vertical_delta_z_m": second_world[2] - first_world[2],
        }

    anterior_names = ("clitoral_hood_glans", "urethral_meatus", "vaginal_introitus")
    posterior_names = ("posterior_fourchette", "external_perineum", "anal_verge")
    anterior_y = sum(feature_records[name]["weighted_world_centroid_m"][1] for name in anterior_names) / len(anterior_names)
    posterior_y = sum(feature_records[name]["weighted_world_centroid_m"][1] for name in posterior_names) / len(posterior_names)
    anal_y = feature_records["anal_verge"]["weighted_world_centroid_m"][1]
    introitus_y = feature_records["vaginal_introitus"]["weighted_world_centroid_m"][1]
    fourchette_y = feature_records["posterior_fourchette"]["weighted_world_centroid_m"][1]
    perineum_y = feature_records["external_perineum"]["weighted_world_centroid_m"][1]

    gates = {
        "source_patch_has_at_least_140mm_anterior_posterior_y_span": (
            max(record["world"][1] for record in records)
            - min(record["world"][1] for record in records)
        ) >= 0.140,
        "3d_centerline_arc_length_at_least_90mm": cumulative[-1] >= 0.090,
        "posterior_group_at_least_30mm_behind_anterior_group": posterior_y - anterior_y >= 0.030,
        "fourchette_is_posterior_to_introitus": fourchette_y > introitus_y,
        "perineum_is_posterior_to_fourchette": perineum_y > fourchette_y,
        "anal_verge_is_posterior_to_introitus_by_at_least_35mm": anal_y - introitus_y >= 0.035,
        "all_consecutive_3d_feature_centroids_separated_by_at_least_7mm": all(
            record["euclidean_m"] >= 0.007 for record in separations.values()
        ),
        "anterior_features_front_facing": all(
            feature_records[name]["weighted_world_normal"][1] < -0.10
            for name in anterior_names
        ),
        "anal_feature_posterior_or_inferior_facing": (
            feature_records["anal_verge"]["weighted_world_normal"][1] > 0.10
            or feature_records["anal_verge"]["weighted_world_normal"][2] < -0.35
        ),
    }
    world_bounds = {
        axis: {
            "minimum": min(record["world"][offset] for record in records),
            "maximum": max(record["world"][offset] for record in records),
            "span_m": max(record["world"][offset] for record in records)
            - min(record["world"][offset] for record in records),
        }
        for axis, offset in (("x", 0), ("y", 1), ("z", 2))
    }
    report = {
        "schema": "kira.avatar.r24_direct_patch_3d_domain_coverage_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "SOURCE_DOMAIN_3D_COVERAGE_PASS_PROPOSE_CENTERLINE_ARC_REMAP_ONLY"
            if all(gates.values())
            else "SOURCE_DOMAIN_3D_COVERAGE_FAIL_POSTERIOR_REGION_EXPANSION_OR_REVIEW_REQUIRED"
        ),
        "input": {"path": relative(INPUT), "sha256": sha256(INPUT)},
        "source_patch_vertex_count": len(records),
        "source_patch_world_bounds": world_bounds,
        "current_world_z_only_span_m": world_bounds["z"]["span_m"],
        "unused_by_current_t_world_y_span_m": world_bounds["y"]["span_m"],
        "proposed_coordinate": {
            "id": "EXACT_SOURCE_PATCH_3D_CENTERLINE_ARC_V1",
            "initial_ordering": "existing 3D LONGITUDINAL projection combining world Y and Z",
            "centerline": "13 weighted central surface controls from exact source vertices",
            "final_t": "nearest 3D centerline-polyline arc-length parameter",
            "lateral_u": "existing source-bound chart lateral coordinate",
            "surface_positions_remapped": False,
            "surface_normals_replaced_by_fixed_axis": False,
            "donor_used": False,
            "centerline_arc_length_m": cumulative[-1],
            "controls": control_records,
        },
        "semantic_world_coverage": feature_records,
        "consecutive_semantic_separations": separations,
        "aggregate_coverage": {
            "anterior_group_mean_y_m": anterior_y,
            "posterior_group_mean_y_m": posterior_y,
            "posterior_minus_anterior_y_m": posterior_y - anterior_y,
            "anal_minus_introitus_y_m": anal_y - introitus_y,
        },
        "gates": gates,
        "visibility_interpretation": {
            "anal_region_primary_facing": (
                "posterior" if feature_records["anal_verge"]["weighted_world_normal"][1] > 0.10 else "inferior"
            ),
            "rear_view_alone_required": False,
            "dedicated_inferior_view_required": True,
            "reason": (
                "The exact source domain places the anal target posteriorly, but its local surface "
                "normal is inferior-facing; positional posterior coverage and inferior visibility "
                "must be gated separately."
            ),
        },
        "all_gates_pass": all(gates.values()),
        "truth": (
            "Read-only source-domain geometry diagnosis. This does not author, save, activate, "
            "assign, export, or prove anatomy, physiology, elimination, reproduction, sensation, "
            "or runtime function."
        ),
    }
    report_path = output / "DOMAIN_COVERAGE_DIAGNOSTIC.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failed = [name for name, value in gates.items() if not value]
    checkpoint = output / "CHECKPOINT.md"
    checkpoint.write_text(
        f"""# Kira R24 direct patch 3D coverage diagnostic

Status: `{report['status']}`

The exact source patch spans `{world_bounds['y']['span_m'] * 1000:.3f}` mm in
world Y and `{world_bounds['z']['span_m'] * 1000:.3f}` mm in world Z. The
current Attempt 04 coordinate used world Z alone. The proposed coordinate uses
the existing source vertices to build a `{cumulative[-1] * 1000:.3f}` mm 3D
centerline and then uses arc length without remapping surface positions.

Failed coverage gates: `{', '.join(failed) if failed else 'none'}`.

- Input: `{relative(INPUT)}` — SHA-256 `{sha256(INPUT)}`
- Report: `{relative(report_path)}` — SHA-256 `{sha256(report_path)}`

No Blender process ran and no mesh or runtime state changed.
""",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "output": relative(report_path)}))


if __name__ == "__main__":
    main()
