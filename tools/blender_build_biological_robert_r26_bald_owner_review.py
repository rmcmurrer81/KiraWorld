"""Run-locked Biological Robert R26 bald private-body assembler.

This file is intentionally prepared before it is executed.  It cannot mutate a
scene or create an output directory unless the CLI interlocks and the durable,
hash-bound post-Kira release checkpoint all pass.  The intended invocation,
only after Kira's final
Blender operation is complete, is::

    blender --background --python \
      Tools/blender_build_biological_robert_r26_bald_owner_review.py -- \
      --config RecoverySprint/continuation_20260802/\
biological_robert_r26_read_only_preparation/ROBERT_R26_BUILD_CONFIG.json \
      --kira-final-blender-complete \
      --kira-release-checkpoint RecoverySprint/continuation_20260802/\
ROBERT_R26_AFTER_KIRA_BLENDER_RELEASE.json \
      --authorize-private-owner-candidate \
      --complete-private-review-package

The worker deliberately does not use Blender automatic/heat/envelope weights.
It reconstructs the exact target-deformed MakeHuman source, transfers the
official CC0 weights from the closest source triangle to the post-Boolean
canonical surface with barycentric interpolation, and copies those weights by
identical vertex index to the bounded v8 Robert-directed surface.  Missing
weights, a residual above the configured gate, changed topology, a changed
lower-body signature, or an existing output directory are fatal.

The worker may instead be run with ``--structural-preflight-only`` to build and
audit entirely in memory without creating an output directory.  A save-capable
run requires the separate ``--complete-private-review-package`` interlock and
does not expose the final candidate path until every eye, brow, lash, skin,
movement, contact, intersection, render, and protected-source gate has passed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import statistics
import struct
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence
import uuid

import bmesh
import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "biological_robert_r26_read_only_preparation"
    / "ROBERT_R26_BUILD_CONFIG.json"
)
FACE_CUTOFF_NATIVE_Z = 6.45
INTERSECTION_AUDITOR = ROOT / "Tools" / "blender_exact_mesh_intersections.py"
NATURAL_NAIL_ADAPTER = ROOT / "Tools" / "blender_avatar_natural_nail_delivery_v3.py"
WEIGHT_CONSTRAINED_NAIL_ADAPTER = (
    ROOT / "Tools" / "blender_avatar_weight_constrained_nail_projection_v1.py"
)
PROFILE_COMPONENTS = ROOT / "Tools" / "blender_profiled_adult_candidate_components.py"


class RobertR26BuildError(RuntimeError):
    """A fail-closed R26 input, geometry, provenance, or sequencing error."""


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--kira-final-blender-complete", action="store_true")
    parser.add_argument("--kira-release-checkpoint")
    parser.add_argument("--authorize-private-owner-candidate", action="store_true")
    parser.add_argument(
        "--structural-preflight-only",
        action="store_true",
        help=(
            "Verify and assemble the body/official rig in memory but do not "
            "create the candidate directory or save a Blend."
        ),
    )
    parser.add_argument(
        "--complete-private-review-package",
        action="store_true",
        help=(
            "Create one append-only complete private owner-review package only "
            "after every configured gate succeeds."
        ),
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RobertR26BuildError(f"JSON object required: {path}")
    return value


def project_path(raw: str) -> Path:
    path = Path(str(raw))
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def require_inside_project(path: Path) -> None:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RobertR26BuildError(f"path escapes project: {path}") from exc


def verify_bound_inputs(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    inputs = config.get("inputs")
    if not isinstance(inputs, dict):
        raise RobertR26BuildError("config.inputs object missing")
    for input_id, row in inputs.items():
        if not isinstance(row, dict) or "path" not in row or "sha256" not in row:
            raise RobertR26BuildError(
                f"every configured input must have an exact path/hash binding: {input_id}"
            )
        path = project_path(str(row["path"]))
        require_inside_project(path)
        if not path.is_file():
            raise RobertR26BuildError(f"bound input missing: {input_id}: {path}")
        actual = sha256_file(path)
        expected = str(row["sha256"]).lower()
        if actual != expected:
            raise RobertR26BuildError(
                f"bound input hash changed: {input_id}: expected {expected}; got {actual}"
            )
        if row.get("bytes") is not None and path.stat().st_size != int(row["bytes"]):
            raise RobertR26BuildError(f"bound input size changed: {input_id}: {path}")
        records.append(
            {
                "id": str(input_id),
                "path": str(path),
                "sha256": actual,
                "bytes": path.stat().st_size,
            }
        )
    return records


def verify_interlocks(args: argparse.Namespace, config: Mapping[str, Any]) -> Path:
    if not args.kira_final_blender_complete:
        raise RobertR26BuildError(
            "REFUSED: Kira's final Blender completion was not explicitly confirmed"
        )
    if not args.authorize_private_owner_candidate:
        raise RobertR26BuildError(
            "REFUSED: private owner-candidate authoring interlock was not supplied"
        )
    if args.structural_preflight_only == args.complete_private_review_package:
        raise RobertR26BuildError(
            "REFUSED: select exactly one of --structural-preflight-only or "
            "--complete-private-review-package"
        )
    output_settings = config.get("output")
    if not isinstance(output_settings, dict):
        raise RobertR26BuildError("R26 output configuration missing")
    if int(output_settings.get("maximum_candidate_count", 0)) != 1:
        raise RobertR26BuildError(
            "REFUSED: the bounded R26 run must allow exactly one candidate"
        )
    output = project_path(str(output_settings["candidate_directory"]))
    require_inside_project(output)
    if output.exists():
        raise RobertR26BuildError(
            f"append-only output path already exists; refusing overwrite: {output}"
        )
    return output


def verify_release_checkpoint(
    args: argparse.Namespace,
    config: Mapping[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    gate = config.get("release_gate")
    if not isinstance(gate, dict):
        raise RobertR26BuildError("R26 durable release-gate configuration missing")
    if not args.kira_release_checkpoint:
        raise RobertR26BuildError(
            "REFUSED: durable post-Kira release checkpoint was not supplied"
        )
    supplied = project_path(str(args.kira_release_checkpoint))
    expected = project_path(str(gate["checkpoint_path"]))
    require_inside_project(supplied)
    if supplied != expected:
        raise RobertR26BuildError(
            f"REFUSED: release checkpoint path differs: {supplied}"
        )
    if not supplied.is_file():
        raise RobertR26BuildError(
            f"REFUSED: post-Kira release checkpoint is absent: {supplied}"
        )
    payload = json_file(supplied)
    required_values = {
        "schema": str(gate["required_schema"]),
        "status": str(gate["required_status"]),
        "candidate_id": str(config["candidate_id"]),
    }
    mismatched = {
        key: {"required": value, "actual": payload.get(key)}
        for key, value in required_values.items()
        if payload.get(key) != value
    }
    if mismatched:
        raise RobertR26BuildError(
            "REFUSED: durable release values differ: "
            + json.dumps(mismatched, sort_keys=True)
        )
    for boolean_key in (
        "kira_targeted_blender_operation_complete",
        "no_active_kira_blender_process_at_release",
        "robert_private_candidate_authoring_released",
    ):
        if payload.get(boolean_key) is not True:
            raise RobertR26BuildError(
                f"REFUSED: release checkpoint boolean is not true: {boolean_key}"
            )
    implementation = payload.get("implementation")
    if not isinstance(implementation, dict):
        raise RobertR26BuildError("REFUSED: release implementation binding missing")
    expected_worker_path = Path(__file__).resolve()
    expected_bindings = {
        "worker_path": project_relative(expected_worker_path),
        "worker_sha256": sha256_file(expected_worker_path),
        "config_path": project_relative(config_path),
        "config_sha256": sha256_file(config_path),
    }
    if any(implementation.get(key) != value for key, value in expected_bindings.items()):
        raise RobertR26BuildError(
            "REFUSED: release checkpoint does not bind the exact worker/config"
        )
    kira_artifact = payload.get("kira_completion_artifact")
    if not isinstance(kira_artifact, dict):
        raise RobertR26BuildError("REFUSED: Kira completion artifact binding missing")
    kira_path = project_path(str(kira_artifact.get("path", "")))
    require_inside_project(kira_path)
    if not kira_path.is_file():
        raise RobertR26BuildError(
            f"REFUSED: bound Kira completion artifact is absent: {kira_path}"
        )
    actual_kira_hash = sha256_file(kira_path)
    if actual_kira_hash != str(kira_artifact.get("sha256", "")).lower():
        raise RobertR26BuildError(
            "REFUSED: bound Kira completion artifact hash changed"
        )
    return {
        "path": project_relative(supplied),
        "sha256": sha256_file(supplied),
        "required_values_exact": True,
        "worker_and_config_hashes_exact": True,
        "kira_completion_artifact": {
            "path": project_relative(kira_path),
            "sha256": actual_kira_hash,
        },
    }


def parse_obj(
    path: Path,
    requested_groups: Iterable[str],
) -> tuple[list[Vector], dict[str, list[tuple[int, ...]]]]:
    requested = set(requested_groups)
    vertices: list[Vector] = []
    groups: dict[str, list[tuple[int, ...]]] = {name: [] for name in requested}
    group = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append(Vector((float(x), float(y), float(z))))
            elif line.startswith("g "):
                group = line[2:].strip()
            elif group in requested and line.startswith("f "):
                row: list[int] = []
                for token in line.split()[1:]:
                    index = int(token.split("/", 1)[0])
                    row.append(index - 1 if index > 0 else len(vertices) + index)
                if len(row) >= 3:
                    groups[group].append(tuple(row))
    if len(vertices) != 19158:
        raise RobertR26BuildError(
            f"unexpected MakeHuman source vertex count: {len(vertices)}"
        )
    missing = [name for name, faces in groups.items() if not faces]
    if missing:
        raise RobertR26BuildError(f"required MakeHuman groups missing: {missing}")
    return vertices, groups


def apply_target(vertices: list[Vector], path: Path, weight: float) -> int:
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
                raise RobertR26BuildError(f"target index outside source: {path}: {index}")
            vertices[index] += Vector(
                (
                    float(fields[1]) * weight,
                    float(fields[2]) * weight,
                    float(fields[3]) * weight,
                )
            )
            changed += 1
    return changed


def target_deformed_source(
    config: Mapping[str, Any],
) -> tuple[list[Vector], dict[str, list[tuple[int, ...]]], list[dict[str, Any]]]:
    base_row = config["inputs"]["makehuman_base_obj"]
    path = project_path(str(base_row["path"]))
    groups_wanted = [str(value) for value in base_row["required_groups"]]
    vertices, groups = parse_obj(path, groups_wanted)
    report = json_file(project_path(str(config["inputs"]["foundation_report"]["path"])))
    records: list[dict[str, Any]] = []
    target_root = (
        ROOT
        / "Avatar"
        / "avatar_builder"
        / "tooling"
        / "makehuman_official"
        / "makehuman"
        / "data"
        / "targets"
    ).resolve()
    for position, row in enumerate(report.get("targets", [])):
        raw_path = Path(str(row["path"]))
        marker = "targets"
        parts = list(raw_path.parts)
        try:
            marker_index = [value.lower() for value in parts].index(marker)
        except ValueError as exc:
            raise RobertR26BuildError(f"target path has no targets segment: {raw_path}") from exc
        relative = Path(*parts[marker_index + 1 :])
        path = (target_root / relative).resolve()
        if target_root not in path.parents or path.suffix.lower() != ".target":
            raise RobertR26BuildError(f"target escapes official target root: {path}")
        actual_hash = sha256_file(path)
        expected_hash = str(row["sha256"]).lower()
        if actual_hash != expected_hash:
            raise RobertR26BuildError(
                f"ordered foundation target changed at {position}: {relative}"
            )
        changed = apply_target(vertices, path, float(row["weight"]))
        if changed != int(row["changed_vertices"]):
            raise RobertR26BuildError(
                f"target changed-row count differs at {position}: {relative}"
            )
        records.append(
            {
                "position": position,
                "relative_path": relative.as_posix(),
                "sha256": actual_hash,
                "weight": float(row["weight"]),
                "changed_vertices": changed,
            }
        )
    if len(records) != 44:
        raise RobertR26BuildError(f"expected exact 44-target stack; got {len(records)}")
    return vertices, groups, records


def converted_native(point: Vector) -> Vector:
    return Vector((point.x, -point.z, point.y))


def read_source_weights(path: Path, source_count: int) -> list[dict[str, float]]:
    payload = json_file(path)
    rows: list[dict[str, float]] = [defaultdict(float) for _ in range(source_count)]
    for bone_name, assignments in payload["weights"].items():
        for raw_index, raw_weight in assignments:
            index = int(raw_index)
            weight = float(raw_weight)
            if not 0 <= index < source_count:
                raise RobertR26BuildError(f"official weight index outside source: {index}")
            if weight > 0.0:
                rows[index][str(bone_name)] += weight
    return rows


def barycentric(point: Vector, a: Vector, b: Vector, c: Vector) -> tuple[float, float, float]:
    first = b - a
    second = c - a
    delta = point - a
    d00 = first.dot(first)
    d01 = first.dot(second)
    d11 = second.dot(second)
    d20 = delta.dot(first)
    d21 = delta.dot(second)
    denominator = d00 * d11 - d01 * d01
    if abs(denominator) <= 1.0e-20:
        distances = [(point - value).length for value in (a, b, c)]
        winner = min(range(3), key=distances.__getitem__)
        return tuple(1.0 if index == winner else 0.0 for index in range(3))
    second_weight = (d11 * d20 - d01 * d21) / denominator
    third_weight = (d00 * d21 - d01 * d20) / denominator
    first_weight = 1.0 - second_weight - third_weight
    raw = [max(0.0, min(1.0, value)) for value in (first_weight, second_weight, third_weight)]
    total = sum(raw)
    if total <= 1.0e-12:
        raise RobertR26BuildError("barycentric interpolation collapsed")
    return tuple(value / total for value in raw)


def source_weight_surface(
    vertices: Sequence[Vector],
    groups: Mapping[str, Sequence[Sequence[int]]],
    root_inset: float,
) -> tuple[BVHTree, list[tuple[int, int, int]], list[Vector]]:
    points: list[Vector] = []
    polygons: list[tuple[int, int, int]] = []
    triangle_sources: list[tuple[int, int, int]] = []
    for group_name in ("body", "helper-genital"):
        offset = Vector((0.0, root_inset, 0.0)) if group_name == "helper-genital" else Vector()
        for face in groups[group_name]:
            for index in range(1, len(face) - 1):
                source_triangle = (int(face[0]), int(face[index]), int(face[index + 1]))
                start = len(points)
                points.extend(converted_native(vertices[value]) + offset for value in source_triangle)
                polygons.append((start, start + 1, start + 2))
                triangle_sources.append(source_triangle)
    if not polygons:
        raise RobertR26BuildError("source weight surface is empty")
    return BVHTree.FromPolygons(points, polygons, all_triangles=True), triangle_sources, points


def interpolate_weights(
    canonical: Any,
    tree: BVHTree,
    triangle_sources: Sequence[tuple[int, int, int]],
    tree_points: Sequence[Vector],
    source_weights: Sequence[Mapping[str, float]],
    *,
    max_residual_native: float,
    max_influences: int,
) -> tuple[
    list[list[tuple[str, float]]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    result: list[list[tuple[str, float]]] = []
    associations: list[dict[str, Any]] = []
    residuals: list[float] = []
    for vertex in canonical.data.vertices:
        query = canonical.matrix_world @ vertex.co
        location, _normal, triangle_index, distance = tree.find_nearest(query)
        if location is None or triangle_index is None:
            raise RobertR26BuildError(f"weight transfer query failed: vertex {vertex.index}")
        residual = float(distance)
        residuals.append(residual)
        if residual > max_residual_native:
            raise RobertR26BuildError(
                f"official-weight transfer residual failed at vertex {vertex.index}: "
                f"{residual:.9g} native > {max_residual_native:.9g}"
            )
        tri = triangle_sources[int(triangle_index)]
        base = int(triangle_index) * 3
        blend = barycentric(
            Vector(location),
            tree_points[base],
            tree_points[base + 1],
            tree_points[base + 2],
        )
        associations.append(
            {
                "source_triangle": tri,
                "barycentric": blend,
                "residual_native": residual,
            }
        )
        combined: dict[str, float] = defaultdict(float)
        for source_index, factor in zip(tri, blend):
            for bone_name, source_weight in source_weights[source_index].items():
                combined[bone_name] += factor * float(source_weight)
        top = sorted(combined.items(), key=lambda item: (-item[1], item[0]))[:max_influences]
        total = sum(value for _name, value in top)
        if total <= 1.0e-12:
            raise RobertR26BuildError(
                f"official-weight transfer produced uncovered vertex {vertex.index}"
            )
        result.append([(name, value / total) for name, value in top])
    sums = [sum(value for _name, value in row) for row in result]
    if len(result) != len(canonical.data.vertices):
        raise RobertR26BuildError("official weight coverage is not 100 percent")
    if min(sums) < 0.999999 or max(sums) > 1.000001:
        raise RobertR26BuildError("normalized official weight sums failed")
    return result, associations, {
        "method": "nearest_exact_source_triangle_barycentric_official_weights",
        "vertex_count": len(result),
        "coverage": 1.0,
        "root_fallback_vertex_count": 0,
        "maximum_influences": max(len(row) for row in result),
        "weight_sum_minimum": min(sums),
        "weight_sum_maximum": max(sums),
        "residual_native_minimum": min(residuals),
        "residual_native_maximum": max(residuals),
        "residual_native_mean": sum(residuals) / len(residuals),
        "required_residual_native_maximum": max_residual_native,
    }


def append_v8_objects(config: Mapping[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    row = config["inputs"]["bounded_v8_face_blend"]
    path = project_path(str(row["path"]))
    requested_names = (
        str(row["canonical_object"]),
        str(row["warped_object"]),
    )
    if len(requested_names) != 2 or len(set(requested_names)) != 2:
        raise RobertR26BuildError("exactly two distinct v8 source objects are required")
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        absent = [name for name in requested_names if name not in source.objects]
        if absent:
            raise RobertR26BuildError(f"required v8 objects absent: {absent}")
        target.objects = list(requested_names)
    loaded = list(target.objects)
    if not all(isinstance(name, str) for name in requested_names):
        raise RobertR26BuildError("immutable requested v8 names changed type after append")
    if len(loaded) != len(requested_names) or any(obj is None for obj in loaded):
        raise RobertR26BuildError(
            "v8 library append did not return exactly two non-null object pointers"
        )
    records: list[dict[str, Any]] = []
    for position, (requested_name, obj) in enumerate(zip(requested_names, loaded)):
        actual_name = str(obj.name)
        suffix = actual_name[len(requested_name) :] if actual_name.startswith(requested_name) else ""
        deterministic_numeric_suffix = (
            suffix.startswith(".") and len(suffix) > 1 and suffix[1:].isdigit()
        )
        if actual_name != requested_name and not deterministic_numeric_suffix:
            raise RobertR26BuildError(
                "loaded v8 object name does not correspond to its requested source "
                f"name at position {position}: requested={requested_name!r}; "
                f"actual={actual_name!r}"
            )
        if obj.type != "MESH" or obj.data is None:
            raise RobertR26BuildError(
                f"loaded v8 source object is not a mesh: {actual_name}"
            )
        obj["source_library_requested_object_name"] = requested_name
        obj["source_library_actual_object_name"] = actual_name
        obj["source_library_request_position"] = position
        records.append(
            {
                "request_position": position,
                "requested_name": requested_name,
                "actual_name": actual_name,
                "actual_name_matches_requested_or_numeric_suffix": True,
                "object_type": str(obj.type),
                "mesh_data_name": str(obj.data.name),
            }
        )
        if not obj.users_collection:
            bpy.context.collection.objects.link(obj)
    return loaded[0], loaded[1], {
        "source_blend": project_relative(path),
        "requested_object_count": len(requested_names),
        "returned_non_null_object_count": len(loaded),
        "request_order_preserved": True,
        "objects": records,
    }


def polygon_index_signature(obj: Any) -> str:
    digest = hashlib.sha256()
    digest.update(struct.pack("<II", len(obj.data.vertices), len(obj.data.polygons)))
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", int(index)))
    return digest.hexdigest()


def point_signature(points: Sequence[Vector]) -> str:
    digest = hashlib.sha256()
    for point in points:
        digest.update(f"{point.x:.7f},{point.y:.7f},{point.z:.7f}\n".encode("ascii"))
    return digest.hexdigest()


def validate_v8(config: Mapping[str, Any], canonical: Any, warped: Any) -> dict[str, Any]:
    if canonical.type != "MESH" or warped.type != "MESH":
        raise RobertR26BuildError("v8 canonical and warped objects must both be meshes")
    canonical_topology = polygon_index_signature(canonical)
    warped_topology = polygon_index_signature(warped)
    if canonical_topology != warped_topology:
        raise RobertR26BuildError("v8 warped/canonical polygon-index topology differs")
    report_row = config["inputs"]["bounded_v8_face_report"]
    report = json_file(project_path(str(report_row["path"])))
    if report.get("status") != report_row["required_status"]:
        raise RobertR26BuildError("v8 report status changed")
    canonical_lower = [v.co.copy() for v in canonical.data.vertices if v.co.z < FACE_CUTOFF_NATIVE_Z]
    warped_lower = [v.co.copy() for v in warped.data.vertices if v.co.z < FACE_CUTOFF_NATIVE_Z]
    expected_count = int(report_row["frozen_lower_body_vertex_count"])
    expected_signature = str(report_row["frozen_lower_body_signature"])
    if len(canonical_lower) != expected_count or len(warped_lower) != expected_count:
        raise RobertR26BuildError("v8 frozen lower-body vertex count changed")
    canonical_signature = point_signature(canonical_lower)
    warped_signature = point_signature(warped_lower)
    if canonical_signature != expected_signature or warped_signature != expected_signature:
        raise RobertR26BuildError("v8 frozen lower-body signature changed")
    return {
        "canonical_polygon_index_signature": canonical_topology,
        "warped_polygon_index_signature": warped_topology,
        "polygon_index_topology_identical": True,
        "frozen_lower_body_vertex_count": expected_count,
        "canonical_lower_body_signature": canonical_signature,
        "warped_lower_body_signature": warped_signature,
        "frozen_lower_body_unchanged": True,
        "owner_likeness_approved": False,
    }


def validate_expected_warped_height_envelope(
    config: Mapping[str, Any],
    warped: Any,
    v8_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind height to the exact V8 warped source without rescaling the body."""
    truth = config.get("foundation_truth")
    if not isinstance(truth, dict):
        raise RobertR26BuildError("foundation truth required for warped-height gate")
    required = (
        "prior_v25_r6_reference_height_m",
        "expected_warped_height_m",
        "expected_warped_height_tolerance_m",
        "expected_warped_native_floor_z",
        "expected_warped_native_top_z",
        "expected_warped_floor_vertex_ids",
        "expected_warped_crown_vertex_id",
        "expected_frozen_lower_body_vertex_count",
        "expected_frozen_lower_body_signature",
    )
    missing = [name for name in required if name not in truth]
    if missing:
        raise RobertR26BuildError(
            f"warped-height gate configuration missing: {sorted(missing)}"
        )
    prior_height = float(truth["prior_v25_r6_reference_height_m"])
    expected_height = float(truth["expected_warped_height_m"])
    tolerance = float(truth["expected_warped_height_tolerance_m"])
    expected_floor = float(truth["expected_warped_native_floor_z"])
    expected_top = float(truth["expected_warped_native_top_z"])
    expected_floor_ids = sorted(
        int(index) for index in truth["expected_warped_floor_vertex_ids"]
    )
    expected_crown_id = int(truth["expected_warped_crown_vertex_id"])
    expected_lower_count = int(truth["expected_frozen_lower_body_vertex_count"])
    expected_lower_signature = str(truth["expected_frozen_lower_body_signature"])
    numeric = (prior_height, expected_height, tolerance, expected_floor, expected_top)
    if not all(math.isfinite(value) for value in numeric):
        raise RobertR26BuildError("warped-height gate contains a non-finite value")
    if prior_height <= 0.0 or expected_height <= 0.0:
        raise RobertR26BuildError("warped-height gate contains a non-positive height")
    if tolerance <= 0.0 or tolerance > 0.00001:
        raise RobertR26BuildError(
            "warped-height tolerance must remain within (0, 0.00001] m"
        )
    if not expected_floor_ids or len(set(expected_floor_ids)) != len(
        expected_floor_ids
    ):
        raise RobertR26BuildError("warped-height floor vertex IDs are invalid")
    if min((*expected_floor_ids, expected_crown_id)) < 0 or max(
        *expected_floor_ids, expected_crown_id
    ) >= len(warped.data.vertices):
        raise RobertR26BuildError("warped-height extremal vertex ID is out of range")
    if expected_lower_count != int(v8_report["frozen_lower_body_vertex_count"]):
        raise RobertR26BuildError(
            "warped-height lower-body vertex-count binding differs from v8 validation"
        )
    if expected_lower_signature != str(v8_report["warped_lower_body_signature"]):
        raise RobertR26BuildError(
            "warped-height lower-body signature binding differs from v8 validation"
        )

    native_z = [float(vertex.co.z) for vertex in warped.data.vertices]
    actual_floor = min(native_z)
    actual_top = max(native_z)
    actual_floor_ids = sorted(
        int(vertex.index)
        for vertex in warped.data.vertices
        if float(vertex.co.z) == actual_floor
    )
    actual_top_ids = sorted(
        int(vertex.index)
        for vertex in warped.data.vertices
        if float(vertex.co.z) == actual_top
    )
    if actual_floor != expected_floor or actual_floor_ids != expected_floor_ids:
        raise RobertR26BuildError(
            "bound warped floor or its exact extremal vertex IDs changed"
        )
    if actual_top != expected_top or actual_top_ids != [expected_crown_id]:
        raise RobertR26BuildError(
            "bound warped crown or its exact extremal vertex ID changed"
        )
    scale = float(truth["native_to_blender_scale"])
    actual_height = (actual_top - actual_floor) * scale
    delta = actual_height - expected_height
    if abs(delta) > tolerance:
        raise RobertR26BuildError(
            "bound warped source height differs from its explicit expectation: "
            f"expected={expected_height:.15f} actual={actual_height:.15f} "
            f"tolerance={tolerance:.15f}"
        )
    return {
        "prior_v25_r6_reference_height_m": prior_height,
        "expected_warped_height_m": expected_height,
        "expected_warped_height_tolerance_m": tolerance,
        "actual_native_floor_z": actual_floor,
        "actual_native_top_z": actual_top,
        "actual_floor_vertex_ids": actual_floor_ids,
        "actual_crown_vertex_id": actual_top_ids[0],
        "actual_warped_height_m_before_prepare": actual_height,
        "height_delta_m_before_prepare": delta,
        "frozen_lower_body_vertex_count": expected_lower_count,
        "frozen_lower_body_signature": expected_lower_signature,
        "uniform_native_to_meter_scale": scale,
        "global_or_nonuniform_rescale_used": False,
        "passed": True,
    }


