#!/usr/bin/env python3
"""Pure source-level audit of all twenty R26 nail inventory mappings.

This audit uses only the exact MakeHuman OBJ, ordered target stack, official
skeleton, official weights, pure nail inventory, and the preserved R26 staged
diagnostic.  It does not import Blender, construct geometry, mutate a config,
or run any model/GPU workload.  Source-neighborhood agreement proves whether
the official inventory itself is internally consistent; it does not substitute
for the separately prepared evaluated-body footprint probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_nail_footprint_binding_v1 import (  # noqa: E402
    summarize_footprint_binding,
    validate_all_twenty_bindings,
)
from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    expected_nail_inventory,
)


EXPECTED_CONFIG_SHA256 = (
    "c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"
)
EXPECTED_R26_DIAGNOSTIC_SHA256 = (
    "c5df50067511dbaffcad5f735416e5b1f5777c06670e5784d2f21d409093b4fc"
)
R26_DIAGNOSTIC_PATH = (
    "RecoverySprint/continuation_20260802/"
    "biological_robert_r26_bounded_run/attempt_09_preparation/"
    "nail_modifier_stage_diagnosis/DIAGNOSTIC_RESULT.json"
)
NEAREST_SOURCE_BODY_VERTEX_COUNT = 32


class OfficialNailInventoryAuditError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise OfficialNailInventoryAuditError(
            f"path escapes project root: {path}"
        ) from exc
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_body_obj(path: Path) -> tuple[list[list[float]], set[int]]:
    vertices: list[list[float]] = []
    body_vertex_indices: set[int] = set()
    active_group = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                fields = line.split()
                vertices.append([float(value) for value in fields[1:4]])
            elif line.startswith("g "):
                active_group = line[2:].strip()
            elif line.startswith("f ") and active_group == "body":
                for token in line.split()[1:]:
                    body_vertex_indices.add(int(token.split("/")[0]) - 1)
    if not vertices or not body_vertex_indices:
        raise OfficialNailInventoryAuditError("MakeHuman body OBJ parse was empty")
    return vertices, body_vertex_indices


def target_path_from_report(raw_path: str, target_root: Path) -> Path:
    source = Path(str(raw_path))
    parts = list(source.parts)
    try:
        marker = [value.lower() for value in parts].index("targets")
    except ValueError as exc:
        raise OfficialNailInventoryAuditError(
            f"target report path lacks targets segment: {source}"
        ) from exc
    path = (target_root / Path(*parts[marker + 1 :])).resolve()
    if target_root.resolve() not in path.parents or path.suffix.lower() != ".target":
        raise OfficialNailInventoryAuditError(f"target escapes root: {path}")
    return path


def apply_target(vertices: list[list[float]], path: Path, weight: float) -> int:
    changed = 0
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 4:
                continue
            index = int(fields[0])
            if not 0 <= index < len(vertices):
                raise OfficialNailInventoryAuditError(
                    f"target index outside source: {path}: {index}"
                )
            for axis in range(3):
                vertices[index][axis] += float(fields[axis + 1]) * float(weight)
            changed += 1
    return changed


def source_weights(path: Path, source_count: int) -> list[dict[str, float]]:
    payload = json_file(path)
    rows: list[dict[str, float]] = [defaultdict(float) for _ in range(source_count)]
    for bone_name, assignments in payload["weights"].items():
        for raw_index, raw_weight in assignments:
            index = int(raw_index)
            weight = float(raw_weight)
            if not 0 <= index < source_count:
                raise OfficialNailInventoryAuditError(
                    f"weight index outside source: {index}"
                )
            if weight > 0.0:
                rows[index][str(bone_name)] += weight
    return [dict(row) for row in rows]


def average_points(
    vertices: Sequence[Sequence[float]], indices: Iterable[int]
) -> tuple[float, float, float]:
    values = [int(index) for index in indices]
    if not values:
        raise OfficialNailInventoryAuditError("point average has no indices")
    return tuple(
        sum(float(vertices[index][axis]) for index in values) / len(values)
        for axis in range(3)
    )


def distance(first: Sequence[float], second: Sequence[float]) -> float:
    return math.sqrt(
        sum((float(left) - float(right)) ** 2 for left, right in zip(first, second))
    )


def terminal_point(
    rig: Mapping[str, Any],
    vertices: Sequence[Sequence[float]],
    bone_name: str,
) -> tuple[float, float, float]:
    bone = rig["bones"].get(str(bone_name))
    if not isinstance(bone, Mapping):
        raise OfficialNailInventoryAuditError(
            f"inventory terminal bone absent from official skeleton: {bone_name}"
        )
    return average_points(vertices, rig["joints"][str(bone["tail"])])


def weighted_centroid(
    vertices: Sequence[Sequence[float]],
    weights: Sequence[Mapping[str, float]],
    body_vertex_indices: set[int],
    bone_name: str,
) -> tuple[float, float, float]:
    assignments = [
        (index, float(weights[index].get(bone_name, 0.0)))
        for index in body_vertex_indices
        if float(weights[index].get(bone_name, 0.0)) > 0.0
    ]
    total = sum(weight for _index, weight in assignments)
    if total <= 0.0:
        raise OfficialNailInventoryAuditError(
            f"official terminal bone has no body weights: {bone_name}"
        )
    return tuple(
        sum(float(vertices[index][axis]) * weight for index, weight in assignments)
        / total
        for axis in range(3)
    )


def terminal_names(kind: str, side: str) -> list[str]:
    prefix = "finger" if str(kind) == "fingernail" else "toe"
    return [
        f"{prefix}{digit}-{'2' if prefix == 'toe' and digit == 1 else '3'}.{side}"
        for digit in range(1, 6)
    ]


def audit_source_inventory(
    *,
    vertices: Sequence[Sequence[float]],
    body_vertex_indices: set[int],
    rig: Mapping[str, Any],
    weights: Sequence[Mapping[str, float]],
) -> list[dict[str, Any]]:
    rows = []
    centroids: dict[str, tuple[float, float, float]] = {}
    for definition in expected_nail_inventory():
        bone = str(definition["bone"])
        centroids[bone] = weighted_centroid(
            vertices, weights, body_vertex_indices, bone
        )
    for definition in expected_nail_inventory():
        kind = str(definition["kind"])
        side = str(definition["side"])
        digit = int(definition["digit"])
        bone = str(definition["bone"])
        tail = terminal_point(rig, vertices, bone)
        comparable = terminal_names(kind, side)
        centroid_distances = sorted(
            (distance(tail, centroids[name]), name) for name in comparable
        )
        nearest_vertices = sorted(
            (
                distance(tail, vertices[index]),
                int(index),
            )
            for index in body_vertex_indices
        )[:NEAREST_SOURCE_BODY_VERTEX_COUNT]
        samples = [
            {"influences": weights[index]}
            for _vertex_distance, index in nearest_vertices
        ]
        binding = summarize_footprint_binding(
            nail_id=str(definition["nail_id"]),
            kind=kind,
            digit=digit,
            side=side,
            expected_bone=bone,
            samples=samples,
            policy="source_terminal_neighborhood",
        )
        binding.update(
            {
                "official_terminal_tail_native": list(tail),
                "nearest_source_body_vertex_count": len(nearest_vertices),
                "nearest_source_body_vertex_distance_native_minimum": (
                    nearest_vertices[0][0]
                ),
                "nearest_source_body_vertex_distance_native_maximum": (
                    nearest_vertices[-1][0]
                ),
                "nearest_terminal_weighted_centroid_bone": (
                    centroid_distances[0][1]
                ),
                "expected_terminal_bone_is_nearest_weighted_centroid": (
                    centroid_distances[0][1] == bone
                ),
                "terminal_weighted_centroid_distances_native": [
                    {"bone": name, "distance": value}
                    for value, name in centroid_distances
                ],
                "nearest_source_body_vertices": [
                    {
                        "vertex_index": index,
                        "distance_native": value,
                        "influences": weights[index],
                    }
                    for value, index in nearest_vertices
                ],
                "scope": "official_source_terminal_neighborhood_not_final_R26_footprint",
            }
        )
        rows.append(binding)
    return rows


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise OfficialNailInventoryAuditError(
            f"append-only output already exists: {output_path}"
        )
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise OfficialNailInventoryAuditError("R26 config hash changed")
    config = json_file(config_path)

    base_path = project_path(str(config["inputs"]["makehuman_base_obj"]["path"]))
    skeleton_path = project_path(
        str(config["inputs"]["makehuman_skeleton"]["path"])
    )
    weights_path = project_path(
        str(config["inputs"]["makehuman_weights"]["path"])
    )
    foundation_path = project_path(
        str(config["inputs"]["foundation_report"]["path"])
    )
    bound_inputs = {}
    for name, path in (
        ("makehuman_base_obj", base_path),
        ("makehuman_skeleton", skeleton_path),
        ("makehuman_weights", weights_path),
        ("foundation_report", foundation_path),
    ):
        expected = config["inputs"][name]
        actual = sha256_file(path)
        if actual != str(expected["sha256"]).lower():
            raise OfficialNailInventoryAuditError(f"bound input changed: {name}")
        bound_inputs[name] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }

    vertices, body_vertex_indices = parse_body_obj(base_path)
    foundation = json_file(foundation_path)
    target_root = project_path(
        "Avatar/avatar_builder/tooling/makehuman_official/"
        "makehuman/data/targets"
    )
    target_records = []
    for position, row in enumerate(foundation.get("targets", [])):
        path = target_path_from_report(str(row["path"]), target_root)
        actual = sha256_file(path)
        if actual != str(row["sha256"]).lower():
            raise OfficialNailInventoryAuditError(
                f"ordered target changed at position {position}"
            )
        changed = apply_target(vertices, path, float(row["weight"]))
        if changed != int(row["changed_vertices"]):
            raise OfficialNailInventoryAuditError(
                f"ordered target row count changed at position {position}"
            )
        target_records.append(
            {
                "position": position,
                "path": path.relative_to(target_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": actual,
                "weight": float(row["weight"]),
                "changed_vertices": changed,
            }
        )
    if len(target_records) != 44:
        raise OfficialNailInventoryAuditError(
            f"ordered target stack is not 44 rows: {len(target_records)}"
        )

    rig = json_file(skeleton_path)
    weights = source_weights(weights_path, len(vertices))
    source_records = audit_source_inventory(
        vertices=vertices,
        body_vertex_indices=body_vertex_indices,
        rig=rig,
        weights=weights,
    )
    source_validation = validate_all_twenty_bindings(source_records)
    if not all(
        row["expected_terminal_bone_is_nearest_weighted_centroid"] is True
        for row in source_records
    ):
        raise OfficialNailInventoryAuditError(
            "one or more inventory bones are not nearest their official source weights"
        )

    diagnostic_path = project_path(R26_DIAGNOSTIC_PATH)
    if sha256_file(diagnostic_path) != EXPECTED_R26_DIAGNOSTIC_SHA256:
        raise OfficialNailInventoryAuditError(
            "preserved R26 staged diagnostic changed"
        )
    diagnostic = json_file(diagnostic_path)
    observed = diagnostic["underlying_body_weight_inventory"]
    observed_definition = next(
        row
        for row in expected_nail_inventory()
        if row["nail_id"] == diagnostic["target"]["nail_id"]
    )
    observed_binding = summarize_footprint_binding(
        nail_id=str(observed_definition["nail_id"]),
        kind=str(observed_definition["kind"]),
        digit=int(observed_definition["digit"]),
        side=str(observed_definition["side"]),
        expected_bone=str(observed_definition["bone"]),
        samples=observed["body_vertices"],
        policy="final_nail_footprint",
    )
    if observed_binding["passed"] is not False:
        raise OfficialNailInventoryAuditError(
            "preserved R26 footprint mismatch was not reproduced"
        )

    gates = {
        "exact_44_target_stack_verified": len(target_records) == 44,
        "exact_20_source_inventory_rows": len(source_records) == 20,
        "all_20_official_source_terminal_neighborhoods_match_inventory": all(
            row["passed"] is True for row in source_records
        ),
        "all_20_inventory_bones_nearest_their_official_weight_centroid": all(
            row["expected_terminal_bone_is_nearest_weighted_centroid"] is True
            for row in source_records
        ),
        "preserved_R26_finger5_L_footprint_rejected": observed_binding["passed"]
        is False,
        "preserved_R26_finger5_L_winning_family_is_finger4_L": (
            observed_binding["winning_digit_family"] == "finger4.L"
        ),
        "no_automatic_bone_remap": observed_binding[
            "automatic_bone_remap_performed"
        ]
        is False,
    }
    if not all(gates.values()):
        raise OfficialNailInventoryAuditError(
            "one or more source mapping audit gates failed"
        )

    payload = {
        "schema": "kira.avatar.robert_r26_official_nail_inventory_mapping_audit.v1",
        "created_utc": utc_now(),
        "status": (
            "PASS_OFFICIAL_SOURCE_MAPPING_AND_CONFIRM_R26_TRANSFER_OR_PROJECTION_MISMATCH"
        ),
        "scope": "pure_read_only_no_Blender_no_candidate_no_mutation",
        "config": {
            "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": config_path.stat().st_size,
            "sha256": sha256_file(config_path),
            "rebound": False,
        },
        "bound_inputs": bound_inputs,
        "ordered_targets": target_records,
        "source_vertex_count": len(vertices),
        "source_body_group_vertex_count": len(body_vertex_indices),
        "source_neighborhood_vertex_count_per_nail": (
            NEAREST_SOURCE_BODY_VERTEX_COUNT
        ),
        "source_mapping_records": source_records,
        "source_all_twenty_validation": source_validation,
        "preserved_R26_diagnostic": {
            "path": diagnostic_path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": diagnostic_path.stat().st_size,
            "sha256": sha256_file(diagnostic_path),
            "status": diagnostic["status"],
        },
        "preserved_R26_observed_footprint_binding": observed_binding,
        "conclusion": {
            "official_inventory_mapping_is_internally_consistent": True,
            "remap_fingernail_5_L_to_finger4_is_supported": False,
            "R26_downstream_transfer_or_projection_requires_all20_audit": True,
            "evaluated_body_surface_must_be_used_for_final_nail_construction": True,
        },
        "gates": gates,
        "candidate_created": False,
        "blend_opened_saved_or_rendered": False,
        "config_or_prior_evidence_modified": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