def import_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RobertR26BuildError(f"could not load required method module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def exact_intersection_report(obj: Any) -> dict[str, Any]:
    auditor = import_module(INTERSECTION_AUDITOR, "robert_r26_exact_intersections")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        report = auditor.exact_nonadjacent_intersection_report(bm)
    finally:
        bm.free()
    if int(report["exact_genuine_penetration_pair_count"]) != 0:
        raise RobertR26BuildError(
            "bounded v8 body failed exact global nonadjacent self-intersection gate"
        )
    return report


def topology_report(obj: Any) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unseen = set(bm.verts)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            vertex = stack.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "components": components,
        "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
        "nonmanifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
    }
    bm.free()
    expected = (13606, 27112, 13508, 1, 0, 0)
    actual = tuple(result[key] for key in (
        "vertices", "edges", "faces", "components", "boundary_edges", "nonmanifold_edges"
    ))
    if actual != expected:
        raise RobertR26BuildError(f"qualified foundation topology changed: {actual}")
    return result


def converted_joint_positions(
    rig: Mapping[str, Any],
    source_vertices: Sequence[Vector],
    *,
    scale: float,
    floor_native: float,
) -> dict[str, Vector]:
    positions: dict[str, Vector] = {}
    for name, raw_indices in rig["joints"].items():
        indices = [int(value) for value in raw_indices]
        if not indices:
            raise RobertR26BuildError(f"empty official joint: {name}")
        point = sum(
            (converted_native(source_vertices[index]) for index in indices),
            Vector(),
        ) / len(indices)
        positions[str(name)] = Vector(
            (point.x * scale, point.y * scale, (point.z - floor_native) * scale)
        )
    return positions


def plane_normal(
    plane_name: str,
    rig: Mapping[str, Any],
    joints: Mapping[str, Vector],
) -> Vector | None:
    names = rig.get("planes", {}).get(plane_name)
    if not isinstance(names, list) or len(names) != 3:
        return None
    if any(name not in joints for name in names):
        return None
    first = (joints[names[1]] - joints[names[0]]).normalized()
    second = (joints[names[2]] - joints[names[1]]).normalized()
    normal = second.cross(first)
    return normal.normalized() if normal.length > 1.0e-8 else None


def build_official_armature(
    body: Any,
    config: Mapping[str, Any],
    source_vertices: Sequence[Vector],
    normalized_weights: Sequence[Sequence[tuple[str, float]]],
    *,
    floor_native: float,
) -> tuple[Any, dict[str, Any]]:
    skeleton_path = project_path(str(config["inputs"]["makehuman_skeleton"]["path"]))
    rig = json_file(skeleton_path)
    expected_bones = int(config["inputs"]["makehuman_skeleton"]["bone_count"])
    expected_joints = int(config["inputs"]["makehuman_skeleton"]["joint_count"])
    expected_planes = int(
        config["inputs"]["makehuman_skeleton"]["rotation_plane_count"]
    )
    actual_source_counts = {
        "bones": len(rig.get("bones", {})),
        "joints": len(rig.get("joints", {})),
        "rotation_planes": len(rig.get("planes", {})),
    }
    if actual_source_counts != {
        "bones": expected_bones,
        "joints": expected_joints,
        "rotation_planes": expected_planes,
    }:
        raise RobertR26BuildError(
            f"official skeleton source counts changed: {actual_source_counts}"
        )
    scale = float(config["foundation_truth"]["native_to_blender_scale"])
    joints = converted_joint_positions(
        rig,
        source_vertices,
        scale=scale,
        floor_native=floor_native,
    )
    candidate_id = str(config["candidate_id"])
    data = bpy.data.armatures.new(f"{candidate_id}_official_makehuman_skeleton")
    armature = bpy.data.objects.new(f"{candidate_id}_official_makehuman_rig", data)
    bpy.context.collection.objects.link(armature)
    armature.show_in_front = True
    for key, value in {
        "candidate_id": candidate_id,
        "private_owner_review_only": True,
        "inactive_candidate": True,
        "runtime_activation_allowed": False,
        "roster_registration_allowed": False,
        "automatic_weights_used": False,
    }.items():
        armature[key] = value
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    remaining = dict(rig["bones"])
    built: set[str] = set()
    roll_aligned: list[str] = []
    bone_plane_records: dict[str, list[str]] = {}
    while remaining:
        progressed = False
        for name, definition in list(remaining.items()):
            parent = definition.get("parent")
            if parent and parent not in built:
                continue
            head = joints[str(definition["head"])]
            tail = joints[str(definition["tail"])]
            if (tail - head).length < 1.0e-5:
                tail = head + Vector((0.0, 0.0, 0.01))
            bone = data.edit_bones.new(str(name))
            bone.head = head
            bone.tail = tail
            bone.use_deform = any(
                str(name) == influence
                for row in normalized_weights
                for influence, _weight in row
            )
            if parent:
                bone.parent = data.edit_bones[str(parent)]
                bone.use_connect = (bone.head - bone.parent.tail).length < 0.0005
            raw_planes = definition.get("rotation_plane")
            names = raw_planes if isinstance(raw_planes, list) else [raw_planes]
            if not names or any(
                not isinstance(plane, str) or plane not in rig["planes"]
                for plane in names
            ):
                bpy.ops.object.mode_set(mode="OBJECT")
                raise RobertR26BuildError(
                    f"official rotation-plane provenance missing for bone: {name}"
                )
            normals = [
                value
                for plane in names
                if isinstance(plane, str)
                for value in [plane_normal(plane, rig, joints)]
                if value is not None
            ]
            if len(normals) != len(names):
                bpy.ops.object.mode_set(mode="OBJECT")
                raise RobertR26BuildError(
                    f"official rotation plane is degenerate for bone: {name}"
                )
            combined_normal = sum(normals, Vector())
            if combined_normal.length <= 1.0e-8:
                bpy.ops.object.mode_set(mode="OBJECT")
                raise RobertR26BuildError(
                    f"official rotation-plane normal collapsed for bone: {name}"
                )
            try:
                bone.align_roll(combined_normal.normalized())
            except ValueError as exc:
                bpy.ops.object.mode_set(mode="OBJECT")
                raise RobertR26BuildError(
                    f"official rotation-plane roll alignment failed for bone: {name}"
                ) from exc
            roll_aligned.append(str(name))
            bone_plane_records[str(name)] = [str(value) for value in names]
            built.add(str(name))
            del remaining[name]
            progressed = True
        if not progressed:
            bpy.ops.object.mode_set(mode="OBJECT")
            raise RobertR26BuildError(f"unresolved official rig parents: {sorted(remaining)}")
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(data.bones) != expected_bones:
        raise RobertR26BuildError("official skeleton bone count changed")
    if len(roll_aligned) != expected_bones or set(roll_aligned) != set(rig["bones"]):
        raise RobertR26BuildError("official rotation-plane roll coverage is incomplete")

    group_names = sorted({name for row in normalized_weights for name, _weight in row})
    groups = {name: body.vertex_groups.new(name=name) for name in group_names}
    assignments = 0
    for vertex_index, row in enumerate(normalized_weights):
        for name, weight in row:
            groups[name].add([vertex_index], float(weight), "REPLACE")
            assignments += 1
    modifier = body.modifiers.new("Robert_R26_Official_MakeHuman_Rig", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    return armature, {
        "skeleton_path": str(skeleton_path),
        "skeleton_sha256": sha256_file(skeleton_path),
        "bone_count": len(data.bones),
        "source_joint_count": len(rig["joints"]),
        "source_rotation_plane_count": len(rig["planes"]),
        "bone_rotation_plane_coverage_count": len(roll_aligned),
        "bone_rotation_plane_coverage": 1.0,
        "roll_alignment_failure_count": 0,
        "joint_definition_sha256": hashlib.sha256(
            json.dumps(rig["joints"], sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest(),
        "rotation_plane_definition_sha256": hashlib.sha256(
            json.dumps(rig["planes"], sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest(),
        "bone_to_rotation_plane_sha256": hashlib.sha256(
            json.dumps(
                bone_plane_records,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "deform_bone_count": sum(1 for bone in data.bones if bone.use_deform),
        "vertex_group_count": len(groups),
        "weight_assignment_count": assignments,
        "automatic_heat_or_envelope_weights_used": False,
        "root_fallback_vertex_count": 0,
        "preserve_volume": True,
    }


def target_source_indices(config: Mapping[str, Any], input_id: str) -> set[int]:
    row = config["inputs"][input_id]
    path = project_path(str(row["path"]))
    require_inside_project(path)
    if sha256_file(path) != str(row["sha256"]).lower():
        raise RobertR26BuildError(f"regional source mask hash changed: {input_id}")
    values: set[int] = set()
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            fields = raw.split()
            if len(fields) == 4 and not fields[0].startswith("#"):
                values.add(int(fields[0]))
    if not values:
        raise RobertR26BuildError(f"regional source mask target is empty: {input_id}")
    return values


def index_signature(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in sorted(set(int(item) for item in values)):
        digest.update(struct.pack("<I", value))
    return digest.hexdigest()


def associated_mask(
    associations: Sequence[Mapping[str, Any]],
    source_indices: set[int],
    *,
    minimum_influence: float = 0.15,
) -> set[int]:
    result: set[int] = set()
    for vertex_index, association in enumerate(associations):
        total = sum(
            float(weight)
            for source_index, weight in zip(
                association["source_triangle"], association["barycentric"]
            )
            if int(source_index) in source_indices
        )
        if total >= minimum_influence:
            result.add(vertex_index)
    return result


def regional_skin_material(
    body: Any,
    config: Mapping[str, Any],
    associations: Sequence[Mapping[str, Any]],
    normalized_weights: Sequence[Sequence[tuple[str, float]]],
) -> tuple[Any, dict[str, Any]]:
    """Create one continuous skin material with exact recorded point masks."""

    settings = config["regional_skin"]
    lip_source = target_source_indices(config, "regional_mask_upper_lip")
    lip_source.update(target_source_indices(config, "regional_mask_lower_lip"))
    genital_source: set[int] = set()
    for input_id in (
        "regional_mask_adult_length",
        "regional_mask_adult_circumference",
        "regional_mask_adult_testicles",
    ):
        genital_source.update(target_source_indices(config, input_id))
    lips = associated_mask(associations, lip_source, minimum_influence=0.12)
    genital = associated_mask(associations, genital_source, minimum_influence=0.08)
    points = [vertex.co.copy() for vertex in body.data.vertices]
    low_z = min(float(point.z) for point in points)
    high_z = max(float(point.z) for point in points)
    height = high_z - low_z
    if height <= 0.0:
        raise RobertR26BuildError("regional skin body height is invalid")

    areola_centers: dict[str, Vector] = {}
    areolae: set[int] = set()
    for label, sign in (("negative_x", -1), ("positive_x", 1)):
        candidates = [
            (index, point)
            for index, point in enumerate(points)
            if low_z + height * 0.69 <= point.z <= low_z + height * 0.80
            and height * 0.055 <= abs(float(point.x)) <= height * 0.19
            and math.copysign(1.0, float(point.x)) == sign
        ]
        if not candidates:
            raise RobertR26BuildError(f"areola mask seed selection empty: {label}")
        _seed_index, center = min(candidates, key=lambda row: float(row[1].y))
        areola_centers[label] = center.copy()
        radius = height * 0.018
        areolae.update(
            index
            for index, point in enumerate(points)
            if (point - center).length <= radius
            and abs(float(point.y - center.y)) <= radius * 0.55
        )

    palms: set[int] = set()
    soles: set[int] = set()
    for index, (vertex, weights) in enumerate(zip(body.data.vertices, normalized_weights)):
        names = {name.lower() for name, value in weights if float(value) >= 0.08}
        if any(name.startswith(("hand.", "finger")) for name in names):
            if float(vertex.normal.z) < -0.12 or float(vertex.normal.y) < -0.45:
                palms.add(index)
        if any(name.startswith(("foot.", "toe")) for name in names):
            if float(vertex.normal.z) < -0.30:
                soles.add(index)
    masks = {
        "lips": lips,
        "areolae_nipples": areolae,
        "adult_external_anatomy": genital,
        "palms": palms,
        "soles": soles,
    }
    empty = [name for name, values in masks.items() if not values]
    if empty:
        raise RobertR26BuildError(f"one or more exact regional skin masks is empty: {empty}")

    colors = {
        "base": tuple(float(value) for value in settings["base_linear_rgba"]),
        "shadow": tuple(float(value) for value in settings["base_shadow_linear_rgba"]),
        "lips": tuple(float(value) for value in settings["lip_linear_rgba"]),
        "areolae_nipples": tuple(float(value) for value in settings["areola_nipple_linear_rgba"]),
        "adult_external_anatomy": tuple(float(value) for value in settings["genital_linear_rgba"]),
        "palms": tuple(float(value) for value in settings["palm_sole_linear_rgba"]),
        "soles": tuple(float(value) for value in settings["palm_sole_linear_rgba"]),
    }
    attribute_name = "Robert_R26_Exact_Regional_Skin_Color"
    existing = body.data.color_attributes.get(attribute_name)
    if existing is not None:
        body.data.color_attributes.remove(existing)
    attribute = body.data.color_attributes.new(
        name=attribute_name,
        type="FLOAT_COLOR",
        domain="POINT",
    )
    priority = ("palms", "soles", "adult_external_anatomy", "areolae_nipples", "lips")
    for index, point in enumerate(points):
        wave = 0.5 + 0.5 * math.sin(
            float(point.x) * 31.7 + float(point.y) * 23.3 + float(point.z) * 17.9
        )
        base = colors["base"]
        shadow = colors["shadow"]
        variation = 0.10 + wave * 0.13
        selected = tuple(
            base[channel] * (1.0 - variation) + shadow[channel] * variation
            for channel in range(3)
        ) + (1.0,)
        for region in priority:
            if index in masks[region]:
                selected = colors[region]
        attribute.data[index].color = selected

    candidate_id = str(config["candidate_id"])
    material = bpy.data.materials.new(f"{candidate_id}_Regional_Natural_Skin")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    color_attribute = nodes.new("ShaderNodeVertexColor")
    color_attribute.layer_name = attribute_name
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 3.5
    noise.inputs["Roughness"].default_value = 0.58
    coordinates = nodes.new("ShaderNodeTexCoord")
    variation = nodes.new("ShaderNodeMixRGB")
    variation.blend_type = "MULTIPLY"
    variation.inputs["Fac"].default_value = 0.12
    links.new(coordinates.outputs["Generated"], noise.inputs["Vector"])
    links.new(color_attribute.outputs["Color"], variation.inputs[1])
    links.new(noise.outputs["Color"], variation.inputs[2])
    links.new(variation.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Roughness"].default_value = float(settings["roughness_base"])
    subsurface = principled.inputs.get("Subsurface Weight")
    if subsurface is None:
        subsurface = principled.inputs.get("Subsurface")
    if subsurface is not None:
        subsurface.default_value = float(settings["subsurface_weight"])
    radius = principled.inputs.get("Subsurface Radius")
    if radius is not None:
        radius.default_value = (1.0, 0.48, 0.28)
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material["regional_skin_direction"] = True
    material["single_flat_color_used"] = False
    material["geometry_plate_regions_used"] = False
    return material, {
        "method": str(settings["method"]),
        "material": material.name,
        "point_color_attribute": attribute_name,
        "single_material_slot_required": True,
        "single_flat_color_used": False,
        "geometry_plate_regions_used": False,
        "mask_records": {
            name: {
                "vertex_count": len(values),
                "vertex_index_sha256": index_signature(values),
            }
            for name, values in sorted(masks.items())
        },
        "areola_centers_m": {
            name: [float(value) for value in center]
            for name, center in areola_centers.items()
        },
        "source_bound_masks": ["lips", "adult_external_anatomy"],
        "surface_measured_masks": ["areolae_nipples", "palms", "soles"],
        "clean_scalp_uses_same_skin_material": True,
    }


def prepare_body_for_meters(body: Any, config: Mapping[str, Any]) -> tuple[float, float]:
    scale = float(config["foundation_truth"]["native_to_blender_scale"])
    floor_native = min(float(vertex.co.z) for vertex in body.data.vertices)
    for vertex in body.data.vertices:
        vertex.co = Vector(
            (
                float(vertex.co.x) * scale,
                float(vertex.co.y) * scale,
                (float(vertex.co.z) - floor_native) * scale,
            )
        )
    body.data.update(calc_edges=True)
    height = max(float(vertex.co.z) for vertex in body.data.vertices)
    return floor_native, height


def body_flags(body: Any, config: Mapping[str, Any]) -> None:
    for key, value in {
        "candidate_id": str(config["candidate_id"]),
        "person_id": "biological_robert",
        "body_class": "adult_male",
        "confirmed_adult": True,
        "one_connected_external_surface": True,
        "private_owner_review_only": True,
        "inactive_candidate": True,
        "runtime_activation_allowed": False,
        "runtime_export_allowed": False,
        "roster_registration_allowed": False,
        "publication_allowed": False,
        "clothing_included": False,
        "scalp_hair_allowed": False,
        "scalp_hair_dependency_present": False,
        "owner_likeness_approved": False,
        "movement_approved": False,
    }.items():
        body[key] = value


def remove_everything_except(keep: Sequence[Any]) -> None:
    keep_names = {obj.name for obj in keep}
    for obj in list(bpy.data.objects):
        if obj.name not in keep_names:
            bpy.data.objects.remove(obj, do_unlink=True)


def add_nails(
    body: Any,
    armature: Any,
    height: float,
    candidate_id: str,
) -> tuple[list[Any], dict[str, Any]]:
    """Build the exact 20-nail inventory with the proven bounded adapter."""

    legacy = import_module(
        NATURAL_NAIL_ADAPTER,
        "robert_r26_natural_nail_materials",
    )
    adapter = import_module(
        WEIGHT_CONSTRAINED_NAIL_ADAPTER,
        "robert_r26_weight_constrained_nails",
    )
    definitions = list(legacy.expected_nail_inventory())
    if len(definitions) != 20 or len(
        {str(row["nail_id"]) for row in definitions}
    ) != 20:
        raise RobertR26BuildError("natural nail inventory is not exactly twenty")

    body_signature_before = legacy._mesh_signature(body)  # noqa: SLF001
    rig_signature_before = legacy._rig_signature(armature)  # noqa: SLF001
    body_modifier_count_before = len(body.modifiers)
    bed_material = legacy._natural_nail_material(  # noqa: SLF001
        f"{candidate_id}_Natural_Nail_Bed_Weight_Constrained_V1",
        legacy.NAIL_BED_MATERIAL,
    )
    free_edge_material = legacy._natural_nail_material(  # noqa: SLF001
        f"{candidate_id}_Natural_Nail_Free_Edge_Weight_Constrained_V1",
        legacy.FREE_EDGE_MATERIAL,
    )
    objects: list[Any] = []
    records: list[dict[str, Any]] = []
    try:
        for definition in definitions:
            nail, record = adapter.build_weight_constrained_nail_v1(
                body=body,
                armature=armature,
                definition=definition,
                target_height_m=height,
                name=(
                    f"{candidate_id}_{definition['nail_id']}"
                    "_weight_constrained_v1"
                ),
                bed_material=bed_material,
                free_edge_material=free_edge_material,
            )
            for key, value in {
                "candidate_id": candidate_id,
                "private_owner_review_only": True,
                "inactive_candidate": True,
                "runtime_activation_allowed": False,
                "runtime_export_allowed": False,
                "roster_registration_allowed": False,
                "unpublished_candidate": True,
                "nail_component": True,
                "avatar_weight_constrained_nail_projection_v1": True,
                "rounded_oval_silhouette": True,
                "translucent_natural_pink_bed": True,
                "softly_paler_free_edge": True,
                "visual_pose_clearance_review_required": True,
            }.items():
                nail[key] = value
            objects.append(nail)
            records.append(
                {
                    **record,
                    "kind": str(definition["kind"]),
                    "side": str(definition["side"]),
                    "digit": int(definition["digit"]),
                    "bone": str(definition["bone"]),
                }
            )

        expected_ids = [str(row["nail_id"]) for row in definitions]
        actual_ids = [str(row["nail_id"]) for row in records]
        strict_footprints = all(
            row["footprint_binding"]["passed"] is True
            and row["selection"]["passed"] is True
            and row["selection"]["every_sample_matches_declared_digit"] is True
            and row["selection"]["every_sample_uses_one_connected_region"] is True
            for row in records
        )
        complete_evaluated_shells = all(
            row["final_evaluated_complete_shell_gate"]["passed"] is True
            and all(
                row["final_evaluated_complete_shell_gate"]["gates"].values()
            )
            for row in records
        )
        no_bone_remap = all(
            row["automatic_bone_remap_performed"] is False
            and row["declared_terminal_bone"] == row["bone"]
            and row["attachment"]["bone"] == row["bone"]
            and row["attachment"]["parent_is_exact_armature"] is True
            and row["attachment"][
                "armature_modifier_targets_exact_rig"
            ]
            is True
            and row["attachment"][
                "every_vertex_has_unit_terminal_bone_weight"
            ]
            is True
            for row in records
        )
        body_signature_after = legacy._mesh_signature(body)  # noqa: SLF001
        rig_signature_after = legacy._rig_signature(armature)  # noqa: SLF001
        natural_material_and_oval_construction = all(
            len(nail.data.vertices) == legacy.PROJECTION_GRID_SIZE ** 2
            and len(nail.data.polygons)
            == (legacy.PROJECTION_GRID_SIZE - 1) ** 2
            and len(nail.data.materials) == 2
            and all(
                math.isfinite(float(value))
                for vertex in nail.data.vertices
                for value in vertex.co
            )
            and bool(nail.get("rounded_oval_silhouette"))
            and row["top_surface_winding"][
                "all_top_surface_faces_outward"
            ]
            is True
            and any(
                modifier.type == "SOLIDIFY"
                and abs(
                    float(modifier.thickness)
                    - float(legacy.NAIL_PLATE_THICKNESS_M)
                )
                <= 1.0e-12
                and abs(float(modifier.offset) - 1.0) <= 1.0e-12
                and bool(getattr(modifier, "use_rim", True))
                for modifier in nail.modifiers
            )
            for nail, row in zip(objects, records)
        )
        gates = {
            "exact_twenty_inventory_in_declared_order": actual_ids == expected_ids
            and len(objects) == 20,
            "all_twenty_strict_declared_digit_footprints": strict_footprints,
            "all_twenty_complete_evaluated_armature_solidify_shells": (
                complete_evaluated_shells
            ),
            "all_twenty_zero_rest_shell_penetrations": all(
                int(
                    row["final_evaluated_complete_shell_gate"][
                        "exact_genuine_triangle_pair_count"
                    ]
                )
                == 0
                for row in records
            ),
            "no_automatic_bone_remap": no_bone_remap,
            "all_twenty_exact_terminal_bone_attachments": no_bone_remap,
            "all_twenty_natural_material_and_oval_construction": (
                natural_material_and_oval_construction
            ),
            "primary_body_mesh_unchanged": (
                body_signature_after == body_signature_before
            ),
            "official_rig_unchanged": rig_signature_after == rig_signature_before,
            "body_modifier_stack_unchanged": (
                len(body.modifiers) == body_modifier_count_before
            ),
        }
        if not all(gates.values()):
            raise RobertR26BuildError(
                "weight-constrained all-20 nail gates failed: "
                + json.dumps(
                    sorted(name for name, passed in gates.items() if not passed)
                )
            )
    except Exception:
        for obj in reversed(objects):
            if obj.name in bpy.data.objects:
                legacy._remove_object_and_mesh(obj)  # noqa: SLF001
        for material in (bed_material, free_edge_material):
            if material.users == 0:
                bpy.data.materials.remove(material)
        raise

    report = {
        "method": adapter.METHOD_ID,
        "expected_nail_count": 20,
        "component_count": len(objects),
        "fingernail_count": sum(row["kind"] == "fingernail" for row in records),
        "toenail_count": sum(row["kind"] == "toenail" for row in records),
        "objects": [obj.name for obj in objects],
        "records": records,
        "gates": gates,
        "material_contract": legacy.material_contract(),
        "material_names": {
            "nail_bed": bed_material.name,
            "free_edge": free_edge_material.name,
        },
        "primary_body_mesh_sha256_before": body_signature_before,
        "primary_body_mesh_sha256_after": body_signature_after,
        "official_rig_sha256_before": rig_signature_before,
        "official_rig_sha256_after": rig_signature_after,
        "body_modifier_count_before": body_modifier_count_before,
        "body_modifier_count_after": len(body.modifiers),
        "component_objects_are_separate_from_primary_body": True,
        "inactive_private_owner_review_only": True,
        "automatic_bone_remap_performed": False,
        "candidate_built_saved_rendered_exported_or_activated_by_this_adapter": False,
    }
    return objects, report


def object_bounds(obj: Any) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(float(point[axis]) for point in points) for axis in range(3))),
        Vector(tuple(max(float(point[axis]) for point in points) for axis in range(3))),
    )


def world_surface_bvh(obj: Any) -> BVHTree:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        triangles = [tuple(int(value) for value in triangle.vertices) for triangle in mesh.loop_triangles]
        if not points or not triangles:
            raise RobertR26BuildError(f"empty surface BVH: {obj.name}")
        return BVHTree.FromPolygons(points, triangles, all_triangles=True)
    finally:
        evaluated.to_mesh_clear()


def simple_material(
    name: str,
    color: Sequence[float],
    *,
    roughness: float,
    transmission: float = 0.0,
    alpha: float = 1.0,
) -> Any:
    material = bpy.data.materials.new(name)
    rgba = tuple(float(value) for value in color)
    material.diffuse_color = rgba
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        raise RobertR26BuildError("Principled BSDF unavailable")
    principled.inputs["Base Color"].default_value = rgba
    principled.inputs["Roughness"].default_value = roughness
    alpha_input = principled.inputs.get("Alpha")
    if alpha_input is not None:
        alpha_input.default_value = alpha
    transmission_input = principled.inputs.get("Transmission Weight")
    if transmission_input is None:
        transmission_input = principled.inputs.get("Transmission")
    if transmission_input is not None:
        transmission_input.default_value = transmission
    ior = principled.inputs.get("IOR")
    if ior is not None:
        ior.default_value = 1.376
    if alpha < 1.0:
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        elif hasattr(material, "blend_method"):
            material.blend_method = "BLEND"
    return material


def natural_blue_iris_material(name: str, config: Mapping[str, Any]) -> Any:
    settings = config["eye_treatment"]
    base = tuple(float(value) for value in settings["iris_linear_base_rgba"])
    light = tuple(float(value) for value in settings["iris_linear_light_rgba"])
    material = bpy.data.materials.new(name)
    material.diffuse_color = base
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    coordinates = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    angle = nodes.new("ShaderNodeMath")
    angle.operation = "ARCTAN2"
    frequency = nodes.new("ShaderNodeMath")
    frequency.operation = "MULTIPLY"
    frequency.inputs[1].default_value = 22.0
    waves = nodes.new("ShaderNodeMath")
    waves.operation = "SINE"
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 11.0
    noise.inputs["Detail"].default_value = 3.0
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.36
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = base
    ramp.color_ramp.elements[1].color = light
    links.new(coordinates.outputs["Generated"], separate.inputs[0])
    links.new(separate.outputs["Z"], angle.inputs[0])
    links.new(separate.outputs["X"], angle.inputs[1])
    links.new(angle.outputs[0], frequency.inputs[0])
    links.new(frequency.outputs[0], waves.inputs[0])
    links.new(coordinates.outputs["Generated"], noise.inputs["Vector"])
    links.new(waves.outputs[0], mix.inputs[1])
    links.new(noise.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Roughness"].default_value = 0.37
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material["actual_muted_blue_gray_iris_material"] = True
    material["lighting_only_eye_color"] = False
    return material


def build_source_group_mesh(
    *,
    name: str,
    faces: Sequence[Sequence[int]],
    source_vertices: Sequence[Vector],
    scale: float,
    floor_native: float,
    material: Any,
) -> tuple[Any, list[int]]:
    used = sorted({int(index) for face in faces for index in face})
    mapping = {source: local for local, source in enumerate(used)}
    points = []
    for source_index in used:
        point = converted_native(source_vertices[source_index])
        points.append(
            Vector(
                (
                    point.x * scale,
                    point.y * scale,
                    (point.z - floor_native) * scale,
                )
            )
        )
    compact_faces = [tuple(mapping[int(index)] for index in face) for face in faces]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([tuple(point) for point in points], [], compact_faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj, used


def assign_rigid_bone(obj: Any, armature: Any, bone_name: str) -> None:
    if armature.data.bones.get(bone_name) is None:
        raise RobertR26BuildError(f"rigid component bone missing: {bone_name}")
    group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("Robert_R26_Rigid_Official_Bone", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    obj.matrix_world = world


def parent_object_to_bone(obj: Any, armature: Any, bone_name: str) -> None:
    if armature.data.bones.get(bone_name) is None:
        raise RobertR26BuildError(f"component parent bone missing: {bone_name}")
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def component_clearance(body_tree: BVHTree, obj: Any) -> dict[str, Any]:
    distances: list[float] = []
    for vertex in obj.data.vertices:
        nearest = body_tree.find_nearest(obj.matrix_world @ vertex.co)
        if nearest[0] is None:
            raise RobertR26BuildError(f"component clearance query failed: {obj.name}")
        distances.append(float(nearest[3]))
    overlap_count = len(body_tree.overlap(world_surface_bvh(obj)))
    return {
        "minimum_unsigned_body_surface_clearance_m": min(distances),
        "maximum_unsigned_body_surface_clearance_m": max(distances),
        "body_surface_triangle_overlap_count": overlap_count,
    }


def bounded_socket_fit(
    body_tree: BVHTree,
    obj: Any,
    settings: Mapping[str, Any],
) -> dict[str, Any]:
    cumulative = 1.0
    iterations = 0
    record = component_clearance(body_tree, obj)
    while (
        int(record["body_surface_triangle_overlap_count"]) != 0
        or float(record["minimum_unsigned_body_surface_clearance_m"])
        < float(settings["minimum_socket_clearance_m"])
    ) and iterations < int(settings["maximum_fit_iterations"]):
        low, high = object_bounds(obj)
        center = (low + high) * 0.5
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            world.x = center.x + (world.x - center.x) * 0.98
            world.z = center.z + (world.z - center.z) * 0.98
            world.y += 0.00006
            vertex.co = obj.matrix_world.inverted() @ world
        obj.data.update()
        cumulative *= 0.98
        iterations += 1
        record = component_clearance(body_tree, obj)
    passed = (
        int(record["body_surface_triangle_overlap_count"]) == 0
        and float(record["minimum_unsigned_body_surface_clearance_m"])
        >= float(settings["minimum_socket_clearance_m"])
        and cumulative >= float(settings["minimum_cumulative_xz_scale"])
    )
    if not passed:
        raise RobertR26BuildError(
            f"bounded eye socket fit failed: {obj.name}: {record}; scale={cumulative}"
        )
    return {
        **record,
        "fit_iterations": iterations,
        "cumulative_xz_scale": cumulative,
        "bounded_socket_fit_passed": True,
    }


def curved_optical_cap(
    *,
    name: str,
    center: Vector,
    front_y: float,
    radius_x: float,
    radius_z: float,
    depth_m: float,
    materials: Sequence[Any],
    iris: bool,
    segments: int = 64,
    rings: int = 16,
) -> Any:
    points: list[Vector] = [Vector((center.x, front_y - depth_m, center.z))]
    for ring in range(1, rings + 1):
        fraction = ring / rings
        y = front_y - depth_m * (1.0 - fraction * fraction)
        for segment in range(segments):
            angle = math.tau * segment / segments
            points.append(
                Vector(
                    (
                        center.x + math.cos(angle) * radius_x * fraction,
                        y,
                        center.z + math.sin(angle) * radius_z * fraction,
                    )
                )
            )
    faces: list[tuple[int, ...]] = []
    material_rows: list[int] = []
    for segment in range(segments):
        faces.append((0, 1 + segment, 1 + (segment + 1) % segments))
        material_rows.append(0 if iris else 0)
    for ring in range(1, rings):
        inner = 1 + (ring - 1) * segments
        outer = 1 + ring * segments
        for segment in range(segments):
            following = (segment + 1) % segments
            faces.append(
                (
                    inner + segment,
                    outer + segment,
                    outer + following,
                    inner + following,
                )
            )
            if iris:
                fraction = ring / rings
                material_rows.append(0 if fraction <= 0.22 else (2 if fraction >= 0.86 else 1))
            else:
                material_rows.append(0)
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([tuple(point) for point in points], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        obj.data.materials.append(material)
    for polygon, material_index in zip(obj.data.polygons, material_rows):
        polygon.material_index = material_index
        polygon.use_smooth = True
    obj["curved_nonflat_optical_cap"] = True
    obj["flat_optical_disk_used"] = False
    return obj


def add_blue_gray_eyes(
    *,
    body: Any,
    armature: Any,
    config: Mapping[str, Any],
    source_vertices: Sequence[Vector],
    source_groups: Mapping[str, Sequence[Sequence[int]]],
    floor_native: float,
) -> tuple[list[Any], dict[str, Any]]:
    settings = config["eye_treatment"]
    candidate_id = str(config["candidate_id"])
    scale = float(config["foundation_truth"]["native_to_blender_scale"])
    sclera_material = simple_material(
        f"{candidate_id}_Natural_Sclera",
        settings["sclera_linear_rgba"],
        roughness=0.42,
    )
    pupil_material = simple_material(
        f"{candidate_id}_Natural_Pupil",
        settings["pupil_linear_rgba"],
        roughness=0.20,
    )
    iris_material = natural_blue_iris_material(
        f"{candidate_id}_Actual_Muted_Blue_Gray_Iris",
        config,
    )
    limbal_material = simple_material(
        f"{candidate_id}_Muted_Blue_Gray_Limbal_Ring",
        settings["limbal_linear_rgba"],
        roughness=0.34,
    )
    cornea_material = simple_material(
        f"{candidate_id}_Transparent_Cornea",
        (0.93, 0.97, 1.0, 0.12),
        roughness=0.08,
        transmission=1.0,
        alpha=0.12,
    )
    body_tree = world_surface_bvh(body)
    objects: list[Any] = []
    records: dict[str, Any] = {}
    for side, group_name in (("L", "helper-l-eye"), ("R", "helper-r-eye")):
        sclera, source_indices = build_source_group_mesh(
            name=f"{candidate_id}_Official_Helper_Sclera_{side}",
            faces=source_groups[group_name],
            source_vertices=source_vertices,
            scale=scale,
            floor_native=floor_native,
            material=sclera_material,
        )
        low, high = object_bounds(sclera)
        center = (low + high) * 0.5
        for vertex in sclera.data.vertices:
            vertex.co = center + (vertex.co - center) * float(settings["helper_fit_scale"])
            vertex.co.y += float(settings["posterior_inset_m"])
        sclera.data.update()
        sclera_fit = bounded_socket_fit(body_tree, sclera, settings)
        low, high = object_bounds(sclera)
        center = (low + high) * 0.5
        radii = (high - low) * 0.5
        front_y = float(low.y)
        iris = curved_optical_cap(
            name=f"{candidate_id}_Curved_Blue_Gray_Iris_{side}",
            center=center,
            front_y=front_y - 0.00020,
            radius_x=float(radii.x * 0.39),
            radius_z=float(radii.z * 0.39),
            depth_m=0.00036,
            materials=(pupil_material, iris_material, limbal_material),
            iris=True,
        )
        iris_fit = bounded_socket_fit(body_tree, iris, settings)
        cornea = curved_optical_cap(
            name=f"{candidate_id}_Shallow_Transparent_Cornea_{side}",
            center=center,
            front_y=front_y - 0.00062,
            radius_x=float(radii.x * 0.43),
            radius_z=float(radii.z * 0.43),
            depth_m=0.00042,
            materials=(cornea_material,),
            iris=False,
            segments=48,
            rings=14,
        )
        cornea_fit = bounded_socket_fit(body_tree, cornea, settings)
        iris_low, _ = object_bounds(iris)
        cornea_low, _ = object_bounds(cornea)
        separation = float(iris_low.y - cornea_low.y)
        if separation < float(settings["minimum_optical_layer_separation_m"]):
            raise RobertR26BuildError(f"blue-eye optical separation failed: {side}")
        for obj in (sclera, iris, cornea):
            assign_rigid_bone(obj, armature, f"eye.{side}")
            obj["candidate_id"] = candidate_id
            obj["private_owner_review_only"] = True
            obj["inactive_candidate"] = True
            obj["runtime_activation_allowed"] = False
            obj["eye_component"] = True
            obj["static_lid_overlay_used"] = False
            objects.append(obj)
        records[side] = {
            "source_group": group_name,
            "source_vertex_count": len(source_indices),
            "components": [sclera.name, iris.name, cornea.name],
            "sclera_fit": sclera_fit,
            "iris_fit": iris_fit,
            "cornea_fit": cornea_fit,
            "minimum_optical_layer_separation_m": separation,
        }
    return objects, {
        "method": "official_helper_sclera_plus_single_curved_blue_gray_optical_cap_and_shallow_cornea_v1",
        "iris_color_family": settings["iris_color_family"],
        "object_count": len(objects),
        "curved_iris_cap_count": 2,
        "flat_iris_disk_count": 0,
        "static_lid_overlay_count": 0,
        "black_band_object_count": 0,
        "geometric_lid_occlusion_exception_allowed": False,
        "required_body_eye_exact_genuine_intersection_pairs": 0,
        "records": records,
        "owner_visual_acceptance_claimed": False,
    }


def assign_official_group_weights(
    obj: Any,
    source_indices: Sequence[int],
    source_weights: Sequence[Mapping[str, float]],
    armature: Any,
    *,
    maximum_influences: int = 4,
) -> dict[str, Any]:
    normalized: list[list[tuple[str, float]]] = []
    for source_index in source_indices:
        top = sorted(
            source_weights[int(source_index)].items(),
            key=lambda item: (-float(item[1]), str(item[0])),
        )[:maximum_influences]
        total = sum(float(value) for _name, value in top)
        if total <= 1.0e-12:
            raise RobertR26BuildError(
                f"official helper component source vertex is unweighted: {source_index}"
            )
        normalized.append([(str(name), float(value) / total) for name, value in top])
    names = sorted({name for row in normalized for name, _value in row})
    groups = {name: obj.vertex_groups.new(name=name) for name in names}
    assignments = 0
    for vertex_index, row in enumerate(normalized):
        for name, value in row:
            groups[name].add([vertex_index], value, "REPLACE")
            assignments += 1
    modifier = obj.modifiers.new("Robert_R26_Official_Helper_Weights", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    return {
        "weighted_vertex_count": len(normalized),
        "coverage": 1.0,
        "root_fallback_vertex_count": 0,
        "maximum_influences": max(len(row) for row in normalized),
        "vertex_group_count": len(groups),
        "assignment_count": assignments,
    }


def add_official_projected_lashes(
    *,
    body: Any,
    armature: Any,
    config: Mapping[str, Any],
    source_vertices: Sequence[Vector],
    source_groups: Mapping[str, Sequence[Sequence[int]]],
    source_weights: Sequence[Mapping[str, float]],
    floor_native: float,
) -> tuple[list[Any], dict[str, Any]]:
    candidate_id = str(config["candidate_id"])
    scale = float(config["foundation_truth"]["native_to_blender_scale"])
    material = simple_material(
        f"{candidate_id}_Natural_Dark_Blond_Lashes",
        (0.055, 0.035, 0.018, 1.0),
        roughness=0.64,
    )
    body_tree = world_surface_bvh(body)
    objects: list[Any] = []
    records: list[dict[str, Any]] = []
    for group_name in (
        "helper-l-eyelashes-1",
        "helper-l-eyelashes-2",
        "helper-r-eyelashes-1",
        "helper-r-eyelashes-2",
    ):
        obj, source_indices = build_source_group_mesh(
            name=f"{candidate_id}_{group_name.replace('helper-', '').replace('-', '_')}",
            faces=source_groups[group_name],
            source_vertices=source_vertices,
            scale=scale,
            floor_native=floor_native,
            material=material,
        )
        projection_distances: list[float] = []
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            nearest, normal, _face, distance = body_tree.find_nearest(world)
            if nearest is None or normal is None:
                raise RobertR26BuildError(f"lash projection failed: {obj.name}")
            distance = float(distance)
            if distance > 0.02:
                raise RobertR26BuildError(
                    f"lash projection exceeded bounded fit: {obj.name}: {distance}"
                )
            outward = Vector(normal).normalized()
            if outward.y > 0.0:
                outward.negate()
            vertex.co = obj.matrix_world.inverted() @ (
                Vector(nearest) + outward * 0.00028
            )
            projection_distances.append(distance)
        obj.data.update(calc_edges=True)
        weight_record = assign_official_group_weights(
            obj,
            source_indices,
            source_weights,
            armature,
        )
        obj["candidate_id"] = candidate_id
        obj["official_makehuman_lash_geometry"] = True
        obj["skin_projected_for_v8_socket_fit"] = True
        obj["private_owner_review_only"] = True
        obj["runtime_activation_allowed"] = False
        objects.append(obj)
        records.append(
            {
                "object": obj.name,
                "source_group": group_name,
                "source_vertex_count": len(source_indices),
                "projection_distance_minimum_m": min(projection_distances),
                "projection_distance_maximum_m": max(projection_distances),
                "official_weights": weight_record,
            }
        )
    return objects, {
        "method": "official_makehuman_lash_helpers_projected_to_bounded_v8_lids_with_official_weights",
        "object_count": len(objects),
        "source_group_count": 4,
        "root_fallback_vertex_count": 0,
        "records": records,
        "visual_lash_acceptance_claimed": False,
    }


def add_projected_strand_brows(
    *,
    body: Any,
    armature: Any,
    config: Mapping[str, Any],
    eye_objects: Sequence[Any],
) -> tuple[list[Any], dict[str, Any]]:
    settings = config["brow_treatment"]
    candidate_id = str(config["candidate_id"])
    body_tree = world_surface_bvh(body)
    material = simple_material(
        f"{candidate_id}_Natural_Dark_Blond_Brows",
        (0.12, 0.067, 0.025, 1.0),
        roughness=0.62,
    )
    sclerae = {
        side: next(
            obj
            for obj in eye_objects
            if obj.name.endswith(f"Official_Helper_Sclera_{side}")
        )
        for side in ("L", "R")
    }
    records: dict[str, Any] = {}
    objects: list[Any] = []
    strand_count = int(settings["strands_per_side"])
    for side, sclera in sclerae.items():
        low, high = object_bounds(sclera)
        eye_center = (low + high) * 0.5
        eye_width = float(high.x - low.x)
        eye_height = float(high.z - low.z)
        curve = bpy.data.curves.new(f"{candidate_id}_Projected_Eyebrow_{side}_data", "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2
        curve.bevel_depth = float(settings["strand_radius_m"])
        curve.bevel_resolution = 2
        projection_distances: list[float] = []
        root_points: list[Vector] = []
        for strand_index in range(strand_count):
            fraction = strand_index / max(1, strand_count - 1)
            direction = -1.0 if side == "L" else 1.0
            x = eye_center.x + direction * (fraction - 0.5) * eye_width * 1.34
            arch = math.sin(math.pi * fraction)
            z = eye_center.z + eye_height * (0.70 + 0.28 * arch - 0.08 * fraction)
            # Start from a guide within the official fitted eye volume, not a
            # distant camera-like ray. The configured projection maximum is
            # therefore a real guide-to-skin fit bound and cannot be replaced
            # by a zero-distance query at the already projected hit.
            guide = Vector((x, eye_center.y, z))
            hit, normal, _face, distance = body_tree.find_nearest(guide)
            if hit is None or normal is None:
                raise RobertR26BuildError(f"brow projection failed: {side}:{strand_index}")
            projection_distance = float(distance)
            if projection_distance > float(settings["maximum_projection_distance_m"]):
                raise RobertR26BuildError(
                    f"brow guide-to-skin projection exceeded bound: "
                    f"{side}:{strand_index}:{projection_distance}"
                )
            outward = Vector(normal).normalized()
            if outward.y >= -0.15:
                raise RobertR26BuildError(
                    f"brow projection did not reach anterior brow skin: "
                    f"{side}:{strand_index}:{tuple(outward)}"
                )
            root = Vector(hit) + outward * float(settings["root_clearance_m"])
            tangent = Vector((direction * eye_width * 0.018, 0.0, eye_height * 0.035))
            length = 0.0052 + arch * 0.0018
            spline = curve.splines.new("POLY")
            spline.points.add(2)
            controls = (
                root,
                root + outward * (length * 0.58) + tangent,
                root + outward * length + tangent * 1.55,
            )
            for point, value in zip(spline.points, controls):
                point.co = (*value, 1.0)
            projection_distances.append(projection_distance)
            root_points.append(root)
        obj = bpy.data.objects.new(f"{candidate_id}_Projected_Strand_Eyebrow_{side}", curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(material)
        parent_object_to_bone(obj, armature, "head")
        obj["candidate_id"] = candidate_id
        obj["individual_projected_strands"] = True
        obj["single_thick_curve_used"] = False
        obj["brow_plate_used"] = False
        obj["painted_brow_used"] = False
        obj["private_owner_review_only"] = True
        obj["runtime_activation_allowed"] = False
        objects.append(obj)
        records[side] = {
            "object": obj.name,
            "strand_count": len(curve.splines),
            "controls_per_strand": int(settings["controls_per_strand"]),
            "root_projection_distance_minimum_m": min(projection_distances),
            "root_projection_distance_maximum_m": max(projection_distances),
            "required_projection_distance_maximum_m": float(
                settings["maximum_projection_distance_m"]
            ),
            "root_clearance_m": float(settings["root_clearance_m"]),
            "projection_bound_passed": max(projection_distances)
            <= float(settings["maximum_projection_distance_m"]),
            "root_point_sha256": point_signature(root_points),
        }
    if sum(len(obj.data.splines) for obj in objects) != strand_count * 2:
        raise RobertR26BuildError("projected brow strand inventory failed")
    return objects, {
        "method": settings["representation"],
        "object_count": len(objects),
        "strand_count_total": sum(len(obj.data.splines) for obj in objects),
        "single_thick_curve_count": 0,
        "plate_or_painted_brow_count": 0,
        "records": records,
        "owner_visual_acceptance_claimed": False,
    }


def reset_pose(armature: Any) -> None:
    armature.animation_data_create()
    armature.animation_data.action = None
    for bone in armature.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def set_pose_transforms(armature: Any, spec: Mapping[str, Any]) -> None:
    """Apply a pose without changing action assignment or scene frame."""

    for bone_name, row in spec.get("rotations", {}).items():
        bone = armature.pose.bones.get(str(bone_name))
        if bone is None:
            raise RobertR26BuildError(f"pose rotation bone missing: {bone_name}")
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = Quaternion(
            Vector(tuple(float(value) for value in row["axis"])),
            math.radians(float(row["degrees"])),
        )
    for bone_name, raw_location in spec.get("locations", {}).items():
        bone = armature.pose.bones.get(str(bone_name))
        if bone is None:
            raise RobertR26BuildError(f"pose location bone missing: {bone_name}")
        bone.location = tuple(float(value) for value in raw_location)


def apply_pose_spec(armature: Any, spec: Mapping[str, Any]) -> None:
    reset_pose(armature)
    set_pose_transforms(armature, spec)
    bpy.context.scene.frame_set(int(spec.get("frame", 30)))
    bpy.context.view_layer.update()


def evaluated_vertices(obj: Any) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def evaluated_mesh_data(obj: Any) -> tuple[Any, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    return evaluated, evaluated.to_mesh()


def exact_evaluated_self_intersections(obj: Any) -> dict[str, Any]:
    auditor = import_module(INTERSECTION_AUDITOR, "robert_r26_exact_intersections_pose")
    evaluated, mesh = evaluated_mesh_data(obj)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.transform(bm, matrix=evaluated.matrix_world, verts=list(bm.verts))
        return auditor.exact_nonadjacent_intersection_report(
            bm,
            include_pair_details=True,
        )
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def bounds_record(points: Sequence[Vector]) -> dict[str, list[float]]:
    return {
        "low": [min(float(point[axis]) for point in points) for axis in range(3)],
        "high": [max(float(point[axis]) for point in points) for axis in range(3)],
        "size": [
            max(float(point[axis]) for point in points)
            - min(float(point[axis]) for point in points)
            for axis in range(3)
        ],
    }


def quantile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def exact_cross_intersections(
    primary: Any,
    components: Sequence[Any],
) -> dict[str, Any]:
    auditor = import_module(INTERSECTION_AUDITOR, "robert_r26_exact_cross")
    primary_eval, primary_mesh = evaluated_mesh_data(primary)
    primary_mesh.calc_loop_triangles()
    primary_points = [primary_eval.matrix_world @ vertex.co for vertex in primary_mesh.vertices]
    primary_triangles = [
        tuple(int(value) for value in triangle.vertices)
        for triangle in primary_mesh.loop_triangles
    ]
    primary_tree = BVHTree.FromPolygons(
        primary_points,
        primary_triangles,
        all_triangles=True,
    )
    diagonal = (Vector(bounds_record(primary_points)["high"]) - Vector(bounds_record(primary_points)["low"])).length
    tolerance = max(1.0e-10, diagonal * 1.0e-8)
    records: list[dict[str, Any]] = []
    total_genuine = 0
    try:
        for component in components:
            component_eval, component_mesh = evaluated_mesh_data(component)
            try:
                component_mesh.calc_loop_triangles()
                component_points = [
                    component_eval.matrix_world @ vertex.co
                    for vertex in component_mesh.vertices
                ]
                component_triangles = [
                    tuple(int(value) for value in triangle.vertices)
                    for triangle in component_mesh.loop_triangles
                ]
                tree = BVHTree.FromPolygons(
                    component_points,
                    component_triangles,
                    all_triangles=True,
                )
                overlaps = primary_tree.overlap(tree)
                genuine = 0
                touches = 0
                for primary_index, component_index in overlaps:
                    result = auditor.classify_triangle_pair(
                        tuple(primary_points[index] for index in primary_triangles[primary_index]),
                        tuple(component_points[index] for index in component_triangles[component_index]),
                        linear_tolerance=tolerance,
                    )
                    if result.get("genuine_penetration") is True:
                        genuine += 1
                    elif result.get("classification") != "bvh_aabb_only":
                        touches += 1
                total_genuine += genuine
                records.append(
                    {
                        "object": component.name,
                        "bvh_triangle_pair_count": len(overlaps),
                        "exact_genuine_triangle_pair_count": genuine,
                        "touch_or_coplanar_triangle_pair_count": touches,
                    }
                )
            finally:
                component_eval.to_mesh_clear()
    finally:
        primary_eval.to_mesh_clear()
    return {
        "method": "evaluated_BVH_broad_phase_plus_exact_triangle_narrow_phase",
        "component_count": len(components),
        "total_exact_genuine_triangle_pair_count": total_genuine,
        "records": records,
    }


def weighted_region_indices(
    body: Any,
    prefixes: Sequence[str],
    minimum_weight: float,
) -> list[int]:
    lower_prefixes = tuple(str(value).lower() for value in prefixes)
    group_indices = {
        group.index
        for group in body.vertex_groups
        if group.name.lower().startswith(lower_prefixes)
    }
    return [
        int(vertex.index)
        for vertex in body.data.vertices
        if any(
            assignment.group in group_indices
            and float(assignment.weight) >= minimum_weight
            for assignment in vertex.groups
        )
    ]


def edge_stretch_report(
    body: Any,
    neutral: Sequence[Vector],
    posed: Sequence[Vector],
    knee_indices: set[int],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    ratios: list[float] = []
    knees: list[float] = []
    for edge in body.data.edges:
        first, second = map(int, edge.vertices)
        before = (neutral[first] - neutral[second]).length
        after = (posed[first] - posed[second]).length
        if before <= 1.0e-10:
            continue
        ratio = after / before
        ratios.append(ratio)
        if first in knee_indices or second in knee_indices:
            knees.append(ratio)
    minimum_allowed = float(config["movement"]["minimum_pose_edge_ratio"])
    maximum_allowed = float(config["movement"]["maximum_pose_edge_ratio"])
    passed = (
        bool(ratios)
        and min(ratios) >= minimum_allowed
        and max(ratios) <= maximum_allowed
    )
    body.data.calc_loop_triangles()
    area_ratios: list[float] = []
    knee_area_ratios: list[float] = []
    for triangle in body.data.loop_triangles:
        first, second, third = map(int, triangle.vertices)
        before_area = (neutral[second] - neutral[first]).cross(
            neutral[third] - neutral[first]
        ).length * 0.5
        after_area = (posed[second] - posed[first]).cross(
            posed[third] - posed[first]
        ).length * 0.5
        if before_area <= 1.0e-12:
            continue
        ratio = after_area / before_area
        area_ratios.append(ratio)
        if first in knee_indices or second in knee_indices or third in knee_indices:
            knee_area_ratios.append(ratio)
    knee_p05_minimum = float(config["movement"]["minimum_knee_area_ratio_p05"])
    knee_p95_maximum = float(config["movement"]["maximum_knee_area_ratio_p95"])
    knee_p05 = quantile(knee_area_ratios, 0.05)
    knee_p95 = quantile(knee_area_ratios, 0.95)
    area_passed = (
        bool(area_ratios)
        and bool(knee_area_ratios)
        and knee_p05 >= knee_p05_minimum
        and knee_p95 <= knee_p95_maximum
    )
    return {
        "edge_count": len(ratios),
        "minimum_ratio": min(ratios, default=1.0),
        "median_ratio": statistics.median(ratios) if ratios else 1.0,
        "p95_ratio": quantile(ratios, 0.95),
        "maximum_ratio": max(ratios, default=1.0),
        "knee_edge_count": len(knees),
        "knee_minimum_ratio": min(knees, default=1.0),
        "knee_p95_ratio": quantile(knees, 0.95),
        "knee_maximum_ratio": max(knees, default=1.0),
        "required_ratio_range": [minimum_allowed, maximum_allowed],
        "area_ratio": {
            "triangle_count": len(area_ratios),
            "minimum": min(area_ratios, default=1.0),
            "p05": quantile(area_ratios, 0.05),
            "median": statistics.median(area_ratios) if area_ratios else 1.0,
            "p95": quantile(area_ratios, 0.95),
            "maximum": max(area_ratios, default=1.0),
            "knee_triangle_count": len(knee_area_ratios),
            "knee_p05": knee_p05,
            "knee_p95": knee_p95,
            "required_knee_p05_minimum": knee_p05_minimum,
            "required_knee_p95_maximum": knee_p95_maximum,
            "passed": area_passed,
        },
        "passed": passed and area_passed,
    }


def leg_points(armature: Any, side: str) -> dict[str, Vector]:
    names = (
        f"upperleg02.{side}",
        f"lowerleg01.{side}",
        f"lowerleg02.{side}",
    )
    if any(armature.pose.bones.get(name) is None for name in names):
        raise RobertR26BuildError(f"official leg chain missing: {side}")
    upper, lower, ankle = (armature.pose.bones[name] for name in names)
    return {
        "hip": armature.matrix_world @ upper.head,
        "knee": armature.matrix_world @ lower.head,
        "ankle": armature.matrix_world @ ankle.tail,
    }


def leg_flexion(points: Mapping[str, Vector]) -> float:
    upper = points["knee"] - points["hip"]
    lower = points["ankle"] - points["knee"]
    cosine = max(-1.0, min(1.0, upper.normalized().dot(lower.normalized())))
    return math.degrees(math.acos(cosine))


def solve_knee_axes(armature: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    axes = {
        "LOCAL_X": Vector((1.0, 0.0, 0.0)),
        "LOCAL_Y": Vector((0.0, 1.0, 0.0)),
        "LOCAL_Z": Vector((0.0, 0.0, 1.0)),
    }
    solutions: dict[str, Any] = {}
    for side in ("L", "R"):
        reset_pose(armature)
        rest = leg_points(armature, side)
        rest_flexion = leg_flexion(rest)
        bone = armature.pose.bones[f"lowerleg01.{side}"]
        candidates: list[dict[str, Any]] = []
        for axis_name, axis in axes.items():
            for sign in (-1, 1):
                reset_pose(armature)
                bone = armature.pose.bones[f"lowerleg01.{side}"]
                bone.rotation_quaternion = Quaternion(axis, math.radians(sign * 55.0))
                bpy.context.view_layer.update()
                posed = leg_points(armature, side)
                displacement = posed["ankle"] - rest["ankle"]
                candidates.append(
                    {
                        "axis_name": axis_name,
                        "axis": [float(value) for value in axis],
                        "sign": sign,
                        "posterior_displacement_m": float(displacement.y),
                        "lateral_displacement_m": abs(float(displacement.x)),
                        "flexion_degrees": leg_flexion(posed),
                        "flexion_change_degrees": abs(
                            leg_flexion(posed) - rest_flexion
                        ),
                    }
                )
        valid = [
            row
            for row in candidates
            if float(row["posterior_displacement_m"]) > 0.01
            and float(row["lateral_displacement_m"])
            <= max(0.02, float(row["posterior_displacement_m"]) * 0.5)
        ]
        if not valid:
            raise RobertR26BuildError(f"no measured posterior knee axis: {side}")
        selected = min(
            valid,
            key=lambda row: (
                abs(float(row["flexion_change_degrees"]) - 55.0),
                float(row["lateral_displacement_m"]),
            ),
        )
        angular_error = abs(float(selected["flexion_change_degrees"]) - 55.0)
        if angular_error > float(config["movement"]["knee_angle_tolerance_degrees"]):
            raise RobertR26BuildError(
                f"measured knee-axis calibration exceeded tolerance: {side}: {angular_error}"
            )
        solutions[side] = {
            **selected,
            "bone": f"lowerleg01.{side}",
            "candidate_count": len(candidates),
            "valid_candidate_count": len(valid),
            "calibration_error_degrees": angular_error,
        }
    reset_pose(armature)
    return solutions


def solve_hip_axis(armature: Any, side: str) -> dict[str, Any]:
    axes = {
        "LOCAL_X": Vector((1.0, 0.0, 0.0)),
        "LOCAL_Y": Vector((0.0, 1.0, 0.0)),
        "LOCAL_Z": Vector((0.0, 0.0, 1.0)),
    }
    reset_pose(armature)
    rest = leg_points(armature, side)
    candidates: list[dict[str, Any]] = []
    for axis_name, axis in axes.items():
        for sign in (-1, 1):
            reset_pose(armature)
            bone = armature.pose.bones[f"upperleg01.{side}"]
            bone.rotation_quaternion = Quaternion(axis, math.radians(sign * 75.0))
            bpy.context.view_layer.update()
            posed = leg_points(armature, side)
            displacement = posed["knee"] - rest["knee"]
            candidates.append(
                {
                    "axis_name": axis_name,
                    "axis": [float(value) for value in axis],
                    "sign": sign,
                    "anterior_displacement_m": -float(displacement.y),
                    "lateral_displacement_m": abs(float(displacement.x)),
                    "vertical_displacement_m": float(displacement.z),
                }
            )
    valid = [
        row
        for row in candidates
        if float(row["anterior_displacement_m"]) > 0.08
        and float(row["lateral_displacement_m"]) < 0.08
    ]
    if not valid:
        raise RobertR26BuildError(f"no measured seated hip axis: {side}")
    selected = max(
        valid,
        key=lambda row: float(row["anterior_displacement_m"])
        - float(row["lateral_displacement_m"]) * 1.5,
    )
    reset_pose(armature)
    return {**selected, "bone": f"upperleg01.{side}"}


def solve_root_region_to_fixed_plane(
    *,
    armature: Any,
    body: Any,
    base_spec: Mapping[str, Any],
    region_indices: Sequence[int],
    plane_z_m: float,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not region_indices:
        raise RobertR26BuildError("fixed-plane root solver received an empty region")
    clearance = float(config["support_targets"]["surface_clearance_m"])
    probe = float(config["support_targets"]["root_translation_probe_m"])
    desired_minimum = float(plane_z_m) + clearance

    def region_minimum_z() -> float:
        points = evaluated_vertices(body)
        return min(float(points[int(index)].z) for index in region_indices)

    apply_pose_spec(armature, base_spec)
    baseline = region_minimum_z()
    axis_records: list[dict[str, Any]] = []
    for axis_index, axis_name in enumerate(("LOCAL_X", "LOCAL_Y", "LOCAL_Z")):
        apply_pose_spec(armature, base_spec)
        root = armature.pose.bones.get("root")
        if root is None:
            raise RobertR26BuildError("official root bone missing")
        location = Vector((0.0, 0.0, 0.0))
        location[axis_index] = probe
        root.location = location
        bpy.context.view_layer.update()
        moved = region_minimum_z()
        gain = (moved - baseline) / probe
        axis_records.append(
            {
                "axis_name": axis_name,
                "axis_index": axis_index,
                "world_z_gain_per_local_m": gain,
            }
        )
    usable = [row for row in axis_records if abs(float(row["world_z_gain_per_local_m"])) >= 0.20]
    if not usable:
        reset_pose(armature)
        raise RobertR26BuildError("root solver found no reliable world-Z translation axis")
    selected = max(usable, key=lambda row: abs(float(row["world_z_gain_per_local_m"])))
    gain = float(selected["world_z_gain_per_local_m"])
    amount = (desired_minimum - baseline) / gain
    maximum = float(config["support_targets"]["maximum_absolute_root_translation_m"])
    if abs(amount) > maximum:
        reset_pose(armature)
        raise RobertR26BuildError(
            f"fixed-plane root translation exceeds bound: {amount} m"
        )
    location = [0.0, 0.0, 0.0]
    location[int(selected["axis_index"])] = amount
    solved_spec = {
        "frame": int(base_spec.get("frame", config["movement"]["pose_frame"])),
        "rotations": dict(base_spec.get("rotations", {})),
        "locations": {**dict(base_spec.get("locations", {})), "root": location},
    }
    apply_pose_spec(armature, solved_spec)
    achieved = region_minimum_z()
    residual = achieved - desired_minimum
    if abs(residual) > float(config["movement"]["contact_tolerance_m"]) * 0.25:
        amount -= residual / gain
        if abs(amount) > maximum:
            reset_pose(armature)
            raise RobertR26BuildError("refined root translation exceeds bound")
        location[int(selected["axis_index"])] = amount
        solved_spec["locations"]["root"] = location
        apply_pose_spec(armature, solved_spec)
        achieved = region_minimum_z()
        residual = achieved - desired_minimum
    tolerance = float(config["movement"]["contact_tolerance_m"]) * 0.25
    if abs(residual) > tolerance:
        reset_pose(armature)
        raise RobertR26BuildError(
            f"fixed-plane root solver residual failed: {residual} m"
        )
    reset_pose(armature)
    return solved_spec, {
        "method": "measured_root_local_axis_to_fixed_world_support_plane",
        "fixed_plane_z_m": float(plane_z_m),
        "required_surface_clearance_m": clearance,
        "baseline_region_minimum_z_m": baseline,
        "desired_region_minimum_z_m": desired_minimum,
        "achieved_region_minimum_z_m": achieved,
        "residual_m": residual,
        "selected_axis": selected,
        "root_location": location,
        "axis_probe_records": axis_records,
        "passed": abs(residual) <= tolerance,
    }


def solve_seated_pose(
    armature: Any,
    body: Any,
    knees: Mapping[str, Mapping[str, Any]],
    hips: Mapping[str, Mapping[str, Any]],
    region_map: Mapping[str, Sequence[int]],
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select one symmetric seated pose from the configured bounded grid."""

    candidates: list[dict[str, Any]] = []
    frame = int(config["movement"]["pose_frame"])
    for hip_degrees in config["movement"]["seat_hip_search_degrees"]:
        for knee_degrees in config["movement"]["seat_knee_search_degrees"]:
            base_spec: dict[str, Any] = {
                "frame": frame,
                "rotations": {
                    **{
                        hips[side]["bone"]: {
                            "axis": hips[side]["axis"],
                            "degrees": int(hips[side]["sign"]) * float(hip_degrees),
                        }
                        for side in ("L", "R")
                    },
                    **{
                        knees[side]["bone"]: {
                            "axis": knees[side]["axis"],
                            "degrees": int(knees[side]["sign"]) * float(knee_degrees),
                        }
                        for side in ("L", "R")
                    },
                },
                "locations": {},
            }
            spec, root_solution = solve_root_region_to_fixed_plane(
                armature=armature,
                body=body,
                base_spec=base_spec,
                region_indices=region_map["pelvis"],
                plane_z_m=float(config["support_targets"]["seat_top_z_m"]),
                config=config,
            )
            apply_pose_spec(armature, spec)
            legs = {side: leg_points(armature, side) for side in ("L", "R")}
            shape_scores: list[float] = []
            for side in ("L", "R"):
                thigh = legs[side]["knee"] - legs[side]["hip"]
                shank = legs[side]["ankle"] - legs[side]["knee"]
                if thigh.length <= 1.0e-8 or shank.length <= 1.0e-8:
                    raise RobertR26BuildError("seated solver encountered zero leg segment")
                thigh_vertical_fraction = abs(float(thigh.z)) / thigh.length
                shank_horizontal_fraction = math.sqrt(
                    float(shank.x) ** 2 + float(shank.y) ** 2
                ) / shank.length
                shape_scores.extend((thigh_vertical_fraction, shank_horizontal_fraction))
            body_intersections = exact_evaluated_self_intersections(body)
            ankle_height_delta = abs(
                float(legs["L"]["ankle"].z - legs["R"]["ankle"].z)
            )
            knee_lateral_asymmetry = abs(
                abs(float(legs["L"]["knee"].x))
                - abs(float(legs["R"]["knee"].x))
            )
            collision_count = int(
                body_intersections["exact_genuine_penetration_pair_count"]
            )
            body_points = evaluated_vertices(body)
            contact = contact_metrics(
                "seated_contact",
                body_points,
                region_map,
                config,
            )
            candidates.append(
                {
                    "hip_degrees": float(hip_degrees),
                    "knee_degrees": float(knee_degrees),
                    "pose_spec": spec,
                    "fixed_support_contact": contact,
                    "root_plane_solution": root_solution,
                    "mean_seated_shape_error": sum(shape_scores) / len(shape_scores),
                    "ankle_height_delta_m": ankle_height_delta,
                    "knee_lateral_asymmetry_m": knee_lateral_asymmetry,
                    "exact_self_intersection_pair_count": collision_count,
                    "score": (
                        collision_count * 1000.0
                        + sum(shape_scores) / len(shape_scores)
                        + ankle_height_delta * 5.0
                        + knee_lateral_asymmetry * 2.0
                    ),
                }
            )
    valid = [
        row
        for row in candidates
        if int(row["exact_self_intersection_pair_count"]) == 0
        and contact_gate(row["fixed_support_contact"])
    ]
    if not valid:
        reset_pose(armature)
        raise RobertR26BuildError(
            "bounded seated search found no fixed-contact zero-intersection candidate"
        )
    selected = min(valid, key=lambda row: float(row["score"]))
    reset_pose(armature)
    return dict(selected["pose_spec"]), {
        "method": "configured_symmetric_hip_knee_grid_plus_exact_surface_gate",
        "candidate_count": len(candidates),
        "zero_intersection_candidate_count": len(valid),
        "selected": {
            key: value for key, value in selected.items() if key != "pose_spec"
        },
        "candidates": [
            {key: value for key, value in row.items() if key != "pose_spec"}
            for row in candidates
        ],
    }


def solve_supine_root(
    armature: Any,
    body: Any,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for axis_name, axis in (
        ("LOCAL_X", Vector((1.0, 0.0, 0.0))),
        ("LOCAL_Y", Vector((0.0, 1.0, 0.0))),
        ("LOCAL_Z", Vector((0.0, 0.0, 1.0))),
    ):
        for sign in (-1, 1):
            reset_pose(armature)
            root = armature.pose.bones.get("root")
            if root is None:
                raise RobertR26BuildError("official root bone missing")
            root.rotation_quaternion = Quaternion(axis, math.radians(sign * 90.0))
            bpy.context.view_layer.update()
            points = evaluated_vertices(body)
            box = bounds_record(points)
            size = box["size"]
            candidates.append(
                {
                    "axis_name": axis_name,
                    "axis": [float(value) for value in axis],
                    "sign": sign,
                    "bounds": box,
                    "vertical_extent_m": float(size[2]),
                    "horizontal_extent_m": max(float(size[0]), float(size[1])),
                }
            )
    valid = [
        row
        for row in candidates
        if float(row["horizontal_extent_m"]) > float(row["vertical_extent_m"]) * 2.0
    ]
    if not valid:
        raise RobertR26BuildError("no measured whole-body supine root orientation")
    solved_candidates: list[dict[str, Any]] = []
    all_indices = list(range(len(body.data.vertices)))
    for row in valid:
        base_spec = {
            "frame": int(config["movement"]["pose_frame"]),
            "rotations": {
                "root": {
                    "axis": row["axis"],
                    "degrees": int(row["sign"]) * 90.0,
                }
            },
            "locations": {},
        }
        solved_spec, fixed_plane = solve_root_region_to_fixed_plane(
            armature=armature,
            body=body,
            base_spec=base_spec,
            region_indices=all_indices,
            plane_z_m=float(config["support_targets"]["world_floor_z_m"]),
            config=config,
        )
        apply_pose_spec(armature, solved_spec)
        body_points = evaluated_vertices(body)
        contact = contact_metrics(
            "supine_lying_contact",
            body_points,
            {},
            config,
        )
        exact = exact_evaluated_self_intersections(body)
        solved_candidates.append(
            {
                **row,
                "pose_spec": solved_spec,
                "fixed_support_plane_solution": fixed_plane,
                "fixed_support_contact": contact,
                "exact_self_intersection_pair_count": int(
                    exact["exact_genuine_penetration_pair_count"]
                ),
            }
        )
    accepted = [
        row
        for row in solved_candidates
        if contact_gate(row["fixed_support_contact"])
        and int(row["exact_self_intersection_pair_count"]) == 0
    ]
    if not accepted:
        reset_pose(armature)
        raise RobertR26BuildError(
            "no fixed-plane supine orientation passed contact and exact geometry"
        )
    selected = min(accepted, key=lambda row: float(row["vertical_extent_m"]))
    reset_pose(armature)
    return {
        **{key: value for key, value in selected.items() if key != "pose_spec"},
        "bone": "root",
        "degrees": int(selected["sign"]) * 90.0,
        "location": selected["pose_spec"]["locations"]["root"],
        "candidate_count": len(candidates),
        "geometrically_oriented_candidate_count": len(valid),
        "fixed_contact_zero_intersection_candidate_count": len(accepted),
    }


def solve_reach(
    armature: Any,
    body: Any,
    region_map: Mapping[str, Sequence[int]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    axes = (
        ("LOCAL_X", Vector((1.0, 0.0, 0.0))),
        ("LOCAL_Y", Vector((0.0, 1.0, 0.0))),
        ("LOCAL_Z", Vector((0.0, 0.0, 1.0))),
    )
    reset_pose(armature)
    shoulder = armature.matrix_world @ armature.pose.bones["upperarm01.L"].head
    rest_hand = armature.matrix_world @ armature.pose.bones["wrist.L"].tail
    neutral_body_points = evaluated_vertices(body)
    neutral_hand_minimum_z = min(
        float(neutral_body_points[index].z) for index in region_map["left_hand"]
    )
    wrist_to_hand_low_offset = float(rest_hand.z) - neutral_hand_minimum_z
    target = Vector(
        (
            shoulder.x * 0.32,
            shoulder.y - 0.34,
            float(config["support_targets"]["table_top_z_m"])
            + float(config["support_targets"]["surface_clearance_m"])
            + wrist_to_hand_low_offset,
        )
    )
    candidates: list[dict[str, Any]] = []
    for upper_axis_name, upper_axis in axes:
        for upper_sign in (-1, 1):
            for upper_degrees in config["movement"]["reach_upperarm_search_degrees"]:
                for lower_axis_name, lower_axis in axes:
                    for lower_sign in (-1, 1):
                        for lower_degrees in config["movement"]["reach_forearm_search_degrees"]:
                            reset_pose(armature)
                            upper = armature.pose.bones["upperarm01.L"]
                            lower = armature.pose.bones["lowerarm01.L"]
                            upper.rotation_quaternion = Quaternion(
                                upper_axis,
                                math.radians(upper_sign * float(upper_degrees)),
                            )
                            lower.rotation_quaternion = Quaternion(
                                lower_axis,
                                math.radians(lower_sign * float(lower_degrees)),
                            )
                            bpy.context.view_layer.update()
                            hand = armature.matrix_world @ armature.pose.bones["wrist.L"].tail
                            candidates.append(
                                {
                                    "upper": {
                                        "bone": "upperarm01.L",
                                        "axis_name": upper_axis_name,
                                        "axis": [float(value) for value in upper_axis],
                                        "degrees": upper_sign * float(upper_degrees),
                                    },
                                    "lower": {
                                        "bone": "lowerarm01.L",
                                        "axis_name": lower_axis_name,
                                        "axis": [float(value) for value in lower_axis],
                                        "degrees": lower_sign * float(lower_degrees),
                                    },
                                    "hand": [float(value) for value in hand],
                                    "target_error_m": float((hand - target).length),
                                    "forward_displacement_m": -float(hand.y - rest_hand.y),
                                }
                            )
    valid = [
        row
        for row in candidates
        if float(row["forward_displacement_m"]) > 0.08
    ]
    if not valid:
        raise RobertR26BuildError("no measured forward reach solution")
    mesh_candidates: list[dict[str, Any]] = []
    for row in sorted(valid, key=lambda value: float(value["target_error_m"]))[
        : int(config["support_targets"]["maximum_reach_mesh_candidates"])
    ]:
        spec = {
            "frame": int(config["movement"]["pose_frame"]),
            "rotations": {
                row["upper"]["bone"]: {
                    "axis": row["upper"]["axis"],
                    "degrees": row["upper"]["degrees"],
                },
                row["lower"]["bone"]: {
                    "axis": row["lower"]["axis"],
                    "degrees": row["lower"]["degrees"],
                },
            },
            "locations": {},
        }
        apply_pose_spec(armature, spec)
        contact = contact_metrics(
            "table_reach_eating_foundation",
            evaluated_vertices(body),
            region_map,
            config,
        )
        contact_passed = contact_gate(contact)
        exact_count = (
            int(
                exact_evaluated_self_intersections(body)[
                    "exact_genuine_penetration_pair_count"
                ]
            )
            if contact_passed
            else -1
        )
        mesh_candidates.append(
            {
                **row,
                "fixed_table_contact": contact,
                "fixed_table_contact_passed": contact_passed,
                "exact_self_intersection_pair_count": exact_count,
            }
        )
    contact_valid = [
        row
        for row in mesh_candidates
        if bool(row["fixed_table_contact_passed"])
        and int(row["exact_self_intersection_pair_count"]) == 0
    ]
    if not contact_valid:
        reset_pose(armature)
        raise RobertR26BuildError(
            "bounded reach search found no fixed-table zero-intersection candidate"
        )
    selected = min(contact_valid, key=lambda row: float(row["target_error_m"]))
    if float(selected["target_error_m"]) > 0.30:
        raise RobertR26BuildError(
            f"bounded reach target fit failed: {selected['target_error_m']}"
        )
    reset_pose(armature)
    return {
        **selected,
        "target_m": [float(value) for value in target],
        "wrist_to_hand_low_offset_m": wrist_to_hand_low_offset,
        "candidate_count": len(candidates),
        "valid_candidate_count": len(valid),
        "mesh_contact_candidate_count": len(mesh_candidates),
        "fixed_table_contact_candidate_count": len(contact_valid),
    }


def build_pose_specs(
    armature: Any,
    body: Any,
    region_map: Mapping[str, Sequence[int]],
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    knees = solve_knee_axes(armature, config)
    hips = {side: solve_hip_axis(armature, side) for side in ("L", "R")}
    seated_spec, seated = solve_seated_pose(
        armature,
        body,
        knees,
        hips,
        region_map,
        config,
    )
    supine = solve_supine_root(armature, body, config)
    reach = solve_reach(armature, body, region_map, config)
    frame = int(config["movement"]["pose_frame"])
    poses: dict[str, Any] = {"neutral_standing": {"frame": frame, "rotations": {}, "locations": {}}}
    for side_name, side in (("left", "L"), ("right", "R")):
        solution = knees[side]
        for degrees in config["movement"]["knee_gate_degrees"]:
            poses[f"{side_name}_knee_{int(degrees)}"] = {
                "frame": frame,
                "rotations": {
                    solution["bone"]: {
                        "axis": solution["axis"],
                        "degrees": int(solution["sign"]) * float(degrees),
                    }
                },
                "locations": {},
            }
    for degrees in config["movement"]["knee_gate_degrees"]:
        poses[f"bilateral_knee_{int(degrees)}"] = {
            "frame": frame,
            "rotations": {
                knees[side]["bone"]: {
                    "axis": knees[side]["axis"],
                    "degrees": int(knees[side]["sign"]) * float(degrees),
                }
                for side in ("L", "R")
            },
            "locations": {},
        }
    poses["seated_contact"] = seated_spec
    poses["supine_lying_contact"] = {
        "frame": frame,
        "rotations": {
            "root": {"axis": supine["axis"], "degrees": supine["degrees"]}
        },
        "locations": {"root": supine["location"]},
    }
    poses["table_reach_eating_foundation"] = {
        "frame": frame,
        "rotations": {
            reach["upper"]["bone"]: {
                "axis": reach["upper"]["axis"],
                "degrees": reach["upper"]["degrees"],
            },
            reach["lower"]["bone"]: {
                "axis": reach["lower"]["axis"],
                "degrees": reach["lower"]["degrees"],
            },
        },
        "locations": {},
    }
    return poses, {
        "knee_axis_solutions": knees,
        "hip_axis_solutions": hips,
        "seated_pose_solution": seated,
        "supine_root_solution": supine,
        "reach_solution": reach,
    }


def author_actions(armature: Any, poses: Mapping[str, Mapping[str, Any]], candidate_id: str) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for pose_name, spec in poses.items():
        action_name = f"{candidate_id}_{pose_name.upper()}"
        if bpy.data.actions.get(action_name) is not None:
            raise RobertR26BuildError(f"refusing action overwrite: {action_name}")
        action = bpy.data.actions.new(action_name)
        action.use_fake_user = True
        armature.animation_data_create()
        # Key every official pose bone at rest and target so each stored action
        # is self-contained and cannot inherit a stale transform from a prior
        # review action.
        involved = sorted(bone.name for bone in armature.pose.bones)
        reset_pose(armature)
        armature.animation_data.action = action
        scene = bpy.context.scene
        target_frame = int(spec.get("frame", 30))
        expected_target: dict[str, Any] = {}
        for frame in (1, target_frame):
            scene.frame_set(frame)
            # Do not call reset_pose/apply_pose_spec while this action is
            # attached: both intentionally clear action assignment.
            for bone in armature.pose.bones:
                bone.rotation_mode = "QUATERNION"
                bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bone.location = (0.0, 0.0, 0.0)
                bone.scale = (1.0, 1.0, 1.0)
            if frame == target_frame:
                set_pose_transforms(armature, spec)
            bpy.context.view_layer.update()
            for bone_name in involved:
                bone = armature.pose.bones[bone_name]
                bone.keyframe_insert(
                    "rotation_quaternion",
                    frame=frame,
                    group=bone.name,
                )
                bone.keyframe_insert("location", frame=frame, group=bone.name)
                bone.keyframe_insert("scale", frame=frame, group=bone.name)
                if frame == target_frame:
                    expected_target[bone_name] = {
                        "rotation_quaternion": [
                            float(value) for value in bone.rotation_quaternion
                        ],
                        "location": [float(value) for value in bone.location],
                        "scale": [float(value) for value in bone.scale],
                    }
        # Re-evaluate from the stored F-curves, rather than trusting the
        # transforms that were present when the keys were written.
        armature.animation_data.action = None
        for bone in armature.pose.bones:
            bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bone.location = (0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
        armature.animation_data.action = action
        scene.frame_set(target_frame)
        bpy.context.view_layer.update()
        maximum_rotation_delta = 0.0
        maximum_location_delta = 0.0
        maximum_scale_delta = 0.0
        for bone_name in involved:
            bone = armature.pose.bones[bone_name]
            expected = expected_target[bone_name]
            expected_rotation = Quaternion(tuple(expected["rotation_quaternion"]))
            maximum_rotation_delta = max(
                maximum_rotation_delta,
                float(bone.rotation_quaternion.rotation_difference(expected_rotation).angle),
            )
            maximum_location_delta = max(
                maximum_location_delta,
                float((bone.location - Vector(expected["location"])).length),
            )
            maximum_scale_delta = max(
                maximum_scale_delta,
                float((bone.scale - Vector(expected["scale"])).length),
            )
        if (
            maximum_rotation_delta > 1.0e-7
            or maximum_location_delta > 1.0e-7
            or maximum_scale_delta > 1.0e-7
        ):
            raise RobertR26BuildError(
                f"stored action target verification failed: {action_name}"
            )
        action["candidate_id"] = candidate_id
        action["private_owner_review_only"] = True
        action["runtime_assignment_allowed"] = False
        action["bounded_movement_foundation_only"] = True
        records[pose_name] = {
            "action": action.name,
            "pose_spec": spec,
            "self_contained_keyed_bone_count": len(involved),
            "stored_fcurve_target_verification": {
                "frame": target_frame,
                "maximum_rotation_delta_radians": maximum_rotation_delta,
                "maximum_location_delta_m": maximum_location_delta,
                "maximum_scale_delta": maximum_scale_delta,
                "passed": True,
            },
            "truth_limit": (
                "One bounded review pose only; this is not proof of universal "
                "human movement or the named activity's complete physiology."
            ),
        }
    reset_pose(armature)
    return records


def contact_metrics(
    pose_name: str,
    body_points: Sequence[Vector],
    region_map: Mapping[str, Sequence[int]],
    config: Mapping[str, Any],
) -> dict[str, Any] | None:
    tolerance = float(config["movement"]["contact_tolerance_m"])
    epsilon = float(config["movement"]["no_penetration_epsilon_m"])

    targets = config["support_targets"]

    def plane(
        points: Sequence[Vector],
        plane_z: float,
        minimum_contact_points: int,
        *,
        minimum_longitudinal_span_m: float = 0.0,
        minimum_lateral_span_m: float = 0.0,
    ) -> dict[str, Any]:
        gaps = [float(point.z) - plane_z for point in points]
        contact_points = [
            point
            for point, gap in zip(points, gaps)
            if -epsilon <= gap <= tolerance
        ]
        x_span = (
            max(float(point.x) for point in contact_points)
            - min(float(point.x) for point in contact_points)
            if contact_points
            else 0.0
        )
        y_span = (
            max(float(point.y) for point in contact_points)
            - min(float(point.y) for point in contact_points)
            if contact_points
            else 0.0
        )
        longitudinal_span = max(x_span, y_span)
        lateral_span = min(x_span, y_span)
        maximum_penetration = max(max(0.0, -value) for value in gaps)
        passed = (
            len(contact_points) >= int(minimum_contact_points)
            and maximum_penetration <= epsilon
            and longitudinal_span >= float(minimum_longitudinal_span_m)
            and lateral_span >= float(minimum_lateral_span_m)
        )
        return {
            "point_count": len(points),
            "plane_z_m": plane_z,
            "plane_source": "fixed_configured_world_support_target",
            "minimum_signed_gap_m": min(gaps),
            "minimum_absolute_gap_m": min(abs(value) for value in gaps),
            "maximum_penetration_m": maximum_penetration,
            "contact_point_count": len(contact_points),
            "required_contact_point_count": int(minimum_contact_points),
            "contact_x_span_m": x_span,
            "contact_y_span_m": y_span,
            "contact_longitudinal_span_m": longitudinal_span,
            "contact_lateral_span_m": lateral_span,
            "required_longitudinal_span_m": float(minimum_longitudinal_span_m),
            "required_lateral_span_m": float(minimum_lateral_span_m),
            "within_tolerance": len(contact_points) >= int(minimum_contact_points),
            "no_penetration": maximum_penetration <= epsilon,
            "passed": passed,
        }

    if pose_name == "seated_contact":
        pelvis = [body_points[index] for index in region_map["pelvis"]]
        left = [body_points[index] for index in region_map["left_foot"]]
        right = [body_points[index] for index in region_map["right_foot"]]
        seat_z = float(targets["seat_top_z_m"])
        floor_z = float(targets["world_floor_z_m"])
        return {
            "kind": "bounded_seated_support",
            "seat": plane(
                pelvis,
                seat_z,
                int(targets["minimum_seat_contact_points"]),
            ),
            "left_foot": plane(
                left,
                floor_z,
                int(targets["minimum_foot_contact_points_each"]),
            ),
            "right_foot": plane(
                right,
                floor_z,
                int(targets["minimum_foot_contact_points_each"]),
            ),
            "truth_limit": "One measured seated contact pose only.",
        }
    if pose_name == "supine_lying_contact":
        return {
            "kind": "bounded_supine_support",
            "support": plane(
                body_points,
                float(targets["world_floor_z_m"]),
                int(targets["minimum_supine_contact_points"]),
                minimum_longitudinal_span_m=float(
                    targets["minimum_supine_contact_longitudinal_span_m"]
                ),
                minimum_lateral_span_m=float(
                    targets["minimum_supine_contact_lateral_span_m"]
                ),
            ),
            "truth_limit": "One supine support pose; not sleep or all lying motions.",
        }
    if pose_name == "table_reach_eating_foundation":
        hand = [body_points[index] for index in region_map["left_hand"]]
        return {
            "kind": "bounded_hand_table_reach",
            "table": plane(
                hand,
                float(targets["table_top_z_m"]),
                int(targets["minimum_table_hand_contact_points"]),
            ),
            "truth_limit": "Reach/contact only; no grasping, eating, chewing, or swallowing claim.",
        }
    return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def project_relative(path: Path) -> str:
    require_inside_project(path)
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def deformation_quality(original: Any, deformed: Any) -> dict[str, Any]:
    """Prove that the bounded v8 warp did not flip or collapse triangles."""

    if polygon_index_signature(original) != polygon_index_signature(deformed):
        raise RobertR26BuildError("deformation quality requires identical topology")
    flipped = 0
    canonical_near_zero = 0
    deformed_near_zero = 0
    ratios: list[float] = []
    sampled = 0
    for polygon in original.data.polygons:
        indices = list(map(int, polygon.vertices))
        for offset in range(1, len(indices) - 1):
            triangle = (indices[0], indices[offset], indices[offset + 1])
            before = [original.data.vertices[index].co for index in triangle]
            after = [deformed.data.vertices[index].co for index in triangle]
            before_cross = (before[1] - before[0]).cross(before[2] - before[0])
            after_cross = (after[1] - after[0]).cross(after[2] - after[0])
            before_area = before_cross.length * 0.5
            after_area = after_cross.length * 0.5
            sampled += 1
            if before_area <= 1.0e-10:
                canonical_near_zero += 1
            if after_area <= 1.0e-10:
                deformed_near_zero += 1
            if before_area <= 1.0e-10:
                continue
            ratios.append(float(after_area / before_area))
            if after_area > 1.0e-10 and before_cross.dot(after_cross) < 0.0:
                flipped += 1
    report = {
        "sampled_triangle_count": sampled,
        "flipped_triangle_count": flipped,
        "canonical_near_zero_area_triangle_count": canonical_near_zero,
        "deformed_near_zero_area_triangle_count": deformed_near_zero,
        "area_ratio_minimum": min(ratios, default=1.0),
        "area_ratio_p05": quantile(ratios, 0.05),
        "area_ratio_median": statistics.median(ratios) if ratios else 1.0,
        "area_ratio_p95": quantile(ratios, 0.95),
        "area_ratio_maximum": max(ratios, default=1.0),
        "passed": (
            bool(ratios)
            and flipped == 0
            and canonical_near_zero == 0
            and deformed_near_zero == 0
        ),
    }
    if not report["passed"]:
        raise RobertR26BuildError(f"bounded v8 deformation quality failed: {report}")
    return report


def region_indices_by_group(
    body: Any,
    predicate: Any,
    minimum_weight: float,
) -> list[int]:
    selected_groups = {
        group.index for group in body.vertex_groups if predicate(group.name.lower())
    }
    return [
        int(vertex.index)
        for vertex in body.data.vertices
        if any(
            assignment.group in selected_groups
            and float(assignment.weight) >= minimum_weight
            for assignment in vertex.groups
        )
    ]


def movement_region_map(body: Any) -> dict[str, list[int]]:
    def side_region(prefixes: tuple[str, ...], side: str) -> list[int]:
        suffix = "." + side.lower()
        return region_indices_by_group(
            body,
            lambda name: name.endswith(suffix) and name.startswith(prefixes),
            0.08,
        )

    regions = {
        "pelvis": region_indices_by_group(
            body,
            lambda name: name.startswith("pelvis."),
            0.16,
        ),
        "left_foot": side_region(("foot.", "toe"), "L"),
        "right_foot": side_region(("foot.", "toe"), "R"),
        "left_hand": side_region(("wrist.", "metacarpal", "finger"), "L"),
        "right_hand": side_region(("wrist.", "metacarpal", "finger"), "R"),
        "knees": region_indices_by_group(
            body,
            lambda name: name.startswith(
                ("upperleg02.", "lowerleg01.", "lowerleg02.")
            ),
            0.22,
        ),
        "head": region_indices_by_group(
            body,
            lambda name: name == "head" or name.startswith(
                ("jaw", "oculi", "orbicularis", "oris", "levator", "risorius")
            ),
            0.08,
        ),
    }
    empty = [name for name, indices in regions.items() if not indices]
    if empty:
        raise RobertR26BuildError(f"weighted movement regions empty: {empty}")
    return regions


def contact_gate(record: Mapping[str, Any] | None) -> bool:
    if record is None:
        return True
    measurements = [
        value
        for value in record.values()
        if isinstance(value, dict) and "passed" in value
    ]
    return bool(measurements) and all(bool(row["passed"]) for row in measurements)


def component_surface_clearance_report(
    body: Any,
    components: Sequence[Any],
) -> dict[str, Any]:
    body_tree = world_surface_bvh(body)
    records: list[dict[str, Any]] = []
    all_distances: list[float] = []
    for component in components:
        points = evaluated_vertices(component)
        distances: list[float] = []
        for point in points:
            nearest = body_tree.find_nearest(point)
            if nearest[0] is None:
                raise RobertR26BuildError(
                    f"component/body clearance query failed: {component.name}"
                )
            distances.append(float(nearest[3]))
        if not distances:
            raise RobertR26BuildError(f"component has no evaluated points: {component.name}")
        all_distances.extend(distances)
        records.append(
            {
                "object": component.name,
                "evaluated_point_count": len(points),
                "minimum_unsigned_surface_clearance_m": min(distances),
                "median_unsigned_surface_clearance_m": statistics.median(distances),
                "maximum_unsigned_surface_clearance_m": max(distances),
            }
        )
    return {
        "component_count": len(components),
        "minimum_unsigned_surface_clearance_m": min(all_distances),
        "maximum_unsigned_surface_clearance_m": max(all_distances),
        "records": records,
    }


def brow_root_clearance_report(body: Any, brows: Sequence[Any]) -> dict[str, Any]:
    body_tree = world_surface_bvh(body)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    records: list[dict[str, Any]] = []
    all_distances: list[float] = []
    for brow in brows:
        evaluated = brow.evaluated_get(depsgraph)
        roots = [
            evaluated.matrix_world @ Vector(spline.points[0].co[:3])
            for spline in brow.data.splines
            if len(spline.points) > 0
        ]
        if not roots:
            raise RobertR26BuildError(f"brow has no strand roots: {brow.name}")
        distances = []
        for point in roots:
            nearest = body_tree.find_nearest(point)
            if nearest[0] is None:
                raise RobertR26BuildError(
                    f"brow-root/body clearance query failed: {brow.name}"
                )
            distances.append(float(nearest[3]))
        all_distances.extend(distances)
        records.append(
            {
                "object": brow.name,
                "strand_root_count": len(roots),
                "minimum_unsigned_surface_clearance_m": min(distances),
                "maximum_unsigned_surface_clearance_m": max(distances),
            }
        )
    return {
        "brow_count": len(brows),
        "root_count": sum(row["strand_root_count"] for row in records),
        "minimum_unsigned_surface_clearance_m": min(all_distances),
        "maximum_unsigned_surface_clearance_m": max(all_distances),
        "records": records,
    }


def pose_geometry_audit(
    *,
    pose_name: str,
    pose_spec: Mapping[str, Any],
    action_name: str,
    armature: Any,
    body: Any,
    nails: Sequence[Any],
    eye_objects: Sequence[Any],
    lash_objects: Sequence[Any],
    brow_objects: Sequence[Any],
    neutral_points: Sequence[Vector],
    region_map: Mapping[str, Sequence[int]],
    config: Mapping[str, Any],
    report_directory: Path | None,
) -> dict[str, Any]:
    reset_pose(armature)
    neutral_leg_flexions = {
        side: leg_flexion(leg_points(armature, side)) for side in ("L", "R")
    }
    apply_pose_spec(armature, pose_spec)
    posed_leg_flexions = {
        side: leg_flexion(leg_points(armature, side)) for side in ("L", "R")
    }
    measured_knee_changes = {
        side: abs(posed_leg_flexions[side] - neutral_leg_flexions[side])
        for side in ("L", "R")
    }
    expected_knees: dict[str, float] = {}
    for side_name, side in (("left", "L"), ("right", "R")):
        prefix = f"{side_name}_knee_"
        if pose_name.startswith(prefix):
            expected_knees[side] = float(pose_name[len(prefix) :])
    if pose_name.startswith("bilateral_knee_"):
        expected = float(pose_name[len("bilateral_knee_") :])
        expected_knees = {"L": expected, "R": expected}
    knee_tolerance = float(config["movement"]["knee_angle_tolerance_degrees"])
    knee_measurement = {
        "neutral_flexion_degrees": neutral_leg_flexions,
        "posed_flexion_degrees": posed_leg_flexions,
        "measured_change_degrees": measured_knee_changes,
        "expected_change_degrees": expected_knees,
        "tolerance_degrees": knee_tolerance,
        "errors_degrees": {
            side: abs(measured_knee_changes[side] - expected)
            for side, expected in expected_knees.items()
        },
    }
    knee_measurement["passed"] = all(
        error <= knee_tolerance
        for error in knee_measurement["errors_degrees"].values()
    )
    points = evaluated_vertices(body)
    if len(points) != int(config["foundation_truth"]["post_union_vertices"]):
        raise RobertR26BuildError(f"evaluated topology count changed in {pose_name}")
    exact_self = exact_evaluated_self_intersections(body)
    exact_nails = exact_cross_intersections(body, nails)
    exact_eyes = exact_cross_intersections(body, eye_objects)
    exact_lashes = exact_cross_intersections(body, lash_objects)
    exact_brows = exact_cross_intersections(body, brow_objects)
    nail_clearance = component_surface_clearance_report(body, nails)
    lash_clearance = component_surface_clearance_report(body, lash_objects)
    brow_root_clearance = brow_root_clearance_report(body, brow_objects)
    stretch = edge_stretch_report(
        body,
        neutral_points,
        points,
        set(map(int, region_map["knees"])),
        config,
    )
    contact = contact_metrics(pose_name, points, region_map, config)
    support_prop_intersections: dict[str, Any] | None = None
    if contact is not None:
        support_material = review_material(
            f"Robert_R26_{pose_name}_Measured_Support_Audit",
            (0.075, 0.12, 0.18, 1.0),
        )
        support_props = support_props_for_pose(
            pose_name,
            points,
            region_map,
            contact,
            support_material,
            config,
        )
        hide_review_props(support_props, False)
        try:
            support_prop_intersections = exact_cross_intersections(body, support_props)
        finally:
            remove_review_props(support_props, extra_materials=(support_material,))
    direct_points = [point.copy() for point in points]
    reset_pose(armature)
    action = bpy.data.actions.get(action_name)
    if action is None:
        raise RobertR26BuildError(f"stored action missing for {pose_name}: {action_name}")
    armature.animation_data_create()
    armature.animation_data.action = action
    bpy.context.scene.frame_set(int(pose_spec.get("frame", 30)))
    bpy.context.view_layer.update()
    action_points = evaluated_vertices(body)
    if len(action_points) != len(direct_points):
        raise RobertR26BuildError(f"stored action topology changed for {pose_name}")
    action_deltas = [
        float((action_point - direct_point).length)
        for action_point, direct_point in zip(action_points, direct_points)
    ]
    action_mesh_verification = {
        "action": action.name,
        "frame": int(pose_spec.get("frame", 30)),
        "direct_point_sha256": point_signature(direct_points),
        "stored_action_point_sha256": point_signature(action_points),
        "maximum_vertex_delta_m": max(action_deltas, default=0.0),
        "mean_vertex_delta_m": (
            sum(action_deltas) / len(action_deltas) if action_deltas else 0.0
        ),
        "required_maximum_vertex_delta_m": 1.0e-7,
        "passed": bool(action_deltas) and max(action_deltas) <= 1.0e-7,
    }
    armature.animation_data.action = None
    reset_pose(armature)
    failures: list[str] = []
    if int(exact_self["exact_genuine_penetration_pair_count"]) != int(
        config["movement"]["exact_self_intersection_pairs_allowed"]
    ):
        failures.append("self_intersection")
    if int(exact_nails["total_exact_genuine_triangle_pair_count"]) != int(
        config["movement"]["exact_body_nail_intersection_pairs_allowed"]
    ):
        failures.append("body_nail_intersection")
    if int(exact_eyes["total_exact_genuine_triangle_pair_count"]) != int(
        config["movement"]["exact_body_eye_intersection_pairs_allowed"]
    ):
        failures.append("body_eye_intersection")
    follow_settings = config["component_follow"]
    if (
        float(nail_clearance["maximum_unsigned_surface_clearance_m"])
        > float(follow_settings["nail_maximum_surface_clearance_m"])
        or float(nail_clearance["minimum_unsigned_surface_clearance_m"])
        > float(follow_settings["nail_minimum_attachment_proximity_m"])
    ):
        failures.append("nail_surface_follow")
    if int(exact_lashes["total_exact_genuine_triangle_pair_count"]) != int(
        follow_settings["exact_body_lash_intersection_pairs_allowed"]
    ):
        failures.append("body_lash_intersection")
    if int(exact_brows["total_exact_genuine_triangle_pair_count"]) != int(
        follow_settings["exact_body_brow_intersection_pairs_allowed"]
    ):
        failures.append("body_brow_intersection")
    if (
        float(lash_clearance["maximum_unsigned_surface_clearance_m"])
        > float(follow_settings["lash_maximum_surface_clearance_m"])
        or float(lash_clearance["minimum_unsigned_surface_clearance_m"])
        > float(follow_settings["lash_minimum_attachment_proximity_m"])
    ):
        failures.append("lash_surface_follow")
    if (
        float(brow_root_clearance["maximum_unsigned_surface_clearance_m"])
        > float(follow_settings["brow_root_maximum_surface_clearance_m"])
    ):
        failures.append("brow_root_surface_follow")
    if not bool(stretch["passed"]):
        failures.append("edge_or_area_stretch")
    if not contact_gate(contact):
        failures.append("support_contact")
    if (
        support_prop_intersections is not None
        and int(
            support_prop_intersections[
                "total_exact_genuine_triangle_pair_count"
            ]
        )
        != 0
    ):
        failures.append("support_prop_intersection")
    if not bool(action_mesh_verification["passed"]):
        failures.append("stored_action_mesh_mismatch")
    if not bool(knee_measurement["passed"]):
        failures.append("measured_knee_angle")
    report: dict[str, Any] = {
        "pose": pose_name,
        "pose_spec": pose_spec,
        "evaluated_vertex_count": len(points),
        "bounds_m": bounds_record(points),
        "exact_self_intersections": exact_self,
        "exact_body_nail_intersections": exact_nails,
        "exact_body_eye_intersections": exact_eyes,
        "exact_body_lash_intersections": exact_lashes,
        "exact_body_brow_intersections": exact_brows,
        "nail_surface_follow": nail_clearance,
        "lash_surface_follow": lash_clearance,
        "brow_root_surface_follow": brow_root_clearance,
        "edge_and_area_deformation": stretch,
        "measured_knee_flexion": knee_measurement,
        "support_contact": contact,
        "exact_body_support_prop_intersections": support_prop_intersections,
        "stored_action_mesh_verification": action_mesh_verification,
        "passed": not failures,
        "failures": failures,
        "truth_limit": (
            "This is one bounded pose/deformation/contact measurement. It is "
            "not proof of every human action or internal physiology."
        ),
    }
    report["canonical_json_sha256"] = json_sha256(report)
    if report_directory is not None:
        write_json(report_directory / f"{pose_name}.json", report)
        report["artifact"] = {
            "package_relative_path": (
                f"{report_directory.name}/{pose_name}.json"
            ),
            "sha256": sha256_file(report_directory / f"{pose_name}.json"),
        }
    if failures:
        raise RobertR26BuildError(
            f"pose geometry gate failed for {pose_name}: {', '.join(failures)}"
        )
    return report


def review_material(name: str, color: Sequence[float]) -> Any:
    return simple_material(name, color, roughness=0.62)


def make_review_box(
    name: str,
    center: Vector,
    size: Vector,
    material: Any,
) -> Any:
    half = size * 0.5
    vertices = [
        center + Vector((sx * half.x, sy * half.y, sz * half.z))
        for sx, sy, sz in (
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        )
    ]
    faces = (
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7),
    )
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["review_context_prop_only"] = True
    obj["must_not_export"] = True
    obj["private_owner_review_only"] = True
    return obj


def hide_review_props(props: Sequence[Any], hidden: bool) -> None:
    for obj in props:
        obj.hide_render = hidden
        obj.hide_viewport = hidden
        obj.hide_set(hidden)


def remove_review_props(
    props: Sequence[Any],
    *,
    extra_materials: Sequence[Any] = (),
) -> None:
    """Remove temporary review objects and their otherwise orphaned data."""

    disposable_data = {
        obj.data.name: obj.data
        for obj in props
        if getattr(obj, "data", None) is not None
    }
    disposable_materials = {
        material.name: material
        for obj in props
        if getattr(obj, "data", None) is not None
        for material in getattr(obj.data, "materials", ())
        if material is not None
    }
    disposable_materials.update(
        {material.name: material for material in extra_materials if material is not None}
    )
    for obj in props:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    for data in disposable_data.values():
        if data.users == 0 and data.name in bpy.data.meshes:
            bpy.data.meshes.remove(data)
    for material in disposable_materials.values():
        if material.users == 0:
            bpy.data.materials.remove(material)


def support_props_for_pose(
    pose_name: str,
    points: Sequence[Vector],
    region_map: Mapping[str, Sequence[int]],
    contact: Mapping[str, Any] | None,
    material: Any,
    config: Mapping[str, Any],
) -> list[Any]:
    props: list[Any] = []
    box = bounds_record(points)
    low = Vector(box["low"])
    high = Vector(box["high"])
    center = (low + high) * 0.5
    targets = config["support_targets"]
    if pose_name == "seated_contact" and contact is not None:
        seat_z = float(contact["seat"]["plane_z_m"])
        floor_z = min(
            float(contact["left_foot"]["plane_z_m"]),
            float(contact["right_foot"]["plane_z_m"]),
        )
        pelvis_points = [points[index] for index in region_map["pelvis"]]
        pelvis_center = sum(pelvis_points, Vector()) / len(pelvis_points)
        seat_size = Vector(tuple(float(value) for value in targets["seat_size_m"]))
        floor_size = Vector(tuple(float(value) for value in targets["floor_size_m"]))
        props.append(
            make_review_box(
                "Robert_R26_Seat_Review_Context_Do_Not_Export",
                Vector((pelvis_center.x, pelvis_center.y, seat_z - seat_size.z * 0.5)),
                seat_size,
                material,
            )
        )
        props.append(
            make_review_box(
                "Robert_R26_Seated_Floor_Review_Context_Do_Not_Export",
                Vector((center.x, center.y, floor_z - floor_size.z * 0.5)),
                floor_size,
                material,
            )
        )
    elif pose_name == "supine_lying_contact" and contact is not None:
        plane_z = float(contact["support"]["plane_z_m"])
        margin = float(targets["supine_support_margin_m"])
        thickness = float(targets["supine_support_thickness_m"])
        props.append(
            make_review_box(
                "Robert_R26_Supine_Support_Review_Context_Do_Not_Export",
                Vector((center.x, center.y, plane_z - thickness * 0.5)),
                Vector((high.x - low.x + margin, high.y - low.y + margin, thickness)),
                material,
            )
        )
    elif pose_name == "table_reach_eating_foundation" and contact is not None:
        plane_z = float(contact["table"]["plane_z_m"])
        hand_points = [points[index] for index in region_map["left_hand"]]
        hand_center = sum(hand_points, Vector()) / len(hand_points)
        table_size = Vector(tuple(float(value) for value in targets["table_size_m"]))
        props.append(
            make_review_box(
                "Robert_R26_Reach_Table_Review_Context_Do_Not_Export",
                Vector((hand_center.x, hand_center.y, plane_z - table_size.z * 0.5)),
                table_size,
                material,
            )
        )
    hide_review_props(props, True)
    return props


def configure_render(config: Mapping[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    requested_engine = str(config["render"]["engine"])
    actual_engine = requested_engine
    try:
        scene.render.engine = requested_engine
    except TypeError:
        if requested_engine != "BLENDER_EEVEE":
            raise
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        actual_engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = int(config["render"]["resolution_x"])
    scene.render.resolution_y = int(config["render"]["resolution_y"])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.004, 0.008, 0.014)
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -1.15
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = int(config["render"]["samples"])

    def add_area(
        name: str,
        location: Vector,
        target: Vector,
        energy: float,
        size: float,
    ) -> None:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()

    target = Vector((0.0, 0.0, 1.05))
    add_area("Robert_R26_Key", Vector((-2.2, -2.8, 2.55)), target, 700.0, 2.0)
    add_area("Robert_R26_Fill", Vector((2.4, -1.8, 1.75)), target, 360.0, 2.1)
    add_area("Robert_R26_Rim", Vector((0.0, 2.6, 2.3)), target, 440.0, 1.8)
    camera_data = bpy.data.cameras.new("Robert_R26_Private_Review_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Robert_R26_Private_Review_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera, {
        "requested_engine": requested_engine,
        "actual_engine": actual_engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "samples": int(config["render"]["samples"]),
    }


def render_view(
    *,
    scene: Any,
    camera: Any,
    output_directory: Path,
    name: str,
    location: Vector,
    target: Vector,
    ortho_scale: float,
    minimum_bytes: int,
) -> dict[str, Any]:
    if ortho_scale <= 0.0 or (target - location).length <= 1.0e-5:
        raise RobertR26BuildError(f"invalid review camera for {name}")
    camera.location = location
    camera.data.ortho_scale = float(ortho_scale)
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    path = output_directory / f"{name}.png"
    if path.exists():
        raise RobertR26BuildError(f"refusing render overwrite: {path}")
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size < minimum_bytes:
        raise RobertR26BuildError(f"review render missing or too small: {path}")
    return {
        "package_relative_path": f"{output_directory.name}/{path.name}",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "pose": str(bpy.context.scene.get("robert_r26_review_pose", "unknown")),
        "private_owner_review_only": True,
    }


def region_center(points: Sequence[Vector], indices: Sequence[int]) -> Vector:
    selected = [points[int(index)] for index in indices]
    if not selected:
        raise RobertR26BuildError("review region is empty")
    return sum(selected, Vector()) / len(selected)


def render_complete_review_inventory(
    *,
    scene: Any,
    camera: Any,
    output_directory: Path,
    armature: Any,
    body: Any,
    poses: Mapping[str, Mapping[str, Any]],
    pose_reports: Mapping[str, Mapping[str, Any]],
    region_map: Mapping[str, Sequence[int]],
    eye_objects: Sequence[Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    if not bool(config["render"].get("neutral_color_reference_chart")):
        raise RobertR26BuildError("neutral color-reference chart gate is disabled")
    minimum_bytes = int(config["render"]["minimum_png_bytes"])
    context_material = review_material(
        "Robert_R26_Review_Context_Material",
        (0.075, 0.12, 0.18, 1.0),
    )
    all_props: list[Any] = []
    records: dict[str, Any] = {}

    def draw(
        name: str,
        location: Vector,
        target: Vector,
        scale: float,
    ) -> None:
        if name in records:
            raise RobertR26BuildError(f"duplicate review render name: {name}")
        records[name] = render_view(
            scene=scene,
            camera=camera,
            output_directory=output_directory,
            name=name,
            location=location,
            target=target,
            ortho_scale=scale,
            minimum_bytes=minimum_bytes,
        )

    def set_pose(name: str) -> tuple[list[Vector], Vector, Vector, float, float]:
        apply_pose_spec(armature, poses[name])
        scene["robert_r26_review_pose"] = name
        points = evaluated_vertices(body)
        box = bounds_record(points)
        low = Vector(box["low"])
        high = Vector(box["high"])
        center = (low + high) * 0.5
        height = float(high.z - low.z)
        distance = max(float((high - low).length), 1.0) * 1.55 + 0.8
        return points, low, high, height, distance

    points, low, high, height, distance = set_pose("neutral_standing")
    center = (low + high) * 0.5
    hide_review_props(all_props, True)
    neutral_views = {
        "front": (Vector((center.x, low.y - distance, center.z)), center, height * 1.08),
        "left_three_quarter": (Vector((center.x - distance * 0.64, low.y - distance, center.z)), center, height * 1.10),
        "right_three_quarter": (Vector((center.x + distance * 0.64, low.y - distance, center.z)), center, height * 1.10),
        "left_profile": (Vector((low.x - distance, center.y, center.z)), center, height * 1.08),
        "right_profile": (Vector((high.x + distance, center.y, center.z)), center, height * 1.08),
        "rear": (Vector((center.x, high.y + distance, center.z)), center, height * 1.08),
        "neutral_standing": (Vector((center.x, low.y - distance, center.z)), center, height * 1.08),
    }
    for name, values in neutral_views.items():
        draw(name, *values)
    head_target = region_center(points, region_map["head"])
    draw(
        "crown_top",
        Vector((head_target.x, head_target.y - 0.08, high.z + 1.25)),
        Vector((head_target.x, head_target.y, high.z - 0.08)),
        0.48,
    )
    draw(
        "rear_scalp",
        Vector((head_target.x, high.y + 1.4, head_target.z + 0.05)),
        head_target,
        0.56,
    )
    eye_centers = [sum(object_bounds(obj), Vector()) * 0.5 for obj in eye_objects if "Sclera" in obj.name]
    eye_target = sum(eye_centers, Vector()) / len(eye_centers) if eye_centers else head_target
    draw(
        "face_eyes_close",
        Vector((eye_target.x, low.y - 1.3, eye_target.z - 0.03)),
        eye_target,
        0.53,
    )
    for name, region, scale in (
        ("left_hand_nails", "left_hand", 0.31),
        ("right_hand_nails", "right_hand", 0.31),
        ("left_foot_nails", "left_foot", 0.36),
        ("right_foot_nails", "right_foot", 0.36),
    ):
        target = region_center(points, region_map[region])
        draw(name, Vector((target.x, target.y - 1.2, target.z + 0.05)), target, scale)
    pelvis = region_center(points, region_map["pelvis"])
    for name, location in {
        "protected_adult_front": Vector((pelvis.x, pelvis.y - 1.35, pelvis.z)),
        "protected_adult_three_quarter": Vector((pelvis.x + 0.82, pelvis.y - 1.25, pelvis.z)),
        "protected_adult_rear": Vector((pelvis.x, pelvis.y + 1.35, pelvis.z)),
    }.items():
        draw(name, location, pelvis, 0.50)
    chart_colors = (
        ("white", (0.80, 0.80, 0.80, 1.0)),
        ("gray", (0.18, 0.18, 0.18, 1.0)),
        ("black", (0.01, 0.01, 0.01, 1.0)),
        ("red", (0.52, 0.025, 0.02, 1.0)),
        ("green", (0.02, 0.40, 0.035, 1.0)),
        ("blue", (0.018, 0.055, 0.48, 1.0)),
    )
    chart_props: list[Any] = []
    for index, (label, color) in enumerate(chart_colors):
        chart_props.append(
            make_review_box(
                f"Robert_R26_Neutral_Reference_{label}_Do_Not_Export",
                Vector((high.x + 0.12, low.y - 0.025, low.z + 0.22 + index * 0.12)),
                Vector((0.09, 0.018, 0.09)),
                review_material(f"Robert_R26_Neutral_Reference_{label}", color),
            )
        )
    all_props.extend(chart_props)
    hide_review_props(chart_props, False)
    draw(
        "neutral_color_reference_chart",
        Vector((center.x, low.y - distance, center.z)),
        center,
        height * 1.25,
    )
    hide_review_props(chart_props, True)

    for side in ("left", "right"):
        for degrees in config["movement"]["knee_gate_degrees"]:
            pose_name = f"{side}_knee_{int(degrees)}"
            points, low, high, height, distance = set_pose(pose_name)
            center = (low + high) * 0.5
            draw(
                pose_name,
                Vector((center.x + distance * 0.50, low.y - distance, center.z)),
                center,
                height * 1.10,
            )
    for degrees in config["movement"]["knee_gate_degrees"]:
        pose_name = f"bilateral_knee_{int(degrees)}"
        points, low, high, height, distance = set_pose(pose_name)
        center = (low + high) * 0.5
        draw(
            pose_name,
            Vector((center.x + distance * 0.50, low.y - distance, center.z)),
            center,
            height * 1.10,
        )

    for pose_name, render_names in (
        ("seated_contact", ("seated_front", "seated_side", "seated_contact_close")),
        ("supine_lying_contact", ("supine_side", "supine_support_close")),
        ("table_reach_eating_foundation", ("table_reach_front", "table_reach_side")),
    ):
        points, low, high, height, distance = set_pose(pose_name)
        center = (low + high) * 0.5
        props = support_props_for_pose(
            pose_name,
            points,
            region_map,
            pose_reports[pose_name].get("support_contact"),
            context_material,
            config,
        )
        all_props.extend(props)
        hide_review_props(all_props, True)
        hide_review_props(props, False)
        if pose_name == "seated_contact":
            draw(render_names[0], Vector((center.x, low.y - distance, center.z)), center, height * 1.15)
            draw(render_names[1], Vector((high.x + distance, center.y, center.z)), center, height * 1.15)
            target = region_center(points, region_map["pelvis"])
            draw(render_names[2], Vector((target.x + 1.0, target.y - 1.0, target.z)), target, 0.72)
        elif pose_name == "supine_lying_contact":
            draw(render_names[0], Vector((high.x + distance, center.y, center.z)), center, max(high.x - low.x, high.y - low.y) * 1.15)
            target = Vector((center.x, center.y, low.z + 0.05))
            draw(render_names[1], Vector((target.x + 1.2, target.y - 1.0, target.z + 0.25)), target, 0.82)
        else:
            draw(render_names[0], Vector((center.x, low.y - distance, center.z)), center, height * 1.12)
            draw(render_names[1], Vector((high.x + distance, center.y, center.z)), center, height * 1.12)
        hide_review_props(props, True)

    required = set(map(str, config["required_private_review_views"]))
    absent = sorted(required - set(records))
    unexpected = sorted(set(records) - required)
    if absent or unexpected:
        raise RobertR26BuildError(
            f"review render inventory mismatch: absent={absent}; unexpected={unexpected}"
        )
    remove_review_props(all_props, extra_materials=(context_material,))
    reset_pose(armature)
    return {
        "required_count": len(required),
        "render_count": len(records),
        "required_inventory_exact": True,
        "records": records,
        "review_context_props_removed_before_save": True,
        "owner_visual_acceptance_claimed": False,
    }


def scalp_hair_dependency_audit() -> dict[str, Any]:
    forbidden_objects: list[str] = []
    allowed_face_hair: list[str] = []
    for obj in bpy.data.objects:
        data_name = getattr(getattr(obj, "data", None), "name", "")
        identity = f"{obj.name} {data_name}".lower()
        if "brow" in identity or "lash" in identity:
            allowed_face_hair.append(obj.name)
            continue
        if any(token in identity for token in ("hair", "groom", "scalp_cap", "scalpcap")):
            if obj.type in {"MESH", "CURVE", "CURVES", "VOLUME"}:
                forbidden_objects.append(obj.name)
    particle_collection = getattr(bpy.data, "particles", ())
    particle_settings = [settings.name for settings in particle_collection]
    hair_curve_collection = getattr(bpy.data, "hair_curves", ())
    hair_curves = [value.name for value in hair_curve_collection]
    forbidden_materials = [
        material.name
        for material in bpy.data.materials
        if any(
            token in material.name.lower()
            for token in ("scalp_hair", "scalphair", "groom", "hair_cap", "haircap")
        )
        and "brow" not in material.name.lower()
        and "lash" not in material.name.lower()
    ]
    forbidden_images = [
        image.name
        for image in bpy.data.images
        if any(
            token in image.name.lower()
            for token in ("scalp_hair", "scalphair", "groom", "hair_cap", "haircap")
        )
    ]
    if (
        forbidden_objects
        or particle_settings
        or hair_curves
        or forbidden_materials
        or forbidden_images
    ):
        raise RobertR26BuildError(
            "bald candidate contains a scalp-hair dependency: "
            + json.dumps(
                {
                    "objects": forbidden_objects,
                    "particle_settings": particle_settings,
                    "hair_curves": hair_curves,
                    "materials": forbidden_materials,
                    "images": forbidden_images,
                },
                sort_keys=True,
            )
        )
    return {
        "forbidden_scalp_hair_objects": forbidden_objects,
        "particle_hair_settings": particle_settings,
        "hair_curve_data": hair_curves,
        "forbidden_scalp_hair_materials": forbidden_materials,
        "forbidden_scalp_hair_images": forbidden_images,
        "allowed_brow_and_lash_objects": sorted(allowed_face_hair),
        "scalp_hair_objects_excluded_not_hidden": True,
        "scalp_hair_runtime_dependency_count": 0,
    }


def object_scope_audit(
    *,
    body: Any,
    armature: Any,
    nails: Sequence[Any],
    eyes: Sequence[Any],
    lashes: Sequence[Any],
    brows: Sequence[Any],
) -> dict[str, Any]:
    expected = {body.name, armature.name}
    expected.update(obj.name for obj in (*nails, *eyes, *lashes, *brows))
    scene_candidate_objects = {
        obj.name
        for obj in bpy.data.objects
        if obj.type not in {"CAMERA", "LIGHT"}
        and not bool(obj.get("review_context_prop_only"))
    }
    unexpected = sorted(scene_candidate_objects - expected)
    missing = sorted(expected - scene_candidate_objects)
    context_survivors = sorted(
        obj.name for obj in bpy.data.objects if bool(obj.get("review_context_prop_only"))
    )
    component_scope_failures = {
        obj.name: {
            "private_owner_review_only": bool(obj.get("private_owner_review_only")),
            "inactive_candidate": bool(obj.get("inactive_candidate")),
            "unassigned_candidate": bool(obj.get("unassigned_candidate")),
            "unpublished_candidate": bool(obj.get("unpublished_candidate")),
            "runtime_activation_allowed": bool(obj.get("runtime_activation_allowed")),
            "runtime_export_allowed": bool(obj.get("runtime_export_allowed")),
        }
        for obj in (body, armature, *nails, *eyes, *lashes, *brows)
        if not (
            bool(obj.get("private_owner_review_only"))
            and bool(obj.get("inactive_candidate"))
            and bool(obj.get("unassigned_candidate"))
            and bool(obj.get("unpublished_candidate"))
            and not bool(obj.get("runtime_activation_allowed"))
            and not bool(obj.get("runtime_export_allowed"))
        )
    }
    report = {
        "body": body.name,
        "body_material_slot_count": len(body.data.materials),
        "body_regional_skin_material": (
            body.data.materials[0].name if len(body.data.materials) == 1 else None
        ),
        "body_regional_skin_direction": (
            bool(body.data.materials[0].get("regional_skin_direction"))
            if len(body.data.materials) == 1
            else False
        ),
        "body_single_flat_color_used": (
            bool(body.data.materials[0].get("single_flat_color_used", True))
            if len(body.data.materials) == 1
            else True
        ),
        "body_geometry_plate_regions_used": (
            bool(body.data.materials[0].get("geometry_plate_regions_used", True))
            if len(body.data.materials) == 1
            else True
        ),
        "official_rig": armature.name,
        "official_bone_count": len(armature.data.bones),
        "nail_count": len(nails),
        "eye_object_count": len(eyes),
        "lash_object_count": len(lashes),
        "brow_object_count": len(brows),
        "candidate_object_count": len(scene_candidate_objects),
        "unexpected_candidate_objects": unexpected,
        "missing_candidate_objects": missing,
        "review_context_prop_survivors": context_survivors,
        "component_scope_failures": component_scope_failures,
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_activation_allowed": False,
        "passed": (
            len(nails) == 20
            and len(eyes) == 6
            and len(lashes) == 4
            and len(brows) == 2
            and not unexpected
            and not missing
            and not context_survivors
            and not component_scope_failures
            and len(body.data.materials) == 1
            and bool(body.data.materials[0].get("regional_skin_direction"))
            and not bool(body.data.materials[0].get("single_flat_color_used", True))
            and not bool(body.data.materials[0].get("geometry_plate_regions_used", True))
        ),
    }
    if not report["passed"]:
        raise RobertR26BuildError(f"candidate object-scope audit failed: {report}")
    return report


def apply_component_scope(objects: Sequence[Any]) -> None:
    for obj in objects:
        obj["private_owner_review_only"] = True
        obj["inactive_candidate"] = True
        obj["unassigned_candidate"] = True
        obj["unpublished_candidate"] = True
        obj["runtime_activation_allowed"] = False
        obj["runtime_export_allowed"] = False
        obj["roster_registration_allowed"] = False


def computed_mandatory_audits(
    *,
    config: Mapping[str, Any],
    input_hashes_unchanged: bool,
    output_absent_before_run: bool,
    v8_report: Mapping[str, Any],
    height_envelope: Mapping[str, Any],
    topology: Mapping[str, Any],
    deformation: Mapping[str, Any],
    transfer: Mapping[str, Any],
    rig: Mapping[str, Any],
    regional_skin: Mapping[str, Any],
    nail_count: int,
    nail_report: Mapping[str, Any],
    pose_reports: Mapping[str, Mapping[str, Any]],
    bald_audit: Mapping[str, Any],
    scope_report: Mapping[str, Any],
) -> dict[str, bool]:
    pose_values = list(pose_reports.values())
    special_contacts = (
        "seated_contact",
        "supine_lying_contact",
        "table_reach_eating_foundation",
    )
    audits = {
        "input_hashes": bool(input_hashes_unchanged),
        "candidate_directory_absent_before_run": bool(output_absent_before_run),
        "polygon_index_topology_identity": bool(
            v8_report["polygon_index_topology_identical"]
        ),
        "frozen_lower_body_signature": bool(
            v8_report["frozen_lower_body_unchanged"]
        ),
        "bound_warped_height_envelope": bool(height_envelope["passed"]),
        "one_connected_closed_manifold_body": (
            int(topology["components"]) == 1
            and int(topology["boundary_edges"]) == 0
            and int(topology["nonmanifold_edges"]) == 0
        ),
        "zero_global_exact_nonadjacent_self_intersections_in_every_pose": all(
            int(row["exact_self_intersections"]["exact_genuine_penetration_pair_count"])
            == 0
            for row in pose_values
        ),
        "zero_body_nail_cross_intersections_in_every_pose": all(
            int(row["exact_body_nail_intersections"]["total_exact_genuine_triangle_pair_count"])
            == 0
            for row in pose_values
        ),
        "zero_body_eye_cross_intersections_with_no_geometric_occlusion_exception": all(
            int(row["exact_body_eye_intersections"]["total_exact_genuine_triangle_pair_count"])
            == 0
            for row in pose_values
        ),
        "zero_body_lash_cross_intersections_in_every_pose": all(
            int(row["exact_body_lash_intersections"]["total_exact_genuine_triangle_pair_count"])
            == 0
            for row in pose_values
        ),
        "zero_body_brow_cross_intersections_in_every_pose": all(
            int(row["exact_body_brow_intersections"]["total_exact_genuine_triangle_pair_count"])
            == 0
            for row in pose_values
        ),
        "lash_and_brow_surface_follow_in_every_pose": all(
            "lash_surface_follow" not in row["failures"]
            and "brow_root_surface_follow" not in row["failures"]
            for row in pose_values
        ),
        "zero_flipped_triangles": int(deformation["flipped_triangle_count"]) == 0,
        "zero_near_zero_triangles": (
            int(deformation["canonical_near_zero_area_triangle_count"]) == 0
            and int(deformation["deformed_near_zero_area_triangle_count"]) == 0
        ),
        "edge_stretch_and_area_ratio_bounds": all(
            bool(row["edge_and_area_deformation"]["passed"])
            for row in pose_values
        ),
        "official_weight_full_coverage_and_normalization": (
            float(transfer["coverage"]) == 1.0
            and int(transfer["root_fallback_vertex_count"]) == 0
            and float(transfer["weight_sum_minimum"]) >= 0.999999
            and float(transfer["weight_sum_maximum"]) <= 1.000001
        ),
        "joint_and_rotation_plane_provenance": (
            int(rig["bone_count"])
            == int(config["inputs"]["makehuman_skeleton"]["bone_count"])
            and int(rig["source_joint_count"])
            == int(config["inputs"]["makehuman_skeleton"]["joint_count"])
            and int(rig["source_rotation_plane_count"])
            == int(config["inputs"]["makehuman_skeleton"]["rotation_plane_count"])
            and float(rig["bone_rotation_plane_coverage"]) == 1.0
            and int(rig["roll_alignment_failure_count"]) == 0
        ),
        "regional_skin_single_continuous_nonuniform_masks": (
            int(scope_report["body_material_slot_count"]) == 1
            and bool(scope_report["body_regional_skin_direction"])
            and not bool(scope_report["body_single_flat_color_used"])
            and not bool(scope_report["body_geometry_plate_regions_used"])
            and all(
                int(row["vertex_count"]) > 0
                for row in regional_skin["mask_records"].values()
            )
        ),
        "fixed_seat_floor_supine_and_reach_contact_metrics": all(
            contact_gate(pose_reports[name]["support_contact"])
            and int(
                pose_reports[name]["exact_body_support_prop_intersections"][
                    "total_exact_genuine_triangle_pair_count"
                ]
            )
            == 0
            for name in special_contacts
        ),
        "stored_actions_match_direct_pose_meshes": all(
            bool(row["stored_action_mesh_verification"]["passed"])
            for row in pose_values
        ),
        "measured_named_knee_angles_within_tolerance": all(
            bool(row["measured_knee_flexion"]["passed"])
            for row in pose_values
        ),
        "twenty_nails_present_with_natural_material_and_oval_construction": (
            int(nail_count) == 20
            and bool(
                nail_report["gates"][
                    "all_twenty_natural_material_and_oval_construction"
                ]
            )
        ),
        "all_twenty_nails_strict_declared_digit_footprint": bool(
            nail_report["gates"][
                "all_twenty_strict_declared_digit_footprints"
            ]
        ),
        "all_twenty_nails_complete_evaluated_shell": bool(
            nail_report["gates"][
                "all_twenty_complete_evaluated_armature_solidify_shells"
            ]
        )
        and bool(
            nail_report["gates"]["all_twenty_zero_rest_shell_penetrations"]
        ),
        "all_twenty_nails_exact_terminal_bone_attachment": bool(
            nail_report["gates"][
                "all_twenty_exact_terminal_bone_attachments"
            ]
        ),
        "nail_surface_follow_in_every_pose": all(
            "nail_surface_follow" not in row["failures"]
            for row in pose_values
        ),
        "scalp_hair_object_dependency_absent": int(
            bald_audit["scalp_hair_runtime_dependency_count"]
        )
        == 0,
        "private_inactive_unassigned_unpublished_flags": bool(
            scope_report["passed"]
        ),
    }
    required = set(map(str, config["mandatory_exact_audits"]))
    if set(audits) != required:
        raise RobertR26BuildError(
            "computed mandatory-audit inventory differs from config: "
            + json.dumps(
                {
                    "missing": sorted(required - set(audits)),
                    "unexpected": sorted(set(audits) - required),
                },
                sort_keys=True,
            )
        )
    failed = sorted(name for name, passed in audits.items() if not passed)
    if failed:
        raise RobertR26BuildError(
            f"one or more computed mandatory audits failed: {failed}"
        )
    return audits


def set_scene_scope(config: Mapping[str, Any]) -> None:
    scene = bpy.context.scene
    values = {
        "candidate_id": str(config["candidate_id"]),
        "person_id": "biological_robert",
        "body_class": "adult_male",
        "confirmed_adult": True,
        "private_owner_review_only": True,
        "inactive_candidate": True,
        "unassigned_candidate": True,
        "owner_approved": False,
        "runtime_assignment_allowed": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "clothing_included": False,
        "scalp_hair_dependency_present": False,
        "complete_human_activity_claimed": False,
    }
    for key, value in values.items():
        scene[key] = value


def write_package_manifest(directory: Path) -> Path:
    manifest_path = directory / "PACKAGE_MANIFEST.json"
    if manifest_path.exists():
        raise RobertR26BuildError(f"refusing manifest overwrite: {manifest_path}")
    files = []
    for path in sorted(value for value in directory.rglob("*") if value.is_file()):
        if path == manifest_path:
            continue
        files.append(
            {
                "path": path.relative_to(directory).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = {
        "schema": "kira.avatar.private_owner_review_package_manifest.v1",
        "candidate_id": "BIOLOGICAL_ROBERT_R26_BALD_OWNER_REVIEW",
        "created_utc": utc_now(),
        "file_count_excluding_manifest": len(files),
        "files": files,
        "append_only": True,
        "private": True,
        "inactive": True,
        "owner_approved": False,
    }
    write_json(manifest_path, payload)
    return manifest_path


def verify_package_manifest(directory: Path, manifest_path: Path) -> dict[str, Any]:
    payload = json_file(manifest_path)
    listed = {
        str(row["path"]): row for row in payload.get("files", [])
    }
    actual_paths = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if set(listed) != actual_paths:
        raise RobertR26BuildError(
            "staging package manifest inventory differs from filesystem"
        )
    failures: list[dict[str, Any]] = []
    for relative, row in sorted(listed.items()):
        path = directory / Path(relative)
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        if actual_hash != str(row["sha256"]).lower() or actual_bytes != int(
            row["bytes"]
        ):
            failures.append(
                {
                    "path": relative,
                    "expected_sha256": row["sha256"],
                    "actual_sha256": actual_hash,
                    "expected_bytes": row["bytes"],
                    "actual_bytes": actual_bytes,
                }
            )
    if failures:
        raise RobertR26BuildError(
            "staging package manifest verification failed: "
            + json.dumps(failures, sort_keys=True)
        )
    return {
        "file_count_excluding_manifest": len(listed),
        "inventory_exact": True,
        "all_hashes_and_sizes_verified": True,
    }


def create_staging_directory(config: Mapping[str, Any]) -> Path:
    root = project_path(str(config["output"]["staging_root"]))
    require_inside_project(root)
    root.mkdir(parents=True, exist_ok=True)
    directory = root / (
        "attempt_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid.uuid4().hex[:10]
    )
    if directory.exists():
        raise RobertR26BuildError(f"unique staging path unexpectedly exists: {directory}")
    directory.mkdir()
    return directory


def preserve_failure_record(stage: Path | None, exc: BaseException) -> None:
    if stage is None or not stage.is_dir():
        return
    path = stage / "FAILED_BUILD.json"
    if path.exists():
        return
    write_json(
        path,
        {
            "schema": "kira.avatar.failed_private_candidate_build.v1",
            "status": "FAILED_STAGING_PRESERVED_NOT_PUBLISHED",
            "failed_utc": utc_now(),
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "candidate_output_created": False,
            "staging_preserved": True,
        },
    )


def publish_staging(stage: Path, output: Path) -> None:
    require_inside_project(stage)
    require_inside_project(output)
    if output.exists():
        raise RobertR26BuildError(f"candidate output appeared before publish: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage.replace(output)
    if stage.exists() or not output.is_dir():
        raise RobertR26BuildError("atomic candidate-directory publish did not complete")


def main() -> None:
    args = arguments()
    config_path = project_path(str(args.config))
    require_inside_project(config_path)
    config = json_file(config_path)
    if config.get("status") != "READY_FOR_RELEASED_BOUNDED_RUN":
        raise RobertR26BuildError("R26 config status no longer matches preparation lock")

    # These gates run before any bpy operation or directory creation.
    output_dir = verify_interlocks(args, config)
    output_absent_before_run = not output_dir.exists()
    release_record = verify_release_checkpoint(args, config, config_path)
    stage: Path | None = (
        create_staging_directory(config)
        if args.complete_private_review_package
        else None
    )
    try:
        input_records_before = verify_bound_inputs(config)
        source_vertices, source_groups, target_records = target_deformed_source(config)
        source_weights = read_source_weights(
            project_path(str(config["inputs"]["makehuman_weights"]["path"])),
            len(source_vertices),
        )

        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        canonical, warped, v8_append_report = append_v8_objects(config)
        v8_report = validate_v8(config, canonical, warped)
        height_envelope = validate_expected_warped_height_envelope(
            config, warped, v8_report
        )
        topology = topology_report(warped)
        deformation_report = deformation_quality(canonical, warped)
        pre_scale_intersections = exact_intersection_report(warped)

        transfer_tree, triangle_sources, tree_points = source_weight_surface(
            source_vertices,
            source_groups,
            float(config["foundation_truth"]["helper_root_inset_native_units"]),
        )
        max_residual_native = (
            float(config["rigging"]["required_transfer_residual_m"])
            / float(config["foundation_truth"]["native_to_blender_scale"])
        )
        normalized_weights, associations, transfer_report = interpolate_weights(
            canonical,
            transfer_tree,
            triangle_sources,
            tree_points,
            source_weights,
            max_residual_native=max_residual_native,
            max_influences=int(config["rigging"]["max_influences_per_vertex"]),
        )

        remove_everything_except([warped])
        warped.name = str(config["candidate_id"]) + "_primary_adult_surface"
        warped.data.name = warped.name + "_mesh"
        body_flags(warped, config)
        floor_native, height = prepare_body_for_meters(warped, config)
        if floor_native != float(height_envelope["actual_native_floor_z"]):
            raise RobertR26BuildError("prepared body floor differs from bound warped floor")
        expected_height = float(height_envelope["expected_warped_height_m"])
        height_tolerance = float(
            height_envelope["expected_warped_height_tolerance_m"]
        )
        if abs(height - expected_height) > height_tolerance:
            raise RobertR26BuildError(
                "prepared body height differs from bound warped expectation: "
                f"expected={expected_height:.15f} actual={height:.15f} "
                f"tolerance={height_tolerance:.15f}"
            )
        height_envelope["prepared_height_m"] = height
        height_envelope["prepared_height_delta_m"] = height - expected_height
        material, skin_report = regional_skin_material(
            warped,
            config,
            associations,
            normalized_weights,
        )
        warped.data.materials.clear()
        warped.data.materials.append(material)
        armature, rig_report = build_official_armature(
            warped,
            config,
            source_vertices,
            normalized_weights,
            floor_native=floor_native,
        )
        nails, nail_report = add_nails(
            warped,
            armature,
            height,
            str(config["candidate_id"]),
        )
        eye_objects, eye_report = add_blue_gray_eyes(
            body=warped,
            armature=armature,
            config=config,
            source_vertices=source_vertices,
            source_groups=source_groups,
            floor_native=floor_native,
        )
        lash_objects, lash_report = add_official_projected_lashes(
            body=warped,
            armature=armature,
            config=config,
            source_vertices=source_vertices,
            source_groups=source_groups,
            source_weights=source_weights,
            floor_native=floor_native,
        )
        brow_objects, brow_report = add_projected_strand_brows(
            body=warped,
            armature=armature,
            config=config,
            eye_objects=eye_objects,
        )
        apply_component_scope(
            [
                warped,
                armature,
                *nails,
                *eye_objects,
                *lash_objects,
                *brow_objects,
            ]
        )

        region_map = movement_region_map(warped)
        poses, solver_report = build_pose_specs(
            armature,
            warped,
            region_map,
            config,
        )
        required_pose_names = {
            "neutral_standing",
            "left_knee_30", "left_knee_55", "left_knee_80",
            "right_knee_30", "right_knee_55", "right_knee_80",
            "bilateral_knee_30", "bilateral_knee_55", "bilateral_knee_80",
            "seated_contact",
            "supine_lying_contact",
            "table_reach_eating_foundation",
        }
        if set(poses) != required_pose_names:
            raise RobertR26BuildError(
                f"bounded pose inventory mismatch: {sorted(set(poses) ^ required_pose_names)}"
            )
        action_report = author_actions(
            armature,
            poses,
            str(config["candidate_id"]),
        )
        reset_pose(armature)
        neutral_points = evaluated_vertices(warped)
        if len(neutral_points) != len(warped.data.vertices):
            raise RobertR26BuildError("neutral evaluated topology is not index stable")

        if args.complete_private_review_package:
            if stage is None:
                raise RobertR26BuildError("complete run lost its private staging root")
            exact_directory = stage / "exact_geometry"
            render_directory = stage / "review_renders"
            exact_directory.mkdir()
            render_directory.mkdir()
        else:
            exact_directory = None
            render_directory = None

        pose_reports: dict[str, Any] = {}
        for pose_name, pose_spec in poses.items():
            pose_reports[pose_name] = pose_geometry_audit(
                pose_name=pose_name,
                pose_spec=pose_spec,
                action_name=str(action_report[pose_name]["action"]),
                armature=armature,
                body=warped,
                nails=nails,
                eye_objects=eye_objects,
                lash_objects=lash_objects,
                brow_objects=brow_objects,
                neutral_points=neutral_points,
                region_map=region_map,
                config=config,
                report_directory=exact_directory,
            )
        reset_pose(armature)
        bald_audit = scalp_hair_dependency_audit()
        set_scene_scope(config)

        base_evidence: dict[str, Any] = {
            "schema": "kira.avatar.biological_robert_r26_bald_owner_review.v2",
            "candidate_id": config["candidate_id"],
            "created_utc": utc_now(),
            "scope": {
                "private": True,
                "inactive": True,
                "unassigned": True,
                "unpublished": True,
                "runtime_exported": False,
                "activated": False,
                "clothing_included": False,
                "scalp_hair_dependency_present": False,
                "confirmed_adult": True,
                "body_class": "adult_male",
                "owner_approved": False,
            },
            "input_hashes_before": input_records_before,
            "durable_post_kira_release": release_record,
            "implementation_binding": {
                "worker": {
                    "path": project_relative(Path(__file__).resolve()),
                    "sha256": sha256_file(Path(__file__).resolve()),
                    "bytes": Path(__file__).resolve().stat().st_size,
                },
                "config": {
                    "path": project_relative(config_path),
                    "sha256": sha256_file(config_path),
                    "bytes": config_path.stat().st_size,
                },
            },
            "ordered_target_stack": target_records,
            "v8_library_append": v8_append_report,
            "v8_bounded_identity_surface": v8_report,
            "bound_warped_height_envelope": height_envelope,
            "v8_deformation_quality": deformation_report,
            "qualified_topology": topology,
            "pre_scale_exact_intersections": pre_scale_intersections,
            "official_weight_transfer": transfer_report,
            "official_rig": rig_report,
            "height_m": height,
            "regional_skin": skin_report,
            "natural_nails": nail_report,
            "blue_gray_eyes": eye_report,
            "official_lashes": lash_report,
            "projected_strand_brows": brow_report,
            "movement_solvers": solver_report,
            "actions": action_report,
            "region_map": {
                name: {
                    "vertex_count": len(indices),
                    "vertex_index_sha256": index_signature(indices),
                }
                for name, indices in sorted(region_map.items())
            },
            "pose_geometry_audits": pose_reports,
            "bald_low_resource_contract": bald_audit,
            "truth_limits": {
                "face": (
                    "The bounded v8 face is the strongest source-bound input, "
                    "but Robert likeness and appearance remain owner-review questions."
                ),
                "movement": (
                    "The stored actions prove only the enumerated bounded poses, "
                    "deformation gates, and support contacts. They do not prove "
                    "all human activities, eating physiology, or reproduction."
                ),
                "anatomy": (
                    "The candidate retains the qualified connected adult-male "
                    "external surface. No internal organs or biological function are claimed."
                ),
            },
        }

        if args.structural_preflight_only:
            scope_report = object_scope_audit(
                body=warped,
                armature=armature,
                nails=nails,
                eyes=eye_objects,
                lashes=lash_objects,
                brows=brow_objects,
            )
            input_records_after = verify_bound_inputs(config)
            before_hashes = {row["id"]: row["sha256"] for row in input_records_before}
            after_hashes = {row["id"]: row["sha256"] for row in input_records_after}
            mandatory_audits = computed_mandatory_audits(
                config=config,
                input_hashes_unchanged=before_hashes == after_hashes,
                output_absent_before_run=output_absent_before_run,
                v8_report=v8_report,
                height_envelope=height_envelope,
                topology=topology,
                deformation=deformation_report,
                transfer=transfer_report,
                rig=rig_report,
                regional_skin=skin_report,
                nail_count=len(nails),
                nail_report=nail_report,
                pose_reports=pose_reports,
                bald_audit=bald_audit,
                scope_report=scope_report,
            )
            base_evidence.update(
                {
                    "status": "COMPLETE_IN_MEMORY_PREFLIGHT_PASSED_NOT_SAVED",
                    "object_scope": scope_report,
                    "input_hashes_after": input_records_after,
                    "mandatory_exact_audits": mandatory_audits,
                    "candidate_output_created": False,
                    "review_renders_created": False,
                    "owner_visual_acceptance_claimed": False,
                    "runtime_eligibility": False,
                }
            )
            print(json.dumps(base_evidence, indent=2, sort_keys=True))
            return

        if stage is None or render_directory is None:
            raise RobertR26BuildError("complete run lost its private staging directory")
        scene, camera, render_setup = configure_render(config)
        render_report = render_complete_review_inventory(
            scene=scene,
            camera=camera,
            output_directory=render_directory,
            armature=armature,
            body=warped,
            poses=poses,
            pose_reports=pose_reports,
            region_map=region_map,
            eye_objects=eye_objects,
            config=config,
        )
        scope_report = object_scope_audit(
            body=warped,
            armature=armature,
            nails=nails,
            eyes=eye_objects,
            lashes=lash_objects,
            brows=brow_objects,
        )
        bald_audit = scalp_hair_dependency_audit()
        set_scene_scope(config)
        reset_pose(armature)

        blend_path = stage / str(config["output"]["blend_name"])
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
        if not blend_path.is_file() or blend_path.stat().st_size <= 0:
            raise RobertR26BuildError("private candidate Blend did not save")
        input_records_after = verify_bound_inputs(config)
        before_hashes = {row["id"]: row["sha256"] for row in input_records_before}
        after_hashes = {row["id"]: row["sha256"] for row in input_records_after}
        if before_hashes != after_hashes:
            raise RobertR26BuildError("one or more protected inputs changed during build")
        mandatory_audits = computed_mandatory_audits(
            config=config,
            input_hashes_unchanged=True,
            output_absent_before_run=output_absent_before_run,
            v8_report=v8_report,
            height_envelope=height_envelope,
            topology=topology,
            deformation=deformation_report,
            transfer=transfer_report,
            rig=rig_report,
            regional_skin=skin_report,
            nail_count=len(nails),
            nail_report=nail_report,
            pose_reports=pose_reports,
            bald_audit=bald_audit,
            scope_report=scope_report,
        )

        evidence = {
            **base_evidence,
            "status": "PRIVATE_INACTIVE_COMPLETE_OWNER_REVIEW_CANDIDATE_AWAITING_ROBERT_VISUAL_DECISION",
            "input_hashes_after": input_records_after,
            "protected_inputs_unchanged": True,
            "mandatory_exact_audits": mandatory_audits,
            "render_setup": render_setup,
            "private_review_renders": render_report,
            "object_scope": scope_report,
            "bald_low_resource_contract": bald_audit,
            "artifacts": {
                "blend": {
                    "package_relative_path": blend_path.name,
                    "sha256": sha256_file(blend_path),
                    "bytes": blend_path.stat().st_size,
                }
            },
            "gates": {
                "all_source_hashes_exact": True,
                "one_connected_closed_adult_male_surface": True,
                "zero_v8_flipped_or_collapsed_triangles": True,
                "official_weight_coverage_100_percent": True,
                "official_163_bone_rig": len(armature.data.bones) == 163,
                "exactly_twenty_nails_with_natural_material_and_oval_construction": (
                    len(nails) == 20
                    and bool(
                        nail_report["gates"][
                            "all_twenty_natural_material_and_oval_construction"
                        ]
                    )
                ),
                "all_twenty_strict_declared_digit_footprints": bool(
                    nail_report["gates"][
                        "all_twenty_strict_declared_digit_footprints"
                    ]
                ),
                "all_twenty_complete_evaluated_shells": bool(
                    nail_report["gates"][
                        "all_twenty_complete_evaluated_armature_solidify_shells"
                    ]
                )
                and bool(
                    nail_report["gates"][
                        "all_twenty_zero_rest_shell_penetrations"
                    ]
                ),
                "all_twenty_exact_terminal_bone_attachments": bool(
                    nail_report["gates"][
                        "all_twenty_exact_terminal_bone_attachments"
                    ]
                ),
                "actual_muted_blue_gray_optical_eye_stack": len(eye_objects) == 6,
                "official_weighted_lashes": len(lash_objects) == 4,
                "projected_individual_strand_brows": len(brow_objects) == 2,
                "regional_skin_not_uniform": True,
                "every_pose_exact_geometry_gate": all(
                    bool(report["passed"]) for report in pose_reports.values()
                ),
                "exact_review_render_inventory": bool(
                    render_report["required_inventory_exact"]
                ),
                "scalp_hair_runtime_dependency_absent": True,
                "private_inactive_unassigned_unpublished": True,
                "owner_likeness_approved": False,
                "whole_body_owner_approved": False,
                "runtime_eligible": False,
            },
        }
        evidence_path = stage / str(config["output"]["evidence_name"])
        write_json(evidence_path, evidence)
        review_path = stage / "OWNER_REVIEW_README.md"
        review_path.write_text(
            "\n".join(
                [
                    "# Biological Robert R26 bald body — private owner review",
                    "",
                    "Status: **COMPLETE CANDIDATE; NOT ACCEPTED, ASSIGNED, OR ACTIVE**",
                    "",
                    "This append-only package contains one connected closed adult-male external surface, the official CC0 163-bone MakeHuman rig and source-bound weights, muted blue/blue-gray optical eyes, official weighted lashes, projected strand eyebrows, regional skin, and twenty detachable natural nails.",
                    "",
                    "The review set includes every required neutral angle and detail, private protected adult views, unilateral and bilateral knee poses at 30/55/80 degrees, one seated-contact pose, one supine-support pose, and one table-reach foundation.",
                    "",
                    "The face input is not claimed to be an approved Robert likeness. Movement evidence is bounded to the exact poses tested and does not claim every human action, eating physiology, internal anatomy, reproduction, or biological humanity.",
                    "",
                    "No scalp hair, clothing, live export, roster assignment, activation, publication, or upload is included. Robert must visually decide whether this candidate is acceptable or needs targeted correction.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        rollback_path = stage / "ROLLBACK.md"
        rollback_path.write_text(
            "\n".join(
                [
                    "# Biological Robert R26 rollback",
                    "",
                    "The worker does not modify or replace a live Robert avatar, roster entry, launcher, or protected source.",
                    "Rollback means moving this single append-only private candidate directory to an owner-selected archive location.",
                    "Do not delete or overwrite the bound foundation, v8 face diagnostic, official MakeHuman files, or earlier rejected Robert evidence.",
                    "No rollback command is executed automatically.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        checkpoint_path = stage / "CHECKPOINT.md"
        checkpoint_path.write_text(
            "\n".join(
                [
                    "# Biological Robert R26 private candidate checkpoint",
                    "",
                    f"Created UTC: `{evidence['created_utc']}`",
                    f"Candidate: `{config['candidate_id']}`",
                    f"Blend SHA-256: `{sha256_file(blend_path)}`",
                    f"Build evidence SHA-256: `{sha256_file(evidence_path)}`",
                    f"Required render count: `{render_report['render_count']}`",
                    "",
                    "The package is private, inactive, unassigned, unpublished, and not runtime eligible.",
                    "Robert likeness and whole-body visual acceptance remain pending owner review.",
                    "Rollback instructions are in `ROLLBACK.md`.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        manifest_path = write_package_manifest(stage)
        manifest_verification = verify_package_manifest(stage, manifest_path)
        output_record = {
            "ok": True,
            "status": evidence["status"],
            "candidate_directory": project_relative(output_dir),
            "blend_sha256": sha256_file(blend_path),
            "evidence_sha256": sha256_file(evidence_path),
            "checkpoint_sha256": sha256_file(checkpoint_path),
            "manifest_sha256": sha256_file(manifest_path),
            "manifest_verification": manifest_verification,
            "render_count": int(render_report["render_count"]),
            "owner_approved": False,
            "runtime_eligible": False,
        }
        publish_staging(stage, output_dir)
        stage = None
        print(json.dumps(output_record, indent=2, sort_keys=True))
    except BaseException as exc:
        preserve_failure_record(stage, exc)
        raise


if __name__ == "__main__":
    main()
